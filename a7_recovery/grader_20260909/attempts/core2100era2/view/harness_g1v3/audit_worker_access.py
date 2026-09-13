"""Machine audit v9: every drafting worker, PROVED from official Workflow state.

WHY v8 WAS CORRECTED (Codex SEQ 1216 — it REVERSES the earlier final-segment-only
ruling). A response the service ends at `max_tokens` and then continues
automatically, under the same proved worker, is ONE ordered answer. `agent()`
hands back only the LAST group, so every earlier group's text is real answer
bytes that the transport silently drops. Measured across this run's ten
completed responses: seven have earlier text-bearing groups, and they lose
142,785 of the 559,719 characters actually produced. v9 therefore keeps two
facts apart — the saved state row must still equal the final group byte-for-byte
(that binds the row to the runtime), while the HANDOFF row carries a copy whose
text is the exact, zero-delimiter concatenation of every group's terminal text
in transcript order. Nothing is inserted, nothing is parsed, nothing is
repaired, and no saved row is ever rewritten.

WHY v7 WAS HARDENED (Codex SEQ 1212). v7 read what a launch REPORTED about
itself but never what it was ASKED to do, so six forgeries passed clean: a
rejection carrying no evidence at all; a rejection with `blocked=false` plus
attempt, tool calls, a wrong effort and a wrong agent type; an initial launch
that silently dropped a lane which a later attempt-2 response then filled; a run
whose first and only launch claimed attempt 2; retry args naming a lane the
state never exposed; and duplicate rows for one arm hiding a completed sibling.
The cause was one missing binding, not six bugs. v8 reads the state's own saved
`args` — the launcher's own rule decides the kind, a list being the whole event
at attempt 1 and an object naming `pairs` being the one retry — derives the arm
set from it, requires an event's FIRST launch to be its attempt-1 invocation,
maps progress rows one-to-one onto result rows BEFORE counting either, and
requires every retried lane's own proved attempt-1 rejection with no prior
completion and no earlier retry. A no-response rejection must now match the
exact live machine shape (`_rejection`), never merely lack an agentId.

WHY v6 WAS REPLACED (Codex SEQ 1207). v6 asserted that one worker produces
exactly one `(message.id, requestId)` pair. That is false: when an answer is long
the service ends a response at `max_tokens` and CONTINUES it under the SAME
scheduled agentId. This is automatic service continuation, not a second worker,
prompt or experiment call, so v6 rejected two lawful workers. v7 validates the
whole chain as an ORDER instead — see `_chain`. Measured over the complete live
population: of the 1,408 ELIGIBLE one-user zero-tool transcripts, 1,406 are a
single response, and the two exceptions are this plan's own first two calls.

WHY v5 WAS REPLACED (Codex SEQ 1203). v5 checked selected FINAL fields but never
bound the whole transcript and the whole run directory to the official worker
identity, so eleven forgeries were accepted as clean: a second assistant
response, a second user turn, wrong agentId or sessionId on every record, the two
transcripts swapped, a surplus agent file, the state order reversed, effort=low,
a wrong model on a non-final record, an omitted scriptPath, and an entire fake
tree under /tmp. (v4 before it accepted a receipt that CLAIMED the facts it had
to prove; v3 before that REQUIRED three worker Reads, the protocol A3 forbids.)

v7 takes ONE overall run_id and an explicit ordered list of official Workflow
state files, and binds every piece of evidence to the runtime's own identities:

  the receipt lives at <run-dir>/receipt.json and <run-dir> IS run_id, and is
      also the raw_transport output directory — the identity is used, not stated
  every state realpaths under the live projects root as
      <projects>/<project>/<session>/workflows/<runId>.json
  state.script bytes  -> WHICH indexed launcher ran -> the event identity
  the launcher        -> the prompt pin, the arms, the model, the effort
  the state's two progress rows -> the two agentIds
  <session>/subagents/workflows/<runId>/ -> EXACTLY those two workers' four
      files, no surplus and none missing
  every transcript record -> must carry that agentId and that sessionId
  the transcript       -> exactly one user turn (the pinned prompt), assistant
      records that all carry the planned model and high effort, ONE ordered
      continuation chain (unique linked record UUIDs; contiguous non-recurring
      response identities; only a response's last record ends it; every
      non-final response ends `max_tokens` and the final one `end_turn`;
      nothing follows that terminal answer; exactly one text-bearing record in
      the final response), no tool use, no tool result
  state.result         -> the two rows the run recorded, each still equal to its
      worker's FINAL response text byte-for-byte — the saved evidence is bound
      to the runtime and is never rewritten
  the handoff          -> a COPY of each row whose text is the whole answer:
      every proved response group's terminal text, concatenated in transcript
      order with nothing between them

CONTENT IS STILL NEVER JUDGED. The audit does not parse JSON, strip a fence,
repair anything, or choose a concatenation because the result happens to parse —
the order is dictated by the transport alone, and thinking blocks never enter
answer text. `parse_exact`, the V2 door, retry selection and the invalid bucket
remain `raw_transport`'s alone.

EFFORT (corrected by Codex SEQ 1203 against live evidence). A saved STATE's
progress rows carry no effort field, but CURRENT transcripts record top-level
`effort` on their assistant records. So effort is proved from the transcript and
must be exactly the planned value: absent is a FAILURE, not a tolerance. The
persisted `state.script` bytes are still required to be byte-identical to a
reviewed launcher, so the lane table that requested that effort is pinned too.

`raw_transport` stays the sole owner of raw-save, exact parse and door rules:
this module derives the one combined handoff and hands it over unchanged.

Usage:
  venv/bin/python harness/audit_worker_access.py <run-dir>/receipt.json [manifest] [bundle]

Receipt shape — these two keys, and no others:
  {"run_id": "<basename of the directory holding this receipt>",
   "states": ["/abs/.../workflows/wf_aaaaaaaa-111.json", ...]}
"""
import collections
import hashlib
import io
import json
import os
import sys

import raw_transport as RT

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MANIFEST = RT.DEFAULT_MANIFEST
DEFAULT_BUNDLE = os.path.join(_HERE, "launch_kfields_a1.bundle.json")

#: Where the runtime actually stores sessions. An "official" state that does not
#: live here is not official (Codex SEQ 1203: a whole tree under /tmp passed).
PROJECTS_ROOT = os.path.expanduser("~/.claude/projects")

#: The receipt's own filename, so the run directory holding it is unambiguous.
RECEIPT_NAME = "receipt.json"


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_pinned(path, want_sha):
    """(document, problem) for a file the run's OWN plan names and pins.

    A missing, unreadable or drifted bundle is a STRUCTURED refusal, never an
    exception: the paid rows are already on disk by the time the audit runs, so
    an uncaught error here would abandon evidence instead of failing closed
    (Codex SEQ 1405 item 4).
    """
    if not path:
        return None, "the run's plan names no launcher bundle"
    try:
        with io.open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:                            # noqa: BLE001 - by design
        return None, "the launcher bundle is unreadable: %s" % exc
    if want_sha and hashlib.sha256(raw).hexdigest() != want_sha:
        return None, ("the launcher bundle's bytes are not the ones its plan "
                      "pinned")
    try:
        return json.loads(raw.decode("utf-8")), None
    except Exception as exc:                          # noqa: BLE001 - by design
        return None, "the launcher bundle is not readable JSON: %s" % exc


#: THE ONE shape `resumeFromRunId` returns for an already-completed agent. The
#: runtime carries `cached` and the model ALIAS, and omits the progress-row
#: `agentType`, `attempt` and `toolCalls` it writes on a fresh spawn. Frozen as
#: an EXACT key set so a row that is merely missing fields can never match
#: (Codex SEQ 1413).
CACHED_ROW_KEYS = frozenset((
    "agentId", "cached", "index", "label", "lastProgressAt", "model",
    "phaseIndex", "phaseTitle", "promptPreview", "resultPreview", "startedAt",
    "state", "type"))

#: A direct child of the workflow. The runtime's own value; nothing in the plan
#: derives it, so it is named once here rather than inferred.
CACHED_META_SPAWN_DEPTH = 1


