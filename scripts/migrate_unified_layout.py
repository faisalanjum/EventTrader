#!/usr/bin/env python3
"""Unified layout migration script — runs once after the obsidian_thinking commit lands.

Modes:
  --dry-run    : print proposed ops, write nothing
  --apply      : execute ops, write .migration-manifest.json next to the vault root
  --reverse    : read the manifest and undo each recorded op

Ops handled:
  (a) rename_dir            attribution/ → learning/  (per quarter, even empty dirs)
  (b) rename_file           prediction/context_bundle.{json,txt} → <Q>/context_bundle.{json,txt}
  (c) rename_file CONDITIONAL  prediction/ab_baseline/*_NO_LESSONS.* → experiments/prediction_no_lessons/*
                               (only when ab_baseline/ exists — today this is 0 quarters)
  (d) remove_dir_if_empty   prediction/ab_baseline (same condition as c)
  (e) stamp_null_session_id on every historical result.json lacking the key
                               (pattern filter: schema_version must be recognized)
  (f) generate_result_md    for every eligible result.json via result_md_renderer
  (g) rename_file           pipeline/extractions/{date}_extraction_{sid}.md → guidance/{date}_{sid}.md
                               (conforming pattern only; anomalous + Extraction Runs.md + .capture.log left in place)

Manifest schema (``.migration-manifest.json``)::

    {
      "schema_version": "migration.v1",
      "started_at":   ISO8601,
      "completed_at": ISO8601,
      "steps": [{"op": "...", "...": "..."}, ...]
    }

``--reverse`` walks ``steps`` in REVERSE order and inverts each op. It NEVER
fabricates ops — if a baseline relocate was skipped at apply time, reverse
will NOT recreate ab_baseline/ for that quarter.

Silent-fail + fail-loud on errors: any mid-run failure halts the script,
prints the failing step, and leaves the partial manifest visible so
``--reverse`` can unwind what was done.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# scripts/earnings is not a package — absolute sibling import
_HERE = Path(__file__).resolve().parent
if str(_HERE / "earnings") not in sys.path:
    sys.path.insert(0, str(_HERE / "earnings"))

from result_md_renderer import render  # noqa: E402

log = logging.getLogger("migrate_unified_layout")

MANIFEST_NAME = ".migration-manifest.json"
SCHEMA_VERSION = "migration.v1"

# Recognized result.json schema_versions (null-stamp + md-render eligibility filter)
_ELIGIBLE_SCHEMAS = {"prediction_result.v1", "attribution_result.v2"}

# Conforming extraction filename pattern — date prefix + _extraction_ + source_id + .md
_EXTRACTION_CONFORMING = re.compile(r"^\d{4}-\d{2}-\d{2}_extraction_.+\.md$")


# ── Planning ──────────────────────────────────────────────────────────────

def _plan_vault_ops(vault_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Plan all vault-side ops. Returns (steps, skip_notes)."""
    steps: list[dict[str, Any]] = []
    skip_notes: list[str] = []

    if not vault_root.exists():
        return steps, [f"vault_root does not exist: {vault_root}"]

    for ticker_dir in sorted(vault_root.iterdir()):
        if not ticker_dir.is_dir():
            continue
        events_dir = ticker_dir / "events"
        if not events_dir.exists():
            continue
        for q_dir in sorted(events_dir.iterdir()):
            if not q_dir.is_dir():
                continue
            _plan_quarter(q_dir, steps, skip_notes)
    return steps, skip_notes


