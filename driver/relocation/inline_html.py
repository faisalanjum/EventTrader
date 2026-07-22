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

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

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


def _aligned_columns(rows, row_number, fact_cell, node_spans=None):
    """The COMPLETE aligned header stack over the exact numeric cell, near→far —
    each header returned WITH its exact source span (corrective-5: every evidence
    piece is an exact slice, never joined text)."""
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
            value = _text(cell).strip(' —-')
            if end <= target_start or start >= target_end or not value \
                    or (start == 0 and target_start > 0) or _hidden_cell(cell):
                continue                     # numeric-only headers ('2024') RETAINED
            stack.append((value, (node_spans or {}).get(id(cell))))
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
        contexts[cid] = {'period': period, 'dims': dims,
                         'typed': typed is not None,
                         'entity': _text(ident).lstrip('0') if ident else ''}
    units = {u.get('id') for u in soup.find_all(
        lambda tag: tag.name and tag.name.lower() == 'xbrli:unit') if u.get('id')}
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
    ctx = prepared['contexts'].get(ctx_ref)
    if ctx is None:
        return None, 'undefined_context'
    if ctx['typed']:
        return None, 'typed_dimensions_unsupported'
    unit_ref = el.get('unitref') or ''
    if unit_ref and unit_ref not in prepared['units']:
        return None, 'undefined_unit'
    try:
        scale = int(el.get('scale') or 0)
    except ValueError:
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
        ev['row_cells'] = [_text(item) for item in visible]
        fact_cell = cells.index(cell) if cell in cells else None
        if fact_cell is not None:
            left = [_text(item) for item in cells[:fact_cell]
                    if not _hidden_cell(item) and _words(_text(item))]
            ev['row_label'] = left[0] if left else ''   # digits in labels LEGAL
        table = row.find_parent('table')
        if table is not None:
            table_rows = [r for r in table.find_all('tr')
                          if r.find_parent('table') is table]
            if row in table_rows and fact_cell is not None:
                row_number = table_rows.index(row)
                col_pairs = _aligned_columns(table_rows, row_number, cell,
                                             prepared.get('node_spans'))
                ev['columns'] = [c for c, _ in col_pairs]
                ev['column_spans'] = [sp for _, sp in col_pairs]
                for prior in reversed(table_rows[:row_number]):
                    prior_cells = prior.find_all(['td', 'th'], recursive=False)
                    labels = [_text(item) for item in prior_cells
                              if not _hidden_cell(item) and _words(_text(item))
                              and not re.search(r'\d', _text(item))]
                    if prior_cells and not _has_number_fact(prior) \
                            and _text(prior_cells[0]) and len(labels) == 1 \
                            and not labels[0].startswith('('):
                        ev['section'] = labels[0].strip(' —-')
                        lab_cells = [item for item in prior_cells
                                     if not _hidden_cell(item)
                                     and _words(_text(item))]
                        if lab_cells:
                            ev['section_span'] = prepared.get(
                                'node_spans', {}).get(id(lab_cells[0]))
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
    try:
        value = Decimal(shown.replace(',', ''))
    except InvalidOperation:
        return None
    return -value if (sign or '') == '-' else value


def reconcile(displayed, fmt, scale, sign, raw_value):
    """displayed ∘ (format, scale, sign) == graph raw value (COMPARISON ONLY)."""
    raw = parse_raw(raw_value)
    if raw is None:
        return False
    base = printed_value(displayed, fmt, sign)
    if base is None:
        return False
    try:
        return base * (Decimal(10) ** int(scale)) == raw
    except (InvalidOperation, ValueError):
        return False
