"""RED-first tests for the ONE Core V2 event route (#827 Part 2, SEQ 984).

THE ROUTE IS THE EXISTING `driver_write_cli.run_event`. V2 replaces the V1
contract AT that entry point — no second public function. Every RED is a REAL
V1-vs-V2 boundary mismatch from calling the contractual path, never a
test-authored gate.

STAGE A IS BUILT IN MEMORY (`build_packets.build_stage_a_v2`). `wp3_*/packets.jsonl`
are protected V1 artifacts and are NEVER read as a V2 event.

PUBLIC OUTPUT IS EXACTLY {index, fact_id, decision, codes, detail}. Internal
relations are read through spies on the real seams, never by widening output.

THE TWO DOORS, by WHICH CONSTRUCTOR builds the fact (the reader supplies
model-owned semantics for BOTH lanes):
    text fact  -> PreparedFactV2.from_dict      never attach_event_xbrl
    XBRL fact  -> attach_event_xbrl             never the public model door

DIMENSION CONVERSION IS CORE'S, BEFORE THE DOOR (ChannelContractV2 §3-4):
    public raw {axis, member}  --Core-->  internal member_refs {axis, member, slice_part}
The door accepts EXACTLY `xbrl_attach._EVENT_ITEM_KEYS`
= ("fact","concept","member_refs","source_evidence") — never an `xbrl` bundle.

Component owners are NOT re-tested here: Stage-A rebuild
(`scripts/driver_seed/test_stage_a_v2.py`), the XBRL door and filing
verification and `check_member_refs`
(`driver/relocation/test_packet_items_through_the_door.py`,
`test_real_726_end_to_end.py`), raw/fact accounting and codeless refusal
(`driver/core/test_raw_fact_accounting.py`).

CLAIM SCOPE (S4_KernelRecipes_DRAFT.md:19-23): WIRING ONLY. Recorded names,
fact_type and period fields are INJECTED WIRING INPUTS (SEQ 982) — never graded.

    ┌─ FAMILY 12 — OWNER-FROZEN 2026-08-12, no longer blocked ──────────────┐
    │ A reader abstention on a SUBMITTED item is the public decision         │
    │ `skipped` carrying `READER_ABSTAINED`, and a malformed generic         │
    │ Stage-A item is `rejected` carrying `CHANNEL_CONTRACT_INVALID`.        │
    │ Both codes live in the ONE owner (`outcome_codes.ROUTE_CODES`).        │
    │ `XBRL_CONTRACT_INVALID` remains the attach door's own code.            │
    └────────────────────────────────────────────────────────────────────────┘
"""
import copy
import json
import os
import sys

from decimal import Decimal

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts", "driver_seed"))

import driver.core.driver_write_cli as CLI                           # noqa: E402
from driver.core import (driver_fusion, driver_validators,           # noqa: E402
                         driver_writer, prepared_fact_v2, slice_menu,
                         xbrl_attach)
from driver.core.driver_write_cli import run_event                   # noqa: E402
from driver.core.test_driver_write_cli import FakeStore              # noqa: E402
from driver.core.test_v2_attacks import item as v2_item, slot        # noqa: E402
import test_stage_a_v2 as SA                                         # noqa: E402

ENVELOPE_FIELDS = ("source_id", "source_type", "ticker", "fye_month",
                   "event_time", "text_parts", "items")
# THE ONE UNRESOLVED PRIVATE SEAM, stated rather than invented (SEQ 985 item 6).
# Authority fixes the producer EVENT VIEW (FableExperimentWorkOrder:635 —
# source_id + text_parts + {ticker, fye_month, event_date} + the pinned slice
# menu) and fixes that the raw POSITION stays in caller control. Authority does
# NOT fix the per-record callback shape: 15_CandidateFactPacket Part B is
# per-record ("a raw label + context") while the adopted producer view is
# whole-event. I do not freeze a key set from convenience; the test below
# asserts only the two things that ARE law — the event view reaches the reader,
# and the raw position does not, checked by an invariant no rename can slip.
EVENT_VIEW_MIN = frozenset(("source_id", "text_parts", "ticker", "fye_month"))
CE_EVENT = "0001306830-24-000155"
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CACHE = {}


# ------------------------------------------------------------------ helpers

def _v2_events():
    if "e" not in _CACHE:
        text_cache, records, sources, fye = {}, [], {}, {}
        for packet in SA._real_v1_packets():
            SA._prepared_text(packet["source_id"], text_cache)
            sources[SA.BP.canonicalize_source_id(packet["source_id"])] = \
                SA.SRC.build_source(packet["source_id"])
            fye[packet["ticker"]] = packet["fye_month"]
            for it in packet["items"]:
                records.append(SA._internal_record(packet, it))
        events, skip, park = SA.BP.build_stage_a_v2(records, [], fye, sources)
        assert not skip and not park, (skip, park)
        _CACHE["e"] = {e["source_id"]: e for e in events}
    return copy.deepcopy(_CACHE["e"])


def _recorded():
    """The already-approved WIRING inputs, keyed `{source_id}#{i}` — time_type,
    exact period dates, recorded fiscal fields, slice tokens, member_refs.
    Read-only fixture LEADS reused as injected inputs (SEQ 986 item 2). These
    are wiring inputs, NEVER semantic gold (SEQ 982).
    """
    if "rec" not in _CACHE:
        import json
        path = os.path.join(_REPO, "data", "driver_catalog_seed", "s4_fixtures",
                            "recorded_candidates.jsonl")
        rows = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                if d.get("kind") != "s4_fixture_header" and d.get("item_id"):
                    rows[d["item_id"]] = d
        _CACHE["rec"] = rows
    return _CACHE["rec"]


def _spy(monkeypatch, owner, name, wrapper):
    """Patch BOTH the owning module and the `driver_write_cli` namespace.

    A `from X import Y` in the route creates `CLI.Y`, which patching X alone
    would miss (SEQ 984 item 5). Patching both catches either lookup style.
    """
    monkeypatch.setattr(owner, name, wrapper)
    monkeypatch.setattr(CLI, name, wrapper, raising=False)


def _reply(source_id, facts=(), abstentions=()):
    """The EXACT reader envelope. The raw index is neither sent nor returned."""
    return {"source_id": source_id, "facts": list(facts),
            "abstentions": list(abstentions)}


def _text_fact(event, raw, **over):
    """A fact ALIGNED TO ITS OWN EVENT: the raw item's exact quote, the event's
    own part ref. A generic quote would fail occurrence for an unrelated
    reason (SEQ 984 item 3)."""
    part = event["text_parts"][0]["part"]
    body = event["text_parts"][0]["content"]
    occ = None if body.count(raw["quote"]) == 1 else 1
    return {"fact_type": over.pop("fact_type", "metric"), "part_ref": part,
            "occurrence_in_part": occ, "per_x": over.pop("per_x", None),
            "item": v2_item(quote=raw["quote"], **over)}


def _xbrl_fact(event, raw, item_id, **over):
    """An XBRL-lane fact carrying the RECORDED wiring inputs for this exact raw
    item — time_type, period dates, fiscal fields, slice tokens. Without them a
    lawful item silently PARKS and an index-only assertion still passes, which
    is hidden recall loss (SEQ 986 item 2). Text-scale evidence is NULL: the
    XBRL basis is the verified structured evidence, never text."""
    rec = _recorded()[item_id]
    part = event["text_parts"][0]["part"]
    # THE SCALE OWNER decides the multiplier. Hardcoding 1 against ix.scale=6
    # turned 726 into 0.000726 m_usd — a MILLION-FOLD error this suite would
    # have accepted (SEQ 987 item 2).
    mult = xbrl_attach.expected_multiplier("m_usd", raw["xbrl"]["ix"]["scale"])
    s = slot(raw["value"], mult, None)
    base = dict(quote=raw["quote"], level_low=s, level_high=s,
                level_unit="m_usd", level_shape_hint="point",
                driver_name=rec["proposed_name"], driver_state=rec["driver_state"],
                time_type=rec["time_type"],
                period_start_date=rec["period_start_date"],
                period_end_date=rec["period_end_date"],
                fiscal_year=rec.get("fiscal_year"),
                fiscal_quarter=rec.get("fiscal_quarter"),
                period_scope=rec.get("period_scope"),
                slice_parts=list(rec.get("slice_tokens") or []),
                per_x=rec.get("per_x"))
    base.update(over)
    return {"fact_type": rec.get("fact_type", "metric"), "part_ref": part,
            "occurrence_in_part": None, "per_x": base.pop("per_x", None),
            "item": v2_item(**base)}


def _xbrl_reader(event, source_id):
    """Feeds each raw item its own recorded wiring inputs. The counter is the
    TEST's own bookkeeping — the route never hands the reader a position."""
    seq = {"i": -1}

    def reader(**kw):
        seq["i"] += 1
        return _reply(source_id,
                      [_xbrl_fact(event, kw["item"], f"{source_id}#{seq['i']}")])
    return reader


def _mixed_reader(event):
    """Mixed lane: XBRL items get their recorded wiring inputs (the copied CE
    raw item keeps CE's own item_id), text items get a text fact."""
    def reader(**kw):
        raw = kw["item"]
        if "xbrl" in raw:
            return _reply(CE_EVENT, [_xbrl_fact(event, raw, f"{CE_EVENT}#0")])
        return _reply(CE_EVENT, [_text_fact(event, raw)])
    return reader


def _abstain(event, raw):
    """ONE lawful typed abstention for a raw item."""
    return {"quote": raw["quote"], "reason": "no du-worthy fact in this row",
            "part_ref": event["text_parts"][0]["part"],
            "occurrence_in_part": None}


def _text_event(source_id, quotes, content=None):
    return {"source_id": source_id, "source_type": "8k", "ticker": "X",
            "fye_month": 12, "event_time": "2026-01-01T00:00:00Z",
            "text_parts": [{"part": "p01", "content": content or " ".join(quotes)}],
            "items": [{"quote": q, "raw_label_or_claim": q} for q in quotes]}


class MatchingGraphStore(FakeStore):
    """FakeStore plus the graph rows the filing really carries, derived from the
    event's OWN xbrl blocks. Without these, `match_xbrl_fact` finds nothing and
    every XBRL item lawfully parks MEMBER_LINK_INVALID (SEQ 994 item 3) — which
    is correct behaviour, but it means an XBRL success control must supply the
    matching rows rather than rely on an empty graph.
    """

    def __init__(self, event, **kw):
        # The stored source MIRRORS the event's own envelope: the channel may
        # only ECHO graph-owned metadata, so a control whose store disagrees is
        # testing the mismatch guard, not the path under test (SEQ 997 item B).
        kw.setdefault("source", {"date": event["event_time"],
                                 "source_type": event["source_type"],
                                 "ticker": event["ticker"],
                                 "fye_month": event["fye_month"]})
        kw.setdefault("companies", [event["ticker"]])
        super().__init__(**kw)
        from driver.relocation.exact_numbers import stored_period_end
        self._rows = {}
        for raw in event["items"]:
            xb = raw.get("xbrl")
            if not xb:
                continue
            self._rows.setdefault(xb["concept"], []).append({
                "period_type": xb["ptype"],
                "start_date": xb["period_start"],
                "end_date": stored_period_end(xb["period_end"]),
                "dims": [{"axis": d["axis"], "member": d["member"],
                          "label": d["member"].split(":")[-1]}
                         for d in xb["dimensions"]]})

    def get_xbrl_fact_dimensions(self, source_id, concept):
        from driver.core.driver_neo4j_adapter import GraphFactRows
        return GraphFactRows(rows=self._rows.get(concept, []), exclusions=())


def _mirror_fake(event, **kw):
    """A FakeStore whose stored source ECHOES the event envelope, with the
    EMPTY graph these unmatched-claim controls need."""
    return FakeStore(source={"date": event["event_time"],
                             "source_type": event["source_type"],
                             "ticker": event["ticker"],
                             "fye_month": event["fye_month"]},
                     companies=[event["ticker"]], **kw)


class FakeFilingProvider:
    """The filing provider is a SEPARATE injected owner — Neo4jStore does not
    own `get_filing_document` (test_round8_xbrl_binding pins that). The route
    must be handed one explicitly; these wiring controls stub the door itself,
    so the provider only has to be the exact object that arrives there."""


def _stub_attach(monkeypatch, seen):
    """Stub the door at the symbol the route uses and return a real
    AttachResult. Filing verification stays owned by the door's own tests
    (SEQ 984 item 4) — FakeStore is not a filing provider."""
    def fake(items, *, source_id, **kw):
        items = list(items)
        seen.append(items)
        # ONE (subset_index, PreparedFactV2) PER LAWFUL ENTRY. Returning zero
        # facts for non-empty input would breach the coverage invariant and make
        # F3/F5/F8/F9/F10 vacuous (SEQ 985 item 3). Built through the door's own
        # trusted `_build`, never the public model door.
        built = []
        for i, it in enumerate(items):
            built.append((i, prepared_fact_v2.PreparedFactV2._build(
                it["fact"], {"xbrl_concept_raw": it["concept"],
                             "member_refs": it["member_refs"]})))
        return xbrl_attach.AttachResult(source_id=source_id, facts=built,
                                        preflight_outcomes=[], member_menu=())
    _spy(monkeypatch, xbrl_attach, "attach_event_xbrl", fake)
    return seen


class BombStore:
    def __getattr__(self, name):
        raise AssertionError(f"the route touched the store ({name}) pre-validation")


# ------------------------------------ F1 exact event + raw-item shape, pre-I/O

def test_F1_the_in_memory_v2_events_carry_exactly_the_seven_envelope_fields():
    for source_id, event in _v2_events().items():
        assert sorted(event) == sorted(ENVELOPE_FIELDS), source_id
        assert event["text_parts"] and event["text_parts"][0]["content"]


