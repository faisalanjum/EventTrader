"""Horizon labels frozen BEFORE any Jev call, from rule 3.40 (short_term / medium_term / long_term / undefined = dateless horizons; a named year, quarter or half = stated_window) and by the explicit wording."""
import re,json,sys,hashlib
sys.path.insert(0,'.')
from jevlib import build_state,find_quote
from neo4j import GraphDatabase
C=json.load(open('horizon_candidates.json'))
LAB={'stated_window':[1,2,5,6,7,12,13,14],'short_term':[4,32,34,35,43,47,48,51,57,58],'medium_term':[49,59,61,62,63,64,65,66,67],
     'long_term':[16,20,21,23,25,40,44,45,39],'undefined':[15,17,18,19,22,27,38,42,46,50,52,53,55]}
env=dict(l.strip().split("=",1) for l in open("/home/faisal/EventMarketDB/.env") if re.match(r"^NEO4J_(URI|USERNAME|PASSWORD)=",l))
drv=GraphDatabase.driver(env["NEO4J_URI"],auth=(env["NEO4J_USERNAME"],env["NEO4J_PASSWORD"].strip("'\"")))
items=[]
with drv.session(default_access_mode="READ") as s:
    for lab,idxs in LAB.items():
        for ci in idxs:
            c=C[ci]; text=s.run("MATCH (p:PreparedRemark {id:$i}) RETURN p.content AS c",i=c['rid']).single()['c']
            m=find_quote(text,c['quote']); assert m,ci
            st=build_state(text,m[0],m[1],'10q','mdna','forward-looking statement')
            st['where_it_appears']="prepared remarks in an earnings call transcript"; st['driver_name']="forward-looking statement"
            assert isinstance(st,dict) and 'quote' in st
            items.append(dict(id=f"HZ{len(items):03d}",task='horizon',L_key=lab,state=st,cand=ci))
json.dump(items,open('items_horizon.json','w'),indent=1)
h=hashlib.sha256(json.dumps([[x['id'],x['L_key']] for x in items]).encode()).hexdigest()[:16]
import collections
print("labels frozen before any Jev call, hash",h,"| items",len(items),dict(collections.Counter(x['L_key'] for x in items)))
