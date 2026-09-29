import json,collections
E=json.load(open('results_all.json')); fx={f['id']:f for f in json.load(open('fixtures_v3.json'))}
old={x['id']:x for x in json.load(open('results_ctx.json'))}
# baseline: v2 (old prompts + old input) mapped onto the same keys
base=[]
for f in fx.values():
    if f['set']!='DEV': continue
    o=old[int(f['id'].split('-')[1])]; base.append(dict(id=f['id'],set='DEV',key=f['key'],one=o['A'],steps=o['B'],one_conf=o['A_conf']))
E['old_prompts_old_input']=base
def acc(rs,p,t=None):
    rs=[r for r in rs if r['key']!='unclear' and (t is None or r['key']==t)]
    return sum(r[p]==r['key'] for r in rs),len(rs)
print(f"{'experiment':28s} {'pattern':12s} | DEV all  metric  action guidance | H1 guidance | H2 metric action")
for name in ('old_prompts_old_input','old_prompts_new_input','new_prompts_old_input','new_prompts_new_input'):
    rs=E[name]
    for p,pl in (('one','one question'),('steps','step-by-step')):
        d=[r for r in rs if r['set']=='DEV']; row=f"{name:28s} {pl:12s} | "
        a,n=acc(d,p); row+=f"{a:3d}/{n:<3d} {100*a/n:4.0f}% "
        for t in ('metric','action_event','guidance'):
            a,n=acc(d,p,t); row+=f" {a:2d}/{n:<2d}  "
        h1=[r for r in rs if r['set']=='H1']; h2=[r for r in rs if r['set']=='H2']
        if h1:
            a,n=acc(h1,p); row+=f"| {a}/{n}      "
            a1,n1=acc(h2,p,'metric'); a2,n2=acc(h2,p,'action_event'); row+=f"| {a1}/{n1}  {a2}/{n2}"
        print(row)
