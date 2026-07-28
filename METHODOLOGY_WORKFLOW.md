# Research Methodology Workflow

The complete methodological workflow for this study, from research aim through to empirical
outputs. This is the reference document for how every variable was constructed and every
measurement was carried out.

---

## Research aim

Quantify and analyse the market concentration of Chinese CDN and IP infrastructure providers in
Southeast Asia, especially relative to that of the American counterparts.

---

## Research objectives

- **Objective 1** — Map and identify the jurisdictional representation of the corresponding Internet
  service providers.
- **Objective 2** — Quantify and measure the Gini Coefficient and HHI to calculate the severity of
  market concentration (by service provider and by jurisdiction) in Southeast Asian markets.
- **Objective 3** — Study any association between the bilateral DSR activity levels and Chinese
  Internet infrastructure market concentration in Southeast Asia.

---

## Research questions

- **RQ1 — Gini Coefficient.** To what extent are Chinese Internet infrastructure providers (CDN and
  IP infrastructure) concentrated in Southeast Asian markets, as measured by the Gini Coefficient?
- **RQ2 — HHI.** What are the HHI scores for Internet infrastructure market concentration in
  Southeast Asia?
- **RQ3 — Digital Silk Road (DSR) Association.** Are stronger DSR ties with China associated with
  higher degrees of Internet infrastructure dependency in Southeast Asia?

---

## Data collection — three datasets

- **Dataset 1 — CDN (ISOC).** Top-1,000 domains per country from Google CrUX, with censored sites
  removed via CitizenLab. CDN providers detected from local residential proxy vantage points via
  WHOIS, DNS CNAME lookup, and HTTP response headers. Covers mid-2024 to January 2026.
- **Dataset 2 — CDN (Nedko).** Top-1,000 domains in all 10 Southeast Asian countries retrieved from
  Google CrUX via BigQuery. CDN providers detected via open-source Nedko CDN Checker. Covers January
  2024 to May 2026.
- **Dataset 3 — IP Infrastructure (OpenINTEL).** OpenINTEL forward-DNS measurements of CrUX top lists
  for all 10 Southeast Asian countries. Yields IP address and ASN per domain. Covers March 2025 to
  June 2026.

---

## Operationalisation & measurement of CDN providers from ISOC & Nedko datasets

- **Stage 1 — Provider Inventory.** All distinct CDN provider labels extracted from both datasets and
  pooled into a single reference table (with a total of 27 providers: 11 Nedko-only, 10 ISOC-only, 6
  in both). Non-provider values (`unknown`, `None detected`, `other`) are excluded as they denote no
  detected CDN.
- **Stage 2 — Legal Name.** Official company website searched manually via Google Search; corporate
  documentation (e.g., terms of service, legal notice, contact us) manually reviewed to record the
  actual legal name of the operating entity.
- **Stage 3 — Parent Company.** Where the documentation states the entity is a subsidiary of a named
  parent, the parent company's legal name is taken and recorded, to ensure that the corresponding
  jurisdiction identified shows the controlling entity but not the local operating entity.
- **Stage 4 — Registry Verification.** Each legal name searched in OpenCorporates; the result URL is
  recorded for audit. The (1) jurisdiction of incorporation and (2) registered address of each legal
  name searched/found on OpenCorporates match one another for triangulation/cross-validation.

Result: [`data/provider_legal_names.csv`](data/provider_legal_names.csv).

---

## Operationalisation & measurement of IP infrastructure providers from OpenINTEL datasets

- **Stage 1 — ASN Retrieval.** OpenINTEL forward-DNS measurements yield the IP address and ASN
  serving each domain. The ASN helps identify the network operator.
- **Stage 2 — CAIDA for Mapping.** Mapping uses the CAIDA AS-Organisations dataset, applied
  longitudinally (on a monthly basis). Every row of the OpenINTEL datasets is matched to the CAIDA
  datasets of the same measurement month (CAIDA datasets featuring monthly snapshots from 202503 to
  202606 are downloaded for mapping).
- **Stage 3 — Provider Name.** Each ASN from OpenINTEL datasets is matched to the organisation that
  registered it from the CAIDA datasets, and that organisation names are recorded as the providers
  serving the domain. The organisation names (covering 721 different providers) are read
  programmatically from the CAIDA records.
- **Stage 4 — Jurisdiction.** The country recorded for that same organisation is taken as its
  jurisdiction, that is, the country in which the organisation registered the ASN with its regional
  Internet registry.

Full detail and the limitation of this approach:
[`CAIDA_jurisdiction_mapping_METHODOLOGY.md`](CAIDA_jurisdiction_mapping_METHODOLOGY.md).

---

## Statistical analysis

- **M1 — Gini Coefficient.** (1) By provider and (2) by jurisdiction. Measures inequality of market
  shares. (Answers RQ1.)
- **M2 — HHI Scores.** (1) By provider and (2) by jurisdiction. Measures severity of concentration
  (sum of squared market shares). (Answers RQ2.)
- **M3 — Linear Panel Regression.** Two models with lagged explanatory variables. Model
  specifications — dependent variables: `CDN_China` and `IP_China` (from Datasets 1–3). Explanatory
  variables (all lagged *t*−1): `CGIT_projects`, `CGIT_amount`, `CGIT_type` (from AEI China Global
  Investment Tracker, technology sector, 2023–2025). (Answers RQ3.)

The measurement detail behind M1–M3 — the market-share unit for each dataset, and how each
regression variable is coded — is set out in [`MEASUREMENT.md`](MEASUREMENT.md).

---

## Empirical outputs

- **Graphs and tables** visualising the Gini Coefficients and HHI scores longitudinally (by service
  provider and by jurisdiction) — answers RQ1 and RQ2.
  → [`outputs/rq1_rq2_concentration/`](outputs/rq1_rq2_concentration/)
- **Panel regression models** displayed in tables — answers RQ3.
  → [`outputs/rq3_panel_regression/`](outputs/rq3_panel_regression/)
