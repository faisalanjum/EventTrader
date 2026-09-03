"""raw_transport — the EXACT-number transport for K-fields / EXP-5 replies.

THE PROBLEM THIS EXISTS TO SOLVE (proven, not theoretical): the launcher used
`agent(..., {schema: SCHEMA})`, which makes the workflow runtime parse the
model's JSON in JAVASCRIPT. JS numbers are IEEE-754 doubles, so
`{"a":1.00000000000000000001,"b":1.00000000000000000002}` becomes `{"a":1,"b":1}`
BEFORE Python ever runs. Python then sees `1.0`, parses a perfectly valid
`Decimal('1.0')`, and every downstream type-gate passes — the digits are gone
and nothing can tell. A downstream fix CANNOT detect upstream loss.

THE ORDER (the whole point — do not reorder):

    raw model TEXT  ->  save unchanged  ->  Decimal JSON parse  ->  the V2
                                                                   checker at
                                                                   the model door

Dropping the workflow's `schema:` removes JS PARSING, never SCHEMA ENFORCEMENT:
enforcement simply moves after the exact parse, where `kf_lint` applies the
authoritative contract. That checker states no shape of its own — it delegates
every item, type, numeric, unit and evidence rule to Core's
`PreparedFactV2.from_dict`, so there is one owner, applied once, on exact values.

WHICH DOOR (B-13). Two plans, two contracts, so two doors:
  `door="gold"`   K-fields drafting — `lint_doc`, which additionally requires
                  du_worthy / gold_extra / ambiguity_note;
  `door="reader"` EXP-5 producing — `lint_v2_reply`, the plain V2 envelope.
The caller passes it FROM ITS PLAN. It is never inferred from the reply, because
a producer reply that happened to carry a gold key would then select its own
door — the wrong-door failure this split exists to prevent. The two plans hold
separate manifests and separate approvals, so the plan identity already decides.
There is NO default and no caller argument: the transport reads the door from
the plan manifest it was given, and a missing or unknown door refuses the ingest
outright rather than guessing.

Workflow scripts have no filesystem access, so the raw reply travels back as a
STRING — strings are never number-parsed — and is written to disk HERE, first,
byte-for-byte, before anything interprets it.
"""
import hashlib
import shutil
import io
import json
import os
from decimal import Decimal

__all__ = ["save_raw", "parse_exact", "ingest_workflow_result",
           "invalid_pairs", "resolve_with_one_retry", "prompt_pin",
           "prompt_evidence_problem", "schedule_from_manifest",
           "manifest_events", "RawTransportError"]


class RawTransportError(ValueError):
    """The reply could not be captured or parsed exactly."""


