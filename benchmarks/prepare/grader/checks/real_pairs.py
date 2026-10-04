"""The contract pairs on real originals (CONVERTER_COMPARISON.md "Required checks", DESIGN.md section 8.2) plus the
8-case development supplement. For each case a correct route output is HAND-BUILT FROM THE ORIGINAL (table grid from
the HTML, words from the PDF's own text layer, fields from the XML), never from a converter; it must PASS. Damaged
copies must FAIL for the stated reason. Standard library plus Poppler's pdftotext.

    cd <repo root> && python3 -m benchmarks.prepare.grader.checks.real_pairs      # writes grader/checks/RESULTS.json and prints the table

Limits (stated, not hidden): the controls cover only the targets' tables and the context the key names (status PARTIAL,
so the nothing-lost gate is skipped); the scanned-page control takes its words from the key's transcription, so it
proves block joining and fault detection, not OCR. The builders below know nothing about any company: they read grids,
raised marks, word boxes and XML elements the same way for every file."""
import copy
import html
import json
import re
import subprocess
import tempfile
import xml.parsers.expat
from pathlib import Path

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.anchor import Visible, norm

KEY = Path(json.loads((Path(__file__).resolve().parents[2] / 'golden/PACKAGE.json').read_text())['package_path'])  # the recorded final package
CATALOG = KEY.parent.parent / 'case_catalog.csv'
HERE = Path(__file__).parent
ROUTE = {'name': 'hand-built control', 'tool': 'none (built from the original)', 'version': 'n/a', 'settings': {}, 'adapter': 'benchmarks/prepare/grader/checks/real_pairs.py', 'linker': None}
MARK = re.compile(r'^(\(\w{1,2}\)|\w|\*|†|‡)$')
_TR = re.compile(rb'(?is)<tr\b.*?(?=<tr\b|</table)')
_TD = re.compile(rb'(?is)<t([dh])\b([^>]*)>(.*?)(?=<t[dh]\b|</tr|$)')
# guide 3.6: a raised mark is <sup>, vertical-align: super, or a relatively positioned span shifted up
_RAISED = re.compile(rb'(?is)<(sup|font|span)\b([^>]*)>(.*?)</\1\s*>')
_UP = re.compile(rb'(?i)vertical-align\s*:\s*(super|top)|position\s*:\s*relative[^"\']*top\s*:\s*-')
_WORD = re.compile(r'<page\b|<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', re.S)


# ------------------------------------------------------------------------------------------- building controls
def html_table(raw, vis, a, b, uid):
    """A table unit from the original's <tr>/<td> grid in bytes [a, b): colspan/rowspan expanded, raised marks apart."""
    cells, until = [], {}  # until[column] = the first row at which that column is free again (rowspans expire by row)
    for r, tr in enumerate(_TR.finditer(raw, a, b)):
        c = 0
        for td in _TD.finditer(tr.group()):
            while until.get(c, 0) > r: c += 1
            attrs = td.group(2); cs = int((re.search(rb'colspan\s*=\s*["\']?(\d+)', attrs) or [0, b'1'])[1]); rs = int((re.search(rb'rowspan\s*=\s*["\']?(\d+)', attrs) or [0, b'1'])[1])
            start, end = tr.start() + td.start(), tr.start() + td.end()
            text, markers = norm(vis.at(start, end)), []
            for m in _RAISED.finditer(td.group(3)):
                if m.group(1).lower() != b'sup' and not _UP.search(m.group(2)): continue
                mk = norm(html.unescape(re.sub(rb'<[^>]*>', b'', m.group(3)).decode('utf-8', 'replace')))
                if MARK.match(mk) and text.endswith(mk): text, markers = text[:-len(mk)].rstrip(), markers + [mk]
            if text and not re.search(rb'display\s*:\s*none', attrs, re.I):
                cell = {'r': r, 'c': c, 'rs': rs, 'cs': cs, 'text': text, 'anchor': {'byte_start': start, 'byte_end_exclusive': end}}
                if markers: cell['markers'] = markers
                cells.append(cell)
            for k in range(c, c + cs): until[k] = r + rs
            c += cs
    return {'id': uid, 'kind': 'table', 'anchor': {'byte_start': a, 'byte_end_exclusive': b}, 'cells': cells}


