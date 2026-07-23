"""Phase-5 item 2 — the Adjusted PRESERVATION chain (no keyword rule anywhere).

Core's duty is to PRESERVE an already-resolved measurement end-to-end and to
fail closed when it cannot — never to detect "adjusted" semantically (that is
the future decomposer's judgment). Fixture is DATA-PINNED to the real graph
fact (read-only census 2026-07-23): PATH 10-Q `0001734722-25-000050` (created
2025-12-08T17:28:43-05:00, FYE January), `path:CostOfRevenueAdjusted`, the
"Adjusted cost of professional services and other" row — the source table is
in USD THOUSANDS and shows 24,999 (graph value 24,999,000 usd); stored period
2025-08-01..2025-11-01 with the stored end EXCLUSIVE -> claimed window
2025-08-01..2025-10-31 = Q3 FY2026; REAL dimensions preserved as slice parts:
srt:ProductOrServiceAxis -> path:ProfessionalServicesAndOtherMember (product)
+ us-gaap:StatementBusinessSegmentsAxis -> path:ReportableSegmentMember
(segment) — a two-part COMPONENT, never presented as the consolidated total.
"""
from decimal import Decimal

from driver.core.driver_write_cli import run_event
from driver.core.prepared_fact import RunInputV1
from driver.core.test_driver_write_cli import FakeStore, audit_docs

SRC_PATH = "0001734722-25-000050"
# the EXACT visible table row (label + footnote markers + the four period
# columns Q3FY26 · Q3FY25 · 9M-FY26 · 9M-FY25 — all four values graph-verified)
REAL_QUOTE = ("Adjusted cost of professional services and other (2)(3)(4) "
              "24,999 14,980 68,906 42,644")
REAL_SLICE = [("product", "ProfessionalServicesAndOther"),
              ("segment", "ReportableSegment")]
REAL_CONCEPT = "path:CostOfRevenueAdjusted"
REAL_DIMS = [{"axis": "srt:ProductOrServiceAxis",
              "member": "path:ProfessionalServicesAndOtherMember",
              "label": "ProfessionalServicesAndOther"},
             {"axis": "us-gaap:StatementBusinessSegmentsAxis",
              "member": "path:ReportableSegmentMember",
              "label": "ReportableSegment"}]
REAL_REFS = [{"axis": d["axis"], "member": d["member"], "slice_part": sp}
             for d, sp in zip(REAL_DIMS,
                              ["product:professionalservicesandother",
                               "segment:reportablesegment"])]


def path_store():
    return FakeStore(
        source={"date": "2025-12-08T17:28:43-05:00", "source_type": "10q",
                "ticker": "PATH", "fye_month": 1},
        companies=["PATH"],
        # deterministic verification rows mirroring the REAL graph fact —
        # stored period end EXCLUSIVE (2025-11-01 = claimed 10-31 + 1 day)
        xbrl_facts={REAL_CONCEPT: [{"period_type": "duration",
                                    "start_date": "2025-08-01",
                                    "end_date": "2025-11-01",
                                    "dims": REAL_DIMS}]})


def adjusted_fact(**over):
    d = {"driver_name": "cost_of_revenue", "driver_state": "reported",
         "quote": REAL_QUOTE,
         "measurement_raw_spans": ["Adjusted"],
         "slice_parts": REAL_SLICE,
         "xbrl_concept_raw": REAL_CONCEPT,
         "member_refs": [dict(r) for r in REAL_REFS],
         "level_low": Decimal("24999"), "level_high": Decimal("24999"),
         "level_unit_raw": "USD thousands", "level_shape_hint": "point",
         "period_start_date": "2025-08-01", "period_end_date": "2025-10-31",
         "fiscal_year": 2026, "fiscal_quarter": 3, "time_type": "duration"}
    d.update(over)
    return d


def run_create(tmp_path, fact_dict):
    ri = RunInputV1.from_dict({"source_id": SRC_PATH, "facts": [fact_dict]})
    return run_event(ri, store=path_store(), audit_dir=str(tmp_path),
                     admissions={0: {"decision": "create",
                                     "driver_name": "cost_of_revenue",
                                     "fact_type": "metric"}})


