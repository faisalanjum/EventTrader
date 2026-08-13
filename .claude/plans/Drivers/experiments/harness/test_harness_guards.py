"""Persistent failure-case tests for the K-fields exam guards (reviewer order
2026-07-24): each test proves a guard TRIPS on its failure case, and the pass
cases pass. Every failure scenario runs on TEMP COPIES — the frozen exam files
are never touched (test_frozen_untouched proves it inside this very suite).

Run: venv/bin/python -m pytest harness/test_harness_guards.py -q
"""
import hashlib
import json
import pytest
from decimal import Decimal
import os
import re
import shutil

import audit_worker_access as AUD
import build_kfields_inputs as BLD
import kf_lint as LNT

_HERE = os.path.dirname(os.path.abspath(__file__))
#: The manifest stores REPO-RELATIVE input paths on purpose — an absolute path
#: would pin one machine. They must therefore be resolved against the repo root,
#: never against the current directory: doing the latter made the launch-plan
#: test pass from the repo root and fail from this directory, i.e. the proof
#: depended on where pytest happened to be invoked.
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
KF = os.path.join(_HERE, "..", "keys", "K-fields")
INPUTS = os.path.join(KF, "draft_inputs")
HASHES = os.path.join(KF, "draft_inputs.hashes.json")


EVENTS_DIR = os.path.join(_HERE, "..", "fixtures", "events")
FROZEN_SET = (
    [os.path.join(INPUTS, f) for f in sorted(os.listdir(INPUTS))]
    + [os.path.join(EVENTS_DIR, f) for f in sorted(os.listdir(EVENTS_DIR))]
    + [HASHES,
       os.path.join(KF, "protocol.md"),
       os.path.join(KF, "drafting_wrapper.md"),
       os.path.join(_HERE, "exp5_prompt_drafter.md"),
       os.path.join(_HERE, "exp5_prompt_producer.md"),
       os.path.join(_HERE, "exp5_prompt_contract.manifest.json")])


def _frozen_state():
    out = {}
    for p in FROZEN_SET:
        out[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    assert len(out) == 78, f"frozen set must be the FULL 78 files, got {len(out)}"
    return out


FROZEN_BEFORE = _frozen_state()


def _agent(dirp, name, assigned, reads, extra_tools=()):
    """Write a synthetic worker transcript."""
    lines = [{"message": {"role": "user",
                          "content": f"Read {AUD.WRAPPER} then {AUD.CONTRACT} "
                                     f"then {assigned}. Go."}}]
    for p in reads:
        lines.append({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": p}}]}})
    for t in extra_tools:
        lines.append({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": t, "input": {"command": "x"}}]}})
    with open(os.path.join(dirp, f"agent-{name}.jsonl"), "w") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")


SID = sorted(os.listdir(INPUTS))[0][:-5]
ASSIGNED = os.path.realpath(os.path.join(INPUTS, f"{SID}.json"))
ALL3 = [AUD.WRAPPER, AUD.CONTRACT, ASSIGNED]


# ---- auditor v3 ----

def test_auditor_fails_empty_dir(tmp_path):
    assert AUD.audit(str(tmp_path)) == 1


def test_auditor_fails_wrong_count(tmp_path):
    _agent(str(tmp_path), "a1", ASSIGNED, ALL3)
    assert AUD.audit(str(tmp_path), expect=2) == 1


def test_auditor_fails_missing_required_read(tmp_path):
    _agent(str(tmp_path), "a1", ASSIGNED, [AUD.WRAPPER, ASSIGNED])  # no contract
    assert AUD.audit(str(tmp_path), expect=1) == 1


def test_auditor_fails_other_events_input(tmp_path):
    other = os.path.realpath(os.path.join(
        INPUTS, sorted(os.listdir(INPUTS))[1]))
    _agent(str(tmp_path), "a1", ASSIGNED, ALL3 + [other])
    assert AUD.audit(str(tmp_path), expect=1) == 1


def test_auditor_fails_forbidden_tool(tmp_path):
    _agent(str(tmp_path), "a1", ASSIGNED, ALL3, extra_tools=("Bash",))
    assert AUD.audit(str(tmp_path), expect=1) == 1


def test_auditor_passes_clean_worker(tmp_path):
    _agent(str(tmp_path), "a1", ASSIGNED, ALL3)
    assert AUD.audit(str(tmp_path), expect=1) == 0


# ---- kf_lint v3 ----

def _fact(**over):
    """A stored GOLD fact: the exact V2 model fact plus ONLY the three review
    fields. The retired gold_item wrapper and duplicate outer quote are gone."""
    q, part_ref, occ = _v2_locator()
    f = _v2_fact(q)
    f.update({"du_worthy": True,
              "gold_extra": {"expectation_comparison_present": False},
              "ambiguity_note": None})
    f.update(over)
    return f


def _doc(facts, abstentions=None):
    """The gold document uses the SAME envelope as the model reply (Step 2 §7)."""
    return {"source_id": SID, "facts": facts,
            "abstentions": abstentions or []}


def _lint(tmp_path, docs, arm=False):
    p = tmp_path / "draft.jsonl"
    p.write_text("\n".join(json.dumps(d) for d in docs))
    return LNT.run(str(p), arm=arm)


def test_lint_fails_empty_input(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("")
    assert LNT.run(str(p)) == 1


def test_lint_arm_fails_single_doc(tmp_path):
    assert _lint(tmp_path, [_doc([_fact()])], arm=True) == 1


def test_lint_fails_blank_quote(tmp_path):
    """A blank ITEM quote must be refused BY THE CORE QUOTE RULE.

    This proof used to also set an OUTER `f["quote"] = ""`, which is not a gold
    fact key at all. `lint_doc` rejected that extra key first, so the test went
    green without the item-quote rule ever being reached — it would have kept
    passing if blank item quotes became acceptable. Only the invented outer
    assignment is removed here; the blank item quote and the count stay."""
    f = _fact()
    f["item"]["quote"] = ""
    errs = []
    LNT.lint_doc(_doc([f]), errs, INPUTS)
    assert len(errs) == 1, errs
    assert "quote" in errs[0].lower(), f"refused for the wrong reason: {errs[0]}"




def test_lint_fails_wrong_type_cleanly(tmp_path):
    """V2 shape: a wrong-typed slot VALUE is refused by the slot owner, not by a
    scalar rule in this module (that duplicate was deleted per Step 2 §7)."""
    q, pr, oc = _v2_locator()
    f = _v2_fact(q)
    f["item"]["level_low"] = _v2_slot(q, value="726")   # string, not a number
    assert _v2_lint(_v2_doc([f]))                       # errors, not a crash


def test_lint_fails_extra_fact_key(tmp_path):
    f = _fact()
    f["bonus"] = 1
    assert _lint(tmp_path, [_doc([f])]) == 1



def test_lint_passes_valid_doc(tmp_path):
    assert _lint(tmp_path, [_doc([_fact()])]) == 0


# ---- immutable-manifest builder ----

def _copy_exam(tmp_path):
    d = tmp_path / "draft_inputs"
    shutil.copytree(INPUTS, d)
    h = tmp_path / "hashes.json"
    shutil.copy(HASHES, h)
    return str(d), str(h)


def test_builder_check_passes_intact_copy(tmp_path):
    d, h = _copy_exam(tmp_path)
    assert BLD.check(out_dir=d, hashes_path=h) == 0


def test_builder_check_fails_changed_file(tmp_path):
    d, h = _copy_exam(tmp_path)
    victim = os.path.join(d, sorted(os.listdir(d))[0])
    with open(victim, "a") as f:
        f.write(" ")
    assert BLD.check(out_dir=d, hashes_path=h) == 1


def test_builder_check_fails_missing_file(tmp_path):
    d, h = _copy_exam(tmp_path)
    os.remove(os.path.join(d, sorted(os.listdir(d))[0]))
    assert BLD.check(out_dir=d, hashes_path=h) == 1


def test_builder_check_fails_extra_file(tmp_path):
    d, h = _copy_exam(tmp_path)
    with open(os.path.join(d, "zz_extra.json"), "w") as f:
        f.write("{}")
    assert BLD.check(out_dir=d, hashes_path=h) == 1


def test_builder_check_fails_missing_manifest(tmp_path):
    d, _ = _copy_exam(tmp_path)
    assert BLD.check(out_dir=d, hashes_path=str(tmp_path / "no.json")) == 1


def test_builder_write_refuses_existing_manifest(tmp_path):
    d, h = _copy_exam(tmp_path)
    assert BLD.write(out_dir=d, hashes_path=h) == 2


def test_builder_write_refuses_nonempty_dir(tmp_path):
    d, _ = _copy_exam(tmp_path)
    assert BLD.write(out_dir=d, hashes_path=str(tmp_path / "new.json")) == 2


# ---- round-8 additions: lint v4 + fact16 rule-18 trips ----
import sys as _sys
_sys.path.insert(0, os.path.join(_HERE, "scorers"))




def test_lint_clean_on_int_date(tmp_path):
    f = _fact()
    f["item"]["period_start_date"] = 123
    assert _lint(tmp_path, [_doc([f])]) == 1     # error lines, no exception


def test_lint_clean_on_list_driver_state(tmp_path):
    f = _fact()
    f["item"]["driver_state"] = []
    assert _lint(tmp_path, [_doc([f])]) == 1     # was: unhashable TypeError


def test_lint_clean_on_list_fact_type(tmp_path):
    f = _fact(fact_type=[])
    assert _lint(tmp_path, [_doc([f])]) == 1     # was: unhashable TypeError


# ---- raw transport: digits must survive to Python (no AI; 2026-07-25) ----
import raw_transport as RT

# the exact pair a JS `JSON.parse` collapses to the SAME double (proven with
# node: {"a":1.0…01,"b":1.0…02} -> {"a":1,"b":1})
_COLLAPSE_A = "1.00000000000000000001"
_COLLAPSE_B = "1.00000000000000000002"


def test_transport_preserves_digits_js_would_collapse(tmp_path):
    """END-TO-END over the REAL capture path (no AI): raw text -> saved
    unchanged -> exact Decimal parse. The two values must stay DISTINCT."""
    text = ('{"source_id":"E1","facts":[{"a":' + _COLLAPSE_A +
            ',"b":' + _COLLAPSE_B + '}]}')
    path, digest = RT.save_raw(text, str(tmp_path), "arm1")
    doc = RT.parse_exact(text)
    # 1. the bytes on disk are the model's text, unchanged
    assert open(path, encoding="utf-8").read() == text
    assert digest == hashlib.sha256(text.encode()).hexdigest()
    # 2. the digits survived the parse
    a, b = doc["facts"][0]["a"], doc["facts"][0]["b"]
    assert isinstance(a, Decimal) and isinstance(b, Decimal)
    assert str(a) == _COLLAPSE_A and str(b) == _COLLAPSE_B
    assert a != b, "the transport collapsed two distinct numbers"


def test_transport_proves_the_js_path_would_have_lost_them():
    """Guards the guard: if these two numbers ever stop colliding under
    double parsing, this test is no longer proving anything."""
    lossy = json.loads('{"a":' + _COLLAPSE_A + ',"b":' + _COLLAPSE_B + '}')
    assert lossy["a"] == lossy["b"], "not a float-collapse pair any more"


def test_generated_launcher_EXECUTES_with_fake_agents(tmp_path):
    """Runs the GENERATED launcher itself (node, fake agents, no AI/network).
    Catches what a text grep cannot: a syntax break — the stray `}` my SCHEMA
    deletion left would have made every paid run fail instantly."""
    import subprocess
    if not shutil.which("node"):
        return                                   # node absent: nothing to assert
    m = json.load(open(os.path.join(_HERE, "launch_kfields_drafts.manifest.json")))
    ev = tmp_path / "ev.json"
    ev.write_text(json.dumps([{"source_id": e["source_id"], "ticker": "T",
                               "input_path": e["input_path"]} for e in m["events"]]))
    r = subprocess.run(
        ["node", os.path.join(_HERE, "run_launcher_fake.mjs"),
         os.path.join(_HERE, "launch_kfields_drafts.workflow.js"), str(ev)],
        capture_output=True, text=True)
    assert r.returncode == 0, f"generated launcher failed to run:\n{r.stderr[:400]}"
    got = json.loads(r.stdout)
    assert got["rows"] == 36 and got["agent_calls"] == 72
    assert got["all_lean_probe"] and got["all_high"]
    assert got["models"] == ["opus", "sonnet"]
    assert got["any_schema"] is False, "schema: would let JS collapse numbers"
    assert got["first_arm_is_raw_string"] and got["digits_intact"]


def _wf_row(sid, raw):
    return {"source_id": sid, "ticker": "T", "sonnet": raw, "opus": raw}


def _full_result(raw_for):
    """A complete, manifest-matching workflow result (all 36 events, both arms)."""
    return {"events": 36, "results": [_wf_row(s, raw_for(s)) for s in RT.manifest_events()]}


def _reply_for(sid, low=None, high=None):
    """A per-event GOLD reply in the V2 shape. The quote must come from THAT
    event's own part, and the number lives at slot["value"]."""
    with open(os.path.join(INPUTS, sid + ".json"), encoding="utf-8") as fh:
        parts = json.load(fh)["text_parts"]
    part = max(parts, key=lambda x: len(x["content"]))
    q = part["content"][:100]
    item = _v2_item(q)
    f = {"fact_type": "metric", "part_ref": part["part"],
         "occurrence_in_part": (None if part["content"].count(q) == 1 else 1),
         "per_x": None, "item": item,
         "du_worthy": True,
       "gold_extra": {"expectation_comparison_present": False},
       "ambiguity_note": None}
    if low is not None:
        f["item"]["level_low"] = {"value": "__LO__", "scale_multiplier": 1,
                                  "unit_scale_evidence": q[:12]}
        f["item"]["level_high"] = {"value": "__HI__", "scale_multiplier": 1,
                                   "unit_scale_evidence": q[:12]}
    body = json.dumps({"source_id": sid, "facts": [f], "abstentions": []})
    if low is not None:
        body = body.replace('"__LO__"', low).replace('"__HI__"', high)
    return body


def test_LIVE_workflow_handoff_delivers_Decimal_to_the_validator(tmp_path):
    """THE REAL HAND-OFF (no AI): the launcher workflow's ACTUAL return shape,
    manifest-complete, carrying a high-precision number — the validator must
    receive an exact Decimal, not a rounded float and not a string."""
    res = _full_result(lambda s: _reply_for(s, _COLLAPSE_A, _COLLAPSE_B)
                       if s == SID else _reply_for(s))
    out = RT.ingest_workflow_result(res, str(tmp_path))
    assert out["ok"], out["errors"]
    got = out["docs"][(SID, "sonnet")]
    assert open(got["raw_path"], encoding="utf-8").read() == _reply_for(
        SID, _COLLAPSE_A, _COLLAPSE_B)
    item = got["doc"]["facts"][0]["item"]
    # V2: the number lives at slot["value"]; the Decimal-exactness law this test
    # exists to prove is unchanged, only its location moved to the owner's shape.
    lo = item["level_low"]["value"] if isinstance(item["level_low"], dict) \
        else item["level_low"]
    hi = item["level_high"]["value"] if isinstance(item["level_high"], dict) \
        else item["level_high"]
    assert isinstance(lo, Decimal) and isinstance(hi, Decimal)
    assert str(lo) == _COLLAPSE_A and str(hi) == _COLLAPSE_B and lo != hi


def test_ingest_rejects_missing_events(tmp_path):
    res = _full_result(_reply_for)
    res["results"] = res["results"][:-1]              # 35 of 36
    out = RT.ingest_workflow_result(res, str(tmp_path))
    assert not out["ok"] and any("MISSING" in e for e in out["errors"])


def test_ingest_rejects_duplicate_rows(tmp_path):
    res = _full_result(_reply_for)
    res["results"].append(dict(res["results"][0]))    # same event twice
    out = RT.ingest_workflow_result(res, str(tmp_path))
    assert not out["ok"] and any("DUPLICATE" in e for e in out["errors"])


def test_ingest_preserves_a_duplicate_rows_PAID_replies(tmp_path):
    """A duplicate row is REJECTED, but its replies were still paid for — they
    must be preserved under a distinct .dupN name, never silently discarded."""
    res = _full_result(_reply_for)
    dup_sid = res["results"][0]["source_id"]
    res["results"].append(dict(res["results"][0]))
    out = RT.ingest_workflow_result(res, str(tmp_path), validate=False)
    assert not out["ok"] and any("DUPLICATE" in e for e in out["errors"])
    for arm in RT.ARMS:
        assert os.path.exists(os.path.join(tmp_path, f"{dup_sid}.{arm}.raw.json"))
        assert os.path.exists(os.path.join(
            tmp_path, f"{dup_sid}.dup1.{arm}.raw.json")), "paid duplicate reply lost"


def test_ingest_handles_a_malformed_row_without_crashing(tmp_path):
    for bad in ["not-a-dict", 42, None, ["x"]]:
        out = RT.ingest_workflow_result({"results": [bad]}, str(tmp_path),
                                        validate=False)
        assert not out["ok"] and any("must be an object" in e or
                                     "source_id" in e for e in out["errors"])


def test_parser_refuses_nan_infinity_and_duplicate_keys():
    for bad in ['{"v":NaN}', '{"v":Infinity}', '{"v":-Infinity}']:
        try:
            RT.parse_exact(bad); assert False, f"{bad} accepted"
        except RT.RawTransportError as e:
            assert "non-standard" in str(e)
    try:
        RT.parse_exact('{"source_id":"A","source_id":"B"}')
        assert False, "duplicate key accepted"
    except RT.RawTransportError as e:
        assert "duplicate JSON key" in str(e)
    # nested objects are covered too
    try:
        RT.parse_exact('{"facts":[{"q":1,"q":2}]}'); assert False, "nested dup accepted"
    except RT.RawTransportError as e:
        assert "duplicate JSON key" in str(e)


def test_ingest_rejects_wrong_event_reply(tmp_path):
    """A reply whose INNER source_id is a different event must be refused."""
    other = [s for s in RT.manifest_events() if s != SID][0]
    res = _full_result(lambda s: _reply_for(other) if s == SID else _reply_for(s))
    out = RT.ingest_workflow_result(res, str(tmp_path))
    assert not out["ok"] and any("WRONG-EVENT" in e for e in out["errors"])
    assert (SID, "sonnet") not in out["docs"]


def test_ingest_saves_every_paid_reply_even_if_one_is_malformed(tmp_path):
    """A malformed EARLY reply must never cost the later PAID replies."""
    bad = RT.manifest_events()[0]
    res = _full_result(lambda s: "{oops" if s == bad else _reply_for(s))
    out = RT.ingest_workflow_result(res, str(tmp_path))
    assert not out["ok"]
    for sid in RT.manifest_events():
        for arm in RT.ARMS:
            assert os.path.exists(os.path.join(
                tmp_path, f"{sid}.{arm}.raw.json")), f"{sid}.{arm} was not saved"


def test_ingest_refuses_to_overwrite_a_captured_reply(tmp_path):
    res = _full_result(_reply_for)
    assert RT.ingest_workflow_result(res, str(tmp_path))["ok"]
    out = RT.ingest_workflow_result(res, str(tmp_path))       # same dir again
    assert not out["ok"] and any("refusing to overwrite" in e for e in out["errors"])


def test_ingest_validates_both_arms_automatically(tmp_path):
    """Validation is not optional or caller-remembered: a contract-breaking
    reply fails ingestion itself."""
    def broken(sid):
        d = json.loads(_reply_for(sid))
        del d["facts"][0]["item"]["driver_name"]         # 36 of 37 fields
        return json.dumps(d)
    out = RT.ingest_workflow_result(_full_result(broken), str(tmp_path))
    assert not out["ok"] and any("FAILED strict validation" in e
                                 for e in out["errors"])


def test_transport_rejects_preparsed_object(tmp_path):
    """A dict means something already parsed the JSON upstream (the JS
    `schema:` path) — digits may be gone, so refuse it loudly."""
    try:
        RT.save_raw({"source_id": "E1"}, str(tmp_path), "arm1")
        assert False, "a pre-parsed object must be rejected"
    except RT.RawTransportError as e:
        assert "TEXT" in str(e)


def test_transport_hands_off_to_the_single_validator(tmp_path):
    """Enforcement is not lost by dropping JS schema parsing — it MOVES here:
    raw -> exact parse -> the one authoritative checker (kf_lint)."""
    f = _fact()
    text = json.dumps(_doc([f]))
    path, _d = RT.save_raw(text, str(tmp_path), "arm1")
    doc = RT.parse_exact(text)
    assert LNT.lint_parsed([doc], INPUTS, door="gold") == 0   # same contract, after the parse


# ---- matcher safety: value-only matches must NEVER auto-credit (2026-07-25) ----
def _vfact(name, low, high=None, quote="x" * 90, **over):
    """A LAWFUL V2 fact for the matcher tests, built by the EXISTING owners.

    Lifted from the retired scorer shape (`lane` / `gold_item` /
    `level_unit_raw`). It delegates to `_v2_fact` / `_v2_item` / `_v2_slot`
    rather than restating 32 defaults: a second fixture would be a second schema
    owner, which is what this whole change removes (Codex SEQ 1118).
    """
    item = _v2_item(quote, driver_name=name,
                    level_low=_v2_slot(quote, value=low),
                    level_high=_v2_slot(quote, value=high if high is not None else low),
                    level_unit="m_usd", level_shape_hint="point",
                    **{k: v for k, v in over.items() if k not in ("fact_type",)})
    return _v2_fact(quote, item=item, fact_type=over.get("fact_type", "metric"))

def test_matcher_never_auto_matches_different_drivers_on_equal_value():
    """revenue $100M vs capital_expenditures $100M: same number, DIFFERENT
    driver, no quote overlap. Auto-pairing would credit recall for a MISSED
    fact and compare fields across unrelated facts."""
    gold = [_vfact("revenue", 100,
                   quote="Revenue was $100 million for the quarter, a solid result.")]
    prod = [_vfact("capital_expenditures", 100,
                   quote="Capital expenditures totalled $100 million in the period.")]
    from driver.core.fact_match import match_facts
    from driver.core.prepared_fact_v2 import PreparedFactV2
    _mf = _match_with_positions
    _r = _mf(gold, prod)
    pairs, ambiguous = _r.links, _r.to_grading_gold
    assert pairs == [], "value-only match across DIFFERENT drivers must not auto-pair"
    assert len(ambiguous) == 1, "it must surface for grading, not vanish silently"


def _idfact(name, low, quote, **extra):
    """A lawful V2 fact for the identity/matching tests, via the existing owners.

    Was the retired `lane`/`gold_item` wrapper carrying `level_unit_raw`, a V1
    field. `record_key` spans all 32 item fields, so these tests only need the
    fields they vary; everything else comes from `_v2_item`.
    """
    item = _v2_item(quote, driver_name=name,
                    level_low=_v2_slot(quote, value=low),
                    level_high=_v2_slot(quote, value=low),
                    level_unit="m_usd", level_shape_hint="point",
                    **{k: v for k, v in extra.items() if k != "fact_type"})
    return _v2_fact(quote, item=item, fact_type=extra.get("fact_type", "metric"))


def test_matcher_rejects_same_name_value_DIFFERENT_PERIOD():
    """Q1 revenue $100M vs Q2 revenue $100M: same driver, same number,
    DIFFERENT period = DIFFERENT facts. Name+value can never prove identity."""
    gold = [_idfact("revenue", 100, "First quarter revenue was $100 million in total.",
                    fiscal_year=2026, fiscal_quarter=1)]
    prod = [_idfact("revenue", 100, "Second quarter revenue came in at $100 million.",
                    fiscal_year=2026, fiscal_quarter=2)]
    from driver.core.fact_match import match_facts
    from driver.core.prepared_fact_v2 import PreparedFactV2
    _mf = _match_with_positions
    _r = _mf(gold, prod)
    pairs, ambiguous = _r.links, _r.to_grading_gold
    assert pairs == [], "different-period facts must not auto-match on name+value"
    assert len(ambiguous) == 1, "must surface for grading"


def test_matcher_rejects_same_name_value_DIFFERENT_SLICE():
    gold = [_idfact("revenue", 100, "Segment A revenue was $100 million for the period.",
                    slice_parts=["segment:a"])]
    prod = [_idfact("revenue", 100, "Segment B contributed $100 million of revenue.",
                    slice_parts=["segment:b"])]
    from driver.core.fact_match import match_facts
    from driver.core.prepared_fact_v2 import PreparedFactV2
    _mf = _match_with_positions
    _r = _mf(gold, prod)
    pairs, ambiguous = _r.links, _r.to_grading_gold
    assert pairs == [] and len(ambiguous) == 1


def test_matcher_rejects_same_name_value_DIFFERENT_MEASUREMENT():
    gold = [_idfact("operating_income", 100, "GAAP operating income was $100 million.",
                    measurement_raw_spans=[])]
    prod = [_idfact("operating_income", 100, "Adjusted operating income totalled $100 million.",
                    measurement_raw_spans=["Adjusted"])]
    from driver.core.fact_match import match_facts
    from driver.core.prepared_fact_v2 import PreparedFactV2
    _mf = _match_with_positions
    _r = _mf(gold, prod)
    pairs, ambiguous = _r.links, _r.to_grading_gold
    assert pairs == [] and len(ambiguous) == 1


def test_matcher_one_sentence_two_facts_is_order_free():
    """One sentence carries BOTH Q1 and Q2 revenue; the model produced only Q2.
    A shared span is a candidate LINK, not proof — crediting whichever gold
    happens to come first is an order-dependent false credit."""
    import itertools
    from driver.core.fact_match import match_facts
    from driver.core.prepared_fact_v2 import PreparedFactV2
    _mf = _match_with_positions
    S = ("Revenue was $100 million in the first quarter and $120 million "
         "in the second quarter.")
    g1 = _idfact("revenue", 100, S, fiscal_quarter=1)
    g2 = _idfact("revenue", 120, S, fiscal_quarter=2)
    prod = [_idfact("revenue", 120, S, fiscal_quarter=2)]
    seen = set()
    for gold in itertools.permutations([g1, g2]):
        _r = _mf(list(gold), prod)
        # WHAT THE SHARED SPAN MUST NOT DO IS CREDIT THE WRONG GOLD. Under
        # `record_key` the produced fact is IDENTICAL to the Q2 gold, so linking
        # it is CORRECT — the old `links == []` expectation belonged to the
        # retired overlap matcher, where a shared sentence alone could pair
        # records. Exactly ONE link, and it must be the Q2 row whatever the gold
        # order; the Q1 row goes to grading, never auto-credited.
        assert len(_r.pairs) == 1, f"expected one exact link, got {_r.pairs}"
        gold_idx, _prod_idx = _r.pairs[0]
        assert gold[gold_idx]["item"]["fiscal_quarter"] == 2, (
            "the shared span credited the WRONG gold row")
        assert len(_r.to_grading_gold) == 1, "the unmatched Q1 gold must surface"
        seen.add((len(_r.links), len(_r.to_grading_gold)))
    assert len(seen) == 1, f"result depends on gold ORDER: {seen}"


def test_matcher_exact_evidence_is_order_free_and_not_fuzzy():
    """B-15: order-freeness survives; the fuzzy/candidate vocabulary does not.

    `fact_match.match_facts` is deterministic and order-free by construction —
    the result depends only on the SETS of records. The retired matcher's
    "contains the gold quote" win is gone with it, because a link now requires an
    identical `record_key`, not overlapping text. The old ambiguity reason this
    test also asserted has no current owner and is not carried forward.
    """
    import itertools
    from driver.core.fact_match import match_facts
    from driver.core.prepared_fact_v2 import PreparedFactV2
    qa, qb = "Revenue rose five percent in the quarter.", "Costs fell two percent."
    conv = lambda f: PreparedFactV2.from_dict(f)
    g = [conv(_v2_fact(qa)), conv(_v2_fact(qb))]
    pr = [conv(_v2_fact(qa)), conv(_v2_fact(qb))]
    outcomes = set()
    for go in itertools.permutations(g):
        for po in itertools.permutations(pr):
            r = match_facts(list(go), list(po))
            outcomes.add((len(r.links), len(r.to_grading_gold),
                          len(r.to_grading_produced), r.emit_once_violation))
    assert outcomes == {(2, 0, 0, False)}, (
        f"match_facts is not order-free over these sets: {outcomes}")


def test_matcher_locator_distinguishes_repeats_of_one_sentence():
    """Same wording twice in a part is disambiguated by occurrence_in_part —
    exact identity, no fuzz."""
    from driver.core.fact_match import match_facts
    from driver.core.prepared_fact_v2 import PreparedFactV2
    _mf = _match_with_positions
    q = "Revenue was $100 million."
    def f(occ):
        # the locator lives at fact level in V2, not inside a gold_item wrapper
        return _v2_fact(q, occurrence_in_part=occ)
    _r = _mf([f(1)], [f(2)])
    pairs, amb = _r.pairs, _r.to_grading_gold
    assert pairs == [] and amb, "different occurrences are different evidence"
    _r2 = _mf([f(1)], [f(1)])
    pairs2 = _r2.pairs
    assert pairs2 == [(0, 0)]




# ---- v2.0 lint corrections (ChatGPT audit 2026-07-25; claims 2/3/4) ----
def test_lint_accepts_du_worthy_false(tmp_path):
    # protocol: du_worthy:false = OPTIONAL near-miss exemplar (LAWFUL, not rejected)
    f = _fact(du_worthy=False)
    assert _lint(tmp_path, [_doc([f])]) == 0


def test_lint_fails_non_bool_du_worthy(tmp_path):
    f = _fact(du_worthy="yes")
    assert _lint(tmp_path, [_doc([f])]) == 1



def test_lint_fails_null_measurement_list(tmp_path):
    f = _fact()
    f["item"]["measurement_raw_spans"] = None  # PreparedFactV1: non-null list
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_null_slice_parts_list(tmp_path):
    f = _fact()
    f["item"]["slice_parts"] = None            # PreparedFactV1: non-null list
    assert _lint(tmp_path, [_doc([f])]) == 1



def test_lint_decimal_exact_END_TO_END(tmp_path):
    """Exercises kf_lint.run() itself with two literals ordinary float parsing
    COLLAPSES. As a `range` they satisfy low < high ONLY under exact Decimal
    parsing — so this goes RED the moment parse_float=Decimal is lost."""
    # V2: the number lives at slot["value"]. The proof is unchanged — ordinary
    # float parsing must COLLAPSE these two literals, and only exact Decimal
    # transport keeps them distinct.
    LOW, HIGH = "1.00000000000000000001", "1.00000000000000000002"
    q, _pr, _oc = _v2_locator()
    f = _fact()
    f["item"]["level_low"] = _v2_slot(q, value="__LO__")
    f["item"]["level_high"] = _v2_slot(q, value="__HI__")
    line = json.dumps(_doc([f])).replace('"__LO__"', LOW).replace('"__HI__"', HIGH)
    # the test is only meaningful if ordinary parsing really collapses them:
    collapsed = json.loads(line)["facts"][0]["item"]
    assert (collapsed["level_low"]["value"]
            == collapsed["level_high"]["value"]), "not a float-collapse pair"
    p = tmp_path / "draft.jsonl"
    p.write_text(line)
    assert LNT.run(str(p)) == 0      # exact Decimal keeps low < high -> clean


def test_lint_clean_on_list_enum_value(tmp_path):
    f = _fact()
    f["item"]["level_shape_hint"] = ["point"]
    assert _lint(tmp_path, [_doc([f])]) == 1



# ---- round-11: scorer metadata mandatory + fiscal-only future parks ----
from score_exp5 import score_arm


def _surprise_gold_and_arm():
    gq, aq = "x" * 60, "y" * 60
    gold = {"E1": [_gold_fact(gq, fact_type="surprise",
                              gold_extra={"expectation_comparison_present": True})]}
    arm = {"E1": {"facts": [_v2_fact(aq, fact_type="surprise", item=_v2_item(
        aq, surprise_basis_hint="actual", comparison_baseline="consensus",
        fiscal_year=2050, fiscal_quarter=1, time_type="duration",
        level_low=_v2_slot(aq, value=5), level_high=_v2_slot(aq, value=5),
        level_shape_hint="point", level_unit="m_usd"))]}}
    return gold, arm


def test_scorer_requires_event_meta():
    gold, arm = _surprise_gold_and_arm()
    try:
        score_arm(gold, arm, None, route=_route_for(arm))
        assert False, "must raise without event_meta"
    except ValueError:
        pass


def test_scorer_requires_complete_meta_per_event():
    gold, arm = _surprise_gold_and_arm()
    try:
        score_arm(gold, arm, {"E1": {"event_date": "2026-04-23"}},   # fye missing
                  route=_route_for(arm))
        assert False, "must raise on incomplete meta"
    except ValueError:
        pass


def test_scorer_parks_fiscal_only_future_surprise():
    gold, arm = _surprise_gold_and_arm()
    r = score_arm(gold, arm,
                  {"E1": {"event_date": "2026-04-23", "fye_month": 12}},
                  route=_route_for(arm))
    # THE OUTCOME IS `rejected`, NOT `parked` — measured, and the distinction is
    # deliberate (SEQ 1126.4): a rejection carries its own code and must never be
    # renamed into the park rate, which would hide a contract violation inside a
    # routine-looking number. So this asserts the REAL public code for an actual
    # surprise dated before its period ends (OD-21 F7), not a would-park figure
    # that is correctly 0.0.
    assert r["route_codes"].get("rejected:F7") == 1, r["route_codes"]
    assert r["PASS"] is not True


# ---- round-12: the LAUNCH MANIFEST machine proof (per-event-per-lane) ----

def test_launch_manifest_exact_plan():
    mp = os.path.join(_HERE, "launch_kfields_drafts.manifest.json")
    m = json.load(open(mp))
    evs = m["events"]
    assert len(evs) == 36 and m["n_events"] == 36 and m["n_workers"] == 72
    sids = [e["source_id"] for e in evs]
    assert len(set(sids)) == 36, "duplicate events in the plan"
    expected_sids = sorted(x[:-5] for x in os.listdir(INPUTS)
                           if x.endswith(".json"))
    assert sorted(sids) == expected_sids, "plan events != the frozen exam set"
    for e in evs:
        models = sorted(l["model"] for l in e["lanes"])
        assert models == ["opus", "sonnet"],             f"{e['source_id']}: lanes must be EXACTLY one sonnet + one opus"
        for l in e["lanes"]:
            assert l["effort"] == "high" and l["agentType"] == "lean-probe"
        assert hashlib.sha256(open(os.path.join(_REPO, e["input_path"]), "rb").read()).hexdigest()             == e["input_sha256"], f"{e['source_id']}: input drifted"
    # pins == the LIVE files (a stale manifest must fail)
    live = {
        "contract": os.path.join(_HERE, "exp5_prompt_drafter.md"),
        "contract_manifest": os.path.join(_HERE,
                                          "exp5_prompt_contract.manifest.json"),
        "wrapper": os.path.join(KF, "drafting_wrapper.md"),
        "protocol": os.path.join(KF, "protocol.md"),
        "inputs_manifest": HASHES,
    }
    for k, p in live.items():
        assert m["pins"][k] == hashlib.sha256(open(p, "rb").read()).hexdigest(),             f"pin {k} stale vs live file"
    # v2.1: the 60-200 quote band is DEAD LAW (it was never in the WorkOrder);
    # SEQ 1093: the copied schema block is DELETED — it was a second owner of the
    # item shape, and swapping its 37 for another hand-written count would have
    # kept the defect. What the plan pins instead is the exact prompt each worker
    # receives, plus the disabled zero-call state.
    assert "schema" not in m, "the copied schema block is back"
    assert m["made_calls"] == 0, "a disabled plan must record made_calls = 0"
    js = open(os.path.join(_HERE, "launch_kfields_drafts.workflow.js"),
              encoding="utf-8").read()
    k = js.index("const PROMPTS = ")
    prompts = json.loads(js[k + 16:js.index("\n", k)])
    assert len(prompts) == len(evs), "prompt count != planned events"
    for e in evs:
        body = prompts[e["source_id"]]
        assert hashlib.sha256(body.encode("utf-8")).hexdigest() == e["prompt_sha256"], \
            f"{e['source_id']}: manifest pin != the bytes the worker receives"
        assert "<<EVENT>>" not in body and body.index("[EVENT]") > body.index("[BOUNDARY]")
    # (the 37-field assertion is DELETED with the copied schema block it read;
    #  the item shape is owned by the Step-2 builder, not restated here)
    b = m["budget"]
    assert b["quarantined"] + b["fresh_drafts"] + b["briefs_max"] ==         b["total_cap"] == 100
    # the persisted workflow script must set lean-probe and must NOT parse the
    # reply in JavaScript (`schema:` would collapse high-precision numbers)
    ws = open(os.path.join(_HERE,
                           "launch_kfields_drafts.workflow.js")).read()
    assert ws.count("agentType: 'lean-probe'") == 2
    assert "minLength: 60" not in ws, "dead 60-200 quote band still in the launcher"
    assert "schema: SCHEMA" not in ws, "JS schema-parsing would destroy exact numbers"
    assert "EXPECTED[e.source_id]" in ws     # manifest-bound, not length-only


# ---- round-12b: the five scorer completions ----
from score_exp5 import (score_union, _canon_level, _meas_tokens,
                        final_gate, presence_disagreement,
                        MEANING_FIELDS)

_META1 = {"E1": {"event_date": "2026-04-23", "fye_month": 12}}
def _full_verdicts(n=4):
    return {("E1", i): {k: True for k in MEANING_FIELDS}
            for i in range(n)}


def _metric_pair(g_slice, p_slice, g_meas=None, p_meas=None):
    q = "z" * 80
    # RETIRED V1 fields mapped by supersession, not dropped silently:
    #   level_unit_raw ("USD millions") -> the canonical `level_unit` ("m_usd")
    #   slice                            -> `slice_parts`
    #   level_unit_kind_hint / level_money_mode_hint -> RETIRED, no successor
    gi = {"driver_name": "revenue", "driver_state": "reported", "quote": q,
          "level_low": _v2_slot(q, value=5), "level_high": _v2_slot(q, value=5),
          "level_shape_hint": "point", "level_unit": "m_usd",
          "time_type": "duration",
          "period_start_date": "2026-01-01", "period_end_date": "2026-03-31",
          "slice_parts": g_slice, "measurement_raw_spans": g_meas or []}
    pi = dict(gi, slice_parts=p_slice, measurement_raw_spans=p_meas or [])
    gold = {"E1": [_gold_fact(q, item=_v2_item(gi.get('quote', q), **{k: v for k, v in gi.items() if k != 'quote'}))]}
    arm = {"E1": {"facts": [_v2_fact(q, item=_v2_item(pi.get('quote', q), **{k: v for k, v in pi.items() if k != 'quote'}))]}}
    return gold, arm


def test_scorer_wrong_slice_drops_accuracy():
    gold, arm = _metric_pair(["segment:acetylchain"], ["segment:engineered"])
    # the slice DIFFERS, so the pair no longer auto-links (an auto-link needs an
    # identical complete record) — the grader names it by index so the
    # difference can be scored rather than silently unmatched
    r = score_arm(gold, arm, _META1, _full_verdicts(), route=_route_for(arm),
                  ambiguity_resolutions={("E1", 0): 0})
    assert r["value_shape_acc"] < 1.0 and r["PASS"] is False


def test_scorer_wrong_measurement_drops_accuracy():
    gold, arm = _metric_pair([], [], g_meas=["adjusted"], p_meas=[])
    r = score_arm(gold, arm, _META1, _full_verdicts(), route=_route_for(arm),
                  ambiguity_resolutions={("E1", 0): 0})
    assert r["value_shape_acc"] < 1.0


def test_scorer_measurement_normalization_equivalent():
    assert _meas_tokens({"measurement_raw_spans": ["Adjusted Diluted"]}) ==         _meas_tokens({"measurement_raw_spans": ["adjusted_diluted"]})




def test_scorer_union_recall_beats_single():
    q1, q2 = "a" * 80, "b" * 80
    def gfact(q):
        return _gold_fact(q)
    gold = {"E1": [gfact(q1), gfact(q2)]}
    arm_a = {"E1": {"facts": [_v2_fact(q1, fact_type="metric")]}}
    arm_b = {"E1": {"facts": [_v2_fact(q2, fact_type="metric")]}}
    ra = score_arm(gold, arm_a, _META1, route=_route_for(arm_a))["recall"]
    ru = score_union(gold, arm_a, arm_b, _META1,
                     route=_union_route(gold, arm_a, arm_b))["recall"]
    assert ra == 0.5 and ru == 1.0


def test_scorer_parks_grounded_surprise_without_home_sibling():
    q = "c" * 80
    gold = {"E1": [_gold_fact(q, fact_type="surprise",
                              gold_extra={"expectation_comparison_present": True})]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="surprise", item=_v2_item(
        # a NAMED, grounded surprise with a lawful surprise state. `_v2_item`
        # defaults `driver_state` to "reported", which is not in the surprise
        # lane — the route then REJECTS on STATE and the orphan rule this test
        # names is never reached.
        q, driver_name="revenue_surprise", driver_state="beat",
        surprise_basis_hint="actual", comparison_baseline="consensus",
        level_low=_v2_slot(q, value=5), level_high=_v2_slot(q, value=5),
        level_shape_hint="point", level_unit="m_usd", time_type="duration",
        period_start_date="2026-01-01",
        period_end_date="2026-03-31"))]}}
    r = score_arm(gold, arm, _META1, _full_verdicts(), route=_route_for(arm))
    # F6: a named surprise with NO same-event home parks as an orphan
    assert r["route_codes"].get("park:F6") == 1, r["route_codes"]
    assert r["would_park"] > 0.10 and r["PASS"] is not True


def test_scorer_emits_ambiguous_for_grader():
    q = "d" * 80
    gold = {"E1": [_gold_fact(q)]}
    arm = {"E1": {"facts": [
        _v2_fact(q, fact_type="metric"),
        _v2_fact(q, fact_type="metric")]}}
    r = score_arm(gold, arm, _META1, route=_route_for(arm))
    assert len(r["ambiguous_rows"]) >= 1
    # THE DUPLICATE COLLAPSES AND THE SURVIVOR LEGITIMATELY MATCHES, so
    # `matched == 1` is correct — the old `== 0` belonged to the retired
    # candidate matcher, where two candidates for one gold made it ambiguous.
    # The finding here is the EMIT-ONCE violation, which must block PASS and be
    # surfaced; the duplicate simply earns no EXTRA recall.
    assert r["matched"] == 1, r
    assert "emit_once_violation" in r["route_codes"], r["route_codes"]
    assert r["extras"]["duplicate"] == 1, r["extras"]
    assert r["PASS"] is not True, r


# ---- round-13 direct failure tests ----




def test_exact_decimal_no_rounding_merge():
    """Two values differing in the 8th decimal must never merge.

    MIGRATED TO V2 SLOTS. It used to hand `_canon_level` raw `Decimal`s plus
    `level_unit_raw` and the two retired hints, and rely on the unit RESOLVER's
    scaled output. That resolver is gone from scoring: EXP-5 field truth is the
    slot OBJECT compared exactly (WorkOrder §649). The requirement is unchanged
    and is if anything stricter now — no scaling step can round two distinct
    values together, because the raw `value` is compared as given.
    """
    q = "d" * 80
    a = _canon_level(_v2_item(q, level_low=_v2_slot(q, value=Decimal("1.00000004")),
                              level_high=_v2_slot(q, value=Decimal("1.00000004"))))
    b = _canon_level(_v2_item(q, level_low=_v2_slot(q, value=Decimal("1.00000014")),
                              level_high=_v2_slot(q, value=Decimal("1.00000014"))))
    assert a != b, "distinct values must never merge"


def _surprise_with_home(home_period_end, home_driver="revenue",
                        home_value=726):
    """Migrated as ONE unit: the two arm records AND the gold record together.

    Lifting only the inner records left the outer gold still wearing the retired
    wrapper, which no shape accepts — measured at +2 failures and reverted.
    `lane` IS `fact_type` and is carried explicitly: dropping it turned a
    SURPRISE into a metric in tests whose whole subject is that relationship.
    Retired fields by supersession: level_unit_raw ("USD millions") -> the
    canonical `level_unit` ("m_usd"); the two hint fields deleted, no successor;
    magnitudes into the V2 slot objects.
    """
    q1, q2 = "s" * 80, "h" * 80
    sp = _v2_fact(q1, fact_type="surprise", item=_v2_item(
        q1, driver_name="revenue_surprise", driver_state="beat",
        #   ^ `_v2_item` DEFAULTS driver_state to "reported", which is not in the
        #     surprise lane vocabulary — the route rejected the whole fixture
        #     with STATE, so every home assertion below was measuring a lane
        #     error instead of the home rule it names.
        surprise_basis_hint="actual",
        comparison_baseline="consensus",
        level_low=_v2_slot(q1, value=726), level_high=_v2_slot(q1, value=726),
        level_shape_hint="point", level_unit="m_usd", time_type="duration",
        period_start_date="2026-01-01", period_end_date="2026-03-31"))
    home = _v2_fact(q2, fact_type="metric", item=_v2_item(
        q2, driver_name=home_driver,
        level_low=_v2_slot(q2, value=home_value),
        level_high=_v2_slot(q2, value=home_value),
        level_shape_hint="point", level_unit="m_usd", time_type="duration",
        period_start_date="2026-01-01", period_end_date=home_period_end))
    gold = {"E1": [_gold_fact(q1, fact_type="surprise",
                              gold_extra={"expectation_comparison_present": True})]}
    arm = {"E1": {"facts": [sp, home]}}
    return gold, arm


def test_home_fact_correct_sibling_no_park():
    gold, arm = _surprise_with_home("2026-03-31")
    assert score_arm(gold, arm, _META1, route=_route_for(arm))["would_park"] == 0.0


def test_home_fact_wrong_period_parks():
    gold, arm = _surprise_with_home("2026-06-30")
    assert score_arm(gold, arm, _META1, route=_route_for(arm))["would_park"] > 0.0


def test_home_fact_unrelated_driver_parks():
    gold, arm = _surprise_with_home("2026-03-31", home_driver="fuel_cost")
    assert score_arm(gold, arm, _META1, route=_route_for(arm))["would_park"] > 0.0


def test_home_fact_value_mismatch_parks():
    gold, arm = _surprise_with_home("2026-03-31", home_value=999)
    assert score_arm(gold, arm, _META1, route=_route_for(arm))["would_park"] > 0.0


def test_union_dedup_no_inflation():
    from score_exp5 import dedup_items
    q = "q" * 80
    f = _v2_fact(q, fact_type="metric", item=_v2_item(
        q, level_low=_v2_slot(q, value=5), level_high=_v2_slot(q, value=5)))
    assert len(dedup_items([f, dict(f)])) == 1


def test_presence_disagreement_metric():
    q1, q2 = "a" * 80, "b" * 80
    def gfact(q):
        return _gold_fact(q)
    gold = {"E1": [gfact(q1), gfact(q2)]}
    arm_a = {"E1": {"facts": [_v2_fact(q1, fact_type="metric")]}}
    arm_b = {"E1": {"facts": [_v2_fact(q2, fact_type="metric")]}}
    assert presence_disagreement(gold, arm_a, arm_b, _META1) == 1.0
    assert presence_disagreement(gold, arm_a, arm_a, _META1) == 0.0


def test_final_gate_or_semantics():
    base = {"PASS": True, "recall": 0.96, "wrong_lane": 0,
            "value_shape_acc": 1.0, "state_acc": 1.0, "would_park": 0.0}
    assert final_gate(base, None) is True                 # single alone
    low = dict(base, PASS=False, recall=0.90)
    u_hi = dict(base, recall=0.99)
    u_lo = dict(base, recall=0.97)
    assert final_gate(low, u_hi) is True                  # union rescues
    assert final_gate(low, u_lo) is False                 # neither bar met
    # a fully-green union leg DECIDES even while the single is pending
    assert final_gate(dict(base, PASS=None), u_hi) is True
    assert final_gate(low, dict(u_hi, PASS=None)) is None


def test_workflow_bound_to_locked_manifest():
    ws = open(os.path.join(_HERE,
                           "launch_kfields_drafts.workflow.js")).read()
    m = json.load(open(os.path.join(
        _HERE, "launch_kfields_drafts.manifest.json")))
    for e in m["events"]:                 # every locked pair embedded
        assert e["source_id"] in ws and e["input_path"] in ws
    assert "unknown event" in ws and "swapped/wrong input" in ws
    assert "no duplicates" in ws
    assert ws.count("agentType: 'lean-probe'") == 2


# ---- round-14 attack tests ----
from score_exp5 import _canon_item_values


def test_home_slice_must_match_through_the_PUBLIC_ROUTE(tmp_path):
    """FINAL_DESIGN.md:153 names `slice` among the fields a home must match, and
    `driver_validators` owns it — so it is proven through the route, both ways.

    Retired `slice` -> canonical `slice_parts`, and parts are `"kind:value"`
    STRINGS per the locked packet law (a tuple is a SchemaError).

    TWO SIBLING TESTS WERE DELETED HERE, NOT SILENTLY DROPPED (Codex SEQ 1125.4):

    * `test_home_numberless_needs_numberless` — SUPERSEDED. Its exact requirement,
      in both directions, is now
      `test_home_numberless_sibling_pairing_is_enforced_by_the_route`, which
      proves it through `run_event` instead of the retired `_home_ok`.

    * `test_home_unresolved_periods_never_match` — HELPER-ONLY, deleted per the
      frozen denominator. §153 requires the home to MATCH on period; it never
      requires the period to be RESOLVED. Measured: with both sides unresolved
      the public route WRITES the surprise. That rule existed only inside
      `_home_ok`, so recreating it here would be inventing law. Reported to Codex.
    """
    for parts, decision, code in (("segment:a", "written", None),
                                  ("segment:b", "parked", "F9")):
        row = _home_route_case({"slice_parts": ["segment:a"]},
                               {"driver_state": "reported",
                                "level_low": _slot_point(),
                                "level_high": _slot_point(),
                                "level_shape_hint": "point",
                                "level_unit": "m_usd",
                                "slice_parts": [parts]}, tmp_path)
        assert row["decision"] == decision, (
            f"home slice {parts!r} against surprise 'segment:a' reached "
            f"{row['decision']!r} {row['codes']}, expected {decision!r}")
        if code:
            assert code in row["codes"], f"slice {parts!r}: codes {row['codes']}"


def test_unresolved_tie_blocks_pass():
    # THE PENDING STATE IS THE POINT, so the run must be one the tie could
    # still RESCUE. The old fixture had 19 IDENTICAL golds, so recall was 0.05
    # and the run was a DEFINITE fail (False) whatever anyone ruled — it proved
    # blocking, but never the pending state it names.
    #
    # Now: 19 unique golds answered cleanly, plus ONE duplicate-gold pair that
    # nobody can lawfully credit. potential_recall stays high enough that the
    # verdict must be PENDING (None) rather than a known failure.
    uniq = [chr(65 + i) * 80 for i in range(19)]
    tie_q = "z" * 80
    # `_mut_item` supplies a RESOLVABLE period; the bare default parks every
    # fact on PERIOD_UNRESOLVED, which pushed would_park to 1.0 and made the run
    # a definite fail for a reason this test is not about.
    gold = {"E1": [_gold_fact(q, item=_mut_item(q)) for q in uniq]
                  + [_gold_fact(tie_q, item=_mut_item(tie_q)),
                     _gold_fact(tie_q, item=_mut_item(tie_q))]}
    facts = [_v2_fact(q, fact_type="metric", item=_mut_item(q)) for q in uniq]
    facts.append(_v2_fact(tie_q, fact_type="metric", item=_mut_item(tie_q)))
    arm = {"E1": {"facts": facts}}
    V = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(21)}
    r = score_arm(gold, arm, _META1, V, route=_route_for(arm))
    assert r["ambiguities_unresolved"] >= 1, r
    assert r["PASS"] is None, (
        f"an unresolved tie must leave the verdict PENDING, got {r['PASS']!r} "
        f"(recall {r['recall']})")




def test_union_keeps_different_facts():
    from score_exp5 import dedup_items
    q = "q" * 80
    def _dated(end):
        return _v2_fact(q, fact_type="metric", item=_v2_item(
            q, level_low=_v2_slot(q, value=5), level_high=_v2_slot(q, value=5),
            time_type="duration", period_start_date="2025-01-01",
            period_end_date=end))
    f1, f2 = _dated("2026-03-31"), _dated("2025-03-31")
    assert len(dedup_items([f1, f2])) == 2
    assert len(dedup_items([f1, dict(f1)])) == 1


def test_state_accuracy_not_diluted():
    q = [chr(65 + i) * 80 for i in range(10)]     # A*80, B*80 ... distinct
    def gf(i):
        return _gold_fact(q[i], fact_type="metric",
                          gold_extra={"expectation_comparison_present": False})
    gold = {"E1": [gf(i) for i in range(10)]}
    arm = {"E1": {"facts": [_v2_fact(q[i], fact_type="metric")
                            for i in range(10)]}}
    V = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(10)}
    V[("E1", 0)] = dict(V[("E1", 0)], driver_state=False)   # 9/10 state
    r = score_arm(gold, arm, _META1, V, route=_route_for(arm))
    assert r["state_acc"] == 0.9 and r["PASS"] is False


def test_false_lane_verdict_increments_wrong_lane():
    q = "w" * 80
    gold = {"E1": [_gold_fact(q)]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="metric")]}}
    V = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    V[("E1", 0)]["lane_routing"] = False
    r = score_arm(gold, arm, _META1, V, route=_route_for(arm))
    assert r["wrong_lane"] == 1 and r["PASS"] is False




