"""S3.5 item-9 MINIMUM: one thin READ-ONLY Neo4j adapter + preflight + CLI entry.

REPORT-ONLY BY DESIGN (the fiscal.ai pilot lane): sources resolve via
(Report {accessionNo})-[:PRIMARY_FILER]->(Company). Transcript/News wiring belongs
to S4 public-channel integration (News currently has no proper ownership edge).
Run it as:  python -m driver.core.driver_neo4j_adapter <input.json> --audit-dir D
            python -m driver.core.driver_neo4j_adapter --preflight

WRITES ARE DISABLED OUTRIGHT: transaction() raises — this adapter serves the dry-run
lane only until the owner's fitness gate opens production. No channel machinery, no
retries, no scheduler, no ORM, no migrations (out of scope by owner instruction).

Verified against the LIVE graph 2026-07-17 (read-only):
  ownership = (Report)-[:PRIMARY_FILER]->(Company)  ·  source time = Report.created
  fye = Company.fiscal_year_end_month (STORED AS A STRING — cast here, once).
Graph numeric read-back follows the owner exactness law: int stays int; float ->
Decimal(repr(f)) — sound because only proven-round-trip floats are ever stored.
"""
import json
import os
from types import MappingProxyType
from collections import namedtuple as _namedtuple

from driver.core.driver_ids import (PERIOD_SENTINEL_SCOPE, SEC_CIK_10_PATTERN,
                                    NON_REGISTRANT_CIK, graph_cik)
from driver.xml_names import graph_qname_parts
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

__all__ = ["Neo4jStore", "preflight", "main"]

_MISSING = object()


def _resolve_id_records(records):
    """Group Dimension/Member records by id, FAIL-CLOSED on disagreement.

    #822: this was `found[rec["id"]] = rec` — last write wins. Two records
    sharing an id but disagreeing on qname or label meant the axis or member a
    fact bound against depended on the order the driver returned rows in.
    Identical duplicates COLLAPSE (a repeated row is not a conflict); a
    disagreement POISONS the id to None, and the caller already treats an
    unresolvable pair as a fact it cannot verify. Exactly the poisoning the
    inline binder applies to duplicate context and unit ids.
    """
    out = {}
    for rec in records:
        # A record we cannot read leaves its id UNRESOLVED, which the caller
        # already treats as a fact it cannot verify. Raising here would be a
        # programming-error signal for what is only a bad row — the very class
        # this module was fixing when this helper was written.
        if not isinstance(rec, dict):
            continue
        # THE COMPLETE SHAPE, not just an id: the kind decides which slot the
        # record may fill, the qname becomes an axis or member name, and the
        # label is recomputed into a slice token. A record we cannot fully read
        # is left UNRESOLVED, and the caller drops such a fact fail-closed.
        if not isinstance(rec.get("id"), str) or not rec["id"].strip():
            continue
        if rec.get("kind") not in ("Dimension", "Member"):
            continue
        if not isinstance(rec.get("qname"), str) or not rec["qname"].strip():
            continue
        # THE LABEL IS NOT DECORATION on a Member: `check_member_refs`
        # RECOMPUTES the slice token from it, so a Member without a usable one
        # verifies nothing and is dropped at the source. A DIMENSION record
        # legitimately has none (the query returns `null AS label`), so this is
        # kind-specific rather than blanket. Census 2026-07-28: 0 of 1,499,049
        # Members carry a null label, so this costs no recall.
        label = rec.get("label")
        if rec["kind"] == "Member":
            if not isinstance(label, str) or not label.strip():
                continue
        elif label is not None:
            # The definition query returns `null AS label` for a Dimension, so
            # ANY other value is a shape our own query cannot produce.
            continue
        rec = dict(rec)
        prior = out.get(rec["id"], _MISSING)
        if prior is _MISSING:
            out[rec["id"]] = rec
        elif prior is None or prior != rec:
            out[rec["id"]] = None                 # ambiguous -> consumers park
    return out

_NUMERIC_FACT_FIELDS = ("level_low", "level_high", "change_value",
                        "comparison_low", "comparison_high")


def _exact(value):
    if isinstance(value, bool) or not isinstance(value, float):
        return value
    return Decimal(repr(value))            # the ONE sanctioned float bridge