def _resumed_cached_row(pr, rid_dir, lane):
    """True only for the exact cached shape backed by its exact agent meta.

    Everything checkable is DERIVED from the planned lane - the alias and the
    agent type both come from `lane`, never from a literal - so this cannot
    become a general missing-field tolerance or a model-alias framework.
    """
    if set(pr) != CACHED_ROW_KEYS or pr.get("cached") is not True:
        return False
    if pr.get("model") != lane["model"]:
        return False
    meta_path = os.path.join(rid_dir, "agent-%s.meta.json" % pr.get("agentId"))
    if not os.path.isfile(meta_path):
        return False
    try:
        with io.open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
    except Exception:                                 # noqa: BLE001 - by design
        return False
    return meta == {"agentType": lane["agentType"], "model": lane["model"],
                    "spawnDepth": CACHED_META_SPAWN_DEPTH}


def _same_published_script(claim, published):
    """True only when the OS proves these name the same regular file.

    Not a path-prefix exception and not a hash allowance: two different files
    with identical bytes are still two files, and are refused. Anything
    missing, malformed or unreadable is refused as well (Codex SEQ 1781).
    """
    if not isinstance(claim, str) or not isinstance(published, str):
        return False
    if not claim or not published:
        return False
    try:
        if not (os.path.isfile(claim) and os.path.isfile(published)):
            return False
        return os.path.samefile(claim, published)
    except OSError:
        return False


def record_state(receipt_path, run_id, state_path):
    """Append one completed official state to THE PUBLISHER'S receipt, atomically.

    A 36-launch sequence can be interrupted. Rewriting the receipt in place
    would leave a torn file and force the next attempt to guess (or to reach for
    "latest", which is never evidence), so the new receipt is written beside the
    old one and moved over it in one step.

    It never CREATES a receipt. A receipt is what the preflight gate published,
    and a state recorded into one this function invented would be evidence of a
    run nobody armed (Codex SEQ 1319 item D).
    """
    if not os.path.isfile(receipt_path):
        raise SystemExit(f"no receipt at {receipt_path}: a state can only be "
                         f"recorded against a run the gate published")
    try:
        receipt = _load(receipt_path)
    except Exception as exc:                          # noqa: BLE001 - by design
        raise SystemExit(f"receipt {receipt_path} is not readable JSON ({exc})")
    if not isinstance(receipt, dict) or not isinstance(receipt.get("states"),
                                                       list):
        raise SystemExit(f"receipt {receipt_path} carries no state inventory")
    if receipt.get("run_id") != run_id:
        raise SystemExit(f"receipt {receipt_path} belongs to run "
                         f"{receipt.get('run_id')!r}, not {run_id!r}")
    state_path = os.path.abspath(state_path)
    if state_path not in receipt["states"]:
        receipt["states"].append(state_path)
    tmp = receipt_path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, receipt_path)
    d = os.open(os.path.dirname(os.path.abspath(receipt_path)), os.O_RDONLY)
    try:
        os.fsync(d)
    finally:
        os.close(d)
    return receipt


def _jsonl(path):
    """Every line of a JSONL file, or None if ANY line is malformed.

    A transcript that cannot be read whole is not partial evidence: the lines it
    failed on are exactly where a tool call would hide.
    """
    out = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                return None
    return out


def _blocks(rec):
    c = ((rec.get("message") or {}).get("content"))
    return c if isinstance(c, list) else []


def _text_of(rec):
    c = ((rec.get("message") or {}).get("content"))
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") for b in (c or [])
                   if isinstance(b, dict) and b.get("type") == "text")


def _role(rec):
    return (rec.get("message") or {}).get("role")


def _rejection(pr, want_type, effort):
    """Why this `state=error` row is NOT a no-response service rejection. -> []

    Measured over every saved Workflow state on this machine: 768 progress rows
    carry `state="error"`. 763 of them name an agentId — a worker that started
    and then failed, which is not a rejection at all. Four more are launch
    configuration failures ("agent type not found") that carry no agentType and
    no `blocked` flag. EXACTLY ONE, this plan's own index-4 K1, is a rejection
    before any model response, and it is the only row of the 768 carrying
    `blocked: true`. So the flag is what separates the class; the absence of an
    agentId accepted five rows where only one was real (Codex SEQ 1212 case 1).

    Nothing here reads the classifier's message. It requires only that the
    runtime recorded SOME error signal — no meaning string, list or regex.
    The row's model already has an owner in the caller, so it is not re-checked.
    """
    bad = []
    if pr.get("blocked") is not True:
        bad.append("state is 'error' but the row is not flagged blocked — an "
                   "error is not by itself a no-response service rejection")
    err = pr.get("error")
    if not isinstance(err, str) or not err.strip():
        bad.append("a rejected lane must carry the runtime's own error signal")
    for k in ("agentId", "attempt", "toolCalls"):
        if k in pr:
            bad.append(f"a lane rejected before any model response cannot "
                       f"record {k}")
    if pr.get("agentType") != want_type:
        bad.append(f"rejected lane ran as agentType {pr.get('agentType')!r}, "
                   f"not the planned {want_type!r}")
    if pr.get("effort") not in (None, effort):
        bad.append(f"rejected lane records effort {pr.get('effort')!r}, not "
                   f"{effort!r}")
    return bad



#: The one display marker the official `promptPreview` appends when it
#: truncates. Removing it is NOT normalisation: nothing else is stripped.
PREVIEW_ELLIPSIS = "\u2026"


def _preview_ok(preview, pin):
    """Is this official preview real corroboration of the pinned bytes?

    A preview is a DISPLAY prefix. A plain one must be an exact prefix, as
    it always had to be. A truncated one carries exactly one U+2026, and
    only that single marker may be removed before the same exact test -
    no whitespace, no three dots, no fences, no length threshold. Missing,
    non-string, empty, ellipsis-only and wrong-prefix all stay refusals,
    and this never replaces the exact-bytes proof `_input` owns.
    """
    if not isinstance(preview, str) or not preview:
        return False
    if not preview.endswith(PREVIEW_ELLIPSIS):
        return pin.startswith(preview)
    shown = preview[:-len(PREVIEW_ELLIPSIS)]
    return bool(shown) and pin.startswith(shown)


def _next_is_input(recs, record):
    """Is the very next transcript record after this one a non-assistant
    input? Position only - no content is read."""
    for i, r in enumerate(recs):
        if r is record:
            nxt = recs[i + 1] if i + 1 < len(recs) else None
            return nxt is not None and (nxt.get("type") != "assistant"
                                        or _role(nxt) != "assistant")
    return False


class _LaterInput(str):
    """A later non-assistant input record - the ONE topology fault the
    runtime itself causes. It stays a fault; carrying its own type only
    lets the caller classify it without matching any content."""


def _input(recs, pin, expected_input=None):
    """THE INPUT TOPOLOGY: exactly one supplied prompt and no hidden input.

    Projecting the prompt's TEXT and counting user turns was not enough (Codex
    SEQ 1208): moving the prompt record after the first answer, splicing in a
    uniquely linked `attachment` record carrying extra context, or replacing the
    user content with `[the pinned text block, another block]` all kept the
    projected hash correct while changing what the worker was actually given.

    So the SHAPE is owned here, not inferred from a projection: record 0 is the
    only user record, every later record is an assistant answer record, and the
    prompt is the exact STRING the manifest pinned — a list is refused even when
    its projected text matches. Measured on the live population: A3's own two
    workers are the only 2 of the 1,408 ELIGIBLE one-user zero-tool transcripts
    that carry NO attachment record; the other 1,406 do, and that injected
    context is exactly what this refuses.
    """
    bad = []
    if not recs:
        return ["the transcript is empty"]
    first = recs[0]
    if first.get("type") != "user" or _role(first) != "user":
        bad.append(f"the first record is {first.get('type')!r}/"
                   f"{_role(first)!r}, not the supplied prompt")
    seen = False
    for i, r in enumerate(recs[1:], 1):
        if _expected_input(r, i, expected_input):
            seen = True
            continue
        if r.get("type") != "assistant" or _role(r) != "assistant":
            bad.append(_LaterInput(
                f"record {i} is {r.get('type')!r}/{_role(r)!r} — a "
                f"no-tool A3 worker receives one prompt and answers it, "
                f"so nothing else may appear between them"))
    if expected_input is not None and not seen:
        # PRESENCE AND POSITION ARE REQUIRED, not merely permitted. A plain
        # problem, never a _LaterInput: a missing declared input is not the
        # runtime adding something, so it may not be held as uncreditable.
        bad.append("the one input this lane declares is not at record %r"
                   % (expected_input.get("record_index")
                      if isinstance(expected_input, dict) else expected_input,))
    content = (first.get("message") or {}).get("content")
    if not isinstance(content, str):
        bad.append(f"the prompt content is {type(content).__name__}, not the "
                   f"single supplied string")
    elif hashlib.sha256(content.encode("utf-8")).hexdigest() != pin:
        bad.append("the prompt actually received is not the manifest's pinned "
                   "bytes")
    return bad


