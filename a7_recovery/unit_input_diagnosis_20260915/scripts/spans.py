import lxml.html
F='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/0000764478-25-000057.htm'
doc=lxml.html.parse(F).getroot()
t=[x for x in doc.xpath('//table') if 'Selected Online Revenue Data' in x.text_content()][0]

def spans(tr):
    """-> [(start_col, end_col, text)] for every cell, counting empty ones."""
    out, col = [], 0
    for c in tr.xpath('./td|./th'):
        w = int(c.get('colspan', 1))
        txt = ' '.join(c.text_content().split())
        out.append((col, col + w, txt))
        col += w
    return out

rows = t.xpath('.//tr')
dur  = [s for s in spans(rows[1]) if s[2]]
date = [s for s in spans(rows[2]) if s[2]]
print('duration bands :', [(a,b,x) for a,b,x in dur])
print('date bands     :', [(a,b,x) for a,b,x in date])
print()
for a, b, d in date:
    owner = [x for p, q, x in dur if p <= a < q]
    print('  cols %2d-%-2d  %-18s  <-  %s' % (a, b-1, d, owner[0] if owner else 'NONE'))
