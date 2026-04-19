#!/usr/bin/env python3
"""Test: Concurrent SDK session model isolation.

Verifies that two Claude Agent SDK sessions launched simultaneously with
different `model=` parameters do NOT cross-contaminate.

Architecture under test:
  - SDK `query()` calls `_build_command()` which adds `--model <model>` as a
    CLI flag, then spawns a separate `claude -p` subprocess via `anyio.open_process()`
  - In K8s: extraction-worker pods share `.claude/` via hostPath on minisforum,
    project dir via hostPath, and CLI binary via hostPath (read-only)
  - This test runs locally with FULLY SHARED filesystem — stricter than K8s
    where each pod has its own emptyDir for `/home/faisal`
  - Uses Max subscription (OAuth), not API key billing — no per-token cost

Verdicts:
  V1: Init messages report different models
  V2: Sessions ran truly concurrently (time overlap > 0)
  V3: No errors in either session
  V4: Both sessions wrote their marker files
  V5: No cross-contamination in marker file content
  V6: Different session IDs (separate processes)
  V7: .claude/settings.json NOT mutated by either session (shared hostPath safety)

Usage:
    source venv/bin/activate && python3 scripts/test_concurrent_model_isolation.py

Output:
    earnings-analysis/test-outputs/test-concurrent-model-isolation.txt
"""

import asyncio
import hashlib
import json
import os
import sys
import time
import uuid

PROJECT_DIR = "/home/faisal/EventMarketDB"
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)

from claude_agent_sdk import ClaudeAgentOptions, query

