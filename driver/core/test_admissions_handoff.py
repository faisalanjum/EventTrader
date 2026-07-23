"""Phase-5 item 1 — the S4 v2.5 Step-3 admissions handoff (dry-run only).

The FULL v2.5 test list (S4_KernelRecipes_DRAFT.md:71-77) + the Phase-5 audit
additions (the create_driver plan carries name + fact_type + the first accepted
fact's evidence quote). NO adapter Driver writes exist — recordings produce
dry-run PLANS only; admissions + enable_writes hard-fails before any planning.
"""
from decimal import Decimal

import pytest

from driver.core.driver_write_cli import run_event
from driver.core.driver_writer import WriterError
from driver.core.prepared_fact import RunInputV1, SchemaError
from driver.core.test_driver_write_cli import SRC, FakeStore, audit_docs, fact


def run_adm(tmp_path, facts, admissions, store=None, **kw):
    ri = RunInputV1.from_dict({"source_id": SRC, "facts": facts})
    return run_event(ri, store=store or FakeStore(), audit_dir=str(tmp_path),
                     admissions=admissions, **kw)


def adm(decision="create", name="gross_margin", ftype="metric"):
    return {"decision": decision, "driver_name": name, "fact_type": ftype}


def newfact(**over):
    d = fact(driver_name="gross_margin")
    d.update(over)
    return d


# ---- mode 1: admissions=None → today's behavior byte-unchanged ----

def test_admissions_none_still_parks_driver_not_ready(tmp_path):
    out = run_event(RunInputV1.from_dict({"source_id": SRC,
                                          "facts": [newfact()]}),
                    store=FakeStore(), audit_dir=str(tmp_path))
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["DRIVER_NOT_READY"]
    assert "driver_plans" not in out


# ---- the rehearsal clamp ----

def test_enable_writes_with_admissions_hard_fails_before_planning(tmp_path):
    with pytest.raises(WriterError):
        run_adm(tmp_path, [newfact()], {0: adm()}, enable_writes=True)
    # ZERO side effects: the clamp fires before the audit file is even created
    assert audit_docs(tmp_path) == []


# ---- map completeness, BOTH ways, before any planning ----

def test_missing_entry_hard_errors(tmp_path):
    with pytest.raises(SchemaError):
        run_adm(tmp_path, [newfact(), newfact(fiscal_quarter=2,
                                              period_start_date="2025-03-30",
                                              period_end_date="2025-06-28")],
                {0: adm()})


def test_extra_entry_hard_errors(tmp_path):
    with pytest.raises(SchemaError):
        run_adm(tmp_path, [newfact()], {0: adm(), 1: adm()})


def test_malformed_entry_hard_errors(tmp_path):
    for bad in ({0: {"decision": "create", "driver_name": "gross_margin"}},
                {0: adm(decision="invent")},
                {0: adm(name="")},
                {0: {**adm(), "extra": "x"}},
                [],                              # wrong container entirely
                [adm()],                         # list, not an index-keyed map
                {0: None}):                      # entry not even a mapping
        with pytest.raises(SchemaError):         # ALWAYS the clean input error —
            run_adm(tmp_path, [newfact()], bad)  # never a raw TypeError crash
    assert audit_docs(tmp_path) == []            # and ZERO side effects


def test_admission_name_must_match_fact_name(tmp_path):
    with pytest.raises(SchemaError):
        run_adm(tmp_path, [newfact()], {0: adm(name="other_driver")})


def test_disagreeing_triples_in_one_group_hard_error(tmp_path):
    facts = [newfact(),
             newfact(fiscal_quarter=2, period_start_date="2025-03-30",
                     period_end_date="2025-06-28")]
    with pytest.raises(SchemaError):
        run_adm(tmp_path, facts, {0: adm("create"), 1: adm("attach")})


# ---- CREATE: born-complete bundle, one Driver plan, full evidence ----

