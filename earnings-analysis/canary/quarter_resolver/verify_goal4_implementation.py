#!/usr/bin/env python3
"""
verify_goal4_implementation.py — Independent verifier for Goal 4 (Rule F
production resolver + orchestrator destructive-write guard).

HAND-WRITTEN BY HUMANS to prevent self-rubber-stamping. Codex must NOT
modify this file; checked via git diff.

CHECKS PERFORMED (default = canonical sign-off; --fast for iteration):
  G1.  Verifier file is git-clean (anti-tampering)
  G2.  scripts/earnings/quarter_identity.py modified — old `_STALE_MATCH_DAYS=150`
       cascade GONE; ALL Rule F source strings present;
       NO ticker allowlist/denylist/FY-table patterns (structural-only check)
  G3.  No production code modified outside allowed paths
       (quarter_identity.py + orchestrator entry + test files)
  G4.  resolve_quarter_info importable; signature unchanged
  G5.  115 odd_52_53 test set produces EXACTLY 94 OK / 0 WRONG / 21 FAIL_CLOSED
  G6.  FCX 0000831259-26-000021 → quarter_label == "Q1_FY2026"
       AND safety_action == "AUTO_OK"
       AND source == "prior_periodic_projection_q4_to_q1"
  G7.  Full-corpus shadow: ALL 9,909 GT rows + 34 SEC-audited NR rows
       (default mode; --fast subsamples 100 currently-firing rows).
       AUTO_OK with wrong (fy, q) → WRONG_AUTO_WROTE; HARD-LOCKED at 0.
  G7b. Regression: every row that fired AUTO_OK in Goal 3's live_mode_audit.csv
       (under prior_periodic_projection) must still return AUTO_OK with the
       same (fy, q) under the new resolver. Rule F replaces ONLY the
       odd_52_53_week branch, so currently-firing rows by construction did
       NOT hit that branch and must preserve their AUTO_OK behavior.
       FULL mode HARD-LOCK: 0 changed-OK AND 0 newly-fail-closed.
       Coverage cannot silently shrink. FAST mode (sample-only): lenient
       on fail-closed due to sample bias.
  G8.  pytest passes on test_quarter_identity.py
  G9.  Orchestrator write-guard: actually runs `pytest -k write_guard`,
       requires ≥1 test collected + executed, exits 0
  G10. GOAL4_REPORT.md content (if present)

EXIT CODES:
  0 = pass; Goal 4 implementation verified
  1 = fatal violation
  2 = verifier infra failed
"""
from __future__ import annotations
import argparse
import csv
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parents[2]
QI_PATH = PROJECT_ROOT / "scripts/earnings/quarter_identity.py"
GOAL4_REPORT_PATH = _HERE / "GOAL4_REPORT.md"
GROUND_TRUTH_PATH = _HERE / "ground_truth.csv"
NEEDS_REVIEW_PATH = _HERE / "needs_review.csv"
LIVE_AUDIT_PATH = _HERE / "live_mode_audit.csv"
SEC_AUDIT_JSON = _HERE / "audit_evidence/sec_52_53_audit/all_verdicts.json"

# ── Allowed production paths Codex MAY modify ────────────────────────
ALLOWED_PROD_MODIFICATIONS = {
    "scripts/earnings/quarter_identity.py",
    "scripts/earnings/test_quarter_identity.py",
    # Orchestrator entry — these paths are heuristic; verifier permits any
    # of these to be modified for the write-guard
    "scripts/earnings/earnings_orchestrator.py",
    ".claude/skills/earnings-orchestrator/SKILL.md",
    ".claude/skills/earnings-orchestrator/scripts/earnings_orchestrator.py",
}

