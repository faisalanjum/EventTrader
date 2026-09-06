"""The raw REFERENCE inventory: one evaluation-data row per reviewed claim.

Codex SEQ 1462/1463. This is benchmark DATA, not semantic code. It carries no
name list, no regex, no slice-to-word converter and no branch on meaning: the
reference name is the originating packet's own `raw_label_or_claim`, and where
one packet settled into several facts and that shared label cannot identify a
branch, the smallest exact source span the effective answer-key decision binds
to that fact is recorded ONCE, as data, with its origin.

THE BINDING IS EXACT, never a (source_id, quote) lookup: nine source/quote
groups cover eighteen different packets, so a first-packet shortcut would
attach a row to another packet's label. Every row binds packet_id and
fact_index through the PER-EVENT effective origin returned by
`build_kfields_final.v6_shards`, because later v4/v5/v6 corrections supersede
the earlier decision directory selectively.
"""
import collections
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

SCHEMA = "a7_reference_inventory/1"
INVENTORY_PATH = "/tmp/a7_reference_inventory.json"

#: Exact source spans, recorded as DATA for rows whose packet label cannot
#: identify the branch. Each was checked against its own quote and its
#: effective decision fact before being written here; none is computed, and
#: nothing in this module reads their text to make a decision.
#: key: (source_id, current gold_idx) -> the exact span
SPAN_OVERRIDES = collections.OrderedDict([
    (("0000006201-26-000031", 5), "domestic"),
    (("0000006201-26-000031", 6), "Pacific"),
    (("0000898173-26-000006", 7), "comparable store sales growth"),
    (("0000898173-26-000006", 8), "record revenue"),
    (("0000898173-26-000006", 9), "operating income"),
    (("0000940944-26-000009", 0), "LongHorn Steakhouse’s sales increase"),
    (("0000940944-26-000009", 1), "same-restaurant sales increases"),
    (("0001041061-25-000109", 2), "Company sales"),
    (("0001041061-25-000109", 3), "restaurant acquisitions"),
    (("0001104659-26-017090", 1), "adjusted diluted net income per share"),
    (("0001104659-26-017090", 2), "higher end of our expectations"),
    (("0001104659-26-032757", 1), "U.S. Supreme Court invalidated tariffs"),
    (("0001104659-26-032757", 2), "President immediately introduced new tariffs"),
    (("0001171843-26-001288", 1), "international sales"),
    (("0001171843-26-001288", 2), "below our expectations"),
    (("DAL_2026-04-08T10.00", 2), "flat capacity growth"),
    (("DAL_2026-04-08T10.00", 3),
     "double-digit passenger unit revenue growth"),
    (("DAL_2026-04-08T10.00", 4),
     "mid-single-digit unit revenue growth in the March quarter"),
    (("DRI_2026-03-19T08.30", 3), "in line with our expectations"),
    (("DRI_2026-03-19T08.30", 7), "mid-single-digit earnings per share growth"),
    (("MCD_2026-02-11T16.30", 5),
     "capital expenditure spend was 3.4 billion"),
    (("MCD_2026-02-11T16.30", 6), "above the high end of the range"),
])


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _effective_origins():
    """-> ({source_id: {gold_idx: (packet_id, fact_index)}}, {sid: origin}).

    The flattened effective facts of each event, in packet then fact order.
    Proven one-to-one against the base key before it is used.
    """
    import build_kfields_final as F
    bound = G._a6().bound()
    shards, _raws, origins, bad = F.v6_shards(bound)
    if bad:
        raise ValueError("the effective key does not derive: %s" % bad[:2])
    mapped = collections.OrderedDict()
    for sid, shard in shards.items():
        flat = []
        for packet_id, row in shard["rows"].items():
            for fact_index, _fact in enumerate(row.get("facts") or []):
                flat.append((packet_id, fact_index))
        mapped[sid] = {n: pair for n, pair in enumerate(flat)}
    return mapped, dict(origins)


def _packets():
    import raw_transport as RT
    plan = RT.a1_plan_for_run(G.PRIMARY)
    return {p["packet_id"]: p for p in plan["packets"]}


def _values(fact):
    """The role-free reference values: the owner's numeric slots, in owner slot
    order, de-duplicated by equal value, keeping the first exact scalar.

    No slot name is exposed and no value is stringified to compare: the
    de-duplication compares the scalars themselves.
    """
    from driver.core.prepared_fact_v2 import NUMERIC_SLOTS
    item = fact.get("item") or {}
    out, seen = [], []
    for slot in NUMERIC_SLOTS:
        stated = item.get(slot)
        value = (stated.get("value") if isinstance(stated, dict) else stated)
        if value is None:
            continue
        if any(value == kept for kept in seen):
            continue
        seen.append(value)
        out.append(value)
    return out


def _ledger_sha():
    import a7_key_correction as K
    return _sha(io.open(K.LEDGER_PATH, encoding="utf-8").read())


