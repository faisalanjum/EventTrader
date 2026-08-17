#!/usr/bin/env python3
"""num_ctx cost: identical fresh (nonced) 6.3k-token prompt at num_ctx 16384 vs 32768,
interleaved, on the production Ollama server. Reports cold prefill tok/s, model
reload time and resident size for each num_ctx. (Each num_ctx change reloads the
model and drops the prefix-cache trie - that is part of what this measures.)"""
import json, os, re, subprocess, time, urllib.request, uuid

HOST = "http://127.0.0.1:11434"; MODEL = "qwen3.8:27b-mlx"
SYSTEM_MESSAGE = ("You are a JSON API. You emit exactly one JSON object and nothing "
                  "else. Never write analysis, reasoning, explanation, or markdown. "
                  "Your entire response must parse as JSON.")
rows = [json.loads(l) for l in open(os.path.join(os.path.dirname(__file__), "cases_dense.jsonl"))]
case = [r for r in rows if r["id"] == "SCR-11-q1"][0]

def battery():
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    m = re.search(r"(\d+)%; (\w+)", out); return f"{m.group(1)}%/{m.group(2)}" if m else "?"

def post(path, payload, timeout=1800):
    req = urllib.request.Request(HOST + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()), time.time() - t0

def ps():
    with urllib.request.urlopen(HOST + "/api/ps", timeout=10) as r:
        d = json.load(r)
    return [(m["name"], m.get("size_vram"), m.get("context_length")) for m in d.get("models", [])]

order = [16384, 32768, 16384, 32768]
res = {}
for ctx in order:
    nonce = f"Session nonce: {uuid.uuid4()}\n\n"
    payload = {"model": MODEL, "stream": False, "think": False,
               "messages": [{"role": "system", "content": SYSTEM_MESSAGE},
                            {"role": "user", "content": nonce + case["prompt"]}],
               "format": case["schema"],
               "options": {"temperature": 0, "num_ctx": ctx, "num_predict": 32}}
    d, wall = post("/api/chat", payload)
    pe, ped = d.get("prompt_eval_count"), d.get("prompt_eval_duration", 0) / 1e9
    ld = d.get("load_duration", 0) / 1e9
    line = (f"num_ctx={ctx} wall={wall:6.1f}s load={ld:5.1f}s prompt_eval={pe} in {ped:6.1f}s "
            f"({pe/ped if ped else 0:5.1f} tok/s) out={d['message']['content'].strip()[:30]!r} "
            f"ps={ps()} batt={battery()}")
    print(line, flush=True)
    res.setdefault(ctx, []).append(pe / ped if ped else 0)
print("SUMMARY cold prefill tok/s:", {k: [round(x, 1) for x in v] for k, v in res.items()})
