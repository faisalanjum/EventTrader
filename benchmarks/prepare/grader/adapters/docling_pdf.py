"""Route adapter: Docling, PDF pipeline -> the common route format.
Native PDF originals: anchors are Docling's own page boxes (converted to the key's top-left points). HTML originals
take the printed-PDF route of the study: headless Chrome prints the page, Docling reads the PDF, and the shared linker
places the text back in the original HTML bytes (the print is a derivative, never the evidence). Shape rules only.

    <docling python> -m benchmarks.prepare.grader.adapters.docling_pdf --key <key package> --split development --out <run dir>
                                                    [--catalog CSV] [--limit N] [--no-ocr] [--reuse-raw]

Settings: table structure FAST, heading hierarchy on, OCR on unless --no-ocr (picture text). A native PDF page whose text layer Docling's own
confidence grades POOR on parsing (an unreadable font encoding: the cells are not words) is converted again alone with OCR over the whole page and
its units take the page's place — the route's own gate escalates, never a file name (ledger §17: one block from word error 1.0 to 0.0)."""
import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

from benchmarks.prepare.grader import grade
from driver.prepare.convert import anchor
from benchmarks.prepare.grader.adapters import cache
from benchmarks.prepare.grader.adapters.docling_html import to_units, unsupported as _unsupported, route_status