def test_final_gate_union_axes_govern():
    single = {"PASS": False, "recall": 0.90, "wrong_lane": 0,
              "value_shape_acc": 1.0, "state_acc": 1.0, "would_park": 0.0}
    union_dirty = {"PASS": False, "recall": 0.99, "wrong_lane": 1,
                   "value_shape_acc": 1.0, "state_acc": 1.0,
                   "would_park": 0.0}
    union_clean = {"PASS": True, "recall": 0.99, "wrong_lane": 0,
                   "value_shape_acc": 1.0, "state_acc": 1.0,
                   "would_park": 0.0}
    assert final_gate(single, union_dirty) is False   # union wrong-lane blocks
    assert final_gate(single, union_clean) is True


def test_generator_idempotent_AND_matches_the_committed_artifacts(tmp_path):
    """Two builds must agree with each other AND with what is committed, and the
    build must not touch the tree.

    TWO DEFECTS THIS CLOSES. The old version ran the generator IN PLACE, so a test
    rewrote two tracked files on every run — invisible here, and caught only when
    the commit gate started re-checking the tree after pytest. And it compared the
    two builds only to EACH OTHER: a generator that deterministically produces
    something different from the committed artifact passed happily. That is
    exactly what was happening — the manifest held absolute `/home/...` paths, so
    every regeneration rewrote all 36 of them.
    """
    import subprocess
    names = ("launch_kfields_drafts.workflow.js",
             "launch_kfields_drafts.manifest.json",
             "launch_exp5_readers.manifest.json")
    # THE COPY MUST HAVE THE REAL DEPTH. The generator derives the repository
    # root by walking five directories up from its own file, and writes paths
    # relative to it — so a flat copy silently produces different relative paths
    # and the comparison fails for a reason that has nothing to do with the
    # artifacts. Reproduce the layout, not just the files.
    exp = tmp_path / ".claude" / "plans" / "Drivers" / "experiments"
    work = exp / "harness"
    shutil.copytree(_HERE, work, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    shutil.copytree(os.path.join(_HERE, "..", "keys"), exp / "keys",
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    # STEP3 §5 BINDING NEEDS THE AUTHORITY AND CORE FILES. The reader plan pins
    # the WorkOrder, FINAL_DESIGN, the staged contract, step3.md and the Core
    # route/matcher, so a reproducible build genuinely requires them — the
    # generator FAILS LOUDLY without them rather than binding a placeholder,
    # which is the behaviour we want. The copy therefore reproduces the exact
    # subtrees the pins name, not just the harness.
    for rel in (os.path.join(".claude", "plans", "Drivers", "FinalDesign"),
                os.path.join("driver", "core")):
        src = os.path.join(_REPO, rel)
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__",
                                                      ".pytest_cache"))
    g = str(work / "build_launch_manifest.py")

    def _hashes():
        return tuple(hashlib.sha256((work / n).read_bytes()).hexdigest()
                     for n in names)

    subprocess.run([_REPO_VENV, g], check=True, capture_output=True)
    h1 = _hashes()
    subprocess.run([_REPO_VENV, g], check=True, capture_output=True)
    assert _hashes() == h1, "two consecutive builds must be byte-identical"
    committed = tuple(hashlib.sha256(
        open(os.path.join(_HERE, n), "rb").read()).hexdigest() for n in names)
    assert h1 == committed, (
        "the committed artifacts are not what the generator produces — one of "
        "them is stale, or the generator records machine-specific values")


# THE INTERPRETER RUNNING THIS TEST, not a path guessed from the tree layout.
# `<repo>/venv/bin/python` exists only on a machine where someone made a venv at
# that exact spot; in any clean checkout of the commit it is simply absent, and
# the test failed with FileNotFoundError while claiming to check build
# determinism. `sys.executable` is the interpreter that is demonstrably present.
_REPO_VENV = _sys.executable


# ---- round-15 attack tests ----

def _matched_pair(g_over=None, p_over=None):
    """A gold/produced pair the GRADER links, so the difference can be SCORED.

    These tests exist to check what happens when the produced side differs. That
    difference is exactly what stops `match_facts` auto-linking — an auto-link
    needs an IDENTICAL complete record — so without a ruling the pair never
    reaches field comparison and every counter stayed 0. The ruling names the
    pair BY INDEX; nothing infers it from quotes or values.

    A resolvable period is supplied so the facts are route-ACCEPTED rather than
    parked on PERIOD_UNRESOLVED, which would make these assertions measure a
    period error instead of the field they name.
    """
    q = "m" * 80
    period = {"time_type": "duration", "period_start_date": "2026-01-01",
              "period_end_date": "2026-03-31"}
    gi = {"driver_name": "revenue", "quote": q, **period}
    pi = dict(gi)
    gi.update(g_over or {})
    pi.update(p_over or {})
    _mk = lambda d: _v2_item(d.get("quote", q),
                             **{k: v for k, v in d.items() if k != "quote"})
    gold = {"E1": [_gold_fact(q, item=_mk(gi))]}
    arm = {"E1": {"facts": [_v2_fact(q, item=_mk(pi))]}}
    V = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    return score_arm(gold, arm, _META1, V, route=_route_for(arm),
                     ambiguity_resolutions={("E1", 0): 0})


def test_wrong_driver_name_fails():
    r = _matched_pair(p_over={"driver_name": "fuel_cost"})
    assert r["wrong_name"] >= 1 and r["PASS"] is False


# `test_wrong_unit_hints_fail` DELETED (B-16 retired-field list). It mutated
# `level_unit_kind_hint` and `level_money_mode_hint` — both DELETED from V2 with
# NO successor — so it asserted that scoring notices a difference in fields that
# no longer exist. There is no V2 behaviour to re-point it at; recreating one
# would be inventing a rule the model never carries.






def _slot_point():
    """The one numeric slot these home cases use. A function, not a constant, so
    each case gets its own instance and no test can mutate another's."""
    from driver.core.test_v2_attacks import slot
    return slot(5, 1, None)


def _home_route_case(sp_over, home_over, tmp_path):
    """§153 home law proven THROUGH the public route — never a scorer-side copy.

    Codex SEQ 1125: all three home distinctions are LIVE requirements
    (FINAL_DESIGN.md:153 for the value/unit cases, FableExperimentWorkOrder.md:423
    for the numberless sibling), so they are rewritten here rather than deleted.
    This case reaches the retired `_home_ok` NOWHERE, and it does not copy
    `driver_validators._home_mismatch` either: it builds a surprise plus a
    candidate home into ONE event and returns the SURPRISE's real outcome row.
    (No test calls `_home_ok` any more. It still EXISTS in the scorer, which
    still calls it internally; B-16 deletes both. Stated precisely so this
    docstring cannot be read as a completion claim it has not earned.)

    Periods are derived from the event's own `event_time`, never hardcoded. The
    retired fixture hardcoded 2026 dates against a 2024 event; through the real
    route that is an OD-21 F7 reject ("actual surprise before period end"), so
    every case died before the home check ever ran and proved nothing.
    """
    import datetime
    from driver.core.driver_write_cli import run_event
    from scorers.score_exp5 import project_replay_items, replay_reader
    R = _core_route_fixtures()
    base = R._v2_events()[R.CE_EVENT]
    raw0 = base["items"][0]
    end = datetime.date.fromisoformat(base["event_time"][:10]) - datetime.timedelta(days=30)
    period = {"time_type": "duration", "period_end_date": end.isoformat(),
              "period_start_date": (end - datetime.timedelta(days=89)).isoformat()}
    point = _slot_point()
    surprise = {"driver_name": "revenue_surprise", "driver_state": "beat",
                "surprise_basis_hint": "actual", "comparison_baseline": "consensus",
                "level_low": point, "level_high": point,
                "level_shape_hint": "point", "level_unit": "m_usd", **period}
    surprise.update(sp_over)
    home = {"driver_name": "revenue", **period}
    home.update(home_over)
    reply = {"source_id": R.CE_EVENT, "abstentions": [],
             "facts": [R._text_fact(base, raw0, fact_type="surprise", **surprise),
                       R._text_fact(base, raw0, fact_type="metric", **home)]}
    items, reader = replay_reader(reply)
    _, index_map = project_replay_items(reply)
    event = {**base, "items": items}
    result = run_event(event, store=R._mirror_fake(event), audit_dir=str(tmp_path),
                       enable_writes=False, reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    return rows[index_map[("fact", 0)]]


NUMBERLESS = {"level_low": None, "level_high": None, "level_shape_hint": None,
              "level_unit": None, "driver_state": "unknown"}


@pytest.mark.parametrize("shape,decision,code,why", [
    ("floor", "parked", "F9",
     "a FLOOR lacks the matching high endpoint, so it is not a matching home"),
    ("point", "written", None,
     "equal point endpoints, unit, and the other §153 identity fields"),
])
def test_home_value_shape_is_decided_by_the_PUBLIC_ROUTE(shape, decision, code,
                                                         why, tmp_path):
    """FINAL_DESIGN.md:153 — a value-bearing home must match on normalized
    value/unit. Both directions live in ONE parametrized owner so the lawful
    control cannot silently rot into the refusal case."""
    home = {"driver_state": "reported", "level_low": _slot_point(),
            "level_high": None if shape == "floor" else _slot_point(),
            "level_shape_hint": shape, "level_unit": "m_usd"}
    row = _home_route_case({}, home, tmp_path)
    assert row["decision"] == decision, (
        f"{why}: expected {decision!r}, got {row['decision']!r} {row['codes']}")
    if code:
        assert code in row["codes"], f"{why}: codes {row['codes']}"
    else:
        assert row["codes"] == [], f"{why}: lawful home carried {row['codes']}"


def test_home_numberless_sibling_pairing_is_enforced_by_the_route(tmp_path):
    """FableExperimentWorkOrder.md:423 — a grounded NUMBERLESS surprise gets a
    NUMBERLESS home sibling. The PAIRING half is production-owned, so it is
    proven here in both directions."""
    numbered = {"driver_state": "reported", "level_low": _slot_point(),
                "level_high": _slot_point(), "level_shape_hint": "point",
                "level_unit": "m_usd"}
    row = _home_route_case(NUMBERLESS, numbered, tmp_path)
    assert row["decision"] == "parked" and "F9" in row["codes"], (
        "a numberless surprise must not accept a NUMBERED home: "
        f"{row['decision']!r} {row['codes']}")

    lawful = {"driver_state": "unknown", "level_low": None, "level_high": None,
              "level_shape_hint": None, "level_unit": None}
    ok = _home_route_case(NUMBERLESS, lawful, tmp_path)
    assert ok["decision"] == "written" and ok["codes"] == [], (
        f"the lawful numberless sibling was refused: {ok['decision']!r} {ok['codes']}")


# DELETED (Codex SEQ 1126): a strict xfail here claimed a production/authority
# mismatch over the numberless home's `driver_state`. That framing was WRONG.
# FableExperimentWorkOrder.md:649 assigns the meaning fields — "driver_state,
# lane routing incl. the ISS-16 surprise-twin presence, OD-13 favorability,
# OD-11 basis, slice pick vs menu" — to the QUALIFIED GRADER. The public route
# owns structural/lane validation and home PAIRING, never the semantic choice
# between two lawful metric states, so there was no production defect to record.
# The pairing half stays proven above; `driver_state=unknown` is proven instead
# through B-16's grader ingestion/accuracy accounting.


def test_union_accepts_tie_resolutions():
    q = "t" * 80
    gold = {"E1": [_gold_fact(q)]}
    arm_a = {"E1": {"facts": [_v2_fact(q, fact_type="metric")]}}
    arm_b = {"E1": {"facts": [_v2_fact(q, fact_type="metric",
                                      item=_v2_item(q, fiscal_year=2026))]}}
    V = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    r = score_union(gold, arm_a, arm_b, _META1, V,
                    ambiguity_resolutions={("E1", 0): 0},
                    route=_union_route(gold, arm_a, arm_b))
    assert r["ambiguities_unresolved"] == 0 and r["matched"] == 1


def test_empty_arm_is_definite_fail():
    q = "e" * 80
    # ADOPTED gold shape (the exact V2 fact + only the review fields); the
    # retired `lane`/`gold_item` wrapper is not accepted by the scorer.
    gold = {"E1": [_gold_fact(q)]}
    r = score_arm(gold, _EMPTY_ARM, _META1, route=_route_for(_EMPTY_ARM))
    assert r["PASS"] is False, "an empty answer is a DEFINITE fail, never None"


def test_error_table_rule_grouped():
    r = _matched_pair(p_over={"driver_name": "fuel_cost"})
    assert "error_table_by_rule" in r
    assert set(r["error_table_by_rule"]) >= {"OD-9", "OD-11", "OD-12", "OD-13",
                                             "OD-14", "OD-21", "ISS-16",
                                             "shapes", "slices"}


def test_frozen_proof_artifact_has_before_and_after():
    p = os.path.join(_HERE, "frozen_proof_r15.txt")
    t = open(p).read()
    assert "## BEFORE" in t and "## AFTER" in t
    assert t.count("  ") >= 154                    # 77 + 77 hash lines
    assert "BEFORE == AFTER, 77/77 byte-identical" in t


# ---- round-16 attack tests ----

def test_name_errors_never_dilute():
    """55% wrong names across 20 pairs with null-padded items must FAIL."""
    qs = [chr(65 + i) * 80 for i in range(20)]
    def gf(i):
        return _gold_fact(qs[i], fact_type="metric",
                          item=_v2_item(qs[i], driver_name="revenue"),
                          gold_extra={"expectation_comparison_present": False})
    gold = {"E1": [gf(i) for i in range(20)]}
    facts = [_v2_fact(qs[i], fact_type="metric",
                      item=_v2_item(qs[i],
                                    driver_name=("W" + str(i) if i < 11
                                                 else "revenue")))
             for i in range(20)]
    V = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(20)}
    r = score_arm(gold, _arm(facts), _META1, V, route=_route_for(_arm(facts)),
                  ambiguity_resolutions={("E1", i): i for i in range(20)})
    assert r["wrong_name"] == 11 and r["PASS"] is False




