"""kf_ draft/key lint v5 (V2 contract) — machine-enforced exam-validity checker.

TWO DOORS, ONE RULE OWNER.
  lint_v2_reply  — the MODEL/READER door. The exact V2 reply envelope
                   (driver_write_cli.V2_REPLY_KEYS), the source-id echo against
                   a trusted expected id, the exact part lookup with its
                   per-part occurrence, and the abstention shape
                   (driver_write_cli.V2_ABSTENTION_KEYS). Every item, type,
                   numeric, unit and evidence rule is delegated to
                   PreparedFactV2.from_dict; the locator verdict comes from
                   prepared_fact_v2.verify_occurrence, which RETURNS its reason.
  lint_doc       — the ADJUDICATED-KEY door. A stored gold fact is the EXACT V2
                   model fact plus ONLY three review fields
                   (du_worthy, gold_extra, ambiguity_note). It owns those three
                   shapes and nothing else: it strips them and delegates the
                   remaining fact to lint_v2_reply. There is no gold_item
                   wrapper and no duplicate outer quote — the quote is
                   item.quote.

Modes:
  single (default): lint the given file's docs (still fails on EMPTY input).
  --arm:            a full arm's output — EXACTLY 36 docs, 36 unique source_ids,
                    each with a draft_inputs file; empty/short/extra = FAIL.

Numbers are exact: drafts are parsed with parse_float=Decimal and the numeric
law is slot_convert.exact_number, the same owner the slot structure uses. A
populated numeric slot is a {value, scale_multiplier, unit_scale_evidence}
object, never a flat number; its scale evidence is quote-local. No semantic
rule, regex, word list or example-specific branch lives in this module.
"""
import json
import os
import sys
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, _REPO)
from driver.core.prepared_fact_v2 import (ITEM_FIELDS,                  # noqa: E402
                                          verify_occurrence,
                                          PreparedFactV2, SchemaError)
from driver.core.driver_write_cli import (V2_ABSTENTION_KEYS,           # noqa: E402
                                          V2_REPLY_KEYS)

# THE ONE AUTHORITATIVE FIELD SOURCE (Step 2 §2). Every structural name is
# DERIVED from the committed Core V2 owners and never re-typed here, so the exam
# contract cannot drift from production:
#   item fields    -> prepared_fact_v2.ITEM_FIELDS   (already excludes the
#                     source-owned pair; NOT re-filtered here)
#   fact-level     -> PreparedFactV2._FACT_KEYS
#   reply envelope -> driver_write_cli.V2_REPLY_KEYS
# Step 2 §7 / rev-4 A3: the adjudicated gold fact is the EXACT V2 model fact
# plus ONLY these three review fields. There is no second model-output shape:
# no gold_item wrapper and no duplicate outer quote — the quote is item.quote.
GOLD_ONLY = ("du_worthy", "gold_extra", "ambiguity_note")
# FableExperimentWorkOrder:420 — the frozen K-fields review record shape.
GOLD_EXTRA_KEYS = ("expectation_comparison_present",)
FACT_KEYS = set(PreparedFactV2._FACT_KEYS) | set(GOLD_ONLY)

DEFAULT_INPUTS = os.path.join(_HERE, "..", "keys", "K-fields", "draft_inputs")
# Step 2 §2: ONE owner for every structural name — the abstention shape is
# Core's, never re-typed here.
ABSTENTION_KEYS = set(V2_ABSTENTION_KEYS)


def _event_parts(source_id, inputs_dir):
    """The event's ordered text_parts[] — the ONLY lawful locator source."""
    with open(os.path.join(inputs_dir, source_id + ".json"),
              encoding="utf-8") as fh:
        return json.load(fh)["text_parts"]



