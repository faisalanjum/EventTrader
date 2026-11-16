"""Whole-call sentence screening; existing native segmentation, no source filtering."""
import json
from pathlib import Path
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from passage_cohort_check import ROOT, DEFINITION, digest, save, log

sys.path.insert(0, str(ROOT / 'vendor'))
import pysbd

OUT = ROOT / 'sentence_screen'
TASK = ("SCREEN_TASK: Under the supplied guidance definition, decide whether the specified sentence "
        "states, reaffirms, withdraws or qualifies management guidance. Use the whole transcript as "
        "context. An analyst's question alone is not management confirmation.")


def prepare(source_id):
    OUT.mkdir(exist_ok=True)
    path = OUT / (source_id + '_request.json')
    assert not path.exists(), 'Do not overwrite a frozen configuration.'
    source = next(s for s in json.loads((ROOT / 'sources.json').read_text()) if s['id'] == source_id)
    base = json.loads((ROOT / 'passage_cohort' / (source_id + '_request.json')).read_text())
    assert source['text'] == '\n\n'.join(p['text'] for p in source['passages'])
    segmenter = pysbd.Segmenter(language='en', clean=False, char_span=True)
    sentences, rendered, original_start = [], [], 0
    for passage in source['passages']:
        text = passage['text']
        spans = segmenter.segment(text)
        coverage = [False] * len(text)
        labels = []
        for span in spans:
            assert text[span.start:span.end] == span.sent
            assert source['text'][original_start + span.start:original_start + span.end] == span.sent
            for index in range(span.start, span.end):
                assert not coverage[index]
                coverage[index] = True
            tag = 'S' + str(len(sentences)).zfill(3)
            assert '[' + tag + ']' not in source['text'], 'Source/label collision; do not reinterpret source as a tag.'
            sentences.append({'tag': tag, 'passage': passage['id'], 'start': span.start,
                              'end': span.end, 'source_start': original_start + span.start,
                              'source_end': original_start + span.end, 'text': span.sent})
            labels.append((span.start, '[' + tag + '] '))
        assert all(covered or character.isspace() for covered, character in zip(coverage, text))
        tagged = text
        for position, label in reversed(labels):
            tagged = tagged[:position] + label + tagged[position:]
        rendered.append('[' + passage['id'] + '] ' + tagged)
        original_start += len(text) + 2
    header = base['state'].split('\n', 1)[0]
    state = header + '\n' + DEFINITION + '\n' + TASK + '\n\n' + '\n\n'.join(rendered)
    questions = {s['tag']: {'type': 'noul', 'instructions': f'Does sentence [{s["tag"]}] meet SCREEN_TASK?'}
                 for s in sentences}
    request = {'source_id': source_id, 'state': state, 'questions': questions,
               'mode': 'isolated', 'sentences': sentences,
               'source_text_sha256': digest(source['text'].encode()),
               'library': {'package': 'pysbd==0.3.4', 'clean': False, 'char_span': True,
                           'source': str(Path(pysbd.__file__).resolve()),
                           'segmenter_sha256': digest(Path(pysbd.segmenter.__file__).read_bytes())},
               'runner_sha256': digest(Path(__file__).read_bytes()),
               'frozen_at': datetime.now(ZoneInfo('America/Toronto')).isoformat(),
               'limits': 'Same broad guidance definition, complete source and metadata header. Shared task wording and short questions reuse the measured shared-definition pattern. Target granularity, tags, question membership and instruction layout differ from passage/turn runs; not a pure single-variable accuracy comparison. No forecast/record completeness claim from sentence flags.'}
    save(path, request)
    log(f'Prepare whole-call sentence targeting for {source_id} using native pysbd exact spans.',
        f'{len(sentences)} sentence targets, all {len(source["passages"])} passages and every non-whitespace source character accounted for. Shared task instructions avoid repeated long questions. No model calls.',
        'Freeze quote-level source controls separately, then run once and compare actual relevant statements as well as parent-passage retention.')
    print(json.dumps({'source': source_id, 'sentences': len(sentences), 'state_characters': len(state),
                      'question_characters': sum(len(q['instructions']) for q in questions.values()),
                      'request_sha256': digest(path.read_bytes())}), flush=True)


def run(source_id):
    request_path = OUT / (source_id + '_request.json')
    request = json.loads(request_path.read_text())
    reference_path = OUT / (source_id + '_reference.json')
    assert reference_path.exists(), 'Freeze separate source controls before inference.'
    path = OUT / (source_id + '_result.json')
    assert not path.exists(), 'Inspect any saved result before retrying.'
    sys.path.insert(0, '/home/faisal/EventMarketDB')
    from config import local_llm as L
    assert L.DECIDER_MODEL == 'pplx-decider-v1.3:8bit'
    result = {'source_id': source_id, 'request_sha256': digest(request_path.read_bytes()),
              'reference_sha256': digest(reference_path.read_bytes()),
              'started_at': datetime.now(ZoneInfo('America/Toronto')).isoformat()}
    print(json.dumps({'started': source_id, 'at': result['started_at'], 'questions': len(request['questions'])}), flush=True)
    started = time.perf_counter()
    try:
        result['response'] = L.decide(request['state'], request['questions'], mode='isolated', timeout=1800)
    except Exception as exc:
        result['error'] = repr(exc)
    result['seconds'] = time.perf_counter() - started
    result['finished_at'] = datetime.now(ZoneInfo('America/Toronto')).isoformat()
    save(path, result)
    log(f'Whole-call direct sentence screening: {source_id}, {len(request["questions"])} questions, no coarse filter.',
        f'{result["seconds"]:.2f}s; usage={result.get("response", {}).get("usage")}; error={result.get("error")}. Complete semantic scoring still pending.',
        'Check frozen source controls and every selected sentence; compare cost/coverage without tuning the threshold or adding a repair layer.')
    print(json.dumps({k: v for k, v in result.items() if k != 'response'}), flush=True)


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]](sys.argv[2])
