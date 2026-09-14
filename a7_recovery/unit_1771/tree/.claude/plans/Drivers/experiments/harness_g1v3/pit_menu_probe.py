#!/usr/bin/env python3
"""EXP-1 PIT-menu proof (READ-ONLY, 0 LLM). On 5 FA events: build the PIT concept menu (the ticker's
COMPLETED-XBRL numeric in-context concepts from reports with r.created <= event_time) and prove
(a) every menu concept's GLOBAL earliest r.created <= event_time (no future leak) and
(b) at least one post-event-only concept exists and is ABSENT from the menu. Writes pit_menu_proof.json."""
import os, json, argparse
from neo4j import GraphDatabase

MENU_Q = ("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$tk}) "
          "WHERE r.formType IN ['10-K','10-Q','10-K/A','10-Q/A'] AND r.xbrl_status='COMPLETED' AND r.created <= $ev "
          "MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) "
          "MATCH (f)-[:IN_CONTEXT]->(:Context) WHERE f.is_numeric='1' RETURN DISTINCT con.qname AS qname")
EARLIEST_Q = ("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$tk}) "
              "WHERE r.formType IN ['10-K','10-Q','10-K/A','10-Q/A'] AND r.xbrl_status='COMPLETED' "
              "MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) "
              "MATCH (f)-[:IN_CONTEXT]->(:Context) WHERE f.is_numeric='1' RETURN con.qname AS qname, min(r.created) AS earliest")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); a = ap.parse_args()
    uri = os.environ['NEO4J_URI']; user = os.environ.get('NEO4J_USERNAME'); pw = os.environ['NEO4J_PASSWORD']
    fa = json.load(open('fixtures/FA_selection.json'))
    filings = [(tk, f['report_id']) for tk, lst in fa['filings'].items() for f in lst]
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw))
    results = []
    with drv.session() as s:
        created = {}
        for tk, rid in filings:
            row = s.run("MATCH (r:Report {id:$rid}) RETURN r.created AS c", rid=rid).single()
            if row and row['c']: created[(tk, rid)] = row['c']
        picks = sorted(created.items(), key=lambda kv: kv[1])[:5]   # 5 earliest -> post-event concepts exist
        for (tk, rid), ev in picks:
            menu = set(x['qname'] for x in s.run(MENU_Q, tk=tk, ev=ev))
            earliest = {x['qname']: x['earliest'] for x in s.run(EARLIEST_Q, tk=tk)}
            a_viol = [qn for qn in menu if earliest.get(qn, '9999') > ev]
            post = [qn for qn, e in earliest.items() if e > ev]
            leaks = [qn for qn in post if qn in menu]
            ok = (len(a_viol) == 0 and len(leaks) == 0 and len(post) > 0)
            results.append({'ticker': tk, 'report_id': rid, 'event_time': ev, 'menu_size': len(menu),
                            'a_menu_concepts_all_le_event': len(a_viol) == 0, 'a_violations': a_viol[:5],
                            'post_event_concepts': len(post), 'b_post_event_absent_from_menu': len(leaks) == 0,
                            'leaks': leaks[:5], 'pass': ok})
    drv.close()
    proof = {'probe': 'PIT-menu proof (5 FA events, read-only)', 'events': results,
             'pass': all(r['pass'] for r in results) and len(results) == 5}
    json.dump(proof, open(a.rundir + '/pit_menu_proof.json', 'w'), indent=2, sort_keys=True)
    for r in results:
        print('%-5s %-24s ev=%s menu=%d post=%d a_ok=%s b_ok=%s PASS=%s' % (
            r['ticker'], r['report_id'], r['event_time'][:10], r['menu_size'], r['post_event_concepts'],
            r['a_menu_concepts_all_le_event'], r['b_post_event_absent_from_menu'], r['pass']))
    print('PIT_MENU_PASS', proof['pass'])
    print('WROTE', a.rundir + '/pit_menu_proof.json')


if __name__ == '__main__':
    main()
