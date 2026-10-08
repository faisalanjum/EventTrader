"""The 506 saved inputs (validation120, development336, hard50) through the runtime in both modes, once each, against the pinned fixtures.

Sonnet off (default): every input goes through the worker with saved readers first (Chandra, PP-OCR and OnnxTR apart: 505 distinct
pictures, each read once; a rerun retries only the one error record) and the packets rebuilt from the worker's results equal the
frozen default baseline (DEFAULT_BASELINE.jsonl, frozen from the development code before migration). A saved Sonnet answer is held
for 502 inputs and never called; no subprocess may start. Optional mode: the saved v6 routes ask exactly 264 inputs (52 + 169 + 43),
the saved reading is used once per asked input and never otherwise, and each packet equals its saved packet (validation eval_packets,
development real336_dev, hard-page historical preservation packets). The 576 saved packets (validation production and evaluation,
development) are rebuilt from the same pass. Allowed differences: the one status line (rule-checked) and the named picture
relocation. These are preservation checks of saved behaviour, not OCR accuracy: the known reading errors are listed at the end.
Ported 2026-10-07 from prepare_work runtime_extract_20261006/modes.py and replay.py and worker_check_20261006/worker_test.py."""
import collections
import hashlib
import json
import os
import tempfile
import types
import unittest
from unittest.mock import patch

from driver.prepare import pictures
from driver.prepare.pictures import packets, readers, worker
from tests.driver.prepare.pictures.saved import SETS, Saved, body, evidence_whole, status_follows_flags

V6 = {'validation120': 'real575_20261005/validation_20261006/ROUTES_V6.json', 'rest': 'real575_20261005/reader_packets/real336_dev/ROUTING_V6_EVAL.json'}
V5 = 'real575_20261005/validation_20261006/ROUTES.json'
BASELINE = 'real575_20261005/runtime_extract_20261006/DEFAULT_BASELINE.jsonl'
SAVED = {'production': 'real575_20261005/validation_20261006/packets/', 'evaluation': 'real575_20261005/validation_20261006/eval_packets/',
         'development': 'real575_20261005/reader_packets/real336_dev/'}


def boom(*a, **k):
    raise AssertionError('a subprocess or a second reader was started where none may be')


