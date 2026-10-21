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
import mimetypes
import re
import urllib.parse
import time
import types
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
    """A copy with a comment <!--g:n--> right after every <td>/<th> start tag (document order; the scanner's own tag end) and the byte span of each cell in
    the original - a comment, never an attribute: a sheet can select an attribute, none sees a comment, :empty and structural selectors ignore it (Root,
    render-mark boundary); and, for each gap, a comment <!--j:n.0-->
    / <!--j:n.1--> right before the character before and after it — a comment is no element: no stylesheet rule and no structural selector sees it, the
    page lays out exactly as before (Codex C2), and the page's own range over the character that follows it is measured. `cells`: False for a copy
    with no cell marks (spans then none). `marks`: (byte, comment) pairs
    set in as given (the symbol runs' marks); `prefix` (`marker_prefix`) begins every comment the step writes, so none the source writes stands for one."""
    vis = Visible(raw) if vis is None else vis
    spans = sorted((a, b) for table in vis.tables for row in table for a, b in row) if cells else []  # the scanner's cells: the parser's own, where a plain search for the tags ran a cell with no end tag on to the next cell anywhere (Codex G2-C3)
    edits = []
    for n, (start, end) in enumerate(spans):
        close = _CELL_END.match(raw, end); spans[n] = (start, close.end() if close else end)  # with its own end tag, where it has one
        edits.append((vis.cell_tag_ends[start], b'<!--%sg:%d-->' % (prefix.encode(), n)))
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
    rows = {c['g']: c.get('rs', 1) for table_cells in measured_by_table.values() for c in table_cells}  # each cell's rows as the browser's table model ends them (rowspan="0" to its row group's end, a larger span stopped there)
    key = lambda u: u.get('id', id(u))  # a unit's id (a caller's bare unit: its identity)
    tabs = {key(u): u for u in units if u.get('kind') == 'table'}

    def owner(cell):  # the measured cell this route cell is: its own source cell (`source`, the adapter's injected identity; None: no place), else - a
        if 'source' in cell:  # route that names none - the innermost measured cell holding its text's first byte; -1: none
            s = cell['source']; j = bisect_left(starts, s['byte_start']) if s else len(starts)
            return j if j < len(starts) and starts[j] == s['byte_start'] else -1
        a = cell.get('anchor'); a = a[0] if isinstance(a, list) else a
        if not isinstance(a, dict) or 'byte_start' not in a: return -1
        g = bisect_right(starts, a['byte_start']) - 1
        while g >= 0 and a['byte_start'] >= spans[g][1]: g = parents[g]
        return g if g >= 0 and spans[g][0] <= a['byte_start'] < spans[g][1] else -1
    n, grid = 0, {}  # grid: route table -> the one measured table all its cells stand in, else None
    for u in tabs.values():
        tables = set()  # the measured table each cell stands in; None: a cell not measured
        for cell in u.get('cells') or []:
            g = owner(cell)
            if g >= 0 and g not in by_g and 'source' in cell: continue  # its own source cell, not laid out (hidden, no width): no place, and no say in the grid
            if g < 0 or g not in by_g: tables.add(None); continue
            r, c, cs = by_g[g]; rs = rows[g]  # a text cell states its rows as a picture in the same cell does
            if (cell['r'], cell['c'], cell.get('rs', 1), cell.get('cs', 1)) != (r, c, rs, cs): cell.update(r=r, c=c, rs=rs, cs=cs); n += 1
            cell['grid'] = 'screen'; tables.add(table_of[g])
        grid[key(u)] = next(iter(tables)) if len(tables) == 1 and None not in tables else None
        if grid[key(u)] is not None: u['cells'].sort(key=lambda x: (x['r'], x['c']))  # stable: cells that share a place keep their order; a table with a cell not measured, or measured in two tables (one inside the other), keeps the tool's order
    holder = {k: (u, c) for u in tabs.values() for c in u.get('cells') or [] for k in c.get('tables') or []}
    for u in units:
        cell = u.get('cell') if u.get('kind') in ('image', 'table') else None
        if not isinstance(cell, dict) or 'table' not in cell: continue  # no route table: no place to state in one
        if u.get('kind') == 'table':  # a table standing in a cell: its holder cell's measured place, where the holder's table has one grid
            p, h = holder.get(u['id'], (None, None))
            if p is not None and grid.get(key(p)) is not None and h.get('grid') == 'screen': cell.update({k: h[k] for k in ('r', 'c', 'rs', 'cs')})
            else:
                for k in ('r', 'c', 'rs', 'cs'): cell.pop(k, None)
            continue
        g, t = bisect_left(starts, cell['byte_start']), grid.get(cell['table'])
        if t is not None and g < len(starts) and starts[g] == cell['byte_start'] and table_of.get(g) == t: r, c, cs = by_g[g]; cell.update(r=r, c=c, rs=rows[g], cs=cs)
        else:
            for k in ('r', 'c', 'rs', 'cs'): cell.pop(k, None)
    return n


JS = """(p) => { p = p || ''; const tables = Array.from(document.querySelectorAll('table')); const out = []; const gap = new RegExp('^' + p + 'j:([0-9]+[.][01])$'), cell = new RegExp('^' + p + 'g:([0-9]+)$');
  const shown = new Map();  // each row's place in its table as the page shows it: rows by their own box's top (equal tops in DOM order); a row with no box stays after the one before it
  for (const t of tables) { let top = -Infinity; const keyed = Array.from(t.rows, tr => { if (tr.getClientRects().length) top = tr.getBoundingClientRect().top; return [top, tr.rowIndex, tr]; });
    keyed.sort((a, b) => a[0] - b[0] || a[1] - b[1]).forEach(([, , tr], i) => shown.set(tr, i)); }
  const named = new Set(), cw = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT);  // a cell's own mark is the first in it, a cell being a native HTML cell (a <td> in SVG or MathML is a foreign element); one the parser moved out of a cell, or a second in one cell (a start tag it ignored), names nothing
  for (let c = cw.nextNode(); c; c = cw.nextNode()) { const m = cell.exec(c.data), el = c.parentElement; if (!m || !(el instanceof HTMLTableCellElement) || named.has(el)) continue; named.add(el);
    const r = el.getBoundingClientRect(); const t = el.closest('table'); const tr = el.parentElement;
    const rest = tr && tr.parentElement && tr.parentElement.rows ? tr.parentElement.rows.length - tr.sectionRowIndex : 1;  // the rows left in its row group, where the table model ends a cell: rowspan="0" runs to there, a larger one stops there
    out.push({g: +m[1], table: tables.indexOf(t), row: tr && shown.has(tr) ? shown.get(tr) : -1, x: r.left, w: r.width, rs: el.rowSpan === 0 ? rest : Math.min(el.rowSpan, rest)}); }
  const boxes = {}; const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT);
  for (let c = w.nextNode(); c; c = w.nextNode()) { const m = gap.exec(c.data); if (!m) continue; let t = c.nextSibling; while (t && t.nodeType === Node.COMMENT_NODE) t = t.nextSibling;  // one character can end one gap and begin the next: its two marks stand side by side
    if (!t || t.nodeType !== Node.TEXT_NODE || !t.data.length) continue;
    let shown = getComputedStyle(t.parentElement).visibility === 'visible';
    for (let el = t.parentElement; el && shown; el = el.parentElement) if (+getComputedStyle(el).opacity === 0) shown = false;
    const r = document.createRange(); r.setStart(t, 0); r.setEnd(t, 1); const rs = r.getClientRects();
    if (rs.length === 1) boxes[m[1]] = {shown, x: rs[0].left, r: rs[0].right, t: rs[0].top, b: rs[0].bottom}; }
  return {cells: out, boxes}; }"""


