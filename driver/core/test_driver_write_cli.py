"""S3.5 CLI — §11.4 v3.6 end-to-end against the FakeStore (same read surface the real
adapter must expose). ZERO Neo4j. Dry-run default; the real-write path is exercised
through the fake transaction; ENABLE_DRIVER_WRITES stays unset except where a test
sets it explicitly and restores it."""
import json
import os
from decimal import Decimal

import pytest

from driver.core.driver_write_cli import CLI_CODES, run_event
from driver.core.driver_writer import FakeGraph
from driver.core.prepared_fact import RunInputV1, PreparedFactV1

SRC = "0000320193-26-000042"


class FakeStore(FakeGraph):
    """FakeGraph + the source/driver/tx surface the CLI drives."""

    def __init__(self, facts=None, periods=None, *, source=..., companies=None,
                 drivers=None, fail_apply=False, prior_units=None,
                 slice_menu=None, xbrl_facts=None):
        super().__init__(facts, periods)
        self.prior_units = prior_units or {}
        self.slice_menu = slice_menu or {"xbrl_members": [], "used_scopes": []}
        self.xbrl_facts = xbrl_facts or {}         # concept -> verification rows
        self.source = ({"date": "2026-07-01T12:00:00", "source_type": "8k",
                        "ticker": None, "fye_month": 9} if source is ... else source)
        self.companies = ["AAPL"] if companies is None else companies
        self.drivers = drivers if drivers is not None else {
            "revenue": {"name": "revenue", "fact_type": "metric"},
            "revenue_surprise": {"name": "revenue_surprise", "fact_type": "surprise"},
        }
        self.fail_apply = fail_apply
        self.applied = []

    def get_source(self, source_id):
        return self.source

    def get_source_companies(self, source_id):
        return self.companies

    def get_driver(self, name):
        return self.drivers.get(name)

    def get_prior_guide_units(self, fact):
        return self.prior_units.get(fact["id"], [])

    def get_company_slice_menu(self, source_id, date):
        return self.slice_menu

    def get_xbrl_fact_dimensions(self, source_id, concept):
        return self.xbrl_facts.get(concept, [])

    def transaction(self):
        store = self

        class _Tx:
            """The tx object carries the SAME read surface — in-tx reads and the
            final plan never touch the bare store (one consistent snapshot)."""
            get_source = staticmethod(store.get_source)
            get_source_companies = staticmethod(store.get_source_companies)
            get_driver = staticmethod(store.get_driver)
            get_sibling_facts = staticmethod(store.get_sibling_facts)
            get_period = staticmethod(store.get_period)
            get_prior_guide_units = staticmethod(store.get_prior_guide_units)

            def __enter__(self):
                self.buf = []
                return self

            def apply(self, op):
                if store.fail_apply:
                    raise RuntimeError("disk full")
                self.buf.append(op)

            def __exit__(self, exc_type, *a):
                if exc_type is None:                 # commit
                    for op in self.buf:
                        store.applied.append(op)
                        if op["op"] == "create_fact":
                            store.facts[op["id"]] = dict(op["props"])
                return False                          # rollback = buffer dropped
        return _Tx()


def fact(**over):
    d = {"driver_name": "revenue", "driver_state": "reported",
         "quote": "Q3 revenue was $100 million",
         "level_low": Decimal("100"), "level_high": Decimal("100"),
         "level_unit_raw": "USD millions", "level_shape_hint": "point",
         "period_start_date": "2025-06-29", "period_end_date": "2025-09-27",
         "fiscal_year": 2025, "fiscal_quarter": 3, "time_type": "duration"}
    d.update(over)
    return d


def run(tmp_path, facts, store=None, **kw):
    ri = RunInputV1.from_dict({"source_id": SRC, "facts": facts})
    return run_event(ri, store=store or FakeStore(), audit_dir=str(tmp_path), **kw)


def audit_docs(tmp_path):
    return [json.load(open(os.path.join(tmp_path, p)))
            for p in sorted(os.listdir(tmp_path)) if p.endswith(".json")]


# ---- gates ----

def test_source_missing_run_fails_items_rejected(tmp_path):
    out = run(tmp_path, [fact()], FakeStore(source=None))
    assert out["status"] == "failed" and out["code"] == "SOURCE_MISSING"
    assert out["items"][0]["decision"] == "rejected"
    assert out["items"][0]["codes"] == ["SOURCE_MISSING"]
    assert audit_docs(tmp_path)[0]["state"] == "failed"


def test_ambiguous_company_parks_all(tmp_path):
    out = run(tmp_path, [fact(), fact()], FakeStore(companies=["AAPL", "AAPL2"]))
    assert all(i["decision"] == "parked"
               and i["codes"] == ["SOURCE_COMPANY_AMBIGUOUS"] for i in out["items"])


def test_untyped_driver_parks(tmp_path):
    out = run(tmp_path, [fact(driver_name="mystery")])
    assert out["items"][0]["codes"] == ["DRIVER_NOT_READY"]


# ---- dry-run default ----

def test_dry_run_plans_written_but_mutates_nothing(tmp_path):
    store = FakeStore()
    out = run(tmp_path, [fact()], store)
    assert out["status"] == "dry_run"
    item = out["items"][0]
    assert item["decision"] == "written" and item["fact_id"].startswith(f"du:{SRC}:revenue:")
    assert store.facts == {} and store.applied == []
    doc = audit_docs(tmp_path)[0]
    assert doc["state"] == "dry_run" and doc["plans"][0]["outcome"] == "created"


