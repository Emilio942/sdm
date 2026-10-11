"""E12 (runs after E11 in chain): eta-scan in consensus mode.
Tests the backbone factor fac = sqrt(2k(1-k/d)/(eta(2-eta))) * (1 + finite-N
inflation) and the retraction eta^2 effect, at k=8, d=64, N=128.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import haar_sample, geodesic_dist, delta_batch, span_metrics_batch, grad_step

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(81)
d, k, N, R, T = 64, 8, 128, 96, 300
mu = 3.6078
eps_c = 0.25 * mu

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

rows = []
for eta in (0.15, 0.45):
    fac = math.sqrt(2 * k * (1 - k / d) / (eta * (2 - eta)))
    sigmas = [0.05, 0.1, 0.15, 0.25]
    Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    lo, hi = 0.0, 0.9995
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        if float(delta_batch(shrink(Qb[0], mid).unsqueeze(0))) > 1.8: lo = mid
        else: hi = mid
    Q0 = shrink(Qb, 0.5 * (lo + hi))
    print(f"eta={eta}: fac={fac:.3f} sigmas={sigmas}", flush=True)
    for sigma in sigmas:
        # T scales with 1/eta for convergence
        Q = Q0.clone(); Tloc = int(T * 0.3 / eta)
        for t in range(Tloc):
            Q = grad_step(Q, eta, sigma, gen=gen)
        Df = delta_batch(Q)
        rank, pr, H = span_metrics_batch(Q)
        rows.append(dict(eta=eta, sigma=sigma, fac=fac, T=Tloc,
                         Delta=float(Df.mean()), Delta_sd=float(Df.std()),
                         ratio=float(Df.mean()) / sigma,
                         pred=float(sigma * fac), PR=float(pr.mean()),
                         rank=float(rank.mean())))
        r = rows[-1]
        print(f"  eta={eta} s={sigma:4.2f} T={Tloc} D={r['Delta']:.4f} "
              f"ratio={r['ratio']:.3f} pred={r['pred']:.4f} "
              f"ratio/pred={r['ratio']/fac:.3f} PR={r['PR']:.2f}", flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e12_etascan.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e12_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
