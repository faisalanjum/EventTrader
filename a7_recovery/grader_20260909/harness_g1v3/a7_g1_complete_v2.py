"""Versioned completion owner for the EVENT-scoped G1 run.

It owns nothing semantic. It selects the highest valid bounded attempt per
lane, pairs the two blind lanes of each event, hands the two relations to the
ONE relation-to-credit owner (`a7_g1_build.validate_merged`), and records the
audit detail plus one terminal category per gold row. The conservative scalar
projection into unchanged `score_exp5.grade_unmatched` happens inside
`validate_merged`; nothing here re-decides it.
"""
import collections, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import a7_g1_build as G


def select_attempt(attempts):
    """The HIGHEST attempt whose reply the frozen event parser accepted.

    `attempts` is {attempt_number: (relation, problems)}. A lane with no
    accepted attempt is ABSENT and contributes nothing at all.
    """
    best = None
    for n in sorted(attempts):
        rel, problems = attempts[n]
        if not problems:
            best = (n, rel)
    return best


def run_digest(run_dir):
    """-> (digest, file_count) over the WHOLE run, deterministic by path.

    One line `<sha256>  ./<relpath>` per file, sorted bytewise, then hashed -
    the same value `find -exec sha256sum | sort | sha256sum` produces, so the
    externally reviewed number and this one are the same number. An added or
    removed file changes it, not just an edited one.
    """
    lines = []
    for base, _dirs, files in os.walk(run_dir):
        for name in files:
            path = os.path.join(base, name)
            lines.append("%s  %s\n" % (G._sha_file(path),
                                       "./" + os.path.relpath(path, run_dir)))
    return (hashlib.sha256("".join(sorted(lines)).encode("utf-8")).hexdigest(),
            len(lines))


