# -*- coding: utf-8 -*-
"""RECOVERY ADAPTER for /tmp/a4_hard_review_run_1495 (Codex SEQ 1608). NOT an owner. Zero model calls.

In a fresh private world: (1) the committed run-1491 world through its own adapter, with the hard-review-era owners
(a6_launch_freeze 8f2d0999, build_kfields_hard_review_targeted 936ef4a2, both final pre-call test files) placed over
the committed harness copies BEFORE the historical import route, every one derived mechanically from recorded
payloads (derive_hr_1495.py) and pinned; (2) the targeted run 1491 replayed to its exact binding; (3) RED: the
hard-review door refused while its budget receipt and package are absent; (4) the restoration Codex SEQ 1612 bounds:
the recovered 1492 receipt placed and the exact 1493 receipt reconstructed from it by the deterministic transform
(reconstruct_receipt_1493.py) with the world's own binding, then the package through the exact owner - the retired
ledger is never walked and the four historical budget scripts (derived/, provenance) are never placed or run;
(5) the 22 pinned official states projected at their exact paths; (6) the exact lifecycle prepare_run (the owner
writes the 22 launchers) -> record_state x22 in call order -> finalize; (7) every identity checked and exported."""
import collections, hashlib, io, json, os, shutil, subprocess, sys, glob

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
HOME = os.environ["HR_1495_HOME"]
R1491 = os.path.dirname(HOME) + "/targeted_run_1491"
P1 = os.path.dirname(HOME) + "/phase1_targeted_1488"
os.environ.setdefault("RUN_1491_HOME", R1491); os.environ.setdefault("PHASE1_1488_HOME", P1)
OUTROOT = HOME + "/out/attempt10"
PINS = json.load(io.open(HOME + "/pins_1608.json", encoding="utf-8"))
RUN = PINS["run_dir"]
SESS = "/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
SRC_ROOT = HOME + "/inputs/session_store/projects"
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
OPENED = set()
QUIET = ("/home/faisal/EventMarketDB/venv", "/usr", "/lib", "/etc", "/proc", "/dev", "/sys")


def _audit(event, args):
    if event == "open" and isinstance(args[0], str) and (args[1] is None or "r" in str(args[1])) and not args[0].startswith(QUIET):
        OPENED.add(args[0])


sys.addaudithook(_audit)
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: io.open(p, "rb").read()


def _tsv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write("".join("\t".join(str(c) for c in r) + "\n" for r in rows))


def derived():
    rows = {}
    for l in io.open(HOME + "/derived/DERIVATION.tsv", encoding="utf-8").read().splitlines()[1:]:
        f, step, ln, ts, n, h, b = l.split("\t"); rows[f] = h                # the last row per file is its final identity
    return rows


def place_hr_owners(A):
    """The hard-review-era owners and tests over the committed harness copies, each pinned to its derived identity."""
    want = {"a6_launch_freeze.py": PINS["a6_owner"], "build_kfields_hard_review_targeted.py": PINS["hard_review_targeted_owner"],
            "test_a4_targeted_accounting_1492.py": PINS["test_accounting"], "test_a4_hard_review_targeted_1492.py": PINS["test_hard_review"]}
    fin = derived(); rows = []
    for name, pin in want.items():
        b = read(HOME + "/derived/" + name)
        if sha(b) != pin or fin.get(name) != pin:
            raise RuntimeError("derived %s is not the pinned identity" % name)
        dst = A.H + "/" + name; before = sha(read(dst)) if os.path.exists(dst) else None
        io.open(dst, "wb").write(b); rows.append(("harness_g1v3/%s (era owner, displaced %s)" % (name, before), sha(read(dst))))
    for name in ("build_kfields_hard_review.py", "build_kfields_key.py", "raw_transport.py"):
        rows.append(("harness_g1v3/%s (committed, unchanged)" % name, sha(read(A.H + "/" + name))))
    return rows


def world():
    import recover_phase1_1488 as A
    import recover_run_1491 as R
    placed = A.place_world_without_correction() + A.place_correction() + R.place_owner(A) + place_hr_owners(A)
    K, T = A.route()
    placed += R.place_baseline(K, A)
    T.build_targeted(T.PKG_DIR)
    if T.package_problems(T.PKG_DIR):
        raise RuntimeError("the canonical targeted package does not rebuild")
    import audit_worker_access as AUD
    return A, R, K, T, AUD, placed