NAME = 'docling-pdf'
CHROME = ['google-chrome', '--headless=new', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer']  # as the 2026-09-30 study


def region(bbox, page_height):
    """Docling box (bottom-left origin unless stated) -> [x0, y0, x1, y1] in points from the page's top-left."""
    l, t, r, b = bbox['l'], bbox['t'], bbox['r'], bbox['b']
    if (bbox.get('coord_origin') or 'BOTTOMLEFT').upper() == 'BOTTOMLEFT': t, b = page_height - t, page_height - b
    return [l, min(t, b), r, max(t, b)]


def mapped(provs, text):
    """Do the provenance character spans split the text page by page: every page has one, each lies inside the text, none reaching back into
    the one before? Docling writes `prov[].charspan` per page (Codex R13 C2); a unit without that mapping keeps its pages only."""
    cs = [p.get('charspan') for p in provs]
    return all(isinstance(c, list) and len(c) == 2 and all(isinstance(v, int) for v in c) and 0 <= c[0] <= c[1] <= len(text) for c in cs) \
        and all(cs[i][0] >= cs[i - 1][1] for i in range(1, len(cs)))


def anchors_from_boxes(doc, units):
    """Give units and cells page/region anchors from Docling's provenance; a block over several pages gets a list, each page with the span of
    the text it holds (`charspan`) when the tool's spans are consistent."""
    heights = {int(k): v['size']['height'] for k, v in (doc.get('pages') or {}).items()}
    items = {k: v for key in ('texts', 'tables', 'pictures') for k, v in ((it['self_ref'], it) for it in doc.get(key) or [])}
    for u in units:
        it = items.get(u['id'], {})
        provs = [{'page': p['page_no'], 'region': region(p['bbox'], heights.get(p['page_no'], 0)), **({'charspan': list(p['charspan'])} if p.get('charspan') else {})} for p in it.get('prov') or [] if p.get('bbox')]
        if not mapped(provs, u.get('text', '')): provs = [{k: v for k, v in p.items() if k != 'charspan'} for p in provs]  # spans out of bounds or out of order map nothing: the pages stay, the split of the text between them is unknown
        if u.get('kind') == 'table':
            for c in u['cells']:
                raw = it['data']['table_cells'][c.pop('_i')]; bb = raw.get('bbox')
                c['anchor'] = {'page': provs[0]['page'], 'region': region(bb, heights.get(provs[0]['page'], 0))} if bb and provs else None
            u['anchor'] = provs[0] if len(provs) == 1 else (provs or None)
        else:
            u['anchor'] = provs[0] if len(provs) == 1 else (provs or None)
    return units


def page_sizes(doc):
    """Docling's page sizes, so the grader can check that every region lies on its page."""
    return {int(k): [v['size']['width'], v['size']['height']] for k, v in (doc.get('pages') or {}).items() if v.get('size')}


def poor_parse_pages(confidence):
    """Pages whose digital text cells Docling grades POOR (its `parse_score`, judged by its own grade scale, no threshold of ours)."""
    return sorted(p for p, c in confidence.pages.items() if type(c)(parse_score=c.parse_score).low_grade.value == 'poor')


def pages_of(u):
    return {a['page'] for a in (u['anchor'] if isinstance(u['anchor'], list) else [u['anchor']]) if a and 'page' in a} if u.get('anchor') else set()


def reread_groups(units, poor):
    """The page groups to convert again: the parse-POOR pages, closed over first-pass units that span further pages (a paragraph read across a
    page break is read again whole, never cut), as contiguous ranges (a, b)."""
    pages, changed = set(poor), True
    while changed:
        changed = False
        for u in units:
            ps = pages_of(u)
            if ps & pages and not ps <= pages: pages |= ps; changed = True
    out, run = [], []
    for p in sorted(pages):
        if run and p != run[-1] + 1: out.append((run[0], run[-1])); run = []
        run.append(p)
    return out + ([(run[0], run[-1])] if run else [])


def spliced(units, reread):
    """The first pass's units in their own order, with each re-read page group's units standing where the first pass reaches the group's first
    page (page order kept, also for a page the first pass had nothing on). A first-pass unit whose pages are all re-read goes; a unit that spans
    a re-read page and one not re-read is kept and marked incomplete, never dropped (the groups are closed over such units upstream). Re-read
    units' ids are prefixed by their group's first page, and references between them (a table's notes, links) follow the new ids."""
    reread = {(k, k) if isinstance(k, int) else tuple(k): v for k, v in reread.items()}  # a group is a page range (a, b); a bare page number means that one page
    covered = {p for a, b in reread for p in range(a, b + 1)}
    def renamed(a, b):  # ids and the fields that refer to them (a table's notes, a link's destination); never text, captions, cell values or hrefs (Codex R13 C5)
        ren = {u['id']: f"p{a}:{u['id']}" for u in reread[(a, b)] if 'id' in u}
        ref = lambda k, v: ren.get(v, v) if k in ('id', 'to') and isinstance(v, str) else [ren.get(n, n) if isinstance(n, str) else n for n in v] if k == 'notes' and isinstance(v, list) else fix(v)
        fix = lambda x: {k: ref(k, v) for k, v in x.items()} if isinstance(x, dict) else [fix(v) for v in x] if isinstance(x, list) else x
        return [fix(u) for u in reread[(a, b)]]
    pending, out = sorted(reread), []
    for u in units:
        ps = pages_of(u)
        if ps and ps <= covered: continue
        first = min(ps) if ps else None
        while pending and first is not None and pending[0][0] <= first: out += renamed(*pending.pop(0))
        out.append(dict(u, incomplete='spans a page converted again') if ps & covered else u)
    for g in pending: out += renamed(*g)
    return out


def route_for_pdf(doc, file_id, sha256, seconds, version, settings=None):
    units = anchors_from_boxes(doc, to_units(doc, with_index=True))  # the tool's own order is kept
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds, 'pages': page_sizes(doc),
            'route': {'name': NAME, 'tool': 'docling', 'version': version, 'settings': settings or {}, 'adapter': 'benchmarks/prepare/grader/adapters/docling_pdf.py', 'linker': None},
            'units': units, 'uncovered': []}


