#!/usr/bin/env python3
"""Build Goal 1 quarter-resolver ground-truth corpus.

Outputs:
  - ground_truth.csv
  - needs_review.csv
  - REPORT.md

The construction intentionally mirrors the locked Goal 1 contract while
leaving the independent verifier untouched.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]

sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from fiscal_math import period_to_fiscal
from get_quarterly_filings import (
    XBRL_DENY_PERIODIC_ACCESSIONS,
    parse_xbrl_fiscal_identity,
    should_use_xbrl_fiscal,
)
from fye_month import get_fye_month


GT_COLUMNS = [
    "accession_8k",
    "ticker",
    "filed_8k",
    "period_of_report",
    "fye_month",
    "fy_xbrl",
    "q_xbrl",
    "fy_math",
    "q_math",
    "agreement",
    "matched_accession_periodic",
    "periodic_created",
    "form_type_periodic",
]
NR_COLUMNS = GT_COLUMNS + ["reason"]

VALID_REASONS = (
    "no_fye",
    "not_same_event_periodic",
    "no_xbrl",
    "denylist",
    "proximity_rejected",
    "xbrl_math_disagree",
)

QUERY = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE r.formType = '8-K' AND r.items CONTAINS '2.02' AND pf.daily_stock IS NOT NULL
  AND ($ticker IS NULL OR c.ticker = $ticker)
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
       c.sector AS sector,
       c.industry AS industry,
       matched_accession_periodic,
       periodic_created,
       period_of_report,
       form_type_periodic,
       xbrl_period,
       xbrl_year
"""


def to_str(val) -> str:
    if val is None:
        return ""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def maybe_int_str(val) -> str:
    if val is None or str(val).strip() == "":
        return ""
    return str(int(val))


def neo4j_driver():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(str(PROJECT_ROOT / ".env"), override=True)
    uri = os.getenv("NEO4J_URI", "bolt://10.102.222.120:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD not set")
    return GraphDatabase.driver(uri, auth=(user, password))


def fetch_contexts(ticker: str | None) -> list[dict]:
    driver = neo4j_driver()
    try:
        with driver.session() as session:
            rows = list(session.run(QUERY, ticker=ticker.upper() if ticker else None))
    finally:
        driver.close()

    contexts: list[dict] = []
    for row in rows:
        contexts.append(
            {
                "accession_8k": row["accession_8k"],
                "ticker": row["ticker"],
                "filed_8k": to_str(row["filed_8k"]),
                "sector": row["sector"] or "",
                "industry": row["industry"] or "",
                "matched_accession_periodic": row["matched_accession_periodic"] or "",
                "periodic_created": to_str(row["periodic_created"]),
                "period_of_report": to_str(row["period_of_report"]),
                "form_type_periodic": row["form_type_periodic"] or "",
                "xbrl_period": row["xbrl_period"],
                "xbrl_year": row["xbrl_year"],
            }
        )
    return contexts


def row_fields(ctx: dict, fye_cache: dict[str, int | None]) -> dict[str, str]:
    ticker = ctx["ticker"]
    if ticker not in fye_cache:
        fye_cache[ticker] = get_fye_month(ticker)
    fye = fye_cache[ticker]

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
        "ticker": str(ticker or ""),
        "filed_8k": str(ctx.get("filed_8k") or ""),
        "period_of_report": str(ctx.get("period_of_report") or "")[:10]
        if ctx.get("period_of_report")
        else "",
        "fye_month": maybe_int_str(fye),
        "fy_xbrl": maybe_int_str(xbrl[0]) if xbrl else "",
        "q_xbrl": str(xbrl[1]) if xbrl else "",
        "fy_math": maybe_int_str(fallback[0]) if fallback else "",
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


