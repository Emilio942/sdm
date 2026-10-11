"""E3b: The Omega* phase diagram in the problem's own coordinates (Delta_0, N, sigma).

Initial condition: shrunk-Haar ensembles calibrated to a target initial diversity
Delta_0 INSIDE the admissible band (calibration per (Delta_0,N) cell by bisection
on the shrink coefficient toward a common core subspace).

Per cell (Delta_0, N, sigma): R replicates of consensus-Grassmannian-SGD; record
  P_collapse = P(min_t Delta_t < eps_c), P_diverge = P(max_t Delta_t > delta_m),
  collapse time, Delta_inf, PR_T, rank_T.
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

d, k, eta, T = 64, 8, 0.3, 160
track_every, npairs = 10, 1024
R_of_N = {8: 384, 16: 256, 32: 192, 64: 128, 128: 64, 256: 32, 512: 16}

A = haar_sample(200_000, d, k, dev); B = haar_sample(200_000, d, k, dev)
mu_haar = float(geodesic_dist(A, B).mean()); del A, B
eps_c, delta_m = 0.25 * mu_haar, 0.90 * mu_haar
print(f"mu_Haar={mu_haar:.4f} eps_c={eps_c:.4f} delta_m={delta_m:.4f}", flush=True)

W = haar_sample(1, d, k, dev, gen)[0]        # common core for the shrink init

def shrink(Qbase, c):
    X = math.sqrt(max(1e-12, 1 - c * c)) * Qbase + c * W.unsqueeze(0)
    return torch.linalg.qr(X).values if False else torch.linalg.qr(X)[0]

def calibrate(Qbase, target):
    lo, hi = 0.0, 0.9995
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        val = float(delta_batch(shrink(Qbase, mid).unsqueeze(0)))
        if val > target: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

Delta0s = [1.0, 1.8, 2.6]
Ns = [8, 16, 32, 64, 128, 256, 512]
sigmas = [0.02, 0.05, 0.1, 0.16, 0.25]

rows = []
for D0t in Delta0s:
    for N in Ns:
        R = R_of_N[N]
        Qbase = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
        # calibrate shrink on a thin slice for speed, apply same c to all reps
        c = calibrate(Qbase[0], D0t)
        Q0 = shrink(Qbase, c)
        D0 = delta_batch(Q0)
        for sigma in sigmas:
            Q = Q0.clone()
            Dmin = torch.full((R,), float("inf"), device=dev)
            Dmax = torch.full((R,), float("-inf"), device=dev)
            tcoll = torch.full((R,), -1.0, device=dev)
            for t in range(T + 1):
                if t % track_every == 0:
                    De = delta_estimate_batch(Q, npairs, gen)
                    Dmin = torch.minimum(Dmin, De)
                    Dmax = torch.maximum(Dmax, De)
                    hit = (De < eps_c) & (tcoll < 0)
                    tcoll[hit] = float(t)
                if t < T:
                    Q = grad_step(Q, eta, sigma, gen=gen)
            Df = delta_batch(Q)
            rank, pr, H = span_metrics_batch(Q)
            rows.append(dict(
                Delta0_target=D0t, c_shrink=c, N=N, sigma=sigma, R=R,
                Delta0=float(D0.mean()),
                Delta_T=float(Df.mean()), Delta_T_sd=float(Df.std()),
                P_collapse=float((Dmin < eps_c).float().mean()),
                P_diverge=float((Dmax > delta_m).float().mean()),
                P_admissible=float(((Dmin >= eps_c) & (Dmax <= delta_m)).float().mean()),
                t_collapse_med=float(tcoll[tcoll >= 0].median()) if (tcoll >= 0).any() else -1.0,
                PR_T=float(pr.mean()), rank_T=float(rank.mean()),
            ))
            r = rows[-1]
            print(f"D0={D0t:.2f}(c={c:.3f}) N={N:4d} s={sigma:5.3f} | "
                  f"D_T={r['Delta_T']:6.3f}+-{r['Delta_T_sd']:5.3f} | "
                  f"Pc={r['P_collapse']:5.3f} Pd={r['P_diverge']:5.3f} "
                  f"Padm={r['P_admissible']:5.3f} tc={r['t_collapse_med']:6.1f} | "
                  f"PR={r['PR_T']:6.2f} rank={r['rank_T']:5.1f}", flush=True)
            pd.DataFrame(rows).to_csv(f"{RES}/e3b_omega.csv", index=False)

json.dump(dict(mu_haar=mu_haar, eps_c=eps_c, delta_m=delta_m, d=d, k=k, eta=eta,
               T=T, wall_s=time.time() - t0), open(f"{RES}/e3b_meta.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
