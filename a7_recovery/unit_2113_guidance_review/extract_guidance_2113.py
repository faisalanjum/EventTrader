"""Extract the COMPLETE set of G2 questions whose produced fact_type is guidance.

Reads only frozen, saved evidence: the G2 candidate the run was frozen against,
its served prompt batches, and the whole-review input's per-question verdicts.
Selection is by the produced record's own fact_type over ALL 306 questions, so
it cannot be a hand-picked or failure-only sample.

    python3 -B extract_guidance_2113.py <out.json>
"""
import collections
import glob
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
K = os.path.join(A7, 'unit_2020_codex_check')
G2 = os.path.join(K, 'codex_g23partial2098_fit/G2')
CAND = os.path.join(G2, 'a7_g1_candidate.json')
REVIEW = os.path.join(K, 'G2_WHOLE_REVIEW_INPUT_2111.json')
PINS = {CAND: 'cc9d51f526e69ff29361f9b620d6ad6085abdc2aa802035f605a1cb261052feb',
        REVIEW: '59d54d9744dc43f922b8571322b238897f3c8f8aaa17ff6a4a25ef8d6ef39d16'}


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


for path, digest in PINS.items():
    assert sha(path) == digest, path

candidate = json.load(io.open(CAND, encoding='utf-8'))
review = json.load(io.open(REVIEW, encoding='utf-8'))
checks = {c['question_id']: c for c in review['question_checks']}
batch_of = {}
for row in candidate['batch_rows']:
    for qid in row['question_ids']:
        batch_of[qid] = row

by_type = collections.Counter()
rows = []
for prompt in sorted(glob.glob(os.path.join(G2, 'prompts/*.prompt.txt'))):
    text = io.open(prompt, encoding='utf-8').read()
    payload = json.loads(text[text.index('[EVENT]') + len('[EVENT]'):])
    bid = os.path.basename(prompt).split('.')[0]
    brow = next(r for r in candidate['batch_rows'] if r['batch_id'] == bid)
    # the prompt states no source_id inside an event, so the binding is the
    # batch's own ordered source list. Asserted, never assumed: one event per
    # source, and the question order the candidate froze.
    assert len(payload['events']) == len(brow['source_ids']), bid
    assert [q['question_id'] for e in payload['events']
            for q in (e.get('questions') or [])] == brow['question_ids'], bid
    for ev_i, event in enumerate(payload['events']):
        assert len(event.get('questions') or []) == 1, (bid, ev_i)
        ctx = event['event_context']
        for q in event.get('questions') or []:
            rec = q['produced_record']
            by_type[rec.get('fact_type')] += 1
            if rec.get('fact_type') != 'guidance':
                continue
            qid = q['question_id']
            row = batch_of[qid]
            # the source part the record says it was read from. text_parts is
            # a LIST of {part, content}; treating it as a mapping silently made
            # every containment check None, so it is indexed by its own `part`.
            parts = {p['part']: (p.get('content') or '')
                     for p in (ctx.get('text_parts') or [])}
            part = rec.get('part_ref')
            body = parts.get(part)
            quote = (rec.get('item') or {}).get('quote') or ''
            rows.append(collections.OrderedDict([
                ('question_id', qid), ('batch_id', row['batch_id']),
                ('prompt_path', row['prompt_path']),
                ('prompt_sha256', row['prompt_sha256']),
                ('source_ids_in_batch', row['source_ids']),
                ('event_source_id', brow['source_ids'][ev_i]),
                ('event_index', ev_i),
                ('event_date', ctx.get('event_date')),
                ('fye_month', ctx.get('fye_month')),
                ('part_ref', part),
                ('quote_found_verbatim_in_part',
                 bool(body) and quote in body),
                ('quote_found_in_any_part',
                 any(quote in v for v in parts.values())),
                ('parts_present', sorted(parts)),
                ('part_body', body),
                ('produced_record', rec),
                ('reference_card', q['reference_card']),
                ('established', (checks.get(qid) or {}).get('established')),
                ('unresolved', (checks.get(qid) or {}).get('unresolved')),
                ('menu', ctx.get('menu')),
            ]))

assert len(rows) == by_type['guidance'], 'lost a guidance question'
out = collections.OrderedDict([
    ('scope', 'every G2 question whose produced fact_type is guidance'),
    ('candidate_sha256', PINS[CAND]), ('review_input_sha256', PINS[REVIEW]),
    ('questions_total', sum(by_type.values())),
    ('questions_by_produced_fact_type', collections.OrderedDict(
        sorted(by_type.items()))),
    ('guidance_questions', len(rows)),
    ('rows', rows),
])
with io.open(sys.argv[1], 'w', encoding='utf-8') as fh:
    fh.write(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: out[k] for k in
                  ('questions_total', 'questions_by_produced_fact_type',
                   'guidance_questions')}, indent=1))
print('WROTE', sys.argv[1], sha(sys.argv[1]))
