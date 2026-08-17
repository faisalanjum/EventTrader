#!/usr/bin/env python3
"""EXP-2 blind driver-name READER exam on the local Qwen model — faithful single-prompt proxy.

Original (2026-07-11): tool-using agents loaded RULES_full.txt + one 40k-char chunk, extracted
candidate causes, and wrote {"chunk_id","candidates":[{proposed_name, quote, evidence, per_x,
slice_note}]}. Qwen has no tools, so ONE assembled prompt carries the same preamble, the same
rulebook text (sha b33ab08b…), the same chunk JSON, the same STEP-3 extraction rules and the same
output shape. Scoring here is STRICT and deterministic (the official EXP-2 metric used Sonnet
graders): per gold row (K-reader v3, sha cf87a09a…):
  name_hit  = a candidate proposed_name equals the gold name or an acceptable alt name
  quote_hit = a candidate quote and the gold quote overlap (one contains the other after
              whitespace/case normalisation, or a common substring >= 40 chars)
  either    = name_hit or quote_hit
The SAME scorer runs over Sonnet's and Opus's saved responses on the same chunks, so the
comparison is like-for-like. Precision cannot be judged deterministically (needs graders);
candidate counts and quote-verbatim rates are reported instead.
Usage: reader_exam.py run [--n 10] [--model qwen3.8:27b-mlx] | score [--n 10]
"""
import argparse, hashlib, json, os, re, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("LOCAL_LLM_HOST", "http://127.0.0.1:11434")
import local_llm as L
EXP = os.path.join(HERE, "exp2_reader/runs/2026-07-11T19-40-47Z_exp2/local_artifacts")
RULES = os.path.join(EXP, "RULES_full.txt"); IDS = os.path.join(EXP, "ids_40k.json")
CHUNKS = os.path.join(HERE, "fixtures/frozen_restaurants/chunks")
KEY = os.path.join(HERE, "keys/K-reader/K-reader.v3.jsonl")
SCHEMA = {"type":"object","additionalProperties":False,"required":["chunk_id","candidates"],"properties":{"chunk_id":{"type":"string"},"candidates":{"type":"array","items":{"type":"object","additionalProperties":False,"required":["proposed_name","quote","evidence","per_x","slice_note"],"properties":{"proposed_name":{"type":"string"},"quote":{"type":"string"},"evidence":{"type":"object","additionalProperties":False,"required":["company","source_type","source_id","date"],"properties":{"company":{"type":"string"},"source_type":{"type":"string"},"source_id":{"type":"string"},"date":{"type":"string"}}},"per_x":{"type":["string","null"]},"slice_note":{"type":["string","null"]}}}}}}
SYSTEM = ("You are a JSON API. You emit exactly one JSON object and nothing else. Never write "
          "analysis, reasoning, explanation, or markdown. Your entire response must parse as JSON.")

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

def build_prompt(chunk_id):
    rules = open(RULES, encoding="utf-8").read()
    chunk_txt = open(os.path.join(CHUNKS, chunk_id), encoding="utf-8").read()
    return (
"You are a BLIND driver-name reader for a financial knowledge graph. You see ONLY this chunk's real "
"content plus the naming rulebook. You have no catalog, no answer key, no other chunks.\n\n"
"RULEBOOK (NAME-01..19 + OD rules; these are your ONLY naming authority - follow them exactly):\n"
"<<<RULEBOOK\n" + rules + "\nRULEBOOK>>>\n\n"
"CHUNK (JSON: {chunk_id, ticker, events:[{content, date, source_id, source_type, ...}]}; the events' "
"content fields are your source text - read ALL of them fully):\n"
"<<<CHUNK\n" + chunk_txt + "\nCHUNK>>>\n\n"
"TASK - extract: from this chunk only, identify every ADMISSIBLE reusable cause per the rulebook "
"(NAME-18 gate: reusable class, source-grounded, unambiguous, cause-only noun; vague text -> skip; own "
"measured company parts -> that is slice territory, keep the part OUT of the name and note it in "
"slice_note). For each cause emit one candidate:\n"
"- proposed_name: the canonical lower_snake_case name per the rulebook\n"
"- quote: a VERBATIM substring copied exactly from one event's content (60-200 chars) that grounds the cause\n"
"- evidence: {company: \"<ticker>\", source_type, source_id, date} of the event the quote came from\n"
"- per_x: the per-X denominator if the rules put one in the name, else null\n"
"- slice_note: if the quote measures an own company part (segment/geography/product/customer/channel/"
"entity_ownership), note it briefly, else null\n"
"Do not invent causes not stated in the text. Do not pad: quality over count.\n\n"
"OUTPUT - return EXACTLY this JSON shape and nothing else:\n"
'{"chunk_id": "<chunk_id>", "candidates": [{"proposed_name": "...", "quote": "...", "evidence": '
'{"company": "...", "source_type": "...", "source_id": "...", "date": "..."}, "per_x": null, "slice_note": null}, ...]}')

