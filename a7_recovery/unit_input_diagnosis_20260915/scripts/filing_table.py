"""One filing HTML table -> data points. Pure structure: colspan geometry + cell
digits. No keyword lists, no per-filing branches, no model call."""
import json, datetime, lxml.html

def spans(tr):
    out, col = [], 0
    for c in tr.xpath('./td|./th'):
        w = int(c.get('colspan', 1))
        out.append((col, col + w, ' '.join(c.text_content().split())))
        col += w
    return out

def has_digit(s): return any(ch.isdigit() for ch in s)

def number(tok):
    neg  = tok.startswith('(') and tok.endswith(')')
    body = tok.strip('()').replace(',', '').replace('$', '').replace('%', '').strip()
    if not any(ch.isdigit() for ch in body): return 0          # a dash cell
    v = float(body)
    if '.' not in body: v = int(v)
    return -v if neg else v

def parse(table):
    rows = [spans(tr) for tr in table.xpath('.//tr')]
    dur = dates = None
    facts = []
    for r in rows:
        filled = [s for s in r if s[2]]
        if not filled: continue
        # a band row carries no label in column 0 and no digits-only values
        if dates is None:
            if all(not has_digit(x) for _, _, x in filled) and len(filled) > 1:
                dur = filled; continue
            if dur and all(',' in x for _, _, x in filled):
                dates = filled
                cols = [(d, next((x for p, q, x in dur if p <= a < q), None))
                        for a, _, d in dates]
                continue
            continue
        if len(filled) == 1: continue                          # heading row
        label = filled[0][2]
        rest  = [x for _, _, x in filled[1:]]
        nums  = [x for x in rest if has_digit(x) or x in ('-', '—', '–')]
        if len(nums) != len(cols): continue
        unit = 'percent' if '%' in rest else ('usd' if '$' in rest else 'count')
        for (d, band), n in zip(cols, nums):
            facts.append({
                'measure': label,
                'duration': band,
                'period_end': datetime.datetime.strptime(d, '%B %d, %Y').date().isoformat(),
                'value': number(n), 'unit': unit})
    return facts

F='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/0000764478-25-000057.htm'
doc = lxml.html.parse(F).getroot()
t = [x for x in doc.xpath('//table') if 'Selected Online Revenue Data' in x.text_content()][0]
facts = parse(t)
print('FACTS:', len(facts))
for f in facts[:4] + facts[-4:]: print(json.dumps(f))
print()
print('distinct measures:', len({f['measure'] for f in facts}))
print('distinct periods :', sorted({(f['duration'], f['period_end']) for f in facts}))
