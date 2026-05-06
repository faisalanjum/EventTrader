#!/usr/bin/env python3
"""
verify_live_mode_resolver.py — Independent verifier for Goal 3 (live-mode
resolver discovery + PIT-safe candidate benchmark).

HAND-WRITTEN BY HUMANS (NOT BY THE AGENT) to prevent self-rubber-stamping.
This script decides whether Goal 3 is complete; the agent's job is to produce
output that passes THIS verifier without modifying it.

DESIGN INVARIANTS (per .claude/plans/quarter-identity-resolver.md):

  Goal 3 north star: ≥99.9% of live earnings 8-Ks fire predictions correctly.
  Goal 3 method: empirically benchmark PIT-safe candidate live-mode resolvers
  against the Goal 1 corpus, simulating live mode at the moment the 8-K was
  filed (no future data visible).

  CRITICAL DESIGN PRINCIPLE: the 99.9% threshold is the NORTH STAR but is NOT
  a verifier hard-pass criterion. The verifier reports the empirically-
  achieved rate and classifies residuals; the decision about whether the rate
  is acceptable for production is a human/strategic decision in the next step.

  HARD-LOCKED safety threshold (the ONLY one):
    - Zero WRONG_AUTO_WROTE across all candidates on all 10,831 corpus rows.

  SOFT-REPORTED metrics (not gated):
    - would_fire rate per candidate
    - correct rate per candidate (on GT rows)
    - fail_closed rate per candidate
    - per-FYE / 52-53-week / Q4 / non-Dec-FYE breakdowns

PIT-SAFETY ENFORCEMENT:

  Sanitized row context — fields candidates MAY see:
    accession_8k, ticker, filed_8k, fye_month

  FORBIDDEN fields (verifier strips before invocation; AST-checked):
    fy_xbrl, q_xbrl, fy_math, q_math, agreement, reason
      (oracle leakage from Goal 1 corpus)
    period_of_report, matched_accession_periodic, periodic_created,
    form_type_periodic
      (future-data leakage from same-event periodic)

  Candidate functions MAY query Neo4j BUT only with PIT-bound clauses
  (created <= $filed_8k or equivalent). The verifier AST-checks for this
  pattern and runtime-checks by passing only the sanitized context.

EXIT CODES:
  0  = all checks pass; Goal 3 verified done
  1  = corpus has fatal violations; Goal 3 not done
  2  = verifier itself failed (Neo4j / missing files / env / tampered file)

USAGE:
  cd /home/faisal/EventMarketDB
  venv/bin/python earnings-analysis/canary/quarter_resolver/verify_live_mode_resolver.py
  # No --fast/--full distinction; verifier is itself fast.

CHECKS PERFORMED (in order; first failure exits 1 unless code is 2):
  L1.  Verifier file is git-clean (catches Codex-tampering)
  L2.  All required deliverables exist + non-empty (live_candidates.py,
       live_mode_audit.csv, LIVE_MODE_REPORT.md)
  L3.  live_mode_audit.csv schema EXACTLY matches REQUIRED_COLUMNS_LIVE_AUDIT
       (ordered)
  L4.  live_candidates.py has ≥3 distinct candidate functions, AND all of
       {prior_periodic_projection, lag_window, hybrid_agreement} are present
       as candidate_live_<name>; each importable. Per-candidate breakdown
       in the report depends on these names.
  L5.  AST PIT-safety check (HARDENED):
       - Forbid references to oracle fields (fy_xbrl, q_xbrl, fy_math,
         q_math, agreement, reason) and same-event-periodic fields
         (period_of_report, matched_accession_periodic, periodic_created,
         form_type_periodic) — these are stripped by sanitization
       - Forbid file I/O imports/calls (csv, pandas, open, read_text,
         read_csv, etc.) — candidates MUST NOT read corpus files
       - Forbid subprocess imports/calls
       - Forbid path/file-name string literals referencing corpus or report
         artifacts (ground_truth.csv, needs_review.csv, GOAL2_REPORT.md, ...)
       - Heuristic Neo4j PIT-bound check: if a candidate function uses
         .run/.execute_read, the function must reference both 'created' and
         a cutoff anchor ('filed_8k' / 'cutoff' / 'pit'). Backed up by L7
         runtime check.
  L6.  Universe coverage: live_mode_audit.csv covers ALL 10,831 corpus rows
       (9,909 GT + 922 NR) per candidate. NOTE: The broader 10,995 earnings
       8-K universe is NOT scored — only the 10,831 rows that have Goal 1
       labels.
  L7.  Independent re-derivation (HARDENED): verifier calls each candidate
       function on a PIT-MASKED sanitized row context for every corpus row,
       passing a PITGuardedSession proxy in place of a raw Neo4j session.
       The proxy intercepts every .run() call and rejects Cypher that
       touches :Report without a `created <= ...` cutoff bound. CSV claims
       (candidate_fy/q/source/safety_action/would_fire/correct/verdicts)
       must match what the function actually returns.
  L8.  HARD-LOCKED: ZERO WRONG_AUTO_WROTE across all candidates on any row
       (the only safety threshold; production fix cannot ship if any
        candidate ever writes wrong fy/q with AUTO_OK).
       NR rows do NOT get correctness credit — AUTO_OK on NR is always
       AUTO_ON_UNCERTAIN_ROW, never "correct".
  L9.  SOFT-REPORTED rates per candidate (informational; no pass/fail):
       would_fire %, correct %, fail_closed %, AUTO_ON_UNCERTAIN_ROW %,
       per-FYE bucket, per-52/53-week bucket, per-FCX-shape bucket.
  L10. Recommended candidate (named in LIVE_MODE_REPORT.md):
       (a) name MUST exist as a function in live_candidates.py
       (b) name MUST have rows in live_mode_audit.csv (>=1)
       (c) MUST have zero WRONG_AUTO_WROTE on any subset
  L11. LIVE_MODE_REPORT.md non-empty + ≥1500 bytes + references all required
       keywords (would_fire, correct, WRONG_AUTO_WROTE, Recommended candidate)
       + explicitly references universe size (10,831 or 10831) + contains
       all required SECTIONS (Universe Contract, Prior-Periodic Availability,
       Per-Candidate Headline Metrics, Per-Bucket Breakdown) + achievability
       statement (YES/PARTIAL/NO).

This module re-uses production helpers (period_to_fiscal, get_fye_month) but
applies them independently of the candidates' implementations.
"""
from __future__ import annotations
import ast
import csv
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
LIVE_AUDIT_PATH = _HERE / "live_mode_audit.csv"
LIVE_CANDIDATES_PATH = _HERE / "live_candidates.py"
LIVE_REPORT_PATH = _HERE / "LIVE_MODE_REPORT.md"
GROUND_TRUTH_PATH = _HERE / "ground_truth.csv"
NEEDS_REVIEW_PATH = _HERE / "needs_review.csv"
PROJECT_ROOT = _HERE.parents[2]

