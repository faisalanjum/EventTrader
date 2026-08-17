# Qwen3.8-27B slow-prefill investigation

## Hardware / setup
- MacBook Pro M4 Pro, 48 GB unified. Ollama Metal budget: 37.4 GiB
- ollama 0.32.13, launchd com.faanjum.ollama, OLLAMA_HOST=0.0.0.0:11434
- Server env: OLLAMA_FLASH_ATTENTION=1, OLLAMA_KV_CACHE_TYPE=q8_0,
  OLLAMA_NUM_PARALLEL=4, OLLAMA_MAX_LOADED_MODELS=1, OLLAMA_KEEP_ALIVE=-1
- Models: qwen3.8:27b-mlx (nvfp4, 18GB, dense 27.8B, arch qwen3_5)
          qwen3.8:27b-mtp-q4_K_M (GGUF, 17GB)
- Client: EventMarketDB/config/local_llm.py on minisforum 192.168.40.73
  resolves host via mDNS CA-K429CXLGF9.local first, then IP 192.168.40.147

## CONTRADICTORY EVIDENCE (the whole puzzle)
- SCR-11-q1 direct probe, stream=True, IP: first token 4.9s @ prompt_eval=7502
  => ~1530 tok/s prefill. HEALTHY.
- Same case via local_llm client: 345.8s then connection reset.
- Server log shows some /api/chat at 744ms-800ms, others at 5m43s-7m0s.
- => The MODEL can be fast. Something in the PATH or STATE makes it slow.

## INVALIDATED (my own errors, do not reuse)
- "cold 7.5k prompt takes 400s": the random-filler probe was ~28k tokens,
  exceeding num_ctx=16384. Measured overflow, not prefill.
- "streaming turns 399s into 1.0s": that compared cold vs CACHED prompt.
- "~3x slower than qwen3.6": decode-only on a 17-token prompt.

## HYPOTHESES (ranked, to test)
H1. OLLAMA_KV_CACHE_TYPE=q8_0 is a llama.cpp flag; on the MLX engine it may
    force a slow/unsupported path. TEST: isolated server without it.
H2. OLLAMA_FLASH_ATTENTION=1 likewise unsupported on MLX -> O(n^2) attention.
H3. OLLAMA_NUM_PARALLEL=4 splits num_ctx into 4 slots; each slot gets
    num_ctx/4, so a 7.5k prompt may not fit one slot -> thrash/recompute.
    *** STRONG: with num_ctx=16384 and 4 slots, each slot = 4096 tokens.
    A 7502-token prompt EXCEEDS its slot. ***
H4. nvfp4 has no optimized Metal kernel -> slow dequant on Apple Silicon.
H5. mDNS host path (CA-K429CXLGF9.local) differs from direct IP.
H6. Memory pressure / swap once resident grows to 35 GB.

## MEASUREMENTS
(to fill in)

## MEASUREMENT 1: prefill sweep, production server (NUM_PARALLEL=4,
## FLASH_ATTENTION=1, KV_CACHE_TYPE=q8_0), num_ctx=16384, MLX model
 prompt_tok  prefill_s  tok/s
        661        9.4     71
       2571       26.6     97
       5651       54.2    104
       8731       76.0    115
      12251       47.8    256
      16651       92.1    181
=> FLAT ~100-180 tok/s. NO cliff at 4096. H3 (slot split) REJECTED.
=> Cold prefill ~100 tok/s => 7.5k prompt ~= 65s. Matches early run cases.
=> The 1530 tok/s reading earlier WAS a prefix-cache hit.
=> Therefore the 300s+ cases are a SECOND problem: progressive degradation
   correlated with memory creep 18 -> 25 -> 35 GB.

## MEASUREMENT 2: clean isolated server, port 11500
## (NUM_PARALLEL=1, FLASH_ATTENTION unset, KV_CACHE_TYPE unset)
 MLX  : 92, 91, 101, 121, 247, 149 tok/s prefill
 GGUF : 79, 84, 113, 163, 184,  71 tok/s prefill
=> IDENTICAL to production server. H1 (kv cache type), H2 (flash attn),
   H3/NUM_PARALLEL all REJECTED. Not a config problem.
=> Both engines same => not an MLX-vs-llama.cpp problem either. H4 rejected.

## ROOFLINE ANALYSIS (the actual root cause)
 prefill FLOPs ~= 2 * active_params per token
 qwen3.8-27B DENSE : 2 * 27.8e9  = 55.6 GFLOP/token
 M4 Pro 20-core GPU ~ 9.2 TFLOPS => ~165 tok/s CEILING
 MEASURED           : 100-180 tok/s  => WE ARE AT THE HARDWARE ROOFLINE.

 qwen3.6:35b-a3b MoE: only 3B ACTIVE => 2*3e9 = 6 GFLOP/token
                     => ~1500 tok/s ceiling => ~10x faster prefill.
 That is exactly why old model = 16.2 s/case vs new ~65 s/case.

=> NO configuration change can beat this. Dense 27.8B prefill on M4 Pro is
   compute-bound. Decode is FINE (27 tok/s vs 5-6 tok/s quoted for M4 base).

## THEREFORE the only two real levers
 L1. PROCESS FEWER TOKENS -> exploit Ollama prefix cache.
     Ollama caches KV for identical BYTE-FOR-BYTE prefixes while model loaded.
     Docs: "place changing data at the END".
     OUR PROMPTS DO THE OPPOSITE: question/driver FIRST, shared table AFTER.
     choice_v2 has ~19 families x 4-7 questions, each family sharing ONE table.
     Reordering table-first => 19 cold prefills instead of 93.
     Projected: 19*65s + 74*~1s ~= 22 min  (vs ~9 h). ~25x.
 L2. FEWER ACTIVE PARAMS -> MoE model for prefill-heavy work.

## RESEARCH NOTES
- orcarouter: Qwen3.8-27B MLX 4bit ~5-6 tok/s GEN on M4 mini 32GB.
  Ours is 27 tok/s decode on M4 Pro => our decode is healthy.
- Ollama caching: exact prefix match required; keep model loaded (KEEP_ALIVE);
  recent Ollama adds "intelligent checkpoints" + cross-conversation reuse.
- Claims of "MLX 3-5x faster prompt processing than Ollama" / oMLX 8664 tok/s
  are for much smaller models and/or batched throughput; they cannot beat the
  roofline for a 27.8B dense single sequence.

