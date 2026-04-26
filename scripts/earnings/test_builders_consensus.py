"""Mocked unit tests for scripts.earnings.builders.consensus."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import os, tempfile, pytest

from scripts.earnings.builders import consensus as bc

pytestmark = pytest.mark.builders


def test_no_api_key_raises():
    """Without ALPHAVANTAGE_API_KEY, build_consensus must raise RuntimeError."""
    with patch.dict(os.environ, {}, clear=True), \
         patch.object(bc, "_load_env", return_value=None):
        with pytest.raises(RuntimeError, match="ALPHAVANTAGE_API_KEY"):
            bc.build_consensus(ticker="CRM", quarter_info={"period_of_report": "2024-09-30"})


def test_historical_mode_no_forward_estimates():
    """Historical PIT mode must return empty forward_estimates and add pit_excluded gap.

    _fetch_all_av returns a TUPLE of three AV JSON responses:
      (EARNINGS, EARNINGS_ESTIMATES, INCOME_STATEMENT)
    Verified at scripts/earnings/build_consensus.py:182 — `def _fetch_all_av(...) -> tuple:`
    and line 203 `return tuple(results)`. Returning a dict would crash the consumer.
    """
    fake_av = (
        {"quarterlyEarnings": []},
        {"data": []},
        {"quarterlyReports": []},
    )
    with patch.object(bc, "_load_env", return_value=None), \
         patch.dict(os.environ, {"ALPHAVANTAGE_API_KEY": "fake_key"}), \
         patch.object(bc, "_fetch_all_av", return_value=fake_av), \
         patch.object(bc, "_get_fye_month", return_value=12):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out = f.name
        try:
            packet = bc.build_consensus(
                ticker="CRM",
                quarter_info={"period_of_report": "2024-09-30"},
                as_of_ts="2024-09-15T16:00:00+00:00",
                out_path=out,
            )
            assert packet["forward_estimates"] == []
            assert any("pit_excluded" in str(g) for g in packet.get("gaps", []))
        finally:
            os.unlink(out)


def test_parse_iso_handles_z_naive_invalid():
    assert bc._parse_iso("2024-09-15T16:00:00Z") is not None
    assert bc._parse_iso("2024-09-15T16:00:00") is not None    # naive
    assert bc._parse_iso("garbage") is None


def test_classifier_singleton_within_canonical_module():
    """First call initializes; second returns same instance.
    (Cross-path identity is tested in Stage 7's test_classifier_singleton_across_paths.)"""
    cls1 = bc._get_classifier()
    cls2 = bc._get_classifier()
    assert cls1 is cls2
