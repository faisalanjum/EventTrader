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

## 9. Hard size limit (measured 2026-08-17) — READ BEFORE DESIGNING A TEST
- Runner memory grows ~0.24 MB per prompt token: 13.7k tokens → 33.9 GiB peak,
  23.5k → 36.2 GiB (48 GB Mac, 37.4 GiB Metal budget). A 70k-token prompt ≈ 47 GiB,
  a 200k window ≈ 78 GiB: **impossible on this machine.**
- Practical ceiling: **~25k tokens per call (≈100 KB rendered text)**, and such calls
  cost 4–5 min each. Treat oversize input as a visible failure BEFORE the call
  (`TruncatedInputError` is raised by the client); never truncate silently.
- Whole-event / long-reasoning single prompts (60–80k tokens) are therefore out of
  scope for Qwen here; they stay on Sonnet unless the role is redesigned as
  self-contained chunks — an owner design decision, not a transport tweak.

## 10. Step-14 comparison rules (how to compare Qwen against Sonnet fairly)
- Use raw `L.generate(prompt, system=<the frozen system text>, think=False,
  temperature=0.0, num_ctx=…, max_tokens=…, timeout=1800, retries=0)`; save the raw
  reply first; feed it to the ONE shared parser/receipt path. Do NOT use
  `structured()` for comparisons (it appends a JSON-only instruction and strips
  fences — prompt-byte and output changes).
- Known risk on the MLX build: no grammar enforcement, so occasional prose or
  fenced JSON → parser rejects → counts against Qwen (correctly). If format
  failures dominate, the GGUF build `qwen3.8:27b-mtp-q4_K_M` grammar-enforces the
  `format` schema (same prefill speed, same accuracy on compared cases, ~3x slower
  decode) — a legitimate transport choice for short-output roles.
- Priming is a transport step: it changes no prompt bytes or outputs; record the
  prime calls in the run record (the reference harness writes `prime_calls`).
- Chunking a source is valid only when each chunk's answer depends solely on that
  chunk; exams that must see the whole event (find all facts, de-duplicate across
  sections) cannot be chunked without a contract change.

## 11. Machine conditions during runs
- With the model resident (29.5 GiB) the Mac swaps heavily if many apps are open
  (swap was 95% full on 2026-08-17). Keep other apps light during batch runs.
- Power (all measured on this Mac): the connected adapter is a 30 W unit (the
  machine, Mac16,8 = 14-inch M4 Pro, ships with 70 W). Under GPU load the battery
  drains ~2%/min even while plugged in, and identical calls ran up to 3.5x slower
  once the battery was low (5–16%). Display sleep is disabled (`pmset displaysleep 0`)
  and the display stack consumed most of the adapter: charging went from 142 mA to
  1,781 mA after `pmset displaysleepnow`. For long batch runs: sleep the display
  and/or use a ≥70 W adapter.

## 12. Qwen test coverage across Steps 1–14 — what can be tested in ORIGINAL form (inventory 2026-08-17)
| Step / role | Frozen material in the repo | Deterministic scorer? | Sonnet baseline | Qwen status |
|---|---|---|---|---|
| 1/4/7 identity judge (EXP-0 contract; K-pairs v1.3: 160 pairs, 110 DIFFERENT / 50 SAME, 89 hard) | byte-identical grader prompt + JSON verdict schema; Fable-locked key `keys/K-pairs/K-pairs.v1.3.jsonl` | YES — `harness/scorers/score_exp0.py` gate: wrong_same=0, false_refusal≤10%, invalid≤2% | Sonnet 0 wrong-SAME, 0–1 false refusal, 0 invalid; Opus same | RUNNABLE (~25–40 min GPU) — see results below when done |
| 9 table locator (choice_v2 / row_v3 / qf01) | frozen harnesses + keys | yes | old qwen3.6 | DONE: 93/93, 93/93, 19/19 |
| 1/3/5 reader — EXP-2 proxy (40 real 40k-char chunks vs K-reader v3, 1,175 gold facts) | prompt, chunks, key, Sonnet arm outputs (recall 40.4% / precision 85%) | PARTLY — official metric used Sonnet graders; only strict deterministic matching is possible (relative comparison, Sonnet outputs re-scored the same way) | relative only | runnable overnight (~1.7 h GPU); not the official metric |
| 3/5 reader — EXP-5 per-event exam (36 events) | prompt builder + K-reader key | NO (needs Sonnet graders); some events likely >25k tokens; NOT yet run on Sonnet | none | not recommended: would pre-consume the unrun exam and cannot be fully scored |
| 1 routing (EXP-3), 1 type/family stamping (EXP-4B), 9 prose/remarks/Q&A/numberless lanes (QF-02..06), 7/8 catalog & concept judges | no built kit or no locked key | — | — | NOT testable in original form today |
Method for every Qwen exam: shadow tree only, own runner + scorer copies under
`qwen38_optimization/`, exact prompt bytes, `generate()` raw (no added instructions),
reasoning off, temperature 0, raw replies saved before parsing, keys never touched,
nothing written into `experiments/`. If the only failures are format (prose/fences),
one rerun on the GGUF build (schema grammar-enforced) separates accuracy from format.

