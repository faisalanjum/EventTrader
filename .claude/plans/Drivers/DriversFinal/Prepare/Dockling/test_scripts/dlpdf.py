import time,collections,re,sys
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
o=PdfPipelineOptions(); o.do_ocr=False; o.do_table_structure=True
conv=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=o)})
ITEM=re.compile(r'^\s*(PART\s+I+V?|Item\s+\d+[A-C]?\.?)',re.I)
for n in sys.argv[1:]:
    t=time.time(); d=conv.convert(n+'.pdf').document; dt=time.time()-t
    c=collections.Counter(str(i.label).split('.')[-1] for i,_ in d.iterate_items())
    heads=[(lvl,i.text.strip()[:80]) for i,lvl in d.iterate_items() if 'section_header' in str(i.label) or 'title' in str(i.label)]
    items=[h for h in heads if ITEM.match(h[1])]
    plain=[i.text[:60] for i,_ in d.iterate_items() if str(i.label).endswith('text') and ITEM.match(i.text or '') and len(i.text)<120]
    print(f"\n=== {n} ({dt:.0f}s) counts {dict(c)}\n headings {len(heads)}; Item/Part headings {len(items)}; Item lines still plain text {len(plain)}")
    for h in heads[:30]: print('  ',h)
    d.save_as_json(n+'_docling.json')
