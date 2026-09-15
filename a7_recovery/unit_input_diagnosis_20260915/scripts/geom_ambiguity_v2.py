"""Geometric test. Every figure sits at a column position. Does exactly one
header cell span that position? If yes, the mapping is forced - no ambiguity."""
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

figs=forced=none_=multi=0; tabs=0
for fn in sample:
    doc=lxml.html.parse(os.path.join(D,fn)).getroot()
    for t in doc.xpath('//table'):
        grid=[spans(tr) for tr in t.xpath('.//tr')]
        # header = every filled cell in rows BEFORE the first data row.
        first_data=None
        for i,r in enumerate(grid):
            f=[s for s in r if s[2]]
            if len(f)>=2 and not hd(f[0][2]) and sum(1 for _,_,x in f[1:] if hd(x))>=2:
                first_data=i; break
        if first_data is None or first_data==0: continue
        hdr=[s for r in grid[:first_data] for s in r if s[2] and s[0]>0]
        if not hdr: continue
        tabs+=1
        for r in grid[first_data:]:
            f=[s for s in r if s[2]]
            if len(f)<2 or hd(f[0][2]): continue
            for a,b,x in f[1:]:
                if not (hd(x) or x in ('-','—','–')): continue
                figs+=1
                cover=[h for h in hdr if h[0] <= a < h[1]]
                labels={h[2] for h in cover}
                if len(cover)==0: none_+=1
                elif len(labels)==1: forced+=1          # exactly ONE label covers it
                else: multi+=1                          # several distinct labels -> ambiguous
print('tables with a header : %d' % tabs)
print('figures placed       : %d' % figs)
print('  column UNIQUELY forced    : %d  (%.2f%%)' % (forced, 100*forced/figs if figs else 0))
print('  no header covers it       : %d  (%.2f%%)' % (none_, 100*none_/figs if figs else 0))
print('  SEVERAL headers cover it  : %d  (%.2f%%)' % (multi, 100*multi/figs if figs else 0))
print('  -> genuinely undecided    : %d  (%.2f%%)' % (none_+multi, 100*(none_+multi)/figs if figs else 0))
