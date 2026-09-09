"""A FAITHFUL fake official state: the real schema, including child JSONL.

Nothing here is a model call. The shape is copied from a real completed
Workflow state and a real child transcript, so a mutation of it is a mutation
of the thing the runtime actually writes.
"""
import io, json, os


def build(tmp_root, run_dir, n, G, lanes=None, errors=None, **over):
    """-> the official state path, with PROJECTS_ROOT redirected under tmp."""
    import audit_worker_access as AUD
    receipt = G.load_receipt(run_dir, n)
    invocation = G._read(receipt["invocation_path"])
    # THE SAVED ARGS AND THE PROMPT ARE TWO DIFFERENT THINGS. The runtime is
    # handed the small identity-only args and saves those; the prompt bytes the
    # agent actually read are RE-DERIVED here from the root, the reservation
    # and the frozen candidate, so a state that echoes the wrong prompt cannot
    # be built out of the very args it is meant to be checked against.
    root = G.load_root(run_dir, receipt["root_sha256"])
    reservation = G._read(G.reservation_path(run_dir, n))
    derived, row_problems = G._rows_for(root["candidate_dir"], root,
                                        reservation["lanes"],
                                        reservation["attempt"])
    assert not row_problems, row_problems
    prompts = over.pop("prompts", None)
    if prompts is None:
        prompts = {r["lane_id"]: r["prompt"] for r in derived}
    order = [r["lane_id"] for r in receipt["rows"]]
    lanes = order if lanes is None else list(lanes)
    errors = errors or {}

    projects = os.path.join(tmp_root, "projects")
    session = os.path.join(projects, "proj", "sess")
    workflows = os.path.join(session, "workflows")
    os.makedirs(workflows, exist_ok=True)
    AUD.PROJECTS_ROOT = projects
    rid = "wf_g1seg%02d" % n
    tdir = os.path.join(session, "subagents", "workflows", rid)
    os.makedirs(tdir, exist_ok=True)

    with io.open(receipt["script_path"], encoding="utf-8") as fh:
        script = fh.read()
    # THE RESULT ROWS ARE WHAT grade_batch.js RETURNS: the published row plus
    # the publication's invocation hash, the text and the error. Building them
    # from anything less makes the fake unable to prove the fields it omits.
    by_lane = {r["lane_id"]: r for r in invocation["args"]}
    session_id = "sess"
    rows, results = [], []
    for i, lane in enumerate(lanes):
        agent_id = "g1a%02d" % i
        # an UNKNOWN lane is itself a mutation, so it must be buildable
        prompt = prompts.get(lane, "unpublished lane")
        answer = (over.get("answers") or {}).get(lane, "[]")
        # A row with no answer text DID NOT succeed, whether or not the caller
        # named an error for it: the runtime records those as errored rows.
        failed = errors.get(lane) or (None if isinstance(answer, str)
                                      else "no text was returned")
        if failed:
            answer = None
        rows.append({
            "type": G.AGENT_ROW_TYPE, "index": i + 1, "label": lane,
            "phaseIndex": 1, "phaseTitle": "G1", "agentId": agent_id,
            "agentType": "lean-probe", "model": "claude-sonnet-5",
            "state": "error" if failed else "done", "attempt": 1,
            "toolCalls": 0, "promptPreview": prompt[:200],
            "startedAt": 1, "lastProgressAt": 2, "tokens": 1})
        published = by_lane.get(lane, {})
        row = {f: published.get(f) for f in G.RESULT_BINDING}
        row["invocation_sha256"] = receipt["invocation_sha256"]
        row["text"] = answer
        row["error"] = failed
        results.append(row)
        if not failed:
            _transcript(tdir, agent_id, session_id, prompt, answer)
    body = {"runId": rid, "status": "completed",
            "scriptPath": receipt["script_path"], "script": script,
            "args": invocation["args"],
            "workflowProgress": [{"type": "workflow_phase", "index": 1,
                                  "title": "G1"}] + rows,
            "result": {"rows": len(order), "calls": len(lanes),
                       "results": results}}
    for key in ("answers",):
        over.pop(key, None)
    body.update(over)
    path = os.path.join(workflows, rid + ".json")
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    return path


def _transcript(tdir, agent_id, session_id, prompt, answer):
    uid = lambda k: "%s-%04d" % (agent_id, k)
    recs = [
        {"type": "user", "uuid": uid(0), "parentUuid": None,
         "agentId": agent_id, "isSidechain": True, "sessionId": session_id,
         "message": {"role": "user", "content": prompt}},
        {"type": "assistant", "uuid": uid(1), "parentUuid": uid(0),
         "agentId": agent_id, "isSidechain": True, "effort": "high",
         "sessionId": session_id, "requestId": "req_%s" % agent_id,
         "message": {"role": "assistant", "id": "msg_%s" % agent_id,
                     "model": "claude-sonnet-5", "stop_reason": "end_turn",
                     "content": [{"type": "text", "text": answer}]}},
    ]
    with io.open(os.path.join(tdir, "agent-%s.jsonl" % agent_id), "w",
                 encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
