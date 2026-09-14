"""Codex SEQ 1431 + 1432 — the Workflow BOUNDARY owner, red first.

The defect being closed is real and was hit live: the transport refuses a script
over its byte cap, and the refusal creates NO run. The published segment is then
stuck forever, because a segment leaves "pending" only through a finalization
and a finalization requires an official state that a refused launch never wrote.

Every fixture here mirrors the exact record shape measured from the live parent
session - including the DICT `toolUseResult` a successful launch writes, which
is what "no run identity" is checked against - so a mutation of a fixture is a
mutation of the thing the runtime actually writes.
"""
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a7_g1_build as G                                          # noqa: E402
import a7_g1_workflow_gate as W                                  # noqa: E402

FROZEN = "/tmp/a7_g1_v14"
APPROVED = "5d5798c7a1c711b5b94c1d325c46b986ec5b93e8997d8f69f92b41e8efd946c2"
USE_ID = "toolu_TEST00000000000000000000"


def _lanes(n, offset=0):
    doc, _sha = G.load_frozen(FROZEN, APPROVED)
    return [r["lane_id"] for r in doc["launchers"]["rows"][offset:offset + n]]


def _projects(tmp_path, monkeypatch):
    """PROJECTS_ROOT redirected into the test's own tree - nothing real is read."""
    import audit_worker_access as AUD
    root = os.path.join(str(tmp_path), "projects")
    os.makedirs(os.path.join(root, "proj", "sess", "workflows"), exist_ok=True)
    monkeypatch.setattr(AUD, "PROJECTS_ROOT", root, raising=False)
    return root


def _frozen_root(tmp_path, name="run"):
    run = str(tmp_path / name)
    root, sha, problems = G.freeze_root(FROZEN, run, APPROVED)
    assert problems == [], problems
    return run, root, sha


def _published(tmp_path, lanes, name="run"):
    """A disposable run with ONE clean published segment."""
    run, _root, sha = _frozen_root(tmp_path, name)
    ident, problems = G.publish_run(FROZEN, run, sha, lanes)
    assert problems == [], problems
    return run, sha, ident["segment"], ident["receipt_sha256"]


def _session(tmp_path, run, n, use_id=USE_ID, name="session.jsonl", **over):
    """A parent session JSONL carrying the exact measured record shape."""
    receipt = G.load_receipt(run, n)
    published = G._read(receipt["invocation_path"])
    use_uuid = over.get("use_uuid", "use-0001")
    script = over.get("script_path", receipt["script_path"])
    payload = {"scriptPath": script,
               "args": over.get("args", json.dumps(published["args"]))}
    payload.update(over.get("extra_input") or {})
    use = {"type": "assistant", "uuid": use_uuid, "parentUuid": "before",
           "sessionId": over.get("use_session", "s"),
           "message": {"role": "assistant", "content": [
               {"type": "tool_use", "id": use_id,
                "name": over.get("tool_name", "Workflow"), "input": payload}]}}
    result = {"type": "user", "uuid": over.get("result_uuid", "res-0001"),
              "parentUuid": over.get("result_parent", use_uuid),
              "sessionId": over.get("result_session", "s"),
              "toolUseResult": over.get(
                  "outcome", "Error: script file exceeds bytes"),
              "message": {"role": "user", "content": [
                  {"type": "tool_result", "tool_use_id": use_id,
                   "is_error": over.get("is_error", True),
                   "content": "<tool_use_error>refused</tool_use_error>"}]}}
    records = [use] + ([] if over.get("drop_result") else [result])
    if over.get("second_use_other_id"):
        other = json.loads(json.dumps(use))
        other["uuid"] = "use-0002"
        other["message"]["content"][0]["id"] = "toolu_ANOTHER0000000000000000"
        records.insert(1, other)
    if over.get("duplicate_result"):
        records.append(dict(result, uuid="res-0002"))
    lines = [json.dumps(r) + "\n" for r in records]
    if over.get("malformed_line"):
        # a BROKEN line that mentions the exact script: it must fail closed
        lines.append('{"scriptPath": "%s", broken\n' % script)
    path = str(tmp_path / name)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    return path


def _close(tmp_path, run, sha, n, rsha, session, use_id=USE_ID, owner=None):
    return W.close_prelaunch_refusal(FROZEN, run, n, sha, rsha,
                                     owner or W.owner_sha256(), session, use_id)


def _listing(run):
    return {os.path.relpath(os.path.join(r, f), run): G._sha_file(
        os.path.join(r, f)) for r, _d, fs in os.walk(run) for f in fs}


