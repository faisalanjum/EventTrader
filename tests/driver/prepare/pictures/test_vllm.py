"""Actual pinned Chandra helpers; the SDK transport is the only substitute."""
import io
import json
import functools
from contextlib import contextmanager
import types
import unittest
from unittest.mock import patch

from PIL import Image

from driver.prepare.pictures import readers


class NativeClient(unittest.TestCase):
    def setUp(self):
        import chandra.model.vllm as native
        self.native = native
        self.calls, self.clients = [], []
        self.raw, self.finish, self.tokens, self.failure = '<p>Printed 25</p>', 'stop', 7, None
        test = self

        class Client:
            def __init__(self, **options):
                self.options, self.closed = options, False
                self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self.create, stream=self.stream))
                test.clients.append(self)

            @contextmanager
            def stream(self, **request):
                response = self.create(**request)
                yield types.SimpleNamespace(until_done=lambda: None, current_completion_snapshot=response)

            def create(self, **request):
                test.calls.append(request)
                if test.failure:
                    if isinstance(test.failure, BaseException): raise test.failure
                    raise RuntimeError(test.failure)
                return types.SimpleNamespace(
                    choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=test.raw), finish_reason=test.finish)],
                    usage=types.SimpleNamespace(completion_tokens=test.tokens,
                                                model_dump=lambda: dict(completion_tokens=test.tokens)),
                    model='chandra', _request_id='native-control')

            def close(self):
                self.closed = True

        self.patch = patch.object(native, 'OpenAI', Client)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        image = io.BytesIO()
        Image.new('RGB', (80, 40), 'white').save(image, 'PNG')
        self.image = image.getvalue()

    def reader(self, **kwargs):
        return readers.chandra_vllm('http://self-hosted.invalid/v1', dict(model='chandra-ocr-2', revision='control'), **kwargs)

    def test_native_request_single_attempt_and_original_raw_result(self):
        reader = self.reader(timeout=60)
        result = reader.read(self.image)
        self.assertEqual(result[0], self.raw)
        self.assertEqual(result[1]['finish_reason'], 'stop')
        self.assertEqual(result[1]['generation_tokens'], 7)
        self.assertEqual(reader.status(result), 'complete')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((self.calls[0]['temperature'], self.calls[0]['top_p'], self.calls[0]['max_tokens']), (0.0, 0.1, 12384))
        self.assertEqual((self.clients[0].options['timeout'], self.clients[0].options['max_retries']), (60, 0))
        self.assertTrue(self.clients[0].closed)
        self.assertNotIn('api_key', reader.settings)

    def test_native_failure_is_not_retried_or_accepted(self):
        self.failure = 'controlled backend failure'
        with self.assertRaises(RuntimeError):
            self.reader().read(self.image)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.clients[0].closed)

    def test_blank_and_unexpected_finish_are_not_complete_readings(self):
        for raw, finish in (('', 'stop'), ('   ', 'stop'), ('<p>Partial</p>', 'content_filter')):
            with self.subTest(raw=raw, finish=finish):
                self.raw, self.finish = raw, finish
                with self.assertRaises(RuntimeError):
                    self.reader().read(self.image)
        self.raw, self.finish = '<p>Positive 25</p>', 'stop'
        self.assertEqual(self.reader().read(self.image)[0], self.raw)

    def test_authoritative_length_finish_is_kept_incomplete_below_token_cap(self):
        self.finish = 'length'
        reader = self.reader()
        result = reader.read(self.image)
        self.assertEqual(reader.status(result), 'cut off')
        self.assertEqual(result[0], self.raw)

    def test_native_repetition_diagnostic_is_retained_without_repair_or_retry(self):
        self.raw = 'repeated ' * 200
        result = self.reader().read(self.image)
        self.assertTrue(result[1]['repeated'])
        self.assertEqual(result[0], self.raw)
        self.assertEqual(len(self.calls), 1)

    def test_machine_failure_is_not_downgraded_to_a_picture_error(self):
        self.failure = MemoryError('controlled memory failure')
        with self.assertRaises(MemoryError):
            self.reader().read(self.image)
        self.assertEqual(len(self.calls), 1)

    def test_actual_sdk_request_and_error_have_no_hidden_transport_retry(self):
        import httpx2
        from openai import OpenAI
        for status in (200, 503):
            calls = []
            def answer(request):
                calls.append(request)
                response = dict(
                    id='independent-native-control', object='chat.completion', created=0, model='chandra',
                    choices=[dict(index=0, finish_reason='stop', message=dict(role='assistant', content='<p>Printed 25</p>'))],
                    usage=dict(prompt_tokens=2, completion_tokens=7, total_tokens=9))
                if status != 200: return httpx2.Response(status, json=response)
                return httpx2.Response(200, headers={'content-type': 'text/event-stream'}, content=sse())
            transport = httpx2.Client(transport=httpx2.MockTransport(answer))
            with self.subTest(status=status), patch.object(self.native, 'OpenAI', functools.partial(OpenAI, http_client=transport)):
                if status == 200:
                    self.assertEqual(self.reader().read(self.image)[0], '<p>Printed 25</p>')
                else:
                    with self.assertRaises(RuntimeError): self.reader().read(self.image)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].url.path, '/v1/chat/completions')
            self.assertEqual(json.loads(calls[0].content)['temperature'], 0.0)
            self.assertTrue(json.loads(calls[0].content)['stream'])
            self.assertEqual(json.loads(calls[0].content)['stream_options'], {'include_usage': True})
            self.assertTrue(transport.is_closed)

    def test_actual_sdk_stream_preserves_raw_length_finish_and_final_usage(self):
        import httpx2
        from openai import OpenAI
        for finish in ('stop', 'length'):
            transport = httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(
                200, headers={'content-type': 'text/event-stream'}, content=sse(finish))))
            with self.subTest(finish=finish), patch.object(self.native, 'OpenAI', functools.partial(OpenAI, http_client=transport)):
                reader = self.reader(); raw, run = reader.read(self.image)
                self.assertEqual(raw, '<p>Printed 25</p>')
                self.assertEqual(run['finish_reason'], finish)
                self.assertEqual(run['generation_tokens'], 7)
                self.assertEqual(run['usage']['total_tokens'], 9)
                self.assertEqual(reader.status([raw, run]), 'complete' if finish == 'stop' else 'cut off')
            self.assertTrue(transport.is_closed)

    def test_actual_sdk_stream_rejects_missing_finish_usage_timeout_and_stream_error(self):
        import httpx2
        from openai import OpenAI
        for failure in ('finish', 'usage', 'timeout', 'error'):
            class Body(httpx2.SyncByteStream):
                def __iter__(self):
                    if failure == 'timeout': raise httpx2.ReadTimeout('controlled stream timeout')
                    yield sse(None if failure == 'finish' else 'stop', usage=failure != 'usage', error=failure == 'error')
            calls = []
            def answer(request):
                calls.append(request)
                return httpx2.Response(200, headers={'content-type': 'text/event-stream'}, stream=Body())
            transport = httpx2.Client(transport=httpx2.MockTransport(answer))
            with self.subTest(failure=failure), patch.object(self.native, 'OpenAI', functools.partial(OpenAI, http_client=transport)):
                with self.assertRaises(RuntimeError): self.reader().read(self.image)
            self.assertEqual(len(calls), 1)
            self.assertTrue(transport.is_closed)


def sse(finish='stop', usage=True, error=False):
    """Independent server events, including the separate final usage-only chunk."""
    def chunk(choices, **extra):
        return dict(id='stream-control', object='chat.completion.chunk', created=0, model='chandra', choices=choices, **extra)
    events = [chunk([dict(index=0, delta=dict(role='assistant', content='<p>Printed '), finish_reason=None)]),
              chunk([dict(index=0, delta=dict(content='25</p>'), finish_reason=finish)])]
    if error: events.append(dict(error=dict(message='controlled stream error', type='server_error')))
    if usage: events.append(chunk([], usage=dict(prompt_tokens=2, completion_tokens=7, total_tokens=9)))
    return (''.join('data: ' + json.dumps(e) + '\n\n' for e in events) + 'data: [DONE]\n\n').encode()


if __name__ == '__main__':
    unittest.main()
