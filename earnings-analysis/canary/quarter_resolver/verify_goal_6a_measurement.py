#!/usr/bin/env python3
"""
verify_goal_6a_measurement.py — Independent verifier for Goal 6a
(measurement-only benchmark of Candidate D + E across full historical /
warm-start / cold-start / latest-per-ticker subsets).

HAND-WRITTEN BY HUMANS to prevent self-rubber-stamping. Codex must NOT
modify this file; checked via git diff.

CHECKS PERFORMED:
  G1.  Verifier file is git-clean (anti-tampering)
  G2.  Immutable evidence inputs are git-clean
  G3.  ZERO production code changes (scripts/earnings/quarter_identity.py
       and friends MUST be unchanged at HEAD)
  G4.  goal6_candidates.py exists at canary path; module docstring contains
       "RESEARCH-ONLY"; not imported by production code under scripts/
  G5.  E's industry-classifier source strings absent from production
       quarter_identity.py (anti-leak)
  G6.  goal6a_d_measurement.csv exists with required schema, 10,674 unique
       rows
  G7.  goal6a_e_measurement.csv exists with required schema, 10,674 unique
       rows, row set identical to D's
  G8.  Determinism: re-import goal6_candidates and re-run a 50-row sample;
       outputs match the CSV byte-for-byte (deterministic)
  G9.  D's measurement on the 9,116-row Goal 4 baseline subset:
       counts (preserved / regressed-to-fc / regressed-to-wrong) are
       recomputed and reported. NOT a 0-tolerance gate (Goal 6a is
       measurement-only); the gate fails only if report counts mismatch.
  G10. D's measurement on the 587 cleaned-NR-wrong subset:
       counts (still-wrong / now-fc / now-correct) are recomputed and
       reported. NOT a 0-tolerance gate; gate fails only on count mismatch.
  G11. GOAL6A_REPORT.md exists with required tables 1/2/3 and the
       DECISION_FLAG_SHIP_D_DIRECTLY value (yes/no)
  G12. Subset reconciliation:
       warm_start + cold_start == 10,674
       latest_per_ticker count == unique-ticker count in scoreable set
  G13. Aggregate counts in GOAL6A_REPORT.md exactly equal independent
       recompute from per-row CSVs (no tolerance)

EXIT CODES:
  0 = pass; Goal 6a measurement verified
  1 = fatal violation
  2 = verifier infra failed
"""
from __future__ import annotations
import argparse
import csv
import importlib
import importlib.util
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

GROUND_TRUTH_PATH = _HERE / "ground_truth.csv"
NEEDS_REVIEW_PATH = _HERE / "needs_review.csv"
LIVE_AUDIT_PATH = _HERE / "live_mode_audit.csv"
SEC_5253_AUDIT_JSON = _HERE / "audit_evidence/sec_52_53_audit/all_verdicts.json"
NR_AUDIT_JSON = _HERE / "audit_evidence/sec_nr_auto_ok_audit/cleaned_all_verdicts.json"
NR_AUDIT_DIR = _HERE / "audit_evidence/sec_nr_auto_ok_audit"
GOAL4_BASELINE_CSV = _HERE / "audit_evidence/goal4_proven_ok_baseline.csv"

# 6a output paths
GOAL6_CANDIDATES_PY = _HERE / "goal6_candidates.py"
D_MEASUREMENT_CSV = _HERE / "goal6a_d_measurement.csv"
E_MEASUREMENT_CSV = _HERE / "goal6a_e_measurement.csv"
GOAL6A_REPORT = _HERE / "GOAL6A_REPORT.md"

# ── Production files that MUST NOT change ────────────────────────────
PRODUCTION_FILES_LOCKED = [
    QI_PATH,
    ORCHESTRATOR_PATH,
    TEST_QI_PATH,
    TEST_QI_U64_PATH,
]

# ── Immutable evidence inputs (git-clean) ────────────────────────────
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

# ── Expected hard-lock numbers ───────────────────────────────────────
EXPECTED_GOAL4_BASELINE_ROWS = 9116
EXPECTED_NR_TOTAL = 838
EXPECTED_NR_OK = 144
EXPECTED_NR_WRONG = 587
EXPECTED_NR_UNCLEAR = 107
EXPECTED_NR_SCOREABLE = EXPECTED_NR_OK + EXPECTED_NR_WRONG  # 731
EXPECTED_ORACLE_POOL = 9909 + 34  # GT + SEC_5253 = 9,943
EXPECTED_TOTAL_SCOREABLE = EXPECTED_ORACLE_POOL + EXPECTED_NR_SCOREABLE  # 10,674