def test_date_is_source_time_and_created_unstamped_in_dry_run(tmp_path):
    out = run(tmp_path, [fact()])
    doc = audit_docs(tmp_path)[0]
    props = next(o for o in doc["plans"][0]["ops"]
                 if o["op"] == "create_fact")["props"]
    assert props["date"] == "2026-07-01T12:00:00"      # the STORED source's time
    assert props["created"] == "__now__"               # stamped only at commit


# ---- member-ref law (step 7: fence removed) / fusion / validation ----

GEO_AXIS = "srt:StatementGeographicalAxis"
EU_DIM = {"axis": GEO_AXIS, "member": "srt:EuropeMember", "label": "Europe"}
EU_REF = {"axis": GEO_AXIS, "member": "srt:EuropeMember",
          "slice_part": "geography:europe"}


def xrow(dims, ptype="duration", start="2025-06-29", end="2025-09-28"):
    # a verification row for the default fact() claim: stored end is EXCLUSIVE
    # (claimed 2025-09-27 inclusive -> stored 2025-09-28)
    return {"period_type": ptype, "start_date": start, "end_date": end,
            "dims": [dict(d) for d in dims]}


def eu_store(**kw):
    return FakeStore(xbrl_facts={"us-gaap:Revenues": [xrow([EU_DIM])]}, **kw)


def test_member_refs_flow_through_and_op_identity_carries_axis(tmp_path):
    out = run(tmp_path, [fact(slice_parts=[("geography", "Europe")],
                              member_refs=[dict(EU_REF)],
                              xbrl_concept_raw="us-gaap:Revenues")], eu_store())
    assert out["items"][0]["decision"] == "written"        # fence is GONE
    doc = audit_docs(tmp_path)[0]
    edges = [o for o in doc["plans"][0]["ops"] if o.get("type") == "MAPS_TO_MEMBER"]
    assert edges == [{"op": "edge", "type": "MAPS_TO_MEMBER",
                      "from": out["items"][0]["fact_id"], "to": "srt:EuropeMember",
                      "axis": "srt:StatementGeographicalAxis",
                      "props": {"slice_part": "geography:europe"}}]


def test_member_ref_with_no_matching_fact_parks_unverifiable(tmp_path):
    # refs are NEVER trusted — the current filing has NO fact with this exact
    # concept + period + dimension set, so the claim parks fail-closed
    out = run(tmp_path, [fact(slice_parts=[("geography", "Europe")],
                              member_refs=[dict(EU_REF)],
                              xbrl_concept_raw="us-gaap:Revenues")])
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["MEMBER_LINK_INVALID"]
    assert "unverifiable" in out["items"][0]["detail"]


def test_member_elsewhere_in_filing_is_insufficient(tmp_path):
    # the member EXISTS in the filing — but on a different period's fact; the
    # exact-fact match must fail (a member seen "somewhere" proves nothing)
    store = FakeStore(xbrl_facts={"us-gaap:Revenues": [
        xrow([EU_DIM], start="2024-06-30", end="2024-09-29")]})
    out = run(tmp_path, [fact(slice_parts=[("geography", "Europe")],
                              member_refs=[dict(EU_REF)],
                              xbrl_concept_raw="us-gaap:Revenues")], store)
    assert out["items"][0]["codes"] == ["MEMBER_LINK_INVALID"]
    assert "unverifiable" in out["items"][0]["detail"]


def test_incomplete_dimension_set_never_matches(tmp_path):
    # the filing's fact carries TWO dimensions; claiming only one of them is a
    # DIFFERENT population — the complete-set equality must fail it
    two_dim = xrow([EU_DIM, {"axis": "us-gaap:StatementBusinessSegmentsAxis",
                             "member": "acme:CoreMember", "label": "Core"}])
    store = FakeStore(xbrl_facts={"us-gaap:Revenues": [two_dim]})
    out = run(tmp_path, [fact(slice_parts=[("geography", "Europe")],
                              member_refs=[dict(EU_REF)],
                              xbrl_concept_raw="us-gaap:Revenues")], store)
    assert out["items"][0]["codes"] == ["MEMBER_LINK_INVALID"]
    assert "unverifiable" in out["items"][0]["detail"]


def test_false_verified_empty_dims_claim_parks(tmp_path):
    # dimensions=[] is a CLAIM: "this concept+period fact has no dimensions" —
    # here every matching-period fact HAS dimensions, so the [] claim is false
    store = FakeStore(xbrl_facts={"us-gaap:Revenues": [xrow([EU_DIM])]})
    out = run(tmp_path, [fact(member_refs=[],
                              xbrl_concept_raw="us-gaap:Revenues")], store)
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["MEMBER_LINK_INVALID"]
    assert "unverifiable" in out["items"][0]["detail"]


def test_true_verified_empty_dims_claim_writes(tmp_path):
    store = FakeStore(xbrl_facts={"us-gaap:Revenues": [xrow([])]})
    out = run(tmp_path, [fact(member_refs=[],
                              xbrl_concept_raw="us-gaap:Revenues")], store)
    assert out["items"][0]["decision"] == "written"


def test_member_ref_supporting_no_fact_slice_parks_invalid(tmp_path):
    # a VERIFIED link must still support one of the fact's OWN slice tokens
    # (FINAL_DESIGN:178) — this fact declares no slices at all
    out = run(tmp_path, [fact(member_refs=[dict(EU_REF)],
                              xbrl_concept_raw="us-gaap:Revenues")], eu_store())
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["MEMBER_LINK_INVALID"]
    assert "supports no slice token" in out["items"][0]["detail"]


def test_menu_is_fetched_pit_at_source_time(tmp_path):
    seen = []

    class Capture(FakeStore):
        def get_company_slice_menu(self, source_id, date):
            seen.append((source_id, date))
            return super().get_company_slice_menu(source_id, date)
    run(tmp_path, [fact(slice_parts=[("geography", "Europe")],
                        member_refs=[dict(EU_REF)],
                        xbrl_concept_raw="us-gaap:Revenues")], Capture())
    assert seen == [(SRC, "2026-07-01T12:00:00")]  # the STORED source's time, once


