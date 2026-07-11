# Pulse Research Fellowship — Chinese CDN & IP-Infrastructure Concentration in Southeast Asia

Data pipeline and datasets for a study measuring the **market concentration of Chinese- versus
American-jurisdiction Content Delivery Network (CDN) and IP-infrastructure providers** serving the
ten Southeast Asian (SEA) countries, and its association with China's **Digital Silk Road (DSR)**
investment.

> **Status.** Measurement is complete for all ten SEA countries across three layers (CDN, IP
> infrastructure, DSR). IP-infrastructure **provider names** and **jurisdiction** are now mapped from
> the CAIDA AS-Organizations dataset. **Important:** the `infrastructure_jurisdiction` variable is the
> *registered country of the organisation that holds the ASN* — a reproducible **proxy**, **not**
> verified controlling ownership (see *Limitations & disclosures*). The concentration metrics
> (Gini/HHI) and the panel regression are not yet in this repository.

---

## Research aim & questions

Quantify and compare the market concentration of Chinese CDN and IP-infrastructure providers across
SEA markets, relative to their American counterparts, and test its association with China's DSR
investment activity.

- **RQ1** — To what extent are Chinese CDN / IP-infrastructure providers concentrated in each SEA
  country's footprint, measured by the **Gini coefficient**?
- **RQ2** — What are the **Herfindahl–Hirschman Index (HHI)** scores for this jurisdiction-based
  concentration?
- **RQ3** — Is stronger Chinese DSR investment **associated** (not causal) with higher Chinese
  infrastructure concentration, via lagged fixed-/random-effects **panel regression**?

Countries: Brunei (BN), Cambodia (KH), Indonesia (ID), Laos (LA), Malaysia (MY), Myanmar (MM),
Philippines (PH), Singapore (SG), Thailand (TH), Vietnam (VN).

---

## Data pipeline (overview)

Everything starts from one domain frame — the Google **CrUX** top-1,000 most-visited domains per
country per month — and measures three layers. The IP-infrastructure layer's provider and
jurisdiction columns are filled from CAIDA (deterministic ASN → organisation → country).

```
                 data/crux/Crux_top_1000_202401_202605.csv   (domain frame: country × month × top-1000)
                        │
     ┌──────────────────┼───────────────────────────────────────────┐
     │                  │                                            │
     ▼                  ▼                                            ▼
 CDN layer          IP-infrastructure layer                    DSR layer (independent)
 run_nedko_fast.py  build_openintel_extended.py                build_aei_sea.py
 (per country,      (raw OpenINTEL forward-DNS → A-records      (aggregates AEI CGIT
  in-country VPN)    for the CrUX list)                         technology transactions)
     │                  │                                            │
     │                  ▼                                            │
     │        map_openintel_caida_sea.py   (as_number → ip_infrastructure_provider)
     │        map_jurisdiction_caida_sea.py (as_number → infrastructure_jurisdiction*)
     │                  │   *CAIDA REGISTERED country of the ASN holder — a proxy, NOT controlling ownership
     ▼                  ▼                                            ▼
 data/cdn_nedko/    data/ip_infrastructure_openintel/           data/dsr_aei/
 nedko_<cc>.csv     openintel_..._<cc>.csv.gz                   AEI.sea.output.csv
     │                  │                                            │
     └────────┬─────────┘                                            │
              ▼                                                      ▼
   Gini / HHI concentration (RQ1, RQ2)  ───────────►  Panel regression (RQ3): CDN_China / IP_China
                                                      on lagged CGIT projects / amount / type
```

---

## Repository structure

```
pulse/
├── README.md
├── CAIDA_jurisdiction_mapping_METHODOLOGY.md      # how infrastructure_jurisdiction was mapped + its limitation
├── .gitignore
├── scripts/
│   ├── run_nedko_fast.py             # CDN detection (Nedko logic), server-less, concurrent, resumable
│   ├── build_openintel_extended.py   # IP-infrastructure ETL from raw OpenINTEL parquet
│   ├── map_openintel_caida_sea.py    # ASN → ip_infrastructure_provider   (CAIDA AS-org, month-matched)
│   ├── map_jurisdiction_caida_sea.py # ASN → infrastructure_jurisdiction  (CAIDA registered country, month-matched)
│   └── build_aei_sea.py              # DSR investment aggregation from AEI CGIT
└── data/
    ├── crux/
    │   └── Crux_top_1000_202401_202605.csv           # domain frame: 10 countries × 29 months × 1000
    ├── cdn_nedko/
    │   └── nedko_<cc>_202401_202605.csv               # CDN provider + IP per domain (10 SEA countries)
    ├── provider_legal_names.csv                       # manually-verified CDN provider legal names + jurisdiction (27 CDN providers)
    ├── ip_infrastructure_openintel/
    │   ├── openintel_ip_infrastructure_extended_<cc>.csv.gz  # IP/ASN/provider/jurisdiction per domain-day (10 countries, gzipped)
    │   └── caida_source.txt                           # CAIDA snapshot provenance (month-matched 202503–202606)
    └── dsr_aei/
        ├── AEI.sea.output.csv                         # DSR tech investment/construction by country-year-type
        └── cgit_raw/
            ├── investment.csv                         # raw AEI CGIT investment records (source)
            ├── construction.csv                       # raw AEI CGIT construction records (source)
            └── SOURCE.txt                             # source URL + citation
```

