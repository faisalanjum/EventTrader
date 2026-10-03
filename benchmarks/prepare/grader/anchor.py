"""Visible text of an original file with byte spans, and a linker that places a tool's output back in it.
Standard library only. Used by the grader (honest anchors, nothing lost) and by route adapters whose tool gives
no source positions (Docling on HTML). The linker never adds, repairs or reorders text: a unit whose text is not
in the source stays unanchored and the source text it should have covered is reported as uncovered. A cell that sits
in several source places (a merged stacked header) must come from the adapter with a list of anchors; the linker
never guesses such a split."""
from array import array
from bisect import bisect_left
import difflib
import html
import re
import unicodedata

# Character classes come from the Unicode database, never from hand-written lists:
#   whitespace = Unicode whitespace plus format marks (zero-width, soft hyphen, direction marks: category Cf);
#   E8 folding = quotation-mark glyphs to their class's ASCII mark (double stays double, single stays single: 6" is not 6'),
#   every dash (Pd) and the minus sign to a hyphen.
_CF = ''.join(chr(i) for i in range(0x110000) if unicodedata.category(chr(i)) == 'Cf')
_WS = re.compile('[\\s' + re.escape(_CF) + ']+')
_FOLD = str.maketrans({**{chr(i): ('"' if ('DOUBLE' in unicodedata.name(chr(i), '') or chr(i) == '"') else "'") for i in range(0x110000) if 'QUOTATION MARK' in unicodedata.name(chr(i), '')},
                       **{chr(i): '-' for i in range(0x110000) if unicodedata.category(chr(i)) == 'Pd' or unicodedata.name(chr(i), '') == 'MINUS SIGN'}})
_TOKEN = re.compile(r'<!--.*?-->|<(script|style|head|title|template)\b[^>]*>.*?</\1\s*>|<[!?][^>]*>|<(?:[^>"\']|"[^"]*"|\'[^\']*\')*>|&#?\w+;|[^<&]+|[<&]', re.S | re.I)
_ATTR = re.compile(r'''([^\s"'=<>/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>]+)))?''')  # one attribute: name, quoted or bare value
_DECL = re.compile(r'([A-Za-z-]+)\s*:\s*([^;]+)')  # one CSS declaration inside a style attribute
_INLINE_DISPLAY = {'inline', 'inline-block', 'inline-flex', 'inline-grid', 'inline-table', 'contents', 'ruby'}  # CSS display values that keep text in the line
_SHEET = re.compile(r'<style\b[^>]*>(?:(?!</style).)*?\b(?:display|visibility|opacity)\s*:|<link\b[^>]*\bstylesheet\b', re.I | re.S)  # stylesheet rules that hide or re-flow text; this scanner does not apply them
_NAME = re.compile(r'</?\s*([\w:.-]+)')
# CSS that removes an element from view (the medium's own rules, guide 2.2 "the screen is the truth"): not shown at all,
# or shown at a size no reader can see (1pt text printed behind slide pictures)
# Hidden subtrees (E16). display:none, opacity:0 and inline-XBRL <ix:hidden> hide every descendant; visibility is inherited but a
# descendant may set visibility:visible again. Font size is never a hiding rule: it is inherited and reset by children, so a
# font-size:0 wrapper hides nothing, and 1pt text is still rendered.
BLOCK = set('p div br tr td th table li ul ol h1 h2 h3 h4 h5 h6 section article header footer blockquote pre dd dt dl hr '
            'caption thead tbody tfoot body html center form address'.split())
VOID = set('br img hr input meta link col area base wbr source track embed param'.split())
STRUCK = set('del s strike'.split())  # removed or struck text is read apart from its neighbours (redlines): a boundary like a block's


def norm(s):
    """Comparison form: glyphs folded (E8), the key's ~~struck~~ marks dropped, whitespace runs -> one space."""
    return _WS.sub(' ', s.translate(_FOLD).replace('~~', '')).strip()


def squash(s):
    """Search form: norm without any whitespace."""
    return _WS.sub('', s.translate(_FOLD).replace('~~', ''))


def _zero(value):
    """Is a CSS number zero (opacity: 0, 0.0, 0%)?"""
    try: return float(value.rstrip('%')) == 0.0
    except ValueError: return False