def _expected_input(rec, i, spec):
    """-> True only when record `i` is EXACTLY the ONE input this lane declares.

    `spec` is that lane's own expectation, frozen in the approved root and
    handed down by the caller: the record index the input must sit at, the
    outer record type it must carry, the field its payload sits in, and that
    payload's canonical sha256. THE ONE MATCH RULE, shared by both input
    owners.

    Nothing is read from the transcript to decide what is allowed; no payload,
    url, type name or keyword is written here; and an absent or malformed
    expectation admits nothing at all.
    """
    if not isinstance(spec, dict):
        return False
    index, kind = spec.get("record_index"), spec.get("record_type")
    field, want = spec.get("payload_field"), spec.get("payload_sha256")
    if isinstance(index, bool) or not isinstance(index, int) or index < 1:
        return False                       # record 0 is the supplied prompt
    if not isinstance(kind, str) or not kind:
        return False
    if not isinstance(field, str) or not field:
        return False
    if not isinstance(want, str) or len(want) != 64:
        return False
    if i != index or not isinstance(rec, dict):
        return False
    if rec.get("type") != kind or rec.get("message") is not None:
        return False
    try:
        canon = json.dumps(rec.get(field), sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return False
    return hashlib.sha256(canon.encode("utf-8")).hexdigest() == want


def _pairs(asst):
    """Assistant records grouped into contiguous `(message.id, requestId)` runs.

    Each group is `[(key), record, record, ...]` in transcript order.
    """
    out = []
    for r in asst:
        key = ((r.get("message") or {}).get("id"), r.get("requestId"))
        if not out or out[-1][0] != key:
            out.append([key, r])
        else:
            out[-1].append(r)
    return out


def _chain(recs, asst):
    """Validate ONE ordered continuation chain. -> (problems, final, complete).

    `final`    the LAST response group's terminal text — exactly what `agent()`
               returned, and what the saved state row must equal byte-for-byte.
    `complete` the whole answer: the exact, zero-delimiter concatenation of every
               proved group's terminal text, in transcript order.

    THE TWO ARE DIFFERENT FACTS AND ARE KEPT SEPARATE (Codex SEQ 1216, which
    reverses the earlier final-segment-only ruling). A response ended at
    `max_tokens` and continued automatically under the same proved worker is ONE
    ordered answer, not two; `agent()` hands back only the last group, so the
    earlier groups' bytes are real answer bytes that the transport drops.
    Measured across this run's ten completed responses: seven have earlier
    text-bearing groups and lose 142,785 of 559,719 characters.

    This is transport order, never content: nothing is inserted between groups,
    no fence is stripped, no fragment is parsed, no JSON is repaired, and
    thinking blocks never contribute. `raw_transport` remains the sole exact-JSON,
    V2-door, invalid-bucket and retry owner.

    A long answer legitimately spans several SERVICE requests: the runtime ends
    one at `max_tokens` and continues it under the SAME scheduled agent, so the
    retired "exactly one identity pair" rule rejected lawful workers (Codex SEQ
    1207). Measured over the complete live population: of the 1,408 ELIGIBLE
    one-user zero-tool transcripts, 1,406 are a single pair and the two
    exceptions are this run's own workers; all 1,408 have unique record UUIDs,
    an exact parent chain and contiguous non-recurring pairs.

    This validates the chain as an ORDER and nothing else. It never parses JSON,
    strips a fence, repairs content, or judges completeness from content — the
    concatenation is dictated by transport order alone and is never chosen
    because the result happens to parse.
    """
    bad = []
    # 1. the record chain itself: unique identity, and each record links to the
    #    one before it.
    seen = set()
    for i, r in enumerate(recs):
        u = r.get("uuid")
        if not u:
            bad.append(f"transcript record {i} carries no uuid")
        elif u in seen:
            bad.append(f"transcript record {i} repeats uuid {u}")
        else:
            seen.add(u)
        want = recs[i - 1].get("uuid") if i else None
        if r.get("parentUuid") != want:
            bad.append(f"transcript record {i} does not link to the record "
                       f"before it")
    groups = _pairs(asst)
    # A RECURRING response identity is NOT checked here: the global
    # (message id, request id) owner in `audit` already rejects any reuse,
    # within a worker or across the run. One owner per fact.
    # 2. within a pair only its LAST record ends; 3. non-final pairs end at
    #    max_tokens and the final pair ends at end_turn.
    # ONE contiguous response identity is a completed answer, not a
    # continuation: `max_tokens` is what a continuation means, so a single
    # response may carry markers on more than its last record as long as EVERY
    # present marker is `end_turn`. The one-terminal-text rule below is
    # untouched, and the multi-response rule stays strict (Codex SEQ 1352 item
    # 1). Nothing here reads content.
    single = len(groups) == 1
    for n, g in enumerate(groups):
        members = g[1:]
        last = members[-1]
        for r in members[:-1]:
            if not single and (r.get("message") or {}).get("stop_reason") is not None:
                bad.append(f"a non-terminal record of response {n + 1} carries "
                           f"a stop reason")
            if _text_of(r):
                bad.append(f"a non-terminal record of response {n + 1} carries "
                           f"text")
        if single:
            wrong = [m for m in ((r.get("message") or {}).get("stop_reason")
                                 for r in members)
                     if m is not None and m != "end_turn"]
            if wrong:
                bad.append(f"the single response carries {wrong[0]!r}, not "
                           f"'end_turn'")
            continue
        got = (last.get("message") or {}).get("stop_reason")
        want = "end_turn" if n == len(groups) - 1 else "max_tokens"
        if got != want:
            why = (f"response {n + 1} of {len(groups)} ends with "
                   f"{got!r}, not {want!r}")
            # STRUCTURAL, never content: a distinct response that ENDS
            # (rather than running out of tokens) immediately before a
            # later input record is the runtime resetting the response -
            # the same added-input class `_input` marks, not a separate
            # fault. A continuation with no added input is untouched.
            bad.append(_LaterInput(why)
                       if got == "end_turn" and _next_is_input(recs, last)
                       else why)
    # 4. nothing follows the terminal answer, and that answer is one text.
    final = groups[-1][1:]
    if recs and recs[-1] is not final[-1]:
        bad.append("a record follows the terminal answer")
    texts = [r for r in final if _text_of(r)]
    if len(texts) != 1:
        bad.append(f"the final response carries {len(texts)} text-bearing "
                   f"records, not exactly one")
        return bad, None, None
    # THAT the one text is the terminal record is not re-checked here: the
    # non-terminal-text rule above already refuses text on any earlier record,
    # so exactly-one-text plus that rule proves it. The SAME rule is what makes
    # the concatenation below well-defined: all answer text lives on terminals,
    # so one group contributes exactly one piece (an empty one when that group
    # carried only thinking, which is why a thinking-only continuation comes
    # back byte-identical).
    return bad, _text_of(final[-1]), "".join(_text_of(g[-1]) for g in groups)


def _official_location(state_path):
    """(session_dir, session_id) if this state sits where the runtime puts one.

    Canonical shape: <PROJECTS_ROOT>/<project>/<session>/workflows/<runId>.json
    """
    real = os.path.realpath(state_path)
    root = os.path.realpath(PROJECTS_ROOT)
    if os.path.commonpath([real, root]) != root:
        return None, None
    rel = os.path.relpath(real, root).split(os.sep)
    if len(rel) != 4 or rel[2] != "workflows":
        return None, None
    return os.path.join(root, rel[0], rel[1]), rel[1]


def _armed(committed, receipt):
    """The bytes the coordinator actually launches: the committed slice with
    its receipt substituted. Binding a state to THIS is stronger than binding it
    to the committed file, because it also proves which subset was authorised.
    """
    import raw_transport as _rt
    if _rt.A1_RECEIPT_LINE not in committed:
        return None
    return committed.replace(
        _rt.A1_RECEIPT_LINE,
        "const RECEIPT = %s\n" % json.dumps(receipt, sort_keys=True), 1)


def audit(receipt_path, manifest_path=DEFAULT_MANIFEST,
          bundle_path=DEFAULT_BUNDLE):
    """Prove every A1 worker from the OFFICIAL state and its CHILD TRANSCRIPT.

    Retargeted from the (source_id, arm) plan to A1's (packet_id, lane_id) one.
    The transcript evidence core below — `_official_location`, `_jsonl`,
    `_input`, `_pairs`, `_chain`, `_rejection` — is unchanged: it is what proves
    the exact first user prompt, every assistant model and effort, the ordered
    answer, and zero tool use. Nothing is inferred from run totals, and a result
    row is corroboration, never the proof.

    Returns `{problems, outcomes, answers}` where `outcomes` are the STRUCTURED
    `(key, outcome, why)` tuples the ledger and retry selection consume.
    """
    import raw_transport as RT
    problems, outcomes, answers, raw_rows = [], [], {}, []

    def _out(key, outcome, why=""):
        """EXACTLY ONE terminal outcome per scheduled key: the first one
        stands. Order used to decide it silently (Codex SEQ 1350 item 2),
        which is not a decision anyone can read."""
        if any(o[0] == key for o in outcomes):
            return
        outcomes.append((key, outcome, why))

    if not isinstance(receipt_path, str) or not os.path.isfile(receipt_path):
        return {"problems": ["receipt %r does not exist" % receipt_path],
                "outcomes": [], "answers": {}, "raw_rows": []}
    if os.path.basename(receipt_path) != RECEIPT_NAME:
        problems.append("the receipt must be %s inside its run directory"
                        % RECEIPT_NAME)
    out_dir = os.path.dirname(os.path.abspath(receipt_path))
    try:
        receipt = _load(receipt_path) or {}
    except Exception as exc:                          # noqa: BLE001 - by design
        return {"problems": ["receipt is not readable JSON (%s)" % exc],
                "outcomes": [], "answers": {}, "raw_rows": []}
    # THE RUN CONTRACT HAS ONE OWNER, and it is `raw_transport`. This audit
    # proves RUNTIME EVIDENCE; it no longer restates receipt rules of its own,
    # and it no longer skips them either (Codex SEQ 1318 item A).
    contract = RT.a1_run_contract_problems(receipt, out_dir)
    problems.extend(contract)
    if contract:
        return {"problems": problems, "outcomes": outcomes,
                "answers": answers,
                "raw_rows": RT.a1_readable_rows(receipt.get("states")
                                                if isinstance(receipt, dict)
                                                else [])}
    allowed = [tuple(c) for c in receipt.get("allowed") or []]
    per_source = receipt.get("receipts") or {}
    attempt = receipt.get("attempt")
    states = receipt.get("states")
    # B (Codex SEQ 1405): THE RUN'S OWN PLAN COMES FIRST. A run that persisted
    # a private plan under <run>/plan/ is audited against THAT plan's exact
    # manifest and bundle; a run without one keeps the current A1 files. The
    # supported path still takes only the receipt/run identity - no
    # caller-selected plan, registry, dynamic import or second auditor.
    _run_plan = RT.a1_plan_for_run(out_dir)
    if _run_plan is not RT.a1_plan() and _run_plan.get("manifest_path"):
        man = _run_plan
        bundle, _bad = _load_pinned(_run_plan.get("bundle_path"),
                                    _run_plan.get("bundle_sha256"))
        if _bad:
            return {"problems": [_bad], "outcomes": [], "answers": {},
                    "raw_rows": []}
    else:
        man = _load(manifest_path)
        bundle = _load(bundle_path)
    # THE DECLARATION COMES FROM THE PLAN THIS OWNER ALREADY RESOLVED,
    # never from a caller argument and never from the receipt: the
    # receipt is the thing being audited, so it may not choose its own
    # allowance (Codex SEQ 1953 item 1). A plan that declares none
    # keeps the old, stricter rule.
    expected_input = man.get("expected_input") if isinstance(man, dict) \
        else None
    # AND THE PLAN IS STILL THIS RUN'S OWN DOCUMENT, so the declaration it
    # carries is checked against the artifact the RUN SERVES before it is used
    # (Codex SEQ 1955 item 2). One owner answers that for every carrier; a
    # plan that carries neither field is legacy and passes unchanged.
    _decl_bad = RT \
        .approved_lane_input_problems(
            expected_input,
            man.get("expected_input_source") if isinstance(man, dict) else None)
    if _decl_bad:
        return {"problems": _decl_bad, "outcomes": [], "answers": {},
                "raw_rows": []}
    for label, obj, kind in (("manifest", man, dict), ("bundle", bundle, dict)):
        if not isinstance(obj, kind):
            return {"problems": ["%s is %s, not an object"
                                 % (label, type(obj).__name__)],
                    "outcomes": [], "answers": {}, "raw_rows": []}
    # THE PINS ARE THE RUN-RESOLVED PLAN'S OWN ROLE AND CONTRACT ERA. Rendering
    # the default door pinned bytes no private-plan worker was ever served;
    # every earlier run happened to share the default prompts, so the first
    # run whose bytes differed audited all of its completed calls as integrity
    # refusals (Codex SEQ 1482 item 2). A plan that carries neither field is
    # the K-fields path and renders exactly as before. No caller may supply
    # the pins, and no door registry or path chooses them: `man` is the one
    # plan this run resolved above.
    #
    # THE PROMPTS COME FROM A BUILDER THAT IMPORTS THE SEMANTIC READER. If
    # that reader has drifted so badly it will not import, the paid rows
    # must still be harvested and returned — so this is a structured
    # problem, never an exception (Codex SEQ 1317 item 7). A role the contract
    # does not declare EXITS the prompt owner; that too is a problem here,
    # never a crash out of a closeout that has already preserved paid bytes.
    try:
        import build_launch_manifest as blm
        prompts = blm.one_item_prompts(man.get("prompt_role"),
                                       man.get("contract_suffix"),
                                       blm.plan_inventory(man))
    except (Exception, SystemExit) as exc:            # noqa: BLE001 - by design
        problems.append("the rendered prompts are unavailable (%s: %s); "
                        "identity cannot be proved"
                        % (type(exc).__name__, exc))
        prompts = {}
    scheduled = {(r["packet_id"], r["lane_id"]): r
                 for r in RT.a1_schedule(man, attempt if attempt in (1, 2) else 1)}
    for call in allowed:
        if call not in scheduled:
            problems.append("the receipt allows %s, which the plan does not "
                            "schedule" % (call,))
    lanes = {lid: dict(scheduled[(pid, lid)]) for (pid, lid) in scheduled}
    base = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))

    # THE ARMED LAUNCHER BYTES ARE THE IDENTITY. Built once, keyed by hash, so a
    # state can only be matched by what the runtime really ran — and only to a
    # launcher armed with THIS run's receipt.
    by_bytes, slices = {}, {r["source_id"]: r for r in bundle.get("slices") or []}
    for sid, row in sorted(slices.items()):
        live = os.path.join(base, row["launcher"])
        if not os.path.isfile(live):
            problems.append("%s: reviewed launcher is missing" % sid)
            continue
        with io.open(live, encoding="utf-8") as fh:
            committed = fh.read()
        if hashlib.sha256(committed.encode("utf-8")).hexdigest() != row["sha256"]:
            problems.append("%s: launcher bytes differ from the bundle" % sid)
        rec = per_source.get(sid)
        if rec is None:
            continue                     # this source was not part of this run
        armed = _armed(committed, rec)
        if armed is None:
            problems.append("%s: the reviewed launcher carries no receipt slot"
                            % sid)
            continue
        digest = hashlib.sha256(armed.encode("utf-8")).hexdigest()
        if digest in by_bytes:
            problems.append("%s: two sources share armed launcher bytes" % sid)
        by_bytes[digest] = sid
    if len(by_bytes) != len(per_source):
        problems.append("%d source receipts produced %d distinct armed "
                        "launchers" % (len(per_source), len(by_bytes)))

    seen_states, seen_runs, seen_agents = set(), {}, {}
    ids = {}                       # (message.id, requestId) -> its one owner
    answered, refused = {}, {}
    #: completed answers that must NEVER be credited - kept apart from
    #: `answered` so no credited path can ever read them
    uncreditable = {}

    for sp in states:
        tag = os.path.basename(str(sp))
        ap = os.path.abspath(str(sp))
        if ap in seen_states:
            problems.append("%s: the same state file is listed twice" % tag)
            continue
        seen_states.add(ap)
        if not os.path.isfile(ap):
            problems.append("%s: official state file does not exist" % tag)
            continue
        session_dir, _sess = _official_location(ap)
        if session_dir is None:
            problems.append("%s: not an official state under %s"
                            % (tag, PROJECTS_ROOT))
            continue
        try:
            st = _load(ap)
        except Exception as exc:                      # noqa: BLE001 - by design
            problems.append("%s: state is not readable JSON (%s)" % (tag, exc))
            continue
        if not isinstance(st, dict):
            problems.append("%s: official state is %s, not an object"
                            % (tag, type(st).__name__))
            continue
        # PAID ROWS ARE HARVESTED BEFORE ANY IDENTITY CHECK. A bad-script state
        # still held 14 result rows and the audit returned none, because every
        # identity `continue` above this point skipped the harvest and the
        # finalizer then saved nothing (Codex SEQ 1316 item 5).
        result = st.get("result")
        state_rows = result.get("results") if isinstance(result, dict) else None
        if result is not None and not isinstance(result, dict):
            problems.append("%s: state.result is %s, not an object"
                            % (tag, type(result).__name__))
        if state_rows is not None and not isinstance(state_rows, list):
            problems.append("%s: state.result.results is %s, not a list"
                            % (tag, type(state_rows).__name__))
            state_rows = None
        for row in state_rows or []:
            raw_rows.append(row)

        rid = st.get("runId")
        if not rid:
            problems.append("%s: state names no runId" % tag)
            continue
        if rid in seen_runs:
            problems.append("%s: runId %s already used" % (tag, rid))
            continue
        seen_runs[rid] = ap
        if os.path.basename(ap) != "%s.json" % rid:
            problems.append("%s: filename does not match runId %s" % (tag, rid))
        if st.get("status") != "completed":
            problems.append("%s: status is %r, not completed"
                            % (tag, st.get("status")))

        script = st.get("script")
        sid = by_bytes.get(hashlib.sha256(
            (script if isinstance(script, str) else "").encode("utf-8")
        ).hexdigest())
        if sid is None:
            problems.append("%s: the script this run persisted is not any "
                            "reviewed launcher armed with this run's receipt"
                            % tag)
            continue
        # THE SCRIPT PATH IS AN IDENTITY, NOT A LABEL. A basename that merely
        # contains the source id proved nothing, and an absent or nonexistent
        # path proved less (Codex SEQ 1314 item 10).
        spath_claim = st.get("scriptPath")
        if not isinstance(spath_claim, str) or not spath_claim:
            problems.append("%s: the state names no scriptPath" % tag)
        elif not os.path.isfile(spath_claim):
            problems.append("%s: scriptPath %r does not exist"
                            % (tag, spath_claim))
        elif os.path.abspath(spath_claim) != os.path.abspath(
                (per_source.get(sid) or {}).get("launcher_path") or ""):
            # a same-byte copy at another path is a different run's evidence
            problems.append("%s: scriptPath %r is not the armed launcher this "
                            "receipt published" % (tag, spath_claim))
        else:
            with io.open(spath_claim, encoding="utf-8") as fh:
                on_disk = fh.read()
            if on_disk != script:
                problems.append("%s: the file at scriptPath is not the script "
                                "this run persisted" % tag)

        # --- the args the RUNTIME saved, compared BYTE FOR BYTE -----------
        # Reducing them to a call set and sorting let a reversed saved-args list
        # audit clean (Codex SEQ 1317 item 1). The canonical projection is the
        # single answer, and the state must equal it exactly.
        saved = st.get("args")
        want_args = RT.a1_expected_args(receipt, sid, man)
        if saved != want_args:
            problems.append("%s: the saved args are not the canonical "
                            "projection for %s" % (tag, sid))
        inv = [row for row in (receipt.get("invocations") or [])
               if isinstance(row, dict) and row.get("source_id") == sid]
        if len(inv) != 1:
            problems.append("%s: the receipt carries %d invocations for %s"
                            % (tag, len(inv), sid))
        elif inv[0].get("args") != saved:
            problems.append("%s: the state's args are not the invocation the "
                            "receipt published" % tag)
        elif inv[0].get("scriptPath") != spath_claim:
            problems.append("%s: the state ran a path the receipt did not "
                            "publish" % tag)

        # --- the OFFICIAL per-agent rows -----------------------------------
        script_ok = isinstance(st.get("script"), str)
        if not script_ok:
            problems.append("%s: the state's script is %s, not text"
                            % (tag, type(st.get("script")).__name__))
        progress = st.get("workflowProgress")
        if not isinstance(progress, list) or not progress:
            problems.append("%s: no official per-agent rows - zero tool use "
                            "cannot be proved from run totals" % tag)
            continue
        for r in progress:
            if not isinstance(r, dict):
                problems.append("%s: a workflowProgress row is %s, not an "
                                "object" % (tag, type(r).__name__))
        agent_rows = [r for r in progress
                      if isinstance(r, dict) and r.get("type") == "workflow_agent"]
        if not agent_rows:
            problems.append("%s: the state records no agent rows" % tag)
            continue
        rid_dir = os.path.join(session_dir, "subagents", "workflows", rid)

        for pr in agent_rows:
            label = pr.get("label")
            lane = lanes.get(label)
            if lane is None:
                problems.append("%s: agent %r names no planned lane"
                                % (tag, label))
                continue
            key = (lane["packet_id"], label)
            if key not in allowed:
                problems.append("%s: %s is not an allowed call" % (tag, key))
                _out(key, "unexpected", "not in the receipt")
                continue
            if key in answered or key in refused:
                problems.append("%s: %s appears in two official rows"
                                % (tag, key))
                _out(key, "duplicate", "two official agent rows")
                continue
            aid = pr.get("agentId")
            if pr.get("state") == "error":
                why = _rejection(pr, lane["agentType"], lane["effort"])
                if why:
                    problems.extend("%s: %s: %s" % (tag, key, c) for c in why)
                    _out(key, "spawned_without_answer", "; ".join(why))
                else:
                    refused[key] = pr.get("error")
                    _out(key, "pre_agent_refusal", str(pr.get("error")))
                continue
            if pr.get("state") != "done":
                problems.append("%s: %s state is %r" % (tag, key, pr.get("state")))
                _out(key, "spawned_without_answer", "state %r" % pr.get("state"))
                continue
            if not aid:
                problems.append("%s: %s records no agentId" % (tag, key))
                _out(key, "integrity_refusal", "no agentId")
                continue
            if aid in seen_agents:
                problems.append("%s: agentId %s is reused by %s and %s"
                                % (tag, aid, seen_agents[aid], key))
                _out(key, "integrity_refusal", "reused agentId")
                continue
            seen_agents[aid] = key
            # A RESUMED, ALREADY-COMPLETED AGENT. The runtime omits three
            # progress fields and reports the alias; its agent meta carries the
            # identity instead. Only that exact shape is excused, and only from
            # these three checks - every transcript check below still runs.
            cached = _resumed_cached_row(pr, rid_dir, lane)
            if not cached and man.get("runtime_model_id") is not None and \
                    pr.get("model") != man["runtime_model_id"]:
                problems.append("%s: %s official row records model %r, frozen "
                                "%r" % (tag, key, pr.get("model"),
                                        man["runtime_model_id"]))
            if not cached and pr.get("agentType") != lane["agentType"]:
                problems.append("%s: %s agentType %r, planned %r"
                                % (tag, key, pr.get("agentType"),
                                   lane["agentType"]))
            if not cached and (pr.get("toolCalls") != 0
                               or "lastToolName" in pr):
                problems.append("%s: %s made %r tool call(s) (%r)"
                                % (tag, key, pr.get("toolCalls"),
                                   pr.get("lastToolName")))
                _out(key, "tool_violation", "toolCalls=%r lastToolName=%r"
                     % (pr.get("toolCalls"), pr.get("lastToolName")))
                continue

            # --- THE CHILD TRANSCRIPT: the only place effort is provable ----
            tpath = os.path.join(rid_dir, "agent-%s.jsonl" % aid)
            if not os.path.isfile(tpath):
                problems.append("%s: %s has no child transcript at %s"
                                % (tag, key, tpath))
                _out(key, "integrity_refusal", "no transcript")
                continue
            recs = _jsonl(tpath)
            if recs is not None and any(not isinstance(r, dict) for r in recs):
                problems.append("%s: %s transcript holds a non-object record"
                                % (tag, key))
                _out(key, "integrity_refusal", "malformed transcript record")
                continue
            if not recs:
                problems.append("%s: %s transcript is empty or unreadable"
                                % (tag, key))
                _out(key, "integrity_refusal", "empty transcript")
                continue
            # EVERY record must belong to THIS agent and THIS session
            for i, r in enumerate(recs):
                got_a = r.get("agentId")
                if not got_a or got_a != aid:
                    problems.append("%s: %s transcript record %d carries agent "
                                    "%r, not the proved worker %r"
                                    % (tag, key, i, got_a, aid))
                got_s = r.get("sessionId")
                if not got_s or got_s != _sess:
                    problems.append("%s: %s transcript record %d carries "
                                    "session %r, not %r"
                                    % (tag, key, i, got_s, _sess))
            pin = prompts.get(lane["packet_id"])
            if pin is None:
                problems.append("%s: %s has no rendered prompt" % (tag, key))
                _out(key, "integrity_refusal", "no pinned prompt")
                continue
            # `_input` owns the topology and takes the pinned HASH
            gaps = list(_input(recs, hashlib.sha256(
                pin.encode("utf-8")).hexdigest(), expected_input))
            asst = [r for r in recs if _role(r) == "assistant"]
            # EFFORT IS PROVABLE, and it is proved HERE. The official progress
            # row carries no `effort` at all (0 of 291 live rows), but the child
            # transcript records it per assistant record - so the transcript is
            # where it is required, not merely tolerated (Codex SEQ 1313 item 7).
            efforts = [r.get("effort") for r in asst]
            if not asst:
                gaps.append("the transcript carries no assistant record")
            elif any(e is None for e in efforts):
                gaps.append("an assistant record records no effort, so the "
                            "planned %r cannot be proved" % lane["effort"])
            for r in asst:
                msg = r.get("message") or {}
                if msg.get("model") != lane.get("runtime_model_id") and \
                        lane.get("runtime_model_id") is not None:
                    gaps.append("an assistant record ran on %r, not the frozen "
                                "%r" % (msg.get("model"),
                                        lane.get("runtime_model_id")))
                if r.get("effort") is not None and r["effort"] != lane["effort"]:
                    gaps.append("an assistant record records effort %r, not %r"
                                % (r["effort"], lane["effort"]))
            # the preview is CORROBORATION: it must still be a real prefix of
            # the bytes the transcript proves were served
            preview = pr.get("promptPreview")
            if not _preview_ok(preview, pin):
                gaps.append("the official prompt preview %r is not a prefix of "
                            "the pinned bytes" % (preview,))
            used = sorted({b.get("name") for r in recs for b in _blocks(r)
                           if b.get("type") == "tool_use"})
            if used:
                gaps.append("the transcript records tool use: %s" % used)
                _out(key, "tool_violation", "transcript tool_use %s" % used)
            # RESPONSE IDENTITY: every group must name one, and no two workers
            # may share one — a shared (message.id, requestId) means one
            # response is being counted as two workers' answers.
            mine = []
            for g in _pairs(asst):
                mid, req = g[0]
                if not mid or not req:
                    gaps.append("a response group carries no (message.id, "
                                "requestId) identity")
                    continue
                if (mid, req) in mine:
                    # A -> B -> A: `_pairs` groups CONTIGUOUS runs, so the same
                    # identity in two separate groups is one response pretending
                    # to be two, or two pretending to be one
                    gaps.append("response identity %s recurs non-contiguously"
                                % ((mid, req),))
                mine.append((mid, req))
                owner = ids.get((mid, req))
                if owner is not None and owner != key:
                    gaps.append("response identity %s is shared with %s"
                                % ((mid, req), owner))
                ids[(mid, req)] = key
            if not asst:
                gaps.append("the transcript carries no assistant record")
                problems.extend("%s: %s: %s" % (tag, key, g) for g in gaps)
                _out(key, "integrity_refusal", "; ".join(gaps[:2]))
                continue
            chain, final_text, complete = _chain(recs, asst)
            gaps.extend(chain)
            if gaps:
                # every fault is the runtime having added input, and nothing
                # else - identity, model, effort, tools and the response
                # chain all passed - so this is an invalid response to retry
                # once, not an integrity fault. Its outcome is withheld until
                # its result row is validated below, so the key receives one
                # terminal outcome and never a later `unexpected`.
                #
                # Its faults are held with it rather than appended to
                # `problems`: an outcome that NAMES its own cause is not an
                # unexplained audit failure, and leaving it in `problems`
                # made one runtime reset refuse the whole run (every other
                # key became integrity_refusal and no retry could derive).
                # If the result row does not then match, the faults are
                # reported in full below and the key refuses.
                if all(isinstance(g, _LaterInput) for g in gaps) \
                        and final_text is not None:
                    uncreditable[key] = {"final": final_text,
                                         "complete": complete,
                                         "why": "; ".join(gaps[:2]),
                                         "held": ["%s: %s: %s" % (tag, key, g)
                                                  for g in gaps]}
                else:
                    problems.extend("%s: %s: %s" % (tag, key, g)
                                    for g in gaps)
                    _out(key, "integrity_refusal", "; ".join(gaps[:2]))
                continue
            answered[key] = {"final": final_text, "complete": complete}

        # --- EXACTLY ONE mandatory result row per completed agent ----------
        rows = state_rows
        if rows is None:
            problems.append("%s: the state carries no result rows" % tag)
            continue
        by_key = {}
        for row in rows:
            if not isinstance(row, dict):
                problems.append("%s: malformed result row" % tag); continue
            k = (row.get("packet_id"), row.get("lane_id"))
            if k in by_key:
                problems.append("%s: %s has two result rows" % (tag, k))
            by_key[k] = row
        # a key with a PROVED official agent - credited or not. An
        # uncreditable one still has an agent, so it can never be the
        # "result row with no proved agent" that `unexpected` means.
        mine = {k for k in list(answered) + list(uncreditable)
                if k[0].split("#")[0] == sid}
        for k in sorted(mine - set(by_key)):
            problems.extend(uncreditable.get(k, {}).get("held", []))
            problems.append("%s: %s completed but returned no result row"
                            % (tag, k))
            _out(k, "integrity_refusal", "completed with no result row")
        for k in sorted(set(by_key) - mine):
            if k in refused:
                continue
            problems.append("%s: result row %s has no completed agent" % (tag, k))
            _out(k, "unexpected", "result row with no proved agent")
        for k in sorted(mine & set(by_key)):
            row, want = by_key[k], scheduled[k]
            bad = RT.a1_identity_problems(row, want)
            if bad:
                problems.extend(uncreditable.get(k, {}).get("held", []))
                problems.extend("%s: %s: %s" % (tag, k, c) for c in bad)
                _out(k, "integrity_refusal", "; ".join(bad))
                continue
            proved = answered.get(k) or uncreditable[k]
            if row.get("text") != proved["final"]:
                problems.extend(uncreditable.get(k, {}).get("held", []))
                problems.append("%s: %s result text is not the transcript's "
                                "completed answer" % (tag, k))
                _out(k, "integrity_refusal", "result text != transcript answer")
                continue
            if k in uncreditable:
                # the row is exactly this agent's completed answer, and the
                # runtime added input to get it: ONE terminal outcome, no
                # credit, and the retry owner may offer exactly one attempt
                _out(k, RT.A1_INVALID_RESPONSE, uncreditable[k]["why"])
                continue
            answers[k] = proved["complete"]
            _out(k, "served", "")

    for call in sorted(set(allowed) - set(answers) - set(refused)):
        if not any(o[0] == call for o in outcomes):
            problems.append("no proved outcome for allowed call %s" % (call,))
            _out(call, "spawned_without_answer", "no official row")
    return {"problems": problems, "outcomes": outcomes, "answers": answers,
            "raw_rows": raw_rows}



