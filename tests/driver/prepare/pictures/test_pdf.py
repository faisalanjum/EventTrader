"""PDF pages as picture inputs (pictures/pdf.py; owner, Oct 10: minimal native PDF integration, OCR last). Expected values come from each fixture's own
definition (page sizes in points, rotation, the colours its appearance streams paint) and PDFium's documented scale rule, never from the adapter. PDFs are
made here with pypdfium2's own document API, or are the three files in cases/ made once with pypdf 5.4.0 (make_fixtures_v1.py in
prepare_work/extraction_closeout_20261010/ocr_pdf_integration_v1). Fake readers only (test_join.fakes): this is the connection, not OCR accuracy."""
import ctypes
import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image

from driver.prepare.get import archive
from driver.prepare.pictures import join, pdf, readers
from tests.driver.prepare.pictures.test_join import fakes

CASES = Path(__file__).parent / 'cases'
sha = lambda b: hashlib.sha256(b).hexdigest()


def made(*pages, rotate=None):  # a PDF of blank pages of these sizes (points), by PDFium's own document API
    doc = pdfium.PdfDocument.new()
    try:
        for k, (w, h) in enumerate(pages):
            page = doc.new_page(w, h)
            if rotate and k in rotate: page.set_rotation(rotate[k])
            page.close()
        b = io.BytesIO(); doc.save(b); return b.getvalue()
    finally: doc.close()


def px(w_pt, h_pt):  # PDFium's render size at Chandra 0.2.0's rule: max(192 DPI, 1,024 px on the shorter side)
    s = max(1024 / min(w_pt, h_pt) * 72, 192) / 72
    return round(w_pt * s), round(h_pt * s)


