# Pulse Research Fellowship — Chinese CDN & IP-Infrastructure Concentration in Southeast Asia

Data, pipeline and empirical outputs for a six-month research study measuring the **market
concentration of Chinese- (relative to American-) jurisdiction Content Delivery Network (CDN) and
IP-infrastructure providers** serving the 10 Southeast Asian (SEA) countries, and its association
with China's **Digital Silk Road (DSR)** investment.

> **Status — complete.** Measurement, jurisdiction mapping, concentration analysis (Gini/HHI) and
> panel regression analysis are all finished and deposited in this repository. The full outputs of
> this project encompass the **(1) methodology** and **(2) empirical materials**, which are publicly
> accessible in this repository, and the **(3) research paper**, which is currently work in progress.

Author and primary contributor: **Jason Hung**  
Mentor: **Cecilia Testart**  
Advisors: **Amreesh Phokeer** & **Hanna Kreitem**

---

## Research aim & questions

Quantify and analyse the market concentration of Chinese CDN and IP-infrastructure providers in SEA,
especially relative to their American counterparts, and study any association with China's DSR
activity.

- **RQ1** — To what extent are Chinese Internet infrastructure providers (CDN and IP infrastructure)
  concentrated in SEA markets, as measured by the **Gini coefficient**?
- **RQ2** — What are the **Herfindahl–Hirschman Index (HHI)** scores for Internet infrastructure
  market concentration in SEA?
- **RQ3** — Are stronger DSR ties with China **associated** (not causal) with higher degrees of
  Internet infrastructure dependency in SEA?

Countries: Brunei (BN), Cambodia (KH), Indonesia (ID), Laos (LA), Malaysia (MY), Myanmar (MM),
Philippines (PH), Singapore (SG), Thailand (TH), Vietnam (VN).

**Documentation.** [`METHODOLOGY_WORKFLOW.md`](METHODOLOGY_WORKFLOW.md) sets out the workflow from aim
to outputs. [`MEASUREMENT.md`](MEASUREMENT.md) specifies how every metric and regression variable is
computed. [`CAIDA_jurisdiction_mapping_METHODOLOGY.md`](CAIDA_jurisdiction_mapping_METHODOLOGY.md)
documents the ASN-to-jurisdiction mapping and its limitation.

---

## Data pipeline

Everything starts from one domain frame — the Google **CrUX** top-1,000 most-visited domains per
country per month — and measures three layers, which then feed the concentration metrics and the
panel regression.

```
              data/crux/Crux_top_1000_202401_202605.csv   (domain frame: country × month × top-1000)
                     │
   ┌─────────────────┼──────────────────────────┬─────────────────────────────┐
   │                 │                          │                             │
   ▼                 ▼                          ▼                             ▼
CDN (Nedko)      CDN (ISOC)            IP infrastructure              DSR (independent)
run_nedko_fast   build_isoc_sea.py     build_openintel_extended.py    build_aei_sea.py
   │                 │                          │                             │
   ▼                 │                          ▼                             │
map_nedko_       (jurisdiction from     map_openintel_caida_sea.py            │
jurisdiction.py   provider_legal_       map_jurisdiction_caida_sea.py         │
   │              names.csv)                    │                             │
   │                 │                   ASN → org → registered country*      │
   ▼                 ▼                          ▼                             ▼
data/cdn_nedko/  data/cdn_isoc/    data/ip_infrastructure_openintel/   data/dsr_aei/
   │                 │                          │                             │
   └────────┬────────┴──────────────────────────┘                             │
            ▼                                                                 │
   analysis_concentration.py                                                  │
   Gini / HHI, by provider and by jurisdiction  (RQ1, RQ2)                     │
            │                                                                 │
            └──────────────────────┬──────────────────────────────────────────┘
                                   ▼
                    build_rq3_regression.py  (Models 1a, 2)
                    build_rq3_isoc.py        (Model 1b)
                    diagnose_rq3.py          (small-cluster robustness)
                    CDN_China / IP_China on lagged CGIT  (RQ3)

  * CAIDA REGISTERED country of the ASN holder — a proxy, NOT verified controlling ownership
```

---

## Repository structure