def _shape_attacks():
    """Attacks derived from the FROZEN CONTRACT BLOCK, not from one observed
    packet (SEQ 985 item 2).

    The block itself says: "Exact allowed spellings; lane-specific PRESENCE is
    described in prose, not implied here. Extra fields are not silently
    allowed." So ALLOWED comes from the block; REQUIRED comes from §2 prose —
    only `quote` and `raw_label_or_claim` are universal. Value/period/XBRL
    fields are present when that source/lane supplies them, so dropping `xbrl`
    yields a LAWFUL sparse text item, NOT a schema error.
    """
    raw_profile = SA._contract_surfaces()["staged_raw_channel"]
    allowed_item = set(raw_profile["item_fields_after_retirement"])
    universal = ("quote", "raw_label_or_claim")          # §2 prose, not observation
    ev = _v2_events()[CE_EVENT]
    raw = ev["items"][0]
    assert set(raw) <= allowed_item, sorted(set(raw) - allowed_item)

    out = [("event missing " + f, {k: v for k, v in ev.items() if k != f})
           for f in raw_profile["event_fields"]]
    out += [("event extra field", {**ev, "not_in_the_contract": 1}),
            ("items is a generator", {**ev, "items": (i for i in ev["items"])}),
            ("items is a str", {**ev, "items": "北"}),
            ("text_parts is a dict", {**ev, "text_parts": {"part": "p01"}})]
    # ONLY the universal item fields may be asserted missing-is-fatal.
    out += [("raw item missing " + f,
             {**ev, "items": [{k: v for k, v in raw.items() if k != f}]})
            for f in universal]
    out += [("raw item extra key", {**ev, "items": [{**raw, "slice_part": "x"}]}),
            ("raw item retired key",
             {**ev, "items": [{**raw, "level_unit_raw": "usd"}]}),
            ("xbrl is not an object", {**ev, "items": [{**raw, "xbrl": [1]}]})]
    # NESTED levels, generated from the PUBLISHED machine block rather than
    # hand-listed (SEQ 986 item 4). source_evidence grammar is delegated to the
    # attach owner and deliberately NOT duplicated here.
    xb = raw["xbrl"]
    for f in raw_profile["xbrl_fields"]:
        if f == "source_evidence":
            continue
        out.append(("xbrl missing " + f,
                    {**ev, "items": [{**raw, "xbrl": {k: v for k, v in xb.items()
                                                      if k != f}}]}))
    out.append(("xbrl extra key",
                {**ev, "items": [{**raw, "xbrl": {**xb, "not_allowed": 1}}]}))
    for f in raw_profile["ix_fields"]:
        out.append(("ix missing " + f,
                    {**ev, "items": [{**raw, "xbrl": {**xb, "ix": {
                        k: v for k, v in xb["ix"].items() if k != f}}}]}))
    out.append(("ix extra key",
                {**ev, "items": [{**raw, "xbrl": {**xb, "ix": {**xb["ix"],
                                                              "nope": 1}}}]}))
    dim0 = xb["dimensions"][0]
    for f in raw_profile["dimension_fields"]:
        out.append(("dimension missing " + f,
                    {**ev, "items": [{**raw, "xbrl": {**xb, "dimensions": [
                        {k: v for k, v in dim0.items() if k != f}]}}]}))
    out.append(("dimension extra key",
                {**ev, "items": [{**raw, "xbrl": {**xb, "dimensions": [
                    {**dim0, "slice_part": "x"}]}}]}))
    return out


def _lawful_sparse_item():
    """A text-lane item carrying ONLY the two universal fields. It must NOT be
    refused — proving the suite does not turn one packet shape into law."""
    ev = _v2_events()[CE_EVENT]
    raw = ev["items"][0]
    return {**ev, "items": [{k: raw[k] for k in ("quote", "raw_label_or_claim")}]}


_ATTACKS = _shape_attacks()          # built ONCE, not twice by the decorator


_EVENT_ATTACKS = [(l, p) for l, p in _ATTACKS if not l.startswith(("raw item", "xbrl", "ix", "dimension"))]
_ITEM_ATTACKS = [(l, p) for l, p in _ATTACKS if l.startswith(("raw item", "xbrl", "ix", "dimension"))]


@pytest.mark.parametrize("label,payload", _EVENT_ATTACKS,
                         ids=[a[0] for a in _EVENT_ATTACKS])
def test_F1_hostile_EVENT_shape_is_refused_before_any_io(label, payload, tmp_path):
    """An EVENT-level fault is still event-wide: there is no lawful item to keep."""
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(payload, store=BombStore(), audit_dir=str(tmp_path))


@pytest.mark.parametrize("label,payload", _ITEM_ATTACKS,
                         ids=[a[0] for a in _ITEM_ATTACKS])
def test_F1_a_malformed_ITEM_is_rejected_item_locally(label, payload, tmp_path):
    """OWNER-FROZEN 2026-08-12: a malformed generic Stage-A channel item is ONE
    public `rejected` row carrying CHANNEL_CONTRACT_INVALID — item-local, with a
    lawful sibling still prepared. The reader is never asked about it."""
    ce = _v2_events()[CE_EVENT]
    ev = {**payload, "items": list(payload["items"]) +
          [{"quote": "alpha", "raw_label_or_claim": "alpha"}],
          "text_parts": [{"part": ce["text_parts"][0]["part"],
                          "content": ce["text_parts"][0]["content"] + " alpha"}]}
    seen = []

    def reader(**kw):
        seen.append(kw["item"])
        return _reply(CE_EVENT, [_text_fact(ev, kw["item"])])

    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(), reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert rows[0]["decision"] == "rejected", (label, rows[0])
    assert rows[0]["codes"] == ["CHANNEL_CONTRACT_INVALID"], (label, rows[0])
    assert len(seen) == 1, "the reader was asked about the malformed item"
    assert rows[1]["fact_id"], ("the lawful sibling was lost", label, rows[1])


def test_F1_a_lawful_sparse_text_item_is_NOT_refused(tmp_path):
    """The counter-control to the 20 attacks: an item carrying only the two
    universal fields is LAWFUL. Without this, `_shape_attacks` could quietly
    harden one observed packet shape into a false requirement."""
    ev = _lawful_sparse_item()
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply(CE_EVENT,
                                                  [_text_fact(ev, kw["item"])]))
    assert [r["index"] for r in result["items"]] == [0]


# ------------------------------------- F2 reader envelope, echo, cardinality

def test_F2_the_reader_gets_the_exact_input_keys_and_never_the_raw_index(tmp_path):
    seen = []
    ev = _text_event("T-2", ["alpha", "beta"])

    def reader(**kw):
        seen.append(kw)
        return _reply("T-2", [_text_fact(ev, kw["item"])])

    run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path), reader=reader)
    assert len(seen) == 2
    for kw in seen:
        assert EVENT_VIEW_MIN <= set(kw), sorted(kw)
    # RENAME-PROOF no-leak law: across two raw items the callback input may
    # differ ONLY in the per-item payload. A raw position leaking under ANY
    # key — however spelled — would show up as a second differing key.
    differing = {k for k in set(seen[0]) | set(seen[1])
                 if seen[0].get(k) != seen[1].get(k)}
    assert differing == {"item"}, sorted(differing)
    # AND the position cannot hide INSIDE the item: each callback item must be
    # value-equal to its original raw item with NO added key (SEQ 986 item 4).
    for kw, original in zip(seen, ev["items"]):
        assert kw["item"] == original, (kw["item"], original)
    # The authoritative source TIME reaches the view. Stage A names it
    # `event_time`; the work order names `event_date`. Both spellings are
    # accepted here because resolving that naming is not this task's to make.
    assert {"event_time", "event_date"} & set(seen[0]), sorted(seen[0])

    # NOTE: this injected per-item reader is a TEMPORARY WIRING SEAM for these
    # tests only. It does not freeze the later AI decomposer API.


@pytest.mark.parametrize("label", [
    "wrong source echo", "unknown envelope key", "facts AND abstention",
    "empty both", "multiple abstentions",
    # R3 (SEQ 1012): FableExperimentWorkOrder:635 fixes the abstention shape as
    # exactly {quote, reason, part_ref, occurrence_in_part}. `{"wrong":"shape"}`
    # was published as a public `skipped`/READER_ABSTAINED row — a made-up
    # outcome from an object that met no contract.
    "abstention of the wrong shape", "abstention missing a key",
    "abstention with an extra key", "abstention with a blank reason",
    "abstention with a non-string reason",
    "abstention quoting a DIFFERENT raw item",
    "abstention naming a part that does not exist",
    "abstention with a wrong occurrence",
    # SEQ 1014: an UNHASHABLE part_ref reached `parts.get(...)` and escaped as a
    # raw TypeError instead of the contract exception — the same crash class as
    # the unhashable axis pair and the non-copyable event.
    "abstention part_ref unhashable list", "abstention part_ref unhashable dict",
    "abstention part_ref not a string", "abstention part_ref blank"])
def test_F2_unlawful_reader_replies_are_refused(label, tmp_path):
    ev = _text_event("T-3", ["alpha", "beta"], content="alpha beta")
    raw = ev["items"][0]
    good = _text_fact(ev, raw)
    ok = _abstain(ev, raw)
    bad = {
        "wrong source echo": _reply("WRONG", [good]),
        "unknown envelope key": {**_reply("T-3", [good]), "extra": 1},
        "facts AND abstention": _reply("T-3", [good], [ok]),
        "empty both": _reply("T-3"),
        "multiple abstentions": _reply("T-3", abstentions=[ok] * 2),
        "abstention of the wrong shape":
            _reply("T-3", abstentions=[{"wrong": "shape"}]),
        "abstention missing a key":
            _reply("T-3", abstentions=[{k: v for k, v in ok.items()
                                        if k != "part_ref"}]),
        "abstention with an extra key":
            _reply("T-3", abstentions=[{**ok, "confidence": 0.9}]),
        "abstention with a blank reason":
            _reply("T-3", abstentions=[{**ok, "reason": "   "}]),
        "abstention with a non-string reason":
            _reply("T-3", abstentions=[{**ok, "reason": 7}]),
        "abstention quoting a DIFFERENT raw item":
            _reply("T-3", abstentions=[{**ok, "quote": "beta"}]),
        "abstention naming a part that does not exist":
            _reply("T-3", abstentions=[{**ok, "part_ref": "p99"}]),
        "abstention with a wrong occurrence":
            _reply("T-3", abstentions=[{**ok, "occurrence_in_part": 9}]),
        "abstention part_ref unhashable list":
            _reply("T-3", abstentions=[{**ok, "part_ref": []}]),
        "abstention part_ref unhashable dict":
            _reply("T-3", abstentions=[{**ok, "part_ref": {}}]),
        "abstention part_ref not a string":
            _reply("T-3", abstentions=[{**ok, "part_ref": 7}]),
        "abstention part_ref blank":
            _reply("T-3", abstentions=[{**ok, "part_ref": "   "}]),
    }[label]
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                  reader=lambda **kw: bad)


# --------------------------------------------- F3 the 11 real XBRL positions

def test_F3_all_11_real_v2_xbrl_items_return_by_ordered_public_index(tmp_path, monkeypatch):
    handed = _stub_attach(monkeypatch, [])
    events = _v2_events()
    assert sum(len(e["items"]) for e in events.values()) == 11
    for source_id, ev in events.items():
        del handed[:]                       # this event's own door subset only
        result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path / source_id),
                           filing_provider=FakeFilingProvider(),
                           reader=_xbrl_reader(ev, source_id))
        assert [r["index"] for r in result["items"]] == list(range(len(ev["items"])))
        # HIDDEN RECALL LOSS GUARD: an index-only assertion passes even when all
        # 11 park. Every lawful item must SURVIVE with a fact_id (SEQ 986 item 2).
        for i, r in enumerate(result["items"]):
            assert r["decision"] not in ("parked", "rejected", "skipped"), r
            assert r["fact_id"], r
        # THE VALUE ITSELF, independently source-fixed: the prepared level must
        # still be the filing's own number in m_usd, not a scaled corruption.
        for i, sub in enumerate(handed[0] if handed else []):
            level = sub["fact"]["item"]["level_low"]
            assert level["value"] == Decimal(str(ev["items"][i]["value"])), (
                i, level, ev["items"][i]["value"])
            # PRESERVATION, no semantic judgment (SEQ 986 item 1 / 988 item 1):
            # the door must receive this raw item's own concept and evidence
            # value-equal, never a rebuilt or normalized copy.
            xb = ev["items"][i]["xbrl"]
            assert sub["concept"] == xb["concept"], (i, sub["concept"])
            assert sub["source_evidence"] == xb["source_evidence"], i


def test_F3_the_four_identical_quote_ce_items_stay_public_0_1_2_3(tmp_path, monkeypatch):
    _stub_attach(monkeypatch, [])
    ev = _v2_events()[CE_EVENT]
    assert len(ev["items"]) == 4 and len({i["quote"] for i in ev["items"]}) == 1
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_xbrl_reader(ev, CE_EVENT))
    assert sorted(r["index"] for r in result["items"]) == [0, 1, 2, 3]


# ------------------------------------------- F4 equal quotes + lawful split

def test_F4_two_equal_quote_text_items_remain_distinct_by_caller_position(tmp_path):
    """Two raw items pointing at ONE unique source occurrence — the real
    locator collision, with no fabricated evidence (SEQ 984 item 3)."""
    ev = _text_event("T-4", ["same", "same"], content="same")
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-4", [_text_fact(ev, kw["item"])]))
    assert sorted(r["index"] for r in result["items"]) == [0, 1]


def test_F4_a_lawful_text_split_keeps_both_facts_on_one_raw_position(tmp_path):
    """ONE quote that EXPLICITLY STATES TWO DIFFERENT METRICS -> two level facts
    with two distinct source-grounded names.

    The previous version emitted change_value=1 from a quote stating only 5 and
    4 — a number the SOURCE NEVER STATED, which the channel contract forbids —
    and its two records were complementary fragments of ONE `revenue` fact that
    `driver_fusion.fuse_event` is designed to fuse into a single row (SEQ 986
    item 1). Scale evidence is now the SMALLEST supporting span, `million`.
    """
    quote = "revenue was $5.0 million and operating income was $1.2 million"
    ev = _text_event("T-5", [quote])
    raw = ev["items"][0]
    rev = _text_fact(ev, raw, driver_name="revenue",
                     level_low=slot("5.0", 1000000, "million"),
                     level_high=slot("5.0", 1000000, "million"),
                     level_unit="m_usd", level_shape_hint="point")
    opi = _text_fact(ev, raw, driver_name="operating_income",
                     level_low=slot("1.2", 1000000, "million"),
                     level_high=slot("1.2", 1000000, "million"),
                     level_unit="m_usd", level_shape_hint="point")
    # FakeStore ships only revenue/revenue_surprise, so `operating_income`
    # would park DRIVER_NOT_READY and the two-row assertion would be a false
    # control (SEQ 987 item 3). Inject BOTH source-grounded metric Drivers.
    store = _mirror_fake(ev, drivers={
        "revenue": {"name": "revenue", "fact_type": "metric"},
        "operating_income": {"name": "operating_income", "fact_type": "metric"}})
    result = run_event(ev, store=store, audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-5", [rev, opi]))
    assert {r["index"] for r in result["items"]} == {0}
    assert len(result["items"]) == 2, "two distinct metrics were fused into one"
    for r in result["items"]:                      # SURVIVING, not merely present
        assert r["decision"] not in ("parked", "rejected", "skipped"), r
        assert r["fact_id"], r


# ----------------------------------- F5 mixed two-door routing + subset remap

def test_F5_mixed_same_source_interleaving_remaps_the_attach_subset_index(
        tmp_path, monkeypatch):
    """text raw 0, XBRL raw 1, text raw 2 — all from the SAME source, so the
    XBRL evidence is lawful for this event. Attach sees a ONE-item subset whose
    subset index 0 must remap to PUBLIC index 1."""
    ce = _v2_events()[CE_EVENT]
    body = ce["text_parts"][0]["content"]
    ev = {**ce, "items": [{"quote": "alpha", "raw_label_or_claim": "alpha"},
                          copy.deepcopy(ce["items"][0]),
                          {"quote": "gamma", "raw_label_or_claim": "gamma"}],
          "text_parts": [{"part": ce["text_parts"][0]["part"],
                          "content": body + " alpha gamma"}]}
    subsets = _stub_attach(monkeypatch, [])
    doors = []
    real_from_dict = prepared_fact_v2.PreparedFactV2.from_dict
    monkeypatch.setattr(prepared_fact_v2.PreparedFactV2, "from_dict",
                        classmethod(lambda cls, d, **k: doors.append(d) or
                                    real_from_dict(d, **k)))
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_mixed_reader(ev))
    assert len(subsets) == 1 and len(subsets[0]) == 1, "wrong XBRL subset"
    assert len(doors) == 2, "text facts must go through from_dict, XBRL must not"
    assert sorted(r["index"] for r in result["items"]) == [0, 1, 2]


