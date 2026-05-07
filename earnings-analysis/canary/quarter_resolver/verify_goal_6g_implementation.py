#!/usr/bin/env python3
"""
verify_goal_6g_implementation.py — Independent verifier for Goal 6g
(audited-issuer ticker bucket on calendar FY-disagreement override).

HAND-WRITTEN BY HUMANS to prevent self-rubber-stamping. Codex/agents
must NOT modify this file; checked via git diff.

WHY A NEW VERIFIER (not Goal 6c reused):
  Goal 6c's verifier intentionally bans ANY ticker frozenset / ticker
  table by regex. Goal 6g deliberately introduces ONE narrow ticker
  set (TRUST_XBRL_ADVANCE = 18 specific tickers). Goal 6c's regex will
  reject Goal 6g's production code by design. Goal 6g therefore needs
  its own verifier with a different ban-list:
    - exactly ONE allowed ticker frozenset literal: TRUST_XBRL_ADVANCE
    - no other ticker tables (industry/sector/SIC/CIK/EX-99/etc still banned)
    - no per-(ticker, period) data structures (constraint: per-company
      rule must hold across all periods)

CHECKS PERFORMED:
  G1.  This verifier is git-clean (anti-tampering)
  G2.  Immutable inputs DIRECTLY USED BY THIS VERIFIER are git-clean:
       - goal6a_d_measurement.csv (Goal 6a's frozen D spec; G6 reference)
       - goal6g_baseline.csv (built by build_goal6g_baseline.py; G6+G9 reference)
       - ground_truth.csv (Goal 1 corpus; tangential reference)
       - needs_review.csv (Goal 1 corpus; tangential reference)
       Note: the broader audit_evidence/ tree is NOT directly checked
       here — those files are inputs to other verifiers. This gate only
       guards what this Goal 6g verifier actually loads.
  G3.  Production scope: only the same files Goal 6c allowed
       (quarter_identity.py, test_quarter_identity.py,
       test_quarter_identity_u64.py) are modified vs HEAD.
       earnings_orchestrator.py / harvest_guidance_sessions.py /
       fiscal_math.py UNCHANGED.
  G4.  TRUST_XBRL_ADVANCE structural constraint:
       - exactly the 18 expected tickers (frozen list below)
       - declared as frozenset[str] (no per-(ticker,period) dimension)
       - exactly ONE such set in production code (no other ticker tables)
  G5.  Banned-pattern regex (industry/sector/SIC/GICS/NAICS/CIK/EX-99/
       HTTP/ML/LLM/per-period-ticker-table) still passes.
  G6.  Per-row baseline match: production resolver output for ALL 10,674
       rows must equal goal6g_baseline.csv on (outcome, fy, q, source).
       --fast samples 200 rows.
  G7.  FCX `0000831259-26-000021` still resolves to
       Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1
       (Goal 4 + 6c regression).
  G8.  Rule F 115 odd_52_53 set still 94 OK / 0 WRONG / 21 FAIL_CLOSED
       (Goal 4 regression).
  G9.  GIII still fail-closes on its calendar-FY-disagreement rows
       (NOT in bucket; baseline has 12 GIII rows still FC).
  G10. pytest scripts/earnings/test_quarter_identity.py exits 0
  G11. pytest -k write_guard exits 0 (orchestrator guard intact)
  G12. NEW source string `rule_h_trusted_issuer_xbrl_advance` present in
       quarter_identity.py.

EXIT CODES:
  0 = pass
  1 = fatal violation
  2 = verifier infra failed
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import subprocess
import sys
from pathlib import Path


# ── Paths ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parents[2]
QI_PATH = PROJECT_ROOT / "scripts/earnings/quarter_identity.py"
ORCHESTRATOR_PATH = PROJECT_ROOT / "scripts/earnings/earnings_orchestrator.py"
TEST_QI_PATH = PROJECT_ROOT / "scripts/earnings/test_quarter_identity.py"
TEST_QI_U64_PATH = PROJECT_ROOT / "scripts/earnings/test_quarter_identity_u64.py"
FISCAL_MATH_PATH = PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts/fiscal_math.py"
HARVEST_GUIDANCE_PATH = PROJECT_ROOT / "scripts/harvest_guidance_sessions.py"

D_MEASUREMENT_CSV = _HERE / "goal6a_d_measurement.csv"
GOAL6G_BASELINE_CSV = _HERE / "goal6g_baseline.csv"
GROUND_TRUTH_PATH = _HERE / "ground_truth.csv"
NEEDS_REVIEW_PATH = _HERE / "needs_review.csv"

ALLOWED_PROD_MODIFICATIONS = {
    "scripts/earnings/quarter_identity.py",
    "scripts/earnings/test_quarter_identity.py",
    "scripts/earnings/test_quarter_identity_u64.py",
}

PRODUCTION_FILES_LOCKED = [
    PROJECT_ROOT / "scripts/earnings/earnings_orchestrator.py",
    PROJECT_ROOT / "scripts/harvest_guidance_sessions.py",
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts/fiscal_math.py",
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py",
]

# ── Frozen expectations ────────────────────────────────────────────────
EXPECTED_TRUST_BUCKET = frozenset({
    "ACI", "ASO", "BJ", "BURL", "CHWY", "DLTR", "FIVE", "GME",
    "KSS", "LOW", "LULU", "OXM", "ROST", "ULTA",
    "KR", "OLLI", "PLAY", "RH",
})
EXPECTED_NEW_SOURCE = "rule_h_trusted_issuer_xbrl_advance"
EXPECTED_BUCKET_NAME = "TRUST_XBRL_ADVANCE"

FCX_ACCESSION_8K = "0000831259-26-000021"
FCX_EXPECTED = {
    "fy": "2026",
    "q": "Q1",
    "outcome": "AUTO_OK",
    "source": "prior_periodic_projection_q4_to_q1",
}

# ── Banned production patterns ─────────────────────────────────────────
# Goal 6g allows EXACTLY ONE ticker frozenset (TRUST_XBRL_ADVANCE).
# All other ticker tables, industry/sector lookups, EX-99 parsing,
# external HTTP, ML/LLM, and per-(ticker,period) structures stay banned.
BANNED_PATTERNS = [
    # Hardcoded ticker comparisons OUTSIDE the bucket helper
    re.compile(
        r"if\s+ticker\s+in\s*[\(\{]['\"](?:AAP|PSTG|NTAP|PEP|LEVI|SYNA|GIII|BOX|WDAY|WMS|NTNX|CNM|PVH|ANF|DKS|PHR|PINC|PRU)"
    ),
    re.compile(
        r"ticker\s*==\s*['\"](?:AAP|PSTG|NTAP|PEP|LEVI|SYNA|GIII|BOX|WDAY|WMS|NTNX|CNM|PVH|ANF|DKS|PHR|PINC|PRU)"
    ),
    # Industry / sector / classifier lookups
    re.compile(r"\b(industry|sector|SIC|GICS|NAICS|CIK)_(?:lookup|map|table|dispatch|classifier)\b", re.I),
    re.compile(r"\b(industry|sector)\s*==\s*['\"]"),
    # EX-99 / press-release text parsing
    re.compile(r"EX[_-]?99[_.]?1?[_.]?(parse|regex|extract|read)", re.I),
    re.compile(r"press[_-]?release[_.]?(parse|regex|extract)", re.I),
    # External HTTP / SEC scrape
    re.compile(r"\b(requests|httpx|urllib)\.(?:get|post|request)\b"),
    re.compile(r"sec\.gov/Archives", re.I),
    # ML / LLM imports or calls (not the `.claude` directory path)
    re.compile(r"(?:^|\s)(?:import|from)\s+(?:anthropic|openai|claude_agent_sdk)\b"),
    re.compile(r"\b(?:anthropic|openai)\s*\.\s*[A-Z]"),
    re.compile(r"\bclaude_agent_sdk\."),
    # Per-(ticker, period) data structures — constraint: per-company rule
    # must hold for all periods. Tuple keys with ticker+period are banned.
    re.compile(r"\(\s*ticker\s*,\s*(?:period|quarter|fy|fiscal_year|year)\s*\)\s*:"),
    re.compile(r"['\"][A-Z]{1,5}[_:][0-9]{4}[_:Q][0-9]?['\"]"),  # "ACI:2023:Q1" style
]

ALLOWED_BUCKET_LITERAL_RE = re.compile(
    r"TRUST_XBRL_ADVANCE\s*=\s*frozenset\s*\(\s*\{[^}]+\}\s*\)",
    re.MULTILINE | re.DOTALL,
)


def _git(*args: str, cwd: Path = PROJECT_ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def _file_dirty(rel_path: str) -> bool:
    try:
        out = _git("status", "--porcelain", "--", rel_path)
    except subprocess.CalledProcessError:
        return True
    return bool(out)


# ── Gates ───────────────────────────────────────────────────────────────


def gate_g1_self_clean(failures: list[str]) -> None:
    rel = str(Path(__file__).resolve().relative_to(PROJECT_ROOT))
    if _file_dirty(rel):
        failures.append(f"G1 FAIL: verifier itself ({rel}) is git-dirty")
    else:
        print("G1 OK: verifier git-clean")


def gate_g2_immutable_inputs(failures: list[str]) -> None:
    inputs = [
        D_MEASUREMENT_CSV,
        GOAL6G_BASELINE_CSV,
        GROUND_TRUTH_PATH,
        NEEDS_REVIEW_PATH,
    ]
    bad = []
    for p in inputs:
        if not p.exists():
            bad.append(f"{p} (MISSING)")
            continue
        rel = str(p.relative_to(PROJECT_ROOT))
        if _file_dirty(rel):
            bad.append(f"{rel} (dirty)")
    if bad:
        failures.append("G2 FAIL: immutable inputs not git-clean: " + "; ".join(bad))
    else:
        print("G2 OK: immutable inputs git-clean")


def gate_g3_production_scope(failures: list[str]) -> None:
    try:
        out = _git("diff", "--name-only", "HEAD", "--", "scripts/earnings/", "scripts/harvest_guidance_sessions.py", ".claude/skills/earnings-orchestrator/scripts/")
    except subprocess.CalledProcessError as e:
        failures.append(f"G3 FAIL: git diff error: {e}")
        return

    changed = [line for line in out.splitlines() if line.strip()]
    bad = [c for c in changed if c not in ALLOWED_PROD_MODIFICATIONS]
    if bad:
        failures.append(f"G3 FAIL: forbidden production files modified: {bad}")
        return

    for locked in PRODUCTION_FILES_LOCKED:
        if not locked.exists():
            continue
        rel = str(locked.relative_to(PROJECT_ROOT))
        if _file_dirty(rel):
            failures.append(f"G3 FAIL: locked production file {rel} is dirty")
            return

    print(f"G3 OK: production scope clean ({len(changed)} allowed files modified)")


def gate_g4_trust_bucket_structure(failures: list[str]) -> None:
    if not QI_PATH.exists():
        failures.append("G4 FAIL: quarter_identity.py missing")
        return
    src = QI_PATH.read_text()

    # Must declare TRUST_XBRL_ADVANCE
    if EXPECTED_BUCKET_NAME not in src:
        failures.append(f"G4 FAIL: {EXPECTED_BUCKET_NAME} not declared in quarter_identity.py")
        return

    # Must be a frozenset literal (structural constraint: no per-period dim)
    m = ALLOWED_BUCKET_LITERAL_RE.search(src)
    if not m:
        failures.append(
            f"G4 FAIL: {EXPECTED_BUCKET_NAME} not declared as frozenset({{...}}) literal "
            f"(constraint: ticker-only set, no period dim)"
        )
        return

    # Extract ticker set from the literal — must equal EXPECTED
    body = m.group(0)
    found = set(re.findall(r"['\"]([A-Z]{1,5})['\"]", body))
    if found != EXPECTED_TRUST_BUCKET:
        extra = found - EXPECTED_TRUST_BUCKET
        missing = EXPECTED_TRUST_BUCKET - found
        msg = []
        if extra:
            msg.append(f"unexpected: {sorted(extra)}")
        if missing:
            msg.append(f"missing: {sorted(missing)}")
        failures.append(f"G4 FAIL: {EXPECTED_BUCKET_NAME} mismatch — " + "; ".join(msg))
        return

    # Must NOT have OTHER ticker containers (any kind: frozenset/set/dict/list/tuple).
    # Heuristic: scan top-level UPPERCASE assignments. If the body contains ≥8 distinct
    # ticker-like literals (letter-only 2-5 char uppercase strings, not Q1-Q4 fiscal
    # placeholders), it's a ticker container — and must be TRUST_XBRL_ADVANCE.
    top_level_assigns = re.findall(
        r"^([A-Z][A-Z0-9_]*)\s*=\s*(.+?)(?=\n[A-Z_]|\nclass\s|\ndef\s|\Z)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    QUARTER_TOKENS = {"Q1", "Q2", "Q3", "Q4", "FY", "EX"}
    suspect_containers = []
    for name, body in top_level_assigns:
        # Letter-only 2-5 uppercase chars, in single OR double quotes
        ticker_strings = set(re.findall(r"['\"]([A-Z]{2,5})['\"]", body))
        ticker_strings -= QUARTER_TOKENS
        if len(ticker_strings) >= 8:
            suspect_containers.append((name, sorted(ticker_strings)[:5]))
    extra = [(n, sample) for (n, sample) in suspect_containers if n != EXPECTED_BUCKET_NAME]
    if extra:
        msg = "; ".join(f"{n} (sample: {s})" for n, s in extra)
        failures.append(f"G4 FAIL: extra ticker container(s) in quarter_identity.py: {msg}")
        return

    # Hard-bound: there must be EXACTLY ONE ticker container, and it must be ours
    if len(suspect_containers) != 1:
        failures.append(
            f"G4 FAIL: expected exactly 1 ticker container ({EXPECTED_BUCKET_NAME}); "
            f"found {len(suspect_containers)}: {[n for n, _ in suspect_containers]}"
        )
        return

    print(f"G4 OK: TRUST_XBRL_ADVANCE = exactly {len(EXPECTED_TRUST_BUCKET)} expected tickers, frozenset[str], sole ticker container")


def gate_g5_banned_patterns(failures: list[str]) -> None:
    if not QI_PATH.exists():
        failures.append("G5 FAIL: quarter_identity.py missing")
        return
    src = QI_PATH.read_text()
    hits = []
    for pat in BANNED_PATTERNS:
        m = pat.search(src)
        if m:
            line_no = src[: m.start()].count("\n") + 1
            hits.append(f"line {line_no}: {pat.pattern[:80]}")
    if hits:
        failures.append("G5 FAIL: banned patterns in quarter_identity.py:\n  " + "\n  ".join(hits))
    else:
        print("G5 OK: no banned patterns detected")


def _resolve_per_row(rows: list[dict]) -> list[dict]:
    """Run production resolver for each (ticker, accession_8k) and return outputs."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))
    if "quarter_identity" in sys.modules:
        del sys.modules["quarter_identity"]
    from quarter_identity import resolve_quarter_info
    out = []
    for r in rows:
        try:
            result = resolve_quarter_info(r["ticker"], r["accession_8k"])
        except Exception as e:
            out.append({
                "ticker": r["ticker"],
                "accession_8k": r["accession_8k"],
                "outcome": "ERROR",
                "fy": "",
                "q": "",
                "source": f"resolver_error: {e}",
            })
            continue
        label = result.get("quarter_label") or ""
        fy = q = ""
        if label and "_FY" in label:
            q, fy = label.split("_FY", 1)
        out.append({
            "ticker": r["ticker"],
            "accession_8k": r["accession_8k"],
            "outcome": result.get("safety_action") or "",
            "fy": fy,
            "q": q,
            "source": result.get("quarter_identity_source") or "",
        })
    return out


