"""#827 — UNIT DECLARATIONS (simple AND divide), counted PER DECLARATION.

NO LONGER DIVIDE-ONLY. The graph query filtered `u.is_divide = '1'`, so when a
simple-unit branch was added downstream it could never receive a row: the
simple list would have been empty, and empty reads as "nothing to report"
rather than "never ran". The filter is gone, `is_divide` is returned and
carried in the shape key, the two kinds are accounted separately, and a
reachability detector fails the run if either branch sees nothing.

Simple declarations are classified from the filing's `expanded_measures` and
divide ones from `expanded_numerator`. That work lives HERE because this side
parses the document and therefore holds each measure's in-scope namespace; the
graph-only census cannot, since `Unit.name` is the filing's own prefix.


WHAT THE PREVIOUS VERSION GOT WRONG. It read ONE filing declaration per graph
shape and then credited every fact carrying that shape — 113 declarations
standing in for 11,942. The reasoning was self-contradictory in a single file:
it argued (correctly) that the graph name is the measures CONCATENATED and so
cannot be split back reliably, then used that same ambiguous name as the
grouping key, which assumes the very uniqueness it had just denied. It also
asserted that the graph did not move without recording a transaction bracket.

WHAT THIS ONE DOES. The unit of account is the DECLARATION — one
(graph shape, accession, unit_ref) triple — because that is what a filing
actually declares. Every declaration and every fact is placed in exactly one
bucket, read or unread, and the totals must add up or the receipt fails. The
graph read is bracketed by `lastCommittedTxn` either side.

THE QUESTION IT CAN ANSWER: do two filings ever declare DIFFERENT structures
that land on the SAME graph name? Any such name is reported as a conflict and
makes shape-level classification unsound.

THE QUESTION IT CANNOT ANSWER: whether the unread declarations agree. They are
reported as unread, never as passed. The frozen cache is the only source, so
this receipt is reproducible by anyone holding it — an earlier run borrowed 43
filings from a temporary directory, which made its numbers unrepeatable.

Read-only: one Neo4j read lane, local files, no network, no AI, no writes.

Run:  venv/bin/python receipts_827/divide_unit_numerators.py
Out:  receipts_827/13_divide_unit_numerators.json
"""
import collections
import datetime
import hashlib
import json
import os
import sys
import warnings
from collections import defaultdict

warnings.filterwarnings("ignore")
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)
OUT = os.path.join(_HERE, "13_divide_unit_numerators.json")
CACHE = os.path.join(_REPO, "scripts", "driver_seed", "relocate_probe",
                     "inline_html_cache")
MANIFEST = os.path.join(_HERE, "01b_ix_input_manifest.txt")


