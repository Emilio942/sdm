"""E9: Private-data innovations vs isotropic noise as diversity mechanisms.

Question: models fine-tune on shared data (consensus, eta) plus their own private
data stream (rho, fresh random subspace per step) plus SGD noise (sigma).
  (a) Does rho alone (sigma=0) maintain a stationary diversity?  Delta_inf(rho)?
  (b) Span efficiency: at matched Delta_inf, does rho produce higher effective
      span (PR) than sigma? (structured vs isotropic perturbations)

Grid: eta=0.3, N=64, rho x sigma, T=300, R=128, Delta_0=1.8.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, delta_batch, span_metrics_batch,
                  grad_step_private)

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(51)
d, k, eta, N, R, T = 64, 8, 0.3, 64, 128, 300

A = haar_sample(200_000, d, k, dev); B = haar_sample(200_000, d, k, dev)
mu_haar = float(geodesic_dist(A, B).mean()); del A, B
eps_c, delta_m = 0.25 * mu_haar, 0.90 * mu_haar
print(f"mu={mu_haar:.4f}", flush=True)

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

Qbase = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
lo, hi = 0.0, 0.9995
for _ in range(14):
    mid = 0.5 * (lo + hi)
    if float(delta_batch(shrink(Qbase[0], mid).unsqueeze(0))) > 1.8: lo = mid
    else: hi = mid
Q0 = shrink(Qbase, 0.5 * (lo + hi))
print(f"Delta_0={float(delta_batch(Q0).mean()):.4f}", flush=True)

rhos = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.35]
sigmas = [0.0, 0.05, 0.16]
rows = []
for rho in rhos:
    for sigma in sigmas:
        Q = Q0.clone()
        for t in range(T):
            Q = grad_step_private(Q, eta, rho, sigma, gen=gen)
        Df = delta_batch(Q)
        rank, pr, H = span_metrics_batch(Q)
        rows.append(dict(rho=rho, sigma=sigma,
                         Delta=float(Df.mean()), Delta_sd=float(Df.std()),
                         PR=float(pr.mean()), rank=float(rank.mean()),
                         Hrank=float(H.mean()),
                         PR_per_Delta=float(pr.mean()) / max(Df.mean().item(), 1e-9),
                         P_below_eps=float((Df < eps_c).float().mean())))
        r = rows[-1]
        print(f"rho={rho:5.3f} s={sigma:4.2f} | D={r['Delta']:.3f}+-{r['Delta_sd']:.3f} "
              f"| PR={r['PR']:5.2f} rank={r['rank']:5.1f} H={r['Hrank']:5.2f} "
              f"| PR/D={r['PR_per_Delta']:5.2f}", flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e9_private.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e9_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
