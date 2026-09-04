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
import collections
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


def _raw_filename(name):
    """The one place a raw stem becomes a filename: the writer and the raw-row
    binding owner both name files through it (Codex SEQ 1483 item 2)."""
    return f"{name}.raw.json"


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
    path = os.path.join(out_dir, _raw_filename(name))
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
#: The runtime itself added input mid-call, so the continued text is not a
#: clean single-shot answer. It earns no credit and exactly one fresh
#: attempt, unlike an integrity refusal (Codex SEQ 1349 item 2). THIS is
#: the one place the string exists; everything below names it.
A1_INVALID_RESPONSE = "invalid_response"
A1_OUTCOMES = ("served", "duplicate", "unexpected", "spawned_without_answer",
               "integrity_refusal", "tool_violation", "pre_agent_refusal",
               "write_refused", A1_INVALID_RESPONSE)
#: The outcomes only the worker audit can see.
A1_AUDIT_OWNED = ("tool_violation", "pre_agent_refusal", A1_INVALID_RESPONSE)


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


def a1_pair_problems(only, scheduled, attempt):
    """Why this requested subset is not a lawful ORDERED pair list.

    Checked BEFORE any set conversion. `{(p, l), (p, l)}` collapses to one
    element, so a duplicate request used to arm cleanly (Codex SEQ 1314 item 1).
    """
    bad = []
    if only is None:
        return bad
    if not isinstance(only, (list, tuple)) or not only:
        return ["the requested subset must be a non-empty ordered list"]
    seen = []
    for n, pair in enumerate(only):
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or not all(isinstance(x, str) for x in pair)):
            bad.append("subset entry %d is not a (packet_id, lane_id) pair" % n)
            continue
        key = (pair[0], pair[1])
        if key in seen:
            bad.append("subset repeats %s at entry %d" % (key, n))
        seen.append(key)
        if key not in scheduled:
            bad.append("subset entry %d names %s, which the plan does not "
                       "schedule at attempt %d" % (n, key, attempt))
    return bad


def a1_readable_rows(state_paths):
    """EVERY readable result row from these official states, in order.

    Defensive on purpose: a malformed state must cost nothing, because these
    rows are paid bytes and they are harvested BEFORE any contract, identity or
    prompt check can exit (Codex SEQ 1318 item C).
    """
    rows = []
    for path in state_paths or []:
        if not isinstance(path, str) or not os.path.isfile(path):
            continue
        try:
            with io.open(path, encoding="utf-8") as fh:
                st = json.load(fh)
        except Exception:                             # noqa: BLE001 - by design
            continue
        if not isinstance(st, dict):
            continue
        result = st.get("result")
        if not isinstance(result, dict):
            continue
        found = result.get("results")
        if not isinstance(found, list):
            continue                       # nothing readable here to preserve
        for row in found:
            rows.append(row)
    return rows


def a1_raw_bindings(rows, attempt):
    """THE ONE raw-row binding owner (Codex SEQ 1483 item 2).

    -> [(stem, text)] for every official row, in order: the exact stem
    `a1_preserve` hands `save_raw` and the exact text `save_raw` writes. A row
    with no string text is preserved as the empty string, and that rule lives
    here and nowhere else - the writer and the ledger's verifier both read
    it, so neither can drift from what was actually written.
    """
    out = []
    for n, row in enumerate(rows or []):
        text = row.get("text") if isinstance(row, dict) else None
        out.append(("%05d.attempt%s" % (n, attempt),
                    text if isinstance(text, str) else ""))
    return out