class Replay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(tmp.cleanup)
        s = cls.s = Saved(tmp.name)
        cls.base = [s.line(BASELINE, i) for i in range(len(s.records))]
        v6 = {('validation120', f): (d['routed'], d['why']) for f, d in s.json(V6['validation120'])['routes'].items()}
        for d in s.json(V6['rest'])['rows']:
            v6['hard50' if d['set'] == 'answer pages' else 'development336', d['file']] = (d['routed'], d['why'])
        cls.v6, cls.v5 = v6, {f: d['routed'] for f, d in s.json(V5)['routes'].items()}
        cls.inputs = {r['id']: s.inputs(r) for r in s.records}
        with patch('subprocess.run', boom), patch('subprocess.Popen', boom):
            cls.work = cls.through_worker(tmp.name)
            cls.off, cls.held = {}, collections.Counter()
            for r in s.records:                                            # default mode, from the worker's results
                name, pic, html, tok, free, second = cls.inputs[r['id']]
                c = cls.work['results']['chandra'][r['id']]
                h, t = (c['result'][0], c['result'][1]['generation_tokens']) if c['result'] else (None, None)
                fr = readers.free_record(cls.work['results']['pp'][r['id']], cls.work['results']['ox'][r['id']])
                cls.held[second[0] is not None] += 1
                cls.off[r['id']] = pictures.read_picture(name, pic, h, t, fr, s.limit, second=lambda _, sec=second: boom() or sec)
            cls.on, cls.asks = {}, collections.Counter()
            for r in s.records:                                            # optional mode, saved readings only
                name, pic, html, tok, free, second = cls.inputs[r['id']]
                def answer(p, rid=r['id'], sec=second): cls.asks[rid] += 1; return sec
                cls.on[r['id']] = pictures.read_picture(name, pic, html, tok, free, s.limit, enable_sonnet=True, second=answer)

    @classmethod
    def through_worker(cls, tmp):  # Chandra, PP-OCR and OnnxTR as saved readers, each run once over the 506 occurrences
        s, by_sha, items = cls.s, {}, []
        for r in s.records:
            data = s.store.read(r['picture']); key = hashlib.sha256(data).hexdigest()
            _, _, html, tok, free, _ = cls.inputs[r['id']]
            by_sha.setdefault(key, (html, tok, free)); items.append((r['id'], data))
        def chandra():
            def read(d):
                html, tok, _ = by_sha[hashlib.sha256(d).hexdigest()]
                if html is None: raise RuntimeError('saved reader: no saved Chandra reading')
                return [html, dict(generation_tokens=tok)]
            return types.SimpleNamespace(read=read, settings=dict(reader='chandra', saved=True), status=readers._chandra_status)
        def free(tool):
            def make():
                def read(d):
                    row = by_sha[hashlib.sha256(d).hexdigest()][2]
                    if row is None or f'{tool}_error' in row: raise RuntimeError('saved reader: no saved free reading')
                    return dict(w=row['w'], h=row['h'], boxes=row[tool])
                return types.SimpleNamespace(read=read, settings=dict(reader=tool, saved=True), status=readers._free_status)
            return make
        folders = {k: f'{tmp}/worker_{k}' for k in ('chandra', 'pp', 'ox')}
        results = {'chandra': worker.run(folders['chandra'], items, chandra), 'pp': worker.run(folders['pp'], items, free('pp')), 'ox': worker.run(folders['ox'], items, free('ox'))}
        retried = []
        def failing():
            def read(d): retried.append(d); raise RuntimeError('simulated reader error on retry')
            return types.SimpleNamespace(read=read, settings=dict(reader='chandra', saved=True), status=readers._chandra_status)
        rerun = worker.run(folders['chandra'], items, failing)
        files = {k: sorted(f for f in os.listdir(v) if f.endswith('.json')) for k, v in folders.items()}   # this run's own output folders
        return dict(results=results, distinct=len(by_sha), files=files, retried=retried, rerun=rerun)

    def test_the_inventory_is_explicit(self):
        sets = collections.Counter(r['set'] for r in self.s.records)
        self.assertEqual(dict(sets), SETS)
        states = collections.Counter((r['chandra']['state'] != 'present', r['chandra']['cut_off_flag'], r['second_reading']['asset'] is None) for r in self.s.records)
        self.assertEqual(sum(v for (missing, _, _), v in states.items() if missing), 1)
        self.assertEqual(sum(v for (_, cut, _), v in states.items() if cut), 2)
        self.assertEqual(sum(v for (_, _, absent), v in states.items() if absent), 4)
        self.assertEqual(self.held, {True: 502, False: 4})

    def test_worker_reads_each_picture_once_and_retries_only_the_error(self):
        self.assertEqual(self.work['distinct'], 505)
        for tool, res in self.work['results'].items():
            self.assertEqual(len(res), 506, tool)
            self.assertEqual(len(self.work['files'][tool]), 505, tool)                 # one result file per distinct picture
        errors = [k for k, v in self.work['results']['chandra'].items() if v['status'] == 'error']
        self.assertEqual(errors, ['validation120/20p_14_0001558370-24-013452_adc-20240930xex10d2017.jpg'])
        self.assertEqual(len(self.work['retried']), 1)                   # only the error record is read again
        self.assertEqual(sum(v['status'] == 'error' for v in self.work['rerun'].values()), 1)

    def test_default_mode_equals_the_frozen_baseline(self):
        for r, b in zip(self.s.records, self.base):
            with self.subTest(r['id']):
                self.assertEqual((b['set'], b['name']), (r['set'], r['name']))
                asked, flags, text, rec = self.off[r['id']]
                self.assertFalse(asked); self.assertEqual(flags, b['flags']); self.assertEqual(rec['sonnet'], 'off')
                line = rec['extraction_status']
                self.assertTrue(status_follows_flags(line, flags) and 'Sonnet off' in line, line)
                self.assertLessEqual(len(line), 260)                          # the one status line stays short (modes.py)
                t, rc = body(*self.s.relocated(r, text, rec))
                self.assertEqual((t, rc), (evidence_whole(b['text'], b['record']), b['record']))

    def test_optional_mode_asks_exactly_the_saved_routes(self):
        asked = collections.Counter()
        for r in self.s.records:
            with self.subTest(r['id']):
                a, flags, text, rec = self.on[r['id']]
                self.assertEqual((a, flags), self.v6[r['set'], r['name']])
                self.assertEqual(self.asks[r['id']], 1 if a else 0)        # the saved reading is used once, only when asked
                asked[r['set']] += a
        self.assertEqual(dict(asked), {'validation120': 52, 'development336': 169, 'hard50': 43})

    def test_optional_mode_equals_the_saved_packets(self):
        for r, b in zip(self.s.records, self.base):
            with self.subTest(r['id']):
                a, flags, text, rec = self.on[r['id']]
                self.assertEqual(rec['sonnet'], 'on')
                self.assertTrue(status_follows_flags(rec['extraction_status'], flags) and 'Sonnet off' not in rec['extraction_status'])
                t, rc = body(*self.s.relocated(r, text, rec))
                exp = r['expected']['on']['assets']
                if exp == [BASELINE]:
                    want = (evidence_whole(b['text'], b['record']), b['record'])
                else:
                    md, js = exp
                    want = (evidence_whole(self.s.text(md)[:-1], self.s.json(js)), self.s.json(js))
                self.assertEqual((t, rc), want)

    def test_the_576_saved_packets(self):
        seen = collections.Counter()
        for r in self.s.records:
            if r['set'] == 'hard50':
                continue
            name, pic, html, tok, free, second = self.inputs[r['id']]
            a, _, text, rec = self.on[r['id']]
            if a:
                two = body(text, rec)                                                                   # the two-reader packet, from this pass when asked
            else:
                t2, r2 = packets.packet(name, pic, html or '', *second, free=free); two = (t2, json.loads(json.dumps(r2)))
            one = body(*self.off[r['id']][2:])                                                      # the Chandra-only packet
            kinds = ('production', 'evaluation') if r['set'] == 'validation120' else ('development',)
            for kind in kinds:
                want = one if kind == 'production' and not self.v5[r['name']] else two
                with self.subTest(kind=kind, picture=r['name']):
                    md, js = SAVED[kind] + r['name'] + '.md', SAVED[kind] + r['name'] + '.json'
                    self.assertIn(md, self.s.store.members('ocr.saved_packets.576')); self.assertIn(js, self.s.store.members('ocr.saved_packets.576'))
                    t, rc = self.s.relocated(r, *want)
                    self.assertEqual((t + '\n', rc), (evidence_whole(self.s.text(md)[:-1], self.s.json(js)) + '\n', self.s.json(js)))
                    seen[kind] += 1
        self.assertEqual(dict(seen), {'production': 120, 'evaluation': 120, 'development': 336})

    def test_known_reading_errors_stay_explicit(self):  # checked against the originals (ANSWERS_LOCAL_ONLY, CHECK10); NOT accuracy passes
        known = [('development336/157_0001558370-25-005434_dlr-20250424xex99d2g026.jpg', '5.1%', '5.1x', 'silent'),
                 ('development336/159_0000899051-24-000082_allcorp93024investorsupp016.jpg', '798', '788', 'silent'),
                 ('hard50/simon_p1_75', '8 7/8', '8 3/8', 'silent'),
                 ('validation120/1_21_0000950170-23-039035_img36028404_0.jpg', 'daxsomme', 'axsome', 'silent'),
                 ('validation120/2-4_12_0001766502-25-000014_chwy-20250202_g1.jpg', 'chemy', 'chewy', 'unconfirmed text'),
                 ('development336/230_c85f24b31df76c56.jpg', 'Dycorn', 'Dycom', 'conflict line with the printed word'),
                 ('development336/277_d77e4ee3141401c9.jpg', 'Laufes', 'Laufs', 'conflict line with the printed word')]
        for rid, wrong, printed, shown in known:
            with self.subTest(rid):
                _, flags, text, rec = self.off[rid]
                self.assertIn(wrong, text)                                 # the default output still holds the wrong reading
                conflict = any(printed in l for l in text.split('\n') if l.startswith('[FREE OCR conflict'))
                self.assertEqual(conflict, shown.startswith('conflict'))
                self.assertEqual('unconfirmed' in rec['extraction_status'], shown == 'unconfirmed text')
                if shown == 'silent':
                    self.assertFalse(any(w in rec['extraction_status'] for w in ('MISSING', 'INCOMPLETE', 'possible skipped', 'unconfirmed')))


if __name__ == '__main__':
    unittest.main()
