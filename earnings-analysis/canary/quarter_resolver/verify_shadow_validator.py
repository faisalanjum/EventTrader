#!/usr/bin/env python3
"""
verify_shadow_validator.py — Independent verifier for Goal 2's output.

HAND-WRITTEN BY HUMANS (NOT BY THE AGENT) to prevent self-rubber-stamping.
This script decides whether Goal 2 is complete; the agent's job is to produce
output that passes THIS verifier without modifying it.

DESIGN INVARIANTS (per .claude/plans/quarter-identity-resolver.md):

  Goal 2 measures the production resolver against the Goal 1 corpus AND
  evaluates >=2 candidate replacement algorithms. Outputs:

    1. shadow_audit.csv          — production resolver run on full universe
    2. candidate_algorithms.py   — executable candidate implementations
    3. candidate_audit.csv       — each candidate run on full universe
    4. GOAL2_REPORT.md           — analysis + recommended candidate

  CRITICAL SCORING RULES:

  GT rows (9,909 — have known fy/q label):
    * production_quarter_verdict / candidate_quarter_verdict ∈ {AGREE, BUG, NO_RESOLUTION}
    * production_safety_verdict  / candidate_safety_verdict  ∈ {OK, WRONG_AUTO_WROTE}
        OK: resolved correctly (matches corpus fy/q)
        WRONG_AUTO_WROTE: resolved confidently but wrong (the FCX harm)

  NR rows (922 — no oracle for fy/q, only safety policy is scoreable):
    * production_quarter_verdict / candidate_quarter_verdict = N_A (always)
    * production_safety_verdict  / candidate_safety_verdict  ∈ {
          CORRECT_FAIL_CLOSED,    ← resolver returned NEEDS_REVIEW / unresolved
          AUTO_ON_UNCERTAIN_ROW,  ← auto-resolved on a row we have no oracle for
                                    (NOT credit; reported separately)
          WRONG_AUTO_WROTE        ← FCX harm fingerprint:
                                    NR.reason == "not_same_event_periodic"
                                    AND resolver.source ∈ {matched_periodic_xbrl,
                                                            matched_periodic_fiscal_math}
                                    (resolver trusted the previous quarter's periodic)
      }
    NO `OK` value for NR rows. Safety credit only for CORRECT_FAIL_CLOSED.

EXIT CODES:
  0  = corpus passes all checks; Goal 2 verified done
  1  = corpus has fatal violations; Goal 2 not done
  2  = verifier itself failed (Neo4j / missing files / env / tampered file)

USAGE:
  cd /home/faisal/EventMarketDB
  # Iteration mode (fast — used during /goal Ralph loops):
  venv/bin/python earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py
  # Final sign-off mode (bulletproof — REQUIRED before Goal 2 is declared done):
  venv/bin/python earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py --full

CHECKS PERFORMED (in order; first failure exits 1):
  S1.  Verifier file is git-clean (catches Codex-tampering)
  S2.  All required deliverables exist + non-empty (shadow_audit.csv,
       candidate_algorithms.py, candidate_audit.csv, GOAL2_REPORT.md)
  S3.  shadow_audit.csv schema EXACTLY matches REQUIRED_COLUMNS_SHADOW
  S4.  candidate_audit.csv schema EXACTLY matches REQUIRED_COLUMNS_CANDIDATE
  S5.  No duplicate accession_8k inside shadow_audit.csv (per row)
  S6.  Universe coverage: shadow_audit covers ALL 10,831 corpus rows
       (9,909 GT + 922 NR), no overlap, no missing
  S6b. Independent production-resolver re-derivation. TWO MODES:
       - DEFAULT (stratified, fast): 100% of NR rows where
         reason=='not_same_event_periodic' (FCX harm class) + deterministic
         stride samples of GT and other-NR. Used during /goal Ralph loops
         for speed. Evadable for non-FCX rows by an adversarial agent that
         reads this verifier — acceptable for iteration, NOT for final
         sign-off.
       - --full (bulletproof, REQUIRED for final Goal 2 sign-off): runs
         resolve_quarter_info() against ALL 10,831 corpus rows. Removes the
         residual evasion concern.
       Both modes call resolve_quarter_info() and assert production_fy/q/
       source in shadow_audit.csv match what the resolver actually returns.
  S7.  Per-row invariants on shadow_audit (verdict enums + INDEPENDENT
       re-derivation of production_quarter_verdict & production_safety_verdict
       from rules; CSV claims must match computed verdicts).
       NR rows have quarter_verdict=N_A; GT rows safety∈{OK,WRONG_AUTO_WROTE};
       NR rows safety∈{CORRECT_FAIL_CLOSED,AUTO_ON_UNCERTAIN_ROW,WRONG_AUTO_WROTE}.
  S8.  candidate_algorithms.py has >=2 distinct candidate functions named
       candidate_<name>(row_context: dict) -> dict; each function importable
  S9.  Each candidate is run independently on every corpus row by THIS verifier
       (NOT trusting candidate_audit.csv). Each candidate sees a SANITIZED
       row_context (oracle fields fy_xbrl/q_xbrl/fy_math/q_math/agreement/
       reason are stripped — candidates cannot cheat by echoing the corpus's
       answer). The verifier additionally re-derives candidate_quarter_verdict
       and candidate_safety_verdict from the candidate's output and asserts
       the CSV matches.
  S10. FCX harm subset (STRICT, ALL CANDIDATES): for each candidate, count
       WRONG_AUTO_WROTE on the (NR.reason == "not_same_event_periodic") subset.
       Hard fail if ANY candidate has > 0 WRONG_AUTO_WROTE on this subset.
       This is stricter than the recommended-only rule below: NO submitted
       candidate (winner OR loser) may emit the FCX harm fingerprint.
  S10b. Recommended candidate (named in GOAL2_REPORT.md) — ADDITIONAL rules:
       (a) name must exist as a function in candidate_algorithms.py
       (b) name must have rows in candidate_audit.csv (>=1)
       (c) ZERO AUTO_OK / AUTO_ON_UNCERTAIN_ROW on not_same_event_periodic
           subset (winner must FAIL CLOSED on FCX-shape rows, not merely
           avoid the harmful auto-write).
  S11. GOAL2_REPORT.md is non-empty and references both production baseline
       and >=2 candidates

This module re-uses production helpers (resolve_quarter_info, period_to_fiscal,
parse_xbrl_fiscal_identity, should_use_xbrl_fiscal, XBRL_DENY_PERIODIC_ACCESSIONS,
get_fye_month) but applies them independently of build_corpus.py and
candidate_algorithms.py.
"""
from __future__ import annotations
import argparse
import csv
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
SHADOW_AUDIT_PATH = _HERE / "shadow_audit.csv"
CANDIDATE_AUDIT_PATH = _HERE / "candidate_audit.csv"
CANDIDATE_ALGORITHMS_PATH = _HERE / "candidate_algorithms.py"
GOAL2_REPORT_PATH = _HERE / "GOAL2_REPORT.md"
GROUND_TRUTH_PATH = _HERE / "ground_truth.csv"
NEEDS_REVIEW_PATH = _HERE / "needs_review.csv"
PROJECT_ROOT = _HERE.parents[2]

