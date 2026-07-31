"""S4 v2.5 DRY-RUN WIRING REHEARSAL — replay-only acceptance (owner GO 2026-07-23).

REPLAY, NEVER SIMULATE: the recorded candidates ARE the decomposer stand-in and
the recorded kernel decisions ARE the kernel stand-in (both independently
reviewed, rev3-accepted). No fake decomposer, kernel, or selector exists here —
the mapper below is pure field transport that FAILS LOUD on anything it does
not recognize. Passing proves WIRING ONLY (v2.5 proof-limit) — never component
precision/recall.

Certification properties (review round 2026-07-24): all seven pins are stamped
INTO every write-ahead audit (each audit alone proves its inputs); packets join
candidates by the approved {source_id}#{index} sidecar identity (content
equality then VERIFIES, never selects); accounting closes BOTH ways (no missing
item/skipped row/result and no orphan plan); normal reruns write to pytest
tmp_path — the reviewable artifact emission happens ONLY when S4_REHEARSAL_OUT
names the output directory; skips are narrow (missing config or genuine Neo4j
connection classes — everything else surfaces).

Seven run_event calls, all dry-run: the 4 real filing events run against the
READ-ONLY live adapter (transaction() raises by design; the write block is
gated behind enable_writes, never entered); the 3 synthetic control events run
against the FakeStore declared in test_state.jsonl. SYN-CTRL-SKIPPED never
reaches Core (accounting only). ZERO model calls, ZERO graph writes (proven by
before/after node counts), no ENABLE_DRIVER_WRITES.

Every input is hash-pinned: the four rev3 fixtures + the three 616b099 packet
files. A pin mismatch is a hard FAILURE, never a skip. Skips happen ONLY for
missing Neo4j config/connectivity (the repo's proven narrow pattern)."""
import hashlib
import json
import os
from decimal import Decimal

import pytest

from driver.core.driver_write_cli import run_event
from driver.core.prepared_fact import PreparedFactV1, RunInputV1
from driver.core.test_driver_write_cli import FakeStore

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FIX = os.path.join(_REPO, "data", "driver_catalog_seed", "s4_fixtures")
_PKT = os.path.join(_REPO, "data", "driver_catalog_seed")

# The ACCEPTED rev3 fixture pins (formal sign-off 2026-07-23) + the 616b099
# packet pins the fixture headers declare. Copied whole from tool output.
PINS = {
    "s4_fixtures/recorded_candidates.jsonl":
        "28fc6ed6928c48d19cea2d1f395b1a5de64c3f6e09491ecac03b76e1d9487331",
    "s4_fixtures/recorded_kernel_decisions.jsonl":
        "e69e82b840abf861a455f717913c06a96deb9fd126701a9fa655266017b16036",
    "s4_fixtures/expected_results.jsonl":
        "0953a2f064b064d7509b0bb0e05ee7f733a045570a808a3e30debc7c8a04fae9",
    "s4_fixtures/test_state.jsonl":
        "283a1588ed4c398021e97c6ccf5f9c6237ce67eca346df747d9dbfa74ac968b5",
    "wp3_ce_compliant/packets.jsonl":
        "f79f39ee8e3d903ae71b3d5e788f2f9863123f7fd4183c09aaeb722762266e24",
    "wp3_aci_stream/packets.jsonl":
        "2f7c0b7cde3c8ee858bc649b59acf890bc23f8919d61f1b5395e7b9ffcbca14f",
    "wp3_aci_stream/no_match_ledger.jsonl":
        "bda988132a0053004b37460b2f182fefdcfa4305def9acd98a96d44f49cc9684",
}

# The complete recorded-candidate vocabulary. An unknown key = the recording
# and this transport have diverged -> FAIL, never guess (no silent drops).
_CAND_KEYS = {"driver_state", "fiscal_quarter", "fiscal_year", "half", "item_id",
              "kind", "level_money_mode_hint", "level_shape_hint",
              "level_unit_kind_hint", "measurement_spans", "member_refs", "note",
              "per_x", "period_end_date", "period_scope", "period_start_date",
              "proposed_name", "quote", "sentinel_class", "slice_tokens",
              "stated_unit_raw", "stated_value", "time_type", "xbrl_evidence"}
_REAL_EVENTS = ("0001306830-24-000155", "0001646972-23-000045",
                "0001646972-23-000056", "0001646972-24-000165")
