"""Inspect a filing with Docling 2.131.0; run with -i to explore `doc` afterward."""
import argparse
import json
from collections import Counter
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.backend_options import HTMLBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import HeadingHierarchyOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, HTMLFormatOption, PdfFormatOption

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', nargs='?', help='Local HTML/PDF or public document URL')
parser.add_argument('--out', default='docling_output')
parser.add_argument('--render-html', action='store_true', help='Use Playwright for HTML coordinates')
parser.add_argument('--no-ocr', action='store_true', help='Skip OCR for a born-digital PDF')
parser.add_argument('--pages', nargs=2, type=int, metavar=('FIRST', 'LAST'))
parser.add_argument('--show-options', action='store_true')
args = parser.parse_args()

pdf_options = PdfPipelineOptions(
    do_ocr=not args.no_ocr,
    generate_parsed_pages=True,
    heading_hierarchy_options=HeadingHierarchyOptions(enabled=True),
    accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=4),
)
# Keep cover text in the body even when the HTML has no semantic heading tags.
html_options = HTMLBackendOptions(render_page=args.render_html, infer_furniture=False)
if args.show_options:
    print(json.dumps({'pdf': pdf_options.model_dump(mode='json'),
                      'html': html_options.model_dump(mode='json')}, indent=2))
if not args.source:
    if args.show_options:
        raise SystemExit(0)
    parser.error('provide a source or --show-options')

converter = DocumentConverter(format_options={
    InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
    InputFormat.HTML: HTMLFormatOption(backend_options=html_options),
})
kwargs = {'page_range': tuple(args.pages)} if args.pages else {}
result = converter.convert(args.source, **kwargs)
doc = result.document  # `python -i docling_probe.py ...` leaves this available.
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
doc.save_as_json(out / 'document.json')
doc.save_as_markdown(out / 'document.md')
doc.save_as_html(out / 'document.html')
outline = []
for item, depth in doc.iterate_items():
    line = f'{"  " * depth}{item.self_ref} [{item.label}]'
    if hasattr(item, 'level'):
        line += f' heading_level={item.level}'
    line += ' ' + getattr(item, 'text', '').replace('\n', ' ')[:180]
    outline.append(line)
    if str(item.label) in ('section_header', 'title'):
        print(line)
(out / 'outline.txt').write_text('\n'.join(outline), encoding='utf-8')
summary = {
    'status': str(result.status), 'errors': [str(x) for x in result.errors],
    'texts': len(doc.texts), 'tables': len(doc.tables), 'pictures': len(doc.pictures),
    'pages': len(doc.pages), 'text_labels': dict(Counter(str(x.label) for x in doc.texts)),
    'text_items_with_locations': sum(bool(x.prov) for x in doc.texts),
}
(out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
print(f'Full JSON, Markdown, HTML and outline: {out.resolve()}')
if doc.tables:
    print('\nFirst table preview:')
    print(doc.tables[0].export_to_dataframe(doc=doc).head().to_string(index=False))
