#!/usr/bin/env python3
"""
CLI wrapper for fiscal→calendar date resolution.

Bridges fiscal_to_dates() (which needs a Neo4j session) to the guidance
extraction agent (which uses MCP for Neo4j).

Usage:
    echo '<period_json>' | python3 fiscal_resolve.py TICKER FISCAL_YEAR FISCAL_QUARTER FYE_MONTH

    period_json: JSON array of {u_id, start_date, end_date} from MCP Cypher query.
    FISCAL_YEAR: e.g. 2025
    FISCAL_QUARTER: Q1, Q2, Q3, Q4, or FY
    FYE_MONTH: 1-12 (fiscal year end month)

Output (JSON):
    {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD",
     "period_u_id": "duration_...", "period_node_type": "duration",
     "source": "lookup"|"fallback"}

Implements §15G of the Guidance System Implementation Spec (v2.3).
Imports period_to_fiscal() and _compute_fiscal_dates() from get_quarterly_filings.py
without modification (Non-negotiable #1).
"""

import json
import sys
import types
from datetime import date, timedelta

# Stub modules that get_quarterly_filings imports at top-level but we don't need.
# The wrapper only uses pure functions (period_to_fiscal, _compute_fiscal_dates,
# _normalize_fiscal_quarter) — none of which touch Neo4j or dotenv.
for _mod_name in ('dotenv', 'neo4j'):
    if _mod_name not in sys.modules:
        _stub = types.ModuleType(_mod_name)
        _stub.load_dotenv = lambda *a, **kw: None
        _stub.GraphDatabase = type('GraphDatabase', (), {'driver': staticmethod(lambda *a, **kw: None)})
        sys.modules[_mod_name] = _stub

# Import non-negotiable functions (no modification)
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
from get_quarterly_filings import (
    period_to_fiscal,
    _compute_fiscal_dates,
    _normalize_fiscal_quarter,
)


