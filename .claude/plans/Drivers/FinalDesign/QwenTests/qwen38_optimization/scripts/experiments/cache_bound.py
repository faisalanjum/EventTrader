import json, time, urllib.request, sys
HOST="http://127.0.0.1:11500"; MODEL="qwen3.8:27b-mlx"
N=str(int(time.time()))
TABLE="".join("Row %d | segment revenue | value %d | pct %d\n"%(i,1000+i,i%40) for i in range(480))  # ~7.5k tok
def call(p):
    pl={"model":MODEL,"messages":[{"role":"user","content":p}],"stream":True,"think":False,
        "options":{"temperature":0.0,"num_ctx":16384,"num_predict":4}}
    r=urllib.request.Request(HOST+"/api/chat",data=json.dumps(pl).encode(),
                             headers={"Content-Type":"application/json"})
    t0=time.time()
    with urllib.request.urlopen(r,timeout=900) as resp:
        for line in resp:
            if not line.strip(): continue
            d=json.loads(line)
            if d.get("done"):
                return d.get("prompt_eval_count",0),(d.get("prompt_eval_duration") or 0)/1e9,time.time()-t0
P=f"[{N}] TABLE:\n{TABLE}\n\nWhich row has value 1042? Reply with the row number only."
print("=== CONTROL: IDENTICAL prompt x3 (upper bound on cache reuse) ===",flush=True)
for i in range(3):
    pe,ped,tot=call(P); print(f"  call {i+1}: tok={pe} prefill={ped:.1f}s total={tot:.1f}s",flush=True)
print("=== VARY ONLY THE LAST LINE (table-first layout), 7.5k tok ===",flush=True)
for i,q in enumerate(["Which row has value 1099? Reply with the row number only.",
                      "Which row has value 1155? Reply with the row number only."]):
    pe,ped,tot=call(f"[{N}] TABLE:\n{TABLE}\n\n{q}")
    print(f"  vary {i+1}: tok={pe} prefill={ped:.1f}s total={tot:.1f}s",flush=True)
