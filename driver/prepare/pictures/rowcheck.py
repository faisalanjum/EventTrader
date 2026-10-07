# Page checker v8: do two readings of a picture hold the same text AND the same table relationships? One decision for every
# use (two readers agreeing, a reading scored against exact answers, validation). Text: the grader's own comparison
# (grade.critical: every ordered difference, and which touch numbers, signs or negations; nothing filtered) on plain text.
# Only identified layout comes out (cell bars, tabs, a bullet that starts a line or cell, dot leaders, code-fence lines);
# stars, operators, exact fractions and the role of raised or lowered text (⌃ raised, ⌄ lowered) stay. Each reader declares
# its format (HTML or text); HTML is read by one parser for text and tables, never by stripping '<...>'; a table caption is
# read as a line where it stands. Tables: kept apart; cells placed by the grader's approved occupancy rule (edgartools_html
# adapter, checks/real_pairs.py: a column is taken until the row its rowspan ends; Codex R7-2); heading roles from the markup
# (th, thead, scope); every non-empty cell, text or number, is one fact: (table, row, column, span, role, text, column
# headings above it, row headings and row label beside it) - the grader's cell model. Two readings agree on tables only when
# their facts are identical. Not certifiable, so unresolved: pipe or tab rows with a digit (free tools, PDF answer rows),
# 'data-uncertain' anywhere, a table inside a table, text inside a table outside its cells and caption, a span that is not a
# whole number from 1 to 1000 or that overlaps another, and '[?]' (unread text is not agreement).
# Three outcomes: same | unresolved | differs. Only "same" passes. Earlier: rowcheck_v6_backup.py, _v5_, _v4_ (text only), _v3_.
import collections, re, statistics, unicodedata
from html.parser import HTMLParser
from ..compare import _TOKEN, critical, norm, reading_units, spacing_only, wer_counts  # the grader's own functions, shared

VULGAR = {'½': '1/2', '⅓': '1/3', '⅔': '2/3', '¼': '1/4', '¾': '3/4', '⅛': '1/8', '⅜': '3/8', '⅝': '5/8', '⅞': '7/8'}

SUP, SUB = '⁰¹²³⁴⁵⁶⁷⁸⁹⁽⁾⁺⁻', '₀₁₂₃₄₅₆₇₈₉₍₎₊₋'

SUPD, SUBD = str.maketrans(SUP, '0123456789()+-'), str.maketrans(SUB, '0123456789()+-')

RAISED, LOWERED = '⌃', '⌄'                                       # the role of raised / lowered text, kept through the comparison

def _fractions(s):  # every way of writing 8⅜ (8³⁄₈, 8³/₈, 8<sup>3</sup>/<sub>8</sub>, 8 3/8) -> '8 3/8': one exact form, never rounded.
    for v, f in VULGAR.items(): s = s.replace(v, ' ' + f)      # A raised digit is a numerator only over a lowered one or after the fraction slash ⁄
    s = re.sub(r'([⁰¹²³⁴⁵⁶⁷⁸⁹]+)(?:\s*[⁄/]\s*([₀₁₂₃₄₅₆₇₈₉]+)|⁄(\d+))', lambda m: ' ' + m.group(1).translate(SUPD) + '/' + (m.group(2) or m.group(3)).translate(SUBD), s)   # raised over lowered, or the fraction slash
    s = re.sub(RAISED + r'\s*(\d+)\s*[⁄/]\s*' + LOWERED + r'\s*(\d+)', r' \1/\2', s)        # HTML: a raised numerator over a lowered denominator
    return re.sub(r'(?<![\d.,/])(\d{1,3}) +(\d{1,2}) ?/ ?(\d{1,2})(?![\d/])', r'\1 \2/\3', s.replace('⁄', '/'))

def plain(text):
    """A reading as plain text: identified layout out, every printed character and its raised/lowered role kept. Out: code-fence
    lines (wrapping), cell bars and tabs (two spaces in their place), dot leaders, spaces inside brackets and before '%'. Kept:
    every printed mark as itself (bullets • ▪ ●, footnote marks, checkboxes ☐ ☒): a mark's role is not known from its place.
    Folded: fractions to one exact form; Unicode
    raised/lowered characters to the role mark + digits (² -> ⌃2), as HTML <sup>/<sub> are; the PDF text layer's hyphen mark
    U+FFFE is a hyphen; compatibility forms (NFKC: ligatures, full-width). Stars, inequalities and letter spacing stay as printed."""
    s = _fractions(re.sub(r'(?m)^\s*```[\w-]*\s*$', '', text).replace('￾', '-'))
    s = re.sub('[' + SUP + ']+', lambda m: ' ' + RAISED + m.group().translate(SUPD) + ' ', s)
    s = re.sub('[' + SUB + ']+', lambda m: ' ' + LOWERED + m.group().translate(SUBD) + ' ', s)
    s = s.replace('|', '  ').replace('\t', '  ')                                         # every printed mark kept as itself (Codex v8 C1)
    s = unicodedata.normalize('NFKC', re.sub(r'(?:\.\s*){3,}', '  ', s))
    return re.sub(r'(\d) %', r'\1%', re.sub(r'\( +', '(', re.sub(r' +\)', ')', s)))