# ── Expected source strings from Goal 4 resolver (Goal 3 + Rule F) ───
# Goal 3 sources (preserved from candidate_live_prior_periodic_projection):
GOAL3_PRESERVED_SOURCES = {
    "prior_periodic_projection_no_fye",
    "prior_periodic_projection_bad_filing_time",
    "prior_periodic_projection_no_prior",
    "prior_periodic_projection_denylisted_prior_fail_closed",
    "prior_periodic_projection_bad_prior_context",
    "prior_periodic_projection_future_prior_fail_closed",
    "prior_periodic_projection_long_gap_fail_closed",
    "prior_periodic_projection_fiscal_math_error",
    "prior_periodic_projection_bad_prior_quarter",
}
# Rule F sources (NEW, replace old odd_52_53_week_prior_fail_closed):
RULE_F_SOURCES = {
    "rule_f_direct_recent_prior",
    "rule_f_advance_xbrl",
    "rule_f_fail_closed_recent_no_xbrl",
    "rule_f_fail_closed_missing_signal",
    "rule_f_fail_closed_fy_disagreement",
}
# All sources expected to appear in the production source code:
EXPECTED_SOURCES = GOAL3_PRESERVED_SOURCES | RULE_F_SOURCES

# ── 115 odd_52_53 expected counts ────────────────────────────────────
EXPECTED_115_OK = 94
EXPECTED_115_WRONG = 0
EXPECTED_115_FAIL_CLOSED = 21

REGRESSION_SAMPLE_N = 100
REGRESSION_SEED = 20260506


def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


# ── G1: git-clean ─────────────────────────────────────────────────────
def check_verifier_git_clean() -> None:
    rel = str(Path(__file__).resolve().relative_to(PROJECT_ROOT))
    r = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", rel],
        cwd=str(PROJECT_ROOT), capture_output=True, timeout=30,
    )
    if r.returncode != 0:
        fail(f"Verifier file has uncommitted changes vs HEAD: {rel}", code=2)
    r = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=str(PROJECT_ROOT), capture_output=True, timeout=10,
    )
    if r.returncode != 0:
        fail(f"Verifier file is not git-committed: {rel}", code=2)
    info("G1 verifier git-clean ✓")


# ── G2: production resolver source check ─────────────────────────────

# Banned patterns — Rule F is STRUCTURAL ONLY, no ticker-specific logic
_BANNED_TICKER_PATTERNS = [
    # Hardcoded ticker sets
    re.compile(r"\b(?:ALLOWLIST|DENYLIST|EXTREME_CALENDAR|FIVE_TWO_THREE|"
               r"WEEK_FIFTY_THREE|FY_CONVENTION|TICKER_SPECIAL|ODD_FISCAL)"
               r"[A-Z_]*\s*=", re.IGNORECASE),
    # Inline ticker dispatches like `if ticker in {"AAP","KR"}` or similar
    re.compile(r"if\s+ticker\s+in\s*[\(\{]['\"](?:AAP|PSTG|ACI|KR|NTAP|"
               r"PEP|LEVI|PLAY|SYNA|ESTC|AZO|COST|GIS|DRI)", re.IGNORECASE),
    # Any direct hardcoded ticker comparison
    re.compile(r"ticker\s*==\s*['\"](?:AAP|PSTG|ACI|KR|NTAP|PEP|LEVI|"
               r"PLAY|SYNA|ESTC)['\"]", re.IGNORECASE),
]


