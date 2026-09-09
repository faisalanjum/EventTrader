"""The frozen source-metadata sidecar: one exact public instant per event.

Codex SEQ 1454 item 2, narrowed by SEQ 1455 item 3. READ-ONLY. It never writes
to Neo4j, never synthesizes a timestamp, never infers a zone, and stops any row
whose data is missing, malformed or inconsistent.

EXACTLY WHAT IS AND IS NOT PROVED LIVE. Only the PUBLIC SOURCE INSTANT is read
from the live graph. `ticker` and `fye_month` are COPIED from the frozen signed
input; they are not re-derived from `Company`. A7 may keep the signed input
`fye_month` because the Work Order derives it from the latest 10-K, but that
means this owner proves the production route against the temporary test store,
NOT against the live Neo4j Company adapter. A read-only comparison found 15 of
the 36 events carrying an input `fye_month` different from live
`Company.fiscal_year_end_month` (DAL 4, BBY 4, YUM 4, ULTA 3); that difference
is carried in the sidecar as an explicit STEP-5 PRODUCTION-ADAPTER RISK and
nothing in Neo4j is changed here.

The owning law, live files:

  15_CandidateFactPacket.md:136  `event_time` = Report.created (PIT stamp),
                                 one Neo4j read per filing, missing -> PARK.
  FableExperimentWorkOrder.md:266  the three source-time properties are
                                 Report.created, Transcript.conference_datetime
                                 and News.created.

`event_date + "T00:00:00"` is the K-fields MENU CUTOFF anchor
(build_kfields_inputs.py, `compose`) and is not a publication time; it must
never reach the route. `route_event` therefore accepts only the frozen instant
itself, whatever its clock value, so the rule is "it must be the source's own
instant", not a blacklist of one string.
"""
import collections
import io
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
while _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)

_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))

#: v1 is the ORIGINAL frozen document: the five keys and nothing else. It was
#: overwritten in place once, which destroyed a frozen artifact; the exact
#: bytes were reconstructed and restored, and the overwritten file is kept
#: beside them as an invalid intermediate. The expanded document is a NEW
#: version at its own path, never a re-issue of /1.
SIDECAR_V1 = "/tmp/a7_source_instants.v1.json"
SCHEMA_V1 = "a7_source_instants/1"
SIDECAR = "/tmp/a7_source_instants.v2.json"
SCHEMA = "a7_source_instants/2"

#: source_type -> (node label, the property that owns its public instant).
#: Read from the law above; this module invents no time of its own.
OWNER = collections.OrderedDict([
    ("8k", ("Report", "created")),
    ("10q", ("Report", "created")),
    ("10k", ("Report", "created")),
    ("transcript", ("Transcript", "conference_datetime")),
    ("news", ("News", "created")),
])

BOUND_FIELDS = ("source_id", "source_type", "ticker", "fye_month",
                "event_time")
#: the ONE field read live; everything else in a row is copied from the frozen
#: signed input and is not evidence about the live graph.
LIVE_FIELDS = ("event_time",)
#: live property that would own `fye_month` in production, compared but never
#: consumed here (SEQ 1455 item 3)
COMPANY_FYE_PROPERTY = "fiscal_year_end_month"


def _inputs():
    """The 36 frozen draft inputs, by source id."""
    import build_launch_manifest as blm
    out = collections.OrderedDict()
    for name in sorted(os.listdir(blm.INPUTS)):
        if not name.endswith(".json"):
            continue
        with io.open(os.path.join(blm.INPUTS, name), encoding="utf-8") as fh:
            doc = json.load(fh)
        out[doc["source_id"]] = doc
    return out


#: the connection variables this owner consumes; it never loads a dotenv file
#: of its own - a scratch-root fallback silently resolved to a tree that has no
#: .env, so it could only ever mask a clear failure with an obscure one.
NEO4J_ENV = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")


def _read_session():
    absent = [name for name in NEO4J_ENV if not os.environ.get(name)]
    if absent:
        raise RuntimeError(
            "the Neo4j read connection needs %s in the environment; %s absent"
            % (", ".join(NEO4J_ENV), ", ".join(absent)))   # names only, ever
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))
    return driver, driver.session(default_access_mode="READ")