def evidence(out_dir, run_dir, expect_root_sha,
             expect_run_digest, expect_run_files):
    """Turn a REAL run's saved evidence into one relation per lane.

    -> (root, doc, lanes, problems). `lanes[lane_id]` carries every attempt's
    parse, the attempt `select_attempt` chose, and that attempt's relation. A
    lane with no valid attempt is ABSENT and carries no relation at all, which
    keeps its whole event inconclusive after the bound retry.

    Every reply is read by the ONE event parser over the frozen event binding;
    there is no second parser and no scalar path.
    """
    # THE WHOLE-RUN PIN, BEFORE ANY PARSING. The expected values are supplied
    # from OUTSIDE after the run is finalized and independently reviewed; this
    # owner never measures its own expectation.
    digest, files = run_digest(run_dir)
    if digest != expect_run_digest or files != expect_run_files:
        return None, None, None, [
            "the run tree is %s over %d files, not the reviewed %s over %d"
            % (digest, files, expect_run_digest, expect_run_files)]
    problems = []
    root = G.load_root(run_dir, expect_root_sha)
    doc, _sha = G.load_frozen(out_dir, root["candidate_sha256"])
    if G.prompt_tree_sha(out_dir, doc) != root["prompt_tree_sha256"]:
        problems.append("the prompt tree no longer hashes to the root's pin")
    live_owners = G.owner_hashes()
    for name, want in sorted(root["owners"].items()):
        if live_owners.get(name) != want:
            problems.append("owner %s is %s at its own path, not the pinned %s"
                            % (name, live_owners.get(name), want))
    for name in sorted(set(live_owners) - set(root["owners"])):
        problems.append("owner %s is live but the root never pinned it" % name)

    pins = {r["lane_id"]: r for r in root["rows"]}
    verdicts, raw_by_attempt = {}, collections.defaultdict(dict)
    for n in G.segments(run_dir):
        if G.segment_state(run_dir, n) != "finalized":
            problems.append("segment %d is not finalized" % n)
            continue
        fin = G._read(G.finalization_path(run_dir, n))
        if fin["root_sha256"] != expect_root_sha:
            problems.append("finalization %d names another root" % n)
        if fin["receipt_sha256"] != G._sha_file(G.receipt_path(run_dir, n)):
            problems.append("finalization %d does not match its receipt" % n)
        if fin["accounting_sha256"] != G._sha_file(
                G.accounting_path(run_dir, n)):
            problems.append("finalization %d does not match its accounting" % n)
        _packet, pre = G.preflight(out_dir, run_dir, n, expect_root_sha,
                                   fin["receipt_sha256"])
        problems.extend("segment %d preflight: %s" % (n, x) for x in pre)
        uncalled = set(fin["uncalled"])
        for lane, ok in fin["validity"]:
            if lane in uncalled:
                continue
            if (lane, fin["attempt"]) in verdicts:
                problems.append("%s attempt %d was finalized twice"
                                % (lane, fin["attempt"]))
            verdicts[(lane, fin["attempt"])] = ok

    # EACH CAPTURE IS READ AGAINST ITS OWN SEGMENT'S RECEIPT, and its binding
    # is decided by the ONE shared owner (`G._outcome_of`) rather than a second
    # partial copy of that rule here. The copy checked batch_id, ordinal,
    # prompt_sha256, the frozen lane settings and the candidate, but never the
    # invocation hash and never the capture's ORDER - so those two could be
    # wrong and this reader saw nothing (Codex SEQ 1856).
    for n in G.segments(run_dir):
        if G.segment_state(run_dir, n) != "finalized":
            continue                      # already reported above
        receipt_n = G._read(G.receipt_path(run_dir, n))
        for cap in G._captures_of(run_dir, n):
            got = cap["returned"]
            lane, att = got.get("lane_id"), got.get("attempt")
            outcome = G._outcome_of(receipt_n, root, cap)
            if outcome != "served" and outcome != "error":
                problems.append("segment %d %s attempt %s: %s"
                                % (n, lane, att, outcome))
                continue
            # the root's own ceiling and candidate, which the receipt-scoped
            # rule above does not speak for
            if got.get("candidate_sha256") != root["candidate_sha256"]:
                problems.append("%s attempt %s: another candidate"
                                % (lane, att))
                continue
            if att > root["max_attempts"]:
                problems.append("%s attempt %s is past the frozen ceiling"
                                % (lane, att))
                continue
            if (lane, att) not in verdicts:
                problems.append("%s attempt %s was captured but never "
                                "finalized" % (lane, att))
                continue
            ruled_valid = verdicts[(lane, att)]
            if outcome == "error":
                # a correctly bound attempt with no answer is lawful history
                # ONLY when the finalization explicitly ruled it invalid
                if ruled_valid:
                    problems.append("%s attempt %s is finalized valid but "
                                    "produced no answer" % (lane, att))
                continue
            if not cap.get("raw_path"):
                problems.append("%s attempt %s is finalized valid but records "
                                "no raw answer" % (lane, att))
                continue
            raw = os.path.join(run_dir, cap["raw_path"])
            if G._sha_file(raw) != cap["raw_sha256"]:
                problems.append("%s attempt %s: the raw bytes moved"
                                % (lane, att))
                continue
            # THE TERMINAL BYTES ABOVE STILL PROVE THE CAPTURE; what gets READ
            # is the WHOLE answer this segment was finalized on, from the one
            # durable record its finalization bound. Re-reading the last piece
            # here let a later completion or resume reach a different verdict
            # from the finalization it is supposed to be confirming
            # (Codex SEQ 1869 item 1).
            bound, bind_problems = G.whole_answers(run_dir, n)
            if bind_problems:
                problems.extend(bind_problems)
                continue
            if lane not in (bound or {}):
                problems.append("%s attempt %s: its segment bound no whole "
                                "answer for this lane" % (lane, att))
                continue
            raw_by_attempt[lane][att] = bound[lane]

    lanes = collections.OrderedDict()
    for lane in [r["lane_id"] for r in root["rows"]]:
        batch_id = pins[lane]["batch_id"]
        # THE KIND'S OWN binding and parser, through the one seam. G1's pair
        # was hard-coded here, so a G2/G3 run could never reach this whole-run
        # selection and had only an in-memory, segment-scoped helper.
        _binding_of, _parser = G.binding_and_parser(G.task_kind(doc))
        binding = _binding_of(doc, batch_id)
        attempts = {}
        for att in sorted(raw_by_attempt.get(lane, {})):
            rel, bad = _parser(raw_by_attempt[lane][att], binding)
            attempts[att] = (rel, bad)
            if (not bad) != verdicts.get((lane, att)):
                problems.append("%s attempt %d disagrees with its finalization"
                                % (lane, att))
        chosen = select_attempt(attempts)
        lanes[lane] = collections.OrderedDict([
            ("batch_id", batch_id),
            ("attempts", {n: not v[1] for n, v in attempts.items()}),
            ("selected", None if chosen is None else chosen[0]),
            ("relation", None if chosen is None else chosen[1])])
    return root, doc, lanes, problems


def relations_from_run(lanes):
    """The selected relation per lane, absent lanes omitted entirely."""
    return {lane: rec["relation"] for lane, rec in lanes.items()
            if rec["selected"] is not None}


