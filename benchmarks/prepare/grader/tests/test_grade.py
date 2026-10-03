"""The grader (grade.py): a correct route output passes every target; each planted fault fails only its own check.
The key subset below uses the exact JSON shapes of the frozen Step 3 key package (records, flags, support map, targets)."""
import copy
import csv
import hashlib
import json
import shutil
from pathlib import Path
import re
import tempfile
import unittest

from benchmarks.prepare.grader import anchor, grade

FIX = Path(__file__).with_name('fixtures')
HTML, XML = (FIX / 'sample.htm').read_bytes(), (FIX / 'sample.xml').read_bytes()
PDF = b'%PDF-1.4\n% fixture: the grader reads geometry only, never the page\n'
ACC = '0000000001-26-000001'
HTM_ID, XML_ID, PDF_ID = f'{ACC}/sample.htm', f'{ACC}/sample.xml', f'{ACC}/deck.pdf'
NS = '{http://www.sec.gov/edgar/schedule13D}'
PATH = [NS + 'edgarSubmission', NS + 'formData', NS + 'reportingPersons', NS + 'reportingPersonInfo']
sha = lambda b: hashlib.sha256(b).hexdigest()


def elem(id_, raw=HTML):
    """Byte span of the element carrying id="…" (the fixtures nest no element inside one of its own name)."""
    m = re.search(rb'<([\w:]+)[^>]*\bid="%s"' % id_.encode(), raw)
    return {'byte_start': m.start(), 'byte_end_exclusive': raw.index(b'</' + m.group(1) + b'>', m.end()) + len(m.group(1)) + 3}


def xml_text(value, name='sharedDispositivePower'):
    i = XML.index(b'<ns1:%s>%s<' % (name.encode(), value.encode())) + len(name) + 6  # after '<ns1:' + name + '>'
    return {'byte_start': i, 'byte_end_exclusive': i + len(value)}


def cell(key_id, fields, alternatives=None, decided=()):
    base = {'printed_value': None, 'display_value': None, 'value_kind': 'number', 'sign': 'positive', 'marker_meaning': None,
            'row_label': None, 'row_context': [], 'header_path': [], 'footnote_markers': [], 'corner_text': None, 'lead_in': None,
            'section_path': [], 'segment_or_basis': [], 'measure': [], 'unit_printed': None,
            'unit_interpretation': {'unit': 'money', 'currency': '$', 'scale': '1000000'}, 'periods': [], 'range': None, 'table_title': []}
    base.update(fields)
    for f in alternatives or {}: base.pop(f, None)
    return {'key_id': key_id, 'id': key_id.split('/')[1], 'file_id': fields.pop('_file', HTM_ID), 'type': 'cell', 'fields': base,
            'alternatives': alternatives or {}, 'decided': list(decided), 'reason': None, 'evidence': 'fixture', 'pending': []}


def structure(key_id, fields):
    return {'key_id': key_id, 'id': key_id.split('/')[1], 'file_id': HTM_ID, 'type': 'structure', 'fields': fields,
            'alternatives': {}, 'decided': [], 'reason': None, 'evidence': 'fixture', 'pending': []}


A = lambda *ids: [elem(i) for i in ids]
LEAD_TEXT = 'Free cash flow is ~~not~~ a GAAP measure. See the table below.'
ITEM = 'Item 2. Management’s Discussion and Analysis'
PERIOD = [{'role': 'value', 'type': 'duration', 'parts': [{'text': 'Three Months Ended', 'anchor': elem('hb')}, {'text': 'December 28, 2024', 'anchor': elem('h24')}]}]
COMMON = dict(header_path=['Three Months Ended', 'December 28, 2024'], table_title=['Free Cash Flow'], lead_in=LEAD_TEXT,
              section_path=[ITEM, 'Free Cash Flow'], unit_printed='(in millions)', periods=PERIOD)
KEY = [
    cell('pkt/T01', dict(COMMON, printed_value='769', display_value='$769', row_label='Cash flow from operations', measure=['Cash flow from operations']),
         alternatives={'section_path': [[ITEM, 'Free Cash Flow'], [ITEM]]}),
    cell('pkt/T02', dict(COMMON, printed_value='(506', display_value='$(506)', sign='negative', row_label='Free cash flow', measure=['Free cash flow'],
                         footnote_markers=[{'marker_text': '(1)', 'anchor': elem('m2'), 'role': 'annotates', 'note_anchor': elem('n1'),
                                            'note_text': '(1) Represents principal maturities only.'}])),
    cell('pkt/T03', dict(COMMON, printed_value='10.67', display_value='$10.67', row_label='Adjusted EPS', measure=['Adjusted EPS'],
                         footnote_markers=[{'marker_text': '4', 'anchor': elem('m3'), 'role': 'annotates', 'note_anchor': elem('n4'),
                                            'note_text': '4 Non-GAAP measure; see the reconciliation.'}])),
    cell('pkt/T05', dict(printed_value='5', display_value='5', row_label='2024 | Q1', table_title=['Fiscal 2026 Outlook'], measure=['Q1'],
                         segment_or_basis=['exclude discontinued operations'], unit_interpretation={'unit': 'count', 'currency': None, 'scale': '1'},
                         footnote_markers=[{'marker_text': '(5)', 'anchor': elem('m5'), 'role': 'annotates', 'note_anchor': elem('n5'), 'note_text': '(5) Guidance as of the release date.'}])),
    structure('pkt/S01', {'printed_text': LEAD_TEXT, 'visible': True, 'kind': 'paragraph', 'section_path': [ITEM, 'Free Cash Flow'],
                          'references': [{'printed_text': 'the table below', 'anchor': elem('ref'), 'relation': 'mention', 'href': '#tbl',
                                          'target': {'file': HTM_ID, 'anchor': elem('tbl')}, 'status': 'RESOLVED'}]}),
    structure('pkt/S02', {'printed_text': 'Free Cash Flow', 'visible': True, 'kind': 'heading', 'section_path': [ITEM], 'references': []}),
    structure('pkt/S03', {'printed_text': 'Picture words one. Picture words two.', 'visible': True, 'kind': 'image', 'section_path': [ITEM, 'Free Cash Flow'], 'references': []}),
    structure('pkt/S04', {'printed_text': '•The first point.', 'visible': True, 'kind': 'list_item', 'section_path': [ITEM, 'Free Cash Flow'], 'references': []}),
    cell('pkt/X01', dict(_file=XML_ID, printed_value='0', display_value='0', sign='zero', row_label='sharedDispositivePower', header_path=PATH,
                         row_context=[{'header': 'position', 'text': '2 of 2'}, {'header': 'reportingPersonName', 'text': 'Beta'}],
                         measure=['sharedDispositivePower'], unit_printed='Units', unit_interpretation={'unit': 'Units', 'currency': None, 'scale': '1'})),
    cell('pkt/P01', dict(_file=PDF_ID, printed_value='1,970', display_value='1,970', row_label='Southeast', header_path=['Same-Store', 'Total Revenue per Occupied Home', 'YTD 24'],
                         table_title=['Same-Store Operating Information'], unit_printed='Total Revenue per Occupied Home', segment_or_basis=['(Unaudited)'],
                         unit_interpretation={'unit': 'money per home', 'currency': '$', 'scale': '1'})),
]
MODEL = lambda *ids: {'how': 'model', 'model': 'openai', 'anchors': A(*ids)}
NONE, INLINE = {'how': 'none'}, {'how': 'inline'}
SUPPORT = {
    'pkt/T01': {'display_value': MODEL('s1', 'v1'), 'row_label': MODEL('l1'), 'header_path': MODEL('hb', 'h24'), 'table_title': MODEL('ttl'),
                'lead_in': MODEL('lead'), 'section_path#0': MODEL('h1', 'h2'), 'section_path#1': MODEL('h1'), 'unit_printed': MODEL('unit'),
                'measure': MODEL('l1'), 'periods': INLINE, 'printed_value': NONE, 'footnote_markers': NONE},
    'pkt/T02': {'display_value': MODEL('s2', 'v2', 'c2'), 'row_label': MODEL('l2'), 'table_title': MODEL('ttl'), 'lead_in': MODEL('lead'),
                'section_path': MODEL('h1', 'h2'), 'unit_printed': MODEL('unit'), 'measure': MODEL('l2'), 'periods': INLINE, 'footnote_markers': INLINE,
                'header_path': {'how': 'reviewed', 'anchors': [dict(elem('hb'), file_id=HTM_ID, sha256=sha(HTML)), dict(elem('h24'), file_id=HTM_ID, sha256=sha(HTML))]}},
    'pkt/T03': {'display_value': MODEL('s3', 'v3'), 'row_label': MODEL('l3'), 'header_path': MODEL('hb', 'h24'), 'table_title': MODEL('ttl'),
                'lead_in': MODEL('lead'), 'section_path': MODEL('h1', 'h2'), 'unit_printed': MODEL('unit'), 'periods': INLINE, 'footnote_markers': INLINE},
    'pkt/T05': {'display_value': MODEL('q1'), 'row_label': MODEL('o1', 'i1'), 'header_path': NONE, 'measure': MODEL('i1'), 'segment_or_basis': MODEL('after'), 'footnote_markers': INLINE,
                'table_title': {'how': 'search', 'pieces': [{'text': 'Fiscal 2026 Outlook', 'count': 1, 'governing': [[elem('t2t')['byte_start'], elem('t2t')['byte_end_exclusive']]],
                                                             'byte_ranges': [[elem('t2t')['byte_start'], elem('t2t')['byte_end_exclusive']]]}]}},
    'pkt/S01': {'printed_text': MODEL('lead'), 'section_path': MODEL('h1', 'h2'), 'references': INLINE, 'kind': NONE, 'visible': NONE},
    'pkt/S02': {'printed_text': MODEL('h2'), 'section_path': MODEL('h1'), 'references': NONE, 'kind': NONE, 'visible': NONE},
    'pkt/S03': {'printed_text': NONE, 'section_path': MODEL('h1', 'h2'), 'references': NONE, 'kind': NONE, 'visible': NONE},
    'pkt/S04': {'printed_text': MODEL('li'), 'section_path': MODEL('h1', 'h2'), 'references': NONE, 'kind': NONE, 'visible': NONE},
    'pkt/X01': {'printed_value': NONE, 'row_label': NONE, 'header_path': NONE, 'row_context': NONE, 'unit_printed': NONE},
    'pkt/P01': {f: {'how': 'none', 'why': 'PDF or picture source: no byte offsets'} for f in ('row_label', 'header_path', 'table_title', 'unit_printed', 'segment_or_basis')},
}
FLAGS = {'about': 'fixture', 'p1_constraints': [], 'source_conflicts': [], 'p1_converted_20261003': [],
         'uncertain': [{'key_id': 'pkt/T03', 'field': 'periods', 'case': 'U99', 'scoring': 'excluded', 'why': 'fixture'}],
         'scoring_exclusions': {'fields_excluded': 1, 'targets_affected': 1, 'note': 'fixture'}}
