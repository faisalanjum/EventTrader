"""The ONE read-only proof of a signer call (Codex SEQ 1919).

The harvest owner proved a call inline, and the compact owner then re-checked a
few of the fields that call's own record supplied - so a record could name a run
that never happened, and two calls could carry one response identity. Both
boundaries now ask the same callable, and it derives every identity from the
official state and the transcript instead of believing the record.

READ-ONLY, by contract: it never writes, never waits for an answer, and never
quietly accepts a missing field. Waiting stays in the harvest owner; so does
every write. The transcript, its response identities and the one complete
ordered answer are audit_worker_access._g1_transcript's, the state and the final
segment are build_kfields_key's, and the outcome is build_kfields_final's single
parser. Nothing here is a second implementation of any of them.
"""
import collections, hashlib, io, json, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import audit_worker_access as AUD                                # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import build_kfields_key as K                                    # noqa: E402

sha = lambda t: hashlib.sha256(t.encode("utf-8")
                               if isinstance(t, str) else t).hexdigest()
shaf = lambda p: sha(io.open(p, "rb").read())
#: the label the signer's own launcher asks the runtime for
LABEL = "a4-final-signer"


def state_of(sess, run_id):
    """Where the runtime puts THIS run's official state."""
    return os.path.join(sess, "workflows", run_id + ".json")


def packet(sig, man, attempt):
    """The frozen prompt and this attempt's own launcher. -> (prompt, script)"""
    pp = os.path.join(sig, "signer_prompt.txt")
    sp = os.path.join(sig, "final_sign.attempt%d.js" % attempt)
    # A MISSING PIECE IS A NAMED REFUSAL, never a traceback: this callable is
    # asked about packets that may have lost a file.
    prompt = io.open(pp, encoding="utf-8").read() if os.path.isfile(pp) else None
    script = io.open(sp, encoding="utf-8").read() if os.path.isfile(sp) else None
    want = next((s["sha256"] for s in man.get("scripts") or []
                 if s["attempt"] == attempt), man["script_sha256"])
    bad = []
    if prompt is None:
        bad.append("the frozen prompt is gone")
    elif sha(prompt) != man["prompt_sha256"]:
        bad.append("the frozen prompt moved")
    if script is None:
        bad.append("attempt %d's frozen launcher is gone" % attempt)
    elif sha(script) != want:
        bad.append("attempt %d's frozen launcher moved" % attempt)
    return prompt, script, bad


def outcome_of(text):
    """The ONE parser. -> (object or None, outcome, problems)"""
    obj, problems = F.read_signature(text)
    if problems:
        return None, "invalid_response", problems
    return obj, ("signed" if obj["signed"] is True else "refused"), []


def _model_ids(path):
    """The runtime model ids an assistant record names. A record or a message
    that is not an object names none; the transcript owner has already refused
    it, and this reader must not raise on the way past."""
    out = set()
    for rec in AUD._jsonl(path) or []:
        if not isinstance(rec, dict) or rec.get("type") != "assistant":
            continue
        msg = rec.get("message")
        if isinstance(msg, dict) and msg.get("model") is not None:
            out.add(msg["model"])
    return out


