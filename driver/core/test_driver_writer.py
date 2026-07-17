"""S3.4b — writer/collision planner tests: the OD-8 ladder vs PRE-BATCH graph state,
fill-without-null-clobber, LWW-with-log for non-signature fields, series_unit (OD-10),
period write-once guard. All against a fake in-memory graph — ZERO Neo4j."""
import pytest

from driver.core.driver_ids import signature_hash
from driver.core.driver_writer import (
    FakeGraph,
    WriterError,
    plan_event_write,
    signature,
    stamp_series_unit,
)

SRC = "0000320193-24-000123"
QP = "gp_2025-07-01_2025-09-30"


def mk(level=None, change=None, quote="q", state="reported", **over):
    fact = {
        "id": f"du:{SRC}:revenue:period={QP}",
        "fact_scope": f"period={QP}", "driver_name": "revenue",
        "driver_state": state, "quote": quote, "date": "2025-11-01T16:05:00",
        "source_type": "8k",
        "level_low": level, "level_high": level,
        "level_unit": "m_usd" if level is not None else None,
        "change_value": change,
        "change_unit": "percent_yoy" if change is not None else None,
        "comparison_low": None, "comparison_high": None, "comparison_baseline": None,
        "value_text": None, "conditions": None, "company_confirmed": None,
        "xbrl_qname": None, "fiscal_year": 2025, "fiscal_quarter": 3,
        "period_scope": "quarter", "time_type": "duration",
        "period_u_id": QP, "gp_start_date": "2025-07-01", "gp_end_date": "2025-09-30",
    }
    fact.update(over)
    return fact


def outcome_of(results, fact_id=None):
    if fact_id:
        return [r for r in results if r.fact_id == fact_id]
    return results


# ---- creation, no-op, fill ----

def test_create_bare_with_period_edges_and_series_unit():
    res = plan_event_write([mk(level=100.0)], FakeGraph())
    assert len(res) == 1 and res[0].outcome == "created"
    ops = {o["op"]: o for o in res[0].ops}
    assert ops["create_fact"]["props"]["created"] == "__now__"
    assert ops["create_fact"]["props"]["series_unit"] == "m_usd"
    assert ops["merge_period"]["id"] == QP
    assert {"OF_DRIVER", "FROM_SOURCE", "HAS_PERIOD"} <= {
        o["type"] for o in res[0].ops if o["op"] == "edge"}


def test_noop_rerun_zero_mutations():
    existing = mk(level=100.0, series_unit="m_usd", created="2025-11-01T16:05:01")
    res = plan_event_write([mk(level=100.0)], FakeGraph([existing]))
    assert res[0].outcome == "noop" and res[0].ops == []


def test_compatible_fill_never_null_clobbers():
    existing = mk(level=100.0, series_unit="m_usd", created="x")
    new = mk(level=100.0, change=12.0)
    res = plan_event_write([new], FakeGraph([existing]))
    assert res[0].outcome == "filled"
    sets = [o for o in res[0].ops if o["op"] == "set_fields"]
    assert sets and sets[0]["fields"] == {"change_value": 12.0,
                                          "change_unit": "percent_yoy"}


def test_sparse_rerun_never_erases_richer_fact():
    existing = mk(level=100.0, change=12.0, series_unit="m_usd", created="x")
    res = plan_event_write([mk(level=100.0)], FakeGraph([existing]))
    assert res[0].outcome == "noop" and res[0].ops == []   # nulls never clobber


def test_non_signature_conflict_lww_with_log():
    existing = mk(level=100.0, quote="old words", series_unit="m_usd", created="x")
    res = plan_event_write([mk(level=100.0, quote="new words")], FakeGraph([existing]))
    assert res[0].outcome == "updated"
    sets = [o for o in res[0].ops if o["op"] == "set_fields"]
    logs = [o for o in res[0].ops if o["op"] == "log"]
    assert sets[0]["fields"] == {"quote": "new words"} and logs


# ---- OD-8 collision ladder ----

def test_conflict_with_one_sibling_creates_member_with_late_log():
    existing = mk(level=100.0, series_unit="m_usd", created="x")
    new = mk(level=999.0)
    res = plan_event_write([new], FakeGraph([existing]))
    assert res[0].outcome == "created_member"
    create = [o for o in res[0].ops if o["op"] == "create_fact"][0]
    h = signature_hash(list(signature(new)))
    assert create["id"] == f"{new['id']}|quote_hash={h}"
    assert "late_collision" not in create["props"]      # flags = logs/counters (OD-8 r9)
    assert any(o["op"] == "log" and o.get("event") == "late_collision"
               for o in res[0].ops)


