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
from itertools import product
from math import prod, isfinite
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata
import xml.etree.ElementTree as ET

from benchmarks.prepare.grader.anchor import Visible, norm, squash, xml_parser

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
    declare(key_dir, targets)
    return targets


def declare(key_dir, targets):
    """The package's contract declarations (FINAL_MANIFEST `contract_declarations`; package 3: CONTRACT_DECISIONS_R4.json): targets EXCLUDED by a
    reviewed source anchor (page numbers, owner decision (d) 2026-10-04) and block kinds compared approximately (pictures, decision (a)). An
    exclusion must name a key target, its file, the file's bytes and the target's own anchor, else the run stops: a declaration that fails its
    checks never grades silently (as E13). A package that declares nothing (package 2) grades as before."""
    name = manifest(key_dir).get('contract_declarations')
    if not name: return
    by, kinds = {t['key_id']: t for t in targets}, set()
    for d in json.loads((Path(key_dir) / name).read_text()).get('decisions') or []:
        kinds |= set((d.get('policy') or {}).get('approximate_kinds') or [])
        for e in d.get('exclusions') or []:
            t = by.get(e['key_id'])
            if not t or (t['file_id'], t['sha256'], t['anchor']) != (e['file_id'], e['sha256'], e['anchor']): raise ValueError(f"{name}: exclusion does not match the key: {e['key_id']}")
            t['excluded_target'] = e['role']
    for t in targets:
        if t['type'] == 'structure' and t['fields'].get('kind') in kinds: t['approximate'] = True


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
    man = manifest(key_dir); listed = man.get('files_sha256') or {}; facts['manifest_sha256'] = sha256(m.read_bytes()); facts['contract_declarations'] = man.get('contract_declarations')
    for rel in KEY_FILES + ((man['contract_declarations'],) if man.get('contract_declarations') else ()):  # pinned and present, or neither: a pinned file that is missing is a declared input lost; a named declarations file is an input too
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
        if a.get('page') != b.get('page') or a.get('file') != b.get('file'): return 0.0  # the same page of the source, or the same picture by its whole identifier: a base name is no identity (Codex R17-C3)
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
        self.raw, self.raw_len, self.paged = raw, (len(raw) if raw is not None else None), ext == '.pdf'  # a PDF's boxes always name their page (contract)
        decl = data.get('pages'); self.pages_declared = decl is not None and decl != {}  # the route declares its page sizes: a box must then lie on a page it validly declares — an unusable declaration never reads as none, an empty list, a false or a zero included; absent, null and an empty object declare nothing (Codex R17-C1, R18-C4)
        self.pages = {int(k): v for k, v in (decl.items() if isinstance(decl, dict) else ()) if str(k).isdecimal() and int(k) > 0 and isinstance(v, list) and len(v) == 2 and all(type(x) in (int, float) and isfinite(x) and x > 0 for x in v)}  # the usable entries: a positive page number with [width, height], two finite positive numbers
        for x in [*self.units, *(c for _, c in self.cells)]:  # a position that cannot be true is no position: it locates nothing, supplies nothing, and the gate counts it (Codex R14-3, R15-3); the claim is kept apart for the gate's report
            a = x.get('anchor'); sp = spans(a)
            if a not in (None, []) and not (sp and all(self.possible(s) for s in sp)): x['_bad_anchor'], x['_claimed'], x['anchor'] = True, a, None
        self.placed = [u for u in self.units if spans(u.get('anchor'))]  # the units with a position: the only ones that may stand as evidence when a lookup goes by text
        # byte index: cells sorted by first byte, with the longest span, so a lookup scans a small window
        byte_cells = [(min(a['byte_start'] for a in sp), max(a['byte_end_exclusive'] for a in sp), u, c)
                      for u, c in self.cells for sp in [[a for a in spans(c.get('anchor')) if 'byte_start' in a]] if sp]
        byte_cells.sort(key=lambda x: x[0])
        self._starts, self._byte_cells = [x[0] for x in byte_cells], byte_cells
        self._max_len = max([e - b for b, e, _, _ in byte_cells], default=0)
        self._box_cells = [(u, c) for u, c in self.cells if any('region' in a for a in spans(c.get('anchor')))]

    def possible(self, a):
        """Can this place be true? A byte span: integers, 0 <= start < end <= the source's length. A box: four numbers, left < right and top < bottom
        from 0, on the canvas the source's format gives it (contract: PDF {page, region}, picture files {file, region}) — in a PDF a positive integer
        page which, when the route declares page sizes, is one it validly declares, with the box inside that size; elsewhere its picture file, and no page.
        A PDF is addressed by page boxes: a byte span alone is no place in one. A place of both kinds must satisfy both; a place of neither kind,
        a box naming no canvas (Codex R16-2), or one that fails its own test, cannot be true."""
        if not isinstance(a, dict) or not ({'byte_start', 'byte_end_exclusive', 'region', 'page'} & set(a)): return False
        if 'byte_start' in a or 'byte_end_exclusive' in a:
            s, e = a.get('byte_start'), a.get('byte_end_exclusive')
            if not (type(s) is int and type(e) is int and 0 <= s < e <= (self.raw_len if self.raw_len is not None else e)): return False
        if 'region' in a or 'page' in a or self.paged:
            r, p = a.get('region'), a.get('page'); size = self.pages.get(p) if type(p) is int else None
            canvas = (type(p) is int and p > 0 and (not self.pages_declared or size is not None)) if self.paged else 'page' not in a and isinstance(a.get('file'), str) and a['file'].strip() != ''
            if not (isinstance(r, list) and len(r) == 4 and all(type(v) in (int, float) and isfinite(v) for v in r) and 0 <= r[0] < r[2] and 0 <= r[1] < r[3]
                    and canvas and (size is None or (r[2] <= size[0] and r[3] <= size[1]))): return False
        return True

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
        """The table's cells that have a position: the only ones a lookup may consult. A cell with none, or with one that cannot be true, is
        counted by the gate (unanchored, dishonest) and is evidence of nothing (Codex R15-3)."""
        return [c for c in table.get('cells') or [] if spans(c.get('anchor'))]


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
        if text.endswith(m) and not splits(numbers(text, markers), len(text) - len(m), len(text)): text = text[:-len(m)].rstrip()  # never a digit cut out of a number (Codex R16-1 class)
        elif text.startswith(m) and not splits(numbers(text, markers), 0, len(m)): text = text[len(m):].lstrip()
    return text


def minus_marks_anywhere(text, markers):
    """The text with the record's own footnote marks deleted wherever they stand, with the commas or spaces between grouped marks (guide 3.2)
    and the space before them: the gap a mark leaves closes up ("features(1):" reads "features:", "Covenants (1)" reads "Covenants"). A mark
    is never cut out of a number ('Segment 215' keeps its '1')."""
    marks = sorted({re.escape(norm(m)) for m in markers if norm(m)}, key=len, reverse=True)
    if not marks: return norm(text)
    one, t = '(?:' + '|'.join(marks) + ')', norm(text); nums = numbers(t, markers)
    return norm(re.sub(r'\s*' + one + r'(?:\s*,?\s*' + one + ')*', lambda m: m.group() if splits(nums, m.end() - len(m.group().lstrip()), m.end()) else '', t))


def without_marks(got, want, markers):
    """Is `got` the key text `want` with the record's own footnote marks printed into it? Marks may sit anywhere — glued to a word, before a
    colon, grouped with commas or spaces between (guide 3.2) — and the space a mark leaves behind closes up. A mark that is part of `want`
    itself is never deleted: every other character of `got` must match `want` in order."""
    g, w = norm(got), norm(want); marks = sorted({norm(m) for m in markers if norm(m)}, key=len, reverse=True)
    if g == w: return True
    if not marks or len(g) <= len(w) or not any(m in g for m in marks): return False  # cheap exits: nothing to delete
    if not any(m in w for m in marks) and squash(minus_marks_anywhere(g, markers)) != squash(w): return False  # when no mark string is part of the key text, deleting them all must leave exactly the key text
    at, nums = {0: {(0, False)}}, numbers(g, markers)  # positions of `got` reached → (position in `want`, gap: the previous character of `got` was deleted — a mark or its separator); forward, no recursion
    for i in range(len(g)):
        for j, gap in at.pop(i, ()):
            for m in marks:
                if g.startswith(m, i) and not splits(nums, i, i + len(m)):  # a mark is never cut out of a number (Codex R16-1 class)
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
    for piece in sorted((norm(x) for x in own if x and norm(x) != want), key=len, reverse=True):
        toks = pieces(rest); rest = re.sub(re.escape(piece), lambda m: m.group() if splits(toks, m.start(), m.end()) else ' ', rest)  # set aside only where it is printed whole (Codex R16-1 class)
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


def mapped_part(unit, anchor):
    """The part of a unit's text that lies at the key's anchor, from the route's own mapping (owner decision (e); Codex R13 C2, R14-1). A unit at
    one place, a unit whose places the key's anchor all overlaps, a table (its cells carry their own places) or a unit placed by bytes (the gate
    certifies its text block by block): its whole text, 'whole'. A unit over several page places (a block across a page break, several boxes)
    of which the key overlaps some: the characters the route maps to those places — `charspan` per place, validated here again: integer bounds
    inside the text, in order, none reaching back — 'mapped'; with no valid mapping, None, 'unmapped': which words lie at the key's place is
    unknown. The key never chooses the split."""
    spans_ = spans(unit.get('anchor')); text = unit.get('text', ''); own = [a for a in spans_ if overlap(a, anchor)]
    if len(spans_) < 2 or len(own) == len(spans_) or unit.get('kind') == 'table' or not all('region' in a for a in spans_): return text, 'whole'
    cs = [a.get('charspan') for a in spans_]
    if not (all(isinstance(c, list) and len(c) == 2 and all(type(v) is int for v in c) and 0 <= c[0] <= c[1] <= len(text) for c in cs) and all(cs[i][0] >= cs[i - 1][1] for i in range(1, len(cs)))): return None, 'unmapped'
    part, end = '', None
    for a in own:
        s, e = a['charspan']; part += ('' if end is None or s == end else ' ') + text[s:e]; end = e
    return part, 'mapped'


