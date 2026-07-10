"""
Build the EXTENDED OpenINTEL IP-infrastructure dataset (MY, SG, TH), 2025-03 -> 2026-06.

Reproduces the schema of the pilot openintel_ip_infrastructure_202601_v5.csv, but for the
full date range, from the raw OpenINTEL daily parquet shards the user downloaded into
OpenINTEL/<Country>/<CC>_YYYY_MM/*.parquet .

Per the user's instruction, EVERY CrUX top-1000 domain (country-specific) that returns an
IPv4 A-record is kept -- one row per A-record, all days -- with NO artificial cap.
ip_infrastructure_provider and infrastructure_jurisdiction are left BLANK on purpose
(the researcher maps them manually with the CAIDA AS-org dataset).

Column mapping (identical to the v5 pilot schema):
  country               <- folder (MY / SG / TH)
  measurement_period    <- folder month (CC_2025_03 -> 202503)
  website               <- parquet query_name, trailing '.' stripped, lowercased
  website_rank          <- rank from that country-month's CrUX top-1000 list
  ip_infrastructure_provider  <- "" (mapped later by researcher via CAIDA)
  infrastructure_jurisdiction <- "" (mapped later by researcher)
  infrastructure_country <- parquet country (OpenINTEL's geolocation of the IP)
  as_number             <- parquet as
  ip_address            <- parquet ip4_address
  source                <- "OpenINTEL CrUX"
  extraction_date       <- day parsed from the parquet timestamp (epoch ms) -> YYYY-MM-DD

Filter applied to each daily parquet:
  response_type == 'A'  AND  ip4_address is not null  AND  host in that month's CrUX top-1000

Robustness:
  * Streams one parquet file at a time (never loads 58 GB at once); low, steady memory.
  * Resumable: records each finished parquet in a state file and skips it on re-run.
  * Disk guard: if free space drops below MIN_FREE_MB it stops cleanly (re-run to continue).

Run (with the anaconda python that has pyarrow/pandas):
  /opt/anaconda3/bin/python3 build_openintel_extended.py
Optional flags:
  --countries Malaysia Singapore Thailand   (subset)
  --limit-files N                            (process only first N parquet files; for testing)
  --outdir PATH                              (default: OpenINTEL_sea_output next to the raw data)
"""

import argparse
import csv
import datetime
import glob
import os
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

BASE = "/Users/newlivehung/Desktop/11. Pulse Research Fellowship/06.07.2026_Folder"
OPENINTEL_DIR = os.path.join(BASE, "OpenINTEL")
CRUX_CSV = os.path.join(BASE, "Crux_top_1000_202401_202605.csv")
DEFAULT_OUTDIR = os.path.join(BASE, "OpenINTEL_sea_output")

COUNTRY_CODE = {"Malaysia": "MY", "Singapore": "SG", "Thailand": "TH", "Indonesia": "ID", "Philippines": "PH",
                "Vietnam": "VN", "Brunei": "BN", "Cambodia": "KH", "Laos": "LA", "Myanmar": "MM"}
CRUX_LAST_MONTH = "202605"   # newest CrUX top-1000 list available; used as fallback for 202606
MIN_FREE_MB = 100            # stop safely if free disk drops below this
BATCH_ROWS = 100000          # rows read into RAM at a time; streaming keeps memory low so a
#                              near-full disk is not filled by macOS swap on large parquet files

READ_COLUMNS = ["query_name", "response_type", "ip4_address", "country", "as", "timestamp"]
OUT_HEADER = ["country", "measurement_period", "website", "website_rank",
              "ip_infrastructure_provider", "infrastructure_jurisdiction",
              "infrastructure_country", "as_number", "ip_address", "source", "extraction_date"]


def norm_host(origin):
    return origin.replace("https://", "").replace("http://", "").rstrip("/").strip().lower()


def load_crux():
    """dict[(cc, yyyymm)] -> dict[host] = rank, from the CrUX top-1000 CSV."""
    table = {}
    with open(CRUX_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["country"], row["measurement_period"])
            table.setdefault(key, {})[norm_host(row["origin"])] = row["rank"]
    return table


def month_of_folder(folder_name):   # "MY_2025_03" -> "202503"
    parts = folder_name.split("_")
    return parts[1] + parts[2]


def free_mb(path):
    return shutil.disk_usage(path).free / 1e6


