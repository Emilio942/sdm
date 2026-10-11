"""E16: CORE consensus measurements with the CORRECTED operator (einsum fix).

Replaces e2b/e8 core numbers. Everything batched-consensus from before this fix
is superseded.
P1: sigma=0 contraction rate.
P2: Delta_inf(sigma) backbone at N=64 and N=128 (T=400, converged).
P3: unbiased boundary probabilities at N=128 (exact Delta_T, Wilson CIs).
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
gen = torch.Generator(device=dev); gen.manual_seed(200)
d, k, eta = 64, 8, 0.3
mu = 3.6078
eps_c, delta_m = 0.25 * mu, 0.90 * mu

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

def calib(Q0_slice, target, iters=12):
    lo, hi = 0.0, 0.9995
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if float(delta_batch(shrink(Q0_slice, mid).unsqueeze(0))) > target: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

def wilson(p, n, z=1.96):
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, ctr - hw), min(1.0, ctr + hw))

print("=" * 70); print("P1: sigma=0 contraction (corrected)")
rows = []
for eta_ in (0.1, 0.3):
    for N in (16, 64):
        R = 48
        Q = shrink(haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k), calib(haar_sample(1 * N, d, k, dev, gen)[0], 1.8, 10) if False else 0.8847)
        # re-calibrate properly per config
        Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
        c = calib(Qb[0], 1.8)
        Q = shrink(Qb, c)
        D = [float(delta_batch(Q).mean())]
        for t in range(60):
            Q = grad_step(Q, eta_, 0.0, gen=gen)
            if (t + 1) % 10 == 0:
                D.append(float(delta_batch(Q).mean()))
        arr = np.array(D); rr = arr / arr[0]
        rate = -np.polyfit(np.arange(len(rr))[1:], np.log(rr[1:]), 1)[0]
        rows.append(dict(eta=eta_, N=N, rate=rate, rate_over_eta=rate / eta_))
        print(f"  eta={eta_} N={N:4d} rate={rate:.4f} rate/eta={rate/eta_:.3f}", flush=True)
pd.DataFrame(rows).to_csv(f"{RES}/e16_P1_contraction.csv", index=False)

print("=" * 70); print("P2/P3: backbone + boundary (corrected)")
rows = []
sigmas = [(0.02, 400, 192), (0.04, 400, 192), (0.06, 400, 192), (0.09, 400, 192),
          (0.12, 500, 256), (0.14, 500, 256), (0.16, 500, 256), (0.18, 500, 256),
          (0.22, 400, 192), (0.28, 400, 192), (0.36, 300, 128), (0.45, 300, 128)]
N = 128
Qb = haar_sample(256 * N, d, k, dev, gen).reshape(256, N, d, k)
c = calib(Qb[0], 1.8)
Q0 = shrink(Qb, c)
for sigma, T, R in sigmas:
    Q = Q0[:R].clone()
    for t in range(T):
        Q = grad_step(Q, eta, sigma, gen=gen)
    Df = delta_batch(Q)
    rank, pr, H = span_metrics_batch(Q)
    Pc = float((Df < eps_c).float().mean()); Pd = float((Df > delta_m).float().mean())
    wc, wd = wilson(Pc, R), wilson(Pd, R)
    rows.append(dict(sigma=sigma, T=T, R=R, Delta_T=float(Df.mean()),
                     Delta_T_sd=float(Df.std()), ratio=float(Df.mean()) / sigma,
                     P_collapse=Pc, Pc_lo=wc[0], Pc_hi=wc[1],
                     P_diverge=Pd, Pd_lo=wd[0], Pd_hi=wd[1],
                     PR=float(pr.mean()), rank=float(rank.mean())))
    r = rows[-1]
    print(f"s={sigma:5.3f} T={T} R={R} | D={r['Delta_T']:.4f}+-{r['Delta_T_sd']:.4f} "
          f"ratio={r['ratio']:.2f} | Pc={Pc:.3f}[{wc[0]:.2f},{wc[1]:.2f}] "
          f"Pd={Pd:.3f} | PR={r['PR']:.2f}", flush=True)
    pd.DataFrame(rows).to_csv(f"{RES}/e16_backbone.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e16_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