# --------------------------------------------------- the G1 adapter (1422) --
#: the runtime's own agent progress-row type
G1_AGENT_ROW = "workflow_agent"


def _g1_shape_problems(recs, agent_id, expected_input=None):
    """THE ONE SHAPE CHECK, run before anything reads a nested field.

    `_role`, `_blocks`, `_text_of`, `_input`, `_pairs` and `_chain` all reach
    into `message` and into the identity fields. A malformed nested shape must
    be a NAMED problem here, not an exception thrown from inside one of them:
    an abandoned traceback loses the paid evidence it was meant to judge.
    """
    bad = []
    for i, rec in enumerate(recs):
        if not isinstance(rec, dict):
            bad.append("agent %s's record %d is %s, not an object"
                       % (agent_id, i, type(rec).__name__))
            continue
        message = rec.get("message")
        if not isinstance(message, dict):
            # THE ONE INPUT THIS LANE DECLARES, at the declared index and only
            # there. Every other message-less record is the problem it was.
            if not _expected_input(rec, i, expected_input):
                bad.append("agent %s's record %d carries a %s message, not an "
                           "object" % (agent_id, i, type(message).__name__))
        uuid = rec.get("uuid")
        if not isinstance(uuid, str) or not uuid:
            bad.append("agent %s's record %d has uuid %r, not a nonempty "
                       "string" % (agent_id, i, uuid))
        parent = rec.get("parentUuid")
        if parent is not None and not isinstance(parent, str):
            bad.append("agent %s's record %d has parentUuid %r, not a string "
                       "or null" % (agent_id, i, parent))
        if isinstance(message, dict) and message.get("role") == "assistant":
            for field, value in (("message.id", message.get("id")),
                                 ("requestId", rec.get("requestId"))):
                if not isinstance(value, str) or not value:
                    bad.append("agent %s's record %d has %s %r, not a nonempty "
                               "string" % (agent_id, i, field, value))
    return bad


