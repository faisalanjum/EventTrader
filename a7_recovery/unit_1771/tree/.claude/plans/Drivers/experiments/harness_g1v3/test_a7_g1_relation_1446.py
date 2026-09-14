"""RED-FIRST tests for the event-scoped identity relation (Codex SEQ 1446).

Written before the implementation. Structural only: no expected meaning is
derived from locator equality or from the code under test. The two semantic
controls are displayed for independent review, never asserted from the harness.
Runs from ONE clean harness path: this versioned scratch copy.
"""
import io, json, os, sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import a7_g1_build as G
assert os.path.dirname(os.path.abspath(G.__file__)) == HERE, G.__file__

FROZEN = "/tmp/a7_g1_v14"


@pytest.fixture(scope="module")
def inv():
    items, legs, totals, meta, problems = G.questions()
    assert problems == []
    doc, _sha = G.load_frozen(FROZEN, G._sha_file(
        os.path.join(FROZEN, "a7_g1_candidate.json")))
    return legs, G.event_groups(items), doc, items



def _expected_questions():
    """THE questions the frozen key and the eligibility owner require.

    Derived here from the KEY and the ELIGIBILITY owner directly, never read
    back from the population being proved - and never a fixed number. `448` was
    such a number: it was the count before the conflicting-name eligibility
    correction, so it pinned an answer the owners had already stopped giving
    (Codex SEQ 1469 item 7).
    """
    import collections
    from driver.core.fact_match import match_facts
    from scorers import score_exp5 as SCO
    gold_by_ev, _identity = G.live_key()
    arms, _meta, _p = G.materialize(RUN)
    # THE UNION LEG IS GRADED TOO, and it is built by the same union owner the
    # route uses. Deriving only the two produced arms missed it entirely.
    a, b = sorted(arms)
    arms = collections.OrderedDict(
        list(arms.items())
        + [(G.LEG_UNION, SCO.union_answer(gold_by_ev, arms[a], arms[b],
                                          (a, b)))])
    out = set()
    for leg in sorted(arms):
        for sid, gold in gold_by_ev.items():
            du = [g for g in gold if g.get("du_worthy") is True]
            produced = (arms[leg].get(sid) or {}).get("facts", [])
            gold_v2, gold_pos = SCO._to_v2_with_positions(du)
            prod_v2, _pp = SCO.eligible_produced(produced)
            mr = match_facts(gold_v2, prod_v2)
            skip = {gold_pos[id(g)]
                    for group in mr.gold_inconclusive for g in group}
            for g in mr.to_grading_gold:
                idx = gold_pos[id(g)]
                if idx not in skip:
                    out.add(G.question_id(leg, sid, idx))
    return out


# ------------------------------------------------------------- inventory ----
def test_every_question_the_key_and_eligibility_owner_require_is_grouped(inv):
    legs, groups, doc, items = inv
    groups = G.expected_groups(legs)
    want = _expected_questions()
    got = sum(len(legs[l][s]["unmatched_gold"]) for l, s in groups)
    assert got == len(want), (got, len(want))
    # every group is one (leg, event); nothing is grouped that has no question
    assert len(groups) == len({(l, s) for l, s in groups})
    assert groups, "no group at all"


def test_each_group_serializes_every_gold_and_produced_row_exactly_once(inv):
    legs, groups, doc, items = inv
    for leg, sid in G.expected_groups(legs):
        p = G.event_packet(groups[(leg, sid)])
        row = legs[leg][sid]
        assert len(p["questions"]) == len(row["unmatched_gold"])
        assert len({q["question_id"] for q in p["questions"]}) == len(p["questions"])
        assert sorted(p["produced_idxs"]) == sorted(row["unmatched_produced"])
        assert len(set(p["produced_idxs"])) == len(p["produced_idxs"])


def test_no_group_mixes_events_and_prompts_hide_leg_and_source(inv):
    legs, groups, doc, items = inv
    for leg, sid in G.expected_groups(legs):
        p = G.event_packet(groups[(leg, sid)])
        row = legs[leg][sid]
        # EVERY QUESTION IS THIS GROUP'S OWN, proved from the group's identity
        # through the id owner. This used to look each id up in the FROZEN
        # candidate's bindings, so once the accepted eligibility correction
        # changed the question set the live population could no longer be
        # checked at all - it raised KeyError on a question that is correct.
        mine = {G.question_id(leg, sid, idx) for idx in row["unmatched_gold"]}
        assert {q["question_id"] for q in p["questions"]} == mine, (
            leg, sid)
        text = p["prompt"]
        assert leg not in text, "the prompt leaks the leg"
        assert sid not in text, "the prompt leaks the source id"