def lint_doc(doc, errors, inputs_dir, expected_source_id=None):
    """THE ADJUDICATED-KEY DOOR. Not a second rule engine.

    A stored gold fact is the EXACT V2 model fact plus only the three review
    fields. This function owns nothing but those three shapes: it strips them
    and hands the remaining exact V2 fact — locator included — to the same V2
    checker every model reply goes through, so Core stays the single owner of
    item, type, numeric, unit, evidence and locator law.
    """
    if not isinstance(doc, dict):
        errors.append(f"doc must be an object, got {type(doc).__name__}")
        return
    facts = doc.get("facts")
    if not isinstance(facts, list):
        errors.append("facts must be a list")
        return
    stripped = []
    for i, f in enumerate(facts):
        w = f"{doc.get('source_id')}#{i}"
        if not isinstance(f, dict):
            errors.append(f"{w}: fact must be an object")
            continue
        if set(f) != FACT_KEYS:
            errors.append(f"{w}: gold fact keys must be EXACTLY "
                          f"{sorted(FACT_KEYS)}, got {sorted(f)}")
            continue
        if not isinstance(f["du_worthy"], bool):
            errors.append(f"{w}: du_worthy must be a bool")
        # The review shape is FROZEN by the WorkOrder's K-fields record:
        # exactly one key, boolean-valued. Mechanical shape, no inference.
        ge = f["gold_extra"]
        if not isinstance(ge, dict) or set(ge) != set(GOLD_EXTRA_KEYS):
            errors.append(f"{w}: gold_extra keys must be EXACTLY "
                          f"{sorted(GOLD_EXTRA_KEYS)}, got "
                          f"{sorted(ge) if isinstance(ge, dict) else type(ge).__name__}")
        elif not isinstance(ge[GOLD_EXTRA_KEYS[0]], bool):
            errors.append(f"{w}: {GOLD_EXTRA_KEYS[0]} must be a bool")
        note = f["ambiguity_note"]
        if note is not None and not isinstance(note, str):
            errors.append(f"{w}: ambiguity_note must be a string or null")
        stripped.append({k: v for k, v in f.items() if k not in GOLD_ONLY})
    lint_v2_reply(dict(doc, facts=stripped), errors, inputs_dir,
                  expected_source_id=expected_source_id)


def lint_v2_reply(doc, errors, inputs_dir, expected_source_id=None):
    """THE MODEL/READER DOOR (Step 2 §8). Deliberately NOT the gold surface.

    This path owns only four things: the reply envelope, the source echo, the
    exact part lookup with its occurrence, and the abstention shape. Every item,
    type, numeric, unit and evidence rule is delegated to its real owner —
    `PreparedFactV2.from_dict` — so no rule is re-implemented here. A gold-only
    review field is refused simply because it is not a Core fact-level key.
    """
    if not isinstance(doc, dict) or set(doc) != set(V2_REPLY_KEYS):
        errors.append(f"reply keys must be EXACTLY {sorted(V2_REPLY_KEYS)}, got "
                      f"{sorted(doc) if isinstance(doc, dict) else type(doc).__name__}")
        return
    sid = doc["source_id"]
    # THE SOURCE ECHO. Without a trusted expected id a reply could name a
    # DIFFERENT but valid event and simply load that file, so the echo is
    # compared BEFORE any part is read. The trusted id comes from the caller
    # (Step 3 wires the existing manifest/transport to this callable); no second
    # manifest or lookup is introduced here.
    if expected_source_id is not None and sid != expected_source_id:
        errors.append(f"source_id echo: expected {expected_source_id!r}, "
                      f"got {sid!r}")
        return
    try:
        parts = {p["part"]: p["content"] for p in _event_parts(sid, inputs_dir)}
    except FileNotFoundError:
        errors.append(f"{sid}: NO draft_inputs file for this source_id")
        return
    for key in ("facts", "abstentions"):
        if not isinstance(doc[key], list):
            errors.append(f"{sid}: {key} must be a list")
            return

    def _locate(w, rec):
        """Exact part lookup + per-part occurrence — this module's own duty."""
        part_ref, quote = rec.get("part_ref"), rec.get("quote")
        if part_ref not in parts:
            errors.append(f"{w}: part_ref {part_ref!r} is not a part of this event")
            return
        if not isinstance(quote, str) or not quote:
            errors.append(f"{w}: quote must be a non-blank string")
            return
        why = verify_occurrence(parts[part_ref], quote,
                                rec.get("occurrence_in_part"))
        if why:                      # the owner RETURNS the reason, never raises
            errors.append(f"{w}: {why}")

    for i, f in enumerate(doc["facts"]):
        w = f"{sid}#{i}"
        try:
            fact = PreparedFactV2.from_dict(f)          # THE owner, not a copy
        except SchemaError as e:
            errors.append(f"{w}: {e}")
            continue
        _locate(w, dict(f, quote=(f.get("item") or {}).get("quote")))
        del fact
    for i, a in enumerate(doc["abstentions"]):
        w = f"{sid}~{i}"
        if not isinstance(a, dict) or set(a) != ABSTENTION_KEYS:
            errors.append(f"{w}: abstention keys must be EXACTLY "
                          f"{sorted(ABSTENTION_KEYS)}")
            continue
        if not isinstance(a.get("reason"), str) or not a["reason"].strip():
            errors.append(f"{w}: reason must be a non-blank string")
        _locate(w, a)
    return