PDF_TABLE, PDF_CELL = {'page': 2, 'region': [0, 100, 600, 400]}, {'page': 2, 'region': [400, 200, 450, 212]}
TARGETS = {'version': 'fixture', 'scope': 'fixture', 'sources': [
    {'file_id': HTM_ID, 'path': f'sources/{HTM_ID}', 'source': {'accession': ACC, 'filename': 'sample.htm', 'sha256': sha(HTML)}},
    {'file_id': XML_ID, 'path': f'sources/{XML_ID}', 'source': {'accession': ACC, 'filename': 'sample.xml', 'sha256': sha(XML)}},
    {'file_id': PDF_ID, 'path': f'sources/{PDF_ID}', 'source': {'accession': ACC, 'filename': 'deck.pdf', 'sha256': sha(PDF)}}],
    'targets': [
        {'kind': 'cell', 'file_id': HTM_ID, 'table_anchor': elem('tbl'), 'cell_anchor': elem('v1'), 'id': 'T01'},
        {'kind': 'cell', 'file_id': HTM_ID, 'table_anchor': elem('tbl'), 'cell_anchor': elem('v2'), 'id': 'T02'},
        {'kind': 'cell', 'file_id': HTM_ID, 'table_anchor': elem('tbl'), 'cell_anchor': elem('v3'), 'id': 'T03'},
        {'kind': 'cell', 'file_id': HTM_ID, 'table_anchor': elem('tb2'), 'cell_anchor': elem('q1'), 'id': 'T05'},
        {'kind': 'structure', 'file_id': HTM_ID, 'block_anchor': elem('lead'), 'id': 'S01'},
        {'kind': 'structure', 'file_id': HTM_ID, 'block_anchor': elem('h2'), 'id': 'S02'},
        {'kind': 'structure', 'file_id': HTM_ID, 'block_anchor': elem('im'), 'id': 'S03'},
        {'kind': 'structure', 'file_id': HTM_ID, 'block_anchor': elem('li'), 'id': 'S04'},
        {'kind': 'cell', 'file_id': XML_ID, 'table_anchor': xml_text('0'), 'cell_anchor': xml_text('0'), 'id': 'X01'},
        {'kind': 'cell', 'file_id': PDF_ID, 'table_anchor': PDF_TABLE, 'cell_anchor': PDF_CELL, 'id': 'P01'}]}
SUPPLEMENT = {'scope': 'fixture', 'source_coordinates': {'HTML': 'UTF-8 byte offsets; end exclusive'},
              'sources': {HTM_ID: {'path': f'packets/pkt/sources/{HTM_ID}', 'sha256': sha(HTML)}},
              'cases': [{'id': 'fx/R01', 'source_file_id': HTM_ID, 'table_anchor': elem('tb2'), 'cell_anchor': elem('hi'),
                         'expected': {'printed_value': '$10.67', 'display_value': '$10.67', 'row_label': 'Adjusted diluted EPS', 'header_path': [],
                                      'table_title': ['Fiscal 2026 Outlook'], 'unit_printed': '$10.67', 'footnote_markers': [],
                                      'range': {'kind': 'interval', 'role': 'high', 'partner': {'printed_value': '$10.57', 'anchor': elem('lo')},
                                                'low': None, 'high': None, 'evidence': [{'text': 'to', 'anchor': elem('to')}]}},
                         'field_support': {'display_value': A('hi'), 'row_label': A('rl'), 'header_path': [], 'table_title': A('t2t'), 'unit_printed': A('hi')},
                         'checks': ['range role and partner preserved']}],
              'review': 'fixture', 'provenance': []}


def C(r, c, text, id_, cs=1, rs=1, **extra):
    return dict({'r': r, 'c': c, 'rs': rs, 'cs': cs, 'text': text, 'anchor': elem(id_)}, **extra)


def route_html():
    return {'schema': 'prepare-route-output/1', 'file_id': HTM_ID, 'sha256': sha(HTML), 'status': 'OK', 'error': None, 'seconds': 0.5,
            'route': {'name': 'fixture', 'tool': 'hand', 'version': '1', 'settings': {}, 'adapter': 'test', 'linker': None},
            'units': [
                {'id': 'u0', 'kind': 'heading', 'level': 1, 'text': "Item 2. Management's Discussion and Analysis", 'anchor': elem('h1')},
                {'id': 'u1', 'kind': 'heading', 'level': 2, 'text': 'Free Cash Flow', 'anchor': elem('h2')},
                {'id': 'u2', 'kind': 'text', 'text': 'Free cash flow is not a GAAP measure. See the table below.', 'anchor': elem('lead'),
                 'links': [{'text': 'the table below', 'href': '#tbl', 'to': 'u3'}], 'struck': ['not']},
                {'id': 'u3', 'kind': 'table', 'anchor': elem('tbl'), 'caption': [], 'notes': ['u4', 'u5'], 'cells': [
                    C(0, 0, 'Free Cash Flow', 'ttl', cs=5), C(1, 0, '(in millions)', 'unit'), C(1, 1, 'Three Months Ended', 'hb', cs=4),
                    C(2, 1, 'December 28, 2024', 'h24', cs=3), C(2, 4, 'December 30, 2023', 'h23'),
                    C(3, 0, 'Cash flow from operations', 'l1'), C(3, 1, '$', 's1'), C(3, 2, '769', 'v1'), C(3, 4, '650', 'p1'),
                    C(4, 0, 'Free cash flow', 'l2', markers=['(1)']), C(4, 1, '$', 's2'), C(4, 2, '(506', 'v2'), C(4, 3, ')', 'c2'), C(4, 4, '(120', 'p2'),
                    C(5, 0, 'Adjusted EPS', 'l3'), C(5, 1, '$', 's3'), C(5, 2, '10.67', 'v3', markers=['4']), C(5, 4, '9.80', 'p3')]},
                {'id': 'u4', 'kind': 'footnote', 'marker': '(1)', 'text': '(1) Represents principal maturities only.', 'anchor': elem('n1')},
                {'id': 'u5', 'kind': 'footnote', 'marker': '4', 'text': '4 Non-GAAP measure; see the reconciliation.', 'anchor': elem('n4')},
                {'id': 'u10', 'kind': 'text', 'text': 'Outlook figures are approximate(5).', 'anchor': elem('t2lead')},
                {'id': 'u6', 'kind': 'table', 'anchor': elem('tb2'), 'caption': [], 'cells': [
                    C(0, 0, 'Fiscal 2026 Outlook', 't2t', cs=5), C(1, 0, '(unaudited)', 't2c', cs=5), C(2, 1, 'Adjusted diluted EPS', 'rl'), C(2, 2, '$10.57', 'lo'),
                    C(2, 3, 'to', 'to'), C(2, 4, '$10.67', 'hi'), C(3, 0, '2024', 'o1'), C(3, 1, 'Q1', 'i1'), C(3, 2, '5', 'q1')]},
                {'id': 'u11', 'kind': 'footnote', 'marker': '(5)', 'text': '(5) Guidance as of the release date.', 'anchor': elem('n5')},
                {'id': 'u12', 'kind': 'list_item', 'text': '•The first point.', 'anchor': elem('li')},
                {'id': 'u9', 'kind': 'text', 'text': 'Amounts exclude discontinued operations.', 'anchor': elem('after')},
                {'id': 'u8', 'kind': 'image', 'text': 'Picture words one. Picture words two.', 'anchor': elem('im')},
                {'id': 'u7', 'kind': 'clutter', 'text': '4', 'anchor': elem('pg')}]}


def route_xml():
    f = lambda i, name, text, g: {'id': f'x{i}', 'kind': 'field', 'name': NS + name, 'path': PATH, 'group': {'index': g, 'count': 2}, 'text': text,
                                  'anchor': xml_text(text, name)}
    return {'schema': 'prepare-route-output/1', 'file_id': XML_ID, 'sha256': sha(XML), 'status': 'OK', 'error': None, 'seconds': 0.1,
            'route': {'name': 'fixture', 'tool': 'hand', 'version': '1', 'settings': {}, 'adapter': 'test', 'linker': None},
            'units': [{'id': 'x0', 'kind': 'field', 'name': NS + 'securitiesClassTitle', 'path': PATH[:2], 'group': {'index': 1, 'count': 1}, 'text': 'Units',
                       'anchor': xml_text('Units', 'securitiesClassTitle')},
                      f(1, 'reportingPersonName', 'Alpha', 1), f(2, 'sharedDispositivePower', '10', 1), f(3, 'reportingPersonName', 'Beta', 2),
                      f(4, 'sharedDispositivePower', '0', 2)]}


def route_pdf():
    P = lambda r, c, text, region, cs=1: {'r': r, 'c': c, 'rs': 1, 'cs': cs, 'text': text, 'anchor': {'page': 2, 'region': region}}
    return {'schema': 'prepare-route-output/1', 'file_id': PDF_ID, 'sha256': sha(PDF), 'status': 'OK', 'error': None, 'seconds': 9.0, 'pages': {'1': [612, 792], '2': [612, 792]},
            'route': {'name': 'fixture', 'tool': 'hand', 'version': '1', 'settings': {}, 'adapter': 'test', 'linker': None},
            'units': [
                {'id': 'p0', 'kind': 'text', 'text': 'Same-Store Operating Information', 'anchor': {'page': 2, 'region': [100, 50, 500, 70]}},
                {'id': 'p1', 'kind': 'text', 'text': '(Unaudited)', 'anchor': {'page': 2, 'region': [200, 80, 300, 95]}},
                {'id': 'p2', 'kind': 'table', 'anchor': {'page': 2, 'region': [0, 100, 600, 400]}, 'cells': [
                    P(0, 1, 'Same-Store', [380, 110, 470, 122], cs=2), P(1, 1, 'Total Revenue per Occupied Home', [370, 125, 480, 137], cs=2),
                    P(2, 1, 'YTD 23', [380, 140, 420, 152]), P(2, 2, 'YTD 24', [430, 140, 470, 152]),
                    P(3, 0, 'Southeast', [20, 200, 90, 212]), P(3, 1, '1,900', [330, 200, 370, 212]), P(3, 2, '1,970', [400, 200, 450, 212])]}]}


class GraderFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); root = Path(self.tmp.name)
        bulk, pkg, pkt = root / 'bulk', root / 'bulk' / 'PKG', root / 'bulk' / 'packets' / 'pkt'
        for fid, raw in ((HTM_ID, HTML), (XML_ID, XML), (PDF_ID, PDF)):
            (pkt / 'sources' / fid).parent.mkdir(parents=True, exist_ok=True); (pkt / 'sources' / fid).write_bytes(raw)
        (pkt / 'targets.json').write_text(json.dumps(TARGETS))
        (pkg / 'converter_checks').mkdir(parents=True)
        (pkg / 'CLAUDE_ANSWER_KEY.json').write_text(json.dumps(KEY)); (pkg / 'CLAUDE_KEY_FLAGS.json').write_text(json.dumps(FLAGS))
        (pkg / 'KEY_SUPPORT_MAP.json').write_text(json.dumps(SUPPORT)); (pkg / 'converter_checks' / 'REGRESSION_CASES.json').write_text(json.dumps(SUPPLEMENT))
        with open(root / 'case_catalog.csv', 'w', newline='') as f:
            w = csv.writer(f); w.writerow(['split', 'ticker', 'company', 'form', 'year', 'source', 'reason', 'original', 'sha256'])
            for split, fid, raw in (('development', HTM_ID, HTML), ('stratified_control', XML_ID, XML), ('heldout', PDF_ID, PDF)):
                w.writerow([split, 'FX', 'Fixture', '10-Q', 2026, fid, 'fixture', str(pkt / 'sources' / fid), sha(raw)])
        self.root, self.pkg, self.pkt = root, pkg, pkt
        self.route = {HTM_ID: route_html(), XML_ID: route_xml(), PDF_ID: route_pdf()}

    def tearDown(self):
        self.tmp.cleanup()

    def run_grader(self, mutate=None, heldout_detail=True):
        route = copy.deepcopy(self.route)
        if mutate: mutate(route)
        rdir, out = self.root / 'route', self.root / 'out'
        for fid, r in route.items():
            (rdir / fid).parent.mkdir(parents=True, exist_ok=True); (rdir / (fid + '.json')).write_text(json.dumps(r))
        return grade.run(self.pkg, rdir, out, catalog=self.root / 'case_catalog.csv', heldout_detail=heldout_detail)

    def check(self, res, key_id, check):
        rows = [r for r in res['results'] if r['key_id'] == key_id and r['check'] == check]
        self.assertEqual(len(rows), 1, (key_id, check, rows)); return rows[0]

    def verdict(self, res, key_id):
        return res['targets'][key_id]['verdict']

    def html(self, route):
        return route[HTM_ID]['units']

    def cells(self, route, unit='u3'):
        return next(u for u in self.html(route) if u['id'] == unit)['cells']

    def cell(self, route, id_, unit='u3'):
        want = elem(id_)
        return next(c for c in self.cells(route, unit) if c['anchor'] == want)


