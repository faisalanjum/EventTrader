"""One reader job (pictures/worker.py): each picture's bytes are read once per reader settings and kept as one complete result file; one job
per folder; storage failures stop; a saved or new record must be well formed and agree with its reader; a failed retry never erases the other
free tool's reading; a repeated occurrence id never replaces a picture. Ported on 2026-10-06 from prepare_work worker_check_20261006/
worker_test.py (Codex r15 plan, r16 corrections) with Codex's r16 regression scenarios and r17 boundary tests; the 506-picture preservation
cases run in test_replay on the pinned fixtures. Fake readers only: no model, no network."""
import copy
import errno
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from driver.prepare.get.acquire import StorageError
from driver.prepare.pictures import readers, worker

ROOT = str(Path(__file__).resolve().parents[4])            # the checkout under test
A, B, C = b'picture one', b'picture two', b'picture three'


def fake(settings=None, text='printed', tokens=10, fail=False, calls=None):  # a reader with the readers.py interface; logs every read
    calls = [] if calls is None else calls
    def read(data):
        calls.append(data)
        if fail: raise RuntimeError('fake reader failure')
        return [text, dict(generation_tokens=tokens)]
    return (lambda: types.SimpleNamespace(read=read, settings=settings or dict(reader='fake', model='m1'), status=readers._chandra_status)), calls


class Base(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup); self.tmp = Path(d.name); self.n = 0

    def folder(self):
        self.n += 1; return str(self.tmp / f'out{self.n}')

    def saved(self, f):
        return sorted(Path(f).glob('*.json'))


class Identity(Base):
    def test_same_bytes_read_once_both_occurrences_kept(self):
        f = self.folder(); mk, calls = fake(); out = worker.run(f, [('a', A), ('logo', A), ('c', B)], mk)
        self.assertEqual(len(calls), 2); self.assertIs(out['a'], out['logo']); self.assertEqual(set(out), {'a', 'logo', 'c'})
        self.assertFalse(any(b'logo' in p.read_bytes() for p in self.saved(f)))             # the saved result names no occurrence

    def test_reuse_and_rereads(self):
        f = self.folder(); worker.run(f, [('a', A), ('c', B)], fake()[0])
        mk, calls = fake(); worker.run(f, [('a', A), ('c', B)], mk); self.assertEqual(calls, [])         # complete results reused
        mk, calls = fake(); worker.run(f, [('c', C)], mk); self.assertEqual(calls, [C])                  # changed bytes under the same id: read again
        for what in ('model', 'prompt', 'preprocessing'):                                                   # changed settings: read again
            with self.subTest(changed=what):
                mk, calls = fake(settings={'reader': 'fake', 'model': 'm1', what: 'changed'}); worker.run(f, [('a', A)], mk)
                self.assertEqual(calls, [A])

    def test_distinct_occurrences_of_the_same_bytes_share_one_read(self):
        mk, calls = fake(); out = worker.run(self.folder(), [('filing1/doc.htm#3', A), ('filing2/ex99.htm#1', A)], mk)
        self.assertEqual((len(calls), set(out)), (1, {'filing1/doc.htm#3', 'filing2/ex99.htm#1'}))

    def test_a_repeated_occurrence_id_stops_before_it_replaces_a_picture(self):  # Codex r16 C4
        mk, calls = fake()
        with self.assertRaises(ValueError): worker.run(self.folder(), [('logo.jpg', b'one'), ('logo.jpg', b'two')], mk)
        self.assertEqual(calls, [b'one'])