# ── Production helpers (re-used independently) ───────────────────────
sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

try:
    from fye_month import get_fye_month  # noqa: F401
    from fiscal_math import period_to_fiscal  # noqa: F401
except ImportError as e:
    print(f"VERIFIER INFRA ERROR: cannot import production module: {e}", file=sys.stderr)
    sys.exit(2)

try:
    from neo4j import GraphDatabase
except ImportError:
    print("VERIFIER INFRA ERROR: neo4j driver not available", file=sys.stderr)
    sys.exit(2)

# ── Schema (locked, ORDERED) ─────────────────────────────────────────
REQUIRED_COLUMNS_LIVE_AUDIT = [
    "accession_8k",
    "ticker",
    "corpus_label",          # "ground_truth" | "needs_review:<reason>"
    "corpus_fy",             # GT only (NR rows leave blank)
    "corpus_q",              # GT only
    "candidate_name",
    "candidate_fy",
    "candidate_q",
    "candidate_source",
    "candidate_safety_action",     # AUTO_OK | NEEDS_REVIEW | FAIL_CLOSED | NO_RESOLUTION
    "would_fire",                  # "true" | "false" — true iff safety_action == AUTO_OK
    "correct",                     # "true" | "false" | "" — only meaningful for GT firing rows
    "candidate_quarter_verdict",   # AGREE | BUG | NO_RESOLUTION | N_A
    "candidate_safety_verdict",    # OK | WRONG_AUTO_WROTE | CORRECT_FAIL_CLOSED | AUTO_ON_UNCERTAIN_ROW
]

# Sanitized row context — fields candidates MAY see at runtime
_RUNTIME_ROW_FIELDS = {
    "accession_8k", "ticker", "filed_8k", "fye_month",
}

# Forbidden fields — must NOT appear as string literals OR attribute accesses
# in candidate code; verifier strips them before invocation
_FORBIDDEN_FIELD_NAMES = {
    # oracle leakage (Goal 1 corpus answers)
    "fy_xbrl", "q_xbrl", "fy_math", "q_math", "agreement", "reason",
    # future-data leakage (same-event periodic, only known retrospectively)
    "period_of_report", "matched_accession_periodic", "periodic_created",
    "form_type_periodic",
}

# Forbidden function calls in candidates.
# NOTE: do NOT include generic names like "run", "call", "load" — those
# would block legitimate uses (e.g., neo4j_session.run, callable.call).
# Subprocess is banned via _FORBIDDEN_IMPORT_MODULES instead.
_FORBIDDEN_CALLS = {
    "resolve_quarter_info",
    # File I/O — candidates must NOT read any file. Corpus is OFF-LIMITS.
    "open",            # builtin open() — opens any file
    "read_text", "read_bytes",
    "read_csv", "read_table", "read_excel", "read_json", "read_parquet",
    "read_pickle", "read_feather", "read_html", "read_sql",
    "DictReader",   # csv.DictReader specifically (csv module also import-banned)
    "loadtxt", "genfromtxt",  # numpy file loaders
    "fromfile",
    # Subprocess-specific entry points (the module itself is import-banned;
    # these are belt-and-suspenders against `from subprocess import Popen`).
    "Popen", "check_call", "check_output", "getoutput", "getstatusoutput",
}

# Forbidden top-level module names (any import is rejected).
_FORBIDDEN_IMPORT_MODULES = {
    "csv", "pandas", "pd", "numpy", "polars", "pyarrow", "openpyxl",
    "xlsxwriter", "subprocess", "shutil", "pickle",
}

# Forbidden file path / accession references inside string literals
_FORBIDDEN_PATH_TOKENS = {
    "ground_truth.csv", "needs_review.csv", "shadow_audit.csv",
    "candidate_audit.csv", "live_mode_audit.csv", "GOAL2_REPORT.md",
    "GOAL1_REPORT.md", "REPORT.md", "audit_packets",
}


def _sanitize_for_candidate(row: dict) -> dict:
    """Strip everything except _RUNTIME_ROW_FIELDS."""
    return {k: v for k, v in row.items() if k in _RUNTIME_ROW_FIELDS}