def save_raw(text, out_dir, name):
    """Write the model's reply EXACTLY as received, before any interpretation.
    Returns (path, sha256). The bytes on disk are the audit record: everything
    downstream is derived from this file, never from a pre-parsed object.

    REFUSES TO OVERWRITE (mode "x"): a paid reply already on disk is evidence;
    silently replacing it would destroy the audit trail."""
    if not isinstance(text, str):
        raise RawTransportError(
            f"raw reply must be the model's TEXT, got {type(text).__name__} — a "
            f"pre-parsed object means digits may already be lost upstream")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.raw.json")
    # ATOMIC COMPLETION, not merely exclusive creation. Opening the FINAL name
    # with mode "x" and writing into it is not atomic: a process death mid-write
    # leaves a truncated file under the real name, and the next attempt then
    # refuses because that partial file exists — the paid reply is lost twice
    # over (Codex SEQ 1313 item 1). So: write the whole thing to a temporary in
    # the SAME directory, flush it, fsync it, and only then publish it under a
    # still-absent final name with `os.link`, which is atomic and fails if the
    # name is taken. A death at any point leaves at most a `.partial`.
    tmp = "%s.partial.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.link(tmp, path)
    except FileExistsError:
        raise RawTransportError(
            f"{path} already exists — refusing to overwrite a captured reply; "
            f"move or delete it deliberately")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs):
    """Python's json silently keeps the LAST of duplicate keys, so
    `{"source_id":"A","source_id":"B"}` becomes B and the first value vanishes —
    a reply could smuggle a second, conflicting value past every check."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise RawTransportError(
                f"duplicate JSON key {k!r} — one value would silently win; the "
                f"reply is ambiguous and is refused")
        out[k] = v
    return out


def _reject_nonstandard_constant(token):
    """`NaN`/`Infinity`/`-Infinity` are NOT valid JSON but Python accepts them by
    default. They are not exactly comparable, so they must never enter scoring."""
    raise RawTransportError(
        f"non-standard JSON constant {token!r} — not a comparable number")


#: The exact fence a whole-response JSON block may use. It is TRANSPORT, not
#: content: a model that wraps its one JSON object in one fenced block has sent
#: the same object, and refusing it would be refusing an envelope rather than a
#: reply (owner ruling via Codex SEQ 1330 item A). Nothing else is unwrapped.
_FENCE = "```"


def unfence(text):
    """THE ONE outer-envelope normalizer, model-neutral and shared.

    Accepts exactly two envelopes and nothing else: a bare payload, or exactly
    ONE whole-response fenced block whose opening fence carries at most a bare
    info word and whose closing fence ends the response. Prose outside the
    block, a second block, an unclosed block or anything after the close is
    refused here rather than repaired.

    It never looks inside the payload: no key is touched, no number is
    reformatted, nothing is repaired. `parse_exact` still owns the parse.
    """
    if not isinstance(text, str):
        raise RawTransportError(
            "reply is %s, not text" % type(text).__name__)
    body = text.strip()
    # THE ENVELOPE FORM IS DECIDED BY THE OPENING ALONE. A fence sequence can
    # occur legitimately INSIDE a JSON string -- a quoted source may contain
    # one -- so the payload is never scanned for fence characters. Text that
    # does not open with a fence is handed on whole; `parse_exact` already
    # refuses real surrounding prose, and it already refuses a second block as
    # extra material (Codex SEQ 1331 item 1).
    if not body.startswith(_FENCE):
        return text
    if not body.endswith(_FENCE) or len(body) < 2 * len(_FENCE):
        raise RawTransportError(
            "the reply opens a fence it never closes at the end of the reply")
    inner = body[len(_FENCE):-len(_FENCE)]
    head, sep, rest = inner.partition("\n")
    if not sep:
        raise RawTransportError("the fenced block carries no payload line")
    if head.strip() and len(head.split()) > 1:
        raise RawTransportError(
            "the opening fence carries %r, not a bare info word" % head.strip())
    return rest


def parse_reply(text):
    """Normalize the OUTER ENVELOPE, then parse exactly. One path for every
    reply, event or final sign. The caller keeps the raw bytes; this returns
    only the parsed object."""
    return parse_exact(unfence(text))


def parse_exact(text):
    """Parse reply text with EXACT decimals. A JSON number with a fraction
    or exponent becomes a Decimal carrying the source digits (parse_float);
    a JSON INTEGER stays a Python int — json.loads has no parse_int hook
    engaged here, and an exact int is already exact (S9: this docstring
    used to claim EVERY number becomes Decimal, which was false). No float
    ever exists in this path. Duplicate keys and NaN/Infinity are refused
    rather than silently accepted."""
    try:
        return json.loads(text, parse_float=Decimal,
                          object_pairs_hook=_reject_duplicate_keys,
                          parse_constant=_reject_nonstandard_constant)
    except json.JSONDecodeError as e:
        raise RawTransportError(f"reply is not valid JSON: {e}")


ARMS = ("sonnet", "opus")
_HERE = os.path.dirname(os.path.abspath(__file__))
#: The repository root, derived from THIS file's location — the same convention
#: the manifest builder uses for its repo-relative paths.
_REPO_ROOT = os.path.abspath(os.path.join(
    _HERE, os.pardir, os.pardir, os.pardir, os.pardir, os.pardir))
DEFAULT_MANIFEST = os.path.join(_HERE, "launch_kfields_drafts.manifest.json")


def manifest_events(manifest_path=DEFAULT_MANIFEST):
    """The AUTHORITATIVE expected event set — read from the launch manifest, so
    ingestion is manifest-BOUND and cannot silently accept a different corpus."""
    with open(manifest_path, encoding="utf-8") as f:
        m = json.load(f)
    sids = [e["source_id"] for e in m["events"]]
    if len(set(sids)) != len(sids):
        raise RawTransportError("manifest itself contains duplicate source_ids")
    return sids


def prompt_pin(manifest_path, source_id):
    """The manifest's pinned `prompt_sha256` for this source, or raise.

    ONE tiny helper, used by initial classification, ingestion, and final
    resolution — so the prompt-evidence comparison exists in a single place
    rather than being copied into three (Codex SEQ 1161.2).
    """
    with io.open(manifest_path, encoding="utf-8") as fh:
        man = json.load(fh)
    pin = next((e.get("prompt_sha256") for e in man["events"]
                if e["source_id"] == source_id), None)
    if pin is None:
        raise RawTransportError(
            f"{source_id}: not an event of {os.path.basename(manifest_path)}")
    return pin


def prompt_evidence_problem(row, manifest_path):
    """`None` if this per-call row proves it used the pinned prompt, else why.

    A lawful FIRST-PASS answer used to be accepted without its prompt evidence
    ever being matched — only rows handed to the retry resolver were checked.
    """
    got = (row or {}).get("prompt_sha256")
    if not got:
        return "no prompt evidence on the reply row"
    try:
        pin = prompt_pin(manifest_path, row["source_id"])
    except RawTransportError as e:
        # an UNEXPECTED event is a refusal to COLLECT, not a crash: the schedule
        # check below names it and the raw reply is already saved
        return str(e)
    if got != pin:
        return (f"used prompt {str(got)[:12]}, not the pinned {pin[:12]}")
    return None


def _attempt_valid(text, source_id, door):
    """Is this ONE raw text a lawful answer for this source? `(doc, reason)`.

    The single validity owner: exact parse, scheduled source echo, and the
    manifest's door through `kf_lint`. Saving is deliberately NOT here — the
    classifier must be able to ask without writing, or it double-saves the same
    reply and trips the overwrite refusal (which is what happened).
    """
    from kf_lint import lint_parsed, DEFAULT_INPUTS
    try:
        doc = parse_exact(text)
    except RawTransportError as e:
        return None, str(e)
    inner = doc.get("source_id") if isinstance(doc, dict) else None
    if inner != source_id:
        return None, f"reply carries source_id {inner!r} — WRONG SOURCE"
    if lint_parsed([doc], DEFAULT_INPUTS, arm=False, door=door) != 0:
        return None, "parseable but NOT a lawful V2 answer"
    return doc, None


def invalid_pairs(captures, manifest_path):
    """PHASE 1 -> PHASE 2. Classify a launch's rows and return the scheduled
    pairs that must be retried EXACTLY ONCE (Codex SEQ 1159).

    Validity is decided HERE, in Python, by the same owners as everywhere else —
    exact parse, scheduled source echo, the manifest's door, `kf_lint`. No
    JSON or V2 rule is evaluated in JavaScript.
    """
    from kf_lint import DOORS
    with io.open(manifest_path, encoding="utf-8") as fh:
        door = json.load(fh).get("door")
    if door not in DOORS:
        raise RawTransportError(f"plan manifest names door {door!r}")
    # NO STRUCTURALLY UNSCHEDULED PAIR MAY LEAVE PHASE 1 AS A RETRY REQUEST
    # (Codex SEQ 1165). The subset refusal used to fire only when phase 2
    # ingested — i.e. AFTER a second call had already been launched and PAID
    # for. The pair's raw stays preserved; it simply never becomes a retry.
    scheduled = schedule_from_manifest(manifest_path)
    retry, integrity = [], []
    for row in (captures.values() if isinstance(captures, dict) else captures):
        why = prompt_evidence_problem(row, manifest_path)
        if why:
            # PROMPT INTEGRITY IS NOT BAD MODEL OUTPUT (Codex SEQ 1162.2). A
            # reply whose prompt evidence is missing or wrong means we do not
            # know what was asked, so re-asking cannot help: it FAILS CLOSED and
            # must never spend the one allowed retry.
            integrity.append(f"{row['source_id']}/{row['arm']}: {why}")
            continue
        # READ THE SAVED BYTES (Codex SEQ 1163.3): classification consumes the
        # persisted capture, never an in-memory text nobody wrote down.
        text = io.open(row["raw_path"], encoding="utf-8").read()
        doc, _why = _attempt_valid(text, row["source_id"], door)
        if doc is None:
            pair = (row["source_id"], row["arm"])
            # THE ONE ALLOWED RETRY IS ALREADY SPENT once this capture IS the
            # retry. Emitting a request here would launch and PAY for a third
            # attempt, which the resolver then refuses — after the money. The
            # capture says which attempt it is, so the request stops here.
            already_retried = (row.get("attempt") or 1) > 1
            if pair in scheduled and not already_retried:
                retry.append({"arm": row["arm"], "source_id": row["source_id"]})
    if integrity:
        raise RawTransportError(
            "prompt integrity failure — the run cannot continue: "
            + "; ".join(integrity[:3]))
    return retry


def schedule_from_manifest(manifest_path):
    """The expected `(source_id, arm)` pairs, DERIVED from the selected plan.

    Codex SEQ 1150: the transport hardcoded `ARMS = ("sonnet", "opus")` and one
    row per EVENT carrying both arms. The reader launcher returns one row per
    CALL — `{arm, source_id, text}` for P1..P5 — so ingesting it reported every
    repeated event as a duplicate and both old arms as missing (reproduced: 432
    errors on 156 lawful replies).

    The schedule is read from whichever manifest is passed; no plan's arm names
    are written here. A K-fields plan names its arms per event in `lanes`; a
    reader plan names them in `arms` with a `scope`. Both are the plan's OWN
    words, not this module's.
    """
    with io.open(manifest_path, encoding="utf-8") as fh:
        man = json.load(fh)
    events = [e["source_id"] for e in man["events"]]
    if "arms" in man:                                   # reader-style plan
        subsample = set((man.get("opus_ref_subsample") or {}).get(
            "source_ids") or ())
        pairs = set()
        for arm in man["arms"]:
            scope = events if arm.get("scope") == "all_36" else [
                s for s in events if s in subsample]
            pairs.update((sid, arm["arm"]) for sid in scope)
        return pairs
    if "packets" in man:                                # A1 one-item plan
        # THE IDENTITY IS (packet_id, lane_id). Two blind lanes of the SAME
        # model are two separate calls; keying on the model name collapsed them
        # and reported 36 pairs for a 336-call plan.
        return {(pk["packet_id"], lane["lane_id"])
                for pk in man["packets"] for lane in pk["lanes"]}
    # K-fields-style plan: each event names its own lanes
    return {(e["source_id"], lane["model"])
            for e in man["events"] for lane in e.get("lanes", ())}


def replies_from_result(result):
    """Normalise BOTH launcher shapes to `[(source_id, arm, text)]`.

    ONE row per CALL — `{arm, source_id, text}` — or the older ONE row per EVENT
    carrying an arm-named field each. Nothing here knows any arm NAME: the
    per-call shape states its own, and the per-event shape is read as "every
    key that is not bookkeeping".
    """
    out = []
    for n, row in enumerate(result or []):
        if not isinstance(row, dict):
            out.append((None, None, None, n, None))     # malformed, reported later
            continue
        sid = row.get("source_id")
        if "packet_id" in row and "lane_id" in row and "text" in row:
            # A1 flat row: identity is the packet and the named lane.
            out.append((row["packet_id"], row["lane_id"], row["text"], n,
                        row.get("prompt_sha256")))
            continue
        if "arm" in row and "text" in row:
            out.append((sid, row["arm"], row["text"], n, row.get("prompt_sha256")))
        else:
            for k, v in row.items():
                if k in ("source_id", "ticker", "prompt_sha256", "attempt"):
                    continue
                out.append((sid, k, v, n, row.get("prompt_sha256")))
    return out


def _ingest_by_schedule(result, out_dir, schedule, manifest_path, validate,
                        inputs_dir, attempt=1, retry_schedule=None):
    """Ingest a plan whose identity is `(source_id, arm)`.

    Same law as the event-keyed path and the SAME owners: save EVERY received
    reply before parsing ANY, then measure against the schedule. Missing, extra,
    duplicate, wrong-arm and wrong-event are all differences from the plan's own
    schedule rather than from a hardcoded arm list.
    """
    # A RETRY SCHEDULE MUST BE A SUBSET of the approved one (Codex SEQ 1163.2).
    # THE REFUSAL IS RECORDED, NOT RETURNED EARLY (Codex SEQ 1164.2): returning
    # here skipped the save loop entirely, so a refused retry lost the raw bytes
    # it had already been PAID for — contradicting this module's own invariant
    # that every received reply is preserved even when a schedule check rejects
    # it.
    errors, saved, seen, captures = [], {}, {}, {}
    unscheduled = (set(retry_schedule) - schedule
                   if retry_schedule is not None else set())
    if unscheduled:
        errors.append(f"retry schedule names unscheduled pair(s) "
                      f"{sorted(unscheduled)[:3]}")
    elif retry_schedule is not None:
        schedule = set(retry_schedule)
    rows = (result or {}).get("results")
    if not isinstance(rows, list):
        return {"docs": {}, "captures": {}, "ok": False,
                "errors": [f"workflow result must carry a `results` list — got "
                           f"{type(rows).__name__}"]}

    # 1. SAVE FIRST. Every reply reached us and was PAID FOR, including the ones
    #    the schedule will reject.
    for sid, arm, text, n, pev in replies_from_result(rows):
        if sid is None or arm is None:
            errors.append(f"row {n}: malformed reply row")
            continue
        key = (sid, arm)
        dup = key in seen
        seen.setdefault(key, 0)
        seen[key] += 1
        suffix = f".dup{seen[key] - 1}" if dup else ""
        if attempt > 1:
            suffix += f".retry{attempt - 1}"      # a DISTINCT attempt name
        try:
            path, sha = save_raw(text, out_dir, f"{sid}{suffix}.{arm}")
            saved[(sid, arm, seen[key])] = (path, sha)
            if not dup:
                # THE CAPTURE RECORD — written BEFORE any interpretation, and
                # what classification and resolution consume from here on.
                captures[key] = {"source_id": sid, "arm": arm, "attempt": attempt,
                                 "raw_path": path, "raw_sha256": sha,
                                 "prompt_sha256": pev}
        except RawTransportError as e:
            errors.append(f"{sid}{suffix}.{arm}: {e}")
        if dup:
            errors.append(f"{sid}/{arm}: DUPLICATE reply — rejected "
                          f"(preserved as {suffix.lstrip('.')})")

    # 2. PROMPT BINDING, at the real ingestion boundary — after saving, before
    #    any content judgement (Codex SEQ 1162.3). Every per-call row must prove
    #    it used the pinned prompt.
    for row in rows:
        if not isinstance(row, dict) or "arm" not in row:
            continue
        why = prompt_evidence_problem(row, manifest_path)
        if why:
            errors.append(f"{row.get('source_id')}/{row.get('arm')}: {why}")

    # 3. MEASURE against the plan's schedule.
    got = set(seen)
    for sid, arm in sorted(schedule - got):
        errors.append(f"MISSING scheduled reply {sid}/{arm}")
    for sid, arm in sorted(got - schedule):
        errors.append(f"UNEXPECTED reply {sid}/{arm} — not in the plan schedule")

    # 4. PARSE + cross-check each lawful, non-duplicate reply exactly once.
    docs = {}
    for (sid, arm), n_seen in sorted(seen.items()):
        if (sid, arm) not in schedule or n_seen != 1:
            continue
        entry = saved.get((sid, arm, 1))
        if not entry:
            continue
        path, _sha = entry            # save_raw returns (path, sha256)
        try:
            doc = parse_exact(io.open(path, encoding="utf-8").read())
        except RawTransportError as e:
            errors.append(f"{sid}/{arm}: {e}")
            continue
        # THE INNER ECHO IS REQUIRED, not merely checked when present: a reply
        # that never says which event it answers cannot be bound to one.
        inner = doc.get("source_id") if isinstance(doc, dict) else None
        if inner != sid:
            errors.append(f"{sid}/{arm}: reply carries source_id {inner!r} — "
                          f"WRONG EVENT")
            continue
        # DURABLY BOUND (Codex SEQ 1151): the checked reply carries the event,
        # the role/arm, the RUN it belongs to, and the EXACT manifest bytes it
        # was scheduled by. A doc that cannot name its run or its plan cannot be
        # audited later.
        docs[(sid, arm)] = {
            "doc": doc, "raw_path": path, "raw_sha256": _sha,
            "source_id": sid, "arm": arm,
            "prompt_sha256": next(
                (r.get("prompt_sha256") for r in rows
                 if isinstance(r, dict) and r.get("source_id") == sid
                 and r.get("arm") == arm), None),
            "run": os.path.basename(os.path.abspath(out_dir)),
            "manifest_path": os.path.relpath(manifest_path, _REPO_ROOT),
            "manifest_sha256": hashlib.sha256(
                io.open(manifest_path, "rb").read()).hexdigest(),
        }

    # ---- VALIDATE through the ONE authoritative checker ----
    # The scheduled path accepted `validate`/`inputs_dir` and used NEITHER, so a
    # schedule-complete, parseable but V2-INVALID reply returned ok=True
    # (reproduced). The door comes from the BOUND MANIFEST exactly as the
    # event-keyed path takes it — never from a caller argument.
    if validate and not errors:
        from kf_lint import lint_parsed, DEFAULT_INPUTS, DOORS
        with io.open(manifest_path, encoding="utf-8") as fh:
            door = json.load(fh).get("door")
        if door not in DOORS:
            errors.append(
                f"plan manifest {os.path.basename(manifest_path)} names door "
                f"{door!r}, which is not one of {sorted(DOORS)}: which contract "
                f"to check is undecidable")
            return {"docs": docs, "captures": captures, "errors": errors, "ok": False}
        # THE SCHEDULE already proves the exact arm population, including P5's
        # 12-event subset, so the arms come from it rather than being named here.
        for arm in sorted({a for _s, a in schedule}):
            arm_docs = [v["doc"] for (s, a), v in sorted(docs.items()) if a == arm]
            # CONTENT/SHAPE ONLY — `arm=False` (Codex SEQ 1154).
            #
            # `arm=True` additionally demands the ENTIRE 36-input population,
            # which is wrong here: an arm's population is whatever the PLAN
            # scheduled for it, and P5 is deliberately a 12-event subset. With
            # `arm=True` a completely LAWFUL 156-reply run failed on P5 — caught
            # only when the missing positive control was added.
            #
            # Population is NOT unchecked: missing, extra and duplicate
            # `(source_id, arm)` pairs were already refused above against the
            # manifest-derived schedule, which is the one owner of who owes what.
            # `lint_parsed` returns a COUNT, not a list.
            if lint_parsed(arm_docs, inputs_dir or DEFAULT_INPUTS, arm=False,
                           door=door) != 0:
                errors.append(f"arm {arm}: FAILED content validation")
    return {"docs": docs, "captures": captures, "errors": errors, "ok": not errors}


def resolve_with_one_retry(source_id, arm, captures, manifest_path):
    """§6 / WorkOrder §1.5 — one retry, decided from ALREADY-SAVED captures.

    THE RESOLVER PERFORMS ZERO WRITES (Codex SEQ 1163.3). It used to save both
    attempts itself, which duplicated the first reply the ingest had already
    written, and it checked prompt evidence BEFORE saving — so a retry with bad
    evidence raised and its PAID raw text was never preserved at all. Saving is
    the ingest's job and happens first, per phase, under a distinct attempt name.

    `captures` are those persisted records in attempt order. Each carries its own
    launcher-emitted prompt evidence, which must equal the manifest pin — a
    retry reuses the SAME prompt. The first lawful attempt wins; a second
    invalid one enters the INVALID BUCKET and is never coerced or retried.
    """
    if len(captures) > 2:
        raise RawTransportError(
            f"{source_id}/{arm}: {len(captures)} attempts — the WorkOrder "
            f"allows the original and EXACTLY ONE retry")
    from kf_lint import DOORS
    with io.open(manifest_path, encoding="utf-8") as fh:
        door = json.load(fh).get("door")
    if door not in DOORS:
        raise RawTransportError(f"plan manifest names door {door!r}")

    reasons = []
    for i, cap in enumerate(captures, 1):
        why = prompt_evidence_problem(cap, manifest_path)
        if why:
            # integrity, not model output — the raw is already preserved
            raise RawTransportError(f"{source_id}/{arm}: attempt {i} {why} — "
                                    f"a retry reuses the SAME prompt")
    for i, cap in enumerate(captures, 1):
        text = io.open(cap["raw_path"], encoding="utf-8").read()
        doc, why = _attempt_valid(text, source_id, door)
        if doc is None:
            reasons.append(f"attempt {i}: {why}")
            continue
        return {"doc": doc, "attempt": i, "raw": [(c["raw_path"],
                                                   c["raw_sha256"])
                                                  for c in captures],
                "invalid": None}
    return {"doc": None, "attempt": None,
            "raw": [(c["raw_path"], c["raw_sha256"]) for c in captures],
            "invalid": f"{source_id}/{arm}: " + "; ".join(reasons)}



def ingest_workflow_result(result, out_dir, manifest_path=DEFAULT_MANIFEST,
                           validate=True, inputs_dir=None, attempt=1,
                           retry_schedule=None):
    """THE single manifest-bound ingestion entry point.

    Order matters and is deliberate:
      1. STRUCTURE — the rows must be EXACTLY the manifest's events: none
         missing, none extra, no duplicates, both arms present on every row.
      2. SAVE EVERYTHING FIRST — every raw reply is written to disk BEFORE any
         parsing. A malformed early reply must never cost the later PAID
         replies (reproduced: the old loop aborted and lost them).
      3. PARSE — each saved reply, exactly (`parse_float=Decimal`).
      4. CROSS-CHECK — the reply's INNER `source_id` must equal the event it was
         assigned (reproduced: a reply for WRONG_B used to pass as ASSIGNED_A).
      5. VALIDATE — automatically, through the ONE authoritative checker, on
         BOTH complete arms.

    Nothing is raised mid-flight: problems are COLLECTED so a single bad reply
    can never discard good, paid work. Returns
    {"docs": {(sid, arm): {...}}, "errors": [...], "ok": bool}.
    """
    errors = []
    rows = (result or {}).get("results")
    if not isinstance(rows, list):
        return {"docs": {}, "ok": False,
                "errors": [f"workflow result must carry a `results` list — got "
                           f"{type(rows).__name__}"]}

    # ---- 0. SCHEDULE-BOUND PATH (Codex SEQ 1150) ----
    # When the selected plan schedules more than one reply per event — any
    # multi-arm plan, of which the reader plan is the first — identity is the
    # PAIR `(source_id, arm)`, not the event. The old event-keyed path below
    # cannot express that and reported 156 lawful replies as duplicates.
    # Routed on the RESULT SHAPE, not on the plan: BOTH plans are multi-arm
    # (K-fields is 36 events x 2 lanes), so "more than one reply per event"
    # cannot distinguish them — my first attempt used that and sent K-fields
    # down the new path, losing its record fields.
    rows_in = (result or {}).get("results")
    if isinstance(rows_in, list) and any(
            isinstance(r, dict) and "arm" in r and "text" in r for r in rows_in):
        return _ingest_by_schedule(result, out_dir,
                                   schedule_from_manifest(manifest_path),
                                   manifest_path, validate, inputs_dir,
                                   attempt=attempt,
                                   retry_schedule=retry_schedule)

    # ---- 1. structure, bound to the manifest ----
    expected = manifest_events(manifest_path)
    seen, dupes = {}, []
    for n, row in enumerate(rows):
        if not isinstance(row, dict):          # a malformed row must not CRASH
            errors.append(f"row {n}: must be an object, got {type(row).__name__}")
            continue
        sid = row.get("source_id")
        if not sid or not isinstance(sid, str):
            errors.append(f"row {n}: missing/invalid source_id ({sid!r})")
            continue
        if sid in seen:
            # REJECTED as a duplicate — but these replies were still PAID FOR,
            # so they are saved below under a distinct .dupN name. Rejecting a
            # row must never destroy the evidence it carries.
            dupes.append((sid, len(dupes) + 1, row))
            errors.append(f"{sid}: DUPLICATE row — rejected (replies preserved "
                          f"as .dup{len(dupes)})")
            continue
        seen[sid] = row
    missing = [s for s in expected if s not in seen]
    extra = [s for s in seen if s not in expected]
    if missing:
        errors.append(f"MISSING {len(missing)} event(s): {missing[:5]}")
    if extra:
        errors.append(f"UNEXPECTED event(s) not in the manifest: {extra[:5]}")

    # ---- 2. save EVERY raw reply before parsing ANY (protect paid work) ----
    def _save(sid, arm, row, suffix=""):
        if arm not in row:
            errors.append(f"{sid}{suffix}: arm {arm!r} missing from result")
            return None
        try:
            return save_raw(row[arm], out_dir, f"{sid}{suffix}.{arm}")
        except RawTransportError as e:
            errors.append(f"{sid}{suffix}.{arm}: {e}")
            return None

    saved = {}
    for sid, row in seen.items():
        for arm in ARMS:
            got = _save(sid, arm, row)
            if got:
                saved[(sid, arm)] = got
    for sid, n, row in dupes:              # paid + rejected + still preserved
        for arm in ARMS:
            _save(sid, arm, row, suffix=f".dup{n}")

    # ---- 3+4. parse exactly, then cross-check the inner source_id ----
    docs = {}
    for (sid, arm), (path, digest) in sorted(saved.items()):
        try:
            doc = parse_exact(open(path, encoding="utf-8").read())
        except RawTransportError as e:
            errors.append(f"{sid}.{arm}: {e}")
            continue
        if not isinstance(doc, dict):
            errors.append(f"{sid}.{arm}: reply must be a JSON object, got "
                          f"{type(doc).__name__}")
            continue
        inner = doc.get("source_id")
        if inner != sid:
            errors.append(f"{sid}.{arm}: reply is for {inner!r}, not the assigned "
                          f"event — WRONG-EVENT reply, refused")
            continue
        docs[(sid, arm)] = {"doc": doc, "raw_path": path, "sha256": digest}

    # ---- 5. automatic strict validation of BOTH complete arms ----
    if validate:
        from kf_lint import lint_parsed, DEFAULT_INPUTS
        # THE DOOR COMES FROM THE PLAN MANIFEST, never from a caller argument.
        # A caller-supplied door with a default is what let a future EXP-5 run
        # take the gold door by simply forgetting to pass one; the approved plan
        # already knows which contract it executes, so it says so.
        with open(manifest_path, encoding="utf-8") as _fh:
            door = json.load(_fh).get("door")
        from kf_lint import DOORS
        # ONE refusal shape for both faults. An unknown door used to escape as a
        # raw ValueError from deep inside the arm loop; a missing one returned a
        # structured error. Same defect, so same answer — and the raw replies are
        # already safely on disk by this point either way.
        if door not in DOORS:
            errors.append(
                f"plan manifest {os.path.basename(manifest_path)} names door "
                f"{door!r}, which is not one of {sorted(DOORS)}: which contract "
                f"to check is undecidable")
            return {"docs": docs, "errors": errors, "ok": False}
        for arm in ARMS:
            arm_docs = [v["doc"] for (s, a), v in sorted(docs.items()) if a == arm]
            if len(arm_docs) != len(expected):
                errors.append(f"arm {arm}: {len(arm_docs)}/{len(expected)} usable "
                              f"docs — not a complete arm, validation skipped")
                continue
            if lint_parsed(arm_docs, inputs_dir or DEFAULT_INPUTS, arm=True,
                           door=door) != 0:
                errors.append(f"arm {arm}: FAILED strict validation")
    return {"docs": docs, "errors": errors, "ok": not errors}


# ---------------------------------------------------------------- A1 ------
# CAPTURE AND RETRY for the one-item plan. Raw text is saved BEFORE anything is
# parsed, because the call is already spent. Basenames are mechanically
# generated ordinals: a packet id contains '#' and a lane id contains '/', and
# an untrusted identifier must never reach a path.

A1_MAX_ATTEMPTS = 2          # one primary + at most one retry, per pair


def a1_ordinals(plan):
    """The manifest's own order is the ordinal owner."""
    out, n = {}, 0
    for pk in plan["packets"]:
        for lane in pk["lanes"]:
            out[(pk["packet_id"], lane["lane_id"])] = n
            n += 1
    return out


