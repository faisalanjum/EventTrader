"""Reconstruction of one saved route E from its saved pieces alone: an ordered readback R and its checks (promoted unchanged from the fable-readback/11 candidate).
Every saved record is carried verbatim exactly once inside the composed body; relations exist only as the body's structure (order, list groups,
holder placement, caption placement, owner attachments, the XML tree). `preserved` is the saved content/structure boundary: the body's inverse must equal E
under type-preserving JSON equality, every body edge must be the one its own records state, and every emitted key is consumed, an annotation, or
an explicit unrepresented family. `annotations` is the uncertainty boundary (a dropped, added or changed unknown fails there); `verify` needs custody, preserved and annotations together. Inputs: the saved route and its bound prepared/ archive
(archive.load_blob); never the original, a reparse, or the raw parser reading. Preservation does not certify fidelity to the original document."""
from collections import Counter
import copy
import graphlib
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA = 'fable-readback/11'  # v11: every unit node carries 'ordinal', its index in E['units'] (outside its record); the inverse orders by it only after an exact 0..n-1 permutation check; ordinals strictly increase within each _units_in_order container; caption side is decided by caption/holder ordinals; the v10 'order' unknown is gone because saved order is now represented. v10: saved source_symbols records attach to their native owners like links (identity only, no range); v9: a run record attaches only where its saved owner names one unit/cell AND a qualified final-text range (audit only)
CUSTODY_KEYS = {'route_sha256', 'complete_sha256', 'prepared', 'raw_reading_sha256', 'raw_reading_receipt_sha256'}
COMPLETE_KEYS = {'file_id', 'source_sha256', 'route_sha256', 'native_status', 'prepared_input_sha256', 'reader_called'}  # every producer (recipe v1, v3, v4)
RAW_KEYS = {'raw_reading_sha256', 'raw_reading_receipt_sha256'}  # recipe v4 adds both (None when it kept no raw reading)
HEXPIN = lambda x: isinstance(x, str) and re.fullmatch('[0-9a-f]{64}', x) is not None
IDENTITY = ('schema', 'file_id', 'sha256', 'route', 'status', 'error', 'seconds')
NOT_REPRESENTED_XML = ('comments', 'processing_instructions', 'xml_declaration', 'doctype', 'source_spelling')  # immutable; each readback emits its own list
REQUIRED_TOP = {'readback_schema', 'identity', 'kind', 'unknowns', 'not_composed'}
UNIT_KEYS, CELL_KEYS = {'record', 'ordinal', 'cells', 'captions', 'attached', 'asset', 'holder', 'position'}, {'record', 'children', 'attached', 'aggregate'}
LIST_KEYS, ITEM_KEYS = {'kind', 'list', 'ordered', 'items'}, {'item', 'members'}
canon = lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False)  # JSON keeps True != 1, null != absent and every list order
ATTACHED = ('source_links', 'source_style', 'source_inline', 'source_symbols')  # families whose saved records name body owners: one owner rule (_owner_site), one stated-vs-body check
RUNS = ('source_style', 'source_inline')  # run-record families: their owners also need a qualified saved final-text range (_placed)
RECORDS = RUNS + ('source_symbols',)  # {read, records} families: body only when read is true and records is a list; read:false readings stay carried; failure lists reported (screen_grid.py :858-866)
_records = lambda k, v: v if k == 'source_links' else v['records']


def _xml_identity(elements):
    """One rooted, acyclic, connected element graph with unique start bytes, resolving children, each named once by its own parent."""
    if not isinstance(elements, list) or not elements: return 'no saved xml_elements'
    if not all(isinstance(e, dict) and isinstance(e.get('anchor'), dict) for e in elements): return 'an element or its anchor is missing'
    starts = [e['anchor'].get('byte_start') for e in elements]
    if any(type(s) is not int for s in starts) or len(set(starts)) != len(starts): return 'element start bytes missing or not unique'
    by = dict(zip(starts, elements))
    refs = [(e['anchor']['byte_start'], x.get('child')) for e in elements for x in e.get('content', []) if isinstance(x, dict)]
    if any(c not in by for _, c in refs): return 'a child reference names no element'
    named = [c for _, c in refs]
    if len(set(named)) != len(named) or any(by[c].get('parent') != p for p, c in refs): return 'a child is named twice or by another parent'
    roots = [s for s in starts if by[s].get('parent') is None]
    if len(roots) != 1 or roots[0] in named or len(named) != len(elements) - 1: return 'not exactly one root over every element'
    try: graphlib.TopologicalSorter({c: {p} for p, c in refs}).prepare()  # native cycle detection only; its order is never used
    except graphlib.CycleError: return 'the element graph has a cycle'
    seen, todo = set(), [roots[0]]
    while todo:
        s = todo.pop(); seen.add(s); todo += [x['child'] for x in by[s].get('content', []) if isinstance(x, dict)]
    return None if len(seen) == len(elements) else 'an element is not reachable from the root'