class Publication(Base):
    def test_one_file_holds_text_run_record_and_status(self):
        f = self.folder(); rec = worker.run(f, [('a', A)], fake(tokens=readers.MAX_TOKENS)[0])['a']
        self.assertEqual((rec['status'], rec['result']), ('cut off', ['printed', dict(generation_tokens=12384)]))
        self.assertEqual(json.loads(self.saved(f)[0].read_text()), json.loads(json.dumps(rec)))
        mk, calls = fake(); worker.run(f, [('a', A)], mk); self.assertEqual(calls, [])                   # cut off: kept, not read again

    def test_a_pending_file_never_counts(self):
        f = self.folder(); worker.run(f, [('a', A)], fake()[0]); p = self.saved(f)[0]
        p.unlink(); Path(str(p) + '.pending').write_text('{"status": "complete", "res')                    # killed before the rename
        mk, calls = fake(); out = worker.run(f, [('a', A)], mk)
        self.assertEqual((calls, out['a']['status']), ([A], 'complete'))

    def test_killed_before_or_after_the_rename(self):
        crash = ("import os, sys, types; sys.path.insert(0, %r)\nfrom driver.prepare.pictures import worker\n"
                 "real = os.replace\ndef replace(a, b):\n    if sys.argv[2] == 'before': os._exit(91)\n    real(a, b); os._exit(92)\nos.replace = replace\n"
                 "mk = lambda: types.SimpleNamespace(read=lambda d: ['printed', dict(generation_tokens=12384)], settings=dict(reader='fake'), status=lambda r: 'cut off')\n"
                 "worker.run(sys.argv[1], [('a', b'picture one')], mk)") % ROOT
        for when, code in (('before', 91), ('after', 92)):
            with self.subTest(killed=when):
                f = self.folder(); p = subprocess.run([sys.executable, '-c', crash, f, when])
                final, pending = self.saved(f), list(Path(f).glob('*.pending'))
                self.assertEqual(p.returncode, code)
                if when == 'before': self.assertEqual((final, len(pending)), ([], 1))
                else:
                    rec = json.loads(final[0].read_text()); self.assertEqual((rec['status'], rec['result'][1]['generation_tokens']), ('cut off', 12384))

    def test_flush_errors_stop_the_job(self):
        for what, target, error in (('file flush', 'os.fsync', OSError('injected')), ('directory flush', 'driver.prepare.pictures.worker._sync_dir', StorageError('injected'))):
            with self.subTest(what=what), patch(target, side_effect=error):
                f = self.folder()
                with self.assertRaises((OSError, StorageError)): worker.run(f, [('a', A)], fake()[0])
                if what == 'file flush': self.assertEqual(self.saved(f), [])


class Ownership(Base):
    SLOW = ("import sys, time, types; sys.path.insert(0, %r)\nfrom driver.prepare.pictures import worker\n"
            "def read(d): open(sys.argv[2], 'a').write('read\\n'); time.sleep(float(sys.argv[3])); return ['printed', dict(generation_tokens=1)]\n"
            "mk = lambda: (open(sys.argv[2], 'a').write('init\\n'), types.SimpleNamespace(read=read, settings=dict(reader='fake'), status=lambda r: 'complete'))[1]\n"
            "try: worker.run(sys.argv[1], [(f'{i}.jpg', bytes([i])) for i in range(4)], mk); print('done')\nexcept RuntimeError as e: print('refused:', e)")

    def test_one_owner_and_restart_after_a_kill(self):
        f = self.folder(); log = str(self.tmp / 'owner.log'); code = self.SLOW % ROOT
        a = subprocess.Popen([sys.executable, '-c', code, f, log, '0.5'], stdout=subprocess.PIPE, text=True); time.sleep(0.6)
        b = subprocess.run([sys.executable, '-c', code, f, log, '0'], capture_output=True, text=True)
        self.assertTrue(b.stdout.startswith('refused: another job')); self.assertEqual(Path(log).read_text().count('init'), 1)   # refused before model start or read
        a.send_signal(signal.SIGKILL); a.wait(); a.stdout.close(); done = len(self.saved(f)); before = Path(log).read_text().count('read')
        c = subprocess.run([sys.executable, '-c', code, f, log, '0'], capture_output=True, text=True)
        self.assertEqual(c.stdout.strip(), 'done'); self.assertTrue(os.path.exists(os.path.join(f, '.lock')))
        self.assertTrue(1 <= done < 4); self.assertEqual(Path(log).read_text().count('read') - before, 4 - done); self.assertEqual(len(self.saved(f)), 4)


