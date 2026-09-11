# -*- coding: utf-8 -*-
"""CLEARLY LABELLED SYNTHETIC PROOF for the source-only key closure.

NO MODEL IS CALLED HERE AND NOTHING HERE IS AN ANSWER. The blind readings this
closure owes do not exist yet, so a positive route cannot be exercised with a
real one. This module builds a FAITHFUL stand-in for exactly one such reading:

  * the reply text reuses each member's OWN already-proved `settled` object,
    lifted from that event's real initial reply and re-emitted with its exact
    digits intact, wrapped in the hard-review owner's own group envelope. It is
    therefore a real, parseable reading of the real rows - and it is a
    stand-in, not evidence about what a reviewer would actually decide.
  * the official state and its transcript copy the SHAPE of a real completed
    Workflow state, with only the identity fields this call must carry swapped.
    A mutation of this fake is therefore a mutation of the thing the runtime
    really writes.

Every artifact it produces is written under the TEST projects tree the binding
shadows. It can never touch the real store, and the fixture never asks the
owners what they expect: every value below is derived from the published
package and run, which the owners themselves produced.
"""
import collections
import decimal
import io
import json
import os
import shutil

#: the one marker text carried into every synthetic artifact, so a stray copy
#: can never be mistaken for evidence of a real call
MARK = "SYNTHETIC-CLOSURE-FIXTURE-2000"


def dumps_exact(obj, indent=1):
    """JSON with every Decimal written back as its own digits, unquoted.

    `json.dumps` has no exact-decimal mode: `default=str` would quote 3.40 into
    a string and a float would lose the trailing zero. Each Decimal is swapped
    for a unique placeholder, the document is serialized, and the placeholder
    is put back as the raw digits it came from.
    """
    marks = {}

    def walk(o):
        if isinstance(o, decimal.Decimal):
            key = "@@EXACT-%d@@" % len(marks)
            marks[key] = str(o)
            return key
        if isinstance(o, dict):
            return collections.OrderedDict((k, walk(v)) for k, v in o.items())
        if isinstance(o, (list, tuple)):
            return [walk(v) for v in o]
        return o

    text = json.dumps(walk(obj), indent=indent, ensure_ascii=False)
    for key, value in marks.items():
        text = text.replace(json.dumps(key), value)
    return text


def reply_text(CL, task, verdict=True, reason=None):
    """One synthetic blind reading of one closure task, as raw reply bytes."""
    shards, raws = CL._initial()
    items = CL.SK.items()
    sid = items[task["members"][0]]["source_id"]
    parsed = CL.K.RT.parse_reply(raws[sid])
    by_row = {n + 1: row for n, row in enumerate(parsed["rows"])}
    order = {p: n + 1 for n, p in enumerate(
        {t["source_id"]: t for t in CL.SK.tasks()}[sid]["rows"])}
    reason = reason or ("%s: a stand-in reading built from this event's own "
                        "already-proved settlements; it is not a judgment."
                        % MARK)
    if task["kind"] == "item":
        return dumps_exact(by_row[order[task["members"][0]]]["settled"])
    members = [collections.OrderedDict([
        ("member_index", n + 1),
        ("settled", by_row[order[key]]["settled"])])
        for n, key in enumerate(task["members"])]
    return dumps_exact(collections.OrderedDict([
        ("members", members), ("members_are_one_fact", verdict),
        ("reason", reason)]))


def _template(pristine_dir):
    """The SHAPE of a real completed state and its transcript."""
    state = json.loads(io.open(os.path.join(pristine_dir, "state.json"),
                               encoding="utf-8").read())
    lines = [json.loads(l) for l in io.open(
        os.path.join(pristine_dir, "transcript.jsonl"), encoding="utf-8")
        if l.strip()]
    return state, lines


