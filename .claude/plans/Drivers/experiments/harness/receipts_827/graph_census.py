"""#827 finite census — graph XBRL units, periods, identities (READ-ONLY).

Every query text is IN this file and echoed into the receipt, so the census is
reproducible verbatim. No write of any kind is issued; the session runs plain
MATCH/RETURN aggregations and SHOW DATABASE only.

SNAPSHOT PINNING — CORRECTED (round 7). The first receipt claimed the last
committed transaction id was UNAVAILABLE; that claim was WRONG — it was made
after trying only `dbms.queryJmx` and `db.info`. The reviewer pointed at
`SHOW DATABASE neo4j YIELD lastCommittedTxn, databaseID`, which serves it
directly. The id is now captured BEFORE and AFTER the census and the two must
be EQUAL, so every count in the receipt provably describes one unmoving
snapshot. Nothing is hardcoded: whatever the server reports is recorded.

Run:  venv/bin/python receipts_827/graph_census.py
Out:  receipts_827/02_graph_census.json
"""
import datetime
import hashlib
import json
import os
import sys

from neo4j import GraphDatabase

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
OUT = os.path.join(_HERE, "02_graph_census.json")

def run_read_only(session, text, **params):
    """The GENERAL gate: EXPLAIN-plan the statement and execute it ONLY if
    the server classifies it 'r' (read-only). Nothing else passes — no
    exemption, no allowance, no pin. 'EXPLAIN safely plans without
    executing' (Cypher manual), so a refused statement never runs.

    WHY THERE IS NO LONGER AN 's' BRANCH (round-13, reviewer-proven): 's'
    covers administration commands that are NOT harmless — Neo4j allows
    `SHOW TRANSACTIONS … TERMINATE TRANSACTIONS`, so neither the plan class
    nor a "starts with SHOW" test guarantees safety, and every attempt to
    carve an exemption for the snapshot statement re-opened a hole (round 11:
    the exemption trusted a variable; round 12: the pin was its own rule;
    round 13: SHOW-prefix admits TERMINATE). The snapshot statement now has
    its own dedicated no-argument path, `snapshot_tx()`, which takes NO input
    at all — there is nothing for a caller or a future edit to widen.

    Session READ_ACCESS remains DEFENSE-IN-DEPTH ONLY: a routing hint, not
    access control (Neo4j python-manual), moot over direct bolt://. A truly
    server-enforced barrier would need separate read-only credentials —
    owner approval required, deliberately not created.

    PARAMETERS CANNOT WIDEN THIS GATE, which is why they are allowed: the plan
    class is computed from the query TEXT, and no value bound to a parameter can
    turn a MATCH into a write. They are passed to EXPLAIN and to the execution
    IDENTICALLY, so the statement that was planned is the statement that runs —
    the alternative, string-building a query out of values, is the thing this
    gate exists to make unnecessary."""
    planned = session.run("EXPLAIN " + text, **params).consume().query_type
    if planned != "r":
        raise RuntimeError(
            f"query planned as {planned!r}, not read-only — REFUSED before "
            f"execution: {text[:100]}")
    return session.run(text, **params), planned


def snapshot_tx(session):
    """The ONE administration read this census performs, as a dedicated
    NO-ARGUMENT path: the statement is a literal inside this function, so no
    caller supplies text and no variable can be rebound to widen it. Returns
    the single row {lastCommittedTxn, databaseID}.

    Its exact text is pinned INDEPENDENTLY, in the harness suite's
    `test_827_census_snapshot_statement_is_pinned_AT_RUNTIME` — a separate
    file, so the pin and the code cannot drift into being the same statement
    about themselves, and the pin RUNS this function against a mock (an
    earlier source-text version passed a mutant that kept the approved
    literal as dead text while executing another query)."""
    return [r.data() for r in session.run(
        "SHOW DATABASE neo4j YIELD lastCommittedTxn, databaseID")][0]


