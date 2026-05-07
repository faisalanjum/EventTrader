#!/usr/bin/env python3
"""
verify_goal_6c_implementation.py — Independent verifier for Goal 6c
(port Candidate D into production quarter_identity.py).

HAND-WRITTEN BY HUMANS to prevent self-rubber-stamping. Codex must NOT
modify this file; checked via git diff.

CHECKS PERFORMED (default = canonical sign-off; --fast for iteration):
  G1.  Verifier + immutable evidence inputs are git-clean
  G2.  quarter_identity.py modified — _STALE_MATCH_DAYS=150 still GONE;
       Goal 4 Rule F sources preserved verbatim; ALL 9 Goal 3 prelude
       sources preserved; ALL 5 new D source strings present
  G3.  No production code modified outside
       (quarter_identity.py + test_quarter_identity.py +
        test_quarter_identity_u64.py); orchestrator/fiscal_math/
       guidance files unchanged
  G4.  resolve_quarter_info importable; signature unchanged
  G5.  FCX 0000831259-26-000021 → Q1_FY2026 / AUTO_OK /
       prior_periodic_projection_q4_to_q1
  G6.  115 odd_52_53 → exactly 94 OK / 0 WRONG / 21 FAIL_CLOSED
       (Rule F preserved)
  G7.  No banned patterns in production: no ticker tables, no industry/
       sector keyed constants, no EX-99 string parsing, no external
       HTTP/sec-api calls
  G8.  Production resolver per-row exactly matches
       goal6a_d_measurement.csv on ALL 10,674 audited rows
       (outcome, fy, q, source). --fast samples 200 rows.
  G9.  pytest scripts/earnings/test_quarter_identity.py exits 0
  G10. pytest scripts/earnings/test_quarter_identity_u64.py exits 0
  G11. pytest -k write_guard collects ≥1 + exits 0
  G12. GOAL6C_REPORT.md (optional) content check

EXIT CODES:
  0 = pass; Goal 6c implementation verified
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

GROUND_TRUTH_PATH = _HERE / "ground_truth.csv"
NEEDS_REVIEW_PATH = _HERE / "needs_review.csv"
LIVE_AUDIT_PATH = _HERE / "live_mode_audit.csv"
SEC_5253_AUDIT_JSON = _HERE / "audit_evidence/sec_52_53_audit/all_verdicts.json"
NR_AUDIT_JSON = _HERE / "audit_evidence/sec_nr_auto_ok_audit/cleaned_all_verdicts.json"
GOAL4_BASELINE_CSV = _HERE / "audit_evidence/goal4_proven_ok_baseline.csv"
D_MEASUREMENT_CSV = _HERE / "goal6a_d_measurement.csv"
GOAL6C_REPORT_PATH = _HERE / "GOAL6C_REPORT.md"

# ── Allowed production modifications (only these 3 files) ────────────
ALLOWED_PROD_MODIFICATIONS = {
    "scripts/earnings/quarter_identity.py",
    "scripts/earnings/test_quarter_identity.py",
    "scripts/earnings/test_quarter_identity_u64.py",
}

# ── Files that MUST be unchanged from HEAD ──────────────────────────
# Explicitly locked: production files that Goal 6c must NOT modify.
# This list covers files OUTSIDE scripts/earnings/ (which is also watched
# wholesale by check_scope_of_changes). Inclusion is conservative — if a
# file is missing on disk the check is skipped, so adding here is safe.
PRODUCTION_FILES_LOCKED = [
    # scripts/earnings/ (also covered by general scan; redundant lock for safety)
    ORCHESTRATOR_PATH,
    # Pure math helpers (Class 3 consumers depend on these)
    FISCAL_MATH_PATH,
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py",
    # Mirror orchestrator under skills (Goal 4 write-guard)
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts/earnings_orchestrator.py",
    # Guidance pipeline / harvest / writer / IDs (consumers of resolve_quarter_info)
    HARVEST_GUIDANCE_PATH,
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py",
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts/guidance_writer.py",
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts/guidance_ids.py",
    # Daemon + extraction orchestration
    PROJECT_ROOT / "scripts/guidance_trigger_daemon.py",
    PROJECT_ROOT / "scripts/extraction_worker.py",
    PROJECT_ROOT / "scripts/trigger-extract.py",
]

# ── Immutable evidence inputs (git-clean) ────────────────────────────
_IMMUTABLE_EVIDENCE_FILES = [
    Path(__file__).resolve(),
    GROUND_TRUTH_PATH,
    NEEDS_REVIEW_PATH,
    LIVE_AUDIT_PATH,
    NR_AUDIT_JSON,
    GOAL4_BASELINE_CSV,
    SEC_5253_AUDIT_JSON,
    D_MEASUREMENT_CSV,  # the SPEC for production D's behavior
]

# ── Goal 4 source strings that MUST still be present ────────────────
GOAL3_PRELUDE_SOURCES = {
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
RULE_F_SOURCES = {
    "rule_f_direct_recent_prior",
    "rule_f_advance_xbrl",
    "rule_f_fail_closed_recent_no_xbrl",
    "rule_f_fail_closed_missing_signal",
    "rule_f_fail_closed_fy_disagreement",
}
RULE_G_NEW_SOURCES = {
    "rule_g_strict_direct_recent_prior_calendar",
    "rule_g_strict_fail_closed_recent_disagreement_calendar",
    "rule_g_fail_closed_fy_disagreement_calendar",
    "rule_g_fail_closed_no_prev_short_gap_calendar",
    "rule_g_fail_closed_same_filing_short_gap_calendar",
}

# ── Expected hard-lock numbers ───────────────────────────────────────
EXPECTED_115_OK = 94
EXPECTED_115_WRONG = 0
EXPECTED_115_FAIL_CLOSED = 21
EXPECTED_TOTAL_SCOREABLE = 10674

FAST_SAMPLE_N = 200
FAST_SEED = 20260508


def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


# ── G1: git-clean (verifier + evidence inputs) ───────────────────────
def check_evidence_git_clean() -> None:
    for path in _IMMUTABLE_EVIDENCE_FILES:
        if not path.is_file():
            fail(f"G1 evidence file missing: {path}", code=2)
        rel = str(path.relative_to(PROJECT_ROOT))
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=str(PROJECT_ROOT), capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            fail(f"G1 evidence file not git-committed: {rel}", code=2)
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
def check_resolver_changed() -> None:
    if not QI_PATH.is_file():
        fail(f"G2 production file missing: {QI_PATH}", code=2)
    src = QI_PATH.read_text(encoding="utf-8")

    # FCX bug constant must STILL be gone
    if re.search(r"_STALE_MATCH_DAYS\s*=\s*150", src):
        fail("G2 old `_STALE_MATCH_DAYS = 150` reappeared — must be absent.")

    # Old Goal 3 odd_52_53 fail-close must STILL be gone (Rule F replaced it in Goal 4)
    if "odd_52_53_week_prior_fail_closed" in src:
        fail("G2 Goal 3's `odd_52_53_week_prior_fail_closed` source reappeared — "
             "Goal 4 replaced it with Rule F; do NOT reintroduce.")

    # ALL Goal 3 prelude + Rule F sources still present
    missing_g3 = [s for s in GOAL3_PRELUDE_SOURCES if s not in src]
    missing_rf = [s for s in RULE_F_SOURCES if s not in src]
    if missing_g3:
        fail(f"G2 missing Goal 3 prelude sources: {sorted(missing_g3)}")
    if missing_rf:
        fail(f"G2 missing Rule F sources: {sorted(missing_rf)}")

    # ALL 5 new D source strings present
    missing_g = [s for s in RULE_G_NEW_SOURCES if s not in src]
    if missing_g:
        fail(f"G2 missing Rule G (D) source strings: {sorted(missing_g)}\n"
             f"D's calendar-branch guards are not implemented. Required: "
             f"{sorted(RULE_G_NEW_SOURCES)}")

    # _effective_fye_month logic preserved
    if "_effective_fye_month" not in src and "effective_fye" not in src:
        fail("G2 `_effective_fye_month` / effective_fye logic missing.")
    if "_effective_fye_from_prior_10k" not in src:
        fail("G2 source augmentation `_effective_fye_from_prior_10k` removed.")

    info(f"G2 resolver: 9 Goal-3 + 5 Rule-F + 5 new Rule-G sources present ✓")


# ── G3: scope check (only quarter_identity.py + 2 test files) ────────
def check_scope_of_changes() -> None:
    # Locked files MUST be unchanged from HEAD in EVERY way:
    # - not modified (M)
    # - not deleted (D)
    # - not newly created untracked (??)
    # `git status --short -- <path>` covers all three. `git diff --quiet`
    # alone misses deletions (when the file no longer exists, the diff
    # is empty until staged) and misses untracked-creations entirely.
    for path in PRODUCTION_FILES_LOCKED:
        rel = str(path.relative_to(PROJECT_ROOT))
        r = subprocess.run(
            ["git", "status", "--short", "--", rel],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
        )
        if r.stdout.strip():
            fail(f"G3 LOCKED FILE CHANGED: {rel}\n"
                 f"  git status: {r.stdout.strip()}\n"
                 f"Goal 6c MUST NOT modify, delete, or newly-create this file "
                 f"(orchestrator / fiscal_math / guidance / daemon / extraction / "
                 f"etc). Revert and re-run.")

    # All scripts/earnings/ changes must be in allowed paths or test fixtures
    r = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "scripts/earnings/"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
    )
    modified = [line for line in r.stdout.splitlines() if line.strip()]
    r2 = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "scripts/earnings/"],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
    )
    untracked = [line for line in r2.stdout.splitlines() if line.strip()]

    forbidden = []
    for p in modified + untracked:
        if p in ALLOWED_PROD_MODIFICATIONS:
            continue
        if "/tests/fixtures/" in p:
            continue
        forbidden.append(p)
    if forbidden:
        for p in forbidden:
            print(f"  {p}", file=sys.stderr)
        fail(f"G3 forbidden changes under scripts/earnings/ "
             f"({len(forbidden)} files). Allowed: {sorted(ALLOWED_PROD_MODIFICATIONS)}")
    info("G3 scope: changes confined to quarter_identity.py + tests ✓")


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
    src = qi.get("quarter_identity_source") or ""
    if ql != "Q1_FY2026":
        fail(f"G5 FCX quarter_label={ql!r}; expected 'Q1_FY2026' (sa={sa!r} src={src!r})")
    if sa != "AUTO_OK":
        fail(f"G5 FCX safety_action={sa!r}; expected 'AUTO_OK'")
    if src != "prior_periodic_projection_q4_to_q1":
        fail(f"G5 FCX source={src!r}; expected 'prior_periodic_projection_q4_to_q1'")
    info(f"G5 FCX 0000831259-26-000021 → Q1_FY2026 / AUTO_OK / {src} ✓")


# ── G6: 115 odd_52_53 — Rule F preserved ─────────────────────────────
def parse_label(quarter_label: str):
    if not quarter_label:
        return (None, None)
    try:
        q_part, fy_part = quarter_label.split("_FY")
        return (fy_part, q_part)
    except ValueError:
        return (None, None)


def check_115_odd_52_53(resolve_quarter_info) -> None:
    if not LIVE_AUDIT_PATH.is_file():
        fail(f"G6 live_mode_audit.csv missing: {LIVE_AUDIT_PATH}", code=2)
    if not SEC_5253_AUDIT_JSON.is_file():
        fail(f"G6 SEC 52/53 audit JSON missing: {SEC_5253_AUDIT_JSON}", code=2)

    all_corpus = {}
    for p in [GROUND_TRUTH_PATH, NEEDS_REVIEW_PATH]:
        for r in csv.DictReader(open(p, encoding="utf-8")):
            all_corpus[r["accession_8k"]] = r
    sec_audit = {r["accession_8k"]: (r["audited_fy"], r["audited_q"])
                 for r in json.load(open(SEC_5253_AUDIT_JSON, encoding="utf-8"))}

    odd = [r for r in csv.DictReader(open(LIVE_AUDIT_PATH, encoding="utf-8"))
           if r["candidate_name"] == "prior_periodic_projection"
           and r["candidate_source"] == "prior_periodic_projection_odd_52_53_week_prior_fail_closed"]
    if len(odd) != 115:
        fail(f"G6 odd_52_53 set size = {len(odd)}; expected 115", code=2)

    oracles = {}
    for r in odd:
        a = r["accession_8k"]
        if r["corpus_label"] == "ground_truth":
            cr = all_corpus[a]
            oracles[a] = (cr["fy_xbrl"], cr["q_xbrl"])
        elif a in sec_audit:
            oracles[a] = sec_audit[a]
    if len(oracles) != 115:
        fail(f"G6 oracle coverage incomplete: {len(oracles)}/115", code=2)

    n_ok = n_wrong = n_fc = 0
    for a, (o_fy, o_q) in oracles.items():
        ticker = next(r["ticker"] for r in odd if r["accession_8k"] == a)
        try:
            qi = resolve_quarter_info(ticker, a)
        except Exception as e:
            fail(f"G6 resolver raised on {a}: {type(e).__name__}: {e}", code=2)
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

    if (n_ok, n_wrong, n_fc) != (EXPECTED_115_OK, EXPECTED_115_WRONG, EXPECTED_115_FAIL_CLOSED):
        fail(f"G6 115 odd_52_53: got {n_ok}/{n_wrong}/{n_fc}; "
             f"expected exactly {EXPECTED_115_OK}/{EXPECTED_115_WRONG}/"
             f"{EXPECTED_115_FAIL_CLOSED} (Rule F preserved). Goal 6c "
             f"must NOT modify Rule F's odd_52_53 branch.")
    info(f"G6 115 odd_52_53: {n_ok}/{n_wrong}/{n_fc} (Rule F preserved) ✓")


# ── G7: banned-pattern anti-leak ─────────────────────────────────────
_BANNED_TICKER_PATTERNS = [
    re.compile(r"\b(?:ALLOWLIST|DENYLIST|EXTREME_CALENDAR|FIVE_TWO_THREE|"
               r"WEEK_FIFTY_THREE|FY_CONVENTION|TICKER_SPECIAL|ODD_FISCAL|"
               r"ISSUER_FY_MAP|FY_NAMING_TABLE|RETAIL_FYE)"
               r"[A-Z_]*\s*=", re.IGNORECASE),
    re.compile(r"if\s+ticker\s+in\s*[\(\{]['\"](?:AAP|PSTG|ACI|KR|NTAP|"
               r"PEP|LEVI|PLAY|SYNA|ESTC|AZO|COST|GIS|DRI|ANF|KSS|BJ|"
               r"BURL|CHWY|FIVE|GME|LOW|LULU|OXM|PVH|ROST|ULTA|DKS|DLTR)",
               re.IGNORECASE),
    re.compile(r"ticker\s*==\s*['\"](?:AAP|PSTG|ACI|KR|NTAP|PEP|LEVI|"
               r"PLAY|SYNA|ESTC|ANF|KSS)['\"]", re.IGNORECASE),
]
_BANNED_INDUSTRY_PATTERNS = [
    re.compile(r"_RISK_INDUSTRIES\b"),
    re.compile(r"_INDUSTRY_RISK\b", re.IGNORECASE),
    re.compile(r"rule_g_[a-z0-9_]*industry[a-z0-9_]*", re.IGNORECASE),
    re.compile(r"industry\s+in\s*[\(\{]", re.IGNORECASE),
    re.compile(r"sector\s+in\s*[\(\{]", re.IGNORECASE),
]
_BANNED_TEXT_PARSING_PATTERNS = [
    # EX-99 / press-release literals
    re.compile(r"['\"]EX-99\.?1?['\"]", re.IGNORECASE),
    re.compile(r"\bex_?99[_-]?1?\b", re.IGNORECASE),
    re.compile(r"['\"](?:Reports?|reports)\s+(?:First|Second|Third|Fourth)\s+Quarter",
               re.IGNORECASE),
    # External SEC/EDGAR domains
    re.compile(r"\bsec[_-]?api\.io\b", re.IGNORECASE),
    re.compile(r"\bedgar\.sec\.gov", re.IGNORECASE),
    # Network library imports — banned in production resolver path
    # (production must be PIT, deterministic, Neo4j-only). Catches both
    # `import requests` and `from requests import X` forms.
    re.compile(r"^\s*import\s+requests\b", re.MULTILINE),
    re.compile(r"^\s*from\s+requests\b", re.MULTILINE),
    re.compile(r"^\s*import\s+httpx\b", re.MULTILINE),
    re.compile(r"^\s*from\s+httpx\b", re.MULTILINE),
    re.compile(r"^\s*import\s+urllib\.request\b", re.MULTILINE),
    re.compile(r"^\s*from\s+urllib\.request\b", re.MULTILINE),
    re.compile(r"^\s*from\s+urllib\s+import\s+request\b", re.MULTILINE),
    re.compile(r"^\s*import\s+sec_api\b", re.MULTILINE),
    re.compile(r"^\s*from\s+sec_api\b", re.MULTILINE),
    re.compile(r"^\s*import\s+edgar\b", re.MULTILINE),
    re.compile(r"^\s*from\s+edgar\b", re.MULTILINE),
    # Direct call patterns (caught even if imported under alias)
    re.compile(r"\brequests\.(?:get|post|put|delete|head|patch)\b"),
    re.compile(r"\bhttpx\.(?:get|post|put|delete|head|patch)\b"),
    re.compile(r"\burlopen\s*\(", re.IGNORECASE),
]


def check_banned_patterns() -> None:
    src = QI_PATH.read_text(encoding="utf-8")
    for pat in _BANNED_TICKER_PATTERNS:
        m = pat.search(src)
        if m:
            ctx = src[max(0, m.start()-50):m.end()+50]
            if "XBRL_DENY_PERIODIC_ACCESSIONS" in ctx:
                continue  # allowed exception
            fail(f"G7 banned ticker pattern in production: {m.group(0)!r}")
    for pat in _BANNED_INDUSTRY_PATTERNS:
        m = pat.search(src)
        if m:
            fail(f"G7 banned industry-classifier pattern in production: "
                 f"{m.group(0)!r}\n"
                 f"E-class industry guards are research-only; do NOT promote "
                 f"to production.")
    for pat in _BANNED_TEXT_PARSING_PATTERNS:
        m = pat.search(src)
        if m:
            fail(f"G7 banned EX-99 / press-release / network pattern: "
                 f"{m.group(0)!r}")
    info("G7 no banned ticker / industry / EX-99 / network patterns ✓")


# ── G8: per-row exact match against goal6a_d_measurement.csv ─────────
def check_d_measurement_match(resolve_quarter_info, *, full_mode: bool) -> None:
    """G8: production resolver must produce per-row outputs identical to
    goal6a_d_measurement.csv on all 10,674 audited rows. This is the
    load-bearing gate: if production D differs from the measured D,
    that's a regression vs the spec we already reviewed."""
    if not D_MEASUREMENT_CSV.is_file():
        fail(f"G8 D measurement CSV missing: {D_MEASUREMENT_CSV}", code=2)
    rows = list(csv.DictReader(open(D_MEASUREMENT_CSV, encoding="utf-8")))
    if len(rows) != EXPECTED_TOTAL_SCOREABLE:
        fail(f"G8 D measurement row count = {len(rows)}; "
             f"expected {EXPECTED_TOTAL_SCOREABLE}", code=2)

    if full_mode:
        sample = rows
    else:
        random.seed(FAST_SEED)
        sample = random.sample(rows, FAST_SAMPLE_N)

    info(f"G8 running resolver on {len(sample)} rows "
         f"({'FULL' if full_mode else 'FAST'})...")

    n_match = n_diff = 0
    diffs = []
    for i, r in enumerate(sample):
        ticker = r["ticker"]
        accn = r["accession_8k"]
        try:
            qi = resolve_quarter_info(ticker, accn)
        except Exception as e:
            fail(f"G8 resolver raised on {ticker}/{accn}: "
                 f"{type(e).__name__}: {e}", code=2)
        # Map production return → measurement schema
        sa = qi.get("safety_action") or ""
        ql = qi.get("quarter_label") or ""
        src = qi.get("quarter_identity_source") or ""
        if sa == "AUTO_OK" and ql:
            rfy, rq = parse_label(ql)
            prod_outcome = "AUTO_OK"
            prod_fy = rfy or ""
            prod_q = rq or ""
        else:
            prod_outcome = "FAIL_CLOSED"
            prod_fy = ""
            prod_q = ""
        prod_source = src

        exp_outcome = r["outcome"]
        exp_fy = r["fy"]
        exp_q = r["q"]
        exp_source = r["source"]

        if (prod_outcome, prod_fy, prod_q, prod_source) == \
           (exp_outcome, exp_fy, exp_q, exp_source):
            n_match += 1
        else:
            n_diff += 1
            if len(diffs) < 10:
                diffs.append(
                    f"  {ticker}/{accn}\n"
                    f"    prod: {prod_outcome} ({prod_fy},{prod_q}) src={prod_source!r}\n"
                    f"    spec: {exp_outcome} ({exp_fy},{exp_q}) src={exp_source!r}"
                )
        if full_mode and (i + 1) % 1000 == 0:
            print(f"  G8: {i+1}/{len(sample)} (match={n_match}, diff={n_diff})",
                  flush=True)

    if n_diff > 0:
        for d in diffs:
            print(d, file=sys.stderr)
        fail(f"G8 production resolver diverges from goal6a_d_measurement.csv "
             f"on {n_diff} of {len(sample)} rows. Production D MUST match "
             f"the measured D exactly.")
    info(f"G8 {len(sample)} rows match D spec exactly ✓")


