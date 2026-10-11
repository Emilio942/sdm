# Theory notes (derivations for the report)

## 1. Exact identities (verified numerically in test_core.py)

For independent Haar subspaces V,W ~ Unif(Gr(k,d)) with principal angles theta_1..theta_k:

  E[ ||Q_V^T Q_W||_F^2 ] = sum_l E[cos^2 theta_l] = k^2/d
    (proof: E[Tr(Q_V^T Q_W Q_W^T Q_V)] = sum_{a,b} E[<u_a,w_b>^2] = k^2 * 1/d)
  => E[ sum_l sin^2 theta_l ] = k - k^2/d.          [MC confirms to 5 digits]

Small-cosine expansion of E[d_G^2] (d >> k):
  theta = pi/2 - eps, cos(theta)=eps, theta^2 = pi^2/4 - pi*eps + eps^2.
  With eps_l ~ |N(0, k/d)| (heuristic, beta-tail):
    E[d_G^2] ~ k*pi^2/4 - pi*k*sqrt(2k/(pi*d)) + k^2/d     ("asy1", 0.2-2% error for k<=8, d>=64;
                                                            naive k*pi^2/4 - pi*k^2/d is off by up to 23%)
Sandwich (exact): (2/pi)^2 (k - k^2/d) <= E[d_G^2] <= (pi/2)^2 (k - k^2/d).  [holds in all 16 grid cells]

k=1 closed form: cos^2 theta ~ Beta(1/2,(d-1)/2) => E[d_G^2] by 1-D quadrature; MC agrees (d=50: 2.1303 vs 2.1291).

## 2. Degenerate U-statistic at Haar  (E1 measurement: slope -2.04)

Delta(S) = (2/(N(N-1))) sum_{i<j} h(V_i,V_j), h = d_G, is a U-statistic.
Hoeffding: Var(Delta) = 4(N-2)/(N(N-1)) zeta_1 + 2/(N(N-1)) zeta_2,
  zeta_1 = Var_{V~mu}( h_1(V) ),  h_1(V) = E_{W~mu}[h(V,W)],  zeta_2 = Var(h).
If mu = Haar, then by O(d)-invariance h_1 is constant => zeta_1 = 0
  => Var(Delta) = 2 zeta_2/(N(N-1)) ~ N^{-2}.
Measured: slope -2.041 over N=4..512  (d=128,k=8, E[Delta]=3.85750 +- 1e-5).
Consequence: Haar-initialized swarms satisfy the mean-band constraint with
  quadratically decaying tail risk; the O(N^{-1}) concentration claimed in the
  research log (cycles 3, 14) is suboptimal — the truth is faster, for a
  structural reason (invariance), not just a better inequality.

## 3. Mean-field OU law for consensus-Phi  (E2b validation)

Phi (consensus mode, covariant Grassmannian SGD):
  Q_i <- orth( Q_i + eta (I - Q_i Q_i^T) Sbar Q_i + sigma Z_i ),  Sbar = (1/N) sum_j Q_j Q_j^T,
  Z_i tangential Gaussian, entry std sigma/sqrt(d) (column norm ~ sigma).

Stationary cloud near consensus W with per-direction rms angle theta:
  E[P_V] = cos^2(theta) P_W + (k/(d-k)) sin^2(theta) (I - P_W)  => top-k eigenspace = W.
Linearization at V=W: grad = (I - QQ^T) Sbar Q ~ -lambda * X  (X tangent perturbation),
  lambda = cos^2(theta) - (k/(d-k)) sin^2(theta) = 1 - O(theta^2 d/(d-k)) ~ 1.
Discrete OU: a = 1 - eta*lambda; Var(X) = sigma^2/(1-a^2).
Pairwise relative dynamics: contraction a, noise variance 2 sigma^2:
  E[d_G(V_i,V_j)^2] ~ 2k sigma^2 / (1 - a^2)
  =>  Delta_inf ~ sigma * sqrt( 2k / (eta*lambda*(2 - eta*lambda)) ).

Validation (eta=0.3, d=64, k=8, N=64, lambda=1 => factor 5.60):
  sigma=0.05: pred 0.280, meas 0.299 (+7%)
  sigma=0.10: pred 0.560, meas 0.588 (+5%)
  sigma=0.15: pred 0.840, meas 0.959 (+14%)   [nonlinear angle corrections]
Residual attributed to (i) discrete-vs-continuum, (ii) d_G vs linearized angles.

Admissible noise window (lambda~1):
  sigma_c(eps_c) = eps_c * sqrt(eta(2-eta)/(2k)),  sigma_delta(delta_m) = delta_m * sqrt(eta(2-eta)/(2k))
  => width ratio = delta_m/eps_c (scale-free); with eta=0.3,k=8: factor sqrt(0.51/16)=0.1785.
     eps_c=0.902 => sigma_c = 0.161 ; delta_m=3.247 => sigma_delta = 0.580 (beyond linear regime, saturates at Haar).

## 4. Finite-N binding: swarm size controls effective coupling (E3/E3b)

Mean-field assumes Sbar ~ E[P_V]. With N samples, Sbar fluctuates; at small N
the "collective attractor" is too jittery to bind => stationary spread inflates.
E3 (Haar-init, T=250): Delta_inf(sigma=0.02): N=4: 2.10, N=8: 1.46, N=16: 0.75,
  N=64: ~0.12, MF-limit 0.104.  => binding strengthens with N; collapse risk
  (Delta_inf < eps_c) INCREASES with N, while span/PR INCREASES with N.
  => genuine two-sided tension: N buys span but buys collapse.
P_collapse(N=4/8/16 at sigma=0.05) = 0.005 / 0.156 / 0.750.

## 5. Omega* reading (to be filled with e3b data)

