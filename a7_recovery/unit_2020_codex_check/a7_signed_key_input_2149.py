"""Serve one externally approved signed key through the existing A5 readers.

The original evaluation is proved before this serial scope. Only the three
approved-key input aliases change; their expected hashes come from a separately
pinned, verified lock report. The same A5 hash/lock/receipt readers still run.
No key is constructed here and no validation is replaced.
"""
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def approved_inputs(E, A5, report_path, expected_sha256):
    if E.G._sha_file(str(report_path)) != expected_sha256:
        raise ValueError('unapproved signed-key report')
    report = E.K._load(str(report_path))
    candidate = Path(report['candidate'])
    if (Path(report['lock']) != candidate / 'a4_final_key_lock.json'
            or Path(report['receipt']) != candidate / 'a4_final_key_lock_receipt.json'):
        raise ValueError('the signed-key report names a different candidate')
    ordinary_logical = str(Path(A5.APPROVED_LOCK_PIN).with_name('ordinary_bound.json'))
    aliases = {
        A5.APPROVED_LOCK_PIN: (report['lock'], report['lock_sha256']),
        A5.APPROVED_RECEIPT_PIN: (report['receipt'], report['receipt_sha256']),
        ordinary_logical: (report['ordinary'], report['ordinary_sha256']),
    }
    original_pin, original_read = A5._binding_pin, A5._pinned_file

    def pin(logical):
        return aliases[logical][1] if logical in aliases else original_pin(logical)

    def read(path, expected, what):
        actual = aliases[path][0] if path in aliases else path
        return original_read(actual, expected, what)

    with E.R._using(A5,
                    APPROVED_KEY_DIR=str(candidate), A4_LOCK_DIR=str(candidate),
                    A4_LOCK_PATH=report['lock'], A4_LOCK_SHA=report['lock_sha256'],
                    A4_LOCK_RECEIPT_SHA=report['receipt_sha256'],
                    _binding_pin=pin, _pinned_file=read):
        # The ordinary file is checked here as well as by G's real decoder.
        # Hashing offered files to invent their expected hashes is forbidden.
        A5._pinned_file(ordinary_logical, A5._binding_pin(ordinary_logical),
                        'approved ordinary binding')
        A5.a4_lock()
        try:
            yield report
        finally:
            if E.G._sha_file(str(report_path)) != expected_sha256:
                raise ValueError('the approved signed-key report changed')
