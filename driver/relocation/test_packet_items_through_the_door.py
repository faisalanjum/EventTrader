"""#824 — EVERY saved packet item, through Core's PUBLIC DOOR, on its own
LITERAL evidence.

Fiscal's byte parity proves the packet PRODUCER did not move. It does not prove
Core can BIND what was saved. Only the CE 726 item had made that trip; this
covers all eleven — CE's four shared-row facts and ACI's 3/2/2 — through one
parameterised translation, never item-specific code.

NOTHING IS RECOMPUTED. Each item submits the four-key `source_evidence` exactly
as written to disk on 2026-07-23, and every premise is asserted against the
fetched filing first. The slice token is the one place a value is derived, and
it is derived by the PRODUCTION owner (`classify_axis` + `member_token`) because
a supplied part is never trusted — so the test may not invent one either.

THE EVENT PART IS SCAFFOLDING, explicitly. It is built from each item's own
quote so the occurrence plumbing runs; the historical model view was never
archived, so nothing here says anything about what the reader actually saw.
"""
import json
import os

import pytest

from driver.relocation.test_real_726_end_to_end import store_or_skip


def _rows_of(store, source_id, concept):
    """The verified rows only — the exclusions have their own
    consumers and are never silently dropped here."""
    return store.get_xbrl_fact_dimensions(source_id, concept).rows

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PACKETS = ("data/driver_catalog_seed/wp3_ce_compliant/packets.jsonl",
            "data/driver_catalog_seed/wp3_aci_stream/packets.jsonl")
_CACHE = os.path.join(_ROOT, "scripts", "driver_seed", "relocate_probe",
                      "inline_html_cache")


def _saved_items():
    out = []
    for rel in _PACKETS:
        path = os.path.join(_ROOT, rel)
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            if line.strip():
                packet = json.loads(line)
                for index, item in enumerate(packet["items"]):
                    out.append((packet["source_id"], index, item))
    return out


_ITEMS = _saved_items()


def _filing(source_id):
    with open(os.path.join(_CACHE, f"{source_id}.htm"),
              encoding="utf-8", errors="replace") as fh:
        return fh.read()



def _door_entry(item, text, store, source_id):
    """THE one translation: a saved packet item -> a public-door event item.

    Parameterised over every saved item; there is no per-item branch. Only the
    slice token is derived, by the production owner.
    """
    from decimal import Decimal

    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    from driver.core.slice_menu import classify_axis, member_token
    from driver.core.xbrl_attach import expected_multiplier
    xbrl = item["xbrl"]
    saved = xbrl["source_evidence"]

    q0, q1 = saved["quote_span"]
    quote = text[q0:q1]

    member_refs = []
    if xbrl["dimensions"]:
        labels = {(d["axis"], d["member"]): d["label"]
                  for row in _rows_of(store, source_id,
                                                            xbrl["concept"])
                  for d in row["dims"]}
        for dim in xbrl["dimensions"]:
            label = labels.get((dim["axis"], dim["member"]))
            assert label, f"the graph carries no label for {dim}"
            status, kind = classify_axis(dim["axis"])
            assert status == "slice", (dim, status)
            member_refs.append({"axis": dim["axis"], "member": dim["member"],
                                "slice_part": member_token(kind, label)})

    scale = int(xbrl["ix"]["scale"])
    slot = {"value": Decimal(str(item["value"])),
            "scale_multiplier": expected_multiplier("m_usd", scale),
            "unit_scale_evidence": None}
    fact_item = {k: None for k in ITEM_FIELDS}
    fact_item.update(driver_name="packet_item", driver_state="reported",
                     quote=quote, measurement_raw_spans=[],
                     slice_parts=[r["slice_part"] for r in member_refs],
                     level_unit="m_usd", level_low=dict(slot),
                     level_high=dict(slot), time_type=xbrl["ptype"],
                     period_start_date=xbrl["period_start"],
                     period_end_date=xbrl["period_end"])
    return {"fact": {"fact_type": "metric", "part_ref": "p1",
                     "occurrence_in_part": None, "per_x": None,
                     "item": fact_item},
            "concept": xbrl["concept"], "member_refs": member_refs,
            "source_evidence": saved}, quote


