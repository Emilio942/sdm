# Optimal Manifold Diversity and Swarm Cardinality against Collapse
## Final Research Report (v2 — corrected operator)

**Date:** 2026-10-10 · **Compute:** 1× RTX 3060, ~24 h total · **Stack:** PyTorch 2.14.1+cu126
**Artifacts:** `sdm_lab/` (code, 18/18 unit tests + batched-consistency checks) · `results/` (40+ CSV/JSON) · `figures/final/` (F1–F4) · `sdm_lab/THEORY_NOTES.md` · `results/scoreboard.csv`

---

## Executive summary

For the model class Φ = consensus Grassmannian-SGD (a faithful abstraction of a
swarm of models repeatedly fine-tuned toward their collective representation), the
research problem P* receives a **complete, closed-form, and experimentally verified
answer**:

  **Δ_∞(σ) = σ·√( 2k(1−k/d) / (η(2−η)) )**  — stationary mean swarm diversity,

verified to **−0.1%** (task mode) and **+0.5%** (consensus mode), **independently of
N for N ≥ 8** (E17: ratio flat at 5.268–5.274 across N = 8…128 at σ=0.1). Both
boundaries of the admissible σ-window are sharp and deterministic:

  **collapse edge  σ_c = ε_c / 5.24 = 0.172** (measured crossing ∈ (0.16, 0.18),
  Wilson CIs [0.985,1] vs [0, 0.015]),
  **divergence edge σ_δ ≈ 0.43** (measured 0.42–0.43; the linear law's 0.62 is
  corrected by the measured nonlinear backbone).

The admissible initial states are **Ω\* = {Δ₀ ∈ [ε_c, δ_m]} × {N ≥ N_sat} ×
{σ ∈ (σ_c, σ_δ)}** with N_sat set by span saturation (Nk ≳ d) — there is **no
upper N constraint**: the "large swarms collapse more" effect was an artifact
(§3). The span objective increases with σ ⇒ the optimum sits at the divergence
edge, not the collapse edge — a reversal of the earlier (artifact-era) conclusion.

Along the way: an exact-law validation at −0.1% (E7), the U-statistic dichotomy
N⁻² vs N⁻¹ with quantitative Hoeffding validation (E1/E5), three refuted claims
from the original research log, and a cautionary tale about a silent einsum bug
that fabricated an entire phenomenology (§3) — caught by a seed-reproducibility
anomaly and fixed with new unit-level cross-checks.

---

## 1. Model and operators

Swarm: V_i ∈ Gr(k,d), bases Q_i ∈ R^{d×k}. Δ(S) = mean pairwise geodesic distance.
Φ (consensus mode, covariant Grassmannian-SGD):

  Q_i ← orth( Q_i + η (I−Q_iQ_iᵀ) S̄ Q_i + σ Z_i ),   S̄ = (1/N) Σ_j Q_j Q_jᵀ,

Z_i tangential Gaussian (column norm σ). Task mode: S̄ = WWᵀ fixed. Private mode
(E13): + ρ·(I−Q_iQ_iᵀ)W_iW_iᵀQ_i with fresh private subspaces.
Settings: d=64, k=8, η∈{0.1,0.3,0.45}, thresholds ε_c=0.902, δ_m=3.247
(= 0.25/0.90 × μ_Haar=3.6078). All batched operators now cross-validated against
single-swarm references and O(d)-covariance (post-fix, see §3).

## 2. Results (all from the corrected operator)

### R1 — Exact stationary law, one law for both modes (E7 + E16)
Task mode (E7): ‖ΔΘ‖_F/σ = 8.577/5.235/4.475 vs exact √(2k(1−k/d)/(η(2−η))) =
8.584/5.239/4.480 at η = 0.1/0.3/0.45 — **−0.1% each**. Geometry d_G = ‖ΔΘ‖_F
verified to 0.01% at small σ; the O(σ²) geometric growth measured (+1.4% at
σ=0.3, η=0.1) and separated from dynamics (fig. F1 left, fig. F4 repo).

### R2 — N-independence of the stationary state (E17, E19)
At σ=0.1 (linear regime): Δ_∞/σ = 5.268, 5.269, 5.270, 5.274, 5.273 for
N = 8, 16, 32, 64, 128 (sd ≤ 0.003) — **flat, I = 1.006**. E19: N=16 vs N=128
agree to 0.15% at every σ and both Δ₀ ∈ {1.0, 2.6}; e.g. Δ_T(σ=0.1) =
0.5263/0.5271/0.5269/0.5271 across four independent (Δ₀, N) cells.