def _g1_transcript(session_dir, session_id, rid, agent_id, prompt_sha, model,
                   effort, response_ids, expected_input=None):
    """One G1 agent's child transcript. -> (problems, final, complete).

    The A1 rules, reused whole: the file must read as JSONL, the input topology
    must be exactly one supplied prompt with no hidden input, every assistant
    record must carry the planned model and effort, no record may carry a tool
    use, and the response chain must yield ONE ordered complete final answer.
    """
    path = os.path.join(session_dir, "subagents", "workflows", rid,
                        "agent-%s.jsonl" % agent_id)
    if not os.path.isfile(path):
        return ["agent %s has no child transcript at %s" % (agent_id, path)], \
            None, False
    recs = _jsonl(path)
    if recs is None:
        return ["agent %s's transcript does not read whole" % agent_id], \
            None, False
    # EVERY nested shape is checked before anything reads a field off it: a
    # malformed line is a refusal, never a traceback.
    shape = _g1_shape_problems(recs, agent_id, expected_input)
    if shape:
        return shape, None, False
    # `_input` owns the EXACT-BYTES proof and takes the pinned digest
    problems = list(_input(recs, prompt_sha, expected_input) or [])
    for i, rec in enumerate(recs):
        # MISSING IS NOT EQUALITY. A record that names no agent or no session
        # proves nothing about whose work it is.
        if rec.get("agentId") != agent_id:
            problems.append("agent %s's record %d names agent %r"
                            % (agent_id, i, rec.get("agentId")))
        if rec.get("sessionId") != session_id:
            problems.append("agent %s's record %d names session %r, not %r"
                            % (agent_id, i, rec.get("sessionId"), session_id))
        for block in _blocks(rec):
            if isinstance(block, dict) and \
                    block.get("type") in ("tool_use", "tool_result"):
                problems.append("agent %s used a tool; this lane allows none"
                                % agent_id)
    asst = [r for r in recs if _role(r) == "assistant"]
    if not asst:
        # nothing downstream can be validated without an answer record, and
        # `_chain` is not asked to reason about an empty transcript
        problems.append("agent %s recorded no assistant answer" % agent_id)
        return problems, None, False
    for rec in asst:
        got = (rec.get("message") or {}).get("model")
        if got != model:
            problems.append("agent %s answered with model %r, not %r"
                            % (agent_id, got, model))
        if rec.get("effort") != effort:
            problems.append("agent %s answered at effort %r, not %r"
                            % (agent_id, rec.get("effort"), effort))
    # THE RESPONSE IDENTITY, not the record uuid: every completed group must
    # carry a nonempty (message.id, requestId), and no pair may recur inside
    # this worker or across the segment's other workers.
    for group in _pairs(asst):
        key = group[0]
        if not key[0] or not key[1]:
            problems.append("agent %s has a response group with no "
                            "(message.id, requestId)" % agent_id)
            continue
        if key in response_ids:
            problems.append("agent %s reuses response identity %r, already "
                            "seen for %s" % (agent_id, key, response_ids[key]))
        else:
            response_ids[key] = agent_id
    chain_problems, final, complete = _chain(recs, asst)
    problems += list(chain_problems or [])
    if not complete:
        problems.append("agent %s has no ONE complete ordered final answer"
                        % agent_id)
    return problems, final, complete