def targeted_run(R, K, T, AUD):
    """The committed run-1491 lifecycle, replayed to its exact binding (the hard review's provenance)."""
    sess, rows = R.place_states(); sid = R.install_seam(AUD, sess)
    items = {i["packet_id"]: i for i in T.targeted_items()}
    R.place_launchers(K, items, R.state_docs(sess), R.LAUNCH)
    fin, cfin, log = R.lifecycle(K, T, sess)
    T.write_binding(R.RUN)
    got = sha(read(T.BINDING))
    if got != PINS["targeted_binding"]:
        raise RuntimeError("the targeted binding is not the pinned identity: %s" % got)
    return sess, sid, got, [(r["attempt"], r["calls"]) for r in T.proved_spend(R.RUN)]


def workflows():
    rows = [l.split("\t") for l in io.open(HOME + "/inputs/WORKFLOWS.tsv", encoding="utf-8").read().splitlines()[1:]]
    return [dict(zip(("order", "label", "wf", "agent_id", "state", "transcript_files", "transcript_dir"), r)) for r in rows]


def place_hr_states(sess):
    src = None
    for proj in os.listdir(SRC_ROOT):
        for sid in os.listdir(SRC_ROOT + "/" + proj):
            src = SRC_ROOT + "/" + proj + "/" + sid
    rows = []
    for w in workflows():
        st_src = src + "/workflows/" + w["wf"] + ".json"; tr_src = src + "/subagents/workflows/" + w["wf"]
        h = hashlib.sha256()
        for f in sorted(os.listdir(tr_src)):
            h.update(("%s/%s\n" % (w["wf"], f)).encode()); h.update(sha(read(tr_src + "/" + f)).encode())
        if sha(read(st_src)) != w["state"] or h.hexdigest() != w["transcript_dir"] or str(len(os.listdir(tr_src))) != w["transcript_files"]:
            raise RuntimeError("copied evidence for %s is not the pinned bytes" % w["wf"])
        st = sess + "/workflows/" + w["wf"] + ".json"; tr = sess + "/subagents/workflows/" + w["wf"]
        if os.path.exists(st) or os.path.isdir(tr):
            raise RuntimeError("%s already present in the world store" % w["wf"])
        shutil.copyfile(st_src, st); shutil.copytree(tr_src, tr)
        rows.append((w["order"], w["label"], w["wf"], w["agent_id"], st, "pinned+projected"))
    return rows


def place_hr_pointer(K, RT):
    """Codex SEQ 1614 item 1: ONLY hr_dir.txt, from the preserved regen_1566 bytes, through the transport's write-once
    owner, into K.EVIDENCE; it must be the pinned bytes and must resolve to the existing historical receipt."""
    b = read(HOME + "/inputs/pointers/hr_dir.txt")
    if sha(b) != PINS["hr_pointer"]:
        raise RuntimeError("the preserved hr_dir.txt is not the pinned bytes")
    dst = K.EVIDENCE + "/hr_dir.txt"
    RT.write_new(dst, b.decode("utf-8"))
    run = b.decode("utf-8").strip(); rec = os.path.join(run, "receipt.json")
    if not os.path.isfile(rec) or not os.path.isfile(os.path.join(run, "finalization.json")):
        raise RuntimeError("hr_dir.txt does not resolve to an existing historical run with a receipt")
    return [("hr_dir.txt pointer", sha(read(dst)), PINS["hr_pointer"]), ("hr_dir.txt resolves (receipt.json present)", os.path.isfile(rec), True), ("hr run receipt (bench)", sha(read(rec)), sha(read(rec)))]


def red(K, RT):
    """The historical door refused while its exact budget receipt and package are absent."""
    import build_kfields_hard_review_targeted as HRT
    out = []
    try:
        HRT._ctx(); out.append("RED ctx: built without the budget receipt (UNEXPECTED)")
    except Exception as exc:                                             # noqa: BLE001 - by design
        out.append("RED ctx: %s: %s" % (type(exc).__name__, str(exc)[:120]))
    try:
        r = HRT.prepare_run(S + "/red_hr_run"); out.append("RED prepare_run: ok=%s problems=%s" % (r["ok"], r["problems"][:2]))
    except Exception as exc:                                             # noqa: BLE001 - by design
        out.append("RED prepare_run: %s: %s" % (type(exc).__name__, str(exc)[:120]))
    out.append("RED package present: %s; budget 1493 present: %s" % (os.path.isdir(HRT.PKG_DIR), os.path.exists(HRT.BUDGET_RECEIPT)))
    return out


