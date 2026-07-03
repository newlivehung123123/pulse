# Pulse Research Fellowship — Chinese CDN & IP-Infrastructure Concentration in Southeast Asia

Work-in-progress data pipeline and datasets for a study measuring the **market concentration
of Chinese- versus American-jurisdiction Content Delivery Network (CDN) and IP-infrastructure
providers** serving the ten Southeast Asian (SEA) countries, and its association with China's
**Digital Silk Road (DSR)** investment.

> Status: **work in progress.** This repository holds the measurement pipeline and the raw/derived
> datasets. The provider-name and jurisdiction columns are intentionally left blank pending manual,
> auditable classification (see *Data flow* below); the concentration metrics and panel-regression
> analysis are not yet in this repository.

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
country per month — and measures three layers. Each measurement leaves a **provider** and/or
**jurisdiction** column blank, to be filled by manual classification.

```
                 data/crux/Crux_top_1000_202401_202605.csv   (domain frame: country × month × top-1000)
                        │
     ┌──────────────────┼───────────────────────────────────────────┐
     │                  │                                            │
     ▼                  ▼                                            ▼
 CDN layer          IP-infrastructure layer                    DSR layer (independent)
 run_nedko_fast.py  build_openintel_extended.py                build_aei_sea.py
 (per country,      (filters raw OpenINTEL forward-DNS         (aggregates AEI CGIT
  in-country VPN)    parquet to A-records for the CrUX list)    technology transactions)
     │                  │                                            │
     ▼                  ▼                                            ▼
 data/cdn_nedko/    data/ip_infrastructure_openintel/           data/dsr_aei/
 nedko_<cc>.csv     openintel_ip_infrastructure_extended_<cc>   AEI.sea.output.csv
     │                  │                                            │
     └────────┬─────────┘                                            │
              ▼                                                      │
   MANUAL classification (not yet in repo):                         │
   • cdn_provider → cdn_jurisdiction  (controlling-ownership operationalisation)
   • as_number → ip_infrastructure_provider (CAIDA AS-org dataset)  │
   • ip_infrastructure_provider → infrastructure_jurisdiction       │
              │                                                      │
              ▼                                                      ▼
   Gini / HHI concentration (RQ1, RQ2)  ───────────►  Panel regression (RQ3): CDN_China / IP_China
                                                      on lagged CGIT projects / amount / type
```

---

## Repository structure

```
pulse/
├── README.md
├── .gitignore
├── scripts/
│   ├── run_nedko_fast.py            # CDN detection (Nedko logic), server-less, concurrent, resumable
│   ├── build_openintel_extended.py  # IP-infrastructure ETL from raw OpenINTEL parquet
│   └── build_aei_sea.py             # DSR investment aggregation from AEI CGIT
└── data/
    ├── crux/
    │   └── Crux_top_1000_202401_202605.csv        # domain frame: 10 countries × 29 months × 1000
    ├── cdn_nedko/
    │   └── nedko_<cc>_202401_202605.csv            # CDN provider + IP per domain (10 SEA countries)
    ├── ip_infrastructure_openintel/
    │   └── openintel_ip_infrastructure_extended_<cc>.csv   # IP/ASN per domain-day (MY, SG, TH, ID)
    └── dsr_aei/
        ├── AEI.sea.output.csv                      # DSR tech investment/construction by country-year-type
        └── cgit_raw/
            ├── investment.csv                      # raw AEI CGIT investment records (source)
            ├── construction.csv                    # raw AEI CGIT construction records (source)
            └── SOURCE.txt                          # source URL + citation
```

Not included (deliberately): the ~108 GB of raw OpenINTEL forward-DNS parquet, and the `cdn-check`
tool clone + Python virtualenv (see *Reproducing*).

---

## How the files connect (data flow)

1. **`data/crux/Crux_top_1000_202401_202605.csv`** is the shared input. Columns: `country,
   measurement_period, origin, rank`. Built from Google CrUX on BigQuery (10 countries × months
   2024-01…2026-05 × 1,000 domains).

2. **CDN layer — `scripts/run_nedko_fast.py`** reads the CrUX frame (filtered per `--country`) and,
   for each domain, reproduces the Nedko `cdn-check` detection (HTTP-header + CNAME signature scoring)
   plus a DNS `A` lookup. Run once per country from an in-country vantage point (residential / VPN) to
   avoid GeoDNS bias. → `data/cdn_nedko/nedko_<cc>_202401_202605.csv`.

