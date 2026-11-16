import time
from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import VlmPipelineOptions
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat
from docling.pipeline.vlm_pipeline import VlmPipeline
M="qwen3.8:27b-mlx"   # the model already loaded on the Mac (avoid swapping)
vo=ApiVlmOptions(url="http://localhost:11434/v1/chat/completions",
    params={"model":M,"reasoning_effort":"none","max_tokens":4096,"temperature":0},
    prompt="Convert this page to markdown. Keep every heading, list and table exactly as shown; do not add anything.",
    response_format=ResponseFormat.MARKDOWN, timeout=900, scale=1.0)
po=VlmPipelineOptions(enable_remote_services=True, vlm_options=vo)
c=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_cls=VlmPipeline,pipeline_options=po),
                                    InputFormat.IMAGE:ImageFormatOption(pipeline_cls=VlmPipeline,pipeline_options=po)})
for f,kw in [('slide005.jpg',{}),('ex99.pdf',{'page_range':(1,2)})]:
    t=time.time(); r=c.convert(f,**kw); d=r.document
    labs=[str(i.label).split('.')[-1] for i,_ in d.iterate_items()]
    print(f"\n=== {f}: {r.status} {time.time()-t:.0f}s | headings {labs.count('section_header')} tables {len(d.tables)} {[(x.data.num_rows,x.data.num_cols) for x in d.tables]}")
    print(d.export_to_markdown()[:900])
