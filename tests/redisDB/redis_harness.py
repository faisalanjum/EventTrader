"""Runs a report_enricher copy's REAL enrich_worker loop against a REAL Redis (test server), with the repo's REAL queue-name module.
Only the heavy work (ReportProcessor), the adapter pointer, logging and the lifecycle helper are fakes. Run in its own process group:
crash modes SIGKILL the WHOLE group. Usage: python -B redis_harness.py <enricher.py> '<json: port, configured, crash, times>'"""
import importlib.util, json, os, signal, sys, types
import redis

ENRICHER, ARGS = sys.argv[1], json.loads(sys.argv[2])
R = redis.Redis(host=ARGS['host'], port=ARGS['port'], decode_responses=True, retry_on_timeout=True, socket_timeout=30.0)  # production settings (redisClasses REDIS_CONN_SETTINGS)
MODE, TIMES = ARGS.get('crash'), ARGS.get('times', 0)


def crash_now():
    return R.incr('test:crashes') <= TIMES


def kill_group():
    os.killpg(os.getpgrp(), signal.SIGKILL)


def module(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m


class Client:
    def __init__(self): self.client = R
    def mark_lifecycle_timestamp(self, key, field, reason=None, ttl=None, external_pipe=None):
        pipe = external_pipe or R.pipeline(); pipe.hset(key, field, 'ts'); return pipe


class Env:
    def __init__(self, source, **k):
        R.rpush('test:calls', f"clear_on_init:{k.get('clear_on_init', True)}"); self.live_client = self.history_client = Client()


class Processor:
    def __init__(self, *a, **k): pass
    def _extract_sections(self, **k):
        retry = R.connection_pool.connection_kwargs.get('retry')  # set only by set_retry; absent = the library default from retry_on_timeout
        R.rpush('test:calls', 'legacy', f"retries:{retry._retries if retry else 'default'}")
        if MODE == 'legacy_kill' and crash_now(): kill_group()
        if MODE == 'legacy_raise': raise RuntimeError('legacy section extraction failed')
        return {'s': 1}
    def _extract_secondary_filing_content(self, url): return 'text'
    def _get_financial_statements(self, **k): return {}
    def _process_exhibits(self, ex): return {}


def pointer(filing, config_path):
    R.rpush('test:calls', 'pointer')
    if MODE == 'pointer_failed': return {'status': 'failed', 'reasons': ['package: OSError: no package'], 'receipt': None}
    return {'status': 'complete', 'receipt': None}


def prepared_done(record):
    return (record.get('prepared_extraction') or {}).get('status') in ('complete', 'incomplete')


_execute = redis.client.Pipeline.execute
def execute(self, *a, **k):  # 'after_exec_kill': die right after the transaction that writes the processed record
    stack = list(self.command_stack); writes_result = any(c[0][0] == 'SET' for c in stack)
    if MODE == 'exec_not_sent' and writes_result and crash_now(): raise redis.exceptions.ConnectionError('lost before sending')
    out = _execute(self, *a, **k)
    if MODE == 'after_exec_kill' and writes_result and crash_now(): kill_group()
    if MODE == 'exec_lost_reply' and writes_result and crash_now(): raise redis.exceptions.ConnectionError('reply lost after EXEC')
    if MODE == 'skip_ack_lost_reply' and {c[0][0] for c in stack} == {'LREM', 'HDEL'} and crash_now(): raise redis.exceptions.ConnectionError('reply lost after skip ACK')
    return out
redis.client.Pipeline.execute = execute

_blmove = redis.Redis.blmove
def blmove(self, *a, **k):  # 'claim_lost_reply': the move happens, the reply is lost
    out = _blmove(self, *a, **k)
    if MODE == 'claim_lost_reply' and out and crash_now(): raise redis.exceptions.ConnectionError('reply lost after BLMOVE')
    return out
redis.Redis.blmove = blmove

spec = importlib.util.spec_from_file_location('redisDB.redis_constants', ARGS['constants'])
constants = importlib.util.module_from_spec(spec); spec.loader.exec_module(constants)
module('utils'); module('utils.log_config', setup_logging=lambda **k: None)
module('redisDB'); module('redisDB.redisClasses', EventTraderRedis=Env); sys.modules['redisDB.redis_constants'] = constants
module('redisDB.ReportProcessor', ReportProcessor=Processor)
flags = module('config.feature_flags', FORM_TYPES_REQUIRING_SECTIONS=['8-K'], FORM_TYPES_REQUIRING_XML=['10-K'], PROCESSED_ITEM_KEY_TTL=60)
module('config', feature_flags=flags)
if not ARGS.get('real_pointer'): module('prepared_filing', pointer=pointer, prepared_done=prepared_done)  # else the image's real adapter (PYTHONPATH)
if ARGS['configured']: os.environ['PREPARED_EXTRACTION_CONFIG'] = ARGS.get('config', '/configured/adapter.json')
else: os.environ.pop('PREPARED_EXTRACTION_CONFIG', None)
spec = importlib.util.spec_from_file_location('enricher_under_test', ENRICHER); enricher = importlib.util.module_from_spec(spec); spec.loader.exec_module(enricher)
enricher.time.sleep = lambda s: None  # the failure path's 1 s pause
enricher.enrich_worker()
