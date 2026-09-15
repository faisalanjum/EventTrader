"""Does the text PRODUCTION actually stores lose table row boundaries?
Compares the HTML grid (truth) against ExtractedSectionContent.content (served)."""
import os, random, lxml.html
from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv('/home/faisal/EventMarketDB/.env')
drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                           auth=(os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD']))

D='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache'
files=sorted(os.listdir(D))
by_prefix={}
for f in files: by_prefix.setdefault(f.split('-')[0], []).append(f)
random.seed(11)
sample=[random.choice(v) for v in by_prefix.values()]
random.shuffle(sample)

def has_digit(s): return any(c.isdigit() for c in s)

checked=lost=kept=0; used=0; missing=0
with drv.session() as s:
    for fn in sample:
        if used>=15: break
        acc=fn[:-4]
        rec=s.run("MATCH (e:ExtractedSectionContent) WHERE e.id CONTAINS $a "
                  "RETURN e.content AS c ORDER BY size(e.content) DESC LIMIT 1",
                  a=acc).single()
        if not rec or not rec['c']: missing+=1; continue
        served=rec['c']
        try: doc=lxml.html.parse(os.path.join(D,fn)).getroot()
        except Exception: continue
        f_checked=f_lost=0
        for t in doc.xpath('//table'):
            for tr in t.xpath('.//tr'):
                cs=[' '.join(c.text_content().split()) for c in tr.xpath('./td|./th')]
                cs=[c for c in cs if c]
                if len(cs)<2 or has_digit(cs[0]) or not any(has_digit(c) for c in cs[1:]): continue
                lab=cs[0]
                i=served.find(lab)
                if i<=0: continue
                f_checked+=1
                if '\n' not in served[max(0,i-3):i]: f_lost+=1
        if f_checked<5: continue
        used+=1; checked+=f_checked; lost+=f_lost
        print('%s  rows=%-4d boundary lost=%-4d (%5.1f%%)' % (acc, f_checked, f_lost, 100*f_lost/f_checked))
print()
print('filings measured : %d   (no section text in DB: %d)' % (used, missing))
print('row labels       : %d' % checked)
print('boundary LOST    : %d  (%.1f%%)' % (lost, 100*lost/checked if checked else 0))
drv.close()