def test_fragments_fuse_and_share_one_fact_id(tmp_path):
    out = run(tmp_path, [
        fact(),
        fact(level_low=None, level_high=None, level_unit_raw=None,
             change_value=Decimal("12"), change_unit_raw="%",
             quote="revenue rose 12% year-over-year"),
    ])
    a, b = out["items"]
    assert a["decision"] == "written" and a["fact_id"] == b["fact_id"]


def test_fusion_ambiguous_parks_group(tmp_path):
    out = run(tmp_path, [
        fact(),
        fact(level_low=None, level_high=None, level_unit_raw=None,
             change_value=Decimal("12"), change_unit_raw="%"),
        fact(level_low=Decimal("101"), level_high=Decimal("101")),
    ])
    assert all(i["codes"] == ["FUSION_AMBIGUOUS"] for i in out["items"])


def test_reject_beats_park(tmp_path):
    # consensus baseline on a metric = REJECT even when park-class issues coexist
    out = run(tmp_path, [fact(comparison_low=Decimal("90"),
                              comparison_high=Decimal("90"),
                              comparison_baseline="consensus")])
    assert out["items"][0]["decision"] == "rejected"


# ---- surprise post-plan rule ----

def surprise_pair(home_level="100"):
    home = fact(level_low=Decimal(home_level), level_high=Decimal(home_level))
    s = fact(driver_name="revenue_surprise", driver_state="beat",
             quote="revenue of $100M beat consensus of $90M",
             surprise_basis_hint="actual", comparison_baseline="consensus",
             comparison_low=Decimal("90"), comparison_high=Decimal("90"),
             comparison_shape_hint="point")
    return [home, s]


def test_surprise_writes_with_accepted_home(tmp_path):
    out = run(tmp_path, surprise_pair())
    assert [i["decision"] for i in out["items"]] == ["written", "written"]


def test_surprise_parks_when_home_plan_not_accepted(tmp_path):
    home, s = surprise_pair()
    home["level_low"] = home["level_high"] = Decimal("1e70")  # NOT_STORABLE park
    s["level_low"] = s["level_high"] = Decimal("1e70")
    out = run(tmp_path, [home, s])
    assert out["items"][0]["codes"] == ["NOT_STORABLE"]
    assert out["items"][1]["decision"] in ("parked",)


# ---- real-write path (fake tx; env gate set + restored) ----

def enabled_run(tmp_path, facts, store, **kw):
    os.environ["ENABLE_DRIVER_WRITES"] = "1"
    try:
        return run(tmp_path, facts, store, enable_writes=True,
                   now_fn=lambda: "2026-07-17T20:00:00.000000", **kw)
    finally:
        del os.environ["ENABLE_DRIVER_WRITES"]


def test_enabled_run_commits_and_stamps_created_once(tmp_path):
    store = FakeStore()
    out = enabled_run(tmp_path, [fact()], store)
    assert out["status"] == "committed"
    created = [f for f in store.facts.values()]
    assert len(created) == 1
    assert created[0]["created"] == "2026-07-17T20:00:00.000000"
    assert audit_docs(tmp_path)[0]["state"] == "committed"


def test_truthful_rollback_execution_failed(tmp_path):
    store = FakeStore(fail_apply=True)
    out = enabled_run(tmp_path, [fact()], store)
    assert out["status"] == "failed" and out["code"] == "EXECUTION_FAILED"
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["EXECUTION_FAILED"]
    assert store.facts == {}                       # nothing written, nothing claimed
    assert audit_docs(tmp_path)[0]["state"] == "failed"


def test_write_gate_env_required(tmp_path):
    out = run(tmp_path, [fact()], enable_writes=True)   # env NOT set
    assert out["status"] == "failed" and out["code"] == "WRITE_GATE"


def test_writer_busy_flock(tmp_path):
    import fcntl
    lock_path = str(tmp_path / "writer.lock")
    holder = open(lock_path, "w")
    fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        out = enabled_run(tmp_path, [fact()], FakeStore(), lock_path=lock_path)
        assert out["status"] == "failed" and out["code"] == "WRITER_BUSY"
    finally:
        holder.close()


# ---- audit + dry-run fidelity + codes ----

def test_audit_file_unique_and_write_ahead(tmp_path):
    run(tmp_path, [fact()], now_fn=lambda: "2026-07-17T20:00:00.000000")
    with pytest.raises(FileExistsError):           # same run_id may never overwrite
        run(tmp_path, [fact()], now_fn=lambda: "2026-07-17T20:00:00.000000")
    doc = audit_docs(tmp_path)[0]
    assert doc["input"]["source_id"] == SRC and doc["results"]


def test_dry_run_fidelity_same_plan_as_real(tmp_path):
    d1, d2 = tmp_path / "a", tmp_path / "b"
    d1.mkdir(), d2.mkdir()
    run(d1, [fact()], FakeStore(), now_fn=lambda: "t1")
    enabled_run(d2, [fact()], FakeStore())
    p1, p2 = audit_docs(d1)[0]["plans"], audit_docs(d2)[0]["plans"]
    assert p1 == p2                                 # SAME reads, SAME final planning


