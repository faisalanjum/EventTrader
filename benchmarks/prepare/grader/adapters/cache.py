"""A saved conversion is reused only whole (Codex R13 C1). Beside the raw output sits a record of the run that produced it: the source bytes
(sha256), the producing tool version and settings, every output file with its own hash, and the run's own outcome. The record is removed before
any output is written again and written only after every output is saved, so a crash in between leaves no record and no stale success. Reuse
checks the record against the files on disk and keeps the producing version: a newer installed tool never relabels an old conversion."""
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def begin(record):
    """The old record no longer vouches for what is about to be written."""
    Path(record).unlink(missing_ok=True)


def save(record, outputs, **run):
    """Written last: `outputs` are the files this run saved (beside the record), `run` its source hash, version, settings and outcome."""
    Path(record).write_text(json.dumps({**run, 'outputs': {Path(p).name: sha256(p) for p in outputs}}))


def reuse(record, sha, settings):
    """The record of a run over these source bytes with these settings whose outputs are still the saved files; RuntimeError says why not."""
    record = Path(record)
    if not record.exists(): raise RuntimeError('cache refused: no record of the cached run')
    m = json.loads(record.read_text())
    problem = ('the cached run converted other bytes' if m.get('sha256') != sha else 'the cached run used other settings' if m.get('settings') != settings
               else 'the cached run recorded no version or outputs' if not (m.get('version') and m.get('outputs'))
               else next((f'{n} is not the file the cached run saved' for n, h in m['outputs'].items() if not (record.parent / n).exists() or sha256(record.parent / n) != h), None))
    if problem: raise RuntimeError(f'cache refused: {problem}')
    return m