# ------------------------------------------------------------- 1. THE RED ----
def test_red_a_refused_segment_is_stuck_before_this_owner_exists(tmp_path,
                                                                 monkeypatch):
    """THE DEFECT, reproduced: published, unlaunchable, unfinalizable, blocking."""
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(2)
    run, sha, n, rsha = _published(tmp_path, lanes)
    root = G.load_root(run, sha)

    assert G._read(G.state_path(run, n))["states"] == []
    assert G._captures_of(run, n) == []
    assert not os.path.isfile(G.accounting_path(run, n))
    assert not os.path.isfile(G.finalization_path(run, n))

    assert G.segment_state(run, n) == "published"
    blocked = G.lifecycle_problems(run, root, _lanes(1, 2), 1)
    assert any("still pending" in p for p in blocked), blocked
    assert any("no official Workflow state" in p
               for p in G.audit_official_state(run, n, sha, rsha))
    final, _rulings, problems = G.finalize_segment(FROZEN, run, n, sha, rsha)
    assert final is None and problems


# ----------------------------------------------------------- 2. THE GREEN ----
def test_green_the_owner_closes_it_and_credits_nothing(tmp_path, monkeypatch):
    """The lawful control: closed, nothing credited, every lane uncalled."""
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(2)
    run, sha, n, rsha = _published(tmp_path, lanes)
    session = _session(tmp_path, run, n)

    before = _listing(run)
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert problems == [], problems
    after = _listing(run)
    for name, digest in before.items():
        assert after[name] == digest, name

    assert final["closure"] == W.CLOSURE_KIND
    assert final["state_audited"] is False and final["credited"] == 0
    assert final["uncalled"] == lanes and final["retry"] == []
    assert final["validity"] == [[l, False] for l in lanes]
    # ZERO calls happened, so the ledger counts zero - while every lane stays
    # visibly refused through validity, problems, uncalled and credited above.
    assert final["ledger"] == {"scheduled": 0, "valid": 0, "invalid": 0,
                               "retry": 0, "uncalled": 2}
    assert final["refusal_sha256"] == G._sha_file(W.refusal_path(run, n))
    assert final["workflow_gate_sha256"] == W.owner_sha256()

    assert G.segment_state(run, n) == "finalized"
    assert G.lane_states(run) == {l: "uncalled" for l in lanes}
    assert G.latest_retry(run) == {}


def test_green_the_evidence_keeps_both_parent_records_whole(tmp_path,
                                                            monkeypatch):
    """SEQ 1432 item 4: the records themselves, not a summary of them."""
    _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    _close(tmp_path, run, sha, n, rsha, session)
    kept = G._read(W.refusal_path(run, n))
    lines = [l for l in io.open(session, encoding="utf-8") if l.strip()]
    assert kept["tool_use_raw_line"] == lines[0]
    assert kept["tool_result_raw_line"] == lines[1]
    assert kept["tool_use_raw_line_sha256"] == G._sha(lines[0])
    assert kept["tool_result_raw_line_sha256"] == G._sha(lines[1])
    assert kept["tool_use_record"] == json.loads(lines[0])
    assert kept["tool_result_record"] == json.loads(lines[1])
    assert kept["error_value"] == "Error: script file exceeds bytes"
    receipt = G.load_receipt(run, n)
    assert kept["script_sha256"] == receipt["script_sha256"]
    assert kept["invocation_sha256"] == receipt["invocation_sha256"]
    assert kept["owner_sha256"] == W.owner_sha256()


def test_green_the_unchanged_publisher_can_republish_those_lanes(tmp_path,
                                                                 monkeypatch):
    """After closure the ORIGINAL publisher takes the same lanes as attempt 1."""
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(2)
    run, sha, n, rsha = _published(tmp_path, lanes)
    _close(tmp_path, run, sha, n, rsha, _session(tmp_path, run, n))
    ident, problems = G.publish_run(FROZEN, run, sha, lanes, 1)
    assert problems == [], problems
    packet, problems = G.preflight(FROZEN, run, ident["segment"], sha,
                                   ident["receipt_sha256"])
    assert problems == [] and [r["lane_id"] for r in packet["args"]] == lanes


def test_green_a_later_valid_segment_supersedes_the_uncalled_state(tmp_path,
                                                                   monkeypatch):
    """`uncalled` is not a tombstone: the existing owner overwrites it."""
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(1)
    run, sha, n, rsha = _published(tmp_path, lanes)
    _close(tmp_path, run, sha, n, rsha, _session(tmp_path, run, n))
    assert G.lane_states(run) == {lanes[0]: "uncalled"}
    ident, _p = G.publish_run(FROZEN, run, sha, lanes, 1)
    m = ident["segment"]
    G._write_new(G.finalization_path(run, m), G._pretty({
        "schema": G.SCHEMA, "segment": m, "attempt": 1,
        "uncalled": [], "retry": [],
        "ledger": {"scheduled": 1, "valid": 1, "invalid": 0, "retry": 0,
                   "uncalled": 0}}) + "\n")
    assert G.lane_states(run) == {lanes[0]: "called"}


