import lxml.html
F='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/0000764478-25-000057.htm'
doc=lxml.html.parse(F).getroot()
t=[x for x in doc.xpath('//table') if 'Selected Online Revenue Data' in x.text_content()][0]
out=[]
for tr in t.xpath('.//tr'):
    cells, col = [], 0
    for c in tr.xpath('./td|./th'):
        w=int(c.get('colspan',1)); txt=' '.join(c.text_content().split())
        if txt: cells.append('c%02d: %s' % (col, txt))
        col+=w
    if cells: out.append('  '.join(cells))
open(SC:='/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/grid.txt','w').write('\n'.join(out))
print('\n'.join(out))
