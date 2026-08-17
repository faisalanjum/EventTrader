import json, time, urllib.request, sys

HOST = "http://127.0.0.1:11500"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.8:27b-mlx"
NUM_CTX = int(sys.argv[2]) if len(sys.argv) > 2 else 16384

# distinct sentences so content is unique per size AND per run (nonce first,
# so no prefix-cache hit is possible)
NONCE = str(int(time.time()))
SENT = ("The quarterly report line item number %d shows a value that the "
        "analyst recorded during the review period. ")

def build(target_words):
    body = "".join(SENT % i for i in range(target_words))
    return f"[run {NONCE}] Ignore the reference text.\n{body}\nReply with only the digit 7."

def call(prompt, timeout=900):
    payload = {"model": MODEL,
               "messages": [{"role": "user", "content": prompt}],
               "stream": True, "think": False,
               "options": {"temperature": 0.0, "num_ctx": NUM_CTX, "num_predict": 4}}
    req = urllib.request.Request(HOST + "/api/chat",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time(); first = None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for line in r:
            if not line.strip():
                continue
            d = json.loads(line)
            if ((d.get("message") or {}).get("content") or "") and first is None:
                first = time.time() - t0
            if d.get("done"):
                pe = d.get("prompt_eval_count", 0)
                ped = (d.get("prompt_eval_duration") or 0) / 1e9
                return pe, ped, first, time.time() - t0
    return 0, 0, first, time.time() - t0

print(f"model={MODEL}  num_ctx={NUM_CTX}")
print(f"{'reps':>6} {'prompt_tok':>10} {'prefill_s':>10} {'tok/s':>9} {'first_tok_s':>12} {'total_s':>9}")
for reps in (30, 120, 260, 400, 560, 760):
    try:
        pe, ped, first, tot = call(build(reps))
        rate = pe / ped if ped else 0
        print(f"{reps:>6} {pe:>10} {ped:>10.1f} {rate:>9.0f} {first if first else -1:>12.1f} {tot:>9.1f}", flush=True)
    except Exception as e:
        print(f"{reps:>6}  FAILED: {type(e).__name__}: {str(e)[:70]}", flush=True)
        break
