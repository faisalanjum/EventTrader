"""No live requests: policy and low-level HTTP are exercised with controls."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import gzip
import http.client
import io
import unittest
from unittest.mock import MagicMock, patch

from driver.prepare.get.transport import DownloadError, HEADERS, LIMITS, download, http_request


URL = 'https://www.sec.gov/Archives/edgar/data/1/000000000123000001/0000000001-23-000001.txt'


class Clock:
    def __init__(self):
        self.value = 0
        self.sleeps = []

    def now(self):
        return self.value

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.value += duration


class DownloadTests(unittest.TestCase):
    def fetch(self, replies, **options):
        clock = Clock()
        calls = []

        def sender(*args):
            calls.append((clock.now(), args))
            result = replies[len(calls) - 1]
            if isinstance(result, Exception):
                raise result
            return result

        self.clock, self.calls = clock, calls
        return download(URL, sender=sender, now=clock.now, sleep=clock.sleep, **options)

    def test_identity_success_and_gzip_response(self):
        for headers, body in (({'content-length': '3'}, b'abc'),
                              ({'content-encoding': 'gzip'}, gzip.compress(b'abc'))):
            data, receipt = self.fetch([(200, headers, body)])
            self.assertEqual(data, b'abc')
            self.assertEqual(len(self.calls), 1)
            self.assertEqual(receipt['url'], URL)
            self.assertIsNotNone(receipt['retrieved_at'])
            self.assertEqual(receipt['attempts'][0]['status'], 200)
            self.assertEqual(self.calls[0][1][1], HEADERS)
            self.assertEqual(self.calls[0][1][2:], (LIMITS['connect_timeout'], LIMITS['read_timeout'], LIMITS['attempt_wall_seconds']))

    def test_each_transient_status_and_network_failure_retries(self):
        failures = [(status, {}, b'bad') for status in (408, 429, 500, 502, 503, 504)]
        failures += [TimeoutError('timeout'), ConnectionError('connection'), http.client.IncompleteRead(b'part')]
        failures += [(200, {'content-length': '99'}, b'bad'), (200, {'content-encoding': 'gzip'}, b'bad')]
        compressed = gzip.compress(b'hello')
        failures.append((200, {'content-encoding': 'gzip'}, compressed[:10] + b'\xff' * 10 + compressed[-8:]))
        for reply in failures:
            with self.subTest(reply=reply):
                data, receipt = self.fetch([reply, (200, {}, b'ok')])
                self.assertEqual(data, b'ok')
                self.assertEqual(self.clock.sleeps, [2])
                self.assertEqual(len(receipt['attempts']), 2)
                self.assertGreaterEqual(self.calls[1][0] - self.calls[0][0], 1)
                if isinstance(reply, tuple) and reply[1].get('content-encoding') == 'gzip':
                    self.assertIn(receipt['attempts'][0]['error'], ('BadGzipFile', 'error'))  # gzip or zlib decoding

    def test_exhaustion_budget_and_retry_after(self):
        with self.assertRaisesRegex(DownloadError, 'exhausted') as caught:
            self.fetch([TimeoutError()] * 3)
        self.assertEqual(len(caught.exception.receipt['attempts']), 3)
        self.assertEqual(self.clock.sleeps, [2, 4])
        for delay in ('10', format_datetime(datetime.now(timezone.utc) + timedelta(seconds=20))):
            with self.subTest(delay=delay):
                self.fetch([(429, {'retry-after': delay}, b''), (200, {}, b'ok')])
                self.assertGreaterEqual(self.clock.sleeps[0], 10)
        self.fetch([(503, {'retry-after': 'invalid'}, b''), (200, {}, b'ok')])
        self.assertEqual(self.clock.sleeps, [2])
        with self.assertRaisesRegex(DownloadError, 'budget'):
            self.fetch([(429, {'retry-after': '9999'}, b'')], budget=20)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.clock.sleeps, [])
        with self.assertRaisesRegex(DownloadError, 'budget'):
            self.fetch([], budget=0)
        self.assertEqual(self.calls, [])

    def test_403_redirects_other_errors_and_unknown_encoding_do_not_retry(self):
        replies = [(403, {'content-length': 'bad', 'content-encoding': 'bad'}, b'part'),
                   (301, {'location': URL}, b''), (302, {'location': 'https://elsewhere.example/'}, b''),
                   (307, {}, b''), (404, {}, b''), (200, {'content-encoding': 'unsupported'}, b'bad')]
        for reply in replies:
            with self.subTest(reply=reply), self.assertRaises(DownloadError) as caught:
                self.fetch([reply])
            self.assertEqual(len(self.calls), 1)
            self.assertEqual(caught.exception.receipt['attempts'][0]['status'], reply[0])

    def test_low_level_timeouts_body_read_and_alarm_cleanup(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.getheaders.return_value = [('Content-Length', '3')]
        response.chunked, response.length = False, 3
        response.headers.get_all.side_effect = lambda name: ['3'] if name == 'content-length' else None
        response.read.return_value = b'abc'
        with patch('driver.prepare.get.transport.http.client.HTTPSConnection', return_value=connection) as create, \
             patch('driver.prepare.get.transport.signal.signal') as handler, \
             patch('driver.prepare.get.transport.signal.setitimer') as timer:
            result = http_request(URL, HEADERS, 10, 60, 120)
        self.assertEqual(result, (200, {'content-length': '3'}, b'abc'))
        create.assert_called_once_with('www.sec.gov', timeout=10)
        connection.sock.settimeout.assert_called_once_with(60)
        connection.close.assert_called_once()
        self.assertEqual(timer.call_args_list[0].args[1], 120)
        self.assertEqual(timer.call_args_list[-1].args[1], 0)
        self.assertEqual(handler.call_count, 2)
        # A denied response stops before attempting to read even a broken body.
        response.status = 403
        response.read.side_effect = http.client.IncompleteRead(b'part')
        response.read.reset_mock()
        with patch('driver.prepare.get.transport.http.client.HTTPSConnection', return_value=connection), \
             patch('driver.prepare.get.transport.signal.signal'), patch('driver.prepare.get.transport.signal.setitimer'):
            self.assertEqual(http_request(URL, HEADERS, 10, 60, 120)[0], 403)
        response.read.assert_not_called()

    def test_an_attempt_past_its_wall_limit_is_a_timeout_and_leaves_no_alarm(self):  # http_request's own SIGALRM handler, the real signal and timer
        import signal, time
        handler = signal.getsignal(signal.SIGALRM)
        stalled = MagicMock(); stalled.connect.side_effect = lambda: time.sleep(5)  # DNS or connect that never answers
        with patch('driver.prepare.get.transport.http.client.HTTPSConnection', return_value=stalled):
            started = time.monotonic()
            with self.assertRaisesRegex(TimeoutError, '^HTTP attempt wall limit$'):
                http_request(URL, HEADERS, 10, 60, 0.05)
        self.assertLess(time.monotonic() - started, 2)  # the limit ended it, not the stalled call
        self.assertEqual((signal.getitimer(signal.ITIMER_REAL), signal.getsignal(signal.SIGALRM)), ((0.0, 0.0), handler))
        quick = MagicMock(); response = quick.getresponse.return_value  # control: an attempt inside its limit, the same real timer
        response.status, response.chunked, response.length = 200, False, 3
        response.getheaders.return_value = [('Content-Length', '3')]
        response.headers.get_all.side_effect = lambda name: ['3'] if name == 'content-length' else None
        response.read.return_value = b'abc'
        with patch('driver.prepare.get.transport.http.client.HTTPSConnection', return_value=quick):
            self.assertEqual(http_request(URL, HEADERS, 10, 60, 5), (200, {'content-length': '3'}, b'abc'))
        self.assertEqual((signal.getitimer(signal.ITIMER_REAL), signal.getsignal(signal.SIGALRM)), ((0.0, 0.0), handler))


class WireConnection:
    """One in-memory server reply, read by Python's own HTTP parser; no network."""
    def __init__(self, wire):
        self.wire, self.sock = wire, MagicMock()

    def connect(self):
        pass

    def request(self, *args, **kwargs):
        pass

    def getresponse(self):
        socket = MagicMock()
        socket.makefile.return_value = io.BytesIO(self.wire)
        response = http.client.HTTPResponse(socket)
        response.begin()
        return response

    def close(self):
        pass


