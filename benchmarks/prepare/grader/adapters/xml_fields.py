"""XML route (agreement point 4): one `field` unit per element that carries text, from the standard library's strict XML parser (expat):
the element's expanded name `{namespace}local`, its ancestors' expanded names, the instance it belongs to (the nearest repeated ancestor: its
place among same-named siblings, "2 of 8", and the byte of its start tag, which tells two first children of two parents apart), the element's
own place among its siblings, its text, and the byte span from its start tag to the end of its text. An element whose own text holds inline
elements (prose) is one field read whole: its descendants are formatting, not fields. Attribute values are not read; their count is reported
as `not_read` so the omission is visible. No field list, nothing inferred, nothing repaired: a document that does not parse is reported FAILED
with the parser's own message.

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


def units_of(raw, facts=None):
    """Field units of one XML document; raises expat.ExpatError when the bytes are not a complete, well-formed document. `facts`, when
    given, receives what the route does not read (`attribute_values`)."""
    p = expat.ParserCreate(namespace_separator='}'); stack, leaves, root_counts, attrs = [], [], {}, 0
    def start(name, a):
        nonlocal attrs; attrs += sum(1 for v in a.values() if v.strip())
        parent = stack[-1]['counts'] if stack else root_counts; parent[name] = parent.get(name, 0) + 1
        stack.append({'name': name, 'index': parent[name], 'parent_counts': parent, 'counts': {}, 'own': [], 'parts': [], 'start_tag': p.CurrentByteIndex, 'mark': len(leaves)})
    def data(text):
        fr = stack[-1]; fr['own'].append(text); fr['parts'].append(text)
    def end(name):
        fr = stack.pop(); text = ''.join(fr['parts'])
        if stack: stack[-1]['parts'].append(text)  # a parent that is prose sees its children's text in place
        if not ''.join(fr['own']).strip(): return  # no text of its own: a container of elements, or empty
        del leaves[fr['mark']:]  # prose with inline elements is one field; the elements inside it are formatting, not fields
        leaves.append({'name': fr['name'], 'index': fr['index'], 'siblings': fr['parent_counts'], 'ancestors': [(a['name'], a['index'], a['parent_counts'], a['start_tag']) for a in stack],
                       'text': text.strip(), 'anchor': {'byte_start': fr['start_tag'], 'byte_end_exclusive': p.CurrentByteIndex}})  # from the element's own start tag to the end of its text
    p.StartElementHandler, p.EndElementHandler, p.CharacterDataHandler = start, end, data
    p.Parse(raw, True)
    if facts is not None: facts['attribute_values'] = attrs
    out = []
    for i, leaf in enumerate(leaves):
        group = next(({'index': idx, 'count': counts[name], 'at': at} for name, idx, counts, at in reversed(leaf['ancestors']) if counts[name] > 1), None) \
            or {'index': 1, 'count': 1, 'at': leaf['ancestors'][0][3] if leaf['ancestors'] else leaf['anchor']['byte_start']}  # no repeated ancestor: the document is the instance
        out.append({'id': f'f{i}', 'kind': 'field', 'name': clark(leaf['name']), 'path': [clark(n) for n, _, _, _ in leaf['ancestors']], 'group': group,
                    'siblings': {'index': leaf['index'], 'count': leaf['siblings'][leaf['name']]}, 'text': leaf['text'], 'anchor': leaf['anchor']})
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
        try:
            facts = {}; doc['units'] = units_of(raw, facts)
            if facts.get('attribute_values'): doc['not_read'] = facts  # what the route leaves unread, stated rather than silent
        except expat.ExpatError as e: doc['status'], doc['error'] = 'FAILED', f'not a complete well-formed XML document: {e}'
        doc['seconds'] = round(time.time() - t0, 3); dst.write_text(json.dumps(doc, ensure_ascii=False)); facts[fid] = {'status': doc['status'], 'fields': len(doc['units']), 'seconds': doc['seconds']}
        print(fid, facts[fid], flush=True)
    (out / 'facts.json').write_text(json.dumps({'route': route, 'files': facts}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
