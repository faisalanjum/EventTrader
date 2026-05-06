#!/usr/bin/env python3
"""
verify_goal5_implementation.py — Independent verifier for Goal 5 (close NR
AUTO_OK wrong-write hole via Rule G structural extension to calendar branch).

HAND-WRITTEN BY HUMANS to prevent self-rubber-stamping. Codex must NOT
modify this file; checked via git diff.

CHECKS PERFORMED (default = canonical sign-off; --fast for iteration):
  G1.  Verifier + immutable evidence/input files are git-clean (anti-tampering)
  G2.  scripts/earnings/quarter_identity.py modified — `_STALE_MATCH_DAYS=150`
       still GONE; Goal 4 Rule F odd_52_53 sources preserved verbatim;
       at least one new `rule_g_*` (or equivalent calendar-branch) source
       added; NO ticker allowlist/denylist/FY-table patterns;
       NO EX-99.1 / press-release string parsing patterns
  G3.  No production code modified outside allowed paths
       (quarter_identity.py + test files only; orchestrator NOT changed)
  G4.  resolve_quarter_info importable; signature unchanged
  G5.  FCX 0000831259-26-000021 still → Q1_FY2026 / AUTO_OK (Goal 4 fix)
  G6.  Cleaned NR oracle (731 scoreable rows = 144 ok + 587 wrong):
       — 0 WRONG_AUTO_WROTE on the 587 cleaned-wrong rows  (HARD-LOCK)
       — 144 cleaned-ok rows preserved as AUTO_OK with same (fy, q)  (HARD-LOCK)
       — 107 unclear rows skipped from hard scoring
  G7.  Goal 4 oracle pool (9,909 GT + 34 SEC-audited NR = 9,943 rows):
       — 0 WRONG_AUTO_WROTE  (HARD-LOCK; Goal 4 baseline preserved)
       — Goal 4 proven-OK baseline has exactly 9,116 unique rows, and every
         row remains AUTO_OK with the same (fy, q)
       — `--fast` mode samples 200 GT rows
  G8.  115 odd_52_53 set still produces EXACTLY 94 OK / 0 WRONG / 21 FAIL_CLOSED
       (Rule F preserved)
  G9.  pytest scripts/earnings/test_quarter_identity.py exits 0
  G10. pytest scripts/earnings/test_quarter_identity_u64.py exits 0
       (PIT-safety regression suite — Goal 4 + earlier protections)
  G11. Orchestrator write-guard pytest -k write_guard collects ≥1 + exits 0
       (Goal 4 destructive-write guard preserved)
  G12. audit_evidence/sec_nr_auto_ok_audit/goal5_candidate_audit.csv exists
       with rows for at least A, B, C; chosen candidate is the verifier's
       observed runtime behavior (sanity match)
  G13. GOAL5_REPORT.md (if present) is non-empty + has required keywords
  G14. Cleaned NR fire rate reported (metric only)

EXIT CODES:
  0 = pass; Goal 5 implementation verified
  1 = fatal violation
  2 = verifier infra failed
"""
from __future__ import annotations
import argparse
import csv
import importlib.util  # noqa: F401  (kept for parity with Goal 4)
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
GOAL5_REPORT_PATH = _HERE / "GOAL5_REPORT.md"
GROUND_TRUTH_PATH = _HERE / "ground_truth.csv"
NEEDS_REVIEW_PATH = _HERE / "needs_review.csv"
LIVE_AUDIT_PATH = _HERE / "live_mode_audit.csv"
SEC_5253_AUDIT_JSON = _HERE / "audit_evidence/sec_52_53_audit/all_verdicts.json"
NR_AUDIT_JSON = _HERE / "audit_evidence/sec_nr_auto_ok_audit/cleaned_all_verdicts.json"
NR_AUDIT_DIR = _HERE / "audit_evidence/sec_nr_auto_ok_audit"
CANDIDATE_AUDIT_CSV = _HERE / "audit_evidence/sec_nr_auto_ok_audit/goal5_candidate_audit.csv"
GOAL4_BASELINE_CSV = _HERE / "audit_evidence/goal4_proven_ok_baseline.csv"

# ── Allowed production paths Codex MAY modify ────────────────────────
# Goal 5 is a NARROWER scope than Goal 4: only quarter_identity.py + tests.
# Orchestrator destructive-write guard is preserved verbatim from Goal 4.
ALLOWED_PROD_MODIFICATIONS = {
    "scripts/earnings/quarter_identity.py",
    "scripts/earnings/test_quarter_identity.py",
    "scripts/earnings/test_quarter_identity_u64.py",
}

# ── Goal 4's source strings that MUST still be present (unchanged) ───
GOAL4_PRESERVED_SOURCES = {
    # Goal 3 prelude (preserved through Goal 4)
    "prior_periodic_projection_no_fye",
    "prior_periodic_projection_bad_filing_time",
    "prior_periodic_projection_no_prior",
    "prior_periodic_projection_denylisted_prior_fail_closed",
    "prior_periodic_projection_bad_prior_context",
    "prior_periodic_projection_future_prior_fail_closed",
    "prior_periodic_projection_long_gap_fail_closed",
    "prior_periodic_projection_fiscal_math_error",
    "prior_periodic_projection_bad_prior_quarter",
    # Rule F (odd_52_53 — Goal 4 NEW; must remain)
    "rule_f_direct_recent_prior",
    "rule_f_advance_xbrl",
    "rule_f_fail_closed_recent_no_xbrl",
    "rule_f_fail_closed_missing_signal",
    "rule_f_fail_closed_fy_disagreement",
}

# ── Expected hard-lock numbers ───────────────────────────────────────
EXPECTED_115_OK = 94
EXPECTED_115_WRONG = 0
EXPECTED_115_FAIL_CLOSED = 21
EXPECTED_GOAL4_AUTO_OK_FLOOR = 9116  # Goal 4's G7 OK count on 9,943
EXPECTED_NR_OK_PRESERVE = 144
EXPECTED_NR_WRONG_HARD_GATE = 0
EXPECTED_NR_UNCLEAR_SKIP = 107
EXPECTED_NR_TOTAL = 838

FAST_GT_SAMPLE_N = 200
FAST_SEED = 20260507


def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