class PITGuardedSession:
    """Wraps a Neo4j session and rejects Cypher queries that look up Report
    nodes without a verified PIT bound.

    A query is considered PIT-safe iff:
      - It does NOT touch :Report at all (harmless lookup, e.g., Entity), OR
      - ALL of the following hold:
        (a) Cypher contains a `created <=` (or `created <`) bound
        (b) Cypher references at least one allowed cutoff parameter name
            ($filed_8k, $cutoff, $pit, $filed)
        (c) The corresponding parameter is present in the parameters dict
        (d) The parameter value matches this row's filed_8k (exact match,
            or one is a date-prefix of the other to tolerate datetime-vs-
            date format variation)

    Literal `datetime('YYYY-MM-DD')` strings are NOT accepted as a cutoff
    proof — Codex could hardcode a future date and bypass the check.

    Violations are accumulated; the verifier asserts zero per call.
    """

    _ALLOWED_CUTOFF_PARAMS = ("filed_8k", "cutoff", "pit", "filed")

    def __init__(self, real_session, *, filed_8k_value: str):
        self._session = real_session
        self._filed_8k = (filed_8k_value or "").strip()
        self.violations: list[str] = []

    @staticmethod
    def _values_align(passed: str, expected: str) -> bool:
        """Tolerate datetime/date format variants — accept if either string
        is a prefix of the other after normalizing common separators.
        Both are stripped + compared; date-prefix-of-datetime is allowed."""
        p = (passed or "").strip().replace("T", " ")
        e = (expected or "").strip().replace("T", " ")
        if not p or not e:
            return False
        if p == e:
            return True
        # date prefix tolerance — first 10 chars are YYYY-MM-DD
        if len(p) >= 10 and len(e) >= 10 and p[:10] == e[:10]:
            return True
        return False

    def _is_pit_safe(self, query: str, parameters: dict | None) -> tuple[bool, str]:
        q_lower = (query or "").lower()
        # Cheap accept: no Report match → harmless lookup (e.g., Entity)
        if "report" not in q_lower:
            return True, ""
        # (a) must have created <= or created < bound
        has_created_bound = (
            "created <=" in q_lower
            or "created<=" in q_lower
            or "created <" in q_lower
            or "created<" in q_lower
        )
        if not has_created_bound:
            return False, "missing `created <= ...` bound"
        # (b) must reference one of the allowed cutoff parameter names
        params = parameters or {}
        used_key = None
        for key in self._ALLOWED_CUTOFF_PARAMS:
            if f"${key}" in q_lower:
                used_key = key
                break
        if used_key is None:
            return False, (
                f"missing allowed cutoff parameter (expected one of "
                f"{['$' + k for k in self._ALLOWED_CUTOFF_PARAMS]})"
            )
        # (c) parameter must actually be passed
        if used_key not in params:
            return False, f"cutoff parameter ${used_key} not supplied in parameters dict"
        # (d) value must match this row's filed_8k
        passed_val = str(params[used_key])
        if not self._values_align(passed_val, self._filed_8k):
            return False, (
                f"cutoff parameter ${used_key}={passed_val!r} does not match "
                f"row's filed_8k={self._filed_8k!r}"
            )
        return True, ""

    def run(self, query, parameters=None, **kwargs):
        # Some neo4j driver versions accept positional parameters dict; merge
        merged = dict(parameters) if parameters else {}
        merged.update(kwargs)
        ok, why = self._is_pit_safe(query, merged)
        if not ok:
            self.violations.append(
                f"PIT-unsafe query — {why}: {(query or '')[:200]}"
            )
        return self._session.run(query, parameters or {}, **kwargs)

    def execute_read(self, fn, *args, **kwargs):
        # Wrap the transaction's run so even txn-scoped reads are guarded
        outer = self

        class _GuardedTx:
            def __init__(self, tx):
                self._tx = tx
            def run(self, q, parameters=None, **kw):
                merged = dict(parameters) if parameters else {}
                merged.update(kw)
                ok, why = outer._is_pit_safe(q, merged)
                if not ok:
                    outer.violations.append(
                        f"PIT-unsafe query in execute_read — {why}: {(q or '')[:200]}"
                    )
                return self._tx.run(q, parameters or {}, **kw)
            def __getattr__(self, name):
                return getattr(self._tx, name)

        def wrapped(tx, *a, **k):
            return fn(_GuardedTx(tx), *a, **k)
        return self._session.execute_read(wrapped, *args, **kwargs)

    def execute_write(self, *a, **k):
        # Goal 3 forbids writes outright
        self.violations.append("forbidden: candidate attempted execute_write")
        return None

    def __getattr__(self, name):
        return getattr(self._session, name)


VALID_QUARTER_VERDICTS = {"AGREE", "BUG", "NO_RESOLUTION", "N_A"}
VALID_GT_SAFETY = {"OK", "WRONG_AUTO_WROTE"}
VALID_NR_SAFETY = {"CORRECT_FAIL_CLOSED", "AUTO_ON_UNCERTAIN_ROW", "WRONG_AUTO_WROTE"}
VALID_SAFETY_ACTIONS = {"AUTO_OK", "NEEDS_REVIEW", "FAIL_CLOSED", "NO_RESOLUTION"}
VALID_QUARTERS = {"Q1", "Q2", "Q3", "Q4"}
_FAIL_CLOSED_ACTIONS = {"NEEDS_REVIEW", "FAIL_CLOSED", "NO_RESOLUTION"}

REQUIRED_DELIVERABLES = (
    "live_candidates.py",
    "live_mode_audit.csv",
    "LIVE_MODE_REPORT.md",
)

MIN_CANDIDATES = 3
MIN_REPORT_BYTES = 1500

REPORT_REQUIRED_KEYWORDS = (
    "would_fire", "correct", "WRONG_AUTO_WROTE", "Recommended candidate",
    "10,831", "10831",   # universe contract: must explicitly state scored corpus
)
REPORT_REQUIRED_SECTIONS = (
    "Universe Contract",
    "Prior-Periodic Availability",
    "Per-Candidate Headline Metrics",
    "Per-Bucket Breakdown",
)
REPORT_ACHIEVABILITY_TOKENS = ("YES", "PARTIAL", "NO")  # at least one must appear