# ------------------------------------------------- 3. IT REFUSES, AND EARLY --
@pytest.mark.parametrize("defect", [
    "wrong_root", "wrong_receipt", "owner_drift", "wrong_use_id",
    "wrong_script_path", "wrong_args", "not_workflow", "not_an_error",
    "unlinked_result", "no_result", "second_use_other_id", "duplicate_result",
    "resume_input_shape", "run_identity_in_result", "malformed_parent_line",
    "split_sessions", "state_in_sidecar", "wrong_sidecar_run_id",
    "sidecar_states_not_a_list", "official_state_exists",
    "child_transcript_exists", "malformed_official_state",
    "already_has_capture", "orphan_extra_raw", "orphan_error",
    "orphan_canonical_raw", "extra_sidecar_key", "sidecar_is_a_list",
    "sidecar_is_invalid_json", "sidecar_is_a_string",
    "already_closed", "edited_script"])
def test_it_refuses_and_writes_nothing(defect, tmp_path, monkeypatch):
    """One condition moves, nothing is written. Every branch, one by one."""
    projects = _projects(tmp_path, monkeypatch)
    lanes = _lanes(2)
    run, sha, n, rsha = _published(tmp_path, lanes)
    receipt = G.load_receipt(run, n)
    kw, use_id, owner = {}, USE_ID, W.owner_sha256()

    if defect == "wrong_root":
        sha = "0" * 64
    elif defect == "wrong_receipt":
        rsha = "0" * 64
    elif defect == "owner_drift":
        owner = "0" * 64
    elif defect == "wrong_use_id":
        use_id = "toolu_SOMETHINGELSE0000000000"
    elif defect == "wrong_script_path":
        kw["script_path"] = "/tmp/somewhere/else.js"
    elif defect == "wrong_args":
        kw["args"] = json.dumps([{"lane_id": "not the published rows"}])
    elif defect == "not_workflow":
        kw["tool_name"] = "Bash"
    elif defect == "not_an_error":
        kw["is_error"] = False
    elif defect == "unlinked_result":
        kw["result_parent"] = "somebody-else"
    elif defect == "no_result":
        kw["drop_result"] = True
    elif defect == "second_use_other_id":
        kw["second_use_other_id"] = True
    elif defect == "duplicate_result":
        kw["duplicate_result"] = True
    elif defect == "resume_input_shape":
        kw["extra_input"] = {"resumeFromRunId": "wf_earlier"}
    elif defect == "run_identity_in_result":
        # the EXACT shape a successful launch writes
        kw["outcome"] = {"runId": "wf_x", "taskId": "t1", "status": "completed",
                         "transcriptDir": "/somewhere", "scriptPath": "x",
                         "summary": "s", "taskType": "t", "workflowName": "w"}
    elif defect == "malformed_parent_line":
        kw["malformed_line"] = True
    elif defect == "split_sessions":
        kw["result_session"] = "another-session"

    session = _session(tmp_path, run, n, **kw)

    if defect in ("state_in_sidecar", "wrong_sidecar_run_id",
                  "sidecar_states_not_a_list", "extra_sidecar_key"):
        body = {"state_in_sidecar": {"run_id": receipt["run_id"],
                                     "states": [{"path": "somewhere"}]},
                "wrong_sidecar_run_id": {"run_id": "another_run",
                                         "states": []},
                "sidecar_states_not_a_list": {"run_id": receipt["run_id"],
                                              "states": {}},
                # exactly right on both named fields, plus one nobody published
                "extra_sidecar_key": {"run_id": receipt["run_id"],
                                      "states": [], "unexpected": "accepted"}
                }[defect]
        os.unlink(G.state_path(run, n))
        G._write_new(G.state_path(run, n), G._pretty(body) + "\n")
    elif defect in ("official_state_exists", "child_transcript_exists"):
        wf = os.path.join(projects, "proj", "sess", "workflows")
        with io.open(os.path.join(wf, "wf_x.json"), "w", encoding="utf-8") as fh:
            json.dump({"runId": "wf_x", "scriptPath": receipt["script_path"]}, fh)
        if defect == "child_transcript_exists":
            os.makedirs(os.path.join(projects, "proj", "sess", "subagents",
                                     "workflows", "wf_x"), exist_ok=True)
    elif defect in ("sidecar_is_a_list", "sidecar_is_invalid_json",
                    "sidecar_is_a_string"):
        raw = {"sidecar_is_a_list": "[]",
               "sidecar_is_invalid_json": "{not json",
               "sidecar_is_a_string": '"nope"'}[defect]
        os.unlink(G.state_path(run, n))
        with io.open(G.state_path(run, n), "w", encoding="utf-8") as fh:
            fh.write(raw)
    elif defect == "malformed_official_state":
        wf = os.path.join(projects, "proj", "sess", "workflows")
        with io.open(os.path.join(wf, "wf_broken.json"), "w",
                     encoding="utf-8") as fh:
            fh.write("{not json")
    elif defect == "already_has_capture":
        G.capture_results(run, n, [{"lane_id": lanes[0], "text": "x",
                                    "error": None}])
    elif defect == "orphan_extra_raw":
        import raw_transport as RT
        RT.save_raw("stray", G._ensure(run, G.EXTRA_DIRNAME),
                    G.capture_name(n, 0))
    elif defect == "orphan_canonical_raw":
        import raw_transport as RT
        RT.save_raw("stray", G._ensure(run, G.RAW_DIRNAME),
                    G.raw_stem(receipt["rows"][0]["ordinal"],
                               receipt["attempt"]))
    elif defect == "orphan_error":
        G._write_new(os.path.join(G._ensure(run, G.ERROR_DIRNAME),
                                  G.capture_name(n, 0) + ".error.json"),
                     G._pretty({"capture": G.capture_name(n, 0)}) + "\n")
    elif defect == "already_closed":
        assert _close(tmp_path, run, sha, n, rsha, session)[1] == []
    elif defect == "edited_script":
        with io.open(receipt["script_path"], "a", encoding="utf-8") as fh:
            fh.write("\n")

    seen = _listing(run)
    final, problems = _close(tmp_path, run, sha, n, rsha, session, use_id, owner)
    assert final is None, defect
    assert problems, defect
    if defect != "already_closed":
        assert not os.path.isfile(W.refusal_path(run, n)), defect
        assert not os.path.isfile(G.finalization_path(run, n)), defect
    assert _listing(run) == seen, defect


