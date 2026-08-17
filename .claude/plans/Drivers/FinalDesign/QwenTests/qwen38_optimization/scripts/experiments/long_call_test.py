import json, time, urllib.request, re, sys
HOST=sys.argv[1]
rows=[json.loads(l) for l in open('/tmp/qwen38_cases.jsonl')]
c=[r for r in rows if r["id"]=="SCR-12-q3"][0]   # previously died at 422.6s
VARY=re.compile(r"^(Known Driver evidence: .*\nRequested cell: .*)$", re.M)
m=VARY.search(c["prompt"]); p=c["prompt"][:m.start()]+c["prompt"][m.end():]+"\n\nTARGET:\n"+m.group(1)
SYS=("You are a JSON API. You emit exactly one JSON object and nothing else. "
     "Never write analysis, reasoning, explanation, or markdown. "
     "Your entire response must parse as JSON.")
pl={"model":"qwen3.8:27b-mlx",
    "messages":[{"role":"system","content":SYS},{"role":"user","content":f"[lt{int(time.time())}]\n"+p}],
    "stream":True,"think":False,"format":c["schema"],
    "options":{"temperature":0.0,"num_ctx":16384,"num_predict":512}}
r=urllib.request.Request(HOST+"/api/chat",data=json.dumps(pl).encode(),
                         headers={"Content-Type":"application/json"})
t0=time.time()
try:
    buf=[]
    with urllib.request.urlopen(r,timeout=3600) as resp:
        for line in resp:
            if not line.strip(): continue
            d=json.loads(line)
            buf.append((d.get("message") or {}).get("content") or "")
            if d.get("done"):
                print(f"SUCCESS in {time.time()-t0:.1f}s  prefill={(d.get('prompt_eval_duration') or 0)/1e9:.1f}s")
                print("  output:", "".join(buf)[:60])
except Exception as e:
    print(f"FAILED after {time.time()-t0:.1f}s: {type(e).__name__}: {e}")
