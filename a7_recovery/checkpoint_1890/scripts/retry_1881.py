# -*- coding: utf-8 -*-
"""Codex SEQ 1881 items 3 and 4: the ONE permitted retry, and the mutations.

RETRY. One lane answers with a valid tail but an INVALID whole answer; its
companion answers lawfully. Finalization must name only the failed lane a
retry. Then:
  * attempt 2 for the FAILED lane is accepted;
  * attempt 2 for the SUCCESSFUL lane is REFUSED by the owner's own guard;
  * the companion's attempt-1 raw bytes are still there, byte-for-byte.

MUTATIONS, in memory and by exact owner identity - no file is written, and
every owner hash is re-measured at the end:
  * whole-answer selection: `_chain` hands back the LAST group as the whole
    answer. The split-answer case must flip to INVALID while the single-group
    case stays valid, so the check is shown to detect ITS OWN defect and not
    an earlier unrelated failure.
  * retry/repeat: `latest_retry` names every lane. Re-publishing the already
    SUCCESSFUL lane must then be accepted, which is exactly the defect the
    unmutated guard refuses.

Declared TEST answers. No model call, no second lifecycle, scorer or runner:
the drive helpers are imported from continuation_1881.
"""
import collections, hashlib, io, json, os, sys, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import continuation_1881 as CONT                                 # noqa: E402

G, B, R, CV = CONT.G, CONT.B, CONT.R, CONT.CV
AUD, FAKE, FT = CONT.AUD, CONT.FAKE, CONT.FT
OUT = CONT.OUT
TAG = CONT.TAG
WORK = CONT.WORK
sha, h = CONT.sha, CONT.h

RESULT = os.path.join(OUT, "RETRY_MUTATIONS_1881_%s.json" % TAG)
res = collections.OrderedDict(
    label="DECLARED_TEST_ANSWERS_NOT_MODEL_MEANING", tag=TAG)
checks = collections.OrderedDict()
OWNERS_BEFORE = dict(CONT.OWNERS_BEFORE)


def identity_of(fn, module):
    """The EXACT owner this mutation replaces: file, hash and qualified name."""
    return collections.OrderedDict([
        ("module", module.__name__), ("file", module.__file__),
        ("file_sha256", sha(module.__file__)),
        ("qualname", getattr(fn, "__qualname__", str(fn)))])


def raw_files(run_dir):
    """Every captured raw file with its bytes' hash, for a byte-for-byte diff."""
    d = os.path.join(run_dir, G.RAW_DIRNAME)
    if not os.path.isdir(d):
        return {}
    return {f: sha(os.path.join(d, f)) for f in sorted(os.listdir(d))}


def build(kind, cand_doc, prompts, identity, tag):
    """A fresh candidate and frozen root for one retry scenario."""
    out_dir = FT.new_dir(os.path.join(WORK, "%s_%s_cand" % (kind, tag)))
    kpath, _ = R.write_kind(out_dir, kind, cand_doc, prompts, identity)
    run_dir = os.path.join(WORK, "%s_%s_run" % (kind, tag))
    root, root_sha, probs = G.freeze_root(out_dir, run_dir, G._sha_file(kpath))
    assert not probs, probs[:2]
    return out_dir, run_dir, root, root_sha, G._read(kpath)


