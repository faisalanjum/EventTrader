"""XML route (agreement point 4): one `field` unit per element that carries text, from the standard library's strict XML parser (expat):
the element's expanded name `{namespace}local`, its ancestors' expanded names, the instance it belongs to (the nearest repeated ancestor: its
place among same-named siblings, "2 of 8", and the byte of its start tag, which tells two first children of two parents apart), the element's
own place among its siblings, its text, and the byte span from its start tag to the end of its text. Units stand in source order. An element whose
own text stands around child elements is read whole as prose (`mixed`) and its children stay fields of their own, each naming the prose unit it
stands `within`: the reading stream is the units held by no other, each source character once; field lookups see every unit (Codex R13 C4).
Attribute values are not read; their count is reported as `not_read` so the omission is visible. No field list, nothing inferred, nothing
repaired: a document that does not parse is reported FAILED with the parser's own message. The parser is the grader's own (`anchor.xml_parser`):
what stands outside the document is refused, so a reading that would need it fails instead of going on without it; an element the parser
makes from an entity's text has no bytes of its own, and the document is refused rather than given a position that is none.

    python3 -m benchmarks.prepare.grader.adapters.xml_fields --key <key package> --split development --out <run dir> [--catalog CSV]"""
# The runtime lives in driver.prepare.convert.xml_fields (moved 2026-10-07); this module keeps the command line over key packets.
import argparse
import json
import time
import xml.parsers.expat as expat
from pathlib import Path
from benchmarks.prepare.grader import grade
from driver.prepare.convert.xml_fields import NAME, clark, units_of


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
            unread = {}; doc['units'] = units_of(raw, unread)  # the per-file unread count, apart from the run's facts
            if unread.get('attribute_values'): doc['not_read'] = unread  # what the route leaves unread, stated rather than silent
        except (expat.ExpatError, ValueError, LookupError) as e: doc['status'], doc['error'] = 'FAILED', f'XML parse failed: {e}'
        doc['seconds'] = round(time.time() - t0, 3); dst.write_text(json.dumps(doc, ensure_ascii=False)); facts[fid] = {'status': doc['status'], 'fields': len(doc['units']), 'seconds': doc['seconds']}
        print(fid, facts[fid], flush=True)
    (out / 'facts.json').write_text(json.dumps({'route': route, 'files': facts}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
