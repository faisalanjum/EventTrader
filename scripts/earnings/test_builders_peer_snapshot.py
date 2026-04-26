"""Mocked unit tests for scripts.earnings.builders.peer_earnings_snapshot.
Deterministic — no live Neo4j calls. Live integration is covered by the
existing test_builder_validation.py harness (opt-in via §12 final gate).
"""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import json
import os
import tempfile

import pytest

from scripts.earnings.builders import peer_earnings_snapshot as ps

pytestmark = pytest.mark.builders


def test_no_rows_returns_empty_peers_packet():
    """Mock get_manager to return empty rows; assert packet shape + empty peers."""
    mock_manager = MagicMock()
    mock_manager.execute_cypher_query_all.return_value = []
    with patch.object(ps, "get_manager", return_value=mock_manager):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name
        try:
            packet = ps.build_peer_earnings_snapshot(
                ticker="CRM",
                pit_cutoff="2024-09-15T16:00:00+00:00",
                out_path=out_path,
            )
            assert packet["schema_version"] == "peer_earnings_snapshot.v1"
            assert packet.get("peers", []) == []
            assert "pit_cutoff" in packet
            assert os.path.exists(out_path)
            # Confirm written JSON matches returned packet
            with open(out_path) as f:
                disk_packet = json.load(f)
            assert disk_packet == packet
        finally:
            os.unlink(out_path)


def test_parse_dt_for_pit_handles_z_suffix():
    """The Z timestamp suffix must parse to a UTC-aware datetime."""
    from datetime import timezone
    dt = ps._parse_dt_for_pit("2024-09-15T16:00:00Z")
    assert dt.tzinfo is not None
    # Z should map to UTC
    assert dt.utcoffset() == timezone.utc.utcoffset(dt)


def test_parse_dt_for_pit_handles_offset_suffix():
    """Standard ISO8601 offset suffix must parse correctly."""
    dt = ps._parse_dt_for_pit("2023-12-07T16:18:51-05:00")
    assert dt.tzinfo is not None
    # -05:00 = -5 hours from UTC
    assert dt.utcoffset().total_seconds() == -5 * 3600


def test_render_text_accepts_minimal_packet():
    """render_text must produce a non-empty string for a minimal valid packet."""
    packet = {
        "schema_version": "peer_earnings_snapshot.v1",
        "ticker": "CRM",
        "pit_cutoff": "2024-09-15T16:00:00+00:00",
        "peers": [],
    }
    text = ps.render_text(packet)
    assert isinstance(text, str)
    assert len(text) > 0