# THE ONE read result: verified rows AND the evidence for what was dropped.
# The drop itself is unchanged and still fail-closed; what changes is that it
# stops being invisible. A named two-field value (not a bare list) so a caller
# cannot keep treating the result as rows and silently lose the evidence.
GraphFactRows = _namedtuple("GraphFactRows", ("rows", "exclusions"))

# The reasons a row is dropped, each an HONEST label for the SYMPTOM observed.
# A misaligned array is not proof of a typed dimension: same symptom, unproved
# cause, and naming the cause would put a guess into the audit record.
_EXCLUDED_UNREADABLE = "graph_row_unreadable"
_EXCLUDED_MISALIGNED = "dimension_member_array_misaligned"
_EXCLUDED_UNRESOLVED = "dimension_definition_unresolved"


def _norm_uid(u_id, expected_company_cik):
    """The node-id spelling of a Context reference, or None.

    THE MATCHED COMPANY IS THE AUTHORITY, not the reference: this used to
    `partition(':')` the reference and trust whatever came out. The two stored
    spellings differ by design — `Company.cik` is ten padded digits, a node id
    drops the leading zeros — so the conversion needs a company, and the caller
    has already matched one. `graph_cik` owns what a lawful cik is.
    """
    cik = graph_cik(expected_company_cik)
    if cik is None or not isinstance(u_id, str):
        return None
    prefix = cik + ":"
    if not u_id.startswith(prefix):
        return None
    # DERIVED FROM THE VALIDATED VALUE, and the suffix is never touched: the
    # colons inside a namespace URI are not delimiters anyone has to interpret.
    # `or '0'` is gone with the fallback it served — once the all-zero marker
    # refuses in `graph_cik`, no lawful cik can strip to the empty string.
    return f"{cik.lstrip('0')}:{u_id[len(prefix):]}"


def _namespace_from_uid(u_id, qname):
    """The namespace a Dimension/Member composite id carries, or None.

    PRIVATE. Decoding the stored composite is this boundary's own business, not
    a new public API — what leaves here is the decoded `axis_namespace` /
    `member_namespace`, never the composite or the means of reading it.

    NEITHER BOUNDARY IS GUESSED, which is the whole reason this is lawful to do:

      * the FIRST colon is the company-id boundary — a contract this module
        already owns and relies on in `_norm_uid`;
      * the SUFFIX is the record's own exact `qname`, supplied by the caller
        rather than inferred;
      * so every character between them is the namespace URI, and the colons
        INSIDE that URI are never a delimiter anyone has to interpret.

    The graph writer composes `company_id + ':' + namespaceURI + ':' + qname`
    and — unlike Concept — persists no separate namespace, so this is the only
    place the value exists. Decoding it is reading the frozen storage contract,
    not parsing a string of unknown shape.

    FAIL-CLOSED: every component is checked, and anything unexpected returns
    None so the caller leaves that record unresolved under its existing truthful
    exclusion path. A namespace is never invented.
    """
    if not isinstance(u_id, str) or not isinstance(qname, str) or not qname:
        return None
    company, sep, rest = u_id.partition(":")     # the boundary `_norm_uid` owns
    if not sep or not company.strip():
        return None
    suffix = ":" + qname
    if not rest.endswith(suffix):
        return None
    namespace = rest[:-len(suffix)]
    if not namespace.strip():
        return None
    # THE QNAME IS ASKED OF THE STANDARDS OWNER, not checked here. This decoder
    # used to accept `a:b:c`, `a: b`, ` a:b` and a tab-separated name, because
    # "has a non-blank local part" is not the XML grammar — it only looks like
    # it. `graph_qname_parts` is the one place that grammar lives, and it asks
    # the XML library rather than restating the rule as a pattern.
    if graph_qname_parts(qname) is None:
        return None
    return namespace