class Outcomes(Base):
    def test_a_reader_failure_is_recorded_once_per_run_and_retried_next_run(self):
        f = self.folder(); mk, calls = fake(fail=True); out = worker.run(f, [('a', A), ('a2', A), ('a3', A)], mk)
        self.assertEqual(len(calls), 1); self.assertEqual((out['a3']['status'], out['a']['result']), ('error', None))
        self.assertIn('fake reader failure', out['a']['error'])
        mk, calls = fake(); out = worker.run(f, [('a', A)], mk); self.assertEqual((calls, out['a']['status']), ([A], 'complete'))

    def test_an_empty_reading_is_kept_as_read(self):  # the packet then says MISSING
        out = worker.run(self.folder(), [('a', A)], fake(text='')[0])
        self.assertEqual((out['a']['status'], out['a']['result'][0]), ('complete', ''))

    def test_bytes_that_do_not_decode_are_the_pictures_content_error(self):
        out = worker.run(self.folder(), [('bad', b'not a picture')], lambda: types.SimpleNamespace(read=readers._image, settings=dict(reader='fake'), status=lambda r: 'complete'))
        self.assertEqual(out['bad']['status'], 'error'); self.assertTrue(out['bad']['error'].startswith('PictureError'))

    def test_sonnet_is_not_part_of_the_worker(self):
        self.assertFalse(any('sonnet' in line.lower() for line in Path(worker.__file__).read_text().splitlines() if 'import' in line))


class Storage(Base):  # Codex r16 C1: a disk fault stops; only the reader's own failure is a picture's error
    def test_storage_failures_inside_a_reading_stop_with_nothing_published(self):
        for exc in (OSError(errno.EIO, 'read'), OSError(errno.ENOSPC, 'full'), StorageError('store'), MemoryError('injected')):
            with self.subTest(error=repr(exc)):
                f, calls = self.folder(), []
                def read(d, exc=exc): calls.append(d); return [(_ for _ in ()).throw(exc)] if d == A else ['printed', dict(generation_tokens=1)]
                mk = lambda: types.SimpleNamespace(read=read, settings=dict(reader='fake'), status=readers._chandra_status)
                with self.assertRaises((OSError, StorageError, MemoryError)): worker.run(f, [('a', A), ('b', B)], mk)
                self.assertEqual((self.saved(f), calls), ([], [A]))                       # nothing published, and the next picture is never read

    def test_memory_exhaustion_keeps_earlier_readings_and_starts_nothing_after(self):   # Codex/root MEMORY_BOUNDARY: a complete reading survives, cached
        f = self.folder(); worker.run(f, [('a', A)], fake()[0]); before = {p.name: p.read_bytes() for p in self.saved(f)}
        calls = []
        def read(d): calls.append(d); raise MemoryError('injected') if d == B else AssertionError('read after the failure')
        mk = lambda: types.SimpleNamespace(read=read, settings=dict(reader='fake', model='m1'), status=readers._chandra_status)
        with self.assertRaises(MemoryError): worker.run(f, [('a', A), ('b', B), ('c', C)], mk)
        self.assertEqual(({p.name: p.read_bytes() for p in self.saved(f)}, calls), (before, [B]))   # A byte-identical and not read again; C never started

    def test_a_disk_error_on_a_saved_result_stops_instead_of_reading_again(self):
        f = self.folder(); worker.run(f, [('a', A)], fake()[0]); mk, calls = fake(); real_open = open
        def eio(p, *a, **k):
            if str(p).endswith('.json'): raise OSError(errno.EIO, 'metadata')
            return real_open(p, *a, **k)
        with patch('builtins.open', side_effect=eio), self.assertRaises(OSError): worker.run(f, [('a', A)], mk)
        self.assertEqual(calls, [])

    def test_the_output_folder_is_created_durably(self):
        f = os.path.join(self.folder(), 'new', 'nested'); worker.run(f, [('a', A)], fake()[0]); self.assertTrue(os.path.isdir(f))


