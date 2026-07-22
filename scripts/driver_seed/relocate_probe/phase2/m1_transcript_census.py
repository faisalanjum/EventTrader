"""PHASE-2 M1b: transcript numeric-occurrence census by source-native block.

Counts numeric occurrences in every nonblank PreparedRemark and QAExchange block
(the lawful reader blocks) — no sentence parsing, structure only. Read-only.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m1_transcript_census.py
"""
import json
import os
import re
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_HERE, 'm1_transcript_census.json')
NUM = re.compile(r'(?<![\w])\$?\d[\d,]*\.?\d*%?')
SPEAKER = re.compile(r'^[^:]{0,120}?\[\d+\]:\s*')      # the ANCHORED
                                             # 'Speaker Name [offset]: ' prefix —
                                             # stripped per utterance (names may
                                             # carry digits, e.g. 'Operator 1');
                                             # in-speech [n] citations stay


def spoken_text(raw):
    """Parse the stored JSON block and return ONLY spoken words: each utterance
    loses its complete anchored speaker prefix (name + [offset] + colon)."""
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        data = raw
    parts = []
    for item in (data if isinstance(data, list) else [data]):
        text = str(item.get('text', '')) if isinstance(item, dict) else str(item)
        parts.append(SPEAKER.sub('', text))
    return ' '.join(parts)


def main():
    from dotenv import dotenv_values
    from neo4j import GraphDatabase
    cfg = dotenv_values(os.path.join(_HERE, '..', '..', '..', '..', '.env'))
    drv = GraphDatabase.driver(cfg['NEO4J_URI'],
                               auth=(cfg['NEO4J_USERNAME'], cfg['NEO4J_PASSWORD']))
    t0 = time.time()
    stats = {}
    with drv.session() as s:
        for label, q, field in (
            ('prepared_remarks',
             "MATCH (p:PreparedRemark) WHERE p.content IS NOT NULL "
             "AND trim(p.content) <> '' RETURN p.content AS t", 't'),
            ('qa_exchanges',
             "MATCH (q:QAExchange) WHERE q.exchanges IS NOT NULL "
             "RETURN toString(q.exchanges) AS t", 't'),
        ):
            blocks = numeric_blocks = occurrences = chars = 0
            for rec in s.run(q):
                text = spoken_text(rec[field] or '')
                if not text.strip():
                    continue
                blocks += 1
                chars += len(text)
                n = len(NUM.findall(text))
                occurrences += n
                if n:
                    numeric_blocks += 1
            stats[label] = {'blocks': blocks, 'numeric_blocks': numeric_blocks,
                            'numeric_occurrences': occurrences,
                            'total_chars': chars}
    drv.close()
    out = {'label': 'M1b transcript numeric census (source-native blocks)',
           'stats': stats, 'secs': round(time.time() - t0)}
    json.dump(out, open(OUT, 'w'), indent=1)
    print('M1B-DONE', json.dumps(out), flush=True)


if __name__ == '__main__':
    main()