def build(key):
    """-> (rows, problems). One row per accepted claim, bound exactly."""
    mapped, origins = _effective_origins()
    packets = _packets()
    rows, problems = [], []
    for sid in sorted(key):
        for gold_idx, fact in enumerate(key[sid]):
            if fact.get("du_worthy") is not True:
                continue
            item = fact.get("item") or {}
            quote = item.get("quote")
            pair = mapped.get(sid, {}).get(gold_idx)
            added = pair is None
            packet_id = fact_index = None
            label = None
            if not added:
                packet_id, fact_index = pair
                packet = packets.get(packet_id)
                if packet is None:
                    problems.append("%s gold %d names an unknown packet %s"
                                    % (sid, gold_idx, packet_id))
                    continue
                label = (packet["item"] or {}).get("raw_label_or_claim")
                if (packet["item"] or {}).get("quote") != quote:
                    problems.append("%s gold %d does not carry its packet's "
                                    "quote" % (sid, gold_idx))
            # A LEDGER-ADDED ROW STILL HAS A SOURCE. Erasing its packet lost
            # the only record of WHERE the claim was stated. It keeps the
            # packet whose quote it carries, and `fact_index` stays null
            # because that packet's own settled facts are its siblings, not
            # this restored row - labelling it index 0 would claim the
            # sibling's seat.
            semantic = None
            if added and quote is not None:
                same = sorted(pid for pid, pk in packets.items()
                              if pk["source_id"] == sid
                              and (pk["item"] or {}).get("quote") == quote)
                if len(same) == 1:
                    packet_id = same[0]
                elif len(same) > 1:
                    problems.append("%s gold %d: its quote is stated by %d "
                                    "packets, so its source is ambiguous"
                                    % (sid, gold_idx, len(same)))
                    continue
                semantic = collections.OrderedDict([
                    ("ledger_action", "add_fact"),
                    ("law", "FINAL_DESIGN.md:153"),
                    ("ledger_sha256", _ledger_sha())])
            override = SPAN_OVERRIDES.get((sid, gold_idx))
            name = override if override is not None else label
            if name is None:
                problems.append("%s gold %d has no reference name"
                                % (sid, gold_idx))
                continue
            if quote is None or name not in quote:
                problems.append("%s gold %d: reference name %r is not an exact "
                                "span of its quote" % (sid, gold_idx, name))
                continue
            rows.append(collections.OrderedDict([
                ("source_id", sid), ("gold_idx", gold_idx),
                ("fact_sha256", _sha(G._plain(fact))),
                ("packet_id", packet_id), ("fact_index", fact_index),
                ("quote_sha256", _sha(quote)),
                ("evidence_origin", origins.get(sid)),
                ("raw_label", label),
                ("reference_name", name),
                ("name_from_override", override is not None),
                ("added_by_ledger", added),
                # TWO DISTINCT TRUTHS: the packet above is SOURCE provenance;
                # this is SEMANTIC provenance - which ledger act created the
                # row and under which law.
                ("semantic_provenance", semantic),
                ("values", _values(fact))]))
    return rows, problems


#: every top-level field the document must carry, and nothing else
DOC_KEYS = ("schema", "key_identity", "rows", "rows_total", "override_rows",
            "ledger_added_rows", "final_role_free_values", "evidence_origins")
#: every field one row must carry, and nothing else
ROW_KEYS = ("source_id", "gold_idx", "fact_sha256", "packet_id", "fact_index",
            "quote_sha256", "evidence_origin", "raw_label", "reference_name",
            "name_from_override", "added_by_ledger", "semantic_provenance",
            "values")


def read(path=INVENTORY_PATH):
    """The frozen inventory document, STRUCTURALLY checked. See `validate` for
    the proof against the live authorities."""
    with io.open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("schema") != SCHEMA:
        raise ValueError("the inventory at %s is schema %r, not %r"
                         % (path, doc.get("schema"), SCHEMA))
    if sorted(doc) != sorted(DOC_KEYS):
        raise ValueError("the inventory carries %s, not exactly %s"
                         % (sorted(doc), sorted(DOC_KEYS)))
    seen = set()
    for row in doc["rows"]:
        if sorted(row) != sorted(ROW_KEYS):
            raise ValueError("an inventory row carries %s, not exactly %s"
                             % (sorted(row), sorted(ROW_KEYS)))
        ident = (row["source_id"], row["gold_idx"])
        if ident in seen:
            raise ValueError("the inventory repeats identity %s" % (ident,))
        seen.add(ident)
    if len(doc["rows"]) != doc["rows_total"]:
        raise ValueError("the inventory holds %d rows but claims %d"
                         % (len(doc["rows"]), doc["rows_total"]))
    return doc