def inner_position(unit, anchor, rf):
    """A block's interval inside the unit that carries it, from the route's own data: the characters its mapping puts at the key's place, or the
    positions of its cells in the table's grid order. None when the unit gives no order to read (a whole text, no mapping). Orders the blocks one
    unit carries, never by the key (Codex R15-2; the interval form is Codex's)."""
    if unit.get('kind') == 'table':
        cells = sorted(rf.cells_in(unit), key=lambda c: (c['r'], c['c']))
        hits = [i for i, c in enumerate(cells) if overlap(c.get('anchor'), anchor)]
        return (min(hits), max(hits) + 1) if hits else None
    if mapped_part(unit, anchor)[1] != 'mapped': return None
    cuts = [a['charspan'] for a in spans(unit.get('anchor')) if overlap(a, anchor) and a['charspan'][0] < a['charspan'][1]]
    return (min(a for a, b in cuts), max(b for a, b in cuts)) if cuts else None


def owners(units):
    """Of the field units at one source position, the innermost: those inside which no other of them lies (the field inside prose, not the prose).
    Several innermost units — the same bytes claimed twice — are an ambiguity to report, never a choice by the wanted value (Codex R14-2)."""
    first = lambda u: (spans(u.get('anchor')) or [{}])[0]
    inside = lambda a, b: 'byte_start' in a and 'byte_start' in b and (a['byte_start'], a['byte_end_exclusive']) != (b['byte_start'], b['byte_end_exclusive']) and b['byte_start'] <= a['byte_start'] and a['byte_end_exclusive'] <= b['byte_end_exclusive']
    return [u for u in units if not any(o is not u and inside(first(o), first(u)) for o in units)]


def struck_kept(key_texts, items, anchors=(), vis=None, markers=()):
    """When the key marks words struck (~~…~~), the route must report the same words struck over the field's own text and no others:
    struck evidence stays struck and never becomes active text (key README). Items are the cells or units that carry the text, in reading
    order. Each key string is one run of their joined text — the run the key's anchor names where the item's text is the source's at its
    place, else the only run — and a route strike counts for the part of it inside that run: a strike crossing the field's boundary is
    seen, a strike elsewhere in a shared unit is not. A strike whose text repeats in its item is placed by the source's own formatting
    (the place the source strikes) when the scanner is certain. None when repeated text leaves the run or a strike's place open
    (unresolved, never certified). The record's own footnote marks printed into the items' text are set aside first: the field is then the run of the
    remaining characters, so a strike over a marked label is judged on the label's own characters; a key string that still is no single run is
    checked by text, as before."""
    texts = [squash(it.get('text', '')) for it in items]; T = ''.join(texts)
    if vis is not None and not vis.certain: vis = None  # an uncertain reading of the source places nothing: neither the field's run nor a strike — what only that map could settle stays open (Codex R18-C1, C2)
    marked = set()  # positions of the record's own marks in T (longest mark first, each position claimed once)
    for m in sorted({squash(m) for m in markers if squash(m)}, key=len, reverse=True):
        for i in range(len(T) - len(m) + 1):
            if T.startswith(m, i) and not any(j in marked for j in range(i, i + len(m))): marked.update(range(i, i + len(m)))
    held = [i for i in range(len(T)) if i not in marked]; T2 = ''.join(T[i] for i in held)  # the text with the marks set aside, and where each remaining character stands in T
    bases, pos = [], 0  # (offset in T, flat index in the source) of each item whose text is the source's at its own place
    for it, tx in zip(items, texts):
        first = [x['byte_start'] for x in spans(it.get('anchor')) if 'byte_start' in x]
        j0 = bisect_left(vis.s, min(first)) if vis is not None and first else None
        bases.append((pos, j0 if j0 is not None and vis.flat[j0:j0 + len(tx)] == tx else None)); pos += len(tx)
    def source(a, b):  # does the source print T[a:b] struck through? True / False when the scanner is certain of it, else None
        for (p, j0), tx in zip(bases, texts):
            if p <= a and b <= p + len(tx):
                if j0 is None: return None
                st = {vis.struck_chars[vis.idx[j0 + k - p]] for k in range(a, b)}
                return True if st == {1} and vis.struck_certain else False if st == {0} and vis.plain_certain else None
        return None
    def located():  # offsets in T the key's anchors point at
        out = []
        for a in anchors or () if vis is not None else ():
            for sp in spans(a):
                if 'byte_start' in sp:
                    i0 = bisect_left(vis.s, sp['byte_start'])
                    out += [p + i0 - j0 for (p, j0), tx in zip(bases, texts) if j0 is not None and 0 <= i0 - j0 < len(tx)]
        return out
    strikes = []  # every place each route strike can take in its own item's text
    for (p, _), it, tx in zip(bases, items, texts):
        for x in it.get('struck') or []:
            w = squash(x)
            if w: strikes.append((w, [(p + i, p + i + len(w)) for i in range(len(tx) - len(w) + 1) if tx.startswith(w, i)]))
    verdict, loose = True, []
    for key in key_texts:
        field = squash(key or '')
        if not field: continue
        want = ''.join(squash(m) for m in _STRUCK.findall(key))
        runs = [list(range(i, i + len(field))) for i in range(len(T) - len(field) + 1) if T.startswith(field, i)]  # each run: the positions in T of the field's characters
        if not runs and marked: runs = [held[j:j + len(field)] for j in range(len(T2) - len(field) + 1) if T2.startswith(field, j)]  # the field around the record's own marks
        if not runs: loose.append((field, want)); continue
        if len(runs) > 1: runs = [r for r in runs if r[0] in set(located())] or runs
        readings = set()
        for pos in runs:
            P, inside = set(pos), []
            hits = lambda iv: any(a in P for a in range(iv[0], iv[1]))
            for _, places in strikes:
                here = [iv for iv in places if hits(iv)]; away = [iv for iv in places if not hits(iv)]
                if not here: continue
                if any(source(*iv) for iv in away) and all(source(*iv) is False for iv in here): continue  # the source strikes the other place, not this one: the claim is that one
                if away and not all(source(*iv) is False for iv in away): here.append(None)  # the strike may sit at the other place
                inside.append(here)
            if len(runs) * prod(map(len, inside)) > 4096: return None  # ponytail: too many readings to enumerate — unresolved, never a guess
            for combo in product(*inside):
                readings.add(''.join(T[i] for a, b in sorted(iv for iv in combo if iv) for i in range(a, b) if i in P) == want)
        if readings == {False}: return False
        if len(readings) > 1: verdict = None
    if loose:
        field = ''.join(f for f, _ in loose); want = ''.join(w for _, w in loose)
        if ''.join(w for w, _ in strikes if w in field) != want: return False
    return verdict


def own_bracket_off(text, own):
    """The text without a trailing bracketed phrase, only when that phrase is one of the record's own pieces (E13: its unit line
    or basis words); any other parenthetical stays and must match."""
    m = _TRAILING_BRACKET.search(text)
    if not m: return text
    inner = norm(m.group()).strip(); bare = inner[1:-1].strip() if len(inner) > 1 else inner
    mine = {norm(x) for x in own if x}
    return text[:m.start()] if mine & {inner, bare, norm(text)} else text  # the bracket, or the whole line, is a declared own piece


_TOKEN_NUMBERS = re.compile(r'\d(?:[\d.,]*\d)?')  # a number keeps its separators
_TOKEN_WORDS = re.compile(_TOKEN_NUMBERS.pattern + r'|\w+')  # the words and numbers of a text, by Unicode category


def numbers(nt, marks=()):
    """The numbers of a normalized text as printed: (first, core, end, maybe). `core`..`end`: the digits with their separators and a leading point
    ('.5'; a point glued to a word is the word's: 'No.5'). Before them may stand a '-' or '+' (glyphs folded; a currency symbol between: '-$10').
    The text settles three cases: glued to a word or number on its left it joins or ranges ('COVID-19', '5-10') — no part of the number; touching
    the number, with nothing before it but a space or an opening bracket and no number before that, it is the number's sign, `first` ('-10',
    'of -10', '(-10)'); standing free between two numbers it ranges ('5 - 10'). Anything else is `maybe`: free-standing before the number
    ('stock – 10,000,000', '1.01% - 2.00%', 'LIBOR + 3.8%'), glued to other punctuation ('11%-63%', "2'-0", '(206)-392', 'x=-10', '$-10') or
    touching it after a number ('n.d. -23 -18', 'US2007 -0287831', '0.79% -3.27%') it is a separator, a range, a join, an operator or a sign —
    the text alone cannot tell (Codex R17-C5; each shape is printed in the development texts). A comma group of the record's own marks ('1,2',
    guide 3.2) is marks, not a number (R15-1, R16-1)."""
    own, out = {norm(m) for m in marks}, []
    for m in _TOKEN_NUMBERS.finditer(nt):
        if ',' in m.group() and set(m.group().split(',')) <= own: continue
        core = j = m.start() - (nt[m.start() - 1:m.start()] == '.' and not nt[m.start() - 2:m.start() - 1].isalnum())
        while j and (nt[j - 1].isspace() or unicodedata.category(nt[j - 1]) == 'Sc'): j -= 1  # back over a currency symbol, by Unicode class, and the spaces around it
        s = j - 1 if j and nt[j - 1] in '+-' and not nt[j - 2:j - 1].isalnum() else None  # a dash or plus that no word or number is glued before
        p = s or 0
        while p and nt[p - 1].isspace(): p -= 1
        q = p
        while q and not nt[q - 1].isspace() and not nt[q - 1].isalnum(): q -= 1  # back over the punctuation of what stands before it ('0.79% -3.27%')
        free = s is not None and (p < s or s == 0 or unicodedata.category(nt[s - 1]) == 'Ps')  # nothing glued before it but an opening bracket
        touching = s is not None and not nt[s + 1].isspace()
        sign = free and touching and not nt[q - 1:q].isdigit()  # it touches the number and no number stands before it
        out.append((s if sign else core, core, m.end(), None if s is None or sign or (nt[p - 1:p].isdigit() and not touching) else s))  # free between two numbers, it ranges
    return out


