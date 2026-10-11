"""E8: UNBIASED collapse/divergence boundary scan (fixes the min-estimator bias).

Definition fix: collapse := (Delta_T < eps_c) at T=500 (converged), computed from
EXACT full-pairwise Delta at the final step only. No min-tracking bias.
Transient violations reported separately with a low-noise estimator (16384 pairs,
8 track points => SE ~ 0.004, bias negligible).

Cells:
  boundary: sigma in {0.11,0.125,0.14,0.155,0.17,0.19}, T=500, R=256
  tail:     sigma in {0.25,0.3,0.4,0.5,0.6,0.7},     T=300, R=128
N=128, k=8, d=64, eta=0.3, Delta_0=1.8 (calibrated).  Wilson 95% CIs everywhere.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, delta_batch, delta_estimate_batch,
                  span_metrics_batch, grad_step)

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(41)
d, k, eta, N = 64, 8, 0.3, 128

A = haar_sample(200_000, d, k, dev); B = haar_sample(200_000, d, k, dev)
mu_haar = float(geodesic_dist(A, B).mean()); del A, B
eps_c, delta_m = 0.25 * mu_haar, 0.90 * mu_haar
print(f"mu={mu_haar:.4f} eps_c={eps_c:.4f} delta_m={delta_m:.4f}", flush=True)

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

def wilson(p, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, ctr - hw), min(1.0, ctr + hw))

R0 = 256
Qbase = haar_sample(R0 * N, d, k, dev, gen).reshape(R0, N, d, k)
lo, hi = 0.0, 0.9995
for _ in range(14):
    mid = 0.5 * (lo + hi)
    if float(delta_batch(shrink(Qbase[0], mid).unsqueeze(0))) > 1.8: lo = mid
    else: hi = mid
Q0 = shrink(Qbase, 0.5 * (lo + hi))
D0 = delta_batch(Q0)
print(f"shrink c={0.5*(lo+hi):.4f}  Delta_0={float(D0.mean()):.4f}", flush=True)

cells = [(s, 500, 256) for s in (0.11, 0.125, 0.14, 0.155, 0.17, 0.19)] + \
        [(s, 300, 128) for s in (0.25, 0.3, 0.4, 0.5, 0.6, 0.7)]
rows = []
for sigma, T, R in cells:
    Q = Q0[:R].clone()
    ntr = max(1, T // 60)
    viol = torch.zeros(R, device=dev)          # transient min<eps_c (low-noise est)
    for t in range(T + 1):
        if t % 60 == 0 and t > 0:
            De = delta_estimate_batch(Q, 16384, gen)
            viol += (De < eps_c).float()
        if t < T:
            Q = grad_step(Q, eta, sigma, gen=gen)
    Df = delta_batch(Q)                        # exact, unbiased
    rank, pr, H = span_metrics_batch(Q)
    Pc = float((Df < eps_c).float().mean())
    Pd = float((Df > delta_m).float().mean())
    Pvi = float((viol > 0).float().mean())
    wc, wd = wilson(Pc, R), wilson(Pd, R)
    rows.append(dict(sigma=sigma, T=T, R=R, Delta_mean=float(D0[:R].mean()),
                     Delta_T=float(Df.mean()), Delta_T_sd=float(Df.std()),
                     Delta_T_p05=float(torch.quantile(Df, 0.05)),
                     Delta_T_p95=float(torch.quantile(Df, 0.95)),
                     P_collapse=Pc, Pc_lo=wc[0], Pc_hi=wc[1],
                     P_diverge=Pd, Pd_lo=wd[0], Pd_hi=wd[1],
                     P_transient_violation=Pvi,
                     PR=float(pr.mean()), rank=float(rank.mean())))
    r = rows[-1]
    print(f"s={sigma:5.3f} T={T} R={R} | D_T={r['Delta_T']:.4f}+-{r['Delta_T_sd']:.4f} "
          f"[{r['Delta_T_p05']:.3f},{r['Delta_T_p95']:.3f}] | "
          f"Pc={Pc:.3f} [{wc[0]:.3f},{wc[1]:.3f}] Pd={Pd:.3f} Pvi={Pvi:.3f} | "
          f"PR={r['PR']:.2f} rank={r['rank']:.1f}", flush=True)
    pd.DataFrame(rows).to_csv(f"{RES}/e8_unbiased_boundary.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e8_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