def prove(sig, man, attempt, run_id, sess, response_ids):
    """Everything one signer call must be, derived. -> (proof, problems)

    `response_ids` is ONE dictionary shared across the attempts being proved:
    that is how a response identity reused between two calls is caught, and the
    rule is the transcript owner's, not this file's.
    """
    proof = collections.OrderedDict([("attempt", attempt), ("run_id", run_id)])
    # THE IDENTITY VALUE ITSELF, at the one boundary that owns it. A run
    # identity is a non-empty string and nothing else; every other JSON value
    # class - absent, null, list, object, number, boolean, empty string - used
    # to reach state_of() and raise TypeError there, so a malformed binding
    # crashed the caller instead of being accounted for. This is a rule about
    # the VALUE CLASS, not a list of the two examples that found it
    # (Codex SEQ 1928 item 1).
    if not isinstance(run_id, str) or not run_id:
        return proof, ["the record names %r as its call, which is not a run "
                       "identity" % (run_id,)]
    prompt, script, bad = packet(sig, man, attempt)
    if prompt is None or script is None:
        return proof, bad          # nothing can be proved against bytes that are gone
    state = state_of(sess, run_id)
    proof["state_path"] = state
    if not os.path.isfile(state):
        return proof, bad + ["%s has no official state at %s" % (run_id, state)]
    session_dir, session_id = AUD._official_location(state)
    if session_dir is None:
        bad.append("the state is not where the runtime puts an official one")
    elif session_id != K.PARENT_SESSION:
        bad.append("parent session %r is not the frozen one" % session_id)
    if session_dir is None:
        return proof, bad          # nothing below can be located without it
    try:
        doc = json.load(io.open(state, encoding="utf-8"))
    except Exception as exc:                          # noqa: BLE001 - by design
        return proof, bad + ["the official state is not readable: %s"
                             % str(exc)[:80]]
    if not isinstance(doc, dict):
        return proof, bad + ["the official state is a %s, not an object"
                             % type(doc).__name__]
    if doc.get("runId") != run_id:
        bad.append("the state names run %r, not %r" % (doc.get("runId"), run_id))
    if doc.get("status") != "completed":
        bad.append("the state status is %r" % doc.get("status"))
    if doc.get("script") != script:
        bad.append("the state did not run attempt %d's frozen launcher" % attempt)
    sp = doc.get("scriptPath")
    if sp is not None:
        if not (isinstance(sp, str) and os.path.isfile(sp)):
            bad.append("scriptPath %r is not readable" % sp)
        elif shaf(sp) != sha(script):
            bad.append("the scriptPath bytes are not the frozen launcher")
    progress = doc.get("workflowProgress") or []
    if not isinstance(progress, list) or any(not isinstance(r, dict)
                                             for r in progress):
        return proof, bad + ["the state's progress carries a member that is "
                             "not an object"]
    rows = [r for r in progress if r.get("type") == "workflow_agent"]
    if len(rows) != 1:
        return proof, bad + ["%d agent rows; one call runs exactly one"
                             % len(rows)]
    row = rows[0]
    agent = row.get("agentId")
    proof["agent_id"] = agent
    if row.get("label") != LABEL:
        bad.append("the agent row is labelled %r, not %r" % (row.get("label"), LABEL))
    if row.get("state") != "done":
        bad.append("the agent row state is %r" % row.get("state"))
    if doc.get("totalToolCalls") != 0 or row.get("toolCalls") not in (0, None):
        bad.append("tool calls recorded: %r / %r"
                   % (doc.get("totalToolCalls"), row.get("toolCalls")))
    got = K.direct_result(doc)
    if got is None:
        return proof, bad + ["the state carries no returned object"]
    if set(got) != set(F.SIGNER_RESULT_FIELDS):
        return proof, bad + ["the returned object's keys are %s, not exactly %s"
                             % (sorted(got), sorted(F.SIGNER_RESULT_FIELDS))]
    # the attempt is a POSITION: a boolean or a float that merely compares
    # equal has not answered for it (the final owner's own genuine-integer test)
    if not F._index_is(got.get("attempt"), attempt):
        bad.append("the returned attempt is %r, not the integer %r"
                   % (got.get("attempt"), attempt))
    for field, want in (("role", "signer"), ("model", K.MODEL),
                        ("effort", K.EFFORT), ("agentType", K.AGENT_TYPE)):
        if got.get(field) != want:
            bad.append("the returned %s is %r, not %r" % (field, got.get(field), want))
    # THE TRANSCRIPT, its response identities and the one complete answer are
    # the transcript owner's; the shared dictionary is what makes a reused
    # identity visible across attempts.
    tp = os.path.join(session_dir or "", "subagents", "workflows", run_id,
                      "agent-%s.jsonl" % agent)
    problems, t_final, t_complete = AUD._g1_transcript(
        session_dir, session_id, run_id, agent, sha(prompt),
        K.RUNTIME_MODEL_ID, K.EFFORT, response_ids)
    bad += list(problems or [])
    if problems:
        # STOP HERE. The transcript owner has already named what is wrong with
        # these records; handing them on to a reader that assumes a shape would
        # turn a named refusal into a traceback, and an exception is not an
        # outcome the harvest owner can record.
        return proof, bad
    # the FINAL SEGMENT and the COMPLETE answer are different things and stay so
    final, complete, why = K._official_proof(state, prompt)
    bad += list(why or [])
    if got.get("text") != final:
        bad.append("the returned text is not the proved final segment")
    if t_complete and complete and t_complete != complete:
        bad.append("the transcript's complete answer is not the proved one")
    if not complete:
        return proof, bad + ["the call has no complete proved answer"]
    obj, outcome, parser_problems = outcome_of(complete)
    proof.update(collections.OrderedDict([
        ("transcript_path", tp),
        ("state_sha256", shaf(state)), ("transcript_sha256", shaf(tp)),
        ("raw_sha256", sha(complete)), ("raw_chars", len(complete)),
        ("prompt_sha256", sha(prompt)), ("script_sha256", sha(script)),
        ("parent_session_id", session_id),
        ("model", got.get("model")), ("effort", got.get("effort")),
        ("agent_type", got.get("agentType")),
        ("runtime_model_ids", sorted(_model_ids(tp))),
        ("tool_calls", doc.get("totalToolCalls")),
        ("total_tokens", doc.get("totalTokens")),
        ("duration_ms", doc.get("durationMs")),
        ("parser", "build_kfields_final.read_signature"),
        ("parser_problems", parser_problems), ("outcome", outcome)]))
    proof["_text"] = complete
    proof["_reply"] = obj
    return proof, bad


