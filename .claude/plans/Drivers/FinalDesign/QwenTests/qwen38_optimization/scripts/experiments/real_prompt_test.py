import json, time, urllib.request, re
HOST="http://127.0.0.1:11500"; MODEL="qwen3.8:27b-mlx"
CASES="/tmp/qwen38_cases.jsonl"
rows=[json.loads(l) for l in open(CASES)]
fam={}
for c in rows:
    key=c["id"].rsplit("-q",1)[0]
    fam.setdefault(key,[]).append(c)
target=[k for k,v in fam.items() if len(v)>=7][0]
cases=sorted(fam[target], key=lambda c:c["id"])[:4]
print(f"family {target}: {[c['id'] for c in cases]}", flush=True)

MARK='"rendered_table"'
def split(p):
    i=p.find(MARK)
    return p[:i], p[i:]

def call(p, nonce):
    pl={"model":MODEL,"messages":[{"role":"user","content":f"[{nonce}]\n"+p}],
        "stream":True,"think":False,
        "options":{"temperature":0.0,"num_ctx":32768,"num_predict":8}}
    r=urllib.request.Request(HOST+"/api/chat",data=json.dumps(pl).encode(),
                             headers={"Content-Type":"application/json"})
    t0=time.time()
    with urllib.request.urlopen(r,timeout=1800) as resp:
        for line in resp:
            if not line.strip(): continue
            d=json.loads(line)
            if d.get("done"):
                return d.get("prompt_eval_count",0),(d.get("prompt_eval_duration") or 0)/1e9,time.time()-t0

N=str(int(time.time()))
print("=== CURRENT layout (question first, table after) ===",flush=True)
for c in cases:
    pe,ped,tot=call(c["prompt"], N+"a")
    print(f"  {c['id']}: tok={pe} prefill={ped:6.1f}s total={tot:6.1f}s",flush=True)
print("=== REORDERED (table first, question after) ===",flush=True)
for c in cases:
    head,tab=split(c["prompt"])
    pe,ped,tot=call(tab+"\n\n"+head, N+"b")
    print(f"  {c['id']}: tok={pe} prefill={ped:6.1f}s total={tot:6.1f}s",flush=True)
