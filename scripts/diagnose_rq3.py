"""
Small-sample diagnostics for the two 'significant' RQ3 coefficients
(Model 1 CGIT_amount, Model 2 CGIT_type). You run this.

Tests whether the p<0.001 results survive proper inference for a panel with only
10 clusters (countries):
  1. Wild cluster bootstrap (Rademacher weights, restricted null H0: beta_j = 0) --
     the standard remedy for <40 clusters. If the effect is real the WCB p stays small;
     if it's the SE-collapse artifact, the WCB p balloons.
  2. Leave-one-country-out refits -- shows whether a single country drives the result.
  3. Lists the country-years that actually identify the coefficient.

FE estimated by LSDV (country dummies); CR1 cluster-robust cov; t-dist with G-1 dof.
Console output only (paste it back). Run:
   /opt/anaconda3/bin/python3 diagnose_rq3.py
"""
import numpy as np
import pandas as pd
from scipy import stats
from build_rq3_regression import nedko_cdn_china, openintel_ip_china, cgit_by_country_year, CCS

XCOLS = ["CGIT_projects", "CGIT_amount", "CGIT_type"]


def build_design(dv, dv_years):
    cg = cgit_by_country_year()
    rows = []
    for cc in CCS:
        for y in dv_years:
            d = dv.get((cc, str(y)))
            if d is None:
                continue
            proj, amt, typ = cg.get((cc, str(y - 1)), (0, 0.0, 0))
            rows.append((cc, y, d, proj, amt, typ))
    return pd.DataFrame(rows, columns=["country", "year", "DV", *XCOLS])


def fe_fit(df, xcols, y):
    countries = sorted(df.country.unique())
    D = np.column_stack([(df.country.values == c).astype(float) for c in countries])
    X = df[xcols].values.astype(float)
    XD = np.column_stack([X, D])
    beta, *_ = np.linalg.lstsq(XD, y, rcond=None)
    return beta, XD, y - XD @ beta


def cr_cov(df, XD, resid):
    XtXi = np.linalg.pinv(XD.T @ XD)
    meat = np.zeros((XD.shape[1], XD.shape[1]))
    cs = df.country.values
    for c in np.unique(cs):
        idx = cs == c
        s = XD[idx].T @ resid[idx]
        meat += np.outer(s, s)
    N, K = XD.shape
    G = len(np.unique(cs))
    corr = (G / (G - 1)) * ((N - 1) / (N - K))
    return corr * (XtXi @ meat @ XtXi), G


def analytic(df, xcols, j):
    y = df.DV.values.astype(float)
    beta, XD, resid = fe_fit(df, xcols, y)
    V, G = cr_cov(df, XD, resid)
    se = np.sqrt(V[j, j]); t = beta[j] / se
    p = 2 * stats.t.sf(abs(t), G - 1)
    return beta[j], se, t, p, G


def wcb(df, xcols, j, B=1999, seed=0):
    rng = np.random.default_rng(seed)
    y = df.DV.values.astype(float)
    beta, XD, resid = fe_fit(df, xcols, y)
    V, _ = cr_cov(df, XD, resid)
    t_obs = beta[j] / np.sqrt(V[j, j])
    xr = [c for i, c in enumerate(xcols) if i != j]
    beta_r, XDr, resid_r = fe_fit(df, xr, y)
    yhat_r = XDr @ beta_r
    cs = df.country.values; uniq = np.unique(cs)
    cnt = 0
    for _ in range(B):
        w = {c: (1.0 if rng.random() < 0.5 else -1.0) for c in uniq}
        wv = np.array([w[c] for c in cs])
        ystar = yhat_r + wv * resid_r
        bb, XDb, rb = fe_fit(df, xcols, ystar)
        Vb, _ = cr_cov(df, XDb, rb)
        tb = bb[j] / np.sqrt(Vb[j, j])
        if abs(tb) >= abs(t_obs):
            cnt += 1
    return t_obs, (cnt + 1) / (B + 1)


def loco(df, xcols, j):
    out = []
    for c in sorted(df.country.unique()):
        sub = df[df.country != c]
        if sub[xcols[j]].nunique() <= 1:
            out.append((c, np.nan, np.nan, np.nan, "no variation left"))
            continue
        b, se, t, p, G = analytic(sub, xcols, j)
        out.append((c, b, se, p, ""))
    return out


def report(name, df, j):
    var = XCOLS[j]
    print(f"\n================ {name}: {var} ================")
    ident = df[df[var] != 0]
    print(f"panel N={len(df)}, countries={df.country.nunique()}")
    print(f"identifying rows ({var} != 0): {len(ident)}")
    for _, r in ident.iterrows():
        print(f"    {r.country} {r.year}: {var}={r[var]}")
    b, se, t, p, G = analytic(df, XCOLS, j)
    print(f"\nFE coef={b:.4f}  CR-robust SE={se:.4f}  t={t:.2f}  analytic p(t,{G-1}df)={p:.4f}")
    t_obs, pwcb = wcb(df, XCOLS, j)
    print(f"WILD CLUSTER BOOTSTRAP p = {pwcb:.4f}   (B=1999, Rademacher, restricted null)")
    verdict = "SURVIVES (still p<0.05)" if pwcb < 0.05 else "DOES NOT SURVIVE (p>=0.05) -> small-sample artifact"
    print(f"  -> {verdict}")
    print("leave-one-country-out (drop each country, refit):")
    for c, bb, sse, pp, note in loco(df, XCOLS, j):
        if note:
            print(f"    drop {c}: {note}")
        else:
            print(f"    drop {c}: coef={bb:+.4f}  p={pp:.4f}")


def main():
    print("building panels...")
    cdn = nedko_cdn_china(); ip = openintel_ip_china()
    m1 = build_design(cdn, [2024, 2025, 2026])
    m2 = build_design(ip, [2025, 2026])
    report("Model 1 (CDN)", m1, XCOLS.index("CGIT_amount"))
    report("Model 2 (IP)",  m2, XCOLS.index("CGIT_type"))
    print("\n(interpretation: if the wild-cluster-bootstrap p is >= 0.05, the original "
          "p<0.001 was a few-clusters SE-collapse artifact, not a real effect.)")


if __name__ == "__main__":
    main()
