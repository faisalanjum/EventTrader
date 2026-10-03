"""One SEC package URL, bounded retries, no redirects. Standard library only."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import gzip
import http.client
import signal
import time
from urllib.parse import urlsplit
import zlib

HEADERS = {'User-Agent': 'EventMarketDB faianjum@gmail.com', 'Accept-Encoding': 'identity'}
LIMITS = dict(connect_timeout=10, read_timeout=60, attempt_wall_seconds=120,
              attempts=3, job_wall_seconds=900, retry_backoff_seconds=(2, 4))
RETRY = {408, 429, 500, 502, 503, 504}


class DownloadError(OSError):
    def __init__(self, message, receipt):
        super().__init__(message)
        self.receipt = receipt


def http_request(url, headers, connect_timeout, read_timeout, wall_timeout):
    """Linux/main thread: bound DNS, connect and body together with SIGALRM."""
    def expired(signum, frame):
        raise TimeoutError('HTTP attempt wall limit')

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, wall_timeout)
    connection = None
    try:
        parsed = urlsplit(url)
        connection = http.client.HTTPSConnection(parsed.hostname, timeout=connect_timeout)
        connection.connect()
        connection.sock.settimeout(read_timeout)
        connection.request('GET', parsed.path, headers=headers)
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}
        # A body's end is proven only by exactly one framing that Python's reader itself accepted (a length or
        # chunked); with none, two, or one it does not support, the body ends where the connection did, maybe cut short.
        framing = [value for name in ('content-length', 'transfer-encoding') for value in response.headers.get_all(name) or ()]
        if response.status == 200 and (len(framing) != 1 or not (response.chunked or response.length is not None)):
            raise http.client.HTTPException(f'Body end not provable from its framing headers {framing}')
        # No error/redirect body is a package; 403 stops even with a broken body.
        body = response.read() if response.status == 200 else b''
        return response.status, headers, body
    finally:
        if connection:
            connection.close()
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def download(url, *, sender=http_request, now=time.monotonic, sleep=time.sleep, budget=None,
             before_send=None):
    """Return package bytes and receipt; errors carry the receipt too.

    Only retries create additional requests. Backoffs are at least two seconds,
    so this call stays below one request/second; callers coordinate shared use.
    """
    receipt = dict(url=url, retrieved_at=None, attempts=[])
    deadline = now() + (LIMITS['job_wall_seconds'] if budget is None else budget)

    def fail(message):
        raise DownloadError(message, receipt)

    for attempt in range(LIMITS['attempts']):
        if before_send:
            before_send()
        remaining = deadline - now()
        if remaining <= 0:
            fail('HTTP job budget exhausted')
        entry = dict(attempt=attempt + 1, started_at=datetime.now(timezone.utc).isoformat(), status=None)
        receipt['attempts'].append(entry)
        retry_after = None
        try:
            status, headers, wire = sender(url, dict(HEADERS), LIMITS['connect_timeout'],
                                          LIMITS['read_timeout'], min(LIMITS['attempt_wall_seconds'], remaining))
            headers = {key.lower(): value for key, value in headers.items()}
            entry.update(status=status, headers=headers)
            if status == 200:
                encoding = headers.get('content-encoding', 'identity').lower()
                if encoding not in ('identity', 'gzip'):
                    fail('Unsupported HTTP content encoding')
                length = headers.get('content-length')
                if length is not None and (not length.isdigit() or int(length) != len(wire)):
                    raise http.client.IncompleteRead(wire)
                data = gzip.decompress(wire) if encoding == 'gzip' else wire
                receipt['retrieved_at'] = datetime.now(timezone.utc).isoformat()
                entry.update(wire_bytes=len(wire), package_bytes=len(data))
                return data, receipt
            if status not in RETRY:
                fail('HTTP ' + str(status) + ('; redirects unsupported' if 300 <= status < 400 else ''))
            retry_after = headers.get('retry-after')
        except DownloadError:
            raise
        except (OSError, EOFError, zlib.error, http.client.HTTPException) as exc:
            entry['error'] = type(exc).__name__
        if attempt + 1 == LIMITS['attempts']:
            fail('HTTP retries exhausted')
        delay = LIMITS['retry_backoff_seconds'][attempt]
        if retry_after:
            try:
                requested = int(retry_after) if retry_after.isdigit() else (
                    parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
                delay = max(delay, requested)
            except (ValueError, TypeError, OverflowError):
                pass
        if now() + delay >= deadline:
            fail('HTTP job budget exhausted before Retry-After/backoff')
        entry['retry_delay_seconds'] = delay
        sleep(delay)