def parse(txt):
    t = txt.strip()
    strict = None
    try:
        o = json.loads(t); strict = o if isinstance(o, dict) and isinstance(o.get("candidates"), list) else None
    except Exception:
        pass
    if strict is not None:
        return strict, True
    t2 = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    m = re.search(r"\{.*\}", t2, re.S)
    if m:
        try:
            o = json.loads(m.group(0))
            if isinstance(o, dict) and isinstance(o.get("candidates"), list):
                return o, False
        except Exception:
            pass
    return None, False

def battery():
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    m = re.search(r"(\d+)%", out); return int(m.group(1)) if m else -1

def run(a):
    ids = json.load(open(IDS))[: a.n]
    L.MODEL = a.model
    outdir = os.path.join(HERE, "results_" + a.model.replace(":", "_") + ("_think" if a.think else "")); os.makedirs(outdir, exist_ok=True)
    done = {f[:-5] for f in os.listdir(outdir) if f.endswith(".json") and f != "manifest.json"}
    json.dump({"model": a.model, "rules_sha256": sha(RULES), "key_sha256": sha(KEY), "system": SYSTEM,
               "think": bool(a.think), "mode": a.mode, "temperature": 0.0, "num_ctx": a.num_ctx, "max_tokens": a.max_tokens,
               "chunks": ids, "assembled_single_prompt": True},
              open(os.path.join(outdir, "manifest.json"), "w"), indent=2)
    print(f"model={a.model} chunks={len(ids)} done={len(done)} batt={battery()}%", flush=True)
    for i, cid in enumerate(ids, 1):
        base = cid[:-5]
        if base in done:
            continue
        if battery() >= 0 and battery() <= a.stop_batt:
            print(f"PAUSE battery {battery()}%", flush=True); sys.exit(75)
        prompt = build_prompt(cid); t0 = time.monotonic()
        rec = {"chunk_id": base, "prompt_chars": len(prompt), "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
        try:
            grammar = a.mode == "grammar"   # GGUF runner enforces SCHEMA; no system message, raw prompt
            txt, st = L.generate(prompt, system=None if grammar else SYSTEM, format=SCHEMA if grammar else None,
                                 think=bool(a.think), temperature=0.0, num_ctx=a.num_ctx,
                                 max_tokens=a.max_tokens, timeout=1800, retries=0, allow_truncation=False, with_stats=True)
            obj, strict = parse(txt)
            rec.update({"completed_response": True, "raw_output": txt, "strict_json": strict,
                        "parsed": obj, "n_candidates": len(obj["candidates"]) if obj else None,
                        "stats": {k: st.get(k) for k in ("prompt_eval_count", "eval_count", "total_s", "done_reason", "truncated_output")}})
        except Exception as e:
            rec.update({"completed_response": False, "raw_output": None, "error": f"{type(e).__name__}: {e}"})
        rec["wall_s"] = round(time.monotonic() - t0, 1)
        json.dump(rec, open(os.path.join(outdir, base + ".json"), "w"), ensure_ascii=False, indent=1)
        s = rec.get("stats") or {}
        print(f"[{i}/{len(ids)}] {base} ok={rec['completed_response']} strict={rec.get('strict_json')} "
              f"cands={rec.get('n_candidates')} prompt_tok={s.get('prompt_eval_count')} out_tok={s.get('eval_count')} "
              f"done={s.get('done_reason')} {rec['wall_s']}s batt={battery()}%", flush=True)
        if not rec["completed_response"]:
            print("transport failure; rerun to resume", flush=True); sys.exit(2)
    print("ALL DONE", flush=True)

def norm(s): return re.sub(r"\s+", " ", (s or "")).strip().lower()

def lcs_len(a, b):
    # longest common substring length (small strings; O(n*m) fine)
    if not a or not b: return 0
    prev = [0] * (len(b) + 1); best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i-1] == b[j-1]:
                cur[j] = prev[j-1] + 1
                if cur[j] > best: best = cur[j]
        prev = cur
    return best

