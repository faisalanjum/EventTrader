import json,re,sys,collections
sys.path.insert(0,'.')
from jevlib import *
old=json.load(open('redo_items.json')); h5=json.load(open('fixtures_h5.json')); h1=json.load(open('h1_raw.json'))
# ---- second reviewer's rulings (proposed interpretations), applied as keys
REKEY={
 'H2-024':('metric','pay change is a metric; the effective date does not change that'),
 'H5M-037':('metric','pay change is a metric'),
 'H1-028':('metric','rate used in the current non-GAAP method'),'H1-029':('metric','rate used in the current non-GAAP method'),'H5G-56':('metric','rate used in the current non-GAAP method'),
 'H2-039':('metric','agreement remaining in force'),
 'H2-043':('action_event','work being performed (INFERRED: reviewer did not name this quote)'),
 'H1-035':('metric','per-share amount under a per-share driver'),'H5G-43':('metric','per-share amount under a per-share driver'),'H5G-59':('metric','per-share amount under a per-share driver'),
 'H5M-016':('action_event','milestone: aircraft entering service'),'H5M-026':('action_event','milestone: aircraft entering service'),
 'H1-013a':('metric','count opened during the quarter'),
 'H5M-004':('action_event','scheduled payment (round-2 ruling 4)'),'H5M-027':('action_event','scheduled payment (round-2 ruling 4)'),
}
items=[]
for x in old:
    y=dict(x);
    if y['id'] in REKEY: y['key'],y['note']=REKEY[y['id']]
    items.append(y)
for x in h5:
    y=dict(x)
    if y['id'] in REKEY: y['key'],y['note']=REKEY[y['id']]
    if y['id'] in ('H5G-60','H5G-70'): continue                      # replaced by split claims below
    items.append(y)
# ---- split the two remaining mixed H5G quotes into exact sub-spans
SPL={60:[("We completed Canada's implementation of Network 2.0 in the fourth quarter of 2025",'action_event','completed implementation'),
         ("expect to complete the U.S. implementation by the end of calendar 2027",'undecided','expected completion of an implementation: guidance or action? not covered by the reviewer')],
     70:[("We became subject to the EU ETS on January 1, 2024, which includes a three-year phase-in period.",'undecided','became subject: event or standing condition? not covered by the reviewer'),
         ("The impact in 2024 will be approximately $50 million.",'guidance','expected impact')]}
for idx,parts in SPL.items():
    o=h1[idx]; name=o['gid'].split(':')[2]
    for n,(sub,k,note) in enumerate(parts):
        m=re.search(r"\s+".join(re.escape(w) for w in sub.split()),o['text'][o['s']:o['e']]); assert m,(idx,sub)
        a,b=o['s']+m.start(),o['s']+m.end()
        items.append(dict(id=f"H5G-{idx}{'ab'[n]}",set='H5G',key=k,note=note,state=build_state(o['text'],a,b,o['src_type'],o['part'],name)))
# 'unclear' leftovers?
left=[x['id'] for x in items if x['key']=='unclear']
print("items",len(items),"| still 'unclear':",left)
print(collections.Counter(x['key'] for x in items))
json.dump(items,open('items_final.json','w'),indent=1)
print("newly ruled:",[x['id'] for x in items if x['id'] in REKEY or x['id'].startswith(('H5G-60','H5G-70'))])