def test_the_rules_block_is_byte_identical_across_every_event(inv):
    legs, groups, doc, items = inv
    seen = set()
    for leg, sid in G.expected_groups(legs):
        p = G.event_packet(groups[(leg, sid)])
        seen.add(p["prompt"].split(G.BOUNDARY)[0])
    assert len(seen) == 1, "the fixed rules block must not vary by event"


def test_the_old_one_to_one_instruction_is_gone(inv):
    """The live batch prompt told the model 'One candidate may be chosen by at
    most one question' - the 1:1 assumption that caused the defect."""
    legs, groups, doc, items = inv
    leg, sid = G.expected_groups(legs)[0]
    text = G.event_packet(groups[(leg, sid)])["prompt"]
    assert "at most one question" not in text
    assert "unrelated" not in text


# ---------------------------------------------------------------- parser ----
def _packet(inv, n=0):
    legs, groups, doc, items = inv
    return G.event_packet(list(groups.values())[n])


def _reply(pk, mapping):
    return json.dumps([{"question_id": q["question_id"],
                        "produced_idxs": mapping.get(q["question_id"], [])}
                       for q in pk["questions"]])


def test_parser_accepts_zero_one_and_many_indices(inv):
    pk = _packet(inv)
    qs = [q["question_id"] for q in pk["questions"]]
    idx = sorted(pk["produced_idxs"])
    m = {qs[0]: []}
    if len(idx) >= 1: m[qs[0]] = [idx[0]]
    if len(qs) > 1 and len(idx) >= 2: m[qs[1]] = [idx[0], idx[1]]
    rel, probs = G.read_event_reply(_reply(pk, m), pk)
    assert probs == [], probs
    assert all(isinstance(v, tuple) for v in rel.values())


def test_parser_accepts_the_same_produced_index_on_several_gold_rows(inv):
    pk = _packet(inv)
    qs = [q["question_id"] for q in pk["questions"]]
    if len(qs) < 2: pytest.skip("event has one gold row")
    p = sorted(pk["produced_idxs"])[0]
    rel, probs = G.read_event_reply(_reply(pk, {qs[0]: [p], qs[1]: [p]}), pk)
    assert probs == [], "cross-gold reuse is evidence, not credit"


@pytest.mark.parametrize("mutate,why", [
    (lambda pk, qs, i: {qs[0]: [i[0], i[0]]}, "repeated index in one array"),
    (lambda pk, qs, i: {qs[0]: [max(i) + 999]}, "off-list produced index"),
    (lambda pk, qs, i: {qs[0]: [True]}, "boolean is not an index"),
])
def test_parser_rejects_bad_index_payloads(inv, mutate, why):
    pk = _packet(inv)
    qs = [q["question_id"] for q in pk["questions"]]
    i = sorted(pk["produced_idxs"])
    _rel, probs = G.read_event_reply(_reply(pk, mutate(pk, qs, i)), pk)
    assert probs, why


def test_parser_rejects_shape_defects(inv):
    pk = _packet(inv)
    base = json.loads(_reply(pk, {}))
    for label, payload in (
            ("unknown question", base[:-1] + [{"question_id": "Qdeadbeefdeadbeef",
                                               "produced_idxs": []}]),
            ("missing question", base[:-1]),
            ("extra question", base + [dict(base[0])]),
            ("missing key", [{"question_id": base[0]["question_id"]}] + base[1:]),
            ("extra key", [dict(base[0], extra=1)] + base[1:]),
    ):
        _rel, probs = G.read_event_reply(json.dumps(payload), pk)
        assert probs, label
    _rel, probs = G.read_event_reply("not json at all", pk)
    assert probs, "malformed payload"


def test_one_bad_event_cannot_invalidate_another(inv):
    good = _packet(inv, 0); other = _packet(inv, 1)
    _r, bad = G.read_event_reply("garbage", good)
    rel, probs = G.read_event_reply(_reply(other, {}), other)
    assert bad and probs == [], "events are independent"