# --------------------------------------- 4. INTERRUPTION, AND EXACT RESUME --
def _stage(tmp_path, run, sha, n, rsha, session, upto):
    """Stage a partial closure the way an interruption would leave one."""
    evidence, problems = W.inspect_prelaunch_refusal(
        FROZEN, run, n, sha, rsha, W.owner_sha256(), session, USE_ID)
    assert problems == [], problems
    G._write_new(W.refusal_path(run, n), G._pretty(evidence) + "\n")
    if upto == "accounting":
        G.account_segment(run, n, G.load_root(run, sha))


def test_resume_after_the_evidence_write(tmp_path, monkeypatch):
    """Interrupted after evidence: the closure continues, nothing overwritten."""
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(2)
    run, sha, n, rsha = _published(tmp_path, lanes)
    session = _session(tmp_path, run, n)
    _stage(tmp_path, run, sha, n, rsha, session, "evidence")
    staged = G._sha_file(W.refusal_path(run, n))
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert problems == [], problems
    assert G._sha_file(W.refusal_path(run, n)) == staged     # never rewritten
    assert final["uncalled"] == lanes and final["credited"] == 0
    assert G.lane_states(run) == {l: "uncalled" for l in lanes}


def test_resume_after_the_accounting_write(tmp_path, monkeypatch):
    """Interrupted after accounting: verified and continued, not re-rendered."""
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(2)
    run, sha, n, rsha = _published(tmp_path, lanes)
    session = _session(tmp_path, run, n)
    _stage(tmp_path, run, sha, n, rsha, session, "accounting")
    staged = {p: G._sha_file(os.path.join(run, p))
              for p in ("prelaunch_refusal.seg%02d.json" % n,
                        os.path.basename(G.accounting_path(run, n)))}
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert problems == [], problems
    for name, digest in staged.items():
        assert G._sha_file(os.path.join(run, name)) == digest
    assert final["accounting_sha256"] == staged[
        os.path.basename(G.accounting_path(run, n))]
    assert G.segment_state(run, n) == "finalized"


def test_a_resume_still_refuses_if_the_live_facts_moved(tmp_path, monkeypatch):
    """The last look really happens: a state that appears after staging stops it."""
    projects = _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    _stage(tmp_path, run, sha, n, rsha, session, "accounting")
    receipt = G.load_receipt(run, n)
    wf = os.path.join(projects, "proj", "sess", "workflows")
    with io.open(os.path.join(wf, "wf_late.json"), "w", encoding="utf-8") as fh:
        json.dump({"runId": "wf_late", "scriptPath": receipt["script_path"]}, fh)
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert final is None and problems
    assert not os.path.isfile(G.finalization_path(run, n))


@pytest.mark.parametrize("altered", ["evidence", "accounting"])
def test_altered_staged_artifacts_are_refused(altered, tmp_path, monkeypatch):
    """A staged artifact that is not what this run derives fails closed."""
    _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    _stage(tmp_path, run, sha, n, rsha, session, "accounting")
    path = (W.refusal_path(run, n) if altered == "evidence"
            else G.accounting_path(run, n))
    body = G._read(path)
    if altered == "evidence":
        body["script_sha256"] = "0" * 64
    else:
        body["captures"] = ["seg01.pos000"]
    os.unlink(path)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(G._pretty(body) + "\n")
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert final is None and problems
    assert not os.path.isfile(G.finalization_path(run, n))


