"""Fiscal Stage-A V2 contract tests.

These tests build V2 events only in memory. V1 stays live, no artifact is
rewritten, and no Core trust door or graph writer is called.
"""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FISCAL = ROOT / "driver" / "channels" / "fiscal_ai"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "driver" / "relocation"))

from driver.channels.fiscal_ai import build_packets as BP
from driver.channels.fiscal_ai import public_contract as PC
from driver.channels.fiscal_ai import run_code_tier as RC
from driver.channels.fiscal_ai import route_a_source as SRC
import locator as LOC
import wp3_compliant_packet as WP3

CONTRACT = ROOT / ".claude/plans/Drivers/FinalDesign/ChannelContractV2.md"


def _contract_surfaces():
    text = CONTRACT.read_text(encoding="utf-8")
    marker = "```json CONTRACT-SURFACES"
    assert text.count(marker) == 1
    start = text.index(marker) + len(marker)
    end = text.index("```", start)
    return json.loads(text[start:end])


RETIRED = frozenset(
    _contract_surfaces()["staged_raw_channel"]["retired_fiscal_fields"])


def _record(source_id="ACC:1", label="Revenue", value="4,828", **extra):
    row = {
        "source_id": source_id,
        "source_type": "10q",
        "ticker": "AAA",
        "event_time": "2026-05-01T09:00:00-04:00",
        "raw_label": label,
        "value": value,
        "fmt": "number",
        "is_currency": True,
        "period_end": "2026-03-31",
        "cadence": "Quarterly",
        "quote": "Revenue was 4,828; dollars in millions.",
        "period_evidence": "Three months ended March 31, 2026",
        "tier": "T2-label",
        "quote_source": "section",
    }
    row.update(extra)
    return row


def _xbrl(axis_members=None):
    return {
        "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "ptype": "duration",
        "unit": "usd",
        "ix": {"scale": 6, "sign": None, "format": "ixt:num-dot-decimal",
               "unit_ref": "usd"},
        "source_evidence": {
            "representation_sha256": "a" * 64,
            "quote_span": [0, 7],
            "raw_label_span": [0, 7],
            "pieces": [],
        },
        "axis_members": axis_members or [],
    }


def _sources(text="Revenue was 4,828; dollars in millions."):
    return {"ACC_1": {
        "source_id": "ACC:1",
        "text_parts": [{"part": "source-node-1", "content": text}],
    }}


def _assert_stage_a_event(event, expected_parts=None):
    """Independent test-only comparison to the frozen contract surface."""
    raw = _contract_surfaces()["staged_raw_channel"]
    assert set(event) == set(raw["event_fields"])
    assert all(set(part) == set(raw["text_part_fields"])
               for part in event["text_parts"])
    if expected_parts is not None:
        assert event["text_parts"] == expected_parts
    for item in event["items"]:
        assert set(item) <= set(raw["item_fields_after_retirement"])
        assert not (set(item) & RETIRED)
        if "xbrl" not in item:
            continue
        xbrl = item["xbrl"]
        assert set(xbrl) == set(raw["xbrl_fields"])
        assert set(xbrl["ix"]) == set(raw["ix_fields"])
        assert all(set(d) == set(raw["dimension_fields"])
                   for d in xbrl["dimensions"])


def test_red_exact_contract_shape_and_shared_event_grouping(monkeypatch):
    raw = _contract_surfaces()["staged_raw_channel"]
    records = [_record(), _record(label="Operating income", value="900")]

    calls = []
    owner = BP._group_events

    def observed(*args, **kwargs):
        calls.append(1)
        return owner(*args, **kwargs)

    monkeypatch.setattr(BP, "_group_events", observed)
    v1, _, _ = BP.build(records, [], {"AAA": 12})
    v2, _, _ = BP.build_stage_a_v2(records, [], {"AAA": 12}, _sources())

    assert len(v1) == len(v2) == 1 and calls == [1, 1]
    event = v2[0]
    _assert_stage_a_event(event, _sources()["ACC_1"]["text_parts"])
    assert len(event["items"]) == 2
    assert all(set(item) <= set(raw["item_fields_after_retirement"])
               for item in event["items"])
    assert set(event["items"][0]) == set(raw["item_fields_after_retirement"]) - {"xbrl"}
    assert all(not (set(item) & RETIRED) for item in event["items"])
    assert all("sequential_evidence" not in item for item in event["items"])
    assert all("text_parts" not in item for item in event["items"])
    assert all(set(part) == set(raw["text_part_fields"])
               for part in event["text_parts"])


