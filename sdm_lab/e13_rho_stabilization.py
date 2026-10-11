"""E13 (best bet): Does private-data diversity STABILIZE the weak-coupling regime?

E10 showed: at eta=0.1, noise CATALYZES collapse (survival decreases with sigma;
geometric decay -> collapse certain). E9 showed private streams (rho) are an
alternative diversity source. Hypothesis: replacing sigma by rho removes the
fluctuation-driven nucleation channel -> survival plateau instead of decay.

Design: eta=0.1, matched-<nothing> (mechanism comparison at equal weight),
N in {16,64}, R=256, T=1200, track every 25 with low-noise Delta (4096 pairs).
Cells: (sigma, rho) in {(0.01,0), (0,0.05), (0,0.1), (0.01,0.05)}.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import haar_sample, geodesic_dist, delta_batch, delta_estimate_batch, grad_step_private

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(91)
d, k, eta, T = 64, 8, 0.1, 1200
eps_c = 0.25 * 3.6078

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

rows = []
for N, R in ((16, 256), (64, 256)):
    Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    lo, hi = 0.0, 0.9995
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        if float(delta_batch(shrink(Qb[0], mid).unsqueeze(0))) > 1.8: lo = mid
        else: hi = mid
    Q0 = shrink(Qb, 0.5 * (lo + hi))
    for sigma, rho in ((0.01, 0.0), (0.0, 0.05), (0.0, 0.1), (0.01, 0.05), (0.03, 0.0), (0.0, 0.2)):
        Q = Q0.clone()
        surv = torch.ones(R, device=dev); curve = []
        Dfin = None
        for t in range(T + 1):
            if t % 25 == 0:
                De = delta_estimate_batch(Q, 4096, gen)
                surv = surv * (De >= eps_c).float()
                curve.append(float(surv.mean()))
            if t < T:
                Q = grad_step_private(Q, eta, rho, sigma, gen=gen)
        Df = delta_batch(Q)
        rows.append(dict(N=N, sigma=sigma, rho=rho, R=R, T=T,
                         P_surv=float(surv.mean()), Delta_T=float(Df.mean()),
                         curve=";".join(f"{v:.4f}" for v in curve)))
        print(f"N={N:3d} s={sigma:4.2f} rho={rho:4.2f} | P_surv({T})={rows[-1]['P_surv']:.4f} "
              f"surv[600]={curve[24]:.4f} surv[1200]={curve[-1]:.4f} | D_T={rows[-1]['Delta_T']:.3f}",
              flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e13_rho_stabilization.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e13_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
