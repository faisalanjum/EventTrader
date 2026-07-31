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
import hashlib
import re
import warnings
from decimal import Decimal, InvalidOperation


from driver.relocation.exact_numbers import (ROUTE_A_BOOLS, ExactError,
                                             exact_scaleb, graph_unit_spelling,
                                             stored_period_end)

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# xsd:integer, EXACTLY: optional sign then ASCII digits, after XML whitespace
# collapsing. `int()` is NOT this check — it also accepts Python underscore
# separators (`1_0`), full-width digits (`１２`), Arabic-Indic (`٦`),
# Devanagari (`६`) and non-breaking spaces, none of which are legal here. And
# `\d` is NOT [0-9]: it matches every Unicode decimal digit, so it would let
# `１２` straight back in.
_XML_WS = ' \t\r\n'
_XML_INT = re.compile(r'[+-]?[0-9]+')


def xml_integer(raw):
    """The ONE XML-integer parser: int, or None when the text is not one.

    Accepts what the spec allows — `6`, `+6`, `-3`, `012`, and the same values
    surrounded by XML whitespace. Rejects everything else, including Python
    values: a bool or an int is not attribute TEXT.
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip(_XML_WS)
    if not _XML_INT.fullmatch(s):
        return None
    try:
        return int(s)
    except ValueError:            # Python refuses to convert a digit string
        return None               # beyond its 4300-digit limit — the contract
                                  # here is "int or None", never an exception

warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)


def sha256_text(html_text):
    return hashlib.sha256(html_text.encode('utf-8', 'surrogatepass')).hexdigest()


# ---- relocated from the pinned extractor (sha 38690c7b…) ------------------------

def _text(node):
    return (' '.join(node.get_text(' ', strip=True).replace('​', '').split())
            if node else '')


def _words(value):
    return re.findall(r"[A-Za-z][A-Za-z’'-]*", value)


def _span(value):
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return 1


def _table_grid(rows):
    occupied_until = {}
    grid = []
    for row_number, row in enumerate(rows):
        placed = []
        column = 0
        for cell in row.find_all(['td', 'th'], recursive=False):
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


def _has_number_fact(row):
    return bool(row.find(
        lambda tag: tag.name and tag.name.lower() == 'ix:nonfraction'))


def _hidden_cell(cell):
    style = str(cell.get('style') or '')
    return cell.has_attr('hidden') \
        or str(cell.get('aria-hidden') or '').lower() == 'true' \
        or bool(re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)',
                          style, re.I))


# THE edge-marker set, and its ONLY definition. These are the decorative
# characters a filing puts around a heading — an em dash, a hyphen, a space.
# They may be ignored when DECIDING whether a cell carries a heading; they are
# never removed from what gets STORED. Written once because a marker list with
# several authors drifts, and drift here silently changes which headings count.
_EDGE_MARKERS = ' —-'


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


_SPAN_TAGS = {'tr', 'td', 'th', 'p', 'li', 'div'}


def _visible_walk(root, spans=None):
    """THE hash-pinned representation walk: whitespace-normalized VISIBLE text
    (ix:hidden + CSS/attr-hidden excluded), optionally recording each structural
    node's EXACT character span — element-specific offsets, never global find()."""
    words = []

    def walk(node):
        name = getattr(node, 'name', None)
        if name is None:
            words.extend(str(node).replace('​', ' ').split())
            return
        if name.lower() == 'ix:hidden' or _hidden_cell(node):
            return
        track = spans is not None and name.lower() in _SPAN_TAGS
        if track:
            start_tok = len(words)
        for child in node.children:
            walk(child)
        if track:
            spans[id(node)] = (start_tok, len(words))

    walk(root)
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


def _visible_text(root):
    return _visible_walk(root)


def _css_hidden_ancestry(el):
    node = el
    while node is not None and getattr(node, 'get', None):
        if _hidden_cell(node):
            return True
        node = node.parent
    return False


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
    target = next((item for item in grid[row_number] if item[0] is fact_cell), None)
    if not target:
        return []
    _, target_start, target_end = target
    stack = []
    for distance in range(1, row_number + 1):
        prior_number = row_number - distance
        if _has_number_fact(rows[prior_number]):
            continue
        for cell, start, end in grid[prior_number]:
            text, span = _visible_slice(cell, prepared)
            # The strip here is the SELECTION test only — a cell that is nothing
            # but an edge marker carries no header. The value appended is the
            # untrimmed slice.
            if end <= target_start or start >= target_end \
                    or not text.strip(_EDGE_MARKERS) \
                    or (start == 0 and target_start > 0) or _hidden_cell(cell):
                continue                     # numeric-only headers ('2024') RETAINED
            stack.append((text, span))
    return stack


