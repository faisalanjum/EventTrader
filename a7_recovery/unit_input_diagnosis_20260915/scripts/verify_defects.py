"""The three exam defects, checked against the SERVED prompt bytes and the key."""
import json, re
P='/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_input_diagnosis_20260915/prompts'
KEY=json.load(open('/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2020_codex_check/'
                   'codex_final_score2174_a/A7_CORRECTED_SCORE.json'))['key']
served=open('%s/SEND_0000764478-25-000057_045.txt'%P).read()
rules=served[:served.index('Everything below is ONE JSON object')]

print('DEFECT 1 - the key applies a period-window rule the served rules never state')
print('  key note (asset_impairment / revenue_mix) applies an "all-or-nothing window"')
for t in ['all-or-nothing','all or nothing','both dates','start and end','close the window',
          'period_start_date is required','requires both']:
    print('    served rules contain %-30r : %d' % (t, rules.lower().count(t.lower())))
g=[r for r in KEY['0000764478-25-000057'] if r['item']['driver_name']=='revenue_mix'][1]
print('    gold YTD record period_start_date =', g['item']['period_start_date'],
      '(inferred, not stated in the source)')

print()
print('DEFECT 2 - the menu offers two interchangeable tokens for one business part')
for t in ['segment:domestic','segment:domesticsegment','segment:international','segment:internationalsegment']:
    print('    menu contains %-32r : %s' % (t, ('"%s"'%t) in served))
print('    gold slice_parts for revenue_mix =', g['item']['slice_parts'])

print()
print('DEFECT 3 - the menu and the key encode the same slice differently')
gi=[r for r in KEY['0000764478-25-000057'] if r['item']['driver_name']=='asset_impairment'][0]['item']
gold_tok=gi['slice_parts'][0]
menu_tok='unknown:us-gaap:ReportingUnitAxis__bestbuyhealth'
print('    menu shows  :', menu_tok, '  present in served prompt:', ('"%s"'%menu_tok) in served)
print('    key expects :', gold_tok)
print('    key token present in served prompt:', gold_tok in served)
h=re.search(r'xbrlaxis_([0-9a-f]+)__', gold_tok)
print('    key hex decodes to:', bytes.fromhex(h.group(1)).decode())
print('    served rule says: "cite it as the menu\'s reference token string, exactly as the menu shows it"'
      , '->', ' '.join('exactly as the menu shows it'.split()) in ' '.join(rules.split()))