# -------------------------------------- F6 model door refuses XBRL-owned fields

@pytest.mark.parametrize("owned", prepared_fact_v2.SOURCE_OWNED_FIELDS)
def test_F6_a_text_fact_cannot_assert_the_source_owned_xbrl_fields(owned, tmp_path):
    ev = _text_event("T-7", ["alpha"])
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                  reader=lambda **kw: _reply(
                      "T-7", [_text_fact(ev, kw["item"], **{owned: "forged"})]))


# ------------------------------------------------ F7 occurrence exactly once

def test_F7_verify_occurrence_runs_exactly_once_per_text_fact(tmp_path, monkeypatch):
    calls = []
    real = prepared_fact_v2.verify_occurrence
    _spy(monkeypatch, prepared_fact_v2, "verify_occurrence",
         lambda *a, **k: calls.append(a) or real(*a, **k))
    ev = _text_event("T-8", ["revenue rose"])
    run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
              reader=lambda **kw: _reply("T-8", [_text_fact(ev, kw["item"])]))
    assert len(calls) == 1, f"verify_occurrence ran {len(calls)}x, expected 1"


def test_F7_the_route_does_not_duplicate_occurrence_for_the_xbrl_lane(
        tmp_path, monkeypatch):
    """Proves only that THE ROUTE adds no second check. That the DOOR performs
    its own verification is owned by the existing attach tests."""
    calls = []
    real = prepared_fact_v2.verify_occurrence
    _spy(monkeypatch, prepared_fact_v2, "verify_occurrence",
         lambda *a, **k: calls.append(a) or real(*a, **k))
    _stub_attach(monkeypatch, [])
    ev = _v2_events()[CE_EVENT]
    run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
              filing_provider=FakeFilingProvider(),
              reader=_xbrl_reader(ev, CE_EVENT))
    assert calls == [], "the route duplicated the door's own verification"


# ------------------------- F8 Core derives member_refs BEFORE the door

def test_F8_core_converts_raw_pairs_to_member_refs_before_the_attach_door(
        tmp_path, monkeypatch):
    """ChannelContractV2 §3-4. Raw `{axis,member}` stay byte-unchanged on the
    event; Core derives internal `member_refs` through the AUTHORIZED chain and
    hands the door its exact key set. `check_member_refs` stays the door's own
    test. No copied rule, no channel-authored slice_part."""
    ev = _v2_events()[CE_EVENT]
    raw_before = copy.deepcopy(ev["items"][0]["xbrl"]["dimensions"])
    # SENTINELS through the AUTHORIZED owners — calling classify_axis once while
    # inventing every token would otherwise pass (SEQ 985 item 5). Labels come
    # from the matched GRAPH row, so match_xbrl_fact is spied too.
    import driver.core.driver_member_fold as MF
    used = []
    # EXACT LIVE SHAPES (slice_menu.py:208-251, 158-164). The claim key is
    # `dims`, the matched rows carry `label`, and classify_axis returns a
    # (status, kind) TUPLE — my previous fakes returned neither, so a CORRECT
    # implementation would have crashed or seen nothing (SEQ 986 item 3).
    _spy(monkeypatch, slice_menu, "match_xbrl_fact",
         lambda claim, rows: used.append("match") or
         [{"axis": a, "member": m, "label": "MEMLABEL"}
          for (a, m) in sorted(claim["dims"])])
    _spy(monkeypatch, slice_menu, "classify_axis",
         lambda axis: used.append("classify") or ("slice", "SENTINELKIND"))
    _spy(monkeypatch, MF, "member_token",
         lambda kind, label: used.append("token") or f"{kind}:SENTINELTOKEN")
    handed = _stub_attach(monkeypatch, [])
    run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
              filing_provider=FakeFilingProvider(),
              reader=_xbrl_reader(ev, CE_EVENT))
    assert handed, "the XBRL door was never called"
    for it in handed[0]:
        assert set(it) == set(xbrl_attach._EVENT_ITEM_KEYS), sorted(it)
        for ref in it["member_refs"]:
            assert sorted(ref) == ["axis", "member", "slice_part"], sorted(ref)
            assert "SENTINELTOKEN" in ref["slice_part"], (
                "slice_part did not come from the authorized token owner: "
                f"{ref['slice_part']!r}")
    assert ev["items"][0]["xbrl"]["dimensions"] == raw_before, "raw pairs mutated"
    # All THREE owners on this control's path. `encode_unknown_axis` is NOT
    # claimed: this test supplies no unknown-axis control, and its own component
    # tests already own that branch.
    assert {"match", "classify", "token"} <= set(used), (
        f"the authorized chain was bypassed; owners actually called: {sorted(set(used))}")


# ------------------- R1 (SEQ 1012): the reader may not rewrite the event ----

def test_R1_a_reader_cannot_mutate_the_event_core_trusts_and_audits(
        tmp_path, monkeypatch):
    """REPRODUCED BY THE REVIEWER: `reader(**view, item=raw)` handed out ALIASES
    to the exact mutable event Core later trusts and audits. A reader that
    rewrote its raw quote `alpha` -> `beta` got `written` back, mutated the
    CALLER's object, and the audit recorded `beta` as if it had been submitted.

    Core must work from ONE trusted deep snapshot taken before validation, and
    the reader must receive independent copies. Three things are asserted
    together, because any one alone can pass while the hole is open:
      1. the CALLER's event bytes are unchanged;
      2. the TRUSTED quote Core acts on is the submitted one;
      3. the AUDIT records the submitted one.
    """
    ev = _text_event("T-R1", ["alpha"])
    before = copy.deepcopy(ev)

    def hostile(**kw):
        kw["item"]["quote"] = "beta"                    # rewrite the raw item
        kw["item"]["raw_label_or_claim"] = "beta"
        kw["text_parts"][0]["content"] = "beta"         # and the evidence text
        return _reply("T-R1", [_text_fact(before, {"quote": "alpha"})])

    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=hostile)
    assert ev == before, "the reader mutated the CALLER's event"
    row, = result["items"]
    assert row["decision"] == "written", row
    blob = "".join(p.read_text(encoding="utf-8")
                   for p in sorted(tmp_path.rglob("*.json")))
    assert "beta" not in blob, "the audit recorded reader-injected bytes"
    assert "alpha" in blob, "the audit lost the submitted quote"


def test_R1_the_lawful_reader_still_sees_the_real_view_and_item(tmp_path):
    """The control that stops R1 from being satisfied by handing the reader
    nothing: it must still receive the true event view and its own raw item."""
    ev = _text_event("T-R1OK", ["alpha"])
    seen = {}

    def reader(**kw):
        seen.update(item=dict(kw["item"]),
                    parts=copy.deepcopy(kw["text_parts"]),
                    source_id=kw["source_id"])
        return _reply("T-R1OK", [_text_fact(ev, kw["item"])])

    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=reader)
    assert seen["item"] == ev["items"][0], seen["item"]
    assert seen["parts"] == ev["text_parts"], seen["parts"]
    assert seen["source_id"] == "T-R1OK"
    assert result["items"][0]["decision"] == "written", result["items"]


# ------- R2 (SEQ 1012): the reader's lane must match the STORED Driver -------

def test_R2_a_fact_type_disagreeing_with_the_stored_driver_parks(tmp_path):
    """REPRODUCED BY THE REVIEWER: a reader fact declaring `fact_type=guidance`
    attached to a stored Driver whose `fact_type` is `metric` came back
    `written`. S4 Step 3 (lines 55-57) requires name AND fact_type agreement,
    and a mismatch parks. This reuses the EXISTING `DRIVER_NOT_READY` branch —
    no new rule, no new code."""
    ev = _text_event("T-R2", ["alpha", "beta"], content="alpha beta")
    calls = []

    def reader(**kw):
        calls.append(1)
        # OTHERWISE A LAWFUL METRIC FACT — only the declared lane disagrees.
        # Making it guidance-SHAPED too would be caught by the validator for
        # unrelated reasons and would not reproduce the reported hole: the
        # declared `fact_type` is simply never compared to the stored Driver's.
        over = {"fact_type": "guidance"} if len(calls) == 1 else {}
        return _reply("T-R2", [_text_fact(ev, kw["item"], **over)])

    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert rows[0]["decision"] == "parked", rows[0]
    assert rows[0]["codes"] == ["DRIVER_NOT_READY"], rows[0]
    assert "fact_type" in (rows[0]["detail"] or ""), rows[0]
    assert rows[1]["fact_id"], ("the lawful sibling was lost", rows[1])


def test_R2_the_matching_lane_is_still_accepted(tmp_path, monkeypatch):
    """Both doors keep working when the lane agrees — the control that stops R2
    from being satisfied by parking everything."""
    ev = _text_event("T-R2OK", ["alpha"])
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-R2OK",
                                                  [_text_fact(ev, kw["item"])]))
    assert result["items"][0]["decision"] == "written", result["items"]
    # the XBRL door shares the one conversion-loop check
    _stub_attach(monkeypatch, [])
    ce = _v2_events()[CE_EVENT]
    xev = {**ce, "items": [copy.deepcopy(ce["items"][0])]}
    xres = run_event(xev, store=MatchingGraphStore(xev), audit_dir=str(tmp_path),
                     filing_provider=FakeFilingProvider(),
                     reader=_xbrl_reader(xev, CE_EVENT))
    assert xres["items"][0]["decision"] == "written", xres["items"]


# ---- R4 (SEQ 1012): one entry, two contracts — neither may ignore the other

def _v1_input():
    """The smallest lawful V1 run input, built through its own owner."""
    from driver.core.prepared_fact import RunInputV1
    from driver.core.test_driver_write_cli import SRC, fact as v1_fact
    return RunInputV1.from_dict({"source_id": SRC, "facts": [v1_fact()]})


@pytest.mark.parametrize("kw", [
    {"admissions": {}}, {"lock_path": "/tmp/x"}, {"period_lookups": {}},
    {"input_bytes": b"{}"}, {"raw_origin": ()}, {"n_raw": 0},
    {"raw_terminals": ({"index": 0},)}])
def test_R4_the_V2_route_refuses_arguments_that_belong_to_V1(kw, tmp_path):
    """REPRODUCED BY THE REVIEWER: V2 silently IGNORED V1's `admissions`,
    raw-accounting and input controls and still returned `written`. A supplied
    argument that changes nothing is a wiring bug the caller cannot see."""
    ev = _text_event("T-R4A", ["alpha"])
    with pytest.raises(RuntimeError):
        run_event(ev, store=BombStore(), audit_dir=str(tmp_path),
                  reader=lambda **k: pytest.fail("reached the reader"), **kw)


@pytest.mark.parametrize("kw", [
    {"reader": lambda **k: None}, {"filing_provider": object()}])
def test_R4_the_V1_route_refuses_arguments_that_belong_to_V2(kw, tmp_path):
    """The other direction, equally reproduced: V1 ignored `reader` and
    `filing_provider` outright."""
    with pytest.raises(RuntimeError):
        run_event(_v1_input(), store=FakeStore(), audit_dir=str(tmp_path), **kw)


def test_R4_each_route_still_accepts_its_OWN_arguments(tmp_path):
    """The control that stops R4 from being satisfied by refusing everything."""
    ev = _text_event("T-R4OK", ["alpha"])
    res = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                    reader=lambda **kw: _reply("T-R4OK",
                                               [_text_fact(ev, kw["item"])]),
                    filing_provider=None)
    assert res["items"][0]["decision"] == "written", res["items"]
    v1 = run_event(_v1_input(), store=FakeStore(), audit_dir=str(tmp_path),
                   raw_origin=(0,), n_raw=1)
    assert v1["status"] == "dry_run", v1


# ---- R7 (SEQ 1012): derive once, read once per concept per event -----------

def test_R7_one_enrichment_read_per_concept_and_one_pair_derivation_per_item(
        tmp_path, monkeypatch):
    """All four CE raw items carry the SAME concept, so the route owes ONE
    enrichment read for the event — it was making four. And the raw dimension
    pair is owned by `axis_member_pairs`, already computed in the pure check;
    recomputing it per item called the rule twice for every item.

    Both are counted through the public route on the real four-item event."""
    reads, pairs = [], []
    ev = _v2_events()[CE_EVENT]
    assert len({i["xbrl"]["concept"] for i in ev["items"]}) == 1, "fixture drift"

    class CountingStore(MatchingGraphStore):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            reads.append(concept)
            return super().get_xbrl_fact_dimensions(source_id, concept)

    # Counted in the ROUTE's namespace only. `slice_menu.match_xbrl_fact`
    # legitimately calls the same owner once per GRAPH ROW it compares — that is
    # the owner using its own rule, not the route deriving the raw pair twice.
    # Patching the shared module would count those and measure the wrong thing.
    real_pairs = slice_menu.axis_member_pairs
    monkeypatch.setattr(CLI, "axis_member_pairs",
                        lambda dims: (pairs.append(1), real_pairs(dims))[1])
    _stub_attach(monkeypatch, [])
    run_event(ev, store=CountingStore(ev), audit_dir=str(tmp_path),
              filing_provider=FakeFilingProvider(),
              reader=_xbrl_reader(ev, CE_EVENT))
    assert len(reads) == 1, f"one concept, {len(reads)} enrichment reads: {reads}"
    assert len(pairs) == len(ev["items"]), (
        f"{len(ev['items'])} raw items but the pair rule ran {len(pairs)} times")


# ---- R8 (SEQ 1012): the fixed literals must BE the contract's ---------------

def test_R8_the_production_V2_tuples_equal_the_staged_contract_block():
    """WHAT AUTHORIZES THE FIXED STRINGS. `test_v2_attacks` reads the machine
    block but deliberately SKIPS `staged_raw_channel`, on the stated premise
    that "that boundary is unbuilt". These `V2_*` tuples ARE that boundary now,
    so the premise died — the same way T10's did in R5.

    The contract side is read through the attacks' OWN existing loader and the
    production side off the live module. Nothing is re-typed here: a
    hand-written third list would just be a copy that can drift with the code.
    Production never parses markdown; only this test reads the document.
    """
    from driver.core.test_v2_attacks import _v2_contract_block, _v2_contract_bytes
    from driver.core.xbrl_attach import _event_part_lookup
    raw = dict(_v2_contract_block(
        _v2_contract_bytes().decode("utf-8")))["staged_raw_channel"]

    assert list(CLI.V2_EVENT_FIELDS) == raw["event_fields"]
    assert list(CLI.V2_ITEM_ALLOWED) == raw["item_fields_after_retirement"]
    assert list(CLI.V2_XBRL_FIELDS) == raw["xbrl_fields"]
    assert list(CLI.V2_IX_FIELDS) == raw["ix_fields"]
    assert list(CLI.V2_DIM_FIELDS) == raw["dimension_fields"]

    # TEXT PARTS through the OWNER, not a fourth tuple: `_event_part_lookup` is
    # what the route actually calls, so feeding it a part built from the
    # contract's own field names proves the owner accepts exactly that shape.
    part = {f: "x" for f in raw["text_part_fields"]}
    assert _event_part_lookup([part]) == {"x": "x"}, raw["text_part_fields"]


