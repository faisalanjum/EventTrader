"""Independent positive and damaged controls for the six round-15 shared rules."""
import contextlib
import copy
import hashlib
import importlib.metadata
import io
import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.adapters import cache, edgartools_html as ed, prestep_headings as ph
from benchmarks.prepare.grader.tests.test_grade import GraderFixture, HTM_ID, XML_ID, PDF_ID, HTML, elem
from driver.prepare.convert import edgartools_html as eh


class BoundaryTests(unittest.TestCase):
    def test_contained_phrases_preserve_full_carrier_token_boundaries(self):
        for text, want, expected in [
            ('Revenue 10', 'Revenue 10', True), ('(Revenue 10).', 'Revenue 10', True),
            ('Revenue 10, approximately', 'Revenue 10', True), ('3.7 %', '3.7%', True),
            ('Revenue 100', 'Revenue 10', False), ('Revenue 10.5', 'Revenue 10', False),
            ('Revenue 10,000', 'Revenue 10', False), ('cannot own', 'not own', False),
            ('10 unitsOutstanding', '10 units', False), ('period 20240', 'period 2024', False),
            ('Revenue 100; Revenue 10', 'Revenue 10', True), ('not own', 'not own', True),
        ]:
            with self.subTest(text=text, want=want): self.assertEqual(grade.contains(text, want), expected)

    def test_marker_containment_allows_labels_but_never_cuts_numbers(self):
        for text, expected in [('Note1', True), ('Note(1)', True), ('Note2015', False), ('Note10', False), ('Note1.5', False), ('Note1,000', False), ('Note1, next', True)]:
            raw = ('<p>' + text + '</p>').encode(); a = {'byte_start': 0, 'byte_end_exclusive': len(raw)}
            rf = grade.RouteFile({'file_id': 's.htm', 'units': [{'id': 'u', 'kind': 'text', 'text': text, 'anchor': a}]}, raw)
            target = dict(key_id='syn/T', file_id='s.htm', format='cell/htm', split='development', fields={}, alternatives={}, excluded=set(), support={})
            g = grade.Grader(target, rf)
            with self.subTest(text=text): self.assertEqual(g.footnotes([{'marker_text': '1', 'anchor': a}], None, {'cells': [], '_order': 1}, [], 0)[0], 'pass' if expected else 'fail')

    def test_reference_phrase_and_inline_unit_use_token_boundaries(self):
        target = dict(key_id='syn/T', file_id='s.htm', type='structure', format='structure/htm', split='development',
                      anchor={}, fields={}, alternatives={}, excluded=set(), support={})
        rf = grade.RouteFile({'file_id': 's.htm', 'units': []}, b'')
        g = grade.Grader(target, rf)
        for text, expected in [('Revenue 10', 'pass'), ('Revenue 100', 'fail')]:
            with self.subTest(text=text):
                self.assertEqual(g.references([{'printed_text': 'Revenue 10'}], None, [], text)[0], expected)
                self.assertEqual(g.unit_printed('10', None, {'cells': []}, 0, [{'text': text}])[0], expected)

    def test_grouped_footnote_marks_keep_their_declared_source_positions(self):
        for marks in [('1', '2'), ('4', '5'), ('10', '11')]:
            group = ','.join(marks); raw = ('<p>Label<sup>' + group + '</sup></p>').encode()
            pos = raw.index(group.encode()); a = {'byte_start': 0, 'byte_end_exclusive': len(raw)}
            declarations = [{'marker_text': m, 'anchor': {'byte_start': pos + sum(len(x) + 1 for x in marks[:i]), 'byte_end_exclusive': pos + sum(len(x) + 1 for x in marks[:i]) + len(m)}} for i, m in enumerate(marks)]
            for text, expected in [('Label' + group, 'pass'), ('Label ' + group, 'pass'), ('Label' + group + '0', 'fail'), ('Label' + marks[0], 'fail')]:
                rf = grade.RouteFile({'file_id': 's.htm', 'units': [{'id': 'u', 'kind': 'text', 'text': text, 'anchor': a}]}, raw)
                target = dict(key_id='syn/T', file_id='s.htm', format='cell/htm', split='development', fields={}, alternatives={}, excluded=set(), support={})
                g = grade.Grader(target, rf)
                with self.subTest(marks=marks, text=text):
                    self.assertEqual(g.footnotes(declarations, None, {'cells': [], '_order': 1}, [], 0)[0], expected)

    def test_declared_numeric_marker_groups_also_work_without_an_html_text_map(self):
        loc = {'page': 1, 'region': [0, 0, 100, 20]}
        for marks in [('1', '2'), ('4', '5'), ('10', '11')]:
            declarations = [{'marker_text': m, 'anchor': loc} for m in marks]
            for text, expected in [('Label' + ','.join(marks), 'pass'), ('Label ' + ','.join(marks), 'pass'),
                                   ('Label' + ','.join(marks) + '0', 'fail'), ('Label' + marks[0], 'fail')]:
                rf = grade.RouteFile({'file_id': 's.pdf', 'units': [{'id': 'u', 'kind': 'text', 'text': text, 'anchor': loc}]}, None, 'pdf')
                target = dict(key_id='syn/T', file_id='s.pdf', format='cell/pdf', split='development', fields={}, alternatives={}, excluded=set(), support={})
                g = grade.Grader(target, rf)
                with self.subTest(marks=marks, text=text):
                    self.assertEqual(g.footnotes(declarations, None, {'cells': [], '_order': 1}, [], 0)[0], expected)

    def test_picture_inventory_tracks_visible_elements_including_void_visibility(self):
        cases = [('<img>', 1), ('<IMG><svg></svg>', 2), ('<!-- <img> -->', 0),
                 ('<script>let x="<img>";</script>', 0), ('<div title="<img>"></div>', 0),
                 ('<div style="display:none"><img></div>', 0), ('<img style="visibility:hidden">', 0),
                 ('<div style="visibility:hidden"><img style="visibility:visible"></div>', 1),
                 ('<div style="display:none"><img style="visibility:visible"></div>', 0),
                 ('<div style="opacity:0"><svg></svg></div>', 0), ('<img hidden>', 0)]
        for source, count in cases:
            with self.subTest(source=source):
                raw = source.encode(); a = {'byte_start': 0, 'byte_end_exclusive': len(raw)}
                rf = grade.RouteFile({'file_id': 's.htm', 'units': [{'id': 'u', 'kind': 'text', 'text': 'Invented 999', 'anchor': a}]}, raw, 'htm')
                self.assertEqual(grade.picture_at(rf, [a]), bool(count))
                g = grade.gates_for_file(rf, 'OK')
                if '<svg' in source or '<script' in source:  # foreign content this scanner does not follow, or a script: the page is not certified (round 19) — not measured, nothing counted
                    self.assertFalse(rf.vis.certain); self.assertIsNone(g['pictures']); self.assertEqual(g['dishonest'], 0); continue
                self.assertEqual(g['pictures'], count)
                self.assertEqual(g['dishonest'], 0 if count else 1)

    def test_invalid_positions_cannot_supply_any_lookup_and_do_not_crash(self):
        raw = b'<p>1</p>'; good = {'byte_start': 3, 'byte_end_exclusive': 4}
        cases = [({}, True), ({'byte_end_exclusive': 4}, True), ({'byte_start': 3}, True),
                 ({'byte_start': -1, 'byte_end_exclusive': 4}, True),
                 ({'byte_start': 3, 'byte_end_exclusive': 100}, True),
                 ({'page': 1, 'region': [-1, 0, 10, 20]}, True),
                 ({'page': 1, 'region': [0, 0, 101, 20]}, True),
                 ({'page': 1, 'region': [0, 0, 0, 20]}, True),
                 ({'page': 1, 'region': [0, 20]}, True), ({'page': 1, 'region': 'bad'}, True),
                 ({'page': 1, 'region': [0, 0, float('nan'), 20]}, True),
                 ({'page': True, 'region': [0, 0, 10, 20]}, True),
                 ([good, {}], True), ([good, {'page': 1, 'region': 'bad'}], True),
                 ('bad', True), (None, False), (good, False)]
        for a, bad in cases:
            with self.subTest(anchor=a):
                u = {'id': 'u', 'kind': 'text', 'text': '1', 'anchor': copy.deepcopy(a)}
                c = {'r': 0, 'c': 0, 'text': '1', 'anchor': copy.deepcopy(a)}
                tb = {'id': 't', 'kind': 'table', 'anchor': good, 'cells': [c]}
                rf = grade.RouteFile({'file_id': 's.htm', 'units': [u, tb], 'pages': {'1': [100, 100]}}, raw)
                valid = a == good
                self.assertEqual(bool(rf.units_at(good)), valid)
                self.assertEqual(bool(rf.cells_at(good)), valid)
                self.assertEqual(bool(rf.cells_in(tb)), valid)
                g = grade.gates_for_file(rf, 'OK')
                self.assertEqual(g['dishonest'], 2 if bad else 0)
                if a is None: self.assertEqual(g['unanchored'], 2)
        rf = grade.RouteFile({'file_id': 's.pdf', 'units': [{'id': 'p', 'kind': 'text', 'text': 'x', 'anchor': {'page': 1, 'region': [0, 0, 10, 20]}}]}, None)
        self.assertEqual(len(rf.units_at({'page': 1, 'region': [0, 0, 10, 20]})), 1)
        self.assertFalse(grade.gates_for_file(rf, 'OK')['anchors_measured'])

    def test_a_gap_flag_does_not_exempt_invented_text(self):
        for text, expected in [('', 0), ('Invented', 1)]:
            rf = grade.RouteFile({'file_id': 's.htm', 'units': [{'id': 'u', 'kind': 'image', 'text': text, 'link_flag': 'gap', 'anchor': {'byte_start': 0, 'byte_end_exclusive': 8}}]}, b'<p>1</p>')
            self.assertEqual(grade.gates_for_file(rf, 'OK')['dishonest'], expected)

    def test_heading_wrapper_uses_the_parsers_complete_opening_tag(self):
        class Read(HTMLParser):
            def __init__(self): super().__init__(); self.tags = []; self.words = []
            def handle_starttag(self, name, attrs): self.tags.append((name, attrs))
            def handle_data(self, value): self.words.append(value)
        for attrs in ['title="x > y"', "title='x > y'", 'title="x &gt; y"', 'title="plain"']:
            raw = ('<div ' + attrs + ' style="font-weight:bold">Annual results</div>').encode()
            old, new = Read(), Read(); old.feed(raw.decode()); new.feed(ph.mark_headings(raw).decode())
            with self.subTest(attrs=attrs):
                self.assertEqual(new.tags, old.tags + [('h2', [])]); self.assertEqual(new.words, old.words)


