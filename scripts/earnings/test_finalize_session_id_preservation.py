"""Regression tests for the resume-path session_id preservation rule.

Rule (added 2026-04-17 after ChatGPT found the A/B resume bug):
  ``finalize_prediction_result`` and ``finalize_learning_result`` must
  NEVER overwrite an existing non-null ``sdk_session_id`` with ``None``.
  Callers' resume paths (e.g., ``scripts/run_ab_baseline.py``) pass
  ``sdk_session_id=None`` when they re-use an existing result.json
  without re-invoking the SDK — in that case the previously-stamped
  real session id must be preserved.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for p in (REPO_ROOT, REPO_ROOT / "scripts", REPO_ROOT / "scripts" / "earnings"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _write_prediction_payload(path: Path, *, with_sid):
    """Write a modern prediction_result.v1 payload; with_sid controls sdk_session_id."""
    payload = {
        "schema_version": "prediction_result.v1",
        "ticker": "AVGO",
        "quarter_label": "Q1_FY2023",
        "direction": "long",
        "confidence_score": 70,
        "expected_move_range_pct": [2.0, 5.0],
        "key_drivers": [{"driver": "test", "direction": "long", "evidence": "x"}],
        "data_gaps": [],
        "evidence_ledger": [],
        "analysis": "test",
        "predicted_at": "2026-04-17T00:00:00Z",
        "model_version": "old-model",
        "prompt_version": "old",
        "confidence_bucket": "HIGH",
        "magnitude_bucket": "moderate",
    }
    if with_sid is not None:
        payload["sdk_session_id"] = with_sid
    path.write_text(json.dumps(payload, indent=2))


def _write_learning_payload(path: Path, *, with_sid):
    payload = {
        "schema_version": "attribution_result.v2",
        "ticker": "AVGO",
        "quarter_label": "Q1_FY2023",
        "filed_8k": "2023-03-02T16:16:43-05:00",
        "accession_8k": "0001730168-23-000004",
        "attributed_at": "2026-04-17T00:00:00Z",
        "model_version": "old-model",
        "pit_mode": "historical",
        "pit_cutoff": "2023-06-01T00:00:00Z",
        "pit_boundary_source": "next_quarter",
        "actual_return": {"daily_stock_pct": 1.0, "hourly_stock_pct": 0.0,
                          "session_stock_pct": 0.5, "daily_macro_pct": 0.5,
                          "daily_sector_pct": 0.5, "daily_industry_pct": 0.5,
                          "market_session": "regular"},
        "primary_driver": {"summary": "x", "category": "y", "evidence_refs": []},
        "contributing_factors": [],
        "feedback": {"why": "x"},
        "global_observations": [],
        "missing_inputs": [],
        "data_sources_used": [],
        "evidence_ledger": [],
        "context_bundle_ref": "context_bundle.json",
        "prediction_result_ref": "prediction/result.json",
    }
    if with_sid is not None:
        payload["sdk_session_id"] = with_sid
    path.write_text(json.dumps(payload, indent=2))


# ── Prediction finalize preservation ──────────────────────────────────────

def test_finalize_prediction_preserves_existing_real_sid_when_caller_passes_none(tmp_path):
    """Resume bug (ChatGPT 2026-04-17): finalize must NOT stamp None over a real sid."""
    from earnings_orchestrator import finalize_prediction_result
    p = tmp_path / "result.json"
    _write_prediction_payload(p, with_sid="real-session-id-abc123")

    finalize_prediction_result(
        result_path=p,
        ticker="AVGO",
        quarter_info={"quarter_label": "Q1_FY2023"},
        model="new-model",
        sdk_session_id=None,  # resume path passes None
    )
    payload = json.loads(p.read_text())
    assert payload["sdk_session_id"] == "real-session-id-abc123", \
        "existing real sdk_session_id MUST be preserved on resume"
    # Other Python-owned metadata is still updated
    assert payload["model_version"] == "new-model"


def test_finalize_prediction_stamps_fresh_sid_when_caller_passes_real_value(tmp_path):
    from earnings_orchestrator import finalize_prediction_result
    p = tmp_path / "result.json"
    _write_prediction_payload(p, with_sid=None)

    finalize_prediction_result(
        result_path=p,
        ticker="AVGO",
        quarter_info={"quarter_label": "Q1_FY2023"},
        model="new-model",
        sdk_session_id="fresh-session-id-xyz789",
    )
    payload = json.loads(p.read_text())
    assert payload["sdk_session_id"] == "fresh-session-id-xyz789"


def test_finalize_prediction_initializes_null_when_missing_and_caller_passes_none(tmp_path):
    """Absent key + caller passes None → stamp null (initialize for consistency)."""
    from earnings_orchestrator import finalize_prediction_result
    p = tmp_path / "result.json"
    # Build payload WITHOUT sdk_session_id key
    payload = {
        "schema_version": "prediction_result.v1",
        "ticker": "AVGO",
        "quarter_label": "Q1_FY2023",
        "direction": "long",
        "confidence_score": 70,
        "expected_move_range_pct": [2.0, 5.0],
        "key_drivers": [],
        "data_gaps": [],
        "evidence_ledger": [],
        "analysis": "test",
        "predicted_at": "2026-04-17T00:00:00Z",
        "model_version": "old",
        "prompt_version": "old",
    }
    p.write_text(json.dumps(payload))

    finalize_prediction_result(
        result_path=p,
        ticker="AVGO",
        quarter_info={"quarter_label": "Q1_FY2023"},
        model="new-model",
        sdk_session_id=None,
    )
    out = json.loads(p.read_text())
    assert "sdk_session_id" in out, "key should be initialized on first finalize"
    assert out["sdk_session_id"] is None


def test_finalize_prediction_preserves_existing_null_sid_when_caller_passes_none(tmp_path):
    """Existing null + caller None → stays null (no-op)."""
    from earnings_orchestrator import finalize_prediction_result
    p = tmp_path / "result.json"
    _write_prediction_payload(p, with_sid=None)

    finalize_prediction_result(
        result_path=p,
        ticker="AVGO",
        quarter_info={"quarter_label": "Q1_FY2023"},
        model="new-model",
        sdk_session_id=None,
    )
    payload = json.loads(p.read_text())
    assert payload["sdk_session_id"] is None


# ── Learning finalize preservation ────────────────────────────────────────

def test_finalize_learning_preserves_existing_real_sid_when_caller_passes_none(tmp_path):
    from earnings_orchestrator import finalize_learning_result
    p = tmp_path / "result.json"
    _write_learning_payload(p, with_sid="real-learning-sid-fff")

    finalize_learning_result(
        result_path=p,
        model="new-model",
        sdk_session_id=None,
        ticker="AVGO",
        quarter_label="Q1_FY2023",
    )
    payload = json.loads(p.read_text())
    assert payload["sdk_session_id"] == "real-learning-sid-fff"


def test_finalize_learning_stamps_fresh_sid(tmp_path):
    from earnings_orchestrator import finalize_learning_result
    p = tmp_path / "result.json"
    _write_learning_payload(p, with_sid=None)

    finalize_learning_result(
        result_path=p,
        model="new-model",
        sdk_session_id="fresh-learning-sid-aaa",
        ticker="AVGO",
        quarter_label="Q1_FY2023",
    )
    payload = json.loads(p.read_text())
    assert payload["sdk_session_id"] == "fresh-learning-sid-aaa"


# ── finalize_attribution_result alias must inherit the preservation rule ──

def test_finalize_attribution_result_alias_also_preserves(tmp_path):
    """The 1-release backward-compat alias must have identical semantics."""
    from earnings_orchestrator import finalize_attribution_result
    p = tmp_path / "result.json"
    _write_learning_payload(p, with_sid="alias-preserved-sid-123")

    finalize_attribution_result(
        result_path=p,
        model="new-model",
        sdk_session_id=None,
        ticker="AVGO",
        quarter_label="Q1_FY2023",
    )
    payload = json.loads(p.read_text())
    assert payload["sdk_session_id"] == "alias-preserved-sid-123"
