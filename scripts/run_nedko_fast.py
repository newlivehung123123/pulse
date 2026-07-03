"""
Nedko CDN detection — Southeast Asia expansion (2024-01 to 2026-05), server-less.

WHY THIS REPLACES run_nedko_sea.py + the Flask server:
The cdn-check Flask app runs, per domain, four extra probes we do not use
(SSL handshake, whois.whois() with NO timeout, email-security DNS, reverse DNS).
Those made each request take 15-30s; whois in particular can hang far longer.
The client timed out at 15s and mislabelled finished work as "timed out".

This script keeps ONLY Nedko's actual CDN-detection logic, copied verbatim from
cdn-check/app.py (the CDNS signature table + the +3 header / +4 CNAME / highest-score
scoring in check_cdn()), so results are methodologically identical to the Jan-2026
Thailand pilot. It drops the server (no port 5000 / AirPlay clash, no Flask-Limiter
429s, no single-thread blocking), adds a hard timeout to every network call, runs
domains concurrently, and is resume-safe.

Per domain it does exactly what Nedko does for CDN + IP:
  1. HTTP GET https://<host>  -> response headers      (requests, 10s timeout)
  2. CNAME lookup for host and its www/apex variant     (dnspython, 5s timeout)
  3. socket.gethostbyname(host) -> ip_address
Then scores headers/CNAMEs against CDNS exactly as app.py does.

Usage (run with the venv python that already has requests + dnspython):
  cd "/Users/newlivehung/Desktop/11. Pulse Research Fellowship/06.07.2026_Folder"
  ./cdn-check/venv/bin/python run_nedko_fast.py --country TH --vantage-point "Bangkok residential"
  ./cdn-check/venv/bin/python run_nedko_fast.py --country MY --vantage-point "Surfshark VPN - Kuala Lumpur"

Run one country at a time, matching the VPN-switching plan. Safe to stop (Ctrl+C)
and re-run: it skips rows already written to the output file.
"""

import argparse
import csv
import os
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
import urllib3
import dns.resolver

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

INPUT_CSV = "Crux_top_1000_202401_202605.csv"
OUTPUT_DIR = "nedko_sea_output"

HTTP_TIMEOUT = 10          # seconds, matches app.py requests.get timeout
DNS_TIMEOUT = 5            # seconds, per CNAME query
IP_TIMEOUT = 5            # seconds, for gethostbyname
CHUNK = 100               # domains committed per batch (= resume granularity)
POLL_SECONDS = 15         # how often to re-check the connection while it is down
# Reliable hosts used only to test whether the VPN/connection itself is up.
PROBE_URLS = ("https://www.google.com", "https://www.cloudflare.com", "https://www.wikipedia.org")

# ---------------------------------------------------------------------------
# CDN signatures — copied verbatim from cdn-check/app.py (CDNS dict, lines 28-85)
# so detection is identical to the Nedko tool used for the pilot.
# ---------------------------------------------------------------------------
CDNS = {
    'CloudFlare': {'headers': ['cf-ray', 'cf-cache-status'], 'cname': r'\.cloudflare\.'},
    'Amazon CloudFront': {'headers': ['x-amz-cf-id'], 'cname': r'\.cloudfront\.net'},
    'Fastly': {'headers': ['fastly-debug-digest', 'x-served-by'], 'cname': r'\.fastly\.'},
    'Akamai': {'headers': ['x-akamai-edgescape'], 'cname': r'\.akamai\.|\.edgesuite\.'},
    'Azure CDN': {'headers': ['x-azure-ref'], 'cname': r'\.azureedge\.'},
    'Google Cloud CDN': {'headers': ['x-goog-generation'], 'cname': r'\.googleusercontent\.'},
    'KeyCDN': {'headers': ['x-edge-location'], 'cname': r'\.kxcdn\.'},
    'BunnyCDN': {'headers': ['cdn-pullzone'], 'cname': r'\.b-cdn\.'},
    'SiteGround CDN': {'headers': ['sg-cdn'], 'cname': r'\.sgcdn\.|\.siteground\.'},
    'Vercel': {'headers': ['x-vercel-id', 'x-vercel-cache'],
               'cname': r'\.vercel\.app|\.vercel-dns\.com|\.vercel\.com'},
    'Limelight Networks': {'headers': ['x-llnw-edge'], 'cname': r'\.lldns\.net|\.llnwd\.net'},
    'CDN77': {'headers': ['x-cdn'], 'cname': r'\.cdn77\.net|\.cdn77\.org'},
    'StackPath': {'headers': ['x-sp-edge', 'x-stackpath-edge'],
                  'cname': r'\.stackpathcdn\.com|\.stackpath\.net'},
    'Alibaba Cloud CDN': {'headers': ['ali-swift-global-savetime', 'eagleid'],
                          'cname': r'\.alicdn\.com|\.aliyuncs\.com'},
    'Tencent Cloud CDN': {'headers': ['x-nws-log-uuid'],
                          'cname': r'\.cdn\.dnsv1\.com|\.tencent-cloud\.com'},
    'Imperva': {'headers': ['x-iinfo', 'x-cdn'], 'cname': r'\.incapdns\.net|\.imperva\.com'},
    'Sucuri': {'headers': ['x-sucuri-id', 'x-sucuri-cache'], 'cname': r'\.sucuri\.net'},
    'CacheFly': {'headers': ['x-cf1', 'x-cf2'], 'cname': r'\.cachefly\.net'},
    'Netlify': {'headers': ['x-nf-request-id', 'server'], 'cname': r'\.netlify\.app|\.netlify\.com'},
    'jsDelivr': {'headers': ['x-jsd-version'], 'cname': r'\.jsdelivr\.net'},
}