#: the record fields a proved call must agree with, all derived above
RECORDED = ("run_id", "agent_id", "attempt", "state_path", "transcript_path",
            "state_sha256", "transcript_sha256", "raw_sha256", "raw_chars",
            "prompt_sha256", "script_sha256", "parent_session_id", "model",
            "effort", "agent_type", "runtime_model_ids", "tool_calls",
            "parser", "outcome")


def _same(saved, derived):
    """The same JSON answer: same type AND same value. `true`, `1` and `1.0`
    are three different answers that Python compares equal, and a proof written
    down is not free to change which one it was."""
    return type(saved) is type(derived) and saved == derived


def disagreements(record, proof):
    """What the saved record claims that the proof did not derive."""
    bad = []
    for field in RECORDED:
        if field not in record:
            bad.append("the record carries no %s" % field)
        elif not _same(record[field], proof.get(field)):
            bad.append("the record's %s is %r, not the derived %r"
                       % (field, record[field], proof.get(field)))
    return bad


# --------------------------------------------------------------------------
# WHICH SAVED CALL THIS PACKET IS ENTITLED TO NEXT (Codex SEQ 1928 item 1).
#
# This lived only in a TEST caller, so the real owners could not offer it and
# every consumer would have had to re-implement it. It belongs here, beside
# the proof it is built on: prove() and disagreements() remain the single
# identity proof, the harvest owner remains the persistence and wait owner,
# and the retry law stays where it already is. Nothing below is a second
# proof engine, a journal, a coordinator or a retry policy - it reads the
# packet's own records, asks prove() about each call they name, and returns a
# decision.
#
# THE CLASSES, and every one of them costs ZERO new calls except the first:
#   "launch"   nothing anywhere records a call for this attempt
#   "reuse"    a proved saved success, already complete
#   "recover"  a proved ORIGINAL call whose local captures are incomplete;
#              the harvest finishes them, and no new call is made
#   "refuse"   a record of a call exists and cannot be used - named
# --------------------------------------------------------------------------

