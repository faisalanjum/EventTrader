import json, time, subprocess, collections, re, traceback
import pypdfium2
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling_core.types.doc import DocItemLabel
from sec_headings import apply_sec_levels, item_ids, headers, ITEM, PART
o=PdfPipelineOptions(); o.do_ocr=False; o.table_structure_options.mode=TableFormerMode.FAST
o.heading_hierarchy_options.enabled=True; o.generate_parsed_pages=True
conv=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=o)})
sel=json.load(open('docling_scale_selection.json'))
out=open('scale/results.jsonl','w')
for s in sel:
    rec={k:s[k] for k in ('kind','ticker','acc','mb')}
    pdf=f"scale/{s['ticker']}_{s['acc']}.pdf"
    try:
        t=time.time()
        subprocess.run(['google-chrome','--headless=new','--disable-gpu','--no-sandbox',f'--print-to-pdf={pdf}','--no-pdf-header-footer','file://'+s['path']],capture_output=True,timeout=600)
        rec['print_s']=round(time.time()-t,1); rec['pages']=len(pypdfium2.PdfDocument(pdf))
        t=time.time(); r=conv.convert(pdf); d=r.document; rec['convert_s']=round(time.time()-t,1)
        rec['status']=str(r.status).split('.')[-1]; rec['grade']=str(getattr(r.confidence,'mean_grade','')).split('.')[-1]
        hs=headers(d); rec['headings']=len(hs); rec['tables']=len(d.tables)
        found=item_ids([h.text for h in hs])
        alltexts=[i.text for i in d.texts if len(i.text)<200]
        expected=item_ids(alltexts)
        rec['items_expected']=sorted(set(expected)); rec['items_as_headings']=sorted(set(found))
        rec['items_missing']=sorted(set(expected)-set(found))
        rec['part_headings']=sum(1 for h in hs if PART.match(h.text.strip()))
        apply_sec_levels(d)
        lv=[(h.level,h.text.strip()[:60]) for h in hs]
        rec['items_at_level2_after_rule']=sum(1 for l,t in lv if l==2 and ITEM.match(t))
        rec['tree_sample']=[f"L{l} {t}" for l,t in lv if ITEM.match(t) or PART.match(t) or l<=3][:40]
        d.save_as_json(pdf[:-4]+'_sec.json')
    except Exception as e:
        rec['error']=f"{type(e).__name__}: {str(e)[:300]}"; traceback.print_exc()
    out.write(json.dumps(rec)+'\n'); out.flush()
    print(rec['kind'],rec['ticker'],rec.get('pages'),'pages',rec.get('print_s'),'s print',rec.get('convert_s'),'s convert',rec.get('status'),'items missing',rec.get('items_missing'),rec.get('error',''),flush=True)