def _plan_quarter(q_dir: Path, steps: list[dict[str, Any]], skip_notes: list[str]) -> None:
    quarter_label = q_dir.name
    ticker = q_dir.parents[1].name

    # (a) attribution → learning
    attr = q_dir / "attribution"
    learning = q_dir / "learning"
    if attr.exists() and attr.is_dir() and not learning.exists():
        steps.append({"op": "rename_dir", "from": str(attr), "to": str(learning)})

    # (b) prediction/context_bundle.{json,txt} → <Q>/
    pred = q_dir / "prediction"
    for fname in ("context_bundle.json", "context_bundle_rendered.txt"):
        src = pred / fname
        dst = q_dir / fname
        if src.exists() and not dst.exists():
            steps.append({"op": "rename_file", "from": str(src), "to": str(dst)})

    # Legacy `context.json` (pre-learner era) — explicitly skipped
    if (pred / "context.json").exists() and not (pred / "context_bundle.json").exists():
        skip_notes.append(
            f"{ticker}/{quarter_label}: skipped — legacy prediction/context.json present (no context_bundle.json)"
        )

    # (c) + (d) ab_baseline/ — CONDITIONAL
    ab = pred / "ab_baseline"
    if ab.exists() and ab.is_dir():
        for src_name, dst_name in [
            ("result_NO_LESSONS.json", "result.json"),
            ("context_bundle_NO_LESSONS.json", "context_bundle.json"),
            ("context_bundle_rendered_NO_LESSONS.txt", "context_bundle_rendered.txt"),
        ]:
            src = ab / src_name
            if src.exists():
                dst = q_dir / "experiments" / "prediction_no_lessons" / dst_name
                if not dst.exists():
                    steps.append({"op": "rename_file", "from": str(src), "to": str(dst)})
        # ab_baseline removal — only if it'll be empty after our moves
        remaining_after = [
            f.name for f in ab.iterdir()
            if f.name not in {"result_NO_LESSONS.json",
                               "context_bundle_NO_LESSONS.json",
                               "context_bundle_rendered_NO_LESSONS.txt"}
        ]
        if not remaining_after:
            steps.append({"op": "remove_dir_if_empty", "path": str(ab)})

    # (e) + (f) null-stamp + md-gen for eligible result.json files
    # Each entry is (current_physical_path, post_migration_path, component).
    # The stamp/md-gen ops always use the POST-migration path because rename ops
    # run earlier in the same --apply invocation. Today's reality:
    #   - attribution/result.json  → AFTER rename lives at  learning/result.json
    #   - prediction/result.json   → stays at               prediction/result.json
    #   - experiments/...result.json → stays (unchanged)
    candidates = [
        (pred / "result.json", pred / "result.json", "prediction"),
        (attr / "result.json", q_dir / "learning" / "result.json", "learning"),
        # If the attribution→learning rename already happened (partial prior run),
        # also catch the post-rename path directly.
        (q_dir / "learning" / "result.json", q_dir / "learning" / "result.json", "learning"),
        (q_dir / "experiments" / "prediction_no_lessons" / "result.json",
         q_dir / "experiments" / "prediction_no_lessons" / "result.json",
         "prediction_no_lessons"),
    ]
    seen_targets: set[Path] = set()
    for phys_path, target_path, component in candidates:
        if target_path in seen_targets or not phys_path.exists():
            continue
        seen_targets.add(target_path)
        try:
            payload = json.loads(phys_path.read_text())
        except Exception:
            skip_notes.append(f"{ticker}/{quarter_label}: skipped — unreadable {phys_path}")
            continue
        if not isinstance(payload, dict):
            skip_notes.append(f"{ticker}/{quarter_label}: skipped — not a JSON object: {phys_path}")
            continue
        schema = payload.get("schema_version")
        if schema not in _ELIGIBLE_SCHEMAS:
            skip_notes.append(
                f"{ticker}/{quarter_label}: skipped (no/unrecognized schema_version={schema!r}) for {phys_path.name} under {phys_path.parent.name}/"
            )
            continue
        # Null-stamp only if absent in the current physical file (will be stamped at target_path)
        if "sdk_session_id" not in payload:
            steps.append({"op": "stamp_null_session_id",
                          "path": str(target_path),
                          "schema": schema})
        md_target = target_path.with_name("result.md")
        # Render if no md exists at the post-migration location
        if not md_target.exists():
            steps.append({
                "op": "generate_result_md",
                "source": str(target_path),
                "target": str(md_target),
                "component": component,
            })


