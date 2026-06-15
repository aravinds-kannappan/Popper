# Spec-faithfulness benchmark

_38 labelled claims across math (24), code (4), verina (10). The task: flag the unfaithful specs, leave the faithful ones alone._

## Headline

| judge | unfaithful caught (recall) | false positives | counterexample yield | F1 |
|---|---|---|---|---|
| Popper | 14/14 (100%) | 0/22 (0%) | 100% | 1.00 |
| Proof checker (AXLE/Lean) | 0/14 (0%) | 0/22 (0%) | 0% | 0.00 |

_LLM judge not run in this pass (no ANTHROPIC_API_KEY). For a published reference point, the Verina paper reports the best general model reaching about 52% combined specification soundness and completeness, and it returns no counterexample. Re-run with `--llm` to fill the row from a live model._

## What the numbers mean

- **Recall** is the fraction of unfaithful specs the judge flagged. The proof checker cannot flag any, by construction, so it scores zero however good the prover is.
- **False positives** are faithful specs wrongly flagged. Lower is better.
- **Counterexample yield** is the fraction of true detections that came with a concrete witness you can act on. Only Popper produces these.

## Per-item verdicts

| item | surface | gold | Popper | Proof checker (AXLE/Lean) | counterexample |
|---|---|---|---|---|---|
| `kl_nonneg` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `kl_nonneg_DROPPED_normalization` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | q=[0.777, 1.534, 1.215] (Σq=3.525≠1) ⇒ Σ pᵢ·log(pᵢ/qᵢ) = -1.1543 < 0 |
| `data_processing` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `data_processing_DROPPED_markov` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | I(X;Z) = 0.8318 > I(X;Y) = 0.0478  (Z leaks X directly) |
| `entropy_concave` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `entropy_concave_WRONG_direction` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | H(λp+(1-λ)q) = 1.0797 > λH(p)+(1-λ)H(q) = 1.0600  (entropy is concave,... |
| `entropy_uniform_vacuous_guard` | math | `INCONCLUSIVE` | `INCONCLUSIVE` | `FAITHFUL` |  |
| `cauchy_schwarz` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `cauchy_schwarz_FLIPPED` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | (a.b)^2=0.0843 < |a|^2|b|^2=0.2061 |
| `am_gm` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `am_gm_FLIPPED` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | AM=2.0233 > GM=1.9374 |
| `triangle_ineq` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `triangle_ineq_FLIPPED` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | x=0.113, y=-0.951: |x+y|=0.838 < |x|+|y|=1.063 |
| `entropy_subadditive` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `entropy_subadditive_FLIPPED` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | H(X,Y)=2.1239 < H(X)+H(Y)=2.1619 |
| `mutual_info_nonneg` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `mutual_info_nonpos_WRONG` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | I(X;Y)=0.0381 > 0 |
| `cross_entropy_ge_entropy` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `cross_entropy_ge_entropy_FLIPPED` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | H(p,q)=1.1647 > H(p)=1.0590 |
| `jensen_log_concave` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `jensen_log_concave_FLIPPED` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | log(mean)=1.2155 > mean(log)=1.1721 |
| `variance_nonneg` | math | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `variance_mean_nonneg_WRONG` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | mean=-1.0829 < 0 for x=[-2.41, 0.11, -0.95] |
| `self_successor_vacuous` | math | `INCONCLUSIVE` | `INCONCLUSIVE` | `FAITHFUL` |  |
| `sort_by_length` | code | `VACUOUS` | `VACUOUS` | `FAITHFUL` | impl 'all_zeros' passes; spec fails to pin down the answer |
| `max_lower_bound_only` | code | `INCOMPLETE` | `INCOMPLETE` | `FAITHFUL` | impl 'max_plus_one' passes the spec; differs from reference at input (... |
| `abs_value` | code | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `abs_strictly_positive` | code | `UNSOUND` | `UNSOUND` | `FAITHFUL` | reference fails spec at input (0,) (→ output 0) |
| `verina_advanced_1` | verina | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `verina_advanced_10` | verina | `FAITHFUL` | `INCONCLUSIVE` | `FAITHFUL` |  |
| `verina_advanced_11` | verina | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `verina_advanced_12` | verina | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `verina_advanced_13` | verina | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `verina_advanced_14` | verina | `FAITHFUL` | `INCONCLUSIVE` | `FAITHFUL` |  |
| `verina_advanced_15` | verina | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `verina_advanced_16` | verina | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `verina_advanced_17` | verina | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |
| `verina_advanced_18` | verina | `FAITHFUL` | `FAITHFUL` | `FAITHFUL` |  |

> Popper falsifies; it does not certify. A FAITHFUL verdict means no counterexample was found within the search budget.

