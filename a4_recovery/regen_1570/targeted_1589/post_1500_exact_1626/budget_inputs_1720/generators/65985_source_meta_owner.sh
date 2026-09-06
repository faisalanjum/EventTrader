V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
cat > "$V3/a7_source_meta.py" <<'PYEOF'
"""The frozen source-metadata sidecar: one exact public instant per event.

Codex SEQ 1454 item 2. READ-ONLY. It opens a Neo4j READ session, reads the
live source node of each event, and freezes what the route needs. It never
writes to Neo4j, never synthesizes a timestamp, never infers a zone, and stops
any row whose data is missing, malformed or inconsistent.

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

SIDECAR = "/tmp/a7_source_instants.json"
SCHEMA = "a7_source_instants/1"

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


def _read_session():
    if not os.environ.get("NEO4J_URI"):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(_REPO, ".env"))
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
    try:
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

    doc = collections.OrderedDict([
        ("schema", SCHEMA),
        ("events", len(rows)),
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
PYEOF
cd "$V3" && CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 timeout 900 /home/faisal/EventMarketDB/venv/bin/python3 -c "
import sys; sys.path.insert(0,'.')
import a7_source_meta as SM, json
path, doc, probs = SM.freeze()
print('problems:', len(probs), probs[:3])
print('path    :', path)
print('events  :', doc['events'])
print('by label:', json.dumps(doc['by_source_label']))
print('by type :', json.dumps(doc['by_source_type']))
" 2>&1 | tail -8