def inline_anchors(t):
    """(kind, anchor, marker) for anchors carried inside key values: period parts, footnote marks/notes, range parts."""
    out = []
    for field in ('periods', 'footnote_markers', 'references', 'range'):
        for _, v in grade.alternatives(t, field):
            for x in (v if isinstance(v, list) else [v]) if v else []:
                for part in x.get('parts') or []: out.append(('text', part.get('anchor'), None))
                if x.get('note_anchor'): out.append(('footnote', x['note_anchor'], x.get('marker_text')))
                if x.get('partner'): out.append(('text', x['partner'].get('anchor'), None))
                for ev in x.get('evidence') or []: out.append(('text', ev.get('anchor'), None))
    return [(k, a, m) for k, a, m in out if isinstance(a, dict)]


def nested(a, others):
    """Is anchor a inside another listed anchor? A tool emits blocks, never a block plus its own sub-phrase."""
    for b in others:
        if b is a or b == a: continue
        if 'byte_start' in a and 'byte_start' in b and b['byte_start'] <= a['byte_start'] and a['byte_end_exclusive'] <= b['byte_end_exclusive']: return True
        if 'region' in a and 'region' in b and a.get('page') == b.get('page'):
            (x0, y0, x1, y1), (u0, v0, u1, v1) = a['region'], b['region']
            if u0 <= x0 and v0 <= y0 and x1 <= u1 and y1 <= v1 and (x1 - x0) * (y1 - y0) < (u1 - u0) * (v1 - v0): return True
    return False


def context_units(t, raw, vis, inside):
    """Text units for every context location the key names outside the table/block: headings, lead-in, notes, phrases."""
    wanted = [('heading', a, None) for a in sum((grade.anchors_of(t, 'section_path', i) for i, _ in grade.alternatives(t, 'section_path')), [])]
    for field in ('table_title', 'lead_in', 'unit_printed', 'segment_or_basis', 'corner_text', 'row_label', 'header_path', 'display_value'):
        for i, _ in grade.alternatives(t, field): wanted += [('text', a, None) for a in grade.anchors_of(t, field, i)]
    wanted += inline_anchors(t)
    boxes = [a for _, a, _ in wanted]
    units, seen = [], set()
    for kind, a, marker in wanted:
        key = json.dumps(a, sort_keys=True)
        if 'byte_start' not in a or grade.overlap(a, inside) or key in seen or nested(a, boxes): continue
        text = norm(vis.at(a['byte_start'], a['byte_end_exclusive']))
        if not text: continue
        seen.add(key); unit = {'id': f'ctx{len(units)}', 'kind': kind, 'text': text, 'anchor': dict(a)}
        if marker: unit['marker'] = marker
        units.append(unit)
    return units


def route_file(t, units, status='PARTIAL', seconds=0.0):
    units = sorted(units, key=lambda u: grade.order_key(u['anchor']))
    return {'schema': 'prepare-route-output/1', 'file_id': t['file_id'], 'sha256': t['sha256'], 'route': ROUTE, 'status': status,
            'error': None, 'seconds': seconds, 'units': units}


def html_cell_control(t):
    raw = t['path'].read_bytes(); vis = Visible(raw); ta = t['table_anchor']
    table = html_table(raw, vis, ta['byte_start'], ta['byte_end_exclusive'], 'tbl')
    return route_file(t, context_units(t, raw, vis, ta) + [table]), table


def pdf_words(path):
    """Words with boxes per page from the PDF's own text layer (pdftotext -bbox; its XHTML is not always well-formed)."""
    out = subprocess.run(['pdftotext', '-bbox', str(path), '-'], check=True, capture_output=True).stdout.decode('utf-8', 'replace')
    pages, page = {}, 0
    for m in _WORD.finditer(out):
        if m.group(0).startswith('<page'): page += 1; pages[page] = []; continue
        pages[page].append(((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))), html.unescape(m.group(5))))
    return pages


