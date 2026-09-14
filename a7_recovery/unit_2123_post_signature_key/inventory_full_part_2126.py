"""The SAME 35 reported-metric rows, over the COMPLETE supplied source parts.

Codex SEQ 2126 item 3: the 700-character window of the 2125 inventory is an
honest limitation, not authority. So this reads each row's whole part and hands
the reviewer every sentence of it that shares a word with that row's own target
label or driver name.

It DECIDES NOTHING. There is no direction vocabulary, no adjacency score and no
threshold that removes a sentence from view: the search terms are the row's own
`raw_label_or_claim` and `driver_name`, taken from the data, and the ranking
only chooses the order the reviewer reads in. Every sentence that shares a term
is emitted, and the count is reported so nothing can be silently dropped.
"""
import collections
import json
import os
import re
import sys
from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E                              # noqa: E402

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
_spec = importlib.util.spec_from_file_location(
    'current_key_candidate_2126', candidate,
    loader=SourceFileLoader('current_key_candidate_2126', candidate))
E.X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E.X)

OUT = E.A7 / 'unit_2123_post_signature_key' / os.environ['A7_TAG']
PRIOR = (E.A7 / 'unit_2123_post_signature_key/core_inv2125_a'
         / 'SOURCE_DEFECT_INVENTORY_2125.json')
PRIOR_SHA256 = '16fa94663269fdcab94b2c15de43cb236234328120c5de4d12d84cff93f18e26'
#: a word of the row's own label; the only terms searched for
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]+")
#: sentence-ish boundaries. Splitting only decides where a snippet starts and
#: ends, never whether the reviewer sees it.
SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
CLEAN = re.compile(r'[​\s]+')


def _terms(row, drivers):
    """The row's OWN words: its located label plus its driver names."""
    text = ' '.join([row['raw_label_or_claim'] or ''] +
                    [(d or '').replace('_', ' ') for d in drivers])
    return sorted({w.lower() for w in WORD.findall(text)})


def _value_forms(f):
    """How the SOURCE could write this fact's own stored numbers.

    Derived from the fact's own level slots - no list, no pattern guess: the
    digits with and without thousands grouping, unsigned, because accounting
    notation writes a negative as parentheses.
    """
    out = set()
    for slot in ('level_low', 'level_high'):
        v = f.get(slot)
        if v is None:
            continue
        # the stored slot is an exact Decimal, serialized as a string
        try:
            n = abs(float(v))
        except (TypeError, ValueError):
            continue
        whole = int(n) if float(n) == int(n) else None
        for form in ([str(whole), '{:,}'.format(whole)] if whole is not None
                     else [('%g' % n)]):
            out.add(form)
    return sorted(out)


def _sentences(text):
    out = []
    for piece in SPLIT.split(text or ''):
        s = CLEAN.sub(' ', piece).strip()
        if s:
            out.append(s)
    return out


def build(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    OUT.mkdir(parents=True)
    assert G._sha_file(str(PRIOR)) == PRIOR_SHA256
    prior = G._read(str(PRIOR))
    bound = G._approved_bound()
    rows = []
    for r in prior['reported_metric_rows']:
        sid = r['source_id']
        src, _display, _back = F.HR._source(sid)
        parts = {p['part']: (p.get('content') or '')
                 for p in (src.get('text_parts') or [])}
        part = parts.get(r['part_ref'], '')
        drivers = [f['driver_name'] for f in r['facts']
                   if f['fact_type'] == 'metric' and f['driver_state'] == 'reported']
        terms = _terms(r, drivers)
        quote = CLEAN.sub(' ', r['quote']).strip()
        hits = []
        for n, s in enumerate(_sentences(part)):
            low = s.lower()
            shared = [t for t in terms if t in low]
            if shared:
                hits.append(collections.OrderedDict([
                    ('n', n), ('shared', len(shared)), ('terms', shared),
                    ('text', s)]))
        hits.sort(key=lambda h: (-h['shared'], h['n']))
        # EVERY line of the part that carries this fact's own stored number.
        # A comparative table line states the value and its prior side by
        # side, so this finds the row's own table without naming a pattern.
        forms = sorted({v for f in r['facts']
                        if f['fact_type'] == 'metric'
                        and f['driver_state'] == 'reported'
                        for v in _value_forms(f)})
        value_lines = []
        for n, s in enumerate(_sentences(part)):
            carried = [v for v in forms if v in s]
            if carried:
                value_lines.append(collections.OrderedDict(
                    [('n', n), ('carries', carried), ('text', s)]))
        rows.append(collections.OrderedDict([
            ('source_id', sid), ('row', r['row']), ('row_index', r['row_index']),
            ('part_ref', r['part_ref']), ('part_chars', len(part)),
            ('raw_label_or_claim', r['raw_label_or_claim']),
            ('drivers', drivers),
            ('facts', r['facts']),
            ('quote', quote),
            ('search_terms', terms),
            ('sentences_in_part', len(_sentences(part))),
            ('sentences_sharing_a_term', len(hits)),
            ('value_forms', forms),
            ('lines_carrying_the_value', len(value_lines)),
            ('value_lines', value_lines),
            ('hits', hits)]))
    doc = collections.OrderedDict([
        ('scope', 'the same 35 reported-metric rows over their COMPLETE source '
                  'parts; a reading aid, no judgement'),
        ('caller_sha256', G._sha_file(__file__)),
        ('prior_inventory_sha256', PRIOR_SHA256),
        ('rows', len(rows)),
        ('totals', collections.OrderedDict([
            ('part_chars', sum(r['part_chars'] for r in rows)),
            ('sentences_in_parts', sum(r['sentences_in_part'] for r in rows)),
            ('sentences_sharing_a_term',
             sum(r['sentences_sharing_a_term'] for r in rows)),
            ('max_hits_for_one_row', max(r['sentences_sharing_a_term']
                                         for r in rows)),
            ('lines_carrying_the_value',
             sum(r['lines_carrying_the_value'] for r in rows))])),
        ('reported_metric_rows', rows)])
    G._write_new(str(OUT / 'FULL_PART_SEARCH_2126.json'), G._pretty(doc) + '\n')
    print('FULL_PART_SEARCH_2126', json.dumps(doc['totals']), flush=True)
    print('sha256', G._sha_file(str(OUT / 'FULL_PART_SEARCH_2126.json')),
          flush=True)
    return doc


E.with_prepared_inputs(build)