The 10 IP-infrastructure datasets are **gzipped** (each >100 MB uncompressed, over GitHub's file
limit; ~11 MB each compressed). `gunzip` to read, or `pandas.read_csv(path)` reads `.gz` directly.

Not included (deliberately): the ~108 GB of raw OpenINTEL forward-DNS parquet, the ~58 MB of CAIDA
AS-org snapshots (re-downloadable — see `caida_source.txt`), and the `cdn-check` tool clone + venv.

---

## How the files connect (data flow)

1. **`data/crux/…`** is the shared input (`country, measurement_period, origin, rank`), built from
   Google CrUX on BigQuery.

2. **CDN layer — `run_nedko_fast.py`** reproduces the Nedko `cdn-check` detection (HTTP-header + CNAME
   signature scoring) plus a DNS `A` lookup, run once per country from an in-country vantage point.
   → `data/cdn_nedko/nedko_<cc>_202401_202605.csv`.

3. **IP-infrastructure layer — `build_openintel_extended.py`** filters the raw OpenINTEL forward-DNS
   parquet to every CrUX top-1,000 domain returning an IPv4 `A`-record (one row per record), recording
   IP, ASN and OpenINTEL geolocation. Then:
   - **`map_openintel_caida_sea.py`** fills `ip_infrastructure_provider` from the CAIDA AS-org name
     (ASN → org), using the CAIDA snapshot from each row's own month.
   - **`map_jurisdiction_caida_sea.py`** fills `infrastructure_jurisdiction` from the CAIDA org
     `country` field (ASN → org → registered country), again month-matched.
   → `data/ip_infrastructure_openintel/openintel_ip_infrastructure_extended_<cc>.csv.gz`.

4. **DSR layer — `build_aei_sea.py`** aggregates the AEI CGIT technology transactions (10 SEA
   countries, 2023–2025) to one row per country × year × investment/construction.
   → `data/dsr_aei/AEI.sea.output.csv`.

5. **Provider reference — `data/provider_legal_names.csv`** lists the 27 CDN providers (Nedko/ISOC) with
   manually-verified legal names, jurisdiction, and supporting documentation (ToS / registry / SEC /
   OpenCorporates). IP-infrastructure provider names and jurisdictions are carried in the
   `ip_infrastructure_openintel` datasets themselves (mapped from CAIDA), not duplicated here.

6. **Analysis (pending, not in repo).** Classified data feeds Gini/HHI concentration (RQ1/RQ2) and the
   lagged panel regression of Chinese CDN/IP concentration on CGIT DSR investment (RQ3), in STATA.

---

## Dataset schemas

**`data/cdn_nedko/nedko_<cc>_202401_202605.csv`**
`country, measurement_period, origin, cdn_provider, ip_address, cdn_jurisdiction, vantage_point, status`
— `cdn_jurisdiction` is blank (manual, controlling-ownership). `status` = `ok` / `unreachable`.

**`data/ip_infrastructure_openintel/openintel_ip_infrastructure_extended_<cc>.csv.gz`**
`country, measurement_period, website, website_rank, ip_infrastructure_provider,
infrastructure_jurisdiction, infrastructure_country, as_number, ip_address, source, extraction_date`
— one row per IPv4 A-record per domain per day, 2025-03 → 2026-06. Three distinct fields to keep clear:
- `ip_infrastructure_provider` — CAIDA organisation that **holds the ASN** (e.g. `Amazon.com, Inc.`).
- `infrastructure_jurisdiction` — CAIDA **registered country of that organisation** (a proxy — see below).
- `infrastructure_country` — OpenINTEL's **geolocation of the IP** (where the server sits), a *different* thing.