#: THE TWO DOORS, NAMED ONCE (B-13). A K-fields gold drafter answers with the
#: review fields attached; an EXP-5 producer answers with the plain V2 envelope.
#: They are different contracts, so they get different doors — and which one
#: applies is decided by the PLAN, never by looking at the reply, because a reply
#: that carries a gold key would otherwise select its own door.
#: Both already share the (doc, errors, inputs_dir) signature, so the map points
#: at them directly — a lambda wrapper would add a layer and no behaviour.
DOORS = {"gold": lint_doc, "reader": lint_v2_reply}


def lint_parsed(docs, inputs_dir=DEFAULT_INPUTS, arm=False, door=None):
    """Validate ALREADY-PARSED docs — the entry point the live pipeline uses.

    raw_transport parses the reply ONCE with parse_float=Decimal; handing the
    parsed object straight here avoids a re-serialize/re-parse round trip that
    would silently turn every exact Decimal back into a string (caught by the
    live hand-off test). Same contract as run(), applied to exact values.
    Returns an exit code: 0 clean, 1 on any error."""
    errors = []
    if not docs:
        errors.append("EMPTY input — nothing to lint is a FAILURE, never a pass")
    # No default: a door the caller forgot is refused, never guessed. The plan
    # manifest names it, so "which contract am I checking" is a property of the
    # approved plan rather than of caller memory.
    if door not in DOORS:
        raise ValueError(f"door {door!r} is not one of {sorted(DOORS)}; the "
                         f"PLAN MANIFEST must name it")
    check = DOORS[door]
    for doc in docs:
        check(doc, errors, inputs_dir)
    sids = [d.get("source_id") for d in docs if isinstance(d, dict)]
    if len(set(sids)) != len(sids):
        errors.append("DUPLICATE source_ids in the set")
    if arm:
        expected = sorted(x[:-5] for x in os.listdir(inputs_dir)
                          if x.endswith(".json"))
        if sorted(set(sids)) != expected or len(docs) != len(expected):
            errors.append(f"--arm requires EXACTLY the {len(expected)} events "
                          f"one doc each; got {len(docs)} docs / "
                          f"{len(set(sids))} unique")
    print(f"docs linted: {len(docs)}; errors: {len(errors)}")
    for e in errors[:40]:
        print(" ", e)
    return 1 if errors else 0


def run(target, arm=False, inputs_dir=DEFAULT_INPUTS):
    """File/dir entry point: read + EXACT-parse, then delegate to lint_parsed.
    Deliberately NO duplicated checking logic — one implementation only (the
    copy that used to live here is exactly the drift class that produced the
    defects reached the door)."""
    paths = ([os.path.join(target, x) for x in sorted(os.listdir(target))]
             if os.path.isdir(target) else [target])
    docs = []
    for p in paths:
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line:
                docs.append(json.loads(line, parse_float=Decimal))
    # `run()` IS the K-fields gold entry point — it reads drafter .jsonl files —
    # so its door is a property of this entry, not a caller's choice. Naming it
    # here is the opposite of the silent default that was removed: no caller of
    # `run()` can select a different contract by omission.
    return lint_parsed(docs, inputs_dir, arm=arm, door="gold")


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a != "--arm"]
    sys.exit(run(argv[0], arm="--arm" in sys.argv))
