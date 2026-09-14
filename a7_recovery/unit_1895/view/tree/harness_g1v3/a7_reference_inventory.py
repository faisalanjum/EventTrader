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
    (("0000027904-26-000022", 2), "1% increase in capacity"),
    (("0000063908-26-000032", 2), "positive global comparable guest counts"),
    (("0000898173-26-000006", 7), "comparable store sales growth"),
    (("0000898173-26-000006", 8), "record revenue"),
    (("0000898173-26-000006", 9), "operating income"),
    (("0000940944-25-000038", 3),
     "alcoholic beverages accounting for 4.7 percent"),
    (("0000940944-26-000009", 0), "LongHorn Steakhouse’s sales increase"),
    (("0000940944-26-000009", 1), "same-restaurant sales increases"),
    (("0000940944-26-000009", 2), "3.9 percent increase in average check"),
    (("0000940944-26-000009", 3),
     "3.3 percent increase in same-restaurant guest counts"),
    (("0001041061-25-000109", 2), "Company sales"),
    (("0001041061-25-000109", 3), "restaurant acquisitions"),
    (("0001104659-25-102611", 6),
     "the vast majority of our stores in Mexico and Brazil"),
    (("0001104659-26-017090", 1), "adjusted diluted net income per share"),
    (("0001104659-26-017090", 2), "higher end of our expectations"),
    (("0001104659-26-027061", 1), "4.2% increase in average ticket"),
    (("0001104659-26-027061", 2), "1.6% increase in transactions"),
    (("0001104659-26-027061", 9), "$1.8 billion remained available"),
    (("0001104659-26-032757", 1), "U.S. Supreme Court invalidated tariffs"),
    (("0001104659-26-032757", 2), "President immediately introduced new tariffs"),
    (("0001171843-26-001288", 1), "international sales"),
    (("0001171843-26-001288", 2), "below our expectations"),
    (("AAL_2026-04-23T08.30", 4), "break-even RASM on the quarter"),
    (("DAL_2026-04-08T10.00", 1), "pre-tax profit of $1 billion"),
    (("DAL_2026-04-08T10.00", 2), "flat capacity growth"),
    (("DAL_2026-04-08T10.00", 3),
     "double-digit passenger unit revenue growth"),
    (("DAL_2026-04-08T10.00", 4),
     "mid-single-digit unit revenue growth in the March quarter"),
    (("DAL_2026-04-08T10.00", 6), "gross leverage of 2.4 times"),
    (("DAL_2026-04-08T10.00", 7),
     "low teens revenue growth in the June quarter"),
    (("DRI_2026-03-19T08.30", 3), "in line with our expectations"),
    (("DRI_2026-03-19T08.30", 7), "mid-single-digit earnings per share growth"),
    (("MCD_2026-02-11T16.30", 5),
     "capital expenditure spend was 3.4 billion"),
    (("MCD_2026-02-11T16.30", 6), "above the high end of the range"),
    (("ULTA_2026-03-12T16.30", 2), "12.4% of sales"),
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


def _packets(run):
    """The packets of THE SUPPLIED prepared run.

    This read `G.PRIMARY` directly, so an inventory built for a fresh run
    silently bound the OLD run's packets.
    """
    # NO DEFAULT. The run is supplied, always: an inventory that falls back to
    # whichever run the module happens to name is an inventory that can bind
    # the wrong evidence and look entirely correct (Codex SEQ 1471 item 3).
    # THE PREPARED IDENTITY ONLY - never a bare path, never a default, and
    # never a `PR.load` of its own. `a1_plan_for_run` lawfully treats a
    # directory with no plan as the default K-fields door, so a wrong path
    # returned the DEFAULT run's 196 packets and looked entirely correct; and a
    # path could name a lawful run of ANY era. `G.run_of` is the single live
    # gate, so this is bound to the same current run as every other consumer
    # (Codex SEQ 1473 item 1).
    primary = G.run_of(run)
    import raw_transport as RT
    plan = RT.a1_plan_for_run(primary)
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


def build(key, run):
    """-> (rows, problems). One row per accepted claim, bound exactly."""
    mapped, origins = _effective_origins()
    packets = _packets(run)
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


def read(path=None):
    """The frozen inventory document, STRUCTURALLY checked. See `validate` for
    the proof against the live authorities."""
    # LATE BINDING. `path=INVENTORY_PATH` bound the constant at import, so the
    # inventory location could not be redirected at all - a test that pointed
    # the serving path at another document silently read the real one and
    # proved nothing.
    path = INVENTORY_PATH if path is None else path
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


def expected_document(run):
    """THE canonical expected inventory, rebuilt from the live authorities.

    ONE builder. Everything the document should contain is DERIVED here - the
    live key and its identity, the effective per-event artifacts, and the
    approved span-override table as immutable evaluation data - so `validate`
    can compare the whole serialized document instead of spot-checking fields.

    Field-by-field membership checks let plausible SAME-DOMAIN swaps through: a
    real packet id from the wrong row, a real evidence origin from the wrong
    correction, a real reference name that is still a substring of the quote.
    An exact comparison has no such gap.
    """
    import a7_key_correction as K
    key, identity = K.current_key()
    rows, problems = build(key, run)
    if problems:
        raise ValueError("the expected inventory does not derive: %s"
                         % problems[:3])
    return collections.OrderedDict([
        ("schema", SCHEMA),
        ("key_identity", identity),
        ("rows", rows),
        ("rows_total", len(rows)),
        ("override_rows", sum(1 for r in rows if r["name_from_override"])),
        ("ledger_added_rows", sum(1 for r in rows if r["added_by_ledger"])),
        ("final_role_free_values", sum(len(r["values"]) for r in rows)),
        ("evidence_origins",
         dict(collections.Counter(r["evidence_origin"] for r in rows))),
    ])


def _first_difference(want, got):
    """The first field where the two documents disagree, for a usable refusal."""
    def flat(o, path=""):
        if isinstance(o, dict):
            for k in sorted(o):
                for x in flat(o[k], path + "/" + str(k)):
                    yield x
        elif isinstance(o, list):
            for i, v in enumerate(o):
                for x in flat(v, path + "[%d]" % i):
                    yield x
        else:
            yield path, o
    a, b = dict(flat(want)), dict(flat(got))
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            return "%s: expected %r, document has %r" % (
                k, str(a.get(k))[:60], str(b.get(k))[:60])
    return None


def validate(path=None, run=None):
    """-> {(source_id, gold_idx): row}, EXACT-COMPARED to the expected document.

    A REFUSAL, never a repair: an inventory that is not byte-for-byte the
    document the live authorities produce is not a weaker inventory, it is a
    different one.
    """
    doc = read(path)
    want = expected_document(run)
    if G._plain(doc) != G._plain(want):
        raise ValueError("the reference inventory is not the expected "
                         "document: %s" % _first_difference(want, doc))
    return collections.OrderedDict(
        ((r["source_id"], r["gold_idx"]), r) for r in doc["rows"])

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


def write(doc, path=None):
    path = INVENTORY_PATH if path is None else path
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
