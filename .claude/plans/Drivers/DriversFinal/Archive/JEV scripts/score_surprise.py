import json,collections
items={x['id']:x for x in json.load(open('surprise_items.json'))}; R=json.load(open('results_surprise.json'))
sc=[i for i,x in items.items() if x['scored']]
sur=[i for i in sc if items[i]['key']=='surprise']; ctl=[i for i in sc if items[i]['key']!='surprise']
def right(i,v):
    a=R[i][v]['choice']; k=items[i]['key']
    return (a=='surprise') if k=='surprise' else (a!='surprise') if k=='not_surprise' else a==k
print("=== S1: fact type (V0 = round-1 prompt, V6 = recommended candidate)")
for v in ('V0#0','V6#0','V6#1'):
    rec=sum(R[i][v]['choice']=='surprise' for i in sur); fp=[i for i in ctl if R[i][v]['choice']=='surprise']
    exact=sum(right(i,v) for i in ctl)
    print(f"  {v}: surprise recall {rec}/{len(sur)} | controls: called surprise {len(fp)}/{len(ctl)}, exact type right {exact}/{len(ctl)}")
    print("     surprises typed as:",dict(collections.Counter(R[i][v]['choice'] for i in sur)),"| control false positives:",fp)
print("  V6 two identical runs differ on:",[i for i in items if R[i]['V6#0']['choice']!=R[i]['V6#1']['choice']])
print("\n=== S2: which comparison")
ok=[i for i in sc if R[i]['S2#0']['choice']==(items[i]['kind'])]
print(f"  all scored {len(ok)}/{len(sc)} | surprise claims {sum(R[i]['S2#0']['choice']==items[i]['kind'] for i in sur)}/{len(sur)} | controls (none) {sum(R[i]['S2#0']['choice']=='none' for i in ctl)}/{len(ctl)}")
for k in ('actual_vs_consensus','actual_vs_guidance','guidance_vs_consensus'):
    ids=[i for i in sur if items[i]['kind']==k]; print(f"    {k}: {sum(R[i]['S2#0']['choice']==k for i in ids)}/{len(ids)}")
print("\n=== S3: beat / in_line / missed / unknown (surprise claims with a state label)")
st=[i for i in sur if items[i]['state_key'] in ('beat','in_line','missed','unknown')]
print(f"  {sum(R[i]['S3#0']['choice']==items[i]['state_key'] for i in st)}/{len(st)}")
for k in ('beat','in_line','missed','unknown'):
    ids=[i for i in st if items[i]['state_key']==k]; print(f"    {k}: {sum(R[i]['S3#0']['choice']==k for i in ids)}/{len(ids)}  picked instead: {dict(collections.Counter(R[i]['S3#0']['choice'] for i in ids if R[i]['S3#0']['choice']!=k))}")
def line(i,tasks):
    x=items[i]; s=x['state']
    return f"[{i}] key={x['key']}/{x['kind'][:7]}/{x['state_key']} | "+" ".join(f"{t}={R[i][t]['choice'][:9]}({R[i][t]['conf']:.2f})" for t in tasks if t in R[i])+f" | driver={s['driver_name']!r} | {s['quote'][:120]!r}"
print("\n--- misses on S1 (V6)")
for i in sc:
    if not right(i,'V6#0'): print(line(i,('V0#0','V6#0','S2#0')))
print("\n--- misses on S2")
for i in sc:
    if R[i]['S2#0']['choice']!=items[i]['kind']: print(line(i,('V6#0','S2#0')))
print("\n--- misses on S3")
for i in st:
    if R[i]['S3#0']['choice']!=items[i]['state_key']: print(line(i,('S3#0',)))
print("\n--- unscored (rule gaps): what Jev said")
for i,x in items.items():
    if not x['scored']: print(line(i,('V6#0','S2#0'))+f" | {x['note'][:60]}")
print("\n--- S3 on the item with an 'unclear' state:",[(i,R[i]['S3#0']['choice'],round(R[i]['S3#0']['conf'],2)) for i in sur if items[i]['state_key']=='unclear'])
