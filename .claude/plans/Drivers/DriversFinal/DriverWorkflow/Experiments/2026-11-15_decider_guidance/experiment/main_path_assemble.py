"""Deterministic source-evidence assembly; unresolved fields are never invented."""
import json,pathlib,sys,re,collections
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
R=T.R
b=json.loads((R/'B_result.json').read_text())
choices=json.loads((R/'C_choices_result.json').read_text())['response']['answers']
targets=json.loads((R/'C_targets.json').read_text())
# Rebuild the exact tagged state and its character map, rather than matching repeated strings.
parts=[]; maps=[];original=[]; offset=0
for p in T.source['passages']:
 text=p['text'];insertions=[]
 for c in b['sentences']+b['candidates']:
  if c['passage']==p['id']:insertions.append((c['start'],'['+c['tag']+'] '))
 mapping=list(range(offset,offset+len(text)))
 for start,label in sorted(insertions,reverse=True):
  text=text[:start]+label+text[start:];mapping[start:start]=[None]*len(label)
 prefix='['+p['id']+'] '
 parts.append(prefix+text);maps.append([None]*len(prefix)+mapping)
 original.append(p['text']);offset+=len(p['text'])+2
original='\n\n'.join(original)
assert original==T.source['text']
state=T.HEADER+'\n\n'.join(parts)
assert state==b['state']
wholemap=[None]*len(T.HEADER)
for i,m in enumerate(maps):
 if i:wholemap.extend([None,None])
 wholemap.extend(m)
assert len(wholemap)==len(state)
starts=[(state.index('['+p['id']+'] '),p) for p in T.source['passages']]
contexts={}
for i,(start,p) in enumerate(starts):
 end=starts[i+1][0] if i+1<len(starts) else len(state)
 contexts[p['id']]=(state[start:end],wholemap[start:end])

def localmap(local):
 m=[None]*len(local)
 for p in T.source['passages']:
  text,segmentmap=contexts[p['id']]
  pos=local.find(text)
  if pos>=0:m[pos:pos+len(text)]=segmentmap
 return m

def mapped_span(span,local,mapping):
 assert local[span['start']:span['end']]==span['text']
 positions=[x for x in mapping[span['start']:span['end']] if x is not None]
 if not positions:return {'error':'No source characters; metadata/tags are not evidence.','returned':span}
 assert positions==sorted(positions)
 start,end=min(positions),max(positions)+1
 return {'start':start,'end':end,'text':original[start:end],'score':span['score']}
fields={}
for f in sorted(R.glob('C_copy_*_result.json')):
 d=json.loads(f.read_text());m=localmap(d['state'])
 for q,a in d['response']['answers'].items():fields[q]=[mapped_span(s,d['state'],m) for s in a['spans']]
optional=R/'D_optional_result.json'
if optional.exists():
 d=json.loads(optional.read_text())
 assert d['state']==state
 for q,a in d['response']['answers'].items():fields[q]=[mapped_span(s,state,wholemap) for s in a['spans']]
rows=[]
for c in targets:
 tag=c['tag'];row={'tag':tag,'kind':c['kind'],'passage':c['passage'],'target_text':c['text'],'choices':{},'fields':{},'reasons':[]}
 for q,a in choices.items():
  if q.startswith(tag+'_'):row['choices'][q[len(tag)+1:]]=a
 form=row['choices']['form']['choice']
 if form in ['none','unclear','several']:
  row['reasons'].append('form_'+form)
 else:
  for key in ['measure','value','context','conditions','comparison_revision']:
   row['fields'][key]=fields.get(tag+'_'+key,[])
  for key in ['measure','value','context']:
   if not row['fields'][key]:row['reasons'].append('missing_'+key)
  for key in ['conditions','comparison_revision']:
   if row['choices'][key]['noul']>=.5 and not row['fields'][key]:row['reasons'].append('positive_presence_missing_'+key)
  for key in ['period','subject_scope','unit_scale','sign','time_type','movement']:
   value=row['choices'][key]['choice']
   if value in ['unclear','several','other_subject','other_stated']:row['reasons'].append(key+'_'+value)
  if form in ['centre_tolerance','reaffirmation','withdrawal','qualification','revision']:
   row['reasons'].append('requires_supported_association_or_encoding_'+form)
  support=[s for spans in row['fields'].values() for s in spans if 'start' in s]
  if any('error' in s for spans in row['fields'].values() for s in spans):row['reasons'].append('non_source_span')
  if support:
   start=min(s['start'] for s in support);end=max(s['end'] for s in support)
   row['quote']={'start':start,'end':end,'text':original[start:end]}
   assert row['quote']['text']==original[start:end]
 row['status']='rejected' if form=='none' else 'unresolved' if row['reasons'] else 'fields_present_for_independent_review'
 # This status does not certify meaning, normalization, canonical identity, all conditions or completeness.
 rows.append(row)
T.save('E_proposals',{'source':T.source['id'],'original_sha256':T.hashlib.sha256(original.encode()).hexdigest(),'proposals':rows,'note':'Exact source mapping is verified. fields_present_for_independent_review is NOT a correct/accepted record count. No repaired or inferred values.'})
summary={'targets':len(rows),'statuses':dict(collections.Counter(x['status'] for x in rows)),'reasons':dict(collections.Counter(k for x in rows for k in x['reasons']))}
T.save('E_assembly_summary',summary)
with (R.parent/'progress.md').open('a') as f:
 f.write('\nTest: E, deterministic assembly of actual C/D outputs with exact mapping back to the original CTAS transcript.\n')
 f.write('Result: '+json.dumps(summary)+'. Field presence is not semantic correctness; independent record review is still required.\n')
 f.write('Next: Audit all proposed/rejected/held targets against source requirements, report the end-to-end outcome and select only a justified generic next fix.\n')
print(json.dumps(summary),flush=True)