def pieces(nt, words=True, marks=()):
    """The numbers of a normalized text and, with `words`, its words: what a stretch may take whole or not at all."""
    return numbers(nt, marks) + ([(m.start(), m.start(), m.end(), None) for m in _TOKEN_WORDS.finditer(nt)] if words else [])


def splits(toks, a, b):
    """Does the stretch [a, b) take part of a word or number and leave part: some of its characters, its digits without their sign or point, its
    sign alone? A currency symbol or a space between a sign and its digits is no part of the number ('$' is printed in '-$506')."""
    return any((a <= first < b or (a < end and core < b)) and not (a <= first and end <= b) for first, core, end, _ in toks)


def tokens(text):
    return _TOKEN_WORDS.findall(norm(text))


def boundary_equal(got, want):
    """Same characters and the same words and numbers: whitespace may move around punctuation and symbols (E12 reflow), but a
    boundary inside a word or a number may not appear or disappear."""
    return squash(got) == squash(want) and tokens(got) == tokens(want)


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


def redline_apart(item, vis, byte):
    """A word or number boundary the source's own strike-through delimits — a redline printed as one run (`TheExcept`, struck `The`): no boundary
    fault when the item's `struck_at` is the scanner's own answer and the text read apart at those places gives the source's words and numbers."""
    at, text = item.get('struck_at'), item.get('text', '')
    if not at or at != struck_at(vis, item): return False
    if any(type(i) is not int for pair in at for i in pair): return False
    cuts = {i for a, b in at for i in (a, b)}
    return boundary_equal(vis.at_any(byte), ''.join((' ' if i in cuts else '') + c for i, c in enumerate(text)))


def objects(carriers):
    """The route objects (cells or units, every piece of a glued run) behind these carriers."""
    return [o for k in carriers for o in (k.get('parts') or [k['cell'] if k.get('cell') is not None else k.get('unit')])]


def spaced(items, want, parts=False):
    """The text of an item — or of several, a space between them — with a space at its joins (where touching pieces were read as one), but for the
    joins the key's text `want` prints closed: the key's characters are looked up in the text, every place they stand whole — or, where they
    stand nowhere whole (a mark the key does not print among them, or the text only a part of the key's), by the longest runs the two share —
    and a join stays closed where the key prints the characters on its two sides in one word. So of all the ways to read the joins it is the one
    nearest the key (`parts`: as the list of its spaced parts). Not a second reading that may pass: the comparison uses it
    only to tell a word boundary the page alone could show (CSS spacing of touching bytes, a join the source cannot settle — unresolved) from a
    real mismatch (fail)."""
    text, joins = '', []
    for it in [items] if isinstance(items, dict) else items:
        text += ' ' * bool(text); joins += [len(text) + j for j in it.get('joins') or []]; text += it.get('text', '')
    nw = norm(want); wi = [i for i, c in enumerate(nw) if c != ' ']; sw, st, at = squash(nw), squash(text), {}
    ds = [-p for p in range(len(st)) if st.startswith(sw, p)]  # where the key's characters stand whole in the text's
    for m in () if ds else difflib.SequenceMatcher(None, st, sw, autojunk=False).get_matching_blocks(): at.update((m.a + k, m.b + k) for k in range(m.size))  # nowhere whole: the key's character each character of the text is read as, by the longest runs the two share
    out, last = [], 0
    for j in joins:
        q = len(squash(text[:j])); l, r = next((at[i] for i in range(q - 1, -1, -1) if i in at), None), next((at[i] for i in range(q, len(st)) if i in at), None)  # the join, counted in characters, and the key's characters nearest it on either side
        if not (any(0 < q + d < len(sw) and wi[q + d] == wi[q + d - 1] + 1 for d in ds) or (l is not None and r == l + 1 and wi[r] == wi[l] + 1)): out.append(text[last:j]); last = j
    out.append(text[last:]); return out if parts else ' '.join(out)


def runs(items, want):
    """Every run of neighbouring parts of `spaced`, for a check that looks for ONE carrier equal to the key's text: read the other way, a piece
    that touches it is a carrier of its own ('1.' beside 'Busi' + 'ness')."""
    sp = spaced(items, want, True); return [' '.join(sp[i:j]) for i in range(len(sp)) for j in range(i + 1, len(sp) + 1)]


def contains(text, want, marker=False, marks=()):
    """Is `want` printed inside `text` as whole words and numbers? A matching stretch may move whitespace around punctuation and symbols
    (E12), never inside a word or a number, and takes each word and number of `text` whole or not at all: 'note 1' is not printed in
    'note 10', nor '250' in '1,250', nor 'not own' in 'cannot own' (Codex R15-1), nor '10' in '-10' or '5' in '.5' (R16-1); a stretch that itself
    begins with a sign or a point begins at one ('-10' is not printed in '5-10'). A footnote mark (`marker`) may touch a word ('Revenue1'),
    but never cut a number ('1' is not printed in '2015', '1,000' or '1.5'); `marks` grouped by commas are marks. Returns True, False, or None:
    printed there only if the dash or plus before its first number is no sign ('stock – 10,000,000 shares', '11%-63%') — the text cannot
    tell, the caller asks the source (R17-C5)."""
    nt, nw = norm(text), norm(want); sw = squash(nw)
    if not sw: return True
    idx = [i for i, c in enumerate(nt) if not c.isspace()]; st = ''.join(nt[i] for i in idx)
    p = st.find(sw)
    if p == -1: return False
    nums = numbers(nt, marks); toks = pieces(nt, not marker, marks)
    starts = {first for first, *_ in nums} | {maybe for *_, maybe in nums} if nw[0] in '+-.' and any(first == 0 for first, *_ in numbers(nw)) else None  # a stretch that begins with a number's sign or point begins where a number of the text does, or at a free-standing dash before one — never at a hyphen that joins
    open_ = False
    while p != -1:
        a, b = idx[p], idx[p + len(sw) - 1] + 1
        if not splits(toks, a, b) and (starts is None or a in starts) and boundary_equal(nt[a:b], nw):
            if not any(maybe is not None and maybe < a <= core for _, core, _, maybe in nums): return True
            open_ = True  # it begins right after a dash that may be its number's sign
        p = st.find(sw, p + 1)
    return None if open_ else False


def at_place(items, read):
    """For `Grader.printed`: the texts tested that lie at a span of the key — `read` over the items whose own place overlaps it; none there, nothing tested there."""
    return lambda a: (lambda here: read(here) if here else [])([x for x in items if overlap(x.get('anchor'), a)])


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
    p = xml_parser(namespace_separator='}'); stack, open_chunk, found = [], [], []  # the parser the source's reading was certified with: the same declarations (an attribute default a parameter entity declares names the namespace)
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


NEG = {'not', 'no', 'never', 'none', 'nor', 'without', 'cannot'}  # negation: a closed grammatical class, read with the word it governs (E10 R4)
_TOKEN = re.compile(r"[(\-+]?\d(?:[\d,]|[./:-](?=\d))*%?\)?|[^\W\d_]+(?:'[^\W\d_]+)*|\S")  # a number with sign, parentheses, percent and separators between digits; a word; any other symbol alone
_digit = lambda w: any(c.isdigit() for c in w)
_symbol = lambda w: len(w) == 1 and unicodedata.category(w) in ('Sc', 'Sm')  # a currency or mathematical sign, by Unicode class, no list of ours
_neg = lambda w: w.lower() in NEG or w.lower().endswith("n't")


def reading_units(s):
    """Reading units of an approximate text: a currency or sign symbol joined to its number ('€20', '20%'), a number joined to the word that follows
    it — its unit or qualifier ('10 shares', '20 million'; deliberately also an ordinary word, so a changed word beside a number counts as critical),
    a negation joined to the word it governs ('not buy'); other words and symbols alone."""
    out = []
    for w in _TOKEN.findall(norm(s).replace('−', '-')):
        last = out[-1] if out else None
        if last is not None and ' ' not in last and ((_symbol(last) and _digit(w)) or (_digit(last) and (_symbol(w) or w[:1].isalpha())) or (_neg(last) and w[:1].isalpha())):
            out[-1] = last + ('' if _symbol(last) or _symbol(w) else ' ') + w
        else: out.append(w)
    return out


def critical(got, want):
    """Every ordered difference between an approximate (OCR) text and its reference, and which of them touch critical facts (E10 R4; Codex R13,
    R14-5). `edits`: the aligned spans that differ (reference tokens → output tokens), nothing filtered. `critical`: among them the tokens holding a
    digit, a currency or sign symbol, or a negation — compared position by position when both texts hold as many such tokens (two swapped values
    both show), by the alignment otherwise. `other`: the remaining differences, kept for review, never declared harmless."""
    crit = lambda w: _digit(w) or any(unicodedata.category(c) in ('Sc', 'Sm') for c in w) or _neg(w.split()[0])
    a, b = reading_units(want), reading_units(got); ca, cb = [w for w in a if crit(w)], [w for w in b if crit(w)]
    ops = [(op, a[i1:i2], b[j1:j2]) for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op != 'equal']
    miss, extra = [w for _, x, _ in ops for w in x], [w for _, _, y in ops for w in y]
    if len(ca) == len(cb) and ca != cb: cm, ce = [x for x, y in zip(ca, cb) if x != y], [y for x, y in zip(ca, cb) if x != y]
    else: cm, ce = [w for w in miss if crit(w)], [w for w in extra if crit(w)]
    return {'edits': [{'op': op, 'reference': x, 'output': y} for op, x, y in ops], 'critical': {'missing': cm, 'extra': ce},
            'other': {'missing': [w for w in miss if not crit(w)], 'extra': [w for w in extra if not crit(w)]}, 'reference_numbers': sum(1 for w in a if _digit(w))}