class Visible:
    """Characters a reader sees (hidden subtrees, head, scripts, styles and comments removed), each with its byte span."""

    def __init__(self, raw, xml=False):
        try:
            s, blen = raw.decode('utf-8'), (lambda t: len(t.encode('utf-8')))
        except UnicodeDecodeError:
            s, blen = raw.decode('cp1252', 'replace'), len
        chars, starts, ends, stack, hidden, pos = [], array('Q'), array('Q'), [], False, 0  # byte offsets tracked per token, not per source byte
        self.hidden_chars = 0  # non-space characters inside hidden subtrees (reported, never graded)
        for m in _TOKEN.finditer(s):
            t = m.group(); start = pos; pos += blen(t)
            if t.startswith('<'):
                if len(t) == 1: chars.append(t); starts.append(start); ends.append(pos); continue
                name = _NAME.match(t)
                if not name or t.startswith('<!') or t.startswith('<?') or m.group(1): continue
                name, was_hidden = name.group(1).lower(), hidden
                attrs = {}
                for am in _ATTR.finditer(t[len(name) + 2 if t.startswith('</') else len(name) + 1:]):  # the tag's attributes, first occurrence wins
                    attrs.setdefault(am.group(1).lower(), am.group(2) or am.group(3) or am.group(4) or '')
                decl = {dm.group(1).lower(): dm.group(2).strip().lower().removesuffix('!important').strip() for dm in _DECL.finditer(attrs.get('style', ''))}  # last declaration wins
                disp = decl.get('display'); block = (disp not in _INLINE_DISPLAY) if disp and disp != 'none' else name in BLOCK or name in STRUCK or 'line-through' in decl.get('text-decoration', '') + decl.get('text-decoration-line', '')
                if t.startswith('</'):
                    if any(fr[0] == name for fr in reversed(stack)):
                        while True:
                            fr = stack.pop()
                            if fr[0] == name: block = fr[3]; break  # the element's own display decides its closing separator too
                elif not t.endswith('/>') and name not in VOID:  # open elements: (name, blocked for good, visibility hidden, block)
                    blocked, vis = stack[-1][1:3] if stack else (False, False)
                    opacity = decl.get('opacity', '').split()[0] if decl.get('opacity') else None
                    gone = disp == 'none' or (opacity is not None and _zero(opacity)) or ('hidden' in attrs and not disp) or name == 'ix:hidden'
                    v = decl.get('visibility')
                    stack.append((name, blocked or gone, vis if not v or v in ('inherit', 'unset') else v not in ('visible', 'initial'), block))  # visibility inherits; a child may set it again
                hidden = bool(stack) and (stack[-1][1] or stack[-1][2])
                if not (hidden or was_hidden) and (xml or block): chars.append(' '); starts.append(start); ends.append(pos)
                continue
            if hidden:
                if not t.startswith('&') or len(t) == 1: self.hidden_chars += len(_WS.sub('', t))
                elif not _WS.match(html.unescape(t)): self.hidden_chars += 1
                continue
            if t.startswith('&') and len(t) > 1:
                for c in html.unescape(t): chars.append(c); starts.append(start); ends.append(pos)
            elif t.isascii() or blen is len:
                chars.extend(t); starts.extend(range(start, start + len(t))); ends.extend(range(start + 1, start + len(t) + 1))
            else:
                off = start
                for c in t: n = blen(c); chars.append(c); starts.append(off); ends.append(off + n); off += n
        self.text, self.starts, self.ends = ''.join(chars), starts, ends
        self.certain = not _SHEET.search(s)  # with stylesheet rules present, visibility is reported as uncertain, never certified
        self.idx = array('Q', (i for i, c in enumerate(chars) if not _WS.match(c)))  # text index of each search-form character
        self.flat = ''.join(chars[i] for i in self.idx).translate(_FOLD)
        self.s = array('Q', (starts[i] for i in self.idx)); self.e = array('Q', (ends[i] for i in self.idx))
        self.raw_len = len(raw)

    def at(self, byte_start, byte_end_exclusive):
        """Visible text whose characters lie wholly inside the byte range."""
        out, j = [], bisect_left(self.starts, byte_start)
        while j < len(self.starts) and self.starts[j] < byte_end_exclusive:
            if self.ends[j] <= byte_end_exclusive: out.append(self.text[j])
            j += 1
        return ''.join(out)

    def at_any(self, anchor):
        """Visible text at one anchor or, for a cell that sits in several places, at each of them joined by a space."""
        spans = anchor if isinstance(anchor, list) else [anchor]
        return ' '.join(self.at(a['byte_start'], a['byte_end_exclusive']) for a in spans)

    def uncovered(self, byte_ranges):
        """Search-form characters inside none of the byte ranges, grouped into spans with their text."""
        n, covered = len(self.flat), bytearray(len(self.flat))
        for a, b in byte_ranges:
            j = bisect_left(self.s, a)
            while j < n and self.s[j] < b:
                if self.e[j] <= b: covered[j] = 1
                j += 1
        spans, j = [], 0
        while j < n:
            if covered[j]: j += 1; continue
            k = j
            while k + 1 < n and not covered[k + 1]: k += 1
            spans.append({'byte_start': self.s[j], 'byte_end_exclusive': self.e[k], 'text': self.text[self.idx[j]:self.idx[k] + 1]})
            j = k + 1
        return spans