def gate_g6_per_row_baseline_match(failures: list[str], fast: bool = False) -> None:
    if not GOAL6G_BASELINE_CSV.exists():
        failures.append(f"G6 FAIL: {GOAL6G_BASELINE_CSV} missing — run build_goal6g_baseline.py first")
        return
    with GOAL6G_BASELINE_CSV.open() as fh:
        baseline = {(r["ticker"], r["accession_8k"]): r for r in csv.DictReader(fh)}

    rows = [{"ticker": t, "accession_8k": a} for (t, a) in sorted(baseline.keys())]
    if fast:
        rng = random.Random(42)
        rng.shuffle(rows)
        rows = rows[:200]

    try:
        actuals = _resolve_per_row(rows)
    except Exception as e:
        failures.append(f"G6 FAIL: resolver error: {e}")
        return

    mismatches = []
    flipped = 0
    for got in actuals:
        key = (got["ticker"], got["accession_8k"])
        exp = baseline[key]
        for fld in ("outcome", "fy", "q", "source"):
            g, e = (got.get(fld) or ""), (exp.get(fld) or "")
            if g != e:
                mismatches.append(f"{key} {fld}: got={g!r} exp={e!r}")
                break
        if exp.get("source") == EXPECTED_NEW_SOURCE:
            flipped += 1
    if mismatches:
        failures.append(
            f"G6 FAIL: {len(mismatches)} row(s) don't match goal6g_baseline.csv. "
            f"First 5: " + "; ".join(mismatches[:5])
        )
        return
    print(f"G6 OK: {len(actuals)} rows match goal6g_baseline.csv ({flipped} via {EXPECTED_NEW_SOURCE})")


