"""E7: Decompose the +8% gap between OU theory and measured Delta_inf.

In task-attractor mode the cloud center W is FIXED, so the tangent coordinates are
directly measurable:  Theta_i = U^T Q_i  (U = fixed orthonormal basis of W-perp).
Therefore:
  (a) dynamics accuracy:  ||Theta_i - Theta_j||_F   vs  OU formula
        sqrt(2k(1-1/d)/(eta(2-eta))) * sigma
  (b) geometry correction:  d_G(V_i,V_j)  vs  ||Theta_i - Theta_j||_F
Also: eta-dependence (0.1 vs 0.3 vs 0.45) separates retraction effects (~eta^2)
from geometric effects (~Delta_inf^2, eta-independent).
"""
import sys, os, json, math, time
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(__file__))
from core import haar_sample, geodesic_dist, principal_cos

dev = "cuda" if torch.cuda.is_available() else "cpu"
RES = os.path.join(os.path.dirname(__file__), "..", "results")
t0 = time.time()
gen = torch.Generator(device=dev); gen.manual_seed(31)
d, k = 64, 8
W = haar_sample(1, d, k, dev, gen)[0]
# fixed complement basis
_Rc = torch.randn(d, d - k, device=dev, generator=gen)
U = torch.linalg.qr(torch.cat([W, _Rc], dim=1))[0][:, k:]                      # (d, d-k)

def task_step(Q, eta, sigma):
    Sq = torch.matmul((W @ W.t()).unsqueeze(0), Q)
    G = Sq - torch.matmul(Q, torch.matmul(Q.transpose(1, 2), Sq))
    Z = torch.randn(*Q.shape, device=dev, generator=gen) / math.sqrt(d)
    Z = Z - torch.matmul(Q, torch.matmul(Q.transpose(1, 2), Z))
    return torch.linalg.qr(Q + eta * G + sigma * Z)[0]

rows = []
for eta in (0.1, 0.3, 0.45):
    fac_ou = math.sqrt(2 * k * (1 - 1 / d) / (eta * (2 - eta)))
    for sigma in (0.03, 0.06, 0.1, 0.15, 0.2, 0.3):
        M = 24_000
        Q = haar_sample(M, d, k, dev, gen)
        for t in range(200):
            Q = task_step(Q, eta, sigma)
        # sample pairs
        P = 200_000
        i = torch.randint(0, M, (P,), device=dev, generator=gen)
        j = torch.randint(0, M, (P,), device=dev, generator=gen)
        Qa, Qb = Q[i], Q[j]
        dg = geodesic_dist(Qa, Qb)
        Th_a = torch.matmul(U.t(), Qa)              # (P, d-k, k)
        Th_b = torch.matmul(U.t(), Qb)
        dTheta = (Th_a - Th_b).norm(dim=(1, 2))
        rows.append(dict(eta=eta, sigma=sigma, fac_ou=fac_ou,
                         E_dg=float(dg.mean()), sd_dg=float(dg.std()),
                         E_dTheta=float(dTheta.mean()), sd_dTheta=float(dTheta.std()),
                         ratio_dg_dTheta=float((dg / dTheta.clamp_min(1e-9)).mean()),
                         ratio_dg_sigma=float(dg.mean()) / sigma,
                         ratio_dTheta_sigma=float(dTheta.mean()) / sigma))
        r = rows[-1]
        print(f"eta={eta:.2f} s={sigma:4.2f} | OU-pred fac={fac_ou:5.2f} | "
              f"||dTheta||/s={r['ratio_dTheta_sigma']:5.2f} | "
              f"dG/s={r['ratio_dg_sigma']:5.2f} | dG/dTheta={r['ratio_dg_dTheta']:5.3f}",
              flush=True)
        pd.DataFrame(rows).to_csv(f"{RES}/e7_decomposition.csv", index=False)
json.dump(dict(wall_s=time.time() - t0), open(f"{RES}/e7_summary.json", "w"), indent=1)
print(f"wall {time.time()-t0:.0f}s")
