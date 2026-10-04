"""Visible text of an original file with byte spans, and a linker that places a tool's output back in it.
Standard library only. Used by the grader (honest anchors, nothing lost) and by route adapters whose tool gives
no source positions (Docling on HTML). The linker never adds, repairs or reorders text: a unit whose text is not
in the source stays unanchored and the source text it should have covered is reported as uncovered. A cell that sits
in several source places (a merged stacked header) must come from the adapter with a list of anchors; the linker
never guesses such a split."""
from array import array
from bisect import bisect_left
import html
import xml.parsers.expat as expat
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
_TOKEN = re.compile(r'<!--.*?-->|<(script|style|head|title|template)\b[^>]*>.*?</\1\s*>|<[!?][^>]*>|<(?=[A-Za-z/])(?:[^>"\']|"[^"]*"|\'[^\']*\')*>|&#?\w+;|[^<&]+|[<&]', re.S | re.I)
_ATTR = re.compile(r'''([^\s"'=<>/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>]+)))?''')  # one attribute: name, quoted or bare value
_DECL = re.compile(r'\s*([-\w]+)\s*:(.*)', re.S)  # one complete declaration: property name, colon, value (anything else the browser drops)
_NUM = re.compile(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?%?')  # a CSS <number> or <percentage> (no trailing dot); nothing else is a number to CSS
_CSS_ESC = re.compile(r'\\([0-9a-fA-F]{1,6})\s?|\\(.)', re.S)  # CSS escapes: \69 is i
_COMMENT = re.compile(r'/\*.*?\*/', re.S)  # a CSS comment is a token boundary, not part of a declaration
_DISPLAY = set('none block inline inline-block flex inline-flex grid inline-grid table inline-table table-row table-cell table-row-group table-header-group '
               'table-footer-group table-column table-column-group table-caption list-item flow flow-root contents ruby ruby-base ruby-text run-in'.split())  # CSS Display Module keywords
_VISIBILITY = set('visible hidden collapse inherit initial unset revert revert-layer'.split())  # CSS visibility values and the CSS-wide keywords
UNKNOWN = 'unknown'  # a value this scanner does not evaluate: the file's visibility is then reported uncertain
_IMPORTANT = re.compile(r'\s*!\s*important\s*$')
_INLINE_DISPLAY = {'inline', 'inline-block', 'inline-flex', 'inline-grid', 'inline-table', 'contents', 'ruby'}  # CSS display values that keep text in the line
_STYLE = re.compile(r'<style\b[^>]*>(.*?)</style\s*>|<link\b[^>]*\bstylesheet\b', re.I | re.S)  # stylesheets: this scanner does not apply them
_PROP = re.compile(r'\b(?:display|visibility|opacity)\s*:|@import\b', re.I)
_DECO_RULE = re.compile(r'\btext-decoration(?:-line)?\s*:([^;}]*)', re.I)  # a stylesheet rule on a decoration, with its value: can it add a strike?
_DECO_LINES, _DECO_STYLES = {'none', 'underline', 'overline', 'line-through', 'blink'}, {'solid', 'double', 'dotted', 'dashed', 'wavy'}  # text-decoration-line and text-decoration-style keywords (CSS Text Decoration)
INVALID = 'invalid'  # a declaration the grammar proves the browser drops (it keeps the one before it): no uncertainty
# HTML tree construction: an opening tag of a kind in `by` closes an open element of a kind in `closes` unless an element in `stop` lies above it
_P_CLOSERS = set('address article aside blockquote details dialog div dl fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header hgroup hr main menu nav ol p pre section table ul'.split())
_IMPLIED = [(_P_CLOSERS, {'p'}, {'table', 'td', 'th', 'caption', 'body', 'html'}), ({'li'}, {'li'}, {'ul', 'ol', 'menu', 'table', 'td', 'th', 'body'}),
            ({'dt', 'dd'}, {'dt', 'dd'}, {'dl', 'table', 'td', 'th', 'body'}), ({'td', 'th'}, {'td', 'th'}, {'tr', 'table', 'body'}),
            ({'tr'}, {'tr', 'td', 'th'}, {'table', 'body'}), ({'tbody', 'thead', 'tfoot'}, {'tbody', 'thead', 'tfoot', 'tr', 'td', 'th'}, {'table', 'body'}), ({'option'}, {'option'}, {'select', 'body'})]
_NAME = re.compile(r'</?\s*([\w:.-]+)')
# CSS that removes an element from view (the medium's own rules, guide 2.2 "the screen is the truth"): not shown at all,
# or shown at a size no reader can see (1pt text printed behind slide pictures)
# Hidden subtrees (E16). display:none, opacity:0 and inline-XBRL <ix:hidden> hide every descendant; visibility is inherited but a
# descendant may set visibility:visible again. Font size is never a hiding rule: it is inherited and reset by children, so a
# font-size:0 wrapper hides nothing, and 1pt text is still rendered.
BLOCK = set('p div br tr td th table li ul ol h1 h2 h3 h4 h5 h6 section article header footer blockquote pre dd dt dl hr '
            'caption thead tbody tfoot body html center form address'.split())
VOID = set('br img hr input meta link col area base wbr source track embed param'.split())
FOREIGN = {'svg', 'math'}  # foreign content (HTML tree construction): a self-closing tag closes its element; SVG reads presentation attributes (HTML inside <foreignObject> is not followed)
UA_HIDDEN = set('datalist noembed noframes rp'.split())  # hidden by the browser's own sheet unless the author sets a display (HTML Standard, Rendering: hidden elements); the rest of that list is void or skipped as raw text
_PRESENTATION = ('display', 'visibility', 'opacity')  # the hiding properties as SVG presentation attributes: declarations the style attribute beats
_UNIT = '(?:px|pt|pc|in|cm|mm|q|em|rem|ex|ch|vw|vh|vmin|vmax|%)'  # CSS length units this scanner reads, and the percentage
_ZERO = re.compile(r'[+-]?(?:0+\.?0*|\.0+)' + _UNIT + '?')  # a zero length, with or without a unit
_SIZE = re.compile(r'\+?(?:\d+(?:\.\d+)?|\.\d+)' + _UNIT + '|' + _ZERO.pattern + '|auto|initial|unset|revert|revert-layer|min-content|max-content|fit-content')  # a CSS width/height this scanner reads: a length, a percentage, zero, a sizing keyword; anything else (calc(), var(), inherit, a bare or negative number the browser drops) is not evaluated
_LIMITS = {'min-width', 'max-width', 'min-height', 'max-height'}  # declarations that override a width or height: not evaluated
_SIZE_RULE = re.compile(r'\b(?:width|height)\s*:', re.I)  # a stylesheet rule that may size an element (min-/max- included)
STRUCK = set('del s strike'.split())  # removed or struck text is read apart from its neighbours (redlines): a boundary like a block's


def norm(s):
    """Comparison form: glyphs folded (E8), the key's ~~struck~~ marks dropped, whitespace runs -> one space."""
    return _WS.sub(' ', s.translate(_FOLD).replace('~~', '')).strip()


def squash(s):
    """Search form: norm without any whitespace."""
    return _WS.sub('', s.translate(_FOLD).replace('~~', ''))


def _zero(value):
    """Is this opacity zero? The value is a CSS number already (`_number`); opacity is clamped to [0, 1], so a negative one is zero."""
    return float(value.rstrip('%')) <= 0.0


def unescape_css(text):
    """CSS escapes decoded (`d\\69 splay` is `display`), so a hiding rule cannot hide behind one."""
    return _CSS_ESC.sub(lambda m: chr(int(m.group(1), 16)) if m.group(1) and int(m.group(1), 16) < 0x110000 else (m.group(2) or ''), text)


def split_declarations(style):
    """Declarations split at `;` outside quotes and parentheses; an escaped character (`\\;`) is part of its token, never a separator."""
    out, buf, quote, depth, i = [], [], None, 0, 0
    while i < len(style):
        ch = style[i]
        if ch == '\\' and i + 1 < len(style): buf.append(ch); buf.append(style[i + 1]); i += 2; continue
        if quote:
            buf.append(ch)
            if ch == quote: quote = None
        else:
            if ch in '"\'': quote = ch
            elif ch == '(': depth += 1
            elif ch == ')': depth = max(0, depth - 1)
            if ch == ';' and depth == 0: out.append(''.join(buf)); buf = []; i += 1; continue
            buf.append(ch)
        i += 1
    out.append(''.join(buf))
    return out


def declarations(style):
    """The declarations of a style attribute, in order: (name, value, important), names and values lower-cased, escapes decoded,
    comments read as token boundaries (a comment inside a name or a value breaks it, as in the browser)."""
    out = []
    for part in split_declarations(_COMMENT.sub(' ', style)):  # split first: an escaped `;` inside a value is not a separator
        m = _DECL.fullmatch(unescape_css(part))
        if not m: continue  # not one complete `name: value` declaration — the browser drops it, so does this
        name, value = m.group(1).lower(), m.group(2).strip().lower()
        important = _IMPORTANT.search(value) is not None
        out.append((name, _IMPORTANT.sub('', value) if important else value, important))
    return out


def _number(value):
    return _NUM.fullmatch(value) is not None


def last(decls, prop):
    """The value of the last declaration of `prop` (an `!important` one beats a later plain one), or None."""
    value, strong = None, False
    for name, v, important in decls:
        if name == prop and (important or not strong): value, strong = v, important
    return value


def decoration(value, prop='text-decoration'):
    """What one text-decoration / text-decoration-line declaration says about striking: True (line-through), False (no line), 'default'
    (revert: the tag's own default), 'inherit' (the parent's own line), INVALID when the grammar proves the browser drops the declaration
    (a style keyword in the line longhand, two styles, a repeated or a `none`-plus-other line keyword), or UNKNOWN for anything this scanner
    does not evaluate — colours, lengths, functions, escapes — which the browser may honour or drop."""
    toks = _IMPORTANT.sub('', value).split()
    if toks in (['initial'], ['unset']): return False  # text-decoration is not inherited: unset is initial, none
    if toks in (['revert'], ['revert-layer']): return 'default'
    if toks == ['inherit']: return 'inherit'
    known = _DECO_LINES | (_DECO_STYLES if prop == 'text-decoration' else set())
    if not toks or '(' in value or '\\' in value or any(t not in known for t in toks):
        return INVALID if toks and '(' not in value and '\\' not in value and all(t in _DECO_LINES | _DECO_STYLES for t in toks) else UNKNOWN  # a style keyword can never be a line
    lines = [t for t in toks if t in _DECO_LINES]
    if len(set(toks)) < len(toks) or len(toks) - len(lines) > 1 or ('none' in lines and len(lines) > 1): return INVALID  # each keyword once, one style at most, none alone
    return 'line-through' in lines


def sheet_can_strike(sheet):
    """Can a stylesheet rule on a decoration add or force a strike? Only a value made of line keywords other than line-through, style
    keywords, initial or unset, without !important, provably cannot; inherit, revert, functions, colours and unknown tokens may."""
    harmless = (_DECO_LINES - {'line-through'}) | _DECO_STYLES | {'initial', 'unset'}
    return any('!' in m.group(1) or '(' in m.group(1) or not m.group(1).split() or any(t not in harmless for t in m.group(1).lower().split()) for m in _DECO_RULE.finditer(sheet))


def xml_chars(raw, chars, starts, ends):
    """Character data of an XML document by the strict standard parser, each character with its byte span: a CDATA section is literal text,
    an entity or character reference decodes to its replacement (every character of it shares the reference's bytes), attributes are not
    text, an element boundary adds no character (`<note>1<b>2</b>3</note>` reads 123). False when the bytes are not a complete well-formed document (nothing is certified then)."""
    p = expat.ParserCreate(); events = []  # (byte index, kind, text), in document order; every construct is an event so each span ends where the next begins
    p.CharacterDataHandler = lambda t: events.append((p.CurrentByteIndex, 'text', t))
    p.StartElementHandler = lambda n, a: events.append((p.CurrentByteIndex, 'tag', None))
    p.EndElementHandler = lambda n: events.append((p.CurrentByteIndex, 'tag', None))
    p.StartCdataSectionHandler = lambda: events.append((p.CurrentByteIndex, 'mark', None))
    p.EndCdataSectionHandler = lambda: events.append((p.CurrentByteIndex, 'mark', None))
    p.DefaultHandlerExpand = lambda d: events.append((p.CurrentByteIndex, 'mark', None))
    try: p.Parse(raw, True)
    except expat.ExpatError: return False
    events.append((len(raw), 'mark', None))
    for (b0, kind, t), (b1, _, _) in zip(events, events[1:]):
        if kind == 'text':  # a tag adds nothing: XML text is the character data alone; element boundaries are structure the route reports apart
            if b1 - b0 == len(t.encode('utf-8')):
                for c in t: n = len(c.encode('utf-8')); chars.append(c); starts.append(b0); ends.append(b0 + n); b0 += n
            else:
                for c in t: chars.append(c); starts.append(b0); ends.append(b1)
    return True


def stylesheets(tokens):
    """The <style> elements and stylesheet links among these tokens, each as its CSS, or None for a sheet this scanner cannot read. A comment's
    content is no token, so a commented-out sheet applies nothing, inside <head> too; the CSS of a <style> keeps its own <!-- -->, which CSS
    ignores (Codex R16-3)."""
    out = []
    for m in tokens:
        t, kind = m.group(), (m.group(1) or '').lower()
        if kind == 'head': out += stylesheets(_TOKEN.finditer(t[t.index('>') + 1:t.rindex('<')]))
        elif kind == 'style' or (not kind and t[:5].lower() == '<link'): out += [None if x.group(1) is None else _COMMENT.sub(' ', unescape_css(x.group(1))) for x in _STYLE.finditer(t)]
    return out


def resolve(decls, prop, valid):
    """The value in force for one property: the last declaration wins and an `!important` one beats a later plain one (the cascade
    inside one attribute). A value outside the forms this scanner evaluates — an unknown keyword, var(), calc(), an escape — gives
    UNKNOWN, because the browser may ignore it or honour it; the caller then reports the file uncertain instead of guessing."""
    value, strong = None, False
    for name, v, important in decls:
        if name != prop or (strong and not important): continue
        if '(' in v or '\\' in v or not valid(v): return UNKNOWN
        value, strong = v, important
    return value


class Visible:
    """Characters a reader sees (hidden subtrees, head, scripts, styles and comments removed), each with its byte span."""

    def __init__(self, raw, xml=False):
        try:
            s, blen = raw.decode('utf-8'), (lambda t: len(t.encode('utf-8')))
        except UnicodeDecodeError:
            s, blen = raw.decode('cp1252', 'replace'), len
        chars, starts, ends, stack, hidden, pos = [], array('Q'), array('Q'), [], False, 0  # byte offsets tracked per token, not per source byte
        struck_chars = array('b')  # per visible character: printed struck through (an <s>/<del>/<strike> ancestor or CSS line-through)
        self.hidden_chars = 0  # non-space characters inside hidden subtrees (reported, never graded)
        computed = False  # a hiding property was given a value this scanner does not evaluate (unknown keyword, var(), calc(), escapes)
        struck_computed = False  # struck text cannot be certified: an unevaluated decoration value, or a formatting element the browser would reopen
        self.pictures = []  # (start, end, shown) of the <img>/<svg> opening tags in subtrees the reader sees: the grader's picture inventory, from the same visibility state as the text (Codex R15-4); shown True, False with a zero width or height, None when its size is not known (R16-3)
        style_cache, sheet_tokens = {}, []
        if xml:  # XML: character data by the strict standard parser (CDATA literal, references decoded, attributes not text); no CSS, nothing hidden
            computed = not xml_chars(raw, chars, starts, ends); struck_chars.extend([0] * len(chars))
        for m in () if xml else _TOKEN.finditer(s):
            t = m.group(); start = pos; pos += blen(t)
            if t.startswith('<') and len(t) > 1:  # a lone < is text and takes the text path below (visibility, hidden count, positions, strike flag)
                name = _NAME.match(t)
                if name and name.group(1).lower() in ('style', 'head', 'link'): sheet_tokens.append(m)  # read for stylesheets after the scan: a comment is never one
                if not name or t.startswith('<!') or t.startswith('<?') or (m.re.groups and m.group(1)): continue
                name, was_hidden = name.group(1).lower(), hidden
                attrs = {}
                for am in _ATTR.finditer(t[len(name) + 2 if t.startswith('</') else len(name) + 1:]):  # the tag's attributes, first occurrence wins, entities decoded
                    attrs.setdefault(am.group(1).lower(), html.unescape(am.group(2) or am.group(3) or am.group(4) or ''))
                style = attrs.get('style', '')
                if style not in style_cache: style_cache[style] = tuple(declarations(style))  # the literal declarations of one style string, parsed once; inheritance is still evaluated per element
                decls = style_cache[style]
                foreign = (t.endswith('/>') or not attrs.keys().isdisjoint(_PRESENTATION)) and (name in FOREIGN or any(fr[0] in FOREIGN for fr in stack))  # SVG/MathML content: its own tag rules
                if foreign: decls = tuple((p, attrs[p].strip().lower(), False) for p in _PRESENTATION if p in attrs) + decls  # presentation attributes come first, so the style attribute beats them (R16-3)
                disp, v, op = resolve(decls, 'display', _DISPLAY.__contains__), resolve(decls, 'visibility', _VISIBILITY.__contains__), resolve(decls, 'opacity', _number)
                if UNKNOWN in (disp, v, op): computed = True; disp, v, op = (None if x == UNKNOWN else x for x in (disp, v, op))
                deco, strong = None, False  # the decoration in force: the last valid text-decoration / text-decoration-line declaration wins, !important beats a later plain one
                for n, val, important in decls:
                    if n in ('text-decoration', 'text-decoration-line') and (important or not strong):
                        d = decoration(val, n)
                        if d == INVALID: continue  # the grammar proves the browser drops this declaration and keeps the one before it
                        if d == UNKNOWN: struck_computed = True; continue  # not evaluated: struck text in this file is uncertain, the declaration is skipped as the browser would skip an invalid one
                        if d == 'inherit': d = stack[-1][5] if stack else False  # the parent's own computed line, whatever propagation would have done
                        deco, strong = d, important
                struck = (name in STRUCK) if deco in (None, 'default') else deco  # an <s>/<del>/<strike> that declares none or underline is not struck by the tag; revert restores the tag's default
                atomic = disp in ('inline-block', 'inline-table', 'inline-flex', 'inline-grid') or last(decls, 'float') in ('left', 'right') or last(decls, 'position') in ('absolute', 'fixed')  # an atomic inline-level or out-of-flow box: a parent's decoration does not reach into it
                block = (disp not in _INLINE_DISPLAY) if disp and disp != 'none' else name in BLOCK or struck
                ua_hidden = 'hidden' in attrs or name in UA_HIDDEN or (name == 'dialog' and 'open' not in attrs)  # not shown by the browser's own sheet; an author display shows it again
                gone = disp == 'none' or (op is not None and _zero(op)) or (ua_hidden and not disp) or name in ('ix:hidden', 'noscript')  # <noscript>: never shown where scripts run, as in the browser
                if name == 'details' and 'open' not in attrs and not t.startswith('</'): computed = True  # a closed <details> shows its summary only: not followed here
                shown = False  # does this tag's own element show (it is the element whose boundary may separate words)
                if t.startswith('</'):
                    if any(fr[0] == name for fr in reversed(stack)):
                        while True:
                            fr = stack.pop()
                            if fr[0] == name: block, shown = fr[3], not (fr[1] or fr[2]); break  # the element's own display decides its closing separator too
                            if fr[0] in STRUCK: struck_computed = True  # an unclosed <s>/<del>/<strike>: the browser reopens it in the next block (formatting elements); not followed here
                else:
                    if True:  # HTML's implied end tags: a new <p>, <li>, <td>, <tr> ... closes the open one, as the browser builds the tree
                        for by, closes, stop in _IMPLIED:
                            if name not in by: continue
                            lowest = None
                            for i in range(len(stack) - 1, -1, -1):  # every open element of those kinds down to the boundary closes (a new <tr> closes the open <td> and the open <tr>)
                                if stack[i][0] in stop: break
                                if stack[i][0] in closes: lowest = i
                            if lowest is not None:
                                if any(fr[1] or fr[2] for fr in stack[lowest + 1:] if fr[0] not in closes): computed = True  # unclosed hiding inline elements inside: the browser rebuilds them around the new block
                                if any(fr[0] in STRUCK for fr in stack[lowest:]): struck_computed = True  # an unclosed <s>/<del>/<strike> the browser would reopen in the new block
                                del stack[lowest:]
                    void = name in VOID or (foreign and t.endswith('/>'))  # a self-closing tag in SVG/MathML content closes its element (R16-3)
                    if not void:  # a slash on a non-void HTML tag closes nothing; open elements: (name, blocked for good, visibility hidden, block, struck in effect, own line)
                        blocked, vis = stack[-1][1:3] if stack else (False, False)
                        # CSS visibility: hidden/collapse hide, visible/initial show; inherit, unset, revert, revert-layer or absent keep the parent's (it is inherited)
                        stack.append((name, blocked or gone, True if v in ('hidden', 'collapse') else False if v in ('visible', 'initial') else vis, block, (stack[-1][4] if stack and not atomic else False) or struck, struck))
                hidden = bool(stack) and (stack[-1][1] or stack[-1][2])
                if not t.startswith('</'):  # an opening element shows when nothing above it is gone and neither it nor an ancestor hides it; a void element was not pushed, so its own visibility is read here
                    own = True if v in ('hidden', 'collapse') else False if v in ('visible', 'initial') else bool(stack) and stack[-1][2]
                    shown = (not gone and not (bool(stack) and stack[-1][1]) and not own) if void else not hidden
                    if shown and name in ('img', 'svg'):  # a picture with a zero width or height shows nothing (False); a size this scanner does not evaluate, or one a min-/max- declaration overrides, leaves it unknown (None)
                        hints = tuple((d, x + 'px' if x.replace('.', '', 1).isdigit() else x, False) for d in ('width', 'height') for x in [attrs.get(d, '').strip().lower()] if x)  # the size attributes: a plain number is pixels; declarations the style attribute beats
                        size = [resolve(hints + decls, d, _SIZE.fullmatch) for d in ('width', 'height')]
                        self.pictures.append((start, pos, None if UNKNOWN in size or any(n in _LIMITS for n, *_ in decls) else not any(x and _ZERO.fullmatch(x) for x in size)))
                if shown and block: chars.append(' '); starts.append(start); ends.append(pos); struck_chars.append(0)  # only a visible block boundary separates words: a hidden block, or a hidden <br>, breaks nothing
                continue
            st = 1 if stack and stack[-1][4] else 0
            if stack and stack[-1][0] in ('table', 'thead', 'tbody', 'tfoot', 'tr') and not _WS.fullmatch(html.unescape(t) if t.startswith('&') else t): computed = True  # the browser moves such text before the table
            if hidden:
                if not t.startswith('&') or len(t) == 1: self.hidden_chars += len(_WS.sub('', t))
                elif not _WS.match(html.unescape(t)): self.hidden_chars += 1
                continue
            if t.startswith('&') and len(t) > 1:
                for c in html.unescape(t): chars.append(c); starts.append(start); ends.append(pos); struck_chars.append(st)
            elif t.isascii() or blen is len:
                chars.extend(t); starts.extend(range(start, start + len(t))); ends.extend(range(start + 1, start + len(t) + 1)); struck_chars.extend([st] * len(t))
            else:
                off = start
                for c in t: n = blen(c); chars.append(c); starts.append(off); ends.append(off + n); struck_chars.append(st); off += n
        self.text, self.starts, self.ends, self.struck_chars = ''.join(chars), starts, ends, struck_chars
        sheets = stylesheets(sheet_tokens)
        if any(x is None or _SIZE_RULE.search(x) for x in sheets): self.pictures = [(a, b, None) for a, b, _ in self.pictures]  # a stylesheet may size a picture (its rule beats the size attributes): no picture's size is known then
        sheet = any(x is None or _PROP.search(x) for x in sheets)  # an external or imported sheet, or a rule on a hiding property (escapes decoded)
        self.certain = not computed and not sheet  # stylesheet rules or unevaluated values: visibility is reported as uncertain, never certified
        external = any(x is None or '@import' in x.lower() for x in sheets)
        self.struck_certain = not struck_computed and not external and not any(_DECO_RULE.search(x) for x in sheets if x)  # a struck run is certified only when no sheet rule touches decorations (a rule can remove a strike), nothing was left unevaluated and no formatting element was reopened
        self.plain_certain = not struck_computed and not external and not any(sheet_can_strike(x) for x in sheets if x)  # "nothing struck here" needs that no sheet rule can add or force a strike (line-through, inherit, revert, a function, !important or any token this scanner does not know)
        self.idx = array('Q', (i for i, c in enumerate(chars) if not _WS.match(c)))  # text index of each search-form character
        self.flat = ''.join(chars[i] for i in self.idx).translate(_FOLD)
        self.s = array('Q', (starts[i] for i in self.idx)); self.e = array('Q', (ends[i] for i in self.idx))
        self.raw_len = len(raw)

    def struck_runs(self):
        """Byte ranges the source prints struck through, each a run of consecutive visible characters."""
        runs, i = [], 0
        while i < len(self.text):
            if self.struck_chars[i] and not self.text[i].isspace():
                j = i
                while j + 1 < len(self.text) and self.struck_chars[j + 1]: j += 1
                while j > i and self.text[j].isspace(): j -= 1
                runs.append((self.starts[i], self.ends[j])); i = j + 1
            else: i += 1
        return runs

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


def grams(s):
    """Every SHORT-gram of a string with its positions, in order."""
    d = {}
    for p in range(len(s) - SHORT + 1): d.setdefault(s[p:p + SHORT], []).append(p)
    return d


def chain(pairs):
    """The longest subsequence of (a, b) pairs, sorted by a, whose b values also increase: the anchors consistent with one reading order."""
    tails, idx, prev = [], [], [None] * len(pairs)
    for i, (a, b) in enumerate(pairs):
        k = bisect_left(tails, b)
        if k == len(tails): tails.append(b); idx.append(i)
        else: tails[k] = b; idx[k] = i
        prev[i] = idx[k - 1] if k else None
    out, i = [], (idx[-1] if idx else None)
    while i is not None: out.append(pairs[i]); i = prev[i]
    return out[::-1]


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
        """A long text the exact search cannot place: its first SHORT characters must be found exactly; from there the text is aligned
        to the source by anchor chaining — the SHORT-grams that occur exactly once in the text and exactly once in the source segment
        are anchors, the longest chain of anchors in the same order on both sides is kept (longest increasing subsequence), and each
        anchor is extended to its maximal run of equal characters. Linear-logarithmic, never a full character diff (difflib took three
        minutes on one filing and is quadratic on repetitive text); within 1 % of difflib's matched characters on the worst file.
        The blocks become a list anchor; the text's characters outside them are the tool's insertions (`inserted_chars`); the source's
        characters between them stay uncovered."""
        obj, n = items[i][1], keys[i]
        taken = {pos[k][0] for k in range(len(items)) if pos[k] and keys[k] == n and k != i}
        j = vis.flat.find(n[:SHORT], lo, hi)
        while j >= 0 and j in taken: j = vis.flat.find(n[:SHORT], j + 1, hi)
        if j < 0: return None
        seg = vis.flat[j:min(hi, j + 2 * len(n))]
        gn, gs = grams(n), grams(seg)
        pairs = sorted((pa[0], gs[g][0]) for g, pa in gn.items() if len(pa) == 1 and len(gs.get(g, ())) == 1)
        blocks, ea, eb = [], 0, 0  # (text start, segment start, size); ends of the previous block on both sides
        for a, b in chain(pairs):
            if a < ea or b < eb: continue  # inside the previous block's extension
            la, lb = a, b
            while la > ea and lb > eb and n[la - 1] == seg[lb - 1]: la -= 1; lb -= 1
            size = a + SHORT - la
            while la + size < len(n) and lb + size < len(seg) and n[la + size] == seg[lb + size]: size += 1
            blocks.append((la, lb, size)); ea, eb = la + size, lb + size
        if not blocks: return None
        obj['anchor'] = [{'byte_start': vis.s[j + b], 'byte_end_exclusive': vis.e[j + b + size - 1]} for a, b, size in blocks]
        obj['pieces'] = [[a, a + size] for a, b, size in blocks]; obj['inserted_chars'] = len(n) - sum(size for _, _, size in blocks); obj['link_flag'] = 'pieced'
        obj.pop('link_error', None); ranges.extend((x['byte_start'], x['byte_end_exclusive']) for x in obj['anchor'])
        return (j + blocks[0][1], j + blocks[-1][1] + blocks[-1][2])

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
