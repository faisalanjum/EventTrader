"""Freeze labels for the surprise test BEFORE any Jev call. Labels follow DRIVER_RULES_Categorized.md: 1.5 (surprise = company value, actual or company guide, vs an outside expectation, or an actual vs the
company's own earlier guide; NOT vs a prior-period actual; NOT a new guide vs the company's own earlier guide), 4.1-4.3 (kinds), 4.10-4.13 (states), 3.52 (baselines)."""
import re,json,sys,hashlib
sys.path.insert(0,'.')
from jevlib import build_state,find_quote
from neo4j import GraphDatabase
C=json.load(open('surprise_candidates.json'))
env=dict(l.strip().split("=",1) for l in open("/home/faisal/EventMarketDB/.env") if re.match(r"^NEO4J_(URI|USERNAME|PASSWORD)=",l))
drv=GraphDatabase.driver(env["NEO4J_URI"],auth=(env["NEO4J_USERNAME"],env["NEO4J_PASSWORD"].strip("'\"")))
S,G,M,A,NS='surprise','guidance','metric','action_event','not_surprise'
AC,AG,GC='actual_vs_consensus','actual_vs_guidance','guidance_vs_consensus'
# (candidate index, span (None = whole quote), driver name, type key, kind, state, note)
L=[
 (0,"Q4 EPS $0.97 Misses $1.80 Estimate","earnings per share",S,AC,'missed',''),(0,"Sales $4.68B Beat $4.56B Estimate","revenue",S,AC,'beat',''),
 (3,"Q4 EPS $1.83 Beats $1.76 Estimate","earnings per share",S,AC,'beat',''),(3,"Sales $2.33B Miss $2.44B Estimate","revenue",S,AC,'missed',''),
 (8,"Q4 EPS $(2.65), Inline","earnings per share",S,AC,'in_line',''),(8,"Sales $38.78M Beat $34.43M Estimate","revenue",S,AC,'beat',''),
 (16,None,"earnings per share",S,AC,'missed',''),
 (18,"Q2 Adj $0.23 In Line","adjusted earnings per share",S,AC,'in_line',''),(18,"Sales $576.20M Miss $580.72M Estimate","revenue",S,AC,'missed',''),
 (24,"Sales $20.762B In-line With Estimate","revenue",S,AC,'in_line',''),
 (11,"Q4 EPS $(2.46) Misses $(2.39) Estimate","earnings per share",S,AC,'missed',''),
 (2,None,"earnings per share",S,AC,'beat','EPS and sales both beat'),
 (29,None,"sales",S,GC,'missed','range below consensus'),
 (32,None,"adjusted earnings per share",S,GC,'missed','range below estimate'),
 (31,None,"revenue",S,GC,'in_line','range contains the estimate (rule 4.10)'),
 (27,"Sees FY25 Adjusted EPS Of $4.10-$4.30 Vs. $4.30 Estimate","adjusted earnings per share",S,GC,'in_line','estimate on the edge of the range (rule 4.10)'),
 (34,None,"adjusted earnings per share",S,GC,'missed','both guided ranges below estimate'),
 (33,"Guides Q2 And FY24 Revenue Below Estimates","revenue",S,GC,'missed',''),
 (23,None,"earnings per share and sales",S,GC,'in_line','affirmed guidance in line with estimates'),
 (19,"Reaffirms Adj. EPS Outlook Of At Least $8.15 In line With $8.15 Estimate","adjusted earnings per share",S,GC,'in_line',''),
 (20,"EPS Beat","earnings per share",S,AC,'beat',''),(20,"Revenues In-Line","revenue",S,AC,'in_line',''),(20,"Q4 Guidance Below Estimates","guidance",S,GC,'missed',''),
 (26,"Revenues Miss","revenue",S,AC,'missed',''),(26,"Q1 Guidance In Line With Estimates","guidance",S,GC,'in_line',''),
 (22,"Reports Q2 Earnings In Line With Estimates","earnings",S,AC,'in_line',''),
 (37,None,"earnings per share",S,AG,'beat',''),(39,None,"cash same-store net operating income growth",S,AG,'beat',''),
 (42,None,"non-GAAP SG&A expense",S,AG,'unknown','outside the range, no good/bad words, expense has a common opposite story (rule 4.12)'),
 (43,None,"revenue growth",S,AG,'beat',''),(44,None,"adjusted EBITDA margin",S,AG,'in_line','inside the target range, no good/bad words; target wording = previous_guidance (rule 3.52)'),
 (45,None,"revenue, margin and earnings per share",S,AG,'beat',''),(46,None,"effective tax rate",S,AG,'unclear','"This benefit" may frame it as good; state unclear'),
 (47,None,"domestic churn",S,AG,'in_line','in line with prior projections'),(36,None,"adjusted EBITDA margin",S,AG,'beat','company target range = previous_guidance (rule 3.52)'),
 (78,None,"oil differential",S,AG,'beat','"better than our expectations", below the low end of guidance'),
 (48,"Adjusted EBITDA exceeded the high end of guidance","adjusted EBITDA",S,AG,'beat',''),(49,"well below our guidance range","operating expenses",S,AG,'beat','"tightly manage" frames it as good'),
 (51,None,"adjusted earnings per share",S,AC,'beat','also above internal expectations; consensus is explicit'),(53,None,"revenue, operating profit, adjusted EBITDA and adjusted earnings per share",S,AC,'beat',''),
 (54,None,"quarterly results",S,AC,'beat','ungrounded generic beat (rule 4.15)'),(57,None,"adjusted earnings per share",S,AC,'beat',''),
 # ---- controls: near misses that must NOT be typed as surprise
 (38,None,"full-year revenue guidance",G,'none','','new guide vs own old guide = guidance movement (4.1)'),(40,None,"capital additions outlook",G,'none','','reaffirmed outlook; compared with D&A estimates of its own'),
 (67,None,"adjusted EBITDA guidance",G,'none','','raised guidance'),(69,None,"adjusted EBITDA guidance",G,'none','','vs previous guidance (movement)'),
 (70,None,"adjusted operating income margin guidance",G,'none','','vs prior guide (movement)'),(71,None,"earnings per share guidance",G,'none','','vs August guidance (movement)'),
 (27,"Sees Capital Expenditures Of Approximately $800M","capital expenditures",G,'none','','forecast with no comparison'),
 (19,"Now Sees A Low-Single-Digit Increase In Organic Revenue (Prior ~4% Organic)","organic revenue growth",G,'none','','new guide vs own prior guide'),
 (22,"Raises Guidance As AI Demand Soars","guidance",G,'none','','raised guidance, no expectation compared'),
 (72,None,"sales",M,'none','','vs prior year (metric change, 4.1)'),(73,None,"organic gross profit",M,'none','','vs prior year'),(75,None,"customers",M,'none','','vs prior year'),
 (76,None,"revenue",M,'none','','vs prior year'),(77,None,"adjusted gross margin",M,'none','','vs prior year'),
 (48,"which is $16.7 million better than Q3 of 2022","adjusted EBITDA",M,'none','','vs prior year quarter'),
 (49,"operating expenses, which were down 19% year-over-year to $555 million","operating expenses",M,'none','','vs prior year'),
 (22,"Announces $1 Billion Buyback","share repurchase",A,'none','',''),
 (55,None,"recession probability",NS,'none','','the word consensus, not a company value vs expectation'),(56,None,"policy support",NS,'none','','the word consensus in another sense'),
 (58,None,"joint steering committee decisions",NS,'none','','contract clause'),(61,None,"foreign exchange translation",NS,'none','','consensus rates used as an input to a forecast'),
 (62,None,"fuel price estimate",NS,'none','','method input'),(63,None,"consensus analyst forecasts",NS,'none','','footnote naming a data source'),
 # ---- unscored: rules do not settle, or several facts in one headline (kept for information)
 (21,None,"bookings",'unclear','','','"estimates" not clearly analysts'),(28,None,"adjusted earnings per share",'unclear','','','new guide vs own old guide AND vs consensus in one headline (4.16)'),
 (30,None,"net sales",'unclear','','','same mixed pattern (4.16)'),(35,None,"revenue",'unclear','','','vs prior guidance AND vs consensus (4.16)'),
 (50,None,"earnings per share",'unclear','','','which value is above consensus?'),(52,None,"global growth",'unclear','','','company macro view vs consensus, not its own metric'),
 (79,None,"brand pharmaceutical pricing",'unclear','','','"our expectations": internal, neither consensus nor guidance (3.52 gap)'),(80,None,"net interest revenue",'unclear','','','"our expectations" (3.52 gap)'),
 (81,None,"new store productivity",'unclear','','','"our expectations" (3.52 gap)'),(82,None,"advertising revenues",'unclear','','','"our expectations" (3.52 gap)'),
]
def get_text(c,s):
    if c['src']=='transcript': return s.run("MATCH (p:PreparedRemark {id:$i}) RETURN p.content AS c",i=c['id']).single()['c']
    if c['src']=='8k': return s.run("MATCH (e:ExhibitContent {id:$i}) RETURN e.content AS c",i=c['id']).single()['c']
