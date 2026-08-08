"""Route A inline-XBRL display-document evidence (FinalPlan §5A; Phase 1 corrective).

Smallest reuse of THE pinned extractor (`scripts/driver_seed/relocate_probe/benchmark/
multiaxis_pool/final/lock_row_extract.py`, sha 38690c7b…): the row/grid/header/hidden
machinery is relocated near-verbatim; new logic = the prepare-once document index, the
element-id join with enumerated fail-closed reasons, typed-dimension detection, the
COMPLETE aligned header stack, and exact-Decimal reconciliation. No prose parser, no
fuzzy logic, no registry, no vocabulary, no distant-text identity authority.

inline_element_id = graph property `Fact.fact_id` (SHORT id, matches HTML `id=`).
Pure functions; no I/O; zero channel imports.
"""
import collections
import hashlib
import re
import unicodedata
import warnings

import tinycss2
from decimal import Decimal


from driver.xml_names import graph_qname_parts, xml_name_ok
#: PRIVATE ALIASES: a plain import would re-publish the owner as
#: `inline_html.graph_cik`, a second public path to one rule.
from driver.core.driver_ids import (SEC_CIK_10_PATTERN as _SEC_CIK_10_PATTERN,
                                    graph_cik as _graph_cik)
from driver.relocation.exact_numbers import (ROUTE_A_BOOLS,
                                             XBRL_INSTANCE_NAMESPACE,
                                             XML_WS, ExactError,
                                             exact_scaleb, graph_unit_spelling,
                                             filing_boundary_graph_end,
                                             filing_boundary_graph_start,
                                             filing_duration_ordered,
                                             parse_filing_boundary)

from bs4 import (BeautifulSoup, CData, Comment, Declaration, Doctype,
                 NavigableString, ProcessingInstruction,
                 XMLParsedAsHTMLWarning)
from lxml import etree

# xsd:integer, EXACTLY: optional sign then ASCII digits, after XML whitespace
# collapsing. `int()` is NOT this check — it also accepts Python underscore
# separators (`1_0`), full-width digits (`１２`), Arabic-Indic (`٦`),
# Devanagari (`६`) and non-breaking spaces, none of which are legal here. And
# `\d` is NOT [0-9]: it matches every Unicode decimal digit, so it would let
# `１２` straight back in.
# `_XML_WS` lived here too. ONE owner now: `exact_numbers.XML_WS`, imported
# above — two spellings of one rule are two rules the day one of them is edited.
#: `_XML_INT` STOOD HERE, a hand-written `[+-]?[0-9]+`. Its one reader now uses
#: `_integer_pattern()` — the grammar the pinned `arelle-release` already
#: carries from the standard — so a second, private copy of the same rule has no
#: owner and no reason to exist.


