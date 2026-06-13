# %% [markdown]
# # Popper — falsify the spec, then verify the proof
#
# *Popper* is the system; **`falsify`** is the package that implements it. This
# notebook runs the whole thing end to end:
#
# 1. the **numerical oracle** (math),
# 2. the **offline code-spec oracle**,
# 3. **M2** counterexample-guided repair, and
# 4. the **live Verina audit over the Axiom Lean Engine (AXLE)**.
#
# A Lean checker answers *"is this proof valid?"*. Popper adds *"is this statement
# faithful and worth proving?"* — an executable oracle that returns counterexamples.

# %%
import os
import sys

for p in (os.path.abspath("."), os.path.abspath("..")):
    if p not in sys.path:
        sys.path.insert(0, p)

import falsify
print("falsify", falsify.__version__)

# %% [markdown]
# ## 1. Numerical oracle (math)
#
# Faithful information-theory statements survive Monte-Carlo falsification;
# unfaithful ones (a dropped hypothesis, a flipped direction) are refuted with the
# concrete violating instance.

# %%
from falsify import NumericalOracle, information_theory_library, run_audit

rep = run_audit(information_theory_library(), NumericalOracle(),
                "Numerical oracle — information theory")
print(rep.render_terminal())

# %% [markdown]
# ## 2. Offline code-spec oracle
#
# Soundness / completeness / vacuity on representative Verina-style tasks,
# evaluated against an executable model (no Lean toolchain needed).

# %%
from falsify import CodeSpecOracle, MockAxleClient, verina_like_tasks

rep = run_audit(verina_like_tasks(), CodeSpecOracle(MockAxleClient()),
                "Code-spec oracle — offline fixtures")
print(rep.render_terminal())

# %% [markdown]
# ## 3. M2 — counterexample-guided repair
#
# Each unfaithful spec is driven to FAITHFUL using the oracle's counterexample.

# %%
from falsify import default_repairer, repair_loop

oracle = CodeSpecOracle(MockAxleClient())
for task in verina_like_tasks():
    print(repair_loop(task, oracle, default_repairer()).render())

# %% [markdown]
# ## 4. Live Verina audit over AXLE
#
# Real benchmark tasks, real Lean. Each task's `expected` / `unexpected` outputs
# become `native_decide` witnesses checked through the Axiom Lean Engine:
# **UNSOUND** if a correct output is rejected, **INCOMPLETE** if a wrong one is
# accepted. Requires `pip install axiom-axle` and `AXLE_API_KEY`.

# %%
from falsify import run_live_audit

if os.environ.get("AXLE_API_KEY"):
    report = run_live_audit(limit=5, max_tests=1, max_unexpected=2, progress=False)
    print(report.render_terminal())
else:
    print("Set AXLE_API_KEY (and `pip install axiom-axle`) to run the live audit.")

# %% [markdown]
# ## Honesty
#
# Popper *falsifies*; it does not certify. **FAITHFUL** = no counterexample within
# the search budget. **INCONCLUSIVE** = the spec isn't `Decidable` on some witness.
# Lean/AXLE remains the ground truth for the *proof*.
