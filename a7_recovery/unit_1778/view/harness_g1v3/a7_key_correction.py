"""The naming correction: a frozen DATA ledger and a GENERIC applier.

Codex SEQ 1456 item 3. The previous version branched on executable semantic
collections holding real driver names, which made the code sample-shaped: it
could only ever be right about the rows someone had already thought of. This
version owns no name at all.

  * the LEDGER is data, keyed by exact row identity - source_id, gold_idx, the
    original fact sha256, the old fact_type and name - and carrying the action,
    the exact patch or park reason, and the reference for each of the two
    independent OD-1 checks;
  * the APPLIER validates the ledger against the live key one-to-one, refuses
    unless every recorded old identity still matches byte for byte, and then
    applies exactly what the data says. It contains no driver name and no
    name-based branch.

Actions are a closed mechanical set, not a vocabulary:

  append_terminal_suffix  the row keeps its name and gains the terminal suffix
                          its own fact_type requires (NAME-17, via driver_ids)
  set_driver_name         the row takes the exact recorded name
  park                    the row leaves the accepted gold with its reason
"""
import collections
import copy
import hashlib
import io
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
while _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)

import a7_g1_build as G                                          # noqa: E402

SCHEMA = "a7_key_correction/4"
#: THE CURRENT LEDGER. Earlier ledgers stay on disk as history and are never
#: the default: a default pointing at a superseded ledger is how the builders,
#: the scorer and the receipts silently kept using an old key.
LEDGER_PATH = "/tmp/a7_key_v9_correction.json"

APPEND_SUFFIX = "append_terminal_suffix"
SET_NAME = "set_driver_name"
PARK = "park"
#: clear or set exactly the recorded item fields. The patch carries BOTH the
#: value it expects to replace and the value it writes, so a field that has
#: moved refuses instead of being overwritten blind.
PATCH_ITEM = "patch_item"
#: add one fact the key omitted. The row is recorded in full and is admitted
#: only against its own evidence reference.
ADD_FACT = "add_fact"
ACTIONS = (APPEND_SUFFIX, SET_NAME, PARK, PATCH_ITEM, ADD_FACT)


def fact_sha256(fact):
    """The row's exact identity, over its own deterministic bytes."""
    return hashlib.sha256(G._plain(fact).encode("utf-8")).hexdigest()


def required_suffix(fact_type):
    """The terminal suffix a fact_type requires, from the ONE owner."""
    from driver.core.driver_ids import GUIDANCE_SUFFIX, SURPRISE_SUFFIX
    return {"guidance": GUIDANCE_SUFFIX, "surprise": SURPRISE_SUFFIX}.get(
        fact_type)


def affected(gold):
    """-> [(source_id, gold_idx, fact)] the naming law can reach.

    DERIVED, never listed: every accepted guidance/surprise row, plus every
    other accepted row that shares a driver_name with one of them inside the
    same event, because a family and its base cannot be corrected apart.
    """
    rows = [(sid, i, f) for sid in sorted(gold)
            for i, f in enumerate(gold[sid])
            if f.get("du_worthy") is True]
    suffixed = {(sid, (f.get("item") or {}).get("driver_name"))
                for sid, _i, f in rows if required_suffix(f.get("fact_type"))}
    return [(sid, i, f) for sid, i, f in rows
            if required_suffix(f.get("fact_type"))
            or (sid, (f.get("item") or {}).get("driver_name")) in suffixed]


def _period_rows(gold, ledger):
    """Rows a PATCH_ITEM or PARK row names that the naming audit never reached.

    The period and unit corrections act on ordinary rows, so the applier must
    admit them into its live view without widening the naming population.
    """
    named = {(r["source_id"], r["gold_idx"]) for r in ledger["rows"]}
    return [(sid, i, f) for sid in sorted(gold)
            for i, f in enumerate(gold[sid])
            if (sid, i) in named and f.get("du_worthy") is True]