def g1_state_audit(state_path, expect):
    """Audit what a G1 invocation ACTUALLY ran. -> (problems, whole).

    `whole` is {lane_id: the exact WHOLE answer} that `_chain` already proves:
    every response group's terminal text, in transcript order. This function
    computed it and threw it away, so everything downstream parsed only the
    LAST returned piece - judging a multi-group answer by its tail alone, in
    both directions (Codex SEQ 1869 item 1). Nothing is parsed, repaired or
    separated here; these are bytes the chain owner has already verified.

    `expect` is derived from the approved root and receipt by the G1 owner and
    is never read out of the state being audited. Everything below must hold
    together; any single failure refuses the whole segment.
    """
    session_dir, session_id = _official_location(state_path)
    if session_dir is None:
        return ["%s is not where the runtime writes an official state"
                % state_path], {}
    if not os.path.isfile(state_path):
        return ["the official state at %s is gone" % state_path], {}
    try:
        st = _load(state_path)
    except Exception as exc:                          # noqa: BLE001 - by design
        return ["the official state at %s is not readable: %s"
                % (state_path, exc)], {}
    if not isinstance(st, dict) or not st:
        return ["the official state at %s carries nothing" % state_path], {}

    problems = []
    rid = os.path.basename(state_path)[:-len(".json")]
    if st.get("runId") != rid:
        problems.append("the state names run %r, its file names %r"
                        % (st.get("runId"), rid))
    if st.get("status") != "completed":
        problems.append("the state's status is %r, not 'completed'"
                        % st.get("status"))
    if st.get("scriptPath") != expect["script_path"] and not _same_published_script(
            st.get("scriptPath"), expect["script_path"]):
        problems.append("the state ran %r, this segment published %r"
                        % (st.get("scriptPath"), expect["script_path"]))
    script = st.get("script")
    if not isinstance(script, str):
        problems.append("the state persisted no script bytes")
    elif hashlib.sha256(script.encode("utf-8")).hexdigest() != \
            expect["script_sha256"]:
        problems.append("the state's persisted script is not the published one")
    if json.dumps(st.get("args"), sort_keys=True) != \
            json.dumps(expect["args"], sort_keys=True):
        problems.append("the state's saved args are not the published ones")

    progress = st.get("workflowProgress")
    if not isinstance(progress, list) or not progress:
        return problems + ["the state records no per-agent rows; zero tool use "
                           "cannot be proved from run totals"], {}
    # A MALFORMED PROGRESS ENTRY IS REJECTED, never filtered away: silently
    # dropping it is how a state that records nothing readable still passes.
    for i, entry in enumerate(progress):
        if not isinstance(entry, dict):
            problems.append("workflowProgress entry %d is %s, not an object"
                            % (i, type(entry).__name__))
    if problems:
        return problems, {}
    rows = [r for r in progress if r.get("type") == G1_AGENT_ROW]
    if not rows:
        return problems + ["the state records no agent rows"], {}
    want = expect["rows"]
    if len(rows) > len(want):
        problems.append("the state records %d agent rows for %d published"
                        % (len(rows), len(want)))
        return problems, {}
    captured = expect["captures"]
    if len(captured) != len(rows):
        return problems + ["the state records %d agent rows but %d captures"
                           % (len(rows), len(captured))], {}
    finals, seen, response_ids = [], set(), {}
    for position, pr in enumerate(rows):
        row = want[position]
        label = pr.get("label")
        if label != row["lane_id"]:
            problems.append("official row %d is %r, published row %d is %r"
                            % (position, label, position, row["lane_id"]))
            continue
        if label in seen:
            problems.append("%s appears in two official agent rows" % label)
            continue
        seen.add(label)
        # A row that ERRORED is lawful only as the LAST attempted row, and
        # only when the capture records the same failure. Anything else must
        # be a completed row.
        errored = pr.get("state") == "error"
        if errored and (position != len(rows) - 1
                        or not captured[position].get("error")):
            problems.append("%s is in state 'error' but is not the last "
                            "attempted row with a recorded failure" % label)
            continue
        if not errored and pr.get("state") != "done":
            problems.append("%s is in state %r, not 'done'"
                            % (label, pr.get("state")))
            continue
        agent_id = pr.get("agentId")
        if not agent_id:
            problems.append("%s records no agentId" % label)
            continue
        # A NATIVE CACHED RETURN, decided by the ONE cached-shape owner against
        # this row's real agent metadata. The plan it is judged against comes
        # from the already-bound expectations, never from a literal: the
        # published args carry the model ALIAS the runtime reports on a cached
        # row, and the root lane carries the agent type (Codex SEQ 1781).
        planned = expect["args"][position] if position < len(expect["args"]) else {}
        lane_plan = {"model": planned.get("model"),
                     "agentType": expect["agentType"]}
        rid_dir = os.path.join(session_dir, "subagents", "workflows", rid)
        cached = _resumed_cached_row(pr, rid_dir, lane_plan)
        if "cached" in pr and not cached:
            # It claims the cached shape but its own metadata does not back it.
            # It must NOT reach the fresh-row path and pass by another route.
            problems.append("%s claims a cached row that its exact shape and "
                            "agent metadata do not support" % label)
            continue
        if not cached and pr.get("model") != expect["runtime_model_id"]:
            problems.append("%s ran model %r, not %r"
                            % (label, pr.get("model"),
                               expect["runtime_model_id"]))
        if not cached and pr.get("agentType") != expect["agentType"]:
            problems.append("%s ran agent type %r, not %r"
                            % (label, pr.get("agentType"), expect["agentType"]))
        # ZERO TOOL USE MUST BE PROVED, not assumed from a missing field - and a
        # cached row is the ONE shape whose key set proves it never spawned.
        if not cached and pr.get("toolCalls") != 0:
            problems.append("%s records toolCalls %r; this lane must prove "
                            "exactly 0" % (label, pr.get("toolCalls")))
        if pr.get("lastToolName") is not None:
            problems.append("%s names a last tool %r; this lane allows none"
                            % (label, pr.get("lastToolName")))
        if not _preview_ok(pr.get("promptPreview"), row["prompt"]):
            problems.append("%s's official prompt preview is not a prefix of "
                            "the published prompt" % label)
        if errored:
            finals.append((label, None, None))
            continue
        why, final, complete = _g1_transcript(
            session_dir, session_id, rid, agent_id, row["prompt_sha256"],
            expect["runtime_model_id"], expect["effort"], response_ids,
            row.get("expected_input"))
        problems += ["%s: %s" % (label, w) for w in why]
        finals.append((label, final, complete))

    # THE THREE SOURCES MUST AGREE, ONE TO ONE.
    outer = st.get("result")
    if not isinstance(outer, dict):
        problems.append("the state's result is %s, not an object"
                        % type(outer).__name__)
        return problems, {}
    result = outer.get("results")
    if not isinstance(result, list):
        problems.append("the state carries no result.results list")
        return problems, {}
    if outer.get("rows") != len(want):
        problems.append("the state's result.rows is %r, not the %d published"
                        % (outer.get("rows"), len(want)))
    if outer.get("calls") != len(result) or len(result) != len(rows):
        problems.append("result.calls %r, result.results %d and agent rows %d "
                        "do not agree" % (outer.get("calls"), len(result),
                                          len(rows)))
    if not (len(result) == len(finals) == len(captured)):
        problems.append("the state returned %d rows, the transcripts %d and "
                        "the captures %d" % (len(result), len(finals),
                                             len(captured)))
        return problems, {}
    whole = collections.OrderedDict()
    for position, (label, final, complete) in enumerate(finals):
        saved = result[position]
        cap = captured[position]
        if not isinstance(saved, dict):
            problems.append("state result row %d is %s, not an object"
                            % (position, type(saved).__name__))
            continue
        if saved.get("lane_id") != label or cap.get("lane_id") != label:
            problems.append("row %d disagrees on identity: state %r, capture "
                            "%r, transcript %r"
                            % (position, saved.get("lane_id"),
                               cap.get("lane_id"), label))
            continue
        # THE COMPLETE RETURNED ROW, not a projection of it. A missing field,
        # an extra field or any changed value is a disagreement.
        want_row = cap.get("returned") or {}
        missing = sorted(set(want_row) - set(saved))
        extra = sorted(set(saved) - set(want_row))
        if missing or extra:
            problems.append("%s: the state row is missing %s and carries extra "
                            "%s" % (label, missing, extra))
            continue
        differing = sorted(k for k in want_row
                           if json.dumps(saved.get(k), sort_keys=True)
                           != json.dumps(want_row.get(k), sort_keys=True))
        if differing:
            problems.append("%s: the state row and the capture differ on %s"
                            % (label, differing))
            continue
        if final is not None and saved.get("text") != final:
            problems.append("%s: the transcript's final answer is not the "
                            "returned text" % label)
            continue
        # THE VERIFIED WHOLE ANSWER, carried out instead of dropped. The
        # terminal text stays exactly what the state returned; this is the
        # same bytes the chain proved, in transcript order.
        if complete:
            whole[label] = complete
    if len(rows) < len(want):
        # A LAWFUL STOPPED TAIL: the last row that WAS attempted must have
        # ended in the recorded error, or the short result is unexplained.
        last = captured[-1] if captured else {}
        if last.get("error") in (None, ""):
            problems.append("the state is short by %d rows and the last "
                            "attempted row records no error"
                            % (len(want) - len(rows)))
    return problems, whole

def main(argv):
    """THE CLI the manifest names: audit one run directory's receipt."""
    if len(argv) < 2:
        print("usage: audit_worker_access.py <run_dir>/receipt.json")
        return 2
    out = audit(argv[1])
    for why in out["problems"]:
        print("  VIOLATION: %s" % why)
    counts = {}
    for _k, outcome, _w in out["outcomes"]:
        counts[outcome] = counts.get(outcome, 0) + 1
    print("outcomes: %s" % (counts or "none"))
    print("RESULT: %s" % ("LAWFUL" if not out["problems"]
                          else "UNLAWFUL (%d)" % len(out["problems"])))
    return 1 if out["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
