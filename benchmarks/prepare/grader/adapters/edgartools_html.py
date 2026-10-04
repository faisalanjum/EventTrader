"""Route adapter: edgartools `parse_html` -> the common route format, anchored by the shared linker.
edgartools keeps no source positions, so the linker places every block. Under its own environment the adapter first
dumps the parsed node tree to plain JSON (kept as the raw output); `to_units` works on that dump, so it is testable
without the package. Shape rules only, no document-specific logic.

    <edgartools python> -m benchmarks.prepare.grader.adapters.edgartools_html --key <key package> --split development --out <run dir> [--catalog CSV]"""
import argparse
import json
import time
from pathlib import Path

from benchmarks.prepare.grader import anchor, grade

NAME = 'edgartools-html'  # the tool's heading nodes nested inside paragraphs are kept as headings
KIND = {'HeadingNode': 'heading', 'ParagraphNode': 'text', 'TextNode': 'text', 'ListItemNode': 'list_item', 'ImageNode': 'image'}
BRANCH = ('DocumentNode', 'ContainerNode', 'SectionNode', 'ListNode')
BLOCKY = ('HeadingNode', 'ParagraphNode', 'ContainerNode', 'SectionNode', 'ListNode', 'TableNode', 'ListItemNode')  # children that make their parent a branch


def dump(node):
    """Plain-dict copy of an edgartools node tree (run under the edgartools environment)."""
    kind = type(node).__name__
    d = {'type': kind}
    if kind == 'TableNode':
        rows = list(node.headers or []) + [getattr(r, 'cells', r) for r in node.rows or []]
        d['caption'] = node.caption
        d['rows'] = [[{'text': (c.text() if callable(c.text) else c.text) or '', 'colspan': c.colspan or 1, 'rowspan': c.rowspan or 1, 'is_header': bool(c.is_header)} for c in row] for row in rows]
        return d
    kids = list(getattr(node, 'children', None) or [])
    if kind in BRANCH:
        d['children'] = [dump(k) for k in kids]; return d
    text = node.text() if callable(getattr(node, 'text', None)) else getattr(node, 'text', '')
    heads = [k for k in kids if type(k).__name__ == 'HeadingNode']
    if heads:  # the tool's heading claim inside a paragraph: kept when its text is the paragraph's start or end (the parser's own text, no new joins)
        ht = (heads[0].text() or '').strip(); pt = (text or '').strip()
        if ht and pt.startswith(ht): d['heading'] = {'text': ht, 'level': getattr(heads[0], 'level', None)}; d['rest'] = pt[len(ht):].strip(); d['order'] = 'head_first'
        elif ht and pt.endswith(ht): d['heading'] = {'text': ht, 'level': getattr(heads[0], 'level', None)}; d['rest'] = pt[:-len(ht)].strip(); d['order'] = 'head_last'
    d['text'] = text or ''
    for k in ('level', 'src', 'href'):
        if getattr(node, k, None) is not None: d[k] = getattr(node, k)
    links = [{'text': (l.text() if callable(l.text) else l.text) or '', 'href': l.href} for l in node.walk() if type(l).__name__ == 'LinkNode'] if hasattr(node, 'walk') else []
    if links: d['links'] = links
    return d


def to_units(tree):
    units = []

    def table_unit(t):
        cells, until = [], {}  # until[column] = the first row at which that column is free again: a rowspan expires by row, whatever later rows hold
        for r, row in enumerate(t.get('rows') or []):
            c = 0
            for cell in row:
                while until.get(c, 0) > r: c += 1
                cs, rs = cell.get('colspan') or 1, cell.get('rowspan') or 1
                if (cell.get('text') or '').strip():
                    cells.append({'r': r, 'c': c, 'rs': rs, 'cs': cs, 'text': cell['text'], 'header': bool(cell.get('is_header'))})
                for k in range(c, c + cs): until[k] = r + rs
                c += cs
        units.append({'id': f't{len(units)}', 'kind': 'table', 'cells': cells, 'caption': [t['caption']] if t.get('caption') else []})

    def walk(n):
        kind = n['type']
        if kind == 'TableNode': table_unit(n)
        elif kind in BRANCH:
            for k in n.get('children') or []: walk(k)
        elif n.get('heading'):  # a paragraph the tool marks as (or starting/ending with) a heading
            parts = [('heading', n['heading']['text'], n['heading'].get('level')), ('text', n.get('rest') or '', None)]
            if n.get('order') == 'head_last': parts.reverse()
            for kind2, text2, level in parts:
                if not anchor.squash(text2): continue
                u = {'id': f'u{len(units)}', 'kind': kind2, 'text': text2}
                if level is not None: u['level'] = level
                units.append(u)
        elif kind == 'ImageNode': units.append({'id': f'u{len(units)}', 'kind': 'image', 'text': ''})
        else:
            if not anchor.squash(n.get('text') or ''): return  # whitespace or control characters only: not a block
            u = {'id': f'u{len(units)}', 'kind': KIND.get(kind, 'other'), 'text': n.get('text') or ''}
            if n.get('level') is not None: u['level'] = n['level']
            if n.get('links'): u['links'] = [{'text': l['text'], 'href': l['href'], 'to': None} for l in n['links']]
            units.append(u)
    walk(tree)
    return units


