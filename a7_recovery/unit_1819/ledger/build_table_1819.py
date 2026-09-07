# -*- coding: utf-8 -*-
"""Join the 206 reference cards to the exact gold claim each is bound to.

Transport only: it reads the two pinned files and lays the card beside its bound
claim so a human can judge them. It makes no judgement, applies no matching rule
and writes nothing back.
"""
import collections, hashlib, io, json, os

P = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/"
     "targeted_1589/post_1500_exact_1626")
INV = P + "/budget_inputs_1720/out_g23/tmp__a7_reference_inventory.json"
KEY = P + "/out/a4_final_lock_1683/tmpfiles/a7_key_v9_gold.json"
U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()

inv = json.load(io.open(INV, encoding="utf-8"))
key = json.load(io.open(KEY, encoding="utf-8"))
rows, quote_ok = [], 0
for r in inv["rows"]:
    sid, gi = r["source_id"], r["gold_idx"]
    gold = key.get(sid, [])
    g = gold[gi] if gi < len(gold) else None
    it = (g or {}).get("item") or {}
    q = it.get("quote") or ""
    if sha(q) == r["quote_sha256"]:
        quote_ok += 1
    lv = lambda k: (it.get(k) or {}).get("value")
    rows.append(collections.OrderedDict([
        ("source_id", sid), ("gold_idx", gi),
        ("packet_id", r["packet_id"]),
        ("reference_name", r["reference_name"]),
        ("raw_label", r["raw_label"]),
        ("card_values", r["values"]),
        ("name_from_override", r["name_from_override"]),
        ("evidence_origin", r["evidence_origin"]),
        ("gold_driver_name", it.get("driver_name")),
        ("gold_fact_type", (g or {}).get("fact_type")),
        ("gold_level_low", lv("level_low")), ("gold_level_high", lv("level_high")),
        ("gold_change", lv("change_value")),
        ("gold_comparison_low", lv("comparison_low")),
        ("gold_level_unit", it.get("level_unit")),
        ("gold_slice_parts", it.get("slice_parts")),
        ("gold_quote", q), ("quote_sha256", r["quote_sha256"]),
        ("fact_sha256", r["fact_sha256"])]))
io.open(U + "/logs/CARDS_206.json", "w", encoding="utf-8").write(
    json.dumps(rows, indent=1) + "\n")
# how many events carry more than one card on the SAME quote - the split class
byq = collections.Counter((r["source_id"], r["quote_sha256"]) for r in rows)
shared = {k for k, n in byq.items() if n > 1}
print("cards            : %d" % len(rows))
print("quote hash joins : %d of %d" % (quote_ok, len(rows)))
print("distinct events  : %d" % len({r["source_id"] for r in rows}))
print("cards sharing a quote with a sibling: %d in %d quote groups"
      % (sum(n for k, n in byq.items() if n > 1), len(shared)))
print("overrides        : %d" % sum(1 for r in rows if r["name_from_override"]))
