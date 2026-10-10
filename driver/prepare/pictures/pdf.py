# PDF pages as picture inputs (owner, Oct 10: minimal native PDF integration; actual OCR last). Every page of one PDF member is rendered by PDFium
# (pypdfium2, pinned) as Chandra 0.2.0 renders a PDF page (chandra/input.py load_pdf_images: forms initialised, the page flattened with FLAT_NORMALDISPLAY
# and loaded again, drawn at max(192 DPI, 1,024 px on the shorter side) as RGB), with every native result recorded; the PNG is that page's input. The
# route's image units are read by join() as a document's pictures are (archive, the three readers, raw records, packets): no second pipeline. A page PDFium
# cannot flatten, or a document whose forms are XFA (this PDFium build draws none), has an error and no input - never a raster without its form fields
# and annotations; a document PDFium cannot open (invalid, password) is FAILED with PDFium's message. The document is closed whatever happens; storage,
# dependency and memory errors propagate. Not read here: the text layer (the original PDF stays in its package).
# v2 (root ROOT_PDF_REVIEW_v1): what flattening removes is read first - each link's rectangle and native target (URI, or destination page and location),
# each annotation's subtype, rectangle and note or form-field value - and each page keeps PDFium's own boxes and rotation, its links mapped to the PNG's
# pixels by PDFium (FPDF_PageToDevice). Embedded files are listed by name, unread. A link whose action or destination PDFium cannot resolve, and every
# embedded file, is listed in `unprocessed` and makes the route PARTIAL: nothing unread looks handled. Places follow the existing public PDF anchor
# contract (the grader's RouteFile, benchmarks/prepare/grader/adapters/docling_pdf.py): `page` is one-based everywhere, each page unit's anchor is
# {page, region} - its whole displayed page, in points from the top left - and route `pages` declares each displayed size; PDFium's zero-based
# index is kept only as `page_index`. Native boxes keep their own declared system (COORDINATES).
import ctypes, hashlib, io, math
import importlib.metadata as md
from ..convert import anchor

DPI, MIN_SIDE = 192, 1024                                                    # chandra/settings.py IMAGE_DPI, MIN_PDF_IMAGE_DIM (0.2.0)
SETTINGS = {'dpi': DPI, 'min_side_px': MIN_SIDE, 'forms': 'init_forms', 'flatten': 'FLAT_NORMALDISPLAY, page loaded again', 'image': 'PNG RGB'}
FORMS = {0: 'none', 1: 'AcroForm', 2: 'XFA full', 3: 'XFA foreground'}      # FPDF_GetFormType
VIEWS = {1: 'XYZ', 2: 'Fit', 3: 'FitH', 4: 'FitV', 5: 'FitR', 6: 'FitB', 7: 'FitBH', 8: 'FitBV'}   # PDFDEST_VIEW_*; 0 is PDFium's unknown mode
ACTIONS = {2: 'remote goto', 4: 'launch', 5: 'embedded goto'}                 # PDFACTION_*: URI (3) and GoTo (1) are read; 0 is unsupported
COORDINATES = {'anchor.region': 'points from the top left of the displayed page (crop box, rotation applied); pages[page] is that page size',
               'size_pt': 'displayed page size in points (PDFium get_size: crop box, rotation applied)',
               'bbox_pt, mediabox_pt, cropbox_pt, links[].rect_pt, annotation_records[].rect_pt': 'native PDF user space in points: left, bottom, right, top; unrotated',
               'mediabox_pt, cropbox_pt': 'as the page itself declares it; None when the page does not (inherited or absent); bbox_pt is the effective displayed box',
               'links[].rect_px': 'pixels of the page PNG input (input.size), by PDFium FPDF_PageToDevice'}


