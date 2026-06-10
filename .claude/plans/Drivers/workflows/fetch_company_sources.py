#!/usr/bin/env python3
"""
Content-pull layer (B) for the Driver catalog seed build.

For ONE ticker, fetch ALL non-news company sources WITH their real text:
  - Transcripts   -> prepared remarks + Q&A exchanges
  - 8-K (earnings, Item 2.02) -> EX-99.1 press release
  - 8-K (other)   -> item codes + short description (the item code IS the driver signal)
  - 10-K / 10-Q   -> MD&A + Risk Factors + Business sections (skip the 139k financial-statement tables)
  - fiscal.ai KPIs

PHASE 0.5 (HierarchicalCatalogPlan §8/D7): ALL caps REMOVED — events are emitted as FULL
STRUCTURED sub-units (sections[] / ex991 / prepared / qa_exchanges[]), uncapped and unjoined;
`chunk_company_sources.py` is the derived layer that joins + splits them into bounded bot inputs
(never dropping a byte). Q&A is sorted NUMERICALLY by toInteger(qa.sequence) — the property is
stored as a STRING, so the old `ORDER BY qa.sequence` scrambled exchange order alphabetically.
Tags per event: high_signal (|daily_stock| >= 2.0), is_earnings (8-K + Item 2.02), source_type, date.
NO >2% filter — every non-news event is included; >2% is only a flag.

Read-only on Neo4j. With --run-dir DIR: writes DIR/sources/<TICKER>.json + DIR/sources_manifest.json
(sha256/source_id_count/bytes per file). Without it (legacy): .claude/plans/Drivers/_sources_<ticker>.json.
Reusable: `python3 fetch_company_sources.py <TICKER> [TICKER2 ...] [--run-dir DIR]`
"""
import os, sys, json, sqlite3, hashlib, argparse
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/faisal/EventMarketDB")
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)
from neo4j import GraphDatabase

URI  = os.getenv("NEO4J_URI", "bolt://10.102.222.120:7687")
USER = os.getenv("NEO4J_USERNAME", "neo4j")
PW   = os.getenv("NEO4J_PASSWORD")
FISCAL_DB = str(ROOT / "data/fiscal_ai_segments/fiscal_segments.sqlite")
OUT_DIR = ROOT / ".claude/plans/Drivers"

REPORTS_Q = """
MATCH (rep:Report)-[r:PRIMARY_FILER]->(c:Company {ticker:$tk})
WHERE rep.formType IS NOT NULL
  AND (rep.formType STARTS WITH '8-K' OR rep.formType STARTS WITH '10-K' OR rep.formType STARTS WITH '10-Q')
OPTIONAL MATCH (rep)-[:HAS_SECTION]->(s:ExtractedSectionContent)
  WHERE s.section_name CONTAINS 'DiscussionandAnalysis' OR s.section_name='RiskFactors' OR s.section_name='Business'
WITH rep, r, collect(DISTINCT {name:s.section_name, content:s.content}) AS secs
OPTIONAL MATCH (rep)-[:HAS_EXHIBIT]->(ex:ExhibitContent) WHERE ex.exhibit_number='EX-99.1'
WITH rep, r, secs, head(collect(ex.content)) AS ex991
RETURN rep.id AS source_id,
       coalesce(rep.formType,'report') AS form_type,
       substring(coalesce(rep.created,''),0,10) AS date,
       toString(coalesce(rep.items,'')) AS items,
       coalesce(rep.description,'') AS description,
       r.daily_stock AS daily_stock,
       secs, ex991
ORDER BY date DESC
"""

TRANS_Q = """
MATCH (t:Transcript)-[r:INFLUENCES]->(c:Company {ticker:$tk})
OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
WITH t, r, head(collect(pr.content)) AS prepared
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
WITH t, r, prepared, qa ORDER BY toInteger(qa.sequence)
WITH t, r, prepared, collect(toString(qa.exchanges)) AS qa_list
RETURN t.id AS source_id,
       substring(coalesce(t.created,t.conference_datetime,''),0,10) AS date,
       toString(t.fiscal_year) AS fy, toString(t.calendar_quarter) AS q,
       r.daily_stock AS daily_stock, prepared, qa_list
ORDER BY date DESC
"""

def hi(ds):
    try: return abs(float(ds)) >= 2.0
    except (TypeError, ValueError): return False

def is_earnings_8k(form_type, items):
    return form_type.startswith("8-K") and "2.02" in (items or "")

# (build_report_content / build_trans_content REMOVED — fetch no longer caps or joins;
#  chunk_company_sources.py builds event_text from these structured sub-units, §12.2)