class Pages(unittest.TestCase):
    def run_pdf(self, data, fid='0000000000-00-000000/x.pdf'):
        return pdf.pages(data, fid, sha(data))

    def test_every_page_in_order_with_its_identity_and_exact_bytes(self):
        data = made((100, 100), (200, 100), (100, 300))
        route, got = self.run_pdf(data)
        self.assertEqual((route['status'], route['error']), ('OK', None))
        self.assertEqual([(u['id'], u['kind'], u['page']) for u in route['units']], [('p1', 'image', 1), ('p2', 'image', 2), ('p3', 'image', 3)])
        for u, size in zip(route['units'], [px(100, 100), px(200, 100), px(100, 300)]):
            i = u['input']
            self.assertEqual((i['how'], i['member_sha256'], i['page'], i['flatten']), ('pdf_page', sha(data), u['page'], 'nothing to flatten'))
            self.assertEqual(sha(got[i['input_sha256']]), i['input_sha256'])
            with Image.open(io.BytesIO(got[i['input_sha256']])) as im: self.assertEqual((im.size, im.mode), (size, 'RGB'))
            self.assertEqual(tuple(i['size']), size)
        sizes = {1: [100, 100], 2: [200, 100], 3: [100, 300]}   # the existing public anchor contract: one-based page, whole displayed page in points
        self.assertEqual((route['pages'], [u['anchor'] for u in route['units']], [u['page_index'] for u in route['units']]),
                         (sizes, [{'page': p, 'region': [0, 0, *wh]} for p, wh in sizes.items()], [0, 1, 2]))
        self.assertEqual(route['route']['settings'], pdf.SETTINGS)

    def test_a_rotated_page_is_rendered_as_shown(self):
        route, got = self.run_pdf(made((200, 100), (200, 100), rotate={1: 90}))
        self.assertEqual([(u['rotation'], tuple(u['input']['size'])) for u in route['units']], [(0, px(200, 100)), (90, px(100, 200))])

    def test_forms_and_annotations_are_drawn_and_recorded(self):
        data = (CASES / 'forms_annotation.pdf').read_bytes()
        route, got = self.run_pdf(data)
        u = route['units'][0]
        self.assertEqual((route['status'], route['form_type'], u['annotations'], u['input']['flatten']), ('OK', 'AcroForm', 2, 'flattened'))
        s = 1024 / 100  # the page is 200 x 100 pt: 10.24 px per pt; PDF y runs upwards
        at = lambda x, y: (round(x * s), round((100 - y) * s))
        with Image.open(io.BytesIO(got[u['input']['input_sha256']])) as im:
            self.assertEqual(im.getpixel(at(30, 20)), (255, 0, 0))      # the Square annotation's appearance
            self.assertEqual(im.getpixel(at(120, 20)), (0, 0, 255))     # the text field's widget appearance
            self.assertEqual(im.getpixel(at(80, 80)), (255, 255, 255))  # positive control: page background elsewhere

    def test_an_xfa_form_is_unsupported_never_a_plain_raster(self):
        route, got = self.run_pdf((CASES / 'xfa.pdf').read_bytes())
        self.assertEqual((route['status'], route['form_type'], got), ('PARTIAL', 'XFA foreground', {}))
        self.assertIn('XFA', route['units'][0]['input']['error'])

    def test_a_flatten_failure_leaves_the_page_without_input(self):
        real = pdfium_c.FPDFPage_Flatten
        pdfium_c.FPDFPage_Flatten = lambda page, flag: pdfium_c.FLATTEN_FAIL
        try: route, got = self.run_pdf(made((100, 100)))
        finally: pdfium_c.FPDFPage_Flatten = real
        self.assertEqual((route['status'], got), ('PARTIAL', {}))
        self.assertIn('flatten', route['units'][0]['input']['error'])
        self.assertEqual(self.run_pdf(made((100, 100)))[0]['status'], 'OK')   # positive control: the native flatten

    def test_invalid_and_encrypted_documents_fail_with_pdfiums_message(self):
        for data, says in ((b'%PDF-1.4\nnot really a pdf\n', 'Data format error'), ((CASES / 'encrypted.pdf').read_bytes(), 'Incorrect password')):
            route, got = self.run_pdf(data)
            self.assertEqual((route['status'], route['units'], got), ('FAILED', [], {}))
            self.assertIn(says, route['error'])

    def test_wrong_source_bytes_are_refused(self):
        data = made((100, 100))
        with self.assertRaises(ValueError): pdf.pages(data, 'x.pdf', '0' * 64)

    def test_the_document_is_closed_and_machine_faults_stop(self):
        one, two = made((100, 100)), made((100, 100), (100, 100))   # made first: only the adapter's own documents are counted below
        closed, real_close, real_render = [], pdfium.PdfDocument.close, pdfium.PdfPage.render
        pdfium.PdfDocument.close = lambda doc, *a, **k: (closed.append(True), real_close(doc, *a, **k))[1]
        try:
            pdfium.PdfPage.render = lambda page, **k: (_ for _ in ()).throw(MemoryError('fake: no memory'))
            with self.assertRaises(MemoryError): self.run_pdf(one)
            self.assertEqual(closed, [True])
            pdfium.PdfPage.render = lambda page, **k: (_ for _ in ()).throw(pdfium.PdfiumError('fake: page failed'))
            route, got = self.run_pdf(two)
            self.assertEqual(closed, [True, True])
            self.assertEqual((route['status'], [u['input'].get('error', '')[:7] for u in route['units']], got), ('PARTIAL', ['PDFium:', 'PDFium:'], {}))
        finally: pdfium.PdfDocument.close, pdfium.PdfPage.render = real_close, real_render
        self.assertEqual(self.run_pdf(made((100, 100)))[0]['status'], 'OK')   # positive control after restoring


