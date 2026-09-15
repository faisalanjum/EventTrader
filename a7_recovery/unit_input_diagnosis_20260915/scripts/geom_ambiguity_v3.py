"""Correct test. A figure's placement is FORCED when, on every header ROW, at most
one cell of that row covers its column position (levels stack; they do not compete).
It is AMBIGUOUS when some header row has two or more cells covering that position."""
import os, random, lxml.html
D='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache'
by={}
for f in sorted(os.listdir(D)): by.setdefault(f.split('-')[0], []).append(f)
random.seed(31)
sample=[random.choice(v) for v in by.values()]; random.shuffle(sample); sample=sample[:25]

def hd(s): return any(c.isdigit() for c in s)
def spans(tr):
    out,col=[],0
    for c in tr.xpath('./td|./th'):
        w=int(c.get('colspan',1)); out.append((col,col+w,' '.join(c.text_content().split()))); col+=w
    return out

figs=forced=none_=ambig=0; tabs=0
for fn in sample:
    doc=lxml.html.parse(os.path.join(D,fn)).getroot()
    for t in doc.xpath('//table'):
        grid=[spans(tr) for tr in t.xpath('.//tr')]
        first=None
        for i,r in enumerate(grid):
            f=[s for s in r if s[2]]
            if len(f)>=2 and not hd(f[0][2]) and sum(1 for _,_,x in f[1:] if hd(x))>=2:
                first=i; break
        if not first: continue
        hdr_rows=[[s for s in r if s[2] and s[0]>0] for r in grid[:first]]
        hdr_rows=[r for r in hdr_rows if r]
        if not hdr_rows: continue
        tabs+=1
        for r in grid[first:]:
            f=[s for s in r if s[2]]
            if len(f)<2 or hd(f[0][2]): continue
            for a,b,x in f[1:]:
                if not (hd(x) or x in ('-','—','–')): continue
                figs+=1
                per_row=[sum(1 for h in hr if h[0] <= a < h[1]) for hr in hdr_rows]
                if max(per_row) >= 2: ambig+=1
                elif sum(per_row) == 0: none_+=1
                else: forced+=1
print('tables with a header : %d' % tabs)
print('figures placed       : %d' % figs)
print('  placement FORCED (<=1 cell per header row) : %d  (%.2f%%)' % (forced, 100*forced/figs))
print('  no header covers it at any level           : %d  (%.2f%%)' % (none_, 100*none_/figs))
print('  AMBIGUOUS (a header row has 2+ covering)   : %d  (%.2f%%)' % (ambig, 100*ambig/figs))
