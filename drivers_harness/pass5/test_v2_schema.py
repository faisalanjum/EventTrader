"""Unit tests for v2_schema.py — the Phase 0.1 foundation. Real behaviors + adversarial edges."""
import pytest
from v2_schema import (Registry, Driver, DriverChange, core_name, canon_metric,
                       canon_mechanism, STATE_ENUM, DIRECTION_ENUM)


# ── structured core: metric pins granularity, synonym fold, invalid cores ──
def test_core_name_synonym_fold():
    assert core_name("sales", "guidance") == "revenue_guidance"          # sales->revenue
    assert core_name("EPS", "Outlook") == "earnings_per_share_guidance"  # eps->eps, outlook->guidance
    assert core_name("revenue", "actuals") == "revenue_actual"

def test_core_distinct_metrics_stay_distinct():
    # the v1 #1 failure must be impossible: revenue vs eps guidance are different cores
    assert core_name("revenue", "guidance") != core_name("eps", "guidance")

def test_metricless_core_invalid():
    with pytest.raises(ValueError):
        core_name("", "guidance")            # bare "forward_guidance" with no metric is invalid
    with pytest.raises(ValueError):
        core_name("revenue", "")

def test_unknown_tokens_pass_through_not_rejected():
    # open vocab: an unseen metric/mechanism is NOT rejected (vs the dead closed vocab)
    assert core_name("datacenter_revenue", "actual") == "datacenter_revenue_actual"
    assert canon_mechanism("supercycle") == "supercycle"


# ── reuse-or-create + lexical alias recording ──
def test_reuse_same_core():
    r = Registry()
    d1 = r.reuse_or_create("revenue", "guidance")
    d2 = r.reuse_or_create("revenue", "guidance")
    assert d1 is d2 and len(r.drivers) == 1

def test_lexical_variant_folds_and_records_alias():
    r = Registry()
    r.reuse_or_create("revenue", "guidance")
    d = r.reuse_or_create("sales", "outlook")            # sales->revenue, outlook->guidance == revenue_guidance
    assert d.core_name == "revenue_guidance" and len(r.drivers) == 1
    assert "sales_outlook" in d.aliases                  # losing lexical variant recorded


# ── recurrence: provisional -> durable at >=2 distinct events; no deadlock ──
def test_recurrence_promotion():
    r = Registry()
    r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"}])
    assert r.drivers["revenue_guidance"].status == "provisional"
    r.admit_event("e2", "MSFT", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"}])
    assert r.drivers["revenue_guidance"].status == "durable"          # 2 distinct events -> durable

def test_same_event_does_not_double_promote():
    r = Registry()
    r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"}])
    # re-admitting the SAME event id must not add a 2nd distinct event
    r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"}])
    assert r.drivers["revenue_guidance"].recurrence_count == 1
    assert r.drivers["revenue_guidance"].status == "provisional"

def test_provisional_is_offered_for_reuse_no_deadlock():
    r = Registry()
    r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"}])
    names = [c["core_name"] for c in r.candidate_view()]
    assert "revenue_guidance" in names                                # provisional IS a reuse candidate


# ── cross-entity company-mismatch reject (objective) ──
def test_company_mismatch_rejects_readthrough():
    r = Registry()
    emitted = r.admit_event("n1", "CI", [{"metric": "revenue", "mechanism": "actual", "direction": "long",
                                          "state": "up", "about_entity": "ANTM"}])
    assert emitted == [] and r.rejects[0]["reason"] == "company_mismatch"
    assert "revenue_actual" not in r.drivers                          # not coined for the wrong filer

def test_about_entity_defaults_to_filer_admits():
    r = Registry()
    emitted = r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "actual", "direction": "long", "state": "up"}])
    assert len(emitted) == 1 and "revenue_actual" in r.drivers

def test_company_mismatch_case_insensitive_match():
    assert Registry.company_mismatch("aapl", "AAPL") is False
    assert Registry.company_mismatch("MSFT", "AAPL") is True


