# -*- coding: utf-8 -*-
"""COLD third-round TEST key at the REAL grading consumer.

A separate operation on purpose: this process re-enters every scope from disk,
so nothing is warm from the build. ZERO AI CALLS; the signature and lock it
consumes are explicitly TEST_ONLY and establish no source truth.
"""
import collections, json, os, sys
from pathlib import Path
from unittest.mock import patch

UNIT = Path(__file__).resolve().parent
A7 = UNIT.parent
BUILD = Path(os.environ['A7_THIRD_TEST_BUILD'])
saved = json.loads((BUILD / 'TEST_RESULT.json').read_text())
base = json.loads((Path(saved['base']) / 'TEST_RESULT.json').read_text())
os.environ['A7_APPROVED_KEY_DIR'] = saved['candidate']
os.environ['A7_ORDINARY_BOUND'] = saved['ordinary']
for rel in ('unit_2009/owner', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2061_settlement_connection',
            'unit_2063_source_closeout', 'unit_2065_closeout_connection',
            'unit_2069_targeted_source'):
    sys.path.insert(0, str(A7 / rel))
sys.path.insert(0, str(A7 / 'unit_2076_latest_source_decisions'))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
import a4_source_decision as D2041                                 # noqa: E402
import a4_source_settlement as S2061                               # noqa: E402
import a4_source_closeout as C2065                                 # noqa: E402
import a4_targeted_source as T2069                                 # noqa: E402
import a4_v6_successor_chain as X                                        # noqa: E402
CL, K, SK, F = R.CL, R.K, R.SK, R.F
import a6_launch_freeze as A6                                      # noqa: E402
import a7_prepared_run as PR                                       # noqa: E402
import a7_g1_build as G                                            # noqa: E402

out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
findings = collections.OrderedDict(saved['findings'])
decision_findings = collections.OrderedDict(saved['decision_findings'])
settlement_findings = collections.OrderedDict(saved['settlement_findings'])
closeout_findings = collections.OrderedDict(saved['closeout_findings'])
PREVIOUS = (findings, decision_findings, settlement_findings, closeout_findings)
first_findings = collections.OrderedDict(base['round2_findings'])
round2_findings = collections.OrderedDict(saved['round3_findings'])
first_run, run2 = base['run2'], saved['run3']
CHAIN = ((base['first_run'], base['first_findings']),)
event = saved['event'][0]
cleared_event = saved['cleared'][0]
round2_name = saved['changed'][event]
first_name = saved['first_name'][event]
checks, notes = [], collections.OrderedDict()


def check(name, ok, why=''):
    print('PASS' if ok else 'FAIL', name, str(why)[:240], flush=True)
    checks.append(name)
    assert ok, '%s %s' % (name, why)


def refuses(fn):
    try:
        fn()
    except (ValueError, SystemExit, OSError, KeyError) as exc:
        return '%s: %s' % (type(exc).__name__, exc)
    return None


def scope(bound, run=None, f=None):
    """Re-enter the same real successor connection in this cold process."""
    return X.successor_scope(bound, round2_findings if f is None else f,
                             first_run if run is None else run,
                             first_findings, PREVIOUS, CHAIN)


def names(facts):
    return [(f.get('item') or {}).get('driver_name') for f in facts]


