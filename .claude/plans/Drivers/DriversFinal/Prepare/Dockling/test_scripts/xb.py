import time, shutil
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
shutil.copy('/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache/0001113169-24-000013.htm','trow_10q.xml')
c=DocumentConverter(allowed_formats=[InputFormat.XML_XBRL])
t=time.time()
try:
    r=c.convert('trow_10q.xml'); d=r.document
    print('XBRL', r.status, f"{time.time()-t:.0f}s", 'tables',len(d.tables), 'texts',len(d.texts))
    print(d.export_to_markdown()[:1500])
except Exception as e: print('XBRL failed:', type(e).__name__, str(e)[:400])