def restore(K, T, RT):
    """Codex SEQ 1612 item 1: the recovered 1492 receipt at its historical path, the exact 1493 receipt from it by
    the deterministic transform with THIS world's binding hash, then the package through the exact owner."""
    import build_kfields_hard_review_targeted as HRT, build_kfields_hard_review as HR, reconstruct_receipt_1493 as RR
    log = []
    b = read(HOME + "/inputs/a7_budget_receipt_1492.json")
    if sha(b) != PINS["budget_receipt_1492"]:
        raise RuntimeError("the recovered 1492 receipt is not the pinned bytes")
    RT.write_new("/tmp/a7_budget_receipt_1492.json", b.decode("utf-8")); log.append(("receipt_1492", sha(read("/tmp/a7_budget_receipt_1492.json"))))
    bsha = sha(read(T.BINDING))
    out = RR.transform(b, bsha)
    if sha(out) != PINS["budget_receipt"]:
        raise RuntimeError("the reconstructed 1493 receipt is not the pinned identity: %s" % sha(out))
    RT.write_new(HRT.BUDGET_RECEIPT, out.decode("utf-8")); log.append(("receipt_1493", sha(read(HRT.BUDGET_RECEIPT)), len(out), "from 1492 by transform with binding " + bsha[:16]))
    for path in ("/tmp/a7_budget_receipt_1488.json", "/tmp/a7_budget_receipt_1492.json", "/tmp/a7_budget_receipt_1493.json"):
        log.append((path, sha(read(path)) if os.path.exists(path) else "MISSING"))
    doc = HRT.build(HRT.PKG_DIR)
    man = os.path.join(HRT.PKG_DIR, HR.MANIFEST_NAME)
    log.append(("manifest", sha(read(man)), doc["manifest_sha256"])); log.append(("prefix", sha(read(os.path.join(HRT.PKG_DIR, "prompt_prefix_item.txt")))))
    log.append(("package_problems", HRT.package_problems(HRT.PKG_DIR))); log.append(("prompt_order_problems", HRT.prompt_order_problems())); pf = HRT.preflight(); log.append(("preflight", pf["ok"], pf["problems"][:2]))
    log.append(("budget", doc["budget"])); log.append(("counts", doc["counts"]))
    return HRT, HR, log


def lifecycle(HRT, HR, sess):
    log = []
    got = HRT.prepare_run(RUN); log.append(("prepare_run", got["ok"], len(got["invocations"]), got["problems"][:2]))
    if not got["ok"]:
        raise RuntimeError("prepare_run refused: %s" % got["problems"][:2])
    inv = {i["label"]: i for i in got["invocations"]}
    launchers = []
    for w in workflows():
        doc = json.loads(read(sess + "/workflows/" + w["wf"] + ".json").decode("utf-8"))
        i = inv[w["label"]]; task, blind = HR._by_label_of(HRT._ctx())[w["label"]]     # the owner's own label map
        want = HRT.render_launcher(task, blind, 1)
        on_disk = read(i["scriptPath"])
        if doc.get("scriptPath") != i["scriptPath"] or doc.get("script") != want or on_disk != want.encode("utf-8") or sha(on_disk) != i["script_sha256"]:
            raise RuntimeError("%s: the state's launcher is not the renderer's" % w["label"])
        launchers.append((w["order"], w["label"], w["wf"], i["scriptPath"], sha(on_disk), len(on_disk)))
    for w in workflows():
        bad = HRT.record_state(RUN, sess + "/workflows/" + w["wf"] + ".json"); log.append(("record_state", w["label"], w["wf"], bad))
        if bad:
            raise RuntimeError("record_state refused %s: %s" % (w["label"], bad))
    fin = HRT.finalize(RUN); log.append(("finalize", fin["ledger"], fin.get("retry"), fin.get("primary_complete"), fin.get("problems")))
    return fin, log, launchers