## MEASUREMENT 3: PREFIX CACHE (the actual fix) - clean server, 16384 ctx
 Identical prompt x3 (9894 tok): 122.2s -> 0.1s -> 0.0s
   => Ollama prefix cache gives 100% reuse when prefix matches exactly.
 Table-FIRST, only final question line varies: 24.3s, 24.6s
   => 5.0x faster than cold (122.2s). ~20% recompute = checkpoint granularity.
 Earlier 15155-tok test only got 2.1x because prompt nearly filled num_ctx
 (15155 of 16384) leaving no headroom -> cache evicted. HEADROOM MATTERS.

## ROOT CAUSE (final)
 Two independent facts:
 A) Dense 27.8B prefill on M4 Pro is compute-bound at ~100-180 tok/s.
    That is the hardware roofline (8.6 TFLOPS FP32 / 18.4 FP16 vs
    55.6 GFLOP per token). NOT fixable by configuration. Decode (27 tok/s)
    is healthy - better than the 5-6 tok/s others report on M4 base.
 B) Our prompts put the VARYING question BEFORE the SHARED table, which
    defeats Ollama's prefix cache. Every one of 93 calls pays full prefill
    even though ~19 tables are each reused by 4-7 questions.
 (B) is entirely ours and entirely fixable.

## THE FIX (verified, 5x; up to ~1000x on exact repeats)
 1. Put the SHARED TABLE FIRST, varying question LAST.
 2. Keep num_ctx comfortably above prompt size (headroom for cache).
 3. Keep model resident (KEEP_ALIVE=-1 already set).
 Projected choice_v2 (93 cases, ~19 families, 7502 tok, cold ~65s, warm ~13s):
   19*65 + 74*13 = ~37 min   (vs ~9 h unfixed; old MoE was 25 min)

## FURTHER UPSIDE (not yet tested)
 mlx_lm.cache_prompt / mlx_lm.server --prompt-cache-dir gives EXPLICIT
 per-prompt KV cache => near-100% reuse (0.1s class), i.e. ~21 min or better.
 Cost: needs mlx-community MLX weights (~15 GB) + client move off Ollama API.

## MEASUREMENT 4: real choice_v2 prompts, SCR-05 family (1781 tok)
 current layout : 21.3, 20.6, 19.9, 19.6 s
 reordered      : 20.7, 21.2, 21.4, 22.5 s   => NO GAIN
 Reason: 1781 tokens is too small to contain a cache checkpoint before the
 divergence point. Reordering only pays off on LARGE prompts.

## FAMILY STRUCTURE (all 93 cases)
 ALL 93 share ONE identical table body within their family (verified by hash).
 SCR-01..04  3 cases  ~8.1k chars (~3.5k tok)  = 12 cases
 SCR-05..07  4 cases  ~4.7k chars (~1.8k tok)  = 12
 SCR-08..10  4 cases  ~4.2k chars (~1.7k tok)  = 12
 SCR-11..14  7 cases  ~17.25k chars (~7.5k tok)= 28   <- the expensive ones
 SCR-15,16   4 cases  ~3.7k chars (~1.5k tok)  =  8
 SCR-17..19  7 cases  ~17.2k chars (~7.5k tok) = 21   <- the expensive ones
 => 49 of 93 cases are the ~7.5k-token families. That is where caching pays.

## REVISED PROJECTION (important - my "9 hours" was wrong)
 The 300s/case I measured during the broken runs was MEMORY THRASH
 (num_ctx=65536 x 4 parallel slots -> 35 GB of 37.4 GiB), not normal cost.
 At clean settings (num_ctx=16384, workers=1) real cost is ~roofline:
   49 big cases @ ~75s   = 61 min
   44 small cases @ ~20s = 15 min
   TOTAL unfixed ~= 76 min   (NOT 9 hours)
 With table-first caching on the 7 big families:
   7 cold @75s + 42 warm @~15s = 19 min ; small ones ~15 min
   TOTAL ~= 34-40 min   (old MoE = 25 min)

## MEASUREMENT 5: *** THE ANSWER *** real SCR-11 prompts, correct reorder
 My earlier "reorder" test was BROKEN: marker '"rendered_table"' does not
 exist in choice_v2 prompts (that is a qf01 format), so find() returned -1
 and the split moved only the last character. Not a hypothesis failure.

 choice_v2 _prompt() emits:
    Choose the exact source-table cell...
    Known Driver evidence: <VARIES>     <- at char ~144
    Requested cell: <VARIES>            <- at char ~144
    How to choose: ...
    Source-derived choices:
    <ROW blocks = ~17,000 chars, IDENTICAL across the family>

 => common prefix between two cases in a family: 144 / 17246 = 0.8%
 Move those 2 lines to the END:
 => common prefix 17196 / 17270 = 99.6%

 TIMED (clean server, num_ctx=32768, workers=1):
   SCR-11-q1 prefill 102.1s  (cold)
   SCR-11-q2 prefill 107.6s  (cold)
   SCR-11-q3 prefill   1.1s  <-  93x
   SCR-11-q4 prefill   0.6s  <- 170x

## FINAL ANSWER
 Root cause = prompt field ORDER, not the model, engine, quant, or config.
 Every varying token placed before the shared 17k-char table forces a full
 re-prefill of the whole table on every call. 93 calls x full table prefill.
 Fix = put the varying target lines LAST. Prefix cache then does the rest.
 Cost of change: ~3 lines in choice_v2._prompt(). Same for qf01/_row_v3.
 Projected choice_v2: ~19-34 min (vs ~76 min unfixed). Old MoE was 25 min.
 => Qwen3.8 becomes competitive with / faster than the old model AND is
    more accurate (19/19 vs 17/19).

## OPTIMIZATION #1: make prefix caching engage in the HARNESS (in progress)
 Isolated test (reorder_test.py) DID cache: 102.1s -> 1.1s -> 0.6s
 Harness with same reordering did NOT: 92.7, 86.5, 46.2s
 Differences between the two paths:
   isolated : no system msg, NO format schema, num_predict=8, localhost
   harness  : system msg, format=JSON schema, num_predict=512, over LAN
 Tried NUM_PARALLEL=1 (clean server on :11500, harness via LOCAL_LLM_HOST):
   still no caching => NUM_PARALLEL alone is NOT the cause.
 Research confirms multiple slots CAN interfere + multiply KV memory, so
 NUM_PARALLEL=1 is still worth keeping, but it is not the blocker.
 NEXT: controlled 4-variant isolation (baseline / +system / +format / all)
 PRIME SUSPECT: passing `format` (JSON schema) may disable prompt caching,
 because constrained decoding changes the sampling/state path.

