# -*- coding: utf-8 -*-
"""Freeze the REAL final candidate and its UNRUN signer packet. NO AI CALL.

Codex SEQ 2081. Everything comes from the selected packet's own saved record:
the two-predecessor chain, the source-only findings, the phase input binding
and the recovery run. The ordinary binding is DERIVED from the live bound, not
copied from any TEST build. CAND owns compose/build/verify and the signer
accounting; X owns the saved succession; F is untouched. No TEST native
signature is written here and no signer is run.
"""
import collections, hashlib, io, json, os, sys
from pathlib import Path

UNIT = Path(__file__).resolve().parent
A7 = UNIT.parent
PKT = Path(os.environ['A7_REAL_PACKET'])
for rel in ('unit_2009/owner', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2053_owner_retry',
            'unit_2061_settlement_connection', 'unit_2065_closeout_connection',
            'unit_2068_input_recovery', 'unit_2069_targeted_source',
            'unit_2076_latest_source_decisions'):
    sys.path.insert(0, str(A7 / rel))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
import a4_source_decision as D2041                                 # noqa: E402
import a4_source_recovery as RECOV                                 # noqa: E402
import a4_source_settlement as S2061                               # noqa: E402
import a4_source_closeout as C2065                                 # noqa: E402
import a4_phase_input as N                                         # noqa: E402
import a4_v6_successor_chain as X                                  # noqa: E402
F, K, SK, INV = R.F, R.K, R.SK, R.INV
assert Path(X.__file__).resolve() == (
    A7 / 'unit_2076_latest_source_decisions/a4_v6_successor_chain.py'), X.__file__

out = UNIT / os.environ['A7_TAG']
out.mkdir()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks, notes = [], collections.OrderedDict()


def check(name, ok, why=''):
    print('PASS' if ok else 'FAIL', name, str(why)[:300], flush=True)
    checks.append(name)
    assert ok, '%s %s' % (name, why)


def step(n, what):
    print('--- step %s: %s' % (n, what), flush=True)


# ---- everything from the saved record ------------------------------------
rec = K._load(str(PKT / 'FINDINGS_BY_EVENT.json'))
pkt = K._load(str(PKT / 'PACKET.json'))
inputs = [rec[k] for k in ('by_event', 'decision_by_event',
                           'settlement_by_event', 'closeout_by_event')]
history = tuple((r, f) for r, f in rec['chain'])
chain, predecessor = history[:-1], rec['predecessor']
pred_findings, findings = rec['predecessor_by_event'], rec['third_by_event']
run3 = rec['third_round']
phase_path = rec['phase_input_binding']
phase = K._load(phase_path)
carrier = K._load(phase['input_binding'])
key_run, key_package = rec['run'], carrier['package']
review, review_pkg = rec['review_run'], rec['review_package']


