"""Persistent failure-case tests for the K-fields exam guards (reviewer order
2026-07-24): each test proves a guard TRIPS on its failure case, and the pass
cases pass. Every failure scenario runs on TEMP COPIES — the frozen exam files
are never touched (test_frozen_untouched proves it inside this very suite).

Run: venv/bin/python -m pytest harness/test_harness_guards.py -q
"""
import hashlib
import json
from decimal import Decimal
import os
import shutil

import audit_worker_access as AUD
import build_kfields_inputs as BLD
import kf_lint as LNT

_HERE = os.path.dirname(os.path.abspath(__file__))
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
       os.path.join(_HERE, "exp5_item_contract.md"),
       os.path.join(_HERE, "exp5_item_contract.manifest.json")])


def _frozen_state():
    out = {}
    for p in FROZEN_SET:
        out[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    assert len(out) == 77, f"frozen set must be the FULL 77 files, got {len(out)}"
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
    text = LNT.event_text(SID, INPUTS)
    q = text[:100]
    gi = {k: None for k in LNT.FIELDS37}
    gi.update({"driver_name": "revenue", "driver_state": "reported",
               "quote": q, "measurement_raw_spans": [], "slice_parts": [],
               "sequential_evidence": False})
    f = {"fact_type": "metric", "du_worthy": True, "gold_item": gi,
         "gold_extra": {"expectation_comparison_present": False},
         "quote": q, "ambiguity_note": None}
    f.update(over)
    return f


def _doc(facts):
    return {"source_id": SID, "facts": facts}


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
    f = _fact()
    f["quote"] = ""
    f["gold_item"]["quote"] = ""
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_inner_outer_mismatch(tmp_path):
    f = _fact()
    f["gold_item"]["quote"] = f["quote"] + "x"
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_none_shape_literal(tmp_path):
    f = _fact()
    f["gold_item"]["level_shape_hint"] = "none"
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_wrong_type_cleanly(tmp_path):
    f = _fact()
    f["gold_item"]["level_low"] = "726"          # string, not number
    f["gold_item"]["level_high"] = "726"
    f["gold_item"]["level_shape_hint"] = "point"
    assert _lint(tmp_path, [_doc([f])]) == 1     # errors, not a crash


def test_lint_fails_extra_fact_key(tmp_path):
    f = _fact()
    f["bonus"] = 1
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_stored_period_scope(tmp_path):
    f = _fact()
    f["gold_item"]["period_scope"] = "quarter"   # store enum, not producer-side
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
from fact16_checks import check_item


def test_lint_fails_null_driver_name(tmp_path):
    f = _fact()
    f["gold_item"]["driver_name"] = None
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_illegal_driver_name(tmp_path):
    f = _fact()
    f["gold_item"]["driver_name"] = "Bad Name!"
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_wrong_lane_state(tmp_path):
    f = _fact()
    f["gold_item"]["driver_state"] = "raised"     # guidance word on metric lane
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_month_13_via_production(tmp_path):
    f = _fact()
    f["gold_item"].update(month=13, fiscal_year=2024, time_type="duration")
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_non_iso_date_via_production(tmp_path):
    f = _fact()
    f["gold_item"].update(period_start_date="01/03/2026",
                          period_end_date="2026-03-31", time_type="duration")
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_start_after_end_via_production(tmp_path):
    f = _fact()
    f["gold_item"].update(period_start_date="2026-06-30",
                          period_end_date="2026-01-01", time_type="duration")
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_fact16_trips_surprise_temporal_baseline():
    item = {"surprise_basis_hint": "actual", "comparison_baseline": "prior_year"}
    codes, _ = check_item(item, "surprise")
    assert "SURPRISE_TYPE_ILLEGAL" in codes


def test_fact16_trips_guidance_vs_previous_guidance():
    item = {"surprise_basis_hint": "guidance",
            "comparison_baseline": "previous_guidance"}
    codes, _ = check_item(item, "surprise")
    assert "SURPRISE_TYPE_ILLEGAL" in codes


def test_fact16_trips_impossible_tense_exact_dates():
    item = {"surprise_basis_hint": "actual", "comparison_baseline": "consensus",
            "period_start_date": "2026-10-01", "period_end_date": "2027-01-01",
            "time_type": "duration"}
    codes, _ = check_item(item, "surprise", event_date="2026-04-23",
                          fye_month=12)
    assert "IMPOSSIBLE_TENSE_ACTUAL_FUTURE" in codes


def test_fact16_trips_impossible_tense_fiscal_only():
    # NO exact dates — the RESOLVED end (production resolver) must catch it
    item = {"surprise_basis_hint": "actual", "comparison_baseline": "consensus",
            "fiscal_year": 2050, "fiscal_quarter": 1, "time_type": "duration"}
    codes, _ = check_item(item, "surprise", event_date="2026-04-23",
                          fye_month=12)
    assert "IMPOSSIBLE_TENSE_ACTUAL_FUTURE" in codes


def test_fact16_passes_legal_surprise():
    item = {"surprise_basis_hint": "actual", "comparison_baseline": "consensus",
            "period_start_date": "2026-01-01", "period_end_date": "2026-03-31",
            "time_type": "duration"}
    codes, notes = check_item(item, "surprise", event_date="2026-04-23",
                              fye_month=12)
    assert "SURPRISE_TYPE_ILLEGAL" not in codes
    assert any("actual_vs_consensus" in n for n in notes)


# ---- round-9: period law = THE PRODUCTION RESOLVER, exactly ----

def test_lint_accepts_production_valid_year_2150(tmp_path):
    f = _fact()
    f["gold_item"].update(fiscal_year=2150, time_type="duration")
    assert _lint(tmp_path, [_doc([f])]) == 0      # my 2100 cap was invented


def test_lint_fails_half_quarter_conflict(tmp_path):
    f = _fact()
    f["gold_item"].update(fiscal_year=2024, fiscal_quarter=2, half=1,
                          time_type="duration")
    assert _lint(tmp_path, [_doc([f])]) == 1      # production: conflicting fields


def test_lint_fails_fractional_year_via_production(tmp_path):
    f = _fact()
    f["gold_item"].update(fiscal_year=2024.5, time_type="duration")
    assert _lint(tmp_path, [_doc([f])]) == 1      # production: out of range


# ---- round-10: malformed AI output fails CLEANLY, never crashes ----

def test_lint_clean_on_int_date(tmp_path):
    f = _fact()
    f["gold_item"]["period_start_date"] = 123
    assert _lint(tmp_path, [_doc([f])]) == 1     # error lines, no exception


def test_lint_clean_on_list_driver_state(tmp_path):
    f = _fact()
    f["gold_item"]["driver_state"] = []
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
    """A per-event reply. The quote MUST come from THAT event's own text —
    the validator rightly rejects a quote that is not verbatim in its event."""
    text = LNT.event_text(sid, INPUTS)
    q = text[:100]
    gi = {k: None for k in LNT.FIELDS37}
    gi.update({"driver_name": "revenue", "driver_state": "reported", "quote": q,
               "measurement_raw_spans": [], "slice_parts": [],
               "sequential_evidence": False})
    f = {"fact_type": "metric", "du_worthy": True, "gold_item": gi,
         "gold_extra": {"expectation_comparison_present": False},
         "quote": q, "ambiguity_note": None}
    if low is not None:
        f["gold_item"]["level_shape_hint"] = "range"
    body = json.dumps({"source_id": sid, "facts": [f]})
    if low is not None:
        body = (body.replace('"level_low": null', '"level_low": ' + low)
                    .replace('"level_high": null', '"level_high": ' + high))
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
    item = got["doc"]["facts"][0]["gold_item"]
    lo, hi = item["level_low"], item["level_high"]
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
        del d["facts"][0]["gold_item"]["driver_name"]         # 36 of 37 fields
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
    assert LNT.lint_parsed([doc], INPUTS) == 0   # same contract, after the parse


# ---- matcher safety: value-only matches must NEVER auto-credit (2026-07-25) ----
def _vfact(name, low, high=None, quote="x" * 90):
    return {"lane": "metric", "quote": quote,
            "gold_item": {"driver_name": name, "level_low": low,
                          "level_high": high if high is not None else low,
                          "level_unit_raw": "USD millions",
                          "level_shape_hint": "point"}}


def test_matcher_never_auto_matches_different_drivers_on_equal_value():
    """revenue $100M vs capital_expenditures $100M: same number, DIFFERENT
    driver, no quote overlap. Auto-pairing would credit recall for a MISSED
    fact and compare fields across unrelated facts."""
    gold = [dict(_vfact("revenue", 100),
                 quote="Revenue was $100 million for the quarter, a solid result.")]
    prod = [dict(_vfact("capital_expenditures", 100),
                 quote="Capital expenditures totalled $100 million in the period.")]
    from score_exp5 import match as _match
    pairs, unmatched_gold, _unmatched_prod, ambiguous = _match(gold, prod)
    assert pairs == [], "value-only match across DIFFERENT drivers must not auto-pair"
    assert len(ambiguous) == 1, "it must surface for grading, not vanish silently"


def _idfact(name, low, quote, **extra):
    gi = {"driver_name": name, "level_low": low, "level_high": low,
          "level_unit_raw": "USD millions", "level_shape_hint": "point"}
    gi.update(extra)
    return {"lane": "metric", "quote": quote, "gold_item": gi}


def test_matcher_rejects_same_name_value_DIFFERENT_PERIOD():
    """Q1 revenue $100M vs Q2 revenue $100M: same driver, same number,
    DIFFERENT period = DIFFERENT facts. Name+value can never prove identity."""
    gold = [_idfact("revenue", 100, "First quarter revenue was $100 million in total.",
                    fiscal_year=2026, fiscal_quarter=1)]
    prod = [_idfact("revenue", 100, "Second quarter revenue came in at $100 million.",
                    fiscal_year=2026, fiscal_quarter=2)]
    from score_exp5 import match as _match
    pairs, _ug, _up, ambiguous = _match(gold, prod)
    assert pairs == [], "different-period facts must not auto-match on name+value"
    assert len(ambiguous) == 1, "must surface for grading"


def test_matcher_rejects_same_name_value_DIFFERENT_SLICE():
    gold = [_idfact("revenue", 100, "Segment A revenue was $100 million for the period.",
                    slice_parts=["segment:a"])]
    prod = [_idfact("revenue", 100, "Segment B contributed $100 million of revenue.",
                    slice_parts=["segment:b"])]
    from score_exp5 import match as _match
    pairs, _ug, _up, ambiguous = _match(gold, prod)
    assert pairs == [] and len(ambiguous) == 1


def test_matcher_rejects_same_name_value_DIFFERENT_MEASUREMENT():
    gold = [_idfact("operating_income", 100, "GAAP operating income was $100 million.",
                    measurement_raw_spans=[])]
    prod = [_idfact("operating_income", 100, "Adjusted operating income totalled $100 million.",
                    measurement_raw_spans=["Adjusted"])]
    from score_exp5 import match as _match
    pairs, _ug, _up, ambiguous = _match(gold, prod)
    assert pairs == [] and len(ambiguous) == 1


def test_matcher_one_sentence_two_facts_is_order_free():
    """One sentence carries BOTH Q1 and Q2 revenue; the model produced only Q2.
    A shared span is a candidate LINK, not proof — crediting whichever gold
    happens to come first is an order-dependent false credit."""
    import itertools
    from score_exp5 import match as _match
    S = ("Revenue was $100 million in the first quarter and $120 million "
         "in the second quarter.")
    g1 = _idfact("revenue", 100, S, fiscal_quarter=1)
    g2 = _idfact("revenue", 120, S, fiscal_quarter=2)
    prod = [_idfact("revenue", 120, S, fiscal_quarter=2)]
    seen = set()
    for gold in itertools.permutations([g1, g2]):
        pairs, _ug, _up, ambiguous = _match(list(gold), prod)
        assert pairs == [], "a span shared by 2 gold facts must not auto-credit"
        assert all(a["reason"] == "shared_span_multiple_facts" for a in ambiguous)
        seen.add((len(pairs), len(ambiguous)))
    assert len(seen) == 1, f"result depends on gold ORDER: {seen}"


def test_matcher_exact_evidence_is_order_free_and_not_fuzzy():
    """With EXACT evidence identity (locator, else exact quote) the old fuzzy
    win disappears: a produced quote that merely CONTAINS a gold quote is no
    longer a link. One-gold/one-produced on the same span still commits, and the
    outcome is identical under every permutation of BOTH lists."""
    import itertools
    from score_exp5 import match as _match
    qa, qb = "Revenue rose five percent in the quarter.", "Costs fell two percent."
    g1 = {"lane": "metric", "quote": qa, "gold_item": {"quote": qa}}
    g2 = {"lane": "metric", "quote": qb, "gold_item": {"quote": qb}}
    p1 = {"lane": "metric", "quote": qa, "gold_item": {"quote": qa}}
    p2 = {"lane": "metric", "quote": qb, "gold_item": {"quote": qb}}
    outcomes = {(len(_match(list(go), list(po))[0]),
                 len(_match(list(go), list(po))[3]))
                for go in itertools.permutations([g1, g2])
                for po in itertools.permutations([p1, p2])}
    assert outcomes == {(2, 0)}, f"order-dependent or over-blocked: {outcomes}"
    # and CONTAINMENT is no longer a match (the deleted 20-char window)
    longer = {"lane": "metric", "quote": qa + " " + qb,
              "gold_item": {"quote": qa + " " + qb}}
    pairs, _ug, _up, amb = _match([g1], [longer])
    assert pairs == [], "substring containment must not auto-match any more"


def test_matcher_locator_distinguishes_repeats_of_one_sentence():
    """Same wording twice in a part is disambiguated by occurrence_in_part —
    exact identity, no fuzz."""
    from score_exp5 import match as _match
    q = "Revenue was $100 million."
    def f(occ):
        return {"lane": "metric", "quote": q, "gold_item": {
            "quote": q, "evidence_locator": {"part_ref": "p01",
                                             "occurrence_in_part": occ}}}
    pairs, _ug, _up, amb = _match([f(1)], [f(2)])
    assert pairs == [] and not amb, "different occurrences are different evidence"
    pairs2, _2, _3, _4 = _match([f(1)], [f(1)])
    assert pairs2 == [(0, 0)]


def test_matcher_auto_pairs_only_on_shared_source_evidence():
    """The ONE lawful auto-match: both cite the same source span."""
    q = "Revenue for the second quarter was $100 million, up five percent."
    gold = [_idfact("revenue", 100, q)]
    prod = [_idfact("revenue", 100, q)]
    from score_exp5 import match as _match
    pairs, _ug, _up, ambiguous = _match(gold, prod)
    assert pairs == [(0, 0)] and not ambiguous


# ---- v2.0 lint corrections (ChatGPT audit 2026-07-25; claims 2/3/4) ----
def test_lint_accepts_du_worthy_false(tmp_path):
    # protocol: du_worthy:false = OPTIONAL near-miss exemplar (LAWFUL, not rejected)
    f = _fact(du_worthy=False)
    assert _lint(tmp_path, [_doc([f])]) == 0


def test_lint_fails_non_bool_du_worthy(tmp_path):
    f = _fact(du_worthy="yes")
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_null_sequential_evidence(tmp_path):
    f = _fact()
    f["gold_item"]["sequential_evidence"] = None    # PreparedFactV1: non-null bool
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_null_measurement_list(tmp_path):
    f = _fact()
    f["gold_item"]["measurement_raw_spans"] = None  # PreparedFactV1: non-null list
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_fails_null_slice_parts_list(tmp_path):
    f = _fact()
    f["gold_item"]["slice_parts"] = None            # PreparedFactV1: non-null list
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_num_accepts_decimal_rejects_float():
    from decimal import Decimal
    assert LNT._is_num(Decimal("1.5")) is True and LNT._is_num(5) is True
    assert LNT._is_num(1.5) is False     # raw float rejected (production-faithful)
    assert LNT._is_num(True) is False


def test_lint_decimal_exact_END_TO_END(tmp_path):
    """Exercises kf_lint.run() itself with two literals ordinary float parsing
    COLLAPSES. As a `range` they satisfy low < high ONLY under exact Decimal
    parsing — so this goes RED the moment parse_float=Decimal is lost."""
    LOW, HIGH = "1.00000000000000000001", "1.00000000000000000002"
    f = _fact()
    f["gold_item"]["level_shape_hint"] = "range"
    line = json.dumps(_doc([f]))
    line = line.replace('"level_low": null', f'"level_low": {LOW}')
    line = line.replace('"level_high": null', f'"level_high": {HIGH}')
    # the test is only meaningful if ordinary parsing really collapses them:
    collapsed = json.loads(line)["facts"][0]["gold_item"]
    assert collapsed["level_low"] == collapsed["level_high"], "not a float-collapse pair"
    p = tmp_path / "draft.jsonl"
    p.write_text(line)
    assert LNT.run(str(p)) == 0      # exact Decimal keeps low < high -> clean


def test_lint_clean_on_list_enum_value(tmp_path):
    f = _fact()
    f["gold_item"]["level_shape_hint"] = ["point"]
    assert _lint(tmp_path, [_doc([f])]) == 1


def test_lint_clean_on_dict_period_scope(tmp_path):
    f = _fact()
    f["gold_item"]["period_scope"] = {"ytd": True}
    assert _lint(tmp_path, [_doc([f])]) == 1


# ---- round-11: scorer metadata mandatory + fiscal-only future parks ----
from score_exp5 import score_arm


def _surprise_gold_and_arm():
    gold = {"E1": [{"lane": "surprise", "du_worthy": True, "quote": "x" * 60,
                    "gold_item": {},
                    "gold_extra": {"expectation_comparison_present": True}}]}
    arm = {"E1": {"facts": [{"lane": "surprise", "quote": "y" * 60,
                             "gold_item": {
        "surprise_basis_hint": "actual", "comparison_baseline": "consensus",
        "fiscal_year": 2050, "fiscal_quarter": 1, "time_type": "duration",
        "level_low": 5, "level_high": 5, "level_shape_hint": "point",
        "level_unit_raw": "USD millions"}}]}}
    return gold, arm


def test_scorer_requires_event_meta():
    gold, arm = _surprise_gold_and_arm()
    try:
        score_arm(gold, arm, None)
        assert False, "must raise without event_meta"
    except ValueError:
        pass


def test_scorer_requires_complete_meta_per_event():
    gold, arm = _surprise_gold_and_arm()
    try:
        score_arm(gold, arm, {"E1": {"event_date": "2026-04-23"}})  # fye missing
        assert False, "must raise on incomplete meta"
    except ValueError:
        pass


def test_scorer_parks_fiscal_only_future_surprise():
    gold, arm = _surprise_gold_and_arm()
    r = score_arm(gold, arm,
                  {"E1": {"event_date": "2026-04-23", "fye_month": 12}})
    # v5: nothing matched -> verdicts trivially complete-empty -> PASS None;
    # the PARK is the point, and PASS must never be True here
    assert r["would_park"] > 0.10 and r["PASS"] is not True


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
        assert hashlib.sha256(open(e["input_path"], "rb").read()).hexdigest()             == e["input_sha256"], f"{e['source_id']}: input drifted"
    # pins == the LIVE files (a stale manifest must fail)
    live = {
        "contract": os.path.join(_HERE, "exp5_item_contract.md"),
        "contract_manifest": os.path.join(_HERE,
                                          "exp5_item_contract.manifest.json"),
        "wrapper": os.path.join(KF, "drafting_wrapper.md"),
        "protocol": os.path.join(KF, "protocol.md"),
        "inputs_manifest": HASHES,
    }
    for k, p in live.items():
        assert m["pins"][k] == hashlib.sha256(open(p, "rb").read()).hexdigest(),             f"pin {k} stale vs live file"
    # v2.1: the 60-200 quote band is DEAD LAW (it was never in the WorkOrder);
    # the contract is now 37 model-owned fields + a verbatim, non-blank quote.
    assert "quote_minLength" not in m["schema"] and "quote_maxLength" not in m["schema"]
    assert m["schema"]["model_owned_fields"] == 37
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
    gi = {"driver_name": "revenue", "driver_state": "reported", "quote": q,
          "level_low": 5, "level_high": 5, "level_shape_hint": "point",
          "level_unit_raw": "USD millions", "level_unit_kind_hint": "money",
          "level_money_mode_hint": "aggregate", "time_type": "duration",
          "period_start_date": "2026-01-01", "period_end_date": "2026-03-31",
          "slice": g_slice, "measurement_raw_spans": g_meas or []}
    pi = dict(gi, slice=p_slice, measurement_raw_spans=p_meas or [])
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": gi,
                    "gold_extra": {"expectation_comparison_present": False}}]}
    arm = {"E1": {"facts": [{"lane": "metric", "quote": q, "gold_item": pi}]}}
    return gold, arm


