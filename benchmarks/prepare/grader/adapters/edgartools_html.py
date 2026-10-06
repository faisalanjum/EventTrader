"""Route adapter: edgartools `parse_html` -> the common route format, anchored by the shared linker.
edgartools keeps no source positions, so the linker places every block. Under its own environment the adapter first
dumps the parsed node tree to plain JSON (kept as the raw output); `to_units` works on that dump, so it is testable
without the package. Shape rules only, no document-specific logic.

    <edgartools python> -m benchmarks.prepare.grader.adapters.edgartools_html --key <key package> --split development --out <run dir> [--catalog CSV]"""
import argparse
import json
from bisect import bisect_right
import re
from dataclasses import asdict
import time
from pathlib import Path

from benchmarks.prepare.grader import anchor, grade
from benchmarks.prepare.grader.adapters import cache

NAME = 'edgartools-html'  # the tool's heading nodes nested inside paragraphs are kept as headings
KIND = {'HeadingNode': 'heading', 'ParagraphNode': 'text', 'TextNode': 'text', 'ListItemNode': 'list_item', 'ImageNode': 'image'}
BRANCH = ('DocumentNode', 'ContainerNode', 'SectionNode', 'ListNode')
BLOCKY = ('HeadingNode', 'ParagraphNode', 'ContainerNode', 'SectionNode', 'ListNode', 'TableNode', 'ListItemNode', 'ImageNode')  # children that make their parent a branch; a picture has no text to merge into a run: flattened with its paragraph it was lost (Codex's worktree)


def dump(node):
    """Plain-dict copy of an edgartools node tree (run under the edgartools environment)."""
    kind = type(node).__name__
    d = {'type': kind}
    if kind == 'HeadingNode':  # the tool's own evidence for its heading claim, kept as a claim: a style or a confidence certifies no heading (Codex's worktree)
        native = {'metadata': dict(getattr(node, 'metadata', None) or {})}
        if getattr(node, 'style', None) is not None: native['style'] = asdict(node.style)
        for key in ('semantic_type', 'semantic_role'):
            value = getattr(node, key, None)
            if value is not None: native[key] = getattr(value, 'value', value)
        d['native'] = native
    if kind == 'TableNode':
        rows = list(node.headers or []) + [getattr(r, 'cells', r) for r in node.rows or []]
        d['caption'] = node.caption
        d['rows'] = [[{'text': (c.text() if callable(c.text) else c.text) or '', 'colspan': c.colspan or 1, 'rowspan': c.rowspan or 1, 'is_header': bool(c.is_header)} for c in row] for row in rows]
        return d
    kids = list(getattr(node, 'children', None) or [])
    if kind in BRANCH or any(type(k).__name__ in BLOCKY and type(k).__name__ != 'HeadingNode' for k in kids):  # a paragraph that holds blocks (a heading child alone keeps the run-in handling below) (a note emitted as one 60,000-character node) is a branch: its own inline runs become units, its blocks are walked
        children, run = [], []
        def flush():
            if run: children.append({'type': 'TextNode', 'text': ''.join(t + (' ' if (getattr(k, 'metadata', None) or {}).get('has_tail_whitespace') else '') for k, t in run).strip(), 'links': [{'text': (l.text() if callable(l.text) else l.text) or '', 'href': l.href} for k, _ in run for l in ([k] if type(k).__name__ == 'LinkNode' else (k.walk() if hasattr(k, 'walk') else [])) if type(l).__name__ == 'LinkNode']}); run.clear()
        for k in kids:
            if type(k).__name__ in BLOCKY: flush(); children.append(dump(k))
            else: run.append((k, (k.text() if callable(getattr(k, 'text', None)) else getattr(k, 'text', '')) or ''))
        flush(); d['children'] = [c for c in children if c.get('type') != 'TextNode' or c.get('text')]; d['type'] = kind if kind in BRANCH else 'ContainerNode'; return d
    text = node.text() if callable(getattr(node, 'text', None)) else getattr(node, 'text', '')
    heads = [k for k in kids if type(k).__name__ == 'HeadingNode']
    if heads:  # the tool's heading claim inside a paragraph: kept when its text is the paragraph's start or end (the parser's own text, no new joins)
        ht = (heads[0].text() or '').strip(); pt = (text or '').strip()
        if ht and pt.startswith(ht): d['heading'] = dict(dump(heads[0]), text=ht); d['rest'] = pt[len(ht):].strip(); d['order'] = 'head_first'
        elif ht and pt.endswith(ht): d['heading'] = dict(dump(heads[0]), text=ht); d['rest'] = pt[:-len(ht)].strip(); d['order'] = 'head_last'
    d['text'] = text or ''
    for k in ('level', 'src', 'href'):
        if getattr(node, k, None) is not None: d[k] = getattr(node, k)
    links = [{'text': (l.text() if callable(l.text) else l.text) or '', 'href': l.href} for l in node.walk() if type(l).__name__ == 'LinkNode'] if hasattr(node, 'walk') else []
    if links: d['links'] = links
    return d