```
pulse/
├── README.md
├── METHODOLOGY_WORKFLOW.md                        # aim → objectives → measurement → outputs
├── MEASUREMENT.md                                 # how each metric and variable is computed
├── CAIDA_jurisdiction_mapping_METHODOLOGY.md      # ASN → jurisdiction mapping + its limitation
├── scripts/
│   ├── run_nedko_fast.py             # CDN detection (Nedko logic), concurrent, resumable
│   ├── build_isoc_sea.py             # ISOC raw crawl → 10-country SEA dataset + jurisdiction
│   ├── map_nedko_jurisdiction.py     # Nedko cdn_provider → cdn_jurisdiction (provider_legal_names.csv)
│   ├── build_openintel_extended.py   # IP-infrastructure ETL from raw OpenINTEL parquet
│   ├── map_openintel_caida_sea.py    # ASN → ip_infrastructure_provider   (CAIDA AS-org, month-matched)
│   ├── map_jurisdiction_caida_sea.py # ASN → infrastructure_jurisdiction  (CAIDA registered country)
│   ├── build_aei_sea.py              # DSR aggregation from AEI CGIT
│   ├── analysis_concentration.py     # Gini + HHI, by provider and jurisdiction (RQ1, RQ2)
│   ├── build_rq3_regression.py       # panel regression Models 1a & 2 (RQ3)
│   ├── build_rq3_isoc.py             # panel regression Model 1b, ISOC CDN source (RQ3)
│   └── diagnose_rq3.py               # wild cluster bootstrap + leave-one-country-out
├── data/
│   ├── crux/Crux_top_1000_202401_202605.csv        # domain frame: 10 countries × 29 months × 1000
│   ├── cdn_nedko/nedko_<cc>_202401_202605.csv      # CDN provider, IP, jurisdiction per domain
│   ├── cdn_isoc/
│   │   ├── lccrawresults_raw.csv                   # ISOC crawl as obtained (all countries)
│   │   └── lccrawresults_full_formatted_sea.csv    # 10 SEA countries, harmonised + jurisdiction
│   ├── ip_infrastructure_openintel/
│   │   ├── openintel_ip_infrastructure_extended_<cc>.csv.gz   # per domain-day (gzipped)
│   │   └── caida_source.txt
│   ├── caida_as_org/                               # 16 monthly CAIDA snapshots 202503–202606
│   ├── dsr_aei/
│   │   ├── AEI.sea.output.csv                      # DSR tech activity by country-year-type
│   │   └── cgit_raw/{investment,construction}.csv  # raw AEI CGIT records + SOURCE.txt
│   └── provider_legal_names.csv                    # 27 CDN providers, verified legal names
└── outputs/
    ├── rq1_rq2_concentration/                      # 12 figures + cross-tab tables (docx)
    └── rq3_panel_regression/                       # regression tables (docx)
```

The 10 IP-infrastructure datasets are **gzipped** (each >100 MB uncompressed, over GitHub's file
limit; ~12 MB each compressed). `gunzip` to read, or `pandas.read_csv(path)` reads `.gz` directly.

Not included: the ~108 GB of raw OpenINTEL forward-DNS parquet (available from openintel.nl), and the
`cdn-check` tool clone and virtualenv. The CAIDA snapshots **are** included, so the jurisdiction
mapping can be reproduced against the exact inputs used rather than against whatever CAIDA currently
publishes.

---

## Dataset schemas

**`data/cdn_nedko/nedko_<cc>_202401_202605.csv`**
`country, measurement_period, origin, cdn_provider, ip_address, cdn_jurisdiction, vantage_point, status`
— one row per domain per month. `cdn_jurisdiction` is mapped from `provider_legal_names.csv`
(manual, controlling-entity based). `status` = `ok` / `unreachable`.

**`data/cdn_isoc/lccrawresults_full_formatted_sea.csv`**
`country, measurement_period, website, website_rank, cdn_provider, cdn_jurisdiction, as_number,
ip_address, source, extraction_date`
— the ISOC crawl restricted to the 10 SEA countries and harmonised to the shared schema, with
`cdn_jurisdiction` mapped from the same `provider_legal_names.csv`. The raw file it derives from is
kept alongside it as `lccrawresults_raw.csv`; note that the raw file reports **website counts**
(`local_websites`, `external_websites`) rather than individual websites, which is why the ISOC
market-share unit differs from the other two datasets — see [`MEASUREMENT.md`](MEASUREMENT.md).