def attempt(out_dir, run_dir, root_sha, doc, kind, lanes, texts_by_lane,
            number, projects):
    """Publish `lanes` at `number`, answer in groups, finalize. -> row."""
    ident, probs = G.publish_run(out_dir, run_dir, root_sha, lanes, number)
    if probs:
        return {"published": False,
                "refusal": [str(p)[:160] for p in probs[:2]]}
    n, rec = ident["segment"], ident["receipt_sha256"]
    packet, probs = G.preflight(out_dir, run_dir, n, root_sha, rec)
    assert not probs, probs[:2]
    receipt = G.load_receipt(run_dir, n)
    binding, _p = G.binding_and_parser(kind)
    rows, terminals = [], {}
    for arg in packet["args"]:
        lane = arg["lane_id"]
        terminals[lane] = texts_by_lane[lane][-1]
        row = collections.OrderedDict((f, arg.get(f)) for f in G.RESULT_BINDING)
        row["invocation_sha256"] = receipt["invocation_sha256"]
        row["text"] = terminals[lane]
        row["error"] = None
        rows.append(row)
    acc, probs = G.save_results(run_dir, n, rows, root_sha, rec)
    assert not probs, probs[:2]
    before = getattr(AUD, "PROJECTS_ROOT", None)
    try:
        # THIS SCENARIO'S OWN tmp_root (Codex SEQ 1881). Passing the shared
        # WORK made every segment-01 case write the same wf_g1seg01.json.
        # Attempts 1 and 2 differ by segment, so one root per scenario is
        # enough and stays distinct from every other scenario.
        os.makedirs(projects, exist_ok=True)
        st = FAKE.build(projects, run_dir, n, G,
                        answers=terminals, errors={})
        CONT.rewrite_transcripts(st, texts_by_lane, run_dir, n)
        probs = G.record_official_state(run_dir, n, st, root_sha, rec)
        assert not probs, probs[:2]
        final, _rulings, probs = G.finalize_segment(out_dir, run_dir, n,
                                                    root_sha, rec)
    finally:
        AUD.PROJECTS_ROOT = before
    if final is None:
        return {"published": True,
                "finalize": [str(p)[:160] for p in (probs or [])[:2]]}
    bound, _bp = G.whole_answers(run_dir, n)
    return {"published": True, "segment": n, "attempt": final.get("attempt"),
            "retry": sorted(final.get("retry") or []),
            "valid_lanes": sorted(l for l in lanes
                                  if l not in (final.get("retry") or [])),
            "state_path": st,
            "bound_whole_sha256": {l: h(v) for l, v in (bound or {}).items()}}


def later_reader(out_dir, run_dir, root_sha):
    """THE ACTUAL CONSUMER: C.evidence -> relations_from_run -> complete_g23.

    A finalized segment's own `attempt` field says what was published; it does
    NOT say which attempt the later reader selects or credits (Codex SEQ 1881).
    -> the complete per-lane attempt map and the exact credited/unresolved ids.
    """
    ident = CV.g23_identity(root_sha, run_dir)
    _r, cdoc, lanes_rec, probs = CV.evidence(
        out_dir, run_dir, root_sha, ident.get("run_digest"),
        ident.get("run_files"))
    if probs:
        return {"evidence": [str(x)[:160] for x in probs[:2]]}
    relations = CV.relations_from_run(lanes_rec)
    result, cprobs = CV.complete_g23(cdoc, relations, ident)
    if cprobs:
        return {"complete": [str(x)[:160] for x in cprobs[:2]]}
    credited = sorted(result.get("credited") or {})
    unresolved = sorted(q.get("question_id") if isinstance(q, dict) else q
                        for q in (result.get("unresolved") or []))
    return collections.OrderedDict([
        ("selected_by_lane",
         {l: rec.get("selected") for l, rec in sorted(lanes_rec.items())}),
        ("attempts_seen_by_lane",
         {l: sorted((rec.get("attempts") or {}))
          for l, rec in sorted(lanes_rec.items())}),
        ("lanes_with_a_relation", sorted(relations)),
        ("credited_questions", credited),
        ("unresolved_questions_n", len(unresolved)),
        ("credited_n", len(credited)),
    ])


