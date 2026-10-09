"""Screen-span step (an allowed small adapter, PrepareStep.md P20/T1): the labellers' guide says a header covers a value
when the value sits inside the header's span ON SCREEN (guide 3.5 rule 3). DOM colspans can disagree with the screen
(spacer columns, hidden cells), and every HTML tool inherits the DOM grid. This step renders the original in headless
Chrome, measures every table cell's box, derives screen columns from the pixel edges, and re-grids a route's table
cells by their byte anchors, and joins a word or number the tool printed with a space the source does not have where Chrome shows its two
characters touching on one baseline (a space the tool adds across inline markup: `CORP ORATION` over an iXBRL tag; the page alone can tell that from
a gap its styles make); and, the mirror, sets a space in where the tool printed touching two characters the source reads apart and Chrome lays them apart
on one baseline (positioned boxes `1.` and `10700` printed `1.10700`). It changes no anchor; the text records where its spaces were. Rules are geometric only.
In the same render, `source_symbols` keeps the meaning of a symbol font's code characters beside the units, which it does not touch: the pinned decoder
(dingbat-to-unicode 1.0.2, its published files unchanged) reads each character the page sets in a typeface it knows (`Yes þ No ¨` in Wingdings:
BALLOT BOX WITH BOLD CHECK, LIGHT WHITE SQUARE), with its exact source bytes and the units that hold them."""
import hashlib
import json
import re
import time
import unicodedata
from bisect import bisect_left, bisect_right
from pathlib import Path

from driver.prepare.convert import anchor, edgartools_html
from driver.prepare.get.acquire import StorageError
from driver.prepare.convert.anchor import Visible

_CELL_END = re.compile(rb'(?i)</t[dh]\s*>')
TOL = 2  # pixels: edges closer than this are the same column edge
_DECODER = {'dist/dingbats.js': '5d99a6ab462352f6a6b2c2ce1dd9062821a0c211b41bbe7249bef631df1e05d6', 'dist/index.js': '92af15874a7bc360f8f7727055a0d8db6fd81906a050a6976fede4e8f4786213',
            'LICENSE': '1013cef4b629a3c7eaf737c110fb5bebbf3abbc16e154d769468d71c3653fa37', 'package.json': '83b29019feaf00315f9c90953a2d10db9dc449a048c5a25462c9e6716d0251a2'}  # the npm tarball's files (sha256 3ff52fb8… of the .tgz)


