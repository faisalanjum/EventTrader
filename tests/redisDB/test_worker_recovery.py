"""Worker crash recovery against a REAL Redis 7.4.4 (REDIS_TEST_PORT): the real enrich_worker loop, SIGKILL of the whole worker process group.
RED = the previous worker (ENRICHER_OLD, e.g. b36aa7d2) loses a payload killed mid-work; GREEN = the fix keeps, finishes or retires it.
DISPOSABLE Redis only: every test runs FLUSHALL. Runs only when REDIS_TEST_PORT (and REDIS_TEST_HOST, default localhost) name a throwaway test server.
Needs the worker's environment (redis-py), e.g. the report-enricher image."""
import json, os, signal, subprocess, sys, time, unittest
from pathlib import Path
try:
    import redis
except ImportError:
    redis = None

HERE = Path(__file__).resolve().parent
NEW = os.environ.get('ENRICHER_UNDER_TEST', str(HERE.parents[1] / 'redisDB/report_enricher.py'))
OLD = os.environ.get('ENRICHER_OLD')  # the previous worker file, for the RED proof and the rollback test only
PORT = int(os.environ['REDIS_TEST_PORT']) if os.environ.get('REDIS_TEST_PORT') else None; HOST = os.environ.get('REDIS_TEST_HOST', 'localhost')
CONSTANTS = os.environ.get('REDIS_CONSTANTS', str(HERE.parents[1] / 'redisDB/redis_constants.py'))  # the real queue names
Q, PROC, DEAD, DELIV = 'reports:queues:enrich', 'reports:queues:enrich:processing', 'reports:queues:enrich:dead', 'reports:queues:enrich:deliveries'
PKEY, DONEQ, FAILQ = 'reports:live:processed:0001004434-23-000015', 'reports:queues:processed', 'reports:queues:failed'
EVENT = {'_original_prefix_type': 'live', '_raw_key': 'reports:live:raw:0001004434-23-000015', 'accessionNo': '0001004434-23-000015',
         'cik': '1004434', 'formType': '8-K', 'primaryDocumentUrl': 'https://www.sec.gov/x.htm', 'items': ['2.02']}
r = redis.Redis(host=HOST, port=PORT, decode_responses=True) if redis and PORT else None


def run(enricher, configured=True, crash=None, times=0, settle=2.0, limit=30):
    """Start one worker in its own process group; return its exit code (-9 = killed itself) or None if it went idle (then stopped)."""
    p = subprocess.Popen([sys.executable, '-B', str(HERE / 'redis_harness.py'), enricher,
                          json.dumps(dict(host=HOST, port=PORT, constants=CONSTANTS, configured=configured, crash=crash, times=times))],
                         start_new_session=True, env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}, cwd=str(HERE),
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    end, idle_since = time.time() + limit, None
    while time.time() < end:
        if p.poll() is not None: p.stderr.close(); return p.returncode
        idle = r.llen(Q) == 0 and r.llen(PROC) == 0
        idle_since = (idle_since or time.time()) if idle else None
        if idle_since and time.time() - idle_since > settle: break
        time.sleep(0.05)
    alive = p.poll() is None
    os.killpg(p.pid, signal.SIGTERM); p.wait(10); err = p.stderr.read(); p.stderr.close()
    assert alive, err[-2000:]
    return None


def push(event=EVENT):
    item = json.dumps(event); r.rpush(Q, item); return item


def calls(kind): return r.lrange('test:calls', 0, -1).count(kind)


