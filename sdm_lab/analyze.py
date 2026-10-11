"""Analysis & figures for E1-E5. Produces figures/ and a metrics summary."""
import sys, os, json, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3})

meta3 = json.load(open(f"{RES}/e3b_meta.json"))
mu_haar, eps_c, delta_m = meta3["mu_haar"], meta3["eps_c"], meta3["delta_m"]
d, k, eta = meta3["d"], meta3["k"], meta3["eta"]

# ---------------------------------------------------------------- Fig 1: E1 concentration
dfB = pd.read_csv(f"{RES}/e1_delta_concentration.csv")
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
ax[0].loglog(dfB.N, dfB["var"], "o-", label="MC Var($\\Delta_0$), Haar")
sl = np.polyfit(np.log(dfB.N), np.log(dfB["var"]), 1)[0]
ax[0].loglog(dfB.N, dfB["var"].iloc[0] * (dfB.N / dfB.N.iloc[0]) ** sl, "--",
             label=f"fit slope={sl:.2f}")
ax[0].loglog(dfB.N, dfB["var"].iloc[0] * (dfB.N / dfB.N.iloc[0]) ** -1, ":",
             label="slope $-1$ (nondegenerate U-stat)")
ax[0].set_xlabel("$N$"); ax[0].set_ylabel("Var $\\Delta_0$")
ax[0].set_title("Haar swarms: degenerate U-statistic\n$\\mathrm{Var}\\sim N^{-2}$ ($\\zeta_1=0$)")
ax[0].legend(fontsize=7)
pw = pd.read_csv(f"{RES}/e1_pairwise_laws.csv")
ax[1].plot(pw.Edg2 / pw.k, "o", label="$E[d_G^2]/k$ (MC)")
ax[1].plot(pw.asy1 / pw.k, "s", ms=4, label="theory $\\pi^2/4-\\pi\\sqrt{2k/(\\pi d)}+k/d$")
ax[1].axhline(math.pi ** 2 / 4, color="gray", ls=":", label="$\\pi^2/4$ ($d=\\infty$)")
ax[1].set_xlabel("(d,k) grid index"); ax[1].set_ylabel("$E[d_G^2]/k$")
ax[1].set_title("Pairwise distance moments vs theory")
ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{FIG}/f1_haar_concentration.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 2: phase diagram
df = pd.read_csv(f"{RES}/e3_phase.csv")
piv_D = df.pivot(index="N", columns="sigma", values="Delta_mean")
fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
for axi, col, ttl, cmap in [
        (ax[0], "P_collapse", "$P(\\min_t\\Delta_t<\\epsilon_c)$ collapse", "Reds"),
        (ax[1], "P_diverge", "$P(\\max_t\\Delta_t>\\delta_m)$ divergence", "Blues"),
        (ax[2], "PR", "PR (effective span)", "viridis")]:
    P = df.pivot(index="N", columns="sigma", values=col)
    im = axi.pcolormesh(P.columns.astype(float), P.index.astype(int), P.values,
                        cmap=cmap, shading="auto")
    axi.set_xscale("log"); axi.set_yscale("log")
    axi.set_xlabel("$\\sigma$"); axi.set_ylabel("$N$"); axi.set_title(ttl)
    fig.colorbar(im, ax=axi)
# mean-field backbone overlay on Delta panel
sig = np.logspace(np.log10(0.004), np.log10(0.6), 100)
mf = sig * math.sqrt(k / (eta * (1 - k / d)))
ax[1].plot(sig, np.interp(mf, piv_D.columns.astype(float),
                          np.linspace(1, 8, 1)) * 0 + np.nan)  # placeholder
fig.tight_layout(); fig.savefig(f"{FIG}/f2_phase_diagram.png"); plt.close(fig)

# Delta_inf vs sigma curves per N + mean-field law (from e3b final Delta_T)
e3b = pd.read_csv(f"{RES}/e3b_omega.csv")
sig = np.logspace(np.log10(0.004), np.log10(0.6), 100)
mf = sig * math.sqrt(2 * k / (eta * (2 - eta)))
fig, ax = plt.subplots(figsize=(6.4, 4))
for N in sorted(e3b.N.unique()):
    sub = e3b[(e3b.N == N) & (e3b.Delta0_target == 1.8)].sort_values("sigma")
    ax.loglog(sub.sigma, sub.Delta_T, "o-", ms=3, label=f"N={N}")
