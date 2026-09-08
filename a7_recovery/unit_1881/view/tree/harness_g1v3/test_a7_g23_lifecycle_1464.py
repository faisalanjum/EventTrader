# -*- coding: utf-8 -*-
"""The G2 and G3 runs, driven through the REAL lifecycle with ZERO calls.

Codex SEQ 1464.3 was right about the earlier claim: asserting that G1's helper
names exist in an empty directory is not lifecycle reuse. Everything here calls
the actual `freeze_root`, `publish_run`, `preflight`, `save_results` and
`finalize_segment`, on a real frozen candidate, and no launcher is ever armed.
"""
import collections
import hashlib
import io
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: THE RECOVERY PACKAGE, BOUND FIRST - the native import order, reused.
#: Importing any harness module runs `a1_reader`, which puts the frozen bench
#: root at sys.path[0]; that bench copy of `driver.core` holds no
#: `xbrl_attach`, so every event became unroutable and each proof below refused
#: UPSTREAM of the boundary it names. Binding the MAIN tree instead was the
#: same mistake with a different wrong package: the two trees differ in
#: `driver_validators.py`, and `xbrl_attach` is byte-identical in both, so its
#: resolution proves nothing (Codex SEQ 1878). This is native_1876's own order.
_RECOVERY = "/home/faisal/EventMarketDB-driver-recovery"
if _RECOVERY not in sys.path:
    sys.path.insert(0, _RECOVERY)
import driver.core.driver_validators as _DV                      # noqa: E402

#: PROVED IN THIS CHILD, not by a separate probe: the validators actually
#: bound here must be the approved recovery bytes the runner pins.
_DV_SHA = hashlib.sha256(io.open(_DV.__file__, "rb").read()).hexdigest()
assert _DV_SHA == os.environ.get("A7_DRIVER_VALIDATORS_SHA"), (
    "this child bound %s (%s), not the approved recovery driver_validators"
    % (_DV.__file__, _DV_SHA))

import a7_g1_build as G          # noqa: E402
import a7_g23_build as B         # noqa: E402
import a7_g23_run as R           # noqa: E402
import a7_g1_complete_v2 as CV   # noqa: E402


def _named_path(var):
    """A path the RUNNER names. Never a default.

    A missing name FAILS here rather than skipping: a silent skip would report
    green for a boundary nobody reached.
    """
    path = os.environ.get(var)
    assert path and os.path.exists(path), (
        "%s must name an existing path; these proofs must not fall back to "
        "another producer, lifecycle or candidate" % var)
    return path


def _named_json(var):
    """A JSON document at a path the RUNNER names."""
    with io.open(_named_path(var), encoding="utf-8") as fh:
        return json.load(fh)


#: THE run these proofs are about, named out loud by the runner: the approved
#: G1's OWN producer, the one the verified native run used. `_PR.load(
#: G.PRIMARY)` loaded a DIFFERENT run, so the approved G1 candidate refused to
#: resolve it (Codex SEQ 1875/1877).
RUN = _named_json("A7_PRODUCER_IDENTITY")["historical_g1"]["producer_identity"]

#: NO historical-v1 marker. This module's producer and the current era owner
#: both say .v3, so the v1 relaxation does not apply to it (Codex SEQ 1879).
#: Other historical modules keep their own marker.

_C = {}


def _approved_g1():
    """The approved G1 lifecycle HANDLE, from a location the runner names.

    A handle and a path only - never grader evidence.
    """
    return _named_json("A7_G1_PINS")


def _frozen():
    """The G2 and G3 candidate, from the SEALED verified population.

    That population build is verified end to end and must not be rebuilt or
    rerouted here (Codex SEQ 1877/1879), so this reuses THAT artifact's own
    bytes instead of routing every event again once per session.
    """
    if "frozen" not in _C:
        cand = _named_path("A7_G23_CANDIDATE")
        doc = G._read(os.path.join(cand, R.CANDIDATE_NAME))
        pdir = os.path.join(cand, R.PROMPT_DIRNAME)
        prompts = {f[:-len(".prompt.txt")]:
                   io.open(os.path.join(pdir, f), encoding="utf-8").read()
                   for f in os.listdir(pdir) if f.endswith(".prompt.txt")}
        _key, identity = G.live_key()
        _C["frozen"] = (doc, prompts, identity)
    return _C["frozen"]


def _required_populations():
    """The post-G1 populations this scoring requires, from the SAME frozen
    candidate the sources were built from. This is the approved interface:
    `official_verdict_maps` compares the persisted candidate against it."""
    doc, _prompts, _identity = _frozen()
    return {"G2": doc["g2_pairs"], "G3": doc["g3_idxs"]}


def _candidate(tmp_path, kind):
    doc, prompts, identity = _frozen()
    out = str(tmp_path / ("cand_" + kind))
    os.makedirs(out)
    path, sha = R.write_kind(out, kind, doc, prompts, identity)
    return out, sha, G._read(path)


def _lawful_reply(kind, question_ids):
    if kind == "G2":
        return json.dumps([
            {"question_id": q,
             "verdicts": {f: True for f in B.meaning_fields()}}
            for q in question_ids])
    return json.dumps([{"question_id": q, "bucket": B.extras_buckets()[0]}
                       for q in question_ids])


def _record_state(tmp_path, monkeypatch, run, n, root_sha, receipt_sha,
                  errors=None):
    """A FAITHFUL official Workflow state that echoes what was captured.

    The same helper and the same seam G1's own proofs use; PROJECTS_ROOT is
    redirected into the test directory so nothing touches the live session.
    """
    import audit_worker_access as AUD
    import g1_fake_state as FAKE
    monkeypatch.setattr(AUD, "PROJECTS_ROOT",
                        os.path.join(str(tmp_path), "projects"), raising=False)
    answers = {}
    for capture in G._captures_of(run, n):
        lane = capture["returned"].get("lane_id")
        if lane:
            answers[lane] = G._capture_text(run, capture)
    # A LANE THAT RETURNED NO TEXT MUST APPEAR AS AN ERROR in the official
    # state too, or the state and the capture disagree and finalize refuses for
    # the wrong reason.
    state = FAKE.build(str(tmp_path), run, n, G, answers=answers,
                       errors=errors or {})
    problems = G.record_official_state(run, n, state, root_sha, receipt_sha)
    assert problems == [], problems[:3]
    return state