DETERMINISM_SAMPLE_N = 50
DETERMINISM_SEED = 20260507

REQUIRED_CSV_COLUMNS = {
    "accession_8k", "ticker", "oracle_source", "oracle_fy", "oracle_q",
    "warm_start", "latest_per_ticker",
    "outcome", "fy", "q", "source", "correct",
}


def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


# ── G1+G2: git-clean (verifier + immutable evidence) ─────────────────
def check_evidence_git_clean() -> None:
    for path in _IMMUTABLE_EVIDENCE_FILES:
        if not path.is_file():
            fail(f"G1/G2 evidence file missing: {path}", code=2)
        rel = str(path.relative_to(PROJECT_ROOT))
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=str(PROJECT_ROOT), capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            fail(f"G1/G2 evidence file not git-committed: {rel}\n"
                 f"All oracle/evidence files must be committed BEFORE Goal 6a runs.",
                 code=2)
        r = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", rel],
            cwd=str(PROJECT_ROOT), capture_output=True, timeout=30,
        )
        if r.returncode != 0:
            fail(f"G1/G2 evidence file has uncommitted changes vs HEAD: {rel}\n"
                 f"Codex MUST NOT modify oracle/evidence inputs.", code=2)
    info(f"G1+G2 verifier + {len(_IMMUTABLE_EVIDENCE_FILES)-1} evidence files "
         f"git-clean ✓")


# ── G3: ZERO production code changes ─────────────────────────────────
def check_no_production_changes() -> None:
    for path in PRODUCTION_FILES_LOCKED:
        if not path.is_file():
            fail(f"G3 production file missing: {path}", code=2)
        rel = str(path.relative_to(PROJECT_ROOT))
        # must be unchanged vs HEAD (no Codex modification)
        r = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", rel],
            cwd=str(PROJECT_ROOT), capture_output=True, timeout=30,
        )
        if r.returncode != 0:
            fail(f"G3 PRODUCTION FILE MODIFIED (forbidden in Goal 6a): {rel}\n"
                 f"Goal 6a is measurement-only. Revert this file before re-running.")

    # Also check no other scripts/earnings/ file outside test fixtures
    # has been modified or added.
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
        # Allow test fixtures
        if "/tests/fixtures/" in p or "/test_fixtures/" in p:
            continue
        if "/test_" in p or p.endswith("_test.py"):
            # allow new tests... but Goal 6a should not need new production tests.
            forbidden.append(f"new/modified test file: {p} (Goal 6a is measurement-only)")
            continue
        forbidden.append(p)
    if forbidden:
        for p in forbidden:
            print(f"  {p}", file=sys.stderr)
        fail(f"G3 forbidden changes under scripts/earnings/ "
             f"({len(forbidden)} files). Goal 6a is measurement-only; "
             f"no scripts/earnings/ files may be modified or added.")
    info("G3 zero production code changes ✓")


# ── G4: goal6_candidates.py research-only isolation ──────────────────
def check_research_file_isolation() -> None:
    if not GOAL6_CANDIDATES_PY.is_file():
        fail(f"G4 goal6_candidates.py missing: {GOAL6_CANDIDATES_PY}\n"
             f"Codex must create this research-only module.")
    src = GOAL6_CANDIDATES_PY.read_text(encoding="utf-8")
    if "RESEARCH-ONLY" not in src:
        fail("G4 goal6_candidates.py module docstring must contain "
             "'RESEARCH-ONLY' (anti-confusion marker).")

    # Check no production code under scripts/ imports it
    r = subprocess.run(
        ["grep", "-rln", "goal6_candidates",
         str(PROJECT_ROOT / "scripts")],
        capture_output=True, text=True, timeout=30,
    )
    matches = [line for line in r.stdout.splitlines() if line.strip()]
    if matches:
        for m in matches:
            print(f"  imports goal6_candidates: {m}", file=sys.stderr)
        fail(f"G4 production code imports goal6_candidates "
             f"({len(matches)} files). Research module MUST NOT be "
             f"imported by anything under scripts/.")
    info("G4 research-only file isolation ✓")


# ── G5: E source strings anti-leak ───────────────────────────────────
_E_INDUSTRY_SOURCE_PATTERNS = [
    re.compile(r"rule_g_[a-z0-9_]*industry[a-z0-9_]*", re.IGNORECASE),
    re.compile(r"rule_g_jan_annual_[a-z0-9_]*", re.IGNORECASE),
    re.compile(r"_RISK_INDUSTRIES\b"),
    re.compile(r"_INDUSTRY_RISK\b", re.IGNORECASE),
]


