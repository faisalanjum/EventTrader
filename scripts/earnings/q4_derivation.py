"""Q4 derivation primitives for segment-level XBRL split extraction (D1 sidecar).

This module defines the arithmetic and identity primitives needed to derive Q4
values from FY and 9M YTD rows at the segment level.

Design principles:
  1. Precision-first — null on any ambiguity, never silently approximate.
  2. Identity-before-math — normalize u_ids to stable qnames before comparing.
  3. Orthogonal schema — basis_type / is_derived_q4 / derivation_method /
     null_reason are independent axes.
  4. One-way dependency — imports from build_prior_financials.py but is never
     imported by production code (sidecar contract).

Public surface:
  - NULL_REASONS             (frozenset of canonical null-reason tags)
  - normalize_uid(uid)       -> str | None
  - qname_from_uid(uid)      -> str | None
  - row_signature(metric_qname, view_kind, member_u_ids) -> tuple
  - fy_minus_9m_ytd(...)     -> (value | None, method_or_reason)
  - fy_minus_q1q2q3(...)     -> (value | None, method_or_reason)
  - derive_q4_view(fy_row, ytd_9m_row, quarterly_rows) -> (value | None, method_or_reason)

Re-exported from build_prior_financials.py (canonical source):
  - classify_period
  - is_target_period
"""
from __future__ import annotations

from typing import Iterable, Optional

# Re-export canonical period helpers from production. One-way import.
from build_prior_financials import classify_period, is_target_period  # noqa: F401


# --------------------------------------------------------------------------- #
# Null reasons — canonical enum                                                #
# --------------------------------------------------------------------------- #

NULL_REASONS: frozenset[str] = frozenset({
    # Required (ChatGPT + user alignment)
    "q4_missing_9m_ytd",
    "q4_missing_q1q2q3_fallback",
    "q4_segment_membership_mismatch",     # true reorg: member sets differ
    "q4_segment_rename_detected",         # fuzzy-label match; recoverable later
    "q4_mixed_basis",                     # FY and prior rows disagree on basis_type
    "q4_cross_dim_unreconciled",          # view_kind == cross_dim
    "q4_annual_only_validation",          # map flags annual-only; no Q4 derivation possible
    # Guardrail extras (non-conflicting)
    "q4_unit_mismatch",                   # USD vs USD-millions etc.
    "q4_decimals_unreconcilable",         # decimals diverge beyond safe tolerance
    "q4_fy_missing",                      # no FY row at all
    "non_primary_qname",                  # coordinator-flagged ticker
})


# --------------------------------------------------------------------------- #
# Identity normalization                                                       #
# --------------------------------------------------------------------------- #