# ---- R9 (SEQ 1012): ONE item through the REAL door, not a stub --------------

@pytest.mark.live
def test_R9_one_real_dimensioned_item_crosses_the_ACTUAL_door_to_the_planner(
        tmp_path, monkeypatch):
    """`test_F3_all_11_real_v2_xbrl_items...` STUBS `attach_event_xbrl`, so it
    proves route indexing, not the door. This runs ONE real dimensioned CE item
    through the ACTUAL door -> conversion -> validator -> planner, using the
    door suite's OWN cached filing and read-only adapter helper — no new fake,
    provider or proof framework, and no claim that all eleven crossed.

    STATED LIMIT, not papered over: the live graph has NO `Driver` label at all
    before the switch (verified — `get_driver` returns None and Neo4j reports
    the label as absent), so the Driver lookup is the one seam wrapped here.
    Everything else is real: the real store's source, companies and enrichment
    rows, the real cached filing document, and the real attach door.
    """
    from driver.relocation.test_real_726_end_to_end import (
        ACCESSION, _filing_text, store_or_skip)
    real_store = store_or_skip(ACCESSION)
    rec = _recorded()[f"{CE_EVENT}#0"]

    class _OneDriverStore:
        """The real store, plus the ONE Driver the pre-switch graph lacks."""
        def __init__(self, inner):
            self._inner = inner
            self.tx_opened = 0

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def get_driver(self, name):
            return {"name": name, "fact_type": rec.get("fact_type", "metric")}

        def transaction(self):
            self.tx_opened += 1
            raise AssertionError("the dry-run route opened a write transaction")

    class _CachedFiling:
        def get_filing_document(self, source_id):
            return _filing_text() if source_id == ACCESSION else None

    ce = _v2_events()[CE_EVENT]
    ev = {**ce, "items": [copy.deepcopy(ce["items"][0])]}
    dims = ev["items"][0]["xbrl"]["dimensions"]
    store = _OneDriverStore(real_store)
    concept = ev["items"][0]["xbrl"]["concept"]

    def graph_snapshot():
        rows = real_store.get_xbrl_fact_dimensions(ACCESSION, concept).rows
        return json.dumps(rows, sort_keys=True, default=str)

    before = graph_snapshot()
    plans = _plan_spy(monkeypatch)
    result = run_event(ev, store=store, audit_dir=str(tmp_path),
                       filing_provider=_CachedFiling(),
                       reader=_xbrl_reader(ev, CE_EVENT))
    after = graph_snapshot()

    # The route imports the door FUNCTION-LOCALLY, so the only way it can be a
    # stub is if the owning module's attribute was replaced. This control never
    # calls `_stub_attach`; the assertion pins that no other fixture did.
    assert xbrl_attach.attach_event_xbrl.__module__ == "driver.core.xbrl_attach", (
        "the door was stubbed — this control exists to run the real one")
    row, = result["items"]
    assert row["decision"] == "written", row
    edges = [o for r in plans["results"] for o in r.ops
             if o.get("type") == "MAPS_TO_MEMBER"]
    assert len(edges) == len(dims), (len(edges), len(dims))
    assert {e["to"] for e in edges} == {d["member"] for d in dims}, edges
    assert before == after, "the read-only probe changed the graph"
    assert store.tx_opened == 0, "a write transaction was opened"


# ==== OD-21 PRE-FUSION ORDER (Codex SEQ 1016) ===============================
# Live authority, not a new rule: FINAL_DESIGN:152-153 (code composes surprise
# BEFORE fusion; an actual surprise before period end REJECTS), BUILD:236 (the
# OD-21 traps validate before fusion with the RIGHT reason), BUILD:814-821
# (canonicalize before fusion; fusion fills lawful nulls; ambiguity parks).
#
# Measured denominator before the fix (three fragments, partially conflicting,
# every fragment carrying the SAME defect — see sendgate/six_case_denominator_854.py):
#   F1 F2 F3 F7 -> parked/FUSION_AMBIGUOUS   (MASKED: fusion parked the group)
#   F4 F5       -> parked/SURPRISE_COMPOSE   (MISCLASSIFIED: park, not F4/F5)
# A defect fusion CANNOT repair must be rejected with its own code first.

_SUR_BASE = dict(fact_type="surprise", driver_name="revenue_surprise",
                 driver_state="beat", surprise_basis_hint="actual",
                 comparison_baseline="consensus",
                 comparison_low=slot(90), comparison_high=slot(90),
                 comparison_shape_hint="point", level_unit="count")
_ENDED = dict(time_type="duration", period_start_date="2023-01-01",
              period_end_date="2023-12-31", fiscal_year=2023)
_FUTURE = dict(time_type="duration", period_start_date="2026-01-01",
               period_end_date="2026-12-31", fiscal_year=2026)


def _three_fragment_run(tmp_path, over, sid):
    """The shape that makes fusion park a group whole: a vs b conflict on the
    level, c is numberless and conflicts with neither."""
    ev = _text_event(sid, ["a", "b", "c"], content="a b c")
    levels = {"a": 100, "b": 200, "c": None}

    def reader(**kw):
        v = levels[kw["item"]["quote"]]
        o = dict(over)
        if v is not None:
            o.update(level_low=slot(v), level_high=slot(v),
                     level_shape_hint="point")
        return _reply(sid, [_text_fact(ev, kw["item"], **o)])

    return run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                     reader=reader)


# EXACT ORDERED SETS, never membership (SEQ 1017). `F2 or F3` would still pass
# after one of the two rules silently disappeared, which is precisely the drift
# these controls exist to catch. The expected list is what the SHARED OD-21
# owner returns for each input, in its own order.
@pytest.mark.parametrize("case,codes,over", [
    # F1's public expression at this boundary IS the missing basis hint: the
    # `surprise=` slot does not exist until code composes it, so the owner's
    # answer here is F3. F1's own slot-mismatch check stays post-conversion.
    ("F1 surprise= missing", ["F3"],
     dict(_SUR_BASE, **_ENDED, surprise_basis_hint=None)),
    # F2's expression is a basis hint on a NON-surprise lane — the existing
    # off-lane rule, which the owner reports as F3.
    ("F2 surprise= off-lane", ["F3"],
     dict(_ENDED, fact_type="metric", driver_name="revenue",
          driver_state="reported", surprise_basis_hint="actual",
          comparison_baseline="consensus", comparison_low=slot(90),
          comparison_high=slot(90), comparison_shape_hint="point",
          level_unit="count")),
    ("F3 basis hint missing", ["F3"],
     dict(_SUR_BASE, **_ENDED, surprise_basis_hint=None)),
    ("F4 baseline missing", ["F4"],
     dict(_SUR_BASE, **_ENDED, comparison_baseline=None)),
    ("F5 guidance+previous_guidance", ["F5"],
     dict(_SUR_BASE, **_ENDED, surprise_basis_hint="guidance",
          comparison_baseline="previous_guidance")),
    ("F7 impossible tense", ["F7"], dict(_SUR_BASE, **_FUTURE)),
])
def test_OD21_a_defect_decidable_before_fusion_is_REJECTED_with_its_exact_codes(
        case, codes, over, tmp_path):
    """Every fragment carries the SAME defect. The route must publish the EXACT
    code list — not FUSION_AMBIGUOUS, not a generic park, and not merely a set
    that happens to contain the right code."""
    result = _three_fragment_run(tmp_path, over, f"OD-{case[:2]}")
    assert [r["index"] for r in result["items"]] == [0, 1, 2], result["items"]
    for row in result["items"]:
        assert row["decision"] == "rejected", (case, row)
        assert row["codes"] == codes, (case, row["codes"], codes)


def test_OD21_fusion_still_COMPLETES_a_lawful_complementary_fragment(tmp_path):
    """THE CONTROL THAT BOUNDS THE FIX. A lawful surprise split across two
    fragments — one carries the comparison, the other the level — must still
    FUSE into one accepted fact. Rejecting incomplete-but-lawful fragments
    before fusion is exactly what this ordering must NOT do."""
    q_home, q_sur = "revenue of 100", "beat consensus of 90"
    ev = _text_event("OD-OK", [q_home, q_sur, "and again"],
                     content=f"{q_home} {q_sur} and again")
    full = dict(_SUR_BASE, **_ENDED, level_low=slot(100), level_high=slot(100),
                level_shape_hint="point")
    partial = dict(_SUR_BASE, **_ENDED)          # comparison only, no level yet

    def reader(**kw):
        q = kw["item"]["quote"]
        if q == q_home:
            return _reply("OD-OK", [_text_fact(
                ev, kw["item"], driver_name="revenue", level_unit="count",
                level_low=slot(100), level_high=slot(100),
                level_shape_hint="point", **_ENDED)])
        over = full if q == q_sur else partial
        return _reply("OD-OK", [_text_fact(ev, kw["item"], **over)])

    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert rows[1]["decision"] == "written", rows[1]
    assert rows[2]["decision"] == "written", rows[2]
    assert rows[1]["fact_id"] == rows[2]["fact_id"], "the lawful pair did not fuse"


def test_OD21_the_lawful_fusion_result_is_permutation_identical(tmp_path):
    """Order must not change the outcome — BUILD:814-821."""
    def outcome(order):
        ev = _text_event("OD-PERM", list(order), content=" ".join(order))
        full = dict(_SUR_BASE, **_ENDED, level_low=slot(100),
                    level_high=slot(100), level_shape_hint="point")
        partial = dict(_SUR_BASE, **_ENDED)

        def reader(**kw):
            over = full if kw["item"]["quote"] == "rich" else partial
            return _reply("OD-PERM", [_text_fact(ev, kw["item"], **over)])

        res = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                        reader=reader)
        return sorted((r["decision"], r["fact_id"]) for r in res["items"])

    assert outcome(("rich", "thin")) == outcome(("thin", "rich"))


# ----------------------------------------------------- F9 the one validator

def test_F9_every_surviving_prepared_fact_reaches_the_one_validator_once(
        tmp_path, monkeypatch):
    """The one-validator claim has TWO legs now that FUSION sits between
    conversion and validation (V1's ordering): every door fact is CONVERTED
    exactly once, and every fused group is VALIDATED exactly once — no more, no
    fewer. The counts are taken against what the DOOR returned, not against
    final rows carrying a fact_id, which would let a writer that drops every
    validated fact make both sides zero and still "correspond" (SEQ 986 item 4).

    It used to spy `validate_via_production`. The route calls that composite's
    two halves at their two correct points instead, so spying it now would
    measure a function nothing calls and pass at zero.
    """
    converted, validated = [], []
    real_conv = prepared_fact_v2.to_stored_fact
    real_val = driver_validators.validate_fact

    def conv(f, **k):
        stored = real_conv(f, **k)
        converted.append(stored)
        return stored

    def val(f, **k):
        validated.append(f["id"])
        return real_val(f, **k)

    _spy(monkeypatch, prepared_fact_v2, "to_stored_fact", conv)
    _spy(monkeypatch, driver_validators, "validate_fact", val)
    handed = _stub_attach(monkeypatch, [])
    ev = _v2_events()[CE_EVENT]
    run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
              filing_provider=FakeFilingProvider(),
              reader=_xbrl_reader(ev, CE_EVENT))
    n_door = sum(len(sub) for sub in handed)
    assert n_door and len(converted) == n_door, (len(converted), n_door)
    assert sorted(validated) == sorted({f["id"] for f in converted}), \
        (validated, [f["id"] for f in converted])


def test_F9_one_bad_sibling_stays_local_to_its_own_raw_position(tmp_path):
    """The bad one is selected by a CALLER-SIDE counter — the reader is never
    told its raw index (SEQ 984 item 1)."""
    ev = _text_event("T-9", ["alpha", "beta"])
    calls = []

    def reader(**kw):
        calls.append(1)
        # LAWFULLY SHAPED, but names a Driver the store does not carry -> the
        # validator's own DRIVER_NOT_READY. A schema-malformed fact would be a
        # violation of the injected seam's contract, which hard-errors by design
        # and has no registered Core code (nothing is minted for it).
        f = _text_fact(ev, kw["item"],
                       **({"driver_name": "not_a_stored_driver"}
                          if len(calls) == 1 else {}))
        return _reply("T-9", [f])

    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path), reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert set(rows) == {0, 1}
    # BOTH halves, or the test proves nothing: the bad row must actually be
    # refused AND the lawful sibling must actually survive (SEQ 985 tail).
    assert rows[0]["decision"] in ("rejected", "parked"), rows[0]
    assert rows[0]["codes"], "a public terminal with no machine code"
    assert rows[1]["decision"] not in ("rejected", "parked"), (
        "a lawful sibling was taken down with its bad neighbour")
    assert rows[1]["fact_id"], "the lawful sibling produced no fact"


# ------------------------------- F10 full internal handoff, 5-field public out

def test_F10_the_public_rows_carry_exactly_the_five_published_fields(
        tmp_path, monkeypatch):
    _stub_attach(monkeypatch, [])
    ev = _v2_events()[CE_EVENT]
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_xbrl_reader(ev, CE_EVENT))
    assert "raw_accounting" not in result, "the route widened public output"
    for row in result["items"]:
        assert sorted(row) == ["codes", "decision", "detail", "fact_id", "index"]


def test_F10_the_route_freezes_the_complete_origin_n_raw_terminals_triple(
        tmp_path, monkeypatch):
    """The WHOLE handoff, not two of its three members."""
    seen = {}
    real = CLI._freeze_raw_accounting

    def spy(raw_origin, n_raw, raw_terminals, n_facts):
        seen.update(origin=raw_origin, n_raw=n_raw, terminals=raw_terminals)
        return real(raw_origin, n_raw, raw_terminals, n_facts)

    monkeypatch.setattr(CLI, "_freeze_raw_accounting", spy)
    _stub_attach(monkeypatch, [])
    ev = _v2_events()[CE_EVENT]
    run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
              filing_provider=FakeFilingProvider(),
              reader=_xbrl_reader(ev, CE_EVENT))
    assert sorted(seen["origin"]) == [0, 1, 2, 3]
    assert seen["n_raw"] == 4
    # EXACT: this event has four lawful XBRL items and the stub returns a fact
    # for every one, so there is no zero-fact raw position and the terminal set
    # must be EMPTY. `== () or all(...)` would have passed on any content.
    assert list(seen["terminals"]) == [], seen["terminals"]