def test_numberless_home_without_a_quote_is_REFUSED_by_the_route(tmp_path):
    """THE ONE LAW — no quote, no fact — proven where production enforces it.

    The retired version asked `_home_ok` whether a quoteless home "counts". The
    real route answers something stronger and more useful: the quoteless home is
    REJECTED outright as a channel-contract violation, so it never becomes a home
    at all, and the grounded surprise then parks as an orphan (F6). Both halves
    are asserted, because the rejection alone would not show that the surprise
    lost its sibling.

    Built without `_text_fact` deliberately: that helper supplies the raw item's
    own quote, so it cannot express "a fact with no quote".
    """
    from driver.core.driver_write_cli import run_event
    from driver.core.test_v2_attacks import item as v2_item
    from scorers.score_exp5 import project_replay_items, replay_reader
    import datetime
    R = _core_route_fixtures()
    base = R._v2_events()[R.CE_EVENT]
    raw0 = base["items"][0]
    end = datetime.date.fromisoformat(base["event_time"][:10]) - datetime.timedelta(days=30)
    period = {"time_type": "duration", "period_end_date": end.isoformat(),
              "period_start_date": (end - datetime.timedelta(days=89)).isoformat()}
    surprise = {"driver_name": "revenue_surprise", "driver_state": "beat",
                "surprise_basis_hint": "actual", "comparison_baseline": "consensus",
                **NUMBERLESS, **period}

    for home_quote, sp_decision, sp_code, home_decision in (
            ("", "parked", "F6", "rejected"),
            (raw0["quote"], "written", None, "written")):
        home_item = v2_item(quote=home_quote, driver_name="revenue",
                            driver_state="unknown", level_low=None, level_high=None,
                            level_shape_hint=None, level_unit=None, **period)
        reply = {"source_id": R.CE_EVENT, "abstentions": [],
                 "facts": [R._text_fact(base, raw0, fact_type="surprise", **surprise),
                           {"fact_type": "metric", "occurrence_in_part": None,
                            "part_ref": base["text_parts"][0]["part"],
                            "per_x": None, "item": home_item}]}
        items, reader = replay_reader(reply)
        _, index_map = project_replay_items(reply)
        event = {**base, "items": items}
        result = run_event(event, store=R._mirror_fake(event),
                           audit_dir=str(tmp_path), enable_writes=False, reader=reader)
        rows = {r["index"]: r for r in result["items"]}
        sp_row = rows[index_map[("fact", 0)]]
        home_row = rows[index_map[("fact", 1)]]
        label = "quoteless" if not home_quote else "quoted"
        assert home_row["decision"] == home_decision, (
            f"{label} home reached {home_row['decision']!r} {home_row['codes']}")
        assert sp_row["decision"] == sp_decision, (
            f"{label} home -> surprise {sp_row['decision']!r} {sp_row['codes']}")
        if sp_code:
            assert sp_code in sp_row["codes"], (
                f"{label}: surprise codes {sp_row['codes']}")
            assert "CHANNEL_CONTRACT_INVALID" in home_row["codes"], (
                f"{label}: home codes {home_row['codes']}")


def test_clean_union_rescues_incomplete_single():
    single_pending = {"PASS": None, "recall": 0.90, "wrong_lane": 0,
                      "wrong_name": 0, "value_shape_acc": 1.0,
                      "state_acc": None, "would_park": 0.0}
    union_clean = {"PASS": True, "recall": 0.99, "wrong_lane": 0,
                   "wrong_name": 0, "value_shape_acc": 1.0,
                   "state_acc": 1.0, "would_park": 0.0}
    assert final_gate(single_pending, union_clean) is True


def test_definite_failures_never_none():
    dead = {"PASS": False, "recall": 0.5, "wrong_lane": 0, "wrong_name": 0,
            "value_shape_acc": 1.0, "state_acc": 1.0, "would_park": 0.0}
    assert final_gate(dead, None) is False
    q = "e" * 80
    gold = {"E1": [_gold_fact(q)]}
    assert score_arm(gold, _EMPTY_ARM, _META1, route=_route_for(_EMPTY_ARM))["PASS"] is False


def test_rule_bucket_actual_counts():
    r = _matched_pair(p_over={"level_shape_hint": "point"})
    # gold hint None vs produced 'point' -> a shapes-bucket mismatch COUNT
    assert r["error_table_by_rule"]["shapes"] >= 1
    r2 = _matched_pair(p_over={"driver_name": "fuel_cost"})
    assert r2["error_table_by_rule"]["other"] >= 1     # name = hard-gated, bucketed other
    from score_exp5 import _bucket
    assert _bucket("mismatch:level_shape_hint") == "shapes"
    assert _bucket("park:LEVEL_HINT_MISMATCH") == "shapes"
    assert _bucket("mismatch:measurement-OD-9") == "OD-9"
    assert _bucket("mismatch:value:level") == "OD-12"
    assert _bucket("park:HOME_FACT_MISSING") == "OD-21"


def test_presence_disagreement_uses_grader_decisions():
    """The metric must count VALID grader-ruled matches, not auto-links alone.

    RE-POINTED AT WHAT ACTUALLY NEEDS A RULING IN V2. The old fixture emitted
    the SAME fact twice and called it a "tie", because the retired candidate
    matcher treated two candidates for one gold as ambiguous. Under
    `record_key` two identical facts are exact DUPLICATES: they collapse, the
    survivor matches, and the gold is captured with no ruling at all — so that
    fixture could no longer distinguish the two states it was comparing.

    What genuinely needs a ruling now is a fact that DIFFERS from its gold: an
    auto-link requires an identical complete record, so the difference leaves it
    unmatched until a grader names the pair by index.
    """
    q = "p" * 80
    gold = {"E1": [_gold_fact(q, item=_mut_item(q))]}
    differing = {"E1": {"facts": [_v2_fact(q, fact_type="metric",
                                           item=_mut_item(q, sentinel_class="na"))]}}
    empty = {"E1": {"facts": []}}
    # With NO ruling an unmatched CANDIDATE still requires grading, so the
    # metric is INCOMPLETE — reporting a clean 0.0 here would be a made-up
    # number (Codex SEQ 1139.3).
    assert presence_disagreement(gold, differing, empty, _META1) is None
    # WITH a valid ruling run A captures it -> exactly-one/either = 1.0
    assert presence_disagreement(gold, differing, empty, _META1,
                                 resolutions_a={("E1", 0): 0}) == 1.0


def test_presence_disagreement_reports_0_for_a_truly_empty_answer():
    """The other side of SEQ 1139.3: with NO produced candidate there is nothing
    a grader could rule on, so 0.0 is a real answer, not a guess."""
    q = "p" * 80
    gold = {"E1": [_gold_fact(q, item=_mut_item(q))]}
    empty = {"E1": {"facts": []}}
    assert presence_disagreement(gold, empty, empty, _META1) == 0.0


# ---- #827 B1 packet 4 (SEQ 300/301): the oracle's NAME-17 home law -------

_SP4_SQ = "revenue beat consensus this quarter, the packet-4 surprise quote"
_SP4_HQ = "the matching home fact quote for the packet-4 pairing control"


def _sp4_surprise(basis):
    """Retired flat `lane` shape -> the adopted V2 fact. `lane` is carried
    explicitly to `fact_type`; the metric default would turn this surprise into
    a metric and quietly destroy the very pairing this control tests."""
    return _v2_fact(_SP4_SQ, fact_type="surprise", item=_v2_item(
        _SP4_SQ, driver_name="revenue_surprise", driver_state="beat",
        surprise_basis_hint=basis, comparison_baseline="consensus",
        fiscal_year=2026, fiscal_quarter=1, time_type="duration",
        level_low=None))          # `_v2_item` DEFAULTS a numeric slot; these
    #   packet-4 facts are NUMBERLESS, and letting the default stand gave them a
    #   value they never had (it showed up as park:NOT_STORABLE, not as a wrong
    #   answer, so it would have been easy to misread as an unrelated defect).


def _sp4_home(name, lane):
    # `company_confirmed` is REQUIRED on the guidance lane and FORBIDDEN
    # elsewhere — production owns that rule (`_lane_matrix`), and it is supplied
    # here rather than asserted, so the control still tests PAIRING and not a
    # lane-shape error. Measured: without it the guidance home is rejected LANE
    # and never becomes a candidate home at all.
    guidance_only = {"company_confirmed": True} if lane == "guidance" else {}
    return _v2_fact(_SP4_HQ, fact_type=lane, item=_v2_item(
        _SP4_HQ, driver_name=name, driver_state="unknown",
        fiscal_year=2026, fiscal_quarter=1, time_type="duration",
        level_low=None, **guidance_only))     # numberless, as above


def _sp4_arm(*facts):
    """ONE object, both routed and scored — building it twice would route one
    dict and score another, and the bijection check would fail for a reason
    these tests are not about."""
    return {"s1": {"facts": list(facts)}}


_SP4_META = {"s1": {"event_date": "2026-04-23", "fye_month": 12}}


def test_827B4_guidance_surprise_finds_its_guidance_home():
    """FINAL_DESIGN:153 — guidance-vs-consensus pairs with the GUIDANCE home
    (base + `_guidance`), never the metric. The oracle must not park a
    lawful pair as HOME_FACT_MISSING."""
    from score_exp5 import score_arm
    arm = _sp4_arm(_sp4_surprise("guidance"), _sp4_home("revenue_guidance", "guidance"))
    r = score_arm({"s1": []}, arm, _SP4_META, route=_route_for(arm))
    assert r["would_park"] == 0.0, r
    assert r["error_table_by_rule"]["OD-21"] == 0, r


@pytest.mark.parametrize("basis,home_name,home_lane",
                          [("actual", "fuel_cost", "metric"),
                           ("guidance", "revenue", "guidance")])
def test_827B4_false_homes_must_park_not_pair(basis, home_name, home_lane):
    """SEQ 304 A / 305 — a false home must PARK, never pair. Two separately
    collected rows; each must fail independently under the old-comparison and
    compat-fallback mutants.

    THE ACTUAL-BASIS CASE WAS NARROWED (Codex SEQ 1130). It used to give the
    metric home the name `revenue_surprise` — the SAME name as the surprise, on
    a different lane. That shape is IMPOSSIBLE: FINAL_DESIGN fixes a Driver's
    fact_type permanently and NAME-17 makes a terminal `_surprise` mean the
    surprise lane, so one reply can never lawfully hold `revenue_surprise` as
    both surprise and metric. The replay store's conflicting-type refusal — kept
    exactly as-is — now says so out loud.

    The retired same-name/two-type helper mutant is NOT preserved as law here.
    What survives is the real requirement: an actual-basis surprise whose only
    same-event home is an unrelated but otherwise lawful metric (a different
    family, `fuel_cost`) parks and is COUNTED. The guidance-basis false home,
    which reduces to bare `revenue` under the retired base-reduction, is
    unchanged and still proves the second path.
    """
    from score_exp5 import score_arm
    arm = _sp4_arm(_sp4_surprise(basis), _sp4_home(home_name, home_lane))
    r = score_arm({"s1": []}, arm, _SP4_META, route=_route_for(arm))
    assert r["would_park"] == 0.5, (basis, home_name, r)
    assert r["error_table_by_rule"]["OD-21"] == 1, (basis, home_name, r)
    # the EXACT public row, not just the rollup total (Codex SEQ 1130): the
    # surprise must PARK on the route's own no-matching-home code.
    assert r["route_codes"].get("park:F9") == 1, (basis, home_name,
                                                 r["route_codes"])


def test_827B4_actual_surprise_finds_its_metric_home():
    """The opposite twin: actual basis pairs with the base-name METRIC home."""
    from score_exp5 import score_arm
    arm = _sp4_arm(_sp4_surprise("actual"), _sp4_home("revenue", "metric"))
    r = score_arm({"s1": []}, arm, _SP4_META, route=_route_for(arm))
    assert r["would_park"] == 0.0, r
    assert r["error_table_by_rule"]["OD-21"] == 0, r



# ---- STEP 2 §1: RED-FIRST proofs of the active V1 defects ----
# Cases derive from the VERIFIED Step 1 receipt rows, not from a second
# hand-written defect list. Each refusal has a lawful control beside it.
# These are EXPECTED RED before the Step 2 fix and must go green after it.

def _v2_owner():
    from driver.core import prepared_fact_v2 as PF
    from driver.core import slot_convert as SC
    return PF, SC


def _step1_rows(step):
    receipt = os.path.join(_HERE, "step1_inventory.json")
    with open(receipt, encoding="utf-8") as fh:
        d = json.load(fh)
    return [r for r in d["behavior_families"]["rows"] if r["later_step"] == step]


def test_step1_receipt_is_the_case_source():
    """Control: the rows this section derives from are present and frozen."""
    rows = _step1_rows(2)
    assert len(rows) == 14, f"expected the 14 frozen Step 2 rows, got {len(rows)}"
    assert {r["id"] for r in rows} >= {"B-01", "B-02", "B-23"}


# ---- Step-2-only LAWFUL V2 REPLY FIXTURE ----
# Derived entirely from the committed Core V2 owners. The older _doc/_fact
# helpers above are the Step-3-era gold shape and are deliberately NOT changed.

def _v2_slot(quote, evidence=None, value=726, mult=1):
    """Exactly slot_convert.SLOT_KEYS. Values are exact JSON numbers, which is
    what the slot owner accepts (a string is rejected: int/Decimal only).
    Evidence is quote-local by default."""
    from driver.core.slot_convert import SLOT_KEYS
    ev = evidence if evidence is not None else quote[:12]
    slot = {"value": value, "scale_multiplier": mult, "unit_scale_evidence": ev}
    assert set(slot) == set(SLOT_KEYS)
    return slot


def _v2_item(quote, **over):
    """Exactly PreparedFactV2.ITEM_FIELDS; numeric slots are slot objects."""
    from driver.core.prepared_fact_v2 import ITEM_FIELDS, NUMERIC_SLOTS
    item = {k: None for k in ITEM_FIELDS}
    item.update({"driver_name": "revenue", "driver_state": "reported",
                 "quote": quote, "measurement_raw_spans": [], "slice_parts": []})
    item["level_low"] = _v2_slot(quote)
    assert set(item) == set(ITEM_FIELDS)
    assert set(NUMERIC_SLOTS) <= set(ITEM_FIELDS)
    item.update(over)
    return item


def _v2_fact(quote=None, **over):
    """Exactly PreparedFactV2._FACT_KEYS — no gold wrapper, no outer quote."""
    from driver.core.prepared_fact_v2 import PreparedFactV2 as P
    # The caller's quote used to be SILENTLY DISCARDED here: the parameter was
    # immediately overwritten by the default locator, so a test that passed a
    # quote from a different event got the default event's locator and failed
    # for a reason that had nothing to do with what it was testing.
    default_quote, part_ref, occ = _v2_locator()
    quote = default_quote if quote is None else quote
    f = {"fact_type": "metric", "part_ref": part_ref,
         "occurrence_in_part": occ, "per_x": None, "item": _v2_item(quote)}
    assert set(f) == set(P._FACT_KEYS)
    f.update(over)
    return f


def _v2_lint(doc, source_id=None):
    """Drive the MODEL/READER door directly; returns the checker's errors."""
    errs = []
    LNT.lint_v2_reply(doc, errs, INPUTS, source_id)
    return errs


def _v2_doc(facts, abstentions=None, source_id=None):
    """Exactly driver_write_cli.V2_REPLY_KEYS."""
    from driver.core.driver_write_cli import V2_REPLY_KEYS
    d = {"source_id": source_id or SID, "facts": facts,
         "abstentions": abstentions or []}
    assert set(d) == set(V2_REPLY_KEYS)
    return d


def _match_with_positions(gold, produced):
    """`match_facts` plus the INDEX PAIRS its links correspond to.

    `match_facts` returns the SAME instances it was given, so `id(instance) ->
    original index` is the only lawful position recovery (Codex SEQ 1108).
    Equality, `list.index`, `record_key`, the locator, and any value/quote logic
    are all forbidden here: each of them can map two genuinely distinct records
    onto one position, which is exactly the mis-attribution the matcher exists
    to prevent.

    Returns the real MatchResult with an added `.pairs` view, so every other
    field (`to_grading_gold`, `produced_duplicates`, ...) stays visible.
    """
    from driver.core.fact_match import match_facts
    from driver.core.prepared_fact_v2 import PreparedFactV2

    def _built(records):
        built, position = [], {}
        for i, rec in enumerate(records):
            obj = PreparedFactV2.from_dict(rec)
            position[id(obj)] = i
            built.append(obj)
        return built, position

    g_objs, g_pos = _built(gold)
    p_objs, p_pos = _built(produced)
    result = match_facts(g_objs, p_objs)
    result.pairs = [(g_pos[id(g)], p_pos[id(pr)]) for g, pr in result.links]
    return result


def _v2_locator():
    """A LAWFUL V2 locator: quote, part_ref and occurrence_in_part all come from
    the SAME text_parts[] entry. event_text() joins parts, so a slice of it can
    span a join boundary and belong to no part at all."""
    with open(os.path.join(INPUTS, SID + ".json"), encoding="utf-8") as fh:
        parts = json.load(fh)["text_parts"]
    part = max(parts, key=lambda x: len(x["content"]))
    quote = part["content"][:100]
    assert quote in part["content"]
    n = part["content"].count(quote)
    return quote, part["part"], (None if n == 1 else 1)


# ---- STEP 2 §1: RED-FIRST proofs, driven through the real checker ----

def test_CONTROL_step3_era_fixture_still_lawful_today(tmp_path):
    """Untouched baseline: the pre-existing gold-shaped document the Step-3-era
    tests rely on still lints clean. Guards against collateral damage."""
    assert _lint(tmp_path, [_doc([_fact()])]) == 0


def test_RED_lawful_v2_reply_is_refused(tmp_path):
    """B-01/B-02/B-04/B-06a: the exact V2 reply envelope must be ACCEPTED.

    Today the checker refuses it: its document key set omits abstentions and its
    fact key set omits part_ref, occurrence_in_part, per_x and item."""
    q, _pr, _oc = _v2_locator()
    assert _v2_lint(_v2_doc([_v2_fact(q)])) == [], (
        "model door REFUSED the exact V2 reply envelope")


def test_RED_v2_fact_missing_a_core_fact_level_key_is_accepted(tmp_path):
    """B-02/B-04/B-06a mutation: drop one Core fact-level key and require
    refusal. Blocked behind the envelope fix above."""
    from driver.core.prepared_fact_v2 import PreparedFactV2 as P
    q, _pr, _oc = _v2_locator()
    f = _v2_fact(q)
    f.pop("per_x")
    assert set(f) != set(P._FACT_KEYS)
    assert _v2_lint(_v2_doc([f])), (
        "model door ACCEPTED a V2 fact missing a Core fact-level key")


def test_CONTROL_source_owned_field_in_the_v2_item_is_refused(tmp_path):
    """B-05 RETAINED control (not a RED): ITEM_FIELDS is built as
    `k not in SOURCE_OWNED_FIELDS` (prepared_fact_v2.py:445-446), so deriving
    the item surface from the owner PRESERVES this refusal. Injected into the
    V2 fact's item, beside the lawful V2 control above."""
    from driver.core.prepared_fact_v2 import SOURCE_OWNED_FIELDS, ITEM_FIELDS
    assert not (set(SOURCE_OWNED_FIELDS) & set(ITEM_FIELDS))
    q, _pr, _oc = _v2_locator()
    f = _v2_fact(q)
    f["item"][sorted(SOURCE_OWNED_FIELDS)[0]] = [{"axis": "a", "member": "m"}]
    assert _v2_lint(_v2_doc([f]))


def test_RED_flat_number_in_a_numeric_slot_is_accepted(tmp_path):
    """B-03: a populated numeric slot is a slot_convert object, not a scalar."""
    q, _pr, _oc = _v2_locator()
    f = _v2_fact(q)
    f["item"]["level_low"] = 726                      # the OLD scalar form
    assert _v2_lint(_v2_doc([f])), (
        "model door ACCEPTED the old scalar form in a numeric slot")


def test_RED_lawful_nested_slot_is_refused(tmp_path):
    """B-06b lawful control, currently PRESERVED RED behind B-03.

    A populated slot with quote-local evidence must be ACCEPTED. Until the slot
    structure is honoured this fails on the scalar rule, which is why the
    outside-quote refusal below cannot yet authorize its own rule."""
    q, _pr, _oc = _v2_locator()
    assert _v2_lint(_v2_doc([_v2_fact(q)])) == [], (
        "model door REFUSED a lawful nested slot with quote-local evidence")


def test_RED_nested_evidence_outside_the_quote_is_accepted(tmp_path):
    """B-06b refusal: change ONLY the nested evidence to text absent from the
    fact's quote. Valid only once the control above is green."""
    q, _pr, _oc = _v2_locator()
    f = _v2_fact(q)
    f["item"]["level_low"] = _v2_slot(q, evidence="ZZ_NOT_IN_THE_QUOTE_ZZ")
    assert "ZZ_NOT_IN_THE_QUOTE_ZZ" not in q
    assert _v2_lint(_v2_doc([f]))


def test_RED_model_reply_carrying_a_gold_only_field_is_accepted(tmp_path):
    """B-09: gold-only review fields stay SEPARATE from the model reply.

    One-field mutation of the lawful V2 reply: add the WorkOrder-owned review
    field du_worthy at fact level and require model-door refusal."""
    from driver.core.prepared_fact_v2 import PreparedFactV2 as P, ITEM_FIELDS
    from driver.core.driver_write_cli import V2_REPLY_KEYS
    name = "du_worthy"
    assert name not in set(P._FACT_KEYS) | set(ITEM_FIELDS) | set(V2_REPLY_KEYS)
    q, _pr, _oc = _v2_locator()
    f = _v2_fact(q)
    f[name] = True
    assert _v2_lint(_v2_doc([f])), (
        "model door ACCEPTED a model reply carrying a gold-only review field")


def test_CONTROL_gold_document_surface_accepts_the_review_field(tmp_path):
    """B-09 converse, proved by REUSING the existing real gold-document
    acceptance path (test_lint_passes_valid_doc, line 176) rather than by
    asserting set membership: the same review field that the MODEL door must
    refuse is accepted on the GOLD surface."""
    f = _fact(du_worthy=True)
    assert "du_worthy" in f
    assert _lint(tmp_path, [_doc([f])]) == 0
    from driver.core.prepared_fact_v2 import PreparedFactV2 as P, ITEM_FIELDS
    from driver.core.driver_write_cli import V2_REPLY_KEYS
    assert "du_worthy" not in (set(P._FACT_KEYS) | set(ITEM_FIELDS)
                               | set(V2_REPLY_KEYS))



def test_CONTROL_v2_owner_names_are_accepted():
    from driver.core.prepared_fact_v2 import NUMERIC_SLOTS, ITEM_FIELDS
    assert set(NUMERIC_SLOTS) <= set(ITEM_FIELDS)


def test_RED_checker_binds_the_v1_schema_owner():
    """B-23 root cause."""
    src = open(os.path.join(_HERE, "kf_lint.py"), encoding="utf-8").read()
    assert "PreparedFactV1" not in src


def test_RED_contract_builder_reads_archived_authority():
    """B-08 owner/dependency row, asserted on the authority the builder actually
    RESOLVES (the manifest it emits) rather than on its prose: a source-string
    check cannot tell an archived read from a sentence recording that the
    archived topology was deleted, so it fails green in both directions."""
    import tempfile
    import build_exp5_contract as BEC
    with tempfile.TemporaryDirectory() as d:
        BEC.build(d)
        blocks = json.load(open(os.path.join(
            d, "exp5_prompt_contract.manifest.json")))["blocks"]
    assert blocks, "the builder resolved no authority at all"
    for b in blocks:
        real = os.path.realpath(os.path.join(BEC._REPO, b["source"]))
        assert os.path.isfile(real), f"authority does not exist: {b['source']}"
        assert "archive" not in real.lower().split(os.sep), f"archived: {real}"
        assert os.path.basename(real) != "15_CandidateFactPacket.md"


def test_RED_contract_builder_refuses_a_pin_that_is_not_exactly_one_place():
    """B-08: the deleted topology failed by silently serving the wrong text
    after its owners moved. A pin resolving to zero OR to many places must be a
    hard failure, never a quiet first-match."""
    import tempfile
    import build_exp5_contract as BEC
    with pytest.raises(SystemExit):                       # zero
        BEC._section(BEC._PKG, "### a heading no live owner declares")
    with tempfile.TemporaryDirectory() as d:              # many
        dup = os.path.join(d, "dup.md")
        with open(dup, "w", encoding="utf-8") as fh:
            fh.write("## H\nfirst\n## H\nsecond\n")
        with pytest.raises(SystemExit):
            BEC._section(dup, "## H")


# ---- B-07/B-08: the ASSEMBLED PROMPT, asserted over generated bytes ----
# Every check below drives the real builder and reads what it actually emits.
# Prose is compared whitespace-normalized because the authority hard-wraps its
# sentences: a line-sensitive check silently misses a wrapped phrase.

def _prompts(tmp_path):
    import build_exp5_contract as BEC
    BEC.build(str(tmp_path))
    out = {}
    for role in BEC.role_prompt_headers():
        raw = open(os.path.join(str(tmp_path), f"exp5_prompt_{role}.md"),
                   encoding="utf-8").read()
        out[role] = (raw, re.sub(r"\s+", " ", raw))
    assert out, "the builder emitted no prompt at all"
    return out


def _role_body(raw):
    """The [ROLE] section only — the one authorized per-role difference."""
    lines = raw.splitlines()
    s = lines.index("[ROLE]")
    e = next(i for i in range(s + 1, len(lines)) if lines[i].startswith("["))
    return lines[s + 1:e]




@pytest.mark.parametrize("surface,old,new", [
    ("reply envelope",  '{"source_id":', '{"retired_top": "<x>", "source_id":'),
    ("reply envelope",  '\n "abstentions": [', '\n "gone_abstentions": ['),
    ("fact keys",       '{"fact_type":', '{"retired_fact_key": "<x>", "fact_type":'),
    ("fact keys",       '"per_x": "<stated denominator', '"gone_per_x": "<stated denominator'),
    ("item fields",     '"driver_name":', '"retired_item": "<x>",\n      "driver_name":'),
    ("item fields",     '"driver_name": "<string, Rule 3>",\n', ''),
    ("slot keys",       'scale_multiplier, unit_scale_evidence}',
                        'scale_multiplier, unit_scale_evidence, retired_key}'),
    # DROPPING a slot key trips slot DETECTION before the key comparison: the
    # field no longer carries the full Core marker, so it stops counting as a
    # slot at all. Labelled by the surface it actually breaks, not the one I
    # first assumed — the extra-key case above is what proves 'slot keys'.
    ("slot-spelling fields", '{value, scale_multiplier,', '{scale_multiplier,'),
    ("abstention keys", '{"quote": "<verbatim>", "reason"',
                        '{"retired_abst": "<x>", "quote": "<verbatim>", "reason"'),
    ("abstention keys", '"reason": "<short>",\n', ''),
    # A NON-FIRST numeric slot degraded to a scalar. The earlier form spelled the
    # slot shape once and back-referenced it, so only the FIELD NAME of the other
    # four was ever checked and this exact line would have passed.
    ("slot-spelling fields",
     '"level_high": "<null OR {value, scale_multiplier, unit_scale_evidence}>",',
     '"level_high": "<string>",'),
    ("slot-spelling fields",
     '"comparison_high": "<null OR {value, scale_multiplier, unit_scale_evidence}>",',
     '"comparison_high": "<number|null>",'),
    # A top-level key REMOVED, not renamed: must still reach and name a surface
    # rather than fall out as a generic malformed-envelope error.
    ("reply envelope", ',\n "abstentions": [\n   {"quote": "<verbatim>", "reason": "<short>",\n    "part_ref": "<the exact `part` label supplied for that text part>",\n    "occurrence_in_part": "<null when unique; else count>"}]}', '}'),
])
def test_every_copied_structural_surface_is_bound_to_core(tmp_path, surface, old,
                                                          new):
    """step2 §2, ONE schema owner — for the WHOLE answer shape, not just `item`.

    The skeleton is a COPY of structure Core owns, so every surface it restates
    must be refused when it drifts either way. Each case mutates exactly one
    surface in a temporary copy of the authority and requires a hard build
    failure naming that surface."""
    import build_exp5_contract as BEC
    live = open(BEC._PKG, encoding="utf-8").read()
    assert old in live, f"{surface}: mutation anchor absent — {old!r}"
    tampered = os.path.join(str(tmp_path), f"pkg_{abs(hash((surface, old)))}.md")
    with open(tampered, "w", encoding="utf-8") as fh:
        fh.write(live.replace(old, new, 1))
    keep = BEC._PKG
    BEC._PKG = tampered
    try:
        with pytest.raises(SystemExit) as e:
            BEC.build(str(tmp_path))
        msg = str(e.value)
        assert "SCHEMA DRIFT" in msg, f"{surface}: wrong refusal — {msg}"
        # It must reach and NAME the intended surface. Without this, a mutation
        # could fail via some unrelated surface and still look proven.
        assert f"{surface!r}" in msg, \
            f"expected drift in {surface!r}, got: {msg}"
    finally:
        BEC._PKG = keep


def test_prompt_builder_writes_into_a_nonexistent_out_dir(tmp_path):
    """The documented --out DIR contract: a directory that does not exist yet
    must be created before the first write, not after the last one."""
    import build_exp5_contract as BEC
    target = os.path.join(str(tmp_path), "does", "not", "exist")
    BEC.build(target)
    assert sorted(os.listdir(target)) == [
        "exp5_prompt_contract.manifest.json", "exp5_prompt_drafter.md",
        "exp5_prompt_producer.md"]


def test_prompt_roles_differ_only_in_the_role_header(tmp_path):
    """step2 §3: one builder, one envelope; only the WorkOrder-authorized role
    preamble may differ."""
    P = _prompts(tmp_path)
    assert len(P) >= 2, f"expected both drafter and producer, got {sorted(P)}"
    bodies = {r: _role_body(raw) for r, (raw, _) in P.items()}
    stripped = {r: raw.replace("\n".join(bodies[r]), "")
                for r, (raw, _) in P.items()}
    assert len(set(stripped.values())) == 1, \
        "the prompts differ OUTSIDE the role header"
    assert len(set(map(tuple, bodies.values()))) == len(bodies), \
        "the role headers are not actually distinct"


def test_prompt_carries_the_fact_gate_and_a_lawful_zero_fact_result(tmp_path):
    """step2 §4: emit every fact passing the official gate; abstain when
    evidence is insufficient; a zero-fact event stays lawful (§7)."""
    for role, (_, flat) in _prompts(tmp_path).items():
        assert "is it a fact?" in flat, role
        assert "Zero facts is a legal answer" in flat, role
        assert "abstain" in flat, role


def test_prompt_demands_every_field_and_forbids_invention(tmp_path):
    """step2 §4: fill every required field, null only where permitted, and
    never invent a value, unit, scale, period, slice, or expansion."""
    for role, (_, flat) in _prompts(tmp_path).items():
        assert "answering every field in the OUTPUT section explicitly" in flat, role
        assert "nstated means null" in flat, role
        assert "never invent" in flat.lower(), role


def test_prompt_makes_the_source_id_echo_a_wrong_event_guard(tmp_path):
    """step2 §4 / A3: source_id is echoed AS the wrong-event guard, not merely
    listed as a key."""
    from driver.core.driver_write_cli import V2_REPLY_KEYS
    for role, (_, flat) in _prompts(tmp_path).items():
        assert "wrong-event" in flat, f"{role}: echo is present but not as a guard"
        for k in V2_REPLY_KEYS:
            assert k in flat, f"{role}: envelope key {k!r} absent"


