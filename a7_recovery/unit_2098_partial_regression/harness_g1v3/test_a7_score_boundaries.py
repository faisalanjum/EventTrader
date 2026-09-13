"""Generic output shapes and exact score thresholds; no model judgments here."""
import copy
import itertools
import json
import re

import pytest

import a7_g1_build as G
import a7_g23_build as B
from scorers import score_exp5_current as S


def test_current_extra_answers_do_not_consult_the_producer_scorer(monkeypatch):
    expected = ["duplicate", "key_miss", "unsupported"]  # Step 1 A7 extras rule.
    assert B.extras_buckets() == list(B._scorer().EXTRAS_BUCKETS) == expected
    rules = B.extras_rules()

    def retired_owner():
        raise AssertionError("current grading read the producer-era bucket owner")

    monkeypatch.setattr(G._a6(), "_extras_buckets", retired_owner)
    assert B.extras_buckets() == expected
    assert B.extras_rules() == rules
    test_every_legal_extra_answer_and_every_blind_pair_still_works()


def test_extra_review_template_shows_a_shape_not_an_example_answer():
    output = B.extras_rules().split("[OUTPUT]", 1)[1].split(G.BOUNDARY, 1)[0]
    template = json.loads(re.search(r"\n(\[\s*\{.*?\}\s*\])\n", output, re.S).group(1))
    placeholder = template[0]["bucket"]
    assert placeholder not in B.extras_buckets() + [None]
    assert all(value in placeholder for value in B.extras_buckets() + ["null"])
    template[0]["question_id"] = "TEST_question"
    answer, problems = B.read_extras_reply(json.dumps(template), {"question_ids": ["TEST_question"]})
    assert answer is None and problems


def test_every_legal_extra_answer_and_every_blind_pair_still_works():
    packet = {"question_ids": ["TEST_question"]}
    choices = B.extras_buckets() + [None]
    for choice in choices:
        answer, problems = B.read_extras_reply(
            json.dumps([{"question_id": "TEST_question", "bucket": choice}]), packet)
        assert problems == [] and answer == {"TEST_question": choice}
    for first, second in itertools.product(choices, repeat=2):
        agreed, unresolved = B.reconcile_extras({"TEST_question": first}, {"TEST_question": second})
        if first is not None and first == second:
            assert agreed == {"TEST_question": first} and not unresolved
        else:
            assert agreed == {} and len(unresolved) == 1
    for body in (
            [{"question_id": "TEST_question", "bucket": "unknown"}],
            [{"question_id": "TEST_question", "bucket": True}],
            [{"question_id": "TEST_question", "bucket": []}],
            [{"question_id": "TEST_question", "bucket": None, "extra": 1}],
            [{"question_id": "TEST_question"}], [],
            [{"question_id": "different", "bucket": None}]):
        answer, problems = B.read_extras_reply(json.dumps(body), packet)
        assert answer is None and problems


@pytest.mark.parametrize("aspect", S.MEANING_FIELDS)
@pytest.mark.parametrize("first,second", itertools.product((True, False, None), repeat=2))
def test_all_seven_aspects_preserve_every_blind_agreement_and_wait(aspect, first, second):
    fields = dict.fromkeys(S.MEANING_FIELDS, True)
    a, b = dict(fields, **{aspect: first}), dict(fields, **{aspect: second})
    packet = {"question_ids": ["TEST"]}
    readings = []
    for verdict in (a, b):
        parsed, problems = B.read_meaning_reply(
            json.dumps([{"question_id": "TEST", "verdicts": verdict}]), packet)
        assert problems == []
        readings.append(parsed)
    agreed, unresolved = B.reconcile_meaning(*readings)
    if first is not None and first == second:
        assert agreed == {"TEST": a} and unresolved == []
    else:
        assert agreed == {} and len(unresolved) == 1
        assert unresolved[0]["question_id"] == "TEST"
        assert unresolved[0]["aspect"] == aspect
        assert unresolved[0]["established"] == {k: True for k in fields if k != aspect}


@pytest.fixture(scope="module")
def one_accepted_fact(tmp_path_factory):
    import test_harness_guards as T
    from kf_lint import GOLD_ONLY
    quote = "The TEST metric was 5 million dollars in the stated quarter."
    fact = T._gold_fact(quote, item=T._mut_item(quote))
    gold = {"E1": [fact]}
    arm = {"E1": {"facts": [{k: copy.deepcopy(v) for k, v in fact.items() if k not in GOLD_ONLY}]}}
    route = T._route_for(arm, tmp_path_factory.mktemp("meaning_safety"))
    assert route["E1"]["result"]["items"][0]["decision"] == "written"

    def score(verdicts=None, **kwargs):
        return S.score_arm(gold, arm, T._META1,
                           grader_verdicts={("E1", 0): verdicts} if verdicts is not None else None,
                           route=route, **kwargs)
    assert score(dict.fromkeys(S.MEANING_FIELDS, True))["PASS"] is True
    return score


@pytest.mark.parametrize("false_aspect", S.MEANING_FIELDS)
def test_a_known_wrong_accept_survives_every_other_missing_aspect(one_accepted_fact, false_aspect):
    for unknown in S.MEANING_FIELDS:
        if unknown == false_aspect:
            continue
        verdict = dict.fromkeys(S.MEANING_FIELDS, True)
        verdict[false_aspect], verdict[unknown] = False, None
        result = one_accepted_fact(verdict)
        assert result["confirmed_wrong_accepted"] == 1
        assert result["required_grading_unfinished"] is True
        assert S.final_gate(result, union_required=True) is False
    pending = dict.fromkeys(S.MEANING_FIELDS, True)
    pending[false_aspect] = None
    result = one_accepted_fact(pending)
    assert result["confirmed_wrong_accepted"] == 0
    assert S.final_gate(result) is None


