"""Codex SEQ 1454 - the three reproduced defects, each RED first.

Every test here is CLASS-WIDE (it asserts over the whole live key or the whole
scorer contract, never over one hand-picked row), and each carries a LAWFUL
POSITIVE CONTROL plus a MUTATION that must fail. Nothing here decides meaning:
the terminal-suffix question of OD-1 is a semantic judgment and stays with a
qualified reviewer; these checks are mechanical only.

Law quoted, live files:
  FINAL_DESIGN.md:97   NAME-17  terminal `_guidance`/`_surprise` stay in the
                       name and also fix permanent `fact_type`.
  FINAL_DESIGN.md:116  OD-2     "C1=guidance/surprise on a BARE name -> a
                       NAMING defect, never a stamp ... re-coin with the
                       suffix through OD-1, else the fact parks."
  FINAL_DESIGN.md:115  OD-1     strip exactly ONE terminal suffix; the
                       admission question runs TWICE independently.
  exp5_scoring_spec_v3.md:87    "Guard: if the model emits the SAME
                       driver_name with CONFLICTING fact_types across facts,
                       reject that name (one name cannot be two types)."
  exp5_scoring_spec_v3.md:97-108  the LOCKED capability bars are recall,
                       wrong-lane, value_shape_acc, state and would_park.
                       `wrong_name` is NOT among them, and "name-meaning" is
                       listed as an ADJUDICATED confirmed-wrong field.
"""
import collections
import hashlib
import io
import hashlib
import io
import json
import os
import sys

import pytest
from test_a7_input_binding import run, inputs

_HERE = os.path.dirname(os.path.abspath(__file__))
while _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)

import a7_g1_build as G                                          # noqa: E402
from test_harness_guards import (_synthetic_event, _route_for,   # noqa: E402
                                 _v2_fact, _v2_item, _v2_slot)

# THE terminal-suffix owner. This file re-owned the strings and the split
# logic; both live in driver.core.driver_ids and are imported, never restated.
from driver.core.driver_ids import (GUIDANCE_SUFFIX, SURPRISE_SUFFIX,
                                    split_terminal_suffix, valid_driver_name)

import a7_prepared_run as _PR                                    # noqa: E402
import a7_g1_build as _G                                         # noqa: E402

#: THE run these proofs are about, named out loud. Nothing defaults to it.
_RUN = None
_INPUTS = None

#: HISTORICAL EVIDENCE. The only executed producer run is v1-era, so the
#: live era gate is relaxed for these structural proofs by the ONE named
#: fixture in conftest.py. See its docstring: when the fresh v3 run
#: exists, these must pass without it.
@pytest.fixture(autouse=True, scope="module")
def _current_context(run, inputs):
    """Current signed TEST key/producer, with no historical era relaxation."""
    global _RUN, _INPUTS
    _RUN, _INPUTS = run, inputs
    yield
    _RUN = _INPUTS = None

#: fact_type -> the terminal suffix its lawful family name must carry, derived
#: from the owner's own constants (NAME-17).
REQUIRED_SUFFIX = {"guidance": GUIDANCE_SUFFIX, "surprise": SURPRISE_SUFFIX}


def _du_facts():
    """Every accepted gold fact of the key this candidate uses.

    A4-v6 itself is preserved as IMMUTABLE HISTORICAL EVIDENCE and is known to
    carry the bare-name defect; it is never edited. The corrected key is a NEW
    version derived from it through the evidence-bound ledger, so the law is
    asserted over that version. Pass corrected=False to assert over the
    historical key, which is how the defect was first proved.
    """
    import a7_key_correction as K
    gold, _identity = K.current_key()
    return [(sid, f) for sid in sorted(gold) for f in gold[sid]
            if f.get("du_worthy") is True]


def _name(fact):
    return (fact.get("item") or {}).get("driver_name")


# ------------------------------------------------- defect 1: bare names -----
def test_defect1_the_historical_key_is_preserved_with_its_bare_name_defect():
    """Preserve the old key's exact evidence; it is not today's approved key.

    The retired assertion rederived 50 historical naming defects through a
    different era's full A3/A4 workflow. Current correctness is tested by the
    complete approved key below; these hashes prove its history was not edited.
    """
    import a7_key_correction as K
    assert G._sha_file(K.LEDGER_PATH) == "e110c1eb642728c706530c87451a5e508b71b72d0ea68658107ed5a15255b2f6"
    assert G._sha_file("/tmp/a7_key_v9_gold.json") == "71de3716ecfb12f478d2fdb50fded5cc3b41314616ee23ecbc301b5896458192"
    key, identity = K.current_key()
    assert identity["schema"] == "a7-current-key/approved"
    assert identity["acted_rows"] == 0 and key


def test_defect1_every_guidance_or_surprise_gold_row_carries_its_terminal_suffix():
    """NAME-17 + OD-2. A guidance/surprise fact on a BARE name is a NAMING
    defect, so the CORRECTED key must not contain one."""
    bad = []
    for sid, fact in _du_facts():
        want = REQUIRED_SUFFIX.get(fact.get("fact_type"))
        if want is None:
            continue
        _base, got = split_terminal_suffix(_name(fact) or "")
        if got != want:
            bad.append((sid, _name(fact), fact.get("fact_type")))
    assert not bad, ("%d guidance/surprise gold rows carry no lawful terminal "
                     "suffix, e.g. %s" % (len(bad), bad[:3]))


def test_defect1_no_event_reuses_one_driver_name_across_fact_types():
    """exp5_scoring_spec_v3.md:87 - one name cannot be two types."""
    seen, clashes = {}, []
    for sid, f in _du_facts():
        name = _name(f)
        if name is None:
            continue
        prior = seen.get((sid, name))
        if prior is not None and prior != f.get("fact_type"):
            clashes.append((sid, name, prior, f.get("fact_type")))
        seen[(sid, name)] = f.get("fact_type")
    assert not clashes, ("%d events reuse one driver_name across fact types, "
                         "e.g. %s" % (len({c[0] for c in clashes}), clashes[:3]))


def _same_base_event(metric_name, guidance_name):
    """A lawful positive control: ONE event carrying a metric fact and a
    guidance fact about the SAME base, under the caller's names."""
    mq, gq = "m" * 60, "g" * 60
    facts = [_v2_fact(mq, fact_type="metric",
                      item=_v2_item(mq, driver_name=metric_name,
                                    fiscal_year=2050, fiscal_quarter=1,
                                    time_type="duration",
                                    level_low=_v2_slot(mq, value=5),
                                    level_high=_v2_slot(mq, value=5),
                                    level_shape_hint="point",
                                    level_unit="m_usd")),
             _v2_fact(gq, fact_type="guidance",
                      item=_v2_item(gq, driver_name=guidance_name,
                                    fiscal_year=2050, fiscal_quarter=2,
                                    time_type="duration",
                                    level_low=_v2_slot(gq, value=7),
                                    level_high=_v2_slot(gq, value=7),
                                    level_shape_hint="point",
                                    level_unit="m_usd"))]
    return {"E1": {"facts": facts, "abstentions": []}}


