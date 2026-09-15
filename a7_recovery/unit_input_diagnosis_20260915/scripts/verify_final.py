import json, glob, os, re
SC='/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad'
def datajson(p):
    i=p.index('"menu"'); j=p.rindex('{',0,i+1); return json.loads(p[j:])

print('FINAL RE-VERIFY of the prompts that will actually be sent')
ok=q=0; n=0; sizes=[]
for tag, pref in (('BBY','0000764478'), ('AAL','0000006201')):
    head=open('%s/HEADFINAL_%s.txt'%(SC,tag)).read()
    for f in sorted(glob.glob('%s/ITEM_*.txt'%SC)):
        pid=os.path.basename(f)[5:-4]
        if pref not in pid: continue
        full=head+open(f).read(); n+=1; sizes.append(len(full))
        try:
            d=datajson(full); ok+=1
            blob=' '.join(p['content'] for p in d['event']['text_parts'])
            if d['item']['quote'] in blob: q+=1
            else: print('  QUOTE LOST:', pid)
        except Exception as e: print('  JSON FAIL:', pid, str(e)[:50])
print('  valid JSON        : %d/%d' % (ok,n))
print('  quotes resolve    : %d/%d' % (q,n))
print('  prompt size range : %d - %d chars' % (min(sizes), max(sizes)))

print()
print('PASS 4 - are the 9 gold answers still derivable?')
key=json.load(open('/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2020_codex_check/codex_final_score2174_a/A7_CORRECTED_SCORE.json'))['key']
for acc, tag in (('0000764478-25-000057','BBY'), ('0000006201-26-000032','AAL')):
    head=open('%s/HEADFINAL_%s.txt'%(SC,tag)).read()
    for r in key[acc]:
        it=r['item']; vals=[]
        for f in ('level_low','level_high','comparison_low','comparison_high'):
            v=it.get(f)
            if isinstance(v,dict) and v.get('value') not in (None,''): vals.append(str(v['value']))
        miss=[v for v in set(vals) if v not in head and v.rstrip('0').rstrip('.') not in head]
        print('  %-6s %-42s values=%-22s all_present=%s' %
              (tag, (it.get('driver_name') or '?')[:42], ','.join(sorted(set(vals)))[:22], not miss))