def wer_counts(got, want):
    """Word error rate with its parts: the substitutions, deletions and insertions of one minimal edit script that turns the output's words into
    the reference's, over the reference's words; `recovered` = reference words read as they are (0 for an empty output: zero recovery)."""
    x, y = norm(want).split(), norm(got).split(); n, m = len(x), len(y)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1): d[i][0] = i
    for j in range(1, m + 1): d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1): d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (x[i - 1] != y[j - 1]))
    s = dl = ins = 0; i, j = n, m
    while i or j:  # back along one minimal path: a match or substitution first, then a deletion, then an insertion
        if i and j and d[i][j] == d[i - 1][j - 1] + (x[i - 1] != y[j - 1]): s += x[i - 1] != y[j - 1]; i -= 1; j -= 1
        elif i and d[i][j] == d[i - 1][j] + 1: dl += 1; i -= 1
        else: ins += 1; j -= 1
    return {'reference': n, 'recovered': n - s - dl, 'substituted': s, 'deleted': dl, 'inserted': ins, 'rate': round((s + dl + ins) / max(1, n), 3)}


def wer(got, want):
    """Word error rate: the substitutions, deletions and insertions that turn the output's words into the reference's, over the reference's words."""
    return wer_counts(got, want)['rate']


# ------------------------------------------------------------------------------------------------- grading one
class Grader:
    def __init__(self, t, rf):
        self.t, self.rf, self.rows = t, rf, []
        self.lenient = self.undecided = False  # the dash question (`printed`): is an undecided dash read as no sign; did the strict reading meet one
        self.touching, self.unsure = True, False  # the join question (`adjacent`): how a join the source cannot settle is read; did the grading meet one
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
                    all(lo <= a < b <= ta['byte_end_exclusive'] and (not rf.vis.certain or squash(rf.vis.at(a, b)) == squash(pc['text'])) for a, b in at)):  # the text is compared only where the source's reading is certain: an uncertain reading proves no key defect
                raise ValueError(f"{t['key_id']}: table_context {pc.get('text')!r} is not the text at an anchor inside this table or its title block (fix the key package)")
            self.table_context.append(pc['text'])

    def same(self, got, want):
        return same(got, want, self.markers, self.own)

    def printed(self, texts, want, anchors=(), at=None, **kw):
        """`contains` over one text or several, with the source as arbiter where a dash or plus stands before the wanted number and the text alone
        cannot tell a separator from a sign (Codex R17-C5). The key's own span for the phrase decides: where the source prints the phrase at that
        span with a dash or plus before it, and a text prints that same stretch — the source's dash through the phrase — the route kept the source's
        text and the phrase is printed; where the source prints none there, or another one, the route's is its own — not printed. With no such
        span, no source text (a PDF, a field found by text) or an uncertain reading of the source the question stays open. An open question proves
        nothing: read strictly it is not printed (so a text that prints the phrase plainly, or by the source's proof, always wins over one that
        leaves it open — Codex R18-C3); only when the strict reading does not pass does the caller read it leniently, and a pass that needs it
        is `unresolved` (`numeric_boundary`) — never a guessed negative, never a pass. `at` (`at_place`), when the anchors given are a whole
        field's: the texts tested that lie at one of them — a span arbitrates only over the route's text at its own place (from what the source
        prints before the phrase through the phrase), so a dash the source prints at one place certifies none the route prints at another, a
        place the route is plainly wrong at answers for no other, and texts that lie at a signed place and at an unsigned one decide nothing."""
        texts = [texts] if isinstance(texts, str) else texts; rs = [contains(x, want, **kw) for x in texts]
        if True in rs or None not in rs: return True in rs
        vis, found, proof = self.rf.vis, [], None
        for y in anchors or () if vis is not None and vis.certain else ():
            for a in (x for x in spans(y) if 'byte_start' in x):
                if boundary_equal(vis.at(a['byte_start'], a['byte_end_exclusive']), want):  # the source prints the wanted phrase at the key's own span: what stands before it there?
                    j = bisect_left(vis.starts, a['byte_start']) - 1
                    while j >= 0 and (not squash(vis.text[j]) or unicodedata.category(vis.text[j]) == 'Sc'): j -= 1
                    here = dict(a, byte_start=vis.starts[j]) if j >= 0 else a  # the place: from what stands before the phrase (a route may cut its text right at the dash) through the phrase
                    mine = [x for x in (texts if at is None else at(here)) if contains(x, want, **kw) is None]  # the texts there that leave the question open: one that is plainly wrong answers nothing
                    if mine: found.append((mine, vis.at(vis.starts[j], a['byte_end_exclusive']) if j >= 0 and norm(vis.text[j]) in ('+', '-') else None))  # with the source's own stretch from its sign, or None where it prints none
        for mine, stretch in found:  # texts that lie at a place the source signs and at one it does not decide nothing: which of their dashes stands where is not known
            if all((x is None) == (stretch is None) for m, x in found if m == mine): proof = proof or (stretch is not None and any(contains(x, stretch, **kw) is True for x in mine))
        if proof is None: self.undecided = self.undecided or not self.lenient; return self.lenient
        return proof

    def row(self, check, verdict, reason=None, detail=None):
        self.rows.append({'key_id': self.t['key_id'], 'file_id': self.t['file_id'], 'split': self.t['split'], 'format': self.t['format'],
                          'check': check, 'verdict': verdict, 'reason': reason, 'detail': detail})

    def field(self, name, fn, *args):
        """Run one check over every accepted value. Each is judged whole — its text, then its strikes — first strictly (only what is proved counts),
        then, where a dash was left undecided, leniently. The first value that passes wins; else the first left open (a value that may hold is no
        failure, whatever the order — Codex R18-C3); else the first failure. Only the rows of the value reported stay."""
        if name in self.t['excluded']: return self.row(name, 'excluded')
        alts = alternatives(self.t, name)
        if not alts: return
        def once(value, alt):  # one reading of one accepted value, and whether its text was found
            self.matched = None; r = fn(value, alt, *args)  # a field may say which carriers matched; the struck check then reads those, not every occurrence the key points at
            if r[0] != 'pass': return r, False
            anchors = anchors_of(self.t, name, alt)  # struck words the key marks must still be struck where the route carries them
            items = self.matched or ([c for a in anchors for c in self.rf.cells_at(a)] + [c for a in anchors for u in self.rf.units_at(a, exclude=('clutter',)) for c in ([x for x in self.rf.cells_in(u) if any(overlap(x.get('anchor'), b) for b in anchors)] if u.get('kind') == 'table' else [u])] if anchors else (self.rf.cells_in(self.tb) if getattr(self, 'tb', None) else []))  # the matched carriers; else a table at the anchor contributes only the cells at this field's support, never another row's strikes
            kept = struck_kept(strings_in(value), list({id(x): x for x in items if x is not None}.values()), anchors, self.rf.vis, self.markers)
            return (r if kept is True else ('fail' if kept is False else 'unresolved', 'struck', None)), True
        results = []
        for alt, value in alts:
            if value in (None, [], {}): return self.row(name, 'na')
            n, self.lenient, self.undecided = len(self.rows), False, False
            r, found = once(value, alt)  # first only what is proved counts: a dash the text and the source leave undecided prints nothing
            if not found and self.undecided:  # not proved — would it hold if those dashes are no signs? Then the value is open, neither failed nor passed (Codex R17-C5, R18-C3)
                del self.rows[n:]; self.lenient = True; r2, _ = once(value, alt); self.lenient = False
                r = ('unresolved', 'numeric_boundary', r2[2]) if r2[0] == 'pass' else r if r[0] == 'unresolved' else r2  # a failure stands only when both readings fail — a strike lost or invented fails either way
            results.append((r, self.rows[n:])); del self.rows[n:]
            if r[0] == 'pass': break
        (verdict, reason, detail), side = next((x for x in results if x[0][0] == 'pass'), None) or next((x for x in results if x[0][0] == 'unresolved'), results[0])
        self.rows += side; self.row(name, verdict, reason, detail)

    # ---- cells
    def grade_cell(self): return self.both(self.cell)

    def cell(self):
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
            hit = lambda text: any(self.same(text, w)[0] if equal else contains(text, w) is not False for w in pieces)
            found += [(tb, c, None) for c in (self.rf.cells_in(tb) if tb else []) if hit(c.get('text', ''))]
            found += [(None, None, u) for u in self.rf.placed if u.get('kind') not in ('table', 'clutter') and hit(u.get('text', ''))]  # by text, among units that have a position (Codex R15-3)
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
            if same_place and squash(p['text']) and squash(k['text']) and self.adjacent(p['anchor'], k['anchor']): merged[-1] = dict(p, text=p['text'] + k['text'], anchor=spans(p['anchor']) + spans(k['anchor']), joins=(p.get('joins') or []) + [len(p['text'])], parts=(p.get('parts') or [p['cell'] if p['cell'] is not None else p['unit']]) + [k['cell'] if k['cell'] is not None else k['unit']])
            else: merged.append(k)
        return merged

    def merged_units(self, units):
        """Text units in order; consecutive units whose anchors touch in the source (span-level output) are read as one; others stay apart;
        a unit with no characters is never glued."""
        out = []
        for u in sorted(units, key=lambda u: (u.get('_order', 0), order_key(u.get('anchor')))):
            p = out[-1] if out else None
            if p is not None and u.get('kind') != 'table' and p.get('kind') != 'table' and squash(p.get('text', '')) and squash(u.get('text', '')) and self.adjacent(p.get('anchor'), u.get('anchor')):
                out[-1] = dict(p, text=p.get('text', '') + u.get('text', ''), anchor=spans(p.get('anchor')) + spans(u.get('anchor')), struck=(p.get('struck') or []) + (u.get('struck') or []), links=(p.get('links') or []) + (u.get('links') or []), joins=(p.get('joins') or []) + [len(p.get('text', ''))])
            else: out.append(u)
        return out

    def merged(self, cells):
        """Cells in reading order; consecutive pieces at one grid position whose anchors touch in the source are read as one cell
        (E12, span-level output), every other cell stays apart. The first piece's cell object is kept, so identity checks still hold."""
        out = []
        for c in sorted(cells, key=lambda c: (c['r'], c['c'], order_key(c.get('anchor')))):
            p = out[-1] if out else None
            if p is not None and (p['r'], p['c']) == (c['r'], c['c']) and self.adjacent(p.get('anchor'), c.get('anchor')):
                out[-1] = dict(p, text=p.get('text', '') + c.get('text', ''), anchor=spans(p.get('anchor')) + spans(c.get('anchor')), markers=(p.get('markers') or []) + (c.get('markers') or []), struck=(p.get('struck') or []) + (c.get('struck') or []), joins=(p.get('joins') or []) + [len(p.get('text', ''))])
            else: out.append(c)
        return out

    def adjacent(self, a, b):
        """Does the output's own mapping put piece b right after piece a in the source, with nothing (not even a space) between? Three answers: proved
        touching, proved apart, or unknown. A certain reading of the source proves either. Under an uncertain one (a stylesheet may hide a <br>
        or set a <span> on its own line) only what needs no reading is proved: where no tag stands between the two pieces their bytes settle it —
        characters between them, or the two meeting inside one run of text. (The route's own text between them proves nothing: it may be text the
        page hides.)
        Every other join is unknown: read as `self.touching` says and noted, so `both` grades the target under the two readings (Codex R18-C2).
        The key never has a say (R9-1)."""
        sa, sb = [x for x in spans(a) if 'byte_start' in x], [x for x in spans(b) if 'byte_start' in x]
        if not sa or not sb or self.rf.vis is None: return False
        end, start = max(x['byte_end_exclusive'] for x in sa), min(x['byte_start'] for x in sb)
        if end > start: return False
        if self.rf.vis.certain: return self.rf.vis.at(end, start) == ''
        raw = self.rf.raw; gap = raw[end:start]
        if b'<' not in gap and b'\x00' not in gap and (gap or (raw[end - 1:end] != b'>' and raw[start:start + 1] != b'<')): return not gap  # no tag between them, nor at either edge where they meet (a null byte is no character: the parser drops it)
        self.unsure = True; return self.touching

    def both(self, grade):
        """Grade under both readings of the joins an uncertain source leaves open: read as touching, then as apart. A check the two readings judge
        alike stands — a wrong text fails either way, whatever reason each reading gives for it; a check that needs no join is untouched. One they
        judge differently depended on a join nobody proved: `unresolved` (`adjacency`), never a pass and never a fail (Codex R18-C2). A target has
        one row per check (`field`), so the rows of the two readings pair by check."""
        n, self.touching, self.unsure = len(self.rows), True, False; out = grade()
        if self.unsure:
            first = self.rows[n:]; del self.rows[n:]; self.touching = False; grade(); self.touching = True
            second = self.rows[n:]; apart = {r['check']: r['verdict'] for r in second}; seen = {r['check'] for r in first}
            self.rows[n:] = [r if apart.get(r['check']) == r['verdict'] and r['check'] in seen else dict(r, verdict='unresolved', reason='adjacency', detail=None) for r in first + [r for r in second if r['check'] not in seen]]  # (a check only one reading wrote was judged differently too)
        return out

    def pieces_match(self, texts, want, anchors=None, cells=None):
        """Do these route pieces, in order, spell the key text `want`? Joins are read from the source alone: pieces whose anchors touch read
        as one, every other join as a space. A piece boundary inside a word of the key is a fault unless the pieces touch in the source
        (E12: span-level output; counted as `fragmented`) — and, for table cells, unless both pieces sit at one grid position: two cells
        show two words whatever the bytes say. Where touching pieces meet inside what the key prints as two words, the page may space them
        (CSS): reported unresolved, never pass or fail — and only when that reading of those joins gives the key's text: a boundary broken or
        glued anywhere else is a fault under every reading. Returns (ok, reason, fragments); ok None = unresolved."""
        nw = norm(want); idx = [i for i, c in enumerate(nw) if not c.isspace()]; sq = ''.join(nw[i] for i in idx); pos = frag = 0; prev = None
        out, page, pending = '', '', False  # the pieces as the source prints them: a proven touching join reads as nothing, every other join as a space; `page`: the same with the space the page may show at a touching join
        for n_, tx in enumerate(texts):
            n = len(squash(tx)); end = pos + n
            if not n: continue
            if not sq.startswith(squash(tx), pos): return False, 'text', frag
            sep = css = ''
            if prev is not None:
                apart = bool(cells) and (cells[prev]['r'], cells[prev]['c']) != (cells[n_]['r'], cells[n_]['c'])  # two cells show two words whatever the bytes say
                touching = not apart and bool(anchors) and self.adjacent(anchors[prev], anchors[n_])
                glue = idx[pos] == idx[pos - 1] + 1  # the key prints no space here
                if glue and touching: frag += 1
                elif glue and not apart and bool(anchors) and all(any('region' in x for x in spans(anchors[i])) for i in (prev, n_)): pending = True  # boxes cannot prove the join
                elif glue and nw[idx[pos]].isalnum() and nw[idx[pos - 1]].isalnum(): return False, 'word_split', frag  # a word or number split without proof
                elif touching: css = ' '  # the bytes touch where the page prints a space: CSS may space them; a word boundary only the page shows cannot be certified from the output
                else: sep = ' '
            out += sep + norm(tx); page += (sep or css) + norm(tx); pos, prev = end, n_
        if pos != len(sq): return False, 'text', frag
        if boundary_equal(out, nw): return (None, 'adjacency', frag) if pending else (True, None, frag)
        return (None, 'adjacency', frag) if boundary_equal(page, nw) else (False, 'spacing', frag)

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
        if True in said[:2]:  # the cancellation on the very cells that spell the value: lost or invented, either changes the number's meaning
            kept = struck_kept([display], shown if said[0] is True else cells, [t['anchor']], self.rf.vis, self.markers)
            return self.row('value', 'pass' if kept is True else 'unresolved' if kept is None else 'fail', None if kept is True else 'struck')
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
        if not ok and self.same(spaced(sorted(cands, key=lambda c: (c['r'], c['c'])), ' '.join(pieces)), ' '.join(pieces))[0]: return 'unresolved', 'adjacency', joined(cands)
        if not ok: return 'fail', 'text', joined(cands)
        if not any(row_hit(c, vr) for c in cands) or any(abs(c['r'] - vr) > 1 for c in cands): return 'fail', 'row', None
        self.matched = list(cands)  # merged cells carry their pieces' strikes
        return 'pass', None, 'marker_in_label' if flag == 'marker_in_text' else flag or ('anchor_unknown' if not anchors else None)

    def row_context(self, value, alt, tb, vr):
        pool = self.merged(self.rf.cells_in(tb))
        for item in value:
            cells = [c for c in pool if row_hit(c, vr) and self.same(c.get('text', ''), item['text'])[0]]  # a row may print the same text twice: the one under the named header is meant
            if not cells: return ('unresolved', 'adjacency', item['text']) if any(row_hit(c, vr) and self.same(spaced(c, item['text']), item['text'])[0] for c in pool) else ('fail', 'row', item['text'])
            self.matched = (self.matched or []) + list(cells)
            if item.get('header') and item['header'] != 'position':
                heads = [c for c in pool if c['r'] < vr] + [k['cell'] for k in self.carriers(anchors_of(self.t, 'row_context', alt), [item['header']])
                                                                           if k['cell'] is not None and k['table'] is not tb and k['order'] < tb['_order']]  # or printed in the first part of a continued table (E1, addendum C5)
                if not any(col_hit(h, c['c']) and self.same(h.get('text', ''), item['header'])[0] for c in cells for h in heads):
                    if any(col_hit(h, c['c']) and self.same(spaced(h, item['header']), item['header'])[0] for c in cells for h in heads): return 'unresolved', 'adjacency', item['header']
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
                if match_pieces([spaced(k, ' '.join(pieces)) for k in cands], pieces, self.markers, self.own + self.table_context)[0]: return 'unresolved', 'adjacency', None
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
        if not ok and match_pieces([spaced(k, ' '.join(pieces)) for k in usable], pieces, self.markers, self.own + self.table_context)[0]: return 'unresolved', 'adjacency', norm(got)
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
        if not ok and match_pieces([spaced(k, value) for k in cars], [value], self.markers, self.own + self.table_context)[0]: return 'unresolved', 'adjacency', None
        return ('pass', None, flag) if ok else ('fail', 'text', ' '.join(k['text'] for k in cars))

    def lead_in(self, value, alt, tb, vr):
        anchors = anchors_of(self.t, 'lead_in', alt)
        cars = [k for k in self.carriers(anchors, [value], tb) if self.in_order(k, tb, vr) and (k['table'] is not tb or k['cell']['r'] < vr)]
        if not cars: return 'fail', 'missing', None
        hit = next((k for k in cars if boundary_equal(k['text'], value)), None)
        if hit is None and self.pieces_match([k['text'] for k in cars], value, [anchor_of(k) for k in cars])[0]: hit = cars[-1]
        flag = None
        if hit is None:
            got = norm(' '.join(k['text'] for k in cars))
            if self.printed(got, value, anchors, at_place(cars, lambda ks: [norm(' '.join(k['text'] for k in ks))])): hit, flag = cars[-1], 'contained'  # whole and in order inside the carriers (addendum C6), as whole words and numbers (Codex R16-1 class)
            elif self.printed(spaced(cars, value), value, anchors, at_place(cars, lambda ks: [spaced(ks, value)])): return 'unresolved', 'adjacency', None
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
                    text, apart, used = cars[a]['text'], [' '.join(sp[x:]) for sp in [spaced(cars[a], want, True)] for x in range(len(sp))], [cars[a]]
                    for b in range(a + 1, len(cars)):
                        if len(squash(text)) > len(sw): break
                        text += ('' if self.adjacent(anchor_of(cars[b - 1]), anchor_of(cars[b])) else ' ') + cars[b]['text']  # read as the source prints the pieces
                        apart = [x + ' ' + spaced(cars[b], want) for x in apart]; used.append(cars[b])  # the other reading of every touching join (the run may begin at any part of its first carrier), for the unresolved verdict only
                    if starts(text): hit, run_in, win = cars[a], True, used; break
                    if any(starts(x) for x in apart): open_run = True  # the pieces touch where the heading prints a space: the page may space them
                if hit is None and open_run: return 'unresolved', 'adjacency', pieces[i]
            if hit is None:
                if any(heading_eq(x, pieces[i]) for k in cars for x in runs(k, pieces[i])): return 'unresolved', 'adjacency', pieces[i]  # the pieces touch where the heading prints a space: the page may space them
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
            read = lambda ks, apart=False: [x for text in [spaced(ks, want) if apart else ' '.join(k['text'] for k in ks)] for x in (text, minus_marks_anywhere(text, self.markers))]  # the phrase, with the record's own marks printed into it; spacing by the boundary rule
            holds = lambda ks, apart=False: self.printed(read(ks, apart), want, anchors, at_place(ks, lambda here: read(here, apart)))
            cars = [k for k in at if holds([k])] or (at if holds(at) else [])  # a phrase read across pieces: every piece carries it
            if not cars and holds(at, True): return 'unresolved', 'adjacency', phrase
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
        if squash(value) and self.printed(' '.join(c.get('text', '') for c in V), value, anchors, at_place(V, lambda cs: [' '.join(c.get('text', '') for c in cs)])): self.matched = list(V); return 'pass', None, 'in_value_cell'  # printed inside the value's own cells, as whole words (Codex R15-1 class)
        if any(self.same(x, value)[0] for k in cars for x in runs(k, value)): return 'unresolved', 'adjacency', None
        return ('fail', 'text', ' '.join(k['text'] for k in cars)) if cars else ('fail', 'missing', None)

    def periods(self, value, alt, tb, vr, vcols):
        change = any(g.get('role') in ('compared', 'comparison') for g in value)  # a change between periods (guide 3.10, addendum C2): its parts head the compared columns
        for group in value:
            for part in group.get('parts') or []:
                want, a = norm(part['text']), part.get('anchor')
                cells = self.merged(self.rf.cells_at(a, tb)) if a else []
                if cells:
                    if not self.same(joined(cells), want)[0] and not self.printed([c.get('text', '') for c in cells], want, [a]):
                        if self.same(spaced(sorted(cells, key=lambda c: (c['r'], c['c'])), want), want)[0] or self.printed([spaced(c, want) for c in cells], want, [a]): return 'unresolved', 'adjacency', part['text']
                        return 'fail', 'text', part['text']
                    self.matched = (self.matched or []) + list(cells)
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
                cars = self.carriers([a], [part['text']], tb, equal=False) if a else [{'text': u.get('text', ''), 'unit': u} for u in self.rf.placed if u.get('kind') not in ('table', 'clutter')]
                hit = [k for k in cars if contains(k['text'], want) is True or (k.get('unit') and want == local(k['unit'].get('name', '')))] or [k for k in cars if self.printed(k['text'], want, [a])]  # a plain match first; else one the source must confirm
                if not hit and not self.printed(' '.join(k['text'] for k in cars), want, [a]):
                    if self.printed(spaced(cars, want), want, [a]): return 'unresolved', 'adjacency', part['text']
                    return 'fail', 'missing', part['text']
                self.matched = (self.matched or []) + objects(hit or cars)
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
        linked, own_marks = [], {norm(m['marker_text']) for m in value}
        for m in value:
            mark, a = m['marker_text'], m.get('anchor')
            cars = self.carriers([a], [mark], tb) if a else []
            apart = any(k['cell'] is not None and mark in (k['cell'].get('markers') or []) for k in cars) or any(squash(k['text']) == squash(mark) for k in cars)
            if not apart:
                if any(k['cell'] in V for k in cars): return 'fail', 'marker_glued', mark
                if not self.printed([k['text'] for k in cars], mark, [a], marker=True, marks=own_marks): return 'fail', 'marker_missing', mark  # glued to a label or title: allowed, flagged there; a digit inside a number is no mark; a comma group of the record's own marks is marks (guide 3.2)
            if m.get('note_anchor'):
                # the note's body, with its own mark set apart, must sit at the note's anchor: alone, spaced, split into
                # pieces, or inside a "Notes:" block that holds several notes
                body = norm(minus_markers(m.get('note_text') or '', [mark]))
                at_note = self.carriers([m['note_anchor']], [m.get('note_text') or ''], tb)
                notes = [k for k in at_note if body and self.printed(minus_markers(k['text'], [mark]), body, [m['note_anchor']])] or ([at_note[0]] if at_note and body and self.printed(' '.join(k['text'] for k in at_note), body, [m['note_anchor']]) else [])
                if not notes: return ('unresolved', 'adjacency', mark) if any(self.printed(minus_markers(spaced(k, body), [mark]), body, [m['note_anchor']]) for k in at_note) else ('fail', 'missing_note', mark)
                k = notes[0]; self.matched = (self.matched or []) + objects([k]) + objects([c for c in cars if squash(c['text']) == squash(mark)])
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
            self.matched = (self.matched or []) + list(cells)
            pending = not exact and spelt is None  # association proven, join not: unresolved unless something below fails
        else: pending = False
        for ev in value.get('evidence') or []:
            hits = self.merged(self.rf.cells_at(ev['anchor'], tb)) + self.merged_units(self.rf.units_at(ev['anchor']))
            held = [h for h in hits if self.printed(h.get('text', ''), ev['text'], [ev['anchor']])]
            if not held:
                if any(self.printed(spaced(h, ev['text']), ev['text'], [ev['anchor']]) for h in hits): pending = True; continue  # evidence split where the page alone could show the space
                return 'fail', 'evidence', ev['text']
            self.matched = (self.matched or []) + held
        return ('unresolved', 'adjacency', None) if pending else ('pass', None, None)

    # ---- XML
    def grade_xml(self):
        t, rf = self.t, self.rf
        V = owners(rf.units_at(t['anchor'], kinds=('field',), exclude=()))  # the field that owns the key's position: the innermost there, never the first in the list nor one picked by the wanted value (Codex R14-2)
        if not V: return None
        if len(V) > 1: self.row('value', 'unresolved', 'ambiguous'); self.row('row_label', 'unresolved', 'ambiguous'); return V[0]  # the same bytes claimed by several fields
        v = V[0]; f = t['fields']; printed = f.get('printed_value') or ''
        if rf.vis is None or not rf.vis.certain:
            self.row('value', 'unresolved', 'source_reading'); self.row('row_label', 'unresolved', 'source_reading'); return v
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
        group = v.get('group') or {}; inst = group.get('at'); inside = lambda u: inst is not None and (u.get('group') or {}).get('at') == inst  # the same instance: one stated, and the same — a field that names none is in none (an absent value is no agreement)
        same_group = [u for u in rf.placed if u.get('kind') == 'field' and inside(u)]  # the fields of the same instance: the one that starts at the same source place (names and "n of m" alone mix two first children of two parents); a field with no true position proves nothing (Codex R15-3)
        ok = True
        for item in f.get('row_context') or []:
            if item['header'] == 'position': ok &= f"{group.get('index')} of {group.get('count')}" == item['text']
            else: ok &= any(local(u.get('name', '')) == item['header'] and norm(u.get('text', '')) == norm(item['text']) for u in same_group)
        if f.get('row_context'): self.row('row_context', 'excluded' if 'row_context' in ex else 'pass' if ok else 'fail', None if ok or 'row_context' in ex else 'group')
        if f.get('unit_printed'):
            declared, fields = (t['support'].get('unit_printed') or {}).get('anchors') or [], [u for u in rf.placed if u.get('kind') == 'field']; self.lenient = self.undecided = False
            carries = lambda u: self.printed(u.get('text', ''), f['unit_printed'], declared, at_place([u], lambda us: [u.get('text', '')])) or norm(f['unit_printed']) == norm(local(u.get('name', '')))  # an XML unit may be a printed text (a security title, as whole words) or the element's own name (percentOfClass, anchored on its tag)
            if 'unit_printed' in ex: self.row('unit_printed', 'excluded')
            elif declared:  # the key names the unit's source place: the field that owns that place must carry it, no other field stands in (Codex R13 C3, R14-2)
                found = [owners([u for u in fields if overlap(u.get('anchor'), a)]) for a in declared]
                if any(len(o) > 1 for o in found): self.row('unit_printed', 'unresolved', 'ambiguous')
                else:
                    at = [o[0] for o in found if o]; hit = any(carries(u) for u in at)  # read strictly first: a field that proves the unit beats one that leaves a dash open (Codex R18-C3)
                    if not hit and self.undecided: self.lenient = True; open_ = any(carries(u) for u in at); self.lenient = False  # printed only if an undecided dash is no sign, and the source could not say (R17-C5)
                    else: open_ = False
                    self.row('unit_printed', 'unresolved' if open_ else 'pass' if hit else 'fail', 'numeric_boundary' if open_ else None if hit else 'missing' if not at else 'text')
            else:  # no declared place: the word in this instance proves no association with the value (unresolved), the word elsewhere none at all
                here = [u for u in fields if inside(u)]; near = any(carries(u) for u in here)
                if not near and self.undecided: self.lenient = True; near = any(carries(u) for u in here); self.lenient = False  # an undecided dash is no proof of absence either
                self.row('unit_printed', 'unresolved' if near else 'fail', 'support' if near else 'missing', 'anchor_unknown')
        self.field('periods', self.periods, {'_order': v['_order'], 'cells': []}, 0, (0, 1))
        for name in T4:
            if name in f: self.row(name, 'excluded' if name in ex else 'not_t1')
        return v

    # ---- structure
    def grade_structure(self): return self.both(self.structure)

    def structure(self):
        t, rf, f = self.t, self.rf, self.t['fields']
        # a block may come back as text units, as one image unit, as ordered blocks (a scanned page) or inside a layout table
        units = rf.units_at(t['anchor'], exclude=('clutter',))
        carries = lambda u: u.get('kind') != 'table' or any(overlap(c.get('anchor'), t['anchor']) for c in rf.cells_in(u))  # a table whose span covers the block but whose cells lie elsewhere (a flattened nested table) does not carry it
        units = [u for u in units if carries(u)] or units
        if not units: return None
        parts = {id(u): mapped_part(u, t['anchor']) for u in units}  # each unit's text at the key's place, by the route's own mapping — applied before any comparison (Codex R14-1)
        def text_of(u):
            if u.get('kind') != 'table': return parts.get(id(u), (u.get('text', ''), 'whole'))[0] or ''
            cells = [c for c in rf.cells_in(u) if overlap(c.get('anchor'), t['anchor'])] or rf.cells_in(u)
            return ' '.join(c.get('text', '') for c in self.merged(cells))
        mapped, unmapped = any(parts[id(u)][1] == 'mapped' for u in units), any(parts[id(u)][1] == 'unmapped' for u in units)
        want = norm(f.get('printed_text') or ''); got = norm(' '.join(text_of(u) for u in self.merged_units(units)))  # touching pieces read as one; the reference phrase and the WER see the block as printed
        block = [dict(u, text=text_of(u)) for u in self.merged_units(units)]  # the block with its joins, for the other reading of them (the unresolved verdict only)
        if 'printed_text' in t['excluded']: self.row('printed_text', 'excluded'); ok = True
        elif unmapped: self.row('printed_text', 'unresolved', 'page_map', {'wer': wer(got, want)}); ok = None  # a unit over several places with no character mapping: which words lie at the key's place is unknown
        else:
            ok, why, frag = self.pieces_match([text_of(u) for u in units], want, [u.get('anchor') for u in units])
            held = contains(text_of(units[0]), want) if ok is False and len(units) == 1 and mapped else False
            if held is None: ok, why = None, 'numeric_boundary'  # the part holds the key's text only if a free-standing dash before its number is no sign: a page box has no source text to ask (Codex R17-C5)
            elif held: ok, why = True, None  # owner 2026-10-04 (e): the block is the part of a paragraph the route read whole across a page break; the part mapped to the key's place holds the key's text in order
            elif ok is False and why == 'text' and len(units) == 1 and mapped and contains(units[0].get('text', ''), want): why = 'page'  # the words exist in the unit, but the route maps them to another place: a contradiction, not a transcription difference
            continued = bool(mapped) and ok is True  # the block is the part of a unit the route read across several places, taken by the route's own mapping
            bearing = [c for u in units for c in ([x for x in rf.cells_in(u) if overlap(x.get('anchor'), t['anchor'])] or [u] if u.get('kind') == 'table' else [u])]  # the text-bearing items: a block laid out in a table is its cells at the target's anchor, never the whole table
            if ok:  # the words survive, but a cancelled word may have become active, or the wrong one cancelled
                kept = struck_kept([f.get('printed_text') or ''], bearing, [t['anchor']], rf.vis, self.markers)
                if kept is not True: ok, why = kept, 'struck'
            if t.get('approximate') and (ok is True or (ok is False and why in ('text', 'word_split'))):  # a picture's text is approximate evidence (owner decision (a), E10 R4): the transcription differences are reported, never a pass; a wrong place, a strike or an unknown mapping stays what it is (Codex R14-3)
                w = wer_counts(got, want); self.row('printed_text', 'approximate', None, {'word_error_rate': w['rate'], 'words': {k: w[k] for k in ('reference', 'recovered', 'substituted', 'deleted', 'inserted')}, **critical(got, want)})
            else: self.row('printed_text', 'pass' if ok else 'unresolved' if ok is None else 'fail', None if ok else why, ({'continued': True} if continued else {'fragmented': frag} if frag else None) if ok else {'wer': wer(got, want)})
        main = next((u for u in units if u.get('kind') != 'table'), units[0])
        if f.get('kind') in LOOSE_KINDS: self.row('kind', 'na', None, main.get('kind'))
        elif f.get('kind'):
            ok = KIND.get(main.get('kind')) == f['kind']; self.row('kind', 'pass' if ok else 'fail', None if ok else 'kind', main.get('kind'))
        self.field('section_path', self.section_path, units[0]['_order'])
        self.field('references', self.references, units, got, block)
        return units[0]

    def references(self, value, alt, units, block_text, block=()):
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
            if not self.printed(block_text, ref['printed_text'], [ref.get('anchor')]): failure = failure or (('unresolved', 'adjacency', ref['printed_text']) if self.printed(spaced(block, ref['printed_text']), ref['printed_text'], [ref.get('anchor')]) else ('fail', 'phrase', ref['printed_text']))  # the phrase as whole words (Codex R15-1 class)
            elif ref.get('href') and not any(l.get('href') == ref['href'] for l in links): failure = failure or ('fail', 'href', ref['href'])
        if linked: self.row('reference_linked', 'pass' if all(linked) else 'fail')
        return failure or ('pass', None, None)


