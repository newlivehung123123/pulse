# IP-infrastructure jurisdiction mapping — methodology & limitations (CAIDA)

**Applies to:** `OpenINTEL_sea_output_caida_mapped/openintel_ip_infrastructure_extended_<cc>.csv`
(10 SEA countries: BN, ID, KH, LA, MM, MY, PH, SG, TH, VN), column
`infrastructure_jurisdiction`.

## What was done

Each observation's `infrastructure_jurisdiction` was assigned from the **CAIDA AS-Organizations
dataset** by a deterministic, auditable mapping:

```
as_number  →  (CAIDA AS record)  org_id  →  (CAIDA org record)  country
```

The mapping is **longitudinal**: every row is mapped with the CAIDA snapshot from the
**same month** as the row's `measurement_period` (monthly snapshots 202503–202606, stored in
`CAIDA_as_org/`, one per OpenINTEL measurement month). No value is inferred, guessed, or taken
from any language-model knowledge; every value is the literal `country` field CAIDA publishes
for the organisation that holds the ASN (source: RIR whois records — ARIN/RIPE/APNIC/LACNIC/AFRINIC).
Script: `map_jurisdiction_caida_sea.py`.

Rows where OpenINTEL returned no ASN (`as_number = '--'`) or whose ASN is absent from the CAIDA
snapshot are left **blank** (missing), never guessed.

## ⚠️ Limitation that MUST be disclosed in the paper

**`infrastructure_jurisdiction` here is the RIR-registered country of the ASN holder, NOT the
provider's controlling ownership.** These usually coincide (e.g. Cloudflare → US, Alibaba → CN,
Tencent → CN), but they diverge whenever a provider registers an ASN through a foreign subsidiary.

Worked example, taken directly from the CAIDA data:
- `AS20940` is held by **`Akamai International B.V.` → country `NL`**, even though Akamai is a
  US-controlled company. The registered country (NL, its Dutch subsidiary) is what CAIDA records.

**Direction of the resulting bias for a China-vs-US concentration measure:**
- It can **under-count Chinese jurisdiction** where a Chinese-controlled provider registers an ASN
  through a Singapore / Hong Kong / other non-mainland entity (would read SG/HK, not CN).
- It likewise displaces US firms' regional infrastructure onto subsidiary countries (e.g. NL, IE).

This is a registration-based proxy, adopted because manually establishing controlling ownership
for **721 distinct providers** (legal-name lookup + entity resolution) is not achievable within the
fellowship timeframe. The proxy is transparent and reproducible; the trade-off is that it measures
registration jurisdiction rather than ultimate control.

## Triangulation / mitigation

Observations are highly concentrated in a few providers — the **top 20 providers cover 91.7%** of
all mapped rows (top 10 = 85.7%). For that small, high-impact set, controlling ownership can be
established manually (legal name → registry lookup) and compared against the CAIDA registration
country, and any divergence reported. The long tail (hundreds of local ISPs/telecoms) is left on the
CAIDA registration-country proxy.

*(This sits alongside the other disclosed methodological limitation — that CDN-provider websites/URLs
were located via manual Google Search — both are stated as limitations rather than discarded.)*

## Citation

CAIDA AS Organizations Dataset, monthly snapshots 20250301–20260601,
https://www.caida.org/catalog/datasets/as-organizations/ (see `CAIDA_as_org/SOURCE.txt`).
