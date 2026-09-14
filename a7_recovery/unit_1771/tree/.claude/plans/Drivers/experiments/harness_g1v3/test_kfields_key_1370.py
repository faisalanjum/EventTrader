"""Codex SEQ 1370 — the two focused defects, proved RED before the fix.

RULING 1  `abstentions[].reason` stays required, nonblank and preserved, but it
          is NOT answer identity. The same-settled-reply comparison omits ONLY
          that free-prose field and still compares the fact/abstain branch, the
          source binding, the exact locator, every fact field and every
          continuity proposal.
RULING 2  The frozen manifest keeps pinning the reviewed BASE (attempt-1)
          rendering and never moves. The official state must instead carry the
          rendering for the attempt its own receipt binds. Attempt 2 changes
          only that bound attempt identity; attempt 3 stays impossible.

Nothing here is semantic string matching and nothing is packet-specific: the
controls are built from whatever the frozen package already contains.
"""
import copy
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_key as K                                    # noqa: E402
# the accepted focused file owns these builders; re-declaring them here would
# be a second fixture for one meaning, so they are imported, never copied
from test_kfields_key_1363 import (build_call, official,        # noqa: E402,F401
                                   primary_with)


# --------------------------------------------------------------- helpers ---
def _item():
    """The first scheduled item; nothing in these controls is item-specific."""
    return K.phase1_items()[0]


def _abstain_body(item, reason):
    return ('{"source_id": %s, "facts": [], "abstentions": [{"reason": %s}], '
            '"continuity_hints": []}'
            % (json.dumps(item["source_id"]), json.dumps(reason)))


def _completed_abstain(item, reason):
    done = K.completed_draft(item, _abstain_body(item, reason))
    assert done is not None, "the control body must itself be lawful"
    return done


def _envelope(item, body, rows, ambiguities="[]"):
    return ('{"packet_id": %s, "settled": %s, "reconciliation": [%s], '
            '"ambiguities": %s}'
            % (json.dumps(item["packet_id"]), body, ", ".join(rows),
               ambiguities))


def _rows_stating(item, truth_of):
    """One reconciliation row per shown lane, stating `truth_of(lane)`."""
    return ['{"lane_id": %s, "exact_match": %s, "why": "compared"}'
            % (json.dumps(d["lane_id"]),
               "true" if truth_of(d) else "false")
            for d in item["a3_drafts"]]


# ============================================ RULING 1 — answer identity ===
def test_the_same_abstention_decided_the_same_way_matches_despite_prose():
    """RED before the fix: two lawful readers word one abstention differently.

    Same branch, same source, same locator, same (empty) facts and continuity
    - only the prose differs. That is one answer, not two.
    """
    item = _item()
    a = _completed_abstain(item, "the scale marker sits outside the quote")
    b = _completed_abstain(item, "the in-quote span carries no scale wording")
    assert a != b, "the control is pointless unless the prose really differs"
    assert K._same_answer(a, b) is True


def test_a_blank_abstention_reason_is_still_refused():
    """The projection must not become a licence to drop the field."""
    item = _item()
    assert K.completed_draft(item, _abstain_body(item, "   ")) is None
    assert K.completed_draft(item, _abstain_body(item, "")) is None


def test_an_abstention_and_a_fact_are_never_the_same_answer():
    item = _item()
    absta = _completed_abstain(item, "no lawful scale evidence inside the quote")
    facts = K.completed_draft(
        item, '{"source_id": %s, "facts": [{"fact_type": "metric", "item": '
              '{"driver_name": "revenue", "driver_state": "reported"}}], '
              '"abstentions": [], "continuity_hints": []}'
              % json.dumps(item["source_id"]))
    assert facts is not None
    assert K._same_answer(absta, facts) is False
    assert K._same_answer(facts, absta) is False


@pytest.mark.parametrize("field", ["quote", "part_ref", "occurrence_in_part"])
def test_a_moved_abstention_locator_is_not_the_same_answer(field):
    """Everything the abstention carries EXCEPT the prose is still identity."""
    item = _item()
    a = _completed_abstain(item, "the scale marker sits outside the quote")
    b = copy.deepcopy(a)
    got = b["abstentions"][0][field]
    b["abstentions"][0][field] = (got + 1) if isinstance(got, int) \
        else (str(got) + " MOVED")
    assert K._same_answer(a, b) is False


