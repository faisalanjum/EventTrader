"""Grade a conversion route against the frozen Step 3 answer key (design: grader/DESIGN.md).
Standard library only. Code only, no AI. Every answer piece is looked for at its own place in the original; matching
words anywhere in a file never count. Meaning fields (unit, scale, period role, measure) are Step 8's and are reported
as not graded here. Every tolerance is driven by the key record itself or by the labellers' guide, never by a document.

    python3 -m benchmarks.prepare.grader.grade --key <key package dir> --route <dir of per-file route json> --out <dir>
                            [--catalog case_catalog.csv] [--heldout-detail]

Route output: one JSON per source file at <route dir>/<file_id>.json in the common format of the design note."""
import argparse
from bisect import bisect_left
import csv
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata
import xml.etree.ElementTree as ET

from benchmarks.prepare.grader.anchor import Visible, norm, squash

T4 = ('value_kind', 'sign', 'marker_meaning', 'measure', 'unit_interpretation')  # meaning: Step 8, not graded here
KIND = {'heading': 'heading', 'title': 'heading', 'list_item': 'list_item', 'footnote': 'footnote', 'caption': 'caption',
        'table': 'table', 'text': 'paragraph'}
LOOSE_KINDS = ('image', 'metadata', 'other')  # reported, never a pass rule
STRUCTURE = ('heading_recognised', 'note_linked', 'reference_linked', 'kind')  # recognition counts: reported, never a pass rule
_CONTINUED = re.compile(r'\s*\((?:continued)\)', re.I)            # E2
_OPEN = ''.join(chr(i) for i in range(0x3000) if unicodedata.category(chr(i)) == 'Ps'); _CLOSE = ''.join(chr(i) for i in range(0x3000) if unicodedata.category(chr(i)) == 'Pe')
_EMPTY_BRACKETS = re.compile('[' + re.escape(_OPEN) + ']\\s*[' + re.escape(_CLOSE) + ']')
_TRAILING_BRACKET = re.compile('\\s*[' + re.escape(_OPEN) + '][^' + re.escape(_OPEN + _CLOSE) + ']*[' + re.escape(_CLOSE) + ']\\s*$')  # guide 3.5 rule 6: a bracketed unit phrase is split off a header
sha256 = lambda b: hashlib.sha256(b).hexdigest()
local = lambda name: name.rsplit('}', 1)[-1]


# ----------------------------------------------------------------------------------------------------- key loading
KEY_FILES = ('CLAUDE_ANSWER_KEY.json', 'CLAUDE_KEY_FLAGS.json', 'KEY_SUPPORT_MAP.json', 'converter_checks/REGRESSION_CASES.json')  # what grading reads from a key package


def manifest(key_dir):
    m = Path(key_dir) / 'FINAL_MANIFEST.json'
    return json.loads(m.read_text()) if m.exists() else {}


def packet_dir(bulk, name, pinned=()):
    """The folder of packet `name`: the one the frozen manifest pins, else the one that exists — never a choice between two."""
    hits = sorted({bulk / rel for rel in pinned if PurePosixPath(rel).name == name} | {d for d in (bulk / 'packets' / name, bulk / 'bundled' / 'packets' / name) if d.exists()})
    if len(hits) != 1: raise FileNotFoundError(f'{len(hits)} packet folders for {name} under {bulk}: ' + ', '.join(str(h.relative_to(bulk)) for h in hits))
    return hits[0]


def _packet(bulk, p, pinned=()):
    d = packet_dir(bulk, p, pinned)
    tj = json.loads((d / 'targets.json').read_text())
    return {'sources': {s['file_id']: (d / s['path'], s['source']['sha256']) for s in tj['sources']}, 'targets': {t['id']: t for t in tj['targets']}}


def load_key(key_dir, catalog=None):
    """Targets of the key package plus the development supplement, each with its anchors, support map and split."""
    key_dir = Path(key_dir); bulk = evidence_root(key_dir); pins = manifest(key_dir).get('packets_sha256') or {}
    records = json.loads((key_dir / 'CLAUDE_ANSWER_KEY.json').read_text())
    flags = json.loads((key_dir / 'CLAUDE_KEY_FLAGS.json').read_text())
    support = json.loads((key_dir / 'KEY_SUPPORT_MAP.json').read_text())
    excluded = {(u['key_id'], u['field'].split('.')[0]) for u in flags.get('uncertain', []) if u.get('scoring') == 'excluded'}
    catalog = Path(catalog) if catalog else bulk.parent / 'case_catalog.csv'
    with open(catalog, newline='') as f: splits = {row['source']: row['split'] for row in csv.DictReader(f)}
    packets, targets = {}, []
    for r in records:
        p = r['key_id'].split('/')[0]
        if p not in packets: packets[p] = _packet(bulk, p, pins)
        t = packets[p]['targets'][r['id']]; path, sha = packets[p]['sources'][r['file_id']]
        targets.append({'key_id': r['key_id'], 'file_id': r['file_id'], 'type': r['type'], 'path': path, 'sha256': sha,
                        'split': splits.get(r['file_id'], 'unknown'), 'fields': r['fields'], 'alternatives': r['alternatives'],
                        'anchor': t.get('cell_anchor') or t.get('block_anchor'), 'table_anchor': t.get('table_anchor'),
                        'support': support.get(r['key_id'], {}), 'excluded': {f for k, f in excluded if k == r['key_id']}})
    sup = key_dir / 'converter_checks' / 'REGRESSION_CASES.json'
    if sup.exists():
        data = json.loads(sup.read_text())
        for c in data['cases']:
            src = data['sources'][c['source_file_id']]
            targets.append({'key_id': c['id'], 'file_id': c['source_file_id'], 'type': 'cell', 'path': bulk / src['path'], 'sha256': src['sha256'],
                            'split': 'supplement', 'fields': c['expected'], 'alternatives': {}, 'anchor': c['cell_anchor'],
                            'table_anchor': c['table_anchor'], 'excluded': set(),
                            'support': {f: {'how': 'model', 'anchors': a} for f, a in c.get('field_support', {}).items() if a}})
    for t in targets:
        ext = Path(t['file_id']).suffix.lower().lstrip('.'); t['format'] = f"{t['type']}/{'htm' if ext == 'html' else ext}"
    missing = sorted({t['file_id'] for t in targets if t['split'] == 'unknown'})
    if missing: raise ValueError(f'no split assignment in {catalog} for: ' + ', '.join(missing))  # never let an unassigned file become public
    return targets


def load_sources(key_dir, catalog=None):
    """The source files of the key package with their hashes and splits — and nothing else, so a converter can be run
    without reading any answer. Packets come from the frozen manifest when there is one, else from the packet folders."""
    key_dir = Path(key_dir); bulk = evidence_root(key_dir); m = key_dir / 'FINAL_MANIFEST.json'
    catalog = Path(catalog) if catalog else bulk.parent / 'case_catalog.csv'
    with open(catalog, newline='') as f: splits = {row['source']: row['split'] for row in csv.DictReader(f)}
    listed = json.loads(m.read_text()).get('packets_sha256') if m.exists() else None
    dirs = [bulk / rel for rel in listed] if listed else [d for base in (bulk / 'packets', bulk / 'bundled' / 'packets') if base.exists() for d in sorted(base.iterdir()) if d.is_dir()]
    out, seen = [], set()
    for d in dirs:
        for src in json.loads((d / 'targets.json').read_text())['sources']:
            if src['file_id'] in seen: continue
            seen.add(src['file_id']); out.append({'file_id': src['file_id'], 'path': d / src['path'], 'sha256': src['source']['sha256'], 'split': splits.get(src['file_id'], 'unknown')})
    sup = key_dir / 'converter_checks' / 'REGRESSION_CASES.json'
    if sup.exists():
        for fid, src in json.loads(sup.read_text())['sources'].items():
            if fid not in seen: seen.add(fid); out.append({'file_id': fid, 'path': bulk / src['path'], 'sha256': src['sha256'], 'split': 'supplement'})
    missing = sorted(x['file_id'] for x in out if x['split'] == 'unknown')
    if missing: raise ValueError(f'no split assignment in {catalog} for: ' + ', '.join(missing))
    return out


def evidence_root(key_dir):
    """Where the originals live: the frozen manifest's declared root, else the key folder's parent."""
    root = manifest(key_dir).get('evidence_root')
    return (key_dir / root).resolve() if root else key_dir.parent


def verify_inputs(key_dir, catalog, route_dir):
    """Checks the inputs grading will consume against the frozen manifest before they are read: the key files, and the targets file of
    every packet the key's records use, at the folder `load_key` reads it from (source hashes are then checked per file as it is read).
    Records the identities. Without a manifest the run is marked unverified; a manifest that does not pin a consumed input, pins one
    that is missing, or disagrees with one, stops the run; `verified` also needs the split catalog pinned."""
    key_dir = Path(key_dir); m = key_dir / 'FINAL_MANIFEST.json'
    facts = {'key_package': str(key_dir), 'route_dir': str(route_dir), 'key_sha256': sha256((key_dir / 'CLAUDE_ANSWER_KEY.json').read_bytes()),
             'catalog_sha256': sha256(Path(catalog or evidence_root(key_dir).parent / 'case_catalog.csv').read_bytes()), 'manifest_sha256': None, 'verified': False, 'packets_verified': 0}
    if not m.exists(): facts['unverified_because'] = 'no frozen manifest'; return facts
    man = manifest(key_dir); listed = man.get('files_sha256') or {}; facts['manifest_sha256'] = sha256(m.read_bytes())
    for rel in KEY_FILES:  # pinned and present, or neither: a pinned file that is missing is a declared input lost
        if (rel in listed) != (key_dir / rel).exists(): raise ValueError(f'{rel} is ' + (f'pinned by the frozen manifest of {key_dir.name} but missing' if rel in listed else f'not pinned by the frozen manifest of {key_dir.name}'))
        if rel in listed and sha256((key_dir / rel).read_bytes()) != listed[rel]: raise ValueError(f'{rel} differs from the frozen manifest of {key_dir.name}')
    root, pins = evidence_root(key_dir), man.get('packets_sha256') or {}
    used = sorted({r['key_id'].split('/')[0] for r in json.loads((key_dir / 'CLAUDE_ANSWER_KEY.json').read_text())})
    if not used: raise ValueError(f'{key_dir.name}: the answer key names no packet')
    for name in used:  # the packets grading consumes, at the folders it will read them from
        rel = packet_dir(root, name, pins).relative_to(root).as_posix()
        if 'targets_sha256' not in (pins.get(rel) or {}): raise ValueError(f'frozen manifest of {key_dir.name} does not pin {rel}/targets.json')
    for rel, pin in pins.items():  # and every pinned packet file must be the pinned bytes
        for fname, key in (('targets.json', 'targets_sha256'), ('manifest.json', 'manifest_sha256')):
            if key in pin and sha256((root / rel / fname).read_bytes()) != pin[key]: raise ValueError(f'{rel}/{fname} differs from the frozen manifest')
    facts['packets_verified'] = len(used)
    pin = man.get('catalog_sha256')  # the split list decides what is public: unpinned, the run is not verified; pinned and changed, it does not run
    if pin is None: facts['unverified_because'] = 'catalog (split assignments) not pinned by the frozen manifest'; return facts
    if pin != facts['catalog_sha256']: raise ValueError(f'case_catalog.csv differs from the frozen manifest of {key_dir.name}')
    facts['verified'] = True
    return facts