class Neo4jStore:
    """The same read surface FakeStore mirrors. Dry-run lane only."""

    def __init__(self, uri=None, user=None, password=None, database="neo4j"):
        from neo4j import GraphDatabase
        self._driver = GraphDatabase.driver(
            uri or os.environ["NEO4J_URI"],
            auth=(user or os.environ["NEO4J_USERNAME"],
                  password or os.environ["NEO4J_PASSWORD"]))
        self._db = database

    def close(self):
        self._driver.close()

    # Neo4j's outage classes derive from its own DriverError/Neo4jError, NOT
    # from OSError, so nothing downstream recognised them and a real outage
    # failed loudly as if it were a programming bug. THE STORE maps its own
    # transient failures, because the store is what knows the driver: the
    # contract module cannot import neo4j to catch them (it is staged, and the
    # G18 gate fires on exactly that). ConnectionError is used deliberately —
    # it IS an OSError, which is the retryable set every consumer already
    # honours, so no shared symbol has to cross the staged/production line.
    @staticmethod
    def _transient():
        from neo4j.exceptions import (ServiceUnavailable, SessionExpired,
                                      TransientError)
        return (ServiceUnavailable, SessionExpired, TransientError)

    def _read(self, query, **params):
        try:
            with self._driver.session(database=self._db,
                                      default_access_mode="READ") as s:
                return [dict(rec) for rec in s.run(query, **params)]
        except self._transient() as e:
            raise ConnectionError(
                f"Neo4j is temporarily unavailable ({type(e).__name__}: {e}) — "
                f"park and retry") from e

    def get_source(self, source_id):
        rows = self._read(
            "MATCH (r:Report {accessionNo: $id}) "
            "OPTIONAL MATCH (r)-[:PRIMARY_FILER]->(c:Company) "
            "RETURN r.created AS date, r.formType AS form, c.ticker AS ticker, "
            "c.fiscal_year_end_month AS fye LIMIT 1", id=source_id)
        if not rows:
            return None
        r = rows[0]
        form = (r["form"] or "").upper().replace("/A", "")   # amendments -> base type
        return {"date": r["date"],
                "source_type": form.lower().replace("-", ""),
                "ticker": r["ticker"],
                "fye_month": int(r["fye"]) if r["fye"] is not None else None}

    def get_source_companies(self, source_id):
        return [r["t"] for r in self._read(
            "MATCH (r:Report {accessionNo: $id})-[:PRIMARY_FILER]->(c:Company) "
            "RETURN c.ticker AS t", id=source_id)]

    def get_xbrl_representation_count(self, source_id):
        """How many XBRL representations CORE'S GRAPH says this source has.

        The one-representation guard must ask here, not count the channel's
        repeated hashes — items agreeing with each other is the channel
        agreeing with itself. Census 2026-07-27: 10,468 XBRL-bearing reports,
        every one with exactly one XBRLNode, zero facts spanning two; 0 for an
        8-K, which carries no XBRL at all.
        """
        rows = self._read(
            "MATCH (r:Report {accessionNo: $id})-[:HAS_XBRL]->(x:XBRLNode) "
            "RETURN count(DISTINCT x) AS n", id=source_id)
        return rows[0]["n"] if rows else 0

    def get_source_company_cik(self, source_id):
        """THE filing entity's CIK, from CORE's OWN graph — never from a
        document provider.

        Under the injected-provider design the provider is channel-supplied, so
        letting it also name the company would let one side furnish both the
        claim and its proof. `Company.id` IS the zero-padded CIK (verified live
        2026-07-27: id == cik == '0001306830' for CE).

        Exactly one PRIMARY_FILER, or None — a multi-registrant or unknown
        source parks (the existing SOURCE_COMPANY_AMBIGUOUS class), never
        guesses by position.
        """
        rows = self._read(
            "MATCH (r:Report {accessionNo: $id})-[:PRIMARY_FILER]->(c:Company) "
            "RETURN DISTINCT c.id AS cik", id=source_id)
        # RAW, EXACTLY AS STORED (#827 frozen contract): Company.id is a
        # ten-character ASCII digit string, returned unchanged and compared
        # exactly downstream. The old `str(...).strip()` did three unlawful
        # things at once — repaired padded data before `graph_cik` could
        # refuse it, minted a spelling for non-string data that no node
        # states, and let the repair COLLAPSE two distinct stored values into
        # one, masking a real ambiguity. Only absence (None) is dropped.
        ciks = {r["cik"] for r in rows if r["cik"] is not None}
        return ciks.pop() if len(ciks) == 1 else None

    def get_driver(self, name):
        rows = self._read("MATCH (d:Driver {name: $name}) "
                          "RETURN d.name AS name, d.fact_type AS fact_type LIMIT 1",
                          name=name)
        return rows[0] if rows else None

    def get_sibling_facts(self, bare_id):
        rows = self._read(
            "MATCH (f:DriverUpdate) WHERE f.id = $bare "
            "OR f.id STARTS WITH $prefix RETURN properties(f) AS p",
            bare=bare_id, prefix=bare_id + "|quote_hash=")
        out = []
        for row in rows:
            p = dict(row["p"])
            for k in _NUMERIC_FACT_FIELDS:
                if k in p:
                    p[k] = _exact(p[k])
            out.append(p)
        return out

    def get_period(self, period_id):
        rows = self._read("MATCH (p:DriverPeriod {id: $pid}) "
                          "RETURN properties(p) AS p LIMIT 1", pid=period_id)
        return rows[0]["p"] if rows else None

    def get_prior_guide_units(self, fact):
        """Prior guide units for the SAME company + SAME complete series, EARLIER
        sources only. Company rides the graph edges (FROM_SOURCE→PRIMARY_FILER —
        never id text); hashed collision members are included by splitting the
        stored fact_scope FIELD at its quote_hash slot; earlier-only uses a real
        datetime comparison. The series match includes period_scope (§9 full
        series key) — same exact dates with a different scope (Q1 vs YTD-Q1) is
        a DIFFERENT series; the null-safe form keeps the dormant-P14
        instant-scope=null flip from silently breaking this. §9 ranking then
        picks ONE winning source (see _rank_prior_units); zero candidates → []
        and the writer parks."""
        rows = self._read(
            "MATCH (:Report {accessionNo: $src})-[:PRIMARY_FILER]->(c:Company) "
            "MATCH (f:DriverUpdate)-[:OF_DRIVER]->(:Driver {name: $driver}) "
            "MATCH (f)-[:FROM_SOURCE]->(r:Report)-[:PRIMARY_FILER]->(c) "
            "WHERE r.accessionNo <> $src "
            "AND datetime(f.date) < datetime($date) "
            "AND f.time_type = $time_type "
            "AND (f.period_scope = $period_scope "
            "OR (f.period_scope IS NULL AND $period_scope IS NULL)) "
            "AND f.series_unit IS NOT NULL "
            "AND split(f.fact_scope, '|quote_hash=')[0] = $scope "
            "RETURN f.series_unit AS series_unit, f.date AS date, "
            "f.source_type AS source_type, r.accessionNo AS source_id",
            src=fact["id"].split(":", 2)[1], driver=fact["driver_name"],
            scope=fact["fact_scope"], date=fact["date"],
            time_type=fact["time_type"], period_scope=fact.get("period_scope"))
        return _rank_prior_units(rows)

    # THE MATCHED COMPANY CARRIES THE IDENTITY. This used to `split(du, ':')[0]`
    # and coerce the result, so every stored reference vouched for itself.
    # `$cik_pattern` / `$non_registrant` are the owner's values, passed as
    # parameters so the rule is not restated in Cypher.
    # AAPL regression: 1,886 dimensional contexts returned ZERO under a raw join.
    #: THE EXACT PREDICATE, named so a read-only test can execute THIS text
    #: rather than a retyped copy of it. A substring assertion alone would only
    #: prove the letters are present; the behaviour test binds `co` and runs it.
    _CIK_GUARD = "co.cik =~ $cik_pattern AND co.cik <> $non_registrant"

    _MEMBER_PAIRING = (
        "WITH DISTINCT co, c "
        "WHERE " + _CIK_GUARD + " "
        "UNWIND range(0, size(c.dimension_u_ids)-1) AS i "
        "WITH DISTINCT co.cik AS cik, c.dimension_u_ids[i] AS du, "
        "c.member_u_ids[i] AS mu "
        "WHERE du STARTS WITH cik + ':' AND mu STARTS WITH cik + ':' "
        # ONLY NOW, on a value already proven to be ten ASCII digits, so the
        # coercion has nothing left to misread and `size(cik)` is a checked
        # length. A misaligned array still yields null and still drops (#828).
        "WITH cik, du, mu, toString(toInteger(cik)) AS ncik "
        "MATCH (d:Dimension {id: ncik + substring(du, size(cik))}) "
        "MATCH (m:Member {id: ncik + substring(mu, size(cik))}) "
        "RETURN DISTINCT d.qname AS axis, m.qname AS member, m.label AS label")

    def get_company_slice_menu(self, source_id, date):
        """RAW fold-menu material (FINAL_DESIGN:172/:48 — cut at the event's
        public time, real datetime compare): (a) fold-menu arm = members from
        the company's PRIOR public 10-K/10-Q (incl. /A, strictly before the
        event — the current filing never feeds its own fold-menu), entity-scoped
        by the P4f FOR_COMPANY edge, numeric facts only; (b) fact_scopes already
        used on stored facts (≤ event time). Fact-level ref VERIFICATION is
        get_xbrl_fact_dimensions, not this. Context-first with an EXISTS
        short-circuit: a company's DIMENSIONAL contexts are few (AAPL: 1,886),
        its facts are hundreds of thousands. Retrieval ONLY — all law lives in
        slice_menu.py."""
        xbrl = self._read(
            "MATCH (:Report {accessionNo: $src})-[:PRIMARY_FILER]->(co:Company) "
            "OPTIONAL MATCH (co)<-[:PRIMARY_FILER]-(pr:Report)"
            "-[:HAS_XBRL]->(px:XBRLNode) "
            "WHERE pr.formType IN ['10-K','10-Q','10-K/A','10-Q/A'] "
            "AND datetime(pr.created) < datetime($date) "
            "WITH co, collect(DISTINCT px) AS xs "
            "MATCH (co)<-[:FOR_COMPANY]-(c:Context) "
            "WHERE size(c.dimension_u_ids) > 0 "
            "AND EXISTS { MATCH (f:Fact)-[:IN_CONTEXT]->(c), "
            "  (f)-[:REPORTS]->(x2:XBRLNode) "
            "  WHERE f.is_numeric = '1' AND x2 IN xs } "
            + self._MEMBER_PAIRING, src=source_id, date=date,
            cik_pattern=SEC_CIK_10_PATTERN, non_registrant=NON_REGISTRANT_CIK)
        used = self._read(
            "MATCH (:Report {accessionNo: $src})-[:PRIMARY_FILER]->(co:Company) "
            "MATCH (du:DriverUpdate)-[:FROM_SOURCE]->(:Report)"
            "-[:PRIMARY_FILER]->(co) "
            "WHERE datetime(du.date) <= datetime($date) "
            "RETURN DISTINCT du.fact_scope AS scope", src=source_id, date=date)
        return {"xbrl_members": xbrl,
                "used_scopes": [r["scope"] for r in used]}

    def get_xbrl_fact_dimensions(self, source_id, concept_qname):
        """Fact-level verification material: every numeric non-nil fact of THE
        current filing carrying this exact concept qname, entity-scoped to the
        source's PRIMARY company via the P4f FOR_COMPANY edge, with its stored
        period (raw — stored ends are EXCLUSIVE; slice_menu applies the
        verified decode) and its COMPLETE dimension set (axis/member qnames +
        labels via the CIK-normalized indexed-id pairing; [] = a genuinely
        dimensionless context). Fail-closed exclusions: facts without a
        Context, contexts with misaligned dimension/member arrays, and
        unresolvable pairs. Called ONCE per concept per event (the CLI caches).
        Empty for XBRL-less sources (e.g. 8-K)."""
        rows = self._read(
            "MATCH (pr:Report {accessionNo: $src})-[:HAS_XBRL]->(x:XBRLNode) "
            "MATCH (pr)-[:PRIMARY_FILER]->(co:Company) "
            "MATCH (f:Fact)-[:REPORTS]->(x) "
            "WHERE f.is_numeric = '1' AND f.is_nil = '0' "
            "AND f.qname = $concept "
            "MATCH (f)-[:HAS_PERIOD]->(p:Period) "
            "MATCH (f)-[:IN_CONTEXT]->(c:Context)-[:FOR_COMPANY]->(co) "
            "MATCH (f)-[:HAS_UNIT]->(u:Unit) "
            # THE CONCEPT'S OWN IDENTITY, both halves from ONE record.
            # `Concept.namespace` is the taxonomy URI the filing declared, so a
            # concept is compared by (namespace, local name) rather than by a
            # prefixed string in which the prefix is only an alias. `con.qname`
            # travels with it because the local half must be read off the SAME
            # record — combining a namespace here with a local part sliced from
            # somewhere else would assert an expanded name no source ever made.
            #
            # `Unit.namespace` is deliberately NOT transported. It holds the
            # Unit Type Registry's `nsUnit`, which is the literal string "null"
            # on 6,753 simple and all 113 divide Unit nodes — a truthy string
            # that any presence test would read as a real namespace. It is not
            # the measure's XML namespace and cannot stand in for one; the
            # filing's expanded measures are the semantic authority and
            # `u.name` stays purely as the storage-integrity comparison.
            #
            # OPTIONAL MATCH so a row missing its Concept edge stays VISIBLE and
            # can be refused by name, instead of vanishing from the result set.
            "OPTIONAL MATCH (f)-[:HAS_CONCEPT]->(con:Concept) "
            "RETURN f.id AS fid, f.fact_id AS fact_id, f.context_id AS context_id, "
            "p.period_type AS period_type, "
            "p.start_date AS start_date, p.end_date AS end_date, "
            "f.unit_ref AS unit_ref, f.value AS value, f.decimals AS decimals, "
            "u.name AS unit_name, u.is_divide AS is_divide, "
            "con.namespace AS concept_namespace, con.qname AS graph_concept_qname, "
            "c.dimension_u_ids AS dus, c.member_u_ids AS mus, "
            # THE MATCHED COMPANY, carried so the conversion has an authority.
            # `co` is already bound by the FOR_COMPANY match above; returning
            # its cik is what lets `_norm_uid` stop trusting each reference.
            "co.cik AS company_cik",
            src=source_id, concept=concept_qname)
        # THE ARRAYS ARE CHECKED BEFORE USE. `len()` on an int, `+` across
        # mismatched container types and `_norm_uid` on a non-string all raised
        # RAW TypeError/AttributeError — the signal reserved for our own bugs,
        # for what is only a bad row. A row we cannot read is DROPPED.
        # THE DROP IS UNCHANGED — only its VISIBILITY. Each reason is counted
        # per concept from THIS read: no second query, no per-fact rows.
        dropped = {}

        def _exclude(reason, r):
            bucket = dropped.setdefault(reason, {"facts": 0, "contexts": set()})
            bucket["facts"] += 1
            if isinstance(r, dict) and isinstance(r.get("context_id"), str):
                bucket["contexts"].add(r["context_id"])

        def _why_unusable(r):
            """The reason this row cannot be read, or None when it can."""
            if not isinstance(r, dict):    # `"dus" not in 5` is a raw TypeError
                return _EXCLUDED_UNREADABLE
            if "dus" not in r or "mus" not in r:
                return _EXCLUDED_UNREADABLE   # a missing column is a broken reader
            # ONLY `None` and `[]` lawfully mean "this fact has no dimensions".
            # `r["dus"] or []` turned EVERY falsey value — "", 0, False, {}, (),
            # set() — into an empty list, so a BROKEN array became a
            # dimensionless fact and the row was ACCEPTED. That is worse than a
            # silent drop: a dimensionless claim could then match a fact whose
            # real dimensions were merely unreadable.
            du, mu = r["dus"], r["mus"]
            du = [] if du is None else du
            mu = [] if mu is None else mu
            if type(du) is not list or type(mu) is not list \
                    or not all(isinstance(u, str) for u in du + mu):
                return _EXCLUDED_UNREADABLE
            # SEPARATE reason: the arrays are readable and disagree in length,
            # which is the symptom #828 exists to count.
            return None if len(du) == len(mu) else _EXCLUDED_MISALIGNED

        keep = []
        for r in rows:
            why = _why_unusable(r)
            if why is None:
                keep.append(r)
            else:
                _exclude(why, r)
        rows = keep
        ids = set()
        for r in rows:
            for u in (r["dus"] or []) + (r["mus"] or []):
                # NONE IS NEVER QUERIED AS AN ID. A reference that is not this
                # company's, or a company we cannot validate, contributes
                # nothing to the lookup and its pair fails closed below.
                n = _norm_uid(u, r.get("company_cik"))
                if n is not None:
                    ids.add(n)
        found = {}
        if ids:
            found = _resolve_id_records(self._read(
                    "MATCH (d:Dimension) WHERE d.id IN $ids "
                    "RETURN d.id AS id, 'Dimension' AS kind, d.qname AS qname, "
                    "null AS label, d.u_id AS u_id "
                    "UNION "
                    "MATCH (m:Member) WHERE m.id IN $ids "
                    "RETURN m.id AS id, 'Member' AS kind, m.qname AS qname, "
                    "m.label AS label, m.u_id AS u_id",
                    ids=sorted(ids)))
        out = []
        for r in rows:
            dims, ok = [], True
            for du, mu in zip(r["dus"] or [], r["mus"] or []):
                d = found.get(_norm_uid(du, r.get("company_cik")))
                m = found.get(_norm_uid(mu, r.get("company_cik")))
                # THE KIND IS CHECKED, not assumed: nothing stopped a MEMBER id
                # in the dimension array from writing a member's qname into the
                # AXIS position, which would fabricate an axis that does not
                # exist. An id must resolve to the node kind its slot requires.
                if not d or not m or d.get("kind") != "Dimension" \
                        or m.get("kind") != "Member":
                    ok = False                     # unresolvable pair: fail-closed —
                    break                          # this fact can't verify a claim
                # THE EXPANDED NAME, carried explicitly. `u_id` itself is
                # never exposed or compared downstream — only the namespace it
                # was decoded into, beside the qname it belongs to.
                axis_ns = _namespace_from_uid(d.get("u_id"), d.get("qname"))
                member_ns = _namespace_from_uid(m.get("u_id"), m.get("qname"))
                if axis_ns is None or member_ns is None:
                    ok = False          # undecodable id: the same fail-closed
                    break               # path as an unresolvable pair
                dims.append({"axis": d["qname"], "member": m["qname"],
                             "label": m["label"],
                             "axis_namespace": axis_ns,
                             "member_namespace": member_ns})
            if ok:
                # ADDITIVE, read-only, and shaped like the certified Route-A
                # source adapter's own query: the SHORT inline element id
                # (`fact_id` — the join key to the filing's rendering), the
                # context id, the raw value string EXACTLY as stored (commas
                # intact; 807,132 of 1,000,000 numeric facts carry them), and
                # the SEMANTIC unit from the linked Unit node — `unit_ref` is a
                # bare pointer, `u.name`/`u.is_divide` are the authority. Scale
                # and evidence spans live in the filing's inline rendering, not
                # in the graph, and are read there by the certified binder.
                out.append({"period_type": r["period_type"],
                            # F5 (#827): the graph stores instants' end as
                            # the LITERAL string "null" (census 2026-07-28:
                            # 3,058 of 3,058); the ADAPTER owns the alias —
                            # it emits None, and no consumer recognises the
                            # sentinel any more.
                            "start_date": (None if r["start_date"] == "null"
                                           else r["start_date"]),
                            "end_date": (None if r["end_date"] == "null"
                                         else r["end_date"]), "dims": dims,
                            "fact_id": r.get("fact_id"),
                            "context_id": r.get("context_id"),
                            "unit_ref": r.get("unit_ref"),
                            "unit_name": r.get("unit_name"),
                            "is_divide": r.get("is_divide"),
                            "value": r.get("value"),
                            "decimals": r.get("decimals"),
                            # THE CONCEPT'S IDENTITY TRAVELS WITH THE ROW.
                            # Selecting these in the query but omitting them
                            # here would leave the binder's required identity
                            # unreachable through the real path, and every
                            # lawful fact would park as
                            # `missing_graph_concept_namespace`.
                            "concept_namespace": r.get("concept_namespace"),
                            "graph_concept_qname": r.get("graph_concept_qname")})
            else:
                _exclude(_EXCLUDED_UNRESOLVED, r)
        # ONE summary per reason, from THIS read — never a second query, never
        # thousands of per-fact rows, and never a sample implying completeness.
        exclusions = tuple(
            MappingProxyType({"event": reason, "where": "graph_fact_dimensions",
                              "concept": concept_qname,
                              "fact_count": bucket["facts"],
                              "context_count": len(bucket["contexts"])})
            for reason, bucket in sorted(dropped.items()))
        # FROZEN WHERE IT IS BUILT. The verification above is what makes these
        # rows worth anything, and a value a caller can edit afterwards carries
        # none of it. This does not import the staged deep-freezer: a LIVE
        # module importing staged code is exactly what the staging gate forbids,
        # so this constructor completes itself over the one shape it owns. The
        # two become one owner at the switch, when the staged half goes live.
        frozen = tuple(
            MappingProxyType({**r, "dims": tuple(MappingProxyType(d)
                                                 for d in r["dims"])})
            for r in out)
        return GraphFactRows(rows=frozen, exclusions=exclusions)

    def transaction(self):
        raise RuntimeError("writes are DISABLED on the Neo4j adapter until the "
                           "fitness gate — dry-run lane only")