## 13. RESULT — identity-judge exam (EXP-0 contract, K-pairs v1.3) on local Qwen, 2026-08-17
Setup (original form): key `experiments/keys/K-pairs/K-pairs.v1.3.jsonl` (sha 023fb1ce…, verified
against the lock), prompt = `experiments/harness/grader_prompt_framing.txt` byte-exact (sha 5a543bd1…),
no system message, no added instructions, reasoning off, temperature 0, one call per pair, raw reply
saved before parsing, schema `{pair_id, verdict, cited_a, cited_b, reason}` enforced by the runner
grammar (GGUF build `qwen3.8:27b-mtp-q4_K_M`) — the MLX build without enforcement answered the raw
prompt in prose and went invalid (1 pair tried), exactly the format risk in §10.

| metric (score_exp0 definitions) | Qwen3.8 (GGUF, schema-enforced) | Sonnet-A / Sonnet-B / Opus |
|---|---|---|
| wrong SAME (over-merge; must be 0) | **0 / 110** | 0 / 0 / 0 |
| false refusal (gold SAME → DIFFERENT) | **2 / 50 (4%)** — kp_0133, kp_0148 | 0 / 1 / 0 |
| invalid | **1 / 160** — kp_0152: runaway `reason` hit the 600-token cap; with the cap lifted it returns a valid DIFFERENT (i.e. a 3rd refusal) | 0 / 0 / 0 |
| correct | 157 / 160 (98.1%) | 160 / 159 / 160 |
| citations verbatim on both sides | 159 / 160 | — |
| gate: wrong_same=0 ∧ false_refusal≤10% ∧ invalid≤2% | **PASS** | PASS |
| speed | 28.4 s per pair (decode-bound on GGUF, ~7 tok/s); 160 pairs = 76 min | — |
Reading: zero unsafe merges (the safety metric), 2–3 over-refusals on the hardest SAME pairs
(DIY-vs-retail scope, RASM/PRASM unit ambiguity), i.e. slightly more conservative than Sonnet.
Set max_tokens ≥ 1500 for this role (the `reason` field is unbounded).
Script + raw results: `.claude/plans/Drivers/FinalDesign/QwenTests/qwen38_optimization/exams/identity_exam/`
(`identity_exam.py run|score --model … [--limit N]`, `run_gated.sh`, `results_qwen3.8_27b-mtp-q4_K_M/`
raw_results.jsonl + score.json + kp_0152_cap1500.json, `identity_exam.log`).

