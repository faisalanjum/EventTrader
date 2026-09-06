V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 /home/faisal/EventMarketDB/venv/bin/python3 - <<'PY'
import io
base = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/"
        "scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/")

# ---- 1. ONE fail-closed reader/validator, in the inventory module -------------
p = base + "a7_reference_inventory.py"
s = io.open(p, encoding="utf-8").read(); o = s
s = s.replace('''def card_of(row):
    """The COLLISION KEY of an inventory row - NOT the card a model receives.

    Same three fields in the same order, but the quote appears as its sha256
    because the inventory stores the hash, not the text. Hashing is injective
    over the rows, so a collision count taken here is exactly the collision
    count of the served card; `a7_g23_build.reference_card` serves the raw
    quote. The two are pinned to each other by test.
    """
    return collections.OrderedDict([
        ("quote_sha256", row["quote_sha256"]),
        ("reference_name", row["reference_name"]),
        ("values", row["values"])])


''', '''''')

s = s.replace('''def read(path=INVENTORY_PATH):
    """The frozen inventory document. One reader, so no consumer re-derives
    the path or the schema check."""
    with io.open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("schema") != SCHEMA:
        raise ValueError("the inventory at %s is schema %r, not %r"
                         % (path, doc.get("schema"), SCHEMA))
    return doc''',
'''#: every top-level field the document must carry, and nothing else
DOC_KEYS = ("schema", "key_identity", "rows", "rows_total", "override_rows",
            "ledger_added_rows", "final_role_free_values", "evidence_origins")
#: every field one row must carry, and nothing else
ROW_KEYS = ("source_id", "gold_idx", "fact_sha256", "packet_id", "fact_index",
            "quote_sha256", "evidence_origin", "raw_label", "reference_name",
            "name_from_override", "added_by_ledger", "values")


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
    return rows''')
assert s != o and "def card_of" not in s
io.open(p, "w", encoding="utf-8").write(s)
print("validator written, card_of removed")
PY
cd "$V3" && CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 /home/faisal/EventMarketDB/venv/bin/python3 -c "
import ast, io; ast.parse(io.open('a7_reference_inventory.py', encoding='utf-8').read()); print('parses OK')"