def test_prompt_demands_a_verbatim_quote_with_part_and_occurrence(tmp_path):
    """step2 §4: copy an exact quote, identify its exact source part, and use a
    per-part occurrence only when the quote repeats there."""
    for role, (_, flat) in _prompts(tmp_path).items():
        assert "VERBATIM" in flat, role
        # NOT "p01": this assertion used to require the invented positional
        # label and so protected the defect it was meant to catch. The locator
        # law is proven against the LIVE inputs in the three tests above.
        assert "part_ref" in flat, role
        assert "occurrence_in_part" in flat, role
        assert "null when unique" in flat, role


def _live_part_labels():
    """Every part label the FROZEN 36 events actually supply, read from the
    inputs themselves. Deliberately not a list in this file: a frozen label list
    would be the same invented vocabulary this test exists to forbid."""
    seen = {}
    for name in sorted(os.listdir(INPUTS)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(INPUTS, name), encoding="utf-8") as fh:
            for part in json.load(fh).get("text_parts", []):
                seen.setdefault(part["part"], (name[:-5], part))
    assert seen, "no part labels found in the frozen inputs"
    return seen


def test_prompt_locator_uses_the_events_own_part_label_not_an_invented_one(tmp_path):
    """The generated instructions must tell the reader to COPY the supplied
    `part` label, never to invent a positional one.

    The prompt used to say `part_ref` is "p01, p02, onward" — a positional label
    no event supplies, so a reader obeying it would cite a part that does not
    exist and a correct quote would carry a broken locator.

    THIS TEST BANS THE RETIRED INSTRUCTION, NOT A LABEL SHAPE. A future event may
    lawfully supply a part called `p01`; the only rule is to copy whatever label
    THIS event gives. Asserting that positional labels are inherently absent
    would replace one invented vocabulary with another."""
    retired = ("`p01`, `p02`, onward", "<p01, p02, onward>")
    for role, (_, flat) in _prompts(tmp_path).items():
        for phrase in retired:
            assert phrase not in flat, \
                f"{role}: the retired positional instruction {phrase!r} survives"
        assert "copy the EXACT `part` label" in flat, \
            f"{role}: no instruction to copy the supplied part label"


def test_every_live_part_label_is_a_lawful_locator(tmp_path):
    """The lawful control, driven through the REAL checker over the REAL inputs:
    every part label the corpus actually uses must lint clean — including the
    ones that look nothing like `pNN`."""
    from driver.core.prepared_fact_v2 import ITEM_FIELDS      # noqa: F401
    live = _live_part_labels()
    for label, (sid, part) in sorted(live.items()):
        quote = part["content"][:100]
        n = part["content"].count(quote)
        fact = _v2_fact(quote)
        fact["part_ref"] = label
        fact["occurrence_in_part"] = None if n == 1 else 1
        errs = _v2_lint(_v2_doc([fact], source_id=sid), source_id=sid)
        assert errs == [], f"lawful part label {label!r} was REFUSED: {errs}"


def test_a_wrong_part_label_is_still_refused(tmp_path):
    """The refusal that must survive: citing a part the event does not contain
    is still an error. Removing the invented pNN grammar must not remove this."""
    live = _live_part_labels()
    label, (sid, part) = sorted(live.items())[0]
    quote = part["content"][:100]
    fact = _v2_fact(quote)
    fact["part_ref"] = label + "_not_a_real_part"
    fact["occurrence_in_part"] = None
    errs = _v2_lint(_v2_doc([fact], source_id=sid), source_id=sid)
    assert errs, "a nonexistent part label was ACCEPTED"


def test_prompt_one_envelope_with_gold_fields_attached_afterward(tmp_path):
    """step2 §7: both roles share the envelope; gold-only review fields are
    attached AFTERWARD, so exactly one model-output format exists."""
    P = _prompts(tmp_path)
    for role, (_, flat) in P.items():
        assert "attached AFTERWARD" in flat, role
        assert "exactly one model-output format exists" in flat, role
    outputs = {r: raw.split("[OUTPUT]")[1].split("[BOUNDARY]")[0]
               for r, (raw, _) in P.items()}
    assert len(set(outputs.values())) == 1, "the OUTPUT envelope differs by role"


def test_prompt_grants_no_file_access_gold_future_or_target_count(tmp_path):
    """step2 §3/§7: the prompt contains no model name, gold answer, future
    information, file-access instruction, other drafter, or target fact count."""
    banned = {
        "file access": r"(?i)\bread the file|\bopen the file|file path|\.json\b",
        "model name": r"(?i)\b(claude|gpt|opus|sonnet|haiku|fable|gemini)\b",
        "other drafter": r"(?i)other drafter|another drafter",
        "target count": r"(?i)you should (?:find|emit) \d+|expect \d+ facts",
        "realized return": r"(?i)realized return|stock (?:move|price) after",
    }
    for role, (_, flat) in _prompts(tmp_path).items():
        for what, pat in banned.items():
            hits = re.findall(pat, flat)
            assert not hits, f"{role}: prompt leaks {what}: {hits[:3]}"


def test_prompt_ends_with_the_event_after_the_untrusted_boundary(tmp_path):
    """step2 §4 / Part A order: the untrusted-evidence boundary sits between
    OUTPUT and the event, and the event placeholder is ALWAYS last."""
    import build_exp5_contract as BEC
    for role, (raw, flat) in _prompts(tmp_path).items():
        order = [l for l in raw.splitlines() if re.fullmatch(r"\[[A-Z]+\]", l)]
        assert order == ["[ROLE]", "[RULES]", "[OUTPUT]", "[BOUNDARY]",
                         "[EVENT]"], f"{role}: wrong order {order}"
        assert "UNTRUSTED SOURCE EVIDENCE" in flat, role
        assert raw.rstrip().endswith(BEC.EVENT_PLACEHOLDER), \
            f"{role}: something follows the event placeholder"


def test_prompt_is_text_only_and_names_xbrl_only_as_forbidden(tmp_path):
    """step2 §5: EXP-5 is text-only. The prompt may state that the source-owned
    XBRL fields are forbidden; it must never teach how an XBRL fact is built."""
    from driver.core.prepared_fact_v2 import SOURCE_OWNED_FIELDS
    for role, (raw, flat) in _prompts(tmp_path).items():
        for name in SOURCE_OWNED_FIELDS:
            assert name in flat, f"{role}: {name} not named as forbidden"
        hits = [l for l in raw.splitlines()
                if re.search(r"(?i)xbrl|member_refs|dimension", l)]
        assert len(hits) == 1, f"{role}: XBRL discussed on {len(hits)} lines"
        assert "NEVER emit" in hits[0], f"{role}: XBRL line is not a prohibition"


def test_CONTROL_door_scoped_field_remains_lawful_reader_output():
    """B-22."""
    import re as _re
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    from driver.core import prepared_fact as V1
    ct = open(os.path.join(_HERE, "..", "..", "FinalDesign",
                           "ChannelContractV2.md"), encoding="utf-8").read()
    surf = json.loads(_re.search(r"```json CONTRACT-SURFACES\n(.*?)\n```",
                                 ct, _re.S).group(1))
    door = set(surf["staged_raw_channel"]["retired_fiscal_fields"])
    door_only = door - (set(V1.PreparedFactV1.FIELDS) - set(ITEM_FIELDS))
    assert door_only
    for name in door_only:
        assert name in ITEM_FIELDS


def test_RED_wrong_part_ref_is_accepted(tmp_path):
    """Locator: part_ref must name a real part of THIS event."""
    q, pr, oc = _v2_locator()
    f = _v2_fact(q); f["part_ref"] = "no_such_part"
    assert _v2_lint(_v2_doc([f])), "model door ACCEPTED an unknown part_ref"


def test_RED_wrong_occurrence_index_is_accepted(tmp_path):
    """Locator: occurrence_in_part must be exact; null only when unique."""
    q, pr, oc = _v2_locator()
    f = _v2_fact(q); f["occurrence_in_part"] = 7
    assert _v2_lint(_v2_doc([f])), "model door ACCEPTED a wrong occurrence index"


def test_CONTROL_lawful_locator_is_accepted(tmp_path):
    """Lawful control beside both locator refusals."""
    q, pr, oc = _v2_locator()
    assert _v2_lint(_v2_doc([_v2_fact(q)])) == []


def test_RED_extra_envelope_key_is_accepted(tmp_path):
    """Envelope: exactly V2_REPLY_KEYS."""
    q, pr, oc = _v2_locator()
    d = _v2_doc([_v2_fact(q)]); d["extra"] = 1
    assert _v2_lint(d), "model door ACCEPTED an extra envelope key"


def test_RED_malformed_abstention_is_accepted(tmp_path):
    """Abstention shape: exactly quote, reason, part_ref, occurrence_in_part."""
    q, pr, oc = _v2_locator()
    d = _v2_doc([], abstentions=[{"quote": q, "reason": "insufficient"}])
    assert _v2_lint(d), "model door ACCEPTED an abstention missing keys"


def test_CONTROL_lawful_abstention_is_accepted(tmp_path):
    """Lawful control for the abstention shape."""
    q, pr, oc = _v2_locator()
    d = _v2_doc([], abstentions=[{"quote": q, "reason": "insufficient evidence",
                                  "part_ref": pr, "occurrence_in_part": oc}])
    assert _v2_lint(d) == []


def _second_pinned_sid():
    """A DIFFERENT but equally valid pinned event id."""
    with open(os.path.join(_HERE, "launch_kfields_drafts.manifest.json"),
              encoding="utf-8") as fh:
        ids = [e["source_id"] for e in json.load(fh)["events"]]
    other = [s for s in ids if s != SID]
    assert other, "expected more than one pinned event"
    return other[0]


def test_CONTROL_source_echo_matches_the_trusted_id():
    """Lawful control: the reply names the event the caller expected."""
    q, pr, oc = _v2_locator()
    errs = []
    LNT.lint_v2_reply(_v2_doc([_v2_fact(q)]), errs, INPUTS,
                      expected_source_id=SID)
    assert errs == []


def test_RED_reply_naming_a_different_valid_event_is_accepted():
    """The echo must be PROVEN, not implied: a reply naming a DIFFERENT but
    valid pinned event must be refused before any part is loaded."""
    q, pr, oc = _v2_locator()
    other = _second_pinned_sid()
    d = _v2_doc([_v2_fact(q)])
    d["source_id"] = other                       # a real, loadable event
    errs = []
    LNT.lint_v2_reply(d, errs, INPUTS, expected_source_id=SID)
    assert errs, ("model door ACCEPTED a reply echoing a different valid event "
                  f"({other} instead of {SID})")


def _gold_fact(quote, item=None, **over):
    """A stored gold fact: the EXACT V2 fact plus only the three review fields.

    This is the ADOPTED gold shape and the only one the scorer accepts — the
    retired `lane` / `gold_item` wrapper is not a variant of it. Overrides go to
    the V2 fact or the review fields; nothing here restates a schema.
    """
    f = _v2_fact(quote, **({"item": item} if item is not None else {}))
    f.update({"du_worthy": True,
              "gold_extra": {"expectation_comparison_present": False},
              "ambiguity_note": None})
    f.update({k: v for k, v in over.items()
              if k in ("du_worthy", "gold_extra", "ambiguity_note",
                       "fact_type", "part_ref", "occurrence_in_part", "per_x")})
    return f


def _gold_lint(doc):
    errs = []
    LNT.lint_doc(doc, errs, INPUTS)
    return errs


def test_CONVERSE_1_lawful_v2_fact_accepted_as_raw_model_output():
    """B-09 step 1: the plain V2 fact passes the MODEL door."""
    q, pr, oc = _v2_locator()
    assert _v2_lint(_v2_doc([_v2_fact(q)])) == []


def test_CONVERSE_2_one_review_field_makes_the_model_door_refuse():
    """B-09 step 2: adding a single gold review field must be refused there."""
    q, pr, oc = _v2_locator()
    f = _v2_fact(q); f["du_worthy"] = True
    assert _v2_lint(_v2_doc([f])), "model door ACCEPTED a gold review field"


def test_CONVERSE_3_adjudicated_door_accepts_the_three_review_fields():
    """B-09 step 3: with exactly the three review fields attached, the
    adjudicated-key door accepts the same underlying fact."""
    q, pr, oc = _v2_locator()
    assert _gold_lint(_v2_doc([_gold_fact(q)])) == []


def test_RED_old_gold_item_wrapper_is_refused():
    """The retired wrapper must not be accepted anywhere."""
    q, pr, oc = _v2_locator()
    f = _gold_fact(q); f["gold_item"] = f.pop("item")
    assert _gold_lint(_v2_doc([f])), "adjudicated door ACCEPTED the gold_item wrapper"


def test_RED_duplicate_outer_quote_is_refused():
    """The quote lives at item.quote; a duplicate outer quote is refused."""
    q, pr, oc = _v2_locator()
    f = _gold_fact(q); f["quote"] = q
    assert _gold_lint(_v2_doc([f])), "adjudicated door ACCEPTED a duplicate outer quote"


def test_RED_gold_fact_missing_per_x_is_refused():
    """A missing Core fact key is refused on the gold side too."""
    q, pr, oc = _v2_locator()
    f = _gold_fact(q); f.pop("per_x")
    assert _gold_lint(_v2_doc([f])), "adjudicated door ACCEPTED a fact missing per_x"


def test_RED_gold_fact_with_bad_locator_is_refused():
    """The locator law is Core's, reached through the same delegation."""
    q, pr, oc = _v2_locator()
    f = _gold_fact(q); f["part_ref"] = "no_such_part"
    assert _gold_lint(_v2_doc([f])), "adjudicated door ACCEPTED a bad locator"


@pytest.mark.parametrize("val", [True, False])
def test_CONTROL_gold_extra_lawful_both_booleans(val):
    """WorkOrder:420 — exactly one key, boolean. Both values are lawful."""
    q, pr, oc = _v2_locator()
    f = _gold_fact(q)
    f["gold_extra"] = {"expectation_comparison_present": val}
    assert _gold_lint(_v2_doc([f])) == []


@pytest.mark.parametrize("bad", [
    {},                                              # missing the key
    {"expectation_comparison_present": True, "x": 1},  # extra key
    {"expectation_comparison_present": "yes"},       # wrong type
    {"other": True},                                 # wrong key
    [],                                              # not an object
])
def test_RED_gold_extra_off_shape_is_refused(bad):
    """The frozen review shape is enforced, not merely 'some dict'."""
    q, pr, oc = _v2_locator()
    f = _gold_fact(q)
    f["gold_extra"] = bad
    assert _gold_lint(_v2_doc([f])), f"adjudicated door ACCEPTED gold_extra={bad!r}"


# ---- Step 2 §9: the remaining boundary classes ----

@pytest.mark.parametrize("bad", ["a string", 7, None, {}])
def test_RED_wrong_container_for_facts_is_refused(bad):
    """§9 wrong container: `facts` must be a LIST. An empty list is NOT here —
    a zero-fact reply is lawful (Step 2 §7) and is proven by the control below."""
    q, pr, oc = _v2_locator()
    d = _v2_doc([_v2_fact(q)]); d["facts"] = bad
    assert _v2_lint(d), f"model door ACCEPTED facts={bad!r}"


def test_CONTROL_lawful_zero_fact_reply_is_accepted():
    """Step 2 §7: a lawful zero-fact event must stay lawful."""
    assert _v2_lint(_v2_doc([])) == []


@pytest.mark.parametrize("bad2", [[], "s", 7])
def test_RED_wrong_container_for_a_fact_is_refused(bad2):
    """§9 wrong container: each fact must be an object."""
    q, pr, oc = _v2_locator()
    assert _v2_lint(_v2_doc([bad2])), f"model door ACCEPTED a fact of {type(bad2).__name__}"


def test_RED_fabricated_quote_is_refused():
    """§9 fabricated quote: a quote absent from the named part must refuse."""
    q, pr, oc = _v2_locator()
    f = _v2_fact(q)
    f["item"]["quote"] = "THIS SENTENCE IS NOT IN THE FILING AT ALL"
    assert _v2_lint(_v2_doc([f])), "model door ACCEPTED a fabricated quote"


def test_RED_same_quote_in_two_parts_needs_the_right_part():
    """§9 same quote in two different parts: the locator must name the part the
    quote is actually taken from, so a quote unique to part A cited against
    part B is refused."""
    with open(os.path.join(INPUTS, SID + ".json"), encoding="utf-8") as fh:
        parts = json.load(fh)["text_parts"]
    big = max(parts, key=lambda x: len(x["content"]))
    other = [p for p in parts if p["part"] != big["part"]][0]
    q = big["content"][:100]
    assert q not in other["content"], "precondition: the quote is unique to one part"
    f = _v2_fact(q); f["part_ref"] = other["part"]
    assert _v2_lint(_v2_doc([f])), "model door ACCEPTED a quote cited against the wrong part"


def test_CONTROL_instruction_like_source_text_stays_evidence():
    """§9 prompt-injection: instruction-like text inside the SOURCE is evidence,
    never an instruction. A lawful quote containing imperative wording is
    accepted exactly like any other quote."""
    with open(os.path.join(INPUTS, SID + ".json"), encoding="utf-8") as fh:
        parts = json.load(fh)["text_parts"]
    big = max(parts, key=lambda x: len(x["content"]))
    q = big["content"][:100]
    f = _v2_fact(q)
    assert _v2_lint(_v2_doc([f])) == []
    # the checker must not treat any source wording as a directive to itself
    assert "ignore" not in repr(_v2_lint(_v2_doc([f])))


def test_RED_schema_owner_drift_breaks_the_generated_card():
    """§9 schema-owner drift: the generated structural card is derived from the
    Core owners, so a drifted owner must change the card rather than be
    silently tolerated."""
    import build_exp5_contract as BEC
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    card = BEC.core_structure_card()
    for name in ITEM_FIELDS:
        assert name in card, f"generated card omits the Core item field {name!r}"
    assert str(len(ITEM_FIELDS)) in card


# ---- the three period proofs with no exact Core survivor (Codex SEQ 1062.2) ----
# Preserved HERE, at the public V2 door, because no single Core test proves them.
# Each drives the real checker and must refuse or accept without a raw exception.

def test_CONTROL_lawful_far_future_fiscal_year_2150_is_accepted():
    """No exact Core survivor: a lawful, far-future fiscal year must still pass
    the public door rather than be rejected by an invented range rule."""
    q, pr, oc = _v2_locator()
    f = _v2_fact(q)
    f["item"]["fiscal_year"] = 2150
    errs = _v2_lint(_v2_doc([f]))
    assert errs == [], f"public door REFUSED a lawful year 2150: {errs}"


def test_RED_fractional_fiscal_year_is_refused_without_a_raw_exception():
    """No exact Core survivor: a non-integer fiscal year must refuse cleanly."""
    q, pr, oc = _v2_locator()
    f = _v2_fact(q)
    f["item"]["fiscal_year"] = 2024.5
    errs = _v2_lint(_v2_doc([f]))          # must not raise
    assert errs, "public door ACCEPTED a fractional fiscal year"


def test_RED_dict_period_scope_is_refused_without_a_raw_exception():
    """No exact Core survivor: a container where a scalar scope is required must
    refuse cleanly rather than crash on an unhashable value."""
    q, pr, oc = _v2_locator()
    f = _v2_fact(q)
    f["item"]["period_scope"] = {"ytd": True}
    errs = _v2_lint(_v2_doc([f]))          # must not raise
    assert errs, "public door ACCEPTED a dict period_scope"


# ---- the meta-proof: this suite touched NO frozen file ----

def test_zz_frozen_untouched():
    assert _frozen_state() == FROZEN_BEFORE


# ---- STEP 3: REPOINT-THEN-DELETE (the obligation Step 2 handed forward) ----

_OLD_CARD = ("exp5_item_contract.md", "exp5_item_contract.manifest.json")


def _code_files():
    """Every executable/config file that could still CALL the retired card.
    Prose files are excluded: history may name a deleted artefact, code may not.
    """
    roots = [os.path.join(_REPO, ".claude", "plans", "Drivers")]
    out = []
    for root in roots:
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d not in
                       (".git", "archive", "receipts_827", "__pycache__")]
            for n in names:
                if not n.endswith((".py", ".js", ".json")) or n.startswith("16_"):
                    continue
                full = os.path.join(base, n)
                # THIS file names the retired artefacts in _OLD_CARD, so scanning
                # it would match the scanner's own definition and never go green.
                if os.path.realpath(full) == os.path.realpath(__file__):
                    continue
                out.append(full)
    assert out, "no code files found to scan"
    return out


def test_step3_no_code_still_calls_the_retired_contract_card():
    """Step 3 obligation: every real caller and pin must point at the two role
    prompts plus the one new manifest. Proven over CODE, not over prose."""
    offenders = {}
    for path in _code_files():
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        hits = [n for n in _OLD_CARD if n in text]
        if hits:
            offenders[os.path.relpath(path, _REPO)] = hits
    assert not offenders, (
        "code still references the retired contract card:\n  "
        + "\n  ".join(f"{k}: {v}" for k, v in sorted(offenders.items())))


# ---- STEP 3 §7 / B-14: the recorded-answer replay projection ----

def test_RED_replay_projection_exists_and_is_lossless():
    """B-14: one synthetic raw item per emitted fact AND per abstention, in
    emitted order (facts first), keeping the exact
    (kind, original_index) -> synthetic_index map, and copying each record's
    quote into BOTH `quote` and `raw_label_or_claim` without deriving anything.

    RED FIRST: the projection does not exist yet. It is asserted here before it
    is written so the mapping law is fixed by a test rather than by the
    implementation that happens to get written."""
    from scorers import score_exp5
    project = getattr(score_exp5, "project_replay_items", None)
    assert project is not None, "score_exp5 owns no replay projection yet"
    reply = {"source_id": "E1",
             "facts": [{"item": {"quote": "alpha"}}, {"item": {"quote": "beta"}}],
             "abstentions": [{"quote": "gamma"}]}
    items, index_map = project(reply)
    assert [i["quote"] for i in items] == ["alpha", "beta", "gamma"], \
        "facts must come first, each in emitted order, then abstentions"
    for it in items:
        assert it["raw_label_or_claim"] == it["quote"], \
            "the quote is copied verbatim into both fields, never derived"
    assert index_map == {("fact", 0): 0, ("fact", 1): 1, ("abstention", 0): 2}


def test_RED_replay_projection_keeps_duplicates_and_empty_answers_honest():
    """Duplicate locators stay SEPARATE positions — collapsing them in the
    adapter would hide exactly what Core/accounting is meant to report — and a
    lawful zero-fact answer projects to zero items rather than a fabricated
    abstention."""
    from scorers import score_exp5
    project = getattr(score_exp5, "project_replay_items", None)
    assert project is not None, "score_exp5 owns no replay projection yet"
    dup = {"source_id": "E1",
           "facts": [{"item": {"quote": "same"}}, {"item": {"quote": "same"}}],
           "abstentions": []}
    items, index_map = project(dup)
    assert len(items) == 2 and len(index_map) == 2, "duplicates were collapsed"
    empty, empty_map = project({"source_id": "E1", "facts": [], "abstentions": []})
    assert empty == [] and empty_map == {}, "an empty answer must project to zero items"


def test_replay_returns_each_record_once_in_order_and_never_calls_a_model():
    """The preloaded callback: the ONE captured whole-event answer is replayed
    item by item, in the projection's deterministic order, and the model is never
    consulted again. A second call for the same position, or any call beyond the
    projected count, is a defect — so both are counted, not assumed."""
    from scorers.score_exp5 import project_replay_items
    reply = {"source_id": "E1",
             "facts": [{"item": {"quote": "alpha"}}, {"item": {"quote": "beta"}}],
             "abstentions": [{"quote": "gamma"}]}
    items, index_map = project_replay_items(reply)
    served, calls = [], {"n": 0}

    def recorded_reader(**kw):
        """Stands where run_event's `reader=` callback stands: returns only the
        record for this position, from the ALREADY-CAPTURED answer."""
        i = calls["n"]
        calls["n"] += 1
        assert i < len(items), "the seam asked for more items than were projected"
        served.append(items[i]["quote"])
        return items[i]

    for _ in items:
        recorded_reader(item={})
    assert served == ["alpha", "beta", "gamma"], served
    assert calls["n"] == len(items) == 3, "one call per projected item, no more"
    # the map puts every reply back exactly where it came from
    assert [items[index_map[("fact", i)]]["quote"] for i in range(2)] == ["alpha", "beta"]
    assert items[index_map[("abstention", 0)]]["quote"] == "gamma"


def test_RED_scorer_reaches_no_second_rule_engine():
    """B-10 (NOT B-15 — Codex SEQ 1098 corrected my conflation): delete the
    duplicate validation engine `fact16_checks`.

    THIS TEST PREVIOUSLY ENCODED THE WRONG REQUIREMENT. It demanded the scorer
    call `validate_via_production` directly at the old call site. SEQ 1098.1
    forbids exactly that: the scorer must consume the outcome rows that
    `run_event` already returns, never invoke a second validation path of its
    own, and `event_meta` must NOT be extended to support such a call. A test
    asserting the forbidden design would have driven me straight back into the
    27-failure migration I just reverted, so the assertion is corrected here
    rather than kept for symmetry.

    Order is fixed by SEQ 1098: B-14's replay through `run_event` lands FIRST,
    and only then does this engine lose its callers and get deleted.
    """
    src = open(os.path.join(_HERE, "scorers", "score_exp5.py"),
               encoding="utf-8").read()
    assert "fact16_checks" not in src, \
        "B-10: the scorer still reaches the duplicate validation engine"
    assert "validate_via_production" not in src, \
        ("B-10/SEQ 1098.1: the scorer must consume run_event's outcome rows, "
         "not invoke a second validation path directly")


# ---- STEP 3 / B-13: the two PLAN-BOUND doors (Codex SEQ 1097) ----

def test_RED_transport_routes_a_gold_drafter_reply_to_the_gold_door():
    """CONTROL 1 (must keep working): a K-fields gold-drafter response reaches
    `lint_doc`, which additionally requires du_worthy / gold_extra /
    ambiguity_note. This is the half the 36-event ingest already proved."""
    import inspect
    import raw_transport as RT
    # The door is a property of the PLAN, so it must NOT be a caller argument:
    # a default is exactly what would let a future EXP-5 run take the gold door
    # by forgetting to pass one.
    assert "door" not in inspect.signature(RT.ingest_workflow_result).parameters, \
        "the door is still caller-selectable"
    man = json.load(open(os.path.join(_HERE, "launch_kfields_drafts.manifest.json"),
                         encoding="utf-8"))
    assert man["door"] == "gold", "the K-fields plan must name its own door"
    f = _fact()                      # the gold-shaped fixture the drafters emit
    assert LNT.lint_parsed([_doc([f])], INPUTS, door="gold") == 0, \
        "the gold door must keep accepting a lawful gold-drafter reply"


def test_RED_transport_routes_an_exp5_producer_reply_to_the_reader_door():
    """CONTROL 2 (currently impossible): a lawful EXP-5 producer reply carries
    only the normal V2 envelope — no du_worthy, no gold_extra, no ambiguity_note
    — so it belongs at `lint_v2_reply`. Today the transport hardwires the GOLD
    door and would REJECT it.

    The selection must be PLAN-BOUND: the two plans already have separate
    manifests and separate approvals, so the manifest identity decides. It must
    never be inferred from the reply's own fields — a producer reply that
    happened to carry a gold key would then pick its own door, which is precisely
    the wrong-door failure this control exists to prevent.
    """
    import kf_lint as LNT
    q, pr, oc = _v2_locator()
    fact = _v2_fact(q)
    fact["part_ref"], fact["occurrence_in_part"] = pr, oc
    producer_reply = _v2_doc([fact])
    gold_errors, reader_errors = [], []
    LNT.lint_doc(producer_reply, gold_errors, INPUTS)
    LNT.lint_v2_reply(producer_reply, reader_errors, INPUTS)
    assert gold_errors, "premise broken: the gold door should refuse a producer reply"
    assert reader_errors == [], f"the reader door must ACCEPT it: {reader_errors}"
    # The dispatch itself lives in kf_lint.DOORS, so proving it BEHAVIOURALLY is
    # both stronger and correct: the same reply must pass through the reader door
    # and fail through the gold one, and the plan chooses which.
    assert LNT.lint_parsed([producer_reply], INPUTS, door="reader") == 0, \
        "the reader door refused a lawful producer reply"
    assert LNT.lint_parsed([producer_reply], INPUTS, door="gold") != 0, \
        "the gold door must still demand its review fields"
    with pytest.raises(ValueError):
        LNT.lint_parsed([producer_reply], INPUTS, door="whatever")


@pytest.mark.parametrize("door,why", [
    (None, "a plan that names no door"),
    ("reader ", "a door with stray whitespace"),
    ("GOLD", "a door in the wrong case"),
    ("tampered", "a door that is not a known contract"),
])
def test_a_plan_whose_manifest_door_is_missing_or_unknown_REFUSES(tmp_path, door, why):
    """B-13: the ingest must refuse rather than fall back. Each case is a real
    manifest on disk, because the refusal has to hold for the file the transport
    is actually handed — not for a value passed in a test."""
    import raw_transport as RT
    live = json.load(open(os.path.join(_HERE, "launch_kfields_drafts.manifest.json"),
                          encoding="utf-8"))
    if door is None:
        live.pop("door", None)
    else:
        live["door"] = door
    man = os.path.join(str(tmp_path), "plan.json")
    with open(man, "w", encoding="utf-8") as fh:
        json.dump(live, fh)
    sids = [e["source_id"] for e in live["events"]]
    body = lambda s: json.dumps({"source_id": s, "facts": [], "abstentions": []})
    res = {"results": [{"source_id": s, "sonnet": body(s), "opus": body(s)}
                       for s in sids]}
    out = RT.ingest_workflow_result(res, str(tmp_path / "o"), manifest_path=man,
                                    validate=True, inputs_dir=INPUTS)
    assert not out["ok"], f"{why} was ACCEPTED"


# ---- B-14: the replay reaches the REAL run_event (Codex SEQ 1100) ----

def _core_route_fixtures():
    """Existing Core fixtures — imported by the TEST, never by scorer code."""
    import sys
    sys.path.insert(0, os.path.join(_REPO, "driver", "core"))
    from driver.core import test_v2_event_route as R
    return R


@pytest.mark.parametrize("n_facts,n_abst,label", [
    (2, 1, "facts and abstentions"),
    (2, 0, "duplicate facts only"),
    (0, 1, "an abstention only"),
    (0, 0, "a lawful EMPTY whole-event answer"),
])
def test_B14_replay_through_the_real_run_event_keeps_the_index_relation(
        tmp_path, n_facts, n_abst, label):
    """B-14: feed the PUBLIC `driver_write_cli.run_event` the projected answer,
    writes OFF, with the SCORER-OWNED callback — and prove the exact
        (kind, original_index) -> raw index -> Core outcome row
    relation, with KIND-SPECIFIC outcomes.

    THE EARLIER VERSION OF THIS TEST WAS FALSE (Codex SEQ 1101). Its callback
    called a Core test helper that CONSTRUCTED a fact, so it ignored the captured
    record entirely and turned every abstention into a fact — it proved the route
    runs, never that the answer is replayed, and never reached
    `skipped/READER_ABSTAINED`. The reply is now authored ONLY by
    `score_exp5.replay_reader`; no test helper builds it. Core fixtures supply
    only the store and the event shell.
    """
    from driver.core.driver_write_cli import run_event
    from scorers.score_exp5 import project_replay_items, replay_reader
    R = _core_route_fixtures()
    base = R._v2_events()[R.CE_EVENT]
    raw0 = base["items"][0]
    part = base["text_parts"][0]
    quote = raw0["quote"]
    occ = None if part["content"].count(quote) == 1 else 1

    # The CAPTURED answer, built ONCE up front — permitted by SEQ 1101, unlike
    # authoring a reply inside the callback, which is what made the old test
    # false. From here on nothing constructs a record: the seam replays these.
    reply = {"source_id": R.CE_EVENT,
             "facts": [R._text_fact(base, raw0) for _ in range(n_facts)],
             "abstentions": [{"quote": quote, "reason": "insufficient evidence",
                              "part_ref": part["part"], "occurrence_in_part": occ}
                             for _ in range(n_abst)]}
    items, reader = replay_reader(reply)
    _, index_map = project_replay_items(reply)
    assert len(items) == n_facts + n_abst == len(index_map)

    event = {**base, "items": items}
    result = run_event(event, store=R._mirror_fake(event),
                       audit_dir=str(tmp_path), enable_writes=False,
                       reader=reader)
    rows = {r["index"]: r for r in result["items"]}
    assert sorted(rows) == list(range(len(items))), \
        f"{label}: Core returned rows {sorted(rows)} for {len(items)} raw items"
    assert result["status"] == "dry_run", f"{label}: writes were not off"

    for (kind, original_index), raw_index in index_map.items():
        row = rows[raw_index]
        if kind == "abstention":
            assert row["decision"] == "skipped", (
                f"{label}: {kind}[{original_index}] -> {row['decision']!r}, "
                f"a lawful abstention must be skipped")
            assert "READER_ABSTAINED" in row["codes"], (
                f"{label}: abstention row carries {row['codes']}")
        else:
            # NOT `!= "skipped"`: that would go green if every lawful fact were
            # parked or rejected, which is the opposite of what this control
            # exists to show. The known-lawful record must reach the accepted
            # dry-run decision, carrying no codes.
            assert row["decision"] == "written", (
                f"{label}: a lawful replayed fact reached {row['decision']!r} "
                f"with codes {row['codes']}")
            assert row["codes"] == [], f"{label}: lawful fact carried {row['codes']}"
    assert len(set(index_map.values())) == len(index_map), \
        f"{label}: two records share one raw index"

    # THE DURABLE AUDIT MUST TELL THE SAME STORY (SEQ 1101/1102). Returned rows
    # and written evidence diverging is precisely the failure this asserts away.
    audits = [f for f in os.listdir(str(tmp_path)) if f.endswith(".json")]
    assert len(audits) == 1, f"{label}: expected ONE audit, found {audits}"
    audit = json.load(open(os.path.join(str(tmp_path), audits[0]), encoding="utf-8"))
    acct = audit["raw_accounting"]
    assert acct["n_raw"] == len(items), \
        f"{label}: audit n_raw={acct['n_raw']} vs {len(items)} projected"
    fact_raw = sorted(v for (k, _), v in index_map.items() if k == "fact")
    abst_raw = sorted(v for (k, _), v in index_map.items() if k == "abstention")
    assert sorted(acct["origin"]) == fact_raw, \
        f"{label}: audit origin {acct['origin']} != fact raw indexes {fact_raw}"
    skipped = sorted(t["index"] for t in acct["terminals"]
                     if t["decision"] == "skipped")
    assert skipped == abst_raw, \
        f"{label}: audit skipped terminals {skipped} != abstentions {abst_raw}"