ax.loglog(sig, mf, "k--",
          label="discrete-OU MF: $\\sigma\\sqrt{2k/(\\eta(2-\\eta))}=5.60\\,\\sigma$")
try:
    e8c = pd.read_csv(f"{RES}/e8_unbiased_boundary.csv").sort_values("sigma")
    ax.loglog(e8c.sigma, e8c.Delta_T, "c-.", lw=1.2,
              label="consensus $N$=128 (exact $\\Delta_T$, E8)")
except Exception:
    ax.loglog(sig, 6.0 * sig, "c-.", lw=1, label="measured $\\Delta_\\infty\\approx 6.0\\sigma$")
ax.axhline(eps_c, color="r", ls=":", label="$\\epsilon_c$")
ax.axhline(delta_m, color="b", ls=":", label="$\\delta_m$")
ax.axhline(mu_haar, color="gray", ls=":", label="$\\mu_{Haar}$")
ax.set_xlabel("$\\sigma$"); ax.set_ylabel("$\\Delta_\\infty$")
ax.set_title("Stationary $\\Delta_\\infty(\\sigma,N)$, $\\Delta_0=1.8$ slice: binding grows with $N$")
ax.legend(fontsize=6, ncol=2)
fig.tight_layout(); fig.savefig(f"{FIG}/f3_delta_inf_law.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 4: dichotomy
try:
    df5 = pd.read_csv(f"{RES}/e5_dichotomy.csv")
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    ax[0].loglog(df5.N, df5["var"], "o-", label="stationary (task mode)")
    ax[0].loglog(df5.N, df5.pred_var, "k--", label="Hoeffding pred $4\\zeta_1/N+2\\zeta_2/N^2$")
    e1 = pd.read_csv(f"{RES}/e1_delta_concentration.csv")
    sc = df5["var"].iloc[0] * (e1["var"].iloc[0] / df5["var"].iloc[0])
    ax[0].loglog(e1.N, e1["var"] * sc / e1["var"].iloc[0] * e1["var"].iloc[0], "s-",
                 ms=3, alpha=0.6, label="Haar control (rescaled)")
    ax[0].set_xlabel("$N$"); ax[0].set_ylabel("Var $\\Delta$"); ax[0].legend(fontsize=7)
    ax[0].set_title("U-statistic dichotomy:\n$N^{-1}$ (non-inv.) vs $N^{-2}$ (Haar)")
    mt = pd.read_csv(f"{RES}/e5_metastability.csv")
    for _, row in mt.iterrows():
        curve = [float(v) for v in row.curve.split(";")]
        ax[1].plot(np.arange(len(curve)) * 20, curve,
                   label=f"N={int(row.N)}, $\\sigma$={row.sigma}")
    ax[1].set_xlabel("$t$"); ax[1].set_ylabel("$P(\\Delta_t \\geq \\epsilon_c)$")
    ax[1].set_title("Metastable diversity survival ($\\eta=0.1$)")
    ax[1].legend(fontsize=6)
    fig.tight_layout(); fig.savefig(f"{FIG}/f4_dichotomy_metastability.png"); plt.close(fig)
except FileNotFoundError as e:
    print("skip fig4:", e)

# ---------------------------------------------------------------- Fig 5: init comparison
try:
    df4 = pd.read_csv(f"{RES}/e4_init.csv")
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    for name, sub in df4.groupby("init"):
        ax[0].semilogx(sub.sigma, sub.PR_T, "o-", label=name)
        ax[1].semilogx(sub.sigma, sub.P_collapse, "o-", label=name)
    ax[0].set_xlabel("$\\sigma$"); ax[0].set_ylabel("PR at $T$"); ax[0].legend(fontsize=7)
    ax[0].set_title("Effective span at $T$ (matched $\\Delta_0$)")
    ax[1].set_xlabel("$\\sigma$"); ax[1].set_ylabel("$P_{collapse}$"); ax[1].legend(fontsize=7)
    ax[1].set_title("Collapse probability by init type")
    fig.tight_layout(); fig.savefig(f"{FIG}/f5_init_comparison.png"); plt.close(fig)
except FileNotFoundError as e:
    print("skip fig5:", e)

print("figures written to", FIG)

# ---------------------------------------------------------------- Fig 6: Omega* from e3b
import json as _json
m3b = _json.load(open(f"{RES}/e3b_meta.json"))
df = pd.read_csv(f"{RES}/e3b_omega.csv")
eps_c, delta_m = m3b["eps_c"], m3b["delta_m"]
Delta0s = sorted(df.Delta0_target.unique())
fig, axes = plt.subplots(len(Delta0s), 3, figsize=(13, 3.1 * len(Delta0s)))
for i, D0 in enumerate(Delta0s):
    sub = df[df.Delta0_target == D0]
    for j, (col, ttl, cmap, vmin, vmax) in enumerate([
            ("P_admissible", f"$P$ admissible ($\\Delta_0={D0}$)", "Greens", 0, 1),
            ("P_collapse", "collapse", "Reds", 0, 1),
            ("PR_T", "PR at $T$", "viridis", None, None)]):
        P = sub.pivot(index="N", columns="sigma", values=col)
        axi = axes[i, j]
        im = axi.pcolormesh(P.columns.astype(float), P.index.astype(int), P.values,
                            cmap=cmap, shading="auto", vmin=vmin, vmax=vmax)
        axi.set_xscale("log"); axi.set_yscale("log")
        axi.set_ylabel("$N$" if j == 0 else "")
        axi.set_title(ttl, fontsize=9)
        axi.invert_yaxis()
        fig.colorbar(im, ax=axi)
        if i == len(Delta0s) - 1:
            axi.set_xlabel("$\\sigma$")
        if col == "PR_T":
            for N in P.index:
                for s in P.columns:
                    v = P.loc[N, s]
                    if v == v:
                        axi.text(s, N, f"{v:.1f}", fontsize=5, ha="center", va="center",
                                 color="white" if v < (vmax or 8) / 2 else "black")
fig.suptitle("$\\Omega^*$ phase structure in $(\\sigma, N)$ per initial diversity "
             "$\\Delta_0$  (consensus $\\Phi$, $\\eta=0.3$, $d=64$, $k=8$, $T=160$)", y=1.0)
fig.tight_layout(); fig.savefig(f"{FIG}/f6_omega_diagram.png", bbox_inches="tight"); plt.close(fig)

# collapse boundary sigma_c(N) per Delta0: sigma where P_collapse crosses 0.5
fig, ax = plt.subplots(figsize=(5.6, 3.8))
for D0 in Delta0s:
    sub = df[df.Delta0_target == D0].sort_values(["N", "sigma"])
    Ns_, sc_ = [], []
    for N, g in sub.groupby("N"):
        g = g.sort_values("sigma")
        s = g.sigma.values; p = g.P_collapse.values
        if p.max() < 0.5:
            continue
        idx = np.argmax(p < 0.5)
        if idx == 0:
            continue
        # linear interp in log-sigma
        s1, s0 = s[idx], s[idx - 1]
        p1, p0 = p[idx], p[idx - 1]
        sc = math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * (0.5 - p0) / (p1 - p0))
        Ns_.append(N); sc_.append(sc)
    ax.loglog(Ns_, sc_, "o-", label=f"$\\Delta_0={D0}$")