**`data/provider_legal_names.csv`**
`#, CDN Provider, Company Website, Documentation Checked, Actual Legal Name, Data Source, Jurisdiction, OpenCorporate Result`
— the 27 CDN providers (Nedko/ISOC) with manually-verified legal names, jurisdiction, and supporting
documentation (ToS / registry / SEC / OpenCorporates). IP-infrastructure provider names and jurisdictions
are **not** repeated here — they live in the `ip_infrastructure_openintel` datasets (mapped from CAIDA).

**`data/dsr_aei/AEI.sea.output.csv`**
`country, year, projects, amount, type` — full country × year × type grid; `amount` in US$ millions.

---

## ⚠️ Limitations & disclosures

1. **`infrastructure_jurisdiction` is a registration proxy, not controlling ownership.** It is the
   country CAIDA/RIR records for the organisation holding the ASN — **not** the ultimate parent's
   jurisdiction, and **not** the physical server location. Where a provider registers an ASN through a
   foreign subsidiary the two diverge: e.g. `Akamai International B.V. → NL`, though Akamai is
   US-controlled. This can under-count Chinese jurisdiction where a Chinese-controlled provider
   registers via Singapore/Hong Kong. It is adopted because manual controlling-ownership resolution for
   721 providers was not feasible in the fellowship window; observations concentrate in the top ~20
   providers (91.7%), for which controlling ownership can be manually verified as triangulation. Full
   detail: [`CAIDA_jurisdiction_mapping_METHODOLOGY.md`](CAIDA_jurisdiction_mapping_METHODOLOGY.md).

2. **CDN-provider websites/URLs were located via manual Google Search** (for the legal-name lookup),
   disclosed as a limitation rather than treated as a systematic source.

3. **OpenINTEL measures from a Dutch vantage point.** For anycast/GeoDNS services the A-records
   returned reflect what a Netherlands-based resolver sees, so `infrastructure_country` skews toward
   NL/EU and should not be read as "where SEA users are served from." This mainly affects the
   geolocation field; the ASN-based `infrastructure_jurisdiction` is largely robust because a provider's
   ASN is the same entity regardless of which edge IP is returned.

---

## Status

| Layer | Coverage | Status |
|---|---|---|
| CrUX domain frame | 10 SEA countries, 2024-01…2026-05 | complete |
| CDN (Nedko) | all 10 SEA countries | complete |
| IP infrastructure (OpenINTEL) | all 10 SEA countries, 2025-03…2026-06 | complete |
| IP provider mapping (CAIDA AS-org) | all 10 | complete |
| IP jurisdiction mapping (CAIDA registered country — **proxy**) | all 10 | complete (see limitations) |
| CDN provider legal names + jurisdiction | 27 CDN providers (Nedko/ISOC), manually verified | complete |
| DSR (AEI CGIT) | 10 SEA countries, 2023–2025, technology | complete |
| CDN controlling-ownership jurisdiction | — | pending (manual) |
| Gini / HHI + panel regression | — | pending |

---

## Reproducing

Scripts use **absolute paths from the author's working environment** (a `BASE` constant at the top of
each file) — adjust before running.

- **`run_nedko_fast.py`** needs `requests` + `dnspython`; reproduces the open-source Nedko `cdn-check`
  logic (<https://github.com/NedkoHristov/cdn-check>), run one country at a time from an in-country
  vantage point.
- **`build_openintel_extended.py`** needs `pyarrow` and the raw OpenINTEL forward-DNS parquet (~108 GB,
  not included), from <https://openintel.nl> (forward-DNS / top-list / CrUX).
- **`map_openintel_caida_sea.py`** and **`map_jurisdiction_caida_sea.py`** need the CAIDA
  AS-Organizations monthly snapshots (not included, ~58 MB, re-downloadable — see `caida_source.txt`).
- **`build_aei_sea.py`** needs only the standard library and the CGIT source files under
  `data/dsr_aei/cgit_raw/`.

---

## Data sources & citation

- **Google CrUX** (Chrome UX Report) — domain frame, via BigQuery.
- **OpenINTEL** — forward-DNS active measurements (<https://openintel.nl>).
- **Nedko `cdn-check`** — CDN detection logic (<https://github.com/NedkoHristov/cdn-check>).
- **CAIDA AS Organizations Dataset** — ASN → organisation → registered country, monthly snapshots
  20250301–20260601 (<https://www.caida.org/catalog/datasets/as-organizations/>).
- **AEI China Global Investment Tracker** — DSR investment. *American Enterprise Institute and Heritage
  Foundation, China Global Investment Tracker, January 2025.*
