"""E20 (final gap closer): k-scaling of the collapse edge with the CORRECTED operator.
k in {4,16}, d=64, eta=0.3, N=128: measure where Delta_inf(sigma) crosses eps_c(k).
Prediction: sigma_c(k) = eps_c(k)/fac(k), fac = sqrt(2k(1-k/d)/(eta(2-eta))).
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import haar_sample, geodesic_dist, delta_batch, grad_step

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(500)
d, eta, N, R, T = 64, 0.3, 128, 192, 300

rows = []
for k in (4, 16):
    A = haar_sample(150_000, d, k, dev); B = haar_sample(150_000, d, k, dev)
    mu = float(geodesic_dist(A, B).mean()); del A, B
    eps_c = 0.25 * mu
    fac = math.sqrt(2 * k * (1 - k / d) / (eta * (2 - eta)))
    sig_c = eps_c / fac
    W = haar_sample(1, d, k, dev, gen)[0]
    Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    lo, hi = 0.0, 0.9995
    tgt = 1.2 * eps_c
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        X = math.sqrt(max(1e-12, 1 - mid * mid)) * Qb[0] + mid * W.unsqueeze(0)
        if float(delta_batch(torch.linalg.qr(X)[0].unsqueeze(0))) > tgt: lo = mid
        else: hi = mid
    Q0 = torch.linalg.qr(math.sqrt(max(1e-12, 1 - (0.5*(lo+hi))**2)) * Qb + (0.5*(lo+hi)) * W.unsqueeze(0))[0]
    sigmas = sorted({round(sig_c * f, 4) for f in (0.82, 0.91, 1.0, 1.09, 1.18)})
    print(f"k={k}: mu={mu:.4f} eps_c={eps_c:.4f} fac={fac:.3f} pred sig_c={sig_c:.4f}", flush=True)
    for sigma in sigmas:
        Q = Q0.clone()
        for t in range(T):
            Q = grad_step(Q, eta, sigma, gen=gen)
        Df = delta_batch(Q)
        rows.append(dict(k=k, mu=mu, eps_c=eps_c, fac=fac, sigma_c_pred=sig_c, sigma=sigma,
                         Delta=float(Df.mean()), Delta_sd=float(Df.std()),
                         crossing_gap=float(Df.mean()) - eps_c))
        r = rows[-1]
        print(f"  k={k} s={sigma:.4f} D={r['Delta']:.4f}+-{r['Delta_sd']:.4f} "
              f"gap_to_eps_c={r['crossing_gap']:+.4f}", flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e20_kscaling_corrected.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e20_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
