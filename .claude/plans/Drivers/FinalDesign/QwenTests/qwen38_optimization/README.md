# qwen38_optimization — Qwen3.8-27B local inference: 100% accuracy + speed work

**Implementing agents: read `QWEN_INFERENCE_GUIDE.md` first — it is the complete usage contract.**

Self-contained record of the Qwen3.8 (qwen3.8:27b-mlx, Ollama MLX engine on the
M4 Pro MacBook, consumed from the Minisforum over the autossh tunnel) optimisation
work. Nothing in here is imported by production code. The ONLY production files
touched by this work are:

    config/local_llm.py                          (inference client — committed alongside)
    ~/Library/LaunchAgents/com.faanjum.ollama.plist  (Mac server; copy in server/)

## Results (all three suites, precision 1.0)
    choice_v2  93/93   (old qwen3.6:35b-a3b: 75/93)
    row_v3     93/93   (old: 93/93)
    qf01       19/19   (old: 17/19 NOT_SAFE_FOR_TASK)
Development sets with opened answers => strong signal, NOT certification.

## Layout
    notes/RUNBOOK.md            the verified recipe — READ THIS FIRST
    notes/HANDOFF.md            state summary
    notes/INVESTIGATION_LOG.md  every measurement, dead end and correction, in order
    harness/choice_v2/          patched harness (dense encoding + occurrence labels +
                                prompt reorder + byte-vs-token budget fix), the exact
                                cases.jsonl used, and result sets:
                                  results_QWEN38_93of93/  results_MLX_89of93/
                                  results_OLD_qwen36/     results_GGUF_partial/
                                *.diff_vs_original = exact delta vs the owner harness
    harness/row_v3/             unchanged harness + 93/93 results (+ old-model results)
    harness/qf01/               NUM_CTX/model edits + 19/19 results (+ July control)
    client/                     original local_llm.py (2026-07-24) + diff to current
    server/                     live launchd plist + the two pre-change backups
    scripts/autoresume.sh       transport-retry driver for long runs
    scripts/experiments/        every isolated experiment script (prefill, prefix
                                cache, env A/B, ctx A/B, mlx-lm bench, ...)

## Where experiments run
    /tmp/qwen38_bench/EventMarketDB   6 GB shadow copy of the repo on the Minisforum.
    All harness runs happen there; the real repo is never executed against.
    (Older notes say /tmp/qwen38_bench — the tree root is one level deeper.)

## Server / client knobs that matter (details in notes/RUNBOOK.md)
    OLLAMA_NUM_PARALLEL=1   OLLAMA_LOAD_TIMEOUT=30m   OLLAMA_KEEP_ALIVE=-1
    num_ctx=16384  workers=1  max_tokens=512  system msg + fence strip (MLX has no
    grammar enforcement)  shared table FIRST / per-call target LAST (prefix cache)