def _refusal_control():
    """Mocked mutation control, run BEFORE any real query. Pure mock — the
    graph is never touched, no write text is ever sent to the server.

    Round-13 shape: the general gate accepts ONLY 'r', so every hostile text
    is refused by the same one rule — CREATE ('w'), DELETE ('rw'), a schema
    write ('s'), and the attack that broke round 12's SHOW-prefix allowance,
    `SHOW TRANSACTIONS … TERMINATE TRANSACTIONS` ('s'). Each must show
    exactly ONE recorded call, the EXPLAIN. Positive control: an ordinary
    read ('r') passes through. The snapshot statement is NOT tested here —
    it has no text input to attack; its literal is pinned independently in
    the harness test suite."""
    class _Summary:
        def __init__(self, qt):
            self.query_type = qt

    class _Result:
        def __init__(self, qt):
            self._qt = qt

        def consume(self):
            return _Summary(self._qt)

    class _MockSession:
        def __init__(self, planned_qt):
            self.planned_qt, self.calls = planned_qt, []

        def run(self, text):
            self.calls.append(text)
            if text.startswith("EXPLAIN "):
                return _Result(self.planned_qt)
            return _Result(self.planned_qt)

    for planned, hostile in (
            ("w", "CREATE (n:_NeverRuns) RETURN n"),
            ("rw", "MATCH (n:_NeverRuns) DELETE n RETURN 1"),
            ("s", "CREATE INDEX _never_runs IF NOT EXISTS "
                  "FOR (n:_X) ON (n.y)"),
            # THE ROUND-13 ATTACK: administration, plans 's', begins with
            # SHOW, and TERMINATES transactions. It broke the SHOW-prefix
            # allowance; under "only 'r' passes" it is refused like any other.
            ("s", "SHOW TRANSACTIONS YIELD transactionId AS txId "
                  "TERMINATE TRANSACTIONS txId")):
        m = _MockSession(planned)
        refused = False
        try:
            run_read_only(m, hostile)
        except RuntimeError:
            refused = True
        if not refused:
            raise RuntimeError(
                f"refusal control FAILED: a {planned!r}-planned statement "
                f"passed the gate: {hostile[:60]}")
        if m.calls != ["EXPLAIN " + hostile]:
            raise RuntimeError(
                f"refusal control FAILED: expected ONLY the EXPLAIN call, "
                f"saw {m.calls}")
    ok = _MockSession("r")
    run_read_only(ok, "MATCH (n) RETURN count(n)")
    if ok.calls != ["EXPLAIN MATCH (n) RETURN count(n)",
                    "MATCH (n) RETURN count(n)"]:
        raise RuntimeError(
            f"refusal control FAILED: a read did not pass through: {ok.calls}")
    return ("PASSED: w / rw / schema-write / SHOW…TERMINATE all refused with "
            "only EXPLAIN run; reads ('r') pass; the snapshot statement has "
            "no text input to widen (dedicated no-argument path)")

