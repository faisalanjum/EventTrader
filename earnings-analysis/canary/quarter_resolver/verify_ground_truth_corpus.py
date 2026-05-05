#!/usr/bin/env python3
"""
verify_ground_truth_corpus.py — Independent verifier for Goal 1's output.

HAND-WRITTEN BY HUMANS (NOT BY THE AGENT) to prevent self-rubber-stamping.
This script decides whether Goal 1 is complete; the agent's job is to produce
output that passes THIS verifier without modifying it.

DESIGN INVARIANTS (per .claude/plans/quarter-identity-resolver.md):

  L1 — Process integrity (deterministic, 100%):
       Schema correct + universe coverage + per-row invariants + full-corpus
       re-derivation + git-diff freeze + needs_review reason-code validation.

  L2 — Source agreement (~99.5-99.8%):
       Every ground_truth row has Tier-2 XBRL == Tier-4 fiscal_math after
       proximity guard + DENY filter, AND structural same-event constraint
       (matched.created > filed_8k) holds.

  L3 — Human audit (Goal 1.5):
       Out of scope for this verifier; handled by stratified packets.

EXIT CODES:
  0  = corpus passes all checks; Goal 1 verified done
  1  = corpus has fatal violations; Goal 1 not done
  2  = verifier itself failed (Neo4j connection, missing files, env issue,
       or the verifier file was modified after being committed)

USAGE:
  cd /home/faisal/EventMarketDB
  venv/bin/python earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py

CHECKS PERFORMED (in order; first failure exits 1):
  C1.  Verifier file is git-clean (catches Codex-tampering)
  C2.  All required deliverables exist (CSVs + build_corpus.py + REPORT.md)
  C3.  ground_truth.csv schema matches REQUIRED_COLUMNS_GT EXACTLY (no extras)
  C4.  needs_review.csv schema matches REQUIRED_COLUMNS_NR EXACTLY (no extras)
  C5.  No duplicate accession_8k inside ground_truth.csv or needs_review.csv
  C6.  Per-row invariants on ground_truth rows (agreement, valid quarter/year,
       DENY check on raw periodic accession, structural same-event,
       date order, ticker, fye_month range)
  C7.  Per-row invariants on needs_review rows (every row has a reason from
       VALID_REASONS; reason field consistent with row contents)
  C8.  Universe coverage: union(GT.accession_8k, NR.accession_8k) ==
       eligible_universe (computed independently via Cypher);
       no overlap, no missing rows.
  C9.  FULL re-derivation (NOT sample): one bulk Cypher streams every
       eligible row's context; verifier independently classifies EACH row
       and asserts:
        - rows whose canonical classification is "ground_truth" are in GT
          with matching xbrl/math/structural/copied metadata values
        - rows whose canonical classification is a reason code are in NR
          with that exact reason and matching copied metadata fields
       Catches every Codex error, not just statistical sample.
  C10. Row count threshold: GT row count >= MIN_GT_ROW_COUNT.

This module re-uses production helpers (period_to_fiscal,
parse_xbrl_fiscal_identity, should_use_xbrl_fiscal,
XBRL_DENY_PERIODIC_ACCESSIONS, get_fye_month) but applies them independently
of whatever build_corpus.py the agent writes.
"""
from __future__ import annotations
import csv
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
CORPUS_PATH = _HERE / "ground_truth.csv"
NEEDS_REVIEW_PATH = _HERE / "needs_review.csv"
PROJECT_ROOT = _HERE.parents[2]

# ── Production helpers (re-used independently) ───────────────────────
sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

try:
    from fiscal_math import period_to_fiscal
    from get_quarterly_filings import (
        parse_xbrl_fiscal_identity,
        should_use_xbrl_fiscal,
        XBRL_DENY_PERIODIC_ACCESSIONS,
    )
    from fye_month import get_fye_month
except ImportError as e:
    print(f"VERIFIER INFRA ERROR: cannot import production module: {e}", file=sys.stderr)
    sys.exit(2)

# ── Schema (locked) ──────────────────────────────────────────────────
REQUIRED_COLUMNS_GT = {
    "accession_8k", "ticker", "filed_8k", "period_of_report", "fye_month",
    "fy_xbrl", "q_xbrl", "fy_math", "q_math", "agreement",
    "matched_accession_periodic",  # raw, NOT PIT-masked
    "periodic_created",             # filing timestamp of matched periodic
    "form_type_periodic",
}
REQUIRED_COLUMNS_NR = REQUIRED_COLUMNS_GT | {"reason"}

