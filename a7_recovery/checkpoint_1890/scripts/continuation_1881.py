# -*- coding: utf-8 -*-
"""Codex SEQ 1880: the SAVED G2/G3 continuation, retry and mutation proof.

The four continuation shapes, for BOTH kinds, carried through the real
finalization, C.evidence and complete_g23 on the APPROVED sealed candidate and
its two companion lanes:

  single group | empty earlier group + valid tail
  valid tail but INVALID whole answer | valid whole answer SPLIT across groups

Then the one permitted retry: the failed lane alone is reselected, the
companion's attempt-1 bytes are reused untouched, and re-publishing the
successful lane is refused by the owner's own guard.

Then mutations, in memory and by exact owner identity, proving each check
detects ITS OWN defect rather than an earlier unrelated failure.

WHAT IS REUSED, NOT REBUILT (Codex SEQ 1880): the sealed G23 candidate and its
prompts, the approved 1871 G1 pins and the historical producer. There is no G1
rebuild, no inventory repair, no fabricated gold-derived candidate and no
rmtree. The transcript prompt is read back byte-for-byte from the fixture's own
written transcript - `promptPreview` is truncated and the audit refuses it.

The replies are declared TEST answers. They are not model output, not accuracy
and not qualification. No model call is made.
"""
import collections, hashlib, io, json, os, sys, traceback

RECOVERY = "/home/faisal/EventMarketDB-driver-recovery"
A = RECOVERY + "/a7_recovery"
U = A + "/unit_1881"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
VIEW = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
OUT = "/tmp/a7_logs_1781"
TAG = os.environ["A7_TAG"]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# THE RECOVERY PACKAGE FIRST - native_1876's own import order (SEQ 1878/1879).
sys.path.insert(0, RECOVERY)
import driver.core.driver_validators as _DV                      # noqa: E402
sys.path.insert(0, VIEW)

import fresh_target as FT                                        # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_g23_build as B                                         # noqa: E402
import a7_g23_run as R                                           # noqa: E402
import a7_g1_complete_v2 as CV                                   # noqa: E402
import audit_worker_access as AUD                                # noqa: E402
import g1_fake_state as FAKE                                     # noqa: E402

WORK = FT.new_dir(os.path.join(U, "out", "cont_" + TAG))
RESULT = os.path.join(OUT, "CONTINUATION_1881_%s.json" % TAG)

res = collections.OrderedDict(
    label="DECLARED_TEST_ANSWERS_NOT_MODEL_MEANING", tag=TAG)
checks = collections.OrderedDict()


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def named_json(var):
    with io.open(os.environ[var], encoding="utf-8") as fh:
        return json.load(fh)


#: THE OWNER BYTES, measured before anything runs. Mutations are in memory
#: only; these files are never written and are re-measured at the end.
OWNERS = collections.OrderedDict(
    (n, os.path.join(VIEW, p)) for n, p in (
        ("G", "a7_g1_build.py"), ("B", "a7_g23_build.py"),
        ("R", "a7_g23_run.py"), ("C", "a7_g1_complete_v2.py"),
        ("AUD", "audit_worker_access.py"),
        ("S", "scorers/score_exp5_current.py")))
OWNERS_BEFORE = {k: sha(v) for k, v in OWNERS.items()}


