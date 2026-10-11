"""E1: Initial-state statistics of Haar-random swarms on Gr(k,d).

Theory anchors verified/estimated here:
  A. Pairwise distance distribution: E[d_G^2] = E[sum_l theta_l^2] vs
     asymptotic  E[d_G^2] ~= k*pi^2/4 - pi*k^2/d   (small cos^2 expansion)
     and sandwich   E[sum sin^2] <= E[d_G^2]*(2/pi)^{-2}... i.e.
       (2/pi)^2 (k - k^2/d) <= E[d_G^2] <= (pi/2)^2 (k - k^2/d)
  B. Delta_0 concentration in N:  U-statistic => Var(Delta) ~ 4 zeta_1 / N
     (rate exp(-c N)), NOT exp(-c N^2).
  C. d_min extreme values: P(d_min < a) vs independent-pairs prediction
     1-(1-F_pair(a))^{N(N-1)/2}.
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import (haar_sample, geodesic_dist, pairwise_geodesic, mean_diversity,
                  principal_cos)

torch.manual_seed(11)
dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RES, exist_ok=True)
t0 = time.time()

# ---------------------------------------------------------------- A: pairwise laws
def pairwise_moments(d, k, M, chunk=50_000, dev="cuda"):
    """Chunked MC moments of pairwise d_G."""
    s1 = s2 = s2sin = 0.0
    done = 0
    while done < M:
        m = min(chunk, M - done)
        A = haar_sample(m, d, k, dev); B = haar_sample(m, d, k, dev)
        dg = geodesic_dist(A, B)
        s1 += float(dg.sum()); s2 += float((dg * dg).sum())
        th = torch.acos(principal_cos(A, B))
        s2sin += float((torch.sin(th) ** 2).sum())
        done += m
        del A, B, dg, th
    return s1 / M, s2 / M, s2sin / M

rows = []
M = 400_000
grid = [(d, k) for d in (32, 64, 128, 256) for k in (2, 4, 8, 16) if 2 * k <= d]
for (d, k) in grid:
    Edg, Edg2, Esin2 = pairwise_moments(d, k, M)
    asy0 = k * math.pi**2 / 4 - math.pi * k * k / d                 # naive expansion
    asy1 = k * math.pi**2 / 4 - math.pi * k * math.sqrt(2 * k / (math.pi * d)) \
           + k * k / d                                              # E|N| correction
    sin2 = k - k * k / d                                            # exact identity
    rows.append(dict(d=d, k=k, Edg=Edg, Edg2=Edg2, asy0=asy0, asy1=asy1,
                     exact_sin2=sin2, mc_sin2=Esin2,
                     lo=(2/math.pi)**2*sin2, hi=(math.pi/2)**2*sin2))
    r = rows[-1]
    print(f"d={d:4d} k={k:3d}  E[dG]={Edg:.4f}  E[dG^2]={Edg2:.4f}  "
          f"asy0={asy0:.3f}({(Edg2-asy0)/asy0:+.1%}) asy1={asy1:.3f}({(Edg2-asy1)/asy1:+.1%}) "
          f"sin2 mc/exact={Esin2/sin2:.5f} sandwich={r['lo'] <= Edg2 <= r['hi']}")
pd.DataFrame(rows).to_csv(f"{RES}/e1_pairwise_laws.csv", index=False)

# ---------------------------------------------------------------- B: Delta_0 vs N
d, k = 128, 8
reps = {4: 20000, 8: 12000, 16: 6000, 32: 3000, 64: 1500, 128: 800, 256: 400, 512: 200}
rowsB = []
for N, R in reps.items():
    vals = np.empty(R); dmin = np.empty(R)
    for r in range(R):
        Q = haar_sample(N, d, k, dev)
        vals[r] = float(mean_diversity(Q))
        D = pairwise_geodesic(Q)
        D.fill_diagonal_(float("inf"))
        dmin[r] = float(D.min())
    # pairwise reference (for C), chunked
    pair_chunks = []
    for _ in range(8):
        A = haar_sample(25_000, d, k, dev); B = haar_sample(25_000, d, k, dev)
        pair_chunks.append(geodesic_dist(A, B).cpu().numpy())
        del A, B
    pair_d = np.concatenate(pair_chunks)
    rowsB.append(dict(N=N, mean=vals.mean(), var=vals.var(),
                      p995=np.quantile(vals, 0.995), p005=np.quantile(vals, 0.005),
                      dmin_mean=dmin.mean(), dmin_p001=np.quantile(dmin, 0.001)))
    print(f"N={N:4d} R={R:6d}  E[Delta]={vals.mean():.6f}  Var={vals.var():.3e}  "
          f"Var*N={vals.var()*N:.3e}  dmin_mean={dmin.mean():.4f}")
dfB = pd.DataFrame(rowsB)
dfB.to_csv(f"{RES}/e1_delta_concentration.csv", index=False)
slope = np.polyfit(np.log(dfB.N), np.log(dfB["var"]), 1)[0]
print(f"Var(Delta) ~ N^slope : slope = {slope:.3f}   (U-statistic theory: -1)")

# ---------------------------------------------------------------- C: d_min extreme value
N = 64
Fs = np.sort(pair_d)
def indep_pred(a):   # P(no pair below a) under i.i.d. pairs
    return 1 - (1 - np.searchsorted(Fs, a, side="right") / len(Fs)) ** (N * (N-1) // 2)
qs = np.array([0.001, 0.01, 0.05, 0.25, 0.5, 0.75])
emp = np.quantile(dmin, qs)
pred = np.array([np.quantile(Fs, 1 - (1-q)**(1/(N*(N-1)//2))) for q in qs])
print("\nC: d_min quantiles empirical vs independent-pair prediction (N=64)")
for q, e, p in zip(qs, emp, pred):
    print(f"  q={q:6.3f}  emp={e:.4f}  pred={p:.4f}  ratio={e/p:.3f}")
pd.DataFrame(dict(q=qs, emp=emp, pred=pred)).to_csv(f"{RES}/e1_dmin_extreme.csv", index=False)

json.dump(dict(slope_var_vs_N=slope, wall_s=time.time()-t0),
          open(f"{RES}/e1_summary.json", "w"), indent=1)
print(f"\nwall time {time.time()-t0:.1f}s")