def test_F10_a_preflight_failure_remaps_to_its_raw_position_and_reaches_accounting(
        tmp_path, monkeypatch):
    """FAMILY-8 obligation. The door returns NO fact for subset index 0 and one
    existing five-field preflight row instead. That row must surface at the
    item's ORIGINAL raw position (1 in this mixed event) and must reach the
    `(origin, n_raw, terminals)` seam — the successful F10 has terminals=[] and
    cannot prove it. Code reused from registered ATTACH_CODES; nothing minted.
    """
    from driver.core.outcome_codes import ATTACH_CODES
    ce = _v2_events()[CE_EVENT]
    body = ce["text_parts"][0]["content"]
    ev = {**ce, "items": [{"quote": "alpha", "raw_label_or_claim": "alpha"},
                          copy.deepcopy(ce["items"][0]),
                          {"quote": "gamma", "raw_label_or_claim": "gamma"}],
          "text_parts": [{"part": ce["text_parts"][0]["part"],
                          "content": body + " alpha gamma"}]}

    def failing_door(items, *, source_id, **kw):
        return xbrl_attach.AttachResult(
            source_id=source_id, facts=[],          # NO fact for that item
            preflight_outcomes=[{"index": 0, "fact_id": None,
                                 "decision": "parked",
                                 "codes": [ATTACH_CODES[0]],
                                 "detail": "representative preflight failure"}],
            member_menu={"folds": {}, "exclusions": []})
    _spy(monkeypatch, xbrl_attach, "attach_event_xbrl", failing_door)

    seen = {}
    real = CLI._freeze_raw_accounting
    monkeypatch.setattr(CLI, "_freeze_raw_accounting",
                        lambda o, n, t, nf: seen.update(origin=o, n_raw=n,
                                                        terminals=t)
                        or real(o, n, t, nf))
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_mixed_reader(ev))
    rows = {r["index"]: r for r in result["items"]}
    assert set(rows) == {0, 1, 2}
    assert rows[1]["decision"] == "parked", rows[1]      # SUBSET 0 -> RAW 1
    assert rows[1]["codes"] == [ATTACH_CODES[0]], rows[1]
    assert sorted(rows[1]) == ["codes", "decision", "detail", "fact_id", "index"]
    assert seen["n_raw"] == 3
    assert [t["index"] for t in seen["terminals"]] == [1], seen["terminals"]


def test_F10_the_doors_member_menu_audit_reaches_the_write_ahead_audit(
        tmp_path, monkeypatch):
    """#825 evidence must not disappear at the new route. The door's real frozen
    `{folds, exclusions}` result carries one distinctive record; the route must
    hand it to the existing write-ahead audit owner WITHOUT adding a public
    field. Member RULES are not retested — that is the door's own suite."""
    ev = _v2_events()[CE_EVENT]
    marker = "SENTINEL-FOLD-NOTE"

    def door(items, *, source_id, **kw):
        items = list(items)
        built = [(i, prepared_fact_v2.PreparedFactV2._build(
            it["fact"], {"xbrl_concept_raw": it["concept"],
                         "member_refs": it["member_refs"]}))
            for i, it in enumerate(items)]
        return xbrl_attach.AttachResult(
            source_id=source_id, facts=built, preflight_outcomes=[],
            member_menu={"folds": {"0": [marker]}, "exclusions": [marker]})
    _spy(monkeypatch, xbrl_attach, "attach_event_xbrl", door)

    # Asserted on the DURABLE FILE, not on a constructor payload. R6 (SEQ 1012)
    # moved the audit open to before the source gate, so Core's own derived
    # bookkeeping — raw accounting and the door's member_menu — now lands by
    # `update()`. Spying the constructor tested the delivery MECHANISM; the
    # claim was always about what survives in the audit.
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_xbrl_reader(ev, CE_EVENT))
    doc = _audit_doc(tmp_path)
    assert marker in json.dumps(doc, default=str), (
        "the door's member_menu audit result did not reach the audit file")
    for row in result["items"]:                    # and no public field grew
        assert sorted(row) == ["codes", "decision", "detail", "fact_id", "index"]



# ------------------------------------------------------------- F11 dry-run

def test_F11_the_dry_run_reads_what_it_needs_and_writes_nothing(tmp_path, monkeypatch):
    """Against FakeStore's REAL owners. The previous version asserted
    `getattr(store,'writes',None) == None`, which was vacuous — FakeStore has no
    `writes` attribute, so it passed whatever happened (SEQ 984 item 5)."""
    _stub_attach(monkeypatch, [])
    ev = _v2_events()[CE_EVENT]
    store = _mirror_fake(ev)
    before = (copy.deepcopy(store.applied), copy.deepcopy(store.facts),
              copy.deepcopy(store.drivers))
    run_event(ev, store=store, audit_dir=str(tmp_path), enable_writes=False,
              filing_provider=FakeFilingProvider(),
              reader=_xbrl_reader(ev, CE_EVENT))
    assert (store.applied, store.facts, store.drivers) == before, \
        "the dry-run route mutated the store"


class InterfaceOnlyStore:
    """THE REAL ADAPTER SURFACE AND NOTHING ELSE.

    `Neo4jStore` has NONE of FakeStore's convenience attributes (`source`,
    `drivers`, `xbrl_facts`, `filing_provider`) — verified against
    driver_neo4j_adapter. Reading those attributes made the route work only
    against the double (SEQ 991 item 1). This store deliberately withholds them
    so that regression cannot come back silently.

    The READ methods below are the real adapter's, checked against
    `dir(Neo4jStore)`. `get_sibling_facts` / `get_period` /
    `get_prior_guide_units` were missing while the route stopped at `prepared`;
    the planner needs them and the REAL store has them, so their absence here
    was a gap in the double, not a route reaching for a convenience.
    """

    def __init__(self):
        self.applied = []

    def __getattr__(self, name):                 # any convenience attr is a bug
        raise AssertionError(
            f"the route read `store.{name}` — a FakeStore-only convenience the "
            f"real Neo4jStore does not have")

    def get_source(self, source_id):
        return {"date": "2026-01-01T00:00:00Z", "source_type": "8k",
                "ticker": "X", "fye_month": 12}

    def get_source_companies(self, source_id):
        return ["X"]

    def get_driver(self, name):
        return {"name": name, "fact_type": "metric"}

    def get_xbrl_fact_dimensions(self, source_id, concept):
        from driver.core.driver_neo4j_adapter import GraphFactRows
        return GraphFactRows(rows=[], exclusions=())

    def get_sibling_facts(self, bare_id):
        return []

    def get_period(self, period_id):
        return None

    def get_prior_guide_units(self, fact):
        return []


def test_F13_the_interface_double_matches_the_REAL_adapters_read_surface():
    """The double may not quietly drift from the store the route really runs
    against: every read method it claims must exist on `Neo4jStore`."""
    from driver.core.driver_neo4j_adapter import Neo4jStore
    declared = {n for n in vars(InterfaceOnlyStore) if n.startswith("get_")}
    missing = declared - set(dir(Neo4jStore))
    assert not missing, f"the double invented reads Neo4jStore lacks: {missing}"


def test_F1_the_route_runs_on_the_REAL_adapter_surface_only(tmp_path):
    """Interface-only control: no FakeStore conveniences exist on this store."""
    ev = _text_event("T-IF", ["alpha"])
    result = run_event(ev, store=InterfaceOnlyStore(), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-IF",
                                                  [_text_fact(ev, kw["item"])]))
    assert [r["index"] for r in result["items"]] == [0]


class _GateStore(InterfaceOnlyStore):
    """Interface-only, with the source gate under test."""

    @classmethod
    def mirroring(cls, event, **kw):
        """A store whose stored source ECHOES this event's envelope, so the
        control exercises its own path rather than the mismatch guard."""
        return cls(stype=event["source_type"], ticker=event["ticker"],
                   fye=event["fye_month"], companies=(event["ticker"],),
                   stamp=event["event_time"], **kw)

    def __init__(self, source=..., companies=("X",), fye=12, stype="8k",
                 ticker="X", stamp="2026-01-01T00:00:00Z"):
        super().__init__()
        self._src = ({"date": stamp, "source_type": stype,
                      "ticker": ticker, "fye_month": fye} if source is ...
                     else source)
        self._companies = list(companies)

    def get_source(self, source_id):
        return self._src

    def get_source_companies(self, source_id):
        return self._companies


def _audit_doc(tmp_path):
    """THE one write-ahead audit file the run produced. BUILD 804-845: one
    unique never-overwritten file per RUN — so a run that returns a public
    result and writes nothing has skipped a required durable record."""
    files = sorted(p for p in tmp_path.rglob("*.json")
                   if not p.name.endswith(".tmp"))
    assert len(files) == 1, [str(p) for p in files]
    return json.loads(files[0].read_text(encoding="utf-8"))


def test_F1_a_missing_stored_source_rejects_every_raw_item(tmp_path):
    """Source-first, exactly as V1: no stored source -> every affected raw item
    rejected/SOURCE_MISSING, and raw accounting still covers them all.

    R6 (SEQ 1012): this gate returned a public result with ZERO audit files."""
    ev = _text_event("T-NOSRC", ["alpha", "beta"])
    result = run_event(ev, store=_GateStore(source=None), audit_dir=str(tmp_path),
                       reader=lambda **kw: pytest.fail("gated before the reader"))
    assert [r["index"] for r in result["items"]] == [0, 1]
    for r in result["items"]:
        assert r["decision"] == "rejected" and r["codes"] == ["SOURCE_MISSING"]
    assert result["status"] == "failed", result
    assert result["code"] == "SOURCE_MISSING", result
    doc = _audit_doc(tmp_path)
    assert doc["state"] == "failed", doc["state"]
    assert doc["code"] == "SOURCE_MISSING", doc
    assert doc["results"] == result["items"], doc["results"]


def test_F1_an_ambiguous_source_company_parks_every_raw_item(tmp_path):
    ev = _text_event("T-AMB", ["alpha", "beta"])
    result = run_event(ev, store=_GateStore(companies=("X", "Y")),
                       audit_dir=str(tmp_path),
                       reader=lambda **kw: pytest.fail("gated before the reader"))
    assert [r["index"] for r in result["items"]] == [0, 1]
    for r in result["items"]:
        assert r["decision"] == "parked"
        assert r["codes"] == ["SOURCE_COMPANY_AMBIGUOUS"]
    assert result["status"] == "dry_run", result
    doc = _audit_doc(tmp_path)
    assert doc["state"] == "dry_run", doc["state"]
    assert doc["results"] == result["items"], doc["results"]


def test_F1_the_STORED_fye_wins_over_the_channel_envelope(tmp_path, monkeypatch):
    """Graph-owned validation metadata is not overridable by the channel."""
    seen = {}
    real = prepared_fact_v2.to_stored_fact
    _spy(monkeypatch, prepared_fact_v2, "to_stored_fact",
         lambda f, **k: seen.update(fye=k.get("fye_month")) or real(f, **k))
    ev = {**_text_event("T-FYE", ["alpha"]), "fye_month": 3}   # envelope says 3
    # The channel may only ECHO graph-owned metadata. A conflicting fye_month is
    # now REFUSED before the reader instead of silently steering it (SEQ 997 B).
    with pytest.raises(prepared_fact_v2.SchemaError) as ei:
        run_event(ev, store=_GateStore(fye=12, stamp=ev["event_time"]),
                  audit_dir=str(tmp_path),
                  reader=lambda **kw: _reply("T-FYE", [_text_fact(ev, kw["item"])]))
    assert "fye_month" in str(ei.value), str(ei.value)
    assert seen == {}, "preparation ran despite a stored-metadata conflict"


def test_F2_a_text_only_event_needs_no_filing_provider(tmp_path):
    """The provider is required only when an XBRL subset exists."""
    ev = _text_event("T-TXT", ["alpha"])
    result = run_event(ev, store=_GateStore.mirroring(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-TXT",
                                                  [_text_fact(ev, kw["item"])]))
    assert [r["index"] for r in result["items"]] == [0]


def test_F5_an_xbrl_event_without_a_filing_provider_fails_closed(tmp_path):
    """Neo4jStore does not own get_filing_document (test_round8_xbrl_binding),
    so the provider is a separate injected owner and its absence refuses."""
    ev = _v2_events()[CE_EVENT]
    with pytest.raises(Exception) as ei:
        # a MATCHING graph, so the item really reaches the door — with an empty
        # graph it would lawfully park MEMBER_LINK_INVALID first and never get
        # far enough to need a provider.
        run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                  reader=_xbrl_reader(ev, CE_EVENT))
    assert "filing_provider" in str(ei.value)


def test_F9_a_typed_preparation_failure_PARKS_with_its_registered_code(
        tmp_path, monkeypatch):
    """ChannelContractV2 §9 + ProductionValidationError's own docstring: callers
    PARK these. The code is read STRUCTURALLY off the exception — never parsed
    from its text — and nothing is minted."""
    def boom(fact, **kw):
        raise prepared_fact_v2.ProductionValidationError(
            "PERIOD_UNRESOLVED: synthetic", code="PERIOD_UNRESOLVED")
    _spy(monkeypatch, prepared_fact_v2, "to_stored_fact", boom)
    ev = _text_event("T-PARK", ["alpha"])
    result = run_event(ev, store=_GateStore.mirroring(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-PARK",
                                                  [_text_fact(ev, kw["item"])]))
    row = result["items"][0]
    assert row["decision"] == "parked" and row["codes"] == ["PERIOD_UNRESOLVED"]
    assert sorted(row) == ["codes", "decision", "detail", "fact_id", "index"]


def test_F9_an_UNCODED_preparation_error_still_propagates_loudly(
        tmp_path, monkeypatch):
    """A programming error must NOT be silently converted into a park."""
    def boom(fact, **kw):
        raise prepared_fact_v2.ProductionValidationError("no structural code")
    _spy(monkeypatch, prepared_fact_v2, "to_stored_fact", boom)
    ev = _text_event("T-LOUD", ["alpha"])
    with pytest.raises(prepared_fact_v2.ProductionValidationError):
        run_event(ev, store=_GateStore.mirroring(ev), audit_dir=str(tmp_path),
                  reader=lambda **kw: _reply("T-LOUD",
                                             [_text_fact(ev, kw["item"])]))


# --- the THREE REAL preparation branches, through public run_event ----------
# Each drives the ACTUAL emitter in prepared_fact_v2, never a synthetic
# already-coded exception, and each keeps ONE lawful sibling that must still be
# prepared (SEQ 993 item 2).

def _two_item_event(sid, bad_over, quotes=("alpha", "beta")):
    ev = _text_event(sid, list(quotes), content=" ".join(quotes))
    calls = []

    def reader(**kw):
        calls.append(1)
        over = bad_over if len(calls) == 1 else {}
        return _reply(sid, [_text_fact(ev, kw["item"], **over)])
    return ev, reader


