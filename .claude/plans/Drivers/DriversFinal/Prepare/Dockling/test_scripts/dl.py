import time,collections,re,sys
from docling.document_converter import DocumentConverter
base='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/'
files={'10-K':base+'inline_html_cache/0001628280-24-005348.htm','10-Q':base+'inline_html_cache/0001113169-24-000013.htm','8-K EX-99.1':base+'exhibit_html_cache/0000002488-23-000007__EX-99.1.htm'}
conv=DocumentConverter()
ITEM=re.compile(r'^\s*(PART\s+I+V?|Item\s+\d+[A-C]?\.?)',re.I)
for k,f in files.items():
    t=time.time(); d=conv.convert(f).document; dt=time.time()-t
    c=collections.Counter(str(i.label).split('.')[-1] for i,_ in d.iterate_items())
    heads=[(lvl,i.text.strip()[:70]) for i,lvl in d.iterate_items() if 'header' in str(i.label) or 'title' in str(i.label)]
    item_heads=[h for h in heads if ITEM.match(h[1])]
    item_texts=[i.text.strip()[:60] for i,_ in d.iterate_items() if 'text' in str(i.label).lower() and ITEM.match(i.text or '') and len(i.text)<120]
    tabs=d.tables; shapes=[(t.data.num_rows,t.data.num_cols) for t in tabs]
    print(f"\n=== {k}  ({dt:.1f}s)  element counts: {dict(c)}")
    print(f"  headings: {len(heads)}; headings that are Items/Parts: {len(item_heads)}; Item/Part lines left as plain text: {len(item_texts)}")
    print("  first headings:", heads[:8])
    print("  Item lines as plain text (sample):", item_texts[:6])
    print(f"  tables: {len(tabs)}; sample shapes (rows x cols): {shapes[:8]}")
    if tabs:
        t0=next((t for t in tabs if t.data.num_rows>=5),tabs[0])
        print("  one table as markdown:\n"+t0.export_to_markdown(doc=d)[:700])
