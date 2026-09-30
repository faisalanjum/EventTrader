import re,json,random
from neo4j import GraphDatabase
env=dict(l.strip().split("=",1) for l in open("/home/faisal/EventMarketDB/.env") if re.match(r"^NEO4J_(URI|USERNAME|PASSWORD)=",l))
drv=GraphDatabase.driver(env["NEO4J_URI"],auth=(env["NEO4J_USERNAME"],env["NEO4J_PASSWORD"].strip("'\"")))
random.seed(9)
CL={'short':r"\b(near[- ]term|short[- ]term|in the coming (weeks|months|quarters)|over the next (few|several) (weeks|months))\b",
    'medium':r"\b(medium[- ]term|mid[- ]term|over the next (few|several|two to three|three to five) years|next several years)\b",
    'long':r"\b(long[- ]term|long[- ]range|long run|over the long haul|longer term)\b",
    'undefined':r"\b(going forward|over time|from here|in the future|eventually|down the road)\b",
    'stated':r"\b(fiscal (year )?20\d\d|full[- ]year 20\d\d|(first|second|third|fourth) quarter|by (the end of )?20\d\d|in 20\d\d|for 20\d\d|\bQ[1-4]\b)"}
FWD=r"(?i)\b(expect|target|goal|plan|aim|anticipate|will|forecast|outlook|guidance|should|intend|committed|see us)\b"
def sents(t): return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"(])",re.sub(r"[ \t]+"," ",t)) if 40<len(x.strip())<380]
out=[]
with drv.session(default_access_mode="READ") as s:
    rows=s.run("MATCH (p:PreparedRemark) WHERE p.content =~ '(?is).*(near.term|short.term|medium.term|mid.term|long.term|long.range|going forward|over time|next (few|several) years|fiscal 20).*' RETURN p.id AS id, p.content AS c LIMIT 1500").data()
    random.shuffle(rows)
    cnt={k:0 for k in CL}
    for r in rows:
        for x in sents(r['c']):
            if not re.search(FWD,x): continue
            hit=[k for k,p in CL.items() if re.search(p,x,re.I)]
            if len(hit)==1 and cnt[hit[0]]<14 and re.search(r"\d|margin|growth|revenue|earnings|capital|cash|EPS|store|cost",x,re.I):
                out.append(dict(cls=hit[0],rid=r['id'],quote=x)); cnt[hit[0]]+=1
        if all(v>=14 for v in cnt.values()): break
json.dump(out,open('horizon_candidates.json','w'),indent=1)
print(len(out),{k:sum(1 for o in out if o['cls']==k) for k in CL})
for i,o in enumerate(out): print(f"[{i:02d}] {o['cls']:9s} {o['quote'][:230]!r}")
