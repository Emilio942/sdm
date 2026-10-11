"""E4: Does Grassmannian-packing initialization beat random initialization?

Research-log claims (cycles 10, 1273): ETF / optimal-packing initial ensembles are
optimal for span dimension and diversity robustness. Test at MATCHED initial mean
diversity Delta_0, under identical Phi (consensus SGD, eta=0.3, sigma in the
admissible window):

  init A "shrunk-random":  V_i = orth(c*W + sqrt(1-c^2) G_i)   (common practice)
  init B "spread-optimal": local min of ||S||_F^2, S=sum P_i (eigenvalue
                           flattening => maximal span uniformity), then rescaled
                           to match Delta_0 via the same shrink map.
  control: iid Haar (Delta_0 ~= 3.61 > delta_m: inadmissible at t=0!)

Measured: P_collapse, min_t Delta, d_min(t) trajectory, PR(T), rank(T).
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, delta_batch, delta_estimate_batch,
                  span_metrics_batch, grad_step, min_pairwise_batch, projector_sum)

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RES, exist_ok=True)
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(101)

d, k, eta, T, track_every, npairs = 64, 8, 0.3, 200, 10, 1024
N, R = 32, 384

A = haar_sample(200_000, d, k, dev); B = haar_sample(200_000, d, k, dev)
mu_haar = float(geodesic_dist(A, B).mean()); del A, B
eps_c, delta_m = 0.25 * mu_haar, 0.90 * mu_haar
print(f"mu_Haar={mu_haar:.4f} eps_c={eps_c:.3f} delta_m={delta_m:.3f}", flush=True)

# ---------------- packing: minimize ||S||_F^2 over configurations (flattens spectrum)
def pack(N, d, k, steps=400, lr=0.5):
    Q = haar_sample(N, d, k, dev, gen)
    for it in range(steps):
        S = projector_sum(Q) / N
        G = torch.einsum("de,ndk->ndk", S, Q)
        G = G - torch.matmul(Q, torch.matmul(Q.transpose(1, 2), G))   # tangent
        Q, _ = torch.linalg.qr(Q - lr * G)
        if (it + 1) % 100 == 0:
            ev = torch.linalg.eigvalsh(projector_sum(Q) / N)
            print(f"    pack it={it+1} eigs[min,max]=[{ev[0]:.4f},{ev[-1]:.4f}] "
                  f"target={k/d:.4f}", flush=True)
    return Q

Qpack = pack(N, d, k)

# ---------------- shrink map toward common W to control Delta_0
W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Qbase, c):
    X = math.sqrt(max(1e-12, 1 - c * c)) * Qbase + c * W.unsqueeze(0)
    Qr, _ = torch.linalg.qr(X)
    return Qr

def calibrate_c(Qbase, target):
    lo, hi = 0.0, 0.999
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        val = float(delta_batch(shrink(Qbase, mid).unsqueeze(0)))
        if val > target: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

target_D0 = 1.6
_b1 = haar_sample(R * N, d, k, dev, gen)
c_rand = calibrate_c(_b1[:N], target_D0)          # calibrate on ONE swarm slice
c_pack = calibrate_c(Qpack, target_D0)
print(f"calibrated shrink: c_rand={c_rand:.4f} c_pack={c_pack:.4f}", flush=True)

inits = {
    "shrunk_random": shrink(haar_sample(R * N, d, k, dev, gen), c_rand).reshape(R, N, d, k),
    "packing_shrunk": shrink(Qpack.unsqueeze(0).expand(R, -1, -1, -1).contiguous(), c_pack),
    "haar_raw": haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k),
}

sigmas = [0.10, 0.16]
rows = []
for name, Q0 in inits.items():
    D0 = delta_batch(Q0)
    d0_min = min_pairwise_batch(Q0)
    for sigma in sigmas:
        Q = Q0.clone()
        Dmin = torch.full((R,), float("inf"), device=dev)
        dmin_t = []
        for t in range(T + 1):
            if t % track_every == 0:
                Dmin = torch.minimum(Dmin, delta_estimate_batch(Q, npairs, gen))
                if R <= 8:
                    dmin_t.append(float(min_pairwise_batch(Q).min()))
            if t < T:
                Q = grad_step(Q, eta, sigma, gen=gen)
        Df = delta_batch(Q)
        rank, pr, H = span_metrics_batch(Q)
        rows.append(dict(init=name, sigma=sigma,
                         D0_mean=float(D0.mean()), D0_sd=float(D0.std()),
                         d0_min=float(d0_min.min()),
                         P_collapse=float((Dmin < eps_c).float().mean()),
                         Delta_T=float(Df.mean()), Delta_T_sd=float(Df.std()),
                         PR_T=float(pr.mean()), rank_T=float(rank.mean()),
                         dmin_traj=";".join(f"{v:.3f}" for v in dmin_t)))
        r = rows[-1]
        print(f"{name:16s} s={sigma:5.3f} | D0={r['D0_mean']:.3f}+-{r['D0_sd']:.3f} "
              f"d0min={r['d0_min']:.3f} | Pc={r['P_collapse']:5.3f} | "
              f"DT={r['Delta_T']:.3f} PR={r['PR_T']:.2f} rank={r['rank_T']:.1f}", flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e4_init.csv", index=False)

json.dump(dict(c_rand=c_rand, c_pack=c_pack, target=target_D0, N=N, d=d, k=k,
               mu_haar=mu_haar, wall_s=time.time() - t0),
          open(f"{RES}/e4_meta.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