def write_state(CL, run_dir, pkg_dir, label, run_id, pristine_dir,
                projects_root, text=None, **over):
    """Write ONE synthetic official state plus its transcript. -> the path.

    `over` mutates exactly one recorded thing at a time in the negative cases;
    with no override the state is the faithful positive control.
    """
    ctx = CL._ctx()
    task, blind = CL.by_label()[label]
    attempt = over.pop("attempt", 1)
    script = CL.render_launcher(task, blind, attempt)
    # THE PUBLISHED SCRIPT FILE, found by its own bytes rather than by a
    # naming convention this fixture would otherwise be asserting.
    want = CL.K._sha(script)
    sdir = os.path.join(run_dir, "scripts")
    script_path = next(
        (os.path.join(sdir, n) for n in sorted(os.listdir(sdir))
         if CL.K._sha(CL.K._read(os.path.join(sdir, n))) == want), None)
    prompt = CL.blind_prompt(task)
    text = reply_text(CL, task) if text is None else text

    state, lines = _template(pristine_dir)
    session = os.path.join(projects_root, "-home-faisal-EventMarketDB",
                           CL.K.PARENT_SESSION)
    agent_id = over.pop("agentId", "syn%s" % run_id[-8:])
    rows = [r for r in state["workflowProgress"]
            if r.get("type") == "workflow_agent"]
    row = dict(rows[0])
    # THE ROW records the runtime's own row model id; the RESULT object
    # records the alias. They are two different recorded fields.
    row.update({"label": label, "agentId": agent_id,
                "model": CL.K.ROW_MODEL_ID, "agentType": CL.K.AGENT_TYPE,
                "state": "done", "attempt": attempt,
                "promptPreview": prompt[:200], "toolCalls": 0})
    row.pop("lastToolName", None)
    row.update(over.pop("row", {}))
    result = collections.OrderedDict([
        ("task_id", task["task_id"]), ("kind", task["kind"]),
        ("members", list(task["members"])), ("blind", blind),
        ("attempt", attempt), ("model", CL.K.MODEL), ("effort", CL.K.EFFORT),
        ("agentType", CL.K.AGENT_TYPE), ("text", text)])
    result.update(over.pop("result", {}))
    body = dict(state)
    body.update({"runId": run_id, "status": "completed",
                 "scriptPath": script_path, "script": script,
                 "workflowProgress": [r for r in state["workflowProgress"]
                                      if r.get("type") != "workflow_agent"]
                 + [row],
                 # `K.direct_result` reads `result` ITSELF as the returned
                 # object; a hard-review run returns one object per call.
                 "result": result, "totalToolCalls": 0})
    body.update(over.pop("state", {}))

    tdir = os.path.join(session, "subagents", "workflows", run_id)
    os.path.isdir(tdir) or os.makedirs(tdir)
    out = [json.loads(json.dumps(rec)) for rec in lines]
    asst = [r for r in out if r.get("type") == "assistant"]
    # ONE text-bearing record, on the LAST response: the chain owner refuses a
    # non-terminal record that carries text, and the pristine transcript this
    # copies is already a lawful chain.
    for rec in out:
        if rec.get("sessionId"):
            rec["sessionId"] = CL.K.PARENT_SESSION
        if "agentId" in rec:
            rec["agentId"] = agent_id
        # EVERY RESPONSE IS ITS OWN. Copying one transcript into several states
        # repeated the runtime's response ids, and the owner refuses a reused
        # one (measured, attempt e2e2001_f).
        for field in ("uuid", "parentUuid", "requestId"):
            if isinstance(rec.get(field), str):
                rec[field] = "%s-%s" % (run_id, rec[field])
        msg0 = rec.get("message")
        if isinstance(msg0, dict) and isinstance(msg0.get("id"), str):
            msg0["id"] = "%s-%s" % (run_id, msg0["id"])
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            msg["content"] = prompt
        if msg.get("role") == "assistant":
            msg["model"] = CL.K.RUNTIME_MODEL_ID
            rec["effort"] = CL.K.EFFORT
            if rec is asst[-1] and isinstance(msg.get("content"), list):
                msg["content"] = [b for b in msg["content"]
                                  if b.get("type") != "text"] \
                    + [{"type": "text", "text": text}]
    for name, value in over.pop("transcript", {}).items():
        for rec in out:
            rec[name] = value
    io.open(os.path.join(tdir, "agent-%s.jsonl" % agent_id), "w",
            encoding="utf-8").write(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))

    path = os.path.join(session, "workflows", run_id + ".json")
    io.open(path, "w", encoding="utf-8").write(
        json.dumps(body, indent=1, ensure_ascii=False))
    return path


