#!/bin/bash
cd /home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2020_codex_check || exit 2
env A4_SOURCE_KEY_HARNESS=/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2008/harness_g1v3 PYTHONPATH=/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2009/owner:/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2006/harness_g1v3:/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2008/harness_g1v3:/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2008/harness /home/faisal/EventMarketDB/venv/bin/python3 -B - <<'PY'
from pathlib import Path
from collections import Counter
import json, copy
import a7_g2_key_reuse_2159 as S
G,B,V=S.G,S.B,S.V
A7=Path.cwd().parent
launch=G._read(str(A7/'unit_2088_real_grading/LAUNCH.json'))
B.bind_grading_scorer(str(A7/'unit_2008/harness_g1v3/scorers/score_exp5_current.py'),launch['owners']['grading_scorer'])
bp=Path('codex_currentg232157_c/CURRENT_G23_PREPARATION.json')
assert G._sha_file(str(bp))=='d726f2464ead0b8100d1bdc58368a806268609c1dd7f35299c4bcc09ab9f144b'
base=G._read(str(bp)); handle=base['candidates']['G3']
prior,_=G.load_frozen(str(Path(handle['path']).parent),handle['sha256'])
current_dir=A7/'unit_2159_current_g3/core_g3prep2159_c/G3'
current,sha=G.load_frozen(str(current_dir),'088902eb930089df3f222bc6ac5aca2ae5c43715983ef17b0341883af10b8013')
rp=A7/'unit_2159_current_g3/core_g3verify2159_a/CURRENT_G3_VERIFICATION_2159.json'
assert G._sha_file(str(rp))=='005ec85ea9d1d672361dc7fa0e393fe43f6caf186c55d0f5f66d470f32d25cb7'
report=G._read(str(rp))
s=S.derive('G2_REUSE_SELECTION_2159.json','9603626914cdddd79461ad8150d4a054dbde5776cb6af4f58057b21dd48228c2')
assert G._plain(current['population'])==G._plain(prior['population'])
fullg2={}
for task in s['current_tasks'].values():
    fullg2.setdefault(task['group'],{})[task['pair'][1]]=V.record_view(task['question']['produced_record'])
g2base,_=G.load_frozen(str(Path(base['candidates']['G2']['path']).parent),base['candidates']['G2']['sha256'])
assert G._plain(current['matched_population'])==G._plain(g2base['population'])
expected={B.extras_question_id(*group.split('|',1),idx):(group,idx) for group,idxs in current['population'].items() for idx in idxs}
saved={}
contexts={}
for task in s['current_tasks'].values():
    sid=task['group'].split('|',1)[1]
    if sid in contexts: assert contexts[sid]==task['context']
    contexts[sid]=task['context']
def body(text):
    return json.loads(text[text.index('\n{\n')+1:])
for batch in prior['batch_rows']:
    path=Path(handle['path']).parent/batch['prompt_path']; assert G._sha_file(str(path))==batch['prompt_sha256']
    for event in body(path.read_text())['events']:
        for question in event['questions']:
            qid=question['question_id']; assert qid not in saved
            saved[qid]=(event,question)
assert set(saved)==set(expected)
rows={row['question_id']:row for row in report['rows']}; assert len(rows)==len(report['rows'])==len(expected)
seen=set(); empties=set(); sizes=[]; scripts=[]; batches=Counter()
for batch in current['batch_rows']:
    path=current_dir/batch['prompt_path']; text=path.read_text()
    assert G._sha_file(str(path))==batch['prompt_sha256']
    assert text.startswith(V.extras_rules())
    sizes.append(len(text.encode())); ids=[]
    for event in body(text)['events']:
        assert len(event['questions'])==1
        question=event['questions'][0]; qid=question['question_id']
        assert qid not in seen; seen.add(qid); ids.append(qid)
        group,idx=expected[qid]; pe,pq=saved[qid]
        want=copy.deepcopy(pq); want['produced_record']=V.record_view(want['produced_record'])
        assert question==want,(qid,'record')
        assert event['event_context']==contexts[group.split('|',1)[1]],(qid,'context')
        assert event['reference_cards']==pe['reference_cards'],(qid,'cards')
        indices=sorted(i for i in fullg2.get(group,{}) if i!=idx)
        wanted=[fullg2[group][i] for i in indices]
        shown=[r['produced_record'] for r in event['other_records']]
        assert shown==wanted,(qid,'comparators')
        if not wanted: empties.add(group)
        r=rows[qid]; assert (r['group'],r['asked_produced_idx'],r['batch_id'],r['comparator_idxs'])==(group,idx,batch['batch_id'],indices)
        for field,value in [('context',event['event_context']),('cards',event['reference_cards']),('record',question['produced_record'])]:
            assert r[field+'_sha256']==G._sha(G._plain(value)),(qid,field)
    assert ids==batch['question_ids']; batches[len(ids)]+=1
assert seen==set(expected)
batch_owner=A7/'unit_2008/harness_g1v3/scorers/grade_batch.js'
assert G._sha_file(str(batch_owner))==launch['owners']['grade_batch_owner']
# Resolve the proven private-namespace source to its identical durable backing for this read-only size check.
G.BATCH_OWNER=str(batch_owner)
for ordinal,call in enumerate(G.launchers(current['batch_rows'])):
    batch=next(b for b in current['batch_rows'] if b['batch_id']==call['batch_id'])
    call=dict(call,ordinal=ordinal,prompt=(current_dir/batch['prompt_path']).read_text())
    for attempt in range(1,G.MAX_ATTEMPTS+1):
        scripts.append(len(G._bound_script([call],{'candidate_sha256':sha},'0'*64,attempt).encode()))
assert max(scripts)<=report['script_byte_limit']
assert (len(seen),len(scripts),max(scripts),max(sizes))==(116,120,report['maximum_bound_script_bytes'],report['maximum_prompt_bytes'])
assert sorted(empties)==report['empty_comparator_groups']
assert report['key_identity']==base['key_identity']
assert not report['audit_problems'] and not report['oversize_variants'] and report['model_calls']==0
print(json.dumps({'verified_questions':len(seen),'current_G2_pairs':sum(map(len,g2base['population'].values())),'batches':dict(batches),'primary_calls':len(current['batch_rows'])*len(G.GRADER_LANES),'script_variants':len(scripts),'max_script_bytes':max(scripts),'empty_groups':sorted(empties),'candidate_sha256':sha},sort_keys=True))
print('All full questions, contexts, cards and exact matched-only comparisons match the previously verified current base; no calls and no score claim.')
PY

