"""E2: Swarm dynamics under Phi (consensus + noise), batched Monte Carlo.

Questions:
  P1  sigma=0: contraction rate of Delta(t) vs (1-eta); N-independence of the
      normalized trajectory Delta(t)/Delta(0).
  P2  stationary diversity Delta_inf(sigma, eta) -- law + N-independence in bulk.
  P3  U-statistic dichotomy: Var(Delta) scaling at stationarity (non-invariant
      law => slope -1) vs Haar init (invariant law => slope -2, from E1).
  P4  span/PR saturation in N at stationarity: N buys effective span.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, delta_batch, geodesic_mean_batch,
                  span_metrics_batch, phi_step)

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RES, exist_ok=True)
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(7)

def run_batch(Q0, T, eta, sigma, rho=0.0, gen=None, track_every=1, rank_tol=None):
    """Q0:(R,N,d,k); returns trajectories dict of (R, n_track) arrays."""
    Q = Q0.clone()
    R, N, d, k = Q.shape
    tr = {"Delta": [], "rank": [], "PR": [], "H": [], "dmin": []}
    def track():
        tr["Delta"].append(delta_batch(Q).cpu())
        r, pr, h = span_metrics_batch(Q)
        tr["rank"].append(r.cpu()); tr["PR"].append(pr.cpu()); tr["H"].append(h.cpu())
        # dmin only for small R (costly); else fill NaN
        if R <= 8:
            from core import pairwise_geodesic
            dm = []
            for r_ in range(R):
                D = pairwise_geodesic(Q[r_]); D.fill_diagonal_(float("inf"))
                dm.append(float(D.min()))
            tr["dmin"].append(torch.tensor(dm))
        else:
            tr["dmin"].append(torch.full((R,), float("nan")))
    track()
    for t in range(T):
        priv = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k) if rho > 0 else None
        B = geodesic_mean_batch(Q)
        X = (1 - eta - rho) * Q + eta * B.unsqueeze(1)
        if rho > 0:
            X = X + rho * priv
        if sigma > 0:
            X = X + sigma * torch.randn(R, N, d, k, device=dev, generator=gen)
        Q, _ = torch.linalg.qr(X)
        if (t + 1) % track_every == 0:
            track()
    return Q, {k_: torch.stack(v, dim=1) for k_, v in tr.items()}

d, k = 64, 8
R = 48

print("=" * 72)
print("P1: sigma=0 contraction")
rows = []
for eta in (0.1, 0.3, 0.6):
    for N in (16, 64, 256):
        Q0 = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
        _, tr = run_batch(Q0, 30, eta, 0.0, gen=gen)
        Delta = tr["Delta"].mean(dim=0).numpy()          # mean over reps
        ratio = Delta / Delta[0]
        # fit log ratio ~ rate * t
        tt = np.arange(len(ratio))
        rate = -np.polyfit(tt[1:], np.log(ratio[1:]), 1)[0]
        rows.append(dict(eta=eta, N=N, rate=rate, rate_over_eta=rate / eta,
                         D0=Delta[0], D_T=Delta[-1]))
        print(f"  eta={eta:.1f} N={N:4d}  rate={rate:.4f}  rate/eta={rate/eta:.3f}  "
              f"Delta0={Delta[0]:.3f} -> DeltaT={Delta[-1]:.2e}")
pd.DataFrame(rows).to_csv(f"{RES}/e2_P1_contraction.csv", index=False)

print("=" * 72)
print("P2: stationary Delta_inf vs sigma")
rows = []
T, burn = 150, 90
for eta in (0.1, 0.3):
    for sigma in (0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.45, 0.6):
        for N in (64,):
            Q0 = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
            Qf, tr = run_batch(Q0, T, eta, sigma, gen=gen, track_every=5)
            Din = tr["Delta"][:, burn // 5:].mean().item()
            Din_sd = tr["Delta"][:, burn // 5:].std().item()
            rows.append(dict(eta=eta, sigma=sigma, N=N, Delta_inf=Din, sd=Din_sd))
            print(f"  eta={eta:.2f} sigma={sigma:.2f}  Delta_inf={Din:.4f} +- {Din_sd:.4f}")
# N-independence check at two sigmas
for sigma in (0.1, 0.3):
    for N in (16, 64, 256):
        Q0 = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
        Qf, tr = run_batch(Q0, T, 0.3, sigma, gen=gen, track_every=5)
        Din = tr["Delta"][:, burn // 5:].mean().item()
        rows.append(dict(eta=0.3, sigma=sigma, N=N, Delta_inf=Din,
                         sd=tr["Delta"][:, burn//5:].std().item()))
        print(f"  [N-check] sigma={sigma:.2f} N={N:4d}  Delta_inf={Din:.4f}")
pd.DataFrame(rows).to_csv(f"{RES}/e2_P2_stationary.csv", index=False)

print("=" * 72)
print("P3: Var(Delta) scaling at stationarity (dichotomy test)")
rows = []
for N in (16, 32, 64, 128, 256):
    Rr = {16: 4000, 32: 2000, 64: 1000, 128: 500, 256: 250}[N]
    # stationary: initialize near attractor and run burn-in jointly in batch
    Q0 = haar_sample(Rr * N, d, k, dev, gen).reshape(Rr, N, d, k)
    Qf, tr = run_batch(Q0, 60, 0.3, 0.15, gen=gen, track_every=60)
    vals = tr["Delta"][:, -1].numpy()
    rows.append(dict(N=N, var=vals.var(), mean=vals.mean()))
    print(f"  N={N:4d} R={Rr:5d}  Var={vals.var():.3e}  Var*N={vals.var()*N:.3e}")
df = pd.DataFrame(rows)
df.to_csv(f"{RES}/e2_P3_dichotomy.csv", index=False)
slope = np.polyfit(np.log(df.N), np.log(df["var"]), 1)[0]
print(f"  slope Var~N^s at stationarity: {slope:.3f}   (theory non-invariant: -1, Haar was -2.04)")

print("=" * 72)
print("P4: effective span vs N at stationarity")
rows = []
for N in (8, 16, 32, 64, 128, 256, 512):
    Rr = {8: 256, 16: 128, 32: 64, 64: 32, 128: 16, 256: 8, 512: 4}[N]
    Q0 = haar_sample(Rr * N, d, k, dev, gen).reshape(Rr, N, d, k)
    Qf, tr = run_batch(Q0, 90, 0.3, 0.15, gen=gen, track_every=30)
    rows.append(dict(N=N, rank=tr["rank"][:, -1].mean().item(),
                     PR=tr["PR"][:, -1].mean().item(),
                     H=tr["H"][:, -1].mean().item(),
                     PR0=tr["PR"][:, 0].mean().item(), rank0=tr["rank"][:, 0].mean().item()))
    print(f"  N={N:4d}  rank {rows[-1]['rank0']:.1f}->{rows[-1]['rank']:.1f}  "
          f"PR {rows[-1]['PR0']:.1f}->{rows[-1]['PR']:.1f}  Hr {rows[-1]['H']:.2f}")
pd.DataFrame(rows).to_csv(f"{RES}/e2_P4_span_vs_N.csv", index=False)

json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e2_summary.json", "w"), indent=1)
print(f"\nwall {time.time()-t0:.0f}s")
