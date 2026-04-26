"""Mocked unit tests for scripts.earnings.builders.prior_financials."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import os, tempfile
import pytest

from scripts.earnings.builders import prior_financials as bpf

pytestmark = pytest.mark.builders


def test_classify_period_quarter():
    # ~92 days (60-120 range) → "quarterly"
    res = bpf.classify_period("2024-07-01", "2024-09-30")
    assert res == "quarterly"


def test_classify_period_annual():
    # ~365 days (340-400 range) → "annual"
    res = bpf.classify_period("2024-01-01", "2024-12-31")
    assert res == "annual"


def test_classify_period_instant():
    # period_end None or 'null' → instant
    assert bpf.classify_period("2024-09-30", None) == "instant"
    assert bpf.classify_period("2024-09-30", "null") == "instant"


def test_classify_period_semi_annual():
    # ~180 days (150-210 range) → "semi_annual"
    res = bpf.classify_period("2024-01-01", "2024-06-30")
    assert res == "semi_annual"


def test_is_target_period_true_when_match():
    assert bpf.is_target_period("2024-09-30", "2024-09-30") is True


def test_is_target_period_false_when_mismatch():
    assert bpf.is_target_period("2024-06-30", "2024-09-30") is False


def test_parse_value_numeric():
    assert bpf._parse_value(1234.5) == 1234.5
    assert bpf._parse_value("1234.5") == 1234.5


def test_parse_value_none():
    assert bpf._parse_value(None) is None
    assert bpf._parse_value("") is None
    assert bpf._parse_value("garbage") is None


def test_get_manager_is_locally_imported_inside_build_function():
    """Sanity guard for patch-target choice in mocked tests below.

    `get_manager` is imported LAZILY inside build_prior_financials() at
    line 1286 (and main() at line 1721 of the OLD file; equivalent locations
    in the canonical copy). There is NO module-level `bpf.get_manager`
    attribute, so `patch.object(bpf, "get_manager")` would fail with
    AttributeError. Use `patch("neograph.Neo4jConnection.get_manager", ...)`
    for the source instead.
    """
    import inspect
    # Module-level: no get_manager attribute on bpf
    assert not hasattr(bpf, "get_manager"), (
        "get_manager is now a module-level attribute — update mock targets "
        "in this file accordingly."
    )
    # Function-internal: import statement must be present in build_prior_financials's source
    src = inspect.getsource(bpf.build_prior_financials)
    assert "from neograph.Neo4jConnection import get_manager" in src