def _xml_tree(elements):  # the saved graph composed as one tree; parent and child references become structure
    by = {e['anchor']['byte_start']: e for e in elements}
    def node(e):
        n = {k: copy.deepcopy(v) for k, v in e.items() if k not in ('parent', 'content')}
        if 'content' in e: n['content'] = [node(by[x['child']]) if isinstance(x, dict) else x for x in e['content']]
        return n
    return [node(next(e for e in elements if e.get('parent') is None))]


def _xml_records(tree):  # inverse: records in pre-order (start-tag order), parent and child references rebuilt from structure
    out = []
    def walk(n, parent):
        rec = {k: v for k, v in n.items() if k != 'content'}
        if 'parent' in rec: rec['!mirror_conflict'] = 'a node states its own parent'  # never let structure silently override a stated relation
        rec['parent'] = parent; out.append(rec)
        if 'content' in n:
            rec['content'] = []
            for x in n['content']:
                if isinstance(x, dict): rec['content'].append({'child': x['anchor']['byte_start']}); walk(x, n['anchor']['byte_start'])
                else: rec['content'].append(x)
    for n in tree: walk(n, None)
    return out


def _asset(u, prepared):
    inp = u.get('input')
    if inp is None: return {'status': 'no_input_record'}
    if not isinstance(inp, dict): return {'status': 'invalid_input_record'}
    if 'error' in inp: return {'status': 'error'}
    if prepared is None: return {'status': 'not_checked'}
    from driver.prepare.get import acquire, archive
    try: archive.load_blob(prepared, inp.get('input_sha256'))
    except FileNotFoundError: return {'status': 'missing'}
    except acquire.AcquisitionError: return {'status': 'hash_mismatch'}
    except ValueError: return {'status': 'invalid_pin'}
    except (OSError, EOFError): return {'status': 'unreadable'}
    return {'status': 'ok'}


def _same_place(cell, ref):  # every coordinate and source span the reference saves must equal the cell's own
    src = cell.get('source') or {}
    return all(cell.get(k) == ref[k] for k in ('r', 'c', 'rs', 'cs') if k in ref) and all(src.get(k) == ref[k] for k in ('byte_start', 'byte_end_exclusive') if k in ref)


def _spans(a):
    return [x for x in (a if isinstance(a, list) else [a]) if isinstance(x, dict) and 'byte_start' in x]


def _first_byte(cell):
    return ([a.get('byte_start') for a in _spans(cell.get('anchor'))] or [None])[0]


