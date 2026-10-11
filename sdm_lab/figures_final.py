"""FINAL figures from corrected-operator data only. Supersedes older figures."""
import sys, os, json, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures", "final")
os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3})
d, k, eta = 64, 8, 0.3
mu = 3.6078
eps_c, delta_m = 0.25 * mu, 0.90 * mu
fac = math.sqrt(2 * k * (1 - k / d) / (eta * (2 - eta)))

# ---------------------------------------------------------- F1: exact backbone + window
e16 = pd.read_csv(f"{RES}/e16_backbone.csv").sort_values("sigma")
fig, ax = plt.subplots(1, 2, figsize=(10, 3.9))
sig = np.linspace(0.001, 0.5, 200)
ax[0].errorbar(e16.sigma, e16.ratio, yerr=e16.Delta_T_sd / e16.sigma, fmt="o-",
               ms=4, capsize=3, color="seagreen",
               label="consensus $N$=128 (exact $\\Delta_T$, E16)")
ax[0].axhline(fac, color="crimson", ls="--",
              label=f"exact law $\\sqrt{{2k(1-k/d)/(\\eta(2-\\eta))}}$ = {fac:.3f}")
ax[0].set_xscale("log"); ax[0].set_ylim(5.0, 8.2)
ax[0].set_xlabel("$\\sigma$"); ax[0].set_ylabel("$\\Delta_\\infty/\\sigma$")
ax[0].set_title("Backbone: one law for both modes (dev. $\\leq$0.5% at $\\sigma\\leq0.12$)")
ax[0].legend(fontsize=7)
# window panel
ax[1].axvspan(eps_c / fac, 0.42, color="palegreen", alpha=0.6,
              label="admissible window $\\Omega^*$")
ax[1].errorbar(e16.sigma, e16.Delta_T, yerr=e16.Delta_T_sd, fmt="o-", ms=4,
               capsize=3, color="seagreen", label="$\\Delta_T\\pm$sd ($N$=128)")
ax[1].axhline(eps_c, color="r", ls=":", label="$\\epsilon_c$")
ax[1].axhline(delta_m, color="b", ls=":", label="$\\delta_m$")
ax[1].axhline(mu, color="gray", ls=":", label="$\\mu_{\\rm Haar}$")
ax[1].set_xscale("log"); ax[1].set_xlabel("$\\sigma$"); ax[1].set_ylabel("$\\Delta_\\infty$")
ax[1].set_title("Sharp deterministic edges: $\\Delta_\\infty(\\sigma)\\in[\\epsilon_c,\\delta_m]$")
ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{FIG}/F1_backbone_window.png"); plt.close(fig)

# ---------------------------------------------------------- F2: N-independence
e17 = pd.read_csv(f"{RES}/e17_inflation_linear.csv")
e19 = pd.read_csv(f"{RES}/e19_omega_corrected.csv")
fig, ax = plt.subplots(1, 2, figsize=(10, 3.9))
ax[0].errorbar(e17.N, e17.ratio, yerr=e17.se, fmt="o-", ms=5, capsize=3,
               color="darkviolet")
ax[0].axhline(5.2394, color="crimson", ls="--", label="exact law 5.239")
ax[0].set_xscale("log", base=2); ax[0].set_xlabel("$N$"); ax[0].set_ylabel("$\\Delta_\\infty/\\sigma$")
ax[0].set_title("$N$-independence at $\\sigma$=0.1 ($I$=1.006, $N$=8…128)")
ax[0].legend(fontsize=8)
for D0, mk in ((1.0, "o"), (2.6, "s")):
    g = e19[e19.Delta0 == D0]
    for N, c in ((16, "orange"), (128, "navy")):
        gg = g[g.N == N].sort_values("sigma")
        ax[1].plot(gg.sigma, gg.Delta_T, mk + "-", ms=4, color=c, alpha=0.8,
                   label=f"$\\Delta_0$={D0}, $N$={N}" if D0 == 1.0 else
                         (f"$\\Delta_0$={D0}, $N$={N}" if N == 16 else None))
