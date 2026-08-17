import json, time, urllib.request
HOST = "http://127.0.0.1:11500"; MODEL = "qwen3.8:27b-mlx"
NONCE = str(int(time.time()))
TABLE = "".join("Row %d | segment revenue | value %d | percent change %d\n" % (i, 1000+i, i % 40)
                for i in range(700))          # ~7k tokens, SHARED across questions
QS = ["Which row has value 1042? Reply with the row number only.",
      "Which row has value 1099? Reply with the row number only.",
      "Which row has value 1155? Reply with the row number only."]

def call(prompt):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "stream": True, "think": False,
               "options": {"temperature": 0.0, "num_ctx": 16384, "num_predict": 4}}
    req = urllib.request.Request(HOST + "/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        for line in r:
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("done"):
                return d.get("prompt_eval_count", 0), (d.get("prompt_eval_duration") or 0)/1e9, time.time()-t0

print("=== LAYOUT A (yours): question FIRST, shared table AFTER -> prefix differs every call")
for i, q in enumerate(QS):
    pe, ped, tot = call(f"[{NONCE}a] {q}\n\nTABLE:\n{TABLE}")
    print(f"  call {i+1}: prompt_tok={pe:>6} prefill={ped:>6.1f}s total={tot:>6.1f}s")

print("=== LAYOUT B (fixed): shared table FIRST, question AFTER -> prefix reusable")
for i, q in enumerate(QS):
    pe, ped, tot = call(f"[{NONCE}b] TABLE:\n{TABLE}\n\n{q}")
    print(f"  call {i+1}: prompt_tok={pe:>6} prefill={ped:>6.1f}s total={tot:>6.1f}s")