def _drive(tmp_path, kind, reply_for=None, tamper=None, stop_after=None,
           monkeypatch=None, tamper_raw_before_finalize=False):
    """freeze_root -> publish_run -> preflight -> save_results -> finalize.

    `reply_for(lane_id, question_ids)` supplies each lane's text; the default
    is a lawful reply. NOTHING here calls a model.
    """
    out, sha, doc = _candidate(tmp_path, kind)
    run = str(tmp_path / ("run_" + kind))
    root, root_sha, problems = G.freeze_root(out, run, sha)
    assert problems == [], problems[:3]
    if stop_after == "root":
        return {"out": out, "run": run, "root": root, "root_sha": root_sha}

    lanes = [r["lane_id"] for r in root["rows"]][:len(G.GRADER_LANES)]
    identity, problems = G.publish_run(out, run, root_sha, lanes)
    assert problems == [], problems[:3]
    n, receipt_sha = identity["segment"], identity["receipt_sha256"]

    packet, problems = G.preflight(out, run, n, root_sha, receipt_sha)
    assert problems == [], problems[:3]
    if tamper:
        tamper(out, run, n, packet)
    if stop_after == "preflight":
        return {"out": out, "run": run, "root_sha": root_sha, "n": n,
                "receipt_sha": receipt_sha, "packet": packet}

    receipt = G.load_receipt(run, n)
    results = []
    for arg in packet["args"]:
        qids = G.binding_and_parser(kind)[0](
            doc, arg["batch_id"])["question_ids"]
        text = (reply_for(arg["lane_id"], qids) if reply_for
                else _lawful_reply(kind, qids))
        row = collections.OrderedDict(
            (f, arg.get(f)) for f in G.RESULT_BINDING)
        # the publication supplies this one, exactly as the real runtime does
        row["invocation_sha256"] = receipt["invocation_sha256"]
        row["text"] = text
        row["error"] = None
        results.append(row)
    accounting, problems = G.save_results(run, n, results, root_sha,
                                          receipt_sha)
    assert problems == [], problems[:3]
    if monkeypatch is not None:
        _record_state(tmp_path, monkeypatch, run, n, root_sha, receipt_sha)
    if tamper_raw_before_finalize:
        raw_dir = os.path.join(run, G.RAW_DIRNAME)
        name = sorted(os.listdir(raw_dir))[0]
        with io.open(os.path.join(raw_dir, name), "a", encoding="utf-8") as fh:
            fh.write(" ")
    final, rulings, problems = G.finalize_segment(out, run, n, root_sha,
                                                  receipt_sha)
    return {"out": out, "run": run, "root_sha": root_sha, "n": n,
            "receipt_sha": receipt_sha, "packet": packet,
            "accounting": accounting, "final": final, "rulings": rulings,
            "problems": problems, "doc": doc, "candidate_sha": sha}


# ------------------------------------------------------- the lawful control --
@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_lawful_reply_completes_the_real_lifecycle_with_zero_calls(
        kind, tmp_path, monkeypatch):
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    assert got["problems"] == [], got["problems"][:3]
    final = got["final"]
    assert final["attempt"] == 1
    assert final["retry"] == [], "a lawful reply asked for a retry"
    assert final["uncalled"] == []
    assert got["rulings"], "no lane produced a ruling"
    # and the run really is on disk, through the SAME paths G1 uses
    for path in (G.root_path(got["run"]), G.receipt_path(got["run"], got["n"]),
                 G.accounting_path(got["run"], got["n"]),
                 G.finalization_path(got["run"], got["n"])):
        assert os.path.isfile(path), path
    # ZERO ARMED CALLS: the candidate says so and no launcher was executed
    assert G._read(os.path.join(got["out"], G.CANDIDATE_NAME))["made_calls"] == 0


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_the_candidate_declares_its_kind_and_dispatches_to_its_own_parser(
        kind, tmp_path):
    _out, _sha, doc = _candidate(tmp_path, kind)
    assert G.task_kind(doc) == kind
    binding, parser = G.binding_and_parser(kind)
    assert parser is (B.read_meaning_reply if kind == "G2"
                      else B.read_extras_reply)
    row = doc["batch_rows"][0]
    assert binding(doc, row["batch_id"])["question_ids"] == row["question_ids"]


# ------------------------------------------------ every malformed reply class --
def _bad(kind, mode):
    def make(_lane_id, qids):
        lawful = json.loads(_lawful_reply(kind, qids))
        if mode == "missing":
            return json.dumps(lawful[:-1])
        if mode == "duplicate":
            return json.dumps(lawful + [lawful[0]])
        if mode == "extra":
            row = dict(lawful[0]); row["question_id"] = "Qnot-in-this-batch"
            return json.dumps(lawful + [row])
        if mode == "wrong_membership":
            row = dict(lawful[0]); row["question_id"] = "Q" + "0" * 16
            return json.dumps([row] + lawful[1:])
        if mode == "wrong_type":
            return json.dumps({"question_id": lawful[0]["question_id"]})
        if mode == "malformed":
            return "{not json at all"
        if mode == "prose":
            return "Here is my answer:\n" + json.dumps(lawful)
        if mode == "fenced":
            return "```json\n" + json.dumps(lawful) + "\n```"
        if mode == "null_verdict":
            row = json.loads(json.dumps(lawful[0]))
            if kind == "G2":
                for f in row["verdicts"]:
                    row["verdicts"][f] = None
            else:
                row["bucket"] = None
            return json.dumps([row] + lawful[1:])
        raise AssertionError(mode)
    return make


REFUSED = ["missing", "duplicate", "extra", "wrong_membership", "wrong_type",
           "malformed", "prose"]
ACCEPTED = ["fenced", "null_verdict"]


@pytest.mark.parametrize("kind", ["G2", "G3"])
@pytest.mark.parametrize("mode", REFUSED)
def test_an_unlawful_reply_is_refused_and_retried_never_credited(
        kind, mode, tmp_path, monkeypatch):
    got = _drive(tmp_path, kind, reply_for=_bad(kind, mode),
                 monkeypatch=monkeypatch)
    final = got["final"]
    assert final["retry"], "%s/%s was accepted" % (kind, mode)
    assert not final.get("rulings"), "an unlawful reply produced a ruling"


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_one_whole_fenced_json_block_is_lawful(kind, tmp_path, monkeypatch):
    got = _drive(tmp_path, kind, reply_for=_bad(kind, "fenced"),
                 monkeypatch=monkeypatch)
    assert got["problems"] == [], got["problems"][:3]
    assert got["final"]["retry"] == [], "a lawful fenced block was refused"


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_null_answer_is_lawful_but_settles_nothing(kind, tmp_path,
                                                    monkeypatch):
    got = _drive(tmp_path, kind, reply_for=_bad(kind, "null_verdict"),
                 monkeypatch=monkeypatch)
    assert got["problems"] == [], got["problems"][:3]
    assert got["final"]["retry"] == [], "null is a lawful answer"