**`data/ip_infrastructure_openintel/openintel_ip_infrastructure_extended_<cc>.csv.gz`**
`country, measurement_period, website, website_rank, ip_infrastructure_provider,
infrastructure_jurisdiction, infrastructure_country, as_number, ip_address, source, extraction_date`
— one row per IPv4 A-record per domain per day, 2025-03 → 2026-06. Three fields are distinct and
should not be conflated:
- `ip_infrastructure_provider` — the CAIDA organisation that **holds the ASN** (e.g. `Amazon.com, Inc.`).
- `infrastructure_jurisdiction` — the CAIDA **registered country of that organisation** (a proxy — see below).
- `infrastructure_country` — OpenINTEL's **geolocation of the IP**, i.e. where the server sits, which
  is a different thing and is not CAIDA-derived.

**`data/provider_legal_names.csv`**
`#, CDN Provider, Company Website, Documentation Checked, Actual Legal Name, Data Source,
Jurisdiction, OpenCorporate Result`
— the 27 CDN providers appearing in the Nedko and ISOC datasets, with manually verified legal names
and jurisdictions. IP-infrastructure providers are **not** listed here; their names and jurisdictions
are carried in the OpenINTEL datasets themselves, mapped from CAIDA.

**`data/dsr_aei/AEI.sea.output.csv`**
`country, year, projects, amount, type` — full country × year × type grid; `amount` in US$ millions.

---

## Empirical outputs

**RQ1 & RQ2 — concentration.** [`outputs/rq1_rq2_concentration/`](outputs/rq1_rq2_concentration/)
holds 12 figures — Gini and HHI, each by provider and by jurisdiction, for each of the three data
sources — with one line per country over time, plus a plain cross-tabulation of market share by
provider/jurisdiction × year × country for each figure. `concentration_analysis.docx` collects all
twelve figures and tables in one document.

**RQ3 — panel regression.** `outputs/rq3_panel_regression/rq3_panel_regression_tables.docx` holds all
three models — 1a (Nedko CDN), 1b (ISOC CDN) and 2 (OpenINTEL IP infrastructure) — each reported with
fixed-effects and random-effects estimates side by side, cluster-robust standard errors by country,
the Hausman test and the model fit statistics. The small-cluster diagnostics are produced separately
by [`scripts/diagnose_rq3.py`](scripts/diagnose_rq3.py), which prints to the console rather than
writing a file; its results are reported below and in [`MEASUREMENT.md`](MEASUREMENT.md).

**What RQ3 found.** The panels are short — Models 1a and 1b have T=3 (N=30), Model 2 has T=2 (N=20) —
and only six of the ten countries record any DSR technology activity at all (Thailand, Malaysia,
Indonesia, Vietnam, Cambodia, Singapore; Brunei, Laos, Myanmar and the Philippines record none), so
the estimates are exploratory. Two coefficients reached significance under naive cluster-robust
standard errors: `CGIT_amount` in Model 1a (FE −0.0002, p < 0.001) and `CGIT_type` in Model 2 (FE
−3.67, p < 0.001). Neither survived the wild cluster bootstrap — p = 0.322 and p = 0.176 respectively
— and each rested on a single country. Dropping Thailand moved the first from p = 0.001 to p = 0.829;
`CGIT_type` in Model 2 is identified by exactly one country-year (Malaysia 2025, lagged), so dropping
Malaysia leaves no identifying variation at all. Model 1b, which repeats Model 1a on the ISOC CDN
data, returned no coefficient significant at p < 0.05.

**The honest reading is a null result.** Across all three data sources there is no robust association
between lagged DSR activity and Chinese CDN or IP-infrastructure market share; the two apparently
significant coefficients are small-cluster artefacts, not findings. The Hausman tests do not reject
random effects in any model (p = 0.822, 0.994, 1.000), and the FE and RE estimates agree closely
throughout, so the choice of estimator is not what drives the result.

---

## ⚠️ Limitations & disclosures