def test_create_plans_one_driver_with_first_fact_bundle(tmp_path):
    out = run_adm(tmp_path, [newfact()], {0: adm()})
    assert out["status"] == "dry_run"
    assert out["items"][0]["decision"] == "written"
    plans = out["driver_plans"]
    assert len(plans) == 1
    p = plans[0]
    assert p["op"] == "create_driver"
    assert p["name"] == "gross_margin" and p["fact_type"] == "metric"
    assert p["fact_ids"] == [out["items"][0]["fact_id"]]
    assert p["first_fact_id"] == out["items"][0]["fact_id"]
    # the LAWFUL evidence shape — exactly what rebuild_anchor consumes
    assert p["definitional_evidence"] == {
        "birth_quotes": ["Q3 revenue was $100 million"]}
    doc = audit_docs(tmp_path)[0]
    assert doc["driver_plans"] == plans
    # ATOMIC bundle: create_driver HEADS the first accepted fact's own plan ops
    fact_plan = next(pl for pl in doc["plans"]
                     if pl["fact_id"] == p["first_fact_id"])
    assert fact_plan["ops"][0]["op"] == "create_driver"
    assert fact_plan["ops"][1]["op"] == "create_fact"


def test_audit_records_admissions_for_reconstruction(tmp_path):
    out = run_adm(tmp_path, [newfact()], {0: adm()})
    assert out["status"] == "dry_run"
    doc = audit_docs(tmp_path)[0]
    assert doc["input"]["admissions"] == {
        "0": {"decision": "create", "driver_name": "gross_margin",
              "fact_type": "metric"}}


def test_rebuild_anchor_consumes_planned_birth_quote(tmp_path):
    # the neutral home is consumed bare-module style (its own suite convention:
    # no package, pytest puts the dir on sys.path) — mirror that here
    import sys
    from pathlib import Path
    reloc = str(Path(__file__).resolve().parents[1] / "relocation")
    if reloc not in sys.path:
        sys.path.insert(0, reloc)
    from locator import rebuild_anchor
    out = run_adm(tmp_path, [newfact()], {0: adm()})
    p = out["driver_plans"][0]
    doc = audit_docs(tmp_path)[0]
    fact_plan = next(pl for pl in doc["plans"]
                     if pl["fact_id"] == p["first_fact_id"])
    props = next(op for op in fact_plan["ops"]
                 if op["op"] == "create_fact")["props"]
    driver_node = {"name": p["name"], "fact_type": p["fact_type"],
                   "definitional_evidence": p["definitional_evidence"]}
    # the birth quote is IMMUTABLE evidence: even after a later LWW quote
    # update on the fact, the anchor's wording comes from birth_quotes
    props = dict(props, quote="a later restated quote (LWW-updated)")
    anchor, stripped = rebuild_anchor(p["first_fact_id"], props, driver_node,
                                      {SRC: "AAPL"})
    assert anchor["wording"] == ("Q3 revenue was $100 million",)
    assert anchor["driver"] == "gross_margin"
    assert anchor["company"] == "AAPL"


def test_two_facts_one_new_driver_exactly_one_create(tmp_path):
    facts = [newfact(),
             newfact(fiscal_quarter=2, period_start_date="2025-03-30",
                     period_end_date="2025-06-28")]
    out = run_adm(tmp_path, facts, {0: adm(), 1: adm()})
    assert [i["decision"] for i in out["items"]] == ["written", "written"]
    plans = out["driver_plans"]
    assert len(plans) == 1                      # ONE create_driver, never per fact
    assert sorted(plans[0]["fact_ids"]) == sorted(
        i["fact_id"] for i in out["items"])
    assert plans[0]["first_fact_id"] == out["items"][0]["fact_id"]
    # atomically bundled EXACTLY ONCE: heads the FIRST fact's ops, nowhere else
    doc = audit_docs(tmp_path)[0]
    heads = [pl["fact_id"] for pl in doc["plans"]
             if pl["ops"] and pl["ops"][0]["op"] == "create_driver"]
    assert heads == [plans[0]["first_fact_id"]]
    total = sum(1 for pl in doc["plans"] for op in pl["ops"]
                if op["op"] == "create_driver")
    assert total == 1
    facts_created = sum(1 for pl in doc["plans"] for op in pl["ops"]
                        if op["op"] == "create_fact")
    assert facts_created == 2                   # one Driver, exactly TWO facts


def test_create_when_driver_already_exists_parks(tmp_path):
    out = run_adm(tmp_path, [fact()],            # 'revenue' EXISTS in FakeStore
                  {0: adm(name="revenue", ftype="metric")})
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["DRIVER_NOT_READY"]
    assert "exists" in out["items"][0]["detail"]
    assert out["driver_plans"] == []


# ---- ATTACH: graph-backed verification + the offline card ----