def check_resolver_changed() -> None:
    if not QI_PATH.is_file():
        fail(f"G2 production file missing: {QI_PATH}", code=2)
    src = QI_PATH.read_text(encoding="utf-8")

    # (a) old FCX bug constant must be gone
    if re.search(r"_STALE_MATCH_DAYS\s*=\s*150", src):
        fail("G2 old `_STALE_MATCH_DAYS = 150` (FCX bug source) still present "
             "in quarter_identity.py — must be removed")

    # (b) The replaced odd_52_53 fail-closed source from Goal 3 must NOT appear
    # (Rule F replaces it; if present, the substitution didn't happen).
    if "odd_52_53_week_prior_fail_closed" in src:
        fail("G2 the Goal 3 source `odd_52_53_week_prior_fail_closed` is still "
             "present in quarter_identity.py — Rule F was supposed to REPLACE "
             "this branch entirely.")

    # (c) ALL Goal 3 preserved sources + ALL Rule F sources present
    missing_goal3 = [s for s in GOAL3_PRESERVED_SOURCES if s not in src]
    missing_rulef = [s for s in RULE_F_SOURCES if s not in src]
    if missing_goal3:
        fail(f"G2 missing Goal-3-preserved source strings: {sorted(missing_goal3)}\n"
             f"Goal 4 must port Goal 3's _prior_periodic_projection structure "
             f"byte-faithfully (only odd_52_53 branch is replaced).")
    if missing_rulef:
        fail(f"G2 missing Rule F source strings: {sorted(missing_rulef)}\n"
             f"All Rule F code paths must be present.")

    # (d) Effective FYE logic preserved
    if "_effective_fye_month" not in src and "effective_fye" not in src:
        fail("G2 Goal 3's `_effective_fye_month` logic is missing from "
             "quarter_identity.py. The normal calendar-shaped branch must "
             "use effective_fye (derived from prior 10-K), not raw fye_month.")
    if "_effective_fye_from_prior_10k" not in src:
        fail("G2 source augmentation `_effective_fye_from_prior_10k` is "
             "missing. Goal 3 appends this when effective_fye != fye_month.")

    # (c) STRUCTURAL only — no ticker tables/special-cases
    for pat in _BANNED_TICKER_PATTERNS:
        m = pat.search(src)
        if m:
            # Allow the existing accession-based denylist (XBRL_DENY_PERIODIC_ACCESSIONS)
            ctx = src[max(0, m.start()-50):m.end()+50]
            if "XBRL_DENY_PERIODIC_ACCESSIONS" in ctx:
                continue
            fail(f"G2 found banned ticker-specific pattern in quarter_identity.py:\n"
                 f"  pattern: {pat.pattern}\n"
                 f"  match: {m.group(0)!r}\n"
                 f"Rule F MUST be structural only — no ticker allowlists, "
                 f"denylists, FY-convention tables, or per-issuer logic.")
    info(f"G2 resolver modified: all {len(EXPECTED_SOURCES)} Rule F sources present, "
         f"no banned ticker patterns ✓")


# ── G3: scope check ───────────────────────────────────────────────────
def check_scope_of_changes() -> None:
    r = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        fail(f"G3 git diff failed: {r.stderr}", code=2)
    modified = {line for line in r.stdout.splitlines() if line.strip()}

    # Untracked files Codex may have added
    r2 = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
    )
    untracked = {line for line in r2.stdout.splitlines() if line.strip()}

    # All production-domain changes must be in allowed paths OR test files
    prod_changes = {p for p in (modified | untracked)
                    if (p.startswith("scripts/")
                        or p.startswith(".claude/skills/earnings-orchestrator/")
                        or p.startswith(".claude/skills/quarter-identity/"))}

    illegal = prod_changes - ALLOWED_PROD_MODIFICATIONS
    # Allow test fixtures + new test files in test directories
    illegal = {p for p in illegal
               if not (p.endswith("test.py")
                       or "/test_" in p
                       or "/tests/" in p)}
    # Allow the verifier's own corpus files
    if illegal:
        fail(f"G3 illegal production-code changes outside allowed paths: "
             f"{sorted(illegal)}\n"
             f"Allowed: {sorted(ALLOWED_PROD_MODIFICATIONS)}")
    info(f"G3 scope: production changes within allowed paths ✓")


# ── G4: import resolver ───────────────────────────────────────────────
def import_resolver():
    sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))
    sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))
    try:
        from quarter_identity import resolve_quarter_info  # type: ignore
    except Exception as e:
        fail(f"G4 cannot import resolve_quarter_info: {e}", code=2)
    info("G4 resolve_quarter_info imported ✓")
    return resolve_quarter_info