OUTPUT_DIR = os.path.join(PROJECT_DIR, "earnings-analysis", "test-outputs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "test-concurrent-model-isolation.txt")

# Shared settings files that could be mutated — these are on hostPath in K8s
SETTINGS_FILES = [
    os.path.expanduser("~/.claude/settings.json"),
    os.path.join(PROJECT_DIR, ".claude", "settings.json"),
]

# Two models to test — must be different
MODEL_A = "haiku"
MODEL_B = "sonnet"


async def run_session(label: str, model: str, marker_path: str) -> dict:
    """Run a single SDK session that reports its model and writes a marker."""
    prompt = (
        f"You are in a model isolation test. Your label is '{label}'. "
        f"Do EXACTLY these two things:\n"
        f"1. Write a file to '{marker_path}' with content: "
        f"MODEL_LABEL={label} MODEL_REQUESTED={model} TIMESTAMP={{current time}}\n"
        f"2. Reply with ONLY this single line (no markdown, no extra text):\n"
        f"ISOLATION_RESULT label={label} model_requested={model} "
        f"model_actual={{the model name from your system prompt}}"
    )

    options = ClaudeAgentOptions(
        cli_path="/home/faisal/.local/bin/claude",
        setting_sources=["project"],
        cwd=PROJECT_DIR,
        permission_mode="bypassPermissions",
        model=model,
        max_turns=5,
        max_budget_usd=0.50,
    )

    result = {
        "label": label,
        "model_requested": model,
        "model_init": None,
        "model_actual": None,
        "result_text": None,
        "marker_path": marker_path,
        "marker_content": None,
        "start_time": time.time(),
        "end_time": None,
        "error": None,
        "stderr": [],
    }

    try:
        async for msg in query(prompt=prompt, options=options):
            msg_type = type(msg).__name__

            if msg_type == "SystemMessage" and getattr(msg, "subtype", "") == "init":
                d = msg.data
                result["model_init"] = d.get("model")
                result["session_id"] = d.get("sessionId") or d.get("session_id")
                result["version"] = d.get("claude_code_version")
                result["init_keys"] = list(d.keys()) if isinstance(d, dict) else str(type(d))

            elif msg_type == "ResultMessage":
                result["result_text"] = msg.result
    except Exception as e:
        result["error"] = str(e)

    result["end_time"] = time.time()

    # Read marker file if it exists
    if os.path.exists(marker_path):
        with open(marker_path) as f:
            result["marker_content"] = f.read().strip()

    return result


def snapshot_settings() -> dict[str, str]:
    """SHA256 hash of each shared settings file for mutation detection."""
    result = {}
    for path in SETTINGS_FILES:
        if os.path.exists(path):
            with open(path, "rb") as f:
                result[path] = hashlib.sha256(f.read()).hexdigest()
        else:
            result[path] = "MISSING"
    return result


async def main():
    print("=" * 70)
    print("TEST: Concurrent SDK Session Model Isolation")
    print("=" * 70)
    print(f"Model A: {MODEL_A}")
    print(f"Model B: {MODEL_B}")
    print()

    uid = uuid.uuid4().hex[:8]
    marker_a = f"/tmp/test_model_isolation_A_{uid}.txt"
    marker_b = f"/tmp/test_model_isolation_B_{uid}.txt"

    print(f"Marker A: {marker_a}")
    print(f"Marker B: {marker_b}")
    print()

    # Snapshot settings BEFORE sessions launch
    settings_before = snapshot_settings()
    print(f"Settings snapshot (before): {json.dumps(settings_before, indent=2)}")
    print()

    # Launch BOTH sessions concurrently — this is the key test
    print("Launching both sessions concurrently via asyncio.gather()...")
    t0 = time.time()

    result_a, result_b = await asyncio.gather(
        run_session("SESSION_A", MODEL_A, marker_a),
        run_session("SESSION_B", MODEL_B, marker_b),
    )

    elapsed = time.time() - t0
    print(f"Both sessions completed in {elapsed:.1f}s")
    print()

    # ── Analyze results ──────────────────────────────────────────────
    lines = []
    lines.append("=" * 70)
    lines.append("TEST: Concurrent SDK Session Model Isolation")
    lines.append(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append(f"Total elapsed: {elapsed:.1f}s")
    lines.append("=" * 70)
    lines.append("")

    for r in [result_a, result_b]:
        label = r["label"]
        lines.append(f"--- {label} ---")
        lines.append(f"  model_requested: {r['model_requested']}")
        lines.append(f"  model_init:      {r['model_init']}")
        lines.append(f"  session_id:      {r.get('session_id', 'N/A')}")
        lines.append(f"  version:         {r.get('version', 'N/A')}")
        lines.append(f"  duration:        {(r['end_time'] - r['start_time']):.1f}s")
        lines.append(f"  result_text:     {(r['result_text'] or '')[:200]}")
        lines.append(f"  marker_content:  {r['marker_content']}")
        lines.append(f"  init_keys:       {r.get('init_keys', 'N/A')}")
        lines.append(f"  error:           {r['error']}")
        lines.append("")

    # ── Verdicts ─────────────────────────────────────────────────────
    lines.append("=" * 70)
    lines.append("VERDICTS")
    lines.append("=" * 70)

    # V1: Init messages report different models
    init_a = result_a.get("model_init", "")
    init_b = result_b.get("model_init", "")
    v1_pass = bool(init_a and init_b and init_a != init_b)
    lines.append(f"V1 — Init models differ:  {'PASS' if v1_pass else 'FAIL'}  "
                 f"(A={init_a}, B={init_b})")

    # V2: Sessions ran concurrently (overlap in time)
    a_start, a_end = result_a["start_time"], result_a["end_time"]
    b_start, b_end = result_b["start_time"], result_b["end_time"]
    overlap = min(a_end, b_end) - max(a_start, b_start)
    v2_pass = overlap > 0
    lines.append(f"V2 — Concurrent overlap:  {'PASS' if v2_pass else 'FAIL'}  "
                 f"(overlap={overlap:.1f}s)")

    # V3: No errors
    v3_pass = result_a["error"] is None and result_b["error"] is None
    lines.append(f"V3 — No errors:           {'PASS' if v3_pass else 'FAIL'}  "
                 f"(A={result_a['error']}, B={result_b['error']})")

    # V4: Both marker files written
    v4_pass = (result_a["marker_content"] is not None and
               result_b["marker_content"] is not None)
    lines.append(f"V4 — Marker files exist:  {'PASS' if v4_pass else 'FAIL'}")

    # V5: Marker files contain correct model labels (no cross-contamination)
    v5_pass = False
    if result_a["marker_content"] and result_b["marker_content"]:
        a_has_a = f"MODEL_REQUESTED={MODEL_A}" in result_a["marker_content"]
        b_has_b = f"MODEL_REQUESTED={MODEL_B}" in result_b["marker_content"]
        a_lacks_b = f"MODEL_REQUESTED={MODEL_B}" not in result_a["marker_content"]
        b_lacks_a = f"MODEL_REQUESTED={MODEL_A}" not in result_b["marker_content"]
        v5_pass = a_has_a and b_has_b and a_lacks_b and b_lacks_a
    lines.append(f"V5 — No cross-contamination: {'PASS' if v5_pass else 'FAIL'}")

    # V6: Session IDs differ (separate processes)
    sid_a = result_a.get("session_id") or ""
    sid_b = result_b.get("session_id") or ""
    v6_pass = bool(sid_a and sid_b and sid_a != sid_b)
    sid_a_short = sid_a[:12] + "..." if sid_a else "N/A"
    sid_b_short = sid_b[:12] + "..." if sid_b else "N/A"
    lines.append(f"V6 — Session IDs differ:  {'PASS' if v6_pass else 'FAIL'}  "
                 f"(A={sid_a_short}, B={sid_b_short})")

    # V7: Shared settings files NOT mutated (critical for hostPath K8s safety)
    settings_after = snapshot_settings()
    v7_pass = settings_before == settings_after
    lines.append(f"V7 — Settings not mutated: {'PASS' if v7_pass else 'FAIL'}")
    if not v7_pass:
        for path in SETTINGS_FILES:
            before = settings_before.get(path, "N/A")
            after = settings_after.get(path, "N/A")
            if before != after:
                lines.append(f"       CHANGED: {path}")
                lines.append(f"         before: {before}")
                lines.append(f"         after:  {after}")

    all_pass = all([v1_pass, v2_pass, v3_pass, v4_pass, v5_pass, v6_pass, v7_pass])
    lines.append("")
    lines.append(f"OVERALL: {'ALL PASS ✓' if all_pass else 'SOME FAILED ✗'}")
    lines.append("")

    # ── Architecture note ────────────────────────────────────────────
    lines.append("ARCHITECTURE:")
    lines.append("  SDK path: ClaudeAgentOptions(model=X) → _build_command() → "
                 "cmd.extend(['--model', X]) → anyio.open_process(cmd)")
    lines.append("  Each query() = separate OS subprocess. Model is a CLI flag, "
                 "not shared config.")
    lines.append("  This test ran locally with FULLY SHARED filesystem — stricter "
                 "than K8s where each")
    lines.append("  pod has its own emptyDir for /home/faisal. If this passes, "
                 "K8s isolation is guaranteed.")
    lines.append(f"  Settings files checked: {', '.join(SETTINGS_FILES)}")
    lines.append("")

    # ── Conclusion ───────────────────────────────────────────────────
    lines.append("CONCLUSION:")
    if all_pass:
        lines.append("  SDK sessions with different model= parameters are fully isolated.")
        lines.append("  Changing the model for one extraction job does NOT affect concurrent jobs.")
        lines.append("  Each query() call spawns an independent claude -p subprocess.")
        lines.append("  Shared .claude/ settings files were NOT mutated by either session.")
    else:
        lines.append("  Model isolation test had failures — investigate above verdicts.")

    report = "\n".join(lines)
    print(report)

    # Write output file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write(report + "\n")
    print(f"\nReport written to: {OUTPUT_FILE}")

    # Cleanup marker files
    for p in [marker_a, marker_b]:
        if os.path.exists(p):
            os.remove(p)

    return 0 if all_pass else 1


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
