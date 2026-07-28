"""
Extract all 10 Southeast Asian countries from the ISOC lccrawresults dataset, in the
schema of lccrawresults_full_formatted.csv (the TH/MY pilot).

cdn_jurisdiction is mapped FROM provider_legal_names.csv (the 'Jurisdiction' column),
NOT from a hardcoded grouping and NOT from any model knowledge — the same source used for
the Nedko cdn_jurisdiction, so the two CDN datasets are consistent.

Controlling-ownership OVERRIDES (per the researcher's instruction; these differ from the
registration jurisdiction in provider_legal_names.csv):
    alibaba -> China   (file says Singapore)
    netflix -> US      (file's first 'netflix' row says Singapore)
    (tencent -> China would apply too, but 'tencent' does not appear in the ISOC data.)

Input : 26.05.2026_Folder/lccrawresults.csv
Lookup: 06.07.2026_Folder/provider_legal_names.csv  ('CDN Provider' -> 'Jurisdiction')
Output: 06.07.2026_Folder/lccrawresults_full_formatted_sea.csv

Schema: country, measurement_period, website, website_rank, cdn_provider,
        cdn_jurisdiction, as_number, ip_address, source, extraction_date

Transform: country<-test_cc; measurement_period<-date(DD/MM/YYYY)->YYYYMM; website/
website_rank/ip_address<-NULL; cdn_provider<-host_cdn; as_number<-test_asn;
source<-'lccrawresults'; extraction_date<-date->YYYY-MM-DD.
Filters: test_cc in the 10 SEA codes; drop host_cdn in {'summary','other'}.

Run:
    /opt/anaconda3/bin/python3 build_isoc_sea.py
"""
import csv, os
from collections import Counter

BASE_OLD = "/Users/newlivehung/Desktop/11. Pulse Research Fellowship/26.05.2026_Folder"
BASE_NEW = "/Users/newlivehung/Desktop/11. Pulse Research Fellowship/06.07.2026_Folder"
RAW  = os.path.join(BASE_OLD, "lccrawresults.csv")
PROV = os.path.join(BASE_NEW, "provider_legal_names.csv")
OUT  = os.path.join(BASE_NEW, "lccrawresults_full_formatted_sea.csv")

SEA  = {"BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN"}
DROP = {"summary", "other"}

# ISOC host_cdn labels whose lowercase form does not directly match a 'CDN Provider'
# entry in provider_legal_names.csv -> alias to the matching entry (same company).
ALIAS = {"cloudfront": "amazon cloudfront"}

# controlling-ownership overrides (same substance as the researcher's corrections)
OVERRIDES = {"alibaba": "China", "netflix": "US"}

OUT_HEADER = ["country", "measurement_period", "website", "website_rank", "cdn_provider",
              "cdn_jurisdiction", "as_number", "ip_address", "source", "extraction_date"]


def build_lookup():
    """lowercase(CDN Provider) -> Jurisdiction, from provider_legal_names.csv (first occurrence)."""
    m = {}
    with open(PROV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row["CDN Provider"] or "").strip().lower()
            jur = (row["Jurisdiction"] or "").strip()
            if name and name not in m:
                m[name] = jur
    return m


def jur_for(host_cdn, lookup):
    if host_cdn in OVERRIDES:
        return OVERRIDES[host_cdn]
    return lookup.get(ALIAS.get(host_cdn, host_cdn))   # None if not found -> flagged


def conv_date(d):
    dd, mm, yyyy = d.strip().split("/")
    return yyyy + mm.zfill(2), f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"


def main():
    lookup = build_lookup()
    rows = []
    unmapped = {}
    with open(RAW, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cc = (row.get("test_cc") or "").strip()
            cdn = (row.get("host_cdn") or "").strip()
            if cc not in SEA or cdn in DROP or not cdn:
                continue
            jur = jur_for(cdn, lookup)
            if jur is None:
                unmapped[cdn] = unmapped.get(cdn, 0) + 1
                jur = ""
            mp, exdate = conv_date(row["date"])
            rows.append([cc, mp, "NULL", "NULL", cdn, jur,
                         (row.get("test_asn") or "").strip(), "NULL", "lccrawresults", exdate])

    rows.sort(key=lambda x: (x[0], x[1], x[4], x[6]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(OUT_HEADER)
        w.writerows(rows)

    print(f"wrote {len(rows):,} rows to {OUT}")
    print("host_cdn -> cdn_jurisdiction (from provider_legal_names.csv):")
    seen = {}
    for r in rows:
        seen[r[4]] = r[5]
    for k in sorted(seen):
        tag = "  [OVERRIDE]" if k in OVERRIDES else ""
        print(f"   {k:12s} -> {seen[k]!r}{tag}")
    print("per country     :", dict(Counter(x[0] for x in rows)))
    print("cdn_jurisdiction:", dict(Counter(x[5] for x in rows)))
    if unmapped:
        print("WARNING — host_cdn not found in provider_legal_names.csv (left blank):", unmapped)


if __name__ == "__main__":
    main()
