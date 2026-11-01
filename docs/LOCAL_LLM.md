# Local LLM inference — structural contract

Model runs on the Mac (M4 Pro, 48 GB); called over the LAN from this Minisforum.
This doc is about the **plumbing** — not any task. Preflight proves it:

```bash
python3 config/preflight.py    # 13 checks; exit 0 = all green
```

## Use it (like a frontier API)

```python
from config import local_llm as L

L.generate("prompt")                 # text; reasoning OFF; raises on silent truncation
L.structured("prompt", schema_dict)  # -> parsed dict, JSON-schema enforced
L.reason("hard question")            # reasoning ON (slow)
L.health()                           # host, model, version, input budget, resident
```

## Guarantees the wrapper enforces

| Risk | Behaviour |
|---|---|
| Malformed JSON | `structured()` passes a JSON schema (GGUF **grammar-enforces** it) + fence-strips + retries |
| **Silent input truncation** | GGUF gives the prompt only **~½ of num_ctx** and drops the FRONT. The client **detects this and RAISES `TruncatedInputError`** — never silent. `allow_truncation=True` to override. |
| Output cut | `done_reason` surfaced in stats; raises `TruncatedOutputError` if it hits the limit with no `max_tokens` set |
| Changing IP | mDNS name `CA-K429CXLGF9.local`; auto-fails over; no hard-coded IP |
| Host down | fails over across hosts, then raises clearly |
| Non-determinism | temperature=0 (verified byte-identical) |

## The two knobs that matter

- **Input budget = num_ctx / 2** (GGUF). Default `num_ctx=32768` → **~16k-token input budget**.
  Bigger inputs: set `num_ctx=` to ≥ 2× your input. **Changing num_ctx forces an ~8 s reload**, so
  keep it fixed across a batch. Env: `LOCAL_LLM_NUM_CTX`.
- **Model** (`LOCAL_LLM_MODEL`), one at a time — VRAM holds one:
  | | JSON/schema | truncation | speed |
  |---|---|---|---|
  | `qwen3.6:35b-a3b` (GGUF, **default**) | ✅ enforced | ½·num_ctx (guarded) | ~51 t/s |
  | `qwen3.6:35b-mlx` | ❌ not enforced | never truncates | ~69 t/s |
  Default is GGUF because guaranteed JSON was the priority. Switch to MLX for pure-speed free-text.

## Speed reality

Aggregate throughput is **~50 t/s regardless of concurrency** — the single GPU is memory-bandwidth
saturated by one stream. `NUM_PARALLEL=4` keeps the GPU fed between requests (no idle gaps); it does
**not** multiply throughput. Bulk time ≈ total_output_tokens / 50.

## Ops (on the Mac)

launchd `~/Library/LaunchAgents/com.faanjum.ollama.plist` — RunAtLoad + KeepAlive, network bind,
`KEEP_ALIVE=-1` (model resident forever), `NUM_PARALLEL=4`. Verified: `kill -9` auto-restarts with
binding intact. Mac set to never idle-sleep on AC. Do **not** `brew services start ollama` (port clash).
