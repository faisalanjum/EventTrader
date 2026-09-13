"""a1_reader — THE one experiment-owned reader for the A1 one-item run.

WHY THIS FILE EXISTS AND WHERE IT GOES. Step 1 may build temporary experiment
tools and use existing Core code, but it may not build the production reader
(Codex SEQ 1313). A1's sparse shapes therefore live HERE, not in
`driver/core/driver_write_cli.py`, and Step 3 later MOVES these exact bytes into
production and connects `_run_event_v2` — it does not copy them.

WHAT IT OWNS, once each:
  * the sparse reply shapes and which fields the SOURCE owns;
  * item defaults, DERIVED from `PreparedItemV2`'s own declarations;
  * the readable, reversible menu mapping;
  * the normalizer that completes a sparse reply from its ONE trusted item;
  * the complete validation of the whole four-field reply, in one pass.

WHAT IT DOES NOT OWN. Every rule that already has an owner is reused, never
restated: `PreparedFactV2.from_dict` is the model door, `verify_occurrence` is
the locator, `driver_ids` is the slice-token grammar and the unknown-axis
decoder, and `V2_ABSTENTION_KEYS` is Core's own completed-abstention shape.
There is no projection to the old three-field envelope and no second schema:
the four-field reply is validated as itself, once.
"""
import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

#: The exact top-level envelope of a raw one-item reply.
REPLY_KEYS = ("source_id", "facts", "abstentions", "continuity_hints")
#: The fields the SOURCE owns. A model that emits any of them is refused whole.
SOURCE_BINDING_FIELDS = ("quote", "part_ref", "occurrence_in_part",
                         "raw_label_or_claim")
#: The raw shapes the model may emit.
ABSTENTION_RAW_KEYS = ("reason",)
CONTINUITY_RAW_KEYS = ("kind", "old", "new")
#: The closed rename vocabulary, owned by FinalDesign/LeftOverSteps/step3.md:63
#: and step2.md:444 — "`kind` is exactly `driver`, `slice_label`, or
#: `measurement_token`". Quoted from the law once, decided nowhere.
CONTINUITY_KINDS = ("driver", "slice_label", "measurement_token")
#: The COMPLETED proposal, step3.md:59.
CONTINUITY_COMPLETE_KEYS = ("kind", "old", "new", "quote", "part_ref",
                            "occurrence_in_part")
#: The model-owned OPTIONAL fact-level fields, mapped to the value an absent
#: field completes to. One owner: the names, the prompt's card and the
#: completion below are all derived from this mapping.
FACT_DEFAULTS = {"per_x": None}


class A1ReaderError(Exception):
    """A reply this owner refuses. Carries every reason, never just the first."""


def sparse_fact_keys():
    """The fact keys a RAW reply may carry: the fact owner's own key list minus
    the fields the source owns. Never a copied tuple."""
    from driver.core.prepared_fact_v2 import PreparedFactV2
    return tuple(k for k in PreparedFactV2._FACT_KEYS
                 if k not in SOURCE_BINDING_FIELDS)


def item_defaults():
    """`PreparedItemV2`'s OWN declared defaults, for the model-owned fields."""
    import dataclasses as dc
    from driver.core.prepared_fact_v2 import PreparedItemV2, ITEM_FIELDS
    owned = set(ITEM_FIELDS)
    out = {}
    for f in dc.fields(PreparedItemV2):
        if f.name not in owned:
            continue
        if f.default is not dc.MISSING:
            out[f.name] = f.default
        elif f.default_factory is not dc.MISSING:      # noqa: B008 - owner's own
            out[f.name] = f.default_factory()
    return out


def required_item_fields():
    """The model-owned item fields with no declared default, minus the source's.

    Proof by construction rather than a copied count: whatever the dataclass
    declares without a default and the source does not own is what the model
    must state.
    """
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    defaults = item_defaults()
    return tuple(f for f in ITEM_FIELDS
                 if f not in defaults and f not in SOURCE_BINDING_FIELDS)


# ----------------------------------------------------------------- menu -----

def readable_menu(tokens):
    """THE readable, REVERSIBLE menu mapping.

    Each token is first proved CANONICAL through the existing slice-token
    grammar; only a valid unknown-axis sentinel is then decoded for display.
    Ordinary tokens are shown unchanged. Order and cardinality are preserved and
    the exact display -> original map is returned. Fails closed on a malformed
    or noncanonical token and on any display collision, because a collision
    would make the restoration ambiguous.
    """
    from driver.core.driver_ids import (IdLawError, UNKNOWN_SLICE_KIND,
                                        decode_unknown_axis, slice_token)
    display, back = [], {}
    for tok in tokens:
        if not isinstance(tok, str):
            raise IdLawError("menu token must be a string: %r" % (tok,))
        kind, sep, value = tok.partition(":")
        if not sep or slice_token(kind, value) != tok:
            raise IdLawError("noncanonical menu token: %r" % tok)
        if kind == UNKNOWN_SLICE_KIND:
            qname, member = decode_unknown_axis(tok)
            shown = "%s:%s__%s" % (kind, qname, member)
        else:
            shown = tok
        if back.get(shown, tok) != tok:
            raise IdLawError("display collision: %r maps to %r and %r"
                             % (shown, back[shown], tok))
        back[shown] = tok
        display.append(shown)
    return display, back