SYMBOLS_JS = "([p, every, decorate]) => { " + _decoder_js() + """ const marks = {}, faces = [], plain = [], inline = {}, decor = {}, color = {}, color_pseudo = {}, style = {}, style_pseudo = {}, tints = new Map(), grounds = new Map(), lifts = new Map(), mark = new RegExp('^' + p + 's:([0-9]+)$');  // every: each run measured, an ordinary one too (page_visibility)
  for (const f of document.fonts) faces.push(f.family.replace(/^["']|["']$/g, '').toUpperCase());  // typefaces the document defines itself (@font-face)
  const STYLED = ['font-weight', 'font-style', '-webkit-text-decorations-in-effect', 'background-color', 'background-image', 'text-transform'];
  const tint = el => { if (!el) return [[], []]; if (tints.has(el)) return tints.get(el);  // an element's and its ancestors' first-letter / first-line readings that differ from their own (nearest first), each element's own and pseudo styles read once: colours [pseudo, colour] as before, and the style readings named [pseudo, property, value] (a pseudo's unset background - initial: transparent, none - covers nothing behind it); which characters they paint is layout's, so they stay an uncertainty
    const own = getComputedStyle(el), up = tint(el.parentElement), c = [], s = [];
    for (const ps of ['::first-letter', '::first-line']) { const q = getComputedStyle(el, ps); if (q.color !== own.color) c.push([ps, q.color]);
      for (const k of STYLED) { const v = q.getPropertyValue(k); if (v !== own.getPropertyValue(k) && !(k.startsWith('background') && (v === 'rgba(0, 0, 0, 0)' || v === 'none'))) s.push([ps, k, v]); } }
    const got = [c.concat(up[0]), s.concat(up[1])]; tints.set(el, got); return got; };
  const ground = el => { if (!el) return []; if (grounds.has(el)) return grounds.get(el);  // the raw background stack of an element and its ancestors: [depth, colour, image, opacity] wherever a colour or image is set or the opacity is not 1, nearest first, no cutoff and no compositing (none observed: [], never "no highlight"), each element read once
    const cs = getComputedStyle(el), got = (cs.backgroundColor !== 'rgba(0, 0, 0, 0)' || cs.backgroundImage !== 'none' || cs.opacity !== '1' ? [[0, cs.backgroundColor, cs.backgroundImage, cs.opacity]] : []).concat(ground(el.parentElement).map(([d, ...x]) => [d + 1, ...x]));
    grounds.set(el, got); return got; };
  const lift = el => { if (!el) return null; if (lifts.has(el)) return lifts.get(el);  // an element's and its ancestors' raised or lowered evidence, nearest first (null: none), each element's style read once:
    const cs = getComputedStyle(el), tag = el.localName, up = lift(el.parentElement);  // a sup or sub, whatever its computed style; a plain inline box whose computed vertical-align is not baseline; any other inline box
    const placed = cs.position !== 'static';  // a positioned box: its own raw computed inset declarations are its evidence (never a measured or judged displacement)
    const got = tag === 'sup' || tag === 'sub' || (cs.display.startsWith('inline') && placed) || (cs.display.startsWith('inline') && cs.verticalAlign !== 'baseline' && (cs.display === 'inline' ||  // only where it is super, sub or a number (Typed OM: a length, percentage, calc or zero), never
      cs.verticalAlign === 'super' || cs.verticalAlign === 'sub' || el.computedStyleMap().get('vertical-align') instanceof CSSNumericValue)) ? [Object.assign({tag, display: cs.display, vertical_align: cs.verticalAlign}, placed ? {position: cs.position, top: cs.top, bottom: cs.bottom, left: cs.left, right: cs.right} : {})].concat(up || []) : up;  // an alignment keyword (a whole inline table set text-bottom; root, ROOT_NATIVE_PREDICATE)
    lifts.set(el, got); return got; };
  const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT);
  for (let c = w.nextNode(); c; c = w.nextNode()) { const m = mark.exec(c.data); if (!m) continue;
    let text = '', el = null, first = null, last = null, n = c.nextSibling;  // the run's text: the text nodes after its mark, across inserted comments, to an element or the next run's mark
    for (; n && (n.nodeType === Node.TEXT_NODE || (n.nodeType === Node.COMMENT_NODE && !mark.test(n.data))); n = n.nextSibling) if (n.nodeType === Node.TEXT_NODE) { text += n.data; el = n.parentElement; first = first || n; last = n; }
    if (!el) { marks[m[1]] = null; continue; }  // the parser moved the run away from its mark (a table's foster parent): unbound
    const cs = getComputedStyle(el), fam = cs.fontFamily.toUpperCase(), chars = Array.from(text);
    if (every) { color[m[1]] = cs.color; const [t, q] = tint(el); if (t.length) color_pseudo[m[1]] = t;
      style[m[1]] = [cs.fontWeight, cs.fontStyle, cs.getPropertyValue('-webkit-text-decorations-in-effect'), ground(el), cs.textTransform]; if (q.length) style_pseudo[m[1]] = q; }  // the same element's weight, style, decorations in effect (inherited too) and raw background stack  // every run measured: the foreground colour the browser computes for the element holding its text (inherited and sheet rules applied), as Chrome writes it; a first-letter / first-line colour that may paint some of its characters, beside it
    if (decorate) decor[m[1]] = [cs.getPropertyValue('-webkit-text-decorations-in-effect'), text];  // asked for (strike-through the scanner cannot certify): the decorations the browser applies to this text, inherited ones too (not the element's own `text-decoration-line`), with the text to bind it
    const face = lib.faces.find(f => { const k = f.indexOf(' ') < 0 ? f : '"' + f + '"'; return fam === k || fam.startsWith(k + ', '); }) || null;  // the primary family, as Chrome writes it
    const ordinary = !face && !/[\\uE000-\\uF8FF\\u{F0000}-\\u{10FFFD}]/u.test(text), lifted = lift(el);
    let boxes = null; const shows = () => { const r = document.createRange(); r.setStart(first, 0); r.setEnd(last, last.length); const rs = Array.from(r.getClientRects()); boxes = rs.map(q => [q.x, q.y, q.width, q.height]);  // the glyphs' own boxes, not the element's: kept raw ([x, y, width, height], CSS pixels, client frame), never a visibility or order verdict
      let seen = getComputedStyle(el).visibility === 'visible'; for (let a = el; a && seen; a = a.parentElement) if (+getComputedStyle(a).opacity === 0) seen = false;  // the gap marks' rule
      return !rs.length || !seen ? 'hidden' : rs.some(q => q.width > 0 && q.height > 0) ? 'shown' : 'unproven'; };
    let visibility = lifted ? shows() : null;
    if (lifted) inline[m[1]] = {text, visibility, ancestors: lifted};  // raised or lowered: kept apart from the symbol records, before the ordinary-font exit
    if (ordinary && !every) { plain.push(m[1]); continue; }  // ordinary text: nothing a symbol record could say (its id only: a large result is slow to leave the page)
    visibility = visibility || shows();
    if (ordinary) { marks[m[1]] = {text, visibility, boxes}; continue; }  // every run measured: an ordinary one says only its text and whether it shows
    marks[m[1]] = {text, family: cs.fontFamily, face, visibility, boxes,
      changed: cs.textTransform !== 'none' || cs.fontVariant !== 'normal' || cs.fontFeatureSettings !== 'normal',
      pseudo: !!face && (() => { for (let a = el; a; a = a.parentElement) { const own = getComputedStyle(a); for (const ps of ['::first-letter', '::first-line']) { const q = getComputedStyle(a, ps);  // a block's first letter or line set another way
        if (q.fontFamily !== own.fontFamily || q.textTransform !== own.textTransform || q.fontVariant !== own.fontVariant || q.fontFeatureSettings !== own.fontFeatureSettings) return true; } } return false; })(),
      decoded: face ? chars.map(ch => { let k = ch.codePointAt(0); if (k >= 0xF020 && k <= 0xF0FF) k -= 0xF000; const r = k <= 0xFF ? lib.codePoint(face, k) : undefined; return r ? r.codePoint : null; }) : null}; }
  return Object.assign({marks, faces, plain: plain.join(','), inline, color, color_pseudo, style, style_pseudo, frame: {viewport: [innerWidth, innerHeight], scroll: [scrollX, scrollY], device_pixel_ratio: devicePixelRatio}}, decorate ? {decor, decorations: getComputedStyle(document.documentElement).getPropertyValue('-webkit-text-decorations-in-effect')} : {}); }"""


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


