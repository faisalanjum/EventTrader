# -*- coding: utf-8 -*-
"""The real connection proof for the source-rule closeout packet. SEQ 2143.

`A7_CASE` selects one case or `remaining`. The remaining cases share one
verified native setup: the pinned 2134 owner already includes served wording
in the existing cache key. Reuse the two completed, stored wording proofs;
do not repeat them. Native execution stays serial.

ZERO CALLS. No invocation is authorized by this task, including the one this
round prepares. Nothing here launches, schedules or signs anything.
"""
import collections
import json
import os
import sys
from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E                                  # noqa: E402

CAND = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(CAND) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
_s = importlib.util.spec_from_file_location(
    'round_owner_2143', CAND, loader=SourceFileLoader('round_owner_2143', CAND))
E.X = importlib.util.module_from_spec(_s)
_s.loader.exec_module(E.X)

U = E.A7 / 'unit_2143_source_authority'
OUT = U / os.environ['A7_TAG']
CASE = os.environ['A7_CASE']
#: the prepared deliverable; one directory, named once, never finalized here
PACKET = U / 'packet_2143'
REPORT = U / 'AUTHORITY_PACKET_2143.json'
#: the two already completed wording cases stored their exact assembled tasks
STORE = U / 'assembled_2143'
#: the completed round this one follows; it must not move while we read it
DONE = str(E.A7 / 'unit_2136_source_questions/packet_2136')
IMMUTABLE = [CAND,
             str(E.A7 / 'unit_2127_source_context/a7_source_context_2127.py'),
             str(E.A7 / 'unit_2128_source_corrections/a7_round_binding_2128.py'),
             str(E.A7 / 'unit_2136_source_questions/a7_round_binding_2136.py'),
             str(E.A7 / 'unit_2136_source_questions/prepare_questions_2136.py'),
             str(E.A7 / 'unit_2136_source_questions/collect_questions_2136.py'),
             str(U / 'collect_authority_2143.py'),
             str(U / 'a7_source_authority_2143.py'),
             str(U / 'a7_round_binding_2143.py')]


def _tree(root):
    return collections.OrderedDict(
        (str(p.relative_to(root)), E.G._sha_file(str(p)))
        for p in sorted(Path(root).rglob('*')) if p.is_file())