def retry_scenario(kind, cand_doc, prompts, identity, tag, mutate_retry=False):
    """attempt 1 (one lane invalid whole) -> the one permitted retry."""
    out_dir, run_dir, root, root_sha, doc = build(kind, cand_doc, prompts,
                                                  identity, tag)
    lanes = [r["lane_id"] for r in root["rows"]][:len(G.GRADER_LANES)]
    failing, good = lanes[0], lanes[1]
    binding, _p = G.binding_and_parser(kind)
    qids = [q["question_id"] if isinstance(q, dict) else q
            for q in binding(doc, doc["batch_rows"][0]["batch_id"])
            ["question_ids"]]
    whole = CONT.lawful(kind, qids)
    projects = os.path.join(WORK, "%s_%s_projects" % (kind, tag))
    first = attempt(out_dir, run_dir, root_sha, doc, kind, lanes,
                    {failing: ["NOT JSON, an earlier answer.\n", whole],
                     good: [whole]}, 1, projects)
    row = collections.OrderedDict([("kind", kind), ("attempt1", first),
                                   ("failing_lane", failing),
                                   ("good_lane", good)])
    if not first.get("published") or "attempt" not in first:
        return row
    row["companion_raw_before"] = raw_files(run_dir)
    # RE-PUBLISHING THE SUCCESSFUL LANE must be refused by the owner's guard.
    repeat = G.publish_run(out_dir, run_dir, root_sha, [good], 2)
    row["successful_lane_republish"] = {
        "published": not repeat[1],
        "refusal": [str(p)[:160] for p in (repeat[1] or [])[:2]]}
    if not repeat[1]:
        row["mutation_allowed_the_repeat"] = True
        return row
    # THE ONE PERMITTED RETRY, for the failed lane only.
    # THE LATER READER, BEFORE the retry: the failed lane must have no
    # selected attempt at all and its questions must stay unresolved.
    row["reader_before_retry"] = later_reader(out_dir, run_dir, root_sha)
    second = attempt(out_dir, run_dir, root_sha, doc, kind, [failing],
                     {failing: [whole]}, 2, projects)
    row["attempt2"] = second
    # THE LATER READER, AFTER the retry: the failed lane now selects 2, the
    # companion still selects 1, and their served questions are credited.
    row["reader_after_retry"] = later_reader(out_dir, run_dir, root_sha)
    row["served_question_ids"] = sorted(qids)
    row["companion_raw_after"] = raw_files(run_dir)
    kept = {k: v for k, v in row["companion_raw_before"].items()}
    row["companion_bytes_unchanged"] = all(
        row["companion_raw_after"].get(k) == v for k, v in kept.items())
    row["new_raw_files"] = sorted(set(row["companion_raw_after"])
                                  - set(kept))
    return row


