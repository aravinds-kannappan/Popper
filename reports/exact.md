# M4: exact falsification, certificates, type-directed generation, trained adversary

## 1a. Exact SMT engine -> exact counterexample or a real certificate

| claim | verdict | backend | certificate | counterexample |
|---|---|---|---|---|
| `abs_strictly_positive` | FALSIFIED | enum | False | x=0: abs(x)=0 is rejected by out > 0 (UNSOUND) |
| `abs_value_faithful` | FAITHFUL | enum | True | - |
| `max_lower_bound_only` | FALSIFIED | enum | False | a=-6, b=-6: max+1=-5 satisfies the spec but != max=-6 (INCOMPLETE) |
| `rare_int_needle` | FALSIFIED | enum | False | n=7 is the single rejecting input (1 in 20,001) |
| `mean_nonneg_overclaim` | FALSIFIED | fourier-motzkin | False | x0=-1, x1=0: mean < 0 |
| `nonneg_sum_certificate` | FAITHFUL | fourier-motzkin | True | - |
| `amgm_flipped_nonlinear` | INCONCLUSIVE | - | False | - |

## 1b. PAC certificate -> survived draws become a bug-rate bound

A faithful statement that survives sampling: with 95% confidence, bug rate <= 0.001 (0 hits in 3000 draws, clopper-pearson).

| clean draws | bug-rate upper bound (95%) |
|---|---|
| 100 | 0.03 |
| 1,000 | 0.003 |
| 3,000 | 0.001 |
| 10,000 | 0.0003 |
| 50,000 | 6e-05 |

## 2. Type-directed generation -> audit a signature with no hand-written fixture

- signature `max2 : Int -> Int -> Int` parses to argument types `['TInt', 'TInt']`
- small-scope enumeration (scope 1) gives 9 inputs, e.g. [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0)]
- the oracle, fed only generated inputs, returns **INCOMPLETE**: impl 'max_plus_one' passes the spec; differs from reference at input (-1, -1)

## 3. Trained adversary -> learn which hacks pay off, transfer across tasks

Over a stream of 24 tasks, candidate evaluations before a catch:

- fixed-order baseline: **216**
- UCB bandit + transfer memory: **151** (30% fewer)

Learned family values (1.0 = always caught a bug):

| family | value | pulls |
|---|---|---|
| identity | 0.33 | 18 |
| declared | 0.33 | 18 |
| const | 0.00 | 13 |
| reverse | 0.00 | 13 |
| negate | 0.00 | 13 |
| off_by_one | 0.00 | 13 |

Trigger-structure search on a 5-D conjunctive sleeper:

- needle_dim5: trigger is a conjunction over coords [0, 1, 2, 3, 4] (proposal mean [0.22, 0.22, 0.19, 0.2, 0.17])

