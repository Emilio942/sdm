"""
Core Grassmannian operations for swarm diversity research.

Conventions (matching the research problem statement):
  - V_i in Gr(k,d): k-dim subspaces of R^d, represented by orthonormal
    basis matrices Q_i in R^{d x k} (Q_i^T Q_i = I_k).
  - d_G(V_i,V_j) = (sum_l theta_l^2)^{1/2}, theta_l = arccos(sigma_l)
    with sigma_l the singular values of Q_i^T Q_j (principal angles).
  - Delta(S) = (2/(N(N-1))) * sum_{i<j} d_G(V_i,V_j).
  - Phi: swarm evolution operator (consensus + noise + task pull).

All heavy ops are batched torch, device-agnostic (cuda/cpu).
"""
from __future__ import annotations
import torch
import math

# ----------------------------------------------------------------------------- sampling

def haar_sample(n: int, d: int, k: int, device=None, gen=None, dtype=torch.float32) -> torch.Tensor:
    """n i.i.d. Haar-uniform points on Gr(k,d) as (n,d,k) orthonormal stacks.

    Column signs are random; that is irrelevant for subspaces.
    """
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    G = torch.randn(n, d, k, device=device, generator=gen, dtype=dtype)
    Q, _ = torch.linalg.qr(G, mode="reduced")
    return Q

def random_orthonormal(d: int, k: int, device=None, gen=None, dtype=torch.float32) -> torch.Tensor:
    return haar_sample(1, d, k, device, gen, dtype)[0]

# ----------------------------------------------------------------------------- geometry

def principal_cos(Qa: torch.Tensor, Qb: torch.Tensor) -> torch.Tensor:
    """Principal cosines (singular values of Qa^T Qb), sorted descending.

    Qa, Qb: (..., d, k) -> (..., k)
    """
    C = torch.matmul(Qa.transpose(-1, -2), Qb)
    sv = torch.linalg.svdvals(C)
    return sv.clamp(0.0, 1.0)

def principal_angles(Qa: torch.Tensor, Qb: torch.Tensor) -> torch.Tensor:
    return torch.acos(principal_cos(Qa, Qb))

def geodesic_dist(Qa: torch.Tensor, Qb: torch.Tensor) -> torch.Tensor:
    """d_G per the problem: || (theta_1..theta_k) ||_2.  (...,) """
    th = principal_angles(Qa, Qb)
    return torch.linalg.vector_norm(th, dim=-1)

def chordal_dist_sq(Qa: torch.Tensor, Qb: torch.Tensor) -> torch.Tensor:
    """||P_a - P_b||_F^2 = 2*(k - ||Qa^T Qb||_F^2)."""
    C = torch.matmul(Qa.transpose(-1, -2), Qb)
    return 2.0 * (Qa.shape[-1] - (C * C).sum(dim=(-1, -2)))

# ----------------------------------------------------------------------------- swarm stats

def _pair_chunk_iter(N: int, chunk: int):
    i = 0
    while i < N:
        j = i + 1
        while j < N:
            hi = min(j + chunk, N)
            yield i, j, hi
            j = hi
        i += 1

def pairwise_geodesic(Q: torch.Tensor, chunk: int = 256) -> torch.Tensor:
    """All pairwise d_G for swarm Q:(N,d,k) -> (N,N) symmetric, diag=0. Chunked."""
    N = Q.shape[0]
    D = torch.zeros(N, N, device=Q.device)
    for i, j, hi in _pair_chunk_iter(N, chunk):
        A = Q[i].unsqueeze(0).expand(hi - j, -1, -1)          # (m,d,k) fixed i
        B = Q[j:hi]                                           # (m,d,k)
        d = geodesic_dist(A, B)                               # (m,)
        D[i, j:hi] = d
        D[j:hi, i] = d
    return D