_SYN_EVENTS = ("SYN-CTRL-MERGED", "SYN-CTRL-PARKED", "SYN-CTRL-REJECTED")


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _rows(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l, parse_float=Decimal) for l in fh if l.strip()]


def _prepared(cand, adm):
    """Candidate -> PreparedFactV1: PURE transport of the recorded fields.
    Judgment lives in the recordings; anything unrecognized fails loud."""
    unknown = set(cand) - _CAND_KEYS
    assert not unknown, f"candidate {cand['item_id']}: unmapped keys {sorted(unknown)}"
    assert cand["proposed_name"] == adm["driver_name"], cand["item_id"]
    assert cand.get("per_x") is None, "per-X transport is not part of this rehearsal"
    ev, refs, concept = cand.get("xbrl_evidence"), None, None
    if ev is not None:
        refs, concept = cand["member_refs"], ev["concept"]
        assert ([{"axis": r["axis"], "member": r["member"]} for r in refs]
                == ev["dimensions"]), f"{cand['item_id']}: refs != evidence dims"
        assert (refs == []) == ev["verified_empty"], cand["item_id"]
    else:
        assert "member_refs" not in cand, cand["item_id"]
    v = cand.get("stated_value")
    level = Decimal(v) if v is not None else None
    return PreparedFactV1.from_dict({
        "driver_name": adm["driver_name"],
        "driver_state": cand["driver_state"],
        "quote": cand["quote"],
        "level_low": level, "level_high": level,
        "level_unit_raw": cand.get("stated_unit_raw"),
        "level_unit_kind_hint": cand.get("level_unit_kind_hint"),
        "level_money_mode_hint": cand.get("level_money_mode_hint"),
        "level_shape_hint": cand.get("level_shape_hint"),
        "measurement_raw_spans": list(cand.get("measurement_spans", [])),
        "period_start_date": cand.get("period_start_date"),
        "period_end_date": cand.get("period_end_date"),
        "fiscal_year": cand.get("fiscal_year"),
        "fiscal_quarter": cand.get("fiscal_quarter"),
        "half": cand.get("half"),
        "sentinel_class": cand.get("sentinel_class"),
        "time_type": cand.get("time_type"),
        "period_scope": cand.get("period_scope"),
        "slice_parts": [tuple(t.split(":", 1)) for t in cand.get("slice_tokens", [])],
        "member_refs": refs, "xbrl_concept_raw": concept})


def _skip_if_disconnected(e):
    """Narrow skip (the proven census pattern): ONLY genuine Neo4j
    connection-class failures skip. Anything else — a missing fixture, a
    KeyError, an assertion — SURFACES as the failure it is."""
    names = {t.__name__ for t in type(e).__mro__}
    if {"ServiceUnavailable", "AuthError", "ConfigurationError",
            "SessionExpired"} & names:
        pytest.skip(f"Neo4j unavailable: {type(e).__name__}: {e}")
    raise e


def _live_store():
    if not os.environ.get("NEO4J_URI"):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(_REPO, ".env"))
    if not (os.environ.get("NEO4J_URI") and os.environ.get("NEO4J_USERNAME")
            and os.environ.get("NEO4J_PASSWORD")):
        pytest.skip("Neo4j environment not configured")
    from driver.core.driver_neo4j_adapter import Neo4jStore
    try:
        store = Neo4jStore()
        store._read("RETURN 1 AS ok")
    except Exception as e:
        _skip_if_disconnected(e)
    return store


def _stamp_pins(audit_dir):
    """Provenance INSIDE the write-ahead record: after the CLI finalizes, the
    harness stamps all seven input pins into the audit file (atomic replace;
    refuses double-stamping). Each audit alone then proves its exact inputs."""
    path = os.path.join(audit_dir, max(os.listdir(audit_dir)))
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert "rehearsal_pins" not in doc, f"double stamp on {path}"
    doc["rehearsal_pins"] = dict(PINS)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    os.replace(tmp, path)
    return doc


