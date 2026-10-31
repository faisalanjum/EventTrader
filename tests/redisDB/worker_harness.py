"""Runs the isolated report_enricher copy's REAL enrich_worker loop for given events, with its imports replaced by recording fakes
(no Redis, no logging setup, no ReportProcessor, no network). Prints the ordered call log as JSON.
Usage: python -B worker_harness.py <enricher.py> '<json: events, existing, legacy_raises, configured>'"""
import importlib.util, json, os, sys, types

ENRICHER, ARGS = sys.argv[1], json.loads(sys.argv[2])
LOG = []


def module(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m


class Pipe:
    def set(self, k, v, ex=None): LOG.append(['set', k, json.loads(v)])
    def lpush(self, q, k): LOG.append(['lpush', q, k])
    def publish(self, ch, k): LOG.append(['publish', ch, k])
    def execute(self): LOG.append(['execute'])
    def lrem(self, k, n, v): LOG.append(['lrem', k])
    def hdel(self, k, f): LOG.append(['hdel', k])
    def rpush(self, k, v): LOG.append(['rpush', k, json.loads(v)])


class Inner:
    def __init__(self): self.events = [json.dumps(e) for e in ARGS['events']]
    def blpop(self, key, timeout):
        if self.events: return key, self.events.pop(0)
        raise KeyboardInterrupt  # ends the worker's endless loop (not caught by its `except Exception`)
    def blmove(self, src, dst, timeout, a, b):  # the reliable claim (configured path)
        LOG.append(['claim', src, dst]); return self.blpop(src, timeout)[1]
    def lrange(self, k, s, e): return []  # nothing left by a killed worker
    def set_retry(self, retry): LOG.append(['set_retry', retry._retries])
    def get(self, k): v = ARGS['existing'].get(k); return json.dumps(v) if v is not None else None
    def pipeline(self, transaction=True): return Pipe()


class Client:
    client = Inner()
    def mark_lifecycle_timestamp(self, meta_key, name, **k): LOG.append(['mark', name]); return k.get('external_pipe')


class Env:
    def __init__(self, source, **k): self.live_client = self.history_client = Client()


class Keys:
    SOURCE_REPORTS, ENRICH_QUEUE, PREFIX_HIST, SUFFIX_PROCESSED = 'reports', 'enrich', 'hist', 'processed'
    @staticmethod
    def get_key(source_type, key_type, prefix_type, identifier): return f'{source_type}:{prefix_type}:{key_type}:{identifier}'
    @staticmethod
    def get_pubsub_channel(source): return 'channel'


class Queues:
    @staticmethod
    def get_queues(source): return {'PROCESSED_QUEUE': 'processed_queue', 'FAILED_QUEUE': 'failed_queue'}


class Processor:
    def __init__(self, *a, **k): pass
    def _extract_sections(self, **k):
        LOG.append(['legacy', '_extract_sections'])
        if ARGS['legacy_raises']: raise RuntimeError('legacy section extraction failed')
        return {'s': 1}
    def _extract_secondary_filing_content(self, url): LOG.append(['legacy', '_extract_secondary_filing_content']); return 'text'
    def _get_financial_statements(self, **k): LOG.append(['legacy', '_get_financial_statements']); return {}
    def _process_exhibits(self, ex): LOG.append(['legacy', '_process_exhibits']); return {}


def pointer(filing, config_path): LOG.append(['pointer', filing['accessionNo']]); return {'status': 'complete', 'receipt': None}


def prepared_done(record): return (record.get('prepared_extraction') or {}).get('status') in ('complete', 'incomplete')


module('utils'); module('utils.log_config', setup_logging=lambda **k: None)
module('redisDB'); module('redisDB.redisClasses', EventTraderRedis=Env)
module('redisDB.redis_constants', RedisKeys=Keys, RedisQueues=Queues)
module('redisDB.ReportProcessor', ReportProcessor=Processor)
flags = module('config.feature_flags', FORM_TYPES_REQUIRING_SECTIONS=['8-K'], FORM_TYPES_REQUIRING_XML=['10-K'], PROCESSED_ITEM_KEY_TTL=60)
module('config', feature_flags=flags)
module('prepared_filing', pointer=pointer, prepared_done=prepared_done)  # the hook's seam: recorded, not run here
if ARGS['configured']: os.environ['PREPARED_EXTRACTION_CONFIG'] = '/configured/adapter.json'
else: os.environ.pop('PREPARED_EXTRACTION_CONFIG', None)
spec = importlib.util.spec_from_file_location('enricher_under_test', ENRICHER); enricher = importlib.util.module_from_spec(spec); spec.loader.exec_module(enricher)
enricher.time.sleep = lambda s: None  # the failure path's 1 s pause
try:
    enricher.enrich_worker()
except KeyboardInterrupt:
    pass
print(json.dumps(LOG))