def xml_integer(raw):
    """The ONE XML-integer parser: int, or None when the text is not one.

    Accepts what the spec allows — `6`, `+6`, `-3`, `012`, and the same values
    surrounded by XML whitespace. Rejects everything else, including Python
    values: a bool or an int is not attribute TEXT.
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip(XML_WS)
    # THE OFFICIAL GRAMMAR JUDGES IT, and the conversion never re-judges it.
    # `int(s)` refuses a digit string past CPython's 4,300-character gate, so a
    # lawful `xs:integer` — which XSD does not bound at all — came back None and
    # its reader announced `malformed_scale`: our runtime's limit, reported as a
    # defect in the filing, under the SAME reason a genuinely broken `6.9` gets.
    # `Decimal` parses the digits without that gate and `int(Decimal(...))` is a
    # numeric conversion, not a string one, so no global limit is raised and no
    # length of our own is invented.
    if not _integer_pattern().fullmatch(s):
        return None
    return int(Decimal(s))

#: THE SUPPRESSION MOVED INTO `_soup`, where the parse it belongs to happens.
#: A module-level `filterwarnings` is PROCESS-WIDE: importing this parser
#: silently changed how every other library in the process reported
#: `XMLParsedAsHTMLWarning`, measured as `warnings.filters` 5 -> 6 in a clean
#: interpreter. The warning is only ever ours to ignore for the one call that
#: causes it.


def sha256_text(html_text):
    return hashlib.sha256(html_text.encode('utf-8', 'surrogatepass')).hexdigest()


# ---- relocated from the pinned extractor (sha 38690c7b…) ------------------------

#: U+200B ZERO WIDTH SPACE, constructed by code point so no editor can hide
#: it. The renderer walk treats it as a TOKEN SEPARATOR (W4); an earlier
#: reader here DELETED it, silently fusing two tokens into one word.
_ZWSP = chr(0x200B)


def _text(node, hidden=frozenset()):
    """THE one renderer-text owner (#827 E / W4). This IS the visible walk:
    Unicode whitespace runs and U+200B become token separators, tokens join
    with U+0020, CSS-hidden subtrees are excluded by the walk itself, and
    ix:hidden containers arrive through `hidden`. The `get_text` body that
    stood here was a SECOND normalizer with two conflicting rules — it deleted
    U+200B where the walk separates on it, and it leaked hidden-descendant
    text into `displayed` — so the walk is now the only reader.
    """
    return _visible_walk(node, hidden=hidden) if node else ''


def _words(value):
    return re.findall(r"[A-Za-z][A-Za-z’'-]*", value)


def _span(value):
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return 1


def _index_by_identity(seq, node):
    """Position of THIS node in `seq`, or None when absent.

    bs4 `Tag.__eq__` is STRUCTURAL, so `.index()`/`in` resolve a node to its
    first structural twin: a later twin row crashed `_aligned_columns` (4
    no-id facts in 0001193125-23-203780.htm) and a later twin cell cut the
    label window short (#827 SEQ 246). Geometry is an identity question —
    `is`, or absent."""
    for number, item in enumerate(seq):
        if item is node:
            return number
    return None


def _table_grid(rows):
    occupied_until = {}
    grid = []
    for row_number, row in enumerate(rows):
        placed = []
        column = 0
        for cell in row.find_all(_CELL_TAGS, recursive=False):
            width = _span(cell.get('colspan'))
            while any(occupied_until.get(item, 0) > row_number
                      for item in range(column, column + width)):
                column += 1
            placed.append((cell, column, column + width))
            height = _span(cell.get('rowspan'))
            if height > 1:
                for item in range(column, column + width):
                    occupied_until[item] = row_number + height
            column += width
        grid.append(placed)
    return grid


def _has_number_fact(row, fact_nodes):
    """Does this renderer row contain a numeric inline fact?

    THE ANSWER IS ALREADY KNOWN and is simply passed in. Which elements are
    facts was settled once, by expanded name, in the strict view; `fact_nodes`
    holds the identities of the renderer nodes those were bridged to. Asking the
    renderer tree itself would mean re-deciding an identity question in the one
    view that cannot answer it — HTML has no namespaces, so the question there
    could only be a prefix guess.
    """
    return any(id(t) in fact_nodes for t in row.find_all(True))


#: THE OFFICIAL VALUE SETS — the STANDARDS' keyword grammars transcribed, each
#: cited to its owner; nothing here is corpus-derived.
#: display: W3C CSS Display Module Level 3, CR Draft 5 June 2026, §2.
_DISPLAY_OUTSIDE = frozenset({'block', 'inline', 'run-in'})
_DISPLAY_INSIDE = frozenset({'flow', 'flow-root', 'table', 'flex', 'grid',
                             'ruby'})
_DISPLAY_SINGLE = (
    _DISPLAY_OUTSIDE | _DISPLAY_INSIDE | {'list-item'}
    | {'table-row-group', 'table-header-group', 'table-footer-group',
       'table-row', 'table-cell', 'table-column-group', 'table-column',
       'table-caption', 'ruby-base', 'ruby-text', 'ruby-base-container',
       'ruby-text-container'}                        # <display-internal>
    | {'contents', 'none'}                           # <display-box>
    | {'inline-block', 'inline-table', 'inline-flex', 'inline-grid'})  # legacy
#: visibility: CSS Display 3 §4. content-visibility: CSS Containment 2 §4.
_VISIBILITY_VALUES = frozenset({'visible', 'hidden', 'collapse'})
_CV_VALUES = frozenset({'visible', 'hidden', 'auto'})
#: CSS-wide keywords: CSS Cascade Level 5 §7. initial/inherit/unset are
#: decidable locally; revert/revert-layer roll back through origin/layer state
#: this inline-only reader does not own.
_WIDE_LOCAL = frozenset({'initial', 'inherit', 'unset'})
_WIDE_ROLLBACK = frozenset({'revert', 'revert-layer'})

_UNSUPPORTED = ('unsupported', None)   # the generic unsupported winner tuple

#: HTML Living Standard, Rendering §15.3.1 — the elements the user agent
#: itself defaults to `display:none`. A UA default is a NORMAL-origin rule an
#: author INLINE declaration lawfully overrides (same shape as the `hidden`
#: attribute), which is why this is state inside `_advance`, never a second
#: walker or a string scan. Deliberately NOT here:
#:   `noscript` — this reader has NO SCRIPTING, and §15.3.1 hides noscript
#:     only when scripting is enabled, so its contents RENDER for us;
#:   `template` — HTML LS §4.12.3 says a template REPRESENTS NOTHING and its
#:     contents are not ordinary rendered children, so it is pruned
#:     UNCONDITIONALLY below, author display notwithstanding;
#:   `input[type=hidden]` — §15.3.1 marks it `!important`, so it is not this
#:     overridable class, and an input carries no text: no branch needed.
_UA_HIDDEN_ELEMENTS = frozenset({
    'area', 'base', 'basefont', 'datalist', 'head', 'link', 'meta',
    'noembed', 'noframes', 'param', 'rp', 'script', 'style', 'title'})


def _display_valid(idents):
    """Is this ident sequence a lawful `display` value? Display 3 §2 grammar
    with `||`/`&&` ORDER INDEPENDENCE: a single keyword from any set above;
    [ <display-outside> || <display-inside> ]; or
    [ <display-outside>? && [ flow | flow-root ]? && list-item ]."""
    s = list(idents)
    if len(s) == 1:
        return s[0] in _DISPLAY_SINGLE
    if len(set(s)) != len(s):
        return False
    if 'list-item' in s:
        rest = [x for x in s if x != 'list-item']
        out = [x for x in rest if x in _DISPLAY_OUTSIDE]
        ins = [x for x in rest if x in ('flow', 'flow-root')]
        return (len(out) <= 1 and len(ins) <= 1
                and len(out) + len(ins) == len(rest))
    if len(s) == 2:
        a, b = s
        return ((a in _DISPLAY_OUTSIDE and b in _DISPLAY_INSIDE)
                or (a in _DISPLAY_INSIDE and b in _DISPLAY_OUTSIDE))
    return False


def _style_state(el):
    """The winning SPECIFIED values of the rendering properties this product
    reads — THE one CSS reader (#827 E, SEQ 227/229). One tinycss2 pass;
    per property the winner is chosen by (important, source order), CSS
    Cascade Level 5 §§4-7; a DEFINITELY INVALID declaration is dropped and
    never erases an earlier winner; a declaration this reader cannot resolve
    (substitution `var()`/`env()`, `revert`, `revert-layer`) that WINS makes
    the answer 'unsupported' — the one truthful lane, never silently visible
    and never silently invalid. The `all` shorthand accepts only CSS-wide
    keywords and feeds every property here, content-visibility included.

    The HTML `hidden` attribute (HTML Living Standard §6.1) is an OVERRIDABLE
    presentational hint: any valid author `display` declaration beats it;
    `hidden=until-found` is an official state outside this reader and takes
    the unsupported lane. `aria-hidden` is accessibility, not rendering, and
    decides nothing (corpus: zero occurrences anyway).

    SCOPE, frozen: inline style attributes and ancestry only — no stylesheet,
    selector, class or browser engine.

    Returns {'display': 'none'|'other'|None, 'visibility': kw|None,
             'cv': kw|None, 'hidden_attr': bool, 'unsupported': reason|None},
    where None means "not declared here" (inherit/absent).
    """
    hv = el.get('hidden') if el.has_attr('hidden') else None
    unsupported = None
    # ENUMERATED ATTRIBUTE, HTML LS: keywords match ASCII-case-insensitively
    # with NO whitespace repair — ' until-found ' and NBSP-padded forms are
    # INVALID VALUES and take the invalid-value default, the Hidden state
    # (SEQ 231 §2). Python .lower() on a proven-ASCII string IS exact ASCII
    # lowering; nothing is stripped.
    if hv is not None and isinstance(hv, str) and hv.isascii() \
            and hv.lower() == 'until-found':
        unsupported = 'hidden=until-found is outside the supported reader'
        hv = None
    cand = {'display': [], 'visibility': [], 'cv': []}
    # CL-090 (#827 DERIVE-CITATION, the six style-state units EU-137..142):
    # this parse rides the PINNED tinycss2 1.4.0 API (installed pin; docs
    # https://doc.courtbouillon.org/tinycss2/, version-matched) —
    # parse_declaration_list; Declaration.type == 'declaration', .name,
    # .lower_name, .important, .value; component token types 'whitespace',
    # 'comment', 'function', 'ident' and .lower_value. The '--' custom-
    # property prefix = CSS Custom Properties L1 §2 (below); the property
    # vocabulary and the 'all' shorthand carry the CSS-PIN board's cited
    # rendering law (Display 3 / Containment 2 / Cascade 4, §201-era cites).
    for i, d in enumerate(
            tinycss2.parse_declaration_list(str(el.get('style') or ''))):
        # CSS Custom Properties for Cascading Variables Level 1 §2: a custom
        # property is ANY property whose name starts with two dashes — never
        # a standard property, so it cannot be display/visibility/cv here.
        if getattr(d, 'type', None) != 'declaration' or d.name.startswith('--'):
            continue
        nm = d.lower_name
        if nm not in ('display', 'visibility', 'content-visibility', 'all'):
            continue
        toks = [t for t in d.value if t.type not in ('whitespace', 'comment')]
        # ANY function-valued winner is UNRESOLVED here, not just var()/env():
        # CSS Values 5 §7.1 lets properties accept whole-value functions and
        # §7.7.1 makes attr() a computed-time substitution too (SEQ 231 §3) —
        # dropping an unknown function as "definitely invalid" would let an
        # earlier hidden winner stand on a value we never understood.
        subst = any(t.type == 'function' for t in toks)
        idents = ([t.lower_value for t in toks]
                  if toks and all(t.type == 'ident' for t in toks) else None)
        key = (bool(d.important), i)
        if nm == 'all':
            if subst:
                for p in cand:
                    cand[p].append((key, _UNSUPPORTED))
            elif idents and len(idents) == 1 \
                    and idents[0] in (_WIDE_LOCAL | _WIDE_ROLLBACK):
                val = (_UNSUPPORTED if idents[0] in _WIDE_ROLLBACK
                       else ('wide', idents[0]))
                for p in cand:
                    cand[p].append((key, val))
            continue                        # non-wide `all` value: invalid
        prop = 'cv' if nm == 'content-visibility' else nm
        if subst:
            cand[prop].append((key, _UNSUPPORTED))
            continue
        if not idents:
            continue                        # definitely invalid: dropped
        if len(idents) == 1 and idents[0] in _WIDE_LOCAL:
            cand[prop].append((key, ('wide', idents[0])))
            continue
        if len(idents) == 1 and idents[0] in _WIDE_ROLLBACK:
            cand[prop].append((key, _UNSUPPORTED))
            continue
        if prop == 'display':
            if _display_valid(idents):
                cand[prop].append(
                    (key, 'none' if idents == ['none'] else 'other'))
            continue                        # invalid display value: dropped
        if prop == 'visibility' and idents == ['force-hidden']:
            # CSS Display Module Level 4 §5: `force-hidden` skips descendants
            # WITHOUT the self-revive `hidden` allows. An official value this
            # reader does not model may neither hide silently nor fall back
            # to an earlier declaration (SEQ 232 §1) — it participates in the
            # cascade, and its refusal detail says exactly what it is
            # (SEQ 234): official but unsupported, not "unresolvable".
            cand[prop].append((key, ('unsupported',
                               'visibility:force-hidden is official '
                               'but unsupported (CSS Display 4 §5)')))
            continue
        if len(idents) == 1 and idents[0] in (
                _VISIBILITY_VALUES if prop == 'visibility' else _CV_VALUES):
            cand[prop].append((key, idents[0]))
    out = {'hidden_attr': hv is not None, 'unsupported': unsupported}
    for p in ('display', 'visibility', 'cv'):
        best = max(cand[p], default=None, key=lambda kv: kv[0])
        v = best[1] if best else None
        tag, payload = v if isinstance(v, tuple) else (None, v)
        if tag == 'unsupported':
            out[p] = None
            out['unsupported'] = out['unsupported'] or (
                payload or f'unresolvable {p} winner in inline style')
        elif tag == 'wide':
            kw = payload
            if kw == 'inherit' or (kw == 'unset' and p == 'visibility'):
                # Cascade 5 §7.3.3: `unset` means INHERIT for an inherited
                # property, and visibility inherits — so visibility:unset
                # under a hidden ancestor STAYS hidden (SEQ 231 §1). display
                # and content-visibility are not inherited: their unset is
                # initial. inherit itself: parent state (None); display never
                # inherits a pruned parent — that subtree is already gone —
                # so display:inherit can never mean none here.
                out[p] = 'other' if p == 'display' else None
            else:                           # initial, or unset on non-inherited
                out[p] = {'display': 'other', 'visibility': 'visible',
                          'cv': 'visible'}[p]
        elif tag is not None:
            # an unknown internal tag is a programming defect — fail loudly,
            # never read it as a CSS value or a lawful abstention
            raise ValueError(f'unknown internal style winner tag: {v!r}')
        else:
            out[p] = payload
    return out


def _advance(vis, el):
    """THE one state-combine owner: fold one element into the inherited
    visibility. Returns (prune, new_vis, unsupported_reason).

    display:none and content-visibility:hidden prune ABSOLUTELY (Containment 2
    §4: no descendant revive); the bare HTML hidden attribute prunes only when
    no valid author `display` overrides it (HTML LS §6.1); visibility is
    INHERITED state a descendant `visibility:visible` may revive (Display 3
    §4). content-visibility:auto/visible INCLUDE — the evidence representation
    is viewport-independent by frozen product decision (SEQ 229).
    """
    st = _style_state(el)
    if st['unsupported']:
        return False, vis, st['unsupported']
    # EU-072 (#827 DERIVE-CITATION): `.name` is the PINNED bs4 element-name
    # API — Beautiful Soup 4.13.3 (installed pin), documented Tag.name
    # ("Every tag has a name"), https://www.crummy.com/software/
    # BeautifulSoup/bs4/doc/#name; '' is the program-logic default for
    # nameless nodes, owned by this function's law.
    name = (getattr(el, 'name', '') or '').lower()
    if name == 'template':
        # EU-070 (#827 DERIVE-CITATION): WHATWG HTML Living Standard
        # (census snapshot 2026-07-20) §4.12.3 The template element,
        # https://html.spec.whatwg.org/multipage/scripting.html#the-template-element
        # — "the template contents are not children of the element itself":
        # a template REPRESENTS NOTHING and no author display can reveal it.
        # Unconditional prune, nested markup included.
        return True, vis, None
    # HTML LS Rendering §15.3.1: UA-default display:none elements — a
    # NORMAL-origin default any valid author INLINE display declaration
    # overrides (exactly the `hidden` attribute's shape), while an author
    # `display:none` still wins.
    ua_hidden = name in _UA_HIDDEN_ELEMENTS
    # EU-071 (#827 DERIVE-CITATION), post-CSS-2.1 rendering law, version-
    # pinned at the census snapshot 2026-07-20: display:none = W3C CSS
    # Display Module Level 3, https://www.w3.org/TR/css-display-3/
    # #valdef-display-none (element and descendants generate no boxes);
    # content-visibility:hidden = W3C CSS Containment Module Level 2,
    # https://www.w3.org/TR/css-contain-2/#propdef-content-visibility
    # (contents are skipped); author-inline vs UA-default precedence =
    # HTML LS Rendering §15.3.1 (the `hidden` attribute's shape).
    prune = (st['display'] == 'none' or st['cv'] == 'hidden'
             or ((st['hidden_attr'] or ua_hidden) and st['display'] is None))
    return prune, (st['visibility'] or vis), None


def _hidden_cell(cell):
    """This ONE element's standalone answer — pruned, or declared invisible
    here. Ancestry and descendant revive are the WALK's and
    `_effective_hidden`'s business; sites that need "does this cell show any
    text" read the representation slice, which the walk owns."""
    prune, vis, unsup = _advance('visible', cell)
    if unsup:
        return False                # never silently hidden; facts refuse instead
    return prune or vis in ('hidden', 'collapse')


def _effective_hidden(node):
    """(hidden, unsupported_reason) for one renderer node, folding its whole
    ancestry through the SAME `_advance` owner the walk uses — top-down, so
    inherited visibility and revive behave exactly as in the representation."""
    chain = []
    n = node
    while n is not None and getattr(n, 'get', None):
        chain.append(n)
        n = n.parent
    vis = 'visible'
    for el in reversed(chain):
        prune, vis, unsup = _advance(vis, el)
        if unsup:
            return None, unsup
        if prune:
            return True, None
    return vis in ('hidden', 'collapse'), None


# THE edge-marker rule, and its ONLY definition. Decorative characters a filing
# puts around a heading — a dash, a space — may be ignored when DECIDING whether
# a cell carries a heading; they are never removed from what gets STORED. It is
# a RULE and not a set: the characters are recognised by asking Unicode, so no
# list exists to drift, and a dash nobody has met yet is covered on arrival.
def _is_edge_marker(ch):
    """A space, or a character Unicode itself calls dash punctuation.

    `_EDGE_MARKERS` stood here as the three characters `' —-'`, hand-picked.
    That is a SAMPLE, not a rule: EN DASH was missing, so a cell holding only
    `–` survived the selection test below and was counted as a column heading —
    3,050 heading decisions across 38 filings in the frozen manifest, every one
    a lone U+2013.

    `General_Category=Dash_Punctuation` is the standard that says which
    characters these are, and it is ASKED, never enumerated: no set is built and
    no code point is listed. U+2212 MINUS SIGN is category `Sm`, so it is
    content and stays — the same answer the three characters gave.

    The representation is whitespace-normalised before either consumer, so
    U+0020 is the only space that can reach here.
    """
    return ch == ' ' or unicodedata.category(ch) == 'Pd'


def _evidence_owner(node):
    """THE node whose span `_evidence_from` will read for `node`, and the ONLY
    place that three-branch choice is written.

      1. a `td`/`th` inside a `tr`   -> the row, for `row_span`
      2. otherwise a `p`/`li`/`div`  -> that block, for `block_span`
      3. otherwise                   -> the direct parent

    Branches 1 and 2 land on tags `_SPAN_TAGS` already records. Branch 3 does
    not, which is why `prepare` asks the walker to record exactly those parents
    as well: without them `block_span` is None and `source_evidence` refuses the
    fact outright. Returning the choice from one owner is what stops the walker
    and the reader disagreeing about which node that is.
    """
    cell = node.find_parent(_CELL_TAGS)
    row = cell.find_parent(_ROW_TAG) if cell is not None else None
    if cell is not None and row is not None:
        return True, row
    return False, node.find_parent(_BLOCK_TAGS) or node.parent


def _after_edge_markers(text):
    """`text` with its LEADING markers dropped — the one place that loop lives.

    Only the leading characters are examined, and it stops at the first one that
    is not a marker.
    """
    i = 0
    while i < len(text) and _is_edge_marker(text[i]):
        i += 1
    return text[i:]


def _visible_slice(node, prepared):
    """A node's text EXACTLY as the pinned representation holds it — its own
    recorded span, sliced out of that text — returned WITH the span.

    THE ONE OPERATION that turns a node into evidence. `_text()` reads through
    `get_text`, which INCLUDES hidden descendants, while the representation
    excludes them; every defect this replaces was that single mismatch wearing a
    different hat — a hidden-only cell becoming the row label, hidden words
    inside a row cell, and a section whose text and span came from different
    cells. Here the text and the span cannot disagree, because they are two
    views of ONE fact. It adds no parser and no rule: the walker already
    recorded both, and this only reads them together.
    """
    span = prepared.get('node_spans', {}).get(id(node))
    if span is None:
        return '', None
    return prepared['text'][span[0]:span[1]], span


#: THE STRUCTURAL GROUPS of the local-evidence contract
#: (UniversalLocator_Design_2026-07-18.md §2 + the current FinalPlan):
#: cells, the row, and the prose blocks. Each spelling is written ONCE and
#: the tracked-span union is DERIVED — the walker and every reader consume
#: these owners, so the two can never disagree about a member.
_CELL_TAGS = ['td', 'th']
_ROW_TAG = 'tr'
_BLOCK_TAGS = ['p', 'li', 'div']
_SPAN_TAGS = frozenset(_CELL_TAGS) | {_ROW_TAG} | frozenset(_BLOCK_TAGS)


def _visible_walk(root, spans=None, hidden=frozenset(), also=frozenset(),
                  flags=None):
    """THE hash-pinned representation walk: whitespace-normalized VISIBLE text
    (ix:hidden + CSS/attr-hidden excluded), optionally recording each structural
    node's EXACT character span — element-specific offsets, never global find().

    `hidden` IS THE SEMANTIC ANSWER, ALREADY RESOLVED. Which nodes are Inline
    XBRL hidden containers is a question about expanded names, and this walker
    reads the renderer tree, where names carry no namespace at all. So it is not
    asked here: `prepare()` resolves it in the strict view and hands over the
    exact renderer nodes. CSS hiding stays local because it genuinely IS a
    rendering property.
    """
    words = []

    def walk(node, vis):
        name = getattr(node, 'name', None)
        if name is None:
            # ONLY REAL TEXT NODES ARE TEXT (#827 E, SEQ 234). `name is None`
            # also matches BeautifulSoup's Comment / CData /
            # ProcessingInstruction / Declaration / Doctype nodes, and none of
            # those is rendered content — a comment or an XML declaration in
            # the representation was fabricated evidence. Emission further
            # requires the 'visible' state: visibility is INHERITED and a
            # nearer visibility:visible revives (Display 3 §4).
            if vis == 'visible' and isinstance(node, NavigableString) \
                    and not isinstance(node, (Comment, CData,
                                              ProcessingInstruction,
                                              Declaration, Doctype)):
                words.extend(str(node).replace(_ZWSP, ' ').split())
            return
        prune, vis, unsup = _advance(vis, node)   # THE one combine owner
        if unsup is not None and flags is not None:
            # AN UNRESOLVABLE WINNER POISONS THE DOCUMENT (SEQ 231 §3): text
            # under it can be neither claimed visible nor hidden, and a clean
            # fact beside it could otherwise attach guessed label/section
            # evidence. The caller turns any flag into ONE truthful
            # document-level `unsupported_style` refusal — priced by the
            # parsed census at zero function-valued winners corpus-wide.
            flags.append(unsup)
        if id(node) in hidden or prune:
            return
        # `also` carries the fallback owners `_evidence_owner` will read for
        # facts that reach its third branch — identities, not a wider tag list.
        track = spans is not None and (name.lower() in _SPAN_TAGS
                                       or id(node) in also)
        if track:
            start_tok = len(words)
        for child in node.children:
            walk(child, vis)
        if track:
            spans[id(node)] = (start_tok, len(words))

    walk(root, 'visible')
    text = ' '.join(words)
    if spans is not None:
        starts = []
        pos = 0
        for w in words:
            starts.append(pos)
            pos += len(w) + 1
        for k, (a, b) in list(spans.items()):
            spans[k] = ((starts[a], starts[b - 1] + len(words[b - 1]))
                        if b > a else (starts[a] if a < len(starts) else 0,) * 2)
    return text


def _aligned_columns(rows, row_number, fact_cell, prepared):
    """The COMPLETE aligned header stack over the exact numeric cell, near→far —
    each header returned WITH its exact source span (corrective-5: every evidence
    piece is an exact slice, never joined text).

    THE STORED TEXT IS THE CELL'S OWN SLICE. Trimming decides only whether a
    cell carries a header at all; it never decides what is STORED, because a
    stored string that differs from the characters at its own offsets is a claim
    about the filing that the filing does not make. This line previously did
    both jobs at once — reading through `_text` and stripping edge markers in
    one expression — so it leaked hidden text AND trimmed the evidence away
    from its span.
    """
    grid = _table_grid(rows)
    # MEMBERSHIP IS GUARANTEED, so there is no absent-target branch: the
    # caller resolved `row_number` by `_index_by_identity`, so `rows[row_number]`
    # IS this cell's own row, and `_table_grid` enumerates
    # `find_all(['td','th'], recursive=False)` on that SAME row object — one
    # node list, matched here by `is`. Rowspan occupancy moves a cell's
    # coordinates, never its membership. (#827 SEQ 246: the old equality-index
    # caller could hand over a structural TWIN's row number, whose grid row
    # holds no identity match — the deleted branch's "impossible" case, made
    # real. Identity restored the invariant this bare `next` now enforces.)
    _, target_start, target_end = next(
        item for item in grid[row_number] if item[0] is fact_cell)
    stack = []
    for distance in range(1, row_number + 1):
        prior_number = row_number - distance
        if _has_number_fact(rows[prior_number],
                            prepared.get('fact_nodes', frozenset())):
            continue
        for cell, start, end in grid[prior_number]:
            text, span = _visible_slice(cell, prepared)
            # The strip here is the SELECTION test only — a cell that is nothing
            # but an edge marker carries no header. The value appended is the
            # untrimmed slice.
            if end <= target_start or start >= target_end \
                    or all(_is_edge_marker(c) for c in text) \
                    or (start == 0 and target_start > 0):
                continue                     # numeric-only headers ('2024') RETAINED
            stack.append((text, span))
    return stack


# ---- document preparation (ONE parse per filing) --------------------------------

class SemanticParseError(Exception):
    """The document is not a readable Inline XBRL report.

    Raised NOWHERE outside this module: both public doors turn it into one
    truthful refusal, so no lxml or bs4 exception ever escapes to a caller.
    """


#: The ONE public reason. Ours, fixed, and identical for every unreadable
#: document: a caller must never be able to read parser wording as a finding.
NOT_WELL_FORMED = 'document is not a well-formed XML Inline XBRL report'
#: SEC EDGAR XBRL Guide June 2026 §11.1 (EFM v49 December-2018 §5.2.5.1
#: before it): an `.htm` attachment carrying a DOCTYPE declaration is not a
#: valid Inline XBRL document. ITS OWN REASON, because such a document can be
#: perfectly well-formed — reporting it as NOT_WELL_FORMED would be false.
DOCTYPE_FORBIDDEN = 'document declares a DOCTYPE, which EDGAR forbids in an Inline XBRL report'


#: THE ONE PARSER POLICY, shared by the bounded prolog pass and the semantic
#: tree so the two can never drift apart. EU-039 (#827, DERIVE-CITATION):
#:  - dependency API: lxml 6.0.2 (the installed pin; drift row 5.3.1->6.0.2
#:    recorded) — lxml.etree.XMLParser documented parameters `recover`,
#:    `resolve_entities`, `load_dtd`, `no_network`, `encoding`
#:    (https://lxml.de/api/lxml.etree.XMLParser-class.html, version-matched);
#:  - product security policy (no network, no DTD, no entity resolution at
#:    parse time): the #826-accepted zero-credential/zero-network clean-lane
#:    law (push 4d473822, reviewer-verified) applied at the parse boundary —
#:    a filing's bytes may never trigger a fetch or expand hidden content;
#:  - 'utf-8' decl-encoding choice: WHOEVER MAKES THE BYTES OWNS THEIR
#:    ENCODING (test_parser_encoding_ownership's law; EDGAR EFM note in
#:    BOARD:EDGAR-EFM).
_PARSER_OPTIONS = dict(recover=False, resolve_entities=False, load_dtd=False,
                       no_network=True, encoding='utf-8')


class _DoctypeDeclared(Exception):
    """Internal signal: the prolog declared a DOCTYPE."""


class _RootReached(Exception):
    """Internal signal: the prolog ended and the root element began."""


class _Prolog:
    """Reads the document PROLOG ONLY. It builds nothing and decides nothing.

    THE DOCTYPE MUST BE REFUSED BEFORE THE ROOT ATTRIBUTES EXPAND. Nested
    internal entities in a single attribute reach libxml2's entity
    amplification limit DURING that expansion, which surfaces as an
    `XMLSyntaxError`; a boundary placed after the parse therefore reported a
    forbidden-but-well-formed document as not-well-formed. Reporting a
    resource limit as a grammar failure is a false statement about the filing.

    IT DOES NOT BUILD THE TREE. A target-built tree was tried and rejected: in
    target mode libxml2 does not raise on an undeclared namespace prefix, so
    `<hid:b/>` silently became `b` — a name turning into a DIFFERENT name,
    which is the one thing this module exists to prevent. Namespace identity
    stays where it is decided correctly, in lxml's own tree parse.

    So this pass answers exactly one question — was a DOCTYPE declared before
    the root began — and `start` ends it at the first root element, before the
    body is read. `close()` re-raises the stored signal because lxml calls it
    even after a callback raises and would otherwise replace the answer.
    """

    def __init__(self):
        self._signal = None

    def doctype(self, name, pubid, system):
        self._signal = _DoctypeDeclared()
        raise self._signal

    def start(self, tag, attrib, nsmap=None):
        self._signal = _RootReached()
        raise self._signal

    def close(self):
        if self._signal is not None:
            raise self._signal


def _semantic_parse(html_text):
    """The strict namespace-aware tree, or SemanticParseError.

    Inline XBRL Part 1 requires a conforming report to be a well-formed XML
    document, and namespaces are defined only over XML. THIS tree therefore owns
    IDENTITY — expanded names and the in-scope namespace map — and nothing else.
    It never owns visible text: that is the renderer view's job, and the two are
    kept plainly separate so neither can quietly answer the other's question.

    `recover=False` so a document that is not well-formed is refused rather than
    silently repaired into a tree nobody wrote; the DTD and the network are off
    so nothing is fetched, and entity RESOLUTION is off. Parser safety limits
    stay at their defaults.

    THE FLAGS ALONE DO NOT CLOSE THE ENTITY CHANNEL, so the DOCTYPE itself is
    refused — by `_Prolog`, at the declaration, before the root attribute is
    expanded. `resolve_entities=False` governs text nodes; lxml still expands
    an internal-subset entity inside an ATTRIBUTE value, so `contextRef="&a;"`
    bound a fact to a context the markup never names. EDGAR forbids the
    declaration outright (June 2026 guide §11.1; EFM v49 December-2018
    §5.2.5.1), so refusing it at THIS boundary — before any context, unit or
    fact is read — closes the channel at its source rather than chasing each
    place an entity might appear.

    TWO LXML INVOCATIONS, ONE TREE. The first is bounded to the prolog and
    stops at the first root element; it builds nothing and answers only
    "was a DOCTYPE declared". The second is the ORIGINAL native parse,
    unchanged, and remains the only semantic tree — because namespace identity
    must be decided by lxml's tree parse, which alone refuses an undeclared
    prefix instead of silently renaming the element. Both read the SAME bytes
    under the SAME `_PARSER_OPTIONS`, so they cannot drift apart.

    ONLY the two internal signals and `XMLSyntaxError` become refusals. A
    TypeError or MemoryError is OUR bug or the machine's limit, and reporting
    either as a malformed filing would be a false finding about the document.
    Each parser is built PER CALL because the prolog target carries
    per-document state.

    THE BYTES ARE OURS, SO THE ENCODING IS OURS TO DECLARE. This function's
    input contract is already-decoded text, which is then encoded to UTF-8 one
    line below. Left unstated, a lawful `encoding="ISO-8859-1"` inside the
    document would re-decode OUR UTF-8 bytes under a different codec: `é`
    became `Ã©`, changing the expanded names, QName values and dimension
    members THIS tree owns. The declaration describes the filer's original
    bytes, which we no longer hold; it cannot describe ours.

    The damage stayed inside this view — the renderer parse is handed the
    original Python string and was never re-decoded — but it was not always
    loud: where the mojibake is still a lawful XML name, nothing raises and the
    identity is simply wrong.
    """
    data = html_text.encode('utf-8', 'surrogatepass')   # encoded ONCE, so both
    try:                                                # passes read one input
        etree.fromstring(data, etree.XMLParser(target=_Prolog(),
                                               **_PARSER_OPTIONS))
    except _DoctypeDeclared:
        raise SemanticParseError(DOCTYPE_FORBIDDEN) from None
    except _RootReached:
        pass                          # the prolog is clean; read the real tree
    except etree.XMLSyntaxError as exc:
        raise SemanticParseError(NOT_WELL_FORMED) from exc
    try:
        return etree.fromstring(data, etree.XMLParser(**_PARSER_OPTIONS))
    except etree.XMLSyntaxError as exc:
        raise SemanticParseError(NOT_WELL_FORMED) from exc


def _soup(html_text):
    """THE RENDERER VIEW — how the filing APPEARS, and nothing else.

    A filing is read by people through a browser, so what counts as the visible
    text, a row, a column heading or a section is decided by HTML's own rules —
    including the repairs a browser performs on imperfect markup. This is
    therefore an HTML parse ON PURPOSE, and it is the sole owner of `text`,
    `node_spans` and every span this module ever reports.

    It has NO authority over meaning. HTML has no namespaces and lower-cases
    every element and attribute name, so `contextRef` and `contextref` and
    `xmlns:XBRLI` and `xbrli:` all arrive indistinguishable — which is exactly
    why identity lives in `_semantic_parse` instead, and why the two views are
    never allowed to answer each other's questions.

    Parsing an XML-declared filing as HTML is this function's DELIBERATE choice,
    so `XMLParsedAsHTMLWarning` is ours to ignore — here, for this call, and
    nowhere else. `catch_warnings` restores the caller's filters on exit.
    """
    # EU-131 (#827 FAIL-CLOSED; measured recall 1,903 corpus docs / 0
    # refusals, g2_evid_recall_EU-131.txt): every parser warning EXCEPT the
    # one deliberate suppression is a signal about the bytes and refuses
    # TYPED — never a silent pass.
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)
        try:
            # EU-132 (#827 DERIVE-CITATION): 'lxml' is the PINNED bs4 tree
            # builder — Beautiful Soup 4.13.3, "Installing a parser" table
            # (https://www.crummy.com/software/BeautifulSoup/bs4/doc/
            # #installing-a-parser), lxml's HTML parser, backed by libxml2
            # via lxml 6.0.2 (drift row 5.3.1->6.0.2 recorded).
            return BeautifulSoup(html_text, 'lxml')
        except Warning as w:
            raise SemanticParseError(
                f"renderer parse warning: {type(w).__name__}: {w}") from w


#: The three namespaces this parser consumes. Fixed standard URIs are the
#: vocabulary of the contract, not a sample-derived allowlist — and they are
#: the ONLY thing that carries identity here. No conventional prefix (`xbrli`,
#: `ix`, `xbrldi`, `i`) appears anywhere in this module's logic.
#: The instance-namespace URI lives at its ONE owner,
#: `exact_numbers.XBRL_INSTANCE_NAMESPACE`.
_DIMENSION_NS = 'http://xbrl.org/2006/xbrldi'
#: INLINE XBRL 1.1, AND ONLY 1.1 — a standards-bound product boundary for the
#: SEC filing route, not a shape inferred from the filings we happen to hold.
#: SEC EDGAR XBRL Guide, June 2026, §11.2: an Inline XBRL document must be
#: valid against Inline XBRL 1.1. Archived EFM v38 §5.2.5.2 names both the
#: version and this exact namespace.
#:
#: The #827 corpus scanner counts the Inline XBRL 1.0 namespace as well, but
#: that is DETECTION ONLY: it exists so a 1.0 document is visible rather than
#: silently absent from a census. Being able to identify 1.0 is not a reason to
#: support it here, and nothing below admits it.
_INLINE_NS = 'http://www.xbrl.org/2013/inlineXBRL'


#: Namespaces in XML 1.0 §3 — the one prefix bound by the standard itself.
_XML_PREFIX_NS = 'http://www.w3.org/XML/1998/namespace'


def _clark(uri, local):
    """(namespace URI, local name) written the way lxml stores a tag.

    EU-078 (#827 DERIVE-CITATION): the '{namespace}local' universal-name
    (Clark) form is the PINNED dependency's documented tag representation —
    lxml 6.0.2 (installed pin; drift row 5.3.1->6.0.2 recorded), namespaces
    section of the official tutorial, https://lxml.de/tutorial.html#namespaces
    ("the ElementTree API ... uses ... {namespace}localname"); notation after
    J. Clark, http://www.jclark.com/xml/xmlns.htm."""
    return '{%s}%s' % (uri, local)


def _is(el, uri, local):
    """Element identity: (namespace URI, local name). NEVER the prefix.

    `el.tag` is the expanded name the parser resolved for THIS element,
    honouring the declaration in scope, any inner rebinding, a default `xmlns=`,
    and case. A comment or processing instruction carries a callable tag, so it
    can never equal a name and needs no separate guard.
    """
    return el.tag == _clark(uri, local)


def _children(el):
    """Direct child ELEMENTS.

    Comments and processing instructions are markup ABOUT a document, not
    content in it. lxml yields them as children where the previous parser did
    not, so they are excluded exactly once — here — rather than at each of the
    four callers that would otherwise read a lawful comment as unknown markup.
    """
    return [k for k in el if isinstance(k.tag, str)]


def _kids(el, uri, local):
    """DIRECT children of that expanded name only.

    XBRL 2.1 fixes WHERE every value lives, and this parser only ever asked
    WHETHER one existed: a subtree search read a filer id inside `period`, dates
    inside `entity`, and a `unitNumerator` with no `divide` above it at all as
    though correctly placed.
    """
    return [k for k in el if k.tag == _clark(uri, local)]


def _all(el, uri, local):
    """Every DESCENDANT of that expanded name — used ONLY to prove nothing of
    ours sits outside its container. Read from the direct children, then check
    the subtree holds no more: markup we do not understand is never evidence."""
    return [d for d in el.iter(_clark(uri, local)) if d is not el]




def _qname(value, el):
    """A QName VALUE resolved where it is written: (uri, local), or None.

    A measure, an axis, a member or a concept name is a QName; its meaning comes
    from the namespace its prefix is bound to, so `notaprefix:USD` names nothing
    at all. An UNPREFIXED value takes the in-scope default namespace, which XBRL
    2.1 §4.8.2 as corrected by the errata to 2013-02-20 (Appendix D erratum 62)
    permits — `measure` is simply `xsd:QName`, so the rule is resolvability, not
    the presence of a colon.

    THE IN-SCOPE MAP COMES FROM THE PARSER (EU-121, #827 DERIVE-CITATION):
    `nsmap` is the PINNED dependency's documented attribute — lxml 6.0.2
    (installed pin; drift row 5.3.1->6.0.2 recorded), _Element.nsmap,
    https://lxml.de/api/lxml.etree._Element-class.html#nsmap — lxml's own view
    of the declarations in force AT THIS ELEMENT, innermost winning, with the
    default under the key `None` — which is exactly what XML scoping means and
    what the hand-written ancestor walk this replaces was re-deriving by hand.

    THE GRAMMAR (EU-122, #827 DERIVE-CITATION, exact form): W3C Namespaces in
    XML 1.0 (Third Edition), W3C Recommendation 8 December 2009,
    https://www.w3.org/TR/2009/REC-xml-names-20091208/ — §4 "Qualified Names"
    (QName ::= PrefixedName | UnprefixedName; PrefixedName wants a NON-EMPTY
    Prefix ':' LocalPart, so ':x' names nothing; an unprefixed name is lawful).

    ONE prefix is not in that map and never can be: `xml`. The SAME REC's §3
    ("Declaring Namespaces") binds it to the URI below BY DEFINITION and says
    it need not — and by its reservation, effectively must not — be declared,
    so lxml reports an empty `nsmap` for a document using it. Calling such a QName undeclared would
    be OUR error, not the filing's. This is the standard's own fixed binding, the
    only one, and no other prefix gets a fallback of any kind.
    """
    if not isinstance(value, str) or not hasattr(el, 'nsmap'):
        return None
    prefix, sep, local = value.partition(':')
    # A colon with NOTHING before it is not a PrefixedName: the grammar wants a
    # non-empty Prefix. The library cannot say so on its own, because it is only
    # ever handed one part at a time.
    if sep and not prefix:
        return None
    if not sep:
        prefix, local = '', value
    if not xml_name_ok(local) or (prefix and not xml_name_ok(prefix)):
        return None
    if prefix:
        # AN EXPLICIT PREFIX MUST BE BOUND. Nothing binds it, nothing names it.
        uri = el.nsmap.get(prefix) or (_XML_PREFIX_NS if prefix == 'xml'
                                       else None)
        return None if uri is None else (uri, local)
    # UNPREFIXED: the in-scope default namespace if one exists, and otherwise
    # the ABSENT namespace — which XML Schema QName resolution makes a lawful
    # value, not an error. `(None, local)` says exactly that and cannot be
    # confused with this function's own failure, a bare `None`. Whether such a
    # name may be USED is the consumer's contract, not this resolver's: a
    # concept or dimension with no namespace simply cannot equal a namespaceful
    # graph target, so it abstains truthfully at the comparison instead of
    # being called malformed here.
    return (el.nsmap.get(None), local)


_PREP_CACHE = {}


#: XBRL 2.1 §4.7.3 makes `scheme` REQUIRED, and it is what gives the digits
#: their meaning: the same ten digits under another registry's scheme name a
#: DIFFERENT entity. The SEC filer manual fixes this one URI, and the graph's
#: `entity_cik` IS a SEC CIK — so this is the only scheme under which those
#: digits may be read as one. Measured over the frozen cache: 733,172
#: identifiers, every one carrying exactly this scheme and exactly ten ASCII
#: digits, so enforcing all of it costs zero real evidence.
SEC_CIK_SCHEME = 'http://www.sec.gov/CIK'
#: XML 1.0 S — the ONLY whitespace a document may pad a value with. Python's
#: `.strip()` also eats NBSP, ideographic and zero-width space, which would
#: quietly normalise ` 0000320193` into a clean CIK.
#:
#: THE DECLARATION IS GONE, and the rule now has ONE owner. It held the same
#: four characters as `exact_numbers.XML_WS`, which this module already imports,
#: so XML 1.0 5e §2.3 was written twice — `xbrl_attach` reading one name and
#: this module the other — under a comment at that import already claiming a
#: single owner. Editing either copy would have moved half the consumers.


def _sec_cik(identifier):
    """The filer's ten ASCII digits, or None when the markup does not state
    them lawfully.

    BOTH HALVES CARRY whiteSpace=COLLAPSE: XBRL 2.1 declares the identifier's
    content as xs:token and its `scheme` as a restricted xs:anyURI. So the same
    shared `_collapse` reads them — never `_text()`, which collapses UNICODE
    whitespace and deletes zero-width characters, and would normalise away the
    very padding this rule exists to catch.
    """
    if (_typed(identifier, 'scheme') or '') != SEC_CIK_SCHEME:
        return None
    raw = _leaf(identifier)
    if raw is None:
        return None
    digits = _collapse(raw)
    # LEXICAL ONLY, from the one owner: the all-zero non-registrant marker is a
    # well-formed identifier in a filing, and refusing it is `graph_cik`'s job.
    return digits if re.fullmatch(_SEC_CIK_10_PATTERN, digits) else None


def _ordered(parent, *names):
    """The named direct children appear in XBRL 2.1's declared sequence.

    ORDER IS PART OF THE SCHEMA, not decoration. `xs:sequence` fixes entity
    before period before scenario, identifier before segment, startDate before
    endDate, and numerator before denominator — and none of it was checked, so
    a reversed divide read `share/USD` as though it were `USD/share`: a
    different unit wearing the same name.
    """
    seen = []
    for t in _children(parent):
        for rank, (uri, local) in enumerate(names):
            if _is(t, uri, local):
                seen.append(rank)
                break
    return seen == sorted(seen)


def _only(parent, *names):
    """Every DIRECT child of `parent` is one of these expanded names.

    Markup we do not understand sitting where our own elements belong is not
    evidence to read around — it means the shape is not the one XBRL declares.
    """
    return all(any(_is(t, uri, local) for uri, local in names)
               for t in _children(parent))


def _xml_id(value):
    """The element's id, or None when it is not a lawful XML name.

    An XML ID is an NCName, and THE GRAMMAR IS THE LIBRARY'S — `xml_name_ok`,
    the same owner every other name in this module is asked of. The ASCII regex
    that stood here restated it and got it wrong in both directions: it rejected
    the lawful Unicode NCNames XML permits, and it was a second grammar to keep
    in step with the first.
    """
    return value if isinstance(value, str) and xml_name_ok(value) else None


def _leaf(el):
    """A leaf element's complete character content, or None when it carries an
    ELEMENT child.

    Flattening markup made `<identifier><b>0000320193</b></identifier>` read as
    a clean CIK and `<startDate><b>2026-01-01</b></startDate>` as a clean date.
    A value with structure inside it is not a value, so an element child still
    refuses — including an EMPTY one whose tail carries the whole value.

    COMMENTS AND PIs ARE NOT CONTENT (XML 1.0 5e §2.5/§2.6: a processor must
    not pass them as character data), so they cannot make a lawful value
    unreadable. `len(el)` counted them, which REFUSED lawful filings at every
    door this helper serves — identifier, instant/startDate/endDate, the
    dimension member value and measure. The old note feared reading
    `<startDate>2026-<!--x-->01-01</startDate>` as the truncated `2026-`; that
    is why the runs are JOINED in document order rather than cut. Not
    `itertext()`, which would also flatten the real element children above.

    THE ONLY NON-ELEMENT CHILDREN THAT REACH HERE ARE THOSE TWO. The third
    kind, an unresolved general entity, cannot: an UNDECLARED entity is an XML
    syntax error, and a DECLARED one needs the DOCTYPE that `_semantic_parse`
    refuses at the document boundary (SEC EDGAR XBRL Guide June 2026 §11.1).
    So the rule is stated on what it actually decides — element or not — and
    the entity case is owned once, upstream, instead of twice.
    """
    if any(isinstance(child.tag, str) for child in el):
        return None
    return (el.text or '') + ''.join(child.tail or '' for child in el)


def _measure_text(m):
    """A measure's QName value, read as xs:QName declares it.

    ONE reader, so the string that is VALIDATED as a QName and the string that
    is STORED are the same string. They used to be produced by two different
    functions, one of which collapsed UNICODE whitespace and deleted zero-width
    characters — a repair, and a QName is never repaired.

    `_collapse` is the type's own facet and nothing more: it is the SAME
    function every other collapse-faceted value goes through, so a measure, a
    member, an axis and a fact's name cannot drift into four spellings of one
    rule. Internal space stays invalid.
    """
    return _collapse(_leaf(m) or '')


#: THE two namespace URIs — XML Schema 1.0 Structures 2e §2.6 defines the XS
#: vocabulary URI and the XSI instance URI. ONE definition each.
_XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
_XS_NS = 'http://www.w3.org/2001/XMLSchema'
#: THE context grammar's fixed types: XBRL 2.1 REC 2003-12-31 + corrected
#: errata 2013-02-20, official instance schema lines 602-680.
#: xbrli:dateUnion admits exactly this triad (:629-636); xsi:type may lawfully
#: restate any member, under ANY in-scope prefix.
_CTX_DATE_TRIAD = frozenset({(XBRL_INSTANCE_NAMESPACE, 'dateUnion'),
                             (_XS_NS, 'date'), (_XS_NS, 'dateTime')})
#: Each supported element's EXACT declared type (same schema, :602-680 for the
#: context grammar, :681-720 for the unit grammar). The EMPTY sets are the law,
#: not a gap: those elements are declared with ANONYMOUS types, and §2.6.1 /
#: §3.3.4 require an asserted type to be validly derived from the declared one
#: — nothing can derive from an anonymous type, so they admit NO xsi:type at
#: all. Re-proven identical in the 2013 Inline-XBRL modified instance schema,
#: so no row here is a version artifact.
_SHAPE_TYPES = {
    'entity': frozenset({(XBRL_INSTANCE_NAMESPACE, 'contextEntityType')}),
    'period': frozenset({(XBRL_INSTANCE_NAMESPACE, 'contextPeriodType')}),
    'scenario': frozenset({(XBRL_INSTANCE_NAMESPACE, 'contextScenarioType')}),
    'instant': _CTX_DATE_TRIAD, 'startDate': _CTX_DATE_TRIAD,
    'endDate': _CTX_DATE_TRIAD,
    'context': frozenset(), 'identifier': frozenset(),
    'segment': frozenset(), 'forever': frozenset(),
    # the unit grammar (XBRL 2.1 §4.8)
    'unit': frozenset(), 'divide': frozenset(),
    'unitNumerator': frozenset({(XBRL_INSTANCE_NAMESPACE, 'measuresType')}),
    'unitDenominator': frozenset({(XBRL_INSTANCE_NAMESPACE, 'measuresType')}),
    'measure': frozenset({(_XS_NS, 'QName')}),
}
#: The only DECLARED no-namespace attributes anywhere in the supported grammar.
#: `unit/@id` is type="ID" use="required"; its VALUE and uniqueness stay with
#: the existing resource-indexing door, which is why only the NAME appears here.
_SHAPE_ATTRS = {'context': frozenset({'id'}),
                'identifier': frozenset({'scheme'}),
                'unit': frozenset({'id'})}
#: The declared CONTENT MODEL. `empty` admits no character item at all, not
#: even XML whitespace; `element-only` admits XML whitespace between children
#: and nothing else; `simple` means the characters ARE the value and belong to
#: the reader that owns them.
_SHAPE_CONTENT = {
    'context': 'element-only', 'entity': 'element-only',
    'period': 'element-only', 'segment': 'element-only',
    'scenario': 'element-only', 'forever': 'empty',
    'identifier': 'simple', 'instant': 'simple',
    'startDate': 'simple', 'endDate': 'simple',
    'unit': 'element-only', 'divide': 'element-only',
    'unitNumerator': 'element-only', 'unitDenominator': 'element-only',
    'measure': 'simple',
}
#: The elements whose asserted xs: member must also match the VALUE's kind.
_SHAPE_TYPED_VALUE = frozenset({'instant', 'startDate', 'endDate'})
#: A unit element asserts a RESOLVED non-standard type. Its own reason, not
#: `unsupported_context_type` and not "malformed": the declaration resolves, so
#: the filing may be perfectly valid — we simply cannot prove the derivation
#: without the foreign schema, and calling a filing malformed because we cannot
#: check it would be a false finding about the document.
UNSUPPORTED_UNIT_TYPE = 'unsupported_unit_type'


def _shape(el, local):
    """THE instance-schema shape law for ONE element: its xsi:type, its
    attributes and its declared character content. 'malformed', 'unsupported',
    or None when the element is well shaped.

    ONE OWNER FOR TWO GRAMMARS (#827 B12 SEQ 369, extended B16). Contexts and
    units are judged by the same three questions against the same pinned
    schema; only the TABLE differs, so this is one rule with data rather than
    two rules that could drift apart. It judges ONLY those three things — it is
    not, and must not become, a general XML validator.

    xsi:type is judged FIRST, so a lawful custom-derived type parks as
    unsupported BEFORE its unknown attributes could be mislabeled malformed.
    """
    t = el.get('{%s}type' % _XSI_NS)
    if t is not None:
        q = _qname(_collapse(t), el)       # THE one QName owner — never a
        if q is None:                      # second strip/partition parser
            return 'malformed'             # malformed/undeclared QName
        ns, lname = q                      # resolved even when ns is None
        allowed = _SHAPE_TYPES[local]
        if not allowed:
            # AN ANONYMOUS DECLARED TYPE ADMITS NO REPLACEMENT AT ALL: an
            # asserted type must be validly DERIVED FROM the declared one
            # (XML Schema 1.0 Structures 2e §2.6.1, §3.3.4), and nothing
            # can reference an anonymous type. Not a custom-park case.
            return 'malformed'
        if (ns, lname) not in allowed:
            if ns in (XBRL_INSTANCE_NAMESPACE, _XS_NS):
                return 'malformed'         # a DIFFERENT known official type
            return 'unsupported'           # resolved non-standard type
        if ns == _XS_NS and local in _SHAPE_TYPED_VALUE:
            # THE TYPE CONSTRAINS THE VALUE (SEQ 373 B, XSD-proven): the
            # one shared dateUnion owner classifies the raw leaf, and the
            # declared member must match its kind. Outside the lexical
            # space entirely -> the existing downstream law owns it; a
            # lawful-but-unrepresentable date (.park) stays lawful here.
            try:
                if parse_filing_boundary(el.text or '').kind != lname:
                    return 'malformed'
            except ExactError:
                pass
    for k in el.attrib:
        qk = etree.QName(k)
        if qk.namespace is None:
            if qk.localname not in _SHAPE_ATTRS.get(local, ()):
                return 'malformed'         # ordinary undeclared attribute
        elif qk.namespace == _XSI_NS and (qk.localname in _XSI_PASS
                                          or qk.localname == 'type'):
            continue                       # xsi specials; type judged above
        else:
            return 'malformed'             # xsi:nil, xml:*, any foreign
    texts = [el.text or ''] + [c.tail or '' for c in el]
    kind = _SHAPE_CONTENT[local]
    if kind == 'empty':                    # NO character item at all,
        if any(texts) or any(isinstance(c.tag, str) for c in el):
            return 'malformed'             # XML whitespace included
    elif kind == 'element-only':
        if any(s.strip(XML_WS) for s in texts):
            return 'malformed'             # non-XML-whitespace character data
    return None                            # 'simple': the text IS the value,
                                           # owned by its own reader
#: The two schema-location hints §2.6.3 permits on ANY element. `xsi:type`
#: (§2.6.1) is judged separately above and is NEVER unconditional — the
#: asserted type must be validly derived from the declared one. The fourth
#: schema-related attribute, `xsi:nil`, is excluded HERE because none of these
#: XBRL context declarations is nillable.
_XSI_PASS = frozenset({'schemaLocation', 'noNamespaceSchemaLocation'})


def _parse_context(context):
    """The XBRL 2.1 §4.7 context: a usable evidence DICT, a truthful refusal
    REASON STRING, or None for malformed structure (the caller names that one).

    The shape law is ONE entity (ONE identifier, at most one segment), ONE
    period holding exactly one form, at most one scenario, dimension members
    only inside a segment or scenario, and — per element — its declared
    attributes, its declared type, and its declared character content."""
    I, D = XBRL_INSTANCE_NAMESPACE, _DIMENSION_NS
    entities, periods = _kids(context, I, 'entity'), _kids(context, I, 'period')
    scenarios = _kids(context, I, 'scenario')
    if len(entities) != 1 or len(periods) != 1 or len(scenarios) > 1:
        return None
    entity, period = entities[0], periods[0]
    idents = _kids(entity, I, 'identifier')
    segments = _kids(entity, I, 'segment')
    if len(idents) != 1 or len(segments) > 1:
        return None
    boxes = segments + scenarios
    members = [m for b in boxes for m in _kids(b, D, 'explicitMember')]
    typed = [t for b in boxes for t in _kids(b, D, 'typedMember')]
    inst = _kids(period, I, 'instant')
    start = _kids(period, I, 'startDate')
    end = _kids(period, I, 'endDate')
    ever = _kids(period, I, 'forever')
    # (the `placed` table went with the descendant check it fed — see below)
    # EXACTLY ONE PERIOD FORM (§4.7.2). One tuple states the whole law that the
    # old arithmetic spread over a `kinds` sum plus four duplicate guards — and
    # it closes the case that sum could not see, TWO `forever` collapsing to one.
    if tuple(map(len, (inst, start, end, ever))) not in (
            (1, 0, 0, 0), (0, 1, 1, 0), (0, 0, 0, 1)):
        return None

    for el, name in ((context, 'context'), (entity, 'entity'),
                     (idents[0], 'identifier'), (period, 'period'),
                     *((s, 'segment') for s in segments),
                     *((s, 'scenario') for s in scenarios),
                     *((d, 'instant') for d in inst),
                     *((d, 'startDate') for d in start),
                     *((d, 'endDate') for d in end),
                     *((f, 'forever') for f in ever)):
        verdict = _shape(el, name)
        if verdict == 'malformed':
            return None
        if verdict == 'unsupported':           # the string IS the reason — the
            return 'unsupported_context_type'  # caller stores it verbatim
    # THE DESCENDANT `placed` CHECK IS DELETED. It compared each direct-child
    # list against EVERY same-named descendant, which the XBRL content model
    # does not license: `segment`/`scenario` are open and a `typedMember` value
    # may lawfully nest arbitrary markup, so a nested element merely SHARING a
    # local name refused the whole context — and refused it as malformed,
    # taking the naming decision away from the typed and open-content rules
    # that own it.
    #
    # Its job is already done, and by rules that are true: the direct-child
    # checks above close the supported tree, `_ordered` fixes the sequence,
    # and both open-content classes (typed, non-XDT) park BEFORE anything
    # inside them is interpreted — so no arbitrary descendant is ever read as
    # evidence. The regression lane is what holds that claim up.
    # UNKNOWN DIRECT CHILDREN. Measured on DIRECT children only — a descendant
    # scan counts the 2,112 lawful typedMember VALUES in the cache and would
    # have argued for refusing real contexts. Direct children of a context are
    # exactly entity and period (733,172/733,172); of an entity, identifier and
    # segment; of a period, its one form; of segment/scenario, members only.
    if not _only(context, (I, 'entity'), (I, 'period'), (I, 'scenario')):
        return None
    if not _only(entity, (I, 'identifier'), (I, 'segment')):
        return None
    if not _only(period, (I, 'instant'), (I, 'startDate'), (I, 'endDate'),
                 (I, 'forever')):
        return None
    # ONE CONTENT-MODEL RULE FOR THE OPEN CONTAINERS, replacing a restriction
    # the standard does not impose. XBRL 2.1 declares `segment` and
    # `scenario` OPEN (`xs:any`, `##other`) and XBRL Dimensions 1.0 §3.1.4.4
    # says plainly that not every element in them is a dimension element — so
    # `_only(box, explicitMember, typedMember)` refused lawful filings, and
    # refused them as MALFORMED, which accuses the filer of an error they did
    # not make.
    #
    # What the schema DOES fix is cardinality: the open content is
    # `minOccurs="1"`, so a container that is present must hold at least one
    # element. Present-and-empty is genuinely malformed — and it used to
    # ATTACH, stating a dimension set it did not carry.
    #
    #   absent            -> allowed (the container is optional)
    #   present, empty    -> malformed, here
    #   present, members  -> handled below
    #   present, other    -> LAWFUL but unrepresentable; recorded as
    #                        `non_xdt` and named by the caller, never dropped —
    #                        ignoring it would merge two distinct contexts.
    # `##other` MEANS OTHER — it admits any namespace EXCEPT the instance
    # namespace itself. So a child in the xbrli namespace is not lawful open
    # content at all; it is markup in a place the schema forbids, and that is
    # genuinely malformed. An existing attack case (`xbrli:notAMember` inside a
    # segment) is exactly this, and it caught my first rule treating every
    # non-member child as lawful.
    kids = [child for box in boxes for child in _children(box)]
    if any(not _children(box) for box in boxes):
        return None                       # present and empty: minOccurs="1"
    # THE LIBRARY'S NAMESPACE IDENTITY, not a prefix-match on the serialised
    # tag. `startswith('{uri}')` re-implements namespace parsing with string
    # matching — the exact habit this audit exists to remove — and would also
    # match a longer URI that merely begins with this one.
    if any(etree.QName(c).namespace == I for c in kids):
        return None                       # instance-namespace child: not `##other`
    non_xdt = any(not (_is(child, D, 'explicitMember')
                       or _is(child, D, 'typedMember')) for child in kids)
    if any(_leaf(d) is None for d in inst + start + end):
        return None
    if not (_ordered(context, (I, 'entity'), (I, 'period'), (I, 'scenario'))
            and _ordered(entity, (I, 'identifier'), (I, 'segment'))
            and _ordered(period, (I, 'startDate'), (I, 'endDate'))):
        return None
    # VALIDATE, THEN SORT. A member with no `dimension=` contributed `None`, and
    # sorting `None` against a string raises TypeError — so ONE nameless
    # dimension beside a lawful one CRASHED the public door instead of parking
    # the fact. A crash is not a refusal: it takes the whole event down rather
    # than one number. Lawful values are passed through UNCHANGED; only the
    # missing and the blank are refused.
    cik = _sec_cik(idents[0])
    if cik is None:
        return None
    # TWO VIEWS OF ONE READING, built in this single loop from the same two
    # values, so they can never describe different dimensions:
    #   `spellings` — the QNames AS THE FILING WROTE THEM, collapsed. This is
    #       the frozen product output and nothing else; a prefix is this
    #       document's private alias and proves no identity.
    #   `dims`      — the EXPANDED (namespace URI, local name) pairs. This is
    #       the only thing any semantic comparison may look at.
    # Naming them apart is what stops the older mistake from returning: one
    # field serving both purposes must be wrong for one of them.
    spellings, dims = [], []
    for member in members:
        # SIMPLE TEXT ONLY, and both halves must be QNames this document
        # declares: `<explicitMember><b>a:M</b></explicitMember>` was flattened
        # by `get_text` into a clean member name.
        # BOTH ARE xs:QName, so both go through the ONE collapse the facet
        # calls for — the same function the fact's own name uses.
        axis, value = _typed(member, 'dimension'), _leaf(member)
        if value is None or axis is None:
            return None
        value = _collapse(value)          # content, not an attribute
        # BOTH HALVES ARE QNAMES, resolved in the scope of the member that
        # writes them — and the EXPANDED NAME is what the filing publishes.
        #
        # The raw spelling used to travel instead, because "that is the graph's
        # contract". It is not, and could not be: `srt:` is a prefix THIS
        # document chose, and the graph's `srt:` is a prefix some other document
        # chose. Comparing them is comparing two unrelated aliases and calling
        # the result identity. The graph's own expanded name is now available
        # (its namespace is decoded at the adapter boundary), so both sides can
        # state the same thing.
        axis_name, member_name = _qname(axis, member), _qname(value, member)
        if axis_name is None or member_name is None:
            return None
        spellings.append((axis, value))
        dims.append((axis_name, member_name))
    # ONE VALUE PER DIMENSION, and the dimension is the EXPANDED axis.
    #
    # XBRL Dimensions 1.0 §3.1.4.2: a context MUST NOT contain more than one
    # value for the same dimension — `xbrldie:RepeatedDimensionInInstanceError`.
    #   https://www.xbrl.org/specification/dimensions/per-2011-11-20/
    #   dimensions-per-2011-11-20.html
    #
    # Checked on the RESOLVED axis, because that is what a dimension IS. Two
    # members writing `srt:GeographicalAxis` and `s2:GeographicalAxis` with both
    # prefixes bound to one URI give the SAME axis two values, and a uniqueness
    # test on the spelling sees two different axes and lets it through.
    if len({axis for axis, _member in dims}) != len(dims):
        return None
    # THE RAW LEAF TEXT reaches the strict dateUnion parser. `_text()`
    # collapses UNICODE whitespace and deletes zero-width characters, so an
    # NBSP- or ZWSP-padded date was normalised into a clean one before the
    # parser could refuse it. The parser strips XML whitespace itself.
    return {'period': ('', _leaf(inst[0])) if inst else
                      (_leaf(start[0]), _leaf(end[0])) if start else ('', ''),
            # `dims` KEEPS ITS ORIGINAL MEANING — the written spellings, which
            # the frozen product output publishes unchanged. Identity moved to
            # its own field instead of being smuggled into this one, so no
            # consumer silently changed shape.
            'dims': tuple(sorted(spellings)),
            'dims_expanded': tuple(sorted(dims)),
            'typed': bool(typed),
            # LAWFUL OPEN CONTENT, carried out truthfully. The caller
            # names the refusal; this parser never drops the content,
            # because dropping it would merge two distinct contexts.
            'non_xdt': non_xdt,
            'entity': cik}


def _parse_unit(u):
    """The XBRL 2.1 §4.8 unit shape, or None: EITHER direct measures OR exactly
    one divide with one numerator and one denominator.

    CONTAINERS ARE COUNTED, MEASURES ARE NOT. A container may lawfully carry
    several measures — a compound unit — and those must keep binding; refusing
    them is the classifier's job downstream, never the parser's.
    """
    I = XBRL_INSTANCE_NAMESPACE
    divides = _kids(u, I, 'divide')
    plain = _kids(u, I, 'measure')
    if len(divides) > 1 or (divides and plain) or not (divides or plain):
        return None
    n_meas = d_meas = []
    if divides:
        nums = _kids(divides[0], I, 'unitNumerator')
        dens = _kids(divides[0], I, 'unitDenominator')
        if len(nums) != 1 or len(dens) != 1:
            return None
        n_meas = _kids(nums[0], I, 'measure')
        d_meas = _kids(dens[0], I, 'measure')
        if not n_meas or not d_meas:
            return None
        if not _ordered(divides[0], (I, 'unitNumerator'), (I, 'unitDenominator')):
            return None
        # UNKNOWN CHILDREN INSIDE THE RATIO ITSELF. The unit's own children
        # were checked; the divide's were not, so anything could ride inside.
        if not _only(divides[0], (I, 'unitNumerator'), (I, 'unitDenominator')):
            return None
        if any(not _only(side, (I, 'measure')) for side in (nums[0], dens[0])):
            return None
        num, den = (tuple(_measure_text(m) for m in n_meas),
                    tuple(_measure_text(m) for m in d_meas))
        # A MEASURE ON BOTH SIDES cancels. Comparing whole TUPLES only caught
        # the exact `USD/USD` case, so `USD·shares / shares` — which is USD
        # wearing a fake ratio — passed. The test is OVERLAP, and it is taken on
        # the EXPANDED names: two prefixes may lawfully alias ONE namespace, so
        # `iso4217:USD` over `cur:USD` is the same measure on both sides wearing
        # different spellings, and comparing the raw strings could not see it.
        # That ratio cancels to nothing and would attach a fabricated unit.
        if (set(_qname(_measure_text(m), m) for m in n_meas)
                & set(_qname(_measure_text(m), m) for m in d_meas)):
            return None
    else:
        num = den = ()
    # NO CONTAINMENT COUNT HERE, and its absence is proven rather than assumed
    # (#827 round 7b, owner ruling). A unit's own subtree is closed by the
    # direct-children rules above: a unit may hold only measures or a divide, a
    # divide only its two sides, each side only measures — and every measure
    # must be a LEAF, so nothing can nest below one. There is nowhere left for
    # a stray element of ours to hide, which is why the `_all`-vs-`placed`
    # count could no longer fail: probed with it disabled, NINE stray
    # placements (a measure between the two sides, a numerator inside a
    # numerator, a divide inside a numerator, a denominator and a measure
    # inside a measure, a numerator beside a plain measure, and measures,
    # divides and numerators under `<div>` wrappers at two depths) were ALL
    # still refused, none of them by the count.
    #
    # THE CONTEXT VERSION IS NOT REDUNDANT AND STAYS: a `typedMember` carries
    # arbitrary value markup, so an explicitMember, a period or an identifier
    # really can hide inside one — measured, three such cases are caught by
    # that count ALONE.
    if not _only(u, (I, 'measure'), (I, 'divide')):
        return None
    measures = _all(u, I, 'measure')
    if any(_leaf(m) is None for m in measures):
        return None
    # A MEASURE IS A QNAME — `xsd:QName`, per XBRL 2.1 §4.8.2 as CORRECTED by
    # the errata to 2013-02-20 (Appendix D erratum 62, which removed the older
    # redundant wording). So the rule is resolvability, NOT the presence of a
    # colon: `notaprefix:USD` names nothing because no declaration binds that
    # prefix, while an UNPREFIXED value is lawful wherever a default namespace
    # is in scope and names nothing only when none is. `_qname` applies exactly
    # that, so both cases fall out of one rule and neither is special-cased.
    if any(_qname(_measure_text(m), m) is None for m in measures):
        return None
    # THE SHAPE LAW, from the SAME owner the context grammar uses (#827 B16).
    # The structural gates above say which elements may appear and where; this
    # says what each of them may CARRY — its xsi:type, its attributes and its
    # declared character content — against the pinned instance schema.
    for el, name in ((u, 'unit'),
                     *((d, 'divide') for d in divides),
                     *((s, 'unitNumerator') for s in
                       (_kids(divides[0], I, 'unitNumerator') if divides else ())),
                     *((s, 'unitDenominator') for s in
                       (_kids(divides[0], I, 'unitDenominator') if divides else ())),
                     *((m, 'measure') for m in measures)):
        verdict = _shape(el, name)
        if verdict == 'malformed':
            return None
        if verdict == 'unsupported':           # the string IS the reason — the
            return UNSUPPORTED_UNIT_TYPE       # caller stores it verbatim
    # THE GRAPH'S OWN SPELLING, computed HERE because this is the only place the
    # namespaces are known. The graph drops the prefix of a measure in the
    # INSTANCE namespace and keeps every other measure exactly as written. That
    # is a rule about the NAMESPACE, not about the five letters `xbrli`: a
    # filing that lawfully binds the instance namespace to `i:` writes
    # `i:shares`, which is the same measure and must reach the graph as
    # `shares`. Matching the literal prefix threw such a filing away.
    return {'measures': num + den if divides else tuple(_measure_text(m)
                                                       for m in plain),
            'is_divide': bool(divides), 'numerator': num, 'denominator': den,
            'graph_numerator': tuple(_graph_measure(m) for m in n_meas),
            'graph_denominator': tuple(_graph_measure(m) for m in d_meas),
            'graph_measures': tuple(_graph_measure(m) for m in plain),
            # THE SEMANTIC IDENTITIES — (namespace URI, local name) per measure,
            # resolved where each measure is written. THESE are what a unit
            # policy must read. The graph cannot supply them: `Unit.namespace`
            # is the Unit Type Registry's `nsUnit`, absent for every divide unit
            # and for 6,752 unregistered simple units, and `Unit.name` is a
            # prefixed string that is concatenated for divides. The filing
            # declares the unit unambiguously, so once the fact and unitRef
            # joins are proven the FILING is the authority on what it means.
            'expanded_numerator': tuple(_qname(_measure_text(m), m)
                                        for m in n_meas),
            'expanded_denominator': tuple(_qname(_measure_text(m), m)
                                          for m in d_meas),
            'expanded_measures': tuple(_qname(_measure_text(m), m)
                                       for m in plain)}


def _graph_measure(m):
    """One measure in the GRAPH's spelling: the INSTANCE namespace's prefix
    dropped, every other measure kept exactly as the filing wrote it.

    Raw spelling is preserved deliberately — the graph stores prefixed measure
    names and this value is compared against them, which is the one place the
    contract requires the text rather than the identity.
    """
    raw = _measure_text(m)
    resolved = _qname(raw, m)
    # THE LOCAL NAME, not "the text after a colon". Those coincide only when the
    # value happens to be written with a prefix. An unprefixed value resolved
    # through an in-scope DEFAULT namespace has no colon at all, so slicing
    # produced the EMPTY STRING and every such fact refused as
    # `unit_name_not_the_filings_measure` — a lawful filing rejected by a rule
    # about punctuation. The resolver already knows the local name; it is asked
    # for it here rather than re-derived from the spelling.
    return (resolved[1]
            if resolved is not None
            and resolved[0] == XBRL_INSTANCE_NAMESPACE else raw)


#: One inline fact seen through BOTH views at once. `sem` is the strict XML
#: element and owns IDENTITY — its expanded name and the namespaces in scope
#: where it is written. `ren` is the renderer node and owns APPEARANCE — the
#: visible text, its row, its table, its offsets. Pairing them here, once and
#: only when the two views provably agree, is what stops either from quietly
#: answering the other's question.
_Fact = collections.namedtuple('_Fact', 'sem ren')

#: The bridge's own refusal. The two views read the SAME bytes, so they should
#: describe the same facts in the same order; when they do not, this parser
#: cannot say which node shows which number and abstains for the document.
VIEWS_DISAGREE = 'semantic and renderer views disagree'


#: THE ATTRIBUTES WHOSE DECLARED TYPE COLLAPSES WHITESPACE. The Inline XBRL 1.1
#: schema (`xhtml-inlinexbrl-1_1-definitions.xsd`) declares `id` as xs:NCName,
#: `contextRef`/`unitRef` as restrictions of xs:NCName, `name`/`format` as
#: xs:QName and `scale` as xs:integer; XBRL 2.1 declares a context's and a
#: unit's `id` as xs:ID, a measure's and an explicitMember's content and its
#: `dimension` as xs:QName, an identifier's content as xs:token and its
#: `scheme` as a restricted xs:anyURI.
#:
#: These do NOT all derive from xs:token — xs:ID and xs:NCName do, xs:QName,
#: xs:integer and xs:anyURI do not. What they share is the FACET: each one
#: independently carries whiteSpace=COLLAPSE (XML Schema Part 2 §4.3.6), so XML
#: whitespace around such a value carries no meaning and a schema-aware reader
#: never sees it. Refusing a padded id was OUR rule, not the standard's.
#:
#: `sign` is deliberately ABSENT: it restricts xs:string, which PRESERVES
#: whitespace, so ' -' is not '-' and must not be made into it.
#: EVERY collapse-faceted ATTRIBUTE this module reads, in one place. Two of
#: them used to call `_collapse` directly instead of going through `_typed`,
#: which meant there were two ways to declare "this value collapses" and this
#: set was silently incomplete — the exact drift a two-way coverage check
#: exists to catch. Element CONTENT (a measure, a member, an identifier) is not
#: an attribute and is read by `_leaf`, so it collapses at its own reader.
_COLLAPSED = frozenset({'id', 'name', 'contextRef', 'unitRef', 'format',
                        'scale', 'dimension', 'scheme',
                        # THE NIL FLAG. `xsi:nil` is `xs:boolean`, which really
                        # does collapse, so ` true ` IS `true`.
                        #
                        # `decimals` and `precision` ARE NOT HERE, and the
                        # comment that used to put them here was half right.
                        # They are UNIONS: `xbrli:decimalsType` over
                        # `xs:integer` and a restriction of **`xs:string`**
                        # enumerated `INF` (`precisionType` the same over
                        # `xs:nonNegativeInteger`). A union has no single
                        # whitespace facet — the member that validates the
                        # value carries it — and `xs:string` PRESERVES, for the
                        # same reason `sign` is excluded above. Collapsing the
                        # whole union turned the malformed ` INF ` into the
                        # value `INF`. Their one reader, `_accuracy_ok`, now
                        # takes the raw spelling and applies the right facet per
                        # member.
                        _clark(_XSI_NS, 'nil')})


#: XML 1.0 3e §3.3.3 / XSD P2 §4.3.6 step one: each #x9, #xA and #xD becomes
#: a space. Consumed ONLY by `_collapse` below — the VALUE-side law. (The
#: renderer-pairing copy of this normalization died with the deleted
#: fingerprint, SEQ 264 §2d; this one reads what values MEAN and stays.)
_ATTR_WS = str.maketrans('\t\r\n', '   ')


def _collapse(value):
    """XML Schema Part 2 §4.3.6 whiteSpace=COLLAPSE, and nothing more.

    ONLY the four characters XML calls space are touched. Python's own
    `.split()` would also eat U+00A0, U+000B, U+000C and U+3000 — characters
    XML does not call space at all — and a value padded with those is NOT
    padded: it is a different value, and it must stay one.
    """
    return ' '.join(part for part in value.translate(_ATTR_WS).split(' ')
                    if part)


def _typed(el, name):
    """One attribute of `el`, read as its DECLARED SCHEMA TYPE, or None.

    THE ONE PLACE the schema's whitespace facet is applied, and EVERY attribute
    is read through it — including the ones whose type preserves whitespace. A
    value that skipped this reader would be protected only by the absence of a
    line of code, which no test can hold onto; routed through it, `_COLLAPSED`
    becomes the single declaration of which types collapse, and getting that
    set wrong is a change a control can catch.

    It reads what the VALUE means, and no pairing normalization is ever
    mixed in — so a normalization meant for comparing two parsers' spellings
    (the deleted fingerprint's job) can never quietly change a fact's
    content.
    """
    value = el.get(name)
    if value is None:
        return None
    return _collapse(value) if name in _COLLAPSED else value


def _lexical(el):
    """How the DOCUMENT spelled this element's name, as HTML would hold it.

    NOT an identity and never used as one. The strict view has already decided,
    by expanded name, which elements these are; this is only the handle needed
    to ask the renderer for the same source nodes, because HTML has no
    namespaces and offers no other. It is read off each element the strict view
    selected — so a filing that binds Inline XBRL to `i:` is asked for `i:` —
    and no prefix is ever assumed, listed or preferred.
    """
    q = etree.QName(el)
    return ('%s:%s' % (el.prefix, q.localname) if el.prefix
            else q.localname).lower()


def _resources(root):
    """Every `ix:resources` this report declares — and only those.

    Inline XBRL 1.1 (Recommendation 2013-11-18) §14.1 fixes the content of
    `ix:resources` to the named resource children, `xbrli:context` and
    `xbrli:unit` among them, and §14.1.1 requires `ix:resources` to be a CHILD
    of `ix:header`. So the ancestry is the rule, not the tag name: an element
    spelled `ix:resources` sitting anywhere else is not this report's resources
    container, and a context or unit outside one is not a declaration the report
    makes.

    Reading them from the whole document — which is what a descendant scan does
    — meant a context buried in a `<div>`, or inside `ix:hidden` (a container
    for FACT markup, not for resources), was indexed and bound exactly like a
    real one. This is a rule about WHERE THIS PARSER LOOKS, not a validator: it
    checks the two links the spec names and nothing else.
    """
    return [r for h in root.iter(_clark(_INLINE_NS, 'header'))
            for r in _children(h) if _is(r, _INLINE_NS, 'resources')]


def _kids_of(parents, uri, local):
    """The named DIRECT children of each container, in document order."""
    return [k for p in parents for k in _kids(p, uri, local)]


def _align_views(root, soup, names):
    """{(uri, local): (strict elements, renderer nodes)} in source order, or None.

    THE ALIGNMENT IS BY SOURCE POSITION, NOT BY NAME LOOKUP. For each spelling
    the document uses, EVERY strict element carrying it is counted — whatever
    namespace it resolves to — and the renderer must report the same total for
    that spelling. A selected element is then paired with the renderer node at
    its own ordinal among them.

    Counting the unselected ones is the whole point. A report may lawfully hold
    a real Inline XBRL element AND an unrelated element spelled the same way,
    under a prefix rebound locally to another namespace. Counting only the real
    ones would find a surplus in the renderer and refuse a lawful filing;
    counting all of them lines the two parses up exactly, and the impostor is
    simply never selected — it is not one of these names.

    The spelling is a SOURCE HANDLE ONLY, used to align two parses of one set of
    bytes because HTML offers nothing else. It decides nothing: which elements
    matter is settled entirely by expanded name in the strict tree.
    """
    picked = {name: [] for name in names}
    totals = {}
    for el in root.iter():
        if not isinstance(el.tag, str):          # comments and PIs are not it
            continue
        spelling = _lexical(el)
        ordinal = totals.get(spelling, 0)
        totals[spelling] = ordinal + 1
        for name in names:
            if _is(el, *name):
                picked[name].append((spelling, ordinal, el))
                break
    seen, out = {}, {}
    for name, rows in picked.items():
        sem, ren = [], []
        for spelling, ordinal, el in rows:
            if spelling not in seen:
                found = soup.find_all(spelling)
                if len(found) != totals[spelling]:
                    return None          # the two views disagree about what is
                seen[spelling] = found   # there; no pairing can be trusted
            sem.append(el)
            ren.append(seen[spelling][ordinal])
        out[name] = (sem, ren)
    return out


def _bridge(sem_facts, ren_facts):
    """Pair semantic facts with renderer nodes, or None to abstain.

    THIS IS SOURCE-ORDER ALIGNMENT — not a key lookup, and the invariant
    is stated once, honestly: for the DECLARED parser stack, strict and
    renderer traversal preserve the tested per-spelling source order, and
    the per-spelling totals plus the length check below fail CLOSED on
    any count divergence. Nothing is ever paired by a prefix or by page
    text, and no attribute fingerprint exists here.

    WHAT THIS DELIBERATELY DOES NOT DO is refuse the document when two
    facts are indistinguishable. Such a pair does not need to be told
    apart here: two facts sharing an id give `duplicate_id` at the id
    door, two id-less facts sharing an identity give `ambiguous_identity`
    at the fallback — truthful per-fact reasons, not one blunt one.
    """
    if len(sem_facts) != len(ren_facts):
        return None
    return [_Fact(sem, ren) for sem, ren in zip(sem_facts, ren_facts)]


def prepare(html_text):
    """Parse and index a display filing EXACTLY ONCE — memoized by content sha so
    repeated locate() calls (one per anchor) share ONE parse per filing.

    TWO VIEWS, each with one job. A document that is not well-formed XML, or
    whose two views disagree, comes back as a refusal dict that every public
    door turns into one truthful reason — no parser exception ever escapes.
    """
    sha = sha256_text(html_text)
    hit = _PREP_CACHE.get(sha)
    if hit is not None:
        return hit
    try:
        root = _semantic_parse(html_text)
    except SemanticParseError as exc:
        return _remember(sha, {'refused': str(exc), 'sha': sha})
    soup = _soup(html_text)
    id_counts = {}
    for el in root.iter():
        eid = _typed(el, 'id') if isinstance(el.tag, str) else None
        if eid is not None:
            id_counts[eid] = id_counts.get(eid, 0) + 1
    # RESOURCES COME FROM ONE PLACE, because the spec puts them in one place.
    declared = _resources(root)
    contexts = {}
    for context in _kids_of(declared, XBRL_INSTANCE_NAMESPACE, 'context'):
        cid = _xml_id(_typed(context, 'id'))
        if not cid:
            continue
        # THE POISON CARRIES ITS OWN REASON. Both refusals used to be the same
        # bare `None`, so the consumer reported malformed structure as a
        # REPEATED ID — a safe abstention under a false name, and no
        # outcome-only test could ever see the lie. The value IS the reason: a
        # string means refused-and-why, a dict means usable evidence.
        if cid in contexts:              # a duplicated context id is AMBIGUOUS
            contexts[cid] = 'duplicate_context_id'   # evidence; last-wins had
            continue                                 # silently picked one
        parsed = _parse_context(context)
        contexts[cid] = 'malformed_context_structure' if parsed is None else parsed
    units = {}
    for u in _kids_of(declared, XBRL_INSTANCE_NAMESPACE, 'unit'):
        uid = _xml_id(_typed(u, 'id'))
        if not uid:
            continue
        if uid in units:                 # a duplicated unit id is AMBIGUOUS
            units[uid] = 'duplicate_unit_id'         # evidence exactly as a
            continue                                 # duplicated context is
        parsed = _parse_unit(u)
        units[uid] = 'malformed_unit_structure' if parsed is None else parsed
    # THE BRIDGE, in ONE aligned pass. The strict view selects BY EXPANDED NAME —
    # facts, and the containers whose content is not rendered — and the renderer
    # nodes are then taken at the matching source positions. An element merely
    # SPELLED like a fact or a hidden container, but bound to another namespace,
    # is counted for alignment and selected as neither.
    aligned = _align_views(root, soup, ((_INLINE_NS, 'nonFraction'),
                                        (_INLINE_NS, 'hidden')))
    facts = None
    if aligned is not None:
        facts = _bridge(*aligned[(_INLINE_NS, 'nonFraction')])
        ren_hidden = aligned[(_INLINE_NS, 'hidden')][1]
    if facts is None:
        return _remember(sha, {'refused': VIEWS_DISAGREE, 'sha': sha})
    elements = {}
    noid_elements = []
    for fact in facts:
        eid = element_id(fact)           # xs:NCName — the collapsed value, and
        if eid:                          # the SAME key `id_counts` is built on
            elements.setdefault(eid, fact)
        else:
            noid_elements.append(fact)       # null-graph-id facts live HERE
    node_spans = {}
    hidden_nodes = frozenset(id(n) for n in ren_hidden)
    # THE BRIDGED RENDERER NODES, by identity. Every later question of the form
    # "is this rendered thing a fact / hidden?" is answered from these, never by
    # re-inspecting the renderer tree, which cannot tell.
    fact_nodes = frozenset(id(f.ren) for f in facts)
    # THE FALLBACK OWNERS, from the consumer itself. `_evidence_owner` names the
    # node whose span each fact's evidence will read; the ones that are not
    # already a `_SPAN_TAGS` tag are the third branch, and without them that
    # fact has no span and `source_evidence` refuses it. Measured over the
    # frozen manifest: 0 facts reach that branch, so this adds 0 of 23,423,401
    # spans there — the cost belongs to documents the corpus has not seen.
    fallback_owners = frozenset(
        id(owner) for owner in
        (_evidence_owner(f.ren)[1] for f in facts)
        if owner is not None and getattr(owner, 'name', '') not in _SPAN_TAGS)
    style_flags = []
    text = _visible_walk(soup, node_spans, hidden_nodes, fallback_owners,
                         style_flags)
    if style_flags:
        # ONE truthful document-level refusal (SEQ 231 §3): an unresolvable
        # inline-style winner anywhere makes every visibility claim in this
        # filing a guess, so nothing in it may bind or quote.
        return _remember(sha, {'refused': 'unsupported_style: '
                               + style_flags[0], 'sha': sha})
    # TWO PROVEN-DEAD OUTPUTS REMOVED (#827 round 5): `raw_sha` was the same
    # value as `sha` under a second name, and `soup` held the whole parse tree
    # alive in a memoized cache. Exhaustive grep: no reader anywhere.
    prepared = {'ids': id_counts, 'contexts': contexts,
                'node_spans': node_spans, 'hidden_nodes': hidden_nodes,
                'fact_nodes': fact_nodes,
                'units': units, 'elements': elements,
                'noid_elements': noid_elements,
                'sha': sha,
                'text': text,               # THE representation (visible text)
                'text_sha': hashlib.sha256(text.encode('utf-8',
                                           'surrogatepass')).hexdigest()}
    return _remember(sha, prepared)


def _remember(sha, prepared):
    """Memoize by content sha. A REFUSAL is remembered exactly like a reading:
    re-parsing an unreadable document cannot make it readable, and the refusal
    is the cheap, stable answer every later call must get."""
    while len(_PREP_CACHE) >= 4:
        _PREP_CACHE.pop(next(iter(_PREP_CACHE)))
    _PREP_CACHE[sha] = prepared
    return prepared


def _prepared(doc_or_html):
    return doc_or_html if isinstance(doc_or_html, dict) else prepare(doc_or_html)


def element_id(fact):
    """A bridged fact's own id as the SCHEMA declares it, or ''.

    Public because the locator needs it and must not reach into the pair to
    read a raw attribute: `id` is xs:NCName, so its value is the collapsed one,
    and one reader means the binder and the locator cannot drift into two
    different ideas of what a fact's id is.
    """
    return _typed(fact.sem, 'id') or ''


def refused(prepared):
    """The reason this document could not be read, or None when it was.

    ONE state, checked at every public door, so an unreadable filing is answered
    the same truthful way everywhere instead of raising a parser exception out
    of whichever door happened to be called first.
    """
    return prepared.get('refused') if isinstance(prepared, dict) else None


def _evidence_from(fact, prepared):
    """Evidence for ONE bridged fact.

    `fact.sem` answers WHAT the fact is — its name, the context and unit it
    refers to, its scale and sign — because those are XML names and values that
    only the strict view spells correctly. `fact.ren` answers HOW it appears —
    its displayed text, its row, its table, its offsets — because that is a
    question about the rendered page. Neither is ever asked the other's half.
    """
    el, node = fact.sem, fact.ren
    # A CONCEPT IS A QNAME, and nothing validated it. The door only compared
    # the document's `name` string to the graph's `concept` string, so the two
    # merely had to agree on the same junk — `Revenues` with no prefix at all,
    # and `zz:Revenues` naming a namespace this document never declared, both
    # bound as readily as the real name. THE ONE FUNNEL: the exact-id path and
    # the identity-fallback path both end here, so one check covers both.
    if _qname(_typed(el, 'name'), el) is None:
        return None, 'malformed_concept_name'
    # A REQUIRED REFERENCE HAS EXACTLY THREE FAILING STATES, and each gets its
    # own name because each needs a different fix:
    #   ABSENT            the fact states no reference at all
    #   PRESENT, UNLAWFUL not a reference — `contextRef` is a restriction of
    #                     xs:NCName, and `c 1` or `` is not one
    #   LAWFUL, UNMATCHED a reference this filing never declared
    # Collapsing the first two into one reason ("missing") said the attribute
    # was absent when it was there and wrong; collapsing the last two said the
    # FILING lacked a context when the fault was in the MARKUP.
    ctx_ref = _typed(el, 'contextRef')
    if ctx_ref is None:
        return None, 'missing_context_ref'
    if _xml_id(ctx_ref) is None:
        return None, 'malformed_context_ref'
    # A STRING IS THE REFUSAL AND ITS REASON; a dict is usable evidence; absent
    # is a context this filing never declared. Three states, one lookup — the
    # old pair of tests reported every poisoned context as a duplicated id.
    ctx = prepared['contexts'].get(ctx_ref)
    if isinstance(ctx, str):
        return None, ctx
    if ctx is None:
        return None, 'undefined_context'
    if ctx['typed']:
        return None, 'typed_dimensions_unsupported'
    # LAWFUL, AND STILL UNREPRESENTABLE. `segment`/`scenario` are open content
    # (XBRL 2.1; Dimensions 1.0 §3.1.4.4), so a company element beside the
    # dimensions is valid markup this product cannot yet carry. It refuses —
    # ignoring it would merge two genuinely different contexts — but it says
    # the true thing rather than calling the filer's markup malformed.
    if ctx['non_xdt']:
        return None, 'unsupported_non_xdt_context'
    # `unitRef` IS REQUIRED on a numeric fact, and the same three states apply
    # as to `contextRef`: absent is a missing reference, unlawful is not a
    # reference at all, and lawful-but-unmatched is one the filing never
    # declared. Treating absence as "no unit" let a numeric fact bind with no
    # statement of what its number measures.
    #
    # THE RULE COMES FROM THE SCHEMA, not from the corpus. Inline XBRL 1.1,
    # `xhtml-inlinexbrl-1_1-definitions.xsd`, declares `unitRef` on the
    # `ix:nonFraction` element as REQUIRED (a restriction of xs:NCName) — that
    # is what makes it required here. The measurement below says only what the
    # change COSTS, and is a sample, stated as one: across 300 files of the
    # frozen cache, 0 of 458,986 ix:nonFraction elements were missing or blank
    # on `unitRef`. A census can never establish a requirement; it can only
    # price one.
    unit_ref = _typed(el, 'unitRef')
    if unit_ref is None:                     # the same three states, by name
        return None, 'missing_unit_ref'
    if _xml_id(unit_ref) is None:
        return None, 'malformed_unit_ref'
    unit = prepared['units'].get(unit_ref)
    if unit is None:
        return None, 'undefined_unit'
    if isinstance(unit, str):                # refused; the string says why
        return None, unit
    # OPTIONAL MEANS ABSENT OR LAWFUL — never "present and empty".
    #
    # The Inline XBRL 1.1 schema declares `sign` as a restriction of xs:string
    # whose pattern is exactly `-`, and `format` as xs:QName. Both are OPTIONAL:
    # no `sign` is the positive case and no `format` means no transform. But an
    # attribute that IS present must satisfy its type, and `sign=""` satisfies
    # nothing — it is neither absent nor `-`. Accepting it let a fixture state a
    # sign it did not have, and let a document assert a transform by a name that
    # resolves to nothing.
    raw_sign = _typed(el, 'sign')
    if raw_sign is not None and raw_sign != '-':
        return None, 'malformed_sign'
    raw_format = _typed(el, 'format')
    if raw_format is not None and _qname(raw_format, el) is None:
        return None, MALFORMED_FORMAT
    raw_scale = _typed(el, 'scale')
    # ABSENT means 0 (the spec default); PRESENT means it must parse as an XML
    # integer — `''`, `6.9`, `1_0` and full-width digits are malformed markup.
    scale = 0 if raw_scale is None else xml_integer(raw_scale)
    if scale is None:
        return None, 'malformed_scale'
    # HIDDEN IS TWO DIFFERENT QUESTIONS. `ix:hidden` is a SEMANTIC container —
    # an expanded name, asked of the strict view. CSS is a RENDERING instruction
    # and is asked of the renderer. Neither view can answer both.
    # THE VALUE COMES FROM THE FACT, not from the page. One reader, at the one
    # boundary both binding paths already funnel through, so neither the binder
    # nor the locator can reconcile against rendered characters again.
    value_input, why_value = fact_value_input(el)
    if value_input is None:
        return None, why_value
    css_hidden, unsup = _effective_hidden(node)
    if unsup is not None:
        # THE ONE TRUTHFUL UNSUPPORTED LANE (SEQ 227/229): a winning value the
        # inline reader cannot resolve must never be guessed visible or hidden
        # for a FACT — the fact refuses with the named reason and parks.
        return None, 'unsupported_style'
    hidden = any(_is(a, _INLINE_NS, 'hidden') for a in el.iterancestors()) \
        or css_hidden
    veiled = prepared.get('hidden_nodes', frozenset())
    numeric = prepared.get('fact_nodes', frozenset())
    ev = {
        'name': _typed(el, 'name') or '',
        # THE CONCEPT'S SEMANTIC IDENTITY, resolved in the scope of the fact
        # element that writes it. The raw text is kept beside it because the
        # graph stores a prefixed string; the identity is what may be compared.
        'name_expanded': _qname(_typed(el, 'name'), el),
        # TWO STRINGS, TWO JOBS, and they must never be swapped again.
        # `value_input` is the fact's own content and is what reconciliation
        # transforms; `displayed` is how the page renders and is only ever
        # quoted back as evidence.
        'value_input': value_input,
        'displayed': _text(node, veiled),
        'scale': scale,
        'sign': raw_sign or '',
        # TWO FIELDS, TWO JOBS. `fmt` is the filing's own spelling and stays
        # exactly as written for evidence and product output; `fmt_expanded` is
        # the (namespace URI, local name) identity, and it is the ONLY thing any
        # semantic decision may read.
        #
        # THERE IS NO THIRD FIELD. A `fmt_raw` sat here to keep ABSENT
        # distinguishable from present — but this record only exists once the
        # boundary has already refused every present-and-malformed `format`, so
        # `fmt_expanded is None` can only mean ABSENT. The extra field was
        # duplicate state, and its job was to let a caller pass a raw string
        # where an identity belongs.
        'fmt': raw_format or '',
        'fmt_expanded': None if raw_format is None else _qname(raw_format, el),
        'unit_ref': unit_ref,
        'context_ref': ctx_ref,
        'period': ctx['period'],
        # BOTH VIEWS TRAVEL TOGETHER, exactly as `name`/`name_expanded` do:
        # the written spellings for the product output, the expanded pairs for
        # every comparison. Carrying only one would force some consumer to
        # re-derive the other from a prefix it cannot resolve here.
        'dims': ctx['dims'],
        'dims_expanded': ctx['dims_expanded'],
        'entity': ctx.get('entity', ''),
        'hidden': hidden,
        'in_table': False,
        'row_span': None,
        'block_span': None,
        'row_text': '',
        'row_cells': [],
        'row_label': '',
        'row_label_span': None,
        'columns': [],
        'column_spans': [],
        'section': '',
        'section_span': None,
        'block': '',
    }
    # ONE call decides row-vs-block AND names the owner whose span is read, so
    # the walker and this reader can never disagree about which node that is.
    in_table, owner = _evidence_owner(node)
    if in_table:
        row = owner
        cell = node.find_parent(_CELL_TAGS)   # the cell, for table detail only
        ev['in_table'] = True
        ev['row_text'] = _text(row, veiled)
        ev['row_span'] = prepared.get('node_spans', {}).get(id(row))
        cells = row.find_all(_CELL_TAGS, recursive=False)
        # THE WALK OWNS VISIBILITY (#827 E). A cell hidden by inheritance, or
        # revived by a descendant visibility:visible, is answered by its own
        # representation slice — a per-cell standalone test here would both
        # leak and drop revived text. Pruned cells simply have no span.
        ev['row_cells'] = [_visible_slice(item, prepared)[0] for item in cells]
        fact_cell = _index_by_identity(cells, cell)
        if fact_cell is not None:
            # SELECT ON VISIBLE TEXT, and take the value and the span from the
            # SAME cell. Selecting on `_text` let a cell whose only content is
            # hidden become the label — a label that appears nowhere in the
            # filing, carrying a span that covers nothing. `find()` stays
            # deleted: the chosen cell already knows its own extent.
            left = [item for item in cells[:fact_cell]
                    if _words(_visible_slice(item, prepared)[0])]
            if left:                                     # digits in labels LEGAL
                ev['row_label'], ev['row_label_span'] = \
                    _visible_slice(left[0], prepared)
        table = row.find_parent('table')
        if table is not None:
            table_rows = [r for r in table.find_all(_ROW_TAG)
                          if r.find_parent('table') is table]
            row_number = _index_by_identity(table_rows, row)
            if row_number is not None and fact_cell is not None:
                col_pairs = _aligned_columns(table_rows, row_number, cell,
                                             prepared)
                ev['columns'] = [c for c, _ in col_pairs]
                ev['column_spans'] = [sp for _, sp in col_pairs]
                for prior in reversed(table_rows[:row_number]):
                    prior_cells = prior.find_all(_CELL_TAGS, recursive=False)
                    # ONE eligible list decides BOTH the text and the span. They
                    # were chosen by two DIFFERENT filters — the text skipped
                    # digit-bearing cells and the span did not — so a row like
                    # "Q1 2023 | Segment detail" reported one cell's words at
                    # the other cell's offsets.
                    eligible = [(t, sp) for t, sp in
                                (_visible_slice(item, prepared)
                                 for item in prior_cells)
                                if _words(t) and not re.search(r'\d', t)]
                    first = (_visible_slice(prior_cells[0], prepared)[0]
                             if prior_cells else '')
                    if prior_cells and not _has_number_fact(prior, numeric) \
                            and first and len(eligible) == 1 \
                            and not _after_edge_markers(
                                eligible[0][0]).startswith('('):
                        # A parenthetical is not a heading. The test ran on the
                        # UNTRIMMED text, so a leading dash walked `— (Loss)`
                        # straight past it. Leading markers are ignored for THIS
                        # DECISION only — the stored text below is untouched.
                        # STORED EXACT. The trim lived here and made the section
                        # a prettified string beside an untrimmed span — the
                        # same defect as the headers, 133 of them corpus-wide.
                        ev['section'], ev['section_span'] = eligible[0]
                        break
    else:
        ev['block'] = _text(owner, veiled)
        ev['block_span'] = prepared.get('node_spans', {}).get(id(owner))
    return ev, 'ok'


def element_evidence(doc_or_html, element_id):
    """(evidence, 'ok') for the exact element carrying id=element_id, else
    (None, reason). Accepts a prepare()d document or raw HTML text."""
    # XML 1.0 S, not Python's Unicode set: a bare `.strip()` called an id of
    # U+00A0 blank, and blank here means "look me up by identity instead".
    prepared = _prepared(doc_or_html)
    if refused(prepared):
        return None, refused(prepared)
    if not element_id or not str(element_id).strip(XML_WS):
        return None, 'blank_id'
    # AN XML ID IS AN NCName, and this is the ONE door both consumers use —
    # the binder and the locator — so the rule lives here rather than being
    # written twice. Contexts and units have been held to it since round 5;
    # the fact's own id never was, so `id="1 2"` and `id="a<b"` resolved and
    # bound through BOTH callers.
    if _xml_id(str(element_id)) is None:
        return None, 'malformed_id'
    count = prepared['ids'].get(element_id, 0)
    if count == 0:
        return None, 'id_not_found'
    if count > 1:
        return None, 'duplicate_id'
    el = prepared['elements'].get(element_id)
    if el is None:
        return None, 'unsupported_element_kind'
    return _evidence_from(el, prepared)


def graph_concept_target(concept_key, concept_namespace, graph_concept_qname):
    """THE graph Concept record as ONE expanded name, or None when it cannot be
    trusted. The single owner both the binder and the locator earn their target
    from — written once so the two cannot drift into different rules.

    A concept is a QName: what identifies it is (namespace URI, local name), and
    the prefix is only an alias the filing chose. `concept_key` is the concept
    the caller is asking about; the Concept record's OWN qname must agree with
    it exactly before either half is trusted, because combining a namespace from
    one record with a local part taken from somewhere else would assert an
    expanded name that no single source ever made.

    Returns None — never a guess — when the identity is missing, unusable, or
    disagrees. The caller turns that into a truthful refusal.
    """
    if not isinstance(concept_namespace, str) or not concept_namespace.strip():
        return None
    if not isinstance(graph_concept_qname, str) or not graph_concept_qname.strip():
        return None
    if graph_concept_qname != concept_key:
        return None
    local = graph_qname_parts(graph_concept_qname)
    if local is None:
        return None
    return (concept_namespace, local)


def one_concept_target(concept_key, records):
    """The ONE target a set of graph Concept records agrees on, or None.

    Identical records may collapse — the same fact read twice is not a conflict.
    DISAGREEMENT MUST PARK: silently taking the first of several disagreeing
    Concept identities would let row order decide what a fact means.
    """
    targets = {graph_concept_target(concept_key, ns, qn)
               for ns, qn in records}
    if len(targets) != 1:
        return None                      # none usable, or they disagree
    return targets.pop()                 # may itself be None -> refuse


def identity_fallback(doc_or_html, target, context_ref, unit_ref):
    """Complete-identity fallback (FinalPlan §5A.3) — searches BOTH id-carrying and
    id-less elements (a null graph fact_id usually MEANS the element has no id).
    Returns (element, 'ok') only when exactly one matches.

    THE CONCEPT HALF IS AN EXPANDED NAME, not the prefixed text. `concept_target`
    is (namespace URI, local name), resolved once by the caller from the graph's
    own Concept record. Comparing the raw `name` attribute instead made the
    "complete identity" incomplete: a document may lawfully bind two prefixes to
    ONE taxonomy, and a fact written `gaap:Revenues` then failed to match a graph
    concept stored as `us-gaap:Revenues` even though they are the same concept —
    so a blank-id fact refused as `no_identity_match` while its exact-id twin
    bound. `contextRef` and `unitRef` stay EXACT: they are document-local IDREFs,
    not QNames, and nothing may normalise them.
    """
    prepared = _prepared(doc_or_html)
    if refused(prepared):
        return None, refused(prepared)
    pool = list(prepared['elements'].values()) + prepared['noid_elements']
    hits = [f for f in pool
            if _qname(_typed(f.sem, 'name'), f.sem) == target
            and (_typed(f.sem, 'contextRef') or '') == context_ref
            and (_typed(f.sem, 'unitRef') or '') == unit_ref]
    if not hits:
        return None, 'no_identity_match'
    if len(hits) > 1:
        return None, 'ambiguous_identity'
    return hits[0], 'ok'


def evidence_for_element(doc_or_html, fact):
    """Evidence for an already-bridged fact (the fallback path)."""
    prepared = _prepared(doc_or_html)
    if refused(prepared):
        return None, refused(prepared)
    return _evidence_from(fact, prepared)


def find_by_identity(doc_or_html, target, unit_ref):
    """Candidate ids by EXPANDED concept identity, for the same reason
    `identity_fallback` uses one: a prefix is an alias, so raw-name equality
    both misses a lawful second binding of one taxonomy and cannot tell two
    taxonomies apart. `unitRef` stays exact — it is a document-local IDREF."""
    prepared = _prepared(doc_or_html)
    if refused(prepared):
        return []            # an unreadable filing offers no candidates
    return [eid for eid, f in prepared['elements'].items()
            if _qname(_typed(f.sem, 'name'), f.sem) == target
            and (_typed(f.sem, 'unitRef') or '') == unit_ref]


# ---- exact Decimal reconciliation ----------------------------------------------

# EXACT ASCII, not `\d`: Python's `\d` matches every Unicode decimal digit and
# `Decimal()` accepts those too, so '７２６' and '٧٢٦' were read as 726 by a rule
# whose only job is the SOURCE's ASCII printed syntax (#827 finding 1, proven
# live before the fix). This validates syntax; it infers no meaning.
# ---------------------------------------------------------------------------
# THE OFFICIAL TRANSFORM REGISTRIES, and nothing else.
#
# `_NUM_DOT` and `_KNOWN_FMT` are GONE. They compared the raw text `ixt:...`,
# which is a prefix — an alias the FILING chooses — so they answered the wrong
# question in both directions, both reproduced through the public door:
#
#   a filing binding its own prefix to the OFFICIAL 2020 registry was REFUSED;
#   a filing binding `ixt` to a near-miss URI was ACCEPTED as an official
#   transform.
#
# ...and they hand-wrote a number grammar beside it, which is the transform
# registry's job, not ours.
#
# SEC EDGAR admits registries only through its release process. Release 26.1's
# machine-readable list names exactly these four; Arelle exposes SEVEN, and the
# extra three (2008, 2010, 2011, WGWD) are NOT admitted here merely because the
# library can reach them. No URI is case-repaired, slash-repaired or spelling-
# repaired: a near-miss is a different registry.
#
# Sources:
#   SEC EDGAR release 26.1 registry list
#   https://www.sec.gov/files/ixbrl-transform-registries.json
#   Inline XBRL 1.1 Part 1 §§10.1.2, 10.2.3, 16.1 — Recommendation 2013-11-18
#   with approved errata corrections to 2026-07-14 (the current edition)
#   https://www.xbrl.org/Specification/inlineXBRL-part1/REC-2013-11-18+errata-2026-07-14/inlineXBRL-part1-REC-2013-11-18+corrected-errata-2026-07-14.html
_TR3 = 'http://www.xbrl.org/inlineXBRL/transformation/2015-02-26'
_TR4 = 'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12'
_TR5 = 'http://www.xbrl.org/inlineXBRL/transformation/2022-02-16'
#: The SEC's OWN registry. Official and admitted by release 26.1, but stock
#: Arelle does not implement it — so a fact using it is lawful and unsupported,
#: which is a different and kinder statement than malformed.
_SEC_REGISTRY = 'http://www.sec.gov/inlineXBRL/transformation/2015-08-31'
#: The three whose transforms an implementation must supply.
_IMPLEMENTED_REGISTRIES = frozenset({_TR3, _TR4, _TR5})

MALFORMED_FORMAT = 'malformed_format'
UNSUPPORTED_TRANSFORM_REGISTRY = 'unsupported_transform_registry'
UNSUPPORTED_OFFICIAL_TRANSFORM = 'unsupported_official_transform'


def _ixt_registry(uri):
    """Arelle's function table for ONE approved registry, or None.

    Arelle owns the transform grammar and behaviour; this only asks it for the
    registry the FILING named. Imported lazily — `arelle` is a large package and
    the transform path is the only place in the driver that needs it.
    """
    from arelle import FunctionIxt
    return FunctionIxt.ixtNamespaceFunctions.get(uri)


def _ixt_refusal():
    """The transform API's DECLARED refusal type, with its translator armed.

    Arelle raises through `XPathContext`, whose `_` gettext name is unbound
    until something initialises it — so an invalid input surfaced as `NameError`
    rather than as the library's own refusal. Only that one hook is set, on the
    module: no process-wide `builtins` install, which would change behaviour for
    every other consumer in the process.
    """
    from arelle.formula import XPathContext
    if getattr(XPathContext, '_', None) is None:
        import gettext
        XPathContext._ = gettext.gettext
    return XPathContext.FunctionArgType


def transform_status(fmt_expanded):
    """Classify a fact's `format`, or None when it may be applied.

    Returns a truthful refusal reason rather than letting an unreadable
    transform fall through to a generic "the number did not match": every one
    of the six legacy/near-miss/SEC cases used to end in
    `value_does_not_reconcile`, which names the arithmetic and hides the cause.

    ONE ARGUMENT, and no raw spelling. This took `fmt_raw` as well, to tell
    ABSENT from present — but the boundary already refuses every present-and-
    malformed `format` before an evidence record exists, so by the time anything
    calls this, `None` can only mean ABSENT. Carrying the raw text as a second
    source of truth let a caller passing `''` be read as "no format", which is
    the raw-string compatibility path this round exists to remove.
    """
    if fmt_expanded is None:                  # ABSENT is lawful and distinct
        return None
    uri, local = fmt_expanded
    if uri == _SEC_REGISTRY:
        # Official under release 26.1, unimplemented by the pinned library. Not
        # malformed, not silently dropped, and NOT hand-written here.
        return UNSUPPORTED_OFFICIAL_TRANSFORM
    if uri not in _IMPLEMENTED_REGISTRIES:
        return UNSUPPORTED_TRANSFORM_REGISTRY
    if local not in (_ixt_registry(uri) or {}):
        # An approved registry that names no such signature: the filing states
        # a transform this version does not define, which is malformed markup.
        return MALFORMED_FORMAT
    return None


#: THE GRAPH'S OWN NUMBER GRAMMAR — an optional sign, ASCII digits in the
#: writer's canonical comma grouping, and an optional 1-3 digit fraction.
#:
#: AUTHORITY, separated plainly (SEQ 269):
#:   · GRAPH lexical spelling — this pattern — is owned by THE FROZEN
#:     CANONICAL GRAPH LEXICAL CONTRACT (SEQ 265 C / 266 §2), derived from
#:     the two identical `neograph/Neo4jManager.py` writer formatters
#:     (`f"{v:,}"` for int, `f"{v:,.3f}".rstrip('0').rstrip('.')` for
#:     float): canonical ASCII comma grouping, no leading-zero repair, an
#:     optional 1-3 digit fraction whose LAST digit is nonzero, lawful
#:     `-0`, no invented size limit. The WRITER CONFORMS TO THIS GRAMMAR —
#:     no claim is made about which strings IEEE floats can reach — and
#:     the 12,402,201-value census (2026-08-01: underscores 0, exponents
#:     0, NaN letters 0, parentheses 0) is compatibility evidence, never
#:     the source of the rule.
#:   · SOURCE accounting signs and parentheses are FinalPlan §6 / source-
#:     reader law: that section describes the shared SOURCE verifier and
#:     its visible accounting-negative lane, not graph `Fact.value`
#:     spelling — so parentheses are refused here and handled where the
#:     source is read.
#: `Decimal()` IS NOT THIS GRAMMAR — it reads Python underscore separators
#: (`1_0` -> 10), full-width and Arabic-Indic digits, exponents, Infinity, and
#: sNaN, a SIGNALLING NaN that raises as soon as anything touches it. The same
#: lesson `xml_integer` already carries, on the graph's side of the join.
#: Non-finite spellings fall outside the grammar and need no branch of their
#: own.
_GRAPH_NUMBER = re.compile(
    r'-?(?:0|[1-9][0-9]{0,2}(?:,[0-9]{3})*)(?:\.[0-9]{0,2}[1-9])?\Z')


def parse_raw(raw):
    """Graph raw value string → exact Decimal, or None when it is not one.

    GRAPH-ONLY. The accepted language is the frozen canonical graph
    lexical contract derived from the two writer formatters (the grammar
    above); corpus evidence shows compatibility, not legality or complete
    formatter reachability. Parentheses, padding, exponents, ungrouped
    digit runs and non-finite spellings fall outside the contract, and all
    refuse here. The SOURCE lane's accounting-negative law (visible
    parentheses with the schema's `sign`) lives with the source readers,
    not in this parser.
    """
    if not isinstance(raw, str):
        return None
    if not _GRAPH_NUMBER.fullmatch(raw):
        return None
    return Decimal(raw.replace(',', ''))


def _no_format_value(text):
    """Inline XBRL 1.1 §10.1.2 — a fact with NO `format` states the number
    itself, and it must be a NON-NEGATIVE XSD decimal.

    XML Schema whitespace collapse ONLY, through the one XML-whitespace owner:
    a blanket Python `.strip()` also eats U+00A0, U+000B, U+000C and U+3000,
    which XML does not call space, so padding with those was silently accepted
    as if the filing had written a clean number.

    The grammar is Arelle's `decimalPattern`, not one written here. `Decimal()`
    is NOT that grammar — it reads Python underscores, Unicode digits,
    exponents, Infinity and signalling NaN. `+0` and `-0` are the value zero and
    lawful; a negative NONZERO value is not.
    """
    from arelle.XmlValidate import decimalPattern
    collapsed = _collapse(text or '')
    if not decimalPattern.fullmatch(collapsed):
        return None
    value = Decimal(collapsed)
    if value < 0:                       # -0 compares equal to 0 and is lawful
        return None
    return value


def printed_value(displayed, fmt_expanded, sign):
    """The SIGNED, UNSCALED source-printed value (the emission value), or None.

    `fmt_expanded` is the format's (namespace URI, local name) — the identity —
    or None when the fact states no format at all. The filing's raw spelling is
    never passed here and never compared: it is a prefix the filer chose, and
    comparing it both refused lawful official transforms and accepted
    imitations of them.
    """
    shown = displayed or ''
    # The sign attribute carries the LITERAL '-' or is absent. It is NOT
    # stripped: repairing ' - ' into '-' invents a reading of malformed markup,
    # the same class as repairing a padded element id. Evidence that strictness
    # is free: 254,351 sign attributes across 1,769 real filings, every one
    # exactly '-'. (Unlike `scale`, whose spec type collapses whitespace — the
    # rule follows each attribute's own lexical space, not a blanket policy.)
    #
    # THIS CHECK NOW RUNS BEFORE THE FIXED-ZERO RETURN. `fixed-zero` returned
    # Decimal(0) first, so `sign="x"` and `sign=" - "` yielded a VALUE from
    # malformed markup instead of abstaining — reachable through the public
    # event door. Moving the existing lines up IS the whole fix: no new code,
    # no new refusal path, and it covers every branch at once. Lawful cases
    # that must keep working, and do: sign absent (193,026 fixed-zero tags in
    # the cache) and sign='-' (936).
    sign = '' if sign is None else sign
    if sign not in ('', '-'):          # a malformed sign is MALFORMED EVIDENCE:
        return None                    # reading it as positive invented a value
    if fmt_expanded is None:
        value = _no_format_value(shown)
    else:
        if transform_status(fmt_expanded) is not None:
            return None                # the caller reports the truthful reason
        # THE REGISTRY TRANSFORMS IT. We do not reimplement `num-dot-decimal`,
        # `fixed-zero` or any other signature, and we do not pre-screen the
        # input: the registry owns which text it accepts — `fixed-zero` lawfully
        # accepts ANY string — and second-guessing it here is how the old
        # hand-written grammar refused lawful facts.
        uri, local = fmt_expanded
        # THE REFUSAL TYPE IS RESOLVED **BEFORE** THE CALL. `except _ixt_refusal():`
        # looks equivalent, but Python evaluates that expression only once an
        # exception is already propagating — so the gettext hook it arms was
        # armed too late for the very refusal it exists to catch, and the FIRST
        # invalid input in a process surfaced as `NameError: name '_' is not
        # defined` instead of an abstention. Resolving it first also means the
        # `except` clause is a plain type, with no work left to fail.
        refusal = _ixt_refusal()
        try:
            out = _ixt_registry(uri)[local](shown)
        except refusal:
            return None                # the API's DECLARED refusal, and only it
        # A TRANSFORM NEED NOT PRODUCE A NUMBER. Date, boolean and word
        # transforms are lawful members of these registries; their output simply
        # cannot become a numeric fact, so it is checked against the same
        # official decimal grammar rather than handed to `Decimal()`.
        if not isinstance(out, str):
            return None
        from arelle.XmlValidate import decimalPattern
        if not decimalPattern.fullmatch(out):
            return None
        value = Decimal(out)
    if value is None:
        return None
    # SIGN LAST, exactly as §10.1.2 orders it: the transform supplies neither
    # sign nor scale, and scale is applied later still, in reconciliation.
    return -value if sign == '-' else value


#: (the ONE `_XSI_NS` definition lives beside the context shape law above —
#: XML Schema instance, where both `nil` and `type` live)
#: The XML Schema boolean lexical space, and ONLY it. `xs:boolean` collapses
#: whitespace and then admits exactly these four spellings; `TRUE`, `yes` and
#: `''` are not among them, so a nil claim written any other way is markup this
#: parser must refuse rather than quietly read as false.
#: https://www.w3.org/TR/xmlschema-2/#boolean
_XS_TRUE, _XS_FALSE = ('true', '1'), ('false', '0')

#: EVERY way a nonFraction can fail to state ONE value, each named for the rule
#: it breaks. Kept beside the reader so a refusal can never be vaguer than the
#: law it enforces.
#: `malformed`, not `unsupported`: these shapes violate the Inline XBRL content
#: model, so the markup is wrong — this product is not merely declining to
#: support something lawful, which is a different and much kinder claim.
MALFORMED_FACT_CONTENT = 'malformed_fact_content_model'
MALFORMED_FACT_NIL = 'malformed_nil'
MALFORMED_NESTED_NIL = 'malformed_nested_nil'
MALFORMED_FACT_ACCURACY = 'malformed_decimals_or_precision'
NESTED_FACT_DISAGREES = 'nested_fact_disagrees'
NIL_FACT_HAS_NO_VALUE = 'nil_fact_has_no_value'


def _integer_pattern():
    """ARELLE OWNS THE OFFICIAL INTEGER GRAMMAR; this only borrows it.

    `xml_integer` CONVERTS, so CPython's 4,300-digit ceiling made it refuse
    integers the schema permits — a limit of our runtime reported as a defect in
    the filing. The pinned `arelle-release` already carries the lexical pattern
    the standard defines, and matching text against it never converts.

    Imported lazily: `arelle` is a large package and this is the one place in
    the driver that needs it, so nothing else pays to load it.
    """
    from arelle.XmlValidate import integerPattern
    return integerPattern


def _nil_true(el):
    """`xsi:nil` read as the `xs:boolean` it is: True, False, or None when the
    attribute is absent — and `_typed` has already applied the collapse facet,
    so ` true ` is `true`. A spelling outside the lexical space raises, because
    reading a misspelled nil claim as "not nil" would bind a value the filing
    says does not exist."""
    raw = _typed(el, '{%s}nil' % _XSI_NS)
    if raw is None:
        return None
    if raw in _XS_TRUE:
        return True
    if raw in _XS_FALSE:
        return False
    raise _MalformedNil()


class _MalformedNil(Exception):
    """`xsi:nil` outside the boolean lexical space — internal to the reader."""


def _accuracy_ok(dec, prec):
    """XBRL 2.1 §4.6.3: a NON-NIL numeric fact states EXACTLY ONE of `decimals`
    or `precision`, each in its own lexical type.

    `xbrli:decimalsType` is the union of `xs:integer` and `INF`;
    `xbrli:precisionType` is the union of `xs:nonNegativeInteger` and `INF`.
    Both are checked as TEXT against Arelle's official pattern, so an integer of
    any length is judged by the standard rather than by a conversion limit.

    NON-NEGATIVE WITHOUT CONVERTING: the sign and the presence of a nonzero
    digit decide it. `-0`, `-00` and arbitrarily long runs of zeros are all the
    value zero and lawful; only a negative with a nonzero digit is not.

    Takes the two VALUES rather than the element: the caller has already read
    them to settle the nil rules, and reading an attribute twice is how the two
    readings drift apart.
    """
    if (dec is None) == (prec is None):        # both, or neither
        return False
    raw = dec if dec is not None else prec
    # THE UNION'S TWO MEMBERS CARRY TWO DIFFERENT FACETS, so the value is read
    # RAW and each member applies its own. The `INF` member restricts
    # `xs:string`, which PRESERVES whitespace, so only the exact three
    # characters are that member's value — ` INF ` is not `INF`, it is
    # malformed markup. The numeric member restricts `xs:integer`, which
    # COLLAPSES, so ` -6 ` is `-6` and is collapsed here, once, by the one
    # XML-whitespace owner.
    if raw == 'INF':                           # the exact string-union member
        return True
    collapsed = _collapse(raw)
    # `fullmatch`, NOT `match`: the pattern ends `$`, which in this engine also
    # matches before a trailing newline, so `6\n` passed.
    if not _integer_pattern().fullmatch(collapsed):
        return False
    raw = collapsed
    if dec is not None:
        return True
    return not (raw.startswith('-') and any(c in '123456789' for c in raw))


def fact_value_input(el):
    """THE TRANSFORM INPUT for one `ix:nonFraction`, read from the STRICT fact.

    Returns `(text, None)` or `(None, reason)`.

    WHY THIS EXISTS. Reconciliation used to consume the RENDERER's `displayed`
    text — the visible characters of whatever the browser lays out under the
    element. Inline XBRL 1.1 §§10.1.1-10.1.2 defines the value from the XML
    fact instead, and the difference is not academic: any markup child rendered
    to the same characters bound just as readily as the real value, and a
    NESTED fact declaring a different scale or unitRef bound while contributing
    a number that means something else.

    THE CONTENT MODEL, and it is small: exactly one child — text, or one nested
    `ix:nonFraction` that AGREES with its ancestor on the three properties that
    change what the number means. Format is compared as an EXPANDED name,
    because a prefix is an alias; scale is compared as a parsed integer,
    because `06` and `6` are the same scale; `unitRef` is an NCName reference
    and is compared exactly.

    MEASURED before it was written, read-only over 150 frozen filings and
    282,604 facts: 98.87% carry text alone, 1.13% (3,206) carry ONE nested
    nonFraction — with ZERO attribute disagreements — and NOT ONE carries a
    markup child. So refusing markup costs nothing real, and the nested case
    had to keep working or the rule would have broken 3,206 lawful facts.

    Spec sources:
      Inline XBRL 1.1 Part 1 §10.1.1 nonFraction, §10.1.2 value —
      Recommendation 2013-11-18 with approved errata corrections to
      2026-07-14, the current edition, read and confirmed unchanged on these
      sections: "exactly one child which SHALL be either an `ix:nonFraction`
      element or a text node, unless it has an `xsi:nil` attribute with the
      value true", the nested element in the SAME namespace, and a text-node
      child that "MUST be a non-empty string".
      https://www.xbrl.org/Specification/inlineXBRL-part1/REC-2013-11-18+errata-2026-07-14/inlineXBRL-part1-REC-2013-11-18+corrected-errata-2026-07-14.html
    """
    node, depth = el, 0
    while True:
        # NIL IS READ ONCE PER LEVEL, and the whole nil/accuracy combination is
        # settled before any "lawful no-value" answer is given. Returning early
        # on `nil=true` skipped both checks below, so a fact carrying a
        # contradiction was reported as a lawful empty one — a refusal that
        # sounds like a fact about the filer's data when it is a fact about
        # their markup.
        try:
            nil = _nil_true(node)
        except _MalformedNil:
            return None, MALFORMED_FACT_NIL
        dec, prec = _typed(node, 'decimals'), _typed(node, 'precision')
        if nil:
            # XBRL 2.1 §4.6.3 — a nil item asserts NO value, so it may bound
            # no accuracy either. Stating both is a contradiction in the markup.
            if dec is not None or prec is not None:
                return None, MALFORMED_FACT_ACCURACY
            # Inline XBRL 1.1 §10.1.1 — a true-nil nonFraction MUST NOT sit
            # below a nonFraction ancestor: the outer fact would then have a
            # child that supplies nothing.
            if depth:
                return None, MALFORMED_NESTED_NIL
            # 4,656 facts in the frozen cache (0.202%) reach here: lawful
            # filings that simply cannot supply the value a non-nil graph row
            # asserts.
            return None, NIL_FACT_HAS_NO_VALUE
        # EVERY CHILD NODE COUNTS, including the ones that render as nothing.
        # `isinstance(c.tag, str)` skipped comments and processing instructions,
        # so `<ix:nonFraction><!--x--></ix:nonFraction>` looked childless and,
        # with `format="ixt:fixed-zero"`, transformed into a clean 0.
        # ACCURACY IS PER FACT, at EVERY level of the chain. XBRL 2.1 §4.6.3
        # binds each numeric item, so checking only the leaf let an outer fact
        # with no `decimals` and no `precision` travel on its child's.
        if not _accuracy_ok(dec, prec):
            return None, MALFORMED_FACT_ACCURACY
        kids = list(node)
        elements = [c for c in kids if isinstance(c.tag, str)]
        if not kids:
            # THE LEAF, and the question is HOW MANY CHILDREN — not what they
            # say. `<f/>` has NO text node and `or ''` used to mint an empty one
            # for it. `<f>   </f>` has ONE, exactly as `390` does.
            #
            # THE TEXT IS NOT STRIPPED, HERE OR ANYWHERE IN THIS READER. An
            # earlier version judged non-emptiness after removing XML whitespace,
            # which refused a lawful shape: `ixt:fixed-zero` accepts ANY string,
            # so whether spaces are a lawful INPUT belongs to the transform. The
            # value is handed on exactly as written.
            if node.text is None:
                return None, MALFORMED_FACT_CONTENT
            return node.text, None
        if len(kids) != 1 or len(elements) != 1 \
                or not _is(elements[0], _INLINE_NS, 'nonFraction'):
            return None, MALFORMED_FACT_CONTENT
        child = elements[0]
        # EXACTLY ONE CHILD, so ANY text node beside the nested fact is a
        # SECOND child — including whitespace, which is a text node like any
        # other. Stripping it first made ` <ix:nonFraction/> ` look like one
        # child when the document plainly holds three.
        if node.text is not None or child.tail is not None:
            return None, MALFORMED_FACT_CONTENT
        # THE THREE PROPERTIES THAT CHANGE THE MEANING OF THE NUMBER. Each is
        # compared in the form that decides identity, not in the form written.
        outer_fmt, inner_fmt = _typed(node, 'format'), _typed(child, 'format')
        if (outer_fmt is None) != (inner_fmt is None):
            return None, NESTED_FACT_DISAGREES
        if outer_fmt is not None and \
                _qname(outer_fmt, node) != _qname(inner_fmt, child):
            return None, NESTED_FACT_DISAGREES
        outer_scale = _typed(node, 'scale')
        inner_scale = _typed(child, 'scale')
        outer_n = 0 if outer_scale is None else xml_integer(outer_scale)
        inner_n = 0 if inner_scale is None else xml_integer(inner_scale)
        if outer_n is None or inner_n is None or outer_n != inner_n:
            return None, NESTED_FACT_DISAGREES
        if _typed(node, 'unitRef') != _typed(child, 'unitRef'):
            return None, NESTED_FACT_DISAGREES
        node, depth = child, depth + 1


def reconcile(displayed, fmt_expanded, scale, sign, raw_value):
    """displayed ∘ (format, scale, sign) == graph raw value (COMPARISON ONLY).

    THE FORMAT ARRIVES AS ITS EXPANDED IDENTITY, never as the filing's prefix.

    EXACT. The multiply used to run under the DEFAULT decimal context, so at 29
    significant digits it REJECTED the correct value and ACCEPTED a rounded
    wrong one — the worst possible pair. A power-of-ten shift never changes the
    coefficient, so `scaleb` under a precision derived from the operands is
    exact; an unrepresentable magnitude simply fails to reconcile."""
    raw = parse_raw(raw_value)
    if raw is None:
        return False
    base = printed_value(displayed, fmt_expanded, sign)
    if base is None:
        return False
    # The scale was ALREADY parsed once, at the HTML boundary, by the one XML
    # integer parser. Here it must be a real Python int and nothing else:
    # `int(6.9)` silently TRUNCATED to 6 and reconciled, and `isinstance(True,
    # int)` is True, so only an exact type check is strict enough.
    if type(scale) is not int:
        return False
    try:
        return exact_scaleb(base, scale) == raw
    except ExactError:
        return False            # unrepresentable simply fails to reconcile

# ---------------------------------------------------------------------------
# THE ONE complete Route-A binding operation (FinalPlan §5A Route A, steps 2-7).
# Exposed here, in the binder, so no caller re-implements any part of it: a Core
# verifier that called these pieces by hand got the identity law INVERTED and
# re-imported an arithmetic defect it had already fixed elsewhere.
# ---------------------------------------------------------------------------

# EU-054 (#827): these Core-facing spellings REUSE the frozen packet
# vocabulary — the exact clause is the Core-Fiscal contract sheet
# (Core_Fiscal_ContractSheet_2026-07-31.md) section 2, "source_evidence —
# exactly four keys": representation_sha256 (SHA-256 of the PREPARED text,
# harvest-time) · quote_span ([start, end) character offsets) ·
# raw_label_span (inside the quote span, or null) · pieces (ordered
# {kind, text, span}; kind in ('header', 'section'); order CARRIED, never
# chosen). Nothing here invents a spelling; the sheet is the owner.
SOURCE_EVIDENCE_KEYS = ('representation_sha256', 'quote_span',
                        'raw_label_span', 'pieces')
PIECE_KEYS = ('kind', 'text', 'span')
PIECE_KINDS = ('header', 'section')


def source_evidence(prepared, ev):
    """THE filing-side evidence for ONE already-resolved element — the four
    approved keys — built once and used by BOTH the locator and Core.

    It was written only inside the locator, so Core had no way to check a
    submitted claim against the filing except by trusting it. Two copies of this
    would be two definitions of what the filing says, which is the one thing a
    verifier may not have.

    PURE over an already-prepared document and already-resolved element
    evidence: it parses nothing, resolves nothing, searches nothing, and creates
    no second representation hash. Every value is an EXACT slice of the pinned
    text at its own recorded span; a piece whose span does not reproduce its
    text is DROPPED rather than corrected. Returns None when the element has no
    reproducible VISIBLE row/block evidence — evidence is never invented.

    "Visible evidence", not "span": there are two ways to have none, and only
    one of them is a missing span. A fact whose owner was never walked has
    `span is None`; a lawful fact that DISPLAYS nothing — whitespace under
    `ixt:fixed-zero`, say — has a real span of zero width and an empty quote.
    Both mean the filing cannot show where this number is, and the guard below
    covers both in one test.
    """
    quote = ev['row_text'] if ev['in_table'] else ev['block']
    span = ev['row_span'] if ev['in_table'] else ev['block_span']
    if not quote or span is None or prepared['text'][span[0]:span[1]] != quote:
        return None
    label_span = ev['row_label_span']
    pieces = [{'kind': 'header', 'text': text, 'span': [sp[0], sp[1]]}
              for text, sp in zip(ev['columns'], ev.get('column_spans', []))
              if sp is not None and prepared['text'][sp[0]:sp[1]] == text]
    sec_span = ev.get('section_span')
    if ev['section'] and sec_span is not None \
            and prepared['text'][sec_span[0]:sec_span[1]] == ev['section']:
        # ORDER IS CARRIED, NOT CHOSEN: aligned headers near→far, then the
        # section. Core compares the sequence exactly; nothing may reorder it.
        pieces.append({'kind': 'section', 'text': ev['section'],
                       'span': [sec_span[0], sec_span[1]]})
    return {'representation_sha256': prepared['text_sha'],
            'quote_span': [span[0], span[1]],
            'raw_label_span': ([label_span[0], label_span[1]]
                               if label_span else None),
            'pieces': pieces}


def bind_graph_fact(doc_or_html, *, inline_element_id, concept, context_id,
                    unit_ref, unit_name, is_divide, period_type, start_date,
                    end_date, dims, entity_cik, raw_value,
                    concept_namespace, graph_concept_qname):
    """Bind ONE graph Fact to its exact inline element, or abstain.

    Returns (bound, 'ok') or (None, reason). `bound` carries exactly FOUR
    keys — `evidence` (the element-local record), `unit_measures_expanded`
    and `unit_numerator_expanded` (the filing's declared unit as semantic
    identities), and `printed_value`. Reconciliation has already proven the
    graph value against what the filing prints, so the record does not carry
    a Decimal copy of the graph's own input back to the caller.

    SUPPORTED INPUT: `doc_or_html` is raw HTML text or the exact mapping
    `prepare()` returned — never an arbitrary caller-built dict. The keyword
    arguments are graph-row values and are validated here; the mapping's
    internals are `prepare()`'s own guarantees, which is why this function
    carries no second copy of `prepare()`'s refusals.

    The law, in order:
      * a NON-BLANK short id must resolve EXACTLY — missing, duplicate or
        unsupported abstains and never falls through (step 2/7);
      * the (name, contextRef, unitRef) fallback is permitted ONLY when the
        short id is null/blank, and only when unique (step 3);
      * the bound element's own concept, context, period, dimensions, entity and
        unit must match the graph fact — a member elsewhere in the filing proves
        nothing (steps 5/6);
      * hidden without local evidence abstains (step 7);
      * displayed ∘ (format, scale, sign) must equal the graph value under EXACT
        Decimal arithmetic (step 4).
    """
    prepared = _prepared(doc_or_html)
    if refused(prepared):
        return None, refused(prepared)
    # A non-string id is MALFORMED input, not something to coerce: an int id
    # used to crash on .strip(). Blank (None/''/whitespace) is LAWFUL and means
    # "this element has no id", which is a lawful shape. The dated, scoped
    # measurement of how many such facts exist has ONE owner in
    # `xbrl_attach`; repeating a bare count here made it look corpus-wide.
    if inline_element_id is not None and not isinstance(inline_element_id, str):
        return None, 'malformed_element_id'
    # BLANKNESS IS AN XML QUESTION, and `.strip()` is not the XML answer: it
    # also eats U+000B, U+000C, U+00A0 and U+3000, so an id made only of those
    # read as "this element carries no id" and was routed to the identity
    # fallback — a law that applies ONLY when the element genuinely has none.
    # XML 1.0 S is the whole set a document may lawfully pad a value with.
    # Blankness decides WHICH path. Whether a non-blank id is a lawful XML name
    # is `element_evidence`'s rule, stated once at the door both callers share;
    # the lookup itself still uses the id EXACTLY as stored, because a padded or
    # re-cased id is a DIFFERENT id, not a typo to repair.
    # THE GRAPH'S CONCEPT BECOMES ONE EXPANDED TARGET BEFORE EITHER PATH RUNS,
    # because BOTH paths need it: the exact-id path compares it to the element
    # it resolved, and the fallback SEARCHES by it. Computing it here is what
    # stops the fallback matching on prefixed text — a document may lawfully
    # bind two prefixes to one taxonomy, and `gaap:Revenues` is then the SAME
    # concept as `us-gaap:Revenues`, which raw string equality calls a miss.
    # EARNED FROM THE ONE OWNER, not rebuilt here — the locator earns its target
    # from the same function, so the two consumers cannot drift into different
    # rules about what a concept IS.
    target = graph_concept_target(concept, concept_namespace,
                                  graph_concept_qname)
    if target is None:
        return None, 'missing_graph_concept_namespace'

    if (inline_element_id or '').strip(XML_WS):
        evidence, why = element_evidence(prepared, inline_element_id)
        if evidence is None:
            return None, f'exact_id_{why}'          # NEVER a fallback
    else:
        el, why = identity_fallback(prepared, target, context_id, unit_ref)
        if el is None:
            return None, f'fallback_{why}'
        evidence, why = evidence_for_element(prepared, el)
        if evidence is None:
            return None, f'fallback_{why}'

    # THE CONCEPT IS COMPARED BY IDENTITY, AND THE IDENTITY IS REQUIRED.
    # `Concept.namespace` is the taxonomy URI the filing declared. Measured
    # read-only over the adapter's numeric non-nil population: 12,402,201 of
    # 12,402,201 facts carry exactly one Concept edge, none missing a namespace
    # and none holding the literal string "null". So there is no lawful case to
    # fall back for, and falling back to a prefixed-text comparison would have
    # quietly restored the very defect this replaces — a prefix is an alias, and
    # the SAME local name under a DIFFERENT taxonomy namespace is a different
    # concept that string equality accepts.
    #
    # THE PAIR COMES FROM ONE RECORD. Combining `namespace` from the Concept
    # with a local part sliced off some other qname would FABRICATE an expanded
    # name that no single source ever asserted. Both halves are taken from the
    # Concept node, and its own qname must agree with the concept the caller
    # asked for before either half is trusted.
    if evidence.get('name_expanded') != target:
        return None, 'concept_mismatch'
    if (evidence.get('context_ref') or '') != context_id:
        return None, 'context_mismatch'
    if (evidence.get('unit_ref') or '') != (unit_ref or ''):
        return None, 'unit_ref_mismatch'
    doc_entity = (evidence.get('entity') or '')
    # LEADING ZEROS ARE PRESERVED. Both sides used to be `lstrip('0')`-ed, so
    # `1` and `0000000001` named the same filer and the exact ten-digit form
    # the document states was thrown away. NOTHING IS PADDED HERE, in either
    # direction: the graph's measured form is already exactly ten ASCII digits
    # (census 2026-08-01, all 796 Company nodes) and so is the form the
    # document must state, so the two are compared exactly. This comment used
    # to say the graph stores the CIK unpadded and is padded up to match —
    # both halves untrue, and contradicted by the census recorded in
    # `graph_cik` twenty lines up in this same file.
    want_entity = _graph_cik(entity_cik)
    if want_entity is None:
        return None, 'malformed_entity_cik'
    # A BLANK doc entity cannot slip through: `_parse_context` :766-768 refuses
    # any context whose identifier is not the lawful ten-digit CIK, and even a
    # hypothetical '' mismatches the ten digits below.
    if doc_entity != want_entity:
        return None, 'entity_mismatch'
    # THE STORED PERIOD END IS EXCLUSIVE (Fable ruling 2026-07-09, 140/140
    # verified, and the law `match_xbrl_fact` already applies): the graph keeps
    # the claimed end PLUS ONE DAY, and an instant is stored in start_date the
    # same way. The DOCUMENT declares the inclusive dates, so the document's own
    # period is converted UP to the stored form before comparison. Real data
    # caught this: the 726 fact is 2023-01-01..2023-06-30 in the filing and
    # ..2023-07-01 in the graph.
    # THE GRAPH'S PERIOD KIND IS TWO WORDS, and every use below asks only
    # `== 'instant'` — so ANY other value, `None` included, fell through as
    # DURATION and bound a fact against a kind the graph never stated. Measured
    # read-only: `Period.period_type` holds exactly duration (8,358) and
    # instant (3,058). This is the same law `is_divide` already carries.
    if period_type not in ('instant', 'duration'):
        return None, 'malformed_period_type'
    # ALWAYS a 2-tuple: `_parse_context` :821-822 yields one in every arm,
    # forever included — the unpack is the contract, not a hazard.
    doc_start, doc_end = tuple(evidence.get('period') or ('', ''))
    # `<forever>` is LAWFUL source data carrying no dated boundary, so it can
    # never back a dated fact. It parks under its own named reason rather than
    # being reported as malformed (#827 blocker 2).
    if not doc_end and not doc_start:
        return None, 'forever_or_undated_period'
    try:
        # THE ONE dateUnion parser: the FILING may lawfully state xs:date or
        # xs:dateTime, so BOTH boundaries are read by the shared parser — the
        # start used to be compared as a RAW STRING and was never validated.
        # A start means MIDNIGHT OF ITS DAY (no day added); an end means the
        # FOLLOWING midnight (one day added). A lawful boundary this graph
        # cannot represent is UNBINDABLE — a different, honest answer from
        # malformed.
        stored_end = filing_boundary_graph_end(doc_end)
        stored_start = (None if period_type == 'instant'
                        else filing_boundary_graph_start(doc_start))
    # ONLY THE DECLARED MALFORMED-INPUT SIGNAL. This caught TypeError and
    # ValueError too, so a genuine code defect became an ordinary refusal —
    # a bug wearing a park's clothes. `ExactError` is the parser's one declared
    # malformed signal and already covers the non-string case explicitly, so
    # the other two names never earned their place. Measured before deleting
    # them: 2,400 real contexts driven through the narrowed binder, ZERO bare
    # TypeError/ValueError escapes — nothing lawful depended on the width.
    except ExactError:
        return None, 'malformed_period'
    if stored_end is None or (period_type != 'instant' and stored_start is None):
        return None, 'unbindable_period'
    # THE PERIOD KIND ITSELF MUST AGREE, and nothing here checked it. A LAWFUL
    # duration context bound a graph row typed `instant`: asking for an instant
    # set `stored_start=None` and compared only the end, so the document's own
    # kind was never read. This is the one shape in the class that needs NO
    # malformed markup — a wrong graph row alone was enough, and it attached
    # through the public door. The document declares an instant exactly when it
    # states no start (`period` is ('', instant)); the reverse direction was
    # refused only by accident, as a blank start reading 'malformed_period'.
    if (not doc_start) != (period_type == 'instant'):
        return None, 'period_kind_disagrees_with_the_filing'
    if period_type != 'instant':
        # A duration must run FORWARDS. Equal or reversed boundaries are not a
        # period, and a comparison that cannot be settled without inventing a
        # timezone is indeterminate — both refuse rather than guess.
        if filing_duration_ordered(doc_start, doc_end) is not True:
            return None, 'period_not_forward'
    stored = ((stored_end,) if period_type == 'instant'
              else (stored_start, stored_end))
    want = (start_date,) if period_type == 'instant' else (start_date, end_date)
    if stored != want:
        return None, 'period_mismatch'
    # THE EXPANDED VIEW, never the spellings. `dims` arrives from the graph as
    # (namespace URI, local name) pairs, so both sides state the same thing;
    # comparing the written prefixes would be comparing two documents' private
    # aliases and calling the result identity.
    if (tuple(sorted(evidence.get('dims_expanded') or ()))
            != tuple(sorted(dims or ()))):
        return None, 'dimension_set_mismatch'
    # EXISTENCE AND POISON ARE `_evidence_from`'s LAW (:1404-1408), proven on
    # this same prepared object before any evidence exists: an undefined or
    # poisoned unitRef never reaches this line, so `declared` is the parsed
    # unit dict by contract — a second check here could never fire.
    declared = (prepared.get('units') or {}).get(unit_ref)
    # THE CERTIFIED BOOLEAN LAW: only the exact graph strings. My own
    # `str(is_divide) in ('0','1')` accepted the Python ints 0 and 1, which this
    # map deliberately abstains on.
    divide_flag = ROUTE_A_BOOLS.get(is_divide) if isinstance(is_divide, str) \
        else None
    if divide_flag is None:
        return None, 'malformed_is_divide'
    if divide_flag != declared['is_divide']:
        return None, 'is_divide_disagrees_with_the_filing'
    # SIDE VALIDITY IS THE PARSER'S LAW. `_parse_unit` refuses a non-1x1
    # divide, a non-leaf measure, and any measure whose text is not a
    # resolvable QName (:848-867, :901-912) — so both sides here are non-blank
    # by construction, and a second non-blankness check could never fire.
    # Cache census 2026-07-27 stands: 2,086 divide declarations, all 1x1 and
    # non-blank. Plurality is LAWFUL; a compound side is the caller's policy.
    # THE FILING'S OWN MEASURES, rendered in the GRAPH's spelling — and the
    # rendering is decided by NAMESPACE, never by the letters of a prefix. The
    # graph drops the prefix of a measure in the INSTANCE namespace, so a filing
    # that lawfully binds that namespace to `i:` writes `i:shares` for the very
    # same measure the graph stores as `shares`; matching the literal text
    # `xbrli:` threw such a filing away. `_parse_unit` resolved each measure
    # where it was written and already produced these strings.
    #
    # KNOWN CONTRACT GAP, recorded rather than papered over: for a SIMPLE unit
    # the graph carries `Unit.namespace`, so this comparison can be made on
    # expanded names. For a DIVIDE unit it does not — `Unit.namespace` is the
    # string "null" and `Unit.name` is the numerator and denominator
    # CONCATENATED (`iso4217:USDshares`, `iso4217:USDiso4217:EUR`), which is not
    # invertible. So a divide unit is still compared on the stored spelling, and
    # that comparison cannot be proven alias-independent from the fields the
    # graph has today. The concatenated name is NEVER split to pretend
    # otherwise. 336,327 facts ride on this; the gap is the owner's to close.
    spelled = (''.join(declared['graph_numerator'])
               + ''.join(declared['graph_denominator']) if divide_flag
               else graph_unit_spelling(declared['graph_measures'], (), (), False))
    if spelled != unit_name:
        return None, 'unit_name_not_the_filings_measure'
    # NO UNIT-NAMESPACE CORROBORATION LIVES HERE, and the attempt is recorded
    # because it was WRONG rather than merely unnecessary. `Unit.namespace`
    # stores the LITERAL STRING "null" — not a Neo4j null — on 6,753 simple and
    # all 113 divide Unit nodes, and a non-empty string is truthy, so a
    # `if unit_namespace` guard would have compared a real namespace against
    # "null" and refused 137,600 lawful simple-unit facts. A sentinel exception
    # for that string would be exactly the kind of machinery this audit exists
    # to delete. The filing's EXPANDED measures, published above, are the
    # semantic authority once the fact and unitRef joins are proven; `unit_name`
    # stays as the storage-integrity comparison and nothing more.
    # THE BINDER REPORTS, IT DOES NOT DECIDE. Its job is finished once the
    # unit is VERIFIED against the filing's own declaration (above); which
    # canonical unit a fact may then claim is POLICY, and the two callers have
    # different policies — the dormant no-AI materializer's narrow whitelist vs
    # the AI-interpreted candidate path, which lawfully covers `pure`. This
    # module is shared, so applying either policy here would impose it on both,
    # and a second copy of the check would then run in the caller anyway.
    if evidence.get('hidden') and not (evidence.get('row_text')
                                       or evidence.get('block_span')):
        return None, 'hidden_without_local_evidence'
    # THE FACT'S OWN CONTENT, never the rendered characters. `displayed` is
    # whatever the browser lays out under this element, so any markup child
    # printing the same glyphs reconciled just as well as the real value.
    # THE FORMAT IS CLASSIFIED BEFORE THE ARITHMETIC, so its refusal keeps its
    # own name. Six distinct cases — the 2008/2010/2011/WGWD legacy registries,
    # a transform leaking across registry versions, and the SEC's own
    # unimplemented registry — all used to end as `value_does_not_reconcile`,
    # which names the subtraction and hides the cause.
    why_fmt = transform_status(evidence.get('fmt_expanded'))
    if why_fmt is not None:
        return None, why_fmt
    if not reconcile(evidence.get('value_input'), evidence.get('fmt_expanded'),
                     evidence.get('scale'), evidence.get('sign'), raw_value):
        return None, 'value_does_not_reconcile'
    # THE BINDER REPORTS WHAT THE FILING PRINTS AND DECLARES — nothing more.
    # A caller still binds the FIELDS rather than a final total, because
    # {390, 10^6}, {390000000, 1} and {0.39, 10^9} all convert to the same
    # number while only one describes what this filing prints. Reconciliation
    # above already proved the graph value against those fields, so the record
    # does not hand the caller a Decimal copy of the caller's own input — and
    # every other echo (the unit spelling, the raw flag, the duplicate scale,
    # the hash the caller already holds) is gone with it: FOUR keys, each with
    # a real production reader, none with two owners (#827 bundle B).
    return {'evidence': evidence,
            # THE FILING'S DECLARED UNIT AS SEMANTIC IDENTITIES — (namespace
            # URI, local name) per measure, resolved where each is written. A
            # prefix is an alias: `iso4217:USD` and `cur:USD` are the same
            # measure, and the same text under a rebound prefix is a DIFFERENT
            # one. Divide-ness needs no flag: a parsed unit cannot be
            # measureless, so `unit_measures_expanded == ()` holds exactly for
            # divide units.
            'unit_measures_expanded': tuple(declared['expanded_measures']),
            'unit_numerator_expanded': tuple(declared['expanded_numerator']),
            'printed_value': printed_value(evidence.get('value_input'),
                                           evidence.get('fmt_expanded'),
                                           evidence.get('sign'))}, 'ok'
