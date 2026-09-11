"""Ordinary regression over the changed deterministic review owner.

The native cohort contains completed historical prompt identities. Run it
with prepare_regression_2006.py's original owner binding, not this override.
The clarified prompt's native lifecycle is exercised by check_integration.py.
"""
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT.parent / 'unit_2006'))
from check_native_isolation_2006 import B, check

assert len(sys.argv) == 1, 'this override is only for the ordinary cohort'
rows = B.read_map(str(UNIT.parent / 'unit_2006/map_regression_ordinary_2006_join2009.tsv'))
assert check(rows)
harness = next(r for r in rows if r['logical'].endswith('/experiments/harness_g1v3')
               and '/bench_1306/' in r['logical'])
owner = UNIT.parent / 'unit_2008/harness_g1v3/build_kfields_hard_review.py'
assert B.file_sha(str(owner)) == 'ceef0f20e090e0793320fe1def79d958189d715a2dda7ddb48039e9ed6d0cc1b'
rows.append(dict(logical=harness['logical'] + '/' + owner.name, source=str(owner),
                 sha=B.file_sha(str(owner)), mode='ro'))
assert not B.validate(rows), B.validate(rows)
path = UNIT / 'map_regression_review_a.tsv'
with path.open('x') as stream:
    stream.write(''.join('\t'.join(r[k] for k in ('logical','source','sha','mode'))
                        + '\n' for r in rows))
print(path)
