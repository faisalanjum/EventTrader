#!/usr/bin/env python3
"""Build EXP-1 dry-run inputs (0-LLM, READ-ONLY Neo4j): FA_selection.json (draft, unsigned)
+ fixtures/fixture_resolutions.json. Env-first creds. No writes, no LLM."""
import os, re, json
from neo4j import GraphDatabase

TICKERS = {'base': ['CAKE','DRI','MCD','YUM','CMG'],
           'adjacent': ['AZO','ORLY','BBY','ULTA'],
           'contrast': ['DAL','AAL','LUV']}
ALL_TICKERS = TICKERS['base'] + TICKERS['adjacent'] + TICKERS['contrast']
WHITELIST_UNITS = {'iso4217:USD', 'shares', 'iso4217:USDshares'}  # live P4c names

def slug(s):
    s = re.sub(r'[^a-z0-9]+', '_', (s or '').lower()).strip('_')
    return re.sub(r'_+', '_', s)

def main():
    uri=os.environ.get('NEO4J_URI'); user=os.environ.get('NEO4J_USERNAME'); pw=os.environ.get('NEO4J_PASSWORD')
    if not (uri and pw): raise SystemExit('ABORT: NEO4J creds not in env (env-first)')
    drv=GraphDatabase.driver(uri, auth=(user or 'neo4j', pw))
    filings={}; fixres={}
    with drv.session() as s:
        def q(query, **p): return list(s.run(query, **p))
        for t in ALL_TICKERS:
            k=q("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$t}) WHERE r.formType='10-K' AND r.xbrl_status='COMPLETED' RETURN r.id AS id, substring(r.created,0,10) AS d, r.periodOfReport AS por ORDER BY r.created DESC LIMIT 2", t=t)
            qq=q("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$t}) WHERE r.formType='10-Q' AND r.xbrl_status='COMPLETED' RETURN r.id AS id, substring(r.created,0,10) AS d, r.periodOfReport AS por ORDER BY r.created DESC LIMIT 3", t=t)
            filings[t]=[{'report_id':x['id'],'form':'10-K','created':x['d'],'periodOfReport':x['por']} for x in k]+[{'report_id':x['id'],'form':'10-Q','created':x['d'],'periodOfReport':x['por']} for x in qq]
            rows=q("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$t}) WHERE r.formType IN ['10-K','10-Q'] AND r.xbrl_status='COMPLETED' AND r.created >= '2023-01-01' MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE f.is_numeric='1' AND f.is_nil='0' OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit) WITH con.qname AS qname, count(f) AS usage, collect(DISTINCT u.name) AS units WHERE usage >= 4 RETURN qname, usage, units ORDER BY usage DESC LIMIT 80", t=t)
            recs=[{'qname':x['qname'],'usage':x['usage'],'units':[u for u in (x['units'] or []) if u],'driver':'fx_'+slug(x['qname'].split(':')[-1])} for x in rows]
            def is_nonwl(r): return not any(u in WHITELIST_UNITS for u in r['units'])
            picked=recs[:40]
            nonwl=[r for r in picked if is_nonwl(r)]
            if len(nonwl) < 5:
                extra=[r for r in recs[40:] if is_nonwl(r)][:5-len(nonwl)]
                picked=picked[:40-len(extra)]+extra
            seen=set(); out=[]
            for r in picked:
                d=r['driver']
                while d in seen: d=d+'_x'
                r['driver']=d; seen.add(d); out.append(r)
            fixres[t]=out
    drv.close()
    fr={'probe':'EXP-1 fixture resolutions','recipe':'top<=40 concepts/company by usage>=4 (2023-2026) numeric non-nil; driver=fx_+slug(qname local); >=5 non-whitelist-unit included; 1:1 qname->driver','whitelist_units':sorted(WHITELIST_UNITS),'by_company':fixres}
    with open('fixtures/fixture_resolutions.json','w') as fh: json.dump(fr, fh, indent=2, sort_keys=True)
    fa={'phase':1,'draft':True,'signed_off_by':None,'o2_status':'PENDING_FABLE_SIGNOFF',
        'note':'EXP-1 dry-run draft: 12 companies + ~60 filings + fixtures. 36 events NOT included (materializer does not consume them; filled at full WP-FA).',
        'groups':{k:{'tickers':v} for k,v in TICKERS.items()},
        'catalog_side':{'fc_build_tickers':['CAKE','DRI','MCD','YUM','CMG','SBUX','QSR','TXRH'],'holdout_tickers':['BLMN','SHAK'],'t0_frozen_db':'2026-04-28'},
        'filings':filings,'filing_count':sum(len(v) for v in filings.values()),
        'mandatory_fixtures':{'filer_5253':'DRI',
          'null_periodofreport_report':'SYNTHETIC (D6 extension: census found 0 COMPLETED-XBRL null-pOR graph-wide; harness blanks a real report periodOfReport - fixture-only, never a graph write; NOT production evidence/design rule)',
          'multi_registrant_report':'SYNTHETIC (D6 extension: census found 0 multi-registrant graph-wide; harness-constructed 2-registrant input for EXP-1 P4f coverage only; NOT production evidence/design rule)',
          'precision_dup_pair_report':'BACKFILLED_BY_DRYRUN'}}
    with open('fixtures/FA_selection.json','w') as fh: json.dump(fa, fh, indent=2, sort_keys=True)
    print('filings total', fa['filing_count'])
    for t in ALL_TICKERS:
        nw=sum(1 for r in fixres[t] if not any(u in WHITELIST_UNITS for u in r['units']))
        print('%-5s filings=%d fixture_concepts=%d nonwl=%d' % (t, len(filings[t]), len(fixres[t]), nw))
    print('WROTE fixtures/FA_selection.json + fixtures/fixture_resolutions.json')

if __name__=='__main__': main()