def _resolve_from_periods(periods_raw, fye_month, fiscal_year, fq):
    """
    Replicate fiscal_to_dates() Phase 1 lookup using pre-fetched Period data.

    Args:
        periods_raw: list of {u_id, start_date, end_date} dicts (from MCP query)
        fye_month: fiscal year end month (1-12)
        fiscal_year: e.g. 2025
        fq: normalized fiscal quarter ("Q1"..."Q4" or "FY")

    Returns:
        (start_date, end_date) as ISO strings, or None if no match.
    """
    # Compute fallback for tie-breaking (same logic as fiscal_to_dates)
    fallback_start_str, fallback_end_str = _compute_fiscal_dates(fye_month, fiscal_year, fq)
    fallback_start = date.fromisoformat(fallback_start_str)
    fallback_end = date.fromisoformat(fallback_end_str)
    expected_days = (fallback_end - fallback_start).days + 1

    # Parse and classify periods
    periods = []
    for r in periods_raw:
        try:
            s = date.fromisoformat(r["start_date"])
            e = date.fromisoformat(r["end_date"])
        except (TypeError, ValueError, KeyError):
            continue
        if e < s:
            continue
        days = (e - s).days + 1
        fy_10q, fq_10q = period_to_fiscal(e.year, e.month, e.day, fye_month, "10-Q")
        fy_10k, fq_10k = period_to_fiscal(e.year, e.month, e.day, fye_month, "10-K")
        periods.append({
            "u_id": r.get("u_id", ""),
            "s": s, "e": e, "days": days,
            "fy_10q": fy_10q, "fq_10q": fq_10q,
            "fy_10k": fy_10k, "fq_10k": fq_10k,
        })

    quarter_like = [p for p in periods if 75 <= p["days"] <= 120]
    year_like = [p for p in periods if 340 <= p["days"] <= 380]

    def pick_best(candidates):
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda p: (
                abs((p["e"] - fallback_end).days),
                abs((p["s"] - fallback_start).days),
                abs(p["days"] - expected_days),
                -p["e"].toordinal(),
                p["u_id"] or "",
            ),
        )

    # FY lookup
    if fq == "FY":
        fy_candidates = [p for p in year_like if p["fy_10k"] == fiscal_year]
        best = pick_best(fy_candidates)
        if best:
            return best["s"].isoformat(), best["e"].isoformat()
        return None

    # Q1/Q2/Q3 lookup
    if fq in {"Q1", "Q2", "Q3"}:
        q_candidates = [
            p for p in quarter_like
            if p["fy_10q"] == fiscal_year and p["fq_10q"] == fq
        ]
        best = pick_best(q_candidates)
        if best:
            return best["s"].isoformat(), best["e"].isoformat()
        return None

    # Q4 lookup (most complex — mirrors fiscal_to_dates exactly)
    if fq == "Q4":
        fy_candidates = [p for p in year_like if p["fy_10k"] == fiscal_year]
        best_fy = pick_best(fy_candidates)
        if best_fy:
            # Try quarter-like periods ending on FY end date
            q4_candidates = [
                p for p in quarter_like
                if p["e"] == best_fy["e"] and p["s"] >= best_fy["s"]
            ]
            best_q4 = pick_best(q4_candidates)
            if best_q4:
                return best_q4["s"].isoformat(), best_q4["e"].isoformat()

            # Derive from Q3 end + 1 day to FY end
            q3_candidates = [
                p for p in quarter_like
                if p["fy_10q"] == fiscal_year and p["fq_10q"] == "Q3"
                and p["e"] < best_fy["e"]
            ]
            if q3_candidates:
                _, exp_q3_end_str = _compute_fiscal_dates(fye_month, fiscal_year, "Q3")
                exp_q3_end = date.fromisoformat(exp_q3_end_str)
                q3 = min(q3_candidates, key=lambda p: abs((p["e"] - exp_q3_end).days))
                q4_start = q3["e"] + timedelta(days=1)
                q4_end = best_fy["e"]
                q4_days = (q4_end - q4_start).days
                if q4_start <= q4_end and q4_days >= 60:
                    return q4_start.isoformat(), q4_end.isoformat()

            # Infer quarter length from available quarter-like periods in same FY
            same_fy_quarters = [
                p["days"] for p in quarter_like
                if p["s"] >= best_fy["s"] and p["e"] <= best_fy["e"]
            ]
            if same_fy_quarters:
                q_len = round(sum(same_fy_quarters) / len(same_fy_quarters))
            else:
                q_len = round(best_fy["days"] / 4)
            q_len = max(75, min(120, q_len))

            q4_end = best_fy["e"]
            q4_start = q4_end - timedelta(days=q_len - 1)
            if q4_start < best_fy["s"]:
                q4_start = best_fy["s"]
            return q4_start.isoformat(), q4_end.isoformat()

    return None


def resolve(ticker, fiscal_year, fiscal_quarter, fye_month, periods_json):
    """
    Main resolution entry point.

    Returns dict with start_date, end_date, period_u_id, period_node_type, source.
    """
    fq = _normalize_fiscal_quarter(fiscal_quarter)
    fiscal_year = int(fiscal_year)
    fye_month = int(fye_month)

    if not 1 <= fye_month <= 12:
        return {"error": f"fye_month must be 1-12, got {fye_month}"}

    # Phase 1: Lookup from pre-fetched periods
    periods_raw = json.loads(periods_json) if isinstance(periods_json, str) else periods_json
    result = _resolve_from_periods(periods_raw, fye_month, fiscal_year, fq)
    source = "lookup"

    # Phase 2: Deterministic fallback
    if result is None:
        start_date, end_date = _compute_fiscal_dates(fye_month, fiscal_year, fq)
        source = "fallback"
    else:
        start_date, end_date = result

    period_u_id = f"duration_{start_date}_{end_date}"

    return {
        "start_date": start_date,
        "end_date": end_date,
        "period_u_id": period_u_id,
        "period_node_type": "duration",
        "source": source,
    }


def main():
    if len(sys.argv) != 5:
        print(json.dumps({
            "error": "Usage: echo '<periods_json>' | python3 fiscal_resolve.py TICKER FISCAL_YEAR FISCAL_QUARTER FYE_MONTH"
        }))
        sys.exit(1)

    ticker = sys.argv[1]
    fiscal_year = sys.argv[2]
    fiscal_quarter = sys.argv[3]
    fye_month = sys.argv[4]

    # Read pre-fetched Period data from stdin
    periods_json = sys.stdin.read().strip()
    if not periods_json:
        periods_json = "[]"

    try:
        result = resolve(ticker, fiscal_year, fiscal_quarter, fye_month, periods_json)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
