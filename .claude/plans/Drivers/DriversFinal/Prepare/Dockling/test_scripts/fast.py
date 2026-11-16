import time
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
for m in [TableFormerMode.FAST, TableFormerMode.ACCURATE]:
    o=PdfPipelineOptions(); o.do_ocr=False; o.table_structure_options.mode=m
    c=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=o)})
    t=time.time(); d=c.convert('ex99.pdf').document
    tb=[x for x in d.tables if x.data.num_rows>8][0]
    print(m.value, f"{time.time()-t:.0f}s", 'tables',len(d.tables), 'shape',(tb.data.num_rows,tb.data.num_cols))
    print(tb.export_to_markdown(doc=d)[:600])