# ----------------------------------------------------------- tamper + resume --
@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_tampered_raw_bytes_are_caught_BEFORE_the_first_finalize(kind, tmp_path,
                                                                 monkeypatch):
    """CAUSAL. Tampering after a finalize proves only that a finalization is
    immutable. This tampers before the FIRST finalize, so the raw hash is the
    only thing that can refuse it - and the same run finalizes clean without
    the tamper."""
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch,
                 tamper_raw_before_finalize=True)
    final = got["final"]
    caught = (final is None and bool(got["problems"])) or bool(
        (final or {}).get("retry"))
    assert caught, "the raw bytes changed before finalize and nothing noticed"


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_tampered_raw_bytes_are_caught_after_capture(kind, tmp_path,
                                                    monkeypatch):
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    assert got["final"]["retry"] == []
    raw_dir = os.path.join(got["run"], G.RAW_DIRNAME)
    name = sorted(os.listdir(raw_dir))[0]
    with io.open(os.path.join(raw_dir, name), "a", encoding="utf-8") as fh:
        fh.write(" ")
    final, _rulings, problems = G.finalize_segment(
        got["out"], got["run"], got["n"], got["root_sha"], got["receipt_sha"])
    # CAUGHT EITHER WAY. Refusing outright is the stronger answer than asking
    # for a retry, and the durable finalization is immutable, so the segment
    # cannot silently be re-classified against changed bytes.
    caught = (final is None and bool(problems)) or bool(
        (final or {}).get("retry"))
    assert caught, "the raw bytes changed and nothing noticed"


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_tampered_prompt_stops_the_preflight(kind, tmp_path):
    def tamper(out, _run, _n, _packet):
        doc = G._read(os.path.join(out, G.CANDIDATE_NAME))
        path = os.path.join(out, doc["batch_rows"][0]["prompt_path"])
        with io.open(path, "a", encoding="utf-8") as fh:
            fh.write("\ntampered\n")
    got = _drive(tmp_path, kind, tamper=tamper, stop_after="preflight")
    _packet, problems = G.preflight(got["out"], got["run"], got["n"],
                                    got["root_sha"], got["receipt_sha"])
    assert problems, "a tampered prompt reached the caller"


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_wrong_root_or_receipt_hash_is_refused(kind, tmp_path):
    got = _drive(tmp_path, kind, stop_after="preflight")
    _p, problems = G.preflight(got["out"], got["run"], got["n"], "0" * 64,
                               got["receipt_sha"])
    assert problems
    _p, problems = G.preflight(got["out"], got["run"], got["n"],
                               got["root_sha"], "0" * 64)
    assert problems


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_an_interrupted_run_resumes_without_repeating_a_segment(
        kind, tmp_path, monkeypatch):
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    run, out, root_sha = got["run"], got["out"], got["root_sha"]
    done = G.segments(run)
    assert done == [got["n"]]
    # a fresh publish must take the NEXT segment, never re-open the finished one
    doc = G._read(os.path.join(out, G.CANDIDATE_NAME))
    lanes = [r["lane_id"] for r in G.load_root(run, root_sha)["rows"]][
        len(G.GRADER_LANES):len(G.GRADER_LANES) * 2]
    identity, problems = G.publish_run(out, run, root_sha, lanes)
    assert problems == [], problems[:3]
    assert identity["segment"] == got["n"] + 1
    assert sorted(G.segments(run)) == [got["n"], got["n"] + 1]


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_second_freeze_of_the_same_run_is_refused(kind, tmp_path):
    got = _drive(tmp_path, kind, stop_after="root")
    _root, _sha, problems = G.freeze_root(got["out"], got["run"],
                                          G._sha_file(os.path.join(
                                              got["out"], G.CANDIDATE_NAME)))
    assert problems, "the run was frozen twice"


# ------------- Codex 1465.5: two blind lanes must RECONCILE before credit --
def _per_lane(kind, first_map, second_map):
    """Serve lane a and lane b different answers."""
    def make(lane_id, qids):
        which = first_map if lane_id.endswith(G.GRADER_LANES[0]) else second_map
        return json.dumps([which(q) for q in qids])
    return make


def _questions_of(doc, batches):
    """The frozen QUESTIONS those batches hold. The unit that is conserved is
    the question, not the call it happened to be packed into."""
    return {q for r in doc["batch_rows"] if r["batch_id"] in batches
            for q in r["question_ids"]}


def _ident(got):
    return CV.g23_identity(got["root_sha"], got["run"])


def _agree(kind):
    def row(q):
        if kind == "G2":
            return {"question_id": q,
                    "verdicts": {f: True for f in B.meaning_fields()}}
        return {"question_id": q, "bucket": B.extras_buckets()[0]}
    return row


def _disagree(kind):
    def row(q):
        if kind == "G2":
            v = {f: True for f in B.meaning_fields()}
            v[B.meaning_fields()[0]] = False        # one aspect differs
            return {"question_id": q, "verdicts": v}
        buckets = B.extras_buckets()
        return {"question_id": q, "bucket": buckets[1 % len(buckets)]}
    return row


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_two_agreeing_lanes_reconcile_and_are_credited(kind, tmp_path,
                                                       monkeypatch):
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch,
                 reply_for=_per_lane(kind, _agree(kind), _agree(kind)))
    assert got["problems"] == [], got["problems"][:2]
    res, probs = CV.complete_g23(got["doc"], got["rulings"], _ident(got))
    assert probs == [], probs[:2]
    served = {l.rsplit("/", 1)[0] for l in got["rulings"]}
    assert served, "no lane was served"
    all_batches = {r["batch_id"] for r in got["doc"]["batch_rows"]}
    # EVERY QUESTION OF THE SERVED BATCH IS CREDITED...
    assert set(res["credited"]) == _questions_of(got["doc"], served)
    # ...AND EVERY QUESTION NOBODY ANSWERED IS A DURABLE UNRESOLVED ROW.
    unanswered = _questions_of(got["doc"], all_batches - served)
    assert {u["question_id"] for u in res["unresolved"]} == unanswered
    assert res["credited_questions"] + len(unanswered) == res["questions"]


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_two_disagreeing_lanes_are_never_credited(kind, tmp_path, monkeypatch):
    """THE MUTATION. Both readings are individually USABLE and both parse; only
    reconciliation can refuse them, and before this seam existed nothing did."""
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch,
                 reply_for=_per_lane(kind, _agree(kind), _disagree(kind)))
    assert got["problems"] == [], got["problems"][:2]
    assert len(got["rulings"]) == len(G.GRADER_LANES), (
        "both lanes must be individually usable, or this proves nothing")
    res, probs = CV.complete_g23(got["doc"], got["rulings"], _ident(got))
    assert probs == [], probs[:2]
    served = {l.rsplit("/", 1)[0] for l in got["rulings"]}
    served_q = _questions_of(got["doc"], served)
    assert served_q and not (set(res["credited"]) & served_q), (
        "a disagreement was credited")
    blocked = [u for u in res["unresolved"] if u["question_id"] in served_q]
    # the reason survives, in full
    assert blocked and blocked[0]["reasons"], blocked[:1]


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_one_usable_lane_is_never_enough(kind, tmp_path, monkeypatch):
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    one = {k: v for k, v in list(got["rulings"].items())[:1]}
    res, _p = CV.complete_g23(got["doc"], one, _ident(got))
    served_q = _questions_of(got["doc"], {l.rsplit("/", 1)[0] for l in one})
    assert not (set(res["credited"]) & served_q), "one lane was enough"
    assert res["unresolved"]
    zero = CV.complete_g23(got["doc"], {}, _ident(got))[0]
    assert not zero["credited"], "no reading at all produced credit"
    # EVERY QUESTION unresolved, not an empty report and not a batch tally
    assert zero["unresolved_questions"] == zero["questions"]


