from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
d=DoclingDocument.load_from_json('10k_full.json')
print('hierarchical (one per item, no size cap):', len(list(HierarchicalChunker().chunk(d))))
for mt in [256,512,1024]:
    c=HybridChunker(max_tokens=mt); ch=list(c.chunk(d))
    print(f'hybrid max_tokens={mt}: {len(ch)} chunks')
c=HybridChunker(max_tokens=512); ch=list(c.chunk(d))
x=next(k for k in ch if k.meta.headings and 'RISK' in ' '.join(k.meta.headings))
print('\nsample chunk headings:', x.meta.headings); print('contextualized start:', c.contextualize(x)[:300].replace('\n',' | '))
print('chunk provenance pages:', sorted({p.page_no for it in x.meta.doc_items for p in it.prov}))