def test_a_different_source_binding_is_not_the_same_answer():
    item = _item()
    a = _completed_abstain(item, "the scale marker sits outside the quote")
    b = copy.deepcopy(a)
    b["source_id"] = a["source_id"] + "_OTHER"
    assert K._same_answer(a, b) is False


def test_an_identical_fact_reply_is_still_the_same_answer():
    """The fact path must be untouched by the projection."""
    item = _item()
    body = ('{"source_id": %s, "facts": [{"fact_type": "metric", "item": '
            '{"driver_name": "revenue", "driver_state": "reported"}}], '
            '"abstentions": [], "continuity_hints": []}'
            % json.dumps(item["source_id"]))
    a, b = K.completed_draft(item, body), K.completed_draft(item, body)
    assert a is not None and K._same_answer(a, b) is True


def test_one_changed_fact_field_is_not_the_same_answer():
    item = _item()
    body = ('{"source_id": %s, "facts": [{"fact_type": "metric", "item": '
            '{"driver_name": "revenue", "driver_state": "reported"}}], '
            '"abstentions": [], "continuity_hints": []}'
            % json.dumps(item["source_id"]))
    a = K.completed_draft(item, body)
    b = copy.deepcopy(a)
    b["facts"][0]["item"]["driver_state"] = "increased"
    assert K._same_answer(a, b) is False


def test_an_added_continuity_proposal_is_not_the_same_answer():
    item = _item()
    a = _completed_abstain(item, "the scale marker sits outside the quote")
    b = copy.deepcopy(a)
    b["continuity_hints"] = [{"note": "carried"}]
    assert K._same_answer(a, b) is False


def test_a_model_boolean_that_contradicts_the_projection_refuses(tmp_path):
    """End to end: the derived projection, never the model's claim, decides."""
    item = _item()
    reason = "the scale marker sits outside the quote"
    body = _abstain_body(item, reason)
    settled = K.completed_draft(item, body)

    def truth(draft):
        return K._same_answer(K.completed_draft(item, draft["text"]), settled)

    honest = _envelope(item, body, _rows_stating(item, truth))
    assert K.read_reply(honest, item)[1] == []

    liar = _envelope(item, body, _rows_stating(item, lambda d: not truth(d)))
    problems = K.read_reply(liar, item)[1]
    assert problems and all("exact_match says" in p for p in problems)


# ============================================== RULING 2 — the attempt pin ===
def test_the_two_lawful_renderings_differ_only_in_the_attempt_value():
    item = _item()
    one, two = K.render_launcher(item, 1), K.render_launcher(item, 2)
    l1, l2 = one.split("\n"), two.split("\n")
    assert len(l1) == len(l2)
    differing = [n for n in range(len(l1)) if l1[n] != l2[n]]
    assert len(differing) == 1, "more than the attempt moved"
    line = differing[0]
    head = "const CALL = "
    assert l1[line].startswith(head) and l2[line].startswith(head)
    c1 = json.loads(l1[line][len(head):])
    c2 = json.loads(l2[line][len(head):])
    assert c1["attempt"] == 1 and c2["attempt"] == 2
    assert {k: v for k, v in c1.items() if k != "attempt"} \
        == {k: v for k, v in c2.items() if k != "attempt"}


def test_the_frozen_manifest_pins_the_base_rendering_for_every_item():
    """The pin is the reviewed base and must never be rewritten per attempt."""
    man = os.path.join(K.PKG_DIR, "phase1.manifest.json")
    rows = {r["packet_id"]: r for r in K._load(man)["items"]}
    items = {i["packet_id"]: i for i in K.phase1_items()}
    assert rows and set(rows) == set(items)
    for key, row in rows.items():
        assert row["script_sha256"] == K._sha(K.render_launcher(items[key], 1))