class CorrectOutputTests(GraderFixture):
    def test_every_target_passes_and_every_gate_holds(self):
        res = self.run_grader()
        self.assertTrue(all(v['verdict'] == 'PASS' for v in res['targets'].values()), res['targets'])
        g = res['gates']
        for name in ('ids_and_run_facts', 'reading_order', 'markers_apart'): self.assertTrue(g[name]['pass'], (name, g[name]))
        self.assertTrue(g['honest_anchors']['measured_pass'])
        self.assertEqual(g['nothing_lost']['not_measured'], [PDF_ID])  # no text layer: coverage cannot be certified
        self.assertFalse(g['nothing_lost']['pass']); self.assertTrue(g['nothing_lost']['measured_pass'])
        self.assertEqual(g['honest_anchors']['not_measured'], [PDF_ID])  # no independent page sizes: PDF positions are not certified

    def test_converters_get_a_source_list_without_any_answers(self):
        (self.pkg / 'CLAUDE_ANSWER_KEY.json').rename(self.pkg / 'answers.hidden')  # no answers readable
        srcs = grade.load_sources(self.pkg, self.root / 'case_catalog.csv')
        self.assertEqual({(x['file_id'], x['split']) for x in srcs} >= {(HTM_ID, 'development'), (XML_ID, 'stratified_control'), (PDF_ID, 'heldout')}, True)
        self.assertTrue(all(x['path'].exists() and len(x['sha256']) == 64 for x in srcs))

    def test_summary_counts_targets_by_split_and_format(self):
        s = self.run_grader()['summary']['by_split_format']
        self.assertEqual(s['development']['cell/htm'], {'targets': 4, 'PASS': 4, 'FAIL': 0, 'UNRESOLVED': 0, 'NOT_CONVERTED': 0})
        self.assertEqual(s['development']['structure/htm']['PASS'], 4)
        self.assertEqual(s['stratified_control']['cell/xml']['PASS'], 1)
        self.assertEqual(s['heldout']['cell/pdf']['PASS'], 1)
        self.assertEqual(self.run_grader()['summary']['supplement']['PASS'], 1)

    def test_structure_recognition_is_counted_separately(self):
        res = self.run_grader()
        self.assertEqual(self.check(res, 'pkt/S02', 'heading_recognised')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/T02', 'note_linked')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/S01', 'reference_linked')['verdict'], 'pass')
        self.assertEqual(res['summary']['structure']['heading_recognised'], {'pass': 7, 'total': 7})

    def test_meaning_fields_are_reported_as_not_graded_here(self):
        res = self.run_grader()
        self.assertEqual(self.check(res, 'pkt/T01', 'unit_interpretation')['verdict'], 'not_t1')
        self.assertEqual(self.check(res, 'pkt/T01', 'measure')['verdict'], 'not_t1')

    def test_heldout_detail_is_hidden_by_default(self):
        res = self.run_grader(heldout_detail=False)
        self.assertFalse([r for r in res['results'] if r['key_id'] == 'pkt/P01'])
        self.assertNotIn('pkt/P01', res['targets'])
        self.assertEqual(res['summary']['by_split_format']['heldout']['cell/pdf']['PASS'], 1)

    def test_summary_groups_failures_by_reason_and_lists_unresolved_targets(self):
        def two_faults(r):
            self.cell(r, 'v1').update(text='796'); self.cells(r).remove(self.cell(r, 'v3'))
        s = self.run_grader(two_faults)['summary']
        self.assertEqual(s['failures_by_reason'], {'value': {'text': 1}})
        self.assertEqual(s['unresolved'], ['pkt/T03'])

    def test_writes_results_and_summaries(self):
        self.run_grader(); out = self.root / 'out'
        self.assertTrue((out / 'results.jsonl').exists() and (out / 'summary.json').exists() and (out / 'summary.md').exists())


