import json
A=json.load(open('ablate_results.json')); keys=A['items']
R2=json.load(open('results_redo.json')); R3=json.load(open('results_v3run.json'))
def get(i,v):
    return (R2.get(i,{}).get(v) or R3.get(i,{}).get(v))
rows=[(i,get(i,'V2b#0')) for i in keys]
wrong=[(i,r['conf']) for i,r in rows if r['choice']!=keys[i]]
print("V2b errors and their confidence:",sorted((round(c,2),i) for i,c in wrong))
for t in (0.6,0.75,0.8,0.9):
    fl=[(i,r) for i,r in rows if r['conf']<t]; caught=sum(1 for i,r in fl if r['choice']!=keys[i])
    print(f"  conf<{t}: flags {len(fl)}/{len(rows)} ({100*len(fl)/len(rows):.0f}%), real errors caught {caught}/{len(wrong)}, correct answers flagged {len(fl)-caught}")
# the disputed / undecided items: how confident is V2b?
DIS=['H1-013a','H1-035','H2-024','H2-039','H2-043','H5G-56','H5M-016','H5M-026','H5M-037','H5G-43','H5G-59','H5G-60','H5G-70']
print("undecided items, V2b answer(conf):",[(i,get(i,'V2b#0')['choice'][:4],round(get(i,'V2b#0')['conf'],2)) for i in DIS if get(i,'V2b#0')])
