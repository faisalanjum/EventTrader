import json, time
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

MODEL = "mlx-community/Qwen3.8-27B-4bit"
print("loading...", flush=True)
t0 = time.time()
model, tok = load(MODEL)
print(f"loaded in {time.time()-t0:.1f}s", flush=True)

rows = [json.loads(l) for l in open('/tmp/cases_labeled.jsonl')]
big = max(rows, key=lambda r: len(r["prompt"]))
SYS = ("You are a JSON API. You emit exactly one JSON object and nothing else. "
       "Never write analysis, reasoning, explanation, or markdown. "
       "Your entire response must parse as JSON.")
msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": big["prompt"]}]
prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
ntok = len(tok.encode(prompt))
print(f"case {big['id']}  prompt_tokens={ntok}", flush=True)

sampler = make_sampler(temp=0.0)
for i in range(2):
    t0 = time.time()
    out = generate(model, tok, prompt=prompt, max_tokens=16, sampler=sampler, verbose=False)
    el = time.time() - t0
    print(f"  run {i+1}: {el:.1f}s total  => {ntok/el:.0f} tok/s effective prefill | out={out[:40]!r}", flush=True)
