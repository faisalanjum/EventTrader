"""Source-reference annotations for reviewing this one run; NEVER model input.

These manually read occurrence IDs identify the actual claim, not its containing
paragraph. They are specific test labels, not extraction rules. Numerical
carriers also include their exact containing sentence as a possible held outcome.
Worded/confirmed claims use management's actual statement, not just an analyst
question or an old number. The reference has prior exposure and is not blind gold.
"""
import json
from pathlib import Path

ROOT = Path('/tmp/decider_claude_review_20261115')
SPEC = {
 'CTAS_2025-09-24T10.00': {
  'SEP01':'V017 V018', 'SEP02':'V019 V020', 'SEP03':'V021 V022',
  'SEP04':'V023 V024', 'SEP05':'V063', 'SEP06':'V065',
  'SEP07':'V096 V097', 'SEP08':'S245', 'SEP09':'S243',
  'SEP11':'S370 S372 S380', 'SEP13':'S485', 'SEP15':'V160',
 },
 'CTAS_2025-12-18T10.00': {
  'DEC01':'V016 V017', 'DEC02':'V018 V019', 'DEC03':'V020 V021',
  'DEC04':'V022 V023', 'DEC05':'V069', 'DEC06':'V071',
  'DEC07':'S137', 'DEC08':'V091 V092', 'DEC09':'V100 V101',
  'DEC10':'V105 V106', 'DEC11':'V108 V109', 'DEC12':'S262',
  'DEC14':'S387', 'DEC15':'V143',
 },
 'CTAS_2026-03-25T10.00': {
  'MAR01':'V015 V016', 'MAR02':'V017 V018', 'MAR03':'V019 V020',
  'MAR04':'V021 V022', 'MAR05':'V059', 'MAR06':'V061',
  'MAR07':'V053', 'MAR08':'V065 V066', 'MAR09':'S121',
  'MAR11':'S227', 'MAR12':'V106', 'MAR13':'V107',
  'MAR15':'S409', 'MAR16':'S514',
 },
 'PAYX_2025-09-30T09.30': {
  'P1-01':'V012', 'P1-02':'V045 V046', 'P1-03':'V047 V048',
  'P1-04':'V050 V051', 'P1-05':'V052 V053', 'P1-06':'V054 V055',
  'P1-07':'V056', 'P1-08':'V057 V058', 'P1-09':'V059 V060',
  'P1-10':'V063', 'P1-11':'V065', 'P1-12':'S096',
  'P1-13':'S123', 'P1-15':'V102',
 },
 'PAYX_2025-12-19T09.30': {
  'P2-01':'V009 V070', 'P2-02':'S083', 'P2-03':'S083', 'P2-04':'S083',
  'P2-05':'V044 V045', 'P2-06':'V046 V047', 'P2-07':'V050',
  'P2-09':'V051', 'P2-10':'V052 V053', 'P2-11':'S240',
  'P2-12':'S504', 'P2-13':'V152',
 },
 'PAYX_2026-03-25T09.30': {
  'P3-01':'V055 V056', 'P3-03':'V057', 'P3-04':'V058 V059',
  'P3-05':'V080', 'P3-06':'V081', 'P3-07':'S326',
  'P3-08':'S348', 'P3-09':'S349', 'P3-10':'S054',
  'P3-11':'V149 V150 S383', 'P3-15':'S514 S515',
  'P3-17':'S566', 'P3-18':'S647',
 },
}

def main():
 rows=[]
 for source_id, claims in SPEC.items():
  data=json.loads((ROOT/'frozen_six'/(source_id+'_input.json')).read_text())
  ref=json.loads((ROOT/'reference_key'/(source_id+'.json')).read_text())
  keys={c['id']:c for c in ref['claims'] if c['status']=='confirmed_claim'}
  assert set(claims)==set(keys)
  index={x['tag']:x for x in data['numbers']+data['sentences']}
  for cid,tags in claims.items():
   c=keys[cid]; selected=[index[t] for t in tags.split()]
   for x in selected:
    assert data['text'][x['start']:x['end']]==x['text']
    assert any(e['global_start']<x['end'] and x['start']<e['global_end'] for e in c['evidence'])
   ns=[x for x in selected if x['tag'].startswith('V')]
   ss=[x for x in selected if x['tag'].startswith('S')]
   ss+=[s for s in data['sentences'] if any(s['start']<=n['start']<s['end'] for n in ns)]
   ss=list({s['tag']:s for s in ss}.values())
   rows.append({'source_id':source_id,'claim_id':cid,'meaning':c['meaning'],
                'number_carriers':ns,'sentence_carriers':ss,
                'reference_status':c['status'], 'complete_record_gold':False})
 assert len(rows)==79
 (ROOT/'frozen_six/review_carriers.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('79 source-reference claim mappings checked; no model calls; no changes to frozen inference.')

if __name__=='__main__': main()