def quote_hit(cq, gq):
    cq, gq = norm(cq), norm(gq)
    if not cq or not gq: return False
    if cq in gq or gq in cq: return True
    return lcs_len(cq, gq) >= 40

def load_candidates(model, base):
    if model.startswith("qwen"):
        p = os.path.join(HERE, "results_" + model.replace(":", "_") + "_think", base + ".json")
        if not os.path.exists(p): p = os.path.join(HERE, "results_" + model.replace(":", "_"), base + ".json")
        if not os.path.exists(p): return None
        r = json.load(open(p)); return (r.get("parsed") or {}).get("candidates") if r.get("parsed") else []
    p = os.path.join(EXP, "responses", model, base + ".json")
    if not os.path.exists(p): return None
    try:
        return json.load(open(p, encoding="utf-8-sig")).get("candidates") or []
    except Exception:
        return []

def score(a):
    ids = json.load(open(IDS))[: a.n]
    gold = [json.loads(l) for l in open(KEY, encoding="utf-8")]
    models = [a.model, "sonnet_40k_1", "opus_40k_1"]
    out = {}
    for m in models:
        tot = {"gold": 0, "name_hit": 0, "quote_hit": 0, "either": 0, "candidates": 0, "chunks": 0,
               "quote_verbatim": 0, "name_wellformed": 0, "hard_gold": 0, "hard_either": 0}
        for cid in ids:
            base = cid[:-5]; cands = load_candidates(m, base)
            if cands is None: continue
            tot["chunks"] += 1; tot["candidates"] += len(cands)
            content = " ".join(e["content"] for e in json.load(open(os.path.join(CHUNKS, cid)))["events"])
            ncontent = norm(content)
            for c in cands:
                if norm(c.get("quote")) and norm(c.get("quote")) in ncontent: tot["quote_verbatim"] += 1
                if re.fullmatch(r"[a-z][a-z0-9_]*", c.get("proposed_name") or ""): tot["name_wellformed"] += 1
            for g in (x for x in gold if x["chunk_ref"]["file"] == cid):
                tot["gold"] += 1
                names = {g["gold_cause"]["proposed_name"], *(g["gold_cause"].get("acceptable_alt_names") or [])}
                nh = any((c.get("proposed_name") or "") in names for c in cands)
                qh = any(quote_hit(c.get("quote"), g["evidence_locator"]["quote"]) for c in cands)
                tot["name_hit"] += nh; tot["quote_hit"] += qh; tot["either"] += (nh or qh)
                if g.get("hard"): tot["hard_gold"] += 1; tot["hard_either"] += (nh or qh)
        if tot["gold"]:
            tot["name_recall"] = round(tot["name_hit"] / tot["gold"], 4)
            tot["quote_recall"] = round(tot["quote_hit"] / tot["gold"], 4)
            tot["either_recall"] = round(tot["either"] / tot["gold"], 4)
            tot["hard_either_recall"] = round(tot["hard_either"] / max(tot["hard_gold"], 1), 4)
            tot["quote_verbatim_rate"] = round(tot["quote_verbatim"] / max(tot["candidates"], 1), 4)
        out[m] = tot
    json.dump(out, open(os.path.join(HERE, f"score_first{a.n}.json"), "w"), indent=2)
    print(f"{'model':16s} {'chunks':>6s} {'gold':>5s} {'name_recall':>11s} {'quote_recall':>12s} {'either':>7s} {'hard_either':>11s} {'cands':>6s} {'verbatim':>8s}")
    for m, t in out.items():
        print(f"{m:16s} {t['chunks']:6d} {t['gold']:5d} {t.get('name_recall',0):11.3f} {t.get('quote_recall',0):12.3f} "
              f"{t.get('either_recall',0):7.3f} {t.get('hard_either_recall',0):11.3f} {t['candidates']:6d} {t.get('quote_verbatim_rate',0):8.3f}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "score"])
    ap.add_argument("--n", type=int, default=10); ap.add_argument("--model", default="qwen3.8:27b-mlx")
    ap.add_argument("--num-ctx", type=int, default=32768); ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--stop-batt", type=int, default=8); ap.add_argument("--think", type=int, default=1)
    ap.add_argument("--mode", choices=["system", "grammar"], default="system")
    a = ap.parse_args(); (run if a.cmd == "run" else score)(a)
