"""
Fill cdn_jurisdiction in the 10 Nedko CDN datasets, mapped from provider_legal_names.csv.

Input : nedko_sea_output/nedko_<cc>_202401_202605.csv       (cdn_jurisdiction blank)
Lookup: provider_legal_names.csv  (column 'CDN Provider' -> column 'Jurisdiction')
Output: nedko_sea_output_mapped/nedko_<cc>_202401_202605.csv (originals left untouched)

Controlling-ownership OVERRIDES (per the researcher's instruction — these differ from the
registration jurisdiction in provider_legal_names.csv):
    Alibaba Cloud CDN  -> China   (file says Singapore)
    Tencent Cloud CDN  -> China   (file says Singapore; provisional)
(netflix -> US is a correction for the ISOC dataset, not Nedko — Nedko has no 'netflix'.)

Non-provider Nedko values map to BLANK cdn_jurisdiction (they are not companies):
    'unknown'        -> ''   (domain unreachable / no CDN signature matched)
    'None detected'  -> ''   (reachable but matched no signature)

Run:
    /opt/anaconda3/bin/python3 map_nedko_jurisdiction.py
"""
import csv, os, sys
csv.field_size_limit(sys.maxsize)

BASE = "/Users/newlivehung/Desktop/11. Pulse Research Fellowship/06.07.2026_Folder"
IN_DIR  = os.path.join(BASE, "nedko_sea_output")
OUT_DIR = os.path.join(BASE, "nedko_sea_output_mapped")
PROV    = os.path.join(BASE, "provider_legal_names.csv")
CCS = ["bn", "id", "kh", "la", "mm", "my", "ph", "sg", "th", "vn"]

OVERRIDES = {"Alibaba Cloud CDN": "China", "Tencent Cloud CDN": "China"}
NON_PROVIDER = {"unknown": "", "None detected": ""}


def build_map():
    """CDN Provider -> Jurisdiction, from provider_legal_names.csv (first occurrence),
    then apply the controlling-ownership overrides."""
    m = {}
    with open(PROV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            name = (row["CDN Provider"] or "").strip()
            jur = (row["Jurisdiction"] or "").strip()
            if name and name not in m:
                m[name] = jur
    m.update(OVERRIDES)
    m.update(NON_PROVIDER)
    return m


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    jmap = build_map()
    print("cdn_provider -> cdn_jurisdiction map in use:")
    for k, v in sorted(jmap.items()):
        tag = "  [OVERRIDE]" if k in OVERRIDES else ("  [non-provider -> blank]" if k in NON_PROVIDER else "")
        print(f"   {k!r:26s} -> {v!r}{tag}")
    print()

    unmapped = {}
    for cc in CCS:
        ip = os.path.join(IN_DIR, f"nedko_{cc}_202401_202605.csv")
        op = os.path.join(OUT_DIR, f"nedko_{cc}_202401_202605.csv")
        if not os.path.exists(ip):
            print(f"[skip] {cc}: not found"); continue
        tot = filled = 0
        with open(ip, newline="", encoding="utf-8") as fin, \
             open(op, "w", newline="", encoding="utf-8") as fout:
            r = csv.reader(fin); w = csv.writer(fout)
            h = next(r); w.writerow(h)
            i_prov = h.index("cdn_provider"); i_jur = h.index("cdn_jurisdiction")
            for row in r:
                tot += 1
                prov = row[i_prov]
                if prov in jmap:
                    row[i_jur] = jmap[prov]
                    if jmap[prov]:
                        filled += 1
                else:
                    row[i_jur] = ""
                    unmapped[prov] = unmapped.get(prov, 0) + 1
                w.writerow(row)
        print(f"[done] {cc.upper()}: {tot:,} rows, cdn_jurisdiction set on {filled:,} provider rows -> {op}")
    if unmapped:
        print("\nWARNING — cdn_provider values with NO mapping (left blank):")
        for k, v in unmapped.items():
            print(f"   {k!r}: {v} rows")
    else:
        print("\nAll cdn_provider values were mapped (or intentionally blanked).")


if __name__ == "__main__":
    main()