class Records(Base):  # Codex r16 C2 and r17: one rule for saving and loading
    def test_a_damaged_saved_record_stops_the_job(self):
        edits = (('missing result', lambda r: r.pop('result')), ('null result', lambda r: r.update(result=None)), ('missing error field', lambda r: r.pop('error')),
                 ('complete where its reader says cut off', lambda r: r.update(result=['x', dict(generation_tokens=12384)])),
                 ('cut off where its reader says complete', lambda r: r.update(status='cut off')), ('error with a reading', lambda r: r.update(status='error', error='x')),
                 ('not an object', None))
        for what, edit in edits:
            with self.subTest(what=what):
                f = self.folder(); worker.run(f, [('a', A)], fake()[0]); p = self.saved(f)[0]; r = json.loads(p.read_text())
                p.write_text(json.dumps([] if edit is None else (edit(r), r)[1])); mk, calls = fake()
                with self.assertRaises(StorageError): worker.run(f, [('a', A)], mk)
                self.assertEqual(calls, [])

    def test_corrupt_or_foreign_saved_results_stop(self):
        f = self.folder(); worker.run(f, [('a', A)], fake()[0]); p = self.saved(f)[0]
        p.write_text('{"status": "compl')
        with self.assertRaisesRegex(StorageError, 'invalid saved result'): worker.run(f, [('a', A)], fake()[0])
        p.write_text(json.dumps(dict(status='complete', result=['x', dict(generation_tokens=1)], error=None, image_sha256=worker.sha(B), settings=dict(reader='fake', model='m1'))))
        with self.assertRaisesRegex(StorageError, 'does not match its key'): worker.run(f, [('a', A)], fake()[0])

    def test_a_reader_returning_nothing_or_a_wrong_shape_stops_unpublished(self):
        for what, ret, status in (('None, with a status that accepts anything', None, lambda r: 'complete'), ('a wrong shape', {'text': 'x'}, readers._chandra_status)):
            with self.subTest(returns=what):
                f = self.folder()
                with self.assertRaises((ValueError, TypeError)):
                    worker.run(f, [('a', A)], lambda ret=ret, status=status: types.SimpleNamespace(read=lambda d: ret, settings=dict(reader='chandra'), status=status))
                self.assertEqual(self.saved(f), [])


