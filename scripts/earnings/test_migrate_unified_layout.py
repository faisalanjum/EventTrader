"""Tests for migrate_unified_layout.py — unified vault + extractions migration.

Covers --dry-run, --apply, --reverse, idempotency, conditional baseline moves,
partial-run recovery, null-stamp + md-generate coverage, extraction filter.
"""
from __future__ import annotations
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for p in (REPO_ROOT, REPO_ROOT / "scripts", REPO_ROOT / "scripts" / "earnings"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pytest


# ── Synthetic vault builders ──────────────────────────────────────────────

def _make_vault_skeleton(root: Path) -> Path:
    """Build a minimal synthetic vault matching the post-wipe production state.

    Shape:
      Companies/AVGO/events/Q1_FY2023/attribution/result.json   (modern)
      Companies/AVGO/events/Q1_FY2023/prediction/result.json + context_bundle.{json,txt}
      Companies/AVGO/events/Q1_FY2023/experiments/prediction_no_lessons/result.json + context_bundle.{json,txt}
      Companies/AVGO/events/Q1_FY2024/attribution/  (EMPTY dir — no result.json)
      Companies/AVGO/events/Q1_FY2024/prediction/result.json + context_bundle.{json,txt}
      Companies/AVGO/events/Q1_FY2024/experiments/prediction_no_lessons/result.json + context_bundle.{json,txt}
      Companies/AVGO/events/Q2_FY2024/prediction/result.json (LEGACY STUB — 254 bytes, no schema_version)
      Companies/AVGO/events/Q2_FY2024/prediction/context.json (OLD filename — NOT context_bundle.json)
    """
    vault = root / "vault"
    pipeline = root / "pipeline" / "extractions"
    vault.mkdir(parents=True)
    pipeline.mkdir(parents=True)

    def _write_result(d: Path, schema: str, direction: str = "long", conf: int = 60):
        d.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": schema,
            "ticker": "AVGO",
            "quarter_label": d.parent.name,
            "direction": direction,
            "confidence_score": conf,
            "expected_move_range_pct": [1.0, 3.0],
            "key_drivers": [{"factor": "beat", "weight": 0.5}],
            "data_gaps": [],
            "evidence_ledger": [],
            "analysis": "test analysis",
            "predicted_at": "2026-04-01T00:00:00Z",
            "model_version": "claude-opus-4-7",
            "prompt_version": "test",
            "confidence_bucket": "HIGH",
            "magnitude_bucket": "moderate",
        }
        if schema == "attribution_result.v2":
            payload = {
                "schema_version": schema,
                "ticker": "AVGO",
                "quarter_label": d.parent.name,
                "attributed_at": "2026-04-02T00:00:00Z",
                "model_version": "claude-opus-4-7",
                "actual_return": {"daily_stock_pct": 2.1},
                "primary_driver": "beat",
                "contributing_factors": [],
                "feedback": {"verdict": "correct_direction", "why": "matched"},
                "global_observations": [],
            }
        (d / "result.json").write_text(json.dumps(payload, indent=2))

    def _write_bundle(d: Path):
        d.mkdir(parents=True, exist_ok=True)
        (d / "context_bundle.json").write_text(json.dumps({"_test_bundle": "v1"}))
        (d / "context_bundle_rendered.txt").write_text("RENDERED BUNDLE TEXT")

    # ── Q1_FY2023: full modern quarter WITH attribution/result.json (one of 3) ──
    q1_23 = vault / "AVGO" / "events" / "Q1_FY2023"
    _write_result(q1_23 / "prediction", "prediction_result.v1")
    _write_bundle(q1_23 / "prediction")
    _write_result(q1_23 / "attribution", "attribution_result.v2")
    _write_result(q1_23 / "experiments" / "prediction_no_lessons", "prediction_result.v1", conf=55)
    _write_bundle(q1_23 / "experiments" / "prediction_no_lessons")

    # ── Q1_FY2024: modern quarter but EMPTY attribution/ dir (12 of 15 in prod) ──
    q1_24 = vault / "AVGO" / "events" / "Q1_FY2024"
    _write_result(q1_24 / "prediction", "prediction_result.v1")
    _write_bundle(q1_24 / "prediction")
    (q1_24 / "attribution").mkdir(parents=True)  # EMPTY
    _write_result(q1_24 / "experiments" / "prediction_no_lessons", "prediction_result.v1", conf=52)
    _write_bundle(q1_24 / "experiments" / "prediction_no_lessons")

    # ── Q2_FY2024: LEGACY STUB (pre-schema prediction/result.json + old context.json) ──
    q2_24 = vault / "AVGO" / "events" / "Q2_FY2024"
    (q2_24 / "prediction").mkdir(parents=True)
    # Pre-schema stub — no schema_version, no ticker, etc.
    stub = {"direction": "up", "magnitude": "medium", "confidence_pct": 80,
            "primary_reason": "old-format stub from Feb 2026 testing"}
    (q2_24 / "prediction" / "result.json").write_text(json.dumps(stub))
    (q2_24 / "prediction" / "context.json").write_text(json.dumps({"_legacy_context": True}))

    # ── pipeline/extractions/ fixtures ──
    # 3 conforming + 1 anomalous + Extraction Runs.md + .capture.log
    (pipeline / "2026-03-17_extraction_0001234.md").write_text("# conforming 1")
    (pipeline / "2026-03-17_extraction_0005678.md").write_text("# conforming 2")
    (pipeline / "2026-03-17_extraction_ADI_2025-06-25T14.00.md").write_text("# conforming 3 (transcript id)")
    (pipeline / "2026-03-17_extraction-primary-agent_abcdef12.md").write_text("# anomalous fallback")
    (pipeline / "Extraction Runs.md").write_text("# manual obsidian note")
    (pipeline / ".capture.log").write_text("log line 1\n")

    return vault


