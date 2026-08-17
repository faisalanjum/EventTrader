# QWEN3.8 OPTIMIZATION — STATE HANDOFF (2026-08-16)

## OUTCOME: 100% accuracy on all three suites
    choice_v2  93/93  precision 1.0   (was 75/93 on old qwen3.6)
    row_v3     93/93  precision 1.0   (3.8 min clean single pass)
    qf01       19/19  precision 1.0   (was 17/19 NOT_SAFE_FOR_TASK)
Development sets with OPENED answers => strong signal, NOT certification.

## MODEL IN USE
qwen3.8:27b-mlx  (nvfp4, dense 27.8B, Ollama's --mlx-engine). 18 GB.
Also installed: qwen3.8:27b-mtp-q4_K_M (GGUF) — tested, do not use.
qwen3.6:35b-a3b and :35b-mlx were DELETED by owner (never met accuracy bar).

## RATES (measured, on a THROTTLED 30W supply — treat as lower bounds)
    prefill cold  ~63-85 tok/s     <-- 99% of every call (outputs are 6-8 tok)
    decode        ~29 tok/s        (old model was 76.7)
    cached doc    0.5-2s total

## CHANGES APPLIED — PRODUCTION (owner-approved)
1. ~/Library/LaunchAgents/com.faanjum.ollama.plist
     OLLAMA_NUM_PARALLEL 4 -> 1        (slot-local cache bug, llama.cpp #22942)
     OLLAMA_LOAD_TIMEOUT  added = 30m  (default 5m aborted every long prefill)
   MUST apply via bootout+bootstrap; `launchctl kickstart -k` does NOT reload env.
   Backups: /tmp/plist_before_numparallel.plist, /tmp/plist_before_loadtimeout.plist
2. /home/faisal/EventMarketDB/config/local_llm.py  (5 timestamped .bak files)
     - _post streams internally and reassembles
     - _input_budget for MLX tracks num_ctx (was hardcoded 200_000)
     - structured() appends JSON instruction on MLX path
     - TCP keepalive (_KeepAliveConnection/_OPENER)
     - default MODEL -> qwen3.8:27b-mlx

## OWNER'S REAL REPO: OTHERWISE UNTOUCHED
Verified: 0 tracked files modified. QwenTests MODEL_NAME still qwen3.6,
cases.jsonl sha 4c1a9083e56c467e, inline_html.py sha 66b25fa2488d1b75.
All experiment work lives in /tmp/qwen38_bench (6 GB shadow copy).

## CHECKPOINT (survives everything): /home/faisal/qwen38_WORKING_CHECKPOINT/
    RUNBOOK.md            <- the full verified recipe, read this first
    choice_v2_100pct/     <- 93/93 results + manifest + patched harness
    row_v3/               <- 93/93 results
    local_llm_PATCHED.py
    autoresume.sh

## THE FOUR THINGS THAT MATTERED (in order)
1. PROMPT ORDER: shared content FIRST, per-call target LAST.
   Was: target at char 144 ahead of 17k shared chars -> prefix match 0.8%.
   Now: 99.2%. Worth 40x on repeated questions against one document.
2. OCCURRENCE LABELS: emit `choice 22: occurrence #1 ...`.
   Model is reliable at judgement, unreliable at ordinal counting.
   Fixed 3 of 4 remaining accuracy failures.
3. DENSE ENCODING: `22|1|2,289|4Q24` + one `cols:` header line.
   46% fewer tokens. Prefill is LINEAR so this also helps NEW documents.
4. AUTO-RESUME for long runs (autoresume.sh). Something on the LAN reaps
   client connections at ~320s; the SERVER completes and caches anyway
   ("200 in 5m19s" while client saw ECONNRESET), so retries converge fast.

## PROCESS LESSONS (each cost hours)
- _prompt() edits do NOTHING until you rm cases.jsonl manifest.json and re-run
  `prepare` — prompts are baked in at prepare time.
- config/local_llm.py edits do NOTHING for the harness: the shadow tree has its
  OWN copy and the harness imports from ROOT=shadow. Sync the copy.
- ALWAYS verify the artifact the run actually reads.
- Throttling gives 3.1x variance on identical work; control test ORDER or the
  measurement is worthless.

## RULED OUT WITH EVIDENCE (do not re-chase)
    native mlx-lm       1.35x, not the advertised 3-5x; needs client rewrite
    GGUF                identical wrong answers; weakness is the MODEL
    num_ctx=8192        3.1x variance on identical config; unmeasurable
    8-bit / mxfp8       slower; 4-bit already 100%
    mlx-dspark          accelerates decode; decode is 1% of cost
    row pruning         lossy; risks the 100% bar
    FLASH_ATTENTION /   measured irrelevant at both 16k and 32k
      KV_CACHE_TYPE

## GENUINELY LEFT UNDONE
1. mlx-lm DISK-PERSISTENT prompt cache (mlx_lm.cache_prompt /
   --prompt-cache-dir). THE remaining answer to the fresh-document case:
   pay a document's prefill once EVER, across runs. I rejected mlx-lm on
   speed and never tested its actual unique feature. <-- best next move
   Weights already downloaded: mlx-community/Qwen3.8-27B-4bit (~21 GB in
   ~/.cache/huggingface). mlx-lm installed in scratchpad/mlxenv.
2. Re-test OLLAMA_NUM_PARALLEL > 1 now that num_ctx=16384 removed the memory
   pressure — might add throughput.
3. Newer Ollama than 0.32.13 (release notes mention cache improvements).
4. Full 93-case GGUF accuracy run — I generalised from only 2 cases.
5. Batching concurrent requests.
6. Clean choice_v2 wall-time — BLOCKED: needs the 140W adapter.

## HARDWARE ISSUE (owner's action)
Mac16,8 = MacBook Pro 16" M4 Pro, ships with 140W. Currently on a genuine
Apple "30W USB-C Power Adapter". Battery sat at 5-16% all session.
Does NOT affect burst speed (decode 27-31 tok/s regardless).
DOES degrade sustained runs up to 3.5x as the battery drains
(SCR-11-q1 85.1s vs SCR-12-q1 295.5s — identical prompt sizes).

## PRE-EXISTING BUG IN OWNER'S REPO (not ours, still open)
QF-01 gold key is STALE. The post-July inline_html.py nbsp fix (commit
7ddc85b0) changed table parsing, invalidating the July answer key. Proven by
re-scoring the owner's OWN July results today — they fail too. qf01 cannot be
scored by ANY model until the key is regenerated or the grader is made
nbsp-insensitive. Workaround used here: restored the frozen July parser
(commit 964bb4e6) into the shadow only.