@pytest.fixture
def one_item(monkeypatch):
    """Schedule exactly one canonical key.

    These controls are about the attempt binding, which is per item; the
    accepted focused file already proves the same route at full 196 scale, so
    re-paying that cost here would buy nothing. The seam is the owner's own
    canonical set, so every receipt stays the one the owner would have written.
    """
    item = _item()
    monkeypatch.setattr(K, "canonical_keys", lambda: [item["packet_id"]])
    return item


def _one_invalid_primary(tmp_path, session, item, run_id="wf_p1"):
    """A COMPLETE primary whose single item is a saved invalid_response."""
    bad = _envelope(item, _abstain_body(item, "prose"),
                    ['{"lane_id": %s, "exact_match": "yes", "why": "x"}'
                     % json.dumps(d["lane_id"]) for d in item["a3_drafts"]])
    state = build_call(session, item, bad, attempt=1, run_id=run_id)
    run = primary_with(tmp_path, session, [state])
    return run


def test_a_lawful_attempt_one_call_is_proved(tmp_path, official, one_item):
    item = one_item
    run = _one_invalid_primary(tmp_path, official, item)
    receipt = K._load(os.path.join(run, "receipt.json"))
    proved, problems = K.run_evidence(run, receipt)
    assert problems == []
    assert proved[item["packet_id"]][0] == "proved"


def test_a_lawful_attempt_two_call_is_proved(tmp_path, official, one_item):
    """RED before the fix: the child could never satisfy the manifest pin."""
    item = one_item
    run = _one_invalid_primary(tmp_path, official, item)
    doc = K.finalize(run)
    child = doc["child"]["dir"]
    state = build_call(official, item, _envelope(
        item, _abstain_body(item, "second look"),
        ['{"lane_id": %s, "exact_match": false, "why": "compared"}'
         % json.dumps(d["lane_id"]) for d in item["a3_drafts"]]),
        attempt=2, run_id="wf_c1")
    assert K.record_state(child, state) == []
    receipt = K._load(os.path.join(child, "receipt.json"))
    assert receipt["attempt"] == 2
    proved, problems = K.run_evidence(child, receipt)
    assert problems == []
    assert proved[item["packet_id"]][0] == "proved"


@pytest.mark.parametrize("what", ["script", "prompt", "model", "tools",
                                  "attempt"])
def test_every_current_attempt_launcher_mutation_refuses(tmp_path, official,
                                                         one_item, what):
    """The attempt-2 proof is not weaker: each of these still refuses."""
    item = one_item
    run = _one_invalid_primary(tmp_path, official, item)
    child = K.finalize(run)["child"]["dir"]
    answer = _envelope(item, _abstain_body(item, "second look"),
                       ['{"lane_id": %s, "exact_match": false, "why": "c"}'
                        % json.dumps(d["lane_id"]) for d in item["a3_drafts"]])

    def mutate(doc):
        if what == "script":
            doc["script"] = doc["script"] + "\n// edited\n"
        elif what == "prompt":
            doc["script"] = doc["script"].replace("const PROMPT = ",
                                                  "const PROMPT = 'x' + ")
        elif what == "model":
            doc["script"] = doc["script"].replace(json.dumps(K.MODEL),
                                                  json.dumps("other-model"))
        elif what == "tools":
            doc["script"] = doc["script"].replace(
                "disallowedTools: ", "disallowedTools: [] || ")
        elif what == "attempt":
            doc["script"] = K.render_launcher(item, 1)

    state = build_call(official, item, answer, attempt=2, run_id="wf_c2",
                       doc_mutate=mutate)
    assert K.record_state(child, state) == []
    receipt = K._load(os.path.join(child, "receipt.json"))
    proved, problems = K.run_evidence(child, receipt)
    assert problems, "%s must not be provable" % what
    assert proved[item["packet_id"]][0] == "unproved"


def test_a_third_attempt_is_impossible(tmp_path):
    out = str(tmp_path / "third")
    os.makedirs(out)
    receipt = K.expected_receipt(out, 3, K.canonical_keys()[:1], None)
    bad = K.receipt_problems(out, receipt)
    assert bad and any("outside 1..%d" % K.MAX_ATTEMPTS in b for b in bad)