VALID_QUARTERS = {"Q1", "Q2", "Q3", "Q4"}
VALID_FY_RANGE = (2000, 2030)
VALID_FYE_RANGE = (1, 12)

# Reason codes for NR (priority order — first match wins; see C8 logic)
VALID_REASONS = (
    "no_fye",                    # ticker has no resolvable fye_month
    "not_same_event_periodic",   # no q with q.created > r.created exists
    "no_xbrl",                   # same-event periodic exists, lacks XBRL focus
    "denylist",                  # matched_accession_periodic in DENY list
    "proximity_rejected",        # should_use_xbrl_fiscal returned False
    "xbrl_math_disagree",        # proximity OK but XBRL != fiscal_math
)

# Thresholds
MIN_GT_ROW_COUNT = 5_000

# Required ancillary deliverables (per Goal 1 prompt)
REQUIRED_DELIVERABLES = ("ground_truth.csv", "needs_review.csv", "build_corpus.py", "REPORT.md")


# ── Output helpers ────────────────────────────────────────────────────
def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


def warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


# ── C1: git freeze check ─────────────────────────────────────────────
def check_verifier_git_clean() -> None:
    """Catch Codex tampering with the verifier itself."""
    rel_path = str(Path(__file__).resolve().relative_to(PROJECT_ROOT))
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", rel_path],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        fail(f"git diff check failed: {e}", code=2)

    if result.returncode != 0:
        fail(
            f"Verifier file has uncommitted changes vs HEAD: {rel_path}\n"
            f"This blocks completion — Codex may have modified the verifier.\n"
            f"Inspect: git diff -- {rel_path}",
            code=2,
        )

    # Also check verifier is git-tracked at all
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel_path],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        fail(
            f"Verifier file is not git-committed: {rel_path}\n"
            f"Commit it before running /goal so this check has a baseline.",
            code=2,
        )
    info("C1 git-clean: verifier matches committed version ✓")


# ── C2/C3/C4: file + schema checks (strict, no extras) ───────────────
def check_files_exist() -> tuple[list[dict], list[dict]]:
    """C2 — every required deliverable file exists and is non-empty."""
    for fname in REQUIRED_DELIVERABLES:
        path = _HERE / fname
        if not path.is_file():
            fail(f"Required deliverable missing: {path}")
        if path.stat().st_size == 0:
            fail(f"Required deliverable is empty: {path}")
    info(f"C2 deliverables present + non-empty: {list(REQUIRED_DELIVERABLES)} ✓")

    with open(CORPUS_PATH, encoding="utf-8") as f:
        gt_rows = list(csv.DictReader(f))
    with open(NEEDS_REVIEW_PATH, encoding="utf-8") as f:
        nr_rows = list(csv.DictReader(f))

    if not gt_rows:
        fail("ground_truth.csv is empty")

    # C3 — GT schema EXACT match (no extras, no missing)
    actual = set(gt_rows[0].keys())
    missing = REQUIRED_COLUMNS_GT - actual
    extras = actual - REQUIRED_COLUMNS_GT
    if missing or extras:
        msg_parts = []
        if missing:
            msg_parts.append(f"missing={sorted(missing)}")
        if extras:
            msg_parts.append(f"unexpected_extras={sorted(extras)}")
        fail(f"C3 GT schema not exact match: {'; '.join(msg_parts)}")
    info(f"C3 GT schema: exactly {len(REQUIRED_COLUMNS_GT)} required columns ✓")

    # C4 — NR schema EXACT match (only checked when NR has rows; empty NR is allowed but unusual)
    if nr_rows:
        actual = set(nr_rows[0].keys())
        missing = REQUIRED_COLUMNS_NR - actual
        extras = actual - REQUIRED_COLUMNS_NR
        if missing or extras:
            msg_parts = []
            if missing:
                msg_parts.append(f"missing={sorted(missing)}")
            if extras:
                msg_parts.append(f"unexpected_extras={sorted(extras)}")
            fail(f"C4 NR schema not exact match: {'; '.join(msg_parts)}")
        info(f"C4 NR schema: exactly {len(REQUIRED_COLUMNS_NR)} required columns ✓")
    else:
        info(f"C4 NR schema: NR empty (allowed but unusual) ✓")

    return gt_rows, nr_rows