def gate_g7_fcx_regression(failures: list[str]) -> None:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))
    if "quarter_identity" in sys.modules:
        del sys.modules["quarter_identity"]
    from quarter_identity import resolve_quarter_info
    result = resolve_quarter_info("FCX", FCX_ACCESSION_8K)
    label = result.get("quarter_label") or ""
    src = result.get("quarter_identity_source") or ""
    safe = result.get("safety_action") or ""
    if label != "Q1_FY2026" or safe != "AUTO_OK" or src != FCX_EXPECTED["source"]:
        failures.append(
            f"G7 FAIL: FCX regression — got label={label!r}, safety={safe!r}, "
            f"source={src!r}; expected Q1_FY2026 / AUTO_OK / {FCX_EXPECTED['source']}"
        )
    else:
        print("G7 OK: FCX 0000831259-26-000021 → Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1")


def gate_g8_rulef_regression(failures: list[str]) -> None:
    """Rule F regression: 115 odd_52_53 rows → exactly 94/0/21."""
    if not GOAL6G_BASELINE_CSV.exists():
        failures.append("G8 FAIL: baseline missing")
        return
    rule_f_sources = {
        "rule_f_direct_recent_prior",
        "rule_f_fail_closed_fy_disagreement",
        "rule_f_advance_xbrl",
    }
    with D_MEASUREMENT_CSV.open() as fh:
        d_rows = list(csv.DictReader(fh))
    rule_f_rows = [r for r in d_rows if r.get("source") in rule_f_sources]
    n_ok = sum(1 for r in rule_f_rows if r["outcome"] == "AUTO_OK" and r["correct"] == "true")
    n_wrong = sum(1 for r in rule_f_rows if r["outcome"] == "AUTO_OK" and r["correct"] == "false")
    n_fc = sum(1 for r in rule_f_rows if r["outcome"] == "FAIL_CLOSED")
    if (n_ok, n_wrong, n_fc) != (94, 0, 21):
        failures.append(
            f"G8 FAIL: Rule F regression — got {n_ok}/{n_wrong}/{n_fc}, expected 94/0/21"
        )
    else:
        print("G8 OK: Rule F preserved (94 OK / 0 WRONG / 21 FAIL_CLOSED)")