QUERIES = {
    "unit_total": "MATCH (u:Unit) RETURN count(u) AS n",
    # THE SHAPES THEMSELVES, not a count of them. This returned
    # `count(DISTINCT [...]) AS n` = 6,924 and stopped, so the census proved
    # how many exist and nothing about whether any is handled. That is the
    # precise failure this programme keeps finding: a total reads like coverage.
    # Every distinct shape is ENUMERATED below. It is deliberately NOT given a
    # semantic verdict: `Unit.name` is the filing's own prefixed spelling, so
    # the currency behind it cannot be known from the graph alone.
    "unit_distinct_name_is_divide":
        "MATCH (u:Unit) RETURN DISTINCT u.name AS name, u.is_divide AS is_divide "
        "ORDER BY name, is_divide",
    "unit_is_divide_values":
        "MATCH (u:Unit) RETURN u.is_divide AS v, count(*) AS n ORDER BY n DESC",
    "unit_duplicate_u_id":
        "MATCH (u:Unit) WITH u.u_id AS k, count(*) AS n WHERE n > 1 "
        "RETURN count(*) AS groups, sum(n) AS nodes",
    "divided_unit_shapes_used_by_numeric_nonnil":
        "MATCH (f:Fact)-[:HAS_UNIT]->(u:Unit) "
        "WHERE u.is_divide = '1' AND f.is_numeric = '1' AND f.is_nil = '0' "
        "RETURN count(DISTINCT [u.name, u.is_divide]) AS shapes, "
        "count(f) AS facts",
    "period_total": "MATCH (p:Period) RETURN count(p) AS n",
    # "non-empty" excludes the literal STRING 'null' — instants store their
    # absent boundary as 'null', and a first draft of this census counted it
    # as a date. The planning number (19,774) was right; the filter was not.
    "period_nonempty_dates":
        "MATCH (p:Period) UNWIND [p.start_date, p.end_date] AS d "
        "WITH d WHERE d IS NOT NULL AND d <> '' AND d <> 'null' "
        "RETURN count(d) AS occurrences, count(DISTINCT d) AS distinct_dates",
    "period_compact_dates":
        "MATCH (p:Period) UNWIND [p.start_date, p.end_date] AS d "
        "WITH d WHERE d IS NOT NULL AND d =~ '\\\\d{8}' "
        "RETURN count(DISTINCT d) AS n",
    # DRIFT vs the planning census, recorded not normalized: planning saw this
    # orphan with ZERO facts; the live graph now attaches numeric non-nil
    # facts to it. THE DATE LAW, corrected round 8: the filing's instant
    # 0224-03-31 is a LAWFUL four-digit XML Schema date meaning year 224
    # (leading zeros required below 1000), and XBRL's date-only instant rule
    # converts it to the following midnight, 0224-04-01. The INVALID form is
    # the GRAPH's stored '224-04-01', which lost its leading zero and is not
    # a legal lexical date. Core parks the source/graph mismatch without
    # "correcting" anything — 2024 is never inferred.
    "malformed_orphan_224_04_01":
        "MATCH (p:Period) WHERE p.start_date = '224-04-01' "
        "OR p.end_date = '224-04-01' "
        "OPTIONAL MATCH (f:Fact)-[:HAS_PERIOD]->(p) "
        "RETURN count(DISTINCT p) AS periods, count(f) AS facts, "
        "count(CASE WHEN f.is_numeric = '1' AND f.is_nil = '0' "
        "THEN 1 END) AS numeric_nonnil_facts",
    # THE IDENTITIES BEHIND THE DRIFT (round-7 repair 3; accession source
    # corrected round 8): the CANONICAL hyphenated accession comes from the
    # graph's own Fact-[:REPORTS]->XBRLNode<-[:HAS_XBRL]-Report relationship
    # and Report.accessionNo — never parsed out of a u_id string.
    "malformed_orphan_fact_identities":
        "MATCH (r:Report)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)"
        "-[:HAS_PERIOD]->(p:Period) "
        "WHERE p.start_date = '224-04-01' OR p.end_date = '224-04-01' "
        "RETURN f.fact_id AS fact_id, f.qname AS qname, f.value AS value, "
        "f.context_id AS context_id, r.accessionNo AS accession, "
        "f.u_id AS u_id "
        "ORDER BY f.qname, f.fact_id",
    "malformed_orphan_fact_summary":
        "MATCH (r:Report)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)"
        "-[:HAS_PERIOD]->(p:Period) "
        "WHERE p.start_date = '224-04-01' OR p.end_date = '224-04-01' "
        "RETURN count(f) AS facts, "
        "count(DISTINCT r.accessionNo) AS distinct_accessions, "
        "count(DISTINCT f.qname) AS distinct_concepts",
    "dimension_total": "MATCH (d:Dimension) RETURN count(d) AS n",
    "dimension_typed_explicit":
        "MATCH (d:Dimension) RETURN d.is_typed AS is_typed, "
        "d.is_explicit AS is_explicit, count(*) AS n",
    "dimension_duplicate_u_id":
        "MATCH (d:Dimension) WITH d.u_id AS k, count(*) AS n WHERE n > 1 "
        "RETURN count(*) AS groups, sum(n) AS nodes",
    "member_total": "MATCH (m:Member) RETURN count(m) AS n",
    "member_duplicate_u_id":
        "MATCH (m:Member) WITH m.u_id AS k, count(*) AS n WHERE n > 1 "
        "RETURN count(*) AS groups, sum(n) AS nodes",
    "db_info": "CALL db.info() YIELD id, name, creationDate RETURN *",
}