def codes(raw, vis):
    """One code for every picture tag that writes a `src`, shown or hidden: the source's own SHA-256 (its first 16 hex digits) and the tag's first byte — letters
    and digits the tool's cleaning cannot touch, and nothing a name written in any source can impersonate — with what it stands for: {code: (tag start, the name
    as the parser reads it)}. EdgarTools rewrites the file's text before it parses it (runs of spaces, a space after a point before a capital, `&amp;amp;`,
    zero-width characters), and a name that reached the linker changed stood at another picture's tag; two tags that name one resource, one of them hidden,
    stood for each other (Codex G3-C2)."""
    sha = grade.sha256(raw)[:16]
    return {sha + str(start): (start, name) for start, (_, name) in vis.picture_names.items()}


def named(raw, vis, codes):
    """The source as the tool gets it, decoded: each picture's name replaced by its code, and the text the page hides left out (where the scanner's reading
    is certain). Every tag the source has, the tool sees — an empty anchor too: it may be laid out as a block and break the line (Codex R3-A)."""
    edits = [(vis.picture_names[start][0], code.encode()) for code, (start, _) in codes.items()]
    if vis.certain: edits += [(span, b'') for span in vis.hidden]  # text the page hides (display:none, visibility:hidden, …): the tool read it as text — a hidden "%" put beside "8.2" for alignment became "8.2 %" and its visible "%" cell a copy, and a whole table's cells were placed out of order (Codex C4); the scanner's reading of what hides must be certain
    out, at = [], 0
    for (a, b), piece in sorted(edits):
        out += [raw[at:a], piece]; at = b
    given = b''.join(out) + raw[at:]
    try: return given.decode('utf-8')
    except UnicodeDecodeError: return given.decode('cp1252', 'replace')


def to_units(tree, codes=None):
    """The units of the tool's tree. With `codes` (this source's, from `codes`), every picture names the tag it came from (`tag`, for the linker: a `src` that is no
    code of this source — the tool's own, from a tag the scanner does not list — names no tag) and keeps its code as `src` until `route_for` gives the name back."""
    units = []

    def table_unit(t):
        cells, until = [], {}  # until[column] = the first row at which that column is free again: a rowspan expires by row, whatever later rows hold
        for r, row in enumerate(t.get('rows') or []):
            c = 0
            for cell in row:
                while until.get(c, 0) > r: c += 1
                cs, rs = cell.get('colspan') or 1, cell.get('rowspan') or 1
                if (cell.get('text') or '').strip():
                    cells.append({'r': r, 'c': c, 'rs': rs, 'cs': cs, 'text': cell['text'], 'header': bool(cell.get('is_header'))})
                for k in range(c, c + cs): until[k] = r + rs
                c += cs
        if cells: units.append({'id': f't{len(units)}', 'kind': 'table', 'cells': cells, 'caption': [t['caption']] if t.get('caption') else []})  # a table with no text in any cell (a spacer, a rule) is nothing to read: no unit (764 such units in 60 files stood between titles and their tables)

        elif t.get('caption'): units.append({'id': f'u{len(units)}', 'kind': 'caption', 'text': t['caption']})  # no text in any cell, but a caption: that is read (Codex R2-C4)

    def walk(n):
        kind = n['type']
        if kind == 'TableNode': table_unit(n)
        elif kind in BRANCH:
            for k in n.get('children') or []: walk(k)
        elif n.get('heading'):  # a paragraph the tool marks as (or starting/ending with) a heading
            parts = [('heading', n['heading']['text'], n['heading'].get('level')), ('text', n.get('rest') or '', None)]
            if n.get('order') == 'head_last': parts.reverse()
            for kind2, text2, level in parts:
                if not anchor.squash(text2): continue
                u = {'id': f'u{len(units)}', 'kind': kind2, 'text': text2}
                if level is not None: u['level'] = level
                if kind2 == 'heading' and n['heading'].get('native') is not None: u['native_heading'] = n['heading']['native']
                units.append(u)
        elif kind == 'ImageNode': units.append({'id': f'u{len(units)}', 'kind': 'image', 'text': '', 'src': n.get('src'), **({'tag': codes.get(n.get('src'), (None,))[0]} if codes is not None else {})})
        else:
            if not anchor.squash(n.get('text') or ''): return  # whitespace or control characters only: not a block
            u = {'id': f'u{len(units)}', 'kind': KIND.get(kind, 'other'), 'text': n.get('text') or ''}
            if n.get('level') is not None: u['level'] = n['level']
            if n.get('native') is not None: u['native_heading'] = n['native']  # (only a heading's dump carries it)
            if n.get('links'): u['links'] = [{'text': l['text'], 'href': l['href'], 'to': None} for l in n['links']]
            units.append(u)
    walk(tree)
    return units