class FramingTests(unittest.TestCase):
    def test_a_body_counts_only_with_one_framing_pythons_reader_accepted(self):
        # Codex recheck 2026-10-03: a body without a proven end could be a cut-short page that lists only some files.
        replies = {'length': (b'Content-Length: 4\r\n', b'part', b'part'),
                   'chunked': (b'Transfer-Encoding: chunked\r\n', b'4\r\npart\r\n0\r\n\r\n', b'part'),
                   'cut chunked': (b'Transfer-Encoding: chunked\r\n', b'4\r\npart', None),
                   'no framing': (b'', b'part', None),
                   'unknown coding': (b'Transfer-Encoding: xchunked\r\n', b'part', None),
                   'coding chain': (b'Transfer-Encoding: chunked, gzip\r\n', b'part', None),
                   'trailing space': (b'Transfer-Encoding: chunked \r\n', b'part', None),
                   'two codings': (b'Transfer-Encoding: xchunked\r\nTransfer-Encoding: chunked\r\n', b'part', None),
                   'length and chunked': (b'Content-Length: 4\r\nTransfer-Encoding: chunked\r\n', b'4\r\npart\r\n0\r\n\r\n', None),
                   'two lengths': (b'Content-Length: 4\r\nContent-Length: 5\r\n', b'part', None),
                   'bad length': (b'Content-Length: four\r\n', b'part', None)}
        for label, (headers, body, expected) in replies.items():
            wire = b'HTTP/1.1 200 OK\r\n' + headers + b'Connection: close\r\n\r\n' + body
            with self.subTest(label), patch('driver.prepare.get.transport.http.client.HTTPSConnection',
                                            return_value=WireConnection(wire)), \
                    patch('driver.prepare.get.transport.signal.signal'), patch('driver.prepare.get.transport.signal.setitimer'):
                if expected is None:
                    with self.assertRaises(http.client.HTTPException):
                        http_request(URL, HEADERS, 10, 60, 120)
                else:
                    self.assertEqual(http_request(URL, HEADERS, 10, 60, 120)[::2], (200, expected))



class CompletionRuleTests(unittest.TestCase):
    def test_closes_is_the_one_rule_for_a_completed_response(self):  # 200, or a final non-200 answer; RETRY statuses and unsupported 3xx stay open; context acquisition uses the same function
        from driver.prepare.get import context_acquire, transport
        table = {200: True, 404: True, 410: True, 400: True, 503: False, 429: False, 408: False, 500: False, 502: False, 504: False, 301: False, 302: False, 304: False}
        self.assertEqual({s: transport.closes({'status': s}) for s in table}, table)
        self.assertEqual([transport.closes(x) for x in (None, {}, {'status': '200'}, {'status': None})], [False] * 4)
        self.assertIs(context_acquire._closes, transport.closes)


if __name__ == '__main__':
    unittest.main()