def route_for(tree, raw, file_id, sha256, seconds, version):
    linked = anchor.link(raw, to_units(tree))
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds,
            'route': {'name': NAME, 'tool': 'edgartools', 'version': version, 'settings': {'parse_html': 'defaults'}, 'adapter': 'benchmarks/prepare/grader/adapters/edgartools_html.py',
                      'linker': 'benchmarks/prepare/grader/anchor.py'}, 'units': linked['units'], 'uncovered': linked['uncovered']}


def unsupported(file_id, sha256, version, status='UNSUPPORTED', error='not an HTML file'):
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': status, 'error': error, 'seconds': 0,
            'route': {'name': NAME, 'tool': 'edgartools', 'version': version, 'settings': {}, 'adapter': 'benchmarks/prepare/grader/adapters/edgartools_html.py', 'linker': None}, 'units': []}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    ap.add_argument('--reuse-raw', action='store_true', help='adapt the saved node dump again instead of parsing')
    a = ap.parse_args(argv)
    from edgar.documents import parse_html  # only here: the grader package stays standard-library
    import importlib.metadata as md
    version = f"edgartools {md.version('edgartools')}"
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True); (out / 'route').mkdir(exist_ok=True)
    files = {}
    for src in grade.load_sources(a.key, a.catalog):  # sources only: converters never read answers
        if src['split'] == a.split: files.setdefault(src['file_id'], (src['path'], src['sha256']))
    facts = {}
    for fid, (path, sha) in sorted(files.items()):
        (out / 'route' / fid).parent.mkdir(parents=True, exist_ok=True); (out / 'raw' / fid).parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() not in ('.htm', '.html'):
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version))); facts[fid] = {'status': 'UNSUPPORTED'}; continue
        raw = path.read_bytes(); t0 = time.time(); rawjson = out / 'raw' / (fid + '.edgartools.json')
        try:
            if a.reuse_raw and rawjson.exists():
                tree, dt = json.loads(rawjson.read_text()), (json.loads((out / 'facts.json').read_text())['files'].get(fid) or {}).get('tool_seconds', 0)
            else:
                try: text = raw.decode('utf-8')
                except UnicodeDecodeError: text = raw.decode('cp1252', 'replace')
                tree = dump(parse_html(text).root); dt = time.time() - t0
        except Exception as e:  # a tool crash is a result, never a stop
            facts[fid] = {'status': 'FAILED', 'error': repr(e)[:300], 'seconds': round(time.time() - t0, 2)}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version, 'FAILED', repr(e)[:300]))); continue
        if not (a.reuse_raw and rawjson.exists()): rawjson.write_text(json.dumps(tree, ensure_ascii=False))
        t1 = time.time(); route = route_for(tree, raw, fid, sha, round(dt, 2), version)
        flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
        facts[fid] = {'status': 'OK', 'tool_seconds': round(dt, 2), 'adapter_seconds': round(time.time() - t1, 2), 'items': len(flat),
                      'unanchored': sum(1 for x in flat if not x.get('anchor')), 'uncovered_spans': len(route['uncovered']),
                      'uncovered_chars': sum(len(anchor.squash(s['text'])) for s in route['uncovered'])}
        (out / 'route' / (fid + '.json')).write_text(json.dumps(route, ensure_ascii=False))
        print(fid, facts[fid], flush=True)
    (out / 'facts.json').write_text(json.dumps({'route': NAME, 'version': version, 'split': a.split, 'files': facts}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