#: the packet's own records, and which of them binds a call to an identity
BINDING_RECORDS = ("evidence", "invocation")
LOCAL_RECORDS = BINDING_RECORDS + ("reply",)


def _record(sig, attempt, kind):
    """One saved record. -> (doc, problem) with problem set when it is unusable."""
    path = os.path.join(sig, "final_sign.attempt%d.%s.json" % (attempt, kind))
    if not os.path.isfile(path):
        return None, None
    name = os.path.basename(path)
    try:
        doc = json.load(io.open(path, encoding="utf-8"))
    except Exception as exc:                          # noqa: BLE001 - by design
        return None, "%s is not readable JSON (%s)" % (name, type(exc).__name__)
    if not isinstance(doc, dict):
        return None, "%s is a %s, not a record" % (name, type(doc).__name__)
    return doc, None


def _relevant_calls(sig, man, attempt, sess):
    """Official calls that RAN this attempt's frozen launcher.

    -> ([run_id], problems). A problem means the inventory could not be
    completed; it is NEVER the same as finding nothing.

    OCCURRENCE, NOT USABILITY, and that distinction is the whole point. A state
    whose script IS this packet's frozen launcher is deterministic evidence
    that a call happened; whether its answer can be proved is a separate
    question, asked afterwards by prove(). The previous version kept only the
    runs that proved, so a call that was still running, or whose transcript had
    gone, left an empty list and the packet looked unserved - the same
    missing/invalid/waiting-versus-unrun defect one level lower
    (Codex SEQ 1929).

    It is still not filename order and still not the answer: identical answers
    from different calls stay indistinguishable, which is why a caller may only
    act on a UNIQUE relevant call.
    """
    folder = os.path.join(sess, "workflows")
    if not os.path.isdir(folder):
        return [], ["the official call inventory is unavailable: there is no "
                    "%s to read" % folder]
    _prompt, script, bad = packet(sig, man, attempt)
    if script is None:
        return [], bad or ["attempt %d's frozen launcher is gone, so no "
                           "official call can be matched to it" % attempt]
    try:
        listing = sorted(os.listdir(folder))
    except OSError as exc:                            # noqa: BLE001 - by design
        # A DIRECTORY THAT CANNOT BE LISTED is the same incomplete inventory
        # as a file that cannot be read; letting the error escape unnamed
        # would leave the caller with no accounted answer at all.
        return [], ["the official call inventory at %s cannot be listed (%s), "
                    "so it is incomplete" % (folder, type(exc).__name__)]
    out, problems = [], []
    for name in listing:
        if not name.endswith(".json"):
            continue
        run = name[:-len(".json")]
        try:
            doc = json.load(io.open(os.path.join(folder, name),
                                    encoding="utf-8"))
        except Exception as exc:                      # noqa: BLE001 - by design
            # A FAILED READ IS NOT AN ABSENCE. This used to `continue` on the
            # reasoning that an unreadable state "names no packet", which
            # turned "I could not look" into "nothing was there" - and an
            # empty inventory then authorized a fresh call for a packet that
            # may well have been served (Codex SEQ 1930).
            problems.append("the official state of %s cannot be read (%s), so "
                            "the inventory is incomplete"
                            % (run, type(exc).__name__))
            continue
        if not isinstance(doc, dict):
            problems.append("the official state of %s is a %s, not an object, "
                            "so the inventory is incomplete"
                            % (run, type(doc).__name__))
            continue
        # THE CLASSIFYING FIELD IS VALIDATED BEFORE IT CLASSIFIES. A record
        # with no script, or with a list where the launcher belongs, is not a
        # DIFFERENT known launcher - it is a record that cannot be placed, and
        # calling it unrelated turns "I cannot tell" into "not this packet"
        # (Codex SEQ 1931). A readable string that simply differs is genuinely
        # unrelated and is still skipped in silence.
        ran = doc.get("script")
        if not isinstance(ran, str):
            problems.append("the official state of %s carries %s where its "
                            "launcher belongs, so it cannot be classified"
                            % (run, type(ran).__name__))
            continue
        if ran == script:
            out.append(run)
    return out, problems


