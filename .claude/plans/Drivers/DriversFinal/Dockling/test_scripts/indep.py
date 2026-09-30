# Independent check: Item IDs from the RAW filing HTML (no Docling), vs Item IDs Docling found as headings.
import json, re
from bs4 import BeautifulSoup
from sec_headings import item_ids
R=[json.loads(l) for l in open('scale/results.jsonl')]
sel={s['acc']:s for s in json.load(open('docling_scale_selection.json'))}
for r in R:
    if r['kind']=='8-K EX-99.1': continue
    html=open(sel[r['acc']]['path'],encoding='utf-8',errors='ignore').read()
    txt=BeautifulSoup(html,'lxml').get_text('\n')
    lines=[re.sub(r'\s+',' ',l).strip() for l in txt.split('\n')]
    raw=set(item_ids([l for l in lines if 0<len(l)<200]))
    found=set(r['items_as_headings'])
    print(f"{r['kind']} {r['ticker']}: raw-HTML items {len(raw)} | Docling heading items {len(found)} | missing in Docling {sorted(raw-found)} | extra in Docling {sorted(found-raw)}")