def test_scorer_wrong_slice_drops_accuracy():
    gold, arm = _metric_pair(["segment:acetylchain"], ["segment:engineered"])
    r = score_arm(gold, arm, _META1, _full_verdicts())
    assert r["value_shape_acc"] < 1.0 and r["PASS"] is False


def test_scorer_wrong_measurement_drops_accuracy():
    gold, arm = _metric_pair([], [], g_meas=["adjusted"], p_meas=[])
    r = score_arm(gold, arm, _META1, _full_verdicts())
    assert r["value_shape_acc"] < 1.0


def test_scorer_measurement_normalization_equivalent():
    assert _meas_tokens({"measurement_raw_spans": ["Adjusted Diluted"]}) ==         _meas_tokens({"measurement_raw_spans": ["adjusted_diluted"]})


def test_scorer_unit_aware_value_match():
    a = _canon_level({"driver_name": "revenue", "level_low": 726,
                     "level_high": 726, "level_unit_raw": "USD millions",
                     "level_unit_kind_hint": "money",
                     "level_money_mode_hint": "aggregate"})
    b = _canon_level({"driver_name": "revenue", "level_low": Decimal("0.726"),
                     "level_high": Decimal("0.726"), "level_unit_raw": "USD billions",
                     "level_unit_kind_hint": "money",
                     "level_money_mode_hint": "aggregate"})
    assert set(a) == set(b) and a[0][0] == "m_usd"