def restore_menu_pick(shown, back):
    """Restore an EXACT displayed menu value to its original token.

    A value that is not an exact display string is a lawful off-menu value and
    is preserved unchanged; only exact picks are restored.
    """
    return back.get(shown, shown)


# ----------------------------------------------------- normalize + validate --

def _nonblank(value):
    return type(value) is str and bool(value.strip())


def _exact(obj, keys, where, problems):
    if not isinstance(obj, dict):
        problems.append("%s: expected an object, got %s"
                        % (where, type(obj).__name__))
        return False
    if set(obj) != set(keys):
        problems.append("%s: keys must be EXACTLY %s (extra %s, missing %s)"
                        % (where, list(keys), sorted(set(obj) - set(keys)),
                           sorted(set(keys) - set(obj))))
        return False
    return True


def read_one(text, item, source_id, menu_back, parts):
    """THE ONE CALL: exact raw parse -> normalize from the frozen item ->
    validate the whole four-field reply once.

    `item` is the trusted, already-located item that travelled with the packet.
    `parts` is that event's part lookup, from the existing duplicate-refusing
    owner. Returns `(completed, problems)`; a single problem accepts nothing.
    """
    import raw_transport
    if not isinstance(text, str):
        return None, ["no reply text: %s" % type(text).__name__]
    try:
        # THE ONE approved envelope owner: a bare payload or exactly one whole
        # fenced block. It normalizes the envelope only and never looks inside
        # the payload; `parse_exact` still owns the exact parse.
        reply = raw_transport.parse_reply(text)
    except raw_transport.RawTransportError as exc:
        return None, [str(exc)]
    completed, problems = normalize(reply, item, source_id, menu_back)
    if problems:
        return None, problems
    problems = validate(completed, item, parts)
    if problems:
        return None, problems
    return completed, []


def normalize(reply, item, source_id, menu_back):
    """Complete a sparse reply from its ONE trusted item. Pure."""
    problems = []
    src = {"quote": item["quote"], "part_ref": item["part_ref"],
           "occurrence_in_part": item["occurrence_in_part"]}
    if not _exact(reply, REPLY_KEYS, "the reply", problems):
        return None, problems
    if reply["source_id"] != source_id:
        return None, ["the reply echoes source %r, but this packet is %r"
                      % (reply["source_id"], source_id)]
    for name in ("facts", "abstentions", "continuity_hints"):
        if type(reply[name]) is not list:
            return None, ["%s must be a list, got %s"
                          % (name, type(reply[name]).__name__)]
    facts, absts, conts = (reply["facts"], reply["abstentions"],
                           reply["continuity_hints"])
    if bool(facts) == bool(absts):
        return None, ["exactly one of facts / abstentions carries content"]
    if absts and len(absts) != 1:
        return None, ["an abstaining reply carries exactly one abstention"]

    def _no_source_fields(obj, where):
        if isinstance(obj, dict):
            for f in SOURCE_BINDING_FIELDS:
                if f in obj:
                    problems.append("%s: %r is owned by the source and must "
                                    "not be emitted" % (where, f))

    defaults, allowed_fact = item_defaults(), set(sparse_fact_keys())
    done_facts = []
    for n, f in enumerate(facts):
        where = "fact %d" % n
        if not isinstance(f, dict):
            problems.append(where + ": not an object"); continue
        _no_source_fields(f, where)
        extra = sorted(set(f) - allowed_fact)
        if extra:
            problems.append("%s: fields the reply contract does not declare: %s"
                            % (where, extra))
        raw_item = f.get("item")
        if not isinstance(raw_item, dict):
            problems.append(where + ": item must be an object"); continue
        _no_source_fields(raw_item, where + ".item")
        unknown = sorted(set(raw_item) - set(defaults)
                         - set(required_item_fields()))
        if unknown:
            problems.append("%s.item: fields the schema does not declare: %s"
                            % (where, unknown))
        for k, v in raw_item.items():
            if k in defaults and v in (None, []) and v != defaults[k]:
                problems.append("%s.item: explicit %r for %r is not that "
                                "field's default" % (where, v, k))
        completed_item = dict(defaults)
        completed_item.update(raw_item)
        completed_item["quote"] = src["quote"]
        picks = completed_item.get("slice_parts")
        if type(picks) is list:
            # the ONLY caller of the reversible mapping: an exact displayed pick
            # is restored to the token the source carries, and anything else is
            # a lawful off-menu value, preserved unchanged
            completed_item["slice_parts"] = [
                restore_menu_pick(v, menu_back) if type(v) is str else v
                for v in picks]
        done = {"fact_type": f.get("fact_type"),
                "part_ref": src["part_ref"],
                "occurrence_in_part": src["occurrence_in_part"],
                "item": completed_item}
        # every absent optional fact field completes to its declared default
        for name, default in FACT_DEFAULTS.items():
            done[name] = f.get(name, default)
        done_facts.append(done)

    from driver.core.driver_write_cli import V2_ABSTENTION_KEYS
    done_absts = []
    for n, a in enumerate(absts):
        if not _exact(a, ABSTENTION_RAW_KEYS, "abstention %d" % n, problems):
            continue
        done_absts.append({"quote": src["quote"], "reason": a["reason"],
                           "part_ref": src["part_ref"],
                           "occurrence_in_part": src["occurrence_in_part"]})
        assert set(done_absts[-1]) == set(V2_ABSTENTION_KEYS)

    done_conts = []
    for n, c in enumerate(conts):
        if not _exact(c, CONTINUITY_RAW_KEYS, "continuity %d" % n, problems):
            continue
        done_conts.append({**{k: c[k] for k in CONTINUITY_RAW_KEYS},
                           "quote": src["quote"], "part_ref": src["part_ref"],
                           "occurrence_in_part": src["occurrence_in_part"]})
    if problems:
        return None, problems
    return {"source_id": source_id, "facts": done_facts,
            "abstentions": done_absts, "continuity_hints": done_conts}, []