_resolver = dns.resolver.Resolver()
_resolver.timeout = DNS_TIMEOUT
_resolver.lifetime = DNS_TIMEOUT


def hostname_from_origin(origin: str) -> str:
    parsed = urlparse(origin)
    host = parsed.netloc or parsed.path
    return host.lower().strip()


def resolve_ip(host: str):
    """socket.gethostbyname with a hard timeout via a worker thread."""
    result = {}

    def _lookup():
        try:
            result['ip'] = socket.gethostbyname(host)
        except Exception:
            result['ip'] = None

    t = threading.Thread(target=_lookup, daemon=True)
    t.start()
    t.join(IP_TIMEOUT)
    return result.get('ip')


def get_cnames(host: str):
    """CNAME lookup for host and its www/apex counterpart, exactly as app.py does."""
    cnames = []
    variants = [host, ('www.' + host) if not host.startswith('www.') else host[4:]]
    for d in variants:
        try:
            cnames.extend([str(r.target) for r in _resolver.resolve(d, 'CNAME')])
        except Exception:
            pass
    return cnames


def score_cdn(headers, cnames):
    """Reproduces app.py check_cdn scoring: +3 per header match, +4 per CNAME match, max wins."""
    scores = {}
    header_keys = list(headers.keys())
    for cdn, sigs in CDNS.items():
        score = 0
        for h in sigs['headers']:
            if any(h.lower() in k.lower() for k in header_keys):
                score += 3
        for cname in cnames:
            if re.search(sigs['cname'], cname.lower()):
                score += 4
        if score > 0:
            scores[cdn] = score
    if scores:
        return max(scores, key=scores.get)
    return 'None detected'


def check_domain(host: str):
    """Returns (cdn_provider, ip_address, status). Mirrors the pilot's output semantics.

    CDN detection needs only the response HEADERS (+ CNAME + IP), never the page body.
    stream=True makes requests.get return as soon as headers arrive and skip the body
    download entirely, so an endpoint that streams data forever can never hang a worker.
    We read the headers, then close the connection to release it immediately.
    """
    url = 'https://' + host
    headers = None
    for verify in (True, False):  # try verified, then retry once without verification (as app.py)
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True,
                                verify=verify, stream=True)
            try:
                headers = dict(resp.headers)  # headers only; body is never downloaded
            finally:
                resp.close()
            break
        except requests.exceptions.SSLError:
            continue
        except Exception:
            return 'unknown', '', 'unreachable'
    if headers is None:
        return 'unknown', '', 'unreachable'

    ip = resolve_ip(host) or ''
    cnames = get_cnames(host)
    cdn = score_cdn(headers, cnames)
    return cdn, ip, 'ok'