def anchors_of(t, field, alt=None):
    """Every source location the key records for a field value (its own pieces; search pieces: all occurrences)."""
    s = t['support'].get(f'{field}#{alt}' if alt is not None else field) or t['support'].get(field) or {}
    out = []
    for a in s.get('anchors') or []:
        out.append({'file': a['file_id'], 'region': a['region']} if 'region' in a and 'file_id' in a else a)
    for piece in s.get('pieces') or []:
        for a, b in (piece.get('governing') or []) + (piece.get('byte_ranges') or []): out.append({'byte_start': a, 'byte_end_exclusive': b})
    return out


# -------------------------------------------------------------------------------------------------------- geometry
def spans(anchor):
    """An anchor is one place or, for a cell that sits in several source places, a list of them."""
    return anchor if isinstance(anchor, list) else [anchor] if isinstance(anchor, dict) else []


def _ratio(a, b):
    if 'byte_start' in a and 'byte_start' in b:
        return float(a['byte_start'] < b['byte_end_exclusive'] and b['byte_start'] < a['byte_end_exclusive'])
    if 'region' in a and 'region' in b:
        if a.get('page') != b.get('page') or Path(str(a.get('file'))).name != Path(str(b.get('file'))).name: return 0.0
        (x0, y0, x1, y1), (u0, v0, u1, v1) = a['region'], b['region']
        inter = max(0, min(x1, u1) - max(x0, u0)) * max(0, min(y1, v1) - max(y0, v0))
        smaller = min((x1 - x0) * (y1 - y0), (u1 - u0) * (v1 - v0))
        return inter / smaller if smaller > 0 else 0.0
    return 0.0


def overlap_ratio(a, b):
    """Bytes: 1 if the ranges intersect. Boxes (same page or picture file): shared area over the smaller box."""
    return max([_ratio(x, y) for x in spans(a) for y in spans(b)] or [0.0])


def overlap(a, b):
    return overlap_ratio(a, b) >= 0.5


def order_key(a):
    a = (spans(a) or [{}])[0]
    return (0, a['byte_start']) if 'byte_start' in a else (a.get('page') or 0, a['region'][1] if 'region' in a else 0)


def source_before(a, b):
    """Is a printed before b? Bytes by offset; boxes sharing a row left to right, otherwise page then top to bottom."""
    a, b = (spans(a) or [{}])[0], (spans(b) or [{}])[0]
    if 'byte_start' in a and 'byte_start' in b: return a['byte_start'] < b['byte_start']
    if 'region' in a and 'region' in b:
        if a.get('page') != b.get('page'): return (a.get('page') or 0) < (b.get('page') or 0)
        (x0, y0, x1, y1), (u0, v0, u1, v1) = a['region'], b['region']
        return x0 < u0 if min(y1, v1) > max(y0, v0) else y0 < v0
    return order_key(a) < order_key(b)


# ------------------------------------------------------------------------------------------------- route per file
class RouteFile:
    """One route output file with lookups by location."""

    def __init__(self, data, raw, fmt=None):
        self.data, self.units = data, data.get('units') or []
        for i, u in enumerate(self.units): u['_order'] = i
        self.cells = [(u, c) for u in self.units if u.get('kind') == 'table' for c in u.get('cells') or []]
        self.by_id = {u['id']: u for u in self.units if 'id' in u}
        ext = '.' + fmt.lower().lstrip('.') if fmt else Path(data['file_id']).suffix.lower()  # the key's declared format decides the checking mode
        self.vis = Visible(raw, xml=ext == '.xml') if raw is not None and ext in ('.htm', '.html', '.xml', '.txt') else None  # PDFs/pictures: geometry only
        self.raw, self.raw_len = raw, (len(raw) if raw is not None else None)
        self.pages = {int(k): v for k, v in (data.get('pages') or {}).items()}  # page sizes [width, height] declared by the route, if any
        # byte index: cells sorted by first byte, with the longest span, so a lookup scans a small window
        byte_cells = [(min(a['byte_start'] for a in sp), max(a['byte_end_exclusive'] for a in sp), u, c)
                      for u, c in self.cells for sp in [[a for a in spans(c.get('anchor')) if 'byte_start' in a]] if sp]
        byte_cells.sort(key=lambda x: x[0])
        self._starts, self._byte_cells = [x[0] for x in byte_cells], byte_cells
        self._max_len = max([e - b for b, e, _, _ in byte_cells], default=0)
        self._box_cells = [(u, c) for u, c in self.cells if any('region' in a for a in spans(c.get('anchor')))]

    def units_at(self, anchor, kinds=None, exclude=('table', 'clutter')):
        return [u for u in self.units if u.get('kind') not in exclude and (kinds is None or u.get('kind') in kinds) and overlap(u.get('anchor'), anchor)]

    def cells_at(self, anchor, table=None):
        """Cells overlapping an anchor, from one table or any. Touching PDF boxes: only the best-overlapping cells."""
        first = (spans(anchor) or [{}])[0]
        if 'byte_start' in first:
            lo, hi = min(a['byte_start'] for a in spans(anchor)), max(a['byte_end_exclusive'] for a in spans(anchor))
            i, j = bisect_left(self._starts, lo - self._max_len), bisect_left(self._starts, hi)
            pool = [(u, c) for _, _, u, c in self._byte_cells[i:j]]
        else:
            pool = self._box_cells
        hits = [(overlap_ratio(c.get('anchor'), anchor), c) for u, c in pool if table is None or u is table]
        hits = [(r, c) for r, c in hits if r >= 0.5]
        if hits and 'region' in first: hits = [(r, c) for r, c in hits if r == max(r for r, _ in hits)]
        return [c for _, c in hits]

    def table_of(self, cell):
        return next(u for u, c in self.cells if c is cell)

    def cells_in(self, table):
        return table.get('cells') or []


# ------------------------------------------------------------------------------------------------ small helpers
def pieces_of(value):
    """The key's display joins are the key's: ' | ' separates pieces; a list is its pieces."""
    if value is None: return []
    if isinstance(value, str): return [p for p in value.split(' | ')]
    return [p for v in value for p in pieces_of(v)]


def alternatives(t, field):
    """Accepted values of a field: the fixed value, or every listed alternative (any one may pass)."""
    if field in t['alternatives']: return [(i, v) for i, v in enumerate(t['alternatives'][field])]
    return [(None, t['fields'].get(field))] if field in t['fields'] else []


def row_hit(cell, r):
    return cell['r'] <= r < cell['r'] + cell.get('rs', 1)


def col_hit(cell, cols):
    """Does the cell's column span touch the value's columns (a single column or a (first, end) range)?"""
    lo, hi = cols if isinstance(cols, tuple) else (cols, cols + 1)
    return cell['c'] < hi and lo < cell['c'] + cell.get('cs', 1)


def joined(cells):
    return norm(' '.join(c.get('text', '') for c in sorted(cells, key=lambda c: (c['r'], c['c']))))


def minus_markers(text, markers):
    """The text without the target's own footnote marks at its ends (a mark glued to a label or title)."""
    text = norm(text)
    for m in sorted((norm(m) for m in markers if m), key=len, reverse=True):
        if text.endswith(m): text = text[:-len(m)].rstrip()
        elif text.startswith(m): text = text[len(m):].lstrip()
    return text


def minus_marks_anywhere(text, markers):
    """The text with the record's own footnote marks deleted wherever they stand, with the commas or spaces between grouped marks (guide 3.2)
    and the space before them: the gap a mark leaves closes up ("features(1):" reads "features:", "Covenants (1)" reads "Covenants")."""
    marks = sorted({re.escape(norm(m)) for m in markers if norm(m)}, key=len, reverse=True)
    if not marks: return norm(text)
    one = '(?:' + '|'.join(marks) + ')'
    return norm(re.sub(r'\s*' + one + '(?:\s*,?\s*' + one + ')*', '', norm(text)))


def without_marks(got, want, markers):
    """Is `got` the key text `want` with the record's own footnote marks printed into it? Marks may sit anywhere — glued to a word, before a
    colon, grouped with commas or spaces between (guide 3.2) — and the space a mark leaves behind closes up. A mark that is part of `want`
    itself is never deleted: every other character of `got` must match `want` in order."""
    g, w = norm(got), norm(want); marks = sorted({norm(m) for m in markers if norm(m)}, key=len, reverse=True)
    if g == w: return True
    if not marks or len(g) <= len(w) or not any(m in g for m in marks): return False  # cheap exits: nothing to delete
    if not any(m in w for m in marks) and squash(minus_marks_anywhere(g, markers)) != squash(w): return False  # when no mark string is part of the key text, deleting them all must leave exactly the key text
    at = {0: {(0, False)}}  # positions of `got` reached → (position in `want`, gap: the previous character of `got` was deleted — a mark or its separator); forward, no recursion
    for i in range(len(g)):
        for j, gap in at.pop(i, ()):
            for m in marks:
                if g.startswith(m, i):
                    k = i + len(m); at.setdefault(k, set()).add((j, True))
                    for sep in (', ', ',', ' '):  # the next mark of a group
                        if g.startswith(sep, k) and any(g.startswith(m2, k + len(sep)) for m2 in marks): at.setdefault(k + len(sep), set()).add((j, True))
            if g[i] == ' ' and (any(g.startswith(m, i + 1) for m in marks) or (gap and (j == len(w) or w[j] != ' '))): at.setdefault(i + 1, set()).add((j, gap))
            if j < len(w) and g[i] == w[j]: at.setdefault(i + 1, set()).add((j + 1, False))
    return any(j == len(w) for j, gap in at.get(len(g), ()))


def same(got, want, markers=(), own=()):
    """Equal text; else equal once the target's own marks, a trailing bracketed unit phrase, or the record's own other
    literal pieces (its unit line, basis words, period phrases) are set aside (each flagged)."""
    got, want = norm(got), norm(want)
    if boundary_equal(got, want): return True, None
    if without_marks(got, want, markers): return True, 'marker_in_text'
    if norm(own_bracket_off(minus_markers(got, markers), own)) == want: return True, 'unit_phrase_split'
    rest = minus_markers(got, markers)
    for piece in sorted((norm(x) for x in own if x and norm(x) != want), key=len, reverse=True): rest = rest.replace(piece, ' ')
    rest = minus_markers(_EMPTY_BRACKETS.sub(' ', rest), markers)  # brackets left empty, and marks now at an end, set aside too
    if norm(rest) == want or norm(own_bracket_off(norm(rest), own)) == want or without_marks(own_bracket_off(norm(rest), own), want, markers): return True, 'joined_with_own_pieces'
    return False, None