#: the statuses that mean a call is over, however it ended. This is the
#: harvest owner's own waiting contract, moved here so both owners read ONE
#: rule: asking only for "completed" reported a FAILED call as "has not
#: finished", which is a different and much more patient answer than the truth
#: (Codex SEQ 1930).
TERMINAL = ("completed", "failed", "error")


def _finished(sess, run_id):
    """Is this call over, whatever its outcome? -> bool

    An unreadable or shapeless state has no status to have reached, so it is
    not 'finished'; the caller names that separately rather than waiting on it
    forever.
    """
    try:
        doc = json.load(io.open(state_of(sess, run_id), encoding="utf-8"))
    except Exception:                                 # noqa: BLE001 - by design
        return False
    return isinstance(doc, dict) and doc.get("status") in TERMINAL


#: the fields an invocation may assert about the call it launched, and that
#: prove() derives independently; anything else it carries is metadata this
#: owner has no opinion about
ASSERTED = ("attempt", "prompt_sha256", "script_sha256", "agent_id", "model",
            "effort", "agent_type", "state_path")

#: THE ONE VALUE THE INVOCATION WRITER CAN LEGITIMATELY NOT KNOW. Read from
#: that writer: harvest_final_sign.record() emits attempt, run_id, outcome,
#: problems, state_path, prompt_sha256 and script_sha256, and every one of
#: those is computed at the moment of writing EXCEPT state_path, which is its
#: own `run` argument and defaults to None. Allowing a null in every asserted
#: field instead let an invocation carrying attempt=None or prompt_sha256=None
#: read as agreement (Codex SEQ 1931).
MAY_BE_UNKNOWN = ("state_path",)


