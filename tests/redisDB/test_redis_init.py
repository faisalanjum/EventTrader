"""The REAL EventTraderRedis initializer (this checkout's redisDB/redisClasses.py) against a DISPOSABLE Redis: raw items survive clear_on_init=False;
the default still wipes them. Every test runs FLUSHALL, so it runs only when REDIS_TEST_PORT (and REDIS_TEST_HOST, default localhost) name a throwaway
test server; the initializer is pointed at that server through its own REDIS_HOST/REDIS_PORT settings. Needs the worker's environment (redis-py)."""
import os, unittest
try:
    import redis
except ImportError:
    redis = None

PORT, HOST = os.environ.get('REDIS_TEST_PORT'), os.environ.get('REDIS_TEST_HOST', 'localhost')
r = redis.Redis(host=HOST, port=int(PORT), decode_responses=True) if redis and PORT else None
RAW = ('reports:live:raw:0001004434-23-000015.x', 'reports:hist:raw:0001004434-23-000015.x')


@unittest.skipUnless(r is not None, 'needs a DISPOSABLE Redis (REDIS_TEST_PORT) and redis-py')
class Init(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['REDIS_HOST'], os.environ['REDIS_PORT'] = HOST, PORT  # the initializer's own settings -> the test server only
        global EventTraderRedis
        from redisDB.redisClasses import EventTraderRedis

    def setUp(self):
        r.flushall(); [r.set(k, '{"sentinel": 1}') for k in RAW]; r.set('reports:live:processed:keep', '1')

    def test_worker_start_keeps_raw_items(self):
        EventTraderRedis(source='reports', clear_on_init=False)
        self.assertEqual([r.exists(k) for k in RAW], [1, 1])

    def test_default_start_still_wipes_raw_items_as_today(self):  # negative control: the wipe is real and unchanged for other callers
        EventTraderRedis(source='reports')
        self.assertEqual([r.exists(k) for k in RAW] + [r.exists('reports:live:processed:keep')], [0, 0, 1])


if __name__ == '__main__':
    unittest.main()
