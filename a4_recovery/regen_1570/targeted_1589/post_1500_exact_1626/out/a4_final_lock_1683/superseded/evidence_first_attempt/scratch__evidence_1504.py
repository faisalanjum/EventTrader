# ponytail: ONE read-only helper the SEQ 1314 claims re-run; every number here is measured, never typed.
import collections, glob, hashlib, io, json, os, re, sys
RUN = "/tmp/a4_final_targeted_corr_run_1504"
W = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
MAN = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/"
       ".claude/plans/Drivers/experiments/kfields_key_a4/final_targeted_corr_1503/final_targeted_correction.manifest.json")
J = lambda p: json.load(io.open(p, encoding="utf-8"))
fsha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def wfs():
    return [f.split(".")[0] for f in J(RUN + "/finalization.json")["harvested_raw"]]


def states():
    return [J(p) for p in J(RUN + "/receipt.json")["states"]]


def trans():
    h = hashlib.sha256(); n = 0
    for wf in wfs():
        for p in sorted(glob.glob("%s/subagents/workflows/%s/*" % (W, wf))):
            h.update(("%s/%s\n" % (wf, os.path.basename(p))).encode()); h.update(fsha(p).encode()); n += 1
    return h.hexdigest(), n


def state_tree():
    h = hashlib.sha256()
    for p in J(RUN + "/receipt.json")["states"]:
        h.update(fsha(p).encode())
    return h.hexdigest()


def serial():
    st = states(); ok = 0; gaps = []
    for a, b in zip(st, st[1:]):
        gap = (b["startTime"] - a["startTime"] - a["durationMs"]) / 1000.0
        gaps.append(gap); ok += gap > 0
    return "%d/%d gaps positive, smallest %.1f s" % (ok, len(st) - 1, min(gaps))


def models():
    c = collections.Counter(); reads = 0; tools = 0; tok = []
    for wf, st in zip(wfs(), states()):
        tools += st["totalToolCalls"]; tok.append(st["totalTokens"])
        c["state_default:" + st["defaultModel"]] += 1
        c["result:" + st["result"]["model"]] += 1; c["agentType:" + st["result"]["agentType"]] += 1
        c["effort:" + st["result"]["effort"]] += 1
        for mp in glob.glob("%s/subagents/workflows/%s/agent-*.meta.json" % (W, wf)):
            c["meta:" + J(mp)["model"]] += 1
        for tp in glob.glob("%s/subagents/workflows/%s/agent-*.jsonl" % (W, wf)):
            for line in io.open(tp, encoding="utf-8"):
                for m in re.findall(r'"model":\s*"([^"]+)"', line):
                    c["transcript:" + m] += 1
                if re.search(r'"name":\s*"Read"', line):
                    reads += 1
    return c, tools, reads, tok


def parse(p):
    t = io.open(p, encoding="utf-8").read().strip()
    t = re.sub(r"^```(?:json)?\s*", "", t); t = re.sub(r"\s*```$", "", t)
    return json.loads(t)


def pairs():
    tasks = {t["task_id"]: t["members"][0] for t in J(MAN)["tasks"]}
    by = collections.defaultdict(dict)
    for p in sorted(glob.glob(RUN + "/raw/hrt-*.proved.json")):
        m = re.match(r"(hrt-\d+)_b(\d)", os.path.basename(p)); by[m.group(1)][int(m.group(2))] = parse(p)
    out = []
    for tid in sorted(by):
        a, b = by[tid][1], by[tid][2]
        out.append((tid, tasks[tid], a, b))
    return out


def _short(v):
    s = json.dumps(v, sort_keys=True)
    return s if len(s) <= 60 else s[:57] + "..."


def deltas(a, b):
    """Every field that differs between two readings, names excluded; level/comparison
    dicts collapse to their wording when value and scale agree. Recognises, never decides."""
    out = []
    for i in range(max(len(a["facts"]), len(b["facts"]))):
        fa = a["facts"][i]["item"] if i < len(a["facts"]) else None
        fb = b["facts"][i]["item"] if i < len(b["facts"]) else None
        if fa is None or fb is None:
            continue
        wording = []
        for k in sorted(set(fa) | set(fb)):
            if k == "driver_name" or fa.get(k) == fb.get(k):
                continue
            x, y = fa.get(k), fb.get(k)
            if isinstance(x, dict) and isinstance(y, dict) and \
                    {q: v for q, v in x.items() if q != "unit_scale_evidence"} == {q: v for q, v in y.items() if q != "unit_scale_evidence"}:
                wording.append((x.get("unit_scale_evidence"), y.get("unit_scale_evidence")))
                continue
            out.append("fact%d %s b1=%s b2=%s" % (i, k, _short(x), _short(y)))
        if wording:
            out.insert(0, "fact%d unit_scale_evidence wording %s vs %s" % (i, json.dumps(wording[0][0]), json.dumps(wording[0][1])))
    return out


