"""Route adapter: Docling, PDF pipeline -> the common route format.
Native PDF originals: anchors are Docling's own page boxes (converted to the key's top-left points). HTML originals
take the printed-PDF route of the study: headless Chrome prints the page, Docling reads the PDF, and the shared linker
places the text back in the original HTML bytes (the print is a derivative, never the evidence). Shape rules only.

    <docling python> -m benchmarks.prepare.grader.adapters.docling_pdf --key <key package> --split development --out <run dir>
                                                    [--catalog CSV] [--limit N] [--no-ocr] [--reuse-raw]

Settings: table structure FAST, heading hierarchy on, OCR on unless --no-ocr (picture text)."""
import argparse
import json
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


def route_for_pdf(doc, file_id, sha256, seconds, version, settings=None):
    units = anchors_from_boxes(doc, to_units(doc, with_index=True))
    placed = [u for u in units if u.get('anchor')]
    units = sorted(placed, key=lambda u: grade.order_key(u['anchor'])) + [u for u in units if not u.get('anchor')]
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds,
            'route': {'name': NAME, 'tool': 'docling', 'version': version, 'settings': settings or {}, 'adapter': 'benchmarks/prepare/grader/adapters/docling_pdf.py', 'linker': None},
            'units': units, 'uncovered': []}


def route_for_printed_html(doc, raw, file_id, sha256, seconds, version, settings=None):
    units = to_units(doc, with_index=True)
    for u in units:
        for c in u.get('cells') or []: c.pop('_i', None)
    linked = anchor.link(raw, units)
    placed = [u for u in linked['units'] if isinstance(u.get('anchor'), (dict, list))]
    linked['units'] = sorted(placed, key=lambda u: grade.order_key(u['anchor'])) + [u for u in linked['units'] if u not in placed]
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds,
            'route': {'name': NAME + ' (printed HTML)', 'tool': 'docling', 'version': version, 'settings': settings or {}, 'adapter': 'benchmarks/prepare/grader/adapters/docling_pdf.py', 'linker': 'benchmarks/prepare/grader/anchor.py'},
            'units': linked['units'], 'uncovered': linked['uncovered']}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    ap.add_argument('--limit', type=int, help='only the N files with most targets (native PDFs first)'); ap.add_argument('--no-ocr', action='store_true')
    ap.add_argument('--reuse-raw', action='store_true', help='adapt saved Docling output again instead of converting')
    a = ap.parse_args(argv)
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, HeadingHierarchyOptions
    import importlib.metadata as md
    version = next((f"{d} {md.version(d)}" for d in ('docling', 'docling-slim') if _installed(md, d)), 'unknown') + f"; docling-core {md.version('docling-core')}"
    opts = PdfPipelineOptions(do_ocr=not a.no_ocr, generate_parsed_pages=True, heading_hierarchy_options=HeadingHierarchyOptions(enabled=True))
    opts.table_structure_options.mode = TableFormerMode.FAST
    settings = {'pipeline': 'PDF', 'table_mode': 'FAST', 'heading_hierarchy': True, 'ocr': not a.no_ocr, 'print': 'google-chrome --headless=new --print-to-pdf' }
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True); (out / 'route').mkdir(exist_ok=True)
    files, counts = {}, {}
    for t in grade.load_key(a.key, a.catalog):
        if t['split'] == a.split: files.setdefault(t['file_id'], (t['path'], t['sha256'])); counts[t['file_id']] = counts.get(t['file_id'], 0) + 1
    order = sorted(files, key=lambda f: (files[f][0].suffix.lower() != '.pdf', -counts[f], f))
    if a.limit: order = order[:a.limit]
    facts = {}
    for fid in order:
        path, sha = files[fid]; ext = path.suffix.lower()
        (out / 'route' / fid).parent.mkdir(parents=True, exist_ok=True); (out / 'raw' / fid).parent.mkdir(parents=True, exist_ok=True)
        if ext not in ('.pdf', '.htm', '.html'):
            (out / 'route' / (fid + '.json')).write_text(json.dumps(_unsupported(fid, sha, version))); facts[fid] = {'status': 'UNSUPPORTED'}; continue
        rawjson = out / 'raw' / (fid + '.docling.json'); t0 = time.time(); printed = 0.0
        try:
            if a.reuse_raw and rawjson.exists():
                doc = json.loads(rawjson.read_text()); prev = (json.loads((out / 'facts.json').read_text())['files'].get(fid) or {}) if (out / 'facts.json').exists() else {}
                dt, printed, status = prev.get('docling_seconds', 0), prev.get('print_seconds', 0), 'reused raw'
            else:
                src = str(path)
                if ext != '.pdf':
                    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False); tmp.close(); src = tmp.name; t1 = time.time()
                    subprocess.run(CHROME + [f'--print-to-pdf={src}', 'file://' + str(path)], capture_output=True, timeout=900, check=True); printed = round(time.time() - t1, 1)
                t2 = time.time(); res = conv.convert(src); doc = res.document.export_to_dict(); dt = round(time.time() - t2, 1); status = str(res.status)
                rawjson.write_text(json.dumps(doc, ensure_ascii=False))
        except Exception as e:  # a tool crash is a result, never a stop
            facts[fid] = {'status': 'FAILED', 'error': repr(e)[:300], 'seconds': round(time.time() - t0, 1)}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(dict(_unsupported(fid, sha, version), status='FAILED', error=repr(e)[:300]))); print(fid, facts[fid], flush=True); continue
        t3 = time.time()
        route = route_for_pdf(doc, fid, sha, dt, version, settings) if ext == '.pdf' else route_for_printed_html(doc, path.read_bytes(), fid, sha, dt, version, settings)
        flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
        facts[fid] = {'status': status, 'print_seconds': printed, 'docling_seconds': dt, 'adapter_seconds': round(time.time() - t3, 2), 'items': len(flat),
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