def route_for_printed_html(doc, raw, file_id, sha256, seconds, version, settings=None):
    units = to_units(doc, with_index=True)
    for u in units:
        for c in u.get('cells') or []: c.pop('_i', None)
    linked = anchor.link(raw, units)  # the tool's own order is kept
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds, 'pages': page_sizes(doc),
            'route': {'name': NAME + ' (printed HTML)', 'tool': 'docling', 'version': version, 'settings': settings or {}, 'adapter': 'benchmarks/prepare/grader/adapters/docling_pdf.py', 'linker': 'driver/prepare/convert/anchor.py'},
            'units': linked['units'], 'uncovered': linked['uncovered']}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    ap.add_argument('--limit', type=int, help='only the first N files (native PDFs first, then by name)'); ap.add_argument('--no-ocr', action='store_true')
    ap.add_argument('--reuse-raw', action='store_true', help='adapt saved Docling output again instead of converting')
    a = ap.parse_args(argv)
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, HeadingHierarchyOptions
    import importlib.metadata as md
    version = next((f"{d} {md.version(d)}" for d in ('docling', 'docling-slim') if _installed(md, d)), 'unknown') + f"; docling-core {md.version('docling-core')}"
    opts = PdfPipelineOptions(do_ocr=not a.no_ocr, generate_parsed_pages=True, heading_hierarchy_options=HeadingHierarchyOptions(enabled=True))
    opts.table_structure_options.mode = TableFormerMode.FAST
    settings = {'pipeline': 'PDF', 'table_mode': 'FAST', 'heading_hierarchy': True, 'ocr': not a.no_ocr, 'print': 'google-chrome --headless=new --print-to-pdf',
                'reread': None if a.no_ocr else 'a native PDF page whose parse grade is POOR (Docling confidence) is converted again alone with OCR mode FULL_PAGE'}
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    from docling.datamodel.pipeline_options import OcrMode
    full = opts.model_copy(deep=True); full.ocr_options.mode = OcrMode.FULL_PAGE  # the same engine and settings, OCR over the whole page
    conv_full = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=full)})
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True); (out / 'route').mkdir(exist_ok=True)
    files = {}
    for t in grade.load_sources(a.key, a.catalog):  # sources only: converters never read answers
        if t['split'] == a.split: files.setdefault(t['file_id'], (t['path'], t['sha256']))
    order = sorted(files, key=lambda f: (files[f][0].suffix.lower() != '.pdf', f))  # native PDFs first, then by name
    if a.reuse_raw: order = [f for f in order if (out / 'raw' / (f + '.docling.json')).exists()]  # re-adapt what was converted, convert nothing new
    if a.limit: order = order[:a.limit]
    facts = {}
    for fid in order:
        path, sha = files[fid]; ext = path.suffix.lower()
        (out / 'route' / fid).parent.mkdir(parents=True, exist_ok=True); (out / 'raw' / fid).parent.mkdir(parents=True, exist_ok=True)
        if ext not in ('.pdf', '.htm', '.html'):
            (out / 'route' / (fid + '.json')).write_text(json.dumps(_unsupported(fid, sha, version))); facts[fid] = {'status': 'UNSUPPORTED'}; continue
        rawjson = out / 'raw' / (fid + '.docling.json'); metajson = out / 'raw' / (fid + '.meta.json'); t0 = time.time(); printed = 0.0; reread, groups, errors = {}, [], []; ver = version
        rawpage = lambda g: out / 'raw' / f'{fid}.p{g[0]}-{g[1]}.fullocr.docling.json'
        try:
            if a.reuse_raw and rawjson.exists():  # a cached run is reused only whole: its record names the source bytes, settings, producing version, every output and the outcome (adapters/cache.py)
                meta = cache.reuse(metajson, sha, settings); done = [tuple(g) for g in meta.get('reread_done') or []]
                if sorted(tuple(g) for g in meta.get('reread_required') or []) != sorted(done): raise RuntimeError('cache refused: the cached run is incomplete')
                doc, groups, status, errors, ver = json.loads(rawjson.read_text()), done, meta['status'], meta.get('errors') or [], meta['version']
                reread = {g: json.loads(rawpage(g).read_text()) for g in done}; dt, printed = meta.get('docling_seconds', 0), meta.get('print_seconds', 0)
            else:
                cache.begin(metajson)  # from here the old record vouches for nothing: a crash below leaves no record
                src = str(path)
                if ext != '.pdf':
                    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False); tmp.close(); src = tmp.name; t1 = time.time()
                    subprocess.run(CHROME + [f'--print-to-pdf={src}', 'file://' + str(path)], capture_output=True, timeout=900, check=True); printed = round(time.time() - t1, 1)
                t2 = time.time(); res = conv.convert(src); doc = res.document.export_to_dict(); status, errors = str(res.status), [str(e) for e in res.errors]
                rawjson.write_text(json.dumps(doc, ensure_ascii=False))
                poor = poor_parse_pages(res.confidence) if ext == '.pdf' and not a.no_ocr else []  # the route's own gate: an unreadable text layer is read again by OCR (printed HTML is our own print: readable)
                groups = reread_groups(route_for_pdf(doc, fid, sha, 0, version, settings)['units'], poor) if poor else []
                for g in groups:  # a page group is read again whole, so a paragraph across a page break is never cut
                    r2 = conv_full.convert(src, page_range=g); reread[g] = r2.document.export_to_dict(); rawpage(g).write_text(json.dumps(reread[g], ensure_ascii=False))
                    if str(r2.status).split('.')[-1] != 'SUCCESS': errors.append(f'pages {g[0]}-{g[1]} read again: {r2.status}'); errors += [str(e) for e in r2.errors]
                if str(status).split('.')[-1] == 'SUCCESS' and any(e.startswith('pages ') for e in errors): status = 'ConversionStatus.PARTIAL_SUCCESS'  # a re-read that did not fully succeed leaves the file partial
                dt = round(time.time() - t2, 1)
                cache.save(metajson, [rawjson, *(rawpage(g) for g in groups)], sha256=sha, version=version, settings=settings, status=status, errors=errors, reread_required=groups, reread_done=groups, docling_seconds=dt, print_seconds=printed)
        except Exception as e:  # a tool crash is a result, never a stop
            facts[fid] = {'status': 'FAILED', 'error': repr(e)[:300], 'seconds': round(time.time() - t0, 1)}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(dict(_unsupported(fid, sha, version), status='FAILED', error=repr(e)[:300]))); print(fid, facts[fid], flush=True); continue
        t3 = time.time()
        route = route_for_pdf(doc, fid, sha, dt, ver, settings) if ext == '.pdf' else route_for_printed_html(doc, path.read_bytes(), fid, sha, dt, ver, settings)
        if reread:
            route['units'] = spliced(route['units'], {g: route_for_pdf(d, fid, sha, dt, ver, settings)['units'] for g, d in reread.items()})
            route['reread'] = {'full_page_ocr_pages': sorted(p for a_, b_ in reread for p in range(a_, b_ + 1)), 'groups': sorted(reread)}
        route['status'], route['error'] = route_status(status, errors)  # SUCCESS alone is OK; a partial conversion or re-read is PARTIAL with its errors
        flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
        facts[fid] = {'status': status, 'version': ver, 'errors': errors, 'print_seconds': printed, 'docling_seconds': dt, 'adapter_seconds': round(time.time() - t3, 2), 'items': len(flat),
                      'reread_required': groups, 'reread_done': sorted(reread), 'reread_pages': sorted(p for a_, b_ in reread for p in range(a_, b_ + 1)),
                      'unanchored': sum(1 for x in flat if not x.get('anchor')), 'uncovered_spans': len(route['uncovered']),
                      'uncovered_chars': sum(len(anchor.squash(s['text'])) for s in route['uncovered']), 'pages': len(doc.get('pages') or {})}
        (out / 'route' / (fid + '.json')).write_text(json.dumps(route, ensure_ascii=False))
        print(fid, facts[fid], flush=True)
        (out / 'facts.json').write_text(json.dumps({'route': NAME, 'version': version, 'settings': settings, 'split': a.split, 'files': facts}, indent=1))
    return 0


def _installed(md, dist):
    try: md.version(dist); return True
    except md.PackageNotFoundError: return False


if __name__ == '__main__':
    raise SystemExit(main())