def fiscal_kpis(tk):
    if not Path(FISCAL_DB).exists(): return []
    con = sqlite3.connect(FISCAL_DB)
    try:
        rows = con.execute(
            "SELECT DISTINCT metric_name FROM fiscal_segments "
            "WHERE section='Key Performance Indicators' AND symbol=?", (tk,)).fetchall()
    finally:
        con.close()
    return sorted({r[0] for r in rows if r[0]})

def fetch(tk, session):
    events = []
    for rec in session.run(REPORTS_Q, tk=tk):
        d = rec.data()
        secs = [s for s in (d["secs"] or []) if s and s.get("content")]
        ex991 = d.get("ex991")
        clen = sum(len(s["content"]) for s in secs) + len(ex991 or "") + len(d["description"] or "")
        events.append({
            "source_id": d["source_id"],
            "source_type": d["form_type"], "date": d["date"],
            "daily_stock": d["daily_stock"], "high_signal": hi(d["daily_stock"]),
            "is_earnings": is_earnings_8k(d["form_type"], d["items"]),
            "items": d["items"], "description": d["description"],
            "sections": secs, "ex991": ex991, "content_len": clen,
        })
    for rec in session.run(TRANS_Q, tk=tk):
        d = rec.data()
        qa = [q for q in (d.get("qa_list") or []) if q]
        prepared = d.get("prepared")
        clen = len(prepared or "") + sum(len(q) for q in qa)
        events.append({
            "source_id": d["source_id"],
            "source_type": "transcript", "date": d["date"],
            "daily_stock": d["daily_stock"], "high_signal": hi(d["daily_stock"]),
            "is_earnings": False, "fy": d["fy"], "q": d["q"],
            "prepared": prepared, "qa_exchanges": qa, "content_len": clen,
        })
    kpis = fiscal_kpis(tk)
    by_type = {}
    for e in events: by_type[e["source_type"]] = by_type.get(e["source_type"], 0) + 1
    return {
        "ticker": tk, "fiscal_kpis": kpis,
        "counts": {"events": len(events), "by_type": by_type, "fiscal_kpis": len(kpis),
                   "high_signal": sum(1 for e in events if e["high_signal"]),
                   "earnings_8k": sum(1 for e in events if e["is_earnings"])},
        "total_content_chars": sum(e["content_len"] for e in events),
        "empty_content_events": sum(1 for e in events if e["content_len"] < 50),
        "events": events,
    }

def main():
    if not PW:
        print("ERROR: NEO4J_PASSWORD not set (.env)", file=sys.stderr); sys.exit(1)
    ap = argparse.ArgumentParser(description="Fetch all non-news company sources into a run dir.")
    ap.add_argument("tickers", nargs="*", help="ticker symbols")
    ap.add_argument("--run-dir", help="run folder: sources -> <run-dir>/sources/<TICKER>.json, hashes -> <run-dir>/sources_manifest.json")
    a = ap.parse_args()
    tickers = a.tickers
    if not tickers:
        print("ERROR: no tickers given. Usage: fetch_company_sources.py TICKER [TICKER ...] [--run-dir DIR]", file=sys.stderr); sys.exit(1)
    run_dir = Path(a.run_dir) if a.run_dir else None
    src_dir = (run_dir / "sources") if run_dir else OUT_DIR
    src_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = []
    driver = GraphDatabase.driver(URI, auth=(USER, PW))
    try:
        with driver.session() as s:
            for tk in tickers:
                data = fetch(tk, s)
                fname = f"{tk}.json" if run_dir else f"_sources_{tk}.json"
                out = src_dir / fname
                blob = json.dumps(data, indent=1)
                out.write_text(blob)
                digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
                manifest.append({"ticker": tk, "file": fname, "sha256": digest,
                                 "source_id_count": data["counts"]["events"], "bytes": len(blob.encode("utf-8"))})
                c = data["counts"]
                print(f"{tk}: {c['events']} events {c['by_type']} | kpis={c['fiscal_kpis']} "
                      f"| hi={c['high_signal']} earn8k={c['earnings_8k']} | "
                      f"{data['total_content_chars']:,} chars | empty={data['empty_content_events']} | sha={digest[:12]} -> {out.name}")
    finally:
        driver.close()
    if run_dir:
        (run_dir / "sources_manifest.json").write_text(json.dumps({"fetched_at": fetched_at, "sources": manifest}, indent=1))
        print(f"sources_manifest.json written ({len(manifest)} tickers, fetched_at={fetched_at})")

if __name__ == "__main__":
    main()
