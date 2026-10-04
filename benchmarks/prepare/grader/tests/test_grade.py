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
    'pkt/X01': {'printed_value': NONE, 'row_label': NONE, 'header_path': NONE, 'row_context': NONE, 'unit_printed': {'how': 'model', 'model': 'openai', 'anchors': [xml_text('Units', 'securitiesClassTitle')]}},  # the unit's declared source place (Codex R13 C3)
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


PERSON_AT = [XML.index(b'<ns1:reportingPersonInfo>'), XML.index(b'<ns1:reportingPersonInfo>', XML.index(b'<ns1:reportingPersonInfo>') + 1)]  # each instance by its start tag


def route_xml():
    f = lambda i, name, text, g: {'id': f'x{i}', 'kind': 'field', 'name': NS + name, 'path': PATH, 'group': {'index': g, 'count': 2, 'at': PERSON_AT[g - 1]}, 'text': text,
                                  'anchor': xml_text(text, name)}
    return {'schema': 'prepare-route-output/1', 'file_id': XML_ID, 'sha256': sha(XML), 'status': 'OK', 'error': None, 'seconds': 0.1, 'not_read': {'attribute_values': 2},
            'route': {'name': 'fixture', 'tool': 'hand', 'version': '1', 'settings': {}, 'adapter': 'test', 'linker': None},
            'units': [{'id': 'x0', 'kind': 'field', 'name': NS + 'securitiesClassTitle', 'path': PATH[:2], 'group': {'index': 1, 'count': 1, 'at': XML.index(b'<ns1:edgarSubmission')}, 'text': 'Units',
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

    def declare(self, exclusions=(), kinds=('image',)):
        """The package names its declarations in the frozen manifest, pinned like every other input (package 3, contract R4)."""
        decl = {'decisions': [{'rule': 'E10', 'policy': {'approximate_kinds': list(kinds)}}, {'rule': 'E10', 'exclusions': list(exclusions)}]}
        (self.pkg / 'CONTRACT_DECISIONS_R4.json').write_text(json.dumps(decl))
        pins = {rel: sha((self.pkg / rel).read_bytes()) for rel in grade.KEY_FILES + ('CONTRACT_DECISIONS_R4.json',)}
        (self.pkg / 'FINAL_MANIFEST.json').write_text(json.dumps({'evidence_root': '..', 'contract_declarations': 'CONTRACT_DECISIONS_R4.json', 'files_sha256': pins,
                                                                   'packets_sha256': {'packets/pkt': {'targets_sha256': sha((self.pkt / 'targets.json').read_bytes())}}}))

    def verdict(self, res, key_id):
        return res['targets'][key_id]['verdict']

    def html(self, route):
        return route[HTM_ID]['units']

    def unit(self, r, id_):
        return next(u for u in self.html(r) if u['id'] == id_)

    def cells(self, route, unit='u3'):
        return next(u for u in self.html(route) if u['id'] == unit)['cells']

    def cell(self, route, id_, unit='u3'):
        want = elem(id_)
        return next(c for c in self.cells(route, unit) if c['anchor'] == want)

    def block_row(self, unit, want='Start of three. More words.', region=(0, 0, 100, 20), approximate=False):
        """One structure target on page 3 of a two-page PDF route, graded against one route unit: (verdict, reason, detail) of `printed_text`."""
        t = {'key_id': 'syn/B1', 'file_id': 'syn/f.pdf', 'format': 'structure/pdf', 'type': 'structure', 'split': 'development', 'anchor': {'page': 3, 'region': list(region)},
             'alternatives': {}, 'excluded': set(), 'support': {}, 'fields': {'printed_text': want, 'kind': 'image' if approximate else 'paragraph'}, **({'approximate': True} if approximate else {})}
        g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.pdf', 'units': [unit], 'pages': {2: [612, 792], 3: [612, 792]}}, None, 'pdf')); g.grade_structure()
        r = next(r for r in g.rows if r['check'] == 'printed_text'); return r['verdict'], r.get('reason'), r.get('detail')


class CorrectOutputTests(GraderFixture):
    def test_every_target_passes_and_every_gate_holds(self):
        res = self.run_grader()
        self.assertTrue(all(v['verdict'] == 'PASS' for v in res['targets'].values()), res['targets'])
        g = res['gates']
        for name in ('ids_and_run_facts', 'reading_order', 'markers_apart'): self.assertTrue(g[name]['pass'], (name, g[name]))
        self.assertTrue(g['honest_anchors']['measured_pass'])
        self.assertEqual(g['nothing_lost']['not_measured'], [PDF_ID])  # no text layer: coverage cannot be certified
        self.assertFalse(g['nothing_lost']['pass']); self.assertTrue(g['nothing_lost']['measured_pass'])
        self.assertEqual(g['honest_anchors']['not_measured'], [PDF_ID, HTM_ID])  # no independent page sizes: PDF positions are not certified; the HTML route carries a reading of its picture, which the bytes cannot certify (Codex R17-C4)

    def test_converters_get_a_source_list_without_any_answers(self):
        (self.pkg / 'CLAUDE_ANSWER_KEY.json').rename(self.pkg / 'answers.hidden')  # no answers readable
        srcs = grade.load_sources(self.pkg, self.root / 'case_catalog.csv')
        self.assertEqual({(x['file_id'], x['split']) for x in srcs} >= {(HTM_ID, 'development'), (XML_ID, 'stratified_control'), (PDF_ID, 'heldout')}, True)
        self.assertTrue(all(x['path'].exists() and len(x['sha256']) == 64 for x in srcs))

    def test_summary_counts_targets_by_split_and_format(self):
        s = self.run_grader()['summary']['by_split_format']
        self.assertEqual(s['development']['cell/htm'], {'targets': 4, 'PASS': 4, 'FAIL': 0, 'UNRESOLVED': 0, 'NOT_CONVERTED': 0, 'EXCLUDED': 0, 'APPROXIMATE': 0})
        self.assertEqual(s['development']['structure/htm']['PASS'], 4)
        self.assertEqual(s['stratified_control']['cell/xml']['PASS'], 1)
        self.assertEqual(s['heldout']['cell/pdf']['PASS'], 1)
        self.assertEqual(self.run_grader()['summary']['supplement']['PASS'], 1)

    def test_package_declarations_exclude_targets_and_report_pictures_approximately(self):
        # package 3 (owner decisions (a) and (d), Codex R13 E10 R4): the manifest names the declarations; a declared page-number target is EXCLUDED (never a pass,
        # counted apart); a block the key declares an image is APPROXIMATE with its word error rate and aligned critical tokens; a declaration that does not match the key stops the run
        declare = lambda anchor: self.declare([{'key_id': 'pkt/S02', 'role': 'page_number', 'file_id': HTM_ID, 'sha256': sha(HTML), 'anchor': anchor}])
        declare(elem('h2'))
        res = self.run_grader(); self.assertEqual(res['run_facts']['contract_declarations'], 'CONTRACT_DECISIONS_R4.json')
        self.assertEqual((self.verdict(res, 'pkt/S02'), self.check(res, 'pkt/S02', 'target')['reason']), ('EXCLUDED', 'page_number'))
        self.assertEqual(sum(1 for r in res['results'] if r['key_id'] == 'pkt/S02'), 1)  # nothing of it is graded
        self.assertEqual(self.verdict(res, 'pkt/S03'), 'APPROXIMATE')
        d = self.check(res, 'pkt/S03', 'printed_text')['detail']  # exact OCR is still not a pass; the reading is described in full
        self.assertEqual((d['word_error_rate'], d['words'], d['critical'], d['other'], d['edits']), (0.0, {'reference': 6, 'recovered': 6, 'substituted': 0, 'deleted': 0, 'inserted': 0}, {'missing': [], 'extra': []}, {'missing': [], 'extra': []}, []))
        self.assertEqual({k: res['summary']['by_split_format']['development']['structure/htm'][k] for k in ('PASS', 'EXCLUDED', 'APPROXIMATE', 'FAIL')}, {'PASS': 2, 'EXCLUDED': 1, 'APPROXIMATE': 1, 'FAIL': 0})
        self.assertIn('| printed_text | 2 | 0 | 0 | 1 | 0 | 0 | 0 |', (self.root / 'out' / 'summary.md').read_text())  # the per-check table shows approximate readings (Codex R14-5): two blocks pass, one excluded, one approximate
        def garble(route): next(u for u in self.html(route) if u['id'] == 'u8')['text'] = 'Picture words one. Picture words 2.'
        row = self.check(self.run_grader(garble), 'pkt/S03', 'printed_text')
        self.assertEqual((row['verdict'], row['detail']['critical']['extra'], row['detail']['edits']), ('approximate', ['2'], [{'op': 'replace', 'reference': ['two'], 'output': ['2']}]))
        dropped = lambda route: self.html(route).remove(next(u for u in self.html(route) if u['id'] == 'u8'))
        self.assertEqual(self.verdict(self.run_grader(dropped), 'pkt/S03'), 'UNRESOLVED')  # a dropped picture is not approximate
        declare(elem('lead'))
        with self.assertRaises(ValueError): self.run_grader()  # the declared anchor is not the target's

    def test_an_approximate_reading_replaces_only_the_transcription_comparison(self):
        # Codex R14-3: the same reading labelled text gets the same verdict and gate; a label exempts no text from the source; an impossible anchor locates nothing and is
        # dishonest; an empty reading is zero recovery; a block moved out of order fails whatever its reading
        self.declare(); im = lambda r: next(u for u in self.html(r) if u['id'] == 'u8')
        base = self.run_grader(); self.assertEqual((self.verdict(base, 'pkt/S03'), base['gates']['honest_anchors']['dishonest']), ('APPROXIMATE', {}))
        as_text = self.run_grader(lambda r: im(r).update(kind='text'))
        self.assertEqual((self.verdict(as_text, 'pkt/S03'), as_text['gates']['honest_anchors']['dishonest']), ('APPROXIMATE', {}))  # the source shows a picture there: the same outcome
        wrong = self.run_grader(lambda r: self.unit(r, 'u9').update(kind='image', text='Invented words'))
        self.assertEqual(wrong['gates']['honest_anchors']['dishonest'], {HTM_ID: 1})  # ordinary source text relabelled image: still certified against the bytes
        bad = self.run_grader(lambda r: im(r).update(anchor={'byte_start': -1, 'byte_end_exclusive': len(HTML) + 1}))
        self.assertEqual((self.verdict(bad, 'pkt/S03'), bad['gates']['honest_anchors']['dishonest']), ('UNRESOLVED', {HTM_ID: 1}))  # a position that cannot be true locates nothing
        empty = self.run_grader(lambda r: im(r).update(text='')); d = self.check(empty, 'pkt/S03', 'printed_text')['detail']
        self.assertEqual((self.verdict(empty, 'pkt/S03'), d['word_error_rate'], d['words']['recovered'], d['words']['deleted']), ('APPROXIMATE', 1.0, 0, 6))  # zero recovery, stated as such
        def moved(r): u = im(r); self.html(r).remove(u); self.html(r).insert(3, u)
        res = self.run_grader(moved); self.assertEqual((self.verdict(res, 'pkt/S03'), res['targets']['pkt/S03']['failed']), ('FAIL', ['order']))  # a strict failure outranks the approximate reading

    def test_a_declared_page_number_left_out_is_not_required_content_loss(self):
        # Codex R14-4: coverage subtracts the declared exclusion's own bytes only and counts them apart; an undeclared footer or any other text left out stays a loss
        key = json.loads((self.pkg / 'CLAUDE_ANSWER_KEY.json').read_text()); next(t for t in key if t['key_id'] == 'pkt/S02')['fields'].update(printed_text='4', kind='page_footer', section_path=[])
        (self.pkg / 'CLAUDE_ANSWER_KEY.json').write_text(json.dumps(key))
        targets = json.loads((self.pkt / 'targets.json').read_text()); next(t for t in targets['targets'] if t['id'] == 'S02')['block_anchor'] = elem('pg'); (self.pkt / 'targets.json').write_text(json.dumps(targets))
        drop = lambda uid: (lambda r: self.html(r).remove(self.unit(r, uid)))
        self.declare([{'key_id': 'pkt/S02', 'role': 'page_number', 'file_id': HTM_ID, 'sha256': sha(HTML), 'anchor': elem('pg')}])
        res = self.run_grader(drop('u7')); nl = res['gates']['nothing_lost']
        self.assertEqual((self.verdict(res, 'pkt/S02'), nl['measured_pass'], nl['uncovered'], nl['excluded_chars']), ('EXCLUDED', True, {}, {HTM_ID: 1}))
        nl = self.run_grader(drop('u9'))['gates']['nothing_lost']; self.assertEqual((nl['measured_pass'], nl['excluded_chars']), (False, {}))  # other text left out is still a loss
        self.declare([]); self.assertFalse(self.run_grader(drop('u7'))['gates']['nothing_lost']['measured_pass'])  # undeclared: a loss, as before

    def test_an_xml_field_is_the_innermost_at_the_keys_position_never_the_prose_around_it(self):
        # Codex R14-2: prose with a field inside emits both; the field owns the position; a missing child does not fall back silently; the same bytes claimed twice is ambiguous
        from benchmarks.prepare.grader.adapters import xml_fields as xf
        def rows(raw, units=None, nth=0):
            at = [m.start() for m in re.finditer(b'10', raw)][nth]; units = xf.units_of(raw) if units is None else units
            t = {'key_id': 'syn/X3', 'file_id': 'syn/x.xml', 'format': 'cell/xml', 'type': 'cell', 'split': 'development', 'anchor': {'byte_start': at, 'byte_end_exclusive': at + 2}, 'alternatives': {}, 'excluded': set(), 'support': {},
                 'fields': {'printed_value': '10', 'display_value': '10', 'row_label': 'amount', 'header_path': ['r', 'p']}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/x.xml', 'units': units}, raw, 'xml')); u = g.grade_cell()
            return (u or {}).get('name'), {r['check']: (r['verdict'], r.get('reason')) for r in g.rows if r['check'] in ('value', 'row_label', 'header_path')}
        plain, mixed = b'<r><p><amount>10</amount></p></r>', b'<r><p>Balance: <amount>10</amount> shares.</p></r>'
        allpass = {'value': ('pass', None), 'row_label': ('pass', None), 'header_path': ('pass', None)}
        self.assertEqual(rows(plain), ('amount', allpass)); self.assertEqual(rows(mixed), ('amount', allpass))  # the field inside the prose, not the prose
        name, r = rows(mixed, [u for u in xf.units_of(mixed) if u['name'] != 'amount']); self.assertEqual((name, r['value'][0], r['row_label']), ('p', 'fail', ('fail', 'name')))  # the child missing: the prose is judged as what it is, never a silent stand-in
        two = b'<r><p><amount>10</amount></p><p>Balance: <amount>10</amount> shares.</p></r>'
        self.assertEqual(rows(two, nth=1), ('amount', allpass))  # the second occurrence: the field of the second paragraph
        twin = xf.units_of(plain); twin.append(dict(twin[0], id='dup'))
        self.assertEqual(rows(plain, twin)[1]['value'], ('unresolved', 'ambiguous'))  # the same bytes claimed by two fields

    def test_critical_differences_are_read_in_order_with_their_context_and_nothing_is_dropped(self):
        # Codex R13 + R14-5: unordered multisets missed swapped values, a dropped Unicode minus and a moved negation; a unit, a currency symbol or a scale word beside a
        # number is critical too; every other difference is kept for review, never declared harmless; the word counts come from the same edit table as the rate
        c = grade.critical
        self.assertEqual(c('Revenue 20. Profit 10.', 'Revenue 10. Profit 20.')['critical'], {'missing': ['10', '20'], 'extra': ['20', '10']})
        self.assertEqual(c('Earnings 20', 'Earnings −20')['critical']['missing'], ['-20'])
        self.assertEqual(c('Buy and do not sell', 'Do not buy and sell')['critical'], {'missing': ['not buy'], 'extra': ['not sell']})  # a negation is read with the word it governs
        self.assertEqual(c('10 barrels', '10 shares')['critical'], {'missing': ['10 shares'], 'extra': ['10 barrels']})  # a number with the word it governs
        self.assertEqual(c('£20', '€20')['critical'], {'missing': ['€20'], 'extra': ['£20']})  # a currency symbol by its Unicode class, no list
        self.assertEqual(c('20 million', '20 billion')['critical'], {'missing': ['20 billion'], 'extra': ['20 million']})
        d = c('Sales rose sharply', 'Sales fell sharply')
        self.assertEqual((d['critical'], d['other'], d['edits']), ({'missing': [], 'extra': []}, {'missing': ['fell'], 'extra': ['rose']}, [{'op': 'replace', 'reference': ['fell'], 'output': ['rose']}]))  # not critical, still reported
        same = c('Sales rose 5% to $1.2 million in 2024', 'Sales rose 5% to $1.2 million in 2024'); self.assertEqual((same['edits'], same['reference_numbers']), ([], 3))
        self.assertEqual(c("We don't expect growth", "We don't expect growth")['edits'], [])
        self.assertEqual(grade.wer_counts('revenue was flat elsewhere rose', 'revenue rose'), {'reference': 2, 'recovered': 2, 'substituted': 0, 'deleted': 0, 'inserted': 3, 'rate': 1.5})
        self.assertEqual(grade.wer_counts('', 'three words here'), {'reference': 3, 'recovered': 0, 'substituted': 0, 'deleted': 3, 'inserted': 0, 'rate': 1.0})  # an empty reading: zero recovery

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

    def test_table_context_may_sit_in_the_title_block_before_the_data_table(self):
        # addendum C1, the real SL Green shape (Codex package-2 verdict): a separate layout table prints the title, 'Unaudited' and the unit line,
        # closes, and the data table follows as a sibling; the nested variant below is a second control
        for raw, data_end in ((b'<table><tr><td><div id="ttl">KEY FINANCIAL DATA</div><div>Unaudited</div><div>(Dollars in Thousands)</div></td></tr></table>'
                               b'<div><table id="data"><tr><td>Debt coverage</td><td>2.31x</td></tr></table></div><p>(Dollars in millions)</p>', b'</table></div>'),
                              (b'<table><tr><td><div id="ttl">KEY FINANCIAL DATA</div><div>Unaudited</div><div>(Dollars in Thousands)</div></td></tr>'
                               b'<tr><td><table id="data"><tr><td>Debt coverage</td><td>2.31x</td></tr></table></td></tr></table><p>(Dollars in millions)</p>', b'</table></td></tr></table>')):
            self._context_case(raw, data_end)

    def _context_case(self, raw, data_end):
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        data = {'byte_start': raw.index(b'<table id="data">'), 'byte_end_exclusive': raw.index(data_end) + 8}
        def grader(context, **support):
            t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'2.31x'), 'table_anchor': data,
                 'fields': {'table_title': ['KEY FINANCIAL DATA'], 'row_label': 'Debt coverage', 'unit_printed': 'x'}, 'alternatives': {}, 'excluded': set(),
                 'support': {'table_title': {'how': 'reviewed', 'anchors': [span(b'KEY FINANCIAL DATA')]}, 'table_context': {'how': 'reviewed', 'pieces': context}}}
            return grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': []}, raw, 'htm'))
        piece = lambda text: {'text': text.decode(), 'byte_ranges': [[raw.index(text), raw.index(text) + len(text)]]}
        g = grader([piece(b'Unaudited'), piece(b'(Dollars in Thousands)')])
        self.assertEqual(g.table_context, ['Unaudited', '(Dollars in Thousands)'])
        self.assertTrue(grade.same('KEY FINANCIAL DATA Unaudited (Dollars in Thousands)', 'KEY FINANCIAL DATA', [], g.own + g.table_context)[0])
        with self.assertRaises(ValueError): grader([piece(b'(Dollars in millions)')])                       # after the table: another table's line
        with self.assertRaises(ValueError): grader([{'text': 'Unaudited', 'byte_ranges': [[0, len(raw)]]}])  # a container is not the line

    def test_a_change_between_periods_is_governed_by_the_compared_columns_headings(self):
        # addendum C2: '2' under Variance; its periods are the 2024 and 2023 column headings, which never cover the change column
        raw = b'<table id="t"><tr><td></td><td>2024</td><td>2023</td><td>Variance</td></tr><tr><td>Revenue</td><td>10</td><td>8</td><td>2</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        cells = [{'r': 0, 'c': 1, 'text': '2024', 'anchor': span(b'2024')}, {'r': 0, 'c': 2, 'text': '2023', 'anchor': span(b'2023')}, {'r': 0, 'c': 3, 'text': 'Variance', 'anchor': span(b'Variance')},
                 {'r': 1, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 1, 'c': 1, 'text': '10', 'anchor': span(b'10')}, {'r': 1, 'c': 2, 'text': '8', 'anchor': span(b'>8<')}, {'r': 1, 'c': 3, 'text': '2', 'anchor': span(b'>2<')}]
        def rows(value_anchor, periods, header_path):
            t = {'key_id': 'syn/C', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': value_anchor, 'table_anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)},
                 'fields': {'printed_value': raw[value_anchor['byte_start']:value_anchor['byte_end_exclusive']].strip(b'<>').decode(), 'row_label': 'Revenue', 'header_path': header_path, 'periods': periods}, 'alternatives': {}, 'excluded': set(), 'support': {}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [{'id': 't', 'kind': 'table', 'anchor': t['table_anchor'], 'cells': cells}]}, raw, 'htm')); g.grade_cell()
            return {r['check']: (r['verdict'], r['reason']) for r in g.rows}
        change = [{'role': 'value', 'type': 'duration', 'parts': [{'text': '2024', 'anchor': span(b'2024')}]}, {'role': 'comparison', 'type': 'duration', 'parts': [{'text': '2023', 'anchor': span(b'2023')}]}]
        r = rows(span(b'>2<'), change, ['Variance']); self.assertEqual((r['periods'], r['header_path']), (('pass', None), ('pass', None)))
        r = rows(span(b'>8<'), change, ['Variance']); self.assertEqual((r['periods'][0], r['header_path']), ('pass', ('fail', 'column')))   # moved under 2023: the column proof fails
        plain = [{'role': 'value', 'type': 'duration', 'parts': [{'text': '2023', 'anchor': span(b'2023')}]}]
        self.assertEqual(rows(span(b'10'), plain, ['2024'])['periods'], ('fail', 'column'))                                               # a plain value's period must cover its column

    def test_row_context_header_may_be_in_the_first_part_of_a_continued_table_and_a_row_may_print_a_text_twice(self):
        # addendum C5: a form repeats its header row per page (two table units); a note names the same company as grantor and payee
        raw = (b'<table id="p1"><tr><td>State</td><td>Type</td></tr><tr><td>NY</td><td>CWS</td></tr></table>'
               b'<table id="p2"><tr><td>NJ</td><td>CWS</td><td>105</td></tr></table>'
               b'<table id="n"><tr><td>Grantor</td><td>Payee</td><td>Amount</td></tr><tr><td>Scotts</td><td>Scotts</td><td>$39</td></tr></table>')
        span = lambda text, start=0: {'byte_start': raw.index(text, start), 'byte_end_exclusive': raw.index(text, start) + len(text)}
        p1 = {'id': 'p1', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': raw.index(b'<table id="p2">')}, 'cells': [
            {'r': 0, 'c': 0, 'text': 'State', 'anchor': span(b'State')}, {'r': 0, 'c': 1, 'text': 'Type', 'anchor': span(b'Type')}, {'r': 1, 'c': 0, 'text': 'NY', 'anchor': span(b'NY')}, {'r': 1, 'c': 1, 'text': 'CWS', 'anchor': span(b'CWS')}]}
        p2s = raw.index(b'<table id="p2">'); p2 = {'id': 'p2', 'kind': 'table', 'anchor': {'byte_start': p2s, 'byte_end_exclusive': raw.index(b'<table id="n">')}, 'cells': [
            {'r': 0, 'c': 0, 'text': 'NJ', 'anchor': span(b'NJ')}, {'r': 0, 'c': 1, 'text': 'CWS', 'anchor': span(b'CWS', p2s)}, {'r': 0, 'c': 2, 'text': '105', 'anchor': span(b'105')}]}
        ns = raw.index(b'<table id="n">'); n = {'id': 'n', 'kind': 'table', 'anchor': {'byte_start': ns, 'byte_end_exclusive': len(raw)}, 'cells': [
            {'r': 0, 'c': 0, 'text': 'Grantor', 'anchor': span(b'Grantor')}, {'r': 0, 'c': 1, 'text': 'Payee', 'anchor': span(b'Payee')}, {'r': 0, 'c': 2, 'text': 'Amount', 'anchor': span(b'Amount')},
            {'r': 1, 'c': 0, 'text': 'Scotts', 'anchor': span(b'Scotts')}, {'r': 1, 'c': 1, 'text': 'Scotts', 'anchor': span(b'Scotts', raw.index(b'Scotts') + 1)}, {'r': 1, 'c': 2, 'text': '$39', 'anchor': span(b'$39')}]}
        rf = grade.RouteFile({'file_id': 'syn/f.htm', 'units': [p1, p2, n]}, raw, 'htm')
        def rows(anchor, table, ctx, anchors):
            t = {'key_id': 'syn/R', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': anchor, 'table_anchor': table['anchor'],
                 'fields': {'printed_value': rf.cells_at(anchor)[0]['text'], 'row_context': ctx}, 'alternatives': {}, 'excluded': set(), 'support': {'row_context': {'how': 'reviewed', 'anchors': anchors}}}
            g = grade.Grader(t, rf); g.grade_cell(); return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'row_context')
        self.assertEqual(rows(span(b'105'), p2, [{'header': 'State', 'text': 'NJ'}], [span(b'State'), span(b'NJ')]), ('pass', None))        # header on the previous page
        self.assertEqual(rows(span(b'105'), p2, [{'header': 'Type', 'text': 'NJ'}], [span(b'Type'), span(b'NJ')]), ('fail', 'header'))     # wrong header stays wrong
        self.assertEqual(rows(span(b'$39'), n, [{'header': 'Payee', 'text': 'Scotts'}], [span(b'Payee'), span(b'Scotts', raw.index(b'Scotts') + 1)]), ('pass', None))

    def test_lead_in_keeps_its_place_across_the_sources_own_page_furniture_and_counts_when_kept_whole_inside_a_unit(self):
        # addendum C6: '94 Table of Contents' printed between the lead-in and its table is the source's own layout, not a displacement
        raw = b'<p>The following table presents the totals.</p><p>94 Table of Contents</p><p>Elsewhere.</p><table id="t"><tr><td>Total</td><td>5</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        lead = b'The following table presents the totals.'; table = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table'), 'byte_end_exclusive': len(raw)},
                                                                     'cells': [{'r': 0, 'c': 0, 'text': 'Total', 'anchor': span(b'Total')}, {'r': 0, 'c': 1, 'text': '5', 'anchor': span(b'>5<')}]}
        def rows(units):
            t = {'key_id': 'syn/L', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'>5<'), 'table_anchor': table['anchor'],
                 'fields': {'printed_value': '5', 'row_label': 'Total', 'lead_in': lead.decode()}, 'alternatives': {}, 'excluded': set(), 'support': {'lead_in': {'how': 'reviewed', 'anchors': [span(lead)]}}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units + [table]}, raw, 'htm')); g.grade_cell(); return next((r['verdict'], r['reason'], r['detail']) for r in g.rows if r['check'] == 'lead_in')
        furniture = {'id': 'f', 'kind': 'text', 'text': '94 Table of Contents', 'anchor': span(b'94 Table of Contents')}
        self.assertEqual(rows([{'id': 'l', 'kind': 'text', 'text': lead.decode(), 'anchor': span(lead)}, furniture]), ('pass', None, None))
        moved = dict(furniture, anchor=span(b'Elsewhere.'), text='Elsewhere.')  # a unit the tool moved in front of the table from elsewhere: displacement
        self.assertEqual(rows([{'id': 'l', 'kind': 'text', 'text': lead.decode(), 'anchor': span(lead)}, {'id': 'x', 'kind': 'text', 'text': 'Elsewhere.', 'anchor': None}])[:2], ('fail', 'placement'))
        merged = {'id': 'm', 'kind': 'text', 'text': lead.decode() + ' 94 Table of Contents', 'anchor': [span(lead), span(b'94 Table of Contents')]}
        self.assertEqual(rows([merged]), ('pass', None, 'contained'))

    def test_struck_words_the_key_marks_must_stay_struck_in_the_route(self):
        # Codex round 7 (R7-3): the words survive, the cancellation must too — lost or moved strike-through fails printed_text
        for change, want in ((lambda u: u.pop('struck', None), 'fail'), (lambda u: u.update(struck=['GAAP']), 'fail'), (lambda u: None, 'pass')):
            res = self.run_grader(lambda r: change(self.unit(r, 'u2')))
            self.assertEqual(self.check(res, 'pkt/S01', 'printed_text')['verdict'], want)
        self.assertEqual(self.check(self.run_grader(lambda r: self.unit(r, 'u2').pop('struck', None)), 'pkt/S01', 'printed_text')['reason'], 'struck')

    def test_fragments_of_one_cell_position_pass_in_every_context_field_and_numbers_do_not_span_columns(self):
        # Codex round 7 (R7-4): <span>Rev</span><span>enue</span> kept as two adjacent pieces at one grid position is faithful output in all seven fields;
        # a number split across two grid columns is two numbers, whether the split is at a digit, a decimal point or a thousands comma
        for field, word in (('row_label', 'Revenue'), ('header_path', '2025'), ('table_title', 'Summary'), ('corner_text', 'Summary'), ('unit_printed', 'Millions'), ('periods', '2025'), ('segment_or_basis', 'Adjusted')):
            r, c = (1, 0) if field == 'row_label' else (0, 1) if field in ('header_path', 'periods') else (0, 0)
            left, right = word[:2], word[2:]; grid = [['<td>Other</td>', '<td>Other</td>'], ['<td>Other</td>', '<td>1234</td>']]
            grid[r][c] = '<td id="f"><span>' + left + '</span><span>' + right + '</span></td>'
            raw = ('<table>' + ''.join('<tr>' + ''.join(row) + '</tr>' for row in grid) + '</table>').encode()
            span = lambda text: {'byte_start': raw.index(text.encode()), 'byte_end_exclusive': raw.index(text.encode()) + len(text)}
            evidence = {'byte_start': raw.index(b'<td id="f">'), 'byte_end_exclusive': raw.index(b'</td>', raw.index(b'<td id="f">')) + 5}
            for form in ('whole', 'fragments'):
                fc = [{'r': r, 'c': c, 'text': word, 'anchor': evidence}] if form == 'whole' else [{'r': r, 'c': c, 'text': piece, 'anchor': span(piece)} for piece in (left, right)]
                tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'cells': fc + [{'r': 1, 'c': 1, 'text': '1234', 'anchor': span('1234')}]}
                value = [{'parts': [{'text': word, 'anchor': evidence}]}] if field == 'periods' else [word] if field == 'header_path' else word
                t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span('1234'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
                     'support': {field: {'how': 'model', 'anchors': [evidence]}}, 'fields': {'printed_value': '1234', 'display_value': '1234', field: value}}
                g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [tb]}, raw, 'htm')); g.grade_cell()
                self.assertEqual(next(x['verdict'] for x in g.rows if x['check'] == field), 'pass', (field, form))
        for number, pieces in (('1234', ['12', '34']), ('12.34', ['12.', '34']), ('1,234', ['1,', '234']), ('$1234', ['$', '1234'])):
            for separate in (False, True):
                raw = ('<table><tr><td>' + number + '</td></tr></table>').encode(); start = raw.index(number.encode()); offset = start; cells = []
                for i, piece in enumerate(pieces):
                    cells.append({'r': 0, 'c': i if separate else 0, 'text': piece, 'anchor': {'byte_start': offset, 'byte_end_exclusive': offset + len(piece)}}); offset += len(piece)
                tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'cells': cells}
                t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': {'byte_start': start, 'byte_end_exclusive': offset}, 'table_anchor': tb['anchor'],
                     'alternatives': {}, 'excluded': set(), 'support': {}, 'fields': {'printed_value': number, 'display_value': number}}
                g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [tb]}, raw, 'htm')); g.grade_cell()
                self.assertEqual(next(x['verdict'] for x in g.rows if x['check'] == 'value'), 'fail' if separate and number != '$1234' else 'pass', (number, separate))

    def test_exclusions_are_honoured_and_counted_on_every_grading_path(self):
        # Codex round 7 (R7-6): an excluded meaning field is reported excluded (not not_t1); XML labels and structure text honour exclusions too
        def exclude(kid, field):
            def go(fx):
                p = fx.pkg / 'CLAUDE_KEY_FLAGS.json'; flags = json.loads(p.read_text()); flags['uncertain'].append({'key_id': kid, 'field': field, 'scoring': 'excluded', 'why': 'test'}); p.write_text(json.dumps(flags))
            return go
        base = self.run_grader()['summary']['excluded_fields']
        for kid, field, check in (('pkt/T01', 'unit_interpretation', 'unit_interpretation'), ('pkt/X01', 'row_label', 'row_label'), ('pkt/S01', 'printed_text', 'printed_text')):
            exclude(kid, field)(self); res = self.run_grader()
            self.assertEqual(self.check(res, kid, check)['verdict'], 'excluded', (kid, field))
        self.assertEqual(res['summary']['excluded_fields'], base + 3)  # every exclusion counted, the meaning field included
        self.assertEqual(res['gates']['nothing_lost']['measures'], 'visible source text; declared exclusions counted apart; picture content is not measured')
        self.assertIn(HTM_ID, res['gates']['nothing_lost']['pictures_not_measured'])  # the fixture has one picture: its content is not what the text map measures

    def test_a_compared_columns_heading_must_belong_to_the_values_group(self):
        # Codex package-2 verdict (C2): North and South groups; swapping the year headings between the groups keeps every anchor exact but breaks the association
        raw = (b'<table><tr><td></td><td colspan="3">North</td><td colspan="3">South</td></tr><tr><td></td><td id="a">2024</td><td id="b">2023</td><td id="c">Change</td>'
               b'<td id="d">2022</td><td id="e">2021</td><td id="f">Change</td></tr><tr><td>Sales</td><td>10</td><td>8</td><td id="target">2</td><td>15</td><td>11</td><td>4</td></tr></table>')
        def span(text, after=None):
            a = raw.index(text, raw.index(after) if after else 0); return {'byte_start': a, 'byte_end_exclusive': a + len(text)}
        cells = [{'r': 0, 'c': 1, 'cs': 3, 'text': 'North', 'anchor': span(b'North')}, {'r': 0, 'c': 4, 'cs': 3, 'text': 'South', 'anchor': span(b'South')}]
        for c, (text, ident) in enumerate([(b'2024', b'a'), (b'2023', b'b'), (b'Change', b'c'), (b'2022', b'd'), (b'2021', b'e'), (b'Change', b'f')], 1):
            cells.append({'r': 1, 'c': c, 'text': text.decode(), 'anchor': span(text, b'id="' + ident + b'"')})
        cells += [{'r': 2, 'c': 0, 'text': 'Sales', 'anchor': span(b'Sales')}, {'r': 2, 'c': 3, 'text': '2', 'anchor': span(b'2', b'id="target"')}]
        t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'2', b'id="target"'), 'table_anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)},
             'alternatives': {}, 'excluded': set(), 'support': {'row_label': {'anchors': [span(b'Sales')]}, 'header_path': {'anchors': [span(b'North'), span(b'Change', b'id="c"')]}},
             'fields': {'printed_value': '2', 'display_value': '2', 'row_label': 'Sales', 'header_path': ['North', 'Change'],
                        'periods': [{'role': 'value', 'parts': [{'text': '2024', 'anchor': span(b'2024')}]}, {'role': 'comparison', 'parts': [{'text': '2023', 'anchor': span(b'2023')}]}]}}
        def verdicts(swap):
            cs = [dict(c) for c in cells]
            if swap:
                for c in cs:
                    if c['r'] == 1 and c['c'] in (1, 2, 4, 5): c['c'] += 3 if c['c'] < 3 else -3
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [{'id': 't', 'kind': 'table', 'anchor': t['table_anchor'], 'cells': sorted(cs, key=lambda c: (c['r'], c['c']))}]}, raw, 'htm')); g.grade_cell()
            return {r['check']: (r['verdict'], r['reason']) for r in g.rows}
        self.assertEqual(verdicts(False)['periods'], ('pass', None)); self.assertEqual(verdicts(True)['periods'], ('fail', 'group'))

    def test_a_mark_printed_inside_a_label_header_or_basis_phrase_is_the_records_own_mark(self):
        # ledger class F: the contract allows a mark glued to a label or title (flagged); the comparison must see through it wherever it sits
        self.assertEqual(grade.same('Resolution of NASH and ≥ 1-stage improvement in fibrosis1,2', 'Resolution of NASH and ≥ 1-stage improvement in fibrosis', ['1', '2']), (True, 'marker_in_text'))
        self.assertEqual(grade.same('Living benefit/GMDB features(1):', 'Living benefit/GMDB features:', ['(1)']), (True, 'marker_in_text'))
        self.assertEqual(grade.same('Additional Shares recovered for issuance (iv) in:', 'Additional Shares recovered for issuance in:', ['(iv)']), (True, 'marker_in_text'))
        self.assertEqual(grade.same('Unsecured Notes Covenants (1)', 'Unsecured Notes Covenants', ['(1)']), (True, 'marker_in_text'))
        self.assertEqual(grade.same('Phase 1 trial', 'Phase 1 trial', ['1']), (True, None))  # a 1 the key prints is text, matched as text
        self.assertFalse(grade.same('Living benefit/GMDB features(2):', 'Living benefit/GMDB features:', ['(1)'])[0])  # another mark is other text
        self.assertFalse(grade.without_marks('Phase trial', 'Phase 1 trial', ['1']))   # nothing may be invented
        for got, want in (('Living benefit/GMDB features(1):', 'Living benefit/GMDB features:'), ('Unsecured Notes Covenants (1)', 'Unsecured Notes Covenants'), ('EPS (1) Growth', 'EPS Growth')):
            self.assertEqual(grade.minus_marks_anywhere(got, ['(1)']), grade.norm(want))  # the space a mark leaves behind closes up (basis containment)
        for n in (50, 500, 1000, 2000):  # Codex R9-3: no recursion, whatever the length; marks at the end or in the middle; a mark that is text; a changed word
            label = ('word ' * (n // 5)).strip()
            self.assertEqual(grade.same(label + ' (1)', label, ['(1)']), (True, 'marker_in_text'), n)
            self.assertEqual(grade.same(label[:n // 2] + '(1)' + label[n // 2:], label, ['(1)']), (True, 'marker_in_text'), n)
            self.assertEqual(grade.same(label + ' 1', label + ' 1', ['1']), (True, None), n)
            self.assertFalse(grade.same(label.replace('word', 'ward', 1) + ' (1)', label, ['(1)'])[0], n)
        # basis containment and a heading printed twice above the value
        res = self.run_grader(lambda r: self.cell(r, 'l2').update(text='Free cash flow(1)'))
        self.assertEqual(self.check(res, 'pkt/T02', 'row_label')['verdict'], 'pass')

    def test_a_table_wide_title_does_not_override_a_conflicting_subgroup(self):
        # Codex round 8 (R8-1): with 'Regional results' above both groups, swapped year headings must still fail; without a swap they pass
        for with_title in (False, True):
            raw = (b'<table>' + (b'<tr><td colspan="7">Regional results</td></tr>' if with_title else b'') + b'<tr><td></td><td colspan="3">North</td><td colspan="3">South</td></tr>'
                   b'<tr><td></td><td id="a">2024</td><td id="b">2023</td><td id="c">Change</td><td id="d">2022</td><td id="e">2021</td><td id="f">Change</td></tr>'
                   b'<tr><td>Sales</td><td>10</td><td>8</td><td id="target">2</td><td>15</td><td>11</td><td>4</td></tr></table>')
            def span(text, after=None):
                a = raw.index(text, raw.index(after) if after else 0); return {'byte_start': a, 'byte_end_exclusive': a + len(text)}
            s = int(with_title); cells = [{'r': s, 'c': 1, 'cs': 3, 'text': 'North', 'anchor': span(b'North')}, {'r': s, 'c': 4, 'cs': 3, 'text': 'South', 'anchor': span(b'South')}]
            if with_title: cells.insert(0, {'r': 0, 'c': 0, 'cs': 7, 'text': 'Regional results', 'anchor': span(b'Regional results')})
            for c, (text, ident) in enumerate([(b'2024', b'a'), (b'2023', b'b'), (b'Change', b'c'), (b'2022', b'd'), (b'2021', b'e'), (b'Change', b'f')], 1):
                cells.append({'r': 1 + s, 'c': c, 'text': text.decode(), 'anchor': span(text, b'id="' + ident + b'"')})
            cells += [{'r': 2 + s, 'c': 0, 'text': 'Sales', 'anchor': span(b'Sales')}, {'r': 2 + s, 'c': 3, 'text': '2', 'anchor': span(b'2', b'id="target"')}]
            t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'2', b'id="target"'), 'table_anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)},
                 'alternatives': {}, 'excluded': set(), 'support': {'row_label': {'anchors': [span(b'Sales')]}, 'header_path': {'anchors': [span(b'North'), span(b'Change', b'id="c"')]}},
                 'fields': {'printed_value': '2', 'display_value': '2', 'row_label': 'Sales', 'header_path': ['North', 'Change'],
                            'periods': [{'role': 'value', 'parts': [{'text': '2024', 'anchor': span(b'2024')}]}, {'role': 'comparison', 'parts': [{'text': '2023', 'anchor': span(b'2023')}]}]}}
            for swap in (False, True):
                cs = [dict(c) for c in cells]
                if swap:
                    for c in cs:
                        if c['r'] == 1 + s and c['c'] in (1, 2, 4, 5): c['c'] += 3 if c['c'] < 3 else -3
                g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [{'id': 't', 'kind': 'table', 'anchor': t['table_anchor'], 'cells': sorted(cs, key=lambda c: (c['r'], c['c']))}]}, raw, 'htm')); g.grade_cell()
                self.assertEqual(next(r['verdict'] for r in g.rows if r['check'] == 'periods'), 'fail' if swap else 'pass', (with_title, swap))

    def test_struck_evidence_must_match_the_cancelled_text_exactly_in_text_units_and_in_table_cells(self):
        # Codex round 8 (R8-2): a part of the cancelled word, or extra cancelled words, change meaning; a one-cell layout table carries the strike on its cell
        for marks, want in ((['not'], 'pass'), ([], 'fail'), (['n'], 'fail'), (['no'], 'fail'), (['not a GAAP measure'], 'fail'), (['GAAP'], 'fail')):
            res = self.run_grader(lambda r: self.unit(r, 'u2').update(struck=marks))
            self.assertEqual(self.check(res, 'pkt/S01', 'printed_text')['verdict'], want, marks)
        def as_table(struck):
            def go(r):
                u = self.unit(r, 'u2'); cell = {'r': 0, 'c': 0, 'text': u['text'], 'anchor': u['anchor'], 'struck': struck}
                u.clear(); u.update(id='u2', kind='table', anchor=cell['anchor'], cells=[cell])
            return go
        self.assertEqual(self.check(self.run_grader(as_table(['not'])), 'pkt/S01', 'printed_text')['verdict'], 'pass')
        self.assertEqual(self.check(self.run_grader(as_table([])), 'pkt/S01', 'printed_text')['verdict'], 'fail')

    def test_fragments_that_are_text_units_pass_like_cell_fragments_in_every_field(self):
        # Codex round 8 (R8-3): <span>Sum</span><span>mary</span> as two or seven touching text units is faithful output for titles, units, basis, periods, lead-ins and headings
        for field, word in (('table_title', 'Summary'), ('unit_printed', 'Millions'), ('segment_or_basis', 'Adjusted'), ('periods', '2025'), ('lead_in', 'Summary'), ('section_path', 'Summary')):
            for n in (1, 2, len(word)):
                raw = ('<p><span>' + word[:2] + '</span><span>' + word[2:] + '</span></p><table><tr><td>Revenue</td><td>1234</td></tr></table>').encode()
                span = lambda text: {'byte_start': raw.index(text.encode()), 'byte_end_exclusive': raw.index(text.encode()) + len(text)}
                evidence = {'byte_start': 0, 'byte_end_exclusive': raw.index(b'<table>')}
                if n == 1: units = [{'id': 'p1', 'kind': 'heading', 'text': word, 'anchor': evidence}]
                elif n == 2: units = [{'id': f'p{i}', 'kind': 'heading', 'text': s, 'anchor': span(s)} for i, s in enumerate([word[:2], word[2:]])]
                else:
                    left, right = raw.index(word[:2].encode()), raw.index(word[2:].encode())
                    units = [{'id': f'p{i}', 'kind': 'heading', 'text': c, 'anchor': {'byte_start': left + i if i < 2 else right + i - 2, 'byte_end_exclusive': left + i + 1 if i < 2 else right + i - 1}} for i, c in enumerate(word)]
                tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table>'), 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span('Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span('1234')}]}
                value = [{'role': 'value', 'parts': [{'text': word, 'anchor': evidence}]}] if field == 'periods' else [word] if field in ('section_path', 'table_title') else word
                t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span('1234'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
                     'support': {field: {'anchors': [evidence]}}, 'fields': {'printed_value': '1234', 'display_value': '1234', field: value}}
                g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units + [tb]}, raw, 'htm')); g.grade_cell()
                self.assertEqual(next(r['verdict'] for r in g.rows if r['check'] == field), 'pass', (field, n))

    def test_a_run_in_heading_printed_in_pieces_is_found_at_its_anchor(self):
        # tool test 3 (contract exhibits): "Section 1.01 Defined Terms." runs into its paragraph; tools emit it as pieces, glued ("1.01Defined") or split by
        # a no-break space; the run-in rule reads the pieces as the source prints them and compares by the boundary rule (same rule as every other field)
        table = b'<table><tr><td>Revenue</td><td>1234</td></tr></table>'
        def graded(raw, units):
            span = lambda text: {'byte_start': raw.index(text[0] if isinstance(text, tuple) else text), 'byte_end_exclusive': raw.index(text[1] if isinstance(text, tuple) else text) + len(text[1] if isinstance(text, tuple) else text)}  # bytes, or (first, last) when tags sit between
            evidence = {'byte_start': 0, 'byte_end_exclusive': raw.index(b'<table>')}
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table>'), 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234')}]}
            t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'1234'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
                 'support': {'section_path': {'anchors': [evidence]}}, 'fields': {'printed_value': '1234', 'display_value': '1234', 'section_path': ['Section 1.01 Defined Terms.']}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [dict(u, anchor=span(u['anchor'])) for u in units] + [tb]}, raw, 'htm')); g.grade_cell()
            return next((r['verdict'], r.get('detail')) for r in g.rows if r['check'] == 'section_path')
        body = b'. As used in this Agreement, the following terms have the meanings set forth below.'
        glued = b'<p><b>Section 1.01</b><u>Defined Terms</u>' + body + b'</p>' + table   # three pieces, glued in the bytes (Docling's shape)
        self.assertEqual(graded(glued, [{'id': 'a', 'kind': 'text', 'text': 'Section 1.01', 'anchor': b'Section 1.01'}, {'id': 'b', 'kind': 'text', 'text': 'Defined Terms', 'anchor': b'Defined Terms'}, {'id': 'c', 'kind': 'text', 'text': body.decode(), 'anchor': body}]), ('pass', 'run_in'))
        self.assertEqual(graded(glued, [{'id': 'a', 'kind': 'heading', 'text': 'Section 1.01', 'anchor': b'Section 1.01'}, {'id': 'b', 'kind': 'text', 'text': 'Defined Terms' + body.decode(), 'anchor': (b'Defined Terms', body)}]), ('pass', 'run_in'))  # EdgarTools' shape
        nbsp = '<p><b>Section 1.01</b>\u00a0\u00a0<u>Defined Terms</u>'.encode() + body + b'</p>' + table   # pieces apart by no-break spaces
        self.assertEqual(graded(nbsp, [{'id': 'a', 'kind': 'heading', 'text': 'Section 1.01', 'anchor': b'Section 1.01'}, {'id': 'b', 'kind': 'text', 'text': 'Defined Terms' + body.decode(), 'anchor': (b'Defined Terms', body)}]), ('pass', 'run_in'))
        self.assertEqual(graded(glued, [{'id': 'a', 'kind': 'text', 'text': 'Section 1.02', 'anchor': b'Section 1.01'}, {'id': 'c', 'kind': 'text', 'text': 'Defined Terms' + body.decode(), 'anchor': (b'Defined Terms', body)}])[0], 'fail')  # a changed number is not the heading

    def test_another_rows_strike_does_not_fail_a_correctly_struck_label(self):
        # Codex R9-2B: the struck check reads the cells at this field's own support, never every cell of the containing table
        raw = b'<table><tr><td><s>Obsolete</s></td><td>10</td></tr><tr><td><s>Cancelled</s></td><td>20</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'cells': [
            {'r': 0, 'c': 0, 'text': 'Obsolete', 'anchor': span(b'Obsolete'), 'struck': ['Obsolete']}, {'r': 0, 'c': 1, 'text': '10', 'anchor': span(b'10')},
            {'r': 1, 'c': 0, 'text': 'Cancelled', 'anchor': span(b'Cancelled'), 'struck': ['Cancelled']}, {'r': 1, 'c': 1, 'text': '20', 'anchor': span(b'20')}]}
        t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'10'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
             'support': {'row_label': {'anchors': [span(b'Obsolete')]}}, 'fields': {'printed_value': '10', 'display_value': '10', 'row_label': '~~Obsolete~~'}}
        g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [tb]}, raw, 'htm')); g.grade_cell()
        self.assertEqual(next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'row_label'), ('pass', None))
        tb['cells'][0]['struck'] = []  # the label's own strike lost: still a failure
        g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [tb]}, raw, 'htm')); g.grade_cell()
        self.assertEqual(next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'row_label'), ('fail', 'struck'))
        t2 = dict(t, fields=dict(t['fields'], row_label='Obsolete')); tb['cells'][0]['struck'] = ['Obsolete']  # Codex R10-2: an invented cancellation changes meaning too
        g = grade.Grader(t2, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [tb]}, raw, 'htm')); g.grade_cell()
        self.assertEqual(next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'row_label'), ('fail', 'struck'))
        tb['cells'][0]['struck'] = []
        g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [tb]}, raw, 'htm')); g.grade_cell()
        self.assertEqual(next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'row_label'), ('fail', 'struck'))

    def test_the_struck_check_reads_the_occurrence_that_matched_not_every_anchor(self):
        # run 26: "EXHIBIT A" is printed plain where the path matched and again later with the A struck (a redline); the key's anchors name both
        table = b'<table><tr><td>Revenue</td><td>1234</td></tr></table>'
        raw = b'<p><b>EXHIBIT A</b></p><p>Body text of the exhibit.</p>' + table + b'<p>See <u>EXHIBIT </u><s>A</s></p>'
        span = lambda text, after=0: {'byte_start': raw.index(text, after), 'byte_end_exclusive': raw.index(text, after) + len(text)}
        first, later = span(b'EXHIBIT A'), {'byte_start': raw.index(b'<u>EXHIBIT'), 'byte_end_exclusive': raw.index(b'</s>') + 4}
        def graded(units):
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table>'), 'byte_end_exclusive': raw.index(b'</table>') + 8}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234')}]}
            t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'1234'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
                 'support': {'section_path': {'anchors': [first, later]}}, 'fields': {'printed_value': '1234', 'display_value': '1234', 'section_path': ['EXHIBIT A']}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units + [tb]}, raw, 'htm')); g.grade_cell()
            return next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'section_path')
        heading = {'id': 'h', 'kind': 'heading', 'text': 'EXHIBIT A', 'anchor': first}
        later_units = [{'id': 'x', 'kind': 'text', 'text': 'See EXHIBIT', 'anchor': {'byte_start': raw.index(b'See'), 'byte_end_exclusive': raw.index(b'</u>')}}, {'id': 'y', 'kind': 'text', 'text': 'A', 'anchor': span(b'A', raw.index(b'<s>')), 'struck': ['A']}]
        self.assertEqual(graded([heading] + later_units), ('pass', None))
        self.assertEqual(graded([dict(heading, struck=['A'])] + later_units), ('fail', 'struck'))  # the strike at the matched heading itself is invented

    def test_a_lead_in_spread_over_pieces_keeps_its_struck_word_in_the_check(self):
        # run 27: the struck word of a lead-in sits in a middle piece; the struck check must read every piece the match used, not the last one
        raw = b'<p><span>Rates apply to</span> <s>Eurocurrency</s> <span>Term loans and more words here.</span></p><table><tr><td>Revenue</td><td>1234</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        for struck, want in ((['Eurocurrency'], 'pass'), ([], 'fail')):
            units = [{'id': 'a', 'kind': 'text', 'text': 'Rates apply to', 'anchor': span(b'Rates apply to')}, {'id': 'b', 'kind': 'text', 'text': 'Eurocurrency', 'anchor': span(b'Eurocurrency'), 'struck': struck}, {'id': 'c', 'kind': 'text', 'text': 'Term loans and more words here.', 'anchor': span(b'Term loans and more words here.')}]
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table>'), 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234')}]}
            t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'1234'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
                 'support': {'lead_in': {'anchors': [{'byte_start': raw.index(b'<p>'), 'byte_end_exclusive': raw.index(b'</p>')}]}}, 'fields': {'printed_value': '1234', 'display_value': '1234', 'lead_in': 'Rates apply to ~~Eurocurrency~~ Term loans and more words here.'}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units + [tb]}, raw, 'htm')); g.grade_cell()
            self.assertEqual(next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'lead_in'), (want, None if want == 'pass' else 'struck'), struck)

    def test_a_table_whose_span_covers_a_block_but_whose_cells_lie_elsewhere_does_not_carry_it(self):
        # run 28: EdgarTools flattens a nested table into one table unit whose span covers a footnote paragraph; the paragraph's own unit matched the key exactly,
        # yet every cell of that table was read into the block and the block failed with a high word error rate
        raw = b'<table><tr><td>Revenue</td><td>1234</td></tr></table><p>(1) Balances are translated at the period-end rate.</p><table><tr><td>Costs</td><td>99</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        note = span(b'(1) Balances are translated at the period-end rate.')
        big = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234')}, {'r': 1, 'c': 0, 'text': 'Costs', 'anchor': span(b'Costs')}, {'r': 1, 'c': 1, 'text': '99', 'anchor': span(b'99')}]}
        para = {'id': 'p', 'kind': 'text', 'text': '(1) Balances are translated at the period-end rate.', 'anchor': note}
        t = {'key_id': 'syn/S2', 'file_id': 'syn/f.htm', 'format': 'structure/htm', 'type': 'structure', 'split': 'development', 'anchor': {'byte_start': note['byte_start'] - 3, 'byte_end_exclusive': note['byte_end_exclusive'] + 4}, 'alternatives': {}, 'excluded': set(), 'support': {},
             'fields': {'printed_text': '(1) Balances are translated at the period-end rate.', 'kind': 'paragraph', 'visible': True}}
        g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [big, para]}, raw, 'htm')); g.grade_structure()
        self.assertEqual(next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'printed_text'), ('pass', None))

    def test_an_invented_cancellation_fails_a_plain_passage_and_a_plain_label(self):
        # Codex R10-2: the key marks nothing struck; a route that cancels "not" changed the meaning as surely as dropping a strike (the label case is in the strike-scope test)
        raw = b'<p>The company may not borrow.</p><table><tr><td>Revenue</td><td>1234</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        for struck, want in (([], 'pass'), (['not'], 'fail')):
            unit = {'id': 'p', 'kind': 'paragraph', 'text': 'The company may not borrow.', 'anchor': span(b'The company may not borrow.'), 'struck': struck}
            t = {'key_id': 'syn/S1', 'file_id': 'syn/f.htm', 'format': 'structure/htm', 'type': 'structure', 'split': 'development', 'anchor': span(b'The company may not borrow.'), 'alternatives': {}, 'excluded': set(), 'support': {},
                 'fields': {'printed_text': 'The company may not borrow.', 'kind': 'paragraph', 'visible': True}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [unit]}, raw, 'htm')); g.grade_structure()
            self.assertEqual(next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'printed_text'), (want, None if want == 'pass' else 'struck'), struck)

    def test_a_row_label_split_where_the_page_alone_could_show_the_space_is_unresolved(self):
        # Codex R10-4: the same unresolved-join rule for the row label (touching "Cash" + "flow" under a key "Cash flow"; "Cashflow" passes; a changed word fails)
        for key, verdict in (('Cashflow', 'pass'), ('Cash flow', 'unresolved'), ('Wrong flow', 'fail')):
            raw = b'<table><tr><td><span>Cash</span><span>flow</span></td><td>10</td></tr></table>'
            span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Cash', 'anchor': span(b'Cash')}, {'r': 0, 'c': 0, 'text': 'flow', 'anchor': span(b'flow')}, {'r': 0, 'c': 1, 'text': '10', 'anchor': span(b'10')}]}
            t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'10'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
                 'support': {'row_label': {'anchors': [{'byte_start': raw.index(b'Cash'), 'byte_end_exclusive': raw.index(b'flow') + 4}]}}, 'fields': {'printed_value': '10', 'display_value': '10', 'row_label': key}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [tb]}, raw, 'htm')); g.grade_cell()
            self.assertEqual(next(r['verdict'] for r in g.rows if r['check'] == 'row_label'), verdict, key)

    def test_a_two_line_heading_whose_second_line_says_continued_is_read_as_pieces(self):
        # E2 inside E12: the window that reads a heading's pieces measures them without "(continued)", so the piece carrying it is not skipped
        raw = b'<p>Consolidated</p><p>Summary (continued)</p><table><tr><td>Revenue</td><td>1234</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        units = [{'id': 'p0', 'kind': 'heading', 'text': 'Consolidated', 'anchor': span(b'Consolidated')}, {'id': 'p1', 'kind': 'heading', 'text': 'Summary (continued)', 'anchor': span(b'Summary (continued)')}]
        tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table>'), 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234')}]}
        evidence = {'byte_start': 0, 'byte_end_exclusive': raw.index(b'<table>')}
        t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'1234'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
             'support': {'section_path': {'anchors': [evidence]}}, 'fields': {'printed_value': '1234', 'display_value': '1234', 'section_path': ['Consolidated Summary']}}
        g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units + [tb]}, raw, 'htm')); g.grade_cell()
        self.assertEqual([(r['check'], r['verdict']) for r in g.rows if r['check'] in ('section_path', 'heading_recognised')], [('heading_recognised', 'pass'), ('section_path', 'pass')])

    def test_touching_pieces_are_read_as_the_source_prints_them_and_a_page_only_space_is_unresolved(self):
        # Codex R9-1: joins come from the output's mapping and the source alone, never from the key. Touching pieces read as one; a digit-letter or symbol join
        # the key spaces is reflow (boundary rule); two words the key spaces but the bytes glue cannot be settled from the output: unresolved, never pass or fail;
        # an empty picture unit never swallows the heading after it
        def graded(raw, units, field, value):
            span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
            evidence = {'byte_start': 0, 'byte_end_exclusive': raw.index(b'<table>')}
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table>'), 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234')}]}
            t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'1234'), 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
                 'support': {field: {'anchors': [evidence]}}, 'fields': {'printed_value': '1234', 'display_value': '1234', field: value}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [dict(u, anchor=span(u['anchor'])) for u in units] + [tb]}, raw, 'htm')); g.grade_cell()
            return {r['check']: r['verdict'] for r in g.rows}
        table = b'<table><tr><td>Revenue</td><td>1234</td></tr></table>'
        rows = graded(b'<p><span>Section 1.01</span><span>Defined Terms</span></p>' + table, [{'id': 'h1', 'kind': 'heading', 'text': 'Section 1.01', 'anchor': b'Section 1.01'}, {'id': 'h2', 'kind': 'heading', 'text': 'Defined Terms', 'anchor': b'Defined Terms'}], 'section_path', ['Section 1.01 Defined Terms'])
        self.assertEqual((rows['section_path'], rows['heading_recognised']), ('pass', 'pass'))
        rows = graded(b'<p><img src="x.png"><span>Financial Trends</span></p>' + table, [{'id': 'i', 'kind': 'image', 'text': '', 'anchor': b'<img src="x.png">'}, {'id': 'h', 'kind': 'heading', 'text': 'Financial Trends', 'anchor': b'Financial Trends'}], 'section_path', ['Financial Trends'])
        self.assertEqual((rows['section_path'], rows['heading_recognised']), ('pass', 'pass'))
        rows = graded('<p><span>•</span><span>depreciation and amortization;</span></p>'.encode() + table, [{'id': 'b', 'kind': 'text', 'text': '•', 'anchor': '•'.encode()}, {'id': 'w', 'kind': 'text', 'text': 'depreciation and amortization;', 'anchor': b'depreciation and amortization;'}], 'segment_or_basis', ['• depreciation and amortization;'])
        self.assertEqual(rows['segment_or_basis'], 'pass')
        rows = graded(b'<p><span>Sum</span><span>mary</span></p>' + table, [{'id': 'h1', 'kind': 'heading', 'text': 'Sum', 'anchor': b'Sum'}, {'id': 'h2', 'kind': 'heading', 'text': 'mary', 'anchor': b'mary'}], 'section_path', ['Summary'])
        self.assertEqual((rows['section_path'], rows['heading_recognised']), ('pass', 'pass'))  # a within-word split the key reads glued still is (E12)
        rows = graded(b'<p><span>written (the "</span><span>Effective Date</span><span>") when:</span></p>' + table, [{'id': 'a', 'kind': 'text', 'text': 'written (the "', 'anchor': b'written (the "'}, {'id': 'b', 'kind': 'text', 'text': 'Effective Date', 'anchor': b'Effective Date'}, {'id': 'c', 'kind': 'text', 'text': '") when:', 'anchor': b'") when:'}], 'segment_or_basis', ['(the "Effective Date")'])
        self.assertEqual(rows['segment_or_basis'], 'pass')  # the key phrase ends two characters into the last piece: the glued reading contains it
        for key, verdict in (('Cashflow', 'pass'), ('Cash flow', 'unresolved')):  # the same output reads 'Cashflow' whatever the key says; only the verdict depends on the key
            rows = graded(b'<p><span>Cash</span><span>flow</span></p>' + table, [{'id': 'a', 'kind': 'heading', 'text': 'Cash', 'anchor': b'Cash'}, {'id': 'b', 'kind': 'heading', 'text': 'flow', 'anchor': b'flow'}], 'section_path', [key])
            self.assertEqual(rows['section_path'], verdict, key)
        rows = graded(b'<p><span>Cash</span> <span>flow</span></p>' + table, [{'id': 'a', 'kind': 'heading', 'text': 'Cash', 'anchor': b'Cash'}, {'id': 'b', 'kind': 'heading', 'text': 'flow', 'anchor': b'flow'}], 'section_path', ['Cashflow'])
        self.assertEqual(rows['section_path'], 'fail')  # a real space in the source: the output's two words cannot spell the key's one
        for key, verdict in (('Cashflow', 'pass'), ('Cash flow', 'unresolved')):  # Codex R10-4: the same rule for a run-in heading that continues into its paragraph
            rows = graded(b'<p><span>Cash</span><span>flow</span> is defined as the net amount of cash generated in the period.</p>' + table, [{'id': 'a', 'kind': 'text', 'text': 'Cash', 'anchor': b'Cash'}, {'id': 'b', 'kind': 'text', 'text': 'flow', 'anchor': b'flow'}, {'id': 'c', 'kind': 'text', 'text': ' is defined as the net amount of cash generated in the period.', 'anchor': b' is defined as the net amount of cash generated in the period.'}], 'section_path', [key])
            self.assertEqual(rows['section_path'], verdict, key)

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
                pieces.append([n, n + len(grade.squash(part))]); n += len(grade.squash(part)); cursor = a + len(part)  # blocks are measured on the squashed text
            u = {'id': 'u', 'kind': 'text', 'text': text, 'anchor': anchors, 'pieces': pieces, 'link_flag': 'pieced', 'inserted_chars': 0}
            g = grade.gates_for_file(grade.RouteFile({'file_id': 'x/p.htm', 'units': [{'id': 'l', 'kind': 'text', 'text': 'Lead.', 'anchor': {'byte_start': 3, 'byte_end_exclusive': 8}}, u]}, raw, 'htm'), 'OK')
            return g['dishonest'], g['boundary']
        self.assertEqual(gate('Revenue increased.', 'Revenue increased.', ('Revenue', 'increased.')), (0, 0))   # control: the space survives
        self.assertEqual(gate('Revenue increased.', 'Revenueincreased.', ('Revenue', 'increased.')), (0, 1))    # word boundary deleted at the join
        self.assertEqual(gate('<span>12</span><span>34</span>', '1234', ('12', '34')), (0, 0))               # control: adjacent fragments of one number
        self.assertEqual(gate('<span>12</span><span>34</span>', '12 34', ('12', '34')), (0, 1))              # number boundary inserted at the join
        self.assertEqual(gate('Alpha Beta', 'Beta Alpha', ('Beta', 'Alpha'), reverse=True), (1, 0))          # source order reversed: not an honest mapping
        # Codex round 6: the space may sit inside a span; numeric punctuation is a number boundary; a symbol is not
        for parts, text, want in ((('Revenue', ' increased.'), 'Revenue increased.', 0), (('Revenue', ' increased.'), 'Revenueincreased.', 1),
                                  (('Revenue ', 'increased.'), 'Revenue increased.', 0), (('Revenue ', 'increased.'), 'Revenueincreased.', 1),
                                  (('12.', '34'), '12.34', 0), (('12.', '34'), '12. 34', 1), (('1,', '234'), '1,234', 0), (('1,', '234'), '1, 234', 1), (('$', '1234'), '$ 1234', 0)):
            self.assertEqual(gate(''.join(parts), text, parts), (0, want), (parts, text))

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
        # Codex round 6: an unproved join never hides a proven wrong row or a reversed endpoint order
        def moved(case):
            partner, value = box(20, 40), box(70, 90); r, c = (1, 1) if case == 'row' else (0, 4)
            cells = [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': box(0, 15)}, {'r': r, 'c': c, 'text': '12', 'anchor': box(20, 30)}, {'r': r, 'c': c, 'text': '34', 'anchor': box(30, 40)},
                     {'r': 0, 'c': 3, 'text': '1500', 'anchor': value}]
            table = {'id': 'tb', 'kind': 'table', 'anchor': {'page': 1, 'region': [0, 0, 100, 30]}, 'cells': cells}
            t = {'key_id': 'syn/R1', 'file_id': 'syn/f.pdf', 'format': 'cell/pdf', 'type': 'cell', 'split': 'development', 'anchor': value, 'table_anchor': table['anchor'],
                 'alternatives': {}, 'excluded': set(), 'support': {}, 'fields': {'printed_value': '1500', 'display_value': '1500', 'row_label': 'Revenue',
                 'range': {'kind': 'interval', 'role': 'high', 'partner': {'printed_value': '1234', 'anchor': partner}, 'evidence': []}}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.pdf', 'units': [table]}, None, 'pdf')); g.grade_cell()
            return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'range')
        self.assertEqual(moved('row'), ('fail', 'row')); self.assertEqual(moved('order'), ('fail', 'order'))

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
            nine = self.sub('v1', '9'); cells[i:i + 1] = [dict(v, text='76', anchor=self.sub('v1', '76')), dict(v, text='9', anchor=dict(nine, byte_start=nine['byte_start'] + 1, byte_end_exclusive=nine['byte_end_exclusive'] + 1))]  # one byte later: the '9' itself lies between the pieces (an empty span would be no position at all)
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

    def test_an_xml_unit_may_be_the_elements_own_name_and_a_title_element_is_text(self):
        # XML route: the key may name the unit as the element itself (percentOfClass) by anchoring its tag; a printed text (a security title) still counts;
        # an XML <title> is an ordinary element, never the HTML document title the scanner skips
        xml = b'<r xmlns="urn:main"><p><percentOfClass>2.4</percentOfClass><title>Chair</title></p></r>'
        i = xml.index(b'>2.4<') + 1; a = {'byte_start': i, 'byte_end_exclusive': i + 3}
        units = [{'id': 'x', 'kind': 'field', 'anchor': {'byte_start': xml.index(b'<percentOfClass>'), 'byte_end_exclusive': i + 3}, 'name': '{urn:main}percentOfClass', 'path': ['{urn:main}r', '{urn:main}p'], 'text': '2.4', 'group': {'index': 1, 'count': 1}},
                 {'id': 'y', 'kind': 'field', 'anchor': {'byte_start': xml.index(b'<title>'), 'byte_end_exclusive': xml.index(b'</title>')}, 'name': '{urn:main}title', 'path': ['{urn:main}r', '{urn:main}p'], 'text': 'Chair', 'group': {'index': 1, 'count': 1}}]
        at = lambda b: {'byte_start': xml.index(b), 'byte_end_exclusive': xml.index(b) + len(b)}
        for unit, declared, want in (('percentOfClass', at(b'<percentOfClass>'), 'pass'), ('Chair', at(b'Chair'), 'pass'), ('shares', at(b'Chair'), 'fail'), ('percentOfClass', None, 'unresolved')):  # Codex R13 C3: the key's declared place decides; none declared is no association
            t = {'key_id': 'syn/X2', 'file_id': 'syn/form.xml', 'type': 'cell', 'format': 'cell/xml', 'split': 'development', 'anchor': a, 'table_anchor': a, 'alternatives': {}, 'excluded': set(),
                 'support': {'unit_printed': {'anchors': [declared]}} if declared else {},
                 'fields': {'printed_value': '2.4', 'display_value': '2.4', 'row_label': 'percentOfClass', 'header_path': ['{urn:main}r', '{urn:main}p'], 'row_context': [], 'periods': [], 'unit_printed': unit}}
            g = grade.Grader(t, grade.RouteFile({'file_id': t['file_id'], 'units': units}, xml, 'xml')); g.grade_cell()
            self.assertEqual(next(x['verdict'] for x in g.rows if x['check'] == 'unit_printed'), want, unit)
        rf = grade.RouteFile({'file_id': 'syn/form.xml', 'units': units}, xml, 'xml'); self.assertIn('Chair', rf.vis.text)
        self.assertEqual(grade.gates_for_file(rf, 'OK')['dishonest'], 0)
        cd = b'<r><job><![CDATA[Manager of A > B & C]]></job></r>'; rf = grade.RouteFile({'file_id': 'syn/c.xml', 'units': [{'id': 'j', 'kind': 'field', 'anchor': {'byte_start': 3, 'byte_end_exclusive': cd.index(b'</job>')}, 'name': 'job', 'path': ['r'], 'text': 'Manager of A > B & C', 'group': {'index': 1, 'count': 1}}]}, cd, 'xml')
        self.assertEqual((rf.vis.text.strip(), grade.gates_for_file(rf, 'OK')['dishonest']), ('Manager of A > B & C', 0))  # a CDATA section is text in XML

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
        self.assertEqual((res['gates']['honest_anchors']['dishonest'], res['gates']['honest_anchors']['bounds_inconsistent']), ({}, {}))  # consistent with the route's own sizes: uncertified, not dishonest
        # Codex R15-3: a box beyond the route's own page, or with no area, is a position that cannot be true — it locates nothing, supplies nothing (the title it carried is now missing), counts dishonest and stays visible as an impossible box
        for place in ({'region': [-100, -100, 99999, 99999]}, {'region': [100, 50, 100, 70]}, {'region': [100, 50, 500, 793]}, {'page': 9}):  # negative, no area, beyond the page, a page the route never declared
            res = self.run_grader(lambda r: r[PDF_ID]['units'][0]['anchor'].update(place))
            self.assertEqual((res['gates']['honest_anchors']['dishonest'], res['gates']['honest_anchors']['bounds_inconsistent']), ({PDF_ID: 1}, {PDF_ID: 1}), place)
            self.assertEqual((self.check(res, 'pkt/P01', 'table_title')['verdict'], self.check(res, 'pkt/P01', 'table_title')['reason']), ('fail', 'missing'), place)

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
        res = self.run_grader(lambda r: r[XML_ID]['units'][4].update(group={'index': 1, 'count': 2, 'at': PERSON_AT[0]}))
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

    # ---- Codex round 11: the strike check over the field's own run, every matched carrier, the value's own cells; XML instances; word error rate
    def synthetic_cell(self, raw, units, fields, support, tb=None, value=b'1234'):
        """One synthetic cell target over `raw`: the check rows of a grader run as {check: (verdict, reason)}."""
        span = lambda text, after=0: {'byte_start': raw.index(text, after), 'byte_end_exclusive': raw.index(text, after) + len(text)}
        tb = tb or {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table>'), 'byte_end_exclusive': raw.index(b'</table>') + 8},
                    'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 0, 'c': 1, 'text': value.decode(), 'anchor': span(value)}]}
        t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(value), 'table_anchor': tb['anchor'],
             'alternatives': {}, 'excluded': set(), 'support': support, 'fields': {'printed_value': value.decode(), 'display_value': value.decode(), **fields}}
        g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units + [tb]}, raw, 'htm')); g.grade_cell()
        return {r['check']: (r['verdict'], r.get('reason')) for r in g.rows}

    def test_the_value_cells_own_cancellation_is_checked_both_ways(self):
        # Codex R11-2: value() sits outside field(); an invented cancellation of the number passed, and so did a lost one
        raw = b'<table><tr><td>Revenue</td><td>1234</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        def value_row(printed, struck):
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(b'Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234'), 'struck': struck}]}
            return self.synthetic_cell(raw, [], {'printed_value': printed, 'display_value': printed}, {}, tb)['value']
        self.assertEqual(value_row('1234', []), ('pass', None))
        self.assertEqual(value_row('1234', ['1234']), ('fail', 'struck'))  # invented
        self.assertEqual(value_row('~~1234~~', ['1234']), ('pass', None))  # faithful
        self.assertEqual(value_row('~~1234~~', []), ('fail', 'struck'))  # lost

    def test_a_strike_crossing_the_fields_boundary_is_seen_at_the_occurrence_the_key_names(self):
        # Codex R11-3: "Ownership remains. Ownership ends." — the heading is the first "Ownership"; a longer strike crossing it was dropped by the text filter
        raw = b'<p>Ownership remains. Ownership ends.</p><table><tr><td>Revenue</td><td>1234</td></tr></table>'
        span = lambda text, after=0: {'byte_start': raw.index(text, after), 'byte_end_exclusive': raw.index(text, after) + len(text)}
        first, second = span(b'Ownership'), span(b'Ownership', 10)
        def path_row(anchors, struck, raw=raw):
            unit = {'id': 'h', 'kind': 'text', 'text': 'Ownership remains. Ownership ends.', 'anchor': {'byte_start': raw.index(b'Ownership'), 'byte_end_exclusive': raw.index(b'</p>')}, 'struck': struck}
            return self.synthetic_cell(raw, [unit], {'section_path': ['Ownership']}, {'section_path': {'anchors': anchors}})['section_path']
        self.assertEqual(path_row([first], []), ('pass', None))
        self.assertEqual(path_row([first], ['Ownership remains.']), ('fail', 'struck'))  # crosses the heading's boundary: the heading's own word is cancelled
        self.assertEqual(path_row([first], ['Ownership']), ('fail', 'struck'))  # the source strikes neither occurrence: the claim lands on the heading
        self.assertEqual(path_row([second], ['Ownership remains.']), ('pass', None))  # the heading is the second occurrence; the strike lies before it
        self.assertEqual(path_row([first, second], ['Ownership remains.']), ('unresolved', 'struck'))  # the key's search pieces name both: the occurrence stays open
        struck_second = raw.replace(b'Ownership ends', b'<s>Ownership</s> ends')  # the source strikes the second occurrence: a claim of "Ownership" is that one
        self.assertEqual(path_row([span(b'Ownership')], ['Ownership'], struck_second), ('pass', None))

    def test_qualifier_period_note_and_range_evidence_carry_their_own_strikes_to_the_check(self):
        # Codex R11-4: every carrier a match used reaches the strike check — the middle piece of a joined phrase, a period part in a paragraph, a note outside the table, a range partner
        table = b'<table><tr><td>Revenue</td><td>1234</td></tr></table>'
        span = lambda raw, text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        for source_struck, key, struck, want in ((True, 'These ~~old~~ terms', ['old'], 'pass'), (True, 'These ~~old~~ terms', [], 'fail'), (False, 'These old terms', ['old'], 'fail'), (False, 'These old terms', [], 'pass')):
            raw = (b'<p><span>These</span> <s>old</s> <span>terms</span></p>' if source_struck else b'<p><span>These</span> <span>old</span> <span>terms</span></p>') + table
            units = [{'id': str(i), 'kind': 'text', 'text': w, 'anchor': span(raw, w.encode()), 'struck': struck if w == 'old' else []} for i, w in enumerate(['These', 'old', 'terms'])]
            rows = self.synthetic_cell(raw, units, {'segment_or_basis': [key]}, {'segment_or_basis': {'anchors': [{'byte_start': 0, 'byte_end_exclusive': raw.index(b'<table>')}]}})
            self.assertEqual(rows['segment_or_basis'], (want, None if want == 'pass' else 'struck'), (source_struck, key, struck))
        for source_struck, key, struck, want in ((True, 'Period ended ~~2025~~', ['2025'], 'pass'), (True, 'Period ended ~~2025~~', [], 'fail'), (False, 'Period ended 2025', ['2025'], 'fail')):
            text = b'Period ended <s>2025</s>' if source_struck else b'Period ended 2025'; raw = b'<p>' + text + b'</p>' + table
            unit = {'id': 'p', 'kind': 'text', 'text': 'Period ended 2025', 'anchor': span(raw, text), 'struck': struck}
            rows = self.synthetic_cell(raw, [unit], {'periods': [{'parts': [{'text': key, 'anchor': span(raw, text)}], 'role': 'value'}]}, {})
            self.assertEqual(rows['periods'], (want, None if want == 'pass' else 'struck'), (source_struck, key, struck))
        for source_struck, key, struck, want in ((True, 'a These ~~old~~ terms apply.', ['old'], 'pass'), (True, 'a These ~~old~~ terms apply.', [], 'fail'), (False, 'a These old terms apply.', ['old'], 'fail')):
            note = b'a These <s>old</s> terms apply.' if source_struck else b'a These old terms apply.'
            raw = b'<table><tr><td>Revenue</td><td>1234<sup>a</sup></td></tr></table><p>' + note + b'</p>'
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': raw.index(b'</table>') + 8}, 'notes': ['n'],
                  'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(raw, b'Revenue')}, {'r': 0, 'c': 1, 'text': '1234', 'markers': ['a'], 'anchor': span(raw, b'1234<sup>a</sup>')}]}
            side = {'id': 'n', 'kind': 'footnote', 'marker': 'a', 'text': 'a These old terms apply.', 'anchor': span(raw, note), 'struck': struck}
            rows = self.synthetic_cell(raw, [side], {'footnote_markers': [{'marker_text': 'a', 'anchor': span(raw, b'<sup>a</sup>'), 'note_text': key, 'note_anchor': span(raw, note)}]}, {}, tb)
            self.assertEqual(rows['footnote_markers'], (want, None if want == 'pass' else 'struck'), (source_struck, key, struck))
        raw = b'<table><tr><td>Revenue</td><td>10</td><td>to</td><td>20</td></tr></table>'
        for struck, want in (([], ('pass', None)), (['20'], ('fail', 'struck'))):
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': span(raw, b'Revenue')}, {'r': 0, 'c': 1, 'text': '10', 'anchor': span(raw, b'10')},
                  {'r': 0, 'c': 2, 'text': 'to', 'anchor': span(raw, b'to')}, {'r': 0, 'c': 3, 'text': '20', 'anchor': span(raw, b'20'), 'struck': struck}]}
            rows = self.synthetic_cell(raw, [], {'range': {'partner': {'printed_value': '20', 'anchor': span(raw, b'20')}, 'evidence': [{'text': 'to', 'anchor': span(raw, b'to')}]}}, {}, tb, value=b'10')
            self.assertEqual(rows['range'], want, struck)

    def test_xml_context_comes_from_the_same_instance_not_from_a_namesake_elsewhere(self):
        # Codex N2: two persons, each with holdings; the first holding of each had the same names-only path and "1 of 2", so the other person's "Common" rescued a wrong name
        from benchmarks.prepare.grader.adapters import xml_fields as xf
        raw = b'<r><person><holdings><holding><name>Common</name><qty>10</qty></holding><holding><name>Preferred</name><qty>20</qty></holding></holdings></person><person><holdings><holding><name>Common</name><qty>30</qty></holding></holdings></person></r>'
        def ctx_row(mutate):
            units = xf.units_of(raw); mutate(units); a = raw.index(b'10')
            t = {'key_id': 'syn/X1', 'file_id': 'syn/a.xml', 'format': 'cell/xml', 'type': 'cell', 'split': 'development', 'anchor': {'byte_start': a, 'byte_end_exclusive': a + 2}, 'alternatives': {}, 'excluded': set(), 'support': {},
                 'fields': {'printed_value': '10', 'display_value': '10', 'row_label': 'qty', 'header_path': ['r', 'person', 'holdings', 'holding'], 'row_context': [{'header': 'position', 'text': '1 of 2'}, {'header': 'name', 'text': 'Common'}]}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/a.xml', 'units': units}, raw, 'xml')); g.grade_cell()
            return {r['check']: (r['verdict'], r.get('reason')) for r in g.rows}
        rows = ctx_row(lambda u: None); self.assertEqual((rows['value'], rows['row_label'], rows['header_path'], rows['row_context']), (('pass', None), ('pass', None), ('pass', None), ('pass', None)))
        self.assertEqual(ctx_row(lambda u: u[0].update(text='Wrong'))['row_context'], ('fail', 'group'))  # the other person's first holding is also "Common": not this instance's

    def test_what_a_route_declares_unread_travels_with_the_file_facts(self):
        # Codex N2: attribute values the XML route does not read are stated, not silent — the grader carries the route's own statement per file
        res = self.run_grader()
        self.assertEqual(res['files'][XML_ID]['not_read'], {'attribute_values': 2}); self.assertIsNone(res['files'][HTM_ID]['not_read'])

    def test_an_xml_unit_comes_from_its_declared_place_not_from_a_namesake_or_a_neighbour(self):
        # Codex R12-5 and R13 C3: the key declares the unit's source place; the field read there must carry the word. The other holding's "shares", a unique
        # unrelated branch, a comment of the same holding and a word with no declared place cannot stand in (a word of this holding alone is unresolved, never a pass)
        from benchmarks.prepare.grader.adapters import xml_fields as xf
        raw = b'<r><title>Common</title><holding><qty>10</qty><unit>shares</unit><comment>No shares were sold</comment></holding><holding><qty>20</qty><unit>shares</unit></holding><fees><description>shares</description></fees></r>'
        at = lambda b: {'byte_start': raw.index(b), 'byte_end_exclusive': raw.index(b) + len(b)}
        def unit_row(unit, declared=None, drop=False, corrupt=False):
            units = [u for u in xf.units_of(raw) if not (drop and u['name'] == 'unit' and u['group']['index'] == 1)]; a = raw.index(b'10')
            if corrupt:  # the first holding's fields that print the word (its unit, its comment) at no true position (Codex R15-3)
                for u in units:
                    if u['group']['index'] == 1 and u['name'] in ('unit', 'comment'): u['anchor'] = {}
            t = {'key_id': 'syn/X1', 'file_id': 'syn/a.xml', 'format': 'cell/xml', 'type': 'cell', 'split': 'development', 'anchor': {'byte_start': a, 'byte_end_exclusive': a + 2}, 'alternatives': {}, 'excluded': set(),
                 'support': {'unit_printed': {'anchors': [declared]}} if declared else {}, 'fields': {'printed_value': '10', 'display_value': '10', 'row_label': 'qty', 'unit_printed': unit}}
            grader = grade.Grader(t, grade.RouteFile({'file_id': 'syn/a.xml', 'units': units}, raw, 'xml')); grader.grade_cell()
            return next((r['verdict'], r.get('reason')) for r in grader.rows if r['check'] == 'unit_printed')
        self.assertEqual(unit_row('shares', at(b'<unit>shares</unit>')), ('pass', None))  # the first holding's own unit, where the key says
        self.assertEqual(unit_row('shares', at(b'<unit>shares</unit>'), drop=True), ('fail', 'missing'))  # removed: the second holding's, the fee description's and the comment's "shares" do not stand in
        self.assertEqual(unit_row('units', at(b'<unit>shares</unit>')), ('fail', 'text'))  # the declared place holds another word
        self.assertEqual(unit_row('share', at(b'<unit>shares</unit>')), ('fail', 'text'))  # Codex R15-1 class: a unit is carried as a whole word, never as the start of a longer one
        self.assertEqual(unit_row('Common', at(b'Common')), ('pass', None))  # the title's place declared: the document's shared context
        self.assertEqual(unit_row('shares'), ('unresolved', 'support'))  # no declared place: a word of this holding proves no association with the value
        self.assertEqual(unit_row('shares', corrupt=True), ('fail', 'missing'))  # the holding's own unit field has no true position: it proves nothing, not even nearness
        self.assertEqual(unit_row('Common'), ('fail', 'missing'))  # no declared place and not in this holding

    def test_a_strike_over_a_marked_label_is_judged_on_the_labels_own_characters(self):
        # Codex R12-7: the label prints "Total(1) revenue" (the record's own mark set aside when matching); an invented strike over the whole label slipped past the text fallback
        raw = b'<table><tr><td>Total<sup>(1)</sup> revenue</td><td>1234</td></tr></table><p>(1) a note</p>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        def label_row(key_label, struck):
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': raw.index(b'</table>') + 8}, 'cells': [{'r': 0, 'c': 0, 'text': 'Total(1) revenue', 'anchor': span(b'Total<sup>(1)</sup> revenue'), 'struck': struck}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234')}]}
            rows = self.synthetic_cell(raw, [], {'row_label': key_label, 'footnote_markers': [{'marker_text': '(1)', 'anchor': span(b'<sup>(1)</sup>'), 'note_text': '(1) a note', 'note_anchor': span(b'(1) a note')}]}, {'row_label': {'anchors': [span(b'Total<sup>(1)</sup> revenue')]}}, tb)
            return rows['row_label']
        self.assertEqual(label_row('Total revenue', []), ('pass', None))
        self.assertEqual(label_row('Total revenue', ['Total(1) revenue']), ('fail', 'struck'))  # invented
        self.assertEqual(label_row('~~Total~~ revenue', ['Total']), ('pass', None))  # faithful
        self.assertEqual(label_row('~~Total~~ revenue', []), ('fail', 'struck'))  # lost

    def test_a_paragraph_read_whole_across_a_page_break_carries_the_block_on_its_page(self):
        # owner decision (e), 2026-10-04: a genuinely continuous paragraph is accepted when the target text is preserved in order and mapped to the correct source page
        block_row = self.block_row
        across = {'id': 'p', 'kind': 'text', 'text': 'End of two. Start of three. More words.', 'anchor': [{'page': 2, 'region': [0, 700, 100, 792], 'charspan': [0, 11]}, {'page': 3, 'region': [0, 0, 100, 20], 'charspan': [12, 39]}]}
        self.assertEqual(block_row(across), ('pass', None, {'continued': True}))  # the block is the part of the paragraph the route maps to page 3
        self.assertEqual(block_row(dict(across, text='End of two. More words. Start of three.'))[:2], ('fail', 'text'))  # not in order
        self.assertEqual(block_row(across, want='End of two.')[:2], ('fail', 'page'))  # Codex R13 C2: the words the key wants on page 3 are mapped to page 2 — a contradiction, named as such
        unmapped = lambda spans_: [{k: v for k, v in a.items() if k != 'charspan'} for a in spans_]
        self.assertEqual(block_row(dict(across, anchor=unmapped(across['anchor'])))[:2], ('unresolved', 'page_map'))  # pages listed, no character mapping: which page holds the words is unknown
        self.assertEqual(block_row(dict(across, anchor=unmapped(across['anchor'])), want='End of two. Start of three. More words.')[:2], ('unresolved', 'page_map'))  # even when the whole text is the key's: the mapping comes before any acceptance (Codex R14-1)
        self.assertEqual(block_row(dict(across, anchor=[across['anchor'][0], dict(across['anchor'][1], charspan=[12, 99])]))[:2], ('unresolved', 'page_map'))  # a span outside the text maps nothing
        self.assertEqual(block_row(dict(across, anchor={'page': 3, 'region': [0, 0, 100, 20]}))[:2], ('fail', 'text'))  # one page only: extra text is a boundary fault, as before
        exact = dict(across, text='Start of three. More words.', anchor=[{'page': 2, 'region': [0, 700, 100, 792], 'charspan': [0, 26]}, {'page': 3, 'region': [0, 0, 100, 20], 'charspan': [26, 27]}])
        self.assertEqual(block_row(exact)[:2], ('fail', 'page'))  # Codex R14-1: the text is exactly the key's, but the route maps all of it except the final period to page 2
        two = dict(across, text='Other. Wrong. Start of three. More words.', anchor=[{'page': 2, 'region': [0, 700, 100, 792], 'charspan': [0, 6]}, {'page': 3, 'region': [0, 0, 100, 20], 'charspan': [7, 13]}, {'page': 3, 'region': [0, 200, 100, 220], 'charspan': [14, 41]}])
        self.assertEqual(block_row(two)[:2], ('fail', 'page'))  # Codex R14-1: the key's region holds 'Wrong.'; the key's words sit in another region of the same page
        self.assertEqual(block_row(two, region=(0, 200, 100, 220)), ('pass', None, {'continued': True}))  # the key's own region
        self.assertEqual(block_row(two, want='Wrong.')[:2], ('pass', None))
        boxes = dict(across, anchor=[{'page': 3, 'region': [0, 0, 100, 20]}, {'page': 3, 'region': [0, 30, 100, 50]}])
        self.assertEqual(block_row(boxes, want='End of two. Start of three. More words.', region=(0, 0, 100, 50))[:2], ('pass', None))  # the key covers every box of the unit: the whole text, no mapping needed
        self.assertEqual(block_row(exact, approximate=True)[:2], ('fail', 'page'))  # Codex R14-3: a picture's words mapped to another place are no approximate reading
        self.assertEqual(block_row(dict(across, text='End of two. Start of three. More wordz.'), approximate=True)[0], 'approximate')  # a transcription difference is

    def test_wer_counts_insertions_substitutions_and_deletions_over_the_reference(self):
        # Codex N3: the old figure was a similarity distance — three inserted words scored zero
        self.assertEqual(grade.wer('revenue was flat elsewhere rose', 'revenue rose'), 1.5)
        self.assertEqual((grade.wer('a b c', 'a b c'), grade.wer('a x c', 'a b c'), grade.wer('a c', 'a b c')), (0.0, 0.333, 0.333))

    def test_a_phrase_is_contained_only_as_whole_words_and_numbers(self):
        # Codex R15-1: 'Revenue 10' was found inside 'Revenue 100', '10.5' and '10,000', 'not own' inside 'cannot own' — a changed number passed a period, a continuation, a reference
        for text, want, expect in (('Revenue 100', 'Revenue 10', False), ('Revenue 10.5', 'Revenue 10', False), ('Revenue 10,000', 'Revenue 10', False), ('cannot own', 'not own', False),
                                   ('see note 10', 'note 1', False), ('1,250', '250', False), ('years ended', 'year', False), ('Revenue -10', 'Revenue 10', False),
                                   ('First (Revenue 10).', 'Revenue 10', True), ('3.7 %', '3.7%', True), ('$1,250', '$', True), ('2024 2025', '2024', True), ('period-ended', 'ended', True), ('x', '', True)):
            self.assertEqual(grade.contains(text, want), expect, (text, want))
        res = self.run_grader(lambda r: self.cell(r, 'h24').update(text='December 28, 20245'))
        self.assertEqual(self.check(res, 'pkt/T01', 'periods')['verdict'], 'fail')  # the period '2024' is not printed inside '20245'
        res = self.run_grader(lambda r: self.unit(r, 'u2').update(text='Free cash flow is not a GAAP measure. See the table belows.'))
        self.assertEqual((self.check(res, 'pkt/S01', 'references')['verdict'], self.check(res, 'pkt/S01', 'references')['reason']), ('fail', 'phrase'))  # the reference phrase is not printed inside a longer word
        across = {'id': 'p', 'kind': 'text', 'text': 'End of two. First Revenue 100', 'anchor': [{'page': 2, 'region': [0, 700, 100, 792], 'charspan': [0, 11]}, {'page': 3, 'region': [0, 0, 100, 20], 'charspan': [12, 29]}]}
        self.assertEqual(self.block_row(across, want='Revenue 10')[:2], ('fail', 'text'))  # a mapped continuation holds 'Revenue 100', not the block 'Revenue 10'
        self.assertEqual(self.block_row(dict(across, text='End of two. First Revenue 10.'), want='Revenue 10')[:2], ('pass', None))
        def in_cell(r, text):  # the unit line printed inside the value cell, no unit cell of its own
            self.cells(r).remove(self.cell(r, 'unit')); self.cell(r, 'v1').update(text=text)
        self.assertEqual(self.check(self.run_grader(lambda r: in_cell(r, '769 (in millions)')), 'pkt/T01', 'unit_printed')['detail'], 'in_value_cell')
        self.assertEqual(self.check(self.run_grader(lambda r: in_cell(r, '769 (in millionsx)')), 'pkt/T01', 'unit_printed')['verdict'], 'fail')
        for text, mark, expect in (('Revenue 2015', '1', False), ('Revenue1', '1', True), ('Note(1)', '1', True), ('2015(1)', '(1)', True), ('Total(1) revenue', '(1)', True), ('Note1, next', '1', True), ('Note1.5', '1', False), ('Note1,000', '1', False), ('see 21', '1', False), ('100*', '*', True)):
            self.assertEqual(grade.contains(text, mark, marker=True), expect, (text, mark))  # a footnote mark may touch a word; it never cuts a number (the number-token rule is Codex's)
        raw = b'<p>December 2024</p><table><tr><td>Revenue 2015<sup>1</sup></td><td>1234</td></tr></table><p>1 a note</p>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        def label_rows(label, marks=('1',)):  # the marks dropped by the tool; their anchor names the label cell
            tb = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table>'), 'byte_end_exclusive': raw.index(b'</table>') + 8}, 'cells': [{'r': 0, 'c': 0, 'text': label, 'anchor': span(b'Revenue 2015<sup>1</sup>')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': span(b'1234')}]}
            return self.synthetic_cell(raw, [{'id': 'n', 'kind': 'footnote', 'text': '1 a note', 'anchor': span(b'1 a note')}], {'footnote_markers': [{'marker_text': m, 'anchor': span(b'<sup>1</sup>'), 'note_text': '1 a note', 'note_anchor': span(b'1 a note')} for m in marks]}, {}, tb)['footnote_markers']
        self.assertEqual(label_rows('Revenue 2015'), ('fail', 'marker_missing')); self.assertEqual(label_rows('Revenue 2015 1'), ('pass', None))
        self.assertEqual(label_rows('Revenue1,2', ('1', '2')), ('pass', None)); self.assertEqual(label_rows('Revenue1,20', ('1', '2')), ('fail', 'marker_missing'))  # a comma group of the record's own marks is marks; '1,20' is a number
        def period_rows(anchor):  # a period part with no source place: found among units that have a position, never among the unplaced
            return self.synthetic_cell(raw, [{'id': 'd', 'kind': 'text', 'text': 'December 2024', 'anchor': anchor}], {'periods': [{'role': 'value', 'type': 'duration', 'parts': [{'text': 'December 2024'}]}]}, {})['periods']
        self.assertEqual(period_rows(span(b'December 2024')), ('pass', None)); self.assertEqual(period_rows(None), ('fail', 'missing'))
        def unit_rows(unit, cell_text=b'1234 shares'):  # the unit printed inside the value cell itself, as a whole word
            raw2 = b'<table><tr><td>Revenue</td><td>' + cell_text + b'</td></tr></table>'; sp = lambda text: {'byte_start': raw2.index(text), 'byte_end_exclusive': raw2.index(text) + len(text)}
            tb = {'id': 't', 'kind': 'table', 'anchor': sp(b'<table>'), 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': sp(b'Revenue')}, {'r': 0, 'c': 1, 'text': cell_text.decode(), 'anchor': sp(cell_text)}]}
            return self.synthetic_cell(raw2, [], {'unit_printed': unit}, {}, tb)['unit_printed']
        self.assertEqual(unit_rows('shares'), ('pass', None)); self.assertEqual(unit_rows('share'), ('fail', 'missing'))  # 'share' is not the word the cell prints

    def test_order_inside_one_unit_is_the_routes_own_mapping_never_the_unit_index(self):
        # Codex R15-2: two blocks of one paragraph read whole across a page break passed as separate units and failed `order` as one correctly mapped unit, while a reversed mapping gave the same verdicts
        parts, boxes = ['The continuous paragraph begins here', 'and finishes on the next page.'], [{'page': 1, 'region': [0, 0, 100, 20]}, {'page': 2, 'region': [0, 0, 100, 20]}]
        (self.pkg / 'CLAUDE_ANSWER_KEY.json').write_text(json.dumps([{'key_id': f'pkt/S{i}', 'id': f'S{i}', 'file_id': PDF_ID, 'type': 'structure', 'fields': {'printed_text': p, 'kind': 'paragraph'}, 'alternatives': {}} for i, p in enumerate(parts, 1)]))
        (self.pkg / 'CLAUDE_KEY_FLAGS.json').write_text(json.dumps({'uncertain': []})); (self.pkg / 'KEY_SUPPORT_MAP.json').write_text('{}')
        tj = json.loads((self.pkt / 'targets.json').read_text()); tj['targets'] = [{'id': f'S{i}', 'kind': 'structure', 'file_id': PDF_ID, 'block_anchor': b} for i, b in enumerate(boxes, 1)]; (self.pkt / 'targets.json').write_text(json.dumps(tj))
        def one_unit(order):  # one unit over both pages; the route's own character mapping says which words lie on which page
            def m(r):
                p = [parts[i] for i in order]; a = [dict(boxes[order[0]], charspan=[0, len(p[0])]), dict(boxes[order[1]], charspan=[len(p[0]) + 1, len(' '.join(p))])]
                r[PDF_ID]['units'] = [{'id': 'u', 'kind': 'text', 'text': ' '.join(p), 'anchor': a}]
            return m
        def separate(r): r[PDF_ID]['units'] = [{'id': f'u{i}', 'kind': 'text', 'text': p, 'anchor': b} for i, (p, b) in enumerate(zip(parts, boxes))]
        verdicts = lambda res: (res['targets']['pkt/S1']['verdict'], res['targets']['pkt/S2']['verdict'], self.check(res, 'pkt/S1', 'order')['verdict'], self.check(res, 'pkt/S2', 'order')['verdict'])
        self.assertEqual(verdicts(self.run_grader(separate)), ('PASS', 'PASS', 'pass', 'pass'))
        self.assertEqual(verdicts(self.run_grader(one_unit((0, 1)))), ('PASS', 'PASS', 'pass', 'pass'))  # merged, mapped in source order: the same as separate
        self.assertEqual(verdicts(self.run_grader(one_unit((1, 0)))), ('FAIL', 'FAIL', 'fail', 'fail'))  # the mapping puts the page-2 words first: a genuine inversion
        self.declare(kinds=('paragraph',))
        self.assertEqual(verdicts(self.run_grader(one_unit((0, 1)))), ('APPROXIMATE', 'APPROXIMATE', 'pass', 'pass'))  # an approximate block keeps its order check
        self.assertEqual(verdicts(self.run_grader(one_unit((1, 0)))), ('FAIL', 'FAIL', 'fail', 'fail'))

    def test_two_blocks_carried_by_one_table_are_ordered_by_its_cells_or_left_unresolved(self):
        # Codex R15-2, table-carried blocks: the cell order inside the unit is the route's own order; two cells at one grid position prove nothing
        def layout(r, rows=((0, 0), (1, 0))):  # the lead paragraph and the list item laid out as the rows of one layout table
            u = self.html(r); lead, li = self.unit(r, 'u2'), self.unit(r, 'u12'); i = u.index(lead); u.remove(lead); u.remove(li)
            u.insert(i, {'id': 'lay', 'kind': 'table', 'anchor': {'byte_start': lead['anchor']['byte_start'], 'byte_end_exclusive': li['anchor']['byte_end_exclusive']}, 'links': lead['links'], 'cells': [
                {'r': rows[0][0], 'c': rows[0][1], 'rs': 1, 'cs': 1, 'text': lead['text'], 'anchor': lead['anchor'], 'struck': lead['struck']}, {'r': rows[1][0], 'c': rows[1][1], 'rs': 1, 'cs': 1, 'text': li['text'], 'anchor': li['anchor']}]})
        verdicts = lambda res: (self.verdict(res, 'pkt/S01'), self.verdict(res, 'pkt/S04'), self.check(res, 'pkt/S01', 'order')['verdict'], self.check(res, 'pkt/S04', 'order')['verdict'])
        self.assertEqual(verdicts(self.run_grader(layout)), ('PASS', 'PASS', 'pass', 'pass'))
        self.assertEqual(verdicts(self.run_grader(lambda r: layout(r, ((1, 0), (0, 0))))), ('FAIL', 'FAIL', 'fail', 'fail'))  # the rows swapped against the source
        self.assertEqual(verdicts(self.run_grader(lambda r: layout(r, ((0, 0), (0, 0))))), ('PASS', 'PASS', 'pass', 'pass'))  # one grid position: the route's own cell order decides (Codex's reading of "its cell order")
        def listed_backwards(r): layout(r, ((0, 0), (0, 0))); self.unit(r, 'lay')['cells'].reverse()
        self.assertEqual(verdicts(self.run_grader(listed_backwards)), ('FAIL', 'FAIL', 'fail', 'fail'))
        def wrong_second(r): layout(r, ((1, 0), (0, 0))); self.unit(r, 'lay')['cells'][1]['text'] = 'Other words.'
        self.assertEqual(verdicts(self.run_grader(wrong_second)), ('FAIL', 'FAIL', 'fail', 'fail'))  # the arrangement is wrong whatever the second cell's text: positions are the route's claims
        def whole_unit(r):  # one text unit, one place, holding both blocks' bytes but only the first block's words: no order to read inside it
            u = self.html(r); lead, li = self.unit(r, 'u2'), self.unit(r, 'u12'); u.remove(li); lead['anchor'] = {'byte_start': lead['anchor']['byte_start'], 'byte_end_exclusive': li['anchor']['byte_end_exclusive']}
        self.assertEqual(verdicts(self.run_grader(whole_unit)), ('UNRESOLVED', 'FAIL', 'unresolved', 'unresolved'))

    def test_blocks_side_by_side_on_one_row_keep_their_source_order(self):
        # Codex's round-15 control: two boxes on one visual row differ in x only; the route's order against the source's left-to-right order is still checked
        parts, boxes = ['Left block', 'Right block'], [{'page': 1, 'region': [0, 0, 40, 20]}, {'page': 1, 'region': [60, 0, 100, 20]}]
        (self.pkg / 'CLAUDE_ANSWER_KEY.json').write_text(json.dumps([{'key_id': f'pkt/S{i}', 'id': f'S{i}', 'file_id': PDF_ID, 'type': 'structure', 'fields': {'printed_text': p, 'kind': 'paragraph'}, 'alternatives': {}} for i, p in enumerate(parts, 1)]))
        (self.pkg / 'CLAUDE_KEY_FLAGS.json').write_text(json.dumps({'uncertain': []})); (self.pkg / 'KEY_SUPPORT_MAP.json').write_text('{}')
        tj = json.loads((self.pkt / 'targets.json').read_text()); tj['targets'] = [{'id': f'S{i}', 'kind': 'structure', 'file_id': PDF_ID, 'block_anchor': b} for i, b in enumerate(boxes, 1)]; (self.pkt / 'targets.json').write_text(json.dumps(tj))
        for table in (False, True):
            for reverse in (False, True):
                def m(r):
                    items = list(zip(parts, boxes))[::-1 if reverse else 1]
                    r[PDF_ID]['units'] = [{'id': 't', 'kind': 'table', 'anchor': boxes, 'cells': [{'r': 0, 'c': i, 'text': p, 'anchor': b} for i, (p, b) in enumerate(items)]}] if table else [{'id': f'u{i}', 'kind': 'text', 'text': p, 'anchor': b} for i, (p, b) in enumerate(items)]
                res = self.run_grader(m)
                self.assertEqual([x['verdict'] for x in res['results'] if x['check'] == 'order'], ['fail' if reverse else 'pass'] * 2, (table, reverse))

    def test_a_position_that_cannot_be_true_supplies_no_evidence_whatever_the_lookup(self):
        # Codex R15-3: an XML unit at [-1, beyond the end) was dishonest and still carried `unit_printed`; a context field with `{}` still proved the person; an anchor with an end and no start, or a string box, read as clean (or crashed)
        def xml_unit(r, anchor, name='securitiesClassTitle'): next(u for u in r[XML_ID]['units'] if grade.local(u['name']) == name).update(anchor=anchor)
        res = self.run_grader(lambda r: xml_unit(r, {'byte_start': -1, 'byte_end_exclusive': 10 ** 6}))
        self.assertEqual((self.verdict(res, 'pkt/X01'), self.check(res, 'pkt/X01', 'unit_printed')['reason'], res['gates']['honest_anchors']['dishonest']), ('FAIL', 'missing', {XML_ID: 1}))
        res = self.run_grader(lambda r: next(u for u in r[XML_ID]['units'] if u['text'] == 'Beta').update(anchor={}))
        self.assertEqual((self.check(res, 'pkt/X01', 'row_context')['verdict'], res['gates']['honest_anchors']['dishonest']), ('fail', {XML_ID: 1}))
        for anchor in ({'byte_end_exclusive': 5}, {'byte_start': 5}, {'byte_start': elem('after')['byte_start'] + 3, 'byte_end_exclusive': elem('after')['byte_start'] + 3}, {'byte_start': 'a', 'byte_end_exclusive': 9}, {'page': 1, 'region': ['x', 0, 1, 1]}, {'page': 1, 'region': [0, 0, 1]}, {'page': 0, 'region': [0, 0, 1, 1]}, {'page': 1, 'region': [0, 0, float('inf'), 1]}, 'gap', 7):
            res = self.run_grader(lambda r: self.unit(r, 'u9').update(anchor=anchor))
            self.assertEqual(res['gates']['honest_anchors']['dishonest'], {HTM_ID: 1}, anchor)  # any claim that is no possible position is a false claim (a string or a number too, as Codex's controls require)
            self.assertEqual(res['gates']['honest_anchors']['bounds_inconsistent'], {HTM_ID: 1} if isinstance(anchor, dict) and 'region' in anchor else {}, anchor)  # of those, the page boxes stay visible as such
            self.assertEqual(self.check(res, 'pkt/T05', 'segment_or_basis')['verdict'], 'fail', anchor)
        res = self.run_grader(lambda r: self.unit(r, 'u9').update(anchor={'byte_start': 5}, link_flag='gap'))
        self.assertEqual(res['gates']['honest_anchors']['dishonest'], {HTM_ID: 1})  # a route flag never hides an impossible position
        res = self.run_grader(lambda r: self.unit(r, 'u3').update(anchor={'byte_start': 5}))
        self.assertEqual((res['gates']['honest_anchors']['dishonest'], self.verdict(res, 'pkt/T01')), ({HTM_ID: 1}, 'PASS'))  # a table's own envelope is a claim too; its placed cells still carry their values
        empty_gap = lambda text: lambda r: self.html(r).append({'id': 'pic2', 'kind': 'image', 'text': text, 'anchor': {'byte_start': 10, 'byte_end_exclusive': 10}, 'link_flag': 'gap'})
        res = self.run_grader(empty_gap(''))
        self.assertEqual((res['gates']['honest_anchors']['dishonest'], res['gates']['honest_anchors']['unplaced']), ({}, {HTM_ID: 1}))  # a picture the linker could not place claims no text: counted apart, never dishonest, never covering
        self.assertEqual(self.run_grader(empty_gap('Invented'))['gates']['honest_anchors']['dishonest'], {HTM_ID: 1})  # text at that position is a claim, and an impossible one
        res = self.run_grader(lambda r: r[PDF_ID]['pages'].update({'2': 'big'}))
        self.assertEqual((res['gates']['honest_anchors']['dishonest'], self.verdict(res, 'pkt/P01')), ({PDF_ID: 10}, 'UNRESOLVED'))  # a page whose declared size is no size: every box on it (two texts, the table's envelope, seven cells) is a position that cannot be checked against the route's own declaration — dishonest, never a crash
        res = self.run_grader(lambda r: self.unit(r, 'u9').update(text='Invented words', link_flag='gap', anchor={'byte_start': elem('after')['byte_start'], 'byte_end_exclusive': elem('after')['byte_end_exclusive']}))
        self.assertEqual(res['gates']['honest_anchors']['dishonest'], {HTM_ID: 1})  # a route's `gap` flag exempts no text from certification
        def unanchored_label(r): next(c for c in r[PDF_ID]['units'][2]['cells'] if c['text'] == 'Southeast')['anchor'] = None
        res = self.run_grader(unanchored_label)
        self.assertEqual((self.check(res, 'pkt/P01', 'row_label')['reason'], res['gates']['honest_anchors']['unanchored']), ('missing', {PDF_ID: 1}))  # a cell with no position is counted, never consulted

    def test_a_picture_is_what_the_reader_sees_never_a_tag_in_the_bytes(self):
        # Codex R15-4: an <img> inside a comment, a script, an attribute or a hidden subtree counted as a picture, so invented text there escaped certification
        page = lambda inner, tail=b'': b'<html><body><p>Text here.</p>' + inner + b'<p>More.</p>' + tail + b'</body></html>'
        raw = page(b'<span></span>', b'<img src="later.png">'); a = {'byte_start': raw.index(b'.</p>') + 5, 'byte_end_exclusive': raw.index(b'<p>More')}
        rf = grade.RouteFile({'file_id': 'syn/doc.htm', 'units': [{'id': 'u', 'kind': 'text', 'text': 'Profit 999', 'anchor': a}]}, raw, 'htm'); g = grade.gates_for_file(rf, 'OK')
        self.assertEqual((grade.picture_at(rf, [a]), g['dishonest'], g['pictures']), (False, 1, 1))  # a picture elsewhere on the page is no picture at these bytes
        raw = page(b'<img src="x.png">', b'<style>p{display:none}</style>'); a = {'byte_start': raw.index(b'.</p>') + 5, 'byte_end_exclusive': raw.index(b'<p>More')}
        rf = grade.RouteFile({'file_id': 'syn/doc.htm', 'units': [{'id': 'u', 'kind': 'text', 'text': 'Profit 999', 'anchor': a}]}, raw, 'htm'); g = grade.gates_for_file(rf, 'OK')
        self.assertEqual((grade.picture_at(rf, [a]), g['dishonest'], g['pictures'], g['anchors_measured']), (True, 0, None, False))  # a stylesheet rule: what is shown is uncertain — nothing that depends on the reading is counted, never a mismatch (Codex R16-3, R17-C4)
        for inner, picture in ((b'<img src="x.png">', True), (b'<IMG SRC="x.png">', True), (b'<div style="visibility:hidden"><img src="x" style="visibility:visible"></div>', True),
                               (b'<!-- <img src="x.png"> -->', False), (b'<script>let x="<img src=x>";</script>', False), (b'<div title="<img src=x>"></div>', False),
                               (b'<div style="display:none"><img src="x.png"></div>', False), (b'<img src="x" style="visibility:hidden">', False), (b'<div style="visibility:hidden"><img src="x"></div>', False), (b'<div hidden><img src="x"></div>', False)):
            raw = page(inner); a = {'byte_start': raw.index(b'.</p>') + 5, 'byte_end_exclusive': raw.index(b'<p>More')}
            rf = grade.RouteFile({'file_id': 'syn/doc.htm', 'units': [{'id': 'u', 'kind': 'text', 'text': 'Profit 999', 'anchor': a}]}, raw, 'htm'); g = grade.gates_for_file(rf, 'OK')
            self.assertEqual((grade.picture_at(rf, [a]), g['dishonest'], g['pictures'], g['anchors_measured']), (picture, 0 if picture else 1, 1 if picture else 0, not picture), inner)  # a reading of a picture is not measured; text at no picture is compared as text

    def test_a_number_is_printed_with_its_sign_and_its_point(self):
        # Codex R16-1: '10 million' was found inside '-10 million', '−10 million', '+10 million'; '5 million' inside '.5 million' — a changed sign or value passed a
        # continuation. Same class (own audit): the lead-in's own containment regex, footnote marks deleted from inside a number, own pieces removed from inside one
        for text, want, expect in (('-10 million', '10 million', False), ('−10 million', '10 million', False), ('+10 million', '10 million', False), ('.5 million', '5 million', False),
                                   ('-.5 million', '5 million', False), ('$.5', '5', False), ('- 10 million', '10 million', None), ('\u2212 10 million', '10 million', None), ('(-10)', '10', False), ('Revenue -10 million', '10 million', False),
                                   ('-10 million', '- 10 million', True), ('- 10 million', '-10 million', True), ('10 million', '-10 million', False), ('The amount is 10 million.', '10 million', True),
                                   ('ages 5-10', '10', True), ('ages 5 - 10', '10', True), ('COVID-19 cases', '19 cases', True), ('No.5', '5', True), ('10.5', '5', False), ('1.5', '.5', False),
                                   ('ages 5-10', '-10', False), ('ages 5 - 10', '-10', False), ('x-.5', '-.5', False), ('rate .5', '.5', True), ('total (-10)', '-10', True),
                                   ('-$10 million', '10 million', False), ('-$10 million', '$10 million', False), ('- $ 10 million', '$10 million', None), ('loss of -$10 million', '-$10 million', True),
                                   ('Preferred stock \u2013 10,000,000 shares authorized:', '10,000,000 shares authorized', None), ('1.01% - 2.00%', '2.00%', None), ('EURIBOR + 3.8%', '3.8%', None), ('- 2 -', '2', None),  # Codex R17-C5, real development texts: a free-standing dash or plus before a number is a separator, a range, an operator or a sign — the text alone cannot tell
                                   ('Preferred stock \u2013 10,000,000 shares', 'stock - 10,000,000 shares', True), ('1/1/23 \u2013 1/31/23', '1/31/23', True), ('CI 0.74 \u2013 0.93, p', '0.93', True), ('2023 - $111,528; 2022', '$111,528', True), ('PTE 84- 14 (a class', '14 (a class', True),  # the dash inside the stretch, a free dash between two numbers, a dash glued to a number: no sign in question
                                   ('11%-63%', '63%', None), ('11 %- 63 %', '63 %', None), ("a 2'-0-methoxyethyl sugar", '0-methoxyethyl sugar', None), ('call (206)-392-5040', '392-5040', None), ('x=-10', '10', None), ('Total:-10', '10', None), ('"-10"', '10', None),
                                   ('5,-10', '10', None), ('$-506', '506', None), ('5\u00a2-10\u00a2', '10\u00a2', None), ('(2)-4', '4', None), ('11%-63%', '-63%', True), ('x=-10', '-10', True), ('(2)-4', '-4', True), ('11%-63%', '11%', True),  # a dash glued to other punctuation: a range, a join or a sign (each printed in the development texts, or its sibling) — undecided; with the dash, the same characters
                                   ('Day 8 n.d. -23 -18 Day 15', '23', False), ('Day 8 n.d. -23 -18 Day 15', '18', None), ('Day 8 n.d. -23 -18 Day 15', '-18', True), ('Codification 825 - 10 -25 (previously', '25 (previously', None), ('US2007 -0287831; US2004', '0287831', None), ('0.79% -3.27% (9)', '3.27% (9)', None), ('(5) -10', '10', None),
                                   ('15 13 % -81 -69 +78', '81', False), ('change (mg/dL) -13 -32', '13', False), ('CI, \u221290 to \u221228; P', '28; P', False),  # after a number (with its own punctuation) a touching dash is a sign in a list of values and a broken join or range elsewhere: undecided, never a pass by the text; after a word or free punctuation it is a sign
                                   ('-$506', '$', True), ('-$506', '506', False), ('-$506', '-', False), ('$-506', '$', True), (chr(0x201c) + 'Premiums' + chr(0x201d) + ' ' + chr(0x2014) + ' $12,100 million unfavorable', '12,100 million', None),  # own audit: a currency symbol between sign and digits stays a piece of its own
                                   ('5-$10', '$10', True), ('5-$10', '-$10', False), ('−€5', '€5', False), ('rated A- or better', '- or better', True), ('$10 million', '10 million', True), ('10%', '10', True)):  # the last two: an unsigned number and its symbol are separate pieces (the key's own split of printed and display values)
            self.assertIs(grade.contains(text, want), expect, (text, want))  # the text settles three cases: a dash glued to a word or number joins or ranges; one touching its number, free of what precedes it, is its sign; one free between two numbers ranges. Any other is undecided (None)
        across = lambda local: {'id': 'p', 'kind': 'text', 'text': 'End of two. ' + local, 'anchor': [{'page': 2, 'region': [0, 700, 100, 792], 'charspan': [0, 11]}, {'page': 3, 'region': [0, 0, 100, 20], 'charspan': [12, 12 + len(local)]}]}
        for local, want, verdict in (('-10 million', '10 million', 'fail'), ('.5 million', '5 million', 'fail'), ('−10 million', '-10 million', 'pass'), ('The amount is 10 million.', '10 million', 'pass')):
            self.assertEqual(self.block_row(across(local), want=want)[0], verdict, (local, want))  # Codex's reproducer: the mapped page-2 part of a continued paragraph
        self.assertEqual(self.block_row(across('Preferred stock \u2013 10,000,000 shares authorized'), want='10,000,000 shares authorized')[:2], ('unresolved', 'numeric_boundary'))  # a page box has no source text to ask: neither a guessed negative nor a pass (R17-C5)
        raw = b'<p>Then sales of 1,250 million follow.</p><table id="t"><tr><td>Total</td><td>5</td></tr></table>'
        span = lambda text: {'byte_start': raw.index(text), 'byte_end_exclusive': raw.index(text) + len(text)}
        table = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table'), 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Total', 'anchor': span(b'Total')}, {'r': 0, 'c': 1, 'text': '5', 'anchor': span(b'>5<')}]}
        def lead_row(lead):
            t = {'key_id': 'syn/L', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': span(b'>5<'), 'table_anchor': table['anchor'], 'alternatives': {}, 'excluded': set(),
                 'fields': {'printed_value': '5', 'lead_in': lead}, 'support': {'lead_in': {'anchors': [span(b'Then sales of 1,250 million follow.')]}}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [{'id': 'l', 'kind': 'text', 'text': 'Then sales of 1,250 million follow.', 'anchor': span(b'Then sales of 1,250 million follow.')}, table]}, raw, 'htm'))
            g.grade_cell(); return next((r['verdict'], r['detail']) for r in g.rows if r['check'] == 'lead_in')
        self.assertEqual(lead_row('sales of 1,250 million follow.'), ('pass', 'contained')); self.assertEqual(lead_row('250 million follow.')[0], 'fail')  # the lead-in reads containment by the same rule
        raw2 = b'<p><span>Then sales of</span><span>1,250 million follow.</span></p><table id="t"><tr><td>Total</td><td>5</td></tr></table>'
        sp2 = lambda text: {'byte_start': raw2.index(text), 'byte_end_exclusive': raw2.index(text) + len(text)}
        tb2 = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw2.index(b'<table'), 'byte_end_exclusive': len(raw2)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Total', 'anchor': sp2(b'Total')}, {'r': 0, 'c': 1, 'text': '5', 'anchor': sp2(b'>5<')}]}
        def touching_row(lead):  # the lead-in read as two touching pieces: the page alone could space them (unresolved), the words must still be whole
            t = {'key_id': 'syn/L', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': sp2(b'>5<'), 'table_anchor': tb2['anchor'], 'alternatives': {}, 'excluded': set(),
                 'fields': {'printed_value': '5', 'lead_in': lead}, 'support': {'lead_in': {'anchors': [{'byte_start': raw2.index(b'Then'), 'byte_end_exclusive': raw2.index(b'</span></p>')}]}}}
            units = [{'id': 'a', 'kind': 'text', 'text': 'Then sales of', 'anchor': sp2(b'Then sales of')}, {'id': 'b', 'kind': 'text', 'text': '1,250 million follow.', 'anchor': sp2(b'1,250 million follow.')}, tb2]
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units}, raw2, 'htm')); g.grade_cell(); return next(r['verdict'] for r in g.rows if r['check'] == 'lead_in')
        self.assertEqual((touching_row('sales of 1,250 million follow.'), touching_row('250 million follow.')), ('unresolved', 'fail'))
        for got, want, marks, expect in (('Revenue 215', 'Revenue 25', ['1'], False), ('Revenue 2015', 'Revenue 201', ['5'], False), ('Revenue 215', 'Revenue 2', ['15'], False), ('Revenue 215', 'Revenue 5', ['21'], False),
                                         ('Revenue 215 1', 'Revenue 25 1', ['1'], False), ('Revenue 215 15', 'Revenue 2 15', ['15'], False), ('Revenue 215 21', 'Revenue 5 21', ['21'], False),  # the mark is part of the key text too: the deletion search itself
                                         ('Revenue1', 'Revenue', ['1'], True), ('Revenue1,2', 'Revenue', ['1', '2'], True), ('Revenue 1, 2', 'Revenue', ['1', '2'], True)):
            self.assertEqual(grade.same(got, want, marks)[0], expect, (got, want, marks))  # a mark is never cut out of a number, at either edge; a comma group of the record's own marks is marks
        self.assertEqual([grade.minus_marks_anywhere('Segment 215', [m]) for m in ('1', '15', '21')] + [grade.minus_marks_anywhere('Segment1 total', ['1']), grade.minus_markers('Revenue 2015', ['5']), grade.minus_markers('12 Revenue', ['1']), grade.minus_markers('Revenue1', ['1'])],
                         ['Segment 215'] * 3 + ['Segment total', 'Revenue 2015', '12 Revenue', 'Revenue'])
        self.assertEqual((grade.same('Total 12015', 'Total 1', (), ['2015']), grade.same('Total 12015', 'Total 5', (), ['1201']), grade.same('Total 2015', 'Total', (), ['2015'])),
                         ((False, None), (False, None), (True, 'joined_with_own_pieces')))  # an own piece is set aside only where it is printed whole, at both edges
        self.assertEqual(grade.same('Revenues total', 'Revenue total', (), ['s']), (False, None))  # nor out of a word
        # the gate is different: a mark the route reports APART may touch a number, as a superscript does ('10.67' + mark '4' over '10.67<sup>4</sup>'): the gate certifies
        # the characters, the value check judges the split ('Revenue 201' + '5' over 'Revenue 2015' is honest characters and a wrong value, test_footnote_digit_glued_to_the_value_fails)
        for source, text, marks in ((b'<p>10.67<sup>4</sup></p>', '10.67', ['4']), (b'<p>Revenue 2015</p>', 'Revenue 201', ['5'])):
            rf = grade.RouteFile({'file_id': 'syn/f.htm', 'units': [{'id': 'u', 'kind': 'text', 'text': text, 'markers': marks, 'anchor': {'byte_start': 3, 'byte_end_exclusive': len(source) - 4}}]}, source, 'htm')
            self.assertEqual(grade.gates_for_file(rf, 'OK')['dishonest'], 0, source)

    def test_a_page_box_names_its_page_and_a_picture_box_its_file(self):
        # Codex R16-2: a PDF box with no page, or a null one, stayed a position and supplied a table title by text; the same box on an undeclared page did not
        pdf = grade.RouteFile({'file_id': 'syn/f.pdf', 'pages': {'1': [100, 100]}, 'units': []}, None, 'pdf'); box = [0, 0, 80, 10]
        for place, ok in (({'page': 1, 'region': box}, True), ({'file': 'f.pdf', 'page': 1, 'region': box}, True), ({'region': box}, False), ({'page': None, 'region': box}, False), ({'file': 'f.pdf', 'region': box}, False),
                          ({'page': 2, 'region': box}, False), ({'page': 0, 'region': box}, False), ({'page': -1, 'region': box}, False), ({'page': 1.0, 'region': box}, False), ({'page': '1', 'region': box}, False),
                          ({'page': True, 'region': box}, False), ({'byte_start': 0, 'byte_end_exclusive': 2, 'region': box}, False), ({'byte_start': 0, 'byte_end_exclusive': 2, 'page': 1, 'region': box}, True),
                          ({'byte_start': 0, 'byte_end_exclusive': 2}, False)):  # own audit, same class: a PDF is addressed by page boxes — a byte span alone dodged every box check and still stood as a position
            self.assertEqual(pdf.possible(place), ok, place)
        bare = grade.RouteFile({'file_id': 'syn/f.pdf', 'units': []}, None, 'pdf')  # a PDF route that declares no page sizes: only the box's own rules decide
        for place, ok in (({'page': 3, 'region': box}, True), ({'region': box}, False), ({'page': None, 'region': box}, False), ({'page': 1, 'region': [0, 0, float('inf'), 10]}, False), ({'page': 1, 'region': [0, 0, 80]}, False)):
            self.assertEqual(bare.possible(place), ok, place)
        for pages in ({'1': None}, {'1': []}, {'1': ['100', '100']}, {'1': 'big'}, {'1': {'width': 100, 'height': 100}}, {'bad': [100, 100]}, {'1.0': [100, 100]}, {'\u00b2': [100, 100]}, {'0': [100, 100]},
                      {'1': [float('inf'), 100]}, {'1': [100, float('inf')]}, {'1': [float('nan'), 100]}, {'1': [True, 100]}, {'1': [0, 100]}, {'1': [-100, 100]}, [[100, 100]], 'x', 7):
            rf = grade.RouteFile({'file_id': 'syn/f.pdf', 'pages': pages, 'units': []}, None, 'pdf')  # Codex R17-C1: a declaration that is unusable never reads as no declaration (and never stops the run: a list, a string, a key that is no number)
            self.assertEqual((rf.possible({'page': 1, 'region': box}), rf.possible({'page': 99, 'region': box})), (False, False), pages)
        for data in ({}, {'pages': {}}, {'pages': None}):
            self.assertTrue(grade.RouteFile({'file_id': 'syn/f.pdf', 'units': [], **data}, None, 'pdf').possible({'page': 3, 'region': box}), data)  # a route that declares no sizes stays as it was: located, never measured
        self.assertEqual([pdf.possible({'page': 1, 'region': r}) for r in ([0, 0, 100, 100], [0, 0, 101, 10])], [True, False])
        htm = grade.RouteFile({'file_id': 'syn/f.htm', 'units': []}, b'<p>x</p>', 'htm')
        for place, ok in (({'file': 'scan.png', 'region': box}, True), ({'region': box}, False), ({'file': '', 'region': box}, False), ({'file': 7, 'region': box}, False), ({'file': 'scan.png', 'page': None, 'region': box}, False),
                          ({'page': 1, 'region': box}, False), ({'file': 'scan.png', 'page': 1, 'region': box}, False), ({'byte_start': 0, 'byte_end_exclusive': 2}, True)):
            self.assertEqual(htm.possible(place), ok, place)  # a picture file's box names the file (contract: picture files {file, region}); only a PDF has pages; a box naming no canvas is no position
        for change, boxes in ((lambda a: a.pop('page'), {PDF_ID: 1}), (lambda a: a.update(page=None), {PDF_ID: 1}), (lambda a: (a.clear(), a.update(byte_start=0, byte_end_exclusive=3)), {})):
            res = self.run_grader(lambda r: change(r[PDF_ID]['units'][0]['anchor']))
            self.assertEqual((self.check(res, 'pkt/P01', 'table_title')['reason'], res['gates']['honest_anchors']['dishonest'], res['gates']['honest_anchors']['bounds_inconsistent']), ('missing', {PDF_ID: 1}, boxes))
        unit = lambda anchor: [{'id': 'a', 'kind': 'text', 'text': 'Words', 'anchor': anchor}]
        for fid, fmt, anchor in (('syn/f.pdf', 'pdf', {'page': 1, 'region': box, 'byte_start': 0, 'byte_end_exclusive': 3}), ('syn/scan.gif', 'gif', {'byte_start': 0, 'byte_end_exclusive': 3})):
            g = grade.gates_for_file(grade.RouteFile({'file_id': fid, 'units': unit(anchor)}, b'no text layer', fmt), 'OK')
            self.assertEqual((g['dishonest'], g['anchors_measured']), (0, False), fid)  # bytes in a source with no text layer are certified by nothing: not measured, never "measured and clean"

    def test_what_the_scanner_cannot_judge_is_not_measured_and_never_a_mismatch(self):
        # Codex R16-3, R17-C4: an exact picture reading became dishonest once a stylesheet made the file uncertain; a picture the page cannot show kept a certain
        # exemption for invented text; an apparent <img> inside literal text counted as a picture; text in SVG vanished from a file reported measured and clean
        def gate(html, text='Revenue 10', at=b'<img', end=None):
            raw = b'<html><body>' + html + b'</body></html>'; s = raw.index(at); a = {'byte_start': s, 'byte_end_exclusive': raw.index(b'>', s) + 1 if end is None else end(raw)}
            rf = grade.RouteFile({'file_id': 'syn/f.htm', 'units': [{'id': 'u', 'kind': 'image', 'text': text, 'anchor': a}]}, raw, 'htm'); g = grade.gates_for_file(rf, 'OK')
            return grade.picture_at(rf, [a]), g['dishonest'], g['anchors_measured']
        img = b'<img width="200" height="40" src="scan.png">'
        for html in (img, b'<!-- <style>img{opacity:0}</style> -->' + img, b'<style>p{color:red}</style>' + img, b'<dialog open>' + img + b'</dialog>',
                     b'<img width="0" height="40" src="scan.png">', b'<img src="scan.png" style="width:0px;height:0px;border:0;padding:0">', b'<img style="inline-size:0;block-size:0" src="scan.png">',
                     b'<img style="clip-path:inset(100%)" src="scan.png">', b'<div style="transform:scale(0)">' + img + b'</div>', b'<div style="width:0;height:0;overflow:hidden">' + img + b'</div>',
                     b'<style>img{opacity:1}</style>' + img, b'<link rel="stylesheet" href="unavailable.css">' + img, img + b'<style><!-- p{display:none} --></style>'):
            self.assertEqual(gate(html), (True, 0, False), html)  # a picture element in a subtree the hiding rules leave shown: whether it paints — its size, clipping, transforms, a stylesheet — is beyond the scanner, so its reading is not measured: never a mismatch, never a certificate
        self.assertEqual(gate(img, text=''), (True, 0, True))  # a unit that claims no text at a picture leaves nothing unmeasured
        for html in (b'<noscript>' + img + b'</noscript>', b'<dialog>' + img + b'</dialog>', b'<div style="display:none">' + img + b'</div>', b'<textarea>' + img + b'</textarea>', b'<xmp>' + img + b'</xmp>',
                     b'<plaintext>' + img, b'<iframe>' + img + b'</iframe>', b'<noembed>' + img + b'</noembed>', b'<noframes>' + img + b'</noframes>'):
            self.assertEqual(gate(html), (False, 1, True), html)  # no picture element there — a hidden subtree, or an apparent tag that is literal text of a raw-text element: the claimed text is compared as text
        self.assertEqual(gate(img, at=b'src=', end=lambda raw: raw.index(b'>', raw.index(b'src=')) + 1), (False, 1, True))  # a span inside the tag is not at the picture (as round 15)
        self.assertEqual(gate(b'<p>Caption</p>' + img, text='Invented', at=b'<p>', end=lambda raw: raw.index(b'scan.png">') + 10), (False, 1, True))  # text the reader sees at the span: no picture-only place
        for html, text, certain, pictures in ((b'<textarea><img src="x">Revenue &amp; 10</textarea>', '<img src="x">Revenue & 10', True, 0), (b'<xmp><img src="x">Revenue &amp; 10</xmp><p>z</p>', '<img src="x">Revenue &amp; 10 z', True, 0),
                                              (b'<p>a</p><plaintext><img src="x"></p>', 'a <img src="x"></p>', True, 0), (b'<iframe><img src="x">Revenue</iframe><p>After</p>', 'After', True, 0),
                                              (b'<noembed style="display:block"><img src="x">Revenue</noembed><p>After</p>', 'After', True, 0), (b'<noframes><img src="x">Revenue</noframes><p>After</p>', 'After', True, 0),
                                              (b'<noframes style="display:block">Revenue</noframes><p>After</p>', 'After', False, 0), (b'<noembed><script></noembed><img src="x"><p>After</p>', 'After', True, 1),
                                              (b'<p>a</p><style>p{display:none}', 'a', False, 0), (b'<p>a</p><title>b', 'a', True, 0), (b'<p>a</p><script>b', 'a', True, 0),
                                              (b'<plaintext>a</plaintext>b', 'a</plaintext>b', True, 0), (b'<XMP><IMG SRC="x"></XMP><p>z</p>', '<IMG SRC="x"> z', True, 0), (b'<p>x</p><textarea hidden><img src="y"></textarea>', 'x', True, 0), (b'<xmp>&amp; 10</xmp>', '&amp; 10', True, 0)):
            v = anchor.Visible(html); self.assertEqual((' '.join(v.text.split()), v.certain, len(v.pictures)), (text, certain, pictures), html)  # raw-text elements hold literal text, never child tags (Chrome: round16_codex/logs/browser_cases.json); a <noframes> the author displays shows its text: uncertain; an unclosed <style> is CSS to the end
        for html, certain in ((b'<svg width="200" height="40" hidden><text y="20">Shown 30</text></svg>', False), (b'<svg style="display:none"><p>Shown 30</p></svg>', False), (b'<p>x</p><math><mi>y</mi></math>', False),
                              (b'<div style="content-visibility:hidden"><p>Hidden 10</p></div>', False), (b'<div style="content-visibility:visible"><p>Shown 10</p></div>', True), (b'<p style="color:red">x</p>', True)):
            self.assertEqual(anchor.Visible(html).certain, certain, html)  # SVG/MathML content and a content-visibility other than visible are beyond the scanner: the file is uncertain, never measured and clean
        raw = b'<html><body><style>p{display:none}</style><p>Revenue</p></body></html>'; at = {'byte_start': raw.index(b'Revenue'), 'byte_end_exclusive': raw.index(b'Revenue') + 7}
        for unit, dishonest in (({'id': 'u', 'kind': 'text', 'text': 'INVENTED', 'anchor': at}, 0), ({'id': 'u', 'kind': 'text', 'text': 'INVENTED', 'anchor': {'byte_start': 5}}, 1)):
            g = grade.gates_for_file(grade.RouteFile({'file_id': 'syn/f.htm', 'units': [unit]}, raw, 'htm'), 'OK')
            self.assertEqual((g['dishonest'], g['boundary'], g['anchors_measured'], g['uncovered']), (dishonest, 0, False, None), unit)  # under an uncertain reading no mismatch and no omission is proven; a position that cannot be true is counted independently
        for html, text, certain in ((b'<datalist><p>Revenue</p></datalist><p>After</p>', 'After', True), (b'<datalist style="display:block"><p>Revenue</p></datalist><p>After</p>', 'Revenue After', True),
                                    (b'<noscript><p>Revenue</p></noscript><p>After</p>', 'After', True), (b'<ruby>kan<rp>(</rp><rt>ji</rt><rp>)</rp></ruby>', 'kanji', True), (b'<dialog><p>Revenue</p></dialog><p>After</p>', 'After', True),
                                    (b'<dialog open><p>Revenue</p></dialog><p>After</p>', 'Revenue After', True), (b'<details open><summary>Sum</summary><p>Revenue</p></details>', 'Sum Revenue', True),
                                    (b'<details><summary>Sum</summary><p>Revenue</p></details>', 'Sum Revenue', False), (b'<div display="none">Revenue</div>', 'Revenue', True)):
            v = anchor.Visible(html); self.assertEqual((' '.join(v.text.split()), v.certain), (text, certain), html)  # what the browser's own sheet never shows is not read (Chrome: r16_browser_facts); a closed <details> is not followed: uncertain
        pics = lambda html: grade.gates_for_file(grade.RouteFile({'file_id': 'syn/f.htm', 'units': []}, html, 'htm'), 'OK')['pictures']
        self.assertEqual((pics(b'<p>x</p><img src="a.png"><img width="0" src="c.png"><div hidden><img src="d.png"></div>'), pics(b'<style>img{opacity:1}</style><img src="a.png">')), (2, None))  # counted: picture elements in shown subtrees, no claim about size; nothing under an uncertain reading
        self.assertEqual([anchor.Visible(b'<html><head>' + sheet + b'</head><body><p>x</p></body></html>').certain for sheet in (b'<!-- <style>p{display:none}</style> -->', b'<style>p{display:none}</style>', b'<style>p{color:red}</style>')], [True, False, True])  # a commented-out sheet in the head applies nothing; a real one there is read

    def test_markup_the_browser_reads_its_own_way_is_read_that_way_or_not_certified(self):
        # own final pass of round 17, the classes of Codex R17-C4, every case against local Chrome (codex_probes_live/r17/final_pass): the scanner was certain and
        # wrong on <noscript> content read as tags, on a <script>, <style>, <title> or <head> the author displays, on a head holding body content, on templates and
        # the fallback content of embedded elements, on block elements read as inline, on a </p> that closes nothing, on cells with no table
        read = lambda html: (lambda v: (' '.join(v.text.split()), v.certain, len(v.pictures)))(anchor.Visible(html))
        for html, expect in ((b'<p>A</p><noscript><!-- </noscript><p>shown 10</p> --><p>B</p>', ('A shown 10 --> B', True, 0)), (b'<p>A</p><noscript><a title="</noscript>">N 10</a></noscript><p>B</p>', ('A ">N 10 B', True, 0)),
                             (b'<p>A</p><noscript style="display:block">N <b>10</b></noscript><p>B</p>', ('A B', True, 0)), (b'<p>A</p><noscript><img src="x.png"></noscript><img src="y.png"><p>B</p>', ('A B', True, 1)), (b'<p>A</p><noscript>N <p>10', ('A', True, 0))):
            self.assertEqual(read(html), expect, html)  # where scripts run — the reading this scanner states — a <noscript> holds raw text to its first closing tag and is never shown
        for html, certain in ((b'<p>A</p><script style="display:block">var x = 10;</script><p>B</p>', False), (b'<p>A</p><style style="display:block">.a{color:red}</style><p>B</p>', False), (b'<p>A</p><title style="display:block">T10</title><p>B</p>', False),
                              (b'<p>A</p><script style="display:inline">var x = 10;', False), (b'<p>A</p><style style="display:block">p{color:red}', False), (b'<p>A</p><title style="display:block">T10', False),
                              (b'<p>A</p><noframes style="display:none">N 10</noframes><p>B</p>', True), (b'<p>A</p><script style="d\\69 splay:block">x</script><p>B</p>', False), (b'<p>A</p><script style="display:var(--d)">x</script><p>B</p>', False),
                              (b'<html><head style="display:block"><title style="display:block">T10</title></head><body><p>B</p></body></html>', False), (b'<p>A</p><script style="display:none">var x = 10;</script><p>B</p>', True),
                              (b'<p>A</p><script style="color:red">var x = 10;</script><p>B</p>', True), (b'<html><head><title style="display:block">T10</title></head><body><p>B</p></body></html>', True), (b'<p>A</p><iframe style="display:block">I 10</iframe><p>B</p>', True)):
            self.assertEqual(read(html)[1], certain, html)  # the browser's own sheet hides them; a display from the author shows their literal text (script, style, title, noframes; inside a head only when the head is displayed too) — uncertain then. An <iframe> or <noembed> stays unshown
        for head, certain in ((b'Hello<title>T</title>', False), (b'<title>T</title><p>Hello 10</p>', False), (b'<title>T</title><img src="x.png">', False), (b'<meta charset="utf-8"/><title/>', False), (b'<title>My doc', False), (b'<noscript><p>N</p></noscript>', False),
                              (b'\n<!-- c --><meta name="a" content="x > y"><base href="/"><title>T</title><style>p{color:red}</style><script>var a;</script>\n', True), (b'<link rel="icon" href="x.ico">', True), (b'', True)):
            self.assertEqual(read(b'<html><head>' + head + b'</head><body><p>B</p></body></html>')[:2], ('B', certain), head)  # a head is skipped whole; what the parser would move into the body, or read to the end of the source (a <title/>), is not followed: uncertain
        for name in 'audio video canvas meter progress select object template svg math'.split():
            self.assertEqual(read(f'<p>A</p><{name}>F 10</{name}><p>B</p>'.encode())[1], False, name)  # content the page does not flow as its text, not modelled here
        self.assertEqual((read(b'<p>A</p><template><p>T</p>')[1], read(b'<p>A</p><button>F 10</button><label>G</label><p>B</p>')[:2]), (False, ('A F 10G B', True)))  # a template never closed, too; ordinary elements stay certain
        for name in 'aside dir fieldset figcaption figure hgroup legend listing main menu nav optgroup option search summary xmp'.split():
            self.assertEqual(read(f'x<{name}>F</{name}>y'.encode())[:2], ('x F y', True), name)  # elements the browser starts on a line of their own: a word boundary (sweep of every element of the HTML Standard's index)
        for html, expect in ((b'x<details open>F</details>y', ('x F y', True)), (b'x<dialog open>F</dialog>y', ('x F y', True)), (b'x<plaintext>F', ('x F', True)), (b'x<span>F</span>y', ('xFy', True)), (b'x<font size="2">F</font>y', ('xFy', True)),
                             (b'x</p>y', ('x y', True)), (b'x</br>y', ('x y', True)), (b'x</div>y', ('xy', True)), (b'x</span>y', ('xy', True)), (b'a<span style="display:none">x</p>y</span>b', ('ab', True)), (b'<p>x</p></p>y', ('x y', True)),
                             (b'x<td>F</td>y', ('x F y', False)), (b'x<tr><td>F</td></tr>y', ('x F y', False)), (b'x<tbody><tr><td>F</td></tr></tbody>y', ('x F y', False)),
                             (b'<table><td>F</td><td>G</td></table>', ('F G', True)), (b'<table><tr><div><td>F</td></div></tr></table>', ('F', True)), (b'<table><caption>C</caption><tr><td>F</td></tr></table>', ('C F', True)),
                             (b'<table><tr><td><table><tr><td>F</td></tr></table></td><td>G</td></tr></table>', ('F G', True))):
            self.assertEqual(read(html)[:2], expect, html)  # a </p> that closes no paragraph is an empty paragraph and a </br> a <br> (a break), any other stray closing tag nothing; a table part with no open table is dropped by the parser: uncertain
        for part in ('caption', 'colgroup', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th'):
            self.assertEqual((read(f'x<{part}></{part}>y'.encode())[1], read(f'<table><{part}></{part}></table><p>y</p>'.encode())[1]), (False, True), part)  # each part: dropped with no table (Chrome prints xy on one line), a part of its table inside one
        state = lambda html: (lambda v: (v.certain, v.struck_certain))(anchor.Visible(html))
        for html, expect in ((b'<p style="display:none">x<table><tr><td>y</td></tr></table>z', (False, True)), (b'<p style="visibility:hidden">x<table><tr><td>y</td></tr></table>z', (False, True)),
                             (b'<p style="text-decoration:line-through">x<table><tr><td>y</td></tr></table>z', (True, False)), (b'<p>x<table><tr><td>y</td></tr></table>z', (True, True)),
                             (b'<div style="display:none"><p>x<table><tr><td>y</td></tr></table></div>z', (True, True)), (b'<p style="display:none">x<div>y</div>z', (True, True))):
            self.assertEqual(state(html), expect, html)  # a file with no doctype is read in quirks mode, where a table does not close the open paragraph: what the paragraph itself hides or strikes then reaches the table (Chrome; 58 of the 60 development originals carry no doctype) — the reading depends on the mode: uncertain
        for html, expect in ((b'<table><font style="display:none"><tr><td>y</td></tr></font></table>', (False, True)), (b'<table><tr><span style="visibility:hidden"><td>y</td></span></tr></table>', (False, True)),
                             (b'<table><form style="display:none"><tr><td>y</td></tr></form></table>', (False, True)), (b'<table><s><tr><td>y</td></tr></s></table>', (True, False)),
                             (b'<table><font size="2"><tr><td>y</td></tr></font></table>', (True, True)), (b'<table><tbody style="display:none"><tr><td>y</td></tr></tbody></table>z', (True, True)),
                             (b'<table><tr style="display:none"><td>y</td></tr><tr><td>z</td></tr></table>', (True, True)), (b'<table><tr><td><font style="display:none">a</font>y</td></tr></table>', (True, True)),
                             (b'<div style="display:none"><table><font color="red"><tr><td>y</td></tr></font></table></div>z', (True, True))):
            self.assertEqual(state(html), expect, html)  # an element that is no part of a table, opened directly inside one, is moved out by the parser while the rows stay: what it hides or strikes does not reach them (Chrome shows y) — uncertain; one that changes nothing, a table part, a hiding element inside a cell are read as written

    def test_the_source_s_character_references_are_read_as_the_browser_reads_them(self):
        # Codex R17-C2: Python's html.unescape deletes numeric references to control characters and non-characters; the browser keeps the character. One development original
        # holds 18,146 of them; the tools keep them, so their units could not be placed
        for token, scalar in (('&#2;', '\x02'), ('&#7;', '\x07'), ('&#11;', '\x0b'), ('&#127;', '\x7f'), ('&#xFFFF;', '￿'), ('&amp;', '&'), ('&#65;', 'A'), ('&#x41;', 'A'), ('&#x80;', '€'),
                              ('&#0;', '�'), ('&#xD800;', '�'), ('&#x110000;', '�'), ('&amp;#2;', '&#2;'), ('&#X7F;', chr(0x7f)), ('&#x1f;', chr(0x1f))):
            self.assertEqual(anchor.Visible(('<p>A' + token + 'B</p>').encode()).text.strip(), 'A' + scalar + 'B', token)  # his controls: retained scalars; the standard's named, C1, null and surrogate rules; never decoded twice
        raw = b'<p>A&#2;B</p>'
        for text, dishonest in (('A\x02B', 0), ('AB', 1)):
            rf = grade.RouteFile({'file_id': 'syn/f.htm', 'units': [{'id': 'p', 'kind': 'text', 'text': text, 'anchor': {'byte_start': 3, 'byte_end_exclusive': len(raw) - 4}}]}, raw, 'htm')
            self.assertEqual(grade.gates_for_file(rf, 'OK')['dishonest'], dishonest, text)  # the route that keeps the character is honest; the one that drops it is not
        hidden = anchor.Visible(b'<p>x</p><div style="display:none">A&#2;B&#11;</div>'); self.assertEqual((hidden.text.strip(), hidden.hidden_chars), ('x', 3))  # counted among the hidden characters too; a referenced character the comparison form reads as whitespace (U+000B) is none
        self.assertEqual([anchor.Visible(b'<table>' + ref + b'<tr><td>x</td></tr></table>').certain for ref in (b'&#2;', b'&#11;', b'')], [False, True, True])  # and it is text where the browser would move it out of the table (whitespace moved changes nothing)
        placed = anchor.link(raw, [{'id': 'p', 'kind': 'text', 'text': 'A\x02B'}])['units'][0]
        self.assertEqual(placed['anchor'], {'byte_start': 3, 'byte_end_exclusive': 9})  # the linker places the tool's text again

    def test_the_same_picture_is_the_same_whole_identifier(self):
        # Codex R17-C3: two pictures with one base name in different folders overlapped, so the wrong picture could carry a block
        a = {'file': 'assets/original/chart.png', 'region': [0, 0, 100, 20]}
        self.assertEqual((grade.overlap(a, dict(a)), grade.overlap(a, dict(a, file='assets/unrelated/chart.png')), grade.overlap(a, dict(a, file='chart.png'))), (True, False, False))
        t = {'key_id': 'syn/S', 'file_id': 'source.png', 'type': 'structure', 'format': 'structure/png', 'split': 'development', 'anchor': a, 'fields': {'printed_text': 'Revenue 10', 'kind': 'paragraph'}, 'support': {}, 'alternatives': {}, 'excluded': set()}
        for asset, found in (('assets/original/chart.png', True), ('assets/unrelated/chart.png', False)):
            rf = grade.RouteFile({'file_id': 'source.png', 'units': [{'id': 'p', 'kind': 'text', 'text': 'Revenue 10', 'anchor': dict(a, file=asset)}]}, b'image', 'png')
            self.assertEqual(grade.Grader(t, rf).grade_structure() is not None, found, asset)
        page = {'page': 1, 'region': [0, 0, 100, 20]}; self.assertTrue(grade.overlap(page, dict(page)))  # a PDF's page boxes name no file: unchanged

    def test_a_free_standing_dash_before_a_number_is_settled_by_the_source(self):
        # Codex R17-C5: 'Preferred stock – 10,000,000 shares authorized:' is printed in a development filing; round 16 read every spaced dash as a minus and rejected
        # the positive phrase. The text alone cannot tell; the key's own span and the source can
        def lead(source, unit_text, want='10,000,000 shares authorized: see below.', pinned=None, head=b''):
            raw = head + b'<p>' + source.encode() + b'</p><table id="t"><tr><td>Total</td><td>5</td></tr></table>'; at = lambda x: {'byte_start': raw.index(x), 'byte_end_exclusive': raw.index(x) + len(x)}
            table = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': raw.index(b'<table'), 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Total', 'anchor': at(b'Total')}, {'r': 0, 'c': 1, 'text': '5', 'anchor': at(b'>5<')}]}
            t = {'key_id': 'syn/L', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': at(b'>5<'), 'table_anchor': table['anchor'], 'alternatives': {}, 'excluded': set(),
                 'fields': {'printed_value': '5', 'lead_in': want}, 'support': {'lead_in': {'anchors': [at((pinned or want).encode())]}}}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': [{'id': 'l', 'kind': 'text', 'text': unit_text, 'anchor': at(source.encode())}, table]}, raw, 'htm'))
            g.grade_cell(); return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'lead_in')
        real = 'Preferred stock – 10,000,000 shares authorized: see below.'
        self.assertEqual(lead(real, real), ('pass', None))  # the source prints the phrase at the key's own span with the same dash before it: the route kept the source's text
        self.assertEqual(lead('Preferred stock 10,000,000 shares authorized: see below.', real), ('fail', 'text'))  # the source prints no dash there: the route invented one
        self.assertEqual(lead('Preferred stock –10,000,000 shares authorized: see below.', 'Preferred stock –10,000,000 shares authorized: see below.'), ('fail', 'text'))  # a sign that touches its number stays protected
        self.assertEqual(lead('Rate: EURIBOR + 3.8% of the notional: see below.', 'Rate: EURIBOR + 3.8% of the notional: see below.', want='3.8% of the notional: see below.'), ('pass', None))  # a plus as an operator, the same way
        premiums = chr(0x201c) + 'Premiums' + chr(0x201d) + ' ' + chr(0x2014) + ' $12,100 million unfavorable: see below.'
        self.assertEqual(lead(premiums, premiums, want='12,100 million unfavorable: see below.'), ('pass', None))  # the dash before the currency symbol of the key's number, read back over the symbol
        ranges = 'Ranges: 11%-63% of the notional: see below.'
        self.assertEqual(lead(ranges, ranges, want='63% of the notional: see below.'), ('pass', None))  # a dash glued to other punctuation, the same way: the source prints it before the key's span
        self.assertEqual(lead('Ranges: 11% 63% of the notional: see below.', ranges, want='63% of the notional: see below.'), ('fail', 'text'))  # and an invented one fails
        self.assertEqual(lead(real, real.replace(chr(0x2013), '+')), ('fail', 'text'))  # the source prints a dash, the route a plus: the route's is not the source's — the stretch from the source's dash through the phrase must be printed
        self.assertEqual(lead(real, real, head=b'<style>p{display:block}</style>'), ('unresolved', 'numeric_boundary'))  # an uncertain reading of the source proves nothing
        self.assertEqual(lead(real, real, pinned=real), ('unresolved', 'numeric_boundary'))  # the key's span does not pin the phrase (it holds more): the source cannot say — neither a guessed negative nor a pass
        raw = b'<p>Results from Operations \xe2\x80\x93 2023 compared to 2022</p><table><tr><td>Revenue</td><td>1234</td></tr></table>'
        unit = lambda text: [{'id': 'd', 'kind': 'text', 'text': text, 'anchor': {'byte_start': 3, 'byte_end_exclusive': raw.index(b'</p>')}}]
        period = lambda units, part: self.synthetic_cell(raw, units, {'periods': [{'role': 'value', 'type': 'duration', 'parts': [part]}]}, {})['periods']
        at = {'byte_start': raw.index(b'2023 compared'), 'byte_end_exclusive': raw.index(b'</p>')}
        self.assertEqual(period(unit('Results from Operations – 2023 compared to 2022'), {'text': '2023 compared to 2022', 'anchor': at}), ('pass', None))  # a period part at its own anchor: the source decides
        self.assertEqual(period(unit('Results from Operations – 2023 compared to 2022'), {'text': '2023 compared to 2022'}), ('unresolved', 'numeric_boundary'))  # found by text only: open
        self.assertEqual(period(unit('Results from Operations – 2023 compared to 2022') + [{'id': 'e', 'kind': 'text', 'text': 'In 2023 compared to 2022', 'anchor': {'byte_start': 3, 'byte_end_exclusive': 10}}], {'text': '2023 compared to 2022'}), ('pass', None))  # a plain match elsewhere needs no arbiter
        raw3 = b'<p>Results from Operations \xe2\x80\x93 2023 compared to 2022</p><table><tr><td>Revenue 2015<sup>1</sup></td><td>1234</td></tr></table><p>1 a note</p>'; sp = lambda x: {'byte_start': raw3.index(x), 'byte_end_exclusive': raw3.index(x) + len(x)}
        tb = {'id': 't', 'kind': 'table', 'anchor': sp(b'<table>'), 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue 2015 1', 'anchor': sp(b'Revenue 2015<sup>1</sup>')}, {'r': 0, 'c': 1, 'text': '1234', 'anchor': sp(b'1234')}]}
        rows = self.synthetic_cell(raw3, [{'id': 'd', 'kind': 'text', 'text': raw3[3:raw3.index(b'</p>')].decode(), 'anchor': {'byte_start': 3, 'byte_end_exclusive': raw3.index(b'</p>')}}, {'id': 'n', 'kind': 'footnote', 'text': '1 a note', 'anchor': sp(b'1 a note')}],
                                   {'periods': [{'role': 'value', 'type': 'duration', 'parts': [{'text': '2023 compared to 2022'}]}], 'footnote_markers': [{'marker_text': '1', 'anchor': sp(b'<sup>1</sup>'), 'note_text': '1 a note', 'note_anchor': sp(b'1 a note')}]}, {}, tb)
        self.assertEqual((rows['periods'], rows['footnote_markers']), (('unresolved', 'numeric_boundary'), ('pass', None)))  # the open question is the field's own: the next field is judged afresh
        xml = b'<r><holding><title>Series B - 5 shares</title><qty>10</qty></holding></r>'; xs = lambda x: {'byte_start': xml.index(x), 'byte_end_exclusive': xml.index(x) + len(x)}
        fields = [{'id': n, 'kind': 'field', 'name': n, 'text': x.decode(), 'anchor': xs(x), 'path': ['r', 'holding'], 'group': {'index': 1, 'count': 1, 'at': xml.index(b'<holding>')}} for n, x in (('title', b'Series B - 5 shares'), ('qty', b'10'))]
        def xml_unit(declared):
            t = {'key_id': 'syn/X', 'file_id': 'syn/a.xml', 'type': 'cell', 'format': 'cell/xml', 'split': 'development', 'anchor': xs(b'10'), 'fields': {'printed_value': '10', 'row_label': 'qty', 'unit_printed': '5 shares'},
                 'support': {'unit_printed': {'anchors': [xs(declared)]}}, 'alternatives': {}, 'excluded': set()}
            g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/a.xml', 'units': copy.deepcopy(fields)}, xml, 'xml')); g.grade_cell(); return next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'unit_printed')
        g = grade.Grader({'key_id': 'syn/X', 'file_id': 'syn/a.xml', 'fields': {}, 'alternatives': {}, 'support': {}, 'excluded': set()}, grade.RouteFile({'file_id': 'syn/a.xml', 'units': []}, xml, 'xml'))
        self.assertEqual((g.printed(['x - 10 units', 'of 10 units'], '10 units'), g.boundary, g.printed(['x - 10 units'], '10 units'), g.boundary), (True, False, True, True))  # among several texts a plain match settles it; only an undecided one leaves the question open
        self.assertEqual((xml_unit(b'5 shares'), xml_unit(b'Series B - 5 shares')), (('pass', None), ('unresolved', 'numeric_boundary')))  # an XML unit, the same way: the key's own span decides, a wider one cannot
        raw4 = b'<table><tr><td>Revenue</td><td>10</td><td><span>up</span><span>to</span></td><td>20</td></tr></table>'; s4 = lambda x: {'byte_start': raw4.index(x), 'byte_end_exclusive': raw4.index(x) + len(x)}
        tb4 = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw4)}, 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': s4(b'Revenue')}, {'r': 0, 'c': 1, 'text': '10', 'anchor': s4(b'10')},
              {'r': 0, 'c': 2, 'text': 'up', 'anchor': s4(b'up')}, {'r': 0, 'c': 2, 'text': 'to', 'anchor': s4(b'to')}, {'r': 0, 'c': 3, 'text': '20', 'anchor': s4(b'20')}]}
        rows = self.synthetic_cell(raw4, [], {'range': {'partner': {'printed_value': '20', 'anchor': s4(b'20')}, 'evidence': [{'text': 'up to', 'anchor': s4(b'<span>up</span><span>to</span>')}]}}, {}, tb4, value=b'10')
        self.assertEqual(rows['range'], ('unresolved', 'adjacency'))  # range evidence read through the same method: pieces that touch where the key prints a space stay unresolved, as before


if __name__ == '__main__':
    unittest.main()
