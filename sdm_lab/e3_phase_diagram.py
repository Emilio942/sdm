"""E3 (efficient): phase diagram (sigma, N) under consensus-coupled Grassmannian SGD.

Per cell: R replicates, T steps; per track estimate Delta from random pairs
(unbiased), record min_t and max_t per replicate; final exact Delta + span metrics.

Key quantities:
  P_collapse = P(min_t Delta_t < eps_c)      P_diverge = P(max_t Delta_t > delta_m)
  Delta_inf (final), PR/rank (effective span), collapse time distribution.
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
os.makedirs(RES, exist_ok=True)
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(23)

d, k, eta, T = 64, 8, 0.3, 200
track_every, npairs = 5, 2048
R_of_N = {4: 1024, 8: 1024, 16: 512, 32: 384, 64: 192, 128: 96, 256: 48, 512: 24}

A = haar_sample(200_000, d, k, dev); B = haar_sample(200_000, d, k, dev)
mu_haar = float(geodesic_dist(A, B).mean()); del A, B
eps_c, delta_m = 0.25 * mu_haar, 0.90 * mu_haar
print(f"mu_Haar={mu_haar:.4f}  eps_c={eps_c:.4f}  delta_m={delta_m:.4f}", flush=True)

sigmas = [0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.07, 0.1, 0.14, 0.2, 0.3, 0.5]
Ns = [4, 8, 16, 32, 64, 128, 256, 512]

rows = []
for N in Ns:
    R = R_of_N[N]
    Q0 = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    for sigma in sigmas:
        Q = Q0.clone()
        Dmin = torch.full((R,), float("inf"), device=dev)
        Dmax = torch.full((R,), float("-inf"), device=dev)
        tcoll = torch.full((R,), -1.0, device=dev)
        for t in range(T + 1):
            if t % track_every == 0:
                De = delta_estimate_batch(Q, npairs, gen)
                Dmin = torch.minimum(Dmin, De)
                newcoll = (De < eps_c) & (tcoll < 0)
                tcoll[newcoll] = float(t)
                Dmax = torch.maximum(Dmax, De)
            if t < T:
                Q = grad_step(Q, eta, sigma, gen=gen)
        Df = delta_batch(Q)
        rank, pr, H = span_metrics_batch(Q)
        rows.append(dict(
            N=N, sigma=sigma, R=R,
            Delta_mean=float(Df.mean()), Delta_sd=float(Df.std()),
            Delta_p05=float(torch.quantile(Df, 0.05)),
            Delta_p95=float(torch.quantile(Df, 0.95)),
            P_collapse=float((Dmin < eps_c).float().mean()),
            P_diverge=float((Dmax > delta_m).float().mean()),
            t_collapse_med=float(tcoll[tcoll >= 0].median()) if (tcoll >= 0).any() else -1.0,
            PR=float(pr.mean()), rank=float(rank.mean()),
        ))
        r = rows[-1]
        print(f"N={N:4d} s={sigma:5.3f} R={R:5d} | D={r['Delta_mean']:6.3f}+-{r['Delta_sd']:5.3f} "
              f"| Pc={r['P_collapse']:5.3f} Pd={r['P_diverge']:5.3f} tc={r['t_collapse_med']:6.1f} "
              f"| PR={r['PR']:6.2f} rank={r['rank']:5.1f}", flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e3_phase.csv", index=False)

json.dump(dict(mu_haar=mu_haar, eps_c=eps_c, delta_m=delta_m, d=d, k=k, eta=eta,
               T=T, wall_s=time.time() - t0), open(f"{RES}/e3_meta.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