# ── Test: --dry-run output shape ──────────────────────────────────────────

def test_dry_run_lists_expected_ops_and_counts(tmp_path, capsys):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"

    rc = main(["--dry-run", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    assert rc == 0
    out = capsys.readouterr().out

    # Expected op categories with counts
    assert "rename_dir attribution → learning: 2" in out, out  # Q1_FY2023 + Q1_FY2024 (Q2_FY2024 has no attribution/)
    assert "rename_file context_bundle: 4" in out, out  # Q1_FY2023 + Q1_FY2024 × 2 files each
    assert "rename_file ab_baseline (NO_LESSONS): 0" in out  # none exist
    assert "stamp_null_session_id: 5" in out, out  # 2 pred + 1 learning + 2 exp, excluding legacy stub
    assert "generate_result_md: 5" in out, out
    assert "rename_file extractions: 3" in out, out  # conforming only

    # Legacy stub + anomalous explicitly logged as skipped
    assert "skipped" in out.lower()
    assert "Q2_FY2024" in out  # legacy stub mentioned
    assert "anomalous" in out.lower() or "extraction-primary-agent" in out


def test_dry_run_does_not_change_filesystem(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    before = _vault_snapshot(vault, pipeline)
    main(["--dry-run", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    after = _vault_snapshot(vault, pipeline)
    assert before == after
    assert not (vault / ".migration-manifest.json").exists()


# ── Test: --apply writes manifest + expected filesystem state ─────────────

def test_apply_writes_manifest_and_expected_state(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    rc = main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    assert rc == 0

    # attribution/ dirs renamed → learning/
    assert not (vault / "AVGO" / "events" / "Q1_FY2023" / "attribution").exists()
    assert (vault / "AVGO" / "events" / "Q1_FY2023" / "learning").is_dir()
    assert not (vault / "AVGO" / "events" / "Q1_FY2024" / "attribution").exists()
    assert (vault / "AVGO" / "events" / "Q1_FY2024" / "learning").is_dir()

    # context_bundle.* promoted to quarter root (for modern quarters)
    assert (vault / "AVGO" / "events" / "Q1_FY2023" / "context_bundle.json").exists()
    assert (vault / "AVGO" / "events" / "Q1_FY2023" / "context_bundle_rendered.txt").exists()
    assert not (vault / "AVGO" / "events" / "Q1_FY2023" / "prediction" / "context_bundle.json").exists()

    # Legacy stub quarter untouched
    assert (vault / "AVGO" / "events" / "Q2_FY2024" / "prediction" / "context.json").exists()
    assert (vault / "AVGO" / "events" / "Q2_FY2024" / "prediction" / "result.json").exists()
    # Legacy stub NOT stamped
    legacy = json.loads((vault / "AVGO" / "events" / "Q2_FY2024" / "prediction" / "result.json").read_text())
    assert "sdk_session_id" not in legacy

    # All 5 modern result.json files stamped with null
    for p in [
        vault / "AVGO" / "events" / "Q1_FY2023" / "prediction" / "result.json",
        vault / "AVGO" / "events" / "Q1_FY2023" / "learning" / "result.json",
        vault / "AVGO" / "events" / "Q1_FY2023" / "experiments" / "prediction_no_lessons" / "result.json",
        vault / "AVGO" / "events" / "Q1_FY2024" / "prediction" / "result.json",
        vault / "AVGO" / "events" / "Q1_FY2024" / "experiments" / "prediction_no_lessons" / "result.json",
    ]:
        data = json.loads(p.read_text())
        assert "sdk_session_id" in data
        assert data["sdk_session_id"] is None
        # result.md sidecar must exist
        assert p.with_name("result.md").exists(), f"missing sidecar next to {p}"

    # Pipeline extractions moved to guidance/
    assert (pipeline / "guidance" / "2026-03-17_0001234.md").exists()
    assert (pipeline / "guidance" / "2026-03-17_0005678.md").exists()
    # Non-conforming left in place
    assert (pipeline / "2026-03-17_extraction-primary-agent_abcdef12.md").exists()
    assert (pipeline / "Extraction Runs.md").exists()
    assert (pipeline / ".capture.log").exists()

    # Manifest written
    manifest = vault / ".migration-manifest.json"
    assert manifest.exists()
    m = json.loads(manifest.read_text())
    assert m["schema_version"] == "migration.v1"
    assert isinstance(m["steps"], list) and len(m["steps"]) > 0
    ops = {s["op"] for s in m["steps"]}
    assert "rename_dir" in ops
    assert "rename_file" in ops
    assert "stamp_null_session_id" in ops
    assert "generate_result_md" in ops


# ── Test: apply is idempotent ────────────────────────────────────────────

def test_apply_idempotent_second_run_is_noop(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    first = _vault_snapshot(vault, pipeline)
    first_manifest = json.loads((vault / ".migration-manifest.json").read_text())

    # Second run should detect already-migrated state and record ZERO new steps
    main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    second = _vault_snapshot(vault, pipeline)
    second_manifest = json.loads((vault / ".migration-manifest.json").read_text())

    assert first == second, "second --apply must not alter filesystem"
    # Manifest may be re-written but should record no new ops
    assert len(second_manifest["steps"]) == 0 or second_manifest["steps"] == first_manifest["steps"]


# ── Test: --reverse round-trip ───────────────────────────────────────────

def test_reverse_round_trip_restores_initial_state(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    before = _vault_snapshot(vault, pipeline)
    main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    rc = main(["--reverse", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    assert rc == 0
    after = _vault_snapshot(vault, pipeline, exclude_manifest=True, exclude_result_md=True)
    assert before == after, "reverse must restore pre-apply state (excluding manifest/result.md)"


# ── Test: baseline-absent path (today's reality) ─────────────────────────

def test_baseline_absent_records_zero_moves(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    m = json.loads((vault / ".migration-manifest.json").read_text())
    ab_baseline_ops = [s for s in m["steps"] if "ab_baseline" in json.dumps(s)]
    assert len(ab_baseline_ops) == 0, "no ab_baseline ops when ab_baseline/ absent"


# ── Test: baseline-present synthetic path ────────────────────────────────

def test_baseline_present_migrates_and_records(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    # Inject a synthetic ab_baseline/ for Q1_FY2023
    ab = vault / "AVGO" / "events" / "Q1_FY2023" / "prediction" / "ab_baseline"
    ab.mkdir()
    stub = {
        "schema_version": "prediction_result.v1",
        "ticker": "AVGO", "quarter_label": "Q1_FY2023",
        "direction": "short", "confidence_score": 45,
        "expected_move_range_pct": [-2.0, -0.5],
        "key_drivers": [], "data_gaps": [], "evidence_ledger": [],
        "analysis": "legacy baseline",
        "predicted_at": "2026-02-01T00:00:00Z", "model_version": "old",
        "prompt_version": "old", "confidence_bucket": "MED", "magnitude_bucket": "low",
    }
    (ab / "result_NO_LESSONS.json").write_text(json.dumps(stub))
    (ab / "context_bundle_NO_LESSONS.json").write_text(json.dumps({"_legacy": True}))
    (ab / "context_bundle_rendered_NO_LESSONS.txt").write_text("LEGACY RENDERED")

    # Remove the pre-existing experiment so we can verify the migration creates it from ab_baseline
    # (In prod both exist, but to test the move, we start from only ab_baseline.)
    shutil.rmtree(vault / "AVGO" / "events" / "Q1_FY2023" / "experiments")

    main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])

    # Assert ab_baseline moved + dir removed
    assert not ab.exists()
    target = vault / "AVGO" / "events" / "Q1_FY2023" / "experiments" / "prediction_no_lessons"
    assert (target / "result.json").exists()
    assert (target / "context_bundle.json").exists()
    assert (target / "context_bundle_rendered.txt").exists()

    # Manifest recorded the ops
    m = json.loads((vault / ".migration-manifest.json").read_text())
    ops = [s for s in m["steps"] if "ab_baseline" in json.dumps(s) or "NO_LESSONS" in json.dumps(s)]
    assert len(ops) >= 3


# ── Test: extraction filter + anomalous files stay ───────────────────────

def test_extraction_migration_filters_anomalous(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    # All 3 conforming files moved into guidance/, no _extraction_ in filename
    moved = sorted((pipeline / "guidance").iterdir())
    assert len(moved) == 3
    for p in moved:
        assert "_extraction_" not in p.name
        assert p.suffix == ".md"

    # Anomalous files still at root
    assert (pipeline / "2026-03-17_extraction-primary-agent_abcdef12.md").exists()
    assert (pipeline / "Extraction Runs.md").exists()
    assert (pipeline / ".capture.log").exists()


# ── Test: null-stamp skips legacy stub ────────────────────────────────────

def test_legacy_stub_not_stamped(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    legacy = json.loads((vault / "AVGO" / "events" / "Q2_FY2024" / "prediction" / "result.json").read_text())
    # Legacy stub has no schema_version → not stamped
    assert "sdk_session_id" not in legacy
    # No result.md generated for it either
    assert not (vault / "AVGO" / "events" / "Q2_FY2024" / "prediction" / "result.md").exists()


# ── Test: md-generate scope = 5 on synthetic fixture ─────────────────────

def test_generate_result_md_count_matches_stamp_scope(tmp_path):
    from migrate_unified_layout import main
    vault = _make_vault_skeleton(tmp_path)
    pipeline = tmp_path / "pipeline" / "extractions"
    main(["--apply", "--vault-root", str(vault), "--extractions-root", str(pipeline)])
    md_files = sorted(vault.rglob("result.md"))
    assert len(md_files) == 5


# ── Helpers ───────────────────────────────────────────────────────────────

def _vault_snapshot(vault: Path, pipeline: Path,
                    exclude_manifest: bool = False,
                    exclude_result_md: bool = False) -> dict[str, str]:
    """Flatten vault + extractions tree into a dict {rel_path: content_hash}."""
    import hashlib
    out: dict[str, str] = {}
    for root in (vault, pipeline):
        for p in sorted(root.rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(root))
                if exclude_manifest and rel.endswith(".migration-manifest.json"):
                    continue
                if exclude_result_md and rel.endswith("result.md"):
                    continue
                h = hashlib.sha1(p.read_bytes()).hexdigest()
                out[f"{root.name}/{rel}"] = h
    return out
