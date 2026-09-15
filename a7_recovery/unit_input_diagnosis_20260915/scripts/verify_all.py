import json, glob, os, re, lxml.html
from collections import Counter
SC='/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad'
CACHE='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/%s.htm'
def datajson(p):
    i=p.index('"menu"'); j=p.rindex('{',0,i+1); return json.loads(p[j:])

print('PASS 1+2 - assembled prompts parse, and every quote still resolves')
ok1=ok2=n=0
for tag, pref in (('BBY','0000764478'), ('AAL','0000006201')):
    head=open('%s/HEADADD_%s.txt'%(SC,tag)).read()
    for f in sorted(glob.glob('%s/ITEM_*.txt'%SC)):
        pid=os.path.basename(f)[5:-4]
        if pref not in pid: continue
        n+=1
        try:
            d=datajson(head+open(f).read()); ok1+=1
            blob=' '.join(p['content'] for p in d['event']['text_parts'])
            if d['item']['quote'] in blob: ok2+=1
            else: print('   QUOTE LOST:', pid)
        except Exception as e: print('   JSON FAIL:', pid, str(e)[:60])
print('   assembled prompts valid JSON : %d/%d' % (ok1,n))
print('   quotes resolving in source   : %d/%d' % (ok2,n))

print()
print('PASS 3 - grid values equal their own table, and no original number lost')
for tag, acc in (('BBY','0000764478-25-000057'), ('AAL','0000006201-26-000032')):
    old=open('%s/HEAD_%s.txt'%(SC,tag)).read(); new=open('%s/HEADADD_%s.txt'%(SC,tag)).read()
    d_old=Counter(re.findall(r'\d[\d,\.]*', old))
    stripped=re.sub(r' \\n\[GRID\]\\n.*?\\n\[/GRID\]\\n','',new)
    print('   %s numbers lost outside grids : %d' % (tag, sum((d_old-Counter(re.findall(r'\d[\d,\.]*',stripped))).values())))
    # every grid must reproduce its table's cell text exactly
    doc=lxml.html.parse(CACHE%acc).getroot()
    tabs={}
    for t in doc.xpath('//table'):
        rows=[]
        for tr in t.xpath('.//tr'):
            cs,col=[],0
            for c in tr.xpath('./td|./th'):
                w=int(c.get('colspan',1)); x=' '.join(c.text_content().replace('\xa0',' ').split())
                if x: cs.append('c%02d: %s'%(col,x))
                col+=w
            if cs: rows.append('  '.join(cs))
        if rows: tabs['\\n'.join(rows).replace('"','\\"')]=1
    grids=re.findall(r'\\n\[GRID\]\\n(.*?)\\n\[/GRID\]\\n', new)
    print('   %s grids found=%d   all match a real table exactly: %s'
          % (tag, len(grids), all(g in tabs for g in grids)))
