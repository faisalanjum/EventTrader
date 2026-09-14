# -*- coding: utf-8 -*-
"""VERIFY the already-saved corrected G3 package. No regeneration, no call.

The package was written by attempt core_g3prep2159_c. Nothing here renders,
batches or prepares anything: it loads those exact frozen bytes in the proven
current-key context and proves, for every one of the 116 rows, that the asked
record is this event's own produced row, that the served context and reference
cards are the ones their owners return for that source, and that the comparison
pool is exactly this event's matched produced rows. Then it measures every
primary and allowed-retry bound script against the existing limit.
"""
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
UNIT = A7 / 'unit_2159_current_g3'
for rel in ('unit_2118_correction_native', 'unit_2020_codex_check',
            'unit_2143_source_authority'):
    sys.path.insert(0, str(A7 / rel))
sys.path.insert(0, str(UNIT))
from build_candidate_2148 import E                                 # noqa: E402
import a7_g1_key_reuse_2152 as REUSE                               # noqa: E402
import a7_grading_script_binding_2156 as TRANSPORT                 # noqa: E402
import a7_grading_input_correction_2114 as V                       # noqa: E402
import g3_checks_2159 as CHECK                                     # noqa: E402

G, B, GR = E.G, E.B, E.GR
KIND = 'G3'
OUT = UNIT / os.environ['A7_TAG']
input_path = os.environ['A7_CURRENT_G23_INPUT']
assert G._sha_file(input_path) == os.environ['A7_CURRENT_G23_INPUT_SHA256']
approved = G._read(input_path)
base_path = os.environ['A7_G3_BASE']
assert G._sha_file(base_path) == os.environ['A7_G3_BASE_SHA256']
base = G._read(base_path)
package_dir = os.environ['A7_G3_PACKAGE']
package_sha = os.environ['A7_G3_PACKAGE_SHA256']


def verify(producer, inputs, g1):
    OUT.mkdir(parents=True)
    # ---- THE SAVED PACKAGE, loaded by hash; nothing is rebuilt -------------
    written, sha = G.load_frozen(package_dir, package_sha)
    assert sha == package_sha
    assert written['task_kind'] == KIND and written['made_calls'] == 0

    # ---- ITS POPULATIONS ARE THE PINNED CURRENT ONES -----------------------
    pinned = {}
    for kind, handle in sorted(base['candidates'].items()):
        frozen, _s = G.load_frozen(str(Path(handle['path']).parent),
                                   handle['sha256'])
        pinned[kind] = frozen
    g3_pop, g2_pop = written['population'], written['matched_population']
    assert G._plain(g3_pop) == G._plain(pinned['G3']['population'])
    assert G._plain(g2_pop) == G._plain(pinned['G2']['population'])
    assert G._plain(written['key_identity']) == G._plain(base['key_identity'])
    assert G._plain(written['g1_identity']) == G._plain(B.g1_identity(g1))
    assert written['input_correction_sha256'] == G._sha_file(V.__file__)

    prompts, prompt_bytes = {}, []
    for row in written['batch_rows']:
        text = (Path(package_dir) / row['prompt_path']).read_text()
        assert G._sha(text) == row['prompt_sha256'], row['batch_id']
        prompts[row['batch_id']] = text
        prompt_bytes.append({'batch_id': row['batch_id'], 'items': row['items'],
                             'prompt_bytes': len(text.encode('utf-8'))})

    # ---- THE OWNERS' OWN VALUES for this event, never the packet's claim ---
    _legs, _t, _m, arms, gold, inv_problems = G.inventory(producer)
    assert not inv_problems, inv_problems

    def context_of(_leg, source_id):
        ctx = dict(B.verified_event_context(inputs, source_id, producer))
        ctx.pop('_source_id', None)
        return ctx

    def cards_of(_leg, source_id):
        return [B.reference_card(f, source_id, i, producer)
                for i, f in ((gi, gold[source_id][gi])
                             for gi in G.accepted_positions(gold[source_id]))]

    rows, problems, empty = CHECK.audit(
        written, prompts, g3_pop, g2_pop,
        lambda leg, sid, i: V.record_view(arms[leg][sid]['facts'][i]),
        B.extras_question_id, context_of, cards_of)

    # ---- THE EXISTING BOUND-SCRIPT GATE, primary and every allowed retry ---
    launches = G.launchers(written['batch_rows'])
    variants, oversize = [], []
    for ordinal, call in enumerate(launches):
        call = dict(call, ordinal=ordinal, prompt=prompts[call['batch_id']])
        for attempt in range(1, G.MAX_ATTEMPTS + 1):
            size = len(G._bound_script(
                [call], {'candidate_sha256': package_sha}, '0' * 64,
                attempt).encode('utf-8'))
            variants.append(size)
            if size > GR.W.SCRIPT_BYTE_LIMIT:
                oversize.append((call['lane_id'], attempt, size))

    report = CHECK.plain_report({
        'scope': 'VERIFICATION of the saved corrected G3 package; nothing '
                 'regenerated, no model call, NOT a launch approval',
        'model_calls': 0, 'regenerated': False,
        'package_dir': package_dir, 'package_sha256': package_sha,
        'input_correction_sha256': written['input_correction_sha256'],
        'rules_block_sha256': written['rules_block_sha256'],
        'checker_sha256': G._sha_file(CHECK.__file__),
        'caller_sha256': G._sha_file(__file__),
        'key_identity': written['key_identity'],
        'producer_identity': producer,
        'questions_declared': written['questions'],
        'questions_audited': len(rows),
        'audit_problems': problems,
        'audit_problem_count': len(problems),
        'population_groups': len(g3_pop),
        'population_rows': sum(len(v) for v in g3_pop.values()),
        'comparator_groups': len(g2_pop),
        'comparator_pairs': sum(len(v) for v in g2_pop.values()),
        'empty_comparator_groups': empty,
        'batches': len(written['batch_rows']),
        'batch_sizes': prompt_bytes,
        'maximum_prompt_bytes': max(r['prompt_bytes'] for r in prompt_bytes),
        'lanes_per_batch': len(G.GRADER_LANES),
        'max_attempts': G.MAX_ATTEMPTS,
        'primary_call_ceiling': len(launches),
        'invalid_only_retry_ceiling': len(launches) * (G.MAX_ATTEMPTS - 1),
        'bound_script_variants': len(variants),
        'maximum_bound_script_bytes': max(variants),
        'script_byte_limit': GR.W.SCRIPT_BYTE_LIMIT,
        'oversize_variants': oversize,
        'rows': rows,
    })
    G._write_new(str(OUT / 'CURRENT_G3_VERIFICATION_2159.json'),
                 G._pretty(report) + '\n')
    print('G3 VERIFIED:', json.dumps({k: report[k] for k in (
        'questions_audited', 'audit_problem_count', 'batches',
        'primary_call_ceiling', 'invalid_only_retry_ceiling',
        'maximum_bound_script_bytes', 'empty_comparator_groups')}), flush=True)
    assert not problems, problems[:3]
    assert not oversize, oversize[:3]
    assert len(rows) == written['questions']
    return report


with TRANSPORT.scope(approved['script_binding'], approved['g1']['pins']):
    REUSE.evaluate(E, approved['report'], approved['g1'], verify)
assert G._sha_file(input_path) == os.environ['A7_CURRENT_G23_INPUT_SHA256']
print('Completed saved-package verification; no model call.', flush=True)
