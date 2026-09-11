"""Freeze this bounded local verification; no Git or model operation."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
REC = UNIT.parents[1]
sys.path.insert(0, str(UNIT.parent / 'unit_2006'))
from check_native_isolation_2006 import B

files = {}
empty_dirs = set()


def add(path, reason):
    path = Path(path)
    assert path.is_relative_to(REC) and not path.is_symlink(), path
    if path.is_dir():
        children = sorted(path.iterdir())
        if not children:
            empty_dirs.add(str(path.relative_to(REC)))
        for child in children:
            add(child, reason)
        return
    assert path.is_file(), path
    rel = str(path.relative_to(REC))
    files[rel] = {'path': rel, 'kind': 'file', 'sha256': B.file_sha(str(path)),
                  'bytes': path.stat().st_size, 'reason': reason}


for path in sorted(UNIT.iterdir()):
    if path.is_file() and path.suffix in ('.py', '.tsv', '.md'):
        add(path, 'local checker, exact binding, or continuity record')
add(UNIT / 'owner', 'review-version and final-key context owner')
add(UNIT.parent / 'unit_2008/harness_g1v3/build_kfields_hard_review.py',
    'clarified envelope and selected-slot owner')
for name in ('TEST_codex_prepare2009_a', 'TEST_codex_join2009_a',
             'TEST_codex_signed2009_c', 'TEST_codex_handoff2009_b',
             'TEST_codex_review_retry2009_a', 'integration_a', 'integration_retry'):
    add(UNIT / name, 'completed TEST artifact and the exact native input path it uses')
add(UNIT.parent / 'unit_2010_native_fixture/native',
    'durable exact copies of113 original states and113 transcripts')
add(UNIT.parent / 'unit_2010_native_fixture/NATIVE_FIXTURE_MANIFEST.json',
    'original native file identities and preservation evidence')
add(UNIT.parent / 'unit_2008/TEST_projects/_pristine',
    'explicit synthetic-test template; never a real approval')

attempts = (
    ('codex_old_owner2009_b', 0, 'historical owner native proof'),
    ('codex_closeout2009_a', 0, 'read-only exact closeout replay'),
    ('codex_prepare2009_a', 0, 'four-call preparation'),
    ('codex_join2009_a', 0, 'native final key and candidate'),
    ('codex_signed2009_a', 1, 'diagnostic: TEST pin requested too early'),
    ('codex_signed2009_b', 1, 'diagnostic: wrong TEST signer identity refused'),
    ('codex_signature_failure2009_a', 0, 'read-only explanation of wrong TEST signer'),
    ('codex_signed2009_c', 0, 'native TEST signature, compact lock,33 mutations'),
    ('codex_handoff2009_a', 1, 'diagnostic: required approval binding missing'),
    ('codex_handoff2009_b', 0, 'new TEST key into382 original answers'),
    ('codex_schedule2009_a', 0, 'all66 live slots and schedule/accounting mutations'),
    ('codex_review_retry2009_a', 0, 'selected-slot native invalid-only retry'),
)
results = []
for tag, expected_exit, why in attempts:
    root = UNIT.parent / 'unit_1947/logs' / ('attempt_' + tag)
    exit_code = int((root / 'exit').read_text())
    assert exit_code == expected_exit, (tag, exit_code)
    for name in ('exit', 'stdout.txt', 'stderr.txt', 'owner.tsv'):
        add(root / name, why)
    results.append({'attempt': tag, 'exit': exit_code, 'purpose': why,
                    'stdout_sha256': B.file_sha(str(root / 'stdout.txt'))})
for tag, group, generation, expected_exit in (
    ('codex_review_regression2009_a', 'ordinary', 'join2009', 0),
    ('codex_review_native_regression2009_a', 'native', 'join2009', 1),
    ('codex_native_version2009_b', 'native', 'join2009b', 0),
):
    outer = UNIT.parent / 'unit_1957/logs' / ('attempt_' + tag)
    assert int((outer / 'exit').read_text()) == expected_exit
    for name in ('exit', 'stdout.txt', 'stderr.txt', 'owner.tsv'):
        add(outer / name, 'raw regression or wrong-version diagnostic')
    root = UNIT.parent / 'unit_2006' / ('regression_' + group + '_' + generation)
    add(root / 'PREPARATION.json', 'private regression preparation identity')
    for path in sorted((root / 'logs' / ('attempt_' + tag)).iterdir()):
        if path.is_file():
            add(path, 'full regression report, test inventory, JUnit and frozen inputs')
    add(UNIT.parent / 'unit_2006' / ('map_regression_' + group + '_2006_' + generation + '.tsv'),
        'qualified regression binding before optional ordinary-owner override')
    results.append({'attempt': tag, 'exit': expected_exit,
                    'purpose': 'wrong-version refusal' if expected_exit else 'full regression'})

prior = {}
for name in ('unit_2002', 'unit_2005', 'unit_2006'):
    p = UNIT.parent / name / 'REVIEW_SNAPSHOT.json'
    doc = json.loads(p.read_text())
    entries = doc.get('entries', doc.get('files', []))
    for e in entries:
        assert B.source_sha(str(REC / e['path'])) == e['sha256'], e['path']
    prior[name] = {'manifest_sha256': B.file_sha(str(p)), 'entries_rechecked': len(entries)}

owners = [UNIT / 'owner/a4_review_composite.py',
          UNIT.parent / 'unit_2008/harness_g1v3/build_kfields_hard_review.py']
functions = {str(p.relative_to(REC)): [n.name for n in ast.parse(p.read_text()).body
                                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
             for p in owners}
doc = {
    'kind': 'Locally verified A7 code checkpoint; independent final closeout pending',
    'model_calls': 0, 'recovery_head': 'f985d272569ea09c1e0f96d95bff7ce00792515d',
    'prior_snapshots_rechecked': prior, 'functions_from_live_owners': functions,
    'attempts': results, 'entries': [files[k] for k in sorted(files)],
    'empty_directories': sorted(empty_dirs),
    'limits': [
        'TEST replies/signatures establish execution and refusal behavior, not source truth.',
        'Real4 clarified reviews,33 final source adjudications, signature and grading remain.',
        'Native historical fixtures retain their original prompt; current prompt has its own native TEST proof.',
        'Two legacy ordinary v10-shell/budget fixture skips; actual current accounting is directly tested.',
        'Serial recovery paths are pinned, not a concurrent or drop-in production service; DEBT-1 stays Step3/5.',
        'Full disposable pytest trees and redundant independent-review mutation clones stay on disk, not in this snapshot.',
    ],
}
path = UNIT / 'REVIEW_SNAPSHOT.json'
with path.open('x') as stream:
    json.dump(doc, stream, indent=1)
print(json.dumps({'manifest_sha256': B.file_sha(str(path)), 'files': len(files),
                  'bytes': sum(e['bytes'] for e in files.values()),
                  'empty_directories': len(empty_dirs), 'prior': prior}, indent=1))