### R3 — Sharp deterministic boundaries; the window (E16)
Consensus N=128: collapse probability is exactly 1.0 for σ ≤ 0.16 (Wilson CI
[0.985, 1.0]) and exactly 0.0 for σ ≥ 0.18 (CI [0, 0.015]) — the crossing sits at
σ_c = 0.172 = ε_c·√(η(2−η)/(2k(1−k/d))), predicted. Divergence edge σ_δ ≈ 0.43
(measured; linear law alone would say 0.62 — the nonlinear backbone matters).
**Admissible window at N=128: σ ∈ (0.172, 0.43).** Population homogeneity: the
Δ_T sd at stationarity is ≤ 0.003 — the fate of the swarm is deterministic given
(σ, η, N), not a per-rep coin flip (fig. F1 right).

### R4 — U-statistic dichotomy (stands; task-mode, unaffected by the bug)
Haar-initialized swarms: Var(Δ₀) ~ N^−2.04 (degenerate U-statistic, ζ₁=0 by
invariance). Trained (non-invariant) stationary swarms: Var(Δ) ~ N^−1.076 with the
un-fitted Hoeffding prediction matching to 0.80–0.97 (fig. F4). Log cycles 3/14
claimed exp(−cN) — the correct statement is a structural dichotomy.

### R5 — Weak coupling: total collapse, no private-data rescue (E13 corrected)
At η=0.1, N ∈ {16,64}: **every** mechanism (σ = 0.01/0.03, ρ = 0.05/0.1/0.2,
mixed) ends in complete collapse (P_surv = 0 at T=1200; Δ_T = 0.086–0.57 ≪ ε_c),
identical across N to 4 decimals. The corrected prediction is simply
Δ_∞ = 8.58·σ < ε_c ⟺ σ < 0.105 — collapse is the stationary fate, not a
metastable accident. Private data pulls are *not* a stabilizer: they are just
another fluctuation source with measured efficiency ≈ Δ_∞/ρ ≈ 2.9 (vs 8.58 for
noise per unit weight — private kicks project only partially onto the tangent of
the consensus geometry).

### R6 — Span behavior
Effective span (PR) stays at the core level (PR ≈ 8 ≈ k) for the whole collapsed
regime, rises only with Δ_∞ (PR ≈ 42 at Haar-full diversity, N=128). Rank saturates
at d once Nk ≳ d regardless of σ ≥ σ_c. **Consequence for P\*: maximizing span
pushes σ to the divergence edge** — the opposite corner from the artifact-era
conclusion.

### R7 — Negative results (all re-verified post-fix where applicable)
1. **Packing/ETF initialization: no effect** (E4 rerun post-fix: P_collapse and
   Δ_T identical to random at matched Δ₀=1.6; min-distance +3.5% — outcome-neutral).
2. **Haar initialization is inadmissible**: Δ₀ = 3.61 > δ_m = 3.25 — instant
   consensus-failure violation (P_diverge = 1 at t=0).
3. **exp(−cN) concentration (log cycles 3/14): wrong** — replaced by the
   N⁻²/N⁻¹ dichotomy (R4).
4. **"Large N collapses more", "metastability", "noise catalysis",
   "Δ₀ nucleation protection" (artifact-era findings, §3): all retracted** — each
   was a property of the broken operator, not of the swarm problem.

## 3. The bug hunt (methodological centerpiece)

A seed-reproducibility anomaly (two runs differing 12σ in survival) triggered an
audit that uncovered `einsum("rndk,rnel->rde")` computing Σ_n u_nu_nᵀ (u_n =
column sums) instead of Σ_n Q_nQ_nᵀ — a basis-**dependent** operator, hence not a
valid operator on Gr(k,d)^N. Every batched consensus experiment run before the fix
(e2b, e3b, e6, e8, e10–e15, e4, e9) inherited it. The bug produced a rich but
fictitious phenomenology: metastable survival, noise-catalyzed collapse,
N-dependent binding, seed-dependent fates. Post-fix, the chain is ergodic and
seed-independent (both seeds agree to 3 decimals), the stationary state is
N-independent, boundaries are sharp and theory-predicted. **Lesson institutionalized
in `sdm_lab/test_core.py`**: batched-vs-single equivalence and covariance checks are
now unit tests. The artifact era is retained in `results/` as a cautionary dataset;
all figures from it are superseded by `figures/final/`.