def a1_capture(rows, out_dir, plan, attempt=1):
    """Save every received string, then classify. Returns (saved, outcomes).

    NOTHING is parsed before the write. Duplicate, unscheduled and malformed
    replies are saved too: they are paid evidence.
    """
    ordinals = a1_ordinals(plan)
    os.makedirs(out_dir, exist_ok=True)
    saved, outcomes, seen = [], [], set()
    for n, row in enumerate(rows or []):
        if not isinstance(row, dict):
            key, text = None, None
        else:
            key = (row.get("packet_id"), row.get("lane_id"))
            text = row.get("text")
        ordinal = ordinals.get(key)
        # a mechanically generated basename; never an untrusted identifier
        base = ("%05d" % ordinal) if ordinal is not None else "unscheduled%05d" % n
        path = os.path.join(out_dir, "%s.attempt%d.raw.txt" % (base, attempt))
        if os.path.exists(path):
            outcomes.append((key, "duplicate"))
            continue                      # refuse to overwrite first evidence
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text if isinstance(text, str) else "")
        saved.append(path)
        if key is None or ordinal is None:
            outcomes.append((key, "unexpected"))
        elif not isinstance(text, str) or not text.strip():
            outcomes.append((key, "spawned_without_answer"))
        elif key in seen:
            outcomes.append((key, "duplicate"))
        else:
            seen.add(key)
            outcomes.append((key, "served"))
    return saved, outcomes