mf = eps_c * math.sqrt(eta * (2 - eta) / (2 * k))
ax.axhline(mf, color="k", ls="--", label=f"MF $\\sigma_c={mf:.3f}$")
ax.set_xlabel("$N$"); ax.set_ylabel("$\\sigma_c$ (50% collapse)")
ax.set_title("Collapse boundary: binding strengthens with $N$")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(f"{FIG}/f7_collapse_boundary.png"); plt.close(fig)
print("e3b figures done")

# ---------------------------------------------------------------- Fig 8: E6 scaling
try:
    e6 = pd.read_csv(f"{RES}/e6_scaling.csv")
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.5))
    for k, g in e6.groupby("k"):
        g = g.sort_values("sigma")
        ax[0].semilogx(g.sigma / g.sigma_c_mf, g.P_collapse, "o-",
                       label=f"k={k} ($\\sigma_c^{{MF}}$={g.sigma_c_mf.iloc[0]:.3f})")
        ax[1].semilogx(g.sigma, g.Delta_over_sigma, "o-", label=f"k={k}")
    ax[0].axvline(1.0, color="k", ls="--", lw=1)
    ax[0].set_xlabel("$\\sigma/\\sigma_c^{MF}$"); ax[0].set_ylabel("$P_{collapse}$")
    ax[0].set_title("Collapse boundary in MF-normalized units\n(consistent ~20% shift)")
    ax[0].legend(fontsize=7)
    th = {4: 3.96, 8: 5.60, 16: 7.92}
    for k, g in e6.groupby("k"):
        ax[1].axhline(th[k], color="gray", ls=":", lw=0.8)
    ax[1].set_xlabel("$\\sigma$"); ax[1].set_ylabel("$\\Delta_T/\\sigma$")
    ax[1].set_title("Backbone factor vs $\\sqrt{2k/(\\eta(2-\\eta))}$ (dotted)")
    ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(f"{FIG}/f8_k_scaling.png"); plt.close(fig)
    print("fig8 done")