def route_for(tree, raw, file_id, sha256, seconds, version, settings=None, vis=None):
    vis = anchor.Visible(raw) if vis is None else vis; known = codes(raw, vis); linked = anchor.link(raw, to_units(tree, known), vis=vis)
    for u in linked['units']:
        if u.get('src') in known: u['src'] = known[u['src']][1]  # the name back, now that the tag has decided the place; a src that is no code stays the tool's own
    units = with_every_picture(linked['units'], vis)
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds,
            'route': {'name': NAME, 'tool': 'edgartools', 'version': version, 'settings': dict(settings or {'parse_html': 'defaults'}, pictures='every shown tag'), 'adapter': 'benchmarks/prepare/grader/adapters/edgartools_html.py',
                      'linker': 'benchmarks/prepare/grader/anchor.py'}, 'units': units, 'uncovered': linked['uncovered']}


def with_every_picture(units, vis):
    """Every picture the source shows stands in the output at its own tag. The tool reads a table's cells as text only and an inline run as text only, so
    a picture there got no unit (386 of 1,508 occurrences in the OCR review's 120 documents, 385 of them in cells; r12). A shown picture tag no unit
    stands at gets one from the scanner's inventory (`vis.pictures`: the same visibility state as the text, so a hidden copy gets none and lends no
    identity), with its own name, inserted before the first unit that starts after the tag — the tool's units keep their order, ids and content — and
    with the cell it stands in: the scanner's innermost cell span, the table unit that holds a cell of the same source table and, where a cell of that
    unit stands in the picture's own cell, its row and column. The same bytes shown twice are two occurrences, two units. `from: source` records it as
    the adapter's work, not the tool's."""
    at = {u['anchor']['byte_start'] for u in units if u.get('kind') == 'image' and isinstance(u.get('anchor'), dict)}
    todo = [(a, b) for a, b in vis.pictures if a not in at]
    if not todo: return units
    def start(x):
        x = x[0] if isinstance(x, list) and x else x
        return x['byte_start'] if isinstance(x, dict) and 'byte_start' in x else None
    spans = sorted((a, b, k) for k, table in enumerate(vis.tables) for row in table for a, b in row); starts = [a for a, _, _ in spans]
    def cell_of(x):  # the innermost source cell holding byte x (the one that starts last among those that do), or -1
        i = bisect_right(starts, x) - 1
        while i >= 0 and not spans[i][0] <= x < spans[i][1]: i -= 1
        return i
    unit_table, route_cell = {}, {}  # source table -> the table unit holding one of its cells; source cell -> (row, column) of the unit's cell in it
    for t in units:
        for c in (t.get('cells') or []) if t.get('kind') == 'table' else []:
            i = cell_of(start(c.get('anchor'))) if start(c.get('anchor')) is not None else -1
            if i >= 0: unit_table.setdefault(spans[i][2], t['id']); route_cell.setdefault(i, (c['r'], c['c']))
    added = []
    for a, b in todo:
        u = {'id': f'p{a}', 'kind': 'image', 'text': '', 'src': vis.picture_sources.get(a), 'anchor': {'byte_start': a, 'byte_end_exclusive': b}, 'from': 'source'}
        i = cell_of(a)
        if i >= 0:
            u['cell'] = {'byte_start': spans[i][0], 'byte_end_exclusive': spans[i][1]}
            if spans[i][2] in unit_table: u['cell']['table'] = unit_table[spans[i][2]]
            if i in route_cell: u['cell']['r'], u['cell']['c'] = route_cell[i]
        added.append(u)
    out = []
    for u in units:
        s0 = start(u.get('anchor'))
        while added and s0 is not None and added[0]['anchor']['byte_start'] < s0: out.append(added.pop(0))
        out.append(u)
    return out + added