def check_no_duplicates(gt_rows: list[dict], nr_rows: list[dict]) -> None:
    """C5 — no duplicate accession_8k inside either file."""
    from collections import Counter

    def _check(rows: list[dict], name: str) -> None:
        accs = [r["accession_8k"] for r in rows]
        counts = Counter(accs)
        dups = [a for a, c in counts.items() if c > 1]
        if dups:
            sample = ", ".join(dups[:5])
            fail(
                f"C5 {name} has {len(dups)} duplicate accession_8k values. "
                f"Sample: {sample}"
            )

    _check(gt_rows, "ground_truth.csv")
    _check(nr_rows, "needs_review.csv")
    info(f"C5 no duplicates: GT and NR both have unique accession_8k ✓")


# ── C6: GT per-row invariants ────────────────────────────────────────
def _to_bool(v) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes"}


def check_gt_per_row(gt_rows: list[dict]) -> None:
    errors: list[str] = []
    for i, row in enumerate(gt_rows):
        accn = row.get("accession_8k", f"<row {i}>")

        # Agreement
        if not _to_bool(row.get("agreement")):
            errors.append(f"C6 GT row {i} ({accn}): agreement=False — must be True")
            continue
        try:
            fy_x = int(row["fy_xbrl"])
            fy_m = int(row["fy_math"])
        except (ValueError, KeyError):
            errors.append(f"C6 GT row {i} ({accn}): fy_xbrl/fy_math not int")
            continue
        q_x = str(row["q_xbrl"]).strip()
        q_m = str(row["q_math"]).strip()
        if (fy_x, q_x) != (fy_m, q_m):
            errors.append(
                f"C6 GT row {i} ({accn}): XBRL=({fy_x},{q_x}) != math=({fy_m},{q_m})"
            )
            continue

        if q_x not in VALID_QUARTERS:
            errors.append(f"C6 GT row {i} ({accn}): q_xbrl={q_x!r}")
        if not (VALID_FY_RANGE[0] <= fy_x <= VALID_FY_RANGE[1]):
            errors.append(f"C6 GT row {i} ({accn}): fy_xbrl={fy_x} out of range")

        # DENY check on RAW matched_accession_periodic (not PIT-masked)
        raw_acc = (row.get("matched_accession_periodic") or "").strip()
        if not raw_acc:
            errors.append(f"C6 GT row {i} ({accn}): matched_accession_periodic empty")
        elif raw_acc in XBRL_DENY_PERIODIC_ACCESSIONS:
            errors.append(
                f"C6 GT row {i} ({accn}): matched_accession_periodic {raw_acc} is in DENY"
            )

        # Structural: periodic_created > filed_8k (same-event constraint)
        try:
            f8k = datetime.fromisoformat(str(row["filed_8k"]).replace("Z", "+00:00"))
            pcr = datetime.fromisoformat(
                str(row["periodic_created"]).replace("Z", "+00:00")
            )
            if pcr <= f8k:
                errors.append(
                    f"C6 GT row {i} ({accn}): periodic_created ({pcr}) NOT > "
                    f"filed_8k ({f8k}) — FCX-shape contamination"
                )
        except (ValueError, KeyError, TypeError):
            errors.append(f"C6 GT row {i} ({accn}): bad filed_8k or periodic_created")

        # filed_8k > period_of_report
        try:
            f8k_d = date.fromisoformat(str(row["filed_8k"])[:10])
            por_d = date.fromisoformat(str(row["period_of_report"])[:10])
            if f8k_d <= por_d:
                errors.append(
                    f"C6 GT row {i} ({accn}): filed_8k {f8k_d} <= period_of_report {por_d}"
                )
        except (ValueError, KeyError, TypeError):
            errors.append(f"C6 GT row {i} ({accn}): bad date format")

        ticker = row.get("ticker", "")
        if (
            ticker != ticker.upper()
            or not ticker.isalpha()
            or not (1 <= len(ticker) <= 5)
        ):
            errors.append(f"C6 GT row {i} ({accn}): bad ticker {ticker!r}")

        try:
            fye = int(row["fye_month"])
            if not (VALID_FYE_RANGE[0] <= fye <= VALID_FYE_RANGE[1]):
                errors.append(f"C6 GT row {i} ({accn}): fye_month={fye}")
        except (ValueError, KeyError):
            errors.append(f"C6 GT row {i} ({accn}): fye_month not int")

    if errors:
        for e in errors[:25]:
            print(f"  {e}")
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more")
        fail(f"C6 GT per-row: {len(errors)} violations")
    info(f"C6 GT per-row: {len(gt_rows)} rows, 0 violations ✓")