def main():
    for line in open(os.path.join(_REPO, ".env")):
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))
    results = {}
    control = _refusal_control()          # mocked; runs before ANY real query
    print(f"refusal control: {control}", flush=True)
    # READ_ACCESS retained as DEFENSE-IN-DEPTH ONLY (round-10 correction: it
    # is a routing hint, not access control — see run_read_only's docstring).
    # The enforced barrier is the EXPLAIN gate in run_read_only.
    import neo4j as _neo4j
    with driver.session(default_access_mode=_neo4j.READ_ACCESS) as s:
        tx_before = snapshot_tx(s)          # dedicated path, no text input
        print(f"lastCommittedTxn BEFORE: {tx_before}", flush=True)
        for name, text in QUERIES.items():
            res, planned = run_read_only(s, text)
            results[name] = {"query": text, "planned_type": planned,
                             "rows": [r.data() for r in res]}
            if name != "malformed_orphan_fact_identities":
                print(f"{name} [{planned}]: {results[name]['rows']}",
                      flush=True)
        tx_after = snapshot_tx(s)
        print(f"lastCommittedTxn AFTER:  {tx_after}", flush=True)
    driver.close()
    # explicit raise, never `assert`: python -O strips asserts, and a control
    # that can be compiled away is not a control (round-8 repair 3)
    if tx_before != tx_after:
        raise RuntimeError(
            f"the graph MOVED during the census ({tx_before} -> {tx_after}); "
            f"these counts describe no single snapshot — rerun until stable")
    # ---- ENUMERATE EVERY OBSERVED UNIT SHAPE (no semantic verdict here) -----
    # This census once ran each (name, is_divide) through
    # `xbrl_attach.candidate_units_for` and bucketed the answer. That was only
    # ever meaningful while the policy read the stored spelling; it now decides
    # on (namespace URI, local name), which this side does not have. The shapes
    # are still surfaced in full — a storage-contract record — and the semantic
    # classification belongs to the filing-side declaration census.
    #
    # DIVIDED UNITS ARE NOT SPLIT FROM THE GRAPH NAME. `u.name` for a divide is
    # the measures CONCATENATED (`iso4217:USDshares`), which cannot be split
    # back reliably — `exact_numbers.graph_unit_spelling` says so and 140 live
    # `utr:galutr:M` facts prove it. The structured numerator can only come from
    # the filing's own <xbrli:unitNumerator>, which this read-only graph census
    # does not hold; so divide shapes are classified as
    # `numerator_not_derivable_from_graph` and named for the FILING-side census
    # to answer. Guessing a split here would fabricate the evidence.
    sys.path.insert(0, _REPO)
    sys.path.insert(0, os.path.join(_REPO, "driver", "relocation"))
    # The policy is no longer imported here: this census cannot supply its
    # input. It records the STORAGE SHAPES it can genuinely see and says so.
    shapes, buckets = [], {}
    for row in results["unit_distinct_name_is_divide"]["rows"]:
        name, is_div = row.get("name"), row.get("is_divide")
        # NO SEMANTIC VERDICT FROM GRAPH-ONLY DATA, for a simple unit either.
        # `Unit.name` is the filing's own prefixed spelling, so a lawful alias
        # or a rebound prefix makes the currency unknowable from this side —
        # the same reason the divide case was already marked not derivable.
        # Turning the text back into an expanded name here would re-invent the
        # prefix convention the product just stopped trusting; the filing-side
        # declaration census is where this can be classified, because only
        # there is each measure's in-scope namespace available.
        verdict, admits = "not_derivable_from_graph", None
        shapes.append({"name": name, "is_divide": is_div,
                       "verdict": verdict, "admits": admits})
        buckets[verdict] = buckets.get(verdict, 0) + 1
    if len(shapes) != len(results["unit_distinct_name_is_divide"]["rows"]):
        raise RuntimeError("a unit shape was returned but not classified")

    doc = {
        "receipt": "#827 graph census — units, periods, identities",
        "unit_shape_classification": {
            "shapes_classified": len(shapes),
            "buckets": dict(sorted(buckets.items(), key=lambda kv: -kv[1])),
            "classified_by": None,   # see the filing-side declaration census
            "why_unclassified": "Unit.name is the filing's own prefix; the currency namespace is not recoverable from graph-only data",
            "shapes": shapes,
        },
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "database": "neo4j",
        # THE SCHEME ONLY. The full `NEO4J_URI` was written verbatim, so this
        # receipt carried the machine's private host and port into a file meant
        # to be committed and shared. The scheme is the part that carries
        # meaning here — it is what makes the READ_ACCESS correction below true
        # (a direct bolt connection, not a routed one). The address itself
        # proves nothing and does not belong in a review artifact.
        "uri_scheme": os.environ["NEO4J_URI"].split("://", 1)[0] + "://",
        "tx_statement": "SHOW DATABASE neo4j YIELD lastCommittedTxn, "
                        "databaseID (executed only by the dedicated "
                        "no-argument snapshot_tx path; its exact text is "
                        "pinned independently in the harness test suite)",
        "lastCommittedTxn_before": tx_before,
        "lastCommittedTxn_after": tx_after,
        "snapshot_stable": True,
        "corrections": [
            "round 7: an earlier receipt claimed the last committed "
            "transaction id was UNAVAILABLE; wrong — SHOW DATABASE serves it "
            "(only dbms.queryJmx and db.info had been tried).",
            "round 10: an earlier comment claimed session READ_ACCESS makes "
            "the server refuse writes; wrong — it is a routing hint, not "
            "access control (Neo4j docs), and this census uses direct "
            "bolt://. READ_ACCESS is now defense-in-depth only.",
            "round 11: the round-10 gate exempted `text == TX_QUERY` from "
            "EXPLAIN entirely — self-referential: a future write placed in "
            "TX_QUERY would have bypassed planning. Now EVERY statement is "
            "planned; 's' is accepted only for the exact reviewed pin.",
            "round 12: the pin was still both the rule AND the expected "
            "value — editing PINNED_SHOW itself to a schema command widened "
            "the gate (reviewer's mock proved it).",
            "round 13: the SHOW-prefix allowance added in round 12 was ALSO "
            "unsafe — Neo4j allows SHOW TRANSACTIONS … TERMINATE "
            "TRANSACTIONS, reproduced executing through the gate in a mock. "
            "ALL exemptions removed: the general gate accepts only 'r', and "
            "the snapshot statement moved to a dedicated no-argument path "
            "with no text input to widen.",
        ],
        "read_only_enforcement": "EVERY caller-supplied statement is "
                                 "EXPLAIN-planned and executes only if "
                                 "planned 'r' — no exemption of any kind. "
                                 "The single administration read runs "
                                 "through the no-argument snapshot_tx path "
                                 "whose literal is pinned independently in "
                                 "the harness test suite. Session "
                                 "READ_ACCESS is defense-in-depth only; "
                                 "separate read-only credentials would need "
                                 "owner approval and were NOT created",
        "refusal_control": _refusal_control(),
        "script_sha256": hashlib.sha256(
            open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "results": results,
    }
    body = json.dumps(doc, indent=1, sort_keys=True)
    open(OUT, "w").write(body + "\n")
    print(f"wrote {os.path.relpath(OUT, _REPO)} "
          f"(sha256 {hashlib.sha256(body.encode()).hexdigest()[:16]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