def validate(key, positions, path=INVENTORY_PATH):
    """-> {(source_id, gold_idx): row}, PROVED against the live authorities.

    ONE owner for this boundary. It used to be two: a raw json.load in the
    packet builder that admitted a duplicate identity by overwriting it, and a
    separate structural read nothing on the serving path called. Everything
    below is a REFUSAL, never a repair - an inventory that cannot be proved is
    not a weaker inventory, it is a different one.
    """
    doc = read(path)
    problems = []
    live_ids = {(sid, gi) for sid in key for gi in positions(key[sid])}
    rows = {(r["source_id"], r["gold_idx"]): r for r in doc["rows"]}

    if set(rows) != live_ids:
        problems.append("identity set differs from the live key: missing %s, "
                        "unknown %s"
                        % (sorted(live_ids - set(rows))[:3],
                           sorted(set(rows) - live_ids)[:3]))
    if doc["rows_total"] != len(live_ids):
        problems.append("rows_total %d is not the live accepted count %d"
                        % (doc["rows_total"], len(live_ids)))

    packets = _packets()
    values_seen = 0
    for ident in sorted(set(rows) & live_ids):
        row = rows[ident]
        sid, gold_idx = ident
        fact = key[sid][gold_idx]
        item = fact.get("item") or {}
        quote = item.get("quote")
        if quote is None or _sha(quote) != row["quote_sha256"]:
            problems.append("%s gold %d: quote hash" % ident)
        if _sha(G._plain(fact)) != row["fact_sha256"]:
            problems.append("%s gold %d: fact hash" % ident)
        # DETERMINISTIC RE-DERIVATION, compared on the exact serialized value so
        # a Decimal is never rejected merely for serializing as a string.
        if G._plain(_values(fact)) != G._plain(row["values"]):
            problems.append("%s gold %d: values do not re-derive" % ident)
        values_seen += len(row["values"])
        if row["reference_name"] is None or row["reference_name"] not in (quote or ""):
            problems.append("%s gold %d: reference name is not a span" % ident)
        if row["added_by_ledger"]:
            if row["fact_index"] is not None:
                problems.append("%s gold %d: a ledger-added row may not claim "
                                "a settled fact's index" % ident)
            if not row["semantic_provenance"]:
                problems.append("%s gold %d: no semantic provenance" % ident)
            # SOURCE provenance is a separate truth and is equally required:
            # erasing the packet loses the only record of where the claim was
            # stated, which is exactly what the first build did.
            if row["packet_id"] is None:
                problems.append("%s gold %d: a ledger-added row still has a "
                                "source packet and may not erase it" % ident)
        else:
            if row["fact_index"] is None:
                problems.append("%s gold %d: a settled row needs its index"
                                % ident)
            if row["semantic_provenance"] is not None:
                problems.append("%s gold %d: only a ledger-added row carries "
                                "semantic provenance" % ident)
        if row["packet_id"] is not None:
            packet = packets.get(row["packet_id"])
            if packet is None:
                problems.append("%s gold %d: unknown packet %s"
                                % (sid, gold_idx, row["packet_id"]))
            elif (packet["item"] or {}).get("quote") != quote:
                problems.append("%s gold %d: packet quote" % ident)
        if row["evidence_origin"] not in doc["evidence_origins"]:
            problems.append("%s gold %d: unknown evidence origin" % ident)

    if values_seen != doc["final_role_free_values"]:
        problems.append("values total %d is not the claimed %d"
                        % (values_seen, doc["final_role_free_values"]))
    n_ovr = sum(1 for r in doc["rows"] if r["name_from_override"])
    if n_ovr != doc["override_rows"]:
        problems.append("override rows %d is not the claimed %d"
                        % (n_ovr, doc["override_rows"]))
    n_add = sum(1 for r in doc["rows"] if r["added_by_ledger"])
    if n_add != doc["ledger_added_rows"]:
        problems.append("ledger-added rows %d is not the claimed %d"
                        % (n_add, doc["ledger_added_rows"]))
    if problems:
        raise ValueError("the reference inventory does not prove: %s"
                         % problems[:4])
    return rows


def raw_value_occurrences(key, positions):
    """-> the count BEFORE de-duplication, from the same owner `_values` uses.

    Counting the slots here rather than in a test keeps one definition of "a
    populated slot": `_values` drops a slot whose object carries no value, and
    a count that did not would report a bigger, wrong denominator.
    """
    from driver.core.prepared_fact_v2 import NUMERIC_SLOTS
    total = 0
    for sid in sorted(key):
        for gold_idx in positions(key[sid]):
            item = key[sid][gold_idx].get("item") or {}
            for slot in NUMERIC_SLOTS:
                stated = item.get(slot)
                value = (stated.get("value") if isinstance(stated, dict)
                         else stated)
                if value is not None:
                    total += 1
    return total


def write(doc, path=INVENTORY_PATH):
    if os.path.exists(path):
        raise ValueError("%s already exists; the inventory is written once"
                         % path)
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            fh.write(G._pretty(doc) + "\n")
        os.rename(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return G._sha_file(path)