_SOURCE_RANK = {"8k": 0, "transcript": 1, "10q": 2, "10k": 3, "news": 4}
_EASTERN = ZoneInfo("America/New_York")


def _rank_prior_units(rows):
    """The §9 read ranking (FINAL_DESIGN 300-301), applied to prior-guide selection:
    latest EASTERN day wins; within one day source rank (8k > transcript > 10q > 10k
    > news), then later absolute time, then source id — a total order that RESOLVES
    cross-source same-day disagreement (the 8-K's unit wins over a transcript's; no
    park). The one genuine ambiguity left is the winning SOURCE conflicting with
    ITSELF (collision records): its distinct units all return and the writer parks
    on multiple."""
    if not rows:
        return []

    def key(r):
        dt = datetime.fromisoformat(r["date"])
        return (dt.astimezone(_EASTERN).date(),
                -_SOURCE_RANK.get(r["source_type"], 9), dt, r["source_id"])
    winner = max(rows, key=key)
    return sorted({r["series_unit"] for r in rows
                   if r["source_id"] == winner["source_id"]})


def preflight(store):
    """READ-ONLY §7 preflight: report what setup exists; never create anything.
    EXACT checks: a UNIQUENESS constraint on <label>.id, and sentinels carrying
    complete properties (u_id present, both dates null)."""
    uniques = {(row["labelsOrTypes"][0], tuple(row["properties"] or ()))
               for row in store._read(
                   "SHOW CONSTRAINTS YIELD labelsOrTypes, properties, type "
                   "WHERE type = 'UNIQUENESS' RETURN labelsOrTypes, properties")
               if row.get("labelsOrTypes")}
    sentinels = [r["id"] for r in store._read(
        "MATCH (p:DriverPeriod) WHERE p.id IN $ids AND p.u_id = p.id "
        "AND p.start_date IS NULL AND p.end_date IS NULL RETURN p.id AS id",
        ids=list(PERIOD_SENTINEL_SCOPE))]
    report = {"constraint_driverupdate": ("DriverUpdate", ("id",)) in uniques,
              "constraint_driverperiod": ("DriverPeriod", ("id",)) in uniques,
              "constraint_driver_name": ("Driver", ("name",)) in uniques,
              "sentinels_present": sorted(sentinels),
              "sentinels_missing": sorted(set(PERIOD_SENTINEL_SCOPE) - set(sentinels))}
    report["ready"] = (report["constraint_driverupdate"]
                       and report["constraint_driverperiod"]
                       and report["constraint_driver_name"]
                       and not report["sentinels_missing"])
    return report


def main(argv=None):
    """The one dry-run command. Real writes are not even a flag here."""
    import argparse

    from driver.core.driver_write_cli import load_run_input, run_event
    p = argparse.ArgumentParser(
        prog="driver-write", description="S3.5 internal writer — DRY-RUN ONLY")
    p.add_argument("input", nargs="?",
                   help="RunInputV1 JSON file (one source event)")
    p.add_argument("--audit-dir")
    p.add_argument("--preflight", action="store_true",
                   help="print the read-only preflight report and exit (no input)")
    a = p.parse_args(argv)
    store = Neo4jStore()
    try:
        if a.preflight:
            print(json.dumps(preflight(store), indent=2))
            return 0
        if not a.input or not a.audit_dir:
            p.error("input and --audit-dir are required unless --preflight")
        raw, run_input = load_run_input(a.input)
        out = run_event(run_input, store=store, audit_dir=a.audit_dir,
                        input_bytes=raw)           # FYE read once, inside run_event
        print(json.dumps(out, default=str, indent=2))
        return 0 if out["status"] != "failed" else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
