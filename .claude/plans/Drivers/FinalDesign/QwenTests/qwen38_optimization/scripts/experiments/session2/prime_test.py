#!/usr/bin/env python3
"""Prefix-PRIMING experiment against the production Ollama server (localhost).

Hypothesis (from ollama x/mlxrunner source, pipeline.go + prefix_cache.go):
  * automatic prefill snapshots land every 8192 tokens and at len(prompt)-4
  * branch-point snapshots are only created during the SECOND request that
    diverges there -> every family costs 2 cold prefills before hits start
  * Qwen3.8 has non-rewindable (recurrent) cache layers, so a diverging
    request cannot trim back to the branch point.
  => a PRIMING request whose tokens are EXACTLY the shared prefix leaves an
     automatic snapshot 4 tokens before the branch point, so the very first
     real request already restores there.

Arm A (control): fresh nonce, q1, q2, q3 via /api/chat  -> expect cold, cold, hot
Arm B (primed):  fresh nonce, PRIME via /api/generate raw, then q1, q2 -> expect cold, hot, hot
"""
import json, os, sys, time, uuid, subprocess, urllib.request, re

HOST = os.environ.get("HOST", "http://127.0.0.1:11434")
MODEL = "qwen3.8:27b-mlx"
NUM_CTX = int(os.environ.get("NUM_CTX", "16384"))
FAMILY = os.environ.get("FAMILY", "SCR-11")
LOG = "/tmp/ollama-agent.err"
SYSTEM_MESSAGE = ("You are a JSON API. You emit exactly one JSON object and nothing "
                  "else. Never write analysis, reasoning, explanation, or markdown. "
                  "Your entire response must parse as JSON.")
JSON_SUFFIX = ("Return JSON only - exactly one object matching the schema, "
               "no prose, no code fence.")

rows = [json.loads(l) for l in open(os.path.join(os.path.dirname(__file__), "cases_dense.jsonl"))]
fam = [r for r in rows if r["id"].startswith(FAMILY + "-")]
assert fam, FAMILY
prompts = [r["prompt"] for r in fam]
schema = fam[0]["schema"]
cp = os.path.commonprefix(prompts)
# cut the shared prefix back to a line boundary
cut = cp.rfind("\n") + 1
P = cp[:cut]
print(f"family={FAMILY} n={len(fam)} prompt_chars={len(prompts[0])} shared_prefix_chars={len(P)} "
      f"(cut at line boundary; tail={P[-60:]!r})")

def battery():
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    m = re.search(r"(\d+)%; (\w+)", out)
    return f"{m.group(1)}%/{m.group(2)}" if m else out.strip()[:40]

def log_pos():
    return os.path.getsize(LOG)

def log_since(pos):
    with open(LOG, "rb") as f:
        f.seek(pos)
        txt = f.read().decode("utf-8", "replace")
    hits = re.findall(r'msg="(cache (?:hit|miss))" total=(\d+) matched=(\d+) cached=(\d+) left=(\d+)', txt)
    spec = re.findall(r'speculative decode stats" iterations=(\d+) drafted=(\d+) accepted=(\d+) acceptance=([\d.]+)', txt)
    return hits, spec

def post(path, payload, timeout=1800):
    req = urllib.request.Request(HOST + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d, time.time() - t0

def real_call(user_prompt, label):
    payload = {"model": MODEL, "stream": False, "think": False,
               "messages": [{"role": "system", "content": SYSTEM_MESSAGE},
                            {"role": "user", "content": user_prompt + "\n\n" + JSON_SUFFIX}],
               "format": schema,
               "options": {"temperature": 0, "num_ctx": NUM_CTX, "num_predict": 64}}
    pos = log_pos()
    d, wall = post("/api/chat", payload)
    hits, spec = log_since(pos)
    pe = d.get("prompt_eval_count"); ped = d.get("prompt_eval_duration", 0) / 1e9
    ec = d.get("eval_count"); ed = d.get("eval_duration", 0) / 1e9
    content = (d.get("message") or {}).get("content", "")
    print(f"  {label:6s} wall={wall:7.1f}s prompt_eval={pe} in {ped:6.1f}s "
          f"({(pe/ped) if ped else 0:5.0f} tok/s)  eval={ec} in {ed:4.1f}s  cache={hits[-1] if hits else '?'}  "
          f"out={content.strip()[:40]!r}  batt={battery()}", flush=True)
    return wall, hits

def prime_call(user_prefix, label="PRIME"):
    raw = ("<|im_start|>system\n" + SYSTEM_MESSAGE.strip() + "<|im_end|>\n"
           "<|im_start|>user\n" + user_prefix)
    payload = {"model": MODEL, "stream": False, "raw": True, "prompt": raw,
               "options": {"temperature": 0, "num_ctx": NUM_CTX, "num_predict": 1}}
    pos = log_pos()
    d, wall = post("/api/generate", payload)
    hits, spec = log_since(pos)
    pe = d.get("prompt_eval_count"); ped = d.get("prompt_eval_duration", 0) / 1e9
    print(f"  {label:6s} wall={wall:7.1f}s prompt_eval={pe} in {ped:6.1f}s "
          f"({(pe/ped) if ped else 0:5.0f} tok/s)  cache={hits[-1] if hits else '?'}  batt={battery()}", flush=True)
    return wall, hits

arms = sys.argv[1:] or ["A", "B"]
for arm in arms:
    nonce = f"Session nonce: {uuid.uuid4()}\n\n"
    print(f"\n=== ARM {arm}  nonce={nonce.strip()}  batt={battery()}", flush=True)
    t0 = time.time()
    if arm == "A":
        for i in range(3):
            real_call(nonce + prompts[i], f"q{i+1}")
    elif arm == "B":
        prime_call(nonce + P)
        for i in range(3):
            real_call(nonce + prompts[i], f"q{i+1}")
    print(f"=== ARM {arm} total wall {time.time()-t0:.1f}s")
