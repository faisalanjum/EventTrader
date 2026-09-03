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
    try:
        with open(path, "x", encoding="utf-8", newline="") as f:
            f.write(text)
    except FileExistsError:
        raise RawTransportError(
            f"{path} already exists — refusing to overwrite a captured reply; "
            f"move or delete it deliberately")
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
