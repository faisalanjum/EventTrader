import json, time, urllib.request, sys, random
HOST=sys.argv[1]; CTX=int(sys.argv[2]); MODEL="qwen3.8:27b-mlx"
WORDS=["revenue","segment","margin","quarter","filing","freight","cargo","fuel",
       "expense","operating","income","adjusted","volume","yield","capacity"]
def build(n_words, seed):
    r=random.Random(seed)
    # UNIQUE random word order per call => NO shared prefix with any other call
    return (" ".join(r.choice(WORDS)+str(r.randint(100,999)) for _ in range(n_words))
            + "\n\nReply with only the digit 7.")
def call(p):
    pl={"model":MODEL,"messages":[{"role":"user","content":p}],"stream":True,"think":False,
        "options":{"temperature":0.0,"num_ctx":CTX,"num_predict":4}}
    r=urllib.request.Request(HOST+"/api/chat",data=json.dumps(pl).encode(),
                             headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(r,timeout=1800) as resp:
        for line in resp:
            if not line.strip(): continue
            d=json.loads(line)
            if d.get("done"):
                return d.get("prompt_eval_count",0),(d.get("prompt_eval_duration") or 0)/1e9
print(f"host={HOST} num_ctx={CTX}  (unique random content per call - no prefix sharing)",flush=True)
print(f"{'words':>7} {'prompt_tok':>11} {'prefill_s':>10} {'tok/s':>8}",flush=True)
for i,w in enumerate((400, 1200, 2400, 3600)):
    pe,ped=call(build(w, seed=90000+i*7919))
    print(f"{w:>7} {pe:>11} {ped:>10.1f} {pe/ped if ped else 0:>8.0f}",flush=True)
