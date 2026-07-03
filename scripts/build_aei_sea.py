"""
Build AEI.sea.output.csv from the AEI China Global Investment Tracker (CGIT).

Source: the two transaction CSVs that power AEI's public CGIT interactive tool
(https://kristol2021live.aei.org/plzchina/infographics/worldinvestments/),
downloaded to AEI_CGIT_raw/investment.csv and AEI_CGIT_raw/construction.csv.
These are the real underlying records (2005-2025), one row per transaction, with
columns: Year, Month, Investor, Millions, Share Size, Partner/Target, Sector,
Subsector, Country, Region, BRI.

Output schema (one row per country x year x type, full grid, nothing omitted):
  country, year, projects, amount, type
    projects = number of technology transactions for that country-year-type
    amount   = summed transaction value (US$ millions) of those transactions
    type     = 'investment' or 'construction'
Country-year-type combinations with no technology projects are KEPT with
projects and amount left EMPTY (per the researcher's instruction).

Filters: Sector == 'Technology'; the 10 SE Asian countries; years 2023-2025;
both investment and construction records.
"""

import csv
import os

BASE = "/Users/newlivehung/Desktop/11. Pulse Research Fellowship/06.07.2026_Folder"
RAW = os.path.join(BASE, "AEI_CGIT_raw")
OUT = os.path.join(BASE, "AEI.sea.output.csv")

SEA = ["Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia",
       "Myanmar", "Philippines", "Singapore", "Thailand", "Vietnam"]
YEARS = ["2023", "2024", "2025"]
TYPES = [("investment", "investment.csv"), ("construction", "construction.csv")]


def parse_millions(s):
    """' $1,740 ' -> 1740.0 ; '' -> None"""
    s = (s or "").replace("$", "").replace(",", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# agg[(country, year, type)] = [project_count, amount_sum, any_amount_seen]
agg = {}
for tname, fname in TYPES:
    with open(os.path.join(RAW, fname), newline="", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            if row["Sector"].strip() != "Technology":
                continue
            country = row["Country"].strip()
            year = row["Year"].strip()
            if country not in SEA or year not in YEARS:
                continue
            key = (country, year, tname)
            rec = agg.setdefault(key, [0, 0.0, False])
            rec[0] += 1
            amt = parse_millions(row["Millions"])
            if amt is not None:
                rec[1] += amt
                rec[2] = True

# Full grid: 10 countries x 3 years x 2 types = 60 rows, ordered.
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["country", "year", "projects", "amount", "type"])
    for country in SEA:
        for year in YEARS:
            for tname, _ in TYPES:
                rec = agg.get((country, year, tname))
                if rec is None:
                    projects, amount = "", ""            # no tech projects -> empty
                else:
                    projects = rec[0]
                    amount = int(rec[1]) if rec[2] else ""  # sum of disclosed amounts
                w.writerow([country, year, projects, amount, tname])

print(f"wrote {OUT}")
