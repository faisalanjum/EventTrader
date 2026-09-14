"""Audit the two real source-review results; never launch or alter a call.

Native evidence uses the existing owner. Collision controls add each actually
observed identity to the prior-spent set in memory, never to a transcript.
This proves collection/identity handling, not the source owner's meaning.
"""
import collections
import importlib.util
import json
import os
from importlib.machinery import SourceFileLoader
from pathlib import Path

import prepare_g23_partial_2097 as E

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
spec = importlib.util.spec_from_file_location(
    'current_key_candidate_2124', candidate,
    loader=SourceFileLoader('current_key_candidate_2124', candidate))
E.X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E.X)

RUN = E.A7 / 'unit_2123_post_signature_key/core_recheck2123_h/recheck_packet'
BINDINGS = E.A7 / 'unit_2020_codex_check/SOURCE_KEY_RECHECK_BINDINGS_2120.json'


def prove(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    assert G._sha_file(str(BINDINGS)) == 'a97d16ba0895f6170e3f4ac5358152d7e4c987057b9c2bdf09c153513b964bb0'
    receipt_path = str(RUN / K.RECEIPT_NAME)
    final_path = str(RUN / K.FINALIZATION_NAME)
    before_files = {str(p): G._sha_file(str(p)) for p in RUN.rglob('*') if p.is_file()}
    assert G._sha_file(receipt_path) == '472a4b7f6905bf68084ff253fb3de3870afed446fd78288633052ebcd634a80d'
    assert G._sha_file(final_path) == 'c8e2bd22d380ed138997d0d3df1d7842cfdffda078b6f888989370f94399f87e'
    receipt, final = K._load(receipt_path), K._load(final_path)
    bound = G._approved_bound()
    before_shards, before_raws, before_origins, bad = F.v6_shards(bound)
    assert not bad, bad
    request = G._read(str(BINDINGS))
    order = [t['source_id'] for t in F.event_tasks(bound.evidence)]
    findings = collections.OrderedDict()
    for event in sorted(request['source_events'], key=lambda x: order.index(x['source_id'])):
        sid = event['source_id']
        assert K._sha(before_raws[sid]) == event['prior_source_raw_sha256']
        assert before_origins[sid] == event['prior_key_origin']
        task = F._task_by_label(bound.evidence, sid)
        assert list(task['rows']) == event['original_task_ids']
        findings[sid] = [collections.OrderedDict([
            ('source_id', sid), ('raw_sha256', K._sha(before_raws[sid])),
            ('row', row)]) for row in task['rows']]
    assert set(receipt['allowed']) == set(findings)
    assert len(receipt['states']) == len(findings) == 2
    next_bound = X.bind(bound, str(RUN))
    identities, negative_controls = [], []
    with X.successor_scope(next_bound, findings, E.saved['third_round'],
                           E.saved['third_by_event'], E.source_inputs,
                           E.chain, signature=E.result['notes']['candidate']):
        assert F._receipt_still_the_proved_one(str(RUN), next_bound) == []

        def positive():
            proved, problems = F.run_evidence(str(RUN), next_bound, receipt)
            assert not problems, problems
            assert set(proved) == set(findings)
            assert all(v[0] == 'proved' for v in proved.values()), proved
            return proved

        positive()
        prior_dirs = F._prior_runs(str(RUN), next_bound, receipt)
        assert prior_dirs
        original_spent = F._spent_identities
        for state_path in receipt['states']:
            state = K._load(state_path)
            session_dir, session_id = F.HR.AUD._official_location(state_path)
            assert session_id == K.PARENT_SESSION
            agents = [r for r in state['workflowProgress'] if r.get('type') == 'workflow_agent']
            assert len(agents) == 1 and agents[0]['state'] == 'done'
            agent, run_id = agents[0], state['runId']
            transcript = Path(session_dir) / 'subagents/workflows' / run_id / ('agent-%s.jsonl' % agent['agentId'])
            records = F.HR.AUD._jsonl(str(transcript))
            assistant = [r for r in records if r.get('type') == 'assistant']
            observed = ({run_id}, {agent['agentId']},
                        {r['message']['id'] for r in assistant},
                        {r['requestId'] for r in assistant})
            assert all(s and None not in s for s in observed)
            models = sorted({r['message']['model'] for r in assistant})
            assert models == ['claude-opus-5'], models
            assert state['script'] == F._v6_context(next_bound, agent['label'], receipt['attempt'])[1]
            identities.append({'source_id': agent['label'], 'run_id': run_id,
                               'state_sha256': G._sha_file(state_path),
                               'transcript_sha256': G._sha_file(str(transcript)),
                               'observed_models': models,
                               'ids': [sorted(s) for s in observed]})
            for slot, name in enumerate(('run', 'agent', 'response', 'request')):
                positive()
                def already_spent(path, slot=slot, observed=observed):
                    sets = [set(s) for s in original_spent(path)]
                    if path == prior_dirs[-1]:
                        sets[slot] |= observed[slot]
                    return tuple(sets)
                with E.R._using(F, _spent_identities=already_spent):
                    refused, problems = F.run_evidence(str(RUN), next_bound, receipt)
                assert refused[agent['label']][0] == 'unproved', (name, refused)
                assert any(name + ' id' in p and 'already spent' in p for p in problems), (name, problems)
                negative_controls.append({'source_id': agent['label'], 'reused': name,
                                          'reasons': problems})
        assert F._spent_identities is original_spent
        after_shards, after_raws, after_origins, problems = F.v6_shards(next_bound)
        assert not problems, problems
        assert set(after_shards) == set(before_shards)
        assert all(after_raws[s] == before_raws[s] and after_origins[s] == before_origins[s]
                   for s in after_shards if s not in findings)
        gate = F.signing_gate(bound.evidence, next_bound)
        before_calls = F.v6_ledger_before(next_bound)
        assert final['ledger']['scheduled'] == final['ledger']['valid'] == len(findings)
        assert final['phase_complete'] and not final['problems'] and not final['retry']
        final_outcomes = {label: outcome for label, outcome, _why in final['outcomes']}
        assert final_outcomes == {s: 'valid' for s in findings}
        native_raws = {s: {'before': K._sha(before_raws[s]), 'after': K._sha(after_raws[s])}
                       for s in findings}
    assert before_files == {str(p): G._sha_file(str(p)) for p in RUN.rglob('*') if p.is_file()}
    report = {'model_calls_started': 0, 'caller_sha256': G._sha_file(__file__),
              'owner_sha256': G._sha_file(X.__file__), 'receipt_sha256': G._sha_file(receipt_path),
              'finalization_sha256': G._sha_file(final_path), 'identities': identities,
              'collision_controls': negative_controls, 'source_raws': native_raws,
              'complete_key_sources': len(after_shards), 'other_sources_unchanged': len(after_shards) - len(findings),
              'source_calls_before': before_calls, 'source_calls_this_round': final['ledger']['scheduled'],
              'source_calls_after': before_calls + final['ledger']['scheduled'],
              'mechanical_gate': {'ok': gate['ok'], 'stops': gate.get('stops'), 'counts': gate.get('counts')},
              'source_meaning_approval': False,
              'limitation': 'Collection and identity proof only; source meaning requires independent review.'}
    G._write_new(str(E.out / 'COMPLETED_SOURCE_RECHECKS_2124.json'), G._pretty(report) + '\n')
    print('COMPLETED_SOURCE_RECHECKS', len(identities), len(negative_controls),
          report['source_calls_after'], gate['ok'], flush=True)


E.with_prepared_inputs(prove)
