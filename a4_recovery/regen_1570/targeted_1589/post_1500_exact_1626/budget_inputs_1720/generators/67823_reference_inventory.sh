V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
cat > "$V3/a7_reference_inventory.py" <<'PYEOF'
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
                ("values", _values(fact))]))
    return rows, problems


def card_of(row):
    """The MODEL-VISIBLE part of an inventory row. Bindings never travel."""
    return collections.OrderedDict([
        ("quote_sha256", row["quote_sha256"]),
        ("reference_name", row["reference_name"]),
        ("values", row["values"])])


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
PYEOF
cd "$V3" && CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 1800 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY' 2>&1 | grep -vi warning | tail -20
import sys, json, collections; sys.path.insert(0,".")
import a7_key_correction as K, a7_reference_inventory as R
key, ident = K.current_key()
rows, probs = R.build(key)
print("inventory rows:", len(rows), "| problems:", len(probs))
for p in probs[:5]: print("   ", p[:110])
if not probs:
    ov=sum(1 for r in rows if r["name_from_override"])
    added=sum(1 for r in rows if r["added_by_ledger"])
    vals=sum(len(r["values"]) for r in rows)
    print("rows from an override span:", ov, "| ledger-added:", added, "| final role-free values:", vals)
    uniq=collections.Counter((r["source_id"], r["quote_sha256"], r["reference_name"], tuple(str(v) for v in r["values"])) for r in rows)
    clash={k:v for k,v in uniq.items() if v>1}
    print("collisions AFTER the inventory:", len(clash))
    for k,v in list(clash.items())[:3]: print("    ", k[0], k[2], v)
PY