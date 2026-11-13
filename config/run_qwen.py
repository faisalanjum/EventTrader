#!/usr/bin/env python3
# =============================================================================
# GENERIC QWEN RUNNER  —  sends each case to the local Qwen model, records output
# =============================================================================
# This is pure inference plumbing. It knows NOTHING about any test, answer key,
# scoring, or naming rule. Cases in -> model outputs out. The calling bot owns
# what a "case" means and how to score the result.
#
# -----------------------------------------------------------------------------
# I/O CONTRACT
# -----------------------------------------------------------------------------
# INPUT  : a JSONL file, one CASE per line:
#   {
#     "id":       "unique-stable-string",     # REQUIRED (used for resume + join)
#     "prompt":   "the user message",         # REQUIRED
#     "system":   "system message",           # optional
#     "schema":   { ...JSON Schema... },       # optional -> output is a parsed dict,
#                                              #   grammar-enforced to the schema
#     "max_tokens": 4096,                      # optional (see constraints below)
#     "think":    false,                       # optional (default false; true = slow)
#     "temperature": 0.0                       # optional (default 0.0 = deterministic)
#   }
#
# OUTPUT : a JSONL file, one RESULT per line (same id):
#   {
#     "id": "...",
#     "ok": true,                              # false if the call/parse failed
#     "output": <string | dict | null>,        # dict when a schema was given, else text
#     "error": null,                            # error string when ok=false
#     "stats": { "tok_s", "eval_count", "prompt_eval_count", "done_reason",
#                "truncated_input", "truncated_output", "total_s", "wall_s",
#                "host", "model" }
#   }
#
# USAGE
#   python3 run_qwen.py cases.jsonl -o results.jsonl --workers 4
#   # Resumable: re-running only fills ids missing from results.jsonl.
#   # Importable: from run_qwen import run_cases; run_cases([{...}, ...])
#
# =============================================================================
# CONSTRAINTS THE CALLING BOT MUST RESPECT
# NOTE 2026-11-12: config/local_llm.py now defaults to qwen3.8:27b-fast at
#   localhost:11435 (JSON enforced, reads the full input, about 2-6x faster).
#   Older model: LOCAL_LLM_MODEL=qwen3.8:27b-mlx. Items 1, 3, 4 and 9 below
#   describe the old qwen3.6 setup. Current runbook:
#   .claude/plans/Drivers/FinalDesign/LeftOverSteps/QwenInference.md
#
# =============================================================================
# 1. INPUT SIZE BUDGET = ~16,000 tokens per case (num_ctx 32768 / 2).
#    The GGUF backend gives the prompt only HALF of num_ctx and silently drops
#    the FRONT beyond that. The client DETECTS this and returns ok=false with
#    error "TruncatedInputError" — it will NOT silently corrupt. If your cases
#    exceed ~16k tokens (prompt + system), tell Faisal the real max and he raises
#    num_ctx (one constant). Rough guide: ~16k tokens ≈ 55–60k characters.
#
# 2. DO NOT VARY num_ctx PER CASE. Changing num_ctx forces an ~8s model RELOAD.
#    num_ctx is fixed batch-wide (default 32768, or --num-ctx). Keep it constant.
#
# 3. ONE MODEL PER BATCH. Only one model fits in VRAM; switching models costs an
#    8–14s reload. Default is qwen3.6:35b-a3b (GGUF) because it GRAMMAR-ENFORCES
#    JSON schema. Override batch-wide with --model / LOCAL_LLM_MODEL, never mid-run.
#      - qwen3.6:35b-a3b (GGUF): schema-enforced JSON, ~51 tok/s   <- default
#      - qwen3.6:35b-mlx (MLX) : ~69 tok/s but JSON is NOT enforced (avoid for schema)
#
# 4. THROUGHPUT ≈ 50 tok/s AGGREGATE, regardless of --workers. The single GPU is
#    memory-bandwidth-saturated by one stream, so concurrency does NOT multiply
#    throughput — it only prevents idle gaps. --workers 4 is the sweet spot
#    (matches server slots); more just queue. Estimate wall time as
#    (total OUTPUT tokens across all cases) / ~50.
#
# 5. OUTPUT LENGTH. If you set max_tokens and the model hits it, the result has
#    stats.truncated_output=true and done_reason="length" (ok stays true — it was
#    your cap). If you DON'T set max_tokens and it runs into the context limit,
#    the case fails loud (TruncatedOutputError). Set max_tokens to bound cost;
#    make it comfortably larger than any expected output.
#
# 6. DETERMINISM. temperature=0 (default) is byte-identical across runs — safe to
#    cache/score reproducibly. Set temperature>0 only if you deliberately want
#    variation (and then determinism/resume-identity no longer hold).
#
# 7. IDs MUST BE UNIQUE AND STABLE. Resume and result-join both key on "id".
#
# 8. THE MODEL IS QUANTIZED (4-bit). It is reliable for extraction, selection,
#    classification and copying, but do NOT rely on it for exact arithmetic —
#    compute numbers downstream, not in the model. (Task-level note; the runner
#    does not enforce this.)
#
# 9. SERVER AVAILABILITY. Inference runs on Faisal's Mac (mDNS
#    CA-K429CXLGF9.local, IP fallback). The Mac is set to never idle-sleep, and
#    the server auto-restarts on crash. If the Mac is off/asleep/off-LAN, cases
#    fail with a ConnectionError (ok=false) — they are resumable once it's back.
# =============================================================================
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, "/home/faisal/EventMarketDB")
from config import local_llm as L  # noqa: E402