# THE SURPRISE-COMPOSE ROW MOVED OUT, and it is not a prune. It asserted
# parked/SURPRISE_COMPOSE for a malformed surprise contract. SEQ 1016 ruled
# from live authority (FINAL_DESIGN:152-153, BUILD:236) that such a contract
# REJECTS with its exact F-code before fusion, so the old expectation is
# superseded — the same input is now covered, more strictly, by the OD-21
# controls above, which demand the exact code rather than any park. The
# ProductionValidationError -> PARK path this table exists for stays proven by
# the two REAL branches below, and V1 is untouched (it already rejected).
@pytest.mark.parametrize("label,code,over,quotes", [
    ("period unresolved", "PERIOD_UNRESOLVED",
     {"time_type": "duration", "period_start_date": None,
      "period_end_date": None, "fiscal_year": None}, ("alpha", "beta")),
    # WITH evidence, so it passes CONSTRUCTION validation and fails only in
    # convert_slot's arithmetic — which is exactly the NOT_STORABLE branch.
    # 5000 nines: LAWFUL at construction (evidence sits inside the quote) but
    # its canonical stored form exceeds _MAX_STORED_CHARS=4096, so it fails only
    # in convert_slot's `assert_storable` — the real NOT_STORABLE branch.
    ("not storable", "NOT_STORABLE",
     {"level_low": {"value": Decimal("9" * 5000),
                    "scale_multiplier": Decimal("1E+6"),
                    "unit_scale_evidence": "million"},
      "level_high": {"value": Decimal("9" * 5000),
                     "scale_multiplier": Decimal("1E+6"),
                     "unit_scale_evidence": "million"},
      "level_unit": "m_usd", "level_shape_hint": "point"},
     ("revenue of 999 million", "beta")),
])
def test_F9_each_REAL_preparation_branch_parks_with_its_own_code(
        label, code, over, quotes, tmp_path):
    ev, reader = _two_item_event(f"T-{code}", over, quotes)
    result = run_event(ev, store=_GateStore.mirroring(ev), audit_dir=str(tmp_path),
                       reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert set(rows) == {0, 1}, rows
    assert rows[0]["decision"] == "parked", (label, rows[0])
    assert rows[0]["codes"] == [code], (label, rows[0])
    assert sorted(rows[0]) == ["codes", "decision", "detail", "fact_id", "index"]
    assert rows[1]["fact_id"], ("the lawful sibling was lost", label, rows[1])


# ---- SEQ 994: the four public-boundary integrity guards ---------------------

def test_F1_hostile_MIXED_TYPE_extra_keys_do_not_crash_the_guard(tmp_path):
    """`{1, "zz"}` extras must refuse cleanly. Sorting untrusted keys raised a
    raw TypeError — the defect `_check_keys` was written to end, which its own
    docstring says "survived in three doors after being fixed in one"."""
    ev = _text_event("T-MIX", ["alpha"])
    hostile = {**ev, 1: "int key", "zz": "str key"}
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(hostile, store=BombStore(), audit_dir=str(tmp_path))


def test_F1_duplicate_text_part_labels_refuse_before_any_io(tmp_path):
    """Two parts with the same label silently overwrote each other in a dict
    comprehension. The one owner refuses them, and BEFORE any store touch."""
    ev = _text_event("T-DUP", ["alpha"])
    ev["text_parts"] = [{"part": "p01", "content": "alpha"},
                        {"part": "p01", "content": "other"}]
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(ev, store=BombStore(), audit_dir=str(tmp_path),
                  reader=lambda **kw: pytest.fail("reached the reader"))


def test_F1_two_distinct_lawful_parts_remain_selectable(tmp_path):
    ev = _text_event("T-2P", ["alpha"])
    ev["text_parts"] = [{"part": "p01", "content": "alpha"},
                        {"part": "p02", "content": "beta"}]
    result = run_event(ev, store=_GateStore.mirroring(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-2P",
                                                  [_text_fact(ev, kw["item"])]))
    assert result["items"][0]["fact_id"]


def test_F8_an_unmatched_dimension_claim_parks_and_never_reaches_the_door(
        tmp_path, monkeypatch):
    """`or []` turned an unverifiable nonempty claim into VERIFIED-EMPTY. It
    must park MEMBER_LINK_INVALID, keep its lawful sibling, and never attach."""
    ce = _v2_events()[CE_EVENT]
    ev = {**ce, "items": [copy.deepcopy(ce["items"][0]),
                          {"quote": "alpha", "raw_label_or_claim": "alpha"}],
          "text_parts": [{"part": ce["text_parts"][0]["part"],
                          "content": ce["text_parts"][0]["content"] + " alpha"}]}
    handed = _stub_attach(monkeypatch, [])
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_mixed_reader(ev))
    rows = {r["index"]: r for r in result["items"]}
    assert rows[0]["decision"] == "parked"
    assert rows[0]["codes"] == ["MEMBER_LINK_INVALID"], rows[0]
    assert handed == [] or all(not sub for sub in handed), "it reached the door"
    assert rows[1]["fact_id"], "the lawful sibling was lost"


def test_F8_a_lawful_split_with_no_graph_match_owes_exactly_ONE_terminal(
        tmp_path, monkeypatch):
    """Refs are derived once per RAW item, not per fact — two facts with no
    match must not emit two terminals for one raw index (SEQ 995)."""
    ce = _v2_events()[CE_EVENT]
    ev = {**ce, "items": [copy.deepcopy(ce["items"][0])]}
    _stub_attach(monkeypatch, [])
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=lambda **kw: _reply(
                           CE_EVENT, [_xbrl_fact(ev, kw["item"], f"{CE_EVENT}#0"),
                                      _xbrl_fact(ev, kw["item"], f"{CE_EVENT}#0")]))
    assert len(result["items"]) == 1, result["items"]
    assert result["items"][0]["codes"] == ["MEMBER_LINK_INVALID"]


def test_F4_a_fact_quoting_a_DIFFERENT_in_part_string_is_refused(tmp_path):
    """Raw `alpha` receiving a fact that quotes `beta` returned prepared with a
    fact_id. ChannelContractV2 §2 verbatim + §7 locator."""
    ev = _text_event("T-Q", ["alpha", "beta"], content="alpha beta")
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(ev, store=_GateStore.mirroring(ev), audit_dir=str(tmp_path),
                  reader=lambda **kw: _reply(
                      "T-Q", [_text_fact(ev, {"quote": "beta"})]))


def test_F4_two_byte_identical_raw_quotes_stay_lawful_and_distinct(tmp_path):
    ev = _text_event("T-QQ", ["same", "same"], content="same")
    result = run_event(ev, store=_GateStore.mirroring(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-QQ",
                                                  [_text_fact(ev, kw["item"])]))
    assert sorted(r["index"] for r in result["items"]) == [0, 1]
    assert all(r["fact_id"] for r in result["items"])


# ---- SEQ 996: the raw XBRL identity class, at the pure boundary -------------

def _ce_with_xbrl(**over):
    ce = _v2_events()[CE_EVENT]
    raw = copy.deepcopy(ce["items"][0])
    raw["xbrl"] = {**raw["xbrl"], **over}
    return {**ce, "items": [raw]}


@pytest.mark.parametrize("label,over", [
    ("unhashable axis", {"dimensions": [{"axis": [], "member": "us-gaap:M"}]}),
    ("blank axis", {"dimensions": [{"axis": "", "member": "us-gaap:M"}]}),
    ("blank member", {"dimensions": [{"axis": "us-gaap:A", "member": ""}]}),
    ("int member", {"dimensions": [{"axis": "us-gaap:A", "member": 7}]}),
    ("list concept", {"concept": ["us-gaap:R"]}),
    ("blank concept", {"concept": ""}),
    ("unlisted ptype", {"ptype": "moment"}),
    ("malformed end date", {"period_end": "not-a-date"}),
    ("malformed start date", {"period_start": "13/40/2026"}),
    ("repeated axis", {"dimensions": [{"axis": "us-gaap:A", "member": "us-gaap:M"},
                                      {"axis": "us-gaap:A", "member": "us-gaap:N"}]}),
])
def test_F8_hostile_raw_xbrl_identity_is_rejected_item_locally(label, over,
                                                               tmp_path):
    """Every one of these previously survived the pure check: the unhashable
    axis raised a raw TypeError inside axis_member_pairs, the blank axis did a
    graph read and was MISLABELLED MEMBER_LINK_INVALID, and an unlisted ptype
    fell into match_xbrl_fact's INSTANT branch where it could match a real
    instant row. Refusal must be the contract exception, before any I/O."""
    ev = _ce_with_xbrl(**over)
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=lambda **kw: pytest.fail("reached the reader"))
    row = result["items"][0]
    assert row["decision"] == "rejected", (label, row)
    assert row["codes"] == ["CHANNEL_CONTRACT_INVALID"], (label, row)


@pytest.mark.parametrize("label,over", [
    ("lawful verified-empty dimensions", {"dimensions": []}),
    ("lawful duration", {"ptype": "duration"}),
    ("lawful standards-owned qname",
     {"dimensions": [{"axis": "srt:StatementGeographicalAxis",
                      "member": "srt:NorthAmericaMember"}]}),
])
def test_F8_lawful_raw_xbrl_identity_is_still_accepted(label, over, tmp_path,
                                                       monkeypatch):
    ev = _ce_with_xbrl(**over)
    _stub_attach(monkeypatch, [])
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_xbrl_reader(ev, CE_EVENT))
    assert [r["index"] for r in result["items"]] == [0], (label, result)


def test_F4_an_XBRL_lane_fact_quoting_a_DIFFERENT_raw_item_is_refused(
        tmp_path, monkeypatch):
    """The XBRL-lane quote binding, proved INDEPENDENTLY of the text lane: N4
    could otherwise be killed by the text call alone (SEQ 996 item 2)."""
    ce = _v2_events()[CE_EVENT]
    ev = {**ce, "items": [copy.deepcopy(ce["items"][0])]}

    def door(items, *, source_id, **kw):
        built = []
        for i, it in enumerate(items):           # the door returns a fact whose
            d = copy.deepcopy(it["fact"])        # quote is NOT this raw item's
            d["item"]["quote"] = "a different quote entirely"
            built.append((i, prepared_fact_v2.PreparedFactV2._build(
                d, {"xbrl_concept_raw": it["concept"],
                    "member_refs": it["member_refs"]})))
        return xbrl_attach.AttachResult(source_id=source_id, facts=built,
                                        preflight_outcomes=[],
                                        member_menu={"folds": {}, "exclusions": []})
    _spy(monkeypatch, xbrl_attach, "attach_event_xbrl", door)
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                  filing_provider=FakeFilingProvider(),
                  reader=_xbrl_reader(ev, CE_EVENT))


# ---- SEQ 999/1000: the event-time PIT boundary -----------------------------
# Codex's live read-only check of the real adapter (source 0001306830-24-000155)
# measured `date` as an exact `str` "2024-08-02T16:17:22-04:00" — offset-aware
# ISO — so no adapter conversion is needed and the promoted owner accepts it.

LIVE_STAMP = "2024-08-02T16:17:22-04:00"


@pytest.mark.parametrize("label,channel,stored,ok", [
    ("same instant, equivalent offsets", LIVE_STAMP, "2024-08-02T20:17:22Z", True),
    ("identical aware stamps", LIVE_STAMP, LIVE_STAMP, True),
    ("same naive wall time", "2026-07-01T12:00:00", "2026-07-01T12:00:00", True),
    ("different instant", LIVE_STAMP, "2024-08-02T16:17:23-04:00", False),
    ("mixed awareness", "2026-07-01T12:00:00Z", "2026-07-01T12:00:00", False),
    ("channel is a bare date", "2026-07-01", "2026-07-01T00:00:00Z", False),
    ("stored is a bare date", "2026-07-01T00:00:00Z", "2026-07-01", False),
    ("channel missing", None, LIVE_STAMP, False),
    ("channel malformed", "not-a-timestamp", LIVE_STAMP, False),
    ("space separator, not RFC3339 T", "2026-07-01 12:00:00",
     "2026-07-01 12:00:00", False),
])
def test_F2_the_event_time_PIT_boundary(label, channel, stored, ok, tmp_path):
    """The channel `event_time` must be PROVEN to denote the same instant as the
    stored source stamp before the reader is called. aware/aware compares the
    INSTANT, naive/naive the exact wall time, and MIXED awareness fails closed
    rather than invent a zone. A bare date is not a full timestamp."""
    ev = {**_text_event("T-PIT", ["alpha"]), "event_time": channel}
    store = _GateStore(stamp=stored)
    call = lambda: run_event(                                    # noqa: E731
        ev, store=store, audit_dir=str(tmp_path),
        reader=lambda **kw: _reply("T-PIT", [_text_fact(ev, kw["item"])]))
    if ok:
        assert [r["index"] for r in call()["items"]] == [0], label
    else:
        with pytest.raises(prepared_fact_v2.SchemaError):
            call()


def test_F2_the_reader_receives_the_STORED_stamp_not_the_channel_spelling(tmp_path):
    """Equivalent offsets are lawful, but only the STORED canonical value may
    travel — the reader's PIT cutoff is graph-owned."""
    seen = []
    ev = {**_text_event("T-PITV", ["alpha"]), "event_time": LIVE_STAMP}
    store = _GateStore(stamp="2024-08-02T20:17:22Z")     # same instant, other spelling

    def reader(**kw):
        seen.append(kw["event_time"])
        return _reply("T-PITV", [_text_fact(ev, kw["item"])])

    run_event(ev, store=store, audit_dir=str(tmp_path), reader=reader)
    assert seen == ["2024-08-02T20:17:22Z"], seen


def test_F1_a_source_type_outside_the_published_vocabulary_is_refused(tmp_path):
    """The membership check uses the ONE owner `driver_validators.SOURCE_TYPES`
    (a copied `V2_SOURCE_TYPES` tuple was a third statement of the same rule,
    SEQ 1001). Refusal happens at the pure boundary, before any store touch."""
    ev = {**_text_event("T-ST", ["alpha"]), "source_type": "bogus"}
    with pytest.raises(prepared_fact_v2.SchemaError) as ei:
        run_event(ev, store=BombStore(), audit_dir=str(tmp_path),
                  reader=lambda **kw: pytest.fail("reached the reader"))
    assert "source_type" in str(ei.value), str(ei.value)


# ---- SEQ 1002: the last Stage-A scalar boundary ----------------------------

@pytest.mark.parametrize("bad", ["x/y", "", None, 5, True, []])
def test_F1_a_bad_source_id_never_reaches_the_store(bad, tmp_path):
    """Every one of these previously reached `store.get_source`, so the claim
    that all pure checks run before I/O was false. The owner
    `driver_ids.valid_source_id` is CALLED, never re-spelled (SEQ 1002 item 1)."""
    ev = {**_text_event("T-SID", ["alpha"]), "source_id": bad}
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(ev, store=BombStore(), audit_dir=str(tmp_path),
                  reader=lambda **kw: pytest.fail("reached the reader"))


@pytest.mark.parametrize("bad", [[], {}, 7, None, True])
def test_F1_a_non_string_source_type_refuses_without_a_raw_TypeError(bad, tmp_path):
    """`[]`/`{}` raised `TypeError: unhashable type` at the set membership test
    — the exact crash class these guards exist to exclude. Shape is now checked
    before the vocabulary owner is consulted."""
    ev = {**_text_event("T-STY", ["alpha"]), "source_type": bad}
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(ev, store=BombStore(), audit_dir=str(tmp_path),
                  reader=lambda **kw: pytest.fail("reached the reader"))


@pytest.mark.parametrize("bad", [None, "2026-07-01", "not-a-stamp", [], {},
                                 "2026-07-01 12:00:00"])
