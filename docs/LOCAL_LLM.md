# Local LLM inference — structural contract

Model runs on the owner's Mac (M4 Pro, 48 GB); called from this Minisforum through
`localhost:11435` (reverse SSH tunnel), with the Mac's LAN name as fallback.

> **2026-11-12:** the default is now `qwen3.8:27b-fast` (about 2–6× faster, JSON format
> enforced, same calls). Older model: `LOCAL_LLM_MODEL=qwen3.8:27b-mlx`; one model loads at a
> time. New runtime, so re-check earlier Qwen results before relying on them. Current
> runbook: `.claude/plans/Drivers/FinalDesign/LeftOverSteps/QwenInference.md`. The speed and ops notes below date from the older qwen3.6 setup.
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
| Malformed JSON | `structured()` passes a JSON schema (the fast and GGUF models **grammar-enforce** it; MLX does not) + fence-strips + retries |
| **Silent input truncation** | GGUF gives the prompt only **~½ of num_ctx** and drops the FRONT. The client **detects this and RAISES `TruncatedInputError`** — never silent. `allow_truncation=True` to override. |
| Output cut | `done_reason` surfaced in stats; raises `TruncatedOutputError` if it hits the limit with no `max_tokens` set |
| Changing IP | tries `localhost:11435` (tunnel) first, then mDNS name `CA-K429CXLGF9.local`, then the last known IP |
| Host down | fails over across hosts, then raises clearly |
| Non-determinism | temperature=0 (verified byte-identical) |

## The two knobs that matter

- **Input budget = num_ctx / 2** (GGUF only; the fast and MLX models read the full input, up to num_ctx − 2048). Default `num_ctx=32768` → **~16k-token input budget**.
  Bigger inputs: set `num_ctx=` to ≥ 2× your input. **Changing num_ctx forces an ~8 s reload**, so
  keep it fixed across a batch. Env: `LOCAL_LLM_NUM_CTX`.
- **Model** (`LOCAL_LLM_MODEL`), one at a time — VRAM holds one:
  | | JSON/schema | long input | speed |
  |---|---|---|---|
  | `qwen3.8:27b-fast` (**default** since 2026-11-12) | ✅ enforced | read in full; oversize refused, never cut | about 2–6× faster than before |
  | `qwen3.8:27b-mlx` | ❌ not enforced | read in full | ~27 t/s decode |
  | `qwen3.8:27b-mtp-q4_K_M` (GGUF) | ✅ enforced | ½·num_ctx (guarded) | about 3× slower decode than MLX |
  The qwen3.6 models this table used to list were removed on 2026-08-15.

## Speed reality

Aggregate throughput is **~50 t/s regardless of concurrency** — the single GPU is memory-bandwidth
saturated by one stream. `NUM_PARALLEL=4` keeps the GPU fed between requests (no idle gaps); it does
**not** multiply throughput. Bulk time ≈ total_output_tokens / 50.

## Ops (on the Mac)

Since 2026-11-12 the Mac also runs an Ollama-compatible adapter on port 11435
(`~/Developer/local-llm`; its `AGENTS.md` has the details). It serves the fast model and the
Ollama models, one loaded at a time.

launchd `~/Library/LaunchAgents/com.faanjum.ollama.plist` — RunAtLoad + KeepAlive, network bind,
`KEEP_ALIVE=-1` (model resident forever), `NUM_PARALLEL=4`. Verified: `kill -9` auto-restarts with
binding intact. Mac set to never idle-sleep on AC. Do **not** `brew services start ollama` (port clash).
