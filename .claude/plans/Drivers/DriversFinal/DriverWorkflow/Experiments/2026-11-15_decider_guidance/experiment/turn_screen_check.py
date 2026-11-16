"""Structural comparison: existing utterances, same definition/question, whole call.

The extractor sees no reference labels. Parent-passage retention is compared with
the frozen six-call reference afterward; max child score is not a parent probability.
"""
import json
from pathlib import Path
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from passage_cohort_check import ROOT, DEFINITION, QUESTION, digest, save, log

OUT = ROOT / 'turn_screen'


def prepare():
    OUT.mkdir(exist_ok=True)
    assert not (OUT / 'manifest.json').exists()
    manifest = []
    for source in json.loads((ROOT / 'sources.json').read_text()):
        sid = source['id']
        base = json.loads((ROOT / 'passage_cohort' / (sid + '_request.json')).read_text())
        snapshot_path = Path(source['snapshot'])
        assert digest(snapshot_path.read_bytes()) == source['snapshot_sha256']
        turns, rendered, source_start = [], [], 0
        for passage in source['passages']:
            if passage['kind'] == 'prepared':
                texts = [passage['text']]
            else:
                # prepare_review.py already preserved these exact native entries
                # while normalizing the two saved snapshot envelopes.
                texts = [e['text'] for e in passage['entries']]
            assert '\n'.join(texts) == passage['text']
            pieces, offset = [], 0
            for text in texts:
                tag = 'T' + str(len(turns)).zfill(3)
                assert passage['text'][offset:offset + len(text)] == text
                assert source['text'][source_start + offset:source_start + offset + len(text)] == text
                turns.append({'tag': tag, 'passage': passage['id'], 'start': offset,
                              'end': offset + len(text), 'text': text,
                              'source_start': source_start + offset,
                              'source_end': source_start + offset + len(text)})
                pieces.append('[' + tag + '] ' + text)
                offset += len(text) + 1
            rendered.append('[' + passage['id'] + '] ' + '\n'.join(pieces))
            source_start += len(passage['text']) + 2
        original = '\n\n'.join(p['text'] for p in source['passages'])
        assert original == source['text']
        header = base['state'].split('\n', 1)[0]
        state = header + '\n' + DEFINITION + '\n\n' + '\n\n'.join(rendered)
        questions = {t['tag']: {'type': 'noul', 'instructions': QUESTION.format(passage=t['tag'])}
                     for t in turns}
        request = {'source_id': sid, 'state': state, 'questions': questions,
                   'mode': 'isolated', 'turns': turns,
                   'source_text_sha256': digest(original.encode())}
        path = OUT / (sid + '_request.json')
        save(path, request)
        manifest.append({'source_id': sid, 'file': path.name, 'sha256': digest(path.read_bytes()),
                         'passages': len(source['passages']), 'turns': len(turns)})
    save(OUT / 'manifest.json', {'requests': manifest, 'definition': DEFINITION,
                               'question': QUESTION, 'model': 'pplx-decider-v1.3:8bit',
                               'runner_sha256': digest(Path(__file__).read_bytes()),
                               'frozen_at': datetime.now(ZoneInfo('America/Toronto')).isoformat(),
                               'scope': 'Same question/definition/header as the passage check. Only target boundaries and their visible tags change. Source text is unchanged. Existing entries are not guaranteed to be perfectly diarized natural turns.'})
    log('Prepare a generic utterance-targeted comparison using stored prepared blocks and Q&A entries, without text heuristics.',
        f'All six frozen sources reconstruct exactly; {sum(x["turns"] for x in manifest)} targets replace {sum(x["passages"] for x in manifest)} passage targets. No model calls during preparation.',
        'Test one complete call with observed passage-screen misses, using identical wording and no answer-key input; compare both coverage and cost.')
    print(json.dumps(manifest, indent=2))


def run(source):
    manifest = json.loads((OUT / 'manifest.json').read_text())
    row = next(r for r in manifest['requests'] if r['source_id'] == source)
    request_path = OUT / row['file']
    assert digest(request_path.read_bytes()) == row['sha256']
    path = OUT / (source + '_result.json')
    assert not path.exists(), 'Inspect saved result before any rerun.'
    request = json.loads(request_path.read_text())
    sys.path.insert(0, '/home/faisal/EventMarketDB')
    from config import local_llm as L
    assert L.DECIDER_MODEL == manifest['model']
    started = time.perf_counter()
    result = {'source_id': source, 'request_sha256': row['sha256']}
    try:
        result['response'] = L.decide(request['state'], request['questions'], mode='isolated', timeout=1800)
    except Exception as exc:
        result['error'] = repr(exc)
    result['seconds'] = time.perf_counter() - started
    result['finished_at'] = datetime.now(ZoneInfo('America/Toronto')).isoformat()
    save(path, result)
    log(f'Whole-call guidance screen, one unchanged question per stored utterance: {source}, {row["turns"]} questions.',
        f'{result["seconds"]:.2f}s; usage={result.get("response", {}).get("usage")}; error={result.get("error")}. Source-based scoring follows.',
        'Compare retained known claims and extra passages with the frozen passage run. Do not adopt from a single call or change the prompt to fit its misses.')
    print(json.dumps({k: v for k, v in result.items() if k != 'response'}), flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'run':
        run(sys.argv[2])
