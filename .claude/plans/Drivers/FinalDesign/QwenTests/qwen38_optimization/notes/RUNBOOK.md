# Qwen3.8-27B on the M4 Pro MacBook — verified fastest 100%-accurate setup (v2, 2026-08-16)

Result so far: choice_v2 93/93, row_v3 93/93, qf01 19/19 — all precision 1.0
(development sets with opened answers: strong signal, NOT certification).
Everything below is measured on THIS machine; numbers elsewhere will differ.

## 0. The physics (read this first)

    cost of one call  ~=  prompt_tokens / PREFILL_RATE  +  output_tokens / DECODE_RATE
    PREFILL_RATE (cold, brand-new text) = 84-87 tok/s   <- the GPU ceiling, see §6
    DECODE_RATE                          = ~29 tok/s     (MTP speculative decoding already on)
    cached prefix                        = ~4000-8000 tok/s (i.e. effectively free)

So a document is expensive exactly ONCE. Every design and setting below exists to
(a) never pay for the same text twice, (b) send fewer tokens, (c) never lose a
finished computation to a timeout, reload, or reset.

## 1. Server (Mac, launchd `~/Library/LaunchAgents/com.faanjum.ollama.plist`, live)

    OLLAMA_HOST=0.0.0.0:11434
    OLLAMA_NUM_PARALLEL=1        # the MLX runner keeps ONE active cache path; a 2nd
                                 # concurrent request with a different prefix pages the
                                 # trie out/in on every switch. Prefill is compute-bound
                                 # anyway, so parallelism adds no throughput.
    OLLAMA_LOAD_TIMEOUT=30m      # default 5m aborts any prefill over ~300 s
    OLLAMA_KEEP_ALIVE=-1         # the prefix cache lives exactly as long as the model
    OLLAMA_MAX_LOADED_MODELS=1
    (FLASH_ATTENTION / KV_CACHE_TYPE are ignored by the MLX engine — harmless)
Apply with bootout+bootstrap; `launchctl kickstart -k` does NOT reload env vars.
Ollama 0.32.13, model `qwen3.8:27b-mlx` (nvfp4, MLX engine). Do not "upgrade" casually:
0.32.14 changes Qwen system-message handling — re-verify §4 priming and the 93/93 after.

## 2. Client (`config/local_llm.py`, committed) — env knobs

    LOCAL_LLM_MODEL    qwen3.8:27b-mlx
    LOCAL_LLM_NUM_CTX  32768 default   (see §5 for per-role values; FIXED per run)
    LOCAL_LLM_TIMEOUT  1800  seconds   (was a hardcoded 300 -> aborted real calls)
    LOCAL_LLM_THINK    0               (renderer default is reasoning ON at "xhigh"!
                                        the client always passes think=false)
    LOCAL_LLM_HOST     override the mDNS/IP host list
Behaviour: streams and reassembles; TCP keepalive; MLX path appends an explicit
"Return JSON only" instruction (MLX does not grammar-enforce `format`); strips fences.

## 3. Prompt layout (the 40x): shared text FIRST, per-call text LAST, byte-identical

Ollama reuses a KV prefix only when the bytes match from position 0. Instructions
+ document first, then the item/anchor/question. Any changing token (ids, dates,
nonces) placed early destroys reuse for everything after it.

## 4. Prefix PRIMING (the 2x on every repeated document) — NEW

Why: the MLX runner (x/mlxrunner/prefix_cache.go) creates a branch-point snapshot only
DURING THE SECOND request that diverges there, and qwen3.8's recurrent layers cannot
be rewound, so the first two calls on a document are BOTH cold. Its automatic
snapshot at `len(prompt)-4` (pipeline.go) is the way in: send the shared prefix ALONE
first, and the very next call restores there.

    import config.local_llm as L
    # K >= 2 upcoming calls share `prefix` byte-for-byte with the same system text:
    L.prime(prefix, system=SYSTEM_MESSAGE, num_ctx=NUM_CTX)      # one cold prefill
    # or, given the batch of prompts over one document:
    L.prime_for(prompts, system=SYSTEM_MESSAGE, num_ctx=NUM_CTX) # computes the prefix
