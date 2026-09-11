"""Read-only proof of the real 33-request key packet; no model calls."""
from collections import Counter, OrderedDict
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

A7 = Path(__file__).resolve().parents[1]
unit = A7 / 'unit_2017_final_source_key'
record_path = unit / 'PREPARED_FINAL_KEY_2017.core_final2017_real.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(record_path) == '7aee43a7e296e68f4dffec91ce3c3229e685cace93b91933a5eb84412a62de89'
record = json.loads(record_path.read_text())
mapping = unit / 'map_final_launch_2017.tsv'
assert sha(mapping) == 'a8654af2102a6f8c38b284c3f64cd0ffcf905ed48f94a537b4e0c6b868646274'
launch = mapping.read_text().splitlines()[-1].split('\t')[0]
os.environ.update(A7_PREP_RECORD=str(record_path), A7_PREP_MAP=str(mapping),
                  A7_LAUNCH_DIR=launch)
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_prepared_run as PR

# Re-execute the submitted read-only assertions, then add independent checks.
runpy.run_path(str(unit / 'verify_final_2017.py'), run_name='__main__')
import boundary as B
rows = B.read_map(str(mapping))
assert B.validate(rows) == []
base_rows = B.read_map(str(A7 / 'unit_2015_real_reviews/map_real_launch_2015.tsv'))
base = {r['logical']: r for r in base_rows}
actual = {r['logical']: r for r in rows}
assert len(rows) == len(actual) == len(base_rows) + 3
review_run, review_pkg = record['review_run'], record['review_package']
output_root = str(Path(review_run).parent)
assert set(actual) - set(base) == {review_run, review_pkg, launch}
for logical, row in base.items():
    want = dict(row)
    if logical == output_root:
        want['source'] = str(unit / 'key_closure')
    assert actual[logical] == want, logical
for logical in (review_run, review_pkg, launch):
    assert actual[logical]['mode'] == 'ro'

SK, K, HR, F = R.SK, R.K, R.HR, R.F
pkg, run = record['package'], record['run']
receipt = json.loads((Path(run) / K.RECEIPT_NAME).read_text())
inventory = json.loads(Path(R.INV.INV).read_text())['records']
plan = json.loads(Path(SK.PLAN_PATH).read_text())
grouped = OrderedDict()
for index, row in enumerate(inventory):
    grouped.setdefault(row['source_id'], []).append((index, row))
assert len(inventory) == len(plan['packets']) == 191
assert len(plan['events']) == 36 and len(grouped) == 33
assert len({e['source_id'] for e in plan['events']}) == 36
assert [p['source_id'] for p in plan['packets']] == [r['source_id'] for r in inventory]
no_rows = [e['source_id'] for e in plan['events'] if e['source_id'] not in grouped]
assert no_rows == record['counts']['events_with_no_located_row']
assert record['call_order'] == receipt['allowed'] == list(grouped)
assert [i['label'] for i in record['invocations']] == list(grouped)

raw_root = Path(os.path.abspath(K.a3_run_dirs()[0]))
answer_paths = sorted(p for base in (raw_root, raw_root / 'retry')
                      for p in (base / 'raw').glob('*') if p.is_file())
