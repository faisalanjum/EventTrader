import time,collections,json
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc import ContentLayer
d=DoclingDocument.load_from_json('10q_full.json')
# 1 table cells
t=max(d.tables,key=lambda x:x.data.num_rows)
cells=t.data.table_cells
print('biggest 10-Q table',t.data.num_rows,'x',t.data.num_cols,'| col-header cells',sum(c.column_header for c in cells),'| row-header cells',sum(c.row_header for c in cells),'| spanning cells',sum((c.row_span>1 or c.col_span>1) for c in cells),'| cells with bbox',sum(c.bbox is not None for c in cells),'of',len(cells))
print(' caption:', t.caption_text(d)[:80] if t.captions else None, '| footnotes', len(t.footnotes))
print(t.export_to_dataframe(doc=d).head(6).to_string()[:900])
# 2 furniture
lay=collections.Counter(str(i.content_layer).split('.')[-1] for i in d.texts)
lab=collections.Counter(str(i.label).split('.')[-1] for i in d.texts if str(i.content_layer).endswith('FURNITURE'))
print('\ncontent layers:',dict(lay),'| furniture labels:',dict(lab))