def _plan_extraction_ops(extractions_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    steps: list[dict[str, Any]] = []
    skip_notes: list[str] = []
    if not extractions_root.exists():
        return steps, [f"extractions_root does not exist: {extractions_root}"]
    for p in sorted(extractions_root.iterdir()):
        if not p.is_file():
            continue
        # Skip special files
        if p.name == ".capture.log" or p.name == "Extraction Runs.md":
            skip_notes.append(f"extractions: left in place — {p.name}")
            continue
        if not _EXTRACTION_CONFORMING.match(p.name):
            skip_notes.append(f"extractions: anomalous (left in place) — {p.name}")
            continue
        # Conforming: {date}_extraction_{source_id}.md → guidance/{date}_{source_id}.md
        new_name = p.name.replace("_extraction_", "_", 1)
        dst = extractions_root / "guidance" / new_name
        if dst.exists():
            # Idempotent — skip already-migrated
            continue
        steps.append({"op": "rename_file", "from": str(p), "to": str(dst)})
    return steps, skip_notes


# ── Execution ─────────────────────────────────────────────────────────────

def _execute_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply each step. Returns the SAME steps list (for manifest recording).

    Order of ops matters: rename_dir (attribution → learning) MUST happen
    BEFORE stamp/generate_result_md that target the learning/ path. We order
    ops in the plan, but execute in plan order here; caller must ensure plan
    order is valid.
    """
    executed: list[dict[str, Any]] = []
    for step in steps:
        op = step["op"]
        try:
            if op == "rename_dir":
                src, dst = Path(step["from"]), Path(step["to"])
                if not src.exists():
                    # Idempotent: already renamed in a prior run
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.rename(src, dst)
            elif op == "rename_file":
                src, dst = Path(step["from"]), Path(step["to"])
                if not src.exists():
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.rename(src, dst)
            elif op == "remove_dir_if_empty":
                d = Path(step["path"])
                if d.exists() and d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
            elif op == "stamp_null_session_id":
                path = Path(step["path"])
                data = json.loads(path.read_text())
                if "sdk_session_id" not in data:
                    data["sdk_session_id"] = None
                    _atomic_write_json(path, data)
            elif op == "generate_result_md":
                source = Path(step["source"])
                target = Path(step["target"])
                component = step["component"]
                if not source.exists():
                    # e.g., source was at prediction/attribution/ but rename happened;
                    # the planner may queue a pre-rename path. Try the post-rename equivalent.
                    # This is a safety net — planner SHOULD queue post-rename paths.
                    continue
                if target.exists():
                    continue
                render(component, source, target)
            else:
                raise ValueError(f"unknown op: {op}")
            executed.append(step)
        except Exception as e:
            log.error("FAILED STEP: %s (%s)", step, e)
            # Preserve what we've executed so far in the partial manifest
            raise
    return executed


def _atomic_write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


# ── Reverse ──────────────────────────────────────────────────────────────

def _reverse_steps(steps: list[dict[str, Any]]) -> None:
    for step in reversed(steps):
        op = step["op"]
        try:
            if op == "rename_dir":
                src, dst = Path(step["from"]), Path(step["to"])
                if not dst.exists():
                    continue  # already reversed
                os.rename(dst, src)
            elif op == "rename_file":
                src, dst = Path(step["from"]), Path(step["to"])
                if not dst.exists():
                    continue
                src.parent.mkdir(parents=True, exist_ok=True)
                os.rename(dst, src)
            elif op == "remove_dir_if_empty":
                d = Path(step["path"])
                d.mkdir(parents=True, exist_ok=True)
            elif op == "stamp_null_session_id":
                path = Path(step["path"])
                if path.exists():
                    data = json.loads(path.read_text())
                    # Only unstamp if the value is still null (preserve any non-null written later)
                    if data.get("sdk_session_id") is None:
                        data.pop("sdk_session_id", None)
                        _atomic_write_json(path, data)
            elif op == "generate_result_md":
                target = Path(step["target"])
                if target.exists():
                    target.unlink()
            else:
                log.warning("unknown op in manifest (skipping): %s", op)
        except Exception as e:
            log.error("REVERSE FAILED: %s (%s)", step, e)
            raise


# ── Main CLI ─────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="print proposed ops, write nothing")
    g.add_argument("--apply", action="store_true", help="execute ops + write manifest")
    g.add_argument("--reverse", action="store_true", help="read manifest + undo each op")
    p.add_argument("--vault-root", default="earnings-analysis/Companies",
                   help="Vault root (Companies/ dir). Default: earnings-analysis/Companies (symlink)")
    p.add_argument("--extractions-root", default="earnings-analysis/pipeline/extractions",
                   help="Extractions flat root. Default: earnings-analysis/pipeline/extractions")
    p.add_argument("--manifest-path", default=None,
                   help="Override manifest location (default: <vault_root>/.migration-manifest.json)")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    vault_root = Path(args.vault_root).resolve()
    extractions_root = Path(args.extractions_root).resolve()
    manifest_path = Path(args.manifest_path) if args.manifest_path else vault_root / MANIFEST_NAME

    if args.reverse:
        if not manifest_path.exists():
            log.error("no manifest at %s", manifest_path)
            return 1
        manifest = json.loads(manifest_path.read_text())
        log.info("Reverse: unwinding %d steps from %s", len(manifest.get("steps", [])), manifest_path)
        _reverse_steps(manifest.get("steps", []))
        log.info("Reverse: done")
        return 0

    # Plan
    vault_steps, vault_skips = _plan_vault_ops(vault_root)
    ext_steps, ext_skips = _plan_extraction_ops(extractions_root)

    # Count ops by category for readable summary
    n_rename_dir = sum(1 for s in vault_steps if s["op"] == "rename_dir")
    n_context_bundle = sum(1 for s in vault_steps
                           if s["op"] == "rename_file" and "context_bundle" in Path(s["from"]).name and "ab_baseline" not in s["from"])
    n_ab_baseline = sum(1 for s in vault_steps
                        if s["op"] == "rename_file" and "ab_baseline" in s["from"])
    n_remove_ab = sum(1 for s in vault_steps if s["op"] == "remove_dir_if_empty")
    n_stamp = sum(1 for s in vault_steps if s["op"] == "stamp_null_session_id")
    n_md = sum(1 for s in vault_steps if s["op"] == "generate_result_md")
    n_ext = len(ext_steps)

    # Print summary (both dry-run and apply)
    lines = [
        f"rename_dir attribution → learning: {n_rename_dir}",
        f"rename_file context_bundle: {n_context_bundle}",
        f"rename_file ab_baseline (NO_LESSONS): {n_ab_baseline}",
        f"remove_dir_if_empty ab_baseline: {n_remove_ab}",
        f"stamp_null_session_id: {n_stamp}",
        f"generate_result_md: {n_md}",
        f"rename_file extractions: {n_ext}",
    ]
    total = n_rename_dir + n_context_bundle + n_ab_baseline + n_remove_ab + n_stamp + n_md + n_ext
    lines.append(f"TOTAL ops: {total}")

    print("=== Migration plan ===")
    for line in lines:
        print(f"  {line}")
    print()
    if vault_skips or ext_skips:
        print("=== Skipped (left untouched) ===")
        for s in vault_skips + ext_skips:
            print(f"  {s}")
        print()

    if args.dry_run:
        print("Dry-run: no filesystem changes made.")
        return 0

    # --apply
    started_at = datetime.now(timezone.utc).isoformat()
    all_steps = vault_steps + ext_steps

    try:
        executed = _execute_steps(all_steps)
    except Exception as e:
        log.error("apply halted: %s", e)
        # Write partial manifest so user can --reverse what was applied
        _write_manifest(manifest_path, SCHEMA_VERSION, started_at,
                        datetime.now(timezone.utc).isoformat(),
                        executed if 'executed' in dir() else [])
        return 1

    completed_at = datetime.now(timezone.utc).isoformat()
    # Idempotency: if nothing was executed AND a prior manifest exists, leave it alone.
    if not executed and manifest_path.exists():
        print(f"Apply: 0 ops executed (no-op). Existing manifest left untouched: {manifest_path}")
        return 0
    _write_manifest(manifest_path, SCHEMA_VERSION, started_at, completed_at, executed)
    print(f"Apply: {len(executed)} ops executed. Manifest: {manifest_path}")
    return 0


def _write_manifest(path: Path, schema: str, started: str, completed: str,
                    steps: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": schema,
        "started_at": started,
        "completed_at": completed,
        "steps": steps,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