class Payloads(Base):  # Codex r17 boundary tests: reader payloads are checked at their status rule, saved and new
    def setUp(self):
        super().setUp(); b = io.BytesIO(); Image.new('RGB', (20, 10)).save(b, 'PNG'); self.items = [('occurrence', b.getvalue())]

    def make(self, value, status=readers._free_status):
        return lambda: types.SimpleNamespace(read=lambda _: value, status=status, settings={'reader': 'fixture'})

    def test_valid_readings_roundtrip_and_reuse(self):
        examples = [({'w': 20, 'h': 10, 'boxes': []}, readers._free_status), ({'w': 20, 'h': 10, 'boxes': [{'t': '10', 'box': [0, 0, 9.5, 4]}]}, readers._free_status),
                    ({'w': 20, 'h': 10, 'boxes': [{'t': '10', 'box': [-1, 0, 9, 0, 9, 4, -1, 4]}]}, readers._free_status), (['', {}], readers._chandra_status),
                    (['text', {'generation_tokens': None}], readers._chandra_status), (['text', {'generation_tokens': 0}], readers._chandra_status),
                    (['text', {'generation_tokens': readers.MAX_TOKENS}], readers._chandra_status)]
        for i, (value, status) in enumerate(examples):
            with self.subTest(example=i):
                f = self.folder(); saved = worker.run(f, self.items, self.make(value, status))
                def no_read(_): raise AssertionError('cached reading re-run')
                self.assertEqual(worker.run(f, self.items, lambda status=status: types.SimpleNamespace(read=no_read, status=status, settings={'reader': 'fixture'})), saved)

    def damaged(self):
        good = {'w': 20, 'h': 10, 'boxes': [{'t': '10', 'box': [0, 0, 9, 4]}]}
        for name in ('w', 'h'):
            for val in (None, True, 0, -1, '20', 1.5, float('nan')):
                x = copy.deepcopy(good); x[name] = val; yield f'{name}={val!r}', x, readers._free_status
        for b in (None, {}, {'t': None, 'box': [0, 0, 1, 1]}, {'t': 10, 'box': [0, 0, 1, 1]}, {'t': 'x', 'box': []}, {'t': 'x', 'box': [0, 0, 1]},
                  {'t': 'x', 'box': [0, 0, 1, 1, 2, 2]}, {'t': 'x', 'box': [None, 0, 1, 1]}, {'t': 'x', 'box': [True, 0, 1, 1]}, {'t': 'x', 'box': ['0', 0, 1, 1]},
                  {'t': 'x', 'box': [float('nan'), 0, 1, 1]}, {'t': 'x', 'box': [0, 0, float('inf'), 1]}):
            x = copy.deepcopy(good); x['boxes'] = [b]; yield repr(b), x, readers._free_status
        for val in (True, -1, 1.5, '12384', float('nan'), float('inf')):
            yield f'tokens={val!r}', ['text', {'generation_tokens': val}], readers._chandra_status

    def test_malformed_new_readings_stop_before_publication(self):
        for label, value, status in self.damaged():
            with self.subTest(payload=label):
                f = self.folder()
                with self.assertRaises(ValueError): worker.run(f, self.items, self.make(value, status))
                self.assertEqual(self.saved(f), [])

    def test_malformed_saved_readings_stop_before_reuse(self):
        for label, value, status in self.damaged():
            with self.subTest(payload=label):
                f = self.folder(); valid = ['text', {}] if status is readers._chandra_status else {'w': 20, 'h': 10, 'boxes': []}
                worker.run(f, self.items, self.make(valid, status)); p = self.saved(f)[0]; r = json.loads(p.read_text()); r['result'] = value; p.write_text(json.dumps(r))
                with self.assertRaises(StorageError): worker.run(f, self.items, self.make(valid, status))


class FreeToolsApart(Base):  # Codex r16 C3: PP-OCR and OnnxTR are separate readers; both failure directions
    def tool(self, name, fail_on_runs, calls, run):
        def read(d):
            calls.append(name)
            if run[0] in fail_on_runs: raise RuntimeError(f'{name} failed on run {run[0]}')
            return dict(w=10, h=5, boxes=[dict(t=f'{name} required fact', box=[0, 0, 1, 1])])
        return lambda: types.SimpleNamespace(read=read, settings=dict(reader=name), status=readers._free_status)

    def test_a_failed_retry_never_erases_the_other_tools_reading(self):
        for good, bad in (('pp', 'ox'), ('ox', 'pp')):
            with self.subTest(good=good, failing=bad):
                f = self.folder(); calls, run = [], [1]; mk = {good: self.tool(good, set(), calls, run), bad: self.tool(bad, {1, 2}, calls, run)}
                for run[0] in (1, 2): recs = {t: worker.run(f, [('a', A)], mk[t])['a'] for t in ('pp', 'ox')}
                rec = readers.free_record(recs['pp'], recs['ox'])
                self.assertEqual((calls.count(good), calls.count(bad)), (1, 2))                      # the good reading is never read again
                self.assertEqual((rec[good][0]['t'], rec[bad]), (f'{good} required fact', [])); self.assertIn(f'{bad}_error', rec)
                self.assertTrue(any(f'{good} required fact' in p.read_text() for p in self.saved(f)))
                run[0] = 3; recs = {t: worker.run(f, [('a', A)], mk[t])['a'] for t in ('pp', 'ox')}; rec = readers.free_record(recs['pp'], recs['ox'])
                self.assertEqual(calls.count(good), 1); self.assertTrue(rec['pp'] and rec['ox']); self.assertNotIn('pp_error', rec); self.assertNotIn('ox_error', rec)

    def test_with_neither_tool_read_there_is_no_free_evidence(self):  # two worker records of one picture (its input was two hand-made dicts without the worker's fields)
        calls, run = [], [1]; f = self.folder()
        recs = {t: worker.run(f, [('a', A)], self.tool(t, {1}, calls, run))['a'] for t in ('pp', 'ox')}
        self.assertEqual((recs['pp']['status'], recs['ox']['status']), ('error', 'error'))
        self.assertIsNone(readers.free_record(recs['pp'], recs['ox']))


