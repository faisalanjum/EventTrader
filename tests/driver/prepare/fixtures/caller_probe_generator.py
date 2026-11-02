"""Test-only generation child for tests/driver/prepare/test_caller.py (never a converter). Same argv as driver/prepare/document.py.
It records what actually executed it (interpreter, HOME, CPU affinity, working directory). If its plan row says `probe.complete`, it then
writes a minimal completion for that row so the job goes on to reconstruct and verify. Otherwise it exits 1 after START."""
import gzip, hashlib, json, os, sys
from pathlib import Path

plan_path, pin, k, attempt = sys.argv[1:]
body = Path(plan_path).read_bytes()
assert hashlib.sha256(body).hexdigest() == pin, 'plan pin mismatch'
row = json.loads(body)['source_commands'][int(k)]
a = Path(attempt); a.mkdir(mode=0o700)
(a / 'START.json').write_text(json.dumps({'ordinal': int(k)}))
(a / 'PROBE.json').write_text(json.dumps({'executable': sys.executable, 'home': os.environ.get('HOME'),
                                          'affinity': sorted(os.sched_getaffinity(0)), 'cwd': os.getcwd()}))
if row['probe'].get('snapshots'):
    for folder in (a, a / 'scriptless_attempt', a / 'unverified'):
        folder.mkdir(exist_ok=True)
        for name in ('ROUTE_BEFORE_INPUTS.json', 'ROUTE_AFTER_INPUTS.json'):
            (folder / name).write_text('{"diagnostic": true}')
    (a / 'OTHER.json').write_text('{"keep": true}')
if not row['probe']['complete']: sys.exit(1)
route = json.dumps({'status': 'OK', 'units': []}).encode()
(a / 'ROUTE.json').write_bytes(route)
(a / 'COMPLETE.json').write_text(json.dumps({'file_id': row['file_id'], 'source_sha256': row['source_sha256'], 'route_sha256': hashlib.sha256(route).hexdigest(),
                                             'native_status': 'OK', 'prepared_input_sha256': [], 'reader_called': False}))
if row['probe'].get('capture'):
    raw = b'Independent captured revenue 125 and cost -7.'
    digest = hashlib.sha256(raw).hexdigest(); good = gzip.compress(raw)
    variants = {'good': good, 'missing': None, 'not_gzip': b'bad', 'truncated': good[:-4],
                'wrong_hash': gzip.compress(b'wrong'), 'bad_deflate': good[:10] + b'\xff' + good[11:],
                'bad_crc': good[:-8] + bytes([good[-8] ^ 1]) + good[-7:]}
    target = a
    where = row['probe'].get('capture_where', 'initial')
    if where != 'initial':
        target = a / ('source_reading' if where == 'source' else 'states/activated@0')
        target.mkdir(parents=True)
        for name in ('ROUTE.json', 'COMPLETE.json'): (target / name).write_bytes((a / name).read_bytes())
        if where == 'state':
            parent_route = json.loads(route)
            parent_route['source_links'] = [{'tag': {'byte_start': 0}, 'activations': [{'state': 'activated@0', 'route_sha256': hashlib.sha256(route).hexdigest()}]}]
            (a / 'ROUTE.json').write_text(json.dumps(parent_route))
    (target / 'captures').mkdir()
    data = variants[row['probe']['capture']]
    if data is not None: (target / 'captures' / (digest + '.gz')).write_bytes(data)
    (target / 'CONTEXT_RENDERS.json').write_text(json.dumps([{'capture': {'sha256': digest}}]))