# ── Production helpers (re-used independently) ───────────────────────
sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

try:
    from fye_month import get_fye_month  # noqa: F401  (used by candidates)
    from fiscal_math import period_to_fiscal  # noqa: F401
    from get_quarterly_filings import (  # noqa: F401
        parse_xbrl_fiscal_identity,
        should_use_xbrl_fiscal,
        XBRL_DENY_PERIODIC_ACCESSIONS,
    )
except ImportError as e:
    print(f"VERIFIER INFRA ERROR: cannot import production module: {e}", file=sys.stderr)
    sys.exit(2)

# ── Schema (locked, ORDERED) ─────────────────────────────────────────
REQUIRED_COLUMNS_SHADOW = [
    "accession_8k",
    "ticker",
    "corpus_label",          # "ground_truth" | "needs_review:<reason>"
    "corpus_fy",             # GT only (NR rows leave blank)
    "corpus_q",              # GT only
    "production_fy",         # what production resolver returned (may be blank if no_resolution)
    "production_q",
    "production_source",     # quarter_identity_source string
    "production_quarter_verdict",   # AGREE | BUG | NO_RESOLUTION | N_A
    "production_safety_verdict",    # OK | WRONG_AUTO_WROTE | CORRECT_FAIL_CLOSED | AUTO_ON_UNCERTAIN_ROW
]

REQUIRED_COLUMNS_CANDIDATE = [
    "accession_8k",
    "ticker",
    "corpus_label",
    "candidate_name",
    "candidate_fy",
    "candidate_q",
    "candidate_source",
    "candidate_safety_action",     # AUTO_OK | NEEDS_REVIEW | FAIL_CLOSED | NO_RESOLUTION
    "candidate_quarter_verdict",   # AGREE | BUG | NO_RESOLUTION | N_A
    "candidate_safety_verdict",    # OK | WRONG_AUTO_WROTE | CORRECT_FAIL_CLOSED | AUTO_ON_UNCERTAIN_ROW
]

# Oracle fields (verifier strips these before passing row to candidate functions
# — candidates MUST NOT see ground-truth answer fields, otherwise they could
# trivially echo the corpus's claim and pass with 100% accuracy).
_ORACLE_FIELDS = {
    "fy_xbrl", "q_xbrl",
    "fy_math", "q_math",
    "agreement",
    "reason",                # NR-only; tells the candidate the corpus already classified the row
}

# Fields candidates MAY see (raw input the runtime resolver would have)
_RUNTIME_ROW_FIELDS = {
    "accession_8k", "ticker", "filed_8k",
    "period_of_report", "fye_month",
    "matched_accession_periodic", "periodic_created", "form_type_periodic",
}


def _sanitize_for_candidate(row: dict) -> dict:
    """Strip oracle fields. Candidates only see raw runtime-shaped input."""
    return {k: v for k, v in row.items() if k in _RUNTIME_ROW_FIELDS}


# Production-resolver re-derivation strata (S6b)
#  - 100% of NR rows where reason == 'not_same_event_periodic' (FCX-shape;
#    the harm class we MUST verify the production CSV did not fake)
#  - deterministic stride sample of remaining GT and NR rows
S6B_GT_SAMPLE_N = 100      # deterministic stride sample of GT
S6B_OTHER_NR_SAMPLE_N = 100  # deterministic stride sample of NR rows whose
                             # reason != 'not_same_event_periodic'

VALID_PROD_QUARTER_VERDICTS = {"AGREE", "BUG", "NO_RESOLUTION", "N_A"}
VALID_GT_SAFETY = {"OK", "WRONG_AUTO_WROTE"}
VALID_NR_SAFETY = {"CORRECT_FAIL_CLOSED", "AUTO_ON_UNCERTAIN_ROW", "WRONG_AUTO_WROTE"}
VALID_SAFETY_ACTIONS = {"AUTO_OK", "NEEDS_REVIEW", "FAIL_CLOSED", "NO_RESOLUTION"}
VALID_QUARTERS = {"Q1", "Q2", "Q3", "Q4"}

# Required ancillary deliverables
REQUIRED_DELIVERABLES = (
    "shadow_audit.csv",
    "candidate_algorithms.py",
    "candidate_audit.csv",
    "GOAL2_REPORT.md",
)

MIN_CANDIDATES = 2


# ── Output helpers ────────────────────────────────────────────────────
def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


