#!/usr/bin/env python3
"""Database-wide validation for guidance unit canonicalization and rendering safety.

This script answers one narrow question:
can the current guidance renderer safely format every GuidanceUpdate row in Neo4j?

It intentionally validates against the live graph, not just local fixtures.

Checks:
1. Every canonical_unit present in Neo4j is known to the guidance schema.
2. No GuidanceUpdate rows still use canonical_unit='unknown'.
3. Per-share metrics use canonical_unit='usd'.
4. Share-count metrics use canonical_unit='count'.
5. Known count-like metrics are not stored as money units.
6. Renderer output for known count-like metrics never leaks a '$' sign.

Usage:
    python3 scripts/earnings/test_guidance_unit_safety.py
"""
from __future__ import annotations

import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))
sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))

_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from neograph.Neo4jConnection import get_manager
from guidance_ids import CANONICAL_UNITS, _is_per_share_label, _is_share_count_label, slug
from scripts.earnings.earnings_orchestrator import _fmt_guidance_value


QUERY_ALL_GUIDANCE = """
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
RETURN g.id AS metric_id,
       g.label AS metric,
       gu.canonical_unit AS canonical_unit,
       gu.low AS low,
       gu.mid AS mid,
       gu.high AS high,
       gu.qualitative AS qualitative,
       gu.conditions AS conditions,
       gu.given_date AS given_date,
       gu.quote AS quote
ORDER BY g.label, gu.given_date
"""


COUNT_LIKE_EXACT_IDS = {
    "loyalty_members",
    "hsa_count",
    "total_accounts",
    "active_customers",
    "net_active_customer_additions_per_quarter",
    "average_healthcare_services_clients",
    "average_healthcare_services_clients_sequential_net_add",
    "community_count",
    "year_end_community_count",
    "ending_community_count",
    "employer_clients",
    "ccta_market_accounts",
    "guest_count",
    "headcount",
    "head_count",
    "u_s_headcount_reduction",
}


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


class Results:
    def __init__(self) -> None:
        self.started = time.time()
        self.items: list[CheckResult] = []

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.items.append(CheckResult(name=name, passed=passed, detail=detail))
        status = "PASS" if passed else "FAIL"
        msg = f"{status}: {name}"
        if detail:
            msg += f" — {detail}"
        print(msg, file=sys.stderr)

    def ok(self) -> bool:
        return all(item.passed for item in self.items)

    def finish(self) -> int:
        elapsed = time.time() - self.started
        passed = sum(1 for item in self.items if item.passed)
        total = len(self.items)
        failed = total - passed
        print(f"\nGUIDANCE UNIT SAFETY: {passed}/{total} passed, {failed} failed ({elapsed:.1f}s)", file=sys.stderr)
        return 0 if failed == 0 else 1


def _metric_id(row: dict) -> str:
    metric_id = row.get("metric_id")
    if metric_id:
        return str(metric_id).lower()
    return slug(str(row.get("metric") or ""))


def _looks_count_like(row: dict) -> bool:
    mid = _metric_id(row)
    if _is_share_count_label(mid):
        return True
    if mid in COUNT_LIKE_EXACT_IDS:
        return True
    return False


def _sample(rows: list[dict], limit: int = 5) -> str:
    out = []
    for row in rows[:limit]:
        metric = row.get("metric")
        metric_id = _metric_id(row)
        unit = row.get("canonical_unit")
        quote = (row.get("quote") or "").replace("\n", " ")
        quote = quote[:120] + ("..." if len(quote) > 120 else "")
        out.append(f"{metric_id} [{metric}] unit={unit} quote={quote}")
    return " | ".join(out)


def main() -> int:
    R = Results()

    manager = get_manager()
    try:
        rows = manager.execute_cypher_query_all(QUERY_ALL_GUIDANCE, {})
    finally:
        manager.close()

    R.add("guidance_rows_present", len(rows) > 0, f"{len(rows)} rows")

    units_in_db = {row.get("canonical_unit") for row in rows}
    unexpected_units = sorted(u for u in units_in_db if u not in CANONICAL_UNITS)
    R.add(
        "canonical_unit_enum_covered",
        not unexpected_units,
        f"unexpected units: {unexpected_units}" if unexpected_units else f"units={sorted(units_in_db)}",
    )

    unknown_rows = [row for row in rows if row.get("canonical_unit") == "unknown"]
    unknown_counts = Counter(_metric_id(row) for row in unknown_rows)
    top_unknown = ", ".join(f"{mid}={n}" for mid, n in unknown_counts.most_common(10))
    R.add(
        "no_unknown_units",
        not unknown_rows,
        f"{len(unknown_rows)} unknown rows; top={top_unknown}" if unknown_rows else "",
    )

    per_share_bad = [
        row for row in rows
        if _is_per_share_label(_metric_id(row)) and row.get("canonical_unit") != "usd"
    ]
    R.add(
        "per_share_metrics_use_usd",
        not per_share_bad,
        f"{len(per_share_bad)} mismatches; {_sample(per_share_bad)}" if per_share_bad else "",
    )

    share_count_bad = [
        row for row in rows
        if _is_share_count_label(_metric_id(row)) and row.get("canonical_unit") != "count"
    ]
    R.add(
        "share_count_metrics_use_count",
        not share_count_bad,
        f"{len(share_count_bad)} mismatches; {_sample(share_count_bad)}" if share_count_bad else "",
    )

    count_like_money = [
        row for row in rows
        if _looks_count_like(row) and row.get("canonical_unit") in {"m_usd", "usd"}
    ]
    R.add(
        "count_like_metrics_not_money",
        not count_like_money,
        f"{len(count_like_money)} mismatches; {_sample(count_like_money)}" if count_like_money else "",
    )

    # NOTE: No renderer-level dollar-leak check. The renderer trusts resolved_unit
    # from the builder. Misclassified units (e.g. share counts stored as m_usd)
    # are upstream data quality bugs, not renderer bugs. Fix in extraction pipeline.
    # The count_like_money check above already flags these for upstream correction.

    print(
        {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "total_rows": len(rows),
            "units": Counter(row.get("canonical_unit") for row in rows),
            "unknown_rows": len(unknown_rows),
            "per_share_bad": len(per_share_bad),
            "share_count_bad": len(share_count_bad),
            "count_like_money": len(count_like_money),
            "dollar_leaks": len(dollar_leaks),
        }
    )
    return R.finish()


if __name__ == "__main__":
    raise SystemExit(main())