_STRUCK = re.compile(r'~~(.+?)~~', re.S)


def strings_in(value):
    """Every string inside a field value (a string, a list of pieces, period groups, context items)."""
    if isinstance(value, str): return [value]
    if isinstance(value, dict): return [x for v in value.values() for x in strings_in(v)]
    if isinstance(value, list): return [x for v in value for x in strings_in(v)]
    return []


def struck_kept(key_texts, items):
    """When the key marks words struck (~~…~~), the route must report the same words struck at that place and no others: struck evidence
    stays struck and never becomes active text (key README). Items are the cells or units that carry the text."""
    want = ''.join(squash(m) for t in key_texts for m in _STRUCK.findall(t or ''))
    scope = squash(' '.join(_STRUCK.sub(r'\1', t or '') for t in key_texts))  # the field's own text: a strike elsewhere in a shared unit is not this field's
    got = ''.join(s for it in items for x in (it.get('struck') or []) for s in [squash(x)] if s and s in scope)  # in reading order; a phrase the route splits into pieces still reads whole
    return got == want  # a lost, partial, extra or invented cancellation all change what the reader is told


def own_bracket_off(text, own):
    """The text without a trailing bracketed phrase, only when that phrase is one of the record's own pieces (E13: its unit line
    or basis words); any other parenthetical stays and must match."""
    m = _TRAILING_BRACKET.search(text)
    if not m: return text
    inner = norm(m.group()).strip(); bare = inner[1:-1].strip() if len(inner) > 1 else inner
    mine = {norm(x) for x in own if x}
    return text[:m.start()] if mine & {inner, bare, norm(text)} else text  # the bracket, or the whole line, is a declared own piece


_TOKEN_WORDS = re.compile(r'\d(?:[\d.,]*\d)?|\w+')  # the words and numbers of a text, by Unicode category; numbers keep their separators


def tokens(text):
    return _TOKEN_WORDS.findall(norm(text))


def boundary_equal(got, want):
    """Same characters and the same words and numbers: whitespace may move around punctuation and symbols (E12 reflow), but a
    boundary inside a word or a number may not appear or disappear."""
    return squash(got) == squash(want) and tokens(got) == tokens(want)


def objects(carriers):
    """The route objects (cells or units, every piece of a glued run) behind these carriers."""
    return [o for k in carriers for o in (k.get('parts') or [k['cell'] if k.get('cell') is not None else k.get('unit')])]


def spaced(item):
    """The item's text with a space at every join where touching pieces were read as one. Not a second reading that may pass: the comparison
    uses it only to tell a word boundary the page alone could show (CSS spacing of touching bytes — unresolved) from a real mismatch (fail)."""
    text, joins = item.get('text', ''), item.get('joins') or []
    if not joins: return text
    idx = [i for i, c in enumerate(text) if not c.isspace()]; out, last = [], 0
    for j in joins:
        cut = idx[j] if j < len(idx) else len(text); out.append(text[last:cut]); last = cut
    out.append(text[last:]); return ' '.join(out)


def contains(text, want):
    """Is `want` printed inside `text`? By the boundary rule on the matching stretch: whitespace may move around punctuation and symbols,
    never inside a word or a number."""
    nt, nw = norm(text), norm(want)
    if nw in nt: return True
    idx = [i for i, c in enumerate(nt) if not c.isspace()]; st = ''.join(nt[i] for i in idx); sw = squash(nw)
    if not sw: return True
    p = st.find(sw)
    while p != -1:
        if boundary_equal(nt[idx[p]:idx[p + len(sw) - 1] + 1], nw): return True
        p = st.find(sw, p + 1)
    return False


def fused(texts, want):
    """Do these cell texts, in order and separated by cell boundaries, spell `want`? The characters must match exactly and no
    word or number may be split or glued across a cell boundary (symbol cells beside a number are fine)."""
    return boundary_equal(' '.join(x for x in texts if norm(x)), want)


def spacing_only(got, want):
    """Same characters, a word or number boundary broken or glued by the tool."""
    return squash(got) == squash(want) and not boundary_equal(got, want)


def match_pieces(texts, pieces, markers=(), own=()):
    """Align the key's pieces, in order, to the tool's cell texts, in order: a piece may span several consecutive
    cells (stacked fragments) and a cell may carry the target's own mark or a trailing bracketed unit phrase."""
    def go(i, j, flag):
        if i == len(pieces): return (True, flag) if j == len(texts) else (False, None)
        if j == len(texts): return False, None
        for k in range(j + 1, len(texts) + 1):  # one piece over one or more cells (stacked fragments)
            ok, f = same(' '.join(texts[j:k]), pieces[i], markers, own)
            if ok:
                done, flag2 = go(i + 1, k, flag or f)
                if done: return True, flag2
        for m in range(i + 2, len(pieces) + 1):  # several pieces merged into one cell
            ok, f = same(texts[j], ' '.join(pieces[i:m]), markers, own)
            if ok:
                done, flag2 = go(m, j + 1, flag or f)
                if done: return True, flag2
        return False, None
    return go(0, 0, None)


def xml_element_at(raw, byte_offset):
    """The expanded name ({namespace}local) of the element whose character data covers `byte_offset` in the XML source;
    None when the source does not parse. Expat reports byte positions, so the occurrence is exact, not a sibling with the same
    name; a data chunk ends where the next parser event starts, so entities inside the text do not shift it."""
    import xml.parsers.expat as expat
    p = expat.ParserCreate(namespace_separator='}'); stack, open_chunk, found = [], [], []
    def close(end):
        if open_chunk and open_chunk[0] <= byte_offset < end: found.append(open_chunk[1])
        open_chunk.clear()
    def start(name, attrs): close(p.CurrentByteIndex); stack.append(name)
    def end(name): close(p.CurrentByteIndex); stack.pop()
    def data(text):
        if open_chunk and open_chunk[1] == stack[-1]: return  # the same element's text continues
        close(p.CurrentByteIndex); open_chunk[:] = [p.CurrentByteIndex, stack[-1]]
    p.StartElementHandler, p.EndElementHandler, p.CharacterDataHandler = start, end, data
    try: p.Parse(raw, True)
    except expat.ExpatError: return None
    close(len(raw))
    if not found: return None
    return ('{' + found[0]) if '}' in found[0] else found[0]


def marks_off(text, markers):
    """The text without the reported marks at its ends, keeping its inner spacing (for the boundary check at an anchor)."""
    text = norm(text)
    for m in sorted((norm(m) for m in markers if m), key=len, reverse=True):
        if m and text.startswith(m): text = text[len(m):].lstrip()
        elif m and text.endswith(m): text = text[:-len(m)].rstrip()
    return text


def anchor_of(k):
    """The source anchor of a carrier: its cell's, else its unit's."""
    return (k['cell'] or k['unit'] or {}).get('anchor')


def heading_eq(a, b):
    """E2: "X (continued)" is X, on either side; spacing by the boundary rule (reflow at punctuation and symbols)."""
    return boundary_equal(_CONTINUED.sub('', norm(a)), _CONTINUED.sub('', norm(b)))


def wer(a, b):
    x, y = norm(a).split(), norm(b).split()
    return round(1 - difflib.SequenceMatcher(None, x, y).ratio(), 3)


