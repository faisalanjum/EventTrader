"""Route adapter: Docling, HTML backend -> the common route format, anchored by the shared linker.
Shape rules only (Docling's JSON: labels, groups, cells, its own formatting flags), no document-specific logic. Runs under a Docling environment; the grader itself
stays standard-library.

    <docling python> -m benchmarks.prepare.grader.adapters.docling_html --key <key package> --split development --out <run dir> [--catalog CSV]

Writes <run dir>/raw/<file_id>.docling.json (Docling's own output, kept apart), <run dir>/route/<file_id>.json and
<run dir>/facts.json. Files of other formats in the split get a route file with status UNSUPPORTED (an explicit gap)."""
import argparse
import json
import re
import time
from pathlib import Path

from benchmarks.prepare.grader import anchor, grade

NAME = 'docling-html'
KIND = {'section_header': 'heading', 'title': 'heading', 'text': 'text', 'paragraph': 'text', 'list_item': 'list_item', 'caption': 'caption',
        'footnote': 'footnote', 'page_header': 'clutter', 'page_footer': 'clutter', 'picture': 'image'}
MARK = re.compile(r'^(\(\w{1,2}\)|\w|\*|†|‡)$')  # guide 3.6: the shapes a footnote mark can take


def to_units(doc, with_index=False):
    """Docling's body in reading order -> units. Rich table cells are read from their piece group; pieces Docling marks
    as superscript are kept apart as `markers`; struck pieces are reported; the pieces are not repeated as units."""
    lists = {k: doc.get(k) or [] for k in ('texts', 'groups', 'tables', 'pictures')}
    item = lambda ref: lists[ref.split('/')[1]][int(ref.split('/')[-1])]
    units = []

    def text_unit(t):
        u = {'id': t['self_ref'], 'kind': KIND.get(t.get('label'), 'other'), 'text': t.get('text') or ''}
        if t.get('level') is not None: u['level'] = t['level']
        if t.get('hyperlink'): u['links'] = [{'text': u['text'], 'href': str(t['hyperlink']), 'to': None}]
        if (t.get('formatting') or {}).get('strikethrough'): u['struck'] = [u['text']]  # Docling says: shown struck through
        units.append(u)

    def table_unit(t):
        cells = []
        for i, c in enumerate(t['data']['table_cells']):
            text, markers = c.get('text') or '', []
            if c.get('ref'):  # a rich cell: its leaf pieces, through nested inline/list groups; raised pieces (Docling's own formatting) are marks kept apart
                def leaves(ref):
                    it = item(ref)
                    return [p for k in it.get('children') or [] for p in leaves(k['$ref'])] if ref.split('/')[1] == 'groups' else [it] if ref.split('/')[1] == 'texts' else []
                pieces = leaves(c['ref']['$ref'])
                markers = [(p.get('text') or '').strip() for p in pieces if (p.get('formatting') or {}).get('script') == 'super' and (p.get('text') or '').strip()]
                text = ' '.join((p.get('text') or '') for p in pieces if (p.get('formatting') or {}).get('script') != 'super' and (p.get('text') or ''))
                struck = [(p.get('text') or '').strip() for p in pieces if (p.get('formatting') or {}).get('strikethrough') and (p.get('text') or '').strip()]
                if not text.strip() and markers: text, markers = ' '.join(markers), []  # a cell printed wholly raised (a mark standing alone, a raised figure) is a cell: its text is what it prints
            if not text.strip(): continue
            cell = {'r': c['start_row_offset_idx'], 'c': c['start_col_offset_idx'], 'rs': c['end_row_offset_idx'] - c['start_row_offset_idx'],
                    'cs': c['end_col_offset_idx'] - c['start_col_offset_idx'], 'text': text, 'header': bool(c.get('column_header'))}
            if markers: cell['markers'] = markers
            if c.get('ref') and struck: cell['struck'] = struck  # Docling says: shown struck through
            if with_index: cell['_i'] = i  # for routes that anchor cells by Docling's own boxes
            cells.append(cell)
        units.append({'id': t['self_ref'], 'kind': 'table', 'cells': cells, 'caption': [item(k['$ref']).get('text') or '' for k in t.get('captions') or []],
                      'notes': [k['$ref'] for k in t.get('footnotes') or []]})

    def walk(ref, layer=None):
        kind, it = ref.split('/')[1], item(ref)
        if kind == 'texts': text_unit(it)
        elif kind == 'tables':
            table_unit(it)
            for k in (it.get('footnotes') or []) + (it.get('captions') or []):  # bodies the tool attached to the table and nowhere else
                if k['$ref'].split('/')[1] == 'texts' and all(u['id'] != k['$ref'] for u in units) and k['$ref'] not in body_refs: text_unit(item(k['$ref']))
        elif kind == 'pictures': units.append({'id': ref, 'kind': 'image', 'text': ''})
        elif kind == 'groups' and (it.get('name') or '').startswith('rich_cell_group'): return  # read by its cell
        if layer and units and units[-1].get('id') == ref: units[-1]['layer'] = layer
        if kind != 'tables':  # headings, pictures and groups may hold further items (pre-order = reading order)
            for k in it.get('children') or []: walk(k['$ref'], layer)

    def refs_under(ref, acc):
        acc.add(ref)
        for k in item(ref).get('children') or []: refs_under(k['$ref'], acc)
        return acc
    body_refs = set()
    for k in doc['body']['children']: refs_under(k['$ref'], body_refs)
    for k in doc['body']['children']: walk(k['$ref'])
    for k in (doc.get('furniture') or {}).get('children') or []: walk(k['$ref'], 'furniture')  # Docling's own layer, kept in its own order
    return units