def lane_relations(doc, per_lane):
    """{lane_id: relation} -> {leg: {sid: (relA, relB)}}, using ONLY the frozen
    binding to say which event a lane belongs to. Never reads a reply for that.
    """
    by_batch = {}
    for b in doc["question_bindings"]:
        by_batch.setdefault(b["batch_id"], (b["leg"], b["source_id"]))
    lanes = list(doc["launchers"]["lanes"])
    out, problems = {}, []
    for lane_id, rel in sorted(per_lane.items()):
        batch_id, letter = lane_id.rsplit("/", 1)
        if batch_id not in by_batch:
            problems.append("%s names no frozen event group" % lane_id)
            continue
        if letter not in lanes:
            problems.append("%s is not one of the frozen blind lanes" % lane_id)
            continue
        leg, sid = by_batch[batch_id]
        slot = out.setdefault(leg, {}).setdefault(sid, [None, None])
        slot[lanes.index(letter)] = rel
    return ({leg: {sid: tuple(v) for sid, v in rows.items()}
             for leg, rows in out.items()}, problems)


G23_SCHEMA = "a7_g23_whole_run_completion/1"
G23_NAME = "a7_g23_completion.json"


def g23_identity(root_sha, run_dir):
    """THE structured identity of one finalized run: which candidate, and the
    live run's own digest and file count from the existing whole-run owner.

    A caller-supplied string could name any run; this is re-measured from the
    tree itself, here and again at load, so a completion cannot be carried to
    a different run or survive a change to the one it judged.
    """
    digest, files = run_digest(run_dir)
    return collections.OrderedDict([
        ("root_sha256", root_sha), ("run_dir", run_dir),
        ("run_digest", digest), ("run_files", files)])


def complete_g23(doc, per_lane, identity):
    """-> (result, problems). THE whole-run G2/G3 judgment, PER QUESTION.

    Not segment-scoped and not in memory. `per_lane` is what `evidence` selected
    across EVERY finalized segment, so two lanes that arrived in different
    segments or at different attempts are combined here. Every frozen QUESTION
    is required and reaches exactly one outcome: deciding per BATCH put one
    agreed question and one disagreeing question in the same call into BOTH
    credited and unresolved, and the batch is not the unit anyone judges.
    """
    reconciler = G.task_owners(G.task_kind(doc))[2]
    by_batch = collections.OrderedDict()
    for lane_id, rel in sorted((per_lane or {}).items()):
        by_batch.setdefault(lane_id.rsplit("/", 1)[0], {})[lane_id] = rel

    credited, unresolved, problems = collections.OrderedDict(), [], []
    frozen = collections.OrderedDict()
    for row in doc["batch_rows"]:
        for qid in row["question_ids"]:
            frozen.setdefault(qid, row["batch_id"])

    def _stop(batch_id, qid, reasons):
        # ANY ASPECT THE READINGS DID ESTABLISH travels with the unresolved
        # row. This does not credit the question - it stays unresolved - but
        # it keeps a confirmed finding available to the final consumer.
        established = {}
        for r in reasons or []:
            for k, v in (r.get("established") or {}).items():
                established.setdefault(k, v)
        row = collections.OrderedDict([
            ("batch_id", batch_id), ("question_id", qid),
            # EVERY reason, never truncated: a dropped reason is the evidence
            # for why a question is unresolved.
            ("reasons", list(reasons))])
        if established:
            row["established"] = established
        unresolved.append(row)

    for row in doc["batch_rows"]:
        batch_id, qids = row["batch_id"], list(row["question_ids"])
        lanes = by_batch.get(batch_id, {})
        if len(lanes) != len(G.GRADER_LANES):
            # A MISSING OR UNUSABLE LANE stops every question it owed, one
            # durable row each - not one row for the call.
            for qid in qids:
                _stop(batch_id, qid, [{"reason": "%d of %d blind readings are "
                                       "usable" % (len(lanes),
                                                   len(G.GRADER_LANES))}])
            continue
        first, second = [lanes[k] for k in sorted(lanes)]
        agreed, blocked = reconciler(first, second)
        held = collections.OrderedDict()
        for b in (blocked or []):
            held.setdefault(b.get("question_id"), []).append(b)
        for qid in qids:
            if agreed is None:
                _stop(batch_id, qid, held.get(qid) or held.get(None) or
                      [{"reason": "no usable reading"}])
            elif qid in held or qid not in agreed:
                _stop(batch_id, qid, held.get(qid) or
                      [{"reason": "the frozen question was not answered"}])
            else:
                credited[qid] = collections.OrderedDict([
                    ("batch_id", batch_id), ("verdict", agreed[qid])])
        for qid in sorted(set(held) - set(qids) - {None}):
            problems.append("a reading answered %r, which batch %s does not "
                            "hold" % (qid, batch_id))
    unknown = sorted(set(by_batch) - {r["batch_id"] for r in doc["batch_rows"]})
    if unknown:
        problems.append("replies name batches this candidate does not have: "
                        "%s" % unknown[:3])
    result = collections.OrderedDict([
        ("schema", G23_SCHEMA),
        ("task_kind", G.task_kind(doc)),
        ("run_identity", identity),
        ("batches", len(doc["batch_rows"])),
        ("questions", len(frozen)),
        ("credited", credited),
        ("credited_questions", len(credited)),
        ("unresolved", unresolved),
        ("unresolved_questions", len(unresolved)),
    ])
    reached = list(credited) + [u["question_id"] for u in unresolved]
    if sorted(reached) != sorted(frozen):
        problems.append("every frozen question must be credited or unresolved "
                        "exactly once: %d frozen, %d reached, %d duplicated"
                        % (len(frozen), len(reached),
                           len(reached) - len(set(reached))))
    return result, problems


