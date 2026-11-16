import time,collections
from docling.document_converter import DocumentConverter, HTMLFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.backend_options import HTMLBackendOptions
f='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/exhibit_html_cache/0000002488-23-000007__EX-99.1.htm'
c=DocumentConverter(format_options={InputFormat.HTML:HTMLFormatOption(backend_options=HTMLBackendOptions(render_page=True))})
t=time.time(); r=c.convert(f); d=r.document
lab=collections.Counter(str(i.label).split('.')[-1] for i,_ in d.iterate_items())
print(f'render_page: {time.time()-t:.0f}s pages {len(d.pages)} labels {dict(lab)}')
it=next(i for i,_ in d.iterate_items() if i.prov); print('first item prov:', it.prov[0].page_no, it.prov[0].bbox)
t0=d.tables[0]; print('table0 shape', t0.data.num_rows, t0.data.num_cols)
