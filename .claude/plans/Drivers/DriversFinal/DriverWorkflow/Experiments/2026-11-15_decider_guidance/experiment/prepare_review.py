import hashlib
import json
from pathlib import Path

ROOT = Path('/tmp/decider_claude_review_20261115')
paths = sorted(Path('/tmp/decider_prompt_study_20261115_djs24x24').glob('*/snapshot.json'))
paths += [Path('/tmp/decider_real_guidance_20261115_r5zglbm_/snapshot.json')]
sources = []
lines = []
for p in paths:
    raw = json.loads(p.read_text())
    if 'records' in raw:
        raw = dict(raw['records'])
        raw['meta'] = raw.pop('metadata')[0]['source']
        raw['qa'] = [x['exchange'] for x in raw['qa']]
    meta = raw['meta'][0] if isinstance(raw['meta'], list) else raw['meta']
    source_id = meta.get('id') or meta.get('transcript_id')
    if not source_id:
        source_id = 'CTAS_2026-03-25T10.00'
    src = {'id': source_id, 'snapshot': str(p), 'snapshot_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'meta': meta, 'passages': [], 'records': raw['guidance'], 'prior_labels': raw.get('prior_labels', [])}
    for prep in raw['prepared']:
        xs = json.loads(prep['content']) if isinstance(prep['content'], str) else prep['content']
        for i, x in enumerate(xs):
            src['passages'].append({'id': f'PR{i:03d}', 'node_id': prep['id'], 'text': x, 'kind': 'prepared', 'entries': None})
    for qa in sorted(raw['qa'], key=lambda x: int(x['sequence'])):
        xs = json.loads(qa['exchanges']) if isinstance(qa['exchanges'], str) else qa['exchanges']
        src['passages'].append({'id': f'QA{int(qa["sequence"]):03d}', 'node_id': qa['id'], 'text': '\n'.join(x['text'] for x in xs), 'kind': 'qa', 'entries': xs})
    src['text'] = '\n\n'.join(x['text'] for x in src['passages'])
    (ROOT / (source_id + '.txt')).write_text('\n\n'.join('[' + x['id'] + ']\n' + x['text'] for x in src['passages']))
    lines.append('\n## ' + source_id)
    for i, rec in enumerate(src['records']):
        u = rec.get('update', rec)
        lines.append(f'\n### {source_id} / {i:02d}')
        lines.append(json.dumps({k: u.get(k) for k in ('label','id','low','mid','high','canonical_unit','qualitative','conditions','segment','period_scope','fiscal_year','fiscal_quarter','basis_raw','source_refs')}, ensure_ascii=False))
        lines.append('Period: ' + json.dumps(rec.get('period')))
        lines.append('Quote: ' + str(u.get('quote')))
    sources.append(src)
(ROOT/'sources.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2))
(ROOT/'records54.md').write_text('\n'.join(lines))
print(json.dumps([{'id': x['id'], 'records': len(x['records']), 'passages': len(x['passages']), 'characters': len(x['text'])} for x in sources], indent=2))
print('Total records', sum(len(x['records']) for x in sources))