def test_RED_score_arm_consumes_route_outcomes_rather_than_validating_itself():
    """B-10 (SEQ 1098.2 / 1104): the scoring path must take its accepted /
    refused / parked / skipped evidence from the outcome rows `run_event`
    already returns, and only then does `fact16_checks` lose its last caller.

    The seam accepts its REAL dependency — the caller supplies the route — so no
    test store and no Core rule enter scorer code. That is the shape SEQ 1100
    allowed: fixtures live in the test, the seam takes what it is given."""
    import inspect
    from scorers import score_exp5
    assert "route" in inspect.signature(score_exp5.score_arm).parameters, \
        "score_arm cannot be handed the Core route, so it must still judge alone"


def test_RED_scorer_uses_core_fact_match_not_its_own_matcher():
    """B-15 (SEQ 1104/1106): the scorer must call ONLY
    `driver.core.fact_match.match_facts` on records converted through
    `PreparedFactV2.from_dict`, and must not retain the old graph/fixpoint/
    value/quote matcher under any name.

    Park accounting is deliberately NOT touched here — SEQ 1106 sequences that
    into the atomic B-10+B-16 change."""
    src = open(os.path.join(_HERE, "scorers", "score_exp5.py"),
               encoding="utf-8").read()
    assert "match_facts" in src, "the scorer does not call Core's matcher"
    assert "def match(" not in src, \
        "the retired automatic matcher is still defined in the scorer"


# ---- B-16 points 1-6: score_arm CONSUMES the completed route (Codex SEQ 1126) ----
#
# RED FIRST, as instructed. These state the interface before the seam exists, so
# each one fails for its OWN reason rather than because the parameter is missing.

def _synthetic_event(quotes, part_ref, source_id="E1"):
    """An event shell whose text ACTUALLY CONTAINS the fixture quotes.

    The scorer fixtures use synthetic quotes ("x"*60) that appear in no real
    filing, and the public route locates every fact by quote AND part. So the
    event carrying them is built from them, under the part the facts already
    name — inventing a part name instead made the route raise
    "quote does not occur in the named part", which `pytest.raises(ValueError)`
    swallowed because SchemaError subclasses ValueError. That made two controls
    pass without ever reaching `score_arm`. Caught by checking, not by the suite.

    This supplies TEXT ONLY — no law, no thresholds, no vocabulary — and the
    route still makes every decision.
    """
    body = "\n\n".join(dict.fromkeys(quotes))       # de-duped, order preserved
    return {"source_id": source_id, "event_time": "2026-04-23T16:00:00-04:00",
            "source_type": "8k", "ticker": "AAPL", "fye_month": 12,
            "text_parts": [{"part": part_ref, "content": body}], "items": []}


def _union_route(gold, arm_a, arm_b):
    """The union's OWN route, over the DEDUPLICATED union answer.

    Never the two single-run routes combined: fusion and planning are event-set
    dependent, so a fact that stood alone in one run can collide in the union.
    """
    from scorers.score_exp5 import union_answer
    return _route_for(union_answer(gold, arm_a, arm_b))


_EMPTY_ARM = {"E1": {"facts": []}}


def _arm(facts, sid="E1"):
    """One arm dict from a fact list — named so the SAME object is both scored
    and routed. Building it twice inline would route one object and score
    another, and the bijection check would then fail for a reason the test is
    not about."""
    return {sid: {"facts": facts}}


def _route_for(arm_by_event, tmp_path=None):
    """Build the REAL route input for an arm: one `route_reply` per event.

    `tmp_path` is optional so a test does not have to take the fixture just to
    hand the audit directory through — the audit output is not what any scoring
    test asserts, and requiring it would have meant editing ~20 test signatures
    for a value none of them read.
    """
    import tempfile
    from scorers.score_exp5 import route_reply
    if tmp_path is None:
        with tempfile.TemporaryDirectory() as td:
            return _route_for(arm_by_event, td)
    out = {}
    for sid, arm in arm_by_event.items():
        facts = arm.get("facts") or []
        abst = arm.get("abstentions") or []
        quotes = [(f.get("item") or {}).get("quote") for f in facts]
        quotes += [a.get("quote") for a in abst]
        parts = {r.get("part_ref") for r in list(facts) + list(abst)}
        # An EMPTY answer is lawful and still needs a route — there is simply no
        # emitted record to take a part from, so the shell keeps its own part.
        assert len(parts) <= 1, f"one fixture event, one part; got {parts}"
        part_ref = parts.pop() if parts else "p01"
        event = _synthetic_event([q for q in quotes if q], part_ref, sid)
        reply = {"source_id": sid, "facts": facts, "abstentions": abst}
        out[sid] = route_reply(reply, event, str(tmp_path))
    return out


def test_B16_route_is_REQUIRED_with_no_legacy_fallback(tmp_path):
    """Point 1. No `None` default, no legacy path — omitting it must RAISE.

    A default would let every existing caller keep self-validating silently,
    which is the exact failure this row exists to end.
    """
    gold, arm = _surprise_gold_and_arm()
    with pytest.raises(TypeError):
        score_arm(gold, arm, _META1)        # route DELIBERATELY omitted — a
        #   blanket regex migration added `route=` here once, which quietly
        #   turned the "route is required" proof into a call that supplies it.
        #   Caught by the control count dropping 12 -> 11, not by the diff.


@pytest.mark.parametrize("mutate,why", [
    (lambda r: {}, "an EMPTY route hides every event"),
    (lambda r: {**r, "E_EXTRA": list(r.values())[0]}, "an EXTRA event was routed"),
])
def test_B16_route_refuses_event_set_mismatch(mutate, why, tmp_path):
    """Point 3, event set. The route must cover exactly the scored events."""
    gold, arm = _surprise_gold_and_arm()
    with pytest.raises(ValueError):
        score_arm(gold, arm, _META1, route=mutate(_route_for(arm, tmp_path)))


def test_B16_route_refuses_duplicate_and_missing_outcome_indexes(tmp_path):
    """Point 3, rows. A duplicated index and a dropped index are both refusals —
    either one silently changes which record a decision is attributed to."""
    gold, arm = _surprise_gold_and_arm()
    base = _route_for(arm, tmp_path)
    rows = base["E1"]["result"]["items"]

    dup = {"E1": {**base["E1"],
                  "result": {**base["E1"]["result"], "items": rows + rows[:1]}}}
    with pytest.raises(ValueError):
        score_arm(gold, arm, _META1, route=dup)

    missing = {"E1": {**base["E1"],
                      "result": {**base["E1"]["result"], "items": rows[1:]}}}
    with pytest.raises(ValueError):
        score_arm(gold, arm, _META1, route=missing)


def test_B16_route_refuses_a_map_pointing_outside_the_result(tmp_path):
    """Point 3, map. An index_map entry with no row is an unmapped emission."""
    gold, arm = _surprise_gold_and_arm()
    base = _route_for(arm, tmp_path)
    bad = {"E1": {**base["E1"],
                  "index_map": {**base["E1"]["index_map"], ("fact", 99): 9999}}}
    with pytest.raises(ValueError):
        score_arm(gold, arm, _META1, route=bad)


def test_B16_rejected_is_reported_with_its_real_code_never_renamed_parked(tmp_path):
    """Point 4. Only a PUBLIC `parked` decision enters the parked numerator.

    A rejected fact is a DIFFERENT outcome with its own codes; counting it as
    parked would overstate the park rate and hide a contract violation behind a
    routine-looking number.

    The unit under test is `score_arm`'s CONSUMPTION of completed rows, so the
    rejected row is supplied directly. That is the real interface — B-16's whole
    point is that the scorer no longer decides anything, it only counts what the
    route already decided. Two production routes were measured first and neither
    can deliver a rejection through this seam: a LANE violation comes back
    `parked`, and a blank quote is refused at PreparedFactV2 construction before
    the route ever sees it. Inventing a fixture to force one would have tested
    the fixture, not the accounting.
    """
    q = "z" * 80
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="metric")]}}
    gold = {"E1": [_gold_fact(q, fact_type="metric",
                              gold_extra={"expectation_comparison_present": False})]}
    base = _route_for(arm, tmp_path)
    row = dict(base["E1"]["result"]["items"][0],
               decision="rejected", codes=["CHANNEL_CONTRACT_INVALID"])
    route = {"E1": {**base["E1"],
                    "result": {**base["E1"]["result"], "items": [row]}}}
    r = score_arm(gold, arm, _META1, route=route)
    assert r["would_park"] == 0.0, (
        f"a REJECTED fact was counted as parked: would_park={r['would_park']}")
    assert "rejected:CHANNEL_CONTRACT_INVALID" in r["route_codes"], (
        f"the rejection was not reported with its real code: {r['route_codes']}")
    assert not any(k.startswith("park:") for k in r["route_codes"]), (
        f"a rejection was renamed into a park code: {r['route_codes']}")


# ---- SEQ 1127: the replay store's read surface must be COMPLETE, all 4 lanes ----

def _lane_case(facts):
    """Drive a reply through the runtime `route_reply` and return its rows.

    Core fixtures build the TEST only. `score_exp5` imports no test module —
    `test_no_scorer_runtime_imports_a_core_test_module` pins that separately.
    """
    import tempfile
    from scorers.score_exp5 import route_reply
    R = _core_route_fixtures()
    base = R._v2_events()[R.CE_EVENT]
    with tempfile.TemporaryDirectory() as td:
        out = route_reply({"source_id": R.CE_EVENT, "facts": facts,
                           "abstentions": []}, base, td)
    assert out["result"]["status"] == "dry_run", "writes were not off"
    return [(r["index"], r["decision"], r["codes"]) for r in out["result"]["items"]]


def _lane_fact(**over):
    import datetime
    from driver.core.test_v2_attacks import slot
    R = _core_route_fixtures()
    base = R._v2_events()[R.CE_EVENT]
    end = datetime.date.fromisoformat(base["event_time"][:10]) - datetime.timedelta(days=30)
    period = {"time_type": "duration", "period_end_date": end.isoformat(),
              "period_start_date": (end - datetime.timedelta(days=89)).isoformat()}
    numeric = {"level_low": slot(5, 1, None), "level_high": slot(5, 1, None),
               "level_shape_hint": "point", "level_unit": "m_usd"}
    fields = {**numeric, **period}
    fields.update(over)
    fact_type = fields.pop("fact_type")
    return R._text_fact(base, base["items"][0], fact_type=fact_type, **fields)


def test_replay_store_serves_EVERY_v2_lane_not_just_metric():
    """SEQ 1127.2 — one lawful fact of EACH fact_type reaches a PUBLIC outcome.

    The original probe was metric-only, which is exactly why a missing read
    method survived review: metric never asks for prior guide units.
    """
    assert _lane_case([_lane_fact(fact_type="metric", driver_name="revenue",
                                  driver_state="reported")]) == [(0, "written", [])]
    assert _lane_case([_lane_fact(fact_type="guidance",
                                  driver_name="revenue_guidance",
                                  driver_state="introduced",
                                  company_confirmed=True)]) == [(0, "written", [])]
    assert _lane_case([_lane_fact(fact_type="action_event",
                                  driver_name="buyback_program",
                                  driver_state="announced")]) == [(0, "written", [])]
    # the surprise carries its REQUIRED §153 home sibling in the same event
    assert _lane_case([
        _lane_fact(fact_type="surprise", driver_name="revenue_surprise",
                   driver_state="beat", surprise_basis_hint="actual",
                   comparison_baseline="consensus"),
        _lane_fact(fact_type="metric", driver_name="revenue",
                   driver_state="reported"),
    ]) == [(0, "written", []), (1, "written", [])]


@pytest.mark.parametrize("state", ["withdrawn", "reaffirmed"])
def test_numberless_guidance_reaches_the_prior_unit_read_not_an_AttributeError(state):
    """SEQ 1127.3 — the read `_ReplayStore` was MISSING.

    A numberless guidance withdrawal/reaffirmation is the only shape that asks
    for prior guide units (OD-10 series_unit). Before the fix this raised
    AttributeError — a crash, not a decision. The recorded expectation is the
    route's ACTUAL fail-closed plan result, not an invented one: the empty
    scratch graph offers no prior guide, so `stamp_series_unit` fails closed and
    the fact PARKS with SERIES_UNIT. That it parks — rather than explodes — is
    the whole proof.
    """
    rows = _lane_case([_lane_fact(fact_type="guidance",
                                  driver_name="revenue_guidance",
                                  driver_state=state, company_confirmed=True,
                                  level_low=None, level_high=None,
                                  level_shape_hint=None, level_unit=None)])
    assert rows == [(0, "parked", ["SERIES_UNIT"])], rows


def test_replay_store_REFUSES_a_transaction_because_scoring_never_writes():
    """SEQ 1127.4 — retained. Writes are off, so a transaction means the route
    tried to write during scoring; failing loudly beats buffering an unread op."""
    from scorers.score_exp5 import _ReplayStore
    with pytest.raises(RuntimeError):
        _ReplayStore({}, {}, []).transaction()


def test_replay_drivers_REFUSE_one_name_with_two_fact_types():
    """SEQ 1127.4 — retained. Silently keeping one would hand the route a
    fabricated registry and change which facts pair with which home."""
    from scorers.score_exp5 import _replay_drivers
    with pytest.raises(ValueError):
        _replay_drivers({"facts": [
            {"fact_type": "metric", "item": {"driver_name": "revenue"}},
            {"fact_type": "guidance", "item": {"driver_name": "revenue"}}]})


def test_no_scorer_runtime_imports_a_core_test_module():
    """SEQ 1126.7 / 1127.2 — the runtime scorer must not import a Core TEST
    fixture. Checked against the source, so it cannot be satisfied by import
    order or a lazy import that only fires on some paths."""
    with open(os.path.join(_REPO, ".claude", "plans", "Drivers", "experiments",
                           "harness", "scorers", "score_exp5.py"),
              encoding="utf-8") as fh:
        src = fh.read()
    for banned in ("test_driver_write_cli", "test_v2_event_route",
                   "test_v2_attacks", "test_stage_a_v2"):
        assert banned not in src, f"scorer runtime imports Core test module {banned}"


def test_every_frozen_v2_field_is_measured_EXACTLY_ONCE():
    """Codex SEQ 1132 — the field denominator must be complete and disjoint.

    Derived from the frozen owners, never a copied schema list: a new V2 item
    field shows up here as UNACCOUNTED instead of silently going unscored, and a
    field that drifts into two measurements shows up as double-counted.

    The bug this closes: the pooled set was `ITEM_FIELDS - GRADER_OWNED - quote`,
    which still contained the five numeric slots, `slice_parts` and
    `measurement_raw_spans` — all of which ALSO have their own specialized
    comparison. Those seven fields were being weighted twice.
    """
    from scorers.score_exp5 import (field_accounting, CODE_FIELDS, GRADER_OWNED,
                                    SPECIALIZED_COLLECTIONS, FACT_LEVEL_FIELDS)
    from driver.core.prepared_fact_v2 import ITEM_FIELDS, NUMERIC_SLOTS

    where = field_accounting()
    expected = set(ITEM_FIELDS) | set(FACT_LEVEL_FIELDS)
    assert set(where) == expected, (
        f"unaccounted: {sorted(expected - set(where))}; "
        f"unknown: {sorted(set(where) - expected)}")

    buckets = {}
    for field, place in where.items():
        buckets.setdefault(place, set()).add(field)
    # disjoint by construction (one dict value per field), so the real check is
    # that each specialized group is EXCLUDED from the generic pool
    pooled = set(CODE_FIELDS)
    for group, name in ((set(NUMERIC_SLOTS), "numeric slots"),
                        (set(SPECIALIZED_COLLECTIONS), "specialized collections"),
                        (set(GRADER_OWNED), "grader-owned"),
                        ({"quote"}, "evidence locator")):
        overlap = pooled & group
        assert not overlap, f"{sorted(overlap)} counted BOTH pooled and as {name}"

    assert buckets["pooled"] == pooled
    assert len(where) == len(ITEM_FIELDS) + len(FACT_LEVEL_FIELDS)


# ---- SEQ 1131/1132: independent field mutations, each proving its own movement ----

_MUT_Q = "m" * 80


def _mut_item(quote=None, **over):
    quote = _MUT_Q if quote is None else quote
    base = dict(driver_name="revenue",
                level_low=_v2_slot(quote, value=5),
                level_high=_v2_slot(quote, value=5),
                level_shape_hint="point", level_unit="m_usd",
                slice_parts=["segment:a", "segment:b"],
                measurement_raw_spans=["Same Store Sales"],
                # A RESOLVABLE period, ending before `_META1`'s event date.
                # Without it the route parks every fixture on
                # PERIOD_UNRESOLVED, so nothing is route-ACCEPTED and the
                # Addendum-A extras path has no eligible fact to classify.
                time_type="duration", period_start_date="2026-01-01",
                period_end_date="2026-03-31")
    base.update(over)
    return _v2_item(quote, **base)


def _mut_score(fact_over=None, item_over=None, slot_over=None):
    """Score ONE gold/produced pair where the produced side carries exactly one
    deliberate difference, with the grader ruling the pair together.

    The ruling is REQUIRED to reach field scoring at all: `match_facts`
    auto-links only IDENTICAL complete records, so any real field error is
    unmatched by construction (Codex SEQ 1132.2). The ruling supplies the pair
    BY INDEX — no quote or value heuristic proposes it.
    """
    from scorers.score_exp5 import MEANING_FIELDS
    gold = {"E1": [_gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                              gold_extra={"expectation_comparison_present": False})]}
    item = _mut_item(**(item_over or {}))
    if slot_over:
        item["level_low"] = dict(item["level_low"], **slot_over)
    produced = _v2_fact(_MUT_Q, fact_type="metric", item=item)
    produced.update(fact_over or {})
    arm = {"E1": {"facts": [produced]}}
    verdicts = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    return score_arm(gold, arm, _META1, verdicts, route=_route_for(arm),
                     ambiguity_resolutions={("E1", 0): 0})


def test_MUT_lawful_unchanged_pair_is_the_control():
    """The control every mutation below is measured against."""
    r = _mut_score()
    assert r["matched"] == 1 and r["value_shape_acc"] == 1.0, r


@pytest.mark.parametrize("kind,kwargs,moves", [
    ("fact_type",             {"fact_over": {"fact_type": "guidance"}}, "lane"),
    ("per_x",                 {"fact_over": {"per_x": "share"}},        "field"),
    ("ordinary item field",   {"item_over": {"sentinel_class": "na"}},  "field"),
    ("slot value",            {"slot_over": {"value": 9}},              "field"),
    ("slot scale_multiplier", {"slot_over": {"scale_multiplier": 1000}}, "field"),
    ("slice MEMBERSHIP",      {"item_over": {"slice_parts": ["segment:a",
                                                             "segment:z"]}}, "field"),
])
def test_MUT_each_axis_moves_its_own_denominator(kind, kwargs, moves):
    """Each axis mutated INDEPENDENTLY must move the measurement it belongs to.

    `fact_type` moves the separate hard `wrong_lane` gate rather than the pooled
    field accuracy — that gate is deliberately kept distinct (SEQ 1132.1).
    """
    control = _mut_score()
    r = _mut_score(**kwargs)
    if moves == "lane":
        assert r["wrong_lane"] > control["wrong_lane"], (kind, r)
    else:
        assert r["value_shape_acc"] < control["value_shape_acc"], (kind, r)


@pytest.mark.parametrize("kind,kwargs", [
    ("slice ORDER", {"item_over": {"slice_parts": ["segment:b", "segment:a"]}}),
    ("measurement SPELLING",
     {"item_over": {"measurement_raw_spans": ["same  store   sales"]}}),
])
def test_MUT_equivalent_spellings_must_NOT_move_the_score(kind, kwargs):
    """The other half of the pair: `slice_parts` is compared as a SET, so ORDER
    is not a difference; measurement spans go through the OD-9 span owner, so
    spelling/whitespace is not a difference. If either moved the score, the
    scorer would be punishing a producer for a lawful equivalent spelling."""
    control = _mut_score()
    r = _mut_score(**kwargs)
    assert r["value_shape_acc"] == control["value_shape_acc"], (kind, r)
    assert r["matched"] == control["matched"], (kind, r)


@pytest.mark.parametrize("rulings,reason", [
    ({("E1", 0): 99},   "ruling_out_of_range"),
    ({},                "ruling_missing"),
])
def test_MUT_invalid_grader_rulings_block_PASS(rulings, reason):
    """An invalid or incomplete ruling must BLOCK, never be quietly ignored —
    proceeding on a malformed ruling means inventing the grader's answer."""
    from scorers.score_exp5 import MEANING_FIELDS
    gold = {"E1": [_gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                              gold_extra={"expectation_comparison_present": False})]}
    produced = _v2_fact(_MUT_Q, fact_type="metric",
                        item=_mut_item(sentinel_class="na"))
    arm = {"E1": {"facts": [produced]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", 0): {k: True for k in MEANING_FIELDS}},
                  route=_route_for(arm), ambiguity_resolutions=rulings)
    assert r["PASS"] is not True, (reason, r)
    assert any(row.get("reason") == reason for row in r["ambiguous_rows"]), (
        reason, r["ambiguous_rows"])


def test_MUT_one_produced_fact_cannot_be_ruled_onto_two_golds():
    """The emit-once law at the grader boundary: double-crediting one produced
    fact to two golds inflates recall for free."""
    from scorers.score_exp5 import MEANING_FIELDS
    q2 = "n" * 80
    gold = {"E1": [_gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                              gold_extra={"expectation_comparison_present": False}),
                   _gold_fact(q2, fact_type="metric",
                              item=_mut_item(driver_name="fuel_cost"),
                              gold_extra={"expectation_comparison_present": False})]}
    arm = {"E1": {"facts": [_v2_fact(_MUT_Q, fact_type="metric",
                                     item=_mut_item(sentinel_class="na"))]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(2)},
                  route=_route_for(arm),
                  ambiguity_resolutions={("E1", 0): 0, ("E1", 1): 0})
    assert r["PASS"] is not True
    assert any(row.get("reason") == "ruling_duplicate_produced"
               for row in r["ambiguous_rows"]), r["ambiguous_rows"]


# ---- SEQ 1133: Addendum-A extras + the confirmed-wrong-accepted safety gate ----

def _safety_case(extra_facts=(), extras_verdicts=None, meaning_all_true=True):
    """One lawful matched pair, plus any EXTRA produced facts the gold does not
    cover. Fake verdicts only — nothing here calls a grader or an AI."""
    from scorers.score_exp5 import MEANING_FIELDS
    gold = {"E1": [_gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                              gold_extra={"expectation_comparison_present": False})]}
    facts = [_v2_fact(_MUT_Q, fact_type="metric", item=_mut_item())]
    facts.extend(extra_facts)
    arm = {"E1": {"facts": facts}}
    verdicts = {("E1", 0): {k: meaning_all_true for k in MEANING_FIELDS}}
    return score_arm(gold, arm, _META1, verdicts, route=_route_for(arm),
                     extras_verdicts=extras_verdicts)


def _extra_fact(quote, **item_over):
    return _v2_fact(quote, fact_type="metric", item=_mut_item(**item_over))


def test_ADDA_all_correct_lawful_path_passes_safety():
    """The control: one lawful pair, no extras, every meaning verdict true."""
    r = _safety_case()
    assert r["confirmed_wrong_accepted"] == 0
    assert r["safety_result"] == "PASS", r


def test_ADDA_unsupported_extra_is_a_confirmed_wrong_ACCEPTED_fact():
    """An accepted fact the source does not support FAILS the run outright —
    the sixth criterion is ANDed in, never averaged against the other five."""
    q = "u" * 80
    r = _safety_case(extra_facts=[_extra_fact(q, driver_name="fuel_cost")],
                     extras_verdicts={("E1", 1): "unsupported"})
    assert r["confirmed_wrong_accepted"] == 1, r
    assert r["safety_result"] == "FAIL" and r["PASS"] is not True, r


def test_ADDA_genuine_key_miss_is_INCONCLUSIVE_not_a_failure():
    """A real gold-key miss leaves the question OPEN. It must not be scored as
    a wrong acceptance — but an open question cannot PASS either."""
    q = "k" * 80
    r = _safety_case(extra_facts=[_extra_fact(q, driver_name="fuel_cost")],
                     extras_verdicts={("E1", 1): "key_miss"})
    assert r["confirmed_wrong_accepted"] == 0, r
    assert r["safety_result"] == "INCONCLUSIVE" and r["PASS"] is not True, r


def test_ADDA_a_false_meaning_verdict_on_an_accepted_fact_is_confirmed_wrong():
    """Not only extras: a matched, ROUTE-ACCEPTED fact whose required meaning
    verdict is false is equally a confirmed-wrong accepted fact."""
    r = _safety_case(meaning_all_true=False)
    assert r["confirmed_wrong_accepted"] == 1, r
    assert r["safety_result"] == "FAIL" and r["PASS"] is not True, r


@pytest.mark.parametrize("verdicts,reason", [
    ({("E1", 1): "not_a_bucket"}, "extras_verdict_malformed"),
    ({("E1", 99): "duplicate"},   "extras_verdict_out_of_range"),
    ({},                          "extras_verdict_missing"),
])
def test_ADDA_malformed_extras_verdicts_block_PASS(verdicts, reason):
    """Every unmatched route-accepted fact needs EXACTLY ONE verdict from the
    three buckets. No other bucket, and no string heuristic invents one."""
    q = "x" * 80
    r = _safety_case(extra_facts=[_extra_fact(q, driver_name="fuel_cost")],
                     extras_verdicts=verdicts)
    assert r["PASS"] is not True, (reason, r)
    assert any(row.get("reason") == reason for row in r["ambiguous_rows"]), (
        reason, r["ambiguous_rows"])


def test_ADDA_a_refused_row_never_enters_the_accepted_fact_safety_count():
    """A parked/rejected/skipped fact is REPORTED but is not a wrong
    ACCEPTANCE — the system already refused it, and counting it here would
    punish the safety gate for working."""
    q = "p" * 80
    # `fuel_cost_surprise`, NOT `revenue_surprise`: the lawful pair already
    # supplies a `revenue` metric, so a revenue surprise would FIND its §153
    # home and be written. This surprise's home is absent, so the route parks
    # it — which is the refused row this control needs.
    parked = _extra_fact(q, driver_name="fuel_cost_surprise",
                         surprise_basis_hint="actual",
                         comparison_baseline="consensus")
    parked["fact_type"] = "surprise"
    parked["item"] = dict(parked["item"], driver_state="beat")
    r = _safety_case(extra_facts=[parked], extras_verdicts={})
    rows = {i: d for i, d, _c in
            [(x["index"], x["decision"], x["codes"])
             for x in _route_for({"E1": {"facts": [
                 _v2_fact(_MUT_Q, fact_type="metric", item=_mut_item()), parked]}}
             )["E1"]["result"]["items"]]}
    assert rows.get(1) != "written", f"fixture no longer refuses row 1: {rows}"
    assert r["confirmed_wrong_accepted"] == 0, r


# ---- SEQ 1134: the four bounded corrections, each with its own control ----

def test_1134_unrun_grading_with_unmatched_gold_cannot_PASS():
    """Gap 1. A <=5% unmatched slice must still block PASS when no ruling exists.

    My earlier claim that existing accounting covered this was WRONG: a raw
    unmatched row increments neither `ambiguities_unresolved` nor
    `verdicts_missing`, and `potential_recall` omits it — so the run could PASS
    with ungraded gold sitting there. A ruling is required exactly when
    unmatched gold exists.
    """
    from scorers.score_exp5 import MEANING_FIELDS
    n = 40                                        # 1/40 unmatched = 2.5%, <=5%
    quotes = [chr(65 + i) * 80 for i in range(n)]
    gold = {"E1": [_gold_fact(q, fact_type="metric", item=_mut_item(q),
                              gold_extra={"expectation_comparison_present": False})
                   for q in quotes]}
    facts = [_v2_fact(q, fact_type="metric", item=_mut_item(q))
             for q in quotes[:-1]]
    facts.append(_v2_fact(quotes[-1], fact_type="metric",
                          item=_mut_item(quotes[-1], sentinel_class="na")))
    arm = {"E1": {"facts": facts}}
    r = score_arm(gold, arm, _META1,
                  {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(n)},
                  route=_route_for(arm))
    assert r["PASS"] is not True, r
    assert any(row.get("reason") == "ruling_missing"
               for row in r["ambiguous_rows"]), r["ambiguous_rows"]


def test_1134_no_extras_verdict_for_an_accepted_extra_is_INCOMPLETE():
    """Gap 2. Same hole on the extras side."""
    r = _safety_case(extra_facts=[_extra_fact("u" * 80, driver_name="fuel_cost")],
                     extras_verdicts=None)
    assert r["PASS"] is not True, r
    assert any(row.get("reason") == "extras_verdict_missing"
               for row in r["ambiguous_rows"]), r["ambiguous_rows"]


def test_1134_no_extras_input_is_LAWFULLY_complete_when_nothing_is_eligible():
    """The other side of gap 2 — the requirement must not fire when there is no
    unmatched route-written fact to classify."""
    r = _safety_case(extras_verdicts=None)
    assert not any(row.get("reason", "").startswith("extras_")
                   for row in r["ambiguous_rows"]), r["ambiguous_rows"]
    assert r["safety_result"] == "PASS", r


def test_1134_score_union_FORWARDS_extras_verdicts():
    """Gap 3. The argument was accepted and then dropped, silently exempting
    every union from the Addendum-A safety requirement."""
    from scorers.score_exp5 import score_union, union_answer, MEANING_FIELDS
    q_extra = "u" * 80
    gold = {"E1": [_gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                              gold_extra={"expectation_comparison_present": False})]}
    arm_a = {"E1": {"facts": [_v2_fact(_MUT_Q, fact_type="metric",
                                       item=_mut_item())]}}
    arm_b = {"E1": {"facts": [_extra_fact(q_extra, driver_name="fuel_cost")]}}
    route = _route_for(union_answer(gold, arm_a, arm_b))
    r = score_union(gold, arm_a, arm_b, _META1,
                    {("E1", 0): {k: True for k in MEANING_FIELDS}},
                    route=route, extras_verdicts={("E1", 1): "unsupported"})
    assert r["confirmed_wrong_accepted"] == 1, r
    assert r["safety_result"] == "FAIL", r


def test_1134_an_UNSAFE_arm_is_never_rescued_by_union_recall():
    """The scoring spec is explicit. `final_gate` was a plain OR, so a passing
    union leg returned True even with a confirmed-wrong ACCEPTED fact in the
    single arm. Safety is a VETO over the tier decision, not another leg."""
    from scorers.score_exp5 import final_gate

    def _res(**over):
        """A complete leg result — `_leg` reads the other axes too, so a thin
        stub would fail on a missing key instead of exercising the veto."""
        base = {"PASS": True, "recall": 0.99, "would_park": 0.0,
                "value_shape_acc": 1.0, "wrong_lane": 0, "wrong_name": 0,
                "confirmed_wrong_accepted": 0, "safety_result": "PASS"}
        base.update(over)
        return base

    good_union = _res()
    unsafe_single = _res(PASS=False, confirmed_wrong_accepted=1,
                         safety_result="FAIL")
    assert final_gate(unsafe_single, good_union) is False, (
        "a passing union leg rescued an UNSAFE single arm")
    # the same union WITHOUT the unsafe single is not blocked by this rule
    assert final_gate(_res(), good_union) is True


