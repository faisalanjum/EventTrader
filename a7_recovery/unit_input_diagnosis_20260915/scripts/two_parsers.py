"""Independent verification: docling's cell model vs my lxml parser.
Different libraries, different code paths. Agreement = the grid is right."""
import json, lxml.html, datetime
from docling.document_converter import DocumentConverter
F='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/0000764478-25-000057.htm'

# --- parser A: my lxml code -------------------------------------------------
src=open('/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/filing_table.py').read().split("F='/home/faisal")[0]
ns={}; exec(src, ns)
doc=lxml.html.parse(F).getroot()
tA=[x for x in doc.xpath('//table') if 'Selected Online Revenue Data' in x.text_content()][0]
A=ns['parse'](tA)

# --- parser B: docling ------------------------------------------------------
d=DocumentConverter().convert(F).document
tB=[x for x in d.tables if 'Selected Online Revenue Data' in x.export_to_markdown(d)][0]
rows={}
for c in tB.data.table_cells:
    if c.text.strip():
        rows.setdefault(c.start_row_offset_idx, []).append((c.start_col_offset_idx, c.text.strip()))
def hd(s): return any(ch.isdigit() for ch in s)
dur =[(a,x) for a,x in sorted(rows.get(1,[]))]
date=[(a,x) for a,x in sorted(rows.get(2,[]))]
# rebuild each band's span from the next band's start
def band(a):
    prev=None
    for p,x in dur:
        if p<=a: prev=x
    return prev
B=[]
for r in sorted(rows):
    if r<3: continue
    cells=sorted(rows[r])
    if len(cells)<2: continue
    if not any(ch.isalpha() for ch in cells[0][1]): continue
    label=cells[0][1]
    nums=[(a,x) for a,x in cells[1:] if hd(x) or x in ('-','—','–')]
    if len(nums)!=len(date): continue
    unit='percent' if any(x=='%' for _,x in cells) else ('usd' if any(x=='$' for _,x in cells) else 'count')
    for (a,x),(da,dt) in zip(nums,date):
        v=ns['number'](x)
        B.append({'measure':label,'duration':band(da),
                  'period_end':datetime.datetime.strptime(dt,'%B %d, %Y').date().isoformat(),
                  'value':v,'unit':unit})

print('parser A (lxml)   : %d facts' % len(A))
print('parser B (docling): %d facts' % len(B))
same = A==B
print('IDENTICAL         : %s' % same)
if not same:
    for i,(x,y) in enumerate(zip(A,B)):
        if x!=y: print('  first diff @%d\n    A=%s\n    B=%s'%(i,x,y)); break
    print('  lenA=%d lenB=%d'%(len(A),len(B)))