def test_scorer_union_recall_beats_single():
    q1, q2 = "a" * 80, "b" * 80
    def gfact(q):
        return {"lane": "metric", "du_worthy": True, "quote": q,
                "gold_item": {"quote": q},
                "gold_extra": {"expectation_comparison_present": False}}
    gold = {"E1": [gfact(q1), gfact(q2)]}
    arm_a = {"E1": {"facts": [{"lane": "metric", "quote": q1, "gold_item": {}}]}}
    arm_b = {"E1": {"facts": [{"lane": "metric", "quote": q2, "gold_item": {}}]}}
    ra = score_arm(gold, arm_a, _META1)["recall"]
    ru = score_union(gold, arm_a, arm_b, _META1)["recall"]
    assert ra == 0.5 and ru == 1.0


def test_scorer_parks_grounded_surprise_without_home_sibling():
    q = "c" * 80
    gold = {"E1": [{"lane": "surprise", "du_worthy": True, "quote": q,
                    "gold_item": {},
                    "gold_extra": {"expectation_comparison_present": True}}]}
    arm = {"E1": {"facts": [{"lane": "surprise", "quote": q, "gold_item": {
        "surprise_basis_hint": "actual", "comparison_baseline": "consensus",
        "level_low": 5, "level_high": 5, "level_shape_hint": "point",
        "level_unit_raw": "USD millions", "time_type": "duration",
        "period_start_date": "2026-01-01",
        "period_end_date": "2026-03-31"}}]}}
    r = score_arm(gold, arm, _META1, _full_verdicts())
    assert r["would_park"] > 0.10 and r["PASS"] is False