# ------------------------------------------------------------------------------------------------- grading one
class Grader:
    def __init__(self, t, rf):
        self.t, self.rf, self.rows = t, rf, []
        self.markers = [m['marker_text'] for _, v in alternatives(t, 'footnote_markers') for m in (v or [])]
        self.own = [p for f in ('unit_printed', 'segment_or_basis', 'corner_text', 'table_title', 'row_label') for _, v in alternatives(t, f) for p in pieces_of(v)]
        self.own += [part['text'] for _, v in alternatives(t, 'periods') for g in (v or []) for part in g.get('parts') or []]
        # table context the key declares for this table (E13, addendum C1): admitted only for the table's heading block — title, header
        # path, corner — and only when every declared anchor reads the phrase inside the table or in its title block (from the declared
        # title's anchor to the table's end: a title printed in an outer cell above a nested data table); anything else is a key defect
        ta = t.get('table_anchor') or {}; self.table_context = []
        lo = min([ta['byte_start']] + [a['byte_start'] for a in anchors_of(t, 'table_title') if 'byte_start' in a]) if 'byte_start' in ta else None
        for pc in (t['support'].get('table_context') or {}).get('pieces') or []:
            at = pc.get('byte_ranges') or []
            if not (pc.get('text') and at and rf.vis is not None and lo is not None and
                    all(lo <= a < b <= ta['byte_end_exclusive'] and squash(rf.vis.at(a, b)) == squash(pc['text']) for a, b in at)):
                raise ValueError(f"{t['key_id']}: table_context {pc.get('text')!r} is not the text at an anchor inside this table or its title block (fix the key package)")
            self.table_context.append(pc['text'])

    def same(self, got, want):
        return same(got, want, self.markers, self.own)

    def row(self, check, verdict, reason=None, detail=None):
        self.rows.append({'key_id': self.t['key_id'], 'file_id': self.t['file_id'], 'split': self.t['split'], 'format': self.t['format'],
                          'check': check, 'verdict': verdict, 'reason': reason, 'detail': detail})

    def field(self, name, fn, *args):
        """Run one check over every accepted value; the first passing value wins, else the first failure is reported."""
        if name in self.t['excluded']: return self.row(name, 'excluded')
        alts = alternatives(self.t, name)
        if not alts: return
        results, matched = [], []
        for alt, value in alts:
            if value in (None, [], {}): return self.row(name, 'na')
            self.matched = None  # a field may say which carriers matched; the struck check then reads those, not every occurrence the key points at
            results.append(fn(value, alt, *args)); matched.append(self.matched)
            if results[-1][0] == 'pass': break
        verdict, reason, detail = results[-1] if results[-1][0] == 'pass' else results[0]
        if verdict == 'pass':  # struck words the key marks must still be struck where the route carries them
            alt, value = alts[len(results) - 1]; anchors = anchors_of(self.t, name, alt)
            items = matched[len(results) - 1] or ([c for a in anchors for c in self.rf.cells_at(a)] + [c for a in anchors for u in self.rf.units_at(a, exclude=('clutter',)) for c in ([x for x in self.rf.cells_in(u) if any(overlap(x.get('anchor'), b) for b in anchors)] if u.get('kind') == 'table' else [u])] if anchors else (self.rf.cells_in(self.tb) if getattr(self, 'tb', None) else []))  # the matched carriers; else a table at the anchor contributes only the cells at this field's support, never another row's strikes
            items = list({id(x): x for x in items if x is not None}.values())
            if not struck_kept(strings_in(value), items): verdict, reason, detail = 'fail', 'struck', None
        self.row(name, verdict, reason, detail)

    # ---- cells
    def grade_cell(self):
        t, rf = self.t, self.rf
        if t['format'].endswith('/xml'): return self.grade_xml()
        hits = rf.cells_at(t['anchor'])
        if not hits: return None
        tb = rf.table_of(hits[0]); V = [c for c in hits if rf.table_of(c) is tb]
        vr, vcols = V[0]['r'], (min(c['c'] for c in V), max(c['c'] + c.get('cs', 1) for c in V))
        self.tb, self.V, self.vr, self.vcols, self.ctx_orders = tb, V, vr, vcols, set()
        self.value(tb, V, vr)
        self.field('row_label', self.row_label, tb, vr)
        self.field('row_context', self.row_context, tb, vr)
        self.field('header_path', self.header_path, tb, vr, vcols)
        self.field('table_title', self.table_title, tb, vr)
        self.field('corner_text', self.corner_text, tb, vr)
        self.field('lead_in', self.lead_in, tb, vr)
        self.field('section_path', self.section_path, tb['_order'], tb)
        self.field('segment_or_basis', self.basis, tb, vr)
        self.field('unit_printed', self.unit_printed, tb, vr, V)
        self.field('periods', self.periods, tb, vr, vcols)
        self.field('footnote_markers', self.footnotes, tb, V, vr)
        self.field('range', self.range_, tb, V, vr, vcols)
        for f in T4:
            if f in t['fields']: self.row(f, 'excluded' if f in t['excluded'] else 'not_t1')
        return tb

    def carriers(self, anchors, pieces=(), tb=None, equal=True):
        """Where the key's text lives in the route output: cells of any table and text units at the key's anchors
        (without anchors: cells of the value's table or units whose text matches a piece). Sorted in reading order."""
        found = []
        if anchors:
            for a in anchors:
                found += [(self.rf.table_of(c), c, None) for c in self.rf.cells_at(a)]
                found += [(None, None, u) for u in self.rf.units_at(a)]
        else:
            want = [norm(p) for p in pieces]
            hit = (lambda s: any(self.same(s, w)[0] for w in want)) if equal else (lambda s: any(contains(s, w) for w in want))
            found += [(tb, c, None) for c in (self.rf.cells_in(tb) if tb else []) if hit(c.get('text', ''))]
            found += [(None, None, u) for u in self.rf.units if u.get('kind') not in ('table', 'clutter') and hit(u.get('text', ''))]
        out, seen = [], set()
        for table, cell, unit in found:
            key = id(cell if cell is not None else unit)
            if key in seen: continue
            seen.add(key)
            out.append({'text': (cell or unit).get('text', ''), 'order': (table or unit)['_order'], 'table': table, 'cell': cell, 'unit': unit,
                        'anchor': (cell or unit).get('anchor')})
        out = sorted(out, key=lambda k: (k['order'], k['cell']['r'] if k['cell'] else -1, k['cell']['c'] if k['cell'] else -1, order_key(k['anchor'])))
        merged = []  # pieces that touch in the source — cells at one grid position, or text units — are one carrier (E12: the source proves nothing between them); a piece with no characters is never glued; the first piece's object is kept
        for k in out:
            p = merged[-1] if merged else None
            same_place = p is not None and ((k['cell'] is not None and p['cell'] is not None and p['table'] is k['table'] and (p['cell']['r'], p['cell']['c']) == (k['cell']['r'], k['cell']['c']))
                                            or (k['cell'] is None and p['cell'] is None))
            if same_place and squash(p['text']) and squash(k['text']) and self.adjacent(p['anchor'], k['anchor']): merged[-1] = dict(p, text=p['text'] + k['text'], anchor=spans(p['anchor']) + spans(k['anchor']), joins=(p.get('joins') or []) + [len(squash(p['text']))], parts=(p.get('parts') or [p['cell'] if p['cell'] is not None else p['unit']]) + [k['cell'] if k['cell'] is not None else k['unit']])
            else: merged.append(k)
        return merged

    def merged_units(self, units):
        """Text units in order; consecutive units whose anchors touch in the source (span-level output) are read as one; others stay apart;
        a unit with no characters is never glued."""
        out = []
        for u in sorted(units, key=lambda u: (u.get('_order', 0), order_key(u.get('anchor')))):
            p = out[-1] if out else None
            if p is not None and u.get('kind') != 'table' and p.get('kind') != 'table' and squash(p.get('text', '')) and squash(u.get('text', '')) and self.adjacent(p.get('anchor'), u.get('anchor')):
                out[-1] = dict(p, text=p.get('text', '') + u.get('text', ''), anchor=spans(p.get('anchor')) + spans(u.get('anchor')), struck=(p.get('struck') or []) + (u.get('struck') or []), links=(p.get('links') or []) + (u.get('links') or []), joins=(p.get('joins') or []) + [len(squash(p.get('text', '')))])
            else: out.append(u)
        return out

    def merged(self, cells):
        """Cells in reading order; consecutive pieces at one grid position whose anchors touch in the source are read as one cell
        (E12, span-level output), every other cell stays apart. The first piece's cell object is kept, so identity checks still hold."""
        out = []
        for c in sorted(cells, key=lambda c: (c['r'], c['c'], order_key(c.get('anchor')))):
            p = out[-1] if out else None
            if p is not None and (p['r'], p['c']) == (c['r'], c['c']) and self.adjacent(p.get('anchor'), c.get('anchor')):
                out[-1] = dict(p, text=p.get('text', '') + c.get('text', ''), anchor=spans(p.get('anchor')) + spans(c.get('anchor')), markers=(p.get('markers') or []) + (c.get('markers') or []), struck=(p.get('struck') or []) + (c.get('struck') or []), joins=(p.get('joins') or []) + [len(squash(p.get('text', '')))])
            else: out.append(c)
        return out

    def adjacent(self, a, b):
        """Does the output's own mapping put piece b right after piece a in the source, with nothing (not even a space) between?"""
        sa, sb = [x for x in spans(a) if 'byte_start' in x], [x for x in spans(b) if 'byte_start' in x]
        if not sa or not sb or self.rf.vis is None: return False
        end, start = max(x['byte_end_exclusive'] for x in sa), min(x['byte_start'] for x in sb)
        return end <= start and self.rf.vis.at(end, start) == ''

    def pieces_match(self, texts, want, anchors=None, cells=None):
        """Do these route pieces, in order, spell the key text `want`? Joins are read from the source alone: pieces whose anchors touch read
        as one, every other join as a space. A piece boundary inside a word of the key is a fault unless the pieces touch in the source
        (E12: span-level output; counted as `fragmented`) — and, for table cells, unless both pieces sit at one grid position: two cells
        show two words whatever the bytes say. Where touching pieces meet inside what the key prints as two words, the page may space them
        (CSS): reported unresolved, never pass or fail. Returns (ok, reason, fragments); ok None = unresolved."""
        nw = norm(want); idx = [i for i, c in enumerate(nw) if not c.isspace()]; sq = ''.join(nw[i] for i in idx); pos = frag = 0; prev = None
        out, pending, ambiguous = '', False, False  # the pieces as the source prints them: a proven touching join reads as nothing, every other join as a space
        for n_, tx in enumerate(texts):
            n = len(squash(tx)); end = pos + n
            if not n: continue
            if not sq.startswith(squash(tx), pos): return False, 'text', frag
            sep = ''
            if prev is not None:
                apart = bool(cells) and (cells[prev]['r'], cells[prev]['c']) != (cells[n_]['r'], cells[n_]['c'])  # two cells show two words whatever the bytes say
                touching = not apart and bool(anchors) and self.adjacent(anchors[prev], anchors[n_])
                glue = idx[pos] == idx[pos - 1] + 1  # the key prints no space here
                if glue and touching: frag += 1
                elif glue and not apart and bool(anchors) and all(any('region' in x for x in spans(anchors[i])) for i in (prev, n_)): pending = True  # boxes cannot prove the join
                elif glue and nw[idx[pos]].isalnum() and nw[idx[pos - 1]].isalnum(): return False, 'word_split', frag  # a word or number split without proof
                elif touching: ambiguous = ambiguous or (nw[idx[pos]].isalnum() and nw[idx[pos - 1]].isalnum())  # the bytes touch where the page prints a space: CSS may space them; a word boundary only the page shows cannot be certified from the output
                else: sep = ' '
            out += sep + norm(tx); pos, prev = end, n_
        if pos != len(sq): return False, 'text', frag
        if pending: return None, 'adjacency', frag
        if boundary_equal(out, nw): return True, None, frag
        return (None, 'adjacency', frag) if ambiguous and spacing_only(out, nw) else (False, 'spacing', frag)

    def in_order(self, k, tb, vr):
        """A carrier inside the value's table keeps the source order of rows; outside, it comes before the table."""
        if k['table'] is tb: return k['cell']['r'] == vr or (k['cell']['r'] < vr) == source_before(k['anchor'], self.t['anchor'])
        return k['order'] < tb['_order']

    def value(self, tb, V, vr):
        t = self.t; printed, display = t['fields'].get('printed_value'), t['fields'].get('display_value') or t['fields'].get('printed_value')
        cells = sorted(V, key=lambda c: c['c']); texts = [c.get('text', '') for c in cells]
        if self.spell(cells, printed) is not True and any(fused(texts, printed + m) or fused(texts, m + printed) for m in self.markers): return self.row('value', 'fail', 'marker_glued')
        danch = anchors_of(t, 'display_value')
        D = list({id(c): c for a in danch for c in self.rf.cells_at(a, tb)}.values()) or V
        if any(not row_hit(c, vr) for c in D): return self.row('value', 'fail', 'symbol_detached')
        shown = sorted(D, key=lambda c: c['c']); said = (self.spell(shown, display), self.spell(cells, display), self.spell(cells, printed))
        if True in said[:2]: return self.row('value', 'pass')
        if said[2] is True: return self.row('value', 'fail', 'symbol_missing', joined(shown))
        if None in said: return self.row('value', 'unresolved', 'adjacency')  # pieces of the value whose page boxes cannot prove adjacency
        if squash(''.join(texts)) in (squash(printed), squash(display)) or squash(joined(shown)) == squash(display): return self.row('value', 'fail', 'spacing', norm(' '.join(texts)))
        self.row('value', 'fail', 'text', norm(' '.join(texts)))

    def spell(self, cells, want):
        """Do these cells, in column order, spell `want`? Pieces at one grid position may join inside a word when their anchors prove
        source adjacency (E12); pieces in different cells never do. True, False, or None when only page boxes could prove the join."""
        return self.pieces_match([c.get('text', '') for c in cells], want, [c.get('anchor') for c in cells], cells)[0]

    def row_label(self, value, alt, tb, vr):
        pieces, anchors = pieces_of(value), anchors_of(self.t, 'row_label', alt)
        cands = [c for a in anchors for c in self.rf.cells_at(a, tb)] if anchors else \
            [c for c in self.rf.cells_in(tb) if abs(c['r'] - vr) <= 1 and norm(c.get('text', '')) in {norm(p) for p in pieces}]
        cands = self.merged({id(c): c for c in cands}.values())
        if not cands: return 'fail', 'missing', None
        ok, flag = self.same(joined(cands), ' '.join(pieces))
        if not ok and any(c.get('joins') for c in cands) and self.same(norm(' '.join(spaced(c) for c in sorted(cands, key=lambda c: (c['r'], c['c'])))), ' '.join(pieces))[0]: return 'unresolved', 'adjacency', joined(cands)
        if not ok: return 'fail', 'text', joined(cands)
        if not any(row_hit(c, vr) for c in cands) or any(abs(c['r'] - vr) > 1 for c in cands): return 'fail', 'row', None
        self.matched = list(cands)  # merged cells carry their pieces' strikes
        return 'pass', None, 'marker_in_label' if flag == 'marker_in_text' else flag or ('anchor_unknown' if not anchors else None)

    def row_context(self, value, alt, tb, vr):
        pool = self.merged(self.rf.cells_in(tb))
        for item in value:
            cells = [c for c in pool if row_hit(c, vr) and self.same(c.get('text', ''), item['text'])[0]]  # a row may print the same text twice: the one under the named header is meant
            if not cells: return ('unresolved', 'adjacency', item['text']) if any(row_hit(c, vr) and c.get('joins') and self.same(spaced(c), item['text'])[0] for c in pool) else ('fail', 'row', item['text'])
            if item.get('header') and item['header'] != 'position':
                heads = [c for c in pool if c['r'] < vr] + [k['cell'] for k in self.carriers(anchors_of(self.t, 'row_context', alt), [item['header']])
                                                                           if k['cell'] is not None and k['table'] is not tb and k['order'] < tb['_order']]  # or printed in the first part of a continued table (E1, addendum C5)
                if not any(col_hit(h, c['c']) and self.same(h.get('text', ''), item['header'])[0] for c in cells for h in heads):
                    if any(col_hit(h, c['c']) and h.get('joins') and self.same(spaced(h), item['header'])[0] for c in cells for h in heads): return 'unresolved', 'adjacency', item['header']
                    return 'fail', 'header', item['header']
        return 'pass', None, None

    def header_path(self, value, alt, tb, vr, vcols):
        pieces, anchors = pieces_of(value), anchors_of(self.t, 'header_path', alt)
        cars = [k for k in self.carriers(anchors, pieces, tb) if k['cell'] is not None]
        own = [k for k in cars if k['table'] is tb and k['cell']['r'] < vr]
        other = [k for k in cars if k['table'] is not tb and k['order'] < tb['_order']]  # the first part of a continued table
        for cands, flag in ((own, None), (own + other, 'continued_table' if other else None)):
            if not cands: continue
            cands = sorted(cands, key=lambda k: (k['order'], k['cell']['r'], k['cell']['c']))
            if len(cands) > len(pieces):  # the key's anchors name a heading printed twice above the value: the copy nearest the value is the path's
                once = {norm(p) for p in pieces if sum(norm(q) == norm(p) for q in pieces) == 1}; nearest = {}
                for k in cands: nearest[norm(k['text'])] = k
                cands = sorted((k for k in cands if norm(k['text']) not in once or nearest[norm(k['text'])] is k), key=lambda k: (k['order'], k['cell']['r'], k['cell']['c']))
            ok, f = match_pieces([k['text'] for k in cands], pieces, self.markers, self.own + self.table_context)
            if not ok:
                if any(k.get('joins') for k in cands) and match_pieces([spaced(k) for k in cands], pieces, self.markers, self.own + self.table_context)[0]: return 'unresolved', 'adjacency', None
                continue
            if any(not col_hit(k['cell'], vcols) for k in cands): return 'fail', 'column', None
            self.ctx_orders.update(k['order'] for k in cands); self.matched = objects(cands)
            return 'pass', None, flag or f or ('anchor_unknown' if not anchors else None)
        if not cars: return 'fail', 'missing', None
        return 'fail', 'text', ' '.join(k['text'] for k in cars)

    def table_title(self, value, alt, tb, vr):
        pieces, anchors = pieces_of(value), anchors_of(self.t, 'table_title', alt)
        if norm(' '.join(tb.get('caption') or [])) == norm(' '.join(pieces)): return 'pass', None, 'caption'
        cars = self.carriers(anchors, pieces, tb)
        usable = [k for k in cars if (k['table'] is tb and k['cell']['r'] < vr) or (k['table'] is not tb and k['order'] < tb['_order'])]
        if not usable: return ('fail', 'placement', None) if cars else ('fail', 'missing', None)
        ok, flag = match_pieces([k['text'] for k in usable], pieces, self.markers, self.own + self.table_context)
        got = ' '.join(k['text'] for k in usable)
        if not ok and any(k.get('joins') for k in usable) and match_pieces([spaced(k) for k in usable], pieces, self.markers, self.own + self.table_context)[0]: return 'unresolved', 'adjacency', norm(got)
        if not ok: return 'fail', 'spacing' if spacing_only(got, ' '.join(pieces)) else 'text', norm(got)
        orders = {k['order'] for k in usable}
        if any(u.get('kind') == 'table' and u['_order'] not in orders and min(orders) < u['_order'] < tb['_order'] for u in self.rf.units): return 'fail', 'placement', None
        self.ctx_orders.update(orders); self.matched = objects(usable)
        return 'pass', None, flag or ('anchor_unknown' if not anchors else None)

    def corner_text(self, value, alt, tb, vr):
        cars = [k for k in self.carriers(anchors_of(self.t, 'corner_text', alt), [value], tb) if k['cell'] is not None and self.in_order(k, tb, vr) and k['cell']['r'] != vr]
        if not cars: return 'fail', 'missing', None
        ok, flag = match_pieces([k['text'] for k in cars], [value], self.markers, self.own + self.table_context)
        if ok: self.ctx_orders.update(k['order'] for k in cars); self.matched = objects(cars)
        if not ok and any(k.get('joins') for k in cars) and match_pieces([spaced(k) for k in cars], [value], self.markers, self.own + self.table_context)[0]: return 'unresolved', 'adjacency', None
        return ('pass', None, flag) if ok else ('fail', 'text', ' '.join(k['text'] for k in cars))

    def lead_in(self, value, alt, tb, vr):
        cars = [k for k in self.carriers(anchors_of(self.t, 'lead_in', alt), [value], tb) if self.in_order(k, tb, vr) and (k['table'] is not tb or k['cell']['r'] < vr)]
        if not cars: return 'fail', 'missing', None
        hit = next((k for k in cars if boundary_equal(k['text'], value)), None)
        if hit is None and self.pieces_match([k['text'] for k in cars], value, [anchor_of(k) for k in cars])[0]: hit = cars[-1]
        flag = None
        if hit is None:
            got = norm(' '.join(k['text'] for k in cars))
            if re.search(r'(?<!\w)' + re.escape(norm(value)) + r'(?!\w)', got): hit, flag = cars[-1], 'contained'  # whole and in order inside the carriers (addendum C6)
            elif any(k.get('joins') for k in cars) and (any(boundary_equal(spaced(k), value) for k in cars) or re.search(r'(?<!\w)' + re.escape(norm(value)) + r'(?!\w)', norm(' '.join(spaced(k) for k in cars)))): return 'unresolved', 'adjacency', None
            else: return 'fail', 'spacing' if any(spacing_only(k['text'], value) for k in cars) or spacing_only(got, value) else 'text', got
        self.matched = objects(cars)  # a lead-in may be spread over several pieces; strikes outside its text do not count (struck_kept scopes by the key text)
        if hit['table'] is tb: return 'pass', None, flag
        between = [u for u in self.rf.units if hit['order'] < u['_order'] < tb['_order'] and u.get('kind') not in ('clutter', 'image') and u['_order'] not in self.ctx_orders
                   and not (source_before(hit['anchor'], u.get('anchor')) and source_before(u.get('anchor'), tb.get('anchor')))]  # what the source prints between them (page furniture) is not a displacement
        return ('pass', None, flag) if not between else ('fail', 'placement', None)

    def section_path(self, value, alt, target_order, tb=None):
        pieces, anchors = pieces_of(value), anchors_of(self.t, 'section_path', alt)
        cars = [k for k in self.carriers(anchors, pieces) if k['order'] < target_order and (tb is None or k['table'] is not tb)]
        found, matched_cars, i, run_in = [], [], 0, False  # matched_cars: every carrier the match used (a heading laid out in pieces, a run-in window), for the struck check
        while i < len(pieces):
            win = None; hit = next((k for k in cars if heading_eq(k['text'], pieces[i])), None)
            if hit is None:  # a heading laid out as adjacent cells or pieces, however many (E12), until the window outgrows the heading
                goal, open_ = len(squash(_CONTINUED.sub('', pieces[i]))), False
                for a in range(len(cars)):
                    for b in range(a + 2, len(cars) + 1):
                        if sum(len(squash(_CONTINUED.sub('', k['text']))) for k in cars[a:b]) > goal: break
                        ok = self.pieces_match([_CONTINUED.sub('', k['text']) for k in cars[a:b]], _CONTINUED.sub('', pieces[i]), [anchor_of(k) for k in cars[a:b]])[0]
                        if ok: hit, win = cars[b - 1], cars[a:b]; break
                        if ok is None: open_ = True  # the pieces touch where the heading prints a space: the page may space them
                    if hit: break
                if hit is None and open_: return 'unresolved', 'adjacency', pieces[i]
            if hit is None and i + 1 < len(pieces):  # E9: two levels printed on one line
                hit2 = next((k for k in cars if heading_eq(k['text'], pieces[i] + ' ' + pieces[i + 1])), None)
                if hit2 is not None: found.append(hit2); matched_cars.append(hit2); i += 2; continue
            if hit is None and anchors:  # a run-in heading: the block at the heading's own anchor starts with it (guide V18); the heading may be printed in pieces (E12), spacing by the boundary rule
                want = _CONTINUED.sub('', norm(pieces[i])).strip(); sw, tw = squash(want), tokens(want); open_run = False
                starts = lambda text: len(squash(text)) > len(sw) and squash(norm(text)).startswith(sw) and tokens(text)[:len(tw)] == tw
                for a in range(len(cars)):
                    text, apart, used = cars[a]['text'], spaced(cars[a]), [cars[a]]
                    for b in range(a + 1, len(cars)):
                        if len(squash(text)) > len(sw): break
                        text += ('' if self.adjacent(anchor_of(cars[b - 1]), anchor_of(cars[b])) else ' ') + cars[b]['text']  # read as the source prints the pieces
                        apart += ' ' + spaced(cars[b]); used.append(cars[b])  # the other reading of every touching join, for the unresolved verdict only
                    if starts(text): hit, run_in, win = cars[a], True, used; break
                    if starts(apart): open_run = True  # the pieces touch where the heading prints a space: the page may space them
                if hit is None and open_run: return 'unresolved', 'adjacency', pieces[i]
            if hit is None:
                if any(k.get('joins') and heading_eq(spaced(k), pieces[i]) for k in cars): return 'unresolved', 'adjacency', pieces[i]  # the pieces touch where the heading prints a space: the page may space them
                near = next((k for k in cars if spacing_only(k['text'], pieces[i])), None)
                return ('fail', 'spacing', pieces[i]) if near else ('fail', 'missing', pieces[i])
            found.append(hit); matched_cars.extend(win or [hit]); i += 1
        self.matched = objects(matched_cars)
        self.row('heading_recognised', 'pass' if not run_in and all(k['unit'] is not None and k['unit'].get('kind') in ('heading', 'title') for k in found) else 'fail')
        return 'pass', None, 'run_in' if run_in else (None if anchors else 'anchor_unknown')

    def basis(self, value, alt, tb, vr):
        """Qualifier phrases: kept at the key's reviewed location; inside the value's table, in source row order."""
        anchors = anchors_of(self.t, 'segment_or_basis', alt)
        for phrase in pieces_of(value):
            want = norm(phrase)
            at = self.carriers(anchors, [phrase], tb, equal=False)
            holds = lambda text: contains(text, want) or contains(minus_marks_anywhere(text, self.markers), want)  # the phrase, with the record's own marks printed into it; spacing by the boundary rule
            cars = [k for k in at if holds(k['text'])] or ([at[0]] if at and holds(' '.join(k['text'] for k in at)) else [])
            if not cars and any(k.get('joins') for k in at) and (any(holds(spaced(k)) for k in at) or holds(' '.join(spaced(k) for k in at))): return 'unresolved', 'adjacency', phrase
            if not cars: return 'fail', 'missing', phrase
            self.matched = (self.matched or []) + objects(cars)
            if not any(self.in_order(k, tb, vr) or k['table'] is None or k['table'] is not tb for k in cars): return 'fail', 'placement', phrase
        return 'pass', None, None if anchors else 'anchor_unknown'

    def unit_printed(self, value, alt, tb, vr, V):
        anchors = anchors_of(self.t, 'unit_printed', alt)
        cars = self.carriers(anchors, [value], tb)
        good = [k for k in cars if self.same(k['text'], value)[0]] or ([cars[-1]] if cars and self.same(' '.join(k['text'] for k in cars), value)[0] else [])
        if good:
            k = good[0]; self.matched = objects(cars)
            if k['table'] is tb and not self.in_order(k, tb, vr): return 'fail', 'placement', None
            return 'pass', None, None
        if squash(value) and squash(value) in squash(''.join(c.get('text', '') for c in V)): return 'pass', None, 'in_value_cell'
        if any(k.get('joins') and self.same(spaced(k), value)[0] for k in cars): return 'unresolved', 'adjacency', None
        return ('fail', 'text', ' '.join(k['text'] for k in cars)) if cars else ('fail', 'missing', None)

    def periods(self, value, alt, tb, vr, vcols):
        change = any(g.get('role') in ('compared', 'comparison') for g in value)  # a change between periods (guide 3.10, addendum C2): its parts head the compared columns
        for group in value:
            for part in group.get('parts') or []:
                want, a = norm(part['text']), part.get('anchor')
                cells = self.merged(self.rf.cells_at(a, tb)) if a else []
                if cells:
                    if not self.same(joined(cells), want)[0] and not any(contains(c.get('text', ''), want) for c in cells):
                        if any(c.get('joins') for c in cells) and (self.same(norm(' '.join(spaced(c) for c in sorted(cells, key=lambda c: (c['r'], c['c'])))), want)[0] or any(contains(spaced(c), want) for c in cells)): return 'unresolved', 'adjacency', part['text']
                        return 'fail', 'text', part['text']
                    label_col = min([c['c'] for c in self.rf.cells_in(tb) if row_hit(c, vr)] or [0])
                    free = [c for c in cells if c['r'] != vr and not col_hit(c, vcols)]  # neither on the value's row nor over its column
                    if any(c['c'] > label_col for c in free):
                        if not change or any(c['r'] > vr for c in free): return 'fail', 'column', part['text']
                        if any(not self.same_group(c, tb, vcols, value) for c in free if c['c'] > label_col): return 'fail', 'group', part['text']
                        continue  # the compared columns' headings, in the value's own group above it; the change column itself is proven by header_path
                    if free:  # a time row in the label column governs the rows after it; the route must keep that group intact (E15)
                        r0, head = max(c['r'] for c in free), max(free, key=lambda c: c['r'])
                        if r0 > vr or not source_before(head.get('anchor'), self.V[0].get('anchor')): return 'fail', 'order', part['text']
                        between = [c for c in self.rf.cells_in(tb) if r0 < c['r'] < vr and squash(c.get('text', '')) and spans(c.get('anchor'))]
                        if any(not (source_before(head.get('anchor'), c['anchor']) and source_before(c['anchor'], self.V[0].get('anchor'))) for c in between):
                            return 'fail', 'scope', part['text']  # a row the route placed in this group comes from elsewhere in the source
                    continue
                cars = self.carriers([a], [part['text']], tb, equal=False) if a else [{'text': u.get('text', ''), 'unit': u} for u in self.rf.units if u.get('kind') not in ('table', 'clutter')]
                if not any(contains(k['text'], want) or (k.get('unit') and want == local(k['unit'].get('name', ''))) for k in cars) and not contains(' '.join(k['text'] for k in cars), want):
                    if any(k.get('joins') for k in cars) and contains(' '.join(spaced(k) for k in cars), want): return 'unresolved', 'adjacency', part['text']
                    return 'fail', 'missing', part['text']
        return 'pass', None, None

    def same_group(self, cell, tb, vcols, periods):
        """Does the heading of a compared column belong to the value's group? The headers above it that cover its column — leaving out
        the record's own period headings — must include one that also covers the value's column; a heading with no such header above it
        stands in the table's top block (addendum C2, Codex's reproducer: year headings swapped into the other group)."""
        parts = [norm(p['text']) for g in periods for p in g.get('parts') or []]
        above = [h for h in self.rf.cells_in(tb) if h['r'] < cell['r'] and col_hit(h, cell['c']) and squash(h.get('text', '')) and not any(self.same(h.get('text', ''), p)[0] for p in parts)]
        if not above: return True
        nearest = max(h['r'] for h in above)  # the innermost group decides: a table-wide title above both groups cannot override a conflicting subgroup
        return any(col_hit(h, vcols) for h in above if h['r'] == nearest)

    def footnotes(self, value, alt, tb, V, vr):
        linked = []
        for m in value:
            mark, a = m['marker_text'], m.get('anchor')
            cars = self.carriers([a], [mark], tb) if a else []
            apart = any(k['cell'] is not None and mark in (k['cell'].get('markers') or []) for k in cars) or any(squash(k['text']) == squash(mark) for k in cars)
            if not apart:
                if any(k['cell'] in V for k in cars): return 'fail', 'marker_glued', mark
                if not any(mark in k['text'] for k in cars): return 'fail', 'marker_missing', mark  # glued to a label or title: allowed, flagged there
            if m.get('note_anchor'):
                # the note's body, with its own mark set apart, must sit at the note's anchor: alone, spaced, split into
                # pieces, or inside a "Notes:" block that holds several notes
                body = norm(minus_markers(m.get('note_text') or '', [mark]))
                at_note = self.carriers([m['note_anchor']], [m.get('note_text') or ''], tb)
                notes = [k for k in at_note if body and contains(minus_markers(k['text'], [mark]), body)] or ([at_note[0]] if at_note and body and contains(' '.join(k['text'] for k in at_note), body) else [])
                if not notes: return ('unresolved', 'adjacency', mark) if any(k.get('joins') and contains(minus_markers(spaced(k), [mark]), body) for k in at_note) else ('fail', 'missing_note', mark)
                k = notes[0]
                declared = (k['unit'] or {}).get('marker')
                if declared and norm(declared) != norm(mark): return 'fail', 'wrong_note_link', mark  # an explicit wrong mark-to-note assignment
                if k['table'] is tb and not self.in_order(k, tb, vr): return 'fail', 'placement', mark
                carrier_ids = {(k['unit'] or k['table']).get('id')}
                linked.append(k['table'] is tb or bool(carrier_ids & set(tb.get('notes') or [])) or (k['unit'] is not None and k['unit'].get('marker') == mark))
        if linked: self.row('note_linked', 'pass' if all(linked) else 'fail')
        return 'pass', None, None

    def range_(self, value, alt, tb, V, vr, vcols):
        partner = value.get('partner')
        if partner:
            at = sorted(self.rf.cells_at(partner['anchor'], tb), key=lambda c: c['c']); spelt = self.spell(at, partner['printed_value'])
            exact = [c for c in at if boundary_equal(c.get('text', ''), partner['printed_value'])]
            cells = exact or (at if spelt in (True, None) else [])  # fragments whose join only boxes could prove still carry a row and a position
            if not cells: return 'fail', 'partner', None
            if not any(row_hit(c, vr) for c in cells): return 'fail', 'row', None
            if source_before(partner['anchor'], self.t['anchor']) != (cells[0]['c'] < vcols[0]): return 'fail', 'order', None
            pending = not exact and spelt is None  # association proven, join not: unresolved unless something below fails
        else: pending = False
        for ev in value.get('evidence') or []:
            hits = self.merged(self.rf.cells_at(ev['anchor'], tb)) + self.merged_units(self.rf.units_at(ev['anchor']))
            if not any(contains(h.get('text', ''), ev['text']) for h in hits):
                if any(h.get('joins') and contains(spaced(h), ev['text']) for h in hits): pending = True; continue  # evidence split where the page alone could show the space
                return 'fail', 'evidence', ev['text']
        return ('unresolved', 'adjacency', None) if pending else ('pass', None, None)

    # ---- XML
    def grade_xml(self):
        t, rf = self.t, self.rf
        V = rf.units_at(t['anchor'], kinds=('field',), exclude=())
        if not V: return None
        v = V[0]; f = t['fields']; printed = f.get('printed_value') or ''
        here = xml_element_at(rf.raw, t['anchor']['byte_start'])  # the element whose text the key points at, by its expanded name
        if here is None: self.row('value', 'unresolved', 'input_invalid'); self.row('row_label', 'unresolved', 'input_invalid'); return v
        ex = t['excluded']
        if 'printed_value' in ex: self.row('value', 'excluded')
        elif fused([v.get('text', '')], printed): self.row('value', 'pass')
        else: self.row('value', 'fail', 'spacing' if squash(v.get('text', '')) == squash(printed) else 'text')
        if f.get('row_label') is not None:
            if 'row_label' in ex: self.row('row_label', 'excluded')
            elif local(v.get('name', '')) != f['row_label']: self.row('row_label', 'fail', 'name')
            else: ok = v.get('name') == here; self.row('row_label', 'pass' if ok else 'fail', None if ok else 'namespace')
        if f.get('header_path'):
            if 'header_path' in ex: self.row('header_path', 'excluded')
            else: ok = list(v.get('path') or []) == list(f['header_path']); self.row('header_path', 'pass' if ok else 'fail', None if ok else 'path')
        group = v.get('group') or {}
        same_group = [u for u in rf.units if u.get('kind') == 'field' and u.get('path') == v.get('path') and (u.get('group') or {}).get('index') == group.get('index')]
        ok = True
        for item in f.get('row_context') or []:
            if item['header'] == 'position': ok &= f"{group.get('index')} of {group.get('count')}" == item['text']
            else: ok &= any(local(u.get('name', '')) == item['header'] and norm(u.get('text', '')) == norm(item['text']) for u in same_group)
        if f.get('row_context'): self.row('row_context', 'excluded' if 'row_context' in ex else 'pass' if ok else 'fail', None if ok or 'row_context' in ex else 'group')
        if f.get('unit_printed'):
            hit = any(norm(f['unit_printed']) in norm(u.get('text', '')) or norm(f['unit_printed']) == norm(local(u.get('name', ''))) for u in rf.units if u.get('kind') == 'field')  # an XML unit may be a printed text (a security title) or the element's own name (percentOfClass), as periods already allow
            if 'unit_printed' in ex: self.row('unit_printed', 'excluded')
            else: self.row('unit_printed', 'pass' if hit else 'fail', None if hit else 'missing', 'anchor_unknown')
        self.field('periods', self.periods, {'_order': v['_order'], 'cells': []}, 0, (0, 1))
        for name in T4:
            if name in f: self.row(name, 'excluded' if name in ex else 'not_t1')
        return v

    # ---- structure
    def grade_structure(self):
        t, rf, f = self.t, self.rf, self.t['fields']
        # a block may come back as text units, as one image unit, as ordered blocks (a scanned page) or inside a layout table
        units = rf.units_at(t['anchor'], exclude=('clutter',))
        if not units: return None
        def text_of(u):
            if u.get('kind') != 'table': return u.get('text', '')
            cells = [c for c in u.get('cells') or [] if overlap(c.get('anchor'), t['anchor'])] or u.get('cells') or []
            return ' '.join(c.get('text', '') for c in self.merged(cells))
        want = norm(f.get('printed_text') or ''); got = norm(' '.join(text_of(u) for u in self.merged_units(units)))  # touching pieces read as one; the reference phrase and the WER see the block as printed
        self.block_spaced = norm(' '.join(spaced(u) if u.get('kind') != 'table' else text_of(u) for u in self.merged_units(units)))  # the other reading, for the unresolved verdict only
        if 'printed_text' in t['excluded']: self.row('printed_text', 'excluded'); ok = True
        else:
            ok, why, frag = self.pieces_match([text_of(u) for u in units], want, [u.get('anchor') for u in units])
            bearing = [c for u in units for c in ([x for x in u.get('cells') or [] if overlap(x.get('anchor'), t['anchor'])] or [u] if u.get('kind') == 'table' else [u])]  # the text-bearing items: a block laid out in a table is its cells at the target's anchor, never the whole table
            if ok and not struck_kept([f.get('printed_text') or ''], bearing): ok, why = False, 'struck'  # the words survive but a cancelled word became active, or the wrong one was cancelled
            self.row('printed_text', 'pass' if ok else 'unresolved' if ok is None else 'fail', None if ok else why, {'fragmented': frag} if ok and frag else None if ok else {'wer': wer(got, want)})
        main = next((u for u in units if u.get('kind') != 'table'), units[0])
        if f.get('kind') in LOOSE_KINDS: self.row('kind', 'na', None, main.get('kind'))
        elif f.get('kind'):
            ok = KIND.get(main.get('kind')) == f['kind']; self.row('kind', 'pass' if ok else 'fail', None if ok else 'kind', main.get('kind'))
        self.field('section_path', self.section_path, units[0]['_order'])
        self.field('references', self.references, units, got)
        return units[0]

    def references(self, value, alt, units, block_text):
        linked, failure, links = [], None, [l for u in units for l in u.get('links') or []]
        for ref in value:
            tgt = ref.get('target')
            if ref.get('status') == 'RESOLVED' and tgt and Path(tgt['file']).name == Path(self.t['file_id']).name:
                dest = self.rf.units_at(tgt['anchor'], exclude=('clutter',))
                mine = [l for l in links if norm(l.get('text') or '') == norm(ref['printed_text']) or (ref.get('href') and l.get('href') == ref['href'])]  # this reference's own edges only
                explicit = [l for l in mine if l.get('to')]
                linked.append(bool(dest) and bool(explicit) and all(self.rf.by_id.get(l.get('to')) in dest for l in explicit))
                if not dest: failure = failure or ('fail', 'destination', ref['printed_text'])
                elif explicit and not all(self.rf.by_id.get(l.get('to')) in dest for l in explicit):  # E6: any contradictory destination is wrong, not merely unlinked
                    failure = failure or ('fail', 'wrong_link', ref['printed_text'])
            if norm(ref['printed_text']) not in block_text: failure = failure or (('unresolved', 'adjacency', ref['printed_text']) if norm(ref['printed_text']) in getattr(self, 'block_spaced', '') else ('fail', 'phrase', ref['printed_text']))
            elif ref.get('href') and not any(l.get('href') == ref['href'] for l in links): failure = failure or ('fail', 'href', ref['href'])
        if linked: self.row('reference_linked', 'pass' if all(linked) else 'fail')
        return failure or ('pass', None, None)