# ---- document preparation (ONE parse per filing) --------------------------------

def _soup(html_text):
    return BeautifulSoup(html_text, 'lxml')


_PREP_CACHE = {}


def prepare(html_text):
    """Parse and index a display filing EXACTLY ONCE — memoized by content sha so
    repeated locate() calls (one per anchor) share ONE parse per filing."""
    sha = sha256_text(html_text)
    hit = _PREP_CACHE.get(sha)
    if hit is not None:
        return hit
    soup = _soup(html_text)
    id_counts = {}
    for el in soup.find_all(id=True):
        eid = el.get('id')
        id_counts[eid] = id_counts.get(eid, 0) + 1
    contexts = {}
    for context in soup.find_all(
            lambda tag: tag.name and tag.name.lower() == 'xbrli:context'):
        cid = context.get('id')
        if not cid:
            continue
        find = lambda name: context.find(
            lambda tag: tag.name and tag.name.lower() == name)
        instant = _text(find('xbrli:instant'))
        period = (('', instant) if instant else
                  (_text(find('xbrli:startdate')), _text(find('xbrli:enddate'))))
        ident = context.find(
            lambda tag: tag.name and tag.name.lower() == 'xbrli:identifier')
        typed = context.find(
            lambda tag: tag.name and tag.name.lower() == 'xbrldi:typedmember')
        dims = tuple(sorted(
            (item.get('dimension'), _text(item))
            for item in context.find_all(
                lambda tag: tag.name and tag.name.lower() == 'xbrldi:explicitmember')))
        if cid in contexts:              # a duplicated context id is AMBIGUOUS
            contexts[cid] = None            # evidence; last-wins silently picked
            continue                        # one. Poison it: consumers abstain.
        contexts[cid] = {'period': period, 'dims': dims,
                         'typed': typed is not None,
                         'entity': _text(ident).lstrip('0') if ident else ''}
    units = {}
    for u in soup.find_all(lambda tag: tag.name and tag.name.lower() == 'xbrli:unit'):
        uid = u.get('id')
        if not uid:
            continue
        # the filing's OWN declaration: which measure(s), and whether it is a
        # divide unit (a per-something ratio such as USD/share)
        divide = u.find(lambda t: t.name and t.name.lower() == 'xbrli:divide')
        def _m(node):
            return tuple(_text(m) for m in node.find_all(
                lambda t: t.name and t.name.lower() == 'xbrli:measure')) if node else ()
        if divide is None:
            measures, num, den = _m(u), (), ()
        else:
            num = _m(divide.find(lambda t: t.name
                                 and t.name.lower() == 'xbrli:unitnumerator'))
            den = _m(divide.find(lambda t: t.name
                                 and t.name.lower() == 'xbrli:unitdenominator'))
            measures = num + den
        if uid in units:                 # a duplicated unit id is AMBIGUOUS
            units[uid] = None            # evidence exactly as a duplicated
            continue                     # context is. Poison it; consumers
                                         # abstain instead of taking the last.
        units[uid] = {'measures': measures, 'is_divide': divide is not None,
                      'numerator': num, 'denominator': den}
    elements = {}
    noid_elements = []
    for el in soup.find_all(
            lambda tag: tag.name and tag.name.lower() == 'ix:nonfraction'):
        eid = el.get('id')
        if eid:
            elements.setdefault(eid, el)
        else:
            noid_elements.append(el)         # null-graph-id facts live HERE
    node_spans = {}
    text = _visible_walk(soup, node_spans)
    prepared = {'soup': soup, 'ids': id_counts, 'contexts': contexts,
                'node_spans': node_spans,
                'units': units, 'elements': elements,
                'noid_elements': noid_elements,
                'raw_sha': sha,             # sha of the RAW fetched bytes/text
                'sha': sha,
                'text': text,               # THE representation (visible text)
                'text_sha': hashlib.sha256(text.encode('utf-8',
                                           'surrogatepass')).hexdigest()}
    while len(_PREP_CACHE) >= 4:
        _PREP_CACHE.pop(next(iter(_PREP_CACHE)))
    _PREP_CACHE[sha] = prepared
    return prepared


