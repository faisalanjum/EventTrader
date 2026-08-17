# Qwen local inference — how to use it (for implementing agents)

Status 2026-08-17: UP AND RUNNING. Nothing to install. Read this whole page (5 min).

## 1. What it is
- Model `qwen3.8:27b-mlx` (Qwen3.8-27B, dense, 4-bit nvfp4) on Faisal's MacBook via
  Ollama 0.32.13's MLX engine. Reasoning OFF, temperature 0, deterministic.
- Reached from the Minisforum through the always-on tunnel: `http://localhost:11434`
  (client resolves `CA-K429CXLGF9.local` / `192.168.40.147` automatically).
- One request at a time (server `OLLAMA_NUM_PARALLEL=1`). Model stays resident.
- Client: `EventMarketDB/config/local_llm.py` — the ONLY supported entry point.

## 2. Call it (Python, from the repo root)
```python
from config import local_llm as L

text, stats = L.generate(prompt, system=SYSTEM, think=False, temperature=0.0,
                         num_ctx=16384, max_tokens=512, timeout=1800,
                         retries=0, with_stats=True)          # plain text reply
obj = L.structured(prompt, schema_dict, system=SYSTEM,
                   num_ctx=16384, max_tokens=512, timeout=1800)  # parsed JSON dict
```
- `structured()` returns a dict; it appends a "return JSON only" instruction on the
  MLX path and strips code fences. `format` (JSON schema) is NOT grammar-enforced by
  the MLX engine — always validate the parsed object yourself.
- `stats`: `prompt_eval_count`, `eval_count`, `total_s`, `truncated_input`,
  `truncated_output`, `done_reason`, `host`, `model`.
- Raises `TruncatedInputError` / `TruncatedOutputError` (never ignore) or
  `RuntimeError` on transport failure. Save the raw reply before parsing.
- Env knobs: `LOCAL_LLM_MODEL` (qwen3.8:27b-mlx), `LOCAL_LLM_NUM_CTX` (32768),
  `LOCAL_LLM_TIMEOUT` (1800 s), `LOCAL_LLM_THINK` (0), `LOCAL_LLM_HOST`.
- Health: `cd EventMarketDB && python3 -m config.local_llm` (prints host, model, a test reply).

## 3. Cost model — plan every call with this
```
call time  ≈  new_prompt_tokens / 95  +  output_tokens / 25   (seconds)
```
- Fresh (never-seen) text: **~95–110 tok/s** prefill on this GPU. That is the hardware
  ceiling; nothing makes a brand-new document faster except sending fewer tokens.
- Cached prefix (same bytes as an earlier call, from position 0): ~free (≈1 s/call).
- Decode: 22–29 tok/s (MTP speculative decoding is on).
- Measured examples: 6k-token table 65 s cold; 13.7k-token whole 8-K exhibit 145 s
  cold; 23.5k-token exhibit 261 s cold; any cached call ~1 s.
- Tokenizer: every digit is a token; indentation and separators are tokens. Numeric
  tables ≈ 1.6 chars/token; prose ≈ 3.4 chars/token. Never send raw HTML
  (10–20x the tokens of the rendered text).

## 4. Rules that make it fast (do these; nothing else is needed)
1. **Prompt layout: shared bytes FIRST, per-call bytes LAST.** Instructions + document
   first; the item / anchor / question at the very end. Any changing token early in
   the prompt (ids, timestamps, nonces) destroys cache reuse for everything after it.
2. **Prime once per document when ≥2 calls will share it:**
   ```python
   L.prime(shared_prefix, system=SYSTEM, num_ctx=NUM_CTX)   # shared_prefix = the exact
   # leading text every upcoming call starts with (line boundary), same system text
   L.prime_for(list_of_prompts, system=SYSTEM, num_ctx=NUM_CTX)  # computes it for you
   ```
   Then make the calls. Without priming the first TWO calls on a document are both
   cold (a server cache quirk); with it only the first is. Priming an already-cached
   prefix costs ~0.1 s, so it is safe to always do it.
3. **Group work by document** (all calls on table A, then table B). Cache holds
   ~8 GiB of snapshots (≈ a few tables); do not interleave documents.
4. **`num_ctx` per role, fixed for the whole run:** 16384 for tables/chunks up to
   ~12k tokens; 32768 for whole exhibits (tested to 23.5k tokens); the client's
   input guard raises `TruncatedInputError` if a prompt would not fit.
5. **Sequential calls only** (workers=1). Parallel workers do not add throughput here
   and thrash the cache.
6. `think=False`, `temperature=0.0`, `retries=0` for graded work; the caller owns
   any transport retry (a resumed call on a completed server computation is ~free).
7. Timeouts: use `timeout=1800`. Something on the LAN can reset a connection idle
   >~5 min during a very long cold prefill; the server finishes and caches anyway —
   just retry the same call.

## 5. What is proven (and what is not)
| suite (development sets, opened keys) | Qwen3.8 | old qwen3.6 | wall now |
|---|---|---|---|
| choice_v2 (table cell choice, 93 cases) | **93/93**, precision 1.0 | 75/93 | 5.3 min (compact) / 6.4 min (dense) |
| row_v3 (row selection, 93) | **93/93** | 93/93 | 3.8 min |
| qf01 aligned 5x50 table contract (19 calls) | **19/19** | 17/19 | 3.4 min |
Not yet tested on Qwen: prose/remarks/Q&A/numberless locators (QF-02..06), identity
(QC-01), the shared reader, catalog reader. Under the 2026-08-14 ruling those roles
run Sonnet 5; Qwen enters a role only through the Step 14 one-role-at-a-time
qualification (same prompt/schema/parser; zero wrong accepted; not worse than baseline).
Note for Step 14's "byte-identical task content": on the MLX path `structured()`
appends the JSON-only instruction and the harnesses use a JSON-API system message.

## 6. Table encoding that scored 100% (reuse it for table roles)
Header once: `Source-derived choices. Every choice line is choice|occurrence|value|headers:`
then per row `ROW n section="…" label="…"` and choice lines `22|1|2,289|4Q24` (no indent),
per-call target block last. Code applies the occurrence; the model never counts.
Reference implementation: `.claude/plans/Drivers/FinalDesign/QwenTests/qwen38_optimization/harness/choice_v2_compact/choice_v2.py`.

## 7. Don'ts
- Don't send raw HTML, don't put the question before the document, don't run
  parallel workers, don't turn thinking on, don't rely on `format` for validity,
  don't change `num_ctx` mid-run, don't restart the Ollama server (drops the cache;
  if you must: `launchctl bootout/bootstrap`, not `kickstart -k`).

## 8. Where things are
- Client: `config/local_llm.py` (committed). Server plist copy, runbook, full
  investigation log, harness copies, all results and scripts:
  `.claude/plans/Drivers/FinalDesign/QwenTests/qwen38_optimization/` (README → notes/RUNBOOK.md).
- Server env (live): NUM_PARALLEL=1, LOAD_TIMEOUT=30m, KEEP_ALIVE=-1, MAX_LOADED_MODELS=1.