def test_graph_attach_verified_uses_stored_driver(tmp_path):
    out = run_adm(tmp_path, [fact()], {0: adm("attach", "revenue", "metric")})
    assert out["items"][0]["decision"] == "written"
    assert out["driver_plans"] == []             # existing Driver: no create plan


def test_graph_attach_wrong_fact_type_parks(tmp_path):
    # a METRIC admission (the fence's only legal type) against a stored Driver
    # whose real fact_type is 'surprise' — the mismatch parks, never silent
    out = run_adm(tmp_path, [fact(driver_name="revenue_surprise")],
                  {0: adm("attach", "revenue_surprise", "metric")})
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["DRIVER_NOT_READY"]
    assert "fact_type" in out["items"][0]["detail"]


def test_offline_card_attach_plans_bundle_with_admission_fact_type(tmp_path):
    out = run_adm(tmp_path, [newfact()], {0: adm("attach")})
    assert out["items"][0]["decision"] == "written"      # never a park
    plans = out["driver_plans"]
    assert len(plans) == 1                               # never a bare create
    assert plans[0]["fact_type"] == "metric"             # FROM the admission


# ---- node invariant + period wiring ----

def test_all_facts_parked_plans_no_driver(tmp_path):
    # half + fiscal_quarter together = conflicting period framing -> PARKS
    # (a fact with NO period fields at all is lawfully periodless and writes)
    bad = newfact(half=1)
    out = run_adm(tmp_path, [bad], {0: adm()})
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["PERIOD_UNRESOLVED"]
    assert out["driver_plans"] == []


def test_admission_fact_type_drives_lane_validation(tmp_path):
    # a sentinel period on a METRIC fact is illegal (sentinels are
    # guidance-only): the REJECT proves the admission's fact_type reached the
    # lane validators for a Driver that exists nowhere in the graph
    sent = newfact(period_start_date=None, period_end_date=None,
                   fiscal_year=None, fiscal_quarter=None,
                   sentinel_class="long_term")
    out = run_adm(tmp_path, [sent], {0: adm()})
    assert out["items"][0]["decision"] == "rejected"
    assert "PERIOD_LANE" in out["items"][0]["codes"]
    assert out["driver_plans"] == []


# ---- the v2.5 rehearsal fence + strict indexes ----

def test_non_metric_admission_hard_errors(tmp_path):
    guide = fact(driver_name="eps_guidance", driver_state="introduced",
                 company_confirmed=True)
    with pytest.raises(SchemaError):
        run_adm(tmp_path, [guide],
                {0: adm("create", "eps_guidance", "guidance")})


def test_non_integer_index_keys_hard_error(tmp_path):
    facts = [newfact(),
             newfact(fiscal_quarter=2, period_start_date="2025-03-30",
                     period_end_date="2025-06-28")]
    with pytest.raises(SchemaError):      # True/False == 1/0 must NOT pass
        run_adm(tmp_path, facts, {False: adm(), True: adm()})
    with pytest.raises(SchemaError):
        run_adm(tmp_path, [newfact()], {0.0: adm()})


def test_early_exit_paths_still_carry_driver_plans(tmp_path):
    # mode-consistency: an admissions run ALWAYS carries driver_plans (empty on
    # early exits) — absent-vs-[] must never be ambiguous for reconciliation
    out = run_adm(tmp_path, [newfact()], {0: adm()},
                  store=FakeStore(companies=["AAPL", "MSFT"]))
    assert out["items"][0]["codes"] == ["SOURCE_COMPANY_AMBIGUOUS"]
    assert out["driver_plans"] == []
    out2 = run_adm(str(tmp_path) + "2", [newfact()], {0: adm()},
                   store=FakeStore(source=None))
    assert out2["code"] == "SOURCE_MISSING" and out2["driver_plans"] == []


# ---- admissions=None: the OLD read path, byte-exact ----

def test_none_mode_preserves_old_driver_read_path(tmp_path):
    calls = []

    class CountingStore(FakeStore):
        def get_driver(self, name):
            calls.append(name)
            return super().get_driver(name)

    run_event(RunInputV1.from_dict({"source_id": SRC, "facts": [fact()]}),
              store=CountingStore(), audit_dir=str(tmp_path))
    # the pre-admissions CLI read the driver TWICE per fact (tail + validation)
    assert calls == ["revenue", "revenue"]