@pytest.mark.parametrize("responses,required,want", [
    (None, False, True), (None, True, None),
    ({"total": 0, "invalid": 0}, True, None),
    ({"total": 50, "invalid": 0}, True, True),
    ({"total": 50, "invalid": 1}, True, True),
    ({"total": 49, "invalid": 1}, True, False),
])
def test_observed_reliability_and_missing_observations_reach_the_final_gate(one_accepted_fact, responses, required, want):
    result = one_accepted_fact(dict.fromkeys(S.MEANING_FIELDS, True),
                               responses=responses, responses_required=required)
    assert S.final_gate(result) is want


@pytest.mark.parametrize("finding,want", [
    ("confirmed_duplicate_groups", False),
    ("disputed_identity_groups", None), ("incomplete", None),
])
def test_g1_findings_are_not_lost_before_the_final_gate(one_accepted_fact, finding, want):
    result = one_accepted_fact(dict.fromkeys(S.MEANING_FIELDS, True),
                               safety_findings={finding: [{"TEST": True}]})
    assert S.final_gate(result) is want


@pytest.fixture(scope="module")
def score_population(tmp_path_factory):
    """Real no-write route and score_arm, not a hand-written displayed score."""
    import test_harness_guards as T
    from kf_lint import GOLD_ONLY
    gold = []
    for i in range(450):
        quote = "TEST metric %d was 5 USD million in the stated quarter." % i
        item = T._v2_item(quote, driver_name="test_metric_%d" % i,
                          time_type="duration", period_start_date="2026-01-01",
                          period_end_date="2026-03-31",
                          level_low=T._v2_slot(quote, value=5),
                          level_high=T._v2_slot(quote, value=5),
                          level_shape_hint="point", level_unit="m_usd")
        gold.append(T._gold_fact(quote, item=item))
    facts = [{k: copy.deepcopy(v) for k, v in f.items() if k not in GOLD_ONLY} for f in gold]
    root = tmp_path_factory.mktemp("exact_score")

    def score(matched, total, name):
        wanted = {"E1": gold[:total]}
        produced = {"E1": {"facts": facts[:matched]}}
        verdicts = {("E1", i): dict.fromkeys(S.MEANING_FIELDS, True) for i in range(matched)}
        missing = {("E1", i): None for i in range(matched, total)}
        directory = root / name
        directory.mkdir()
        route = T._route_for(produced, directory)
        result = S.score_arm(wanted, produced, T._META1, grader_verdicts=verdicts,
                             ambiguity_resolutions=missing, route=route)
        assert result["gold_n"] == total and result["matched"] == matched
        assert result["wrong_lane"] == 0
        assert result["would_park"] == 0
        assert not result["confirmed_wrong_accepted"] and not result["duplicate_violations"]
        return result
    return score


def test_a_real_rounded_up_union_score_must_not_pass(score_population):
    below = score_population(440, 449, "below")
    exact = score_population(441, 450, "exact")
    assert 440 * 100 < 449 * 98
    assert 441 * 100 == 450 * 98
    assert below["recall"] == exact["recall"] == 0.98
    assert below["PASS"] is True and exact["PASS"] is True  # both meet the single's 95%
    assert S._leg(exact, 0.98) is True
    assert S._leg(below, 0.98) is False
    single = score_population(400, 449, "single")
    assert single["PASS"] is False
    assert S.final_gate(single, below, originals=[single, single], union_required=True) is False
    exact_single = score_population(400, 450, "exact_single")
    assert S.final_gate(exact_single, exact, originals=[exact_single, exact_single], union_required=True) is True


@pytest.mark.parametrize("matched,total,bar,want", [
    (18, 20, 0.95, False), (19, 20, 0.95, True), (20, 20, 0.95, True),
    (48, 50, 0.98, False), (49, 50, 0.98, True), (50, 50, 0.98, True),
    (0, 0, 0.95, False), (0, 0, 0.98, False),
    (440, 449, 0.98, False), (441, 450, 0.98, True),
])
def test_exact_count_boundaries_ignore_display_rounding(matched, total, bar, want):
    result = {"matched": matched, "gold_n": total, "recall": round(matched / total, 4) if total else 0,
              "PASS": True, "wrong_lane": 0, "would_park": 0, "value_shape_acc": 1}
    assert S._leg(result, bar) is want


def test_display_value_never_replaces_counts_and_failures_precede_unknown():
    base = {"matched": 98, "gold_n": 100, "recall": 0,
            "PASS": True, "wrong_lane": 0, "would_park": 0, "value_shape_acc": 1}
    assert S._leg(base, 0.98) is True
    with pytest.raises(KeyError):
        S._leg({k: v for k, v in base.items() if k != "matched"}, 0.98)
    pending = dict(base, required_grading_unfinished=True)
    assert S.final_gate(base, pending, originals=[base, base], union_required=True) is None
    for reason in ("confirmed_wrong_accepted", "duplicate_violations", "reliability_failed"):
        bad = dict(base, **{reason: True})
        assert S.final_gate(bad, pending, originals=[bad, base], union_required=True) is False