def test_scorer_emits_ambiguous_for_grader():
    q = "d" * 80
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": {"quote": q},
                    "gold_extra": {"expectation_comparison_present": False}}]}
    arm = {"E1": {"facts": [
        {"lane": "metric", "quote": q, "gold_item": {}},
        {"lane": "metric", "quote": q, "gold_item": {}}]}}
    r = score_arm(gold, arm, _META1)
    assert len(r["ambiguous_rows"]) >= 1
    assert r["matched"] == 0        # ambiguous stays UNSCORED


# ---- round-13 direct failure tests ----


def test_e2e_unit_value_match_now_works():
    """Round-13 guard, RESCOPED 2026-07-25. Unit-aware canonical equality
    (726 USD millions == 0.726 USD billions) must still hold — that capability
    is what round 13 fixed and must never silently break. What CHANGED: equal
    canonical value with NON-overlapping quotes no longer AUTO-matches (it
    could pair different periods/slices/measurements); it now forms a grader
    candidate. Both facts are asserted here."""
    gi_g = {"driver_name": "revenue", "driver_state": "reported",
            "quote": "a" * 80, "level_low": 726, "level_high": 726,
            "level_shape_hint": "point", "level_unit_raw": "USD millions",
            "level_unit_kind_hint": "money", "level_money_mode_hint":
            "aggregate", "time_type": "duration",
            "period_start_date": "2026-01-01",
            "period_end_date": "2026-03-31"}
    gi_p = dict(gi_g, level_low=Decimal("0.726"), level_high=Decimal("0.726"),
                level_unit_raw="USD billions", quote="b" * 80)
    # (1) the CAPABILITY survives: 726M and 0.726B are canonically equal
    from score_exp5 import _value_eq, match as _match
    g_fact = {"lane": "metric", "quote": "a" * 80, "gold_item": gi_g}
    p_fact = {"lane": "metric", "quote": "b" * 80, "gold_item": gi_p}
    assert _value_eq(g_fact, p_fact) is True, "unit-aware canonical equality broke"
    # (2) but equal value + different evidence is a GRADER CANDIDATE, not a match
    pairs, _ug, _up, ambiguous = _match([g_fact], [p_fact])
    assert pairs == [] and len(ambiguous) == 1
    assert ambiguous[0]["reason"] == "value_match_same_name"
    # (3) end-to-end: with the SAME source evidence they pair and score 1.0
    same_q = "Revenue was $726 million for the first quarter of the year."
    gold2 = {"E1": [{"lane": "metric", "du_worthy": True, "quote": same_q,
                     "gold_item": dict(gi_g, quote=same_q),
                     "gold_extra": {"expectation_comparison_present": False}}]}
    arm2 = {"E1": {"facts": [{"lane": "metric", "quote": same_q,
                              "gold_item": dict(gi_p, quote=same_q)}]}}
    assert score_arm(gold2, arm2, _META1)["recall"] == 1.0