def pages(data, file_id, sha256):
    """(route, {input SHA-256: PNG bytes}) for one PDF member's bytes. Route: schema, file_id, sha256, status (OK / PARTIAL when a page has an error or
    anything is unprocessed / FAILED when PDFium cannot open it or its forms), error, route {name, tool, version, settings}, pages {page: [w, h] pt},
    coordinates (COORDINATES), form_type, attachments
    [{index, name}], unprocessed [{what, page, index, why} or {what: 'attachment', index, name}], units: one per page in order, {'id': 'p<page>', 'kind':
    'image', 'page' (one-based), 'page_index' (PDFium's, zero-based), 'anchor' {page, region}, 'size_pt', 'rotation', 'bbox_pt', 'mediabox_pt', 'cropbox_pt', 'annotations' (count), 'annotation_records', 'links', 'input'};
    a link: {rect_pt (left, bottom, right, top), rect_px (in the PNG), uri | dest {page, page_index, x, y, zoom} | unprocessed}; input = {'member_sha256',
    'input_sha256', 'how': 'pdf_page', 'page', 'scale', 'size' (the PNG's pixels), 'flatten'} or {'error'}. Bytes that are not `sha256` raise ValueError."""
    import pypdfium2 as pdfium, pypdfium2.raw as c                         # only here: the rest of the package needs no PDFium
    anchor.check_source(data, sha256)
    route = {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'units': [], 'unprocessed': [], 'pages': {}, 'coordinates': COORDINATES,
             'route': {'name': 'pdf-pages', 'tool': 'pypdfium2', 'version': f"pypdfium2 {md.version('pypdfium2')}; PDFium {pdfium.PDFIUM_INFO}", 'settings': SETTINGS}}
    try: doc = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as e: route.update(status='FAILED', error=f'PDFium: {e}'); return route, {}
    got = {}
    try:
        try: doc.init_forms(); form = doc.get_formtype()
        except pdfium.PdfiumError as e: route.update(status='FAILED', error=f'PDFium forms: {e}'); return route, {}
        route['form_type'] = FORMS.get(form, f'unknown form type {form}')
        route['attachments'] = []
        for i in range(doc.count_attachments()):
            try: name = doc.get_attachment(i).get_name() or None                           # None: PDFium read no name
            except pdfium.PdfiumError: name = None
            route['attachments'].append({'index': i, 'name': name})
        route['unprocessed'] += [{'what': 'attachment', **a} for a in route['attachments']]
        for k in range(len(doc)):
            u = {'id': f'p{k + 1}', 'kind': 'image', 'page': k + 1, 'page_index': k}; route['units'].append(u)
            if form not in (0, 1): u['input'] = {'error': f"{route['form_type']}: this PDFium build draws no such form content"}; continue
            im = None
            try:
                page = doc[k]
                try:
                    w, h = page.get_size(); route['pages'][k + 1] = [w, h]; u['anchor'] = {'page': k + 1, 'region': [0, 0, w, h]}
                    own = [page.get_mediabox(fallback_ok=False), page.get_cropbox(fallback_ok=False)]; bbox = page.get_bbox()
                    u.update(size_pt=[w, h], rotation=page.get_rotation(), bbox_pt=list(bbox), mediabox_pt=own[0] and list(own[0]), cropbox_pt=own[1] and list(own[1]),
                             annotations=c.FPDFPage_GetAnnotCount(page.raw), annotation_records=_annotations(c, doc, page), links=_links(c, doc, page))
                    if not (math.isfinite(w) and math.isfinite(h) and w > 0 and h > 0):  # e.g. a CropBox outside the MediaBox: PDFium shows no page
                        u['input'] = {'error': f'PDFium gives the page no usable displayed size ({w} x {h}): no picture'}; continue
                    if own[0] is None: page.set_mediabox(*bbox)  # flattening writes a box the page does not declare itself from a default, not from the
                    if own[1] is None: page.set_cropbox(*bbox)   # inherited one: the shown box is declared first, in this in-memory document only
                    flat = c.FPDFPage_Flatten(page.raw, c.FLAT_NORMALDISPLAY)
                finally: page.close()
                if flat not in (c.FLATTEN_SUCCESS, c.FLATTEN_NOTHINGTODO):
                    u['input'] = {'error': 'PDFium could not flatten the page: its form fields and annotations would be missing' if flat == c.FLATTEN_FAIL
                                  else f'PDFium flatten returned unknown value {flat}'}; continue
                scale, page = max(MIN_SIDE / min(w, h) * 72, DPI) / 72, doc[k]   # a flattened page is drawn once it is loaded again (as Chandra does)
                try:
                    if (list(page.get_size()), list(page.get_bbox())) != ([w, h], list(bbox)):  # the displayed frame must be the one recorded: never a picture of another
                        u['input'] = {'error': f'PDFium flattening changed the page frame from {[w, h]} {list(bbox)} to {list(page.get_size())} {list(page.get_bbox())}'}; continue
                    bitmap = page.render(scale=scale)
                    try:
                        drawn = bitmap.to_pil()
                        try: im = drawn.convert('RGB')
                        finally: drawn.close()
                    finally: bitmap.close()
                    for l in u['links']:  # PDFium's own page -> pixel mapping (boxes, rotation); a failed mapping is no place
                        l['rect_px'] = _device(c, page, im.size, l['rect_pt']) if l['rect_pt'] else None
                        if l['rect_pt'] and l['rect_px'] is None: _miss(l, 'PDFium could not map it to the picture')
                finally: page.close()
                b = io.BytesIO(); im.save(b, format='PNG'); size = im.size
            except pdfium.PdfiumError as e: u['input'] = {'error': f'PDFium: {e}'}; continue
            finally:
                if im is not None: im.close()                                                 # the RGB copy, whatever follows its creation
            png = b.getvalue(); s = hashlib.sha256(png).hexdigest(); got[s] = png
            u['input'] = {'member_sha256': sha256, 'input_sha256': s, 'how': 'pdf_page', 'page': k + 1, 'scale': scale, 'size': list(size),
                          'flatten': 'flattened' if flat == c.FLATTEN_SUCCESS else 'nothing to flatten'}
    finally: doc.close()
    for u in route['units']:  # every link or annotation PDFium read only in part, by page
        route['unprocessed'] += [{'what': what, 'page': u['page'], 'index': j, 'why': x.get('error') or x['unprocessed']}
                                 for what in ('link', 'annotation') for j, x in enumerate(u.get(what + 's' if what == 'link' else 'annotation_records') or []) if 'error' in x or 'unprocessed' in x]
    if route['unprocessed'] or any('error' in u['input'] for u in route['units']): route['status'] = 'PARTIAL'
    return route, got