# --------------------------------------------------------------------------------------------------------- gates
def picture_at(rf, byte):
    """Does the source hold a picture element and no text at these bytes? Then a unit's text there is a reading of the picture — approximate evidence
    the bytes cannot certify — whatever the route calls the unit: the source decides, never the output kind (Codex R14-3). A picture element is one
    the scanner found in a subtree the contract's hiding rules leave shown, never a tag inside a comment, a script, an attribute, literal text or a
    hidden subtree (R15-4, R17-C4). Whether it paints — its size, clipping, transforms — is beyond the scanner, so the reading is not measured."""
    return not squash(rf.vis.at_any(byte)) and any(a['byte_start'] <= s < a['byte_end_exclusive'] for a in byte for s, _ in rf.vis.pictures)


def gates_for_file(rf, status, excluded=()):
    """Per-file P14 facts: dishonest or missing anchors, duplicate ids, order breaks, uncovered visible text. A check that cannot be
    made (no text layer, no page sizes, stylesheet-dependent visibility, a PARTIAL route) is reported as None = not measured. `excluded`: the
    anchors of targets the package declares out of scoring (page numbers): their characters are subtracted from required-content coverage only,
    and counted apart (Codex R14-4)."""
    g = {'dishonest': 0, 'unanchored': 0, 'unplaced': 0, 'bounds_inconsistent': 0, 'boundary': 0, 'inserted_chars': 0, 'dup_ids': 0, 'order_breaks': 0, 'uncovered': None, 'anchors_measured': True,
         'hidden_chars': rf.vis.hidden_chars if rf.vis else None}
    ids = [u.get('id') for u in rf.units]; g['dup_ids'] = len(ids) - len(set(ids))
    def held(u):  # a unit declared `within` another (a field inside prose) is read there, once: it follows its holder and its span lies inside the holder's (Codex R13 C4)
        h = rf.by_id.get(u.get('within')); a, b = (spans(u.get('anchor')) or [{}])[0], (spans(h.get('anchor')) or [{}])[0] if h else {}
        return bool(h) and h['_order'] < u['_order'] and 'byte_start' in a and 'byte_start' in b and b['byte_start'] <= a['byte_start'] and a['byte_end_exclusive'] <= b['byte_end_exclusive']
    g['dishonest'] += sum(1 for u in rf.units if u.get('within') and not held(u))
    keys = [order_key(u['anchor']) for u in rf.units if spans(u.get('anchor')) and u.get('layer') != 'furniture']
    g['order_breaks'] = sum(1 for a, b in zip(keys, keys[1:]) if b < a)
    ranges = []
    for u in rf.units:
        items = (u.get('cells') or []) if u.get('kind') == 'table' else [u]  # every item, placed or not: the gate counts what a lookup never consults
        if u.get('kind') == 'table' and u.get('_bad_anchor'): g['dishonest'] += 1  # the table's own envelope, a false claim of position
        for x in items:
            if x.get('_bad_anchor'):  # a position that cannot be true (RouteFile), for every kind of unit and of anchor (Codex R14-3, R15-3): text there is a false claim; an item with no text (a picture the linker gave an empty gap) claims nothing — counted apart, covering nothing; impossible boxes stay visible as such
                g['dishonest' if squash(x.get('text', '')) else 'unplaced'] += 1; g['bounds_inconsistent'] += any(isinstance(a, dict) and 'region' in a for a in spans(x.get('_claimed'))); continue
            parts = spans(x.get('anchor'))
            if x.get('link_flag') == 'gap' and not squash(x.get('text', '')): continue  # a picture placed between its neighbours: the derived location certifies nothing, covers nothing; text under that flag is certified like any other
            if not parts:
                if squash(x.get('text', '')): g['unanchored'] += 1  # text claimed without a source position, whatever the route calls the unit
                continue
            for a in parts:
                if 'region' in a and 'byte_start' not in a: g['anchors_measured'] = False; break  # no independent page geometry: a region is never certified (its consistency with the route's own page sizes is a condition of being a position at all, RouteFile)
            else:
                byte = [a for a in parts if 'byte_start' in a]
                if byte and rf.vis is None: g['anchors_measured'] = False  # a source with no text layer: nothing reads these bytes, so nothing certifies them
                if byte and rf.vis is not None:
                    ranges.extend((a['byte_start'], a['byte_end_exclusive']) for a in byte)
                    if not rf.vis.certain: continue  # an uncertain reading proves no mismatch: nothing that depends on it is counted (the file is reported not measured below) (Codex R17-C4)
                    if picture_at(rf, byte):  # a picture element and no text here: the unit's text is a reading of it, counted under pictures — not measured, never a mismatch, never a certificate (R16-3, R17-C4)
                        if squash(x.get('text', '')): g['anchors_measured'] = False
                        continue
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
                    seen = squash(rf.vis.at_any(byte))
                    for mm in (squash(m) for m in x.get('markers') or []):  # each reported mark sits right before or right after the text (a mark the route reports apart may touch a number, as a superscript does: the gate certifies characters; whether it is a mark is the value's and the footnote check's question)
                        if mm and seen.startswith(mm): seen = seen[len(mm):]
                        elif mm and seen.endswith(mm): seen = seen[:-len(mm)]
                    if seen != squash(x.get('text', '')): g['dishonest'] += 1
                    elif not boundary_equal(marks_off(rf.vis.at_any(byte), x.get('markers') or []), x.get('text', '')) and not redline_apart(x, rf.vis, byte): g['boundary'] += 1  # same characters, a word or number boundary lost or added — unless the source's own strike-through delimits it and the item says where
    if rf.vis is not None and not rf.vis.certain: g['anchors_measured'] = False  # visibility depends on stylesheet rules this scanner does not read
    if rf.vis is not None and rf.vis.certain and status == 'OK':
        excl = [(a['byte_start'], a['byte_end_exclusive']) for e in excluded for a in spans(e) if 'byte_start' in a]  # the declared exclusions' own bytes, nothing wider
        raw_loss, g['uncovered'] = rf.vis.uncovered(ranges), rf.vis.uncovered(ranges + excl)  # raw coverage kept; required-content coverage subtracts the declared bytes only
        g['excluded_chars'] = sum(len(squash(x['text'])) for x in raw_loss) - sum(len(squash(x['text'])) for x in g['uncovered'])
    g['pictures'] = len(rf.vis.pictures) if rf.vis is not None and rf.vis.certain else None  # the picture elements in shown subtrees (the scanner's inventory, certain visibility only): their content is never measured by the text map
    return g


