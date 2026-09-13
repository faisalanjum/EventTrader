"""Provision the CURRENT TEST view through the EXISTING preparer.

Two scoped bindings, both restored afterwards, and prepare.py itself untouched:

  * prepare.HARNESS -> this unit's private CURRENT tree (unit_2008 plus the
    map_g23_transport_2098 overlays, which is the real map plus only the one
    new G2/G3 grouping owner).
  * boundary.read_map -> for the ONE historical template path, read this
    unit's private copy instead. That copy differs from the original in
    exactly one field: the main FinalDesign directory pin, re-measured from
    the live tree. Validation stays on and the original validator is used
    unchanged; the historical template is never written.

Everything else - the fixture lineage, the key fixture, the reuse path - comes
from the verified sources the previous native run already used.
"""
import collections
import hashlib
import io
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A7 = HERE.parent
REC = A7.parent
NAME = os.environ.get('A7_PROVISION_NAME', 'core2099base')
REUSE = 'path7'                       # the attempt that owns the trace fixture
PAYLOAD = HERE / 'payload_2099.py'
PRIVATE = HERE / 'harness_g1v3'
TEMPLATE_COPY = HERE / 'template_2099_test.tsv'
OUT = HERE / 'PROVISION_2099.json'

sys.path.insert(0, str(REC / 'a4_recovery/regen_1570/targeted_1589'
                             '/post_1500_exact_1626/out/a4_final_lock_1683/launcher'))
sys.path.insert(0, str(A7 / 'grader_20260909'))
import boundary as B                                             # noqa: E402
import prepare as P                                              # noqa: E402

ORIGINAL_TEMPLATE = P.UNIT / 'map_1957_test.tsv'


def sha(path):
    with io.open(str(path), 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def write_private_template():
    """The historical template with ONE re-measured pin, and nothing else."""
    rows = B.read_map(str(ORIGINAL_TEMPLATE))
    changed = []
    for row in rows:
        if row['mode'] != 'ro' or row['sha'] in ('-', '', None):
            continue
        measured = B.source_sha(row['source'])
        if measured != row['sha']:
            changed.append({'logical': row['logical'], 'source': row['source'],
                            'was': row['sha'], 'now': measured})
            row['sha'] = measured
    assert len(changed) == 1, 'expected exactly one drifted pin, got %d' % len(changed)
    with io.open(str(TEMPLATE_COPY), 'x', encoding='utf-8') as fh:
        for row in rows:
            fh.write('\t'.join(row[k] for k in
                               ('logical', 'source', 'sha', 'mode')) + '\n')
    # the copy must differ from the original in exactly one line
    a = io.open(str(ORIGINAL_TEMPLATE), encoding='utf-8').read().split('\n')
    b = io.open(str(TEMPLATE_COPY), encoding='utf-8').read().split('\n')
    assert len(a) == len(b), 'the copy changed the row count'
    differing = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    assert len(differing) == 1, 'the copy differs on %d lines' % len(differing)
    assert not B.validate(B.read_map(str(TEMPLATE_COPY))), 'the copy still refuses'
    return changed[0], differing[0]


if not TEMPLATE_COPY.exists():
    change, line = write_private_template()
else:
    change, line = None, None

original_read_map = B.read_map
original_harness = P.HARNESS
redirects = []


def scoped_read_map(path, *a, **k):
    """The existing read_map, pointed at the private copy for that ONE path."""
    if os.path.abspath(path) == os.path.abspath(str(ORIGINAL_TEMPLATE)):
        redirects.append(path)
        return original_read_map(str(TEMPLATE_COPY), *a, **k)
    return original_read_map(path, *a, **k)


P.HARNESS = PRIVATE
B.read_map = scoped_read_map
try:
    result = P.prepare(NAME, PAYLOAD, native=True, key_fixture=True, reuse=REUSE)
finally:
    B.read_map = original_read_map
    P.HARNESS = original_harness

report = json.load(io.open(str(HERE / 'PRIVATE_HARNESS_2099.json')))
record = collections.OrderedDict([
    ('kind', 'CURRENT TEST view provisioned through the existing preparer'),
    ('preparer', str(A7 / 'grader_20260909/prepare.py')),
    ('preparer_sha256', sha(A7 / 'grader_20260909/prepare.py')),
    ('bound_harness', str(PRIVATE)),
    ('bound_harness_tree_sha256', report['private_tree_sha256']),
    ('harness_overlays', [o['name'] for o in report['overrides']]),
    ('original_template', str(ORIGINAL_TEMPLATE)),
    ('original_template_sha256', sha(ORIGINAL_TEMPLATE)),
    ('private_template', str(TEMPLATE_COPY)),
    ('private_template_sha256', sha(TEMPLATE_COPY)),
    ('the_one_changed_pin', change),
    ('differing_line_index', line),
    ('template_redirects_used', len(redirects)),
    ('validation_left_enabled', True),
    ('reuse_attempt', REUSE),
    ('result', result),
    ('model_calls', 0)])
with io.open(str(OUT), 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print(json.dumps(record, indent=1))