class FreeRecordOnePicture(Base):  # Root, picture_record_binding_20261009: the join takes two worker records of ONE picture's bytes
    tool = FreeToolsApart.tool  # the same fake free tools

    def recs(self, pp_data, ox_data, pp_fail=(), ox_fail=(), ox_size=None):
        calls, run = [], [1]; f = self.folder(); ox = self.sized('ox', ox_size) if ox_size else self.tool('ox', set(ox_fail), calls, run)
        return worker.run(f, [('p', pp_data)], self.tool('pp', set(pp_fail), calls, run))['p'], worker.run(f, [('o', ox_data)], ox)['o']

    def sized(self, name, size):  # a reader that measures the picture otherwise
        read = lambda d: dict(w=size[0], h=size[1], boxes=[dict(t=f'{name} required fact', box=[0, 0, 1, 1])])
        return lambda: types.SimpleNamespace(read=read, settings=dict(reader=name), status=readers._free_status)

    def test_records_of_different_pictures_are_refused(self):  # failed before: the wrong pair joined into the right pair's evidence
        for pp_fail, ox_fail in (((), ()), ((), {1}), ({1}, ()), ({1}, {1})):
            with self.subTest(pp_failed=bool(pp_fail), ox_failed=bool(ox_fail)), self.assertRaises(ValueError):
                readers.free_record(*self.recs(A, B, pp_fail, ox_fail))

    def test_a_record_without_the_picture_identity_is_refused(self):
        pp, ox = self.recs(A, A)
        for k in ('pp', 'ox'):
            for bad in (None, '', 'absent'):
                with self.subTest(record=k, image_sha256=bad), self.assertRaises(ValueError):
                    x, y = copy.deepcopy(pp), copy.deepcopy(ox); z = x if k == 'pp' else y
                    z.pop('image_sha256') if bad == 'absent' else z.__setitem__('image_sha256', bad); readers.free_record(x, y)

    def test_two_readings_of_one_picture_in_different_frames_are_refused(self):  # failed before: the second tool's size silently replaced the first's
        with self.assertRaises(ValueError): readers.free_record(*self.recs(A, A, ox_size=(11, 5)))
        rec = readers.free_record(*self.recs(A, A, ox_fail={1}))                  # an error carries no frame: the one reading keeps its own
        self.assertEqual((rec['w'], rec['h']), (10, 5))

    def test_one_picture_joins_as_before_whatever_the_settings(self):  # the two tools' settings differ by design; the join is unchanged
        pp, ox = self.recs(A, A); self.assertNotEqual(pp['settings'], ox['settings'])
        want = dict(pp=[dict(t='pp required fact', box=[0, 0, 1, 1])], w=10, h=5, ox=[dict(t='ox required fact', box=[0, 0, 1, 1])])
        self.assertEqual(json.dumps(readers.free_record(pp, ox)), json.dumps(want))   # same keys, order and values
        self.assertEqual(json.dumps(readers.free_record(*self.recs(A, A, ox_fail={1}))), json.dumps(dict(pp=want['pp'], w=10, h=5, ox=[], ox_error='RuntimeError: ox failed on run 1')))
        self.assertEqual(json.dumps(readers.free_record(*self.recs(A, A, pp_fail={1}))), json.dumps(dict(pp=[], pp_error='RuntimeError: pp failed on run 1', ox=want['ox'], w=10, h=5)))
        self.assertIsNone(readers.free_record(*self.recs(A, A, {1}, {1})))


if __name__ == '__main__':
    unittest.main()
