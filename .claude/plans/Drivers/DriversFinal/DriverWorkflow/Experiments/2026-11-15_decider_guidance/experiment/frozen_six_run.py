"""One bounded six-call diagnostic. No reference answers, repair loop or writer.

Uses existing native segmentation, metadata exclusion, choice definitions,
number normalization and period resolution. Every request and outcome is saved.
The reference inventory is read only by the separate post-run review.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
from collections import Counter
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

ROOT = Path('/tmp/decider_claude_review_20261115')
OUT = ROOT / 'frozen_six'
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor'), '/home/faisal/EventMarketDB']
import pysbd
from config import local_llm as L
from metadata_candidates import digit_tokens
from proposal_numbers import normalize
from passage_cohort_check import DEFINITION
from sentence_screen_check import TASK
from driver_reference.core.driver_period_resolver import ensure_driver_period


def stamp():
    return datetime.now(ZoneInfo('America/Toronto')).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def log(test, result, next_step):
    with (ROOT / 'progress.md').open('a') as f:
        f.write(f'\nTest: {test}\nResult: {result}\nNext: {next_step}\n')


def json_after(state, marker):
    return json.JSONDecoder().raw_decode(state.split(marker, 1)[1])[0]


def configuration():
    field_request = json.loads((ROOT / 'quote_fields/basis_check_request.json').read_text())
    state = field_request['state']
    fields = json_after(state, 'FIELD_RULES:\n')
    time_line = next(x for x in state.splitlines() if x.startswith('TIME_TYPE_DEFINITION:'))
    fields['time_type'] = {'instructions': time_line.split(': ', 1)[1].split(' Choose from')[0],
                           'criteria': json.loads(time_line[time_line.index('{'):])}
    basis_start = state.index('GROWTH_BASIS_TASK:')
    basis_end = state.index('UNIT_RULE_3_33', basis_start)
    basis_definition = state[basis_start:basis_end].strip()
    fields['basis_evidence'] = {
        'instructions': 'Which GROWTH_BASIS_TASK option is supported for this exact target?',
        'criteria': field_request['questions']['F0_basis_evidence']['criteria']}
    remaining = json.loads((ROOT / 'prepared_record/request.json').read_text())['state']
    fields['amount_meaning'] = {
        'instructions': 'What does this amount represent? A forecast change in the underlying measure is a value; only a revision of the forecast itself is a guidance revision.',
        'criteria': json_after(remaining, 'MEANING_OPTIONS=')}
    fields['comparison_baseline'] = {
        'instructions': 'Which headline comparison is explicitly stated for this forecast? A target year alone is not a comparison. A baseline may be stated without a number; never invent one.',
        'criteria': json_after(remaining, 'COMPARISON_OPTIONS=')}
    original = json.loads((ROOT / 'main_path/B_result.json').read_text())
    roles = next(q['criteria'] for q in original['questions'].values() if q['type'] == 'choice')
    bound = json.loads((ROOT / 'main_path/numeric_bounds_request.json').read_text())
    special = {k:v for k,v in next(iter(bound['questions'].values()))['criteria'].items()
               if not (k.startswith('V') and k[1:].isdigit())}
    return {'definition': DEFINITION, 'screen_task': TASK, 'roles': roles,
            'fields': fields, 'units': json_after(state, 'UNIT_OPTIONS:\n'),
            'period_menu': json_after(state, 'PERIOD_OPTIONS:\n'),
            'basis_definition': basis_definition,
            'unit_rule': next(x for x in state.splitlines() if x.startswith('UNIT_RULE_3_33')),
            'bound_rule': 'For the current management forecast containing the target, select the requested lower or upper value. A point forecast uses the same occurrence for both values; a closed range uses its two stated endpoints; a one-sided bound leaves the other side unstated. Resolve using the whole call. If this occurrence is not a current forecast amount, choose no_current_forecast; never substitute another forecast or calculate an unstated amount.',
            'bound_special': special, 'sentence_cutoff': .25, 'choice_cutoff': .5,
            'optional_cutoff': .5, 'model': 'pplx-decider-v1.3:8bit',
            'mode': 'isolated', 'timeout': 1800,
            'limits': 'Diagnostic cutoffs, not calibrated acceptance. Calendar menu is the existing verified month-end development-fixture menu; it is not a generic calendar service. All other dates/units remain held. Main strategy is not changed.'}


def prepare(source):
    assert source['text'] == '\n\n'.join(p['text'] for p in source['passages'])
    speaker_value = source['meta'].get('speakers', {})
    speakers = json.loads(speaker_value) if isinstance(speaker_value, str) else speaker_value
    segmenter = pysbd.Segmenter(language='en', clean=False, char_span=True)
    sentences, numbers, passages = [], [], []
    offset = 0
    for p in source['passages']:
        text = p['text']
        spans = segmenter.segment(text)
        covered = set()
        for span in spans:
            assert text[span.start:span.end] == span.sent
            assert not covered.intersection(range(span.start, span.end))
            covered.update(range(span.start, span.end))
            sentences.append({'tag': f'S{len(sentences):03d}', 'passage': p['id'],
                              'start': offset+span.start, 'end': offset+span.end, 'text': span.sent})
        assert all(i in covered or c.isspace() for i,c in enumerate(text))
        entries = p.get('entries') or [{'text': text}]
        assert '\n'.join(e['text'] for e in entries) == text
        local = 0
        for e in entries:
            for n in digit_tokens(e['text'], speakers, e.get('speaker')):
                numbers.append({'tag': f'V{len(numbers):03d}', 'passage': p['id'],
                                'start': offset+local+n['start'], 'end': offset+local+n['end'],
                                'text': n['text']})
            local += len(e['text'])+1
        passages.append({'id':p['id'], 'kind':p['kind'], 'start':offset, 'end':offset+len(text)})
        offset += len(text)+2
    for item in sentences+numbers:
        assert source['text'][item['start']:item['end']] == item['text']
        assert '['+item['tag']+']' not in source['text']
    meta = source['meta']
    fy = str(meta['fiscal_year']).replace(',', '')
    header = (f'Source: {source["id"]}. Company: {meta.get("company", meta.get("company_name"))}. '
              f'Call: {meta.get("date", meta.get("created"))}. Reported fiscal Q{meta["fiscal_quarter"]} FY{fy}. '
              'Development fixture calendar: ordinary fiscal year ending May 31. '
              'Metadata does not supply an unstated forecast period.\n')
    return {'source_id': source['id'], 'text':source['text'], 'header':header,
            'sentences':sentences, 'numbers':numbers, 'passages':passages,
            'source_sha256':hashlib.sha256(source['text'].encode()).hexdigest()}


def render(data, start=0, end=None):
    end = len(data['text']) if end is None else end
    text = data['text'][start:end]
    mapping = list(range(start,end))
    for item in sorted(data['sentences']+data['numbers'], key=lambda x:(x['start'],x['tag']), reverse=True):
        if start <= item['start'] < end:
            pos = item['start']-start
            label = '['+item['tag']+'] '
            text = text[:pos]+label+text[pos:]
            mapping[pos:pos] = [None]*len(label)
    assert len(text) == len(mapping)
    assert ''.join(c for c,m in zip(text,mapping) if m is not None) == data['text'][start:end]
    return text,mapping


def invoke(folder, name, state, questions, cfg):
    assert questions
    assert all(len(q.get('criteria',{}))<=255 for q in questions.values())
    if any(q['type']=='locate' for q in questions.values()):
        assert len(questions)<=128
    path=folder/(name+'_result.json')
    assert not path.exists(), 'One run only: inspect saved result, never overwrite.'
    request={'state':state,'questions':questions,'mode':cfg['mode']}
    save(folder/(name+'_request.json'),request)
    print(json.dumps({'source':folder.name,'stage':name,'started':stamp(),'questions':len(questions)}),flush=True)
    result={'started_at':stamp(),'request_sha256':digest(folder/(name+'_request.json'))}
    t=time.monotonic()
    try:
        result['response']=L.decide(**request,timeout=cfg['timeout'])
        assert result['response']['model']==cfg['model']
        assert set(result['response']['answers'])==set(questions)
    except Exception as e:
        result['error']=repr(e)
    result.update(seconds=time.monotonic()-t,finished_at=stamp())
    save(path,result)
    log(f'Frozen six-call run {folder.name}/{name}, {len(questions)} questions.',
        f'{result["seconds"]:.2f}s; usage={result.get("response",{}).get("usage")}; error={result.get("error")}.',
        'Continue this fixed procedure without repairs; score all six and wait for owner.')
    print(json.dumps({'source':folder.name,'stage':name,'seconds':result['seconds'],
                      'usage':result.get('response',{}).get('usage'),'error':result.get('error')}),flush=True)
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result['response']['answers']


def mapped(span,state,mapping,source,body_start):
    assert state[span['start']:span['end']]==span['text']
    if span['start']<body_start:
        return {'error':'H_EVIDENCE','returned':span,'reason':'Non-source header.'}
    positions=[p for p in mapping[span['start']:span['end']] if p is not None]
    if not positions or positions != list(range(min(positions),max(positions)+1)):
        return {'error':'H_EVIDENCE','returned':span,'reason':'Missing/noncontinuous source positions.'}
    a,z=positions[0],positions[-1]+1
    return {'start':a,'end':z,'text':source[a:z],'score':span['score']}


def one_call(data,cfg):
    folder=OUT/data['source_id'];folder.mkdir()
    save(folder/'prepared.json',data)
    tagged,_=render(data)
    state=data['header']+cfg['definition']+'\n'+cfg['screen_task']+'\nNUMERIC_ROLES:\n'+json.dumps(cfg['roles'])+'\n\n'+tagged
    q={s['tag']:{'type':'noul','instructions':f'Does sentence [{s["tag"]}] meet SCREEN_TASK?'} for s in data['sentences']}
    q.update({n['tag']:{'type':'choice','instructions':f'What is the role of the exact source occurrence {n["text"]!r} at [{n["tag"]}] under NUMERIC_ROLES? Use the whole call.','criteria':{k:None for k in cfg['roles']}} for n in data['numbers']})
    scan=invoke(folder,'01_scan',state,q,cfg)
    ledger=[];selected=[]
    for n in data['numbers']:
        a=scan[n['tag']];p=a['probabilities'][a['choice']]
        if p<cfg['choice_cutoff']:status,hold='held','H_CONFIDENCE'
        elif a['choice']=='current':status,hold='numeric_candidate',None;selected.append(n)
        elif a['choice'] in ['qualification','unclear']:status,hold='held','H_ASSOCIATION'
        else:status,hold='not_current',None
        ledger.append({**n,'kind':'number','answer':a,'status':status,'hold':hold})
    for s in data['sentences']:
        a=scan[s['tag']]
        selected_sentence=a['noul']>=cfg['sentence_cutoff']
        ledger.append({**s,'kind':'sentence','answer':a,
                       'status':'held' if selected_sentence else 'not_selected',
                       'hold':'H_SENTENCE_UNRESOLVED' if selected_sentence else None})
    save(folder/'ledger.json',ledger)
    if not selected:
        save(folder/'proposals.json',[]);return
    by_tag={n['tag']:n for n in data['numbers']}
    q={}
    for n in selected:
        options={x['tag']:None for x in data['numbers'] if x['passage']==n['passage']}
        options.update({k:None for k in cfg['bound_special']})
        for side in ['lower','upper']:
            q[n['tag']+'_'+side]={'type':'choice','instructions':f'For the exact source occurrence {n["text"]!r} at [{n["tag"]}], select its {side} value under BOUND_SELECTION_RULES.','criteria':options}
    bound_state='BOUND_SELECTION_RULES:\n'+cfg['bound_rule']+'\nAlternative meanings:\n'+json.dumps(cfg['bound_special'])+'\n'+state
    bounds=invoke(folder,'02_bounds',bound_state,q,cfg)
    groups={};bound_holds=[]
    for n in selected:
        answers={side:bounds[n['tag']+'_'+side] for side in ['lower','upper']}
        values=tuple(answers[side]['choice'] for side in ['lower','upper'])
        confidence=min(a['probabilities'][a['choice']] for a in answers.values())
        if confidence<cfg['choice_cutoff'] or any(v not in by_tag and v!='no_stated_bound' for v in values):
            bound_holds.append({**n,'hold':'H_CONFIDENCE' if confidence<cfg['choice_cutoff'] else 'H_BOUNDS','answers':answers})
            continue
        if values==('no_stated_bound','no_stated_bound'):
            bound_holds.append({**n,'hold':'H_BOUNDS','answers':answers});continue
        group=groups.setdefault(values,{'tag':n['tag'],'anchor':n,'lower':values[0],'upper':values[1],'aliases':[],'bound_answers':[]})
        group['aliases'].append(n['tag']);group['bound_answers'].append(answers)
    save(folder/'bound_holds.json',bound_holds)
    targets=list(groups.values());save(folder/'targets.json',targets)
    if not targets:
        save(folder/'proposals.json',[]);return
    field_state=data['header']+cfg['definition']+'\n'+cfg['unit_rule']+'\n'+cfg['basis_definition']+'\nFIELD_RULES:\n'+json.dumps(cfg['fields'])+'\nPERIOD_OPTIONS:\n'+json.dumps(cfg['period_menu'])+'\nUNIT_OPTIONS:\n'+json.dumps(cfg['units'])+'\nSOURCE:\n'+tagged
    q={}
    optional={
        'conditions':'any applicable assumption, exclusion, dependency or qualification that changes this forecast meaning, including a shared statement elsewhere in the call; exclude generic boilerplate and mere causes',
        'comparison_revision':'any explicitly stated earlier-forecast comparison or size of revision; exclude values only obtainable by arithmetic'}
    for t in targets:
        target=f'{t["anchor"]["text"]!r} at [{t["tag"]}]'
        for key,r in cfg['fields'].items():
            q[t['tag']+'_'+key]={'type':'choice','instructions':f'For {target} in SOURCE, answer {key} using FIELD_RULES.','criteria':{k:None for k in r['criteria']}}
        for key,description in optional.items():
            q[t['tag']+'_'+key]={'type':'noul','instructions':f'Does management explicitly attach {description} to {target}?'}
    fields=invoke(folder,'03_fields',field_state,q,cfg)
    copying=[];preholds={}
    form_holds={'words':'H_WORDS','several':'H_MULTIPLE','centre_tolerance':'H_RULE_TOLERANCE',
                'reaffirmation':'H_PRIOR_SCOPE','withdrawal':'H_PRIOR_SCOPE',
                'revision':'H_FIELD','qualification':'H_ASSOCIATION','unclear':'H_FIELD'}
    for t in targets:
        form=fields[t['tag']+'_form']['choice']
        if form in form_holds:preholds[t['tag']]=[form_holds[form]]
        elif form=='none':preholds[t['tag']]=['REJECTED_NOT_GUIDANCE']
        else:copying.append(t)
    # Local copying uses full prepared remarks or a complete stored exchange.
    # Required evidence elsewhere may still fail; never fill it from the key.
    local_groups={}
    for t in copying:
        p=next(p for p in data['passages'] if p['id']==t['anchor']['passage'])
        key='prepared' if p['kind']=='prepared' else p['id']
        local_groups.setdefault(key,[]).append(t)
    copies={}
    for key,ts in local_groups.items():
        ps=[p for p in data['passages'] if p['kind']=='prepared'] if key=='prepared' else [p for p in data['passages'] if p['id']==key]
        text,m=render(data,min(p['start'] for p in ps),max(p['end'] for p in ps))
        prefix=data['header']+cfg['definition']+'\n\n';local=prefix+text;mapping=[None]*len(prefix)+m
        q={}
        for t in ts:
            target=f'{t["anchor"]["text"]!r} at [{t["tag"]}]'
            for name,label in {
                'measure':'source wording naming the financial or operating measure, including applicable business scope; follow references including confirmed analyst wording; not a bare amount, date or unit',
                'context':'source wording giving the target period, unit and scale applying to this forecast',
                'qualifiers':'exact qualifying words that specify measurement, approximation, strict bounds, or growth/change meaning; do not return the amount or a cause'
            }.items():
                q[t['tag']+'_'+name]={'type':'locate','instructions':f'For the current management forecast {target}, copy {label}.'}
        items=list(q.items())
        for i in range(0,len(items),128):
            answer=invoke(folder,f'04_copy_{key}_{i//128}',local,dict(items[i:i+128]),cfg)
            for qid,a in answer.items():copies[qid]=[mapped(s,local,mapping,data['text'],len(prefix)) for s in a['spans']]
    q={}
    for t in copying:
        target=f'{t["anchor"]["text"]!r} at [{t["tag"]}]'
        for key in optional:
            if fields[t['tag']+'_'+key]['noul']>=cfg['optional_cutoff']:
                desc=('every applicable forecast assumption, exclusion or dependency, including shared guidance assumptions when applicable; not generic boilerplate or causes'
                      if key=='conditions' else 'any explicitly stated comparison or revision amount, its unit and baseline; not a derived value')
                q[t['tag']+'_'+key]={'type':'locate','instructions':f'For the current management forecast {target}, copy {desc}.'}
    if q:
        text,m=render(data);prefix=data['header']+cfg['definition']+'\n\n';local=prefix+text;mapping=[None]*len(prefix)+m
        items=list(q.items())
        for i in range(0,len(items),128):
            answer=invoke(folder,f'05_optional_{i//128}',local,dict(items[i:i+128]),cfg)
            for qid,a in answer.items():copies[qid]=[mapped(s,local,mapping,data['text'],len(prefix)) for s in a['spans']]
    save(folder/'copies.json',copies)
    proposals=[]
    for t in targets:
        answers={k:fields[t['tag']+'_'+k] for k in list(cfg['fields'])+list(optional)}
        values={k:a['choice'] for k,a in answers.items() if a['type']=='choice'}
        holds=list(preholds.get(t['tag'],[]))
        if any(a['probabilities'][a['choice']]<cfg['choice_cutoff'] for a in answers.values() if a['type']=='choice'):holds.append('H_CONFIDENCE')
        for key in ['subject_scope','period','unit_scale','sign','time_type','movement']:
            if values[key] in ['unclear','several','other_stated','other_subject','shared']:
                holds.append('H_CALENDAR' if key=='period' else 'H_FIELD')
        copied={key:copies.get(t['tag']+'_'+key,[]) for key in ['measure','context','qualifiers']+list(optional)}
        if not copied['measure']:holds.append('H_MEASURE')
        if not copied['context']:holds.append('H_EVIDENCE')
        if values['amount_meaning'] in ['unclear','several','guidance_revision','reference_only']:
            holds.append('H_FIELD')
        if values['comparison_baseline']=='unclear':holds.append('H_FIELD')
        for key in optional:
            if answers[key]['noul']>=cfg['optional_cutoff'] and not copied[key]:holds.append('H_MODIFIERS' if key=='conditions' else 'H_FIELD')
        if any('error' in x for spans in copied.values() for x in spans):holds.append('H_EVIDENCE')
        unit=values['unit_scale']
        if unit in ['percent_yoy','percent_sequential'] and values['basis_evidence']=='not_stated':unit='unknown'
        if unit=='percent_sequential' and values['period'].startswith('FY'):unit='percent_yoy'
        numeric={};period=None
        try:
            for side in ['lower','upper']:
                n=by_tag.get(t[side])
                numeric[side]=normalize(n['text'],unit,values['sign'])[0] if n else None
            if all(numeric.get(k) is not None for k in ['lower','upper']) and Decimal(numeric['lower'])>Decimal(numeric['upper']):raise ValueError('Reversed normalized bounds.')
        except (ValueError,ArithmeticError):holds.append('H_NUMBER')
        try:
            code=values['period']
            menu=cfg['period_menu'][code]
            if ' through ' in menu:
                lo,hi=menu.split(' through ')
                frame={'fiscal_year':int(code.split('FY')[-1])}
                if code.startswith('Q'):frame['fiscal_quarter']=int(code[1])
                elif code.startswith('H'):frame['half']=int(code[1])
                if values['time_type']=='instant':lo=hi
                period=ensure_driver_period({**frame,'period_start_date':lo,'period_end_date':hi,'time_type':values['time_type']},fact_type='guidance',fye_month=None)
            elif code in ['short_term','medium_term','long_term','undefined_horizon']:
                period=ensure_driver_period({'sentinel_class':'undefined' if code=='undefined_horizon' else code,'time_type':values['time_type']},fact_type='guidance',fye_month=None)
            else:holds.append('H_CALENDAR')
        except (ValueError,KeyError,TypeError):holds.append('H_CALENDAR')
        evidence=[x for spans in copied.values() for x in spans if 'start' in x]
        evidence += [by_tag[k] for k in [t['lower'],t['upper']] if k in by_tag]
        quote=None
        if evidence:
            start=min(x['start'] for x in evidence);end=max(x['end'] for x in evidence)
            quote={'start':start,'end':end,'text':data['text'][start:end]}
        proposals.append({**t,'answers':answers,'fields':values,'unit_after_rule':unit,
                          'numeric':numeric,'period':period,'copied':copied,'quote':quote,
                          'holds':sorted(set(holds)),
                          'status':'rejected' if 'REJECTED_NOT_GUIDANCE' in holds else 'held' if holds else 'needs_source_review',
                          'accepted':False})
    save(folder/'proposals.json',proposals)
    log(f'Frozen six-call assembly {data["source_id"]}.',
        f'{len(proposals)} numeric proposals; {dict(Counter(p["status"] for p in proposals))}; all sentence/number routing outcomes retained. No correctness claim before source review.',
        'Continue the same procedure on remaining calls, then report complete/held/missed and stop.')


def freeze():
    OUT.mkdir()
    cfg=configuration();save(OUT/'configuration.json',cfg)
    sources=json.loads((ROOT/'sources.json').read_text())
    inputs=[]
    for source in sources:
        data=prepare(source)
        # Whole text and target maps are source-only; no legacy rows or answer key.
        save(OUT/(source['id']+'_input.json'),data)
        inputs.append({'source_id':source['id'],'sha256':digest(OUT/(source['id']+'_input.json')),
                       'sentences':len(data['sentences']),'numbers':len(data['numbers'])})
    files=[Path(__file__),ROOT/'metadata_candidates.py',ROOT/'proposal_numbers.py',
           Path('/home/faisal/EventMarketDB/config/local_llm.py'),
           Path('/home/faisal/EventMarketDB/driver_reference/core/driver_period_resolver.py')]
    manifest={'frozen_at':stamp(),'inputs':inputs,'configuration_sha256':digest(OUT/'configuration.json'),
              'code_sha256':{str(p):digest(p) for p in files},
              'reference_sha256':{p.name:digest(p) for p in sorted((ROOT/'reference_key').glob('*.json'))},
              'contract':'One new run per source; no prompt or code edits after freeze, no repair calls, reference excluded from inference, no production writes. Separate post-run source review determines record counts.'}
    save(OUT/'manifest.json',manifest)
    print(json.dumps(manifest,indent=2))


def run_all():
    manifest=json.loads((OUT/'manifest.json').read_text())
    cfg=json.loads((OUT/'configuration.json').read_text())
    assert L.DECIDER_MODEL==cfg['model']
    assert digest(OUT/'configuration.json')==manifest['configuration_sha256']
    for path,h in manifest['code_sha256'].items():assert digest(path)==h
    for entry in manifest['inputs']:
        path=OUT/(entry['source_id']+'_input.json');assert digest(path)==entry['sha256']
        if (OUT/entry['source_id']).exists():
            raise RuntimeError('Already started source; inspect exact stage, never rerun automatically.')
        try:one_call(json.loads(path.read_text()),cfg)
        except Exception as e:
            folder=OUT/entry['source_id'];folder.mkdir(exist_ok=True)
            save(folder/'technical_hold.json',{'hold':'H_TECHNICAL','error':repr(e),'at':stamp()})
            print(json.dumps({'source':entry['source_id'],'hold':'H_TECHNICAL','error':repr(e)}),flush=True)
    save(OUT/'run_finished.json',{'finished_at':stamp(),'sources':len(manifest['inputs']),'next':'Source review, owner memo and stop. No further model calls.'})


if __name__=='__main__':
    {'freeze':freeze,'run':run_all}[sys.argv[1]]()