items=[]; bodies={}
with drv.session(default_access_mode="READ") as s:
    for n,(ci,span,name,key,kind,state,note) in enumerate(L):
        c=C[ci]; q=c['quote']; sp=span or q
        assert sp in q,(ci,sp)
        if c['src']=='news':
            i0=q.index(sp); before=q[:i0].strip(); after=(q[i0+len(sp):].strip()+" "+(c['after'] or '')[:200].replace("\n"," ")).strip()
            st=dict(where_it_appears="news headline",driver_name=name,text_before_quote=before,quote=sp,text_after_quote=after)
        else:
            text=bodies.get(c['id']) or get_text(c,s); bodies[c['id']]=text
            m=find_quote(text,q); assert m,(ci,'quote not in source text')
            sub=re.search(r"\s+".join(re.escape(w) for w in sp.split()),text[m[0]:m[1]]); assert sub,(ci,sp)
            a,b=m[0]+sub.start(),m[0]+sub.end()
            st=build_state(text,a,b,'10q','mdna',name.replace(' ','_'))
            st['where_it_appears']="prepared remarks in an earnings call transcript" if c['src']=='transcript' else "exhibit to a current report (8-K)"
            st['driver_name']=name
        items.append(dict(id=f"S{n:03d}",cand=ci,key=key,kind=kind,state_key=state,note=note,scored=(key!='unclear'),state=st))
frozen=json.dumps([{k:v for k,v in x.items() if k!='state'} for x in items],sort_keys=True)
h=hashlib.sha256(frozen.encode()).hexdigest()[:16]
json.dump(items,open('surprise_items.json','w'),indent=1)
import collections
print("labels frozen BEFORE any Jev call, hash",h)
print("items",len(items),"| scored",sum(x['scored'] for x in items),collections.Counter(x['key'] for x in items))
print("surprise kinds:",collections.Counter(x['kind'] for x in items if x['key']==S),"| states:",collections.Counter(x['state_key'] for x in items if x['key']==S))