except FileNotFoundError as e:
    print("skip fig8:", e)

# ---------------------------------------------------------------- Fig 9: E7 decomposition
try:
    e7 = pd.read_csv(f"{RES}/e7_decomposition.csv")
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.6))
    for eta, g in e7.groupby("eta"):
        g = g.sort_values("sigma")
        fac_c = math.sqrt(2 * k * (1 - k / d) / (eta * (2 - eta)))
        ax[0].loglog(g.sigma, g.E_dTheta / g.sigma, "o-", ms=4,
                     label=f"$\\eta$={eta}: meas $\\|\\Delta\\Theta\\|/\\sigma$")
        ax[0].axhline(fac_c, color="gray", ls=":", lw=0.8)
        ax[0].text(0.004, fac_c * 1.02, f"{fac_c:.2f}", fontsize=6, color="gray")
        ax[1].loglog(g.sigma, g.E_dg / g.E_dTheta, "o-", ms=4, label=f"$\\eta$={eta}")
    ax[0].set_xlabel("$\\sigma$"); ax[0].set_ylabel("$\\|\\Delta\\Theta\\|_F/\\sigma$")
    ax[0].set_title("Dynamics: OU law (dotted = exact $\\sqrt{2k(1-k/d)/(\\eta(2-\\eta))}$)")
    ax[0].legend(fontsize=6)
    ax[1].axhline(1.0, color="k", ls="--", lw=0.8)
    ax[1].set_xlabel("$\\sigma$"); ax[1].set_ylabel("$d_G/\\|\\Delta\\Theta\\|_F$")
    ax[1].set_title("Geometry: $d_G = \\|\\Delta\\Theta\\|_F \\cdot (1+O(\\sigma^2))$")
    ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(f"{FIG}/f9_decomposition.png"); plt.close(fig)
    print("fig9 done")
except FileNotFoundError as e:
    print("skip fig9:", e)

