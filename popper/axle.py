"""Backend for the code-specification oracle.

Two pieces live here:

* :class:`Task` — a Verina-style verifiable-coding task. It carries the Lean
  artifacts (signature, reference implementation, candidate specs, mutant
  implementations) *and*, for offline runs, executable Python models of each, so
  the oracle's decision logic can be exercised without a Lean toolchain.

* The AXLE backends, both exposing one primitive:
  ``spec_satisfied(task, impl, spec) -> SpecCheckResult``.
    - :class:`AxleClient` talks to the real Axiom Lean Engine over HTTP (stdlib
      ``urllib`` only). It reads ``AXLE_API_KEY`` from the environment. This is
      the live path; it builds a Lean obligation and uses AXLE's ``disprove`` /
      ``check`` verbs to look for a counterexample.
    - :class:`MockAxleClient` *evaluates the task's Python model* over the test
      inputs plus fuzzed inputs. It is a real evaluator of the modelled
      semantics — only the bridge to genuine Lean is stubbed — so the audit
      numbers it produces are real with respect to that model.

The oracle code in :mod:`popper.codespec` is identical regardless of backend.
"""

from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

Args = tuple


@dataclass
class Task:
    """A verifiable-coding task (Verina format)."""

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
    lean: dict[str, str] = field(default_factory=dict)     # optional Lean source (live path)
    fuzz_n: int = 200

    def output(self, impl: str, args: Args) -> Any:
        return self.impls_py[impl](*args)

    def differs_from_reference(self, impl: str, inputs: list[Args]) -> Optional[Args]:
        """First input where ``impl`` disagrees with the reference (proof it is wrong)."""
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


class AxleClient:
    """Live backend talking to the Axiom Lean Engine (https://axle.axiommath.ai).

    Network calls only happen when a method is invoked, so importing this module
    never requires connectivity. Get a free key at
    https://axle.axiommath.ai/app/console and ``export AXLE_API_KEY=...``.
    """

    live = True
    DEFAULT_BASE = "https://axle.axiommath.ai/v1"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 timeout: int = 120):
        self.api_key = api_key or os.environ.get("AXLE_API_KEY")
        self.base_url = (base_url or os.environ.get("AXLE_BASE_URL") or self.DEFAULT_BASE).rstrip("/")
        self.timeout = timeout
        self._cache: dict = {}
        if not self.api_key:
            raise RuntimeError(
                "AxleClient needs an API key. Set AXLE_API_KEY "
                "(free key at https://axle.axiommath.ai/app/console), "
                "or use MockAxleClient for the offline demo."
            )

    # -- raw API verbs (mirror the AXLE docs) ------------------------------- #
    def _post(self, endpoint: str, payload: dict) -> dict:
        key = (endpoint, json.dumps(payload, sort_keys=True))
        if key in self._cache:
            return self._cache[key]
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            data=data,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                out = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:  # surface AXLE's message
            raise RuntimeError(f"AXLE {endpoint} HTTP {e.code}: {e.read().decode()[:300]}") from e
        self._cache[key] = out
        return out

    def check(self, code: str) -> dict:
        """`check`: compile Lean code and report errors."""
        return self._post("check", {"code": code})

    def verify_proof(self, statement: str, proof: str) -> dict:
        """`verify_proof`: validate a proof against a formal statement."""
        return self._post("verify_proof", {"statement": statement, "proof": proof})

    def disprove(self, theorem: str) -> dict:
        """`disprove`: attempt to find a counterexample to a theorem."""
        return self._post("disprove", {"theorem": theorem})

    def theorem2sorry(self, code: str) -> dict:
        """`theorem2sorry`: strip proofs, leaving just the statements."""
        return self._post("theorem2sorry", {"code": code})

    # -- the oracle primitive ---------------------------------------------- #
    def spec_satisfied(self, task: Task, impl: str, spec: Optional[str] = None) -> SpecCheckResult:
        """Does ``impl`` satisfy ``spec`` for every valid input?

        Live strategy: build the obligation ``∀ inputs, precond → postcond(impl
        inputs)`` from the task's Lean artifacts and ask AXLE to ``disprove`` it.
        A returned counterexample ⇒ not satisfied; no counterexample within
        budget ⇒ treated as satisfied (a falsifier, never a certifier).
        """
        spec_name = spec or task.spec
        obligation = _build_obligation(task, impl, spec_name)
        result = self.disprove(obligation)
        if result.get("disproved") or result.get("counterexample"):
            return SpecCheckResult(
                satisfied=False,
                counterexample={"axle": result.get("counterexample")},
                detail=f"AXLE disproved obligation for impl '{impl}' vs spec '{spec_name}'",
            )
        return SpecCheckResult(satisfied=True, detail="no counterexample found by AXLE")


def _build_obligation(task: Task, impl: str, spec_name: str) -> str:
    """Assemble the Lean obligation string for the live `disprove` call."""
    impl_src = task.lean.get(f"impl::{impl}", f"-- TODO impl {impl}")
    spec_src = task.lean.get(f"spec::{spec_name}", f"-- TODO spec {spec_name}")
    return "\n".join([
        task.lean.get("preamble", "import Mathlib"),
        impl_src,
        spec_src,
        f"theorem obligation : ∀ x, {spec_name}_pre x → {spec_name}_post x ({impl} x) := by intro x; sorry",
    ])