@pytest.mark.parametrize("second,expect_agreed", [
    ({("E1", 0): 0}, True),      # identical independent answers -> scorable
    ({("E1", 0): 1}, False),     # different answers -> no ruling
    ({}, False),                 # present in one input only -> no ruling
])
def test_1134_two_grader_inputs_are_scorable_ONLY_when_they_agree(second,
                                                                  expect_agreed):
    """Silently preferring one input would be the scorer choosing between two
    qualified graders, which is not its call."""
    from scorers.score_exp5 import reconcile_rulings
    agreed, disagreements = reconcile_rulings({("E1", 0): 0}, second)
    assert bool(agreed) is expect_agreed, (agreed, disagreements)
    assert bool(disagreements) is not expect_agreed
    if disagreements:
        assert disagreements[0]["reason"] == "ruling_disagreement"


# ---- SEQ 1126.5: abstentions split by LOCATOR, never by decision spelling ----

_ABST_MISS_Q = "w" * 80


def _abst_case(abstention_quote):
    """TWO gold facts: one the producer answers, one it does NOT.

    The unanswered gold is what an abstention can be linked to — SEQ 1135 links
    a gold abstention one-to-one to an OTHERWISE-UNMATCHED gold row. An
    abstention beside an already-matched gold is not a miss, so the fixture has
    to leave a gold row genuinely unanswered for the linked case to exist.
    """
    from scorers.score_exp5 import MEANING_FIELDS
    gold = {"E1": [
        _gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                   gold_extra={"expectation_comparison_present": False}),
        _gold_fact(_ABST_MISS_Q, fact_type="metric",
                   item=_mut_item(_ABST_MISS_Q, driver_name="fuel_cost"),
                   gold_extra={"expectation_comparison_present": False})]}
    _q, part, occ = _v2_locator()
    arm = {"E1": {"facts": [_v2_fact(_MUT_Q, fact_type="metric",
                                     item=_mut_item())],
                  "abstentions": [{"quote": abstention_quote, "part_ref": part,
                                   "occurrence_in_part": occ,
                                   "reason": "insufficient evidence"}]}}
    return score_arm(gold, arm, _META1,
                     {("E1", i): {k: True for k in MEANING_FIELDS}
                      for i in range(2)},
                     route=_route_for(arm))


def test_ABST_a_gold_linked_abstention_is_charged_as_a_park():
    """Declining on evidence that carries a real gold fact is NOT being right:
    it enters both the would-park numerator and its denominator."""
    r = _abst_case(_ABST_MISS_Q)
    assert r["would_park"] > 0.0, r
    assert any(k.startswith("abstained_on_gold:") for k in r["route_codes"]), \
        r["route_codes"]


def test_ABST_a_diagnostic_abstention_is_charged_to_NEITHER_side():
    """An abstention on evidence no gold covers must not be charged — that
    would punish a producer for correctly saying nothing about a non-fact."""
    linked = _abst_case(_ABST_MISS_Q)
    diagnostic = _abst_case("z" * 80)
    assert diagnostic["would_park"] == 0.0, diagnostic
    assert diagnostic["would_park"] < linked["would_park"]
    assert not any(k.startswith("abstained_on_gold:")
                   for k in diagnostic["route_codes"]), diagnostic["route_codes"]


def test_ABST_the_split_is_the_LOCATOR_not_the_route_decision():
    """Both abstentions above reach the SAME public decision, so a split derived
    from a decision spelling would put them in one bucket. Proven by showing the
    decisions are identical while the accounting differs."""
    from scorers.score_exp5 import route_reply
    import tempfile
    _q, part, occ = _v2_locator()
    decisions = []
    for quote in (_ABST_MISS_Q, "z" * 80):
        arm = {"E1": {"facts": [_v2_fact(_MUT_Q, fact_type="metric",
                                         item=_mut_item())],
                      "abstentions": [{"quote": quote, "part_ref": part,
                                       "occurrence_in_part": occ,
                                       "reason": "insufficient evidence"}]}}
        rows = _route_for(arm)["E1"]["result"]["items"]
        decisions.append(rows[1]["decision"])
    assert decisions[0] == decisions[1], (
        f"fixture no longer shares one decision: {decisions}")
    assert (_abst_case(_ABST_MISS_Q)["would_park"]
            != _abst_case("z" * 80)["would_park"])


def test_1135_a_produced_DUPLICATE_earns_no_recall_and_blocks_PASS():
    """SEQ 1135. One fact emitted twice must not inflate the would-park
    denominator, must earn no extra recall, and must BLOCK PASS —
    `MatchResult.can_pass` already says so, but the scorer was recording the
    violation and passing anyway."""
    from scorers.score_exp5 import MEANING_FIELDS
    gold = {"E1": [_gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                              gold_extra={"expectation_comparison_present": False})]}
    one = _v2_fact(_MUT_Q, fact_type="metric", item=_mut_item())
    twice = {"E1": {"facts": [one, dict(one)]}}
    single = {"E1": {"facts": [one]}}
    verdicts = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    r_dup = score_arm(gold, twice, _META1, verdicts, route=_route_for(twice))
    r_one = score_arm(gold, single, _META1, verdicts, route=_route_for(single))
    assert r_dup["recall"] == r_one["recall"], "the duplicate earned recall"
    assert r_dup["would_park"] == r_one["would_park"], (
        "the duplicate inflated the would-park denominator")
    assert "emit_once_violation" in r_dup["route_codes"], r_dup["route_codes"]
    assert r_dup["PASS"] is not True, r_dup


def test_1135_an_abstention_with_an_unsound_locator_is_REFUSED_upstream():
    """SEQ 1135 — validated by the ONE `verify_occurrence` owner against the
    exact named part, at the seam that actually has the event text."""
    import tempfile
    from scorers.score_exp5 import route_reply
    # A CONTROLLED event: `_route_for` builds its shell FROM the record quotes,
    # so a fabricated quote cannot be expressed through it — the quote would be
    # in the text by construction. The event here holds ONLY the fact's quote.
    event = _synthetic_event([_MUT_Q], "p01")
    fact = dict(_v2_fact(_MUT_Q, fact_type="metric", item=_mut_item()),
                part_ref="p01", occurrence_in_part=None)
    for quote, part_ref, why in (
            ("a quote that appears nowhere in this part", "p01", "fabricated"),
            (_MUT_Q, "no_such_part", "unknown part")):
        reply = {"source_id": "E1", "facts": [fact],
                 "abstentions": [{"quote": quote, "part_ref": part_ref,
                                  "occurrence_in_part": None,
                                  "reason": "insufficient evidence"}]}
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(ValueError):
                route_reply(reply, event, td)
    # ...and the LAWFUL locator is accepted, so the guard is not simply refusing
    # everything
    ok = {"source_id": "E1", "facts": [fact],
          "abstentions": [{"quote": _MUT_Q, "part_ref": "p01",
                           "occurrence_in_part": None,
                           "reason": "insufficient evidence"}]}
    with tempfile.TemporaryDirectory() as td:
        assert route_reply(ok, event, td)["result"]["status"] == "dry_run"


def test_1135_one_abstention_cannot_be_charged_against_TWO_gold_rows():
    """One-to-one: two unanswered golds sharing a locator must not both be
    charged to a single abstention — that would double-count one miss."""
    from scorers.score_exp5 import classify_abstentions
    gold = [_gold_fact(_ABST_MISS_Q, fact_type="metric",
                       item=_mut_item(_ABST_MISS_Q),
                       gold_extra={"expectation_comparison_present": False})
            for _ in range(2)]
    _q, part, occ = _v2_locator()
    abstentions = [{"quote": _ABST_MISS_Q, "part_ref": part,
                    "occurrence_in_part": occ, "reason": "insufficient evidence"}]
    linked, diagnostic = classify_abstentions(abstentions, gold, [0, 1])
    assert len(linked) == 1, linked
    assert linked[0][0] == 0 and linked[0][1] in (0, 1)


def test_1136_an_answered_gold_row_cannot_ALSO_be_charged_to_an_abstention():
    """SEQ 1136.1 — a gold row answered through a VALID grader ruling is no
    longer available to an abstention. Charging both would count one gold row's
    outcome twice: once as answered, once as declined."""
    from scorers.score_exp5 import MEANING_FIELDS
    gold = {"E1": [
        _gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                   gold_extra={"expectation_comparison_present": False}),
        _gold_fact(_ABST_MISS_Q, fact_type="metric",
                   item=_mut_item(_ABST_MISS_Q, driver_name="fuel_cost"),
                   gold_extra={"expectation_comparison_present": False})]}
    _q, part, occ = _v2_locator()
    # the produced fact differs from gold[1], so it needs a RULING to link
    arm = {"E1": {"facts": [
        _v2_fact(_MUT_Q, fact_type="metric", item=_mut_item()),
        _v2_fact(_ABST_MISS_Q, fact_type="metric",
                 item=_mut_item(_ABST_MISS_Q, driver_name="fuel_cost",
                                sentinel_class="na"))],
        "abstentions": [{"quote": _ABST_MISS_Q, "part_ref": part,
                         "occurrence_in_part": occ,
                         "reason": "insufficient evidence"}]}}
    verdicts = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(2)}
    unruled = score_arm(gold, arm, _META1, verdicts, route=_route_for(arm))
    ruled = score_arm(gold, arm, _META1, verdicts, route=_route_for(arm),
                      ambiguity_resolutions={("E1", 1): 1})
    assert any(k.startswith("abstained_on_gold:") for k in unruled["route_codes"])
    assert not any(k.startswith("abstained_on_gold:")
                   for k in ruled["route_codes"]), (
        "the abstention still charged a gold row the grader had answered")


def test_1136_the_duplicate_bucket_is_filled_from_the_identity_owner():
    """SEQ 1136.2 — `MatchResult` already collapsed exact duplicates, so the
    named bucket is populated mechanically rather than asking a fake grader to
    rediscover them."""
    from scorers.score_exp5 import MEANING_FIELDS
    gold = {"E1": [_gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                              gold_extra={"expectation_comparison_present": False})]}
    one = _v2_fact(_MUT_Q, fact_type="metric", item=_mut_item())
    arm = {"E1": {"facts": [one, dict(one)]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", 0): {k: True for k in MEANING_FIELDS}},
                  route=_route_for(arm))
    assert r["extras"]["duplicate"] == 1, r["extras"]
    assert r["PASS"] is not True, "emit-once must still block PASS"


def test_1136_presence_disagreement_returns_INCOMPLETE_end_to_end():
    """SEQ 1135/1136 — two independent grader inputs that DISAGREE must make the
    METRIC incomplete, not merely the helper. Reaches `presence_disagreement`
    itself, not `reconcile_rulings` alone."""
    from scorers.score_exp5 import presence_disagreement
    gold = {"E1": [_gold_fact(_MUT_Q, fact_type="metric", item=_mut_item(),
                              gold_extra={"expectation_comparison_present": False})]}
    differing = {"E1": {"facts": [_v2_fact(_MUT_Q, fact_type="metric",
                                           item=_mut_item(sentinel_class="na"))]}}
    other = {"E1": {"facts": []}}
    agree = ({("E1", 0): 0}, {("E1", 0): 0})
    disagree = ({("E1", 0): 0}, {("E1", 0): None})
    assert presence_disagreement(gold, differing, other, _META1,
                                 resolutions_a=disagree) is None, \
        "a grader disagreement did not make the metric incomplete"
    agreed = presence_disagreement(gold, differing, other, _META1,
                                   resolutions_a=agree,
                                   resolutions_b={("E1", 0): None})
    assert agreed is not None, "agreeing graders should yield a usable number"


def test_1139_a_grader_linked_surprise_is_not_ALSO_a_missing_twin():
    """SEQ 1139.1 — the missing-twin check must use gold left unmatched AFTER
    valid rulings, not the raw pre-grader set.

    Reproduced by Codex as `matched=1, recall=1.0, wrong_lane=1` on ONE fact:
    the grader linked the surprise, and the same row was still charged as a
    missing surprise twin.
    """
    from scorers.score_exp5 import MEANING_FIELDS
    q = "s" * 80
    gold = {"E1": [_gold_fact(q, fact_type="surprise", item=_mut_item(
        q, driver_name="revenue_surprise", driver_state="beat",
        surprise_basis_hint="actual", comparison_baseline="consensus"),
        gold_extra={"expectation_comparison_present": True})]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="surprise", item=_mut_item(
        q, driver_name="revenue_surprise", driver_state="beat",
        surprise_basis_hint="actual", comparison_baseline="consensus",
        sentinel_class="na"))]}}          # differs -> needs a ruling to link
    V = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    linked = score_arm(gold, arm, _META1, V, route=_route_for(arm),
                       ambiguity_resolutions={("E1", 0): 0})
    assert linked["matched"] == 1, linked
    assert linked["wrong_lane"] == 0, (
        "a grader-LINKED surprise was still charged as a missing twin")
    # the genuinely unlinked control still IS a missing twin
    unlinked = score_arm(gold, {"E1": {"facts": []}}, _META1, V,
                         route=_route_for({"E1": {"facts": []}}))
    assert unlinked["wrong_lane"] >= 1, unlinked


def test_1139_duplicate_gold_is_an_inconclusive_KEY_erratum_not_model_failure():
    """SEQ 1139.2 — two identical gold rows mean the KEY is wrong. The producer
    cannot lawfully answer both, so scoring it as recall 0 blames the model for
    a defect in the answer key, and no ordinary pair ruling can fix it."""
    from scorers.score_exp5 import MEANING_FIELDS
    q = "g" * 80
    gold = {"E1": [_gold_fact(q, item=_mut_item(q)),
                   _gold_fact(q, item=_mut_item(q))]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_mut_item(q))]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(2)},
                  route=_route_for(arm))
    assert r["gold_n"] == 0, (
        f"the inconclusive duplicate group must leave the denominator: {r}")
    assert r["ambiguities_unresolved"] >= 1 and r["PASS"] is not True
    assert not any(row.get("reason") == "ruling_missing"
                   for row in r["ambiguous_rows"]), (
        "duplicate gold was sent through ordinary pair rulings: "
        f"{r['ambiguous_rows']}")
    assert any(row.get("reason") == "duplicate_gold"
               for row in r["ambiguous_rows"]), r["ambiguous_rows"]


# ---- SEQ 1140: the one-to-one ceiling and the pure key erratum ----

def _ceiling_case(n_gold, n_candidates, rulings=None):
    """`n_gold` unmatched gold rows and `n_candidates` unmatched produced rows.

    Every produced fact DIFFERS from its gold, so nothing auto-links and the
    whole set is what a grader would still have to rule on.
    """
    from scorers.score_exp5 import MEANING_FIELDS
    # The produced facts carry DIFFERENT EVIDENCE from the gold, which is a
    # lawful way to be unmatched: every route-visible field stays valid and each
    # fact is WRITTEN. Mutating a scored field instead does not work here —
    # measured, nearly every one is refused by the route (`sentinel_class` and
    # `fiscal_year` break period resolution; `conditions`, `value_text` and the
    # shape hints are rejected outright), so the run would fail on the mutation
    # rather than exercise the one-to-one ceiling this case is about.
    gq = [chr(65 + i) * 80 for i in range(n_gold)]
    pq = [chr(97 + i) * 80 for i in range(n_candidates)]
    gold = {"E1": [_gold_fact(q, item=_mut_item(q)) for q in gq]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_mut_item(q))
                            for q in pq]}}
    V = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(n_gold)}
    return score_arm(gold, arm, _META1, V, route=_route_for(arm),
                     ambiguity_resolutions=rulings)


def test_1140_unresolved_gold_WITH_enough_candidates_stays_PENDING():
    """A missing ruling CAN still become a match when an unused candidate
    exists, so the run is not yet a known failure (Codex SEQ 1140.3)."""
    r = _ceiling_case(4, 4)
    assert r["PASS"] is None, (
        f"enough candidates remain to reach the bar, so this is PENDING: {r}")


def test_1140_unresolved_gold_WITHOUT_candidates_is_a_definite_FAIL():
    """The other side: with too few candidates no grader could reach the bar,
    so the ceiling makes it a known failure rather than pending."""
    r = _ceiling_case(4, 0)
    assert r["PASS"] is False, (
        f"no candidate can repair this, so it is a DEFINITE fail: {r}")


def test_1140_an_explicit_None_ruling_earns_no_potential_credit():
    """A decided miss is decided. It must not be counted as still-repairable."""
    r = _ceiling_case(4, 4, rulings={("E1", i): None for i in range(4)})
    assert r["PASS"] is False, (
        f"explicit None rulings are decided misses, not potential matches: {r}")


def test_1140_a_pure_duplicate_key_erratum_is_None_not_False():
    """SEQ 1140.2 — when the ONLY problem is a broken answer key, there is
    nothing to conclude about the model, so the verdict is INCONCLUSIVE."""
    from scorers.score_exp5 import MEANING_FIELDS
    q = "g" * 80
    gold = {"E1": [_gold_fact(q, item=_mut_item(q)),
                   _gold_fact(q, item=_mut_item(q))]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_mut_item(q))]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(2)},
                  route=_route_for(arm))
    assert r["gold_n"] == 0 and r["PASS"] is None, (
        f"a pure key erratum must be INCONCLUSIVE, not a model failure: {r}")


def test_1140_a_real_hard_failure_still_returns_False():
    """The independent control: the erratum exemption must not swallow a
    genuine failure that happens to sit beside it."""
    from scorers.score_exp5 import MEANING_FIELDS
    # duplicate-gold erratum PLUS two gold rows no candidate can ever answer.
    # The one produced fact matches its own gold exactly, so nothing is left
    # free to repair the other two — the ceiling is 1/3, a known failure.
    q, m, x, y = "g" * 80, "m" * 80, "x" * 80, "y" * 80
    gold = {"E1": [_gold_fact(q, item=_mut_item(q)),
                   _gold_fact(q, item=_mut_item(q)),
                   _gold_fact(m, item=_mut_item(m)),
                   _gold_fact(x, item=_mut_item(x)),
                   _gold_fact(y, item=_mut_item(y))]}
    arm = {"E1": {"facts": [_v2_fact(m, fact_type="metric", item=_mut_item(m))]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(5)},
                  route=_route_for(arm))
    assert r["PASS"] is False, (
        f"unanswerable gold beside the erratum must still FAIL: {r}")


def test_1140_a_gold_linked_abstention_does_NOT_answer_a_surprise_twin():
    """SEQ 1140.1 — an abstention is a park AND a recall non-match, so it never
    supplies the required surprise twin."""
    from scorers.score_exp5 import MEANING_FIELDS
    q = "s" * 80
    _lq, part, occ = _v2_locator()
    gold = {"E1": [_gold_fact(q, fact_type="surprise", item=_mut_item(
        q, driver_name="revenue_surprise", driver_state="beat",
        surprise_basis_hint="actual", comparison_baseline="consensus"),
        gold_extra={"expectation_comparison_present": True})]}
    arm = {"E1": {"facts": [],
                  "abstentions": [{"quote": q, "part_ref": part,
                                   "occurrence_in_part": occ,
                                   "reason": "insufficient evidence"}]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", 0): {k: True for k in MEANING_FIELDS}},
                  route=_route_for(arm))
    assert r["wrong_lane"] >= 1, (
        f"an abstention answered the surprise twin it must not answer: {r}")


def _two_event_case(a_gold, a_prod, b_gold, b_prod):
    """Two events, each with its own gold/produced counts. Produced facts carry
    DIFFERENT evidence from gold, so nothing auto-links."""
    from scorers.score_exp5 import MEANING_FIELDS
    gold, arm, verdicts = {}, {}, {}
    for sid, (ng, npd), base in (("E1", (a_gold, a_prod), 65),
                                 ("E2", (b_gold, b_prod), 97)):
        gq = [chr(base + i) * 80 for i in range(ng)]
        pq = [chr(base + 10 + i) * 80 for i in range(npd)]
        gold[sid] = [_gold_fact(q, item=_mut_item(q)) for q in gq]
        arm[sid] = {"facts": [_v2_fact(q, fact_type="metric", item=_mut_item(q))
                              for q in pq]}
        for i in range(ng):
            verdicts[(sid, i)] = {k: True for k in MEANING_FIELDS}
    meta = {sid: {"event_date": "2026-04-23", "fye_month": 12} for sid in gold}
    return score_arm(gold, arm, meta, verdicts, route=_route_for(arm))


def test_1141_a_spare_candidate_in_ANOTHER_event_cannot_raise_the_ceiling():
    """SEQ 1141 — matching is SAME-EVENT (WorkOrder EXP-5 point 1).

    E1 has 4 unmatched gold and NO candidate; E2 has 0 gold and 4 spare
    candidates. Accumulating the two sides separately and taking one global
    `min` made those spares repair E1's gap — a pair no grader can ever make.
    """
    r = _two_event_case(4, 0, 0, 4)
    assert r["PASS"] is False, (
        f"a cross-event candidate raised the ceiling: {r}")


def test_1141_a_SAME_event_candidate_still_raises_the_ceiling():
    """The counter-control: the fix must not simply refuse every repair."""
    r = _two_event_case(4, 4, 0, 0)
    assert r["PASS"] is None, (
        f"a same-event candidate must still keep this PENDING: {r}")


# ---- step3 §4: TWO separate, exact, deterministic, DISABLED launch plans ----

def _plan(name):
    with open(os.path.join(_REPO, ".claude", "plans", "Drivers", "experiments",
                           "harness", name), encoding="utf-8") as fh:
        return json.load(fh)


def test_step3_4_both_launch_plans_are_exact_and_DISABLED():
    """The WorkOrder-owned counts, and neither plan may have made a call."""
    kf = _plan("launch_kfields_drafts.manifest.json")
    rd = _plan("launch_exp5_readers.manifest.json")
    assert kf["n_events"] == 36 and kf["n_workers"] == 72, kf["n_workers"]
    assert rd["planned_producer_calls"] == 156, rd["planned_producer_calls"]
    for p in (kf, rd):
        assert p["made_calls"] == 0, "a DISABLED plan has made a call"


def test_step3_4_the_two_plans_are_SEPARATE_and_neither_launches_the_other():
    """§4: separate approvals, separate manifests, neither may launch the other.

    The reader plan names the K-fields file exactly once, inside its own
    `separation` prose declaring the boundary — that is a statement, not a
    launch path. Asserted precisely so a real cross-reference elsewhere in the
    document would still fail.
    """
    rd = _plan("launch_exp5_readers.manifest.json")
    kf = _plan("launch_kfields_drafts.manifest.json")
    assert "launch_exp5" not in json.dumps(kf), "K-fields references the reader plan"
    hits = [k for k, v in rd.items()
            if "launch_kfields" in json.dumps(v)]
    assert hits == ["separation"], f"reader plan references K-fields in {hits}"


def test_step3_4_the_opus_ref_subsample_is_h32_LAW_not_a_choice():
    """WorkOrder:172 — all sampling is an h32-seeded deterministic shuffle with
    the seed recorded. The selection must be reproducible from the manifest
    alone, using the EXISTING `key_lint.h32` owner."""
    from key_lint import h32
    rd = _plan("launch_exp5_readers.manifest.json")
    sub = rd["opus_ref_subsample"]
    assert sub["n"] == 12 and sub["seed"], sub
    ids = [e["source_id"] for e in rd["events"]]
    ordered = sorted(ids, key=lambda sid: (h32(sub["seed"] + sid), sid))
    assert sorted(ordered[:12]) == sub["source_ids"], (
        "the recorded subsample is not what the recorded seed produces")


def test_step3_4_runtime_model_IDS_are_NOT_frozen():
    """§4: pin the ROLES; never freeze an alias as though it were the final ID."""
    rd = _plan("launch_exp5_readers.manifest.json")
    assert rd["model_resolution"]["pinned"] == "ROLES ONLY", rd["model_resolution"]
    assert rd["conditional_cheap_fallback"]["enabled"] is False
    assert "P6 local-Qwen" in rd["withdrawn"]
    assert rd["grading"]["exact_count"] is None, (
        "an invented exact grading count was frozen into the plan")


# ---- step3 §11: score boundaries and union tier rules ----

def _at_recall(n_gold, n_matched):
    """`n_gold` gold rows of which `n_matched` are answered EXACTLY, so recall is
    a chosen fraction and every other axis stays clean."""
    from scorers.score_exp5 import MEANING_FIELDS
    qs = [chr(65 + i) * 80 for i in range(n_gold)]
    gold = {"E1": [_gold_fact(q, item=_mut_item(q)) for q in qs]}
    facts = [_v2_fact(qs[i], fact_type="metric", item=_mut_item(qs[i]))
             for i in range(n_matched)]
    arm = {"E1": {"facts": facts}}
    V = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(n_gold)}
    return score_arm(gold, arm, _META1, V, route=_route_for(arm),
                     ambiguity_resolutions={("E1", i): None
                                            for i in range(n_matched, n_gold)})


@pytest.mark.parametrize("n_gold,n_matched,recall,expect", [
    (20, 18, 0.90, False),   # immediately BELOW the 0.95 bar
    (20, 19, 0.95, True),    # exactly AT it
    (20, 20, 1.00, True),    # ABOVE
])
def test_step3_11_recall_boundary_below_at_and_above(n_gold, n_matched, recall,
                                                     expect):
    """The official bar is `recall >= 0.95`. A `>` would fail an exactly-at-bar
    run and a `>=` on the wrong side would pass one below it, so all three
    points are pinned. Unanswered gold carries an explicit `None` ruling — a
    DECIDED miss — so the run is complete and the bar is what decides it.
    """
    r = _at_recall(n_gold, n_matched)
    assert r["recall"] == recall, r["recall"]
    assert (r["PASS"] is True) is expect, (
        f"recall {recall} against the 0.95 bar returned {r['PASS']!r}")


def test_step3_11_a_cross_tier_union_is_REFUSED():
    """Same-tier unions ONLY. Unioning a stronger arm into a weaker one would
    report a recall the weaker tier never achieved."""
    from scorers.score_exp5 import score_union, union_answer
    q = "u" * 80
    gold = {"E1": [_gold_fact(q, item=_mut_item(q))]}
    a = {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_mut_item(q))]}}
    b = {"E1": {"facts": []}}
    route = _route_for(union_answer(gold, a, b))
    with pytest.raises(ValueError):
        score_union(gold, a, b, _META1, route=route, tiers=("haiku", "opus"))


def test_step3_11_a_same_tier_union_is_ALLOWED():
    """The counter-control: the refusal must not block the lawful case."""
    from scorers.score_exp5 import score_union, union_answer, MEANING_FIELDS
    q = "u" * 80
    gold = {"E1": [_gold_fact(q, item=_mut_item(q))]}
    a = {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_mut_item(q))]}}
    b = {"E1": {"facts": []}}
    route = _route_for(union_answer(gold, a, b))
    r = score_union(gold, a, b, _META1,
                    {("E1", 0): {k: True for k in MEANING_FIELDS}},
                    route=route, tiers=("sonnet", "sonnet"))
    assert r["recall"] == 1.0, r


def test_step3_11_the_reader_plan_pins_a_tier_on_every_arm():
    """The tier labels the union rule compares are PINNED per arm in the plan,
    so a union can be checked against the approved plan rather than caller
    memory."""
    rd = _plan("launch_exp5_readers.manifest.json")
    assert all(a.get("tier") for a in rd["arms"]), rd["arms"]
    assert rd["unions"] == "same-tier only", rd["unions"]


def test_step3_5_the_reader_plan_binds_every_required_identity():
    """§5 lists exactly what a disabled plan must bind. Checked by NAME against
    that list, so a silently dropped pin fails rather than going unnoticed."""
    rd = _plan("launch_exp5_readers.manifest.json")
    required = {
        "workorder", "core_foundation", "staged_v2_contract",
        "step2_builder", "step2_instruction_producer", "step2_contract_manifest",
        "step2_checker", "reply_transport", "matcher", "scorer", "core_route",
        "launcher_template", "tests"}
    required |= {"launcher_generated"}
    got = set(rd["identities"])
    assert required <= got, f"unbound identities: {sorted(required - got)}"
    for name, ident in rd["identities"].items():
        # {path, sha256}, not a bare hash — the live-bytes control below checks
        # each one actually matches the file it names
        assert set(ident) == {"path", "sha256"}, (name, ident)
        assert len(ident["sha256"]) == 64, (name, ident)


def test_step3_5_no_credential_machine_path_or_self_hash_is_bound():
    """§5: exclude credentials, machine paths, volatile values, and
    self-referential hashes. The manifest must never hash itself."""
    import hashlib
    path = os.path.join(_REPO, ".claude", "plans", "Drivers", "experiments",
                        "harness", "launch_exp5_readers.manifest.json")
    raw = open(path, "rb").read()
    own = hashlib.sha256(raw).hexdigest()
    body = raw.decode("utf-8")
    assert own not in body, "the manifest binds its OWN hash (self-referential)"
    assert "/home/" not in body and "sk-" not in body, "machine path or key bound"
    rd = json.loads(body)
    for e in rd["events"]:
        assert not os.path.isabs(e["input_path"]), e["input_path"]


def test_step3_5_the_kfields_lock_is_NULL_not_a_placeholder():
    """§5: the future lock does not exist yet. A final-looking placeholder is
    exactly how an unreviewed lock gets accepted as reviewed, so it must be
    NULL and the runner must refuse to start without the real one."""
    rd = _plan("launch_exp5_readers.manifest.json")
    lock = rd["kfields_lock"]
    assert lock["sha256"] is None, f"a placeholder lock was frozen: {lock}"
    assert "REFUSES TO START" in lock["runner_rule"], lock


def test_step3_5_every_arm_pins_role_effort_tier_and_active_state():
    """§5: model roles, effort, exact active/disabled arms, planned calls."""
    rd = _plan("launch_exp5_readers.manifest.json")
    for a in rd["arms"]:
        for k in ("arm", "role", "tier", "effort", "active", "scope"):
            assert k in a, (k, a)
    assert rd["output"]["no_overwrite"], rd["output"]
    assert rd["made_calls"] == 0


@pytest.mark.parametrize("axis,bar,direction", [
    ("recall", 0.95, "min"),
    ("value_shape_acc", 0.98, "min"),
    ("state_acc", 0.95, "min"),
    ("would_park", 0.10, "max"),
])
def test_step3_11_every_official_bar_is_inclusive_at_its_threshold(axis, bar,
                                                                   direction):
    """§11: each score boundary immediately BELOW, AT, and ABOVE its threshold.

    Driven through the SCORER'S OWN `passes_official_bars`, which `score_arm`
    calls — not a copy of the expression. An earlier version restated the gate
    inside this test and guarded it with a source-text search; Codex SEQ 1143
    rejected that correctly, because a copied expression is a second rule owner
    that can agree with itself while the scorer behaves differently, and a text
    search cannot tell a live fragment from a dead or reordered one.

    The recall bar is ALSO proven end-to-end through the real pipeline above;
    this pins the comparison at every bar, which fixtures cannot reach exactly.
    """
    from scorers.score_exp5 import passes_official_bars
    clean = {"recall": 0.99, "lane_wrong": 0, "wrong_name": 0,
             "value_shape_acc": 1.0, "state_acc": 1.0, "would_park": 0.0,
             "safety_result": "PASS"}
    eps = 0.01
    below = bar - eps if direction == "min" else bar + eps
    above = bar + eps if direction == "min" else bar - eps
    for value, expect in ((below, False), (bar, True), (above, True)):
        assert passes_official_bars(**{**clean, axis: value}) is expect, (
            f"{axis}={value} against its {bar} bar returned {not expect}")


def test_step3_11_score_arm_uses_that_same_bar_owner():
    """The owner must be the one `score_arm` actually calls, proven by
    BEHAVIOUR: monkeypatching it to refuse must flip a passing run."""
    from scorers import score_exp5
    gold, arm = _surprise_gold_and_arm()
    route = _route_for(arm)
    real = score_exp5.passes_official_bars
    try:
        score_exp5.passes_official_bars = lambda **_kw: False
        forced = score_arm(gold, arm, _META1, _full_verdicts(), route=route)
    finally:
        score_exp5.passes_official_bars = real
    assert forced["PASS"] is not True, (
        "score_arm reached PASS without consulting the bar owner")


def test_step3_5_the_reader_launcher_executes_its_EXACT_156_schedule():
    """§5/§11 — the generated reader launcher must be EXECUTABLE with fake
    agents and prove its exact arm/event schedule, including P5's 12-event
    restriction (Codex SEQ 1145).

    Runs the REAL generated launcher against fake `agent`/`pipeline`/`parallel`
    hooks. No model is contacted: the fake agent records its options and returns
    a constant, so this proves the SCHEDULE, never a reply.
    """
    import subprocess
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is unavailable in this environment")
    got = _fake_reader_run(_LAWFUL_RUN_INPUTS)
    assert got["ok"] and got["total"] == got["planned"] == 156, got
    assert got["byArm"] == {"P1": 36, "P2": 36, "P3": 36, "P4": 36, "P5": 12}, got
    assert got["agentTypes"] == ["lean-probe"], got
    # the EXACT runtime IDs supplied as run inputs reach the agent — never the
    # aliases, which start gate 2 refuses
    assert len(got["models"]) == 3 and not (
        {"haiku", "opus", "sonnet"} & set(got["models"])), got["models"]


