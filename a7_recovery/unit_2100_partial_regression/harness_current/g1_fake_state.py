"""A FAITHFUL fake official state: the real schema, including child JSONL.

Nothing here is a model call. The shape is copied from a real completed
Workflow state and a real child transcript, so a mutation of it is a mutation
of the thing the runtime actually writes.
"""
import io, json, os


def complete_test_run(kind, candidate, document, destination, projects_root):
    """Real capture/finalization with fixed TEST answers; no model is called."""
    import collections
    from pathlib import Path
    import a7_g1_build as G
    import a7_g23_build as B
    import a7_g1_complete_v2 as CV
    import audit_worker_access as AUD
    candidate, document, destination = map(Path, (candidate, document, destination))

    def check(problems):
        assert not problems, problems[:5]
    root, root_sha, problems = G.freeze_root(str(candidate), str(destination),
                                             G._sha_file(str(document)))
    check(problems)
    lanes = [row["lane_id"] for row in root["rows"]]
    assert lanes, (kind, root)
    identity, problems = G.publish_run(str(candidate), str(destination),
                                       root_sha, lanes)
    check(problems)
    segment, receipt_sha = identity["segment"], identity["receipt_sha256"]
    packet, problems = G.preflight(str(candidate), str(destination), segment,
                                   root_sha, receipt_sha)
    check(problems)
    receipt = G.load_receipt(str(destination), segment)
    doc = G._read(str(document))
    binding, parser = G.binding_and_parser(kind)
    answers, results = {}, []
    for arg in packet["args"]:
        bound = binding(doc, arg["batch_id"])
        if kind == "G1":
            body = [{"question_id": q["question_id"], "produced_idxs": []}
                    for q in bound["questions"]]
        else:
            qids = [q["question_id"] if isinstance(q, dict) else q
                    for q in bound["question_ids"]]
            if kind == "G2":
                body = [{"question_id": q,
                         "verdicts": dict.fromkeys(B.meaning_fields(), True)}
                        for q in qids]
            else:
                body = [{"question_id": q, "bucket": None} for q in qids]
        text = json.dumps(body)
        _answer, problems = parser(text, bound)
        check(problems)
        result = collections.OrderedDict((k, arg.get(k)) for k in G.RESULT_BINDING)
        result.update(invocation_sha256=receipt["invocation_sha256"], text=text,
                      error=None)
        results.append(result)
        answers[arg["lane_id"]] = text
    _accounting, problems = G.save_results(str(destination), segment, results,
                                          root_sha, receipt_sha)
    check(problems)
    projects_before = AUD.PROJECTS_ROOT
    try:
        state = build(str(destination.parent), str(destination), segment,
                           G, answers=answers, errors={},
                           projects_root=projects_root,
                           run_id="wf_test_" + G._sha(str(destination))[:20])
        check(G.record_official_state(str(destination), segment, state,
                                       root_sha, receipt_sha))
        final, _rulings, problems = G.finalize_segment(
            str(candidate), str(destination), segment, root_sha, receipt_sha)
        check(problems)
        assert final is not None and not final["retry"] and not final["uncalled"]
    finally:
        AUD.PROJECTS_ROOT = projects_before
    ident = CV.g23_identity(root_sha, str(destination))
    _root, cdoc, records, problems = CV.evidence(
        str(candidate), str(destination), root_sha,
        ident["run_digest"], ident["run_files"])
    check(problems)
    assert len(records) == len(lanes)
    if kind == "G1":
        pins = {"root_sha256": root_sha, "run_tree_sha256": ident["run_digest"],
                "run_file_count": ident["run_files"],
                "candidate_sha256": root["candidate_sha256"],
                "prompt_tree_sha256": root["prompt_tree_sha256"],
                "rules_block_sha256": root["rules_block_sha256"],
                "git_head": B._git("rev-parse", "HEAD"),
                "git_tree": B._git("rev-parse", "HEAD^{tree}")}
        valid, problems = B.refuse(str(candidate), str(destination), pins)
        check(problems)
        assert valid is not None
        return {"candidate_dir": str(candidate), "run_dir": str(destination),
                "pins": pins}
    completed, problems = CV.complete_g23(cdoc, CV.relations_from_run(records), ident)
    check(problems)
    _path, digest = CV.persist_g23(str(candidate), completed)
    assert CV.load_g23(str(candidate), digest, root_sha, str(destination)) == completed
    return {"candidate_dir": str(candidate), "run_dir": str(destination),
            "root_sha256": root_sha, "completion_sha256": digest,
            "lanes": len(lanes)}



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

    projects = over.pop("projects_root", os.path.join(tmp_root, "projects"))
    session = os.path.join(projects, "proj", "sess")
    workflows = os.path.join(session, "workflows")
    os.makedirs(workflows, exist_ok=True)
    AUD.PROJECTS_ROOT = projects
    rid = over.pop("run_id", "wf_g1seg%02d" % n)
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


def declared_input_record():
    """-> the ONE input record a served lane's transcript really carries, or
    None when this run serves no approved declaration.

    The live runtime splices an extra input record into almost every worker
    transcript: `audit_worker_access._input` measured 1,406 of 1,408 eligible
    ones carrying it. A fake that carries NONE is therefore not the thing the
    runtime writes, and a package that declares its one lawful input made every
    call built on such a fake unprovable (Codex SEQ 1955).

    Nothing here is authored: the shape comes from the approved declaration,
    and the payload object comes from the artifact THAT declaration names, is
    checked against the sha the declaration recorded for it, and must
    canonicalise to the payload sha the declaration pins.
    """
    import raw_transport as RT
    spec, _sha = RT.declared_lane_input()
    if not isinstance(spec, dict):
        return None
    doc = json.load(io.open(RT.LANE_INPUT_PROFILES, encoding="utf-8"))
    src = (doc.get("sources") or {}).get("declared_payload") or {}
    path = src.get("path")
    if not path or not os.path.isfile(path):
        return None
    if RT._sha_file(path) != src.get("sha256"):
        raise ValueError("the declared payload artifact at %s is not the %s "
                         "the approved declaration names" % (path,
                                                             src.get("sha256")))
    for entry in json.load(io.open(path, encoding="utf-8"))["attachments"]:
        if entry.get("canonical_sha256") == spec.get("payload_sha256"):
            return dict(spec, payload=entry["object"])
    return None


def _transcript(tdir, agent_id, session_id, prompt, answer, declared=None):
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
    if declared:
        recs.insert(declared["record_index"],
                    {"type": declared["record_type"], "uuid": uid(9),
                     "parentUuid": None, "agentId": agent_id,
                     "isSidechain": True, "sessionId": session_id,
                     declared["payload_field"]: declared["payload"]})
        # THE CHAIN IS THE ORDER. A record spliced into the middle becomes the
        # parent of what follows it; leaving the old links made the answer
        # point past the new record and the chain owner refused it.
        for prev, rec in zip(recs, recs[1:]):
            rec["parentUuid"] = prev["uuid"]
    with io.open(os.path.join(tdir, "agent-%s.jsonl" % agent_id), "w",
                 encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