def decorations(raw, vis, runs, got):
    """The browser's own decoration of each source text run in this render (asked of `SYMBOLS_JS` with `decorate`: per run it reached, the decorations it
    applies - `-webkit-text-decorations-in-effect`, inherited ones too - and the text its mark reached), for a source whose strike-through the scanner
    cannot certify (`source_formatting.rendered`): [[first byte, end byte, verdict]] for every run with more than white space - 'struck' or 'unstruck'
    only where the run's mark reached exactly its own text and the browser gave the property (it names it, 'none' included, on the document element
    too); 'excluded' where the reading hides the run; else 'unresolved: why' - literal text, where no mark may stand; unbound, the parser moved it or its
    own text was not what its mark reached; no mark found; no decoration, the property or the answer missing; paint, a line in this file may be drawn
    unseen (`Visible.paint_uncertain`). Never a guess: no answer is no proof of an unstruck run."""
    decor = got.get('decor'); usable = isinstance(decor, dict) and bool(got.get('decorations'))  # a browser without the property, or a malformed answer, proves nothing
    bom = next((len(b) for b in (b'\xef\xbb\xbf', b'\xfe\xff', b'\xff\xfe') if raw.startswith(b)), 0)  # the encoding's own mark: no text the page shows (as page_visibility)
    open_ = [(r['at']['byte_start'], r['at']['byte_end_exclusive']) for r in (vis.page or {}).get('unresolved') or []] if vis.paged else []  # runs the visibility verdict never reached: already said, theirs
    out = []
    for k, (_, chars, hidden, ok) in enumerate(runs):
        glyphs = _glyphs(raw, chars)[1]
        if not glyphs: continue  # white space only: nothing to bind it by, nothing a strike shows on
        d = decor.get(str(k)) if usable else None
        if chars[-1][1] <= bom: continue
        if hidden: verdict = 'excluded'
        elif any(x <= chars[0][0] and chars[-1][1] <= y for x, y in open_): verdict = 'unresolved: visibility'  # its visibility itself is unknown (page_visibility's own unresolved)
        elif not ok: verdict = 'unresolved: literal text'
        elif not usable: verdict = 'unresolved: no decoration'
        elif str(k) not in decor: verdict = 'unresolved: unbound' if got['marks'].get(str(k), False) is None or str(k) in (got.get('plain') or '').split(',') else 'unresolved: no mark'
        elif not (isinstance(d, list) and len(d) == 2 and isinstance(d[0], str) and d[0] and isinstance(d[1], str)): verdict = 'unresolved: no decoration'
        elif not _bound(glyphs, d[1]): verdict = 'unresolved: unbound'
        elif 'line-through' in d[0].split(): verdict = 'unresolved: paint' if vis.paint_uncertain else 'struck'
        else: verdict = 'unstruck'
        out.append([chars[0][0], chars[-1][1], verdict])
    return out


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
                            'why': 'literal text' if not marked else 'unbound' if str(k) in got['marks'] else 'mark not found', **({'bytes': raw[s0:e0].hex()} if any(g is None for x, g in every if s0 <= x[0] < e0) else {}),
                            'owners': None, **({} if vis.certain else {'certain': False})})  # the source text as written, spaces kept; bytes that are not UTF-8 kept as they are
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


def _owners(vis, units, spaced=False):
    """owners(s, e) for a source run's bytes: (each owner (`_holders`) with the code-point ranges of its final text the run's characters stand at
    (`text_at`, consecutive positions only), or None; why not) - every character held, each owner's text the source's own at ordered whole-byte
    places (`anchor._reading`, read once per owner) and every character read. One run-to-owner rule for every per-run record (`inline`, `styles`).
    `spaced`: two ranges with only white space CSS collapses between them in the owner's text are one (a run's words, not a map of each word)."""
    held, owner, _ = edgartools_html._holders(units, vis)
    item, readings = {(u['id'], None): u for u in units if u.get('kind') not in ('table', 'image')}, {}
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
            if spaced:  # the run's ranges joined across white space only: no character of other text is ever inside one
                text, joined = item[key].get('text') or '', []
                for a, b in ranges:
                    if joined and not text[joined[-1][1]:a].strip(anchor._SPACE): joined[-1][1] = b
                    else: joined.append([a, b])
                ranges = joined
            read.update(k for k in range(lo, hi) if k in at); out.append(dict(owner(key), text_at=ranges))
        return (out, None) if len(read) == hi - lo else (None, 'not every character read')
    return owners


def inline(raw, vis, runs, got, units):
    """`source_inline` records from the page's marks (`SYMBOLS_JS`'s `inline`): each source run the page sets under a sup or sub element, whatever its
    computed style, an inline box whose computed vertical-align is not baseline (other than a plain one: super, sub or a number), or an inline box whose
    computed position is not static (its record also carries the raw computed position, top, bottom, left and right) - that evidence
    nearest-first (`ancestors`), the run's exact bytes
    and source text and, where it shows and its owners (`_holders`) hold every character of it and read it whole (each owner's text the source's own at
    ordered whole-byte places, `anchor._reading`, read once per owner), the code-point ranges of their final text it stands at (`text_at`). Declared tags
    and computed styles only, evidence and never a measured position (a zero or auto inset is evidence too, never a claim of displacement; transforms and
    pseudo-element positioning are not read; an inline block's or table's alignment keyword is not counted), nothing read as a footnote or an exponent, no text changed. A run its mark does not reach whole, or that may not carry one (literal text), is `unresolved`, never matched by text."""
    found, marks, plain = got.get('inline') or {}, got.get('marks') or {}, set(got.get('plain', '').split(','))
    owners, records, unresolved = _owners(vis, units), [], []
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


def styles(raw, vis, runs, got, units):
    """`source_style` records from the same render's marks (`SYMBOLS_JS`'s `color` and `style`, read with `every`): for every source run its mark
    reaches whole, the foreground colour, font weight, font style, decorations in effect and text transform the browser computes for the element holding its text
    (inherited and sheet rules applied; as Chrome writes them, never interpreted - a default is a reading too), its raw `background` stack where one
    is observed ([depth, colour, image, opacity]: no paint, coverage or image-content claim; none observed: no key), first-letter / first-line values
    that differ (`pseudo` for colour, `style_pseudo` named by property), its exact bytes and, where it shows, its owners' `text_at` (`_owners`, as `inline`). A hidden
    run keeps its reading with no owner. A run its mark does not reach whole, or that may not carry one (literal text), is `unresolved` with its source
    text beside it, never matched by text; no record repeats a run's text (its bytes and owners locate it)."""
    found, marks, owners, records, unresolved = got.get('color') or {}, got.get('marks') or {}, _owners(vis, units, spaced=True), [], []
    styled, shaded = got.get('style') or {}, got.get('style_pseudo') or {}
    tinted = got.get('color_pseudo') or {}  # a first-letter / first-line colour of the element or an ancestor: some characters may be painted so (layout decides which)
    for k, (_, chars, hidden, marked) in enumerate(runs):
        every, glyphs = _glyphs(raw, chars)
        if not glyphs: continue
        key, s0, e0 = str(k), glyphs[0][0][0], glyphs[-1][0][1]; m = marks.get(key) if marked else None
        where = {'at': {'byte_start': s0, 'byte_end_exclusive': e0}, **({} if vis.certain else {'certain': False})}
        if m is None or key not in found or not _bound(glyphs, m['text']):  # what kept the run from being read
            if not hidden: unresolved.append(dict(where, raw=''.join(g if g is not None else '�' for (x, g) in every if s0 <= x[0] < e0), why='literal text' if not marked else 'unbound' if m is not None or key in marks else 'mark not found'))
            continue
        rec = dict(where, color=found[key], **({'pseudo': tinted[key]} if key in tinted else {}), **({'boxes': m['boxes']} if m.get('boxes') is not None else {}))  # the whole native run's raw client boxes in this render's `frame`: positions, never an order or a visibility proof
        if 'boxes' in rec and (chars[0][0], chars[-1][1]) != (s0, e0): rec['boxes_at'] = {'byte_start': chars[0][0], 'byte_end_exclusive': chars[-1][1]}  # the source the boxes measure (the whole run, preserved white space too) where it differs from `at`
        if key in styled: w, f, d, g, t = styled[key]; rec.update(weight=w, font_style=f, decorations=d, text_transform=t, **({'background': g} if g else {}), **({'style_pseudo': shaded[key]} if key in shaded else {}))  # the element's colour, and beside it what may paint some characters otherwise: not every character's proved colour
        if m['visibility'] != 'shown': rec.update(visibility=m['visibility'], owners=None)  # hidden, or boxes of no area: no text of an owner stands for it
        else:
            rec['owners'], why = owners(s0, e0)
            if why: rec['why'] = why
        records.append(rec)
    return {'records': records, 'unresolved': unresolved, **({'frame': got['frame']} if got.get('frame') else {})}  # the one frame of every box: viewport, scroll origin, device pixel ratio


