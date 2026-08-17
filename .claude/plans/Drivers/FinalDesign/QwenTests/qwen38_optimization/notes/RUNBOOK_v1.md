# Qwen3.8-27B on M4 Pro — verified 100% setup

Result: choice_v2 93/93, row_v3 93/93, qf01 19/19 — all precision 1.0.
(Development sets with opened answers: strong signal, NOT certification.)

## 1. Ollama server settings (already applied to the launchd plist)
    OLLAMA_HOST=0.0.0.0:11434
    OLLAMA_NUM_PARALLEL=1        # >1 makes prompt-cache checkpoints slot-local
                                 # (llama.cpp #22942) AND multiplies KV memory
    OLLAMA_LOAD_TIMEOUT=30m      # default 5m ABORTS any prefill over ~300s
    OLLAMA_KEEP_ALIVE=-1         # cache dies with the model
    OLLAMA_MAX_LOADED_MODELS=1
Apply with bootout+bootstrap, NOT `launchctl kickstart -k`
(kickstart silently does NOT reload EnvironmentVariables):
    launchctl bootout   gui/$UID/com.faanjum.ollama
    launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.faanjum.ollama.plist

## 2. Model
    qwen3.8:27b-mlx   (nvfp4, MLX engine — Ollama's recommended Apple build)
    NOT 27b-mtp-q4_K_M: MTP is an NVIDIA-Blackwell optimisation, useless here,
    and it decodes 4x slower for identical accuracy.

## 3. Client (config/local_llm.py) — patched copy in this directory
  a. stream internally and reassemble (keeps the socket active)
  b. _input_budget for MLX tracks num_ctx (was a hardcoded 200_000 that
     silently disabled the truncation guard)
  c. structured() appends an explicit JSON instruction on the MLX path
     (MLX does NOT grammar-enforce `format`)
  d. TCP keepalive (SO_KEEPALIVE, KEEPIDLE/INTVL 30, KEEPCNT 60 — must be <=127)

## 4. Prompt construction — THE BIG ONE (40x)
  a. SHARED CONTENT FIRST, per-call target LAST.
     Ollama's prefix cache matches byte-for-byte from position 0.
     Before: target at char 144 -> shared prefix 0.8%
     After : target at the end  -> shared prefix 99.2%
  b. LABEL THE OCCURRENCE: emit `choice 22: occurrence #1 ...`.
     The model is reliable at judgement, unreliable at ordinal counting.
  c. DENSE ENCODING: `22|1|2,289|4Q24` with one `cols:` header line.
     46% fewer tokens across all 93 prompts. Prefill is LINEAR in tokens, so
     this also speeds up brand-new documents that caching cannot help.
  !! Prompts are baked into cases.jsonl at prepare() time.
     After ANY _prompt() change you MUST rm cases.jsonl manifest.json and
     re-run `prepare`, or the change has no effect.

## 5. Run settings
    num_ctx=16384   max_tokens=512   workers=1   timeout=1800   temp=0
    system message: "You are a JSON API. ... Your entire response must parse
    as JSON."  (required: MLX has no grammar enforcement)
    strip ``` fences before json.loads (MLX sometimes wraps output)

## 6. Long runs: use autoresume.sh (in this directory)
    Something on the LAN reaps client connections at ~320s during long cold
    prefills. The SERVER completes and CACHES the work anyway (log shows
    "200 in 5m19s" while the client saw ECONNRESET), so each resume lands on
    a warm cache. Converged 81 -> 93 in TWO passes.

## 7. Known-open
  - 30W adapter on a machine that ships with 140W. Does NOT affect burst
    speed (decode 27-31 tok/s regardless) but degrades SUSTAINED runs up to
    3.5x as the battery drains. Get the 140W adapter for batch work.
  - QF-01 gold key is stale: the post-July inline_html.py nbsp fix
    invalidated it. qf01 cannot be scored against it by ANY model until the
    key is regenerated or the grader is made nbsp-insensitive.
