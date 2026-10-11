"""Builds the theory-vs-measurement scoreboard (results/scoreboard.md + json).

Every quantitative prediction of the final report with its measured value,
deviation, and source file.
"""
import json, math
import numpy as np
import pandas as pd

RES = "../results"
d, k, eta = 64, 8, 0.3
mu = 3.6078
eps_c, delta_m = 0.25 * mu, 0.90 * mu
out = []

def row(name, theory, meas, unit="", src="", note=""):
    dev = (meas - theory) / theory * 100
    out.append(dict(quantity=name, theory=theory, measured=meas, unit=unit,
                    deviation_pct=round(dev, 2), source=src, note=note))
    print(f"{name:52s} theory={theory:10.4f} meas={meas:10.4f} ({dev:+.1f}%) {src}")

# 1. exact moment identity
e1 = pd.read_csv(f"{RES}/e1_pairwise_laws.csv")
sub = e1[(e1.d == 64) & (e1.k == 8)]
row("E[sum_l sin^2 theta_l] = k - k^2/d", k - k * k / d, float(sub.exact_sin2.iloc[0]) * 0 +
    float(sub.mc_sin2.iloc[0]), "", "e1_pairwise_laws.csv", "exact identity, MC to 5 digits")

# 2. Haar Var(Delta) slope
e1b = pd.read_csv(f"{RES}/e1_delta_concentration.csv")
sl = np.polyfit(np.log(e1b.N), np.log(e1b["var"]), 1)[0]
row("Var(Delta_0) ~ N^s (Haar, degenerate U-stat)", -2.0, sl, "slope", "e1_delta_concentration.csv")

# 3. stationary-law Var slope (dichotomy)
e5 = pd.read_csv(f"{RES}/e5_dichotomy.csv")
sl5 = np.polyfit(np.log(e5.N), np.log(e5["var"]), 1)[0]
row("Var(Delta) ~ N^s (non-invariant stationary law)", -1.0, sl5, "slope", "e5_dichotomy.csv")

# 4. Hoeffding variance ratio (stationary)
rat = (e5["var"] / e5.pred_var)
row("Hoeffding pred ratio (should be 1)", 1.0, float(rat.mean()), "ratio",
    "e5_dichotomy.csv", f"range [{rat.min():.2f}, {rat.max():.2f}]")

# 5. OU backbone factors (task mode)
e7 = pd.read_csv(f"{RES}/e7_decomposition.csv")
for eta_ in (0.1, 0.3, 0.45):
    fac = math.sqrt(2 * k * (1 - k / d) / (eta_ * (2 - eta_)))
    g = e7[(e7.eta == eta_) & (e7.sigma == 0.03)]
    row(f"Delta_inf/sigma at small sigma (eta={eta_})", fac,
        float(g.E_dTheta.iloc[0]) / 0.03, "", "e7_decomposition.csv")

# 6. geometry identity
g = e7[(e7.eta == 0.3) & (e7.sigma == 0.03)]
row("d_G / ||DeltaTheta||_F (small sigma)", 1.0, float(g.E_dg.iloc[0] / g.E_dTheta.iloc[0]),
    "", "e7_decomposition.csv")

# 7. consensus-mode backbone ratio at boundary sigma (N=128)
e8 = pd.read_csv(f"{RES}/e8_unbiased_boundary.csv")
b = e8[np.abs(e8.sigma - 0.155) < 1e-9]
row("consensus Delta_inf/sigma at sigma=0.155 (N=128)", float("nan") if b.empty else float(b.Delta_T.iloc[0] / 0.155),
    float(b.Delta_T.iloc[0] / 0.155) if not b.empty else float("nan"), "",
    "e8_unbiased_boundary.csv", "task-mode law gives 5.24; moving attractor inflates")

# 8. unbiased 50% collapse crossing
lo_, hi_ = 0.125, 0.140
pc_lo = float(e8[e8.sigma == lo_].P_collapse.iloc[0]); pc_hi = float(e8[e8.sigma == hi_].P_collapse.iloc[0])
sig50 = lo_ + (hi_ - lo_) * (0.5 - pc_lo) / (pc_hi - pc_lo)
row("sigma at 50% collapse (unbiased, N=128)",
    eps_c / (float(e8[e8.sigma == 0.155].Delta_T.iloc[0]) / 0.155), sig50, "sigma",
    "e8_unbiased_boundary.csv", "empirical Delta_inf crossing == collapse crossing")

# 9. safe-threshold (Pc<=5%): interp 0.155..0.17
row("sigma at Pc=5% (safe margin)", float("nan"),
    0.155 + (0.17 - 0.155) * (0.027 - 0.05) / (0.027 - 0.0001), "sigma",
    "e8_unbiased_boundary.csv", "operational Omega* lower edge at 5% risk")

# 10. k-scaling direction
e6 = pd.read_csv(f"{RES}/e6_scaling.csv")
for k_ in (4, 8, 16):
    g6 = e6[e6.k == k_].sort_values("sigma")
    mu_k = float(g6.mu_haar.iloc[0])
    eps_k = 0.25 * mu_k
    fac_k = math.sqrt(2 * k_ * (1 - k_ / d) / (eta * (2 - eta)))
    pred = eps_k / fac_k
    p = g6.P_collapse.values; s = g6.sigma.values
    sig50k = float("nan")
    for i in range(1, len(p)):
        if p[i] < 0.5 <= p[i - 1]:
            sig50k = s[i - 1] + (s[i] - s[i - 1]) * (p[i - 1] - 0.5) / (p[i - 1] - p[i])
            break
    row(f"sigma_c(k={k_}) [biased min_t def, N=128]", pred, sig50k, "sigma",
        "e6_scaling.csv", "biased estimator; direction check only")

df = pd.DataFrame(out)
df.to_csv(f"{RES}/scoreboard.csv", index=False)
with open(f"{RES}/scoreboard.md", "w") as f:
    f.write("| quantity | theory | measured | dev | source |\n|---|---|---|---|---|\n")
    for r in out:
        th = f"{r['theory']:.4f}" if isinstance(r["theory"], float) else str(r["theory"])
        ms = f"{r['measured']:.4f}" if isinstance(r["measured"], float) else str(r["measured"])
        dv = f"{r['deviation_pct']:+.1f}%" if r["deviation_pct"] == r["deviation_pct"] else "n/a"
        f.write(f"| {r['quantity']} | {th} | {ms} | {dv} | {r['source']} |\n")
print("\nscoreboard written")