def rows():
    lines = []; agree = differ = abst = numeric = 0; hints = 0
    for tid, pid, a, b in pairs():
        hints += len(a.get("continuity_hints", [])) + len(b.get("continuity_hints", []))
        n1 = [f["item"].get("driver_name") for f in a["facts"]]; n2 = [f["item"].get("driver_name") for f in b["facts"]]
        ab1 = a.get("abstentions", []); ab2 = b.get("abstentions", [])
        d = deltas(a, b)
        numeric += sum(1 for x in d if re.search(r"(level|comparison)_(low|high) b1=", x) or "change_value b1=" in x and "b2=null" not in x)
        if ab1 or ab2:
            abst += 1; verdict = "ABSTENTION vs valid"
        elif n1 == n2:
            agree += 1; verdict = "AGREE on name"
        else:
            differ += 1; verdict = "DIFFER on name"
        b1 = ("ABSTAINED - " + ab1[0].get("reason", json.dumps(ab1[0]))) if ab1 else " | ".join(n1)
        b2 = ("ABSTAINED - " + ab2[0].get("reason", json.dumps(ab2[0]))) if ab2 else " | ".join(n2)
        extra = ("; " + "; ".join(d)) if d else "; every field identical"
        lines.append("   %s %s: b1 %s :: b2 %s :: %s%s" % (tid, pid, b1, b2, verdict, extra))
    return "\n".join(lines), agree, differ, abst, numeric, hints


if __name__ == "__main__" and sys.argv[1] not in ("events", "run_ids"):
    cmd = sys.argv[1]
    if cmd == "trans": print(trans()[0])
    elif cmd == "transn": print(trans()[1])
    elif cmd == "states": print(state_tree())
    elif cmd == "serial": print(serial())
    elif cmd == "tokens": print(sum(models()[3]))
    elif cmd == "tokmin": print(min(models()[3]))
    elif cmd == "tokmax": print(max(models()[3]))
    elif cmd == "tools": print(models()[1])
    elif cmd == "reads": print(models()[2])
    elif cmd == "mid": print(models()[0]["transcript:claude-sonnet-5"])
    elif cmd == "modelset": print(json.dumps(sorted(models()[0].items())))
    elif cmd == "agree": print(rows()[1])
    elif cmd == "differ": print(rows()[2])
    elif cmd == "abst": print(rows()[3])
    elif cmd == "numeric": print(rows()[4])
    elif cmd == "hints": print(rows()[5])
    elif cmd == "completed": print(sum(1 for s in states() if s["status"] == "completed"))
    else: raise SystemExit("unknown " + cmd)


def events():
    """Per event (mechanical parse of the proved shard text, never a judgment):
    rows, facts, abstentions, exclusions, open issues, leads agreeing/disagreeing."""
    out = []
    for p in sorted(glob.glob(RUN + "/raw/*.attempt1.proved.json")):
        d = parse(p); sid = d["source_id"]
        facts = sum(len(r["settled"]["facts"]) for r in d["rows"]); abst = sum(len(r["settled"]["abstentions"]) for r in d["rows"])
        excl = sum(1 for r in d["rows"] if r["final_outcome"] != "fact")
        agree = sum(1 for l in d["lead_reconciliation"] if l["agrees"] is True); dis = sum(1 for l in d["lead_reconciliation"] if l["agrees"] is False)
        out.append("   %s  rows %d  facts %d  abstentions %d  non-fact rows %d  open_issues %d  leads agree %d / disagree %d"
                   % (sid, len(d["rows"]), facts, abst, excl, len(d["open_issues"]), agree, dis))
    return "\n".join(out)


def run_ids():
    return "\n".join("   %s  %s" % (os.path.splitext(os.path.basename(s))[0], (lambda d: [r for r in d["workflowProgress"] if r.get("type") == "workflow_agent"][0]["label"])(J(s))) for s in J(RUN + "/receipt.json")["states"])


if __name__ == "__main__" and sys.argv[1] in ("events", "run_ids"):
    print(events() if sys.argv[1] == "events" else run_ids())