def route_for(doc, raw, file_id, sha256, seconds, version, settings=None):
    linked = anchor.link(raw, to_units(doc))  # the tool's own order is kept: the reading-order gate measures the tool, not the adapter
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds,
            'route': {'name': NAME, 'tool': 'docling', 'version': version, 'settings': settings or {'backend': 'HTML', 'options': 'defaults'},
                      'adapter': 'benchmarks/prepare/grader/adapters/docling_html.py', 'linker': 'benchmarks/prepare/grader/anchor.py'}, 'units': linked['units'], 'uncovered': linked['uncovered']}


def unsupported(file_id, sha256, version):
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'UNSUPPORTED', 'error': 'not an HTML file', 'seconds': 0,
            'route': {'name': NAME, 'tool': 'docling', 'version': version, 'settings': {}, 'adapter': 'benchmarks/prepare/grader/adapters/docling_html.py', 'linker': None}, 'units': []}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    ap.add_argument('--reuse-raw', action='store_true', help='adapt saved Docling output again instead of converting')
    ap.add_argument('--prestep-headings', action='store_true', help='wrap guide-style heading lines in <h2> before conversion (P7); anchors still point at the original')
    a = ap.parse_args(argv)
    from docling.document_converter import DocumentConverter  # only here: the grader package stays standard-library
    import importlib.metadata as md
    version = next((f"{d} {md.version(d)}" for d in ('docling', 'docling-slim') if _installed(md, d)), 'unknown') + f"; docling-core {md.version('docling-core')}"
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True); (out / 'route').mkdir(exist_ok=True)
    files = {}
    for src in grade.load_sources(a.key, a.catalog):  # sources only: converters never read answers
        if src['split'] == a.split: files.setdefault(src['file_id'], (src['path'], src['sha256']))
    conv, facts = DocumentConverter(), {}
    for fid, (path, sha) in sorted(files.items()):
        (out / 'route' / fid).parent.mkdir(parents=True, exist_ok=True); (out / 'raw' / fid).parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() not in ('.htm', '.html'):
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version))); facts[fid] = {'status': 'UNSUPPORTED'}; continue
        t0 = time.time(); rawjson = out / 'raw' / (fid + '.docling.json')
        try:
            if a.reuse_raw and rawjson.exists():
                doc, dt, status, errors = json.loads(rawjson.read_text()), (json.loads((out / 'facts.json').read_text())['files'].get(fid) or {}).get('docling_seconds', 0), 'reused raw', []
            else:
                src = str(path)
                if a.prestep_headings:
                    from benchmarks.prepare.grader.adapters.prestep_headings import mark_headings
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile(suffix='.htm', delete=False); tmp.write(mark_headings(path.read_bytes())); tmp.close(); src = tmp.name
                res = conv.convert(src); doc = res.document.export_to_dict(); dt = time.time() - t0; status, errors = str(res.status), [str(e) for e in res.errors]
        except Exception as e:  # a tool crash is a result, never a stop
            facts[fid] = {'status': 'FAILED', 'error': repr(e)[:300], 'seconds': round(time.time() - t0, 2)}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(dict(unsupported(fid, sha, version), status='FAILED', error=repr(e)[:300]))); continue
        if not (a.reuse_raw and rawjson.exists()): rawjson.write_text(json.dumps(doc, ensure_ascii=False))
        t1 = time.time(); route = route_for(doc, path.read_bytes(), fid, sha, round(dt, 2), version, {'backend': 'HTML', 'options': 'defaults', 'prestep': 'headings' if a.prestep_headings else None})
        if a.prestep_headings: route['route']['name'] = NAME + '+headings'
        flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
        facts[fid] = {'status': status, 'docling_seconds': round(dt, 2), 'adapter_seconds': round(time.time() - t1, 2), 'items': len(flat),
                      'unanchored': sum(1 for x in flat if not x.get('anchor')), 'uncovered_spans': len(route['uncovered']),
                      'uncovered_chars': sum(len(anchor.squash(s['text'])) for s in route['uncovered']), 'errors': errors}
        (out / 'route' / (fid + '.json')).write_text(json.dumps(route, ensure_ascii=False))
        print(fid, facts[fid], flush=True)
    (out / 'facts.json').write_text(json.dumps({'route': NAME, 'version': version, 'split': a.split, 'files': facts}, indent=1))
    return 0


def _installed(md, dist):
    try: md.version(dist); return True
    except md.PackageNotFoundError: return False


if __name__ == '__main__':
    raise SystemExit(main())
