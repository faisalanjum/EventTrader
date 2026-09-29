import re,json,random
from neo4j import GraphDatabase
env=dict(l.strip().split("=",1) for l in open("/home/faisal/EventMarketDB/.env") if re.match(r"^NEO4J_(URI|USERNAME|PASSWORD)=",l))
drv=GraphDatabase.driver(env["NEO4J_URI"],auth=(env["NEO4J_USERNAME"],env["NEO4J_PASSWORD"].strip("'\"")))
random.seed(2026); C=[]
def sents(t):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"(])",re.sub(r"[ \t]+"," ",t)) if 25<len(x.strip())<420]
with drv.session(default_access_mode="READ") as s:
    # ---- news headlines (text sample only; news is off in release 1, rule 9.5)
    pats={'news_beat':r"(?i).*\bQ[1-4]\b.*\bbeats?\b.*estimates?.*",'news_miss':r"(?i).*\bQ[1-4]\b.*\bmiss(es|ed)?\b.*estimates?.*",
          'news_inline':r"(?i).*\b(in line|in-line|matches|meets)\b.*estimates?.*",'news_sees':r"(?i).*\b(sees|guides|forecasts?)\b.*\b(estimates?|consensus)\b.*"}
    for k,p in pats.items():
        rows=s.run("MATCH (n:News) WHERE n.title =~ $p RETURN n.id AS id, n.title AS t, left(n.body,300) AS b LIMIT 600",p=p).data()
        random.shuffle(rows)
        for r in rows[:9]: C.append(dict(cat=k,src='news',id=r['id'],quote=r['t'],after=r['b'] or ''))
    # ---- prepared remarks: actual vs guidance / consensus sentences
    rows=s.run("MATCH (p:PreparedRemark) WHERE p.content =~ '(?is).*(exceed|above|ahead of|top end|high end|below|low end|within the range|in line with).{0,50}(guidance|outlook|guided|range).*' RETURN p.id AS id, p.content AS c LIMIT 800").data()
    random.shuffle(rows); n=0
    for r in rows:
        ss=sents(r['c']); hit=[x for x in ss if re.search(r"(?i)(exceed|above|ahead of|top end|high end|below|low end|within the (guidance )?range|in line with).{0,50}(guidance|outlook|guided|range)",x) and re.search(r"\d",x)]
        if hit: C.append(dict(cat='remark_guidance',src='transcript',id=r['id'],quote=random.choice(hit),after='')); n+=1
        if n>=14: break
    rows=s.run("MATCH (p:PreparedRemark) WHERE p.content =~ '(?is).*consensus.*' RETURN p.id AS id, p.content AS c LIMIT 289").data()
    random.shuffle(rows); n=0
    for r in rows:
        hit=[x for x in sents(r['c']) if 'consensus' in x.lower()]
        if hit: C.append(dict(cat='remark_consensus',src='transcript',id=r['id'],quote=random.choice(hit),after='')); n+=1
        if n>=8: break
    rows=s.run("MATCH (e:ExhibitContent) WHERE e.content =~ '(?is).*consensus.*' RETURN e.id AS id, e.content AS c LIMIT 255").data()
    random.shuffle(rows); n=0
    for r in rows:
        hit=[x for x in sents(r['c']) if 'consensus' in x.lower()]
        if hit: C.append(dict(cat='exhibit_consensus',src='8k',id=r['id'],quote=random.choice(hit),after='')); n+=1
        if n>=8: break
    # ---- near-miss negatives from the same transcripts
    rows=s.run("MATCH (p:PreparedRemark) WHERE p.content =~ '(?is).*(raising|raised|increasing|lowering|reducing|updating).{0,40}(full.year|fiscal.{0,8}\\\\d{4}).{0,40}(guidance|outlook).*' RETURN p.id AS id, p.content AS c LIMIT 500").data()
    random.shuffle(rows); n=0
    for r in rows:
        hit=[x for x in sents(r['c']) if re.search(r"(?i)(rais|increas|lower|reduc|updat)\w*.{0,50}(guidance|outlook)",x) and re.search(r"\d",x) and 'consensus' not in x.lower()]
        if hit: C.append(dict(cat='neg_guidance_move',src='transcript',id=r['id'],quote=random.choice(hit),after='')); n+=1
        if n>=6: break
    rows=s.run("MATCH (p:PreparedRemark) WHERE p.content =~ '(?is).*(increased|decreased|grew|declined|rose).{0,40}(year.over.year|compared to (the )?(prior|last) year|versus (the )?(prior|last) year).*' RETURN p.id AS id, p.content AS c LIMIT 500").data()
    random.shuffle(rows); n=0
    for r in rows:
        hit=[x for x in sents(r['c']) if re.search(r"(?i)(increased|decreased|grew|declined|rose).{0,40}(year.over.year|compared to (the )?(prior|last) year|versus (the )?(prior|last) year)",x) and re.search(r"\d",x) and not re.search(r"(?i)guidance|consensus|expect|estimate",x)]
        if hit: C.append(dict(cat='neg_vs_prior_year',src='transcript',id=r['id'],quote=random.choice(hit),after='')); n+=1
        if n>=6: break
    rows=s.run("MATCH (p:PreparedRemark) WHERE p.content =~ '(?is).*(exceeded|ahead of|better than|above) (our )?expectations.*' RETURN p.id AS id, p.content AS c LIMIT 400").data()
    random.shuffle(rows); n=0
    for r in rows:
        hit=[x for x in sents(r['c']) if re.search(r"(?i)(exceeded|ahead of|better than|above) (our )?expectations",x)]
        if hit: C.append(dict(cat='vague_expectations',src='transcript',id=r['id'],quote=random.choice(hit),after='')); n+=1
        if n>=5: break
json.dump(C,open('surprise_candidates.json','w'),indent=1)
import collections; print(len(C),collections.Counter(c['cat'] for c in C))
for i,c in enumerate(C): print(f"[{i:02d}] {c['cat']:17s} {c['quote'][:260]!r}")