SHORT = 20  # search-form characters; shorter texts are ambiguous (a word can occur anywhere) and are placed between neighbours


def link(raw, units, xml=False):
    """Give every unit and cell a byte anchor from the visible stream. Long texts are placed in order first; short ones
    only between their anchored neighbours; pictures and empty units take the gap between neighbours.
    Returns {'units': units (anchored in place), 'uncovered': spans of source text no unit covers}."""
    vis, ranges = Visible(raw, xml), []
    items = [(u, c) for u in units for c in (u.get('cells') or [u])]  # reading order; cells row-major inside their table
    keys = [squash(c.get('text', '')) if u.get('kind') != 'image' else '' for u, c in items]

    def place(i, lo, hi, forward_only):
        """Anchor item i inside flat[lo:hi]; forward search first, else the nearest earlier occurrence (flagged)."""
        obj, n = items[i][1], keys[i]
        marks = [squash(m) for m in obj.get('markers') or () if squash(m)]; allm = ''.join(marks)
        taken = {pos[k][0] for k in range(len(items)) if pos[k] and keys[k] == n and k != i}  # copies of this text other units already hold
        found = []
        for k in ([allm + n, n + allm] if marks else []) + [n]:
            off = len(allm) if marks and k == allm + n else 0; j = vis.flat.find(k, lo, hi)
            while j >= 0 and j + off in taken: j = vis.flat.find(k, j + 1, hi)
            if j >= 0: found.append((j, -len(k), k))
        j, _, key = min(found) if found else (-1, 0, n)  # marks kept apart sit right before or right after the text; the earliest start wins,
        flag = None                                      # because a mark that follows may belong to the next cell
        if j < 0 and not forward_only:
            key, j, flag = n, vis.flat.rfind(n, 0, lo + len(n)), 'out_of_order'  # found only before the window: the tool moved it
            while j >= 0 and j in taken: j = vis.flat.rfind(n, 0, j)
        if j < 0: obj['anchor'] = None; obj['link_error'] = 'not_in_source'; return None
        left, end, used = j, j + len(key), set(range(len(marks))) if key != n else set()
        for k in reversed(range(len(marks))):  # marks not covered by the key: right before the text (inside this window) ...
            if k not in used and left - len(marks[k]) >= lo and vis.flat.startswith(marks[k], left - len(marks[k])): left -= len(marks[k]); used.add(k)
        for k in range(len(marks)):  # ... or right after it
            if k not in used and vis.flat.startswith(marks[k], end): end += len(marks[k]); used.add(k)
        j = left
        if flag: obj['link_flag'] = flag
        obj.pop('link_error', None)
        obj['anchor'] = {'byte_start': vis.s[j], 'byte_end_exclusive': vis.e[end - 1]}
        ranges.append((obj['anchor']['byte_start'], obj['anchor']['byte_end_exclusive']))
        return (j + (len(key) - len(n) if key == allm + n and allm else 0), end)  # the text's own start: one copy, one unit

    def piece(i, lo, hi):
        """A long text the exact search cannot place: align it to the source and anchor its matching blocks (each at least SHORT
        characters), in order, as a list anchor. The unit's characters outside the blocks are the tool's insertions, reported
        as `inserted_chars`; the source characters between the blocks stay uncovered (the tool dropped them)."""
        obj, n = items[i][1], keys[i]
        taken = {pos[k][0] for k in range(len(items)) if pos[k] and keys[k] == n and k != i}
        j = vis.flat.find(n[:SHORT], lo, hi)
        while j >= 0 and j in taken: j = vis.flat.find(n[:SHORT], j + 1, hi)
        if j < 0: return None
        seg = vis.flat[j:min(hi, j + 2 * len(n))]
        blocks = [b for b in difflib.SequenceMatcher(None, n, seg, autojunk=False).get_matching_blocks() if b.size >= SHORT]
        if not blocks or blocks[0].a > 0 and n[:SHORT] != seg[blocks[0].b:blocks[0].b + SHORT]: return None
        obj['anchor'] = [{'byte_start': vis.s[j + b.b], 'byte_end_exclusive': vis.e[j + b.b + b.size - 1]} for b in blocks]
        obj['pieces'] = [[b.a, b.a + b.size] for b in blocks]; obj['inserted_chars'] = len(n) - sum(b.size for b in blocks); obj['link_flag'] = 'pieced'
        obj.pop('link_error', None); ranges.extend((a['byte_start'], a['byte_end_exclusive']) for a in obj['anchor'])
        return (j + blocks[0].b, j + blocks[-1].b + blocks[-1].size)

    pos = [None] * len(items)
    def window(i):
        lo = next((pos[k][1] for k in range(i - 1, -1, -1) if pos[k]), 0)
        hi = next((pos[k][0] for k in range(i + 1, len(items)) if pos[k]), len(vis.flat))
        return lo, hi
    def unclaimed(i):
        """A copy of this text that no unit with the same text holds yet, anywhere in the source: a tool that lists repeated
        blocks out of order still gets one unit per copy. Flagged, because it was not where its neighbours said."""
        n = keys[i]; taken = {pos[k][0] for k in range(len(items)) if pos[k] and keys[k] == n}; m = sum(len(squash(x)) for x in items[i][1].get('markers') or ())
        j = vis.flat.find(n)
        while j >= 0:
            if j not in taken:
                hit = place(i, max(0, j - m), j + len(n) + m, forward_only=True)
                if hit: items[i][1]['link_flag'] = 'out_of_order'
                return hit
            j = vis.flat.find(n, j + 1)
        return None
    for i, n in enumerate(keys):  # pass 1: long texts that occur exactly once in the source — unambiguous, whatever order the tool used
        if len(n) < SHORT: continue
        j = vis.flat.find(n)
        if j >= 0 and vis.flat.find(n, j + 1) < 0: pos[i] = place(i, 0, len(vis.flat), forward_only=True)
    for i, n in enumerate(keys):  # pass 2: the other long texts, in the tool's order, inside the window their anchored neighbours leave
        if len(n) < SHORT or pos[i]: continue
        lo, hi = window(i)
        pos[i] = place(i, lo, hi, forward_only=True) or unclaimed(i) or piece(i, lo, hi) or place(i, lo, hi, forward_only=False)
    for i, n in enumerate(keys):  # pass 3: short texts, only between their anchored neighbours, never far ahead by elimination
        if not n or len(n) >= SHORT: continue
        lo, hi = window(i)
        pos[i] = place(i, lo, hi, forward_only=False)  # not in its window: the nearest earlier occurrence, flagged
    last = -1
    for i in range(len(items)):  # a unit placed before the one the tool listed ahead of it: the tool moved it
        if not pos[i] or items[i][1].get('link_flag'): continue
        if pos[i][0] < last: items[i][1]['link_flag'] = 'out_of_order'
        else: last = pos[i][0]
    for u in units:
        if u.get('kind') == 'table':
            got = [x for c in u.get('cells', []) if c.get('anchor') for x in (c['anchor'] if isinstance(c['anchor'], list) else [c['anchor']])]
            u['anchor'] = {'byte_start': min(a['byte_start'] for a in got), 'byte_end_exclusive': max(a['byte_end_exclusive'] for a in got)} if got else None  # cells cover, the envelope does not
        elif u.get('kind') == 'image':
            u['anchor'] = 'gap'  # pictures: the source gap between their anchored neighbours
        elif not isinstance(u.get('anchor'), (dict, list)): u['anchor'], u['link_error'] = None, u.get('link_error', 'empty')  # nothing to find: no anchor, no gap
    first = lambda a: a[0] if isinstance(a, list) else a
    last = lambda a: a[-1] if isinstance(a, list) else a
    for i, u in enumerate(units):
        if u.get('anchor') != 'gap': continue
        before = [last(x['anchor'])['byte_end_exclusive'] for x in units[:i] if isinstance(x.get('anchor'), (dict, list))]
        after = [first(x['anchor'])['byte_start'] for x in units[i + 1:] if isinstance(x.get('anchor'), (dict, list))]
        u['anchor'] = {'byte_start': before[-1] if before else 0, 'byte_end_exclusive': after[0] if after else vis.raw_len}
        u['link_flag'] = 'gap'  # a derived location: it places the picture, it never certifies coverage of the bytes between
    return {'units': units, 'uncovered': vis.uncovered(ranges)}