def process_country(country_name, crux, outdir, limit_files):
    cc = COUNTRY_CODE[country_name]
    country_root = os.path.join(OPENINTEL_DIR, country_name)
    out_path = os.path.join(outdir, f"openintel_ip_infrastructure_extended_{cc}.csv")
    state_path = os.path.join(outdir, f".state_{cc}.txt")

    done = set()
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            done = set(line.strip() for line in f if line.strip())

    write_header = not os.path.exists(out_path)
    total_rows = 0
    files_done = 0

    with open(out_path, "a", newline="", encoding="utf-8") as out_f, \
            open(state_path, "a", encoding="utf-8") as st_f:
        writer = csv.writer(out_f)
        if write_header:
            writer.writerow(OUT_HEADER)
            out_f.flush()

        # month folders may be nested (OpenINTEL/<Country>/<CC>_YYYY_MM) or flat (OpenINTEL/<CC>_YYYY_MM)
        month_dirs = sorted(glob.glob(os.path.join(country_root, f"{cc}_*")))
        if not month_dirs:
            month_dirs = sorted(glob.glob(os.path.join(OPENINTEL_DIR, f"{cc}_*")))
        for month_dir in month_dirs:
            if not os.path.isdir(month_dir):
                continue
            mp = month_of_folder(os.path.basename(month_dir))
            crux_key = (cc, mp) if (cc, mp) in crux else (cc, CRUX_LAST_MONTH)
            hosts = crux.get(crux_key)
            if not hosts:
                print(f"  [skip] no CrUX list for {cc} {mp}")
                continue
            if crux_key[1] != mp:
                print(f"  [note] {cc} {mp}: no CrUX list for this month; using {CRUX_LAST_MONTH} list")

            # value set for a fast Arrow membership test: host and host-with-trailing-dot
            value_set = []
            for h in hosts:
                value_set.append(h)
                value_set.append(h + ".")
            value_arr = pa.array(value_set, type=pa.string())

            for pfile in sorted(glob.glob(os.path.join(month_dir, "*.parquet"))):
                if pfile in done:
                    continue
                if free_mb(outdir) < MIN_FREE_MB:
                    print(f"\n*** LOW DISK (<{MIN_FREE_MB} MB free) — stopping cleanly. "
                          f"Free space and re-run to resume {cc} from here.")
                    return "lowdisk", total_rows, files_done

                # Stream the file in batches of BATCH_ROWS instead of loading all ~1.1M rows
                # at once, so peak RAM stays low and macOS does not swap-fill a near-full disk.
                n = 0
                for batch in pq.ParquetFile(pfile).iter_batches(batch_size=BATCH_ROWS, columns=READ_COLUMNS):
                    table = pa.Table.from_batches([batch])
                    qn_lower = pc.utf8_lower(table["query_name"])
                    mask = pc.and_(
                        pc.equal(table["response_type"], "A"),
                        pc.and_(pc.is_valid(table["ip4_address"]),
                                pc.is_in(qn_lower, value_set=value_arr)),
                    )
                    sub = table.filter(mask)

                    qn = sub["query_name"].to_pylist()
                    ip = sub["ip4_address"].to_pylist()
                    ctry = sub["country"].to_pylist()
                    asn = sub["as"].to_pylist()
                    ts = sub["timestamp"].to_pylist()

                    for j in range(len(qn)):
                        host = (qn[j] or "").rstrip(".").lower()
                        rank = hosts.get(host)
                        if rank is None:
                            continue
                        day = datetime.datetime.fromtimestamp(ts[j] / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
                        writer.writerow([cc, mp, host, rank, "", "",
                                         ctry[j] or "", asn[j] or "", ip[j] or "",
                                         "OpenINTEL CrUX", day])
                        n += 1
                    del table, sub, qn, ip, ctry, asn, ts

                out_f.flush()
                st_f.write(pfile + "\n")
                st_f.flush()
                done.add(pfile)
                total_rows += n
                files_done += 1
                print(f"  {cc} {os.path.basename(month_dir)} "
                      f"{os.path.basename(pfile)[:22]} -> {n} rows  (cum {total_rows})")

                if limit_files and files_done >= limit_files:
                    return "limit", total_rows, files_done

    return "done", total_rows, files_done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", nargs="+", default=["Malaysia", "Singapore", "Thailand"])
    ap.add_argument("--limit-files", type=int, default=0, help="process only first N files (testing)")
    ap.add_argument("--outdir", default=DEFAULT_OUTDIR)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    print(f"free disk: {free_mb(args.outdir):.0f} MB | output dir: {args.outdir}")
    print("loading CrUX top-1000 lists...")
    crux = load_crux()

    for country in args.countries:
        if country not in COUNTRY_CODE:
            print(f"[skip] unknown country {country}")
            continue
        print(f"\n=== {country} ({COUNTRY_CODE[country]}) ===")
        status, rows, files = process_country(country, crux, args.outdir, args.limit_files)
        print(f"--- {country}: {status}; {files} files, {rows} rows this run ---")
        if status == "lowdisk":
            print("Stopped early due to low disk. Re-run the same command to resume.")
            break


if __name__ == "__main__":
    main()