def evidence(fin):
    import build_kfields_final as F
    rec = json.loads(read(RUN + "/receipt.json").decode("utf-8")); states = [json.loads(read(p).decode("utf-8")) for p in rec["states"]]
    h = hashlib.sha256()
    for p in rec["states"]: h.update(sha(read(p)).encode())
    state_tree = h.hexdigest()
    wfs = [f.split(".")[0] for f in fin["harvested_raw"]]
    h = hashlib.sha256(); n = 0
    for wf in wfs:
        for p in sorted(glob.glob("%s/subagents/workflows/%s/*" % (SESS, wf))): h.update(("%s/%s\n" % (wf, os.path.basename(p))).encode()); h.update(sha(read(p)).encode()); n += 1
    trans_tree = h.hexdigest()
    gaps = [(b["startTime"] - a["startTime"] - a["durationMs"]) / 1000.0 for a, b in zip(states, states[1:])]
    agents = [[r for r in s["workflowProgress"] if r.get("type") == "workflow_agent"][0] for s in states]
    tools = sum(s["totalToolCalls"] for s in states); tokens = sum(s["totalTokens"] for s in states)
    metas = collections.Counter(); reads = 0
    for wf in wfs:
        for mp in glob.glob("%s/subagents/workflows/%s/agent-*.meta.json" % (SESS, wf)): metas[json.loads(read(mp).decode("utf-8"))["model"]] += 1
        for tp in glob.glob("%s/subagents/workflows/%s/agent-*.jsonl" % (SESS, wf)):
            for line in io.open(tp, encoding="utf-8"):
                if '"name": "Read"' in line or '"name":"Read"' in line: reads += 1
    shell = subprocess.run("cd %s/raw && sha256sum * | sha256sum" % RUN, shell=True, capture_output=True, text=True).stdout.split()[0]
    canon = F.raw_tree(RUN)
    rows = [("run receipt", sha(read(RUN + "/receipt.json")), PINS["run_receipt"]), ("run finalization", sha(read(RUN + "/finalization.json")), PINS["run_finalization"]),
            ("raw tree canonical (owner)", canon["sha256"], PINS["raw_tree_canonical"]), ("raw files", len(os.listdir(RUN + "/raw")), PINS["raw_files"]), ("raw tree shell checksum (separately named)", shell, PINS["raw_tree_shell"]),
            ("official-state tree", state_tree, PINS["state_tree"]), ("transcript tree", trans_tree, PINS["transcript_tree"]), ("transcript files", n, PINS["transcript_files"]),
            ("states recorded", len(rec["states"]), PINS["states"]), ("completed states", sum(1 for s in states if s["status"] == "completed"), 22),
            ("ledger valid/invalid/unproved/missing/transport", (fin["ledger"]["valid"], fin["ledger"]["invalid_response"], fin["ledger"]["unproved"], fin["ledger"]["missing"], fin["ledger"]["transport_no_answer"]), (22, 0, 0, 0, 0)),
            ("retry (no child)", list(fin.get("retry") or []), []), ("primary_complete", fin.get("primary_complete"), True), ("finalization problems", list(fin.get("problems") or []), []),
            ("distinct agent ids", len({a["agentId"] for a in agents}), 22), ("agent labels", len({a["label"] for a in agents}), 22), ("agent model sonnet", sum(1 for a in agents if a.get("model") == "claude-sonnet-5"), 22),
            ("result model sonnet / lean-probe / high", (sum(1 for s in states if s["result"]["model"] == "sonnet"), sum(1 for s in states if s["result"]["agentType"] == "lean-probe"), sum(1 for s in states if s["result"]["effort"] == "high")), (22, 22, 22)),
            ("meta model sonnet", metas.get("sonnet", 0), 22), ("tool calls summed", tools, 0), ("Read in transcripts", reads, 0), ("serial gaps positive", sum(1 for g in gaps if g > 0), 21), ("tokens summed", tokens, 1034662),
            ("budget ledger_before/ledger_after (finalization)", (fin.get("budget", {}).get("ledger_before"), fin.get("budget", {}).get("ledger_after")), (PINS["ledger_before"], PINS["ledger_after"]))]
    return [(k, g, w, "ok" if g == w else "DIFF") for k, g, w in rows], canon


def loaded_modules():
    return [(n, m.__file__.replace(S + "/", ""), sha(read(m.__file__))) for n, m in sorted(sys.modules.items()) if getattr(m, "__file__", None) and (m.__file__.startswith(S) or m.__file__.startswith(HOME) or m.__file__.startswith(P1) or m.__file__.startswith(R1491))]


