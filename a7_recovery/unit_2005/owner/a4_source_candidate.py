"""Source-only stage bindings for the existing final-key artifact builder.

No key is interpreted here. The verified closure scope owns the full evidence,
population, role and signing gate. The candidate owner still builds, signs and
checks its artifacts. Only its obsolete phase-one artifact list is supplied
from the real source-only stages for the duration of one serial operation.
"""
import collections
import contextlib
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'unit_2002/owner'))
import a4_source_closure as CL
sys.path.insert(0, str(HERE))
import build_final_key_candidate as C
if Path(C.__file__).resolve() != HERE / 'build_final_key_candidate.py':
    raise RuntimeError('a different final-key candidate owner is already loaded')


@contextlib.contextmanager
def candidate_scope(review_run, review_package, key_run, key_package):
    """Use the complete proved key and its ACTUAL stages, never a fake phase one."""
    expected = CL.SK.bound(key_run, key_package)
    fields = ('package', 'evidence', 'hr', 'events', 'hr_package')

    def bindings(bound):
        if any(getattr(bound, f) != getattr(expected, f) for f in fields):
            raise ValueError('the ordinary binding is not this exact source-only key')
        rows = [
            ('final_package', os.path.join(key_package, CL.SK.MANIFEST_NAME), key_package),
            ('initial_source_package', os.path.join(CL.SK.PKG_DIR, CL.SK.MANIFEST_NAME), CL.SK.PKG_DIR),
            ('hard_review_package', os.path.join(review_package, CL.MANIFEST_NAME), review_package),
        ]
        runs = []
        for stage, primary in (('initial_source', CL.INITIAL_RUN),
                               ('hard_review', review_run), ('event', key_run)):
            for attempt, run in ((1, primary), (2, os.path.join(primary, 'retry'))):
                if attempt == 2 and not os.path.isfile(os.path.join(run, CL.K.RECEIPT_NAME)):
                    continue
                runs.append(run)
                name = stage if attempt == 1 else stage + '_retry'
                rows.extend((name + '_' + kind, os.path.join(run, filename), run)
                            for kind, filename in (('receipt', CL.K.RECEIPT_NAME),
                                                   ('finalization', CL.K.FINALIZATION_NAME)))
        return runs, collections.OrderedDict(
            (name, collections.OrderedDict(path=path, sha256=CL.INV.sha_file(path), run_dir=run))
            for name, path, run in rows)

    with CL.final_scope(review_run, review_package, bind_role=True):
        saved = C.ordinary_bindings
        C.ordinary_bindings = bindings
        try:
            if not C.ORDINARY:
                raise ValueError('the source-only candidate requires its ordinary binding')
            bindings(C._ordinary_bound())
            yield C
        finally:
            C.ordinary_bindings = saved
