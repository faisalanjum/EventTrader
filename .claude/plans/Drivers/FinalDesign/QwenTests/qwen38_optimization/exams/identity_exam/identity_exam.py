#!/usr/bin/env python3
"""EXP-0 identity-judge exam on the LOCAL Qwen model, in ORIGINAL form.

- Key: K-pairs.v1.3.jsonl (sha verified against the lock) — 160 pairs, gold SAME/DIFFERENT.
- Prompt: harness/grader_prompt_framing.txt (the pinned section-6 contract), byte-exact,
  with <<SIDE_A>>/<<SIDE_B>> = JS-style compact JSON of each side and <<PAIR_ID>>.
- Call: config.local_llm.generate() RAW — no system message, no added instruction,
  think=False, temperature=0, format=VERDICT_SCHEMA (ignored by the MLX engine,
  enforced by the GGUF engine), retries=0. Raw reply saved BEFORE parsing.
- Scoring (same definitions as harness/scorers/score_exp0.py):
    wrong_same     = verdict SAME   where gold DIFFERENT   (denominator 110)
    false_refusal  = verdict DIFFERENT where gold SAME     (denominator 50)
    invalid        = no strict-valid verdict                (denominator 160)
    gate: wrong_same == 0 and false_refusal <= 0.10 and invalid_rate <= 0.02
  STRICT validity = the whole reply parses as one JSON object with exactly the schema
  keys and verdict in {SAME, DIFFERENT}. LENIENT = same after stripping code fences /
  surrounding prose (reported separately: format-only failures).
- Resumable: appends to raw_results.jsonl, skips done pair_ids.
Usage: identity_exam.py run [--model qwen3.8:27b-mlx] | score
"""
import argparse, hashlib, json, os, re, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("LOCAL_LLM_HOST", "http://127.0.0.1:11434")
import local_llm as L  # the same client as config/local_llm.py

KEY = os.path.join(HERE, "K-pairs.v1.3.jsonl")
LOCK = os.path.join(HERE, "K-pairs.v1.3.lock.json")
FRAMING = os.path.join(HERE, "grader_prompt_framing.txt")
VERDICT_SCHEMA = {"type": "object", "additionalProperties": False,
                  "required": ["pair_id", "verdict", "cited_a", "cited_b", "reason"],
                  "properties": {"pair_id": {"type": "string"},
                                 "verdict": {"type": "string", "enum": ["SAME", "DIFFERENT"]},
                                 "cited_a": {"type": "string"}, "cited_b": {"type": "string"},
                                 "reason": {"type": "string"}}}
KEYS = {"pair_id", "verdict", "cited_a", "cited_b", "reason"}

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def load_pairs():
    lock = json.load(open(LOCK))
    assert sha(KEY) == lock["sha256"], "K-pairs sha mismatch vs lock"
    return [json.loads(l) for l in open(KEY, encoding="utf-8")]

def js_json(o):  # JSON.stringify(): compact, insertion order, no ASCII escaping
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))

def build_prompt(p, framing):
    return (framing.replace("<<SIDE_A>>", js_json(p["side_a"]))
                   .replace("<<SIDE_B>>", js_json(p["side_b"]))
                   .replace("<<PAIR_ID>>", p["pair_id"]))

def strict_parse(txt):
    try:
        o = json.loads(txt)
    except Exception:
        return None
    if not isinstance(o, dict) or set(o) != KEYS or o.get("verdict") not in ("SAME", "DIFFERENT"):
        return None
    return o

def lenient_parse(txt):
    t = txt.strip()
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(o, dict) or o.get("verdict") not in ("SAME", "DIFFERENT"):
        return None
    return o

def battery():
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    m = re.search(r"(\d+)%", out); return int(m.group(1)) if m else -1

