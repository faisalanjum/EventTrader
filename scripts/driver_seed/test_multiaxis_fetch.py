"""R1 RED: the FETCH side must emit EVERY raw (axis, member) pair for a multi-axis XBRL fact.

Real fixture: a CAG 10-K 2025 fact whose `segment.explicitMember` is a LIST (the multi-axis shape).
The certified `oracle._members_all` reads both members; `link_lib.seg_axis_members` currently drops the
list shape and returns [] -> the fact would masquerade as a consolidated total (ChannelContract §3 /
OD-17c "never silently consolidate"). This pins the bug R1 fixes.

    venv/bin/python -m pytest scripts/driver_seed/test_multiaxis_fetch.py -q
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
import link_lib
import oracle

# REAL multi-axis fact, extracted read-only from Neo4j (CAG 10-K, period 2025-05-25).
MULTIAXIS_FC = {
    "segment": {"explicitMember": [
        {"dimension": "us-gaap:DisposalGroupClassificationAxis",
         "$t": "us-gaap:DisposalGroupHeldforsaleNotDiscontinuedOperationsMember"},
        {"dimension": "us-gaap:IncomeStatementBalanceSheetAndAdditionalDisclosuresByDisposalGroupsIncludingDiscontinuedOperationsAxis",
         "$t": "cag:ChefBoyardeeBusinessMember"}]},
    "value": "69200000", "period": {"instant": "2025-05-25"}}

BOTH_MEMBERS = {"us-gaap:DisposalGroupHeldforsaleNotDiscontinuedOperationsMember",
                "cag:ChefBoyardeeBusinessMember"}

BOTH_PAIRS = {
    ("us-gaap:DisposalGroupClassificationAxis",
     "us-gaap:DisposalGroupHeldforsaleNotDiscontinuedOperationsMember"),
    ("us-gaap:IncomeStatementBalanceSheetAndAdditionalDisclosuresByDisposalGroupsIncludingDiscontinuedOperationsAxis",
     "cag:ChefBoyardeeBusinessMember"),
}


def test_certified_parser_reads_both_members():
    # characterization: pins the certified behavior we must match (already GREEN).
    assert set(oracle._members_all(MULTIAXIS_FC)) == BOTH_MEMBERS


def test_fetch_emission_captures_both_axis_member_pairs():
    # RED: the packet's raw emission must carry BOTH exact (axis, member) pairs, never [] (mislabel as total).
    pairs = link_lib.seg_axis_members(MULTIAXIS_FC)
    assert set(pairs) == BOTH_PAIRS, f"multi-axis (axis,member) pairs dropped -> masquerades as consolidated: {pairs}"