def a1_account(outcomes, validity, schedule, attempt=1):
    """The exact outcome ledger. `validity` maps key -> True/False for served
    rows that were run through the sparse parser/normalizer/validator."""
    served = {k for k, o in outcomes if o == "served"}
    tag = "retried" if attempt > 1 else "served"
    acc = collections.Counter()
    for k in served:
        ok = validity.get(k)
        acc["%s_valid" % tag if ok else "%s_invalid" % tag] += 1
    for k, o in outcomes:
        if o != "served":
            acc[o] += 1
    acc["missing"] = len(set(schedule) - served) if attempt == 1 else 0
    return dict(acc)


def a1_retry_set(outcomes, validity, integrity_failures=()):
    """Only an ACTUAL response that the exact validators refuse earns a retry.

    An integrity failure, an unscheduled row, a pre-agent refusal and a tool
    violation are not bad model JSON and must not silently spend the one retry.
    """
    integrity = set(integrity_failures)
    return {k for k, o in outcomes
            if o == "served" and validity.get(k) is False and k not in integrity}


def a1_read_one(text, item, source_id, parts):
    """Raw model TEXT -> completed objects, through the EXISTING owners only.

    THE ORDER IS THE POINT, and it is the same order this module already
    enforces everywhere else:

        raw text -> parse_exact (exact numbers, duplicate keys refused)
                 -> normalize_one_item_reply (the ONE sparse normalizer, which
                    lives at the production per-item reader boundary)
                 -> the SAME validators every other reply reaches:
                    `PreparedFactV2.from_dict` (the model door) and
                    `_v2_check_reply`'s abstention contract.

    Nothing here states a shape of its own, and nothing is accepted partially:
    a single problem accepts none of the reply. Returns `(completed, problems)`.
    """
    from driver.core.driver_write_cli import (normalize_one_item_reply,
                                              _v2_check_reply, V2_REPLY_KEYS)
    from driver.core.prepared_fact_v2 import PreparedFactV2, SchemaError
    if not isinstance(text, str):
        return None, ["no reply text: %s" % type(text).__name__]
    try:
        reply = parse_exact(text)
    except RawTransportError as exc:
        return None, [str(exc)]
    completed, problems = normalize_one_item_reply(reply, item, source_id)
    if problems:
        return None, problems
    try:
        # the completed envelope, minus the transient continuity proposals the
        # frozen three-field contract does not carry (FINAL_DESIGN §5.4)
        _v2_check_reply({k: completed[k] for k in V2_REPLY_KEYS},
                        source_id, item, parts)
        for fact in completed["facts"]:
            PreparedFactV2.from_dict(fact)
    except SchemaError as exc:
        return None, [str(exc)]
    return completed, []
# ---------------------------------------------------------------- A1 ------
# THE ONE A1 ROUTE. There is no second capture/retry engine: the raw write goes
# through `save_raw`, this module's existing atomic (mode "x") owner, and the
# ordered schedule is the manifest's own packet/lane rows.
#
# The supported sequence, and the only one:
#   fresh run dir -> all-problem preflight -> launch -> save EVERY raw string
#   -> exact call-identity audit -> exact parse -> the one normalizer ->
#   complete validators -> outcome ledger -> at most one eligible retry ->
#   the same path again for that retry.

A1_MAX_ATTEMPTS = 2          # exactly one primary and at most one retry

#: What every scheduled, returned, captured and audited row must carry. A row
#: missing any of these is an INTEGRITY REFUSAL — never `served`, never retried.
A1_IDENTITY_FIELDS = ("packet_id", "lane_id", "source_id", "input_sha256",
                      "prompt_sha256", "model", "effort", "agentType")