class ThroughJoin(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.folder = t.name; self.calls = []

    def test_pages_reach_the_readers_archive_and_records_as_occurrences(self):
        data = made((100, 100), (200, 100), (100, 100))   # pages 0 and 2 render to the same bytes: one input, two occurrences
        route, got = pdf.pages(data, 'f/x.pdf', sha(data))
        _, out = join.join(route, got, self.folder, fakes(self.calls))
        self.assertEqual([e['occurrence'] for e in out], ['f/x.pdf#p1', 'f/x.pdf#p2', 'f/x.pdf#p3'])
        for e, u in zip(out, route['units']):
            s = u['input']['input_sha256']
            self.assertEqual(archive.load_blob(e['archive']['root'], s), got[s])
            self.assertEqual({r['image_sha256'] for r in e['records'].values()}, {s})
            self.assertIn('packet', e)
        self.assertEqual(len({h for _, h in self.calls}), 2)            # each distinct page image read once per reader

    def test_reader_failure_and_cutoff_stay_explicit(self):
        data = made((100, 100), (200, 100))
        route, got = pdf.pages(data, 'f/x.pdf', sha(data))
        _, out = join.join(route, got, self.folder, fakes(self.calls, tokens=readers.MAX_TOKENS, fail_ox={route['units'][1]['input']['input_sha256']}))
        self.assertEqual([e['records']['chandra']['status'] for e in out], ['cut off', 'cut off'])
        self.assertEqual([e['records']['ox']['status'] for e in out], ['complete', 'error'])
        self.assertTrue(all('cut off' in e['flags'] for e in out))

    def test_a_page_whose_bytes_are_not_its_recorded_size_stops(self):
        data = made((100, 100))
        route, got = pdf.pages(data, 'f/x.pdf', sha(data))
        route['units'][0]['input']['size'] = [1, 1]
        with self.assertRaises(ValueError): join.join(route, got, self.folder, fakes(self.calls))
        route, got = pdf.pages(data, 'f/x.pdf', sha(data))                # positive control: the recorded size
        self.assertIn('packet', join.join(route, got, os.path.join(self.folder, 'ok'), fakes(self.calls))[1][0])



def geometry_pdf(rotation):  # media box 300x200, crop box (10,20)-(210,120), a red rectangle drawn at x 30-70, y 40-60 and a URI link over it (PDFium's own API)
    doc = pdfium.PdfDocument.new()
    try:
        page = doc.new_page(300, 200); page.set_cropbox(10, 20, 210, 120); page.set_rotation(rotation)
        obj = pdfium_c.FPDFPageObj_CreateNewRect(30, 40, 40, 20); pdfium_c.FPDFPageObj_SetFillColor(obj, 255, 0, 0, 255)
        pdfium_c.FPDFPath_SetDrawMode(obj, pdfium_c.FPDF_FILLMODE_ALTERNATE, 0); pdfium_c.FPDFPage_InsertObject(page.raw, obj); pdfium_c.FPDFPage_GenerateContent(page.raw)
        annot = pdfium_c.FPDFPage_CreateAnnot(page.raw, pdfium_c.FPDF_ANNOT_LINK)
        pdfium_c.FPDFAnnot_SetRect(annot, pdfium_c.FS_RECTF(30, 60, 70, 40)); pdfium_c.FPDFAnnot_SetURI(annot, b'https://example.invalid/g'); pdfium_c.FPDFPage_CloseAnnot(annot)
        page.close(); b = io.BytesIO(); doc.save(b); return b.getvalue()
    finally: doc.close()


class Relations(unittest.TestCase):  # v2 (root ROOT_PDF_REVIEW_v1): native links, source geometry, attachments, notes and field values
    def run_pdf(self, data):
        return pdf.pages(data, 'f/x.pdf', sha(data))

    def test_links_keep_their_native_targets_and_unsupported_ones_stay_unprocessed(self):
        route, got = self.run_pdf((CASES / 'links.pdf').read_bytes())
        links = route['units'][0]['links']
        self.assertEqual([l['rect_pt'] for l in links], [[10, 10, 50, 30], [60, 10, 100, 30], [110, 10, 150, 30], [160, 10, 195, 30]])
        self.assertEqual(links[0]['uri'], 'https://example.invalid/a')
        self.assertEqual(links[1]['dest'], {'page': 2, 'page_index': 1, 'view': 'XYZ', 'x': 5.0, 'y': 80.0, 'zoom': None})
        self.assertNotIn('uri', links[2]); self.assertIn('unprocessed', links[2])
        self.assertEqual(links[3].get('unprocessed'), 'destination not found')
        self.assertEqual(route['units'][1]['links'], [])                                   # positive control: a page without links
        self.assertEqual((route['status'], [(u['page'], u['index']) for u in route['unprocessed']]), ('PARTIAL', [(1, 2), (1, 3)]))
        self.assertEqual(len(got), 2)                                                     # every page still has its input
        notes = [a for a in route['units'][0]['annotation_records'] if a['subtype'] == 'text']
        self.assertEqual([(a['rect_pt'], a['contents']) for a in notes], [([10, 60, 30, 80], 'source note')])

    def test_attachments_are_inventoried_and_unprocessed(self):
        route, _ = self.run_pdf((CASES / 'attachment.pdf').read_bytes())
        self.assertEqual((route['status'], route['attachments']), ('PARTIAL', [{'index': 0, 'name': 'note.txt'}]))
        self.assertEqual([u['what'] for u in route['unprocessed']], ['attachment'])
        route, _ = self.run_pdf(made((100, 100)))                                          # positive control
        self.assertEqual((route['status'], route['attachments'], route['unprocessed']), ('OK', [], []))

    def test_form_field_values_and_annotations_are_kept(self):
        route, _ = self.run_pdf((CASES / 'forms_annotation.pdf').read_bytes())
        recs = route['units'][0]['annotation_records']
        self.assertEqual([(a['subtype'], a['rect_pt']) for a in recs], [('square', [10, 10, 50, 30]), ('widget', [100, 10, 140, 30])])
        self.assertEqual((recs[1]['field'], recs[1]['value']), ('amount', '42'))

    def test_source_geometry_crop_origin_and_all_right_angle_rotations(self):
        s = 1024 / 100   # the crop box is 200 x 100 pt; the red rectangle is crop x 20-60, y 20-40 (crop origin 10,20; PDF y upwards)
        want = {0: (2048, 1024, [20, 60, 60, 80]), 90: (1024, 2048, [20, 20, 40, 60]), 180: (2048, 1024, [140, 20, 180, 40]), 270: (1024, 2048, [60, 140, 80, 180])}
        for rotation, (w, h, box) in want.items():
            with self.subTest(rotation=rotation):
                route, got = self.run_pdf(geometry_pdf(rotation)); u = route['units'][0]
                self.assertEqual((u['rotation'], u['bbox_pt'], u['cropbox_pt'], u['mediabox_pt']), (rotation, [10, 20, 210, 120], [10, 20, 210, 120], [0, 0, 300, 200]))
                self.assertEqual(tuple(u['input']['size']), (w, h))
                shown = [200, 100] if rotation in (0, 180) else [100, 200]                     # the displayed crop box, rotation applied
                self.assertEqual((route['pages'], u['anchor']), ({1: shown}, {'page': 1, 'region': [0, 0, *shown]}))
                link = u['links'][0]
                self.assertEqual((link['rect_pt'], link['uri']), ([30, 40, 70, 60], 'https://example.invalid/g'))
                for got_v, want_v in zip(link['rect_px'], box): self.assertLessEqual(abs(got_v - want_v * s), 1)
                x, y = (link['rect_px'][0] + link['rect_px'][2]) // 2, (link['rect_px'][1] + link['rect_px'][3]) // 2
                with Image.open(io.BytesIO(got[u['input']['input_sha256']])) as im:
                    self.assertEqual(im.getpixel((x, y)), (255, 0, 0))                       # the drawn rectangle is where PDFium maps the link
                    self.assertEqual(im.getpixel((5, 5)), (255, 255, 255))

    def test_unknown_native_values_and_form_failures_are_never_success(self):
        real_flat, real_init = pdfium_c.FPDFPage_Flatten, pdfium.PdfDocument.init_forms
        pdfium_c.FPDFPage_Flatten = lambda page, flag: 7
        try: route, got = self.run_pdf(made((100, 100)))
        finally: pdfium_c.FPDFPage_Flatten = real_flat
        self.assertEqual((route['status'], got), ('PARTIAL', {})); self.assertIn('7', route['units'][0]['input']['error'])
        pdfium.PdfDocument.init_forms = lambda doc, *a, **k: (_ for _ in ()).throw(pdfium.PdfiumError('fake: forms failed'))
        try: route, got = self.run_pdf(made((100, 100)))
        finally: pdfium.PdfDocument.init_forms = real_init
        self.assertEqual((route['status'], route['units'], got), ('FAILED', [], {})); self.assertIn('forms failed', route['error'])

    def test_the_images_are_closed_when_encoding_fails(self):
        data, closed, real_save, real_close = made((100, 100)), [], Image.Image.save, Image.Image.close
        Image.Image.save = lambda im, *a, **k: (_ for _ in ()).throw(OSError('fake: cannot write'))
        Image.Image.close = lambda im: (closed.append(im.mode), real_close(im))[1]
        try:
            with self.assertRaises(OSError): self.run_pdf(data)
        finally: Image.Image.save, Image.Image.close = real_save, real_close
        self.assertIn('RGB', closed); self.assertGreaterEqual(len(closed), 2)               # the page bitmap's image and its RGB copy
        self.assertEqual(self.run_pdf(data)[0]['status'], 'OK')                            # positive control


class NativeBoundary(unittest.TestCase):  # root ROOT_PDF_REVIEW_v2: native destination views, and every declared native failure return kept as a failure
    def run_pdf(self, data):
        return pdf.pages(data, 'f/x.pdf', sha(data))

    def test_destination_views_and_parameters(self):
        route, _ = self.run_pdf((CASES / 'views.pdf').read_bytes())
        links = route['units'][0]['links']
        self.assertEqual([l.get('dest') for l in links[:5]], [
            {'page': 2, 'page_index': 1, 'view': 'Fit', 'params': []},
            {'page': 2, 'page_index': 1, 'view': 'FitH', 'params': [80.0]},
            {'page': 2, 'page_index': 1, 'view': 'FitR', 'params': [11.0, 12.0, 73.0, 94.0]},
            {'page': 2, 'page_index': 1, 'view': 'XYZ', 'x': None, 'y': None, 'zoom': None},      # null is not zero
            {'page': 2, 'page_index': 1, 'view': 'XYZ', 'x': 0.0, 'y': 0.0, 'zoom': None}])
        self.assertEqual((links[5].get('dest'), links[5].get('unprocessed')), (None, 'destination not found'))   # a link with no target
        self.assertEqual([(u['what'], u['index']) for u in route['unprocessed']], [('link', 5)])

    def failing(self, name, value, data):  # the module's run with one native call returning its declared failure value
        real = getattr(pdfium_c, name); setattr(pdfium_c, name, lambda *a: value)
        try: return self.run_pdf(data)
        finally: setattr(pdfium_c, name, real)

    def test_declared_native_failures_are_never_known_values(self):
        forms, links = (CASES / 'forms_annotation.pdf').read_bytes(), geometry_pdf(0)
        ok_forms, ok_links = self.run_pdf(forms)[0], self.run_pdf(links)[0]                   # positive controls: the same sources read
        self.assertEqual((ok_forms['status'], ok_links['status']), ('OK', 'OK'))
        self.assertEqual(ok_forms['units'][0]['annotation_records'][0]['rect_pt'], [10, 10, 50, 30])
        self.assertEqual(ok_links['units'][0]['links'][0]['uri'], 'https://example.invalid/g')
        route, _ = self.failing('FPDFPage_GetAnnot', None, forms)
        self.assertEqual((route['status'], [a.get('error', '')[:6] for a in route['units'][0]['annotation_records']]), ('PARTIAL', ['PDFium', 'PDFium']))
        route, _ = self.failing('FPDFAnnot_GetRect', 0, forms)
        self.assertEqual((route['status'], [a['rect_pt'] for a in route['units'][0]['annotation_records']]), ('PARTIAL', [None, None]))
        route, _ = self.failing('FPDFLink_GetAnnotRect', 0, links)
        self.assertEqual((route['status'], route['units'][0]['links'][0]['rect_pt'], route['units'][0]['links'][0]['rect_px']), ('PARTIAL', None, None))
        route, got = self.failing('FPDF_PageToDevice', 0, links)
        self.assertEqual((route['status'], route['units'][0]['links'][0]['rect_px'], len(got)), ('PARTIAL', None, 1))
        route, _ = self.failing('FPDFAction_GetURIPath', 0, links)
        self.assertEqual((route['status'], route['units'][0]['links'][0].get('uri'), route['units'][0]['links'][0].get('unprocessed')), ('PARTIAL', None, 'URI unreadable'))
        for u in route['unprocessed']: self.assertIn('why', u)
        route, _ = self.failing('FPDFAnnot_GetSubtype', pdfium_c.FPDF_ANNOT_UNKNOWN, forms)   # added with the fix: the subtype's declared failure value
        self.assertEqual((route['status'], len([u for u in route['unprocessed'] if u['what'] == 'annotation'])), ('PARTIAL', 2))

    def test_the_rgb_image_is_closed_when_a_fault_follows_its_creation(self):
        data, copies, closed = geometry_pdf(0), [], []
        real_close, real_convert, real_map = Image.Image.close, Image.Image.convert, pdfium_c.FPDF_PageToDevice
        Image.Image.convert = lambda im, *a, **k: (lambda out: (copies.append(out), out)[1])(real_convert(im, *a, **k))
        Image.Image.close = lambda im: (closed.append(im), real_close(im))[1]
        pdfium_c.FPDF_PageToDevice = lambda *a: (_ for _ in ()).throw(MemoryError('fake: no memory'))
        try:
            with self.assertRaises(MemoryError): self.run_pdf(data)
        finally: Image.Image.close, Image.Image.convert, pdfium_c.FPDF_PageToDevice = real_close, real_convert, real_map
        self.assertEqual(len(copies), 1); self.assertTrue(any(im is copies[0] for im in closed))   # the RGB copy itself, made before the fault
        self.assertEqual(self.run_pdf(data)[0]['status'], 'OK')                              # positive control



class StringBoundary(unittest.TestCase):  # root OCR_PDF_STRING_BOUNDARY: PDFium's two-call UTF-16 getters - 2 bytes = empty/missing, 0 = error
    GETTERS = (('FPDFAnnot_GetStringValue', 'links.pdf', 4, 'contents'), ('FPDFAnnot_GetFormFieldName', 'forms_annotation.pdf', 1, 'field'),
               ('FPDFAnnot_GetFormFieldValue', 'forms_annotation.pdf', 1, 'value'))   # each getter on a record whose value is not empty ('source note', amount, 42)

    def run_pdf(self, data, name=None, fake=None):
        if name is None: return pdf.pages(data, 'f/x.pdf', sha(data))
        real = getattr(pdfium_c, name); setattr(pdfium_c, name, fake(real))
        try: return pdf.pages(data, 'f/x.pdf', sha(data))
        finally: setattr(pdfium_c, name, real)

    def test_native_strings_are_kept_exactly_and_an_empty_one_is_absent(self):
        route, got = self.run_pdf((CASES / 'forms_annotation.pdf').read_bytes())
        recs = route['units'][0]['annotation_records']
        self.assertEqual((route['status'], recs[0]['contents'], recs[1]['field'], recs[1]['value'], route['unprocessed']), ('OK', None, 'amount', '42', []))
        text = 'a\x00b\x00'.encode('utf-16-le') + b'\x00\x00'                               # a native string holding NULs, one at its end, then its terminator
        def native(real):
            def fn(*a):
                if a[-2] is None or a[-1] < len(text): return len(text)
                ctypes.memmove(a[-2], text, len(text)); return len(text)
            return fn
        route, _ = self.run_pdf((CASES / 'forms_annotation.pdf').read_bytes(), 'FPDFAnnot_GetStringValue', native)
        self.assertEqual((route['status'], route['units'][0]['annotation_records'][0]['contents']), ('OK', 'a\x00b\x00'))

    def test_a_failed_first_or_second_read_is_unprocessed_and_siblings_stay(self):
        first = lambda real: (lambda *a: 0)                                                          # PDFium's error return
        second = lambda real: (lambda *a: real(*a) if a[-2] is None else real(*a) - 2)               # a second read shorter than the first said
        for name, case, k, key in self.GETTERS:
            data = (CASES / case).read_bytes(); good, inputs = self.run_pdf(data)
            self.assertIsNotNone(good['units'][0]['annotation_records'][k][key])                    # positive control: the value is there
            for how in (first, second):
                with self.subTest(getter=name, read='first' if how is first else 'second'):
                    route, got = self.run_pdf(data, name, how)
                    rec = route['units'][0]['annotation_records'][k]
                    self.assertEqual((route['status'], rec[key], len(got)), ('PARTIAL', None, len(inputs)))
                    self.assertIn(key, rec['unprocessed'])
                    if key == 'field': self.assertEqual(rec['value'], '42')                         # its sibling still read
                    if key == 'value': self.assertEqual(rec['field'], 'amount')



class PageAttachment(unittest.TestCase):  # root OCR_PDF_PAGE_ATTACHMENT: a file attached by a page annotation is listed as unread, as a document one is
    def run_pdf(self, name):
        data = (CASES / name).read_bytes(); return pdf.pages(data, 'f/x.pdf', sha(data))

    def test_a_page_attachment_is_named_and_unread_and_its_siblings_stay(self):
        route, got = self.run_pdf('page_attachment.pdf')
        recs = route['units'][0]['annotation_records']
        self.assertEqual((route['status'], route['attachments'], len(got)), ('PARTIAL', [], 2))
        self.assertEqual((recs[0]['subtype'], recs[0]['attachment']), ('fileattachment', {'name': 'qualification.txt'}))
        self.assertEqual((recs[1]['subtype'], recs[1]['contents'], 'unprocessed' in recs[1]), ('text', 'source note', False))
        self.assertEqual([(u['what'], u['page'], u['index']) for u in route['unprocessed']], [('annotation', 1, 0)])
        self.assertIn('content unread', route['unprocessed'][0]['why'])
        blank = made((100, 100)); none, _ = pdf.pages(blank, 'f/y.pdf', sha(blank))            # positive control: no attachment anywhere
        self.assertEqual((none['status'], none['unprocessed']), ('OK', []))

    def test_document_and_page_attachments_are_each_kept(self):
        doc_only, _ = self.run_pdf('attachment.pdf')                                            # the existing document-level control
        self.assertEqual([u['what'] for u in doc_only['unprocessed']], ['attachment'])
        both, _ = self.run_pdf('both_attachment.pdf')
        self.assertEqual((both['attachments'], both['units'][0]['annotation_records'][0]['attachment']), ([{'index': 0, 'name': 'qualification.txt'}], {'name': 'qualification.txt'}))
        self.assertEqual(sorted(u['what'] for u in both['unprocessed']), ['annotation', 'attachment'])   # one record per source occurrence, no merging

    def test_a_missing_handle_or_name_stays_unread(self):
        route, got = self.run_pdf('broken_attachment.pdf')
        recs = route['units'][0]['annotation_records']
        self.assertEqual((route['status'], recs[0]['attachment'], recs[1]['attachment'], len(got)), ('PARTIAL', None, {'name': None}, 1))
        self.assertIn('no attached file', recs[0]['unprocessed']); self.assertIn('name unread', recs[1]['unprocessed'])



class Boxes(unittest.TestCase):  # root OCR_PDF_BOX_CORRECTION (Fable F1-F3): inherited page boxes through flattening, own-box values, a widget with no form
    def run_pdf(self, name):
        data = (CASES / name).read_bytes(); return pdf.pages(data, 'f/x.pdf', sha(data))

    def test_inherited_boxes_render_exactly_as_their_direct_twins(self):  # the direct twin declares the same boxes on the page itself
        for pair in ('media', 'wide', 'crop', 'rot'):
            with self.subTest(pair=pair):
                (inh, gi), (dr, gd) = self.run_pdf(f'boxes_{pair}_inh.pdf'), self.run_pdf(f'boxes_{pair}_dir.pdf')
                self.assertEqual((inh['status'], dr['status'], inh['pages']), ('OK', 'OK', dr['pages']))
                for a, b in zip(inh['units'], dr['units']):
                    self.assertEqual((a['anchor'], a['bbox_pt'], a['rotation'], a['input']['size']), (b['anchor'], b['bbox_pt'], b['rotation'], b['input']['size']))
                    self.assertEqual(a['input']['input_sha256'], b['input']['input_sha256'])          # the same pixels
                    self.assertEqual([l['rect_px'] for l in a['links']], [l['rect_px'] for l in b['links']])
        wide = self.run_pdf('boxes_wide_inh.pdf')[0]['units'][0]
        self.assertEqual((wide['size_pt'], wide['input']['size']), ([1224, 792], list(px(1224, 792))))  # not Letter (3264 x 2112 at 192 DPI): x 900-940 stays on the page

    def test_page_boxes_are_the_pages_own_or_none(self):
        own = lambda name: [(u['mediabox_pt'], u['cropbox_pt'], u['bbox_pt']) for u in self.run_pdf(name)[0]['units']][0]
        self.assertEqual(own('boxes_media_inh.pdf'), (None, None, [0, 0, 300, 200]))                   # inherited: not declared on the page
        self.assertEqual(own('boxes_media_dir.pdf'), ([0, 0, 300, 200], None, [0, 0, 300, 200]))
        self.assertEqual(own('boxes_crop_inh.pdf'), ([0, 0, 300, 200], None, [10, 20, 210, 120]))
        self.assertEqual(own('boxes_crop_dir.pdf'), ([0, 0, 300, 200], [10, 20, 210, 120], [10, 20, 210, 120]))

    def test_a_frame_changed_by_flattening_is_an_error_never_a_picture(self):
        real = pdfium_c.FPDFPage_Flatten
        for name, box in (('size', (0, 0, 612, 792)), ('shifted origin, same size', (10, 10, 310, 210))):
            def flatten(page, flag, box=box):
                rc = real(page, flag); pdfium_c.FPDFPage_SetMediaBox(page, *box); pdfium_c.FPDFPage_SetCropBox(page, *box); return rc
            pdfium_c.FPDFPage_Flatten = flatten
            try: route, got = self.run_pdf('boxes_media_dir.pdf')
            finally: pdfium_c.FPDFPage_Flatten = real
            with self.subTest(change=name):
                self.assertEqual((route['status'], got), ('PARTIAL', {})); self.assertIn('frame', route['units'][0]['input']['error'])
        self.assertEqual(self.run_pdf('boxes_media_dir.pdf')[0]['status'], 'OK')                        # positive control: the native flatten

    def test_a_widget_without_a_form_is_unread_and_the_next_page_still_read(self):
        route, got = self.run_pdf('orphan_widget.pdf')
        rec = route['units'][0]['annotation_records'][0]
        self.assertEqual((route['status'], rec['subtype'], rec['field'], rec['value'], len(got)), ('PARTIAL', 'widget', None, None, 2))
        self.assertIn('form environment', rec['unprocessed'])
        self.assertEqual([u['what'] for u in route['unprocessed']], ['annotation'])
        good = self.run_pdf('forms_annotation.pdf')[0]['units'][0]['annotation_records'][1]                # positive control: an AcroForm document
        self.assertEqual((good['field'], good['value']), ('amount', '42'))



class EmptyFrame(unittest.TestCase):  # root OCR_PDF_EMPTY_FRAME: a crop box disjoint from the media box leaves PDFium no displayed page (0 x 0)
    def pdf(self, crop):  # page 1: MediaBox 300 x 200 with this CropBox (or none); page 2: a valid 100 x 100 page (PDFium's own API)
        doc = pdfium.PdfDocument.new()
        try:
            page = doc.new_page(300, 200)
            if crop: page.set_cropbox(*crop)
            page.close(); doc.new_page(100, 100).close(); b = io.BytesIO(); doc.save(b); return b.getvalue()
        finally: doc.close()

    def test_a_page_with_no_displayed_area_is_an_error_and_the_next_page_is_read(self):
        data = self.pdf((500, 500, 600, 600)); route, got = pdf.pages(data, 'f/x.pdf', sha(data))
        bad, good = route['units']
        self.assertEqual((route['status'], len(got)), ('PARTIAL', 1))
        self.assertEqual((bad['mediabox_pt'], bad['cropbox_pt']), ([0, 0, 300, 200], [500, 500, 600, 600]))   # the page's own boxes stay recorded
        self.assertNotIn('input_sha256', bad['input']); self.assertIn('size', bad['input']['error'])
        self.assertEqual(tuple(good['input']['size']), px(100, 100))
        data = self.pdf(None); route, got = pdf.pages(data, 'f/x.pdf', sha(data))                             # positive control: no disjoint crop
        self.assertEqual((route['status'], len(got), tuple(route['units'][0]['input']['size'])), ('OK', 2, px(300, 200)))



class UriBytes(unittest.TestCase):  # root OCR_PDF_URI_PRESERVATION: PDFium returns a URI's bytes as written ("may contain badly encoded data")
    def test_ascii_uris_read_and_other_bytes_kept_exactly_and_unread(self):
        data = (CASES / 'uris.pdf').read_bytes(); route, got = pdf.pages(data, 'f/x.pdf', sha(data))
        links = route['units'][0]['links']
        self.assertEqual([l.get('uri') for l in links], ['https://example.test/plain', 'https://example.test/%C3%A9', None,
                                                         'https://example.test/a\x00b', 'https://example.test/end\x00'])   # only the terminator removed
        self.assertEqual((links[2].get('uri_bytes_hex'), 'unprocessed' in links[2]), ((b'https://example.test/caf\xc3\xa9').hex(), True))
        self.assertTrue(all('uri_bytes_hex' not in l and 'unprocessed' not in l for k, l in enumerate(links) if k != 2))   # ASCII links: as before
        self.assertEqual(([(u['what'], u['index']) for u in route['unprocessed']], len(got)), ([('link', 2)], 1))
        self.assertEqual(route['status'], 'PARTIAL')                                                                       # never OK with a changed link

    def test_a_uri_without_its_terminator_is_unread(self):
        data = (CASES / 'uris.pdf').read_bytes(); real = pdfium_c.FPDFAction_GetURIPath
        def no_nul(doc, action, buf, n):  # the declared length, but the last byte is not the NUL terminator
            m = real(doc, action, buf, n)
            if buf is not None: ctypes.memset(buf, ord('x'), n)
            return m
        pdfium_c.FPDFAction_GetURIPath = no_nul
        try: route, _ = pdf.pages(data, 'f/x.pdf', sha(data))
        finally: pdfium_c.FPDFAction_GetURIPath = real
        self.assertTrue(all(l.get('uri') is None and l.get('unprocessed') == 'URI unreadable' for l in route['units'][0]['links']))


if __name__ == '__main__':
    unittest.main()