def select_saved_call(sig, man, attempt, sess, response_ids=None):
    """Which call this packet is entitled to next. -> (decision, run_id, why)

      "launch"   NOTHING records or shows a call for this attempt
      "reuse"    a proved saved success, already complete
      "recover"  a proved call whose local captures are incomplete; the
                 existing harvest finishes them and makes no new call
      "wait"     a call that has occurred and has not finished
      "refuse"   a call has occurred and cannot be used - named

    Only the first of those costs a call.
    """
    ids = {} if response_ids is None else response_ids
    # THE FROZEN PACKET FIRST. packet() already reports a prompt or launcher
    # that is gone or has moved, and that report used to be discarded: the
    # inventory then searched with the CHANGED bytes, matched nothing, and the
    # empty result authorized a fresh call. Nothing about this packet can be
    # decided while the bytes it is made of are not the ones it was frozen
    # with (Codex SEQ 1930).
    _prompt, _script, frozen = packet(sig, man, attempt)
    if frozen:
        return "refuse", None, ("attempt %d's frozen packet is not intact: %s"
                                % (attempt, frozen[0]))
    records, problems = collections.OrderedDict(), []
    for kind in LOCAL_RECORDS:
        doc, bad = _record(sig, attempt, kind)
        if bad:
            problems.append(bad)
        elif doc is not None:
            records[kind] = doc
    raw = os.path.join(sig, "final_sign.attempt%d.raw.json" % attempt)
    has_raw = os.path.isfile(raw)
    if problems:
        return "refuse", None, "attempt %d: %s" % (attempt, problems[0])

    # EVERY BINDING ASSERTION, KEPT TYPED. Collecting these through a dict
    # keyed by their string form turned None, a list and a number into strings
    # before prove()'s value guard could see them, and dropping the refusals as
    # soon as one record proved let a conflicting or malformed assertion pass
    # unnamed. Conflicts are named BEFORE anything is selected, however many of
    # the others prove (Codex SEQ 1929).
    named = [(kind, records[kind].get("run_id"))
             for kind in BINDING_RECORDS if kind in records]
    distinct = []
    for _kind, value in named:
        if not any(type(value) is type(seen) and value == seen
                   for seen in distinct):
            distinct.append(value)
    if len(distinct) > 1:
        return "refuse", None, (
            "attempt %d's own records name %d different calls (%s); they "
            "disagree about which call this packet made"
            % (attempt, len(distinct), ", ".join(repr(v) for v in distinct)))

    if distinct:
        run = distinct[0]
        proof, why = prove(sig, man, attempt, run, sess, dict(ids))
        if why:
            if isinstance(run, str) and run and not _finished(sess, run):
                return "wait", run, ("attempt %d's call %s has not finished: "
                                     "%s" % (attempt, run, why[0]))
            return "refuse", None, ("attempt %d records a call that does not "
                                    "prove: %r: %s" % (attempt, run, why[0]))
        # The invocation writer's own assertions about the call it launched are
        # checked against the derivation, so a record that names the right call
        # while asserting the wrong packet is a conflict, not a success.
        inv = records.get("invocation") or {}
        for field in ASSERTED:
            if field in inv \
                    and not (field in MAY_BE_UNKNOWN and inv[field] is None) \
                    and not _same(inv[field], proof.get(field)):
                return "refuse", None, (
                    "attempt %d's invocation asserts %s %r, and the call it "
                    "names derives %r" % (attempt, field, inv[field],
                                          proof.get(field)))
        record = records.get("evidence")
        if record is not None:
            # A SAVED RECORD THAT CONTRADICTS THE DERIVATION IS A CONFLICT,
            # not something to recover past. Only a field the record actually
            # CARRIES can contradict: one it never wrote is metadata it could
            # not know yet, and treating that as a refusal would turn a
            # formerly waiting outcome into a permanent one (Codex SEQ 1929).
            clash = [f for f in RECORDED
                     if f in record and not _same(record[f], proof.get(f))]
            if clash:
                return "refuse", None, (
                    "attempt %d's saved record contradicts the call it names: "
                    "%s is %r, and %s derives %r"
                    % (attempt, clash[0], record[clash[0]], run,
                       proof.get(clash[0])))
            if record.get("outcome") == "signed" \
                    and not disagreements(record, proof):
                return "reuse", run, None
        return "recover", run, None

    # NO BINDING RECORD. That is not the same as no call: a capture may be
    # gone, or the call may still be running. Ask the official inventory
    # WITHOUT filtering the unprovable away, and let a local raw or reply -
    # which is itself evidence that an answer arrived - keep this packet out of
    # the launch branch.
    relevant, incomplete = _relevant_calls(sig, man, attempt, sess)
    if incomplete:
        return "refuse", None, (
            "attempt %d holds no record of its own and its official call "
            "inventory could not be completed, so whether it was served is "
            "unknown: %s" % (attempt, incomplete[0]))
    if len(relevant) > 1:
        return "refuse", None, (
            "attempt %d holds no record of its own, and %d official calls ran "
            "its frozen launcher (%s); the original cannot be identified "
            "without guessing" % (attempt, len(relevant), ", ".join(relevant)))
    if not relevant:
        if has_raw or records:
            return "refuse", None, (
                "attempt %d holds %s but no record binding it to a call, and "
                "no official call of its frozen launcher remains; an answer "
                "without its call cannot be used"
                % (attempt, ", ".join(sorted(set(list(records) +
                                                 (["raw"] if has_raw else []))))))
        return "launch", None, None
    run = relevant[0]
    proof, why = prove(sig, man, attempt, run, sess, dict(ids))
    if not why:
        return "recover", run, None
    if not _finished(sess, run):
        return "wait", run, ("attempt %d's call %s has not finished: %s"
                             % (attempt, run, why[0]))
    return "refuse", None, (
        "attempt %d was served by call %s, whose result does not prove: %s"
        % (attempt, run, why[0]))