# ── G5: 115 odd_52_53 set produces 94/0/21 ────────────────────────────
def check_115_odd_52_53(resolve_quarter_info) -> None:
    if not LIVE_AUDIT_PATH.is_file():
        fail(f"G5 live_mode_audit.csv missing: {LIVE_AUDIT_PATH}", code=2)
    if not SEC_AUDIT_JSON.is_file():
        fail(f"G5 SEC audit JSON missing: {SEC_AUDIT_JSON}\n"
             "Commit the audit_evidence/sec_52_53_audit/ directory first.",
             code=2)
    if not GROUND_TRUTH_PATH.is_file() or not NEEDS_REVIEW_PATH.is_file():
        fail("G5 corpus files missing", code=2)

    all_corpus = {}
    for p in [GROUND_TRUTH_PATH, NEEDS_REVIEW_PATH]:
        for r in csv.DictReader(open(p, encoding="utf-8")):
            all_corpus[r["accession_8k"]] = r

    sec_audit = {}
    for r in json.load(open(SEC_AUDIT_JSON, encoding="utf-8")):
        sec_audit[r["accession_8k"]] = (r["audited_fy"], r["audited_q"])

    # Identify the 115 odd_52_53 set
    odd = []
    for r in csv.DictReader(open(LIVE_AUDIT_PATH, encoding="utf-8")):
        if (r["candidate_name"] == "prior_periodic_projection"
                and r["candidate_source"]
                == "prior_periodic_projection_odd_52_53_week_prior_fail_closed"):
            odd.append(r)
    if len(odd) != 115:
        fail(f"G5 odd_52_53 set size = {len(odd)}; expected 115. "
             f"Has live_mode_audit.csv changed?")

    # Build oracle
    oracles = {}
    for r in odd:
        a = r["accession_8k"]
        if r["corpus_label"] == "ground_truth":
            cr = all_corpus[a]
            oracles[a] = (cr["fy_xbrl"], cr["q_xbrl"], "GT")
        elif a in sec_audit:
            f, q = sec_audit[a]
            oracles[a] = (f, q, "SEC")

    if len(oracles) != 115:
        fail(f"G5 oracle coverage incomplete: {len(oracles)}/115. "
             f"Some odd_52_53 rows lack GT or SEC oracle.")

    # Run new resolver against each
    n_ok = n_wrong = n_fc = 0
    wrongs = []
    for a in oracles:
        ticker = next(r["ticker"] for r in odd if r["accession_8k"] == a)
        try:
            qi = resolve_quarter_info(ticker, a)
        except Exception as e:
            fail(f"G5 resolver raised on {a}: {type(e).__name__}: {e}", code=2)
        # Parse output
        ql = qi.get("quarter_label") or ""
        sa = qi.get("safety_action") or ""
        if sa != "AUTO_OK" or not ql:
            n_fc += 1
            continue
        # Parse "Q1_FY2026" → ("2026","Q1")
        try:
            q_part, fy_part = ql.split("_FY")
            r_fy, r_q = fy_part, q_part
        except ValueError:
            n_fc += 1
            continue
        oracle_fy, oracle_q, _ = oracles[a]
        if (r_fy, r_q) == (oracle_fy, oracle_q):
            n_ok += 1
        else:
            n_wrong += 1
            if len(wrongs) < 5:
                wrongs.append(f"{ticker}/{a} got=({r_fy},{r_q}) oracle=({oracle_fy},{oracle_q})")

    if (n_ok, n_wrong, n_fc) != (EXPECTED_115_OK, EXPECTED_115_WRONG, EXPECTED_115_FAIL_CLOSED):
        for w in wrongs:
            print(f"  {w}", file=sys.stderr)
        fail(f"G5 115 odd_52_53 set: got OK={n_ok} WRONG={n_wrong} FC={n_fc}; "
             f"expected exactly OK={EXPECTED_115_OK} WRONG={EXPECTED_115_WRONG} "
             f"FC={EXPECTED_115_FAIL_CLOSED} (Rule F deterministic outcome)")
    info(f"G5 115 odd_52_53: {n_ok}/{n_wrong}/{n_fc} OK/WRONG/FC ✓")


# ── G6: FCX regression ────────────────────────────────────────────────
FCX_EXPECTED_SOURCE = "prior_periodic_projection_q4_to_q1"


def check_fcx(resolve_quarter_info) -> None:
    accn = "0000831259-26-000021"
    qi = resolve_quarter_info("FCX", accn)
    ql = qi.get("quarter_label") or ""
    sa = qi.get("safety_action") or ""
    src = qi.get("quarter_identity_source") or ""
    if ql != "Q1_FY2026":
        fail(f"G6 FCX returned quarter_label={ql!r}; expected 'Q1_FY2026' "
             f"(safety_action={sa!r}, source={src!r})")
    if sa != "AUTO_OK":
        fail(f"G6 FCX safety_action={sa!r}; expected 'AUTO_OK'")
    if src != FCX_EXPECTED_SOURCE:
        fail(f"G6 FCX source={src!r}; expected {FCX_EXPECTED_SOURCE!r}. "
             f"FCX is a normal calendar-shaped q4-to-q1 projection case; "
             f"Rule F is only for the odd 52/53-week branch.")
    info(f"G6 FCX 0000831259-26-000021 → Q1_FY2026 / AUTO_OK / {src} ✓")


