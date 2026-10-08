"""Route adapter: edgartools `parse_html` -> the common route format, anchored by the shared linker.
edgartools keeps no source positions, so the linker places every block. Under its own environment the adapter first
dumps the parsed node tree to plain JSON (kept as the raw output); `to_units` works on that dump, so it is testable
without the package. Shape rules only, no document-specific logic."""
from bisect import bisect_left, bisect_right
from copy import copy
from itertools import accumulate
import re
import time
from dataclasses import asdict
from types import SimpleNamespace
from urllib.parse import quote, unquote

from driver.prepare.convert import anchor
from driver.prepare.compare import _CF
from driver.prepare.get.acquire import StorageError

NAME = 'edgartools-html'  # the tool's heading nodes nested inside paragraphs are kept as headings
KIND = {'HeadingNode': 'heading', 'ParagraphNode': 'text', 'TextNode': 'text', 'ListItemNode': 'list_item', 'ImageNode': 'image'}
BRANCH = ('DocumentNode', 'ContainerNode', 'SectionNode', 'ListNode')
BLOCKY = ('HeadingNode', 'ParagraphNode', 'ContainerNode', 'SectionNode', 'ListNode', 'TableNode', 'ListItemNode', 'ImageNode')  # children that make their parent a branch; a picture has no text to merge into a run: flattened with its paragraph it was lost (Codex's worktree)
TABLE = 'data-prepare-table'  # the attribute that carries a table's code (`codes`) through the tool to its table node
_NO_FORMAT = str.maketrans('', '', _CF)


def _heading_boundary(text, cut):
    """A partial style claim needs whitespace; lost layout gaps are proved later."""
    left, right = text[:cut].translate(_NO_FORMAT), text[cut:].translate(_NO_FORMAT)
    return not left or not right or left[-1].isspace() or right[0].isspace()


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
        code = (getattr(node, 'metadata', None) or {}).get(TABLE)
        if code: d['code'] = code  # the source table it came from (`codes`)
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
        nonempty = [k for k in kids if (k.text() or '').strip()]
        ht = (heads[0].text() or '').strip(); pt = (text or '').strip()
        if ht and heads[0] is nonempty[0] and pt.startswith(ht):
            d['heading' if _heading_boundary(pt, len(ht)) else 'pending_heading'] = dict(dump(heads[0]), text=ht)
            d['rest'] = pt[len(ht):].strip(); d['order'] = 'head_first'
            if len(nonempty) > 1: d['heading_gap'] = bool(getattr(nonempty[1], '_prepare_left_gap', False))
        elif ht and heads[0] is nonempty[-1] and pt.endswith(ht):
            d['heading' if _heading_boundary(pt, len(pt)-len(ht)) else 'pending_heading'] = dict(dump(heads[0]), text=ht)
            d['rest'] = pt[:-len(ht)].strip(); d['order'] = 'head_last'
            d['heading_gap'] = bool(getattr(heads[0], '_prepare_left_gap', False))
    d['text'] = text or ''
    for k in ('level', 'src', 'href'):
        if getattr(node, k, None) is not None: d[k] = getattr(node, k)
    links = [{'text': (l.text() if callable(l.text) else l.text) or '', 'href': l.href} for l in node.walk() if type(l).__name__ == 'LinkNode'] if hasattr(node, 'walk') else []
    if links: d['links'] = links
    return d


def codes(raw, vis):
    """One code for every picture tag that writes a `src`, shown or hidden, and for every table tag the page shows: the source's own SHA-256 (its first 16 hex
    digits) and the tag's first byte — letters and digits the tool's cleaning cannot touch, and nothing a name written in any source can impersonate — with what it
    stands for: {code: (tag start, the name as the parser reads it; None for a table)}. EdgarTools rewrites the file's text before it parses it (runs of spaces, a
    space after a point before a capital, `&amp;amp;`, zero-width characters), and a name that reached the linker changed stood at another picture's tag; two
    tags that name one resource, one of them hidden, stood for each other (Codex G3-C2); two copies of one table took each other's cells (A3)."""
    sha = anchor.sha256(raw)[:16]
    return {sha + str(start): (start, name) for start, (_, name) in vis.picture_names.items()} | {sha + str(start): (start, None) for start in vis.table_tags if start is not None}


