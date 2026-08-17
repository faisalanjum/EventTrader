import json, time, urllib.request, sys
CTX = int(sys.argv[1])
rows = [json.loads(l) for l in open('/tmp/cases_dense.jsonl')]
big = max(rows, key=lambda r: len(r["prompt"]))
SYS = ("You are a JSON API. You emit exactly one JSON object and nothing else. "
       "Never write analysis, reasoning, explanation, or markdown. "
       "Your entire response must parse as JSON.")
N = str(int(time.time()*1000))
def call(tag):
    pl = {"model":"qwen3.8:27b-mlx",
          "messages":[{"role":"system","content":SYS},
                      {"role":"user","content":f"[{tag}]\n"+big["prompt"]}],
          "stream":True,"think":False,"format":big["schema"],
          "options":{"temperature":0.0,"num_ctx":CTX,"num_predict":16}}
    r = urllib.request.Request("http://127.0.0.1:11434/api/chat",
        data=json.dumps(pl).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(r, timeout=1800) as resp:
        for line in resp:
            if not line.strip(): continue
            d = json.loads(line)
            if d.get("done"):
                return d.get("prompt_eval_count",0), (d.get("prompt_eval_duration") or 0)/1e9
pe, ped = call(N + "cold")          # unique tag => genuinely cold
print(f"num_ctx={CTX:>6}  prompt_tok={pe}  COLD prefill={ped:6.1f}s  => {pe/ped if ped else 0:5.0f} tok/s")