def mean_diversity(Q: torch.Tensor, chunk: int = 256) -> torch.Tensor:
    """Delta(S) = mean over unordered pairs of d_G."""
    N = Q.shape[0]
    if N < 2:
        return torch.tensor(0.0, device=Q.device)
    D = pairwise_geodesic(Q, chunk)
    n_pairs = N * (N - 1) / 2
    return (D.sum() / 2.0) / n_pairs

def min_pairwise(Q: torch.Tensor, chunk: int = 256) -> torch.Tensor:
    N = Q.shape[0]
    if N < 2:
        return torch.tensor(0.0, device=Q.device)
    D = pairwise_geodesic(Q, chunk)
    D.fill_diagonal_(float("inf"))
    return D.min()

def pairwise_matrix(Q: torch.Tensor, chunk: int = 256):
    D = pairwise_geodesic(Q, chunk)
    return D

# ----------------------------------------------------------------------------- span metrics

def projector_sum(Q: torch.Tensor) -> torch.Tensor:
    """S = sum_i Q_i Q_i^T : (N,d,k) -> (d,d).  S[de] = sum_{i,k} Q[i,d,k] Q[i,e,k]."""
    return torch.einsum("ndk,nek->de", Q, Q)

def span_rank(Q: torch.Tensor, tol: float = 1e-6) -> int:
    """dim Span(∪ V_i) = rank of projector sum."""
    ev = torch.linalg.eigvalsh(projector_sum(Q))
    return int((ev > tol).sum().item())

def participation_ratio(Q: torch.Tensor) -> float:
    """PR = (Tr S)^2 / Tr(S^2) in [k, min(Nk,d)]; soft effective span dimension."""
    S = projector_sum(Q)
    ev = torch.linalg.eigvalsh(S).clamp_min(0.0)
    return float((ev.sum() ** 2 / (ev * ev).sum()).item())

def effective_rank_entropy(Q: torch.Tensor) -> float:
    """exp(shannon entropy of normalized eigenvalues of S/k)."""
    S = projector_sum(Q)
    ev = torch.linalg.eigvalsh(S).clamp_min(1e-12)
    p = ev / ev.sum()
    H = float(-(p * p.clamp_min(1e-12).log()).sum().item())
    return math.exp(H)

# ----------------------------------------------------------------------------- dynamics

def geodesic_mean(Q: torch.Tensor) -> torch.Tensor:
    """Principal k-geodesic mean (argmax_V sum_i <P_V, P_i>): top-k eigvecs of mean projector.

    Q: (N,d,k) -> (d,k)
    """
    S = projector_sum(Q) / Q.shape[0]
    _, U = torch.linalg.eigh(S)          # ascending
    return U[..., :, -Q.shape[-1]:]      # top-k

def geodesic_mean_batch(Qb: torch.Tensor) -> torch.Tensor:
    """Batched mean for swarms Qb:(R,N,d,k) -> (R,d,k)."""
    R, N, d, k = Qb.shape
    S = torch.einsum("rndk,rnek->rde", Qb, Qb) / N
    _, U = torch.linalg.eigh(S)
    return U[..., :, -k:]

def delta_batch(Qb: torch.Tensor, chunk: int = 256) -> torch.Tensor:
    """Delta for each of R swarms Qb:(R,N,d,k) -> (R,)."""
    R, N, d, k = Qb.shape
    if N < 2:
        return torch.zeros(R, device=Qb.device)
    out = torch.zeros(R, device=Qb.device)
    n_pairs = N * (N - 1) / 2
    i = 0
    while i < N:
        j = i + 1
        while j < N:
            hi = min(j + chunk, N)
            A = Qb[:, i].unsqueeze(1).expand(R, hi - j, d, k)
            B = Qb[:, j:hi]
            out += geodesic_dist(A, B).sum(dim=1)
            j = hi
        i += 1
    return out / n_pairs

