"""The signer handoff verifier must refuse every way the binding can break.

`verify_signer_handoff.py` decides whether the already-paid signer answer is still
bound to the workflow that produced it. A decision-bearing rule with no control is what
drifts, and this one had only ever been run by hand.

Each control corrupts a COPY of the pinned inventory and requires a refusal.
"""
import io
import os
import shutil
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
import verify_signer_handoff as V                              # noqa: E402


def _copy(tmp_path):
    dest = str(tmp_path / "SIGNER_HANDOFF.tsv")
    shutil.copy(os.path.join(_R, "products", "SIGNER_HANDOFF.tsv"), dest)
    return dest


def _lines(p):
    return [l.rstrip("\n") for l in io.open(p, encoding="utf-8") if l.strip()]


def _write(p, lines):
    io.open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def test_the_live_handoff_verifies():
    assert V.failures() == []


def test_it_REFUSES_a_missing_role(tmp_path):
    p = _copy(tmp_path)
    lines = [l for l in _lines(p) if not l.startswith("agent_transcript\t")]
    _write(p, lines)
    assert any("does not pin agent_transcript" in x for x in V.failures(p, _R))


def test_it_REFUSES_an_altered_digest(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    for i, l in enumerate(lines):
        if l.startswith("signer_raw\t"):
            f = l.split("\t")
            f[3] = f[3][:-1] + ("0" if f[3][-1] != "0" else "1")
            lines[i] = "\t".join(f)
    _write(p, lines)
    assert any("do not hash to the pinned digest" in x for x in V.failures(p, _R))


def test_it_REFUSES_an_altered_byte_count(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    for i, l in enumerate(lines):
        if l.startswith("signer_reply\t"):
            f = l.split("\t")
            f[2] = str(int(f[2]) + 1)
            lines[i] = "\t".join(f)
    _write(p, lines)
    assert any("pinned" in x for x in V.failures(p, _R))


def test_it_REFUSES_a_missing_artefact(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    for i, l in enumerate(lines):
        if l.startswith("workflow_state\t"):
            f = l.split("\t")
            f[1] = "/nowhere/does-not-exist.json"
            lines[i] = "\t".join(f)
    _write(p, lines)
    assert any("missing at" in x for x in V.failures(p, _R))


def test_it_REFUSES_a_malformed_header(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    lines[0] = lines[0].replace("role", "roleX", 1)
    _write(p, lines)
    assert any("malformed" in x or "header" in x for x in V.failures(p, _R))


def test_the_terminal_text_equality_is_actually_checked():
    """The relationship that matters: the kept answer IS the terminal message.
    Proved by pointing signer_raw at different bytes and requiring a refusal."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="signer_ctl_")
    try:
        p = os.path.join(tmp, "SIGNER_HANDOFF.tsv")
        shutil.copy(os.path.join(_R, "products", "SIGNER_HANDOFF.tsv"), p)
        other = os.path.join(tmp, "not_the_answer.bin")
        io.open(other, "wb").write(b"this is not what the signer said")
        import hashlib
        raw = io.open(other, "rb").read()
        lines = _lines(p)
        for i, l in enumerate(lines):
            if l.startswith("signer_raw\t"):
                lines[i] = "\t".join(["signer_raw", other, str(len(raw)),
                                      hashlib.sha256(raw).hexdigest()])
        _write(p, lines)
        assert any("not byte-identical to raw.bin" in x for x in V.failures(p, _R))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# SEQ 1558 item 4: prompt, agent id, model and tool-call total must be BOUND.
# These controls corrupt the ARTEFACTS rather than the inventory, and re-pin the
# TSV so the corruption is not caught by the digest check instead of the binding
# it is meant to test. A control that trips an earlier rule proves nothing about
# the rule it names.
# ---------------------------------------------------------------------------
import hashlib
import json


def _rebuild(tmp_path, role, mutate):
    """Copy every pinned artefact into tmp, mutate ONE, and re-pin honestly."""
    pins = V.pinned()
    out = []
    tsv = str(tmp_path / "SIGNER_HANDOFF.tsv")
    for r, entry in pins.items():
        src = entry["path"] if os.path.isabs(entry["path"]) else \
            os.path.join(_R, entry["path"])
        raw = io.open(src, "rb").read()
        if r == role:
            raw = mutate(raw)
        dst = str(tmp_path / os.path.basename(entry["path"]))
        io.open(dst, "wb").write(raw)
        out.append("%s\t%s\t%d\t%s"
                   % (r, dst, len(raw), hashlib.sha256(raw).hexdigest()))
    _write(tsv, ["\t".join(V.COLUMNS)] + out)
    return tsv


def _agent_edit(fn):
    def mutate(raw):
        wf = json.loads(raw.decode("utf-8"))
        for e in wf["workflowProgress"]:
            if isinstance(e, dict) and e.get("agentId"):
                fn(e, wf)
                break
        return json.dumps(wf).encode("utf-8")
    return mutate


def test_the_rebuilt_copy_still_verifies(tmp_path):
    """The rebuild itself must be lawful, or every control below is vacuous."""
    p = _rebuild(tmp_path, None, lambda raw: raw)
    assert V.failures(p, _R) == []


def test_it_REFUSES_a_tool_call_total_that_contradicts_the_transcript(tmp_path):
    p = _rebuild(tmp_path, "workflow_state",
                 _agent_edit(lambda e, wf: wf.__setitem__("totalToolCalls", 1)))
    assert any("reports 1 tool calls" in x for x in V.failures(p, _R))


def test_it_REFUSES_more_than_one_agent_record(tmp_path):
    def mutate(raw):
        wf = json.loads(raw.decode("utf-8"))
        extra = [e for e in wf["workflowProgress"]
                 if isinstance(e, dict) and e.get("agentId")]
        wf["workflowProgress"].append(dict(extra[0]))
        return json.dumps(wf).encode("utf-8")
    p = _rebuild(tmp_path, "workflow_state", mutate)
    assert any("2 agent records" in x for x in V.failures(p, _R))


# ---------------------------------------------------------------------------
# Codex SEQ 1559 item 4: a self-consistent, re-pinned forgery must be refused.
# Every control below re-pins the altered bytes honestly (see _rebuild), so the
# digest check is never what refuses; only the binding under test can.
# ---------------------------------------------------------------------------
def _transcript_edit(fn):
    def mutate(raw):
        rows = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
        fn(rows)
        return ("\n".join(json.dumps(r) for r in rows) + "\n").encode("utf-8")
    return mutate


def test_it_REFUSES_codex_full_forgery_re_pinned(tmp_path):
    """wf_WRONG run id, last prompt byte changed, every agent id changed, every
    session id nulled, every parent uuid broken, both efforts low - then re-pinned."""
    def wf_mut(raw):
        wf = json.loads(raw.decode()); wf["runId"] = "wf_WRONG"
        for e in wf["workflowProgress"]:
            if isinstance(e, dict) and e.get("agentId"): e["agentId"] = "f" * 17
        wf["script"] = wf["script"][:-1] + "X"
        return json.dumps(wf).encode()
    def tr_mut(rows):
        for r in rows:
            r["agentId"] = "f" * 17; r["sessionId"] = None; r["parentUuid"] = "broken"
            if r.get("type") == "assistant": r["effort"] = "low"
        c = rows[0]["message"]["content"]
        if isinstance(c, str): rows[0]["message"]["content"] = c[:-1] + "X"
    pins = V.pinned(); out = []; tsv = str(tmp_path / "SIGNER_HANDOFF.tsv")
    for r, e in pins.items():
        src = e["path"] if os.path.isabs(e["path"]) else os.path.join(_R, e["path"])
        raw = io.open(src, "rb").read()
        if r == "workflow_state": raw = wf_mut(raw)
        if r == "agent_transcript": raw = _transcript_edit(tr_mut)(raw)
        dst = str(tmp_path / os.path.basename(e["path"])); io.open(dst, "wb").write(raw)
        out.append("%s\t%s\t%d\t%s" % (r, dst, len(raw), hashlib.sha256(raw).hexdigest()))
    _write(tsv, ["\t".join(V.COLUMNS)] + out)
    bad = V.failures(tsv, _R)
    for needle in ("run id", "agentId", "sessionId", "parentUuid", "effort"):
        assert any(needle in x for x in bad), (needle, bad)


def test_it_REFUSES_a_wrong_run_id(tmp_path):
    p = _rebuild(tmp_path, "workflow_state", lambda raw: json.dumps(
        dict(json.loads(raw.decode()), runId="wf_WRONG")).encode())
    assert any("run id" in x for x in V.failures(p, _R))


def test_it_REFUSES_a_prompt_that_differs_by_one_byte_from_the_full_script_literal(tmp_path):
    """The preview-prefix test passed this; only full equality refuses it."""
    def mut(rows):
        c = rows[0]["message"]["content"]
        rows[0]["message"]["content"] = (c[:-1] + ("X" if c[-1] != "X" else "Y")) \
            if isinstance(c, str) else c
    p = _rebuild(tmp_path, "agent_transcript", _transcript_edit(mut))
    assert any("full PROMPT" in x for x in V.failures(p, _R))


def test_it_REFUSES_a_broken_uuid_chain(tmp_path):
    def mut(rows): rows[2]["parentUuid"] = rows[0]["uuid"]
    p = _rebuild(tmp_path, "agent_transcript", _transcript_edit(mut))
    assert any("parentUuid" in x for x in V.failures(p, _R))


def test_it_REFUSES_a_nulled_session_id(tmp_path):
    def mut(rows): rows[1]["sessionId"] = None
    p = _rebuild(tmp_path, "agent_transcript", _transcript_edit(mut))
    assert any("sessionId" in x for x in V.failures(p, _R))


def test_it_REFUSES_an_effort_that_is_not_the_reported_one(tmp_path):
    def mut(rows):
        for r in rows:
            if r.get("type") == "assistant": r["effort"] = "low"
    p = _rebuild(tmp_path, "agent_transcript", _transcript_edit(mut))
    assert any("effort" in x for x in V.failures(p, _R))


def test_it_REFUSES_a_model_that_disagrees_with_the_report(tmp_path):
    p = _rebuild(tmp_path, "agent_meta", lambda raw: json.dumps(
        dict(json.loads(raw.decode()), model="claude-opus-5")).encode())
    assert any("agent meta" in x for x in V.failures(p, _R))


def test_it_REFUSES_an_agent_id_the_report_did_not_name(tmp_path):
    p = _rebuild(tmp_path, "workflow_state",
                 _agent_edit(lambda e, wf: e.__setitem__("agentId", "0" * 17)))
    assert any("agent id" in x for x in V.failures(p, _R))


def test_it_REFUSES_a_workflow_result_that_is_not_the_raw_answer(tmp_path):
    p = _rebuild(tmp_path, "workflow_state", lambda raw: json.dumps(
        dict(json.loads(raw.decode()), result="{}")).encode())
    assert any("workflow result" in x for x in V.failures(p, _R))


def test_it_REFUSES_an_answer_with_an_extra_key(tmp_path):
    def mut(raw):
        d = json.loads(raw.decode()); d["extra"] = 1
        return json.dumps(d).encode()
    p = _rebuild(tmp_path, "signer_reply", mut)
    assert any("expected exactly signed, blocked, why" in x for x in V.failures(p, _R))


def test_it_REFUSES_an_acceptance_that_does_not_pin_the_report_bytes(tmp_path):
    p = _rebuild(tmp_path, "producer_report", lambda raw: raw + b"\n")
    assert any("IDENTITY does not pin" in x for x in V.failures(p, _R))
