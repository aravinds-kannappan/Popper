# Live Verina spec-faithfulness audit (AXLE)

_oracle: `verina-live`, 10 claims | ✓ FAITHFUL 8  ? INCONCLUSIVE 2_

| | verdict | claim | reason / counterexample |
|---|---|---|---|
| ✓ | `FAITHFUL` | `verina_advanced_1` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ? | `INCONCLUSIVE` | `verina_advanced_10` | spec not decidable on some witnesses (no Decidable instance / timeout) |
| ✓ | `FAITHFUL` | `verina_advanced_11` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_advanced_12` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_advanced_13` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ? | `INCONCLUSIVE` | `verina_advanced_14` | spec not decidable on some witnesses (no Decidable instance / timeout) |
| ✓ | `FAITHFUL` | `verina_advanced_15` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_advanced_16` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_advanced_17` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_advanced_18` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |

> Popper breaks statements; it does not certify them. A FAITHFUL verdict means no counterexample was found within the search budget. The common real-world failures (dropped hypotheses, vacuity, wrong direction, too-loose or too-tight specs) are exactly what it catches.