def test_step3_5_every_identity_names_a_path_and_matches_its_LIVE_bytes():
    """§5.3 — a bare hash cannot be re-checked against the file it names. Every
    identity is `{path, sha256}` and is recomputed here from the live bytes."""
    import hashlib
    rd = _plan("launch_exp5_readers.manifest.json")
    for name, ident in rd["identities"].items():
        assert set(ident) == {"path", "sha256"}, (name, ident)
        assert not os.path.isabs(ident["path"]), (name, ident["path"])
        real = hashlib.sha256(
            open(os.path.join(_REPO, ident["path"]), "rb").read()).hexdigest()
        assert real == ident["sha256"], (
            f"{name} binds {ident['path']} at a hash that is not its live bytes")


def test_step3_5_the_launcher_bound_is_the_READER_one_not_the_draft_one():
    """§5.1 — the K-fields template hardcodes 36 x (sonnet+opus) = 72 gold
    drafts and cannot express P1-P5, so pinning it was pinning the wrong
    launcher. Both the template AND the generated launcher are bound."""
    rd = _plan("launch_exp5_readers.manifest.json")
    for key in ("launcher_template", "launcher_generated"):
        path = rd["identities"][key]["path"]
        assert "exp5_readers" in path, f"{key} names {path}"
        assert "kfields" not in path, f"{key} still names the draft launcher"


def test_step3_5_every_reader_event_carries_its_assembled_PRODUCER_prompt():
    """§5 — the exact prompt for every event, built from the PRODUCER
    instruction, not the drafter's."""
    import hashlib
    rd = _plan("launch_exp5_readers.manifest.json")
    kf = _plan("launch_kfields_drafts.manifest.json")
    assert len(rd["events"]) == 36
    for e in rd["events"]:
        assert len(e["prompt_sha256"]) == 64, e
    reader = {e["source_id"]: e["prompt_sha256"] for e in rd["events"]}
    drafter = {e["source_id"]: e["prompt_sha256"] for e in kf["events"]}
    assert set(reader) == set(drafter)
    assert all(reader[s] != drafter[s] for s in reader), (
        "the reader plan pinned the DRAFTER prompts")


# ---- step3 §5: the runner's TWO START GATES (Codex SEQ 1147) ----

_TEST_LOCK = "a" * 64
#: EXACT-looking runtime IDs supplied as RUN INPUTS. Nothing is frozen into the
#: plan — the manifest still pins ROLES only; these exist to prove the gate
#: accepts exact IDs and refuses aliases.
_LAWFUL_RUN_INPUTS = [
    f"--plan-lock={_TEST_LOCK}", f"--lock={_TEST_LOCK}",
    "--id-sonnet=claude-sonnet-5-20260101",
    "--id-haiku=claude-haiku-4-5-20251001",
    "--id-opus=claude-opus-5-20260101",
]