def _resolve(units):
    """The relations the saved records state: placed[i] = ('cell', p, k) or ('caption', j); ambiguous or broken ones become unknowns."""
    count = Counter(u.get('id') for u in units)
    by_id = {u.get('id'): i for i, u in enumerate(units) if count[u.get('id')] == 1}
    placed, unknowns = {}, [] if len(by_id) == len(units) else [{'family': 'units', 'why': 'unit ids missing or repeated'}]
    for i, u in enumerate(units):
        ref = u.get('cell')
        if not isinstance(ref, dict) or u.get('kind') not in ('table', 'image'): continue
        p = by_id.get(ref.get('table'))
        cells = (units[p].get('cells') or []) if p is not None and units[p].get('kind') == 'table' else []
        hits = [k for k, c in enumerate(cells) if isinstance(c, dict) and _same_place(c, ref) and (u.get('kind') != 'table' or u.get('id') in (c.get('tables') or []))]
        if len(hits) == 1: placed[i] = ('cell', p, hits[0])
        else: unknowns.append({'family': 'nesting', 'unit': u.get('id'), 'why': 'holder reference unresolved or inconsistent'})
    for i in list(placed):  # a holder chain must reach an unplaced unit; a loop stays unresolved
        seen, j = set(), i
        while j in placed and j not in seen: seen.add(j); j = placed[j][1]
        if j in seen:
            for x in seen: placed.pop(x, None)
            unknowns.append({'family': 'nesting', 'unit': units[i].get('id'), 'why': 'holder references form a loop'})
    for p, u in enumerate(units):
        for k, c in enumerate((u.get('cells') or []) if u.get('kind') == 'table' else []):
            if not isinstance(c, dict): continue
            for t in c.get('tables') or []:
                if placed.get(by_id.get(t)) != ('cell', p, k): unknowns.append({'family': 'nesting', 'unit': u.get('id'), 'why': 'a holder cell names a child that does not name it'})
            if c.get('link_error'): unknowns.append({'family': 'placement', 'unit': u.get('id'), 'why': 'cell link_error'})
        if u.get('link_error'): unknowns.append({'family': 'placement', 'unit': u.get('id'), 'why': 'link_error'})
    tables = {}
    for j, t in enumerate(units):
        if t.get('kind') == 'table' and t.get('source_table') is not None: tables.setdefault(canon(t['source_table']), []).append(j)
    for i, u in enumerate(units):  # captions: a present, unambiguous saved table identity; two nulls never match
        if u.get('kind') != 'caption': continue
        st = u.get('source_table'); hits = tables.get(canon(st), []) if st is not None else []
        if len(hits) == 1: placed[i] = ('caption', hits[0])
        else: unknowns.append({'family': 'caption', 'unit': u.get('id'), 'why': 'no unique saved table identity' if st is not None else 'caption identity is null'})
    return by_id, placed, unknowns


def _owner_site(o, units, by_id):  # the one unit, or one cell by its first anchor byte, that a saved owner names; None if not exactly one
    i = by_id.get(o.get('unit')) if isinstance(o, dict) else None
    if i is None: return None
    if 'cell' not in o: return ('unit', i)
    hits = [k for k, c in enumerate(units[i].get('cells') or []) if isinstance(c, dict) and o['cell'] is not None and _first_byte(c) == o['cell']]
    return ('cell', i, hits[0]) if len(hits) == 1 else None


def _ranges_ok(ranges, text):  # a saved run owner's text_at as the producer writes it (screen_grid._owners :388-405): ascending, non-overlapping [start, end) int pairs in the owner's saved text
    return (isinstance(ranges, list) and bool(ranges) and isinstance(text, str)
            and all(isinstance(p, list) and len(p) == 2 and all(type(x) is int for x in p) and 0 <= p[0] < p[1] <= len(text) for p in ranges)
            and all(p[1] <= q[0] for p, q in zip(ranges, ranges[1:])))


def _placed(f, o, units, by_id):  # (site, None) or (None, why): the one placement rule of builder and checker; run records also need a qualified saved range
    site = _owner_site(o, units, by_id)
    if site is None: return None, 'an owner is absent or unresolved'
    if f in RUNS and not _ranges_ok(o.get('text_at'), (units[site[1]] if site[0] == 'unit' else units[site[1]]['cells'][site[2]]).get('text')):
        return None, 'an owner range is not a code-point range of its saved final text'
    return site, None


def _group(seq):
    """Saved list membership (`lists`, outer first) groups consecutive members of any kind, in saved order."""
    out, stack = [], []
    for n in seq:
        chain = n['record'].get('lists') or []
        d = 0
        while d < len(stack) and d < len(chain) and stack[d]['key'] == chain[d].get('list') and stack[d]['ordered'] == chain[d].get('ordered'):
            if stack[d]['no'] != chain[d].get('item'):
                del stack[d + 1:]
                it = {'item': chain[d].get('item'), 'members': []}; stack[d]['node']['items'].append(it); stack[d].update(item=it, no=chain[d].get('item'))
                d += 1; break
            d += 1
        del stack[d:]
        for lv in chain[d:]:
            it = {'item': lv.get('item'), 'members': []}; ln = {'kind': 'list', 'list': lv.get('list'), 'ordered': lv.get('ordered'), 'items': [it]}
            (stack[-1]['item']['members'] if stack else out).append(ln); stack.append({'key': lv.get('list'), 'ordered': lv.get('ordered'), 'node': ln, 'item': it, 'no': lv.get('item')})
        (stack[-1]['item']['members'] if stack else out).append(n)
    return out