class Source:
    """The exact evidence one document's renders may use, nothing else: the document's own `path` among its bundle's verified `members`
    ({path: bytes}, from the package reader; `bundle` names that bundle, e.g. its package sha256), read at `base` + path - `base` the bundle's
    recorded address, or None for the step's own address, which no source writes - and `observed`, recorded answers for exact URLs
    ({url: {'status', 'content_type', 'observed_at', 'sha256', 'body'}}). The browser resolves every reference itself (relative paths, <base>,
    @import); a URL is answered only by the member at exactly that path under `base` or by its own observation - a 200 only with the bytes its
    sha256 names. One document's: bound to its bytes at first use (the declared member, where it is one, must be those bytes). `records`: one per
    URL asked (member path and sha256, observation status and time, or 'refused' and why); `charset`: the browser's for the document, read once."""
    def __init__(self, path, members, base=None, observed=None, bundle=None):
        split = urllib.parse.urlsplit(base) if base is not None else None
        if split is not None and not (split.scheme and split.netloc and base.endswith('/')): raise ValueError('base: an absolute address ending in "/", or None')
        if path.startswith('/') or urllib.parse.urlsplit(path).scheme: raise ValueError("path: the document's member path, relative to base")
        if not all(isinstance(k, str) and type(v) is bytes for k, v in members.items()): raise ValueError('members: verified {path: bytes}')
        if not all(isinstance(o.get('status'), int) and isinstance(o.get('observed_at'), str) for o in (observed or {}).values()): raise ValueError('observed: {url: {status, observed_at, ...}}')
        self.path, self.base, self.bundle = path, base, bundle  # the evidence as given, unchangeable afterwards: a record always names the bytes every render used
        self.members, self.observed = types.MappingProxyType(dict(members)), types.MappingProxyType({u: types.MappingProxyType(dict(o)) for u, o in (observed or {}).items()})
        self.records, self.refusals, self.root, self.document, self.charset = {}, [], None, None, None

    def bind(self, raw):  # ValueError unless `raw` is this source's document: its declared member (where it is one), the bytes it was first used for
        digest = hashlib.sha256(raw).hexdigest()
        if self.path in self.members and self.members[self.path] != raw: raise ValueError('the declared document member is not these bytes')
        if self.document not in (None, digest): raise ValueError("a source is one document's evidence: these are other bytes")
        self.document = digest

    def at(self, address, raw):  # the document's address for a render whose own address is `address`
        self.bind(raw); self.root = self.base or address; return self.root + urllib.parse.quote(self.path)  # the member path as a URL writes it

    def identity(self):  # what the route keeps: the document and the evidence its renders used
        return {'document': {'path': self.path, 'base': self.base, 'bundle': self.bundle, 'sha256': self.document},
                'dependencies': sorted(self.records.values(), key=lambda r: json.dumps(r, sort_keys=True))}

    def _refuse(self, url, key, name, kind, why=None):
        self.refusals.append((url, kind)); self.records.setdefault(key, {('path' if key == name else 'url'): key, 'status': 'refused', 'kind': kind, **({'why': why} if why else {})})

    def answer(self, url, kind, navigation=False):
        name = urllib.parse.unquote(urllib.parse.urlsplit(url).path)[len(urllib.parse.urlsplit(self.root).path):] if self.root and url.startswith(self.root) else None  # the pictures' member rule: the decoded path under the address
        key = name if self.base is None and name is not None else url
        if navigation: return self._refuse(url, key, name, 'navigation')  # a member path never answers a navigation
        if name in self.members:
            body = self.members[name]; self.records.setdefault(key, {'member': name, 'sha256': hashlib.sha256(body).hexdigest(), 'status': 200, 'kind': kind})
            return 200, mimetypes.guess_type(name)[0] or 'application/octet-stream', body
        seen = self.observed.get(url)
        if seen is None: return self._refuse(url, key, name, kind)
        body = seen.get('body')
        if seen['status'] == 200 and (body is None or hashlib.sha256(body).hexdigest() != seen.get('sha256')): return self._refuse(url, key, name, kind, 'observed bytes are not the recorded sha256')
        self.records.setdefault(key, {'url': url, 'status': seen['status'], 'observed_at': seen['observed_at'], 'sha256': seen.get('sha256'), 'kind': kind})
        return seen['status'], seen.get('content_type') or 'application/octet-stream', body or b''


def _offline_page(browser, asked=None, document=None, source=None):
    """A page as the step opens it: a wide window, the document's scripts never run, nothing fetched - a document's own references are never fetched
    (EDGAR forbids external ones; the step must not depend on that). `asked`: a list that gets the address of every style sheet the page requests
    and no evidence answers. `document`: (address, bytes[, charset]) answered once, to the page's own first load: with no charset named, as a server
    sends a page that names none, so the browser decodes the bytes by its own rules (a byte order mark, a <meta>, its default); with one, in that
    charset. `source` (a Source): a request that is no navigation is answered from its evidence only. Every other request is refused - a later
    navigation (a refresh, a frame, a redirect) as cancelled, so that the page stays the one loaded."""
    page = browser.new_page(viewport={'width': 1400, 'height': 1000}, java_script_enabled=False); first = [document]
    def answer(route):
        r = route.request
        if first[0] and r.url == first[0][0] and r.is_navigation_request() and r.frame == page.main_frame: (_, body, *named), first[0] = first[0], None; return route.fulfill(status=200, content_type='text/html' + ''.join('; charset=' + c for c in named), body=body)
        got = source.answer(r.url, r.resource_type, r.is_navigation_request()) if source is not None else None
        if got: return route.fulfill(status=got[0], content_type=got[1], body=got[2])
        if asked is not None and r.resource_type == 'stylesheet': asked.append(r.url)
        route.abort('aborted' if document else 'failed')  # cancelled: no error page replaces the loaded one ('failed', the default, for the step's other renders)
    page.route('**/*', answer); return page


def _document(browser, raw, body, source):
    """A page with `body` (the document's bytes, or a marked copy of them) at the source's declared address, in the charset the browser gives the
    original `raw` there (read once per source, as `page_visibility` reads it); the page, its address and where its own load's refusals start."""
    address = source.at('http://%s.invalid/' % marker_prefix(raw), raw)
    if source.charset is None:
        page = _offline_page(browser, None, (address, raw), source)
        try: page.goto(address, wait_until='load'); source.charset = page.evaluate('document.characterSet')
        finally: page.close()
    first = len(source.refusals); page = _offline_page(browser, None, (address, body, source.charset), source)
    try: page.goto(address, wait_until='load')
    except BaseException: page.close(); raise
    return page, address, first


GENERATED_STYLES = ['display', 'visibility', 'color', 'opacity', 'content', 'list-style-image', '-webkit-text-decorations-in-effect', 'vertical-align', 'font-weight', 'font-style', 'background-color', 'background-image']  # the last two: the existing strike (as SYMBOLS_JS reads it, ancestors' too) and raise readings
PSEUDO_ROLE = {'marker': 'inserts', 'before': 'inserts', 'after': 'inserts', 'first-letter': 'formats'}  # the native pseudo types: generated content, or a format of text already there; any other type is kept raw
TEXT_CONTENT = {'function': {'counter', 'counters'}, 'ident': {'open-quote', 'close-quote'}}  # the CSS content items that name text (with a non-empty string); Chrome's computed content resolves attr() to a string
NO_CONTENT = {'no-open-quote', 'no-close-quote', 'normal', 'none'}  # the CSS content keywords that name nothing