# ── G1: git-clean (verifier + immutable evidence inputs) ─────────────
# ALL of these files are oracle/evidence inputs that the verifier reads.
# If Codex could modify any of them, it could bypass the hard gates
# (e.g. delete rows from cleaned_all_verdicts.json to trivially satisfy
# G6's "0 wrong" requirement). They MUST be git-tracked AND clean
# vs HEAD before the verifier runs.
_IMMUTABLE_EVIDENCE_FILES = [
    Path(__file__).resolve(),
    GROUND_TRUTH_PATH,
    NEEDS_REVIEW_PATH,
    LIVE_AUDIT_PATH,
    NR_AUDIT_JSON,
    GOAL4_BASELINE_CSV,
    NR_AUDIT_DIR / "CLEANED_SUMMARY.md",
    NR_AUDIT_DIR / "validation_report.txt",
    SEC_5253_AUDIT_JSON,
]


def check_verifier_git_clean() -> None:
    for path in _IMMUTABLE_EVIDENCE_FILES:
        if not path.is_file():
            fail(f"G1 immutable evidence file missing: {path}", code=2)
        rel = str(path.relative_to(PROJECT_ROOT))
        # must be git-tracked
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=str(PROJECT_ROOT), capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            fail(f"G1 evidence file is not git-committed: {rel}\n"
                 f"All oracle/evidence files must be committed BEFORE Goal 5 runs.",
                 code=2)
        # must be clean vs HEAD (no Codex tampering)
        r = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", rel],
            cwd=str(PROJECT_ROOT), capture_output=True, timeout=30,
        )
        if r.returncode != 0:
            fail(f"G1 evidence file has uncommitted changes vs HEAD: {rel}\n"
                 f"Codex MUST NOT modify oracle/evidence inputs.", code=2)
    info(f"G1 verifier + {len(_IMMUTABLE_EVIDENCE_FILES)-1} evidence files "
         f"git-clean ✓")


# ── G2: production resolver source check ─────────────────────────────

# Banned patterns — Rule G is STRUCTURAL ONLY, no ticker-specific logic
_BANNED_TICKER_PATTERNS = [
    re.compile(r"\b(?:ALLOWLIST|DENYLIST|EXTREME_CALENDAR|FIVE_TWO_THREE|"
               r"WEEK_FIFTY_THREE|FY_CONVENTION|TICKER_SPECIAL|ODD_FISCAL|"
               r"ISSUER_FY_MAP|FY_NAMING_TABLE|RETAIL_FYE)"
               r"[A-Z_]*\s*=", re.IGNORECASE),
    re.compile(r"if\s+ticker\s+in\s*[\(\{]['\"](?:AAP|PSTG|ACI|KR|NTAP|"
               r"PEP|LEVI|PLAY|SYNA|ESTC|AZO|COST|GIS|DRI|ANF|KSS|BJ|BURL|"
               r"CHWY|FIVE|GME|LOW|LULU|OXM|PVH|ROST|ULTA|DKS|DLTR|GRPN|LAND)",
               re.IGNORECASE),
    re.compile(r"ticker\s*==\s*['\"](?:AAP|PSTG|ACI|KR|NTAP|PEP|LEVI|"
               r"PLAY|SYNA|ESTC|ANF|KSS|BJ|BURL|CHWY|FIVE|GME|LOW|LULU|"
               r"OXM|PVH|ROST|ULTA|DKS|DLTR|GRPN|LAND)['\"]", re.IGNORECASE),
]

# Banned EX-99 / press-release / 8-K body parsing in production
_BANNED_TEXT_PARSING_PATTERNS = [
    re.compile(r"['\"]EX-99\.?1?['\"]", re.IGNORECASE),
    re.compile(r"\bex_?99[_-]?1?\b", re.IGNORECASE),
    re.compile(r"['\"](?:Reports?|reports)\s+(?:First|Second|Third|Fourth)\s+Quarter",
               re.IGNORECASE),
    re.compile(r"['\"](?:first|second|third|fourth)\s+quarter\s+of\s+fiscal",
               re.IGNORECASE),
    # press-release fetch primitives
    re.compile(r"\bsec[_-]?api\.io\b", re.IGNORECASE),
    re.compile(r"\bedgar\.sec\.gov", re.IGNORECASE),
    re.compile(r"\brequests\.get\s*\(\s*['\"]https?://", re.IGNORECASE),
    re.compile(r"\burlopen\s*\(\s*['\"]https?://", re.IGNORECASE),
]


