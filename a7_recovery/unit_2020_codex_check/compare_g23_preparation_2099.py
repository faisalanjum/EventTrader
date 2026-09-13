"""Full frozen-population comparison for the transport-only batching change."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G


def load(name):
    path = os.environ[name]
    assert G._sha_file(path) == os.environ[name + '_SHA256']
    return G._read(path), Path(path).parent


def content(preparation):
    seen = {}
    for kind, identity in preparation['candidates'].items():
        directory = Path(identity['path']).parent
        candidate, _ = G.load_frozen(str(directory), identity['sha256'])
        for row in candidate['batch_rows']:
            text = (directory / row['prompt_path']).read_text()
            assert G._sha(text) == row['prompt_sha256']
            marker = '\n{\n "events":'
            assert text.count(marker) == 1
            start = text.index(marker) + 1
            assert G._sha(text[:start]) == candidate['rules_block_sha256']
            events = json.loads(text[start:])['events']
            assert len(events) == row['items'] == len(row['source_ids'])
            ids = []
            for sid, event in zip(row['source_ids'], events):
                # Only the local E1/E2 display label may change with grouping.
                context = {k: v for k, v in event.items() if k not in ('event', 'questions')}
                for question in event['questions']:
                    qid = question['question_id']
                    assert qid not in seen
                    seen[qid] = {'kind': kind, 'source_id': sid, 'context': context, 'question': question}
                    ids.append(qid)
            assert ids == row['question_ids']
        assert candidate['questions'] == sum(r['items'] for r in candidate['batch_rows'])
    return seen


old, old_dir = load('A7_OLD_G23_PREPARATION')
new, new_dir = load('A7_VERIFY_G23_PREPARATION')
old_doc = G._read(str(old_dir / 'a7_g23_candidate.json'))
new_doc = G._read(str(new_dir / 'a7_g23_candidate.json'))
batch_fields = {'g2', 'g3', 'batching', 'launchers', 'question_to_batch', 'prompt_bytes', 'remaining_calls'}
assert {k: v for k, v in old_doc.items() if k not in batch_fields} == \
       {k: v for k, v in new_doc.items() if k not in batch_fields}
assert old_doc['g3'] == new_doc['g3']
before, after = content(old), content(new)
assert before == after, 'a question, its event context, source card or produced record changed'
for kind in ('G2', 'G3'):
    rows = [r for r in new_doc['batching']['rows'] if r['batch_id'].startswith(kind + '-')]
    assert old_doc[kind.lower()]['questions'] == new_doc[kind.lower()]['questions'] == sum(r['items'] for r in rows)
    assert new_doc[kind.lower()]['batches'] == len(rows)
    assert new_doc['remaining_calls'][kind.lower()] == len(rows) * len(G.GRADER_LANES)
    assert all(len(set(r['source_ids'])) == r['items'] <= new_doc['batching']['max_items_per_call'] for r in rows)
out = Path(__file__).parent / os.environ['A7_TAG']
out.mkdir()
report = {'scope': 'every frozen G2/G3 question compared; zero model calls',
          'old_preparation': os.environ['A7_OLD_G23_PREPARATION_SHA256'],
          'new_preparation': os.environ['A7_VERIFY_G23_PREPARATION_SHA256'],
          'questions': len(after), 'question_context_digest': G._sha(G._plain(after)),
          'unchanged_population_inputs_and_rules': True,
          'g2': new_doc['g2'], 'g3': new_doc['g3'], 'remaining_calls': new_doc['remaining_calls']}
G._write_new(str(out / 'COMPARISON.json'), G._pretty(report) + '\n')
print(G._plain(report), flush=True)