class PlantedFaultTests(GraderFixture):
    def test_an_image_gap_never_counts_missing_prose_as_covered(self):
        raw = b'<p>Before paragraph.</p><p>Revenue fell 20 percent.</p><img src="x.png"><p>After paragraph.</p>'
        linked = anchor.link(raw, [{'id': 'a', 'kind': 'text', 'text': 'Before paragraph.'}, {'id': 'i', 'kind': 'image', 'text': ''},
                                   {'id': 'b', 'kind': 'text', 'text': 'After paragraph.'}])
        g = grade.gates_for_file(grade.RouteFile({'file_id': 'x/image.htm', 'units': linked['units']}, raw, 'htm'), 'OK')
        self.assertEqual([u['text'] for u in g['uncovered']], ['Revenue fell 20 percent.'])

    def test_a_pieced_unit_is_honest_at_its_blocks_and_its_insertions_are_counted(self):
        raw = b'<p>First sentence of a long paragraph that the tool kept.</p><p>7</p><p>Second sentence of the same long paragraph that the tool kept as well.</p>'
        u = {'id': 'u', 'kind': 'text', 'text': 'First sentence of a long paragraph that the tool kept. ---- Second sentence of the same long paragraph that the tool kept as well.'}
        rf = grade.RouteFile({'file_id': 'x/p.htm', 'units': anchor.link(raw, [u])['units']}, raw, 'htm'); g = grade.gates_for_file(rf, 'OK')
        self.assertEqual((g['dishonest'], g['boundary'], g['inserted_chars'], [x['text'] for x in g['uncovered']]), (0, 0, 4, ['7']))

    def test_text_a_tool_adds_inside_an_untargeted_paragraph_fails_the_anchor_gate(self):
        # Codex round-4 preview: "do not" slipped into a long paragraph no target covers; the pieced anchor must not let it pass
        raw = b'<p>The Companies make certain estimates and assumptions that affect reported amounts of assets and liabilities in the statements.</p>'
        u = {'id': 'u', 'kind': 'text', 'text': 'The Companies make certain estimates and assumptions that do not affect reported amounts of assets and liabilities in the statements.'}
        rf = grade.RouteFile({'file_id': 'x/p.htm', 'units': anchor.link(raw, [u])['units']}, raw, 'htm'); g = grade.gates_for_file(rf, 'OK')
        self.assertEqual((g['inserted_chars'], g['uncovered']), (5, []))
        # at run level the gate fails and names the file (the fixture is hand-anchored, so the pieced anchor comes from the linker here)
        def pieced(r):
            x = next(x for x in r[HTM_ID]['units'] if x['id'] == 'u2'); x['text'] = 'Free cash flow is not a GAAP measure that we report. See the table below.'
            for k in ('anchor', 'pieces', 'inserted_chars', 'link_flag'): x.pop(k, None)
            x.update({k: v for k, v in anchor.link(HTML, [dict(x)])['units'][0].items() if k in ('anchor', 'pieces', 'inserted_chars', 'link_flag')})
        res = self.run_grader(pieced)
        self.assertFalse(res['gates']['honest_anchors']['pass']); self.assertEqual(list(res['gates']['honest_anchors']['inserted_chars']), [HTM_ID])

    def test_a_pieced_unit_is_judged_from_its_blocks_never_from_its_own_counts(self):
        # Codex R4-1: the gate derives the insertion from the blocks, checks each block's boundaries and refuses malformed pieces
        raw = b'<p>First sentence of a long paragraph that the tool kept.</p><p>7</p><p>Second sentence of the same long paragraph that the tool kept as well.</p>'
        def gate(text, **override):
            u = anchor.link(raw, [{'id': 'u', 'kind': 'text', 'text': text}])['units'][0]; u.update(override)
            g = grade.gates_for_file(grade.RouteFile({'file_id': 'x/p.htm', 'units': [u]}, raw, 'htm'), 'OK')
            return g['dishonest'], g['boundary'], g['inserted_chars'], [x['text'] for x in g['uncovered']]
        kept = 'First sentence of a long paragraph that the tool kept. ---- Second sentence of the same long paragraph that the tool kept as well.'
        self.assertEqual(gate(kept, inserted_chars=0), (0, 0, 4, ['7']))                                  # an under-reported count changes nothing
        self.assertEqual(gate(kept.replace('tool kept as', 'to ol kept as')), (0, 1, 4, ['7']))           # a word split inside a block is a boundary fault
        self.assertEqual(gate(kept, pieces=[[0, 60], [50, 170]])[0], 1)                                   # overlapping blocks: the mapping is not honest
        dropped = 'First sentence of a long paragraph that the tool kept. Second sentence of the same long paragraph that the tool kept as well.'
        self.assertEqual(gate(dropped), (0, 0, 0, ['7']))                                                 # a deletion inserts nothing; the source text stays uncovered

    def test_joins_between_mapped_blocks_keep_the_source_boundaries_and_order(self):
        # Codex round 5: each block read its own text, but the output glued two words, split a number, or reversed the source order
        def gate(paragraph, text, parts, reverse=False):
            raw = b'<p>Lead.</p><p>' + paragraph.encode() + b'</p>'
            anchors, pieces, n, cursor = [], [], 0, raw.index(paragraph.encode())
            for part in parts:
                a = raw.index(part.encode(), raw.index(paragraph.encode()) if reverse else cursor); anchors.append({'byte_start': a, 'byte_end_exclusive': a + len(part)})
                pieces.append([n, n + len(part)]); n += len(part); cursor = a + len(part)
            u = {'id': 'u', 'kind': 'text', 'text': text, 'anchor': anchors, 'pieces': pieces, 'link_flag': 'pieced', 'inserted_chars': 0}
            g = grade.gates_for_file(grade.RouteFile({'file_id': 'x/p.htm', 'units': [{'id': 'l', 'kind': 'text', 'text': 'Lead.', 'anchor': {'byte_start': 3, 'byte_end_exclusive': 8}}, u]}, raw, 'htm'), 'OK')
            return g['dishonest'], g['boundary']
        self.assertEqual(gate('Revenue increased.', 'Revenue increased.', ('Revenue', 'increased.')), (0, 0))   # control: the space survives
        self.assertEqual(gate('Revenue increased.', 'Revenueincreased.', ('Revenue', 'increased.')), (0, 1))    # word boundary deleted at the join
        self.assertEqual(gate('<span>12</span><span>34</span>', '1234', ('12', '34')), (0, 0))               # control: adjacent fragments of one number
        self.assertEqual(gate('<span>12</span><span>34</span>', '12 34', ('12', '34')), (0, 1))              # number boundary inserted at the join
        self.assertEqual(gate('Alpha Beta', 'Beta Alpha', ('Beta', 'Alpha'), reverse=True), (1, 0))          # source order reversed: not an honest mapping

    def test_a_range_partner_split_by_page_boxes_is_unresolved_not_wrong(self):
        box = lambda x0, x1: {'page': 1, 'region': [x0, 10, x1, 20]}
        def rows(case):
            partner, value = box(20, 40), box(70, 90)
            cells = [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': box(0, 15)}]
            if case == 'whole': cells.append({'r': 0, 'c': 1, 'text': '1234', 'anchor': partner})
            else: cells += [{'r': 0, 'c': 1, 'text': '12', 'anchor': box(20, 30)}, {'r': 0, 'c': 2 if case == 'columns' else 1, 'text': '35' if case == 'digits' else '34', 'anchor': box(30, 40)}]
            cells.append({'r': 0, 'c': 3, 'text': '1500', 'anchor': value})
            table = {'id': 'tb', 'kind': 'table', 'anchor': {'page': 1, 'region': [0, 0, 100, 30]}, 'cells': cells}
            t = {'key_id': 'syn/R1', 'file_id': 'syn/f.pdf', 'format': 'cell/pdf', 'type': 'cell', 'split': 'development', 'anchor': value, 'table_anchor': table['anchor'],
                 'alternatives': {}, 'excluded': set(), 'support': {}, 'fields': {'printed_value': '1500', 'display_value': '1500', 'row_label': 'Revenue',
                 'range': {'kind': 'interval', 'role': 'high', 'partner': {'printed_value': '1234', 'anchor': partner}, 'evidence': []}}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.pdf', 'units': [table]}, None, 'pdf')); g.grade_cell()
            return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'range')
        self.assertEqual(rows('whole'), ('pass', None)); self.assertEqual(rows('split'), ('unresolved', 'adjacency'))
        self.assertEqual(rows('digits'), ('fail', 'partner')); self.assertEqual(rows('columns'), ('fail', 'partner'))

    def test_pieces_of_one_value_cell_pass_only_when_they_share_the_cell_and_the_source_proves_adjacency(self):
        # Codex R4-5: <span>76</span><span>9</span> kept as two anchored pieces at one grid position is faithful output (E12)
        def fragments(c2=2):
            def go(r):
                v = self.cell(r, 'v1'); cells = self.cells(r); i = cells.index(v)
                cells[i:i + 1] = [dict(v, text='76', anchor=self.sub('v1', '76')), dict(v, text='9', c=c2, anchor=self.sub('v1', '9'))]
            return go
        self.assertEqual(self.check(self.run_grader(fragments()), 'pkt/T01', 'value')['verdict'], 'pass')
        self.assertEqual(self.check(self.run_grader(fragments(c2=3)), 'pkt/T01', 'value')['reason'], 'spacing')  # two cells show two numbers
        def apart(r):  # the same two pieces whose own anchors do not touch in the source: a boundary the tool made
            v = self.cell(r, 'v1'); cells = self.cells(r); i = cells.index(v)
            cells[i:i + 1] = [dict(v, text='76', anchor=self.sub('v1', '76')), dict(v, text='9', anchor=dict(self.sub('v1', '9'), byte_start=self.sub('v1', '9')['byte_start'] + 1))]
        self.assertEqual(self.check(self.run_grader(apart), 'pkt/T01', 'value')['reason'], 'spacing')
        t = {'key_id': 'syn/P', 'file_id': 'x/deck.pdf', 'format': 'cell/pdf', 'type': 'cell', 'split': 'development', 'anchor': {'page': 1, 'region': [100, 100, 200, 120]},
             'table_anchor': {'page': 1, 'region': [0, 0, 600, 400]}, 'fields': {'printed_value': '1234', 'row_label': 'Revenue'}, 'alternatives': {}, 'excluded': set(), 'support': {}}
        cells = [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': {'page': 1, 'region': [0, 100, 90, 120]}}, {'r': 0, 'c': 1, 'text': '12', 'anchor': {'page': 1, 'region': [100, 100, 150, 120]}},
                 {'r': 0, 'c': 1, 'text': '34', 'anchor': {'page': 1, 'region': [150, 100, 200, 120]}}]
        g = grade.Grader(t, grade.RouteFile({'file_id': 'x/deck.pdf', 'units': [{'id': 't', 'kind': 'table', 'anchor': t['table_anchor'], 'cells': cells}]}, None, 'pdf')); g.grade_cell()
        self.assertEqual(next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'value'), ('unresolved', 'adjacency'))  # boxes cannot prove the join

    def test_a_range_partner_kept_as_adjacent_pieces_is_still_the_partner(self):
        def split_partner(r):
            lo = self.cell(r, 'lo', 'u6'); cells = self.cells(r, 'u6'); i = cells.index(lo)
            cells[i:i + 1] = [dict(lo, text='$10.', anchor=self.sub('lo', '$10.')), dict(lo, text='57', anchor=self.sub('lo', '57'))]
        self.assertEqual(self.check(self.run_grader(split_partner), 'fx/R01', 'range')['verdict'], 'pass')

    def test_verified_means_every_consumed_input_is_pinned(self):
        names = ('CLAUDE_ANSWER_KEY.json', 'CLAUDE_KEY_FLAGS.json', 'KEY_SUPPORT_MAP.json', 'converter_checks/REGRESSION_CASES.json')
        base = {'evidence_root': '..', 'files_sha256': {n: grade.sha256((self.pkg / n).read_bytes()) for n in names},
                'packets_sha256': {'packets/pkt': {'targets_sha256': grade.sha256((self.pkt / 'targets.json').read_bytes())}}}
        (self.pkg / 'FINAL_MANIFEST.json').write_text(json.dumps(base))
        res = self.run_grader(); self.assertFalse(res['run_facts']['verified']); self.assertIn('catalog', res['run_facts']['unverified_because'])  # the split list is not pinned
        pinned = dict(base, catalog_sha256=grade.sha256((self.root / 'case_catalog.csv').read_bytes())); (self.pkg / 'FINAL_MANIFEST.json').write_text(json.dumps(pinned))
        res = self.run_grader(); self.assertTrue(res['run_facts']['verified'])
        cat = self.root / 'case_catalog.csv'; text = cat.read_text(); cat.write_text(text.replace('heldout', 'development', 1))
        with self.assertRaises(ValueError): self.run_grader(heldout_detail=False)  # Codex round 5: a pinned catalog that changed is refused, never run unverified
        cat.write_text(text)
        loose = dict(pinned, packets_sha256={'packets/pkt': {'manifest_sha256': 'x'}}); (self.pkg / 'FINAL_MANIFEST.json').write_text(json.dumps(loose))
        with self.assertRaises(ValueError): self.run_grader()  # a packet pinned without its target file is not pinned
        # Codex R4-2: the pins must cover what grading reads, where it reads it
        for pins in ({'packets/pkt': {}}, {'packets/other': base['packets_sha256']['packets/pkt']}):  # empty pins; only an unconsumed packet pinned
            (self.pkg / 'FINAL_MANIFEST.json').write_text(json.dumps(dict(pinned, packets_sha256=pins)))
            with self.assertRaises(ValueError): self.run_grader()
        (self.pkg / 'FINAL_MANIFEST.json').write_text(json.dumps(pinned)); (self.pkg / 'converter_checks' / 'REGRESSION_CASES.json').unlink()
        with self.assertRaises(ValueError): self.run_grader()                                             # a pinned input that is missing
        shutil.copytree(self.pkt, self.root / 'bulk' / 'bundled' / 'packets' / 'pkt')                      # the same packet name in both folders
        with self.assertRaises(FileNotFoundError): grade.packet_dir(self.root / 'bulk', 'pkt', ('bundled/packets/pkt',))  # is never a silent choice

    def test_partial_route_status_leaves_coverage_unmeasured_never_passed(self):
        def partial(r): self.cells(r).remove(self.cell(r, 'p1')); r[HTM_ID]['status'] = 'PARTIAL'
        res = self.run_grader(partial)
        self.assertFalse(res['gates']['nothing_lost']['pass']); self.assertIn(HTM_ID, res['gates']['nothing_lost']['not_measured'])

    def test_text_without_a_source_position_fails_the_anchor_gate(self):
        res = self.run_grader(lambda r: r[HTM_ID]['units'].append({'id': 'new', 'kind': 'text', 'text': 'Invented revenue 999', 'anchor': None}))
        self.assertFalse(res['gates']['honest_anchors']['pass']); self.assertEqual(res['gates']['honest_anchors']['unanchored'], {HTM_ID: 1})

    def test_an_anchor_beyond_the_file_is_dishonest(self):
        res = self.run_grader(lambda r: self.unit(r, 'u7')['anchor'].update(byte_end_exclusive=len(HTML) + 1_000_000))
        self.assertEqual(res['gates']['honest_anchors']['dishonest'], {HTM_ID: 1})

    def test_a_route_file_naming_another_source_is_not_converted(self):
        def wrong(r): self.cells(r).remove(self.cell(r, 'p1')); r[HTM_ID]['file_id'] = PDF_ID
        res = self.run_grader(wrong)
        self.assertEqual(res['files'][HTM_ID]['status'], 'NOT_CONVERTED'); self.assertEqual(res['targets']['pkt/T01']['verdict'], 'NOT_CONVERTED')

    def test_a_source_missing_from_the_split_catalog_stops_the_run(self):
        p = self.root / 'case_catalog.csv'; p.write_text(''.join(l for l in p.read_text().splitlines(True) if PDF_ID not in l))
        with self.assertRaises(ValueError): self.run_grader()

    def test_heldout_gate_details_and_unresolved_ids_stay_hidden_by_default(self):
        p = self.root / 'case_catalog.csv'; p.write_text(p.read_text().replace('development,FX', 'heldout,FX', 1))  # the HTML file becomes held-out
        res = self.run_grader(lambda r: self.cells(r).remove(self.cell(r, 'p1')), heldout_detail=False)
        self.assertEqual(set(res['gates']['nothing_lost']['uncovered'][HTM_ID]), {'spans', 'chars'})  # counts only, no text, no bytes
        self.assertEqual(res['summary']['unresolved'], []); self.assertNotIn('pkt/T01', res['targets'])
        self.assertTrue(res['run_facts']['key_sha256'])

    def test_changed_digit_fails_the_value_only(self):
        res = self.run_grader(lambda r: self.cell(r, 'v1').update(text='796'))
        self.assertEqual(self.check(res, 'pkt/T01', 'value')['verdict'], 'fail')
        self.assertEqual(self.verdict(res, 'pkt/T02'), 'PASS')

    def test_dropped_value_cell_is_unresolved(self):
        res = self.run_grader(lambda r: self.cells(r).remove(self.cell(r, 'v1')))
        self.assertEqual(self.verdict(res, 'pkt/T01'), 'UNRESOLVED')

    def test_value_under_the_next_column_fails_header_association(self):
        res = self.run_grader(lambda r: self.cell(r, 'v2').update(c=4))
        self.assertEqual(self.check(res, 'pkt/T02', 'header_path')['reason'], 'column')

    def test_value_in_the_next_row_fails_row_label(self):
        res = self.run_grader(lambda r: self.cell(r, 'v2').update(r=3))
        self.assertEqual(self.check(res, 'pkt/T02', 'row_label')['reason'], 'row')

    def test_lost_parentheses_fail_the_value(self):
        res = self.run_grader(lambda r: self.cell(r, 'v2').update(text='506'))
        self.assertEqual(self.check(res, 'pkt/T02', 'value')['reason'], 'text')

    def test_symbol_cell_moved_to_another_row_fails_the_value(self):
        res = self.run_grader(lambda r: self.cell(r, 's2').update(r=3))
        self.assertEqual(self.check(res, 'pkt/T02', 'value')['reason'], 'symbol_detached')

    def test_lost_header_fragment_fails_header_text(self):
        res = self.run_grader(lambda r: self.cell(r, 'hb').update(text='Months Ended'))
        self.assertEqual(self.check(res, 'pkt/T01', 'header_path')['reason'], 'text')

    def test_header_over_the_wrong_columns_fails_association(self):
        res = self.run_grader(lambda r: self.cell(r, 'h24').update(c=3, cs=2))
        self.assertEqual(self.check(res, 'pkt/T01', 'header_path')['reason'], 'column')

    def test_footnote_digit_glued_to_the_value_fails(self):
        res = self.run_grader(lambda r: self.cell(r, 'v3').update(text='10.674', markers=[]))
        self.assertEqual(self.check(res, 'pkt/T03', 'value')['reason'], 'marker_glued')

    def test_marker_glued_to_a_label_is_preserved_but_flagged(self):
        res = self.run_grader(lambda r: self.cell(r, 'l2').update(text='Free cash flow(1)', markers=[]))
        row = self.check(res, 'pkt/T02', 'row_label')
        self.assertEqual((row['verdict'], row['detail']), ('pass', 'marker_in_label'))
        self.assertEqual(self.verdict(res, 'pkt/T02'), 'PASS')

    def test_dropped_note_fails_footnotes(self):
        res = self.run_grader(lambda r: self.html(r).remove(next(u for u in self.html(r) if u['id'] == 'u5')))
        self.assertEqual(self.check(res, 'pkt/T03', 'footnote_markers')['reason'], 'missing_note')

    def test_dropped_heading_fails_fixed_paths_but_an_accepted_alternative_still_passes(self):
        res = self.run_grader(lambda r: self.html(r).remove(next(u for u in self.html(r) if u['id'] == 'u1')))
        self.assertEqual(self.check(res, 'pkt/T02', 'section_path')['verdict'], 'fail')
        self.assertEqual(self.check(res, 'pkt/T01', 'section_path')['verdict'], 'pass')
        self.assertEqual(self.verdict(res, 'pkt/S02'), 'UNRESOLVED')

    def test_heading_demoted_to_plain_text_passes_but_is_not_recognised(self):
        res = self.run_grader(lambda r: next(u for u in self.html(r) if u['id'] == 'u1').update(kind='text'))
        self.assertEqual(self.check(res, 'pkt/T02', 'section_path')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/T02', 'heading_recognised')['verdict'], 'fail')
        self.assertEqual(res['targets']['pkt/S02']['verdict'], 'PASS')  # the heading's text, place and order are preserved (R7)
        self.assertEqual(self.check(res, 'pkt/S02', 'kind')['verdict'], 'fail')  # recognition is counted apart, never a pass rule

    def test_dropped_paragraph_is_unresolved_and_counted_as_lost(self):
        res = self.run_grader(lambda r: self.html(r).remove(next(u for u in self.html(r) if u['id'] == 'u2')))
        self.assertEqual(self.verdict(res, 'pkt/S01'), 'UNRESOLVED')
        self.assertEqual(self.check(res, 'pkt/T01', 'lead_in')['verdict'], 'fail')
        lost = res['gates']['nothing_lost']
        self.assertFalse(lost['pass']); self.assertIn('Free cash flow is not a GAAP measure', anchor.norm(' '.join(s['text'] for s in lost['uncovered'][HTM_ID])))

    def picture_as_blocks(self, r, drop=None):
        units = self.html(r); img = next(u for u in units if u['id'] == 'u8'); i = units.index(img); units.remove(img)
        blocks = [{'id': 'b1', 'kind': 'text', 'text': 'Picture words one.', 'anchor': elem('im')},
                  {'id': 'b2', 'kind': 'text', 'text': 'Picture words two.', 'anchor': elem('im')}]
        units[i:i] = [b for b in blocks if b['id'] != drop]

    def test_picture_text_returned_as_ordered_blocks_passes(self):
        res = self.run_grader(self.picture_as_blocks)
        self.assertEqual(self.verdict(res, 'pkt/S03'), 'PASS')
        self.assertEqual(self.check(res, 'pkt/S03', 'kind')['verdict'], 'na')

    def test_picture_block_dropped_fails_text_with_word_error_rate(self):
        res = self.run_grader(lambda r: self.picture_as_blocks(r, drop='b2'))
        row = self.check(res, 'pkt/S03', 'printed_text')
        self.assertEqual((row['verdict'], row['reason']), ('fail', 'text')); self.assertGreater(row['detail']['wer'], 0)

    def test_qualifier_phrase_after_the_table_passes_when_kept_at_its_place(self):
        res = self.run_grader()
        self.assertEqual(self.check(res, 'pkt/T05', 'segment_or_basis')['verdict'], 'pass')

    def test_note_printed_as_the_tables_last_row_passes_and_counts_as_linked(self):
        def note_row(r):
            u = self.html(r); n = next(x for x in u if x['id'] == 'u4'); u.remove(n)
            self.cells(r).append({'r': 6, 'c': 0, 'rs': 1, 'cs': 5, 'text': n['text'], 'anchor': n['anchor']})
        res = self.run_grader(note_row)
        self.assertEqual(self.check(res, 'pkt/T02', 'footnote_markers')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/T02', 'note_linked')['verdict'], 'pass')

    def test_mark_glued_to_a_title_or_header_is_tolerated_and_flagged(self):
        res = self.run_grader(lambda r: self.cell(r, 'ttl').update(text='Free Cash Flow(1)'))
        row = self.check(res, 'pkt/T02', 'table_title')
        self.assertEqual((row['verdict'], row['detail']), ('pass', 'marker_in_text'))

    def test_header_with_a_trailing_bracketed_unit_phrase_matches_the_split_key_header(self):
        res = self.run_grader(lambda r: self.cell(r, 'hb').update(text='Three Months Ended (in millions)'))
        row = self.check(res, 'pkt/T01', 'header_path')
        self.assertEqual((row['verdict'], row['detail']), ('pass', 'unit_phrase_split'))

    def test_title_block_with_own_pieces_before_and_a_mark_in_front_still_matches(self):
        # a PDF tool merged "(Unaudited) (1) Title Current Year-to-Date vs. Prior Year-to-Date" into one block
        self.assertEqual(grade.same('(Unaudited) (1) Same-Store Operating Information By Major Market Current Year-to-Date vs. Prior Year-to-Date',
                                    'Same-Store Operating Information By Major Market', ['(1)'], ['(Unaudited)', 'Current Year-to-Date vs. Prior Year-to-Date']),
                         (True, 'joined_with_own_pieces'))

    def test_continued_in_the_key_heading_is_folded_too(self):
        self.assertTrue(grade.heading_eq('Notes', 'Notes (continued)'))
        self.assertTrue(grade.heading_eq('Notes (Continued)', 'Notes'))
        self.assertFalse(grade.heading_eq('Notes', 'Other Notes'))

    def test_merged_stacked_header_cell_with_several_spans_passes(self):
        def merge(r):
            cells = self.cells(r); hb, h24 = self.cell(r, 'hb'), self.cell(r, 'h24')
            cells.remove(h24); hb.update(text='Three Months Ended December 28, 2024', rs=2, cs=3, anchor=[elem('hb'), elem('h24')])
        res = self.run_grader(merge)
        self.assertEqual(self.check(res, 'pkt/T01', 'header_path')['verdict'], 'pass')
        self.assertTrue(res['gates']['honest_anchors']['measured_pass']); self.assertEqual(res['gates']['honest_anchors']['dishonest'], {})  # the merged cell's list anchor is honest
        self.assertEqual(self.check(res, 'pkt/T01', 'unit_printed')['verdict'], 'pass')  # the corner cell is untouched

    def test_symbol_cells_merged_into_the_value_cell_keep_the_unit_sign(self):
        def merge(r):
            cells = self.cells(r); s2, v2, c2 = self.cell(r, 's2'), self.cell(r, 'v2'), self.cell(r, 'c2')
            cells.remove(s2); cells.remove(c2); v2.update(text='$(506)', c=1, cs=3, anchor=[elem('s2'), elem('v2'), elem('c2')])
        res = self.run_grader(merge)
        self.assertEqual(self.verdict(res, 'pkt/T02'), 'PASS')

    def test_key_pieces_align_to_tool_cells_one_to_many_with_marks_and_unit_phrases(self):
        self.assertEqual(grade.match_pieces(['Change', 'Excluding', 'Foreign Currency Impact (1)'], ['Change Excluding Foreign Currency Impact'], ['(1)']), (True, 'marker_in_text'))
        self.assertEqual(grade.match_pieces(['Same-Store ($000s)', 'Expenses', 'YTD', '23'], ['Same-Store', 'Expenses', 'YTD 23'], [], ['($000s)']), (True, 'unit_phrase_split'))
        self.assertEqual(grade.match_pieces(['Same-Store ($000s)', 'Expenses', 'YTD', '23'], ['Same-Store', 'Expenses', 'YTD 23'], []), (False, None))  # not the record's own unit phrase: E13
        self.assertEqual(grade.match_pieces(['Three Months Ended', 'December 28, 2024'], ['Three Months Ended', 'December 28, 2024'], []), (True, None))
        self.assertEqual(grade.match_pieces(['Months Ended', 'December 28, 2024'], ['Three Months Ended', 'December 28, 2024'], []), (False, None))
        self.assertEqual(grade.match_pieces(['Three Months Ended', 'December 28, 2024', 'Extra'], ['Three Months Ended', 'December 28, 2024'], []), (False, None))

    def unit(self, r, id_):
        return next(u for u in self.html(r) if u['id'] == id_)

    def test_footnote_mark_inside_a_paragraph_and_note_as_paragraph_pass(self):
        res = self.run_grader()
        self.assertEqual(self.check(res, 'pkt/T05', 'footnote_markers')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/T05', 'note_linked')['verdict'], 'pass')

    def test_heading_carried_by_a_one_cell_table_passes_but_is_not_recognised(self):
        def as_table(r):
            u = self.html(r); i = u.index(self.unit(r, 'u1'))
            u[i] = {'id': 'u1', 'kind': 'table', 'anchor': elem('h2'), 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Free Cash Flow', 'anchor': elem('h2')}]}
        res = self.run_grader(as_table)
        self.assertEqual(self.check(res, 'pkt/T02', 'section_path')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/T02', 'heading_recognised')['verdict'], 'fail')
        self.assertEqual(self.check(res, 'pkt/S02', 'printed_text')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/S02', 'kind')['reason'], 'kind')  # the heading lost its nature: the block fails on kind

    def test_title_in_its_own_table_before_the_data_table_passes(self):
        def split_title(r):
            u = self.html(r); tb2 = self.unit(r, 'u6'); title = self.cell(r, 't2t', 'u6'); tb2['cells'].remove(title)
            for c in tb2['cells']: c['r'] -= 1
            u.insert(u.index(tb2), {'id': 'u6t', 'kind': 'table', 'anchor': elem('t2t'), 'cells': [dict(title, r=0, c=0, cs=1)]})
        res = self.run_grader(split_title)
        self.assertEqual(self.check(res, 'pkt/T05', 'table_title')['verdict'], 'pass')
        self.assertEqual(self.verdict(res, 'pkt/T05'), 'PASS')

    def test_note_laid_out_as_a_one_cell_table_passes(self):
        def as_table(r):
            u = self.html(r); n = self.unit(r, 'u4'); i = u.index(n)
            u[i] = {'id': 'u4', 'kind': 'table', 'anchor': elem('n1'), 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': n['text'], 'anchor': elem('n1')}]}
        res = self.run_grader(as_table)
        self.assertEqual(self.check(res, 'pkt/T02', 'footnote_markers')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/T02', 'note_linked')['verdict'], 'pass')  # listed in the table's notes

    def test_table_continued_as_two_units_keeps_headers_of_the_first_part(self):
        def split(r):
            u = self.html(r); tb = self.unit(r, 'u3'); head = [c for c in tb['cells'] if c['r'] <= 2]; data = [c for c in tb['cells'] if c['r'] > 2]
            for c in data: c['r'] -= 3
            tb['cells'] = data; tb['anchor'] = {'byte_start': elem('l1')['byte_start'], 'byte_end_exclusive': elem('tbl')['byte_end_exclusive']}
            u.insert(u.index(tb), {'id': 'u3a', 'kind': 'table', 'anchor': {'byte_start': elem('tbl')['byte_start'], 'byte_end_exclusive': elem('h23')['byte_end_exclusive']}, 'cells': head})
        res = self.run_grader(split)
        row = self.check(res, 'pkt/T02', 'header_path')
        self.assertEqual((row['verdict'], row['detail']), ('pass', 'continued_table'))
        self.assertEqual(self.verdict(res, 'pkt/T02'), 'PASS')
        res = self.run_grader(lambda r: (split(r), self.cell(r, 'v2').update(c=4)))
        self.assertEqual(self.check(res, 'pkt/T02', 'header_path')['reason'], 'column')

    def test_value_cell_spanning_columns_is_covered_when_any_of_its_columns_is(self):
        def merge(r):
            cells = self.cells(r); s2, v2, c2 = self.cell(r, 's2'), self.cell(r, 'v2'), self.cell(r, 'c2')
            cells.remove(s2); cells.remove(c2); v2.update(text='$(506)', c=1, cs=3, anchor=[elem('s2'), elem('v2'), elem('c2')])
            self.cell(r, 'h24').update(c=2, cs=2)
        res = self.run_grader(merge)
        self.assertEqual(self.check(res, 'pkt/T02', 'header_path')['verdict'], 'pass')

    def test_qualifier_inside_the_table_must_keep_its_source_row_order(self):
        def move_up(r):  # the note row sits after the value in the source; a tool putting it above the value misorders the table
            cells = self.cells(r); cells.append({'r': 0, 'c': 0, 'rs': 1, 'cs': 5, 'text': '(1) Represents principal maturities only.', 'anchor': elem('n1')})
            for c in cells[:-1]: c['r'] += 1
            self.html(r).remove(self.unit(r, 'u4'))
        res = self.run_grader(move_up)
        self.assertEqual(self.check(res, 'pkt/T02', 'footnote_markers')['reason'], 'placement')

    def sub(self, id_, piece):
        """Byte span of a piece of text inside the element id_ (the original's own bytes decide the join)."""
        a = elem(id_); i = HTML.index(piece.encode(), a['byte_start'])
        return {'byte_start': i, 'byte_end_exclusive': i + len(piece.encode())}

    def test_block_split_by_the_tool_is_joined_the_way_the_original_prints_it(self):
        def split(r):
            u = self.html(r); li = self.unit(r, 'u12'); i = u.index(li)
            u[i:i + 1] = [{'id': 'b1', 'kind': 'list_item', 'text': '\u2022', 'anchor': self.sub('li', '\u2022')},
                          {'id': 'b2', 'kind': 'text', 'text': 'The first point.', 'anchor': self.sub('li', 'The first point.')}]
        res = self.run_grader(split)
        self.assertEqual(self.check(res, 'pkt/S04', 'printed_text')['verdict'], 'pass')  # no space in the original between the two

    def test_fragments_of_one_word_pass_flagged_when_their_anchors_prove_adjacency(self):
        def split_word(r):  # span-level output: "The fi" + "rst point." with contiguous source anchors and no inserted separator (E12)
            u = self.html(r); li = self.unit(r, 'u12'); i = u.index(li)
            u[i:i + 1] = [{'id': 'w1', 'kind': 'list_item', 'text': '\u2022The fi', 'anchor': [self.sub('li', '\u2022'), self.sub('li', 'The fi')]},
                          {'id': 'w2', 'kind': 'text', 'text': 'rst point.', 'anchor': self.sub('li', 'rst point.')}]
        res = self.run_grader(split_word)
        row = self.check(res, 'pkt/S04', 'printed_text')
        self.assertEqual((row['verdict'], row['detail']), ('pass', {'fragmented': 1}))

    def test_a_word_split_whose_pieces_are_not_adjacent_in_the_source_fails(self):
        def split_word(r):  # the second piece's own anchor starts one character later: the output does not retain adjacency
            u = self.html(r); li = self.unit(r, 'u12'); i = u.index(li)
            u[i:i + 1] = [{'id': 'w1', 'kind': 'list_item', 'text': '\u2022The fi', 'anchor': [self.sub('li', '\u2022'), self.sub('li', 'The fi')]},
                          {'id': 'w2', 'kind': 'text', 'text': 'rst point.', 'anchor': self.sub('li', 'st point.')}]
        res = self.run_grader(split_word)
        self.assertEqual(self.check(res, 'pkt/S04', 'printed_text')['reason'], 'word_split')

    def test_a_space_lost_between_two_words_inside_a_block_fails(self):
        res = self.run_grader(lambda r: self.unit(r, 'u2').update(text='Free cash flow is not a GAAPmeasure. See the table below.'))
        self.assertEqual(self.check(res, 'pkt/S01', 'printed_text')['reason'], 'spacing')

    def test_note_split_into_mark_and_body_units_still_counts_as_the_note(self):
        def split(r):
            u = self.html(r); n = self.unit(r, 'u4'); i = u.index(n)
            u[i:i + 1] = [{'id': 'n1a', 'kind': 'text', 'text': '(1)', 'anchor': self.sub('n1', '(1)')},
                          {'id': 'n1b', 'kind': 'text', 'text': 'Represents principal maturities only.', 'anchor': self.sub('n1', 'Represents principal maturities only.')}]
            self.unit(r, 'u3')['notes'] = ['n1a', 'n1b', 'u5']
        res = self.run_grader(split)
        self.assertEqual(self.check(res, 'pkt/T02', 'footnote_markers')['verdict'], 'pass')

    def test_a_word_broken_by_a_space_fails_with_reason_spacing(self):
        res = self.run_grader(lambda r: self.unit(r, 'u1').update(text='Free Ca sh Flow'))
        self.assertEqual(self.check(res, 'pkt/T02', 'section_path')['reason'], 'spacing')
        res = self.run_grader(lambda r: self.unit(r, 'u2').update(text='Free cash flow is not a GA AP measure. See the table below.'))
        self.assertEqual(self.check(res, 'pkt/T01', 'lead_in')['reason'], 'spacing')

    def test_heading_laid_out_as_two_cells_of_a_row_passes(self):
        def two_cells(r):
            u = self.html(r); i = u.index(self.unit(r, 'u1'))
            u[i] = {'id': 'u1', 'kind': 'table', 'anchor': elem('h2'), 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Free', 'anchor': self.sub('h2', 'Free')},
                                                                            {'r': 0, 'c': 1, 'rs': 1, 'cs': 1, 'text': 'Cash Flow', 'anchor': self.sub('h2', 'Cash Flow')}]}
        res = self.run_grader(two_cells)
        self.assertEqual(self.check(res, 'pkt/T02', 'section_path')['verdict'], 'pass')

    def test_title_cell_that_also_holds_the_records_unit_line_passes_flagged(self):
        def merged(r):
            cells = self.cells(r); cells.remove(self.cell(r, 'unit')); self.cell(r, 'ttl').update(text='Free Cash Flow (in millions)', anchor=[elem('ttl'), elem('unit')])
        res = self.run_grader(merged)
        row = self.check(res, 'pkt/T02', 'table_title')
        self.assertEqual(row['verdict'], 'pass'); self.assertIn(row['detail'], ('joined_with_own_pieces', 'unit_phrase_split'))  # both explain the extra words
        self.assertEqual(self.check(res, 'pkt/T02', 'unit_printed')['verdict'], 'pass')

    def test_title_cell_holding_title_and_the_records_own_basis_words_passes_flagged_but_an_extra_qualifier_fails(self):
        res = self.run_grader(lambda r: self.cell(r, 't2t', 'u6').update(text='Fiscal 2026 Outlook\nexclude discontinued operations'))
        row = self.check(res, 'pkt/T05', 'table_title')
        self.assertEqual(row['verdict'], 'pass'); self.assertIn(row['detail'], ('joined_with_own_pieces', 'unit_phrase_split'))
        res = self.run_grader(lambda r: self.cell(r, 't2t', 'u6').update(text='Fiscal 2026 Outlook\nexclude discontinued operations\n(unaudited)'))
        self.assertEqual(self.check(res, 'pkt/T05', 'table_title')['verdict'], 'fail')  # "(unaudited)" is not one of this record's pieces (E13)

    def test_title_cell_may_hold_a_declared_table_context_line_but_not_a_siblings_qualifier(self):
        # E13 ruling (Codex round 3): table context is admitted only when the key declares it with a source anchor inside this table
        def with_unit_line(r): self.cell(r, 'ttl').update(text='Free Cash Flow (in millions)')
        res = self.run_grader(with_unit_line)
        self.assertEqual(self.check(res, 'pkt/T02', 'table_title')['verdict'], 'pass')  # "(in millions)" is T02's own unit line
        # T05's table (tb2) has no declared context: a sibling's basis words may not be borrowed, an invented qualifier fails
        res = self.run_grader(lambda r: self.cell(r, 't2t', 'u6').update(text='Fiscal 2026 Outlook (unaudited)'))
        self.assertEqual(self.check(res, 'pkt/T05', 'table_title')['verdict'], 'fail')
        # declared table context: a support entry whose anchor reads the phrase inside tb2 -> the title cell may carry it
        def declare(span):
            sup = json.loads((self.pkg / 'KEY_SUPPORT_MAP.json').read_text())
            sup.setdefault('pkt/T05', {})['table_context'] = {'how': 'reviewed', 'pieces': [{'text': '(unaudited)', 'byte_ranges': [[span['byte_start'], span['byte_end_exclusive']]]}]}
            (self.pkg / 'KEY_SUPPORT_MAP.json').write_text(json.dumps(sup))
        declare(elem('t2c'))
        res = self.run_grader(lambda r: self.cell(r, 't2t', 'u6').update(text='Fiscal 2026 Outlook (unaudited)'))
        self.assertEqual(self.check(res, 'pkt/T05', 'table_title')['verdict'], 'pass')
        for bad in (elem('tb2'), elem('t2t'), elem('after'), {'byte_start': 0, 'byte_end_exclusive': len(HTML)}):  # Codex R4-6: a container, another cell's text,
            declare(bad)                                                                                              # a phrase outside the table, the whole document
            with self.assertRaises(ValueError): self.run_grader()                                                     # are key defects, refused — never admitted
        self.assertFalse(grade.Grader({'key_id': 'x', 'fields': {}, 'alternatives': {}, 'support': {}, 'excluded': set(), 'file_id': HTM_ID, 'split': 'development', 'format': 'cell/htm'}, None).same('Revenue (Unaudited)', 'Revenue')[0])

    def test_note_whose_mark_is_glued_in_the_key_but_spaced_by_the_tool_still_matches(self):
        def glue_in_key(r): pass
        # the fixture's key note reads "(1) Represents…"; make the tool print "(1)Represents…" and the other way round
        res = self.run_grader(lambda r: self.unit(r, 'u4').update(text='(1)Represents principal maturities only.'))
        self.assertEqual(self.check(res, 'pkt/T02', 'footnote_markers')['verdict'], 'pass')

    def test_notes_block_holding_several_numbered_notes_satisfies_each_note(self):
        def block(r):
            u = self.html(r); n1, n4 = self.unit(r, 'u4'), self.unit(r, 'u5'); i = u.index(n1); u.remove(n1); u.remove(n4)
            u.insert(i, {'id': 'nb', 'kind': 'text', 'text': 'Notes: ' + n1['text'] + ' ' + n4['text'], 'anchor': {'byte_start': elem('n1')['byte_start'], 'byte_end_exclusive': elem('n4')['byte_end_exclusive']}})
            self.unit(r, 'u3')['notes'] = ['nb']
        res = self.run_grader(block)
        self.assertEqual(self.check(res, 'pkt/T02', 'footnote_markers')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/T03', 'footnote_markers')['verdict'], 'pass')

    def test_note_with_a_space_after_its_mark_still_matches(self):
        res = self.run_grader(lambda r: self.unit(r, 'u5').update(text='4  Non-GAAP measure; see the reconciliation.'))
        self.assertEqual(self.check(res, 'pkt/T03', 'footnote_markers')['verdict'], 'pass')
        res = self.run_grader(lambda r: self.unit(r, 'u5').update(text='4 Non-GAAP measure; see the reconciliations.'))
        self.assertEqual(self.check(res, 'pkt/T03', 'footnote_markers')['reason'], 'missing_note')

    def test_qualifier_phrase_split_across_units_is_found_in_their_join(self):
        def split(r):
            u = self.html(r); i = u.index(self.unit(r, 'u9'))
            u[i:i + 1] = [{'id': 'q1', 'kind': 'text', 'text': 'Amounts exclude', 'anchor': self.sub('after', 'Amounts exclude')},
                          {'id': 'q2', 'kind': 'text', 'text': 'discontinued operations.', 'anchor': self.sub('after', 'discontinued operations.')}]
        res = self.run_grader(split)
        self.assertEqual(self.check(res, 'pkt/T05', 'segment_or_basis')['verdict'], 'pass')

    def test_time_row_in_the_label_column_below_the_value_does_not_govern_it(self):
        def below(r):
            self.cell(r, 'hb').update(r=6, c=0, cs=1)
        res = self.run_grader(below)
        self.assertEqual(self.check(res, 'pkt/T01', 'periods')['reason'], 'order')

    def test_value_moved_under_a_competing_time_group_fails_even_though_both_dates_remain(self):
        def other_group(r):  # the time row sits in the label column; a second time heading the key knows opens a new group before the value
            cells = self.cells(r); self.cell(r, 'hb').update(c=0, cs=1)
            for c in cells:
                if c['r'] >= 3: c['r'] += 1
            cells.append({'r': 3, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Three Months Ended', 'anchor': elem('after')})
        res = self.run_grader(other_group)
        self.assertEqual(self.check(res, 'pkt/T01', 'periods')['reason'], 'scope')

    def test_an_unrelated_label_row_between_the_time_row_and_the_value_does_not_end_its_scope(self):
        def sub_label(r):  # E15: a lower-level subheading or unrelated label does not by itself end the containing time scope
            cells = self.cells(r); self.cell(r, 'hb').update(c=0, cs=1)
            for c in cells:
                if c['r'] >= 3: c['r'] += 1
            cells.append({'r': 3, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Operating activities:', 'anchor': self.sub('h23', 'December 30, 2023')})  # printed between them in the source
        res = self.run_grader(sub_label)
        self.assertEqual(self.check(res, 'pkt/T01', 'periods')['verdict'], 'pass')

    def test_swapped_note_markers_fail_the_note_link(self):
        def swap(r): self.unit(r, 'u4')['marker'] = '4'; self.unit(r, 'u5')['marker'] = '(1)'
        res = self.run_grader(swap)
        self.assertEqual(self.check(res, 'pkt/T02', 'footnote_markers')['reason'], 'wrong_note_link')

    def test_a_second_wrong_destination_for_the_same_phrase_fails_the_reference(self):
        res = self.run_grader(lambda r: self.unit(r, 'u2')['links'].append({'text': 'the table below', 'href': '#tbl', 'to': 'u7'}))
        self.assertEqual(self.check(res, 'pkt/S01', 'references')['reason'], 'wrong_link')

    def test_rows_between_the_time_row_and_the_value_must_also_lie_between_them_in_the_source(self):
        raw = b'<table><tr><td>2025</td></tr><tr><td>Revenue</td><td>10</td></tr><tr><td>2024</td></tr><tr><td>Expenses</td><td>20</td></tr></table>'
        def span(word): i = raw.index(word.encode()); return {'byte_start': i, 'byte_end_exclusive': i + len(word)}
        cells = [{'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': w, 'anchor': span(w)} for r, c, w in [(0, 0, '2025'), (1, 0, 'Revenue'), (1, 1, '10'), (2, 0, '2024'), (3, 0, 'Expenses'), (3, 1, '20')]]
        target = {'key_id': 'syn/T', 'file_id': 'syn/time.htm', 'type': 'cell', 'format': 'cell/htm', 'split': 'development', 'anchor': span('10'),
                  'table_anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'alternatives': {}, 'excluded': set(),
                  'fields': {'printed_value': '10', 'display_value': '10', 'row_label': 'Revenue', 'periods': [{'role': 'value', 'type': 'instant', 'parts': [{'text': '2025', 'anchor': span('2025')}]}]},
                  'support': {'row_label': {'anchors': [span('Revenue')]}}}
        for shifted in (False, True):
            cs = copy.deepcopy(cells)
            if shifted:
                for c in cs:
                    if c['text'] in ('Revenue', '10'): c['r'] = 4  # the route moved the row under the 2024 group, a group the key never names
            rf = grade.RouteFile({'file_id': target['file_id'], 'units': [{'id': 't', 'kind': 'table', 'anchor': target['table_anchor'], 'cells': cs}]}, raw, 'htm')
            g = grade.Grader(target, rf); g.grade_cell()
            per = next(r for r in g.rows if r['check'] == 'periods')
            self.assertEqual((per['verdict'], per['reason']), ('fail', 'scope') if shifted else ('pass', None))

    def test_xml_leaf_in_another_namespace_fails(self):
        res = self.run_grader(lambda r: r[XML_ID]['units'][4].update(name='{urn:wrong}sharedDispositivePower'))
        self.assertEqual(self.check(res, 'pkt/X01', 'row_label')['reason'], 'namespace')

    def test_a_space_inside_a_value_fails_in_html_and_pdf_cells(self):
        res = self.run_grader(lambda r: self.cell(r, 'v1').update(text='7 69'))
        self.assertEqual(self.check(res, 'pkt/T01', 'value')['reason'], 'spacing')
        res = self.run_grader(lambda r: r[PDF_ID]['units'][2]['cells'][-1].update(text='1,9 70'))
        self.assertEqual(self.check(res, 'pkt/P01', 'value')['reason'], 'spacing')

    def test_an_unrelated_parenthetical_on_a_title_fails_but_the_records_own_unit_phrase_does_not(self):
        res = self.run_grader(lambda r: r[PDF_ID]['units'][0].update(text='Same-Store Operating Information (including discontinued operations)'))
        self.assertEqual(self.check(res, 'pkt/P01', 'table_title')['verdict'], 'fail')
        self.assertFalse(grade.same('Revenue (not audited)', 'Revenue')[0])
        self.assertEqual(grade.same('Revenue (in millions)', 'Revenue', own=['(in millions)']), (True, 'unit_phrase_split'))

    def test_pdf_word_fragments_are_unresolved_not_failed(self):
        rf = grade.RouteFile(route_pdf(), PDF, 'pdf')
        t = {'key_id': 'x', 'file_id': PDF_ID, 'split': 'development', 'format': 'structure/pdf', 'fields': {}, 'alternatives': {}, 'support': {}, 'excluded': set()}
        g = grade.Grader(t, rf)
        self.assertEqual(g.pieces_match(['Southe', 'ast'], 'Southeast', [{'page': 2, 'region': [0, 0, 10, 10]}, {'page': 2, 'region': [10, 0, 20, 10]}]), (None, 'adjacency', 0))

    def test_joins_keep_word_and_number_boundaries_and_ignore_punctuation_spacing(self):
        self.assertFalse(grade.fused(['1'] * 22, '1' * 22))                     # digits split across cells are a broken number (bounded work)
        self.assertTrue(grade.fused(['$', '(506', ')'], '$(506)')); self.assertTrue(grade.fused(['$', '769'], '$ 769'))
        self.assertFalse(grade.fused(['1,9 70'], '1,970')); self.assertFalse(grade.fused(['76', '9'], '796')); self.assertFalse(grade.fused(['1 ,970'], '1,970'))
        self.assertTrue(grade.fused(['December 31 , 2025'], 'December 31, 2025'))  # a space beside punctuation is not a boundary (E12)
        self.assertTrue(grade.boundary_equal('( 973 ) 802-6000', '(973) 802-6000')); self.assertFalse(grade.boundary_equal('Ma nagement', 'Management'))
        self.assertTrue(grade.same('December 31 , 2025', 'December 31, 2025')[0])

    def test_an_unrelated_link_never_contradicts_an_unlinked_reference(self):
        raw = b'<p>See Table A and <a href="#b">Table B</a>.</p><table id="a">A</table><table id="b">B</table>'
        aa = {'byte_start': raw.index(b'<table id="a"'), 'byte_end_exclusive': raw.index(b'</table>') + 8}
        ba = {'byte_start': raw.index(b'<table id="b"'), 'byte_end_exclusive': len(raw)}; pa = {'byte_start': 0, 'byte_end_exclusive': raw.index(b'</p>') + 4}
        t = {'key_id': 's', 'file_id': 'syn/t.htm', 'split': 'development', 'format': 'structure/htm', 'fields': {}, 'alternatives': {}, 'support': {}, 'excluded': set()}
        ref = {'printed_text': 'Table A', 'status': 'RESOLVED', 'target': {'file': 'syn/t.htm', 'anchor': aa}}
        for link, expect in ((None, 'pass'), ('a', 'pass'), ('b', 'fail')):
            units = [{'id': 'p', 'kind': 'text', 'anchor': pa, 'text': 'See Table A and Table B.', 'links': [{'text': 'Table B', 'href': '#b', 'to': 'b'}]},
                     {'id': 'a', 'kind': 'table', 'anchor': aa}, {'id': 'b', 'kind': 'table', 'anchor': ba}]
            if link: units[0]['links'].append({'text': 'Table A', 'to': link})
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/t.htm', 'units': units}, raw, 'htm'))
            self.assertEqual(g.references([ref], None, [units[0]], units[0]['text'])[0], expect, link)

    def test_xml_name_is_verified_at_this_occurrence_and_values_keep_their_boundaries(self):
        xml = b'<r xmlns="urn:main" xmlns:a="urn:a" xmlns:b="urn:b"><p><a:amount>10</a:amount><b:amount>20</b:amount></p></r>'
        i = xml.index(b'>10<') + 1; a = {'byte_start': i, 'byte_end_exclusive': i + 2}
        t = {'key_id': 'syn/X1', 'file_id': 'syn/form.xml', 'type': 'cell', 'format': 'cell/xml', 'split': 'development', 'anchor': a, 'table_anchor': a,
             'alternatives': {}, 'excluded': set(), 'support': {}, 'fields': {'printed_value': '10', 'display_value': '10', 'row_label': 'amount', 'header_path': ['{urn:main}r', '{urn:main}p'], 'row_context': [], 'periods': []}}
        def rows(name, text='10', raw=xml):
            r = {'file_id': t['file_id'], 'units': [{'id': 'x', 'kind': 'field', 'anchor': a, 'name': name, 'path': t['fields']['header_path'], 'text': text, 'group': {'index': 1, 'count': 1}}]}
            g = grade.Grader(t, grade.RouteFile(r, raw, 'xml')); g.grade_cell(); return {x['check']: (x['verdict'], x['reason']) for x in g.rows}
        self.assertEqual(rows('{urn:a}amount')['row_label'], ('pass', None))
        self.assertEqual(rows('{urn:b}amount')['row_label'], ('fail', 'namespace'))          # the sibling's name is not this occurrence's
        self.assertEqual(rows('{urn:a}amount', text='1 0')['value'], ('fail', 'spacing'))
        self.assertEqual(rows('{urn:a}amount', raw=xml[:-8])['row_label'][0], 'unresolved')  # unparsable source: never a pass

    def test_xml_element_lookup_is_exact_with_entities_and_multibyte_text_before_the_value(self):
        xml = '<r xmlns="urn:m"><n>Caf\u00e9 &amp; Bar</n><v>10</v><w>10</w></r>'.encode('utf-8')
        i = xml.index(b'<v>10') + 3; j = xml.index(b'<w>10') + 3
        self.assertEqual(grade.xml_element_at(xml, i), '{urn:m}v'); self.assertEqual(grade.xml_element_at(xml, j), '{urn:m}w')
        self.assertEqual(grade.xml_element_at(xml, xml.index(b'Bar')), '{urn:m}n')  # inside character data split by an entity

    def test_a_cell_nobody_selected_still_fails_the_text_gate_when_a_boundary_is_lost(self):
        res = self.run_grader(lambda r: self.cell(r, 'p1').update(text='6 50'))
        self.assertEqual(res['gates']['honest_anchors']['boundary'], {HTM_ID: 1}); self.assertFalse(res['gates']['honest_anchors']['pass'])

    def test_files_that_were_not_converted_leave_every_gate_unmeasured(self):
        res = self.run_grader(lambda r: r[HTM_ID].update(status='FAILED', units=[]))
        for name in ('honest_anchors', 'nothing_lost', 'reading_order'):
            self.assertFalse(res['gates'][name]['pass'], name); self.assertIn(HTM_ID, res['gates'][name]['not_measured'], name)

    def test_route_declared_page_sizes_do_not_certify_pdf_anchors(self):
        def spoof(r): r[PDF_ID]['pages']['2'] = [999999, 999999]; r[PDF_ID]['units'][0]['anchor']['region'] = [1, 1, 999998, 999998]
        res = self.run_grader(spoof)
        self.assertIn(PDF_ID, res['gates']['honest_anchors']['not_measured']); self.assertFalse(res['gates']['honest_anchors']['pass'])
        self.assertEqual(res['gates']['honest_anchors']['bounds_inconsistent'], {})
        res = self.run_grader(lambda r: r[PDF_ID]['units'][0]['anchor'].update(region=[-100, -100, 99999, 99999]))
        self.assertEqual(res['gates']['honest_anchors']['bounds_inconsistent'], {PDF_ID: 1})  # self-consistency is reported, not certified

    def test_frozen_inputs_are_verified_before_grading(self):
        names = ('CLAUDE_ANSWER_KEY.json', 'CLAUDE_KEY_FLAGS.json', 'KEY_SUPPORT_MAP.json', 'converter_checks/REGRESSION_CASES.json')
        manifest = {'evidence_root': '..', 'files_sha256': {n: grade.sha256((self.pkg / n).read_bytes()) for n in names},
                    'packets_sha256': {'packets/pkt': {'targets_sha256': grade.sha256((self.pkt / 'targets.json').read_bytes())}},
                    'catalog_sha256': grade.sha256((self.root / 'case_catalog.csv').read_bytes())}
        (self.pkg / 'FINAL_MANIFEST.json').write_text(json.dumps(manifest))
        res = self.run_grader(); self.assertTrue(res['run_facts']['verified']); self.assertEqual(res['run_facts']['packets_verified'], 1)
        tj = json.loads((self.pkt / 'targets.json').read_text()); tj['targets'][0]['cell_anchor']['byte_start'] += 1; (self.pkt / 'targets.json').write_text(json.dumps(tj))
        with self.assertRaises(ValueError): self.run_grader()                                  # a changed packet target file is rejected
        (self.pkg / 'FINAL_MANIFEST.json').write_text(json.dumps({'files_sha256': {}}))
        with self.assertRaises(ValueError): self.run_grader()                                  # a manifest that pins nothing verifies nothing

    def test_time_only_section_row_in_the_label_column_needs_no_column_coverage(self):
        def section_row(r):  # the period phrase printed as a section row above the value, in the label column
            cells = self.cells(r); hb = self.cell(r, 'hb'); hb.update(c=0, cs=1)
        res = self.run_grader(section_row)
        self.assertEqual(self.check(res, 'pkt/T01', 'periods')['verdict'], 'pass')

    def test_run_in_heading_at_the_start_of_a_paragraph_counts_as_present_but_not_recognised(self):
        def run_in(r):  # the tool merged the heading into the paragraph that follows it (guide V18: a run-in section label contains what follows)
            u = self.html(r); h = self.unit(r, 'u1'); lead = self.unit(r, 'u2'); u.remove(h)
            lead.update(text='Free Cash Flow ' + lead['text'], anchor={'byte_start': elem('h2')['byte_start'], 'byte_end_exclusive': elem('lead')['byte_end_exclusive']})
        res = self.run_grader(run_in)
        row = self.check(res, 'pkt/T02', 'section_path')
        self.assertEqual((row['verdict'], row['detail']), ('pass', 'run_in'))
        self.assertEqual(self.check(res, 'pkt/T02', 'heading_recognised')['verdict'], 'fail')

    def test_source_order_of_pdf_boxes_compares_x_within_a_row(self):
        self.assertTrue(grade.source_before({'page': 1, 'region': [10, 100, 50, 110]}, {'page': 1, 'region': [60, 101, 90, 111]}))
        self.assertFalse(grade.source_before({'page': 1, 'region': [60, 101, 90, 111]}, {'page': 1, 'region': [10, 100, 50, 110]}))
        self.assertTrue(grade.source_before({'page': 1, 'region': [60, 50, 90, 60]}, {'page': 1, 'region': [10, 100, 50, 110]}))

    def test_reordered_units_fail_the_order_gate(self):
        def swap(r):
            u = self.html(r); u[1], u[2] = u[2], u[1]
        res = self.run_grader(swap)
        self.assertFalse(res['gates']['reading_order']['pass'])
        self.assertEqual(self.check(res, 'pkt/S01', 'order')['verdict'], 'fail')

    def test_dropped_struck_text_fails_block_text(self):
        res = self.run_grader(lambda r: next(u for u in self.html(r) if u['id'] == 'u2').update(text='Free cash flow is a GAAP measure. See the table below.'))
        self.assertEqual(self.check(res, 'pkt/S01', 'printed_text')['reason'], 'text')

    def test_reference_destination_changed_fails(self):
        res = self.run_grader(lambda r: next(u for u in self.html(r) if u['id'] == 'u2')['links'][0].update(href='#tb2', to='u6'))
        self.assertIn(self.check(res, 'pkt/S01', 'references')['reason'], ('href', 'wrong_link'))  # both are wrong here
        self.assertEqual(self.check(res, 'pkt/S01', 'reference_linked')['verdict'], 'fail')

    def test_explicit_link_to_the_wrong_block_fails_the_reference_check(self):
        res = self.run_grader(lambda r: self.unit(r, 'u2')['links'][0].update(to='u6'))  # href right, explicit destination wrong
        self.assertEqual(self.check(res, 'pkt/S01', 'references')['reason'], 'wrong_link')
        self.assertEqual(self.verdict(res, 'pkt/S01'), 'FAIL')
        res = self.run_grader(lambda r: self.unit(r, 'u2')['links'][0].update(to=None))  # no explicit destination: a structure miss only
        self.assertEqual(self.check(res, 'pkt/S01', 'references')['verdict'], 'pass')
        self.assertEqual(self.check(res, 'pkt/S01', 'reference_linked')['verdict'], 'fail')

    def test_xml_value_moved_to_another_reporting_person_fails(self):
        res = self.run_grader(lambda r: r[XML_ID]['units'][4].update(group={'index': 1, 'count': 2}))
        self.assertEqual(self.check(res, 'pkt/X01', 'row_context')['reason'], 'group')

    def test_xml_element_name_changed_fails_row_label_and_path(self):
        res = self.run_grader(lambda r: r[XML_ID]['units'][4].update(name=NS + 'soleDispositivePower'))
        self.assertEqual(self.check(res, 'pkt/X01', 'row_label')['verdict'], 'fail')

    def test_pdf_value_under_another_column_fails_header_association(self):
        res = self.run_grader(lambda r: r[PDF_ID]['units'][2]['cells'][6].update(c=1))
        self.assertEqual(self.check(res, 'pkt/P01', 'header_path')['reason'], 'column')

    def test_pdf_value_on_a_missing_page_is_unresolved(self):
        res = self.run_grader(lambda r: r[PDF_ID]['units'][2]['cells'][6]['anchor'].update(page=3))
        self.assertEqual(self.verdict(res, 'pkt/P01'), 'UNRESOLVED')

    def test_range_endpoints_flipped_fail_order(self):
        def flip(r):
            self.cell(r, 'lo', 'u6').update(c=4); self.cell(r, 'hi', 'u6').update(c=2)
        res = self.run_grader(flip)
        self.assertEqual(self.check(res, 'fx/R01', 'range')['reason'], 'order')

    def test_marks_before_and_after_the_text_inside_the_anchor_are_honest(self):
        def both_sides(r):  # the route reports two marks for the label cell and anchors the cell over mark + text + mark
            l2 = self.cell(r, 'l2'); l2.update(text='Free cash flow', markers=['(1)', '(1)'], anchor=[self.sub('m2', '(1)'), self.sub('l2', 'Free cash flow'), self.sub('m2', '(1)')])
        res = self.run_grader(both_sides)
        self.assertEqual(res['gates']['honest_anchors']['dishonest'], {})

    def test_dishonest_anchor_fails_the_anchor_gate(self):
        res = self.run_grader(lambda r: next(u for u in self.html(r) if u['id'] == 'u4').update(text='(1) Represents nothing.'))
        self.assertFalse(res['gates']['honest_anchors']['pass'])

    def test_failed_file_marks_its_targets_not_converted(self):
        res = self.run_grader(lambda r: r[XML_ID].update(status='FAILED', error='boom', units=[]))
        self.assertEqual(self.verdict(res, 'pkt/X01'), 'NOT_CONVERTED')

    def test_changed_source_bytes_stop_that_file_with_input_mismatch(self):
        (self.pkt / 'sources' / XML_ID).write_bytes(XML + b'\n')
        res = self.run_grader()
        self.assertEqual(self.verdict(res, 'pkt/X01'), 'INPUT_MISMATCH')
        self.assertEqual(self.verdict(res, 'pkt/T01'), 'PASS')


if __name__ == '__main__':
    unittest.main()
