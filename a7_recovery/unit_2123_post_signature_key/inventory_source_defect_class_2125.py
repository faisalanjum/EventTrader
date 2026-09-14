"""MECHANICAL inventory of the live 33-source key. No meaning is judged here.

Codex SEQ 2125: code may enumerate structured fields and rows; every semantic
judgement is made by the reviewer against this output. So this file only
counts, copies and locates: it reads the current key through F's own parser,
lists each located target with the facts the key emitted for it, and copies a
fixed window of the SAME source part around each located quote so the reviewer
can read the adjacency itself.

It writes one JSON. It calls nothing, changes nothing and decides nothing.
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
    'current_key_candidate_2125', candidate,
    loader=SourceFileLoader('current_key_candidate_2125', candidate))
E.X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E.X)

OUT = E.A7 / 'unit_2123_post_signature_key' / os.environ['A7_TAG']
#: how much of the SAME part to copy on each side of a located quote. A fixed
#: window, never a search for something interesting.
WINDOW = 700
#: a numeric token: any run of digits, with optional grouping and decimals.
#: It RECOGNISES numerals so the reviewer can see how many a quote carries;
#: it decides nothing about what any of them mean.
NUMBER = re.compile(r'\d[\d,]*(?:\.\d+)?')


def _period(item):
    return collections.OrderedDict(
        (k, item.get(k)) for k in
        ('fiscal_year', 'fiscal_quarter', 'half', 'month', 'period_scope',
         'period_start_date', 'period_end_date', 'time_type',
         'sentinel_class') if item.get(k) is not None)


def _slot(item, name):
    v = item.get(name)
    return None if not isinstance(v, dict) else v.get('value')


def inventory(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    OUT.mkdir(parents=True)
    bound = G._approved_bound()
    request = G._read(str(E.A7 / 'unit_2020_codex_check'
                          / 'SOURCE_KEY_RECHECK_BINDINGS_2120.json'))
    two = [e['source_id'] for e in request['source_events']]
    run_id = E.saved['third_round']
    candidate_dir = E.result['notes']['candidate']
    findings = collections.OrderedDict()
    order = [t['source_id'] for t in F.event_tasks(bound.evidence)]
    for event in sorted(request['source_events'],
                        key=lambda e: order.index(e['source_id'])):
        sid = event['source_id']
        findings[sid] = [collections.OrderedDict(
            [('source_id', sid),
             ('raw_sha256', event['prior_source_raw_sha256']), ('row', row)])
            for row in event['original_task_ids']]
    next_bound = X.bind(bound, str(E.A7 / 'unit_2123_post_signature_key'
                                   / 'core_recheck2123_h/recheck_packet'))

    items = F.HR._items()
    kinds = {p: r['proposed_record_kind'] for p, r in F._inventory()}
    with X.successor_scope(next_bound, findings, run_id,
                           E.saved['third_by_event'], E.source_inputs,
                           E.chain, signature=candidate_dir):
        shards, raws, origins, bad = F.v6_shards(next_bound)
        assert not bad, bad
        rows = []
        for task in F.event_tasks(bound.evidence):
            sid = task['source_id']
            shard, sbad = F.read_shard(raws[sid], task,
                                       F.event_leads(next_bound, task))
            assert shard is not None, (sid, sbad[:1])
            src, _display, _back = F.HR._source(sid)
            parts = {p['part']: (p.get('content') or '')
                     for p in (src.get('text_parts') or [])}
            for n, packet in enumerate(task['rows']):
                item = items[packet]
                quote = item.get('quote') or ''
                part = item.get('part_ref')
                text = parts.get(part, '')
                at = text.find(quote) if quote else -1
                settled = (shard['rows'] or {}).get(packet) or {}
                facts = settled.get('facts') or []
                rows.append(collections.OrderedDict([
                    ('source_id', sid), ('event_index', task['event_index']),
                    ('row', packet), ('row_index', n + 1),
                    ('proposed_record_kind', kinds.get(packet)),
                    ('origin', origins[sid]),
                    ('final_outcome', (shard['outcomes'] or {}).get(packet)),
                    ('raw_label_or_claim', item.get('raw_label_or_claim')),
                    ('part_ref', part), ('quote', quote),
                    ('quote_numbers', NUMBER.findall(quote)),
                    ('quote_found_at', at),
                    ('source_before', text[max(0, at - WINDOW):at]
                     if at >= 0 else None),
                    ('source_after', text[at + len(quote):at + len(quote) + WINDOW]
                     if at >= 0 else None),
                    ('facts', [collections.OrderedDict([
                        ('fact_index', i), ('fact_type', f.get('fact_type')),
                        ('driver_name', (f.get('item') or {}).get('driver_name')),
                        ('driver_state', (f.get('item') or {}).get('driver_state')),
                        ('level_low', _slot(f.get('item') or {}, 'level_low')),
                        ('level_high', _slot(f.get('item') or {}, 'level_high')),
                        ('level_unit', (f.get('item') or {}).get('level_unit')),
                        ('comparison_low', _slot(f.get('item') or {}, 'comparison_low')),
                        ('comparison_high', _slot(f.get('item') or {}, 'comparison_high')),
                        ('comparison_baseline', (f.get('item') or {}).get('comparison_baseline')),
                        ('slice_parts', (f.get('item') or {}).get('slice_parts')),
                        ('measurement_raw_spans', (f.get('item') or {}).get('measurement_raw_spans')),
                        ('period', _period(f.get('item') or {}))])
                        for i, f in enumerate(facts)]),
                    ('abstentions', len(settled.get('abstentions') or []))]))

    reported = [r for r in rows
                for f in r['facts']
                if f['fact_type'] == 'metric' and f['driver_state'] == 'reported']
    reported = [r for i, r in enumerate(reported) if r not in reported[:i]]
    # STRUCTURAL only: a located quote carrying more numerals than the facts
    # the key emitted for it. This selects rows for the reviewer to READ; it
    # asserts nothing about what any numeral means.
    multi = [r for r in rows
             if len(r['quote_numbers']) > max(1, len(r['facts']))]
    doc = collections.OrderedDict([
        ('scope', 'mechanical inventory of the live 33-source key; no meaning '
                  'judged here'),
        ('caller_sha256', G._sha_file(__file__)),
        ('owner_sha256', G._sha_file(X.__file__)),
        ('key_sources', len(shards)), ('rows_total', len(rows)),
        ('window_chars_each_side', WINDOW),
        ('the_two_rechecked_events', two),
        ('counts', collections.OrderedDict([
            ('rows', len(rows)),
            ('facts', sum(len(r['facts']) for r in rows)),
            ('rows_by_outcome', collections.OrderedDict(sorted(
                collections.Counter(r['final_outcome'] for r in rows).items()))),
            ('facts_by_type', collections.OrderedDict(sorted(
                collections.Counter(f['fact_type'] for r in rows
                                    for f in r['facts']).items()))),
            ('metric_states', collections.OrderedDict(sorted(
                collections.Counter(f['driver_state'] for r in rows
                                    for f in r['facts']
                                    if f['fact_type'] == 'metric').items()))),
            ('rows_with_a_reported_metric', len(reported)),
            ('rows_with_more_numerals_than_facts', len(multi)),
            ('quotes_not_found_in_their_part',
             len([r for r in rows if r['quote_found_at'] < 0]))])),
        ('reported_metric_rows', reported),
        ('multi_numeral_rows', multi)])
    G._write_new(str(OUT / 'SOURCE_DEFECT_INVENTORY_2125.json'),
                 G._pretty(doc) + '\n')
    print('SOURCE_DEFECT_INVENTORY_2125', json.dumps(doc['counts']), flush=True)
    print('sha256', G._sha_file(str(OUT / 'SOURCE_DEFECT_INVENTORY_2125.json')),
          flush=True)
    return doc


E.with_prepared_inputs(inventory)
