import json, time, urllib.request, re
HOST="http://127.0.0.1:11434"; MODEL="qwen3.8:27b-mlx"
rows=[json.loads(l) for l in open('/tmp/qwen38_cases.jsonl')]
fam=sorted([c for c in rows if c["id"].startswith("SCR-11-q")], key=lambda c:c["id"])[:2]
VARY=re.compile(r"^(Known Driver evidence: .*\nRequested cell: .*)$", re.M)
def reorder(p):
    m=VARY.search(p); return p[:m.start()]+p[m.end():]+"\n\nTARGET:\n"+m.group(1)
SYS=("You are a JSON API. You emit exactly one JSON object and nothing else. "
     "Never write analysis, reasoning, explanation, or markdown. "
     "Your entire response must parse as JSON.")
def call(p, nonce, system=None, fmt=None, npred=8):
    msgs=([{"role":"system","content":system}] if system else [])+[{"role":"user","content":f"[{nonce}]\n"+p}]
    pl={"model":MODEL,"messages":msgs,"stream":True,"think":False,
        "options":{"temperature":0.0,"num_ctx":32768,"num_predict":npred}}
    if fmt is not None: pl["format"]=fmt
    r=urllib.request.Request(HOST+"/api/chat",data=json.dumps(pl).encode(),
                             headers={"Content-Type":"application/json"})
    t0=time.time()
    with urllib.request.urlopen(r,timeout=1800) as resp:
        for line in resp:
            if not line.strip(): continue
            d=json.loads(line)
            if d.get("done"):
                return (d.get("prompt_eval_duration") or 0)/1e9
VARIANTS=[
 ("baseline (no system, no format, npred=8)", dict()),
 ("+ system message",                          dict(system=SYS)),
 ("+ format schema",                           dict(fmt=fam[0]["schema"])),
 ("+ system + format + npred=512",             dict(system=SYS, fmt=fam[0]["schema"], npred=512)),
]
for label,kw in VARIANTS:
    N=str(int(time.time()*1000))
    a=call(reorder(fam[0]["prompt"]), N, **kw)
    b=call(reorder(fam[1]["prompt"]), N, **kw)
    verdict="CACHE WORKS" if b < a/5 else "CACHE BROKEN"
    print(f"{label:44s} cold={a:7.1f}s  second={b:7.1f}s  -> {verdict}", flush=True)