# ── finite enums (state is closed; free text -> state_note) ──
def test_freetext_state_rejected():
    r = Registry()
    with pytest.raises(ValueError):                                   # "raised" is a verb -> must be state_note
        r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "raised"}])

def test_bad_direction_rejected():
    r = Registry()
    with pytest.raises(ValueError):
        r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "up", "state": "up"}])

def test_state_note_carries_verb():
    r = Registry()
    em = r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long",
                                       "state": "up", "state_note": "raised FY guide to $X"}])
    assert em[0].state == "up" and "raised" in em[0].state_note


# ── defer, segment, side-channel, catalogs, persistence ──
def test_defer_recorded():
    r = Registry()
    r.admit_event("e1", "AAPL", [])
    assert r.rejects[0]["reason"] == "deferred" and not r.drivers

def test_segment_default_total_and_specific():
    r = Registry()
    em = r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "actual", "direction": "long", "state": "up"}])
    assert em[0].segment == "Total"
    em2 = r.admit_event("e2", "AAPL", [{"metric": "revenue", "mechanism": "actual", "direction": "long",
                                        "state": "up", "segment": "iphone"}])
    assert em2[0].segment == "iPhone"        # snapped to canonical XBRL Member

def test_member_snapping_normalizes_variants_and_commodity():
    from v2_schema import snap_member
    # variant bleed killed: every iPhone spelling -> one Member
    assert snap_member("AAPL", "iphone") == snap_member("AAPL", "iPhone") == snap_member("AAPL", "iPhone sales") == "iPhone"
    assert snap_member("AAPL", "services") == "Services"          # distinct from iPhone -> no bleed
    assert snap_member("NVDA", "data_center") == snap_member("NVDA", "datacenter") == "DataCenter"
    # commodity, IF routed through segment, snaps to the real XBRL menu member (oil != gas, distinct, not Total).
    # (In the anchoring contract a commodity normally goes in the METRIC; snap_member must still resolve it if not.)
    assert snap_member("FANG", "oil") == "Oil" and snap_member("EQT", "natural gas") == "NaturalGas"
    assert snap_member("X", "") == "Total" and snap_member("X", "company") == "Total"

def test_primary_flag_carried():
    r = Registry()
    em = r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "short",
                                       "state": "down", "primary": True},
                                      {"metric": "eps", "mechanism": "actual", "direction": "long", "state": "up"}])
    prim = [c for c in em if c.primary]
    assert len(prim) == 1 and prim[0].core_ref == "revenue_guidance"

def test_sidechannel_on_change_not_in_core():
    r = Registry()
    em = r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "actual", "direction": "long", "state": "up"}],
                       sector="Technology")
    assert em[0].filer_ticker == "AAPL" and em[0].sector == "Technology"
    # core identity carries no ticker/sector
    assert "AAPL" not in r.drivers["revenue_actual"].core_name

def test_catalogs():
    r = Registry()
    r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"},
                                 {"metric": "eps", "mechanism": "actual", "direction": "long", "state": "up"}])
    assert r.metric_catalog() == ["earnings_per_share", "revenue"]
    assert set(r.mechanism_catalog()) == {"actual", "guidance"}

def test_save_load_roundtrip(tmp_path):
    r = Registry()
    r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"}])
    r.admit_event("e2", "MSFT", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"}])
    p = tmp_path / "reg.json"; r.save(p)
    r2 = Registry.load(p)
    assert r2.drivers["revenue_guidance"].status == "durable"
    assert r2.stats()["durable"] == 1 and r2.stats()["changes"] == 2

def test_stats_counts():
    r = Registry()
    r.admit_event("e1", "AAPL", [{"metric": "revenue", "mechanism": "guidance", "direction": "long", "state": "up"}])
    r.admit_event("n1", "CI", [{"metric": "revenue", "mechanism": "actual", "direction": "long", "state": "up",
                                "about_entity": "ANTM"}])
    r.admit_event("e3", "AAPL", [])
    s = r.stats()
    assert s["deferred"] == 1 and s["company_mismatch"] == 1 and s["drivers"] == 1


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