def test_a_transient_scan_count_does_not_block_a_resume(tmp_path, monkeypatch):
    """The tree keeps growing; that was never part of the evidence's identity."""
    projects = _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    _stage(tmp_path, run, sha, n, rsha, session, "evidence")
    # an UNRELATED workflow state appears between the two writes
    wf = os.path.join(projects, "proj", "sess", "workflows")
    with io.open(os.path.join(wf, "wf_unrelated.json"), "w",
                 encoding="utf-8") as fh:
        json.dump({"runId": "wf_unrelated", "scriptPath": "/tmp/other.js"}, fh)
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert problems == [], problems
    assert final["credited"] == 0


def test_a_completed_closure_still_refuses_a_second_time(tmp_path, monkeypatch):
    _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    assert _close(tmp_path, run, sha, n, rsha, session)[1] == []
    before = _listing(run)
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert final is None and problems
    assert _listing(run) == before


def test_accounting_without_evidence_is_refused(tmp_path, monkeypatch):
    """A half state nobody could have produced lawfully."""
    _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    G.account_segment(run, n, G.load_root(run, sha))
    final, problems = _close(tmp_path, run, sha, n, rsha,
                             _session(tmp_path, run, n))
    assert final is None and problems


ACCOUNTING_FIELDS = ["schema", "segment", "attempt", "receipt_sha256",
                     "captures", "selected", "outcomes", "counts"]


@pytest.mark.parametrize("field", ACCOUNTING_FIELDS)
def test_every_staged_accounting_field_is_verified(field, tmp_path,
                                                   monkeypatch):
    """SEQ 1433 item 3: the WHOLE object, not the four fields I checked."""
    _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    _stage(tmp_path, run, sha, n, rsha, session, "accounting")
    body = G._read(G.accounting_path(run, n))
    assert field in body, field
    body[field] = {"schema": "other/9", "segment": 99, "attempt": 9,
                   "receipt_sha256": "0" * 64, "captures": ["x"],
                   "selected": 99, "outcomes": {"nobody": "served"},
                   "counts": {"served": 99}}[field]
    os.unlink(G.accounting_path(run, n))
    with io.open(G.accounting_path(run, n), "w", encoding="utf-8") as fh:
        fh.write(G._pretty(body) + "\n")
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert final is None, field
    assert problems, field
    assert not os.path.isfile(G.finalization_path(run, n)), field


@pytest.mark.parametrize("field", ACCOUNTING_FIELDS)
def test_a_missing_staged_accounting_field_is_refused(field, tmp_path,
                                                      monkeypatch):
    """A field removed is exactly as disqualifying as a field changed."""
    _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    _stage(tmp_path, run, sha, n, rsha, session, "accounting")
    body = G._read(G.accounting_path(run, n))
    body.pop(field)
    os.unlink(G.accounting_path(run, n))
    with io.open(G.accounting_path(run, n), "w", encoding="utf-8") as fh:
        fh.write(G._pretty(body) + "\n")
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert final is None and problems, field


def test_an_extra_staged_accounting_field_is_refused(tmp_path, monkeypatch):
    _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    _stage(tmp_path, run, sha, n, rsha, session, "accounting")
    body = G._read(G.accounting_path(run, n))
    body["unexpected"] = "accepted"
    os.unlink(G.accounting_path(run, n))
    with io.open(G.accounting_path(run, n), "w", encoding="utf-8") as fh:
        fh.write(G._pretty(body) + "\n")
    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert final is None and problems


@pytest.mark.parametrize("late", ["second_workflow_use", "sidecar_changed"])
def test_a_change_between_the_two_inspections_is_refused(late, tmp_path,
                                                         monkeypatch):
    """SEQ 1434 item 1: the mutation lands in the ONE window that matters.

    Staging the change beforehand only proves the FIRST inspection works -
    deleting the final re-inspection would leave such a test green, which is
    exactly what my previous version did. Wrapping the real accounting writer
    puts the change AFTER the first inspection and BEFORE the last look.
    """
    _projects(tmp_path, monkeypatch)
    run, sha, n, rsha = _published(tmp_path, _lanes(2))
    session = _session(tmp_path, run, n)
    receipt = G.load_receipt(run, n)
    real_account = G.account_segment

    def account_then_mutate(run_dir, seg, root):
        written = real_account(run_dir, seg, root)   # the REAL zero-capture write
        if late == "second_workflow_use":
            extra = json.loads(io.open(session, encoding="utf-8")
                               .readline())          # the same use, another id
            extra["uuid"] = "use-late"
            extra["message"]["content"][0]["id"] = "toolu_LATE00000000000000000000"
            with io.open(session, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(extra) + "\n")
        else:
            os.unlink(G.state_path(run_dir, seg))
            G._write_new(G.state_path(run_dir, seg), G._pretty(
                {"run_id": receipt["run_id"],
                 "states": [{"path": "late"}]}) + "\n")
        return written
    monkeypatch.setattr(G, "account_segment", account_then_mutate)

    final, problems = _close(tmp_path, run, sha, n, rsha, session)
    assert final is None, late
    assert problems, late
    assert not os.path.isfile(G.finalization_path(run, n)), late
    # the accounting really was written first, so the window was real
    assert os.path.isfile(G.accounting_path(run, n)), late