def run(args):
    pairs = load_pairs()
    framing = open(FRAMING, encoding="utf-8").read()
    L.MODEL = args.model
    outdir = os.path.join(HERE, "results_" + args.model.replace(":", "_").replace("/", "_"))
    os.makedirs(outdir, exist_ok=True)
    raw_path = os.path.join(outdir, "raw_results.jsonl")
    done = set()
    if os.path.exists(raw_path):
        for l in open(raw_path, encoding="utf-8"):
            r = json.loads(l)
            if r.get("completed_response"):
                done.add(r["pair_id"])
    meta = {"key_sha256": sha(KEY), "framing_sha256": sha(FRAMING), "model": args.model,
            "n_pairs": len(pairs), "think": False, "temperature": 0.0, "num_ctx": args.num_ctx,
            "max_tokens": args.max_tokens, "system": None, "added_instructions": False,
            "format_passed": True, "client": "config/local_llm.py generate()"}
    json.dump(meta, open(os.path.join(outdir, "manifest.json"), "w"), indent=2)
    print(f"model={args.model} pairs={len(pairs)} done={len(done)} batt={battery()}%", flush=True)
    processed = 0
    with open(raw_path, "a", encoding="utf-8") as fh:
        for i, p in enumerate(pairs, 1):
            if p["pair_id"] in done:
                continue
            if args.limit and processed >= args.limit:
                print(f"LIMIT {args.limit} reached; {len(pairs)-len(done)-processed} pending", flush=True); return
            processed += 1
            if battery() >= 0 and battery() <= args.stop_batt:
                print(f"PAUSE: battery {battery()}% <= {args.stop_batt}%", flush=True)
                sys.exit(75)  # resumable pause
            prompt = build_prompt(p, framing)
            t0 = time.monotonic()
            rec = {"pair_id": p["pair_id"], "gold": p["gold"], "family": p["family"], "hard": p.get("hard"),
                   "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
            try:
                txt, st = L.generate(prompt, system=None, format=VERDICT_SCHEMA, think=False,
                                     temperature=0.0, num_ctx=args.num_ctx, max_tokens=args.max_tokens,
                                     timeout=900, retries=0, allow_truncation=False, with_stats=True)
                rec.update({"completed_response": True, "raw_output": txt,
                            "stats": {k: st.get(k) for k in ("prompt_eval_count", "eval_count", "total_s",
                                                             "done_reason", "truncated_output")}})
                so, lo = strict_parse(txt), lenient_parse(txt)
                rec["strict_valid"] = so is not None
                rec["verdict_strict"] = so["verdict"] if so else None
                rec["verdict_lenient"] = lo["verdict"] if lo else None
                v = so or lo or {}
                qa = "".join(p["side_a"].get("quotes") or []); qb = "".join(p["side_b"].get("quotes") or [])
                rec["cited_a_verbatim"] = bool(v.get("cited_a")) and v.get("cited_a") in qa
                rec["cited_b_verbatim"] = bool(v.get("cited_b")) and v.get("cited_b") in qb
            except Exception as e:  # transport failure -> not completed, will be re-asked on resume
                rec.update({"completed_response": False, "raw_output": None, "error": f"{type(e).__name__}: {e}"})
            rec["wall_s"] = round(time.monotonic() - t0, 3)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
            print(f"[{i}/{len(pairs)}] {p['pair_id']} gold={p['gold']:9s} strict={rec.get('verdict_strict')} "
                  f"lenient={rec.get('verdict_lenient')} {rec['wall_s']}s batt={battery()}%", flush=True)
            if not rec["completed_response"]:
                print("transport failure; rerun to resume", flush=True); sys.exit(2)
    print("ALL DONE", flush=True)

def score(args):
    pairs = {p["pair_id"]: p for p in load_pairs()}
    outdir = os.path.join(HERE, "results_" + args.model.replace(":", "_").replace("/", "_"))
    rows = [json.loads(l) for l in open(os.path.join(outdir, "raw_results.jsonl"), encoding="utf-8")]
    rows = {r["pair_id"]: r for r in rows if r.get("completed_response")}
    def metrics(mode):
        m = {"n": 0, "wrong_same": 0, "false_refusal": 0, "invalid": 0, "correct": 0,
             "n_SAME": 0, "n_DIFFERENT": 0, "by_family": {}, "hard": {"n": 0, "wrong_same": 0, "false_refusal": 0, "invalid": 0}}
        for pid, p in pairs.items():
            r = rows.get(pid); v = (r or {}).get("verdict_" + mode)
            m["n"] += 1; m["n_" + p["gold"]] += 1
            fam = m["by_family"].setdefault(p["family"], {"n": 0, "wrong_same": 0, "false_refusal": 0, "invalid": 0})
            fam["n"] += 1
            if p.get("hard"): m["hard"]["n"] += 1
            if v is None:
                m["invalid"] += 1; fam["invalid"] += 1
                if p.get("hard"): m["hard"]["invalid"] += 1
            elif v == p["gold"]:
                m["correct"] += 1
            elif v == "SAME":
                m["wrong_same"] += 1; fam["wrong_same"] += 1
                if p.get("hard"): m["hard"]["wrong_same"] += 1
            else:
                m["false_refusal"] += 1; fam["false_refusal"] += 1
                if p.get("hard"): m["hard"]["false_refusal"] += 1
        m["wrong_same_rate"] = round(m["wrong_same"] / m["n_DIFFERENT"], 4)
        m["false_refusal_rate"] = round(m["false_refusal"] / m["n_SAME"], 4)
        m["invalid_rate"] = round(m["invalid"] / m["n"], 4)
        m["gate_pass"] = (m["wrong_same"] == 0 and m["false_refusal_rate"] <= 0.10 and m["invalid_rate"] <= 0.02)
        return m
    walls = [r["wall_s"] for r in rows.values()]
    out = {"model": args.model, "completed": len(rows), "strict": metrics("strict"), "lenient": metrics("lenient"),
           "citations_verbatim_both": sum(1 for r in rows.values() if r.get("cited_a_verbatim") and r.get("cited_b_verbatim")),
           "wall_total_s": round(sum(walls), 1), "wall_mean_s": round(sum(walls) / max(len(walls), 1), 2),
           "sonnet_baseline": {"g_sonnet_a": {"wrong_same": 0, "false_refusal": 0, "invalid": 0},
                               "g_sonnet_b": {"wrong_same": 0, "false_refusal": 1, "invalid": 0},
                               "g_opus": {"wrong_same": 0, "false_refusal": 0, "invalid": 0}}}
    json.dump(out, open(os.path.join(outdir, "score.json"), "w"), indent=2)
    s, l = out["strict"], out["lenient"]
    print(f"model={args.model} completed={len(rows)}/160 wall={out['wall_total_s']}s mean={out['wall_mean_s']}s")
    print(f"STRICT : wrong_same={s['wrong_same']}/110 false_refusal={s['false_refusal']}/50 invalid={s['invalid']}/160 correct={s['correct']} gate_pass={s['gate_pass']}")
    print(f"LENIENT: wrong_same={l['wrong_same']}/110 false_refusal={l['false_refusal']}/50 invalid={l['invalid']}/160 correct={l['correct']} gate_pass={l['gate_pass']}")
    print(f"hard subset (n={s['hard']['n']}): strict wrong_same={s['hard']['wrong_same']} false_refusal={s['hard']['false_refusal']} invalid={s['hard']['invalid']}")
    print("citations verbatim on both sides:", out["citations_verbatim_both"])
    fails = [(pid, p["gold"], rows[pid].get("verdict_strict"), rows[pid].get("verdict_lenient")) for pid, p in pairs.items()
             if pid in rows and rows[pid].get("verdict_lenient") != p["gold"]]
    print("mismatches (pair, gold, strict, lenient):", fails[:40])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "score"])
    ap.add_argument("--model", default="qwen3.8:27b-mlx"); ap.add_argument("--num-ctx", type=int, default=16384)
    ap.add_argument("--max-tokens", type=int, default=400); ap.add_argument("--stop-batt", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(); (run if a.cmd == "run" else score)(a)