def a1_raw_binding_problems(run_dir, rows, attempt):
    """Why `<run_dir>/raw` is not EXACTLY what `a1_preserve` wrote for these
    official rows at this attempt: the filename set must be exactly the
    expected one, and every file's bytes must equal its row's text bytes.

    Comparing a file COUNT to a row count proved no binding at all: an edited
    file, or two files with their contents swapped, still counted as the paid
    answers (Codex SEQ 1483). Empty = every row is bound.
    """
    raw_dir = os.path.join(run_dir, "raw")
    bindings = a1_raw_bindings(rows, attempt)
    expected = [_raw_filename(stem) for stem, _text in bindings]
    actual = sorted(os.listdir(raw_dir)) if os.path.isdir(raw_dir) else []
    if actual != sorted(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        return ["the raw directory holds %d file(s) for %d official row(s): "
                "%d expected name(s) missing %s, %d unexpected %s"
                % (len(actual), len(expected), len(missing), missing[:2],
                   len(extra), extra[:2])]
    bad = []
    for (stem, text), name in zip(bindings, expected):
        with io.open(os.path.join(raw_dir, name), "rb") as fh:
            got = fh.read()
        if got != text.encode("utf-8"):
            bad.append("%s does not hold the official row's text bytes" % name)
    return bad


def a1_preserve(rows, out_dir, attempt):
    """Save every received string. THE ONLY WRITER, and it needs nothing but
    the rows: no schedule, no `allowed`, no semantic import. What it writes is
    exactly what `a1_raw_bindings` names, so the ledger can later verify every
    file against the official row it came from."""
    records = []
    for n, (row, (stem, text)) in enumerate(zip(rows or [],
                                                a1_raw_bindings(rows, attempt))):
        try:
            path, digest = save_raw(text, out_dir, stem)
        except RawTransportError as exc:
            records.append({"index": n, "row": row, "path": None,
                            "sha256": None, "write_error": str(exc)})
            continue
        records.append({"index": n, "row": row, "path": path,
                        "sha256": digest, "write_error": None})
    return records


def a1_classify_rows(records, plan, attempt, allowed):
    """Classify already-PRESERVED rows against the receipt's schedule.

    Writing and judging are separate: nothing here can cost a paid byte.
    """
    want = {} if plan is None else {(r["packet_id"], r["lane_id"]): r
                                    for r in a1_schedule(plan, attempt)}
    permitted = [tuple(c) for c in allowed]
    seen, outcomes = {}, []
    for rec in records:
        row = rec["row"]
        pid = row.get("packet_id") if isinstance(row, dict) else None
        lid = row.get("lane_id") if isinstance(row, dict) else None
        # ONLY A PAIR OF STRINGS IS AN IDENTITY. A list-valued id is not
        # hashable, so hashing it here crashed the whole closeout instead of
        # refusing one row (Codex SEQ 1319 item B).
        key = (pid, lid) if isinstance(pid, str) and isinstance(lid, str) \
            else (None, None)
        text = row.get("text") if isinstance(row, dict) else None
        if rec["write_error"]:
            outcomes.append((key, "write_refused", rec["write_error"]))
            continue
        repeat = seen.get(key, 0)
        seen[key] = repeat + 1
        if key not in permitted:
            outcomes.append((key, "unexpected", "not a call this receipt allows"))
        elif key not in want:
            outcomes.append((key, "unexpected", "the receipt allows a call "
                             "this plan does not schedule"))
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
    return outcomes


def a1_classify(outcomes, validity, audit_outcomes=(), audit_failed=False):
    """ONE final classification per key; the audit outranks the capture."""
    verdict = {k: o for k, o, _w in audit_outcomes if o != "served"}
    captured = {k for k, _o, _w in outcomes}
    final = collections.OrderedDict()
    for k, o, _w in outcomes:
        if k in verdict:
            final[k] = ("integrity_refusal"
                        if verdict[k] == "spawned_without_answer"
                        and k in captured else verdict[k])
        elif o in ("served", "spawned_without_answer") and audit_failed:
            final[k] = "integrity_refusal"
        elif k in final and final[k] != "duplicate" and o == "duplicate":
            continue
        else:
            final.setdefault(k, o)
    for k, o in verdict.items():
        final.setdefault(k, o)
    return final


#: The EXACT top-level receipt keys, per attempt. Extras are refused.
A1_RECEIPT_TOP = ("run_id", "states", "attempt", "manifest_sha256",
                  "max_output_tokens", "allowed", "receipts", "invocations")
A1_PARENT = ("run_id", "receipt_sha256", "finalization_sha256")
A1_FINALIZATION = ("run_id", "manifest_sha256", "receipt_sha256", "attempt",
                   "ledger", "audit_problems", "classification", "validity",
                   "retry")


PLAN_DIRNAME = "plan"


def a1_plan_for_run(run_dir):
    """THE plan THIS run was published under.

    A door that is not K-fields persists its own complete transport plan in
    `<run>/plan/`, so the run directory itself says which door it is. The
    contract, the auditor and the finalizer therefore resolve the same plan
    with no caller argument, no registry and no dynamic import (Codex SEQ 1404
    items 1 and 2). A run with no such file is K-fields.
    """
    run_dir = os.path.abspath(run_dir or ".")
    # A RETRY IS ITS PRIMARY'S CHILD, so it runs the primary's exact plan. The
    # child persists no second copy: a plan it could carry on its own is a plan
    # that could disagree with the one the paid primary was published under.
    if os.path.basename(run_dir) == RETRY_DIRNAME:
        parent = os.path.dirname(run_dir)
        if os.path.isdir(os.path.join(parent, PLAN_DIRNAME)):
            return a1_plan_for_run(parent)
    pdir = os.path.join(run_dir, PLAN_DIRNAME)
    if not os.path.isdir(pdir):
        # ONLY AN ABSENT PLAN DIRECTORY IS K-FIELDS. That door persists no
        # plan, so its absence is the signal - and it is the only lawful one.
        return a1_plan()
    # A PRESENT PLAN DIRECTORY MUST YIELD EXACTLY ONE PLAN. Skipping a
    # malformed document and then falling back answered a run's questions from
    # the DEFAULT K-fields plan while that run's own plan sat there broken:
    # the caller could not tell a corrupt plan from a door that has none, and
    # the wrong plan reads as success (Codex SEQ 1470 item 2).
    found, names = [], sorted(n for n in os.listdir(pdir)
                              if n.endswith(".json"))
    if not names:
        raise RawTransportError(
            "%s holds no plan document, so this run's plan cannot be "
            "resolved; only a run with NO plan directory is K-fields" % pdir)
    for name in names:
        path = os.path.join(pdir, name)
        try:
            with io.open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except ValueError as exc:
            raise RawTransportError(
                "%s is not readable json (%s); a run's own plan is never "
                "skipped in favour of the default" % (path, exc))
        if isinstance(doc, dict) and isinstance(doc.get("events"), list) \
                and isinstance(doc.get("packets"), list):
            found.append((name, doc))
    if not found:
        raise RawTransportError(
            "%s holds %d json document(s), none of them a transport plan: %s"
            % (pdir, len(names), names[:3]))
    if len(found) > 1:
        raise RawTransportError(
            "%s holds %d transport plans (%s); which one a run was published "
            "under must never be decided by sort order"
            % (pdir, len(found), [n for n, _d in found][:3]))
    return found[0][1]


def a1_plan_identity(plan):
    """(manifest path, launcher prefix) for THIS plan.

    A door's own plan carries its identity, so publication, the run contract,
    the auditor and the finalizer all resolve the same pair from the same
    object without a registry, a dynamic import or a caller-supplied override
    (Codex SEQ 1404 items 1 and 2). A plan that names neither is K-fields.
    """
    plan = a1_plan() if plan is None else plan
    path = (plan or {}).get("manifest_path") or a1_plan_path()
    prefix = (plan or {}).get("launcher_prefix") or "kfields_a1_"
    return path, prefix


def a1_expected_receipt(run_dir, allowed, attempt, parent=None, plan=None,
                        plan_path=None, launcher_prefix=None):
    """THE ONE expected receipt for a run of this exact shape.

    The publisher BUILDS from this and the validator COMPARES to it, so there
    is exactly one description of a lawful receipt (Codex SEQ 1318 item A).
    """
    import build_launch_manifest as blm
    plan = a1_plan() if plan is None else plan
    _path, _prefix = a1_plan_identity(plan)
    plan_path = _path if plan_path is None else plan_path
    launcher_prefix = _prefix if launcher_prefix is None else launcher_prefix
    events = {e["source_id"]: e for e in plan["events"]}
    final_dir = os.path.join(run_dir, "launch")
    receipts, invocations = {}, []
    for sid in a1_source_order(allowed):
        calls = a1_projection(allowed, sid)
        path = os.path.join(final_dir,
                            "%s%s.attempt%d.js" % (launcher_prefix, sid,
                                                   attempt))
        receipts[sid] = {"source_id": sid, "attempt": attempt,
                         "input_sha256": events[sid]["input_sha256"],
                         "max_output_tokens": blm.MAX_OUTPUT_TOKENS_SETTING,
                         "launcher_path": path,
                         "allowed": [list(c) for c in calls]}
        invocations.append({"source_id": sid, "scriptPath": path,
                            "args": a1_args_for(plan, calls, attempt)})
    doc = {"run_id": os.path.basename(os.path.abspath(run_dir)),
           "states": [], "attempt": attempt,
           "manifest_sha256": _sha_file(plan_path),
           "max_output_tokens": blm.MAX_OUTPUT_TOKENS_SETTING,
           "allowed": [list(c) for c in allowed],
           "receipts": receipts, "invocations": invocations}
    if parent is not None:
        doc["parent"] = parent
    return doc


def _exact_keys(obj, keys, where, bad):
    if not isinstance(obj, dict):
        bad.append("%s is %s, not an object" % (where, type(obj).__name__))
        return False
    # `sorted` on a mixed str/int key set raises; a shape door must never
    # crash on the shape it exists to refuse (Codex SEQ 1319 item B).
    extra = sorted(repr(k) for k in set(obj) - set(keys))
    missing = sorted(repr(k) for k in set(keys) - set(obj))
    if extra or missing:
        bad.append("%s keys are not exactly %s (extra %s, missing %s)"
                   % (where, list(keys), extra, missing))
        return False
    return True


def a1_run_contract_problems(receipt, run_dir, plan=None):
    """THE attempt-specific run contract, exact and typed.

    Publication, direct audit and finalization all call THIS. A field that is
    changed, extra, mistyped or coherent-but-wrong refuses here, once.
    """
    plan = a1_plan_for_run(run_dir) if plan is None else plan
    bad = []
    if not isinstance(receipt, dict):
        return ["the receipt is %s, not an object" % type(receipt).__name__]
    attempt = receipt.get("attempt")
    if isinstance(attempt, bool) or not isinstance(attempt, int) \
            or attempt not in range(1, A1_MAX_ATTEMPTS + 1):
        return ["the receipt names attempt %r" % (attempt,)]
    want_keys = A1_RECEIPT_TOP + (("parent",) if attempt > 1 else ())
    if not _exact_keys(receipt, want_keys, "the receipt", bad):
        return bad
    if not isinstance(receipt["states"], list) or \
            any(not isinstance(s, str) for s in receipt["states"]):
        bad.append("receipt.states is not a list of paths")
    allowed = _pairs_of(receipt.get("allowed"))
    if allowed is None:
        return bad + ["receipt.allowed is not a list of (packet, lane) pairs"]
    canonical = a1_canonical_calls(plan, attempt)
    keep = set(allowed)
    if len(keep) != len(allowed) or allowed != [c for c in canonical
                                                if c in keep]:
        bad.append("receipt.allowed is not the canonical order filtered")
        return bad
    if attempt == 1 and allowed != canonical:
        bad.append("attempt 1 is not the COMPLETE canonical primary schedule: "
                   "%d of %d calls" % (len(allowed), len(canonical)))
        return bad
    parent = receipt.get("parent") if attempt > 1 else None
    if attempt > 1:
        if not _exact_keys(parent, A1_PARENT, "receipt.parent", bad):
            return bad
        if any(not isinstance(parent[k], str) or not parent[k]
               for k in A1_PARENT):
            bad.append("receipt.parent carries a non-string identity")
            return bad
    # ONE TYPED WHOLE-FIELD COMPARISON. The expected receipt already builds the
    # exact nested dicts and lists, so the second nested walk proved nothing
    # extra and crashed on a scalar `receipts` or `invocations` before it could
    # refuse them; it is gone (Codex SEQ 1319 item B). The container type comes
    # from the EXPECTED value, so nothing here names a field or a kind.
    want = a1_expected_receipt(run_dir, allowed, attempt, parent, plan)
    for field in A1_RECEIPT_TOP:
        if field == "states":
            continue                       # grows as the run is recorded
        if not isinstance(receipt[field], type(want[field])):
            bad.append("receipt.%s is %s, not the %s a lawful run carries"
                       % (field, type(receipt[field]).__name__,
                          type(want[field]).__name__))
        elif receipt[field] != want[field]:
            bad.append("receipt.%s is not what a lawful run of this shape "
                       "carries" % field)
    if attempt > 1:
        bad += _a1_child_problems(run_dir, receipt, plan)
    return bad


def _a1_child_problems(run_dir, receipt, plan):
    """Why this attempt-2 run is not the ONE lawful child of its primary."""
    bad = []
    if os.path.basename(os.path.abspath(run_dir)) != RETRY_DIRNAME:
        return ["a retry lives only at the fixed %r child of its primary"
                % RETRY_DIRNAME]
    primary = os.path.dirname(os.path.abspath(run_dir))
    fpath = os.path.join(primary, FINALIZATION_NAME)
    rpath = os.path.join(primary, "receipt.json")
    if not os.path.isfile(fpath) or not os.path.isfile(rpath):
        return ["the primary run's receipt or finalization is missing"]
    try:
        with io.open(fpath, encoding="utf-8") as fh:
            fin = json.load(fh)
    except Exception as exc:                          # noqa: BLE001 - by design
        return ["the primary finalization is unreadable: %s" % exc]
    bad += a1_primary_evidence_problems(fin, plan, primary)
    parent = receipt.get("parent")
    if not isinstance(parent, dict):
        return bad + ["receipt.parent is %s, not an object"
                      % type(parent).__name__]
    for field, value in (("run_id", fin.get("run_id")),
                         ("receipt_sha256", _sha_file(rpath)),
                         ("finalization_sha256", _sha_file(fpath))):
        if parent.get(field) != value:
            bad.append("the child's parent %s does not bind its primary"
                       % field)
    if not bad:
        want = a1_primary_retry_keys(fin, plan)
        got = _pairs_of(receipt.get("allowed")) or []
        if got != want:
            bad.append("the child's calls are not the invalid-only canonical "
                       "filter its primary derives")
    return bad


def _a1_keyed(rows):
    """`[[[packet, lane], value], ...]` -> `{(packet, lane): value}`.

    Malformed rows are dropped, never raised on: this reads a file another
    process wrote, and the callers refuse it on the shape, not on a traceback.
    """
    out = {}
    for r in rows or []:
        if isinstance(r, (list, tuple)) and len(r) == 2 \
                and isinstance(r[0], (list, tuple)) and len(r[0]) == 2 \
                and all(isinstance(x, str) for x in r[0]):
            out[(r[0][0], r[0][1])] = r[1]
    return out


def a1_primary_retry_keys(fin, plan=None):
    """The invalid-only canonical filter, RECOMPUTED from a finalization.

    It does not re-encode the filter: `a1_retry_set` is the sole owner, and a
    second copy is exactly how the two could drift (Codex SEQ 1319 item C).
    """
    plan = a1_plan() if plan is None else plan
    return a1_retry_set(_a1_keyed(fin.get("classification")),
                        _a1_keyed(fin.get("validity")),
                        a1_canonical_calls(plan, 1), 1)


def a1_primary_evidence_problems(fin, plan=None, primary_dir=None):
    """Why this finalization is not a COMPLETE, clean, exactly typed PRIMARY
    of this exact run. The attempt-1 case of `a1_finalization_problems`."""
    return a1_finalization_problems(fin, plan, primary_dir, attempt=1)


def a1_finalization_problems(fin, plan=None, run_dir=None, attempt=1,
                             expected_keys=None):
    """Why this finalization is not a COMPLETE, clean, exactly typed record
    of this exact run at THIS attempt.

    `run_dir` is the directory the finalization claims to close out. Without it
    the record was only ever checked against itself, so forging `run_id`,
    `manifest_sha256` or `receipt_sha256` still armed a retry (SEQ 1319 item C).

    ONE VALIDATOR FOR BOTH ATTEMPTS (Codex SEQ 1471 item 2). A consumer that
    only HASHED these files trusted their fields, so a finalization could
    contradict itself - classifications deriving an owed retry beside an empty
    `retry` list - and still be selected from. `expected_keys` is the key set
    this attempt must classify; a retry closes out only the keys it was armed
    for, not the whole schedule.
    """
    plan = a1_plan() if plan is None else plan
    primary_dir = run_dir
    bad = []
    if not _exact_keys(fin, A1_FINALIZATION, "the finalization", bad):
        return bad
    if isinstance(fin.get("attempt"), bool) or fin.get("attempt") != attempt:
        bad.append("the finalization is for attempt %r, not the expected %d"
                   % (fin.get("attempt"), attempt))
    if not isinstance(fin.get("audit_problems"), list):
        bad.append("finalization.audit_problems is not a list")
    elif fin["audit_problems"]:
        bad.append("attempt %d did not audit clean; there is nothing lawful "
                   "to select from it" % attempt)
    led = fin.get("ledger")
    if not isinstance(led, dict):
        bad.append("finalization.ledger is not an object")
    elif any(not isinstance(k, str) or isinstance(v, bool)
             or not isinstance(v, int) for k, v in led.items()):
        # `True == 1`, so a boolean count reconciles against an integer one
        bad.append("finalization.ledger is not string names to real integers")
    for field in ("run_id", "manifest_sha256", "receipt_sha256"):
        if not isinstance(fin.get(field), str) or not fin[field]:
            bad.append("finalization.%s is not a nonblank string" % field)
    if bad:
        return bad
    if primary_dir is not None:
        rpath = os.path.join(primary_dir, "receipt.json")
        if fin["run_id"] != os.path.basename(os.path.abspath(primary_dir)):
            bad.append("the finalization names run %r, not the directory it "
                       "closes out" % fin["run_id"])
        # the SAME resolver the finalizer stamped it with; a run without a
        # private plan still resolves to the committed A1 manifest path
        if fin["manifest_sha256"] != _sha_file(a1_plan_identity(plan)[0]):
            bad.append("the finalization was written against different plan "
                       "bytes than the ones live now")
        if not os.path.isfile(rpath):
            bad.append("the primary run has no receipt to bind to")
        elif fin["receipt_sha256"] != _sha_file(rpath):
            bad.append("the finalization does not bind this run's receipt "
                       "bytes")
        if bad:
            return bad
    canonical = (list(expected_keys) if expected_keys is not None
                 else a1_canonical_calls(plan, attempt))
    rows = fin.get("classification")
    if not isinstance(rows, list):
        return bad + ["finalization.classification is not a list"]
    keys = _pairs_of([r[0] for r in rows
                      if isinstance(r, (list, tuple)) and len(r) == 2])
    if keys is None or len(keys) != len(rows):
        return bad + ["finalization.classification holds a malformed row"]
    if keys != canonical:
        return bad + ["the finalization classifies %d keys, not the complete "
                      "canonical %d in order" % (len(keys), len(canonical))]
    outcomes = [r[1] for r in rows]
    if any(not isinstance(o, str) for o in outcomes):
        return bad + ["finalization.classification holds a non-string outcome"]
    unknown = sorted(set(outcomes) - set(A1_OUTCOMES) - {"missing"})
    if unknown:
        return bad + ["finalization.classification names outcomes no owner "
                      "declares: %s" % unknown]
    vrows = fin.get("validity")
    if not isinstance(vrows, list):
        return bad + ["finalization.validity is not a list"]
    vkeys = _pairs_of([r[0] for r in vrows
                       if isinstance(r, (list, tuple)) and len(r) == 2])
    if vkeys is None or len(vkeys) != len(vrows):
        return bad + ["finalization.validity holds a malformed row"]
    served = [c for c, o in zip(keys, outcomes) if o == "served"]
    if vkeys != served:
        return bad + ["finalization.validity is not exactly the served keys in "
                      "canonical order"]
    if any(not isinstance(r[1], bool) for r in vrows):
        return bad + ["finalization.validity holds a non-boolean"]
    stored = _pairs_of(fin.get("retry"))
    if stored is None:
        return bad + ["finalization.retry is not a list of pairs"]
    if attempt == 1:
        if stored != a1_primary_retry_keys(fin, plan):
            return bad + ["the stored retry list is not the invalid-only set "
                          "this run's own classifications derive"]
    elif stored:
        # attempt 2 is the last one; it can never derive a third
        return bad + ["a retry finalization names %d further retries; attempt "
                      "2 can never create attempt 3" % len(stored)]
    # the ledger must be the accounting owner's own recomputation
    validity = dict((tuple(r[0]), r[1]) for r in vrows)
    final = collections.OrderedDict(zip(keys, outcomes))
    if fin["ledger"] != a1_ledger(final, validity, len(canonical), attempt):
        return bad + ["finalization.ledger is not the accounting owner's "
                      "recomputation of its own classifications"]
    return bad


def a1_ledger(final, validity, scheduled, attempt):
    """THE one accounting owner. Nothing counts anywhere else."""
    tag = "retry" if attempt > 1 else "primary"
    acc = collections.Counter()
    for k, o in final.items():
        if o == "served":
            acc["%s_%s" % (tag, "valid" if validity.get(k) else "invalid")] += 1
        elif o != "missing":
            acc[o] += 1
    acc["scheduled"] = scheduled
    acc["missing"] = sum(1 for o in final.values() if o == "missing")
    return dict(acc)


RETRY_DIRNAME = "retry"
FINALIZATION_NAME = "finalization.json"
#: The exact line the committed launcher carries, and the ONLY substitution.
A1_RECEIPT_LINE = "const RECEIPT = null\n"


def _pairs_of(seq):
    """`[[p, l], ...]` -> `[(p, l), ...]`, or None if any entry is not a pair."""
    if not isinstance(seq, list):
        return None
    out = []
    for c in seq:
        if not isinstance(c, (list, tuple)) or len(c) != 2 \
                or not all(isinstance(x, str) for x in c):
            return None
        out.append((c[0], c[1]))
    return out


def _sha_file(path):
    with io.open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path, text):
    """Atomic AND write-once: it REFUSES to replace an existing file.

    `tmp` + `os.replace` is atomic REPLACEMENT, not write-once - two builders
    can both pass a freshness check and then silently overwrite each other's
    plan bytes, and the loser never learns. `os.link` fails if the target
    exists, so the first writer wins and the second is told (Codex SEQ 1471
    item 1). This lives here because it is the lowest owner both the A5 kit
    and the A7 builders already import.
    """
    tmp = "%s.partial.%d" % (path, os.getpid())
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
    except OSError:
        os.unlink(tmp)
        raise ValueError("%s already exists; a published plan is never "
                         "overwritten" % path)
    os.unlink(tmp)
    _fsync_dir(os.path.dirname(os.path.abspath(path)))


