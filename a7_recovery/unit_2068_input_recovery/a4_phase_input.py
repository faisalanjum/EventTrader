"""Bind a later source-key phase's actual input without changing its history.

C2023 remains the input-carrier builder and validator. This connection adds
only a pinned phase boundary: historical reads use their old carrier/profile;
this phase and its consumers use the new one. F owns the historical run list,
receipts, native proof, accounting and finalization. No model is called.
"""
import contextlib
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
sys.path.insert(0, str(A7 / 'unit_2023_source_correction'))
import a4_review_composite as R
import a4_source_correction as C

F, K, SK, RT, INV = R.F, R.K, R.SK, R.RT, R.INV


@contextlib.contextmanager
def _binding_scope(path):
    """Pin this after-call connection in C's existing immutable carrier."""
    doc = K._load(path)
    paths = {'input_binding', 'previous_input_binding', 'original_run', 'run'}
    if (not isinstance(doc, dict) or set(doc) != paths | {'phase'}
            or any(not isinstance(doc[k], str) or not os.path.isabs(doc[k])
                   for k in paths)):
        raise ValueError('phase-input binding needs four absolute paths and a phase')
    original_read = C._input_binding
    current, _ = original_read(doc['input_binding'])
    previous, _ = original_read(doc['previous_input_binding'])
    receipt_path = os.path.join(doc['original_run'], K.RECEIPT_NAME)
    receipt = K._load(receipt_path)
    if (doc['phase'] not in F.PHASES or receipt.get('phase') != doc['phase']
            or receipt.get('attempt') != 1
            or os.path.realpath(doc['run']) == os.path.realpath(doc['original_run'])
            or current['source_package'] != previous['package']
            or current['source_run'] != previous['source_run']):
        raise ValueError('phase-input recovery does not match its original phase/carrier')
    if os.path.isfile(os.path.join(doc['original_run'], K.FINALIZATION_NAME)):
        raise ValueError('a finalized original run cannot be replaced by this input recovery')
    original_manifest = os.path.join(current['source_package'], SK.MANIFEST_NAME)
    if receipt.get('manifest_sha256') != INV.sha_file(original_manifest):
        raise ValueError('the original receipt does not name the preserved source carrier')
    pins = {name: {'path': value, 'sha256': INV.sha_file(value)}
            for name, value in (('binding', path),
                                ('previous_binding', doc['previous_input_binding']),
                                ('original_receipt', receipt_path))}
    pins['owner_sha256'] = INV.sha_file(__file__)

    def bound_input(value):
        data, existing = original_read(value)
        if value == doc['input_binding']:
            existing['phase_input_recovery'] = pins
        return data, existing

    with R._using(C, _input_binding=bound_input):
        yield doc, current, receipt


def build_input_package(path):
    """The existing builder writes one NEW carrier with the recovery pins."""
    with _binding_scope(path) as (doc, _current, _receipt):
        return C.build_input_package(doc['input_binding'])


@contextlib.contextmanager
def input_scope(path):
    """Reconstruct the persisted binding for preparation and every consumer."""
    with _binding_scope(path) as (doc, current, receipt), \
            C.input_scope(doc['previous_input_binding']), \
            C.input_scope(doc['input_binding']):
        read = F.accepted_shards
        producer_evidence = K.a3_evidence
        old_profile = RT.LANE_INPUT_PROFILES

        def historical_producer():
            # The evaluated answers precede this key phase too. Their one
            # evidence owner must see their original input declaration even
            # when the later key is read by the grading consumer.
            with R._using(RT, LANE_INPUT_PROFILES=old_profile):
                return producer_evidence()

        def historical_read(run, bound, phase='events'):
            # F's existing phase-order owner includes all earlier phases and
            # their retry children; active recovery scopes add their own run.
            if (bound.package == current['package']
                    and run in F._prior_runs(doc['run'], bound, receipt)):
                with R._using(RT, LANE_INPUT_PROFILES=old_profile):
                    return read(run, bound._replace(package=current['source_package']), phase)
            return read(run, bound, phase)

        with R._using(F, accepted_shards=historical_read), \
                R._using(K, a3_evidence=historical_producer), \
                R._using(RT, LANE_INPUT_PROFILES=current['profile']):
            yield