def freeze(dest=SIDECAR):
    """-> (path, doc, problems). One READ pass; refuses to overwrite."""
    if os.path.exists(dest):
        raise ValueError("%s already exists; the sidecar is frozen once" % dest)
    inputs = _inputs()
    problems, instants = [], {}
    for source_type in sorted({d["source_type"] for d in inputs.values()}):
        if source_type not in OWNER:
            problems.append("no source-time owner for source_type %r"
                            % source_type)
    driver, session = _read_session()
    company_fye = {}
    expected_tickers = sorted({d["ticker"] for d in inputs.values()})
    try:
        seen = []
        for record in session.run(
                "MATCH (c:Company) WHERE c.ticker IN $tickers "
                "RETURN c.ticker AS ticker, c.`%s` AS fye"
                % COMPANY_FYE_PROPERTY, tickers=expected_tickers):
            seen.append(record["ticker"])
            company_fye[record["ticker"]] = record["fye"]
        # EXACTLY ONE ROW PER EXPECTED TICKER. A missing, duplicated or null
        # value is an explicit problem; silently omitting it would understate
        # the very risk this comparison exists to record.
        for ticker in expected_tickers:
            if seen.count(ticker) > 1:
                problems.append("Company %s matched %d nodes"
                                % (ticker, seen.count(ticker)))
            elif ticker not in company_fye:
                problems.append("Company %s has no live node" % ticker)
            elif company_fye[ticker] is None:
                problems.append("Company %s carries no %s"
                                % (ticker, COMPANY_FYE_PROPERTY))
        for label, prop in sorted(set(OWNER.values())):
            ids = [sid for sid, d in inputs.items()
                   if OWNER.get(d["source_type"]) == (label, prop)]
            if not ids:
                continue
            query = ("MATCH (n:%s) WHERE n.id IN $ids "
                     "RETURN n.id AS id, n.`%s` AS instant" % (label, prop))
            for record in session.run(query, ids=ids):
                if record["id"] in instants:
                    problems.append("%s matches more than one source node"
                                    % record["id"])
                instants[record["id"]] = (label, prop, record["instant"])
    finally:
        session.close()
        driver.close()

    rows, counts = collections.OrderedDict(), collections.Counter()
    for sid, doc in inputs.items():
        found = instants.get(sid)
        if found is None:
            problems.append("%s: no live source node" % sid)
            continue
        label, prop, instant = found
        instant = None if instant is None else str(instant)
        if not instant or len(instant) <= len(doc["event_date"]):
            problems.append("%s: %s.%s is not a full public instant: %r"
                            % (sid, label, prop, instant))
            continue
        if instant[:10] != doc["event_date"]:
            problems.append("%s: instant %s does not fall on the frozen event "
                            "date %s" % (sid, instant, doc["event_date"]))
            continue
        counts[label] += 1
        rows[sid] = collections.OrderedDict([
            ("source_id", sid),
            ("source_type", doc["source_type"]),
            ("ticker", doc["ticker"]),
            ("fye_month", doc["fye_month"]),
            ("event_time", instant),
            ("event_date", doc["event_date"]),
            ("source_label", label),
            ("source_time_property", prop)])

    # SEQ 1455 item 3: recorded as a RISK, never applied. A7 keeps the signed
    # input value; this says out loud where that value is not the live one.
    fye_risk = [collections.OrderedDict([
        ("source_id", sid), ("ticker", row["ticker"]),
        ("input_fye_month", row["fye_month"]),
        ("live_company_fye_month", company_fye.get(row["ticker"]))])
        for sid, row in rows.items()
        if company_fye.get(row["ticker"]) is not None
        and str(company_fye[row["ticker"]]) != str(row["fye_month"])]

    doc = collections.OrderedDict([
        ("schema", SCHEMA),
        ("events", len(rows)),
        ("supersedes", collections.OrderedDict([
            ("path", SIDECAR_V1), ("schema", SCHEMA_V1)])),
        ("expected_tickers", len(expected_tickers)),
        ("live_fields", list(LIVE_FIELDS)),
        ("copied_from_signed_input",
         [f for f in BOUND_FIELDS if f not in LIVE_FIELDS]),
        ("step5_production_adapter_risk", collections.OrderedDict([
            ("what", "input fye_month differs from live Company.%s; the route "
                     "is proved against the temporary test store, not the live "
                     "Company adapter" % COMPANY_FYE_PROPERTY),
            ("events", len(fye_risk)),
            ("by_ticker", collections.OrderedDict(sorted(
                collections.Counter(r["ticker"] for r in fye_risk).items()))),
            ("rows", fye_risk)])),
        ("by_source_label", collections.OrderedDict(sorted(counts.items()))),
        ("by_source_type", collections.OrderedDict(sorted(
            collections.Counter(r["source_type"]
                                for r in rows.values()).items()))),
        ("rows", rows)])
    if problems:
        return None, doc, problems
    directory = os.path.dirname(os.path.abspath(dest))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, indent=2, sort_keys=False) + "\n")
        os.rename(tmp, dest)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return dest, doc, []


def load(path=SIDECAR):
    """{source_id: row} from the frozen sidecar."""
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)["rows"]


def route_event(sid, instant=None, path=SIDECAR):
    """ONE event exactly as the write-disabled Stage-A route requires it.

    `instant` exists so a mutation test can try to substitute a time; any value
    that is not this event's own frozen instant is refused. There is no
    special case for midnight - a real source may publish at midnight - the
    rule is simply that the route uses the source's own recorded instant.
    """
    from driver.core.driver_write_cli import V2_EVENT_FIELDS
    import build_launch_manifest as blm
    row = load(path)[sid]
    if instant is not None and instant != row["event_time"]:
        raise ValueError("%s: %r is not this source's frozen public instant "
                         "%r; the route never takes a substituted time"
                         % (sid, instant, row["event_time"]))
    with io.open(os.path.join(blm.INPUTS, "%s.json" % sid),
                 encoding="utf-8") as fh:
        raw = json.load(fh)
    for field in BOUND_FIELDS:
        if field == "event_time":
            continue
        if raw[field] != row[field]:
            raise ValueError("%s: frozen %s %r does not match the input %r"
                             % (sid, field, row[field], raw[field]))
    raw = dict(raw, event_time=row["event_time"])
    return {k: raw[k] for k in V2_EVENT_FIELDS if k != "items"}