def test_defect1_control_lawful_suffixed_family_routes_and_bare_one_does_not():
    """The positive control and its mutation, through the UNCHANGED route."""
    lawful = _same_base_event("revenue", "revenue_guidance")
    routed = _route_for(lawful)
    assert routed["E1"]["result"]["status"] == "dry_run"
    assert len(routed["E1"]["result"]["items"]) == 2

    # THE MUTATION. One name with two fact_types no longer kills the event:
    # the spec rejects the NAME, so the route must still run and must ACCOUNT
    # the rejection rather than raise.
    bare = _same_base_event("revenue", "revenue")
    out = _route_for(bare)["E1"]
    assert out["result"]["status"] == "dry_run"
    assert out["rejected_conflicting_names"] == ["revenue"]
    assert out["rejected_fact_idxs"] == [0, 1]
    assert out["result"]["items"] == [], (
        "both facts bore the rejected name, so none may route")
    # and the lawful control above rejected nothing
    assert routed["E1"]["rejected_conflicting_names"] == []


# --------------------------------------- defect 2: the real source instant --
def test_defect2_a_frozen_source_instant_sidecar_exists_for_every_event():
    """ChannelContract fixes `event_time` as the SOURCE PUBLIC timestamp. The
    K-fields `date + T00:00:00` anchor is only the menu cutoff and must never
    become a route input."""
    import a7_source_meta as SM
    side = SM.load()
    gold, _sc = G.gold_by_event()
    missing = [sid for sid in sorted(gold) if sid not in side]
    assert not missing, "%d events have no frozen source instant" % len(missing)
    for sid, row in sorted(side.items()):
        assert row["event_time"] and len(row["event_time"]) > 10, (
            "%s carries no full source instant: %r" % (sid, row["event_time"]))
        assert row["event_time"][:10] == row["event_date"], (
            "%s: frozen instant %s does not fall on the frozen event date %s"
            % (sid, row["event_time"], row["event_date"]))


def test_defect2_the_route_event_carries_the_frozen_instant_not_midnight():
    """Control plus mutation: the route input must equal the frozen instant,
    and a synthesized midnight must be refused."""
    import a7_source_meta as SM
    side = SM.load()
    sid = sorted(side)[0]
    event = SM.route_event(sid)
    assert event["event_time"] == side[sid]["event_time"]
    # A real source MAY publish at midnight, so nothing here forbids a clock
    # value. The rule is exact equality with this source's own frozen instant:
    # substitute a different, perfectly valid instant and it must be refused.
    other = sorted({r["event_time"] for r in side.values()}
                   - {side[sid]["event_time"]})[0]
    with pytest.raises(ValueError, match="frozen public instant"):
        SM.route_event(sid, instant=other)


# ------------------------------------------- defect 3: O-5 name meaning -----
def test_defect3_the_versioned_scorer_grades_name_meaning_and_retires_wrong_name():
    """exp5_scoring_spec_v3.md:97-108 - `wrong_name` is not a locked bar and
    name-meaning is an adjudicated field."""
    from scorers import score_exp5 as S2
    assert "driver_name_meaning" in S2.MEANING_FIELDS
    where = S2.field_accounting()
    assert where["driver_name"] == "grader_owned", (
        "driver_name is still measured as an exact code field: %r"
        % where["driver_name"])
    import inspect
    assert "wrong_name" not in inspect.signature(
        S2.passes_official_bars).parameters, (
        "the retired exact-string wrong_name counter is still a bar")
    # the counter must be gone from EVERY hard gate, not only from the bars:
    # `definite_fail` and `_leg` read it too, which is how a wrapper that only
    # renamed the reported key still produced a false definite failure.
    import io as _io
    body = _io.open(S2.__file__, encoding="utf-8").read()
    for owner in ("definite_fail = ", "def _leg("):
        chunk = body.split(owner, 1)[1][:600]
        assert "wrong_name" not in chunk, (
            "%s still gates on the retired exact-string counter" % owner)


def test_defect3_control_lawful_synonym_passes_and_wrong_meaning_fails_safety():
    """Control plus mutation, both through the versioned scorer."""
    # the versioned scorer IS the one copied scorer of this tree; there is no
    # second scorer and no wrapper.
    from scorers import score_exp5 as S2
    from test_harness_guards import _gold_fact
    q = "s" * 60
    gold = {"E1": [_gold_fact(q, fact_type="metric",
                              item=_v2_item(q, driver_name="revenue",
                                            fiscal_year=2050,
                                            fiscal_quarter=1,
                                            time_type="duration",
                                            level_low=_v2_slot(q, value=5),
                                            level_high=_v2_slot(q, value=5),
                                            level_shape_hint="point",
                                            level_unit="m_usd"))]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_v2_item(
        q, driver_name="total_revenue", fiscal_year=2050, fiscal_quarter=1,
        time_type="duration", level_low=_v2_slot(q, value=5),
        level_high=_v2_slot(q, value=5), level_shape_hint="point",
        level_unit="m_usd"))], "abstentions": []}}
    meta = {"E1": {"event_date": "2026-04-23T16:00:00-04:00", "fye_month": 12}}
    route = _route_for(arm)
    assert [r["decision"] for r in route["E1"]["result"]["items"]] == ["written"]
    # A lawful synonym is exactly what the deterministic matcher CANNOT link,
    # so the real pipeline links it in G1 and grades its meaning in G2. Without
    # that ruling the pair never becomes a matched pair and no verdict is read
    # at all - which is how the first run of this mutation passed vacuously.
    g1_link = {("E1", 0): 0}
    true_all = {("E1", 0): {k: True for k in S2.MEANING_FIELDS}}
    ok = S2.score_arm(gold, arm, meta, true_all, g1_link, route=route,
                      extras_verdicts={})
    assert ok["matched"] == 1, "the control never produced a matched pair"
    assert ok["confirmed_wrong_accepted"] == 0, (
        "a lawful synonym with a TRUE name-meaning verdict tripped safety")
    assert ok["name_spelling_differences"] == 1, (
        "the exact spelling difference must still be REPORTED as a diagnostic")

    wrong = {("E1", 0): dict(true_all[("E1", 0)], driver_name_meaning=False)}
    bad = S2.score_arm(gold, arm, meta, wrong, g1_link, route=route,
                       extras_verdicts={})
    assert bad["confirmed_wrong_accepted"] >= 1, (
        "a FALSE name-meaning verdict on a route-written fact did not reach "
        "the confirmed-wrong-accepted safety failure")


def test_defect3_an_incomplete_run_is_never_failed_by_spelling_alone():
    """The false-fail the wrapper hid: `definite_fail` gated on the retired
    exact-string counter INSIDE the scorer, so an incomplete run with a lawful
    synonym and a still-pending verdict was reported as a definite failure."""
    from scorers import score_exp5 as S
    from test_harness_guards import _gold_fact
    q = "p" * 60
    gold = {"E1": [_gold_fact(q, fact_type="metric", item=_v2_item(
        q, driver_name="revenue", fiscal_year=2050, fiscal_quarter=1,
        time_type="duration", level_low=_v2_slot(q, value=5),
        level_high=_v2_slot(q, value=5), level_shape_hint="point",
        level_unit="m_usd"))]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_v2_item(
        q, driver_name="total_revenue", fiscal_year=2050, fiscal_quarter=1,
        time_type="duration", level_low=_v2_slot(q, value=5),
        level_high=_v2_slot(q, value=5), level_shape_hint="point",
        level_unit="m_usd"))], "abstentions": []}}
    meta = {"E1": {"event_date": "2026-04-23T16:00:00-04:00", "fye_month": 12}}
    # the pair is linked by G1 but its meaning verdict has NOT arrived yet
    res = S.score_arm(gold, arm, meta, None, {("E1", 0): 0},
                      route=_route_for(arm), extras_verdicts={})
    assert res["name_spelling_differences"] == 1
    assert res["verdicts_missing"] == 1
    assert res["PASS"] is not False, (
        "a pending verdict plus a spelling difference was reported as a "
        "definite failure: %r" % res["PASS"])