# --------- COLD: the original owners still reconstruct in this process ------
with R.final_scope(saved['review'], saved['review_package'], bind_role=True):
    bound = SK.bound(saved['key_run'], saved['key_package'])
    cold = F.final_prompt(bound, F._task_by_label(bound.evidence, event))
    check('COLD: the original executed prompt owner rebuilds unchanged',
          '[A4 FINAL DECISION TASK]' not in cold
          and '[A7 SOURCE CORRECTION TASK]' not in cold)
    closed = C2065.bind(S2061.bind(D2041.bind(
        C2023.bind(bound, saved['corrections']), saved['decision']),
        saved['settlement']), saved['closeout'])
    b2 = X.bind(closed, run2)
    prior_owner = F._prior_runs
    with scope(b2):
        warm = F.v6_prompt(b2, event)
        origins = F.v6_shards(b2)[2]
    after = F.final_prompt(bound, F._task_by_label(bound.evidence, event))
    check('the successor scope leaves the original owner restored',
          after == cold and '[A7 SOURCE CORRECTION TASK]' in warm)
    check('the scope restores every owner it bound, at all six phases',
          all(getattr(F, n) is v for n, v in X._ORIGINAL.items())
          and F._prior_runs is prior_owner
          and F.v6_shards.__module__ == F.__name__
          and F.v5_prompt.__module__ != C2065.__name__)
    check('COLD: the body still carries the FIRST ROUND\'s reply under its '
          'own name', X.PRIOR_KEY in warm and 'v5_shard' not in warm)
    check('COLD: the merge still reports the TRUE mixed origins',
          collections.Counter(origins.values())
          == collections.Counter(saved['notes']['origins']),
          dict(collections.Counter(origins.values())))
    check('COLD: all three v6 rounds are still on disk with receipt and '
          'finalization',
          all(os.path.isfile(os.path.join(r, n))
              for r in (CHAIN[0][0], first_run, run2)
              for n in (K.RECEIPT_NAME, K.FINALIZATION_NAME)))
    # REAL COLD RESUME: in this fresh process the existing owner re-derives
    # the published round from disk and re-validates the receipt against it.
    with scope(b2):
        stale = F._receipt_still_the_proved_one(run2, b2)
        redone = K._sha(F.v6_prompt(b2, event))
    rec = K._load(os.path.join(run2, K.RECEIPT_NAME))
    check('COLD RESUME: the published successor receipt is still the proved '
          'one and its pinned prompt re-derives byte-identically from disk',
          not stale and rec['prompts'][event] == redone, (stale, redone))
    check('COLD RESUME: this receipt pins both earlier rounds exactly',
          rec['v1_evidence']['v6'] == F._run_evidence_pins(first_run)
          and rec['v1_evidence']['v6_round1']
          == F._run_evidence_pins(CHAIN[0][0]))
    check('COLD RESUME: each round\'s finalization records its own valid call',
          all(K._load(os.path.join(r, K.FINALIZATION_NAME))['ledger']['valid']
              >= 1 for r in (CHAIN[0][0], first_run, run2)))

    # ---- DISCONNECT: the first round supplied to the scope is load-bearing --
    with scope(b2, run=saved['closeout']):
        why = refuses(lambda: F.v6_prompt(b2, event))
    check('DISCONNECT 1: pointing the successor at the superseded closeout '
          'instead of the first round REFUSES rather than serving a stale '
          'prior reply', why is not None, str(why)[:160])
    notes['wrong_first_round_refusal'] = str(why)[:200]
    with scope(b2, run=saved['closeout']):
        why2 = refuses(lambda: F._receipt_still_the_proved_one(run2, b2))
    check('DISCONNECT 2: and the published receipt cannot even be RE-VALIDATED '
          'under the wrong first round - the resume path refuses outright '
          'rather than silently accepting it', why2 is not None,
          str(why2)[:160])
    notes['wrong_first_round_resume_refusal'] = str(why2)[:200]