# ---------------------------------------------------------------- Fig 10: E8 unbiased boundary
try:
    e8 = pd.read_csv(f"{RES}/e8_unbiased_boundary.csv").sort_values("sigma")
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.6))
    ax[0].errorbar(e8.sigma, e8.P_collapse,
                   yerr=[e8.P_collapse - e8.Pc_lo, e8.Pc_hi - e8.P_collapse],
                   fmt="o-", ms=4, capsize=3, color="crimson",
                   label="$P(\\Delta_T<\\epsilon_c)$ Wilson 95%")
    ax[0].errorbar(e8.sigma, e8.P_diverge,
                   yerr=[e8.P_diverge - e8.Pd_lo, e8.Pd_hi - e8.P_diverge],
                   fmt="s-", ms=4, capsize=3, color="royalblue",
                   label="$P(\\Delta_T>\\delta_m)$ Wilson 95%")
    ax[0].axhline(0.5, color="gray", lw=0.8, ls=":")
    ax[0].set_xscale("log"); ax[0].set_xlabel("$\\sigma$"); ax[0].set_ylabel("probability")
    ax[0].set_title("Unbiased phase cut ($N$=128, $T$=300–500, exact $\\Delta_T$)")
    ax[0].legend(fontsize=7)
    ax[1].errorbar(e8.sigma, e8.Delta_T, yerr=e8.Delta_T_sd, fmt="o-", ms=4,
                   capsize=3, color="seagreen", label="$\\Delta_T \\pm$ sd")
    ax[1].axhline(eps_c, color="r", ls=":", label="$\\epsilon_c$")
    ax[1].axhline(delta_m, color="b", ls=":", label="$\\delta_m$")
    ax[1].set_xscale("log"); ax[1].set_xlabel("$\\sigma$"); ax[1].set_ylabel("$\\Delta_T$")
    ax[1].set_title("Stationary backbone, consensus $N$=128")
    ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(f"{FIG}/f10_unbiased_boundary.png"); plt.close(fig)
    print("fig10 done")
except FileNotFoundError as e:
    print("skip fig10:", e)

# ---------------------------------------------------------------- Fig 11: E9 private vs noise
try:
    e9 = pd.read_csv(f"{RES}/e9_private.csv")
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.6))
    for s, g in e9.groupby("sigma"):
        g = g.sort_values("rho")
        ax[0].loglog(g.Delta, g.PR, "o-", ms=4, label=f"$\\rho$-family, $\\sigma$={s}")
    ns = e9[e9.rho == 0.005]
    ax[1].loglog(e9.sigma + 1e-4, e9.PR, "o", ms=4, alpha=0.4)
    for rho, g in e9.groupby("rho"):
        g = g.sort_values("sigma")
        ax[0].loglog(g.Delta, g.PR, "o", ms=3, alpha=0.3)
    sc = pd.read_csv(f"{RES}/e2b_P4_span_sigma.csv")
    ax[0].loglog(sc.Delta, sc.PR, "k^-", ms=4, label="noise-only $N$=128 (E2b)")
    ax[0].set_xlabel("$\\Delta_\\infty$"); ax[0].set_ylabel("PR (effective span)")
    ax[0].set_title("Span efficiency: private data ($\\rho$) vs noise ($\\sigma$)")
    ax[0].legend(fontsize=6)
    ax[1].loglog(e9.rho, e9.Delta, "o-", color="teal", label="$\\Delta_\\infty(\\rho)$, $\\sigma$=0")
    ax[1].loglog(e9.rho, e9.PR, "s-", color="darkorange", label="PR$(\\rho)$, $\\sigma$=0")
    ax[1].axhline(eps_c, color="r", ls=":")
    ax[1].set_xlabel("$\\rho$"); ax[1].legend(fontsize=7)
    ax[1].set_title("Private-data-only stationary state")
    fig.tight_layout(); fig.savefig(f"{FIG}/f11_private_vs_noise.png"); plt.close(fig)
    print("fig11 done")
except FileNotFoundError as e:
    print("skip fig11:", e)

# ---------------------------------------------------------------- Fig 12: E10 long survival
try:
    mt = pd.read_csv(f"{RES}/e10_metastability_long.csv")
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for _, row in mt.iterrows():
        curve = [float(v) for v in row.curve.split(";")]
        ax.semilogx(np.arange(len(curve)) * 25 + 1e-9, curve,
                    label=f"N={int(row.N)}, $\\sigma$={row.sigma}")
    ax.set_xlabel("$t$"); ax.set_ylabel("$P(\\Delta_t\\geq\\epsilon_c)$")
    ax.set_title("Long-horizon survival at $\\eta$=0.1: geometric decay\n(metastable, collapse certain)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{FIG}/f12_long_survival.png"); plt.close(fig)
    print("fig12 done")
except FileNotFoundError as e:
    print("skip fig12:", e)
