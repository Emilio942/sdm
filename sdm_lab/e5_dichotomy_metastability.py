"""E5: (a) Clean U-statistic dichotomy with quantitative Hoeffding validation
         (task-attractor mode => iid particles at stationarity);
       (b) metastability & collapse-time under consensus coupling at small eta.

Theory (Hoeffding 1948): for iid V_1..V_N ~ mu and kernel h,
  Var(Delta) = 4(N-2)/(N(N-1)) * zeta_1 + 2/(N(N-1)) * zeta_2
  zeta_1 = Var_{V~mu}( h_1(V) ),  h_1(V) = E_{W~mu}[ h(V,W) ],  zeta_2 = Var(h).
  - mu = Haar: h_1 constant (rotational invariance) => zeta_1 = 0 => Var ~ 2 zeta_2/N^2.
  - mu = stationary near attractor: zeta_1 > 0 => Var ~ 4 zeta_1 / N.
Both intercepts and slopes are predicted => sharp numerical test.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, delta_batch, delta_estimate_batch,
                  grad_step, span_metrics_batch)

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RES, exist_ok=True)
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(5)
d, k = 64, 8

# ---------------------------------------------------------------- (a) dichotomy
W = haar_sample(1, d, k, dev, gen)[0]

def stationary_samples_task(M, eta, sigma, T=300, chunk=200_000):
    """iid stationary samples under task-attractor SGD: returns (m,d,k)."""
    Q = haar_sample(M, d, k, dev, gen)
    for t in range(T):
        Sq = torch.matmul((W @ W.t()).unsqueeze(0), Q)                # (M,d,k)
        G = Sq - torch.matmul(Q, torch.matmul(Q.transpose(1, 2), Sq))
        Z = torch.randn(M, d, k, device=dev, generator=gen) / math.sqrt(d)
        Z = Z - torch.matmul(Q, torch.matmul(Q.transpose(1, 2), Z))
        X = Q + eta * G + sigma * Z
        Q, _ = torch.linalg.qr(X)
    return Q

sigma_stat = 0.05
Qstat = stationary_samples_task(60_000, eta=0.3, sigma=sigma_stat, T=60)

# zeta_1, zeta_2 from the stationary law
M = 60_000
V = Qstat[:M]
Widx = torch.randint(0, M, (M,), device=dev, generator=gen)
h = geodesic_dist(V, Qstat[Widx])                     # conditional MC of h1 inner mean
# proper h1: average over n_inner draws per V
n_inner = 32
h1_parts = []
for r0 in range(0, M, 25_000):
    r1 = min(r0 + 25_000, M)
    idx = torch.randint(0, M, (r1 - r0, n_inner), device=dev, generator=gen)
    h1_parts.append(geodesic_dist(V[r0:r1].unsqueeze(1), Qstat[idx]).mean(dim=1))
    del idx
h1 = torch.cat(h1_parts)
zeta1 = float(h1.var())
zeta2 = float(h.var())
print(f"[dichotomy] zeta1={zeta1:.5f} zeta2={zeta2:.5f} (sigma={sigma_stat})", flush=True)

rows = []
for N in (4, 8, 16, 32, 64, 128, 256):
    R = {4: 12000, 8: 7000, 16: 3500, 32: 1800, 64: 900, 128: 450, 256: 225}[N]
    idxN = torch.randint(0, M, (R, N), device=dev, generator=gen)
    vals = []
    for r0 in range(0, R, 32):
        r1 = min(r0 + 32, R)
        Qb = Qstat[idxN[r0:r1]]                        # (r1-r0, N, d, k)
        vals.append(delta_batch(Qb))
    vals = torch.cat(vals)
    pred_var = 4 * (N - 2) / (N * (N - 1)) * zeta1 + 2 / (N * (N - 1)) * zeta2
    rows.append(dict(N=N, R=R, mean=float(vals.mean()), var=float(vals.var()),
                     pred_var=pred_var))
    print(f"[dichotomy] N={N:4d} R={R:6d} mean={rows[-1]['mean']:.4f} "
          f"var={rows[-1]['var']:.3e} pred={pred_var:.3e} "
          f"ratio={rows[-1]['var']/pred_var:.3f}", flush=True)
df = pd.DataFrame(rows); df.to_csv(f"{RES}/e5_dichotomy.csv", index=False)
slope = np.polyfit(np.log(df.N), np.log(df["var"]), 1)[0]
print(f"[dichotomy] slope={slope:.3f} (theory -1); Haar control was -2.04", flush=True)

# ---------------------------------------------------------------- (b) metastability
print("[metastability] consensus eta=0.1: survival curves", flush=True)
d_, k_ = d, k
eta_m = 0.1
Tm, track = 800, 20
eps_c = 0.25 * 3.6079
rows = []
for N in (16, 64, 256):
    R = {16: 192, 64: 96, 256: 32}[N]
    Q0 = haar_sample(R * N, d_, k_, dev, gen).reshape(R, N, d_, k_)
    for sigma in (0.01, 0.02, 0.03):
        Q = Q0.clone()
        surv = torch.ones(R, device=dev)
        curve = []
        for t in range(Tm + 1):
            if t % track == 0:
                De = delta_estimate_batch(Q, 2048, gen)
                surv = surv * (De >= eps_c).float()
                curve.append(float(surv.mean()))
            if t < Tm:
                Q = grad_step(Q, eta_m, sigma, gen=gen)
        rows.append(dict(N=N, sigma=sigma, P_surv_T=float(surv.mean()),
                         curve=";".join(f"{v:.4f}" for v in curve)))
        print(f"[metastability] N={N:4d} s={sigma:5.3f} P_surv(T={Tm})={rows[-1]['P_surv_T']:.4f}",
              flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e5_metastability.csv", index=False)

json.dump(dict(zeta1=zeta1, zeta2=zeta2, slope=slope, sigma_stat=sigma_stat,
               wall_s=time.time() - t0), open(f"{RES}/e5_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