def verify_frozen_cache():
    """PROVE the cache is frozen instead of calling it frozen.

    This census described its source as "the frozen cache" and checked nothing:
    a filing edited, added or removed underneath it would have changed every
    number in the receipt silently. The manifest of 1,769 name+sha256 pairs
    already existed and was simply never read. Every name and every hash is
    checked, not a sample — a partial check on a frozen-input claim is the
    claim restated, not evidence for it.
    """
    with open(MANIFEST) as fh:
        pinned = dict(line.split() for line in fh if line.strip())
    on_disk = {f for f in os.listdir(CACHE) if f.endswith(".htm")}
    if on_disk != set(pinned):
        raise SystemExit(
            f"the cache is NOT the pinned input set: "
            f"{len(on_disk - set(pinned))} unpinned file(s) present, "
            f"{len(set(pinned) - on_disk)} pinned file(s) missing")
    for name in sorted(pinned):
        with open(os.path.join(CACHE, name), "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        if digest != pinned[name]:
            raise SystemExit(f"{name} does not match its pinned sha256 — the "
                             f"cache changed under this receipt")
    return len(pinned)

#: ONE ROW PER DECLARATION. `collect(DISTINCT ...)` used to fold every filing
#: that declares a shape into one list, which is exactly what let a single
#: representative speak for all of them.
DECLARATIONS = (
    # EVERY DECLARATION, NOT ONLY DIVIDES. The `WHERE u.is_divide = '1'`
    # filter made the simple branch downstream UNREACHABLE, so a simple
    # census built on it would have been empty and green. `is_divide` is
    # now RETURNED and the two kinds are accounted separately.
    "MATCH (f:Fact)-[:HAS_UNIT]->(u:Unit) "
    "MATCH (f)-[:REPORTS]->(x:XBRLNode) "
    "RETURN u.name AS name, u.is_divide AS is_divide, "
    "       x.accessionNo AS accession, "
    "       f.unit_ref AS unit_ref, count(f) AS facts, "
    "       sum(CASE WHEN f.is_numeric = '1' AND f.is_nil = '0' THEN 1 ELSE 0 END) "
    "           AS facts_numeric_nonnil "
    "ORDER BY name, is_divide, accession, unit_ref")


#: MODULE SCOPE, because `tally` and `_emit` use them and `main` no longer
#: does. They were local to `main` while everything lived there.
from driver.core.xbrl_attach import candidate_units_for          # noqa: E402
from driver.relocation.inline_html import prepare, refused        # noqa: E402


def main():
    from graph_census import GraphDatabase, run_read_only, snapshot_tx

    # BEFORE the graph is touched: if the inputs are not the pinned ones there
    # is no point measuring anything against them.
    verified_filings = verify_frozen_cache()
    print(f"frozen cache PROVEN: {verified_filings:,} filings, "
          f"every name and sha256 matched", flush=True)

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ.get("NEO4J_USERNAME", "neo4j"),
              os.environ["NEO4J_PASSWORD"]))
    try:
        with driver.session(database="neo4j") as session:
            tx_before = snapshot_tx(session)
            result, _kind = run_read_only(session, DECLARATIONS)
            rows = [r.data() for r in result]
            tx_after = snapshot_tx(session)
    finally:
        driver.close()

    cached = {f[:-4] for f in os.listdir(CACHE) if f.endswith(".htm")}
    return _emit(tally(rows, {}, cached), tx_before, tx_after,
                 verified_filings, cached)