def test_two_scenario_same_event_both_hashed_no_bare():
    a, b = mk(level=100.0, quote="scenario A"), mk(level=999.0, quote="scenario B")
    res = plan_event_write([a, b], FakeGraph())
    assert [r.outcome for r in res] == ["created_member", "created_member"]
    ids = [o["id"] for r in res for o in r.ops if o["op"] == "create_fact"]
    assert all("|quote_hash=" in i for i in ids) and len(set(ids)) == 2
    assert not any(o["op"] == "log" and o.get("event") == "late_collision"
                   for r in res for o in r.ops)        # in-batch, not late


def test_exact_match_among_multiple_siblings_merges():
    bare = mk(level=100.0, series_unit="m_usd", created="x")
    member = mk(level=999.0, series_unit="m_usd", created="x",
                id=bare["id"] + "|quote_hash=" + "f" * 64)
    res = plan_event_write([mk(level=999.0)], FakeGraph([bare, member]))
    assert res[0].outcome == "noop"                    # merged onto the exact member


def test_compatible_not_exact_with_multiple_siblings_parks():
    bare = mk(level=100.0, series_unit="m_usd", created="x")
    member = mk(level=999.0, series_unit="m_usd", created="x",
                id=bare["id"] + "|quote_hash=" + "f" * 64)
    res = plan_event_write([mk(level=100.0, change=12.0)], FakeGraph([bare, member]))
    assert res[0].outcome == "parked" and "ambiguous" in res[0].reason


def test_conflict_with_all_siblings_creates_member():
    bare = mk(level=100.0, series_unit="m_usd", created="x")
    member = mk(level=999.0, series_unit="m_usd", created="x",
                id=bare["id"] + "|quote_hash=" + "f" * 64)
    res = plan_event_write([mk(level=555.0)], FakeGraph([bare, member]))
    assert res[0].outcome == "created_member"


def test_two_inbatch_competitors_for_one_partial_sibling_park_both():
    partial = mk(level=100.0, series_unit="m_usd", created="x")
    a = mk(level=100.0, change=12.0, quote="A")
    b = mk(level=100.0, change=15.0, quote="B")
    res = plan_event_write([a, b], FakeGraph([partial]))
    assert [r.outcome for r in res] == ["parked", "parked"]


def test_unfused_compatible_inbatch_pair_parks_fail_closed():
    a = mk(level=100.0)
    b = mk(level=100.0, change=12.0)
    res = plan_event_write([a, b], FakeGraph())
    assert [r.outcome for r in res] == ["parked", "parked"]
    assert "fus" in res[0].reason                     # fusion should have merged these


def test_exact_inbatch_duplicates_dedupe_to_one_create():
    res = plan_event_write([mk(level=100.0), mk(level=100.0)], FakeGraph())
    outcomes = sorted(r.outcome for r in res)
    assert outcomes == ["created", "deduped"]


# ---- guards ----

def test_period_write_once_mismatch_hard_fails():
    graph = FakeGraph(periods={QP: {"start_date": "2025-07-02",
                                    "end_date": "2025-09-30"}})
    with pytest.raises(WriterError, match="write-once"):
        plan_event_write([mk(level=100.0)], graph)


def test_cross_event_batch_rejected():
    other = mk(level=100.0, id=f"du:OTHER-SRC:revenue:period={QP}")
    with pytest.raises(WriterError, match="one source event"):
        plan_event_write([mk(level=100.0), other], FakeGraph())


# ---- OD-10 series_unit ----

def test_series_unit_rules():
    assert stamp_series_unit(mk(level=100.0)) == "m_usd"
    assert stamp_series_unit(mk(change=12.0)) == "percent_yoy"   # delta-only: exact
    assert stamp_series_unit(mk()) is None                       # numberless
    w = mk(state="withdrawn", driver_name="revenue_guidance")
    assert stamp_series_unit(w, prior_series_unit="m_usd") == "m_usd"
    with pytest.raises(WriterError, match="fail.?closed"):
        stamp_series_unit(w)                                     # no clear prior


def test_permutation_exact_plus_conflict_each_decidable():
    # A matches the sibling exactly (merge); B conflicts with sibling AND A (member)
    sib = mk(level=100.0, series_unit="m_usd", created="x")
    a, b = mk(level=100.0), mk(level=999.0, quote="B")
    res = plan_event_write([a, b], FakeGraph([sib]))
    assert [r.outcome for r in res] == ["noop", "created_member"]


def test_permutation_both_conflict_everything_both_members():
    sib = mk(level=100.0, series_unit="m_usd", created="x")
    a, b = mk(level=555.0, quote="A"), mk(level=999.0, quote="B")
    res = plan_event_write([a, b], FakeGraph([sib]))
    assert [r.outcome for r in res] == ["created_member", "created_member"]