def _miss(x, why):  # what PDFium did not read of a link or annotation
    x['unprocessed'] = why if 'unprocessed' not in x else x['unprocessed'] + '; ' + why


def _wide(c, fn, *args):  # PDFium's two-call UTF-16 getter: (read, text). Its byte length counts the 2-byte terminator: 0 = error; 2 = an empty or
    # missing value (None, read); a second call that returns another length is an error. Only the terminator is removed (a NUL in the text stays).
    n = fn(*args, None, 0)
    if n == 2: return True, None
    if n < 2 or n % 2: return False, None
    buf = ctypes.create_string_buffer(n)
    if fn(*args, ctypes.cast(buf, ctypes.POINTER(c.FPDF_WCHAR)), n) != n or buf.raw[n - 2:n] != b'\x00\x00': return False, None
    return True, buf.raw[:n - 2].decode('utf-16-le')


def _annotations(c, doc, page):  # every annotation as PDFium reads it before flattening: subtype, rectangle, its note or form-field name and value,
    # the name of a file it attaches
    import pypdfium2 as pdfium
    names = {v: n[11:].lower() for n, v in vars(c).items() if n.startswith('FPDF_ANNOT_') and n.count('_') == 2 and isinstance(v, int)}
    out = []
    for i in range(c.FPDFPage_GetAnnotCount(page.raw)):
        a = c.FPDFPage_GetAnnot(page.raw, i)
        if not a: out.append({'error': 'PDFium returned no annotation'}); continue
        try:
            t, r = c.FPDFAnnot_GetSubtype(a), c.FS_RECTF()
            rec = {'subtype': names.get(t, f'unknown {t}'), 'rect_pt': [r.left, r.bottom, r.right, r.top] if c.FPDFAnnot_GetRect(a, r) else None}
            if rec['rect_pt'] is None: _miss(rec, 'PDFium could not read its rectangle')
            if t == c.FPDF_ANNOT_UNKNOWN: _miss(rec, 'PDFium could not read its subtype')
            if t == c.FPDF_ANNOT_WIDGET and doc.formenv is None:  # a field with no /AcroForm: PDFium has no form environment to read its name or value
                rec.update(field=None, value=None); _miss(rec, 'no form environment: its field name and value unread'); reads = []
            else:
                reads = [('field', c.FPDFAnnot_GetFormFieldName, doc.formenv.raw, a), ('value', c.FPDFAnnot_GetFormFieldValue, doc.formenv.raw, a)] if t == c.FPDF_ANNOT_WIDGET \
                    else [('contents', c.FPDFAnnot_GetStringValue, a, b'Contents')]
            for key, fn, *args in reads:
                ok, rec[key] = _wide(c, fn, *args)
                if not ok: _miss(rec, f'PDFium could not read its {key}')
            if t == c.FPDF_ANNOT_FILEATTACHMENT:  # a file a page annotation attaches: its name, the content unread (as a document's attachments)
                h = c.FPDFAnnot_GetFileAttachment(a)
                if not h: rec['attachment'] = None; _miss(rec, 'PDFium returned no attached file')
                else:
                    try: name = pdfium.PdfAttachment(h, doc).get_name() or None
                    except pdfium.PdfiumError: name = None
                    rec['attachment'] = {'name': name}; _miss(rec, 'attached file content unread' + ('' if name else '; its name unread'))
        finally: c.FPDFPage_CloseAnnot(a)
        out.append(rec)
    return out