def test_exact_decimal_no_rounding_merge():
    a = _canon_level({"driver_name": "x", "level_low": Decimal("1.00000004"),
                      "level_high": Decimal("1.00000004"), "level_unit_raw": "USD",
                      "level_unit_kind_hint": "money",
                      "level_money_mode_hint": "aggregate"})
    b = _canon_level({"driver_name": "x", "level_low": Decimal("1.00000014"),
                      "level_high": Decimal("1.00000014"), "level_unit_raw": "USD",
                      "level_unit_kind_hint": "money",
                      "level_money_mode_hint": "aggregate"})
    assert set(a) != set(b), "distinct values must never merge"


def test_fact16_change_value_requires_change_unit():
    codes, _ = check_item({"change_value": 5}, "metric")
    assert "CHANGE_UNIT_REQUIRED" in codes
    codes2, _ = check_item({"change_value": 5, "change_unit_raw": "percent"},
                           "metric")
    assert "CHANGE_UNIT_REQUIRED" not in codes2


def _surprise_with_home(home_period_end, home_driver="revenue",
                        home_value=726):
    q1, q2 = "s" * 80, "h" * 80
    sp = {"lane": "surprise", "quote": q1, "gold_item": {
        "driver_name": "revenue_surprise", "surprise_basis_hint": "actual",
        "comparison_baseline": "consensus", "level_low": 726,
        "level_high": 726, "level_shape_hint": "point",
        "level_unit_raw": "USD millions", "level_unit_kind_hint": "money",
        "level_money_mode_hint": "aggregate", "time_type": "duration",
        "period_start_date": "2026-01-01", "period_end_date": "2026-03-31"}}
    home = {"lane": "metric", "quote": q2, "gold_item": {
        "driver_name": home_driver, "level_low": home_value,
        "level_high": home_value, "level_shape_hint": "point",
        "level_unit_raw": "USD millions", "level_unit_kind_hint": "money",
        "level_money_mode_hint": "aggregate", "time_type": "duration",
        "period_start_date": "2026-01-01",
        "period_end_date": home_period_end}}
    gold = {"E1": [{"lane": "surprise", "du_worthy": True, "quote": q1,
                    "gold_item": {},
                    "gold_extra": {"expectation_comparison_present": True}}]}
    arm = {"E1": {"facts": [sp, home]}}
    return gold, arm