def test_adjusted_chain_span_to_id_to_anchor(tmp_path):
    import sys
    from pathlib import Path
    reloc = str(Path(__file__).resolve().parents[1] / "relocation")
    if reloc not in sys.path:
        sys.path.insert(0, reloc)
    from locator import rebuild_anchor

    out = run_create(tmp_path, adjusted_fact())
    assert out["items"][0]["decision"] == "written"
    fact_id = out["items"][0]["fact_id"]
    # 1. the recorded candidate carries the RAW span (audit input, reconstructable)
    doc = audit_docs(tmp_path)[0]
    assert doc["input"]["facts"][0]["measurement_raw_spans"] == ["Adjusted"]
    # 2. the fact ID carries the resolved measurement token
    assert "measurement=adjusted" in fact_id
    # 3. the planned stored fact: token in scope, REAL value at the REAL scale
    #    (source thousands 24,999 -> stored 24.999 m_usd — never trillions),
    #    and BOTH real categories preserved (a component, not a total)
    props = next(op for pl in doc["plans"] for op in pl["ops"]
                 if op["op"] == "create_fact")["props"]
    assert "measurement=adjusted" in props["fact_scope"]
    assert props["level_low"] == 24.999 and props["level_unit"] == "m_usd"
    assert "slice=product:professionalservicesandother;" \
           "segment:reportablesegment" in props["fact_scope"]
    # 3b. the categories are VERIFIED XBRL, not copied strings: both member
    #     links are planned, each with its axis at TOP LEVEL (edge identity)
    links = [op for pl in doc["plans"] for op in pl["ops"]
             if op.get("type") == "MAPS_TO_MEMBER"]
    assert {(l["axis"], l["to"]) for l in links} == {
        (d["axis"], d["member"]) for d in REAL_DIMS}
    assert all(l["props"]["slice_part"] == r["slice_part"]
               for l, r in zip(sorted(links, key=lambda x: x["axis"]),
                               sorted(REAL_REFS, key=lambda x: x["axis"])))
    # 4. the rebuilt anchor RETURNS the measurement and the full slice
    p = out["driver_plans"][0]
    driver_node = {"name": p["name"], "fact_type": p["fact_type"],
                   "definitional_evidence": p["definitional_evidence"]}
    anchor, _ = rebuild_anchor(p["first_fact_id"], props, driver_node,
                               {SRC_PATH: "PATH"})
    assert anchor["measurement"] == "adjusted"
    assert anchor["slice"] == ("product:professionalservicesandother;"
                               "segment:reportablesegment")
    assert anchor["company"] == "PATH"
    assert anchor["wording"] == (REAL_QUOTE,)


def test_unresolvable_measurement_parks_before_creation(tmp_path):
    # a span that normalizes to NOTHING is unresolvable: the candidate parks
    # (EMPTY_LABEL) and NO Driver creation is ever planned. ("%%" truly
    # normalizes to empty; "™" does NOT — NFKD folds it to the letters "TM",
    # so it lawfully becomes measurement=tm and writes)
    out = run_create(tmp_path, adjusted_fact(measurement_raw_spans=["%%"]))
    assert out["items"][0]["decision"] == "parked"
    assert out["items"][0]["codes"] == ["EMPTY_LABEL"]
    assert out["driver_plans"] == []


def test_plain_version_never_planned(tmp_path):
    # with the Adjusted span resolved, EVERY planned representation carries the
    # token — a plain (measurement-less) twin never appears anywhere in the plan
    out = run_create(tmp_path, adjusted_fact())
    doc = audit_docs(tmp_path)[0]
    created = [op for pl in doc["plans"] for op in pl["ops"]
               if op["op"] == "create_fact"]
    assert len(created) == 1
    assert all("measurement=adjusted" in op["props"]["fact_scope"]
               and "measurement=adjusted" in op["props"]["id"]
               for op in created)
    assert all("measurement=adjusted" in fid
               for fid in out["driver_plans"][0]["fact_ids"])
