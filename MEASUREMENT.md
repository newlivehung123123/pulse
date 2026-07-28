# Measurement Specification

How each metric and each regression variable is actually computed. This document is the bridge
between [`METHODOLOGY_WORKFLOW.md`](METHODOLOGY_WORKFLOW.md) (what was done) and the scripts in
[`scripts/`](scripts/) (how it was done in code).

---

## Part 1 — Concentration metrics (RQ1, RQ2)

Produced by [`scripts/analysis_concentration.py`](scripts/analysis_concentration.py) →
[`outputs/rq1_rq2_concentration/`](outputs/rq1_rq2_concentration/).

### Common set-up

- The unit of analysis is a **(country × month)** cell. The metric is computed for each cell, plotted
  as a time series (one line per country), and summarised in a yearly cross-tabulation.
- **Gini coefficient** — the standard Gini of the market-share distribution. For shares sorted
  ascending, `G = 2·Σ(i·xᵢ)/(n·Σx) − (n+1)/n`. It runs from 0, where every provider holds an equal
  share, towards 1, where a single provider holds everything. With a finite number of providers *n*
  the attainable maximum is (n−1)/n rather than exactly 1.
- **HHI** — `Σ(sᵢ²) × 10,000`, where `sᵢ` is each unit's share of the market. The scale runs 0–10,000,
  where 10,000 is a pure monopoly.
- Table cells report the **mean monthly share (%)** within each country-year, averaged over *all*
  months in that year. A provider or jurisdiction absent in a given month contributes 0 to that
  month, so each year's shares sum to approximately 100%.
- "By provider" uses only providers present in that month (share > 0). "By jurisdiction" uses a
  **fixed three-category market {China, USA, Other}**, retaining zeros for absent categories so that
  the three series remain comparable across countries and months.

### Dataset 1 — Nedko (CDN)

- **Market-share unit.** One top-1,000 domain is one row per month, so a provider's weight is its
  count of **distinct domains served**.
- **Base.** Served sites only: rows whose provider is `unknown` or `None detected` are excluded,
  since they record that no CDN was detected rather than that a provider served the site.
- **By provider.** Weight = number of domains served by each CDN provider in that country-month.
- **By jurisdiction.** Each served domain is assigned to China, USA or Other through
  `cdn_jurisdiction`; the weight is the domain count in each of the three categories.

### Dataset 2 — ISOC (CDN)

- **Market-share unit.** ISOC does not list individual websites; it reports a **count of websites**
  served by each CDN in each country on each crawl date. That count is therefore the only available
  measure of a provider's size, and a provider's weight is `local_websites + external_websites`.
  `local_websites` counts top-list sites hosted inside the country, `external_websites` those hosted
  abroad; both are sites in the country's top list served by that CDN, so the total footprint is
  their sum.
- **Repeated rows.** The raw file repeats the same website count once per observing vantage point
  (`test_asn`), so summing rows would multiply the true figure several-fold. One record is kept per
  (country, month, CDN). Where a month contains more than one crawl date, the **latest date** in that
  month is taken as the month's reading, which also aligns ISOC to the one-value-per-month structure
  used for the other two datasets.
- **Base.** Served sites only: `summary` and `other` rows are excluded.
- **By provider.** Weight = website count per `host_cdn`.
- **By jurisdiction.** Each `host_cdn` is assigned to China, USA or Other, and weights are summed
  within each category.

### Dataset 3 — OpenINTEL (IP infrastructure)

- **Market-share unit.** Distinct **(website, provider)** pairs per country-month. The raw data
  repeats each website across roughly 31 measurement days and across every IP address returned for
  it, so a single website can generate well over a thousand rows in one month. Counting rows would
  measure how many IP addresses and crawl days happened to be recorded rather than how many websites
  a provider serves. Collapsing to distinct (website, provider) pairs removes that repetition. A
  website served by more than one provider counts once **for each** provider it uses, since it
  genuinely draws on both networks.
- **Base.** Served sites only: rows whose provider could not be identified are excluded (see
  *Unidentified providers* below).
- **By provider.** Weight = number of distinct websites served by each `ip_infrastructure_provider`.
  Because 721 distinct providers appear, the cross-tabulations show the top 12 providers plus an
  "Other" aggregate; the Gini and HHI figures themselves use the full distribution.
- **By jurisdiction.** Each provider is assigned to China, USA or Other through
  `infrastructure_jurisdiction`; the weight is the count of distinct websites per category.

### Unidentified providers

Naming a provider requires two lookups: IP → AS number, then AS number → organisation in CAIDA.
Where either step fails the pipeline writes a placeholder beginning with `ASN ` rather than
inventing a name. Two cases occur in the data: `ASN unparseable`, where the row carried no usable AS
number, and `ASN <n> not in CAIDA <month>`, where the network is known but has no organisation record
in that month's snapshot. These rows are excluded from all market-share denominators, because a
market share can only be attributed to a named provider.

---

## Part 2 — Panel regression (RQ3)

Produced by [`scripts/build_rq3_regression.py`](scripts/build_rq3_regression.py) (Models 1a and 2) and
[`scripts/build_rq3_isoc.py`](scripts/build_rq3_isoc.py) (Model 1b) →
[`outputs/rq3_panel_regression/`](outputs/rq3_panel_regression/).

### Specification