3. **IP-infrastructure layer — `scripts/build_openintel_extended.py`** reads the raw OpenINTEL
   forward-DNS daily parquet (not in repo) and the CrUX frame, keeps every CrUX top-1,000 domain that
   returns an IPv4 `A`-record (one row per record), and records the IP, ASN and OpenINTEL geolocation.
   → `data/ip_infrastructure_openintel/openintel_ip_infrastructure_extended_<cc>.csv`.

4. **DSR layer — `scripts/build_aei_sea.py`** reads the two raw AEI CGIT transaction files in
   `data/dsr_aei/cgit_raw/`, filters to the Technology sector, the 10 SEA countries and 2023–2025, and
   aggregates to one row per country × year × investment/construction. → `data/dsr_aei/AEI.sea.output.csv`.

5. **Manual classification (pending, not in repo).** The measurement outputs intentionally leave
   provider/jurisdiction columns blank:
   - `cdn_provider → cdn_jurisdiction` — via a documented controlling-ownership operationalisation
     (mainland-China vs Hong Kong vs USA vs other), using company registries / disclosure filings.
   - `as_number → ip_infrastructure_provider` — via the **CAIDA AS-to-Organisation** dataset.
   - `ip_infrastructure_provider → infrastructure_jurisdiction` — via the same operationalisation.

6. **Analysis (pending, not in repo).** The classified data feeds Gini/HHI concentration (RQ1/RQ2)
   and the lagged fixed-/random-effects panel regression of Chinese CDN/IP concentration on CGIT
   DSR investment (RQ3), in STATA.

---

## Dataset schemas

**`data/cdn_nedko/nedko_<cc>_202401_202605.csv`**
`country, measurement_period, origin, cdn_provider, ip_address, cdn_jurisdiction, vantage_point, status`
— `cdn_jurisdiction` is blank (manual). `status` = `ok` / `unreachable`.

**`data/ip_infrastructure_openintel/openintel_ip_infrastructure_extended_<cc>.csv`**
`country, measurement_period, website, website_rank, ip_infrastructure_provider,
infrastructure_jurisdiction, infrastructure_country, as_number, ip_address, source, extraction_date`
— `ip_infrastructure_provider` and `infrastructure_jurisdiction` are blank (manual, via CAIDA +
operationalisation). One row per IPv4 A-record per domain per day; 2025-03-17 → 2026-06-30.

**`data/dsr_aei/AEI.sea.output.csv`**
`country, year, projects, amount, type`
— full country × year × type grid; `projects`/`amount` empty where a country-year-type has no
technology deals. `amount` is US$ millions. `type` ∈ {investment, construction}.

---

## Status (work in progress)

| Layer | Coverage | Status |
|---|---|---|
| CrUX domain frame | 10 SEA countries, 2024-01…2026-05 | complete |
| CDN (Nedko) | all 10 SEA countries | complete |
| IP infrastructure (OpenINTEL) | MY, SG, TH, ID | 4 of 10 done; PH, VN, MM, KH, LA, BN pending |
| DSR (AEI CGIT) | 10 SEA countries, 2023–2025, technology | complete |
| Provider/jurisdiction classification | — | pending (manual: CAIDA + operationalisation) |
| Gini / HHI + panel regression | — | pending |

---

## Reproducing

The scripts use **absolute paths from the author's working environment** (a `BASE` constant at the
top of each file) and expect the original folder layout, not this repository layout — adjust those
paths before running.

- **`run_nedko_fast.py`** needs `requests` + `dnspython`. It reproduces the CDN-detection logic of the
  open-source Nedko `cdn-check` tool (<https://github.com/NedkoHristov/cdn-check>), which is **not**
  included here (external clone + virtualenv). Run one country at a time from an in-country vantage point.
- **`build_openintel_extended.py`** needs `pyarrow`. It requires the raw OpenINTEL forward-DNS parquet
  (**not** included, ~108 GB), downloadable from <https://openintel.nl> (forward-DNS / top-list / CrUX).
- **`build_aei_sea.py`** needs only the standard library and the CGIT source files under
  `data/dsr_aei/cgit_raw/`.

---

## Data sources & citation

- **Google CrUX** (Chrome UX Report) — domain frame, via BigQuery.
- **OpenINTEL** — forward-DNS active measurements (<https://openintel.nl>).
- **Nedko `cdn-check`** — CDN detection logic (<https://github.com/NedkoHristov/cdn-check>).
- **AEI China Global Investment Tracker** — DSR investment. *American Enterprise Institute and
  Heritage Foundation, China Global Investment Tracker, January 2025.*
- **CAIDA AS-to-Organisation dataset** — for ASN → provider mapping (manual stage).