# ------------------------------------- a GENUINELY interrupted segment ------
@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_an_interrupted_segment_retries_only_the_lane_that_failed(kind,
                                                                  tmp_path,
                                                                  monkeypatch):
    """The earlier version finished segment 1 and opened segment 2, which shows
    nothing about interruption. Here ONE lane returns no text, so the segment
    is genuinely incomplete, and the retry must name only that lane."""
    out, sha, doc = _candidate(tmp_path, kind)
    run = str(tmp_path / ("run_" + kind))
    root, root_sha, problems = G.freeze_root(out, run, sha)
    assert problems == []
    lanes = [r["lane_id"] for r in root["rows"]][:len(G.GRADER_LANES)]
    identity, problems = G.publish_run(out, run, root_sha, lanes)
    assert problems == []
    n, receipt_sha = identity["segment"], identity["receipt_sha256"]
    packet, problems = G.preflight(out, run, n, root_sha, receipt_sha)
    assert problems == []

    receipt = G.load_receipt(run, n)
    # the LAST attempted row: the audit requires a failure to be terminal
    dead = packet["args"][-1]["lane_id"]
    results = []
    for arg in packet["args"]:
        qids = G.binding_and_parser(kind)[0](doc, arg["batch_id"])["question_ids"]
        row = collections.OrderedDict((f, arg.get(f)) for f in G.RESULT_BINDING)
        row["invocation_sha256"] = receipt["invocation_sha256"]
        if arg["lane_id"] == dead:
            row["text"] = None
            row["error"] = "the agent returned no text"
        else:
            row["text"] = _lawful_reply(kind, qids)
            row["error"] = None
        results.append(row)
    _acc, problems = G.save_results(run, n, results, root_sha, receipt_sha)
    assert problems == [], problems[:2]
    _record_state(tmp_path, monkeypatch, run, n, root_sha, receipt_sha,
                  errors={dead: "the agent returned no text"})
    final, rulings, fin_problems = G.finalize_segment(out, run, n, root_sha,
                                                      receipt_sha)

    assert final is not None, fin_problems[:3]
    assert final["retry"] == [dead], (final["retry"], dead)
    assert dead not in rulings, "a lane with no text produced a ruling"
    assert len(rulings) == len(lanes) - 1, "the completed lane was lost"
    # AND the incomplete segment cannot be credited
    res, _p = CV.complete_g23(doc, rulings, "pin")
    served = {l.rsplit("/", 1)[0] for l in rulings}
    assert not (set(res["credited"]) & served)
    assert res["unresolved"]


# -------------------------------------- zero calls, from the LEDGER itself --
@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_the_whole_lifecycle_spends_nothing_measured_from_the_ledger(
        kind, tmp_path, monkeypatch):
    """`made_calls: 0` is the candidate's own claim about itself. This measures
    the real spend owner before and after a complete lifecycle."""
    before, _prov = G.all_prior_calls()
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    after, _prov2 = G.all_prior_calls()
    assert after == before, (before, after)
    # and the fake run left no launcher execution behind: every raw file is one
    # of ours, named by the ordinals this segment published
    raws = sorted(os.listdir(os.path.join(got["run"], G.RAW_DIRNAME)))
    assert raws, "no raw capture was written at all"
    expected = {G.raw_stem(r["ordinal"], 1) + ".raw.json"
                for r in G.load_receipt(got["run"], got["n"])["rows"]}
    assert set(raws) <= expected, sorted(set(raws) - expected)