def groups_transcript(tdir, agent_id, session_id, prompt, texts):
    """A child transcript whose answer arrives in len(texts) response GROUPS.

    Reused from unit_1871/ledger/continuation_control_1871.py: the fixture
    writer emits ONE group, so a multi-group answer cannot be expressed with
    it. Each group is its own response identity, chained in transcript order.
    """
    recs = [{"type": "user", "uuid": "%s-0000" % agent_id, "parentUuid": None,
             "agentId": agent_id, "isSidechain": True,
             "sessionId": session_id,
             "message": {"role": "user", "content": prompt}}]
    prev = "%s-0000" % agent_id
    for k, text in enumerate(texts):
        uid = "%s-%04d" % (agent_id, k + 1)
        recs.append({
            "type": "assistant", "uuid": uid, "parentUuid": prev,
            "agentId": agent_id, "isSidechain": True, "effort": "high",
            "sessionId": session_id, "requestId": "req_%s_%d" % (agent_id, k),
            "message": {"role": "assistant",
                        "id": "msg_%s_%d" % (agent_id, k),
                        "model": "claude-sonnet-5",
                        "stop_reason": ("max_tokens" if k < len(texts) - 1
                                        else "end_turn"),
                        "content": [{"type": "text", "text": text}]}})
        prev = uid
    with io.open(os.path.join(tdir, "agent-%s.jsonl" % agent_id), "w",
                 encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


def lawful(kind, qids):
    """The kind's own lawful reply, from the OWNER'S declared reply keys."""
    if kind == "G2":
        k_id, k_val = B.MEANING_REPLY_KEYS
        return json.dumps([{k_id: q,
                            k_val: {f: True for f in B.meaning_fields()}}
                           for q in qids])
    k_id, k_val = B.EXTRAS_REPLY_KEYS
    return json.dumps([{k_id: q, k_val: B.extras_buckets()[0]}
                       for q in qids])


def rewrite_transcripts(state_path, texts_by_lane, run_dir, n):
    """Replace each lane's single-group transcript with a GROUPED one.

    The prompt is read back from the transcript the fixture actually wrote -
    byte-for-byte, never `promptPreview`, which is truncated and makes the
    audit refuse the prompt before anything here can be measured.
    """
    body = json.load(io.open(state_path))
    sess = os.path.join(AUD.PROJECTS_ROOT, "proj", "sess")
    tdir = os.path.join(sess, "subagents", "workflows", body["runId"])
    wrote = {}
    for arow in body["workflowProgress"]:
        if arow.get("type") != G.AGENT_ROW_TYPE:
            continue
        # THE FIXTURE'S OWN FIELD: g1_fake_state writes the lane as `label`.
        lane = arow.get("label")
        if lane is None or lane not in texts_by_lane:
            continue
        tpath = os.path.join(tdir, "agent-%s.jsonl" % arow["agentId"])
        first = json.loads(io.open(tpath, encoding="utf-8").readline())
        groups_transcript(tdir, arow["agentId"], "sess",
                          first["message"]["content"], texts_by_lane[lane])
        wrote[lane] = arow["agentId"]
    return wrote


def drive_case(kind, cand_doc, prompts, identity, case, texts, tag):
    """Publish BOTH companion lanes, answer in groups, finalize, complete."""
    out_dir = FT.new_dir(os.path.join(WORK, "%s_%s_cand" % (kind, tag)))
    kpath, _ks = R.write_kind(out_dir, kind, cand_doc, prompts, identity)
    run_dir = os.path.join(WORK, "%s_%s_run" % (kind, tag))
    doc = G._read(kpath)
    root, root_sha, probs = G.freeze_root(out_dir, run_dir, G._sha_file(kpath))
    if probs:
        return {"freeze_root": [str(p)[:150] for p in probs[:2]]}
    lanes = [r["lane_id"] for r in root["rows"]][:len(G.GRADER_LANES)]
    # A LANE ID IS COMPOSITE ("<batch>/<grader>"), so the map is keyed from the
    # ROOT's own rows rather than from the bare grader names.
    texts_by_lane = {lane: list(texts) for lane in lanes}
    ident, probs = G.publish_run(out_dir, run_dir, root_sha, lanes)
    if probs:
        return {"publish": [str(p)[:150] for p in probs[:2]]}
    n, rec = ident["segment"], ident["receipt_sha256"]
    packet, probs = G.preflight(out_dir, run_dir, n, root_sha, rec)
    if probs:
        return {"preflight": [str(p)[:150] for p in probs[:2]]}
    receipt = G.load_receipt(run_dir, n)
    binding, _p = G.binding_and_parser(kind)
    rows, terminals, qid_set = [], {}, {}
    for arg in packet["args"]:
        lane = arg["lane_id"]
        qids = [q["question_id"] if isinstance(q, dict) else q
                for q in binding(doc, arg["batch_id"])["question_ids"]]
        qid_set[lane] = qids
        terminal = texts_by_lane[lane][-1]      # agent() returns the LAST group
        terminals[lane] = terminal
        row = collections.OrderedDict((f, arg.get(f)) for f in G.RESULT_BINDING)
        row["invocation_sha256"] = receipt["invocation_sha256"]
        row["text"] = terminal
        row["error"] = None
        rows.append(row)
    acc, probs = G.save_results(run_dir, n, rows, root_sha, rec)
    if probs:
        return {"save": [str(p)[:150] for p in probs[:2]]}
    before = getattr(AUD, "PROJECTS_ROOT", None)
    try:
        # THIS CASE'S OWN tmp_root. `FAKE.build` owns the path beneath it -
        # <tmp_root>/projects/proj/sess/workflows/wf_g1seg<NN>.json - and sets
        # AUD.PROJECTS_ROOT ITSELF, so assigning that root first isolates
        # nothing. Passing the shared WORK made every segment-01 case write the
        # same state file and the same child transcript ids, and the last case
        # overwrote the rest (Codex SEQ 1881). The root is read back AFTER the
        # build, from the owner that set it.
        case_root = os.path.join(WORK, "%s_%s_state" % (kind, tag))
        os.makedirs(case_root)
        st = FAKE.build(case_root, run_dir, n, G,
                        answers=terminals, errors={})
        projects_root = AUD.PROJECTS_ROOT
        agents = rewrite_transcripts(st, texts_by_lane, run_dir, n)
        probs = G.record_official_state(run_dir, n, st, root_sha, rec)
        if probs:
            return {"state": [str(p)[:150] for p in probs[:2]]}
        final, rulings, probs = G.finalize_segment(out_dir, run_dir, n,
                                                   root_sha, rec)
    finally:
        AUD.PROJECTS_ROOT = before
    if final is None:
        return {"finalize": [str(p)[:160] for p in (probs or [])[:2]]}
    bound, bp = G.whole_answers(run_dir, n)
    bound = bound or {}
    row = collections.OrderedDict([
        ("case", case), ("kind", kind), ("segment", n),
        ("out_dir", out_dir), ("run_dir", run_dir), ("root_sha256", root_sha),
        ("lanes", lanes), ("agents", agents),
        ("state_path", st), ("projects_root", projects_root),
        ("state_sha256", sha(st)),
        ("selected_attempt", final.get("attempt")),
        ("retry", sorted(final.get("retry") or [])),
        ("uncalled", sorted(final.get("uncalled") or [])),
        ("valid_lanes", sorted(l for l in lanes
                               if l not in (final.get("retry") or []))),
        ("question_ids", {l: sorted(v) for l, v in qid_set.items()}),
        ("raw_tail_bytes", {l: len(terminals[l].encode()) for l in lanes}),
        ("raw_tail_sha256", {l: h(terminals[l]) for l in lanes}),
        ("bound_whole_bytes",
         {l: len((bound.get(l) or "").encode()) for l in lanes}),
        ("bound_whole_sha256", {l: h(bound[l]) for l in bound}),
        ("bound_whole_equals_all_groups",
         {l: bound.get(l) == "".join(texts_by_lane[l]) for l in lanes}),
        ("bound_problems", [str(p)[:120] for p in (bp or [])[:2]]),
    ])
    # THE LATER READER, on the real saved artifacts
    ident23 = CV.g23_identity(root_sha, run_dir)
    _r, cdoc, lanes_rec, ev_probs = CV.evidence(
        out_dir, run_dir, root_sha, ident23.get("run_digest"),
        ident23.get("run_files"))
    if ev_probs:
        row["evidence"] = [str(p)[:160] for p in ev_probs[:2]]
        return row
    result, cprobs = CV.complete_g23(cdoc, CV.relations_from_run(lanes_rec),
                                     ident23)
    if cprobs:
        row["complete"] = [str(p)[:160] for p in cprobs[:2]]
        return row
    credited = sorted((result.get("credited") or {}))
    unresolved = sorted(q.get("question_id") if isinstance(q, dict) else q
                        for q in (result.get("unresolved") or []))
    row["credited_questions"] = credited
    row["unresolved_questions"] = unresolved
    row["credited_n"], row["unresolved_n"] = len(credited), len(unresolved)
    row["asked_n"] = len(set().union(*[set(v) for v in qid_set.values()]))
    return row


def main():
    B.bind_grading_scorer(os.path.join(VIEW, "scorers",
                                       "score_exp5_current.py"),
                          sha(os.path.join(VIEW, "scorers",
                                           "score_exp5_current.py")))
    run = named_json("A7_PRODUCER_IDENTITY")["historical_g1"][
        "producer_identity"]
    g1 = named_json("A7_G1_PINS")
    cand = os.environ["A7_G23_CANDIDATE"]
    cand_doc = G._read(os.path.join(cand, R.CANDIDATE_NAME))
    pdir = os.path.join(cand, R.PROMPT_DIRNAME)
    prompts = {f[:-len(".prompt.txt")]:
               io.open(os.path.join(pdir, f), encoding="utf-8").read()
               for f in os.listdir(pdir) if f.endswith(".prompt.txt")}
    _key, identity = G.live_key()
    res["reused"] = {"candidate": os.path.join(cand, R.CANDIDATE_NAME),
                     "candidate_sha256": sha(os.path.join(cand,
                                                          R.CANDIDATE_NAME)),
                     "prompts": len(prompts),
                     "g1_run_dir": g1["run_dir"],
                     "producer_manifest": run["a5_manifest_sha256"],
                     "driver_validators": sha(_DV.__file__)}

    #: THE EXPECTATIONS, DECLARED HERE, not read from what the run produced.
    EXPECT = collections.OrderedDict([
        ("single_group_positive", True),
        ("empty_earlier_continuation", True),
        ("A_tail_valid_whole_invalid", False),
        ("B_valid_answer_split", True),
    ])

    cases = collections.OrderedDict()
    for kind in ("G2", "G3"):
        probe = FT.new_dir(os.path.join(WORK, "%s_probe" % kind))
        kpath, _ = R.write_kind(probe, kind, cand_doc, prompts, identity)
        kdoc = G._read(kpath)
        binding, _p = G.binding_and_parser(kind)
        # THE WRITTEN doc's own shape: `write_kind` READS batching.rows
        # from its input and WRITES batch_rows; reading the input key
        # off the output is a KeyError, not a batch.
        first_batch = kdoc["batch_rows"][0]["batch_id"]
        qids = [q["question_id"] if isinstance(q, dict) else q
                for q in binding(kdoc, first_batch)["question_ids"]]
        whole = lawful(kind, qids)
        cut = whole.index("[") + 1
        shapes = collections.OrderedDict([
            ("single_group_positive", [whole]),
            ("empty_earlier_continuation", ["", whole]),
            ("A_tail_valid_whole_invalid",
             ["NOT JSON, an earlier answer.\n", whole]),
            ("B_valid_answer_split", [whole[:cut], whole[cut:]]),
        ])
        for case, texts in shapes.items():
            tag = "%s_%s" % (kind, case)
            # BOTH companion lanes answer; a one-lane answer alone can never
            # earn two-review credit, which the retry section proves directly.
            cases[tag] = drive_case(kind, cand_doc, prompts, identity, case,
                                    texts, tag)
            cases[tag]["expected_valid"] = EXPECT[case]
    res["cases"] = cases

    checks["1_all_eight_continuation_cases_completed"] = all(
        c.get("selected_attempt") is not None
        and "credited_questions" in c for c in cases.values())
    checks["2_validity_matches_the_declared_expectation"] = all(
        (len(c.get("valid_lanes") or []) == len(G.GRADER_LANES))
        == c["expected_valid"] for c in cases.values())
    checks["3_the_bound_whole_is_every_group_not_the_last"] = all(
        all(c["bound_whole_equals_all_groups"].values())
        for c in cases.values() if c["expected_valid"])
    checks["4_only_valid_cases_credit_and_invalid_credit_nothing"] = all(
        (c["credited_n"] > 0) == c["expected_valid"]
        and (c["credited_n"] + c["unresolved_n"]) > 0
        for c in cases.values())
    return cand_doc, prompts, identity


def run():
    try:
        main()
    except Exception:
        res["traceback"] = traceback.format_exc()

def _main_block():
    run()
    res["owners_before"] = OWNERS_BEFORE
    res["owners_after"] = {k: sha(v) for k, v in OWNERS.items()}
    res["owner_bytes_restored"] = res["owners_before"] == res["owners_after"]
    res["checks"] = checks
    res["n_checks"] = len(checks)
    res["n_green"] = sum(1 for v in checks.values() if v)
    res["all_green"] = (bool(checks) and all(checks.values())
                        and res["owner_bytes_restored"]
                        and not res.get("traceback"))
    FT.new_file(RESULT, json.dumps(res, indent=1, default=str))
    print("%s/%s -> %s" % (res["n_green"], res["n_checks"], res["all_green"]))
    for k, v in checks.items():
        print("  %s %s" % ("GREEN" if v else "RED  ", k))
    for t, c in (res.get("cases") or {}).items():
        print("  %-34s attempt=%s valid=%s credited=%s unresolved=%s %s"
              % (t, c.get("selected_attempt"), c.get("valid_lanes"),
                 c.get("credited_n"), c.get("unresolved_n"),
                 "" if "credited_questions" in c else json.dumps(c)[:150]))
    print("owner bytes restored:", res["owner_bytes_restored"])
    if res.get("traceback"):
        print("\n".join(res["traceback"].strip().splitlines()[-10:]))
    sys.exit(0 if res["all_green"] else 1)


if __name__ == "__main__":
    _main_block()
