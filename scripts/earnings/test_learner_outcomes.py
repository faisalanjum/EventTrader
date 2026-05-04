"""Contract tests for ``earnings_orchestrator.LearnerOutcome``.

Pins:
  * exactly 13 outcome strings (LearnerLoopRevamp.md commit 2 added
    ``FAILED_AGGREGATOR`` for D18 success-path audit-aggregator failures)
  * exactly 15 return statements in ``run_learner_for_quarter`` (some
    outcomes — notably ``FAILED_RECOVERY_APPEND`` — appear at multiple
    sites because the recovery path now performs sibling-load + cross-file
    validation + aggregation, each with its own failure return)
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

from earnings_orchestrator import (  # noqa: E402
    LearnerFailed,
    LearnerOutcome,
    LearnerSkipped,
)


# ── Taxonomy invariants ──────────────────────────────────────────────────

def test_all_has_exactly_thirteen_members():
    """13 outcomes total. LearnerLoopRevamp.md commit 2 added
    FAILED_AGGREGATOR for D18 success-path aggregator IO failures."""
    assert len(LearnerOutcome.ALL) == 13


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


def test_failed_contains_exactly_the_nine_pipeline_errors():
    assert LearnerOutcome.FAILED == frozenset({
        LearnerOutcome.FAILED_NO_RESULT,
        LearnerOutcome.FAILED_INVALID_JSON,
        LearnerOutcome.FAILED_NO_RESULT_RETRY,
        LearnerOutcome.FAILED_INVALID_JSON_RETRY,
        LearnerOutcome.FAILED_VALIDATION,
        LearnerOutcome.FAILED_RECOVERY_APPEND,
        LearnerOutcome.FAILED_TICKER_APPEND,
        LearnerOutcome.FAILED_GLOBAL_APPEND,
        LearnerOutcome.FAILED_AGGREGATOR,
    })


def test_all_constants_are_lowercase_snake_case_strings():
    """No accidental None, no trailing whitespace, no uppercase surprises."""
    import re
    pattern = re.compile(r"^[a-z][a-z_]+[a-z]$")
    for v in LearnerOutcome.ALL:
        assert isinstance(v, str), f"{v!r} is not a str"
        assert pattern.match(v), f"{v!r} is not lowercase_snake_case"


# ── Return-site count parity ─────────────────────────────────────────────

def test_run_learner_for_quarter_has_sixteen_return_statements():
    """Grep the function source — must find exactly 16 ``return`` statements.

    Note: the count is NOT 1:1 with LearnerOutcome.ALL anymore.
    LearnerLoopRevamp.md commit 2 (D18 + D19) added three new branches in
    the recovery path (sibling-file existence, cross-file validation,
    aggregator wrap), all of which surface ``FAILED_RECOVERY_APPEND``
    when they fail. Plus one new branch in the success path for D18
    aggregator failure → ``FAILED_AGGREGATOR``. Commit 2.1 added one more
    recovery-path branch (sibling-totality check) also tagged
    ``FAILED_RECOVERY_APPEND`` → 16 returns total.

    The lower-level test ``test_every_return_returns_a_two_tuple_with_a_known_outcome``
    is now the authoritative invariant — every return must tag a known
    outcome, even if multiple returns share the same outcome.
    """
    import ast
    import inspect
    from earnings_orchestrator import run_learner_for_quarter as rlfq
    src = inspect.getsource(rlfq)
    tree = ast.parse(src)
    returns = [n for n in ast.walk(tree) if isinstance(n, ast.Return)]
    assert len(returns) == 16, (
        f"run_learner_for_quarter has {len(returns)} return statements; "
        f"expected 16. If you added a new branch, ensure it tags a known "
        f"LearnerOutcome (the AST tagging test will catch a bare or "
        f"unknown-constant return) and update this count."
    )


# ── Typed exception contract (for auxiliary-script distinguishing) ──────

def test_learner_skipped_carries_outcome_and_has_structured_message():
    e = LearnerSkipped(LearnerOutcome.SKIPPED_NO_PREDICTION, context="Q3_FY2025")
    assert isinstance(e, RuntimeError)
    assert e.outcome == LearnerOutcome.SKIPPED_NO_PREDICTION
    assert "skipped_no_prediction" in str(e)
    assert "Q3_FY2025" in str(e)


def test_learner_failed_carries_outcome_and_has_structured_message():
    e = LearnerFailed(LearnerOutcome.FAILED_VALIDATION, context="Q1_FY2024")
    assert isinstance(e, RuntimeError)
    assert e.outcome == LearnerOutcome.FAILED_VALIDATION
    assert "failed_validation" in str(e)
    assert "Q1_FY2024" in str(e)


def test_skipped_and_failed_are_distinct_types():
    """Callers must be able to write `except LearnerSkipped` and
    `except LearnerFailed` without one catching the other."""
    assert not issubclass(LearnerSkipped, LearnerFailed)
    assert not issubclass(LearnerFailed, LearnerSkipped)


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
