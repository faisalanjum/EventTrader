"""XBRL concept-link test C1, OpenAI model on the FRESH TEST set (12 companies): gpt-6-luna at reasoning xhigh through `codex exec` on the ChatGPT subscription only (OPENAI_API_KEY removed from the environment).
Same inputs and same production pick/verify prompt text as the Haiku arm (scratchpad c1t_hk_<T>.json = menu lines "qname|label" + the 29 names). One call per company for the pick, then one per company for the verify.
Outputs: scratchpad c1t_{TAG}_pick_<T>.json, c1t_{TAG}_verres_<T>.json, luna_log.json (seconds per call). Usage: python3 run_luna_c1.py [pick|verify]"""
import json, subprocess, sys, time, os, re, concurrent.futures as cf
D = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
MODEL = "gpt-6-luna"; EFFORT = os.environ.get("EFFORT", "xhigh"); TAG = "luna" if EFFORT == "xhigh" else "luna" + EFFORT   # file tag: luna (xhigh), lunalow, lunamedium, lunahigh
M = json.load(open("c1_test_menus.json"))["companies"]; TS = sorted(M)
PICK = ("You are a precise XBRL concept matcher. Company {t}.\nRead exactly one file: {f} . Do not open, list or search any other file or folder, do not use the web, and run no other commands. "
        "It has `menu` (the ONLY allowed answers, each line \"qname|label\") and `names` (metrics).\nFor EACH metric in `names`, independently (one answer per metric, do not let one metric's answer influence another):\n"
        "Pick the ONE menu qname that IS exactly this metric (the same accounting line a filer tags), or null.\n"
        "SAME metric only — a related-but-different line is NOT a match (cost-of-revenue≠revenue; income-tax≠net-income; a subtotal≠the total; basic≠diluted). Two equal candidates → higher usage.\n"
        "Output ONLY a JSON list, nothing else, one object per metric: {{\"name\": \"<metric name exactly as given>\", \"qname\": \"us-gaap:...\" or null}}. The qname must be copied exactly from the menu. Include all {n} metrics.")
VER = ("You are a STRICT XBRL link auditor — default to refuted when unsure (a wrong link is the cardinal sin). Company {t}.\nRead exactly one file: {f} . Do not open, list or search any other file or folder, do not use the web, and run no other commands. "
       "It has `proposals`, each {{\"name\": metric, \"qname\": proposed concept, \"label\": its label}}.\nFor EACH proposal, independently: Proposed: metric \"<name>\" -> <qname> (label: \"<label>\"). "
       "Refute if the concept is a related-but-different line, a different value (GAAP vs non-GAAP, gross vs net, subtotal vs total), the wrong statement, or a dimension instead of the consolidated line.\n"
       "Output ONLY a JSON list, nothing else, one object per proposal: {{\"name\": \"<name exactly as given>\", \"real\": true or false}}. Include every proposal exactly once.")
def run(prompt, out):
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    t0 = time.time(); p = subprocess.run(["codex", "exec", "-m", MODEL, "-c", f"model_reasoning_effort={EFFORT}", "-s", "read-only", "--skip-git-repo-check", "--ephemeral", "-o", out, prompt],
                                         capture_output=True, text=True, timeout=1500, env=env, cwd="/tmp")
    tok = re.findall(r"tokens used\s*\n\s*([\d,]+)", p.stdout + p.stderr); return round(time.time() - t0), (tok[-1] if tok else None)
def parse(path):
    s = open(path).read(); i, j = s.find("["), s.rfind("]"); return json.loads(s[i:j + 1])
def pick(t):
    out = f"{D}/c1t_{TAG}_pick_{t}.raw"; sec, tok = run(PICK.format(t=t, f=f"{D}/c1t_hk_{t}.json", n=29), out)
    json.dump(parse(out), open(f"{D}/c1t_{TAG}_pick_{t}.json", "w")); return t, sec, tok
def verify(t):
    valid = {c["q"]: c for c in M[t]["concepts"]}; rows = json.load(open(f"{D}/c1t_{TAG}_pick_{t}.json")); props = []
    for r in rows:
        q = r.get("qname")
        if q in valid: props.append({"name": r["name"], "qname": q, "label": valid[q]["label"]})
    json.dump({"company": t, "proposals": props}, open(f"{D}/c1t_{TAG}_ver_{t}.json", "w"))
    out = f"{D}/c1t_{TAG}_verres_{t}.raw"; sec, tok = run(VER.format(t=t, f=f"{D}/c1t_{TAG}_ver_{t}.json"), out)
    json.dump(parse(out), open(f"{D}/c1t_{TAG}_verres_{t}.json", "w")); return t, sec, tok
if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "pick"; fn = pick if step == "pick" else verify; log = {}
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn, t): t for t in TS}
        for f in cf.as_completed(futs):
            t = futs[f]
            try: _, sec, tok = f.result(); log[t] = (sec, tok); print(step, t, f"{sec}s", "tokens", tok, flush=True)
            except Exception as e: log[t] = str(e)[:150]; print(step, t, "FAILED", str(e)[:150], flush=True)
    json.dump(log, open(f"{D}/{TAG}_log_{step}.json", "w"))