1. **`infrastructure_jurisdiction` is a registration proxy, not controlling ownership.** It is the
   country CAIDA and the regional Internet registries record for the organisation holding the ASN —
   not the ultimate parent's jurisdiction, and not the physical server location. Where a provider
   registers an ASN through a foreign subsidiary the two diverge: `Akamai International B.V. → NL`,
   though Akamai is US-controlled. This can under-count Chinese jurisdiction where a
   Chinese-controlled provider registers via Singapore or Hong Kong. It was adopted because manual
   controlling-ownership resolution for 721 providers was not feasible within the fellowship window;
   observations concentrate in the top ~20 providers (91.7%), for which controlling ownership can be
   verified manually as triangulation. Full detail:
   [`CAIDA_jurisdiction_mapping_METHODOLOGY.md`](CAIDA_jurisdiction_mapping_METHODOLOGY.md).

2. **CDN-provider websites were located via manual Google Search** as the entry point for the
   legal-name lookup. This is disclosed as a limitation rather than presented as a systematic source.

3. **OpenINTEL measures from a Dutch vantage point.** For anycast and GeoDNS services the A-records
   returned reflect what a Netherlands-based resolver sees, so `infrastructure_country` skews towards
   NL/EU and should not be read as "where SEA users are served from". This mainly affects the
   geolocation field; the ASN-based `infrastructure_jurisdiction` is largely robust, because a
   provider's ASN identifies the same entity regardless of which edge IP is returned.

4. **AEI does not publish its category definitions.** The distinction between CGIT `investment` and
   `construction` transactions is inferred from the structure of the distributed source files (the
   presence or absence of an ownership-percentage field), not quoted from a published codebook. See
   [`MEASUREMENT.md`](MEASUREMENT.md).

5. **RQ3 is underpowered.** Ten countries, T=2–3, and three construction country-years in total. The
   regressions are reported for transparency, with small-cluster diagnostics attached; they should
   not be read as establishing or excluding an effect.

---

## Status

| Layer | Coverage | Status |
|---|---|---|
| CrUX domain frame | 10 SEA countries, 2024-01…2026-05 | complete |
| CDN (Nedko) | 10 countries, 2024-01…2026-05 | complete |
| CDN (ISOC) | 10 countries, mid-2024…2026-01 | complete |
| IP infrastructure (OpenINTEL) | 10 countries, 2025-03…2026-06 | complete |
| IP provider + jurisdiction mapping (CAIDA) | all 10, month-matched | complete (proxy — see limitations) |
| CDN provider legal names + jurisdiction | 27 providers, manually verified | complete |
| DSR (AEI CGIT) | 10 countries, 2023–2025, technology | complete |
| Gini / HHI concentration (RQ1, RQ2) | 3 sources × 2 metrics × 2 dimensions | complete |
| Panel regression (RQ3) | Models 1, 1b, 2 + robustness | complete (null; underpowered) |
| Research paper | — | work in progress |

---

## Reproducing

Scripts use **absolute paths from the author's working environment** (a `BASE` constant at the top of
each file) — adjust before running.

| Script | Requires |
|---|---|
| `run_nedko_fast.py` | `requests`, `dnspython`; run per country from an in-country vantage point |
| `build_openintel_extended.py` | `pyarrow` and the raw OpenINTEL parquet (~108 GB, not included) |
| `map_openintel_caida_sea.py`, `map_jurisdiction_caida_sea.py` | `data/caida_as_org/` (included) |
| `build_isoc_sea.py`, `map_nedko_jurisdiction.py`, `build_aei_sea.py` | standard library only |
| `analysis_concentration.py` | `matplotlib`, `python-docx` |
| `build_rq3_regression.py`, `build_rq3_isoc.py`, `diagnose_rq3.py` | `linearmodels`, `pandas`, `numpy`, `scipy`, `python-docx` |

---

## Data sources & citation

- **Google CrUX** (Chrome UX Report) — domain frame, via BigQuery.
- **OpenINTEL** — forward-DNS active measurements (<https://openintel.nl>).
- **Nedko `cdn-check`** — CDN detection logic (<https://github.com/NedkoHristov/cdn-check>).
- **Internet Society (ISOC) Pulse** — country CDN crawl results.
- **CAIDA AS Organizations Dataset** — ASN → organisation → registered country, monthly snapshots
  20250301–20260601 (<https://www.caida.org/catalog/datasets/as-organizations/>).
- **AEI China Global Investment Tracker** — DSR activity. *American Enterprise Institute and Heritage
  Foundation, China Global Investment Tracker, January 2025.*