def _atomic_json(path, payload):
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_dir(os.path.dirname(os.path.abspath(path)))


def a1_plan_path():
    import build_launch_manifest as blm
    return os.path.join(blm._HERE, "launch_kfields_drafts.manifest.json")


def a1_plan():
    with io.open(a1_plan_path(), encoding="utf-8") as fh:
        return json.load(fh)


def a1_canonical_calls(plan, attempt=1):
    """The CANONICAL ordered call list. Never sorted, never regrouped."""
    return [(r["packet_id"], r["lane_id"]) for r in a1_schedule(plan, attempt)]


def a1_projection(calls, source_id):
    """This source's calls, in the canonical order they appear."""
    return [c for c in calls if c[0].split("#")[0] == source_id]


def a1_source_order(calls):
    """Source keys by FIRST ENCOUNTER in the canonical order."""
    out = []
    for pid, _lid in calls:
        sid = pid.split("#")[0]
        if sid not in out:
            out.append(sid)
    return out


def a1_args_for(plan, calls, attempt):
    """THE ONE Workflow-args serializer, and it lives here, not in a caller."""
    by_pid = {pk["packet_id"]: pk for pk in plan["packets"]}
    order, want = [], collections.OrderedDict()
    for pid, lid in calls:
        if pid not in want:
            order.append(pid)
            want[pid] = []
        want[pid].append(lid)
    rows = []
    for pid in order:
        pk = by_pid[pid]
        planned = [l["lane_id"] for l in pk["lanes"]]
        base = {"attempt": attempt, "input_path": pk["input_path"],
                "packet_id": pid, "source_id": pk["source_id"]}
        if want[pid] == planned:
            rows.append(base)
        else:
            rows.extend(dict(base, lane_id=lid) for lid in want[pid])
    return rows