def test_every_emitting_branch_carries_a_code(tmp_path):
    """The §5 one-test rule: every non-written outcome carries an explicit code and
    the CLI-owned registry is fully reachable (planner/validator codes ride along)."""
    emitted = set()
    def collect(out):
        for i in out["items"]:
            if i["decision"] in ("parked", "rejected"):
                assert i["codes"], f"codeless {i}"
                emitted.update(i["codes"])
        if out.get("code"):
            emitted.add(out["code"])
    collect(run(tmp_path / "1", [fact()], FakeStore(source=None)))
    collect(run(tmp_path / "2", [fact()], FakeStore(companies=[])))
    collect(run(tmp_path / "3", [fact(driver_name="mystery")]))
    collect(run(tmp_path / "4", [fact(surprise_basis_hint="guidance",
                                      comparison_baseline="previous_guidance")]))
    collect(run(tmp_path / "5", [fact(period_start_date="2025-01-01",
                                      period_end_date="2025-06-30")]))
    collect(run(tmp_path / "6", [fact(level_unit_raw="fortnights")]))
    collect(run(tmp_path / "7", [fact(member_refs=[
        {"axis": "a", "member": "m", "slice_part": "s:p"}],
        xbrl_concept_raw="c")]))
    collect(run(tmp_path / "8", [fact(driver_name="x")],
                FakeStore(drivers={"x": {"name": "x", "fact_type": "metric"}})))
    collect(run(tmp_path / "9", [fact(), fact(level_low=None, level_high=None,
                                              level_unit_raw=None,
                                              change_value=Decimal("12"),
                                              change_unit_raw="%"),
                                 fact(level_low=Decimal("101"),
                                      level_high=Decimal("101"))]))
    h, s = surprise_pair()
    h["level_low"] = h["level_high"] = Decimal("1e70")
    s["level_low"] = s["level_high"] = Decimal("1e70")
    collect(run(tmp_path / "10", [h, s]))
    collect(enabled_run(tmp_path / "11", [fact()], FakeStore(fail_apply=True)))
    collect(run(tmp_path / "12", [fact()], enable_writes=True))
    collect(run(tmp_path / "13", [fact(measurement_raw_spans=["—"])]))
    must_reach = {"SOURCE_MISSING", "SOURCE_COMPANY_AMBIGUOUS", "DRIVER_NOT_READY",
                  "SURPRISE_COMPOSE", "PERIOD_UNRESOLVED", "MEMBER_LINK_INVALID",
                  "FUSION_AMBIGUOUS", "NOT_STORABLE", "EXECUTION_FAILED",
                  "WRITE_GATE", "EMPTY_LABEL"}
    assert must_reach <= emitted, must_reach - emitted
    assert CLI_CODES - {"UNIT_UNRESOLVED", "ID_LAW", "SURPRISE_HOME_NOT_ACCEPTED",
                        "WRITER_BUSY", "F7", "INTERNAL_UNTRACKED"} <= emitted


# ---- review-round regressions (each reproduced first) ----

def test_writer_busy_parks_never_written(tmp_path):
    import fcntl
    lock_path = str(tmp_path / "writer.lock")
    holder = open(lock_path, "w")
    fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        out = enabled_run(tmp_path, [fact()], FakeStore(), lock_path=lock_path)
        assert out["code"] == "WRITER_BUSY"
        assert out["items"][0]["decision"] == "parked"        # was: falsely "written"
        assert out["items"][0]["codes"] == ["WRITER_BUSY"]
    finally:
        holder.close()


def test_lock_is_mandatory_default_lock_used(tmp_path):
    out = enabled_run(tmp_path, [fact()], FakeStore())         # no lock_path given
    assert out["status"] == "committed"
    assert os.path.exists(tmp_path / "writer.lock")            # default lock engaged


def test_future_period_actual_surprise_rejected_f7(tmp_path):
    h, s = surprise_pair()
    for f in (h, s):                                           # 91d quarter ending
        f.update(period_start_date="2026-09-28",               # after the source time
                 period_end_date="2026-12-27", fiscal_quarter=1)
    out = run(tmp_path, [h, s])
    assert out["items"][1]["decision"] == "rejected"
    assert out["items"][1]["codes"] == ["F7"]


def test_wordless_beat_inside_consensus_corrected_to_in_line(tmp_path):
    h, s = surprise_pair()
    s.update(has_favorability_wording=False, comparison_low=Decimal("90"),
             comparison_high=Decimal("110"), comparison_shape_hint="range")
    out = run(tmp_path, [h, s])
    doc = audit_docs(tmp_path)[0]
    states = [o["props"]["driver_state"] for p in doc["plans"] for o in p["ops"]
              if o["op"] == "create_fact" and "surprise=" in o["id"]]
    assert states == ["in_line"]                               # OD-21 inline correction


def test_audit_prepared_carries_plans_logs_and_exact_bytes(tmp_path):
    doc_in = {"source_id": SRC, "facts": [
        fact(level_low=100, level_high=100),
        fact(level_low=None, level_high=None, level_unit_raw=None,
             change_value=12, change_unit_raw="%",
             level_shape_hint=None, quote="rose 12% year-over-year")]}
    raw = json.dumps(doc_in).encode()              # the REAL bytes, oddly spaced
    ri = RunInputV1.from_dict(json.loads(raw.decode(), parse_float=Decimal))
    from driver.core.driver_write_cli import run_event
    run_event(ri, store=FakeStore(), audit_dir=str(tmp_path),
              input_bytes=raw)
    doc = audit_docs(tmp_path)[0]
    assert doc["input_bytes"] == raw.decode()                  # exact bytes preserved
    assert doc["plans"] and doc["fusion_logs"] is not None     # pre-mutation content