def main():
    # THE CURRENT GRADING SCORER, bound exactly as the continuation payload
    # binds it. Rendering a kind needs it, and this module runs its own drives
    # rather than continuation_1881's main().
    _sc = os.path.join(CONT.VIEW, "scorers", "score_exp5_current.py")
    B.bind_grading_scorer(_sc, sha(_sc))
    run = CONT.named_json("A7_PRODUCER_IDENTITY")["historical_g1"][
        "producer_identity"]
    cand = os.environ["A7_G23_CANDIDATE"]
    cand_doc = G._read(os.path.join(cand, R.CANDIDATE_NAME))
    pdir = os.path.join(cand, R.PROMPT_DIRNAME)
    prompts = {f[:-len(".prompt.txt")]:
               io.open(os.path.join(pdir, f), encoding="utf-8").read()
               for f in os.listdir(pdir) if f.endswith(".prompt.txt")}
    _key, identity = G.live_key()
    res["producer_manifest"] = run["a5_manifest_sha256"]

    # ---- 3. THE RETRY, both kinds ------------------------------------------
    retries = collections.OrderedDict()
    for kind in ("G2", "G3"):
        retries[kind] = retry_scenario(kind, cand_doc, prompts, identity,
                                       "retry")
    res["retry"] = retries
    checks["1_only_the_failed_lane_is_named_a_retry"] = all(
        r["attempt1"]["retry"] == [r["failing_lane"]]
        and r["attempt1"]["valid_lanes"] == [r["good_lane"]]
        for r in retries.values())
    checks["2_republishing_the_successful_lane_is_REFUSED"] = all(
        not r["successful_lane_republish"]["published"]
        and any(r["good_lane"] in m
                for m in r["successful_lane_republish"]["refusal"])
        for r in retries.values())
    checks["3_the_one_permitted_retry_selects_only_the_failed_lane"] = all(
        r.get("attempt2", {}).get("attempt") == 2
        and r["attempt2"].get("valid_lanes") == [r["failing_lane"]]
        for r in retries.values())
    checks["4_the_companion_attempt1_bytes_are_reused_untouched"] = all(
        r.get("companion_bytes_unchanged") for r in retries.values())
    # THE READER'S OWN VERDICT, not the segment's attempt field.
    checks["5_before_the_retry_the_failed_lane_selects_nothing"] = all(
        r["reader_before_retry"]["selected_by_lane"].get(r["failing_lane"])
        is None
        and r["reader_before_retry"]["selected_by_lane"].get(r["good_lane"])
        == 1
        and r["reader_before_retry"]["credited_n"] == 0
        for r in retries.values())
    checks["6_after_the_retry_the_reader_selects_2_and_1_and_credits_them"] = (
        all(r["reader_after_retry"]["selected_by_lane"].get(r["failing_lane"])
            == 2
            and r["reader_after_retry"]["selected_by_lane"].get(r["good_lane"])
            == 1
            and (r["reader_after_retry"]["credited_questions"]
                 == r["served_question_ids"])
            for r in retries.values()))

    # ---- 4. THE MUTATIONS --------------------------------------------------
    mutations = collections.OrderedDict()

    # M1: the WHOLE answer becomes the LAST group only.
    real_chain = AUD._chain
    mutations["whole_answer_selection"] = collections.OrderedDict([
        ("replaces", identity_of(real_chain, AUD)),
        ("defect", "_chain returns the last group where the whole answer "
                   "belongs, which is the SEQ 1216 shape")])

    def last_group_only(recs, asst):
        problems, final, _complete = real_chain(recs, asst)
        return problems, final, final

    split_case, single_case = {}, {}
    try:
        AUD._chain = last_group_only
        for kind in ("G2", "G3"):
            probe = FT.new_dir(os.path.join(WORK, "%s_m1_probe" % kind))
            kpath, _ = R.write_kind(probe, kind, cand_doc, prompts, identity)
            kdoc = G._read(kpath)
            binding, _p = G.binding_and_parser(kind)
            qids = [q["question_id"] if isinstance(q, dict) else q
                    for q in binding(kdoc, kdoc["batch_rows"][0]["batch_id"])
                    ["question_ids"]]
            whole = CONT.lawful(kind, qids)
            cut = whole.index("[") + 1
            split_case[kind] = CONT.drive_case(
                kind, cand_doc, prompts, identity, "B_valid_answer_split",
                [whole[:cut], whole[cut:]], "m1_split_%s" % kind)
            single_case[kind] = CONT.drive_case(
                kind, cand_doc, prompts, identity, "single_group_positive",
                [whole], "m1_single_%s" % kind)
    finally:
        AUD._chain = real_chain
    mutations["whole_answer_selection"]["split_valid_lanes_under_mutation"] = {
        k: v.get("valid_lanes") for k, v in split_case.items()}
    mutations["whole_answer_selection"]["single_valid_lanes_under_mutation"] = {
        k: v.get("valid_lanes") for k, v in single_case.items()}
    mutations["whole_answer_selection"]["restored"] = AUD._chain is real_chain
    checks["5_the_split_whole_answer_check_detects_its_own_defect"] = all(
        not split_case[k].get("valid_lanes") for k in split_case) and all(
        len(single_case[k].get("valid_lanes") or []) == len(G.GRADER_LANES)
        for k in single_case)

    # M2: latest_retry names EVERY lane, so a successful lane could repeat.
    real_latest = G.latest_retry
    mutations["retry_repeat_guard"] = collections.OrderedDict([
        ("replaces", identity_of(real_latest, G)),
        ("defect", "latest_retry names every lane, so the guard that refuses "
                   "re-publishing a successful lane cannot fire")])
    m2 = {}
    probe = FT.new_dir(os.path.join(WORK, "m2_lane_probe"))
    kpath, _ = R.write_kind(probe, "G2", cand_doc, prompts, identity)
    _r, _rs, proot, _psha, _pd = build("G2", cand_doc, prompts, identity,
                                       "m2_lanes")
    _ALL_LANES = [r["lane_id"] for r in proot["rows"]][:len(G.GRADER_LANES)]
    try:
        G.latest_retry = lambda run_dir: list(_ALL_LANES)
        for kind in ("G2",):
            m2[kind] = retry_scenario(kind, cand_doc, prompts, identity,
                                      "m2_repeat")
    finally:
        G.latest_retry = real_latest
    mutations["retry_repeat_guard"]["republish_allowed_under_mutation"] = {
        k: v.get("successful_lane_republish", {}).get("published")
        for k, v in m2.items()}
    mutations["retry_repeat_guard"]["restored"] = G.latest_retry is real_latest
    checks["6_the_repeat_guard_detects_its_own_defect"] = all(
        v.get("successful_lane_republish", {}).get("published") is True
        for v in m2.values())
    # M3: THE SELECTION ITSELF. `select_attempt` takes the HIGHEST attempt
    # whose reply the parser accepted; the defect is taking the FIRST attempt
    # whether or not it was accepted. That must break the mixed retry - whose
    # first attempt is the invalid one - while a lane with a single valid
    # attempt is unaffected, which is the genuine positive beside it.
    real_select = CV.select_attempt
    mutations["attempt_selection"] = collections.OrderedDict([
        ("replaces", identity_of(real_select, CV)),
        ("defect", "select_attempt returns the FIRST attempt even when its "
                   "reply was refused, instead of the highest accepted one")])

    def first_attempt_even_if_invalid(attempts):
        for n in sorted(attempts):
            return (n, attempts[n][0])
        return None

    m3 = {}
    try:
        CV.select_attempt = first_attempt_even_if_invalid
        for kind in ("G2", "G3"):
            m3[kind] = retry_scenario(kind, cand_doc, prompts, identity,
                                      "m3_select")
    finally:
        CV.select_attempt = real_select
    mutations["attempt_selection"]["mixed_retry_under_mutation"] = {
        k: v.get("reader_after_retry", {}).get("selected_by_lane")
        for k, v in m3.items()}
    mutations["attempt_selection"]["credited_under_mutation"] = {
        k: v.get("reader_after_retry", {}).get("credited_n")
        for k, v in m3.items()}
    mutations["attempt_selection"]["single_valid_attempt_positive"] = {
        k: v.get("reader_before_retry", {}).get("selected_by_lane", {}).get(
            v.get("good_lane")) for k, v in m3.items()}
    mutations["attempt_selection"]["restored"] = (
        CV.select_attempt is real_select)
    # THE MIXED RETRY BREAKS: the failed lane selects its INVALID first attempt
    # instead of the valid second, so the reader no longer credits its served
    # questions. The companion, whose only attempt is valid, still selects 1.
    checks["7_the_selection_mutation_breaks_the_mixed_retry_only"] = all(
        m3[k].get("reader_after_retry", {}).get("selected_by_lane", {}).get(
            m3[k]["failing_lane"]) == 1
        and m3[k].get("reader_after_retry", {}).get("credited_n") == 0
        and m3[k].get("reader_before_retry", {}).get(
            "selected_by_lane", {}).get(m3[k]["good_lane"]) == 1
        for k in m3)
    res["mutations"] = mutations


try:
    main()
except Exception:
    res["traceback"] = traceback.format_exc()

res["owners_before"] = OWNERS_BEFORE
res["owners_after"] = {k: sha(v) for k, v in CONT.OWNERS.items()}
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
print("owner bytes restored:", res["owner_bytes_restored"])
if res.get("traceback"):
    print("\n".join(res["traceback"].strip().splitlines()[-10:]))
sys.exit(0 if res["all_green"] else 1)