def a1_expected_args(receipt, source_id, plan=None):
    """The canonical args for one source of THIS receipt."""
    plan = a1_plan() if plan is None else plan
    allowed = _pairs_of(receipt.get("allowed")) or []
    return a1_args_for(plan, a1_projection(allowed, source_id),
                       receipt.get("attempt"))


def a1_retry_set(final, validity, allowed, attempt):
    """THE invalid-only filter. Attempt 2 never produces a successor."""
    if attempt >= A1_MAX_ATTEMPTS:
        return []
    return [c for c in allowed
            if (final.get(c) == "served" and validity.get(c) is False)
            or final.get(c) == A1_INVALID_RESPONSE]


def a1_load_receipt_loosely(run_dir):
    """The MINIMUM needed to preserve evidence: a mapping and its state paths.

    Nothing semantic, nothing strict — a malformed receipt must still not erase
    bytes that were already paid for (Codex SEQ 1318 item 3).
    """
    path = os.path.join(run_dir, "receipt.json")
    if not os.path.isfile(path):
        raise RawTransportError("no receipt at %s — this run was never gated"
                                % path)
    try:
        with io.open(path, encoding="utf-8") as fh:
            receipt = json.load(fh)
    except Exception as exc:                          # noqa: BLE001 - by design
        return None, [], "the receipt is not readable JSON: %s" % exc
    if not isinstance(receipt, dict):
        return None, [], ("the receipt is %s, not an object; there is no lawful "
                          "state inventory to read"
                          % type(receipt).__name__)
    states = receipt.get("states")
    if not isinstance(states, list):
        return receipt, [], "receipt.states is not a list"
    return receipt, [s for s in states if isinstance(s, str)], None


