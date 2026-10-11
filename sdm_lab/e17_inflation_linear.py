"""E17: clean finite-N inflation scan in the LINEAR regime (sigma=0.1, eta=0.3).
N in {8, 16, 32, 64, 128, 256, 512}: ratio(N) vs task-mode law 5.239.
Long T, dedicated seeds, exact Delta. This supersedes e14 (sigma=0.2 confound).
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import haar_sample, delta_batch, grad_step

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(300)
d, k, eta, sigma, T = 64, 8, 0.3, 0.1, 400

W = haar_sample(1, d, k, dev, gen)[0]
def shrink(Q, c):
    return torch.linalg.qr(math.sqrt(max(1e-12, 1 - c * c)) * Q + c * W.unsqueeze(0))[0]

rows = []
for N, R in ((8, 512), (16, 384), (32, 256), (64, 192), (128, 128), (256, 64), (512, 32), (1024, 16)):
    Qb = haar_sample(R * N, d, k, dev, gen).reshape(R, N, d, k)
    lo, hi = 0.0, 0.9995
    for _ in range(10):
        mid = 0.5 * (lo + hi)
        X = math.sqrt(max(1e-12, 1 - mid * mid)) * Qb[0] + mid * W.unsqueeze(0)
        if float(delta_batch(torch.linalg.qr(X)[0].unsqueeze(0))) > 1.8: lo = mid
        else: hi = mid
    Q = shrink(Qb, 0.5 * (lo + hi))
    for t in range(T):
        Q = grad_step(Q, eta, sigma, gen=gen)
    Df = delta_batch(Q)
    ratio = float(Df.mean()) / sigma
    se = float(Df.std()) / sigma / math.sqrt(R)
    rows.append(dict(N=N, R=R, Delta=float(Df.mean()), Delta_sd=float(Df.std()),
                     ratio=ratio, se=se, inflation=ratio / 5.2394))
    r = rows[-1]
    print(f"N={N:5d} R={R:4d} | D={r['Delta']:.4f}+-{r['Delta_sd']:.4f} | "
          f"ratio={ratio:.3f}+-{se:.3f} | I={r['inflation']:.3f}", flush=True)
    pd.DataFrame(rows).to_csv(f"{RES}/e17_inflation_linear.csv", index=False)

df = pd.DataFrame(rows)
df["Iminus1"] = df.inflation - 1
for p, name in ((1.0, "1/N"), (0.5, "1/sqrt(N)")):
    xx = (1.0 / df.N) ** p
    a = float((xx * df.Iminus1).sum() / (xx * xx).sum())
    rms = float(np.sqrt(((df.Iminus1 - a * xx) ** 2).mean()))
    print(f"fit I-1 = {a:.3f} * {name}: rms={rms:.4f}")
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e17_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