ax[1].axhline(eps_c, color="r", ls=":")
ax[1].axhline(delta_m, color="b", ls=":")
ax[1].set_xlabel("$\\sigma$"); ax[1].set_ylabel("$\\Delta_T$")
ax[1].set_title("All (Δ₀, N) collapse onto one curve")
ax[1].legend(fontsize=6)
fig.tight_layout(); fig.savefig(f"{FIG}/F2_N_independence.png"); plt.close(fig)

# ---------------------------------------------------------- F3: weak coupling + private
try:
    e13 = pd.read_csv(f"{RES}/e13_rho_stabilization.csv")
    e13 = e13[e13.N == 16]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.9))
    lab = {(0.01, 0.0): "noise $\\sigma$=0.01", (0.03, 0.0): "noise $\\sigma$=0.03",
           (0.0, 0.05): "private $\\rho$=0.05", (0.0, 0.1): "private $\\rho$=0.1",
           (0.0, 0.2): "private $\\rho$=0.2", (0.01, 0.05): "mixed"}
    for _, r in e13.iterrows():
        curve = [float(v) for v in r.curve.split(";")]
        key = (r.sigma, r.rho)
        ax[0].plot(np.arange(len(curve)) * 25, curve,
                   label=lab.get(key, f"({r.sigma},{r.rho})"))
    ax[0].set_xlabel("$t$"); ax[0].set_ylabel("$P(\\Delta_t\\geq\\epsilon_c)$")
    ax[0].set_title("$\\eta$=0.1, $N$=16 (corrected): total collapse for all\n"
                    "$\\sigma\\leq0.03$, $\\rho\\leq0.2$ — no stabilization")
    ax[0].legend(fontsize=6)
    # private efficiency at eta=0.3 (E9 needs rerun? E9 used broken operator -> superseded)
    ax[1].axis("off")
    ax[1].text(0.05, 0.6, "E9 (private mode) must be rerun with the\n"
               "corrected operator — superseded.\n\n"
               "E13-corrected: private pulls are ALSO\n"
               "fluctuation sources; at $\\eta$=0.1 nothing\n"
               "survives below $\\sigma^* = \\epsilon_c/8.58 = 0.105$.",
               fontsize=9, family="monospace")
except FileNotFoundError as e:
    print("skip F3:", e)
fig.tight_layout(); fig.savefig(f"{FIG}/F3_weak_coupling.png"); plt.close(fig)

# ---------------------------------------------------------- F4: E1 + dichotomy (stand)
try:
    e1b = pd.read_csv(f"{RES}/e1_delta_concentration.csv")
    e5 = pd.read_csv(f"{RES}/e5_dichotomy.csv")
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.9))
    sl = np.polyfit(np.log(e1b.N), np.log(e1b["var"]), 1)[0]
    ax[0].loglog(e1b.N, e1b["var"], "o-", label="Haar $\\Delta_0$ (MC)")
    ax[0].loglog(e1b.N, e1b["var"].iloc[0] * (e1b.N / e1b.N.iloc[0]) ** sl, "--",
                 label=f"slope {sl:.2f}")
    ax[0].loglog(e1b.N, e1b["var"].iloc[0] * (e1b.N / e1b.N.iloc[0]) ** -1, ":",
                 label="$N^{-1}$ (non-degenerate)")
    ax[0].set_xlabel("$N$"); ax[0].set_ylabel("Var $\\Delta_0$")
    ax[0].set_title("Degenerate U-statistic at Haar: $N^{-2}$")
    ax[0].legend(fontsize=7)
    sl5 = np.polyfit(np.log(e5.N), np.log(e5["var"]), 1)[0]
    ax[1].loglog(e5.N, e5["var"], "s-", color="darkorange",
                 label="stationary swarm (task mode)")
    ax[1].loglog(e5.N, e5.pred_var, "k--", label="Hoeffding $4\\zeta_1/N+2\\zeta_2/N^2$")
    ax[1].set_xlabel("$N$"); ax[1].set_ylabel("Var $\\Delta$")
    ax[1].set_title(f"Non-invariant law: $N^{{{sl5:.2f}}}$ (dichotomy)")
    ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(f"{FIG}/F4_concentration_dichotomy.png"); plt.close(fig)
    print("F4 done")
except FileNotFoundError as e:
    print("skip F4:", e)
print("final figures in", FIG)
