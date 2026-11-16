"""Read-only grading of saved inference; no model calls or repair of outputs."""
import json
from collections import Counter
from pathlib import Path

ROOT=Path('/tmp/decider_claude_review_20261115/frozen_six')

def read(path, default):
 return json.loads(path.read_text()) if path.exists() else default

def main():
 carriers=read(ROOT/'review_carriers.json',[])
 reviews=read(ROOT/'proposal_reviews.json',{})
 rows=[]; by_source={}
 for c in carriers:
  source=c['source_id']; folder=ROOT/source
  ledger={x['tag']:x for x in read(folder/'ledger.json',[])}
  proposals=read(folder/'proposals.json',[])
  bounds={x['tag']:x for x in read(folder/'bound_holds.json',[])}
  technical=read(folder/'technical_hold.json',None)
  tags={x['tag'] for x in c['number_carriers']}
  ss=[ledger[x['tag']] for x in c['sentence_carriers'] if x['tag'] in ledger]
  ns=[ledger[x] for x in tags if x in ledger]
  matches=[p for p in proposals if tags.intersection(p['aliases']) or
           c['claim_id'] in reviews.get(source+'/'+p['tag'],{}).get('related_claims',[])]
  explanations=[]; complete=[]; source_complete=[]; held=[]
  for p in matches:
   key=source+'/'+p['tag']; review=reviews.get(key)
   if review and c['claim_id'] in review.get('complete_claims',[]):
    source_complete.append(key)
   if review and c['claim_id'] in review.get('complete_claims',[]) and not p['holds']:
    complete.append(key)
   elif p['status']!='rejected':
    held+=p['holds'] or ['H_EVIDENCE']
    if review:held+=review.get('holds',[])
    explanations.append({'proposal':key,'automatic_holds':p['holds'],'review':review})
  for n in ns:
   if n['status']=='held':held.append(n['hold'])
   if n['tag'] in bounds:held.append(bounds[n['tag']]['hold'])
  for s in ss:
   if s['status']=='held':held.append(s['hold'])
  if complete: status='complete'
  elif held: status='held'
  elif technical: status='technical_unassessed'
  elif not (folder/'proposals.json').exists(): status='pending'
  else: status='missed'
  row={**c,'outcome':status,'complete_proposals':complete,
       'source_complete_proposals':source_complete,'holds':sorted(set(held)),
       'number_decisions':[{k:n[k] for k in ['tag','text','status','hold','answer']} for n in ns],
       'sentence_decisions':[{k:s[k] for k in ['tag','text','status','hold','answer']} for s in ss],
       'proposal_review':explanations,'technical':technical}
  rows.append(row)
  by_source.setdefault(source,Counter())[status]+=1
  by_source[source]['reference_claims']+=1
 result={'scope':'79 confirmed source claims in the exposed development reference; 23 other reference entries remain outside this settled-claim count. Not a blind full-record key or corpus accuracy estimate.',
         'counts':dict(Counter(r['outcome'] for r in rows)),
         'source_complete_but_held':sum(bool(r['source_complete_proposals']) and r['outcome']=='held' for r in rows),
         'by_source':{k:dict(v) for k,v in by_source.items()},'claims':rows}
 (ROOT/'review_counts.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['counts','source_complete_but_held','by_source']},indent=2))

if __name__=='__main__':main()