# ── S1: git freeze check ─────────────────────────────────────────────
def check_verifier_git_clean() -> None:
    rel_path = str(Path(__file__).resolve().relative_to(PROJECT_ROOT))
    try:
        r = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", rel_path],
            cwd=str(PROJECT_ROOT), capture_output=True, timeout=30,
        )
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        fail(f"git diff check failed: {e}", code=2)
    if r.returncode != 0:
        fail(
            f"Verifier file has uncommitted changes vs HEAD: {rel_path}\n"
            f"This blocks completion — Codex may have modified the verifier.",
            code=2,
        )
    r = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel_path],
        cwd=str(PROJECT_ROOT), capture_output=True, timeout=10,
    )
    if r.returncode != 0:
        fail(f"Verifier file is not git-committed: {rel_path}", code=2)
    info("S1 git-clean: verifier matches committed version ✓")


# ── S2/S3/S4: file + schema checks ────────────────────────────────────
def check_files_exist() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Return (shadow_rows, candidate_rows, gt_rows, nr_rows)."""
    for fname in REQUIRED_DELIVERABLES:
        path = _HERE / fname
        if not path.is_file():
            fail(f"Required deliverable missing: {path}")
        if path.stat().st_size == 0:
            fail(f"Required deliverable is empty: {path}")
    if not GROUND_TRUTH_PATH.is_file():
        fail(f"ground_truth.csv missing — Goal 1 must be in place", code=2)
    if not NEEDS_REVIEW_PATH.is_file():
        fail(f"needs_review.csv missing — Goal 1 must be in place", code=2)
    info(f"S2 deliverables present + non-empty: {list(REQUIRED_DELIVERABLES)} ✓")

    with open(SHADOW_AUDIT_PATH, encoding="utf-8") as f:
        shadow_rows = list(csv.DictReader(f))
    with open(CANDIDATE_AUDIT_PATH, encoding="utf-8") as f:
        candidate_rows = list(csv.DictReader(f))
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        gt_rows = list(csv.DictReader(f))
    with open(NEEDS_REVIEW_PATH, encoding="utf-8") as f:
        nr_rows = list(csv.DictReader(f))

    if not shadow_rows:
        fail("shadow_audit.csv has no data rows")
    # Read the actual header line directly to enforce ORDERED schema match
    with open(SHADOW_AUDIT_PATH, encoding="utf-8") as f:
        actual_shadow_cols = list(csv.reader(f))[0] if SHADOW_AUDIT_PATH.exists() else []
    if actual_shadow_cols != REQUIRED_COLUMNS_SHADOW:
        fail(
            f"S3 shadow_audit.csv columns not in expected order/set:\n"
            f"  expected: {REQUIRED_COLUMNS_SHADOW}\n"
            f"  actual:   {actual_shadow_cols}"
        )
    info(f"S3 shadow_audit.csv schema: {len(REQUIRED_COLUMNS_SHADOW)} columns in correct order ✓")

    if not candidate_rows:
        fail("candidate_audit.csv has no data rows")
    with open(CANDIDATE_AUDIT_PATH, encoding="utf-8") as f:
        actual_cand_cols = list(csv.reader(f))[0] if CANDIDATE_AUDIT_PATH.exists() else []
    if actual_cand_cols != REQUIRED_COLUMNS_CANDIDATE:
        fail(
            f"S4 candidate_audit.csv columns not in expected order/set:\n"
            f"  expected: {REQUIRED_COLUMNS_CANDIDATE}\n"
            f"  actual:   {actual_cand_cols}"
        )
    info(f"S4 candidate_audit.csv schema: {len(REQUIRED_COLUMNS_CANDIDATE)} columns in correct order ✓")

    return shadow_rows, candidate_rows, gt_rows, nr_rows


# ── S5: shadow_audit no duplicates ───────────────────────────────────
def check_shadow_no_duplicates(shadow_rows: list[dict]) -> None:
    from collections import Counter
    accs = [r["accession_8k"] for r in shadow_rows]
    counts = Counter(accs)
    dups = [a for a, c in counts.items() if c > 1]
    if dups:
        fail(f"S5 shadow_audit has {len(dups)} duplicate accession_8k. Sample: {dups[:5]}")
    info(f"S5 shadow_audit: {len(accs)} unique accessions ✓")


# ── S6: universe coverage ────────────────────────────────────────────
def check_universe_coverage(
    shadow_rows: list[dict], gt_rows: list[dict], nr_rows: list[dict]
) -> None:
    expected = {r["accession_8k"] for r in gt_rows} | {r["accession_8k"] for r in nr_rows}
    actual = {r["accession_8k"] for r in shadow_rows}
    missing = expected - actual
    extra = actual - expected
    if missing:
        fail(
            f"S6 shadow_audit missing {len(missing)} corpus accessions. "
            f"Sample: {sorted(missing)[:5]}"
        )
    if extra:
        fail(
            f"S6 shadow_audit has {len(extra)} accessions not in corpus. "
            f"Sample: {sorted(extra)[:5]}"
        )
    info(
        f"S6 universe coverage: shadow_audit covers all {len(expected)} corpus rows "
        f"({len(gt_rows)} GT + {len(nr_rows)} NR) ✓"
    )


# ── S7: per-row invariants on shadow_audit (verdicts RE-DERIVED, not just enum-checked) ──
def _compute_production_quarter_verdict(*, is_gt: bool, prod_fy: str, prod_q: str,
                                         corpus_fy: str, corpus_q: str) -> str:
    """Independently compute what the verdict SHOULD be."""
    if not is_gt:
        return "N_A"
    if not prod_fy and not prod_q:
        return "NO_RESOLUTION"
    if prod_fy == corpus_fy and prod_q == corpus_q:
        return "AGREE"
    return "BUG"


def _compute_production_safety_verdict(*, is_gt: bool, qv: str,
                                         prod_fy: str, prod_q: str,
                                         prod_source: str,
                                         nr_reason: str | None) -> str:
    """Independently compute what the safety verdict SHOULD be.
    GT: OK if AGREE or NO_RESOLUTION; WRONG_AUTO_WROTE if BUG.
    NR: CORRECT_FAIL_CLOSED if production returned no quarter (blank fy AND
                              blank q) — quarter_verdict is always N_A on NR
                              so we cannot rely on `qv == NO_RESOLUTION` here;
        WRONG_AUTO_WROTE if FCX-shape (reason==not_same_event_periodic AND
                                       source in matched_periodic_*);
        AUTO_ON_UNCERTAIN_ROW otherwise (resolved confidently on uncertain row,
                                          but not the FCX harm fingerprint).
    """
    if is_gt:
        if qv in ("AGREE", "NO_RESOLUTION"):
            return "OK"
        if qv == "BUG":
            return "WRONG_AUTO_WROTE"
        return "OK"  # defensive (shouldn't reach)
    # NR — quarter_verdict is N_A so detect fail-closed via empty fy/q
    if not prod_fy and not prod_q:
        return "CORRECT_FAIL_CLOSED"
    # production resolved confidently on an NR row
    if (nr_reason == "not_same_event_periodic"
            and prod_source in ("matched_periodic_xbrl", "matched_periodic_fiscal_math")):
        return "WRONG_AUTO_WROTE"
    return "AUTO_ON_UNCERTAIN_ROW"


# ── Candidate-verdict re-derivation helpers (mirror production rules but
# ── operate on the candidate's own safety_action + source/fy/q output) ──
_FAIL_CLOSED_ACTIONS = {"NEEDS_REVIEW", "FAIL_CLOSED", "NO_RESOLUTION"}


def _compute_candidate_quarter_verdict(*, is_gt: bool, cand_fy: str, cand_q: str,
                                         corpus_fy: str, corpus_q: str,
                                         safety_action: str) -> str:
    """For GT rows: AGREE/BUG/NO_RESOLUTION based on candidate's auto-resolution.
    For NR rows: always N_A (no oracle to check against).

    A candidate that fails closed (safety_action in {NEEDS_REVIEW, FAIL_CLOSED,
    NO_RESOLUTION}) on a GT row is scored NO_RESOLUTION (safe abstain), not BUG.
    AUTO_OK with empty fy/q is treated as NO_RESOLUTION (defensive).
    """
    if not is_gt:
        return "N_A"
    if safety_action in _FAIL_CLOSED_ACTIONS:
        return "NO_RESOLUTION"
    # AUTO_OK
    if not cand_fy and not cand_q:
        return "NO_RESOLUTION"
    if cand_fy == corpus_fy and cand_q == corpus_q:
        return "AGREE"
    return "BUG"


def _compute_candidate_safety_verdict(*, is_gt: bool, qv: str, cand_source: str,
                                        cand_safety_action: str,
                                        nr_reason: str | None) -> str:
    """GT: OK if AGREE/NO_RESOLUTION; WRONG_AUTO_WROTE if BUG.
    NR: CORRECT_FAIL_CLOSED if candidate explicitly fails closed;
        WRONG_AUTO_WROTE if candidate AUTO_OK on FCX-shape NR row
                         (reason==not_same_event_periodic AND source claims
                         it trusted the matched periodic);
        AUTO_ON_UNCERTAIN_ROW otherwise (candidate AUTO_OK on uncertain NR row
                                          but not the FCX harm fingerprint).
    """
    if is_gt:
        if qv in ("AGREE", "NO_RESOLUTION"):
            return "OK"
        if qv == "BUG":
            return "WRONG_AUTO_WROTE"
        return "OK"  # defensive
    # NR
    if cand_safety_action in _FAIL_CLOSED_ACTIONS:
        return "CORRECT_FAIL_CLOSED"
    # candidate AUTO_OK on NR row
    if (nr_reason == "not_same_event_periodic"
            and cand_source in ("matched_periodic_xbrl", "matched_periodic_fiscal_math")):
        return "WRONG_AUTO_WROTE"
    return "AUTO_ON_UNCERTAIN_ROW"


def check_shadow_per_row(shadow_rows: list[dict], gt_rows: list[dict], nr_rows: list[dict]) -> None:
    gt_set = {r["accession_8k"] for r in gt_rows}
    nr_set = {r["accession_8k"] for r in nr_rows}
    nr_reason_by_accn = {r["accession_8k"]: r.get("reason", "") for r in nr_rows}
    errors: list[str] = []

    for i, row in enumerate(shadow_rows):
        accn = row.get("accession_8k", f"<row {i}>")
        is_gt = accn in gt_set
        is_nr = accn in nr_set

        # corpus_label correctness
        cl = row.get("corpus_label", "")
        if is_gt and cl != "ground_truth":
            errors.append(f"S7 row {i} ({accn}): GT row has corpus_label={cl!r} (expected 'ground_truth')")
        if is_nr and not cl.startswith("needs_review:"):
            errors.append(f"S7 row {i} ({accn}): NR row has corpus_label={cl!r} (expected 'needs_review:<reason>')")

        # Re-derive verdicts independently from rules
        # Find corpus row to get corpus_fy/q
        gt_row = next((r for r in gt_rows if r["accession_8k"] == accn), None)
        corpus_fy = (gt_row.get("fy_xbrl", "") if gt_row else "").strip()
        corpus_q = (gt_row.get("q_xbrl", "") if gt_row else "").strip()
        prod_fy = (row.get("production_fy", "") or "").strip()
        prod_q = (row.get("production_q", "") or "").strip()
        prod_source = (row.get("production_source", "") or "").strip()
        nr_reason = nr_reason_by_accn.get(accn) if is_nr else None

        expected_qv = _compute_production_quarter_verdict(
            is_gt=is_gt, prod_fy=prod_fy, prod_q=prod_q,
            corpus_fy=corpus_fy, corpus_q=corpus_q,
        )
        expected_sv = _compute_production_safety_verdict(
            is_gt=is_gt,
            qv=expected_qv,
            prod_fy=prod_fy,
            prod_q=prod_q,
            prod_source=prod_source,
            nr_reason=nr_reason,
        )

        actual_qv = row.get("production_quarter_verdict", "")
        actual_sv = row.get("production_safety_verdict", "")

        # Enum membership
        if actual_qv not in VALID_PROD_QUARTER_VERDICTS:
            errors.append(f"S7 row {i} ({accn}): production_quarter_verdict={actual_qv!r}")
        if is_gt and actual_sv not in VALID_GT_SAFETY:
            errors.append(
                f"S7 row {i} ({accn}) GT: production_safety_verdict={actual_sv!r} "
                f"(must be one of {VALID_GT_SAFETY})"
            )
        if is_nr and actual_sv not in VALID_NR_SAFETY:
            errors.append(
                f"S7 row {i} ({accn}) NR: production_safety_verdict={actual_sv!r} "
                f"(must be one of {VALID_NR_SAFETY})"
            )

        # CORRECTNESS — re-derived rules must match CSV claims
        if actual_qv != expected_qv:
            errors.append(
                f"S7 row {i} ({accn}) quarter_verdict mismatch: csv={actual_qv!r} "
                f"computed={expected_qv!r} (prod_fy={prod_fy} prod_q={prod_q} "
                f"corpus_fy={corpus_fy} corpus_q={corpus_q})"
            )
        if actual_sv != expected_sv:
            errors.append(
                f"S7 row {i} ({accn}) safety_verdict mismatch: csv={actual_sv!r} "
                f"computed={expected_sv!r} (qv={expected_qv} source={prod_source} "
                f"nr_reason={nr_reason})"
            )

    if errors:
        for e in errors[:25]:
            print(f"  {e}")
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more")
        fail(f"S7 shadow_audit per-row: {len(errors)} violations")
    info(f"S7 shadow_audit per-row + verdict-correctness: {len(shadow_rows)} rows, 0 violations ✓")


# ── S6b: independent production-resolver re-derivation ──────────────
def check_production_sample_rederivation(
    shadow_rows: list[dict], gt_rows: list[dict], nr_rows: list[dict],
    *, full: bool = False,
) -> None:
    """Independent re-derivation of production resolver. Two modes:

    Default (stratified): fast, used during /goal iteration.
      - 100% of NR rows where reason == 'not_same_event_periodic' (FCX-shape)
      - deterministic stride sample of GT rows (S6B_GT_SAMPLE_N)
      - deterministic stride sample of other-reason NR rows (S6B_OTHER_NR_SAMPLE_N)

    --full: bulletproof, REQUIRED for final Goal 2 sign-off.
      - Runs resolve_quarter_info() against ALL 10,831 corpus rows.
      - Removes the residual evasion concern (Codex could read this verifier
        and selectively populate only the stratified sample positions).
      - Slower (Neo4j roundtrips × 10,831).

    The FCX-shape stratum is always exhaustive in stratified mode: this is the
    harm class we MUST prove the production CSV did not fake. The --full mode
    makes the proof complete across all rows.
    """
    try:
        from quarter_identity import resolve_quarter_info
    except ImportError as e:
        fail(f"S6b cannot import resolve_quarter_info: {e}", code=2)

    shadow_by_accn = {r["accession_8k"]: r for r in shadow_rows}

    if full:
        sample_accns = sorted(shadow_by_accn.keys())
        info(
            f"S6b FULL production re-derivation: ALL {len(sample_accns)} corpus rows. "
            f"This is the bulletproof gate; expect Neo4j roundtrip × N runtime."
        )
    else:
        nr_fcx = sorted(
            r["accession_8k"] for r in nr_rows
            if r.get("reason") == "not_same_event_periodic"
        )
        nr_other_sorted = sorted(
            r["accession_8k"] for r in nr_rows
            if r.get("reason") != "not_same_event_periodic"
        )
        gt_sorted = sorted(r["accession_8k"] for r in gt_rows)

        def _stride(seq: list[str], k: int) -> list[str]:
            if not seq or k <= 0:
                return []
            if len(seq) <= k:
                return list(seq)
            step = len(seq) / k
            return [seq[int(i * step)] for i in range(k)]

        gt_pick = _stride(gt_sorted, S6B_GT_SAMPLE_N)
        nr_other_pick = _stride(nr_other_sorted, S6B_OTHER_NR_SAMPLE_N)
        sample_accns = list(dict.fromkeys(nr_fcx + gt_pick + nr_other_pick))

        info(
            f"S6b stratified production re-derivation: {len(nr_fcx)} FCX-shape NR + "
            f"{len(gt_pick)} GT (stride/{S6B_GT_SAMPLE_N}) + {len(nr_other_pick)} "
            f"other-NR (stride/{S6B_OTHER_NR_SAMPLE_N}) = {len(sample_accns)} unique rows. "
            f"For final sign-off, re-run with --full to verify all 10,831 rows."
        )

    mismatches: list[str] = []
    n_called = 0
    for accn in sample_accns:
        r = shadow_by_accn.get(accn)
        if r is None:
            mismatches.append(f"S6b {accn}: not in shadow_audit.csv (S6 should have caught this)")
            continue
        ticker = r["ticker"]
        try:
            qi = resolve_quarter_info(ticker, accn)
        except Exception as e:
            mismatches.append(f"S6b {accn}: resolve_quarter_info raised: {type(e).__name__}: {e}")
            continue
        n_called += 1
        ql = qi.get("quarter_label") or ""
        if ql:
            try:
                q_part, fy_part = ql.split("_FY")
                expected_fy = fy_part
                expected_q = q_part
            except ValueError:
                expected_fy, expected_q = "", ""
        else:
            expected_fy, expected_q = "", ""
        expected_source = qi.get("quarter_identity_source") or ""

        csv_fy = (r.get("production_fy", "") or "").strip()
        csv_q = (r.get("production_q", "") or "").strip()
        csv_source = (r.get("production_source", "") or "").strip()

        if csv_fy != expected_fy:
            mismatches.append(
                f"S6b {accn} production_fy: csv={csv_fy!r} actual={expected_fy!r}"
            )
        if csv_q != expected_q:
            mismatches.append(
                f"S6b {accn} production_q: csv={csv_q!r} actual={expected_q!r}"
            )
        if csv_source != expected_source:
            mismatches.append(
                f"S6b {accn} production_source: csv={csv_source!r} actual={expected_source!r}"
            )

    mode_label = "FULL" if full else "stratified"
    if mismatches:
        for m in mismatches[:25]:
            print(f"  {m}")
        if len(mismatches) > 25:
            print(f"  ... and {len(mismatches) - 25} more")
        fail(
            f"S6b {mode_label} production-resolver re-derivation: {len(mismatches)} "
            f"mismatches across {len(sample_accns)} rows ({n_called} resolver calls). "
            f"Codex's shadow_audit.csv production columns do not match what "
            f"resolve_quarter_info() actually returns."
        )
    info(f"S6b {mode_label} production-resolver re-derivation: {n_called} resolver calls match ✓")


# ── S8: candidate_algorithms.py imports + has >=2 candidates ────────
def import_candidates() -> dict:
    """Import candidate_algorithms.py and return {name: callable}."""
    spec = importlib.util.spec_from_file_location("candidate_algorithms", str(CANDIDATE_ALGORITHMS_PATH))
    if spec is None or spec.loader is None:
        fail(f"S8 candidate_algorithms.py cannot be imported", code=2)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        fail(f"S8 candidate_algorithms.py raised on import: {e}", code=2)

    candidates = {}
    for name in dir(module):
        if name.startswith("candidate_") and callable(getattr(module, name)):
            candidates[name[len("candidate_"):]] = getattr(module, name)

    if len(candidates) < MIN_CANDIDATES:
        fail(
            f"S8 candidate_algorithms.py has only {len(candidates)} candidate "
            f"function(s); minimum {MIN_CANDIDATES} required. Found: {list(candidates)}"
        )
    info(f"S8 candidate_algorithms.py: {len(candidates)} candidates loaded: {sorted(candidates)}")
    return candidates


# ── S9: independent re-derivation of candidate verdicts ──────────────
def check_candidate_rederivation(
    candidates: dict,
    candidate_rows: list[dict],
    shadow_rows: list[dict],
    gt_rows: list[dict],
    nr_rows: list[dict],
) -> None:
    """For each (accession, candidate), independently call the candidate function
    on the row's context and assert the CSV matches. This catches faked candidate
    output (Codex writing false verdicts to candidate_audit.csv)."""
    gt_by_accn = {r["accession_8k"]: r for r in gt_rows}
    nr_by_accn = {r["accession_8k"]: r for r in nr_rows}
    shadow_by_accn = {r["accession_8k"]: r for r in shadow_rows}

    # Group candidate_audit rows by candidate_name
    by_cand = {}
    for r in candidate_rows:
        by_cand.setdefault(r["candidate_name"], []).append(r)

    if set(by_cand.keys()) != set(candidates.keys()):
        fail(
            f"S9 candidate set mismatch: candidate_algorithms.py has "
            f"{sorted(candidates)}, candidate_audit.csv has {sorted(by_cand)}"
        )

    expected_n = len(gt_rows) + len(nr_rows)
    expected_accns = {r["accession_8k"] for r in gt_rows} | {r["accession_8k"] for r in nr_rows}
    for cname, rows in by_cand.items():
        if len(rows) != expected_n:
            fail(
                f"S9 candidate '{cname}': {len(rows)} rows in candidate_audit.csv, "
                f"expected {expected_n} (full corpus). Each candidate must "
                f"produce output for EVERY corpus row — no missing outputs."
            )
        cand_accns = {r["accession_8k"] for r in rows}
        missing = expected_accns - cand_accns
        if missing:
            fail(
                f"S9 candidate '{cname}': missing output for {len(missing)} corpus "
                f"accessions. Sample: {sorted(missing)[:5]}"
            )

    # Independent re-derivation: call each candidate function on each accession's
    # SANITIZED context (oracle fields stripped) and compare. We also re-derive
    # candidate_quarter_verdict and candidate_safety_verdict from the candidate's
    # output + corpus rules.
    nr_reason_by_accn = {r["accession_8k"]: r.get("reason", "") for r in nr_rows}
    gt_set = {r["accession_8k"] for r in gt_rows}
    nr_set = {r["accession_8k"] for r in nr_rows}

    mismatches: list[str] = []
    for cname, fn in candidates.items():
        rows_for_cand = by_cand[cname]
        for cand_row in rows_for_cand:
            accn = cand_row["accession_8k"]
            corpus_row = gt_by_accn.get(accn) or nr_by_accn.get(accn)
            if corpus_row is None:
                mismatches.append(f"S9 {cname}/{accn}: not in corpus")
                continue

            # Sanitize: strip oracle fields before passing to candidate
            sanitized = _sanitize_for_candidate(corpus_row)

            try:
                actual = fn(sanitized)
            except Exception as e:
                mismatches.append(f"S9 {cname}/{accn}: candidate raised: {type(e).__name__}: {e}")
                continue
            if not isinstance(actual, dict):
                mismatches.append(f"S9 {cname}/{accn}: candidate returned non-dict {type(actual).__name__}")
                continue
            missing_keys = {"fy", "q", "source", "safety_action"} - set(actual.keys())
            if missing_keys:
                mismatches.append(f"S9 {cname}/{accn}: candidate dict missing {sorted(missing_keys)}")
                continue

            # Normalize candidate output for comparison
            actual_fy = "" if actual["fy"] is None else str(actual["fy"])
            actual_q = "" if actual["q"] is None else str(actual["q"])
            actual_src = str(actual["source"]) if actual["source"] is not None else ""
            actual_sa = str(actual["safety_action"]) if actual["safety_action"] is not None else ""

            csv_fy = (cand_row.get("candidate_fy", "") or "").strip()
            csv_q = (cand_row.get("candidate_q", "") or "").strip()
            csv_src = (cand_row.get("candidate_source", "") or "").strip()
            csv_sa = (cand_row.get("candidate_safety_action", "") or "").strip()
            csv_qv = (cand_row.get("candidate_quarter_verdict", "") or "").strip()
            csv_sv = (cand_row.get("candidate_safety_verdict", "") or "").strip()

            # Output match
            if actual_fy != csv_fy:
                mismatches.append(f"S9 {cname}/{accn} fy: csv={csv_fy!r} actual={actual_fy!r}")
            if actual_q != csv_q:
                mismatches.append(f"S9 {cname}/{accn} q: csv={csv_q!r} actual={actual_q!r}")
            if actual_src != csv_src:
                mismatches.append(f"S9 {cname}/{accn} source: csv={csv_src!r} actual={actual_src!r}")
            if actual_sa != csv_sa:
                mismatches.append(f"S9 {cname}/{accn} safety_action: csv={csv_sa!r} actual={actual_sa!r}")

            # safety_action enum
            if csv_sa not in VALID_SAFETY_ACTIONS:
                mismatches.append(
                    f"S9 {cname}/{accn}: safety_action={csv_sa!r} not in {VALID_SAFETY_ACTIONS}"
                )

            # Re-derive candidate_quarter_verdict + candidate_safety_verdict
            is_gt = accn in gt_set
            is_nr = accn in nr_set
            corpus_fy = ((gt_by_accn.get(accn) or {}).get("fy_xbrl", "") or "").strip()
            corpus_q = ((gt_by_accn.get(accn) or {}).get("q_xbrl", "") or "").strip()
            nr_reason = nr_reason_by_accn.get(accn) if is_nr else None

            expected_qv = _compute_candidate_quarter_verdict(
                is_gt=is_gt, cand_fy=actual_fy, cand_q=actual_q,
                corpus_fy=corpus_fy, corpus_q=corpus_q,
                safety_action=actual_sa,
            )
            expected_sv = _compute_candidate_safety_verdict(
                is_gt=is_gt, qv=expected_qv,
                cand_source=actual_src, cand_safety_action=actual_sa,
                nr_reason=nr_reason,
            )

            if csv_qv != expected_qv:
                mismatches.append(
                    f"S9 {cname}/{accn} quarter_verdict mismatch: csv={csv_qv!r} "
                    f"computed={expected_qv!r}"
                )
            if csv_sv != expected_sv:
                mismatches.append(
                    f"S9 {cname}/{accn} safety_verdict mismatch: csv={csv_sv!r} "
                    f"computed={expected_sv!r}"
                )

    if mismatches:
        for m in mismatches[:30]:
            print(f"  {m}")
        if len(mismatches) > 30:
            print(f"  ... and {len(mismatches) - 30} more")
        fail(f"S9 candidate re-derivation: {len(mismatches)} mismatches")
    info(
        f"S9 candidate re-derivation: 0 mismatches across "
        f"{len(by_cand)} candidates × {expected_n} rows = {len(candidate_rows)} cells ✓"
    )


# ── S10: FCX harm subset hard fail ───────────────────────────────────
def check_fcx_harm_subset(candidate_rows: list[dict], nr_rows: list[dict]) -> None:
    """Hard fail: any candidate with WRONG_AUTO_WROTE on
    NR.reason == 'not_same_event_periodic' is disqualified."""
    fcx_shape_accns = {
        r["accession_8k"] for r in nr_rows if r.get("reason") == "not_same_event_periodic"
    }
    info(f"S10 FCX-shape subset size: {len(fcx_shape_accns)} not_same_event_periodic rows")

    by_cand: dict[str, int] = {}
    for r in candidate_rows:
        if r["accession_8k"] in fcx_shape_accns and r.get("candidate_safety_verdict") == "WRONG_AUTO_WROTE":
            by_cand[r["candidate_name"]] = by_cand.get(r["candidate_name"], 0) + 1

    if by_cand:
        for cname, n in by_cand.items():
            print(f"  candidate '{cname}': {n} WRONG_AUTO_WROTE on FCX-shape subset")
        fail(
            f"S10 hard-fail: {len(by_cand)} candidate(s) had WRONG_AUTO_WROTE on "
            f"the not_same_event_periodic subset. Per Goal 2 spec, NO candidate "
            f"may have ANY WRONG_AUTO_WROTE on this subset (the FCX bug shape)."
        )
    info(f"S10 FCX harm subset: 0 WRONG_AUTO_WROTE across all candidates ✓")


# ── S10b: recommended-candidate hard rules ───────────────────────────
def check_recommended_candidate(
    candidate_rows: list[dict], nr_rows: list[dict], candidates: dict
) -> None:
    """Verify the 'recommended' candidate named in GOAL2_REPORT.md:
      (a) exists as a function in candidate_algorithms.py
      (b) has rows in candidate_audit.csv
      (c) has ZERO AUTO_OK / AUTO_ON_UNCERTAIN_ROW on the
          not_same_event_periodic subset (FCX-shape rows must fail closed).
    """
    text = GOAL2_REPORT_PATH.read_text(encoding="utf-8")

    # Parse recommended candidate name. Format expected: a line containing
    # 'Recommended candidate:' or 'RECOMMENDED:' followed by the name.
    import re
    m = re.search(r"(?:recommended\s+candidate|RECOMMENDED)\s*[:=]\s*[`'\"]?([a-zA-Z0-9_]+)",
                  text, re.IGNORECASE)
    if not m:
        fail(
            "S10b GOAL2_REPORT.md must contain an explicit 'Recommended candidate: <name>' "
            "line so the verifier can identify the winner. Add a line like "
            "'Recommended candidate: <candidate_name>' (matching one of the candidate "
            "function names)."
        )
    recommended = m.group(1)

    # (a) must exist as a function in candidate_algorithms.py
    if recommended not in candidates:
        fail(
            f"S10b recommended candidate '{recommended}' (named in GOAL2_REPORT.md) "
            f"is NOT a candidate function in candidate_algorithms.py. "
            f"Available candidates: {sorted(candidates)}"
        )
    # (b) must have rows in candidate_audit.csv
    cand_rows_for_winner = [r for r in candidate_rows if r.get("candidate_name") == recommended]
    if not cand_rows_for_winner:
        fail(
            f"S10b recommended candidate '{recommended}' has 0 rows in "
            f"candidate_audit.csv. Cannot verify a winner with no audited rows."
        )

    fcx_shape_accns = {
        r["accession_8k"] for r in nr_rows if r.get("reason") == "not_same_event_periodic"
    }

    # (c) zero AUTO_OK / AUTO_ON_UNCERTAIN_ROW on FCX-shape subset
    bad_actions = {"AUTO_OK", "AUTO_ON_UNCERTAIN_ROW"}
    bad_count = 0
    rows_checked = 0
    samples: list[str] = []
    for r in cand_rows_for_winner:
        if r.get("accession_8k") not in fcx_shape_accns:
            continue
        rows_checked += 1
        action = r.get("candidate_safety_action", "")
        verdict = r.get("candidate_safety_verdict", "")
        if action in bad_actions or verdict in bad_actions:
            bad_count += 1
            if len(samples) < 5:
                samples.append(
                    f"{r['accession_8k']} action={action} verdict={verdict}"
                )

    if rows_checked == 0:
        fail(
            f"S10b recommended candidate '{recommended}' has 0 rows on the "
            f"not_same_event_periodic subset ({len(fcx_shape_accns)} expected). "
            f"Cannot verify FCX-safety with empty subset."
        )

    if bad_count > 0:
        for s in samples:
            print(f"  {s}")
        fail(
            f"S10b recommended candidate '{recommended}' has {bad_count} "
            f"AUTO_OK/AUTO_ON_UNCERTAIN_ROW rows on the not_same_event_periodic "
            f"subset. The winner MUST fail closed on FCX-shape rows. "
            f"Either pick a different recommended candidate or fix the recommended "
            f"one to fail closed on these rows."
        )
    info(
        f"S10b recommended candidate '{recommended}': exists in "
        f"candidate_algorithms.py + has {len(cand_rows_for_winner)} rows in "
        f"candidate_audit.csv; 0 AUTO actions on not_same_event_periodic subset "
        f"({rows_checked} rows checked) ✓"
    )


# ── S11: GOAL2_REPORT.md content ─────────────────────────────────────
def check_report() -> None:
    text = GOAL2_REPORT_PATH.read_text(encoding="utf-8")
    if len(text) < 500:
        fail(f"S11 GOAL2_REPORT.md too short ({len(text)} bytes)")
    required_keywords = ("production", "candidate", "FCX", "WRONG_AUTO_WROTE")
    missing_keywords = [k for k in required_keywords if k.lower() not in text.lower()]
    if missing_keywords:
        fail(f"S11 GOAL2_REPORT.md missing required keywords: {missing_keywords}")
    info(f"S11 GOAL2_REPORT.md: {len(text)} bytes, all required keywords present ✓")


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Goal 2 shadow-validator verifier (hand-written; do not modify)."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "S6b: re-derive production resolver output for ALL 10,831 corpus rows "
            "(bulletproof; required for final Goal 2 sign-off). Default is "
            "deterministic stratified sampling (FCX-shape exhaustive + GT/other-NR "
            "stride samples) — fast for /goal iteration but evadable for non-FCX rows."
        ),
    )
    args = parser.parse_args()

    mode_label = "FULL re-derivation" if args.full else "stratified (iteration mode)"
    print(f"=== Goal 2 verifier (hand-written, do not modify) — S6b: {mode_label} ===")
    print(f"Shadow audit:        {SHADOW_AUDIT_PATH}")
    print(f"Candidate algorithms:{CANDIDATE_ALGORITHMS_PATH}")
    print(f"Candidate audit:     {CANDIDATE_AUDIT_PATH}")
    print(f"Report:              {GOAL2_REPORT_PATH}")
    print()

    check_verifier_git_clean()                                            # S1
    shadow_rows, candidate_rows, gt_rows, nr_rows = check_files_exist()   # S2, S3, S4
    check_shadow_no_duplicates(shadow_rows)                               # S5
    check_universe_coverage(shadow_rows, gt_rows, nr_rows)                # S6
    check_production_sample_rederivation(                                 # S6b
        shadow_rows, gt_rows, nr_rows, full=args.full
    )
    check_shadow_per_row(shadow_rows, gt_rows, nr_rows)                   # S7
    candidates = import_candidates()                                      # S8
    check_candidate_rederivation(candidates, candidate_rows, shadow_rows, gt_rows, nr_rows)  # S9
    check_fcx_harm_subset(candidate_rows, nr_rows)                        # S10
    check_recommended_candidate(candidate_rows, nr_rows, candidates)      # S10b
    check_report()                                                        # S11

    print()
    info("=" * 60)
    if args.full:
        info("ALL CHECKS PASSED — Goal 2 shadow validator verified (FULL mode)")
    else:
        info("ALL CHECKS PASSED — Goal 2 shadow validator verified (stratified mode)")
        info("REMINDER: re-run with --full before final Goal 2 sign-off.")
    info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