# --------------------------------------------------------------------------------------------------------- gates
def gates_for_file(rf, status):
    """Per-file P14 facts: dishonest or missing anchors, duplicate ids, order breaks, uncovered visible text. A check that cannot be
    made (no text layer, no page sizes, stylesheet-dependent visibility, a PARTIAL route) is reported as None = not measured."""
    g = {'dishonest': 0, 'unanchored': 0, 'boundary': 0, 'inserted_chars': 0, 'bounds_inconsistent': 0, 'dup_ids': 0, 'order_breaks': 0, 'uncovered': None, 'anchors_measured': True,
         'hidden_chars': rf.vis.hidden_chars if rf.vis else None}
    ids = [u.get('id') for u in rf.units]; g['dup_ids'] = len(ids) - len(set(ids))
    keys = [order_key(u['anchor']) for u in rf.units if spans(u.get('anchor')) and u.get('layer') != 'furniture']
    g['order_breaks'] = sum(1 for a, b in zip(keys, keys[1:]) if b < a)
    ranges = []
    for u in rf.units:
        items = rf.cells_in(u) if u.get('kind') == 'table' else [u]
        for x in items:
            parts = spans(x.get('anchor'))
            if u.get('kind') == 'image' or x.get('link_flag') == 'gap': continue  # pictures carry no text to certify
            if not parts:
                if squash(x.get('text', '')): g['unanchored'] += 1  # text claimed without a source position
                continue
            for a in parts:
                if 'byte_start' in a:
                    if not (0 <= a['byte_start'] < a['byte_end_exclusive'] <= (rf.raw_len or 0)): g['dishonest'] += 1; break
                elif 'region' in a:  # no independent page geometry: a region is never certified; its consistency with the route's own sizes is reported
                    g['anchors_measured'] = False; size = rf.pages.get(a.get('page'))
                    if size is not None:
                        x0, y0, x1, y1 = a['region']
                        if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]): g['bounds_inconsistent'] += 1
                    break
            else:
                byte = [a for a in parts if 'byte_start' in a]
                if byte and rf.vis is not None:
                    ranges.extend((a['byte_start'], a['byte_end_exclusive']) for a in byte)
                    seen = squash(rf.vis.at_any(byte))
                    if x.get('link_flag') == 'pieced':  # each anchor must read its block of the text; the characters outside the blocks are the tool's insertion
                        nt = norm(x.get('text', '')); idx = [i for i, c in enumerate(nt) if c != ' ']; sq = nt.replace(' ', '')
                        pieces = [tuple(pc) for pc in x.get('pieces') or []]
                        if len(pieces) != len(byte) or not all(0 <= a < b <= len(sq) and (k == 0 or a >= pieces[k - 1][1]) for k, (a, b) in enumerate(pieces)) \
                                or any(byte[k]['byte_start'] < byte[k - 1]['byte_end_exclusive'] for k in range(1, len(byte))) \
                                or any(squash(rf.vis.at(sp['byte_start'], sp['byte_end_exclusive'])) != sq[a:b] for sp, (a, b) in zip(byte, pieces)): g['dishonest'] += 1; continue  # blocks out of source order, or not reading their text
                        g['inserted_chars'] += len(sq) - sum(b - a for a, b in pieces)  # derived from the blocks, never from the tool's own count
                        # read block by block, the source (each span with its own whitespace, a separator wherever the source prints anything between two
                        # spans) and the output (each block as printed, a separator wherever the output prints anything between two blocks) must have the
                        # same words and numbers — inside blocks and across every join; the ordinary boundary rule decides, nothing is exempt by hand
                        src = ''.join(rf.vis.at(sp['byte_start'], sp['byte_end_exclusive']) + (' ' if k + 1 < len(byte) and rf.vis.at(sp['byte_end_exclusive'], byte[k + 1]['byte_start']) else '') for k, sp in enumerate(byte))
                        out = ''.join(nt[idx[a]:idx[b - 1] + 1] + (' ' if k + 1 < len(pieces) and idx[pieces[k + 1][0]] > idx[b - 1] + 1 else '') for k, (a, b) in enumerate(pieces))
                        if not boundary_equal(src, out): g['boundary'] += 1
                        continue
                    for mm in (squash(m) for m in x.get('markers') or []):  # each reported mark sits right before or right after the text
                        if mm and seen.startswith(mm): seen = seen[len(mm):]
                        elif mm and seen.endswith(mm): seen = seen[:-len(mm)]
                    if seen != squash(x.get('text', '')): g['dishonest'] += 1
                    elif not boundary_equal(marks_off(rf.vis.at_any(byte), x.get('markers') or []), x.get('text', '')): g['boundary'] += 1  # same characters, a word or number boundary lost or added
    if rf.vis is not None and not rf.vis.certain: g['anchors_measured'] = False  # visibility depends on stylesheet rules this scanner does not read
    if rf.vis is not None and rf.vis.certain and status == 'OK': g['uncovered'] = rf.vis.uncovered(ranges)
    g['pictures'] = rf.raw.count(b'<img') if rf.vis is not None and rf.raw is not None else None  # picture content is never measured by the text map
    return g


