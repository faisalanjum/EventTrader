"""THE WORKFLOW BOUNDARY OWNER — two facts, and no meaning at all.

  1. WHICH rows may be published next, DERIVED from the externally pinned root
     and the existing lifecycle state, and how many of them fit in one script,
     decided from the EXACT bytes the existing renderer would write.
  2. HOW a Workflow TOOL refusal that created no run is closed, durably, so the
     lifecycle can move on without anyone deleting or rewriting a byte.

Why it lives outside `a7_g1_build`: a frozen root pins that file's hash, so
editing it mid-run would make every later publication fail owner drift. This
owner is pinned separately, by the reviewer, per root.

It renders and reads ONLY through `a7_g1_build`. It never parses a prompt, a
reply, or the WORDING of an error. A refusal is recognised structurally: the
transport's own `is_error` flag on the uniquely linked result, the ABSENCE of
the transport's own run-identity fields, and the measured absence of any
official state or transcript naming this exact script. There is no regex, no
keyword list, no threshold about meaning, and no fallback.

Nothing here trusts a caller. The root is loaded from its externally supplied
hash; the eligible lanes are derived; a malformed record that could have been
the evidence is a REFUSAL, never a line to skip.
"""
import collections
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import a7_g1_build as G                                          # noqa: E402

#: The transport's proven maximum, taken from its own refusal of a larger
#: script. An EXTERNAL PROTOCOL LIMIT, not a judgement about content.
SCRIPT_BYTE_LIMIT = 524288
CLOSURE_KIND = "prelaunch_refusal"
#: this gate admits PRIMARY rows only; retries are the finalizer's
PRIMARY_ATTEMPT = 1
SCHEMA = "a7_g1_workflow_gate/1"

#: The exact input a FRESH launch carries. A resume adds `resumeFromRunId`, so
#: an exact key set is what separates one from the other.
LAUNCH_INPUT_KEYS = ("args", "scriptPath")
#: The transport's own run-identity fields. Their presence means a run exists.
RUN_IDENTITY_KEYS = ("runId", "taskId", "transcriptDir")


def owner_sha256():
    """This owner's live bytes. The reviewer pins this value per root."""
    return G._sha_file(os.path.abspath(__file__))


def refusal_path(run_dir, n):
    return os.path.join(run_dir, "prelaunch_refusal.seg%02d.json" % n)


# ------------------------------------------------- 1. admission by exact size
def _script_bytes(out_dir, root, lanes, attempt):
    """The EXACT byte size the publisher would write for these lanes.

    The invocation hash is always 64 hex characters, so a placeholder of the
    same length yields the byte-exact length of the real script. This calls the
    SAME renderer the publisher calls; it is not a model of it.
    """
    rows, problems = G._rows_for(out_dir, root, list(lanes), attempt)
    if problems:
        return None, problems
    return len(G._bound_script(rows, root, "0" * 64, attempt)
               .encode("utf-8")), []


def _largest_prefix(out_dir, root, lanes, attempt):
    """The largest NONEMPTY prefix of `lanes` whose exact script fits."""
    size, problems = _script_bytes(out_dir, root, lanes[:1], attempt)
    if problems:
        return [], None, problems
    if size > SCRIPT_BYTE_LIMIT:
        return [], size, ["%s alone renders %d bytes, over the transport's %d"
                          % (lanes[0], size, SCRIPT_BYTE_LIMIT)]
    best = 1
    for k in range(2, len(lanes) + 1):
        got, problems = _script_bytes(out_dir, root, lanes[:k], attempt)
        if problems:
            return [], None, problems
        if got > SCRIPT_BYTE_LIMIT:
            break
        best, size = k, got
    return lanes[:best], size, []


def next_admissible(out_dir, run_dir, expect_root_sha):
    """The next PRIMARY rows to publish. -> (lanes, bytes, problems).

    THE CALLER CHOOSES NOTHING - not the lanes, not their order, and not the
    attempt. This is attempt 1 only; a retry set is the finalizer's to name and
    has no business in a size gate.

    The existing lifecycle owner runs BEFORE any sizing, so a pending
    publication, an already-called lane or anything else it refuses stops this
    outright. No second lifecycle rule is invented here.
    """
    try:
        root = G.load_root(run_dir, expect_root_sha)
    except ValueError as exc:
        return [], None, [str(exc)]
    states = G.lane_states(run_dir)                 # the existing owner decides
    lanes = [r["lane_id"] for r in root["rows"]
             if states.get(r["lane_id"], "unseen") != "called"]
    if not lanes:
        return [], None, ["every primary lane of this root has been called"]
    problems = G.lifecycle_problems(run_dir, root, lanes, PRIMARY_ATTEMPT)
    if problems:
        return [], None, problems
    return _largest_prefix(out_dir, root, lanes, PRIMARY_ATTEMPT)