def span_metrics_batch(Qb: torch.Tensor, tol: float = 1e-4):
    """(rank, PR, H-rank) for each swarm in Qb:(R,N,d,k) -> three (R,) tensors."""
    R, N, d, k = Qb.shape
    S = torch.einsum("rndk,rnek->rde", Qb, Qb)
    ev = torch.linalg.eigvalsh(S).clamp_min(0.0)
    rank = (ev > tol * k).sum(dim=-1).float()
    pr = ev.sum(-1) ** 2 / (ev * ev).sum(-1).clamp_min(1e-12)
    p = ev / ev.sum(-1, keepdim=True).clamp_min(1e-12)
    H = -(p * p.clamp_min(1e-12).log()).sum(-1)
    return rank, pr, H.exp()

# ------------------------------------------------------------------ covariant Phi

def _tangent(Z: torch.Tensor, Q: torch.Tensor) -> torch.Tensor:
    """Project (...,d,k) onto tangent space of Gr at Q: Z - Q(Q^T Z)."""
    return Z - torch.matmul(Q, torch.matmul(Q.transpose(-1, -2), Z))

def delta_estimate_batch(Qb: torch.Tensor, n_pairs: int = 2048, gen=None,
                         pair_chunk: int = 256) -> torch.Tensor:
    """Unbiased MC estimate of Delta from n_pairs random pairs per swarm. Fast, chunked."""
    R, N, d, k = Qb.shape
    if N < 2:
        return torch.zeros(R, device=Qb.device)
    acc = torch.zeros(R, device=Qb.device)
    done = 0
    while done < n_pairs:
        m = min(pair_chunk, n_pairs - done)
        i = torch.randint(0, N, (m,), device=Qb.device, generator=gen)
        j = torch.randint(0, N - 1, (m,), device=Qb.device, generator=gen)
        j = j + (j >= i).long()
        A = Qb[torch.arange(R, device=Qb.device).unsqueeze(1), i.unsqueeze(0).expand(R, -1)]
        B = Qb[torch.arange(R, device=Qb.device).unsqueeze(1), j.unsqueeze(0).expand(R, -1)]
        acc += geodesic_dist(A, B).sum(dim=1)
        done += m
    return acc / n_pairs

def min_pairwise_batch(Qb: torch.Tensor, chunk: int = 256) -> torch.Tensor:
    """Exact min pairwise distance for each swarm in Qb:(R,N,d,k)."""
    R, N, d, k = Qb.shape
    out = torch.full((R,), float("inf"), device=Qb.device)
    if N < 2:
        return torch.zeros(R, device=Qb.device)
    i = 0
    while i < N:
        j = i + 1
        while j < N:
            hi = min(j + chunk, N)
            A = Qb[:, i].unsqueeze(1).expand(R, hi - j, d, k)
            B = Qb[:, j:hi]
            out = torch.minimum(out, geodesic_dist(A, B).min(dim=1).values)
            j = hi
        i += 1
    return out

def grad_step_private(Qb: torch.Tensor, eta: float, rho: float, sigma: float,
                      gen=None) -> torch.Tensor:
    """Consensus + PRIVATE-DATA objective coupling.

    Each model i additionally ascends  rho * <P_V, W_i W_i^T>  with a fresh random
    private subspace W_i each step (models fine-tuned on shared + private data):

        G_i = (I - Q_iQ_i^T)(Sbar + rho-scale W_iW_i^T) Q_i

    implemented as X = Q + eta*G_cons + rho*G_priv + sigma*Z_tang, QR retraction.
    """
    R, N, d, k = Qb.shape
    Sbar = torch.einsum("rndk,rnek->rde", Qb, Qb) / N
    Gc = torch.matmul(Sbar.unsqueeze(1), Qb)
    Gc = _tangent(Gc, Qb)
    Wp = haar_sample(R * N, d, k, Qb.device, gen).reshape(R, N, d, k)
    Gp = torch.matmul(Wp, torch.matmul(Wp.transpose(-1, -2), Qb))   # W W^T Q
    Gp = _tangent(Gp, Qb)
    X = Qb + eta * Gc + rho * Gp
    if sigma > 0:
        Zn = torch.randn(R, N, d, k, device=Qb.device, generator=gen) * (sigma / math.sqrt(d))
        X = X + _tangent(Zn, Qb)
    return torch.linalg.qr(X)[0]

