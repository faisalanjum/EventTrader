"""Tests for scripts.earnings.builders.adapters."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import os
import tempfile
import pytest

from scripts.earnings.builders import adapters as A

pytestmark = pytest.mark.builders


def test_derive_mode_logic():
    """live mode = no pit_cutoff; historical mode = pit_cutoff present."""
    assert A._derive_mode(None) == "live"
    assert A._derive_mode("2024-09-15T16:00:00+00:00") == "historical"


def test_enrich_packet_adds_required_fields():
    """_enrich_packet must add pit_cutoff, source_mode, effective_cutoff_ts."""
    packet = {"schema_version": "8k_packet.v1", "ticker": "CRM"}
    enriched = A._enrich_packet(packet, pit_cutoff="2024-09-15T16:00:00+00:00",
                                 effective_cutoff_ts=None)
    assert enriched["pit_cutoff"] == "2024-09-15T16:00:00+00:00"
    assert enriched["source_mode"] == "historical"
    assert "effective_cutoff_ts" in enriched


def test_enrich_packet_live_mode():
    packet = {"schema_version": "8k_packet.v1", "ticker": "CRM"}
    enriched = A._enrich_packet(packet, pit_cutoff=None,
                                 effective_cutoff_ts="2024-09-15T16:00:00+00:00")
    assert enriched["source_mode"] == "live"
    assert enriched["pit_cutoff"] is None
    assert enriched["effective_cutoff_ts"] == "2024-09-15T16:00:00+00:00"


def test_8k_packet_catches_systemexit():
    """If legacy raises SystemExit (8-K not found), adapter must raise ValueError.

    Stage 4 canonicalized adapters.py to import from .eight_k_packet directly
    (not via the warmup_cache facade hop). The mock target is the canonical
    domain module — that's where the lazy import resolves.
    """
    with patch("scripts.earnings.builders.eight_k_packet.build_8k_packet",
               side_effect=SystemExit(1)):
        with pytest.raises(ValueError, match="8-K not found"):
            A.build_8k_packet(
                ticker="CRM",
                quarter_info={"accession_8k": "0001234567-89-000001"},
            )


def test_helpers_present():
    """All 6 private helpers must be on the adapters module."""
    for name in ("_SuppressStdout", "_enrich_packet", "_write_enriched",
                 "_ensure_dir", "_derive_mode", "_now_iso"):
        assert hasattr(A, name), f"adapters module missing helper {name}"


def test_seven_adapter_functions_present():
    """All 7 adapter functions must be on the adapters module."""
    for name in ("build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
                 "build_peer_earnings_snapshot", "build_macro_snapshot",
                 "build_consensus", "build_prior_financials"):
        assert hasattr(A, name), f"adapters module missing {name}"
        assert callable(getattr(A, name)), f"{name} not callable"


def test_macro_adapter_defaults_polygon_for_historical_and_yahoo_for_live():
    """U33 guard: historical macro builds must not enter Yahoo live semantics by default."""
    calls = []

    def fake_legacy(ticker, pit_cutoff, market_session, out_path=None, source=None, **kwargs):
        calls.append({
            "ticker": ticker,
            "pit_cutoff": pit_cutoff,
            "market_session": market_session,
            "source": source,
        })
        return {
            "schema_version": "macro_snapshot.v2",
            "ticker": ticker,
            "market_now": {},
            "catalysts": {},
            "gaps": [],
        }

    qi = {"market_session": "pre_market"}
    with patch("scripts.earnings.builders.macro_snapshot.build_macro_snapshot", side_effect=fake_legacy):
        fd, out = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            A.build_macro_snapshot("CRM", qi, pit_cutoff="2026-05-01T06:52:00-04:00", out_path=out)
            A.build_macro_snapshot("CRM", qi, pit_cutoff=None, out_path=out)
        finally:
            if os.path.exists(out):
                os.unlink(out)

    assert calls[0]["source"] == "polygon"
    assert calls[0]["market_session"] == "pre_market"
    assert calls[1]["source"] == "yahoo"
    assert calls[1]["market_session"] is None


# ─── U34 adapter live_mode propagation ────────────────────────────────


def _capture_macro_legacy_call():
    """Returns (calls list, fake legacy callable). Patch the legacy import path."""
    calls = []

    def fake_legacy(ticker, pit_cutoff, market_session, out_path=None, source=None,
                    live_mode=None, **kwargs):
        calls.append({
            "ticker": ticker,
            "pit_cutoff": pit_cutoff,
            "market_session": market_session,
            "source": source,
            "live_mode": live_mode,
        })
        return {
            "schema_version": "macro_snapshot.v2",
            "ticker": ticker,
            "market_now": {},
            "catalysts": {},
            "gaps": [],
        }
    return calls, fake_legacy


def test_macro_adapter_passes_live_mode_true_when_pit_cutoff_none():
    """U34 — adapter live mode must propagate live_mode=True to legacy builder."""
    calls, fake_legacy = _capture_macro_legacy_call()
    qi = {"market_session": "post_market"}
    with patch("scripts.earnings.builders.macro_snapshot.build_macro_snapshot",
               side_effect=fake_legacy):
        fd, out = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            A.build_macro_snapshot("CRM", qi, pit_cutoff=None, out_path=out)
        finally:
            if os.path.exists(out):
                os.unlink(out)

    assert calls[0]["live_mode"] is True
    assert calls[0]["source"] == "yahoo"


def test_macro_adapter_passes_live_mode_false_when_pit_cutoff_set():
    """U34 — adapter historical mode must propagate live_mode=False."""
    calls, fake_legacy = _capture_macro_legacy_call()
    qi = {"market_session": "post_market"}
    with patch("scripts.earnings.builders.macro_snapshot.build_macro_snapshot",
               side_effect=fake_legacy):
        fd, out = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            A.build_macro_snapshot("CRM", qi, pit_cutoff="2024-09-15T16:00:00-04:00",
                                    out_path=out)
        finally:
            if os.path.exists(out):
                os.unlink(out)

    assert calls[0]["live_mode"] is False
    assert calls[0]["source"] == "polygon"
