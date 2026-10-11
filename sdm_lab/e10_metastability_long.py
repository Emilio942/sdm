"""E10: Metastability at weak coupling: does survival plateau (bistability)
        or keep decaying (eventual collapse)? T=1600, eta=0.1.
Also E11 (d-scaling of Delta_inf crossing) and E12 (eta-scan in consensus mode)
run in sequence by the chain runner.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, delta_batch, delta_estimate_batch,
                  grad_step, grad_step)

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(61)
d, k = 64, 8
mu = 3.6078
eps_c = 0.25 * mu

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

def calibrate(Qbase_slice, target):
    lo, hi = 0.0, 0.9995
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        if float(delta_batch(shrink(Qbase_slice, mid).unsqueeze(0))) > target: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

cells = [(16, 0.01, 384, 1600), (64, 0.01, 192, 1600), (16, 0.02, 384, 1600),
         (32, 0.015, 256, 1600)]
rows = []
for N, sigma, R, T in cells:
    Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    c = calibrate(Qb[0], 1.8)
    Q0 = shrink(Qb, c)
    Q = Q0.clone()
    surv = torch.ones(R, device=dev); curve = []
    for t in range(T + 1):
        if t % 25 == 0:
            De = delta_estimate_batch(Q, 4096, gen)
            surv = surv * (De >= eps_c).float()
            curve.append(float(surv.mean()))
        if t < T:
            Q = grad_step(Q, 0.1, sigma, gen=gen)
    rows.append(dict(N=N, sigma=sigma, R=R, T=T, P_surv=float(surv.mean()),
                     curve=";".join(f"{v:.4f}" for v in curve)))
    print(f"N={N:3d} s={sigma:5.3f} T={T} P_surv={rows[-1]['P_surv']:.4f} "
          f"(half-life check: surv[600]={curve[24]:.4f} surv[1200]={curve[48]:.4f})", flush=True)
    pd.DataFrame(rows).to_csv(f"{RES}/e10_metastability_long.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e10_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