# ── C7: NR per-row invariants ────────────────────────────────────────
def check_nr_per_row(nr_rows: list[dict]) -> None:
    errors: list[str] = []
    for i, row in enumerate(nr_rows):
        accn = row.get("accession_8k", f"<row {i}>")
        reason = (row.get("reason") or "").strip()
        if reason not in VALID_REASONS:
            errors.append(
                f"C7 NR row {i} ({accn}): reason={reason!r} not in {VALID_REASONS}"
            )

        ticker = row.get("ticker", "")
        if ticker != ticker.upper() or not ticker.isalpha():
            errors.append(f"C7 NR row {i} ({accn}): bad ticker {ticker!r}")

    if errors:
        for e in errors[:25]:
            print(f"  {e}")
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more")
        fail(f"C7 NR per-row: {len(errors)} violations")
    info(f"C7 NR per-row: {len(nr_rows)} rows, 0 violations ✓")


# ── Neo4j helpers ─────────────────────────────────────────────────────
def _neo4j_driver():
    try:
        from dotenv import load_dotenv
        from neo4j import GraphDatabase
        load_dotenv(str(PROJECT_ROOT / ".env"), override=True)
        uri = os.getenv("NEO4J_URI", "bolt://10.102.222.120:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        if not password:
            fail("NEO4J_PASSWORD not set", code=2)
        return GraphDatabase.driver(uri, auth=(user, password))
    except Exception as e:
        fail(f"Neo4j driver init failed: {e}", code=2)


# Bulk universe + per-row context query — single round-trip, returns ALL
# eligible 8-Ks with everything the verifier needs to independently classify
# each row. Used by C8 (universe) + C9 (full re-derivation) together.
_BULK_QUERY = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE r.formType = '8-K' AND r.items CONTAINS '2.02' AND pf.daily_stock IS NOT NULL
WITH r, c
OPTIONAL CALL (r, c) {
  MATCH (q:Report)-[:PRIMARY_FILER]->(c)
  WHERE q.formType IN ['10-Q', '10-K']
        AND date(q.periodOfReport) < date(datetime(r.created))
        AND datetime(q.created) > datetime(r.created)
  WITH q ORDER BY q.periodOfReport DESC LIMIT 1
  OPTIONAL MATCH (q)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fp:Fact {qname: 'dei:DocumentFiscalPeriodFocus'})
  WITH q, collect(DISTINCT fp.value) AS xbrl_periods
  OPTIONAL MATCH (q)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fy:Fact {qname: 'dei:DocumentFiscalYearFocus'})
  WITH q, xbrl_periods, collect(DISTINCT fy.value) AS xbrl_years
  RETURN q.accessionNo AS matched_accession_periodic,
         q.created AS periodic_created,
         q.periodOfReport AS period_of_report,
         q.formType AS form_type_periodic,
         CASE WHEN size(xbrl_periods) = 1 THEN head(xbrl_periods) END AS xbrl_period,
         CASE WHEN size(xbrl_years) = 1 THEN head(xbrl_years) END AS xbrl_year
}
RETURN r.accessionNo AS accession_8k,
       r.created AS filed_8k,
       c.ticker AS ticker,
       matched_accession_periodic,
       periodic_created,
       period_of_report,
       form_type_periodic,
       xbrl_period,
       xbrl_year
