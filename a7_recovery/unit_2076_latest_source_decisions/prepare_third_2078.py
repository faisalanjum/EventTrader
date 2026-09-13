"""Verify and prepare the THIRD round over the same two events. No model call.

Codex SEQ 2078. The predecessor is the completed SECOND round; the round
before it is carried as a SAVED CHAIN taken from the previous packet's own
record, not from a new Bound field. The rehomed owner
`unit_2076_latest_source_decisions/a4_v6_successor_chain.py` is the one used;
the frozen module at the called packet's pinned path is never imported.
"""
import contextlib
import copy
import json
import os
import sys
from pathlib import Path

UNIT = Path(__file__).resolve().parent
A7 = UNIT.parent
for rel in ('unit_2009/owner', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2053_owner_retry',
            'unit_2061_settlement_connection', 'unit_2065_closeout_connection',
            'unit_2068_input_recovery', 'unit_2069_targeted_source',
            'unit_2005/owner'):
    sys.path.insert(0, str(A7 / rel))
sys.path.insert(0, str(UNIT))
import a4_review_composite as R
import a4_source_correction as C
import a4_source_decision as D
import a4_source_recovery as RECOV
import a4_source_settlement as S
import a4_source_closeout as V
import a4_phase_input as N
import a4_targeted_source as T
import a4_v6_successor_chain as X
import build_final_key_candidate as CAND

assert Path(X.__file__).resolve() == UNIT / 'a4_v6_successor_chain.py', X.__file__
F, K, SK = R.F, R.K, R.SK

PKT2 = A7 / 'unit_2072_two_event_closeout/packet_codex_succpkt2073_b'
saved = K._load(str(PKT2 / 'FINDINGS_BY_EVENT.json'))
inputs = [saved[k] for k in ('by_event', 'decision_by_event',
                             'settlement_by_event', 'closeout_by_event')]
RUN1, FIND1 = saved['first_round'], saved['first_round_by_event']
RUN2, FIND2 = saved['successor'], saved['successor_by_event']
CHAIN = ((RUN1, FIND1),)
phase_path = saved['phase_input_binding']
phase = K._load(phase_path)
carrier = K._load(phase['input_binding'])
finding_path = A7 / 'unit_2020_codex_check/SOURCE_FINDINGS_2076_v2.json'
findings = K._load(str(finding_path))['findings']
out = UNIT / ('packet_' + os.environ['A7_TAG'])
out.mkdir()
connected = os.environ.get('A7_THIRD_CONNECT') == '1'
checks = []


def check(name, ok, detail=None):
    print('PASS' if ok else 'FAIL', name, str(detail)[:400], flush=True)
    assert ok, (name, detail)
    checks.append(name)


def rejects(fn):
    try:
        fn()
    except (ValueError, OSError, KeyError) as exc:
        return str(exc)
    return None


def dependencies():
    """Every module really loaded from a tracked tree, and its hash. DERIVED
    from sys.modules after the packet is built, never a hand-written list."""
    roots = (os.path.realpath(str(A7.parent)), '/tmp/claude-1000')
    got = {}
    for _n, mod in sorted(sys.modules.items()):
        path = getattr(mod, '__file__', None)
        if not path or not str(path).endswith('.py'):
            continue
        real = os.path.realpath(path)
        if os.path.isfile(real) and any(real.startswith(r) for r in roots):
            got[real] = R.INV.sha_file(real)
    return got