def test_red_exact_text_parts_once_without_cleanup_or_guessing():
    text = "  Revenue was 4,828; dollars in millions.  "
    source = {"source_id": "ACC:1", "text_parts": [
        {"part": "source-node-a", "content": text},
        {"part": "source-node-b", "content": text},
    ]}
    parts = [
        {"part": "source-node-a", "content": text},
        {"part": "source-node-b", "content": text},
    ]
    assert not hasattr(RC, "event_text_parts")

    records = [_record(quote=text), _record(label="Other revenue", quote=text)]
    events, _, _ = BP.build_stage_a_v2(
        records, [], {"AAA": 12}, {"ACC_1": source})
    event = events[0]
    assert event["text_parts"] == parts
    assert event["text_parts"] is not source["text_parts"]
    assert [item["quote"] for item in event["items"]] == [text, text]
    assert all("xbrl" not in item for item in event["items"])
    assert event["items"][0]["value"] == "4,828"
    assert event["items"][0]["fmt"] == "number"
    assert event["items"][0]["is_currency"] is True


def test_red_prose_parts_use_source_node_ids_and_order_without_content_dedupe():
    class Session:
        query = None
        params = None

        def run(self, query, **params):
            self.query = query
            self.params = params
            return [
                {"part": "source-node-a", "content": "same words"},
                {"part": "source-node-b", "content": "same words"},
            ]

    session = Session()
    parts = RC._fetch_text_parts(
        session, "ACC-1", ("HAS_EXHIBIT", "HAS_SECTION"))
    assert parts == [
        {"part": "source-node-a", "content": "same words"},
        {"part": "source-node-b", "content": "same words"},
    ]
    assert "RETURN n.id AS part, n.content AS content" in session.query
    assert "ORDER BY part" in session.query
    assert "DISTINCT" not in session.query
    assert session.params == {
        "accession": "ACC-1",
        "relationship_types": ["HAS_EXHIBIT", "HAS_SECTION"],
    }


def test_red_contract_mutations_catch_parts_retired_fields_and_dimensions():
    parts = [
        {"part": "source-node-a", "content": "Revenue was 4,828."},
        {"part": "source-node-b", "content": "Dollars in millions."},
    ]
    source = {"source_id": "ACC:1", "text_parts": copy.deepcopy(parts)}
    records = [_record(xbrl=_xbrl([["axis", "member"]]), tier="T1-xbrl")]
    event = BP.build_stage_a_v2(
        records, [], {"AAA": 12}, {"ACC_1": source})[0][0]
    _assert_stage_a_event(event, parts)  # positive control

    mutations = []
    missing = copy.deepcopy(event)
    missing["text_parts"].pop()
    mutations.append(missing)
    reordered = copy.deepcopy(event)
    reordered["text_parts"].reverse()
    mutations.append(reordered)
    retired = copy.deepcopy(event)
    retired["items"][0][next(iter(RETIRED))] = "forbidden"
    mutations.append(retired)
    bypassed = copy.deepcopy(event)
    bypassed_xbrl = bypassed["items"][0]["xbrl"]
    bypassed_xbrl["axis_members"] = [
        [d["axis"], d["member"]] for d in bypassed_xbrl.pop("dimensions")]
    mutations.append(bypassed)

    for mutant in mutations:
        with pytest.raises(AssertionError):
            _assert_stage_a_event(mutant, parts)


def test_red_xbrl_transport_uses_the_existing_dimension_owner(monkeypatch):
    raw = _contract_surfaces()["staged_raw_channel"]
    xbrl = _xbrl([["srt:GeographicalAxis", "srt:NorthAmericaMember"]])
    before = copy.deepcopy(xbrl)
    calls = []
    owner = PC.convert_dimensions

    def observed(value):
        calls.append(1)
        return owner(value)

    monkeypatch.setattr(PC, "convert_dimensions", observed)
    events, _, _ = BP.build_stage_a_v2(
        [_record(xbrl=xbrl, tier="T1-xbrl")], [], {"AAA": 12}, _sources())
    public = PC.to_public([{"items": [{"raw_label": "Revenue", "xbrl": xbrl}]}])

    assert calls == [1, 1]
    assert xbrl == before
    got = events[0]["items"][0]["xbrl"]
    assert set(got) == set(raw["xbrl_fields"])
    assert set(got["ix"]) == set(raw["ix_fields"])
    assert got["dimensions"] == [
        {"axis": "srt:GeographicalAxis", "member": "srt:NorthAmericaMember"}
    ]
    assert all(set(d) == set(raw["dimension_fields"]) for d in got["dimensions"])
    assert "axis_members" not in got and "slice_part" not in got
    assert got["source_evidence"] == before["source_evidence"]
    assert public[0]["items"][0]["xbrl"]["dimensions"] == got["dimensions"]


