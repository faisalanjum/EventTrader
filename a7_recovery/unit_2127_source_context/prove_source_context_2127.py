"""Prove the source-context renderer at the REAL seam. No call, no mutation.

Four things, in order:
  1. the prefix served today lacks the clarification (the RED);
  2. installed at the existing `F.v6_prefix` seam, the current prompt gains
     exactly that one span and nothing else;
  3. WITH the install held, a nested prior-round read still renders its
     recorded prompt byte-exact, and every recorded raw stays untouched;
  4. the focused tests and the directly affected 2063 prefix regression run,
     both sides, and their raw output is kept and hashed.
"""
import collections
import json
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E                              # noqa: E402

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
_spec = importlib.util.spec_from_file_location(
    'current_key_candidate_2127', candidate,
    loader=SourceFileLoader('current_key_candidate_2127', candidate))
E.X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E.X)

U = E.A7 / 'unit_2127_source_context'
OUT = U / os.environ['A7_TAG']
PACKET = E.A7 / 'unit_2123_post_signature_key/core_recheck2123_h/recheck_packet'


def _run(name, module, env_extra):
    """One test module, as its own process, with its raw output kept."""
    env = dict(os.environ)
    env.update(env_extra)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    r = subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v', module],
                       cwd=str(module_dir(module)), env=env,
                       capture_output=True, text=True)
    (OUT / ('%s.stdout.txt' % name)).write_text(r.stdout)
    (OUT / ('%s.stderr.txt' % name)).write_text(r.stderr)
    tail = [l for l in r.stderr.strip().split('\n') if l.strip()][-1:]
    return collections.OrderedDict([
        ('module', module), ('env', env_extra), ('exit', r.returncode),
        ('summary', tail[0] if tail else ''),
        ('stdout_sha256', E.G._sha_file(str(OUT / ('%s.stdout.txt' % name)))),
        ('stderr_sha256', E.G._sha_file(str(OUT / ('%s.stderr.txt' % name))))])


def module_dir(module):
    return (E.A7 / 'unit_2127_source_context' if module.startswith('test_source')
            else E.A7 / 'unit_2063_source_closeout')


