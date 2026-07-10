"""
Map ip_infrastructure_provider in the 10 SEA OpenINTEL datasets using the CAIDA
AS-Organizations snapshots, LONGITUDINALLY: every row is mapped with the CAIDA
snapshot from the SAME month as that row's measurement_period.

Input  : OpenINTEL_sea_output/openintel_ip_infrastructure_extended_<cc>.csv   (provider column blank)
CAIDA   : CAIDA_as_org/<YYYYMM>01.as-org2info.txt.gz                          (one per month 202503..202606)
Output  : OpenINTEL_sea_output_caida_mapped/openintel_ip_infrastructure_extended_<cc>.csv
          (a NEW file per country; the ORIGINAL input files are left untouched)

What this fills:
  * ip_infrastructure_provider  <- "<org_name> (<aut_name>)" from the row's-month CAIDA snapshot
                                    (org_name from ASN->org_id->org_name; aut_name as fallback)
What this does NOT touch:
  * infrastructure_jurisdiction  <- left BLANK. Jurisdiction is assigned later by the
                                    researcher's controlling-ownership operationalisation, NOT
                                    by CAIDA's RIR registration country.
  * infrastructure_country       <- left as OpenINTEL's own IP geolocation (unchanged).

Rows whose ASN is not found in that month's CAIDA snapshot get the literal marker
"ASN <n> not in CAIDA <YYYYMM>" so they are easy to find and audit (never a guessed name).

Run (one country at a time, or all):
  /opt/anaconda3/bin/python3 map_openintel_caida_sea.py                 # all 10
  /opt/anaconda3/bin/python3 map_openintel_caida_sea.py --countries MY  # subset
"""

import argparse
import csv
import gzip
import os
import sys
from functools import lru_cache

csv.field_size_limit(sys.maxsize)

BASE = "/Users/newlivehung/Desktop/11. Pulse Research Fellowship/06.07.2026_Folder"
CAIDA_DIR = os.path.join(BASE, "CAIDA_as_org")
IN_DIR = os.path.join(BASE, "OpenINTEL_sea_output")
OUT_DIR = os.path.join(BASE, "OpenINTEL_sea_output_caida_mapped")

COUNTRIES = ["BN", "ID", "KH", "LA", "MM", "MY", "PH", "SG", "TH", "VN"]


@lru_cache(maxsize=3)
def load_snapshot(yyyymm):
    """Parse the CAIDA snapshot for a given YYYYMM. Returns (org_name_by_id,
    org_id_by_asn, aut_name_by_asn) or None if that snapshot file is missing.
    lru_cache keeps at most 3 parsed snapshots in memory at once (low, bounded RAM)."""
    path = os.path.join(CAIDA_DIR, f"{yyyymm}01.as-org2info.txt.gz")
    if not os.path.exists(path):
        return None

    org_name_by_id = {}
    org_id_by_asn = {}
    aut_name_by_asn = {}
    section = None

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#"):
                low = line.lower()
                if "format:aut|" in low or "format: aut|" in low:
                    section = "AS"
                elif "format:org_id|" in low or "format: org_id|" in low:
                    section = "ORG"
                continue
            if not line.strip():
                continue
            parts = line.split("|")
            if section == "AS" and len(parts) >= 4:
                try:
                    asn = int(parts[0].strip())
                except ValueError:
                    continue
                aut_name_by_asn[asn] = parts[2].strip()
                org_id_by_asn[asn] = parts[3].strip()
            elif section == "ORG" and len(parts) >= 3:
                org_name_by_id[parts[0].strip()] = parts[2].strip()

    return org_name_by_id, org_id_by_asn, aut_name_by_asn


def lookup_provider(asn_int, snap):
    org_name_by_id, org_id_by_asn, aut_name_by_asn = snap
    org_id = org_id_by_asn.get(asn_int)
    org_name = org_name_by_id.get(org_id) if org_id else None
    aut_name = aut_name_by_asn.get(asn_int)
    if org_name and aut_name:
        return f"{org_name} ({aut_name})"
    if org_name:
        return org_name
    if aut_name:
        return aut_name
    return None


def process_country(cc):
    in_path = os.path.join(IN_DIR, f"openintel_ip_infrastructure_extended_{cc}.csv")
    out_path = os.path.join(OUT_DIR, f"openintel_ip_infrastructure_extended_{cc}.csv")
    if not os.path.exists(in_path):
        print(f"[skip] {cc}: input not found ({in_path})")
        return

    with open(in_path, newline="", encoding="utf-8") as fin:
        reader = csv.reader(fin)
        header = next(reader)
        i_mp = header.index("measurement_period")
        i_asn = header.index("as_number")
        i_prov = header.index("ip_infrastructure_provider")

        total = 0
        matched = 0
        unmatched = {}          # asn -> count
        no_snapshot_months = {}  # yyyymm -> count

        with open(out_path, "w", newline="", encoding="utf-8") as fout:
            writer = csv.writer(fout)
            writer.writerow(header)

            for row in reader:
                total += 1
                mp = (row[i_mp] or "").strip()
                snap = load_snapshot(mp)
                if snap is None:
                    row[i_prov] = f"no CAIDA snapshot for {mp}"
                    no_snapshot_months[mp] = no_snapshot_months.get(mp, 0) + 1
                    writer.writerow(row)
                    continue

                raw_asn = (row[i_asn] or "").strip()
                try:
                    asn_int = int(float(raw_asn))
                except (ValueError, TypeError):
                    row[i_prov] = "ASN unparseable"
                    unmatched[f"unparseable:{raw_asn!r}"] = unmatched.get(f"unparseable:{raw_asn!r}", 0) + 1
                    writer.writerow(row)
                    continue

                provider = lookup_provider(asn_int, snap)
                if provider:
                    row[i_prov] = provider
                    matched += 1
                else:
                    row[i_prov] = f"ASN {asn_int} not in CAIDA {mp}"
                    unmatched[asn_int] = unmatched.get(asn_int, 0) + 1
                writer.writerow(row)

    pct = (100.0 * matched / total) if total else 0.0
    print(f"[done] {cc}: {total:,} rows, {matched:,} matched ({pct:.1f}%), "
          f"{len(unmatched)} distinct unmatched ASNs -> {out_path}")
    if no_snapshot_months:
        print(f"        WARNING months with no CAIDA snapshot on disk: {no_snapshot_months}")
    if unmatched:
        top = sorted(((v, k) for k, v in unmatched.items()), reverse=True)[:15]
        print("        top unmatched (rows, ASN):")
        for v, k in top:
            print(f"          {v:>7,}  AS{k}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", nargs="+", default=COUNTRIES,
                    help="subset of ISO-2 codes (default: all 10)")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    for cc in args.countries:
        process_country(cc.upper())


if __name__ == "__main__":
    main()