# ── G9/G10/G11: pytest checks ─────────────────────────────────────────
def check_pytest(test_path: Path, label: str) -> None:
    if not test_path.is_file():
        fail(f"{label} test file missing: {test_path}")
    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest", "-xvs",
         str(test_path)],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        print(r.stdout[-3000:], file=sys.stderr)
        print(r.stderr[-1000:], file=sys.stderr)
        fail(f"{label} pytest exited {r.returncode}")
    info(f"{label} pytest passed ✓")


def check_write_guard() -> None:
    """G11: Goal 4's destructive-write guard tests must still pass."""
    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest",
         "-v", "-k", "write_guard", "--collect-only", "-q",
         str(PROJECT_ROOT / "scripts/earnings/")],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120,
    )
    m = re.search(r"(\d+)\s+tests?\s+collected", r.stdout)
    n_collected = int(m.group(1)) if m else 0
    if n_collected == 0:
        fail("G11 no tests matching '-k write_guard' collected. "
             "Goal 4's destructive-write guard tests must still exist.")

    r = subprocess.run(
        [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest",
         "-xvs", "-k", "write_guard",
         str(PROJECT_ROOT / "scripts/earnings/")],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        print(r.stdout[-3000:], file=sys.stderr)
        fail(f"G11 write-guard pytest exited {r.returncode}")
    info(f"G11 write-guard preserved: {n_collected} test(s) passed ✓")


# ── G12: report (optional) ────────────────────────────────────────────
def check_report_optional() -> None:
    if not GOAL6C_REPORT_PATH.is_file():
        info("G12 GOAL6C_REPORT.md not present (optional) — skipping")
        return
    text = GOAL6C_REPORT_PATH.read_text(encoding="utf-8")
    if len(text) < 300:
        fail(f"G12 GOAL6C_REPORT.md too short ({len(text)} bytes)")
    required = ["Candidate D", "goal6a_d_measurement", "10,674"]
    missing = [k for k in required if k not in text]
    if missing:
        fail(f"G12 GOAL6C_REPORT.md missing keywords: {missing}")
    info(f"G12 GOAL6C_REPORT.md: {len(text)} bytes, all keywords present ✓")


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Goal 6c implementation verifier (hand-written; do not modify)."
    )
    parser.add_argument(
        "--fast", action="store_true",
        help="G8 samples 200 rows instead of full 10,674. Bare command = sign-off."
    )
    args = parser.parse_args()
    full_mode = not args.fast

    mode_label = "FULL (canonical sign-off)" if full_mode else "FAST (iteration)"
    print(f"=== Goal 6c verifier (hand-written, do not modify) — {mode_label} ===")
    print(f"Production code: {QI_PATH}")
    print(f"Verifier file:   {Path(__file__).resolve()}")
    print(f"D spec:          {D_MEASUREMENT_CSV}")
    print()

    check_evidence_git_clean()                             # G1
    check_resolver_changed()                               # G2
    check_scope_of_changes()                               # G3
    resolve_quarter_info = import_resolver()               # G4
    check_fcx_preserved(resolve_quarter_info)              # G5
    check_115_odd_52_53(resolve_quarter_info)              # G6
    check_banned_patterns()                                # G7
    check_d_measurement_match(resolve_quarter_info,        # G8
                                full_mode=full_mode)
    check_pytest(TEST_QI_PATH, "G9")                       # G9
    check_pytest(TEST_QI_U64_PATH, "G10")                  # G10
    check_write_guard()                                    # G11
    check_report_optional()                                # G12

    print()
    info("=" * 60)
    if full_mode:
        info("ALL CHECKS PASSED — Goal 6c verified (FULL — canonical sign-off)")
    else:
        info("ALL CHECKS PASSED — Goal 6c verified (FAST — iteration only)")
        info("REMINDER: re-run without --fast for canonical sign-off.")
    info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