def normalize_uid(uid: Optional[str]) -> Optional[str]:
    """Strip leading zeros from a numeric CIK prefix so padded and unpadded
    forms compare equal.

    Example:
        '0001467858:http://fasb.org/srt/2025:srt:ProductOrServiceAxis'
        -> '1467858:http://fasb.org/srt/2025:srt:ProductOrServiceAxis'
    """
    if not uid:
        return uid
    parts = uid.split(":", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return f"{int(parts[0])}:{parts[1]}"
    return uid


def qname_from_uid(uid: Optional[str]) -> Optional[str]:
    """Extract the trailing prefix:localname qname from a u_id.

    Example:
        '0001467858:http://fasb.org/srt/2025:srt:ProductOrServiceAxis'
        -> 'srt:ProductOrServiceAxis'
    """
    if not uid:
        return None
    uid = normalize_uid(uid)
    parts = uid.split(":")
    if len(parts) >= 2:
        return f"{parts[-2]}:{parts[-1]}"
    return None


def row_signature(
    metric_qname: str,
    view_kind: str,
    member_u_ids: Iterable[str],
) -> tuple[str, str, frozenset[str]]:
    """Stable identity key for a split row.

    Identity is independent of basis_type — basis is a separate guard.
    Identity is independent of raw u_id — member qnames are normalized.

    Args:
        metric_qname: e.g. "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
        view_kind: "total" | "business_segment" | "geography" | "product_service" | "cross_dim"
        member_u_ids: raw u_ids from Context.member_u_ids; normalized inside

    Returns:
        (metric_qname, view_kind, frozenset(normalized member qnames))
    """
    normalized_members: set[str] = set()
    for uid in member_u_ids or []:
        qn = qname_from_uid(uid)
        if qn:
            normalized_members.add(qn)
    return (metric_qname, view_kind, frozenset(normalized_members))


# --------------------------------------------------------------------------- #
# Arithmetic primitives                                                        #
# --------------------------------------------------------------------------- #

def _decimals_compatible(dec_a: Optional[int], dec_b: Optional[int]) -> bool:
    """XBRL decimals values reconcile when within a reasonable delta.

    decimals = -6 means rounded to millions; -3 means rounded to thousands.
    A gap of 3 (e.g. -3 vs -6) is tolerable at the row level because we
    widen tolerance to match the coarser side.
    A gap > 6 indicates truly incompatible rounding (shouldn't happen in
    clean filings; null the derivation).
    """
    if dec_a is None or dec_b is None:
        return True  # If either is missing we can't assert incompatibility
    return abs(dec_a - dec_b) <= 6


def _combined_tolerance(decimals_list: list[Optional[int]], scale_hint: float = 1.0) -> float:
    """Tolerance = 10 ** (-min_dec). Uses the most negative (coarsest) decimals."""
    valid = [d for d in decimals_list if d is not None]
    if not valid:
        return max(1.0, abs(scale_hint) * 0.001)
    min_dec = min(valid)
    return 10 ** (-min_dec)


def fy_minus_9m_ytd(
    fy_value: float,
    ytd_9m_value: float,
    fy_decimals: Optional[int],
    ytd_decimals: Optional[int],
    fy_unit: str,
    ytd_unit: str,
) -> tuple[Optional[float], str]:
    """Compute Q4 = FY − 9M YTD. Returns (value, 'fy_minus_9m_ytd') on success,
    (None, reason) on guardrail failure.
    """
    if fy_unit != ytd_unit:
        return None, "q4_unit_mismatch"
    if not _decimals_compatible(fy_decimals, ytd_decimals):
        return None, "q4_decimals_unreconcilable"
    return float(fy_value) - float(ytd_9m_value), "fy_minus_9m_ytd"


def fy_minus_q1q2q3(
    fy_value: float,
    q_values: list[float],
    fy_decimals: Optional[int],
    q_decimals_list: list[Optional[int]],
    fy_unit: str,
    q_units: list[str],
) -> tuple[Optional[float], str]:
    """Compute Q4 = FY − (Q1 + Q2 + Q3). Fallback path when 9M YTD is missing.

    Returns (value, 'fy_minus_q1q2q3') on success, (None, reason) on failure.
    """
    if len(q_values) != 3 or len(q_decimals_list) != 3 or len(q_units) != 3:
        return None, "q4_missing_q1q2q3_fallback"
    if any(u != fy_unit for u in q_units):
        return None, "q4_unit_mismatch"
    for qd in q_decimals_list:
        if not _decimals_compatible(fy_decimals, qd):
            return None, "q4_decimals_unreconcilable"
    return float(fy_value) - sum(float(v) for v in q_values), "fy_minus_q1q2q3"


# --------------------------------------------------------------------------- #
# Top-level Q4 derivation                                                      #
# --------------------------------------------------------------------------- #

def _member_sig(row: dict) -> frozenset[str]:
    """Extract the normalized member-qname set from a row dict."""
    sig = row.get("member_signature")
    if isinstance(sig, (set, frozenset)):
        return frozenset(sig)
    if isinstance(sig, (list, tuple)):
        return frozenset(sig)
    # Fallback: derive from raw member_u_ids if caller didn't pre-normalize
    uids = row.get("member_u_ids", [])
    return frozenset(q for q in (qname_from_uid(u) for u in uids) if q)


def derive_q4_view(
    fy_row: Optional[dict],
    ytd_9m_row: Optional[dict],
    quarterly_rows: Optional[list[dict]] = None,
    *,
    annual_only_map_flag: bool = False,
) -> tuple[Optional[float], str]:
    """Derive a Q4 value for a single (metric, view_kind, member_sig) triple.

    Applies guardrails in this order:
      1. annual_only_map_flag set by caller  -> q4_annual_only_validation
      2. fy_row is None                      -> q4_fy_missing
      3. view_kind == 'cross_dim'            -> q4_cross_dim_unreconciled
      4. FY basis != 9M basis                -> q4_mixed_basis
      5. FY member_sig != 9M member_sig      -> q4_segment_rename_detected
                                                (if fuzzy-label stub matches)
                                                or q4_segment_membership_mismatch
      6. fy_minus_9m_ytd guards              -> q4_unit_mismatch / q4_decimals_unreconcilable
      7. 9M missing, try Q1+Q2+Q3 fallback  -> full identity/basis match on all 3
      8. No fallback possible                -> q4_missing_9m_ytd or q4_missing_q1q2q3_fallback

    Each row is a dict with keys:
        value, basis_type, view_kind, member_signature (or member_u_ids),
        decimals, unit

    Returns:
        (value, method_tag) on success where method_tag ∈ {"fy_minus_9m_ytd", "fy_minus_q1q2q3"}
        (None, null_reason_tag) on any guardrail failure
    """
    if annual_only_map_flag:
        return None, "q4_annual_only_validation"
    if fy_row is None:
        return None, "q4_fy_missing"

    fy_view = fy_row.get("view_kind")
    if fy_view == "cross_dim":
        return None, "q4_cross_dim_unreconciled"

    fy_basis = fy_row.get("basis_type")
    fy_sig = _member_sig(fy_row)

    if ytd_9m_row is not None:
        ytd_basis = ytd_9m_row.get("basis_type")
        if fy_basis != ytd_basis:
            return None, "q4_mixed_basis"
        ytd_sig = _member_sig(ytd_9m_row)
        if fy_sig != ytd_sig:
            # D1: rename heuristic is log-only. Always report mismatch; a future
            # D1.5 release may add fuzzy-label matching and flip this to
            # q4_segment_rename_detected when the heuristic confirms.
            return None, "q4_segment_membership_mismatch"
        # All guards passed; do the arithmetic.
        return fy_minus_9m_ytd(
            fy_row["value"],
            ytd_9m_row["value"],
            fy_row.get("decimals"),
            ytd_9m_row.get("decimals"),
            fy_row.get("unit", ""),
            ytd_9m_row.get("unit", ""),
        )

    # 9M YTD missing — try Q1+Q2+Q3 fallback.
    if not quarterly_rows or len(quarterly_rows) != 3:
        return None, "q4_missing_9m_ytd"

    # Every quarterly row must match FY on identity + basis.
    for qr in quarterly_rows:
        if qr.get("basis_type") != fy_basis:
            return None, "q4_mixed_basis"
        if _member_sig(qr) != fy_sig:
            return None, "q4_segment_membership_mismatch"

    return fy_minus_q1q2q3(
        fy_row["value"],
        [qr["value"] for qr in quarterly_rows],
        fy_row.get("decimals"),
        [qr.get("decimals") for qr in quarterly_rows],
        fy_row.get("unit", ""),
        [qr.get("unit", "") for qr in quarterly_rows],
    )