def test_the_saved_corpus_is_the_eleven_items_this_file_claims():
    assert len(_ITEMS) == 11, [i[0] for i in _ITEMS]


@pytest.mark.live
@pytest.mark.parametrize("source_id,index,item", _ITEMS,
                         ids=[f"{s}#{i}" for s, i, _ in _ITEMS])
def test_every_saved_packet_item_attaches_on_its_LITERAL_evidence(
        source_id, index, item):
    from driver.core.test_round10_event_boundary import parts_for
    from driver.core.xbrl_attach import attach_event_xbrl
    from driver.relocation.inline_html import prepare

    # THE CACHE IS A PREMISE, not an optional service. Skipping a missing one
    # would quietly shrink this regression from eleven items to however many
    # happen to be on disk.
    assert os.path.exists(os.path.join(_CACHE, f"{source_id}.htm")), \
        f"the cached filing for {source_id} is REQUIRED by this regression"
    prepared = prepare(_filing(source_id))
    saved = item["xbrl"]["source_evidence"]

    # PREMISES FIRST, against the fetched filing — if the saved coordinates
    # ever drift, this fails here rather than proving nothing.
    assert sorted(saved) == ["pieces", "quote_span", "raw_label_span",
                             "representation_sha256"]
    assert saved["representation_sha256"] == prepared["text_sha"]
    text = prepared["text"]
    q0, q1 = saved["quote_span"]
    assert 0 <= q0 < q1 <= len(text) and text[q0:q1].strip()
    if saved["raw_label_span"] is not None:
        l0, l1 = saved["raw_label_span"]
        assert q0 <= l0 and l1 <= q1 and text[l0:l1].strip()
    for piece in saved["pieces"]:
        a, b = piece["span"]
        assert text[a:b] == piece["text"], piece

    store = store_or_skip(source_id)
    try:
        entry, quote = _door_entry(item, text, store, source_id)

        class _Provider:
            def get_filing_document(self, s):
                return _filing(source_id) if s == source_id else None

        res = attach_event_xbrl([entry], source_id=source_id, store=store,
                                filing_provider=_Provider(),
                                text_parts=parts_for([entry]))
        # THE DOOR NOW RETURNS ITS RESULT RECORD (#825). A success test unwraps
        # the (original_index, fact) pair — and it can now say something the old
        # bare list could not: that the event reported NO outcome row. A
        # silently parked item used to look exactly like an empty list, so the
        # failure said "0 != 1" and nothing about WHY.
        assert res.preflight_outcomes == (), \
            [dict(o) for o in res.preflight_outcomes]
        assert [i for i, _f in res.facts] == [0]
        assert res.source_id == source_id
        fact = res.facts[0][1]
        assert fact.item.quote == quote
        assert fact.item.xbrl_concept_raw == item["xbrl"]["concept"]
    finally:
        store.close()


def test_EU054_the_core_facing_evidence_vocabulary_is_the_sheets():
    """EU-054 (#827): the Core-facing spellings ARE the frozen packet
    vocabulary — the Core-Fiscal contract sheet section 2 clause, pinned
    member-for-member. The corpus nodes above prove the SUBMIT side against
    saved packets (working/live lanes; the corpus lives outside the git
    tree); this node pins the SHAPE side self-contained, so a drifted
    spelling reddens in the isolated lane too."""
    from driver.relocation.inline_html import (PIECE_KEYS, PIECE_KINDS,
                                               SOURCE_EVIDENCE_KEYS)
    assert SOURCE_EVIDENCE_KEYS == ('representation_sha256', 'quote_span',
                                    'raw_label_span', 'pieces')
    assert PIECE_KEYS == ('kind', 'text', 'span')
    assert PIECE_KINDS == ('header', 'section')