def check_resolver_changed() -> None:
    if not QI_PATH.is_file():
        fail(f"G2 production file missing: {QI_PATH}", code=2)
    src = QI_PATH.read_text(encoding="utf-8")

    # (a) old FCX bug constant must STILL be gone (no regression)
    if re.search(r"_STALE_MATCH_DAYS\s*=\s*150", src):
        fail("G2 old `_STALE_MATCH_DAYS = 150` (FCX bug source) reappeared in "
             "quarter_identity.py — Goal 4 removed it; do NOT reintroduce.")

    # (b) Goal 3's odd_52_53 fail-closed must STILL be gone (Goal 4 substitution)
    if "odd_52_53_week_prior_fail_closed" in src:
        fail("G2 Goal 3's `odd_52_53_week_prior_fail_closed` source reappeared "
             "in quarter_identity.py — Goal 4 replaced it with Rule F; do NOT "
             "reintroduce.")

    # (c) ALL Goal 4 sources still present
    missing_g4 = [s for s in GOAL4_PRESERVED_SOURCES if s not in src]
    if missing_g4:
        fail(f"G2 missing Goal-4-preserved source strings: {sorted(missing_g4)}\n"
             f"Goal 5 must preserve Rule F's odd_52_53 branch + Goal 3 prelude "
             f"verbatim.")

    # (d) at least one NEW source string for the Goal 5 calendar-branch logic
    # The chosen candidate must add something to the calendar branch.
    # Acceptable patterns: rule_g_*, calendar_*, prior_periodic_projection_recent_*,
    # prior_periodic_projection_fy_disagreement_*, etc.
    new_source_patterns = [
        re.compile(r"['\"](rule_g_[a-z0-9_]+)['\"]"),
        re.compile(r"['\"](rule_g_strict_[a-z0-9_]+)['\"]"),
        re.compile(r"['\"](prior_periodic_projection_recent_[a-z0-9_]+)['\"]"),
        re.compile(r"['\"](prior_periodic_projection_calendar_recent_[a-z0-9_]+)['\"]"),
        re.compile(r"['\"](prior_periodic_projection_fy_disagreement_[a-z0-9_]+)['\"]"),
    ]
    new_sources_found = set()
    for pat in new_source_patterns:
        for m in pat.finditer(src):
            new_sources_found.add(m.group(1))
    if not new_sources_found:
        fail("G2 no new Goal-5 source strings found in quarter_identity.py.\n"
             "Expected at least one of: rule_g_*, rule_g_strict_*, "
             "prior_periodic_projection_recent_*, "
             "prior_periodic_projection_calendar_recent_*, "
             "prior_periodic_projection_fy_disagreement_*.\n"
             "Goal 5 must add at least one calendar-branch guard that produces "
             "a distinct source string.")

    # (e) Effective FYE logic preserved
    if "_effective_fye_month" not in src and "effective_fye" not in src:
        fail("G2 `_effective_fye_month` / effective_fye logic missing from "
             "quarter_identity.py.")
    if "_effective_fye_from_prior_10k" not in src:
        fail("G2 source augmentation `_effective_fye_from_prior_10k` removed.")

    # (f) STRUCTURAL only — no ticker tables/special-cases
    for pat in _BANNED_TICKER_PATTERNS:
        m = pat.search(src)
        if m:
            ctx = src[max(0, m.start()-50):m.end()+50]
            if "XBRL_DENY_PERIODIC_ACCESSIONS" in ctx:
                continue
            fail(f"G2 found banned ticker-specific pattern in quarter_identity.py:\n"
                 f"  pattern: {pat.pattern}\n"
                 f"  match: {m.group(0)!r}\n"
                 f"Rule G MUST be structural only — no ticker allowlists, "
                 f"denylists, FY-convention tables, or per-issuer logic.")

    # (g) NO EX-99.1 / press-release / network calls in production
    for pat in _BANNED_TEXT_PARSING_PATTERNS:
        m = pat.search(src)
        if m:
            fail(f"G2 found banned EX-99.1 / press-release / network-call "
                 f"pattern in quarter_identity.py:\n"
                 f"  pattern: {pat.pattern}\n"
                 f"  match: {m.group(0)!r}\n"
                 f"D8 lock: production code MUST NOT parse press releases or "
                 f"call external SEC/EDGAR endpoints. Audits MAY use them as "
                 f"oracle; production MUST NOT.")

    info(f"G2 resolver: Goal 4 sources preserved, "
         f"new Goal 5 sources found: {sorted(new_sources_found)} ✓")


# ── G3: scope check ───────────────────────────────────────────────────
def check_scope_of_changes() -> None:
    r = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        fail(f"G3 git diff failed: {r.stderr}", code=2)
    modified = {line for line in r.stdout.splitlines() if line.strip()}

    r2 = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
    )
    untracked = {line for line in r2.stdout.splitlines() if line.strip()}

    # All scripts/ changes must be in allowed paths OR test files
    prod_changes = {p for p in (modified | untracked)
                    if (p.startswith("scripts/")
                        or p.startswith(".claude/skills/earnings-orchestrator/")
                        or p.startswith(".claude/skills/quarter-identity/"))}

    illegal = prod_changes - ALLOWED_PROD_MODIFICATIONS
    illegal = {p for p in illegal
               if not (p.endswith("test.py")
                       or "/test_" in p
                       or "/tests/" in p)}
    if illegal:
        fail(f"G3 illegal production-code changes outside allowed paths: "
             f"{sorted(illegal)}\n"
             f"Allowed: {sorted(ALLOWED_PROD_MODIFICATIONS)}\n"
             f"Goal 5 may modify ONLY quarter_identity.py + tests. "
             f"Orchestrator destructive-write guard is preserved verbatim.")
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


# ── G5: FCX preserved ─────────────────────────────────────────────────
def check_fcx_preserved(resolve_quarter_info) -> None:
    accn = "0000831259-26-000021"
    qi = resolve_quarter_info("FCX", accn)
    ql = qi.get("quarter_label") or ""
    sa = qi.get("safety_action") or ""
    if ql != "Q1_FY2026":
        fail(f"G5 FCX returned quarter_label={ql!r}; expected 'Q1_FY2026' "
             f"(safety_action={sa!r}). Goal 4 fix lost.")
    if sa != "AUTO_OK":
        fail(f"G5 FCX safety_action={sa!r}; expected 'AUTO_OK'. Goal 4 fix lost.")
    info(f"G5 FCX 0000831259-26-000021 → Q1_FY2026 / AUTO_OK ✓")


# ── G6: cleaned NR oracle hard-lock ──────────────────────────────────
def parse_label(quarter_label: str):
    """Returns (fy, q) or (None, None) if not parseable."""
    if not quarter_label:
        return (None, None)
    try:
        q_part, fy_part = quarter_label.split("_FY")
        return (fy_part, q_part)
    except ValueError:
        return (None, None)