def test_defect3_structural_name_check_is_retained_for_lawful_and_malformed():
    """`valid_driver_name` stays the CODE check; only correctness moved."""
    assert valid_driver_name("revenue_guidance")
    assert not valid_driver_name("Revenue Guidance")
    assert not valid_driver_name("")


def test_defect3_the_route_refuses_a_malformed_name_and_accepts_a_lawful_one():
    """The STRUCTURAL check stays with code, proven where production enforces
    it: the public write-disabled route, not a unit call on the predicate."""
    q = "n" * 60
    def arm(name):
        return {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_v2_item(
            q, driver_name=name, fiscal_year=2050, fiscal_quarter=1,
            time_type="duration", level_low=_v2_slot(q, value=5),
            level_high=_v2_slot(q, value=5), level_shape_hint="point",
            level_unit="m_usd"))], "abstentions": []}}
    lawful = _route_for(arm("revenue"))
    assert [r["decision"] for r in lawful["E1"]["result"]["items"]] == ["written"]
    assert valid_driver_name("revenue")

    # the route does not RAISE on a malformed name; it refuses it as a typed
    # public outcome, which is the stronger guarantee: the row is reported
    # with the identity-law code and is never written.
    for malformed in ("Revenue Guidance", "revenue guidance", "REVENUE"):
        assert not valid_driver_name(malformed)
        rows = _route_for(arm(malformed))["E1"]["result"]["items"]
        assert [r["decision"] for r in rows] == ["parked"], malformed
        assert rows[0]["codes"] == ["ID_LAW"], (malformed, rows[0]["codes"])


def test_field_ownership_is_exactly_once_and_a_double_count_is_detectable():
    """The MUTATION for exactly-once field ownership.

    Asserting `driver_name` is grader-owned proves where it lives; it does not
    prove the accounting would NOTICE it living in two places. Putting it back
    into the pooled set must make the code-field pool grow by exactly one, so
    the two homes are provably distinct populations.
    """
    from scorers import score_exp5 as S
    where = S.field_accounting()
    assert where["driver_name"] == "grader_owned"
    assert "driver_name" not in S.CODE_FIELDS
    assert "driver_name_meaning" in S.MEANING_FIELDS

    grader_owned = set(S.GRADER_OWNED)
    assert not (grader_owned & set(S.CODE_FIELDS)), (
        "a field is both grader-owned and pooled: %s"
        % sorted(grader_owned & set(S.CODE_FIELDS)))

    # the mutation: hand the derivation a GRADER_OWNED set without the name
    import driver.core.prepared_fact_v2 as V2
    mutated = tuple(f for f in S.GRADER_OWNED if f != "driver_name")
    excluded = (set(mutated) | set(V2.NUMERIC_SLOTS)
                | set(S.SPECIALIZED_COLLECTIONS) | {"quote"})
    pooled_again = [f for f in V2.ITEM_FIELDS if f not in excluded]
    assert len(pooled_again) == len(S.CODE_FIELDS) + 1
    assert "driver_name" in pooled_again


# ---------------------------------- the OD-1 response door (SEQ 1456 item 2) --
_OD1_QUOTE = "our international sales, in constant currency, were slightly below our expectations"
_OD1_GOOD = '{"verdict": "YES", "evidence_phrase": "in constant currency"}'


def _od1(text, quote=_OD1_QUOTE):
    A = _historical_od1()
    return A.read_reply(text, quote)


def _historical_od1():
    """Read the retired probe only as pinned historical test evidence."""
    import importlib.util
    path = "/tmp/a7_historical_harness/a7_od1_admission.py"
    assert hashlib.sha256(open(path, "rb").read()).hexdigest() == (
        "b647d66424d4e062a526e0e4a989721b02c09a487d7eb1a0f9f263d67df80811")
    spec = importlib.util.spec_from_file_location("historical_od1_test", path)
    module = importlib.util.module_from_spec(spec)
    saved = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved  # the retired module must not change active imports
    return module


def test_od1_door_accepts_plain_and_fenced_identically():
    plain, p1 = _od1(_OD1_GOOD)
    fenced, p2 = _od1("```json\n" + _OD1_GOOD + "\n```")
    assert not p1 and not p2, (p1, p2)
    assert plain == fenced


def test_od1_door_refuses_every_malformed_envelope():
    bad = {
        "surrounding text": "Here is my answer:\n" + _OD1_GOOD,
        "trailing text": _OD1_GOOD + "\nHope that helps.",
        "a second block": "```json\n" + _OD1_GOOD + "\n```\n```json\n"
                          + _OD1_GOOD + "\n```",
        "an unclosed fence": "```json\n" + _OD1_GOOD,
        "duplicate keys": '{"verdict": "YES", "verdict": "NO", '
                          '"evidence_phrase": "in constant currency"}',
        "an extra field": '{"verdict": "YES", "evidence_phrase": '
                          '"in constant currency", "why": "because"}',
        "a missing field": '{"verdict": "YES"}',
        "an unlawful verdict": '{"verdict": "MAYBE", "evidence_phrase": '
                               '"in constant currency"}',
    }
    for label, text in bad.items():
        answer, problems = _od1(text)
        assert answer is None and problems, "accepted %s: %r" % (label, text)


def test_od1_door_refuses_an_evidence_phrase_that_is_not_in_the_quote():
    """A made-up phrase is the one failure a JSON check cannot catch."""
    made_up = '{"verdict": "YES", "evidence_phrase": "revenue grew strongly"}'
    answer, problems = _od1(made_up)
    assert answer is None
    assert any("substring" in p for p in problems), problems
    ok, none = _od1('{"verdict": "YES", "evidence_phrase": "%s"}' % _OD1_QUOTE)
    assert not none and ok["verdict"] == "YES"


def test_od1_prompt_serves_only_the_four_permitted_fields():
    """The LEAK control. No identity and no answer field may reach the model."""
    A = _historical_od1()
    candidate = {"candidate_id": "OD1-000", "proposed_name": "sales_surprise",
                 "quote": _OD1_QUOTE, "source_id": "SID-X", "gold_idx": 2,
                 "fact_sha256": "0" * 64}
    built = A.candidates([candidate])[0]
    rendered = A.prompt_for(built)
    for leaked in ("SID-X", "gold_idx", "fact_sha256", "0" * 64,
                   "du_worthy", "driver_state", "slice_parts",
                   "measurement_raw_spans", "polarity_proof", "fact_type"):
        assert leaked not in rendered, "the prompt leaks %r" % leaked
    assert sorted(A.served(built)) == sorted(A.SERVED_FIELDS)
    assert rendered.startswith(A.RULES[:60])           # rules first
    assert rendered.rstrip().endswith("}")             # the one item last