# ── G7: full-corpus shadow (default) / --fast 100-row sample ─────────
def check_full_corpus_safety(resolve_quarter_info, *, full_mode: bool) -> None:
    """G7: HARD-LOCKED 0 WRONG_AUTO_WROTE.
    Runs new resolver against either ALL GT rows + 34 SEC-audited (full mode)
    or 100 random rows (fast mode).
    AUTO_OK with wrong (fy, q) → WRONG_AUTO_WROTE; must be 0.
    """
    gt_rows = list(csv.DictReader(open(GROUND_TRUTH_PATH, encoding="utf-8")))
    nr_rows = list(csv.DictReader(open(NEEDS_REVIEW_PATH, encoding="utf-8")))
    nr_by_accn = {r["accession_8k"]: r for r in nr_rows}

    sec_audit = {}
    if SEC_AUDIT_JSON.is_file():
        for r in json.load(open(SEC_AUDIT_JSON, encoding="utf-8")):
            sec_audit[r["accession_8k"]] = (r["audited_fy"], r["audited_q"])

    if full_mode:
        oracles = []
        for r in gt_rows:
            oracles.append((r["accession_8k"], r["ticker"],
                            r["fy_xbrl"], r["q_xbrl"], "GT"))
        for accn, (f, q) in sec_audit.items():
            nr = nr_by_accn.get(accn)
            if nr:
                oracles.append((accn, nr["ticker"], f, q, "SEC"))
        info(f"G7 FULL: {len(oracles)} oracles "
             f"({len(gt_rows)} GT + {len(sec_audit)} SEC-audited)")
    else:
        # --fast: 100 random sample
        random.seed(REGRESSION_SEED)
        oracles_full = []
        for r in gt_rows:
            oracles_full.append((r["accession_8k"], r["ticker"],
                                  r["fy_xbrl"], r["q_xbrl"], "GT"))
        oracles = random.sample(oracles_full, min(REGRESSION_SAMPLE_N, len(oracles_full)))
        info(f"G7 FAST: {len(oracles)} sampled GT oracles")

    n_ok = n_wrong = n_fc = 0
    wrongs = []
    n_total = len(oracles)
    for i, (accn, ticker, o_fy, o_q, src_label) in enumerate(oracles):
        try:
            qi = resolve_quarter_info(ticker, accn)
        except Exception as e:
            fail(f"G7 resolver raised on {ticker}/{accn}: "
                 f"{type(e).__name__}: {e}", code=2)
        ql = qi.get("quarter_label") or ""
        sa = qi.get("safety_action") or ""
        if sa != "AUTO_OK" or not ql:
            n_fc += 1
            continue
        try:
            q_part, fy_part = ql.split("_FY")
        except ValueError:
            n_fc += 1
            continue
        if (fy_part, q_part) == (o_fy, o_q):
            n_ok += 1
        else:
            n_wrong += 1
            if len(wrongs) < 10:
                wrongs.append(f"{ticker}/{accn} got=({fy_part},{q_part}) "
                              f"oracle=({o_fy},{o_q}) [{src_label}]")
        if full_mode and (i + 1) % 500 == 0:
            print(f"  G7: {i+1}/{n_total} processed "
                  f"(ok={n_ok}, wrong={n_wrong}, fc={n_fc})", flush=True)

    if n_wrong > 0:
        for w in wrongs:
            print(f"  {w}", file=sys.stderr)
        fail(f"G7 HARD-LOCK FAILED: {n_wrong} WRONG_AUTO_WROTE "
             f"across {n_total} oracles. ZERO is required.")
    mode = "FULL" if full_mode else "FAST"
    info(f"G7 {mode}: {n_ok} OK / {n_wrong} WRONG / {n_fc} FAIL_CLOSED out of "
         f"{n_total} oracle rows ✓ (0 wrong-auto-writes)")


# ── G7b: regression on Goal-3 currently-firing rows ──────────────────
EXPECTED_FIRING_COUNT = 9860  # from Goal 3 prior_periodic_projection candidate


