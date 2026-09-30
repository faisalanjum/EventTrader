import time
from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
o=PdfPipelineOptions(); o.do_ocr=True; o.heading_hierarchy_options.enabled=True; o.generate_parsed_pages=True
o.do_picture_classification=True
c=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=o),InputFormat.IMAGE:ImageFormatOption(pipeline_options=o)})
for f in ['amd8k.pdf','slide005.jpg']:
    t=time.time(); d=c.convert(f).document
    print(f'\n=== {f} ({time.time()-t:.0f}s)')
    for i,_ in d.iterate_items():
        lab=str(i.label).split('.')[-1]
        extra=''
        if lab=='picture':
            extra=str([a.predicted_classes[0].class_name for a in (i.annotations or []) if hasattr(a,'predicted_classes')][:1]) + ' ' + str(getattr(i,'meta',None))[:120]
        print(f"  {lab}{('-L'+str(i.level)) if hasattr(i,'level') else ''}: {(getattr(i,'text','') or '')[:90]} {extra}")
    print(' tables:',[(x.data.num_rows,x.data.num_cols) for x in d.tables])