def _a1_publish(run_dir, allowed, attempt, parent=None):
    """THE PRIVATE PUBLISHER — the only writer of a callable run.

    Codex SEQ 1405 C: it resolves the plan THIS run was published under, so a
    door that persisted a private plan under <run>/plan/ publishes from it and
    K-fields, which persists none, behaves exactly as before. There is still
    one serializer and one receipt contract.
    """
    import build_launch_manifest as blm
    plan = a1_plan_for_run(run_dir)
    canonical = a1_canonical_calls(plan, attempt)
    bad = a1_pair_problems(list(allowed), set(canonical), attempt)
    if bad:
        return {"ok": False, "problems": bad, "launchers": {}, "receipts": {},
                "invocations": []}
    allowed = [tuple(c) for c in allowed]
    keep = set(allowed)
    ordered = [c for c in canonical if c in keep]
    if len(ordered) != len(allowed):
        return {"ok": False, "launchers": {}, "receipts": {}, "invocations": [],
                "problems": ["the requested calls are not a subset of the "
                             "canonical schedule"]}
    payload = a1_expected_receipt(run_dir, ordered, attempt, parent, plan)
    # THE PUBLISHER PROVES ITS OWN OUTPUT against the same contract audit and
    # finalize use — including, for a retry, the full child chain.
    self_check = a1_run_contract_problems(payload, run_dir, plan)
    if self_check:
        return {"ok": False, "problems": self_check, "launchers": {},
                "receipts": {}, "invocations": []}
    # THE REAL ENVIRONMENT, AND THIS RUN'S OWN PLAN. Calling the gate with no
    # plan checked the COMMITTED A1 pair at the default era while this run was
    # about to serve its own v3 launchers - the gate proved v1 and the run
    # served v3 (Codex SEQ 1469 item 2). The publisher already resolved the
    # right plan above; it now hands the same pair to the gate.
    problems = blm.preflight(run_dir=run_dir,
                             manifest_path=plan.get("manifest_path"),
                             bundle_path=plan.get("bundle_path"))
    # A door that persisted its own plan has already written <run>/plan/. That
    # is not published output, so the run is still unpublished exactly when the
    # plan directory is the ONLY thing in it. K-fields persists no plan and
    # therefore never takes this branch.
    if plan.get("manifest_path") and os.path.isdir(run_dir) \
            and os.listdir(run_dir) == [PLAN_DIRNAME]:
        problems = [x for x in problems
                    if "output directory is not fresh" not in x]
    if problems:
        return {"ok": False, "problems": problems, "launchers": {},
                "receipts": {}, "invocations": []}

    # AT THIS PLAN'S OWN ERA, like the gate above. Deriving at the default era
    # here described a v1 launch while this run serves v3.
    derived = blm.derive_expected(
        plan.get("runtime_model_id"),
        contract_suffix=plan.get("contract_suffix"))
    # A door with its own persisted bundle publishes THOSE exact unarmed bytes,
    # never the committed K-fields launchers.
    bpath = plan.get("bundle_path")
    if bpath and os.path.isfile(bpath):
        with io.open(bpath, encoding="utf-8") as fh:
            own = json.load(fh)
        base = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(blm.__file__)),
            "..", "..", "..", "..", ".."))
        for row in own.get("slices") or []:
            live = os.path.join(base, row["launcher"])
            with io.open(live, encoding="utf-8") as fh:
                derived["launchers"][row["source_id"]] = fh.read()
    staging = os.path.join(run_dir, ".launch.partial")
    os.makedirs(staging, exist_ok=True)
    launchers = {}
    for inv in payload["invocations"]:
        sid = inv["source_id"]
        text = derived["launchers"][sid]
        if A1_RECEIPT_LINE not in text:
            raise RawTransportError(
                "%s: the derived launcher carries no receipt slot" % sid)
        armed = text.replace(A1_RECEIPT_LINE,
                             "const RECEIPT = %s\n" % json.dumps(
                                 payload["receipts"][sid], sort_keys=True), 1)
        with io.open(os.path.join(staging, os.path.basename(inv["scriptPath"])),
                     "w", encoding="utf-8") as fh:
            fh.write(armed)
            fh.flush()
            os.fsync(fh.fileno())
        launchers[sid] = inv["scriptPath"]
    _fsync_dir(staging)
    _atomic_json(os.path.join(run_dir, "receipt.json"), payload)
    os.rename(staging, os.path.join(run_dir, "launch"))
    _fsync_dir(run_dir)
    return {"ok": True, "problems": [], "launchers": launchers,
            "receipts": payload["receipts"],
            "invocations": payload["invocations"],
            "allowed": [list(c) for c in ordered]}