def named(raw, vis, codes):
    """The source as the tool gets it, decoded: each picture's name replaced by its code, each shown table tag given its code (one attribute, `TABLE`, its
    first: no attribute the source writes is changed), and the text the page hides left out (where the scanner's reading is certain). Every tag the source
    has, the tool sees — an empty anchor too: it may be laid out as a block and break the line (Codex R3-A)."""
    edits = [(vis.picture_names[start][0], code.encode()) if name is not None else ((start + 6, start + 6), f' {TABLE}="{code}"'.encode()) for code, (start, name) in codes.items()]  # after "<table"
    if vis.certain: edits += [(span, b'') for span in vis.hidden]  # text the page hides (display:none, visibility:hidden, …): the tool read it as text — a hidden "%" put beside "8.2" for alignment became "8.2 %" and its visible "%" cell a copy, and a whole table's cells were placed out of order (Codex C4); the scanner's reading of what hides must be certain
    out, at = [], 0
    for (a, b), piece in sorted(edits):
        out += [raw[at:a], piece]; at = b
    given = b''.join(out) + raw[at:]
    try: return given.decode('utf-8')
    except UnicodeDecodeError: return given.decode('cp1252', 'replace')


def to_units(tree, codes=None):
    """The units of the tool's tree. With `codes` (this source's, from `codes`), every picture names the tag it came from (`tag`, for the linker: a `src` that is no
    code of this source — the tool's own, from a tag the scanner does not list — names no tag) and keeps its code as `src` until `route_for` gives the name back;
    every table names the table it came from the same way (`tag`, None when the tool's table carries no code of this source: it then stands nowhere)."""
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
        if cells: units.append({'id': f't{len(units)}', 'kind': 'table', 'cells': cells, 'caption': [t['caption']] if t.get('caption') else [], **({'tag': codes[t['code']][0] if t.get('code') in codes and codes[t['code']][1] is None else None} if codes is not None else {})})  # `tag`: the source table it came from (None: no table of this source - it stands nowhere), for the linker; a table with no text in any cell (a spacer, a rule) is nothing to read: no unit (764 such units in 60 files stood between titles and their tables)

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
            if n.get('pending_heading'):
                first = n['order'] == 'head_first'
                u['_heading'] = {'first': first, 'claim': n['pending_heading'],
                                 'gap': n.get('heading_gap', False),
                                 'cut': len(anchor.squash(n['pending_heading']['text'] if first else n['rest']))}
            units.append(u)
    walk(tree)
    return units


_BR = re.compile(rb'</?br(?=[\s/>])', re.I)


