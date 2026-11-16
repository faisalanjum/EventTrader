import time
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import VlmPipelineOptions
from docling.pipeline.vlm_pipeline import VlmPipeline
c=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_cls=VlmPipeline, pipeline_options=VlmPipelineOptions())})
t=time.time(); r=c.convert('ex99.pdf', page_range=(1,2)); d=r.document
print('VLM', r.status, f"{time.time()-t:.0f}s for 2 pages")
print([ (str(i.label).split('.')[-1], (getattr(i,'text','') or '')[:50]) for i,_ in d.iterate_items()][:15])
print('tables', len(d.tables), [(x.data.num_rows,x.data.num_cols) for x in d.tables])