def test_permutation_single_filler_plus_conflicter():
    # A is the ONLY fill candidate (fills); B conflicts with sibling and A (member)
    sib = mk(level=100.0, series_unit="m_usd", created="x")
    a = mk(level=100.0, change=12.0, quote="A")
    b = mk(level=999.0, quote="B")
    res = plan_event_write([a, b], FakeGraph([sib]))
    assert [r.outcome for r in res] == ["filled", "created_member"]


def test_float_representation_dirt_never_mints_a_sibling():
    existing = mk(level=570.0, series_unit="m_usd", created="x")
    dirty = mk(level=570.0000000000001)
    res = plan_event_write([dirty], FakeGraph([existing]))
    assert res[0].outcome == "noop"                    # same real value, one fact


def test_series_unit_filled_when_a_compatible_fact_gains_a_level():
    target = mk(series_unit=None, created="x")         # numberless, unit-less
    new = mk(level=100.0)
    res = plan_event_write([new], FakeGraph([target]))
    sets = [o for o in res[0].ops if o["op"] == "set_fields"][0]["fields"]
    assert sets["series_unit"] == "m_usd"


def test_series_unit_conflict_on_fill_parks_for_repair():
    target = mk(change=12.0, series_unit="percent_yoy", created="x")
    new = mk(level=100.0, change=12.0)                 # compatible, but changes the axis
    res = plan_event_write([new], FakeGraph([target]))
    assert res[0].outcome == "parked" and "series_unit" in res[0].reason


def test_inbatch_duplicate_fusion_is_input_order_independent():
    a = mk(level=100.0, quote="alpha words")
    b = mk(level=100.0, quote="beta words")            # same signature, different quote
    res_ab = plan_event_write([dict(a), dict(b)], FakeGraph())
    res_ba = plan_event_write([dict(b), dict(a)], FakeGraph())
    kept_ab = [o["props"]["quote"] for r in res_ab for o in r.ops
               if o["op"] == "create_fact"]
    kept_ba = [o["props"]["quote"] for r in res_ba for o in r.ops
               if o["op"] == "create_fact"]
    assert kept_ab == kept_ba                          # order never picks the quote
    dedup_ops = [o for r in res_ab + res_ba for o in r.ops if o["op"] == "log"]
    assert dedup_ops                                    # dropped variant is logged


def test_period_op_carries_u_id():
    res = plan_event_write([mk(level=100.0)], FakeGraph())
    op = [o for o in res[0].ops if o["op"] == "merge_period"][0]
    assert op["u_id"] == QP == op["id"]


def test_series_unit_prior_must_be_exactly_one():
    w = mk(state="withdrawn", driver_name="revenue_guidance",
           id=f"du:{SRC}:revenue_guidance:period={QP}")
    res = plan_event_write([w], FakeGraph(),
                           prior_series_units={w["id"]: ["m_usd", "usd"]})
    assert res[0].outcome == "parked" and "exactly one" in res[0].reason
    res = plan_event_write([w], FakeGraph(), prior_series_units={w["id"]: ["m_usd"]})
    assert res[0].outcome == "created"


def test_text_signature_drift_never_mints_a_sibling():
    g_id = f"du:{SRC}:revenue_guidance:period={QP}"
    existing = mk(level=None, id=g_id, driver_name="revenue_guidance",
                  state="unknown", value_text="Similar to  Last Year",
                  series_unit=None, created="x", company_confirmed=True)
    new = mk(level=None, id=g_id, driver_name="revenue_guidance", state="unknown",
             value_text="similar to last year", company_confirmed=True)
    res = plan_event_write([new], FakeGraph([existing]))
    assert res[0].outcome in ("noop", "updated")     # equal canonically — never a member


def test_stored_node_is_exactly_the_24_fields_members_included():
    res = plan_event_write([mk(level=100.0)], FakeGraph())
    props = [o for o in res[0].ops if o["op"] == "create_fact"][0]["props"]
    assert len(props) == 24 and "driver_name" not in props
    a, b = mk(level=100.0, quote="A"), mk(level=999.0, quote="B")
    member_props = [o for r in plan_event_write([a, b], FakeGraph())
                    for o in r.ops if o["op"] == "create_fact"][0]["props"]
    assert set(member_props) == set(props)              # zero new stored artifacts


def test_withdrawal_without_prior_parks_in_plan():
    w = mk(state="withdrawn", driver_name="revenue_guidance",
           id=f"du:{SRC}:revenue_guidance:period={QP}")
    res = plan_event_write([w], FakeGraph())
    assert res[0].outcome == "parked" and "series_unit" in res[0].reason