class ContextTests(GraderFixture):
    def test_source_order_also_distinguishes_blocks_on_the_same_visual_row(self):
        anchors = [{'page': 1, 'region': [0, 0, 40, 20]}, {'page': 1, 'region': [60, 0, 100, 20]}]
        parts = ['Left block', 'Right block']
        key = [dict(key_id=f'pkt/S{i + 1}', id=f'S{i + 1}', file_id=PDF_ID, type='structure', fields=dict(printed_text=p, kind='paragraph'), alternatives={}) for i, p in enumerate(parts)]
        (self.pkg / 'CLAUDE_ANSWER_KEY.json').write_text(json.dumps(key))
        (self.pkg / 'CLAUDE_KEY_FLAGS.json').write_text(json.dumps({'uncertain': []}))
        (self.pkg / 'KEY_SUPPORT_MAP.json').write_text('{}')
        (self.pkg / 'converter_checks/REGRESSION_CASES.json').unlink()
        packet = json.loads((self.pkt / 'targets.json').read_text())
        packet['targets'] = [dict(id=f'S{i + 1}', kind='structure', file_id=PDF_ID, block_anchor=a) for i, a in enumerate(anchors)]
        (self.pkt / 'targets.json').write_text(json.dumps(packet))
        for table in (False, True):
            for reverse in (False, True):
                def mutate(routes):
                    items = list(zip(parts, anchors))
                    if reverse: items.reverse()
                    if table: units = [dict(id='t', kind='table', anchor=anchors, cells=[dict(r=0, c=i, text=p, anchor=a) for i, (p, a) in enumerate(items)])]
                    else: units = [dict(id=f'u{i}', kind='text', text=p, anchor=a) for i, (p, a) in enumerate(items)]
                    routes[PDF_ID]['units'] = units
                with self.subTest(table=table, reverse=reverse):
                    result = self.run_grader(mutate)
                    self.assertEqual([r['verdict'] for r in result['results'] if r['check'] == 'order'], ['fail' if reverse else 'pass'] * 2)

    def test_invalid_context_cannot_pass_xml_or_html_fallback(self):
        for name in ('xml_unit', 'xml_person', 'fallback_unit'):
            with self.subTest(name=name):
                if name == 'fallback_unit':
                    s = json.loads((self.pkg / 'KEY_SUPPORT_MAP.json').read_text()); s['pkt/T01']['unit_printed'] = {'how': 'none'}
                    (self.pkg / 'KEY_SUPPORT_MAP.json').write_text(json.dumps(s))
                kid, check = ('pkt/T01', 'unit_printed') if name == 'fallback_unit' else ('pkt/X01', 'row_context' if name == 'xml_person' else 'unit_printed')
                baseline = self.run_grader()
                self.assertEqual(next(r['verdict'] for r in baseline['results'] if r['key_id'] == kid and r['check'] == check), 'pass')
                def mutate(routes):
                    if name.startswith('xml'):
                        field = 'reportingPersonName' if name == 'xml_person' else 'securitiesClassTitle'
                        u = next(u for u in routes[XML_ID]['units'] if grade.local(u.get('name', '')) == field and (field != 'reportingPersonName' or u.get('text') == 'Beta'))
                    else: u = next(c for t in routes[HTM_ID]['units'] for c in t.get('cells', []) if c['anchor'] == elem('unit'))
                    u['anchor'] = {'byte_start': -1, 'byte_end_exclusive': 100000}
                result = self.run_grader(mutate)
                self.assertNotEqual(next(r['verdict'] for r in result['results'] if r['key_id'] == kid and r['check'] == check), 'pass')

    def test_separate_merged_and_reversed_blocks_have_proven_order(self):
        parts = ['The continuous paragraph begins here', 'and finishes on the next page.']
        anchors = [{'page': i + 1, 'region': [0, 0, 100, 20]} for i in range(2)]
        packet = json.loads((self.pkt / 'targets.json').read_text())
        packet['targets'] = [dict(id=f'S{i + 1}', kind='structure', file_id=PDF_ID, block_anchor=a) for i, a in enumerate(anchors)]
        (self.pkt / 'targets.json').write_text(json.dumps(packet))
        (self.pkg / 'CLAUDE_KEY_FLAGS.json').write_text(json.dumps({'uncertain': []}))
        (self.pkg / 'KEY_SUPPORT_MAP.json').write_text('{}')
        (self.pkg / 'converter_checks/REGRESSION_CASES.json').unlink()
        for approximate in (False, True):
            key = [dict(key_id=f'pkt/S{i + 1}', id=f'S{i + 1}', file_id=PDF_ID, type='structure', fields=dict(printed_text=p, kind='image' if approximate else 'paragraph'), alternatives={}) for i, p in enumerate(parts)]
            (self.pkg / 'CLAUDE_ANSWER_KEY.json').write_text(json.dumps(key))
            # Inject only the fixture's approximate flag, without modifying the real package or policy.
            original = grade.load_key
            def load(*args, **kwargs):
                ts = original(*args, **kwargs)
                for t in ts: t['approximate'] = approximate
                return ts
            for mode in ('separate', 'merged', 'reverse', 'unmapped', 'table', 'table_reverse'):
                def mutate(routes):
                    reverse = mode in ('reverse', 'table_reverse'); p = parts[::-1] if reverse else parts; a = anchors[::-1] if reverse else anchors
                    if mode == 'separate': units = [dict(id=f'u{i}', kind='text', text=x, anchor=b) for i, (x, b) in enumerate(zip(p, a))]
                    elif mode.startswith('table'):
                        units = [dict(id='t', kind='table', anchor=a, cells=[dict(r=i, c=0, text=x, anchor=b) for i, (x, b) in enumerate(zip(p, a))])]
                    else:
                        loc = a if mode == 'unmapped' else [dict(a[0], charspan=[0, len(p[0])]), dict(a[1], charspan=[len(p[0]) + 1, len(' '.join(p))])]
                        units = [dict(id='u', kind='text', text=' '.join(p), anchor=loc)]
                    routes[PDF_ID]['units'] = units
                with self.subTest(approximate=approximate, mode=mode), patch.object(grade, 'load_key', side_effect=load):
                    result = self.run_grader(mutate)
                    expected = 'fail' if mode in ('reverse', 'table_reverse') else 'unresolved' if mode == 'unmapped' else 'pass'
                    self.assertEqual([r['verdict'] for r in result['results'] if r['check'] == 'order'], [expected, expected])