def test_in_tx_final_replan_catches_stale_state(tmp_path):
    class ShiftyStore(FakeStore):
        def transaction(self):
            # a sibling appears between provisional planning and the tx
            self.facts["du:%s:revenue:period=gp_2025-06-29_2025-09-27" % SRC] = {
                "id": "du:%s:revenue:period=gp_2025-06-29_2025-09-27" % SRC,
                "level_low": Decimal("999"), "level_high": Decimal("999"),
                "level_unit": "m_usd", "change_value": None, "change_unit": None,
                "comparison_low": None, "comparison_high": None,
                "comparison_baseline": None, "value_text": None, "conditions": None,
                "series_unit": "m_usd"}
            return super().transaction()
    out = enabled_run(tmp_path, [fact()], ShiftyStore())
    assert out["status"] == "failed" and out["code"] == "EXECUTION_FAILED"
    assert out["items"][0]["decision"] == "parked"             # stale plan never runs


# ---- review-round-2 regressions (each reproduced first) ----

def test_wordless_beat_without_polarity_proof_becomes_unknown(tmp_path):
    h, s = surprise_pair()
    s.update(has_favorability_wording=False)       # beat OUTSIDE range, no proof
    out = run(tmp_path, [h, s])
    doc = audit_docs(tmp_path)[0]
    states = [o["props"]["driver_state"] for p in doc["plans"] for o in p["ops"]
              if o["op"] == "create_fact" and "surprise=" in o["id"]]
    assert states == ["unknown"]                   # no proof, no favorability call


def test_wordless_beat_with_valid_proof_survives(tmp_path):
    h, s = surprise_pair()
    s.update(has_favorability_wording=False,
             polarity_proof={"polarity": "higher_favorable",
                             "basis": "metric_meaning",
                             "evidence": "revenue higher is favorable",
                             "sentence": "revenue of $100M vs $90M consensus"})
    out = run(tmp_path, [h, s])
    doc = audit_docs(tmp_path)[0]
    states = [o["props"]["driver_state"] for p in doc["plans"] for o in p["ops"]
              if o["op"] == "create_fact" and "surprise=" in o["id"]]
    assert states == ["beat"]


def test_measurement_case_normalized_once_home_match_holds(tmp_path):
    h, s = surprise_pair()
    h["measurement_raw_spans"] = ["Adjusted"]      # producer wording differs by case
    s["measurement_raw_spans"] = ["adjusted"]
    out = run(tmp_path, [h, s])
    assert [i["decision"] for i in out["items"]] == ["written", "written"]


def test_audit_records_the_final_executed_plan(tmp_path):
    out = enabled_run(tmp_path, [fact()], FakeStore())
    assert out["status"] == "committed"
    doc = audit_docs(tmp_path)[0]
    assert doc["final_plans"] and doc["final_plans"][0]["outcome"] == "created"


def test_log_ops_never_reach_the_graph(tmp_path):
    existing = {"id": f"du:{SRC}:revenue:period=gp_2025-06-29_2025-09-27",
                "level_low": Decimal("100"), "level_high": Decimal("100"),
                "level_unit": "m_usd", "change_value": None, "change_unit": None,
                "comparison_low": None, "comparison_high": None,
                "comparison_baseline": None, "value_text": None, "conditions": None,
                "series_unit": "m_usd", "driver_state": "reported", "quote": "old",
                "date": "2026-06-01T00:00:00", "source_type": "8k",
                "company_confirmed": None, "xbrl_qname": None, "fiscal_year": 2025,
                "fiscal_quarter": 3, "period_scope": "quarter",
                "time_type": "duration", "fact_scope": "period=gp_2025-06-29_2025-09-27"}
    store = FakeStore(facts=[existing])
    out = enabled_run(tmp_path, [fact(change_value=Decimal("12"),
                                      change_unit_raw="%",
                                      quote="new wording")], store)
    assert out["status"] == "committed"
    assert all(op["op"] != "log" for op in store.applied)   # audit-only, never graph


def test_input_bytes_must_match_parsed_input(tmp_path):
    ri = RunInputV1.from_dict({"source_id": SRC, "facts": [fact()]})
    from driver.core.driver_write_cli import run_event
    with pytest.raises(ValueError, match="input_bytes"):
        run_event(ri, store=FakeStore(), audit_dir=str(tmp_path),
                  input_bytes=b'{"source_id": "other", "facts": []}')


def test_fusion_hint_survivor_is_order_independent():
    from driver.core.driver_fusion import fuse_event

    def frag(idx, **over):
        f = {"driver_name": "revenue", "driver_state": "reported", "quote": "q",
             "date": "2026-07-01", "source_type": "8k", "company_confirmed": None,
             "level_low": None, "level_high": None, "level_unit": None,
             "change_value": None, "change_unit": None, "comparison_low": None,
             "comparison_high": None, "comparison_baseline": None,
             "value_text": None, "conditions": None, "level_shape_hint": None}
        f.update(over)
        return (idx, "k", f)
    a = dict(level_low=Decimal("5"), level_high=Decimal("5"), level_shape_hint="point")
    b = dict(change_value=Decimal("2"), change_unit="percent_yoy",
             level_shape_hint=None)                # None fills; conflicts never fuse
    f1, _ = fuse_event([frag(0, **a), frag(1, **b)])
    f2, _ = fuse_event([frag(0, **b), frag(1, **a)])
    assert f1[0].fact["level_shape_hint"] == f2[0].fact["level_shape_hint"] == "point"
    conf1, p1 = fuse_event([frag(0, company_confirmed=True, **a),
                            frag(1, company_confirmed=False, **b)])
    assert len(conf1) == 2 and p1 == []            # True-vs-False never fuses


# ---- final correction round (each reproduced first) ----

def test_empty_labels_park_never_crash_or_reject(tmp_path):
    out = run(tmp_path / "a", [fact(slice_parts=[["product", "—"]])])
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["EMPTY_LABEL"]     # was: raw IdLawError crash
    out = run(tmp_path / "b", [fact(measurement_raw_spans=["—"])])
    assert out["items"][0]["decision"] == "parked"         # was: rejected ID_LAW
    assert out["items"][0]["codes"] == ["EMPTY_LABEL"]