# ----------------------------------------------------------------------------------------------------------- run
def verdict_of(rows):
    """A target's verdict from its check rows: a failed check fails it, else an open one leaves it unresolved, else an approximate one makes it
    approximate. The recognition rows (STRUCTURE) are counts — reported, never deciding, failed or left open."""
    graded = {r['verdict'] for r in rows if r['check'] not in STRUCTURE}
    return next((name for v, name in (('fail', 'FAIL'), ('unresolved', 'UNRESOLVED'), ('approximate', 'APPROXIMATE')) if v in graded), 'PASS')


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
        files[fid] = {'status': status, 'route_status': (data or {}).get('status'), 'error': (data or {}).get('error'), 'seconds': (data or {}).get('seconds'), 'not_read': (data or {}).get('not_read')}
        routes[fid] = (data or {}).get('route')
        rf = RouteFile(data, raw, mine[0]['format'].split('/')[-1]) if status == 'OK' else None
        if rf: per_file[fid] = gates_for_file(rf, data.get('status'), [t['anchor'] for t in mine if t.get('excluded_target')])
        structure_units = []
        for t in mine:
            if t.get('excluded_target'):  # declared out of scoring by the package (page numbers): reported apart, never a pass
                verdicts[t['key_id']] = 'EXCLUDED'; rows.append({'key_id': t['key_id'], 'file_id': fid, 'split': t['split'], 'format': t['format'], 'check': 'target', 'verdict': 'excluded', 'reason': t['excluded_target'], 'detail': None}); continue
            if status != 'OK': verdicts[t['key_id']] = status; continue
            g = Grader(t, rf)
            unit = g.grade_cell() if t['type'] == 'cell' else g.grade_structure()
            if unit is None: verdicts[t['key_id']] = 'UNRESOLVED'; rows += g.rows; continue
            if t['type'] == 'structure': structure_units.append((t['key_id'], t['anchor'], unit['_order'], inner_position(unit, t['anchor'], rf)))
            marker_glued += sum(1 for r in g.rows if r['reason'] == 'marker_glued')
            verdicts[t['key_id']] = verdict_of(g.rows)
            rows += g.rows
        for kid, a, o, inner in structure_units:  # block order within the file: the route's own order between units, its mapping or cell order inside a shared unit, never the key's (Codex R15-2); the source's order comes from `source_before`, side by side on one row included
            bad = pending = False
            for k2, a2, o2, inner2 in structure_units:
                if k2 == kid or not (source_before(a, a2) or source_before(a2, a)): continue
                if o != o2: before = o < o2
                elif inner is not None and inner2 is not None and inner[1] <= inner2[0]: before = True
                elif inner is not None and inner2 is not None and inner2[1] <= inner[0]: before = False
                else: pending = True; continue  # one unit, no readable order between the two blocks: unproved
                bad |= source_before(a, a2) != before
            rows.append({'key_id': kid, 'file_id': fid, 'split': next(t['split'] for t in mine if t['key_id'] == kid),
                         'format': next(t['format'] for t in mine if t['key_id'] == kid), 'check': 'order', 'verdict': 'fail' if bad else 'unresolved' if pending else 'pass',
                         'reason': 'order' if bad else 'internal_order' if pending else None, 'detail': None})
            if bad: verdicts[kid] = 'FAIL'  # a strict failure outranks an approximate or an unresolved reading (Codex R14-3)
            elif pending and verdicts[kid] in ('PASS', 'APPROXIMATE'): verdicts[kid] = 'UNRESOLVED'
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
                           'unplaced': {f: g['unplaced'] for f, g in per_file.items() if g['unplaced']},  # textless items at a position that cannot be true (pictures in an empty linker gap): no claim, no coverage, reported
                           'bounds_inconsistent': {f: g['bounds_inconsistent'] for f, g in per_file.items() if g['bounds_inconsistent']},  # of the impossible positions, the page boxes (beyond the page, no area, malformed): visible as such
                           'boundary': {f: g['boundary'] for f, g in per_file.items() if g['boundary']},
                           'inserted_chars': {f: g['inserted_chars'] for f, g in per_file.items() if g['inserted_chars']}, 'not_measured': anc_unmeasured},
        'ids_and_run_facts': {'pass': not ungraded and all(g['dup_ids'] == 0 for g in per_file.values()) and all(isinstance(routes[f], dict) and all(k in routes[f] for k in ('tool', 'version', 'settings')) for f in per_file), 'not_measured': ungraded},
        'reading_order': {'pass': not ungraded and sum(g['order_breaks'] for g in per_file.values()) == 0, 'breaks': {f: g['order_breaks'] for f, g in per_file.items() if g['order_breaks']}, 'not_measured': ungraded},
        'markers_apart': {'pass': not ungraded and marker_glued == 0, 'glued': marker_glued, 'not_measured': ungraded},
        'nothing_lost': {'pass': not uncovered and not cov_unmeasured, 'measured_pass': not uncovered, 'uncovered': uncovered, 'not_measured': cov_unmeasured,
                         'excluded_chars': {f: g['excluded_chars'] for f, g in per_file.items() if g.get('excluded_chars')},  # characters of declared exclusions (page numbers) no unit covers: counted apart, never required loss
                         'measures': 'visible source text; declared exclusions counted apart; picture content is not measured', 'pictures_not_measured': {f: g['pictures'] for f, g in per_file.items() if g.get('pictures')}},
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


