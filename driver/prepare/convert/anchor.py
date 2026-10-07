"""Visible text of an original file with byte spans, and a linker that places a tool's output back in it.
Standard library only. Used by the grader (honest anchors, nothing lost) and by route adapters whose tool gives
no source positions (Docling on HTML). The linker never adds, repairs or reorders text: a unit whose text is not
in the source stays unanchored and the source text it should have covered is reported as uncovered. A cell that sits
in several source places (a merged stacked header) must come from the adapter with a list of anchors; the linker
never guesses such a split."""
from array import array
from bisect import bisect_left
from collections import Counter, defaultdict, namedtuple
from functools import cached_property
import hashlib
import html
from html.entities import html5
import xml.parsers.expat as expat
import re
from driver.prepare.compare import _FOLD, _TOKEN_WORDS, _WS, norm, squash  # the comparison form, one implementation shared with production; the scanner's _TOKEN below is its own

# The tokens of an HTML source (HTML Standard, tokenization): a comment — to `-->` or `--!>`, at once for `<!-->` and `<!--->`, to the end of the source when it never
# ends; an element taken whole up to its closing tag, or to the end of the source when it has none (group 1); a declaration or processing instruction; a tag (a `>` inside a
# quoted attribute value is no end); a character reference (a numeric one is its digits); text; a `<` that begins none of these (text); `&`; and (group 2) a `<` that begins a tag
# or a declaration which never ends — with the rest of the source when no `>` follows at all: the parser drops it, and nothing is looked for in it again
_TOKEN = re.compile(r'<!--(?:-?>|.*?--!?>|.*)|<(script|style|title|template)(?=[ \t\n\f\r/>])[^>]*>.*?(?=</\1[ \t\n\f\r/>]|\Z)|<[!?][^>]*>|<(?=[A-Za-z/])(?:[^>"\']|"[^"]*"|\'[^\']*\')*>|&#[xX][0-9a-fA-F]+;?|&#[0-9]+;?|&\w+;?|[^<&]+|<(?![A-Za-z/!?])|&|(<(?:[^>]*\Z)?)', re.S | re.I)
# A tag in the plain form, which every tokenizer cuts the same way: an ASCII name, attributes set apart by HTML white space, each value quoted or free of quotes, `=`, `<`, `>`
# and backticks. A tag written otherwise (a quote or `=` astray, other white space, `</` before no name) the HTML tokenizer cuts by rules this scanner does not follow: the
# reading is then not certified (Codex R18-C1). 2 of 22,483 real filing documents hold such a tag (codex_probes_live/r18/r18_census_real_markup)
_TAG = re.compile(r'</?[A-Za-z][-\w:.]*(?:[ \t\n\f\r]+[A-Za-z_:][-\w:.]*(?:[ \t\n\f\r]*=[ \t\n\f\r]*(?:"[^"]*"|\'[^\']*\'|[^\s"\'=<>`]+))?)*[ \t\n\f\r]*/?>', re.A)
_ATTR = re.compile(r'''([^\s"'=<>/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>]+)))?''', re.A)  # one attribute: name, quoted or bare value (ASCII white space, as in HTML)
_REF = re.compile(r'&(?:#[0-9]+|#[xX][0-9a-fA-F]+|([A-Za-z0-9]+));')  # a complete character reference; group 1 is a name
_CSS_CHAR, _CSS_STR = r'[\t\n\f\r !#-&*-?A-Z^-z|~]', r'"[^"\\\n]*"|\'[^\'\\\n]*\''
_PLAIN = re.compile(f'(?:{_CSS_CHAR}|{_CSS_STR}|\\((?:{_CSS_CHAR}|{_CSS_STR})*\\))*')  # a style string this scanner reads as CSS does: printable ASCII and CSS white space; no backslash (CSS has its own white space, letter case and escapes), no bracket, brace or `@` (CSS reads blocks whole), every quote the start of a string that ends on its line, every parenthesis closed with none inside it (an unquoted url( ends at the first `)`); comments set aside first
_DECL = re.compile(r'\s*([-\w]+)\s*:(.*)', re.S)  # one complete declaration: property name, colon, value (anything else the browser drops)
_NUM = re.compile(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?%?')  # a CSS <number> or <percentage> (no trailing dot); nothing else is a number to CSS
_CSS_ESC = re.compile(r'\\([0-9a-fA-F]{1,6})\s?|\\(.)', re.S)  # CSS escapes: \69 is i
_COMMENT = re.compile(r'("(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|url\((?:[^)\\]|\\.)*\))|/\*.*?(?:\*/|\Z)', re.S | re.I)  # a CSS comment is a token boundary, not part of a declaration; one never closed runs to the end; a string or a url() (group 1) holds none
uncomment = lambda css: _COMMENT.sub(lambda m: m.group(1) or ' ', css)
_DISPLAY = set('none block inline inline-block flex inline-flex grid inline-grid table inline-table table-row table-cell table-row-group table-header-group '
               'table-footer-group table-caption list-item flow flow-root contents'.split())  # the CSS display keywords this scanner follows (the ruby values, run-in and the column boxes are not: Chrome sweep, codex_probes_live/r18/r18_display_facts)
_TABLE_BOX = set('table-row table-cell table-row-group table-header-group table-footer-group table-caption'.split())  # the inner boxes of a table (CSS Display: the table values of <display-internal>), as a display an author gives
_ITEMS = {'flex', 'inline-flex', 'grid', 'inline-grid'}  # containers whose child elements are boxes of their own lines, whatever their display says (CSS Flexbox 4, CSS Grid 6)
_SHED = _ITEMS | {'table', 'inline-table'} | _TABLE_BOX - {'table-cell', 'table-caption'}  # the boxes that show none of their own white-space-only text: those containers, a table, and the row boxes of one (CSS 2 17.2.1; Chrome)
_SPACE = ' \t\n\r\f'  # the white space CSS collapses
_WHITE = set('normal nowrap pre pre-wrap break-spaces inherit initial unset'.split())  # the white-space keywords this scanner follows (not pre-line: an invisible line feed under it takes the space before it away; in no real filing)
_KEPT = ('pre', 'pre-wrap', 'break-spaces')  # white-space values under which no white space is dropped
_PRE = set('pre listing xmp plaintext textarea'.split())  # elements in which the browser's own sheet keeps white space
_EATS = {'pre', 'listing', 'textarea'}  # the start tags after which the parser drops a line feed that comes first (HTML tree construction: "newlines at the start of pre blocks are ignored"; Chrome)
# An open element of the scan. `gone`: removed for good (display:none, hidden by the browser's own sheet, ix:hidden — its own or an ancestor's); `unseen`:
# invisible in its place — visibility hidden (inherited; a child may show again) or a zero opacity (no child shows again); `block`: its edges break the line; `struck`: the strike in effect inside it, `strikes`: its own decoration
# line; `inside`: the innermost table, row group, row or cell it stands in; `edge`: 'own' for a box the page sets by rules of its own, 'atomic' for an inline box that
# holds lines of its own; `disp`: the display its author declares (a <textarea>: the browser's); `start`: where its content starts among the scan's characters; `declares`: it hides or sets visibility
# itself; `pre`: white space is kept in it
Open = namedtuple('Open', 'name gone unseen block struck strikes inside edge disp start declares pre loose')
_VISIBILITY = set('visible hidden collapse inherit initial unset revert revert-layer'.split())  # CSS visibility values and the CSS-wide keywords
_POSITION, _FLOAT = set('static relative absolute fixed sticky'.split()), set('none left right'.split())  # the position and float keywords this scanner evaluates
UNKNOWN = 'unknown'  # a value this scanner does not evaluate: the file's visibility is then reported uncertain
_IMPORTANT = re.compile(r'\s*!\s*important\s*$')
_INLINE_DISPLAY = {'inline', 'inline-block', 'inline-flex', 'inline-grid', 'inline-table', 'contents'}  # CSS display values that keep text in the line
_ALIGNED = {'img', 'input', 'embed', 'iframe', 'table'}  # the boxes an `align` of left or right floats: those in the line, and a table (a float is a block either way; a parent's strike does not reach into it)
_ATOMIC = {'inline-block', 'inline-flex', 'inline-grid', 'inline-table'}  # inline boxes that hold lines of their own
_SHEET_LINK = re.compile(r'<link\b.*\bstylesheet\b', re.I | re.S)  # a stylesheet link: this scanner does not fetch or apply it
_UNREAD = set('all content appearance -webkit-appearance -webkit-text-security white-space-collapse -webkit-opacity'.split())  # properties that change the page's text, or hide it, and are not evaluated here: a declaration of one is not followed. The list is what was left when every property Chrome lists was tried with every value it accepts (r18_props_facts.py)
_MODE = {'writing-mode', '-webkit-writing-mode', '-epub-writing-mode'}  # the writing mode, under the three names Chrome accepts (the last it does not list): one other than its parent's makes an element in the line a box of its own lines — the white space inside its edges is dropped, a parent's strike does not reach it (r19_edges_facts.py, r19_hidden_facts.py); a block reads the same in any mode (a real 10-K turns its table headings so)
_PROP = re.compile(r'\b(?:display|visibility|opacity)\s*:|(?<![\w-])(?:position|float|white-space|' + '|'.join(sorted(_UNREAD | _MODE)) + r')\s*:|@import\b', re.I)  # a sheet rule on a property that hides or lays out: which elements it reaches is not followed
_SEEN = re.compile(r'(?!transparent$)[a-z]+|#[0-9a-f]{3}(?:[0-9a-f]{3})?|(?:rgb|hsl)a?\((?:[^(),/]+,){2}[^(),/]+(?:,\s*1\s*)?\)')  # a colour that surely paints: a name, three or six hex digits, rgb()/hsl() in the comma form with no alpha or a literal full alpha of 1 — the forms filings write. `transparent`, any other alpha (Chrome reads -1, 0e0, 1e-999 as none) and what is not evaluated (other functions, the space form) may paint nothing
_ROOMY = re.compile(r'normal|\+?(?:\d+\.?\d*|\.\d+)[a-z%]*')  # a letter-spacing that takes no room from the letters: none, or a length that is not negative
_LINE, _ROOM = {'color', 'text-decoration-color', '-webkit-text-fill-color'}, {'letter-spacing', 'contain'}  # what colours a strike (its own colour, else its element's text colour — the fill colour where one is given), and what may leave struck letters no room to be struck in (a negative spacing sets them on one spot; `contain` may give their box no size)
_PAINT = re.compile(r'(?<![\w-])(' + '|'.join(sorted(_LINE | _ROOM)) + r')\s*:\s*([^;}!]*)', re.I)  # a sheet rule on one of them: which elements it reaches is not followed
unpaints = lambda name, value: name == 'contain' or not (_ROOMY if name == 'letter-spacing' else _SEEN).fullmatch(value.strip().lower())  # may this declaration leave a strike with nothing to see?
_DECO_RULE = re.compile(r'\btext-decoration(?:-line)?\s*:([^;}]*)', re.I)  # a stylesheet rule on a decoration, with its value: can it add a strike?
_DECO_LINES, _DECO_STYLES = {'none', 'underline', 'overline', 'line-through', 'blink'}, {'solid', 'double', 'dotted', 'dashed', 'wavy'}  # text-decoration-line and text-decoration-style keywords (CSS Text Decoration)
INVALID = 'invalid'  # a declaration the grammar proves the browser drops (it keeps the one before it): no uncertainty
_TABLE = ('table', 'thead', 'tbody', 'tfoot', 'tr', 'colgroup')  # a table and the parts that hold only its rows, cells or columns: what stands directly inside one is a part of the table, or markup the parser moves out of it
_PARTS = ('caption', 'colgroup', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th')  # the parts of a table that hold content
_HEADINGS = frozenset('h1 h2 h3 h4 h5 h6'.split())
# The HTML Standard's "special" elements (tree construction, the stack of open elements) that can stand open here — void ones never do, and html, head and body are no open elements to this scanner
_SPECIAL = frozenset('address applet article aside blockquote button caption center colgroup dd details dir div dl dt fieldset figcaption figure footer form frameset h1 h2 h3 h4 h5 h6 header hgroup iframe li listing '
                     'main marquee menu nav noembed noframes noscript object ol p plaintext pre script search section select style summary table tbody td template textarea tfoot th thead title tr ul xmp'.split())
_ENDED = frozenset('p li dd dt'.split())  # the elements a special element's closing tag ends on its way (the standard's implied end tags, those modelled here)
_ONCE = _HEADINGS | frozenset('a nobr'.split())  # elements the parser never opens inside their like: it closes the open one first (a link, a <nobr>, a heading it stands in)
# HTML tree construction: an opening tag of a kind in `by` closes an open element of a kind in `closes` unless an element in `stop` lies above it
_P_CLOSERS = set('address article aside blockquote center details dialog dir div dl fieldset figcaption figure footer header hgroup main menu nav ol p search section summary ul '
                 'h1 h2 h3 h4 h5 h6 pre listing form li dd dt plaintext table hr xmp'.split())  # the start tags that close an open <p> (the standard's "in body" rules, every one)
_IMPLIED = [(_P_CLOSERS, {'p'}, {'table'}),  # "a p element in button scope" (the other scope elements are not modelled at all)
            ({'li'}, {'li'}, _SPECIAL - {'address', 'div', 'p', 'li'}), ({'dd', 'dt'}, {'dd', 'dt'}, _SPECIAL - {'address', 'div', 'p', 'dd', 'dt'}),  # up to the first special element other than address, div and p
            (set(_PARTS) | {'col'}, {'caption'}, {'table'}), (set(_PARTS), {'colgroup'}, {'table'}),  # a caption ends at any table part, a column group at any but a <col>
            ({'td', 'th'}, {'td', 'th'}, {'tr', 'table'}), ({'tr'}, {'tr', 'td', 'th'}, {'table'}),
            ({'tbody', 'thead', 'tfoot', 'caption', 'colgroup', 'col'}, {'tbody', 'thead', 'tfoot', 'tr', 'td', 'th'}, {'table'}),
            ({'table'}, {'table'}, {'td', 'th', 'caption'})]  # a table opened in a table outside any cell and caption ends the open one first
_NAME = re.compile(r'</?\s*([\w:.-]+)')
# CSS that removes an element from view (the medium's own rules, guide 2.2 "the screen is the truth"): not shown at all,
# or shown at a size no reader can see (1pt text printed behind slide pictures)
# Hidden subtrees (E16). display:none, opacity:0 and inline-XBRL <ix:hidden> hide every descendant (what opacity hides keeps its place in the
# page, like invisible text); visibility is inherited but a descendant may set visibility:visible again. Font size is never a hiding rule: it is inherited and reset by children, so a
# font-size:0 wrapper hides nothing, and 1pt text is still rendered.
BLOCK = set('p div br tr td th table li ul ol h1 h2 h3 h4 h5 h6 section article header footer blockquote pre dd dt dl hr '
            'caption thead tbody tfoot center form address '
            'aside details dir fieldset figcaption figure hgroup listing main menu nav plaintext search summary xmp'.split())  # the elements the browser starts on a line of their own (its own sheet); the last line from a sweep of every element of the HTML Standard's index in Chrome (R17)
VOID = set('br img hr input meta link col area base wbr source track embed param basefont bgsound frame keygen'.split())  # the elements the parser inserts and closes at once (HTML tree construction)
UNMODELLED = set('svg math template audio video canvas meter progress select object option optgroup ruby rb rt rtc rp image frameset button marquee applet dialog legend wbr slot form'.split())  # content the page does not flow as its text and this scanner does not model: foreign content (its own rendering, the tags that break out of it), a template's fragment, the fallback content of embedded elements and controls, options and ruby text (their own implied endings and line rules), <image> (the parser reads <img>), a frameset, and elements whose box the browser sets by rules of its own (a button, a marquee, an applet, a dialog, a legend, a <wbr>, after which it drops white space), a <slot> (its children are laid out as its parent's) and a <form> (the parser keeps a pointer of its own for it and drops a second one) — a file holding any is uncertain (Codex R17-C4, R18-C1; Chrome sweeps). None stands in 22,483 real filing documents
UA_HIDDEN = {'datalist'}  # hidden by the browser's own sheet unless the author sets a display (HTML Standard, Rendering: hidden elements); the rest of that list is void, raw text, skipped whole or not modelled
SHOWN_BY_DISPLAY = set('noframes noscript noembed iframe'.split())  # raw text never read because the browser's own sheet hides the element: a `display` the author gives it can show the literal text (Chrome: block for some, contents for others) — uncertain then
_RAW_OPEN = re.compile(r'<(textarea|title|xmp|iframe|noembed|noframes|noscript|plaintext|script|style)(?=[ \t\n\f\r/>])', re.I)  # elements whose content is literal text, never child tags (HTML tokenization: RCDATA, RAWTEXT, script data, PLAINTEXT; <noscript> where scripts run, the reading this scanner states)
_ENTITY_TEXT = re.compile(r'&#[xX][0-9a-fA-F]+;?|&#[0-9]+;?|&\w+;?|[^&]+|&')  # the text of an RCDATA element: references and literal runs
_META = re.compile(rb'<meta[^>]*charset\s*=(?!\s*["\']?\s*utf-?8)', re.I)  # a <meta> that declares an encoding other than UTF-8
_ZEROS = re.compile(r'^(&#[xX]?)0+(?=[0-9a-fA-F])')  # the leading zeros of a numeric reference
_FORMATTING = frozenset('a b big code em font i nobr s small strike strong tt u'.split())  # the formatting elements (HTML tree construction): one the parser moves out of a table it opens again inside the cells
STRUCK = set('del s strike'.split())  # removed or struck text is read apart from its neighbours (redlines): a boundary where the element begins and ends


def text_reference(token):
    """One character reference as the HTML parser decodes it. html.unescape keeps the standard's named, C1, null and surrogate rules but deletes
    references to control characters and non-characters, which the parser keeps (`&#2;` is U+0002): only its empty result is restored. One token,
    so an escaped ampersand is never decoded twice (Codex R17-C2; the helper is his)."""
    token = _ZEROS.sub(r'\1', token)
    try: value = html.unescape(token)
    except ValueError: return '\ufffd'  # more digits than Python converts: far beyond the last code point, which the parser reads as U+FFFD
    if value or not token.startswith('&#'): return value
    digits = token[2:].rstrip(';')
    return chr(int(digits[1:], 16) if digits[:1].lower() == 'x' else int(digits))


_ATTRIBUTE_REF = re.compile(r'&(?:#[xX][0-9a-fA-F]+;?|#[0-9]+;?|[A-Za-z][A-Za-z0-9]*;?)')
_NAME_MAX = max(map(len, html5))


def attribute_span(tag, name, attr):
    """Where, in a start tag's text, the first value written for an attribute stands (inside its quotes when quoted); None when the tag writes no such
    attribute or no value for it. The first occurrence, as the parser keeps it."""
    for am in _ATTR.finditer(tag[len(name) + 1:]):
        if am.group(1).lower() == attr:
            g = next((g for g in (2, 3, 4) if am.group(g) is not None), None)
            return (am.start(g) + len(name) + 1, am.end(g) + len(name) + 1) if g else None
    return None


def attribute_value(value):
    """An attribute's value as the HTML parser reads it, decoded once (HTML Standard, character references in attributes; Codex G3-C1, the function is his): a
    numeric reference always, a named one unless it lacks its semicolon and a letter, a digit or `=` follows — `&notit;` and `&not=1` stay as written —, an `&` that begins
    none as it stands; line ends and nulls as the input stream gives them, before any reference is read (a decoded carriage return stays one)."""
    def replace(m):
        token = m.group()
        if token.startswith('&#'): return text_reference(token)
        tail = token[1:]
        for n in range(min(len(tail), _NAME_MAX), 0, -1):
            name = tail[:n]
            if name not in html5: continue
            following = m.string[m.start() + 1 + n:m.start() + 2 + n]
            if not name.endswith(';') and following and following in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=': return token
            return html5[name] + tail[n:]
        return token
    return _ATTRIBUTE_REF.sub(replace, value.replace('\r\n', '\n').replace('\r', '\n').replace('\x00', '\ufffd'))


def html_tokens(s):
    """The tokens of an HTML source as (text, kind, literal), every source character once. `kind` names what is no text: an element taken whole up to
    its closing tag ('script', 'style', 'title', 'template'), the body of a raw-text element the page never renders ('iframe', 'noembed', 'noframes',
    'noscript', an unclosed 'script', 'style' or 'title'), or 'open' for a `<` that begins a tag or a declaration which never ends (the parser drops
    the rest of the source with it). `literal` 1 is literal text — no tag, no reference (<xmp>, <plaintext>); 2 the text of a <textarea> (references
    decoded, no tags). The content of a raw-text element is never child tags; it ends at `</name` before white space, `/` or `>`, as in the
    tokenizer (Codex R17-C4, R18-C1; the tokenizer is his worktree's)."""
    pos = 0
    while pos < len(s):
        m = _TOKEN.match(s, pos); t = m.group(); pos = m.end()
        yield t, (m.group(1) or '').lower() or ('open' if m.group(2) else ''), 0
        raw = _RAW_OPEN.match(t)  # (for an element taken whole the body found below is empty)
        if raw:
            tag = raw.group(1).lower()
            end = None if tag == 'plaintext' else re.compile('</' + tag + r'(?=[ \t\n\f\r/>])', re.I).search(s, pos)
            body = s[pos:end.start() if end else len(s)]; pos += len(body)
            if tag == 'textarea': yield from ((x.group(), '', 2) for x in _ENTITY_TEXT.finditer(body))
            elif body: yield body, '' if tag in ('xmp', 'plaintext') else tag, 1


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
    for part in split_declarations(uncomment(style)):  # split first: an escaped `;` inside a value is not a separator
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
    does not evaluate — colours other than opaque hex, lengths, functions, escapes — which the browser may honour or drop."""
    toks = _IMPORTANT.sub('', value).split()
    if toks in (['initial'], ['unset']): return False  # text-decoration is not inherited: unset is initial, none
    if toks in (['revert'], ['revert-layer']): return 'default'
    if toks == ['inherit']: return 'inherit'
    known = _DECO_LINES | (_DECO_STYLES if prop == 'text-decoration' else set())
    colour = [t for t in toks if t.startswith('#') and _SEEN.fullmatch(t.lower())] if prop == 'text-decoration' else []  # hex digits are case-insensitive (Chrome strikes `line-through #ABC`)
    if len(colour) == 1 and '(' not in value: toks = [t for t in toks if t != colour[0]]  # one valid opaque hex colour; _SEEN's arbitrary names are safe only in a longhand, where an invalid name drops that declaration
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


_XML_SHARED = re.compile(rb'&[^;]*;|\r\n?')  # the bytes several characters, or a character of another length, may share: one reference, or one line ending the parser reads as a line feed


def xml_parser(**how):
    """The strict standard XML parser as every reader of the grader sets it, so that all read one document: the declarations are read as written — a
    parameter entity is expanded where it stands (left unread, the parser keeps a later declaration of the same name, or loses an attribute's
    default: another text, another element name) — and whatever stands outside the document (its external subset, an external parameter or general
    entity) is asked for and refused: nothing external is fetched, and without it the reading is not complete."""
    p = expat.ParserCreate(**how); p.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_ALWAYS); p.ExternalEntityRefHandler = lambda *args: 0
    return p


def xml_chars(raw, chars, starts, ends):
    """Character data of an XML document by the strict standard parser, each character with its byte span: a CDATA section is literal text,
    an entity or character reference decodes to its replacement (every character of it shares the reference's bytes), attributes are not
    text, an element boundary adds no character (`<note>1<b>2</b>3</note>` reads 123). False when the bytes are not a complete well-formed document, when a part of
    it stands outside (nothing external is fetched), or when a character cannot be placed at its own bytes (nothing is certified then)."""
    p = xml_parser(); events = []  # (byte index, kind, text), in document order; every construct is an event so each span ends where the next begins
    p.CharacterDataHandler = lambda t: events.append((p.CurrentByteIndex, 'text', t))
    p.StartElementHandler = lambda n, a: events.append((p.CurrentByteIndex, 'tag', None))
    p.EndElementHandler = lambda n: events.append((p.CurrentByteIndex, 'tag', None))
    p.StartCdataSectionHandler = lambda: events.append((p.CurrentByteIndex, 'mark', None))
    p.EndCdataSectionHandler = lambda: events.append((p.CurrentByteIndex, 'mark', None))
    p.DefaultHandlerExpand = lambda d: events.append((p.CurrentByteIndex, 'mark', None))
    p.SkippedEntityHandler = lambda name, is_parameter: events.append((p.CurrentByteIndex, 'skipped', None))  # a reference to an entity no declaration names, which the parser passes over where the document has parameter entities: its text is missing
    try: p.Parse(raw, True)
    except (expat.ExpatError, LookupError, ValueError): return False
    events.append((len(raw), 'mark', None))
    for (b0, kind, t), (b1, _, _) in zip(events, events[1:]):
        if kind == 'skipped': return False
        if kind == 'text':  # a tag adds nothing: XML text is the character data alone; element boundaries are structure the route reports apart
            if raw[b0:b1] == t.encode('utf-8'):
                for c in t: n = len(c.encode('utf-8')); chars.append(c); starts.append(b0); ends.append(b0 + n); b0 += n
            elif _XML_SHARED.fullmatch(raw, b0, b1):
                for c in t: chars.append(c); starts.append(b0); ends.append(b1)
            else: return False  # no bytes at all (an expanded entity gives several events at its one place), bytes of another encoding, or more than the chunk's own (a reference that expands to nothing follows it): no character is placed by a guess
    return True


def stylesheets(tokens):
    """The <style> elements and stylesheet links among these tokens (`html_tokens`), each as its CSS, or None for a sheet this scanner cannot read. A
    comment's content is no token, so a commented-out sheet applies nothing; the CSS of a <style> keeps its own <!-- -->, which CSS ignores
    (Codex R16-3); the body of a <style> that is never closed is CSS to the end of the source."""
    out = []
    for t, kind, literal in tokens:
        m = _TAG.match(t)  # an element taken whole: its content starts where its plain opening tag ends; an opening tag in another form bounds nothing
        if kind == 'style': css = t if literal else t[m.end():] if m else None; out.append(css and unescape_css(uncomment(css) + ' ' + css))  # read twice, comments set aside and kept: a rule a comment splits and a rule inside what only looks like a comment are both seen (the callers only ask whether a property is named)
        elif not literal and _SHEET_LINK.match(t): out.append(None)
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
    """Characters a reader sees (hidden subtrees, head, scripts, styles and comments removed), each with its byte span. `certain` is False where
    the source holds something this scanner knows it does not follow — a value it does not evaluate, a stylesheet rule on a hiding property,
    content it does not model, markup the parser would move: nothing is certified from the reading then."""

    def __init__(self, raw, xml=False):
        try:
            s, blen = raw.decode('utf-8'), (lambda t: len(t.encode('utf-8')))
        except UnicodeDecodeError:
            s, blen = raw.decode('cp1252', 'replace'), len
        chars, starts, ends, stack, hidden, pos = [], array('Q'), array('Q'), [], False, 0  # byte offsets tracked per token, not per source byte
        struck_chars = array('b')  # per visible character: printed struck through (an <s>/<del>/<strike> ancestor or CSS line-through)
        apart = []  # (place in `chars`, byte span of the tag) where an element that strikes, and is no block otherwise, begins or ends: struck text is read apart from its neighbours (the contract's redline rule). The page has no line break there, so the layout rules below never see one — the boundary is set in after the scan
        self.hidden_chars = 0  # non-space characters inside hidden subtrees (reported, never graded)
        self.hidden = []  # the byte spans of the text in hidden subtrees, as written (text tokens and references), for an adapter that hands a tool the source without it
        computed = '\x00' in s or (not raw.isascii() and (blen is len or raw.startswith(b'\xef\xbb\xbf') or _META.search(raw) is not None))  # the reading cannot be certified: a hiding property with a value this scanner does not evaluate (unknown keyword, var(), calc(), escapes), markup it does not follow — a null character, which the parser drops or replaces by where it stands (Codex R18-C1) — or bytes beyond ASCII that are not plainly UTF-8: the browser decodes them by the mark, the <meta> or a guess of its own (every one of 22,483 real documents is ASCII)
        struck_computed = False  # struck text cannot be certified: an unevaluated decoration value, or a formatting element the browser would reopen
        self.pictures = []  # byte spans of the <img>/<svg> opening tags in subtrees the contract's hiding rules leave shown: the grader's picture inventory, from the same visibility state as the text (Codex R15-4). Whether a picture paints (its size, clipping, transforms) is beyond this scanner: a reading of one is never measured (R17-C4)
        self.picture_names = {}  # every <img>/<svg> opening tag that writes a `src`, shown or hidden: its first byte -> (the byte span of the value as written, the name as the parser reads it) — for an adapter that hands a tool the source with a name it cannot alter
        self.picture_sources = {}  # the `src` of each of those tags as the parser reads it (references decoded once), by the tag's first byte: which picture a tool's unit is, where the tool names its resource (Codex's worktree)
        style_cache, sheet_tokens = {}, []
        self.tables, grid, spans = [], [], {}  # every table of the source in order: its rows, each the byte spans of its own cells (a nested table is a table of its own; a cell outside any row stands in the row the parser makes for it). `grid`: for each table open now, its rows and the row that takes the next cell; `spans`: the open cells by their depth on the stack — a cell ends where its element ends, an unclosed one with the source
        self.table_tags = []  # for each table of `tables`, the first byte of its start tag where the page shows the table, else None: the adapter names a table by it (edgartools_html.codes)
        lead = touch = tail = veil = None  # places in `chars`: where an inline box opened right after a word (white space next would be dropped by the browser), where a word right after such a box would touch its last word, where collapsible white space was last written, where invisible text last ended with white space (the browser drops the white space that follows it)
        line = seen = 0; after = fresh = eat = dimmed = False  # where the current line starts in `chars` (after the last break), where its last word ends, and whether a box that must have its line to itself ended on it; `fresh`: the last thing read was a tag, so white space alone after it may be a text of its own; `eat`: the last thing read was a start tag after which the parser drops a line feed; `dimmed`: the file holds a zero opacity

        def read(tag, name):
            """A tag's attributes as written (first occurrence wins), the declarations of its style string (parsed once; inheritance is still evaluated
            per element) and whether that string is plain: every `&` in it begins a complete reference the standard knows — the parser decodes a cut
            one in an attribute by a rule of its own — and, decoded, it is printable ASCII with no backslash and declares no property that changes the
            text without being evaluated here (`_UNREAD`)."""
            attrs = {}
            for am in _ATTR.finditer(tag[len(name) + 2 if tag.startswith('</') else len(name) + 1:]): attrs.setdefault(am.group(1).lower(), am.group(2) or am.group(3) or am.group(4) or '')
            raw = attrs.get('style', '')
            if raw not in style_cache:
                known = lambda m: m.group(1) is None or m.group(1) + ';' in html5
                style = _REF.sub(lambda m: text_reference(m.group()) if known(m) else m.group(), raw)
                decls = tuple(declarations(style))
                style_cache[raw] = decls, '&' not in _REF.sub(lambda m: '' if known(m) else m.group(), raw) and _PLAIN.fullmatch(uncomment(style)) is not None and not any(d[0] in _UNREAD for d in decls)
            return (attrs, *style_cache[raw])

        simple = lambda i: not (stack[i].block or stack[i].edge or stack[i].declares or stack[i].strikes)  # an inline element in the line that neither hides, strikes nor forms a box of its own: the same wherever the browser opens it again

        def leave(k):
            """The open elements from k on end here. Returns whether a visible block ends (a break) and whether a box ends that must have its line to itself."""
            nonlocal veil, touch, struck_computed
            for d in range(len(stack) - 1, k - 1, -1):  # the tables, rows and cells that end here, innermost first
                if d in spans: spans.pop(d)[1] = start
                if stack[d].name == 'table': grid.pop()
                elif grid and stack[d].name == 'tr': grid[-1][1] = None
            ended = stack[k:]; del stack[k:]
            if any(f.name in _FORMATTING and f.loose for f in ended[1:]): struck_computed = True  # a formatting element left open under a spacing or a containment: the browser opens it again for what follows (after a paragraph, a list item, a table), and struck text there may stand under it — which text is not followed
            apart.extend((len(chars), start, pos) for f in ended if f.strikes and not f.block and f.disp is None and not (f.gone or f.unseen))  # where an element set apart for its strike ends
            if any(f.block and not f.gone for f in ended): veil = None  # a line ends here, seen or not — unless the block is removed: what is not there ends nothing
            if ended[0].edge == 'atomic' and tail == len(chars) > ended[0].start: touch = len(chars)  # white space at the end of an inline box's content: the browser drops it, so a word right after the box touches its last word
            return any(f.block and not (f.gone or f.unseen) for f in ended), any(f.block and not f.gone and (f.unseen or f.edge == 'own') for f in ended)

        if xml:  # XML: character data by the strict standard parser (CDATA literal, references decoded, attributes not text); no CSS, nothing hidden
            computed = not xml_chars(raw, chars, starts, ends)
            if computed: del chars[:], starts[:], ends[:]  # refused part-way: half a reading is none
            struck_chars.extend([0] * len(chars))
        for t, kind, literal in () if xml else html_tokens(s):
            start = pos; pos += blen(t); eaten, eat = eat, False  # eaten: the token before this one was a start tag that eats a first line feed
            if kind == 'style' or t[:5].lower() == '<link': sheet_tokens.append((t, kind, literal))  # read for stylesheets after the scan: a comment is never one
            if kind:  # an element taken whole, a raw body the page never renders, or a construct that never ends: certain only while nothing can show it or move it — a plain opening tag, a plain style, no template, no `display` from the author (R17, R18-C1, Chrome)
                if not literal:
                    m = _TAG.match(t); decls, plain = read(m.group(), kind)[1:] if m else ((), False)
                    if not plain or kind == 'template' or resolve(decls, 'display', _DISPLAY.__contains__) not in (None, 'none'): computed = True
                if kind == 'script': computed = True  # a script is not run: what it would write into the page or change in it is not followed
                continue
            if not literal and t.startswith('<') and len(t) > 1:  # a lone < is text and takes the text path below (visibility, hidden count, positions, strike flag)
                if t[1] in '!?': continue  # a comment or a declaration
                fresh = True
                if not _TAG.fullmatch(t): computed = True  # a tag outside the plain form: the tokenizer may cut it elsewhere — not followed
                name = _NAME.match(t)
                if not name: continue
                name, brk, lone = name.group(1).lower(), False, False  # brk: this tag breaks the line (a visible block starts or ends at it); lone: a box ends at it that must have its line to itself
                attrs, decls, plain = read(t, name)
                if (name == 'link' and '&' in attrs.get('rel', '')) or (name in _ALIGNED and '&' in attrs.get('align', '')): computed = True  # these layout attributes are not entity-decoded here
                if any(a.startswith('on') or a == 'srcdoc' for a in attrs) or (name in ('iframe', 'embed') and 'src' in attrs): computed = True  # the script of an event attribute, or a document set into the page (it can script its parent): not run, not followed
                if '&' in attrs.get('http-equiv', '') or attrs.get('http-equiv', '').strip().lower() in ('content-security-policy', 'refresh'): computed = True  # a <meta> that hands the browser a content security policy (it can turn the style attributes and sheets off: what they hide shows) or sends it to another page (Chrome then prints that page), or whose instruction is written with a reference: not followed. The other instructions change no reading (Chrome)
                disp, v, op, cv = resolve(decls, 'display', _DISPLAY.__contains__), resolve(decls, 'visibility', _VISIBILITY.__contains__), resolve(decls, 'opacity', _number), resolve(decls, 'content-visibility', 'visible'.__eq__)
                place, flo, white = resolve(decls, 'position', _POSITION.__contains__), resolve(decls, 'float', _FLOAT.__contains__), resolve(decls, 'white-space', _WHITE.__contains__)
                if place is None and 'popover' in attrs: place = 'fixed'  # the browser's own sheet takes a popover out of the flow (HTML rendering): shown by an author's display it is a box of its own
                if flo is None and name in _ALIGNED and attrs.get('align', '').strip().lower() in ('left', 'right'): flo = 'left'  # the old way to float a picture (HTML rendering: attributes for embedded content and images; Chrome)
                if not plain or UNKNOWN in (disp, v, op, cv, place, flo, white) or name in UNMODELLED or (name in SHOWN_BY_DISPLAY and disp not in (None, 'none')) or attrs.get('hidden') or (name == 'textarea' and disp not in (None, 'none')): computed = True  # beyond this scanner, so nothing is certified: a style string it does not read as CSS does, an unevaluated value, a content-visibility other than visible, content that is not modelled, an element the browser's own sheet hides and the author displays (its literal text then shows), a `hidden` attribute with a value (until-found hides by another rule) (Codex R17-C4, R18-C1)
                disp, v, op = (None if x == UNKNOWN else x for x in (disp, v, op))
                deco, strong = None, False  # the decoration in force: the last valid text-decoration / text-decoration-line declaration wins, !important beats a later plain one
                for n, val, important in decls:
                    if n in _LINE and unpaints(n, val): struck_computed = True  # a line in this colour may not be seen, and letters inside may be coloured again: no strike is certified in this file
                    if n in ('text-decoration', 'text-decoration-line') and (important or not strong):
                        d = decoration(val, n)
                        if d == INVALID: continue  # the grammar proves the browser drops this declaration and keeps the one before it
                        if d == UNKNOWN: struck_computed = True; continue  # not evaluated: struck text in this file is uncertain, the declaration is skipped as the browser would skip an invalid one
                        deco, strong = d, important
                ua_hidden = 'hidden' in attrs or 'popover' in attrs or name in UA_HIDDEN  # not shown by the browser's own sheet; an author display shows it again
                dim = op is not None and _zero(op); dimmed = dimmed or dim  # a zero opacity: nothing inside shows, whatever a descendant declares, and every box keeps its place — invisible like visibility:hidden, not removed
                gone = disp == 'none' or (ua_hidden and not disp) or name == 'ix:hidden'
                if disp is None and name == 'textarea': disp = 'inline-block'  # the browser's own sheet: a <textarea> is an inline box that holds its text (HTML rendering, form controls); one the author gives a display is not followed (as `contents` it is not rendered at all)
                if name == 'details' and 'open' not in attrs and not t.startswith('</'): computed = True  # a closed <details> shows its summary only: not followed here
                if name in ('html', 'head', 'body'):  # the document's own elements: the parser keeps one of each wherever their tags stand, and merges a repeated tag's attributes into the first — none opens, closes or breaks anything here, and one that hides, strikes or is given a display other than block is not followed
                    if not t.startswith('</') and (dim or ua_hidden or v in ('hidden', 'collapse') or disp not in (None, 'block')): computed = True  # (a body laid out as a flex row or a table sets its children as that box does; a repeated tag's `hidden` is merged without its style)
                    if not t.startswith('</') and (name in STRUCK if deco in (None, 'default') else deco): struck_computed = True
                    if not t.startswith('</') and any(n in _ROOM and unpaints(n, val) for n, val, _ in decls): struck_computed = True  # root styles reach descendants; roots are not held on this stack
                    continue
                if t.startswith('</'):
                    i = next((k for k in range(len(stack) - 1, -1, -1) if stack[k].name == name), None)
                    if i is None:
                        if name in ('p', 'br') and not (stack and stack[-1].gone):  # the parser reads a </p> that closes no paragraph as an empty paragraph and a </br> as <br> (HTML tree construction; Chrome): a break — where nothing shows (visibility) an invisible line of its own, not followed; inside what is removed, nothing at all
                            computed |= hidden; brk, veil = not hidden, None
                        elif (name in _HEADINGS and any(f.name in _HEADINGS for f in stack)) or (name in ('tr', 'tbody', 'thead', 'tfoot') and stack and stack[-1].inside in ('td', 'th', 'tr')): computed = True  # a heading closed by another level's tag: the parser closes it; a row's or row group's closing tag with none open, inside a row or a cell: the parser closes the row or the body it implied — not followed
                    else:
                        if i < len(stack) - 1:  # the tag closes other open elements on its way: followed only where the parser simply closes them too (Codex R18-C1)
                            part = name in _PARTS or name == 'table'  # a table part's own closing tag ends the rows and cells inside it, whatever stands open in them
                            barrier = {'table'} if part else _SPECIAL - _ENDED if name in _SPECIAL else _SPECIAL  # a special element's closing tag ends the paragraphs and list items left open inside it (the standard's implied end tags); no other tag simply crosses an open special element — the parser ignores it, or moves the block out of the element
                            if any(f.name in barrier for f in stack[i + 1:]): computed = True  # across a nested table, an open block, list or cell, or a </form>, which closes nothing inside it: not followed
                            elif not part and not all(stack[j].name in _ENDED or simple(j) for j in range(i + 1, len(stack))): computed = True  # an element closed on the way that hides, strikes or forms a box of its own: the browser opens a formatting element again for what follows — which ones is not followed (a paragraph or list item ended on the way stays ended)
                            if any(f.name in STRUCK for f in stack[i + 1:]): struck_computed = True  # an unclosed <s>/<del>/<strike>: the browser reopens it in the next block (formatting elements); not followed here
                        brk, lone = leave(i)
                else:
                    eat = name in _EATS
                    if name in _ONCE and any(f.name in (_HEADINGS if name in _HEADINGS else (name,)) for f in stack): computed = True  # opened inside its like: the parser closes the open one first, or drops the tag — not followed
                    for by, closes, stop in _IMPLIED:  # HTML's implied end tags: a new <p>, <li>, <td>, <tr> ... closes the open one, as the browser builds the tree
                        if name not in by: continue
                        lowest = None
                        for i in range(len(stack) - 1, -1, -1):  # every open element of those kinds down to the boundary closes (a new <tr> closes the open <td> and the open <tr>)
                            if stack[i].name in stop: break
                            if stack[i].name in closes: lowest = i
                        if lowest is not None:
                            if not all(stack[j].name in closes or simple(j) for j in range(lowest + 1, len(stack))): computed = True  # unclosed elements inside that hide, strike or form a box of their own: the browser rebuilds formatting elements around the new block
                            if name == 'table' and closes == {'p'}: computed = True  # outside standards mode (a file with no doctype) the parser keeps the paragraph open around the table: the tree, and with it what the paragraph hides, strikes or ends, depends on the mode — not followed (1 such table in 22,483 real documents)
                            b, e = leave(lowest); brk, lone = brk or b, lone or e  # a visible block closed here ends its line, whether or not the new element starts one
                    if name in _PARTS and not any(f.name == 'table' for f in stack): computed = True  # a table part with no open table: the parser drops its tags (the text then runs on)
                    top = stack[-1] if stack else None  # the element this one stands in, once the implied endings are made
                    struck = (name in STRUCK) if deco in (None, 'default') else (top.strikes if top else False) if deco == 'inherit' else deco  # an <s>/<del>/<strike> that declares none or underline is not struck by the tag; revert restores the tag's default; inherit takes the parent's own line
                    if disp == 'contents' and struck: struck_computed = True  # no principal box: the element's own decoration may not paint
                    item = bool(top) and top.disp in _ITEMS  # a child of a flex or grid container: a box of its own line whatever its display says
                    out = (place in ('absolute', 'fixed') or flo in ('left', 'right')) and disp != 'contents'  # a box taken out of the flow: a line of its own in the page's text whatever its display says (CSS 2 section 9.7; Chrome), and a parent's decoration does not reach into it
                    block = (disp not in _INLINE_DISPLAY) if disp else name in BLOCK  # (of a removed element nothing is asked)
                    # A box the page sets by rules of its own — an inline box out of the flow (printed where its offsets put it), an inner table box an author declares (set in a table the
                    # browser makes up), a paragraph given an inline display (the browser still prints it on its own line): read as a line of its own, and certified only when it has that
                    # line to itself (R18; `(232,724<font style="position:absolute">)</font>` in a real filing; alone in its cell it is certain, as in real 8-K tables). An inline box that
                    # holds lines of its own is `atomic`: read in the line
                    edge = None if item else 'own' if (out and not block) or disp in _TABLE_BOX or (name == 'p' and disp in _INLINE_DISPLAY and disp != 'contents') else 'atomic' if disp in _ATOMIC else None
                    block = block or item or edge == 'own'
                    if not block and any(n in _MODE for n, _, _ in decls): computed = True  # a writing mode on an element in the line: whether it is its parent's is not followed
                    if (item and disp == 'contents') or (name in VOID and name not in ('hr', 'img', 'input') and disp not in (None, 'none')) or (name in _PARTS and disp not in (None, 'none')) or (name == 'table' and disp not in (None, 'none', 'table', 'inline-table')): computed = True  # not followed: an item that hands its children to the container, a void element other than a rule, a picture or a field given a box of its own (the browser keeps a <br> a break and prints nothing for the others), a part of a table given another display
                    off = gone or (bool(top) and top.gone)
                    unseen = True if dim or v in ('hidden', 'collapse') else False if v in ('visible', 'initial') else bool(top) and top.unseen  # CSS visibility: hidden/collapse hide, visible/initial show; inherit, unset, revert, revert-layer or absent keep the parent's (it is inherited)
                    if dimmed and not unseen and bool(top) and top.unseen: computed = True  # shown again under an invisible parent in a file that holds a zero opacity: under that one nothing shows again — which parent it is, is not followed
                    if not unseen and bool(top) and top.unseen and top.struck: struck_computed = True  # shown again inside invisible struck text: whether the invisible element's line is painted on it is not followed
                    shown = not (off or unseen)  # an opening element shows when nothing above it is gone and neither it nor an ancestor hides it
                    if block and not off: veil = None  # a line starts here, seen or not (a removed one starts nothing)
                    alone = block and not off and (unseen or edge == 'own')  # a box that must have its line to itself: one the page sets by its own rules, or an invisible one — the page keeps its line, the browser's text glues what stands around it (visibility, not display)
                    if alone and (seen > line or (after and shown)): computed = True  # a word before it on its line, or — for one that shows — another such box (invisible ones follow each other freely: the cells of a hidden row)
                    if shown and edge == 'atomic' and (after or touch == len(chars)): computed = True  # an inline box on the line of a box that must have it to itself, or right after an inline box that ended with white space (dropped by the browser: the two boxes touch); a picture or a field there holds no word, so what follows it is asked instead
                    if name in ('img', 'svg'):
                        span = attribute_span(t, name, 'src')
                        if span is not None: self.picture_names[start] = ((start + blen(t[:span[0]]), start + blen(t[:span[1]])), attribute_value(attrs['src']))
                        if shown: self.pictures.append((start, pos)); self.picture_sources[start] = self.picture_names[start][1] if start in self.picture_names else None
                    if shown and edge == 'atomic' and chars and not _WS.fullmatch(chars[-1]): lead = len(chars)  # white space at the start of an inline box's content: the browser drops it, so the word before the box touches its first word
                    brk = brk or (shown and block)
                    if name not in VOID:  # a void one ends where it starts; a slash on a non-void HTML tag closes nothing
                        inside = name if name in _PARTS or name == 'table' else top.inside if top else None  # the innermost table, row group, row or cell this element stands in
                        pre = white in _KEPT or (white in (None, 'inherit', 'unset') and ((white is None and name in _PRE) or (bool(top) and top.pre and name != 'table')))  # outside standards mode the browser's own sheet resets white-space at a table: what a table inherits is not taken as kept
                        stack.append(Open(name, off, unseen, block, (top.struck if top and not (out or disp in _ATOMIC) else False) or struck, struck, inside, edge, disp, len(chars), gone or dim or v is not None, pre, (bool(top) and top.loose) or any(n in _ROOM and unpaints(n, val) for n, val, _ in decls)))  # an atomic inline-level or out-of-flow box: a parent's decoration does not reach into it
                        if struck and not block and disp is None and shown: apart.append((len(chars), start, pos))
                        if name == 'table': self.tables.append([]); self.table_tags.append(start if shown else None); grid.append([self.tables[-1], None])
                        elif grid and name in ('tr', 'thead', 'tbody', 'tfoot'): grid[-1][1] = None  # a row or a group of rows starts: the row before it has ended
                        if grid and name in ('tr', 'td', 'th') and grid[-1][1] is None: grid[-1][1] = []; grid[-1][0].append(grid[-1][1])
                        if grid and name in ('td', 'th'): spans[len(stack) - 1] = [start, len(raw)]; grid[-1][1].append(spans[len(stack) - 1])
                        if inside in _TABLE and name not in _PARTS and name != 'table': f = stack[-1]; computed |= f.declares or f.pre != top.pre or (name in _FORMATTING and bool(f.block or f.edge)); struck_computed |= f.struck != top.struck  # no part of a table, standing in one outside any cell: the parser moves the element out and leaves the rows behind — what it hides, strikes or keeps of white space does not reach them, and a formatting element it opens again inside the cells: one with a box of its own is not followed
                hidden = bool(stack) and (stack[-1].gone or stack[-1].unseen)
                if brk: chars.append(' '); starts.append(start); ends.append(pos); struck_chars.append(0); line, after = len(chars), False  # only a visible block boundary separates words: a hidden block, or a hidden <br>, breaks nothing
                after = after or lone
                continue
            top = stack[-1] if stack else None
            st, keeps = 1 if top and top.struck else 0, bool(top) and top.pre  # keeps: white space is kept here, never dropped
            ref = literal != 1 and t[0] == '&' and t[-1] == ';'  # a character reference: decoded as the parser decodes it, never inside literal text
            if eaten and (text_reference(t) == '\n' if ref else t[0] in '\r\n'):  # the line feed the parser drops: one written as a reference, or the first of this text (a CR or a CR LF in the source is one line feed)
                n = len(t) if ref else 2 if t[:2] == '\r\n' else 1; start += n; t = t[n:]
                if not t: continue
            if literal != 1 and not ref and text_reference(t) != t: computed = True  # a reference without its semicolon that the browser decodes ('&#150 ', '&nbsp ', '&notes'): read literally here, so not certified (Codex R18-C1)
            text = text_reference(t) if ref else t; word = not _WS.fullmatch(text)
            if top and top.inside in _TABLE and word: computed = True  # text in a table outside any cell — directly, or inside an element the parser moves out: the browser prints it before the table
            if hidden:
                if not ref: self.hidden_chars += len(_WS.sub('', t))
                elif not _WS.match(text): self.hidden_chars += 1
                self.hidden.append((start, pos))
                if not top.gone: veil = len(chars) if text[-1] in ('\r\n' if keeps else _SPACE) or (veil == len(chars) and not word) else None  # invisible text that ends with collapsible white space, or with a kept line feed (the line it starts drops the white space that follows) — and kept white space after either leaves it so; removed text is not there at all and changes nothing
                continue
            if (after and word) or (touch == len(chars) and not _WS.match(text)) or (not keeps and text[0] in _SPACE and len(chars) in (lead, veil)) or (fresh and bool(top) and top.disp in _SHED and not text.strip(_SPACE) and bool(chars) and not _WS.fullmatch(chars[-1])): computed = True  # a word on the line of a box that must have it to itself; white space the browser drops — at the edge of an inline box between two words, after invisible text that ended with white space, or alone between a word and a tag in a flex, grid or table box, which shows none of its white space that stands alone between its children (CSS Flexbox 4, CSS 2 17.2.1; what follows is not looked at)
            fresh = False
            if st and top.loose: struck_computed = True  # struck letters that may have no room (a spacing or a containment declared on their element or above it): the line may have no length — not certified
            if ref:
                for c in text: chars.append(c); starts.append(start); ends.append(pos); struck_chars.append(st)
            elif t.isascii() or blen is len:
                chars.extend(t); starts.extend(range(start, start + len(t))); ends.extend(range(start + 1, start + len(t) + 1)); struck_chars.extend([st] * len(t))
            else:
                off = start
                for c in t: n = blen(c); chars.append(c); starts.append(off); ends.append(off + n); struck_chars.append(st); off += n
            if not keeps and chars[-1] in _SPACE: tail = len(chars)
            if word: seen = len(chars)
        keep = [m for m in apart if (m[0] and struck_chars[m[0] - 1]) or (m[0] < len(chars) and struck_chars[m[0]])]  # a boundary only next to a struck character: an element that strikes nothing it shows (it is empty, or begins or ends with a box its line does not reach into) sets nothing apart there
        def spliced(seq, fill):
            out, prev = seq[:0], 0
            for (i, _, _), x in zip(keep, fill): out += seq[prev:i]; out.append(x); prev = i
            return out + seq[prev:]
        if keep: chars, starts, ends, struck_chars = spliced(chars, ' ' * len(keep)), spliced(starts, [m[1] for m in keep]), spliced(ends, [m[2] for m in keep]), spliced(struck_chars, [0] * len(keep))
        self.text, self.starts, self.ends, self.struck_chars = ''.join(chars), starts, ends, struck_chars
        sheets = stylesheets(sheet_tokens)
        sheet = any(x is None or _PROP.search(x) for x in sheets)  # an external or imported sheet, or a rule on a hiding property (escapes decoded)
        self.certain = not computed and not sheet  # stylesheet rules or unevaluated values: visibility is reported as uncertain, never certified
        struck_computed = struck_computed or any(unpaints(m.group(1).lower(), m.group(2)) for x in sheets if x for m in _PAINT.finditer(x))  # a sheet may colour a line so that it is not seen, or leave struck letters no room
        self.struck_certain = self.certain and not struck_computed and not any(_DECO_RULE.search(x) for x in sheets)  # a struck run is certified only when the reading is, no sheet rule touches decorations (a rule can remove a strike), nothing was left unevaluated and no formatting element was reopened
        self.plain_certain = self.certain and not struck_computed and not any(sheet_can_strike(x) for x in sheets)  # "nothing struck here" needs, besides, that no sheet rule can add or force a strike (line-through, inherit, revert, a function, !important or any token this scanner does not know)
        self.idx = array('Q', (i for i, c in enumerate(chars) if not _WS.match(c)))  # text index of each search-form character
        self.flat = ''.join(chars[i] for i in self.idx).translate(_FOLD)
        self.s = array('Q', (starts[i] for i in self.idx)); self.e = array('Q', (ends[i] for i in self.idx))
        self.raw_len = len(raw)

    @cached_property
    def struck_flat(self):
        """The struck flag of each character of the search form (`flat`), as bytes; made on first use."""
        return bytes(self.struck_chars[i] for i in self.idx)

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
NOWHERE = (range(0), 0, -1)  # where a cell may stand when its adapter names, for its table, no table of the source: nowhere (table_places)


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


def table_places(vis, items, keys):
    """Where the cells of a tool's table may stand when that table is one table of the source — the same texts, each as often, in exactly one table on either side:
    {id(cell): (places in `vis.flat`, the first, the last)}, and those places by text — kept for these cells: no other item may take one (a text the tool lists before
    its table would take a cell's place and leave the cell none; Codex G2-C1). A cell may stand where a source cell of the table reads as it does; where the tool kept the table's rows
    (the same rows by their texts) and a row's texts single it out, only in that row — a text the row holds twice in the row's order — so that a repeated label stays
    with its values when the tool moves rows (Codex's worktree, test_table_sources). Texts are evidence, never the order of tables: of two tables that read alike none is tied
    by its texts. A table the adapter names (`tag`: its own start tag, `Visible.table_tags`) stands in that table only (Codex, accuracy-fable-1 A3: the tool's moved rows
    were placed in the other copy of a table or in the prose before it): tied to it as above when it reads as it and no other table names it; else each cell anywhere in
    that table and nowhere else (a cell the tool lost or changed, a table the tool split); a table its adapter names by no table of the source has no place at all
    (`NOWHERE`). The places of a named table are kept for its cells. A table no adapter names (`tag` absent) is read as before."""
    holds = lambda texts: tuple(sorted(Counter(t for t in texts if t).items()))  # the texts of a table or of a row, each with its number, in no order
    mine, alike, source, out, reserved = defaultdict(list), defaultdict(list), defaultdict(list), {}, defaultdict(set)
    by_tag, named = {start: k for k, start in enumerate(vis.table_tags) if start is not None}, {}
    for (u, c), key in zip(items, keys):
        if c is not u:
            mine[id(u)].append((key, c))
            if 'tag' in u: named[id(u)] = by_tag.get(u['tag'], NOWHERE)
    for cells in mine.values(): alike[holds(key for key, _ in cells)].append(cells)
    tables =[[[(vis.flat[a:b], a) for a, b in ((bisect_left(vis.s, x), bisect_left(vis.s, y)) for x, y in row)] for row in table] for table in vis.tables] if mine else []
    for rows in tables: source[holds(text for row in rows for text, _ in row)].append(rows)
    once = Counter(named.values())
    ties = [(cells, tables[named[u]]) for u, cells in mine.items() if named.get(u, NOWHERE) is not NOWHERE and once[named[u]] == 1
            and holds(key for key, _ in cells) == holds(text for row in tables[named[u]] for text, _ in row)]
    tied = {id(cells) for cells, _ in ties}
    for u, k in named.items():
        if id(mine[u]) in tied: continue
        if k is NOWHERE:
            for key, c in mine[u]: out[id(c)] = NOWHERE
            continue
        spans = [(at, at + len(text)) for row in tables[k] for text, at in row]; lo, hi = min(a for a, _ in spans), max(b for _, b in spans)
        for text, at in (x for row in tables[k] for x in row):
            if text: reserved[text].add(at)
        for key, c in mine[u]:
            if key: out[id(c)] = (range(lo, hi), lo, hi - len(key))  # anywhere in its own table: a text that starts there
    handled, claimed = {id(mine[u]) for u in named}, {id(tables[k]) for k in named.values() if k is not NOWHERE}  # a named table, and a table a unit names, are never tied by texts
    ties += [(cells[0], source[texts][0]) for texts, cells in alike.items() if len(cells) == 1 and len(source.get(texts, ())) == 1 and id(cells[0]) not in handled and id(source[texts][0]) not in claimed]
    for cells, rows in ties:
        theirs, ours, anywhere = defaultdict(list), defaultdict(list), defaultdict(set)
        for row in rows:
            theirs[holds(text for text, _ in row)].append(row)
            for text, at in row: anywhere[text].add(at)
        anywhere = {text: (at, min(at), max(at)) for text, at in anywhere.items() if text}
        for text, (at, _, _) in anywhere.items(): reserved[text] |= at
        for key, c in cells: ours[c.get('r')].append((key, c))
        ours = [(holds(key for key, _ in row), row) for row in ours.values()]
        kept = Counter(h for h, _ in ours if h) == Counter({h: len(v) for h, v in theirs.items() if h})  # the tool's rows are the source's rows
        for h, row in ours:
            own = defaultdict(list)  # a row that is one row of the source: each text's places in it, in the source's order — the n-th cell that reads so is the n-th there
            for text, at in theirs[h][0] if kept and len(theirs[h]) == 1 else (): own[text].append(at)
            for key, c in row:
                if key: out[id(c)] = ({own[key][0]}, own[key][0], own[key].pop(0)) if own else anywhere[key]
    return out, reserved


def link(raw, units, xml=False, vis=None):
    """Give every unit and cell a byte anchor from the visible stream. Long texts are placed in order first; short ones
    only between their anchored neighbours; a picture stands at a picture tag of the source that is its own — the tag the adapter names for it (`tag`: a code
    it alone gave the tool, edgartools_html.codes; shown, or no place at all), else by the resource it names, or the only one between its anchored
    neighbours — and has no place otherwise; an empty unit has none.
    Returns {'units': units (anchored in place), 'uncovered': spans of source text no unit covers}. `vis`: the source's reading when the caller has it."""
    vis, ranges = Visible(raw, xml) if vis is None else vis, []
    items = [(u, c) for u in units for c in (u.get('cells') or [u])]  # reading order; cells row-major inside their table
    keys = [squash(c.get('text', '')) if u.get('kind') != 'image' else '' for u, c in items]
    same_text = {}  # the items that carry each text, found once: asking every item again for each placement took time with the square of their number (Codex's worktree)
    for k, key in enumerate(keys): same_text.setdefault(key, []).append(k)
    confined = {id(c) for u, c in items if c is not u and 'tag' in u}  # the cells of a table its adapter names: every path below keeps them in that table (table_places)
    (allowed, reserved), anywhere = table_places(vis, items, keys), (None, 0, len(vis.flat))
    for u in units:
        if u.get('kind') == 'table': u.pop('tag', None)  # the table's own start tag has decided where its cells may stand (table_places); it is no part of the route
    cell, edge = array('i', [-1]) * len(vis.flat), {}  # the innermost table cell each search-form character stands in (-1: none) and each cell's first and last character
    for n, (a, b) in enumerate(sorted((a, b) for table in vis.tables for row in table for a, b in row)):
        lo, hi = bisect_left(vis.s, a), bisect_left(vis.s, b); cell[lo:hi] = array('i', [n]) * (hi - lo); edge[n] = (lo, hi)
    same = lambda j, n: cell[j] == cell[j + n - 1]  # one cell, or none (a text is never empty here)
    def whole(j, n):  # a text found across cells only as whole cells: "10.7 %" is a value cell and its sign cell (the tool merged them); "10.8" is never read from "10.1|0.82" (Codex C4)
        a, b = cell[j], cell[j + n - 1]
        return same(j, n) or (a >= 0 and b >= 0 and j == edge[a][0] and j + n == edge[b][1])

    def place(i, lo, hi, forward_only):
        """Anchor item i inside flat[lo:hi]; forward search first, else the nearest earlier occurrence (flagged)."""
        obj, n = items[i][1], keys[i]
        if allowed.get(id(obj)) is NOWHERE: obj['anchor'], obj['link_error'] = None, 'unknown_source_table'; return None  # its table is named by no table of the source
        marks = [squash(m) for m in obj.get('markers') or () if squash(m)]; allm = ''.join(marks)
        ok, first, final = allowed.get(id(obj), anywhere); lo, hi = max(lo, first - len(allm)), min(hi, final + len(n) + len(allm))  # a cell of a table that is one table of the source: only at its places there
        free = ok.__contains__ if ok else lambda j, held=reserved.get(n, ()): j not in held  # any other item: never at a place kept for such a cell
        taken = {pos[k][0] for k in same_text[n] if pos[k] and k != i}  # copies of this text other units already hold
        found = []
        for k in ([allm + n, n + allm] if marks else []) + [n]:
            off = len(allm) if marks and k == allm + n else 0; j = vis.flat.find(k, lo, hi)
            while j >= 0 and (j + off in taken or not free(j + off) or not whole(j + off, len(n))): j = vis.flat.find(k, j + 1, hi)
            if j >= 0: found.append((j, -len(k), k))
        j, _, key = min(found) if found else (-1, 0, n)  # marks kept apart sit right before or right after the text; the earliest start wins,
        flag = None                                      # because a mark that follows may belong to the next cell
        if j < 0 and not forward_only:
            key, j, flag = n, vis.flat.rfind(n, first, min(lo, final) + len(n)), 'out_of_order'  # found only before the window: the tool moved it
            while j >= 0 and (j in taken or not free(j) or not whole(j, len(n))): j = vis.flat.rfind(n, first, j)
        if j < 0: obj['anchor'] = None; obj['link_error'] = 'not_in_source'; return None
        left, end, used = j, j + len(key), set(range(len(marks))) if key != n else set()
        for k in reversed(range(len(marks))):  # marks not covered by the key: right before the text (inside this window) ...
            if k not in used and left - len(marks[k]) >= lo and vis.flat.startswith(marks[k], left - len(marks[k])): left -= len(marks[k]); used.add(k)
        for k in range(len(marks)):  # ... or right after it
            if k not in used and vis.flat.startswith(marks[k], end): end += len(marks[k]); used.add(k)
        if flag: obj['link_flag'] = flag
        obj.pop('link_error', None)
        obj['anchor'] = {'byte_start': vis.s[left], 'byte_end_exclusive': vis.e[end - 1]}  # the anchor takes the marks in; the position given back stays the text's own — given as the first mark's, a second unit that reads the same took the same copy (Codex G2-R2)
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
        if id(obj) in confined:  # a cell of a named table: only inside its own table
            ok, first, final = allowed.get(id(obj), NOWHERE)
            if ok is NOWHERE[0]: return None
            lo, hi = max(lo, first), min(hi, final + len(n))
        taken = {pos[k][0] for k in same_text[n] if pos[k] and k != i} | reserved.get(n, set())  # (and no place kept for a table's cell that reads so)
        j = vis.flat.find(n[:SHORT], lo, hi)
        while j >= 0 and (j in taken or not same(j, SHORT)): j = vis.flat.find(n[:SHORT], j + 1, hi)
        if j < 0: return None
        seg = vis.flat[j:min(hi, j + 2 * len(n))]
        gn, gs = grams(n), grams(seg)
        pairs = sorted((pa[0], gs[g][0]) for g, pa in gn.items() if len(pa) == 1 and len(gs.get(g, ())) == 1)
        blocks, ea, eb = [], 0, 0  # (text start, segment start, size); ends of the previous block on both sides
        for a, b in chain(pairs):
            if a < ea or b < eb: continue  # inside the previous block's extension
            la, lb = a, b
            while la > ea and lb > eb and n[la - 1] == seg[lb - 1] and same(j + lb - 1, 2): la -= 1; lb -= 1
            size = a + SHORT - la
            while la + size < len(n) and lb + size < len(seg) and n[la + size] == seg[lb + size] and same(j + lb + size - 1, 2): size += 1
            first, last = j + lb, j + lb + size  # a block over several cells keeps a cell only whole: a part of a cell at either end is cut off (Codex R2-C2: "10.82" was read from "10.1 | 0.82 …" by a chain)
            if not same(first, size):
                left, right = cell[first], cell[last - 1]
                cut_left = edge[left][1] - first if left >= 0 and first > edge[left][0] else 0
                cut_right = last - edge[right][0] if right >= 0 and last < edge[right][1] else 0
                la += cut_left; lb += cut_left; size -= cut_left + cut_right
            if size <= 0: continue
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
        n = keys[i]; taken = {pos[k][0] for k in same_text[n] if pos[k]}; m = sum(len(squash(x)) for x in items[i][1].get('markers') or ())
        ok, first, final = allowed.get(id(items[i][1]), anywhere); held = reserved.get(n, ()); j = vis.flat.find(n, first)
        while j >= 0:
            if j not in taken and (j in ok if ok else j not in held):
                hit = place(i, max(0, j - m), j + len(n) + m, forward_only=True)
                if hit: items[i][1]['link_flag'] = 'out_of_order'; return hit
            j = vis.flat.find(n, j + 1, final + len(n))
        return None
    for i in range(len(items)):  # first, the cells with one place they may stand at — unambiguous, whatever order the tool lists its cells in
        if len(allowed.get(id(items[i][1]), anywhere)[0] or ()) == 1: pos[i] = place(i, 0, len(vis.flat), forward_only=True)
    for i, n in enumerate(keys):  # pass 1: long texts that occur exactly once in the source — unambiguous, whatever order the tool used
        if len(n) < SHORT: continue
        j = vis.flat.find(n)
        if j >= 0 and vis.flat.find(n, j + 1) < 0: pos[i] = place(i, 0, len(vis.flat), forward_only=True)
    for i, n in enumerate(keys):  # pass 2: the other long texts, in the tool's order, inside the window their anchored neighbours leave
        if len(n) < SHORT or pos[i]: continue
        lo, hi = window(i)
        pos[i] = place(i, lo, hi, forward_only=True) or unclaimed(i) or piece(i, lo, hi) or place(i, lo, hi, forward_only=False)
    for i, n in enumerate(keys):  # pass 3: short texts, only between their anchored neighbours, never far ahead by elimination
        if not n or len(n) >= SHORT or pos[i]: continue
        lo, hi = window(i)
        pos[i] = place(i, lo, hi, forward_only=False)  # not in its window: the nearest earlier occurrence, flagged
        if not pos[i] and id(items[i][1]) in allowed: pos[i] = unclaimed(i)  # a cell whose places are known stands at one of them: the first that is free (elimination is no guess here)
    last = -1
    for i in range(len(items)):  # a unit placed before the one the tool listed ahead of it: the tool moved it
        if not pos[i] or items[i][1].get('link_flag'): continue
        if pos[i][0] < last: items[i][1]['link_flag'] = 'out_of_order'
        else: last = pos[i][0]
    for u in units:
        if u.get('kind') == 'table':
            got = [x for c in u.get('cells', []) if c.get('anchor') for x in (c['anchor'] if isinstance(c['anchor'], list) else [c['anchor']])]
            u['anchor'] = {'byte_start': min(a['byte_start'] for a in got), 'byte_end_exclusive': max(a['byte_end_exclusive'] for a in got)} if got else None  # cells cover, the envelope does not
        elif u.get('kind') == 'image': u['anchor'] = None  # a picture's place is its own tag in the source, found below — never the gap its neighbours leave
        elif not isinstance(u.get('anchor'), (dict, list)): u['anchor'], u['link_error'] = None, u.get('link_error', 'empty')  # nothing to find: no anchor, no gap
    first = lambda a: a[0] if isinstance(a, list) else a
    last = lambda a: a[-1] if isinstance(a, list) else a
    claimed = set()
    for i, u in enumerate(units):  # a picture: the one shown picture tag the tool names by its resource, or the only one between the unit's anchored neighbours; pictures that cannot be told apart are placed nowhere — as many tags as units is no identity (Codex's worktree and decision; test_image_sources)
        if u.get('kind') != 'image': continue
        if 'tag' in u: tag = u.pop('tag'); candidates = [(a, b) for a, b in vis.pictures if a == tag]  # the adapter says which tag the unit came from: that tag if shown, else nowhere — no name, no neighbour decides for it
        else:
            before = [last(x['anchor'])['byte_end_exclusive'] for x in units[:i] if x.get('kind') != 'image' and isinstance(x.get('anchor'), (dict, list))]
            after = [first(x['anchor'])['byte_start'] for x in units[i + 1:] if x.get('kind') != 'image' and isinstance(x.get('anchor'), (dict, list))]
            lo, hi = (before[-1] if before else 0), (after[0] if after else vis.raw_len)
            candidates = [(a, b) for a, b in vis.pictures if not u.get('src') or vis.picture_sources[a] == u['src']]
            if not u.get('src') or len(candidates) != 1: candidates = [(a, b) for a, b in candidates if lo <= a and b <= hi]
        if len(candidates) != 1 or candidates[0][0] in claimed: u['link_error'] = 'ambiguous_image_location'; continue
        a, b = candidates[0]; claimed.add(a)
        u['anchor'] = {'byte_start': a, 'byte_end_exclusive': b}; u['link_flag'] = 'source_picture'
        u.pop('link_error', None)
    return {'units': units, 'uncovered': vis.uncovered(ranges)}


# Route-item helpers the runtime shares with the grader (moved from grade.py with the scanner, 2026-10-07)

sha256 = lambda b: hashlib.sha256(b).hexdigest()


def check_source(raw, expected):
    """Refuse a mismatched source identity before parsing or changing a route."""
    if sha256(raw) != expected: raise ValueError("source bytes differ from the declared SHA-256")


def spans(anchor):
    """An anchor is one place or, for a cell that sits in several source places, a list of them."""
    return anchor if isinstance(anchor, list) else [anchor] if isinstance(anchor, dict) else []


def struck_at(vis, item):
    """Where the source strikes the item's text: ranges [start, end) of the text's characters (code points) the source prints struck through, [] when
    none is — or None when that cannot be said exactly: the decoration is not certified (`struck_certain`, which the scanner gives only where
    `plain_certain` holds too), a place of the item is no byte span or its places overlap, or its text is not the source's text at its places (same
    characters in the comparison form, so a reported mark or an inserted character leaves the places unsaid). A range never covers white space: a
    struck run of words is one range per word."""
    byte = [a for a in spans(item.get('anchor')) if 'byte_start' in a]
    if not vis.struck_certain or len(byte) != len(spans(item.get('anchor'))) or any(a['byte_end_exclusive'] > b['byte_start'] for a, b in zip(byte, byte[1:])): return None
    piece, flags = [], []
    for a in byte:
        lo, hi = bisect_left(vis.s, a['byte_start']), bisect_left(vis.s, a['byte_end_exclusive'])
        if hi > lo and max(vis.e[lo:hi]) > a['byte_end_exclusive']: return None  # a character whose bytes run past the place's end: the place is no whole reading
        piece.append(vis.flat[lo:hi]); flags.append(vis.struck_flat[lo:hi])
    text = item.get('text', ''); own, out = None, []
    if ''.join(piece) != squash(text): return None
    for m in re.finditer(b'\x01+', b''.join(flags)):  # each run of struck characters, split where the text puts white space between them
        own = own or [m.start() for m in re.finditer(r'~~|.', text, re.S) if squash(m.group())]  # the text's own position of each search-form character, made only where something is struck
        for i in (own[j] for j in range(m.start(), m.end())): out[-1].__setitem__(1, i + 1) if out and out[-1][1] == i else out.append([i, i + 1])
    return out


def tool_spaces(vis, item):
    """Where the item's text puts white space between two characters the source prints touching as one word or number — a space the tool added:
    [(start, end) of each such run in the text, with the search-form index of the character before and after] — or [] where the text is not the source's
    text at its places. The page may still space the two (CSS): that is for a step with the page to decide; the gate's boundary rule stays as it is."""
    byte = [a for a in spans(item.get('anchor')) if 'byte_start' in a]
    if len(byte) != len(spans(item.get('anchor'))): return []
    src = []
    for a in byte:
        lo, hi = bisect_left(vis.s, a['byte_start']), bisect_left(vis.s, a['byte_end_exclusive'])
        if hi > lo and max(vis.e[lo:hi]) > a['byte_end_exclusive']: return []  # a character whose bytes run past the place's end: the place is no whole reading
        src += range(lo, hi)
    text = item.get('text', ''); own = [m.start() for m in re.finditer(r'~~|.', text, re.S) if squash(m.group())]
    if ''.join(vis.flat[k] for k in src) != squash(text): return []
    out = []
    for p, (i, j) in enumerate(zip(own, own[1:])):
        k, l = src[p], src[p + 1]
        if not text[i + 1:j].isspace() or vis.idx[l] != vis.idx[k] + 1: continue  # the text has no white space there (nothing, or something else), or the source itself puts something between the two
        a = vis.flat[k - 1:k + 1] if k and vis.idx[k - 1] + 1 == vis.idx[k] else vis.flat[k]  # each side with the neighbour the source prints touching it:
        b = vis.flat[l:l + 2] if l + 1 < len(vis.flat) and vis.idx[l + 1] == vis.idx[l] + 1 else vis.flat[l]  # a number's own separator belongs to the number ("0.|69"), as the gate's tokens read it
        if len(_TOKEN_WORDS.findall(vis.flat[k] + ' ' + vis.flat[l])) != 2 and _TOKEN_WORDS.findall(a + b) == _TOKEN_WORDS.findall(a + ' ' + b): continue  # a space there cuts no word or number in two (reflow at punctuation and symbols is allowed, E12)
        out.append((i + 1, j, k, l))
    return out