# ------------------------------------------- ADMISSION HONOURS THE LIFECYCLE --
def test_a_pending_segment_blocks_admission(tmp_path, monkeypatch):
    """SEQ 1433 item 1: the existing lifecycle gate runs BEFORE sizing."""
    _projects(tmp_path, monkeypatch)
    run, root, sha = _frozen_root(tmp_path, "pending")
    lanes, size, problems = W.next_admissible(FROZEN, run, sha)
    assert problems == [] and lanes and size          # clean while nothing pends

    G.publish_run(FROZEN, run, sha, lanes)            # now one is pending
    blocked = G.lifecycle_problems(run, root, [r["lane_id"]
                                               for r in root["rows"]], 1)
    assert any("still pending" in p for p in blocked), blocked
    lanes2, size2, problems2 = W.next_admissible(FROZEN, run, sha)
    assert lanes2 == [] and size2 is None
    assert problems2 == blocked, (problems2, blocked)


def test_the_public_admission_cannot_be_asked_for_attempt_two(tmp_path):
    """A retry set is the finalizer's to name; this gate is primary-only."""
    import inspect
    names = list(inspect.signature(W.next_admissible).parameters)
    assert names == ["out_dir", "run_dir", "expect_root_sha"], names
    assert W.PRIMARY_ATTEMPT == 1
    with pytest.raises(TypeError):
        W.next_admissible(FROZEN, "/tmp/whatever", "0" * 64, 2)