def _fake_reader_run(extra):
    """Run the GENERATED reader launcher against fake agents. No model is
    contacted; the fake agent records its options and returns a constant."""
    import subprocess
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is unavailable in this environment")
    out = subprocess.run(
        [node, os.path.join(_HERE, "run_reader_launcher_fake.mjs"),
         os.path.join(_HERE, "launch_exp5_readers.workflow.js"),
         os.path.join(_HERE, "launch_exp5_readers.manifest.json")] + list(extra),
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("extra,fragment", [
    (["--bare-args"], "has not been reviewed"),
    ([f"--plan-lock={_TEST_LOCK}"], "no K-fields lock supplied"),
    ([f"--plan-lock={_TEST_LOCK}", "--lock=" + "b" * 64,
      "--id-sonnet=x", "--id-haiku=y", "--id-opus=z"], "does not match"),
    ([f"--plan-lock={_TEST_LOCK}", f"--lock={_TEST_LOCK}"],
     "no exact runtime model ID"),
    ([f"--plan-lock={_TEST_LOCK}", f"--lock={_TEST_LOCK}",
      "--id-sonnet=sonnet", "--id-haiku=haiku", "--id-opus=opus"],
     "ALIAS, not an exact runtime ID"),
])
def test_step3_5_the_runner_REFUSES_before_the_first_call(extra, fragment):
    """SEQ 1147 — both gates were PROSE ONLY, and my own fake run disproved the
    claimed one by completing all 156 calls with a null lock.

    Every refusal must happen BEFORE the first agent call, so `calls == 0` is
    asserted alongside the reason: a runner that refuses after spending the
    first call has already done the thing the gate exists to prevent.
    """
    got = _fake_reader_run(extra)
    assert got["ok"] is False, got
    assert fragment in got["refused"], got["refused"]
    assert got["calls"] == 0, f"the gate fired AFTER {got['calls']} calls"


def test_step3_5_a_lawful_run_input_set_still_yields_the_exact_156():
    """The positive control: the gates must not simply refuse everything, and
    the exact runtime IDs — not the aliases — are what reach the agent."""
    got = _fake_reader_run(_LAWFUL_RUN_INPUTS)
    assert got["ok"] and got["total"] == 156, got
    assert got["byArm"] == {"P1": 36, "P2": 36, "P3": 36, "P4": 36, "P5": 12}
    for alias in ("sonnet", "haiku", "opus"):
        assert alias not in got["models"], f"an ALIAS reached the agent: {alias}"


def test_step3_5_the_committed_plan_still_carries_NO_lock_and_NO_frozen_ids():
    """The gates are exercised with SUPPLIED run inputs and a TEMPORARY
    plan-lock rewrite. Nothing may leak into the committed plan: the lock stays
    null and only ROLES stay pinned (§5 — never freeze an alias or an ID)."""
    rd = _plan("launch_exp5_readers.manifest.json")
    assert rd["kfields_lock"]["sha256"] is None, rd["kfields_lock"]
    assert rd["model_resolution"]["pinned"] == "ROLES ONLY"
    body = json.dumps(rd)
    for frozen in ("claude-sonnet-5", "claude-haiku-4", "claude-opus-5",
                   _TEST_LOCK):
        assert frozen not in body, f"{frozen} was frozen into the plan"
    src = open(os.path.join(_HERE, "launch_exp5_readers.workflow.js"),
               encoding="utf-8").read()
    assert "const KFIELDS_LOCK_SHA256 = null" in src, (
        "the committed launcher carries a lock value")


# ---- step3 §6: the two remaining fake-reply cases ----

def test_step3_6_an_INTERRUPTED_batch_keeps_every_reply_it_already_paid_for():
    """§6 — a batch that stops partway is MISSING rows, which must be refused;
    but the replies already received were PAID FOR and must survive on disk.

    An interrupted run is the ordinary failure of a long paid job. Losing the
    completed half because the batch was incomplete would turn one interruption
    into a second, larger cost.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        res = _full_result(_reply_for)
        kept = res["results"][:5]                 # the batch died after 5 events
        res["results"] = kept
        out = RT.ingest_workflow_result(res, td, validate=False)
        assert not out["ok"], "an incomplete batch must be refused"
        assert any("MISSING" in e for e in out["errors"]), out["errors"]
        for row in kept:
            for arm in RT.ARMS:
                p = os.path.join(td, f"{row['source_id']}.{arm}.raw.json")
                assert os.path.exists(p), (
                    f"an interrupted batch lost the PAID reply {p}")


@pytest.mark.parametrize("literal", [
    "1" + "0" * 400,                       # far beyond float range
    "1e-400",                              # underflows a float to 0.0
    "0.1000000000000000000000000000001",   # more digits than a float can hold
    "-1" + "0" * 400,
])
def test_step3_6_extreme_magnitudes_survive_the_exact_parse(literal):
    """§6 — very large/small values must reach Python with their digits intact.

    A float would render the first as `inf`, the second as `0.0`, and round the
    third — each one silently, and each one a WRONG number rather than a
    failure. The exact parse keeps the source digits, which is the whole reason
    this path refuses `schema:` in the launcher.
    """
    from decimal import Decimal
    doc = RT.parse_exact('{"v": ' + literal + '}')
    # AN INTEGER LITERAL BECOMES A PYTHON `int`, and that is CORRECT: `int` is
    # arbitrary-precision, so nothing is lost and `parse_float=Decimal` is not
    # meant to touch it. Only float-shaped literals need Decimal. Asserting
    # Decimal for everything failed here — my assertion was wrong, not the
    # parser.
    is_float_shaped = "." in literal or "e" in literal.lower()
    assert isinstance(doc["v"], Decimal if is_float_shaped else int), (
        literal, type(doc["v"]))
    assert Decimal(str(doc["v"])) == Decimal(literal), (str(doc["v"]), literal)
    # and the float path WOULD have destroyed it — proven, not asserted
    as_float = float(literal)
    assert (as_float in (float("inf"), float("-inf"), 0.0)
            or Decimal(repr(as_float)) != Decimal(literal)), (
        f"{literal} does not actually demonstrate float loss")


# ---- step3 §6: the READER launcher's own result shape (Codex SEQ 1150/1151) ----

def _reader_rows(text_for=None):
    """The reader launcher's REAL return shape: one row per CALL."""
    man = _plan("launch_exp5_readers.manifest.json")
    sub = set(man["opus_ref_subsample"]["source_ids"])
    out = []
    for a in man["arms"]:
        for e in man["events"]:
            if a["scope"] == "all_36" or e["source_id"] in sub:
                sid = e["source_id"]
                out.append({"arm": a["arm"], "source_id": sid,
                            # real launcher rows carry their prompt evidence,
                            # and the ingestion boundary now requires it
                            "prompt_sha256": e["prompt_sha256"],
                            "text": (text_for(sid, a["arm"]) if text_for
                                     else json.dumps({"source_id": sid}))})
    return out


_READER_MANIFEST = None


def _reader_ingest(rows, tmp_path):
    global _READER_MANIFEST
    _READER_MANIFEST = os.path.join(_HERE, "launch_exp5_readers.manifest.json")
    return RT.ingest_workflow_result({"results": rows}, str(tmp_path),
                                     manifest_path=_READER_MANIFEST,
                                     validate=False)


def test_step3_6_the_reader_launchers_156_replies_ALL_ingest(tmp_path):
    """SEQ 1150 — the transport hardcoded `ARMS=("sonnet","opus")` and one row
    per EVENT, so the reader's 156 per-CALL rows came back as 432 errors with
    every repeated event read as a duplicate. Reproduced before fixing."""
    rows = _reader_rows()
    assert len(rows) == 156
    out = _reader_ingest(rows, tmp_path)
    assert out["ok"], out["errors"][:5]
    assert len(out["docs"]) == 156, len(out["docs"])


@pytest.mark.parametrize("mutate,fragment", [
    (lambda r: r[1:], "MISSING scheduled reply"),
    (lambda r: r + [dict(r[0])], "DUPLICATE reply"),
    (lambda r: [dict(r[0], arm="P9")] + r[1:], "UNEXPECTED reply"),
    (lambda r: [dict(r[0], source_id="NOT-AN-EVENT")] + r[1:],
     "UNEXPECTED reply"),
])
def test_step3_6_schedule_attacks_refuse_without_losing_raw(mutate, fragment,
                                                            tmp_path):
    """Every attack is measured against the PLAN'S OWN schedule, and every reply
    that arrived is still on disk — each one was paid for."""
    rows = mutate(_reader_rows())
    out = _reader_ingest(rows, tmp_path)
    assert not out["ok"], "the attack was accepted"
    assert any(fragment in e for e in out["errors"]), out["errors"][:4]
    written = sum(1 for _r, _d, files in os.walk(str(tmp_path))
                  for _f in files)
    assert written >= len(rows), (
        f"only {written} raw files kept for {len(rows)} received replies")


def test_step3_6_the_kfields_plan_still_ingests_lawfully(tmp_path):
    """The positive control for the OLD shape: generalising the transport must
    not break the plan it already served."""
    out = RT.ingest_workflow_result(_full_result(_reply_for), str(tmp_path),
                                    validate=False)
    assert out["ok"], out["errors"][:5]


def test_step3_6_every_checked_reply_is_bound_to_event_arm_run_and_manifest(
        tmp_path):
    """SEQ 1151 — a doc that cannot name its run or its plan cannot be audited
    later."""
    import hashlib
    out = _reader_ingest(_reader_rows(), tmp_path)
    (sid, arm), rec = sorted(out["docs"].items())[0]
    assert rec["source_id"] == sid and rec["arm"] == arm
    assert rec["run"] == os.path.basename(str(tmp_path))
    assert rec["manifest_path"].endswith("launch_exp5_readers.manifest.json")
    assert not os.path.isabs(rec["manifest_path"])
    real = hashlib.sha256(open(_READER_MANIFEST, "rb").read()).hexdigest()
    assert rec["manifest_sha256"] == real
    assert os.path.exists(rec["raw_path"]) and len(rec["raw_sha256"]) == 64


# `test_step3_6_an_invalid_reply_retries_EXACTLY_once` DELETED (Codex SEQ
# 1158.4, deletion-first). It was the PARSE-ONLY surface: its "good" reply was
# `{"source_id": "E1"}`, which is valid JSON and NOT a lawful V2 reader answer,
# so it asserted the very behaviour that let off-contract output win. The real
# seam now owns all of it — off-contract, invalid bucket, wrong source, lawful
# first reply, pinned prompt, and the third-attempt refusal are each controlled
# above against the manifest door and the Step-2 checker.


def _build_in(dest):
    """Reproduce the repo layout a §5 build needs, run BOTH plan builders, and
    return {filename: sha256} for every generated artifact."""
    import subprocess
    exp = dest / ".claude" / "plans" / "Drivers" / "experiments"
    work = exp / "harness"
    shutil.copytree(_HERE, work, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    shutil.copytree(os.path.join(_HERE, "..", "keys"), exp / "keys",
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    for rel in (os.path.join(".claude", "plans", "Drivers", "FinalDesign"),
                os.path.join("driver", "core")):
        d = dest / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(os.path.join(_REPO, rel), d, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__",
                                                      ".pytest_cache"))
    names = ("launch_kfields_drafts.manifest.json",
             "launch_kfields_drafts.workflow.js",
             "launch_exp5_readers.manifest.json",
             "launch_exp5_readers.workflow.js")
    # REMOVE THE GENERATED TARGETS FIRST (Codex SEQ 1153.2). The copy brings the
    # already-built artifacts along, so two roots could agree on a STALE copy
    # the builder never recreated — the comparison would pass while the builder
    # was broken. Deleting them makes the builder prove it produces all four.
    for n in names:
        (work / n).unlink()
    subprocess.run([_REPO_VENV, str(work / "build_launch_manifest.py")],
                   check=True, capture_output=True)
    for n in names:
        assert (work / n).exists(), f"the builder did not recreate {n}"
    return work, {n: hashlib.sha256((work / n).read_bytes()).hexdigest()
                  for n in names}


def test_step3_12_two_independent_builds_are_byte_identical(tmp_path):
    """§12 — build BOTH plans twice from the same inputs in SEPARATE temporary
    locations, and require identical filenames, ordering, counts and hashes.

    Two builds in ONE directory can agree by overwriting each other; two
    separate roots cannot.
    """
    _w1, a = _build_in(tmp_path / "build_a")
    _w2, b = _build_in(tmp_path / "build_b")
    assert set(a) == set(b), (sorted(a), sorted(b))
    assert a == b, {k: (a[k][:12], b[k][:12]) for k in a if a[k] != b[k]}
    for root in (_w1, _w2):
        rd = json.loads((root / "launch_exp5_readers.manifest.json").read_text())
        kf = json.loads((root / "launch_kfields_drafts.manifest.json").read_text())
        assert rd["planned_producer_calls"] == 156 and rd["made_calls"] == 0
        assert kf["n_workers"] == 72 and kf["made_calls"] == 0
        assert [e["source_id"] for e in rd["events"]] == \
               [e["source_id"] for e in kf["events"]], "event ORDER diverged"


@pytest.mark.parametrize("cls,rel,mutate", [
    ("source", "keys/K-fields/draft_inputs/{first_input}", "bytes"),
    ("prompt", "harness/exp5_prompt_producer.md", "bytes"),
    ("contract", "harness/exp5_prompt_contract.manifest.json", "bytes"),
    ("scorer", "harness/scorers/score_exp5.py", "bytes"),
    ("model_setting", "harness/build_launch_manifest.py", "effort"),
    ("writes_disabled", "harness/build_launch_manifest.py", "made_calls"),
])
def test_step3_12_the_gate_detects_a_mutation_in_every_protected_class(
        cls, rel, mutate, tmp_path):
    """§12 — mutate ONE representative member of each protected class and prove
    the existing gate notices. A build that produces identical artifacts after a
    protected file changed would mean the plan is not really bound to it."""
    work_clean, clean = _build_in(tmp_path / "clean")
    work_dirty, _ = _build_in(tmp_path / "dirty")
    exp = work_dirty.parent
    if "{first_input}" in rel:
        inputs = exp / "keys" / "K-fields" / "draft_inputs"
        first = sorted(p.name for p in inputs.iterdir() if p.suffix == ".json")[0]
        rel = rel.replace("{first_input}", first)
    target = exp / rel
    assert target.exists(), target
    if mutate == "bytes" and target.suffix == ".json":
        # A JSON source must stay PARSEABLE: appending a comment made the build
        # crash instead of producing different artifacts, which proves nothing
        # about binding. Re-serialising with an extra key changes the bytes
        # while keeping the file lawful.
        doc = json.loads(target.read_text())
        doc["_mutation_marker"] = True
        target.write_text(json.dumps(doc, sort_keys=True))
    elif mutate == "bytes":
        target.write_text(target.read_text() + "\n<!-- mutated -->\n")
    elif mutate == "effort":
        target.write_text(target.read_text().replace('"effort": "high"',
                                                     '"effort": "low"'))
    else:
        target.write_text(target.read_text().replace(
            '"made_calls": 0,          # DISABLED', '"made_calls": 1,          # DISABLED'))
    import subprocess
    subprocess.run([_REPO_VENV, str(work_dirty / "build_launch_manifest.py")],
                   check=True, capture_output=True)
    dirty = {n: hashlib.sha256((work_dirty / n).read_bytes()).hexdigest()
             for n in clean}
    assert dirty != clean, (
        f"a {cls} mutation produced BYTE-IDENTICAL artifacts — the plan is not "
        f"bound to {rel}")


def test_step3_6_scheduled_replies_reach_the_authoritative_V2_checker(tmp_path):
    """SEQ 1153.1 — the scheduled path accepted `validate`/`inputs_dir` and used
    NEITHER, so a schedule-complete, parseable but V2-INVALID reader reply
    returned `ok=True`. Reproduced before fixing.

    The door comes from the BOUND MANIFEST, never a caller argument, and the arm
    population comes from the schedule — which already proves P5's 12-event
    subset — so no arm name is written here.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    sub = set(man["opus_ref_subsample"]["source_ids"])

    def rows(make):
        return [{"arm": a["arm"], "source_id": e["source_id"],
                 "text": make(e["source_id"])}
                for a in man["arms"] for e in man["events"]
                if a["scope"] == "all_36" or e["source_id"] in sub]

    # parseable, schedule-complete, NOT a lawful V2 reply
    bad = rows(lambda s: json.dumps({"source_id": s, "nonsense": True}))
    out = _reader_ingest_validated(bad, tmp_path / "invalid")
    assert not out["ok"] and out["errors"], "an invalid V2 reply was admitted"
    # ...and every paid reply is still on disk, saved BEFORE validation
    kept = sum(len(f) for _r, _d, f in os.walk(str(tmp_path / "invalid")))
    assert kept == len(bad), f"{kept} raw files kept for {len(bad)} replies"

    # a reply that never says WHICH event it answers cannot be bound to one
    anon = rows(lambda _s: json.dumps({"facts": [], "abstentions": []}))
    out2 = _reader_ingest_validated(anon, tmp_path / "anon")
    assert not out2["ok"], "a reply with no inner source_id was admitted"
    assert any("WRONG EVENT" in e for e in out2["errors"]), out2["errors"][:3]


def _reader_ingest_validated(rows, out_dir):
    os.makedirs(str(out_dir), exist_ok=True)
    return RT.ingest_workflow_result(
        {"results": rows}, str(out_dir),
        manifest_path=os.path.join(_HERE, "launch_exp5_readers.manifest.json"),
        validate=True)


def test_step3_3_the_OD11_contingency_is_recorded_DISABLED_in_both_plans():
    """§3 / completion — "all 36 events AND the disabled contingency are
    accounted for". An absence cannot be audited, so the disabled state is a
    RECORDED FACT in both artifacts.

    It may be PROPOSED only after later drafting finds fewer than the official
    number of sequential-basis facts, and then needs a new versioned record.
    No general substitution engine exists.
    """
    for name in ("launch_kfields_drafts.manifest.json",
                 "launch_exp5_readers.manifest.json"):
        plan = _plan(name)
        c = plan["od11_contingency"]
        assert c["enabled"] is False, (name, c)
        assert c["substitution_engine"] is None, (name, c)
        assert c["may_be_proposed_only_if"] and c["then_requires"], (name, c)
        assert plan["n_events"] == 36, name


# ---- step3 §3: the finite event population, ALL 36, not a sample ----

def _all_inputs():
    import build_launch_manifest as B
    out = []
    for fn in sorted(os.listdir(B.INPUTS)):
        if fn.endswith(".json"):
            with open(os.path.join(B.INPUTS, fn), encoding="utf-8") as fh:
                out.append((fn, json.load(fh)))
    return out


def test_step3_3_every_events_internal_id_matches_its_filename():
    """§3 — "unique source ID and MATCHING INTERNAL ID". A file whose inner id
    disagrees with its name would be scored against the wrong event while every
    hash and path still looked right."""
    seen = set()
    inputs = _all_inputs()
    assert len(inputs) == 36, len(inputs)
    for fn, doc in inputs:
        assert doc["source_id"] == fn[:-5], (fn, doc["source_id"])
        assert doc["source_id"] not in seen, f"duplicate source id {doc['source_id']}"
        seen.add(doc["source_id"])


def test_step3_3_source_parts_are_complete_ordered_and_stably_referenced():
    """§3 — complete ordered source parts and STABLE part references.

    Stability is what the whole evidence locator rests on: `part_ref` names a
    part, so a duplicated or empty part id makes two different pieces of text
    indistinguishable, and a locator can then point at the wrong evidence while
    still verifying.
    """
    for fn, doc in _all_inputs():
        parts = doc["text_parts"]
        assert parts, f"{fn}: no text parts"
        ids = [p["part"] for p in parts]
        assert all(isinstance(i, str) and i.strip() for i in ids), (fn, ids)
        assert len(set(ids)) == len(ids), f"{fn}: duplicate part ids {ids}"
        assert all(isinstance(p.get("content"), str) for p in parts), fn
        # ORDER is a property of the stored list and must survive a reload
        import build_launch_manifest as B
        with open(os.path.join(B.INPUTS, fn), encoding="utf-8") as fh:
            again = json.load(fh)
        assert [q["part"] for q in again["text_parts"]] == ids, f"{fn}: order drift"


def test_step3_3_the_menu_is_point_in_time_and_carries_no_prohibited_leakage():
    """§3 — a lawful point-in-time menu and NO prohibited leakage.

    The producer view is built from a FIXED key set; anything outside it cannot
    reach a worker. This asserts the inputs themselves carry none of the banned
    classes, so the restriction is not the only thing standing between a
    producer and future information.
    """
    banned = {"gold", "gold_item", "du_worthy", "returns", "realized_return",
              "future", "xbrl_facts", "answer", "label"}
    for fn, doc in _all_inputs():
        leaked = banned & set(doc)
        assert not leaked, f"{fn}: prohibited key(s) {sorted(leaked)}"
        assert isinstance(doc.get("menu_tokens"), list), fn
        # the menu is POINT-IN-TIME: it is recorded with the event, not derived
        # later, and its size is stated by the event itself
        assert isinstance(doc.get("menu_n_raw"), int), fn
        assert doc.get("event_date"), fn


def test_step3_6_a_LAWFUL_156_reply_run_passes_validation(tmp_path):
    """THE MISSING POSITIVE CONTROL (Codex SEQ 1154).

    My scheduled-validation test carried only malformed and missing-ID cases, so
    it could not notice that a completely LAWFUL 156-reply run also failed:
    `lint_parsed(..., arm=True)` demands the entire 36-input population, and P5
    is deliberately a 12-event subset. A gate that refuses everything is not a
    gate.

    Population ownership stays with the manifest-derived schedule — missing,
    extra and duplicate `(source_id, arm)` pairs are already refused against it —
    so the checker is asked only about CONTENT/SHAPE here. Nothing hardcodes P5,
    12, 36, or any arm name.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    sub = set(man["opus_ref_subsample"]["source_ids"])
    rows = [{"arm": a["arm"], "source_id": e["source_id"],
             "prompt_sha256": e["prompt_sha256"],
             "text": json.dumps({"source_id": e["source_id"], "facts": [],
                                 "abstentions": []})}
            for a in man["arms"] for e in man["events"]
            if a["scope"] == "all_36" or e["source_id"] in sub]
    assert len(rows) == 156
    out = _reader_ingest_validated(rows, tmp_path / "lawful")
    assert out["ok"], out["errors"][:5]
    assert len(out["docs"]) == 156, len(out["docs"])


def test_step3_9_the_would_park_formula_is_kept_EXACTLY():
    """§9 states the formula literally:

        parked emitted facts + gold-linked abstentions
        ----------------------------------------------
        deduplicated emitted facts + gold-linked abstentions

    Computed here from the four counted quantities and compared to what the
    scorer reports, so a drift in either numerator or denominator shows up as a
    number rather than as prose that still reads correctly.
    """
    from scorers.score_exp5 import MEANING_FIELDS
    q_ok, q_park, q_miss = "a" * 80, "b" * 80, "c" * 80
    _lq, part, occ = _v2_locator()
    # one lawful fact, one that PARKS (a named surprise with no home), one
    # duplicate of the lawful fact, and one gold-linked abstention
    lawful = _v2_fact(q_ok, fact_type="metric", item=_mut_item(q_ok))
    parked = _v2_fact(q_park, fact_type="surprise", item=_mut_item(
        q_park, driver_name="fuel_cost_surprise", driver_state="beat",
        surprise_basis_hint="actual", comparison_baseline="consensus"))
    gold = {"E1": [_gold_fact(q_ok, item=_mut_item(q_ok)),
                   _gold_fact(q_park, fact_type="surprise",
                              item=_mut_item(q_park,
                                             driver_name="fuel_cost_surprise",
                                             driver_state="beat",
                                             surprise_basis_hint="actual",
                                             comparison_baseline="consensus"),
                              gold_extra={"expectation_comparison_present": False}),
                   _gold_fact(q_miss, item=_mut_item(q_miss))]}
    arm = {"E1": {"facts": [lawful, dict(lawful), parked],
                  "abstentions": [{"quote": q_miss, "part_ref": part,
                                   "occurrence_in_part": occ,
                                   "reason": "insufficient evidence"}]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(3)},
                  route=_route_for(arm))

    parked_facts = sum(v for k, v in r["route_codes"].items()
                       if k.startswith("park:") and not k.startswith("park:F6")
                       or k == "park:F6")
    gold_linked = sum(v for k, v in r["route_codes"].items()
                      if k.startswith("abstained_on_gold:"))
    deduped_facts = 2          # three emitted, one an exact duplicate collapsed
    expected = ((parked_facts + gold_linked)
                / (deduped_facts + gold_linked))
    assert r["would_park"] == round(expected, 4), (
        f"formula drift: reported {r['would_park']}, formula gives {expected} "
        f"(parked={parked_facts} gold_linked={gold_linked} "
        f"deduped={deduped_facts})")
    assert gold_linked == 1, r["route_codes"]


# ---- step3 §3: the PIT menu probe must survive #827's `_norm_uid` change ----

class _FakeSession:
    """A two-query fake of the driver session `_menu_rows` uses. It returns the
    rows the real Cypher would, so the probe's own logic is exercised with NO
    graph access."""

    def __init__(self, pair_rows, lookup_rows):
        self._pairs, self._lookup, self._n = pair_rows, lookup_rows, 0

    def run(self, _q, **_kw):
        self._n += 1
        return self._pairs if self._n == 1 else self._lookup

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


class _FakeDriver:
    def __init__(self, session):
        self._s = session

    def session(self, **_kw):
        return self._s

    def close(self):
        pass


def _run_menu_rows(monkeypatch, pair_rows, lookup_rows):
    import slice_menu_probe as SMP
    monkeypatch.setattr(SMP, "_driver",
                        lambda: _FakeDriver(_FakeSession(pair_rows, lookup_rows)))
    return SMP._menu_rows("AAPL", "2026-04-23T16:00:00-04:00")


def test_step3_3_the_menu_probe_carries_the_MATCHED_company_cik(monkeypatch):
    """#827 made `_norm_uid` require the matched company, precisely so a stored
    reference can no longer vouch for its own. This probe still called the
    one-argument form and crashed with a TypeError before the population was
    ever checked — reproduced from Codex's exact command.

    The cik now travels with each `(du, mu)` pair from the `co:Company` row the
    query ALREADY matched. Nothing infers a company from the reference and no
    cik is parsed here.
    """
    # THE TWO SPELLINGS DIFFER BY DESIGN: the stored Context arrays carry the
    # ZERO-PADDED cik, while node ids drop the leading zeros — that asymmetry is
    # the whole reason `_norm_uid` exists. My first fixture had it backwards and
    # returned no rows.
    cik = "0000320193"
    node = "320193"
    pairs = [{"du": f"{cik}:seg", "mu": f"{cik}:us-gaap_ProductMember",
              "cik": cik}]
    lookup = [{"id": f"{node}:seg", "kind": "dim", "qname": "srt:Segment",
               "label": None},
              {"id": f"{node}:us-gaap_ProductMember", "kind": "mem",
               "qname": "us-gaap:ProductMember", "label": "Product"}]
    rows = _run_menu_rows(monkeypatch, pairs, lookup)
    assert rows == [{"axis": "srt:Segment", "member": "us-gaap:ProductMember",
                     "label": "Product"}], rows


@pytest.mark.parametrize("cik,why", [
    (None, "missing"),
    ("", "empty"),
    ("not-a-cik", "malformed"),
    ("0000000001", "mismatching registrant"),
])
def test_step3_3_a_bad_cik_FAILS_CLOSED_without_a_raw_exception(monkeypatch,
                                                                cik, why):
    """A missing, malformed, non-registrant or mismatching cik must drop the
    pair, never raise. A crash here would abort the whole recompute — which is
    exactly what the TypeError did."""
    good = "0000320193"
    pairs = [{"du": f"{good}:seg", "mu": f"{good}:mem", "cik": cik}]
    lookup = [{"id": "320193:seg", "kind": "dim", "qname": "srt:Segment",
               "label": None},
              {"id": "320193:mem", "kind": "mem", "qname": "us-gaap:M",
               "label": "M"}]
    rows = _run_menu_rows(monkeypatch, pairs, lookup)
    assert rows == [], f"{why} cik produced rows: {rows}"


def test_step3_3_the_point_in_time_cutoff_is_unchanged():
    """§3/§1 — the menu may use only information public by the event date. The
    cutoff is asserted VERBATIM so a later edit cannot loosen it silently."""
    src = open(os.path.join(_HERE, "slice_menu_probe.py"), encoding="utf-8").read()
    assert "datetime(pr.created) <= datetime($event_time)" in src, (
        "the point-in-time cutoff was changed or removed")


# ---- step3 §10: the reliability gate and its rule-of-three bound ----

@pytest.mark.parametrize("total,invalid,rate,passes", [
    (100, 1, 0.01, True),     # below the 2% bar
    (100, 2, 0.02, True),     # exactly AT it — inclusive
    (100, 3, 0.03, False),    # above
])
def test_step3_10_the_invalid_response_bar_is_2_percent_inclusive(total, invalid,
                                                                  rate, passes):
    """§10 — "invalid-response rate at most 2%, per the WorkOrder's reliability
    gate". Driven through the SAME owner `score_arm` calls."""
    from scorers.score_exp5 import invalid_response_stats, passes_official_bars
    st = invalid_response_stats({"total": total, "invalid": invalid})
    assert st["applicable"] and st["rate"] == rate, st
    clean = {"recall": 0.99, "lane_wrong": 0, "wrong_name": 0,
             "value_shape_acc": 1.0, "state_acc": 1.0, "would_park": 0.0,
             "safety_result": "PASS"}
    assert passes_official_bars(**clean, invalid_response_rate=rate) is passes


def test_step3_10_zero_responses_is_NOT_APPLICABLE_not_zero_percent():
    """Step 3 makes no model call. Reporting 0% would invent reliability data
    nobody measured, and an inapplicable metric must not read as a pass."""
    from scorers.score_exp5 import invalid_response_stats
    for empty in (None, {}, {"total": 0, "invalid": 0}):
        st = invalid_response_stats(empty)
        assert st["applicable"] is False and st["rate"] is None, (empty, st)


def test_step3_10_the_rule_of_three_bound_is_reported_for_a_clean_run():
    """§10 names the rule-of-three bounds. With ZERO observed failures in N
    trials the 95% upper bound is 3/N — so 156 clean replies show at most ~1.9%,
    NOT 0%. Reported so a small clean run cannot be read as proof of reliability
    it does not carry."""
    from scorers.score_exp5 import invalid_response_stats
    st = invalid_response_stats({"total": 156, "invalid": 0})
    assert st["rate"] == 0.0
    assert abs(st["upper95"] - 3.0 / 156) < 1e-12, st
    assert st["upper95"] > 0.019, "the bound must not read as certainty"
    # with a failure observed the bound is not the rule-of-three form
    assert invalid_response_stats({"total": 156, "invalid": 1})["upper95"] is None


def test_step3_10_du_worthy_false_rows_never_enter_recall():
    """§10 — "the official denominators; `du_worthy:false` rows never enter
    recall". A near-miss exemplar must not make recall look worse."""
    from scorers.score_exp5 import MEANING_FIELDS
    q, near = "r" * 80, "n" * 80
    gold = {"E1": [_gold_fact(q, item=_mut_item(q)),
                   dict(_gold_fact(near, item=_mut_item(near)), du_worthy=False)]}
    arm = {"E1": {"facts": [_v2_fact(q, fact_type="metric", item=_mut_item(q))]}}
    r = score_arm(gold, arm, _META1,
                  {("E1", 0): {k: True for k in MEANING_FIELDS}},
                  route=_route_for(arm))
    assert r["gold_n"] == 1, f"a du_worthy:false row entered the denominator: {r}"
    assert r["recall"] == 1.0, r


def test_step3_7_a_reader_exception_is_a_LOUD_failed_run_not_an_outcome(tmp_path):
    """§7 — "writes are disabled and an exception remains a LOUD FAILED RUN, not
    a made-up outcome".

    This was the one §7 property with no control. It matters more than it looks:
    a route that swallowed a reader exception would emit ordinary-looking
    decision rows for facts nobody actually produced, and every downstream
    number would be computed from fabricated outcomes. Silence is the dangerous
    failure here, not the crash.
    """
    from driver.core.driver_write_cli import run_event
    from scorers.score_exp5 import project_replay_items, replay_reader
    R = _core_route_fixtures()
    base = R._v2_events()[R.CE_EVENT]
    raw0 = base["items"][0]
    reply = {"source_id": R.CE_EVENT, "abstentions": [],
             "facts": [R._text_fact(base, raw0)]}
    items, good = replay_reader(reply)
    _, index_map = project_replay_items(reply)
    assert len(items) == 1 and index_map

    boom = RuntimeError("the recorded reader failed")

    def exploding(**_kw):
        raise boom

    event = {**base, "items": items}
    with pytest.raises(Exception) as caught:
        run_event(event, store=R._mirror_fake(event), audit_dir=str(tmp_path),
                  enable_writes=False, reader=exploding)
    assert boom is caught.value or boom.args[0] in str(caught.value), (
        f"the reader's failure was replaced by {caught.value!r}")

    # the LAWFUL control: the same event with the real callback still runs, so
    # this cannot be satisfied by a route that simply refuses everything
    ok = run_event({**base, "items": items}, store=R._mirror_fake(event),
                   audit_dir=str(tmp_path), enable_writes=False, reader=good)
    assert ok["status"] == "dry_run" and len(ok["items"]) == 1, ok


def test_step3_8_no_shortcut_can_create_a_link_structurally():
    """§8 — "No quote overlap, value equality, fuzzy match, regex, or
    first-match shortcut may create a link."

    Checked STRUCTURALLY against the scorer's own AST, not by reading: every
    retired shortcut was deleted at some point, and prose in a docstring cannot
    stop one being reintroduced. A meaning-based match is the qualified grader's
    decision alone; the only automatic linker is `fact_match`.
    """
    import ast
    src = open(os.path.join(_HERE, "scorers", "score_exp5.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)

    # 1. no fuzzy/similarity library may be reachable
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
            for n in names:
                assert "difflib" not in n and "fuzz" not in n.lower(), n
        # 2. no regex is compiled or used to decide anything
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert not (node.value.id == "re" and node.attr in
                        ("match", "search", "fullmatch", "compile")), \
                "a regex decision path reappeared in the scorer"

    # 3. the retired shortcut FUNCTIONS are gone, not merely unused
    defined = {n.name for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for retired in ("_value_eq", "_overlap", "_best_candidate", "apply_resolutions",
                    "_home_ok"):
        assert retired not in defined, f"{retired} is defined again"

    # 4. `fact_match` is the ONLY thing that produces links
    assert "from driver.core.fact_match import match_facts" in src
    assert src.count("match_facts(") <= 3, (
        "more match_facts call sites than the scorer's known seams")


# ---- step3 §6 / WorkOrder §1.5: the retry must validate V2, not just JSON ----

_RD_MANIFEST = os.path.join(_HERE, "launch_exp5_readers.manifest.json")


def _retry(source_id, texts, out_dir, prompt_sha=None):
    """SAVE each attempt through the ingest, THEN resolve from the captures.

    Saving is the ingest's job and happens BEFORE any interpretation; the
    resolver performs zero writes (Codex SEQ 1163).
    """
    man = _plan("launch_exp5_readers.manifest.json")
    pinned = next(e["prompt_sha256"] for e in man["events"]
                  if e["source_id"] == source_id)
    caps = []
    for i, t in enumerate(texts, 1):
        row = {"arm": "P1", "source_id": source_id, "text": t,
               "prompt_sha256": prompt_sha or pinned}
        os.makedirs(str(out_dir), exist_ok=True)
        ing = RT.ingest_workflow_result(
            {"results": [row]}, str(out_dir), manifest_path=_RD_MANIFEST,
            validate=False, attempt=i,
            retry_schedule={(source_id, "P1")})
        caps.append(ing["captures"][(source_id, "P1")])
    return RT.resolve_with_one_retry(source_id, "P1", caps, _RD_MANIFEST)


def _lawful_v2(source_id):
    return json.dumps({"source_id": source_id, "facts": [], "abstentions": []})


def test_step3_6_retry_treats_parseable_but_OFF_CONTRACT_as_invalid(tmp_path):
    """WorkOrder §1.5 / step3 §6 — the retry judged only whether the text
    PARSED. `{"source_id": "E1"}` is valid JSON and is NOT a lawful V2 reader
    answer, so off-contract output won and never received its one allowed retry.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]
    off = json.dumps({"source_id": sid, "nonsense": True})
    out = _retry(sid, [off, _lawful_v2(sid)], tmp_path / "a")
    assert out["attempt"] == 2 and out["invalid"] is None, out
    assert len(out["raw"]) == 2, "both PAID attempts must be preserved"


def test_step3_6_two_off_contract_replies_enter_the_invalid_bucket(tmp_path):
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]
    off = json.dumps({"source_id": sid, "nonsense": True})
    out = _retry(sid, [off, off], tmp_path / "b")
    assert out["doc"] is None and out["invalid"], out
    assert len(out["raw"]) == 2


def test_step3_6_retry_refuses_a_reply_for_the_WRONG_source(tmp_path):
    man = _plan("launch_exp5_readers.manifest.json")
    sid, other = (e["source_id"] for e in man["events"][:2])
    out = _retry(sid, [_lawful_v2(other)], tmp_path / "c")
    assert out["doc"] is None and "source" in (out["invalid"] or "").lower(), out


def test_step3_6_a_lawful_FIRST_reply_wins_without_a_retry(tmp_path):
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]
    out = _retry(sid, [_lawful_v2(sid)], tmp_path / "d")
    assert out["attempt"] == 1 and out["invalid"] is None, out


def test_step3_6_the_retry_must_reuse_the_EXACT_pinned_prompt(tmp_path):
    """§6 "retry with the SAME prompt", proved rather than asserted.

    The expected prompt comes from the BOUND MANIFEST for that source, so a
    caller that re-prompted differently is refused. A caller-supplied label or
    hash it can merely claim would prove nothing.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]
    with pytest.raises(RT.RawTransportError):
        _retry(sid, [_lawful_v2(sid)], tmp_path / "e", prompt_sha="f" * 64)


def test_step3_6_more_than_two_attempts_still_refuses(tmp_path):
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]
    with pytest.raises(RT.RawTransportError):
        _retry(sid, [_lawful_v2(sid)] * 3, tmp_path / "f")


def test_step3_4_the_gold_drafting_plan_can_NEVER_use_the_cheap_tier():
    """§4 — "Haiku NEVER drafts gold."

    True today only because nobody wrote it in. That is an absence, and an
    absence is not a guard: adding a third cheap lane would look like a sensible
    cost saving and nothing would object. The gold key is the thing every later
    score is measured against, so a cheaper drafter silently degrades every
    number downstream while every test stays green.

    Asserted from the plan's OWN lanes rather than a name list of my own: the
    lawful drafting tiers are exactly the two the WorkOrder names.
    """
    kf = _plan("launch_kfields_drafts.manifest.json")
    lanes = {l["model"] for e in kf["events"] for l in e["lanes"]}
    assert lanes == {"sonnet", "opus"}, f"the drafting tiers drifted: {lanes}"
    body = json.dumps(kf)
    assert "haiku" not in body.lower(), "a cheap tier reached the gold plan"
    # every event carries BOTH lanes — 36 x 2 = the 72 the plan claims
    assert all(len(e["lanes"]) == 2 for e in kf["events"])
    assert kf["n_workers"] == 2 * len(kf["events"]) == 72


def test_step3_4_no_producer_under_test_can_define_its_own_key():
    """§4 — "No producer under test can define its own key."

    The reader arms are the producers UNDER TEST; the drafting plan makes the
    key. So no reader tier may appear as a gold drafting lane, and the two plans
    must stay separately approved. Checked as a SET RELATION between the two
    artifacts, so adding a reader tier to the drafting plan fails here rather
    than being noticed in review.
    """
    kf = _plan("launch_kfields_drafts.manifest.json")
    rd = _plan("launch_exp5_readers.manifest.json")
    drafting = {l["model"] for e in kf["events"] for l in e["lanes"]}
    reader_only = {a["tier"] for a in rd["arms"]} - drafting
    assert reader_only, "every reader tier also drafts the key it is scored on"
    assert kf["door"] == "gold" and rd["door"] == "reader", (kf["door"], rd["door"])


def test_step3_6_the_REAL_launcher_retries_exactly_once_end_to_end(tmp_path):
    """SEQ 1159 — the retry requirement proved on the FUTURE EXECUTION PATH.

    My previous proof drove a helper with ZERO callers and supplied the claimed
    prompt itself. That proved nothing about the real path: the launcher called
    `agent()` once per item and never retried, and one caller-supplied prompt
    string could not say which prompt produced attempt 1 versus attempt 2.

    Two honest phases, both through the generated launcher: launch -> PYTHON
    classifies validity -> retry ONLY the invalid scheduled pairs. No JSON or V2
    rule is evaluated in JavaScript; `_attempt_valid` remains the single owner.
    """
    import subprocess
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is unavailable in this environment")
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]

    def launch(extra):
        out = subprocess.run(
            [node, os.path.join(_HERE, "run_reader_launcher_fake.mjs"),
             os.path.join(_HERE, "launch_exp5_readers.workflow.js"),
             _RD_MANIFEST] + _LAWFUL_RUN_INPUTS + extra,
            capture_output=True, text=True, check=True)
        return json.loads(out.stdout.strip().splitlines()[-1])

    first = launch([f"--bad={sid}"])
    assert first["total"] == 156, first["total"]

    # SAVE BEFORE INTERPRETATION (§6's first invariant, Codex SEQ 1162.1). My
    # earlier order classified the paid first replies before writing them, so a
    # stop after classification would have lost every one.
    p1_dir = tmp_path / "phase1"
    os.makedirs(str(p1_dir), exist_ok=True)
    ing, retry = _save_then_classify(first["rows"], p1_dir)
    saved = sum(len(f) for _r, _d, f in os.walk(str(p1_dir)))
    assert saved == 156, f"{saved} raw files saved for 156 paid replies"
    assert not any("prompt" in e for e in ing["errors"]), ing["errors"][:3]
    assert retry and all(r["source_id"] == sid for r in retry), retry

    second = launch([f"--retry={json.dumps(retry)}"])
    assert second["total"] == len(retry), (
        f"the retry launched {second['total']} calls for {len(retry)} pairs")
    p2_dir = tmp_path / "phase2"
    i2, still = _save_then_classify(second["rows"], p2_dir, attempt=2,
                                    retry=retry)
    assert still == [], "retry did not fix it"
    # EXACTLY 156 first captures + N distinct `.retry1` captures, counted on
    # disk BEFORE resolution. My earlier version ingested phase 2 TWICE and
    # wrote 156 + 2N while claiming 156 + N (Codex SEQ 1164.1).
    before = sum(len(f) for _r, _d, f in os.walk(str(tmp_path)))
    assert before == 156 + len(retry), (
        f"{before} raw files for 156 + {len(retry)} replies")
    assert all("retry1" in os.path.basename(c["raw_path"])
               for c in i2["captures"].values()), i2["captures"]

    # BOTH attempts used the SAME pinned prompt, evidenced by the LAUNCHER
    by = {(r["arm"], r["source_id"]): r for r in first["rows"]}
    for pair in retry:
        a = by[(pair["arm"], pair["source_id"])]
        b = next(r for r in second["rows"]
                 if r["arm"] == pair["arm"] and r["source_id"] == pair["source_id"])
        assert a["prompt_sha256"] == b["prompt_sha256"], (a, b)
        key = (pair["source_id"], pair["arm"])
        cap1, cap2 = ing["captures"][key], i2["captures"][key]
        n_before = sum(len(f) for _r, _d, f in os.walk(str(tmp_path)))
        got = RT.resolve_with_one_retry(pair["source_id"], pair["arm"],
                                        [cap1, cap2], _RD_MANIFEST)
        n_after = sum(len(f) for _r, _d, f in os.walk(str(tmp_path)))
        assert n_after == n_before, "the resolver WROTE — it must consume captures"
        assert got["attempt"] == 2 and got["invalid"] is None, got
        assert len(got["raw"]) == 2, "both paid attempts must be preserved"


def test_step3_6_a_lawful_first_launch_triggers_NO_retry():
    """The counter-control: with every answer lawful there is nothing to retry,
    so the two-phase seam must not manufacture a second launch."""
    import subprocess
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is unavailable in this environment")
    out = subprocess.run(
        [node, os.path.join(_HERE, "run_reader_launcher_fake.mjs"),
         os.path.join(_HERE, "launch_exp5_readers.workflow.js"),
         _RD_MANIFEST] + _LAWFUL_RUN_INPUTS,
        capture_output=True, text=True, check=True)
    rows = json.loads(out.stdout.strip().splitlines()[-1])["rows"]
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _i, retry = _save_then_classify(rows, td)
    assert retry == [], "a lawful launch asked for a retry"


def _save_then_classify(rows, out_dir, attempt=1, retry=None):
    """SAVE through the ingest, THEN classify from the persisted captures.

    Classification consumes what was written, never an in-memory text nobody
    recorded — §6's first invariant, on BOTH phases (Codex SEQ 1163).
    """
    os.makedirs(str(out_dir), exist_ok=True)
    kw = {}
    if retry is not None:
        kw["retry_schedule"] = {(r["source_id"], r["arm"]) for r in retry}
    ing = RT.ingest_workflow_result({"results": rows}, str(out_dir),
                                    manifest_path=_RD_MANIFEST, validate=False,
                                    attempt=attempt, **kw)
    return ing, RT.invalid_pairs(ing["captures"], _RD_MANIFEST)


def _launch_capturing(extra):
    """Run the fake launcher and return its rows PLUS the actual prompt bytes
    each `agent(...)` call received."""
    import subprocess
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is unavailable in this environment")
    out = subprocess.run(
        [node, os.path.join(_HERE, "run_reader_launcher_fake.mjs"),
         os.path.join(_HERE, "launch_exp5_readers.workflow.js"),
         _RD_MANIFEST] + _LAWFUL_RUN_INPUTS + list(extra),
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_step3_6_the_emitted_prompt_hash_equals_the_BYTES_ACTUALLY_SENT():
    """SEQ 1161.1 — my previous proof compared the launcher's emitted hash to
    ITSELF. The fake agent never saw the real prompt, so a mutant could send
    changed bytes while emitting the untouched `PROMPT_SHA` and the test would
    pass.

    The runner now records the exact bytes each `agent(...)` received; this
    hashes them INDEPENDENTLY and requires them to equal both the emitted claim
    and the manifest pin.
    """
    import hashlib
    res = _launch_capturing([])
    man = {e["source_id"]: e["prompt_sha256"]
           for e in _plan("launch_exp5_readers.manifest.json")["events"]}
    checked = 0
    for row, sent in zip(res["rows"], res["sent"]):
        real = hashlib.sha256(sent["prompt"].encode("utf-8")).hexdigest()
        assert real == row["prompt_sha256"], (
            f"{row['source_id']}: emitted {row['prompt_sha256'][:12]} but SENT "
            f"bytes hash to {real[:12]}")
        assert real == man[row["source_id"]], "sent bytes are not the plan's pin"
        checked += 1
    assert checked == 156, checked


def test_step3_6_a_MUTATED_prompt_is_caught_even_with_an_untouched_claim():
    """The direct mutant: send changed bytes, leave `PROMPT_SHA` alone. The
    proof above must FAIL — otherwise it was only checking a claim."""
    import hashlib
    res = _launch_capturing(["--mutate-prompt"])
    row, sent = res["rows"][0], res["sent"][0]
    real = hashlib.sha256(sent["prompt"].encode("utf-8")).hexdigest()
    assert real != row["prompt_sha256"], (
        "the mutated prompt was NOT detectable — the control proves nothing")


def test_step3_6_first_pass_rows_need_prompt_evidence_too():
    """SEQ 1161.2 — `invalid_pairs` accepted a lawful FIRST-PASS answer without
    ever matching its prompt evidence; only retry rows were checked."""
    import tempfile
    res = _launch_capturing([])
    rows = res["rows"]
    with tempfile.TemporaryDirectory() as td:
        _i, retry = _save_then_classify(rows, td)
    assert retry == [], "lawful first pass refused"
    # PROMPT INTEGRITY FAILS THE RUN CLOSED — it is not bad model output, so
    # re-asking cannot help and it must NEVER spend the one allowed retry
    # (Codex SEQ 1162.2). My earlier control expected these in the retry list,
    # which asserted exactly the wrong behaviour.
    for broken, why in ((None, "no evidence"), ("f" * 64, "wrong prompt")):
        rows2 = [dict(r, prompt_sha256=broken) for r in rows]
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(RT.RawTransportError, match="prompt integrity"):
                _save_then_classify(rows2, td)


def test_step3_6_retry_raw_uses_a_DISTINCT_name_and_writes_nothing_twice(tmp_path):
    """SEQ 1162/1163 — the retry's raw lands under its own attempt name, both
    hashes stay checkable, and the RESOLVER writes nothing."""
    import hashlib
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]
    texts = [json.dumps({"source_id": sid, "nonsense": True}), _lawful_v2(sid)]
    before = sum(len(f) for _r, _d, f in os.walk(str(tmp_path)))
    got = _retry(sid, texts, tmp_path)
    assert got["attempt"] == 2 and got["invalid"] is None, got
    names = [os.path.basename(p) for p, _s in got["raw"]]
    assert len(set(names)) == 2 and any("retry1" in n for n in names), names
    for (path, sha), text in zip(got["raw"], texts):
        on_disk = hashlib.sha256(open(path, "rb").read()).hexdigest()
        assert sha == on_disk == hashlib.sha256(
            text.encode("utf-8")).hexdigest(), path
    after = sum(len(f) for _r, _d, f in os.walk(str(tmp_path)))
    assert after == before + 2, f"{after - before} files written for 2 attempts"


def test_step3_6_actual_bytes_match_the_pin_on_BOTH_phases():
    """SEQ 1162 — the byte check must cover the RETRY launch too, not only the
    first. A retry that quietly re-worded would otherwise be invisible."""
    import hashlib
    man = {e["source_id"]: e["prompt_sha256"]
           for e in _plan("launch_exp5_readers.manifest.json")["events"]}
    sid = sorted(man)[0]
    import tempfile
    first = _launch_capturing([f"--bad={sid}"])
    with tempfile.TemporaryDirectory() as td:
        _i, retry = _save_then_classify(first["rows"], td)
    second = _launch_capturing([f"--retry={json.dumps(retry)}"])
    assert second["total"] == len(retry) > 0
    for phase in (first, second):
        for row, sent in zip(phase["rows"], phase["sent"]):
            real = hashlib.sha256(sent["prompt"].encode("utf-8")).hexdigest()
            assert real == row["prompt_sha256"] == man[row["source_id"]], (
                f"{row['source_id']}: sent bytes do not match the pin")


def test_step3_6_a_second_invalid_answer_stops_with_no_third_launch():
    """SEQ 1162 — a second invalid reply enters the invalid bucket and the seam
    must NOT launch again. Proven at the seam: after the retry the pair is still
    content-invalid, and resolving it yields the invalid bucket rather than a
    third attempt."""
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]
    import tempfile
    first = _launch_capturing([f"--bad={sid}"])
    with tempfile.TemporaryDirectory() as td:
        i1, retry = _save_then_classify(first["rows"], td)
        i1_caps = i1["captures"]
        # the retry ALSO answers off-contract
        second = _launch_capturing([f"--retry={json.dumps(retry)}",
                                    f"--bad={sid}", "--retry-also-bad"])
        i2, still = _save_then_classify(second["rows"], td, attempt=2,
                                        retry=retry)
        # THE RETRY IS SPENT: a second failure must request NO further launch.
        # This used to assert `still == retry`, which encoded the defect — it
        # would have paid for a third attempt (Codex SEQ 1165, one layer down).
        assert still == [], "a second failure asked for a THIRD paid launch"
        # ...and the pair lands in the INVALID BUCKET rather than being coerced
        key = (retry[0]["source_id"], retry[0]["arm"])
        caps = [c for c in (i1_caps.get(key), i2["captures"].get(key)) if c]
        got = RT.resolve_with_one_retry(key[0], key[1], caps, _RD_MANIFEST)
        assert got["doc"] is None and got["invalid"], got
    # and a THIRD attempt is refused outright
    fake_caps = [{"source_id": sid, "arm": "P1", "raw_path": "x",
                  "raw_sha256": "y", "prompt_sha256": "z"}] * 3
    with pytest.raises(RT.RawTransportError, match="EXACTLY ONE retry"):
        RT.resolve_with_one_retry(sid, "P1", fake_caps, _RD_MANIFEST)


def test_step3_6_a_retry_schedule_must_be_a_SUBSET_of_the_approved_plan(tmp_path):
    """SEQ 1163.2 — phase 2 may only re-ask pairs the plan already scheduled.

    I BUILT this refusal and did not test it, which is the same gap I have been
    finding elsewhere: the code was written, the proof was not, and nothing
    would have noticed it rotting.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    e = man["events"][0]
    row = {"arm": "P1", "source_id": e["source_id"],
           "prompt_sha256": e["prompt_sha256"],
           "text": _lawful_v2(e["source_id"])}

    # an arm the plan never scheduled
    for name, bad in (("bad_arm", {(e["source_id"], "P9")}),
                      ("bad_event", {("NOT-AN-EVENT", "P1")})):
        d = tmp_path / name
        out = RT.ingest_workflow_result(
            {"results": [row]}, str(d), manifest_path=_RD_MANIFEST,
            validate=False, attempt=2, retry_schedule=bad)
        assert not out["ok"] and any("unscheduled" in x for x in out["errors"]), out
        # ...and the PAID raw is still preserved exactly once. Refusing early
        # used to skip the save loop entirely and lose it (Codex SEQ 1164.2).
        kept = sum(len(f) for _r, _d, f in os.walk(str(d)))
        assert kept == 1, f"{name}: {kept} raw files kept for 1 paid reply"

    # ...and the LAWFUL subset is still accepted, so this is not a blanket refusal
    ok = RT.ingest_workflow_result(
        {"results": [row]}, str(tmp_path / "lawful"),
        manifest_path=_RD_MANIFEST, validate=False, attempt=2,
        retry_schedule={(e["source_id"], "P1")})
    assert ok["ok"], ok["errors"][:3]
    assert (e["source_id"], "P1") in ok["captures"], sorted(ok["captures"])


def test_step3_6_a_duplicate_retry_reply_is_refused_but_still_PRESERVED(tmp_path):
    """The retry path's duplicate branch, which nothing exercised.

    A duplicate is REFUSED and gets no capture record — it must not become a
    second answer for the same pair. But it was still PAID FOR, so its bytes
    stay on disk under a distinct name. Refusing and discarding would turn one
    duplicated reply into a lost one.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    e = man["events"][0]
    row = {"arm": "P1", "source_id": e["source_id"],
           "prompt_sha256": e["prompt_sha256"],
           "text": _lawful_v2(e["source_id"])}
    out = RT.ingest_workflow_result(
        {"results": [row, dict(row)]}, str(tmp_path),
        manifest_path=_RD_MANIFEST, validate=False, attempt=2,
        retry_schedule={(e["source_id"], "P1")})
    assert not out["ok"] and any("DUPLICATE" in x for x in out["errors"]), out
    assert len(out["captures"]) == 1, (
        "a duplicate produced a SECOND capture for one scheduled pair")
    kept = sum(len(f) for _r, _d, f in os.walk(str(tmp_path)))
    assert kept == 2, f"{kept} raw files kept for 2 paid replies"


def test_step3_6_writes_happen_ONLY_at_an_ingest_measured_globally(tmp_path):
    """The invariant behind every §6 file-count assertion, measured GLOBALLY.

    Three rounds of review found the same shape of defect: a locally correct
    assertion around a wrong global flow — a "resolver wrote zero" check that
    was true only inside the window it measured, while extra writes happened
    outside it. A per-step total over the WHOLE tree cannot be fooled that way.

    Expected, and asserted step by step:
      launch    +0    launching contacts no disk
      ingest    +N    the ONE saving boundary
      classify  +0    reads persisted captures
      resolve   +0    consumes captures
    """
    man = _plan("launch_exp5_readers.manifest.json")
    sid = man["events"][0]["source_id"]

    def total():
        return sum(len(f) for _r, _d, f in os.walk(str(tmp_path)))

    first = _launch_capturing([f"--bad={sid}"])
    assert total() == 0, "a launch wrote to disk"

    ing, retry = _save_then_classify(first["rows"], tmp_path / "p1")
    assert total() == 156, total()
    after_classify = total()
    assert after_classify == 156, "classification wrote to disk"

    second = _launch_capturing([f"--retry={json.dumps(retry)}"])
    assert total() == 156, "the retry launch wrote to disk"

    i2, still = _save_then_classify(second["rows"], tmp_path / "p2",
                                    attempt=2, retry=retry)
    assert total() == 156 + len(retry), total()
    assert still == [], still

    before_resolve = total()
    for pair in retry:
        key = (pair["source_id"], pair["arm"])
        got = RT.resolve_with_one_retry(key[0], key[1],
                                        [ing["captures"][key],
                                         i2["captures"][key]], _RD_MANIFEST)
        assert got["attempt"] == 2 and got["invalid"] is None, got
    assert total() == before_resolve, "resolution wrote to disk"


@pytest.mark.parametrize("mutate,why", [
    (lambda r, e: dict(r, arm="P9"), "unscheduled ARM"),
    (lambda r, e: dict(r, source_id="NOT-AN-EVENT"), "unscheduled EVENT"),
])
def test_step3_6_an_unscheduled_pair_never_becomes_a_retry_REQUEST(mutate, why,
                                                                   tmp_path):
    """SEQ 1165 — the subset refusal used to fire only when phase 2 INGESTED,
    i.e. after a second call had already been launched and PAID for.

    A structurally unscheduled pair must never leave phase 1 as a retry request.
    Its raw is still preserved and the run is still red — the refusal costs
    nothing extra.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    e = man["events"][0]
    row = mutate({"arm": "P1", "source_id": e["source_id"],
                  "prompt_sha256": e["prompt_sha256"],
                  "text": json.dumps({"source_id": e["source_id"],
                                      "nonsense": True})}, e)
    try:
        ing, retry = _save_then_classify([row], tmp_path)
        assert not ing["ok"], f"{why}: an unscheduled pair was accepted"
        assert retry == [], f"{why}: it would have launched and PAID for a retry"
    except RT.RawTransportError:
        # AN UNSCHEDULED EVENT HAS NO MANIFEST PIN, so the prompt-integrity
        # check fires first and FAILS THE RUN CLOSED. That is stronger than
        # returning an empty retry list — it stops the run outright — and it
        # still satisfies "red, and zero retry calls".
        pass
    assert sum(len(f) for _r, _d, f in os.walk(str(tmp_path))) == 1, (
        f"{why}: the paid raw was not preserved")


def test_step3_6_a_scheduled_pair_with_the_same_bad_content_DOES_retry(tmp_path):
    """The positive half: identical invalid content on a SCHEDULED pair must
    still yield exactly one retry — the refusal must not swallow real work."""
    man = _plan("launch_exp5_readers.manifest.json")
    e = man["events"][0]
    row = {"arm": "P1", "source_id": e["source_id"],
           "prompt_sha256": e["prompt_sha256"],
           "text": json.dumps({"source_id": e["source_id"], "nonsense": True})}
    _ing, retry = _save_then_classify([row], tmp_path)
    assert retry == [{"arm": "P1", "source_id": e["source_id"]}], retry


def test_step3_6_a_second_failure_never_requests_a_THIRD_launch(tmp_path):
    """The one allowed retry is SPENT once a capture IS the retry.

    Same shape as SEQ 1165, one layer deeper: `invalid_pairs` emitted a retry
    request for an already-retried capture, so a third attempt would be launched
    and PAID for before the resolver refused it. The refusal existed, but after
    the money.

    The capture records which attempt it is, so the request stops at the source.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    e = man["events"][0]
    bad = {"arm": "P1", "source_id": e["source_id"],
           "prompt_sha256": e["prompt_sha256"],
           "text": json.dumps({"source_id": e["source_id"], "nonsense": True})}

    _i1, first = _save_then_classify([bad], tmp_path / "p1")
    assert first == [{"arm": "P1", "source_id": e["source_id"]}], first

    _i2, second = _save_then_classify([bad], tmp_path / "p2", attempt=2,
                                      retry=first)
    assert second == [], "a second failure asked for a THIRD paid launch"
    # both paid attempts are still preserved
    assert sum(len(f) for _r, _d, f in os.walk(str(tmp_path))) == 2


def test_step3_6_missing_and_wrong_prompt_evidence_give_DISTINCT_reasons():
    """A mutation sweep showed the missing-evidence branch could be deleted with
    NO test noticing: the later hash comparison still refuses, so the OUTCOME is
    unchanged and only the REASON degrades.

    The reason is what a future operator acts on — "no evidence" and "wrong
    prompt" need different investigations — so the distinction is asserted
    rather than left to survive by luck.
    """
    man = _plan("launch_exp5_readers.manifest.json")
    e = man["events"][0]
    base = {"source_id": e["source_id"], "arm": "P1"}
    for absent in (None, ""):
        why = RT.prompt_evidence_problem(dict(base, prompt_sha256=absent),
                                         _RD_MANIFEST)
        assert why and "no prompt evidence" in why, (absent, why)
    wrong = RT.prompt_evidence_problem(dict(base, prompt_sha256="f" * 64),
                                       _RD_MANIFEST)
    assert wrong and "not the pinned" in wrong, wrong
    assert "no prompt evidence" not in wrong, "the two reasons collapsed"


@pytest.mark.parametrize("door,why", [
    ("not_a_door", "unknown"),
    (None, "missing"),
])
def test_step3_6_an_unknown_or_missing_DOOR_refuses_the_scheduled_ingest(
        door, why, tmp_path):
    """A mutation sweep found this branch UNGUARDED: deleting the scheduled
    path's door check broke no test at all.

    The door decides WHICH contract a reply is checked against. An unknown or
    missing one means that question is undecidable, so proceeding would validate
    against whatever happened to be default — the exact failure the
    manifest-owned door exists to prevent.
    """
    man = json.loads(open(_RD_MANIFEST, encoding="utf-8").read())
    if door is None:
        man.pop("door", None)
    else:
        man["door"] = door
    bad_manifest = tmp_path / "bad_door.manifest.json"
    bad_manifest.write_text(json.dumps(man, sort_keys=True), encoding="utf-8")

    # A SCHEDULE-COMPLETE set: the door check runs only once the structural
    # checks pass, so a single row would fail on MISSING replies first and the
    # door would never be reached — my first attempt did exactly that.
    rows = _reader_rows()
    out = RT.ingest_workflow_result(
        {"results": rows}, str(tmp_path / "out"),
        manifest_path=str(bad_manifest), validate=True)
    assert not out["ok"], f"a {why} door was accepted"
    assert any("door" in x for x in out["errors"]), out["errors"][:3]
    # every PAID reply is still preserved — the door check must not cost evidence
    assert sum(len(f) for _r, _d, f in os.walk(str(tmp_path / "out"))) == len(rows)