def test_red_dimension_mutation_refused_by_one_owner_with_positive_control():
    good = _record(xbrl=_xbrl([["a", "m"]]))
    events, _, _ = BP.build_stage_a_v2([good], [], {"AAA": 12}, _sources())
    assert events[0]["items"][0]["xbrl"]["dimensions"] == [
        {"axis": "a", "member": "m"}
    ]

    bad = _record(xbrl=_xbrl([["axis-only"]]))
    with pytest.raises(ValueError, match="malformed dimension pair"):
        BP.build_stage_a_v2([bad], [], {"AAA": 12}, _sources())
    with pytest.raises(ValueError, match="malformed dimension pair"):
        PC.to_public([{"items": [{"raw_label": "Revenue", "xbrl": bad["xbrl"]}]}])


def test_red_v1_routing_owner_and_v2_staging_are_separate():
    abstain = {
        "item_id": "one", "ticker": "AAA", "raw_label": "Missing",
        "period_end": "2026-03-31", "form": "10-Q",
        "status": "value_absent", "reason": "value_absent",
        "sources_searched": ["10q"], "sources_incomplete": True,
    }
    _, v1_skip, v1_park = BP.build([], [abstain], {})
    _, v2_skip, v2_park = BP.build_stage_a_v2([], [abstain], {}, {})
    assert (v2_skip, v2_park) == (v1_skip, v1_park)
    assert v2_park[0]["reason"] == "sources_incomplete"

    source = {"source_id": "ACC:1", "text_parts": [
        {"part": "source-node-1", "content": "Revenue 1"},
    ]}
    out, _, _ = BP.build_stage_a_v2(
        [_record(value="1", quote="Revenue 1")], [], {"AAA": 12},
        {"ACC_1": source})
    assert not (set(out[0]["items"][0]) & RETIRED)
    assert set(BP.build(
        [_record(value="1", quote="Revenue 1")], [], {"AAA": 12}
    )[0][0]["items"][0]) & RETIRED == RETIRED


def _real_v1_packets():
    paths = [
        ROOT / "data/driver_catalog_seed/wp3_ce_compliant/packets.jsonl",
        ROOT / "data/driver_catalog_seed/wp3_aci_stream/packets.jsonl",
    ]
    return [json.loads(line) for path in paths for line in path.read_text().splitlines()]


def _prepared_text(source_id, cache):
    from driver.relocation import inline_html as IH
    path = ROOT / "scripts/driver_seed/relocate_probe/inline_html_cache" / f"{source_id}.htm"
    assert path.is_file(), f"real-data cache missing: {path}"
    if source_id not in cache:
        cache[source_id] = IH.prepare(path.read_text(encoding="utf-8", errors="replace"))
    return cache[source_id]


def _internal_record(packet, item):
    record = {k: copy.deepcopy(v) for k, v in item.items()
              if k not in RETIRED and k != "raw_label_or_claim"}
    if "raw_label_or_claim" in item:
        record["raw_label"] = item["raw_label_or_claim"]
    else:
        assert "raw_label" in record
    record.update({k: packet[k] for k in
                   ("source_id", "source_type", "ticker", "event_time")})
    return record


def test_red_real_route_a_source_locator_to_stage_a_has_prepared_part():
    packet = next(p for p in _real_v1_packets() if p["source_id"] == WP3.ACC)
    source = SRC.build_source(WP3.ACC)
    assert source is not None
    located = LOC.locate(WP3.ANCHOR, source)
    assert located["status"] is None and len(located["items"]) == 4
    records = [dict(
        item,
        source_id=source["source_id"],
        source_type=source["source_type"],
        ticker="CE",
        fmt="number",
        is_currency=True,
        tier="T1-xbrl",
        period_end=item["xbrl"]["period_end"],
        cadence=WP3.CADENCE_FIXTURE[
            (WP3.ACC, item["xbrl"]["period_start"], item["xbrl"]["period_end"])],
        event_time=packet["event_time"],
    ) for item in located["items"]]
    events, skip, park = BP.build_stage_a_v2(
        records, [], {"CE": 12}, {WP3.ACC: source})
    assert not skip and not park and len(events) == 1
    assert events[0]["text_parts"] == source["text_parts"]
    assert events[0]["text_parts"][0]["part"] == source["source_id"]
    assert all(item["quote"] in events[0]["text_parts"][0]["content"]
               for item in events[0]["items"])


