"""E19: corrected Omega* essentials — does Delta_0 still protect? (post-fix re-check)
Reduced grid: Delta_0 in {1.0, 2.6}, N in {16,128}, sigma in {0.10,0.13,0.16,0.19},
T=300, R=256/192. Collapse via exact Delta_T. Fast verify of the Delta_0-nucleation
claim under the corrected operator.
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
gen = torch.Generator(device=dev); gen.manual_seed(400)
d, k, eta, T = 64, 8, 0.3, 300
eps_c, delta_m = 0.25 * 3.6078, 0.90 * 3.6078

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

def calib(Q0_slice, target):
    lo, hi = 0.0, 0.9995
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        if float(delta_batch(shrink(Q0_slice, mid).unsqueeze(0))) > target: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

rows = []
for D0t in (1.0, 2.6):
    for N, R in ((16, 256), (128, 192)):
        Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
        c = calib(Qb[0], D0t)
        Q0 = shrink(Qb, c)
        for sigma in (0.10, 0.13, 0.16, 0.19):
            Q = Q0.clone()
            for t in range(T):
                Q = grad_step(Q, eta, sigma, gen=gen)
            Df = delta_batch(Q)
            rank, pr, H = span_metrics_batch(Q)
            rows.append(dict(Delta0=D0t, N=N, sigma=sigma, c=c,
                             Delta_T=float(Df.mean()), Delta_sd=float(Df.std()),
                             P_collapse=float((Df < eps_c).float().mean()),
                             P_diverge=float((Df > delta_m).float().mean()),
                             PR=float(pr.mean()), rank=float(rank.mean())))
            r = rows[-1]
            print(f"D0={D0t} N={N:4d} s={sigma:4.2f} | D_T={r['Delta_T']:.4f}+-{r['Delta_sd']:.4f} "
                  f"| Pc={r['P_collapse']:.3f} Pd={r['P_diverge']:.3f} | PR={r['PR']:.2f}",
                  flush=True)
            pd.DataFrame(rows).to_csv(f"{RES}/e19_omega_corrected.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e19_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