# ------------------------------------- 2. closing a refusal that created no run
def _parent_records(session_jsonl, script_path, tool_use_id):
    """Every Workflow use naming this script, and the results linked to them.

    -> (uses, results, problems). A line that MENTIONS this script or this tool
    id but cannot be parsed is a refusal, never a line to skip: the one record
    that would have disproved the closure must never be lost to a `continue`.
    """
    uses, results, problems = [], [], []
    with io.open(session_jsonl, encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            # a mechanical prefilter on two exact strings; it decides nothing
            if script_path not in line and tool_use_id not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                problems.append("line %d of the session mentions this script or "
                                "tool id and is not readable JSON" % number)
                continue
            body = (rec.get("message") or {}).get("content")
            for block in body if isinstance(body, list) else []:
                if not isinstance(block, dict):
                    continue
                if (block.get("type") == "tool_use"
                        and block.get("name") == "Workflow"
                        and (block.get("input") or {}).get("scriptPath")
                        == script_path):
                    uses.append((rec, line, block))
                if block.get("type") == "tool_result":
                    results.append((rec, line, block))
    return uses, results, problems


def _states_naming(script_path):
    """Every official Workflow state whose scriptPath is EXACTLY this one.

    -> (matches, scanned, problems). An unreadable or non-object state file is
    a PROBLEM, not a file to skip: a place we could not look is not a place
    where nothing is.
    """
    import audit_worker_access as AUD
    matches, scanned, problems = [], 0, []
    root = AUD.PROJECTS_ROOT
    if not os.path.isdir(root):
        return matches, scanned, ["%s is not a directory" % root]
    for here, _dirs, files in os.walk(root):
        if os.path.basename(here) != "workflows":
            continue
        if os.path.basename(os.path.dirname(here)) == "subagents":
            continue
        for name in sorted(files):
            if not name.endswith(".json"):
                continue
            scanned += 1
            path = os.path.join(here, name)
            try:
                with io.open(path, encoding="utf-8") as fh:
                    body = json.load(fh)
            except (ValueError, OSError) as exc:
                problems.append("the official state %s cannot be read (%s)"
                                % (path, type(exc).__name__))
                continue
            if not isinstance(body, dict):
                problems.append("the official state %s is not an object" % path)
                continue
            if body.get("scriptPath") == script_path:
                matches.append((path, body.get("runId")))
    return matches, scanned, problems


def _transcripts_for(run_ids):
    """Child transcript directories for any of these run ids. -> [paths]."""
    import audit_worker_access as AUD
    out = []
    if not run_ids or not os.path.isdir(AUD.PROJECTS_ROOT):
        return out
    for here, dirs, _files in os.walk(AUD.PROJECTS_ROOT):
        if os.path.basename(here) != "workflows":
            continue
        if os.path.basename(os.path.dirname(here)) != "subagents":
            continue
        for name in sorted(dirs):
            if name in run_ids:
                out.append(os.path.join(here, name))
    return out


def _no_output(run_dir, n, receipt, allow=()):
    """Every reason this segment has already produced output. -> [problems].

    `allow` names artifacts a RESUME has already staged; everything else must be
    absent. Canonical raw, EXTRA raw, errors and captures are each checked on
    their own naming, because they do not share one.
    """
    problems = []
    if G._captures_of(run_dir, n):
        problems.append("segment %d already has captures" % n)
    for label, path in (("accounting", G.accounting_path(run_dir, n)),
                        ("finalization", G.finalization_path(run_dir, n)),
                        ("refusal evidence", refusal_path(run_dir, n))):
        if label not in allow and os.path.isfile(path):
            problems.append("segment %d already has %s" % (n, label))
    #: raw is named by the RECEIPT ordinal; extra and errors by the CAPTURE
    #: identity. Three shapes, so each is asked on its own terms.
    stems = {
        G.RAW_DIRNAME: [G.raw_stem(r["ordinal"], receipt["attempt"])
                        for r in receipt["rows"]],
        G.EXTRA_DIRNAME: [G._seg(n) + "."],
        G.ERROR_DIRNAME: [G._seg(n) + "."]}
    for label, sub in (("raw replies", G.RAW_DIRNAME),
                       ("extra raw output", G.EXTRA_DIRNAME),
                       ("errors", G.ERROR_DIRNAME)):
        here = os.path.join(run_dir, sub)
        if not os.path.isdir(here):
            continue
        if any(name.startswith(stem) for name in sorted(os.listdir(here))
               for stem in stems[sub]):
            problems.append("segment %d already has %s" % (n, label))
    return problems


def inspect_prelaunch_refusal(out_dir, run_dir, n, expect_root_sha,
                              expect_receipt_sha, expect_owner_sha,
                              session_jsonl, tool_use_id, allow=()):
    """READ-ONLY. Every condition that must hold before anything is written.

    -> (evidence, problems). `evidence` is None whenever a single condition
    fails, so a caller cannot write half a closure. The two parent records are
    carried WHOLE, with their exact raw lines.
    """
    if expect_owner_sha != owner_sha256():
        return None, ["this owner is %s, not the reviewed %s"
                      % (owner_sha256(), expect_owner_sha)]
    _packet, problems = G.preflight(out_dir, run_dir, n, expect_root_sha,
                                    expect_receipt_sha)
    if problems:
        return None, problems
    receipt = G.load_receipt(run_dir, n)
    published = G._read(receipt["invocation_path"])
    script_path = receipt["script_path"]

    uses, results, problems = _parent_records(session_jsonl, script_path,
                                              tool_use_id)
    if problems:
        return None, problems
    # EXACTLY ONE launch of this script, and it must be the one we were given.
    if len(uses) != 1:
        return None, ["the session records %d Workflow uses naming %s; exactly "
                      "one is required" % (len(uses), script_path)]
    use_rec, use_line, use_block = uses[0]
    if use_block.get("id") != tool_use_id:
        return None, ["the only Workflow use of this script is %r, not the "
                      "supplied %r" % (use_block.get("id"), tool_use_id)]
    linked = [r for r in results if r[2].get("tool_use_id") == tool_use_id]
    if len(linked) != 1:
        return None, ["the session records %d results for %s; exactly one is "
                      "required" % (len(linked), tool_use_id)]
    res_rec, res_line, res_block = linked[0]

    if sorted((use_block.get("input") or {})) != sorted(LAUNCH_INPUT_KEYS):
        problems.append("the tool use carries %s, not a fresh launch's %s"
                        % (sorted(use_block.get("input") or {}),
                           sorted(LAUNCH_INPUT_KEYS)))
    args = (use_block.get("input") or {}).get("args")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = None
    if args is None or G._plain(args) != G._plain(published["args"]):
        problems.append("the tool use did not carry the published invocation "
                        "arguments")
    if res_rec.get("parentUuid") != use_rec.get("uuid"):
        problems.append("the result is not linked to that tool use")
    if not use_rec.get("uuid") or not res_rec.get("uuid"):
        problems.append("a parent record carries no uuid")
    if use_rec.get("sessionId") != res_rec.get("sessionId"):
        problems.append("the two parent records are from different sessions")
    # STRUCTURAL, both ways: flagged an error, and carrying no run identity.
    if res_block.get("is_error") is not True:
        problems.append("the linked result is not flagged as an error")
    outcome = res_rec.get("toolUseResult")
    named = [k for k in RUN_IDENTITY_KEYS
             if (isinstance(outcome, dict) and k in outcome)
             or k in res_block or k in res_rec]
    if named:
        problems.append("the result carries run identity %s; a run exists"
                        % sorted(named))

    # A sidecar we cannot read, or that is not an object at all, is a NAMED
    # refusal. It used to raise, which is a crash where a verdict belongs.
    try:
        sidecar = G._read(receipt["state_path"])
    except (ValueError, OSError) as exc:
        sidecar = None
        problems.append("the state sidecar at %s cannot be read (%s)"
                        % (receipt["state_path"], type(exc).__name__))
    if sidecar is not None and not isinstance(sidecar, dict):
        problems.append("the state sidecar is a %s, not an object"
                        % type(sidecar).__name__)
        sidecar = None
    if sidecar is not None:
        if sorted(sidecar) != ["run_id", "states"]:
            problems.append("the state sidecar carries %s, not exactly run_id "
                            "and states" % sorted(sidecar))
        if sidecar.get("run_id") != receipt["run_id"]:
            problems.append("the state sidecar names run %r, not %r"
                            % (sidecar.get("run_id"), receipt["run_id"]))
        if sidecar.get("states") != []:
            problems.append("the state sidecar is not an empty state list")
    matches, scanned, scan_problems = _states_naming(script_path)
    problems += scan_problems
    if matches:
        problems.append("an official Workflow state names this script: %s"
                        % matches[0][0])
    transcripts = _transcripts_for({rid for _p, rid in matches if rid})
    if transcripts:
        problems.append("a child transcript exists for this script: %s"
                        % transcripts[0])
    problems += _no_output(run_dir, n, receipt, allow)
    if problems:
        return None, problems

    evidence = collections.OrderedDict([
        ("schema", SCHEMA), ("closure", CLOSURE_KIND), ("segment", n),
        ("attempt", receipt["attempt"]),
        ("root_sha256", expect_root_sha),
        ("receipt_sha256", expect_receipt_sha),
        ("run_id", receipt["run_id"]),
        ("script_path", script_path),
        ("script_sha256", receipt["script_sha256"]),
        ("script_bytes", os.path.getsize(script_path)),
        ("invocation_sha256", receipt["invocation_sha256"]),
        ("owner_sha256", expect_owner_sha),
        ("session_jsonl", os.path.abspath(session_jsonl)),
        ("tool_use_id", tool_use_id),
        # THE TWO PARENT RECORDS, WHOLE, with the exact bytes they arrived as
        ("tool_use_record", json.loads(use_line)),
        ("tool_use_raw_line", use_line),
        ("tool_use_raw_line_sha256", G._sha(use_line)),
        ("tool_result_record", json.loads(res_line)),
        ("tool_result_raw_line", res_line),
        ("tool_result_raw_line_sha256", G._sha(res_line)),
        # RECORDED as evidence, never used to decide anything
        ("error_value", outcome),
        ("workflow_uses_naming_this_script", len(uses)),
        ("official_states_naming_this_script", 0),
        ("child_transcripts", 0),
        ("captures", 0), ("raw_replies", 0), ("extra_raw", 0), ("errors", 0),
        ("lanes", [r["lane_id"] for r in receipt["rows"]]),
        # NOT part of this evidence's identity: the tree keeps growing, so a
        # resume must not be blocked by a count that was always transient.
        ("transient", collections.OrderedDict([
            ("official_states_scanned", scanned)]))])
    return evidence, []


def _zero_capture_accounting(run_dir, n, receipt):
    """The ONE accounting a segment with no captures can lawfully have.

    This is not a second renderer: with zero captures the existing owner's
    result is closed-form - the first receipt row is `missing`, every later row
    is `stopped_tail`, because the tail opens as soon as a row is not served.
    Written out here so the WHOLE object can be compared, not four fields of it.
    """
    order = [r["lane_id"] for r in receipt["rows"]]
    outcomes = collections.OrderedDict(
        (lane, "missing" if i == 0 else "stopped_tail")
        for i, lane in enumerate(order))
    counts = collections.Counter(outcomes.values())
    return collections.OrderedDict([
        ("schema", G.SCHEMA), ("segment", n), ("attempt", receipt["attempt"]),
        ("receipt_sha256", G._sha_file(G.receipt_path(run_dir, n))),
        ("captures", []), ("selected", len(order)),
        ("outcomes", outcomes),
        ("counts", collections.OrderedDict(sorted(counts.items())))])


def _stable(evidence):
    """The evidence minus the parts that were never its identity."""
    return G._plain(collections.OrderedDict(
        (k, v) for k, v in evidence.items() if k != "transient"))


def close_prelaunch_refusal(out_dir, run_dir, n, expect_root_sha,
                            expect_receipt_sha, expect_owner_sha,
                            session_jsonl, tool_use_id):
    """Durably close a segment the transport refused before any run existed.

    -> (final, problems). Evidence first, then the ordinary accounting from zero
    captures, then a finalization that says plainly what happened.

    IT RESUMES. An interrupted closure left exact artifacts behind; those are
    verified and continued, never overwritten. Anything that does not match
    exactly is a refusal, and the live no-run facts are re-checked immediately
    before the finalization is written.
    """
    if os.path.isfile(G.finalization_path(run_dir, n)):
        return None, ["segment %d is already closed" % n]
    staged = []
    if os.path.isfile(refusal_path(run_dir, n)):
        staged.append("refusal evidence")
    if os.path.isfile(G.accounting_path(run_dir, n)):
        if "refusal evidence" not in staged:
            return None, ["segment %d has accounting but no refusal evidence"
                          % n]
        staged.append("accounting")

    evidence, problems = inspect_prelaunch_refusal(
        out_dir, run_dir, n, expect_root_sha, expect_receipt_sha,
        expect_owner_sha, session_jsonl, tool_use_id, allow=tuple(staged))
    if problems:
        return None, problems

    if "refusal evidence" in staged:
        if _stable(G._read(refusal_path(run_dir, n))) != _stable(evidence):
            return None, ["the staged refusal evidence for segment %d is not "
                          "the evidence this run derives" % n]
    else:
        G._write_new(refusal_path(run_dir, n), G._pretty(evidence) + "\n")

    receipt = G.load_receipt(run_dir, n)
    if "accounting" in staged:
        # THE WHOLE OBJECT, not a few fields of it: a changed schema, selected
        # count, outcome or count is exactly as disqualifying as a changed hash.
        staged_acc = G._read(G.accounting_path(run_dir, n))
        want = _zero_capture_accounting(run_dir, n, receipt)
        if G._plain(staged_acc) != G._plain(want):
            return None, ["the staged accounting for segment %d is not the "
                          "canonical zero-capture accounting of it" % n]
        accounting = staged_acc
    else:
        accounting = G.account_segment(
            run_dir, n, G.load_root(run_dir, expect_root_sha))

    # THE LAST LOOK IS THE WHOLE INSPECTION, repeated. A subset of it once let a
    # second Workflow use appear between staging and finalization; re-deriving
    # the entire evidence and requiring it to equal what we started with catches
    # a late parent record, sidecar, capture, raw, error or state alike.
    again, problems = inspect_prelaunch_refusal(
        out_dir, run_dir, n, expect_root_sha, expect_receipt_sha,
        expect_owner_sha, session_jsonl, tool_use_id,
        allow=("refusal evidence", "accounting"))
    if problems:
        return None, problems
    if _stable(again) != _stable(evidence):
        return None, ["the evidence for segment %d changed between staging and "
                      "finalization" % n]

    lanes = [r["lane_id"] for r in receipt["rows"]]
    final = collections.OrderedDict([
        ("schema", G.SCHEMA), ("segment", n), ("attempt", receipt["attempt"]),
        ("root_sha256", expect_root_sha),
        ("candidate_sha256", receipt["candidate_sha256"]),
        ("receipt_sha256", accounting["receipt_sha256"]),
        ("accounting_sha256", G._sha_file(G.accounting_path(run_dir, n))),
        ("validity", [[lane, False] for lane in lanes]),
        ("problems", collections.OrderedDict(
            (lane, [CLOSURE_KIND]) for lane in lanes)),
        ("retry", []), ("uncalled", list(lanes)),
        # ZERO CALLS HAPPENED, so the ledger counts zero. Writing len(lanes)
        # here billed a refusal that never reached a model, and then billed the
        # same lanes again when they were republished and served - 2N for N.
        # Every lane is still visibly refused, just above: invalid, uncalled,
        # credited nothing.
        ("ledger", collections.OrderedDict([
            ("scheduled", 0), ("valid", 0),
            ("invalid", 0), ("retry", 0),
            ("uncalled", len(lanes))])),
        # THE CLOSURE IS NAMED. This finalization must never be mistaken for
        # one the official state auditor produced, because it did not run.
        ("closure", CLOSURE_KIND),
        ("state_audited", False),
        ("credited", 0),
        ("refusal_sha256", G._sha_file(refusal_path(run_dir, n))),
        ("workflow_gate_sha256", expect_owner_sha)])
    G._write_new(G.finalization_path(run_dir, n), G._pretty(final) + "\n")
    return final, []
