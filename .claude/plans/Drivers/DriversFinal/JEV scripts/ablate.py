import json,sys,collections,copy
sys.path.insert(0,'.')
import prompts_v3 as P
from variants import v2a,v2b
from concurrent.futures import ThreadPoolExecutor
# leave-one-out: remove ONE clause group from V2b, see what changes
S={
 'c2_totals_of_transactions':("metric","what"," A total, count or amount measured for a period is such a variable even when it is made up of transactions."),
 'c3_method_in_use':("metric","what"," A method, policy or arrangement that is already in use and continues is a condition in force, not the moment it was created."),
 'c4a_per_unit_level':("metric","what"," A standing per-unit level is a metric."),
 'c4b_one_time_decision':("action_event","what"," A one-time decision to start, change or suspend a policy is an action_event."),
 'c5_incident_with_effect':("action_event","what"," An incident counts even when the quote also states its effect on a result."),
 'c6_announced_stays_action':("action_event","what"," An announced, committed or scheduled action stays an action_event even when it happens later."),
 'c7_continuing_condition':("action_event","not_for"," A continuing condition or a measured severity is a metric."),
}
READ_RULE=" When two drivers cover one topic, the driver name tells which fact is meant: a driver named for a per-unit amount is a metric; a driver named for the decision or event is an action_event."
def drop(name):
    q=v2b()
    if name in S:
        k,f,t=S[name]; assert t in q['criteria'][k][f],name; q['criteria'][k][f]=q['criteria'][k][f].replace(t,"")
    elif name=='c8_read_driver_rule':
        assert READ_RULE in q['instructions']['read']; q['instructions']['read']=q['instructions']['read'].replace(READ_RULE,"")
    elif name=='c1_guidance_rewrite':      # back to the locked guidance wording (V2a text)
        a=v2a(); q['criteria']['guidance']=a['criteria']['guidance']; q['instructions']['order']=a['instructions']['order']
        q['criteria']['action_event']['what']=q['criteria']['action_event']['what'].replace(S['c6_announced_stays_action'][2],"")
    return q
NAMES=list(S)+['c8_read_driver_rule','c1_guidance_rewrite']
items=[]
for f in ('redo_items.json','fixtures_h5.json'):
    items+=json.load(open(f))
DISPUTED={'H1-013a','H1-035','H2-024','H2-039','H2-043','H5G-56','H5M-016','H5M-026','H5M-037'}
FIX={'H5M-004':'action_event','H5M-027':'action_event'}          # earlier-model label wrong under the advice (scheduled payment = action)
dec=[x for x in items if x['key']!='unclear' and x['id'] not in DISPUTED]
for x in dec:
    if x['id'] in FIX: x['key']=FIX[x['id']]
print("decided items:",len(dec))
def one(a):
    x,n=a; return x['id'],n,P.call(x['state'],{"fact_type":drop(n)})
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,[(x,n) for x in dec for n in NAMES]))
out=collections.defaultdict(dict); err=0
for i,n,r in R:
    if 'error' in r: err+=1; continue
    a=r['answers']['fact_type']; out[i][n]=dict(choice=a['choice'],conf=a['confidence'])
json.dump({'items':{x['id']:x['key'] for x in dec},'R':out},open('ablate_results.json','w'))
print("errors",err)
