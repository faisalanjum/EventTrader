import os,re,json,random
from neo4j import GraphDatabase
env=dict(l.strip().split("=",1) for l in open("/home/faisal/EventMarketDB/.env") if re.match(r"^NEO4J_(URI|USERNAME|PASSWORD)=",l))
drv=GraphDatabase.driver(env["NEO4J_URI"],auth=(env["NEO4J_USERNAME"],env["NEO4J_PASSWORD"].strip("'\"")))
random.seed(7)
with drv.session(default_access_mode="READ") as s:
    rows=s.run("""MATCH (g:GuidanceUpdate)-[:FROM_SOURCE]->(r:Report)
      WHERE g.source_type IN ['8k','10q','10k'] AND g.source_key IN ['EX-99.1','MD&A'] AND size(g.quote)>40
      RETURN g.id AS id,g.quote AS quote,g.source_type AS st,g.source_key AS sk,r.id AS rid,r.cik AS cik""").data()
    print("candidates",len(rows))
    by={}
    for r in rows: by.setdefault(r["rid"],[]).append(r)
    rids=list(by); random.shuffle(rids)
    out=[]
    for rid in rids:
        r=random.choice(by[rid]); q=re.sub(r"^\[[^\]]{1,10}\]\s*","",r["quote"]).strip()
        key=re.sub(r"\s+"," ",q)[:70]
        # find the content node containing the start of the quote (whitespace-insensitive is hard in cypher; try plain prefix)
        pref=q[:60]
        c=s.run("""MATCH (rp:Report {id:$rid})-[]->(c) WHERE (c:ExhibitContent OR c:ExtractedSectionContent) AND c.content CONTAINS $p
                   RETURN labels(c)[0] AS lab, coalesce(c.exhibit_number,c.section_name) AS part, c.content AS content LIMIT 1""",rid=rid,p=pref).single()
        if not c: continue
        text=c["content"]
        pat=r"\s+".join(re.escape(w) for w in q.split())
        m=re.search(pat,text)
        if not m: continue
        out.append(dict(rid=rid,cik=r["cik"],gid=r["id"],src_type=r["st"],part=c["part"],quote=text[m.start():m.end()],s=m.start(),e=m.end(),text=text))
        if len(out)>=75: break
json.dump(out,open("h1_raw.json","w"))
import collections
print("found",len(out),collections.Counter(o["src_type"] for o in out),"companies",len({o['cik'] for o in out}))
