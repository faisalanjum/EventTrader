"""Compare matched source/definition at passage vs stored-utterance boundaries."""
import json
from pathlib import Path
import sys
from passage_cohort_check import ROOT, digest, save, log

source = sys.argv[1]
folder = ROOT / 'turn_screen'
request_path = folder / (source + '_request.json')
request = json.loads(request_path.read_text())
result = json.loads((folder / (source + '_result.json')).read_text())
assert result['request_sha256'] == digest(request_path.read_bytes())
assert 'error' not in result
response = result['response']
assert response['model'] == 'pplx-decider-v1.3:8bit'
assert set(response['answers']) == set(request['questions'])
reference = [r for r in json.loads((ROOT / 'passage_cohort/reference.json').read_text())['rows']
             if r['source_id'] == source]
baseline = json.loads((ROOT / 'passage_cohort' / (source + '_result.json')).read_text())
by_passage = {r['passage']: [] for r in reference}
for turn in request['turns']:
    probability = response['answers'][turn['tag']]['noul']
    assert 0 <= probability <= 1
    by_passage[turn['passage']].append({**turn, 'probability': probability})
rows = []
for ref in reference:
    children = by_passage[ref['passage']]
    assert children
    rows.append({**ref, 'passage_score': baseline['response']['answers'][ref['passage']]['noul'],
                 'max_turn_score': max(t['probability'] for t in children), 'turns': children})
scores = {}
for cutoff in [0.5, 0.25]:
    comparison = {}
    for name, field in [('passages', 'passage_score'), ('turns', 'max_turn_score')]:
        counts = dict(tp=0, fn=0, fp=0, tn=0, unadjudicated_retained=0, unadjudicated_filtered=0)
        for row in rows:
            keep = row[field] >= cutoff
            if row['label'] == 'unadjudicated':
                key = 'unadjudicated_retained' if keep else 'unadjudicated_filtered'
            elif row['label'] == 'positive':
                key = 'tp' if keep else 'fn'
            else:
                key = 'fp' if keep else 'tn'
            counts[key] += 1
        assert sum(counts.values()) == len(rows)
        comparison[name] = counts
    scores[str(cutoff)] = comparison
report = {'source': source, 'rows': rows, 'scores': scores,
          'timings': {'passages_seconds': baseline['seconds'], 'turns_seconds': result['seconds']},
          'usage': {'passages': baseline['response']['usage'], 'turns': response['usage']},
          'limits': 'Parent passage retained if any native utterance meets the cutoff. Maximum child score is not a calibrated parent probability. Same source and wording; target granularity/tags/question membership differ. Single development call, no complete-record or unseen score. Inspect which speaker text triggered a retained passage.'}
save(folder / (source + '_comparison.json'), report)
log(f'Compare passage vs existing-utterance guidance targeting on {source}, using the frozen source-derived labels.',
    f'{scores}; timings={report["timings"]}; usage={report["usage"]}. Parent retention only; complete records and semantic error review remain separate.',
    'Inspect changed classifications against source before retaining or rejecting this structural alternative; no prompt repair or cutoff tuning.')
print(json.dumps({k: v for k, v in report.items() if k not in ['rows', 'limits']}, indent=2))