def _units_in_order(seq, container=None, path=()):
    """The body's own order: list members by item; before-captions, the unit, its cells' children, after-captions. Yields (node, container, chain)."""
    for n in seq:
        if 'record' not in n:
            for it in n.get('items', []):
                yield from _units_in_order(it.get('members', []), container, path + ({'list': n.get('list'), 'ordered': n.get('ordered'), 'item': it.get('item')},))
            continue
        caps = n.get('captions', [])
        yield from ((x, ('caption', id(n)), ()) for x in caps if x.get('position') == 'before')
        yield n, container, path
        for k, c in enumerate(n.get('cells', [])):
            yield from _units_in_order(c.get('children', []), ('cell', id(n), k))
        yield from ((x, ('caption', id(n)), ()) for x in caps if x.get('position') != 'before')


def _html(route, prepared, R, families):
    units = route.get('units') or []
    nodes = []
    for i, u in enumerate(units):
        n = {'record': {k: v for k, v in u.items() if k != 'cells'}, 'ordinal': i}  # saved emission order, outside the record
        if 'cells' in u: n['cells'] = [{'record': c} for c in u['cells'] or []]
        if u.get('kind') == 'image': n['asset'] = _asset(u, prepared)
        nodes.append(n)
    by_id, placed, unknowns = _resolve(units); R['unknowns'] += unknowns
    for i, u in enumerate(units):
        if isinstance(u.get('cell'), dict) and u.get('kind') in ('table', 'image') and i not in placed: nodes[i]['holder'] = 'unresolved'
    for i in sorted(placed):  # saved order within every holder
        w = placed[i]
        if w[0] == 'caption': nodes[i]['position'] = 'before' if i < w[1] else 'after'; nodes[w[1]].setdefault('captions', []).append(nodes[i])
        else: nodes[w[1]]['cells'][w[2]].setdefault('children', []).append(nodes[i])
    for n in nodes:
        for c in n.get('cells', []):
            if c.get('children'):
                c['children'] = _group(c['children'])
                if any(x['record'].get('kind') == 'table' for x, _, _ in _units_in_order(c['children'])): c['aggregate'] = 'unresolved'
    R['sequence'] = _group([n for i, n in enumerate(nodes) if i not in placed])
    for f in families:  # each saved owner, resolved once by _owner_site, holds its record's index; the family itself is kept verbatim
        R[f] = route[f]
        for key in ('unresolved', 'unread') if f in RECORDS else ():  # the producer's two failure lists (screen_grid.py :861, :865), kept raw in the family
            if route[f].get(key): R['unknowns'].append({'family': f, 'why': f'saved {key} entries'})
        for j, rec in enumerate(_records(f, route[f])):
            owners = rec.get('owners') if isinstance(rec, dict) else None
            for o in owners or []:
                site, why = _placed(f, o, units, by_id)
                if site is None: R['unknowns'].append({'family': f, 'record': j, 'why': why}); continue
                target = nodes[site[1]] if site[0] == 'unit' else nodes[site[1]]['cells'][site[2]]
                target.setdefault('attached', {}).setdefault(f, []).append(j)
            if not owners: R['unknowns'].append({'family': f, 'record': j, 'why': 'no saved owner'})


def _roles(E):
    """The one ownership rule, decided from the saved route E alone: every key of E is 'identity', 'body' (of E's own format) or 'carry'."""
    fmt = 'xml' if 'xml_elements' in E or (E.get('route') or {}).get('name') == 'xml-fields' else 'html'
    units = isinstance(E.get('units'), list) and all(isinstance(u, dict) for u in E['units'])
    def body(k, v):
        if k == 'units': return units and fmt == 'html'  # XML field units: verbatim copies are carry-through, never a body slot
        if k == 'source_links': return fmt == 'html' and units and isinstance(v, list)
        if k in RECORDS: return fmt == 'html' and units and isinstance(v, dict) and v.get('read') is True and isinstance(v.get('records'), list)
        return fmt == 'xml' and k == 'xml_elements' and _xml_identity(v) is None
    return fmt, {k: 'identity' if k in IDENTITY else 'body' if body(k, v) else 'carry' for k, v in E.items()}


