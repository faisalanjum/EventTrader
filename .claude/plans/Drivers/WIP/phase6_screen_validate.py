#!/usr/bin/env python3
"""REPEATABLE Phase-6 screen validator (zero AI). Check count = the printed PASS lines."""
import json, hashlib, os, sys
W=os.path.dirname(os.path.abspath(__file__))
EX=os.path.join(W,'..','..','..','..','scripts','driver_seed','relocate_probe','exhibit_html_cache')
ok=True
def chk(n,c):
    global ok; print(('PASS' if c else 'FAIL'),n); ok=ok and c
calls=[json.load(open(f'{W}/phase6_screen_call_{i+1}.json')) for i in range(3)]
raw=' '.join(open(f'{W}/phase6_screen_call_{i+1}.json').read() for i in range(3))
A=json.load(open(f'{W}/phase6_screen_answers_HIDDEN.json'))['answers']
allc=[c for f in calls for c in f['cases']]; reqs=[r for c in allc for r in c['requests']]
tabs={k:v for f in calls for k,v in f['tables'].items()}
chk('prompt embedded per call', all(f.get('prompt','').startswith('You are matching') for f in calls))
chk('leak: no expected*/truth/cell-answer keys; hidden file never referenced',
    all(t not in raw for t in ('expected','truth_','HIDDEN','cell_text','grading_law')))
chk('structural headings: every table has a non-numeric heading block',
    all(any(not any(ch.isdigit() for ch in b['text']) and b['text'].strip() for b in v['blocks']) for v in tabs.values()))
chk('source hashes: every table sha256 re-verified against cached bytes',
    all(hashlib.sha256(open(os.path.join(EX,v['source_file']),'rb').read()).hexdigest()==v['source_sha256'] for v in tabs.values()))
chk('93 requests / 19 rows / 8 tables / 7 filings',
    len(reqs)==93 and len(allc)==19 and len(tabs)==8 and len({v['source_file'] for v in tabs.values()})==7)
chk('full-field grading data present for every request',
    all(all(k in A[r['request_id']] for k in ('expected_request_id','expected_anchor_id','expected_occurrence','expected_block_id','expected_copied_label','expected_period_evidence_array')) for r in reqs))
chk('every evidence array nonempty, from audited aligned_headers_verbatim',
    all(A[r['request_id']]['expected_period_evidence_array'] for r in reqs))
chk('no label carries $', all('$' not in A[r['request_id']]['expected_copied_label'] for r in reqs))
chk('request and anchor ids are DIFFERENT fields',
    all(q['request_id']!=q['anchor_id'] and q['anchor_id']==A[q['request_id']]['expected_anchor_id'] for f2 in calls for c2 in f2['cases'] for q in c2['requests']))
sys.path.insert(0,W)
import importlib, phase6_screen_grade; importlib.reload(phase6_screen_grade)
from phase6_screen_grade import grade_one
rid0=reqs[0]['request_id']; a0=A[rid0]
good={'request_id':rid0,'anchor_id':a0['expected_anchor_id'],'block_id':a0['expected_block_id'],'occurrence_id':a0['expected_occurrence'],'copied_label':a0['expected_copied_label'],'copied_period_evidence':list(a0['expected_period_evidence_array']),'abstain':False}
chk('grader accepts the true answer', grade_one(rid0,good,A)=='CORRECT')
chk('ATTACK: wrong anchor fails', grade_one(rid0,dict(good,anchor_id='SCR-99-anchor'),A)=='WRONG:anchor')
chk('ATTACK: vendor label fails', grade_one(rid0,dict(good,copied_label='Cargo Revenue'),A)=='WRONG:label')
chk('ATTACK: fabricated header fails', grade_one(rid0,dict(good,copied_period_evidence=['Twelve Months Ended']),A)=='WRONG:period_evidence')
chk('ATTACK: PARTIAL array fails', grade_one(rid0,dict(good,copied_period_evidence=good['copied_period_evidence'][1:]),A)=='WRONG:period_evidence')
chk('ATTACK: bare substring ("2") fails', grade_one(rid0,dict(good,copied_period_evidence=['2']),A)=='WRONG:period_evidence')
chk('ATTACK: MISSING evidence fails', grade_one(rid0,dict(good,copied_period_evidence=None),A)=='WRONG:period_evidence')
chk('ATTACK: DUPLICATE entries fail', grade_one(rid0,dict(good,copied_period_evidence=good['copied_period_evidence']+good['copied_period_evidence']),A)=='WRONG:period_evidence')
blocks={b['block_id']:b['text'] for f in calls for v in f['tables'].values() for b in v['blocks']}
chk('every expected label is an exact slice of its own block',
    all(A[r['request_id']]['expected_copied_label'] in blocks[A[r['request_id']]['expected_block_id']] for r in reqs))