def check_cleaned_nr_oracle(resolve_quarter_info) -> tuple:
    """G6: 587 cleaned-wrong rows MUST NOT WRONG_AUTO_WROTE; 144 cleaned-ok rows
    MUST remain AUTO_OK with same (fy, q). 107 unclear skipped.
    Returns (correct_auto_ok_count, observed_per_row_dict).
    observed_per_row_dict: {accession_8k: ('AUTO_OK'|'FAIL_CLOSED', fy, q)}
    for each cleaned-NR scoreable row (used by G12 to cross-check the
    chosen candidate's per-row CSV)."""
    if not NR_AUDIT_JSON.is_file():
        fail(f"G6 cleaned NR audit JSON missing: {NR_AUDIT_JSON}\n"
             "Commit audit_evidence/sec_nr_auto_ok_audit/cleaned_all_verdicts.json first.",
             code=2)

    rows = json.load(open(NR_AUDIT_JSON, encoding="utf-8"))
    if not isinstance(rows, list):
        fail(f"G6 cleaned NR audit must be a JSON list; got {type(rows).__name__}",
             code=2)
    if len(rows) != EXPECTED_NR_TOTAL:
        fail(f"G6 cleaned NR audit row count = {len(rows)}; "
             f"expected {EXPECTED_NR_TOTAL}.")

    by_verdict = {"ok": [], "wrong": [], "unclear": []}
    for r in rows:
        v = r.get("final_verdict")
        if v not in by_verdict:
            fail(f"G6 unexpected final_verdict={v!r} in cleaned NR audit "
                 f"(accession={r.get('accession_8k')}); expected one of "
                 f"ok/wrong/unclear.", code=2)
        by_verdict[v].append(r)

    if len(by_verdict["ok"]) != EXPECTED_NR_OK_PRESERVE:
        fail(f"G6 cleaned NR ok count = {len(by_verdict['ok'])}; "
             f"expected {EXPECTED_NR_OK_PRESERVE}.")
    if len(by_verdict["unclear"]) != EXPECTED_NR_UNCLEAR_SKIP:
        fail(f"G6 cleaned NR unclear count = {len(by_verdict['unclear'])}; "
             f"expected {EXPECTED_NR_UNCLEAR_SKIP}.")
    expected_wrong = EXPECTED_NR_TOTAL - EXPECTED_NR_OK_PRESERVE - EXPECTED_NR_UNCLEAR_SKIP
    if len(by_verdict["wrong"]) != expected_wrong:
        fail(f"G6 cleaned NR wrong count = {len(by_verdict['wrong'])}; "
             f"expected {expected_wrong}.")

    info(f"G6 cleaned NR oracle: {len(by_verdict['ok'])} ok / "
         f"{len(by_verdict['wrong'])} wrong / "
         f"{len(by_verdict['unclear'])} unclear")

    # observed_per_row records every scoreable row's runtime outcome for G12
    observed_per_row: dict = {}

    def _run_and_record(r):
        accn = r["accession_8k"]
        ticker = r["ticker"]
        try:
            qi = resolve_quarter_info(ticker, accn)
        except Exception as e:
            fail(f"G6 resolver raised on {ticker}/{accn}: "
                 f"{type(e).__name__}: {e}", code=2)
        ql = qi.get("quarter_label") or ""
        sa = qi.get("safety_action") or ""
        if sa != "AUTO_OK" or not ql:
            observed_per_row[accn] = ("FAIL_CLOSED", "", "")
            return None  # FAIL_CLOSED
        rfy, rq = parse_label(ql)
        if rfy is None:
            observed_per_row[accn] = ("FAIL_CLOSED", "", "")
            return None
        observed_per_row[accn] = ("AUTO_OK", rfy, rq)
        return (rfy, rq)

    # ── 587 cleaned-WRONG rows: 0 WRONG_AUTO_WROTE hard-lock ─────────
    n_still_wrong = 0
    n_wrong_now_fc = 0
    n_wrong_now_correct = 0  # candidate happened to fire AUTO_OK with cleaned truth
    wrong_violations = []
    for r in by_verdict["wrong"]:
        truth_fy = str(r["cleaned_audited_fy"])
        truth_q = str(r["cleaned_audited_q"])
        rv = _run_and_record(r)
        if rv is None:
            n_wrong_now_fc += 1
            continue
        rfy, rq = rv
        if (rfy, rq) == (truth_fy, truth_q):
            # Lucky hit: candidate produced the cleaned truth instead of the
            # Goal 4 wrong. That counts as OK (not WRONG).
            n_wrong_now_correct += 1
            continue
        n_still_wrong += 1
        if len(wrong_violations) < 10:
            wrong_violations.append(
                f"{r['ticker']}/{r['accession_8k']} got AUTO_OK ({rfy},{rq}) "
                f"but cleaned truth is ({truth_fy},{truth_q})"
            )

    if n_still_wrong > 0:
        for w in wrong_violations:
            print(f"  {w}", file=sys.stderr)
        fail(f"G6 HARD-LOCK FAILED: {n_still_wrong} cleaned-wrong rows still "
             f"WRONG_AUTO_WROTE. Required: 0. (FC={n_wrong_now_fc}, "
             f"correct-hits={n_wrong_now_correct})")

    # ── 144 cleaned-OK rows: each MUST remain AUTO_OK with same (fy, q) ──
    n_ok_preserved = 0
    n_ok_lost_to_fc = 0
    n_ok_changed_label = 0
    ok_violations = []
    for r in by_verdict["ok"]:
        truth_fy = str(r["cleaned_audited_fy"])
        truth_q = str(r["cleaned_audited_q"])
        rv = _run_and_record(r)
        if rv is None:
            n_ok_lost_to_fc += 1
            if len(ok_violations) < 10:
                ok_violations.append(
                    f"{r['ticker']}/{r['accession_8k']} cleaned=OK "
                    f"({truth_fy},{truth_q}) now FAIL_CLOSED"
                )
            continue
        rfy, rq = rv
        if (rfy, rq) == (truth_fy, truth_q):
            n_ok_preserved += 1
        else:
            n_ok_changed_label += 1
            if len(ok_violations) < 10:
                ok_violations.append(
                    f"{r['ticker']}/{r['accession_8k']} cleaned=OK "
                    f"({truth_fy},{truth_q}) now AUTO_OK ({rfy},{rq})"
                )

    if n_ok_preserved != EXPECTED_NR_OK_PRESERVE:
        for v in ok_violations:
            print(f"  {v}", file=sys.stderr)
        fail(f"G6 HARD-LOCK FAILED: cleaned-ok preservation = "
             f"{n_ok_preserved}/{EXPECTED_NR_OK_PRESERVE}. "
             f"Lost to fail-close: {n_ok_lost_to_fc}; "
             f"label changed: {n_ok_changed_label}.")

    # ── NR fire rate metric ──
    correct_auto_ok = n_ok_preserved + n_wrong_now_correct
    fail_closed_total = n_ok_lost_to_fc + n_wrong_now_fc
    scoreable = EXPECTED_NR_OK_PRESERVE + (EXPECTED_NR_TOTAL - EXPECTED_NR_OK_PRESERVE - EXPECTED_NR_UNCLEAR_SKIP)
    nr_fire_rate = 100.0 * correct_auto_ok / scoreable

    info(f"G6 cleaned-NR HARD-LOCKS PASSED: "
         f"587 wrong → 0 still-wrong / {n_wrong_now_fc} fail-closed / "
         f"{n_wrong_now_correct} now-correct; "
         f"144 ok → {n_ok_preserved} preserved ✓")
    info(f"G14 cleaned-NR fire rate (correct_AUTO_OK / scoreable {scoreable}): "
         f"{nr_fire_rate:.2f}% "
         f"(correct={correct_auto_ok}, fail-closed={fail_closed_total})")
    return correct_auto_ok, observed_per_row