REQUIRED_CANDIDATES = {
    "prior_periodic_projection",
    "lag_window",
    "hybrid_agreement",
}

CANDIDATE_PREFIX = "candidate_live_"


# ── Output helpers ────────────────────────────────────────────────────
def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


# ── L1: git freeze check ─────────────────────────────────────────────
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
    info("L1 git-clean: verifier matches committed version ✓")


# ── L2/L3: file + schema checks ──────────────────────────────────────
def check_files_exist() -> tuple[list[dict], list[dict], list[dict]]:
    """Return (audit_rows, gt_rows, nr_rows)."""
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
    info(f"L2 deliverables present + non-empty: {list(REQUIRED_DELIVERABLES)} ✓")

    with open(LIVE_AUDIT_PATH, encoding="utf-8") as f:
        audit_rows = list(csv.DictReader(f))
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        gt_rows = list(csv.DictReader(f))
    with open(NEEDS_REVIEW_PATH, encoding="utf-8") as f:
        nr_rows = list(csv.DictReader(f))

    if not audit_rows:
        fail("live_mode_audit.csv has no data rows")

    with open(LIVE_AUDIT_PATH, encoding="utf-8") as f:
        actual_cols = list(csv.reader(f))[0]
    if actual_cols != REQUIRED_COLUMNS_LIVE_AUDIT:
        fail(
            f"L3 live_mode_audit.csv columns not in expected order/set:\n"
            f"  expected: {REQUIRED_COLUMNS_LIVE_AUDIT}\n"
            f"  actual:   {actual_cols}"
        )
    info(f"L3 live_mode_audit.csv schema: {len(REQUIRED_COLUMNS_LIVE_AUDIT)} columns in correct order ✓")

    return audit_rows, gt_rows, nr_rows


# ── L4: candidate import ─────────────────────────────────────────────
def import_candidates() -> dict:
    """Import live_candidates.py and return {short_name: callable}."""
    spec = importlib.util.spec_from_file_location("live_candidates", str(LIVE_CANDIDATES_PATH))
    if spec is None or spec.loader is None:
        fail(f"L4 live_candidates.py cannot be imported", code=2)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        fail(f"L4 live_candidates.py raised on import: {e}", code=2)

    candidates = {}
    for name in dir(module):
        if name.startswith(CANDIDATE_PREFIX) and callable(getattr(module, name)):
            short = name[len(CANDIDATE_PREFIX):]
            candidates[short] = getattr(module, name)

    if len(candidates) < MIN_CANDIDATES:
        fail(
            f"L4 live_candidates.py has only {len(candidates)} candidate "
            f"function(s); minimum {MIN_CANDIDATES} required. Found: {list(candidates)}"
        )
    missing_required = REQUIRED_CANDIDATES - set(candidates.keys())
    if missing_required:
        fail(
            f"L4 missing required candidate functions: {sorted(missing_required)}. "
            f"Goal 3 mandates {sorted(REQUIRED_CANDIDATES)} for separate per-candidate "
            f"benchmarking. Found: {sorted(candidates)}"
        )
    info(f"L4 live_candidates.py: {len(candidates)} candidates loaded: {sorted(candidates)}")
    return candidates