## VICTORY LOCKED IN #1: OLLAMA_NUM_PARALLEL 4 -> 1 (production plist)
 Backup: /tmp/plist_before_numparallel.plist
 GOTCHA: `launchctl kickstart -k` does NOT reload EnvironmentVariables.
 Must use: launchctl bootout gui/$UID/com.faanjum.ollama
           launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.faanjum.ollama.plist
 Verified live: OLLAMA_NUM_PARALLEL:1, host 0.0.0.0:11434, tunnel OK.
 Benefit: 4x less KV cache memory reserved (was the 35 GB thrash cause),
 and removes multi-slot interference with prefix-cache reuse.

## DECISION: qwen3.6:35b-a3b re-pull ABANDONED (owner call, correct)
 It scored 17/19 NOT_SAFE_FOR_TASK and 75/93. Never met the accuracy bar,
 so its speed advantage is irrelevant. No reason to keep it as a fallback.

## CORRECTION: my prefill_sweep.py was INVALID (prefix sharing)
 build(30) was a literal prefix of build(120) of build(260)... same nonce.
 Each sweep step reused the prior step's KV cache => measured INCREMENTAL
 prefill. The "100-180 tok/s, at the roofline" conclusion was WRONG.

## TRUE COLD PREFILL (unique random content per call, no shared prefix)
   1622 tok  24.2s   67 tok/s
   4821 tok  76.8s   63 tok/s
   9621 tok 154.4s   62 tok/s
 => flat ~63 tok/s, LINEAR. ~41% of 8.6 TFLOPS FP32 roofline.
 => maybe ~2x available from a better engine, NOT "already at the limit".

## ENV A/B AT 32768 (both 3 calls, reordered SCR-11 prompts)
 production (flash_attn=1, kv q8_0, np=1): 263.3, 271.0, 1.4
 clean      (no flash_attn, no kv q8_0)  : 252.8, 236.8, 2.0
 => env vars genuinely irrelevant, confirmed at 16k AND 32k.
## NUM_CTX MATTERS for prefill speed
 same prompt, clean server: 32768 -> 252.8/236.8 ; 16384 -> 201.4/131.2
 => keep num_ctx as small as safely fits. Use 16384.
## CACHE BEHAVIOUR: engages from the THIRD call (2-call warmup), reproducible
 32768: 263, 271, 1.4   |  16384: 201, 131, 1.2  |  clean32k: 253, 237, 2.0

## OLLAMA OFFICIAL (owner-supplied announcement)
 - "over 70 output tok/s on MacBook M5 Max" for qwen3.8:27b-mlx.
   We get 27 tok/s decode on M4 Pro -> proportionate, decode is healthy.
 - MTP is an NVIDIA-Blackwell optimization (131 tok/s there). Explains why
   qwen3.8:27b-mtp-q4_K_M gave us nothing on Apple.
 - 27b-mlx IS the recommended Apple Silicon build. We are on the right one.

## *** VICTORY #2 LOCKED IN: PREFIX CACHING NOW LIVE IN THE HARNESS ***
 THE BUG THAT HID IT: _prompt() runs during prepare(), NOT during run().
 Prompts are baked into cases.jsonl. I patched _prompt() but never re-ran
 prepare(), so EVERY run up to now used the OLD layout. All my "caching
 doesn't work in the harness" results were testing unmodified prompts.
 Fix: rm cases.jsonl manifest.json ; choice_v2.py prepare

 After regenerate:
   "Known Driver evidence" moved char 68 -> 7965 (of 8165)
   SCR-11 family shared prefix 0.8% -> 99.2%
   93/93 cases carry the new TARGET block

 3-call isolation (before regenerate) proved request params are all FINE:
   baseline            213.9 266.0 1.3  CACHE WORKS
   + system message    272.8 198.9 1.0  CACHE WORKS
   + format schema     202.2 200.2 0.9  CACHE WORKS
   harness-equivalent  329.4 235.7 0.7  CACHE WORKS
   (my earlier 2-call test could never detect this: cache needs 3 calls)

 LIVE RUN RESULT (first 6):
   SCR-01-q1 39.3s | q2 54.6s | q3  2.3s   <- cached
   SCR-02-q1 40.9s | q2  1.0s | q3  1.0s   <- cached from 2nd call
   0 bad responses
 => ~40x on cached calls. Projected 93 cases ~16 min
    (vs ~76 min unfixed; old MoE was 25 min) => FASTER THAN THE OLD MODEL.