def gate_g9_giii_still_fail_closed(failures: list[str]) -> None:
    """GIII must remain fail-closed — not in TRUST_XBRL_ADVANCE."""
    with GOAL6G_BASELINE_CSV.open() as fh:
        rows = [r for r in csv.DictReader(fh) if r["ticker"] == "GIII"]
    fc = [r for r in rows if r["outcome"] == "FAIL_CLOSED"]
    auto = [r for r in rows if r["outcome"] == "AUTO_OK"]
    if not fc or auto:
        failures.append(
            f"G9 FAIL: GIII not preserved fail-closed — "
            f"FC={len(fc)}, AUTO_OK={len(auto)} (expected: all FC)"
        )
    else:
        print(f"G9 OK: GIII still fail-closes in baseline ({len(fc)} rows)")


def gate_g10_pytest(failures: list[str]) -> None:
    cmd = [
        str(PROJECT_ROOT / "venv/bin/python"),
        "-m", "pytest",
        "scripts/earnings/test_quarter_identity.py",
        "-q", "--no-header", "-x",
    ]
    try:
        subprocess.check_call(cmd, cwd=PROJECT_ROOT)
        print("G10 OK: pytest test_quarter_identity.py passed")
    except subprocess.CalledProcessError as e:
        failures.append(f"G10 FAIL: pytest test_quarter_identity.py exit {e.returncode}")


