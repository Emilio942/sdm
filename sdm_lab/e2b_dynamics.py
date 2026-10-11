"""E2b: swarm dynamics under the COVARIANT Grassmannian-SGD Phi.

  grad ascent on f(V)=<P_V, Sbar> with Sbar = swarm mean projector (consensus)
  + tangential noise of relative amplitude sigma.

P1: sigma=0 contraction rate of Delta(t); N-independence of normalized curve.
P2: Delta_inf(sigma, eta) fine grid in the interesting low-sigma regime.
P3: U-statistic dichotomy: Var(Delta) ~ N^s at stationarity vs Haar (s=-2).
P4: effective span (PR) collapse vs sigma at fixed N.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, delta_batch, geodesic_mean_batch,
                  span_metrics_batch, grad_step, pairwise_geodesic)

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RES, exist_ok=True)
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(7)

def init(R, N, d, k):
    return haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)

def run(Q0, T, eta, sigma, track_every=1):
    Q = Q0.clone()
    R, N, d, k = Q.shape
    tr = {"Delta": [], "rank": [], "PR": [], "H": []}
    def track():
        tr["Delta"].append(delta_batch(Q).cpu())
        r, pr, h = span_metrics_batch(Q)
        tr["rank"].append(r.cpu()); tr["PR"].append(pr.cpu()); tr["H"].append(h.cpu())
    track()
    for t in range(T):
        Q = grad_step(Q, eta, sigma, gen=gen)
        if (t + 1) % track_every == 0:
            track()
    return Q, {key: torch.stack(v, 1) for key, v in tr.items()}

d, k = 64, 8

print("=" * 72); print("P1: sigma=0 contraction rate")
rows = []
for eta in (0.05, 0.1, 0.3):
    for N in (16, 64, 256):
        R = 48
        _, tr = run(init(R, N, d, k), 40, eta, 0.0)
        D = tr["Delta"].mean(0).numpy()
        rr = D / D[0]
        rate = -np.polyfit(np.arange(1, len(rr)), np.log(rr[1:]), 1)[0]
        rows.append(dict(eta=eta, N=N, rate=rate, rate_over_eta=rate / eta))
        print(f"  eta={eta:4.2f} N={N:4d}  rate={rate:.4f}  rate/eta={rate/eta:.3f}  "
              f"D0={D[0]:.3f} DT={D[-1]:.2e}")
pd.DataFrame(rows).to_csv(f"{RES}/e2b_P1_contraction.csv", index=False)

print("=" * 72); print("P2: Delta_inf(sigma, eta)")
rows = []
T, burn = 200, 100
for eta in (0.1, 0.3):
    for sigma in (0.005, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.25, 0.4):
        R = 48
        _, tr = run(init(R, 64, d, k), T, eta, sigma, track_every=5)
        v = tr["Delta"][:, burn // 5:]
        rows.append(dict(eta=eta, sigma=sigma, Delta_inf=v.mean().item(), sd=v.std().item()))
        print(f"  eta={eta:.2f} sigma={sigma:5.3f}  Delta_inf={rows[-1]['Delta_inf']:.4f} "
              f"+- {rows[-1]['sd']:.4f}")
pd.DataFrame(rows).to_csv(f"{RES}/e2b_P2_stationary.csv", index=False)

print("=" * 72); print("P3: dichotomy Var(Delta) ~ N^s")
rows = []
for N in (16, 32, 64, 128, 256):
    Rr = {16: 6000, 32: 3000, 64: 1500, 128: 750, 256: 375}[N]
    _, tr = run(init(Rr, N, d, k), 60, 0.3, 0.05, track_every=60)
    v = tr["Delta"][:, -1].numpy()
    rows.append(dict(N=N, var=v.var(), mean=v.mean()))
    print(f"  N={N:4d} R={Rr:5d}  Var={v.var():.3e}  Var*N={v.var()*N:.3e}  mean={v.mean():.3f}")
df = pd.DataFrame(rows); df.to_csv(f"{RES}/e2b_P3_dichotomy.csv", index=False)
print(f"  slope = {np.polyfit(np.log(df.N), np.log(df['var']), 1)[0]:.3f}  (Haar was -2.04)")

print("=" * 72); print("P4: span collapse vs sigma (N=128)")
rows = []
for sigma in (0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2):
    R = 24
    _, tr = run(init(R, 128, d, k), 150, 0.3, sigma, track_every=50)
    rows.append(dict(sigma=sigma, PR=tr["PR"][:, -1].mean().item(),
                     rank=tr["rank"][:, -1].mean().item(),
                     Delta=tr["Delta"][:, -1].mean().item()))
    print(f"  sigma={sigma:5.3f}  Delta={rows[-1]['Delta']:.4f}  "
          f"PR={rows[-1]['PR']:.2f}  rank={rows[-1]['rank']:.1f}")
pd.DataFrame(rows).to_csv(f"{RES}/e2b_P4_span_sigma.csv", index=False)

json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e2b_summary.json", "w"), indent=1)
print(f"\nwall {time.time()-t0:.0f}s")