def check_regression(resolve_quarter_info, *, full_mode: bool) -> None:
    """G7b: Rule F replaces ONLY the odd_52_53_week branch — currently-firing
    rows didn't hit that branch, so Rule F MUST preserve all of them.

    FULL mode (canonical): HARD-LOCK
      - Goal-3 firing count == 9,860 (catches corpus drift)
      - every row still returns AUTO_OK with same (fy, q)
      - 0 changed-OK AND 0 newly-fail-closed
    FAST mode (iteration): sample-based, lenient on fail-closed (sample bias).
    """
    firing = [r for r in csv.DictReader(open(LIVE_AUDIT_PATH, encoding="utf-8"))
              if r["candidate_name"] == "prior_periodic_projection"
                 and r["would_fire"] == "true"]

    if full_mode:
        if len(firing) != EXPECTED_FIRING_COUNT:
            fail(f"G7b expected {EXPECTED_FIRING_COUNT} currently-firing rows in "
                 f"live_mode_audit.csv; found {len(firing)}. The corpus may have "
                 f"drifted since Goal 3.")
        sample = firing
    else:
        random.seed(REGRESSION_SEED + 1)
        sample = random.sample(firing, min(REGRESSION_SAMPLE_N, len(firing)))

    info(f"G7b regression: {len(sample)} {'(FULL — strict)' if full_mode else '(FAST — sample)'} "
         f"currently-firing rows")

    n_match = n_changed_ok = n_fail_closed = 0
    changed = []
    fc_examples = []
    for r in sample:
        accn = r["accession_8k"]
        ticker = r["ticker"]
        csv_fy = (r.get("candidate_fy") or "").strip()
        csv_q = (r.get("candidate_q") or "").strip()
        try:
            qi = resolve_quarter_info(ticker, accn)
        except Exception as e:
            fail(f"G7b resolver raised on {accn}: {type(e).__name__}: {e}", code=2)
        sa = qi.get("safety_action") or ""
        ql = qi.get("quarter_label") or ""
        if sa != "AUTO_OK":
            n_fail_closed += 1
            if len(fc_examples) < 8:
                fc_examples.append(f"{ticker}/{accn} was-firing csv=({csv_fy},{csv_q}) "
                                    f"now safety_action={sa!r}")
            continue
        try:
            q_part, fy_part = ql.split("_FY")
        except ValueError:
            n_fail_closed += 1
            if len(fc_examples) < 8:
                fc_examples.append(f"{ticker}/{accn} was-firing csv=({csv_fy},{csv_q}) "
                                    f"now ql={ql!r}")
            continue
        if (fy_part, q_part) == (csv_fy, csv_q):
            n_match += 1
        else:
            n_changed_ok += 1
            if len(changed) < 8:
                changed.append(f"{ticker}/{accn} csv=({csv_fy},{csv_q}) "
                                f"new=({fy_part},{q_part})")

    # HARD-LOCK: changed-OK is a regression in BOTH modes
    if n_changed_ok > 0:
        for c in changed:
            print(f"  {c}", file=sys.stderr)
        fail(f"G7b regression: {n_changed_ok} firing rows now return DIFFERENT "
             f"AUTO_OK answers. Rule F must preserve existing AUTO_OK results.")

    # HARD-LOCK: fail-closed regression is forbidden in FULL mode
    if full_mode and n_fail_closed > 0:
        for ex in fc_examples:
            print(f"  {ex}", file=sys.stderr)
        fail(f"G7b regression (FULL): {n_fail_closed} previously-firing rows now "
             f"fail-closed. Rule F replaces ONLY the odd_52_53 branch; currently-"
             f"firing rows by construction did not hit that branch and must "
             f"preserve their AUTO_OK behavior. Coverage cannot silently shrink.")

    if full_mode:
        info(f"G7b regression FULL: {n_match}/{len(sample)} match, "
             f"0 changed-OK, 0 newly-fail-closed ✓")
    else:
        info(f"G7b regression FAST: {n_match} match / {n_fail_closed} fail-closed "
             f"(sample bias allowed in fast mode) / 0 changed-OK ✓")