def split_lines(raw, units, vis=None):
    vis = anchor.Visible(raw) if vis is None else vis
    if not vis.certain:
        for u in units: u.pop('_heading', None)
        return units
    # Scanner-emitted spaces whose original token is <br>: hidden tags,
    # comments and attribute strings never enter this inventory.
    breaks = sorted({s for c, s, e in zip(vis.text, vis.starts, vis.ends)
                     if c == ' ' and e - s > 1 and _BR.match(raw, s)})
    referenced = {ref for u in units for ref in u.get('notes') or []}
    referenced |= {link['to'] for u in units for link in u.get('links') or [] if link.get('to')}
    out = []
    for unit in units:
        pending = unit.pop('_heading', None)  # never publish an unproved split
        a, text = unit.get('anchor'), unit.get('text', '')
        if unit.get('kind') in ('table', 'image') or unit.get('id') in referenced or unit.get('links') or not text or not isinstance(a, dict) or 'byte_start' not in a:
            out.append(unit); continue
        lo, hi = bisect_left(vis.s, a['byte_start']), bisect_left(vis.s, a['byte_end_exclusive'])
        if anchor.squash(text) != vis.flat[lo:hi]:
            out.append(unit); continue
        left, right = bisect_left(breaks, a['byte_start']), bisect_left(breaks, a['byte_end_exclusive'])
        cuts = {bisect_left(vis.s, b) for b in breaks[left:right]} - {lo, hi}
        heading_cut = lo + pending['cut'] if pending else None
        # The native terminal reader can erase a real BR/block/spacer boundary.
        # Only the matched parent's exact source occurrence may restore it.
        if heading_cut is not None and lo < heading_cut < hi and (pending.get('gap') or any(vis.text[i].isspace() and i not in vis.reading_breaks for i in range(vis.idx[heading_cut-1]+1, vis.idx[heading_cut]))):
            cuts.add(heading_cut)
        else: heading_cut = None
        cuts = sorted(cuts)
        if not cuts:
            out.append(unit); continue
        idx = [i for i, c in enumerate(text) if not anchor._WS.match(c)]
        for n, (start, end) in enumerate(zip([lo] + cuts, cuts + [hi])):
            piece = dict(unit, id=unit['id'] + '_line_' + str(n),
                         text=text[idx[start-lo]:idx[end-lo-1]+1],
                         anchor={'byte_start':vis.s[start], 'byte_end_exclusive':vis.e[end-1]})
            # Every removed field is indexed into the old text; existing downstream
            # steps recompute them from this slice and its unchanged source bytes.
            for key in ('struck', 'struck_at', 'joins', '_order'): piece.pop(key, None)
            if heading_cut is not None and (end <= heading_cut if pending['first'] else start >= heading_cut):
                piece['kind'] = 'heading'
                if pending['claim'].get('level') is not None: piece['level'] = pending['claim']['level']
                if pending['claim'].get('native') is not None: piece['native_heading'] = pending['claim']['native']
            out.append(piece)
    return out


def route_for(tree, raw, file_id, sha256, seconds, version, settings=None, vis=None):
    vis = anchor.Visible(raw) if vis is None else vis; known = codes(raw, vis); linked = anchor.link(raw, to_units(tree, known), vis=vis)
    linked['units'] = split_lines(raw, linked['units'], vis)
    for u in linked['units']:
        if u.get('src') in known: u['src'] = known[u['src']][1]  # the name back, now that the tag has decided the place; a src that is no code stays the tool's own
    units = with_every_picture(linked['units'], vis); base = {'source_base': {'tag': {'byte_start': vis.base['start'], 'byte_end_exclusive': vis.base['end']}, 'href': vis.base['href']}} if vis.base else {}
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds,
            'route': {'name': NAME, 'tool': 'edgartools', 'version': version, 'settings': dict(settings or {'parse_html': 'defaults'}, pictures='every shown tag', source_lines='certified <br> breaks'), 'adapter': 'driver/prepare/convert/edgartools_html.py',
                      'linker': 'driver/prepare/convert/anchor.py'}, 'units': units, 'uncovered': linked['uncovered'], 'source_links': source_links(units, vis), **base}