def main(tag):
    out = OUTROOT + "/" + tag; os.makedirs(out, exist_ok=True)
    sys.path.insert(0, P1); sys.path.insert(0, R1491); sys.path.insert(0, HOME)
    A, R, K, T, AUD, placed = world()
    import raw_transport as RT, build_exp5_contract as C, build_launch_manifest as BLM
    sess, sid, binding, spend = targeted_run(R, K, T, AUD)
    reds = red(K, RT); io.open(out + "/red.txt", "w", encoding="utf-8").write("\n".join(reds) + "\n"); print("\n".join(reds))
    HRT, HR, rlog = restore(K, T, RT); print("\n".join("restore %s" % json.dumps(r, default=str)[:220] for r in rlog))
    prow = place_hr_pointer(K, RT); print("pointer", json.dumps(prow, default=str))
    ledger_before = json.loads(read(HRT.BUDGET_RECEIPT).decode("utf-8"))["completed_before"]
    rules = sha(C.role_rules("drafter", BLM.PRODUCER_CONTRACT_SUFFIX).encode("utf-8"))
    srows = place_hr_states(sess)
    fin, log, launchers = lifecycle(HRT, HR, sess)
    ck, canon = evidence(fin)
    extra = [("targeted binding", binding, PINS["targeted_binding"]), ("targeted spend", spend, [(1, 11), (2, 1)]), ("budget receipt 1492 (recovered)", rlog[0][1], PINS["budget_receipt_1492"]),
          ("budget receipt 1493 (transform)", sha(read("/tmp/a7_budget_receipt_1493.json")), PINS["budget_receipt"]), ("hard-review owner imported", sha(read(HRT.__file__)), PINS["hard_review_targeted_owner"]), ("base owner imported", sha(read(HR.__file__)), PINS["hard_review_owner"]), ("hard-review manifest", rlog[[r[0] for r in rlog].index("manifest")][1], PINS["hr_manifest"]),
          ("prefix", rlog[[r[0] for r in rlog].index("prefix")][1], PINS["hr_prefix"]), ("v3 rules", rules, PINS["rules_v3"]), ("ledger before (the receipt's completed_before)", ledger_before, PINS["ledger_before"]),
          ("launchers", len(launchers), 22), ("launcher paths distinct", len({l[3] for l in launchers}), 22)] + prow
    ck = [(k, g, w, "ok" if g == w else "DIFF") for k, g, w in extra] + ck
    ok = all(c[3] == "ok" for c in ck)
    lines = ["seam: 22 states projected at %s; audit session == PARENT_SESSION %s" % (SESS, sid == K.PARENT_SESSION)] + ["restore %s" % json.dumps(r, default=str)[:220] for r in rlog] + ["lifecycle %s" % json.dumps(l, default=str)[:200] for l in log]
    lines += ["check %s: %s vs %s %s" % (c[0], str(c[1])[:150], str(c[2])[:150], c[3]) for c in ck] + ["RESULT " + ("MATCH" if ok and sid == K.PARENT_SESSION else "DIFF")]
    io.open(out + "/RESULT.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n"); print("\n".join(lines))
    io.open(out + "/LIFECYCLE.txt", "w", encoding="utf-8").write("\n".join(json.dumps(l, default=str) for l in log) + "\n")
    for n in ("receipt.json", "finalization.json"): shutil.copyfile(RUN + "/" + n, out + "/run." + n)
    os.makedirs(out + "/raw", exist_ok=True)
    for f in os.listdir(RUN + "/raw"): shutil.copyfile(RUN + "/raw/" + f, out + "/raw/" + f)
    for src, dst in ((HRT.PKG_DIR + "/" + HR.MANIFEST_NAME, "hard_review.manifest.json"), (HRT.PKG_DIR + "/prompt_prefix_item.txt", "prompt_prefix_item.txt"), ("/tmp/a7_budget_receipt_1492.json", "a7_budget_receipt_1492.json"), ("/tmp/a7_budget_receipt_1493.json", "a7_budget_receipt_1493.json"), (T.BINDING, "targeted_binding.json")):
        shutil.copyfile(src, out + "/" + dst)
    io.open(out + "/raw_tree_canonical.json", "w", encoding="utf-8").write(json.dumps(canon, indent=1, default=str))
    _tsv(out + "/STATES.tsv", [("order", "label", "wf", "agent_id", "world_state_path", "status")] + srows)
    _tsv(out + "/LAUNCHERS.tsv", [("order", "label", "wf", "scriptPath", "sha256", "bytes")] + launchers)
    _tsv(out + "/PLACED.tsv", [("path", "sha256")] + placed); _tsv(out + "/CHECKS.tsv", [("check", "got", "want", "status")] + [(c[0], json.dumps(c[1], default=str), json.dumps(c[2], default=str), c[3]) for c in ck])
    _tsv(out + "/DEPENDENCIES.tsv", [("module", "path", "sha256")] + loaded_modules())
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HOME))))
    classes = (("unit", HOME), ("run1491", R1491), ("phase1", P1), ("regen_1570", ROOT + "/a4_recovery/regen_1570"), ("bench", S), ("tmp", "/tmp/"), ("store", SESS))
    rows = []
    for p in sorted({os.path.normpath(p) for p in OPENED if os.path.isfile(p)}):
        cls = next((c for c, pre in classes if p.startswith(pre)), "OUTSIDE"); rows.append((cls, p[len(ROOT) + 1:] if p.startswith(ROOT + "/") else p.replace(S + "/", ""), sha(read(p))))
    _tsv(out + "/OPENED.tsv", [("class", "path", "sha256")] + rows)
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
