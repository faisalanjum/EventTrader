"""Verify and prepare the two-source SUCCESSOR round; no model call, no approval.

The real no-call packet for Codex SEQ 2072: the second round of the existing
`decision_correction_v6` phase over the two whole-event decisions the first
round left unsettled, carrying its other four corrections untouched.
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
import a4_v6_successor as X
import build_final_key_candidate as CAND

F, K, SK = R.F, R.K, R.SK
previous_packet = A7 / 'unit_2069_targeted_source/packet_codex_tarpkt2069_b'
saved = K._load(str(previous_packet / 'FINDINGS_BY_EVENT.json'))
inputs = [saved[k] for k in ('by_event', 'decision_by_event',
                             'settlement_by_event', 'closeout_by_event')]
first_run = saved['targeted']
first_findings = saved['targeted_by_event']
phase_path = saved['phase_input_binding']
phase = K._load(phase_path)
carrier = K._load(phase['input_binding'])
finding_path = A7 / 'unit_2020_codex_check/SOURCE_FINDINGS_2072.json'
findings = K._load(str(finding_path))['findings']
out = UNIT / ('packet_' + os.environ['A7_TAG'])
out.mkdir()
connected = os.environ.get('A7_SUCC_CONNECT') == '1'
checks = []


def check(name, ok, detail=None):
    print('PASS' if ok else 'FAIL', name, str(detail)[:500], flush=True)
    assert ok, (name, detail)
    checks.append(name)


def dependencies():
    """Every module really loaded from a tracked tree, and its hash.

    DERIVED from sys.modules after the packet is built, never a hand-written
    helper list: a module this run actually imported cannot be left off. The
    DATA inputs are pinned by the boundary map, which is hashed alongside.
    """
    roots = (os.path.realpath(str(A7.parent)), '/tmp/claude-1000')
    out = {}
    for _name, mod in sorted(sys.modules.items()):
        path = getattr(mod, '__file__', None)
        if not path or not str(path).endswith('.py'):
            continue
        real = os.path.realpath(path)
        if os.path.isfile(real) and any(real.startswith(r) for r in roots):
            out[real] = R.INV.sha_file(real)
    return out


def rejects(fn):
    try:
        fn()
    except (ValueError, OSError, KeyError) as exc:
        return str(exc)
    return None


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
            # what must NOT move: the 31 closeout scripts, the closeout
            # receipt, and every byte of the completed first v6 round.
            old_v5 = {sid: K._sha(F.render_v5_launcher(closed, sid))
                      for sid in F.v5_labels(closed)}
            old_v5_receipt = R.INV.sha_file(os.path.join(phase['run'],
                                                         K.RECEIPT_NAME))
            fb = X.first_bound(closed, first_run)
            with X.first_round_scope(closed, first_run, first_findings, inputs):
                old_v6 = {sid: K._sha(F.render_v6_launcher(fb, sid))
                          for sid in F.v6_labels(fb)}
                old_v6_receipt = R.INV.sha_file(os.path.join(first_run,
                                                             K.RECEIPT_NAME))
                first_ledger_before = F.v6_ledger_before(fb)
            first_calls = X._finalized_scheduled(first_run)
            # OUTSIDE the successor scope on purpose: here the authoritative
            # owner reads F's OWN unbound chain and adds the first round once.
            authoritative = CAND.signer_ledger_before(fb)
            check('the completed first v6 round reads cleanly and really made '
                  'its own calls',
                  len(old_v6) == 6 and first_calls == 6, (len(old_v6),
                                                          first_calls))

            connection = (X.successor_scope(closed, findings, first_run,
                                            first_findings, inputs)
                          if connected else contextlib.nullcontext())
            with connection:
                labels = F.v6_labels(closed)
                check('the existing v6 owner selects exactly the two reviewed '
                      'sources', labels == list(findings) and len(labels) == 2,
                      labels)
                check('the primary ceiling is exactly the two affected events',
                      len(F.v6_scripts(closed)) == 2)
                before = F.v6_ledger_before(closed)
                check('the pre-call ledger counts every previous call exactly '
                      'once, the first round included, and agrees with the '
                      'authoritative owner',
                      before == first_ledger_before + first_calls
                      and before == authoritative,
                      (first_ledger_before, first_calls, before, authoritative))
                check('COUNTER MUTATION: asking the authoritative owner with '
                      'the FIRST round\'s binding from INSIDE this scope adds '
                      'that round twice - the signer must be asked with THIS '
                      'round\'s binding',
                      CAND.signer_ledger_before(fb) == before + first_calls,
                      (before, first_calls, CAND.signer_ledger_before(fb)))
                prepared = F.prepare_v6(str(out / 'v6r2'), closed)
                check('the existing preparer freezes two requests before any '
                      'launch',
                      prepared['ok'] and len(prepared['invocations']) == 2,
                      prepared.get('problems'))
                frozen = K._load(str(out / 'v6r2' / K.RECEIPT_NAME))
                check('the receipt PINS the completed first round as history, '
                      'which F cannot do for itself',
                      frozen['v1_evidence']['v6']
                      == F._run_evidence_pins(first_run))
                measured = []
                for inv in prepared['invocations']:
                    sid = inv['label']
                    prompt = F.v6_prompt(closed, sid)
                    body = json.loads(prompt.split('[INPUT]\n', 1)[1])
                    script = F.render_v6_launcher(closed, sid)
                    assert C.declared_keys(prompt) == list(body), sid
                    assert 'v5_shard' not in prompt, sid
                    assert body['reviewer_finding']['finding'] == findings[sid], sid
                    assert body[X.PRIOR_KEY]['origin'] == X.PRIOR_ORIGIN, sid
                    assert body[X.PRIOR_KEY]['sha256'] == findings[sid][0]['raw_sha256'], sid
                    assert K._sha(body[X.PRIOR_KEY]['raw']) == body[X.PRIOR_KEY]['sha256'], sid
                    assert Path(inv['scriptPath']).read_text() == script, sid
                    assert frozen['prompts'][sid] == K._sha(prompt), sid
                    assert len(script.encode()) < K.TRANSPORT_LIMIT, sid
                    measured.append(dict(source_id=sid,
                                         prompt_sha256=K._sha(prompt),
                                         prior_raw_sha256=body[X.PRIOR_KEY]['sha256'],
                                         script_path=inv['scriptPath'],
                                         script_sha256=K._sha(script),
                                         script_bytes=len(script.encode())))
                check('both exact source/raw/row findings reach the real body '
                      'and script, bound to the FIRST ROUND\'s reply', True)
                check('the real receipt is still uncalled and unfinalized',
                      not frozen['states']
                      and not (out / 'v6r2' / K.FINALIZATION_NAME).exists())
                budget = F.v6_budget(closed)
                carried = [s for s in first_findings if s not in findings]
                base_shards, base_raws, base_origins, base_bad = F.v5_shards(closed)
                check('the merge base is the first round\'s completed key: '
                      'all six of its corrections stand, four of them carried '
                      'untouched into this round',
                      not base_bad and len(base_shards) == 33
                      and len(carried) == 4
                      and all(base_origins[s] == X.ORIGIN
                              for s in first_findings), base_bad)
            check('all 31 closeout scripts and the closeout receipt are '
                  'unchanged',
                  old_v5 == {sid: K._sha(F.render_v5_launcher(closed, sid))
                             for sid in F.v5_labels(closed)}
                  and old_v5_receipt == R.INV.sha_file(
                      os.path.join(phase['run'], K.RECEIPT_NAME)))
            with X.first_round_scope(closed, first_run, first_findings, inputs):
                check('all six first-round scripts and its receipt are '
                      'unchanged, and its receipt is still the proved one',
                      old_v6 == {sid: K._sha(F.render_v6_launcher(fb, sid))
                                 for sid in F.v6_labels(fb)}
                      and old_v6_receipt == R.INV.sha_file(
                          os.path.join(first_run, K.RECEIPT_NAME))
                      and not F._receipt_still_the_proved_one(first_run, fb))
            if connected:
                for field, value in (('raw_sha256', '0' * 64),
                                     ('source_id', 'not-this-source'),
                                     ('row', 'not-this-row')):
                    changed = copy.deepcopy(findings)
                    changed[next(iter(changed))][0][field] = value
                    with X.successor_scope(closed, changed, first_run,
                                           first_findings, inputs):
                        why = rejects(lambda: F.v6_scripts(closed))
                    check('wrong finding identity refuses: ' + field,
                          why is not None, why)
                with V.closeout_scope(*inputs):
                    _s, closeout_raws, cbad = F.accepted_shards(
                        phase['run'], closed, V.PHASE)
                assert not cbad, cbad
                stale = copy.deepcopy(findings)
                sid0 = next(iter(stale))
                stale[sid0][0]['raw_sha256'] = K._sha(closeout_raws[sid0])
                with X.successor_scope(closed, stale, first_run,
                                       first_findings, inputs):
                    why = rejects(lambda: F.v6_scripts(closed))
                check('a finding bound to the SUPERSEDED closeout reply '
                      'refuses', why is not None, why)
                reversed_findings = dict(reversed(list(findings.items())))
                with X.successor_scope(closed, reversed_findings, first_run,
                                       first_findings, inputs):
                    why = rejects(lambda: F.v6_labels(closed))
                check('a changed population order refuses at the existing '
                      'owner', why is not None, why)
                with X.successor_scope(closed, findings, phase['run'],
                                       first_findings, inputs):
                    why = rejects(lambda: F.v6_scripts(closed))
                check('pointing the successor at the superseded closeout '
                      'instead of the first round refuses', why is not None,
                      why)
                with X.successor_scope(closed, findings, str(out / 'v6r2'),
                                       first_findings, inputs):
                    why = rejects(lambda: F.v6_scripts(closed))
                check('pointing the successor at ITSELF refuses rather than '
                      'building a round on its own unanswered receipt',
                      why is not None, why)
                record = dict(saved, first_round=first_run,
                              first_round_by_event=first_findings,
                              successor_by_event=findings,
                              successor=str(out / 'v6r2'))
                K.RT.write_new(str(out / 'FINDINGS_BY_EVENT.json'),
                               json.dumps(record, indent=1))
                result = dict(
                    kind='verified no-call preparation of the SECOND round of '
                         'decision_correction_v6; source truth still '
                         'unapproved',
                    phase=X.PHASE, round=2, first_round=first_run,
                    first_round_calls=first_calls,
                    ledger_before=before, events=measured,
                    carried_unchanged=carried,
                    findings_path=str(finding_path),
                    findings_sha256=R.INV.sha_file(str(finding_path)),
                    phase_input_binding=phase_path,
                    successor_owner_sha256=R.INV.sha_file(
                        os.path.abspath(X.__file__)),
                    receipt_sha256=R.INV.sha_file(
                        str(out / 'v6r2' / K.RECEIPT_NAME)),
                    transport=K._transport_block(), budget=budget,
                    boundary_map=os.environ.get('A7_RUN_BINDING'),
                    boundary_map_sha256=R.INV.sha_file(
                        os.environ['A7_RUN_BINDING']),
                    first_round_receipt_sha256=R.INV.sha_file(
                        os.path.join(first_run, K.RECEIPT_NAME)),
                    first_round_finalization_sha256=R.INV.sha_file(
                        os.path.join(first_run, K.FINALIZATION_NAME)),
                    previous_packet=str(previous_packet),
                    dependencies=dependencies(),
                    checks=checks, model_calls=0)
                K.RT.write_new(str(out / 'PACKET.json'),
                               json.dumps(result, indent=1))
                print(json.dumps(result, indent=1))
    print('COMPLETE', len(checks), 'checks; model calls 0', flush=True)


main()
