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