def a1_schedule(plan):
    """The ORDERED schedule with each call's full expected identity.

    A LIST, never a set: a set collapses a duplicated packet or a repeated lane
    id and the totals then reconcile against a schedule that never existed.
    """
    inputs = {e["source_id"]: e["input_sha256"] for e in plan.get("events", [])}
    rows = []
    for pk in plan["packets"]:
        for lane in pk["lanes"]:
            rows.append({"packet_id": pk["packet_id"],
                         "lane_id": lane["lane_id"],
                         "source_id": pk["source_id"],
                         "input_sha256": inputs.get(pk["source_id"]),
                         "prompt_sha256": pk["prompt_sha256"],
                         "model": lane["model"], "effort": lane["effort"],
                         "agentType": lane["agentType"]})
    return rows


def a1_ordinals(plan):
    """The manifest's own order is the ordinal owner. A packet id contains '#'
    and a lane id contains '/', so neither may ever reach a path."""
    return {(r["packet_id"], r["lane_id"]): n
            for n, r in enumerate(a1_schedule(plan))}


def a1_identity_problems(row, want):
    """Why this returned row is not the call that was scheduled. Empty = bound.

    Every field is compared against the REVIEWED PLAN, never against the row's
    own echo of itself.
    """
    if not isinstance(row, dict):
        return ["result row is %s, not an object" % type(row).__name__]
    bad = []
    for field in A1_IDENTITY_FIELDS:
        if field not in row:
            bad.append("missing required identity field %r" % field)
        elif row[field] != want[field]:
            bad.append("%s is %r, scheduled %r" % (field, row[field], want[field]))
    return bad


def _a1_name(ordinal, attempt, dup):
    """A MECHANICALLY generated evidence basename. Never an untrusted id."""
    base = "%05d.attempt%d" % (ordinal, attempt) if ordinal is not None else \
        "unscheduled%05d.attempt%d" % (dup, attempt)
    return base


def a1_capture(rows, out_dir, plan, attempt=1):
    """Save EVERY received string, then classify. Returns (saved, outcomes).

    NOTHING is parsed before the write, and NOTHING paid is ever dropped: a
    second response for one scheduled key is written to its OWN distinct path
    and counted `duplicate`. The previous version skipped it because the first
    path already existed, so one of two paid strings vanished (Codex SEQ 1312
    item 1).
    """
    if attempt not in range(1, A1_MAX_ATTEMPTS + 1):
        raise RawTransportError(
            "attempt must be 1..%d, got %r — refused BEFORE any call or write"
            % (A1_MAX_ATTEMPTS, attempt))
    ordinals = a1_ordinals(plan)
    want = {(r["packet_id"], r["lane_id"]): r for r in a1_schedule(plan)}
    saved, outcomes, seen = [], [], {}
    for n, row in enumerate(rows or []):
        key = (row.get("packet_id"), row.get("lane_id")) \
            if isinstance(row, dict) else (None, None)
        text = row.get("text") if isinstance(row, dict) else None
        ordinal = ordinals.get(key)
        repeat = seen.get(key, 0)
        name = _a1_name(ordinal, attempt, n)
        if repeat:                      # a SECOND paid string for one key
            name += ".dup%d" % repeat
        # the paid bytes reach disk before anything interprets them
        try:
            path, _digest = save_raw(text if isinstance(text, str) else "",
                                     out_dir, name)
            saved.append(path)
        except RawTransportError as exc:
            outcomes.append((key, "write_refused", str(exc)))
            continue
        seen[key] = repeat + 1
        if ordinal is None:
            outcomes.append((key, "unexpected", "not a scheduled call"))
        elif repeat:
            outcomes.append((key, "duplicate", "a second response for one call"))
        else:
            problems = a1_identity_problems(row, want[key])
            if problems:
                outcomes.append((key, "integrity_refusal", "; ".join(problems)))
            elif not isinstance(text, str) or not text.strip():
                outcomes.append((key, "spawned_without_answer", "no text"))
            else:
                outcomes.append((key, "served", ""))
    return saved, outcomes


#: Every outcome an A1 row can have. Named here so the ledger cannot silently
#: grow a category that nothing reconciles.
A1_OUTCOMES = ("served", "duplicate", "unexpected", "spawned_without_answer",
               "integrity_refusal", "tool_violation", "pre_agent_refusal",
               "write_refused")


def a1_account(outcomes, validity, schedule, attempt=1, audit_outcomes=()):
    """The exact ledger, reconciled against the ORDERED schedule.

    `audit_outcomes` carries the rows only the WORKER AUDIT can classify — a
    tool violation and a pre-agent refusal are properties of the official
    transcript, not of the returned text — so those two categories are counted
    here by their real owner instead of being enumerated and left unreachable.
    """
    tag = "retry" if attempt > 1 else "primary"
    acc = collections.Counter()
    outcomes = list(outcomes) + list(audit_outcomes)
    served = [k for k, o, _why in outcomes if o == "served"]
    for k in served:
        acc["%s_%s" % (tag, "valid" if validity.get(k) else "invalid")] += 1
    for _k, o, _why in outcomes:
        if o != "served":
            acc[o] += 1
    if attempt == 1:
        want = [(r["packet_id"], r["lane_id"]) for r in schedule]
        answered = collections.Counter(k for k, _o, _w in outcomes)
        acc["missing"] = sum(1 for k in want if not answered.get(k))
        acc["scheduled"] = len(want)
    return dict(acc)


def a1_retry_set(outcomes, validity, audit_outcomes=()):
    """ONLY a received response the exact validators refuse earns attempt 2.

    An integrity refusal, a tool violation, a pre-agent refusal, a missing
    output and an unexpected or duplicate row are NOT bad model JSON and must
    never spend the one retry. A call the worker audit condemns is withdrawn
    even if its text happened to parse: the answer is not trustworthy evidence.
    """
    condemned = {k for k, o, _why in audit_outcomes
                 if o in ("tool_violation", "pre_agent_refusal")}
    return {k for k, o, _why in outcomes
            if o == "served" and validity.get(k) is False and k not in condemned}


def a1_read_one(text, item, source_id, parts, menu_back):
    """Raw model TEXT -> completed objects, through the EXISTING owners only.

        raw text -> parse_exact -> normalize_one_item_reply -> the SAME
        validators every other reply reaches (`PreparedFactV2.from_dict`,
        `_v2_check_reply`'s abstention contract, `_v2_check_continuity`).

    Nothing states a shape of its own and nothing is accepted partially.
    """
    from driver.core.driver_write_cli import (normalize_one_item_reply,
                                              _v2_check_reply,
                                              _v2_check_continuity,
                                              V2_REPLY_KEYS)
    from driver.core.prepared_fact_v2 import PreparedFactV2, SchemaError
    if not isinstance(text, str):
        return None, ["no reply text: %s" % type(text).__name__]
    try:
        reply = parse_exact(text)
    except RawTransportError as exc:
        return None, [str(exc)]
    completed, problems = normalize_one_item_reply(reply, item, source_id,
                                                   menu_back)
    if problems:
        return None, problems
    try:
        _v2_check_reply({k: completed[k] for k in V2_REPLY_KEYS},
                        source_id, item, parts)
        # the rename proposals are validated too — they are no longer carried
        # past the door unjudged
        _v2_check_continuity(completed["continuity_hints"], item, parts)
        for fact in completed["facts"]:
            PreparedFactV2.from_dict(fact)
    except SchemaError as exc:
        return None, [str(exc)]
    return completed, []


def a1_ingest(result, run_dir, plan, inputs_dir, attempt=1,
              audit_outcomes=()):
    """THE post-launch half of the one A1 route.

    Order, and it is the whole point: the paid bytes reach disk BEFORE anything
    is parsed, so a drifted tree or a malformed reply can never cost evidence.
    The pre-launch gate is `build_launch_manifest.preflight`, which the operator
    must run first and which is intentionally NO-GO until A2 resolves the exact
    runtime; re-running it HERE would be a second gate over already-spent calls,
    so its problems are RECORDED, never used to discard a paid response.

    Returns the run record: saved paths, outcomes, per-call validity, the
    reconciled ledger and the retry set.
    """
    import kf_lint
    rows = (result or {}).get("results") if isinstance(result, dict) else result
    saved, outcomes = a1_capture(rows, run_dir, plan, attempt)
    schedule = a1_schedule(plan)
    items = {pk["packet_id"]: pk["item"] for pk in plan["packets"]}
    sources = {pk["packet_id"]: pk["source_id"] for pk in plan["packets"]}
    menus = {e["source_id"]: e.get("menu_display_to_original", {})
             for e in plan.get("events", [])}
    by_key = {(r.get("packet_id"), r.get("lane_id")): r
              for r in (rows or []) if isinstance(r, dict)}

    validity, problems, parts_by_src = {}, {}, {}
    for key, outcome, _why in outcomes:
        if outcome != "served":
            continue
        sid = sources[key[0]]
        if sid not in parts_by_src:
            parts_by_src[sid] = kf_lint.part_lookup(sid, inputs_dir)
        completed, why = a1_read_one(by_key[key].get("text"), items[key[0]],
                                     sid, parts_by_src[sid], menus.get(sid, {}))
        validity[key] = not why
        if why:
            problems[key] = why
    return {"saved": saved, "outcomes": outcomes, "validity": validity,
            "problems": problems,
            "ledger": a1_account(outcomes, validity, schedule, attempt,
                                 audit_outcomes),
            "retry": sorted(a1_retry_set(outcomes, validity, audit_outcomes))}