BLOCK = {'p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'table', 'section', 'header', 'footer', 'blockquote', 'pre', 'hr'}

SNIFF = re.compile(r'<(?:table|tr|td|th|thead|tbody|caption|div|p|span|br|sup|sub|h[1-6]|li|ul|ol|b|i|em|strong|img)\b', re.I)

class _Html(HTMLParser):
    """One HTML reading: text lines in order (a table row is one line, cells joined by ' | '; a caption is a line where it stands),
    lines outside tables, tables as {rows of cells {text, cs, rs, head, scope}, row groups}, and whether anything is uncertain or
    unsupported. Inside a cell or caption a block or line break keeps words apart; inline fragments stay joined. A list item
    starts a line; the markup's own marker is not invented (a mark the reader writes as text stays). A checkbox is ☒ (checked)
    or ☐ where it stands; any other form control is not certified."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.free, self.tables, self.uncertain = [], [], [], False
        self.buf, self.cell, self.row, self.rows, self.cap, self.thead, self.depth = [], None, None, None, None, False, 0
        self.group, self.cur = 0, None                                   # row groups: thead/tbody/tfoot, or a run of rows outside them
    def _sink(self): return self.cell['text'] if self.cell is not None else self.cap if self.cap is not None else self.buf
    def _end_line(self):
        t = ''.join(self.buf)
        if t.strip():
            if self.rows is None: self.free.append(t)
            else: self.uncertain = True                               # text inside a table outside its cells: kept, not certified
            self.lines.append(t)
        self.buf = []
    def _end_caption(self):                                          # a caption ends at its end tag, any table part, the table's end or EOF
        if self.cap is not None:
            t = ''.join(self.cap)
            if t.strip(): self.lines.append(t)
            self.cap = None
    def _end_cell(self):
        if self.cell is not None: self.row.append(dict(self.cell, text=''.join(self.cell['text']))); self.cell = None
    def _end_row(self):
        self._end_cell()
        if self.row is not None:
            self.rows['rows'].append(self.row); self.rows['groups'].append(self.row_group)
            self.lines.append(' | '.join(c['text'] for c in self.row)); self.row = None
    def _start_row(self):
        self._end_caption(); self._end_line(); self._end_row()
        if self.cur is None: self.group += 1; self.cur = ('rows', self.group)  # rows outside an explicit group form one implicit group
        self.row, self.row_group = [], self.cur
    def handle_starttag(self, tag, attrs):
        a, names = dict(attrs), [k for k, _ in attrs]
        if 'data-uncertain' in a: self.uncertain = True
        if any(names.count(k) > 1 for k in ('colspan', 'rowspan', 'checked', 'type')): self.uncertain = True   # browsers keep the first, dict the last
        if tag == 'table':
            self.depth += 1
            if self.depth == 1: self._end_line(); self.rows, self.cur = {'rows': [], 'groups': []}, None
            else: self.uncertain = True                               # a table inside a table: its text stays in the cell, not certified
            return
        if tag in ('sup', 'sub'): self._sink().append(' ' + (RAISED if tag == 'sup' else LOWERED)); return
        if tag == 'input':
            if (a.get('type') or '').lower() == 'checkbox': self._sink().append(' ' + ('☒' if 'checked' in names else '☐') + ' ')
            else: self.uncertain = True
            return
        if tag in ('select', 'textarea', 'button'): self.uncertain = True; return
        if self.depth > 1: return
        inside = self.cell is not None or self.cap is not None
        if tag == 'caption' and self.rows is not None: self._end_caption(); self._end_line(); self.cap = []
        elif tag in ('thead', 'tbody', 'tfoot') and self.rows is not None:
            self._end_caption(); self._end_line(); self._end_row(); self.group += 1; self.cur = (tag, self.group); self.thead = tag == 'thead'
        elif tag == 'tr' and self.rows is not None: self._start_row()
        elif tag in ('td', 'th') and self.rows is not None:
            if self.row is None: self._start_row()
            self._end_caption(); self._end_line(); self._end_cell()
            def span(k):
                vs = [v for kk, v in attrs if kk == k]
                if not vs: return 1
                v = (vs[0] or '').strip()
                if not re.fullmatch('[0-9]+', v) or not 1 <= int(v) <= 1000: self.uncertain = True; return 1   # "0", "²", "٢", "x", 5000: not certified
                return int(v)
            self.cell = dict(text=[], cs=span('colspan'), rs=span('rowspan'), head=tag == 'th' or self.thead, scope=(a.get('scope') or '').lower())
        elif tag == 'li':                                                # a list item: its marker is decoration (the markup says list)
            if inside: self._sink().append(' ')
            elif self.rows is None: self._end_line()
        elif tag in BLOCK:
            if inside: self._sink().append(' ')
            elif self.rows is None: self._end_line()
    def handle_endtag(self, tag):
        if tag == 'table':
            self.depth -= 1
            if self.depth == 0 and self.rows is not None:
                self._end_caption(); self._end_line(); self._end_row(); self.tables.append(self.rows); self.rows = None
            return
        if tag in ('sup', 'sub'): self._sink().append(' '); return
        if self.depth > 1: return
        inside = self.cell is not None or self.cap is not None
        if tag == 'caption': self._end_caption()
        elif tag in ('thead', 'tbody', 'tfoot') and self.rows is not None: self._end_row(); self.thead = False; self.cur = None
        elif tag in ('td', 'th'): self._end_cell()
        elif tag == 'tr': self._end_row()
        elif tag in BLOCK | {'li'}:
            if inside: self._sink().append(' ')
            elif self.rows is None: self._end_line()
    def handle_data(self, d):
        if self.cell is not None or self.cap is not None: self._sink().append(d.replace('\n', ' '))
        else:
            parts = d.split('\n'); self.buf.append(parts[0])
            for p in parts[1:]: self._end_line(); self.buf.append(p)
    def close(self):
        super().close()
        self._end_caption()
        if self.rows is not None: self._end_line(); self._end_row(); self.tables.append(self.rows); self.rows = None
        self._end_line()

def read(x, fmt=None):
    """(text lines, tables or None, lines outside tables, uncertain) of one reading in its declared format: 'html' through the
    parser (entities decoded once there), 'text' as lines. fmt None: HTML when the text holds an HTML tag, else text."""
    if fmt == 'html' or (fmt is None and SNIFF.search(x)): p = _Html(); p.feed(x); p.close(); return p.lines, p.tables, p.free, p.uncertain
    lines = x.split('\n'); return lines, None, lines, False

def boxes_to_lines(boxes):  # free tools: rebuild visual rows from box geometry (y-overlap), left to right, boxes by tabs (gaps, not proven columns)
    bs = []
    for b in boxes:
        v = b['box']; xs, ys = v[0::2], v[1::2]
        bs.append((min(ys), max(ys), min(xs), b['t']))
    if not bs: return []
    mh = statistics.median(y1 - y0 for y0, y1, _, _ in bs) or 1
    rows = []
    for y0, y1, x0, t in sorted(bs, key=lambda b: (b[0] + b[1]) / 2):
        c = (y0 + y1) / 2
        if rows and abs(c - rows[-1][0]) <= 0.5 * mh: rows[-1][1].append((x0, t)); rows[-1][0] = (rows[-1][0] + c) / 2
        else: rows.append([c, [(x0, t)]])
    return ['\t'.join(t for _, t in sorted(r[1])) for r in rows]

def placed(tb):
    """One table's cells on its grid, as facts() places them (the placement shared with the position check): each cell with its
    row r, column c, index i in its row, comparison key and role (row/col heading or data); None when the table cannot be placed
    as declared (a span reaching a slot still taken, or a rowspan reaching past its row group)."""
    key = lambda c: ' '.join(_TOKEN.findall(norm(plain(c))))
    rows, groups = tb['rows'], tb['groups']
    last = {r: max(q for q in range(len(rows)) if groups[q] == groups[r]) for r in range(len(rows))}   # each row group's last row
    cells, until = [], {}
    for r, row in enumerate(rows):
        if r and groups[r] != groups[r - 1]: until = {}                # spans never reach into another row group
        c = 0
        for i, x in enumerate(row):
            while until.get(c, 0) > r: c += 1
            if any(until.get(k, 0) > r for k in range(c, c + x['cs'])) or r + x['rs'] - 1 > last[r]: return None
            for k in range(c, c + x['cs']): until[k] = r + x['rs']
            cells.append(dict(x, r=r, c=c, i=i, key=key(x['text']))); c += x['cs']
    for x in cells:
        data_in_row = any(not y['head'] for y in rows[x['r']])
        x['role'] = ('row' if x['scope'].startswith('row') else 'col' if x['scope'].startswith('col') else 'row' if data_in_row else 'col') if x['head'] else 'data'
    return cells

def facts(tables):
    """Every non-empty cell of every table as one relationship fact, or None when a table cannot be placed as declared.
    Placement: the grader's occupancy rule (a column is taken until the row its rowspan ends; each cell at the first free column;
    edgartools_html adapter, checks/real_pairs.py, Codex R7-2), within its row group (thead, tbody, tfoot, or a run of rows
    outside them): a span reaching a slot still taken, or a rowspan reaching past its group, is not placed (None). Roles from the
    markup: a th or thead cell is a heading; scope row/col says which kind, otherwise a heading in a row that also holds data
    cells heads its row, else its column. A column heading governs the cells below it whose columns its span touches (grader's
    col_hit); a row heading or the row's first cell governs the cells to its right. Row identity: heading rows and data rows
    counted apart, rows without any filled cell skipped. Spans are kept as declared. One shape is layout, not a relationship: a
    table of exactly one row with one cell (a title wrapper), whose text is compared as text."""
    out = collections.Counter()
    tables = [tb for tb in tables if not (len(tb['rows']) == 1 and len(tb['rows'][0]) == 1)]
    for t, tb in enumerate(tables):
        rows, cells = tb['rows'], placed(tb)
        if cells is None: return None
        filled = sorted({x['r'] for x in cells if x['key']})
        head_rows = [r for r in filled if all(y['head'] for y in rows[r])]
        rid = {r: ('h', head_rows.index(r)) if r in head_rows else ('d', [q for q in filled if q not in head_rows].index(r)) for r in filled}
        for x in cells:
            if not x['key']: continue
            cols, rws = range(x['c'], x['c'] + x['cs']), range(x['r'], x['r'] + x['rs'])
            ch = tuple(h['key'] for h in cells if h['role'] == 'col' and h['key'] and h['r'] + h['rs'] <= x['r'] and any(h['c'] <= c < h['c'] + h['cs'] for c in cols))
            rh = tuple(h['key'] for h in cells if h['role'] == 'row' and h['key'] and h is not x and h['c'] + h['cs'] <= x['c'] and any(h['r'] <= r < h['r'] + h['rs'] for r in rws))
            first = next((y for y in cells if y['c'] == 0 and y['r'] <= x['r'] < y['r'] + y['rs']), None)
            label = first['key'] if first is not None and first is not x else ''
            out[(t, rid[x['r']], x['c'], x['cs'], x['rs'], x['role'], x['key'], ch, rh, label)] += 1
    return out

def _loose(line):  # a line outside any table holding two or more cells (bars or tabs) and a digit: relationships unproven
    cells = [c for c in re.split(r'\t|\|', line) if c.strip()]
    return len(cells) >= 2 and any(re.search(r'\d', c) for c in cells)

def compare(got, want, got_fmt=None, want_fmt=None):
    """The one decision. 'same': the same reading units in the same order, and the same table relationships (identical facts;
    no loose cell lines; nothing uncertain or unsupported), and nothing left unread. 'unresolved': the same units in another
    order (a heading set on two lines, or a swap: the text cannot tell which); the same characters spaced differently (why=
    'spacing', grader's spacing_only); the same text with relationships not proven (why='columns'); the same text with '[?]'
    in it (why='unreadable'). 'differs': anything else. Two empty readings are 'unresolved' (two free tools read nothing on
    the BUNGE and bxp logos, Oct 5). Formats: 'html' or 'text', declared by the caller (None: sniffed)."""
    (lg, tg, fg, ug), (lw, tw, fw, uw) = read(got, got_fmt), read(want, want_fmt)
    g, w = plain('\n'.join(lg)), plain('\n'.join(lw))
    a, b = reading_units(w), reading_units(g)
    pieces = lambda t: collections.Counter(_TOKEN.findall(norm(t).replace('−', '-')))   # single tokens: reading units join neighbours
    verdict = 'unresolved' if not a and not b else 'same' if a == b else 'unresolved' if pieces(w) == pieces(g) else 'differs'
    why = None
    if verdict == 'differs' and spacing_only(g, w): verdict, why = 'unresolved', 'spacing'
    if verdict == 'same' and ('[?]' in g or '[?]' in w): verdict, why = 'unresolved', 'unreadable'
    if verdict == 'same':
        fa, fb = facts(tg or []), facts(tw or [])
        if ug or uw or fa is None or fb is None or any(map(_loose, fg + fw)) or fa != fb: verdict, why = 'unresolved', 'columns'
    return dict(verdict=verdict, why=why, **critical(g, w), words=wer_counts(g, w))
