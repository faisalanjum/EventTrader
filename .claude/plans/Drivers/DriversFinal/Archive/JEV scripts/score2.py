import json,collections,sys
sys.path.insert(0,'.')
items={x['id']:x for x in json.load(open('redo_items.json'))}; R=json.load(open('results_redo.json'))
DISPUTED={'H1-013a','H1-035','H2-024','H2-039','H2-043'}   # advice pulls two ways / key only inferred -> back to owner
ids=[i for i in items if i not in DISPUTED]
print(f"decided items {len(ids)} (5 disputed set aside)")
for v in ('V0','V1','V2a','V2b'):
    for rep in (0,1):
        if f'{v}#{rep}' not in R[ids[0]]: continue
        wrong=[i for i in ids if R[i][f'{v}#{rep}']['choice']!=items[i]['key']]
        print(f"  {v}#{rep}: {len(ids)-len(wrong)}/{len(ids)} = {100*(len(ids)-len(wrong))/len(ids):.1f}%   wrong: {wrong}")
# confidence of the wrong answers (V2b#0)
for v in ('V2b#0',):
    w=sorted(round(R[i][v]['conf'],2) for i in ids if R[i][v]['choice']!=items[i]['key']); print("V2b wrong-answer confidences:",w)