def test_home_fact_correct_sibling_no_park():
    gold, arm = _surprise_with_home("2026-03-31")
    assert score_arm(gold, arm, _META1)["would_park"] == 0.0


def test_home_fact_wrong_period_parks():
    gold, arm = _surprise_with_home("2026-06-30")
    assert score_arm(gold, arm, _META1)["would_park"] > 0.0


def test_home_fact_unrelated_driver_parks():
    gold, arm = _surprise_with_home("2026-03-31", home_driver="fuel_cost")
    assert score_arm(gold, arm, _META1)["would_park"] > 0.0


def test_home_fact_value_mismatch_parks():
    gold, arm = _surprise_with_home("2026-03-31", home_value=999)
    assert score_arm(gold, arm, _META1)["would_park"] > 0.0


def test_union_dedup_no_inflation():
    from score_exp5 import dedup_items
    f = {"lane": "metric", "quote": "q" * 80, "gold_item": {"level_low": 5,
         "level_high": 5}}
    assert len(dedup_items([f, dict(f)])) == 1


def test_presence_disagreement_metric():
    q1, q2 = "a" * 80, "b" * 80
    def gfact(q):
        return {"lane": "metric", "du_worthy": True, "quote": q,
                "gold_item": {"quote": q},
                "gold_extra": {"expectation_comparison_present": False}}
    gold = {"E1": [gfact(q1), gfact(q2)]}
    arm_a = {"E1": {"facts": [{"lane": "metric", "quote": q1,
                               "gold_item": {}}]}}
    arm_b = {"E1": {"facts": [{"lane": "metric", "quote": q2,
                               "gold_item": {}}]}}
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
from score_exp5 import _canon_item_values, _home_ok


def test_home_unresolved_periods_never_match():
    sp = {"lane": "surprise", "quote": "s" * 80, "gold_item": {
        "driver_name": "revenue_surprise", "surprise_basis_hint": "actual",
        "comparison_baseline": "consensus"}}
    home = {"lane": "metric", "quote": "h" * 80,
            "gold_item": {"driver_name": "revenue"}}
    assert _home_ok(sp, [sp, home], 12) is False


def test_home_numberless_needs_numberless():
    sp = {"lane": "surprise", "quote": "s" * 80, "gold_item": {
        "driver_name": "revenue_surprise", "surprise_basis_hint": "actual",
        "comparison_baseline": "consensus", "time_type": "duration",
        "period_start_date": "2026-01-01", "period_end_date": "2026-03-31"}}
    home_numbered = {"lane": "metric", "quote": "h" * 80, "gold_item": {
        "driver_name": "revenue", "level_low": 5, "level_high": 5,
        "level_shape_hint": "point", "level_unit_raw": "USD",
        "time_type": "duration", "period_start_date": "2026-01-01",
        "period_end_date": "2026-03-31"}}
    assert _home_ok(sp, [sp, home_numbered], 12) is False
    home_numberless = {"lane": "metric", "quote": "h" * 80, "gold_item": {
        "driver_name": "revenue", "driver_state": "unknown",
        "quote": "the stated numberless reading quoted verbatim from source",
        "time_type": "duration",
        "period_start_date": "2026-01-01", "period_end_date": "2026-03-31"}}
    assert _home_ok(sp, [sp, home_numberless], 12) is True


def test_home_slice_and_scope_must_match():
    base_sp = {"driver_name": "revenue_surprise",
               "surprise_basis_hint": "actual",
               "comparison_baseline": "consensus", "time_type": "duration",
               "period_start_date": "2026-01-01",
               "period_end_date": "2026-03-31", "slice": ["segment:a"]}
    sp = {"lane": "surprise", "quote": "s" * 80, "gold_item": base_sp}
    home_wrong_slice = {"lane": "metric", "quote": "h" * 80, "gold_item": {
        "driver_name": "revenue", "time_type": "duration",
        "period_start_date": "2026-01-01", "period_end_date": "2026-03-31",
        "slice": ["segment:b"]}}
    assert _home_ok(sp, [sp, home_wrong_slice], 12) is False