def test_F2_a_malformed_event_time_never_reaches_the_store(bad, tmp_path):
    """The promoted timestamp owner now runs at the PURE boundary; the
    same-instant comparison still happens after the source read."""
    ev = {**_text_event("T-ETP", ["alpha"]), "event_time": bad}
    with pytest.raises(prepared_fact_v2.SchemaError):
        run_event(ev, store=BombStore(), audit_dir=str(tmp_path),
                  reader=lambda **kw: pytest.fail("reached the reader"))


@pytest.mark.parametrize("channel_fye", [True, 1.0])
def test_F1_a_stored_owned_echo_must_match_TYPE_as_well_as_value(channel_fye,
                                                                 tmp_path):
    """`True == 1` and `1.0 == 1` are both True in Python, so a bool or float
    `fye_month` sailed past a value-only compare and produced a prepared fact
    against stored int 1. The echo is now exact in type AND value."""
    ev = {**_text_event("T-ECHO", ["alpha"]), "fye_month": channel_fye}
    store = _GateStore(fye=1, stamp=ev["event_time"])
    with pytest.raises(prepared_fact_v2.SchemaError) as ei:
        run_event(ev, store=store, audit_dir=str(tmp_path),
                  reader=lambda **kw: _reply("T-ECHO", [_text_fact(ev, kw["item"])]))
    assert "fye_month" in str(ei.value), str(ei.value)


def test_F1_the_lawful_exact_int_fye_echo_is_still_accepted(tmp_path):
    ev = {**_text_event("T-ECHO-OK", ["alpha"]), "fye_month": 1}
    store = _GateStore(fye=1, stamp=ev["event_time"])
    result = run_event(ev, store=store, audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-ECHO-OK",
                                                  [_text_fact(ev, kw["item"])]))
    assert [r["index"] for r in result["items"]] == [0]


# ---- OWNER FREEZE 2026-08-12: the three final public contract choices --------

@pytest.mark.parametrize("label,start,ok", [
    ("instant with null start — LAWFUL", None, True),
    ("instant with empty-string start", "", False),
    ("instant with the date duplicated into start", "2023-06-30", False),
])
def test_F8_an_instant_context_carries_a_null_start_only(label, start, ok,
                                                         tmp_path, monkeypatch):
    """XBRL 2.1 §4.7.2: an instant context has an `instant`, not a `startDate`.
    OWNER-FROZEN: raw `period_start` is JSON null; the empty string (a Fiscal
    sentinel) and a duplicated instant date are NOT aliases."""
    ev = _ce_with_xbrl(ptype="instant", period_start=start)
    _stub_attach(monkeypatch, [])
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_xbrl_reader(ev, CE_EVENT))
    row = result["items"][0]
    if ok:
        assert row["decision"] != "rejected", (label, row)
    else:
        assert row["decision"] == "rejected", (label, row)
        assert row["codes"] == ["CHANNEL_CONTRACT_INVALID"], (label, row)


def test_F12_a_reader_abstention_is_a_public_skipped_row(tmp_path):
    """OWNER-FROZEN: a reader abstention on a SUBMITTED item is `skipped` +
    READER_ABSTAINED — item-local, with a lawful sibling still prepared. This
    branch was fail-closed for the whole build because the code did not exist."""
    ev = _text_event("T-ABST", ["alpha", "beta"], content="alpha beta")
    calls = []

    def reader(**kw):
        calls.append(1)
        if len(calls) == 1:
            return _reply("T-ABST", abstentions=[_abstain(ev, kw["item"])])
        return _reply("T-ABST", [_text_fact(ev, kw["item"])])

    result = run_event(ev, store=_GateStore.mirroring(ev),
                       audit_dir=str(tmp_path), reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert rows[0]["decision"] == "skipped", rows[0]
    assert rows[0]["codes"] == ["READER_ABSTAINED"], rows[0]
    assert rows[0]["fact_id"] is None, rows[0]
    assert sorted(rows[0]) == ["codes", "decision", "detail", "fact_id", "index"]
    assert rows[1]["fact_id"], ("the lawful sibling was lost", rows[1])


def test_F12_the_XBRL_door_keeps_its_OWN_code_not_the_generic_one(tmp_path,
                                                                  monkeypatch):
    """CHANNEL_CONTRACT_INVALID is the GENERIC channel boundary only. An
    XBRL-door-specific failure still surfaces the door's own
    XBRL_CONTRACT_INVALID — not replaced, aliased or duplicated."""
    from driver.core.outcome_codes import ATTACH_CODES
    ce = _v2_events()[CE_EVENT]
    # ONE item, so the door's single preflight row accounts for the whole event
    # — with four, the accounting owner rightly refuses the three left unfilled.
    ev = {**ce, "items": [copy.deepcopy(ce["items"][0])]}

    def failing_door(items, *, source_id, **kw):
        return xbrl_attach.AttachResult(
            source_id=source_id, facts=[],
            preflight_outcomes=[{"index": 0, "fact_id": None,
                                 "decision": "rejected",
                                 "codes": ["XBRL_CONTRACT_INVALID"],
                                 "detail": "door-specific failure"}],
            member_menu={"folds": {}, "exclusions": []})
    _spy(monkeypatch, xbrl_attach, "attach_event_xbrl", failing_door)
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_xbrl_reader(ev, CE_EVENT))
    rows = {r["index"]: r for r in result["items"]}
    assert rows[0]["codes"] == ["XBRL_CONTRACT_INVALID"], rows[0]
    assert "XBRL_CONTRACT_INVALID" in ATTACH_CODES     # still the door's own


def test_F12_both_new_codes_live_in_the_ONE_vocabulary_owner():
    """No second registry, no copied vocabulary."""
    from driver.core.outcome_codes import (OUTCOME_CODES, ROUTE_CODES,
                                           require_known)
    assert ROUTE_CODES == ("READER_ABSTAINED", "CHANNEL_CONTRACT_INVALID")
    for code in ROUTE_CODES:
        assert code in OUTCOME_CODES and require_known(code) == code


# =============================================================================
# F13 — FUSION + THE EXISTING PLANNER, DRY-RUN (Codex SEQ 1009)
#
# The route used to stop at `prepared`. It now continues through the SAME
# owners the V1 path uses, in the SAME order:
#
#   to_stored_fact  ->  fuse_event  ->  validate_fact  ->  plan_event_write
#   conversion/id       S3.5 fusion     THE rule         THE planner
#                                       engine
#
# Nothing is restated and no second vocabulary is minted: the run status is
# V1's own `dry_run` and every row decision comes from V1's own `_DECISION`.
# =============================================================================

def _plan_spy(monkeypatch):
    """Record what the EXISTING planner was really handed and really returned —
    proof of reuse that a route-local re-implementation could not fake."""
    seen = {"facts": [], "results": []}
    real = driver_writer.plan_event_write

    def spy(facts, graph, prior_series_units=None):
        facts = list(facts)
        results = real(facts, graph, prior_series_units)
        seen["facts"].extend(facts)
        seen["results"].extend(results)
        return results
    _spy(monkeypatch, driver_writer, "plan_event_write", spy)
    return seen


def _point(v):
    """The four level slots that make a fact carry a number."""
    return {"level_low": slot(v), "level_high": slot(v),
            "level_unit": "count", "level_shape_hint": "point"}


def test_F13_all_FOUR_existing_owners_run_on_the_ONE_route_IN_V1_ORDER(
        tmp_path, monkeypatch):
    """V1's ordering, reused exactly: conversion/id, then FUSION, then the one
    rule engine, then the one planner. Fusion sits BEFORE validation because it
    fills nulls — validating first would refuse fragments fusion would heal."""
    used = []
    for owner, name in ((prepared_fact_v2, "to_stored_fact"),
                        (driver_fusion, "fuse_event"),
                        (driver_validators, "validate_fact"),
                        (driver_writer, "plan_event_write")):
        real = getattr(owner, name)
        _spy(monkeypatch, owner, name,
             (lambda n, r: lambda *a, **k: (used.append(n), r(*a, **k))[1])(
                 name, real))
    ev = _text_event("T-OWNERS", ["alpha"])
    run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
              reader=lambda **kw: _reply("T-OWNERS", [_text_fact(ev, kw["item"])]))
    assert used == ["to_stored_fact", "fuse_event", "validate_fact",
                    "plan_event_write"], used


def test_F13_a_lawful_text_singleton_is_PLANNED_by_the_existing_writer(
        tmp_path, monkeypatch):
    plans = _plan_spy(monkeypatch)
    ev = _text_event("T-PLAN1", ["alpha"])
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-PLAN1",
                                                  [_text_fact(ev, kw["item"])]))
    # V1's OWN status word for a planned-but-unwritten run — not a second
    # vocabulary. A row saying "written" under a bespoke "ok" would be a lie.
    assert result["status"] == "dry_run", result["status"]
    row, = result["items"]
    assert row["index"] == 0 and row["decision"] == "written", row
    assert row["fact_id"].startswith("du:"), row
    assert [f["id"] for f in plans["facts"]] == [row["fact_id"]], plans["facts"]
    assert [r.outcome for r in plans["results"]] == ["created"], plans["results"]


def test_F13_a_lawful_XBRL_singleton_is_PLANNED_too(tmp_path, monkeypatch):
    """The XBRL door's fact reaches the SAME planner as the text lane."""
    plans = _plan_spy(monkeypatch)
    _stub_attach(monkeypatch, [])
    ce = _v2_events()[CE_EVENT]
    ev = {**ce, "items": [copy.deepcopy(ce["items"][0])]}
    result = run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
                       filing_provider=FakeFilingProvider(),
                       reader=_xbrl_reader(ev, CE_EVENT))
    row, = result["items"]
    assert row["decision"] == "written", row
    assert [r.outcome for r in plans["results"]] == ["created"], plans["results"]


def test_F13_two_raw_facts_that_FUSE_yield_ONE_fact_on_BOTH_raw_positions(
        tmp_path, monkeypatch):
    """A successful same-fact collapse must not duplicate a result, and must not
    swallow a raw item: ONE planner call, TWO raw rows, ONE shared fact_id."""
    plans = _plan_spy(monkeypatch)
    ev = _text_event("T-FUSE", ["alpha", "beta"], content="alpha beta")
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-FUSE",
                                                  [_text_fact(ev, kw["item"])]))
    rows = {r["index"]: r for r in result["items"]}
    assert len(result["items"]) == 2 and sorted(rows) == [0, 1], result["items"]
    assert rows[0]["fact_id"] == rows[1]["fact_id"], rows
    assert len(plans["facts"]) == 1, "fusion did not collapse before the planner"


def test_F13_validation_runs_on_the_FUSED_fact_not_on_the_fragment(tmp_path, monkeypatch):
    """WHY fusion must precede validation, driven rather than argued.

    Fragment 0 carries a shape hint and NO numbers — on its own the validator
    rejects it ("hint without numbers"). Fragment 1 carries the numbers. They
    share an id and do not conflict, so fusion fills the nulls and the merged
    fact is lawful. Validating the fragment instead of the fused result would
    refuse a fact that fusion had already healed — and no other control in this
    suite catches that swap, because everywhere else the two are the same object.
    """
    ev = _text_event("T-FILL", ["alpha", "beta"], content="alpha beta")

    def reader(**kw):
        over = ({"level_shape_hint": "point"}                  # hint, no numbers
                if kw["item"]["quote"] == "alpha" else _point(5))
        return _reply("T-FILL", [_text_fact(ev, kw["item"], **over)])

    seen = _plan_spy(monkeypatch)
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert sorted(rows) == [0, 1], result["items"]
    for i, r in rows.items():
        assert r["decision"] == "written", (i, r)
    assert rows[0]["fact_id"] == rows[1]["fact_id"], rows
    # AND the CONTENT that reached the planner is the FUSED content. Both facts
    # share an id, so checking rows alone cannot tell the fused fact from the
    # fragment — the planner would happily "create" the numberless one under the
    # same id and every public row would still read "written".
    op = next(o for r in seen["results"] for o in r.ops
              if o["op"] == "create_fact")
    assert op["props"]["level_low"] == 5, op["props"]
    assert op["props"]["level_unit"] == "count", op["props"]
    # R6 (SEQ 1012), closing my own SEQ 848 self-find: the provisional plan and
    # the fusion logs must REACH the write-ahead audit. Nothing read either.
    doc = _audit_doc(tmp_path)
    assert doc["plans"], doc.get("plans")
    assert doc["plans"][0]["fact_id"] == rows[0]["fact_id"], doc["plans"]
    assert doc["fusion_logs"], doc.get("fusion_logs")
    assert doc["fusion_logs"][0]["event"] == "fused_fragment", doc["fusion_logs"]


def test_F13_REJECT_still_beats_PARK_on_the_fused_fact(tmp_path):
    """A surprise fact with `value_text` carries BOTH a REJECT (value_text is
    guidance-only) and a PARK (no home fact). The row must be REJECTED.

    V1's own `test_reject_beats_park` does not actually pin this — I drove its
    fixture and it produces a REJECT alone, so the precedence never gets
    exercised there. This control checks both actions are really present first,
    so it cannot silently degrade into a one-sided test the way that one did.
    """
    quote = "revenue of 100 beat consensus of 90"
    ev = _text_event("T-PREC", [quote])
    over = dict(fact_type="surprise",
                driver_name="revenue_surprise", driver_state="beat",
                surprise_basis_hint="actual", comparison_baseline="consensus",
                comparison_low=slot(90), comparison_high=slot(90),
                comparison_shape_hint="point", value_text="some text",
                **_point(100))
    actions = []
    real = driver_validators.validate_fact

    def val(f, **k):
        out = real(f, **k)
        actions.extend(v.action for v in out)
        return out

    with pytest.MonkeyPatch.context() as mp:
        _spy(mp, driver_validators, "validate_fact", val)
        result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                           reader=lambda **kw: _reply(
                               "T-PREC", [_text_fact(ev, kw["item"], **over)]))
    assert {"REJECT", "PARK"} <= set(actions), actions
    row, = result["items"]
    assert row["decision"] == "rejected", row
    assert row["codes"] == ["VALUE_TEXT"], row


def test_F13_a_numberless_guidance_withdrawal_carries_its_PRIOR_units(
        tmp_path, monkeypatch):
    """The ONE case that needs prior guide units: a withdrawal has no numbers,
    so its series_unit copies exactly one clear prior. Dropping the prior lookup
    turns a lawful withdrawal into a SERIES_UNIT park — silently, unless this
    control exists."""
    seen = _plan_spy(monkeypatch)
    ev = _text_event("T-WDRAW", ["alpha"])
    guide = {"fact_type": "guidance", "driver_name": "guide",
             "driver_state": "withdrawn", "company_confirmed": True,
             "time_type": "duration", "period_start_date": "2026-01-01",
             "period_end_date": "2026-12-31", "fiscal_year": 2026}
    store = _mirror_fake(ev, drivers={"guide": {"name": "guide",
                                                "fact_type": "guidance"}})

    def go():
        return run_event(ev, store=store, audit_dir=str(tmp_path),
                         reader=lambda **kw: _reply(
                             "T-WDRAW", [_text_fact(ev, kw["item"], **guide)]))

    # NO prior known -> the writer fails closed rather than invent an axis
    row, = go()["items"]
    assert row["decision"] == "parked", row
    assert row["codes"] == ["SERIES_UNIT"], row
    # exactly ONE clear prior -> the same withdrawal is planned and stamped.
    # Both halves matter: a control that only asserted the happy path would pass
    # with the lookup deleted if the fixture happened to need no prior.
    store.prior_units = {row["fact_id"]: ["m_usd"]}
    seen["results"].clear()
    second, = go()["items"]
    assert second["decision"] == "written", second
    assert [r.outcome for r in seen["results"]] == ["created"], seen["results"]
    op = next(o for r in seen["results"] for o in r.ops
              if o["op"] == "create_fact")
    assert op["props"]["series_unit"] == "m_usd", op["props"]