Measured (6.2k-token table): control q1 79.3 s, q2 74.4 s, q3 1.5 s = 155 s;
primed PRIME 72.3 s, q1 2.9 s, q2 1.9 s, q3 1.2 s = 78 s; identical answers.
Rules: same model, same system text, same num_ctx as the real calls (a num_ctx change
reloads the model and drops the whole cache); prefix must start at the beginning of
the user content and end on a line boundary. Priming a cached prefix is nearly free.
Which roles: reader per item (same event parts), Fiscal locator per anchor (same
table), concept picker per company (same menu). Not: catalog reader (each chunk once),
identity judge (unique inputs).

## 5. num_ctx per role (measured on the real 7 filings of the test set)

    role                          input size (tokens)      num_ctx
    table locator (dense encoding) 1.2k - 6.5k              16384
    catalog reader chunk           40,000 chars ~ 11-13k     16384 (32768 if output is long)
    reader, one whole 8-K EX-99.1  10.7k - 23.4k as TEXT     32768
    reader, multi-exhibit event    > 24k                     65536
Never send raw HTML: the same exhibits are 120k-490k tokens as HTML (10-20x).
Cost preview at 85 tok/s: 13.5k-token exhibit = 160 s cold; 23.4k = 275 s cold.
Memory: 16384 -> ~29.4 GB resident (of 37.4 GiB Metal budget); larger contexts cost
KV memory — measure before choosing 65536 (the earlier 35 GB thrash came from
num_ctx 65536 x 4 parallel slots).

## 6. Engine bake-off (why MLX, why nothing faster exists here)

    Ollama MLX (nvfp4)      cold prefill 84-87 tok/s   decode ~29 tok/s (MTP, acceptance 1.0 on JSON)
    llama.cpp b10450 Metal  pp6144      81.6 tok/s     tg 9.8-10.1 tok/s (no MTP)
    mlx-lm 0.31.3 (4-bit)   ~84-88 tok/s               (needs client rewrite; no gain)
    llama.cpp Apple-Silicon table, M4 Pro 16-core: 7B Q4_0 pp512 = 364 t/s -> x(6.7/27.8) = ~88
Dense 27.8B prefill on a 16-core M4 Pro GPU is compute-bound at ~85 tok/s. Faster new-
document prefill = fewer tokens (§7) or faster hardware (M4 Max ~2x; M5-class much
more: llama.cpp logs "tensor API disabled for pre-M5 devices").

## 7. Fewer tokens (the only software lever left for a first-ever document)

Qwen's tokenizer splits every digit; separators and indentation are whole tokens.
    verbose choice lines -> dense `22|1|2,289|4Q24`     -46% tokens  (93/93 verified)
    dense -> compact (no 2-space indent, one `cols` legend) -16.7%    (verification run
                                                              queued: choice_v2_compact)
Any prompt change is a new prompt: re-run the full suite before adopting.

## 8. Reliability
    LOAD_TIMEOUT 30m (server) · TIMEOUT 1800 (client) · keepalive · scripts/autoresume.sh
    (the LAN reaps idle connections at ~320 s; the server finishes and caches anyway,
    so a resume lands on warm cache).

## 9. Power (owner action) — the biggest practical bottleneck for BATCH runs
Machine: Mac16,8 = 14-inch MacBook Pro, M4 Pro 12-core CPU / 16-core GPU, 48 GB.
Ships with a 70W USB-C adapter (96W optional). Connected: 30W (a MacBook Air charger).
Under GPU load: -2%/min; idle: +0.25%/min. Bursts are full speed above ~15%; long
runs drain and then throttle (up to 3.5x). A 70W+ adapter removes this entirely.

## 10. Where things are
    real repo (committed):   config/local_llm.py ; .claude/plans/Drivers/FinalDesign/QwenTests/qwen38_optimization/
    experiments (shadow):    /tmp/qwen38_bench/EventMarketDB/...  (never the real tree)
    checkpoint:              /home/faisal/qwen38_WORKING_CHECKPOINT/