# ---------------------------------------------------------------- A1 ------
# THE ONE A1 TRANSPORT. It owns nothing that already has an owner: the write is
# `save_raw` above, the reply contract is `a1_reader`, and the schedule is the
# manifest's own ordered rows. What it adds is the run: capture, identity,
# ledger and retry, for the one-item packet/lane plan.

A1_MAX_ATTEMPTS = 2          # exactly one primary and at most one retry
#: The door this route executes. The plan names it; the route refuses any other.
A1_DOOR = "one_item_sparse"

#: What every scheduled, returned, captured and audited row must carry. A row
#: missing any of these is an INTEGRITY REFUSAL — never `served`, never retried.
#: `attempt` is here because an attempt-2 answer filed as attempt 1 is a
#: different call, and `runtime_model_id` because the alias is not the runtime.
A1_IDENTITY_FIELDS = ("packet_id", "lane_id", "source_id", "input_sha256",
                      "prompt_sha256", "model", "effort", "agentType",
                      "attempt", "runtime_model_id")

#: Every outcome an A1 row can have. Named once, so the ledger cannot grow a
#: category that nothing reconciles.
A1_OUTCOMES = ("served", "duplicate", "unexpected", "spawned_without_answer",
               "integrity_refusal", "tool_violation", "pre_agent_refusal",
               "write_refused")
#: The outcomes only the worker audit can see.
A1_AUDIT_OWNED = ("tool_violation", "pre_agent_refusal")


def a1_limits(plan):
    """The three call limits, DERIVED from the frozen inventory — never read
    back from the plan's own totals, which is what let a coherent truncation
    pass (Codex SEQ 1313 item 5)."""
    import build_launch_manifest as blm
    with io.open(blm.INVENTORY, encoding="utf-8") as fh:
        records = json.load(fh)["records"]
    primary = len(records) * blm.LANES_PER_PACKET
    retries = primary * (A1_MAX_ATTEMPTS - 1)
    return {"primary_calls": primary, "retry_cap": retries,
            "all_in_max": primary + retries}


def a1_schedule(plan, attempt=1):
    """The ORDERED schedule with each call's full expected identity.

    A LIST, never a set: a set collapses a duplicated packet or a repeated lane
    id, and the totals then reconcile against a schedule that never existed.
    """
    inputs = {e["source_id"]: e["input_sha256"] for e in plan.get("events", [])}
    rows = []
    for pk in plan["packets"]:
        for lane in pk["lanes"]:
            rows.append({"packet_id": pk["packet_id"],
                         "lane_id": lane["lane_id"],
                         "source_id": pk["source_id"],
                         "input_sha256": inputs.get(pk["source_id"]),
                         "prompt_sha256": pk["prompt_sha256"],
                         "model": lane["model"], "effort": lane["effort"],
                         "agentType": lane["agentType"], "attempt": attempt,
                         "runtime_model_id": plan.get("runtime_model_id")})
    return rows


def a1_ordinals(plan):
    """The manifest's own order is the ordinal owner. A packet id contains '#'
    and a lane id contains '/', so neither may ever reach a path."""
    return {(r["packet_id"], r["lane_id"]): n
            for n, r in enumerate(a1_schedule(plan))}


def a1_identity_problems(row, want):
    """Why this returned row is not the call that was scheduled. Empty = bound.

    Every field is compared against the REVIEWED PLAN, never against the row's
    own echo of itself.
    """
    if not isinstance(row, dict):
        return ["result row is %s, not an object" % type(row).__name__]
    bad = []
    for field in A1_IDENTITY_FIELDS:
        if field not in row:
            bad.append("missing required identity field %r" % field)
        elif row[field] != want[field]:
            bad.append("%s is %r, scheduled %r" % (field, row[field],
                                                   want[field]))
    return bad


def a1_capture(rows, out_dir, plan, attempt=1):
    """Save EVERY received string, then classify. Returns (records, outcomes).

    NOTHING is parsed before the write, and NOTHING paid is dropped: a second
    response for one scheduled call is written to its OWN distinct path and
    counted `duplicate`. Each record carries the persisted path, its hash and
    the row's identity, so the ingest can parse THE PERSISTED FIRST CAPTURE
    rather than whichever row happened to be last in memory (Codex SEQ 1313
    item 2).
    """
    if (isinstance(attempt, bool) or not isinstance(attempt, int)
            or attempt not in range(1, A1_MAX_ATTEMPTS + 1)):
        raise RawTransportError(
            "attempt must be an int 1..%d, got %r — refused BEFORE any call or "
            "write" % (A1_MAX_ATTEMPTS, attempt))
    ordinals = a1_ordinals(plan)
    want = {(r["packet_id"], r["lane_id"]): r
            for r in a1_schedule(plan, attempt)}
    records, outcomes, seen = [], [], {}
    for n, row in enumerate(rows or []):
        key = (row.get("packet_id"), row.get("lane_id")) \
            if isinstance(row, dict) else (None, None)
        text = row.get("text") if isinstance(row, dict) else None
        ordinal = ordinals.get(key)
        repeat = seen.get(key, 0)
        name = ("%05d.attempt%d" % (ordinal, attempt)) if ordinal is not None \
            else "unscheduled%05d.attempt%d" % (n, attempt)
        if repeat:
            name += ".dup%d" % repeat
        try:
            path, digest = save_raw(text if isinstance(text, str) else "",
                                    out_dir, name)
        except RawTransportError as exc:
            outcomes.append((key, "write_refused", str(exc)))
            continue
        seen[key] = repeat + 1
        if ordinal is None:
            outcome, why = "unexpected", "not a scheduled call"
        elif repeat:
            outcome, why = "duplicate", "a second response for one call"
        else:
            problems = a1_identity_problems(row, want[key])
            if problems:
                outcome, why = "integrity_refusal", "; ".join(problems)
            elif not isinstance(text, str) or not text.strip():
                outcome, why = "spawned_without_answer", "no text"
            else:
                outcome, why = "served", ""
        records.append({"key": key, "path": path, "sha256": digest,
                        "ordinal": ordinal, "repeat": repeat,
                        "attempt": attempt, "outcome": outcome, "why": why,
                        "identity": {f: row.get(f) for f in A1_IDENTITY_FIELDS}
                        if isinstance(row, dict) else {}})
        outcomes.append((key, outcome, why))
    return records, outcomes


def a1_account(outcomes, validity, schedule, attempt=1, audit_outcomes=()):
    """The exact ledger, reconciled against the ORDERED schedule.

    `audit_outcomes` carries the rows only the WORKER AUDIT can classify — a
    tool violation and a pre-agent refusal are properties of the official
    transcript, not of the returned text.
    """
    tag = "retry" if attempt > 1 else "primary"
    acc = collections.Counter()
    outcomes = list(outcomes) + list(audit_outcomes)
    condemned = {k for k, o, _w in outcomes if o in A1_AUDIT_OWNED}
    for k, o, _w in outcomes:
        if o == "served":
            if k in condemned:
                continue          # the audit's verdict outranks a parsed answer
            acc["%s_%s" % (tag, "valid" if validity.get(k) else "invalid")] += 1
        else:
            acc[o] += 1
    if attempt == 1:
        want = [(r["packet_id"], r["lane_id"]) for r in schedule]
        answered = collections.Counter(k for k, _o, _w in outcomes)
        acc["missing"] = sum(1 for k in want if not answered.get(k))
        acc["scheduled"] = len(want)
    return dict(acc)


def a1_retry_set(outcomes, validity, audit_outcomes=()):
    """ONLY a received response the exact validators refuse earns attempt 2.

    An integrity refusal, a tool violation, a pre-agent refusal, a missing
    output and an unexpected or duplicate row are NOT bad model JSON and must
    never spend the one retry.
    """
    condemned = {k for k, o, _w in list(audit_outcomes) + list(outcomes)
                 if o in A1_AUDIT_OWNED}
    return {k for k, o, _w in outcomes
            if o == "served" and validity.get(k) is False and k not in condemned}


