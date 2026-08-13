"""K-fields/EXP-5 PIT slice-menu probe — ra_0009 ruling (Fable 2026-07-24).

Retrieval = the O13-ratified positional pairing (the production adapter's law,
S4-exercised), anchored on (Company {ticker}) + event_time because the 36
events include transcripts/news that are not Report nodes. Classification,
normalization, FS-20 and provisional handling come UNCHANGED from
driver.core.slice_menu.build_menu (read-only import — sanctioned by the
work-order harness-imports table). Read-only; zero writes; zero LLM.

Usage:  venv/bin/python harness/slice_menu_probe.py TICKER EVENT_TIME_ISO
        -> prints {"tokens": [...], "n_raw": N, "n_logs": N}
Import: menu_for(ticker, event_time) -> (sorted tokens, raw rows, logs)
"""
import json
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
sys.path.insert(0, _REPO)

from driver.core.slice_menu import build_menu                    # THE law
from driver.core.driver_neo4j_adapter import _norm_uid           # proven CIK fix

def _driver():
    if not os.environ.get("NEO4J_URI"):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(_REPO, ".env"))
    from neo4j import GraphDatabase
    return GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))


def _menu_rows(ticker, event_time):
    """Two-phase like the adapter: pull the DISTINCT (du, mu) pairs, then the
    CIK-normalized indexed-id lookup in one second query (arrays carry a
    zero-padded cik segment; node ids do not — _norm_uid, the proven fix)."""
    drv = _driver()
    try:
        with drv.session(default_access_mode="READ") as s:
            pairs = [(r["du"], r["mu"], r["cik"]) for r in s.run(
                "MATCH (co:Company {ticker: $ticker}) "
                "MATCH (co)<-[:PRIMARY_FILER]-(pr:Report)-[:HAS_XBRL]->(px:XBRLNode) "
                "WHERE pr.formType IN ['10-K','10-Q','10-K/A','10-Q/A'] "
                "AND datetime(pr.created) <= datetime($event_time) "
                "WITH co, collect(DISTINCT px) AS xs "
                "MATCH (co)<-[:FOR_COMPANY]-(c:Context) "
                "WHERE size(c.dimension_u_ids) > 0 "
                "AND size(c.dimension_u_ids) = size(c.member_u_ids) "
                "AND EXISTS { MATCH (f:Fact)-[:IN_CONTEXT]->(c), "
                "  (f)-[:REPORTS]->(x2:XBRLNode) "
                "  WHERE f.is_numeric = '1' AND x2 IN xs } "
                "WITH DISTINCT co, c "
                "UNWIND range(0, size(c.dimension_u_ids)-1) AS i "
                "RETURN DISTINCT c.dimension_u_ids[i] AS du, "
                "  c.member_u_ids[i] AS mu, co.cik AS cik",
                ticker=ticker, event_time=event_time)]
            if not pairs:
                return []
            # THE MATCHED COMPANY IS THE AUTHORITY (production `_norm_uid`
            # docstring). #827 made that argument required precisely so a stored
            # reference can no longer vouch for its own company; this probe still
            # called the one-argument form and crashed. The cik travels with the
            # pair from the `co:Company` row that was ALREADY matched — it is
            # never inferred from the reference and no cik is parsed here.
            ids = sorted({n for du, mu, cik in pairs
                          for u in (du, mu)
                          for n in (_norm_uid(u, cik),) if n})
            found = {r["id"]: (r["kind"], r["qname"], r["label"]) for r in s.run(
                "CALL { MATCH (d:Dimension) WHERE d.id IN $ids "
                "       RETURN d.id AS id, 'dim' AS kind, d.qname AS qname, null AS label "
                "  UNION MATCH (m:Member) WHERE m.id IN $ids "
                "       RETURN m.id AS id, 'mem' AS kind, m.qname AS qname, m.label AS label } "
                "RETURN id, kind, qname, label", ids=ids)}
            rows = []
            for du, mu, cik in pairs:
                # FAIL CLOSED: a missing, malformed, non-registrant or
                # mismatching cik makes `_norm_uid` return None, which resolves
                # to no row here and the pair is skipped — never a raw exception.
                d = found.get(_norm_uid(du, cik))
                m = found.get(_norm_uid(mu, cik))
                if not d or not m or d[0] != "dim" or m[0] != "mem":
                    continue                        # unresolvable pair: fail-closed skip
                rows.append({"axis": d[1], "member": m[1], "label": m[2]})
            return rows
    finally:
        drv.close()


def menu_for(ticker, event_time):
    """(sorted token list, raw rows, structured logs). used_scopes arm = [] —
    honestly stated: the pre-build catalog-used half is EMPTY (work-order
    'stated honestly in the packet')."""
    raw = _menu_rows(ticker, event_time)
    tokens, logs = build_menu(raw, [])
    return sorted(tokens), raw, logs


if __name__ == "__main__":
    t, ts = sys.argv[1], sys.argv[2]
    tokens, raw, logs = menu_for(t, ts)
    print(json.dumps({"ticker": t, "event_time": ts, "n_raw": len(raw),
                      "n_tokens": len(tokens), "tokens": tokens,
                      "n_logs": len(logs)}, indent=1))
