# -*- coding: utf-8 -*-
"""Preserve ONE returned workflow's raw evidence before anything reads it.

Copies the official state, the journal, the returned payload and every child
transcript into the kind's durable evidence directory and byte-compares each
copy against its original. Interprets nothing and changes nothing.
"""
import hashlib, io, json, os, shutil, sys
sys.dont_write_bytecode = True
KIND, SEGMENT, RUN_ID = sys.argv[1], int(sys.argv[2]), sys.argv[3]
A7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U = os.path.join(A7, 'unit_2173_grading')
SESSION = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
           '5ae9b86b-f0f6-4449-beee-9cac7cfa7200')
sha = lambda p: hashlib.sha256(io.open(p, 'rb').read()).hexdigest()
out = os.path.join(U, KIND, 'evidence', RUN_ID)
os.path.isdir(out) or os.makedirs(out)
state = os.path.join(SESSION, 'workflows', RUN_ID + '.json')
kids = os.path.join(SESSION, 'subagents', 'workflows', RUN_ID)
copied, mismatch = [], []
for src in [state] + ([os.path.join(kids, f) for f in sorted(os.listdir(kids))]
                      if os.path.isdir(kids) else []):
    dst = os.path.join(out, os.path.basename(src))
    if not os.path.isfile(src):
        continue
    shutil.copy2(src, dst)
    (copied if sha(src) == sha(dst) else mismatch).append(os.path.basename(src))
doc = json.load(io.open(state, encoding='utf-8'))
payload = os.path.join(out, 'returned_payload.json')
io.open(payload, 'w', encoding='utf-8').write(
    json.dumps(doc.get('result'), indent=1, sort_keys=True) + '\n')
record = {'kind': KIND, 'segment': SEGMENT, 'run_id': RUN_ID,
          'status': doc.get('status'), 'agents': doc.get('agentCount'),
          'tokens': doc.get('totalTokens'), 'duration_ms': doc.get('durationMs'),
          'tool_calls': doc.get('totalToolCalls'),
          'state_sha256': sha(state), 'files_preserved': len(copied),
          'mismatches': mismatch,
          'results': len((doc.get('result') or {}).get('results') or []),
          'errors': [r.get('error') for r in
                     ((doc.get('result') or {}).get('results') or [])
                     if r.get('error')],
          'empty_text': [r.get('lane_id') for r in
                         ((doc.get('result') or {}).get('results') or [])
                         if not (r.get('text') or '').strip()],
          'evidence_dir': out, 'payload_sha256': sha(payload)}
assert not mismatch, mismatch
print(json.dumps(record, sort_keys=True))
