# Spec-faithfulness benchmark

_334 labelled claims across math (320), code (4), verina (10). The task: flag the unfaithful specs, leave the faithful ones alone._

## Headline

| judge | unfaithful caught (recall) | false positives | counterexample yield | F1 |
|---|---|---|---|---|
| Popper | 168/168 (100%) | 0/163 (0%) | 100% | 1.00 |
| Proof checker (AXLE/Lean) | 0/168 (0%) | 0/163 (0%) | 0% | 0.00 |

_LLM judge not run in this pass (no ANTHROPIC_API_KEY). For a published reference point, the Verina paper reports the best general model reaching about 52% combined specification soundness and completeness, and it returns no counterexample. Re-run with `--llm` to fill the row from a live model._

## What the numbers mean

- **Recall** is the fraction of unfaithful specs the judge flagged. The proof checker cannot flag any, by construction, so it scores zero however good the prover is.
- **False positives** are faithful specs wrongly flagged. Lower is better.
- **Counterexample yield** is the fraction of true detections that came with a concrete witness you can act on. Only Popper produces these.

## By kind of bug

| bug | count | Popper | Proof checker (AXLE/Lean) |
|---|---|---|---|
| direction-error | 122 | 122/122 | 0/122 |
| over-claim | 26 | 26/26 | 0/26 |
| dropped-hypothesis | 17 | 17/17 | 0/17 |
| vacuous | 1 | 1/1 | 0/1 |
| incomplete | 1 | 1/1 | 0/1 |
| unsound | 1 | 1/1 | 0/1 |

## By surface

| surface | unfaithful | Popper | Proof checker (AXLE/Lean) |
|---|---|---|---|
| math | 165 | 165/165 | 0/165 |
| code | 3 | 3/3 | 0/3 |
| verina | 0 | 0/0 | 0/0 |

## Sample of caught specs

_24 of 171 unfaithful items; full table in results/benchmark.csv._

| item | surface | gold | Popper | Proof checker (AXLE/Lean) | counterexample |
|---|---|---|---|---|---|
| `kl_DROPPED_norm_k2` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=2.04!=1 => KL=-0.695 < 0 |
| `kl_FLIPPED_k2` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.018 > 0 |
| `kl_DROPPED_norm_k3` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=3.53!=1 => KL=-1.154 < 0 |
| `kl_FLIPPED_k3` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.106 > 0 |
| `kl_DROPPED_norm_k4` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=6.01!=1 => KL=-1.662 < 0 |
| `kl_FLIPPED_k4` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.131 > 0 |
| `kl_DROPPED_norm_k5` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=7.66!=1 => KL=-1.944 < 0 |
| `kl_FLIPPED_k5` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.091 > 0 |
| `kl_DROPPED_norm_k6` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=10.68!=1 => KL=-2.226 < 0 |
| `kl_FLIPPED_k6` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.142 > 0 |
| `kl_DROPPED_norm_k7` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=11.44!=1 => KL=-2.245 < 0 |
| `kl_FLIPPED_k7` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.192 > 0 |
| `kl_DROPPED_norm_k8` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=13.14!=1 => KL=-2.442 < 0 |
| `kl_FLIPPED_k8` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.134 > 0 |
| `kl_DROPPED_norm_k9` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=17.39!=1 => KL=-2.676 < 0 |
| `kl_FLIPPED_k9` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.180 > 0 |
| `kl_DROPPED_norm_k10` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=20.77!=1 => KL=-2.914 < 0 |
| `kl_FLIPPED_k10` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.119 > 0 |
| `kl_DROPPED_norm_k11` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=21.17!=1 => KL=-2.846 < 0 |
| `kl_FLIPPED_k11` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.207 > 0 |
| `kl_DROPPED_norm_k12` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=24.40!=1 => KL=-3.054 < 0 |
| `kl_FLIPPED_k12` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.140 > 0 |
| `kl_DROPPED_norm_k13` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | sum q=25.28!=1 => KL=-3.116 < 0 |
| `kl_FLIPPED_k13` | math | `FALSIFIED` | `FALSIFIED` | `FAITHFUL` | KL=0.113 > 0 |

> Popper falsifies; it does not certify. A FAITHFUL verdict means no counterexample was found within the search budget.