## 14. Which roles/steps benefit from the cache (and what has to change)
By role (7 real AI roles): **3 of 7 use the cache** — reader (many items per event), table/prose
locator (many anchors per table), concept picker (many facts per company menu). These are the
high-volume roles, so by call count roughly **70–80% of all calls are cache-fast** (~1 s each after the
document's one cold read). The other 4 — catalog chunk reader (each 40k-char chunk read once),
identity judge, continuity judge, graders/reviewers — read each input once at the plain ~95 tok/s;
their inputs are small (~1k tokens), so they still cost only ~10 s each.
By step: caching helps Steps **3, 5, 8, 9, 11**; Steps 1, 4, 7, 12, 13 don't benefit; Steps 0, 2, 6,
10, 14 have little or no model work.
Do tests change? **No test changes its questions or answers.** Two mechanical requirements to get
the cache: (1) put the shared document BEFORE the per-call part in the prompt — a prompt-layout
change, so re-freeze that prompt version; (2) one `L.prime()` call per document — touches nothing.

Speed vs Sonnet (for planning): fresh document — Sonnet ≈ 5–15 s to first token on 13k tokens vs
Qwen ≈ 2.3 min (10–20x); repeated document — Qwen ~1 s (competitive or faster); Qwen is one call
at a time. Backfill estimate: ~790 companies × 3 years × ~4 releases (+ transcripts) ≈ 10–30k
documents ≈ 150–450M tokens ≈ **3 weeks–2 months of 24/7 GPU** for one full read (later question
passes over the same documents are near-free only while cached).
Hardest exam for any LLM: the reader (every exact fact from a whole filing; Sonnet ≈ 40% recall in
EXP-2). Identity and table lanes are near-perfect for both.

## 15. RESULT — reader exam (EXP-2 blind driver-name reader, 10-chunk subset) on local Qwen, 2026-08-17
Setup (faithful single-prompt proxy; the July run was tool-using agents): same preamble, same
rulebook `RULES_full.txt` (sha b33ab08b…), same 40k-char chunk JSON, same STEP-3 extraction rules,
same output shape; key K-reader v3 (sha cf87a09a…); first 10 of the 40 chunks (296 gold facts).
Scorer = strict, deterministic (the official metric used Sonnet graders): a gold row is hit if a
candidate's name equals the gold/alt name OR its quote overlaps the gold quote; the SAME scorer
was run over Sonnet's and Opus's saved July responses on the same chunks (like-for-like, relative).

| first 10 chunks, 296 gold | Qwen3.8 | Sonnet 5 (July) | Opus (July) |
|---|---|---|---|
| either-recall (name or quote) | **50.0%** | 45.3% | 52.4% |
| exact-name recall | 32.8% | 32.1% | 35.5% |
| quote-anchored recall | 42.2% | 39.2% | 45.6% |
| recall on "hard" gold rows | 39.8% | 49.0% | 48.0% |
| candidates emitted / quotes verbatim | 148 / 98% | 120 / 100% | 126 / 100% |
| chunks with ZERO candidates | **2 of 10** (BLMN_031 10-K, CAKE_050 transcript) | 0 | 0 |
| speed | 394 s per chunk (GGUF, decode-bound) = 66 min for 10 | — | — |
Settings that worked / failed (all tried on the same chunk):
  MLX + JSON system message, reasoning off  -> valid JSON, EMPTY candidate list
  MLX, reasoning on / "low"                -> reasoning ran past 8,000–12,000 tokens, no answer
  GGUF runner + schema grammar, no reasoning -> 18 candidates, 56% recall  <== USED
Reading: on aggregate Qwen matches Sonnet on this strict scorer (and beats it on 6 of 10 chunks),
but it is less reliable — 2 of 10 chunks came back empty and it trails on the hard rows; empties
are trivially detectable (0 candidates → route to Sonnet). Precision was not judged (needs
graders). Full 40-chunk run would take ~4.5 h GPU. Set max_tokens ≥ 8000 (one chunk needed 5,097).
Script + raw results: `qwen38_optimization/exams/reader_exam/` (`reader_exam.py run|score --n 10
--model qwen3.8:27b-mtp-q4_K_M --mode grammar --think 0 --max-tokens 8000`; results in
`results_qwen3.8_27b-mtp-q4_K_M/`, `score_first10.json`, `per_chunk_first10.txt`, probe files for
the failed modes; inputs are read from `experiments/` — see README.txt).