def check_e_anti_leak() -> None:
    src = QI_PATH.read_text(encoding="utf-8")
    leaked = []
    for pat in _E_INDUSTRY_SOURCE_PATTERNS:
        for m in pat.finditer(src):
            leaked.append(f"  {pat.pattern} matched {m.group(0)!r}")
    if leaked:
        for l in leaked:
            print(l, file=sys.stderr)
        fail(f"G5 E's industry-classifier source strings leaked into "
             f"production quarter_identity.py ({len(leaked)} matches). "
             f"E is research-only and must not appear in production.")
    info("G5 E industry-classifier source strings absent from production ✓")


# ── G6+G7: measurement CSVs schema/rowcount ──────────────────────────
def _read_measurement_csv(path: Path, label: str) -> list[dict]:
    if not path.is_file():
        fail(f"{label} measurement CSV missing: {path}")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if not rows:
        fail(f"{label} measurement CSV is empty: {path}")
    missing = REQUIRED_CSV_COLUMNS - set(rows[0].keys())
    if missing:
        fail(f"{label} measurement CSV missing columns: {sorted(missing)}")
    if len(rows) != EXPECTED_TOTAL_SCOREABLE:
        fail(f"{label} measurement CSV has {len(rows)} rows; "
             f"expected exactly {EXPECTED_TOTAL_SCOREABLE} "
             f"(9,943 oracle + 731 cleaned-NR scoreable).")
    accns = [r["accession_8k"] for r in rows]
    if len(set(accns)) != len(accns):
        seen = set()
        dup = next((a for a in accns if a in seen or seen.add(a)), None)
        fail(f"{label} measurement CSV has duplicate accession {dup!r}")
    return rows


def check_d_csv() -> list[dict]:
    rows = _read_measurement_csv(D_MEASUREMENT_CSV, "G6 D")
    info(f"G6 D measurement CSV: {len(rows)} unique rows ✓")
    return rows


def check_e_csv(d_rows: list[dict]) -> list[dict]:
    rows = _read_measurement_csv(E_MEASUREMENT_CSV, "G7 E")
    d_accns = {r["accession_8k"] for r in d_rows}
    e_accns = {r["accession_8k"] for r in rows}
    if d_accns != e_accns:
        only_d = d_accns - e_accns
        only_e = e_accns - d_accns
        fail(f"G7 E measurement CSV has different accession set than D's. "
             f"D-only={len(only_d)} E-only={len(only_e)}")
    info(f"G7 E measurement CSV: {len(rows)} unique rows, set matches D's ✓")
    return rows