def clear(projects_root, keep):
    """Remove every synthetic state this fixture wrote, keeping the real ones.

    The real preserved copies are NEVER deleted: `keep` names them and the
    fixture only removes run ids it created itself.
    """
    session = os.path.join(projects_root, "-home-faisal-EventMarketDB",
                           "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
    wf = os.path.join(session, "workflows")
    for name in sorted(os.listdir(wf)):
        rid = os.path.splitext(name)[0]
        if rid in keep:
            continue
        os.remove(os.path.join(wf, name))
        tdir = os.path.join(session, "subagents", "workflows", rid)
        if os.path.isdir(tdir):
            shutil.rmtree(tdir)


# ------------------------- the FINAL ADJUDICATION side of the same fixture --
def final_reply_text(CL, task, leads, resolve_open_issues=False):
    """One synthetic FINAL reply for one event, as raw reply bytes.

    It reuses that event's OWN already-proved initial reply verbatim and
    changes exactly one thing: `lead_reconciliation`, which the initial reply
    had to leave empty because it was shown no lead and which the closure reply
    must carry one row per lead for. Nothing else is touched, so this is a real
    parseable final reply over real settlements - and a stand-in, not a
    judgment about what an adjudicator would decide.
    """
    _shards, raws = CL._initial()
    sid = task["source_id"]
    obj = CL.K.RT.parse_reply(raws[sid])
    if resolve_open_issues:
        # THE ONE THING A CLOSURE REPLY IS FOR. Having been shown the blind
        # readings, the adjudicator may close what its first pass could not.
        # This stand-in models that it did; it does NOT model any particular
        # answer, and the gate's refusal while issues remain is exercised as
        # its own case beside this one.
        obj["open_issues"] = []
    obj["lead_reconciliation"] = [collections.OrderedDict([
        ("lead_id", l["lead_id"]), ("agrees", True),
        ("why", "%s: a stand-in reconciliation; no meaning was decided." % MARK)])
        for l in leads]
    return dumps_exact(obj)


def write_final_state(CL, run_dir, pkg_dir, label, run_id, projects_root,
                      by_source, text=None, script_path=None,
                      resolve_open_issues=False, **over):
    """Write ONE synthetic official state for a FINAL adjudication call.

    The template is that event's OWN real collection state, so the door, the
    key role, the result shape and the transcript chain are the real ones; only
    the script bytes, the prompt and the returned text are this phase's.
    """
    K = CL.K
    task = {t["source_id"]: t for t in CL.SK.tasks()}[label]
    attempt = over.pop("attempt", 1)
    # THE SOURCE OWNER'S OWN DOORS, so the fixture renders exactly what the
    # publication rendered. Calling the locked owner directly rendered the
    # HISTORICAL prompt instead and reached the A3 evidence a source-only key
    # may not read (measured, attempt e2e2001_e).
    with CL._prompt_scope(by_source):
        script = CL.SK.render_launcher(task, attempt)
        prompt = CL.SK.prompt(task)
    leads = by_source.get(label, [])
    text = (final_reply_text(CL, task, leads, resolve_open_issues)
            if text is None else text)
    # THE PUBLISHED SCRIPT FILE, named by the run that published it. The
    # caller passes the invocation's own path; there is no naming convention
    # asserted here.
    if script_path is None:
        raise ValueError("the published scriptPath for %s was not supplied"
                         % label)
    if K._sha(K._read(script_path)) != K._sha(script):
        raise ValueError("%s: the published script is not the rendered one"
                         % label)

    # THE REAL STATE OF THIS EVENT'S OWN INITIAL CALL is the shape template
    session = os.path.join(projects_root, "-home-faisal-EventMarketDB",
                           K.PARENT_SESSION)
    src_id = None
    for name in sorted(os.listdir(os.path.join(session, "workflows"))):
        doc = json.loads(io.open(os.path.join(session, "workflows", name),
                                 encoding="utf-8").read())
        rows = [r for r in (doc.get("workflowProgress") or [])
                if r.get("type") == "workflow_agent"]
        if len(rows) == 1 and rows[0].get("label") == label:
            src_id = os.path.splitext(name)[0]
            template, trow = doc, rows[0]
            break
    if src_id is None:
        raise ValueError("no real state template for %s" % label)
    lines = [json.loads(l) for l in io.open(
        os.path.join(session, "subagents", "workflows", src_id,
                     "agent-%s.jsonl" % trow["agentId"]), encoding="utf-8")
        if l.strip()]

    agent_id = over.pop("agentId", "fin%s" % run_id[-8:])
    row = dict(trow)
    row.update({"label": label, "agentId": agent_id, "state": "done",
                "attempt": attempt, "promptPreview": prompt[:200],
                "toolCalls": 0})
    row.pop("lastToolName", None)
    row.update(over.pop("row", {}))
    result = collections.OrderedDict(
        (k, v) for k, v in (CL.K.direct_result(template) or {}).items())
    result["text"] = text
    result["attempt"] = attempt
    result.update(over.pop("result", {}))
    body = dict(template)
    body.update({"runId": run_id, "status": "completed",
                 "scriptPath": script_path, "script": script,
                 "workflowProgress": [r for r in template["workflowProgress"]
                                      if r.get("type") != "workflow_agent"]
                 + [row],
                 "result": result, "totalToolCalls": 0})
    body.update(over.pop("state", {}))

    tdir = os.path.join(session, "subagents", "workflows", run_id)
    os.path.isdir(tdir) or os.makedirs(tdir)
    out = [json.loads(json.dumps(r)) for r in lines]
    asst = [r for r in out if r.get("type") == "assistant"]
    for rec in out:
        if rec.get("sessionId"):
            rec["sessionId"] = K.PARENT_SESSION
        if "agentId" in rec:
            rec["agentId"] = agent_id
        # EVERY RESPONSE IS ITS OWN. Copying one transcript into several states
        # repeated the runtime's response ids, and the owner refuses a reused
        # one (measured, attempt e2e2001_f).
        for field in ("uuid", "parentUuid", "requestId"):
            if isinstance(rec.get(field), str):
                rec[field] = "%s-%s" % (run_id, rec[field])
        msg0 = rec.get("message")
        if isinstance(msg0, dict) and isinstance(msg0.get("id"), str):
            msg0["id"] = "%s-%s" % (run_id, msg0["id"])
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            msg["content"] = prompt
        if msg.get("role") == "assistant" and rec is asst[-1] \
                and isinstance(msg.get("content"), list):
            msg["content"] = [b for b in msg["content"]
                              if b.get("type") != "text"] \
                + [{"type": "text", "text": text}]
    io.open(os.path.join(tdir, "agent-%s.jsonl" % agent_id), "w",
            encoding="utf-8").write(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    path = os.path.join(session, "workflows", run_id + ".json")
    io.open(path, "w", encoding="utf-8").write(
        json.dumps(body, indent=1, ensure_ascii=False))
    return path


def write_signature_state(CL, signer_dir, bound, label, run_id, projects_root,
                          signed=True, **over):
    """Write ONE synthetic official state for the SIGNER call.

    A TEST SIGNATURE, never a real one: it says only that the shapes reproduce,
    and the freeze that records it says so in the same breath. The template is
    again a real completed state, so the door, role, result shape and
    transcript chain are the runtime's own.
    """
    K, F = CL.K, CL.F
    attempt = over.pop("attempt", 1)
    script = F.signer_script(bound, attempt)
    prompt, _s = F._signer_context(bound, attempt)
    text = over.pop("text", None)
    if text is None:
        text = json.dumps(collections.OrderedDict([
            ("signed", bool(signed)),
            ("blocked", [] if signed else
             ["%s: a stand-in refusal, not a real finding" % MARK]),
            ("why", "%s: a TEST signature over reproduced shapes. It "
                    "establishes no source truth." % MARK)]), indent=1)
    want = K._sha(script)
    sdir = os.path.join(signer_dir, "scripts")
    script_path = next(
        (os.path.join(sdir, n) for n in sorted(os.listdir(sdir))
         if K._sha(K._read(os.path.join(sdir, n))) == want), None)

    session = os.path.join(projects_root, "-home-faisal-EventMarketDB",
                           K.PARENT_SESSION)
    names = sorted(os.listdir(os.path.join(session, "workflows")))
    template = trow = src_id = None
    for name in names:
        doc = json.loads(io.open(os.path.join(session, "workflows", name),
                                 encoding="utf-8").read())
        rows = [r for r in (doc.get("workflowProgress") or [])
                if r.get("type") == "workflow_agent"]
        if len(rows) == 1 and doc.get("status") == "completed":
            template, trow, src_id = doc, rows[0], os.path.splitext(name)[0]
            break
    if template is None:
        raise ValueError("no real state template available")
    lines = [json.loads(l) for l in io.open(
        os.path.join(session, "subagents", "workflows", src_id,
                     "agent-%s.jsonl" % trow["agentId"]), encoding="utf-8")
        if l.strip()]

    agent_id = "sig%s" % run_id[-8:]
    row = dict(trow)
    row.update({"label": label, "agentId": agent_id, "state": "done",
                "attempt": attempt, "promptPreview": prompt[:200],
                "toolCalls": 0})
    row.pop("lastToolName", None)
    row.update(over.pop("row", {}))
    # THE SIGNER RETURNS ITS OWN FIELDS, not an event call's, and the owner
    # checks them exactly (measured, attempt e2e2001_i).
    base = K.direct_result(template) or {}
    result = collections.OrderedDict(
        (k, base.get(k)) for k in F.SIGNER_RESULT_FIELDS)
    result["role"] = "signer"
    result["text"] = text
    result["attempt"] = attempt
    result.update(over.pop("result", {}))
    body = dict(template)
    body.update({"runId": run_id, "status": "completed",
                 "scriptPath": script_path, "script": script,
                 "workflowProgress": [r for r in template["workflowProgress"]
                                      if r.get("type") != "workflow_agent"]
                 + [row],
                 "result": result, "totalToolCalls": 0})
    body.update(over.pop("state", {}))

    tdir = os.path.join(session, "subagents", "workflows", run_id)
    os.path.isdir(tdir) or os.makedirs(tdir)
    out = [json.loads(json.dumps(r)) for r in lines]
    asst = [r for r in out if r.get("type") == "assistant"]
    for rec in out:
        if rec.get("sessionId"):
            rec["sessionId"] = K.PARENT_SESSION
        if "agentId" in rec:
            rec["agentId"] = agent_id
        # EVERY RESPONSE IS ITS OWN. Copying one transcript into several states
        # repeated the runtime's response ids, and the owner refuses a reused
        # one (measured, attempt e2e2001_f).
        for field in ("uuid", "parentUuid", "requestId"):
            if isinstance(rec.get(field), str):
                rec[field] = "%s-%s" % (run_id, rec[field])
        msg0 = rec.get("message")
        if isinstance(msg0, dict) and isinstance(msg0.get("id"), str):
            msg0["id"] = "%s-%s" % (run_id, msg0["id"])
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            msg["content"] = prompt
        if msg.get("role") == "assistant" and rec is asst[-1] \
                and isinstance(msg.get("content"), list):
            msg["content"] = [b for b in msg["content"]
                              if b.get("type") != "text"] \
                + [{"type": "text", "text": text}]
    io.open(os.path.join(tdir, "agent-%s.jsonl" % agent_id), "w",
            encoding="utf-8").write(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    path = os.path.join(session, "workflows", run_id + ".json")
    io.open(path, "w", encoding="utf-8").write(
        json.dumps(body, indent=1, ensure_ascii=False))
    return path
