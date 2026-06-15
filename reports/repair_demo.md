
=== M2: counterexample-guided spec repair ===

✓ sort_by_length: ✗VACUOUS  →  ✓FAITHFUL
      first counterexample: impl 'all_zeros' passes; spec fails to pin down the answer
✓ max_lower_bound_only: ✗INCOMPLETE  →  ✓FAITHFUL
      first counterexample: impl 'max_plus_one' passes the spec; differs from reference at input (3, 5)
✓ abs_value: ✓FAITHFUL
✓ abs_strictly_positive: ✗UNSOUND  →  ✓FAITHFUL
      first counterexample: reference fails spec at input (0,) (→ output 0)

repaired 3 unfaithful specs to FAITHFUL (4/4 faithful overall)