def test_red_all_11_real_route_a_items_rebuild_in_memory_without_skips():
    packets = _real_v1_packets()
    cache = {}
    source_cache = {}
    records = []
    sources = {}
    expected = []
    for packet in packets:
        prepared = _prepared_text(packet["source_id"], cache)
        if packet["source_id"] not in source_cache:
            source_cache[packet["source_id"]] = SRC.build_source(packet["source_id"])
        source = source_cache[packet["source_id"]]
        assert source is not None
        assert source["text_parts"] == [
            {"part": packet["source_id"], "content": prepared["text"]}]
        sources[BP.canonicalize_source_id(packet["source_id"])] = source
        for item in packet["items"]:
            evidence = item["xbrl"]["source_evidence"]
            assert evidence["representation_sha256"] == prepared["text_sha"]
            qa, qb = evidence["quote_span"]
            assert prepared["text"][qa:qb] == item["quote"]
            for piece in evidence["pieces"]:
                pa, pb = piece["span"]
                assert prepared["text"][pa:pb] == piece["text"]
            records.append(_internal_record(packet, item))
            expected.append({k: copy.deepcopy(v) for k, v in item.items()
                             if k not in RETIRED})

    fye = {packet["ticker"]: packet["fye_month"] for packet in packets}
    events, skip, park = BP.build_stage_a_v2(records, [], fye, sources)
    got = [item for event in events for item in event["items"]]
    assert not skip and not park
    assert len(got) == len(expected) == 11
    assert got == expected
    assert all(len(event["text_parts"]) == 1 for event in events)
    assert all(item["quote"] in event["text_parts"][0]["content"]
               for event in events for item in event["items"])


def _tracked_v1_packet_paths():
    paths = subprocess.check_output(
        ["git", "ls-files", "data/driver_catalog_seed"], cwd=ROOT,
        text=True).splitlines()
    out = []
    for name in paths:
        path = ROOT / name
        if name.endswith("/packets.jsonl") and any(
                f'"{field}"' in path.read_text(encoding="utf-8")
                for field in RETIRED):
            out.append(path)
    return out


def test_red_complete_tracked_v1_packet_population_is_classified():
    paths = _tracked_v1_packet_paths()
    cache = {}
    totals = {"artifacts": len(paths),
              "packaged": {"events": 0, "items": 0},
              "source_replay": {
                  "complete": {"events": 0, "items": 0},
                  "cache_missing": {"events": 0, "items": 0},
                  "quote_mismatch": {"events": 0, "items": 0},
              }, "by_source_type": {}}
    for path in paths:
        for packet in (json.loads(line) for line in path.read_text().splitlines()):
            nitems = len(packet["items"])
            totals["packaged"]["events"] += 1
            totals["packaged"]["items"] += nitems
            st = totals["by_source_type"].setdefault(
                packet["source_type"], {"events": 0, "items": 0})
            st["events"] += 1
            st["items"] += nitems

            html = (ROOT / "scripts/driver_seed/relocate_probe/inline_html_cache" /
                    f"{packet['source_id']}.htm")
            if html.is_file():
                prepared = _prepared_text(packet["source_id"], cache)
                source = {"source_id": packet["source_id"],
                          "text_parts": [
                              {"part": packet["source_id"],
                               "content": prepared["text"]}]}
                replay = ("complete" if all(item["quote"] in prepared["text"]
                                             for item in packet["items"])
                          else "quote_mismatch")
            else:
                source = {"source_id": packet["source_id"], "text_parts": []}
                replay = "cache_missing"
            totals["source_replay"][replay]["events"] += 1
            totals["source_replay"][replay]["items"] += nitems
            records = [_internal_record(packet, item) for item in packet["items"]]
            events, skip, park = BP.build_stage_a_v2(
                records, [], {packet["ticker"]: packet["fye_month"]},
                {BP.canonicalize_source_id(packet["source_id"]): source})
            assert len(events) == 1 and not skip and not park
            assert len(events[0]["items"]) == len(packet["items"])
            assert all(not (set(item) & RETIRED) for item in events[0]["items"])

    print("STAGE_A_V1_POPULATION " + json.dumps(totals, sort_keys=True))
    assert totals == {
        "artifacts": 7, "packaged": {"events": 136, "items": 743},
        "source_replay": {
            "complete": {"events": 40, "items": 137},
            "cache_missing": {"events": 47, "items": 185},
            "quote_mismatch": {"events": 49, "items": 421},
        },
        "by_source_type": {
            "10k": {"events": 69, "items": 434},
            "10q": {"events": 22, "items": 127},
            "8k": {"events": 45, "items": 182},
        },
    }


def test_red_fiscal_staging_has_no_core_door_or_writer_import():
    for path in (FISCAL / "build_packets.py", FISCAL / "run_code_tier.py",
                 FISCAL / "public_contract.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        modules = []
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(node.module or "")
                names.extend(alias.name for alias in node.names)
        assert not any(name.startswith("driver.core") for name in modules)
        assert not ({"attach_event_xbrl", "validate_via_production"} & set(names))

    source = BP.build_stage_a_v2.__doc__ + "\n" + __import__("inspect").getsource(
        BP.build_stage_a_v2)
    assert "to_public(" not in source
    assert "unit_hints(" not in source
