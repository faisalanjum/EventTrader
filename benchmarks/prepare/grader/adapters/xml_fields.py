"""XML route (agreement point 4): one `field` unit per leaf element that carries text, from the standard library's strict XML parser (expat):
the element's expanded name `{namespace}local`, its ancestors' expanded names, its place among same-named siblings of the nearest repeated
ancestor ("2 of 8"), its text, and the byte span from its start tag to the end of its text. No field list, nothing inferred, nothing repaired:
a document that does not parse is reported FAILED with the parser's own message.

    python3 -m benchmarks.prepare.grader.adapters.xml_fields --key <key package> --split development --out <run dir> [--catalog CSV]"""
import argparse
import json
import time
import xml.parsers.expat as expat
from pathlib import Path

from benchmarks.prepare.grader import grade

NAME = 'xml-fields'


def clark(name):
    return '{' + name if '}' in name else name


def units_of(raw):
    """Field units of one XML document; raises expat.ExpatError when the bytes are not a complete, well-formed document."""
    p = expat.ParserCreate(namespace_separator='}'); stack, leaves, root_counts = [], [], {}
    def start(name, attrs):
        parent = stack[-1]['counts'] if stack else root_counts; parent[name] = parent.get(name, 0) + 1
        stack.append({'name': name, 'index': parent[name], 'parent_counts': parent, 'counts': {}, 'text': [], 'text_start': None, 'has_child': False, 'start_tag': p.CurrentByteIndex})
        if len(stack) > 1: stack[-2]['has_child'] = True
    def data(text):
        fr = stack[-1]
        if fr['text_start'] is None: fr['text_start'] = p.CurrentByteIndex
        fr['text'].append(text)
    def end(name):
        fr = stack.pop(); text = ''.join(fr['text'])
        if fr['has_child'] or not text.strip(): return
        leaves.append({'name': clark(fr['name']), 'ancestors': [(a['name'], a['index'], a['parent_counts']) for a in stack], 'text': text.strip(),
                       'anchor': {'byte_start': fr['start_tag'], 'byte_end_exclusive': p.CurrentByteIndex}})  # from the element's own start tag to the end of its text
    p.StartElementHandler, p.EndElementHandler, p.CharacterDataHandler = start, end, data
    p.Parse(raw, True)
    out = []
    for i, leaf in enumerate(leaves):
        group = next(({'index': idx, 'count': counts[name]} for name, idx, counts in reversed(leaf['ancestors']) if counts[name] > 1), {'index': 1, 'count': 1})
        out.append({'id': f'f{i}', 'kind': 'field', 'name': leaf['name'], 'path': [clark(n) for n, _, _ in leaf['ancestors']], 'group': group, 'text': leaf['text'], 'anchor': leaf['anchor']})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    a = ap.parse_args(argv); out = Path(a.out); facts = {}
    route = {'name': NAME, 'tool': 'python xml.parsers.expat', 'version': expat.EXPAT_VERSION, 'settings': {'namespaces': True, 'recover': False}, 'adapter': 'benchmarks/prepare/grader/adapters/xml_fields.py', 'linker': None}
    for s in grade.load_sources(a.key, a.catalog):
        fid, path, sha = s['file_id'], s['path'], s['sha256']
        if s['split'] != a.split or path.suffix.lower() != '.xml': continue
        dst = out / 'route' / (fid + '.json'); dst.parent.mkdir(parents=True, exist_ok=True); t0 = time.time()
        raw = path.read_bytes(); doc = {'schema': 'prepare-route-output/1', 'file_id': fid, 'sha256': sha, 'status': 'OK', 'error': None, 'route': route, 'units': []}
        try: doc['units'] = units_of(raw)
        except expat.ExpatError as e: doc['status'], doc['error'] = 'FAILED', f'not a complete well-formed XML document: {e}'
        doc['seconds'] = round(time.time() - t0, 3); dst.write_text(json.dumps(doc, ensure_ascii=False)); facts[fid] = {'status': doc['status'], 'fields': len(doc['units']), 'seconds': doc['seconds']}
        print(fid, facts[fid], flush=True)
    (out / 'facts.json').write_text(json.dumps({'route': route, 'files': facts}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
