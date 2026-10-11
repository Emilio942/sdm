"""Mathematical self-tests for core.py.

Verified identities:
  (1) QR orthonormality: Q^T Q = I.
  (2) d_G symmetric, zero iff same subspace, <= k*pi/2.
  (3) E[||Q_a^T Q_b||_F^2] = k^2/d for independent Haar subspaces  (exact).
  (4) E[sum_l sin^2 theta_l] = k - k^2/d  (equivalent to (3)).
  (5) k=1: cos^2 theta ~ Beta(1/2,(d-1)/2) -> closed form E[theta^2]
      compared with MC.
  (6) span_rank / participation_ratio sanity: identical subspaces -> span=k, PR=k;
      orthogonal disjoint -> span=Nk (<=d), PR=Nk.
  (7) mean_diversity matches brute-force loop.
"""
import sys, torch, math
import numpy as np
from numpy.polynomial.legendre import leggauss
sys.path.insert(0, ".")
from core import *

torch.manual_seed(0)
dev = "cuda" if torch.cuda.is_available() else "cpu"
DT = torch.float64   # tests run in double precision
ok = True

def check(name, cond, detail=""):
    global ok
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    ok = ok and bool(cond)

# (1) orthonormality
Q = haar_sample(64, 48, 12, dev, dtype=DT)
err = (Q.transpose(1, 2) @ Q - torch.eye(12, device=dev, dtype=DT)).abs().max().item()
check("QR orthonormality", err < 1e-5, f"max err={err:.2e}")

# (2) symmetry & range
A = haar_sample(32, 40, 8, dev, dtype=DT); B = haar_sample(32, 40, 8, dev, dtype=DT)
dab = geodesic_dist(A, B); dba = geodesic_dist(B, A)
check("d_G symmetric", (dab - dba).abs().max().item() < 1e-6,
      f"maxdiff={(dab-dba).abs().max().item():.2e}")
check("d_G in [0, k*pi/2]", ((dab >= -1e-9) & (dab <= 8 * math.pi / 2 + 1e-6)).all().item())
check("d_G(V,V)=0", geodesic_dist(B[0], B[0]).item() < 1e-7)

# (3)+(4) E||Qa^TQb||_F^2 = k^2/d
M = 40000
for (d, k) in [(40, 8), (64, 16), (30, 10)]:
    A = haar_sample(M, d, k, dev, dtype=DT); B = haar_sample(M, d, k, dev, dtype=DT)
    C = torch.matmul(A.transpose(1, 2), B)
    f2 = (C * C).sum(dim=(1, 2)).mean().item()
    th = torch.acos(principal_cos(A, B))
    s2 = (torch.sin(th) ** 2).sum(dim=1).mean().item()
    check(f"E[||Qa^TQb||_F^2]=k^2/d d={d} k={k}",
          abs(f2 - k * k / d) < 0.02 * k * k / d,
          f"mc={f2:.5f} exact={k*k/d:.5f}")
    check(f"E[sum sin^2]=k-k^2/d d={d} k={k}",
          abs(s2 - (k - k * k / d)) < 0.02 * (k - k * k / d),
          f"mc={s2:.5f} exact={k-k*k/d:.5f}")

# (5) k=1 closed form: E[theta^2] where cos^2 theta ~ Beta(1/2,(d-1)/2)
d, k = 50, 1
A = haar_sample(M, d, k, dev, dtype=DT); B = haar_sample(M, d, k, dev, dtype=DT)
mc = (geodesic_dist(A, B) ** 2).mean().item()
a, b = 0.5, (d - 1) / 2.0
# integrate with substitution c = u^2 to remove c^{-1/2} endpoint singularity
from scipy.special import betaln
u, w = leggauss(400)              # u in [-1,1] -> s in [0,1]
s = 0.5 * (u + 1)
c = s * s                          # cos^2 theta
pdf = np.exp(-betaln(a, b) + (a - 1) * np.log(c) + (b - 1) * np.log1p(-c))
th2 = np.arccos(np.sqrt(c)) ** 2
exact = float(np.sum(0.5 * w * 2 * s * pdf * th2))  # dc = 2s ds, w sums to 2
check("k=1 E[d_G^2] closed form", abs(mc - exact) / exact < 0.01,
      f"mc={mc:.5f} quad={exact:.5f}")

# (6) span metrics
Qident = B[0:1].expand(5, -1, -1).contiguous()
check("identical subspaces: span=k", span_rank(Qident) == 40 and False or span_rank(Qident) == k) if False else None
check("identical: span=k", span_rank(Qident) == k, f"span={span_rank(Qident)}")
check("identical: PR=k", abs(participation_ratio(Qident) - k) < 1e-3)
d_, k_ = 24, 4
# build N=5 mutually orthogonal subspaces
E = torch.zeros(5, d_, k_, device=dev, dtype=DT)
for i in range(5):
    E[i, i * k_:(i + 1) * k_] = torch.eye(k_, device=dev, dtype=DT)
check("orthogonal: span=Nk", span_rank(E) == 20, f"span={span_rank(E)}")
check("orthogonal: PR=Nk", abs(participation_ratio(E) - 20) < 1e-3)

# (7) mean_diversity vs brute force
Q = haar_sample(9, 16, 5, dev, dtype=DT)
D = pairwise_geodesic(Q)
bf = []
for i in range(9):
    for j in range(i + 1, 9):
        bf.append(geodesic_dist(Q[i], Q[j]).item())
check("mean_diversity vs brute force",
      abs(mean_diversity(Q).item() - sum(bf) / len(bf)) < 1e-6)

# (8) geodesic mean: maximizes Tr(P_M S) = sum_i ||M^T Q_i||^2, i.e. equals top-k eigsum of S
Qs = haar_sample(7, 20, 6, dev)
Msub = geodesic_mean(Qs)
gain = sum((Msub.t() @ Qs[i]).pow(2).sum().item() for i in range(7))
S = projector_sum(Qs)
ev = torch.linalg.eigvalsh(S)
topk = float(ev[-6:].sum().item())
gains_members = [sum((Qs[m].t() @ Qs[i]).pow(2).sum().item() for i in range(7)) for m in range(7)]
check("geodesic mean achieves top-k eigsum", abs(gain - topk) < 1e-6 * max(1, topk),
      f"mean={gain:.6f} topk={topk:.6f}")
check("geodesic mean beats every member", gain >= max(gains_members) - 1e-6,
      f"mean={gain:.4f} max_member={max(gains_members):.4f}")

print("\nALL PASS" if ok else "\nSOME FAILURES")
sys.exit(0 if ok else 1)
