"""Representative Verina-style tasks for the offline demo.

These are hand-authored in the Verina format (NL description + signature +
reference implementation + formal spec + tests) so the audit pipeline runs with
no Lean toolchain and no network. They are deliberately chosen to exhibit each
verdict the oracle can return:

    sort_by_length        → VACUOUS    (a length-only postcondition; a constant
                                         function satisfies it)
    max_lower_bound_only  → INCOMPLETE (out ≥ a ∧ out ≥ b, but never pinned to a or b)
    abs_value             → FAITHFUL
    abs_strictly_positive → UNSOUND    (out > 0 rejects the correct abs(0) = 0)

The real benchmark (189 tasks, CC-BY-SA-4.0) lives at https://verina.io ; point
a loader at the HuggingFace/GitHub release and feed an `AxleClient` to audit it
for real. We do NOT vendor the CC-BY-SA data into this Apache-2.0 repo.
"""

from __future__ import annotations

from .axle import Task
from .mutation import fuzz_int, fuzz_list_int


def verina_like_tasks() -> list[Task]:
    # --- sorting: the canonical "too weak / vacuous" spec ------------------ #
    sort_task = Task(
        name="sort_by_length",
        description="Sort a list of integers in non-decreasing order.",
        signature="sort : List Int → List Int",
        reference="library_sort",
        spec="post_length_only",
        impls_py={
            "library_sort": lambda lst: sorted(lst),
            "identity":     lambda lst: list(lst),
            "reverse":      lambda lst: list(reversed(lst)),
            "all_zeros":    lambda lst: [0] * len(lst),   # the throwaway impl
        },
        spec_py={
            # BUG: only constrains length — says nothing about order or contents.
            "post_length_only": lambda args, out: len(out) == len(args[0]),
        },
        wrong_impls=["identity", "reverse"],
        arbitrary="all_zeros",
        test_inputs=[([3, 1, 2],), ([],), ([2, 2, 2],), ([5, -1, 0, 3],)],
        gen_input=lambda rng: (fuzz_list_int(rng),),
        lean={"spec::post_length_only": "def post (xs out : List Int) : Prop := out.length = xs.length"},
    )

    # --- max of two ints: a too-weak (incomplete) spec --------------------- #
    max_task = Task(
        name="max_lower_bound_only",
        description="Return the maximum of two integers.",
        signature="max2 : Int → Int → Int",
        reference="builtin_max",
        spec="post_lower_bound",
        impls_py={
            "builtin_max":  lambda a, b: max(a, b),
            "max_plus_one": lambda a, b: max(a, b) + 1,   # ≥ both, but wrong
            "neg_inf":      lambda a, b: -(10 ** 9),       # throwaway (will fail)
        },
        spec_py={
            # BUG: a lower bound on both inputs, but never requires out ∈ {a, b}.
            "post_lower_bound": lambda args, out: out >= args[0] and out >= args[1],
        },
        wrong_impls=["max_plus_one"],
        arbitrary="neg_inf",
        test_inputs=[(3, 5), (5, 3), (-2, -7), (0, 0), (10, -10)],
        gen_input=lambda rng: (fuzz_int(rng), fuzz_int(rng)),
        lean={"spec::post_lower_bound": "def post (a b out : Int) : Prop := out ≥ a ∧ out ≥ b"},
    )

    # --- absolute value: a FAITHFUL spec ----------------------------------- #
    _abs_impls = {
        "builtin_abs": lambda x: abs(x),
        "identity":    lambda x: x,
        "negate":      lambda x: -x,
        "const_five":  lambda x: 5,
    }
    abs_faithful = Task(
        name="abs_value",
        description="Return the absolute value of an integer.",
        signature="absInt : Int → Int",
        reference="builtin_abs",
        spec="post_abs",
        impls_py=dict(_abs_impls),
        spec_py={
            "post_abs": lambda args, out: out >= 0 and (out == args[0] or out == -args[0]),
        },
        wrong_impls=["identity", "negate"],
        arbitrary="const_five",
        test_inputs=[(0,), (5,), (-5,), (7,), (-3,)],
        gen_input=lambda rng: (fuzz_int(rng),),
        lean={"spec::post_abs": "def post (x out : Int) : Prop := out ≥ 0 ∧ (out = x ∨ out = -x)"},
    )

    # --- absolute value, but an UNSOUND (too strong) spec ------------------ #
    abs_unsound = Task(
        name="abs_strictly_positive",
        description="Absolute value, but the spec wrongly demands a strictly positive result.",
        signature="absInt : Int → Int",
        reference="builtin_abs",
        spec="post_abs_strict",
        impls_py=dict(_abs_impls),
        spec_py={
            # BUG: out > 0 rejects the correct answer abs(0) = 0.
            "post_abs_strict": lambda args, out: out > 0 and (out == args[0] or out == -args[0]),
        },
        wrong_impls=["identity", "negate"],
        arbitrary="const_five",
        test_inputs=[(0,), (5,), (-5,), (7,), (-3,)],
        gen_input=lambda rng: (fuzz_int(rng),),
        lean={"spec::post_abs_strict": "def post (x out : Int) : Prop := out > 0 ∧ (out = x ∨ out = -x)"},
    )

    return [sort_task, max_task, abs_faithful, abs_unsound]