def pdf_text(pages, page, region):
    x0, y0, x1, y1 = region
    return ' '.join(w for (a, b, c, d), w in pages[page] if x0 <= (a + c) / 2 <= x1 and y0 <= (b + d) / 2 <= y1)


def pdf_cell_control(t, pages):
    """A minimal grid for one PDF cell from the key's own locations: header rows above (the innermost over the value
    column only), in-table context rows, then the value row with its label and partner; prose and titles as units."""
    f, sup, ta = t['fields'], t['support'], t['table_anchor']
    A = lambda field: (sup.get(field) or {}).get('anchors') or []
    text = lambda a: pdf_text(pages, a['page'], a['region'])
    inside = lambda a: grade.overlap(a, ta)
    rows = []  # header anchors grouped into visual rows
    for a in sorted(A('header_path'), key=lambda a: (a['region'][1], a['region'][0])):
        for row in rows:
            if min(row[0]['region'][3], a['region'][3]) > max(row[0]['region'][1], a['region'][1]): row.append(a); break
        else: rows.append([a])
    cells = []
    for r, row in enumerate(rows):
        inner = r == len(rows) - 1
        for a in row: cells.append({'r': r, 'c': 2 if inner else 0, 'rs': 1, 'cs': 1 if inner else 3, 'text': text(a), 'anchor': a})
    rng = f.get('range') or {}
    fixed = [t['anchor']] + A('row_label') + ([rng['partner']['anchor']] if rng.get('partner') else [])  # the value row's own boxes
    ctx = []
    for a in sorted((a for field in ('table_title', 'unit_printed', 'segment_or_basis', 'corner_text') for a in A(field) if inside(a)), key=lambda a: a['region'][1]):
        if any(grade.overlap(a, b) for b in fixed) or any(a == c['anchor'] for c in cells): continue
        within = [c for c in cells if grade.overlap_ratio(c['anchor'], a) >= 0.9 and nested(c['anchor'], [a])]
        if within:  # a tool's cell is the whole printed line, not the key's sub-phrase: widen that header cell
            within[0].update(text=text(a), anchor=a); continue
        if not any(grade.overlap(a, c['anchor']) for c in cells): ctx.append(a)
    for a in ctx: cells.append({'r': len(rows) + len([c for c in cells if c['r'] >= len(rows)]), 'c': 0, 'rs': 1, 'cs': 3, 'text': text(a), 'anchor': a})
    R = max([c['r'] for c in cells], default=-1) + 1
    cells.append({'r': R, 'c': 2, 'rs': 1, 'cs': 1, 'text': text(t['anchor']), 'anchor': dict(t['anchor'])})
    for a in A('row_label'): cells.append({'r': R, 'c': 0, 'rs': 1, 'cs': 1, 'text': text(a), 'anchor': a})
    if rng.get('partner'): cells.append({'r': R, 'c': 1, 'rs': 1, 'cs': 1, 'text': text(rng['partner']['anchor']), 'anchor': rng['partner']['anchor']})
    for ev in rng.get('evidence') or []:
        if not any(grade.overlap(ev['anchor'], c['anchor']) for c in cells): cells.append({'r': 0, 'c': 1, 'rs': 1, 'cs': 2, 'text': text(ev['anchor']), 'anchor': ev['anchor']})
    units, all_boxes = [], [a for field in sup for a in A(field)]
    for field in ('table_title', 'lead_in', 'unit_printed', 'segment_or_basis', 'corner_text'):
        outs = [a for a in A(field) if (field == 'lead_in' or not inside(a)) and not nested(a, all_boxes) and not any(grade.overlap(a, c['anchor']) for c in cells)]
        if not outs: continue
        if field == 'lead_in': units.append({'id': f'u{len(units)}', 'kind': 'text', 'text': ' '.join(text(a) for a in outs), 'anchor': outs if len(outs) > 1 else outs[0]})
        else:
            for a in outs:
                if not any(u['anchor'] == a for u in units): units.append({'id': f'u{len(units)}', 'kind': 'text', 'text': text(a), 'anchor': a})
    for m in f.get('footnote_markers') or []:
        units.append({'id': f'u{len(units)}', 'kind': 'text', 'text': m['marker_text'], 'anchor': m['anchor']})
        if m.get('note_anchor'): units.append({'id': f'u{len(units)}', 'kind': 'footnote', 'marker': m['marker_text'], 'text': text(m['note_anchor']), 'anchor': m['note_anchor']})
    table = {'id': 'tbl', 'kind': 'table', 'anchor': dict(ta), 'cells': cells}
    return route_file(t, units + [table]), table


