"""E6: (d,k)-scaling check of the mean-field collapse threshold
       sigma_c^MF(k) = eps_c(k) * sqrt(eta(2-eta)/(2k)),  eps_c(k) = 0.25*mu_Haar(k).
   Fine sigma scan at N=128 (binding-saturated regime), Delta_0 = 1.2*eps_c(k).
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
gen = torch.Generator(device=dev); gen.manual_seed(77)

d, eta, T, track_every, npairs = 64, 0.3, 160, 10, 1024
N, R = 128, 96

def shrink(Q, c, W):
    X = math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0)
    return torch.linalg.qr(X)[0]

rows = []
for k in (4, 8, 16):
    A = haar_sample(200_000, d, k, dev); B = haar_sample(200_000, d, k, dev)
    mu = float(geodesic_dist(A, B).mean()); del A, B
    eps_c = 0.25 * mu
    sc_mf = eps_c * math.sqrt(eta * (2 - eta) / (2 * k))
    D0t = 1.2 * eps_c
    W = haar_sample(1, d, k, dev, gen)[0]
    Qbase = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    lo, hi = 0.0, 0.9995
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        if float(delta_batch(shrink(Qbase[0], mid, W).unsqueeze(0))) > D0t: lo = mid
        else: hi = mid
    Q0 = shrink(Qbase, 0.5 * (lo + hi), W)
    fac = math.sqrt(2 * k / (eta * (2 - eta)))
    sigmas = sorted({round(sc_mf * f, 4) for f in
                     (0.55, 0.7, 0.85, 0.95, 1.05, 1.15, 1.3, 1.5)})
    print(f"k={k}: mu={mu:.3f} eps_c={eps_c:.3f} sigma_c_MF={sc_mf:.4f} "
          f"Delta_inf/sigma factor={fac:.2f} sigmas={sigmas}", flush=True)
    for sigma in sigmas:
        Q = Q0.clone()
        Dmin = torch.full((R,), float("inf"), device=dev)
        for t in range(T + 1):
            if t % track_every == 0:
                Dmin = torch.minimum(Dmin, delta_estimate_batch(Q, npairs, gen))
            if t < T:
                Q = grad_step(Q, eta, sigma, gen=gen)
        Df = delta_batch(Q)
        pc = float((Dmin < eps_c).float().mean())
        rows.append(dict(k=k, mu_haar=mu, eps_c=eps_c, sigma_c_mf=sc_mf, sigma=sigma,
                         ratio=sigma / sc_mf, P_collapse=pc, Delta_T=float(Df.mean()),
                         Delta_over_sigma=float(Df.mean()) / sigma))
        r = rows[-1]
        print(f"  k={k} s={sigma:.4f} (s/sc_mf={r['ratio']:.2f}) Pc={pc:.3f} "
              f"D_T={r['Delta_T']:.3f} D/s={r['Delta_over_sigma']:.2f}", flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e6_scaling.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e6_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