def grad_step(Qb: torch.Tensor, eta: float, sigma: float, gen=None,
              Sbar: torch.Tensor | None = None, sigma_rel: bool = True) -> torch.Tensor:
    """Covariant Grassmannian SGD step on Qb:(R,N,d,k).

        V_i' = Retr( V_i, eta * grad <P_V, Sbar> + tangent noise )

    grad of f(V)=Tr(Q^T Sbar Q) on Gr:  G = (I - Q Q^T) Sbar Q.
    Retraction = QR.  Noise amplitude sigma is per-column-norm relative
    (entries sigma/sqrt(d)) so the step size is dimension-free.
    Consensus mode: Sbar = mean projector of the swarm.
    """
    R, N, d, k = Qb.shape
    if Sbar is None:
        Sbar = torch.einsum("rndk,rnek->rde", Qb, Qb) / N
    Sq = torch.matmul(Sbar.unsqueeze(1), Qb)                    # (R,N,d,k)
    G = _tangent(Sq, Qb)                                        # tangent gradient
    X = Qb + eta * G
    if sigma > 0:
        s = sigma / math.sqrt(d) if sigma_rel else sigma
        Zn = torch.randn(R, N, d, k, device=Qb.device, generator=gen) * s
        X = X + _tangent(Zn, Qb)
    Qn, _ = torch.linalg.qr(X)
    return Qn

def phi_step(Q: torch.Tensor,
             eta: float,
             sigma: float,
             gen: torch.Generator,
             attractor: torch.Tensor | None = None,
             private: torch.Tensor | None = None,
             rho: float = 0.0,
             consensus: bool = True) -> torch.Tensor:
    """One step of Phi on swarm Q:(N,d,k).

      B_i' = orth( (1 - eta - rho) * B_i
                   + eta * B_star            (shared task/consensus pull)
                   + rho * B_priv_i          (private data innovation)
                   + sigma * G_i )           (SGD noise)

    B_star = swarm geodesic mean (consensus=True) or fixed attractor basis.
    orth() = polar/QR projection back to Gr(k,d).
    """
    N, d, k = Q.shape
    B_star = geodesic_mean(Q) if (consensus and attractor is None) else attractor
    X = (1.0 - eta - rho) * Q
    if eta > 0:
        X = X + eta * B_star.unsqueeze(0)
    if rho > 0:
        X = X + rho * private
    if sigma > 0:
        X = X + sigma * torch.randn(N, d, k, device=Q.device, generator=gen)
    R, _ = torch.linalg.qr(X, mode="reduced")
    return R

def run_swarm(Q0: torch.Tensor, T: int, eta: float, sigma: float, gen: torch.Generator,
              attractor: torch.Tensor | None = None, rho: float = 0.0,
              private_seq=None, consensus: bool = True,
              track: bool = True, chunk: int = 256):
    """Run Phi for T steps. Returns dict with trajectories."""
    Q = Q0.clone()
    traj = {"Delta": [], "dmin": [], "span": [], "PR": [], "H_rank": []}
    if track:
        traj["Delta"].append(float(mean_diversity(Q, chunk)))
        traj["dmin"].append(float(min_pairwise(Q, chunk)))
        traj["span"].append(span_rank(Q))
        traj["PR"].append(participation_ratio(Q))
        traj["H_rank"].append(effective_rank_entropy(Q))
    for t in range(T):
        priv = private_seq[t] if private_seq is not None else None
        Q = phi_step(Q, eta, sigma, gen, attractor=attractor, private=priv,
                     rho=rho, consensus=consensus)
        if track:
            traj["Delta"].append(float(mean_diversity(Q, chunk)))
            traj["dmin"].append(float(min_pairwise(Q, chunk)))
            traj["span"].append(span_rank(Q))
            traj["PR"].append(participation_ratio(Q))
            traj["H_rank"].append(effective_rank_entropy(Q))
    return Q, traj