def _shape(E):
    """The exact keys R must have at every owning boundary, implied by _roles(E); R's own content never decides them."""
    fmt, roles = _roles(E); body = {k for k, r in roles.items() if r == 'body'}
    top = REQUIRED_TOP | ({'sequence'} if fmt == 'html' and 'units' in body else set()) | {k for k in ATTACHED if k in body} | ({'xml'} if fmt == 'xml' else set())
    return {'kind': fmt, 'top': top, 'identity': {k for k, r in roles.items() if r == 'identity'}, 'carry': {k for k, r in roles.items() if r == 'carry'},
            'xml': {'elements', 'not_represented'} if fmt == 'xml' else None, 'elements': 'xml_elements' in body}


def readback(route, prepared=None):
    route = copy.deepcopy(route)  # R never shares objects with the caller's E
    fmt, roles = _roles(route)
    R = {'readback_schema': SCHEMA, 'kind': fmt, 'identity': {k: v for k, v in route.items() if roles[k] == 'identity'}, 'unknowns': [], 'not_composed': {}}
    if route.get('status') != 'OK': R['unknowns'].append({'family': 'status', 'why': f"route status {route.get('status')!r}"})
    if fmt == 'xml':
        R['xml'] = {'elements': _xml_tree(route['xml_elements']) if roles.get('xml_elements') == 'body' else None, 'not_represented': list(NOT_REPRESENTED_XML)}
        why = _xml_identity(route.get('xml_elements'))
        if why: R['unknowns'].append({'family': 'xml_elements', 'why': why})
    elif roles.get('units') == 'body':
        _html(route, prepared, R, [k for k in ATTACHED if roles.get(k) == 'body'])
    for k, v in route.items():  # every carry family: verbatim, explicit unrepresented scope, never proof of composition
        if roles[k] != 'carry': continue
        R['not_composed'][k] = v
        if not (k == 'uncovered' and v == []):
            R['unknowns'].append({'family': k, 'why': 'saved as not read' if isinstance(v, dict) and v.get('read') is False else 'not composed in this readback'})
    return json.loads(json.dumps(R))  # native JSON copy: exclusive ownership of every emitted object


def _saved_order(nodes):
    """The body's unit nodes in saved order: only when their ordinals are exactly the ints 0..n-1, each once (bool is not an int here)."""
    ords = [n.get('ordinal') for n in nodes]
    if not all(type(o) is int for o in ords) or sorted(ords) != list(range(len(nodes))): raise ValueError('unit ordinals are not exactly the integers 0..n-1, each once')
    return [nodes[k] for k in sorted(range(len(nodes)), key=ords.__getitem__)]


def _rebuild(n):
    rec = dict(n['record'])
    if 'cells' in rec: rec['!mirror_conflict'] = 'a record states its own cells'  # never let structure silently override a stated value
    return {**rec, **({'cells': [c['record'] for c in n['cells']]} if 'cells' in n else {})}


def inverse(R):
    """The saved route that R's body represents, recovered from structure alone."""
    body = {}
    if R['kind'] == 'xml':
        if R['xml'].get('elements') is not None: body['xml_elements'] = _xml_records(R['xml']['elements'])
    else:
        if 'sequence' in R: body['units'] = [_rebuild(n) for n in _saved_order([n for n, _, _ in _units_in_order(R['sequence'])])]
        body.update({k: R[k] for k in ATTACHED if k in R})
    E = {}
    for part in (R['identity'], R['not_composed'], body):  # disjoint by contract: a family with two owners is an error, never an overwrite
        if set(E) & set(part): raise ValueError(f'two owners for {sorted(set(E) & set(part))}')
        E.update(part)
    return E