def prove(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    OUT.mkdir(parents=True)
    sys.path.insert(0, str(E.A7 / 'unit_2063_source_closeout'))
    sys.path.insert(0, str(U))
    import a4_source_taskv2 as V2                                 # noqa: E402
    import a7_source_context_2127 as V3                           # noqa: E402

    bound = G._approved_bound()
    request = G._read(str(E.A7 / 'unit_2020_codex_check'
                          / 'SOURCE_KEY_RECHECK_BINDINGS_2120.json'))
    order = [t['source_id'] for t in F.event_tasks(bound.evidence)]
    findings = collections.OrderedDict()
    for event in sorted(request['source_events'],
                        key=lambda e: order.index(e['source_id'])):
        sid = event['source_id']
        findings[sid] = [collections.OrderedDict(
            [('source_id', sid),
             ('raw_sha256', event['prior_source_raw_sha256']), ('row', row)])
            for row in event['original_task_ids']]
    run_id = E.saved['third_round']
    candidate_dir = E.result['notes']['candidate']
    next_bound = X.bind(bound, str(PACKET))

    raws_before = {p.name: G._sha_file(str(p))
                   for p in sorted((PACKET / 'raw').glob('*'))}
    with X.successor_scope(next_bound, findings, run_id,
                           E.saved['third_by_event'], E.source_inputs,
                           E.chain, signature=candidate_dir):
        # ---- 1. the RED, at the seam this phase actually serves ------------
        before = {sid: F.v6_prompt(next_bound, sid) for sid in findings}
        red = {sid: V3.CLARIFICATION_BLOCK in t for sid in before
               for t in [before[sid]]}
        # ---- 2. the scoped install: ONE call, the way C2065 installs V2 ----
        #: the seam the scope ALREADY installed, captured BEFORE the swap.
        #: Reading the live attribute inside the replacement would call this
        #: function again and recurse forever - the discipline V2 records for
        #: `_C2023_SERVED_PREFIX` and this module's own capture of V2's builder.
        installed = F.v6_prefix

        def context_prefix(package, keys):
            with E.R._using(V2, served_prefix=V3.served_prefix):
                return installed(package, keys)

        with E.R._using(F, v6_prefix=context_prefix):
            after = {sid: F.v6_prompt(next_bound, sid) for sid in findings}
            # ---- 3. a nested prior-round read, WITH the install held -------
            history = list(E.chain) + [(run_id, E.saved['third_by_event'])]
            historical = []
            for i, (prior_run, prior_findings) in enumerate(history):
                prior_bound = X.first_bound(bound, prior_run)
                with X.first_round_scope(bound, prior_run, prior_findings,
                                         E.source_inputs, tuple(history[:i])):
                    recorded = K._load(os.path.join(prior_run, K.RECEIPT_NAME))
                    actual = {s: K._sha(F.v6_prompt(prior_bound, s))
                              for s in F.v6_labels(prior_bound)}
                historical.append(collections.OrderedDict([
                    ('run', prior_run), ('prompts', len(actual)),
                    ('byte_exact', actual == recorded['prompts'])]))

    rows = []
    for sid in findings:
        b, a = before[sid], after[sid]
        head, tail = b.split(V3.SPAN_OLD, 1)
        rows.append(collections.OrderedDict([
            ('source_id', sid),
            ('served_today_has_the_clarification', red[sid]),
            ('clarification_occurrences_after', a.count(V3.CLARIFICATION_BLOCK)),
            ('exactly_one_span_changed', a == head + V3.SPAN_NEW + tail),
            ('bytes_added', len(a) - len(b)),
            ('prompt_sha256_before', K._sha(b)), ('prompt_sha256_after', K._sha(a)),
            ('input_body_identical',
             b.split('[INPUT]\n', 1)[1] == a.split('[INPUT]\n', 1)[1])]))

    tests = [
        _run('focused_red', 'test_source_context_2127', {}),
        _run('focused_green', 'test_source_context_2127',
             {'A7_CONTEXT_OWNER': 'new'}),
        _run('regression_2063_red', 'test_prefix_spans_2063', {}),
        _run('regression_2063_green', 'test_prefix_spans_2063',
             {'A7_PREFIX_OWNER': 'new'}),
    ]
    # the expected RED/GREEN pattern is ASSERTED, not merely recorded: each
    # suite must fail on the prefix served today and pass on the candidate.
    expected = [1, 0, 1, 0]
    assert [t['exit'] for t in tests] == expected, \
        'test outcomes are %s, not the RED/GREEN pattern %s' % (
            [t['exit'] for t in tests], expected)
    raws_after = {p.name: G._sha_file(str(p))
                  for p in sorted((PACKET / 'raw').glob('*'))}
    report = collections.OrderedDict([
        ('scope', 'the source-context renderer proved at the real v6_prefix '
                  'seam; no call, no key or answer mutation'),
        ('caller_sha256', G._sha_file(__file__)),
        ('renderer_sha256', G._sha_file(str(U / 'a7_source_context_2127.py'))),
        ('focused_test_sha256', G._sha_file(str(U / 'test_source_context_2127.py'))),
        ('builds_on', V3.__dict__['VERSION']),
        ('clarification', V3.CLARIFICATION),
        ('clarification_block', V3.CLARIFICATION_BLOCK),
        ('span_old', V3.SPAN_OLD), ('span_new', V3.SPAN_NEW),
        ('prompts', rows),
        ('historical_rounds_byte_exact_with_the_install_held', historical),
        ('recorded_raws_unchanged', raws_before == raws_after),
        ('recorded_raws', raws_after),
        ('packet_receipt_sha256', G._sha_file(str(PACKET / K.RECEIPT_NAME))),
        ('tests', tests),
        ('model_calls', 0)])
    G._write_new(str(OUT / 'SOURCE_CONTEXT_PROOF_2127.json'),
                 G._pretty(report) + '\n')
    print('SOURCE_CONTEXT_PROOF_2127', json.dumps(collections.OrderedDict([
        ('red', [r['served_today_has_the_clarification'] for r in rows]),
        ('after', [r['clarification_occurrences_after'] for r in rows]),
        ('one_span', [r['exactly_one_span_changed'] for r in rows]),
        ('input_identical', [r['input_body_identical'] for r in rows]),
        ('historical', [h['byte_exact'] for h in historical]),
        ('raws_unchanged', report['recorded_raws_unchanged']),
        ('tests', [(t['module'][:26], bool(t['env']), t['exit']) for t in tests]),
    ])), flush=True)
    print('sha256', G._sha_file(str(OUT / 'SOURCE_CONTEXT_PROOF_2127.json')),
          flush=True)
    return report


E.with_prepared_inputs(prove)
