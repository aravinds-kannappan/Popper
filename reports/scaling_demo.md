# Scaling Popper with AI-safety principles

## 1. Sleeper Agents -> adaptive search for rare-trigger bugs

Uniform Monte-Carlo needs ~1/p draws to hit a trigger of probability p. Cross-Entropy-Method search steers draws to the low-margin boundary.

| claim | gold | uniform found | uniform draws | adaptive found | adaptive draws | speedup |
|---|---|---|---|---|---|---|
| `rare_edge_p0.05` | FALSIFIED | True | 36 | True | 18 | 2x |
| `rare_edge_p0.01` | FALSIFIED | True | 41 | True | 20 | 2x |
| `rare_edge_p0.002` | FALSIFIED | True | 41 | True | 20 | 2x |
| `rare_edge_p0.0005` | FALSIFIED | True | 403 | True | 20 | 20x |
| `rare_edge_p0.0001` | FALSIFIED | True | 5756 | True | 20 | 288x |
| `needle_dim3` | FALSIFIED | True | 182 | True | 190 | 1x |
| `needle_dim5` | FALSIFIED | True | 3165 | True | 632 | 5x |
| `rare_edge_faithful` | FAITHFUL | False | 20000 | False | 20000 | inf |

## 2. Reward Hacking -> active search for a spec-gaming implementation

| task | hacked | hacker | acceptance | agreement | margin | verdict |
|---|---|---|---|---|---|---|
| `sort_by_length` | True | `all_zeros` | 1.00 | 0.15 | 0.85 | VACUOUS |
| `max_lower_bound_only` | True | `max_plus_one` | 1.00 | 0.00 | 1.00 | INCOMPLETE |
| `abs_value` | False | `-` | 0.00 | 0.00 | 0.00 | FAITHFUL |
| `abs_strictly_positive` | False | `-` | 0.00 | 0.00 | 0.00 | FAITHFUL |

## 3. Safe RLHF -> constrained faithfulness score (reward - lambda*cost)

| task | reward | cost | objective | constraint | verdict |
|---|---|---|---|---|---|
| `sort_by_length` | 1.00 | 1.00 | -3.00 | VIOLATED | INCOMPLETE |
| `max_lower_bound_only` | 1.00 | 0.50 | -1.00 | VIOLATED | INCOMPLETE |
| `abs_value` | 1.00 | 0.00 | +1.00 | ok | FAITHFUL |
| `abs_strictly_positive` | 0.94 | 0.00 | +0.94 | ok | UNSOUND |

## 4. Scalable Debate -> a cheap verifier recovers the missing premise

```
=== debate: gibbs_dropped_normalization -> FALSIFIED (premise: sum_q_eq_1) ===
  [falsifier] counterexample after 1 draws: q=[1.833, 0.585, 1.435] (sum=3.854 != 1) => KL=-1.2638 < 0
  [defender ] add premise 'q0_small'; the witness violates it, so it was the missing hypothesis
  [verifier ] premise 'q0_small' rejected: still falsifiable (q=[0.1, 0.517, 1.528] (sum=2.145 != 1) => KL=-0.0274 < 0)
  [defender ] add premise 'sum_q_eq_1'; the witness violates it, so it was the missing hypothesis
  [verifier ] premise 'sum_q_eq_1' holds up under 4000+4000 draws; Defender wins
```

## 5. Bridge -> calibrate a guessing judge against the executable oracle

On 120 math items (synthetic judge, declared bias, no witness):

- judge accuracy vs oracle: **0.82**, kappa **0.63**, flag-bias **+0.00**
- ensemble (oracle witness wins, judge discounted by bias) keeps **66/66** of the oracle's true catches


## 6. Model Eval -> risk card and PROVE / REPAIR / REJECT gate

| task | capability | propensity | risk | gate | verdict |
|---|---|---|---|---|---|
| `sort_by_length` | 1.00 | 1.00 | 1.00 | **REJECT** | VACUOUS |
| `max_lower_bound_only` | 1.00 | 1.00 | 1.00 | **REPAIR** | INCOMPLETE |
| `abs_value` | 1.00 | 0.00 | 0.00 | **PROVE** | FAITHFUL |
| `abs_strictly_positive` | 0.94 | 0.00 | 0.06 | **REJECT** | UNSOUND |
