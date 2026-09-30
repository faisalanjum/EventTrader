import json,re,sys,copy
sys.path.insert(0,'.')
from jevlib import *
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"
fx=json.load(open('fixtures_v3.json'))+json.load(open('fixtures_h3.json'))+json.load(open('fixtures_h4.json'))
byid={f['id']:f for f in fx}
# ---- rulings (proposed interpretations from the pasted advice), one key per item, grouped
G={
 1:("cash-flow totals -> metric",'metric',"H4-024 H4-025 H4-027 H4-038 H2-025 H2-038"),
 2:("storm incidents -> action_event",'action_event',"DEV-042 DEV-052 DEV-061"),
 3:("forecast assumptions -> guidance",'guidance',"DEV-092 DEV-109 DEV-097 DEV-108 DEV-085"),
 '4a':("announced/implemented action -> action_event",'action_event',"DEV-078 DEV-054"),
 '4b':("expected volume -> guidance",'guidance',"H2-059"),
 5:("dividend per share -> metric",'metric',"H1-001 H1-035"),
 7:("standing arrangement in use -> metric",'metric',"H1-028 H1-029 H2-039 H2-043"),
 8:("pay levels / reserve adjustments / revenue performance -> metric",'metric',"H2-024 H2-027 H2-051"),
 'x':("the one clear error last round (dividend program, per-share driver)",'metric',"DEV-039"),
}
newkey={};grp={}
for g,(desc,k,ids) in G.items():
    for i in ids.split(): newkey[i]=k; grp[i]=str(g)
# ---- group 6: split mixed quotes into separate claims (exact sub-spans of the original quote)
def locate(f):
    if f['set']=='H1':
        o=json.load(open('h1_raw.json'))[int(f['id'].split('-')[1])]; return o['text'],o['s'],o['e'],o['src_type'],o['part']
    d=json.load(open(f"{EV}/{f['src']}.json"))
    for p in d['text_parts']:
        m=find_quote(p['content'],f['state']['quote'])
        if m: return p['content'],m[0],m[1],d['source_type'],p['part']
    raise SystemExit("not found "+f['id'])
SPLITS={
 'DEV-028':[("As of December 31, 2025, we had approximately $2.4 billion of U.S. federal pre-tax net operating loss carryforwards",'metric'),
            ("which we are expecting to utilize during 2026",'guidance')],
 'H1-013':[("We opened 9 new stores and closed one store during the first quarter of fiscal 2023",'metric'),
           ("we expect to open approximately 45 stores during fiscal 2023",'guidance')],
}
items=[]
for f in fx:
    i=f['id']
    if i in SPLITS:
        text,s,e,st,part=locate(f); name=f['state']['driver_name']
        for n,(sub,k) in enumerate(SPLITS[i]):
            m=re.search(r"\s+".join(re.escape(w) for w in sub.split()),text[s:e]); assert m,(i,sub)
            a,b=s+m.start(),s+m.end()
            items.append(dict(id=f"{i}{'ab'[n]}",set=f['set'],key=k,group='6',state=build_state(text,a,b,st,part,name.replace(' ','_')),orig=i))
        continue
    key=newkey.get(i, f['key'])
    items.append(dict(id=i,set=f['set'],key=key,group=grp.get(i,''),state=f['state'],orig=i))
# any item still 'unclear'?
print("items",len(items),"still unclear:",[x['id'] for x in items if x['key']=='unclear'])
redo=[x for x in items if x['group']]; print("redo set:",len(redo),{k:sum(1 for x in redo if x['key']==k) for k in ('metric','action_event','guidance')})
json.dump(items,open('redo_items.json','w'),indent=1)
# ---- review table: every redo claim with its driver, key and exact claim, to check the rulings against the words
for x in redo:
    s=x['state']; print(f"[{x['id']}] g{x['group']} key={x['key']} | driver={s['driver_name']} | QUOTE: {s['quote'][:210]!r}")
