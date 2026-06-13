"""Backends for the code-specification oracle.

* :class:`Task` — a Verina-style task carrying executable Python models (for the
  offline demo) alongside optional Lean artifacts.
* :class:`MockAxleClient` — offline evaluator of the Python model.
* :class:`AxleClient` — a thin *synchronous* wrapper over the official async
  ``axle.AxleClient`` (``pip install axiom-axle``). The official package is
  imported lazily inside ``__init__`` so that ``import popper`` never requires it;
  only the live path does.

The live Verina audit (see :mod:`popper.verina`) drives the official async client
directly for concurrency; this sync wrapper is the convenient general-purpose
handle (``check`` / ``disprove``).
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


class AxleClient:
    """Synchronous handle on the live Axiom Lean Engine.

    Requires ``pip install axiom-axle`` and an API key (``AXLE_API_KEY`` env var,
    free key at https://axle.axiommath.ai/app/console).
    """

    live = True

    def __init__(self, api_key: Optional[str] = None, url: Optional[str] = None,
                 environment: str = "lean-4.28.0", max_concurrency: int = 8,
                 timeout_seconds: float = 200.0):
        import asyncio
        try:
            import axle as _axle
        except ImportError as e:  # pragma: no cover - exercised only on the live path
            raise RuntimeError(
                "The live path needs the official client: pip install axiom-axle"
            ) from e
        self._axle = _axle
        self.environment = environment
        self.timeout_seconds = timeout_seconds
        self._loop = asyncio.new_event_loop()
        self._client = self._loop.run_until_complete(
            _axle.AxleClient(api_key=api_key, url=url, max_concurrency=max_concurrency).__aenter__()
        )

    # -- lifecycle ---------------------------------------------------------- #
    def close(self) -> None:
        try:
            self._loop.run_until_complete(self._client.__aexit__(None, None, None))
        finally:
            self._loop.close()

    def __enter__(self) -> "AxleClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- verbs -------------------------------------------------------------- #
    def check(self, content: str, ignore_imports: Optional[bool] = None,
              timeout_seconds: Optional[float] = None):
        return self._loop.run_until_complete(self._client.check(
            content=content, environment=self.environment,
            ignore_imports=ignore_imports,
            timeout_seconds=timeout_seconds or self.timeout_seconds,
        ))

    def disprove(self, content: str, ignore_imports: Optional[bool] = None,
                 timeout_seconds: Optional[float] = None):
        return self._loop.run_until_complete(self._client.disprove(
            content=content, environment=self.environment,
            ignore_imports=ignore_imports,
            timeout_seconds=timeout_seconds or self.timeout_seconds,
        ))
