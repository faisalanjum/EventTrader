import json,sys,collections
sys.path.insert(0,'.')
import prompts_v3 as P
from concurrent.futures import ThreadPoolExecutor
fx=json.load(open('fixtures_v3.json'))+json.load(open('fixtures_h3.json'))+json.load(open('fixtures_h4.json'))
READ="Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them only to see what `quote` refers to."
QM2={"level_and_future":{"type":"noul",
 "instructions":{"question":"Does `quote` state something that already happened or is true now, and also state something about the future?","read":READ},
 "criteria":{"true":{"what":"One part of the quote reports something that already happened or is true now, and another part of the same quote looks ahead to the future."},
             "false":{"what":"The whole quote is about the past or present only, or the whole quote is about the future only."}}}}
def go(f): return f['id'],P.call(f['state'],QM2)
with ThreadPoolExecutor(8) as ex: R=list(ex.map(go,fx))
p={i:r['answers']['level_and_future']['noul'] for i,r in R if 'answers' in r}
flag=sorted([(v,i) for i,v in p.items() if v>=0.5],reverse=True)
print("flagged >=0.5:",len(flag),"of",len(p)); print("known mixed: DEV-028 =",round(p['DEV-028'],2),"| H1-013 =",round(p['H1-013'],2))
byid={f['id']:f for f in fx}
for v,i in flag[:14]: print(f"  {v:.2f} {i:8s} {byid[i]['state']['quote'][:120]!r}")