def load_done_keys(output_path: str):
    done = set()
    if os.path.exists(output_path):
        with open(output_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done.add((row["country"], row["measurement_period"], row["origin"]))
    return done


def connectivity_ok():
    """True if the machine can currently reach the wider internet (i.e. VPN is up)."""
    for probe in PROBE_URLS:
        try:
            requests.get(probe, timeout=8, stream=True).close()
            return True
        except Exception:
            continue
    return False


def wait_for_connectivity():
    """Block until the connection returns, printing a heartbeat. Returns seconds waited."""
    waited = 0
    while not connectivity_ok():
        print(f"  [network down] VPN/connection unreachable — waiting {POLL_SECONDS}s "
              f"(down {waited}s so far). Reconnect Surfshark; the run resumes on its own.")
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    if waited:
        print(f"  [network back] connection restored after {waited}s — resuming.")
    return waited


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", required=True, help="Two-letter country code, e.g. TH, MY")
    parser.add_argument("--vantage-point", required=True,
                        help='e.g. "Bangkok residential" or "Surfshark VPN - Kuala Lumpur"')
    parser.add_argument("--input-csv", default=INPUT_CSV)
    parser.add_argument("--workers", type=int, default=24, help="concurrent requests")
    parser.add_argument("--limit", type=int, default=0, help="process only N rows (0 = all); for testing")
    args = parser.parse_args()

    country = args.country.upper()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"nedko_{country.lower()}_202401_202605.csv")

    done_keys = load_done_keys(output_path)
    print(f"Resuming: {len(done_keys)} rows already done for {country}"
          if done_keys else f"Starting fresh for {country}")

    rows = []
    with open(args.input_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["country"] != country:
                continue
            if (row["country"], row["measurement_period"], row["origin"]) in done_keys:
                continue
            rows.append(row)
    if args.limit:
        rows = rows[:args.limit]

    total = len(rows)
    print(f"{total} rows to process for {country} with {args.workers} workers")
    if total == 0:
        return

    write_header = not os.path.exists(output_path)
    counts = {"ok": 0, "unreachable": 0, "done": 0}

    def work(row):
        host = hostname_from_origin(row["origin"])
        cdn, ip, status = check_domain(host)
        return row, cdn, ip, status

    if not connectivity_ok():
        print("Network/VPN not reachable yet — waiting before starting...")
        wait_for_connectivity()

    with open(output_path, "a", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=[
            "country", "measurement_period", "origin", "cdn_provider",
            "ip_address", "cdn_jurisdiction", "vantage_point", "status",
        ])
        if write_header:
            writer.writeheader()
            out_f.flush()

        # Process in small batches. Each batch is committed to disk ONLY after we
        # confirm the connection was still up when it finished. If the VPN dropped
        # during a batch, its failures are false, so we throw the whole batch away
        # (write nothing), wait for the VPN to return, and re-run the SAME rows.
        # This makes every saved row trustworthy and lets a resume pick up exactly
        # where the last good batch left off.
        i = 0
        while i < total:
            batch = rows[i:i + CHUNK]
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                results = [f.result() for f in as_completed([pool.submit(work, r) for r in batch])]

            fails = sum(1 for (_, _, _, s) in results if s != "ok")

            # A batch with failures might have been caught in a drop. Only trust it
            # if the connection is verifiably up right now; otherwise discard + retry.
            if fails > 0 and not connectivity_ok():
                print(f"  [network dropped @ {i}/{total}] discarded {len(batch)} unwritten "
                      f"results; waiting for the VPN to come back, then retrying this batch.")
                wait_for_connectivity()
                continue  # do NOT advance i and do NOT write — re-run the same batch

            for row, cdn, ip, status in results:
                writer.writerow({
                    "country": row["country"],
                    "measurement_period": row["measurement_period"],
                    "origin": row["origin"],
                    "cdn_provider": cdn,
                    "ip_address": ip,
                    "cdn_jurisdiction": "",
                    "vantage_point": args.vantage_point,
                    "status": status,
                })
                counts["done"] += 1
                counts[status] = counts.get(status, 0) + 1
            out_f.flush()
            i += len(batch)
            print(f"  {counts['done']}/{total}  ok={counts.get('ok', 0)} "
                  f"unreachable={counts.get('unreachable', 0)}")

    print(f"Finished {country}. Output: {output_path}")


if __name__ == "__main__":
    main()