def test_F13_a_one_raw_lawful_split_keeps_BOTH_planned_facts(tmp_path,
                                                             monkeypatch):
    """Two different facts from ONE raw item: several rows at the same raw
    index, each with its own planned id."""
    plans = _plan_spy(monkeypatch)
    ev = _text_event("T-SPLIT", ["alpha"])
    store = _mirror_fake(ev, drivers={
        "revenue": {"name": "revenue", "fact_type": "metric"},
        "margin": {"name": "margin", "fact_type": "metric"}})
    result = run_event(ev, store=store, audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-SPLIT", [
                           _text_fact(ev, kw["item"]),
                           _text_fact(ev, kw["item"], driver_name="margin")]))
    assert [r["index"] for r in result["items"]] == [0, 0], result["items"]
    assert len({r["fact_id"] for r in result["items"]}) == 2, result["items"]
    assert len(plans["facts"]) == 2, plans["facts"]


def test_F13_a_split_with_MIXED_outcomes_loses_neither_branch(tmp_path):
    """A failed branch is NEVER collapsed into its lawful sibling: both survive
    on the same raw index, with their own decisions."""
    ev = _text_event("T-MIX", ["alpha"])
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=lambda **kw: _reply("T-MIX", [
                           _text_fact(ev, kw["item"]),
                           _text_fact(ev, kw["item"],
                                      driver_name="not_a_stored_driver")]))
    assert [r["index"] for r in result["items"]] == [0, 0], result["items"]
    assert sorted(r["decision"] for r in result["items"]) == ["parked",
                                                              "written"]
    bad = next(r for r in result["items"] if r["decision"] == "parked")
    assert bad["codes"] == ["DRIVER_NOT_READY"], bad


def test_F13_an_AMBIGUOUS_fusion_group_parks_every_raw_item_in_it(tmp_path,
                                                                  monkeypatch):
    """alpha=5 and beta=7 conflict; gamma is numberless and conflicts with
    neither. The group neither folds cleanly nor conflicts pairwise-everywhere,
    so it PARKS whole — one row per raw item, never one row per group."""
    plans = _plan_spy(monkeypatch)
    ev = _text_event("T-AMBF", ["alpha", "beta", "gamma"],
                     content="alpha beta gamma")
    values = {"alpha": 5, "beta": 7, "gamma": None}

    def reader(**kw):
        v = values[kw["item"]["quote"]]
        return _reply("T-AMBF", [_text_fact(ev, kw["item"],
                                            **({} if v is None else _point(v)))])

    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert len(result["items"]) == 3 and sorted(rows) == [0, 1, 2], result["items"]
    for i, r in rows.items():
        assert r["decision"] == "parked", (i, r)
        assert r["codes"] == ["FUSION_AMBIGUOUS"], (i, r)
    assert plans["facts"] == [], "an ambiguous group reached the planner"


def test_F13_two_pairwise_CONFLICTING_facts_both_plan_as_hashed_members(
        tmp_path, monkeypatch):
    """Every pair conflicts, so fusion lets both stand (it promises no hashing)
    and the planner mints hashed members. Raw origins survive: one row each."""
    plans = _plan_spy(monkeypatch)
    ev = _text_event("T-MEMB", ["alpha", "beta"], content="alpha beta")
    values = {"alpha": 5, "beta": 7}
    result = run_event(
        ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
        reader=lambda **kw: _reply("T-MEMB", [_text_fact(
            ev, kw["item"], **_point(values[kw["item"]["quote"]]))]))
    rows = {r["index"]: r for r in result["items"]}
    assert sorted(rows) == [0, 1], result["items"]
    assert [r.outcome for r in plans["results"]] == ["created_member",
                                                     "created_member"]
    assert rows[0]["fact_id"] != rows[1]["fact_id"], rows
    assert all("quote_hash=" in r["fact_id"] for r in rows.values()), rows


def test_F13_the_planner_DEDUPED_outcome_is_CLOSED_OFF_in_this_scope(
        tmp_path, monkeypatch):
    """`deduped` needs two facts reaching the planner with the SAME id AND the
    SAME ten-slot signature. Fusion only lets both stand when EVERY pair
    conflicts, and `driver_fusion._conflicts` fires on exactly three things:

        a signature slot   -> the two signatures then DIFFER, so no dedup
        company_confirmed  -> guidance-only, and guidance demands exactly True,
                              so a True-vs-False pair cannot both be stored
        a *_shape_hint     -> the hint must EQUAL the actual shape, which the
                              equal numbers already fix, so it cannot differ

    I first reported this outcome reachable via `company_confirmed` — that
    field really is outside the signature — and only found the closure by
    driving it. This test drives that live escape hatch rather than reasoning
    about it: both facts are refused, and the planner is handed nothing.
    """
    seen = _plan_spy(monkeypatch)
    ev = _text_event("T-DEDUP", ["alpha", "beta"], content="alpha beta")
    flags = {"alpha": True, "beta": False}
    result = run_event(
        ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
        reader=lambda **kw: _reply("T-DEDUP", [_text_fact(
            ev, kw["item"], company_confirmed=flags[kw["item"]["quote"]],
            **_point(5))]))
    assert [r["decision"] for r in result["items"]] == ["rejected", "rejected"]
    assert all("LANE" in r["codes"] for r in result["items"]), result["items"]
    assert seen["facts"] == [], "a fact the validator refused reached the planner"


def test_F13_ONE_raw_item_in_a_parked_fusion_group_owes_exactly_ONE_row(
        tmp_path):
    """Bound 3, the hard direction: three facts from a SINGLE raw item form one
    ambiguous group. A failed group is ONE relation per raw item, so this raw
    position owes exactly one public row — not three copies of the same park."""
    ev = _text_event("T-1RAW", ["alpha"])
    result = run_event(
        ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
        reader=lambda **kw: _reply("T-1RAW", [
            _text_fact(ev, kw["item"], **_point(5)),
            _text_fact(ev, kw["item"], **_point(7)),
            _text_fact(ev, kw["item"])]))          # numberless: conflicts with neither
    assert len(result["items"]) == 1, result["items"]
    row, = result["items"]
    assert row["index"] == 0 and row["decision"] == "parked", row
    assert row["codes"] == ["FUSION_AMBIGUOUS"], row


def test_R5_the_member_links_the_XBRL_door_proved_reach_the_planner(
        tmp_path, monkeypatch):
    """REPRODUCED BY THE REVIEWER on the real CE route: four planned facts and
    ZERO `MAPS_TO_MEMBER` operations, although every raw fact carried two
    dimensions. The door builds `PreparedFactV2.member_refs`, but
    `to_stored_fact` deliberately dropped them under T10 — whose premise ("the
    clean path discards it") became FALSE the moment this route became a real
    consumer and started planning writes.

    The proof inspects the REAL planner operations, not an internal field."""
    plans = _plan_spy(monkeypatch)
    _stub_attach(monkeypatch, [])
    ce = _v2_events()[CE_EVENT]
    ev = {**ce, "items": [copy.deepcopy(ce["items"][0])]}
    dims = ev["items"][0]["xbrl"]["dimensions"]
    assert dims, "fixture lost its dimensions"
    run_event(ev, store=MatchingGraphStore(ev), audit_dir=str(tmp_path),
              filing_provider=FakeFilingProvider(),
              reader=_xbrl_reader(ev, CE_EVENT))
    edges = [o for r in plans["results"] for o in r.ops
             if o.get("type") == "MAPS_TO_MEMBER"]
    assert len(edges) == len(dims), (len(edges), len(dims), edges)
    assert {e["to"] for e in edges} == {d["member"] for d in dims}, edges
    assert {e["axis"] for e in edges} == {d["axis"] for d in dims}, edges
    for e in edges:
        assert e["props"]["slice_part"], e


def test_R5_a_text_fact_plans_NO_member_edges(tmp_path, monkeypatch):
    """The no-edge control: a text fact has no dimension claim at all, so
    restoring the movement must not invent one."""
    plans = _plan_spy(monkeypatch)
    ev = _text_event("T-R5T", ["alpha"])
    run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
              reader=lambda **kw: _reply("T-R5T", [_text_fact(ev, kw["item"])]))
    edges = [o for r in plans["results"] for o in r.ops
             if o.get("type") == "MAPS_TO_MEMBER"]
    assert edges == [], edges


def _seed_then_rerun(tmp_path, monkeypatch, seed_over):
    """Run once against an EMPTY graph, take the fact the WRITER ITSELF planned
    to create, seed a second graph with it, and re-run. The stored-fact shape is
    the planner's own output — no graph row is hand-authored here."""
    ev = _text_event("T-OUT", ["alpha"])

    def reader(**kw):
        return _reply("T-OUT", [_text_fact(ev, kw["item"], **_point(5))])

    seen = _plan_spy(monkeypatch)
    run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path), reader=reader)
    op = next(o for r in seen["results"] for o in r.ops
              if o["op"] == "create_fact")
    seed = dict(op["props"], **seed_over)
    seen["facts"].clear()
    seen["results"].clear()
    result = run_event(ev, store=_mirror_fake(ev, facts=[seed]),
                       audit_dir=str(tmp_path), reader=reader)
    return seen, result


@pytest.mark.parametrize("label,seed_over,outcome,decision", [
    ("byte-identical stored fact", {}, "noop", "merged"),
    ("stored fact missing one signature slot", {"level_high": None},
     "filled", "merged"),
    ("stored fact carrying an older quote", {"quote": "older wording"},
     "updated", "merged"),
])
def test_F13_the_existing_planner_outcomes_are_really_reachable(
        label, seed_over, outcome, decision, tmp_path, monkeypatch):
    seen, result = _seed_then_rerun(tmp_path, monkeypatch, seed_over)
    row, = result["items"]
    assert [r.outcome for r in seen["results"]] == [outcome], (label, seen)
    assert row["decision"] == decision, (label, row)


def test_F13_a_planner_PARK_reaches_the_public_row_with_the_planners_own_code(
        tmp_path, monkeypatch):
    """Two stored siblings — one compatible, one conflicting — and the planner
    refuses to guess which member to fill. Its code rides on PlanResult and is
    published unchanged; the route mints nothing."""
    ev = _text_event("T-COLL", ["alpha"])

    def reader(**kw):
        return _reply("T-COLL", [_text_fact(ev, kw["item"], **_point(5))])

    seen = _plan_spy(monkeypatch)
    run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path), reader=reader)
    op = next(o for r in seen["results"] for o in r.ops
              if o["op"] == "create_fact")
    bare = op["props"]["id"]
    siblings = [dict(op["props"], level_high=None),               # compatible
                dict(op["props"], id=f"{bare}|quote_hash=zz",     # conflicting
                     level_low=9, level_high=9)]
    seen["results"].clear()
    result = run_event(ev, store=_mirror_fake(ev, facts=siblings),
                       audit_dir=str(tmp_path), reader=reader)
    row, = result["items"]
    assert [r.code for r in seen["results"]] == ["COLLISION_AMBIGUOUS"], seen
    assert row["decision"] == "parked" and row["codes"] == ["COLLISION_AMBIGUOUS"]


def _surprise_event():
    """A home metric fact and the surprise that depends on it, in one event."""
    q_home, q_sur = "revenue of 100", "revenue of 100 beat consensus of 90"
    ev = _text_event("T-SUR", [q_home, q_sur], content=q_sur)
    sur = dict(fact_type="surprise",
               driver_name="revenue_surprise", driver_state="beat",
               surprise_basis_hint="actual", comparison_baseline="consensus",
               comparison_low=slot(90), comparison_high=slot(90),
               comparison_shape_hint="point", **_point(100))

    def reader(**kw):
        over = _point(100) if kw["item"]["quote"] == q_home else sur
        return _reply("T-SUR", [_text_fact(ev, kw["item"], **over)])
    return ev, reader


def test_F13_a_surprise_stands_when_its_home_fact_is_accepted(tmp_path):
    """The lawful half. Without it the park control below would pass even if
    every surprise parked for the wrong reason."""
    ev, reader = _surprise_event()
    result = run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                       reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert sorted(rows) == [0, 1], result["items"]
    for i, r in rows.items():
        assert r["decision"] == "written", (i, r)
    assert "surprise=" in rows[1]["fact_id"], rows[1]


def test_F13_a_surprise_PARKS_when_its_home_fact_is_not_accepted(tmp_path,
                                                                 monkeypatch):
    """V1's surprise post-plan rule, now reachable because the route plans. The
    home fact is forced to a planner PARK (two siblings, one compatible and one
    conflicting), and the surprise must NOT be published as written."""
    ev, reader = _surprise_event()
    seen = _plan_spy(monkeypatch)
    run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path), reader=reader)
    op = next(o for r in seen["results"] for o in r.ops
              if o["op"] == "create_fact" and "surprise=" not in o["id"])
    bare = op["props"]["id"]
    siblings = [dict(op["props"], level_high=None),               # compatible
                dict(op["props"], id=f"{bare}|quote_hash=zz",     # conflicting
                     level_low=9, level_high=9)]
    result = run_event(ev, store=_mirror_fake(ev, facts=siblings),
                       audit_dir=str(tmp_path), reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert rows[0]["decision"] == "parked", rows[0]        # the home itself
    assert rows[1]["decision"] == "parked", rows[1]        # the surprise
    assert rows[1]["codes"] == ["SURPRISE_HOME_NOT_ACCEPTED"], rows[1]


def test_F13_the_dry_run_planner_still_writes_NOTHING(tmp_path):
    """Planning is not writing: the store is byte-identical afterwards."""
    ev = _text_event("T-NOWRITE", ["alpha", "beta"], content="alpha beta")
    store = _mirror_fake(ev)
    before = (copy.deepcopy(store.applied), copy.deepcopy(store.facts),
              copy.deepcopy(store.drivers))
    run_event(ev, store=store, audit_dir=str(tmp_path),
              reader=lambda **kw: _reply("T-NOWRITE",
                                         [_text_fact(ev, kw["item"])]))
    assert (store.applied, store.facts, store.drivers) == before


def test_F13_enable_writes_is_STILL_refused_after_the_planner_is_wired(tmp_path):
    """Planning reaching the writer must not be mistaken for permission to
    execute: the flag stays refused until the owner-gated switch."""
    ev = _text_event("T-GATE", ["alpha"])
    with pytest.raises(driver_writer.WriterError):
        run_event(ev, store=_mirror_fake(ev), audit_dir=str(tmp_path),
                  enable_writes=True,
                  reader=lambda **kw: _reply("T-GATE",
                                             [_text_fact(ev, kw["item"])]))