def a1_ingest(result, run_dir, plan, inputs_dir, attempt=1, audit_outcomes=(),
              only=None):
    """THE post-launch half of the one A1 route.

    Order, and it is the whole point: the paid bytes reach disk BEFORE anything
    is parsed, and what is parsed is THE PERSISTED FIRST CAPTURE for each
    scheduled call — not whichever row was last in memory. A bad first response
    followed by a good duplicate must read as a bad first response, because
    that is what the run actually produced.

    `only` is the exact `(packet_id, lane_id)` subset this launch was allowed to
    make; on a retry it is the eligible set and anything outside it is
    unscheduled. The pre-launch gate is `build_launch_manifest.preflight`.
    """
    import kf_lint
    import a1_reader
    if plan.get("door") != A1_DOOR:
        raise RawTransportError(
            "this plan names door %r; the one-item route only executes %r"
            % (plan.get("door"), A1_DOOR))
    limits = a1_limits(plan)
    full = a1_schedule(plan, attempt)
    if len(full) != limits["primary_calls"]:
        raise RawTransportError(
            "the plan schedules %d primary calls; the frozen inventory derives "
            "%d" % (len(full), limits["primary_calls"]))
    allowed = set(only) if only is not None else {(r["packet_id"], r["lane_id"])
                                                  for r in full}
    if attempt > 1 and only is None:
        raise RawTransportError(
            "a retry must name the exact eligible (packet_id, lane_id) subset")
    if len(allowed) > limits["retry_cap"] and attempt > 1:
        raise RawTransportError("the retry set exceeds the derived retry cap")
    schedule = [r for r in full if (r["packet_id"], r["lane_id"]) in allowed]

    rows = (result or {}).get("results") if isinstance(result, dict) else result
    records, outcomes = a1_capture(rows, run_dir, plan, attempt)
    items = {pk["packet_id"]: pk["item"] for pk in plan["packets"]}
    sources = {pk["packet_id"]: pk["source_id"] for pk in plan["packets"]}
    menus = {e["source_id"]: e.get("menu_display_to_original", {})
             for e in plan.get("events", [])}

    # THE PERSISTED FIRST CAPTURE per scheduled call
    first = {}
    for rec in records:
        if rec["outcome"] == "served" and rec["key"] not in first:
            first[rec["key"]] = rec
    validity, problems, parts_by_src = {}, {}, {}
    for key, rec in sorted(first.items()):
        sid = sources[key[0]]
        if sid not in parts_by_src:
            parts_by_src[sid] = kf_lint.part_lookup(sid, inputs_dir)
        with io.open(rec["path"], encoding="utf-8") as fh:
            text = fh.read()                       # FROM DISK, not from memory
        completed, why = a1_reader.read_one(text, items[key[0]], sid,
                                            menus.get(sid, {}),
                                            parts_by_src[sid])
        validity[key] = not why
        if why:
            problems[key] = why
    return {"records": records, "outcomes": outcomes, "validity": validity,
            "problems": problems, "limits": limits,
            "ledger": a1_account(outcomes, validity, schedule, attempt,
                                 audit_outcomes),
            "retry": sorted(a1_retry_set(outcomes, validity, audit_outcomes))}


#: The exact line the committed launcher carries, and the ONLY thing the
#: coordinator substitutes. A launcher whose receipt is still null cannot call.
A1_RECEIPT_LINE = "const RECEIPT = null\n"


def a1_prepare_run(run_dir, plan, only=None, attempt=1, env=None):
    """THE RUN COORDINATOR — the only path by which an agent can run.

    A successful preflight for THIS fresh run directory and these exact frozen
    bytes is required before any launcher becomes callable. On any problem it
    writes NOTHING, so nothing can be launched: the committed launchers under
    `launchers_a1/` carry `RECEIPT = null` and refuse before their first call.

    Returns `{ok, problems, launchers, receipts}`. `only` is the exact
    `(packet_id, lane_id)` subset this run may make; a retry must name it.
    """
    import build_launch_manifest as blm
    if (isinstance(attempt, bool) or not isinstance(attempt, int)
            or attempt not in range(1, A1_MAX_ATTEMPTS + 1)):
        raise RawTransportError(
            "attempt must be an int 1..%d, got %r" % (A1_MAX_ATTEMPTS, attempt))
    if attempt > 1 and not only:
        raise RawTransportError(
            "a retry must name the exact eligible (packet_id, lane_id) subset")
    limits = a1_limits(plan)
    full = [(r["packet_id"], r["lane_id"]) for r in a1_schedule(plan, attempt)]
    allowed = [c for c in full if only is None or tuple(c) in {tuple(o)
                                                              for o in only}]
    if only is not None and len(allowed) != len({tuple(o) for o in only}):
        return {"ok": False, "launchers": {}, "receipts": {},
                "problems": ["the requested subset names calls the plan does "
                             "not schedule"]}
    if not allowed:
        return {"ok": False, "launchers": {}, "receipts": {},
                "problems": ["the requested subset is empty"]}
    cap = limits["primary_calls"] if attempt == 1 else limits["retry_cap"]
    if len(allowed) > cap:
        return {"ok": False, "launchers": {}, "receipts": {},
                "problems": ["%d calls exceed the derived cap %d for attempt %d"
                             % (len(allowed), cap, attempt)]}

    problems = blm.preflight(env=env, run_dir=run_dir)
    if problems:
        # NOTHING is written: with no run-specific launcher there is nothing to
        # launch, and the committed generic launchers cannot call.
        return {"ok": False, "problems": problems, "launchers": {},
                "receipts": {}}

    derived = blm.derive_expected(plan.get("runtime_model_id"))
    by_source = collections.OrderedDict()
    for pid, lid in allowed:
        by_source.setdefault(pid.split("#")[0], []).append([pid, lid])
    events = {e["source_id"]: e for e in plan["events"]}
    out_dir = os.path.join(run_dir, "launch")
    os.makedirs(out_dir, exist_ok=True)
    launchers, receipts = {}, {}
    for sid, calls in by_source.items():
        receipt = {"source_id": sid, "attempt": attempt,
                   "input_sha256": events[sid]["input_sha256"],
                   "allowed": calls}
        text = derived["launchers"][sid]
        if A1_RECEIPT_LINE not in text:
            raise RawTransportError(
                "%s: the derived launcher carries no receipt slot" % sid)
        armed = text.replace(A1_RECEIPT_LINE,
                             "const RECEIPT = %s\n" % json.dumps(
                                 receipt, sort_keys=True), 1)
        path = os.path.join(out_dir, "kfields_a1_%s.attempt%d.js" % (sid, attempt))
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(armed)
        launchers[sid] = path
        receipts[sid] = receipt
    # THE RECEIPT the worker audit reads. `states` is filled after the run by
    # the audit owner's `record_state`, so one file carries what was authorised
    # and what actually ran.
    with io.open(os.path.join(run_dir, "receipt.json"), "w",
                 encoding="utf-8") as fh:
        json.dump({"run_id": os.path.basename(os.path.abspath(run_dir)),
                   "states": [], "attempt": attempt,
                   "allowed": [list(c) for c in allowed],
                   "receipts": receipts}, fh, indent=1, sort_keys=True)
    return {"ok": True, "problems": [], "launchers": launchers,
            "receipts": receipts}


#: The ONE canonical A1 plan. The coordinator loads THIS and executes THIS; a
#: caller-supplied plan object let a one-packet plan arm calls after the real
#: manifest had been preflighted green (Codex SEQ 1314 item 6).
def a1_plan_path():
    import build_launch_manifest as blm
    return os.path.join(blm._HERE, "launch_kfields_drafts.manifest.json")


def a1_plan():
    with io.open(a1_plan_path(), encoding="utf-8") as fh:
        return json.load(fh)


def a1_read_receipt(run_dir):
    """The receipt this run was authorised by, or a refusal."""
    path = os.path.join(run_dir, "receipt.json")
    if not os.path.isfile(path):
        raise RawTransportError("no receipt at %s — this run was never gated"
                                % path)
    with io.open(path, encoding="utf-8") as fh:
        receipt = json.load(fh)
    allowed = _pairs_of(receipt.get("allowed"))
    if allowed is None:
        raise RawTransportError(
            "receipt.allowed is not a list of (packet_id, lane_id) pairs")
    if not allowed:
        raise RawTransportError("the receipt allows no calls")
    return receipt, allowed, receipt.get("attempt")


def a1_ingest(result, run_dir, inputs_dir, audit, plan=None):
    """THE FINALIZER, and it cannot run without a completed worker audit.

        save every raw string -> audit -> fail closed on any audit problem, or
        parse ONLY audit-proved answers -> one ledger -> one exact retry subset

    `audit` is the worker audit's own result. There is no default that lets a
    caller parse or choose retries without it (Codex SEQ 1314 item 9): a reply
    whose worker was never proved is not evidence of anything.
    """
    import kf_lint
    import a1_reader
    plan = a1_plan() if plan is None else plan
    if plan.get("door") != A1_DOOR:
        raise RawTransportError(
            "this plan names door %r; the one-item route only executes %r"
            % (plan.get("door"), A1_DOOR))
    if not isinstance(audit, dict) or "problems" not in audit \
            or "outcomes" not in audit:
        raise RawTransportError(
            "the finalizer requires the worker audit's result; parsing a reply "
            "whose worker was never proved is not evidence")
    receipt, allowed, attempt = a1_read_receipt(run_dir)
    limits = a1_limits(plan)
    full = a1_schedule(plan, attempt)
    if len(full) != limits["primary_calls"]:
        raise RawTransportError(
            "the plan schedules %d primary calls; the frozen inventory derives "
            "%d" % (len(full), limits["primary_calls"]))
    schedule = [r for r in full if (r["packet_id"], r["lane_id"]) in set(allowed)]

    rows = (result or {}).get("results") if isinstance(result, dict) else result
    records, outcomes = a1_capture(rows, os.path.join(run_dir, "raw"), plan,
                                   attempt, allowed=allowed)
    audit_outcomes = [(tuple(k), o, w) for k, o, w in audit["outcomes"]]

    validity, problems = {}, {}
    if audit["problems"]:
        # FAIL CLOSED: no semantic parse and no retry when the run itself is
        # unproved. The paid bytes are already saved.
        return {"records": records, "outcomes": outcomes, "validity": {},
                "problems": {}, "limits": limits, "attempt": attempt,
                "audit_problems": list(audit["problems"]),
                "ledger": a1_account(outcomes, {}, schedule, attempt,
                                     audit_outcomes),
                "retry": []}
    proved = {k for k, o, _w in audit_outcomes if o == "served"}
    items = {pk["packet_id"]: pk["item"] for pk in plan["packets"]}
    sources = {pk["packet_id"]: pk["source_id"] for pk in plan["packets"]}
    menus = {e["source_id"]: e.get("menu_display_to_original", {})
             for e in plan.get("events", [])}
    first, parts_by_src = {}, {}
    for rec in records:
        if rec["outcome"] == "served" and rec["key"] not in first:
            first[rec["key"]] = rec
    for key, rec in sorted(first.items()):
        if key not in proved:
            continue                       # only audit-proved answers are read
        sid = sources[key[0]]
        if sid not in parts_by_src:
            parts_by_src[sid] = kf_lint.part_lookup(sid, inputs_dir)
        with io.open(rec["path"], encoding="utf-8") as fh:
            text = fh.read()               # FROM DISK, not from memory
        completed, why = a1_reader.read_one(text, items[key[0]], sid,
                                            menus.get(sid, {}),
                                            parts_by_src[sid])
        validity[key] = not why
        if why:
            problems[key] = why
    return {"records": records, "outcomes": outcomes, "validity": validity,
            "problems": problems, "limits": limits, "attempt": attempt,
            "audit_problems": [],
            "ledger": a1_account(outcomes, validity, schedule, attempt,
                                 audit_outcomes),
            "retry": sorted(a1_retry_set(outcomes, validity, audit_outcomes,
                                         attempt))}


