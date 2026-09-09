"""T06: current G1 reply/credit boundary; structured TEST data, no model truth.

The 1825 historical parser cases are retained in their original evidence.
This portable check also covers every pair of two-by-two blind relations,
including a competing edge stated by only one reviewer. No application change.
"""
import copy
import itertools
import json

import pytest

import a7_g1_build as G

GOLDS, PRODUCED = (3, 17), (5, 23)
PACKET = {"questions": [{"question_id": "Q3"}, {"question_id": "Q17"}],
          "produced_idxs": list(PRODUCED), "q_to_gold": {"Q3": 3, "Q17": 17}}
LEGS = {"P1": {"TEST_event": {"unmatched_gold": list(GOLDS),
                               "unmatched_produced": list(PRODUCED)}}}


def _reply(bits):
    edges = list(itertools.product(GOLDS, PRODUCED))
    return [{"question_id": "Q%d" % g,
             "produced_idxs": [p for n, (h, p) in enumerate(edges)
                               if h == g and bits & (1 << n)]} for g in GOLDS]


@pytest.mark.parametrize("first_bits", range(16))
@pytest.mark.parametrize("second_bits", range(16))
def test_every_two_by_two_blind_relation_preserves_only_uncontested_credit(first_bits, second_bits):
    a, b = _reply(first_bits), _reply(second_bits)
    # Independent oracle: identical singleton answers, and no other question
    # in either answer mentions that produced record. No graph/degree helper.
    expected = []
    for i, g in enumerate(GOLDS):
        ps = a[i]["produced_idxs"]
        if len(ps) == 1 and ps == b[i]["produced_idxs"] and all(
                ps[0] not in rows[j]["produced_idxs"]
                for rows in (a, b) for j in range(len(GOLDS)) if j != i):
            expected.append((g, ps[0]))
    for reversed_order in (False, True):
        relations = []
        for rows in (a, b):
            served = copy.deepcopy(rows)
            if reversed_order:
                served.reverse()
                for row in served:
                    row["produced_idxs"].reverse()
            text = json.dumps(served)
            for raw in (text, "```json\n" + text + "\n```"):
                relation, problems = G.read_event_reply(raw, PACKET)
                assert problems == []
            relations.append(relation)
        supplied = {"P1": {"TEST_event": relations}}
        pairs, problems, incomplete, report = G.validate_merged(supplied, LEGS)
        assert problems == incomplete == []
        assert pairs == {"P1": {"TEST_event": expected}}
        terminals = G.terminal_categories(supplied, LEGS)
        assert set(terminals) == {("P1", "TEST_event", g) for g in GOLDS}
        assert sum(v == "accepted" for v in terminals.values()) == len(expected)
        assert report[("P1", "TEST_event")]["accepted_pairs"] == expected


@pytest.mark.parametrize("bad", [None, True, 1, [], {}, "", "Qforeign"])
def test_invalid_question_identity_never_leaves_partial_credit(bad):
    base = _reply(9)
    good, problems = G.read_event_reply(json.dumps(base), PACKET)
    assert problems == [] and good == {3: (5,), 17: (23,)}
    base[0]["question_id"] = bad
    got, problems = G.read_event_reply(json.dumps(base), PACKET)
    assert got == {} and problems


@pytest.mark.parametrize("bad", [None, True, 1, {}, "5", [True], [5.0], [-1], [99], [5, 5]])
def test_invalid_produced_index_never_leaves_partial_credit(bad):
    base = _reply(9)
    good, problems = G.read_event_reply(json.dumps(base), PACKET)
    assert problems == [] and good == {3: (5,), 17: (23,)}
    base[0]["produced_idxs"] = bad
    got, problems = G.read_event_reply(json.dumps(base), PACKET)
    assert got == {} and problems


def test_missing_extra_duplicate_and_wrong_shape_answers_are_not_completion():
    base = _reply(9)
    good, problems = G.read_event_reply(json.dumps(base), PACKET)
    assert problems == [] and len(good) == len(GOLDS)
    cases = [base[:-1], base + [base[0]], base + [{"question_id": "Qforeign", "produced_idxs": []}],
             [dict(base[0], extra=True), base[1]], [{"question_id": "Q3"}, base[1]],
             [None, base[1]], {}, None]
    for rows in cases:
        got, problems = G.read_event_reply(json.dumps(rows), PACKET)
        assert got == {} and problems
    for pair in (None, (good, None), (None, good)):
        supplied = {"P1": {"TEST_event": pair}}
        pairs, problems, incomplete, _ = G.validate_merged(supplied, LEGS)
        assert pairs == {} and problems == []
        assert len(incomplete) == 1 and incomplete[0]["of"] == len(GOLDS)
        assert set(G.terminal_categories(supplied, LEGS).values()) == {"absent"}
    _, problems, _, _ = G.validate_merged({"foreign": {"TEST_event": (good, good)}}, LEGS)
    assert problems == [{"leg": "foreign", "sid": "TEST_event", "reason": "event_not_in_this_leg"}]