def persist_g23(out_dir, result):
    """Write the ONE immutable whole-run completion. Refuses to overwrite."""
    path = os.path.join(out_dir, G23_NAME)
    if os.path.exists(path):
        raise ValueError("%s already exists; a completion is written once"
                         % path)
    G._write_new(path, G._pretty(result) + "\n")
    return path, G._sha_file(path)


def load_g23(out_dir, expect_sha, root_sha, run_dir):
    """The completion, refused unless its bytes AND the LIVE run still match.

    The run identity is re-measured from `run_dir` here. Comparing a recorded
    string to a recorded string only proved the file was consistent with
    itself; it could not notice the judged run changing underneath it. This is
    the ONLY lawful G2/G3 input to scoring.
    """
    path = os.path.join(out_dir, G23_NAME)
    got = G._sha_file(path)
    if got != expect_sha:
        raise ValueError("the completion at %s hashes %s, not the approved %s"
                         % (path, got, expect_sha))
    doc = G._read(path)
    live = g23_identity(root_sha, run_dir)
    was = doc.get("run_identity") or {}
    # `run_dir` IS PART OF THE IDENTITY. Comparing only the digest and file
    # count meant two byte-identical runs at different paths were the same
    # identity, so a completion made for one silently opened the other - which
    # is exactly the substitution this binding exists to stop.
    for field in ("root_sha256", "run_dir", "run_digest", "run_files"):
        if was.get(field) != live[field]:
            raise ValueError("the completion was made for %s %r, but this run "
                             "measures %r" % (field, was.get(field),
                                              live[field]))
    return doc


def complete(doc, legs, per_lane, run_pin=None):
    """-> (result, problems). The whole new-run completion, audit included."""
    relations, problems = lane_relations(doc, per_lane)
    pairs, merged_problems, incomplete, report = G.validate_merged(
        relations, legs)
    categories = G.terminal_categories(relations, legs)
    counts = collections.OrderedDict(
        (k, sum(1 for v in categories.values() if v == k)) for k in G.TERMINAL)
    total = sum(counts.values())
    expected = sum(len(legs[l][s]["unmatched_gold"])
                   for l, s in G.expected_groups(legs))
    if total != expected:
        problems.append("terminal categories cover %d gold rows, not %d"
                        % (total, expected))
    # A scorer problem is a BLOCKING failure, not a stored note. Reporting
    # success while parking it under result made the contract lie.
    problems.extend("scorer: %s" % json.dumps(p, sort_keys=True)
                    for p in merged_problems)
    credited = [p for leg in pairs for sid in pairs[leg]
                for p in pairs[leg][sid]]
    result = collections.OrderedDict([
        ("schema", "a7_g1_completion/2"),
        ("inputs", collections.OrderedDict([
            ("run_tree_sha256", None if run_pin is None else run_pin[0]),
            ("run_file_count", None if run_pin is None else run_pin[1])])),
        ("events", len(G.expected_groups(legs))),
        ("gold_rows", expected),
        ("terminal_counts", counts),
        ("terminal_total", total),
        ("accepted_pairs", credited),
        ("audit", collections.OrderedDict(
            ("%s|%s" % k, v) for k, v in sorted(report.items()))),
        ("incomplete", incomplete),
        ("scorer_problems", merged_problems),
        # ONLY components both lanes asserted identically may feed the
        # existing zero duplicate-emission bar.
        ("duplicate_emission_groups", [
            dict(c, leg=k[0], source_id=k[1])
            for k, v in report.items()
            for c in G.confirmed_duplicate_groups(v)]),
        # a contested component is ONE lane's claim: unresolved identity
        # evidence, never a confirmed duplicate
        ("disputed_identity_groups", [
            dict(c, leg=k[0], source_id=k[1])
            for k, v in report.items() for c in v["components"]
            if c["contested"]]),
    ])
    return result, problems
