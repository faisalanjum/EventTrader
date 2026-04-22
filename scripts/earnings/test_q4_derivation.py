"""Unit tests for q4_derivation primitives.

Pure unit tests — no Neo4j, no I/O. Covers every NULL_REASONS path plus
the arithmetic primitives.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

import pytest

from q4_derivation import (
    NULL_REASONS,
    normalize_uid,
    qname_from_uid,
    row_signature,
    fy_minus_9m_ytd,
    fy_minus_q1q2q3,
    derive_q4_view,
)


# --------------------------------------------------------------------------- #
# Normalization                                                                #
# --------------------------------------------------------------------------- #

def test_normalize_uid_strips_zero_padded_cik():
    assert normalize_uid("0001467858:http://fasb.org/srt/2025:srt:Axis") == \
        "1467858:http://fasb.org/srt/2025:srt:Axis"


def test_normalize_uid_preserves_non_numeric_prefix():
    assert normalize_uid("us-gaap:SomeMember") == "us-gaap:SomeMember"


def test_normalize_uid_passes_through_none():
    assert normalize_uid(None) is None
    assert normalize_uid("") == ""


def test_qname_from_uid_extracts_trailing_prefix_localname():
    uid = "0001467858:http://fasb.org/srt/2025:srt:ProductOrServiceAxis"
    assert qname_from_uid(uid) == "srt:ProductOrServiceAxis"


def test_qname_from_uid_works_without_cik():
    assert qname_from_uid("us-gaap:StatementBusinessSegmentsAxis") == \
        "us-gaap:StatementBusinessSegmentsAxis"


def test_row_signature_independent_of_uid_ordering():
    sig_a = row_signature("us-gaap:Revenues", "business_segment",
                          ["0001467858:http://fasb.org/us-gaap/2025:us-gaap:NASTMember",
                           "0001467858:http://fasb.org/us-gaap/2025:us-gaap:GFSMember"])
    sig_b = row_signature("us-gaap:Revenues", "business_segment",
                          ["1467858:http://fasb.org/us-gaap/2025:us-gaap:GFSMember",
                           "1467858:http://fasb.org/us-gaap/2025:us-gaap:NASTMember"])
    assert sig_a == sig_b


def test_row_signature_varies_with_view_kind():
    a = row_signature("us-gaap:Revenues", "business_segment", ["X:Y"])
    b = row_signature("us-gaap:Revenues", "geography", ["X:Y"])
    assert a != b


# --------------------------------------------------------------------------- #
# Arithmetic primitives                                                        #
# --------------------------------------------------------------------------- #

def test_fy_minus_9m_ytd_happy_path():
    v, tag = fy_minus_9m_ytd(100.0, 75.0, -3, -3, "USD", "USD")
    assert tag == "fy_minus_9m_ytd"
    assert v == pytest.approx(25.0)


def test_fy_minus_9m_ytd_unit_mismatch():
    v, tag = fy_minus_9m_ytd(100.0, 75.0, -3, -3, "USD", "EUR")
    assert v is None
    assert tag == "q4_unit_mismatch"


def test_fy_minus_9m_ytd_decimals_unreconcilable():
    v, tag = fy_minus_9m_ytd(100.0, 75.0, 0, -7, "USD", "USD")
    assert v is None
    assert tag == "q4_decimals_unreconcilable"


def test_fy_minus_q1q2q3_happy_path():
    v, tag = fy_minus_q1q2q3(100.0, [25.0, 25.0, 25.0],
                              -3, [-3, -3, -3], "USD", ["USD", "USD", "USD"])
    assert tag == "fy_minus_q1q2q3"
    assert v == pytest.approx(25.0)


def test_fy_minus_q1q2q3_missing_quarter_rejects():
    v, tag = fy_minus_q1q2q3(100.0, [25.0, 25.0], -3, [-3, -3], "USD", ["USD", "USD"])
    assert v is None
    assert tag == "q4_missing_q1q2q3_fallback"


def test_fy_minus_q1q2q3_unit_mismatch():
    v, tag = fy_minus_q1q2q3(100.0, [25.0, 25.0, 25.0], -3, [-3, -3, -3],
                              "USD", ["USD", "USD", "EUR"])
    assert v is None
    assert tag == "q4_unit_mismatch"


# --------------------------------------------------------------------------- #
# derive_q4_view top-level guards                                              #
# --------------------------------------------------------------------------- #

def _row(**kwargs):
    """Small factory for test row dicts."""
    return {
        "value": kwargs.get("value", 100.0),
        "basis_type": kwargs.get("basis_type", "memberless_total"),
        "view_kind": kwargs.get("view_kind", "business_segment"),
        "member_signature": kwargs.get("member_signature", frozenset(["us-gaap:NASTMember"])),
        "decimals": kwargs.get("decimals", -3),
        "unit": kwargs.get("unit", "USD"),
    }


def test_derive_q4_annual_only_flag():
    v, tag = derive_q4_view(_row(), _row(value=75.0), None, annual_only_map_flag=True)
    assert v is None
    assert tag == "q4_annual_only_validation"


def test_derive_q4_fy_missing():
    v, tag = derive_q4_view(None, _row(value=75.0), None)
    assert v is None
    assert tag == "q4_fy_missing"


def test_derive_q4_cross_dim_unreconciled():
    v, tag = derive_q4_view(_row(view_kind="cross_dim"), _row(value=75.0), None)
    assert v is None
    assert tag == "q4_cross_dim_unreconciled"


def test_derive_q4_mixed_basis():
    v, tag = derive_q4_view(_row(basis_type="memberless_total"),
                             _row(value=75.0, basis_type="aggregate_basis"),
                             None)
    assert v is None
    assert tag == "q4_mixed_basis"


def test_derive_q4_segment_membership_mismatch():
    v, tag = derive_q4_view(
        _row(member_signature=frozenset(["us-gaap:NASTMember"])),
        _row(value=75.0, member_signature=frozenset(["us-gaap:GFSMember"])),
        None,
    )
    assert v is None
    assert tag == "q4_segment_membership_mismatch"


def test_derive_q4_happy_path_via_9m():
    v, tag = derive_q4_view(_row(value=100.0), _row(value=75.0), None)
    assert tag == "fy_minus_9m_ytd"
    assert v == pytest.approx(25.0)


def test_derive_q4_missing_9m_no_fallback():
    v, tag = derive_q4_view(_row(), None, None)
    assert v is None
    assert tag == "q4_missing_9m_ytd"


def test_derive_q4_fallback_q1q2q3_happy_path():
    v, tag = derive_q4_view(
        _row(value=100.0),
        None,
        [_row(value=25.0), _row(value=25.0), _row(value=25.0)],
    )
    assert tag == "fy_minus_q1q2q3"
    assert v == pytest.approx(25.0)


def test_derive_q4_fallback_rejects_quarterly_basis_mismatch():
    v, tag = derive_q4_view(
        _row(value=100.0, basis_type="memberless_total"),
        None,
        [_row(value=25.0, basis_type="memberless_total"),
         _row(value=25.0, basis_type="aggregate_basis"),
         _row(value=25.0, basis_type="memberless_total")],
    )
    assert v is None
    assert tag == "q4_mixed_basis"


def test_derive_q4_fallback_rejects_quarterly_member_mismatch():
    v, tag = derive_q4_view(
        _row(value=100.0, member_signature=frozenset(["A"])),
        None,
        [_row(value=25.0, member_signature=frozenset(["A"])),
         _row(value=25.0, member_signature=frozenset(["B"])),
         _row(value=25.0, member_signature=frozenset(["A"]))],
    )
    assert v is None
    assert tag == "q4_segment_membership_mismatch"


def test_null_reasons_enum_membership():
    # Ensure every reason returned above is declared in the enum
    returned = {
        "q4_annual_only_validation", "q4_fy_missing", "q4_cross_dim_unreconciled",
        "q4_mixed_basis", "q4_segment_membership_mismatch",
        "q4_missing_9m_ytd", "q4_missing_q1q2q3_fallback",
        "q4_unit_mismatch", "q4_decimals_unreconcilable",
    }
    assert returned.issubset(NULL_REASONS)