def test_unresolved_tie_blocks_pass():
    q1, q2 = "t" * 80, "u" * 80
    def gf(q):
        return {"lane": "metric", "du_worthy": True, "quote": q,
                "gold_item": {"quote": q},
                "gold_extra": {"expectation_comparison_present": False}}
    gold = {"E1": [gf(q1)] * 19 + [gf(q2)]}
    facts = [{"lane": "metric", "quote": q2, "gold_item": {}},
             {"lane": "metric", "quote": q2, "gold_item": {}}]
    facts += [{"lane": "metric", "quote": q1, "gold_item": {}}
              for _ in range(19)]
    arm = {"E1": {"facts": facts}}
    V = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(20)}
    r = score_arm(gold, arm, _META1, V)
    assert r["ambiguities_unresolved"] >= 1 and r["PASS"] is None


def test_ambiguity_resolution_input_works():
    q = "t" * 80
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": {"quote": q},
                    "gold_extra": {"expectation_comparison_present": False}}]}
    arm = {"E1": {"facts": [{"lane": "metric", "quote": q, "gold_item": {}},
                            {"lane": "metric", "quote": q, "gold_item": {}}]}}
    V = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    r = score_arm(gold, arm, _META1, V, ambiguity_resolutions={("E1", 0): 1})
    assert r["matched"] == 1 and r["ambiguities_unresolved"] == 0


def test_union_keeps_different_facts():
    from score_exp5 import dedup_items
    f1 = {"lane": "metric", "quote": "q" * 80, "gold_item": {
        "level_low": 5, "level_high": 5, "period_end_date": "2026-03-31"}}
    f2 = {"lane": "metric", "quote": "q" * 80, "gold_item": {
        "level_low": 5, "level_high": 5, "period_end_date": "2025-03-31"}}
    assert len(dedup_items([f1, f2])) == 2
    assert len(dedup_items([f1, dict(f1)])) == 1


def test_state_accuracy_not_diluted():
    q = [chr(65 + i) * 80 for i in range(10)]     # A*80, B*80 ... distinct
    def gf(i):
        return {"lane": "metric", "du_worthy": True, "quote": q[i],
                "gold_item": {"quote": q[i]},
                "gold_extra": {"expectation_comparison_present": False}}
    gold = {"E1": [gf(i) for i in range(10)]}
    arm = {"E1": {"facts": [{"lane": "metric", "quote": q[i],
                             "gold_item": {}} for i in range(10)]}}
    V = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(10)}
    V[("E1", 0)] = dict(V[("E1", 0)], driver_state=False)   # 9/10 state
    r = score_arm(gold, arm, _META1, V)
    assert r["state_acc"] == 0.9 and r["PASS"] is False


def test_false_lane_verdict_increments_wrong_lane():
    q = "w" * 80
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": {"quote": q},
                    "gold_extra": {"expectation_comparison_present": False}}]}
    arm = {"E1": {"facts": [{"lane": "metric", "quote": q, "gold_item": {}}]}}
    V = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    V[("E1", 0)]["lane_routing"] = False
    r = score_arm(gold, arm, _META1, V)
    assert r["wrong_lane"] == 1 and r["PASS"] is False


def test_large_ints_never_merge():
    a = _canon_item_values({"level_low": 2 ** 60, "level_high": 2 ** 60})
    b = _canon_item_values({"level_low": 2 ** 60 + 1,
                            "level_high": 2 ** 60 + 1})
    assert a["level"] != b["level"]


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
             "launch_kfields_drafts.manifest.json")
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
    q = "m" * 80
    gi = {"driver_name": "revenue", "level_unit_kind_hint": "money",
          "level_money_mode_hint": "aggregate", "quote": q}
    pi = dict(gi)
    gi.update(g_over or {})
    pi.update(p_over or {})
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": gi,
                    "gold_extra": {"expectation_comparison_present": False}}]}
    arm = {"E1": {"facts": [{"lane": "metric", "quote": q, "gold_item": pi}]}}
    V = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    return score_arm(gold, arm, _META1, V)


def test_wrong_driver_name_fails():
    r = _matched_pair(p_over={"driver_name": "fuel_cost"})
    assert r["wrong_name"] >= 1 and r["PASS"] is False


def test_wrong_unit_hints_fail():
    r = _matched_pair(p_over={"level_unit_kind_hint": "ratio",
                              "level_money_mode_hint": "price_like"})
    assert r["value_shape_acc"] < 1.0 and r["PASS"] is False


def test_comparison_only_value_match():
    from score_exp5 import _value_eq
    g = {"gold_item": {"comparison_low": 3, "comparison_high": 3}}
    p = {"gold_item": {"comparison_low": 3, "comparison_high": 3}}
    assert _value_eq(g, p) is True


def test_change_only_value_match():
    from score_exp5 import _value_eq
    g = {"gold_item": {"change_value": 12, "change_unit_raw": "percent"}}
    p = {"gold_item": {"change_value": 12, "change_unit_raw": "percent"}}
    assert _value_eq(g, p) is True


def _home_case(home_item_over, sp_over=None):
    sp_gi = {"driver_name": "revenue_surprise", "surprise_basis_hint": "actual",
             "comparison_baseline": "consensus", "time_type": "duration",
             "period_start_date": "2026-01-01",
             "period_end_date": "2026-03-31", "level_low": 5, "level_high": 5,
             "level_shape_hint": "point", "level_unit_raw": "USD"}
    sp_gi.update(sp_over or {})
    home_gi = {"driver_name": "revenue", "time_type": "duration",
               "period_start_date": "2026-01-01",
               "period_end_date": "2026-03-31"}
    home_gi.update(home_item_over)
    sp = {"lane": "surprise", "quote": "s" * 80, "gold_item": sp_gi}
    home = {"lane": "metric", "quote": "h" * 80, "gold_item": home_gi}
    return _home_ok(sp, [sp, home], 12)