req2tab={q['request_id']:c['table'] for f in calls for c in f['cases'] for q in c['requests']}
import re as _re
tabblocks={k:_re.sub(r'\u27e8[^\u27e9]*\u27e9','',' '.join(b['text'] for b in v['blocks'])) for f in calls for k,v in f['tables'].items()}   # markers are OUR annotation, not source — strip before verbatim-slice grading
chk('every evidence-array line is a verbatim slice of its own table (marker-stripped)',
    all(all(h in tabblocks[req2tab[r['request_id']]] for h in A[r['request_id']]['expected_period_evidence_array']) for r in reqs))
chk('prompt requests anchor_id and block_id and copied fields',
    all(all(t in f['prompt'] for t in ('anchor_id','block_id','copied_label','copied_period_evidence')) for f in calls))
chk('caps: <=8 cases and <=100000 bytes per call',
    all(len(f['cases'])<=8 for f in calls) and all(os.path.getsize(f'{W}/phase6_screen_call_{i+1}.json')<=100000 for i in range(3)))
chk('expected occurrences exist in inputs', all(a['expected_occurrence'] in raw for a in A.values()))
chk('expected blocks exist in inputs', all(a['expected_block_id'] in raw for a in A.values()))
from phase6_screen_grade import grade_batch
rids={r['request_id'] for r in reqs}
def mk(rid):
    a=A[rid]
    return {'request_id':rid,'anchor_id':a['expected_anchor_id'],'block_id':a['expected_block_id'],
            'occurrence_id':a['expected_occurrence'],'copied_label':a['expected_copied_label'],
            'copied_period_evidence':list(a['expected_period_evidence_array']),'abstain':False}
full=[mk(r) for r in sorted(rids)]
g=grade_batch(full, rids, A)
chk('BATCH: complete perfect batch grades clean, 93 CORRECT',
    g['clean'] and sum(1 for v in g['per_request'].values() if v=='CORRECT')==93)
chk('BATCH ATTACK: missing response detected',
    any(e.startswith('MISSING') for e in grade_batch(full[:-1], rids, A)['batch_errors']))
chk('BATCH ATTACK: duplicated response detected',
    any(e.startswith('DUPLICATE') for e in grade_batch(full+[full[0]], rids, A)['batch_errors']))
chk('BATCH ATTACK: extra unknown request detected',
    any(e.startswith('EXTRA') for e in grade_batch(full+[dict(full[0],request_id='SCR-99-q9')], rids, A)['batch_errors']))
chk('BATCH ATTACK: malformed row detected',
    any(e.startswith('MALFORMED') for e in grade_batch(full+['junk'], rids, A)['batch_errors']))
chk('BATCH ATTACK: non-list payload detected',
    grade_batch({'a':1}, rids, A)['batch_errors']==['MALFORMED:not-a-list'])
wrongb=[dict(r) for r in full]; wrongb[0]['copied_label']='Fabricated'
gw=grade_batch(wrongb, rids, A)
chk('RED->BATCH ATTACK: batch with one WRONG answer must NOT be clean',
    gw['clean'] is False and any(v.startswith('WRONG') for v in gw['per_request'].values()))
typed=[dict(r) for r in full]; typed[0]['occurrence_id']=42
xf=[dict(r) for r in full]; xf[0]['smuggled']='x'
chk('RED->ATTACK: EXTRA field must be malformed',
    any(e.startswith('MALFORMED') for e in grade_batch(xf, rids, A)['batch_errors']))
xa=[dict(r) for r in full]
xa[0]={'request_id':xa[0]['request_id'],'anchor_id':xa[0]['anchor_id'],'block_id':None,
       'occurrence_id':None,'copied_label':None,'copied_period_evidence':None,
       'abstain':True,'evidence':'smuggled'}
chk('RED->ATTACK: abstention with EXTRA evidence key must be malformed',
    any(e.startswith('MALFORMED') for e in grade_batch(xa, rids, A)['batch_errors']))
ab=[dict(r) for r in full]
ab[0].update({'abstain':True,'anchor_id':'SCR-99-anchor'})
chk('RED->ATTACK: abstain with WRONG anchor must NOT be clean',
    grade_batch(ab, rids, A)['clean'] is False)
ab2=[dict(r) for r in full]; ab2[0]['abstain']=True   # evidence fields left non-null
chk('RED->ATTACK: abstain with non-null evidence must NOT be clean',
    grade_batch(ab2, rids, A)['clean'] is False)
chk('BATCH ATTACK: wrong field TYPE detected as malformed',
    any(e.startswith('MALFORMED') for e in grade_batch(typed, rids, A)['batch_errors']))
out_bytes=len(json.dumps(full))
print(f'DERIVED output size len(json.dumps(full_batch)) = {out_bytes} bytes ~ {out_bytes//4} tokens/tier')
man=json.load(open(f'{W}/phase6_screen_manifest_v2.json'))
import os as _os
chk('MANIFEST-CONSISTENCY: byte figures match recomputation',
    man['model_input_bytes']==sum(_os.path.getsize(f'{W}/phase6_screen_call_{i+1}.json') for i in range(3))
    and str(out_bytes) in man['cost']['output_derivation'])
chk('MANIFEST-CONSISTENCY: counts match', man['cases']==19 and man['requests']==93
    and man['independence']['independent_tables']==8 and man['independence']['filings']==7)
sys.exit(0 if ok else 1)
