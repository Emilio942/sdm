# Optimal Manifold Diversity and Swarm Cardinality against Collapse

Autonomous computational research project: a complete, closed-form, and
experimentally verified answer to the formal problem **P\*** — characterizing the
admissible initial states (Δ₀, N) of a swarm of models whose subspaces
V_i ∈ Gr(k,d) evolve under recursive fine-tuning, such that the mean swarm
diversity Δ(S) stays within a prescribed band [ε_c, δ_m] (no manifold collapse,
no consensus failure) while the span of the union of subspaces is maximized.

**Start here:** [`report.md`](report.md) — final report (executive summary,
results, scoreboard, limitations).

## Headline result

For Φ = consensus Grassmannian-SGD (models repeatedly fine-tuned toward their
collective representation with SGD noise), the stationary mean swarm diversity
follows the exact law

```
Δ_∞ = σ · √( 2k(1 − k/d) / (η(2 − η)) )
```

validated to **−0.1%** (task-attractor mode), **≤ +1%** (consensus mode), and
**independently of N for N ≥ 8**. Both edges of the admissible σ-window are sharp
and deterministic (σ_c = ε_c / fac, measured −1% at k = 4, 8, 16), the final state
is independent of Δ₀ (which only has to start inside the band), and N is free from
above (span saturates once Nk ≳ d). A U-statistic dichotomy (Var ~ N⁻² for Haar
initialization vs N⁻¹ for trained swarms, with quantitative Hoeffding validation)
supplements the picture. Three claims from the original research log are refuted
along the way.

## Repository layout

| path | content |
|---|---|
| `report.md` | **final report** (start here) |
| `sdm_lab/core.py` | Grassmannian operations + covariant Φ (batched, GPU) |
| `sdm_lab/test_core.py` | mathematical unit tests (18/18, incl. batched-vs-single + covariance checks) |
| `sdm_lab/e*.py` | experiments E1–E20 (each rerunnable standalone) |
| `sdm_lab/analyze.py`, `figures_final.py`, `scoreboard.py` | figures + theory-vs-measurement scoreboard |
| `sdm_lab/THEORY_NOTES.md` | full derivations, incl. the two wrong factors caught and corrected |
| `results/` | all CSV/JSON outputs + `scoreboard.md` |
| `figures/final/` | publication-ready figures (F1–F4) |
| `figures/artifact_era/` | superseded figures, retained as a cautionary record |
| `sdm.md` | original research log (98 formal-verification cycles) |

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu126  # or cpu
pip install numpy scipy pandas matplotlib

cd sdm_lab
python test_core.py              # 18/18 mathematical self-tests
python e16_corrected_core.py     # headline measurement (~30 min GPU)
python figures_final.py          # final figures from corrected data
```

Hardware: developed and run on a single RTX 3060; total GPU budget ≈ 6 h.
Everything runs on CPU as well (slower).

## Scientific highlights

1. **Exact stationary law** for the swarm diversity, derived via tangent-space
   calculus on the Grassmannian and validated to −0.1% at three learning rates.
2. **U-statistic dichotomy**: Var(Δ₀) ~ N⁻² for Haar initialization (degenerate
   U-statistic, ζ₁ = 0 by rotational invariance) vs Var(Δ) ~ N⁻¹ for trained
   swarms, with the un-fitted Hoeffding prediction matching to 0.8–0.97.
3. **Sharp deterministic phase boundaries**: the collapse probability jumps from
   exactly 1 to exactly 0 across σ_c — the swarm's fate is deterministic given
   (σ, η, N).
4. **Refuted claims** (from the original log): exp(−cN) concentration rate
   (wrong: N⁻²/N⁻¹ dichotomy), packing/ETF initialization advantage (none at
   matched diversity), "large swarms collapse more" (artifact).
5. **A cautionary tale** (report §3): a silent einsum bug fabricated an entire
   phenomenology (metastability, noise catalysis, N-dependent binding) and was
   caught only through a seed-reproducibility anomaly — institutionalized now as
   batched-vs-single and covariance unit tests.

## Answer to P\*

```
Ω* = { (Δ₀, N, σ) :  Δ₀ ∈ [ε_c, δ_m]  (t = 0 constraint);
                     ε_c < Δ_∞(σ) < δ_m  (sharp, theory-predicted edges);
                     N·k ≳ d            (span saturation) }
```

There is no upper bound on N: the span objective pushes σ toward the divergence
edge while N simply buys saturation.

## License

None specified yet — contact the repository owner.
