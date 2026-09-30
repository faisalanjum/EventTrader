"""New slice keys from the proposed ruling 3 (JEV.md §6.4), frozen BEFORE the rescore run."""
import json,hashlib
items=json.load(open('items_more.json'))
REMAP={'mainline':'unknown','regionalcarrier':'unknown','mro business':'unknown','salestoairlinesegment':'customer'}
n=0
for x in items:
    if x['task']=='slice':
        v=x['state']['slice_value']; x['L_key_old']=x['L_key']
        if v in REMAP: x['L_key']=REMAP[v]; n+=1
json.dump(items,open('items_more2.json','w'),indent=1)
h=hashlib.sha256(json.dumps([[x['id'],x['L_key']] for x in items if x['task']=='slice']).encode()).hexdigest()[:16]
import collections
print("slice keys changed:",n,"| new slice key counts:",dict(collections.Counter(x['L_key'] for x in items if x['task']=='slice')),"| hash",h)