# ---------------------------------------------------------------- credit ----
def _credit(a, b):
    return G.event_credit(a, b)


def test_identical_isolated_one_to_one_links_credit():
    acc, rep = _credit({0: (5,)}, {0: (5,)})
    assert acc == {0: 5}
    assert rep["accepted"] == 1


def test_two_valid_empty_sets_are_a_decided_miss_not_an_absent_answer():
    acc, rep = _credit({0: ()}, {0: ()})
    assert acc == {}
    assert rep["no_link"] == 1 and rep.get("absent", 0) == 0


def test_any_lane_difference_gets_zero():
    acc, rep = _credit({0: (5,)}, {0: (6,)})
    assert acc == {} and rep["disagreement"] == 1


def test_an_agreed_edge_touched_by_a_one_lane_competing_edge_gets_zero():
    acc, rep = _credit({0: (5,)}, {0: (5, 6)})
    assert acc == {}, "a disputed competing link must suppress the agreed edge"


def test_agreed_one_gold_many_produced_gets_zero_and_is_reported():
    acc, rep = _credit({0: (5, 6)}, {0: (5, 6)})
    assert acc == {} and rep["one_gold_many_produced"] == 1


def test_agreed_many_gold_one_produced_gets_zero_and_is_reported():
    acc, rep = _credit({0: (5,), 1: (5,)}, {0: (5,), 1: (5,)})
    assert acc == {} and rep["many_gold_one_produced"] == 1


def test_agreed_many_to_many_gets_zero_and_is_reported():
    acc, rep = _credit({0: (5, 6), 1: (5,)}, {0: (5, 6), 1: (5,)})
    assert acc == {} and rep["many_to_many"] >= 1


def test_no_produced_row_can_be_credited_twice():
    acc, rep = _credit({0: (5,), 1: (5,)}, {0: (5,), 1: (5,)})
    assert len(set(acc.values())) == len(acc)


def test_an_unrelated_clean_pair_in_the_same_event_still_credits():
    acc, rep = _credit({0: (5,), 1: (7, 8)}, {0: (5,), 1: (7, 8)})
    assert acc == {0: 5}, "one messy component must not poison a clean one"


# ------------------------------------------------------------ population ----
def test_population_conserves_every_required_question_exactly_once(inv):
    legs, groups, doc, items = inv
    seen_q, seen_pairs, seen_prod = set(), 0, 0
    for key, group in groups.items():
        p = G.event_packet(group)
        seen_q |= {q["question_id"] for q in p["questions"]}
        seen_pairs += len(p["questions"])
        seen_prod += len(p["produced_idxs"])
    # EXACT SET EQUALITY against the owners, and each asked exactly once
    want = _expected_questions()
    assert seen_q == want, (
        len(seen_q - want), len(want - seen_q))
    assert seen_pairs == len(want), (seen_pairs, len(want))
    assert seen_prod > 0
    assert sorted(groups) == sorted(G.expected_groups(legs))


def test_all_seven_historical_conflicts_are_co_visible_now(inv):
    """Structural only: the two gold rows that were credited one produced row
    must appear in ONE event packet. Their old judgments are not truth here."""
    legs, groups, doc, items = inv
    comp = json.load(io.open("/tmp/a7_g1_completion_1441.json"))
    byk = {(b["leg"], b["source_id"], b["gold_idx"]): b["question_id"]
           for b in doc["question_bindings"]}
    for pr in comp["validation"]["problems"]:
        pk = G.event_packet(groups[(pr["leg"], pr["sid"])])
        ids = {q["question_id"] for q in pk["questions"]}
        for g in pr["gold_idxs"]:
            assert byk[(pr["leg"], pr["sid"], g)] in ids
        assert pr["produced_idx"] in pk["produced_idxs"]


# ------------------------------- validate_merged as the one credit owner ----
def test_validate_merged_projects_a_scalar_into_the_unchanged_scorer(inv):
    legs, groups, doc, items = inv
    leg, sid = G.expected_groups(legs)[0]
    row = legs[leg][sid]
    g0 = row["unmatched_gold"][0]; p0 = row["unmatched_produced"][0]
    rel = {g: () for g in row["unmatched_gold"]}
    rel[g0] = (p0,)
    pairs, problems, incomplete, report = G.validate_merged(
        {leg: {sid: (rel, dict(rel))}}, legs)
    assert problems == [], problems
    assert report[(leg, sid)]["accepted"] == 1
    assert len(incomplete) == 104, "every other event has no lane answer"