def unsupported(file_id, sha256, version, status='UNSUPPORTED', error='not an HTML file'):
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': status, 'error': error, 'seconds': 0,
            'route': {'name': NAME, 'tool': 'edgartools', 'version': version, 'settings': {}, 'adapter': 'benchmarks/prepare/grader/adapters/edgartools_html.py', 'linker': None}, 'units': []}


def whole_headings():
    """A block the tool takes for a heading is read whole — every descendant's text, as the tool reads <h1>–<h6> and as the browser shows it. Its
    `DocumentBuilder._get_element_text` reads a block only to its first child element, and a `HeadingNode` is terminal: `<div><a id="x"></a>Item 1A. Risk
    Factors</div>` read nothing and fell through to a paragraph (seven section headings of one file), `For the quarterly period ended <ix:nonNumeric …>December
    28, 2024</ix:nonNumeric>` lost its date. Two moments, both the tool's own decision and its own <h1> reader: (a) as it reads the block it is deciding on —
    only a block of inline runs (its own `_is_text_only_container`), laid out as a block, no table part or list, no table or picture inside: a container of
    blocks keeps its own segmentation, a row is never a line; (b) a heading it made from a block's leading text, when that block holds blocks (an inline-laid
    <div> with the file number): read whole after the fact, again unless a table or picture is inside — the tool's terminal heading would swallow them (stated,
    the tool's). An inline run it takes for a heading (a bold <font> inside a sentence) keeps the tool's own reading. Codex R2-C1, R3-A; recorded here, never in
    the environment. Idempotent."""
    try: from edgar.documents.nodes import HeadingNode; from edgar.documents.strategies import document_builder as db
    except ImportError: return  # a stand-in for the tool (the tests') has no builder: nothing to fix there; the tool itself has one (tests/test_whole_headings.py, under its environment)
    if getattr(db.DocumentBuilder, '_whole_headings', False): return
    H, PARTS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'), {'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'caption', 'colgroup', 'col', 'ul', 'ol', 'li', 'dl', 'dt', 'dd'}
    create, read = db.DocumentBuilder._create_node_for_element, db.DocumentBuilder._get_element_text
    def line(self, element, style):  # a block the tool may take for one line of heading: not inline by tag, not laid out inline, not a table or list part, nothing but inline runs in it, no table or picture under it
        tag = element.tag.lower() if isinstance(element.tag, str) else ''
        return tag and tag not in H and tag not in self.INLINE_ELEMENTS and tag not in PARTS and not tag.startswith(('ix:', '{')) and getattr(style, 'display', None) not in ('inline', 'inline-block') \
            and not any(isinstance(d.tag, str) and d.tag.lower() in ('table', 'img') for d in element.iterdescendants())
    def whole(self, element):
        kept, element.tag = element.tag, 'h1'  # the tool reads an <h1> whole: the same reading for the block it takes for one
        try: return read(self, element)
        finally: element.tag = kept
    def creating(self, element, style):
        self._making = (element, style) if line(self, element, style) and self._is_text_only_container(element) and not (element.text or '').strip() and len(element) and not (element[0].text_content() or '').strip() else None  # (a): only where the block's text begins after an element holding nothing — the branch the tool's reader loses
        try: node = create(self, element, style)
        finally: self._making = None
        if isinstance(node, HeadingNode) and line(self, element, style): node.content = whole(self, element)  # (b): every heading the tool made from a block, read whole
        return node
    def reading(self, element):
        made = getattr(self, '_making', None)
        return whole(self, element) if made and made[0] is element else read(self, element)  # (a)
    db.DocumentBuilder._create_node_for_element, db.DocumentBuilder._get_element_text, db.DocumentBuilder._whole_headings = creating, reading, True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    ap.add_argument('--reuse-raw', action='store_true', help='adapt the saved node dump again instead of parsing')
    a = ap.parse_args(argv)
    from edgar.documents import parse_html  # only here: the grader package stays standard-library
    whole_headings()
    import importlib.metadata as md
    version = f"edgartools {md.version('edgartools')}"
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True); (out / 'route').mkdir(exist_ok=True)
    files = {}
    for src in grade.load_sources(a.key, a.catalog):  # sources only: converters never read answers
        if src['split'] == a.split: files.setdefault(src['file_id'], (src['path'], src['sha256']))
    facts, settings = {}, {'parse_html': 'defaults', 'retain_pictures': True, 'retain_native_heading_evidence': True, 'picture_names': 'codes', 'hidden_text': 'left out', 'headings': 'detected blocks read whole'}  # what the saved parse keeps: one saved before pictures were kept answers to other settings and is not reused
    for fid, (path, sha) in sorted(files.items()):
        (out / 'route' / fid).parent.mkdir(parents=True, exist_ok=True); (out / 'raw' / fid).parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() not in ('.htm', '.html'):
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version))); facts[fid] = {'status': 'UNSUPPORTED'}; continue
        raw = path.read_bytes(); t0 = time.time(); vis = anchor.Visible(raw); scanned = time.time() - t0; t0 = time.time(); rawjson = out / 'raw' / (fid + '.edgartools.json'); metajson = out / 'raw' / (fid + '.meta.json'); ver = version
        try:
            if a.reuse_raw and rawjson.exists():  # a saved parse is reused only whole: its record names the source bytes, settings, producing version and output (adapters/cache.py; Codex R13 C1, R15-5)
                meta = cache.reuse(metajson, sha, settings)
                if meta.get('status') != 'OK': raise RuntimeError('cache refused: the cached run did not succeed')
                tree, dt, ver = json.loads(rawjson.read_text()), meta.get('tool_seconds', 0), meta['version']
            else:
                cache.begin(metajson)  # from here the old record vouches for nothing: a crash below leaves no record
                tree = dump(parse_html(named(raw, vis, codes(raw, vis))).root); dt = time.time() - t0  # the tool reads the source with the pictures' names as codes and no empty anchor
                rawjson.write_text(json.dumps(tree, ensure_ascii=False)); cache.save(metajson, [rawjson], sha256=sha, version=version, settings=settings, status='OK', tool_seconds=round(dt, 2))
        except Exception as e:  # a tool crash is a result, never a stop
            facts[fid] = {'status': 'FAILED', 'error': repr(e)[:300], 'seconds': round(time.time() - t0, 2)}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version, 'FAILED', repr(e)[:300]))); continue
        t1 = time.time(); route = route_for(tree, raw, fid, sha, round(dt, 2), ver, settings, vis)
        flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
        facts[fid] = {'status': 'OK', 'version': ver, 'tool_seconds': round(dt, 2), 'adapter_seconds': round(time.time() - t1 + scanned, 2), 'items': len(flat),
                      'unanchored': sum(1 for x in flat if not x.get('anchor')), 'uncovered_spans': len(route['uncovered']),
                      'uncovered_chars': sum(len(anchor.squash(s['text'])) for s in route['uncovered'])}
        (out / 'route' / (fid + '.json')).write_text(json.dumps(route, ensure_ascii=False))
        print(fid, facts[fid], flush=True)
    (out / 'facts.json').write_text(json.dumps({'route': NAME, 'version': version, 'split': a.split, 'files': facts}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