# ── G8: pytest ────────────────────────────────────────────────────────
def check_pytest() -> None:
    test_path = PROJECT_ROOT / "scripts/earnings/test_quarter_identity.py"
    if not test_path.is_file():
        fail(f"G8 test file missing: {test_path}")
    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest", "-xvs",
         str(test_path)],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        print(r.stdout[-3000:], file=sys.stderr)
        print(r.stderr[-1000:], file=sys.stderr)
        fail(f"G8 pytest exited {r.returncode}")
    info("G8 pytest passed ✓")


# ── G9: write-guard test (RUNS pytest -k write_guard) ────────────────
def check_write_guard() -> None:
    """Run `pytest -k write_guard` against the entire scripts/earnings/ test
    tree. Require ≥1 test collected AND test exit 0."""
    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest",
         "-v", "-k", "write_guard",
         "--collect-only", "-q",
         str(PROJECT_ROOT / "scripts/earnings/")],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120,
    )
    # Collect-only output: count "<x> tests collected"
    m = re.search(r"(\d+)\s+tests?\s+collected", r.stdout)
    n_collected = int(m.group(1)) if m else 0
    # pytest exit code 5 = no tests collected; 0 = collected something
    if n_collected == 0:
        fail(f"G9 no tests matching '-k write_guard' were collected.\n"
             f"Test must include at least one test with 'write_guard' in its name "
             f"(e.g., `def test_write_guard_refuses_fail_closed`).\n"
             f"pytest stdout tail:\n{r.stdout[-500:]}")

    # Now actually RUN them
    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest",
         "-xvs", "-k", "write_guard",
         str(PROJECT_ROOT / "scripts/earnings/")],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        print(r.stdout[-3000:], file=sys.stderr)
        print(r.stderr[-500:], file=sys.stderr)
        fail(f"G9 write-guard pytest exited {r.returncode} (expected 0)")
    info(f"G9 write-guard: {n_collected} test(s) collected and passed ✓")


# ── G10: report ───────────────────────────────────────────────────────
def check_report_optional() -> None:
    if not GOAL4_REPORT_PATH.is_file():
        info("G10 GOAL4_REPORT.md not present (optional) — skipping content check")
        return
    text = GOAL4_REPORT_PATH.read_text(encoding="utf-8")
    if len(text) < 300:
        fail(f"G10 GOAL4_REPORT.md too short ({len(text)} bytes)")
    required = ["Rule F", "FCX", "WRONG_AUTO_WROTE"]
    missing = [k for k in required if k not in text]
    if missing:
        fail(f"G10 GOAL4_REPORT.md missing keywords: {missing}")
    info(f"G10 GOAL4_REPORT.md: {len(text)} bytes, all keywords present ✓")


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Goal 4 implementation verifier (hand-written; do not modify)."
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Iteration shortcut: G7 runs 100-row sample instead of full GT corpus, "
             "G7b regression samples 100 firing rows. Bare command (no --fast) is "
             "the canonical sign-off and runs all 9,909 GT + all currently-firing rows.",
    )
    args = parser.parse_args()
    full_mode = not args.fast

    mode_label = "FULL (canonical sign-off)" if full_mode else "FAST (iteration only)"
    print(f"=== Goal 4 verifier (hand-written, do not modify) — {mode_label} ===")
    print(f"Production code: {QI_PATH}")
    print(f"Verifier file:   {Path(__file__).resolve()}")
    print()

    check_verifier_git_clean()                            # G1
    check_resolver_changed()                              # G2
    check_scope_of_changes()                              # G3
    resolve_quarter_info = import_resolver()              # G4
    check_115_odd_52_53(resolve_quarter_info)             # G5
    check_fcx(resolve_quarter_info)                       # G6
    check_full_corpus_safety(resolve_quarter_info,        # G7
                              full_mode=full_mode)
    check_regression(resolve_quarter_info,                # G7b
                      full_mode=full_mode)
    check_pytest()                                        # G8
    check_write_guard()                                   # G9
    check_report_optional()                               # G10

    print()
    info("=" * 60)
    if full_mode:
        info("ALL CHECKS PASSED — Goal 4 verified (FULL — canonical sign-off)")
    else:
        info("ALL CHECKS PASSED — Goal 4 verified (FAST — iteration only)")
        info("REMINDER: re-run without --fast for canonical sign-off.")
    info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
