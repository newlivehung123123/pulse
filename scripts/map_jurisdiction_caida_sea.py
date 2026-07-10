"""
Fill infrastructure_jurisdiction in the 10 SEA OpenINTEL datasets using the CAIDA
AS-Organizations dataset, LONGITUDINALLY (each row uses the CAIDA snapshot from its
own measurement month), by mapping ASN -> org_id -> the org record's `country` field.

IMPORTANT (read before using the output in the paper):
  The value written is the CAIDA/RIR *registered country of the ASN holder*. It is a
  jurisdiction PROXY, NOT controlling ownership. An ASN registered through a foreign
  subsidiary is attributed to the subsidiary's country (e.g. Akamai International B.V.
  -> NL, though Akamai is US-controlled). See CAIDA_jurisdiction_mapping_METHODOLOGY.md
  for the disclosure that must accompany this variable.

Input/Output (updated IN PLACE, safely via a temp file + atomic replace):
  OpenINTEL_sea_output_caida_mapped/openintel_ip_infrastructure_extended_<cc>.csv
    - ip_infrastructure_provider : already filled (map_openintel_caida_sea.py)
    - infrastructure_jurisdiction : filled here from CAIDA org country
    - infrastructure_country      : left as OpenINTEL IP geolocation (unchanged)

Rows with as_number == '--' (OpenINTEL returned no ASN) or an ASN absent from CAIDA get
infrastructure_jurisdiction left BLANK (missing) -- never guessed. Counts are reported.

Run (one country or all):
  /opt/anaconda3/bin/python3 map_jurisdiction_caida_sea.py
  /opt/anaconda3/bin/python3 map_jurisdiction_caida_sea.py --countries MY SG
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
MAP_DIR = os.path.join(BASE, "OpenINTEL_sea_output_caida_mapped")
COUNTRIES = ["BN", "ID", "KH", "LA", "MM", "MY", "PH", "SG", "TH", "VN"]


@lru_cache(maxsize=3)
def load_snapshot(yyyymm):
    """Parse the CAIDA snapshot for YYYYMM -> dict[asn] = org_country (2-letter),
    or None if that snapshot file is missing."""
    path = os.path.join(CAIDA_DIR, f"{yyyymm}01.as-org2info.txt.gz")
    if not os.path.exists(path):
        return None
    org_country_by_id = {}
    org_id_by_asn = {}
    section = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#"):
                low = line.lower()
                if "format:aut|" in low:
                    section = "AS"
                elif "format:org_id|" in low:
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
                org_id_by_asn[asn] = parts[3].strip()
            elif section == "ORG" and len(parts) >= 4:
                # org_id | changed | org_name | country | source
                org_country_by_id[parts[0].strip()] = parts[3].strip()
    # collapse to asn -> country
    return {asn: org_country_by_id.get(oid, "") for asn, oid in org_id_by_asn.items()}


def process_country(cc):
    path = os.path.join(MAP_DIR, f"openintel_ip_infrastructure_extended_{cc}.csv")
    if not os.path.exists(path):
        print(f"[skip] {cc}: not found ({path})")
        return
    tmp = path + ".tmp"

    total = filled = blank_noasn = blank_notcaida = 0
    with open(path, newline="", encoding="utf-8") as fin, \
            open(tmp, "w", newline="", encoding="utf-8") as fout:
        r = csv.reader(fin)
        w = csv.writer(fout)
        header = next(r)
        i_mp = header.index("measurement_period")
        i_asn = header.index("as_number")
        i_jur = header.index("infrastructure_jurisdiction")
        w.writerow(header)

        for row in r:
            total += 1
            mp = row[i_mp].strip()
            asn_raw = (row[i_asn] or "").strip()
            try:
                asn = int(float(asn_raw))
            except (ValueError, TypeError):
                row[i_jur] = ""          # no ASN from OpenINTEL -> missing, never guessed
                blank_noasn += 1
                w.writerow(row); continue
            snap = load_snapshot(mp)
            country = snap.get(asn, "") if snap else ""
            if country:
                row[i_jur] = country
                filled += 1
            else:
                row[i_jur] = ""          # ASN absent from CAIDA -> missing, never guessed
                blank_notcaida += 1
            w.writerow(row)

    os.replace(tmp, path)                 # atomic; original never left half-written
    pct = 100.0 * filled / total if total else 0.0
    print(f"[done] {cc}: {total:,} rows | jurisdiction filled {filled:,} ({pct:.1f}%) | "
          f"blank(no ASN) {blank_noasn:,} | blank(ASN not in CAIDA) {blank_notcaida:,}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", nargs="+", default=COUNTRIES)
    args = ap.parse_args()
    print("Filling infrastructure_jurisdiction from CAIDA org country (registered country "
          "of the ASN holder -- a PROXY, see CAIDA_jurisdiction_mapping_METHODOLOGY.md).\n")
    for cc in args.countries:
        process_country(cc.upper())


if __name__ == "__main__":
    main()
