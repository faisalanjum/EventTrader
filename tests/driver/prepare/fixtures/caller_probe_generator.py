"""Test-only generation child for tests/driver/prepare/test_caller.py (never a converter). Same argv as driver/prepare/document.py.
It records what actually executed it (interpreter, HOME, CPU affinity, working directory). If its plan row says `probe.complete`, it then
writes a minimal completion for that row so the job goes on to reconstruct and verify. Otherwise it exits 1 after START."""
import hashlib, json, os, sys
from pathlib import Path

plan_path, pin, k, attempt = sys.argv[1:]
body = Path(plan_path).read_bytes()
assert hashlib.sha256(body).hexdigest() == pin, 'plan pin mismatch'
row = json.loads(body)['source_commands'][int(k)]
a = Path(attempt); a.mkdir(mode=0o700)
(a / 'START.json').write_text(json.dumps({'ordinal': int(k)}))
(a / 'PROBE.json').write_text(json.dumps({'executable': sys.executable, 'home': os.environ.get('HOME'),
                                          'affinity': sorted(os.sched_getaffinity(0)), 'cwd': os.getcwd()}))
if not row['probe']['complete']: sys.exit(1)
route = json.dumps({'status': 'OK', 'units': []}).encode()
(a / 'ROUTE.json').write_bytes(route)
(a / 'COMPLETE.json').write_text(json.dumps({'file_id': row['file_id'], 'source_sha256': row['source_sha256'], 'route_sha256': hashlib.sha256(route).hexdigest(),
                                             'native_status': 'OK', 'prepared_input_sha256': [], 'reader_called': False}))