# --------- Codex 1466.5: ONE durable, run-bound whole-run completion --------
@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_the_completion_is_persisted_once_and_reloads_bound_to_its_run(
        kind, tmp_path, monkeypatch):
    """An in-memory result is not a judgment: it cannot be re-read, cannot be
    checked, and cannot be the input scoring is pinned to."""
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    ident = _ident(got)
    result, problems = CV.complete_g23(got["doc"], got["rulings"], ident)
    assert problems == [], problems[:2]

    path, sha = CV.persist_g23(got["out"], result)
    assert os.path.isfile(path)

    # FRESH RELOAD: the live run is RE-HASHED here, not taken on trust
    again = CV.load_g23(got["out"], sha, got["root_sha"], got["run"])
    assert again["credited_questions"] == result["credited_questions"]
    assert again["unresolved_questions"] == result["unresolved_questions"]
    assert again["run_identity"] == ident
    assert again["run_identity"]["run_files"] > 0

    # WRITTEN ONCE: a second write is refused rather than overwriting a result
    with pytest.raises(ValueError):
        CV.persist_g23(got["out"], result)

    # A DIFFERENT VALID RUN is refused, though the bytes are the approved ones
    other = str(tmp_path / "another_run")
    os.makedirs(other)
    with io.open(os.path.join(other, "x.json"), "w", encoding="utf-8") as fh:
        fh.write("{}")
    with pytest.raises(ValueError):
        CV.load_g23(got["out"], sha, got["root_sha"], other)


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_post_run_tampering_with_the_completion_is_refused(kind, tmp_path,
                                                           monkeypatch):
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    result, _p = CV.complete_g23(got["doc"], got["rulings"], _ident(got))
    path, sha = CV.persist_g23(got["out"], result)
    # (a) the COMPLETION's own bytes
    with io.open(path, "a", encoding="utf-8") as fh:
        fh.write(" ")
    with pytest.raises(ValueError):
        CV.load_g23(got["out"], sha, got["root_sha"], got["run"])

    # (b) THE RUN TREE ITSELF, after the completion was written. Comparing a
    # recorded string to a recorded string could not see this at all.
    os.remove(path)
    result2, _p2 = CV.complete_g23(got["doc"], got["rulings"], _ident(got))
    path2, sha2 = CV.persist_g23(got["out"], result2)
    assert CV.load_g23(got["out"], sha2, got["root_sha"], got["run"])
    victim = os.path.join(got["run"], "receipt.json")
    with io.open(victim, "a", encoding="utf-8") as fh:
        fh.write(" ")
    with pytest.raises(ValueError):
        CV.load_g23(got["out"], sha2, got["root_sha"], got["run"])


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_two_lanes_from_different_attempts_are_combined_whole_run(kind,
                                                                  tmp_path,
                                                                  monkeypatch):
    """The two blind readings of one batch need not arrive together. A
    segment-scoped helper could only see whatever one segment held."""
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    lanes = sorted(got["rulings"])
    assert len(lanes) == len(G.GRADER_LANES)
    # simulate them arriving separately: neither half alone may credit
    for half in ({lanes[0]: got["rulings"][lanes[0]]},
                 {lanes[1]: got["rulings"][lanes[1]]}):
        res, _p = CV.complete_g23(got["doc"], half, _ident(got))
        assert not res["credited"], "one arrival credited a batch"
    # together, from whatever segments they came, they do
    both, _p = CV.complete_g23(got["doc"], got["rulings"], _ident(got))
    assert set(both["credited"]) == _questions_of(
        got["doc"], {lanes[0].rsplit("/", 1)[0]})


# ------- Codex 1468.5: the QUESTION is conserved, never the batch -----------
@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_one_mixed_batch_splits_per_question_and_is_never_both(kind, tmp_path,
                                                               monkeypatch):
    """Codex's own control. One agreed question beside one disagreeing question
    in the SAME call put that call into credited AND unresolved, and tripped
    the conservation check against itself. The batch is not the unit anyone
    judges; the question is."""
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    lanes = sorted(got["rulings"])
    batch = lanes[0].rsplit("/", 1)[0]
    qids = sorted(_questions_of(got["doc"], {batch}))
    if len(qids) < 2:
        pytest.skip("this candidate packs one question per call")
    agree, disagree = _agree(kind)(qids[0]), _disagree(kind)(qids[0])

    def _answer(row):
        return {k: v for k, v in row.items() if k != "question_id"}

    first = {qids[0]: _answer(agree)}
    second = dict(first)
    for q in qids[1:]:
        first[q] = _answer(_agree(kind)(q))
        second[q] = _answer(_disagree(kind)(q))
    if kind == "G3":
        first = {q: v["bucket"] for q, v in first.items()}
        second = {q: v["bucket"] for q, v in second.items()}
    else:
        first = {q: v["verdicts"] for q, v in first.items()}
        second = {q: v["verdicts"] for q, v in second.items()}

    res, probs = CV.complete_g23(
        got["doc"], {lanes[0]: first, lanes[1]: second}, _ident(got))
    credited, held = set(res["credited"]), {u["question_id"]
                                            for u in res["unresolved"]}
    assert qids[0] in credited, "the agreed question lost its credit"
    assert set(qids[1:]) <= held, "a disagreement was credited"
    # NEITHER OUTCOME TWICE, and every frozen question reached exactly one
    assert not (credited & held), sorted(credited & held)
    assert len(credited) + len(held) == res["questions"]
    assert probs == [], probs[:2]


# ---- Codex SEQ 1473 item 2: the OFFICIAL scorer, on saved evidence --------
def _source(got, kind, completion_sha):
    """The grader run plus approved hashes ONLY: the candidate location and
    hash are derived from the root (Codex SEQ 1476)."""
    return {kind: {"run_dir": got["run"],
                   "root_sha256": got["root_sha"],
                   "completion_sha256": completion_sha}}


def _every_frozen_question_is_unresolved(got, result):
    """A malformed reply must leave EVERY frozen question unresolved.

    Looping over `credited` passed whenever `credited` was empty - including
    when nothing was ever asked - so it proved nothing (Codex SEQ 1477 item 4).
    The frozen population is asserted nonempty, nothing malformed is credited,
    and each frozen question appears in `unresolved` exactly once.
    """
    frozen = [q for row in got["doc"]["batch_rows"]
              for q in row["question_ids"]]
    assert frozen, "the frozen candidate asked nothing, so nothing was tested"
    assert not (result["credited"] or {}), result["credited"]
    unresolved = [u["question_id"] for u in (result["unresolved"] or [])]
    assert sorted(unresolved) == sorted(frozen), (
        len(unresolved), len(frozen))
    assert len(set(unresolved)) == len(unresolved), "a question repeats"


def _completed(got):
    """Persist the whole-run completion for a driven lifecycle."""
    ident = CV.g23_identity(got["root_sha"], got["run"])
    result, problems = CV.complete_g23(got["doc"], got["rulings"], ident)
    assert problems == [], problems[:2]
    _path, sha = CV.persist_g23(got["out"], result)
    return sha, result


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_the_official_entry_derives_its_maps_from_saved_evidence(
        kind, tmp_path, monkeypatch):
    """Real saved segments and attempts, real frozen candidate, real
    completion - loaded by location and hash only."""
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    sha, result = _completed(got)
    assert result["credited"], "the lifecycle credited nothing to derive from"

    # the CANDIDATE's own stored binding
    population = got["doc"]["population"]
    assert population, "the frozen candidate stores no question binding"
    leg = sorted(population)[0].split("|", 1)[0]
    graders, extras = B.official_verdict_maps(leg, _source(got, kind, sha), RUN,
                                              _required_populations(),
                                              _approved_g1())
    derived = graders if kind == "G2" else extras
    assert derived, (kind, list(result["credited"])[:2])
    if kind == "G2":
        # every LIVE meaning field, as booleans - the shape score_arm requires
        for verdict in derived.values():
            assert set(verdict) == set(B.meaning_fields()), verdict
            assert all(isinstance(v, bool) for v in verdict.values())
    else:
        for bucket in derived.values():
            assert bucket in B.extras_buckets(), bucket


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_kind_swap_between_candidate_and_completion_REFUSES(
        kind, tmp_path, monkeypatch):
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    sha, _r = _completed(got)
    other = "G3" if kind == "G2" else "G2"
    with pytest.raises(ValueError) as exc:
        B.official_verdict_maps("P1", _source(got, other, sha), RUN,
                                _required_populations(), _approved_g1())
    assert other in str(exc.value) or kind in str(exc.value)


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_changed_grader_run_REFUSES(kind, tmp_path, monkeypatch):
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    sha, _r = _completed(got)
    with io.open(os.path.join(got["run"], "receipt.json"), "a",
                 encoding="utf-8") as fh:
        fh.write(" ")
    with pytest.raises(ValueError):
        B.official_verdict_maps("P1", _source(got, kind, sha), RUN,
                                _required_populations(), _approved_g1())


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_recomputed_caller_source_cannot_substitute_a_candidate(
        kind, tmp_path, monkeypatch):
    """A mutated candidate with a recomputed hash must still refuse: the hash
    is the APPROVED one, not whatever the file now says."""
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    sha, _r = _completed(got)
    path = os.path.join(got["out"], G.CANDIDATE_NAME)
    doc = G._read(path)
    doc["population"] = {}
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(G._pretty(doc) + "\n")
    src = _source(got, kind, sha)                      # still the approved sha
    with pytest.raises(ValueError) as exc:
        B.official_verdict_maps("P1", src, RUN,
                                _required_populations(), _approved_g1())
    # the ROOT binds the candidate's hash, so a recomputed caller hash cannot
    # help: the root and the file disagree
    assert "not the approved" in str(exc.value), str(exc.value)[:140]