def _decoder_js():
    """The pinned decoder as the page runs it: its two published modules, checked byte for byte, under a minimal CommonJS shim (the page has no module
    system); `lib.codePoint(typeface, code)` and `lib.faces`, the typefaces its table knows."""
    src = {}
    for name, digest in _DECODER.items():
        data = (Path(__file__).with_name('dingbat_to_unicode_1_0_2') / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest: raise ImportError(name + ': not the pinned dingbat-to-unicode 1.0.2')
        src[name] = data.decode()
    load = 'const load = (code, req) => { const module = {exports: {}}; new Function("exports", "require", "module", code)(module.exports, req, module); return module.exports; };'
    return ('const lib = (() => { ' + load + ' const tables = load(' + json.dumps(src['dist/dingbats.js']) + ', null);'
            ' return {codePoint: load(' + json.dumps(src['dist/index.js']) + ', () => tables).codePoint, faces: Object.keys(tables.default)}; })();')


def gaps_of(vis, units):
    """Every space the tool added inside a word or number, and every boundary it dropped where a space parts two words or numbers the source reads apart,
    per item: [(item, text start, text end, search-form index before, after)]; a dropped boundary is the empty range at its place (anchor.tool_spaces,
    anchor.tool_joins)."""
    return [(x, a, b, k, l) for u in units for x in ((u.get('cells') or []) if u.get('kind') == 'table' else [u]) for a, b, k, l in anchor.tool_spaces(vis, x) + anchor.tool_joins(vis, x)]


def endpoints_of(vis, units):
    gaps=[]
    for item in units:
        if item.get('kind') in ('image','table') or not item.get('text'): continue
        aa=anchor.spans(item.get('anchor'))
        if not aa or not all('byte_start' in a for a in aa):continue
        start,end=min(a['byte_start'] for a in aa),max(a['byte_end_exclusive'] for a in aa)
        k,l=bisect_left(vis.s,start),bisect_left(vis.e,end)
        if k>=len(vis.s) or l>=len(vis.e) or vis.s[k]!=start or vis.e[l]!=end:continue
        if (k + 1 < len(vis.s) and vis.s[k + 1] == start) or (l + 1 < len(vis.e) and vis.e[l + 1] == end): continue
        gaps.append(({'start':start,'end':end},0,0,k,l))
    return gaps


def tag_cells(raw, vis=None, gaps=(), marks=(), prefix='', cells=True):
    """A copy with data-g="n" on every <td>/<th> (document order) and the byte span of each cell in the original; and, for each gap, a comment <!--j:n.0-->
    / <!--j:n.1--> right before the character before and after it — a comment is no element: no stylesheet rule and no structural selector sees it, the
    page lays out exactly as before (Codex C2), and the page's own range over the character that follows it is measured. `cells`: False for a copy
    with no attribute added (comments only: a sheet can select an attribute; spans then none). `marks`: (byte, comment) pairs
    set in as given (the symbol runs' marks); `prefix` (`marker_prefix`) begins every comment the step writes, so none the source writes stands for one."""
    vis = Visible(raw) if vis is None else vis
    spans = sorted((a, b) for table in vis.tables for row in table for a, b in row) if cells else []  # the scanner's cells: the parser's own, where a plain search for the tags ran a cell with no end tag on to the next cell anywhere (Codex G2-C3)
    edits = []
    for n, (start, end) in enumerate(spans):
        close = _CELL_END.match(raw, end); spans[n] = (start, close.end() if close else end)  # with its own end tag, where it has one
        edits.append((start + 3, b' data-g="%d"' % n))
    for n, (_, _, _, k, l) in enumerate(gaps):
        for side, c in ((0, k), (1, l)): edits.append((vis.s[c], b'<!--%sj:%d.%d-->' % (prefix.encode(), n, side)))
    edits.extend(marks)
    out, pos = [], 0
    for at, piece in sorted(edits, key=lambda e: e[0]): out += [raw[pos:at], piece]; pos = at
    out.append(raw[pos:])
    return b''.join(out), spans


def join(gaps, boxes, vis=None, tol=0.75):
    """Remove from each item's text the added spaces whose two characters Chrome lays out on one baseline, touching (the boxes' bottoms within a pixel — their
    tops may differ, a smaller font on the same baseline as small capitals print; the right box begins where the left one ends, within `tol` pixels); and,
    the mirror, set one space in at each dropped boundary whose two characters Chrome lays out on one baseline apart (further than `tol`: positioned boxes
    `1.` and `10700` printed `1.10700`); returns how many. Each item keeps `joins`: [[start, end, gap in pixels]] and `parts`: [[place, gap in pixels]] in the text as it was; its struck places, which count the
    text's characters, are read again from the source (`vis`; Codex C3) — or dropped where that cannot be done."""
    by_item, n = {}, 0
    for g, (x, a, b, k, l) in enumerate(gaps):
        left, right = boxes.get('%d.0' % g), boxes.get('%d.1' % g)
        if not left or not right or abs(left['b'] - right['b']) > 1: continue  # not one baseline: another line, or a raised or lowered mark ($5¹, CO₂ stay apart; 6ᵗʰ stays together)
        gap = right['x'] - left['r']
        if a < b and not -tol <= gap <= tol: continue  # the page spaces them (its styles), or lays them apart: no join
        if a == b and not (gap > tol and left.get('shown') and right.get('shown')): continue  # a dropped boundary comes back only where both are shown and the right one begins clearly after the left: touching, an overlap or a reversed pair is no gap
        by_item.setdefault(id(x), (x, []))[1].append((a, b, round(gap, 2)))
    for x, runs in by_item.values():
        text = x['text']
        for a, b, _ in sorted(runs, reverse=True): text = text[:a] + ('' if a < b else ' ') + text[b:]
        x['text'] = text; n += len(runs)
        for key, got in (('joins', [[a, b, g] for a, b, g in sorted(runs) if a < b]), ('parts', [[a, g] for a, b, g in sorted(runs) if a == b])):
            if got: x[key] = got
        if 'struck_at' in x:
            at = anchor.struck_at(vis, x) if vis is not None else None
            if at: x['struck_at'] = at
            else: x.pop('struck_at')
    return n


def screen_grid(cells):
    """{g: (row, column, span)} from measured boxes of one table: columns are the distinct left edges of visible cells."""
    shown = [c for c in cells if c['w'] > 0]
    edges = []
    for x in sorted(c['x'] for c in shown):
        if not edges or x - edges[-1] > TOL: edges.append(x)
    grid = {}
    for c in shown:
        col = max(i for i, e in enumerate(edges) if e <= c['x'] + TOL)
        span = sum(1 for e in edges[col + 1:] if e < c['x'] + c['w'] - TOL) + 1
        grid[c['g']] = (c['row'], col, span)
    return grid


def apply(units, spans, measured_by_table):
    """Re-grid the route's table cells whose byte anchors fall in a measured cell; returns how many changed. A table whose every cell is measured in
    one source table is then listed row by row, as the route's cells are (DESIGN §4): the tool may list rows in another order than the page. A picture
    in a cell of such a table takes its own cell's measured row, column and spans (its rows where the browser's table model ends them), as a text cell
    there would, an image-only cell too; a picture in any other route table states none, its cell span kept: a row and column copied before this step
    are the tool's grid, which the step replaced (a hidden or zero-width column), and a table holding cells of two grids has no one row or column
    (Codex, PICTURE_CONTEXT_ORDER)."""
    starts = [s for s, _ in spans]; by_g, table_of = {}, {}
    parents, stack = [], []  # the cell each cell stands in (a table inside a cell): text after the inner table is the outer cell's again (Codex's worktree)
    for g, (start, end) in enumerate(spans):
        while stack and spans[stack[-1]][1] <= start: stack.pop()
        parents.append(stack[-1] if stack else -1); stack.append(g)
    for t, table_cells in measured_by_table.items():
        for g, (r, c, cs) in screen_grid(table_cells).items(): by_g[g] = (r, c, cs); table_of[g] = t
    rows = {c['g']: c.get('rs', 1) for table_cells in measured_by_table.values() for c in table_cells}  # each cell's rows as the browser's table model ends them (for pictures: a text cell keeps the tool's)
    n, grid = 0, {}  # grid: route table -> the one measured table all its cells stand in, else None
    for u in units:
        if u.get('kind') != 'table': continue
        tables = set()  # the measured table each cell stands in; None: a cell not measured
        for cell in u.get('cells') or []:
            a = cell.get('anchor'); a = a[0] if isinstance(a, list) else a
            if not isinstance(a, dict) or 'byte_start' not in a: tables.add(None); continue
            g = bisect_right(starts, a['byte_start']) - 1
            while g >= 0 and a['byte_start'] >= spans[g][1]: g = parents[g]
            if g < 0 or not (spans[g][0] <= a['byte_start'] < spans[g][1]) or g not in by_g: tables.add(None); continue
            r, c, cs = by_g[g]
            if (cell['r'], cell['c'], cell.get('cs', 1)) != (r, c, cs): cell.update(r=r, c=c, cs=cs); n += 1
            cell['grid'] = 'screen'; tables.add(table_of[g])
        grid[u.get('id')] = next(iter(tables)) if len(tables) == 1 and None not in tables else None
        if grid[u.get('id')] is not None: u['cells'].sort(key=lambda x: (x['r'], x['c']))  # stable: cells that share a place keep their order; a table with a cell not measured, or measured in two tables (one inside the other), keeps the tool's order
    for u in units:
        cell = u.get('cell') if u.get('kind') == 'image' else None
        if not isinstance(cell, dict) or 'table' not in cell: continue  # no route table: no place to state in one
        g, t = bisect_left(starts, cell['byte_start']), grid.get(cell['table'])
        if t is not None and g < len(starts) and starts[g] == cell['byte_start'] and table_of.get(g) == t: r, c, cs = by_g[g]; cell.update(r=r, c=c, rs=rows[g], cs=cs)
        else:
            for k in ('r', 'c', 'rs', 'cs'): cell.pop(k, None)
    return n


JS = """(p) => { p = p || ''; const tables = Array.from(document.querySelectorAll('table')); const out = []; const gap = new RegExp('^' + p + 'j:([0-9]+[.][01])$');
  for (const el of document.querySelectorAll('td[data-g], th[data-g]')) { const r = el.getBoundingClientRect(); const t = el.closest('table'); const tr = el.parentElement;
    const rest = tr && tr.parentElement && tr.parentElement.rows ? tr.parentElement.rows.length - tr.sectionRowIndex : 1;  // the rows left in its row group, where the table model ends a cell: rowspan="0" runs to there, a larger one stops there
    out.push({g: +el.dataset.g, table: tables.indexOf(t), row: tr ? tr.rowIndex : -1, x: r.left, w: r.width, rs: el.rowSpan === 0 ? rest : Math.min(el.rowSpan, rest)}); }
  const boxes = {}; const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT);
  for (let c = w.nextNode(); c; c = w.nextNode()) { const m = gap.exec(c.data); if (!m) continue; let t = c.nextSibling; while (t && t.nodeType === Node.COMMENT_NODE) t = t.nextSibling;  // one character can end one gap and begin the next: its two marks stand side by side
    if (!t || t.nodeType !== Node.TEXT_NODE || !t.data.length) continue;
    let shown = getComputedStyle(t.parentElement).visibility === 'visible';
    for (let el = t.parentElement; el && shown; el = el.parentElement) if (+getComputedStyle(el).opacity === 0) shown = false;
    const r = document.createRange(); r.setStart(t, 0); r.setEnd(t, 1); const rs = r.getClientRects();
    if (rs.length === 1) boxes[m[1]] = {shown, x: rs[0].left, r: rs[0].right, t: rs[0].top, b: rs[0].bottom}; }
  return {cells: out, boxes}; }"""


SYMBOLS_JS = "([p, every]) => { " + _decoder_js() + """ const marks = {}, faces = [], plain = [], inline = {}, lifts = new Map(), mark = new RegExp('^' + p + 's:([0-9]+)$');  // every: each run measured, an ordinary one too (page_visibility)
  for (const f of document.fonts) faces.push(f.family.replace(/^["']|["']$/g, '').toUpperCase());  // typefaces the document defines itself (@font-face)
  const lift = el => { if (!el) return null; if (lifts.has(el)) return lifts.get(el);  // an element's and its ancestors' raised or lowered evidence, nearest first (null: none), each element's style read once:
    const cs = getComputedStyle(el), tag = el.localName, up = lift(el.parentElement);  // a sup or sub, whatever its computed style; a plain inline box whose computed vertical-align is not baseline; any other inline box
    const got = tag === 'sup' || tag === 'sub' || (cs.display.startsWith('inline') && cs.verticalAlign !== 'baseline' && (cs.display === 'inline' ||  // only where it is super, sub or a number (Typed OM: a length, percentage, calc or zero), never
      cs.verticalAlign === 'super' || cs.verticalAlign === 'sub' || el.computedStyleMap().get('vertical-align') instanceof CSSNumericValue)) ? [{tag, display: cs.display, vertical_align: cs.verticalAlign}].concat(up || []) : up;  // an alignment keyword (a whole inline table set text-bottom; root, ROOT_NATIVE_PREDICATE)
    lifts.set(el, got); return got; };
  const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT);
  for (let c = w.nextNode(); c; c = w.nextNode()) { const m = mark.exec(c.data); if (!m) continue;
    let text = '', el = null, first = null, last = null, n = c.nextSibling;  // the run's text: the text nodes after its mark, across inserted comments, to an element or the next run's mark
    for (; n && (n.nodeType === Node.TEXT_NODE || (n.nodeType === Node.COMMENT_NODE && !mark.test(n.data))); n = n.nextSibling) if (n.nodeType === Node.TEXT_NODE) { text += n.data; el = n.parentElement; first = first || n; last = n; }
    if (!el) { marks[m[1]] = null; continue; }  // the parser moved the run away from its mark (a table's foster parent): unbound
    const cs = getComputedStyle(el), fam = cs.fontFamily.toUpperCase(), chars = Array.from(text);
    const face = lib.faces.find(f => { const k = f.indexOf(' ') < 0 ? f : '"' + f + '"'; return fam === k || fam.startsWith(k + ', '); }) || null;  // the primary family, as Chrome writes it
    const ordinary = !face && !/[\\uE000-\\uF8FF\\u{F0000}-\\u{10FFFD}]/u.test(text), lifted = lift(el);
    const shows = () => { const r = document.createRange(); r.setStart(first, 0); r.setEnd(last, last.length); const rs = Array.from(r.getClientRects());  // the glyphs' own boxes, not the element's
      let seen = getComputedStyle(el).visibility === 'visible'; for (let a = el; a && seen; a = a.parentElement) if (+getComputedStyle(a).opacity === 0) seen = false;  // the gap marks' rule
      return !rs.length || !seen ? 'hidden' : rs.some(q => q.width > 0 && q.height > 0) ? 'shown' : 'unproven'; };
    let visibility = lifted ? shows() : null;
    if (lifted) inline[m[1]] = {text, visibility, ancestors: lifted};  // raised or lowered: kept apart from the symbol records, before the ordinary-font exit
    if (ordinary && !every) { plain.push(m[1]); continue; }  // ordinary text: nothing a symbol record could say (its id only: a large result is slow to leave the page)
    visibility = visibility || shows();
    if (ordinary) { marks[m[1]] = {text, visibility}; continue; }  // every run measured: an ordinary one says only its text and whether it shows
    marks[m[1]] = {text, family: cs.fontFamily, face, visibility,
      changed: cs.textTransform !== 'none' || cs.fontVariant !== 'normal' || cs.fontFeatureSettings !== 'normal',
      pseudo: !!face && (() => { for (let a = el; a; a = a.parentElement) { const own = getComputedStyle(a); for (const ps of ['::first-letter', '::first-line']) { const q = getComputedStyle(a, ps);  // a block's first letter or line set another way
        if (q.fontFamily !== own.fontFamily || q.textTransform !== own.textTransform || q.fontVariant !== own.fontVariant || q.fontFeatureSettings !== own.fontFeatureSettings) return true; } } return false; })(),
      decoded: face ? chars.map(ch => { let k = ch.codePointAt(0); if (k >= 0xF020 && k <= 0xF0FF) k -= 0xF000; const r = k <= 0xFF ? lib.codePoint(face, k) : undefined; return r ? r.codePoint : null; }) : null}; }
  return {marks, faces, plain: plain.join(','), inline}; }"""


def marker_prefix(raw):
    """The prefix of every comment the step writes: a digest of the source that the source's bytes nowhere contain (a comment can be written many ways,
    `<!x>` too), so no source comment can stand for a gap's or a run's mark."""
    k = hashlib.sha256(raw).hexdigest(); n = 8
    while k[:n].encode() in raw: n += 1
    return 'm' + k[:n]


def symbol_runs(raw, vis):
    """The runs a page may set in one font: the scanner's characters (`text`, `starts`, `ends`: source white space included) with no markup between
    their bytes, and the hidden text spans, contiguous ones together; as [(mark byte, [(start, end) of each source character], hidden, marked)], and the
    spans the page shows but the scan never reads (<noscript>). A synthetic character (a block's or a strike's space) carries markup bytes: never one.
    One reference read as two characters (&NotEqualTilde;) is one source character. A run in any raw-text or RCDATA body (html_tokens' literal text:
    <textarea>, <title>, <script>, <style>, …, a hidden one too) is never marked: a comment there would be text."""
    runs = []
    for s, e in zip(vis.starts, vis.ends):
        if raw[s:s + 1] == b'<' or runs and (s, e) == runs[-1][1][-1]: continue
        if runs and not runs[-1][2] and b'<' not in raw[runs[-1][1][-1][1]:s]: runs[-1][1].append((s, e))
        else: runs.append((s, [(s, e)], False))
    for a, b in vis.hidden:  # a reference, or literal text split into its UTF-8 characters (whole where it is not UTF-8)
        try: text, chars = (None, [(a, b)]) if raw[a:a + 1] == b'&' else (raw[a:b].decode(), [])
        except UnicodeDecodeError: text, chars = None, [(a, b)]
        for ch in text or '':  # one running byte offset: linear (root, ROOT_FONT_HIDDEN_COST_DEVELOPMENT)
            n = len(ch.encode()); chars.append((a, a + n)); a += n
        if not chars: continue
        if runs and runs[-1][2] and runs[-1][1][-1][1] == chars[0][0]: runs[-1][1].extend(chars)
        else: runs.append((chars[0][0], chars, True))
    ends, literal, unread, pos = [], [], [], 0
    for t, kind, lit in anchor.html_tokens(raw.decode('latin-1')):  # latin-1: one character per byte, so positions are bytes
        pos += len(t)
        if kind == 'noscript' and lit: unread.append({'byte_start': pos - len(t), 'byte_end_exclusive': pos, 'why': 'noscript'})  # the page shows it (scripts off); the scan does not read it
        if lit: literal.append((pos - len(t), pos))
        elif t[:1] == '<' and t[1:2] and (t[1].isalpha() or t[1] in '/!?'): ends.append(pos)  # a tag, comment or declaration ends here: text starts
    def at(a):  # a run's mark stands where its text starts after markup, so it never splits the text Chrome lays out (a split moves glyphs 1/64 px)
        i = bisect_right(ends, a) - 1; return ends[i] if i >= 0 else 0
    return [(at(a), chars, hidden, not any(x <= a < y for x, y in literal)) for a, chars, hidden in sorted(runs)], unread


def _char(b):  # one source character's text as the parser decodes it (anchor.text_reference); None where its bytes are not UTF-8 (never kept as Unicode)
    try: return anchor.text_reference(b.decode()) if b[:1] == b'&' else b.decode('utf-8')
    except UnicodeDecodeError: return None


def _glyphs(raw, chars):  # a run's source characters with their text, and those of them that are not white space CSS collapses
    every = [((s, e), _char(raw[s:e])) for s, e in chars]
    return every, [(x, g) for x, g in every if g is None or g.strip(anchor._SPACE)]


def _bound(glyphs, text):  # the DOM text a mark reached is exactly its own run's characters, white space CSS collapses aside: missing, moved or misread text is not
    return [ch for _, g in glyphs for ch in (g if g is not None else '\ufffd')] == [ch for ch in text if ch not in anchor._SPACE]


def symbols(raw, vis, runs, got, units):
    """`source_symbols` records from the page's marks (`SYMBOLS_JS`): each glyph of a run the page sets in a decoder typeface, and each private-use
    glyph in any other, by its own bytes; owners as the source links' (`_holders`), null where hidden or not every character is held. A run its mark
    does not reach whole (unbound) or may not carry a mark (literal text) is one unresolved record, never matched by text."""
    _, _, owners = edgartools_html._holders(units, vis); out = []; plain = set(got.get('plain', '').split(','))
    for k, (a, chars, hidden, marked) in enumerate(runs):
        if marked and str(k) in plain: continue  # bound or not, a run in an ordinary font with no private-use character carries no symbol
        m = got['marks'].get(str(k)) if marked else None  # None: the mark's text was moved away (null) or the mark was never found (absent)
        every, glyphs = _glyphs(raw, chars)  # only the white space CSS collapses is left out
        cps = [(i, ch) for i, (_, g) in enumerate(glyphs) for ch in (g if g is not None else '\ufffd')]
        dom = [(ch, d) for ch, d in zip(m['text'], m['decoded'] or [None] * len(m['text'])) if ch not in anchor._SPACE] if m else None
        if m is None or not _bound(glyphs, m['text']):
            if glyphs and not hidden:
                s0, e0 = glyphs[0][0][0], glyphs[-1][0][1]
                out.append({'at': {'byte_start': s0, 'byte_end_exclusive': e0}, 'raw': ''.join(g if g is not None else '\ufffd' for (x, g) in every if s0 <= x[0] < e0), 'status': 'unresolved',
                            'why': 'literal text' if not marked else 'unbound' if str(k) in got['marks'] else 'mark not found', 'owners': None, **({} if vis.certain else {'certain': False})})  # the source text as written, spaces kept
            continue
        ds = [[] for _ in glyphs]
        for (j, _), (_, d) in zip(cps, dom): ds[j].append(d)  # each glyph's decoded code points
        for i, ((s, e), g) in enumerate(glyphs):
            private = g is not None and any(unicodedata.category(c) == 'Co' for c in g)
            if not m['face'] and not private: continue  # ordinary text
            rec = {'at': {'byte_start': s, 'byte_end_exclusive': e}, 'raw': g, 'font_family': m['family'], 'typeface': m['face']}
            if g is None: rec.update(status='unresolved', why='not UTF-8', bytes=raw[s:e].hex())
            elif not m['face']: rec['status'] = 'unknown_pua'
            elif m['face'] in got['faces']: rec.update(status='unresolved', why='font-face')
            elif m['changed']: rec.update(status='unresolved', why='transform')
            elif m['pseudo']: rec.update(status='unresolved', why='first letter or line')
            elif len(g) > 1: rec.update(status='unicode_kept') if not private and all(ord(c) > 0xFF for c in g) else rec.update(status='unresolved', why='several characters')
            elif ds[i][0] is not None: d = ds[i][0]; rec.update(status='decoded', unicode={'code_point': 'U+%04X' % d, 'string': chr(d), 'name': unicodedata.name(chr(d), None)})
            else: rec['status'] = 'unknown_code' if private or ord(g) <= 0xFF else 'unicode_kept'
            shown = m['visibility'] == 'shown'; held, _, unheld = owners(s, e)  # shown: a box with area, visible, not transparent; no box: hidden; a box of no area: unproven
            rec.update(**({} if shown else {'visibility': m['visibility']}), **({} if vis.certain else {'certain': False}), owners=held if shown and held and not unheld else None)
            out.append(rec)
    return out


def inline(raw, vis, runs, got, units):
    """`source_inline` records from the page's marks (`SYMBOLS_JS`'s `inline`): each source run the page sets under a sup or sub element, whatever its
    computed style, or an inline box whose computed vertical-align is not baseline (other than a plain one: super, sub or a number) - that evidence
    nearest-first (`ancestors`), the run's exact bytes
    and source text and, where it shows and its owners (`_holders`) hold every character of it and read it whole (each owner's text the source's own at
    ordered whole-byte places, `anchor._reading`, read once per owner), the code-point ranges of their final text it stands at (`text_at`). Declared tags
    and computed styles only, evidence and never a measured position (a relatively positioned raise is not seen; an inline block's or table's alignment
    keyword is not counted), nothing read as a footnote or an exponent, no text changed. A run its mark does not reach whole, or that may not carry one (literal text), is `unresolved`, never matched by text."""
    held, owner, _ = edgartools_html._holders(units, vis); found, marks, plain = got.get('inline') or {}, got.get('marks') or {}, set(got.get('plain', '').split(','))
    item, readings, records, unresolved = {(u['id'], None): u for u in units if u.get('kind') not in ('table', 'image')}, {}, [], []
    for u in (u for u in units if u.get('kind') == 'table'):
        for c in u.get('cells') or []:
            a = [x for x in anchor.spans(c.get('anchor')) if 'byte_start' in x]
            if a: item[(u['id'], a[0]['byte_start'])] = c  # the holders' key: a cell by its table and its anchor's first byte

    def reading(key):  # the owner's text position of each search-form character it holds, or None where its text is not the source's at ordered whole-byte places
        if key not in readings:
            x = item[key]; a = [s for s in anchor.spans(x.get('anchor')) if 'byte_start' in s]
            r = anchor._reading(vis, x) if all(p['byte_end_exclusive'] <= q['byte_start'] for p, q in zip(a, a[1:])) else None
            readings[key] = dict(zip(r[2], r[1])) if r else None
        return readings[key]

    def owners(s, e):  # (each owner with the ranges of its text the run's characters stand at, or None; why not)
        has, n, unheld = held(s, e)
        if not n or unheld: return None, 'not every character held'
        lo, hi, out, read = bisect_left(vis.s, s), bisect_left(vis.s, e), [], set()
        for key in sorted(has, key=lambda k: has[k][0]):
            at = reading(key)
            if at is None: return None, 'an owner is not read whole'
            ranges = []
            for p in sorted(at[k] for k in range(lo, hi) if k in at):  # consecutive positions only: a range never spans text the run does not hold
                if ranges and ranges[-1][1] == p: ranges[-1][1] = p + 1
                else: ranges.append([p, p + 1])
            read.update(k for k in range(lo, hi) if k in at); out.append(dict(owner(key), text_at=ranges))
        return (out, None) if len(read) == hi - lo else (None, 'not every character read')

    for k, (_, chars, hidden, marked) in enumerate(runs):
        key = str(k); m = found.get(key) if marked else None
        if m is None and marked and (key in plain or marks.get(key) is not None): continue  # bound and not raised: nothing to say (almost every run)
        every, glyphs = _glyphs(raw, chars)
        if not glyphs: continue
        s0, e0 = glyphs[0][0][0], glyphs[-1][0][1]
        where = {'at': {'byte_start': s0, 'byte_end_exclusive': e0}, 'raw': ''.join(g if g is not None else '\ufffd' for (x, g) in every if s0 <= x[0] < e0), **({} if vis.certain else {'certain': False})}
        if m is None or not _bound(glyphs, m['text']):  # what kept the run from being read
            if not hidden: unresolved.append(dict(where, why='literal text' if not marked else 'unbound' if m is not None or key in marks else 'mark not found'))
            continue
        rec = dict(where, ancestors=m['ancestors'])
        if m['visibility'] != 'shown': rec.update(visibility=m['visibility'], owners=None)  # hidden, or boxes of no area: no text of an owner stands for it
        else:
            rec['owners'], why = owners(s0, e0)
            if why: rec['why'] = why
        records.append(rec)
    return {'records': records, 'unresolved': unresolved}


def _offline_page(browser, asked=None, document=None):
    """A page as the step opens it: a wide window, the document's scripts never run, nothing fetched - a document's own references are never fetched
    (EDGAR forbids external ones; the step must not depend on that). `asked`: a list that gets the address of every style sheet the page requests.
    `document`: (address, bytes[, charset]) answered once, to the page's own first load: with no charset named, as a server sends a page that names
    none, so the browser decodes the bytes by its own rules (a byte order mark, a <meta>, its default); with one, in that charset. Every other request
    is refused - a later navigation (a refresh, a frame, a redirect) as cancelled, so that the page stays the one loaded."""
    page = browser.new_page(viewport={'width': 1400, 'height': 1000}, java_script_enabled=False); first = [document]
    def answer(route):
        r = route.request
        if first[0] and r.url == first[0][0] and r.is_navigation_request() and r.frame == page.main_frame: (_, body, *named), first[0] = first[0], None; return route.fulfill(status=200, content_type='text/html' + ''.join('; charset=' + c for c in named), body=body)
        if asked is not None and r.resource_type == 'stylesheet': asked.append(r.url)
        route.abort('aborted' if document else 'failed')  # cancelled: no error page replaces the loaded one ('failed', the default, for the step's other renders)
    page.route('**/*', answer); return page


def measure(marked_html, browser, prefix=None, every=False):
    """Boxes of every tagged cell as Chrome lays the document out (the document's own styles, a wide window; the document's scripts never run). Only
    table cells are read: a source element that writes the mark itself (`<div data-g="2">`) is no cell and measured nothing in its place (Codex,
    MEASURE_ALIAS_BASELINE); on a cell the step's own mark stands first and the browser keeps the first. With a symbol-mark `prefix`, the same page's
    symbol marks (`SYMBOLS_JS`) come third: with `every`, each run's, an ordinary one's too."""
    page = _offline_page(browser)
    try:
        page.set_content(marked_html.decode('utf-8', 'replace'), wait_until='load'); got = page.evaluate(JS) if prefix is None else page.evaluate(JS, prefix)
        try: sym = page.evaluate(SYMBOLS_JS, [prefix, every]) if prefix is not None else None
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: sym = {'error': repr(e)[:200]}  # the symbols alone: the geometry measured stays (the step says why)
    finally:
        page.close()
    by_table = {}
    for c in got['cells']: by_table.setdefault(c['table'], []).append(c)
    return (by_table, got['boxes']) if prefix is None else (by_table, got['boxes'], sym)


def page_visibility(raw, vis, browser):
    """Which of the scanner's text runs the page itself hides, for a file whose reading is not certain, before the tool reads it: the step's own marks
    (`symbol_runs`, `tag_cells` with comments only, no cell attribute a sheet could select) in a page that loads the marked bytes in the charset the
    browser gives the original bytes (read first, sent as a server sends a page naming none); each run measured by the symbol marks' rule (`SYMBOLS_JS`) - no box, not
    visible, or an ancestor at opacity 0: hidden; a box with area: shown; boxes of no area: neither (`unproven`). A run counts only where it holds more
    than white space and the text its mark reached is exactly its own (`_bound`, as for symbols): one that is unmarked (literal text, or before a byte
    order mark, which stays first), unbound (the parser moved it), decoded otherwise than by the scanner or not found counts nothing, and the scanner's
    reading stays for it.
    {'hidden': [[start, end], ...] the runs proved hidden, 'shown': [...] the runs the scanner hides that the page shows,
    'unproven': n, 'unbound': [...] the runs no verdict reached, and - where there are any - 'unresolved': beside each of those spans, in order, its
    exact source fragment as evidence (`at`; `raw`, those bytes read as UTF-8 and nothing more - no reference decoded, so it encodes back to them
    exactly - or, where they are not UTF-8, the `bytes` in hex; `why`): source spelling, not what the browser shows; neither shown nor hidden, its
    place in the page unknown (Root, fostered_text_20261009)}. A page the browser cannot read raises, and so does one that names a style sheet (its
    request, refused offline: what the sheet shows or hides is not known)."""
    runs, _ = symbol_runs(raw, vis); prefix = marker_prefix(raw); asked = []; address = 'http://%s.invalid/' % prefix  # an address the source nowhere writes
    bom = next((len(b) for b in (b'\xef\xbb\xbf', b'\xfe\xff', b'\xff\xfe') if raw.startswith(b)), 0)  # a byte order mark stays first: the browser decodes by it
    marked, _ = tag_cells(raw, vis, (), [(a, b'<!--%ss:%d-->' % (prefix.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok and a >= bom], prefix, cells=False)  # comments only: no attribute a sheet could select
    page = _offline_page(browser, asked, (address, raw))  # first the original bytes as they are: how the browser itself decodes them, and what they ask for
    try: page.goto(address, wait_until='load'); charset = page.evaluate('document.characterSet')
    finally: page.close()
    if asked: raise RuntimeError('style sheets the page names cannot be read offline: ' + ', '.join(asked)[:150])  # every sheet the page names is requested from a page with an address, and refused: what it shows or hides is not known, no verdict at all
    page = _offline_page(browser, None, (address, marked, charset))  # then the marked bytes in that charset: a comment cannot move a <meta> out of the browser's reach
    try: page.goto(address, wait_until='load'); got = page.evaluate(SYMBOLS_JS, [prefix, True])
    finally: page.close()
    out, unresolved = {'hidden': [], 'shown': [], 'unproven': 0, 'unbound': []}, []
    for k, (_, chars, hidden, ok) in enumerate(runs):
        glyphs = _glyphs(raw, chars)[1]; m = got['marks'].get(str(k)) if ok else None
        if not glyphs: continue  # white space only: nothing to bind it by
        if m is None or not _bound(glyphs, m['text']):  # listed: text the parser moved, literal or misread, kept as the scanner reads it - and its source beside it
            s, e = chars[0][0], chars[-1][1]; out['unbound'].append([s, e])
            try: fragment = {'raw': raw[s:e].decode('utf-8')}
            except UnicodeDecodeError: fragment = {'bytes': raw[s:e].hex()}
            unresolved.append({'at': {'byte_start': s, 'byte_end_exclusive': e}, **fragment,
                               'why': 'byte order mark' if e <= bom else 'literal text' if not ok else 'unbound' if str(k) in got['marks'] else 'mark not found'})  # as `symbols` says it; the encoding's own mark is no text the page shows
        elif m['visibility'] == 'hidden': out['hidden'].append([chars[0][0], chars[-1][1]])
        elif m['visibility'] == 'unproven': out['unproven'] += 1
        elif hidden: out['shown'].append([chars[0][0], chars[-1][1]])
    if unresolved: out['unresolved'] = unresolved
    return out


def step(raw, route, browser):
    """The step on one document's route (the caller's bytes and browser): its tables gridded as Chrome lays them out (`apply`), the spaces the tool
    added measured and joined where Chrome shows them touching on one baseline (`join`), in a file the scanner cannot read for certain the units'
    endpoint boxes recorded; the route record names the step. Returns the step's facts; a page that cannot be measured keeps the route's content and
    anchors as they were, adds only the failure evidence (`source_symbols` read: false) and says why; a failed symbol reading alone keeps the geometry
    measured, says the same, and its error makes the route PARTIAL. Bytes that are not the route's source raise ValueError before any browser work; storage, dependency and resource errors propagate."""
    anchor.check_source(raw, route.get('sha256'))
    t0 = time.time(); return _step(raw, route, browser, Visible(raw, page=route.get('page_visibility')), t0)  # the reading the route was made with; the step's time counts its own scan


def _step(raw, route, browser, vis, t0=None):  # `step` on a reading already made of the route's own bytes (html_route.prepare, which checked them): the one the route was made with
    if vis.page != route.get('page_visibility'): raise ValueError('the screen step reads the source as the route was read (its page visibility), not another reading')
    t0 = time.time() if t0 is None else t0; gaps = gaps_of(vis, route['units']); endpoints = endpoints_of(vis, route['units']) if not vis.certain else []  # a reading made before the step is not its time
    (runs, unread), prefix = symbol_runs(raw, vis), marker_prefix(raw)
    marked, spans = tag_cells(raw, vis, gaps + endpoints, [(a, b'<!--%ss:%d-->' % (prefix.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], prefix)
    try: measured, boxes, got = measure(marked, browser, prefix)
    except (OSError, StorageError, ImportError, MemoryError): raise
    except Exception as e:
        if not browser.is_connected(): raise
        err = repr(e)[:200]; route['source_symbols'], route['source_inline'] = {'read': False, 'error': err}, {'read': False, 'error': err}  # content and anchors stay; the failure is said, never an empty success
        return {'error': repr(e)[:200]}
    if endpoints:  # source-bound endpoints, measured in the existing render; no answer key chooses them
        route['screen_endpoints'] = {side: {str(g[0][side]): boxes[str(len(gaps) + n) + '.' + str(ix)] for n, g in enumerate(endpoints) if str(len(gaps) + n) + '.' + str(ix) in boxes} for ix, side in enumerate(('start', 'end'))}
    if 'error' in got and not browser.is_connected(): raise RuntimeError('browser disconnected: ' + got['error'])
    route['source_symbols'] = {'read': False, 'error': got['error']} if 'error' in got else {'read': True, 'decoder': 'dingbat-to-unicode 1.0.2', 'records': symbols(raw, vis, runs, got, route['units']), **({'unread': unread} if unread else {})}
    n = apply(route['units'], spans, measured); join(gaps, boxes, vis); route['route'] = dict(route['route'], name=route['route']['name'] + '+screen', settings=dict(route['route'].get('settings') or {}, screen_grid=True, joins='touching on one baseline', parts='apart on one baseline'))
    route['source_inline'] = {'read': False, 'error': got['error']} if 'error' in got else {'read': True, **inline(raw, vis, runs, got, route['units']), **({'unread': unread} if unread else {})}  # the owners' final text: after the re-grid and the joins
    edited = {id(x): x for x, *_ in gaps}.values()
    return {'cells_regridded': n, 'cells_measured': sum(len(v) for v in measured.values()), 'spaces_the_tool_added': sum(a < b for _, a, b, _, _ in gaps), 'joined': sum(len(x.get('joins', ())) for x in edited),
            'boundaries_the_tool_dropped': sum(a == b for _, a, b, _, _ in gaps), 'parted': sum(len(x.get('parts', ())) for x in edited), 'seconds': round(time.time() - t0, 1),
            **({'error': 'symbols: ' + got['error']} if 'error' in got else {})}  # html_route marks the route PARTIAL with it