@unittest.skipUnless(r is not None, 'needs a DISPOSABLE Redis (REDIS_TEST_PORT) and redis-py')
class Recovery(unittest.TestCase):
    def setUp(self): r.flushall()

    @unittest.skipUnless(OLD, 'needs ENRICHER_OLD (the previous worker file)')
    def test_red_current_worker_loses_a_payload_killed_mid_work(self):
        push()
        self.assertEqual(run(OLD, crash='legacy_kill', times=1), -signal.SIGKILL)
        self.assertIsNone(run(OLD))
        self.assertEqual((r.exists(PKEY), r.llen(Q), r.llen(FAILQ)), (0, 0, 0))  # gone: no result, no queue copy, no failure record

    def test_positive_control_success_is_acked_in_the_same_transaction(self):
        push(); self.assertIsNone(run(NEW))
        self.assertEqual((r.exists(PKEY), r.llen(DONEQ), r.llen(PROC), r.hlen(DELIV), r.llen(DEAD)), (1, 1, 0, 0, 0))
        self.assertEqual(json.loads(r.get(PKEY))['prepared_extraction']['status'], 'complete')
        self.assertEqual(calls('retries:0'), 1)  # native resend off (production default would be 1)
        self.assertEqual(calls('clear_on_init:False'), 1)  # a (re)starting worker never wipes the producer's raw items (also unconfigured: test_unconfigured_never_wipes)

    def test_kill_after_claim_before_publication_resumes_exactly_once(self):
        push()
        self.assertEqual(run(NEW, crash='legacy_kill', times=1), -signal.SIGKILL)
        self.assertEqual((r.llen(PROC), r.exists(PKEY)), (1, 0))  # kept while the worker is down
        self.assertIsNone(run(NEW, crash='legacy_kill', times=1))
        self.assertEqual((r.exists(PKEY), r.llen(DONEQ), r.llen(PROC), r.hlen(DELIV), r.llen(DEAD), calls('pointer')), (1, 1, 0, 0, 0, 2))

    def test_kill_right_after_publication_is_not_reprocessed(self):
        push()
        self.assertEqual(run(NEW, crash='after_exec_kill', times=1), -signal.SIGKILL)
        self.assertIsNone(run(NEW, crash='after_exec_kill', times=1))
        self.assertEqual((r.exists(PKEY), r.llen(DONEQ), r.llen(PROC), r.llen(DEAD), calls('pointer')), (1, 1, 0, 0, 1))

    def test_killed_on_every_delivery_is_retired_after_three_with_full_input_and_no_spin(self):
        item = push()
        for _ in range(3): self.assertEqual(run(NEW, crash='legacy_kill', times=99), -signal.SIGKILL)
        self.assertIsNone(run(NEW, crash='legacy_kill', times=99))  # 4th start retires it at reclaim, then idles
        self.assertIsNone(run(NEW, crash='legacy_kill', times=99))  # and stays idle
        dead = [json.loads(x) for x in r.lrange(DEAD, 0, -1)]
        self.assertEqual([d['item'] for d in dead], [item]); self.assertIn('3 deliveries', dead[0]['reason'])
        self.assertEqual((r.exists(PKEY), r.llen(Q), r.llen(PROC), r.hlen(DELIV), calls('pointer')), (0, 0, 0, 0, 3))

    def test_handled_failure_is_terminal_with_full_input_and_worker_continues(self):
        item = push(); second = push(dict(EVENT, _raw_key='reports:live:raw:0000000000-00-000002', accessionNo='0000000000-00-000002'))
        self.assertIsNone(run(NEW, crash='legacy_raise'))  # stays alive through both failures
        dead = [json.loads(x) for x in r.lrange(DEAD, 0, -1)]
        self.assertEqual([d['item'] for d in dead], [item, second]); self.assertTrue(dead[0]['reason'].startswith('RuntimeError'))
        self.assertEqual(r.lrange(FAILQ, 0, -1), ['reports:live:raw:0000000000-00-000002', EVENT['_raw_key']])  # legacy record kept
        self.assertEqual((r.exists(PKEY), r.llen(PROC), r.hlen(DELIV)), (0, 0, 0))

    def test_missing_routing_fields_is_terminal_not_discarded(self):
        item = push({k: v for k, v in EVENT.items() if k != '_raw_key'})
        self.assertIsNone(run(NEW))
        self.assertEqual([json.loads(x)['item'] for x in r.lrange(DEAD, 0, -1)], [item]); self.assertEqual(r.llen(PROC), 0)

    def test_already_done_is_acked_without_work(self):
        r.set(PKEY, json.dumps({'enriched': True, 'prepared_extraction': {'status': 'complete'}})); push()
        self.assertIsNone(run(NEW))
        self.assertEqual((r.llen(PROC), r.llen(DEAD), calls('pointer'), calls('legacy')), (0, 0, 0, 0))

    def test_unconfigured_never_wipes_raw_items(self):
        self.assertIsNone(run(NEW, configured=False)); self.assertEqual(calls('clear_on_init:False'), 1)

    @unittest.skipUnless(OLD, 'needs ENRICHER_OLD (the previous worker file)')
    def test_rollback_returns_a_pending_payload_to_the_old_worker(self):
        push()
        self.assertEqual(run(NEW, crash='legacy_kill', times=1), -signal.SIGKILL)
        while r.lmove(PROC, Q, 'RIGHT', 'LEFT'): pass  # the rollback step, before the old worker starts
        self.assertIsNone(run(OLD, configured=False))
        self.assertEqual((r.exists(PKEY), r.llen(Q), r.llen(PROC)), (1, 0, 0))


    def test_lost_claim_reply_stops_with_one_reservation_then_resumes(self):
        push(); push(dict(EVENT, _raw_key='reports:live:raw:0000000000-00-000002', accessionNo='0000000000-00-000002'))
        self.assertEqual(run(NEW, crash='claim_lost_reply', times=1), 1)  # stops: no second claim, no failure record
        self.assertEqual((r.llen(PROC), r.llen(Q), r.llen(DEAD), r.llen(FAILQ)), (1, 1, 0, 0))
        self.assertIsNone(run(NEW))
        self.assertEqual((r.exists(PKEY), r.exists('reports:live:processed:0000000000-00-000002'), r.llen(DONEQ), r.llen(PROC), r.llen(DEAD)), (1, 1, 2, 0, 0))

    def test_lost_publication_reply_stops_and_is_not_reprocessed(self):
        push()
        self.assertEqual(run(NEW, crash='exec_lost_reply', times=1), 1)
        self.assertEqual((r.llen(PROC), r.llen(DONEQ), r.llen(DEAD)), (0, 1, 0))  # committed with its ack
        self.assertIsNone(run(NEW))
        self.assertEqual((r.llen(DONEQ), calls('pointer'), r.llen(DEAD)), (1, 1, 0))

    def test_unsent_publication_stops_and_resumes_once(self):
        push()
        self.assertEqual(run(NEW, crash='exec_not_sent', times=1), 1)
        self.assertEqual((r.llen(PROC), r.exists(PKEY), r.llen(DEAD), r.llen(FAILQ)), (1, 0, 0, 0))
        self.assertIsNone(run(NEW))
        self.assertEqual((r.exists(PKEY), r.llen(DONEQ), r.llen(PROC), r.llen(DEAD), calls('pointer')), (1, 1, 0, 0, 2))

    def test_failed_prepared_extraction_hands_over_full_input_with_the_published_result(self):
        item = push()
        self.assertIsNone(run(NEW, crash='pointer_failed'))
        handed = [json.loads(x) for x in r.lrange(DEAD, 0, -1)]
        self.assertEqual([h['item'] for h in handed], [item]); self.assertIn('legacy result published): package: OSError', handed[0]['reason'])
        self.assertEqual(json.loads(r.get(PKEY))['prepared_extraction']['status'], 'failed')
        self.assertEqual((r.llen(DONEQ), r.llen(PROC), r.hlen(DELIV)), (1, 0, 0))  # legacy publication not blocked


    def test_lost_skip_ack_reply_stops_without_a_second_publication(self):
        r.set(PKEY, json.dumps({'enriched': True, 'prepared_extraction': {'status': 'complete'}})); push()
        self.assertEqual(run(NEW, crash='skip_ack_lost_reply', times=1), 1)
        self.assertIsNone(run(NEW))
        self.assertEqual((r.llen(DONEQ), r.llen(PROC), r.llen(DEAD), calls('pointer'), calls('legacy')), (0, 0, 0, 0, 0))

    def test_empty_claimed_payload_is_terminal_not_pending_forever(self):
        r.rpush(Q, '')
        self.assertIsNone(run(NEW))
        self.assertEqual(([json.loads(x)['item'] for x in r.lrange(DEAD, 0, -1)], r.llen(PROC)), ([''], 0))


if __name__ == '__main__':
    unittest.main()