def xml_fields(raw):
    """Every text-bearing element as a field unit: expanded name, parent path, position among same-name siblings;
    the anchor spans the whole element (its name is checked by name, its text as text)."""
    units, stack, counts, text, start = [], [], [{}], [], [None, None]
    p = xml.parsers.expat.ParserCreate(namespace_separator='}')
    fix = lambda n: '{' + n if '}' in n else n
    def s(name, attrs):
        counts[-1][name] = counts[-1].get(name, 0) + 1
        stack.append((fix(name), counts[-1][name], p.CurrentByteIndex)); counts.append({}); text.clear()
    def ch(d): text.append(d)
    def e(name):
        full = ''.join(text); kids = counts.pop(); me, pos, begin = stack.pop()
        if full.strip() and not kids:
            end = raw.index(b'>', p.CurrentByteIndex) + 1
            units.append({'id': f'x{len(units)}', 'kind': 'field', 'name': me, 'path': [n for n, _, _ in stack], 'group': {'index': stack[-1][1] if stack else 1, 'count': None},
                          'text': norm(full), 'anchor': {'byte_start': begin, 'byte_end_exclusive': end}, '_parent_key': tuple(n for n, _, _ in stack)})
        text.clear()
    p.StartElementHandler, p.CharacterDataHandler, p.EndElementHandler = s, ch, e
    p.Parse(raw, True)
    totals = {}
    for u in units: totals[u['_parent_key']] = max(totals.get(u['_parent_key'], 0), u['group']['index'])
    for u in units: u['group']['count'] = totals[u.pop('_parent_key')]
    return units


def xml_control(t):
    raw = t['path'].read_bytes(); units = xml_fields(raw)
    return route_file(t, units, status='OK'), units


# -------------------------------------------------------------------------------------------------- the cases
def damage(route, fn):
    r = copy.deepcopy(route); fn(r); return r


def tbl_of(route):
    return next(u for u in route['units'] if u['kind'] == 'table')


def cell_by_anchor(table, anchor):
    return next(c for c in table['cells'] if grade.overlap(c['anchor'], anchor))


def swap_cols(table, t):
    v = cell_by_anchor(table, t['anchor']); p = cell_by_anchor(table, t['fields']['range']['partner']['anchor'])
    v['c'], p['c'] = p['c'], v['c']