@F._operation
def main():
    step(1, 'the real lane, rebuilt from the saved record only')
    with R.final_scope(review, review_pkg, bind_role=True), \
            N.input_scope(phase_path):
        corrected = C2023.bind(SK.bound(key_run, key_package), rec['corrections'])
        closed = C2065.bind(S2061.bind(D2041.bind(corrected, rec['decision']),
                                       rec['settlement']), phase['run'])
        with RECOV.recovery_scope(rec['recovery'], corrected, inputs[0]), \
                C2065.closeout_scope(*inputs):
            b3 = X.bind(closed, run3)

            def scope(b=None):
                return X.successor_scope(b if b is not None else b3, findings,
                                         predecessor, pred_findings, inputs,
                                         chain)

            with scope():
                gate = F.signing_gate(b3.events, b3)
                shards, raws, origins, bad = F.v6_shards(b3)
            check('the ACTUAL signing gate is clean over the real key',
                  gate['ok'] and not bad, (gate.get('stops') or [])[:2])
            check('all 33 source events carry a raw origin', len(origins) == 33
                  and len(shards) == 33 and len(raws) == 33, len(origins))
            notes['origins'] = dict(collections.Counter(origins.values()))
            notes['source_origins'] = dict(origins)
            notes['source_raw_sha256'] = {sid: K._sha(raw) for sid, raw in raws.items()}
            notes['counts'] = {k: gate['counts'][k] for k in sorted(gate['counts'])
                               if isinstance(gate['counts'][k], int)}
            check('the gate reports zero open issues',
                  gate['counts'].get('open_issues') == 0,
                  gate['counts'].get('open_issues'))

            # ---- the ordinary binding, DERIVED from the live bound --------
            step(2, 'the ordinary binding, derived from the live owners')
            ordinary = out / 'ordinary_bound.json'
            R.RT.write_new(str(ordinary), json.dumps(collections.OrderedDict(
                [(f, getattr(b3, f)) for f in
                 ('package', 'evidence', 'hr', 'events', 'hr_package')]
                + [('corrections', b3.corrections), ('decision', b3.decision),
                   ('decision_correction', b3.decision_correction),
                   ('decision_correction_v5', b3.decision_correction_v5),
                   ('decision_correction_v6', b3.decision_correction_v6),
                   ('recovery', rec['recovery'])]),
                indent=1))
            os.environ['A7_ORDINARY_BOUND'] = str(ordinary)
            sys.path.insert(0, str(A7 / 'unit_2005/owner'))
            import build_final_key_candidate as CAND               # noqa: E402
            check('the candidate owner bound THIS run\'s ordinary binding',
                  CAND.ORDINARY == str(ordinary), CAND.ORDINARY)
            check('the derived binding round-trips to the same live bound',
                  CAND._ordinary_bound() == b3,
                  (CAND._ordinary_bound(), b3))
            notes['ordinary'] = str(ordinary)
            notes['ordinary_sha256'] = sha(ordinary)

            # ---- the pre-signer count -------------------------------------
            step(3, 'the pre-signer count through the authoritative owner')
            with scope():
                before = CAND.signer_ledger_before(b3)
            made = sum(X._finalized_scheduled(r) for r, _f in history)
            check('the pre-signer count is exactly 667, every call once',
                  before == 667 and before == 657 + made + 2,
                  (before, made))
            notes['signer_ledger_before'] = before
            notes['calls_by_round'] = {r: X._finalized_scheduled(r)
                                       for r, _f in history}

            # ---- history pins still exact ---------------------------------
            step(4, 'the current receipt, finalization and history pins')
            frozen = K._load(os.path.join(run3, K.RECEIPT_NAME))
            fin = K._load(os.path.join(run3, K.FINALIZATION_NAME))
            check('this round is finalized with exactly two valid calls',
                  fin['ledger'] == {'scheduled': 2, 'valid': 2,
                                    'invalid_response': 0,
                                    'transport_no_answer': 0, 'unproved': 0,
                                    'missing': 0}, json.dumps(fin['ledger']))
            check('the receipt pins BOTH earlier rounds exactly',
                  frozen['v1_evidence']['v6']
                  == F._run_evidence_pins(predecessor)
                  and frozen['v1_evidence']['v6_round1']
                  == F._run_evidence_pins(history[0][0]))
            with scope():
                stale = F._receipt_still_the_proved_one(run3, b3)
            check('the finalized receipt is still the proved one', not stale,
                  stale)
            notes['receipt_sha256'] = sha(os.path.join(run3, K.RECEIPT_NAME))
            notes['finalization_sha256'] = sha(os.path.join(run3,
                                                            K.FINALIZATION_NAME))
            notes['source_findings_sha256'] = pkt['findings_sha256']
            notes['live_source_input'] = INV.sha_file(pkt['findings_path'])
            check('the live source input is the identity the packet froze',
                  notes['live_source_input'] == pkt['findings_sha256'])

    # ---- the real candidate and its UNRUN signer --------------------------
    step(5, 'the REAL candidate through C.build and C.verify')
    candidate = out / 'candidate'
    # ORDER MATTERS AND IS MEASURED (attempt core_cand2081_a): candidate_scope
    # opens its OWN final_scope, which re-stages the OLD review package against
    # the LIVE context. Entering it inside N.input_scope makes that staging see
    # a swapped input and refuse with "the pinned transport is not the live
    # one" plus all 33 tasks. The candidate boundary therefore goes OUTSIDE the
    # phase-input, recovery and succession boundaries, not inside them.
    with R.candidate_scope(review, review_pkg, key_run, key_package) as C:
        with N.input_scope(phase_path):
            corrected = C2023.bind(SK.bound(key_run, key_package),
                                   rec['corrections'])
            closed = C2065.bind(S2061.bind(D2041.bind(corrected, rec['decision']),
                                           rec['settlement']), phase['run'])
            with RECOV.recovery_scope(rec['recovery'], corrected, inputs[0]), \
                    C2065.closeout_scope(*inputs):
                b3 = X.bind(closed, run3)
                with X.successor_scope(b3, findings, predecessor,
                                       pred_findings, inputs, chain):
                    hashes, full_counts, cand_counts, manifest = C.build(
                        str(candidate))
                    problems = C.verify(str(candidate))
                check('C.build and its full verifier accept the ACTUAL final '
                      'key', not problems, str(problems)[:300])
                identity = json.loads((candidate / 'key_identity.json').read_text())
                check('the candidate binds this round\'s receipt and '
                      'finalization and names the run',
                      all(n in identity['bindings'] for n in
                          ('v6_correction_receipt', 'v6_correction_finalization'))
                      and run3 in identity['runs'])
                check('every bound artifact is the exact byte on disk',
                      all(identity['bindings'][n]['sha256']
                          == sha(identity['bindings'][n]['path'])
                          for n in identity['bindings']))
                recovery = RECOV.binding(rec['recovery'])[0]
                recovery_paths = {
                    'recovery_binding': rec['recovery'],
                    'recovery_record': os.path.join(recovery['recovery_run'], RECOV.RECORD_NAME),
                    'recovery_receipt': os.path.join(recovery['recovery_run'], K.RECEIPT_NAME),
                    'recovery_finalization': os.path.join(recovery['recovery_run'], K.FINALIZATION_NAME),
                }
                check('the saved recovery binding and every recovered-stage artifact are carried',
                      recovery['recovery_run'] in identity['runs']
                      and all(identity['bindings'][name]['path'] == path
                              for name, path in recovery_paths.items()), recovery_paths)
                prov = json.loads((candidate / 'provenance.json').read_text())
                check('the candidate carries all 33 TRUE origins',
                      prov['origins'] == notes['source_origins']
                      and set(prov['provenance']['events']) == set(notes['source_raw_sha256'])
                      and all(prov['provenance']['events'][sid]['raw_sha256'] == digest
                              for sid, digest in notes['source_raw_sha256'].items()),
                      len(prov['provenance']['events']))
                notes['candidate_counts'] = cand_counts if isinstance(
                    cand_counts, dict) else str(cand_counts)
                notes['manifest_budget'] = manifest['budget']
                check('the signer manifest counts 667 before it',
                      manifest['budget']['before'] == 667,
                      manifest['budget'])
    step(6, 'the UNRUN signer packet')
    sig = candidate / 'signer'
    prompt = sig / 'signer_prompt.txt'
    script = sig / 'final_sign.attempt1.js'
    check('the signer prompt and script exist and NOTHING was run',
          prompt.is_file() and script.is_file()
          and not (sig / 'scripts').exists()
          and not (sig / K.FINALIZATION_NAME).exists())
    size = script.stat().st_size
    check('the signer script is under the transport limit',
          size < K.TRANSPORT_LIMIT, (size, K.TRANSPORT_LIMIT))
    notes['signer'] = collections.OrderedDict([
        ('prompt_path', str(prompt)), ('prompt_sha256', sha(prompt)),
        ('script_path', str(script)), ('script_sha256', sha(script)),
        ('script_bytes', size), ('transport_limit', K.TRANSPORT_LIMIT),
        ('manifest_sha256', sha(sig / 'signer.manifest.json')),
        ('transport', K._transport_block())])
    notes['candidate'] = str(candidate)
    notes['candidate_files'] = {p.name: sha(p) for p in
                                sorted(candidate.rglob('*')) if p.is_file()}
    notes['cold_resume_command'] = (
        'cd %s/unit_1947/ledger && A7_LANE_INPUT_PROFILES=/tmp/a7_lane_input_profiles.json '
        'A7_SOURCE_PROJECTS=/home/faisal/.claude/projects '
        'A7_REVIEW_OUT=/tmp/a7_real_package_1947 A7_SOURCE_CONTEXT=/tmp/a7_source_context '
        'PYTHONDONTWRITEBYTECODE=1 A7_TAG=<tag> A7_REAL_PACKET=%s '
        'A7_RUN_BINDING=%s/unit_2081_final_key_candidate/<map> '
        'bash ./run_real_1947.sh ../unit_2081_final_key_candidate/<map> '
        '../../unit_2081_final_key_candidate/build_real_candidate_2081.py <tag> 1800'
        % (A7, PKT, A7))
    R.RT.write_new(str(out / 'RESULT.json'), json.dumps(collections.OrderedDict([
        ('kind', 'REAL final candidate and UNRUN signer packet; no AI call, '
                 'no signature, no lock, no source approval'),
        ('model_calls', 0), ('passed', len(checks)), ('checks', checks),
        ('packet', str(PKT)), ('notes', notes)]), indent=1, default=str))
    print(json.dumps({'ordinary': notes['ordinary_sha256'],
                      'signer_before': notes['signer_ledger_before'],
                      'signer_script_bytes': notes['signer']['script_bytes'],
                      'origins': notes['origins']}, indent=1))
    print('COMPLETE', len(checks), 'checks; zero AI calls;', out)


main()