def preserved(route, R):
    """The saved content/structure boundary (uncertainty is checked by annotations). [] only when the inverse equals E exactly, every body edge is the one its records state, and no key is unaccounted."""
    try:
        S, problems = _shape(route), []
        if R.get('readback_schema') != SCHEMA or R.get('kind') != S['kind']: problems.append('readback_schema or kind is not the required value')
        if set(R) - {'custody'} != S['top']: problems.append(f'top-level keys differ from the owners E implies: {sorted(set(R) ^ S["top"] - {"custody"})}')
        if 'custody' in R:
            c, hexpin = R['custody'], HEXPIN
            if not (isinstance(c, dict) and set(c) == CUSTODY_KEYS and type(c['prepared']) is bool and hexpin(c['route_sha256']) and hexpin(c['complete_sha256'])
                    and all(c[k] is None or hexpin(c[k]) for k in ('raw_reading_sha256', 'raw_reading_receipt_sha256'))):
                problems.append('custody is not the exact custody record (keys and JSON types)')
        for part in ('identity', 'carry'):
            got_keys = R.get('identity' if part == 'identity' else 'not_composed')
            if not isinstance(got_keys, dict) or set(got_keys) != S[part]: problems.append(f'{part} keys differ from the owners E implies')
        if S['xml'] is not None and (not isinstance(R.get('xml'), dict) or set(R['xml']) != S['xml'] or (R['xml'].get('elements') is not None) != S['elements']):
            problems.append('xml body keys or composed tree presence differ from what E implies')
        if problems: return problems
        got = inverse(R)
        if canon(got) != canon(route):
            keys = sorted(set(got) | set(route))
            bad = [k for k in keys if canon(got.get(k, '<absent>')) != canon(route.get(k, '<absent>'))]
            first = next((i for i, (a, b) in enumerate(zip(got.get('units') or [], route.get('units') or [])) if canon(a) != canon(b)), None)
            problems.append(f'inverse differs from E in {bad}' + (f' (first differing unit {first})' if first is not None else ''))
        if R['kind'] == 'xml': return problems
        flat = list(_units_in_order(R.get('sequence', [])))
        recs = [_rebuild(n) for n, _, _ in flat]; at = {id(n): i for i, (n, _, _) in enumerate(flat)}
        by_id, placed, _ = _resolve(recs)
        last = {}  # container -> previous ordinal: saved order must strictly increase inside every container (top level and list members, cell children, captions)
        for i, (n, container, chain) in enumerate(flat):  # every body edge is the one its own records state
            if container in last and not last[container] < n['ordinal']: problems.append(f'unit {i}: original ordinal does not increase within its container')
            last[container] = n['ordinal']
            where = None if container is None else (container[0], at.get(container[1])) + tuple(container[2:])
            if placed.get(i) != where: problems.append(f'unit {i}: placed where its records do not place it')
            if container is None or container[0] == 'cell':
                if canon(list(chain)) != canon(recs[i].get('lists', [])): problems.append(f'unit {i}: list group differs from its saved lists')
            elif chain: problems.append(f'unit {i}: caption inside a list group')
            if (container is not None and container[0] == 'caption') != ('position' in n) or ('position' in n and n['position'] != ('before' if n['ordinal'] < flat[at[container[1]]][0]['ordinal'] else 'after')):
                problems.append(f'unit {i}: caption position differs from saved order')
            problems += [f'unit {i}: unaccounted key {k!r}' for k in n if k not in UNIT_KEYS]
            for k, c in enumerate(n.get('cells', [])): problems += [f'unit {i} cell {k}: unaccounted key {x!r}' for x in c if x not in CELL_KEYS]
            for a in [n.get('attached', {})] + [c.get('attached', {}) for c in n.get('cells', [])]: problems += [f'unit {i}: unaccounted attachment {x!r}' for x in a if x not in ATTACHED]
        problems += _lists_ok(R.get('sequence', []))
        for f in ATTACHED:  # one stated-vs-body check for every attached family, from the records R itself carries (their equality to E is checked above)
            recs_f = _records(f, R[f]) if f in R else []
            stated = Counter((j, _placed(f, o, recs, by_id)[0]) for j, rec in enumerate(recs_f) for o in (rec.get('owners') if isinstance(rec, dict) else None) or [])
            stated = Counter({k: v for k, v in stated.items() if k[1] is not None})
            idx = [j for n, _, _ in flat for a in [n.get('attached', {})] + [c.get('attached', {}) for c in n.get('cells', [])] for j in a.get(f, [])]
            if any(type(j) is not int or not 0 <= j < len(recs_f) for j in idx): problems.append('an attachment index is not a valid int')
            body = Counter((j, ('unit', i)) for i, (n, _, _) in enumerate(flat) for j in n.get('attached', {}).get(f, []))
            body += Counter((j, ('cell', i, k)) for i, (n, _, _) in enumerate(flat) for k, c in enumerate(n.get('cells', [])) for j in c.get('attached', {}).get(f, []))
            if stated != body: problems.append(('link' if f == 'source_links' else f) + ' owner attachments differ from the owners the saved records state')
        return problems
    except (KeyError, TypeError, AttributeError, IndexError, ValueError) as error:
        return [f'R is malformed: {type(error).__name__}: {error}']