# per-case keys that may override defaults (NOTE: num_ctx is intentionally NOT here)
_CASE_KW = ("max_tokens", "think", "temperature", "timeout")
_write_lock = threading.Lock()


def run_case(case: dict, num_ctx: int) -> dict:
    cid = case.get("id")
    t0 = time.monotonic()
    if not case.get("prompt"):
        return {"id": cid, "ok": False, "output": None,
                "error": "case has no 'prompt'", "stats": {}}
    kw = {k: case[k] for k in _CASE_KW if k in case}
    kw["num_ctx"] = num_ctx
    schema = case.get("schema")
    try:
        if schema:
            obj, stats = L.structured(case["prompt"], schema, case.get("system"),
                                      with_stats=True, **kw)
            output, ok, err = obj, True, None
        else:
            text, stats = L.generate(case["prompt"], case.get("system"),
                                     with_stats=True, **kw)
            output, ok, err = text, True, None
    except Exception as e:  # noqa: BLE001
        return {"id": cid, "ok": False, "output": None,
                "error": f"{type(e).__name__}: {e}",
                "stats": {"wall_s": round(time.monotonic() - t0, 2)}}
    stats["wall_s"] = round(time.monotonic() - t0, 2)
    return {"id": cid, "ok": ok, "output": output, "error": err, "stats": stats}


def run_cases(cases: list[dict], workers: int = 4, num_ctx: int | None = None,
              out_path: str | None = None, done_ids: set | None = None) -> list[dict]:
    num_ctx = num_ctx or L.NUM_CTX
    done_ids = done_ids or set()
    pending = [c for c in cases if c.get("id") not in done_ids]
    results = []
    fh = open(out_path, "a", encoding="utf-8") if out_path else None
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_case, c, num_ctx): c for c in pending}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            results.append(rec)
            if fh:
                with _write_lock:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
            s = rec.get("stats", {})
            print(f"[{i}/{len(pending)}] id={rec['id']} ok={rec['ok']} "
                  f"{('err='+rec['error'][:50]) if not rec['ok'] else ''}"
                  f"{s.get('wall_s','?')}s {s.get('tok_s','')}t/s", flush=True)
    if fh:
        fh.close()
    return results


def _load_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Generic local-Qwen batch runner")
    ap.add_argument("cases", help="input JSONL of cases")
    ap.add_argument("-o", "--out", required=True, help="output JSONL of results")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--model", help="override LOCAL_LLM_MODEL for this batch")
    ap.add_argument("--num-ctx", type=int, default=None,
                    help="fixed context size for the batch (default 32768)")
    args = ap.parse_args()

    if args.model:
        L.MODEL = args.model
    num_ctx = args.num_ctx or L.NUM_CTX

    cases = _load_jsonl(args.cases)
    done = set()
    if Path(args.out).exists():
        done = {r.get("id") for r in _load_jsonl(args.out)}

    h = L.health()
    print(f"model={L.MODEL}  num_ctx={num_ctx}  input_budget≈{num_ctx//2 if 'mlx' not in L.MODEL else '262k'} tok"
          f"  host={h.get('host')}  resident={h.get('loaded')}")
    print(f"cases={len(cases)}  already_done={len(done)}  workers={args.workers}")
    if L.MODEL not in (h.get("loaded") or []):
        print("NOTE: target model not resident yet; first call loads it (~8s).")

    t0 = time.time()
    res = run_cases(cases, workers=args.workers, num_ctx=num_ctx,
                    out_path=args.out, done_ids=done)

    n_ok = sum(r["ok"] for r in res)
    trunc = sum(r["stats"].get("truncated_output") is True for r in res)
    errs = {}
    for r in res:
        if not r["ok"]:
            key = (r["error"] or "").split(":")[0]
            errs[key] = errs.get(key, 0) + 1
    toks = sum(r["stats"].get("eval_count", 0) for r in res)
    print("=" * 60)
    print(f"done: {n_ok}/{len(res)} ok  | failures={errs or 'none'}  | "
          f"output-capped={trunc}")
    print(f"wall={time.time()-t0:.1f}s  output_tokens={toks}  "
          f"agg={toks/max(time.time()-t0,1):.0f} tok/s  -> {args.out}")
    return 0 if n_ok == len(res) else 1


if __name__ == "__main__":
    raise SystemExit(main())