class EdgarCacheTests(unittest.TestCase):
    def test_receipt_controls_source_settings_outputs_and_producing_version(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / 's.htm'; src.write_bytes(b'<p>Revenue 10.</p>'); out = root / 'run'
            sources = [dict(file_id='s.htm', path=src, sha256=grade.sha256(src.read_bytes()), split='development')]
            stub = types.ModuleType('edgar.documents'); stub.parse_html = lambda text: types.SimpleNamespace(root=object(), metadata=types.SimpleNamespace(xbrl_data=[]))
            def run(reuse=False, version='OLD', failure=False):
                with patch.dict(sys.modules, {'edgar': types.ModuleType('edgar'), 'edgar.documents': stub}), patch.object(grade, 'load_sources', return_value=sources), patch('importlib.metadata.version', return_value=version), patch('driver.prepare.convert.edgartools_html.dump', side_effect=RuntimeError('interrupted') if failure else None, return_value=dict(type='ParagraphNode', text='Revenue 10.')), redirect_stdout(io.StringIO()):
                    ed.main(['--key', td, '--split', 'development', '--out', str(out)] + (['--reuse-raw'] if reuse else []))
                return json.loads((out / 'route/s.htm.json').read_text())
            self.assertEqual(run()['status'], 'OK')
            reused = run(True, 'NEW'); self.assertEqual(reused['status'], 'OK'); self.assertEqual(reused['route']['version'], 'edgartools OLD')
            raw = out / 'raw/s.htm.edgartools.json'; receipt = out / 'raw/s.htm.meta.json'
            raw.write_bytes(raw.read_bytes() + b' '); self.assertEqual(run(True)['status'], 'FAILED')
            run(); src.write_bytes(b'<p>Revenue 100.</p>'); sources[0]['sha256'] = grade.sha256(src.read_bytes())
            self.assertEqual(run(True)['status'], 'FAILED'); src.write_bytes(b'<p>Revenue 10.</p>'); sources[0]['sha256'] = grade.sha256(src.read_bytes())
            run(); m = json.loads(receipt.read_text()); m['settings'] = {'parse_html': 'changed'}; receipt.write_text(json.dumps(m)); self.assertEqual(run(True)['status'], 'FAILED')
            run(); m = json.loads(receipt.read_text()); m.pop('status'); receipt.write_text(json.dumps(m)); self.assertEqual(run(True)['status'], 'FAILED')
            run(); self.assertEqual(run(failure=True)['status'], 'FAILED'); self.assertFalse(receipt.exists()); self.assertEqual(run(True)['status'], 'FAILED')
            run()
            with patch.object(cache, 'save', side_effect=OSError('interrupted receipt save')):
                with self.assertRaises(OSError): run()
            self.assertFalse(receipt.exists()); self.assertEqual(run(True)['status'], 'FAILED')
            run(); receipt.unlink(); self.assertEqual(run(True)['status'], 'FAILED')


# The command line's timing with a reused parse (Codex CODEX_CLEANUP_R1_VERDICT C4; his probe, ported unchanged)
sha = lambda raw: hashlib.sha256(raw).hexdigest()
RAW = b'<p><i>10</i> 20</p>'
TREE = {'type': 'DocumentNode', 'children': [{'type': 'ParagraphNode', 'text': '10 20'}]}


class ReplayTiming(unittest.TestCase):
    def test_cached_tool_duration_is_not_subtracted_from_current_adapter_time(self):
        from benchmarks.prepare.grader.adapters import edgartools_html as cli, cache
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / 's.htm'; src.write_bytes(RAW)
            out = root / 'out'; raw_dir = out / 'raw'; raw_dir.mkdir(parents=True)
            cached = raw_dir / 's.htm.edgartools.json'; cached.write_text(json.dumps(TREE))
            cache.save(raw_dir / 's.htm.meta.json', [cached], sha256=sha(RAW), version='edgartools prior',
                       settings=eh.SETTINGS, status='OK', tool_seconds=600.0)
            sources = [dict(file_id='s.htm', path=src, sha256=sha(RAW), split='development')]
            with patch.object(cli.grade, 'load_sources', return_value=sources), patch.object(cli, 'parse', side_effect=AssertionError('must reuse saved parse')), contextlib.redirect_stdout(io.StringIO()):
                cli.main(['--key', 'unused', '--split', 'development', '--out', str(out), '--reuse-raw'])
            facts = json.loads((out / 'facts.json').read_text())['files']['s.htm']
            self.assertEqual(facts['tool_seconds'], 600.0)
            self.assertEqual(facts['version'], 'edgartools prior')
            self.assertGreaterEqual(facts['adapter_seconds'], 0)
            self.assertLess(facts['adapter_seconds'], 10)


class SettingsCache(unittest.TestCase):
    def test_a_parse_saved_under_the_previous_settings_is_refused_and_one_under_the_current_settings_is_reused(self):  # Codex, accuracy-fable-1: a lossy parse saved before page-number candidates were kept is never reused
        from benchmarks.prepare.grader.adapters import edgartools_html as cli, cache
        previous = {k: v for k, v in eh.SETTINGS.items() if k != 'page_number_candidates'}
        for settings, status in ((previous, 'FAILED'), (eh.SETTINGS, 'OK')):
            with tempfile.TemporaryDirectory() as td, self.subTest(saved_under=sorted(settings)[-1]):
                root = Path(td); src = root / 's.htm'; src.write_bytes(RAW); out = root / 'out'; raw_dir = out / 'raw'; raw_dir.mkdir(parents=True)
                cached = raw_dir / 's.htm.edgartools.json'; cached.write_text(json.dumps(TREE))
                cache.save(raw_dir / 's.htm.meta.json', [cached], sha256=sha(RAW), version='edgartools prior', settings=settings, status='OK', tool_seconds=1.0)
                sources = [dict(file_id='s.htm', path=src, sha256=sha(RAW), split='development')]
                with patch.object(cli.grade, 'load_sources', return_value=sources), patch.object(cli, 'parse', side_effect=AssertionError('a saved parse must decide')), contextlib.redirect_stdout(io.StringIO()):
                    cli.main(['--key', 'unused', '--split', 'development', '--out', str(out), '--reuse-raw'])
                route = json.loads((out / 'route' / 's.htm.json').read_text())
                self.assertEqual(route['status'], status)
                if status == 'FAILED': self.assertIn('other settings', route['error'])
                else: self.assertEqual(route['route']['settings']['page_number_candidates'], 'kept')


if __name__ == '__main__': unittest.main()