def _lists_ok(seq):  # list and item nodes: only their own keys, never empty
    out = []
    for n in seq:
        if 'record' in n:
            for c in n.get('cells', []): out += _lists_ok(c.get('children', []))
            continue
        out += ([] if set(n) == LIST_KEYS and n['kind'] == 'list' else ['a list node lacks its exact keys or kind']) + (['list without items'] if not n.get('items') else [])
        for it in n.get('items', []):
            out += ([] if set(it) == ITEM_KEYS else ['a list item lacks its exact keys']) + (['empty list item'] if not it.get('members') else [])
            out += _lists_ok(it.get('members', []))
    return out


def annotations(route, R, prepared=None):
    """The uncertainty boundary: annotations and unknowns equal a recomputation from the same frozen inputs (a dropped unknown fails here). Not missing-content detection, not truth."""
    def marks(X):
        if X.get('kind') == 'xml': return {'unknowns': X['unknowns'], 'not_represented': X['xml'].get('not_represented')}
        units = [[{k: n[k] for k in ('asset', 'holder') if k in n}, [{k: c[k] for k in ('aggregate',) if k in c} for c in n.get('cells', [])]] for n, _, _ in _units_in_order(X.get('sequence', []))]
        return {'unknowns': X['unknowns'], 'units': units}
    try: return [] if canon(marks(R)) == canon(marks(readback(route, prepared))) else ['annotations or unknowns differ from a recomputation (reproducibility only)']
    except (KeyError, TypeError, AttributeError) as error: return [f'R is malformed: {type(error).__name__}: {error}']