## 4. Answer to P\* (final form)

With fac = √(2k(1−k/d)/(η(2−η))) and the measured backbone Δ_∞(σ):

  **Ω\* = { (Δ₀, N, σ): Δ₀ ∈ [ε_c, δ_m] (t=0);  ε_c < Δ_∞(σ) < δ_m;  N·k ≳ d }**

- Δ₀ only needs to start in-band (final state is Δ₀-independent to 0.15%);
- the σ-window is **sharp** (deterministic edges): σ ∈ (0.172, 0.43) here;
- **N is free from above** — the objective (rank/PR) saturates for Nk ≳ d; there
  is no stability penalty for large N. The optimum: σ at the divergence edge
  (span maximal), any Δ₀ in-band, N ≈ d/k … a few ×d/k.
- At weak coupling the window closes at σ_c(η=0.1) = 0.105: below that, the band
  is unreachable at stationarity — the ∀t constraint fails by design, not by
  fluctuation.

## 5. Scoreboard

| quantity | theory | measured | dev |
|---|---|---|---|
| E[Σ sin²θₗ] = k−k²/d (exact) | 7.0000 | 7.0001 | +0.0% |
| Δ_∞/σ task mode, η=0.1/0.3/0.45 | 8.584/5.239/4.480 | 8.577/5.235/4.475 | −0.1% |
| Δ_∞/σ consensus, N=128 (σ ≤ 0.12) | 5.239 | 5.24–5.29 | ≤+1% |
| Δ_∞/σ consensus, N=8…128 (σ=0.1) | 5.239 | 5.268–5.274 | +0.6% |
| d_G/‖ΔΘ‖_F (small σ) | 1 | 1.0001 | +0.0% |
| Var(Δ₀) slope, Haar | −2 | −2.041 | +2% |
| Var(Δ) slope, trained | −1 | −1.076 | +8% |
| collapse crossing σ_c | 0.172 | ∈ (0.16, 0.18) | ✓ |
| σ_c(k=4) = ε_c/fac | 0.178 | 0.176 | −1.1% |
| σ_c(k=16) = ε_c/fac | 0.166 | 0.165 | −1.0% |
| divergence crossing σ_δ | (linear: 0.62) | 0.42–0.43 | nonlinear regime |

## 6. Figures (`figures/final/`)

F1 backbone + window · F2 N-independence + (Δ₀,N)-collapse · F3 weak-coupling
survival (corrected) · F4 concentration dichotomy. (Earlier `figures/*.png` are
artifact-era; retained for the record only.)

## 7. Limitations & next steps

- The nonlinear backbone near the δ_m edge is measured, not derived (a
  self-consistent λ(σ) + saturation ansatz would close the upper-edge form).
- k/d-scaling is CLOSED post-fix (E20): σ_c(k=4)=0.176 vs 0.178 predicted (−1.1%),
  σ_c(k=16)=0.165 vs 0.166 (−1.0%) — sharp deterministic edges, sd ±0.003.
- Private-mode theory (measured Δ_∞/ρ ≈ 2.9) is empirical; the projection factor
  for rank-k private pulls is derivable with the same tangent calculus.
- Single Φ topology; heterogeneous/directed coupling unexplored (new research,
  not a gap in this program).

## 8. Reproducibility (corrected pipeline)

| file | content |
|---|---|
| `test_core.py` | unit tests incl. batched-vs-single + covariance checks |
| `e1_init_distribution.py` | Haar laws, concentration, d_min (stands) |
| `e7_decomposition.py` | exact-law decomposition (stands; task mode) |
| `e16_corrected_core.py` | **backbone + sharp boundary (N=128)** |
| `e17_inflation_linear.py` | **N-independence scan** |
| `e19_omega_corrected.py` | **(Δ₀, N) invariance + edges** |
| `e13_rho_stabilization.py` | weak-coupling: total collapse, no ρ-rescue |
| `e4_init_comparison.py` | packing negative result (rerun post-fix) |
| `figures_final.py`, `scoreboard.py` | final figures + scoreboard |
| superseded: `e2b, e3b, e6, e8, e10, e11, e12, e14, e15, e9` | artifact-era (einsum bug) |