# ------------------------------- the generic applier (SEQ 1456 item 3) -------
def test_the_applier_owns_no_driver_name_and_no_name_branch():
    """The anti-sample-shape control: the applier's own source must contain no
    driver name from the corpus it corrects."""
    import a7_key_correction as K
    body = io.open(K.__file__, encoding="utf-8").read()
    ledger = K.load()
    corpus = {r["old_driver_name"] for r in ledger["rows"]}
    corpus |= {r["patch"]["driver_name"] for r in ledger["rows"]
               if r["action"] == K.SET_NAME}
    leaked = sorted(n for n in corpus if n and n in body)
    assert not leaked, "the applier names %s" % leaked


def test_the_applier_refuses_a_row_whose_bytes_moved():
    """MUTATION: the recorded old identity is the permission to act."""
    import a7_key_correction as K
    # The old correction ledger is not applied to today's newly signed key.
    # Exercise the unchanged generic historical applier on explicit TEST data.
    fact = _v2_fact("test guidance " * 5, fact_type="guidance",
                    item=_v2_item("test guidance " * 5, driver_name="test_metric"))
    fact["du_worthy"] = True
    gold = {"TEST": [fact]}
    ledger = {"rows": [{"source_id": "TEST", "gold_idx": 0,
                        "action": K.APPEND_SUFFIX,
                        "old_driver_name": "test_metric", "old_fact_type": "guidance",
                        "old_fact_sha256": K.fact_sha256(fact)}]}
    corrected, problems = K.apply(gold, ledger)
    assert problems == []
    assert corrected["TEST"][0]["item"]["driver_name"] == "test_metric" + GUIDANCE_SUFFIX
    tampered = dict(ledger, rows=[dict(r) for r in ledger["rows"]])
    tampered["rows"][0]["old_fact_sha256"] = "0" * 64
    _corrected, problems = K.apply(gold, tampered)
    assert any("recorded bytes" in p for p in problems), problems


def test_the_ledger_covers_the_acted_population_exactly_once():
    """The CURRENT ledger names every row it acts on exactly once, and its
    published counts are the ones SEQ 1458 item 1 required: the actionable
    naming population, the wider family audit it was derived from, and the
    controls that are checked unchanged rather than acted on."""
    import a7_key_correction as K
    ledger = K.load()
    keys = [(r["source_id"], r["gold_idx"]) for r in ledger["rows"]]
    assert len(keys) == len(set(keys)) == ledger["acted_rows"]
    assert ledger["actionable_population"] == 52
    assert ledger["family_audit_population"] == 68
    assert ledger["unchanged_controls"] == 16
    assert (ledger["actionable_population"] + ledger["unchanged_controls"]
            == ledger["family_audit_population"])
    # This is historical ledger accounting, not permission to replay its
    # corrections against the new signed key.
    current, identity = K.current_key()
    assert identity["acted_rows"] == 0
    assert identity["accepted_rows"] == sum(f.get("du_worthy") is True
                                           for facts in current.values() for f in facts)
    # the acted rows go beyond the naming population, because the period and
    # unit corrections act on ordinary rows the naming audit never reached
    assert ledger["acted_rows"] >= ledger["actionable_population"]


# ------------------------------- the G2 meaning door (SEQ 1456 item 8) -------
def _real_rows(n=1):
    """REAL inventory-bound rows: a synthetic fact has no bound identity, and
    the card is looked up by identity on purpose."""
    import a7_key_correction as K
    key, _identity = K.current_key()
    for sid in sorted(key):
        idxs = [i for i, f in enumerate(key[sid])
                if f.get("du_worthy") is True]
        if len(idxs) >= n:
            return sid, key[sid], idxs[:n]
    raise AssertionError("no event with %d accepted rows" % n)


def _g2_packet():
    import a7_g23_build as B
    sid, facts, idxs = _real_rows(1)
    prod = [_v2_fact("g" * 60, fact_type="metric", item=_v2_item(
        "g" * 60, driver_name="total_revenue", fiscal_year=2050))]
    packet = B.meaning_packet(sid, sid, [(0, 0)], facts, prod,
                              _RUN, inputs=_INPUTS)
    return B, packet


def test_g2_prompt_carries_the_live_rule_and_every_meaning_field():
    B, packet = _g2_packet()
    text = packet["prompt"]
    for field in B.meaning_fields():
        assert field in text, "the G2 prompt omits %s" % field
    assert "driver_name_meaning" in text
    # O-5's live rule must be stated, not implied. Assert the SUBSTANCE: the
    # earlier version pinned one capitalisation and broke when the definition
    # was rewritten, which tested the wording rather than the rule.
    assert "lawful alternative name is correct" in text
    assert "identical spelling is not the test" in text
    # a reviewer conclusion must never reach the grader
    import kf_lint
    for gold_only in kf_lint.GOLD_ONLY:
        assert gold_only not in text, "the G2 prompt leaks %s" % gold_only


def test_g2_door_requires_exactly_the_complete_field_set():
    B, packet = _g2_packet()
    qid = packet["question_ids"][0]
    full = {f: True for f in B.meaning_fields()}

    ok, problems = B.read_meaning_reply(
        json.dumps([{"question_id": qid, "verdicts": full}]), packet)
    assert not problems and ok[qid] == full

    short = {f: True for f in B.meaning_fields() if f != "driver_name_meaning"}
    _none, problems = B.read_meaning_reply(
        json.dumps([{"question_id": qid, "verdicts": short}]), packet)
    assert any("aspects" in p for p in problems), problems

    extra = dict(full, invented=True)
    _none, problems = B.read_meaning_reply(
        json.dumps([{"question_id": qid, "verdicts": extra}]), packet)
    assert any("aspects" in p for p in problems), problems

    _none, problems = B.read_meaning_reply(json.dumps([]), packet)
    assert any("not answered" in p for p in problems), problems


def test_g2_door_accepts_the_four_lawful_answer_shapes():
    """correct name, lawful alternative, wrong name, and uncertain."""
    B, packet = _g2_packet()
    qid = packet["question_ids"][0]
    for label, name_verdict in (("correct name", True),
                                ("lawful alternative name", True),
                                ("wrong name", False),
                                ("uncertain", None)):
        verdicts = {f: True for f in B.meaning_fields()}
        verdicts["driver_name_meaning"] = name_verdict
        ok, problems = B.read_meaning_reply(
            json.dumps([{"question_id": qid, "verdicts": verdicts}]), packet)
        assert not problems, (label, problems)
        assert ok[qid]["driver_name_meaning"] is name_verdict, label


def test_g2_question_ids_bind_all_four_identity_parts():
    import a7_g23_build as B
    base = B.meaning_question_id("P1", "E1", 0, 0)
    assert base != B.meaning_question_id("P2", "E1", 0, 0)
    assert base != B.meaning_question_id("P1", "E2", 0, 0)
    assert base != B.meaning_question_id("P1", "E1", 1, 0)
    assert base != B.meaning_question_id("P1", "E1", 0, 1)