#: A source dict with the right KEYS and unusable contents. The kinds gate
#: compares key sets and refuses BEFORE any source is opened - so if it ever
#: opened one, these proofs would fail on a load error instead, which is part
#: of what they prove. Driving real grader runs here is impossible anyway: the
#: lifecycle must repoint AUD.PROJECTS_ROOT, and the fresh producer
#: populations this gate derives from need the real one.
_UNOPENED = {"run_dir": "/nonexistent", "root_sha256": "0" * 64,
             "completion_sha256": "0" * 64}

#: A G1 lifecycle that is PRESENT but unusable, for the same reason.
_G1_STUB = {"candidate_dir": "/nonexistent", "run_dir": "/nonexistent",
            "pins": {}}


def _required_legs():
    """Every leg the frozen populations actually carry."""
    doc, _prompts, _identity = _frozen()
    return {k.split("|", 1)[0]
            for pop in (doc["g2_pairs"], doc["g3_idxs"])
            for k in pop}


def _required(leg):
    """The kinds this leg's OWN frozen populations oblige, measured."""
    doc, _prompts, _identity = _frozen()
    return {kind for kind, pop in (("G2", doc["g2_pairs"]),
                                   ("G3", doc["g3_idxs"]))
            if any(k.split("|", 1)[0] == leg for k in pop)}


def _scoped_derivation(monkeypatch):
    """The ALREADY-VERIFIED derivation, handed to `score_leg_official` for the
    handle/kind gates ONLY - an explicitly scoped upstream TEST adapter.

    Those populations were routed and scored once, natively, and independently
    recomputed (Codex SEQ 1877/1879); re-deriving them here would reroute the
    same 108 event-legs per test and is forbidden. The adapter replaces ONLY
    the upstream derivation. `_score_leg_bound` - the code under test - runs
    completely unchanged, so each gate below is the owner's own check.

    -> a Counter that records how far past the gates execution actually got.
    """
    doc, _prompts, _identity = _frozen()
    reached = collections.Counter()
    real_maps = B._verdict_maps_from

    def bundle(producer, audit_root, g1):
        reached["derivation"] += 1
        return {"g2": doc["g2_pairs"], "g3": doc["g3_idxs"],
                "arms": {leg: {} for leg in _required_legs()},
                "gold": {}, "meta": {}, "derived": {}, "state": {},
                "completions": {}}

    def maps(*a, **k):
        # THE COUNTED DOWNSTREAM BOUNDARY. Reaching it proves the handle and
        # kind gates both passed; it is a marker, never evidence of a score.
        reached["verdict_maps"] += 1
        raise _DownstreamReached()

    monkeypatch.setattr(B, "_official_derivation", bundle)
    monkeypatch.setattr(B, "_verdict_maps_from", maps)
    assert real_maps is not B._verdict_maps_from
    return reached


class _DownstreamReached(Exception):
    """Marks the boundary past the gates. Not a score and not model meaning."""


def test_a_lawful_handle_and_kind_set_REACHES_the_downstream_boundary(
        tmp_path, monkeypatch):
    """The positive control for the four gates below.

    Without it a refusal proves nothing: every negative would also "pass" if
    the gates refused everything. This is a counted marker, NOT a score.
    """
    reached = _scoped_derivation(monkeypatch)
    leg = sorted(_required_legs())[0]
    full = {k: dict(_UNOPENED) for k in _required(leg)}
    with pytest.raises(_DownstreamReached):
        B.score_leg_official(leg, RUN, full, str(tmp_path / "ok"),
                             _approved_g1())
    assert reached["derivation"] == 1, dict(reached)
    assert reached["verdict_maps"] == 1, dict(reached)


def test_the_official_entry_REFUSES_before_grader_evidence_exists(
        tmp_path, monkeypatch):
    """NO graders is a scoring BYPASS, not an empty verdict map.

    My previous end-to-end test passed `{}` and no G1 and accepted a score;
    that is exactly the hole A7 exists to close (Codex SEQ 1477 item 1).
    """
    reached = _scoped_derivation(monkeypatch)
    leg = sorted(_required_legs())[0]
    assert _required(leg), "this leg obliges no grading, so it proves nothing"
    with pytest.raises(ValueError) as exc:
        B.score_leg_official(leg, RUN, {}, str(tmp_path / "a"), None)
    assert "G1" in str(exc.value) or "grader" in str(exc.value), exc.value
    assert not reached["verdict_maps"], "it ran past the gate it must stop at"


def test_a_missing_required_grader_kind_REFUSES(tmp_path, monkeypatch):
    """One kind short is refused BY NAME, not silently scored without it."""
    reached = _scoped_derivation(monkeypatch)
    leg = sorted(_required_legs())[0]
    need = _required(leg)
    assert len(need) > 1, sorted(need)
    dropped = sorted(need)[-1]
    short = {k: dict(_UNOPENED) for k in need if k != dropped}
    with pytest.raises(ValueError) as exc:
        B.score_leg_official(leg, RUN, short, str(tmp_path / "b"),
                             _approved_g1())
    assert dropped in str(exc.value), str(exc.value)[:160]
    assert not reached["verdict_maps"], "it ran past the gate it must stop at"


