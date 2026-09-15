"""ADDITIVE repair: keep every original byte, insert a clean cell grid right
after each table's flattened text. Quotes keep resolving; nothing is lost."""
import re, lxml.html
SC='/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad'
CACHE='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/%s.htm'

def squash_index(s):
    out, idx, i, n = [], [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '\\' and i+1 < n and s[i+1] in 'nrt': i += 2; continue
        if c == '\\' and i+1 < n and s[i+1] == '"': out.append('"'); idx.append(i); i += 2; continue
        if c.isspace() or c == '\xa0': i += 1; continue
        out.append(c); idx.append(i); i += 1
    return ''.join(out), idx

def squash(s): return squash_index(s)[0]

def grid(table):
    lines = []
    for tr in table.xpath('.//tr'):
        cells, col = [], 0
        for c in tr.xpath('./td|./th'):
            w = int(c.get('colspan', 1))
            t = ' '.join(c.text_content().replace('\xa0', ' ').split())
            if t: cells.append('c%02d: %s' % (col, t))
            col += w
        if cells: lines.append('  '.join(cells))
    return ' \\n[GRID]\\n' + '\\n'.join(lines).replace('"', '\\"') + '\\n[/GRID]\\n'

for tag, acc in (('BBY','0000764478-25-000057'), ('AAL','0000006201-26-000032')):
    text = open('%s/HEAD_%s.txt' % (SC, tag)).read()
    sq, idx = squash_index(text)
    doc = lxml.html.parse(CACHE % acc).getroot()
    ins = []
    for t in doc.xpath('//table'):
        key = squash(t.text_content())
        if len(key) < 40 or sq.count(key) != 1: continue
        p = sq.index(key)
        ins.append((idx[p + len(key) - 1] + 1, grid(t)))     # insert AFTER the table text
    ins.sort()
    out, last = [], 0
    for at, g in ins:
        out.append(text[last:at]); out.append(g); last = at
    out.append(text[last:])
    new = ''.join(out)
    open('%s/HEADADD_%s.txt' % (SC, tag), 'w').write(new)
    # losslessness: removing every inserted grid must give back the original exactly
    back = re.sub(r' \\n\[GRID\]\\n.*?\\n\[/GRID\]\\n', '', new)
    print('%s  grids inserted=%-2d  %d -> %d chars   ORIGINAL RECOVERED EXACTLY: %s'
          % (tag, len(ins), len(text), len(new), back == text))