def classify(ctx: dict, fields: dict[str, str]) -> str | None:
    if fields["fye_month"] == "":
        return "no_fye"

    if not ctx.get("matched_accession_periodic"):
        return "not_same_event_periodic"

    xbrl = parse_xbrl_fiscal_identity(ctx.get("xbrl_year"), ctx.get("xbrl_period"))
    if xbrl is None:
        return "no_xbrl"

    raw_acc = ctx["matched_accession_periodic"]
    if raw_acc in XBRL_DENY_PERIODIC_ACCESSIONS:
        return "denylist"

    por = ctx.get("period_of_report")
    if not por:
        return "no_xbrl"

    try:
        fye = int(fields["fye_month"])
        d = date.fromisoformat(str(por)[:10])
    except ValueError:
        return "no_xbrl"

    form_type = ctx.get("form_type_periodic") or "10-Q"
    fallback = period_to_fiscal(d.year, d.month, d.day, fye, form_type)

    if not should_use_xbrl_fiscal(fallback, xbrl):
        return "proximity_rejected"

    if xbrl != fallback:
        return "xbrl_math_disagree"

    return None


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=columns,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def render_report(
    *,
    contexts: list[dict],
    gt_rows: list[dict[str, str]],
    nr_rows: list[dict[str, str]],
    reason_counts: Counter,
) -> str:
    ticker_counts = Counter(ctx["ticker"] for ctx in contexts)
    gt_ticker_counts = Counter(row["ticker"] for row in gt_rows)
    nr_ticker_counts = Counter(row["ticker"] for row in nr_rows)
    sector_counts = Counter((ctx.get("sector") or "Unknown") for ctx in contexts)

    top_tickers = ", ".join(f"{t} ({n})" for t, n in ticker_counts.most_common(10))
    top_gt = ", ".join(f"{t} ({n})" for t, n in gt_ticker_counts.most_common(8))
    top_nr = ", ".join(f"{t} ({n})" for t, n in nr_ticker_counts.most_common(8))
    top_sectors = ", ".join(f"{s} ({n})" for s, n in sector_counts.most_common(8))
    reason_lines = "\n".join(
        f"- {reason}: {reason_counts.get(reason, 0)}" for reason in VALID_REASONS
    )

    return f"""# Goal 1 Ground-Truth Corpus Report

Eligible universe size is {len(contexts):,} earnings 8-K rows, defined by `formType="8-K"`, `items CONTAINS "2.02"`, and a non-null `PRIMARY_FILER.daily_stock`. The generated corpus assigns every eligible accession to exactly one output file: {len(gt_rows):,} rows in `ground_truth.csv` and {len(nr_rows):,} rows in `needs_review.csv`.

`ground_truth.csv` contains only same-event historical rows where the matched 10-Q/10-K was filed after the 8-K, the periodic filing has parseable SEC XBRL fiscal focus tags, the periodic accession is not in the XBRL denylist, the XBRL/fiscal-math proximity guard accepts the pair, and the XBRL and fiscal-math identities agree. This is a high-confidence historical benchmark corpus, not a live-mode solution.

Needs-review breakdown:
{reason_lines}

Ticker distribution is broad across the eligible universe. The most represented tickers are {top_tickers or "n/a"}. Ground-truth-heavy tickers include {top_gt or "n/a"}, while needs-review-heavy tickers include {top_nr or "n/a"}. Sector distribution from available company metadata is led by {top_sectors or "Unknown"}; rows without sector metadata are grouped as `Unknown`.

The main unusual finding is expected from the Goal 1 design: `not_same_event_periodic` rows are not defects in the historical ground-truth set. They are the FCX-shaped/live-mode cases where no later same-quarter periodic filing exists in the graph at the 8-K point-in-time, or the eligible 8-K is too recent for such a filing. Those rows remain classified residuals for Goal 2/3 handling and must fail closed rather than being forced into the benchmark.
"""


def build(ticker: str | None = None) -> tuple[int, int]:
    contexts = fetch_contexts(ticker)
    fye_cache: dict[str, int | None] = {}
    gt_rows: list[dict[str, str]] = []
    nr_rows: list[dict[str, str]] = []
    reason_counts: Counter = Counter()

    for ctx in contexts:
        fields = row_fields(ctx, fye_cache)
        reason = classify(ctx, fields)
        if reason is None:
            gt_rows.append({col: fields[col] for col in GT_COLUMNS})
        else:
            reason_counts[reason] += 1
            nr_rows.append({**{col: fields[col] for col in GT_COLUMNS}, "reason": reason})

    sort_key = lambda row: (row["ticker"], row["filed_8k"], row["accession_8k"])
    gt_rows.sort(key=sort_key)
    nr_rows.sort(key=sort_key)

    suffix = f".{ticker.upper()}" if ticker else ""
    write_csv(HERE / f"ground_truth{suffix}.csv", GT_COLUMNS, gt_rows)
    write_csv(HERE / f"needs_review{suffix}.csv", NR_COLUMNS, nr_rows)
    if ticker is None:
        (HERE / "REPORT.md").write_text(
            render_report(
                contexts=contexts,
                gt_rows=gt_rows,
                nr_rows=nr_rows,
                reason_counts=reason_counts,
            ),
            encoding="utf-8",
        )

    return len(gt_rows), len(nr_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", help="Optional ticker smoke-test mode.")
    args = parser.parse_args()

    gt_count, nr_count = build(args.ticker)
    label = f" for {args.ticker.upper()}" if args.ticker else ""
    print(f"wrote {gt_count:,} GT rows and {nr_count:,} NR rows{label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
