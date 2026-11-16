import re
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
KEY=re.compile(r'^(PART|Item|ITEM|NOTE)\b')
for name,kw in [('numbering only',dict(use_style=False)),('style only',dict(use_numbering=False))]:
    o=PdfPipelineOptions(); o.do_ocr=False; o.generate_parsed_pages=True; o.heading_hierarchy_options.enabled=True
    for k,v in kw.items(): setattr(o.heading_hierarchy_options,k,v)
    d=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=o)}).convert('10q.pdf').document
    hs=[(i.level,i.text.strip()[:55]) for i,_ in d.iterate_items() if 'section_header' in str(i.label) and KEY.match(i.text.strip())]
    print(f'\n== {name}:'); [print('  '+'  '*(l-1)+f'L{l} {t}') for l,t in hs[:22]]