def test_an_unrequired_grader_kind_REFUSES(tmp_path, monkeypatch):
    """An EXTRA kind is refused at the same gate.

    Every leg in this run obliges both kinds, so there is no lawful leg with a
    spare kind to hand in; the extra is proved with a kind the populations
    never oblige, and the refusal must NAME it - failing later on a candidate
    that does not exist would not prove this gate at all.
    """
    reached = _scoped_derivation(monkeypatch)
    leg = sorted(_required_legs())[0]
    extra = {k: dict(_UNOPENED) for k in _required(leg)}
    extra["G9"] = dict(_UNOPENED)
    with pytest.raises(ValueError) as exc:
        B.score_leg_official(leg, RUN, extra, str(tmp_path / "c"),
                             _approved_g1())
    assert "G9" in str(exc.value), str(exc.value)[:160]
    assert not reached["verdict_maps"], "it ran past the gate it must stop at"


def test_the_approved_G1_lifecycle_is_REQUIRED(tmp_path, monkeypatch):
    """A complete set of grader kinds still may not be scored without G1."""
    reached = _scoped_derivation(monkeypatch)
    leg = sorted(_required_legs())[0]
    full = {k: dict(_UNOPENED) for k in _required(leg)}
    with pytest.raises(ValueError) as exc:
        B.score_leg_official(leg, RUN, full, str(tmp_path / "d"), None)
    assert "G1" in str(exc.value), str(exc.value)[:160]
    assert not reached["verdict_maps"], "it ran past the gate it must stop at"


#: RETIRED: test_the_derived_route_reaches_score_arm_STRUCTURALLY.
#: It asserted only that the route `populations` derived is the one `score_arm`
#: accepts, and it re-routed all 108 event-legs to do it. That weaker
#: requirement is fully covered by the verified native 1876 run - which scored
#: all three legs through this exact path - and by Codex's independent
#: recomputation of all 25 fields of all three score objects (Codex SEQ
#: 1877/1879). Retired by that ruling, mapped to that saved proof in
#: logs/INVENTORY_TO_PROOF_1879.json, not skipped and not re-created here.


def test_no_builder_api_can_stamp_a_separate_producer():
    """The producer identity is STORED by the freeze, never handed in."""
    import inspect
    for fn in (R.kind_candidate, R.write_kind):
        names = set(inspect.signature(fn).parameters)
        assert "producer" not in names, (fn.__name__, sorted(names))


def test_the_freeze_document_stores_the_validated_producer_identity():
    """`freeze` already validated the run; it must RECORD which one."""
    doc, _prompts, _identity = _frozen()
    assert doc.get("producer_identity") == RUN, sorted(doc)[:8]


#: `refuse` is the ONLY lifecycle evidence read, so these name a location it
#: will never reach: the stub answers, or the real owner refuses the pins.
_LIFECYCLE = {"candidate_dir": "/nonexistent", "run_dir": "/nonexistent",
              "pins": {}}

_G1_DOC = {}


def _g1_document():
    """The REAL G1 candidate document, built once by its own owner.

    Not a hand-made shape: `a7_g1_build.freeze` produces it, `task_kind`
    reports G1 for it, and it carries the producer identity that freeze
    recorded.
    """
    if "doc" not in _G1_DOC:
        # THE APPROVED SAVED DOCUMENT, verified against the hash its own
        # lifecycle pins. Rebuilding it with `G.freeze` re-derived a whole
        # population these task-kind and producer checks never needed
        # (Codex SEQ 1879).
        g1 = _approved_g1()
        path = os.path.join(g1["candidate_dir"], G.CANDIDATE_NAME)
        want = g1["pins"]["candidate_sha256"]
        got = G._sha_file(path)
        assert got == want, (path, got, want)
        doc = G._read(path)
        assert G.task_kind(doc) == "G1", G.task_kind(doc)
        assert doc.get("producer_identity") == RUN, "saved no producer"
        _G1_DOC["doc"] = doc
    return _G1_DOC["doc"]


def _watch(monkeypatch, state=None):
    """Count what `official_resolution` reaches, in order.

    `state=None` leaves the REAL `refuse` in place. Otherwise `refuse` answers
    with the supplied lifecycle state, so the branch AFTER a successful
    lifecycle is what gets exercised. `load_root`/`load_frozen` are counted to
    prove no second ownership path is used, and `inventory` is counted because
    it is the first step of derivation.
    """
    seen = collections.Counter()
    real_refuse = B.refuse

    def refuse(cand_dir, run_dir, pins):
        seen["refuse"] += 1
        if state is None:
            return real_refuse(cand_dir, run_dir, pins)
        return state, []

    monkeypatch.setattr(B, "refuse", refuse)
    for name in ("load_root", "load_frozen"):
        def counted(*a, _n=name, _r=getattr(G, name), **k):
            seen[_n] += 1
            return _r(*a, **k)
        monkeypatch.setattr(G, name, counted)

    def inventory(run):
        seen["inventory"] += 1
        return [], {}, {}, {}, {}, []

    monkeypatch.setattr(G, "inventory", inventory)
    return seen


def test_incomplete_pins_give_the_NAMED_lifecycle_refusal_not_KeyError(
        monkeypatch):
    """The shared owner reports missing pins; the caller must not crash first.

    Reading the root before `refuse` indexed `pins["root_sha256"]` and raised
    KeyError, which is not a lifecycle refusal at all (Codex SEQ 1478).
    """
    seen = _watch(monkeypatch)
    with pytest.raises(ValueError) as exc:
        B.official_resolution("P1", _LIFECYCLE, RUN)
    assert "lifecycle does not hold" in str(exc.value), str(exc.value)[:160]
    assert seen["refuse"] == 1, seen
    assert seen["load_root"] == 0 and seen["load_frozen"] == 0, seen


def test_a_non_G1_candidate_refuses_BY_TASK_KIND_before_derivation(
        tmp_path, monkeypatch):
    """An otherwise valid lifecycle carrying a G2 candidate resolves nothing."""
    _out, _sha, doc = _candidate(tmp_path, "G2")
    assert G.task_kind(doc) == "G2", G.task_kind(doc)
    seen = _watch(monkeypatch, state=({}, doc, {}))
    with pytest.raises(ValueError) as exc:
        B.official_resolution("P1", _LIFECYCLE, RUN)
    assert "G1" in str(exc.value), str(exc.value)[:160]
    assert seen["refuse"] == 1, seen
    assert seen["inventory"] == 0, "derivation ran before the kind was checked"