def run(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    OUT.mkdir(parents=True)
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections', 'unit_2136_source_questions',
                'unit_2143_source_authority'):
        sys.path.insert(0, str(E.A7 / rel))
    import a7_source_context_2127 as V3                               # noqa: E402
    import a7_round_binding_2136 as B2136                             # noqa: E402
    import prepare_questions_2136 as P                                # noqa: E402
    import collect_authority_2143 as C                                # noqa: E402
    import a7_source_authority_2143 as V4                             # noqa: E402
    import a7_round_binding_2143 as B                                 # noqa: E402

    before_files = {p: G._sha_file(p) for p in IMMUTABLE}
    done_before = _tree(DONE)
    out = collections.OrderedDict([('case', CASE),
                                   ('caller_sha256', G._sha_file(__file__))])

    def refuses(action):
        try:
            action()
        except ValueError as exc:
            return str(exc)
        raise AssertionError('%s did not refuse' % CASE)

    def assembled(version):
        """The FULLY assembled task for this round's one event, rendered."""
        bb = B.binding(E, X, B2136, V4)
        _sh, raws, _o, bad = B.current_key(E, X, bb)
        assert not bad, bad[:2]
        findings = B.round_findings(E, bb, raws)
        bound = X.bind(bb.bound, str(PACKET))
        label = bb.affected[0]
        with B.scope(E, X, bb, bound, findings, version):
            return label, F.v6_prompt(bound, label)

    # ------------------------------------------------------------------ #
    if CASE == 'authority_absent':
        # TEST FIRST: the defect itself, measured in the fully assembled task
        # under the wording the completed eight were actually served.
        label, prompt = assembled(V3)
        STORE.mkdir(parents=True, exist_ok=True)
        path = str(STORE / 'ASSEMBLED_UNDER_2127.txt')
        G._write_new(path, prompt)
        text = V4.clause()
        out['label'] = label
        out['stored'] = path
        out['stored_sha256'] = G._sha_file(path)
        out['prompt_bytes'] = len(prompt.encode('utf-8'))
        out['clause_sha256'] = K._sha(text)
        out['clause_occurrences'] = prompt.count(text)
        out['anchor_occurrences'] = prompt.count(V4.TARGET_ITEM)
        out['label_occurrences'] = prompt.count(V4.LABEL)
        # the authority is MISSING, and the place it belongs is present exactly
        # once - so the gap is a real absence, not a missing anchor
        assert out['clause_occurrences'] == 0, out['clause_occurrences']
        assert out['label_occurrences'] == 0, out['label_occurrences']
        assert out['anchor_occurrences'] == 1, out['anchor_occurrences']

    elif CASE == 'authority_served':
        stored = str(STORE / 'ASSEMBLED_UNDER_2127.txt')
        old = K._read(stored)
        label, prompt = assembled(V4)
        path = str(STORE / 'ASSEMBLED_UNDER_2143.txt')
        G._write_new(path, prompt)
        text = V4.clause()
        out['label'] = label
        out['compared_against'] = stored
        out['compared_against_sha256'] = G._sha_file(stored)
        out['stored_sha256'] = G._sha_file(path)
        out['clause_occurrences'] = prompt.count(text)
        out['clause_owner_sha256'] = G._sha_file(V4.owner_path())
        out['bytes_before'] = len(old.encode('utf-8'))
        out['bytes_after'] = len(prompt.encode('utf-8'))
        out['bytes_added'] = out['bytes_after'] - out['bytes_before']
        # EXACT INSERTION: putting the anchor back where the served block is
        # restores the earlier assembled task byte for byte, so the inserted
        # block is the ONLY difference anywhere in the task.
        restored = prompt.replace(V4.span_new(), V4.TARGET_ITEM, 1)
        out['only_difference_is_the_inserted_block'] = restored == old
        out['inserted_block_sha256'] = K._sha(V4.span_new())
        out['served_block'] = V4.span_new()
        assert out['clause_occurrences'] == 1, out['clause_occurrences']
        assert out['only_difference_is_the_inserted_block']
        assert out['bytes_added'] == len(
            ('\n%s\n%s\n' % (V4.LABEL, text)).encode('utf-8'))

    elif CASE == 'prepare':
        report = P.prepare(E, X, B, B2136, V4, str(PACKET))
        G._write_new(str(REPORT), G._pretty(report) + '\n')
        out['report_sha256'] = G._sha_file(str(REPORT))
        out['events'] = len(report['events'])
        out['rows_served'] = sum(report['rows_served'].values())
        out['findings_served'] = sum(report['findings_served'].values())
        out['accounting'] = report['accounting']
        out['capacity_problems'] = report['capacity_problems']
        out['largest_script_bytes'] = report['largest_script_bytes']
        out['receipt_states'] = report['receipt_states']
        out['renderer_sha256'] = report['renderer_sha256']
        out['binding_sha256'] = report['binding_sha256']
        out['declared_scope'] = report['pointers']['round_declared_scope']
        out['round_event_rows'] = report['pointers']['round_event_rows']
        # the packet must serve the EXACT assembled task the diff proved
        proved = str(STORE / 'ASSEMBLED_UNDER_2143.txt')
        out['proved_assembly'] = proved
        out['served_prompt_sha256'] = report['input_declarations'][0]['prompt_sha256']
        out['served_prompt_matches_proved_assembly'] = (
            out['served_prompt_sha256'] == K._sha(K._read(proved)))
        assert out['served_prompt_matches_proved_assembly']
        assert out['events'] == 1, out['events']
        assert out['rows_served'] == 6, out['rows_served']
        assert out['findings_served'] == 1, out['findings_served']
        assert out['receipt_states'] == []
        assert not out['capacity_problems'], out['capacity_problems']

    elif CASE == 'predecessor':
        bb = B.binding(E, X, B2136, V4)
        _sh, raws, origins, bad = B.current_key(E, X, bb)
        assert not bad, bad[:2]
        review = B.pinned(E, B.REVIEW, B.REVIEW_SHA256)
        root_raw = review['all_current_raw_sha256']
        root_org = review['all_current_origins']
        out['key_sources'] = len(raws)
        out['root_sources'] = len(root_raw)
        mismatched = sorted(s for s in raws if K._sha(raws[s]) != root_raw.get(s))
        out['raw_mismatches_vs_root'] = mismatched
        out['affected'] = list(bb.affected)
        out['origin_mismatches_vs_root'] = sorted(
            s for s in raws if origins.get(s) != root_org.get(s))
        carried = [s for s in sorted(raws) if s not in bb.affected]
        out['unaffected_sources'] = len(carried)
        out['unaffected_carry_matches_root'] = all(
            K._sha(raws[s]) == root_raw.get(s) and origins.get(s) == root_org.get(s)
            for s in carried)
        out['predecessor_run'] = bb.predecessor
        out['prefix_rounds'] = sorted(bb.prefixes)
        out['prior_rounds'] = [r for r, _f in bb.prior]
        # the key is the REAL eight's, source for source, against root's own
        # independently measured review
        assert out['key_sources'] == out['root_sources'] == 33, out['key_sources']
        assert not mismatched, mismatched
        assert not out['origin_mismatches_vs_root'], out['origin_mismatches_vs_root']
        assert out['unaffected_sources'] == 32, out['unaffected_sources']
        assert out['unaffected_carry_matches_root']
        assert bb.predecessor == DONE, bb.predecessor

    elif CASE == 'collect':
        # The collector is proved on its OWN isolated probe, never on the
        # deliverable: finalizing the deliverable would leave it no longer
        # unrun (measured in the 2136 round, core_q2136_collect, exit 1).
        states = json.loads(os.environ['A7_COLLECT_STATES'])
        assert states == [], 'the empty-answer probe requires an explicit empty list'
        out['supplied_states'] = states
        probe = str(OUT / 'zero_answer_probe_packet')
        probe_report = str(OUT / 'PROBE_REPORT.json')
        rep = P.prepare(E, X, B, B2136, V4, probe)
        G._write_new(probe_report, G._pretty(rep) + '\n')
        out['probe_run_dir'] = probe
        out['probe_events'] = len(rep['events'])
        rec = C.collect(E, probe_report, G._sha_file(probe_report), states)
        out['outcomes'] = sorted({o for _l, o, _w in rec['finalization']['outcomes']})
        out['reasons'] = sorted({w for _l, _o, w in rec['finalization']['outcomes']})
        out['ledger'] = rec['finalization']['ledger']
        out['phase_complete'] = rec['finalization']['phase_complete']
        out['retry'] = rec['finalization']['retry']
        out['child'] = rec['finalization']['child']
        out['paid_raw_files'] = list(rec['paid_raw_files'])
        out['before_this_round'] = rec['accounting']['before_this_round']
        out['finalization_sha256'] = rec['finalization']['sha256']
        assert out['probe_events'] == 1, out['probe_events']
        assert out['ledger']['scheduled'] == 1, out['ledger']
        assert out['ledger']['valid'] == 0, out['ledger']
        assert 'valid' not in out['outcomes'], out['outcomes']
        assert not out['phase_complete'] and out['retry'] == []
        assert out['child'] is None
        assert not out['paid_raw_files'], out['paid_raw_files']
        # resume is idempotent and pays nothing
        again = C.collect(E, probe_report, G._sha_file(probe_report), states)
        out['resume_identical'] = (
            again['finalization']['outcomes'] == rec['finalization']['outcomes']
            and again['finalization']['sha256'] == out['finalization_sha256'])
        out['resume_states_still_empty'] = again['receipt_states_after'] == []
        assert out['resume_identical'] and out['resume_states_still_empty']
        out['deliverable_untouched_by_this_case'] = not os.path.exists(
            os.path.join(str(PACKET), K.FINALIZATION_NAME))
        assert out['deliverable_untouched_by_this_case']

    elif CASE == 'wrong_authority':
        # VALID CONTROL FIRST, in this same process: the authority reads and
        # serves cleanly, so every refusal below is the tamper and not the
        # environment.
        control = V4.clause()
        out['control_clause_sha256'] = K._sha(control)
        out['control_reads'] = control == V4.clause()
        assert out['control_reads']
        real_clause, real_owner = V4.CLAUSE_SHA256, V4.CLAUSE_OWNER_SHA256
        try:
            V4.CLAUSE_SHA256 = '0' * 64
            out['refusal_wrong_clause_pin'] = refuses(V4.clause)
            V4.CLAUSE_SHA256 = real_clause
            V4.CLAUSE_OWNER_SHA256 = '0' * 64
            out['refusal_wrong_owner_pin'] = refuses(V4.clause)
        finally:
            V4.CLAUSE_SHA256, V4.CLAUSE_OWNER_SHA256 = real_clause, real_owner
        # a version module that is not the pinned renderer is refused too
        out['refusal_wrong_version'] = refuses(
            lambda: B.binding(E, X, B2136, V3))
        out['control_after'] = V4.clause() == control
        assert 'not once' in out['refusal_wrong_clause_pin']
        assert 'not the pinned' in out['refusal_wrong_owner_pin']
        assert 'not the pinned renderer' in out['refusal_wrong_version']
        assert out['control_after']

    elif CASE == 'missing_prefix':
        bb = B.binding(E, X, B2136, V4)
        # VALID CONTROL: with the declared prefixes the predecessor reads
        _sh, raws, _o, bad = B.current_key(E, X, bb)
        out['control_key_sources'] = len(raws)
        out['control_clean'] = not bad
        assert out['control_clean'] and len(raws) == 33
        out['refusal'] = refuses(lambda: X.first_round_key(
            bb.bound, bb.predecessor, bb.predecessor_findings,
            E.source_inputs, bb.prior, signatures=bb.signatures, prefixes={}))
        assert 'receipt.prompts is not the expected value' in out['refusal'], \
            out['refusal']
    else:
        raise AssertionError('unknown case %r' % CASE)

    out['pinned_files_unchanged'] = \
        {p: G._sha_file(p) for p in IMMUTABLE} == before_files
    out['completed_packet_unchanged'] = _tree(DONE) == done_before
    out['model_calls'] = 0
    assert out['pinned_files_unchanged'] and out['completed_packet_unchanged']
    G._write_new(str(OUT / ('CASE_%s.json' % CASE)), G._pretty(out) + '\n')
    print('AUTHORITY_2143', json.dumps(collections.OrderedDict(
        [(k, v) for k, v in out.items()
         if k not in ('caller_sha256', 'served_block')]
        + [('sha', G._sha_file(str(OUT / ('CASE_%s.json' % CASE))))]))[:1100],
        flush=True)
    return out


def run_remaining(producer, inputs):
    global CASE, OUT
    root = U / os.environ['A7_TAG']
    results = collections.OrderedDict()
    for CASE in ('prepare', 'predecessor', 'collect',
                 'wrong_authority', 'missing_prefix'):
        OUT = root / CASE
        results[CASE] = run(producer, inputs)
    import run_preserve_2143 as PR
    PR.OUT = root / 'preserve'
    results['preserve'] = PR.run(producer, inputs)
    E.G._write_new(str(root / 'REMAINING_CHECKS_2144.json'),
                   E.G._pretty(results) + '\n')
    return results


if __name__ == '__main__':
    E.with_prepared_inputs(run_remaining if CASE == 'remaining' else run)
