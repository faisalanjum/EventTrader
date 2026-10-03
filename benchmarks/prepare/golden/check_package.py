"""Is the golden-set package still where PACKAGE.json says, byte-for-byte? Then run the package's own gate. Stdlib only.
Usage: python3 benchmarks/prepare/golden/check_package.py"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
rec = json.loads((HERE / 'PACKAGE.json').read_text())
pkg = Path(rec['package_path'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
bad = [(rel, got) for rel, want in rec['files_sha256'].items() if (got := sha(pkg / rel)) != want]
bad += [('golden/' + rel, got) for rel, want in rec['copies_sha256'].items() if (got := sha(HERE / rel)) != want]
if bad:
    print('CHANGED OR MISSING:', bad); sys.exit(1)
print(f"package {pkg.name}: {len(rec['files_sha256'])} recorded files unchanged; {len(rec['copies_sha256'])} verbatim copies match")
r = subprocess.run([sys.executable, '-B', str(pkg / 'VERIFY_PACKAGE.py')], capture_output=True, text=True, cwd='/')
print(r.stdout.strip() or r.stderr.strip()); sys.exit(r.returncode)
