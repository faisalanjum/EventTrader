"""Native TEST records -> format recovery -> unchanged real A7 scorer.

No AI calls. The source key, producer and G1 are real saved evidence; only
G2/G3 verdicts are explicitly labelled TEST fixtures. Nothing is overwritten.
"""
import copy
import json
import os
from functools import partial
from pathlib import Path

import prepare_g23_partial_2097 as E
import a7_g1_complete_v2 as C
import a7_meaning_format_2105 as F
import audit_worker_access as AUD
import g1_fake_state as FAKE
import raw_transport as RT

G, B, GR, R = E.G, E.B, E.GR, E.R
pins = [os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']]
root_dir = E.out / 'TEST_only'
projects = str(root_dir / 'projects')
native_evidence = C.evidence


def check(problems):
    assert not problems, problems


def run(producer, _inputs):
    path = os.environ['A7_VERIFY_G23_PREPARATION']
    assert G._sha_file(path) == os.environ['A7_VERIFY_G23_PREPARATION_SHA256']
    prep = G._read(path)
    assert prep['producer'] == producer and prep['g1'] == E.g1
    reuse_path = os.environ['A7_TEST_REUSE_SOURCES']
    assert G._sha_file(reuse_path) == os.environ['A7_TEST_REUSE_SOURCES_SHA256']
    reuse = G._read(reuse_path)
    old_root = Path(reuse['test_root'])
    old_projects = str(old_root / 'projects')
    combined = G._read(str(Path(path).parent / GR.CANDIDATE_NAME))
    ident = prep['candidates']['G2']
    original = Path(ident['path']).parent
    doc, _ = G.load_frozen(str(original), ident['sha256'])
    prompts = {r['batch_id']: (original / r['prompt_path']).read_text() for r in doc['batch_rows']}
    candidate, run_dir = root_dir / 'candidate_G2', root_dir / 'run_G2'
    _candidate_path, digest = GR.write_kind(str(candidate), 'G2', combined, prompts, prep['key_identity'])
    assert digest == ident['sha256']
    spec, _ = RT.declared_lane_input()
    transcript = os.environ['A7_TEST_INPUT_TRANSCRIPT']
    assert G._sha_file(transcript) == os.environ['A7_TEST_INPUT_TRANSCRIPT_SHA256']
    record = [json.loads(line) for line in Path(transcript).read_text().splitlines()][spec['record_index']]
    assert AUD._expected_input(record, spec['record_index'], spec)
    declared = dict(spec, payload=record[spec['payload_field']])
    root, root_sha, bad = G.freeze_root(str(candidate), str(run_dir), digest,
        lane_inputs={r['lane_id']: copy.deepcopy(spec) for r in doc['launchers']['rows']})
    check(bad)
    binding, strict_parser = G.binding_and_parser('G2')
    batches = doc['batch_rows']
    false_q, null_q, disagree_q = [r['question_ids'][0] for r in batches[:3]]
    bad_batch = batches[3]
    bad_lane = bad_batch['batch_id'] + '/' + G.GRADER_LANES[0]
    field = B.meaning_fields()[0]
    expected_unresolved = {null_q, disagree_q, *bad_batch['question_ids']}
    expected_relations, finals = {}, []

    def collect(lanes, attempt):
        identity, bad = G.publish_run(str(candidate), str(run_dir), root_sha, lanes, attempt=attempt)
        check(bad)
        n, receipt_sha = identity['segment'], identity['receipt_sha256']
        packet, bad = G.preflight(str(candidate), str(run_dir), n, root_sha, receipt_sha)
        check(bad)
        receipt = G.load_receipt(str(run_dir), n)
        answers, results = {}, []
        for arg in packet['args']:
            body = [{'question_id': q, 'verdicts': dict.fromkeys(B.meaning_fields(), 'true')}
                    for q in binding(doc, arg['batch_id'])['question_ids']]
            for row in body:
                qid = row['question_id']
                if qid == false_q:
                    row['verdicts'][field] = 'false'
                if qid == null_q:
                    row['verdicts'][field] = 'null'
                if qid == disagree_q and arg['lane_id'].endswith('/' + G.GRADER_LANES[0]):
                    row['verdicts'][field] = 'false'
            if arg['lane_id'] == bad_lane:
                body[0]['verdicts'][field] = 'True'  # deliberately NOT recoverable
            raw = json.dumps(body)
            assert strict_parser(raw, binding(doc, arg['batch_id']))[1]
            if arg['lane_id'] != bad_lane:
                expected_relations[arg['lane_id']] = {
                    r['question_id']: {f: json.loads(v) for f, v in r['verdicts'].items()} for r in body}
            result = {k: arg.get(k) for k in G.RESULT_BINDING}
            result.update(invocation_sha256=receipt['invocation_sha256'], text=raw, error=None)
            results.append(result)
            answers[arg['lane_id']] = raw
        _accounting, bad = G.save_results(str(run_dir), n, results, root_sha, receipt_sha)
        check(bad)
        state = FAKE.build(str(root_dir), str(run_dir), n, G, answers=answers,
            errors={}, projects_root=projects, run_id='wf_TEST_format_%s_%s' % (G._sha(str(run_dir))[:12], n))
        check(G.record_official_state(str(run_dir), n, state, root_sha, receipt_sha))
        final, _rulings, bad = G.finalize_segment(str(candidate), str(run_dir), n, root_sha, receipt_sha)
        check(bad)
        assert not final['uncalled'] and not any(ok for _lane, ok in final['validity'])
        check(G.audit_official_state(str(run_dir), n, root_sha, receipt_sha)[0])
        finals.append(final)

    def fixture_evidence(candidate, run, *args):
        location = Path(run).resolve()
        selected = projects if location.is_relative_to(root_dir.resolve()) else (
            old_projects if location.is_relative_to(old_root.resolve()) else None)
        if selected:
            with R._using(AUD, PROJECTS_ROOT=selected):
                return native_evidence(candidate, run, *args)
        return native_evidence(candidate, run, *args)

    before = C.run_digest(E.g1['run_dir'])
    with R._using(AUD, PROJECTS_ROOT=projects), \
            R._using(FAKE, _transcript=partial(FAKE._transcript, declared=declared)):
        collect([r['lane_id'] for r in root['rows']], 1)
        collect([bad_lane], 2)
    original_identity = C.g23_identity(root_sha, str(run_dir))
    run_pins = (root_sha, original_identity['run_digest'], original_identity['run_files'])
    with R._using(C, evidence=fixture_evidence):
        original_records = C.evidence(str(candidate), str(run_dir), *run_pins)
        check(original_records[3])
        assert not C.relations_from_run(original_records[2])
        with F.scope(*pins):
            _root, cdoc, lanes, bad = C.evidence(str(candidate), str(run_dir), *run_pins)
            check(bad)
            assert C.relations_from_run(lanes) == expected_relations
            assert all(not any(r['attempts'].values()) for r in lanes.values())
            assert lanes[bad_lane]['selected'] is None
            assert C.evidence(str(candidate), str(run_dir), root_sha, '0' * 64, run_pins[2])[3]
            identity = C.g23_identity(root_sha, str(run_dir))
            audit = identity['meaning_format_recovery']['attempts']
            assert len(audit) == len(root['rows']) + 1
            assert sum(r['recovered'] for r in audit) == len(root['rows']) - 1
            assert not any(r['original_valid'] for r in audit)
            completion, bad = C.complete_g23(cdoc, C.relations_from_run(lanes), identity)
            check(bad)
            assert {r['question_id'] for r in completion['unresolved']} == expected_unresolved
            assert completion['questions'] == doc['questions']
            assert completion['credited_questions'] == doc['questions'] - len(expected_unresolved)
            assert completion['credited'][false_q]['verdict'][field] is False
            _path, completion_sha = C.persist_g23(str(candidate), completion)
            assert C.load_g23(str(candidate), completion_sha, root_sha, str(run_dir)) == completion
            sources = dict(reuse['sources'], G2={'run_dir': str(run_dir), 'root_sha256': root_sha,
                'completion_sha256': completion_sha})
            by_leg = {leg: sources for leg in prep['findings']}
            routed, loads = [], []
            route, load = B.route_for, C.load_g23
            def route_event(*args, **kwargs):
                routed.extend((Path(args[1]).name, sid) for sid in args[0])
                return route(*args, **kwargs)
            def load_completion(*args, **kwargs):
                loads.append(args[0])
                return load(*args, **kwargs)
            with R._using(B, route_for=route_event), R._using(C, load_g23=load_completion):
                decisions, results = B.official_tier_decision(producer, by_leg, str(E.out / 'route'), E.g1)
            expected_routes = {(leg, sid) for leg in by_leg for sid in G.live_key()[0]}
            assert len(routed) == len(expected_routes) and set(routed) == expected_routes
            assert len(loads) == 2
            assert all(r['gold_n'] == prep['full_key_fact_count'] for r in results.values())
            assert results['P2']['required_grading_unfinished']
            assert results['P2']['matched'] <= prep['full_key_fact_count'] - prep['findings']['P2']['incomplete'][0]['of']
            false_legs = [leg for key, pairs in doc['population'].items()
                          for leg, sid in [key.split('|', 1)] for gi, pi in pairs
                          if B.meaning_question_id(leg, sid, gi, pi) == false_q]
            assert len(false_legs) == 1
            assert results[false_legs[0]]['confirmed_wrong_accepted'] >= 1
            assert set(decisions.values()) == {False}
            # These negative controls target the actual consumer boundary
            # already exercised above; routing all99 event-legs again cannot
            # add proof to a completion-hash or completion-rederivation check.
            wrong = {'G2': dict(sources['G2'], completion_sha256='0' * 64)}
            try:
                B._verdict_maps_from(false_legs[0], wrong, producer,
                                     {'G2': doc['population']}, E.g1, {})
            except ValueError as exc:
                assert 'not the approved' in str(exc)
                wrong_hash = str(exc)
            else:
                raise AssertionError('wrong completion hash reached scoring')
        try:
            B._verdict_maps_from(false_legs[0], {'G2': sources['G2']}, producer,
                                 {'G2': doc['population']}, E.g1, {})
        except ValueError as exc:
            assert 'not what its own saved attempts derive' in str(exc)
            strict_refusal = str(exc)
        else:
            raise AssertionError('format-dependent completion scored without its approved recovery')
    assert C.run_digest(E.g1['run_dir']) == before
    assert C.run_digest(str(run_dir)) == (run_pins[1], run_pins[2])
    report = {'scope': 'native TEST G2/G3; real key/producer/G1; NOT an A7 score',
        'actual_model_calls': 0, 'code_sha256': pins[0], 'rule_sha256': pins[1],
        'sources': sources, 'completion': completion, 'original_invalid_attempts': len(audit),
        'recovered_attempts': sum(r['recovered'] for r in audit),
        'expected_unresolved': sorted(expected_unresolved), 'route_count': len(routed),
        'strict_control': strict_refusal, 'wrong_hash_control': wrong_hash,
        'decisions': decisions, 'results': results, 'original_records_unchanged': True}
    G._write_new(str(E.out / 'SCORING_CONNECTION.json'), G._pretty(report) + '\n')
    print('VERIFIED native TEST recovery through actual scorer; %s original invalids, %s recovered, %s unresolved questions' % (
        len(audit), sum(r['recovered'] for r in audit), len(expected_unresolved)), flush=True)


E.with_prepared_inputs(run)