- Delta_0 must lie in [eps_c, delta_m] (t=0 constraint; Haar init = 3.61 > delta_m is
  inadmissible — a common practical mistake).
- At fixed Phi(eta,sigma): admissible N is bounded ABOVE (binding collapse) —
  N <= N_max(sigma); objective (PR) increasing in N => N* = N_max(sigma).
- Path dependence: collapse from an admissible Delta_0 is autocatalytic
  (isotropy of Sbar at large spread slows early collapse; clustering sharpens
  Sbar and accelerates binding) => Delta_0 near delta_m is transiently safest,
  Delta_0 near eps_c nucleates fastest (to be confirmed by t_collapse columns).

## 6. Corrected mean-field derivation (v2, careful tangent calculus)

Tangent space at V ≅ Hom(V, V⊥); noise column norm σ spreads over (d−k) directions:
  E[Θ_lm²] = σ²(1−1/d) / ((d−k)(1−a²)),   a = 1 − ηλ   (discrete OU per entry).

Two-particle relative: var ×2, contraction a (both drift toward S̄):
  d_G(V_i,V_j) = ||ΔΘ||_F + O(||ΔΘ||³)   (principal angles = singular values of ΔΘ)
  =>  E[d_G²] ≈ 2kσ²(1−1/d) / (1−a²)
  =>  **Δ_∞ = σ·√( 2k(1−1/d) / (ηλ(2−ηλ)) )**

λ = c² − (k/(d−k))s² ≈ 1 − θ̄²d/(d−k); with θ̄² from above λ ≈ 1 − O(σ²/d) ≈ 1.
  2D check (k=1,d=2): exact rate λ = cos 2θ̄ ✓.

Prediction at (k=8,d=64,η=0.3,λ=1): √(2·8·0.984/0.51) = 5.56; measured 6.00 (+8%).
  Residual candidates: (i) retraction 2nd-order (η²), (ii) geometric d_G vs ||ΔΘ|| at
  Δ_∞ ~ 0.5–1 (||ΔΘ|| entries ~0.2). TESTABLE SEPARATELY (E7): in task mode,
  Θ_i = U^TQ_i is directly measurable -> compare ||ΔΘ||_F (dynamics) vs d_G (geometry)
  vs OU formula (theory).  η-dependence distinguishes (i): retraction error ~η².

Collapse boundary, self-consistent: σ_c solves Δ_∞(σ_c) = ε_c with the FULL
nonlinear Δ_∞(σ) (ratio drifts 5.6 -> 7.0 as σ: 0.05 -> 0.17, measured).
  Linear-UF only: σ_c = ε_c√(ηλ(2−ηλ)/(2k(1−1/d))) = 0.162 — overestimates the
  measured crossing (≈0.145) because the true ratio at the boundary is 6.3, not 5.56.

## 7. Statistical bias found in e3b/e6 boundary measurement (to fix in E8)

P_collapse was defined via min_t Δ̂_t with Δ̂ estimated from 1024 random pairs
(SE ≈ 0.04). min over 16 tracked points of a noisy estimator is downward-biased
by ≈ SE·√(2 ln 16) ≈ 0.14  => cells with true min_t Δ near ε_c get inflated
P_collapse => the boundary σ_c(N) measured too LOW. Fix: define collapse by
converged final Δ_T (unbiased), long T, no min-tracking; Wilson intervals.

## 8. v3 — EXACT tangent-projection factor (E7 validation)

E[r_l^2] for tangentially projected noise: E||z - QQ^Tz||^2 = sigma^2 (1 - k/d)
  (NOT (1-1/d): the projection removes k/d, one fraction per column).
Per-entry: E[Theta_lm^2] = sigma^2 (1-k/d) / ((d-k)(1-a^2)).

=>  **Delta_inf = sigma * sqrt( 2k (1-k/d) / (eta*lambda*(2-eta*lambda)) )**

E7 task-mode validation (dG vs ||dTheta|| agree to 0.4%; OU vs measurement to <1%):
  eta=0.10: pred 8.58, measured 8.58 (s=0.03)
  eta=0.30: pred 5.24, measured 5.23
  eta=0.45: pred 4.48, (pending)
Geometric correction d_G/||dTheta|| grows with sigma (8.58->8.85 for s=0.03->0.3 at eta=0.1).

Consensus-mode ratio (N=64) is ~6.0 > 5.24: finite-N mean jitter adds effective
noise to the relative dynamics -> collapses faster than mean field (E3b trend: increases with N).

Corrected MF collapse threshold: sigma_c = eps_c / fac = eps_c * sqrt(eta(2-eta)/(2k(1-k/d)))
  = 0.902 * sqrt(0.51/(16*0.875)) = 0.1722  (k=8,d=64,eta=0.3). Unbiased e8 scan decides.

## 9. FINAL: einsum bug + resolution

"rndk,rnel->rde" summed k,l independently => Sbar was sum of rank-1 column-sum
outer products (basis-DEPENDENT, not an operator on Gr^N). All batched consensus
runs before the fix were invalid; the seed paradox (0.51 vs 0.86 survival for two
seeds, 12 sigma apart) was its fingerprint. Post-fix:
  - seed paradox gone (both seeds identical to 3 decimals);
  - consensus backbone == task-mode exact law for ALL N>=8 (I=1.006);
  - boundaries sharp and deterministic (Pc: 1.0 at sigma=0.14, 0.0 at 0.18);
  - eta=0.1: total collapse for sigma<0.105 (=eps_c/8.58); private rho does NOT rescue;
  - artifact-era claims RETRACTED: metastability, noise catalysis, N-binding,
    Delta_0 nucleation protection, synchronized cliffs.
Unit-test guard added: batched-vs-single equivalence + covariance under
within-subspace rotations.
