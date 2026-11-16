import ast, hashlib, json, pathlib, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = pathlib.Path('/tmp/decider_claude_review_20261115')
sys.path.insert(0, '/home/faisal/EventMarketDB')

def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str))

def boundary_audit():
    src=pathlib.Path('/tmp/claude_decider_review_20261115')
    tree=ast.parse((src/'locate_boundaries.py').read_text())
    env={}
    for n in tree.body:
        if isinstance(n,ast.Assign) and all(isinstance(t,(ast.Name,ast.Tuple)) for t in n.targets):
            try: exec(compile(ast.Module(body=[n],type_ignores=[]),'<constants>','exec'),{},env)
            except (NameError,TypeError): pass
        if 'CASES' in env: break
    cases=env['CASES']; out={}
    for variant in ['before','after']:
        data=json.loads((src/f'locate_{variant}.json').read_text())
        hits=total=extra=badpos=nh=nt=0; misses=[]
        assert len(cases)==len(data['cases'])
        for (text,label,gold),r in zip(cases,data['cases']):
            assert text==r['text'] and label==r['label']
            found={s['text'] for s in r['spans']}
            h=sum(any(v in found for v in opts) for opts in gold)
            hits+=h; total+=len(gold)
            extra+=sum(not any(v in opts for opts in gold) for v in found)
            badpos+=sum(text[s['start']:s['end']]!=s['text'] for s in r['spans'])
            if label in ['Percentages','Dollar amounts']: nh+=h; nt+=len(gold)
            if h<len(gold): misses.append({'text':text,'expected':gold,'found':sorted(found)})
        out[variant]={'cases':len(cases),'hits':hits,'expected':total,'extra':extra,'incorrect_offsets':badpos,'numeric_hits':nh,'numeric_expected':nt,'misses':misses}
    save('boundary_audit.json',out);print(json.dumps(out),flush=True)

def graph_check():
    from scripts.earnings.utils import load_env,get_neo4j_config
    from neo4j import GraphDatabase,READ_ACCESS,Query
    load_env();uri,user,pw=get_neo4j_config()
    sources=json.loads((ROOT/'sources.json').read_text())
    queries=json.loads(pathlib.Path('/tmp/decider_prompt_study_20261115_djs24x24/snapshot_queries.json').read_text())
    all_results=[]
    with GraphDatabase.driver(uri,auth=(user,pw)) as driver:
        with driver.session(default_access_mode=READ_ACCESS) as session:
            for s in sources:
                fresh={k:[r.data() for r in session.run(Query(queries[k],timeout=45),id=s['id'])] for k in ['meta','prepared','qa','guidance']}
                old={r['update']['id']:r['update'] for r in s['records']}
                new={r['update']['id']:r['update'] for r in fresh['guidance']}
                changed=[i for i in old.keys() & new.keys() if old[i]!=new[i]]
                all_results.append({'id':s['id'],'old_records':len(old),'live_records':len(new),'missing_ids':sorted(old.keys()-new.keys()),'extra_ids':sorted(new.keys()-old.keys()),'changed_record_ids':changed,'prepared_nodes':len(fresh['prepared']),'qa_exchanges':len(fresh['qa']),'fresh':fresh})
                print(json.dumps({k:v for k,v in all_results[-1].items() if k!='fresh'}),flush=True)
            catalog=session.run(Query('MATCH (g:Guidance) RETURN count(g) AS nodes,count(DISTINCT g.label) AS labels',timeout=45)).single().data()
    save('live_graph_check.json',{'checked_at':datetime.now(ZoneInfo('America/Toronto')).isoformat(),'catalog':catalog,'sources':all_results})
    print('catalog',catalog,flush=True)

def model_checks():
    from config import local_llm as L
    sources={s['id']:s for s in json.loads((ROOT/'sources.json').read_text())}
    cs=sources['CTAS_2026-03-25T10.00']; ps=sources['PAYX_2025-12-19T09.30']
    cases=[]
    for s,pids,name in [(cs,['QA016'],'organic'),(cs,['QA022'],'erp'),(cs,[p['id'] for p in cs['passages'] if p['kind']=='prepared'],'cintas_prepared'),(ps,[p['id'] for p in ps['passages'] if p['kind']=='prepared'],'paychex_prepared')]:
        text='\n\n'.join('['+p['id']+'] '+p['text'] for p in s['passages'] if p['id'] in pids)
        cases.append({'name':name,'source_id':s['id'],'state':text,'questions':{'values':{'type':'locate','instructions':'Numbers, amounts, percentages and numeric ranges'},'wording':{'type':'locate','instructions':'Forecast wording without a number (e.g. low double digits, towards the low end of the range, something less than that)'}}})
    # Freeze inputs before any inference. Expected records are never given to the model.
    save('candidate_requests.json',cases)
    results=[]
    for c in cases:
        t=time.perf_counter()
        try:
            response=L.decide(c['state'],c['questions'],mode='isolated',timeout=1800)
            result={**c,'response':response,'seconds':time.perf_counter()-t,'finished_at':datetime.now(ZoneInfo('America/Toronto')).isoformat()}
        except Exception as e:
            result={**c,'error':str(e),'seconds':time.perf_counter()-t}
        results.append(result);save('candidate_results.json',results)
        print(json.dumps({'name':c['name'],'seconds':round(result['seconds'],2),'error':result.get('error'),'answers':result.get('response',{}).get('answers'),'usage':result.get('response',{}).get('usage')},ensure_ascii=False),flush=True)

if __name__=='__main__':
    {'boundary':boundary_audit,'graph':graph_check,'model':model_checks}[sys.argv[1]]()