# ----------------------------------------------------------------------------------------------------------- run
def run(key_dir, route_dir, out_dir, catalog=None, heldout_detail=False):
    facts = verify_inputs(key_dir, catalog, route_dir)  # before anything is read: the frozen manifest must pin what grading consumes
    targets = load_key(key_dir, catalog)
    route_dir, out_dir = Path(route_dir), Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    rows, verdicts, files, per_file, routes = [], {}, {}, {}, {}
    marker_glued = 0
    for fid in sorted({t['file_id'] for t in targets}):
        mine = [t for t in targets if t['file_id'] == fid]; path, want = mine[0]['path'], mine[0]['sha256']
        raw = path.read_bytes() if path.exists() else None
        rpath = route_dir / (fid + '.json')
        data = json.loads(rpath.read_text()) if rpath.exists() else None
        if raw is None or sha256(raw) != want: status = 'INPUT_MISMATCH'
        elif data is None: status = 'NOT_CONVERTED'; data = {'file_id': fid, 'status': 'MISSING', 'units': []}
        elif data.get('sha256') != want: status = 'NOT_CONVERTED'; data['error'] = f"route converted other bytes: {data.get('sha256')}"
        elif data.get('file_id') != fid: status = 'NOT_CONVERTED'; data['error'] = f"route names another source: {data.get('file_id')}"
        elif data.get('status') not in ('OK', 'PARTIAL'): status = 'NOT_CONVERTED'
        else: status = 'OK'
        files[fid] = {'status': status, 'route_status': (data or {}).get('status'), 'error': (data or {}).get('error'), 'seconds': (data or {}).get('seconds')}
        routes[fid] = (data or {}).get('route')
        rf = RouteFile(data, raw, mine[0]['format'].split('/')[-1]) if status == 'OK' else None
        if rf: per_file[fid] = gates_for_file(rf, data.get('status'))
        structure_units = []
        for t in mine:
            if status != 'OK': verdicts[t['key_id']] = status; continue
            g = Grader(t, rf)
            unit = g.grade_cell() if t['type'] == 'cell' else g.grade_structure()
            if unit is None: verdicts[t['key_id']] = 'UNRESOLVED'; rows += g.rows; continue
            if t['type'] == 'structure': structure_units.append((t['key_id'], order_key(t['anchor']), unit['_order']))
            failed = [r['check'] for r in g.rows if r['verdict'] == 'fail' and r['check'] not in STRUCTURE]
            marker_glued += sum(1 for r in g.rows if r['reason'] == 'marker_glued')
            verdicts[t['key_id']] = 'FAIL' if failed else 'UNRESOLVED' if any(r['verdict'] == 'unresolved' for r in g.rows) else 'PASS'
            rows += g.rows
        for kid, a, o in structure_units:  # block order within the file
            bad = any((a < a2) != (o < o2) for k2, a2, o2 in structure_units if k2 != kid and a != a2)
            rows.append({'key_id': kid, 'file_id': fid, 'split': next(t['split'] for t in mine if t['key_id'] == kid),
                         'format': next(t['format'] for t in mine if t['key_id'] == kid), 'check': 'order', 'verdict': 'fail' if bad else 'pass',
                         'reason': 'order' if bad else None, 'detail': None})
            if bad and verdicts[kid] == 'PASS': verdicts[kid] = 'FAIL'
    hidden_files = set() if heldout_detail else {t['file_id'] for t in targets if t['split'] == 'heldout'}
    public = {t['file_id'] for t in targets} - hidden_files  # a file with any held-out target shows counts only
    uncovered = {fid: (g['uncovered'] if fid in public else {'spans': len(g['uncovered']), 'chars': sum(len(squash(x['text'])) for x in g['uncovered'])})
                 for fid, g in per_file.items() if g['uncovered']}
    ungraded = sorted(f for f, x in files.items() if x['status'] != 'OK')  # a file that was not graded has no measured gate
    cov_unmeasured = sorted(set(f for f, g in per_file.items() if g['uncovered'] is None) | set(ungraded))
    anc_unmeasured = sorted(set(f for f, g in per_file.items() if not g['anchors_measured']) | set(ungraded))
    clean = all(g['dishonest'] == 0 and g['unanchored'] == 0 and g['boundary'] == 0 and g['inserted_chars'] == 0 for g in per_file.values())  # text the tool added is text the source cannot certify
    gates = {
        'honest_anchors': {'pass': not anc_unmeasured and clean, 'measured_pass': clean,
                           'dishonest': {f: g['dishonest'] for f, g in per_file.items() if g['dishonest']},
                           'unanchored': {f: g['unanchored'] for f, g in per_file.items() if g['unanchored']},
                           'boundary': {f: g['boundary'] for f, g in per_file.items() if g['boundary']},
                           'bounds_inconsistent': {f: g['bounds_inconsistent'] for f, g in per_file.items() if g['bounds_inconsistent']},
                           'inserted_chars': {f: g['inserted_chars'] for f, g in per_file.items() if g['inserted_chars']}, 'not_measured': anc_unmeasured},
        'ids_and_run_facts': {'pass': not ungraded and all(g['dup_ids'] == 0 for g in per_file.values()) and all(all(k in (routes[f] or {}) for k in ('tool', 'version', 'settings')) for f in per_file), 'not_measured': ungraded},
        'reading_order': {'pass': not ungraded and sum(g['order_breaks'] for g in per_file.values()) == 0, 'breaks': {f: g['order_breaks'] for f, g in per_file.items() if g['order_breaks']}, 'not_measured': ungraded},
        'markers_apart': {'pass': not ungraded and marker_glued == 0, 'glued': marker_glued, 'not_measured': ungraded},
        'nothing_lost': {'pass': not uncovered and not cov_unmeasured, 'measured_pass': not uncovered, 'uncovered': uncovered, 'not_measured': cov_unmeasured,
                         'measures': 'visible source text; picture content is not measured', 'pictures_not_measured': {f: g['pictures'] for f, g in per_file.items() if g.get('pictures')}},
    }
    shown = [t for t in targets if heldout_detail or t['split'] != 'heldout']
    report = {
        'results': [r for r in rows if heldout_detail or r['split'] != 'heldout'],
        'targets': {t['key_id']: {'verdict': verdicts[t['key_id']], 'split': t['split'], 'format': t['format'], 'file_id': t['file_id'],
                                  'failed': sorted({r['check'] for r in rows if r['key_id'] == t['key_id'] and r['verdict'] == 'fail' and r['check'] not in STRUCTURE})}
                    for t in shown},
        'gates': gates, 'files': files,
        'summary': summarize(targets, rows, verdicts, files, next((r for r in routes.values() if r), None), {t['key_id'] for t in shown}),
        'run_facts': facts,
    }
    with open(out_dir / 'results.jsonl', 'w') as f:
        for r in report['results']: f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + '\n')
    (out_dir / 'summary.json').write_text(json.dumps({k: report[k] for k in ('summary', 'gates', 'files', 'targets', 'run_facts')}, indent=1, sort_keys=True, ensure_ascii=False, default=str))
    (out_dir / 'summary.md').write_text(markdown(report))
    return report


