"""Current source findings at the existing v6 correction seams.

F still owns the body, launcher, population checks, receipts, native proof,
merge, finalization and scoring gates. V owns the already-approved source-only
prefix and historical closeout. This connection supplies only the current
hash-bound findings, never the historical answer-derived findings file.
"""
import contextlib
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2065_closeout_connection'))
import a4_source_closeout as V

R, C, F, K = V.R, V.C2023, V.F, V.K


@contextlib.contextmanager
def correction_scope(bound, findings, previous_findings):
    """Reconstruct the unchanged earlier phases and this one source task."""
    if not findings:
        raise ValueError('the targeted source correction needs explicit findings')
    with V.closeout_scope(*previous_findings):
        original_entries = F.findings_entries

        def entries(package, name):
            if name != F.V6_FINDINGS_NAME:
                return original_entries(package, name)
            if os.path.abspath(package) != os.path.abspath(bound.package):
                raise ValueError('the targeted findings name a different carrier')
            _shards, raws, bad = F.accepted_shards(
                bound.decision_correction_v5, bound, V.PHASE)
            if bad:
                raise ValueError('the current closeout is not proved: %s' % bad[:2])
            result = []
            for sid in findings:
                rows = C.entries_for(findings, sid)
                if sid not in raws or not rows:
                    raise ValueError('a finding has no accepted closeout source: %s' % sid)
                allowed = F._task_by_label(bound.evidence, sid)['rows']
                for row in rows:
                    if (row.get('source_id') != sid
                            or row.get('raw_sha256') != K._sha(raws[sid])
                            or row.get('row') not in allowed):
                        raise ValueError('a finding does not bind the exact source/raw/row: %s' % sid)
                result.append((sid, rows))
            return result

        def prefix(package, keys):
            if os.path.abspath(package) != os.path.abspath(bound.package):
                raise ValueError('the targeted prefix names a different carrier')
            return V.closeout_prefix(bound, keys)

        with R._using(F, findings_entries=entries, v6_prefix=prefix):
            yield