def tally(rows, parsed, cached):
    """THE PER-DECLARATION ACCOUNTING — rows in, accumulators out.

    Lifted out of `main` so a detector can drive it with two hand-made rows
    instead of a graph and 1,769 filings. While it lived inline nothing could
    reach it, and that is exactly how a branch no row could enter, and a
    read-counter that skipped the simple path, both survived review.

    NOT PURE, and saying so plainly rather than adding an abstraction to
    make the word true: it is graph-free and writes no output file, but it
    still opens and parses cache files lazily into `parsed`. A caller that
    pre-populates `parsed` — as the detector does — never touches the disk.
    """
    # name -> structure -> {declarations, facts}; structure is the FILING's own
    # (numerator, denominator), never anything split out of the graph name.
    observed = defaultdict(lambda: defaultdict(
        lambda: {"declarations": 0, "facts": 0}))
    observed_simple = defaultdict(lambda: defaultdict(
        lambda: {"declarations": 0, "facts": 0}))
    #: ONLY the independent query totals. The read counters that used to live
    #: here are derived from `routes` now, so they cannot disagree with it.
    totals = {"declarations": 0, "facts": 0, "facts_numeric_nonnil": 0}
    per_name = defaultdict(lambda: {"facts": 0, "declarations": 0,
                                    "declarations_read": 0})
    #: EVERY ROW LANDS IN EXACTLY ONE ROUTE, carrying BOTH its declaration and
    #: its facts. The receipt used to derive "never read" as `total - read` and
    #: publish that under the cache scope limit — so the cached document
    #: refusal, an unusable declaration and a flag conflict were all silently
    #: attributed to uncached filings. Subtraction cannot tell those apart;
    #: only an explicit route can.
    routes = {name: {"declarations": 0, "facts": 0} for name in (
        "read_simple", "read_divide", "uncached", "document_refused",
        "declaration_unusable", "flag_disagreement")}

    def route(name, row):
        """ONE increment for both numbers, so a route can never count a
        declaration without its facts — the two drifting apart is precisely
        how a total stops meaning anything."""
        routes[name]["declarations"] += 1
        routes[name]["facts"] += row["facts"]

    #: Reason diagnostics beside the routes: same events, named. Each carries
    #: declarations AND facts so a reason can be weighed, not just listed.
    unreadable = defaultdict(lambda: {"declarations": 0, "facts": 0})
    document_refusals = defaultdict(lambda: {"declarations": 0, "facts": 0})
    flag_disagreements = []
    #: MEASURED during routing, so the scope statement reports what this
    #: run actually saw instead of a number copied from an older one.
    uncached_accessions = set()
    # THE FLAG VOCABULARY IS VALIDATED OVER EVERY ROW, BEFORE ANY SKIP.
    # It used to be checked inside the loop, below the `acc not in cached`
    # continue — so an unknown flag attached to an UNCACHED filing walked
    # straight past it. The whole population is proven here and the counts are
    # recorded, so the receipt states what it actually saw rather than what
    # the cached subset happened to contain.
    #
    # Measured read-only over the whole label before requiring it:
    # '0' 6,844 and '1' 113, nothing else, transaction bracket unmoved.
    is_divide_counts = collections.Counter(r["is_divide"] for r in rows)
    unknown_flags = {v: n for v, n in is_divide_counts.items()
                     if v not in ("0", "1")}
    if unknown_flags:
        raise SystemExit(
            "unknown graph is_divide value(s) %r — the proven vocabulary is "
            "'0'/'1'; a new spelling must be adjudicated, never guessed"
            % (unknown_flags,))

    for row in sorted(rows, key=lambda r: (r["name"], r["is_divide"] or "",
                                           r["accession"], r["unit_ref"])):
        # `(name, is_divide)` KEYS THE SHAPE. One spelling can be stored both
        # as a simple and as a divide unit, and collapsing those would let one
        # kind speak for the other.
        name, acc, uref = ((row["name"], row["is_divide"]),
                           row["accession"], row["unit_ref"])
        totals["declarations"] += 1
        totals["facts"] += row["facts"]
        totals["facts_numeric_nonnil"] += row["facts_numeric_nonnil"]
        per_name[name]["facts"] += row["facts"]
        per_name[name]["declarations"] += 1
        if acc not in cached:
            uncached_accessions.add(acc)
            route("uncached", row)
            continue
        if acc not in parsed:
            with open(os.path.join(CACHE, acc + ".htm"), encoding="utf-8",
                      errors="replace") as fh:
                # ONLY THE UNITS ARE KEPT. Retaining the whole prepared filing
                # held its parse tree, visible text and every node span for all
                # 1,769 filings at once: the run reached 47 GB and left 586 MB
                # free before it was stopped. The units dict is a few hundred
                # bytes; nothing else here is ever read.
                # UNITS, OR THE DOCUMENT'S OWN REFUSAL — never the full tree.
                # `prepare` returns NO `units` key when the document is not a
                # well-formed Inline XBRL report, so `[...]["units"]` raised
                # KeyError and took the whole census down. At least one filing
                # in the current population does exactly that
                # (0001579241-25-000008, 1,467 facts, 4 declarations), so this
                # is a live crash, not a hypothetical.
                #
                # A refused document is ACCOUNTED, not repaired and not
                # special-cased: its rows land in one explicit unreadable
                # bucket below and the independent totals still balance.
                _prep = prepare(fh.read())
                _why = refused(_prep)
                if "units" in _prep:
                    parsed[acc] = _prep["units"]
                elif _why:
                    parsed[acc] = _why       # the document's OWN refusal
                else:
                    # NEITHER usable units NOR a documented refusal is a
                    # PROGRAMMER/TOOL defect, not a fact about the filing.
                    # A `.get(..., "document_refused")` fallback would invent a
                    # reason and let the defect travel into the receipt looking
                    # like evidence.
                    raise SystemExit(
                        f"prepare() returned neither units nor a documented "
                        f"refusal for {acc}: keys {sorted(_prep)}")
            if len(parsed) % 200 == 0:
                print(f"   parsed {len(parsed)} filings", flush=True)
        declared = parsed[acc]
        # THE INVARIANT IS ENFORCED WHERE IT IS CONSUMED, not only where it is
        # produced. A caller may pre-populate `parsed` — the detector does —
        # and anything other than a units dict or a documented refusal string
        # is a defect. Without this it surfaced as a bare `AttributeError`
        # deep in the loop, which is the raw-exception-instead-of-a-truthful-
        # refusal shape this programme keeps removing.
        if not isinstance(declared, (dict, str)):
            raise SystemExit(
                f"parsed[{acc!r}] is {type(declared).__name__}, not units nor "
                f"a documented refusal — neither units nor a documented "
                f"refusal is a programmer defect, never a fact about a filing")
        if isinstance(declared, str):
            # THE DOCUMENT ITSELF WAS REFUSED, so no declaration in it can be
            # read. The exact reason is recorded and adjudicated afterwards —
            # NOT labelled a source defect in advance, because `prepare()` also
            # reports view disagreement, whose cause is not proven to be the
            # filing's fault. Kept in its OWN accumulator so it cannot collapse
            # into the census-invalidating bucket below: collapsed, the one
            # strict refusal this population provably contains would make a
            # successful census impossible.
            document_refusals[declared]["declarations"] += 1
            document_refusals[declared]["facts"] += row["facts"]
            route("document_refused", row)
            continue
        unit = declared.get(uref)
        if not isinstance(unit, dict):
            # the filing is here but the declaration is not usable: refused by
            # the structure rule, or absent. Counted, never hidden.
            _why_u = unit if isinstance(unit, str) else "absent"
            unreadable[_why_u]["declarations"] += 1
            unreadable[_why_u]["facts"] += row["facts"]
            route("declaration_unusable", row)
            continue
        # THE GRAPH FLAG AND THE FILING MUST AGREE. Two independent statements
        # about one declaration; if they disagree neither branch can be
        # trusted, and the receipt says so instead of filing it under whichever
        # was read second.
        if (row["is_divide"] == "1") != bool(unit["is_divide"]):
            flag_disagreements.append(
                {"name": name[0], "graph_is_divide": row["is_divide"],
                 "filing_is_divide": bool(unit["is_divide"]),
                 "accession": acc, "unit_ref": uref,
                 "facts": row["facts"]})
            route("flag_disagreement", row)
            continue
        # THE TWO READ ROUTES. `declarations_read` and
        # `facts_on_read_declarations` are GONE as separate counters — they
        # said the same thing as `read_simple + read_divide` and were free to
        # drift from it. One fact, one owner.
        per_name[name]["declarations_read"] += 1
        if not unit["is_divide"]:
            skey = (tuple(unit["measures"]), tuple(unit["expanded_measures"]))
            observed_simple[name][skey]["declarations"] += 1
            observed_simple[name][skey]["facts"] += row["facts"]
            route("read_simple", row)
            continue
        route("read_divide", row)
        # THE EXPANDED IDENTITIES TRAVEL IN THE KEY. This census PARSES THE
        # FILING, so it holds each measure's in-scope namespace — the very
        # thing the graph cannot supply. Keying on the written spellings alone
        # would merge two different taxonomies that share a local name and
        # split one namespace written under two prefixes.
        key = (tuple(unit["numerator"]), tuple(unit["denominator"]),
               tuple(unit["expanded_numerator"]),
               tuple(unit["expanded_denominator"]))
        observed[name][key]["declarations"] += 1
        observed[name][key]["facts"] += row["facts"]

    return {"observed": observed, "observed_simple": observed_simple,
            "totals": totals, "per_name": per_name, "unreadable": unreadable,
            "document_refusals": document_refusals,
            "flag_disagreements": flag_disagreements,
            "routes": routes,
            "uncached_accessions": uncached_accessions,
            "is_divide_counts": is_divide_counts}


