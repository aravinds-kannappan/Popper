"""The offline task model and its evaluator.

* :class:`Task` - a Verina-style task carrying executable Python models so the
  oracle's decision logic runs without a Lean toolchain.
* :class:`MockAxleClient` - evaluates the Python model over test + fuzzed inputs.

The live counterpart (real Lean checking over the API) is
:class:`falsify.live.axle.AxleClient`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

Args = tuple


@dataclass
class Task:
    """A verifiable-coding task (Verina format) with an executable model."""

    name: str
    description: str
    signature: str
    reference: str                              # key into impls_* naming the correct impl
    spec: str                                   # key into spec_* naming the spec under audit
    impls_py: dict[str, Callable[..., Any]]     # name -> fn(*args)
    spec_py: dict[str, Callable[[Args, Any], bool]]  # name -> fn(args, output) -> bool
    test_inputs: list[Args]
    gen_input: Callable[[random.Random], Args]
    wrong_impls: list[str] = field(default_factory=list)   # known-incorrect impls (mutants)
    arbitrary: Optional[str] = None             # an "anything goes" impl; if it passes ⇒ vacuous
    lean: dict[str, str] = field(default_factory=dict)     # optional Lean source (display/live)
    fuzz_n: int = 200

    def output(self, impl: str, args: Args) -> Any:
        return self.impls_py[impl](*args)

    def differs_from_reference(self, impl: str, inputs: list[Args]) -> Optional[Args]:
        for a in inputs:
            if self.impls_py[impl](*a) != self.impls_py[self.reference](*a):
                return a
        return None


@dataclass
class SpecCheckResult:
    satisfied: bool
    counterexample: Optional[dict] = None  # {"input": ..., "output": ...}
    detail: str = ""


class MockAxleClient:
    """Offline backend: evaluates the task's executable Python model."""

    live = False

    def __init__(self, seed: int = 0):
        self.seed = seed

    def spec_satisfied(self, task: Task, impl: str, spec: Optional[str] = None) -> SpecCheckResult:
        spec_name = spec or task.spec
        predicate = task.spec_py[spec_name]
        rng = random.Random(self.seed)
        inputs = list(task.test_inputs) + [task.gen_input(rng) for _ in range(task.fuzz_n)]
        for args in inputs:
            out = task.output(impl, args)
            if not predicate(args, out):
                return SpecCheckResult(
                    satisfied=False,
                    counterexample={"input": args, "output": out},
                    detail=f"spec '{spec_name}' violated by impl '{impl}'",
                )
        return SpecCheckResult(satisfied=True, detail=f"impl '{impl}' satisfies spec '{spec_name}'")
