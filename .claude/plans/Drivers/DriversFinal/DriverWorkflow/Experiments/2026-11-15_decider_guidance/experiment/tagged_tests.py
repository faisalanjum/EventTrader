import json,pathlib,sys,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
ss={x['id']:x for x in json.loads((R/'sources.json').read_text())}
roles={
 'current_level':'A currently stated or confirmed forecast level.',
 'current_change':'A currently stated or confirmed forecast of growth or change in the measure.',
 'revision_size':'The amount by which management changes an earlier forecast.',
 'earlier_forecast':'An earlier forecast, only recalled or replaced here.',
 'actual':'An observed result, not a forecast.',
 'analyst_only':'An analyst estimate not clearly confirmed by management.',
 'hypothetical':'An illustrative scenario, not management guidance.',
 'qualification':'A condition, bound or qualification of current guidance.',
 'reaffirm_or_withdraw':'A reaffirmation or withdrawal without a new amount.',
 'other_or_unclear':'None of these, or meaning cannot be established.'}

def tagged(source, needles):
 text=source['text']; occ=[]
 for needle in needles:
  start=0
  while True:
   pos=text.find(needle,start)
   if pos<0:break
   occ.append({'start':pos,'end':pos+len(needle),'text':needle});start=pos+len(needle)
 occ.sort(key=lambda v:(v['start'],v['end']))
 for i,v in enumerate(occ,1):v['tag']=f'V{i:03d}'
 for v in reversed(occ):text=text[:v['start']]+f"[{v['tag']}] "+text[v['start']:]
 return text,occ

tests=[]
pay=ss['PAYX_2025-12-19T09.30']
state,occ=tagged(pay,['18%','11%'])
qs={v['tag']:{'type':'choice','instructions':f"Using the whole transcript, what role does the exact occurrence '{v['text']}' immediately following [{v['tag']}] have? Distinguish current forecasts from results and replaced forecasts.",'criteria':roles} for v in occ}
tests.append({'name':'paychex_tagged_roles','state':state,'occurrences':occ,'questions':qs})
cs=ss['CTAS_2026-03-25T10.00']
state,occ=tagged(cs,['7.6','something less than that'])
qs={}
for v in occ:
 tag=v['tag']; target=f"the exact occurrence '{v['text']}' immediately following [{tag}]"
 qs[tag+'_guidance']={'type':'noul','instructions':f'Does {target} state or qualify management guidance elsewhere in this transcript? Judge it using the whole call, including the question and all qualifications.'}
 qs[tag+'_role']={'type':'choice','instructions':f'Using the whole transcript, what role does {target} have?','criteria':roles}
 for field,label in {'measure':'the financial or operating measure being forecast','value':'the numeric value or bounds that apply, including numbers referred back to','period':'the target period wording','unit':'the unit or scale wording that applies','conditions':'all conditions and qualifications that change this forecast\'s meaning'}.items():
  qs[tag+'_'+field]={'type':'locate','instructions':f"For {target}, locate {label}. Follow references in this transcript. Exclude unrelated actuals and replaced forecasts. Return exact source text only."}
tests.append({'name':'cintas_tagged_fields','state':state,'occurrences':occ,'questions':qs})
(R/'tagged_requests.json').write_text(json.dumps(tests,indent=2))
out=[]
for test in tests:
 t=time.perf_counter()
 try: r={**test,'response':L.decide(test['state'],test['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**test,'error':str(e),'seconds':time.perf_counter()-t}
 out.append(r);(R/'tagged_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':r['name'],'seconds':round(r['seconds'],2),'occurrences':r['occurrences'],'answers':r.get('response',{}).get('answers'),'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