def a1_prepare_run(run_dir):
    """PUBLIC. Arm the COMPLETE canonical primary schedule for one fresh run."""
    return _a1_publish(run_dir, a1_canonical_calls(a1_plan(), 1), 1)


def a1_prepare_retry(primary_run_dir):
    """PUBLIC. The ONE lawful retry, rederived from the primary's own record."""
    fpath = os.path.join(primary_run_dir, FINALIZATION_NAME)
    rpath = os.path.join(primary_run_dir, "receipt.json")
    fail = {"ok": False, "launchers": {}, "receipts": {}, "invocations": []}
    if not os.path.isfile(fpath) or not os.path.isfile(rpath):
        return dict(fail, problems=["no primary finalization at %s — a retry "
                                    "without a finalized primary is not a "
                                    "retry" % fpath])
    try:
        with io.open(fpath, encoding="utf-8") as fh:
            fin = json.load(fh)
    except Exception as exc:                          # noqa: BLE001 - by design
        return dict(fail, problems=["the finalization is unreadable: %s" % exc])
    plan = a1_plan_for_run(primary_run_dir)
    problems = a1_primary_evidence_problems(fin, plan, primary_run_dir)
    child = os.path.join(primary_run_dir, RETRY_DIRNAME)
    if os.path.exists(child):
        problems.append("a retry has already been prepared at %s; there is "
                        "exactly one" % child)
    if problems:
        return dict(fail, problems=problems)
    derived = a1_primary_retry_keys(fin, plan)
    if not derived:
        return dict(fail, problems=["the primary finalization names no invalid "
                                    "call to retry"])
    return _a1_publish(child, derived, 2,
                       parent={"run_id": fin.get("run_id"),
                               "receipt_sha256": _sha_file(rpath),
                               "finalization_sha256": _sha_file(fpath)})