def test_conflicting_shape_hints_never_fuse():
    from driver.core.driver_fusion import fuse_event
    base = {"driver_name": "revenue", "driver_state": "reported", "quote": "q",
            "date": "2026-07-01", "source_type": "8k", "company_confirmed": None,
            "level_low": None, "level_high": None, "level_unit": None,
            "change_value": None, "change_unit": None, "comparison_low": None,
            "comparison_high": None, "comparison_baseline": None,
            "value_text": None, "conditions": None}
    a = dict(base, level_low=Decimal("5"), level_high=Decimal("5"),
             level_shape_hint="point")
    b = dict(base, change_value=Decimal("2"), change_unit="percent_yoy",
             level_shape_hint="range")
    fused, parked = fuse_event([(0, "k", a), (1, "k", b)])
    assert parked == [] and len(fused) == 2                # fragments stand separately


def test_writer_busy_preserves_planner_parks(tmp_path):
    import fcntl
    lock_path = str(tmp_path / "writer.lock")
    holder = open(lock_path, "w")
    fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
    store = FakeStore(drivers={
        "revenue": {"name": "revenue", "fact_type": "metric"},
        "opex": {"name": "opex", "fact_type": "metric"}})
    try:
        out = enabled_run(tmp_path, [
            fact(),
            fact(driver_name="opex", level_low=Decimal("1e70"),
                 level_high=Decimal("1e70"))], store, lock_path=lock_path)
        assert out["items"][0]["codes"] == ["WRITER_BUSY"]
        assert out["items"][1]["codes"] == ["NOT_STORABLE"]  # park SURVIVES the busy
    finally:
        holder.close()


def test_write_gate_items_get_write_gate_code(tmp_path):
    out = run(tmp_path, [fact()], enable_writes=True)      # env NOT set
    assert out["code"] == "WRITE_GATE"
    assert out["items"][0]["codes"] == ["WRITE_GATE"]      # was: EXECUTION_FAILED


def test_inconsistent_polarity_proof_becomes_unknown(tmp_path):
    h, s = surprise_pair()
    s.update(has_favorability_wording=False,               # beat + above needs
             polarity_proof={"polarity": "lower_favorable",  # higher_favorable
                             "basis": "metric_meaning",
                             "evidence": "e", "sentence": "s"})
    out = run(tmp_path, [h, s])
    doc = audit_docs(tmp_path)[0]
    states = [o["props"]["driver_state"] for p in doc["plans"] for o in p["ops"]
              if o["op"] == "create_fact" and "surprise=" in o["id"]]
    assert states == ["unknown"]


def test_audit_final_ops_stamped_and_exactly_executed(tmp_path):
    store = FakeStore()
    out = enabled_run(tmp_path, [fact()], store)
    assert out["status"] == "committed"
    doc = audit_docs(tmp_path)[0]
    created = [o["props"]["created"] for o in doc["final_ops"]
               if o["op"] == "create_fact"]
    assert created == ["2026-07-17T20:00:00.000000"]       # REAL timestamp, pre-write
    assert doc["final_ops"] == [json.loads(json.dumps(op, default=str))
                                for op in store.applied]   # those SAME ops executed


def guidance_withdrawal():
    return fact(driver_name="revenue_guidance", driver_state="withdrawn",
                quote="withdrawing our FY2026 revenue guidance",
                level_low=None, level_high=None, level_unit_raw=None,
                level_shape_hint=None, company_confirmed=True,
                period_start_date=None, period_end_date=None,
                fiscal_year=2026, fiscal_quarter=None)


def test_numberless_withdrawal_copies_exactly_one_prior_unit(tmp_path):
    gid = f"du:{SRC}:revenue_guidance:period=gp_2025-10-01_2026-09-30"
    drivers = {"revenue_guidance": {"name": "revenue_guidance",
                                    "fact_type": "guidance"}}
    ok = run(tmp_path / "one", [guidance_withdrawal()],
             FakeStore(drivers=drivers, prior_units={gid: ["m_usd"]}))
    assert ok["items"][0]["decision"] == "written"
    two = run(tmp_path / "two", [guidance_withdrawal()],
              FakeStore(drivers=drivers, prior_units={gid: ["m_usd", "usd"]}))
    assert two["items"][0]["decision"] == "parked"
    assert two["items"][0]["codes"] == ["SERIES_UNIT"]     # zero/multiple still park


# ---- round-4 regressions (each reproduced first) ----

def test_open_bound_positions_are_definitive():
    from driver.core.driver_validators import surprise_position
    D = Decimal
    assert surprise_position(D("80"), D("80"), D("90"), None) == "below"
    assert surprise_position(D("95"), D("95"), D("90"), None) == "above"
    assert surprise_position(D("120"), D("120"), None, D("110")) == "above"
    assert surprise_position(D("100"), D("100"), None, D("110")) == "below"
    assert surprise_position(D("90"), D("90"), D("90"), None) == "at_floor"


def test_priors_queried_only_for_numberless_withdrawn_reaffirmed(tmp_path):
    calls = []

    class CountingStore(FakeStore):
        def get_prior_guide_units(self, bare_id):
            calls.append(bare_id)
            return super().get_prior_guide_units(bare_id)
    out = run(tmp_path, [fact()], CountingStore())      # value-bearing metric
    assert out["items"][0]["decision"] == "written"
    assert calls == []                                  # never queried


def test_in_tx_source_change_aborts(tmp_path):
    class ShiftySrc(FakeStore):
        def transaction(self):
            self.source = dict(self.source, date="2026-07-02T00:00:00")
            return super().transaction()
    out = enabled_run(tmp_path, [fact()], ShiftySrc())
    assert out["status"] == "failed" and out["code"] == "EXECUTION_FAILED"
    assert out["items"][0]["decision"] == "parked"