"""


def _to_str(val) -> str | None:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _blank(v) -> bool:
    return v is None or str(v).strip() == ""


def _same_datetime(a, b) -> bool:
    if _blank(a) and _blank(b):
        return True
    if _blank(a) or _blank(b):
        return False
    try:
        return datetime.fromisoformat(str(a).replace("Z", "+00:00")) == datetime.fromisoformat(
            str(b).replace("Z", "+00:00")
        )
    except ValueError:
        return str(a).strip() == str(b).strip()


def _same_date(a, b) -> bool:
    if _blank(a) and _blank(b):
        return True
    if _blank(a) or _blank(b):
        return False
    return str(a)[:10] == str(b)[:10]


def _maybe_int_str(v) -> str:
    if _blank(v):
        return ""
    return str(int(v))


def _expected_row_fields(ctx: dict) -> dict[str, str]:
    """Canonical row fields derived independently from Neo4j + production helpers.

    This is stricter than classifying GT vs NR: it verifies that every copied
    metadata field in the CSV is faithful to the raw context too.
    """
    fye = get_fye_month(ctx["ticker"])
    xbrl = parse_xbrl_fiscal_identity(ctx.get("xbrl_year"), ctx.get("xbrl_period"))

    fallback = None
    if fye is not None and ctx.get("period_of_report"):
        try:
            d = date.fromisoformat(str(ctx["period_of_report"])[:10])
            form_type = ctx.get("form_type_periodic") or "10-Q"
            fallback = period_to_fiscal(d.year, d.month, d.day, fye, form_type)
        except ValueError:
            fallback = None

    return {
        "accession_8k": str(ctx.get("accession_8k") or ""),
        "ticker": str(ctx.get("ticker") or ""),
        "filed_8k": str(ctx.get("filed_8k") or ""),
        "period_of_report": str(ctx.get("period_of_report") or "")[:10] if ctx.get("period_of_report") else "",
        "fye_month": _maybe_int_str(fye),
        "fy_xbrl": _maybe_int_str(xbrl[0]) if xbrl else "",
        "q_xbrl": str(xbrl[1]) if xbrl else "",
        "fy_math": _maybe_int_str(fallback[0]) if fallback else "",
        "q_math": str(fallback[1]) if fallback else "",
        "agreement": (
            "true"
            if xbrl and fallback and xbrl == fallback
            else ("false" if xbrl and fallback else "")
        ),
        "matched_accession_periodic": str(ctx.get("matched_accession_periodic") or ""),
        "periodic_created": str(ctx.get("periodic_created") or ""),
        "form_type_periodic": str(ctx.get("form_type_periodic") or ""),
    }


def _compare_row_fields(
    *,
    accn: str,
    row: dict,
    expected: dict[str, str],
    fields: set[str],
    mismatches: list[str],
    prefix: str,
) -> None:
    for field in sorted(fields):
        actual = row.get(field, "")
        exp = expected.get(field, "")

        if field in {"filed_8k", "periodic_created"}:
            ok = _same_datetime(exp, actual)
        elif field == "period_of_report":
            ok = _same_date(exp, actual)
        elif field in {"fye_month", "fy_xbrl", "fy_math"}:
            ok = _maybe_int_str(exp) == _maybe_int_str(actual)
        elif field == "agreement":
            ok = str(actual).strip().lower() == str(exp).strip().lower()
        else:
            ok = str(actual or "").strip() == str(exp or "").strip()

        if not ok:
            mismatches.append(
                f"{accn}: {prefix} field {field} expected={exp!r} actual={actual!r}"
            )


def _canonical_reason(ctx: dict) -> tuple[str | None, dict]:
    """Given a per-row context dict from Neo4j, return (reason or None for GT, metadata).

    Priority order (first match wins):
      no_fye → not_same_event_periodic → no_xbrl → denylist
        → proximity_rejected → xbrl_math_disagree → (None == GT)
    """
    ticker = ctx["ticker"]
    fye = get_fye_month(ticker)
    if fye is None:
        return ("no_fye", {})

    if not ctx.get("matched_accession_periodic"):
        return ("not_same_event_periodic", {})

    xbrl = parse_xbrl_fiscal_identity(ctx.get("xbrl_year"), ctx.get("xbrl_period"))
    if xbrl is None:
        return ("no_xbrl", {})

    raw_acc = ctx["matched_accession_periodic"]
    if raw_acc in XBRL_DENY_PERIODIC_ACCESSIONS:
        return ("denylist", {})

    por = ctx.get("period_of_report")
    if not por:
        return ("no_xbrl", {})  # missing period → can't compute fiscal_math
    try:
        d = date.fromisoformat(str(por)[:10])
    except ValueError:
        return ("no_xbrl", {})

    form_type = ctx.get("form_type_periodic") or "10-Q"
    fallback = period_to_fiscal(d.year, d.month, d.day, fye, form_type)

    if not should_use_xbrl_fiscal(fallback, xbrl):
        return ("proximity_rejected", {"xbrl": xbrl, "fallback": fallback})

    if xbrl != fallback:
        return ("xbrl_math_disagree", {"xbrl": xbrl, "fallback": fallback})

    return (None, {"xbrl": xbrl, "fallback": fallback, "fye": fye})


# ── C8 + C9: bulk fetch + universe coverage + FULL re-derivation ────
def check_universe_and_full_rederivation(
    gt_rows: list[dict], nr_rows: list[dict]
) -> None:
    """Single bulk Cypher → independently classify EVERY eligible row →
    compare against corpus. No sampling: every row is checked.

    C8: union(GT, NR) == eligible universe, no overlap, no missing.
    C9: every GT row matches independent classification = "ground_truth"
        with matching xbrl/math/structural; every NR row matches
        independent classification = its claimed reason.
    """
    driver = _neo4j_driver()
    info("Bulk-fetching all eligible 8-Ks + matched periodic context (one Cypher)...")
    try:
        with driver.session() as session:
            results = list(session.run(_BULK_QUERY))
    finally:
        driver.close()
    info(f"Bulk fetch returned {len(results)} eligible rows")

    # Build universe → context dict
    universe_ctx: dict[str, dict] = {}
    for r in results:
        accn = r["accession_8k"]
        universe_ctx[accn] = {
            "accession_8k": accn,
            "ticker": r["ticker"],
            "filed_8k": _to_str(r["filed_8k"]),
            "matched_accession_periodic": r["matched_accession_periodic"],
            "periodic_created": _to_str(r["periodic_created"]),
            "period_of_report": _to_str(r["period_of_report"]),
            "form_type_periodic": r["form_type_periodic"],
            "xbrl_period": r["xbrl_period"],
            "xbrl_year": r["xbrl_year"],
        }

    universe = set(universe_ctx.keys())
    gt_by_accn = {r["accession_8k"]: r for r in gt_rows}
    nr_by_accn = {r["accession_8k"]: r for r in nr_rows}
    gt_set = set(gt_by_accn.keys())
    nr_set = set(nr_by_accn.keys())

    # ── C8: universe coverage ────────────────────────────────────────
    overlap = gt_set & nr_set
    if overlap:
        fail(
            f"C8 universe: {len(overlap)} accessions in BOTH GT and NR. "
            f"Sample: {sorted(overlap)[:5]}"
        )
    union = gt_set | nr_set
    missing = universe - union
    if missing:
        fail(
            f"C8 universe: {len(missing)} accessions in eligible universe but "
            f"absent from both CSVs (cherry-picking?). "
            f"Sample: {sorted(missing)[:5]}"
        )
    extra = union - universe
    if extra:
        fail(
            f"C8 universe: {len(extra)} accessions in CSVs but NOT eligible. "
            f"Sample: {sorted(extra)[:5]}"
        )
    info(
        f"C8 universe coverage: {len(universe)} eligible = "
        f"{len(gt_set)} GT + {len(nr_set)} NR (no overlap, no missing) ✓"
    )

    # ── C9: FULL re-derivation across every eligible row ────────────
    info(
        f"C9 FULL re-derivation: independently classifying {len(universe)} rows..."
    )
    mismatches: list[str] = []
    gt_checked = 0
    nr_checked = 0

    for accn, ctx in universe_ctx.items():
        reason, meta = _canonical_reason(ctx)
        expected = _expected_row_fields(ctx)

        if reason is None:
            # Should be in GT
            if accn not in gt_by_accn:
                mismatches.append(
                    f"{accn}: classified as ground_truth but absent from GT "
                    f"(found in NR with reason={nr_by_accn.get(accn, {}).get('reason', '?')!r})"
                )
                continue
            gt_checked += 1
            row = gt_by_accn[accn]
            xbrl = meta["xbrl"]
            fallback = meta["fallback"]
            before_mismatch_count = len(mismatches)
            _compare_row_fields(
                accn=accn,
                row=row,
                expected=expected,
                fields=REQUIRED_COLUMNS_GT,
                mismatches=mismatches,
                prefix="GT",
            )
            if len(mismatches) != before_mismatch_count:
                continue

            try:
                if (xbrl[0], xbrl[1]) != (int(row["fy_xbrl"]), row["q_xbrl"].strip()):
                    mismatches.append(
                        f"{accn}: GT XBRL re-derived {xbrl} != corpus "
                        f"({row['fy_xbrl']}, {row['q_xbrl']})"
                    )
                    continue
                if (fallback[0], fallback[1]) != (
                    int(row["fy_math"]),
                    row["q_math"].strip(),
                ):
                    mismatches.append(
                        f"{accn}: GT math re-derived {fallback} != corpus "
                        f"({row['fy_math']}, {row['q_math']})"
                    )
                    continue
            except (ValueError, KeyError):
                mismatches.append(f"{accn}: GT row has malformed fy/q fields")
                continue

            if not ctx["matched_accession_periodic"]:
                mismatches.append(
                    f"{accn}: classified as ground_truth but no matched periodic in Neo4j"
                )
                continue
            if ctx["matched_accession_periodic"] != (
                row.get("matched_accession_periodic") or ""
            ).strip():
                mismatches.append(
                    f"{accn}: matched_accession_periodic Neo4j="
                    f"{ctx['matched_accession_periodic']!r} corpus="
                    f"{row.get('matched_accession_periodic')!r}"
                )
                continue
            if ctx["periodic_created"] != (row.get("periodic_created") or "").strip():
                # Allow timestamp formatting differences as long as datetime parses equal
                try:
                    a = datetime.fromisoformat(
                        str(ctx["periodic_created"]).replace("Z", "+00:00")
                    )
                    b = datetime.fromisoformat(
                        str(row.get("periodic_created", "")).replace("Z", "+00:00")
                    )
                    if a != b:
                        mismatches.append(
                            f"{accn}: periodic_created Neo4j={a} corpus={b}"
                        )
                except (ValueError, TypeError):
                    mismatches.append(
                        f"{accn}: periodic_created unparseable in corpus or Neo4j"
                    )
        else:
            # Should be in NR with this reason
            if accn not in nr_by_accn:
                mismatches.append(
                    f"{accn}: classified as NR/{reason} but absent from NR "
                    f"(found in GT)" if accn in gt_by_accn else
                    f"{accn}: classified as NR/{reason} but absent from both"
                )
                continue
            nr_checked += 1
            claimed = (nr_by_accn[accn].get("reason") or "").strip()
            if claimed != reason:
                mismatches.append(
                    f"{accn}: NR reason claimed={claimed!r} actual={reason!r}"
                )
                continue
            before_mismatch_count = len(mismatches)
            _compare_row_fields(
                accn=accn,
                row=nr_by_accn[accn],
                expected=expected,
                fields=REQUIRED_COLUMNS_GT,
                mismatches=mismatches,
                prefix="NR",
            )
            if len(mismatches) != before_mismatch_count:
                continue

    if mismatches:
        for m in mismatches[:30]:
            print(f"  {m}")
        if len(mismatches) > 30:
            print(f"  ... and {len(mismatches) - 30} more")
        fail(
            f"C9 FULL re-derivation: {len(mismatches)} mismatches "
            f"(checked {gt_checked} GT + {nr_checked} NR = "
            f"{gt_checked + nr_checked} total)"
        )
    info(
        f"C9 FULL re-derivation: 0 mismatches across {gt_checked} GT + "
        f"{nr_checked} NR = {gt_checked + nr_checked} rows ✓"
    )


# ── C10: row count threshold ─────────────────────────────────────────
def check_row_count(gt_rows: list[dict]) -> None:
    if len(gt_rows) < MIN_GT_ROW_COUNT:
        fail(f"C10 row count {len(gt_rows)} < threshold {MIN_GT_ROW_COUNT}")
    info(f"C10 GT row count: {len(gt_rows)} (>= {MIN_GT_ROW_COUNT}) ✓")


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    print(f"=== Goal 1 verifier (hand-written, do not modify) ===")
    print(f"Corpus:        {CORPUS_PATH}")
    print(f"NEEDS_REVIEW:  {NEEDS_REVIEW_PATH}")
    print()

    check_verifier_git_clean()                         # C1
    gt_rows, nr_rows = check_files_exist()             # C2 + C3 + C4
    check_no_duplicates(gt_rows, nr_rows)              # C5
    check_gt_per_row(gt_rows)                          # C6
    check_nr_per_row(nr_rows)                          # C7
    check_universe_and_full_rederivation(gt_rows, nr_rows)  # C8 + C9
    check_row_count(gt_rows)                           # C10

    print()
    info("=" * 60)
    info("ALL CHECKS PASSED — Goal 1 corpus verified")
    info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