def a1_finalize(run_dir):
    """PUBLIC, and it takes NOTHING but the run directory.

    THE ORDER IS THE LAW (Codex SEQ 1319 item A). Everything above the raw
    writes is a loose mapping read; the first import, load or check of anything
    else happens only AFTER every paid byte is on disk:

        loose receipt + its state paths -> harvest EVERY readable result row ->
        save them all through the raw-only writer -> only then load the plan and
        check the run contract, the runtime evidence, the protected pins and the
        live inputs -> only when THOSE are clean, import the semantic owners and
        parse -> one ledger -> one durable finalization, on every attempt.

    A corrupted protected plan, a broken receipt and a failed write are all
    structured refusals here. None of them may cost a byte or skip the closeout.
    """
    receipt, state_paths, loose = a1_load_receipt_loosely(run_dir)
    attempt = receipt.get("attempt") if isinstance(receipt, dict) else None
    attempt = attempt if attempt in (1, 2) else 1

    # ---- 1. THE EVIDENCE, BEFORE ANY IMPORT, LOAD OR CHECK -----------------
    records = a1_preserve(a1_readable_rows(state_paths),
                          os.path.join(run_dir, "raw"), attempt)
    problems = ["raw row %d was not written: %s" % (r["index"],
                                                    r["write_error"])
                for r in records if r["write_error"]]
    if loose:
        problems.append(loose)

    # ---- 2. THE PLAN, THE CONTRACT AND THE RUNTIME EVIDENCE ----------------
    plan, canonical, manifest_sha = None, None, None
    try:
        # Codex SEQ 1405 D: the same run plan the publisher, the contract and
        # the auditor resolve. A run with no private plan is K-fields, exactly
        # as before, and the manifest hashed is the one the plan names.
        plan = a1_plan_for_run(run_dir)
        manifest_sha = _sha_file(a1_plan_identity(plan)[0])
    except Exception as exc:                          # noqa: BLE001 - by design
        problems.append("the protected plan is unusable: %s: %s"
                        % (type(exc).__name__, exc))
    if plan is not None and plan.get("door") != A1_DOOR:
        problems.append("this plan names door %r; the one-item route only "
                        "executes %r" % (plan.get("door"), A1_DOOR))
        plan = None
    if plan is not None:
        canonical = a1_canonical_calls(plan, attempt)
        if not problems:
            problems += a1_run_contract_problems(receipt, run_dir, plan)

    allowed = _pairs_of(receipt.get("allowed")) if isinstance(receipt, dict) \
        else None
    allowed = allowed if allowed is not None else []
    outcomes = a1_classify_rows(records, plan, attempt, allowed)

    audit, audit_outcomes = {"answers": {}}, []
    if not problems:
        import build_launch_manifest as blm
        import audit_worker_access as AUD
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

    # ---- 3. LAST: the semantic owners. A reader too broken to import must
    #         not cost the paid bytes, so nothing above may need it.
    validity, why_by_key = {}, {}
    if not problems:
        import build_launch_manifest as blm
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
    # ONE ROW PER SCHEDULED CALL, IN CANONICAL ORDER, against a FIXED
    # denominator: a refused run closes out over the whole schedule, and with
    # the plan itself unusable the lawful receipt is the only denominator left.
    fallback = canonical if canonical is not None else allowed
    scope = fallback if problems else (allowed or fallback)
    final = collections.OrderedDict((c, graded.get(c, "missing"))
                                    for c in scope)
    # A row for a call this run does not schedule is PRESERVED and REPORTED,
    # never given a scheduled identity (Codex SEQ 1319 item B).
    stray = [k for k in graded if k not in final]
    if stray:
        problems.append("%d returned rows are not calls this run schedules; "
                        "their bytes are preserved and they are classified "
                        "nowhere" % len(stray))
    ledger = a1_ledger(final, validity, len(scope), attempt)
    retry = [] if problems else a1_retry_set(final, validity, allowed, attempt)
    doc = {"run_id": receipt.get("run_id") if isinstance(receipt, dict) else None,
           "manifest_sha256": manifest_sha,
           "receipt_sha256": _sha_file(os.path.join(run_dir, "receipt.json")),
           "attempt": attempt, "ledger": ledger,
           "audit_problems": problems,
           "classification": [[list(k), v] for k, v in final.items()],
           "validity": [[list(k), validity[k]] for k in final
                        if k in validity and final[k] == "served"],
           "retry": [list(k) for k in retry]}
    # WRITE-ONCE (Codex SEQ 1482 item 3). Atomic REPLACEMENT let a second
    # closeout - whose raw preservation had already refused because the paid
    # files exist - overwrite a clean record with a refused one. The first
    # writer wins, a second or racing writer is told, and the first bytes stay.
    write_new(os.path.join(run_dir, FINALIZATION_NAME),
              json.dumps(doc, indent=1, sort_keys=True))
    try:
        limits = a1_limits(plan)
    except Exception:                                 # noqa: BLE001 - by design
        limits = None            # a diagnostic; it may never break a closeout
    return {"records": records, "outcomes": outcomes, "validity": validity,
            "problems": why_by_key, "audit_problems": problems,
            "classification": doc["classification"], "limits": limits,
            "attempt": attempt, "ledger": ledger, "retry": doc["retry"]}