def test_g2_prompt_defines_every_aspect_in_plain_words():
    """SEQ 1457 item 8: six opaque labels cannot be answered."""
    import a7_g23_build as B
    text = B.meaning_rules()
    for field in B.meaning_fields():
        definition = B.ASPECT_DEFINITIONS[field]
        assert len(definition) > 40, field
        assert definition in text, "the rendered prompt omits %s's meaning" % field
    # the true/false/null contract must be stated, not implied
    plain = " ".join(text.split())
    assert "null means this event's evidence does not settle it" in plain
    assert "never guess" in plain


def test_g2_output_example_is_valid_json():
    import a7_g23_build as B
    import re
    text = B.meaning_rules()
    block = text[text.index("[OUTPUT]"):text.index("No prose")]
    found = re.search(r"\[\s*\{.*?\}\s*\]", block, re.S)
    assert found, "no output example found"
    parsed = json.loads(found.group(0))          # must be REAL JSON
    assert isinstance(parsed, list) and len(parsed) == 1
    assert sorted(parsed[0]["verdicts"]) == sorted(B.meaning_fields())
    assert set(parsed[0]["verdicts"].values()) == {"<true | false | null>"}


def test_g2_two_graders_must_agree_per_aspect():
    import a7_g23_build as B
    full = {f: True for f in B.meaning_fields()}
    agreed, unresolved = B.reconcile_meaning({"M1": dict(full)},
                                             {"M1": dict(full)})
    assert agreed == {"M1": full} and not unresolved

    # one aspect disagrees -> the WHOLE pair is unresolved, never half-selected
    other = dict(full, growth_basis=False)
    agreed, unresolved = B.reconcile_meaning({"M1": dict(full)}, {"M1": other})
    assert agreed == {} and any(u.get("aspect") == "growth_basis"
                                for u in unresolved)

    # a null from either reading is unresolved, not a false
    nulled = dict(full, slice_vs_menu=None)
    agreed, unresolved = B.reconcile_meaning({"M1": dict(full)}, {"M1": nulled})
    assert agreed == {} and any(u.get("aspect") == "slice_vs_menu"
                                for u in unresolved)

    # answered by only one reading
    agreed, unresolved = B.reconcile_meaning({"M1": dict(full)}, {})
    assert agreed == {} and unresolved[0]["reason"] == "answered by only one reading"

    # a missing reading altogether
    agreed, unresolved = B.reconcile_meaning({"M1": dict(full)}, None)
    assert agreed is None and unresolved


# ------------------- the two served clarifications (SEQ 1458 item 3) ---------
def _period_arm(**item_over):
    q = "d" * 60
    base = dict(fiscal_year=2050, fiscal_quarter=1, time_type="duration",
                level_low=_v2_slot(q, value=5), level_high=_v2_slot(q, value=5),
                level_shape_hint="point", level_unit="m_usd",
                driver_name="revenue")
    base.update(item_over)
    return {"E1": {"facts": [_v2_fact(q, fact_type="metric",
                                      item=_v2_item(q, **base))],
                   "abstentions": []}}


def _decisions(arm):
    return [(r["decision"], tuple(r["codes"]))
            for r in _route_for(arm)["E1"]["result"]["items"]]


def test_rule6_an_exact_duration_window_is_all_or_nothing():
    """Control, control, mutation — all through the public route."""
    # complete fiscal framing, no exact dates: lawful
    assert _decisions(_period_arm())[0][0] == "written"
    # BOTH exact endpoints: lawful
    both = _period_arm(period_start_date="2050-01-01",
                       period_end_date="2050-03-31")
    assert _decisions(both)[0][0] == "written"
    # ONE lone endpoint: the mutation the clarification exists to stop
    lone = _period_arm(period_end_date="2050-03-31")
    decision, codes = _decisions(lone)[0]
    assert decision == "parked" and "PERIOD_UNRESOLVED" in codes, (decision, codes)


def test_rule5a_a_numberless_growth_basis_uses_level_unit():
    """Control and mutation for the unit clarification."""
    q = "u" * 60
    def arm(level_unit, change_unit):
        # genuinely NUMBERLESS: every value slot and shape hint null, which is
        # the shape the corrected key rows actually carry. A fixture with a
        # level value is rejected on SHAPE and proves nothing about units.
        return {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_v2_item(
            q, driver_name="revenue", fiscal_year=2050, fiscal_quarter=1,
            time_type="duration", driver_state="increased",
            level_low=None, level_high=None, change_value=None,
            comparison_low=None, comparison_high=None,
            level_shape_hint=None, comparison_shape_hint=None,
            level_unit=level_unit, change_unit=change_unit))],
            "abstentions": []}}
    # lawful: the numberless growth basis rides in level_unit
    assert _decisions(arm("percent_yoy", None))[0][0] == "written"
    # mutation: change_unit with no change_value
    decision, codes = _decisions(arm(None, "percent_yoy"))[0]
    assert decision == "rejected" and "UNIT" in codes, (decision, codes)