def _generated(page, prefix):
    """The page's own layout of generated content (CDP DOMSnapshot.captureSnapshot of this very page, no rects): per pseudo element (before, after,
    marker, first-letter, any other), in tree order (CSS's own places: an element's marker, its before, its children, its after), its layout text
    fragments in native order with their bounds, its computed readings, its own visibility by the existing rule (checkVisibility called on the pseudo
    element itself: its inherited or overridden visibility, opacity, box), the source runs under its owner (their marks) and whether native text
    there follows no source run mark. Raw readings only: nothing here proves that a fragment paints, or where it stands in a unit."""
    cdp = page.context.new_cdp_session(page)
    snap = cdp.send('DOMSnapshot.captureSnapshot', {'computedStyles': GENERATED_STYLES})
    S, d = snap['strings'], snap['documents'][0]; N, L = d['nodes'], d['layout']
    parent, ntype, nval = N['parentIndex'], N['nodeType'], N.get('nodeValue') or []
    pseudo = dict(zip(N.get('pseudoType', {}).get('index', []), N.get('pseudoType', {}).get('value', [])))
    mark = re.compile('^' + re.escape(prefix) + r's:(\d+)$'); run = {}
    for i, t in enumerate(ntype):
        m = mark.match(S[nval[i]]) if t == 8 and i < len(nval) and nval[i] >= 0 else None
        if m: run[i] = int(m.group(1))
    kids = {}
    for i, p in enumerate(parent): kids.setdefault(p, []).append(i)
    groups = {}
    for k, ni in enumerate(L['nodeIndex']):
        if ni not in pseudo: continue  # a pseudo element's box, text and image layout objects all name the pseudo node itself
        g = groups.setdefault(ni, {'pseudo': S[pseudo[ni]], 'owner': parent[ni], 'fragments': [], 'bounds': [], 'computed': dict(zip(GENERATED_STYLES, (S[x] for x in L['styles'][k])))})
        t = L['text'][k] if k < len(L['text']) else -1
        if t >= 0 and S[t]: g['fragments'].append(S[t]); g['bounds'].append(L['bounds'][k])
    lay = {}
    for k, ni in enumerate(L['nodeIndex']):
        if len(L['styles'][k]) == len(GENERATED_STYLES): lay.setdefault(ni, k)  # a node's first layout object that carries its computed styles (some carry none)
    styled = lambda k: dict(zip(GENERATED_STYLES, (S[x] for x in L['styles'][k])))
    def ground(i):  # this snapshot's own raw background stack from a node up ([depth, colour, image, opacity], as SYMBOLS_JS reads a run's); a node with no layout object says nothing (never guessed)
        out, d = [], 0
        while i is not None and i >= 0:
            c = styled(lay[i]) if i in lay else None
            if c and (c['background-color'] != 'rgba(0, 0, 0, 0)' or c['background-image'] != 'none' or c['opacity'] != '1'): out.append([d, c['background-color'], c['background-image'], c['opacity']])
            i, d = parent[i], d + 1
        return out
    images = [{'node': '::' + S[pseudo[ni]] if ni in pseudo else S[N['nodeName'][ni]], 'value': c['background-image'], 'visibility': c['visibility']}
              for ni, k in sorted(lay.items()) if ntype[ni] == 1 for c in [styled(k)] if c['background-image'] != 'none']  # elements and pseudo elements: a text node only repeats its parent's style  # every laid-out element or pseudo element painting a background image (an owner with no text too): its content is never read here
    def below(o):  # the owner's descendants, its own pseudo elements apart
        out, todo = [], list(kids.get(o, []))
        while todo:
            i = todo.pop(); out.append(i)
            if i not in pseudo: todo.extend(kids.get(i, []))
        return [i for i in out if i not in pseudo]
    def follows_mark(i):  # a text node the source run reading reaches: after its run's mark, across text and other comments only (as SYMBOLS_JS reads a run)
        sib = kids.get(parent[i], []); j = sib.index(i)
        while j > 0:
            j -= 1; q = sib[j]
            if q in run: return True
            if not (ntype[q] == 3 or (ntype[q] == 8 and q not in run)): return False
        return False
    order, todo = {}, kids.get(-1, [])[::-1]  # tree order: an element's marker, its before and any other pseudo, its children, its after
    while todo:
        i = todo.pop()
        if i in pseudo: order[i] = len(order); continue
        ps = [k for k in kids.get(i, []) if k in pseudo]
        todo += [k for k in ps if S[pseudo[k]] == 'after'] + [k for k in kids.get(i, []) if k not in pseudo][::-1] + sorted((k for k in ps if S[pseudo[k]] != 'after'), key=lambda k: S[pseudo[k]] != 'marker')[::-1]
    records = []
    for ni, g in sorted(groups.items(), key=lambda x: order.get(x[0], len(order))):  # records at one place in a unit apply in this order
        o = g['owner']; desc = below(o); rec = {k: g[k] for k in ('pseudo', 'fragments', 'bounds', 'computed')}; b = ground(ni)
        if b: rec['background'] = b
        rec.update(owner=o, runs=sorted(run[i] for i in desc if i in run), unknown_text=any(ntype[i] == 3 and i < len(nval) and nval[i] >= 0 and S[nval[i]].strip() and not follows_mark(i) for i in desc))
        try:
            obj = cdp.send('DOM.resolveNode', {'backendNodeId': N['backendNodeId'][ni]})['object']['objectId']  # the pseudo element itself, not its owner
            rec['visible'] = cdp.send('Runtime.callFunctionOn', {'objectId': obj, 'returnByValue': True, 'functionDeclaration': 'function () { return this.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}); }'})['result']['value']
        except (OSError, StorageError, ImportError, MemoryError): raise  # a process, storage or dependency failure is no content verdict (the step's own policy)
        except Exception as e: rec['visible'], rec['visible_error'] = None, repr(e)[:200]  # unknown: never a hidden verdict, never a shown one
        records.append(rec)
    return {'read': True, 'records': records, 'background_images': images}


def _content(c, marker):
    """The computed content as the pinned native tokenizer (tinycss2) reads it: whether it names text (a non-empty string, a counter, a quote: what a
    first-letter may take whole, so its own fragments cannot say) and each item that is no text - an image (url, image-set, a gradient), any other item,
    or what it could not read; a marker's list-style-image too where its content is normal. Raw, as written; the alternative text after '/' is never shown."""
    import tinycss2  # only here: the rest of the package (pictures, Source) needs no CSS parser
    text, out = False, []
    for t in tinycss2.parse_component_value_list(c.get('content') or ''):
        if t.type == 'literal' and t.value == '/': break
        name = getattr(t, 'lower_name', None) or getattr(t, 'lower_value', None)
        if t.type == 'string' or name in TEXT_CONTENT.get(t.type, ()): text = text or t.type != 'string' or t.value != ''
        elif t.type != 'whitespace' and not (t.type == 'ident' and name in NO_CONTENT): out.append('unread: ' + t.message if t.type == 'error' else t.serialize())
    if marker and (c.get('content') or 'normal') == 'normal' and (c.get('list-style-image') or 'none') != 'none': out.append(c['list-style-image'])
    return text, out