```
Model 1a  CDN_China_it = β0 + β1·CGIT_projects_i,t-1 + β2·CGIT_amount_i,t-1 + β3·CGIT_type_i,t-1 + αi + εit   (Nedko)
Model 1b  CDN_China_it = β0 + β1·CGIT_projects_i,t-1 + β2·CGIT_amount_i,t-1 + β3·CGIT_type_i,t-1 + αi + εit   (ISOC)
Model 2   IP_China_it  = β0 + β1·CGIT_projects_i,t-1 + β2·CGIT_amount_i,t-1 + β3·CGIT_type_i,t-1 + αi + εit   (OpenINTEL)
```

Each model is estimated by **fixed effects (within)** and **random effects** side by side, with
**cluster-robust standard errors by country**, and a **Hausman test** to choose between them. All
three explanatory variables are lagged one year.

Fixed effects use only variation within a country over time, and so absorb every stable difference
between countries, including unobserved ones. Random effects additionally use variation between
countries and are more efficient, but are consistent only if the country effects are uncorrelated
with the predictors. The Hausman test examines that assumption: a p-value below 0.05 rejects it and
indicates fixed effects should be preferred; a p-value at or above 0.05 leaves random effects
admissible.

### Dependent variables

- **`CDN_China` (continuous, per cent).** The share of served sites carried by a Chinese-jurisdiction
  CDN, per country-year. Within each month the share is (sites on a Chinese-jurisdiction CDN ÷ total
  served sites) × 100, and the year's value is the mean of its monthly shares. Model 1a takes this
  from the **Nedko** dataset, using distinct domains; Model 1b takes it from the **ISOC** dataset,
  using the website counts described in Part 1.
- **`IP_China` (continuous, per cent).** The share of distinct served websites resolving to a
  Chinese-jurisdiction IP-infrastructure provider, per country-year, computed monthly and averaged
  over the year in the same way.

Both dependent variables are **market shares**, not the Gini or HHI figures reported for RQ1 and RQ2.
RQ1 and RQ2 measure how concentrated a market is overall; RQ3's outcome is specifically the size of
the Chinese share of it.

### Explanatory variables

All three are drawn from the AEI China Global Investment Tracker, technology sector, aggregated to
country-year and lagged one year.

- **`CGIT_projects` (continuous, count).** Number of Chinese technology projects recorded in that
  country-year.
- **`CGIT_amount` (continuous, US$ millions).** Total recorded value of those projects.
- **`CGIT_type` (binary).** Coded **1** where the country-year contains at least one *construction*
  transaction, and **0** otherwise.

### How `CGIT_type` is grounded

CGIT distributes its data as two separate files, `investment.csv` and `construction.csv`, and the
`type` field records which file a transaction came from. Across the Southeast Asian technology
extract the field takes exactly two values, `investment` and `construction`, with no blanks. The
distinction between them is visible in the source files themselves: `investment` records carry a
`Share Size` field giving an ownership percentage (populated on 1,421 of 2,473 rows, e.g. 100%, 51%,
70%) alongside named acquisition targets, whereas `construction` records leave that field empty on
2,333 of 2,431 rows and name engineering contractors as the counterparty. Investment transactions
therefore correspond to China acquiring an ownership stake, and construction transactions to Chinese
firms being contracted to build a project, generally without taking one.

Two qualifications are recorded rather than smoothed over. First, AEI does not publish these
category definitions on its public site, so the above is inferred from the structure of the
distributed files rather than quoted from a codebook. Second, roughly four per cent of construction
records do carry an ownership percentage, so "no ownership stake" describes the general case and not
every transaction.

Aggregating to country-year also means **`CGIT_type = 0` covers two distinct situations**: a
country-year with investment activity but no construction, and a country-year with no recorded
Chinese technology activity at all. Only three country-years in the panel contain any construction
transaction (Cambodia 2023, Malaysia 2023, Malaysia 2024), and two of those contain an investment
transaction as well, so `1` should be read as "at least one construction contract was present"
rather than as "a construction rather than an investment country-year". The panel is too short to
support an additional control separating the two kinds of zero.

### Inference with ten clusters

Cluster-robust standard errors are unreliable when the number of clusters is small, and this panel
has ten countries. Any coefficient significant at p < 0.05 under the naive cluster-robust standard
errors is therefore re-tested by **wild cluster bootstrap** (1,999 Rademacher draws, restricted null,
clustered by country), which is the standard remedy below roughly forty clusters, and by
**leave-one-country-out refits**, which reveal whether a result depends on a single country. Both
procedures are implemented in [`scripts/diagnose_rq3.py`](scripts/diagnose_rq3.py), which prints its
results to the console rather than writing an output file.

Two coefficients required this treatment, and neither survived it.

| Coefficient | Naive cluster-robust | Wild cluster bootstrap | Leave-one-out |
|---|---|---|---|
| `CGIT_amount`, Model 1a (FE −0.0002) | p = 0.0010 | **p = 0.3220** | drop TH → p = 0.8292; all other drops p ≤ 0.005 |
| `CGIT_type`, Model 2 (FE −3.6681) | p < 0.0001 | **p = 0.1755** | drop MY → no identifying variation remains; drop ID → coef −24.91 |

Model 2's `CGIT_type` is identified by exactly **one** country-year in the lagged panel (Malaysia
2025), which is why removing Malaysia leaves nothing to estimate. Both coefficients should be read as
few-cluster standard-error artefacts rather than as evidence of an association.