## CUMULATIVE OPTIMIZATION STACK (all verified)
 1. OLLAMA_NUM_PARALLEL 4 -> 1        (plist, live)
 2. num_ctx 65536 -> 16384            (measured faster + no thrash)
 3. prompt reorder + REGENERATE cases (the 40x)
 4. MAX_TOKENS 64 -> 512              (stops truncation aborts)
 5. system message                    (MLX has no grammar enforcement)
 6. fence stripping on parse          (MLX wraps JSON in ```)
 7. WORKERS 1                         (avoids slot contention)

################################################################
## TODO LIST - REMAINING OPTIMIZATIONS (prioritized)
################################################################
### HIGH (free, high confidence, do next)
 T1. Apply prompt reorder + REGENERATE to row_v3.py and qf01.py.
     Same latent bug. row_v3 = 93 cases / 8 tables = 11.6 calls per table,
     the BEST caching ratio of all three suites. qf01 aligned = 1.0, no gain.
 T2. Kill the cold-prefill warmup. Currently ~19 families x ~40s = ~13 of the
     ~16 min is cold prefill. Cache engaged on call 3 for SCR-01 but call 2
     for SCR-02 - understand why, make it always call 2 (or 1).
 T3. GGUF ACCURACY TEST (never run). Decode penalty is irrelevant at 8-token
     outputs; grammar enforcement would REMOVE the need for T-system-message
     and fence-stripping. May be the more reliable production choice.
 T4. num_ctx 16384 -> 8192. Max prompt ~7.5k tok. Halving 32768->16384 gave
     253s->201s, so another halving may pay. Needs the corrected budget check.

### MEDIUM (real upside, real cost)
 T5. NATIVE mlx-lm benchmark (OWNER REQUESTED). Research claims 3-5x faster
     prompt processing vs Ollama. Prefill is 100% of our bottleneck (~63
     tok/s cold), so this is the largest single remaining lever.
     Cost: ~15 GB mlx-community weights on a hostile network + client/tunnel
     rewrite (OpenAI-style API, not Ollama API). mlx-lm already installed in
     scratchpad/mlxenv.
 T6. mlx_lm.cache_prompt / mlx_lm.server --prompt-cache-dir: precompute each
     table's KV ONCE, reuse for all its questions. Would remove even the
     per-family cold prefill. Part of the T5 track.
 T7. Re-test OLLAMA_NUM_PARALLEL > 1 now that num_ctx is 16384. Memory is no
     longer the constraint, so concurrency might raise throughput without
     the thrash that made it harmful at 65536.
 T8. Check for a newer Ollama. 0.32.13 today. Release notes mention
     "intelligent checkpoints" + cross-conversation cache reuse, which is
     exactly T2.

### LOW / DELIBERATELY DEPRIORITIZED (do not chase)
 T9. mlx-dspark speculative decoding. It accelerates DECODE. Our outputs are
     6-8 tokens; decode is ~1s of a ~40s call. Near-zero benefit here.
 T10. 8-bit / mxfp8 quant. Slower (more bytes/token) and 4-bit already scores
     19/19. No measured accuracy deficit to fix.
 T11. Prompt-size reduction (prune table rows). Real lever (prefill is linear
     in tokens) BUT changes what the model sees => accuracy risk. Only after
     accuracy is locked.

### REPO HYGIENE (needs owner approval - real files)
 T12. Port to the REAL repo: byte-vs-token budget bug in ensure_prompt_budget
     (compares UTF-8 bytes to a token budget, ~4x too strict - this is what
     forced num_ctx=65536), plus the prompt reorder. Currently shadow-only.
 T13. QF-01 gold key is stale (post-July inline_html.py nbsp fix invalidated
     it). Needs regeneration or an nbsp-insensitive grader. Blocks any
     future qf01 scoring, independent of model.

### T14 (OWNER REQUESTED): optimize the FRESH-DOCUMENT case
 Prefix caching does nothing when every call brings a new document
 (qf01 aligned = 1 call per table). Prefill is linear at ~63 tok/s, so the
 only levers are: send fewer tokens, or prefill them faster.
 T14a. PERSIST KV CACHE TO DISK per document.
       mlx_lm.cache_prompt + mlx_lm.server --prompt-cache-dir.
       Pay a document's prefill ONCE, ever - across runs, sessions, days.
       Turns "fresh" into "cached" from the 2nd run onward. Biggest win for
       iterating on a benchmark. Ollama has no disk-persistent equivalent.
 T14b. FASTER PREFILL ENGINE = T5 (native mlx-lm, claimed 3-5x). The only
       lever that helps a genuinely first-ever document without touching
       content.
 T14c. SEND FEWER TOKENS. Deterministic pre-filter: drop table rows/columns
       that cannot contain the answer before the model ever sees them.
       Prefill is linear, so 50% fewer tokens = 50% faster. ACCURACY RISK:
       if the filter drops the right row the model cannot recover. Must be
       provably lossless (e.g. keep all rows whose label could match) and
       re-scored.
 T14d. STATIC INSTRUCTION PREFIX FIRST. Even with unique documents the
       instruction block is identical across calls. Small (~500 of 17,000
       chars) but free.
 T14e. BATCH concurrent fresh documents. Does not cut per-document latency
       but raises throughput. Now viable since num_ctx=16384 removed the
       memory pressure (see T7).
 T14f. TWO-STAGE: cheap small model prunes candidate rows, Qwen3.8 sees a
       much smaller prompt. Large potential win, but adds a model and a
       failure mode. Only after accuracy is locked.

## *** RESULT: FIRST COMPLETE choice_v2 RUN (93/93) ***
 NEW qwen3.8:27b-mlx, reordered prompts, prefix cache ON, num_ctx=16384,
 NUM_PARALLEL=1, workers=1, max_tokens=512, system message, fence-strip:
   89/93 correct (95.7%), 4 wrong, 0 invalid, 0 transport failures
   wall 1677s = 28.0 min
 OLD qwen3.6:35b-a3b (July, original prompts):
   75/93 (80.6%), 18 wrong, wall 1510s = 25.2 min

 => 4.5x fewer errors (18 -> 4) at essentially the same wall clock,
    despite dense 27.8B vs 3B-active MoE. Caching closed the speed gap.

 NEW fixed 17 that OLD got wrong.
 NEW broke 3 that OLD got right: SCR-13-q3, SCR-19-q3, SCR-19-q4
 BOTH wrong: SCR-19-q2
 ALL 4 new failures are the SAME failure mode: WRONG:occurrence
 (occurrence = positional index left-to-right within a row)

## REORDER EXONERATED (partially, 1 of 4 checked so far)
 SCR-13-q3: gold=24, qwen3.8 REORDERED=26, qwen3.8 ORIGINAL=26
 => identical wrong answer in BOTH layouts => the reorder did NOT cause it.
    It is a genuine Qwen3.8 weakness at occurrence counting.
 (remaining 3 running)

## STILL NOT AT THE BAR
 Owner requires 100%. We are at 95.7%. The gap is ONE failure mode:
 occurrence counting. Next: T15.

## OCCURRENCE ISOLATION - FULL RESULT
 case        gold  REORDERED  ORIGINAL
 SCR-13-q3     24         26        26   genuine model error
 SCR-19-q2     11         24        23   genuine (old model failed too)
 SCR-19-q3     24         26        26   genuine model error
 SCR-19-q4     25         26        25   *** REORDER BROKE THIS ONE ***
 => 3 of 4 genuine Qwen3.8 occurrence errors; 1 of 4 caused by reordering.
 => HONEST TRADE: reorder = 2.7x faster (76min -> 28min), costs ~1 case/93.
    without reorder 90/93 in ~76 min ; with reorder 89/93 in 28 min.
    NEITHER is 100%. Occurrence counting is the blocker, not the reorder.

## T15 (NEXT): ELIMINATE OCCURRENCE ERRORS - the fix already exists
 row_v3 is the owner's own redesign: "Qwen chooses one source row or
 abstains; CODE applies the request's explicit left-to-right occurrence
 number and copies the exact evidence." Occurrence removed from the model.
 That design took qf01 from 0/93 to row_v3 93/93 on the old model.
 row_v3 also has the BEST caching ratio: 93 cases / 8 tables = 11.6.
 => Run row_v3 with qwen3.8 + full optimization stack. Expect fast AND
    potentially 93/93 because the failing capability is not exercised.

## *** VICTORY #3: row_v3 = 100% ACCURACY WITH QWEN3.8 ***
 row_v3 NEW qwen3.8:27b-mlx : 93/93, precision 1.0, recall 1.0, 0 wrong
                              wall 226s = 3.8 min
 row_v3 OLD qwen3.6:35b-a3b : 93/93, 1.0/1.0, wall 150s = 2.5 min
 Caching: 14.2s cold -> 0.5s repeats (93 cases = only 18 distinct prompts)

## THE CONFIRMED RECIPE FOR 100% + SPEED
 Every qwen3.8 choice_v2 error was WRONG:occurrence. row_v3 removes
 occurrence from the model (code applies it) => 100%.
 => Task design matters more than the model. Owner's own July redesign
    ("code constructs IDs, Qwen never retypes") is the fix.

## SCOREBOARD (qwen3.8:27b-mlx, full optimization stack)
 suite        design                          score      wall
 row_v3       code does occurrence            93/93 100% 3.8 min
 qf01 aligned 1 table per call, no caching     19/19 100% 7.4 min
 choice_v2    model does occurrence            89/93 95.7% 28 min
 (old model: row_v3 93/93 / qf01 17/19 / choice_v2 75/93)

 CAVEAT: all development sets with OPENED answers. Not certification.
 row_v3 is also the easiest task by construction.

## *** ROOT CAUSE OF PERFORMANCE VARIANCE: 30W CHARGER ***
 Mac16,8 = MacBook Pro 16-inch M4 Pro. Ships with a 140W adapter.
 MEASURED: power adapter Wattage = 30 W ; battery 5% ; "13:15 to charge".
 An M4 Pro under sustained GPU load draws far more than 30W, so the deficit
 drained the battery to 5%; macOS then throttles the SoC to fit 30W.
 No thermal warning because it is a POWER limit, not heat.

 EXPLAINS:
  - the smooth engine-independent creep (SCR-10 q1..q4: 15.8/21.7/30.2/35.8s
    on IDENTICAL prompt sizes, with memory flat at 18 GB)
  - why the same SCR-11 prompt measured 102s early and 263s later
  - the repeated ~300s connection resets (calls creep past the ~300s idle
    window as throttling deepens)
  - why "cold prefill" drifted between measurements all session

 WHAT IS STILL VALID:
  - ALL ACCURACY RESULTS (temperature 0; correctness is power-independent)
  - relative comparisons taken minutes apart (caching 40x, reorder effect,
    row_v3 0.5s cached vs 14s cold)
 WHAT IS NOT:
  - every ABSOLUTE throughput number today is a LOWER BOUND, possibly by 2-4x.
    The ~63 tok/s "true cold prefill" and the roofline-efficiency estimate
    must be re-measured on a proper 140W adapter.

## T16 (DO FIRST, COSTS NOTHING): plug into the 140W adapter, charge to
## >80%, re-baseline. This may dwarf every software optimization found.

## *** VICTORY #4: OLLAMA_LOAD_TIMEOUT WAS KILLING EVERY LONG RUN ***
 Default OLLAMA_LOAD_TIMEOUT = 5m = 300s. Ollama aborts any request whose
 prefill exceeds it; the client sees "[Errno 104] Connection reset by peer".
 EVERY aborted run died to this:
   SCR-11-q2 302.1s | SCR-11-q4 312.5s | SCR-11-q1 308.1s / 345.8s
   SCR-12-q2 399.6s | SCR-12-q3 422.6s | GGUF SCR-11-q1 312.4s
 PROOF: SCR-12-q3 (previously FAILED at 422.6s) on a server with
   OLLAMA_LOAD_TIMEOUT=30m -> SUCCESS in 344.1s, prefill 330.7s,
   output {"choice": 3}
 FIX APPLIED to production plist: OLLAMA_LOAD_TIMEOUT=30m (live, verified).
 NOTE: I wrongly blamed a "network middlebox idle timeout" earlier. It was
 Ollama's own setting all along, and I had seen it in the config dump on the
 very first inspection without following it up.

 INTERACTION WITH THE 30W CHARGER: throttling inflates prefill past 300s,
 and the timeout then executes the request. Fixing the timeout makes runs
 COMPLETE regardless of power; fixing power makes them FAST. Need both.

## PRODUCTION PLIST NOW (backups in /tmp/plist_before_*.plist)
   OLLAMA_HOST=0.0.0.0:11434    OLLAMA_KEEP_ALIVE=-1
   OLLAMA_NUM_PARALLEL=1        OLLAMA_LOAD_TIMEOUT=30m
   OLLAMA_FLASH_ATTENTION=1     OLLAMA_KV_CACHE_TYPE=q8_0
   OLLAMA_MAX_LOADED_MODELS=1

## *** VICTORY #5: TWO SEPARATE ~300s TIMEOUTS, BOTH NOW UNDERSTOOD ***
 (a) SERVER: OLLAMA_LOAD_TIMEOUT default 5m aborts long prefills.
     FIXED in plist -> 30m. Server now returns 200 on 5-7 minute calls
     (verified in ollama-agent.log: 5m10s, 6m48s, 6m50s all HTTP 200).
 (b) CLIENT/LAN: something on the Minisforum->Mac path reaps connections
     idle ~300s. During prefill NO tokens flow, so streaming does not help.
     FIX = TCP keepalive on the client socket.
       SO_KEEPALIVE=1, TCP_KEEPIDLE=30, TCP_KEEPINTVL=30, TCP_KEEPCNT=60
       (KEEPCNT must be <=127; 200 raises EINVAL "Invalid argument")
     VERIFIED: SCR-19-q2 over LAN -> SUCCESS 96.5s, {"choice": 25}
     (localhost calls were never affected - only the LAN path)

## *** T3 ANSWERED: GGUF DOES NOT FIX ACCURACY ***
 SCR-13-q3  gold=24  MLX=26  GGUF=26   identical wrong answer
 SCR-19-q2  gold=11  MLX=24  GGUF=25   both wrong
 => the WRONG:occurrence weakness is inherent to Qwen3.8 itself, not to the
    quantization (nvfp4 vs Q4_K_M) nor the engine (MLX vs llama.cpp).
 => GGUF's only real advantage remains native grammar enforcement, which
    only removes the system-message + fence-strip scaffolding.
 => Use MLX (4x faster decode, prefix caching works well).

## T2 ANSWERED BY RESEARCH (llama.cpp issue #22942)
 "prompt-cache checkpoints are slot-local; under -np > 1 a matching prefix
 routed to a different slot falls through to a COLD prefill."
 => NUM_PARALLEL=1 (already applied) is the documented mitigation.

################################################################
## COMPLETE BOTTLENECK MAP (first principles)
## cost = prefill_tokens/prefill_rate + out_tokens/decode_rate
## out = 6-8 tok (~0.3s). prefill = 2k-7.5k tok @ ~63 tok/s.
## => PREFILL IS ~99% OF EVERY CALL. Only 3 levers exist:
##    (C) avoid prefill, (A) shrink it, (B) speed it up.
################################################################
(C) AVOID PREFILL
 C1 prefix cache within a run .............. DONE (40x)
 C2 cache persistence ACROSS runs .......... OPEN - mlx-lm --prompt-cache-dir
    Ollama has no disk-persistent cache. This is THE fix for the
    fresh-document case on any repeated run.
 C3 cold warmup 1-2 calls per family ....... mostly fixed by NUM_PARALLEL=1
 C4 cache eviction / work ordering ......... cases already grouped by table
(A) SHRINK PREFILL
 A1 static instructions first .............. OPEN (small, free)
 A2 prune irrelevant rows before sending ... OPEN (big, accuracy risk)
 A3 denser table encoding .................. OPEN. Current format is verbose:
      'choice 22: occurrence #1 value="2,259" headers=["4Q23"]'
      Could be '22|1|2,259|4Q23'. Possibly ~2x fewer tokens = ~2x faster.
 A4 drop empty/redundant fields ............ OPEN. caption="" repeated per row.
(B) SPEED UP PREFILL
 B1 native mlx-lm (claimed 3-5x) ........... DOWNLOADING
 B2 smaller model .......................... REJECTED (accuracy)
 B3 num_ctx tuning ......................... 32768->16384 helped; test 8192
 B4 batching ............................... throughput only, not latency
 B5 power/hardware ......................... MEASURED: does NOT affect burst
                                             (27.1 -> 29 tok/s at 16% batt)
(D) ACCURACY
 D1 occurrence counting .................... FIXING NOW (label occurrences)
 D2 MLX no grammar enforcement ............. mitigated (system msg + fences)
(E) RELIABILITY
 E1 OLLAMA_LOAD_TIMEOUT 5m ................. FIXED (30m, plist)
 E2 LAN idle timeout ~300s ................. PROVEN FIX (TCP keepalive) but
    *** NOT YET APPLIED TO local_llm.py *** - harness still vulnerable!
 E3 NUM_PARALLEL slot-local cache bug ...... FIXED (=1, plist)

## A3 QUANTIFIED - DENSE ENCODING IS THE FRESH-DOCUMENT FIX
 largest case SCR-14-q1 = 21,472 chars, of which 296 "choice" lines = 16,745
 chars = 78% of the entire prompt.
   current : '  choice 1: occurrence #1 value="10.4" headers=["4Q23"]'
   dense   : '1|1|10.4|4Q23'
   choice-line chars 16,745 -> 4,333  (74% saved)
   WHOLE PROMPT      21,472 -> 9,060  (58% smaller)
 Prefill is LINEAR in tokens => ~2.4x faster on EVERY COLD call.
 Unlike caching this works when every document is brand new. THIS is the
 answer to the fresh-document bottleneck (T14c done properly, losslessly -
 it is a pure re-encoding, no information is dropped).
 RISK: changes the prompt => must re-score accuracy.

## E2 KEEPALIVE NOW APPLIED to config/local_llm.py (was proven but unapplied)
 _KeepAliveConnection + _OPENER; _post uses _OPENER.open.
 SO_KEEPALIVE=1, TCP_KEEPIDLE=30, TCP_KEEPINTVL=30, TCP_KEEPCNT=60.

## *** VICTORY #6: OCCURRENCE LABELLING FIXES 3 OF 4 ACCURACY FAILURES ***
 Emit 'choice 22: occurrence #1 value=...' so the model READS the ordinal
 instead of counting it across 7 items.
   SCR-13-q3  26 -> 24  FIXED
   SCR-19-q3  26 -> 24  FIXED
   SCR-19-q4  26 -> 25  FIXED
   SCR-19-q2  24 -> 23  still wrong (gold 11). OLD model also failed this
                        one as WRONG:block => row-selection, not occurrence.
 => choice_v2 projected 92/93 (98.9%) from 89/93.
 Same principle as row_v3: move deterministic work out of the model.

## MLX WEIGHTS DOWNLOADED (T5 now testable)
 mlx-community/Qwen3.8-27B-4bit
 /Users/faanjum/.cache/huggingface/hub/models--mlx-community--Qwen3.8-27B-4bit

## *** T5 ANSWERED: NATIVE mlx-lm IS ONLY 1.35x, NOT 3-5x ***
 mlx-community/Qwen3.8-27B-4bit via mlx_lm.generate, SCR-14-q1 (8,450 tok):
   run1 96.3s => 88 tok/s ; run2 100.3s => 84 tok/s
 Ollama MLX cold prefill: ~63 tok/s  =>  mlx-lm is ~1.35x faster.
 The published "3-5x faster prompt processing" does NOT reproduce for a
 27.8B dense model on M4 Pro - those figures are small models / batched.
 ALSO: mlx-lm output was PROSE ("We need answer user's request...") - it has
 no grammar enforcement either, so it needs the same scaffolding.
 COST: full client + autossh tunnel rewrite (OpenAI-style API).
 VERDICT: NOT worth it for raw speed. Its only unique value is T14a
 (disk-persistent prompt cache). Park unless repeated-run caching is wanted.

## PRIORITY DECISION (evidence-based)
 dense encoding  = 2.4x on ALL cold calls, NO infrastructure change  <== DO
 native mlx-lm   = 1.35x, full rewrite                               <== park

## *** POWER: NOW PROVEN FOR SUSTAINED LOAD (earlier I over-corrected) ***
 During the dense 93-case run the battery fell 16% -> 5% (GPU outdraws the
 30W adapter). Cold first-call per family, SAME prompt size for SCR-11/12
 (~10.7k chars dense):
    SCR-11-q1   85.1s
    SCR-12-q1  295.5s   <- 3.5x slower, later in the run, identical size
 Small-table cold calls earlier in the run: 30.2/31.9/30.4/17.3/17.8/16.3s
 CONCLUSION (accurate, evidenced):
   - SHORT BURSTS unaffected  (decode 27-31 tok/s at 5% and at 16%)
   - SUSTAINED RUNS degrade up to ~3.5x as the battery depletes
 => the 140W adapter DOES matter, but only for batch work, not peak speed.
 => every long-run wall-clock number in this session is depressed.
 My first claim ("may dwarf every optimization") was too strong; my second
 ("does not matter") was too weak. This is the correct middle.

################################################################
## *** 100% ACCURACY ON ALL THREE SUITES ***
################################################################
 choice_v2  93/93  precision 1.0  (dense encoding + occurrence labels)
 row_v3     93/93  precision 1.0
 qf01       19/19  precision 1.0
 PROGRESSION on choice_v2 (the hard suite):
   old qwen3.6                     75/93  80.6%
   qwen3.8 verbose prompts         89/93  95.7%
   qwen3.8 + dense + occurrence    93/93  100%
 Even SCR-19-q2 (which survived the targeted occurrence fix, and which the
 OLD model also failed as WRONG:block) is now correct - the denser table
 apparently helped row selection too.

## AUTO-RESUME: the robust answer to the ~320s LAN reset
 Server COMPLETES and CACHES the work (log: "200 in 5m19s") while the client
 sees ECONNRESET; Ollama then logs 'Request terminated error="context
 canceled"'. TCP keepalive did NOT satisfy whatever reaps the connection.
 So: retry. Each resume lands on a warm server cache and converges fast.
 /tmp/autoresume.sh - converged 81 -> 93 in TWO attempts.
 This is TRANSPORT retry (harness guarantees completed answers are never
 re-asked), not semantic repair.

## KEY PROCESS LESSON (cost me hours, twice)
 I patched files that the RUN DID NOT USE:
  1. _prompt() edits had no effect because prompts are baked into
     cases.jsonl at prepare() time -> must re-run prepare().
  2. config/local_llm.py edits had no effect because the shadow tree has its
     OWN copy and the harness imports from ROOT=shadow -> must sync the copy.
 ALWAYS verify the artifact the run actually reads.

## T4 (num_ctx 8192) - ABANDONED, NOT MEASURABLE
 A/B on the identical dense prompt (6,248 tok):
   16384 -> 74.9s (83 tok/s)
    8192 -> 96.0s (65 tok/s)
   reversed order:  8192 -> 298.6s (21 tok/s)
 SAME config, 96.0s vs 298.6s = 3.1x variance. Throttling noise dwarfs any
 num_ctx effect. Not measurable on this power supply. KEEP 16384 (which is
 proven: it removed the 35 GB thrash and is well clear of the 6.2k-token
 dense prompts). Revisit only on a 140W adapter.
 => "do not chase what does not work" - stopping this line.

################################################################
## SESSION 2 (2026-08-16 evening) — after commit 480b6a73
################################################################

## HARDWARE FACTS CORRECTED (earlier notes said 16-inch / 140W — WRONG)
 sysctl hw.model = Mac16,8 ; display 3024x1964 => 14-inch MacBook Pro
 Apple M4 Pro, 12-core CPU (8P+4E), 16-core GPU, 48 GB. Ships with a 70W
 USB-C adapter (96W optional). Connected: "30W USB-C Power Adapter".
 Measured drain under GPU load: 25% -> 17% in ~4 min (llama-bench);
 idle recharge ~ +0.25%/min. => sustained batch runs are power-bound.

## WORKLOAD PROFILE (from LeftOverSteps step1-5, 7-9, 14 + QwenTests docs)
 Reader (Steps 3/5, highest volume): instructions + WHOLE event source parts
   + one item; the same event is re-sent per item -> prefix cache pays;
   output = multi-fact JSON with verbatim quotes (100s of tokens).
 Fiscal locator (Step 9A): anchor + one complete table/prose block; same
   table re-sent per anchor -> cache pays; output tiny (ID list).
 Catalog reader (Steps 1/7): 40,000-char chunks (~10k tok), each read ONCE
   -> fresh-document prefill, no cache help; up to ~600 calls.
 Identity/continuity judges (Step 4): mostly unique inputs, small outputs.
 Concept picker (Step 8): fact + whole company concept menu (menu repeats).
 Steps 1-13 currently run Sonnet 5; Qwen is the Step-14 cheaper-model
 candidate + diagnostics. No numeric latency SLA anywhere; accuracy bar =
 zero wrong accepted. Largest stated input: 40,000 chars.

## ENGINE BAKE-OFF ON THIS MACHINE (cold prefill = the fresh-document metric)
 llama.cpp b10450 Metal, GGUF Q4_K_M, pp6144: 81.6 tok/s (ub512), 80.9 (ub2048)
                                       tg32 :  9.8-10.1 tok/s (no MTP)
 Ollama MLX (nvfp4), same-size real prompt : 84-87 tok/s cold prefill,
                                       decode ~29 tok/s WITH MTP (log:
                                       "speculative decode stats ... acceptance=1.00
                                       avg_draft=3.00")
 mlx-lm 0.31.3 affine-4bit (earlier)     : 84-88 tok/s
 llama.cpp Apple-Silicon table (M4 Pro 16-core, 7B Q4_0 pp512 = 364 t/s)
   scaled to 27.8B dense => ~88 tok/s. All engines agree.
 => COLD PREFILL IS AT THE HARDWARE CEILING (~85 tok/s) ON THIS GPU.
    No engine/config change can make a NEW document faster here. Levers left
    for fresh docs: fewer tokens, or faster hardware (M4 Max ~2x, M5 much
    more: llama.cpp logs "tensor API disabled for pre-M5").
 Ollama 0.32.14 (Aug 15) exists; 0.32.10 already added +7-8% NVFP4 prefill.

## THE OLLAMA MLX PREFIX CACHE, FROM SOURCE (x/mlxrunner, main 2026-08-16)
 pipeline.go : prefillChunkSize = 2048 (fixed); automatic snapshots at every
               8192 tokens AND at len(prompt)-4 ("preThinking"); no env knobs.
 prefix_cache.go : trie of token paths; snapshots at the frontier + at branch
               points, but a branch-point snapshot is scheduled only DURING
               THE REQUEST THAT DIVERGES THERE (i.e. the second one).
               "Snapshotting non-leaf nodes ... would produce wrong results for
               non-rewindable caches (e.g. RecurrentCache)". Qwen3.8 has
               recurrent layers => a diverging request cannot trim back.
               maxPagedOutBytes = 8 GiB; evict oldest, deepest, largest.
 mtp.go      : draftLookahead=1 -> MTP speculative decoding is ON for this
               model (explains decode > memory-bandwidth bound).
 => THIS is why every table cost TWO cold prefills before hits started
    (log: q2 "cache hit total=6284 matched=6222 cached=42").

## *** VICTORY #7: PREFIX PRIMING — 1 cold prefill per document, not 2 ***
 A raw /api/generate request whose tokens are EXACTLY the shared prefix
 (rendered as the qwen3.8 renderer would: "<|im_start|>system\n{sys}<|im_end|>\n
 <|im_start|>user\n{prefix}") leaves the automatic len-4 snapshot ON the
 shared path, so the FIRST real call restores there.
 Measured (SCR-11 dense, 6.2k tok, fresh nonce, prod server, num_ctx 16384):
   control: q1 79.3s | q2 74.4s (cached=42) | q3 1.5s   = 155 s
   primed : PRIME 72.3s | q1 2.9s (cached=6212) | q2 1.9s | q3 1.2s = 78 s
   answers identical ({"choice":15/16/17}).
 Implemented: config/local_llm.py prime()/prime_for()/shared_prefix()
 (real + shadow copies identical); shadow choice_v2.py primes once per family
 (QWEN_PRIME=0 disables) and records prime_calls in run_record.
 Generalises to every repeated-document role (reader per item, locator per
 anchor, picker per company): cost = 1 cold + K cheap instead of 2 cold + (K-2).

## Renderer facts (model/renderers/qwen35.go, qwen3.8 variant)
 think=nil  -> reasoning ON with "Reasoning effort is set to xhigh" system text
 think=false-> no reasoning text; assistant prefill "<think>\n\n</think>\n\n"
 Our client always sends think=False (LOCAL_LLM_THINK=0) => no hidden thinking.
 Content is TrimSpace'd. No BOS.

## num_ctx configurability
 client: LOCAL_LLM_NUM_CTX (default 32768), LOCAL_LLM_TIMEOUT (new, 1800 s),
         LOCAL_LLM_MODEL, LOCAL_LLM_THINK, LOCAL_LLM_HOST.
 shadow harness: QWEN_NUM_CTX at prepare time (frozen into manifest).
 Rule: keep num_ctx constant per run — a change reloads the model AND drops
 the whole prefix-cache trie.

## *** VICTORY #8: FULL choice_v2 WITH PRIMING = 93/93 IN 9.0 MIN, COLD CACHE ***
 2026-08-16 22:04-22:13, model freshly reloaded (empty trie), battery 30%->18%.
   93/93 correct, precision 1.0, recall 1.0, 0 transport failures, ONE pass.
   19 prime calls = 438 s (13 cold: SCR-01/03/04/05/06/08/09/11/12/15/16/17/18;
   6 hits on shared tables: SCR-02/07/10/13/14/19 at 0.1-0.4 s)
   93 case calls = 103 s (every call 1.0-1.2 s)
   TOTAL 541 s = 9.0 min   (old MoE: 25.2 min at 75/93; previous 93/93 run:
                            24-35 min of compute with LAN resets)
 Cold prefill at 30% battery: SCR-11 6217 tok / 65.9 s = 94 tok/s; SCR-01
   2574 tok / 26.5 s = 97 tok/s  => this GPU's real ceiling is ~95-100 tok/s
   (the 84-87 seen at 25-30% earlier and 63 at 5-16% were throttled).
 Floor for this suite = ~40.8k cold tokens / 95 + 93 x 1 s ~= 8.7 min. We are
 within ~5% of the hardware floor. Nothing software can take from here except
 fewer tokens (compact encoding, queued) or hardware.

## J2: WARM RE-RUN OF choice_v2 (23:27-23:37) = 93/93 again, but 9.4 min, NOT faster
 First prime of the re-run logged "cache hit total=2574 matched=152 cached=152":
 J1's snapshots were gone although the model never reloaded (no server events
 in the 74-min gap). Eviction is purely size-based: maxPagedOutBytes = 8 GiB
 (compile-time, prefix_cache.go) — evict oldest, then deepest, then largest.
 A 93-case / 8-table run exceeds it, and re-running in the same order is the
 LRU worst case (each cold table evicts the next one you need). Peak runner
 memory during the run: 27.8 GiB (model 18) — consistent with the cap being hit.
 => Within a run: everything hits. Across runs: only working sets that fit in
    8 GiB of snapshots persist. Production events (seen once) are unaffected;
    benchmark re-runs pay the 8 cold tables again (~4 min). No disk cache in
    Ollama; mlx-lm's disk cache would only matter for repeated benchmark runs.

## THIRD-ORDER FINDING (from J1/J2 logs): family-level priming still re-prefills
## a table when a SECOND family uses the same table with a different Known-Driver
 J2 SCR-12 prime: "cache hit total=6182 matched=6172 cached=152 left=6030" — the
 trie held SCR-11's path (6172 tokens matched) but the branch point (before the
 Known-Driver line) had no snapshot -> full re-prefill. 6 such pairs in the
 suite (13 cold primes for 8 tables).
 FIX: prime at TABLE level — prefix up to and including "TARGET FOR THIS CALL:\n"
 (8 distinct prefixes = the 8 tables). Cold tokens 40.8k -> 22.9k => projected
 ~5.8 min for the whole suite (from 9.0). Implemented in both shadow harness
 copies (_prime_key/_prime_table), re-prepared (dense cases sha unchanged
 19fe0382b26f4a72). Queued as J8 (cv2_tableprime) after J4/J3.
 General rule: prime the LONGEST prefix shared by the LARGEST group of upcoming
 calls (the document), not the per-question group.

## J4: num_ctx COST (00:28-00:33, battery 30-26%, same fresh 6.26k-token prompt, interleaved)
   num_ctx=16384 : 93.6, 98.0 tok/s cold prefill
   num_ctx=32768 : 97.1, 98.0 tok/s
 => NO measurable prefill cost for 32k vs 16k on the MLX engine (the earlier
    "32k slower" reading was throttling noise). load=0.0 s on the 32k requests
    and `ollama ps` kept context_length=16384: the MLX runner did NOT reload
    for the larger per-request num_ctx (KV grows dynamically). Whether it then
    ACCEPTS a >16k-token prompt is tested by the whole-exhibit decode probe (J7).
    Resident size unchanged (~29.4 GB).

## POWER (00:12): idle charging had collapsed to 142 mA (~1.6 W net) because the
 display never sleeps (pmset displaysleep 0) and WindowServer + an animated
 aerial wallpaper + a DisplayLink external display + app helpers ate the 30 W.
 `pmset displaysleepnow` (transient, any keypress wakes it) -> 1,781 mA (~20 W
 into the battery), 12x faster recharge. Owner suggestion: set a display-sleep
 timeout on AC; and a >=70 W adapter.

## *** VICTORY #9: COMPACT ENCODING + TABLE-LEVEL PRIMING = 93/93 IN 5.3 MIN ***
 2026-08-17 00:41-00:46, cold trie, battery 30->26%.
   93/93, precision 1.0, recall 1.0, 0 transport failures, one pass.
   8 primes (one per table) = 199 s ; 93 case calls = 117 s ; TOTAL 316 s = 5.3 min
   prime prefill s: 24.2 21.6 12.3 10.7 53.8 9.0 8.8 53.3
 Progression at 100% accuracy: 9.0 min (dense, family priming) -> 5.3 min
 (compact -16.7% tokens, table priming). Old MoE model: 25.2 min at 75/93.
 Compact encoding = no 2-space indent + one `cols` legend; VERIFIED 93/93,
 adopt it. Harness: table_evidence/choice_v2_compact (cases sha c4565c09675db3bf).

## CHECKPOINT 00:50 — still running unattended in queue 2 (battery-gated):
   J8 dense+table-priming run (expect ~5.8 min), J6 qf01 table-first+primed
   (19 calls), J7 whole-exhibit decode/ctx probe (13.5k and 23.4k tokens at
   num_ctx 32768). Logs: scratchpad/gpu_queue2.log*, /tmp/qwen38_scratch/s2/*.log
   on the Minisforum; results in the shadow harness dirs.
