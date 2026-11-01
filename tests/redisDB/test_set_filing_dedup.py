"""set_filing dedup: only a filing confirmed in Neo4j is skipped (d84dad2); a processed-list entry alone must not block it.

No Redis server: a minimal in-memory client stands in for redis-py, and the lifecycle helpers are stubbed.
Run: env -u PYTHONPATH venv/bin/python -B -m unittest tests.redisDB.test_set_filing_dedup -v
"""
import logging
from itertools import product
import unittest
from unittest.mock import Mock, patch

try:
    import redis
except ImportError:
    redis = None

if redis is not None:
    from redisDB.redisClasses import RedisClient
else:  # The Prepare-only environment may not include redis-py.
    RedisClient = None

ACC, FILED = "0000320193-26-000006", "2026-01-30T16:30:00-05:00"
PREFIX = "reports:hist:"
PROCESSED = "reports:queues:processed"
RAW = "reports:queues:raw"
STAMP = FILED.replace(":", ".")


class FakeRedis:
    def __init__(self, lists=None, sets=None):
        self.lists, self.sets, self.kv = lists or {}, sets or {}, {}

    def lrange(self, key, start, end):
        return list(self.lists.get(key, []))

    def sismember(self, key, member):
        return member in self.sets.get(key, set())

    def pipeline(self, transaction=True):
        return FakePipe(self)


class FakePipe:
    def __init__(self, r):
        self.r, self.ops = r, []

    def set(self, key, value, ex=None):
        self.ops.append(lambda: self.r.kv.__setitem__(key, value) or True)
        return self

    def lpush(self, key, value):
        self.ops.append(lambda: self.r.lists.setdefault(key, []).insert(0, value) or 1)
        return self

    def execute(self):
        return [op() for op in self.ops]


class Filing:
    accessionNo = ACC

    def __init__(self, filed_at=FILED):
        self.filedAt = filed_at

    def model_dump_json(self):
        return "{}"


def client(fake, prefix=PREFIX):
    c = object.__new__(RedisClient)
    c.client, c.prefix, c.source_type = fake, prefix, "reports"
    c.PROCESSED_QUEUE, c.RAW_QUEUE, c.logger, c.pool = PROCESSED, RAW, logging.getLogger("test"), None
    c.mark_lifecycle_timestamp = lambda *a, external_pipe=None, **k: external_pipe
    c.set_lifecycle_data = lambda *a, external_pipe=None, **k: external_pipe
    return c


@unittest.skipUnless(RedisClient is not None, 'needs redis-py and the redisDB import chain (e.g. the repo venv or the worker image)')
class SetFilingDedup(unittest.TestCase):
    def test_processed_list_entry_alone_does_not_block(self):
        for prefix, filed_at, processed, confirmed in product(
            ("reports:hist:", "reports:live:"), (FILED, "2026-01-30T21:30:00Z"),
            (False, True), (set(), {"0001004434-23-000015"}),
        ):
            with self.subTest(prefix=prefix, filed_at=filed_at, processed=processed, confirmed=confirmed):
                stamp = filed_at.replace(":", ".")
                entries = [f"{prefix}processed:{ACC}.{stamp}"] if processed else []
                fake = FakeRedis(lists={PROCESSED: entries}, sets={"reports:confirmed_in_neo4j": confirmed})
                self.assertTrue(client(fake, prefix).set_filing(Filing(filed_at)))
                self.assertEqual(fake.kv, {f"{prefix}raw:{ACC}.{stamp}": "{}"})
                self.assertEqual(fake.lists[RAW], [f"{prefix}raw:{ACC}.{stamp}"])

    def test_filing_confirmed_in_neo4j_is_skipped(self):
        for prefix, filed_at, processed in product(
            ("reports:hist:", "reports:live:"), (FILED, "2026-01-30T21:30:00Z"), (False, True),
        ):
            with self.subTest(prefix=prefix, filed_at=filed_at, processed=processed):
                stamp = filed_at.replace(":", ".")
                entries = [f"{prefix}processed:{ACC}.{stamp}"] if processed else []
                fake = FakeRedis(lists={PROCESSED: entries}, sets={"reports:confirmed_in_neo4j": {ACC}})
                self.assertFalse(client(fake, prefix).set_filing(Filing(filed_at)))
                self.assertEqual(fake.kv, {})
                self.assertNotIn(RAW, fake.lists)

    def test_lookup_failure_retries_without_accepting_an_unchecked_filing(self):
        for last, accepted in ((False, True), (True, False), (redis.ConnectionError("offline"), False)):
            with self.subTest(last=last):
                fake = FakeRedis()
                fake.sismember = Mock(side_effect=[redis.ConnectionError("offline"), redis.ConnectionError("offline"), last])
                with patch("redisDB.redisClasses.redis.Redis", return_value=fake), \
                     patch("redisDB.redisClasses.time.sleep"), self.assertLogs("test", level="ERROR"):
                    self.assertEqual(client(fake).set_filing(Filing()), accepted)
                self.assertEqual(fake.sismember.call_count, 3)
                self.assertEqual(fake.lists.get(RAW, []), [f"{PREFIX}raw:{ACC}.{STAMP}"] if accepted else [])
                self.assertEqual(bool(fake.kv), accepted)


if __name__ == "__main__":
    unittest.main()
