import json, time, urllib.request, os, re
HOST="http://127.0.0.1:11500"; MODEL="qwen3.8:27b-mlx"
rows=[json.loads(l) for l in open('/tmp/qwen38_cases.jsonl')]
fam=sorted([c for c in rows if c["id"].startswith("SCR-11-q")], key=lambda c:c["id"])[:4]

VARY = re.compile(r"^(Known Driver evidence: .*\nRequested cell: .*)$", re.M)
def reorder(p):
    m = VARY.search(p)
    if not m:
        return None
    moved = m.group(1)
    stripped = p[:m.start()] + p[m.end():]
    return stripped + "\n\nTARGET FOR THIS CALL:\n" + moved

# prove the prefix now matches
ra, rb = reorder(fam[0]["prompt"]), reorder(fam[1]["prompt"])
print("reordered common prefix: %d of %d chars (%.1f%%)" %
      (len(os.path.commonprefix([ra,rb])), len(ra),
       100*len(os.path.commonprefix([ra,rb]))/len(ra)), flush=True)

def call(p, nonce):
    pl={"model":MODEL,"messages":[{"role":"user","content":f"[{nonce}]\n"+p}],
        "stream":True,"think":False,"options":{"temperature":0.0,"num_ctx":32768,"num_predict":8}}
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
print("=== REORDERED: target lines moved to END (shared table is now the prefix) ===",flush=True)
for c in fam:
    pe,ped,tot=call(reorder(c["prompt"]), N)
    print(f"  {c['id']}: tok={pe} prefill={ped:7.1f}s total={tot:7.1f}s",flush=True)
