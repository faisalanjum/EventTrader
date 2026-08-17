# HANDOFF v3 — Qwen3.8 local inference program (2026-08-17 ~15:30)

## State (all pushed; latest commit f96fe27b on origin/main)
- Only two repo paths ever committed by me: config/local_llm.py and
  .claude/plans/Drivers/FinalDesign/QwenTests/qwen38_optimization/. Owner's tree is very dirty (900+); never stage anything else.
- Owner's own copy of the guide: .claude/plans/Drivers/FinalDesign/LeftOverSteps/QwenInference.md — I overwrite its
  CONTENT with the canonical QWEN_INFERENCE_GUIDE.md when asked, but never git-add it (his area).
- Production: qwen3.8:27b-mlx resident on the Mac (Ollama 0.32.13, NUM_PARALLEL=1, LOAD_TIMEOUT=30m, KEEP_ALIVE=-1),
  tunnel to Minisforum OK. Mac now on a 61 W adapter (was 30 W); display sleep helps charging.

## Results so far (all in the guide §5, §13, §15, §15a)
- Table lanes: choice_v2 93/93 in 5.3 min (compact encoding + table-level priming), row_v3 93/93, qf01 19/19 in 3.4 min.
- Identity judge (K-pairs v1.3, 160): 0 wrong-SAME, 2 false refusals, 1 invalid (cap artifact) — gate PASS; GGUF schema-enforced needed;
  MLX raw prompt -> prose/invalid. 28 s/pair.
- Reader (EXP-2 proxy, first 10 of 40 chunks, 296 gold): strict recall Qwen 50.0% vs Sonnet 45.3% vs Opus 52.4%; 2/10 chunks empty;
  compliance: shape/name-syntax 100%, quotes verbatim 98%, quotes 60-200 chars only 74%. GGUF grammar + reasoning OFF was the only working
  mode (MLX no-reason -> [], reasoning -> runaway).
- Cold prefill ~95-110 tok/s = GPU ceiling (llama.cpp 81.6, mlx-lm 84-88); decode 22-29 MLX / 7-10 GGUF; 25k-token practical ceiling
  (0.24 MB/token runner memory); num_ctx 16k vs 32k free.

## Optional next (owner decides): full 40-chunk reader run (~4.5 h GPU); reader precision needs a grader; other roles have no locked keys.
## Scratchpad locations: identity_exam/, reader_exam/, qwen38_investigation.md, QWEN_INFERENCE_GUIDE.md (canonical source).