# ── L5: AST PIT-safety check ─────────────────────────────────────────
def check_pit_safety_ast() -> None:
    """Lint live_candidates.py for forbidden field references and calls.

    Specifically:
    - Reject any string literal matching a forbidden field name (would only
      be present if the candidate is reading that key from a dict/object)
    - Reject any attribute access of a forbidden field name
    - Reject any call to forbidden functions (e.g., resolve_quarter_info)
    - Heuristic check: if any string literal contains 'session.run' or 'tx.run',
      assert the surrounding text in the same function references 'created' AND
      ('filed_8k' or 'filed' or 'cutoff') — proxy for PIT bound usage. This is
      a structural lint, not a proof.
    """
    src = LIVE_CANDIDATES_PATH.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        fail(f"L5 live_candidates.py has syntax error: {e}", code=2)

    violations: list[str] = []

    # Top-level: ban forbidden imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _FORBIDDEN_IMPORT_MODULES:
                    violations.append(f"forbidden import: {alias.name}")
        if isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod in _FORBIDDEN_IMPORT_MODULES:
                violations.append(f"forbidden import-from: {node.module}")

    # Walk per-function so we can do per-function PIT-bound heuristic check
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = getattr(f, "attr", None) or getattr(f, "id", None)
            if name in _FORBIDDEN_CALLS:
                violations.append(f"forbidden call: {name}")
        if isinstance(node, ast.Attribute):
            if node.attr in _FORBIDDEN_FIELD_NAMES:
                violations.append(f"forbidden attribute access: .{node.attr}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in _FORBIDDEN_FIELD_NAMES:
                violations.append(
                    f"forbidden field name as string literal: {node.value!r} "
                    f"(suggests reading row_context[{node.value!r}])"
                )
            # ban path/accession-file tokens
            sval = node.value
            for tok in _FORBIDDEN_PATH_TOKENS:
                if tok in sval:
                    violations.append(
                        f"forbidden file/path token in string literal: {tok!r} "
                        f"(candidates may not reference corpus or report files)"
                    )
                    break

    # Per-function PIT-bound heuristic
    for fn_node in ast.walk(tree):
        if not isinstance(fn_node, ast.FunctionDef):
            continue
        if not fn_node.name.startswith(CANDIDATE_PREFIX):
            continue
        fn_src = ast.get_source_segment(src, fn_node) or ""
        # Does this function appear to query Neo4j?
        has_run_call = (".run(" in fn_src) or (".execute_read" in fn_src)
        if has_run_call:
            # Must include a temporal bound reference in the same function
            has_created = "created" in fn_src.lower() or "valid_to" in fn_src.lower()
            has_pit_anchor = (
                "filed_8k" in fn_src.lower()
                or "filed" in fn_src.lower()
                or "cutoff" in fn_src.lower()
                or "$filed" in fn_src.lower()
            )
            if not (has_created and has_pit_anchor):
                violations.append(
                    f"function {fn_node.name} appears to call Neo4j (.run/.execute_read) "
                    f"but does not contain BOTH a 'created'/'valid_to' reference AND a "
                    f"'filed_8k'/'filed'/'cutoff' anchor — likely missing PIT bound. "
                    f"Cypher MUST filter on `created <= $filed_8k` (or equivalent) for "
                    f"every Neo4j read."
                )

    if violations:
        for v in violations[:30]:
            print(f"  ✗ {v}")
        if len(violations) > 30:
            print(f"  ... and {len(violations) - 30} more")
        fail(
            f"L5 PIT-safety AST check found {len(violations)} violations in "
            f"live_candidates.py. Candidates MUST NOT read forbidden fields or "
            f"query Neo4j without a PIT bound."
        )
    info("L5 PIT-safety AST check: no forbidden field references or unbounded Neo4j reads ✓")


# ── L6: universe coverage per candidate ──────────────────────────────
def check_universe_coverage(audit_rows: list[dict], gt_rows: list[dict],
                              nr_rows: list[dict], candidates: dict) -> None:
    expected_accns = {r["accession_8k"] for r in gt_rows} | {r["accession_8k"] for r in nr_rows}
    expected_n = len(expected_accns)

    by_cand: dict[str, set] = {}
    for r in audit_rows:
        by_cand.setdefault(r["candidate_name"], set()).add(r["accession_8k"])

    cand_names_audit = set(by_cand.keys())
    cand_names_module = set(candidates.keys())
    if cand_names_audit != cand_names_module:
        fail(
            f"L6 candidate set mismatch: live_candidates.py has "
            f"{sorted(cand_names_module)}, live_mode_audit.csv has "
            f"{sorted(cand_names_audit)}"
        )

    for cname, accns in by_cand.items():
        missing = expected_accns - accns
        extra = accns - expected_accns
        if missing:
            fail(
                f"L6 candidate '{cname}': missing {len(missing)} corpus accessions. "
                f"Sample: {sorted(missing)[:5]}"
            )
        if extra:
            fail(
                f"L6 candidate '{cname}': has {len(extra)} accessions not in corpus. "
                f"Sample: {sorted(extra)[:5]}"
            )
    info(
        f"L6 universe coverage: live_mode_audit covers all {expected_n} corpus rows "
        f"per candidate ({len(by_cand)} candidates × {expected_n} = "
        f"{len(by_cand) * expected_n} expected total) ✓"
    )


# ── Verdict re-derivation helpers ────────────────────────────────────
def _compute_quarter_verdict(*, is_gt: bool, cand_fy: str, cand_q: str,
                               corpus_fy: str, corpus_q: str,
                               safety_action: str) -> str:
    """For GT rows: AGREE/BUG/NO_RESOLUTION based on candidate's auto-resolution.
    For NR rows: always N_A."""
    if not is_gt:
        return "N_A"
    if safety_action in _FAIL_CLOSED_ACTIONS:
        return "NO_RESOLUTION"
    if not cand_fy and not cand_q:
        return "NO_RESOLUTION"
    if cand_fy == corpus_fy and cand_q == corpus_q:
        return "AGREE"
    return "BUG"


def _compute_safety_verdict(*, is_gt: bool, qv: str,
                              cand_safety_action: str,
                              nr_reason: str | None) -> str:
    """GT: OK if AGREE/NO_RESOLUTION; WRONG_AUTO_WROTE if BUG.
    NR: CORRECT_FAIL_CLOSED if candidate explicitly fails closed;
        WRONG_AUTO_WROTE only if candidate AUTO_OK on a row that we have
            independent evidence is wrong (here: no evidence path, so we
            cannot mark NR as WRONG_AUTO_WROTE — rest is AUTO_ON_UNCERTAIN_ROW);
        AUTO_ON_UNCERTAIN_ROW if candidate AUTO_OK on uncertain NR row.

    NOTE: For Goal 3, the FCX-shape WRONG_AUTO_WROTE classification is
    different from Goal 2: in live mode, a candidate that AUTO_OK's on
    not_same_event_periodic does NOT necessarily commit the FCX harm IF its
    output happens to be the correct quarter. But we conservatively still
    flag WRONG_AUTO_WROTE for any AUTO_OK on a GT row where the answer is
    wrong, since GT has an oracle.
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
    return "AUTO_ON_UNCERTAIN_ROW"


def _compute_would_fire(safety_action: str) -> str:
    return "true" if safety_action == "AUTO_OK" else "false"


def _compute_correct(*, is_gt: bool, would_fire: str, cand_fy: str, cand_q: str,
                       corpus_fy: str, corpus_q: str) -> str:
    if not is_gt:
        return ""
    if would_fire != "true":
        return ""
    if cand_fy == corpus_fy and cand_q == corpus_q:
        return "true"
    return "false"


# ── L7: independent re-derivation ────────────────────────────────────
def check_rederivation(audit_rows: list[dict], gt_rows: list[dict],
                         nr_rows: list[dict], candidates: dict,
                         neo4j_session) -> None:
    """For each (accession, candidate), independently call the candidate
    function on the SANITIZED row context and assert the CSV matches."""
    gt_by_accn = {r["accession_8k"]: r for r in gt_rows}
    nr_by_accn = {r["accession_8k"]: r for r in nr_rows}
    nr_reason_by_accn = {r["accession_8k"]: r.get("reason", "") for r in nr_rows}
    gt_set = {r["accession_8k"] for r in gt_rows}
    nr_set = {r["accession_8k"] for r in nr_rows}

    by_cand: dict[str, list[dict]] = {}
    for r in audit_rows:
        by_cand.setdefault(r["candidate_name"], []).append(r)

    mismatches: list[str] = []
    for cname, fn in candidates.items():
        rows_for_cand = by_cand.get(cname, [])
        for cand_row in rows_for_cand:
            accn = cand_row["accession_8k"]
            corpus_row = gt_by_accn.get(accn) or nr_by_accn.get(accn)
            if corpus_row is None:
                mismatches.append(f"L7 {cname}/{accn}: not in corpus")
                continue

            sanitized = _sanitize_for_candidate(corpus_row)
            guarded = PITGuardedSession(
                neo4j_session, filed_8k_value=sanitized.get("filed_8k", "")
            )
            try:
                actual = fn(sanitized, neo4j_session=guarded)
            except Exception as e:
                mismatches.append(f"L7 {cname}/{accn}: candidate raised: {type(e).__name__}: {e}")
                continue
            if guarded.violations:
                for v in guarded.violations[:3]:
                    mismatches.append(f"L7 {cname}/{accn} PIT-unsafe Cypher: {v}")
                continue
            if not isinstance(actual, dict):
                mismatches.append(f"L7 {cname}/{accn}: candidate returned non-dict {type(actual).__name__}")
                continue
            missing_keys = {"fy", "q", "source", "safety_action"} - set(actual.keys())
            if missing_keys:
                mismatches.append(f"L7 {cname}/{accn}: candidate dict missing {sorted(missing_keys)}")
                continue

            actual_fy = "" if actual["fy"] is None else str(actual["fy"])
            actual_q = "" if actual["q"] is None else str(actual["q"])
            actual_src = str(actual["source"]) if actual["source"] is not None else ""
            actual_sa = str(actual["safety_action"]) if actual["safety_action"] is not None else ""

            csv_fy = (cand_row.get("candidate_fy", "") or "").strip()
            csv_q = (cand_row.get("candidate_q", "") or "").strip()
            csv_src = (cand_row.get("candidate_source", "") or "").strip()
            csv_sa = (cand_row.get("candidate_safety_action", "") or "").strip()
            csv_wf = (cand_row.get("would_fire", "") or "").strip()
            csv_correct = (cand_row.get("correct", "") or "").strip()
            csv_qv = (cand_row.get("candidate_quarter_verdict", "") or "").strip()
            csv_sv = (cand_row.get("candidate_safety_verdict", "") or "").strip()

            if actual_fy != csv_fy:
                mismatches.append(f"L7 {cname}/{accn} fy: csv={csv_fy!r} actual={actual_fy!r}")
            if actual_q != csv_q:
                mismatches.append(f"L7 {cname}/{accn} q: csv={csv_q!r} actual={actual_q!r}")
            if actual_src != csv_src:
                mismatches.append(f"L7 {cname}/{accn} source: csv={csv_src!r} actual={actual_src!r}")
            if actual_sa != csv_sa:
                mismatches.append(f"L7 {cname}/{accn} safety_action: csv={csv_sa!r} actual={actual_sa!r}")

            if csv_sa not in VALID_SAFETY_ACTIONS:
                mismatches.append(
                    f"L7 {cname}/{accn}: safety_action={csv_sa!r} not in {VALID_SAFETY_ACTIONS}"
                )

            # Re-derive verdicts + would_fire + correct
            is_gt = accn in gt_set
            corpus_fy = ((gt_by_accn.get(accn) or {}).get("fy_xbrl", "") or "").strip()
            corpus_q = ((gt_by_accn.get(accn) or {}).get("q_xbrl", "") or "").strip()
            nr_reason = nr_reason_by_accn.get(accn) if accn in nr_set else None

            expected_qv = _compute_quarter_verdict(
                is_gt=is_gt, cand_fy=actual_fy, cand_q=actual_q,
                corpus_fy=corpus_fy, corpus_q=corpus_q,
                safety_action=actual_sa,
            )
            expected_sv = _compute_safety_verdict(
                is_gt=is_gt, qv=expected_qv,
                cand_safety_action=actual_sa,
                nr_reason=nr_reason,
            )
            expected_wf = _compute_would_fire(actual_sa)
            expected_correct = _compute_correct(
                is_gt=is_gt, would_fire=expected_wf,
                cand_fy=actual_fy, cand_q=actual_q,
                corpus_fy=corpus_fy, corpus_q=corpus_q,
            )

            if csv_qv != expected_qv:
                mismatches.append(
                    f"L7 {cname}/{accn} quarter_verdict: csv={csv_qv!r} computed={expected_qv!r}"
                )
            if csv_sv != expected_sv:
                mismatches.append(
                    f"L7 {cname}/{accn} safety_verdict: csv={csv_sv!r} computed={expected_sv!r}"
                )
            if csv_wf != expected_wf:
                mismatches.append(
                    f"L7 {cname}/{accn} would_fire: csv={csv_wf!r} computed={expected_wf!r}"
                )
            if csv_correct != expected_correct:
                mismatches.append(
                    f"L7 {cname}/{accn} correct: csv={csv_correct!r} computed={expected_correct!r}"
                )

    if mismatches:
        for m in mismatches[:30]:
            print(f"  {m}")
        if len(mismatches) > 30:
            print(f"  ... and {len(mismatches) - 30} more")
        fail(f"L7 candidate re-derivation: {len(mismatches)} mismatches")

    total_cells = sum(len(rows) for rows in by_cand.values())
    info(
        f"L7 candidate re-derivation: 0 mismatches across "
        f"{len(by_cand)} candidates × ~{total_cells // max(1, len(by_cand))} rows = {total_cells} cells ✓"
    )


# ── L8: zero WRONG_AUTO_WROTE hard-lock ──────────────────────────────
def check_zero_wrong_auto_wrote(audit_rows: list[dict]) -> None:
    by_cand: dict[str, int] = {}
    samples: dict[str, list[str]] = {}
    for r in audit_rows:
        if r.get("candidate_safety_verdict") == "WRONG_AUTO_WROTE":
            cname = r["candidate_name"]
            by_cand[cname] = by_cand.get(cname, 0) + 1
            if len(samples.setdefault(cname, [])) < 5:
                samples[cname].append(
                    f"{r['accession_8k']} fy={r['candidate_fy']} q={r['candidate_q']} "
                    f"corpus_fy={r['corpus_fy']} corpus_q={r['corpus_q']}"
                )
    if by_cand:
        for cname, n in by_cand.items():
            print(f"  candidate '{cname}': {n} WRONG_AUTO_WROTE rows. Sample:")
            for s in samples.get(cname, []):
                print(f"    {s}")
        fail(
            f"L8 hard-lock: {len(by_cand)} candidate(s) had WRONG_AUTO_WROTE rows. "
            f"This is the ONE absolute safety threshold for Goal 3. NO candidate "
            f"may auto-resolve to a wrong quarter."
        )
    info("L8 zero WRONG_AUTO_WROTE: all candidates safe ✓")


# ── L9: soft-reported rates ──────────────────────────────────────────
def report_rates(audit_rows: list[dict], gt_rows: list[dict],
                   nr_rows: list[dict]) -> None:
    """Compute and print rates per candidate. NO pass/fail — informational."""
    gt_set = {r["accession_8k"] for r in gt_rows}
    nr_reason_by_accn = {r["accession_8k"]: r.get("reason", "") for r in nr_rows}
    fye_by_accn = {}
    for r in gt_rows + nr_rows:
        fye_by_accn[r["accession_8k"]] = r.get("fye_month", "")

    by_cand: dict[str, list[dict]] = {}
    for r in audit_rows:
        by_cand.setdefault(r["candidate_name"], []).append(r)

    print("")
    print("=" * 70)
    print("L9 SOFT-REPORTED RATES (informational only — verifier does not gate)")
    print("=" * 70)
    for cname in sorted(by_cand.keys()):
        rows = by_cand[cname]
        n = len(rows)
        n_fire = sum(1 for r in rows if r.get("would_fire") == "true")
        n_gt = sum(1 for r in rows if r["accession_8k"] in gt_set)
        n_correct = sum(1 for r in rows if r["accession_8k"] in gt_set
                                          and r.get("correct") == "true")
        n_fail_closed = sum(1 for r in rows
                              if r.get("candidate_safety_verdict") == "CORRECT_FAIL_CLOSED")
        n_auto_uncert = sum(1 for r in rows
                              if r.get("candidate_safety_verdict") == "AUTO_ON_UNCERTAIN_ROW")
        n_fcx = sum(1 for r in rows
                      if nr_reason_by_accn.get(r["accession_8k"]) == "not_same_event_periodic")
        n_fcx_fail = sum(1 for r in rows
                           if nr_reason_by_accn.get(r["accession_8k"]) == "not_same_event_periodic"
                           and r.get("candidate_safety_verdict") == "CORRECT_FAIL_CLOSED")

        print(f"\n  Candidate: {cname}")
        print(f"    rows                 = {n}")
        print(f"    would_fire           = {n_fire}/{n} ({100.0*n_fire/n:.2f}%)")
        if n_gt > 0:
            print(f"    correct on GT        = {n_correct}/{n_gt} ({100.0*n_correct/n_gt:.2f}%)")
        print(f"    fail_closed          = {n_fail_closed}/{n} ({100.0*n_fail_closed/n:.2f}%)")
        print(f"    auto_on_uncertain_row= {n_auto_uncert}/{n} ({100.0*n_auto_uncert/n:.2f}%)")
        if n_fcx > 0:
            print(f"    fail_closed on FCX-shape = {n_fcx_fail}/{n_fcx} ({100.0*n_fcx_fail/n_fcx:.2f}%)")

        # per-FYE-bucket would_fire
        fye_buckets: dict[str, list[dict]] = {}
        for r in rows:
            fye = fye_by_accn.get(r["accession_8k"], "")
            fye_buckets.setdefault(fye, []).append(r)
        if len(fye_buckets) > 1:
            print(f"    by FYE month (would_fire %):")
            for fye in sorted(fye_buckets.keys()):
                bucket = fye_buckets[fye]
                bn = len(bucket)
                bf = sum(1 for r in bucket if r.get("would_fire") == "true")
                print(f"      FYE={fye!r}: {bf}/{bn} ({100.0*bf/bn:.1f}%)")
    print("")
    print("=" * 70)
    print("REMINDER: 99.9% would_fire is the NORTH STAR but NOT verifier-gated.")
    print("Whether the achieved rate is acceptable for production is a human/")
    print("strategic decision, made AFTER reading LIVE_MODE_REPORT.md.")
    print("=" * 70)


# ── L10: recommended candidate ───────────────────────────────────────
def check_recommended_candidate(audit_rows: list[dict], candidates: dict) -> None:
    text = LIVE_REPORT_PATH.read_text(encoding="utf-8")

    import re
    m = re.search(r"(?:recommended\s+candidate|RECOMMENDED)\s*[:=]\s*[`'\"]?([a-zA-Z0-9_]+)",
                  text, re.IGNORECASE)
    if not m:
        fail(
            "L10 LIVE_MODE_REPORT.md must contain an explicit "
            "'Recommended candidate: <name>' line so the verifier can "
            "identify the winner. The name must match one of the "
            "candidate_live_<name> functions (without the prefix)."
        )
    recommended = m.group(1)

    if recommended not in candidates:
        fail(
            f"L10 recommended candidate '{recommended}' (named in "
            f"LIVE_MODE_REPORT.md) is NOT a candidate function in "
            f"live_candidates.py. Available: {sorted(candidates)}"
        )

    cand_rows_for_winner = [r for r in audit_rows if r.get("candidate_name") == recommended]
    if not cand_rows_for_winner:
        fail(
            f"L10 recommended candidate '{recommended}' has 0 rows in "
            f"live_mode_audit.csv. Cannot verify a winner with no audited rows."
        )

    n_wrong = sum(1 for r in cand_rows_for_winner
                    if r.get("candidate_safety_verdict") == "WRONG_AUTO_WROTE")
    if n_wrong > 0:
        fail(
            f"L10 recommended candidate '{recommended}' has {n_wrong} "
            f"WRONG_AUTO_WROTE rows. The winner MUST have zero. (L8 "
            f"should have caught this earlier; this is a redundant safety check.)"
        )
    info(
        f"L10 recommended candidate '{recommended}': exists in "
        f"live_candidates.py + has {len(cand_rows_for_winner)} rows in "
        f"live_mode_audit.csv + zero WRONG_AUTO_WROTE ✓"
    )


# ── L11: report content ──────────────────────────────────────────────
def check_report() -> None:
    text = LIVE_REPORT_PATH.read_text(encoding="utf-8")
    if len(text) < MIN_REPORT_BYTES:
        fail(f"L11 LIVE_MODE_REPORT.md too short ({len(text)} bytes; minimum {MIN_REPORT_BYTES})")

    # Keyword presence (relaxed: at least one form of the universe number must appear)
    text_lower = text.lower()
    # Check keywords with disjunction for "10,831"/"10831" alternatives
    required_simple = [k for k in REPORT_REQUIRED_KEYWORDS if "," not in k and not k.replace(",", "").isdigit()]
    missing_keywords = [k for k in required_simple if k.lower() not in text_lower]
    if missing_keywords:
        fail(f"L11 LIVE_MODE_REPORT.md missing required keywords: {missing_keywords}")
    # Universe number must appear (either form)
    if "10,831" not in text and "10831" not in text:
        fail(
            f"L11 LIVE_MODE_REPORT.md must explicitly state the scored corpus size "
            f"(10,831 rows or 10831). Universe contract section is mandatory."
        )

    # Required sections (header presence)
    missing_sections = [s for s in REPORT_REQUIRED_SECTIONS if s.lower() not in text_lower]
    if missing_sections:
        fail(
            f"L11 LIVE_MODE_REPORT.md missing required section headers: "
            f"{missing_sections}. Each section must appear in the report."
        )

    import re
    achievability_re = re.compile(
        r"^[#\s>\*\-]*Achievability\s*[:=]\s*(YES|PARTIAL|NO)\b",
        re.MULTILINE | re.IGNORECASE,
    )
    m = achievability_re.search(text)
    if not m:
        fail(
            f"L11 LIVE_MODE_REPORT.md missing explicit achievability line. "
            f"Must contain a line matching `Achievability: YES` (or PARTIAL/NO) "
            f"as the answer to whether ≥99.9% would_fire is achievable. "
            f"Substring presence of those tokens elsewhere in the doc is NOT sufficient."
        )
    info(
        f"L11 LIVE_MODE_REPORT.md: {len(text)} bytes, all required keywords + "
        f"sections present, achievability={m.group(1).upper()} ✓"
    )


# ── Neo4j session helper ─────────────────────────────────────────────
def open_neo4j_session():
    uri = os.environ.get("NEO4J_URI")
    pw = os.environ.get("NEO4J_PASSWORD")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    if not uri or not pw:
        fail("NEO4J_URI / NEO4J_PASSWORD env vars not set", code=2)
    driver = GraphDatabase.driver(uri, auth=(user, pw))
    session = driver.session()
    return driver, session


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    print("=== Goal 3 verifier (hand-written, do not modify) — live-mode resolver ===")
    print(f"Live audit:       {LIVE_AUDIT_PATH}")
    print(f"Live candidates:  {LIVE_CANDIDATES_PATH}")
    print(f"Report:           {LIVE_REPORT_PATH}")
    print()

    check_verifier_git_clean()                                            # L1
    audit_rows, gt_rows, nr_rows = check_files_exist()                    # L2, L3
    candidates = import_candidates()                                      # L4
    check_pit_safety_ast()                                                # L5
    check_universe_coverage(audit_rows, gt_rows, nr_rows, candidates)     # L6

    driver, neo4j_session = open_neo4j_session()
    try:
        check_rederivation(audit_rows, gt_rows, nr_rows, candidates,     # L7
                            neo4j_session)
    finally:
        try:
            neo4j_session.close()
        finally:
            driver.close()

    check_zero_wrong_auto_wrote(audit_rows)                               # L8
    report_rates(audit_rows, gt_rows, nr_rows)                            # L9 (soft)
    check_recommended_candidate(audit_rows, candidates)                   # L10
    check_report()                                                        # L11

    print()
    info("=" * 70)
    info("ALL CHECKS PASSED — Goal 3 live-mode resolver verifier passed")
    info("Achieved rates reported above as INFO. Whether the rate is")
    info("acceptable for production is a human decision (read LIVE_MODE_REPORT.md).")
    info("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