def test_validate_merged_marks_a_missing_lane_incomplete_not_credited(inv):
    legs, groups, doc, items = inv
    leg, sid = G.expected_groups(legs)[0]
    row = legs[leg][sid]
    rel = {g: () for g in row["unmatched_gold"]}
    pairs, problems, incomplete, report = G.validate_merged(
        {leg: {sid: (rel, None)}}, legs)
    assert (leg, sid) not in report
    assert any(i["leg"] == leg and i["sid"] == sid for i in incomplete)


def test_the_credit_path_contains_no_locator_logic():
    """Codex's 'choose by locator' mutation is INAPPLICABLE by construction:
    there is no locator code in the credit path to mutate."""
    src = io.open(os.path.join(HERE, "a7_g1_build.py"), encoding="utf-8").read()
    body = src[src.index("def event_credit("):src.index("def expected_groups(")]
    for banned in ("_locator", "part_ref", "occurrence_in_part", "quote"):
        assert banned not in body, "credit path must not consult %s" % banned


# ------------------------------------------------- displayed controls -------
#: Chosen by READING the records (values, periods, quotes), never from locator
#: equality and never from the code under test. Their MEANINGS are asserted by
#: Core in SEQ 1265 for Codex's independent review; the tests below assert only
#: that the new contract can PRESENT and EXPRESS them.
CONTROL_EVENT = ("P1", "0000027904-26-000013")


def _control_packet(inv):
    legs, groups, doc, items = inv
    leg, sid = CONTROL_EVENT
    return leg, sid, G.event_packet(groups[(leg, sid)])


def test_control_A_same_claim_field_error_is_co_visible_and_expressible(inv):
    """gold 0 and produced 0 carry the SAME number (17), SAME period (FY2025)
    and the SAME quote; only the extracted driver_name differs. Rule 4 says a
    wrong field alone is not a different claim."""
    leg, sid, pk = _control_packet(inv)
    assert 0 in pk["gold_idxs"] and 0 in pk["produced_idxs"]
    qid = G.question_id(leg, sid, 0)
    rel, probs = G.read_event_reply(json.dumps(
        [{"question_id": q["question_id"],
          "produced_idxs": [0] if q["question_id"] == qid else []}
         for q in pk["questions"]]), pk)
    assert probs == [] and rel[0] == (0,)


def test_control_B_distinct_claims_sharing_one_quote_stay_separable(inv):
    """gold 0 (17%, FY2025) and gold 1 (19%, FY2024) are DISTINCT claims that
    share ONE quote. Locator equality would call them the same; reading the
    numbers and periods says otherwise. The contract must let a reviewer link
    produced 0 to gold 0 alone."""
    leg, sid, pk = _control_packet(inv)
    assert {0, 1}.issubset(set(pk["gold_idxs"]))
    q0, q1 = G.question_id(leg, sid, 0), G.question_id(leg, sid, 1)
    rel, probs = G.read_event_reply(json.dumps(
        [{"question_id": q["question_id"],
          "produced_idxs": [0] if q["question_id"] == q0 else []}
         for q in pk["questions"]]), pk)
    assert probs == [] and rel[0] == (0,) and rel[1] == ()
    acc, rep = G.event_credit(rel, dict(rel))
    assert acc == {0: 0}, "the separable link is creditable"


def test_control_C_a_real_merge_is_expressible_and_earns_zero(inv):
    """gold 9 ($0.15) and gold 10 ($0.1875) are two distinct dividend claims;
    produced 6 spans BOTH (lo=0.15, hi=0.1875). This is one of the seven
    historical cross-batch duplicates. The contract must let a reviewer SAY
    produced 6 attempts both - and that relation must earn ZERO credit."""
    leg, sid, pk = _control_packet(inv)
    assert {9, 10}.issubset(set(pk["gold_idxs"])) and 6 in pk["produced_idxs"]
    rel = {g: ((6,) if g in (9, 10) else ()) for g in pk["gold_idxs"]}
    acc, rep = G.event_credit(rel, dict(rel))
    assert acc == {} and rep["many_gold_one_produced"] == 1