def validate(completed, item, parts):
    """Validate the WHOLE four-field reply once. Returns every problem.

    There is no projection to the old three-field envelope: the four-field
    reply is checked as itself. Every fact, abstention and continuity proposal
    is bound to the frozen quote and locator through the SAME owners.
    """
    from driver.core.driver_write_cli import V2_ABSTENTION_KEYS
    from driver.core.prepared_fact_v2 import (PreparedFactV2, SchemaError,
                                              verify_occurrence)
    problems = []

    def _binding(obj, where, quote_at=None):
        """The source binding, through the ONE locator owner.

        A completed FACT carries its quote inside `item` while its locator is
        top level, so the quote is read from where that object actually keeps
        it. Reading it from the wrong place raised KeyError and meant the fact
        branch was never bound at all (Codex SEQ 1313 item 8).
        """
        got_quote = obj["item"]["quote"] if quote_at == "item" else obj["quote"]
        if got_quote != item["quote"]:
            problems.append("%s: quote is not this item's frozen quote" % where)
        if obj["part_ref"] != item["part_ref"]:
            problems.append("%s: part_ref is not this item's frozen part" % where)
        if obj["occurrence_in_part"] != item["occurrence_in_part"]:
            problems.append("%s: occurrence is not this item's frozen locator"
                            % where)
        why = verify_occurrence(parts.get(obj["part_ref"], ""), got_quote,
                                obj["occurrence_in_part"])
        if why:
            problems.append("%s: %s" % (where, why))

    for n, fact in enumerate(completed["facts"]):
        where = "fact %d" % n
        _binding(fact, where, quote_at="item")
        try:
            PreparedFactV2.from_dict(fact)
        except SchemaError as exc:
            problems.append("%s: %s" % (where, exc))

    for n, a in enumerate(completed["abstentions"]):
        where = "abstention %d" % n
        if _exact(a, V2_ABSTENTION_KEYS, where, problems):
            if not _nonblank(a["reason"]):
                problems.append("%s: reason must be a nonblank string" % where)
            _binding(a, where)

    for n, c in enumerate(completed["continuity_hints"]):
        where = "continuity proposal %d" % n
        if not _exact(c, CONTINUITY_COMPLETE_KEYS, where, problems):
            continue
        if c["kind"] not in CONTINUITY_KINDS:
            problems.append("%s kind: one of %s (step3.md:63), got %r"
                            % (where, list(CONTINUITY_KINDS), c["kind"]))
        for field in ("old", "new", "quote", "part_ref"):
            if not _nonblank(c[field]):
                problems.append("%s %s: an exact nonblank string (step3.md:63)"
                                ", got %r" % (where, field, c[field]))
        _binding(c, where)
    return problems


def owner_sha256():
    """This owner's own bytes — the thing Step 3 will MOVE, unchanged."""
    with open(os.path.abspath(__file__), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
