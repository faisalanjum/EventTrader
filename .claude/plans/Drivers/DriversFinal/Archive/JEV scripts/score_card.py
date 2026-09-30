import json,collections
items={x['id']:x for x in json.load(open('card_items.json'))}; R=json.load(open('results_card.json'))
TASK={'state':'L_state','unit_level':'L_lvl','unit_change':'L_chg','time_type':'L_tt'}
def ids(t): return [i for i in items if i in R and f"{t}#0" in R[i]]
print(f"{'task':12s} {'n':>4s} {'run1':>14s} {'run2':>14s}  {'agreed-label subset':>22s}  runs differ")
for t,f in TASK.items():
    I=ids(t); a=[i for i in I if items[i][f+'_agreed']]
    def acc(v,S): return sum(R[i][f"{t}#{v}"]['choice']==items[i][f] for i in S)
    d=[i for i in I if R[i][f"{t}#0"]['choice']!=R[i][f"{t}#1"]['choice']]
    print(f"{t:12s} {len(I):4d} {acc(0,I):4d} ({100*acc(0,I)/len(I):4.1f}%) {acc(1,I):4d} ({100*acc(1,I)/len(I):4.1f}%)  {acc(0,a):4d}/{len(a)} ({100*acc(0,a)/len(a):4.1f}%)   {len(d)}")
for t,f in TASK.items():
    I=ids(t); print(f"\n--- {t}: per label (run 1)")
    for lab in sorted({items[i][f] for i in I}):
        S=[i for i in I if items[i][f]==lab]; ok=sum(R[i][f"{t}#0"]['choice']==lab for i in S)
        wrong=collections.Counter(R[i][f"{t}#0"]['choice'] for i in S if R[i][f"{t}#0"]['choice']!=lab)
        print(f"   {lab:19s} {ok}/{len(S)}  picked instead: {dict(wrong)}")
# confidence separation (run 1)
for t,f in TASK.items():
    I=ids(t); w=[i for i in I if R[i][f"{t}#0"]['choice']!=items[i][f]]
    for c in (0.6,0.8,0.9):
        fl=[i for i in I if R[i][f"{t}#0"]['conf']<c]; print(f"{t:12s} conf<{c}: flags {len(fl)}/{len(I)} ({100*len(fl)/len(I):.0f}%), catches {sum(1 for i in fl if i in w)}/{len(w)} misses")
json.dump({t:[i for i in ids(t) if R[i][f"{t}#0"]['choice']!=items[i][TASK[t]]] for t in TASK},open('card_misses.json','w'))