def test_home_point_vs_floor_rejected():
    # surprise = POINT 5; home = FLOOR >=5 — must NOT satisfy the home law
    assert _home_case({"level_low": 5, "level_shape_hint": "floor",
                       "level_unit_raw": "USD"}) is False


def test_home_point_matches_point():
    assert _home_case({"level_low": 5, "level_high": 5,
                       "level_shape_hint": "point",
                       "level_unit_raw": "USD"}) is True


def test_home_numberless_requires_unknown_state():
    numberless_sp = {"level_low": None, "level_high": None,
                     "level_shape_hint": None, "level_unit_raw": None}
    assert _home_case({}, sp_over=numberless_sp) is False       # no state
    assert _home_case({"driver_state": "reported"},
                      sp_over=numberless_sp) is False            # wrong state
    assert _home_case({"driver_state": "unknown",
                       "quote": "the stated numberless reading quoted here"},
                      sp_over=numberless_sp) is True


def test_union_accepts_tie_resolutions():
    q = "t" * 80
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": {"quote": q},
                    "gold_extra": {"expectation_comparison_present": False}}]}
    arm_a = {"E1": {"facts": [{"lane": "metric", "quote": q, "gold_item": {}}]}}
    arm_b = {"E1": {"facts": [{"lane": "metric", "quote": q,
                               "gold_item": {"fiscal_year": 2026}}]}}
    V = {("E1", 0): {k: True for k in MEANING_FIELDS}}
    r = score_union(gold, arm_a, arm_b, _META1, V,
                    ambiguity_resolutions={("E1", 0): 0})
    assert r["ambiguities_unresolved"] == 0 and r["matched"] == 1


def test_empty_arm_is_definite_fail():
    q = "e" * 80
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": {"quote": q},
                    "gold_extra": {"expectation_comparison_present": False}}]}
    r = score_arm(gold, {"E1": {"facts": []}}, _META1)
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
        return {"lane": "metric", "du_worthy": True, "quote": qs[i],
                "gold_item": {"driver_name": "revenue", "quote": qs[i]},
                "gold_extra": {"expectation_comparison_present": False}}
    gold = {"E1": [gf(i) for i in range(20)]}
    facts = [{"lane": "metric", "quote": qs[i],
              "gold_item": {"driver_name": ("W" + str(i) if i < 11
                                            else "revenue")}}
             for i in range(20)]
    V = {("E1", i): {k: True for k in MEANING_FIELDS} for i in range(20)}
    r = score_arm(gold, {"E1": {"facts": facts}}, _META1, V)
    assert r["wrong_name"] == 11 and r["PASS"] is False


def test_shared_endpoint_never_matches():
    from score_exp5 import _value_eq
    g = {"gold_item": {"level_low": 5, "level_high": 10}}
    p = {"gold_item": {"level_low": 5, "level_high": 999}}
    assert _value_eq(g, p) is False
    assert _value_eq(g, {"gold_item": {"level_low": 5,
                                       "level_high": 10}}) is True


def test_numberless_home_requires_quote():
    sp = {"lane": "surprise", "quote": "s" * 80, "gold_item": {
        "driver_name": "revenue_surprise", "surprise_basis_hint": "actual",
        "comparison_baseline": "consensus", "time_type": "duration",
        "period_start_date": "2026-01-01", "period_end_date": "2026-03-31"}}
    base_home = {"driver_name": "revenue", "driver_state": "unknown",
                 "time_type": "duration", "period_start_date": "2026-01-01",
                 "period_end_date": "2026-03-31"}
    no_q = {"lane": "metric", "quote": "h" * 80, "gold_item": dict(base_home)}
    with_q = {"lane": "metric", "quote": "h" * 80,
              "gold_item": dict(base_home, quote="the stated numberless "
                                                 "reading quoted verbatim "
                                                 "from the source text")}
    assert _home_ok(sp, [sp, no_q], 12) is False
    assert _home_ok(sp, [sp, with_q], 12) is True


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
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": {"quote": q},
                    "gold_extra": {"expectation_comparison_present": False}}]}
    assert score_arm(gold, {"E1": {"facts": []}}, _META1)["PASS"] is False


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


def test_presence_disagreement_uses_tie_decisions():
    q = "p" * 80
    gold = {"E1": [{"lane": "metric", "du_worthy": True, "quote": q,
                    "gold_item": {"quote": q},
                    "gold_extra": {"expectation_comparison_present": False}}]}
    tie_arm = {"E1": {"facts": [{"lane": "metric", "quote": q, "gold_item": {}},
                                {"lane": "metric", "quote": q,
                                 "gold_item": {}}]}}
    empty = {"E1": {"facts": []}}
    # without a tie decision the ambiguous gold is uncaptured -> 0/0 = 0.0
    assert presence_disagreement(gold, tie_arm, empty, _META1) == 0.0
    # WITH the tie decision, run A captures it -> exactly-one/either = 1.0
    assert presence_disagreement(gold, tie_arm, empty, _META1,
                                 resolutions_a={("E1", 0): 0}) == 1.0


# ---- the meta-proof: this suite touched NO frozen file ----

def test_zz_frozen_untouched():
    assert _frozen_state() == FROZEN_BEFORE