def summarize(targets, rows, verdicts, files, route, shown_ids=None):
    by, sup = {}, {'targets': 0, 'PASS': 0, 'FAIL': 0, 'UNRESOLVED': 0, 'NOT_CONVERTED': 0}
    for t in targets:
        v = verdicts[t['key_id']]
        if t['split'] == 'supplement':
            sup['targets'] += 1; sup[v] = sup.get(v, 0) + 1; continue
        cell = by.setdefault(t['split'], {}).setdefault(t['format'], {'targets': 0, 'PASS': 0, 'FAIL': 0, 'UNRESOLVED': 0, 'NOT_CONVERTED': 0})
        cell['targets'] += 1; cell[v] = cell.get(v, 0) + 1
    fields, structure = {}, {}
    for r in rows:
        if r['check'] in STRUCTURE:
            s = structure.setdefault(r['check'], {'pass': 0, 'total': 0}); s['total'] += 1; s['pass'] += r['verdict'] == 'pass'
        else:
            f = fields.setdefault(r['check'], {}); f[r['verdict']] = f.get(r['verdict'], 0) + 1
    reasons = {}
    for r in rows:
        if r['verdict'] == 'fail' and r['check'] not in STRUCTURE:
            d = reasons.setdefault(r['check'], {}); d[r['reason']] = d.get(r['reason'], 0) + 1
    return {'by_split_format': by, 'supplement': sup, 'by_field': fields, 'structure': structure, 'failures_by_reason': reasons,
            'unresolved': sorted(k for k, v in verdicts.items() if v == 'UNRESOLVED' and (shown_ids is None or k in shown_ids)),
            'excluded_fields': sum(1 for r in rows if r['verdict'] == 'excluded'),
            'run_facts': {'route': route, 'files': {s: sum(1 for f in files.values() if f['status'] == s) for s in sorted({f['status'] for f in files.values()})},
                          'seconds': round(sum(f['seconds'] or 0 for f in files.values()), 3)}}


