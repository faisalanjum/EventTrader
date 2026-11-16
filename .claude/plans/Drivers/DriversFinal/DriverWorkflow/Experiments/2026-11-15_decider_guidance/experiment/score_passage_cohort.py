"""Score frozen passage results; no model calls or interpretation heuristics."""
import hashlib
import json
from pathlib import Path

ROOT = Path('/tmp/decider_claude_review_20261115')
OUT = ROOT / 'passage_cohort'
manifest = json.loads((OUT / 'manifest.json').read_text())
assert hashlib.sha256((OUT / 'reference.json').read_bytes()).hexdigest() == manifest['reference_sha256']
reference = json.loads((OUT / 'reference.json').read_text())['rows']
rows, runs, missing, errors = [], [], [], []
for m in manifest['requests']:
    source = m['source_id']
    path = OUT / (source + '_result.json')
    if not path.exists():
        missing.append(source)
        continue
    result = json.loads(path.read_text())
    assert result['request_sha256'] == m['sha256']
    if 'error' in result:
        errors.append({'source': source, 'error': result['error']})
        continue
    response = result['response']
    assert response['model'] == manifest['model']
    answers = response['answers']
    expected = [r for r in reference if r['source_id'] == source]
    assert set(answers) == {r['passage'] for r in expected}
    for row in expected:
        probability = answers[row['passage']]['noul']
        assert isinstance(probability, (float, int)) and 0 <= probability <= 1
        rows.append({**row, 'probability': probability})
    runs.append({'source': source, 'seconds': result['seconds'], 'usage': response['usage']})

by_source = {r['source_id']: {} for r in rows}
for r in rows:
    by_source[r['source_id']][r['passage']] = r
scores = {}
for cutoff in [0.5, 0.25]:
    totals = {'tp': 0, 'fn': 0, 'fp': 0, 'tn': 0,
              'unadjudicated_retained': 0, 'unadjudicated_filtered': 0}
    per_source, disagreements, unavailable_context = [], [], []
    for source, passages in by_source.items():
        counts = {k: 0 for k in totals}
        for r in passages.values():
            kept = r['probability'] >= cutoff
            if r['label'] == 'unadjudicated':
                outcome = 'unadjudicated_retained' if kept else 'unadjudicated_filtered'
            elif r['label'] == 'positive':
                outcome = 'tp' if kept else 'fn'
            else:
                outcome = 'fp' if kept else 'tn'
            counts[outcome] += 1
            if outcome in ['fn', 'fp']:
                disagreements.append({**r, 'outcome': outcome})
        assert sum(counts.values()) == len(passages)
        for k, value in counts.items():
            totals[k] += value
        per_source.append({'source': source, **counts})
        inventory = json.loads((ROOT / 'reference_key' / (source + '.json')).read_text())
        for claim in inventory['claims']:
            for e in claim['evidence']:
                if passages[e['passage']]['probability'] < cutoff:
                    unavailable_context.append({
                        'source': source, 'claim': claim['id'], 'claim_status': claim['status'],
                        'claim_meaning': claim['meaning'], 'passage': e['passage'],
                        'evidence_role': e['role'], 'evidence_text': e['text'],
                        'probability': passages[e['passage']]['probability'],
                        'note': 'Source remains in full context. A later sentence/choice menu restricted to retained passages cannot point here. This is not automatically a detector error or a complete-record miss.'})
    scores[str(cutoff)] = {'counts': totals, 'per_source': per_source,
                          'disagreements': disagreements,
                          'context_outside_retained_passages': unavailable_context}

report = {
    'scope': 'Six development calls, one fixed passage question. Labels are source-derived, not independently adjudicated gold. Existing 0.5 and 0.25 cutoffs are descriptive comparisons, not tuned or certified settings.',
    'complete': not missing and not errors, 'missing_results': missing, 'technical_errors': errors,
    'runs': runs, 'rows': rows, 'scores': scores,
    'elapsed_sum_seconds': sum(r['seconds'] for r in runs),
    'input_tokens': sum(r['usage']['input_tokens'] for r in runs),
    'sequences': sum(r['usage']['sequences'] for r in runs),
}
(OUT / 'scores.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'complete': report['complete'], 'completed_calls': len(runs),
                  'passages': len(rows), 'seconds': round(report['elapsed_sum_seconds'], 2),
                  'cutoffs': {k: v['counts'] for k, v in scores.items()},
                  'technical_errors': errors}, indent=2))