def with_every_picture(units, vis):
    """Every picture the source shows stands in the output at its own tag. The tool reads a table's cells as text only and an inline run as text only, so
    a picture there got no unit (386 of 1,508 occurrences in the OCR review's 120 documents, 385 of them in cells; r12). A shown picture tag no unit
    stands at gets one from the scanner's inventory (`vis.pictures`: the same visibility state as the text, so a hidden copy gets none and lends no
    identity), with its own name, inserted before the first unit that starts after the tag — the tool's units keep their order, ids and content — and
    with the cell it stands in: the scanner's innermost cell span, the table unit that holds the cells of the same source table (where one does) and, where a cell of that
    unit stands in the picture's own cell, its row and column (the tool's grid; the screen step measures it again). The same bytes shown twice are two
    occurrences, two units. `from: source` records it as the adapter's work, not the tool's. Every picture at a shown tag, the tool's own too, gets the
    same: its cell, and the `alt` and `title` its tag writes (`vis.picture_descriptions`), beside it, never as its text (Codex, PICTURE_CONTEXT_ORDER)."""
    at = {u['anchor']['byte_start'] for u in units if u.get('kind') == 'image' and isinstance(u.get('anchor'), dict)}
    todo = [(a, b) for a, b in vis.pictures if a not in at]
    if not vis.pictures: return units
    def start(x):
        x = x[0] if isinstance(x, list) and x else x
        return x['byte_start'] if isinstance(x, dict) and 'byte_start' in x else None
    spans = sorted((a, b, k) for k, table in enumerate(vis.tables) for row in table for a, b in row); starts = [a for a, _, _ in spans]
    def cell_of(x):  # the innermost source cell holding byte x (the one that starts last among those that do), or -1
        i = bisect_right(starts, x) - 1
        while i >= 0 and not spans[i][0] <= x < spans[i][1]: i -= 1
        return i
    unit_table, route_cell = {}, {}  # source table -> the table unit holding its cells (None: cells of it in two units, no one table); source cell -> (row, column) of the unit's cell in it
    for t in units:
        for c in (t.get('cells') or []) if t.get('kind') == 'table' else []:
            i = cell_of(start(c.get('anchor'))) if start(c.get('anchor')) is not None else -1
            if i >= 0: k = spans[i][2]; unit_table[k] = t['id'] if unit_table.get(k, t['id']) == t['id'] else None; route_cell.setdefault(i, (c['r'], c['c']))
    def placed(u, a):  # a picture at its shown tag `a`: the cell it stands in, and what its tag says of it
        i = cell_of(a)
        if i >= 0:
            u['cell'] = {'byte_start': spans[i][0], 'byte_end_exclusive': spans[i][1]}
            if unit_table.get(spans[i][2]) is not None:
                u['cell']['table'] = unit_table[spans[i][2]]
                if i in route_cell: u['cell']['r'], u['cell']['c'] = route_cell[i]
        u.update(vis.picture_descriptions.get(a, {}))
        return u
    shown = {a for a, _ in vis.pictures}
    for u in units:
        if u.get('kind') == 'image' and start(u.get('anchor')) in shown: placed(u, start(u['anchor']))
    added = [placed({'id': f'p{a}', 'kind': 'image', 'text': '', 'src': vis.picture_sources.get(a), 'anchor': {'byte_start': a, 'byte_end_exclusive': b}, 'from': 'source'}, a) for a, b in todo]
    out = []
    for u in units:
        s0 = start(u.get('anchor'))
        while added and s0 is not None and added[0]['anchor']['byte_start'] < s0: out.append(added.pop(0))
        out.append(u)
    return out + added


_URL_EDGES, _URL_INSIDE = ''.join(map(chr, range(0x21))), str.maketrans('', '', '\t\n\r')  # what the URL standard drops from an href: C0 controls and spaces at its ends, tabs and line ends anywhere (a no-break space is part of the path)
_FRAGMENT_SAFE = ''.join(chr(c) for c in range(0x21, 0x7f) if chr(c) not in '"<>`')  # what the URL standard leaves as written in a fragment; a space, a quote, <, >, `, a control or any non-ASCII character it percent-encodes (UTF-8) - before the page is searched (Codex, LINK_URL_SERIALIZATION)