def markdown(report):
    s, out = report['summary'], ['# Route grading summary', '']
    out += ['| split | format | targets | PASS | FAIL | UNRESOLVED | NOT_CONVERTED |', '|---|---|---:|---:|---:|---:|---:|']
    for split, fmts in s['by_split_format'].items():
        for fmt, c in fmts.items(): out.append(f"| {split} | {fmt} | {c['targets']} | {c['PASS']} | {c['FAIL']} | {c['UNRESOLVED']} | {c['NOT_CONVERTED']} |")
    sp = s['supplement']; out.append(f"| supplement | cell | {sp['targets']} | {sp['PASS']} | {sp['FAIL']} | {sp['UNRESOLVED']} | {sp['NOT_CONVERTED']} |")
    out += ['', f"Excluded fields (not scored, counted): {s['excluded_fields']}", '', '| check | pass | fail | unresolved | na | excluded | not_t1 |', '|---|---:|---:|---:|---:|---:|---:|']
    for f, c in s['by_field'].items():
        out.append(f"| {f} | {c.get('pass', 0)} | {c.get('fail', 0)} | {c.get('unresolved', 0)} | {c.get('na', 0)} | {c.get('excluded', 0)} | {c.get('not_t1', 0)} |")
    out += ['', '| failed check | reason | count |', '|---|---|---:|'] + [f'| {c} | {r} | {n} |' for c, d in s['failures_by_reason'].items() for r, n in d.items()]
    if s['unresolved']: out += ['', 'Unresolved (not found at its spot): ' + ', '.join(s['unresolved'])]
    out += ['', '| structure | pass | total |', '|---|---:|---:|'] + [f"| {k} | {v['pass']} | {v['total']} |" for k, v in s['structure'].items()]
    word = lambda v: 'yes' if v['pass'] else ('not measured for ' + ', '.join(v['not_measured']) if v.get('not_measured') and v.get('measured_pass', not any(v.get(k) for k in ('dishonest', 'unanchored'))) else 'NO')
    out += ['', '| gate | pass |', '|---|---|'] + [f"| {k} | {word(v)} |" for k, v in report['gates'].items()]
    out += ['', f"Run facts: key {report['run_facts']['key_sha256'][:12]}…, manifest {str(report['run_facts'].get('manifest_sha256'))[:12]}…, catalog {report['run_facts']['catalog_sha256'][:12]}…"]
    out += ['', f"Run facts: {json.dumps(s['run_facts'], default=str)}", '']
    return '\n'.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', default=json.loads((Path(__file__).resolve().parents[1] / 'golden/PACKAGE.json').read_text())['package_path'], help='key package folder (default: the one recorded in golden/PACKAGE.json)'); ap.add_argument('--route', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--catalog'); ap.add_argument('--heldout-detail', action='store_true')
    a = ap.parse_args(argv)
    run(a.key, a.route, a.out, a.catalog, a.heldout_detail)
    print((Path(a.out) / 'summary.md').read_text())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