def _generated_owners(raw, vis, runs, marks, gen, units):
    """`generated_content` from the page's own readings (`_generated`), in their tree order: each pseudo element's fragments and computed readings and
    its `role` by native pseudo type (PSEUDO_ROLE). One that formats text already there (first-letter) inserts nothing and is never placed; where the
    units carry the source text it formats (`_holders`), its strike or raise, a hidden or unproved visibility or an unproved paint is not carried (PARTIAL). One of any other type is kept raw (PARTIAL where it shows content). One that inserts is `required` unless
    checkVisibility on the pseudo element proves it hidden - a transparent colour leaves paint `uncertain`, never hidden - and, where its owner's whole
    source content is proved (every source run under the owner marked, the page's own (`_bound`), contiguous with no foreign or literal run inside,
    no native text outside a run, all held by units, no first-letter over a before that names text), `at`: the unit or cell and the character offset in its text
    where it stands (before/marker: before the owner's first character a unit holds; after: after its last), from the existing source-to-text
    reading (anchor._reading) - else `unbound_because` (one not shown is given no place); records at one offset apply in their order. `status` complete only where it was read and
    every required one is bound, no non-text item among them (`non_text`, by the native tokens of its computed content: `_content`); else PARTIAL with `why`."""
    if not gen or not gen.get('read'): return {'read': False, **({'error': gen['error']} if gen else {}), 'records': [], 'status': 'PARTIAL', 'why': ['generated content: no native reading']}
    held, owner_key, _ = edgartools_html._holders(units, vis); item = {}
    for u in units:
        for x in ([c for c in u.get('cells') or []] if u.get('kind') == 'table' else [u]):
            sp = [a for a in anchor.spans(x.get('anchor')) if 'byte_start' in a]
            if sp: item[(u['id'], sp[0]['byte_start'] if u.get('kind') == 'table' else None)] = x
    formats, out, why = {r['owner']: r['pseudo'] for r in gen['records'] if PSEUDO_ROLE.get(r['pseudo']) == 'formats'}, [], set()
    for r in gen['records']:
        role = PSEUDO_ROLE.get(r['pseudo'])
        text, non = _content(r['computed'], r['pseudo'] == 'marker')
        rec = {k: r[k] for k in ('pseudo', 'fragments', 'bounds', 'computed', 'background') if k in r}; rec.update(role=role, non_text=non, visible=r.get('visible'))
        if r.get('visible_error'): rec['visible_error'] = r['visible_error']
        c = r['computed']; rec['required'] = role != 'formats' and r.get('visible') is not False and bool(r['fragments'] or non or (text and r['owner'] in formats))  # text a first-letter took whole leaves no fragment of its own
        if c.get('opacity') == '0' or re.match(r'rgba\(.*,\s*0\)$', c.get('color', '')) or c.get('color') == 'transparent': rec['paint'] = 'uncertain'  # a shadow or stroke may still paint it
        struck, lift = 'line-through' in (c.get('-webkit-text-decorations-in-effect') or '').split(), c.get('vertical-align') or 'baseline'
        if struck or lift != 'baseline': rec['formatting'] = {**({'struck': True} if struck else {}), **({'vertical_align': lift} if lift != 'baseline' else {})}  # the existing meanings, kept with the text: decorations in effect (own or an ancestor's), raise or lower
        mine = [k for k in r['runs'] if runs[k][3] and _glyphs(raw, runs[k][1])[1]]; reason = None
        if role != 'inserts' or not rec['required']:  # kept raw, never placed: no place is given to text that is not shown
            rec.update(bound=False, unbound_because='its native pseudo type is not handled' if not role else 'it formats text already there' if role == 'formats' else 'not shown' if r.get('visible') is False else 'it shows nothing')
            carried = role == 'formats' and bool(mine) and bool(held(runs[mine[0]][1][0][0], runs[mine[-1]][1][-1][1])[0])  # the source text it formats is in the units as written (none there, as when all of it is hidden: nothing to say)
            if carried and rec.get('formatting'): why.add('source text formatting by ::%s not carried' % r['pseudo'])
            if carried and r.get('visible') is False: why.add('source text in the units is hidden by ::%s' % r['pseudo'])
            elif carried and r.get('visible') is None: why.add('source text in the units: its visibility under ::%s is not proved' % r['pseudo'])
            elif carried and rec.get('paint') == 'uncertain': why.add('source text in the units: its paint under ::%s is not proved' % r['pseudo'])  # a transparent letter: never hidden, never proved
            if not role and rec['required']: why.add('native pseudo element ::%s not handled' % r['pseudo'])
            out.append(rec); continue
        if r['pseudo'] == 'before' and r['owner'] in formats and (r['fragments'] or text): reason = '::%s may format part of it' % formats[r['owner']]  # its first letter may be this text's, or all of it: which is not proved
        elif r['unknown_text']: reason = 'native text under the owner follows no source run'
        elif not mine: reason = 'the owner has no proved source text'
        elif any(not (marks or {}).get(str(k)) or not _bound(_glyphs(raw, runs[k][1])[1], marks[str(k)]['text']) for k in mine): reason = "a run under the owner is not the page's"
        elif any(k not in mine and (_glyphs(raw, runs[k][1])[1] or not runs[k][3]) for k in range(mine[0], mine[-1] + 1)): reason = 'a foreign or literal run stands inside the owner'
        else:
            lo, hi = runs[mine[0]][1][0][0], runs[mine[-1]][1][-1][1]; got, n, unheld = held(lo, hi)
            edge = lo if r['pseudo'] != 'after' else hi
            glyphs = [g for k in mine for g in runs[k][1]]  # its first (after: last) glyph a unit holds: a collapsed edge space no unit holds is no text (the whole-owner check counts no white space unheld)
            near = next((h for h in (held(a, b)[0] for a, b in (glyphs if r['pseudo'] != 'after' else glyphs[::-1])) if h), {})
            if unheld or len(near) != 1: reason = 'the owner text is not held by one unit at its edge'
            else:
                key = next(iter(near)); reading = anchor._reading(vis, item.get(key, {}))
                pos = None if reading is None else [i for i, k in enumerate(reading[2]) if (vis.s[k] >= edge if r['pseudo'] != 'after' else vis.e[k] <= edge)]
                if not pos: reason = 'its place in the unit text is not proved'
                else:
                    i = pos[0] if r['pseudo'] != 'after' else pos[-1]
                    rec['at'] = {**owner_key(key), 'offset': reading[1][i] if r['pseudo'] != 'after' else reading[1][i] + 1}
        rec['bound'] = 'at' in rec
        if not rec['bound']: rec['unbound_because'] = reason
        if rec['required'] and rec['non_text']: why.add('generated non-text content not extracted')
        if rec['required'] and not rec['bound']: why.add('generated text not bound: ' + reason)
        if rec['required'] and r.get('visible') is None: why.add('generated text: its visibility is not proved')  # shown or hidden unproved: its raw reading and error kept
        out.append(rec)
    images = gen.get('background_images') or []
    if any(x['visibility'] == 'visible' for x in images): why.add('background image content not read')  # a picture the page paints behind or without text: kept raw, never read here
    return {'read': True, 'records': out, **({'background_images': images} if images else {}), 'status': 'PARTIAL' if why else 'complete', 'why': sorted(why)}


def measure(marked_html, browser, prefix=None, every=False, decorate=False, raw=None, source=None, refused=None):
    """Boxes of every tagged cell as Chrome lays the document out (the document's own styles, a wide window; the document's scripts never run). Only
    table cells are read: a mark names the td/th it stands first in; one the parser moved out of its cell, or a second in one cell, names nothing,
    and the source never writes the step's own prefix (`marker_prefix`; Codex MEASURE_ALIAS_BASELINE). With a symbol-mark `prefix`, the same page's
    symbol marks (`SYMBOLS_JS`) come third: with `every`, each run's, an ordinary one's too. The page is read as every render reads it: at the
    `source`'s address (none given: the step's own, with no evidence), in the browser's charset for the original `raw` (the bytes given, without
    it), its references answered from that evidence only; one nothing answers raises: the geometry is not proved the original's. Its geometry is the
    page's own: with no run map it claims nothing about any route's text - the screen step (`_step`) applies it only where every marked source run
    shows exactly the characters the route keeps (`every`, `_bound`). `refused`: a list that gets what no evidence answered instead of the raise, the
    readings then made in the same render - for a caller (the screen step) that withholds the geometry and keeps them."""
    source = source or Source('', {})  # no evidence given: nothing answers, so anything the page names leaves its geometry unproved
    page, _, first = _document(browser, marked_html if raw is None else raw, marked_html, source)
    try:
        unproved = [url for url, kind in source.refusals[first:] if kind != 'navigation']  # a sheet, font or picture no evidence answered
        if unproved and refused is None: raise RuntimeError('what the page names cannot be read offline, so its geometry is unproved: ' + ', '.join(unproved)[:150])
        if refused is not None: refused.extend(unproved)
        got = page.evaluate(JS) if prefix is None else page.evaluate(JS, prefix)
        try: sym = page.evaluate(SYMBOLS_JS, [prefix, every, decorate]) if prefix is not None else None
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: sym = {'error': repr(e)[:200]}  # the symbols alone: the geometry measured stays (the step says why)
        if prefix is not None:  # the page's own layout of generated content (pseudo elements, list markers), read once in this same page
            try: gen = _generated(page, prefix)
            except (OSError, StorageError, ImportError, MemoryError): raise
            except Exception as e: gen = {'read': False, 'error': repr(e)[:200]}
            sym = dict(sym, generated=gen)
    finally:
        page.close()
    by_table = {}
    for c in got['cells']: by_table.setdefault(c['table'], []).append(c)
    return (by_table, got['boxes']) if prefix is None else (by_table, got['boxes'], sym)


