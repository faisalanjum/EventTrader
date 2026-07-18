"""S3.5 FUSION — §11.4 v3.6: fills nulls only, on CANONICAL values (units run first —
the 1B/1M trap), ten-signature-slot disagreement prevents fusion, ambiguous groups
PARK, LWW-with-log for quote/state/date, permutation-identical. TDD: written first."""
import random
from decimal import Decimal

from driver.core.driver_fusion import fuse_event


def frag(idx, key="k1", **over):
    f = {"driver_name": "revenue", "driver_state": "reported", "quote": "q",
         "date": "2026-07-01", "source_type": "8k",
         "level_low": None, "level_high": None, "level_unit": None,
         "change_value": None, "change_unit": None,
         "comparison_low": None, "comparison_high": None, "comparison_baseline": None,
         "value_text": None, "conditions": None}
    f.update(over)
    return (idx, key, f)


def test_complementary_fragments_fuse_fill_nulls_only():
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("42600"), level_high=Decimal("42600"),
             level_unit="m_usd"),
        frag(1, change_value=Decimal("12"), change_unit="percent_yoy"),
    ])
    assert parked == [] and len(fused) == 1
    f = fused[0]
    assert f.indexes == (0, 1)
    assert f.fact["level_low"] == Decimal("42600") and f.fact["level_unit"] == "m_usd"
    assert f.fact["change_value"] == Decimal("12")


def test_signature_slot_disagreement_prevents_fusion_canonical_values():
    # post-units both are CANONICAL: a real disagreement (1000 vs 1) stands as two
    # facts for the OD-8 ladder — fusion never averages, never picks
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("1000"), level_high=Decimal("1000"), level_unit="m_usd"),
        frag(1, level_low=Decimal("1"), level_high=Decimal("1"), level_unit="m_usd"),
    ])
    assert parked == [] and len(fused) == 2
    assert sorted(f.indexes for f in fused) == [(0,), (1,)]


def test_equal_canonical_values_are_not_a_conflict():
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("42600.0"), level_high=Decimal("42600.0")),
        frag(1, level_low=Decimal("42600"), level_high=Decimal("42600"),
             change_value=Decimal("12"), change_unit="percent_yoy"),
    ])
    assert parked == [] and len(fused) == 1 and fused[0].indexes == (0, 1)


def test_lww_is_deterministic_and_logged():
    fused, parked = fuse_event([
        frag(0, quote="older wording", date="2026-06-30",
             level_low=Decimal("5"), level_high=Decimal("5")),
        frag(1, quote="newer wording", date="2026-07-01",
             change_value=Decimal("2"), change_unit="percent_yoy"),
    ])
    assert len(fused) == 1
    assert fused[0].fact["quote"] == "newer wording"      # latest date wins
    assert any(log["event"] == "fused_fragment" and "quote" in log["dropped_fields"]
               for log in fused[0].logs)


def test_ambiguous_group_parks_whole():
    # A fuses with B, A conflicts with C -> neither clean-fold nor all-conflict
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("10"), level_high=Decimal("10")),
        frag(1, change_value=Decimal("3"), change_unit="percent_yoy"),
        frag(2, level_low=Decimal("11"), level_high=Decimal("11")),
    ])
    assert fused == []
    assert len(parked) == 1 and parked[0].code == "FUSION_AMBIGUOUS"
    assert parked[0].indexes == (0, 1, 2)


def test_different_keys_never_interact():
    fused, parked = fuse_event([
        frag(0, key="a", level_low=Decimal("1"), level_high=Decimal("1")),
        frag(1, key="b", level_low=Decimal("2"), level_high=Decimal("2")),
    ])
    assert parked == [] and len(fused) == 2


def test_permutation_identical():
    items = [
        frag(0, level_low=Decimal("42600"), level_high=Decimal("42600"),
             level_unit="m_usd", date="2026-06-30", quote="a"),
        frag(1, change_value=Decimal("12"), change_unit="percent_yoy",
             date="2026-07-01", quote="b"),
        frag(2, key="k2", level_low=Decimal("7"), level_high=Decimal("7")),
    ]
    base = fuse_event(items)
    for seed in range(6):
        shuffled = items[:]
        random.Random(seed).shuffle(shuffled)
        assert fuse_event(shuffled) == base