def test_fye_always_from_stored_source_no_override(tmp_path):
    import inspect
    from driver.core.driver_write_cli import run_event as re_fn
    assert "fye_month" not in inspect.signature(re_fn).parameters
    # December-FYE source shifts the pure-math annual window accordingly
    store = FakeStore(source={"date": "2026-07-01T12:00:00", "source_type": "8k",
                              "ticker": None, "fye_month": 12},
                      drivers={"revenue_guidance": {"name": "revenue_guidance",
                                                    "fact_type": "guidance"}},
                      prior_units={f"du:{SRC}:revenue_guidance:"
                                   f"period=gp_2026-01-01_2026-12-31": ["m_usd"]})
    out = run(tmp_path, [guidance_withdrawal()], store)
    assert out["items"][0]["decision"] == "written"
    assert "gp_2026-01-01_2026-12-31" in out["items"][0]["fact_id"]


# ---- round-5: the prior-guidance lookup must be company/time/series-safe ----

def _mk_neo4j_store_with_fake_read(rows, captured):
    from driver.core.driver_neo4j_adapter import Neo4jStore
    store = Neo4jStore.__new__(Neo4jStore)         # no connection — _read is faked

    def fake_read(query, **params):
        captured.append((query, params))
        return rows
    store._read = fake_read
    return store


PRIOR_FACT = {"id": f"du:{SRC}:revenue_guidance:period=gp_2026-01-01_2026-12-31",
              "driver_name": "revenue_guidance",
              "fact_scope": "period=gp_2026-01-01_2026-12-31",
              "date": "2026-07-01T12:00:00-04:00", "time_type": "duration",
              "period_scope": "annual"}


def test_prior_query_is_company_time_and_series_scoped():
    captured = []
    store = _mk_neo4j_store_with_fake_read([], captured)
    assert store.get_prior_guide_units(PRIOR_FACT) == []
    query, params = captured[0]
    assert params["src"] == SRC                    # company via the CURRENT source
    assert params["scope"] == "period=gp_2026-01-01_2026-12-31"
    assert params["driver"] == "revenue_guidance"
    assert params["time_type"] == "duration"
    assert params["date"] == "2026-07-01T12:00:00-04:00"
    assert params["period_scope"] == "annual"      # §9 series key INCLUDES scope —
    assert "period_scope" in query                 # Q1 never copies from YTD-Q1
    assert "PRIMARY_FILER" in query                # company by GRAPH EDGE, never id
    assert "quote_hash" in query                   # hashed members included via field
    assert "datetime(" in query                    # earlier-only by real time compare


def test_prior_ranking_latest_earlier_guide_wins():
    rows = [{"series_unit": "usd", "date": "2026-05-01T09:00:00-04:00",
             "source_type": "10q", "source_id": "acc-old"},
            {"series_unit": "m_usd", "date": "2026-06-15T16:05:00-04:00",
             "source_type": "8k", "source_id": "acc-new"}]
    store = _mk_neo4j_store_with_fake_read(rows, [])
    assert store.get_prior_guide_units(PRIOR_FACT) == ["m_usd"]  # latest day wins


def test_prior_ranking_same_day_8k_beats_transcript():
    # §9 (FINAL_DESIGN 300): same day is RESOLVED by source rank — never a park
    rows = [{"series_unit": "m_usd", "date": "2026-06-15T08:00:00-04:00",
             "source_type": "8k", "source_id": "acc-8k"},
            {"series_unit": "usd", "date": "2026-06-15T11:00:00-04:00",
             "source_type": "transcript", "source_id": "acc-tr"}]
    store = _mk_neo4j_store_with_fake_read(rows, [])
    assert store.get_prior_guide_units(PRIOR_FACT) == ["m_usd"]


def test_prior_ranking_tiebreaks_later_time_then_source_id():
    rows = [{"series_unit": "usd", "date": "2026-06-15T08:00:00-04:00",
             "source_type": "8k", "source_id": "acc-a"},
            {"series_unit": "m_usd", "date": "2026-06-15T11:00:00-04:00",
             "source_type": "8k", "source_id": "acc-b"}]
    store = _mk_neo4j_store_with_fake_read(rows, [])
    assert store.get_prior_guide_units(PRIOR_FACT) == ["m_usd"]  # later time wins
    rows = [{"series_unit": "usd", "date": "2026-06-15T11:00:00-04:00",
             "source_type": "8k", "source_id": "acc-a"},
            {"series_unit": "m_usd", "date": "2026-06-15T11:00:00-04:00",
             "source_type": "8k", "source_id": "acc-b"}]
    store = _mk_neo4j_store_with_fake_read(rows, [])
    assert store.get_prior_guide_units(PRIOR_FACT) == ["m_usd"]  # then source id


def test_prior_ranking_day_is_eastern_not_string_prefix():
    # 02:00Z on the 16th IS 22:00 Eastern on the 15th — same Eastern day ("Day" =
    # Eastern Time, FINAL_DESIGN 301), so the 8-K still wins by source rank
    rows = [{"series_unit": "usd", "date": "2026-06-16T02:00:00+00:00",
             "source_type": "transcript", "source_id": "acc-tr"},
            {"series_unit": "m_usd", "date": "2026-06-15T20:00:00-04:00",
             "source_type": "8k", "source_id": "acc-8k"}]
    store = _mk_neo4j_store_with_fake_read(rows, [])
    assert store.get_prior_guide_units(PRIOR_FACT) == ["m_usd"]


