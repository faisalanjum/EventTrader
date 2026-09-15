"""Preserve ONE returned probe workflow's raw evidence before anything reads it.

Copies the official state, the journal, every child transcript and the exact
returned text into this durable directory and byte-compares each copy against
its original. Interprets nothing and changes nothing.

    python3 -B preserve_probe.py <diagnostic_id> <run_id>
"""
import hashlib, io, json, os, shutil, sys

sys.dont_write_bytecode = True
DIAG, RUN = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'evidence', RUN)
SESSION = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
           '5ae9b86b-f0f6-4449-beee-9cac7cfa7200')
sha = lambda p: hashlib.sha256(io.open(p, 'rb').read()).hexdigest()

os.path.isdir(OUT) or os.makedirs(OUT)
state = os.path.join(SESSION, 'workflows', RUN + '.json')
kids = os.path.join(SESSION, 'subagents', 'workflows', RUN)
copied, mismatch, originals = [], [], {}
sources = [state]
if os.path.isdir(kids):
    sources += [os.path.join(kids, f) for f in sorted(os.listdir(kids))]
for src in sources:
    if not os.path.isfile(src):
        continue
    dst = os.path.join(OUT, os.path.basename(src))
    shutil.copy2(src, dst)
    originals[src] = sha(src)
    (copied if sha(src) == sha(dst) else mismatch).append(os.path.basename(src))

doc = json.load(io.open(state, encoding='utf-8'))
result = doc.get('result') or {}
text = result.get('text')
raw = os.path.join(OUT, 'returned_text.txt')
io.open(raw, 'w', encoding='utf-8').write(text if isinstance(text, str) else '')
payload = os.path.join(OUT, 'returned_result.json')
io.open(payload, 'w', encoding='utf-8').write(
    json.dumps(result, indent=1, sort_keys=True) + '\n')

manifest = {
    'diagnostic_id': DIAG, 'run_id': RUN, 'status': doc.get('status'),
    'agents': doc.get('agentCount'), 'tool_calls': doc.get('totalToolCalls'),
    'tokens': doc.get('totalTokens'), 'duration_ms': doc.get('durationMs'),
    'returned_error': result.get('error'),
    'returned_text_present': isinstance(text, str),
    'returned_text_chars': len(text) if isinstance(text, str) else None,
    'returned_text_utf8_bytes': len(text.encode('utf-8')) if isinstance(text, str) else None,
    'returned_text_sha256': sha(raw),
    'returned_result_sha256': sha(payload),
    'state_sha256': sha(state),
    'original_paths': originals,
    'files_preserved': sorted(copied), 'mismatches': mismatch,
    'evidence_dir': OUT,
}
out = os.path.join(OUT, 'MANIFEST.json')
io.open(out, 'w', encoding='utf-8').write(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
assert not mismatch, mismatch
print(json.dumps(manifest, sort_keys=True))
