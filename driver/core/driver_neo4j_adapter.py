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
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

__all__ = ["Neo4jStore", "preflight", "main"]

_NUMERIC_FACT_FIELDS = ("level_low", "level_high", "change_value",
                        "comparison_low", "comparison_high")
_SENTINELS = ("gp_ST", "gp_MT", "gp_LT", "gp_UNDEF")


def _exact(value):
    if isinstance(value, bool) or not isinstance(value, float):
        return value
    return Decimal(repr(value))            # the ONE sanctioned float bridge


def _norm_uid(u_id):
    """The proven harness fix (bug1_cik_zero_padding): context arrays carry a
    zero-padded cik segment, node ids an unpadded one — strip before lookup."""
    cik, _, rest = (u_id or "").partition(":")
    return f"{cik.lstrip('0') or '0'}:{rest}"


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

    def _read(self, query, **params):
        with self._driver.session(database=self._db,
                                  default_access_mode="READ") as s:
            return [dict(rec) for rec in s.run(query, **params)]

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

    # the context arrays carry a zero-PADDED cik segment while Dimension/Member
    # u_ids carry it UNPADDED — the proven harness fix (norm_uid, bug1_cik_zero_
    # padding): strip the zeros ON the cik segment before the lookup, and look
    # up by id (== u_id, verified live), the INDEXED property on both labels.
    # AAPL regression: 1,886 dimensional contexts returned ZERO under a raw join.
    _MEMBER_PAIRING = (
        "WITH DISTINCT c "
        "UNWIND range(0, size(c.dimension_u_ids)-1) AS i "
        "WITH DISTINCT c.dimension_u_ids[i] AS du, c.member_u_ids[i] AS mu "
        "WITH du, mu, split(du, ':')[0] AS dcik, split(mu, ':')[0] AS mcik "
        "WITH toString(toInteger(dcik)) + substring(du, size(dcik)) AS ndu, "
        "toString(toInteger(mcik)) + substring(mu, size(mcik)) AS nmu "
        "MATCH (d:Dimension {id: ndu}) "
        "MATCH (m:Member {id: nmu}) "
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
            + self._MEMBER_PAIRING, src=source_id, date=date)
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
            "RETURN f.id AS fid, p.period_type AS period_type, "
            "p.start_date AS start_date, p.end_date AS end_date, "
            "c.dimension_u_ids AS dus, c.member_u_ids AS mus",
            src=source_id, concept=concept_qname)
        rows = [r for r in rows                    # misaligned arrays: fail-closed
                if len(r["dus"] or []) == len(r["mus"] or [])]
        ids = set()
        for r in rows:
            for u in (r["dus"] or []) + (r["mus"] or []):
                ids.add(_norm_uid(u))
        found = {}
        if ids:
            for rec in self._read(
                    "MATCH (d:Dimension) WHERE d.id IN $ids "
                    "RETURN d.id AS id, d.qname AS qname, null AS label "
                    "UNION "
                    "MATCH (m:Member) WHERE m.id IN $ids "
                    "RETURN m.id AS id, m.qname AS qname, m.label AS label",
                    ids=sorted(ids)):
                found[rec["id"]] = rec
        out = []
        for r in rows:
            dims, ok = [], True
            for du, mu in zip(r["dus"] or [], r["mus"] or []):
                d, m = found.get(_norm_uid(du)), found.get(_norm_uid(mu))
                if not d or not m:
                    ok = False                     # unresolvable pair: fail-closed —
                    break                          # this fact can't verify a claim
                dims.append({"axis": d["qname"], "member": m["qname"],
                             "label": m["label"]})
            if ok:
                out.append({"period_type": r["period_type"],
                            "start_date": r["start_date"],
                            "end_date": r["end_date"], "dims": dims})
        return out

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
        ids=list(_SENTINELS))]
    report = {"constraint_driverupdate": ("DriverUpdate", ("id",)) in uniques,
              "constraint_driverperiod": ("DriverPeriod", ("id",)) in uniques,
              "constraint_driver_name": ("Driver", ("name",)) in uniques,
              "sentinels_present": sorted(sentinels),
              "sentinels_missing": sorted(set(_SENTINELS) - set(sentinels))}
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