@pytest.mark.live
def test_s4_rehearsal(tmp_path):
    assert os.environ.get("ENABLE_DRIVER_WRITES") != "1", \
        "the write gate must be OFF for the rehearsal"
    # normal reruns stay in tmp; the reviewable emission is explicit-only
    out_root = os.environ.get("S4_REHEARSAL_OUT") or str(tmp_path)

    # ---- 1. every pin verified (hard fail, never skip) ----
    hashes = {}
    for rel, want in PINS.items():
        got = _sha(os.path.join(_PKT, rel))
        assert got == want, f"PIN MISMATCH {rel}: {got}"
        hashes[rel] = got
    cands = _rows(os.path.join(_FIX, "recorded_candidates.jsonl"))
    decs = _rows(os.path.join(_FIX, "recorded_kernel_decisions.jsonl"))
    exps = _rows(os.path.join(_FIX, "expected_results.jsonl"))
    states = _rows(os.path.join(_FIX, "test_state.jsonl"))
    header = cands[0]
    assert header["revision"] == 3
    assert {k: v for k, v in
            header["valid_only_while"]["packet_sha256"].items()} == {
        "wp3_ce_compliant/packets.jsonl": PINS["wp3_ce_compliant/packets.jsonl"],
        "wp3_aci_stream/packets.jsonl": PINS["wp3_aci_stream/packets.jsonl"],
        "wp3_aci_stream/no_match_ledger.jsonl":
            PINS["wp3_aci_stream/no_match_ledger.jsonl"]}

    # ---- 2. sidecar ids at load: {source}#{zero-based position per event} ----
    by_event, positions = {}, {}
    for row in cands[1:]:
        src, _, idx = row["item_id"].rpartition("#")
        pos = positions.get(src, 0)
        assert int(idx) == pos, f"sidecar order broken at {row['item_id']}"
        positions[src] = pos + 1
        by_event.setdefault(src, []).append(row)
    dec_by_item = {}
    for row in decs[1:]:
        d = dict(row)
        d.pop("note", None)
        dec_by_item[d.pop("item_id")] = d
    skipped = by_event.pop("SYN-CTRL-SKIPPED")
    assert len(skipped) == 1 and skipped[0]["kind"] == "TEST-CONTROL-SKIPPED"
    assert "SYN-CTRL-SKIPPED#0" not in dec_by_item, \
        "the skipped item must have NO kernel decision"
    assert set(by_event) == set(_REAL_EVENTS) | set(_SYN_EVENTS)
    assert sum(len(v) for v in by_event.values()) == 14      # to-Core items

    # ---- 3. packet traceback by IDENTITY: the approved sidecar
    # {source_id}#{index} names the packet item DIRECTLY (join by identity;
    # content equality then VERIFIES the recording — search never selects) ----
    packet_items = {}
    for rel in ("wp3_ce_compliant/packets.jsonl", "wp3_aci_stream/packets.jsonl"):
        for pkt in _rows(os.path.join(_PKT, rel)):
            packet_items.setdefault(pkt["source_id"], []).extend(pkt["items"])
    for src in _REAL_EVENTS:
        assert len(packet_items[src]) == len(by_event[src]), \
            f"{src}: {len(packet_items[src])} packet items vs " \
            f"{len(by_event[src])} recorded candidates"
        for i, c in enumerate(by_event[src]):
            it = packet_items[src][i]
            assert Decimal(str(it["value"])) == Decimal(str(c["stated_value"])), \
                (c["item_id"], it["value"])
            assert it["xbrl"]["period_start"] == c["period_start_date"], c["item_id"]
            assert it["xbrl"]["period_end"] == c["period_end_date"], c["item_id"]
            assert it["quote"] == c["quote"], c["item_id"]
            # the XBRL EVIDENCE itself must be equal end-to-end: packet concept,
            # period type, and the exact dimension list == the candidate's
            # recorded evidence (verified-empty [] included)
            x, ev = it["xbrl"], c["xbrl_evidence"]
            assert x["concept"] == ev["concept"], c["item_id"]
            assert x["ptype"] == c["time_type"], (c["item_id"], x["ptype"])
            assert x["dimensions"] == ev["dimensions"], (c["item_id"],
                                                         x["dimensions"])
            assert (x["dimensions"] == []) == ev["verified_empty"], c["item_id"]

    # ---- 4. the seven dry-run events ----
    live = _live_store()
    pre_counts = {lbl: live._read(f"MATCH (n:{lbl}) RETURN count(n) AS c")[0]["c"]
                  for lbl in ("Driver", "DriverUpdate")}
    assert pre_counts["Driver"] == 0, "gold precondition: zero Driver nodes"
    state_by_event = {r["event"]: r for r in states[1:]}
    for ev in ("SYN-CTRL-PARKED", "SYN-CTRL-REJECTED"):
        assert state_by_event[ev]["preload"] == {"drivers": {}, "facts": []}, \
            f"{ev} must see no pre-existing Driver/fact"
    os.makedirs(out_root, exist_ok=True)
    results, audits = {}, {}
    for src in _REAL_EVENTS + _SYN_EVENTS:
        rows = by_event[src]
        adms = {i: dec_by_item[r["item_id"]] for i, r in enumerate(rows)}
        facts = [_prepared(r, adms[i]) for i, r in enumerate(rows)]
        if src in _SYN_EVENTS:
            st = state_by_event[src]
            store = FakeStore(facts=st["preload"]["facts"],
                              source=dict(st["source"]),
                              companies=list(st["companies"]),
                              drivers=dict(st["preload"]["drivers"]))
        else:
            store = live
        audit_dir = os.path.join(out_root, "audit", src)
        os.makedirs(audit_dir, exist_ok=True)
        out = run_event(RunInputV1(source_id=src, facts=facts),
                        store=store, audit_dir=audit_dir, admissions=adms)
        assert out["status"] == "dry_run", (src, out["status"])
        # every result index present exactly once (per-event completeness)
        assert [it["index"] for it in out["items"]] == list(range(len(rows))), src
        results[src] = out
        audits[src] = _stamp_pins(audit_dir)       # all 7 pins ride EVERY audit
        assert audits[src]["rehearsal_pins"] == PINS, src
        if src == "SYN-CTRL-MERGED":
            assert store.applied == [] and len(store.facts) == 1, \
                "merged control: ZERO new writes, the one preloaded fact only"

    # ---- 5. compare vs the expected gold, item by item ----
    exp_rows = {r["item_id"]: r for r in exps[1:-1]}
    summary = exps[-1]
    assert summary["kind"] == "expected_summary"
    # TWO-WAY completeness of the answer sheet itself: every raw item
    # (skipped included) has exactly one expected row, and no expected row
    # names an item that does not exist
    all_item_ids = {r["item_id"] for rows in by_event.values() for r in rows}
    all_item_ids |= {skipped[0]["item_id"]}
    assert len(exps) == 1 + 15 + 1, len(exps)
    assert set(exp_rows) == all_item_ids and len(exp_rows) == 15
    cand_by_item = {r["item_id"]: r for rows in by_event.values() for r in rows}
    written_ids, report_items = set(), []
    for item_id, e in sorted(exp_rows.items()):
        src, _, idx = item_id.rpartition("#")
        if e["expected_outcome"] == "skipped":
            assert src == "SYN-CTRL-SKIPPED" and src not in results
            assert e["expected_reason"] == skipped[0]["part_b_exclusion_reason"]
            assert e["expected_fact_count"] == 0
            report_items.append({"item_id": item_id, "outcome": "skipped",
                                 "ok": True, "detail": "never sent into Core"})
            continue
        got = results[src]["items"][int(idx)]
        assert got["index"] == int(idx)
        assert got["decision"] == e["expected_outcome"], (
            item_id, got["decision"], e["expected_outcome"], got["detail"])
        if e["expected_outcome"] in ("parked", "rejected"):
            assert got["codes"] == e["expected_codes"], (item_id, got["codes"])
            assert got["fact_id"] is None
            report_items.append({"item_id": item_id, "outcome": got["decision"],
                                 "codes": got["codes"], "ok": True})
            continue
        assert got["fact_id"] == e["expected_fact_id"], (item_id, got["fact_id"])
        plan = next(p for p in audits[src]["plans"]
                    if p["fact_id"] == e["expected_fact_id"])
        if e["expected_outcome"] == "merged":
            assert plan["outcome"] == "noop"
            real_ops = [o for o in plan["ops"] if o.get("op") != "log"]
            assert len(real_ops) == e["expected_ops"] == 0, real_ops
        else:                                       # written
            written_ids.add(got["fact_id"])
            create = next(o for o in plan["ops"] if o.get("op") == "create_fact")
            p = create["props"]
            for lo_hi in ("level_low", "level_high"):
                assert Decimal(str(p[lo_hi])) == Decimal(str(e["expected_level"])), (
                    item_id, lo_hi, p[lo_hi])
            assert p["level_unit"] == e["expected_level_unit"], item_id
            assert p["series_unit"] == e["expected_series_unit"], item_id
            assert p["period_scope"] == e["expected_period_scope"], (
                item_id, p["period_scope"])
            assert p["driver_state"] == e["expected_driver_state"], item_id
            links = [o for o in plan["ops"] if o.get("op") == "edge"
                     and o.get("type") == "MAPS_TO_MEMBER"]
            assert len(links) == e["expected_member_links"], (item_id, links)
            # the EXACT links, never just the count: every planned
            # (axis, member, slice_part) triple must equal the candidate's
            # recorded references one-to-one, and hang off THIS fact
            planned = sorted((o["axis"], o["to"], o["props"]["slice_part"])
                             for o in links)
            recorded = sorted(
                (r["axis"], r["member"], r["slice_part"])
                for r in cand_by_item[item_id].get("member_refs") or [])
            assert planned == recorded, (item_id, planned, recorded)
            assert all(o["from"] == e["expected_fact_id"] for o in links), item_id
        report_items.append({"item_id": item_id, "outcome": got["decision"],
                             "fact_id": got["fact_id"], "ok": True})

    # ---- 6. accounting closes both ways + the born-complete Driver plans ----
    assert len(written_ids) == 11 == summary["outcome_counts"]["written"]
    # NO ORPHANS in either direction: every audit plan belongs to an expected
    # written/merged fact, and every expected written/merged fact has exactly
    # one plan; every result index was consumed by the expected loop above
    planned_fact_ids = [p["fact_id"] for src in results
                        for p in audits[src]["plans"]]
    expected_planned = {e["expected_fact_id"] for e in exp_rows.values()
                        if e["expected_outcome"] in ("written", "merged")}
    assert len(planned_fact_ids) == len(set(planned_fact_ids)) == 12
    assert set(planned_fact_ids) == expected_planned, \
        (sorted(set(planned_fact_ids) ^ expected_planned))
    result_keys = {(src, it["index"]) for src, out in results.items()
                   for it in out["items"]}
    expected_keys = {(i.rpartition("#")[0], int(i.rpartition("#")[2]))
                     for i in exp_rows if not i.startswith("SYN-CTRL-SKIPPED")}
    assert result_keys == expected_keys, (result_keys ^ expected_keys)
    for src in _REAL_EVENTS:
        plans = results[src]["driver_plans"]
        assert len(plans) == summary["driver_plans_per_real_event"] == 1, src
        dp = plans[0]
        assert (dp["op"], dp["name"], dp["fact_type"]) == (
            "create_driver", "revenue", "metric")
        ev_written = [r["items"][i]["fact_id"] for i, r in
                      [(i, results[src]) for i in range(len(by_event[src]))]
                      if r["items"][i]["decision"] == "written"]
        assert dp["fact_ids"] == ev_written and dp["first_fact_id"] == ev_written[0]
        first_quote = by_event[src][0]["quote"]
        assert dp["definitional_evidence"]["birth_quotes"] == [first_quote]
        head = next(p for p in audits[src]["plans"]
                    if p["fact_id"] == dp["first_fact_id"])
        assert head["ops"][0].get("op") == "create_driver", \
            "the create_driver op must atomically HEAD its first fact's ops"
    assert results["SYN-CTRL-MERGED"]["driver_plans"] == [], \
        "attach onto the preloaded Driver plans NO creation"

    # ---- 7. zero-graph-write proof ----
    post_counts = {lbl: live._read(f"MATCH (n:{lbl}) RETURN count(n) AS c")[0]["c"]
                   for lbl in ("Driver", "DriverUpdate")}
    assert post_counts == pre_counts, (pre_counts, post_counts)
    live.close()

    # ---- 8. the rehearsal report (the reviewable verdict artifact) ----
    with open(os.path.join(out_root, "report.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "verdict": "PASS — WIRING ONLY (v2.5 proof-limit: this proves the "
                       "recorded answers flow through run_event to the expected "
                       "plans; it certifies NO component precision/recall)",
            "run_mode": {"dry_run": True, "enable_writes": False,
                         "live_ai_calls": 0, "graph_writes": 0},
            "pins_verified": hashes,
            "events": {src: {"status": results[src]["status"],
                             "items": results[src]["items"],
                             "driver_plans": results[src]["driver_plans"]}
                       for src in results},
            "graph_counts_pre_post": [pre_counts, post_counts],
            "item_table": report_items,
            "outcome_counts": summary["outcome_counts"],
            "per20_note": "no selector was built or simulated (owner order); "
                          "all four real events are 10-K/Q by pinned "
                          "construction; the PER-20 selector remains a future "
                          "build behind its own recipe",
        }, fh, indent=1, default=str)
