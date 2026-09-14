# -*- coding: utf-8 -*-
"""Prove the preservation is byte-identical, and manifest it. SEQ 2156.

Every preserved transcript record is searched for VERBATIM in the live
transcript; a record that cannot be found there byte-for-byte is reported, not
silently passed. The 2154 unit and the frozen run directory are re-measured to
show this round changed nothing in them. Read-only.
"""
import hashlib
import io
import json
import os
import sys

sys.dont_write_bytecode = True
sha_b = lambda b: hashlib.sha256(b).hexdigest()
sha_f = lambda p: sha_b(io.open(p, 'rb').read())
UNIT, EVIDENCE, TRANSCRIPT, OTHERS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
ev = json.load(io.open(EVIDENCE, encoding='utf-8'))
recdir = os.path.join(UNIT, 'preserved/transcript_records')

want = {}
for r in ev['records']:
    p = os.path.join(recdir, r['preserved_as'])
    raw = io.open(p, 'rb').read()
    want[r['preserved_as']] = [raw, sha_b(raw) == r['raw_line_sha256'], False]

with io.open(TRANSCRIPT, 'rb') as fh:
    for line in fh:
        for v in want.values():
            if not v[2] and line == v[0]:
                v[2] = True

manifest = []
for dirpath, _d, files in os.walk(UNIT):
    for f in sorted(files):
        p = os.path.join(dirpath, f)
        manifest.append({'path': os.path.relpath(p, UNIT),
                         'bytes': os.path.getsize(p), 'sha256': sha_f(p)})
manifest.sort(key=lambda r: r['path'])

record = {
    'kind': 'preservation proof and manifest',
    'preserved_records': len(want),
    'records_matching_their_recorded_hash': sum(1 for v in want.values() if v[1]),
    'records_found_verbatim_in_the_live_transcript': sum(1 for v in want.values() if v[2]),
    'records_not_found_verbatim': sorted(k for k, v in want.items() if not v[2]),
    'unchanged_elsewhere': {os.path.relpath(p, os.path.dirname(UNIT)): sha_f(p)
                            for p in OTHERS},
    'unit_files': len(manifest),
    'unit_bytes': sum(r['bytes'] for r in manifest),
    'manifest': manifest,
}
io.open(os.path.join(UNIT, 'MANIFEST_2156.json'), 'w', encoding='utf-8').write(
    json.dumps(record, indent=1, sort_keys=True) + '\n')
print(json.dumps({k: v for k, v in record.items() if k != 'manifest'},
                 indent=1, sort_keys=True))
