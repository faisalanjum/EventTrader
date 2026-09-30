import json,sys,collections
sys.path.insert(0,'.')
import prompts_v3 as P
from more_prompts import HORIZON,HORIZON2,SLICE,SLICE2
from concurrent.futures import ThreadPoolExecutor
sl=[x for x in json.load(open('items_more2.json')) if x['task']=='slice']; hz=json.load(open('items_horizon.json'))
def one(a):
    x,q,r=a; assert isinstance(x['state'],dict) and 'quote' in x['state']; return x['id'],r,P.call(x['state'],q)
jobs=[(x,SLICE2,r) for x in sl for r in (0,1)]+[(x,HORIZON2,r) for x in hz for r in (0,1)]
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,jobs))
out=collections.defaultdict(dict); err=0
for i,r,res in R:
    if 'error' in res: err+=1; continue
    a=list(res['answers'].values())[0]; out[i][f"r{r}"]=dict(choice=a['choice'],conf=a['confidence'])
json.dump(out,open('results_rescore.json','w'),indent=1); print("calls",len(jobs),"errors",err)
old=json.load(open('results_more.json')); oldh=json.load(open('results_horizon.json'))
def block(name,I,new,old_res,key):
    ok=lambda R,r,S: sum(R[i][r]['choice']==I[i][key] for i in S)
    S=list(I)
    print(f"\n=== {name}: n={len(S)} | NEW prompt+keys: run1 {ok(new,'r0',S)} ({100*ok(new,'r0',S)/len(S):.1f}%) run2 {ok(new,'r1',S)} | old prompt against the same keys: {ok(old_res,'r0',S)} ({100*ok(old_res,'r0',S)/len(S):.1f}%) | runs differ {len([i for i in S if new[i]['r0']['choice']!=new[i]['r1']['choice']])}")
    for lab in sorted({I[i][key] for i in S}):
        T=[i for i in S if I[i][key]==lab]; w=collections.Counter(new[i]['r0']['choice'] for i in T if new[i]['r0']['choice']!=lab)
        print(f"   {lab:19s} {sum(new[i]['r0']['choice']==lab for i in T)}/{len(T)} picked instead: {dict(w)}")
    miss=[i for i in S if new[i]['r0']['choice']!=I[i][key]]
    print(f"   misses {len(miss)}; confidence<0.9 catches {sum(1 for i in miss if new[i]['r0']['conf']<0.9)}/{len(miss)}")
    return miss
Is={x['id']:x for x in sl}; Ih={x['id']:x for x in hz}
ms=block('slice kind',Is,out,old,'L_key'); mh=block('horizon (49 real sentences)',Ih,out,oldh,'L_key')
print("\nHORIZON misses:")
for i in mh: print(f"[{i}] label={Ih[i]['L_key']} jev={out[i]['r0']['choice']}({out[i]['r0']['conf']:.2f}) | {Ih[i]['state']['quote'][:170]!r}")
print("\nSLICE misses:")
for i in ms:
    s=Is[i]['state']; print(f"[{i}] key={Is[i]['L_key']} (old {Is[i]['L_key_old']}) jev={out[i]['r0']['choice']}({out[i]['r0']['conf']:.2f}) | slice={s['slice_value']!r} | {s['quote'][:110]!r}")
