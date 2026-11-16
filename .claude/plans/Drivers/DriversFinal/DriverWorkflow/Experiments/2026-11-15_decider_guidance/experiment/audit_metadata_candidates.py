"""Read-only full-cohort check of verified-header candidate exclusion."""
import hashlib
import json
import pathlib
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/home/faisal/EventMarketDB')
sys.path.insert(0, '/tmp/decider_claude_review_20261115')
from metadata_candidates import body_start, digit_tokens
from scripts.driver_seed.relocate_probe.phase2.m1_transcript_census import spoken_text
from scripts.earnings.utils import load_env, get_neo4j_config
from neo4j import GraphDatabase, READ_ACCESS, Query

OUT = pathlib.Path('/tmp/decider_claude_review_20261115/metadata_filter')
OUT.mkdir(exist_ok=True)
COHORT = '''EXISTS { (t)-[:HAS_PREPARED_REMARKS]->(:PreparedRemark) }
AND EXISTS { (t)-[:HAS_QA_EXCHANGE]->(:QAExchange) }
AND NOT EXISTS { (t)-[:HAS_QA_SECTION]->(:QuestionAnswer) }
AND NOT EXISTS { (t)-[:HAS_FULL_TEXT]->(:FullTranscriptText) }'''
queries = {
    'prepared': 'MATCH (t:Transcript)-[:HAS_PREPARED_REMARKS]->(b:PreparedRemark) WHERE ' + COHORT +
                ' RETURN t.id AS tid,t.speakers AS speakers,b.id AS id,b.content AS content ORDER BY tid,id',
    'qa': 'MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(b:QAExchange) WHERE ' + COHORT +
          ' RETURN t.id AS tid,t.speakers AS speakers,b.id AS id,b.exchanges AS content ORDER BY tid,id'}
counts = defaultdict(Counter)
source_ids = defaultdict(set)
speaker_metadata = {}
hashes = {k: hashlib.sha256() for k in queries}
exceptions = []
examples = {}
started = time.monotonic()


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


load_env()
uri, user, password = get_neo4j_config()
with GraphDatabase.driver(uri, auth=(user, password)) as driver:
    with driver.session(default_access_mode=READ_ACCESS, fetch_size=500) as session:
        for kind, query in queries.items():
            for row in session.run(Query(query, timeout=300)):
                tid = row['tid']
                source_ids[kind].add(tid)
                counts[kind]['blocks'] += 1
                raw = row['content']
                hashes[kind].update((tid + '\0' + row['id'] + '\0' + str(raw) + '\n').encode())
                if tid not in speaker_metadata:
                    speaker_metadata[tid] = decoded(row['speakers'])
                speakers = speaker_metadata[tid]
                data = decoded(raw)
                if not isinstance(data, list):
                    raise ValueError('Cohort no longer has expected stored lists: ' + row['id'])
                for index, entry in enumerate(data):
                    text = entry['text'] if isinstance(entry, dict) else entry
                    if not isinstance(text, str):
                        raise ValueError('Non-text entry: ' + row['id'])
                    speaker = entry.get('speaker') if isinstance(entry, dict) else None
                    start, reason = body_start(text, speakers, speaker)
                    counts[kind]['utterances'] += 1
                    counts[kind][reason] += 1
                    before = [m for m in re.finditer(r'\S+', text) if any(c.isdecimal() for c in m[0])]
                    after = digit_tokens(text, speakers, speaker)
                    counts[kind]['numeric_questions_before'] += len(before)
                    counts[kind]['numeric_questions_after'] += len(after)
                    counts[kind]['question_reduction'] += len(before) - len(after)
                    assert all(text[x['start']:x['end']] == x['text'] for x in after)
                    if start:
                        assert text[start:] == spoken_text(json.dumps([entry]))
                        body_digits = {i for i in range(start, len(text)) if text[i].isdecimal()}
                        candidate_digits = {i for x in after for i in range(x['start'], x['end']) if text[i].isdecimal()}
                        assert body_digits == candidate_digits
                        counts[kind]['body_digits_preserved'] += len(body_digits)
                    else:
                        assert [(m.start(), m.end(), m[0]) for m in before] == [(x['start'], x['end'], x['text']) for x in after]
                        exceptions.append({'source': tid, 'block': row['id'], 'entry': index, 'reason': reason})
                    if reason not in examples:
                        examples[reason] = {'source': tid, 'block': row['id'], 'entry': index,
                                            'prefix': text[:min(start or 100, 160)], 'speaker': speaker}
            print(json.dumps({'finished': kind, 'counts': dict(counts[kind]), 'seconds': round(time.monotonic() - started, 2)}), flush=True)

report = {'checked_at': datetime.now(ZoneInfo('America/Toronto')).isoformat(),
          'seconds': time.monotonic() - started, 'sources': {k: len(v) for k, v in source_ids.items()},
          'source_sets_equal': source_ids['prepared'] == source_ids['qa'],
          'counts': {k: dict(v) for k, v in counts.items()},
          'stream_hashes': {k: v.hexdigest() for k, v in hashes.items()},
          'examples': examples, 'exceptions': exceptions,
          'queries': queries,
          'code_sha256': hashlib.sha256(pathlib.Path('/tmp/decider_claude_review_20261115/metadata_candidates.py').read_bytes()).hexdigest(),
          'scope': 'Candidate enumeration only. Model context and original source are unchanged. Model answers and end-to-end speed/accuracy are not measured here.'}
(OUT / 'live_audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
with (OUT.parent / 'progress.md').open('a') as f:
    f.write('\nTest: Read-only live audit of metadata-only candidate exclusion across the entire standard transcript cohort, using existing native header recognition and each source\'s speaker metadata.\n')
    f.write(f'Result: {report["sources"]}; {dict((k, dict(v)) for k, v in counts.items())}; all retained source offsets/body digits exact, every unverified header keeps original candidates. No model calls.\n')
    f.write('Next: Retain only the measured structural simplification; changed model grouping still needs validation in the final procedure, and semantic extraction gaps remain open.\n')
print(json.dumps({'report': str(OUT / 'live_audit.json'), 'seconds': report['seconds'], 'sources': report['sources'], 'exceptions': len(exceptions)}), flush=True)
