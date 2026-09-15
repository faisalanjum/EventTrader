"""Replace each flattened table region in the prompt with a clean cell grid.
Everything outside those regions stays byte-identical."""
import re, sys, lxml.html
CACHE='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/%s.htm'

def squash_index(s):
    """-> (squashed string, list mapping squashed pos -> original pos)"""
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch.isspace() or ch == '\xa0': continue
        out.append(ch); idx.append(i)
    return ''.join(out), idx

def grid(table):
    lines=[]
    for tr in table.xpath('.//tr'):
        cells, col = [], 0
        for c in tr.xpath('./td|./th'):
            w=int(c.get('colspan',1)); txt=' '.join(c.text_content().replace('\xa0',' ').split())
            if txt: cells.append('c%02d: %s' % (col, txt))
            col += w
        if cells: lines.append('    ' + '  '.join(cells))
    return '\n[TABLE]\n' + '\n'.join(lines) + '\n[/TABLE]\n'

def repair(text, acc):
    sq, idx = squash_index(text)
    doc = lxml.html.parse(CACHE % acc).getroot()
    spans=[]
    for t in doc.xpath('//table'):
        key = re.sub(r'\s+','', t.text_content().replace('\xa0',' '))
        if len(key) < 40: continue
        if sq.count(key) != 1: continue
        p = sq.index(key)
        spans.append((idx[p], idx[p+len(key)-1]+1, grid(t)))
    spans.sort()
    # no overlaps allowed
    for (a,b,_),(c,d,_) in zip(spans, spans[1:]):
        assert b <= c, 'overlapping table spans %d-%d vs %d-%d' % (a,b,c,d)
    out, last = [], 0
    for a,b,g in spans:
        out.append(text[last:a]); out.append(g); last = b
    out.append(text[last:])
    return ''.join(out), spans

if __name__ == '__main__':
    for tag, acc in (('BBY','0000764478-25-000057'), ('AAL','0000006201-26-000032')):
        head = open('%s/HEAD_%s.txt' % (SC:=sys.path[0] or '.', tag)).read() if False else \
               open('/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/HEAD_%s.txt'%tag).read()
        new, spans = repair(head, acc)
        open('/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/HEADFIX_%s.txt'%tag,'w').write(new)
        print('%s  tables spliced=%d  %d -> %d chars' % (tag, len(spans), len(head), len(new)))
        for a,b,g in spans: print('     span %6d-%-6d  (%d chars of mush -> %d chars of grid)' % (a,b,b-a,len(g)))