VERDICTS = ('PASS', 'FAIL', 'UNRESOLVED', 'NOT_CONVERTED', 'EXCLUDED', 'APPROXIMATE')  # a target's verdicts; the last two only where the package declares them (R4), counted apart, never passes


def summarize(targets, rows, verdicts, files, route, shown_ids=None):
    by, sup = {}, {'targets': 0, **{v: 0 for v in VERDICTS}}
    for t in targets:
        v = verdicts[t['key_id']]
        if t['split'] == 'supplement':
            sup['targets'] += 1; sup[v] = sup.get(v, 0) + 1; continue
        cell = by.setdefault(t['split'], {}).setdefault(t['format'], {'targets': 0, **{v: 0 for v in VERDICTS}})
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
    out += ['| split | format | targets | ' + ' | '.join(VERDICTS) + ' |', '|---|---|---:|' + '---:|' * len(VERDICTS)]
    line = lambda split, fmt, c: f"| {split} | {fmt} | {c['targets']} | " + ' | '.join(str(c.get(v, 0)) for v in VERDICTS) + ' |'
    for split, fmts in s['by_split_format'].items():
        for fmt, c in fmts.items(): out.append(line(split, fmt, c))
    out.append(line('supplement', 'cell', s['supplement']))
    out += ['', f"Excluded fields (not scored, counted): {s['excluded_fields']}", '', '| check | pass | fail | unresolved | approximate | na | excluded | not_t1 |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for f, c in s['by_field'].items():
        out.append(f"| {f} | {c.get('pass', 0)} | {c.get('fail', 0)} | {c.get('unresolved', 0)} | {c.get('approximate', 0)} | {c.get('na', 0)} | {c.get('excluded', 0)} | {c.get('not_t1', 0)} |")
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