LINKS_JS = """p => { const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT), tags = new Map(), out = {links: {}, runs: {}, pictures: {}, reconstructed: 0}, mark = new RegExp('^' + p + '([sqa]):([0-9]+)$');
  const marks = []; for (let c = w.nextNode(); c; c = w.nextNode()) { const m = mark.exec(c.data); if (m) marks.push([m[1], m[2], c]); }
  for (const [kind, k, c] of marks) if (kind === 'a') { const e = c.parentNode; if (e && e.nodeType === 1 && e.localName === 'a' && e.firstChild === c && !tags.has(e)) { tags.set(e, k); out.links[k] = {href: e.getAttribute('href')}; } else out.links[k] = null; }  // the mark stands first inside the element made for its own tag
  for (const a of document.querySelectorAll('a[href]')) if (!tags.has(a)) out.reconstructed++;  // an <a href> the parser made with no source tag of its own (a reconstruction)
  const near = el => { const a = el && el.closest('a[href]'); return a ? (tags.has(a) ? tags.get(a) : 'reconstructed') : null; };
  for (const [kind, k, c] of marks) {
    if (kind === 'q') { const e = c.nextSibling; out.pictures[k] = e && e.nodeType === 1 && (e.localName === 'img' || e.localName === 'svg') ? near(e) : 'unbound'; }  // PICTURES_JS's own rule: the <img>/<svg> right after its mark, else nothing (a moved picture binds no link)
    if (kind === 's') { let el = null; for (let n = c.nextSibling; n && (n.nodeType === Node.TEXT_NODE || (n.nodeType === Node.COMMENT_NODE && !mark.test(n.data))); n = n.nextSibling) if (n.nodeType === Node.TEXT_NODE) { el = n.parentElement; break; }
      out.runs[k] = el ? near(el) : 'unbound'; } }
  return out; }"""  # each source link's own tag, and the nearest such link of every run and picture mark (closest a[href]), in the visibility render


def _link_owners(raw, vis, runs, near, unsure):  # {'proved': [link starts], 'unproved': {start: [why]}}: a link's owners are proved only where the scan's extent is whole, its tag binds the browser's <a>
    # (href equal), every marked run and picture in that extent stands in it and none outside does, every such run has a verdict, and the parser made no <a href> of its own
    out = {'proved': [], 'unproved': {}}
    for l in vis.links:
        key, end = str(l['start']), l['end']; inside = lambda a, b: end is not None and l['tag_end'] <= a and b <= end
        within = [k for k, (_, chars, _, ok) in enumerate(runs) if ok and inside(chars[0][0], chars[-1][1])]
        literal = any(not ok and inside(chars[0][0], chars[-1][1]) and _glyphs(raw, chars)[1] for _, chars, _, ok in runs)  # a run no mark can reach (raw text, RCDATA): never bound
        got = near['links'].get(key) or {}; holds = any(_glyphs(raw, runs[k][1])[1] for k in within) or any(inside(a, b) for a, b in vis.picture_tags)
        why = [w for w, bad in (('extent', not (l['whole'] and end is not None)), ('tag', got.get('href') != l['href']),
                                 ('no text or picture of its own: that nothing else shows is not proved', not holds),  # never [] on this path (Root: zero own area does not prove an empty link)
                                 ('literal text in it', literal),
                                 ('a run in it stands elsewhere', any(_glyphs(raw, runs[k][1])[1] and near['runs'].get(str(k)) != key for k in within)),
                                 ('a run outside stands in it', any(v == key and int(k) not in within for k, v in near['runs'].items())),
                                 ('a picture in it stands elsewhere', any(inside(a, b) and near['pictures'].get(str(k)) != key for k, (a, b) in enumerate(vis.picture_tags))),
                                 ('a picture outside stands in it', any(v == key and not inside(*vis.picture_tags[int(k)]) for k, v in near['pictures'].items())),
                                 ('a run in it has no verdict', any(k in unsure for k in within if _glyphs(raw, runs[k][1])[1])), ('reconstructed', near['reconstructed'] > 0)) if bad]
        (out['unproved'].__setitem__(key, why) if why else out['proved'].append(l['start']))
    return out


PICTURES_JS = """p => { const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT), out = {};
  while (w.nextNode()) { const c = w.currentNode, e = c.nextSibling;  // a picture mark binds only the <img>/<svg> right after it; one the parser moved binds nothing (null)
    if (c.data.startsWith(p)) out[c.data.slice(p.length)] = e && e.nodeType === 1 && (e.localName === 'img' || e.localName === 'svg') ? e.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) : null; }
  return out; }"""  # the native verdict: no box, CSS visibility other than visible, or opacity 0 on it or an ancestor hide it; its size is not asked (painting is another matter)