def test_the_corrected_prompt_version_is_frozen_beside_its_predecessors():
    """Version 3 carries both clarifications and is FROZEN. It is not yet the
    served contract: the committed plan, its pins, the launchers and every A1
    proof belong to version 1, and switching the served version without
    re-planning the launch broke 103 tests in that chain. Serving it is a
    re-plan, and that decision is not this test's to make.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    def read(name):
        return io.open(os.path.join(here, name), encoding="utf-8").read()
    v3 = read("exp5_prompt_producer.v3.md")
    assert "exact duration window is all-or-nothing" in v3
    assert "numberless growth fact states its basis in `level_unit`" in v3
    assert "MUST end in `_guidance`" in v3
    # every earlier version stays exactly as it was
    v1 = read("exp5_prompt_producer.md")
    assert "may end a name" in v1 and "all-or-nothing" not in v1
    v2 = read("exp5_prompt_producer.v2.md")
    assert "MUST end in `_guidance`" in v2 and "all-or-nothing" not in v2
    # the two carriers of version 3 share the same corrected rules
    assert "exact duration window is all-or-nothing" in read(
        "exp5_prompt_drafter.v3.md")


# --------------------- the two plan eras, separately (SEQ 1458 item 6) -------
def test_the_historical_plan_and_the_rebuilt_one_are_distinguishable():
    """The version-1 plan stays immutable evidence; THE current plan is the A5
    kit's, and it pins different contract bytes. Neither is checked against the
    other's era.

    This used to read `launch_kfields_drafts.manifest.v3.json` - an A1-SHAPED
    artifact rebuilt for the v3 era, which made it look as though two current
    launches existed. There is one current plan and it is the A5 kit's
    (Codex SEQ 1469 item 2).
    """
    import build_a5_exp5_kit as A5
    here = os.path.dirname(os.path.abspath(__file__))
    def plan(name):
        return json.load(io.open(os.path.join(here, name), encoding="utf-8"))
    v1 = plan("launch_kfields_drafts.manifest.json")
    v3 = A5.plan()
    assert v1["plan_version"] == "a1-one-item-v1"
    assert v3["contract_suffix"] == ".v3", v3.get("contract_suffix")
    assert v1["pins"]["contract"] != v3["pins"]["contract"]
    pinned_v1 = hashlib.sha256(io.open(
        os.path.join(here, "exp5_prompt_drafter.md"), "rb").read()).hexdigest()
    assert v1["pins"]["contract"] == pinned_v1, (
        "the historical plan must still pin its own era's contract")
    pinned_v3 = hashlib.sha256(io.open(
        os.path.join(here, "exp5_prompt_drafter.v3.md"), "rb").read()).hexdigest()
    assert v3["pins"]["contract"] == pinned_v3, (
        "the rebuilt plan must pin the corrected contract")


# --------------------- raw evidence only, all graders (SEQ 1459 item 3) ------
def test_the_reference_card_is_a_structural_whitelist():
    """SEQ 1460 item 4: a string scan cannot prove zero hidden answers - it
    ignores numbers, booleans, short strings, lists and dicts. The card is an
    exact key whitelist and the proof is structural."""
    import a7_g23_build as B
    import a7_key_correction as K
    key, _identity = K.current_key()
    checked = 0
    for sid in sorted(key):
        for idx, fact in enumerate(key[sid]):
            if fact.get("du_worthy") is not True:
                continue
            card = B.reference_card(fact, sid, idx, _RUN)
            assert sorted(card) == sorted(B.CARD_KEYS)
            assert not B.card_problems(card)
            checked += 1
    assert checked == sum(f.get("du_worthy") is True
                          for facts in key.values() for f in facts) > 0


def test_a_card_carrying_a_forbidden_key_class_is_refused():
    """Mutate every forbidden class, not only one example."""
    import a7_g23_build as B
    # the reference name is the SOURCE'S OWN span, so a lawful control must
    # actually appear in its quote. The old control did not, and only passed
    # because the door had not yet checked it.
    lawful = collections.OrderedDict([
        ("quote", "revenue " + "x" * 40), ("reference_name", "revenue"),
        ("values", [5])])
    assert not B.card_problems(lawful), B.card_problems(lawful)
    for label, bad in (
            ("an interpreted conclusion",
             dict(lawful, fact_type="metric")),
            ("a state", dict(lawful, driver_state="increased")),
            ("a period", dict(lawful, period_end_date="2026-01-01")),
            ("a slice", dict(lawful, slice_parts=["geography:nonus"])),
            ("a measurement", dict(lawful, measurement_raw_spans=["adjusted"])),
            ("a missing key", {"quote": lawful["quote"], "values": {}}),
            ("a name that is not a span of its quote",
             dict(lawful, reference_name="not in the quote at all")),
            ("a reordered card", collections.OrderedDict(
                reversed(list(lawful.items())))),
            ("a slot-named mapping",
             dict(lawful, values={"level_low": 5})),
            ("a boolean verdict", dict(lawful, values=[True])),
            ("an inexact float", dict(lawful, values=[5.0])),
            ("a nested container", dict(lawful, values=[[5]]))):
        assert B.card_problems(bad), "accepted %s" % label


def test_quote_only_could_not_identify_a_claim_but_the_card_can():
    """The defect the earlier quote-only rule froze, measured on the live key."""
    import a7_g23_build as B
    import a7_key_correction as K
    key, _identity = K.current_key()
    by_quote = collections.defaultdict(list)
    for sid in sorted(key):
        for idx, fact in enumerate(key[sid]):
            if fact.get("du_worthy") is not True:
                continue
            by_quote[(sid, (fact.get("item") or {}).get("quote"))].append(idx)
    repeated = {k: v for k, v in by_quote.items() if len(v) > 1}
    assert repeated, "the control must contain more than one claim in one quote"
    assert max(len(v) for v in by_quote.values()) >= 2

    clashes = B.non_unique_cards(key, _RUN)
    assert len(clashes) < len(repeated), (
        "the reference card did not reduce the ambiguity")
    # whatever remains is PRE-CALL UNRESOLVED and must be reported, not guessed
    for clash in clashes:
        assert len(clash["gold_idxs"]) > 1 and clash["source_id"]


# ------------------------------------ the G3 door (SEQ 1459 item 4) ----------
def _g3():
    import a7_g23_build as B
    sid, facts, idxs = _real_rows(1)
    prod = [_v2_fact("x" * 60, fact_type="metric",
                     item=_v2_item("x" * 60, driver_name="total_revenue"))]
    packet = B.extras_packet(sid, sid, [0], prod,
                             [(idxs[0], facts[idxs[0]])], _RUN)
    return B, packet


def test_g3_prompt_defines_every_bucket_and_shows_valid_json():
    import re
    B, packet = _g3()
    for bucket in B.extras_buckets():
        assert bucket in packet["prompt"]
        assert B.BUCKET_DEFINITIONS[bucket] in packet["prompt"]
    block = packet["prompt"]
    found = re.search(r"\[\s*\{.*?\}\s*\]", block, re.S)
    assert found and isinstance(json.loads(found.group(0)), list)


def test_g3_door_is_strict_and_never_crashes():
    B, packet = _g3()
    qid = packet["question_ids"][0]
    ok, problems = B.read_extras_reply(
        json.dumps([{"question_id": qid, "bucket": B.extras_buckets()[0]}]),
        packet)
    assert not problems and ok[qid] == B.extras_buckets()[0]
    ok, problems = B.read_extras_reply(
        json.dumps([{"question_id": qid, "bucket": None}]), packet)
    assert not problems and ok[qid] is None
    for bad in ({"question_id": qid, "bucket": "invented"},
                {"question_id": qid, "bucket": 1},
                {"question_id": [1], "bucket": "duplicate"},
                {"question_id": "", "bucket": "duplicate"},
                {"question_id": qid}):
        answer, problems = B.read_extras_reply(json.dumps([bad]), packet)
        assert answer is None and problems, bad


def test_g3_two_answers_must_agree_on_a_named_bucket():
    B, _packet = _g3()
    first = B.extras_buckets()[0]
    agreed, unresolved = B.reconcile_extras({"X1": first}, {"X1": first})
    assert agreed == {"X1": first} and not unresolved
    for a, b in (({"X1": first}, {"X1": B.extras_buckets()[1]}),
                 ({"X1": first}, {"X1": None}),
                 ({"X1": first}, {})):
        agreed, unresolved = B.reconcile_extras(a, b)
        assert agreed == {} and unresolved


# --------------------------- deterministic batching (SEQ 1459 item 7) --------
def test_batches_hold_at_most_ten_items_from_distinct_source_events():
    import a7_g23_build as B
    by = {}
    for leg in ("P1", "P2", "UNION"):
        for n in range(36):
            by["%s|E%02d" % (leg, n)] = [1] * 4
    batches = B.pack_batches(by)
    assert not B.batch_problems(batches)
    assert max(len(b) for b in batches) <= B.MAX_ITEMS_PER_CALL
    for batch in batches:
        events = [B.source_event(k) for k, _i in batch]
        assert len(set(events)) == len(events), "two legs of one event batched"
    assert sum(len(b) for b in batches) == sum(len(v) for v in by.values())
    assert B.pack_batches(by) == batches, "packing must be deterministic"


# ------------- the version reaches the SERVED packet bytes (SEQ 1459 item 1) --
#: THE EXTERNALLY REVIEWED v3 BYTES. Codex reproduced these independently from
#: the transcript; they are the only thing a packet test may compare against.
REVIEWED_V3 = {
    "drafter": "421613e2998cb29b4482507b2713bbf225dcd71bdbf61f7cf613871a4e25030c",
    "producer": "b8bcbf0f4712218db1578cefbc3508e762b0db938c9fbf44996a98bc6e5f3f57",
}



def test_the_contract_version_reaches_every_assembled_packet():
    """EXACT BYTES, not meaning fragments.

    The previous version compared diff lines against a list of approved English
    phrases. A phrase list can accept unrelated text that happens to contain
    one of them, and it is exactly the semantic hardcoding the rules forbid.
    Every assembled packet must instead BE the externally reviewed contract
    with only its own event substituted.
    """
    import build_exp5_contract as bec
    import build_launch_manifest as blm

    # the externally reviewed bytes, by hash
    for role, want in (("drafter", REVIEWED_V3["drafter"]),
                       ("producer", REVIEWED_V3["producer"])):
        text = bec.build_prompt(role, contract_suffix=".v3")
        assert hashlib.sha256(text.encode()).hexdigest() == want, role
        on_disk = io.open(bec.prompt_path(role, ".v3"), encoding="utf-8").read()
        assert text == on_disk, role

    events = blm._events()
    _pk, served = blm._one_item_packets([dict(e) for e in events],
                                        contract_suffix=".v3")
    assert len(served) == len(_pk) > 0
    fixed = bec.build_prompt("drafter", contract_suffix=".v3")
    head, sep, tail = fixed.partition(bec.EVENT_PLACEHOLDER)
    assert sep, "the contract has no event placeholder to substitute"
    # the placeholder sits last, so `head` IS the entire contract text: every
    # rule, every clarification, every byte before the event.
    assert tail.strip() == "", repr(tail[:40])
    head_sha = hashlib.sha256(head.encode()).hexdigest()
    for key, text in served.items():
        # BYTE EQUALITY of the whole contract portion, then the remainder must
        # be this packet's own event and nothing else.
        assert text.startswith(head), key
        assert hashlib.sha256(text[:len(head)].encode()).hexdigest() == \
            head_sha, key
        rest = text[len(head):].strip()
        assert rest.startswith("{") and rest.endswith("}"), key
        json.loads(rest)                      # a real event, not stray prose


def test_version_one_packets_are_reproducible_without_touching_its_tree():
    """Version 1 must still assemble exactly as it always did."""
    import build_launch_manifest as blm
    import hashlib as _h
    events = blm._events()
    _a, first = blm._one_item_packets([dict(e) for e in events],
                                      contract_suffix="")
    _b, again = blm._one_item_packets([dict(e) for e in events],
                                      contract_suffix="")
    assert first == again, "version 1 no longer assembles deterministically"
    here = os.path.dirname(os.path.abspath(__file__))
    pkg = io.open(os.path.join(here, "exp5_rev4_package.md"),
                  encoding="utf-8").read()
    assert "may end a name" in pkg, "the version-1 package was mutated"


def test_an_unresolved_reference_stops_the_launch_before_any_call():
    """SEQ 1461 item 3. Two reviewed claims whose PERMITTED card is identical
    cannot be asked about lawfully, so the candidate must refuse to launch
    rather than spend calls it can never resolve."""
    import a7_g23_build as B
    import a7_key_correction as K
    key, _identity = K.current_key()
    # the reference inventory resolved every collision, so the LAWFUL state is
    # now zero unresolved and a clean gate
    assert B.precall_unresolved(key, _RUN) == []
    assert B.preflight_problems(key, _RUN) == []

    # the MUTATION: a key whose two rows share a bound card must still stop.
    # Duplicating a row reproduces exactly that, without touching the key.
    import copy
    sid = sorted(key)[0]
    idx = next(i for i, f in enumerate(key[sid]) if f.get("du_worthy") is True)
    clashing = {s: list(v) for s, v in key.items()}
    clashing[sid] = list(clashing[sid]) + [copy.deepcopy(key[sid][idx])]
    try:
        stopped = bool(B.preflight_problems(clashing, _RUN))
    except ValueError:
        stopped = True          # an unbound duplicate is refused even earlier
    assert stopped, "a duplicated bound card did not stop the gate"


# ------------- Codex 1465.2: a rejected fact must earn NO credit anywhere --
def _conflicted_arm():
    """One event where a conflicting name is ALSO an exact gold match.

    Two facts share `revenue` with different fact_types, so the law rejects
    that name. A third, unrelated fact is lawful and must keep its credit.
    """
    mq, gq, oq = "m" * 60, "g" * 60, "o" * 60
    def metric(q, name, value):
        return _v2_fact(q, fact_type="metric",
                        item=_v2_item(q, driver_name=name, fiscal_year=2050,
                                      fiscal_quarter=1, time_type="duration",
                                      level_low=_v2_slot(q, value=value),
                                      level_high=_v2_slot(q, value=value),
                                      level_shape_hint="point",
                                      level_unit="m_usd"))
    rejected = metric(mq, "revenue", 5)
    conflict = _v2_fact(gq, fact_type="guidance",
                        item=_v2_item(gq, driver_name="revenue",
                                      fiscal_year=2050, fiscal_quarter=2,
                                      time_type="duration",
                                      level_low=_v2_slot(gq, value=7),
                                      level_high=_v2_slot(gq, value=7),
                                      level_shape_hint="point",
                                      level_unit="m_usd"))
    lawful = metric(oq, "headcount", 9)
    return [rejected, conflict, lawful]


def test_a_rejected_fact_that_exactly_matches_gold_earns_zero_credit():
    """THE MUTATION. `rejected` is a byte-identical copy of a gold row, so the
    matcher would link it and it would earn recall and field credit for a
    record the route refused to write."""
    import copy
    from scorers import score_exp5 as SCO
    facts = _conflicted_arm()
    gold = [copy.deepcopy(facts[0]), copy.deepcopy(facts[2])]
    for g in gold:
        g["du_worthy"] = True

    # the law sees the conflict, and it costs exactly the two facts that bear it
    bad = SCO.conflicting_driver_names({"facts": facts})
    assert bad == {"revenue"}
    assert SCO.facts_bearing({"facts": facts}, bad) == {0, 1}

    # ELIGIBILITY: the rejected pair never reaches the matcher, and the lawful
    # fact keeps its ORIGINAL index so terminal accounting can still name it
    v2, pos = SCO.eligible_produced(facts)
    assert len(v2) == 1, "a rejected fact reached the matcher"
    assert sorted(pos.values()) == [2], pos

    from driver.core.fact_match import match_facts
    gold_v2, gold_pos = SCO._to_v2_with_positions(gold)
    mr = match_facts(gold_v2, v2)
    linked_gold = {gold_pos[id(g)] for g, _p in mr.links}
    assert 0 not in linked_gold, "the rejected exact match captured a gold row"

    # THE POSITIVE CONTROL: with no conflict at all, the same shapes DO link
    lawful_only = [facts[2]]
    v2b, posb = SCO.eligible_produced(lawful_only)
    assert len(v2b) == 1 and sorted(posb.values()) == [0]
    mrb = match_facts(*(SCO._to_v2_with_positions([gold[1]])[0], v2b))
    assert mrb.links, "the lawful control did not link, so this proves nothing"


def test_eligibility_never_filters_a_parked_or_skipped_fact():
    """The eligibility owner restates NO other law: only the conflicting-name
    rejection removes a fact from matching."""
    from scorers import score_exp5 as SCO
    facts = _conflicted_arm()
    clean = [facts[2]]                      # no conflicting name at all
    assert SCO.conflicting_driver_names({"facts": clean}) == set()
    v2, pos = SCO.eligible_produced(clean)
    assert len(v2) == len(clean) and sorted(pos.values()) == [0]


# ---- Codex 1465.3: one input, many facts - and the accounting is exact ----
def _one_quote_pair(name_a, name_b):
    """TWO facts located at ONE quote - the only lawful shape for a split.

    A raw item carries one quote, and the route refuses a reply whose fact
    quotes something else, so a split's branches necessarily share it.
    """
    q = "s" * 60
    def one(name, value):
        return _v2_fact(q, fact_type="metric",
                        item=_v2_item(q, driver_name=name, fiscal_year=2050,
                                      fiscal_quarter=1, time_type="duration",
                                      level_low=_v2_slot(q, value=value),
                                      level_high=_v2_slot(q, value=value),
                                      level_shape_hint="point",
                                      level_unit="m_usd"))
    return [one(name_a, 5), one(name_b, 6)]


def _route_entry(facts, groups=None):
    """A REAL route entry for a synthetic event, optionally packet-grouped."""
    arm = {"E1": {"facts": facts, "abstentions": []}}
    return _route_for(arm, groups_by_sid={"E1": groups} if groups else None)["E1"]


def test_one_raw_input_with_two_facts_keeps_BOTH_branches():
    """The production route preserves several rows at one raw index. The old
    replay turned every fact into its own raw input, so this shape could not
    occur at all and nothing tested it."""
    from scorers.score_exp5 import _rows_for_event
    facts = _one_quote_pair("revenue", "margin")
    grouped = _route_entry(facts, groups=[[0, 1]])
    idxs = [r["index"] for r in grouped["result"]["items"]]
    assert idxs == [0, 0], idxs
    # and each branch still reaches its OWN outcome row
    out = _rows_for_event({"E1": grouped}, "E1", facts, 0)
    assert set(out) == {("fact", 0), ("fact", 1)}
    assert out[("fact", 0)] is not out[("fact", 1)]

    # THE CONTROL: ungrouped, the same facts are two separate raw inputs
    apart = _route_entry(facts)
    assert [r["index"] for r in apart["result"]["items"]] == [0, 1]


def test_a_split_with_mixed_outcomes_loses_neither_branch():
    """One lawful fact and one the route cannot write, on ONE raw index."""
    from scorers.score_exp5 import _rows_for_event
    q = "z" * 60
    lawful = _v2_fact(q, fact_type="metric",
                      item=_v2_item(q, driver_name="revenue",
                                    fiscal_year=2050, fiscal_quarter=1,
                                    time_type="duration",
                                    level_low=_v2_slot(q, value=5),
                                    level_high=_v2_slot(q, value=5),
                                    level_shape_hint="point",
                                    level_unit="m_usd"))
    unknown = _v2_fact(q, fact_type="metric",
                       item=_v2_item(q, driver_name="not_a_stored_driver",
                                     fiscal_year=2050, fiscal_quarter=1,
                                     time_type="duration",
                                     level_low=_v2_slot(q, value=6),
                                     level_high=_v2_slot(q, value=6),
                                     level_shape_hint="point",
                                     level_unit="m_usd"))
    facts = [lawful, unknown]
    entry = _route_entry(facts, groups=[[0, 1]])
    idxs = [r["index"] for r in entry["result"]["items"]]
    assert idxs == [0, 0], idxs
    out = _rows_for_event({"E1": entry}, "E1", facts, 0)
    decisions = sorted(out[("fact", i)]["decision"] for i in (0, 1))
    assert len(set(decisions)) >= 1 and len(out) == 2, decisions


def test_the_rejection_accounting_is_required_and_exactly_rederived():
    from scorers.score_exp5 import _rows_for_event
    facts = _one_quote_pair("revenue", "margin")
    entry = _route_entry(facts, groups=[[0, 1]])
    assert entry["rejected_conflicting_names"] == []
    assert entry["rejected_fact_idxs"] == []

    for label, broken in (
            ("a missing accounting key",
             {k: v for k, v in entry.items()
              if k != "rejected_fact_idxs"}),
            ("an unknown key", dict(entry, surprise=1)),
            ("a negative index", dict(entry, rejected_fact_idxs=[-1])),
            ("a boolean index", dict(entry, rejected_fact_idxs=[True])),
            ("a duplicate index", dict(entry, rejected_fact_idxs=[0, 0])),
            ("an index past the end", dict(entry, rejected_fact_idxs=[99])),
            ("a name that does not rederive",
             dict(entry, rejected_conflicting_names=["revenue"],
                  rejected_fact_idxs=[0])),
            ("accounting that is not a list",
             dict(entry, rejected_fact_idxs="0")),):
        with pytest.raises(ValueError):
            _rows_for_event({"E1": broken}, "E1", facts, 0)


def test_a_partially_rejected_packet_still_serves_its_survivors():
    """A packet can be part rejected. The raw item must still be served, its
    quote taken from a SURVIVING fact, and every survivor must keep the
    original index its caller already holds."""
    from scorers.score_exp5 import (project_replay_items,
                                    conflicting_driver_names, facts_bearing)
    reply = {"facts": [
        {"fact_type": "metric", "item": {"driver_name": "rev", "quote": "q1"}},
        {"fact_type": "guidance", "item": {"driver_name": "rev", "quote": "q1"}},
        {"fact_type": "metric", "item": {"driver_name": "hc", "quote": "q1"}}]}
    bad = conflicting_driver_names(reply)
    skip = facts_bearing(reply, bad)
    assert bad == {"rev"} and skip == {0, 1}

    items, imap = project_replay_items(reply, skip_facts=skip,
                                       groups=[[0, 1, 2]])
    assert len(items) == 1, "the packet lost its raw item entirely"
    assert items[0]["quote"] == "q1"
    assert imap == {("fact", 2): 0}, imap

    # A PACKET WHOSE FACTS ARE ALL REJECTED serves nothing at all, rather than
    # an empty raw item the route would have to interpret.
    items2, imap2 = project_replay_items(reply, skip_facts={0, 1, 2},
                                         groups=[[0, 1, 2]])
    assert items2 == [] and imap2 == {}


def test_a_fact_with_no_driver_name_is_never_rejected_by_this_law():
    """The conflicting-name law is about NAMES. A nameless fact has none, so it
    cannot conflict and must not be filtered by the eligibility owner."""
    from scorers.score_exp5 import conflicting_driver_names, facts_bearing
    reply = {"facts": [
        {"fact_type": "metric", "item": {"driver_name": None, "quote": "q"}},
        {"fact_type": "guidance", "item": {"driver_name": None, "quote": "q"}}]}
    assert conflicting_driver_names(reply) == set()
    assert facts_bearing(reply, set()) == set()
