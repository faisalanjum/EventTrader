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
import re
import subprocess
import tempfile
import time
from pathlib import Path

from benchmarks.prepare.grader import anchor, grade
from benchmarks.prepare.grader.adapters.docling_html import to_units, unsupported as _unsupported

NAME = 'docling-pdf'
CHROME = ['google-chrome', '--headless=new', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer']  # as the 2026-09-30 study


def region(bbox, page_height):
    """Docling box (bottom-left origin unless stated) -> [x0, y0, x1, y1] in points from the page's top-left."""
    l, t, r, b = bbox['l'], bbox['t'], bbox['r'], bbox['b']
    if (bbox.get('coord_origin') or 'BOTTOMLEFT').upper() == 'BOTTOMLEFT': t, b = page_height - t, page_height - b
    return [l, min(t, b), r, max(t, b)]


def anchors_from_boxes(doc, units):
    """Give units and cells page/region anchors from Docling's provenance; a block over several pages gets a list."""
    heights = {int(k): v['size']['height'] for k, v in (doc.get('pages') or {}).items()}
    items = {k: v for key in ('texts', 'tables', 'pictures') for k, v in ((it['self_ref'], it) for it in doc.get(key) or [])}
    for u in units:
        it = items.get(u['id'], {})
        provs = [{'page': p['page_no'], 'region': region(p['bbox'], heights.get(p['page_no'], 0))} for p in it.get('prov') or [] if p.get('bbox')]
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


def spliced(units, reread):
    """The first pass's units in their own order, except that every unit on a re-read page goes and the re-read page's units stand where its
    first unit stood (ids prefixed by the page, so ids stay unique). A unit anchored on several pages goes when any of them is re-read."""
    pages = lambda u: {a['page'] for a in (u['anchor'] if isinstance(u['anchor'], list) else [u['anchor']]) if a} if u.get('anchor') else set()
    renamed = lambda p: [dict(x, id=f"p{p}:{x['id']}") for x in reread[p]]
    out, done = [], set()
    for u in units:
        hit = pages(u) & set(reread)
        if not hit: out.append(u); continue
        for p in sorted(hit - done): out += renamed(p); done.add(p)
    for p in sorted(set(reread) - done): out += renamed(p)  # a re-read page the first pass had nothing on
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
            'route': {'name': NAME + ' (printed HTML)', 'tool': 'docling', 'version': version, 'settings': settings or {}, 'adapter': 'benchmarks/prepare/grader/adapters/docling_pdf.py', 'linker': 'benchmarks/prepare/grader/anchor.py'},
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
        rawjson = out / 'raw' / (fid + '.docling.json'); t0 = time.time(); printed = 0.0; reread = {}
        rawpage = lambda p: out / 'raw' / f'{fid}.p{p}.fullocr.docling.json'
        try:
            if a.reuse_raw and rawjson.exists():
                doc = json.loads(rawjson.read_text()); prev = (json.loads((out / 'facts.json').read_text())['files'].get(fid) or {}) if (out / 'facts.json').exists() else {}
                dt, printed, status = prev.get('docling_seconds', 0), prev.get('print_seconds', 0), 'reused raw'
                reread = {int(m.group(1)): json.loads(p.read_text()) for p in (out / 'raw' / fid).parent.glob(Path(fid).name + '.p*.fullocr.docling.json') for m in [re.search(r'\.p(\d+)\.fullocr\.docling\.json$', p.name)] if m}
            else:
                src = str(path)
                if ext != '.pdf':
                    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False); tmp.close(); src = tmp.name; t1 = time.time()
                    subprocess.run(CHROME + [f'--print-to-pdf={src}', 'file://' + str(path)], capture_output=True, timeout=900, check=True); printed = round(time.time() - t1, 1)
                t2 = time.time(); res = conv.convert(src); doc = res.document.export_to_dict(); status = str(res.status)
                rawjson.write_text(json.dumps(doc, ensure_ascii=False))
                for p in (poor_parse_pages(res.confidence) if ext == '.pdf' and not a.no_ocr else []):  # the route's own gate: an unreadable text layer is read again by OCR (printed HTML is our own print: readable)
                    reread[p] = conv_full.convert(src, page_range=(p, p)).document.export_to_dict(); rawpage(p).write_text(json.dumps(reread[p], ensure_ascii=False))
                dt = round(time.time() - t2, 1)
        except Exception as e:  # a tool crash is a result, never a stop
            facts[fid] = {'status': 'FAILED', 'error': repr(e)[:300], 'seconds': round(time.time() - t0, 1)}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(dict(_unsupported(fid, sha, version), status='FAILED', error=repr(e)[:300]))); print(fid, facts[fid], flush=True); continue
        t3 = time.time()
        route = route_for_pdf(doc, fid, sha, dt, version, settings) if ext == '.pdf' else route_for_printed_html(doc, path.read_bytes(), fid, sha, dt, version, settings)
        if reread:
            route['units'] = spliced(route['units'], {p: route_for_pdf(d, fid, sha, dt, version, settings)['units'] for p, d in reread.items()}); route['reread'] = {'full_page_ocr_pages': sorted(reread)}
        flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
        facts[fid] = {'status': status, 'print_seconds': printed, 'docling_seconds': dt, 'adapter_seconds': round(time.time() - t3, 2), 'items': len(flat), 'reread_pages': sorted(reread),
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
