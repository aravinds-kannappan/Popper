# Code-spec oracle — Verina-style tasks [offline model (MockAxleClient)]

_oracle: `codespec` — 4 claims | ✓ FAITHFUL 1  ✗ UNSOUND 1  ✗ INCOMPLETE 1  ✗ VACUOUS 1_

| | verdict | claim | reason / counterexample |
|---|---|---|---|
| ✗ | `VACUOUS` | `sort_by_length` | spec constrains nothing — even the throwaway impl 'all_zeros' satisfies it **⟵ impl 'all_zeros' passes; spec fails to pin down the answer** |
| ✗ | `INCOMPLETE` | `max_lower_bound_only` | spec is too weak — the wrong impl 'max_plus_one' satisfies it yet disagrees with the reference **⟵ impl 'max_plus_one' passes the spec; differs from reference at input (3, 5)** |
| ✓ | `FAITHFUL` | `abs_value` | reference passes; no wrong implementation slips through; not vacuous |
| ✗ | `UNSOUND` | `abs_strictly_positive` | spec is too strong — it rejects the correct reference implementation **⟵ reference fails spec at input (0,) (→ output 0)** |

> Popper *falsifies*; it does not certify. A FAITHFUL verdict means no counterexample was found within the search budget — the dominant real-world failures (dropped hypotheses, vacuity, wrong direction, too-strong/too-weak specs) are exactly what it catches.