# ── G7: Goal 4 proven-OK baseline preserved (per-row HARD-LOCK) ─────
def check_goal4_oracle_preserved(resolve_quarter_info, *, full_mode: bool) -> None:
    """G7: every row in goal4_proven_ok_baseline.csv MUST return AUTO_OK with
    the same (fy, q) under the new resolver.

    Plus full-corpus 0-WRONG hard-lock on the 9,943 oracle pool (Goal 4's G7).

    The baseline file enumerates the 9,116 specific (accession, ticker, fy, q)
    tuples that Goal 4 returned AUTO_OK with the matching oracle. This catches
    the silent regression where a candidate fail-closes some proven-OK rows
    and compensates by newly correcting others (an aggregate-count check
    cannot detect this).

    --fast mode: samples 200 baseline rows + 200 GT-oracle rows for the
    0-WRONG check.
    """
    if not GOAL4_BASELINE_CSV.is_file():
        fail(f"G7 Goal 4 proven-OK baseline missing: {GOAL4_BASELINE_CSV}\n"
             f"Run audit_evidence/sec_nr_auto_ok_audit/compute_goal4_baseline.py "
             f"to produce this file before Goal 5 begins.", code=2)
    baseline = list(csv.DictReader(open(GOAL4_BASELINE_CSV, encoding="utf-8")))
    if not baseline:
        fail(f"G7 baseline CSV is empty: {GOAL4_BASELINE_CSV}", code=2)
    required_cols = {"accession_8k", "ticker", "fy", "q"}
    missing_cols = required_cols - set(baseline[0].keys())
    if missing_cols:
        fail(f"G7 baseline CSV missing columns: {sorted(missing_cols)}", code=2)

    # Hard-lock: baseline must be EXACTLY 9,116 rows (re-derived empirically
    # from running Goal 4's resolver against the 9,943 oracle pool).
    if len(baseline) != EXPECTED_GOAL4_AUTO_OK_FLOOR:
        fail(f"G7 baseline CSV row count = {len(baseline)}; "
             f"expected exactly {EXPECTED_GOAL4_AUTO_OK_FLOOR}. "
             f"Re-run compute_goal4_baseline.py if Goal 4's behavior changed; "
             f"otherwise the baseline file may have been tampered.", code=2)
    # Hard-lock: every accession in baseline must be unique.
    accns = [r["accession_8k"] for r in baseline]
    if len(set(accns)) != len(accns):
        # Find first duplicate for the error message
        seen = set()
        dup = next((a for a in accns if a in seen or seen.add(a)), None)
        fail(f"G7 baseline CSV contains duplicate accessions "
             f"(e.g. {dup!r}); each row must be unique.", code=2)

    info(f"G7 baseline CSV: {len(baseline)} unique proven-OK rows "
         f"(== expected {EXPECTED_GOAL4_AUTO_OK_FLOOR}) ✓")

    # ── Part (a): per-row baseline preservation ──
    if full_mode:
        sample = baseline
    else:
        random.seed(FAST_SEED)
        sample = random.sample(baseline, min(FAST_GT_SAMPLE_N, len(baseline)))
        info(f"G7 FAST: sampling {len(sample)} of {len(baseline)} baseline rows")

    n_preserved = n_lost_to_fc = n_changed_label = 0
    violations = []
    for i, row in enumerate(sample):
        accn = row["accession_8k"]
        ticker = row["ticker"]
        o_fy = row["fy"]
        o_q = row["q"]
        try:
            qi = resolve_quarter_info(ticker, accn)
        except Exception as e:
            fail(f"G7 resolver raised on baseline {ticker}/{accn}: "
                 f"{type(e).__name__}: {e}", code=2)
        ql = qi.get("quarter_label") or ""
        sa = qi.get("safety_action") or ""
        if sa != "AUTO_OK" or not ql:
            n_lost_to_fc += 1
            if len(violations) < 10:
                violations.append(
                    f"{ticker}/{accn} baseline=({o_fy},{o_q}) "
                    f"now safety_action={sa!r} ql={ql!r}"
                )
            continue
        rfy, rq = parse_label(ql)
        if (rfy, rq) == (o_fy, o_q):
            n_preserved += 1
        else:
            n_changed_label += 1
            if len(violations) < 10:
                violations.append(
                    f"{ticker}/{accn} baseline=({o_fy},{o_q}) "
                    f"now AUTO_OK ({rfy},{rq})"
                )
        if full_mode and (i + 1) % 1000 == 0:
            print(f"  G7 baseline: {i+1}/{len(sample)} "
                  f"(preserved={n_preserved}, lost={n_lost_to_fc + n_changed_label})",
                  flush=True)

    if n_lost_to_fc > 0 or n_changed_label > 0:
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        fail(f"G7 HARD-LOCK FAILED: {n_lost_to_fc + n_changed_label} of "
             f"{len(sample)} Goal 4 proven-OK baseline rows regressed "
             f"(lost-to-fc={n_lost_to_fc}, label-changed={n_changed_label}). "
             f"ZERO regressions required.")

    info(f"G7 baseline preservation ({'FULL' if full_mode else 'FAST'}): "
         f"{n_preserved}/{len(sample)} preserved, 0 regressions ✓")

    # ── Part (b): full 9,943 oracle pool — 0 WRONG hard-lock (Goal 4's G7) ──
    gt_rows = list(csv.DictReader(open(GROUND_TRUTH_PATH, encoding="utf-8")))
    nr_rows = list(csv.DictReader(open(NEEDS_REVIEW_PATH, encoding="utf-8")))
    nr_by_accn = {r["accession_8k"]: r for r in nr_rows}

    if not SEC_5253_AUDIT_JSON.is_file():
        fail(f"G7 SEC 52/53 audit JSON missing: {SEC_5253_AUDIT_JSON}", code=2)
    sec_data = json.load(open(SEC_5253_AUDIT_JSON, encoding="utf-8"))
    sec_audit = {r["accession_8k"]: (r["audited_fy"], r["audited_q"])
                 for r in sec_data}

    if full_mode:
        oracles = []
        for r in gt_rows:
            oracles.append((r["accession_8k"], r["ticker"],
                            r["fy_xbrl"], r["q_xbrl"], "GT"))
        for accn, (f, q) in sec_audit.items():
            nr = nr_by_accn.get(accn)
            if nr:
                oracles.append((accn, nr["ticker"], f, q, "SEC"))
    else:
        random.seed(FAST_SEED + 1)
        gt_oracles = [(r["accession_8k"], r["ticker"],
                        r["fy_xbrl"], r["q_xbrl"], "GT")
                       for r in gt_rows]
        oracles = random.sample(gt_oracles, min(FAST_GT_SAMPLE_N, len(gt_oracles)))

    n_ok = n_wrong = n_fc = 0
    wrongs = []
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
        rfy, rq = parse_label(ql)
        if rfy is None:
            n_fc += 1
            continue
        if (rfy, rq) == (o_fy, o_q):
            n_ok += 1
        else:
            n_wrong += 1
            if len(wrongs) < 10:
                wrongs.append(f"{ticker}/{accn} got=({rfy},{rq}) "
                              f"oracle=({o_fy},{o_q}) [{src_label}]")
        if full_mode and (i + 1) % 1000 == 0:
            print(f"  G7 oracle: {i+1}/{len(oracles)} "
                  f"(ok={n_ok}, wrong={n_wrong}, fc={n_fc})", flush=True)

    if n_wrong > 0:
        for w in wrongs:
            print(f"  {w}", file=sys.stderr)
        fail(f"G7 HARD-LOCK FAILED: {n_wrong} WRONG_AUTO_WROTE on Goal 4 oracle "
             f"pool ({len(oracles)} rows). ZERO required. Goal 4 baseline broken.")

    info(f"G7 oracle-pool 0-WRONG ({'FULL' if full_mode else 'FAST'}): "
         f"{n_ok}/{n_wrong}/{n_fc} OK/WRONG/FC on {len(oracles)} rows ✓")


