"""raw_transport — the EXACT-number transport for K-fields / EXP-5 replies.

THE PROBLEM THIS EXISTS TO SOLVE (proven, not theoretical): the launcher used
`agent(..., {schema: SCHEMA})`, which makes the workflow runtime parse the
model's JSON in JAVASCRIPT. JS numbers are IEEE-754 doubles, so
`{"a":1.00000000000000000001,"b":1.00000000000000000002}` becomes `{"a":1,"b":1}`
BEFORE Python ever runs. Python then sees `1.0`, parses a perfectly valid
`Decimal('1.0')`, and every downstream type-gate passes — the digits are gone
and nothing can tell. A downstream fix CANNOT detect upstream loss.

THE ORDER (the whole point — do not reorder):

    raw model TEXT  ->  save unchanged  ->  Decimal JSON parse  ->  strict
                                                                   37-field
                                                                   validation

Dropping the workflow's `schema:` removes JS PARSING, never SCHEMA ENFORCEMENT:
enforcement simply moves after the exact parse, where `kf_lint` already applies
the authoritative contract (fields derived from `PreparedFactV1`, production's
own numeric rule, the enums, the period resolver). One validator, applied once,
on exact values.

Workflow scripts have no filesystem access, so the raw reply travels back as a
STRING — strings are never number-parsed — and is written to disk HERE, first,
byte-for-byte, before anything interprets it.
"""
import hashlib
import json
import os
from decimal import Decimal

__all__ = ["save_raw", "parse_exact", "ingest_workflow_result",
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


def ingest_workflow_result(result, out_dir, manifest_path=DEFAULT_MANIFEST,
                           validate=True, inputs_dir=None):
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
        for arm in ARMS:
            arm_docs = [v["doc"] for (s, a), v in sorted(docs.items()) if a == arm]
            if len(arm_docs) != len(expected):
                errors.append(f"arm {arm}: {len(arm_docs)}/{len(expected)} usable "
                              f"docs — not a complete arm, validation skipped")
                continue
            if lint_parsed(arm_docs, inputs_dir or DEFAULT_INPUTS, arm=True) != 0:
                errors.append(f"arm {arm}: FAILED strict validation")
    return {"docs": docs, "errors": errors, "ok": not errors}
