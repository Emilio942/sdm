"""E14: N-scaling of the consensus-mode inflation factor.
Consensus mode at sigma=0.2 (safely stationary), eta=0.3, k=8, d=64.
Inflation I(N) = (Delta_inf/sigma) / 5.235 (task-mode exact factor).
Fits: I-1 ~ a/N vs a/sqrt(N) vs a/N^(2/3).
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import haar_sample, geodesic_dist, delta_batch, grad_step

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(101)
d, k, eta, sigma, T = 64, 8, 0.3, 0.2, 400

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

rows = []
for N, R in ((8, 512), (16, 384), (32, 256), (64, 192), (128, 128), (256, 64), (512, 32), (1024, 16)):
    Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    lo, hi = 0.0, 0.9995
    for _ in range(10):
        mid = 0.5 * (lo + hi)
        if float(delta_batch(shrink(Qb[0], mid).unsqueeze(0))) > 1.8: lo = mid
        else: hi = mid
    Q = shrink(Qb, 0.5 * (lo + hi))
    for t in range(T):
        Q = grad_step(Q, eta, sigma, gen=gen)
    Df = delta_batch(Q)
    ratio = float(Df.mean()) / sigma
    se = float(Df.std()) / sigma / math.sqrt(R)
    rows.append(dict(N=N, R=R, Delta=float(Df.mean()), Delta_sd=float(Df.std()),
                     ratio=ratio, se=se, inflation=ratio / 5.235))
    r = rows[-1]
    print(f"N={N:5d} R={R:4d} | D={r['Delta']:.4f}+-{r['Delta_sd']:.4f} | "
          f"ratio={ratio:.3f}+-{se:.3f} | I={r['inflation']:.3f}", flush=True)
    pd.DataFrame(rows).to_csv(f"{RES}/e14_inflation_scaling.csv", index=False)

# fits on I-1 (admissible cells only: N>=32)
df = pd.DataFrame(rows); df = df[df.N >= 32]
x = 1.0 / df.N.values; y = df.inflation.values - 1
for p, name in ((1.0, "1/N"), (0.5, "1/sqrt(N)"), (2/3, "1/N^(2/3)")):
    xx = x ** p
    a = float((xx * y).sum() / (xx * xx).sum())
    resid = float(np.sqrt(((y - a * xx) ** 2).mean()))
    print(f"fit I-1 = {a:.3f}*{name}:  rms resid = {resid:.4f}")
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e14_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
