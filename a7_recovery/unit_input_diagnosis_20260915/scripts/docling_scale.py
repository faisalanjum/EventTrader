import os, random, time
from docling.document_converter import DocumentConverter
D='/home/faisal/EventMarketDB/scripts/driver_seed/relocate_probe/inline_html_cache'
files=sorted(os.listdir(D))
by={}
for f in files: by.setdefault(f.split('-')[0], []).append(f)
random.seed(23)
sample=[random.choice(v) for v in by.values()]; random.shuffle(sample); sample=sample[:30]
conv=DocumentConverter()
ok=fail=tables=0; times=[]; sizes=0
for fn in sample:
    p=os.path.join(D,fn); sizes+=os.path.getsize(p)
    t0=time.time()
    try:
        d=conv.convert(p).document
        tables+=len(d.tables); ok+=1
    except Exception as e:
        fail+=1; print('FAIL', fn, type(e).__name__)
    times.append(time.time()-t0)
times.sort()
print()
print('filings          : %d   (distinct filers in cache: %d)' % (len(sample), len(by)))
print('parsed OK        : %d' % ok)
print('failed           : %d' % fail)
print('tables recovered : %d  (avg %.0f per filing)' % (tables, tables/max(ok,1)))
print('median time      : %.2fs   p95: %.2fs   total input: %.0f MB' %
      (times[len(times)//2], times[int(len(times)*0.95)], sizes/1e6))
print('projected 1,769  : %.1f minutes' % (sum(times)/len(times)*1769/60))