def cases(targets):
    T = {t['key_id']: t for t in targets}
    out = []

    # 1. Berry T05: symbol cells $ ( ) around the value
    t = T['0001140361-25-003207/T05']; ctl, tbl = html_cell_control(t)
    v = cell_by_anchor(tbl, t['anchor']); sym = [c for a in grade.anchors_of(t, 'display_value') for c in tbl['cells'] if grade.overlap(c['anchor'], a) and c is not v]
    merged = copy.deepcopy(ctl); tb = tbl_of(merged); mv = cell_by_anchor(tb, t['anchor'])
    for c in [c for c in tb['cells'] if any(c['anchor'] == s['anchor'] for s in sym)]: tb['cells'].remove(c)
    mv.update(text=t['fields']['display_value'], c=min(c['c'] for c in sym + [v]), cs=len(sym) + 1, anchor=[c['anchor'] for c in sorted(sym + [v], key=lambda c: c['c'])])
    out.append(('Berry T05', t['key_id'], [
        ('valid: $ ( ) kept as separate cells in the row', ctl, 'PASS', None),
        ('valid: symbol cells joined into one cell "$(506)"', merged, 'PASS', None),
        ('damaged: parentheses removed', damage(ctl, lambda r: cell_by_anchor(tbl_of(r), t['anchor']).update(text='506')), 'FAIL', 'value'),
        ('damaged: "$" attached to the row above', damage(ctl, lambda r: [c.update(r=c['r'] - 1) for c in tbl_of(r)['cells'] if c['anchor'] == sym[0]['anchor']]), 'FAIL', 'value'),
        ('damaged: value moved under the other year column', damage(ctl, lambda r: cell_by_anchor(tbl_of(r), t['anchor']).update(c=cell_by_anchor(tbl_of(r), t['anchor'])['c'] + 3)), 'FAIL', 'header_path')]))

    # 2. Aflac T03: five stacked header fragments
    t = T['bundle-006/0000004977-23-000059:T03']; ctl, tbl = html_cell_control(t)
    frag = [c for a in grade.anchors_of(t, 'header_path') for c in tbl['cells'] if grade.overlap(c['anchor'], a)]
    joined = copy.deepcopy(ctl); jt = tbl_of(joined); jf = [c for c in jt['cells'] if any(c['anchor'] == f['anchor'] for f in frag)]
    for c in jf[1:]: jt['cells'].remove(c)
    jf[0].update(text=' '.join(f['text'] for f in frag), anchor=[f['anchor'] for f in frag], rs=len(frag))
    def lose_excluding(r):
        tb = tbl_of(r); tb['cells'].remove(next(c for c in tb['cells'] if c['anchor'] == frag[1]['anchor']))
    def shift(r):
        for c in tbl_of(r)['cells']:
            if any(c['anchor'] == f['anchor'] for f in frag): c['c'] += c['cs']
    out.append(('Aflac T03', t['key_id'], [
        ('valid: five header fragments as separate stacked cells', ctl, 'PASS', None),
        ('valid: fragments joined into one header cell (several spans)', joined, 'PASS', None),
        ('damaged: "Excluding" fragment lost', damage(ctl, lose_excluding), 'FAIL', 'header_path'),
        ('damaged: header assigned to the adjacent column', damage(ctl, shift), 'FAIL', 'header_path')]))

    # 3 + supplement UDR: PDF cells
    pages = pdf_words(T['udr/P01']['path'])
    for cid in ('udr/P01', 'udr/P02', 'udr/P03', 'udr/P04', 'udr/P05'):
        t = T[cid]; ctl, tbl = pdf_cell_control(t, pages)
        variants = [('valid: value linked to its row, column and page', ctl, 'PASS', None),
                    ('damaged: correct number under a different column', damage(ctl, lambda r: cell_by_anchor(tbl_of(r), t['anchor']).update(c=1 if cell_by_anchor(tbl_of(r), t['anchor'])['c'] != 1 else 0)), 'FAIL', 'header_path'),
                    ('damaged: value on a missing page', damage(ctl, lambda r: cell_by_anchor(tbl_of(r), t['anchor'])['anchor'].update(page=t['anchor']['page'] + 1)), 'UNRESOLVED', None)]
        if cid == 'udr/P03':
            variants.append(('damaged: scenario columns swapped (Low/High flipped)', damage(ctl, lambda r: swap_cols(tbl_of(r), t)), 'FAIL', 'range'))
        def space_inside(r, t=t):  # Codex's review case: "1,970" -> "1,9 70" must fail (R6)
            c = cell_by_anchor(tbl_of(r), t['anchor']); x = c['text']; c['text'] = x[:len(x) // 2] + ' ' + x[len(x) // 2:]
        variants.append(('damaged: a space inserted inside the value', damage(ctl, space_inside), 'FAIL', 'value'))
        if cid == 'udr/P01':
            title = t['fields']['table_title'][0]
            def qualify(r):  # Codex's review case: a qualifier the record does not own is appended to the title (E13)
                u = next(u for u in r['units'] if u.get('kind') != 'table' and grade.norm(u.get('text', '')) == grade.norm(title)); u['text'] += ' (including discontinued operations)'
            variants.append(('damaged: an unrelated qualifier appended to the title', damage(ctl, qualify), 'FAIL', 'table_title'))
        out.append((f'UDR {cid}', cid, variants))

    # 4 + supplement Darden: range / footnote
    for cid, dmg in (('darden/C07', [('damaged: footnote digit joined to the value ("0.152")', lambda t: lambda r: cell_by_anchor(tbl_of(r), t['anchor']).update(text='0.152', markers=[]), 'FAIL', 'value')]),
                     ('darden/C08', [('damaged: minus sign lost ("0.26")', lambda t: lambda r: cell_by_anchor(tbl_of(r), t['anchor']).update(text='0.26'), 'FAIL', 'value')]),
                     ('darden/C09', [('damaged: range endpoints flipped', lambda t: lambda r: swap_cols(tbl_of(r), t), 'FAIL', 'range')])):
        t = T[cid]; ctl, tbl = html_cell_control(t)
        out.append((f'Darden {cid}', cid, [('valid: scenario/range cells with roles kept', ctl, 'PASS', None)] + [(n, damage(ctl, f(t)), e, chk) for n, f, e, chk in dmg]))

    # 5. Carnival scanned page: ordered text blocks
    t = T['bundle-030/0000815097-26-000037:T01']; text = t['fields']['printed_text']; page, (x0, y0, x1, y1) = t['anchor']['page'], t['anchor']['region']
    sentences = re.split(r'(?<=[.:;])\s+', text); chunk = max(1, len(sentences) // 6)
    blocks = [' '.join(sentences[i:i + chunk]) for i in range(0, len(sentences), chunk)]
    band = (y1 - y0) / len(blocks)
    units = [{'id': f'b{i}', 'kind': 'text', 'text': b, 'anchor': {'page': page, 'region': [x0, y0 + i * band, x1, y0 + (i + 1) * band]}} for i, b in enumerate(blocks)]
    units.append({'id': 'h', 'kind': 'heading', 'text': t['fields']['section_path'][0], 'anchor': grade.anchors_of(t, 'section_path')[0]})
    ctl = route_file(t, units)
    def drop_not(r):
        u = next(u for u in r['units'] if ' not ' in u['text']); u['text'] = u['text'].replace(' not ', ' ', 1)
    def reorder(r):
        i = next(i for i, u in enumerate(r['units']) if u['id'] == 'b1'); r['units'][i], r['units'][i + 1] = r['units'][i + 1], r['units'][i]
    out.append(('Carnival scanned page T01', t['key_id'], [
        ('valid: page text split into ordered blocks', ctl, 'PASS', None),
        ('damaged: one block omitted', damage(ctl, lambda r: r['units'].remove(next(u for u in r['units'] if u['id'] == 'b2'))), 'FAIL', 'printed_text'),
        ('damaged: one "not" omitted', damage(ctl, drop_not), 'FAIL', 'printed_text'),
        ('damaged: blocks out of order', damage(ctl, reorder), 'FAIL', 'printed_text', 'reading_order')]))

    # 6. Alpha Units XML T01
    t = T['0000950170-24-139133/T01']; ctl, units = xml_control(t)
    v = next(u for u in units if grade.overlap(u['anchor'], t['anchor']))
    pick = lambda r: next(u for u in r['units'] if u['anchor'] == v['anchor'])
    def move_person(r): pick(r)['group']['index'] = 1
    def other_ns(r): pick(r)['path'] = [p_.replace('schedule13D', 'schedule13G') for p_ in pick(r)['path']]
    def rename(r): pick(r)['name'] = v['name'].replace('shared', 'sole')
    out.append(('Alpha Units XML T01', t['key_id'], [
        ('valid: expanded names (any prefix in the file)', ctl, 'PASS', None),
        ('damaged: value moved to another reporting person', damage(ctl, move_person), 'FAIL', 'row_context'),
        ('damaged: namespace changed', damage(ctl, other_ns), 'FAIL', 'header_path'),
        ('damaged: element renamed (sole/shared)', damage(ctl, rename), 'FAIL', 'row_label')]))

    # 7. AMG T05 caption with "The following table" -> the table
    t = T['bundle-001/0001004434-23-000015:T05']; raw = t['path'].read_bytes(); vis = Visible(raw)
    ref = t['fields']['references'][0]; ta = ref['target']['anchor']
    table = html_table(raw, vis, ta['byte_start'], ta['byte_end_exclusive'], 'tbl')
    block = {'id': 'cap', 'kind': 'caption', 'text': norm(vis.at(t['anchor']['byte_start'], t['anchor']['byte_end_exclusive'])), 'anchor': dict(t['anchor']),
             'links': [{'text': ref['printed_text'], 'href': None, 'to': 'tbl'}]}
    ctl = route_file(t, context_units(t, raw, vis, ta) + [block, table])
    out.append(('AMG T05 reference', t['key_id'], [
        ('valid: caption + link to the table it introduces', ctl, 'PASS', None),
        ('damaged: referenced table omitted', damage(ctl, lambda r: r['units'].remove(next(u for u in r['units'] if u['id'] == 'tbl'))), 'FAIL', 'references'),
        ('damaged: link points to another block (E6: a contradictory destination)', damage(ctl, lambda r: next(u for u in r['units'] if u['id'] == 'cap')['links'][0].update(to='ctx0')), 'FAIL', 'references')]))
    return out


# ---------------------------------------------------------------------------------------------------- runner
def main():
    targets = grade.load_key(KEY, CATALOG)
    results, ok = [], True
    for name, kid, variants in cases(targets):
        for variant in variants:
            label, route, expect, check = variant[:4]; gate = variant[4] if len(variant) > 4 else None
            with tempfile.TemporaryDirectory() as tmp:
                rdir = Path(tmp) / 'route'; (rdir / route['file_id']).parent.mkdir(parents=True)
                (rdir / (route['file_id'] + '.json')).write_text(json.dumps(route))
                rep = grade.run(KEY, rdir, Path(tmp) / 'out', CATALOG, heldout_detail=False)
            verdict = rep['targets'][kid]['verdict']; rows = [r for r in rep['results'] if r['key_id'] == kid]
            fired = sorted({r['check'] for r in rows if r['verdict'] == 'fail' and r['check'] not in grade.STRUCTURE})
            structure = sorted({r['check'] for r in rows if r['verdict'] == 'fail' and r['check'] in grade.STRUCTURE})
            reasons = {r['check']: r['reason'] for r in rows if r['verdict'] == 'fail'}
            good = verdict == expect and (check is None or check in fired + structure)
            if expect == 'PASS' and check is None: good = good and not fired
            if gate: good = good and not rep['gates'][gate]['pass']
            ok &= good
            results.append({'case': name, 'key_id': kid, 'variant': label, 'expected': expect, 'expected_check': check, 'expected_gate_fail': gate,
                            'verdict': verdict, 'failed_checks': fired, 'structure_misses': structure, 'reasons': reasons, 'ok': good})
            want = f"{expect}{' + ' + check if check else ''}{' + gate ' + gate if gate else ''}"
            print(f"{'ok ' if good else 'BAD'} | {name:<26} | {label:<62} | want {want:<32} | got {verdict} {fired} {reasons if fired or structure else ''}")
    (HERE / 'RESULTS.json').write_text(json.dumps({'key': str(KEY), 'all_ok': ok, 'results': results}, indent=1, ensure_ascii=False))
    print(f"\n{sum(r['ok'] for r in results)}/{len(results)} variants behaved as required; RESULTS.json written")
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