def _prepared(doc_or_html):
    return doc_or_html if isinstance(doc_or_html, dict) else prepare(doc_or_html)


def _evidence_from(el, prepared):
    ctx_ref = el.get('contextref')
    if not ctx_ref:
        return None, 'missing_context_ref'
    if ctx_ref in prepared['contexts'] and prepared['contexts'][ctx_ref] is None:
        return None, 'duplicate_context_id'
    ctx = prepared['contexts'].get(ctx_ref)
    if ctx is None:
        return None, 'undefined_context'
    if ctx['typed']:
        return None, 'typed_dimensions_unsupported'
    unit_ref = el.get('unitref') or ''
    if unit_ref:
        if unit_ref not in prepared['units']:
            return None, 'undefined_unit'
        if prepared['units'][unit_ref] is None:      # duplicated unit id: the
            return None, 'duplicate_unit_id'        # declaration is ambiguous
    raw_scale = el.get('scale')
    # ABSENT means 0 (the spec default); PRESENT means it must parse as an XML
    # integer — `''`, `6.9`, `1_0` and full-width digits are malformed markup.
    scale = 0 if raw_scale is None else xml_integer(raw_scale)
    if scale is None:
        return None, 'malformed_scale'
    hidden = el.find_parent(
        lambda tag: tag.name and tag.name.lower() == 'ix:hidden') is not None \
        or _css_hidden_ancestry(el)
    ev = {
        'name': el.get('name') or '',
        'displayed': _text(el),
        'scale': scale,
        'sign': el.get('sign') or '',
        'fmt': el.get('format') or '',
        'unit_ref': unit_ref,
        'context_ref': ctx_ref,
        'period': ctx['period'],
        'dims': ctx['dims'],
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
    cell = el.find_parent(['td', 'th'])
    row = cell.find_parent('tr') if cell is not None else None
    if cell is not None and row is not None:
        ev['in_table'] = True
        ev['row_text'] = _visible_text(row)
        ev['row_span'] = prepared.get('node_spans', {}).get(id(row))
        cells = row.find_all(['td', 'th'], recursive=False)
        visible = [item for item in cells if not _hidden_cell(item)]
        # A cell can be visible while a DESCENDANT of it is hidden, so excluding
        # hidden cells is not enough — the text has to come from the
        # representation itself.
        ev['row_cells'] = [_visible_slice(item, prepared)[0] for item in visible]
        fact_cell = cells.index(cell) if cell in cells else None
        if fact_cell is not None:
            # SELECT ON VISIBLE TEXT, and take the value and the span from the
            # SAME cell. Selecting on `_text` let a cell whose only content is
            # hidden become the label — a label that appears nowhere in the
            # filing, carrying a span that covers nothing. `find()` stays
            # deleted: the chosen cell already knows its own extent.
            left = [item for item in cells[:fact_cell]
                    if not _hidden_cell(item)
                    and _words(_visible_slice(item, prepared)[0])]
            if left:                                     # digits in labels LEGAL
                ev['row_label'], ev['row_label_span'] = \
                    _visible_slice(left[0], prepared)
        table = row.find_parent('table')
        if table is not None:
            table_rows = [r for r in table.find_all('tr')
                          if r.find_parent('table') is table]
            if row in table_rows and fact_cell is not None:
                row_number = table_rows.index(row)
                col_pairs = _aligned_columns(table_rows, row_number, cell,
                                             prepared)
                ev['columns'] = [c for c, _ in col_pairs]
                ev['column_spans'] = [sp for _, sp in col_pairs]
                for prior in reversed(table_rows[:row_number]):
                    prior_cells = prior.find_all(['td', 'th'], recursive=False)
                    # ONE eligible list decides BOTH the text and the span. They
                    # were chosen by two DIFFERENT filters — the text skipped
                    # digit-bearing cells and the span did not — so a row like
                    # "Q1 2023 | Segment detail" reported one cell's words at
                    # the other cell's offsets.
                    eligible = [(t, sp) for t, sp in
                                (_visible_slice(item, prepared)
                                 for item in prior_cells
                                 if not _hidden_cell(item))
                                if _words(t) and not re.search(r'\d', t)]
                    first = (_visible_slice(prior_cells[0], prepared)[0]
                             if prior_cells else '')
                    if prior_cells and not _has_number_fact(prior) \
                            and first and len(eligible) == 1 \
                            and not eligible[0][0].lstrip(
                                _EDGE_MARKERS).startswith('('):
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
        block = el.find_parent(['p', 'li', 'div'])
        ev['block'] = (_visible_text(block) if block is not None
                       else _visible_text(el.parent))
        src_node = block if block is not None else el.parent
        ev['block_span'] = prepared.get('node_spans', {}).get(id(src_node))
    return ev, 'ok'


def element_evidence(doc_or_html, element_id):
    """(evidence, 'ok') for the exact element carrying id=element_id, else
    (None, reason). Accepts a prepare()d document or raw HTML text."""
    if not element_id or not str(element_id).strip():
        return None, 'blank_id'
    prepared = _prepared(doc_or_html)
    count = prepared['ids'].get(element_id, 0)
    if count == 0:
        return None, 'id_not_found'
    if count > 1:
        return None, 'duplicate_id'
    el = prepared['elements'].get(element_id)
    if el is None:
        return None, 'unsupported_element_kind'
    return _evidence_from(el, prepared)


def identity_fallback(doc_or_html, name, context_ref, unit_ref):
    """Complete-identity fallback (FinalPlan §5A.3) — searches BOTH id-carrying and
    id-less elements (a null graph fact_id usually MEANS the element has no id).
    Returns (element, 'ok') only when exactly one matches."""
    prepared = _prepared(doc_or_html)
    pool = list(prepared['elements'].values()) + prepared['noid_elements']
    hits = [el for el in pool
            if (el.get('name') or '') == name
            and (el.get('contextref') or '') == context_ref
            and (el.get('unitref') or '') == unit_ref]
    if not hits:
        return None, 'no_identity_match'
    if len(hits) > 1:
        return None, 'ambiguous_identity'
    return hits[0], 'ok'


def evidence_for_element(doc_or_html, el):
    """Evidence for an already-resolved element node (the fallback path)."""
    return _evidence_from(el, _prepared(doc_or_html))


def find_by_identity(doc_or_html, name, unit_ref):
    prepared = _prepared(doc_or_html)
    return [eid for eid, el in prepared['elements'].items()
            if (el.get('name') or '') == name
            and (el.get('unitref') or '') == unit_ref]


# ---- exact Decimal reconciliation ----------------------------------------------

_NUM_DOT = re.compile(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?$|\d+(?:\.\d+)?$|\.\d+$')
_KNOWN_FMT = {'', 'ixt:num-dot-decimal', 'ixt:numdotdecimal'}


def parse_raw(raw):
    """Graph raw value string → exact Decimal (commas + accounting-paren law)."""
    if raw is None:
        return None
    s = str(raw).strip().replace(',', '')
    neg = s.startswith('(') and s.endswith(')')
    if neg:
        s = s[1:-1]
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return -d if neg else d


def printed_value(displayed, fmt, sign):
    """The SIGNED, UNSCALED source-printed value (the emission value), or None."""
    fmt = (fmt or '').strip()
    shown = (displayed or '').strip()
    if fmt == 'ixt:fixed-zero':
        return Decimal(0)
    if fmt not in _KNOWN_FMT or not _NUM_DOT.fullmatch(shown):
        return None
    # The sign attribute carries the LITERAL '-' or is absent. It is NOT
    # stripped: repairing ' - ' into '-' invents a reading of malformed markup,
    # the same class as repairing a padded element id. Evidence that strictness
    # is free: 254,351 sign attributes across 1,769 real filings, every one
    # exactly '-'. (Unlike `scale`, whose spec type collapses whitespace — the
    # rule follows each attribute's own lexical space, not a blanket policy.)
    sign = '' if sign is None else sign
    if sign not in ('', '-'):          # a malformed sign is MALFORMED EVIDENCE:
        return None                    # reading it as positive invented a value
    try:
        value = Decimal(shown.replace(',', ''))
    except InvalidOperation:
        return None
    return -value if sign == '-' else value


def reconcile(displayed, fmt, scale, sign, raw_value):
    """displayed ∘ (format, scale, sign) == graph raw value (COMPARISON ONLY).

    EXACT. The multiply used to run under the DEFAULT decimal context, so at 29
    significant digits it REJECTED the correct value and ACCEPTED a rounded
    wrong one — the worst possible pair. A power-of-ten shift never changes the
    coefficient, so `scaleb` under a precision derived from the operands is
    exact; an unrepresentable magnitude simply fails to reconcile."""
    raw = parse_raw(raw_value)
    if raw is None:
        return False
    base = printed_value(displayed, fmt, sign)
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
    reproducible row/block span — evidence is never invented.
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
                    end_date, dims, entity_cik, raw_value):
    """Bind ONE graph Fact to its exact inline element, or abstain.

    Returns (bound, 'ok') or (None, reason). `bound` carries the element-local
    evidence, the EXACT Decimal value, and the semantic unit.

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
    # A non-string id is MALFORMED input, not something to coerce: an int id
    # used to crash on .strip(). Blank (None/''/whitespace) is LAWFUL and means
    # "this element has no id", which is a lawful shape. The dated, scoped
    # measurement of how many such facts exist has ONE owner in
    # `xbrl_attach`; repeating a bare count here made it look corpus-wide.
    if inline_element_id is not None and not isinstance(inline_element_id, str):
        return None, 'malformed_element_id'
    # blankness decides WHICH path; the lookup itself uses the id EXACTLY as
    # stored — a padded or re-cased id is a DIFFERENT id, not a typo to repair.
    if (inline_element_id or '').strip():
        evidence, why = element_evidence(prepared, inline_element_id)
        if evidence is None:
            return None, f'exact_id_{why}'          # NEVER a fallback
    else:
        el, why = identity_fallback(prepared, concept, context_id, unit_ref)
        if el is None:
            return None, f'fallback_{why}'
        evidence, why = evidence_for_element(prepared, el)
        if evidence is None:
            return None, f'fallback_{why}'

    if (evidence.get('name') or '') != concept:
        return None, 'concept_mismatch'
    if (evidence.get('context_ref') or '') != context_id:
        return None, 'context_mismatch'
    if (evidence.get('unit_ref') or '') != (unit_ref or ''):
        return None, 'unit_ref_mismatch'
    doc_entity = (evidence.get('entity') or '')
    want_entity = str(entity_cik or '').lstrip('0')
    if not doc_entity or not want_entity:      # an ABSENT identifier proves
        return None, 'entity_missing'          # nothing; '' == '' is fail-open
    if doc_entity != want_entity:
        return None, 'entity_mismatch'
    # THE STORED PERIOD END IS EXCLUSIVE (Fable ruling 2026-07-09, 140/140
    # verified, and the law `match_xbrl_fact` already applies): the graph keeps
    # the claimed end PLUS ONE DAY, and an instant is stored in start_date the
    # same way. The DOCUMENT declares the inclusive dates, so the document's own
    # period is converted UP to the stored form before comparison. Real data
    # caught this: the 726 fact is 2023-01-01..2023-06-30 in the filing and
    # ..2023-07-01 in the graph.
    doc_period = tuple(evidence.get('period') or ())
    if len(doc_period) != 2:
        return None, 'period_missing'
    try:
        doc_start, doc_end = doc_period
        stored = ((stored_period_end(doc_end),) if period_type == 'instant'
                  else (doc_start, stored_period_end(doc_end)))
    except (ExactError, TypeError, ValueError):
        return None, 'malformed_period'
    want = (start_date,) if period_type == 'instant' else (start_date, end_date)
    if stored != want:
        return None, 'period_mismatch'
    if tuple(sorted(evidence.get('dims') or ())) != tuple(sorted(dims or ())):
        return None, 'dimension_set_mismatch'
    if unit_ref in (prepared.get('units') or {}) \
            and (prepared['units'][unit_ref] is None):
        return None, 'duplicate_unit_id'
    declared = (prepared.get('units') or {}).get(unit_ref)
    if not isinstance(declared, dict):
        return None, 'unit_not_declared_in_filing'
    # THE CERTIFIED BOOLEAN LAW: only the exact graph strings. My own
    # `str(is_divide) in ('0','1')` accepted the Python ints 0 and 1, which this
    # map deliberately abstains on.
    divide_flag = ROUTE_A_BOOLS.get(is_divide) if isinstance(is_divide, str) \
        else None
    if divide_flag is None:
        return None, 'malformed_is_divide'
    if divide_flag != declared['is_divide']:
        return None, 'is_divide_disagrees_with_the_filing'
    # XBRL 2.1 requires BOTH sides of a divide to carry at least one measure.
    # STRUCTURAL VALIDITY of the filing, so it is checked HERE, once, in the
    # shared binder — not in any caller's unit policy. A USD numerator with an
    # empty denominator used to bind, and so did an empty numerator and a blank
    # measure. MORE than one measure per side is LAWFUL and is not refused
    # here; whether a compound numerator can be read is the caller's policy.
    # Cache census 2026-07-27: 1,769 filings, 2,086 divide declarations, every
    # one 1x1 and non-blank — this guard changes no current fact.
    # EVERY measure must be NON-BLANK, on both sides — not merely one per side,
    # which is what the first guard asked, so a real measure paired with a blank
    # one still bound. That is the whole claim: this checks non-blankness, NOT
    # that the text is a well-formed QName, and no XML validator is built here.
    # Plurality is LAWFUL and is not what is refused.
    def _valid_side(measures):
        return bool(measures) and all(
            isinstance(m, str) and m.strip() for m in measures)

    if declared['is_divide'] and not (_valid_side(declared['numerator'])
                                      and _valid_side(declared['denominator'])):
        return None, 'malformed_divide_unit_measure'
    # THE FILING'S OWN MEASURES, rendered in the GRAPH's spelling. The graph
    # drops the `xbrli:` prefix, so comparing the two spellings DIRECTLY made
    # every share fact ('shares' vs 'xbrli:shares') and every per-share fact
    # abstain — the whole EPS and share-count class, in every real filing.
    if graph_unit_spelling(declared['measures'], declared['numerator'],
                           declared['denominator'], divide_flag) != unit_name:
        return None, 'unit_name_not_the_filings_measure'
    # THE BINDER REPORTS, IT DOES NOT DECIDE. Its job is finished once the
    # unit is VERIFIED against the filing's own declaration (above); which
    # canonical unit a fact may then claim is POLICY, and the two callers have
    # different policies — the dormant no-AI materializer's narrow whitelist vs
    # the AI-interpreted candidate path, which lawfully covers `pure`. This
    # module is shared, so applying either policy here would impose it on both,
    # and a second copy of the check would then run in the caller anyway.
    unit_key = (unit_name, divide_flag)
    if evidence.get('hidden') and not (evidence.get('row_text')
                                       or evidence.get('block_span')):
        return None, 'hidden_without_local_evidence'
    if not reconcile(evidence.get('displayed'), evidence.get('fmt'),
                     evidence.get('scale'), evidence.get('sign'), raw_value):
        return None, 'value_does_not_reconcile'
    value = parse_raw(raw_value)
    if value is None:
        return None, 'unparsable_graph_value'
    # THE BINDER REPORTS WHAT THE FILING PRINTS AND DECLARES — nothing more.
    # A caller still binds the three FIELDS rather than a final total, because
    # {390, 10^6}, {390000000, 1} and {0.39, 10^9} all convert to the same
    # number while only one describes what this filing prints.
    # It used to compute a stored multiplier too, so that one decision had two
    # authors (and the binder's copy was not even the one Core used). The
    # declared scale VERIFIES the graph value (2.6 x 10^-2 = 0.026); turning it
    # into a stored multiplier depends on the fact's canonical unit, which only
    # Core knows — a percentage stores 2.6 with multiplier 1.
    return {'evidence': evidence, 'value': value, 'unit_name': unit_name,
            'is_divide': is_divide, 'unit_key': unit_key,
            # the filing's OWN verified measures — the caller derives base-unit
            # compatibility from these, never from the concatenated name
            'unit_numerator': tuple(declared['numerator']),
            'unit_denominator': tuple(declared['denominator']),
            'printed_value': printed_value(evidence.get('displayed'),
                                           evidence.get('fmt'),
                                           evidence.get('sign')),
            'ix_scale': int(evidence['scale']),
            'representation_sha256': prepared['text_sha']}, 'ok'