def test_a_G1_state_with_the_SAME_producer_reaches_derivation(monkeypatch):
    """Exactly one lifecycle read, then derivation - no earlier refusal."""
    seen = _watch(monkeypatch, state=({}, _g1_document(), {}))
    try:
        B.official_resolution("P1", _LIFECYCLE, RUN)
    except Exception as exc:                          # noqa: BLE001 - checked
        assert "not G1" not in str(exc) and "producer" not in str(exc), exc
    assert seen["refuse"] == 1, seen
    assert seen["inventory"] == 1, "derivation was never reached"
    assert seen["load_root"] == 0 and seen["load_frozen"] == 0, seen


def test_a_G1_state_with_a_DIFFERENT_producer_refuses_after_the_lifecycle(
        monkeypatch):
    """The producer check runs on the lifecycle's OWN document, after it holds.

    The test it replaces wrote a G2 candidate and supplied only a root pin, so
    it passed on the pre-validation read rather than on this branch.
    """
    doc = dict(_g1_document())
    doc["producer_identity"] = dict(RUN, run_dir="/another/run")
    seen = _watch(monkeypatch, state=({}, doc, {}))
    with pytest.raises(ValueError) as exc:
        B.official_resolution("P1", _LIFECYCLE, RUN)
    assert "producer" in str(exc.value), str(exc.value)[:160]
    assert seen["refuse"] == 1, "the lifecycle must hold before this check"
    assert seen["inventory"] == 0, "derivation ran before the producer check"


@pytest.mark.parametrize("kind", ["G2", "G3"])
def test_a_tampered_ignored_completion_field_REFUSES(kind, tmp_path,
                                                     monkeypatch):
    """The WHOLE saved completion is compared, not four of its fields.

    `credited_questions` is a field nothing downstream reads, so it is exactly
    what a partial comparison lets through. The caller's completion hash is
    recomputed after the edit, so only the re-derivation can refuse it.
    """
    got = _drive(tmp_path, kind, monkeypatch=monkeypatch)
    sha, result = _completed(got)
    path = os.path.join(got["out"], CV.G23_NAME)
    doc = G._read(path)
    doc["credited_questions"] = (doc.get("credited_questions") or 0) + 1
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(G._pretty(doc) + "\n")
    with pytest.raises(ValueError) as exc:
        B.official_verdict_maps(
            sorted(got["doc"]["population"])[0].split("|", 1)[0],
            _source(got, kind, G._sha_file(path)), RUN,
            _required_populations(), _approved_g1())
    assert "derive" in str(exc.value) or "completion" in str(exc.value), \
        str(exc.value)[:160]


def test_zero_replies_credit_nothing(tmp_path, monkeypatch):
    got = _drive(tmp_path, "G2", monkeypatch=monkeypatch,
                 reply_for=lambda lane, qids: json.dumps([]))
    ident = CV.g23_identity(got["root_sha"], got["run"])
    result, _p = CV.complete_g23(got["doc"], got["rulings"], ident)
    assert not result["credited"], "an empty reply credited something"
    _path, sha = CV.persist_g23(got["out"], result)
    graders, _e = B.official_verdict_maps(
        sorted(got["doc"]["population"])[0].split("|", 1)[0],
        _source(got, "G2", sha), RUN, _required_populations(), _approved_g1())
    assert graders == {}


def test_an_absent_leg_gets_no_verdicts(tmp_path, monkeypatch):
    got = _drive(tmp_path, "G2", monkeypatch=monkeypatch)
    sha, _r = _completed(got)
    graders, _e = B.official_verdict_maps("NO-SUCH-LEG",
                                          _source(got, "G2", sha), RUN,
                                          _required_populations(), _approved_g1())
    assert graders == {}


def test_a_malformed_meaning_verdict_is_never_credited(tmp_path, monkeypatch):
    """A verdict the live scorer would reject must not reach it."""
    def bad(lane, qids):
        return json.dumps([{"question_id": q, "verdicts": {"nonsense": True}}
                           for q in qids])

    got = _drive(tmp_path, "G2", monkeypatch=monkeypatch, reply_for=bad)
    ident = CV.g23_identity(got["root_sha"], got["run"])
    result, _p = CV.complete_g23(got["doc"], got["rulings"], ident)
    _every_frozen_question_is_unresolved(got, result)


def test_a_malformed_extras_bucket_is_never_credited(tmp_path, monkeypatch):
    def bad(lane, qids):
        return json.dumps([{"question_id": q, "bucket": "not-a-bucket"}
                           for q in qids])

    got = _drive(tmp_path, "G3", monkeypatch=monkeypatch, reply_for=bad)
    ident = CV.g23_identity(got["root_sha"], got["run"])
    result, _p = CV.complete_g23(got["doc"], got["rulings"], ident)
    _every_frozen_question_is_unresolved(got, result)


def test_a_changed_producer_run_refuses_at_the_official_entry(tmp_path,
                                                              monkeypatch):
    """The scorer inputs are bound to the producer identity, not the caller."""
    got = _drive(tmp_path, "G2", monkeypatch=monkeypatch)
    sha, _r = _completed(got)
    leg = sorted(got["doc"]["population"])[0].split("|", 1)[0]
    stale = dict(RUN, a6_freeze_sha256="0" * 64)
    with pytest.raises(ValueError) as exc:
        B.score_leg_official(leg, stale, _source(got, "G2", sha),
                             R.AUDIT_ROOT, _G1_STUB)
    # the re-verification now re-pins the captured A6 freeze hash (Codex SEQ
    # 1517), so a stale/forged hash trips the freeze pin directly.
    assert "not the required" in str(exc.value)


def test_the_official_entry_takes_no_caller_population_or_verdicts():
    """The signature itself: nothing about the evidence may be handed in."""
    import inspect
    banned = {"gold_by_ev", "arm_by_event", "meta", "route", "g2", "g3",
              "grader_verdicts", "extras_verdicts", "completions"}
    names = set(inspect.signature(B.score_leg_official).parameters)
    assert not (names & banned), sorted(names & banned)
    maps = set(inspect.signature(B.official_verdict_maps).parameters)
    # `producer` is the identity the candidate must BIND to, not evidence the
    # caller supplies; `sources` names only locations and approved hashes;
    # `required` is the post-G1 population the OFFICIAL consumer derived and
    # the candidate must match, and `g1` is the approved lifecycle HANDLE.
    assert maps == {"leg", "sources", "producer", "required", "g1"}, \
        sorted(maps)
    assert not (maps & banned), sorted(maps & banned)