# -------------------- the consumer over the TEST-locked key ----------------
with R.candidate_scope(saved['review'], saved['review_package'],
                       saved['key_run'], saved['key_package']):
    approved = G._approved_bound()
    check('the consumer binding reader carries ALL FIVE later phases',
          approved.corrections == saved['corrections']
          and approved.decision == saved['decision']
          and approved.decision_correction == saved['settlement']
          and approved.decision_correction_v5 == saved['closeout']
          and approved.decision_correction_v6 == run2)
    with scope(approved):
        key, sidecar = G.gold_by_event()
    by_event = collections.OrderedDict((s, names(f)) for s, f in key.items())
    check('the SUCCESSOR content is what the REAL consumer sees for that '
          'event', round2_name in by_event[event], by_event[event])
    check('the first round\'s name it replaced is NOT at the consumer',
          first_name not in by_event[event])
    check('the event whose correction stood keeps its CORRECTED content',
          saved['corrected'][cleared_event] in by_event[cleared_event])
    check('no successor name leaks into any other event',
          not any(round2_name in by_event[s] for s in by_event if s != event))
    check('both carried ORIGINAL news results are still original',
          collections.Counter(origins.values())['a4_final_v1'] == 31)

    # ---- DISCONNECT MUTATIONS AT EACH AFFECTED HANDOFF -------------------
    real_approved = G._approved_bound

    def drop(**kw):
        return lambda: real_approved()._replace(**kw)

    with patch.object(G, '_approved_bound', drop(decision_correction_v6=None)):
        with scope(approved):
            stale_key, _s = G.gold_by_event()
    stale_names = names(stale_key[event])
    # MEASURED, not assumed: dropping the v6 slot does NOT fall all the way
    # back to the closed key. With no v6 run bound the gate dispatches to
    # `v5_shards`, which under the successor scope IS the first round's
    # completed merge - so the first round's six corrections are still served
    # and only THIS round's two events are silently lost. That is the carry
    # Codex requires, holding even under a dropped successor binding.
    check('DISCONNECT 3: dropping the v6 slot at the consumer read boundary '
          'silently loses ONLY this round - the first round is still served '
          'as the successor\'s merge base, and the positive name assertion is '
          'what detects the loss',
          round2_name not in stale_names and first_name in stale_names,
          stale_names)
    notes['dropped_v6_names'] = stale_names

    with patch.object(G, '_approved_bound',
                      drop(decision_correction=None,
                           decision_correction_v5=None,
                           decision_correction_v6=None)):
        with scope(approved):
            why = refuses(G.gold_by_event)
            stripped = real_approved()._replace(
                decision_correction=None, decision_correction_v5=None,
                decision_correction_v6=None)
            incomplete = F.signing_gate(stripped.events, stripped)
    check('DISCONNECT 4: dropping every correction phase DOES refuse, and the '
          'named mechanism is an INCOMPLETE key rather than a silent swap',
          why is not None and 'signing gate is not clean' in why
          and not incomplete['ok'] and len(incomplete['shards']) < 33,
          (str(why)[:120], len(incomplete['shards'])))
    notes['dropped_all_refusal'] = str(why)[:200]

    # the POSITIVE CONTROL: the previous round still works on its own
    with patch.object(G, '_approved_bound', drop(decision_correction_v6=first_run)):
        with X.first_round_scope(real_approved()._replace(
                decision_correction_v6=first_run), first_run, first_findings,
                                 PREVIOUS, CHAIN):
            ctrl, _c = G.gold_by_event()
    ctrl_names = names(ctrl[event])
    check('POSITIVE CONTROL: bound to the FIRST round under its own scope the '
          'consumer still produces that complete key, unchanged',
          len(ctrl) == len(key) and first_name in ctrl_names
          and round2_name not in ctrl_names, ctrl_names)

    with scope(approved):
        live, identity = G.live_key()
    live_names = [n for facts in live.values() for n in names(facts)]
    check('the successor fact survives into G.live_key, the key every G1 path '
          'reads', round2_name in live_names)
    check('the first round\'s superseded name is nowhere in the live key',
          first_name not in live_names)

    primary, _ = K.a3_run_dirs()
    original_answers = PR._executed(primary)
    frozen = A6.reuse_freeze(primary, os.path.join(CL.SK.PKG_DIR,
                                                   CL.SK.MANIFEST_NAME))
    text = A6.render(frozen)
    pin = K._sha(text)
    CL.RT.write_new(str(out / A6.REUSE_FREEZE_NAME), text)
    run = PR.reuse(str(out), pin)
    with scope(approved):
        arms, meta, problems = G.materialize(run)
    check('the successor TEST key enters the actual saved-answer grading path',
          not problems, str(problems[:2]))
    check('all 36 events, 191 packets and 382 original answers, zero new '
          'producer calls',
          (meta['events'], meta['packets'], meta['answers']) == (36, 191, 382)
          and len(meta['trace']) == 382
          and frozen['budget']['planned_producer_primary'] == 0)
    check('every original answer byte is unchanged',
          PR._executed(primary) == original_answers)
    notes['meta'] = {k: meta[k] for k in ('events', 'packets', 'answers')}

CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind': 'TEST ONLY: a TEST signature and lock; no model call, no real key '
            'approval and no grading', 'model_calls': 0,
    'passed': len(checks), 'checks': checks, 'notes': notes,
    'build': str(BUILD), 'evaluation_sha256': pin, 'identity': run},
    indent=1, default=str))
print('COMPLETE', len(checks), 'checks; zero AI calls;', out)
