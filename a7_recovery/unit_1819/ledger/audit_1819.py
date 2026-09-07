# -*- coding: utf-8 -*-
"""The 206-row reference-card meaning disposition + its first failing test.

The DECISION is mine and is carried as an explicit list of judged rows in
candidate/EXPECTED_CARDS.json; this script only records those judgments beside
every card and checks them against the source. It contains no matching rule,
no word list and no field-to-text converter: it cannot decide a row by itself.
"""
import collections, hashlib, io, json, os

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cards = json.load(io.open(U + "/logs/CARDS_206.json", encoding="utf-8"))
exp = json.load(io.open(U + "/candidate/EXPECTED_CARDS.json", encoding="utf-8"))
judged = {(r["source_id"], r["gold_idx"]): r for r in exp["rows"]}
ctrl = exp["positive_control"]
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
byq = collections.Counter((c["source_id"], c["quote_sha256"]) for c in cards)

# ---- 1. the 206-row disposition -------------------------------------------
rows, counts = [], collections.Counter()
for c in cards:
    k = (c["source_id"], c["gold_idx"])
    shared = byq[(c["source_id"], c["quote_sha256"])] > 1
    if k in judged:
        d, why = "CHANGE", judged[k]["reason"]
    else:
        d = "KEEP"
        why = ("its quote covers only this claim and the name states it"
               if not shared else
               "shares a quote with a sibling, and the card's own name or its "
               "distinct values bind it to this branch")
    counts[d] += 1
    rows.append(collections.OrderedDict([
        ("source_id", c["source_id"]), ("gold_idx", c["gold_idx"]),
        ("packet_id", c["packet_id"]), ("fact_sha256", c["fact_sha256"]),
        ("quote_sha256", c["quote_sha256"]),
        ("gold_driver_name", c["gold_driver_name"]),
        ("reference_name", c["reference_name"]),
        ("shares_quote_with_sibling", shared),
        ("disposition", d), ("reason", why),
        ("proposed_reference_name",
         judged[k]["expected_reference_name"] if k in judged else None)]))
io.open(U + "/logs/DISPOSITION_206.json", "w", encoding="utf-8").write(
    json.dumps(collections.OrderedDict([
        ("rows_total", len(rows)), ("counts", dict(counts)), ("rows", rows)]),
        indent=1) + "\n")

# ---- 2. every proposed span must be VERBATIM in its own bound quote --------
quote = {(c["source_id"], c["gold_idx"]): c["gold_quote"] for c in cards}
span_checks = []
for k, r in sorted(judged.items()):
    q = quote.get(k, "")
    span_checks.append(collections.OrderedDict([
        ("source_id", k[0]), ("gold_idx", k[1]),
        ("proposed", r["expected_reference_name"]),
        ("verbatim_substring_of_its_own_quote",
         r["expected_reference_name"] in q)]))

# ---- 3. THE RED: the current producer's card against the judged expectation
results = []
def check(name, expectation, got):
    results.append(collections.OrderedDict([
        ("check", name), ("expected", expectation), ("observed", got),
        ("status", "GREEN" if expectation == got else "RED")]))

current = {(c["source_id"], c["gold_idx"]): c["reference_name"] for c in cards}
for k, r in sorted(judged.items()):
    check("%s g%s card identifies its own branch" % (k[0], k[1]),
          r["expected_reference_name"], current.get(k))
ck = (ctrl["source_id"], ctrl["gold_idx"])
check("POSITIVE CONTROL %s g%s already correct" % ck,
      ctrl["expected_reference_name"], current.get(ck))

doc = collections.OrderedDict([
    ("disposition_counts", dict(counts)),
    ("rows_total", len(rows)),
    ("proposed_span_checks", span_checks),
    ("all_proposed_spans_verbatim",
     all(s["verbatim_substring_of_its_own_quote"] for s in span_checks)),
    ("producer_checks", results),
    ("red", sum(1 for r in results if r["status"] == "RED")),
    ("green", sum(1 for r in results if r["status"] == "GREEN"))])
io.open(U + "/logs/AUDIT_TEST_1819.json", "w", encoding="utf-8").write(
    json.dumps(doc, indent=1) + "\n")

print("  disposition: %s  total %d" % (dict(counts), len(rows)))
print("  every proposed span is verbatim in its own quote: %s"
      % doc["all_proposed_spans_verbatim"])
bad = [s for s in span_checks if not s["verbatim_substring_of_its_own_quote"]]
for s in bad:
    print("    NOT VERBATIM: %s g%s %r" % (s["source_id"], s["gold_idx"], s["proposed"]))
print("  producer vs judged expectation: %d RED, %d GREEN"
      % (doc["red"], doc["green"]))
for r in results:
    if r["status"] == "GREEN":
        print("    GREEN %s" % r["check"])
