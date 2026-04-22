"""XBRL Exact Splits — revenue segment extractor (D1 sidecar).

Produces per-period segment/geography/product_service splits for a ticker,
using the Wave 2 precision-first revenue qname maps.

Contract (D1 scope):
  - Revenue extraction only. Operating is deferred to D2.
  - Primary rows are direct 1D or §8-collapsed-to-1D exact reconciled views.
  - Cross-dimensional residuals go to an audit sibling file, never primary.
  - Identity = (metric_qname, view_kind, normalized_member_signature).
  - Q4 derivation is guarded on identity + basis + unit match; else null.
  - basis_type / is_derived_q4 / derivation_method / null_reason are orthogonal.
  - Sidecar posture: imports from build_prior_financials.py but nothing in the
    existing production pipeline imports this module.

Invocation:
  venv/bin/python scripts/earnings/xbrl_exact_splits.py \\
      --ticker LSTR \\
      [--period 2025-12-31] \\
      [--pit-cutoff 2025-06-30T00:00:00-04:00] \\
      [--maps-dir data/xbrl_maps] \\
      [--out-dir /tmp] \\
      [--history-quarters 8]

Output:
  {out_dir}/segment_splits_{TICKER}.json        (primary, reconciled rows only)
  {out_dir}/segment_splits_{TICKER}_audit.json  (diagnostics, cross_dim residuals)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from neograph.Neo4jConnection import get_manager
from q4_derivation import (
    NULL_REASONS,
    normalize_uid,
    qname_from_uid,
    row_signature,
    derive_q4_view,
    classify_period,
    is_target_period,
)

# --------------------------------------------------------------------------- #
# Constants                                                                    #
# --------------------------------------------------------------------------- #

SCHEMA_VERSION = "segment_splits.v1"

DEFAULT_MAPS_DIR = PROJECT_ROOT / "data/xbrl_maps"
DEFAULT_OUT_DIR = Path("/tmp")
DEFAULT_HISTORY_QUARTERS = 8
CURRENT_PERIOD_TOLERANCE_DAYS = 7
QUERY_TIMEOUT_SEC = 120

# Axis qnames (normalized, prefix:localname form)
BUSINESS_SEGMENT_AXIS = "us-gaap:StatementBusinessSegmentsAxis"
GEOGRAPHY_AXES = {"srt:StatementGeographicalAxis", "us-gaap:StatementGeographicalAxis"}
PRODUCT_AXES = {"srt:ProductOrServiceAxis", "us-gaap:ProductOrServiceAxis"}
ADJUSTMENT_AXES = {
    "srt:ConsolidationItemsAxis",
    "us-gaap:SubsegmentsConsolidationItemsAxis",
}

# Canonical "primary" members on adjustment axes — only these may be collapsed
# into a core view by §8. Non-primary members (Corporate, Eliminations,
# ReconcilingItems, etc.) remain as aggregate_basis adjustment candidates so
# they don't pollute the primary split with duplicate coordinates.
PRIMARY_CONSOLIDATION_MEMBERS = {
    "us-gaap:OperatingSegmentsMember",
}

VIEW_TOTAL = "total"
VIEW_SEGMENT = "business_segment"
VIEW_GEOGRAPHY = "geography"
VIEW_PRODUCT_SERVICE = "product_service"
VIEW_CROSS_DIM = "cross_dim"

PRIMARY_VIEW_KINDS = (VIEW_TOTAL, VIEW_SEGMENT, VIEW_GEOGRAPHY, VIEW_PRODUCT_SERVICE)

# Fallback-discovery candidate order (priority highest → lowest). Used ONLY
# when a ticker is not present in the curated Wave-2 map AND the caller
# explicitly opts in via allow_discovery_fallback=True. Matches the Wave-2
# REVENUE_CANDIDATES order so a future Wave-N ingestion would rank
# identically. Fallback output is always tagged qname_source="fallback_discovery"
# so downstream consumers can gate trust.
STANDARD_REVENUE_CANDIDATES = [
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
    "us-gaap:Revenues",
    "us-gaap:SalesRevenueNet",
    "us-gaap:NetSales",
]
STANDARD_OPERATING_CANDIDATES = [
    "us-gaap:OperatingIncomeLoss",
]

# Packet-level tags for qname provenance.
QNAME_SOURCE_MAPPED = "mapped"
QNAME_SOURCE_FALLBACK = "fallback_discovery"


# --------------------------------------------------------------------------- #
# Map loader                                                                   #
# --------------------------------------------------------------------------- #

_MAP_CACHE: dict[str, dict[str, dict]] = {}


def load_map(maps_dir: Path, kind: str) -> dict[str, dict]:
    """Load revenue_map_783.jsonl or operating_map_783.jsonl.

    Returns: {ticker: map_entry}
    Memoized per-process.
    """
    cache_key = f"{maps_dir}:{kind}"
    if cache_key in _MAP_CACHE:
        return _MAP_CACHE[cache_key]

    path = Path(maps_dir) / f"{kind}_map_783.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Map file not found: {path}. Copy from "
            f".claude/plans/xbrl_subagent_chunks/merged/ (see data/xbrl_maps/MAPS_README.md)."
        )
    out: dict[str, dict] = {}
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            out[entry["ticker"]] = entry
    _MAP_CACHE[cache_key] = out
    return out


# --------------------------------------------------------------------------- #
# Neo4j queries                                                                #
# --------------------------------------------------------------------------- #

_ALL_PERIODS_QUERY = """
MATCH (r:Report)-[:PRIMARY_FILER]->(:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q','10-K','10-Q/A','10-K/A']
  AND r.xbrl_status = 'COMPLETED'
  AND ($snapshot_ts IS NULL OR r.created <= $snapshot_ts)
RETURN DISTINCT r.periodOfReport AS period
ORDER BY period DESC
LIMIT $limit
"""

_FACTS_QUERY = """
MATCH (r:Report)-[:PRIMARY_FILER]->(:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q','10-K','10-Q/A','10-K/A']
  AND r.xbrl_status = 'COMPLETED'
  AND ($snapshot_ts IS NULL OR r.created <= $snapshot_ts)
  AND r.periodOfReport IN $target_periods
MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:HAS_PERIOD]->(p:Period)
WHERE con.qname = $metric_qname
  AND f.is_numeric = '1'
  AND p.end_date IS NOT NULL AND p.end_date <> 'null'
OPTIONAL MATCH (f)-[:FACT_MEMBER]->(m:Member)
WITH r, con, f, ctx, p,
     collect({qname: m.qname, label: m.label, uid: m.u_id}) AS rel_members
RETURN r.accessionNo AS accession,
       r.formType    AS form_type,
       r.periodOfReport AS period_of_report,
       r.created     AS filed_ts,
       con.qname     AS concept,
       f.value       AS value,
       f.decimals    AS decimals,
       f.unit_ref    AS unit_ref,
       ctx.u_id      AS context_u_id,
       ctx.dimension_u_ids AS dim_uids,
       ctx.member_u_ids    AS member_uids,
       p.start_date  AS period_start,
       p.end_date    AS period_end,
       rel_members   AS rel_members
"""


# --------------------------------------------------------------------------- #
# Fact normalization                                                           #
# --------------------------------------------------------------------------- #

def _parse_value(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    # Strings may carry comma-separated formatting like "4,819,245,000"
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_decimals(v: Any) -> Optional[int]:
    if v is None or v == "INF":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def classify_duration(start_date: Optional[str], end_date: Optional[str]) -> str:
    """Same classification logic as chunk workers and build_prior_financials."""
    if not end_date or end_date == "null":
        return "instant"
    if not start_date or start_date == "null":
        return "instant"
    if start_date == end_date:
        return "instant"
    try:
        days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days
    except Exception:
        return "other"
    if 60 <= days <= 120:
        return "quarterly"
    if 150 <= days <= 210:
        return "semi_annual"
    if 240 <= days <= 310:
        return "nine_month"
    if 340 <= days <= 400:
        return "annual"
    return "other"


def _axis_qnames(dim_uids: list[str]) -> list[str]:
    """Extract normalized axis qnames from a context's dimension_u_ids."""
    out = []
    for uid in dim_uids or []:
        qn = qname_from_uid(uid)
        if qn:
            out.append(qn)
    return out


def _member_qnames_positional(member_uids: list[str]) -> list[str]:
    """Return normalized member qnames in Context.member_u_ids order.

    IMPORTANT: Context.member_u_ids is positionally paired with
    Context.dimension_u_ids. We MUST use this array as the positional
    backbone for any axis-member pairing (notably §8 collapse). FACT_MEMBER
    `collect()` ordering is indeterminate and must NOT be used as the
    backbone — live CHRW data shows 8/10 multi-axis rows disagree with
    Context order.
    """
    out: list[str] = []
    for uid in member_uids or []:
        qn = qname_from_uid(uid)
        if qn:
            out.append(qn)
    return out


def _classify_view_kind(axis_qnames: list[str]) -> str:
    """Map axis set → view_kind."""
    if not axis_qnames:
        return VIEW_TOTAL
    axis_set = set(axis_qnames)
    # Strip adjustment axes for view classification; they're for §8 collapse.
    core = axis_set - ADJUSTMENT_AXES
    if not core:
        # Only adjustment axes present → still treat as total-ish (rare)
        return VIEW_TOTAL
    if len(core) == 1:
        only = next(iter(core))
        if only == BUSINESS_SEGMENT_AXIS:
            return VIEW_SEGMENT
        if only in GEOGRAPHY_AXES:
            return VIEW_GEOGRAPHY
        if only in PRODUCT_AXES:
            return VIEW_PRODUCT_SERVICE
        # Single non-standard axis → cross_dim (unclassified primary)
        return VIEW_CROSS_DIM
    return VIEW_CROSS_DIM


def _member_label_map(rel_members: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in rel_members or []:
        qn = m.get("qname")
        lbl = m.get("label")
        if qn and lbl:
            out[qn] = lbl
    return out


def _fetch_facts(
    manager,
    ticker: str,
    metric_qname: str,
    target_periods: list[str],
    snapshot_ts: Optional[str],
) -> list[dict]:
    """Retrieve all facts for metric_qname across target_periods. PIT-gated."""
    params = {
        "ticker": ticker,
        "metric_qname": metric_qname,
        "target_periods": target_periods,
        "snapshot_ts": snapshot_ts,
    }
    result = manager.execute_cypher_query_all(_FACTS_QUERY, params)
    return list(result or [])


def _normalize_fact_row(row: dict) -> Optional[dict]:
    """Project a raw Neo4j row into the normalized shape used downstream.

    Applies:
      - normalize_uid on all member/dim uids
      - length-mismatch guard (context dim/member uid cardinality must match)
      - period-end ±7d filter vs periodOfReport (drops prior-year comparatives)
    """
    member_uids = list(row.get("member_uids") or [])
    dim_uids = list(row.get("dim_uids") or [])

    # Length-mismatch guard
    if len(member_uids) != len(dim_uids):
        return {"__skip__": True, "reason": "length_mismatch", "context_u_id": row.get("context_u_id")}

    # Normalize u_ids
    norm_members = [normalize_uid(u) for u in member_uids]
    norm_dims = [normalize_uid(u) for u in dim_uids]

    period_of_report = row.get("period_of_report")
    period_end = row.get("period_end")
    # Period ±7d filter
    try:
        if period_end and period_of_report:
            if not is_target_period(period_end, period_of_report):
                return {"__skip__": True, "reason": "period_window", "period_end": period_end}
    except Exception:
        pass

    value = _parse_value(row.get("value"))
    if value is None:
        return {"__skip__": True, "reason": "non_numeric"}

    dim_qnames = _axis_qnames(norm_dims)
    # Positional backbone: use ctx.member_u_ids order, NOT FACT_MEMBER collect order.
    member_qnames = _member_qnames_positional(norm_members)
    # FACT_MEMBER rel_members is used ONLY as a qname → label lookup (order-independent).
    member_labels = _member_label_map(row.get("rel_members") or [])
    view_kind = _classify_view_kind(dim_qnames)

    duration = classify_duration(row.get("period_start"), period_end)

    concept_qname = row.get("concept")
    return {
        "accession": row.get("accession"),
        "form_type": row.get("form_type"),
        "period_of_report": period_of_report,
        "filed_ts": row.get("filed_ts"),
        "concept": concept_qname,
        "value": value,
        "decimals": _parse_decimals(row.get("decimals")),
        "unit": row.get("unit_ref") or "",
        "context_u_id": row.get("context_u_id"),
        "dim_qnames": dim_qnames,
        "member_qnames": member_qnames,
        "member_labels": member_labels,
        "view_kind": view_kind,
        "period_start": row.get("period_start"),
        "period_end": period_end,
        "duration": duration,
        # Stable normalized identity signature = canonical row_signature() form
        "member_signature": frozenset(member_qnames),
        "row_signature": row_signature(concept_qname, view_kind, norm_members),
    }


def _dedupe_rows(rows: list[dict]) -> list[dict]:
    """6-element dedupe key. Amendment overlay: keep newest filed_ts per key."""
    seen: dict[tuple, dict] = {}
    for r in rows:
        key = (
            r["period_of_report"],
            r["duration"],
            r["period_start"],
            r["period_end"],
            tuple(sorted(r["member_qnames"])),
            tuple(sorted(r["dim_qnames"])),
        )
        prev = seen.get(key)
        if prev is None or (r.get("filed_ts") or "") > (prev.get("filed_ts") or ""):
            seen[key] = r
    return list(seen.values())


# --------------------------------------------------------------------------- #
# Reconciliation (subset-sum)                                                  #
# --------------------------------------------------------------------------- #

def _rounding_tolerance(decimals_list: list[Optional[int]], scale_hint: float = 1.0) -> float:
    valid = [d for d in decimals_list if d is not None]
    if not valid:
        return max(1.0, abs(scale_hint) * 0.001)
    min_dec = min(valid)
    return 10 ** (-min_dec)


def _subset_sum_reconciles(values: list[float], target: float, tol: float, max_items: int = 16) -> Optional[list[int]]:
    n = len(values)
    if n == 0:
        return None
    full = sum(values)
    if abs(full - target) <= tol:
        return list(range(n))
    if n > max_items:
        return None
    for size in range(1, min(n, max_items) + 1):
        if size == n:
            continue
        for combo in combinations(range(n), size):
            if abs(sum(values[i] for i in combo) - target) <= tol:
                return list(combo)
    return None


def _aggregate_basis_reconciles(
    primary_vals: list[float], adj_vals: list[float], target: float, tol: float, max_items: int = 12
) -> Optional[tuple[list[int], list[int]]]:
    """sum(primary_subset) + sum(adj_subset) == target within tol."""
    n_p = len(primary_vals)
    n_a = len(adj_vals)
    if n_p == 0:
        return None
    # Prefer full primary + full adj
    if abs(sum(primary_vals) + sum(adj_vals) - target) <= tol:
        return list(range(n_p)), list(range(n_a))
    if abs(sum(primary_vals) - target) <= tol:
        return list(range(n_p)), []
    if n_p > max_items or n_a > max_items:
        return None
    for ps in range(1, n_p + 1):
        for pcombo in combinations(range(n_p), ps):
            psum = sum(primary_vals[i] for i in pcombo)
            if abs(psum - target) <= tol:
                return list(pcombo), []
            for asize in range(1, n_a + 1):
                for acombo in combinations(range(n_a), asize):
                    if abs(psum + sum(adj_vals[i] for i in acombo) - target) <= tol:
                        return list(pcombo), list(acombo)
    return None


# --------------------------------------------------------------------------- #
# §8 cross-dim collapse                                                        #
# --------------------------------------------------------------------------- #

def _try_collapse_cross_dim(row: dict) -> list[dict]:
    """If row's dim set contains an adjustment axis + exactly one core axis,
    produce a collapsed row on the core axis alone.

    Only collapses when EVERY adjustment-axis coordinate is a canonical
    primary member (PRIMARY_CONSOLIDATION_MEMBERS). Non-primary coordinates
    (Corporate, Eliminations, ReconcilingItems) remain as cross_dim so they
    don't pollute the primary split. This prevents e.g. a
    `CorporateNonSegment + US` row from collapsing into the US geography
    line and creating a duplicate US row.
    """
    core = [d for d in row["dim_qnames"] if d not in ADJUSTMENT_AXES]
    adj = [d for d in row["dim_qnames"] if d in ADJUSTMENT_AXES]
    if not adj or len(core) != 1:
        return []

    # Gate on adjustment-axis member identity (positional via ctx.member_u_ids).
    adj_members = [
        mq for axis_q, mq in zip(row["dim_qnames"], row["member_qnames"])
        if axis_q in ADJUSTMENT_AXES
    ]
    if any(m not in PRIMARY_CONSOLIDATION_MEMBERS for m in adj_members):
        return []  # Non-primary adjustment member → stay cross_dim (audit only).

    # Drop the adjustment axis coordinate from members by positional alignment.
    # (Context.dimension_u_ids and member_u_ids are ordered pair-wise.)
    new_members_q: list[str] = []
    new_labels: dict[str, str] = {}
    for axis_q, member_q in zip(row["dim_qnames"], row["member_qnames"]):
        if axis_q not in ADJUSTMENT_AXES:
            new_members_q.append(member_q)
            if member_q in row["member_labels"]:
                new_labels[member_q] = row["member_labels"][member_q]

    collapsed = dict(row)
    collapsed["dim_qnames"] = core
    collapsed["member_qnames"] = new_members_q
    collapsed["member_labels"] = new_labels
    collapsed["view_kind"] = _classify_view_kind(core)
    collapsed["member_signature"] = frozenset(new_members_q)
    collapsed["__collapsed_from_cross_dim__"] = True
    return [collapsed]


# --------------------------------------------------------------------------- #
# View reconciliation per (period, duration, view_kind)                        #
# --------------------------------------------------------------------------- #

def _reconcile_group(
    memberless_total_row: Optional[dict],
    group_rows: list[dict],
    adjustment_only_rows: list[dict],
) -> Optional[dict]:
    """Given a group of rows sharing (period, duration, view_kind), attempt
    to reconcile against the memberless_total.
    Returns a dict describing the reconciled primary view, or None if it fails.
    """
    if not group_rows:
        return None
    if memberless_total_row is None:
        # No memberless total means we can't verify reconciliation.
        return None

    target = memberless_total_row["value"]
    decimals_pool = [r.get("decimals") for r in group_rows] + [memberless_total_row.get("decimals")]
    tol = _rounding_tolerance(decimals_pool, scale_hint=target)

    # Try memberless_total (primary rows only)
    primary_vals = [r["value"] for r in group_rows]
    subset = _subset_sum_reconciles(primary_vals, target, tol)
    if subset is not None:
        chosen = [group_rows[i] for i in subset]
        return {
            "basis_type": "memberless_total",
            "rows": chosen,
            "memberless_total_value": target,
            "memberless_total_row": memberless_total_row,
        }

    # Try aggregate_basis (primary + adjustment)
    if adjustment_only_rows:
        adj_vals = [r["value"] for r in adjustment_only_rows]
        match = _aggregate_basis_reconciles(primary_vals, adj_vals, target, tol)
        if match is not None:
            p_idx, a_idx = match
            return {
                "basis_type": "aggregate_basis",
                "rows": [group_rows[i] for i in p_idx],
                "adjustment_rows": [adjustment_only_rows[i] for i in a_idx],
                "memberless_total_value": target,
                "memberless_total_row": memberless_total_row,
            }
    return None


def _build_primary_views(
    normalized_rows: list[dict],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Build reconciled primary views keyed by (period_of_report, duration).

    Returns:
        {(period, duration): {
            "memberless_total": row or None,
            "views": {view_kind: reconciled_view_dict},
            "cross_dim_residual_rows": [...],
            "collapsed_attempted_rows": [...]
        }}
    """
    out: dict[tuple[str, str], dict[str, Any]] = {}

    # Group by (period, duration)
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in normalized_rows:
        grouped[(r["period_of_report"], r["duration"])].append(r)

    for key, rows in grouped.items():
        # Identify memberless_total
        memberless = next((r for r in rows if not r["dim_qnames"]), None)

        # Classify rows
        by_view: dict[str, list[dict]] = defaultdict(list)
        adj_only: list[dict] = []
        cross_dim_rows: list[dict] = []
        collapsed_rows: list[dict] = []

        for r in rows:
            if not r["dim_qnames"]:
                continue  # memberless total
            # Rows whose *only* axes are adjustment axes → adjustment-only pool
            if all(d in ADJUSTMENT_AXES for d in r["dim_qnames"]):
                adj_only.append(r)
                continue

            # If adjustment axis is present OR row is cross_dim, route through
            # §8 collapse before classification. Rows like
            # (ConsolidationItemsAxis + BusinessSegmentsAxis) classify as
            # VIEW_SEGMENT by core-axis stripping but still carry TWO members
            # — we must drop the adjustment-axis coordinate so only the core
            # business-segment member is emitted.
            has_adjustment = any(d in ADJUSTMENT_AXES for d in r["dim_qnames"])
            if has_adjustment or r["view_kind"] == VIEW_CROSS_DIM:
                collapsed = _try_collapse_cross_dim(r)
                if collapsed:
                    for cr in collapsed:
                        cvk = cr["view_kind"]
                        if cvk in (VIEW_SEGMENT, VIEW_GEOGRAPHY, VIEW_PRODUCT_SERVICE):
                            by_view[cvk].append(cr)
                            collapsed_rows.append(cr)
                        else:
                            cross_dim_rows.append(r)  # residual
                else:
                    cross_dim_rows.append(r)
                continue

            by_view[r["view_kind"]].append(r)

        reconciled_views: dict[str, Any] = {}
        for vk, vrows in by_view.items():
            reconciled = _reconcile_group(memberless, vrows, adj_only)
            if reconciled is not None:
                reconciled["view_kind"] = vk
                reconciled_views[vk] = reconciled

        # Even the "total" view gets an explicit entry when memberless exists
        if memberless is not None:
            reconciled_views[VIEW_TOTAL] = {
                "basis_type": "memberless_total",
                "rows": [memberless],
                "memberless_total_value": memberless["value"],
                "memberless_total_row": memberless,
                "view_kind": VIEW_TOTAL,
            }

        out[key] = {
            "memberless_total": memberless,
            "views": reconciled_views,
            "cross_dim_residual_rows": cross_dim_rows,
            "collapsed_attempted_rows": collapsed_rows,
        }
    return out


# --------------------------------------------------------------------------- #
# Per-period emission                                                          #
# --------------------------------------------------------------------------- #

def _emit_view_rows(reconciled_view: dict, view_kind: str) -> list[dict]:
    """Turn a reconciled view (with rows[] + basis_type) into flat row dicts."""
    basis = reconciled_view["basis_type"]
    out: list[dict] = []
    for r in reconciled_view.get("rows", []):
        # For the TOTAL view, rows==[memberless]; emit value only
        member_qnames = r.get("member_qnames", [])
        label_map = r.get("member_labels", {})
        if view_kind == VIEW_TOTAL or not member_qnames:
            out.append({
                "view_kind": VIEW_TOTAL,
                "member": None,
                "label": None,
                "value": r["value"],
                "unit": r.get("unit", ""),
                "decimals": r.get("decimals"),
                "basis_type": basis,
                "null_reason": None,
                "metric_qname": r.get("concept"),
                "period_of_report": r.get("period_of_report"),
                "period_start": r.get("period_start"),
                "period_end": r.get("period_end"),
                "accession": r.get("accession"),
                "form_type": r.get("form_type"),
            })
        else:
            for mq in member_qnames:
                out.append({
                    "view_kind": view_kind,
                    "member": mq,
                    "label": label_map.get(mq),
                    "value": r["value"],
                    "unit": r.get("unit", ""),
                    "decimals": r.get("decimals"),
                    "basis_type": basis,
                    "null_reason": None,
                    "metric_qname": r.get("concept"),
                    "period_of_report": r.get("period_of_report"),
                    "period_start": r.get("period_start"),
                    "period_end": r.get("period_end"),
                    "accession": r.get("accession"),
                    "form_type": r.get("form_type"),
                })
    return out


def _fiscal_label_stub(duration: str) -> dict:
    """D1 minimal fiscal label (placeholder until fiscal_math integration).

    We don't block D1 on fiscal labeling. The extractor emits the raw
    period_of_report + duration; downstream promotion hooks can resolve
    fiscal year/period from the existing _get_fiscal_labels path.
    """
    return {"duration": duration}


def _build_period_block(
    metric: str,
    metric_qname: str,
    period_of_report: str,
    duration: str,
    primary: dict,
    map_entry: dict,
) -> dict:
    """Assemble a single period-metric block for the primary output.

    primary is the dict from _build_primary_views()[(period, duration)].
    """
    views_out: dict[str, Any] = {}
    null_reasons: dict[str, str] = {}

    capability = {
        "segments": bool(map_entry.get("works_for_segments")),
        "geography": bool(map_entry.get("works_for_geography")),
        "product_service": bool(map_entry.get("works_for_product_service")),
    }

    reconciled = primary.get("views", {})
    if VIEW_TOTAL in reconciled:
        rows = _emit_view_rows(reconciled[VIEW_TOTAL], VIEW_TOTAL)
        views_out[VIEW_TOTAL] = rows[0] if rows else None
    else:
        views_out[VIEW_TOTAL] = None
        null_reasons[VIEW_TOTAL] = "no_memberless_total"

    for vk, cap_key in (
        (VIEW_SEGMENT, "segments"),
        (VIEW_GEOGRAPHY, "geography"),
        (VIEW_PRODUCT_SERVICE, "product_service"),
    ):
        if not capability[cap_key]:
            # Map says this view isn't validated — omit (not null).
            continue
        if vk in reconciled:
            views_out[vk] = _emit_view_rows(reconciled[vk], vk)
        else:
            views_out[vk] = []
            null_reasons[vk] = "view_not_reconciled_this_period"

    # Block provenance: anchor accession/form from the memberless_total row
    anchor = primary.get("memberless_total")
    anchor_accession = anchor["accession"] if anchor else None
    anchor_form = anchor["form_type"] if anchor else None
    anchor_ps = anchor["period_start"] if anchor else None
    anchor_pe = anchor["period_end"] if anchor else None

    return {
        "metric": metric,
        "metric_qname": metric_qname,
        "period_of_report": period_of_report,
        "period_start": anchor_ps,
        "period_end": anchor_pe,
        "duration": duration,
        "fiscal_label": _fiscal_label_stub(duration),
        "accession": anchor_accession,
        "form_type": anchor_form,
        "is_derived_q4": False,
        "derivation_method": None,
        "sources": [],
        "views": views_out,
        "null_reasons": null_reasons,
    }


# --------------------------------------------------------------------------- #
# Q4 derivation                                                                #
# --------------------------------------------------------------------------- #

def _locate_q3_ytd_block(
    all_blocks: list[dict],
    fy_period_of_report: str,
) -> Optional[dict]:
    """Find the 9M YTD block that precedes the FY period.

    9M YTD is a fact with duration='nine_month' found in the Q3 10-Q. Its
    period_of_report is the Q3 end date (e.g. 2025-09-30 for FY=2025-12-31).
    """
    fy_end = date.fromisoformat(fy_period_of_report)
    best: Optional[dict] = None
    for b in all_blocks:
        if b["duration"] != "nine_month":
            continue
        try:
            pe = date.fromisoformat(b["period_of_report"])
        except Exception:
            continue
        delta = (fy_end - pe).days
        if 60 <= delta <= 120:  # quarter gap
            if best is None or pe > date.fromisoformat(best["period_of_report"]):
                best = b
    return best


def _locate_quarterly_blocks(
    all_blocks: list[dict],
    fy_block: dict,
) -> Optional[list[dict]]:
    """Return [Q1, Q2, Q3] quarterly blocks for the fiscal year of fy_block.

    Criteria:
      - duration == 'quarterly'
      - not derived
      - period_of_report falls strictly within (fy_period_start, fy_period_of_report]
    Returns chronologically sorted list if exactly 3 found; None otherwise.
    """
    try:
        fy_start = date.fromisoformat(fy_block["period_start"])
        fy_end = date.fromisoformat(fy_block["period_of_report"])
    except Exception:
        return None
    qs: list[dict] = []
    for b in all_blocks:
        if b.get("duration") != "quarterly" or b.get("is_derived_q4"):
            continue
        try:
            pe = date.fromisoformat(b["period_of_report"])
        except Exception:
            continue
        if fy_start < pe <= fy_end:
            qs.append(b)
    if len(qs) != 3:
        return None
    qs.sort(key=lambda b: b["period_of_report"])
    return qs


def _signature_of_emitted_row(row: dict, fy_block_metric_qname: str) -> tuple:
    """Build the canonical (metric_qname, view_kind, frozenset(members)) tuple
    from an emitted primary row. Used as identity key for Q4 derivation matching.
    """
    mq = row.get("metric_qname") or fy_block_metric_qname
    vk = row.get("view_kind", VIEW_TOTAL)
    member = row.get("member")
    members = frozenset([member]) if member else frozenset()
    return (mq, vk, members)


def _lookup_by_signature(rows: list[dict], target_sig: tuple, metric_qname: str) -> Optional[dict]:
    for r in rows:
        if _signature_of_emitted_row(r, metric_qname) == target_sig:
            return r
    return None


def _derive_q4_for_period(
    fy_block: dict,
    ytd_9m_block: Optional[dict],
    quarterly_blocks: Optional[list[dict]],
    map_entry: dict,
) -> dict:
    """Produce a derived-Q4 block from an FY block, 9M YTD (primary), and
    Q1/Q2/Q3 quarterly blocks (fallback when 9M is missing).

    Derivation runs per (metric_qname, view_kind, member_signature). Any view
    whose derivation fails emits a null row with an explicit null_reason.
    """
    annual_only = map_entry.get("validation_period_types") == ["annual"]
    metric_qname = fy_block["metric_qname"]

    derived_views: dict[str, Any] = {}
    derivation_methods: set[str] = set()
    null_reasons: dict[str, str] = {}

    # TOTAL view
    fy_total = fy_block["views"].get(VIEW_TOTAL)
    ytd_total = (ytd_9m_block["views"].get(VIEW_TOTAL) if ytd_9m_block else None)
    total_sig = (metric_qname, VIEW_TOTAL, frozenset())
    q_totals = None
    if quarterly_blocks is not None:
        q_totals = []
        for qb in quarterly_blocks:
            qt = qb["views"].get(VIEW_TOTAL)
            if qt is None:
                q_totals = None
                break
            q_totals.append(qt)

    total_val, total_tag = derive_q4_view(
        _row_to_derivation_input(fy_total) if fy_total else None,
        _row_to_derivation_input(ytd_total) if ytd_total else None,
        [_row_to_derivation_input(qt) for qt in q_totals] if q_totals else None,
        annual_only_map_flag=annual_only,
    )
    if total_val is not None:
        derived_views[VIEW_TOTAL] = {
            "view_kind": VIEW_TOTAL,
            "member": None,
            "label": None,
            "value": total_val,
            "unit": (fy_total or {}).get("unit", ""),
            "decimals": (fy_total or {}).get("decimals"),
            "basis_type": (fy_total or {}).get("basis_type"),
            "null_reason": None,
            "metric_qname": metric_qname,
            "period_of_report": fy_block["period_of_report"],
            "period_start": fy_block["period_start"],
            "period_end": fy_block["period_end"],
            "accession": fy_block["accession"],
            "form_type": "derived",
        }
        derivation_methods.add(total_tag)
    else:
        derived_views[VIEW_TOTAL] = None
        null_reasons[VIEW_TOTAL] = total_tag

    # Per-view-kind per-signature derivation
    for vk in (VIEW_SEGMENT, VIEW_GEOGRAPHY, VIEW_PRODUCT_SERVICE):
        fy_rows = fy_block["views"].get(vk) or []
        if not fy_rows:
            continue
        ytd_rows = (ytd_9m_block["views"].get(vk) if ytd_9m_block else None) or []
        q_rows_per_quarter: Optional[list[list[dict]]] = None
        if quarterly_blocks is not None:
            q_rows_per_quarter = [qb["views"].get(vk) or [] for qb in quarterly_blocks]

        emitted: list[dict] = []
        per_view_nulls: dict[str, str] = {}
        for fyr in fy_rows:
            fy_sig = _signature_of_emitted_row(fyr, metric_qname)
            ytd = _lookup_by_signature(ytd_rows, fy_sig, metric_qname)

            # Build quarterly_rows list only if every quarter has a match
            q_matches: Optional[list[dict]] = None
            if q_rows_per_quarter is not None:
                candidates = [
                    _lookup_by_signature(qrs, fy_sig, metric_qname)
                    for qrs in q_rows_per_quarter
                ]
                if all(c is not None for c in candidates):
                    q_matches = candidates  # type: ignore[assignment]

            val, tag = derive_q4_view(
                _row_to_derivation_input(fyr),
                _row_to_derivation_input(ytd) if ytd else None,
                [_row_to_derivation_input(qm) for qm in q_matches] if q_matches else None,
                annual_only_map_flag=annual_only,
            )
            if val is not None:
                emitted.append({
                    **fyr,
                    "value": val,
                    "form_type": "derived",
                    "null_reason": None,
                })
                derivation_methods.add(tag)
            else:
                per_view_nulls[fyr.get("member") or "(no_member)"] = tag
        if emitted:
            derived_views[vk] = emitted
        if per_view_nulls:
            null_reasons[vk] = json.dumps(per_view_nulls, sort_keys=True)

    method = None
    if len(derivation_methods) == 1:
        method = next(iter(derivation_methods))
    elif len(derivation_methods) > 1:
        method = "mixed"

    sources: list[dict] = []
    if fy_block.get("accession"):
        sources.append({"accession": fy_block["accession"], "form_type": fy_block.get("form_type"), "role": "fy"})
    if ytd_9m_block and ytd_9m_block.get("accession"):
        sources.append({"accession": ytd_9m_block["accession"], "form_type": ytd_9m_block.get("form_type"), "role": "9m_ytd"})
    if quarterly_blocks and method == "fy_minus_q1q2q3":
        for i, qb in enumerate(quarterly_blocks, start=1):
            if qb.get("accession"):
                sources.append({"accession": qb["accession"], "form_type": qb.get("form_type"), "role": f"q{i}"})

    return {
        "metric": fy_block["metric"],
        "metric_qname": metric_qname,
        "period_of_report": fy_block["period_of_report"],
        "period_start": fy_block["period_start"],
        "period_end": fy_block["period_end"],
        "duration": "derived_q4",
        "fiscal_label": {"duration": "derived_q4"},
        "accession": fy_block["accession"],
        "form_type": "derived",
        "is_derived_q4": True,
        "derivation_method": method,
        "sources": sources,
        "views": derived_views,
        "null_reasons": null_reasons,
    }


def _row_to_derivation_input(row: Optional[dict]) -> Optional[dict]:
    """Shape a primary-output row for q4_derivation.derive_q4_view().

    The member_signature here is a single-element frozenset because each
    emitted primary row represents exactly one (axis, member) pairing.
    """
    if row is None:
        return None
    return {
        "value": row.get("value"),
        "basis_type": row.get("basis_type"),
        "view_kind": row.get("view_kind"),
        "member_signature": frozenset([row["member"]]) if row.get("member") else frozenset(),
        "decimals": row.get("decimals"),
        "unit": row.get("unit", ""),
    }


# --------------------------------------------------------------------------- #
# Packet assembly                                                              #
# --------------------------------------------------------------------------- #

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_has_facts(
    manager,
    ticker: str,
    candidate_qname: str,
    snapshot_ts: Optional[str],
) -> bool:
    """Cheap probe: does this ticker have any numeric facts for candidate_qname?"""
    q = """
    MATCH (r:Report)-[:PRIMARY_FILER]->(:Company {ticker: $ticker})
    WHERE r.formType IN ['10-Q','10-K','10-Q/A','10-K/A']
      AND r.xbrl_status = 'COMPLETED'
      AND ($snapshot_ts IS NULL OR r.created <= $snapshot_ts)
    MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
    WHERE con.qname = $qname AND f.is_numeric = '1'
    RETURN count(f) AS n
    """
    result = manager.execute_cypher_query_all(
        q, {"ticker": ticker, "qname": candidate_qname, "snapshot_ts": snapshot_ts}
    ) or []
    if not result:
        return False
    return int(result[0].get("n", 0)) > 0


def _synthetic_map_entry(ticker: str, qname: str) -> dict:
    """Build a lower-trust map entry for a ticker discovered via fallback.

    No works_for_* capabilities are asserted here — the extractor will emit
    whichever views actually reconcile from live data. Downstream consumers
    should gate trust on qname_source="fallback_discovery".
    """
    return {
        "ticker": ticker,
        "qname": qname,
        "source_form_types": [],
        "last_validated_filing": None,
        "last_validated_period": None,
        # Capabilities intentionally set to True so the extractor will emit
        # every view that actually reconciles. The final view_capability in
        # the packet is computed post-extraction from real output.
        "works_for_segments": True,
        "works_for_geography": True,
        "works_for_product_service": True,
        "validation_period_types": [],
        "basis_type": None,
        "notes": ["fallback_discovery"],
    }


def _resolve_metric_identity(
    ticker: str,
    metric: str,
    maps_dir: Path,
    pit_cutoff: Optional[str],
    allow_discovery_fallback: bool,
) -> tuple[Optional[str], Optional[dict], Optional[str], Optional[list[str]]]:
    """Resolve (metric_qname, map_entry, qname_source, tried_candidates).

    Cascade:
      1. Ticker in curated map WITH non-null qname → ("mapped", map_entry)
      2. Ticker in curated map WITH null qname → (None, map_entry, None)
         (coordinator-flagged; short-circuits to null packet later)
      3. Ticker NOT in map, fallback disabled → (None, None, None)
      4. Ticker NOT in map, fallback enabled → try STANDARD candidates in order;
         first candidate with facts wins, tag "fallback_discovery"
    """
    rev_map = load_map(maps_dir, metric)
    map_entry = rev_map.get(ticker)

    if map_entry is not None:
        qname = map_entry.get("qname")
        if qname is not None:
            return qname, map_entry, QNAME_SOURCE_MAPPED, None
        return None, map_entry, None, None  # Coordinator-flagged null

    if not allow_discovery_fallback:
        return None, None, None, None

    candidates = (
        STANDARD_REVENUE_CANDIDATES if metric == "revenue" else STANDARD_OPERATING_CANDIDATES
    )
    manager = get_manager()
    tried: list[str] = []
    for cand in candidates:
        tried.append(cand)
        if _candidate_has_facts(manager, ticker, cand, pit_cutoff):
            return cand, _synthetic_map_entry(ticker, cand), QNAME_SOURCE_FALLBACK, tried
    return None, None, None, tried


def extract_segment_splits(
    ticker: str,
    *,
    period: Optional[str] = None,
    pit_cutoff: Optional[str] = None,
    maps_dir: Path = DEFAULT_MAPS_DIR,
    out_dir: Path = DEFAULT_OUT_DIR,
    history_quarters: int = DEFAULT_HISTORY_QUARTERS,
    metric: str = "revenue",
    allow_discovery_fallback: bool = False,
    write_packets: bool = True,
) -> dict:
    """Run the extractor for a single ticker and write primary + audit packets.

    Returns the primary packet dict.

    Set allow_discovery_fallback=True to enable a lower-trust path for
    tickers outside the curated Wave-2 universe. Fallback packets are tagged
    qname_source="fallback_discovery" so consumers can gate trust.
    """
    t0 = time.time()
    ticker = ticker.upper()
    maps_dir = Path(maps_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mode = "historical" if pit_cutoff else "live"

    # 1. Resolve metric identity
    metric_qname, map_entry, qname_source, tried_candidates = _resolve_metric_identity(
        ticker, metric, maps_dir, pit_cutoff, allow_discovery_fallback
    )

    # 2a. Coordinator-flagged null (ticker in map but qname=None)
    if map_entry is not None and metric_qname is None:
        packet = {
            "schema_version": SCHEMA_VERSION,
            "ticker": ticker,
            "metric": metric,
            "metric_qname": None,
            "qname_source": None,
            "period_of_report": period,
            "pit_cutoff": pit_cutoff,
            "source_mode": mode,
            "view_capability": {
                "segments": bool(map_entry.get("works_for_segments")),
                "geography": bool(map_entry.get("works_for_geography")),
                "product_service": bool(map_entry.get("works_for_product_service")),
            },
            "per_period_splits": [],
            "gaps": [{"type": "non_primary_qname", "reason": "coordinator-review nulled ticker"}],
            "assembled_at": _now_iso(),
            "elapsed_s": round(time.time() - t0, 3),
        }
        if write_packets:
            _write_packets(packet, {"audit_rows": []}, ticker, out_dir)
        return packet

    # 2b. Ticker not in map (fallback either disabled or exhausted)
    if metric_qname is None:
        gap_type = (
            "fallback_discovery_exhausted" if tried_candidates else "ticker_not_in_universe"
        )
        gap_reason = (
            f"No standard revenue candidate produced facts for {ticker!r}; "
            f"tried {tried_candidates}"
            if tried_candidates
            else f"Ticker {ticker!r} is outside the 783-ticker Wave 2 universe "
                 f"(enable --allow-discovery-fallback to attempt fallback discovery)"
        )
        packet = {
            "schema_version": SCHEMA_VERSION,
            "ticker": ticker,
            "metric": metric,
            "metric_qname": None,
            "qname_source": None,
            "period_of_report": period,
            "pit_cutoff": pit_cutoff,
            "source_mode": mode,
            "view_capability": {"segments": False, "geography": False, "product_service": False},
            "per_period_splits": [],
            "gaps": [{"type": gap_type, "reason": gap_reason}],
            "assembled_at": _now_iso(),
            "elapsed_s": round(time.time() - t0, 3),
        }
        if write_packets:
            _write_packets(packet, {"audit_rows": []}, ticker, out_dir)
        return packet

    # 2. Connect + discover periods
    manager = get_manager()
    period_rows = manager.execute_cypher_query_all(
        _ALL_PERIODS_QUERY,
        {"ticker": ticker, "snapshot_ts": pit_cutoff, "limit": history_quarters * 2},
    ) or []
    discovered_periods = [r["period"] for r in period_rows]

    # If caller pinned a period, focus on it + predecessors (for Q4 derivation)
    if period:
        discovered_periods = [p for p in discovered_periods if p <= period][:history_quarters]

    target_periods = discovered_periods[:history_quarters]
    if not target_periods:
        packet = {
            "schema_version": SCHEMA_VERSION,
            "ticker": ticker,
            "metric": metric,
            "metric_qname": metric_qname,
            "qname_source": qname_source,
            "period_of_report": period,
            "pit_cutoff": pit_cutoff,
            "source_mode": mode,
            "view_capability": {
                "segments": bool(map_entry.get("works_for_segments")),
                "geography": bool(map_entry.get("works_for_geography")),
                "product_service": bool(map_entry.get("works_for_product_service")),
            },
            "per_period_splits": [],
            "gaps": [{"type": "no_periods_after_pit_cutoff"}],
            "assembled_at": _now_iso(),
            "elapsed_s": round(time.time() - t0, 3),
        }
        if write_packets:
            _write_packets(packet, {"audit_rows": []}, ticker, out_dir)
        return packet

    # 3. Fetch facts
    raw_rows = _fetch_facts(manager, ticker, metric_qname, target_periods, pit_cutoff)

    # 4. Normalize + dedupe
    skipped_audit: list[dict] = []
    normalized: list[dict] = []
    for row in raw_rows:
        n = _normalize_fact_row(row)
        if n is None:
            continue
        if n.get("__skip__"):
            skipped_audit.append(n)
            continue
        normalized.append(n)
    normalized = _dedupe_rows(normalized)

    # 5. Build primary views per (period, duration)
    per_pd_views = _build_primary_views(normalized)

    # 6. Emit per-period blocks
    blocks: list[dict] = []
    for (pd_period, pd_duration), primary in per_pd_views.items():
        if pd_duration == "instant":
            continue
        block = _build_period_block(metric, metric_qname, pd_period, pd_duration, primary, map_entry)
        blocks.append(block)

    # 7. Q4 derivation: for each annual block, try FY − 9M YTD
    derived_blocks: list[dict] = []
    for fy_block in blocks:
        if fy_block["duration"] != "annual":
            continue
        ytd = _locate_q3_ytd_block(blocks, fy_block["period_of_report"])
        quarterlies = _locate_quarterly_blocks(blocks, fy_block)
        derived = _derive_q4_for_period(fy_block, ytd, quarterlies, map_entry)
        derived_blocks.append(derived)

    # 8. Merge + sort by period desc, annual first within period
    all_blocks = blocks + derived_blocks

    def _block_sort_key(b: dict) -> tuple:
        order = {"annual": 0, "nine_month": 1, "semi_annual": 2, "quarterly": 3, "derived_q4": 4, "other": 9}
        return (b["period_of_report"], -order.get(b["duration"], 9))
    all_blocks.sort(key=_block_sort_key, reverse=True)

    # 9. Audit: cross_dim residuals that never collapsed
    audit_rows: list[dict] = []
    for (pd_period, pd_duration), primary in per_pd_views.items():
        for r in primary.get("cross_dim_residual_rows", []):
            audit_rows.append({
                "period_of_report": pd_period,
                "duration": pd_duration,
                "accession": r.get("accession"),
                "form_type": r.get("form_type"),
                "dim_qnames": r.get("dim_qnames"),
                "member_qnames": r.get("member_qnames"),
                "value": r.get("value"),
                "reason": "cross_dim_unreconciled",
            })
    for sk in skipped_audit:
        audit_rows.append({
            "reason": sk.get("reason"),
            "context_u_id": sk.get("context_u_id"),
            "period_end": sk.get("period_end"),
        })

    # view_capability: for mapped tickers, trust the curated Wave-2 flags.
    # For fallback-discovered tickers, compute from actual reconciled output
    # so the exposed capabilities reflect real structural success, not the
    # synthetic entry's optimistic defaults.
    if qname_source == QNAME_SOURCE_FALLBACK:
        seen_views = set()
        for b in all_blocks:
            for vk, v in b.get("views", {}).items():
                rows = v if isinstance(v, list) else ([v] if v else [])
                if any(r.get("value") is not None for r in rows):
                    seen_views.add(vk)
        view_capability = {
            "segments": VIEW_SEGMENT in seen_views,
            "geography": VIEW_GEOGRAPHY in seen_views,
            "product_service": VIEW_PRODUCT_SERVICE in seen_views,
        }
    else:
        view_capability = {
            "segments": bool(map_entry.get("works_for_segments")),
            "geography": bool(map_entry.get("works_for_geography")),
            "product_service": bool(map_entry.get("works_for_product_service")),
        }

    packet = {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker,
        "metric": metric,
        "metric_qname": metric_qname,
        "qname_source": qname_source,
        "period_of_report": period,
        "pit_cutoff": pit_cutoff,
        "source_mode": mode,
        "view_capability": view_capability,
        "per_period_splits": all_blocks,
        "gaps": [],
        "assembled_at": _now_iso(),
        "elapsed_s": round(time.time() - t0, 3),
    }

    if write_packets:
        _write_packets(packet, {"audit_rows": audit_rows}, ticker, out_dir)
    return packet


def _write_packets(primary: dict, audit: dict, ticker: str, out_dir: Path) -> None:
    """Atomic write of primary + audit files."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    primary_path = out_dir / f"segment_splits_{ticker}.json"
    audit_path = out_dir / f"segment_splits_{ticker}_audit.json"

    def _atomic_write(path: Path, payload: dict) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w") as fh:
            json.dump(payload, fh, indent=2, default=str, ensure_ascii=False)
        os.replace(tmp, path)

    audit_wrapper = {
        "schema_version": "segment_splits_audit.v1",
        "ticker": ticker,
        "audit_rows": audit["audit_rows"],
        "assembled_at": _now_iso(),
    }
    _atomic_write(primary_path, primary)
    _atomic_write(audit_path, audit_wrapper)


# --------------------------------------------------------------------------- #
# Lean bundle summary                                                          #
# --------------------------------------------------------------------------- #

_DISPLAY_LABEL_REPLACEMENTS = (
    ("Canadaand Mexico", "Canada and Mexico"),
    ("Rest Of World", "Rest of World"),
    ("Software As A Service", "Software as a Service"),
    ("Non US Or Europe", "Non US or Europe"),
)


def _display_member_label(label: Optional[str], member: Optional[str]) -> Optional[str]:
    """Return a cleaner display label without changing extraction semantics."""
    raw = (label or member or "").strip()
    if not raw:
        return None

    if ":" in raw:
        raw = raw.split(":", 1)[1]

    raw = re.sub(r"Member$", "", raw)
    raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw)
    raw = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", raw)
    raw = re.sub(r"\bAnd\b", "and", raw)
    raw = re.sub(r"\bOr\b", "or", raw)

    for old, new in _DISPLAY_LABEL_REPLACEMENTS:
        raw = raw.replace(old, new)

    raw = re.sub(r"\bUs\b", "US", raw)
    raw = re.sub(r"\bEmea\b", "EMEA", raw)
    raw = re.sub(r"\bSaa S\b", "SaaS", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" -_/")
    return raw or None


def build_revenue_splits_section(packet: dict, quarter_rows: list[dict], max_quarters: int = 4) -> Optional[dict]:
    """Compress a rich extractor packet into lean LLM-facing percentage tables.

    The returned shape is intentionally small:
      {
        "quarters": [{"period": "...", "fiscal_label": "Q4 FY2025"}, ...],
        "business_segment": [{"member": "...", "label": "...", "pct": [..]}],
        "geography": [...],
        "product_service": [...]
      }

    It contains no provenance, no derivation flags, and no raw values.
    """
    if not packet or packet.get("metric_qname") is None:
        return None

    quarter_rows = list(quarter_rows or [])[:max_quarters]
    if not quarter_rows:
        return None

    blocks_by_period: dict[str, dict[str, dict]] = defaultdict(dict)
    for block in packet.get("per_period_splits", []) or []:
        period = block.get("period_of_report")
        duration = block.get("duration")
        if period and duration:
            blocks_by_period[period][duration] = block

    selected_blocks: list[tuple[dict, Optional[dict]]] = []
    for q in quarter_rows:
        period = q.get("period")
        bucket = blocks_by_period.get(period, {})
        # Builder quarter rows are quarter-equivalent; prefer derived Q4 when
        # the period is an annual filing, otherwise use direct quarterly.
        block = bucket.get("derived_q4") or bucket.get("quarterly")
        selected_blocks.append((q, block))

    out = {
        "quarters": [
            {"period": q.get("period"), "fiscal_label": q.get("fiscal_label", q.get("period", "?"))}
            for q, _ in selected_blocks
        ],
        "business_segment": [],
        "geography": [],
        "product_service": [],
    }

    for view_kind, out_key in (
        (VIEW_SEGMENT, "business_segment"),
        (VIEW_GEOGRAPHY, "geography"),
        (VIEW_PRODUCT_SERVICE, "product_service"),
    ):
        member_to_vals: dict[str, list[Optional[float]]] = {}
        member_to_label: dict[str, str] = {}

        for idx, (_, block) in enumerate(selected_blocks):
            if not block:
                continue
            total_row = block.get("views", {}).get(VIEW_TOTAL)
            total_val = total_row.get("value") if isinstance(total_row, dict) else None
            if total_val in (None, 0):
                continue
            view_rows = block.get("views", {}).get(view_kind) or []
            for row in view_rows:
                member = row.get("member")
                if not member:
                    continue
                label = _display_member_label(row.get("label"), member) or member
                pct = round((float(row["value"]) / float(total_val)) * 100.0, 1)
                member_to_vals.setdefault(member, [None] * len(selected_blocks))[idx] = pct
                # Keep the most recent non-empty label encountered.
                member_to_label.setdefault(member, label)

        def _sort_key(item: tuple[str, list[Optional[float]]]) -> tuple:
            member, vals = item
            most_recent = vals[0]
            return (most_recent is None, -(most_recent or -1.0), member_to_label.get(member, member))

        rows = []
        for member, vals in sorted(member_to_vals.items(), key=_sort_key):
            rows.append({
                "member": member,
                "label": member_to_label.get(member, member),
                "pct": vals,
            })
        out[out_key] = rows

    if not any(out[k] for k in ("business_segment", "geography", "product_service")):
        return None
    return out


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="XBRL Exact Splits — revenue segment extractor (D1)")
    p.add_argument("--ticker", required=True, help="Ticker symbol (uppercased)")
    p.add_argument("--period", default=None, help="Anchor period_of_report (YYYY-MM-DD); discovered if omitted")
    p.add_argument("--pit-cutoff", default=None, help="PIT snapshot timestamp (ISO-8601). None = live mode.")
    p.add_argument("--maps-dir", default=str(DEFAULT_MAPS_DIR), help="Directory with {revenue,operating}_map_783.jsonl")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory for packets")
    p.add_argument("--history-quarters", type=int, default=DEFAULT_HISTORY_QUARTERS, help="How many periods to include")
    p.add_argument("--metric", default="revenue", choices=["revenue", "operating"],
                    help="Which map to use (D1 = revenue only)")
    p.add_argument("--allow-discovery-fallback", action="store_true",
                    help="For tickers outside the curated Wave-2 map, attempt "
                         "lower-trust fallback discovery using standard revenue "
                         "candidates. Packet is tagged qname_source='fallback_discovery'.")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    packet = extract_segment_splits(
        ticker=args.ticker,
        period=args.period,
        pit_cutoff=args.pit_cutoff,
        maps_dir=Path(args.maps_dir),
        out_dir=Path(args.out_dir),
        history_quarters=args.history_quarters,
        metric=args.metric,
        allow_discovery_fallback=args.allow_discovery_fallback,
    )
    # Print a concise summary to stdout
    n_periods = len(packet.get("per_period_splits", []))
    n_derived = sum(1 for b in packet.get("per_period_splits", []) if b.get("is_derived_q4"))
    print(json.dumps({
        "ticker": packet["ticker"],
        "metric": packet["metric"],
        "metric_qname": packet["metric_qname"],
        "qname_source": packet.get("qname_source"),
        "periods_emitted": n_periods,
        "q4_derived": n_derived,
        "source_mode": packet["source_mode"],
        "pit_cutoff": packet["pit_cutoff"],
        "elapsed_s": packet["elapsed_s"],
        "primary_path": str(Path(args.out_dir) / f"segment_splits_{packet['ticker']}.json"),
        "audit_path":   str(Path(args.out_dir) / f"segment_splits_{packet['ticker']}_audit.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