def gate_g11_write_guard(failures: list[str]) -> None:
    cmd = [
        str(PROJECT_ROOT / "venv/bin/python"),
        "-m", "pytest", "scripts/earnings",
        "-k", "write_guard",
        "-q", "--no-header", "-x",
    ]
    try:
        subprocess.check_call(cmd, cwd=PROJECT_ROOT)
        print("G11 OK: pytest -k write_guard passed")
    except subprocess.CalledProcessError as e:
        failures.append(f"G11 FAIL: pytest -k write_guard exit {e.returncode}")


def gate_g12_new_source_present(failures: list[str]) -> None:
    if not QI_PATH.exists():
        failures.append("G12 FAIL: quarter_identity.py missing")
        return
    src = QI_PATH.read_text()
    if EXPECTED_NEW_SOURCE not in src:
        failures.append(f"G12 FAIL: source string {EXPECTED_NEW_SOURCE!r} not present in quarter_identity.py")
    else:
        print(f"G12 OK: new source string {EXPECTED_NEW_SOURCE!r} present")


# ── Main ──────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true",
                        help="Sample 200 rows for G6 instead of all 10,674")
    parser.add_argument("--skip-resolver", action="store_true",
                        help="Skip G6/G7 (don't run resolver — useful before prod change is live)")
    parser.add_argument("--skip-pytest", action="store_true",
                        help="Skip G10/G11 (don't run pytest)")
    args = parser.parse_args()

    failures: list[str] = []

    gate_g1_self_clean(failures)
    gate_g2_immutable_inputs(failures)
    gate_g3_production_scope(failures)
    gate_g4_trust_bucket_structure(failures)
    gate_g5_banned_patterns(failures)
    if not args.skip_resolver:
        gate_g6_per_row_baseline_match(failures, fast=args.fast)
        gate_g7_fcx_regression(failures)
    gate_g8_rulef_regression(failures)
    gate_g9_giii_still_fail_closed(failures)
    if not args.skip_pytest:
        gate_g10_pytest(failures)
        gate_g11_write_guard(failures)
    gate_g12_new_source_present(failures)

    print()
    if failures:
        print("=" * 60)
        print(f"GOAL 6g VERIFIER FAILED ({len(failures)} gate(s)):")
        for f in failures:
            print(f"  - {f}")
        print("=" * 60)
        return 1
    print("=" * 60)
    print("GOAL 6g VERIFIER PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