def _scratch_owner_with_the_old_ledger(tmp_path):
    """A COPY of the owner carrying the pre-fix ledger.

    SEQ 1435: never edit a reviewed owner in place to mutation-proof a test.
    This writes a scratch module and imports it under its own name, so the
    reviewed file is never touched.
    """
    import importlib.util
    with io.open(os.path.join(_HERE, "a7_g1_workflow_gate.py"),
                 encoding="utf-8") as fh:
        src = fh.read()
    fixed = ('("scheduled", 0), ("valid", 0),\n'
             '            ("invalid", 0), ("retry", 0),')
    before = ('("scheduled", len(lanes)), ("valid", 0),\n'
              '            ("invalid", len(lanes)), ("retry", 0),')
    assert fixed in src, "the ledger block moved; this proof must be updated"
    path = str(tmp_path / "gate_old_ledger.py")
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(fixed, before, 1))
    spec = importlib.util.spec_from_file_location("gate_old_ledger", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _closed_then_served(tmp_path, monkeypatch, owner, count):
    """Close `count` zero-call lanes through `owner`, then serve them for real.

    -> (zero_call_ledger, summed finalized scheduled). The second segment is a
    stand-in for `count` real calls, written through the existing owner's own
    finalization shape.
    """
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(count)
    run, sha, n, rsha = _published(tmp_path, lanes)
    session = _session(tmp_path, run, n)
    final, problems = owner.close_prelaunch_refusal(
        FROZEN, run, n, sha, rsha, owner.owner_sha256(), session, USE_ID)
    assert problems == [], problems

    ident, problems = G.publish_run(FROZEN, run, sha, lanes, 1)
    assert problems == [], problems           # the lanes really are republishable
    m = ident["segment"]
    G._write_new(G.finalization_path(run, m), G._pretty({
        "schema": G.SCHEMA, "segment": m, "attempt": 1, "uncalled": [],
        "retry": [], "ledger": {"scheduled": count, "valid": count,
                                "invalid": 0, "retry": 0, "uncalled": 0}}) + "\n")
    total = sum(G._read(G.finalization_path(run, k))["ledger"]["scheduled"]
                for k in G.segments(run)
                if G.segment_state(run, k) == "finalized")
    return final["ledger"], total


@pytest.mark.parametrize("count", [2, 3])
def test_zero_call_lanes_are_never_billed_and_never_billed_twice(
        count, tmp_path, monkeypatch):
    """SEQ 1435: N zero-call lanes close at scheduled 0; N real calls sum to N."""
    ledger, total = _closed_then_served(tmp_path, monkeypatch, W, count)
    assert ledger == {"scheduled": 0, "valid": 0, "invalid": 0, "retry": 0,
                      "uncalled": count}
    assert total == count, "N real calls must sum to N, never 2N"


def test_the_old_ledger_would_have_billed_twice(tmp_path, monkeypatch):
    """The mutation proof, on a SCRATCH COPY - the reviewed owner is untouched."""
    old = _scratch_owner_with_the_old_ledger(tmp_path)
    reviewed = G._sha_file(os.path.join(_HERE, "a7_g1_workflow_gate.py"))
    ledger, total = _closed_then_served(tmp_path, monkeypatch, old, 2)
    assert ledger["scheduled"] == 2, "the scratch copy did not carry the defect"
    assert total == 4, "the defect is 2N; this control would not have caught it"
    # and the file under review never moved
    assert G._sha_file(os.path.join(_HERE, "a7_g1_workflow_gate.py")) == reviewed


# -------------------------------------------------------- 5. THE LIVE RUN ----
LIVE_RUN = "/tmp/a7_g1_run3"
LIVE_ROOT = "664bb96a11654fc0319ecbb30b399c84bcba99882f72a2fe847fe2dcf4ccbc56"
LIVE_SESSION = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
                "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
LIVE_USE_ID = "toolu_01TX6Jo4diWbizLqvmJLkoTK"          # the refused seg 2
LIVE_SEG1_USE_ID = "toolu_018MpF7RA9uGwzYHwZq1ncFJ"     # the launched seg 1


def _live():
    if not os.path.isfile(os.path.join(LIVE_RUN, "root.json")):
        pytest.skip("the live run is not present")
    return LIVE_RUN


def test_prelaunch_refusal_evidence_is_provable_on_a_FIXTURE_run(tmp_path,
                                                                monkeypatch):
    """MIGRATED (SEQ 1447). The old version of this test bound to the live
    run3 and broke the moment its segment 2 was closed. The RULE is
    state-independent, so it is proved on a fixture run instead."""
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(2)
    run, sha, n, rsha = _published(tmp_path, lanes)
    session = _session(tmp_path, run, n)
    evidence, problems = W.inspect_prelaunch_refusal(
        FROZEN, run, n, sha, rsha, W.owner_sha256(), session, USE_ID)
    assert problems == [], problems
    assert evidence["closure"] == W.CLOSURE_KIND
    assert evidence["tool_use_id"] == USE_ID
    assert evidence["official_states_naming_this_script"] == 0


def test_the_wrong_tool_id_is_refused_on_a_FIXTURE_run(tmp_path, monkeypatch):
    """MIGRATED: the id check fires on its own, without any live state."""
    _projects(tmp_path, monkeypatch)
    lanes = _lanes(2)
    run, sha, n, rsha = _published(tmp_path, lanes)
    session = _session(tmp_path, run, n)
    evidence, problems = W.inspect_prelaunch_refusal(
        FROZEN, run, n, sha, rsha, W.owner_sha256(), session,
        "toolu_WRONG0000000000000000000")
    assert evidence is None
    assert any("not the supplied" in p for p in problems), problems


def test_the_versioned_owner_is_REFUSED_against_the_frozen_live_run():
    """A PASSING test that expects refusal (SEQ 1447 item 7).

    run3 was published under the frozen owner. This versioned owner has
    different bytes, so the gate must refuse to touch that run at all. That
    refusal is the guarantee the new owner cannot be applied retroactively.
    """
    if not os.path.isfile(os.path.join(LIVE_RUN, "root.json")):
        pytest.skip("the live run is not present")
    evidence, problems = W.inspect_prelaunch_refusal(
        FROZEN, LIVE_RUN, 2, LIVE_ROOT, G._sha_file(G.receipt_path(LIVE_RUN, 2)),
        W.owner_sha256(), LIVE_SESSION, LIVE_USE_ID)
    assert evidence is None
    assert any("owner a7_g1_build changed since publication" in p
               for p in problems), problems


# ------------------------------------------------- 6. ADMISSION BY THE BYTE --
def test_the_caller_cannot_choose_the_admission_rows():
    """SEQ 1432 item 1: the trusting entry points are gone for good.

    The signature itself is asserted by
    `test_the_public_admission_cannot_be_asked_for_attempt_two`.
    """
    assert not hasattr(W, "admissible_prefix")   # the old, trusting entry point
    assert not hasattr(W, "script_bytes")


def test_admission_derives_root_order_and_skips_called_lanes(tmp_path,
                                                             monkeypatch):
    """It reads the root and the lifecycle; it is told nothing."""
    _projects(tmp_path, monkeypatch)
    run, root, sha = _frozen_root(tmp_path)
    order = [r["lane_id"] for r in root["rows"]]
    first, size, problems = W.next_admissible(FROZEN, run, sha)
    assert problems == [] and size <= W.SCRIPT_BYTE_LIMIT
    assert first == order[:len(first)], "not the root's own order"

    # close the first group as uncalled, and it is STILL eligible
    ident, _p = G.publish_run(FROZEN, run, sha, first)
    n = ident["segment"]
    _close(tmp_path, run, sha, n, ident["receipt_sha256"],
           _session(tmp_path, run, n))
    again, _s, problems = W.next_admissible(FROZEN, run, sha)
    assert problems == [] and again == first

    # now mark them CALLED, and admission moves past them, in root order
    ident2, _p = G.publish_run(FROZEN, run, sha, first)
    m = ident2["segment"]
    G._write_new(G.finalization_path(run, m), G._pretty({
        "schema": G.SCHEMA, "segment": m, "attempt": 1, "uncalled": [],
        "retry": [], "ledger": {"scheduled": len(first), "valid": len(first),
                                "invalid": 0, "retry": 0, "uncalled": 0}}) + "\n")
    after, _s, problems = W.next_admissible(FROZEN, run, sha)
    assert problems == []
    assert after[0] == order[len(first)], "it did not advance in root order"
    assert not set(after) & set(first), "a called lane was re-admitted"


def test_the_predicted_size_is_the_published_size(tmp_path):
    """The prediction is the same renderer, so it must match to the byte."""
    run, _root, sha = _frozen_root(tmp_path, "sizing")
    lanes, predicted, problems = W.next_admissible(FROZEN, run, sha)
    assert problems == []
    ident, problems = G.publish_run(FROZEN, run, sha, lanes)
    assert problems == []
    actual = os.path.getsize(G.script_path(run, ident["segment"]))
    assert predicted == actual, (predicted, actual)


def test_admission_is_the_largest_prefix_that_fits(tmp_path):
    """Exactly one more row would break it - that is what largest means."""
    run, root, sha = _frozen_root(tmp_path, "largest")
    lanes, size, problems = W.next_admissible(FROZEN, run, sha)
    assert problems == [] and size <= W.SCRIPT_BYTE_LIMIT
    order = [r["lane_id"] for r in root["rows"]]
    over, problems = W._script_bytes(FROZEN, root, order[:len(lanes) + 1], 1)
    assert problems == [] and over > W.SCRIPT_BYTE_LIMIT


def test_admission_is_not_a_fixed_group_size(tmp_path):
    """Different prompts, different groups: the bytes decide, nothing else."""
    run, root, sha = _frozen_root(tmp_path, "vary")
    order = [r["lane_id"] for r in root["rows"]]
    groups, i = [], 0
    while i < len(order):
        prefix, size, problems = W._largest_prefix(FROZEN, root, order[i:], 1)
        assert problems == [] and size <= W.SCRIPT_BYTE_LIMIT
        groups.append(len(prefix))
        i += len(prefix)
    assert sum(groups) == len(order)
    assert len(set(groups)) > 1, "every group the same size hides the byte rule"


def test_admission_refuses_a_row_that_cannot_fit_alone(tmp_path, monkeypatch):
    """One row over the cap is a STOP, never a smaller batch."""
    run, root, sha = _frozen_root(tmp_path, "toobig")
    one, _p = W._script_bytes(FROZEN, root,
                              [root["rows"][0]["lane_id"]], 1)
    monkeypatch.setattr(W, "SCRIPT_BYTE_LIMIT", one - 1)
    lanes, size, problems = W.next_admissible(FROZEN, run, sha)
    assert lanes == [] and problems and size == one


def test_admission_accepts_an_exact_fit(tmp_path, monkeypatch):
    """At exactly the limit it fits; one byte lower it does not."""
    run, root, sha = _frozen_root(tmp_path, "exact")
    order = [r["lane_id"] for r in root["rows"]]
    two, _p = W._script_bytes(FROZEN, root, order[:2], 1)
    monkeypatch.setattr(W, "SCRIPT_BYTE_LIMIT", two)
    lanes, size, problems = W.next_admissible(FROZEN, run, sha)
    assert problems == [] and len(lanes) == 2 and size == two
    monkeypatch.setattr(W, "SCRIPT_BYTE_LIMIT", two - 1)
    lanes, _s, problems = W.next_admissible(FROZEN, run, sha)
    assert problems == [] and len(lanes) == 1


def test_admission_refuses_an_unpinned_root(tmp_path):
    """The root arrives as a HASH, not as an object a caller can shape."""
    run, _root, _sha = _frozen_root(tmp_path, "unpinned")
    lanes, _size, problems = W.next_admissible(FROZEN, run, "0" * 64)
    assert lanes == [] and problems


def test_the_limit_is_the_transports_proven_number():
    """A protocol constant, recorded once, not a tunable threshold."""
    assert W.SCRIPT_BYTE_LIMIT == 524288