def _emit(t, tx_before, tx_after, verified_filings, cached):
    """Everything after the accounting: shapes, conflicts, proofs, receipt.

    Split from `tally` so the accounting can be tested on its own — this half
    needs the transaction bracket and writes a file, and neither belongs in a
    pure function.
    """
    observed, observed_simple = t["observed"], t["observed_simple"]
    totals, per_name = t["totals"], t["per_name"]
    unreadable, flag_disagreements = t["unreadable"], t["flag_disagreements"]
    document_refusals = t["document_refusals"]
    routes = t["routes"]
    uncached_accessions = t["uncached_accessions"]
    read_simple, read_divide = routes["read_simple"], routes["read_divide"]
    is_divide_counts = t["is_divide_counts"]
    shapes, conflicts = [], []
    for name in sorted(per_name, key=lambda n: (-per_name[n]["facts"], n)):
        seen = observed.get(name, {})
        structures = []
        for (num, den, xnum, xden), tally in sorted(
                seen.items(), key=lambda kv: (-kv[1]["facts"], kv[0])):
            # CLASSIFIED FROM THE FILING'S OWN EXPANDED NUMERATOR. An earlier
            # revision of mine wrote `not_derivable_from_graph` here, borrowing
            # the graph-only census's honest limit — but this receipt reads the
            # DOCUMENT, so that claim was simply false. The identity it needs
            # was already in hand.
            admits = sorted(candidate_units_for((), xnum))
            structures.append({
                "numerator": list(num), "denominator": list(den),
                "expanded_numerator": [list(m) for m in xnum],
                "expanded_denominator": [list(m) for m in xden],
                "declarations": tally["declarations"], "facts": tally["facts"],
                "verdict": "admits:" + ",".join(admits) if admits else "refused"})
        row = {"name": name[0], "is_divide": name[1],
               "facts": per_name[name]["facts"],
               "declarations": per_name[name]["declarations"],
               "declarations_read": per_name[name]["declarations_read"],
               "structures": structures}
        if len(structures) > 1:
            conflicts.append(row)
        shapes.append(row)

    # ONE DERIVED READ TOTAL, from the two read routes. The separate
    # `totals` read counters
    # are deleted, and every place below that used to read them reads this.
    read_decl = routes["read_simple"]["declarations"] + routes["read_divide"]["declarations"]
    read_facts = routes["read_simple"]["facts"] + routes["read_divide"]["facts"]
    # GLOBAL unread is still total minus read — that is a true statement about
    # coverage. What it must NOT do is masquerade as the CACHE scope, which
    # comes from the uncached route alone.
    unread = totals["declarations"] - read_decl
    facts_unread = totals["facts"] - read_facts
    doc = {
        "receipt": "#827 divided units — per (shape, accession, unit_ref)",
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "script_sha256": hashlib.sha256(
            open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "method": "each DECLARATION is read from its own filing's "
                  "<xbrli:unitNumerator>/<xbrli:unitDenominator> via "
                  "inline_html.prepare; the concatenated graph name is NEVER "
                  "split; classification is driver.core.xbrl_attach."
                  "candidate_units_for",
        "graph_read": {"lastCommittedTxn_before": tx_before["lastCommittedTxn"],
                       "lastCommittedTxn_after": tx_after["lastCommittedTxn"],
                       "unchanged": tx_before == tx_after,
                       "databaseID": tx_before["databaseID"]},
        "source": {"filings_available": len(cached),
                   "manifest": os.path.basename(MANIFEST),
                   "every_name_and_sha256_verified": verified_filings,
                   "note": "the frozen cache ONLY, and PROVEN frozen against "
                           "the pinned manifest before the graph was read — "
                           "this receipt used to call the cache frozen without "
                           "checking a single hash"},
        "declarations": {"total": totals["declarations"],
                         "read": read_decl, "unread": unread},
        "facts": {"total": totals["facts"],
                  "numeric_nonnil": totals["facts_numeric_nonnil"],
                  "on_read_declarations": read_facts,
                  "on_unread_declarations": facts_unread},
        "coverage_pct": {
            "declarations": round(100.0 * read_decl
                                  / totals["declarations"], 2),
            "facts": round(100.0 * read_facts
                           / totals["facts"], 2)},
        "shapes_total": len(per_name),
        "shapes_with_at_least_one_declaration_read":
            sum(1 for s in shapes if s["declarations_read"]),
        # SIMPLE DECLARATIONS, classified from the filing's expanded measures.
        # The graph-only census deliberately no longer gives these a verdict,
        # so this is where their semantics are recorded.
        "simple_declaration_shapes": [
            {"name": nm[0], "is_divide": nm[1], "measures": list(meas),
             "expanded_measures": [list(m) for m in xmeas],
             "declarations": t["declarations"], "facts": t["facts"],
             "verdict": ("admits:" + ",".join(sorted(a)) if (
                 a := candidate_units_for(xmeas, ())) else "refused")}
            for nm, seen in sorted(observed_simple.items())
            for (meas, xmeas), t in sorted(
                seen.items(), key=lambda kv: (-kv[1]["facts"], kv[0]))],
        # BOTH BRANCHES MUST BITE. The simple branch was once unreachable
        # because the query filtered `u.is_divide = '1'`, so an empty simple
        # list read as "nothing to report" instead of "never ran". These two
        # counts make that failure loud.
        "branch_reachability": {
            "divide_shapes_observed": len(observed),
            "simple_shapes_observed": len(observed_simple),
            "BOTH_BRANCHES_REACHED": bool(observed) and bool(observed_simple),
        },
        "routes": routes,
        "read_subtotals": {"simple": read_simple, "divide": read_divide,
                           "general_declarations_read":
                               read_decl,
                           "general_facts_on_read_declarations":
                               read_facts},
        "graph_is_divide_vocabulary_required": ["0", "1"],
        "graph_is_divide_counts_over_ALL_rows":
            dict(sorted(is_divide_counts.items(),
                        key=lambda kv: (kv[0] is None, kv[0]))),
        "graph_vs_filing_is_divide_disagreements": flag_disagreements,
        "structure_conflicts": conflicts,
        "declarations_present_but_unusable": dict(sorted(unreadable.items())),
        # NEUTRAL LABEL, EXACT REASON. Calling every one of these an "expected
        # source defect" over-claims: `prepare()` also reports view
        # disagreement, whose cause is not proven to be the filing's fault.
        # The reason is recorded verbatim and adjudicated after the run, not
        # named by a category chosen in advance.
        "document_refusals": dict(sorted(document_refusals.items())),
        "shapes": shapes,
        "SCOPE_LIMIT": {
            "this_census_is_BOUNDED_to_the_frozen_cache": True,
            # ONLY the uncached route. This published `total - read`,
            # which swept the cached document refusal, unusable
            # declarations and flag conflicts into a number labelled
            # "not in our cache" — a limitation that was partly not
            # about the cache at all.
            "declarations_never_read": routes["uncached"]["declarations"],
            "facts_on_them": routes["uncached"]["facts"],
            # MEASURED, not copied from an old run. The previous literal
            # "8,569 uncached filings" was a corpus number frozen into
            # prose; observed counts belong in receipts, never as fixed
            # values in the tool that produces them.
            "uncached_accessions_seen": len(uncached_accessions),
            "ruling_2026-07-31": "reviewer-accepted: do NOT fetch them merely "
                                 "to claim historical completeness. The runtime "
                                 "validates every filing it binds, per fact, at "
                                 "bind time — that is where correctness is "
                                 "enforced. This census measures WHAT EXISTS in "
                                 "the cache; it is not, and must never be "
                                 "described as, a proof about ALL graph facts.",
            "no_completeness_claim_is_made_here": True,
        },
    }
    # THE RECEIPT IS WRITTEN FIRST, then the run is judged. A failure that
    # deletes its own diagnostics tells you only that something broke.
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    # ---- EVERY ROW IN EXACTLY ONE ROUTE -----------------------------------
    # Both numbers, both directions. A row landing in two routes or in none
    # breaks these; subtraction could never notice either.
    if (sum(r["declarations"] for r in routes.values())
            != totals["declarations"]
            or sum(r["facts"] for r in routes.values()) != totals["facts"]):
        raise SystemExit(
            "ROUTING MISMATCH: routes hold %d declarations / %d facts but the "
            "query returned %d / %d — a row is in two routes or in none: %s"
            % (sum(r["declarations"] for r in routes.values()),
               sum(r["facts"] for r in routes.values()),
               totals["declarations"], totals["facts"], routes))

    # ---- INDEPENDENT ACCOUNTING PROOFS ------------------------------------
    # Summed FROM THE TABLES, not from the counters that filled them. The old
    # `read + derived_unread == total` check could never fail — it derived one
    # side from the other — and so said nothing when simple declarations were
    # classified and counted unread at the same time.
    held_simple = {"declarations": sum(t["declarations"] for seen in
                                       observed_simple.values()
                                       for t in seen.values()),
                   "facts": sum(t["facts"] for seen in observed_simple.values()
                                for t in seen.values())}
    held_divide = {"declarations": sum(t["declarations"] for seen in
                                       observed.values()
                                       for t in seen.values()),
                   "facts": sum(t["facts"] for seen in observed.values()
                                for t in seen.values())}
    if held_simple != read_simple or held_divide != read_divide:
        raise SystemExit(
            "ACCOUNTING MISMATCH: the observed tables hold simple=%s divide=%s "
            "but the read subtotals say simple=%s divide=%s — a declaration was "
            "counted in one place and not the other"
            % (held_simple, held_divide, read_simple, read_divide))
    if (read_simple["declarations"] + read_divide["declarations"]
            != read_decl
            or read_simple["facts"] + read_divide["facts"]
            != read_facts):
        raise SystemExit(
            "ACCOUNTING MISMATCH: simple+divide read subtotals do not equal the "
            "general read totals (%d+%d vs %d declarations)"
            % (read_simple["declarations"], read_divide["declarations"],
               read_decl))
    if not (observed and observed_simple):
        raise SystemExit(
            "BRANCH UNREACHABLE: divide shapes=%d simple shapes=%d — one kind "
            "of declaration never reached its classifier, so this receipt "
            "would be green about a census that did not run"
            % (len(observed), len(observed_simple)))
    if flag_disagreements:
        raise SystemExit(
            "%d declaration(s) where the graph `is_divide` and the filing's own "
            "structure disagree — see graph_vs_filing_is_divide_disagreements"
            % len(flag_disagreements))

    # EXPLICIT FAILURES, NOT ASSERTS. `assert` disappears under `python -O`, so
    # the accounting guarantee would silently stop existing in exactly the run
    # someone optimises. Each of these is a receipt-invalidating condition.
    if tx_before != tx_after:
        raise SystemExit(
            f"THE GRAPH MOVED DURING THE READ: lastCommittedTxn "
            f"{tx_before['lastCommittedTxn']} -> {tx_after['lastCommittedTxn']}."
            f" Every count here spans two different graphs; the receipt is void.")
    if (doc["declarations"]["read"] + doc["declarations"]["unread"]
            != doc["declarations"]["total"]):
        raise SystemExit("declaration accounting does not balance")
    if (doc["facts"]["on_read_declarations"]
            + doc["facts"]["on_unread_declarations"] != doc["facts"]["total"]):
        raise SystemExit("fact accounting does not balance")
    # A DECLARATION INSIDE A READABLE FILING MUST HAVE BEEN READ. Anything else
    # is a silent hole: the document parsed and the census still skipped it.
    #
    # DOCUMENT REFUSALS ARE NOT IN THIS BUCKET, and they are NOT pre-labelled
    # a source defect either: `prepare()` also refuses on view disagreement,
    # whose cause is not proven to be the filing's fault. Each reason is
    # recorded verbatim under `document_refusals` and adjudicated after the
    # run. They are kept out of THIS bucket only so that one strict refusal —
    # which this population provably contains — cannot make a successful
    # census impossible. No completeness credit is given either way.
    if unreadable:
        raise SystemExit(
            f"{sum(v['declarations'] for v in unreadable.values())} "
            f"declaration(s) whose filing IS present could not be read: "
            f"{dict(unreadable)}. A present-but-unread declaration is a "
            f"defect, not a coverage limit.")

    print(f"\ntx {tx_before['lastCommittedTxn']} -> "
          f"{tx_after['lastCommittedTxn']}  "
          f"({'unchanged' if tx_before == tx_after else 'MOVED'})")
    print(f"declarations : {totals['declarations']:,} total, "
          f"{read_decl:,} read "
          f"({doc['coverage_pct']['declarations']}%), {unread:,} UNREAD")
    print(f"facts        : {totals['facts']:,} total, "
          f"{read_facts:,} on read declarations "
          f"({doc['coverage_pct']['facts']}%)")
    print(f"shapes       : {len(per_name)} total, "
          f"{doc['shapes_with_at_least_one_declaration_read']} with a "
          f"declaration read")
    print(f"CONFLICTS (one name, two structures): {len(conflicts)}")
    for row in conflicts:
        print(f"   {row['name']}")
        for s in row["structures"]:
            print(f"      {s['facts']:>8,} facts  num={s['numerator']} "
                  f"den={s['denominator']}")
    print(f"wrote {os.path.basename(OUT)}")
    # A conflict makes shape-level classification unsound: that is a blocker.
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
