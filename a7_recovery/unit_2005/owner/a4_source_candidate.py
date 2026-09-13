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
sys.path.insert(0, str(HERE.parents[1] / 'unit_2053_owner_retry'))
import a4_source_recovery as RECOV
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
        stages = [('initial_source', CL.INITIAL_RUN),
                  ('hard_review', review_run), ('event', key_run)]
        # THE CORRECTION PHASE IS A REAL STAGE of this key when the run serves
        # one: the key is materialized over its accepted shards, so its receipt
        # and finalization belong in this identity exactly as the event phase's
        # do, and its allowed retry is picked up by the same loop below
        # (Codex SEQ 2025 item 3). No correction run leaves this unchanged.
        if bound.corrections:
            stages.append(('correction', bound.corrections))
        # THE DECISION PHASE IS A REAL STAGE for the same reason: the key is
        # materialized over its accepted shards, so its receipt and
        # finalization belong in this identity exactly as the correction
        # phase's do (Codex SEQ 2039 item 3).
        if bound.decision:
            stages.append(('decision', bound.decision))
        # THE SETTLEMENT PHASE IS A REAL STAGE for the same reason, one phase
        # later: the key is materialized over its accepted shards, so its
        # receipt and finalization belong in this identity exactly as the
        # decision phase's do (Codex SEQ 2060 item 2). Absent stays absent, so
        # an unsettled candidate is byte-identical.
        if bound.decision_correction:
            stages.append(('settlement', bound.decision_correction))
        # THE CLOSEOUT PHASE IS A REAL STAGE for the same reason, one phase
        # later again: the key is materialized over its accepted shards, so
        # its receipt and finalization belong in this identity exactly as the
        # settlement phase's do (Codex SEQ 2064 item 4). Absent stays absent,
        # so an unclosed candidate is byte-identical.
        if bound.decision_correction_v5:
            stages.append(('closeout', bound.decision_correction_v5))
        # THE V6 CORRECTION IS A REAL STAGE for the same reason, one phase
        # later again: the key is materialized over its accepted shards, so
        # its receipt and finalization belong in this identity exactly as the
        # closeout phase's do (Codex SEQ 2069). Absent stays absent, so a
        # candidate with no v6 correction is byte-identical.
        if bound.decision_correction_v6:
            stages.append(('v6_correction', bound.decision_correction_v6))
        # THE RECOVERY RUN IS A REAL STAGE for the same reason the correction
        # and decision phases are: the key is materialized over its accepted
        # shard too. It rides on the ordinary binding this candidate was
        # handed, so an approval that names one cannot be read as one that
        # does not, and its own authorizing record is pinned beside its
        # receipt and finalization (Codex SEQ 2055 item 1). Absent stays
        # absent, so a candidate with no recovery is byte-identical.
        held = None
        if C.ORDINARY:
            declared = (CL.K._load(C.ORDINARY) or {}).get('recovery')
            if declared:
                held = RECOV.binding(declared)[0]
                stages.append(('recovery', held['recovery_run']))
        for stage, primary in stages:
            for attempt, run in ((1, primary), (2, os.path.join(primary, 'retry'))):
                # A retry is a STAGE only once it is finalized. A published but
                # unfinalized child has a receipt and no finalization, and
                # hashing the absent file raised FileNotFoundError instead of
                # letting the signing gate give its own refusal (measured,
                # attempt core_sbx_b). The gate still owns that refusal.
                if attempt == 2 and not all(
                        os.path.isfile(os.path.join(run, name)) for name in
                        (CL.K.RECEIPT_NAME, CL.K.FINALIZATION_NAME)):
                    continue
                runs.append(run)
                name = stage if attempt == 1 else stage + '_retry'
                rows.extend((name + '_' + kind, os.path.join(run, filename), run)
                            for kind, filename in (('receipt', CL.K.RECEIPT_NAME),
                                                   ('finalization', CL.K.FINALIZATION_NAME)))
        if held:
            rows.append(('recovery_binding', declared, held['recovery_run']))
            rows.append(('recovery_record',
                         os.path.join(held['recovery_run'], RECOV.RECORD_NAME),
                         held['recovery_run']))
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