def _custody(attempt_dir):
    """The one custody gate (main and verify): ROUTE.json bound by COMPLETE.json, known identity, reader proved unused. Returns (route, prepared, custody)."""
    a = Path(attempt_dir)
    try: body, cbody = (a / 'ROUTE.json').read_bytes(), (a / 'COMPLETE.json').read_bytes()
    except FileNotFoundError as error: raise ValueError(f'attempt file missing: {Path(error.filename).name}')
    complete, route = json.loads(cbody), json.loads(body)
    if not isinstance(complete, dict) or not isinstance(route, dict): raise ValueError('attempt files are not JSON objects')
    if set(complete) not in (COMPLETE_KEYS, COMPLETE_KEYS | RAW_KEYS): raise ValueError('completion keys are not a producer contract')
    if complete.get('route_sha256') != hashlib.sha256(body).hexdigest(): raise ValueError('ROUTE.json is not the route its completion names')
    if not all(isinstance(x, str) and x for x in (complete.get('file_id'), complete.get('source_sha256'))): raise ValueError('completion identity is unknown')
    if (complete.get('file_id'), complete.get('source_sha256')) != (route.get('file_id'), route.get('sha256')): raise ValueError('completion names another document')
    if complete.get('reader_called') is not False: raise ValueError('reader use is not proved absent')
    if canon(complete['native_status']) != canon(route.get('status')): raise ValueError('completion native_status is not the route status')  # any status, if consistent
    pins = complete['prepared_input_sha256']
    if not (isinstance(pins, list) and all(HEXPIN(x) for x in pins) and pins == sorted(set(pins))): raise ValueError('prepared input pins are not a sorted unique pin list')
    named = sorted({u['input']['input_sha256'] for u in route.get('units') or [] if isinstance(u, dict) and isinstance(u.get('input'), dict) and 'input_sha256' in u['input']})
    if named != pins: raise ValueError('prepared input pins differ from the inputs the route names')  # the producer stores exactly those inputs
    p = a / 'prepared'
    if p.exists() and not p.is_dir(): raise ValueError('prepared exists but is not a directory')
    if pins and not p.is_dir(): raise ValueError('the completion declares prepared inputs but there is no prepared archive')
    def restore(root, pin, what):  # existence and exact restore by the native owner, imported only when there is something to restore
        from driver.prepare.get import acquire, archive
        try: archive.load_blob(root, pin)
        except (acquire.AcquisitionError, ValueError, OSError, EOFError) as error: raise ValueError(f'{what} does not restore: {type(error).__name__}')
    for pin in pins: restore(p, pin, 'a declared prepared input')
    raw, receipt, rfile = complete.get('raw_reading_sha256'), complete.get('raw_reading_receipt_sha256'), a / 'RAW_READING.json'
    if (raw is None) != (receipt is None): raise ValueError('raw reading pins are not both present or both absent')
    if raw is None and rfile.exists(): raise ValueError('a raw reading receipt exists but the completion claims none')
    if raw is not None:  # identity only: the raw reading is restore-checked, never read into R
        if not (HEXPIN(raw) and HEXPIN(receipt) and rfile.is_file() and hashlib.sha256(rfile.read_bytes()).hexdigest() == receipt): raise ValueError('raw reading receipt missing or not its pin')
        r = json.loads(rfile.read_bytes())
        if not isinstance(r, dict) or r.get('raw_reading_sha256') != raw or r.get('source_sha256') != complete['source_sha256']: raise ValueError('raw reading receipt does not bind this completion')
        restore(a / 'raw_reading', raw, 'the raw reading')
    prepared = p if p.is_dir() else None
    return route, prepared, {'route_sha256': complete['route_sha256'], 'complete_sha256': hashlib.sha256(cbody).hexdigest(), 'prepared': prepared is not None,
                             'raw_reading_sha256': complete.get('raw_reading_sha256'), 'raw_reading_receipt_sha256': complete.get('raw_reading_receipt_sha256')}  # identity only


def main(argv):
    """main([attempt_dir, out_json]): one frozen attempt (ROUTE.json bound by COMPLETE.json, optional prepared/) to one new readback file."""
    route, prepared, custody = _custody(argv[0])
    R = readback(route, prepared); R['custody'] = custody
    with open(argv[1], 'x', encoding='utf-8') as f: json.dump(R, f, ensure_ascii=False, indent=1)


def verify(attempt_dir, r_json):
    """Preservation and annotation results for one written readback against its frozen ROUTE.json (and prepared/), kept separate."""
    R = json.loads(Path(r_json).read_bytes())
    try: route, prepared, custody = _custody(attempt_dir)
    except (ValueError, json.JSONDecodeError) as error:
        return {'custody': [f'custody not proved: {error}'], 'preserved': ['not checked: custody failed'], 'unrepresented': [], 'annotations': ['not checked: custody failed']}
    if not isinstance(R, dict) or canon(R.get('custody')) != canon(custody): return {'custody': ['R.custody differs from the custody this attempt proves'], 'preserved': preserved(route, R) if isinstance(R, dict) else ['R is not an object'], 'unrepresented': [], 'annotations': ['not checked: custody failed']}
    unrepresented = sorted(set(R.get('not_composed') or {}) | set((R.get('xml') or {}).get('not_represented') or []) | {u.get('family') for u in R.get('unknowns') or [] if isinstance(u, dict)})
    return {'custody': [], 'preserved': preserved(route, R), 'unrepresented': unrepresented, 'annotations': annotations(route, R, prepared)}


if __name__ == '__main__':  # from the repository root: python -m driver.prepare.reconstruct <attempt_dir> <out_json> | verify <attempt_dir> <R.json> (exit 0 only if custody, preserved and annotations are all empty)
    if sys.argv[1] == 'verify':
        result = verify(sys.argv[2], sys.argv[3]); print(json.dumps(result, indent=1)); sys.exit(1 if result['custody'] or result['preserved'] or result['annotations'] else 0)
    main(sys.argv[1:])
