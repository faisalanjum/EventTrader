"""Score a frozen sentence screen; controls and parent retention stay separate."""
import json
import math
import sys
from passage_cohort_check import ROOT, digest, save, log


def counts(rows, field, expected, cutoff):
    out = dict(tp=0, fn=0, fp=0, tn=0, unadjudicated_retained=0,
               unadjudicated_filtered=0)
    for row in rows:
        keep = row[field] >= cutoff
        label = row[expected]
        if label == 'unadjudicated':
            key = 'unadjudicated_retained' if keep else 'unadjudicated_filtered'
        elif label is True or label == 'positive':
            key = 'tp' if keep else 'fn'
        else:
            assert label is False or label == 'negative'
            key = 'fp' if keep else 'tn'
        out[key] += 1
    assert sum(out.values()) == len(rows)
    return out


source_id = sys.argv[1]
folder = ROOT / 'sentence_screen'
request_path = folder / (source_id + '_request.json')
reference_path = folder / (source_id + '_reference.json')
request = json.loads(request_path.read_text())
reference = json.loads(reference_path.read_text())
result = json.loads((folder / (source_id + '_result.json')).read_text())
assert result['request_sha256'] == reference['request_sha256'] == digest(request_path.read_bytes())
assert result['reference_sha256'] == digest(reference_path.read_bytes())
assert 'error' not in result
response = result['response']
assert response['model'] == 'pplx-decider-v1.3:8bit'
assert set(response['answers']) == set(request['questions'])
source = next(s for s in json.loads((ROOT / 'sources.json').read_text()) if s['id'] == source_id)
assert digest(source['text'].encode()) == reference['source_sha256'] == request['source_text_sha256']
passages = {p['id']: p for p in source['passages']}
sentences = []
for sentence in request['sentences']:
    assert source['text'][sentence['source_start']:sentence['source_end']] == sentence['text']
    score = response['answers'][sentence['tag']]['noul']
    assert math.isfinite(score) and 0 <= score <= 1
    sentences.append({**sentence, 'score': score})
by_tag = {s['tag']: s for s in sentences}
controls = []
for control in reference['controls']:
    assert passages[control['passage']]['text'][control['start']:control['end']] == control['text']
    assert len(control['sentences']) == 1, 'Report multi-sentence controls separately.'
    sentence = by_tag[control['sentences'][0]]
    assert sentence['passage'] == control['passage']
    assert sentence['start'] <= control['start'] < control['end'] <= sentence['end']
    controls.append({**control, 'score': sentence['score']})
parent_reference = [r for r in json.loads((ROOT / 'passage_cohort/reference.json').read_text())['rows']
                    if r['source_id'] == source_id]
baseline = json.loads((ROOT / 'passage_cohort' / (source_id + '_result.json')).read_text())
parents = []
for row in parent_reference:
    children = [s for s in sentences if s['passage'] == row['passage']]
    assert children
    parents.append({**row, 'max_sentence_score': max(s['score'] for s in children),
                    'passage_score': baseline['response']['answers'][row['passage']]['noul']})
scores = {str(c): {'controls': counts(controls, 'score', 'expected', c),
                  'sentences_selected': sum(s['score'] >= c for s in sentences),
                  'parents_from_sentences': counts(parents, 'max_sentence_score', 'label', c),
                  'parent_baseline': counts(parents, 'passage_score', 'label', c)}
          for c in (0.5, 0.25)}
report = {'source_id': source_id, 'scores': scores, 'controls': controls, 'parents': parents,
          'sentences': sentences, 'seconds': result['seconds'], 'usage': response['usage'],
          'limits': 'Previously fixed development controls, not complete independent gold. Parent retention may mask missed claims inside a retained passage. Maximum child score is not a parent probability. Every selected sentence still needs source review; no full-record or calibration claim.'}
save(folder / (source_id + '_scores.json'), report)
log(f'Score all {len(sentences)} sentence responses for {source_id}, verifying frozen hashes, exact text and complete answer coverage.',
    f'{scores}; {result["seconds"]:.2f}s, usage={response["usage"]}. Controls are development labels, not distinct-fact recall.',
    'Review each selected sentence and all control misses; record limitations without a fourth screening repair or fitted cutoff.')
print(json.dumps({k: v for k, v in report.items() if k not in ('controls', 'parents', 'sentences', 'limits')}, indent=2))
for row in controls:
    print(f'CONTROL {row["expected"]!s:5s} {row["sentences"][0]} {row["score"]:.4f} {row["id"]}: {row["text"]}')
for sentence in sentences:
    if sentence['score'] >= 0.25:
        print(f'SELECTED {sentence["tag"]} {sentence["passage"]} {sentence["score"]:.4f}: {sentence["text"]}')