#: The exact line the committed launcher carries, and the ONLY thing the
#: coordinator substitutes. A launcher whose receipt is still null cannot call.
A1_RECEIPT_LINE = "const RECEIPT = null\n"


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def a1_prepare_run(run_dir, only=None, attempt=1, env=None):
    """THE RUN COORDINATOR — the only path by which an agent can run.

    It LOADS AND EXECUTES the exact manifest it preflights; there is no caller
    plan argument, because preflighting one plan and arming another is not a
    gate at all. The receipt is published atomically and durably BEFORE any
    armed launcher becomes visible, so an interrupted preparation leaves nothing
    callable.
    """
    import build_launch_manifest as blm
    if (isinstance(attempt, bool) or not isinstance(attempt, int)
            or attempt not in range(1, A1_MAX_ATTEMPTS + 1)):
        raise RawTransportError(
            "attempt must be an int 1..%d, got %r" % (A1_MAX_ATTEMPTS, attempt))
    if attempt > 1 and not only:
        raise RawTransportError(
            "a retry must name the exact eligible (packet_id, lane_id) subset")
    plan = a1_plan()
    full = [(r["packet_id"], r["lane_id"]) for r in a1_schedule(plan, attempt)]
    scheduled = set(full)
    # ORDERED VALIDATION FIRST, before any set conversion
    bad = a1_pair_problems(only, scheduled, attempt)
    if bad:
        return {"ok": False, "problems": bad, "launchers": {}, "receipts": {}}
    allowed = [tuple(c) for c in only] if only is not None else list(full)
    limits = a1_limits(plan)
    cap = limits["primary_calls"] if attempt == 1 else limits["retry_cap"]
    if len(allowed) > cap:
        return {"ok": False, "launchers": {}, "receipts": {},
                "problems": ["%d calls exceed the derived cap %d for attempt %d"
                             % (len(allowed), cap, attempt)]}

    problems = blm.preflight(env=env, run_dir=run_dir)
    if problems:
        return {"ok": False, "problems": problems, "launchers": {},
                "receipts": {}}

    derived = blm.derive_expected(plan.get("runtime_model_id"))
    by_source = collections.OrderedDict()
    for pid, lid in allowed:
        by_source.setdefault(pid.split("#")[0], []).append([pid, lid])
    events = {e["source_id"]: e for e in plan["events"]}
    staging = os.path.join(run_dir, ".launch.partial")
    final_dir = os.path.join(run_dir, "launch")
    os.makedirs(staging, exist_ok=True)
    launchers, receipts = {}, {}
    for sid, calls in by_source.items():
        receipt = {"source_id": sid, "attempt": attempt,
                   "input_sha256": events[sid]["input_sha256"],
                   "allowed": calls}
        text = derived["launchers"][sid]
        if A1_RECEIPT_LINE not in text:
            raise RawTransportError(
                "%s: the derived launcher carries no receipt slot" % sid)
        armed = text.replace(A1_RECEIPT_LINE,
                             "const RECEIPT = %s\n" % json.dumps(
                                 receipt, sort_keys=True), 1)
        name = "kfields_a1_%s.attempt%d.js" % (sid, attempt)
        with io.open(os.path.join(staging, name), "w", encoding="utf-8") as fh:
            fh.write(armed)
            fh.flush()
            os.fsync(fh.fileno())
        launchers[sid] = os.path.join(final_dir, name)
        receipts[sid] = receipt
    _fsync_dir(staging)
    # THE RECEIPT IS DURABLE BEFORE ANYTHING IS CALLABLE
    rpath = os.path.join(run_dir, "receipt.json")
    tmp = rpath + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"run_id": os.path.basename(os.path.abspath(run_dir)),
                   "states": [], "attempt": attempt,
                   "allowed": [list(c) for c in allowed],
                   "receipts": receipts}, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, rpath)
    _fsync_dir(run_dir)
    os.rename(staging, final_dir)          # only NOW is a launcher callable
    _fsync_dir(run_dir)
    return {"ok": True, "problems": [], "launchers": launchers,
            "receipts": receipts, "allowed": [list(c) for c in allowed]}


def a1_finalize(run_dir):
    """The PRE-1319 order: plan and door FIRST, evidence after."""
    import build_launch_manifest as blm
    import audit_worker_access as AUD
    plan = a1_plan()
    if plan.get("door") != A1_DOOR:
        raise RawTransportError(
            "this plan names door %r; the one-item route only executes %r"
            % (plan.get("door"), A1_DOOR))
    receipt, state_paths, loose = a1_load_receipt_loosely(run_dir)
    attempt = receipt.get("attempt") if isinstance(receipt, dict) else None
    attempt = attempt if attempt in (1, 2) else 1
    canonical = a1_canonical_calls(plan, attempt)

    records = a1_preserve(a1_readable_rows(state_paths),
                          os.path.join(run_dir, "raw"), attempt)

    problems = [loose] if loose else []
    if not problems:
        problems += a1_run_contract_problems(receipt, run_dir, plan)
    allowed = _pairs_of(receipt.get("allowed")) if isinstance(receipt, dict) \
        else None
    allowed = allowed if allowed is not None else []
    outcomes = a1_classify_rows(records, plan, attempt, allowed)

    audit_outcomes = []
    if not problems:
        audit = AUD.audit(os.path.join(run_dir, "receipt.json"))
        problems += list(audit["problems"])
        audit_outcomes = [(tuple(k), o, w) for k, o, w in audit["outcomes"]]
        problems += blm.protected_pin_problems(plan)
        for e in plan.get("events", []):
            live = os.path.join(blm._REPO, e["input_path"])
            if not os.path.isfile(live):
                problems.append("%s: input is missing" % e["source_id"])
            elif _sha_file(live) != e["input_sha256"]:
                problems.append("%s: live input bytes are not the plan's"
                                % e["source_id"])
    else:
        audit = {"answers": {}}

    validity, why_by_key = {}, {}
    if not problems:
        import kf_lint
        import a1_reader
        answers = audit["answers"]
        answers = {tuple(k): v for k, v in (answers.items()
                                            if isinstance(answers, dict)
                                            else answers)}
        items = {pk["packet_id"]: pk["item"] for pk in plan["packets"]}
        sources = {pk["packet_id"]: pk["source_id"] for pk in plan["packets"]}
        menus = {e["source_id"]: e.get("menu_display_to_original", {})
                 for e in plan.get("events", [])}
        ordinals = a1_ordinals(plan)
        parts_by_src = {}
        for key in [c for c in allowed if c in answers]:
            sid = sources[key[0]]
            if sid not in parts_by_src:
                parts_by_src[sid] = kf_lint.part_lookup(sid, blm.INPUTS)
            path, _d = save_raw(answers[key],
                                os.path.join(run_dir, "answers"),
                                "%05d.attempt%d.complete"
                                % (ordinals[key], attempt))
            with io.open(path, encoding="utf-8") as fh:
                text = fh.read()
            completed, why = a1_reader.read_one(text, items[key[0]], sid,
                                                menus.get(sid, {}),
                                                parts_by_src[sid])
            validity[key] = not why
            if why:
                why_by_key[key] = why

    graded = a1_classify(outcomes, validity, audit_outcomes, bool(problems))
    scope = allowed if (allowed and not problems) else canonical
    final = collections.OrderedDict()
    for c in scope:
        final[c] = graded.get(c, "missing")
    for k, v in graded.items():
        final.setdefault(k, v)
    ledger = a1_ledger(final, validity, len(scope), attempt)
    retry = [] if problems else a1_retry_set(final, validity, allowed, attempt)
    doc = {"run_id": receipt.get("run_id") if isinstance(receipt, dict) else None,
           "manifest_sha256": _sha_file(a1_plan_path()),
           "receipt_sha256": _sha_file(os.path.join(run_dir, "receipt.json")),
           "attempt": attempt, "ledger": ledger,
           "audit_problems": problems,
           "classification": [[list(k), v] for k, v in final.items()],
           "validity": [[list(k), validity[k]] for k in final
                        if k in validity and final[k] == "served"],
           "retry": [list(k) for k in retry]}
    _atomic_json(os.path.join(run_dir, FINALIZATION_NAME), doc)
    return {"records": records, "outcomes": outcomes, "validity": validity,
            "problems": why_by_key, "audit_problems": problems,
            "classification": doc["classification"], "limits": a1_limits(plan),
            "attempt": attempt, "ledger": ledger, "retry": doc["retry"]}