# ── G8: 115 odd_52_53 produces 94/0/21 (Rule F preserved) ────────────
def check_115_odd_52_53(resolve_quarter_info) -> None:
    if not LIVE_AUDIT_PATH.is_file():
        fail(f"G8 live_mode_audit.csv missing: {LIVE_AUDIT_PATH}", code=2)
    if not SEC_5253_AUDIT_JSON.is_file():
        fail(f"G8 SEC 52/53 audit JSON missing: {SEC_5253_AUDIT_JSON}", code=2)
    if not GROUND_TRUTH_PATH.is_file() or not NEEDS_REVIEW_PATH.is_file():
        fail("G8 corpus files missing", code=2)

    all_corpus = {}
    for p in [GROUND_TRUTH_PATH, NEEDS_REVIEW_PATH]:
        for r in csv.DictReader(open(p, encoding="utf-8")):
            all_corpus[r["accession_8k"]] = r

    sec_audit = {}
    for r in json.load(open(SEC_5253_AUDIT_JSON, encoding="utf-8")):
        sec_audit[r["accession_8k"]] = (r["audited_fy"], r["audited_q"])

    odd = []
    for r in csv.DictReader(open(LIVE_AUDIT_PATH, encoding="utf-8")):
        if (r["candidate_name"] == "prior_periodic_projection"
                and r["candidate_source"]
                == "prior_periodic_projection_odd_52_53_week_prior_fail_closed"):
            odd.append(r)
    if len(odd) != 115:
        fail(f"G8 odd_52_53 set size = {len(odd)}; expected 115. "
             f"Has live_mode_audit.csv changed?")

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
        fail(f"G8 oracle coverage incomplete: {len(oracles)}/115.")

    n_ok = n_wrong = n_fc = 0
    wrongs = []
    for a in oracles:
        ticker = next(r["ticker"] for r in odd if r["accession_8k"] == a)
        try:
            qi = resolve_quarter_info(ticker, a)
        except Exception as e:
            fail(f"G8 resolver raised on {a}: {type(e).__name__}: {e}", code=2)
        ql = qi.get("quarter_label") or ""
        sa = qi.get("safety_action") or ""
        if sa != "AUTO_OK" or not ql:
            n_fc += 1
            continue
        rfy, rq = parse_label(ql)
        if rfy is None:
            n_fc += 1
            continue
        oracle_fy, oracle_q, _ = oracles[a]
        if (rfy, rq) == (oracle_fy, oracle_q):
            n_ok += 1
        else:
            n_wrong += 1
            if len(wrongs) < 5:
                wrongs.append(f"{ticker}/{a} got=({rfy},{rq}) "
                              f"oracle=({oracle_fy},{oracle_q})")

    if (n_ok, n_wrong, n_fc) != (EXPECTED_115_OK, EXPECTED_115_WRONG, EXPECTED_115_FAIL_CLOSED):
        for w in wrongs:
            print(f"  {w}", file=sys.stderr)
        fail(f"G8 115 odd_52_53 set: got OK={n_ok} WRONG={n_wrong} FC={n_fc}; "
             f"expected exactly OK={EXPECTED_115_OK} WRONG={EXPECTED_115_WRONG} "
             f"FC={EXPECTED_115_FAIL_CLOSED} (Rule F deterministic outcome). "
             f"Goal 5 must NOT modify Rule F's odd_52_53 branch.")
    info(f"G8 115 odd_52_53: {n_ok}/{n_wrong}/{n_fc} OK/WRONG/FC "
         f"(Rule F preserved) ✓")


# ── G9: pytest test_quarter_identity.py ──────────────────────────────
def check_pytest() -> None:
    test_path = PROJECT_ROOT / "scripts/earnings/test_quarter_identity.py"
    if not test_path.is_file():
        fail(f"G9 test file missing: {test_path}")
    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest", "-xvs",
         str(test_path)],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        print(r.stdout[-3000:], file=sys.stderr)
        print(r.stderr[-1000:], file=sys.stderr)
        fail(f"G9 pytest exited {r.returncode}")
    info("G9 pytest test_quarter_identity.py passed ✓")


# ── G10: pytest test_quarter_identity_u64.py (PIT-safety regression) ─
def check_pytest_u64() -> None:
    test_path = PROJECT_ROOT / "scripts/earnings/test_quarter_identity_u64.py"
    if not test_path.is_file():
        fail(f"G10 PIT-safety test file missing: {test_path}")
    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest", "-xvs",
         str(test_path)],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        print(r.stdout[-3000:], file=sys.stderr)
        print(r.stderr[-1000:], file=sys.stderr)
        fail(f"G10 pytest test_quarter_identity_u64.py exited {r.returncode}")
    info("G10 PIT-safety regression suite passed ✓")