def page_visibility(raw, vis, browser, source=None):
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
    request, refused offline: what the sheet shows or hides is not known) - unless the `source`'s evidence answers it (`Source`: the page is then
    read at the source's address)."""
    runs, _ = symbol_runs(raw, vis); prefix = marker_prefix(raw); asked = []; address = 'http://%s.invalid/' % prefix  # an address the source nowhere writes
    if source is not None: address = source.at(address, raw)
    bom = next((len(b) for b in (b'\xef\xbb\xbf', b'\xfe\xff', b'\xff\xfe') if raw.startswith(b)), 0)  # a byte order mark stays first: the browser decodes by it
    marked, _ = tag_cells(raw, vis, (), [(l['tag_end'], b'<!--%sa:%d-->' % (prefix.encode(), l['start'])) for l in vis.links if l['start'] >= bom] + [(a, b'<!--%ss:%d-->' % (prefix.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok and a >= bom] + [(a, b'<!--%sq:%d-->' % (prefix.encode(), k)) for k, (a, _) in enumerate(vis.picture_tags) if a >= bom], prefix, cells=False)  # comments only: no attribute a sheet could select
    page = _offline_page(browser, asked, (address, raw), source)  # first the original bytes as they are: how the browser itself decodes them, and what they ask for
    try: page.goto(address, wait_until='load'); charset = page.evaluate('document.characterSet')
    finally: page.close()
    if source is not None: source.charset = charset  # read once: every later render of this document reads it so
    if asked: raise RuntimeError('style sheets the page names cannot be read offline: ' + ', '.join(asked)[:150])  # every sheet the page names is requested from a page with an address, and refused: what it shows or hides is not known, no verdict at all
    page = _offline_page(browser, None, (address, marked, charset), source)  # then the marked bytes in that charset: a comment cannot move a <meta> out of the browser's reach
    try: page.goto(address, wait_until='load'); got = page.evaluate(SYMBOLS_JS, [prefix, True]); seen = page.evaluate(PICTURES_JS, prefix + 'q:'); near = page.evaluate(LINKS_JS, prefix)
    finally: page.close()
    out, unresolved = {'hidden': [], 'shown': [], 'unproven': 0, 'unbound': []}, []; unsure = set()  # the runs no verdict reached (unbound, unproven)
    for k, (_, chars, hidden, ok) in enumerate(runs):
        glyphs = _glyphs(raw, chars)[1]; m = got['marks'].get(str(k)) if ok else None
        if not glyphs: continue  # white space only: nothing to bind it by
        if m is None or not _bound(glyphs, m['text']):  # listed: text the parser moved, literal or misread, kept as the scanner reads it - and its source beside it
            s, e = chars[0][0], chars[-1][1]; out['unbound'].append([s, e]); unsure.add(k)
            try: fragment = {'raw': raw[s:e].decode('utf-8')}
            except UnicodeDecodeError: fragment = {'bytes': raw[s:e].hex()}
            unresolved.append({'at': {'byte_start': s, 'byte_end_exclusive': e}, **fragment,
                               'why': 'byte order mark' if e <= bom else 'literal text' if not ok else 'unbound' if str(k) in got['marks'] else 'mark not found'})  # as `symbols` says it; the encoding's own mark is no text the page shows
        elif m['visibility'] == 'hidden': out['hidden'].append([chars[0][0], chars[-1][1]])
        elif m['visibility'] == 'unproven': out['unproven'] += 1; unsure.add(k)
        elif hidden: out['shown'].append([chars[0][0], chars[-1][1]])
    if unresolved: out['unresolved'] = unresolved
    if vis.picture_tags: out['pictures'] = {'hidden': [], 'shown': [], 'unbound': []}  # every picture tag (Visible.picture_tags) by its first byte: the page's verdict, or none reached it
    for k, (a, b) in enumerate(vis.picture_tags): out['pictures']['unbound' if seen.get(str(k)) is None else 'shown' if seen[str(k)] else 'hidden'].append(a)
    if vis.picture_tags and out['pictures']['unbound']: out['unresolved_pictures'] = [{'at': {'byte_start': a, 'byte_end_exclusive': b}, 'raw': raw[a:b].decode('utf-8', 'replace'), 'why': 'unbound'} for a, b in vis.picture_tags if a in out['pictures']['unbound']]  # the tag as written: the scanner's reading stays for it
    if vis.links: out['links'] = _link_owners(raw, vis, runs, near, unsure)  # which link each run and picture stands in, as this render shows it
    return out


def step(raw, route, browser):
    """The step on one document's route (the caller's bytes and browser): its tables gridded as Chrome lays them out (`apply`), the spaces the tool
    added measured and joined where Chrome shows them touching on one baseline (`join`), in a file the scanner cannot read for certain the units'
    endpoint boxes recorded; the route record names the step. Returns the step's facts; a page that cannot be measured keeps the route's content and
    anchors as they were, adds only the failure evidence (`source_symbols` read: false) and says why; a failed symbol reading alone keeps the geometry
    measured, says the same, and its error makes the route PARTIAL. Bytes that are not the route's source raise ValueError before any browser work; storage, dependency and resource errors propagate."""
    anchor.check_source(raw, route.get('sha256'))
    t0 = time.time(); return _step(raw, route, browser, Visible(raw, page=route.get('page_visibility')), t0)  # the reading the route was made with; the step's time counts its own scan


def _step(raw, route, browser, vis, t0=None, source=None):  # `step` on a reading already made of the route's own bytes (html_route.prepare, which checked them): the one the route was made with
    if vis.page != route.get('page_visibility'): raise ValueError('the screen step reads the source as the route was read (its page visibility), not another reading')
    decorate = vis.paged or not vis.struck_certain  # strike-through the scanner cannot certify (a browser-read page never is): this render decides it
    t0 = time.time() if t0 is None else t0; gaps = gaps_of(vis, route['units']); endpoints = endpoints_of(vis, route['units']) if not vis.certain else []  # a reading made before the step is not its time
    (runs, unread), prefix = symbol_runs(raw, vis), marker_prefix(raw)
    marked, spans = tag_cells(raw, vis, gaps + endpoints, [(a, b'<!--%ss:%d-->' % (prefix.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], prefix)
    refused = []  # what the page names and no evidence answered: the geometry is withheld, the readings of the same render kept
    try: measured, boxes, got = measure(marked, browser, prefix, every=True, decorate=True, raw=raw, source=source, refused=refused) if decorate else measure(marked, browser, prefix, every=True, raw=raw, source=source, refused=refused)
    except (OSError, StorageError, ImportError, MemoryError): raise
    except Exception as e:
        if not browser.is_connected(): raise
        err = repr(e)[:200]; route['source_symbols'], route['source_inline'] = {'read': False, 'error': err}, {'read': False, 'error': err}  # content and anchors stay; the failure is said, never an empty success
        route['source_style'] = {'read': False, 'error': err}  # no render, no style: a fallback page's is never a proved original style
        return {'error': repr(e)[:200]}
    if 'error' in got and not browser.is_connected(): raise RuntimeError('browser disconnected: ' + got['error'])
    marks = None if 'error' in got else got['marks']  # each marked run's own text as this render shows it (`every`)
    bom = next((len(b) for b in (b'\xef\xbb\xbf', b'\xfe\xff', b'\xff\xfe') if raw.startswith(b)), 0)  # the encoding's own mark: no text the page shows (as page_visibility and decorations)
    off = None if marks is None else sum(1 for k, (_, chars, _, ok) in enumerate(runs) if ok and chars[-1][1] > bom and (g := [(x, c if c is not None else vis.at(*x) or None) for x, c in _glyphs(raw, chars)[1]]) and not (marks.get(str(k)) and _bound(g, marks[str(k)]['text'])))  # where `_char` cannot decode bytes, the text the scan already keeps for them (anchor.Visible: one cp1252 character per byte for a file that is not UTF-8)
    if marks is not None:  # the readers below take an ordinary run by its id only, as a reading without `every` gives it
        plain = {k for k, m in marks.items() if m is not None and 'family' not in m}; got = dict(got, plain=','.join(sorted(plain)), marks={k: m for k, m in marks.items() if k not in plain})
    proved = off == 0 and not refused  # the geometry is the page's: it applies only where the page shows every marked source run exactly as the scan reads it - a run missing, moved or read otherwise (another decoding too), or no reading of the runs at all, leaves it unproved; every reading below is kept either way, each bound run by run
    unproved = '; '.join(([repr(RuntimeError('what the page names cannot be read offline, so its geometry is unproved: ' + ', '.join(refused)[:150]))[:200]] if refused else []) +
                         (["RuntimeError('the page shows %d source run%s otherwise than the scan reads %s, so its geometry is unproved')" % (off, '' if off == 1 else 's', 'it' if off == 1 else 'them')] if off else [])) or None  # no charset diagnosis
    if endpoints and proved:  # source-bound endpoints, measured in the existing render; no answer key chooses them
        route['screen_endpoints'] = {side: {str(g[0][side]): boxes[str(len(gaps) + n) + '.' + str(ix)] for n, g in enumerate(endpoints) if str(len(gaps) + n) + '.' + str(ix) in boxes} for ix, side in enumerate(('start', 'end'))}
    route['source_symbols'] = {'read': False, 'error': got['error']} if 'error' in got else {'read': True, 'decoder': 'dingbat-to-unicode 1.0.2', 'records': symbols(raw, vis, runs, got, route['units']), **({'unread': unread} if unread else {})}
    n = 0
    if proved: n = apply(route['units'], spans, measured); join(gaps, boxes, vis); route['route'] = dict(route['route'], name=route['route']['name'] + '+screen', settings=dict(route['route'].get('settings') or {}, screen_grid=True, joins='touching on one baseline', parts='apart on one baseline'))
    route['source_inline'] = {'read': False, 'error': got['error']} if 'error' in got else {'read': True, **inline(raw, vis, runs, got, route['units']), **({'unread': unread} if unread else {})}  # the owners' final text: after the re-grid and the joins (where the geometry applies)
    route['generated_content'] = _generated_owners(raw, vis, runs, marks, got.get('generated'), route['units'])  # the page's own generated content, on the final units
    route['route'] = dict(route['route'], settings=dict(route['route'].get('settings') or {}, generated_content='native layout (DOMSnapshot); proved whole owners'))
    generated = None if route['generated_content']['status'] == 'complete' else 'generated: ' + '; '.join(route['generated_content']['why'])
    seen = None if 'error' in got else {**styles(raw, vis, runs, dict(got, marks=marks), route['units']), **({'unread': unread} if unread else {})}  # every bound run's own colour, on the same final text (every run's mark, ordinary ones too)
    route['source_style'] = ({'read': False, 'error': got['error']} if seen is None else {'read': True, **seen} if not refused else  # what the page names and no evidence answered may set any colour: the render's is kept as a fallback reading, never the proved original
                             {'read': False, 'error': repr(RuntimeError('what the page names cannot be read offline, so its colours are unproved: ' + ', '.join(refused)[:150]))[:200], 'fallback': seen})
    edited = {id(x): x for x, *_ in gaps}.values()
    formatting = None
    if decorate:  # the source-formatting owner, on the final units (joins and parts done), from this render's own verdict per source run
        from driver.prepare.convert import source_formatting
        n_struck, undecided = source_formatting.rendered(vis, route, None if 'error' in got else decorations(raw, vis, runs, got))
        if undecided: route['source_formatting'] = {'unresolved': undecided}
        k = sum(r[2] != 'unresolved: visibility' for r in undecided or [])  # a run whose visibility is itself unresolved is said once, by the visibility verdict
        formatting = 'source formatting: no native decoration verdict' if n_struck is None else 'source formatting: %d text run%s without a native decoration verdict' % (k, '' if k == 1 else 's') if k else None
    return {'cells_regridded': n, 'cells_measured': sum(len(v) for v in measured.values()), 'spaces_the_tool_added': sum(a < b for _, a, b, _, _ in gaps), 'joined': sum(len(x.get('joins', ())) for x in edited),
            'boundaries_the_tool_dropped': sum(a == b for _, a, b, _, _ in gaps), 'parted': sum(len(x.get('parts', ())) for x in edited), 'seconds': round(time.time() - t0, 1),
            **({'source_formatting': n_struck} if decorate else {}),  # items the render's own decoration proved struck (None: no verdict)
            **({'error': '; '.join(x for x in ('symbols: ' + got['error'] if 'error' in got else None, unproved, formatting, generated) if x)} if 'error' in got or unproved or formatting or generated else {})}  # html_route marks the route PARTIAL with it