def _links(c, doc, page):  # every link, enumerated by PDFium before flattening removes it: rectangle and native target, else why it is unprocessed
    import pypdfium2 as pdfium
    out, pos, link = [], ctypes.c_int(0), c.FPDF_LINK()
    while c.FPDFLink_Enumerate(page.raw, ctypes.byref(pos), ctypes.byref(link)):
        r = c.FS_RECTF(); l = {'rect_pt': [r.left, r.bottom, r.right, r.top] if c.FPDFLink_GetAnnotRect(link, r) else None}; out.append(l)
        if l['rect_pt'] is None: _miss(l, 'PDFium could not read its rectangle')
        action, dest = c.FPDFLink_GetAction(link), c.FPDFLink_GetDest(doc.raw, link)
        if action:
            t = c.FPDFAction_GetType(action)
            if t == c.PDFACTION_URI:
                n = c.FPDFAction_GetURIPath(doc.raw, action, None, 0); buf = ctypes.create_string_buffer(max(n, 1))   # 0: failed; 1: its NUL alone
                if n <= 1 or c.FPDFAction_GetURIPath(doc.raw, action, buf, n) != n or buf.raw[n - 1] != 0: _miss(l, 'URI unreadable'); continue
                raw = buf.raw[:n - 1]  # its bytes as written, the NUL terminator alone removed; PDFium does not validate them ("may contain badly encoded data")
                if raw.isascii(): l['uri'] = raw.decode('ascii')   # the 7-bit ASCII a PDF URI is; any other bytes are kept exactly, uninterpreted
                else: l['uri'] = None; l['uri_bytes_hex'] = raw.hex(); _miss(l, 'URI bytes are not 7-bit ASCII: kept as hex, not interpreted')
                continue
            if t != c.PDFACTION_GOTO: _miss(l, f"action {ACTIONS.get(t, 'not supported by PDFium')}"); continue
            dest = c.FPDFAction_GetDest(doc.raw, action)
        dest = pdfium.PdfDest(dest, doc) if dest else None                                    # PDFium's own destination helper
        page_index = dest.get_index() if dest else None
        if page_index is None: _miss(l, 'destination not found'); continue
        mode, params = dest.get_view(); l['dest'] = {'page': page_index + 1, 'page_index': page_index, 'view': VIEWS.get(mode)}
        if mode not in VIEWS: _miss(l, 'destination view unknown'); continue
        if mode != c.PDFDEST_VIEW_XYZ: l['dest']['params'] = params; continue
        has, at = [ctypes.c_int() for _ in range(3)], [ctypes.c_float() for _ in range(3)]  # XYZ: get_view gives a null as 0; this call tells them apart
        if not c.FPDFDest_GetLocationInPage(dest.raw, *map(ctypes.byref, has + at)): _miss(l, 'XYZ location unread'); continue
        l['dest'].update({k: (v.value if h.value else None) for k, h, v in zip(('x', 'y', 'zoom'), has, at)})
    return out


def _device(c, page, size, rect):  # a page rectangle (left, bottom, right, top) in the rendered picture's pixels, by PDFium's page -> device mapping
    xy = []
    for px, py in ((rect[0], rect[3]), (rect[2], rect[1])):
        dx, dy = ctypes.c_int(), ctypes.c_int()
        if not c.FPDF_PageToDevice(page.raw, 0, 0, size[0], size[1], 0, px, py, ctypes.byref(dx), ctypes.byref(dy)): return None
        xy.append((dx.value, dy.value))
    return [min(x for x, _ in xy), min(y for _, y in xy), max(x for x, _ in xy), max(y for _, y in xy)]
