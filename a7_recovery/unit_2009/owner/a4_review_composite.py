"""Preserve proved old reviews and complete only their unsatisfied blind slots.

Existing owners still decide prompts, identities, parsing, finalization,
adjudication and signing. This serial adapter binds their historical/current
contexts and carries both real stages into the final key. It calls no model.
"""
import collections
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'unit_2002/owner'))
import a4_source_closure as CL

HR, K, SK, F, RT, INV = CL.HR, CL.K, CL.SK, CL.F, CL.RT, CL.INV
OLD_OWNER_PATH = ROOT / 'unit_1997/harness_g1v3/build_kfields_hard_review.py'
_spec = importlib.util.spec_from_file_location('a7_preserved_hard_review', OLD_OWNER_PATH)
OLD = importlib.util.module_from_spec(_spec)
_path = list(sys.path)
try:
    _spec.loader.exec_module(OLD)
finally:
    sys.path[:] = _path
BASE = Path(CL.PKG_DIR).parent
OLD_RUN, OLD_PKG = str(BASE / 'review_2004'), str(BASE / 'closure_2004')
NEW_RUN, NEW_PKG = str(BASE / 'review_2009'), str(BASE / 'closure_2009')
_FINAL_SCOPE = CL.final_scope


@contextlib.contextmanager
def _using(owner, **values):
    saved = {name: getattr(owner, name) for name in values}
    try:
        for name, value in values.items():
            setattr(owner, name, value)
        yield
    finally:
        for name, value in saved.items():
            setattr(owner, name, value)


@contextlib.contextmanager
def old_scope():
    """Reproduce the old package using its actual original callable owner."""
    with contextlib.ExitStack() as stack:
        for owner in (CL, SK, F):
            stack.enter_context(_using(owner, HR=OLD))
        stack.enter_context(_using(F, _HERE=str(OLD_OWNER_PATH.parent)))
        yield


def _existing(path, text):
    if not os.path.isfile(path) or Path(path).read_bytes() != text.encode('utf-8'):
        raise ValueError('completed evidence is missing or differs: %s' % path)


def _no_raw_write(*args, **kwargs):
    raise ValueError('completed raw evidence is missing; verification cannot recover it')


def _completed(owner, ctx, run, package):
    """Replay the finalizer as an exact comparison, never as a writer.

    Require directories/child receipts before entering, so even its directory
    creation branches cannot write. Missing raw or proved output refuses.
    """
    fin_path = os.path.join(run, K.FINALIZATION_NAME)
    if not os.path.isdir(os.path.join(run, 'raw')) or not os.path.isfile(fin_path):
        raise ValueError('the review attempt is not finalized: %s' % run)
    stored = K._load(fin_path)
    if stored.get('retry') and not os.path.isfile(
            os.path.join(run, 'retry', K.RECEIPT_NAME)):
        raise ValueError('the finalized retry has no receipt: %s' % run)
    with _using(RT, write_new=_existing, save_raw=_no_raw_write):
        got = owner._finalize(ctx, run, package)
    if got.get('primary_complete') is not True or got.get('problems'):
        raise ValueError('the review closeout is not complete: %s' % run)
    return got


def _stage(owner, ctx, run, package):
    """One complete stage through its own package, closeout and reading owners."""
    bad = owner._package_problems(ctx, package)
    if bad:
        raise ValueError('review package refused: %s' % bad)
    evidence = collections.OrderedDict()
    for attempt, base in ((1, run), (owner.MAX_ATTEMPTS, os.path.join(run, 'retry'))):
        receipt = os.path.join(base, K.RECEIPT_NAME)
        if attempt != 1 and not os.path.isfile(receipt):
            continue
        _completed(owner, ctx, base, package)
        evidence[base] = {'receipt_sha256': INV.sha_file(receipt),
                          'finalization_sha256': INV.sha_file(
                              os.path.join(base, K.FINALIZATION_NAME))}
    with _using(CL, _ctx=lambda: ctx):
        readings, bad = CL.readings(run, package)
    if bad:
        raise ValueError('review native evidence refused: %s' % bad)
    return readings, {'package': package, 'run': run,
                      'manifest_sha256': INV.sha_file(os.path.join(package, CL.MANIFEST_NAME)),
                      'evidence': evidence}


def _prior(new_run=None):
    return F.Bound(package=OLD_PKG, evidence=CL.INITIAL_RUN, hr=OLD_RUN,
                   fix=new_run, events=None, hr_package=OLD_PKG)


def old_readings():
    with old_scope():
        return _stage(OLD, CL._ctx(), OLD_RUN, OLD_PKG)


