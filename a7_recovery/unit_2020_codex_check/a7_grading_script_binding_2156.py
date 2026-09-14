"""Admit one independently reviewed execution-location correction.

The original publication and runtime records remain unchanged. An external
approval pins the actual pre-call copy and its evidence; only the expected
location changes. The existing native auditor still proves every answer.
This is not same-file equivalence or a content-only allowance.
"""
from contextlib import contextmanager

import a4_review_composite as R
import a7_g1_build as G
import audit_worker_access as AUD

CODE_PIN = 'grading_script_binding_owner_sha256'
BINDING_PIN = 'grading_script_binding_sha256'


def _checked(path, pins):
    for name, filename in ((CODE_PIN, __file__), (BINDING_PIN, path)):
        if pins.get(name) != G._sha_file(filename):
            raise ValueError('unapproved script binding: ' + name)
    record = G._read(path)
    if record.get('schema') != 'A7-executed-script-binding-v1':
        raise ValueError('unsupported executed-script binding')
    files = record['evidence_files']
    for key in ('state_path', 'invocation_path', 'precall_path'):
        if record[key] not in files:
            raise ValueError('script binding has no pinned ' + key)
    for filename, expected in files.items():
        if G._sha_file(filename) != expected:
            raise ValueError('script binding evidence changed: ' + filename)
    if G._sha_file(AUD.__file__) != record['native_audit_sha256']:
        raise ValueError('the native audit owner changed')
    before = G._read(record['precall_path'])
    invocation = G._read(record['invocation_path'])
    if (record['published_script_path'] != before['frozen_script_path']
            or record['executed_script_path'] != before['staged_script_path']
            or record['published_script_path'] != invocation['scriptPath']
            or record['script_sha256'] != before['frozen_script_sha256']
            or record['script_sha256'] != before['staged_script_sha256']):
        raise ValueError('the script binding disagrees with its pre-call evidence')
    return record, invocation


@contextmanager
def scope(binding_path, pins):
    """One exact state only; all other native audits retain their original path."""
    record, invocation = _checked(binding_path, pins)
    native = AUD.g1_state_audit

    def audit(state_path, expected):
        if state_path != record['state_path']:
            return native(state_path, expected)
        _checked(binding_path, pins)
        if (expected['script_path'] != record['published_script_path']
                or expected['script_sha256'] != record['script_sha256']
                or expected['args'] != invocation['args']):
            raise ValueError('the script binding names a different published invocation')
        return native(state_path, dict(expected, script_path=record['executed_script_path']))

    with R._using(AUD, g1_state_audit=audit):
        try:
            yield
        finally:
            _checked(binding_path, pins)