def test_fill_never_overwrites_a_present_value():
    fused, _ = fuse_event([
        frag(0, level_low=Decimal("5"), level_high=Decimal("5"), value_text=None),
        frag(1, value_text="approximately five"),
    ])
    assert len(fused) == 1
    assert fused[0].fact["level_low"] == Decimal("5")
    assert fused[0].fact["value_text"] == "approximately five"


# ---- step-7 round 3: member_refs union/dedupe/incompatibility (TDD red first) ----

R_GEO = {"axis": "srt:StatementGeographicalAxis", "member": "country:US",
         "slice_part": "geography:us"}
R_SEG = {"axis": "us-gaap:StatementBusinessSegmentsAxis", "member": "country:US",
         "slice_part": "segment:us"}


def test_member_refs_identical_complete_lists_fuse():
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("5"), level_high=Decimal("5"), level_unit="m_usd",
             member_refs=[dict(R_SEG), dict(R_GEO)]),
        frag(1, change_value=Decimal("2"), change_unit="percent_yoy",
             member_refs=[dict(R_GEO), dict(R_SEG)]),      # same SET, any order
    ])
    assert parked == [] and len(fused) == 1
    assert fused[0].fact["member_refs"] == [R_GEO, R_SEG]  # sorted, deduped


def test_member_refs_none_is_no_claim_and_inherits_the_one_list():
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("5"), level_high=Decimal("5"), level_unit="m_usd"),
        frag(1, change_value=Decimal("2"), change_unit="percent_yoy",
             member_refs=[dict(R_SEG)]),
    ])
    assert parked == [] and len(fused) == 1
    assert fused[0].fact["member_refs"] == [R_SEG]         # None never erases refs


def test_member_refs_two_different_complete_lists_park_never_union():
    # each verified list is COMPLETE — combining [geo] and [seg] would fabricate
    # a dimension set no real XBRL fact carries (reproduced 2026-07-17)
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("5"), level_high=Decimal("5"), level_unit="m_usd",
             member_refs=[dict(R_GEO)]),
        frag(1, change_value=Decimal("2"), change_unit="percent_yoy",
             member_refs=[dict(R_SEG)]),
    ])
    assert fused == [] and len(parked) == 1
    assert parked[0].code == "FUSION_AMBIGUOUS" and parked[0].indexes == (0, 1)
    assert "different complete dimension sets" in parked[0].reason


def test_member_refs_subset_list_also_parks():
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("5"), level_high=Decimal("5"), level_unit="m_usd",
             member_refs=[dict(R_GEO)]),
        frag(1, change_value=Decimal("2"), change_unit="percent_yoy",
             member_refs=[dict(R_GEO), dict(R_SEG)]),      # superset != identical
    ])
    assert fused == [] and len(parked) == 1
    assert parked[0].code == "FUSION_AMBIGUOUS"


def test_member_refs_verified_empty_vs_refs_is_incompatible_parks():
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("5"), level_high=Decimal("5"), level_unit="m_usd",
             member_refs=[]),                               # VERIFIED no dimensions
        frag(1, change_value=Decimal("2"), change_unit="percent_yoy",
             member_refs=[dict(R_SEG)]),
    ])
    assert fused == [] and len(parked) == 1
    assert parked[0].code == "FUSION_AMBIGUOUS" and parked[0].indexes == (0, 1)


def test_member_refs_same_provenance_two_slice_parts_parks():
    fused, parked = fuse_event([
        frag(0, level_low=Decimal("5"), level_high=Decimal("5"), level_unit="m_usd",
             member_refs=[dict(R_GEO)]),
        frag(1, change_value=Decimal("2"), change_unit="percent_yoy",
             member_refs=[dict(R_GEO, slice_part="geography:americas")]),
    ])
    assert fused == [] and len(parked) == 1
    assert parked[0].code == "FUSION_AMBIGUOUS"


def test_member_refs_fold_is_permutation_identical():
    def build(order):
        frags = [frag(0, level_low=Decimal("5"), level_high=Decimal("5"),
                      level_unit="m_usd", member_refs=[dict(R_SEG), dict(R_GEO)]),
                 frag(1, change_value=Decimal("2"), change_unit="percent_yoy",
                      member_refs=[dict(R_GEO), dict(R_SEG)])]
        items = [frags[i] for i in order]
        items = [(n, k, f) for n, (_, k, f) in enumerate(items)]
        fused, parked = fuse_event(items)
        assert parked == []
        return fused[0].fact["member_refs"]
    assert build([0, 1]) == build([1, 0]) == [R_GEO, R_SEG]
