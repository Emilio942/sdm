"""E15: Finite-size scaling of the synchronized collapse (cliff).
eta=0.3, sigma=0.1 (binding transition zone), Delta_0=1.8.
Collapse time = first track where low-noise Delta estimate < eps_c
(4096 pairs, track every 10 -> SE~0.006, bias negligible).
Look for scaling collapse of survival curves S(t; N) = F(t / t*(N)).
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import haar_sample, geodesic_dist, delta_batch, delta_estimate_batch, grad_step

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(111)
d, k, eta, sigma, T = 64, 8, 0.3, 0.1, 400
eps_c = 0.25 * 3.6078

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

rows = []
tgrid = list(range(0, T + 1, 10))
for N, R in ((16, 384), (32, 384), (64, 256), (128, 256), (256, 192)):
    Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    lo, hi = 0.0, 0.9995
    for _ in range(10):
        mid = 0.5 * (lo + hi)
        if float(delta_batch(shrink(Qb[0], mid).unsqueeze(0))) > 1.8: lo = mid
        else: hi = mid
    Q = shrink(Qb, 0.5 * (lo + hi))
    alive = torch.ones(R, device=dev)
    tc = torch.full((R,), float("nan"), device=dev)
    surv = []
    for t in range(T + 1):
        if t % 10 == 0:
            De = delta_estimate_batch(Q, 4096, gen)
            newly = (De < eps_c) & (tc != tc)
            tc[newly] = float(t)
            alive = alive * (De >= eps_c).float()
            surv.append(float(alive.mean()))
        if t < T:
            Q = grad_step(Q, eta, sigma, gen=gen)
    tcl = tc[tc == tc]
    rows.append(dict(N=N, R=R,
                     t_mean=float(tcl.mean()) if len(tcl) else float("nan"),
                     t_med=float(tcl.median()) if len(tcl) else float("nan"),
                     t_sd=float(tcl.std()) if len(tcl) else float("nan"),
                     P_surv=float(alive.mean()),
                     surv=";".join(f"{v:.4f}" for v in surv)))
    r = rows[-1]
    cv = r["t_sd"] / r["t_mean"] if r["t_mean"] == r["t_mean"] else float("nan")
    print(f"N={N:4d} R={R} | t_mean={r['t_mean']:6.1f} t_sd={r['t_sd']:6.1f} "
          f"CV={cv:.3f} P_surv={r['P_surv']:.4f}", flush=True)
    pd.DataFrame(rows).to_csv(f"{RES}/e15_cliff_scaling.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e15_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
