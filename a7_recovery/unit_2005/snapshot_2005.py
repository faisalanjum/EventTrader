"""Read-only exact code/test freeze; emits JSON, never writes or calls a model."""
import ast
import hashlib
import json
from pathlib import Path

unit = Path(__file__).resolve().parent
a7 = unit.parent
files = set()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    files.update(p for p in path.rglob('*') if p.is_file()
                 and not p.is_symlink() and '__pycache__' not in p.parts)


prior_path = a7 / 'unit_2002/REVIEW_SNAPSHOT.json'
prior = json.loads(prior_path.read_text())
drift = [r['path'] for r in prior['files']
         if not Path(r['path']).is_file() or sha(Path(r['path'])) != r['sha256']]
assert not drift, drift
files.add(prior_path)
files.update(p for p in unit.iterdir() if p.is_file()
             and p.name != 'REVIEW_SNAPSHOT.json')
tree(unit / 'owner')
for name in ('build_final_key_candidate.py', 'signer_proof.py',
             'harvest_final_sign.py', 'build_final_key_lock.py'):
    files.add(a7 / 'unit_1955/lock_owners' / name)
attempts = ('codex_candidate2005_b', 'codex_signed2005_a',
            'codex_approved2005_b', 'codex_scope2005_a')
for tag in attempts:
    log = a7 / 'unit_1947/logs' / ('attempt_' + tag)
    assert (log / 'exit').read_text().strip() == '0', tag
    assert not (log / 'stderr.txt').read_bytes(), tag
    tree(log)
    tree(unit / ('TEST_' + tag))
evidence = unit / 'TEST_codex_signed2005_a/candidate/signer/final_sign.attempt1.evidence.json'
signer = json.loads(evidence.read_text())
official = Path('/home/faisal/.claude/projects')
for field in ('state_path', 'transcript_path'):
    physical = a7 / 'unit_2002/TEST_projects' / Path(signer[field]).relative_to(official)
    assert sha(physical) == signer[field.replace('_path', '_sha256')]
    files.add(physical)
functions = {p.name: [{'name': n.name, 'line': n.lineno}
                    for n in ast.parse(p.read_text()).body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
             for p in sorted((unit / 'owner').glob('*.py'))}
print(json.dumps({
    'kind': 'A7 source-only key HANDOFF CODE; TEST evidence only, no factual key approval',
    'model_calls': 0,
    'prior_snapshot_sha256': sha(prior_path), 'prior_pins_rechecked': len(prior['files']),
    'prior_pin_drift': drift, 'functions_from_live_owners': functions,
    'tests': [{'attempt': tag, 'exit': 0,
               'stdout_sha256': sha(a7 / 'unit_1947/logs' / ('attempt_' + tag) / 'stdout.txt')}
              for tag in attempts],
    'files': [{'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size}
              for p in sorted(files)],
    'file_count': len(files),
    'limits': ['Core independent review pending', 'Real key meaning/signature unapproved',
               'A5/A6 saved-answer evaluation packet not created by these tests',
               'No actual A7 grading result or production certification'],
}, indent=1))
