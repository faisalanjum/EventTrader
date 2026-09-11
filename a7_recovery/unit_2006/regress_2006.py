"""Run every shipped harness test file, separately, under either exact map.

The baseline and candidate runs use this same payload and tests. Save complete
stdout/stderr for each test; compare real failures rather than green totals.
No model calls or database writes are part of this harness suite.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT.parent / 'unit_1997/owner'))
import a4_source_key as SK
HARNESS = Path(SK.F.__file__).parent
out = UNIT / ('REGRESSION_' + os.environ['A7_TAG'])
out.mkdir()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
           PYTHONPATH=str(HARNESS) + os.pathsep + '/home/faisal/EventMarketDB')
results = []
for path in sorted(HARNESS.glob('test_*.py')):
    result = subprocess.run([sys.executable, '-B', '-m', 'pytest', '-q',
                             '-p', 'no:cacheprovider', str(path)],
                            cwd=str(HARNESS), env=env, capture_output=True, text=True)
    SK.RT.write_new(str(out / (path.stem + '.stdout.txt')), result.stdout)
    SK.RT.write_new(str(out / (path.stem + '.stderr.txt')), result.stderr)
    row = {'test': path.name, 'test_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
           'exit': result.returncode, 'summary': result.stdout.strip().splitlines()[-1:]}
    results.append(row)
    print(json.dumps(row), flush=True)
SK.RT.write_new(str(out / 'RESULTS.json'), json.dumps(results, indent=1))
print(json.dumps({'suite_files': len(results), 'failures': sum(r['exit'] != 0 for r in results)}))
raise SystemExit(0 if all(r['exit'] == 0 for r in results) else 3)