def source_links(units, vis):
    """Every <a href> the source writes, as source evidence beside the units, which it does not touch (Codex HREF_DESIGN_REVIEW, HREF_URL_REVIEW): the href
    as written (decoded once, nothing trimmed), its opening tag, `hidden` where it stands in a removed subtree, `certain: false` where the scanner's
    reading is not certain. Its `extent` (opening tag to its own </a>) and `owners` - every unit, table cell (by its anchor's first byte, which the
    screen step's re-grid and sort leave as it is) or picture holding what it shows, [] for nothing shown (empty, or text the page does not show; not
    `hidden`), `unheld` for shown characters no unit holds - only where the scan proves the element whole
    (`vis.links`): a link the parser splits, reopens, cuts short or moves is left unresolved, never given an owner. Where it points: a same-document
    fragment with no active <base href> names its targets as Chromium finds them - the fragment as the URL holds it (percent-encoded by the standard's
    own set), then one UTF-8 percent-decoding; ids before
    names; every duplicate - and the unit or cell a single target's own text all stands in, where that is exactly one (an empty anchor or a target
    holding several units names none); any other href, and any under a base, stays as written: no URL resolution, no member guess, no fetch."""
    items, pics = [], []  # (start, end, (unit, cell or None)) of every anchored unit and cell; pictures apart (they hold a tag, no text)
    for u in units:
        for x, cell in ([(c, True) for c in u.get('cells') or []] if u.get('kind') == 'table' else [(u, False)]):
            sp = [a for a in anchor.spans(x.get('anchor')) if 'byte_start' in a]
            (pics if u.get('kind') == 'image' else items).extend((a['byte_start'], a['byte_end_exclusive'], (u['id'], sp[0]['byte_start'] if cell else None)) for a in sp)
    items.sort(); starts = [s for s, _, _ in items]; reach = list(accumulate((e for _, e, _ in items), max))
    owner = lambda key: {'unit': key[0]} if key[1] is None else {'unit': key[0], 'cell': key[1]}

    def held(lo, hi):  # each unit or cell holding visible characters of [lo, hi): {key: (first such character, how many)}, how many there are, how many none holds
        chars, got, covered = vis.s[bisect_left(vis.s, lo):bisect_left(vis.s, hi)], {}, set()
        i = bisect_right(starts, chars[-1]) - 1 if chars else -1
        while i >= 0 and reach[i] > chars[0]:
            s, e, key = items[i]; a, b = bisect_left(chars, s), bisect_left(chars, e)
            if b > a: first, n = got.get(key, (chars[a], 0)); got[key] = (min(first, chars[a]), n + b - a); covered.update(range(a, b))
            i -= 1
        return got, len(chars), len(chars) - len(covered)

    def target(t):  # the one unit or cell that holds all of a target's own text
        if t['end'] is None: return None
        got, n, unheld = held(t['start'], t['end'])
        return owner(next(iter(got))) if n and not unheld and len(got) == 1 and next(iter(got.values()))[1] == n else None

    def destination(href):
        url = href.strip(_URL_EDGES).translate(_URL_INSIDE)
        if vis.base is not None or not url.startswith('#'): return {'kind': 'as_written'}
        frag = quote(url[1:], safe=_FRAGMENT_SAFE)  # the fragment as the URL holds it
        if not frag: return {'kind': 'same_document', 'targets': [], 'status': 'top'}  # a bare #: the top of the page, whatever has an empty id or name
        for key in dict.fromkeys((frag, unquote(frag, errors='replace'))):  # as the URL holds it first, then once decoded (Chromium, LINK_URL_CONTROLS)
            for by, found in (('id', vis.ids), ('name', vis.names)):
                if key in found:
                    hits = found[key]
                    return {'kind': 'same_document', 'by': by, 'targets': [t['start'] for t in hits], 'status': 'one' if len(hits) == 1 else 'several', 'owner': target(hits[0]) if len(hits) == 1 and vis.certain else None}
        return {'kind': 'same_document', 'targets': [], 'status': 'top' if unquote(frag, errors='replace').lower() == 'top' else 'none'}

    out = []
    for l in vis.links:
        rec = {'href': l['href'], 'tag': {'byte_start': l['start'], 'byte_end_exclusive': l['tag_end']}, **({'hidden': True} if l['hidden'] else {}), **({} if vis.certain else {'certain': False})}
        whole = vis.certain and not l['hidden'] and l['whole'] and l['end'] is not None
        rec['extent'] = {'byte_start': l['start'], 'byte_end_exclusive': l['end']} if whole else None
        if whole:
            got, _, unheld = held(l['tag_end'], l['end'])
            found = sorted([(first, key) for key, (first, _) in got.items()] + [(s, k) for s, e, k in pics if l['tag_end'] <= s and e <= l['end']])
            rec['owners'] = [owner(k) for _, k in found]
            if unheld: rec['unheld'] = unheld  # shown characters of it that no unit holds (the linker left them uncovered): said, not dropped
        else: rec['owners'] = None
        rec['destination'] = destination(l['href']); out.append(rec)
    return out


