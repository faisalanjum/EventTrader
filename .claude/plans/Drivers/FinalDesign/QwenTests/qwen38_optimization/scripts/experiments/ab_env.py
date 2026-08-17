import json, time, urllib.request, re, sys
HOST=sys.argv[1]; MODEL="qwen3.8:27b-mlx"; CTX=int(sys.argv[2])
rows=[json.loads(l) for l in open('/tmp/qwen38_cases.jsonl')]
fam=sorted([c for c in rows if c["id"].startswith("SCR-11-q")], key=lambda c:c["id"])[:3]
VARY=re.compile(r"^(Known Driver evidence: .*\nRequested cell: .*)$", re.M)
def reorder(p):
    m=VARY.search(p); return p[:m.start()]+p[m.end():]+"\n\nTARGET:\n"+m.group(1)
def call(p,nonce):
    pl={"model":MODEL,"messages":[{"role":"user","content":f"[{nonce}]\n"+p}],
        "stream":True,"think":False,"options":{"temperature":0.0,"num_ctx":CTX,"num_predict":8}}
    r=urllib.request.Request(HOST+"/api/chat",data=json.dumps(pl).encode(),
                             headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(r,timeout=1800) as resp:
        for line in resp:
            if not line.strip(): continue
            d=json.loads(line)
            if d.get("done"): return (d.get("prompt_eval_duration") or 0)/1e9
N=str(int(time.time()*1000))
print(f"host={HOST} num_ctx={CTX}",flush=True)
for i,c in enumerate(fam):
    print(f"  call {i+1}: prefill={call(reorder(c['prompt']),N):7.1f}s",flush=True)
