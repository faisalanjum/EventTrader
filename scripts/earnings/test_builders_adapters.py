"""Tests for scripts.earnings.builders.adapters."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
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

    The lazy import goes to scripts.earnings.builders.warmup_cache after Stage 12
    canonicalization. We patch that target.
    """
    with patch("scripts.earnings.builders.warmup_cache.build_8k_packet",
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