def unsupported(file_id, sha256, version, status='UNSUPPORTED', error='not an HTML file'):
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': status, 'error': error, 'seconds': 0,
            'route': {'name': NAME, 'tool': 'edgartools', 'version': version, 'settings': {}, 'adapter': 'driver/prepare/convert/edgartools_html.py', 'linker': None}, 'units': []}


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
    from edgar.documents.nodes import ContainerNode, HeadingNode, TextNode, _has_left_gap
    from edgar.documents.strategies import document_builder as db
    from edgar.documents.processors.preprocessor import HTMLPreprocessor as P
    from edgar.documents.strategies.style_parser import StyleParser
    from edgar.documents.utils import get_cache_manager
    if getattr(db.DocumentBuilder, '_whole_headings', False): return
    H, PARTS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'), {'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'caption', 'colgroup', 'col', 'ul', 'ol', 'li', 'dl', 'dt', 'dd'}
    try:
        create, read = db.DocumentBuilder._create_node_for_element, db.DocumentBuilder._get_element_text
        compile_ = P._compile_patterns
        skipped, inline = db.DocumentBuilder.SKIP_ELEMENTS - {'ix:exclude'}, db.DocumentBuilder.INLINE_ELEMENTS | {'ix:exclude'}
        parse_style, clear_styles = StyleParser.parse, get_cache_manager().style_cache.clear
        apply_style, read_length = StyleParser._apply_property, StyleParser._parse_length
    except AttributeError as exc:
        raise ImportError("required EdgarTools preparation hooks are unavailable") from exc
    def line(self, element, style):  # a block the tool may take for one line of heading: not inline by tag, not laid out inline, not a table or list part, nothing but inline runs in it, no table or picture under it
        tag = element.tag.lower() if isinstance(element.tag, str) else ''
        return tag and tag not in H and tag not in self.INLINE_ELEMENTS and tag not in PARTS and not tag.startswith(('ix:', '{')) and getattr(style, 'display', None) not in ('inline', 'inline-block') \
            and not any(isinstance(d.tag, str) and d.tag.lower() in ('table', 'img') for d in element.iterdescendants())
    def whole(self, element):
        kept, element.tag = element.tag, 'h1'  # the tool reads an <h1> whole: the same reading for the block it takes for one
        try: return read(self, element)
        finally: element.tag = kept
    def runs(self, element):  # nothing below but inline text runs — inline by tag, an inline-XBRL fact, or laid out inline by its own style, the tool's own notions; a link or a picture keeps the tool's traversal (as for inline facts)
        return all(not isinstance(d.tag, str) or d.tag.lower() not in ('a', 'img') and (d.tag.lower() in self.INLINE_ELEMENTS or d.tag.lower().startswith('ix:') or getattr(self._extract_style(d), 'display', None) in ('inline', 'inline-block')) for d in element.iterdescendants())
    def left_gap(self, element):
        # Use the existing CSS cascade and native length/box reader. Unknown
        # or negative spacing cannot prove a gap; never retain a stale positive.
        parsed = self.style_parser.parse('')
        for prop, value, _ in sorted(anchor.declarations(element.get('style', '')), key=lambda d: d[2]):
            if prop not in ('margin', 'margin-left', 'padding', 'padding-left'): continue
            parts = value.split()
            if not 1 <= len(parts) <= (1 if prop.endswith('-left') else 4): return None
            lengths = [read_length(self.style_parser, p) for p in parts]
            if any(n is None or n < 0 or n != 0 and anchor._number(p) for p, n in zip(parts, lengths)): return None
            apply_style(self.style_parser, parsed, prop, value)
        return _has_left_gap(SimpleNamespace(style=parsed))
    def creating(self, element, style):
        tag = element.tag.lower() if isinstance(element.tag, str) else ''
        if tag in self.INLINE_ELEMENTS and any(d.tag == 'table' for d in element.iterdescendants()):
            return ContainerNode(tag_name=element.tag, style=style)  # a table stays structural through inline wrappers
        if tag.startswith('ix:') and tag in self.INLINE_ELEMENTS and any(c.tag in self.BLOCK_ELEMENTS or c.tag in ('table', 'div', 'p') for c in element if hasattr(c, 'tag')):
            return ContainerNode(tag_name=element.tag, style=style)  # an inline-XBRL element holding blocks is a container — the tool's own rule for ix:nonNumeric and ix:continuation; the tool read an ix:footnote's table as one string ("2025202420252024")
        inline = tag not in self.INLINE_ELEMENTS and getattr(style, 'display', None) in ('inline', 'inline-block') and (element.text or '').strip() and any(isinstance(c.tag, str) for c in element)  # a block laid out inline with text of its own and elements: the tool kept that text only ("…on Form" lost "8-K does not constitute…"); without text of its own it walks the children itself
        whole_run = inline and runs(self, element); self._run = element if whole_run else None
        self._making = (element, style) if line(self, element, style) and self._is_text_only_container(element) and not (element.text or '').strip() and len(element) and not (element[0].text_content() or '').strip() else None  # (a): only where the block's text begins after an element holding nothing — the branch the tool's reader loses
        try: node = create(self, element, style)
        finally: self._making = self._run = None
        if isinstance(node, HeadingNode) and line(self, element, style): node.content = whole(self, element)  # (b): every heading the tool made from a block, read whole
        if tag == 'table' and type(node).__name__ == 'TableNode' and element.get(TABLE): node.set_metadata(TABLE, element.get(TABLE))  # the table's code (named), kept in the tool's own metadata for dump (A3)
        if inline and not whole_run and getattr(node, 'metadata', {}).get('inline_via_css'): node = ContainerNode(tag_name=element.tag, style=style)  # blocks below: the tool's own fallback for an inline-laid block, each child walked — nothing dropped
        if isinstance(node, (TextNode, HeadingNode)) and isinstance(node.content, str):
            # A terminal wrapper hides its descendants from ParagraphNode's
            # own gap check. Keep this private claim only for an anchored
            # heading seam, without changing the node's text or own Style.
            first = next((t for t in element.xpath('.//text()') if str(t).strip()), None) if len(element) else None
            parent = first.getparent() if first is not None else element
            if first is not None and first.is_tail: parent = parent.getparent()
            gap = False
            while parent is not None and first is not None:
                value = left_gap(self, parent)
                if value is None: gap = False; break
                gap |= value
                if parent is element: break
                parent = parent.getparent()
            if gap: node._prepare_left_gap = True
        return node
    def reading(self, element):
        # The tool treats inline XBRL as terminal text but its reader only walks
        # descendants for inline HTML tags. Reuse that reader for inline facts;
        # containers with blocks, pictures, or links keep the tool's traversal.
        # A fact with no element inside too: read as terminal text it lost the spaces at its edges, which the page shows ("North Carolina 27703" became
        # "Carolina27703"); read as a run it keeps them (Codex, accuracy-fable-1 A2)
        if element is getattr(self, '_run', None) or isinstance(element.tag, str) and element.tag.lower() in ('ix:nonnumeric', 'ix:continuation') and not any(
                isinstance(d.tag, str) and d.tag.lower() in self.BLOCK_ELEMENTS | {'table', 'img', 'a'} for d in element.iterdescendants()):
            kept, element.tag = element.tag, 'span'
            try: return read(self, element)
            finally: element.tag = kept
        made = getattr(self, '_making', None)
        return whole(self, element) if made and made[0] is element else read(self, element)  # (a)
    def independent_style(self, style_string):
        # The native cache returns one mutable Style for every equal CSS string.
        # The builder adds bold/italic/underline/align to it; keep those changes
        # local to their element, on cache misses as well as hits.
        return copy(parse_style(self, style_string))
    clear_styles()  # once: a native caller may already have polluted old entries
    StyleParser.parse = independent_style
    db.DocumentBuilder._create_node_for_element, db.DocumentBuilder._get_element_text = creating, reading
    def patterns(self):  # the tool's cleaner deleted every white space before . , ; ! ? in the raw page ("1,855,579 ,941,411" became one number, "Sections .13, .14"
        found = compile_(self); found['space_before_punct'] = re.compile(r'(?!)()'); return found  # "Sections.13,.14"); the page prints the space and so does the route: a pattern that never matches (its replacement names group 1)
    P._compile_patterns = patterns
    # The tool deletes any element whose whole text is a short number, a roman numeral or "Page N" when its style looks like a footer (centered or
    # right-aligned, a bottom margin, a page break near): a cover ZIP code, a right-aligned "125" under "Shares outstanding", a tagged shares fact and a
    # debt class "IV" were lost with the page numbers (Codex, accuracy-fable-1). Nothing is deleted here: what the page shows stays, in source order.
    db.DocumentBuilder._is_page_number_container = lambda self, element: False
    # <ix:exclude> marks shown text that belongs to no XBRL fact - a scale line "(in thousands)", the "not" inside a tagged sentence. The tool skipped it
    # (its SKIP_ELEMENTS), so what the page shows was deleted; it is read as the tool reads its other inline-XBRL tags: inline in its sentence, a
    # container where it holds blocks or a table (the rules above); hidden is still hidden (Codex, accuracy-fable-1 A4)
    db.DocumentBuilder.SKIP_ELEMENTS, db.DocumentBuilder.INLINE_ELEMENTS = skipped, inline
    db.DocumentBuilder._whole_headings = True


