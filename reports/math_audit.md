# Numerical oracle - information-theory ladder

_oracle: `numerical`, 7 claims | ✓ FAITHFUL 3  ✗ FALSIFIED 3  ? INCONCLUSIVE 1_

| | verdict | claim | reason / counterexample |
|---|---|---|---|
| ✓ | `FAITHFUL` | `kl_nonneg` | survived 2000 Monte-Carlo draws (2000 with hypothesis active) |
| ✗ | `FALSIFIED` | `kl_nonneg_DROPPED_normalization` | counterexample found; the formalized statement is false as written **⟵ q=[0.777, 1.534, 1.215] (Σq=3.525≠1) ⇒ Σ pᵢ·log(pᵢ/qᵢ) = -1.1543 < 0** |
| ✓ | `FAITHFUL` | `data_processing` | survived 2000 Monte-Carlo draws (2000 with hypothesis active) |
| ✗ | `FALSIFIED` | `data_processing_DROPPED_markov` | counterexample found; the formalized statement is false as written **⟵ I(X;Z) = 0.8318 > I(X;Y) = 0.0478  (Z leaks X directly)** |
| ✓ | `FAITHFUL` | `entropy_concave` | survived 2000 Monte-Carlo draws (2000 with hypothesis active) |
| ✗ | `FALSIFIED` | `entropy_concave_WRONG_direction` | counterexample found; the formalized statement is false as written **⟵ H(λp+(1-λ)q) = 1.0797 > λH(p)+(1-λ)H(q) = 1.0600  (entropy is concave, not convex)** |
| ? | `INCONCLUSIVE` | `entropy_uniform_vacuous_guard` | hypothesis satisfied in 0/2000 draws; conclusion never exercised (possibly vacuous) |

> Popper breaks statements; it does not certify them. A FAITHFUL verdict means no counterexample was found within the search budget. The common real-world failures (dropped hypotheses, vacuity, wrong direction, too-loose or too-tight specs) are exactly what it catches.