# ── G11: write-guard preserved ────────────────────────────────────────
def check_write_guard() -> None:
    """Run `pytest -k write_guard` against scripts/earnings/. Goal 4's
    destructive-write guard tests must still collect AND pass."""
    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest",
         "-v", "-k", "write_guard",
         "--collect-only", "-q",
         str(PROJECT_ROOT / "scripts/earnings/")],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120,
    )
    m = re.search(r"(\d+)\s+tests?\s+collected", r.stdout)
    n_collected = int(m.group(1)) if m else 0
    if n_collected == 0:
        fail(f"G11 no tests matching '-k write_guard' were collected.\n"
             f"Goal 4's destructive-write guard tests must still exist. "
             f"pytest stdout tail:\n{r.stdout[-500:]}")

    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest",
         "-xvs", "-k", "write_guard",
         str(PROJECT_ROOT / "scripts/earnings/")],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        print(r.stdout[-3000:], file=sys.stderr)
        print(r.stderr[-500:], file=sys.stderr)
        fail(f"G11 write-guard pytest exited {r.returncode} (expected 0)")
    info(f"G11 write-guard preserved: {n_collected} test(s) passed ✓")


# ── G12: candidate matrix integrity (independent recompute) ──────────
def _recompute_candidate_aggregates(per_row_path: Path,
                                    truth_by_accn: dict) -> tuple:
    """Read a per-row candidate CSV, join with cleaned NR truth, return
    (ok, wrong, fail_closed, total_seen, errors)."""
    if not per_row_path.is_file():
        return None
    n_ok = n_wrong = n_fc = 0
    errors = []
    seen = set()
    for r in csv.DictReader(open(per_row_path, encoding="utf-8")):
        accn = r.get("accession_8k", "").strip()
        truth = truth_by_accn.get(accn)
        if not truth:
            errors.append(f"  per-row row {accn!r} not in cleaned-NR scoreable set")
            continue
        if accn in seen:
            errors.append(f"  per-row row {accn!r} appears more than once")
            continue
        seen.add(accn)
        outcome = (r.get("candidate_outcome") or "").strip().upper()
        cfy = (r.get("candidate_fy") or "").strip()
        cq = (r.get("candidate_q") or "").strip()
        truth_fy = str(truth["cleaned_audited_fy"])
        truth_q = str(truth["cleaned_audited_q"])
        if outcome == "FAIL_CLOSED":
            n_fc += 1
        elif outcome == "AUTO_OK":
            if (cfy, cq) == (truth_fy, truth_q):
                n_ok += 1
            else:
                n_wrong += 1
        else:
            errors.append(f"  {accn} unknown candidate_outcome={outcome!r}")
    return n_ok, n_wrong, n_fc, len(seen), errors


def check_candidate_audit_csv(resolve_quarter_info,
                              observed_fire_count: int,
                              observed_per_row: dict) -> None:
    """G12: aggregate CSV + per-row CSVs must agree (recomputed independently);
    chosen candidate's per-row CSV must agree with runtime resolver behavior.

    observed_per_row: dict {accession_8k: ('AUTO_OK'|'FAIL_CLOSED', fy, q)}
        for each cleaned-NR scoreable row, computed by G6 from runtime resolver.
    """
    if not CANDIDATE_AUDIT_CSV.is_file():
        fail(f"G12 candidate audit CSV missing: {CANDIDATE_AUDIT_CSV}")

    rows = list(csv.DictReader(open(CANDIDATE_AUDIT_CSV, encoding="utf-8")))
    required_cols = {"candidate", "ok_count", "wrong_count",
                     "fail_closed_count", "fire_rate_pct",
                     "source_strings_added", "lines_added_vs_goal4", "notes"}
    if rows:
        missing_cols = required_cols - set(rows[0].keys())
        if missing_cols:
            fail(f"G12 aggregate CSV missing required columns: {sorted(missing_cols)}")

    candidates_present = {r["candidate"].strip().upper() for r in rows}
    required_candidates = {"A", "B", "C"}
    missing = required_candidates - candidates_present
    if missing:
        fail(f"G12 aggregate CSV missing required candidates: {sorted(missing)}.")

    # Build cleaned-NR truth lookup over scoreable rows (ok ∪ wrong)
    nr = json.load(open(NR_AUDIT_JSON, encoding="utf-8"))
    truth_by_accn = {r["accession_8k"]: r for r in nr
                     if r["final_verdict"] in ("ok", "wrong")}
    expected_total = len(truth_by_accn)
    if expected_total != EXPECTED_NR_OK_PRESERVE + (
            EXPECTED_NR_TOTAL - EXPECTED_NR_OK_PRESERVE - EXPECTED_NR_UNCLEAR_SKIP):
        fail(f"G12 expected {EXPECTED_NR_OK_PRESERVE + (EXPECTED_NR_TOTAL - EXPECTED_NR_OK_PRESERVE - EXPECTED_NR_UNCLEAR_SKIP)} "
             f"scoreable cleaned-NR rows; got {expected_total}", code=2)

    # ── Recompute aggregates for every reported candidate ──
    discrepancies = []
    for r in rows:
        cand = r["candidate"].strip().upper()
        per_row_path = NR_AUDIT_DIR / f"goal5_candidate_{cand}_per_row.csv"
        result = _recompute_candidate_aggregates(per_row_path, truth_by_accn)
        if result is None:
            fail(f"G12 per-row CSV missing for candidate {cand}: {per_row_path}")
        rok, rwrong, rfc, rseen, errs = result
        if errs:
            for e in errs[:5]:
                print(e, file=sys.stderr)
            fail(f"G12 per-row CSV for candidate {cand} has errors "
                 f"({len(errs)} issues; see above).")
        if rseen != expected_total:
            fail(f"G12 per-row CSV for candidate {cand} covers {rseen} rows; "
                 f"expected {expected_total} (every cleaned-NR scoreable row).")
        # Compare reported aggregate vs recomputed — EXACT match required.
        # Per-row outputs are deterministic; any divergence indicates either
        # a stale aggregate CSV or self-reporting tampering.
        try:
            r_ok = int(r["ok_count"])
            r_wrong = int(r["wrong_count"])
            r_fc = int(r["fail_closed_count"])
        except (ValueError, KeyError):
            fail(f"G12 candidate {cand} has invalid integer fields in aggregate CSV")
        if (r_ok, r_wrong, r_fc) != (rok, rwrong, rfc):
            discrepancies.append(
                f"  {cand}: reported(ok={r_ok}, wrong={r_wrong}, fc={r_fc}) "
                f"vs recomputed(ok={rok}, wrong={rwrong}, fc={rfc})"
            )
    if discrepancies:
        for d in discrepancies:
            print(d, file=sys.stderr)
        fail(f"G12 aggregate CSV does NOT exactly match per-row recompute "
             f"on {len(discrepancies)} candidate(s). Per-row outputs are "
             f"deterministic; aggregates must match exactly.")

    # ── Identify chosen candidate ──
    chosen_rows = [r for r in rows
                   if any(k in (r.get("notes") or "").lower()
                          for k in ("chosen", "winner", "selected", "implemented"))]
    if not chosen_rows:
        fail("G12 no candidate marked chosen/winner/selected/implemented in notes.")
    if len(chosen_rows) > 1:
        fail(f"G12 multiple chosen candidates: "
             f"{[r['candidate'] for r in chosen_rows]}.")
    chosen = chosen_rows[0]
    chosen_letter = chosen["candidate"].strip().upper()

    # ── Hard-gate: chosen has 0 wrong (verified by recompute above) ──
    chosen_wrong = int(chosen["wrong_count"])
    if chosen_wrong != 0:
        fail(f"G12 chosen candidate {chosen_letter} has wrong_count={chosen_wrong}; "
             f"selection rule requires 0 wrong.")
    chosen_ok = int(chosen["ok_count"])

    # ── Selection rule: chosen has max fire among 0-wrong candidates ──
    zero_wrong_oks = []
    for r in rows:
        try:
            if int(r["wrong_count"]) == 0:
                zero_wrong_oks.append(int(r["ok_count"]))
        except (ValueError, KeyError):
            continue
    if zero_wrong_oks and chosen_ok < max(zero_wrong_oks):
        fail(f"G12 chosen candidate {chosen_letter} has ok_count={chosen_ok}; "
             f"another 0-wrong candidate has ok_count={max(zero_wrong_oks)}. "
             f"Selection rule requires highest fire rate among 0-wrong.")

    # ── Cross-check: chosen candidate's per-row CSV matches runtime ──
    # The chosen candidate is what's implemented in production; resolver is
    # deterministic given the same inputs. Any divergence between chosen
    # per-row CSV and runtime behavior means the CSV was generated from a
    # different implementation than what's running. Exact match required.
    chosen_per_row = NR_AUDIT_DIR / f"goal5_candidate_{chosen_letter}_per_row.csv"
    diffs = []
    for r in csv.DictReader(open(chosen_per_row, encoding="utf-8")):
        accn = r["accession_8k"]
        outcome = (r["candidate_outcome"] or "").strip().upper()
        cfy = (r.get("candidate_fy") or "").strip()
        cq = (r.get("candidate_q") or "").strip()
        runtime = observed_per_row.get(accn)
        if runtime is None:
            diffs.append(f"  {accn} appears in chosen per-row but not in runtime")
            continue
        r_outcome, r_fy, r_q = runtime
        if r_outcome != outcome:
            diffs.append(f"  {accn} chosen-csv={outcome}, runtime={r_outcome}")
            continue
        if outcome == "AUTO_OK" and (cfy, cq) != (r_fy, r_q):
            diffs.append(f"  {accn} chosen-csv=({cfy},{cq}) runtime=({r_fy},{r_q})")
    if diffs:
        for d in diffs[:10]:
            print(d, file=sys.stderr)
        fail(f"G12 chosen candidate {chosen_letter}'s per-row CSV diverges "
             f"from runtime resolver on {len(diffs)} rows. Per-row outcomes "
             f"are deterministic — exact match required. The implemented "
             f"production resolver does NOT match the chosen candidate spec.")

    info(f"G12 candidate matrix: {sorted(candidates_present)} reported, "
         f"per-row recomputed exactly, chosen={chosen_letter} "
         f"(ok={chosen_ok}, wrong=0), runtime matches chosen spec ✓")