def load(path=LEDGER_PATH):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def apply(gold, ledger):
    """-> (corrected, problems). `gold` is never mutated.

    The applier is generic: it reads identity and action from the data and
    verifies both against the live key before touching anything.
    """
    from driver.core.driver_ids import split_terminal_suffix, valid_driver_name
    corrected = copy.deepcopy(gold)
    problems = []
    acted = {(r["source_id"], r["gold_idx"]): r for r in ledger["rows"]}
    if len(acted) != len(ledger["rows"]):
        problems.append("the ledger names one row twice")

    # an ADD_FACT row names a source event and an index that does not exist
    # yet; it is appended after every in-place action, so no existing index
    # moves under another row's feet.
    added = [r for r in ledger["rows"] if r["action"] == ADD_FACT]
    acted = {k: r for k, r in acted.items() if r["action"] != ADD_FACT}
    live = {(sid, i): f for sid, i, f in affected(gold)}
    live.update({(sid, i): f for sid, i, f in _period_rows(gold, ledger)})
    for key in sorted(set(acted) - set(live)):
        problems.append("%s gold %d is not in the affected population"
                        % (key[0], key[1]))
    unacted = sorted(set(live) - set(acted))

    for key in sorted(set(acted) & set(live)):
        row, fact = acted[key], live[key]
        item = (fact.get("item") or {})
        if fact_sha256(fact) != row["old_fact_sha256"]:
            problems.append("%s gold %d no longer matches its recorded bytes"
                            % key)
            continue
        if (item.get("driver_name") != row["old_driver_name"]
                or fact.get("fact_type") != row["old_fact_type"]):
            problems.append("%s gold %d does not match its recorded identity"
                            % key)
            continue
        if row["action"] not in ACTIONS:
            problems.append("%s gold %d names an unknown action %r"
                            % (key[0], key[1], row["action"]))
            continue
        target = corrected[key[0]][key[1]]
        target_item = target.setdefault("item", {})
        if row["action"] == PARK:
            if not row.get("park_reason"):
                problems.append("%s gold %d parks with no reason" % key)
            target["du_worthy"] = False
            target["parked_reason"] = row.get("park_reason")
            continue
        # A ROW MAY NEED BOTH A NAME AND A FIELD CORRECTION. Keying the
        # ledger one-row-per-identity and then de-duplicating silently dropped
        # the second correction, so `patch` is applied for EVERY action, not
        # only for PATCH_ITEM.
        if row.get("patch") and row["action"] != SET_NAME:
            stale = [f for f, c in sorted(row["patch"].items())
                     if item.get(f) != c["from"]]
            if stale:
                problems.append("%s gold %d: %s is not the recorded value"
                                % (key[0], key[1], ", ".join(stale)))
                continue
            for field, change in sorted(row["patch"].items()):
                target_item[field] = change["to"]
        if row["action"] == PATCH_ITEM:
            continue                      # the patch above was the whole action
        if row["action"] == APPEND_SUFFIX:
            suffix = required_suffix(row["old_fact_type"])
            if suffix is None:
                problems.append("%s gold %d cannot take a terminal suffix"
                                % key)
                continue
            new = row["old_driver_name"] + suffix
        else:
            new = row["patch"]["driver_name"]
        if not valid_driver_name(new):
            problems.append("%s gold %d would take an invalid name %r"
                            % (key[0], key[1], new))
            continue
        target_item["driver_name"] = new

    # CONSERVATION: nothing outside the ledger may have moved, and the rows the
    # ledger deliberately leaves alone must be provably unchanged.
    for key in unacted:
        if fact_sha256(corrected[key[0]][key[1]]) != fact_sha256(live[key]):
            problems.append("%s gold %d changed without a ledger row" % key)
    for row in added:
        if row["source_id"] not in corrected:
            problems.append("%s is not an event of this key" % row["source_id"])
            continue
        if row["gold_idx"] != len(corrected[row["source_id"]]):
            problems.append("%s add_fact names index %d, not the next index %d"
                            % (row["source_id"], row["gold_idx"],
                               len(corrected[row["source_id"]])))
            continue
        corrected[row["source_id"]].append(copy.deepcopy(row["fact"]))
    before = sum(1 for s in gold for f in gold[s] if f.get("du_worthy") is True)
    after = sum(1 for s in corrected for f in corrected[s]
                if f.get("du_worthy") is True)
    parked = sum(1 for r in ledger["rows"] if r["action"] == PARK)
    gained = sum(1 for r in added
                 if (r.get("fact") or {}).get("du_worthy") is True)
    if before - parked + gained != after:
        problems.append("%d accepted minus %d parked plus %d added is not %d"
                        % (before, parked, gained, after))
    return corrected, problems


def current_key():
    """-> (key, identity). THE ONE executable key of this candidate.

    The executable key is the DERIVATION - the signed v6 materialization with
    the current ledger applied - not a serialized file. A serialized copy is
    display-only: `_plain` renders a Decimal as a string, and a string does not
    round-trip through PreparedFactV2, so a file-backed key would quietly stop
    being the thing the scorer runs. Deriving it costs one materialization and
    can never drift from its ledger.

    `identity` is what every builder, prompt inventory, scorer and receipt must
    carry so a run can name the exact key it used.
    """
    base, _sidecar = G.gold_by_event()
    ledger = load()
    key, problems = apply(base, ledger)
    if problems:
        raise ValueError("the current key does not derive: %s" % problems[:2])
    accepted = sum(1 for sid in key for f in key[sid]
                   if f.get("du_worthy") is True)
    identity = collections.OrderedDict([
        ("schema", ledger["schema"]),
        ("base_owner", "a7_g1_build.gold_by_event"),
        ("ledger_path", LEDGER_PATH),
        ("ledger_sha256", G._sha_file(LEDGER_PATH)),
        ("acted_rows", ledger["acted_rows"]),
        ("accepted_rows", accepted),
        ("events", len(key)),
        # a deterministic FINGERPRINT of the derived key. It identifies the
        # key; it is not a substitute for deriving it.
        ("key_digest", hashlib.sha256(
            G._plain(key).encode("utf-8")).hexdigest())])
    return key, identity


def write(ledger, path=LEDGER_PATH):
    if os.path.exists(path):
        raise ValueError("%s already exists; the ledger is written once" % path)
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            fh.write(G._pretty(ledger) + "\n")
        os.rename(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return G._sha_file(path)