# ── G8: TRUE determinism check (re-run candidates against CSV) ──────
def _load_candidates_module():
    sys.path.insert(0, str(_HERE))
    sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))
    sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))
    try:
        spec = importlib.util.spec_from_file_location(
            "goal6_candidates", GOAL6_CANDIDATES_PY
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
    except Exception as e:
        fail(f"G8 cannot import goal6_candidates.py: "
             f"{type(e).__name__}: {e}", code=2)
    if not hasattr(mod, "candidate_d"):
        fail("G8 goal6_candidates.py must expose `candidate_d` callable.")
    if not hasattr(mod, "candidate_e"):
        fail("G8 goal6_candidates.py must expose `candidate_e` callable.")
    return mod


def _open_neo4j_session():
    """Open Neo4j session using .env credentials. Same pattern as
    compute_goal4_baseline.py."""
    import os
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(
                    k.strip(), v.strip().strip('"').strip("'"))
    try:
        from neo4j import GraphDatabase
    except Exception as e:
        fail(f"G8 cannot import neo4j: {e}", code=2)
    uri = os.environ.get("NEO4J_URI", "bolt://minisforum3:30687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    pw = os.environ.get("NEO4J_PASSWORD")
    if not pw:
        fail("G8 NEO4J_PASSWORD not set in .env or environment", code=2)
    driver = GraphDatabase.driver(uri, auth=(user, pw))
    return driver


def _verify_sample(mod, candidate_name: str, csv_rows: list[dict],
                   driver, label: str) -> None:
    """Sample N rows from csv_rows, call candidate_<name> on each via
    candidate_d / candidate_e, exact-match the (outcome, fy, q, source)
    tuple. Any mismatch fails."""
    fn = getattr(mod, candidate_name)
    rng = random.Random(DETERMINISM_SEED if candidate_name == "candidate_d"
                        else DETERMINISM_SEED + 1)
    sample = rng.sample(csv_rows, min(DETERMINISM_SAMPLE_N, len(csv_rows)))
    mismatches = []
    with driver.session() as session:
        for i, r in enumerate(sample):
            try:
                got = fn(r["ticker"], r["accession_8k"], neo4j_session=session)
            except Exception as e:
                fail(f"G8 {candidate_name} raised on "
                     f"{r['ticker']}/{r['accession_8k']}: "
                     f"{type(e).__name__}: {e}", code=2)
            if not isinstance(got, dict):
                fail(f"G8 {candidate_name} did not return dict; got {type(got).__name__}")
            for k in ("outcome", "fy", "q", "source"):
                if k not in got:
                    fail(f"G8 {candidate_name} return dict missing key "
                         f"{k!r} (got keys: {sorted(got.keys())})")
            # Exact match on all 4 fields
            mismatch_fields = []
            for k in ("outcome", "fy", "q", "source"):
                csv_val = r.get(k, "")
                got_val = got.get(k, "")
                if str(csv_val) != str(got_val):
                    mismatch_fields.append(f"{k}: csv={csv_val!r} got={got_val!r}")
            if mismatch_fields:
                mismatches.append(
                    f"  {r['ticker']}/{r['accession_8k']}: "
                    + "; ".join(mismatch_fields)
                )
                if len(mismatches) > 10:
                    break
    if mismatches:
        for m in mismatches[:10]:
            print(m, file=sys.stderr)
        fail(f"G8 {candidate_name} CSV diverges from runtime on "
             f"{len(mismatches)} of {len(sample)} sampled rows. "
             f"The {label} per-row CSV was not produced by the current "
             f"candidate code. Re-generate the CSV.")
    info(f"G8 {candidate_name}: {len(sample)} sample rows match runtime exactly ✓")


def check_determinism(d_rows: list[dict], e_rows: list[dict]) -> None:
    """G8: TRUE rerun. Open Neo4j session, sample 50 rows each from D
    and E CSVs, call candidate_d / candidate_e on each, exact-match
    (outcome, fy, q, source) against the CSV."""
    mod = _load_candidates_module()
    driver = _open_neo4j_session()
    try:
        _verify_sample(mod, "candidate_d", d_rows, driver, "D")
        _verify_sample(mod, "candidate_e", e_rows, driver, "E")
    finally:
        try:
            driver.close()
        except Exception:
            pass


# ── G9: D's behavior on Goal 4 baseline (measurement, not gate) ─────
def check_goal4_baseline_measurement(d_rows: list[dict]) -> tuple:
    """Measurement-only: count D's preserved / regressed-to-fc /
    regressed-to-wrong on Goal 4 baseline (9,116 rows). Returns the
    counts for G13 to cross-check against the report. Does NOT fail on
    magnitude — Goal 6a is measurement-only; the SHIP_D_DIRECTLY flag
    in the report is what informs the user's downstream decision."""
    baseline = list(csv.DictReader(open(GOAL4_BASELINE_CSV, encoding="utf-8")))
    if len(baseline) != EXPECTED_GOAL4_BASELINE_ROWS:
        fail(f"G9 Goal 4 baseline has {len(baseline)} rows; "
             f"expected {EXPECTED_GOAL4_BASELINE_ROWS}", code=2)

    baseline_accns = {r["accession_8k"]: r for r in baseline}
    d_by_accn = {r["accession_8k"]: r for r in d_rows}

    n_preserved = 0
    n_lost_to_fc = 0
    n_changed_label = 0
    for accn, b in baseline_accns.items():
        d = d_by_accn.get(accn)
        if d is None:
            fail(f"G9 baseline accession {accn} missing from D measurement CSV",
                 code=2)
        if d["outcome"] == "FAIL_CLOSED":
            n_lost_to_fc += 1
            continue
        if (d["fy"], d["q"]) == (b["fy"], b["q"]):
            n_preserved += 1
        else:
            n_changed_label += 1

    info(f"G9 D vs Goal 4 baseline: preserved={n_preserved}/{EXPECTED_GOAL4_BASELINE_ROWS} "
         f"regressed-to-fc={n_lost_to_fc} regressed-to-wrong={n_changed_label} "
         f"(measurement-only; not a 0-tolerance gate) ✓")
    return n_preserved, n_lost_to_fc, n_changed_label


# ── G10: D's behavior on cleaned-NR-wrong (measurement, not gate) ──
def check_d_on_nr_wrongs(d_rows: list[dict]) -> tuple:
    """Measurement-only: count D's still-wrong / now-fc / now-correct on
    the 587 cleaned-NR-wrong subset. Returns the counts for G13 to
    cross-check against the report. Does NOT fail on residual wrongs —
    Goal 6a is measurement-only. Goal 5 audited D at 11 wrongs; that's
    expected. The SHIP_D_DIRECTLY flag handles the ship/no-ship call."""
    nr = json.load(open(NR_AUDIT_JSON, encoding="utf-8"))
    wrong_accns = {r["accession_8k"] for r in nr if r["final_verdict"] == "wrong"}
    if len(wrong_accns) != EXPECTED_NR_WRONG:
        fail(f"G10 cleaned-NR wrong count={len(wrong_accns)}; "
             f"expected {EXPECTED_NR_WRONG}", code=2)

    nr_truth = {r["accession_8k"]: (str(r["cleaned_audited_fy"]),
                                      str(r["cleaned_audited_q"]))
                 for r in nr if r["final_verdict"] == "wrong"}
    d_by_accn = {r["accession_8k"]: r for r in d_rows}

    n_still_wrong = 0
    n_now_fc = 0
    n_now_correct = 0
    for accn in wrong_accns:
        d = d_by_accn.get(accn)
        if d is None:
            fail(f"G10 cleaned-NR-wrong accession {accn} missing from D CSV",
                 code=2)
        truth_fy, truth_q = nr_truth[accn]
        if d["outcome"] == "FAIL_CLOSED":
            n_now_fc += 1
            continue
        if (d["fy"], d["q"]) == (truth_fy, truth_q):
            n_now_correct += 1
            continue
        n_still_wrong += 1

    info(f"G10 D on cleaned-NR-wrong (587 rows): "
         f"still-wrong={n_still_wrong} fail-closed={n_now_fc} now-correct={n_now_correct} "
         f"(measurement-only; not a 0-tolerance gate) ✓")
    return n_still_wrong, n_now_fc, n_now_correct


# ── G11: report exists with required tables + decision flag ─────────
def check_report() -> dict:
    """Returns the parsed DECISION_FLAG values from the report."""
    if not GOAL6A_REPORT.is_file():
        fail(f"G11 GOAL6A_REPORT.md missing: {GOAL6A_REPORT}")
    text = GOAL6A_REPORT.read_text(encoding="utf-8")
    if len(text) < 500:
        fail(f"G11 GOAL6A_REPORT.md too short ({len(text)} bytes)")
    required_keywords = [
        "Full historical", "Warm-start", "Cold-start", "Latest-per-ticker",
        # Derived percentages
        "DECISION_FLAG_D_WARM_START_CORRECT_PCT",
        "DECISION_FLAG_D_WARM_START_WRONG_PCT",
        "DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT_PCT",
        "DECISION_FLAG_D_LATEST_PER_TICKER_WRONG_PCT",
        # G9 measurement
        "DECISION_FLAG_D_GOAL4_BASELINE_PRESERVED",
        "DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_FC",
        "DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_WRONG",
        # G10 measurement
        "DECISION_FLAG_D_CLEANED_NR_WRONG_STILL_WRONG",
        "DECISION_FLAG_D_CLEANED_NR_WRONG_FAIL_CLOSED",
        "DECISION_FLAG_D_CLEANED_NR_WRONG_NOW_CORRECT",
        # Ship decision
        "DECISION_FLAG_SHIP_D_DIRECTLY",
        # 24 subset raw counts (D × 4 × 3)
        "DECISION_FLAG_D_FULL_HISTORICAL_CORRECT",
        "DECISION_FLAG_D_FULL_HISTORICAL_WRONG",
        "DECISION_FLAG_D_FULL_HISTORICAL_FC",
        "DECISION_FLAG_D_WARM_START_CORRECT",
        "DECISION_FLAG_D_WARM_START_WRONG",
        "DECISION_FLAG_D_WARM_START_FC",
        "DECISION_FLAG_D_COLD_START_CORRECT",
        "DECISION_FLAG_D_COLD_START_WRONG",
        "DECISION_FLAG_D_COLD_START_FC",
        "DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT",
        "DECISION_FLAG_D_LATEST_PER_TICKER_WRONG",
        "DECISION_FLAG_D_LATEST_PER_TICKER_FC",
        # 24 subset raw counts (E × 4 × 3)
        "DECISION_FLAG_E_FULL_HISTORICAL_CORRECT",
        "DECISION_FLAG_E_FULL_HISTORICAL_WRONG",
        "DECISION_FLAG_E_FULL_HISTORICAL_FC",
        "DECISION_FLAG_E_WARM_START_CORRECT",
        "DECISION_FLAG_E_WARM_START_WRONG",
        "DECISION_FLAG_E_WARM_START_FC",
        "DECISION_FLAG_E_COLD_START_CORRECT",
        "DECISION_FLAG_E_COLD_START_WRONG",
        "DECISION_FLAG_E_COLD_START_FC",
        "DECISION_FLAG_E_LATEST_PER_TICKER_CORRECT",
        "DECISION_FLAG_E_LATEST_PER_TICKER_WRONG",
        "DECISION_FLAG_E_LATEST_PER_TICKER_FC",
    ]
    missing = [k for k in required_keywords if k not in text]
    if missing:
        fail(f"G11 GOAL6A_REPORT.md missing keywords/sections: {missing}")

    flags = {}
    for k in ["DECISION_FLAG_D_WARM_START_CORRECT_PCT",
               "DECISION_FLAG_D_WARM_START_WRONG_PCT",
               "DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT_PCT",
               "DECISION_FLAG_D_LATEST_PER_TICKER_WRONG_PCT"]:
        m = re.search(rf"{re.escape(k)}\s*=\s*([0-9.]+)", text)
        if not m:
            fail(f"G11 cannot parse {k} from report")
        flags[k] = float(m.group(1))

    m = re.search(r"DECISION_FLAG_SHIP_D_DIRECTLY\s*=\s*[\"']?(yes|no)[\"']?",
                   text, re.IGNORECASE)
    if not m:
        fail("G11 cannot parse DECISION_FLAG_SHIP_D_DIRECTLY from report "
             "(expected 'yes' or 'no')")
    flags["DECISION_FLAG_SHIP_D_DIRECTLY"] = m.group(1).lower()

    info(f"G11 GOAL6A_REPORT.md: {len(text)} bytes, all flags parseable ✓")
    info(f"     warm-start D correct={flags['DECISION_FLAG_D_WARM_START_CORRECT_PCT']:.2f}% "
         f"wrong={flags['DECISION_FLAG_D_WARM_START_WRONG_PCT']:.2f}%")
    info(f"     latest-per-ticker D correct={flags['DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT_PCT']:.2f}% "
         f"wrong={flags['DECISION_FLAG_D_LATEST_PER_TICKER_WRONG_PCT']:.2f}%")
    info(f"     SHIP_D_DIRECTLY = {flags['DECISION_FLAG_SHIP_D_DIRECTLY']}")
    return flags


# ── G12: subset reconciliation ───────────────────────────────────────
def check_subset_reconciliation(d_rows: list[dict]) -> None:
    n_warm = sum(1 for r in d_rows if r["warm_start"].lower() == "true")
    n_cold = sum(1 for r in d_rows if r["warm_start"].lower() == "false")
    if n_warm + n_cold != EXPECTED_TOTAL_SCOREABLE:
        fail(f"G12 warm_start ({n_warm}) + cold_start ({n_cold}) "
             f"= {n_warm+n_cold}; expected {EXPECTED_TOTAL_SCOREABLE}")

    n_latest = sum(1 for r in d_rows if r["latest_per_ticker"].lower() == "true")
    unique_tickers = len({r["ticker"] for r in d_rows})
    if n_latest != unique_tickers:
        fail(f"G12 latest_per_ticker count={n_latest} != unique tickers "
             f"({unique_tickers}). Each ticker must contribute exactly one "
             f"latest-per-ticker row.")
    info(f"G12 subset reconcile: warm={n_warm} + cold={n_cold} = {n_warm+n_cold} "
         f"({EXPECTED_TOTAL_SCOREABLE}); latest_per_ticker={n_latest} == "
         f"unique tickers ({unique_tickers}) ✓")


# ── G13: aggregate counts in report match per-row recompute ─────────
def _parse_int_flag(text: str, key: str) -> int:
    m = re.search(rf"^\s*{re.escape(key)}\s*=\s*([0-9]+)\s*$", text, re.MULTILINE)
    if not m:
        fail(f"G13 cannot parse {key} from GOAL6A_REPORT.md "
             f"(expected line `{key} = <int>`)")
    return int(m.group(1))


def _parse_str_flag(text: str, key: str) -> str:
    m = re.search(rf"^\s*{re.escape(key)}\s*=\s*[\"']?([A-Za-z]+)[\"']?\s*$",
                   text, re.MULTILINE)
    if not m:
        fail(f"G13 cannot parse {key} from GOAL6A_REPORT.md")
    return m.group(1).lower()


# Subset predicates for recompute. Order matches expected DECISION_FLAG
# subset names (FULL_HISTORICAL, WARM_START, COLD_START, LATEST_PER_TICKER).
_SUBSETS = [
    ("FULL_HISTORICAL", lambda r: True),
    ("WARM_START", lambda r: r["warm_start"].lower() == "true"),
    ("COLD_START", lambda r: r["warm_start"].lower() == "false"),
    ("LATEST_PER_TICKER", lambda r: r["latest_per_ticker"].lower() == "true"),
]


def _recompute_subset(rows: list[dict], predicate) -> tuple:
    correct = wrong = fc = 0
    for r in rows:
        if not predicate(r):
            continue
        if r["outcome"] == "FAIL_CLOSED":
            fc += 1
        elif r["outcome"] == "AUTO_OK":
            if r["correct"].lower() == "true":
                correct += 1
            else:
                wrong += 1
    return correct, wrong, fc


def check_report_aggregates(d_rows: list[dict],
                             e_rows: list[dict],
                             *,
                             g9_counts: tuple = None,
                             g10_counts: tuple = None) -> None:
    """G13: every reported number is parsed by exact DECISION_FLAG key
    and exact-matched against the verifier's runtime recompute. No
    permissive integer scanning. Also enforces the SHIP_D_DIRECTLY rule
    derivation."""
    text = GOAL6A_REPORT.read_text(encoding="utf-8")

    # ── 24 subset raw-count flags (D × 4 subsets, E × 4 subsets) ──
    for cand_label, rows in (("D", d_rows), ("E", e_rows)):
        for subset_label, pred in _SUBSETS:
            r_correct = _parse_int_flag(
                text, f"DECISION_FLAG_{cand_label}_{subset_label}_CORRECT")
            r_wrong = _parse_int_flag(
                text, f"DECISION_FLAG_{cand_label}_{subset_label}_WRONG")
            r_fc = _parse_int_flag(
                text, f"DECISION_FLAG_{cand_label}_{subset_label}_FC")
            c, w, f = _recompute_subset(rows, pred)
            if (r_correct, r_wrong, r_fc) != (c, w, f):
                fail(f"G13 {cand_label}/{subset_label} subset count mismatch:\n"
                     f"  report:    correct={r_correct} wrong={r_wrong} fc={r_fc}\n"
                     f"  recompute: correct={c} wrong={w} fc={f}")

    # ── G9 measurement flags ──
    if g9_counts is not None:
        n_pres, n_fc, n_chg = g9_counts
        rep_pres = _parse_int_flag(text, "DECISION_FLAG_D_GOAL4_BASELINE_PRESERVED")
        rep_fc = _parse_int_flag(text, "DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_FC")
        rep_chg = _parse_int_flag(text, "DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_WRONG")
        if (rep_pres, rep_fc, rep_chg) != (n_pres, n_fc, n_chg):
            fail(f"G13 G9 baseline measurement mismatch:\n"
                 f"  report:    preserved={rep_pres} fc={rep_fc} regressed_wrong={rep_chg}\n"
                 f"  recompute: preserved={n_pres} fc={n_fc} regressed_wrong={n_chg}")

    # ── G10 measurement flags ──
    if g10_counts is not None:
        n_wrong, n_fc, n_correct = g10_counts
        rep_wrong = _parse_int_flag(text, "DECISION_FLAG_D_CLEANED_NR_WRONG_STILL_WRONG")
        rep_fc = _parse_int_flag(text, "DECISION_FLAG_D_CLEANED_NR_WRONG_FAIL_CLOSED")
        rep_correct = _parse_int_flag(text, "DECISION_FLAG_D_CLEANED_NR_WRONG_NOW_CORRECT")
        if (rep_wrong, rep_fc, rep_correct) != (n_wrong, n_fc, n_correct):
            fail(f"G13 G10 cleaned-NR-wrong measurement mismatch:\n"
                 f"  report:    still-wrong={rep_wrong} fc={rep_fc} correct={rep_correct}\n"
                 f"  recompute: still-wrong={n_wrong} fc={n_fc} correct={n_correct}")

    # ── SHIP_D_DIRECTLY rule enforcement ──
    # Derive expected_ship from D's WARM_START and LATEST_PER_TICKER raw counts.
    d_warm_correct, d_warm_wrong, d_warm_fc = _recompute_subset(
        d_rows, dict(_SUBSETS)["WARM_START"])
    d_latest_correct, d_latest_wrong, d_latest_fc = _recompute_subset(
        d_rows, dict(_SUBSETS)["LATEST_PER_TICKER"])
    d_warm_total = d_warm_correct + d_warm_wrong + d_warm_fc
    d_latest_total = d_latest_correct + d_latest_wrong + d_latest_fc
    if d_warm_total == 0 or d_latest_total == 0:
        fail("G13 SHIP rule: D warm-start or latest-per-ticker subset "
             "has zero rows; cannot derive expected_ship.")
    warm_correct_pct = 100.0 * d_warm_correct / d_warm_total
    warm_wrong_pct = 100.0 * d_warm_wrong / d_warm_total
    latest_correct_pct = 100.0 * d_latest_correct / d_latest_total
    latest_wrong_pct = 100.0 * d_latest_wrong / d_latest_total
    expected_ship = (
        "yes" if (warm_correct_pct >= 95.0
                  and warm_wrong_pct < 1.0
                  and latest_correct_pct >= 95.0
                  and latest_wrong_pct < 1.0)
        else "no"
    )
    reported_ship = _parse_str_flag(text, "DECISION_FLAG_SHIP_D_DIRECTLY")
    if reported_ship != expected_ship:
        fail(f"G13 SHIP_D_DIRECTLY rule violation:\n"
             f"  report:   {reported_ship!r}\n"
             f"  expected: {expected_ship!r}\n"
             f"  derived from D rates: "
             f"warm_correct={warm_correct_pct:.2f}% (≥95? {warm_correct_pct >= 95.0}), "
             f"warm_wrong={warm_wrong_pct:.2f}% (<1? {warm_wrong_pct < 1.0}), "
             f"latest_correct={latest_correct_pct:.2f}% (≥95? {latest_correct_pct >= 95.0}), "
             f"latest_wrong={latest_wrong_pct:.2f}% (<1? {latest_wrong_pct < 1.0})")
    info(f"G13 24 subset flags + 6 measurement flags + SHIP_D_DIRECTLY rule "
         f"all match recompute exactly ✓")


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Goal 6a measurement verifier (hand-written; do not modify)."
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Iteration shortcut: G8 samples 50 rows. Other gates always run "
             "fully because they're cheap.",
    )
    args = parser.parse_args()
    full_mode = not args.fast

    mode_label = "FULL (canonical sign-off)" if full_mode else "FAST (iteration)"
    print(f"=== Goal 6a verifier (hand-written, do not modify) — {mode_label} ===")
    print(f"Production locked: {QI_PATH.name}, {ORCHESTRATOR_PATH.name}, etc.")
    print(f"Verifier file:     {Path(__file__).resolve()}")
    print()

    check_evidence_git_clean()           # G1+G2
    check_no_production_changes()        # G3
    check_research_file_isolation()      # G4
    check_e_anti_leak()                  # G5
    d_rows = check_d_csv()               # G6
    e_rows = check_e_csv(d_rows)         # G7
    check_determinism(d_rows, e_rows)    # G8 (TRUE rerun via Neo4j)
    g9_counts = check_goal4_baseline_measurement(d_rows)   # G9 (measurement)
    g10_counts = check_d_on_nr_wrongs(d_rows)              # G10 (measurement)
    flags = check_report()               # G11
    check_subset_reconciliation(d_rows)  # G12
    check_report_aggregates(d_rows, e_rows,
                             g9_counts=g9_counts,
                             g10_counts=g10_counts)        # G13

    print()
    info("=" * 60)
    info(f"ALL CHECKS PASSED — Goal 6a measurement verified")
    info(f"  warm-start D: correct={flags['DECISION_FLAG_D_WARM_START_CORRECT_PCT']:.2f}%, "
         f"wrong={flags['DECISION_FLAG_D_WARM_START_WRONG_PCT']:.2f}%")
    info(f"  latest-per-ticker D: correct={flags['DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT_PCT']:.2f}%, "
         f"wrong={flags['DECISION_FLAG_D_LATEST_PER_TICKER_WRONG_PCT']:.2f}%")
    info(f"  → SHIP_D_DIRECTLY = {flags['DECISION_FLAG_SHIP_D_DIRECTLY']}")
    info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
