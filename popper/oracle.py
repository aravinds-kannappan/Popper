"""Core abstractions shared by every Popper oracle.

A Popper oracle takes a *formalized claim* (a math statement, or a code
specification) and tries to **falsify** it cheaply with an executable signal.
It never *certifies* faithfulness — it only reports whether it managed to break
the claim, and if so, hands back a concrete counterexample that doubles as a
repair signal and an RL reward.

This module is intentionally tiny: it defines the verdict vocabulary and the
`Oracle` interface that both `NumericalOracle` (math) and `CodeSpecOracle`
(Verina-style code specs) implement, so the same audit/report machinery works
for both surfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Verdict(str, Enum):
    """The outcome of auditing one formalized claim.

    FAITHFUL is the *only* "pass". Everything else is a way of being unfaithful
    that the proof checker alone would not have surfaced.
    """

    FAITHFUL = "FAITHFUL"          # survived falsification; plausibly faithful
    FALSIFIED = "FALSIFIED"        # math: a counterexample to the claim was found
    UNSOUND = "UNSOUND"            # code spec too strong: rejects the correct reference
    INCOMPLETE = "INCOMPLETE"      # code spec too weak: accepts a *wrong* implementation
    VACUOUS = "VACUOUS"            # claim is trivially satisfied; it constrains nothing
    INCONCLUSIVE = "INCONCLUSIVE"  # not enough signal (e.g. hypothesis never exercised)

    @property
    def is_faithful(self) -> bool:
        return self is Verdict.FAITHFUL

    @property
    def is_falsified(self) -> bool:
        return self in (
            Verdict.FALSIFIED,
            Verdict.UNSOUND,
            Verdict.INCOMPLETE,
            Verdict.VACUOUS,
        )


# Short glyphs for terminal/markdown reports.
GLYPH = {
    Verdict.FAITHFUL: "✓",
    Verdict.FALSIFIED: "✗",
    Verdict.UNSOUND: "✗",
    Verdict.INCOMPLETE: "✗",
    Verdict.VACUOUS: "✗",
    Verdict.INCONCLUSIVE: "?",
}


@dataclass
class OracleResult:
    """What an oracle reports about a single claim."""

    name: str
    verdict: Verdict
    reason: str
    counterexample: Optional[str] = None  # human-readable; the actionable repair signal
    trials: int = 0                       # how much falsification effort was spent
    details: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.verdict.is_faithful

    def one_line(self) -> str:
        g = GLYPH[self.verdict]
        tail = f"  ⟵ {self.counterexample}" if self.counterexample else ""
        return f"{g} [{self.verdict.value:<12}] {self.name}: {self.reason}{tail}"


class Oracle(ABC):
    """Anything that can try to falsify a formalized claim."""

    name: str = "oracle"

    @abstractmethod
    def audit(self, item: Any) -> OracleResult:
        """Return an :class:`OracleResult` for one claim/spec."""
        raise NotImplementedError