SETTINGS = {'parse_html': 'defaults', 'retain_pictures': True, 'retain_native_heading_evidence': True, 'picture_names': 'codes', 'hidden_text': 'left out', 'headings': 'detected blocks read whole', 'inline_facts': 'read whole', 'page_number_candidates': 'kept', 'ix_exclude': 'read as shown', 'inline_fact_spaces': 'kept', 'table_identity': 'own start tag', 'style_values': 'independent', 'heading_boundaries': 'source matched'}  # what this route does, recorded in every route and with every saved parse: a parse saved under other settings is not reused


def version():
    import importlib.metadata as md
    return f"edgartools {md.version('edgartools')}"


def parse(raw, vis):
    """The tool's own parse of the caller's bytes - the pictures' names given as codes (`named`), its reading of headings fixed (`whole_headings`) - as
    a plain node dump: (dump, seconds, producing version)."""
    from edgar.documents import parse_html  # only here: the rest of the module needs no EdgarTools
    whole_headings(); t0 = time.time()
    tree = dump(parse_html(named(raw, vis, codes(raw, vis))).root)
    return tree, round(time.time() - t0, 2), version()


def convert(raw, file_id, sha256, parse=parse):
    """One HTML document into its route (the caller's bytes): scanned, parsed by the tool, adapted and linked to the source (`route_for`). A document parse error is a
    FAILED route; source-identity, storage, dependency and resource failures stop the caller. `parse(raw, vis)` -> (dump, seconds, version) is the tool call; the command line passes one that reuses its saved parses."""
    anchor.check_source(raw, sha256)
    vis = anchor.Visible(raw)
    try: tree, seconds, made_by = parse(raw, vis)
    except (OSError, StorageError, ImportError, MemoryError): raise
    except Exception as e: return unsupported(file_id, sha256, version(), 'FAILED', repr(e)[:300])
    return route_for(tree, raw, file_id, sha256, seconds, made_by, SETTINGS, vis)
