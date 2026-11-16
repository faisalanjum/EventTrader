"""Source-boundary controls, not model-accuracy tests."""
import json
from pathlib import Path
import pytest
import frozen_six_run as R


def test_all_six_sources_preserve_text_and_every_candidate():
    sources=json.loads((R.ROOT/'sources.json').read_text())
    assert len(sources)==6
    for source in sources:
        data=R.prepare(source)
        text,mapping=R.render(data)
        assert ''.join(c for c,p in zip(text,mapping) if p is not None)==source['text']
        assert len([p for p in mapping if p is not None])==len(source['text'])
        for n in data['numbers']:
            assert source['text'][n['start']:n['end']]==n['text']


def test_mapping_copies_original_but_refuses_instruction_text():
    raw='Expect 18.5%.'
    data={'text':raw,'sentences':[],'numbers':[{'tag':'V000','start':7}]}
    body,m=R.render(data)
    prefix='INSTRUCTION: '
    state=prefix+body;mapping=[None]*len(prefix)+m
    a=state.index('18.5%')
    copied=R.mapped({'start':a,'end':a+5,'text':'18.5%','score':.9},state,mapping,raw,len(prefix))
    assert (copied['start'],copied['end'],copied['text'])==(7,12,'18.5%')
    wrong=R.mapped({'start':0,'end':len(state),'text':state,'score':.9},state,mapping,raw,len(prefix))
    assert wrong['error']=='H_EVIDENCE'


def test_changed_returned_text_is_rejected():
    with pytest.raises(AssertionError):
        R.mapped({'start':0,'end':2,'text':'19','score':.9},'18',[0,1],'18',0)


def test_configuration_has_no_hidden_metric_or_value_options():
    c=R.configuration()
    assert c['model']=='pplx-decider-v1.3:8bit'
    assert list(c['fields'])==['form','subject_scope','period','unit_scale','sign','movement','time_type','basis_evidence','amount_meaning','comparison_baseline']
    assert 'GROWTH_BASIS_TASK' in c['basis_definition']
    assert 'SOURCE:' not in c['basis_definition']
    assert all(len(f['criteria'])<=255 for f in c['fields'].values())
    assert '18.5' not in json.dumps(c)