def test_prior_winning_source_collision_conflict_parks():
    # the one genuine ambiguity: the winning SOURCE disagrees with ITSELF
    # (collision records) — its distinct units all return and the writer parks;
    # the outranked transcript's unit never rides along
    rows = [{"series_unit": "m_usd", "date": "2026-06-15T08:00:00-04:00",
             "source_type": "8k", "source_id": "acc-8k"},
            {"series_unit": "usd", "date": "2026-06-15T08:00:00-04:00",
             "source_type": "8k", "source_id": "acc-8k"},
            {"series_unit": "eur", "date": "2026-06-15T11:00:00-04:00",
             "source_type": "transcript", "source_id": "acc-tr"}]
    store = _mk_neo4j_store_with_fake_read(rows, [])
    assert store.get_prior_guide_units(PRIOR_FACT) == ["m_usd", "usd"]


def test_priors_lookup_receives_period_scope(tmp_path):
    seen = []

    class Capture(FakeStore):
        def get_prior_guide_units(self, fact):
            seen.append(fact["period_scope"])
            return super().get_prior_guide_units(fact)
    gid = f"du:{SRC}:revenue_guidance:period=gp_2025-10-01_2026-09-30"
    drivers = {"revenue_guidance": {"name": "revenue_guidance",
                                    "fact_type": "guidance"}}
    out = run(tmp_path, [guidance_withdrawal()],
              Capture(drivers=drivers, prior_units={gid: ["m_usd"]}))
    assert out["items"][0]["decision"] == "written"
    assert seen == ["annual"]                      # the FY window's scope rides along


def test_preflight_positive_and_negative():
    from driver.core.driver_neo4j_adapter import preflight

    class Stub:
        def __init__(self, constraints, sentinels):
            self._c, self._s = constraints, sentinels

        def _read(self, query, **params):
            return self._c if "CONSTRAINT" in query else self._s
    ready = preflight(Stub(
        [{"labelsOrTypes": ["DriverUpdate"], "properties": ["id"]},
         {"labelsOrTypes": ["DriverPeriod"], "properties": ["id"]},
         {"labelsOrTypes": ["Driver"], "properties": ["name"]}],
        [{"id": s} for s in ("gp_ST", "gp_MT", "gp_LT", "gp_UNDEF")]))
    assert ready["ready"] is True                  # POSITIVE: full setup -> ready
    not_ready = preflight(Stub(
        [{"labelsOrTypes": ["DriverUpdate"], "properties": ["id"]},
         {"labelsOrTypes": ["DriverPeriod"], "properties": ["id"]}],
        [{"id": s} for s in ("gp_ST", "gp_MT", "gp_LT", "gp_UNDEF")]))
    assert not_ready["ready"] is False             # NEGATIVE: Driver.name missing


def test_permutation_identical_decisions(tmp_path):
    facts = surprise_pair() + [fact(driver_name="x")]
    store = FakeStore(drivers={
        "revenue": {"name": "revenue", "fact_type": "metric"},
        "revenue_surprise": {"name": "revenue_surprise", "fact_type": "surprise"}})
    out1 = run(tmp_path / "p1", facts, store)
    out2 = run(tmp_path / "p2", list(reversed(facts)), store)
    by_decision1 = sorted((i["decision"], tuple(i["codes"])) for i in out1["items"])
    by_decision2 = sorted((i["decision"], tuple(i["codes"])) for i in out2["items"])
    assert by_decision1 == by_decision2


# ---- step-7 round 5: exact-fact query hardening + fetch-once ----

def test_xbrl_fact_query_is_company_scoped_nonnil_and_length_guarded():
    captured = []

    def fake_read(query, **params):
        captured.append(query)
        if "HAS_XBRL" in query:                    # the facts read
            return [
                {"fid": "f1", "period_type": "duration",
                 "start_date": "2025-06-29", "end_date": "2025-09-28",
                 "dus": ["1:ns:ax"], "mus": ["1:ns:me"]},
                {"fid": "f2", "period_type": "duration",     # MISALIGNED arrays:
                 "start_date": "2025-06-29", "end_date": "2025-09-28",
                 "dus": ["1:ns:ax", "1:ns:ax2"], "mus": ["1:ns:me"]}]
        return [{"id": "1:ns:ax", "qname": "ns:ax", "label": None},
                {"id": "1:ns:me", "qname": "ns:me", "label": "Me"}]
    from driver.core.driver_neo4j_adapter import Neo4jStore
    store = Neo4jStore.__new__(Neo4jStore)
    store._read = fake_read
    rows = store.get_xbrl_fact_dimensions(SRC, "us-gaap:Revenues")
    q = captured[0]
    assert "PRIMARY_FILER" in q and "FOR_COMPANY" in q     # company-scoped context
    assert "f.is_numeric = '1'" in q and "f.is_nil = '0'" in q
    assert [r["dims"] for r in rows] == [                  # misaligned row DROPPED
        [{"axis": "ns:ax", "member": "ns:me", "label": "Me"}]]


def test_xbrl_fact_rows_fetched_once_per_concept_per_event(tmp_path):
    calls = []

    class Counting(FakeStore):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            calls.append(concept)
            return super().get_xbrl_fact_dimensions(source_id, concept)
    store = Counting(xbrl_facts={"us-gaap:Revenues": [xrow([EU_DIM]), xrow([])]})
    run(tmp_path, [
        fact(slice_parts=[("geography", "Europe")], member_refs=[dict(EU_REF)],
             xbrl_concept_raw="us-gaap:Revenues"),
        fact(level_low=None, level_high=None, level_unit_raw=None,
             level_shape_hint=None, change_value=Decimal("7"),
             change_unit_raw="%", member_refs=[],
             xbrl_concept_raw="us-gaap:Revenues")], store)
    assert calls == ["us-gaap:Revenues"]           # two facts, ONE fetch
