"""Tests for result_md_renderer — deterministic JSON→MD sidecar renderer.

Covers: 4 render functions (prediction, learning, baseline_experiment, guidance),
determinism, frontmatter shape, read-only marker, component/experiment_name field.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "earnings") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "earnings"))

import pytest


# ── Fixture payloads matching real schemas ────────────────────────────────

def _prediction_payload():
    """Matches real prediction_result.v1 schema (verified 2026-04-17)."""
    return {
        "schema_version": "prediction_result.v1",
        "ticker": "BURL",
        "quarter_label": "Q4_FY2025",
        "direction": "long",
        "confidence_score": 68,
        "expected_move_range_pct": [2.0, 5.5],
        "confidence_bucket": "moderate",
        "magnitude_bucket": "medium",
        "key_drivers": [
            {"driver": "Clean broad-based Q4 beat", "direction": "long",
             "evidence": "EPS $4.99 vs $4.75 consensus (+5.1%)"},
            {"driver": "FY26 guide implies ~10% EPS growth", "direction": "long",
             "evidence": "FY26 guide $10.95-$11.45"},
        ],
        "data_gaps": [
            {"gap": "Consensus for FY26 not provided in bundle",
             "impact": "reduces precision on guidance-vs-expectations delta"},
        ],
        "evidence_ledger": [
            {"metric": "Q4 Adj EPS", "value": "$4.99 vs $4.75 (+5.1%)",
             "source": "EX-99.1; bzNews_49196246"},
        ],
        "analysis": "Strong quarter with beat + raise pattern.",
        "predicted_at": "2026-04-16T23:13:00Z",
        "model_version": "claude-opus-4-6",
        "prompt_version": "v1-65f04cd84766",
        "sdk_session_id": "f128475b-1234-5678-9abc-def012345678",
    }


def _learning_payload():
    """Matches real attribution_result.v2 schema (verified 2026-04-17)."""
    return {
        "schema_version": "attribution_result.v2",
        "ticker": "AVGO",
        "quarter_label": "Q1_FY2023",
        "filed_8k": "2023-03-02T16:16:43-05:00",
        "accession_8k": "0001730168-23-000004",
        "attributed_at": "2026-04-17T12:00:00Z",
        "model_version": "claude-opus-4-7",
        "pit_mode": "historical",
        "pit_cutoff": "2023-06-01T16:17:30-04:00",
        "pit_boundary_source": "next_quarter",
        "actual_return": {
            "daily_stock_pct": 5.54, "hourly_stock_pct": 0.17,
            "session_stock_pct": 3.72, "daily_macro_pct": 1.58,
            "daily_sector_pct": 2.15, "daily_industry_pct": 1.52,
            "market_session": "post_market",
        },
        "primary_driver": {
            "summary": "Management quantified AI/hyperscaler dollar tailwinds inside a Q2 revenue guide that BEAT consensus",
            "category": "guidance_quantification",
            "evidence_refs": ["E1", "E3", "E7"],
        },
        "contributing_factors": [
            {"summary": "Six sell-side PT raises morning after",
             "category": "analyst_action", "evidence_refs": ["E12"]},
        ],
        "feedback": {
            "prediction_comparison": {
                "predicted_direction": "no_call",
                "predicted_confidence_score": 25,
                "predicted_move_range_pct": [1.0, 3.0],
                "direction_correct": False,
                "magnitude_error_pct": 2.54,
            },
            "what_worked": ["identified EPS beat"],
            "what_failed": ["missed guidance-raise signal"],
            "why": "Predictor applied backward-EPS frame; needed forward-cost-guide frame.",
            "predictor_lessons": ["When management quantifies new dollar tailwinds, weight forward cost-guide"],
            "data_lessons": ["Fetch full analyst commentary, not just point estimates"],
        },
        "global_observations": [
            {"scope": "sector", "target_sector": "Technology",
             "lesson": "Quantified thematic tailwinds dominate backward EPS beats."},
        ],
        "evidence_ledger": [
            {"id": "E1", "claim": "EPS beat", "value": "$10.33 vs $10.11 (+2.2%)",
             "source": "bzNews_31182019", "date": "2023-03-02"},
        ],
        "missing_inputs": ["xbrl_actuals"],
        "data_sources_used": ["neo4j-transcript", "neo4j-news"],
        "context_bundle_ref": "context_bundle.json",
        "prediction_result_ref": "prediction/result.json",
        "sdk_session_id": "98984e15-2570-425a-9429-dec0c3dbf7ff",
    }


def _baseline_payload():
    # Same shape as prediction, but represents the no_lessons experiment
    p = _prediction_payload()
    p["confidence_score"] = 62
    p["sdk_session_id"] = None
    return p


def _guidance_payload():
    return {
        "ticker": "BURL",
        "quarter_label": "Q4_FY2025",
        "source_id": "0001757143-26-000001",
        "period_of_report": "2026-02-01",
        "schema_version": "guidance_result.v1",
        "sdk_session_id": None,
        "summary": "Raised FY guidance; quantified outlook range.",
    }


# ── render_prediction ─────────────────────────────────────────────────────

def test_render_prediction_frontmatter_has_required_keys(tmp_path):
    from result_md_renderer import render_prediction
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_prediction_payload()))
    md_path = tmp_path / "result.md"
    render_prediction(json_path, md_path)

    md = md_path.read_text()
    assert "autogenerated: true" in md
    assert "source: result.json" in md
    assert "generator: scripts/earnings/result_md_renderer.py" in md
    assert "component: prediction" in md
    assert "ticker: BURL" in md
    assert "quarter: Q4_FY2025" in md
    assert "direction: long" in md
    assert "confidence_score: 68" in md
    assert "sdk_session_id: f128475b-1234-5678-9abc-def012345678" in md


def test_render_prediction_has_readonly_marker(tmp_path):
    from result_md_renderer import render_prediction
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_prediction_payload()))
    md_path = tmp_path / "result.md"
    render_prediction(json_path, md_path)
    md = md_path.read_text()
    assert "AUTOGENERATED" in md
    assert "DO NOT EDIT MANUALLY" in md


def test_render_prediction_is_deterministic(tmp_path):
    from result_md_renderer import render_prediction
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_prediction_payload()))
    md_1 = tmp_path / "a.md"
    md_2 = tmp_path / "b.md"
    render_prediction(json_path, md_1)
    render_prediction(json_path, md_2)
    assert md_1.read_bytes() == md_2.read_bytes()


def test_render_prediction_handles_null_session_id(tmp_path):
    from result_md_renderer import render_prediction
    p = _prediction_payload()
    p["sdk_session_id"] = None
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(p))
    md_path = tmp_path / "result.md"
    render_prediction(json_path, md_path)
    md = md_path.read_text()
    assert "sdk_session_id: null" in md


def test_render_prediction_handles_missing_session_id_key(tmp_path):
    from result_md_renderer import render_prediction
    p = _prediction_payload()
    del p["sdk_session_id"]
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(p))
    md_path = tmp_path / "result.md"
    render_prediction(json_path, md_path)
    md = md_path.read_text()
    assert "sdk_session_id: null" in md


# ── render_learning ──────────────────────────────────────────────────────

def test_render_learning_frontmatter(tmp_path):
    from result_md_renderer import render_learning
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    md_path = tmp_path / "result.md"
    render_learning(json_path, md_path)
    md = md_path.read_text()
    assert "component: learning" in md
    assert "ticker: AVGO" in md
    assert "quarter: Q1_FY2023" in md
    assert "schema_version: attribution_result.v2" in md  # schema name unchanged


def test_render_learning_is_deterministic(tmp_path):
    from result_md_renderer import render_learning
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    render_learning(json_path, a)
    render_learning(json_path, b)
    assert a.read_bytes() == b.read_bytes()


# ── render_baseline_experiment ───────────────────────────────────────────

def test_render_baseline_experiment_has_component_prediction_and_experiment_name(tmp_path):
    from result_md_renderer import render_baseline_experiment
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_baseline_payload()))
    md_path = tmp_path / "result.md"
    render_baseline_experiment(json_path, md_path)
    md = md_path.read_text()
    # Experiments: component is PARENT (prediction), experiment_name is the variant tag
    assert "component: prediction" in md
    assert "experiment_name: prediction_no_lessons" in md


def test_render_baseline_experiment_is_deterministic(tmp_path):
    from result_md_renderer import render_baseline_experiment
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_baseline_payload()))
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    render_baseline_experiment(json_path, a)
    render_baseline_experiment(json_path, b)
    assert a.read_bytes() == b.read_bytes()


# ── render_guidance ──────────────────────────────────────────────────────

def test_render_guidance_frontmatter(tmp_path):
    from result_md_renderer import render_guidance
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_guidance_payload()))
    md_path = tmp_path / "result.md"
    render_guidance(json_path, md_path)
    md = md_path.read_text()
    assert "component: guidance" in md
    assert "ticker: BURL" in md


def test_render_guidance_tolerates_minimal_shape(tmp_path):
    from result_md_renderer import render_guidance
    minimal = {"ticker": "BURL", "quarter_label": "Q4_FY2025"}
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(minimal))
    md_path = tmp_path / "result.md"
    render_guidance(json_path, md_path)
    md = md_path.read_text()
    assert "component: guidance" in md
    assert "ticker: BURL" in md


# ── Dispatch function ────────────────────────────────────────────────────

def test_render_dispatch_prediction(tmp_path):
    from result_md_renderer import render
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_prediction_payload()))
    md_path = tmp_path / "result.md"
    render("prediction", json_path, md_path)
    assert md_path.exists()
    assert "component: prediction" in md_path.read_text()


def test_render_dispatch_learning(tmp_path):
    from result_md_renderer import render
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    md_path = tmp_path / "result.md"
    render("learning", json_path, md_path)
    assert "component: learning" in md_path.read_text()


def test_render_dispatch_prediction_no_lessons(tmp_path):
    from result_md_renderer import render
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_baseline_payload()))
    md_path = tmp_path / "result.md"
    render("prediction_no_lessons", json_path, md_path)
    md = md_path.read_text()
    assert "component: prediction" in md
    assert "experiment_name: prediction_no_lessons" in md


def test_render_dispatch_guidance(tmp_path):
    from result_md_renderer import render
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_guidance_payload()))
    md_path = tmp_path / "result.md"
    render("guidance", json_path, md_path)
    assert "component: guidance" in md_path.read_text()


def test_render_dispatch_unknown_component_raises(tmp_path):
    from result_md_renderer import render
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_prediction_payload()))
    md_path = tmp_path / "result.md"
    with pytest.raises(ValueError):
        render("unknown_component", json_path, md_path)


# ── Real-schema rendering completeness (guard against ?-placeholder bugs) ──

def test_prediction_render_contains_actual_driver_text_not_question_marks(tmp_path):
    """Regression guard: 'Key Drivers' must show actual driver text, NOT ? placeholders."""
    from result_md_renderer import render_prediction
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_prediction_payload()))
    md_path = tmp_path / "result.md"
    render_prediction(json_path, md_path)
    md = md_path.read_text()
    assert "Key Drivers" in md
    assert "Clean broad-based Q4 beat" in md, "real driver text should appear in sidecar"
    assert "FY26 guide implies" in md
    # Guard against the exact regression reported:  **?** (weight: )
    assert "**?** (weight: )" not in md
    assert "**?**" not in md.split("Key Drivers")[1].split("## ")[0], "no ? placeholder in Key Drivers"


def test_prediction_render_contains_data_gaps_text(tmp_path):
    from result_md_renderer import render_prediction
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_prediction_payload()))
    md_path = tmp_path / "result.md"
    render_prediction(json_path, md_path)
    md = md_path.read_text()
    assert "Data Gaps" in md
    assert "Consensus for FY26 not provided" in md


def test_prediction_render_includes_evidence_ledger_table(tmp_path):
    from result_md_renderer import render_prediction
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_prediction_payload()))
    md_path = tmp_path / "result.md"
    render_prediction(json_path, md_path)
    md = md_path.read_text()
    assert "Evidence Ledger" in md
    assert "Q4 Adj EPS" in md
    assert "$4.99 vs $4.75" in md


def test_learning_render_primary_driver_dict_unpacked(tmp_path):
    """Regression guard: primary_driver is dict {summary, category, evidence_refs}."""
    from result_md_renderer import render_learning
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    md_path = tmp_path / "result.md"
    render_learning(json_path, md_path)
    md = md_path.read_text()
    assert "Primary Driver" in md
    assert "Management quantified AI/hyperscaler" in md
    assert "guidance_quantification" in md
    # Guard against legacy string-shape rendering where primary was printed as dict repr
    assert "{'summary'" not in md
    assert "evidence_refs" not in md.replace("_Evidence refs:_", "")  # key name should only appear via our render


def test_learning_render_contributing_factors_summary_field(tmp_path):
    from result_md_renderer import render_learning
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    md_path = tmp_path / "result.md"
    render_learning(json_path, md_path)
    md = md_path.read_text()
    assert "Contributing Factors" in md
    assert "Six sell-side PT raises" in md
    # Guard against old assumption key
    assert "(weight: )" not in md


def test_learning_render_all_7_actual_return_keys(tmp_path):
    from result_md_renderer import render_learning
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    md_path = tmp_path / "result.md"
    render_learning(json_path, md_path)
    md = md_path.read_text()
    assert "Actual Returns" in md
    for k in ("daily_stock_pct", "hourly_stock_pct", "session_stock_pct",
              "daily_macro_pct", "daily_sector_pct", "daily_industry_pct",
              "market_session"):
        assert k in md, f"learning sidecar missing actual_return key {k}"


def test_learning_render_feedback_rich_fields(tmp_path):
    from result_md_renderer import render_learning
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    md_path = tmp_path / "result.md"
    render_learning(json_path, md_path)
    md = md_path.read_text()
    # All 6 feedback sub-sections rendered
    assert "Prediction vs actual" in md
    assert "Why (causal explanation)" in md
    assert "What worked" in md
    assert "What failed" in md
    assert "Predictor lessons" in md
    assert "Data lessons" in md
    assert "identified EPS beat" in md
    assert "missed guidance-raise signal" in md


def test_learning_render_evidence_ledger_and_missing_inputs(tmp_path):
    from result_md_renderer import render_learning
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    md_path = tmp_path / "result.md"
    render_learning(json_path, md_path)
    md = md_path.read_text()
    assert "Evidence Ledger" in md
    assert "bzNews_31182019" in md
    assert "Missing Inputs" in md
    assert "xbrl_actuals" in md
    assert "Data Sources Used" in md
    assert "neo4j-transcript" in md


def test_learning_render_pit_block(tmp_path):
    from result_md_renderer import render_learning
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps(_learning_payload()))
    md_path = tmp_path / "result.md"
    render_learning(json_path, md_path)
    md = md_path.read_text()
    assert "PIT" in md
    assert "historical" in md
    assert "next_quarter" in md


def test_learning_render_global_observations_with_routing():
    """Routing fields (target_sector, related_tickers) should appear in rendered observations."""
    from result_md_renderer import render_learning
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        json_path = tmp / "result.json"
        json_path.write_text(json.dumps(_learning_payload()))
        md_path = tmp / "result.md"
        render_learning(json_path, md_path)
        md = md_path.read_text()
        assert "Global Observations (1)" in md
        assert "target_sector=Technology" in md
        assert "Quantified thematic tailwinds" in md
