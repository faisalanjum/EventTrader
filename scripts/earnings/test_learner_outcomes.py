"""Contract tests for ``earnings_orchestrator.LearnerOutcome``.

Pins:
  * exactly 12 outcome strings (matches the 12 return sites in
    ``run_learner_for_quarter`` — adding a return without tagging here will
    trip this test, surfacing the omission before it ships)
  * the three category sets (SUCCESS, SKIPPED, FAILED) are pairwise
    disjoint and together equal ALL — caller mapping logic depends on this

These tests are the canary: if the function grows a new return path and the
author forgets to categorize it, the regression surface is this file —
loudly, not "silently mislabeled in production".
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "earnings") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "earnings"))

from earnings_orchestrator import LearnerOutcome  # noqa: E402


# ── Taxonomy invariants ──────────────────────────────────────────────────

def test_all_has_exactly_twelve_members():
    """12 return sites → 12 outcome strings. Pins the 1:1 mapping."""
    assert len(LearnerOutcome.ALL) == 12


def test_success_skipped_failed_are_pairwise_disjoint():
    assert LearnerOutcome.SUCCESS.isdisjoint(LearnerOutcome.SKIPPED)
    assert LearnerOutcome.SUCCESS.isdisjoint(LearnerOutcome.FAILED)
    assert LearnerOutcome.SKIPPED.isdisjoint(LearnerOutcome.FAILED)


def test_all_equals_union_of_the_three_category_sets():
    assert (
        LearnerOutcome.ALL
        == LearnerOutcome.SUCCESS | LearnerOutcome.SKIPPED | LearnerOutcome.FAILED
    )


def test_success_contains_succeeded_and_recovered():
    assert LearnerOutcome.SUCCEEDED in LearnerOutcome.SUCCESS
    assert LearnerOutcome.RECOVERED in LearnerOutcome.SUCCESS
    assert len(LearnerOutcome.SUCCESS) == 2


def test_skipped_contains_exactly_the_two_hard_gates():
    assert LearnerOutcome.SKIPPED == frozenset({
        LearnerOutcome.SKIPPED_NO_PREDICTION,
        LearnerOutcome.SKIPPED_NO_DAILY_STOCK,
    })


def test_failed_contains_exactly_the_eight_pipeline_errors():
    assert LearnerOutcome.FAILED == frozenset({
        LearnerOutcome.FAILED_NO_RESULT,
        LearnerOutcome.FAILED_INVALID_JSON,
        LearnerOutcome.FAILED_NO_RESULT_RETRY,
        LearnerOutcome.FAILED_INVALID_JSON_RETRY,
        LearnerOutcome.FAILED_VALIDATION,
        LearnerOutcome.FAILED_RECOVERY_APPEND,
        LearnerOutcome.FAILED_TICKER_APPEND,
        LearnerOutcome.FAILED_GLOBAL_APPEND,
    })


def test_all_constants_are_lowercase_snake_case_strings():
    """No accidental None, no trailing whitespace, no uppercase surprises."""
    import re
    pattern = re.compile(r"^[a-z][a-z_]+[a-z]$")
    for v in LearnerOutcome.ALL:
        assert isinstance(v, str), f"{v!r} is not a str"
        assert pattern.match(v), f"{v!r} is not lowercase_snake_case"


# ── Return-site count parity ─────────────────────────────────────────────

def test_run_learner_for_quarter_has_twelve_return_statements():
    """Grep the function source — must find exactly 12 ``return`` statements.

    Why: the taxonomy size is derived from the function's return-site count.
    If someone adds a new return branch they must also add a new outcome
    constant. This test fails loudly when the two drift apart.
    """
    import ast
    import inspect
    from earnings_orchestrator import run_learner_for_quarter as rlfq
    src = inspect.getsource(rlfq)
    tree = ast.parse(src)
    returns = [n for n in ast.walk(tree) if isinstance(n, ast.Return)]
    assert len(returns) == 12, (
        f"run_learner_for_quarter has {len(returns)} return statements; "
        f"expected 12 (one per LearnerOutcome). If you added a new branch, "
        f"add a matching LearnerOutcome constant and update this count + "
        f"LearnerOutcome.ALL."
    )


def test_every_return_returns_a_two_tuple_with_a_known_outcome():
    """Static check: every ``return`` in run_learner_for_quarter returns a
    tuple literal ``(X, LearnerOutcome.Y)`` where Y is a known constant."""
    import ast
    import inspect
    from earnings_orchestrator import run_learner_for_quarter as rlfq

    src = inspect.getsource(rlfq)
    tree = ast.parse(src)
    known = set(LearnerOutcome.ALL)
    missing = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        val = node.value
        # Must be a 2-tuple
        if not isinstance(val, ast.Tuple) or len(val.elts) != 2:
            missing.append(ast.unparse(val))
            continue
        tag_node = val.elts[1]
        # Tag must be Attribute access on LearnerOutcome, and resolve to a known constant
        if not (
            isinstance(tag_node, ast.Attribute)
            and isinstance(tag_node.value, ast.Name)
            and tag_node.value.id == "LearnerOutcome"
        ):
            missing.append(ast.unparse(val))
            continue
        const_name = tag_node.attr
        const_value = getattr(LearnerOutcome, const_name, None)
        if const_value not in known:
            missing.append(f"{ast.unparse(val)} (unknown constant)")
    assert not missing, (
        "run_learner_for_quarter has untagged/incorrectly-tagged returns:\n  "
        + "\n  ".join(missing)
    )
