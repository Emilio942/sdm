"""E11 (runs after E10 in chain): d-scaling of the stationary diversity law.
Consensus mode, k=8, N=128, eta=0.3: measure Delta_inf(sigma) for d in {32,128,256}
and locate the crossing sigma_c where Delta_inf = eps_c(d) = 0.25*mu_Haar(d).
Theory: fac(d) = sqrt(2k(1-k/d)/(eta(2-eta))) =>
  sigma_c(d) = eps_c(d) / fac(d);  mu_Haar(d) from 400k-pair MC.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, delta_batch, span_metrics_batch,
                  grad_step)

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(71)
k, eta, N, R, T = 8, 0.3, 128, 96, 300

W = haar_sample(1, d, k, dev, gen)[0] if False else None
rows = []
for d in (32, 128, 256):
    A = haar_sample(150_000, d, k, dev); B = haar_sample(150_000, d, k, dev)
    mu = float(geodesic_dist(A, B).mean()); del A, B
    eps_c = 0.25 * mu
    fac = math.sqrt(2 * k * (1 - k / d) / (eta * (2 - eta)))
    sig_c_mf = eps_c / fac
    sigmas = sorted({round(sig_c_mf * f, 4) for f in (0.7, 0.85, 1.0, 1.15, 1.3, 1.5)})
    W = haar_sample(1, d, k, dev, gen)[0]
    Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    lo, hi = 0.0, 0.9995
    tgt = 1.2 * eps_c
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        X = math.sqrt(max(1e-12, 1 - mid * mid)) * Qb[0] + mid * W.unsqueeze(0)
        if float(delta_batch(torch.linalg.qr(X)[0].unsqueeze(0))) > tgt: lo = mid
        else: hi = mid
    c = 0.5 * (lo + hi)
    Q0 = torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Qb + c * W.unsqueeze(0))[0]
    print(f"d={d}: mu={mu:.4f} eps_c={eps_c:.4f} fac={fac:.3f} sig_c_MF={sig_c_mf:.4f} "
          f"sigmas={sigmas}", flush=True)
    for sigma in sigmas:
        Q = Q0.clone()
        for t in range(T):
            Q = grad_step(Q, eta, sigma, gen=gen)
        Df = delta_batch(Q)
        rank, pr, H = span_metrics_batch(Q)
        rows.append(dict(d=d, mu_haar=mu, eps_c=eps_c, fac=fac, sigma_c_mf=sig_c_mf,
                         sigma=sigma, ratio=sigma / sig_c_mf,
                         Delta=float(Df.mean()), Delta_sd=float(Df.std()),
                         PR=float(pr.mean()), rank=float(rank.mean()),
                         P_below_eps=float((Df < eps_c).float().mean())))
        r = rows[-1]
        print(f"  d={d} s={sigma:.4f} (r={r['ratio']:.2f}) D={r['Delta']:.4f}"
              f"+-{r['Delta_sd']:.4f} eps_c={eps_c:.3f} "
              f"Pb={r['P_below_eps']:.3f} PR={r['PR']:.2f} rank={r['rank']:.0f}", flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e11_dscaling.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e11_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