@F._operation
def main():
    with R.final_scope(saved['review_run'], saved['review_package'],
                       bind_role=True), N.input_scope(phase_path):
        corrected = C.bind(SK.bound(saved['run'], carrier['package']),
                           saved['corrections'])
        closed = V.bind(S.bind(D.bind(corrected, saved['decision']),
                               saved['settlement']), phase['run'])
        with RECOV.recovery_scope(saved['recovery'], corrected, inputs[0]), \
                V.closeout_scope(*inputs):
            # what must not move: both completed rounds and the closeout
            old = {}
            with X.first_round_scope(closed, RUN1, FIND1, inputs):
                fb1 = X.first_bound(closed, RUN1)
                old['r1'] = {s: K._sha(F.render_v6_launcher(fb1, s))
                             for s in F.v6_labels(fb1)}
            with X.first_round_scope(closed, RUN2, FIND2, inputs, CHAIN):
                fb2 = X.first_bound(closed, RUN2)
                old['r2'] = {s: K._sha(F.render_v6_launcher(fb2, s))
                             for s in F.v6_labels(fb2)}
                before_chain = F.v6_ledger_before(fb2)
            calls = {r: X._finalized_scheduled(r) for r in (RUN1, RUN2)}
            check('both completed rounds read cleanly and made their own calls',
                  len(old['r1']) == 6 and len(old['r2']) == 2
                  and calls[RUN1] == 6 and calls[RUN2] == 2, (len(old['r1']), calls))

            conn = (X.successor_scope(closed, findings, RUN2, FIND2, inputs, CHAIN)
                    if connected else contextlib.nullcontext())
            with conn:
                labels = F.v6_labels(closed)
                check('the existing owner selects exactly the two reviewed sources',
                      labels == list(findings) and len(labels) == 2, labels)
                before = F.v6_ledger_before(closed)
                check('ledger_before counts every previous call once at 665',
                      before == before_chain + calls[RUN2]
                      and before == 657 + calls[RUN1] + calls[RUN2],
                      (before_chain, calls, before))
                prepared = F.prepare_v6(str(out / 'v6r3'), closed)
                check('the existing preparer freezes two requests before any launch',
                      prepared['ok'] and len(prepared['invocations']) == 2,
                      prepared.get('problems'))
                frozen = K._load(str(out / 'v6r3' / K.RECEIPT_NAME))
                check('the receipt pins BOTH completed rounds as history',
                      frozen['v1_evidence']['v6'] == F._run_evidence_pins(RUN2)
                      and frozen['v1_evidence']['v6_round1']
                      == F._run_evidence_pins(RUN1))
                measured = []
                for inv in prepared['invocations']:
                    sid = inv['label']
                    prompt = F.v6_prompt(closed, sid)
                    body = json.loads(prompt.split('[INPUT]\n', 1)[1])
                    script = F.render_v6_launcher(closed, sid)
                    assert C.declared_keys(prompt) == list(body), sid
                    assert 'v5_shard' not in prompt, sid
                    assert body['reviewer_finding']['finding'] == findings[sid], sid
                    assert body[X.PRIOR_KEY]['sha256'] == findings[sid][0]['raw_sha256'], sid
                    assert K._sha(body[X.PRIOR_KEY]['raw']) == body[X.PRIOR_KEY]['sha256'], sid
                    assert Path(inv['scriptPath']).read_text() == script, sid
                    assert frozen['prompts'][sid] == K._sha(prompt), sid
                    assert len(script.encode()) < K.TRANSPORT_LIMIT, sid
                    measured.append(dict(source_id=sid, prompt_sha256=K._sha(prompt),
                                         prior_raw_sha256=body[X.PRIOR_KEY]['sha256'],
                                         findings_rows=len(findings[sid]),
                                         script_path=inv['scriptPath'],
                                         script_sha256=K._sha(script),
                                         script_bytes=len(script.encode())))
                check('both bodies carry the LATEST raws and this round\'s findings',
                      True)
                check('the real receipt is uncalled and unfinalized',
                      not frozen['states']
                      and not (out / 'v6r3' / K.FINALIZATION_NAME).exists())
                budget = F.v6_budget(closed)
                base = F.v5_shards(closed)
                check('the merge base carries BOTH completed rounds, 33 events',
                      not base[3] and len(base[0]) == 33
                      and sum(1 for v in base[2].values() if v == X.ORIGIN) == 6,
                      base[3])
                prior_dirs = F._prior_runs(str(out / 'v6r3'), closed,
                                           {'phase': X.PHASE})
                check('both earlier rounds are in the protected identity set',
                      RUN1 in prior_dirs and RUN2 in prior_dirs)
            # nothing earlier moved
            with X.first_round_scope(closed, RUN1, FIND1, inputs):
                check('round one scripts and receipt unchanged, still proved',
                      old['r1'] == {s: K._sha(F.render_v6_launcher(fb1, s))
                                    for s in F.v6_labels(fb1)}
                      and not F._receipt_still_the_proved_one(RUN1, fb1))
            with X.first_round_scope(closed, RUN2, FIND2, inputs, CHAIN):
                check('round two scripts and receipt unchanged, still proved',
                      old['r2'] == {s: K._sha(F.render_v6_launcher(fb2, s))
                                    for s in F.v6_labels(fb2)}
                      and not F._receipt_still_the_proved_one(RUN2, fb2))
            if connected:
                for field, value in (('raw_sha256', '0' * 64),
                                     ('source_id', 'not-this-source'),
                                     ('row', 'not-this-row')):
                    changed = copy.deepcopy(findings)
                    changed[next(iter(changed))][0][field] = value
                    with X.successor_scope(closed, changed, RUN2, FIND2, inputs, CHAIN):
                        why = rejects(lambda: F.v6_scripts(closed))
                    check('wrong finding identity refuses: ' + field, why is not None, why)
                stale = copy.deepcopy(findings)
                sid0 = next(iter(stale))
                with X.first_round_scope(closed, RUN1, FIND1, inputs):
                    _s, r1raws = F.accepted_shards(RUN1, fb1, X.PHASE)[:2]
                stale[sid0][0]['raw_sha256'] = K._sha(r1raws[sid0])
                with X.successor_scope(closed, stale, RUN2, FIND2, inputs, CHAIN):
                    why = rejects(lambda: F.v6_scripts(closed))
                check('a finding bound to the SUPERSEDED round-one reply refuses',
                      why is not None, why)
                with X.successor_scope(closed, findings, RUN2, FIND2, inputs, ()):
                    why = rejects(lambda: F.v6_scripts(closed))
                check('dropping the saved chain refuses rather than mis-reading '
                      'the predecessor', why is not None, why)
                with X.successor_scope(closed, findings, RUN1, FIND1, inputs, ()):
                    why = rejects(lambda: F.v6_labels(closed))
                check('pointing the round at the SUPERSEDED first round refuses',
                      why is not None, why)
                record = dict(saved, third_round=str(out / 'v6r3'),
                              third_by_event=findings,
                              chain=[[RUN1, FIND1], [RUN2, FIND2]],
                              predecessor=RUN2, predecessor_by_event=FIND2)
                K.RT.write_new(str(out / 'FINDINGS_BY_EVENT.json'),
                               json.dumps(record, indent=1))
                result = dict(
                    kind='verified no-call preparation of the THIRD round of '
                         'decision_correction_v6; source truth still unapproved',
                    phase=X.PHASE, round=3, predecessor=RUN2,
                    chain=[RUN1, RUN2], calls_by_round={RUN1: calls[RUN1],
                                                        RUN2: calls[RUN2]},
                    ledger_before=before, proposed_primaries=len(measured),
                    ledger_after_proposed=before + len(measured),
                    ledger_after_proposed_signer=before + len(measured) + 1,
                    events=measured, findings_path=str(finding_path),
                    findings_sha256=R.INV.sha_file(str(finding_path)),
                    phase_input_binding=phase_path,
                    chain_owner=str(Path(X.__file__).resolve()),
                    chain_owner_sha256=R.INV.sha_file(str(Path(X.__file__).resolve())),
                    receipt_sha256=R.INV.sha_file(str(out / 'v6r3' / K.RECEIPT_NAME)),
                    boundary_map=os.environ.get('A7_RUN_BINDING'),
                    boundary_map_sha256=R.INV.sha_file(os.environ['A7_RUN_BINDING']),
                    transport=K._transport_block(), budget=budget,
                    dependencies=dependencies(), checks=checks, model_calls=0)
                K.RT.write_new(str(out / 'PACKET.json'), json.dumps(result, indent=1))
                print(json.dumps({k: result[k] for k in
                                  ('ledger_before', 'proposed_primaries',
                                   'ledger_after_proposed',
                                   'ledger_after_proposed_signer', 'round',
                                   'model_calls')}, indent=1))
    print('COMPLETE', len(checks), 'checks; model calls 0', flush=True)


main()