# ── G13: report (optional) ────────────────────────────────────────────
def check_report_optional() -> None:
    if not GOAL5_REPORT_PATH.is_file():
        info("G13 GOAL5_REPORT.md not present (optional) — skipping content check")
        return
    text = GOAL5_REPORT_PATH.read_text(encoding="utf-8")
    if len(text) < 500:
        fail(f"G13 GOAL5_REPORT.md too short ({len(text)} bytes)")
    required = ["cleaned NR", "0 WRONG", "candidate"]
    missing = [k for k in required if k.lower() not in text.lower()]
    if missing:
        fail(f"G13 GOAL5_REPORT.md missing keywords: {missing}")
    info(f"G13 GOAL5_REPORT.md: {len(text)} bytes, all keywords present ✓")


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Goal 5 implementation verifier (hand-written; do not modify)."
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Iteration shortcut: G7 runs 200-row sample. G6 (cleaned NR) "
             "always runs all 731 scoreable rows (cheap). Bare command "
             "(no --fast) is canonical sign-off.",
    )
    args = parser.parse_args()
    full_mode = not args.fast

    mode_label = "FULL (canonical sign-off)" if full_mode else "FAST (iteration only)"
    print(f"=== Goal 5 verifier (hand-written, do not modify) — {mode_label} ===")
    print(f"Production code: {QI_PATH}")
    print(f"Verifier file:   {Path(__file__).resolve()}")
    print(f"Cleaned NR:      {NR_AUDIT_JSON}")
    print()

    check_verifier_git_clean()                            # G1
    check_resolver_changed()                              # G2
    check_scope_of_changes()                              # G3
    resolve_quarter_info = import_resolver()              # G4
    check_fcx_preserved(resolve_quarter_info)             # G5
    nr_correct_count, nr_observed = check_cleaned_nr_oracle(  # G6 (+ G14)
        resolve_quarter_info)
    check_goal4_oracle_preserved(resolve_quarter_info,    # G7
                                  full_mode=full_mode)
    check_115_odd_52_53(resolve_quarter_info)             # G8
    check_pytest()                                        # G9
    check_pytest_u64()                                    # G10
    check_write_guard()                                   # G11
    check_candidate_audit_csv(resolve_quarter_info,       # G12
                               observed_fire_count=nr_correct_count,
                               observed_per_row=nr_observed)
    check_report_optional()                               # G13

    print()
    info("=" * 60)
    if full_mode:
        info("ALL CHECKS PASSED — Goal 5 verified (FULL — canonical sign-off)")
    else:
        info("ALL CHECKS PASSED — Goal 5 verified (FAST — iteration only)")
        info("REMINDER: re-run without --fast for canonical sign-off.")
    info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
