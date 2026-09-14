#!/bin/bash
cd /home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2020_codex_check || exit 2
env A4_SOURCE_KEY_HARNESS=/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2008/harness_g1v3 PYTHONPATH=/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2009/owner:/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2006/harness_g1v3:/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2008/harness_g1v3:/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2008/harness /home/faisal/EventMarketDB/venv/bin/python3 -B - <<'PY'
from pathlib import Path
from collections import Counter
import json, copy
import a7_g2_key_reuse_2159 as S
G,B=S.G,S.B
launch_path=Path('../unit_2088_real_grading/LAUNCH.json')
assert G._sha_file(str(launch_path))=='ef8095d796b59b36e6fd8e4039a99f26ca24a012b9692560b0fb3060cf9bb327'
launch=G._read(str(launch_path))
B.bind_grading_scorer(str(Path('../unit_2008/harness_g1v3/scorers/score_exp5_current.py').resolve()),launch['owners']['grading_scorer'])
rp=Path('codex_g2reuse2159_a/G2_REUSE_AND_CORRECTION_2159.json')
assert G._sha_file(str(rp))=='75612fc52044e167a50b6aa6476fae3cfdb12d1dddd6c564c4381a6d325b7175'
r=G._read(str(rp)); s=S.derive('G2_REUSE_SELECTION_2159.json','9603626914cdddd79461ad8150d4a054dbde5776cb6af4f58057b21dd48228c2')
old=G._read('codex_keyreuse2123_a/KEY_GRADING_REUSE_BASE.json')
cp=Path('codex_g23partial2098_fit/G2/a7_g23_completion.json')
assert G._sha_file(str(cp))==old['g23_sources']['G2']['completion_sha256']
completion=G._read(str(cp))
established={qid:row['verdict'] for qid,row in completion['credited'].items()}
for row in completion['unresolved']:
    if row.get('established'):
        assert row['question_id'] not in established
        established[row['question_id']]=row['established']
seen=set(); kinds=Counter(); aspects=Counter(); fields=Counter()
for row in r['native_carry']:
    new,original=row['question_id'],row['original_question_id']; assert new not in seen; seen.add(new)
    assert s['carry'][new]==original
    assert row['group']==s['current_tasks'][new]['group']==s['original_tasks'][original]['group']
    assert row['current_pair']==s['current_tasks'][new]['pair'] and row['original_pair']==s['original_tasks'][original]['pair']
    assert row['established']==established.get(original)
    assert row['has_established_fields']==(original in established)
    d=row['established'] or {}; fields[len(d)]+=1
    for v in d.values():
        assert v is None or type(v) is bool
        aspects[str(v)]+=1
    kinds['with_false' if any(v is False for v in d.values()) else 'no_established_false']+=1
assert seen==set(s['carry'])
path=r['corrected_candidate']['path']; doc,_=G.load_frozen(str(Path(path).parent),r['corrected_candidate']['sha256'])
assert G._plain(doc['population'])==G._plain(s['correction_population'])
expected={B.meaning_question_id(*group.split('|',1),*pair) for group,pairs in s['correction_population'].items() for pair in pairs}
seen=set(); batches=Counter()
for batch in doc['batch_rows']:
    p=Path(path).parent/batch['prompt_path']; assert G._sha_file(str(p))==batch['prompt_sha256']
    text=p.read_text(); assert text.startswith(S.V.meaning_rules())
    body=json.loads(text.split('[EVENT]\n',1)[1]); ids=[]
    for event in body['events']:
        for q in event['questions']:
            qid=q['question_id']; assert qid in expected and qid not in seen
            seen.add(qid); ids.append(qid)
            old_task=s['current_tasks'][qid]
            assert event['event_context']==old_task['context']
            eq=copy.deepcopy(old_task['question']); eq['produced_record']=S.V.record_view(eq['produced_record'])
            assert q==eq
    assert ids==batch['question_ids']; batches[len(ids)]+=1
assert seen==expected and len(seen)==82
assert seen.isdisjoint(s['carry']) and seen|set(s['carry'])==set(s['current_tasks'])
print('VERIFIED exact original saved completion -> report: 228/228; no added, dropped or changed judgment fields')
print('Field counts',dict(fields),'aspects',dict(aspects),'row categories',dict(kinds))
print('Corrected full source/task input equality: 82/82; carry+correction 310/310')
print('Batch sizes',dict(batches),'candidate',r['corrected_candidate'])
print('No calls; no score claim. All pins unchanged.')
PY
