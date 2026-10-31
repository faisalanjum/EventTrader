"""The worker seam: the REAL enrich_worker loop of this checkout's redisDB/report_enricher.py (or ENRICHER_UNDER_TEST), run by worker_harness.py
with recording fakes. Needs the worker's environment (redis-py), e.g. the report-enricher image."""
import importlib.util, json, os, subprocess, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENRICHER = os.environ.get('ENRICHER_UNDER_TEST', str(HERE.parents[1] / 'redisDB/report_enricher.py'))
EVENT = {'_original_prefix_type': 'live', '_raw_key': 'reports:live:raw:0001004434-23-000015', 'accessionNo': '0001004434-23-000015',
         'cik': '1004434', 'formType': '8-K', 'primaryDocumentUrl': 'https://www.sec.gov/x.htm', 'items': ['2.02']}
PKEY = 'reports:live:processed:0001004434-23-000015'


def run(events=(EVENT,), existing=None, legacy_raises=False, configured=True):
    p = subprocess.run([sys.executable, '-B', str(HERE / 'worker_harness.py'), ENRICHER,
                        json.dumps(dict(events=list(events), existing=existing or {}, legacy_raises=legacy_raises, configured=configured))],
                       capture_output=True, text=True, env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}, cwd=str(HERE))
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


def names(log): return [e[0] if e[0] != 'legacy' else e[1] for e in log if e[0] not in ('claim', 'lrem', 'hdel', 'rpush', 'execute', 'set_retry')]


@unittest.skipUnless(importlib.util.find_spec('redis'), 'needs the worker environment (redis-py)')
class WorkerOrder(unittest.TestCase):
    def test_extraction_starts_before_any_legacy_heavy_work(self):
        n = names(run())
        self.assertEqual(n[:2], ['pointer', '_extract_sections'], n)

    def test_legacy_failure_cannot_prevent_extraction_and_keeps_the_existing_failure_path(self):
        log = run(legacy_raises=True); n = names(log)
        self.assertEqual(n[:2], ['pointer', '_extract_sections'], n)
        self.assertIn(['lpush', 'failed_queue', EVENT['_raw_key']], log); self.assertNotIn('set', n)  # no processed record, as today
        self.assertEqual([e[2]['item'] for e in log if e[0] == 'rpush'], [json.dumps(EVENT)])  # full input kept

    def test_processed_record_contract_unchanged_plus_one_key(self):
        log = run(); sets = [e for e in log if e[0] == 'set']
        self.assertEqual(len(sets), 1); rec = sets[0][2]
        self.assertEqual((rec['enriched'], rec['extracted_sections'], rec['prepared_extraction']['status']), (True, {'s': 1}, 'complete'))
        self.assertIn(['lpush', 'processed_queue', PKEY], log); self.assertIn(['publish', 'channel', PKEY], log)
        tx = log[log.index(sets[0]):]; self.assertLess(tx.index(['lrem', 'enrich:processing']), tx.index(['execute']))  # finished in the same transaction

    def test_not_configured_is_the_old_path(self):
        n = names(run(configured=False))
        self.assertNotIn('pointer', n); self.assertEqual(n[0], '_extract_sections')
        self.assertTrue(all('prepared_extraction' not in e[2] for e in run(configured=False) if e[0] == 'set'))

    def test_skip_only_when_prepared_product_done(self):
        done = {PKEY: {'enriched': True, 'prepared_extraction': {'status': 'complete'}}}
        failed = {PKEY: {'enriched': True, 'prepared_extraction': {'status': 'failed'}}}
        self.assertEqual(names(run(existing=done)), [])  # skipped: nothing called
        self.assertEqual(names(run(existing=failed))[:2], ['pointer', '_extract_sections'])  # reprocessed
        self.assertEqual(names(run(existing=done, configured=False)), [])  # unconfigured: today's enriched skip


if __name__ == '__main__':
    unittest.main()
