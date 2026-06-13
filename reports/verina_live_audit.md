# Live Verina spec-faithfulness audit (AXLE)

_oracle: `verina-live` — 10 claims | ✓ FAITHFUL 8  ? INCONCLUSIVE 2_

| | verdict | claim | reason / counterexample |
|---|---|---|---|
| ✓ | `FAITHFUL` | `verina_basic_1` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_basic_2` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ? | `INCONCLUSIVE` | `verina_basic_3` | spec not decidable on some witnesses (no Decidable instance / timeout) |
| ✓ | `FAITHFUL` | `verina_basic_4` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_basic_5` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_basic_6` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_basic_7` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ✓ | `FAITHFUL` | `verina_basic_8` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |
| ? | `INCONCLUSIVE` | `verina_basic_9` | spec not decidable on some witnesses (no Decidable instance / timeout) |
| ✓ | `FAITHFUL` | `verina_basic_10` | correct outputs accepted; all wrong outputs rejected (on test witnesses) |

> Popper *falsifies*; it does not certify. A FAITHFUL verdict means no counterexample was found within the search budget — the dominant real-world failures (dropped hypotheses, vacuity, wrong direction, too-strong/too-weak specs) are exactly what it catches.
