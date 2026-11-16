import time,collections,re,sys,json
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
def conv(mode=TableFormerMode.ACCURATE, hh=True):
    o=PdfPipelineOptions(); o.do_ocr=False; o.table_structure_options.mode=mode
    o.heading_hierarchy_options.enabled=hh; o.generate_parsed_pages=hh
    return DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=o)})
C=conv(); out={}
for n in sys.argv[1:]:
    t=time.time(); r=C.convert(n+'.pdf'); d=r.document; dt=time.time()-t
    heads=[(i.level if hasattr(i,'level') else lvl, i.text.strip()[:70]) for i,lvl in d.iterate_items() if 'section_header' in str(i.label)]
    lv=collections.Counter(h[0] for h in heads)
    first=next(i for i,_ in d.iterate_items() if 'section_header' in str(i.label))
    prov=first.prov[0] if first.prov else None
    md=d.export_to_markdown(); html=d.export_to_html(); dt_tags=d.export_to_doctags()
    ch=list(HybridChunker().chunk(d)); 
    paths=[" > ".join(c.meta.headings or []) for c in ch]
    print(f"\n=== {n}: {len(r.pages)} pages, {dt:.0f}s, status {r.status}, confidence {getattr(r.confidence,'mean_grade',None)}")
    print(" heading levels:", dict(sorted(lv.items())))
    for h in heads[:40]: print("   "+"  "*(h[0]-1)+f"L{h[0]} {h[1]}")
    print(" provenance of first heading:", prov.page_no if prov else None, prov.bbox if prov else None)
    print(f" tables {len(d.tables)}; exports: md {len(md):,} ch, html {len(html):,}, doctags {len(dt_tags):,}")
    print(f" chunks {len(ch)}; sample chunk heading paths:", [p for p in paths if p][:6])
    d.save_as_json(n+'_full.json')
