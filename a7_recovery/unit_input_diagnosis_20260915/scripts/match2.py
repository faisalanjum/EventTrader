import re, lxml.html
CACHE='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/%s.htm'
def squash(s): return re.sub(r'\s+','', s.replace('\xa0',' '))
for tag, acc in (('BBY','0000764478-25-000057'), ('AAL','0000006201-26-000032')):
    head=open('/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/HEAD_%s.txt'%tag).read()
    sq=squash(head)
    doc=lxml.html.parse(CACHE%acc).getroot()
    once=multi=absent=tiny=0; absent_ex=[]
    for t in doc.xpath('//table'):
        txt=squash(t.text_content())
        if len(txt)<40: tiny+=1; continue
        n=sq.count(txt)
        if n==1: once+=1
        elif n>1: multi+=1
        else:
            absent+=1
            if len(absent_ex)<2: absent_ex.append(txt[:90])
    print('%s  matched_once=%-3d multi=%-2d NOT_FOUND=%-3d tiny=%d' % (tag, once, multi, absent, tiny))
    for e in absent_ex: print('     miss:', e)
