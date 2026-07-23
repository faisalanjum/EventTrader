"""Phase-5 item 4 — the backfill handoff seam (Design D14-v3, the locked
narrow gate).

`backfill_candidate_driver_name` is a CORE-ONLY side record keyed by item/fact
identity, riding existing provenance — never a public packet field, never a
registry, never a new subsystem. Exactly ONE candidate may reach the kernel;
the kernel reconfirms from OLD-SOURCE evidence alone; a mismatch never forces
attachment. The real kernel does not exist (S4): this seam is the pure gate it
will call, and the reconfirmation verdict arrives as its recorded judgment.
"""
import pytest

from driver.core.backfill_seam import backfill_gate
from driver.core.prepared_fact import PreparedFactV1, SchemaError


def test_zero_candidates_no_forced_attachment():
    d = backfill_gate([], reconfirmed=None)
    assert d.driver_name is None and d.reason == "no_candidate"


def test_exactly_one_correct_candidate_attaches_after_recheck():
    d = backfill_gate(["revenue"], reconfirmed=True)
    assert d.driver_name == "revenue" and d.reason == "reconfirmed"


def test_one_wrong_candidate_never_attaches():
    d = backfill_gate(["revenue"], reconfirmed=False)
    assert d.driver_name is None and d.reason == "reconfirmation_failed"


def test_missing_reconfirmation_fails_closed():
    d = backfill_gate(["revenue"], reconfirmed=None)
    assert d.driver_name is None and d.reason == "reconfirmation_missing"


def test_multiple_candidates_fail_closed_ambiguous():
    d = backfill_gate(["revenue", "net_revenue"], reconfirmed=True)
    assert d.driver_name is None and d.reason == "ambiguous_multiple"
    # duplicates of one name are STILL multiple entries — fail closed, never
    # deduplicated here (dedup would be a silent judgment)
    d2 = backfill_gate(["revenue", "revenue"], reconfirmed=True)
    assert d2.driver_name is None and d2.reason == "ambiguous_multiple"


def test_malformed_candidate_fails_closed():
    for bad in ([""], ["  "], [None], [42]):
        d = backfill_gate(bad, reconfirmed=True)
        assert d.driver_name is None and d.reason == "malformed_candidate"


def test_unlawful_driver_names_rejected_never_normalized():
    # Core's NAME-05 law (the SAME check build_id enforces) — the gate must
    # REJECT these outright, never clean, casefold, trim, or normalize them
    # "revenue\n": Python's $ matches BEFORE a final newline — re.match+$
    # accepted it and build_id minted an id containing a newline (reproduced);
    # the predicate must use exact full-string matching and REJECT, never trim
    for bad in (["Revenue"], ["a__b"], ["a_"], [" revenue "], ["1x"], ["a"],
                ["revenue\n"]):
        d = backfill_gate(bad, reconfirmed=True)
        assert d.driver_name is None and d.reason == "malformed_candidate", bad


def test_public_packet_rejects_the_field():
    # never a public packet field: the frozen schema rejects it as unknown
    assert "backfill_candidate_driver_name" not in PreparedFactV1.FIELDS
    with pytest.raises(SchemaError):
        PreparedFactV1.from_dict({
            "driver_name": "revenue", "driver_state": "reported",
            "quote": "q", "backfill_candidate_driver_name": "revenue"})


def test_side_record_rides_item_identity():
    # the side record is a plain mapping keyed by ITEM identity — one optional
    # candidate list per internal fact, resolved independently per item
    side = {"item-1": ["revenue"], "item-2": [], "item-3": ["a", "b"]}
    verdicts = {k: backfill_gate(v, reconfirmed=(True if len(v) == 1 else None))
                for k, v in side.items()}
    assert verdicts["item-1"].driver_name == "revenue"
    assert verdicts["item-2"].driver_name is None
    assert verdicts["item-3"].reason == "ambiguous_multiple"