def _context(old, stage):
    ctx = CL._ctx()
    by_label = HR._by_label_of(ctx)
    if list(old) != HR._canonical_of(ctx):
        raise ValueError('the old and current review populations differ')
    slots = [(by_label[label][0]['task_id'], by_label[label][1])
             for label, value in old.items() if value[0] != 'valid']
    # An exhausted invalid reply is not a successful answer and cannot be
    # retried under an unchanged task. The original owner proves exhaustion.
    if slots:
        child = os.path.join(OLD_RUN, 'retry')
        if child not in stage['evidence']:
            raise ValueError('the original invalid-only retry is not complete')
        old_manifest = K._load(os.path.join(OLD_PKG, CL.MANIFEST_NAME))
        prompts = {row['task_id']: row['prompt_sha256'] for row in old_manifest['tasks']}
        for task_id, blind in slots:
            task = by_label[HR.call_label(task_id, blind)][0]
            if prompts[task_id] == K._sha(HR._blind_prompt(ctx, task)):
                raise ValueError('an unresolved slot still has its original prompt: %s' % task_id)
    derived = collections.OrderedDict(ctx['derived_from'])
    derived.update(composite_owner_sha256=INV.sha_file(__file__), preserved_review=stage)
    return dict(ctx, slots=slots, before=F._ledger_before(_prior()), derived_from=derived)


def _ctx():
    return _context(*old_readings())


@contextlib.contextmanager
def _current_scope():
    ctx = _ctx()
    with _using(CL, _ctx=lambda: ctx):
        yield


def build(package=NEW_PKG):
    with _current_scope():
        return CL.build(package)


def prepare_run(run=NEW_RUN, package=NEW_PKG):
    with _current_scope():
        return CL.prepare_run(run, package)


def finalize(run=NEW_RUN, package=NEW_PKG):
    with _current_scope():
        return CL.finalize(run, package)


def blind_prompt(task):
    return HR._blind_prompt(_ctx(), task)


def render_launcher(task, blind, attempt=1):
    return HR._render_launcher(_ctx(), task, blind, attempt)


_initial = CL._initial


def merged_readings(run=NEW_RUN, package=NEW_PKG):
    old, old_stage = old_readings()
    ctx = _context(old, old_stage)
    new, new_stage = _stage(HR, ctx, run, package)
    owed = HR._canonical_of(ctx)
    if list(new) != owed:
        raise ValueError('the clarified readings are not exactly the missing slots')
    merged = collections.OrderedDict((label, value if value[0] == 'valid' else new[label])
                                     for label, value in old.items())
    return merged, collections.OrderedDict(preserved=old_stage, clarified=new_stage)


@contextlib.contextmanager
def final_scope(run=NEW_RUN, package=NEW_PKG, bind_role=False):
    """Enter the real final-key gate with both native-proved review stages."""
    got, stages = merged_readings(run, package)
    before = F._ledger_before(_prior(run))

    def readings(review_run, review_package):
        if (review_run, review_package) != (OLD_RUN, OLD_PKG):
            raise ValueError('the final phase names a different preserved review')
        return got, []

    with _using(CL, readings=readings), _using(F, _ledger_before=lambda bound: before):
        with _FINAL_SCOPE(OLD_RUN, OLD_PKG, bind_role=bind_role) as proof:
            original_manifest, original_owners = SK.manifest, SK._owners

            def manifest():
                doc = original_manifest()
                doc['hard_review']['stages'] = stages
                return doc

            def owners():
                result = original_owners()
                result['review_composite_owner'] = INV.sha_file(__file__)
                result['clarified_review_manifest'] = stages['clarified']['manifest_sha256']
                return result

            with _using(SK, manifest=manifest, _owners=owners):
                yield dict(proof, stages=stages)


@contextlib.contextmanager
def candidate_scope(run, package, key_run, key_package):
    """Extend the existing artifact list, keeping its builder and gates intact."""
    sys.path.insert(0, str(ROOT / 'unit_2005/owner'))
    import a4_source_candidate as SC
    if Path(SC.__file__).resolve() != ROOT / 'unit_2005/owner/a4_source_candidate.py':
        raise ValueError('a different source-key candidate binding is loaded')

    def scope(review_run, review_package, bind_role=False):
        if (review_run, review_package) != (OLD_RUN, OLD_PKG):
            raise ValueError('the candidate names a different preserved review')
        return final_scope(run, package, bind_role=bind_role)

    with _using(CL, final_scope=scope):
        with SC.candidate_scope(OLD_RUN, OLD_PKG, key_run, key_package) as builder:
            original = builder.ordinary_bindings

            def bindings(bound):
                runs, rows = original(bound)
                rows['clarified_review_package'] = collections.OrderedDict(
                    path=os.path.join(package, CL.MANIFEST_NAME),
                    sha256=INV.sha_file(os.path.join(package, CL.MANIFEST_NAME)), run_dir=package)
                for attempt, base in ((1, run), (HR.MAX_ATTEMPTS, os.path.join(run, 'retry'))):
                    if attempt != 1 and not os.path.isfile(os.path.join(base, K.RECEIPT_NAME)):
                        continue
                    runs.append(base)
                    name = 'clarified_review' if attempt == 1 else 'clarified_review_retry'
                    for kind, filename in (('receipt', K.RECEIPT_NAME),
                                            ('finalization', K.FINALIZATION_NAME)):
                        path = os.path.join(base, filename)
                        rows[name + '_' + kind] = collections.OrderedDict(
                            path=path, sha256=INV.sha_file(path), run_dir=base)
                return runs, rows

            with _using(builder, ordinary_bindings=bindings):
                yield builder