assert len(answer_paths) == 2 * len(inventory) == 382
answers = [p.read_text() for p in answer_paths]
assert all(answers)
script_hashes, prompt_hashes, lead_ids = [], [], []
group_count = 0
with R.final_scope(review_run, review_pkg) as proof:
    assert receipt == SK.expected_receipt(run, package=pkg)
    assert SK.preflight(pkg)['problems'] == []
    tasks = list(SK.tasks())
    assert [t['source_id'] for t in tasks] == list(grouped)
    for task, inv in zip(tasks, record['invocations']):
        sid = task['source_id']
        prompt = SK.prompt(task)
        assert SK.prompt_problems(task) == [], sid
        assert prompt.startswith(SK.prompt_prefix())
        data = json.loads(prompt[len(SK.prompt_prefix()):])
        assert list(data) == ['menu', 'event', 'rows', 'groups', 'leads']
        source = K.source_input(sid)
        assert data['event'] == {k: source[k] for k in HR.EVENT_VIEW}
        display, back = K.a1_reader.readable_menu(source['menu_tokens'])
        assert data['menu'] == list(display)
        assert [K.a1_reader.restore_menu_pick(d, back) for d in display] == source['menu_tokens']
        wanted_rows, locations = [], OrderedDict()
        for row_index, (global_index, row) in enumerate(grouped[sid], 1):
            assert plan['packets'][global_index]['packet_id'] == task['rows'][row_index - 1]
            fields = {k: row[k] for k in ('proposed_record_kind', 'part_ref',
                                         'occurrence_in_part', 'quote', 'raw_label_or_claim')}
            wanted_rows.append(dict(row_index=row_index, **fields))
            locator = tuple(row[k] for k in ('part_ref', 'occurrence_in_part', 'quote'))
            locations.setdefault(locator, []).append(row_index)
        assert data['rows'] == wanted_rows
        wanted_groups = [{'member_row_indexes': v} for v in locations.values() if len(v) > 1]
        assert data['groups'] == wanted_groups
        group_count += len(wanted_groups)
        assert data['leads'] == proof['by_source'][sid] and len(data['leads']) == 2
        for lead in data['leads']:
            assert set(lead) == set(F.LEAD_KEYS)
            assert hashlib.sha256(lead['reply'].encode()).hexdigest() == lead['sha256']
            lead_ids.append(lead['lead_id'])
        assert not any(a in prompt for a in answers)
        expected = SK.render_launcher(task, attempt=1).encode()
        durable = Path(inv['scriptPath']).read_bytes()
        assert expected == durable == (Path(launch) / Path(inv['scriptPath']).name).read_bytes()
        assert hashlib.sha256(durable).hexdigest() == inv['script_sha256']
        assert len(durable) < K.TRANSPORT_LIMIT
        assert inv['attempt'] == 1 and inv['args'] is None
        ph = hashlib.sha256(prompt.encode()).hexdigest()
        assert receipt['prompts'][sid] == ph
        prompt_hashes.append(ph)
        script_hashes.append(inv['script_sha256'])
    assert group_count == 5 and len(lead_ids) == len(set(lead_ids)) == 66
    budget = SK.manifest()['budget']
    assert budget['before'] == 499
    assert budget['before'] + len(tasks) == 532
    assert budget['planned_signer'] == 1 and budget['after_planned'] == 533
    assert budget['worst_case_after'] == 567
    resume = SK.resume_plan(run, package=pkg)
    assert resume['allowed'] == resume['owed'] == list(grouped)
    assert resume['served'] == resume['never_repeat'] == resume['retryable'] == []
    assert dict(Counter(resume['outcomes'].values())) == {'missing': 33}
    assert resume['problems'] == [] and resume['finalized'] is False

# A receipt with no states alone is not proof of no prior call. Search the
# project's durable workflow records for every exact prepared script identity.
native_root = Path('/home/faisal/.claude/projects/-home-faisal-EventMarketDB')
scanned, prior = 0, []
for path in native_root.glob('*/workflows/*.json'):
    doc = json.loads(path.read_text())
    scanned += 1
    if isinstance(doc.get('script'), str):
        if hashlib.sha256(doc['script'].encode()).hexdigest() in script_hashes:
            prior.append(str(path))
assert scanned > 0 and prior == [], prior
a3 = PR._executed(str(raw_root))
assert a3 == {'run_digest': '460c543b82ec3c69be70b2eebec3df1311263ecf885d3a1215ddc8627ad08034',
              'run_files': 799}
print(json.dumps({'independent_packet_verified': True, 'binding_rows': len(rows),
                  'source_events': len(plan['events']), 'scheduled': len(grouped),
                  'inventory_rows': len(inventory), 'no_row_events': no_rows,
                  'locator_groups': group_count, 'review_leads': len(lead_ids),
                  'saved_answers_compared': len(answers), 'a3': a3,
                  'all_requests_enumerated': len(prompt_hashes),
                  'native_states_scanned': scanned, 'matching_prior_calls': prior,
                  'model_calls': 0, 'key_truth_approved': False}, indent=1))
