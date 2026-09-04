# -*- coding: utf-8 -*-
"""RECOVERY ADAPTER for the phase1_targeted_1488 package (Codex SEQ 1598). NOT an owner.

Inside a fresh private projected world it (1) places every input the targeted owner opens, each
hash-pinned from the unit's immutable inputs/ directory (the accepted correction outputs as one
directory, the corrected inventory, the budget receipt, the locator receipt, the A3 re-audit owner,
the three A1-era files the G1v3 A3 proof reads), (2) records the red: the exact build refuses
while the correction directory is absent, (3) writes the A3 v2 baseline through the exact re-audit
owner and compares it with its pins, (4) runs the exact targeted owner through the historical
import route and compares its two files with the pins, recomputing every binding from the bytes,
and (5) exports the package, the loaded-module census and every check. Nothing is hand-built.
"""
import collections, hashlib, io, json, os, shutil, subprocess, sys

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
H = X + "/harness_g1v3"
LOCK = S + "/lock"
HOME = os.environ["PHASE1_1488_HOME"]
INP = HOME + "/inputs"
OUTROOT = HOME + "/out/attempt5"
PINS = json.load(io.open(HOME + "/pins_1598.json", encoding="utf-8"))
P99 = json.load(io.open(HOME + "/pins_1599.json", encoding="utf-8"))
OPENED = set()


def _audit(event, args):                       # every file the adapter process opens for reading (Python audit hook)
    if event == "open" and isinstance(args[0], str) and (args[1] is None or "r" in str(args[1])) and args[0].startswith(S):
        OPENED.add(args[0])


sys.addaudithook(_audit)
CORR = json.load(io.open(os.path.dirname(HOME) + "/correction_1488/pins_1594.json", encoding="utf-8"))
PY = "/home/faisal/EventMarketDB/venv/bin/python3"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return io.open(p, "rb").read()


def _cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def _tsv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write("".join("\t".join(str(c) for c in r) + "\n" for r in rows))


def _pin(path, want, what):
    got = sha(read(path))
    if got != want:
        raise RuntimeError("%s is %s, not the pinned %s" % (what, got, want))
    return got


def place_world_without_correction():
    """Every input but the correction directory, each pinned."""
    rows = []
    for name in ("build_kfields_key.py", "build_kfields_key_targeted.py", "raw_transport.py"):
        rows.append(("harness_g1v3/" + name, sha(read(H + "/" + name))))
    _pin(H + "/build_kfields_key.py", PINS["key_owner_sha256"], "key owner"); _pin(H + "/build_kfields_key_targeted.py", PINS["targeted_owner_sha256"], "targeted owner"); _pin(H + "/raw_transport.py", PINS["transport_sha256"], "transport")
    # the two measured A3 dependencies at their 1488 bytes (Codex SEQ 1599), over the stage-1 tree's later copies
    for name, key in (("build_launch_manifest.py", "blm_1488_sha256"), ("audit_worker_access.py", "aud_1488_sha256")):
        before = sha(read(H + "/" + name)); _cp(INP + "/era_1488/" + name, H + "/" + name); rows.append(("harness_g1v3/" + name + " (1488 bytes, displaced " + before + ")", _pin(H + "/" + name, P99[key], name)))
    # the A1-era files the G1v3 A3 proof reads (the accepted locator unit's derivation: the plan by the A3 receipt's manifest_sha256)
    primary = read(S + "/a3_serial_dir.txt").decode("utf-8").strip()
    want = json.loads(read(primary + "/receipt.json").decode("utf-8"))["manifest_sha256"]
    for name in ("launch_kfields_drafts.manifest.json", "launch_kfields_a1.bundle.json", "exp5_rev4_package.md"):
        before = sha(read(H + "/" + name)) if os.path.exists(H + "/" + name) else None
        _cp(INP + "/a1_era/" + name, H + "/" + name); rows.append(("harness_g1v3/" + name + " (A1-era, displaced " + str(before) + ")", sha(read(H + "/" + name))))
    if sha(read(H + "/launch_kfields_drafts.manifest.json")) != want:
        raise RuntimeError("the A1 plan is not the one the A3 receipt binds")
    # THE PLAN'S OWN PROTECTED PINS (Codex SEQ 1599 stop point, attempt 4): the A1 plan the A3 receipt binds names
    # the hash of every protected file; where the G1v3 copy is not that hash and the unit's a1_era/ input is, the
    # pinned bytes are placed. The name -> path mapping is the placed launch-manifest owner's own (_protected_pins),
    # read in a clean interpreter so the historical import route stays untouched.
    plan_pins = json.loads(read(H + "/launch_kfields_drafts.manifest.json").decode("utf-8"))["pins"]
    m = subprocess.run([PY, "-B", "-c", "import sys, json; sys.path.insert(0, %r); import build_launch_manifest as B; print(json.dumps(B._protected_pins('')))" % H], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    for pname, path in json.loads(m.stdout.strip().splitlines()[-1]).items():
        want_pin = plan_pins[pname]; cur = sha(read(path)) if os.path.exists(path) else None
        if cur == want_pin:
            continue
        cand = INP + "/a1_era/" + os.path.basename(path)
        if not os.path.exists(cand) or sha(read(cand)) != want_pin:
            raise RuntimeError("protected pin %s wants %s; the G1v3 copy is %s and no pinned input holds it" % (pname, want_pin, cur))
        _cp(cand, path); rows.append(("harness_g1v3/%s (plan pin %s, displaced %s)" % (os.path.basename(path), pname, cur), _pin(path, want_pin, pname)))
    _cp(INP + "/one_item_benchmark_inventory.v2_1487.json", X + "/one_item_benchmark_inventory.v2_1487.json"); rows.append(("experiments/one_item_benchmark_inventory.v2_1487.json", _pin(X + "/one_item_benchmark_inventory.v2_1487.json", CORR["final_inventory"], "corrected inventory")))
    rows.append(("experiments/one_item_benchmark_inventory.json (frozen)", sha(read(X + "/one_item_benchmark_inventory.json"))))
    _cp(INP + "/a7_budget_receipt_1488.json", "/tmp/a7_budget_receipt_1488.json"); rows.append(("/tmp/a7_budget_receipt_1488.json", _pin("/tmp/a7_budget_receipt_1488.json", PINS["budget_receipt_sha256"], "budget receipt")))
    _cp(INP + "/a7_source_locator_audit_1486.json", "/tmp/a7_source_locator_audit_1486.json"); rows.append(("/tmp/a7_source_locator_audit_1486.json", sha(read("/tmp/a7_source_locator_audit_1486.json"))))
    _cp(INP + "/a3_reaudit_v2.py", S + "/a4/a3_reaudit_v2.py"); rows.append(("a4/a3_reaudit_v2.py", _pin(S + "/a4/a3_reaudit_v2.py", PINS["reaudit_sha256"], "re-audit owner")))
    rows.append(("a4/a3_baseline.json (v1)", sha(read(S + "/a4/a3_baseline.json"))))
    return rows


def place_correction():
    rows = []
    for name, key in (("final_inventory.json", "final_inventory"), ("adjudication_sidecar.json", "adjudication_sidecar"), ("validator_receipt.json", "validator_receipt"), ("correction_receipt.json", "correction_receipt")):
        _cp(INP + "/candidate_v2_1488/" + name, LOCK + "/candidate_v2_1488/" + name); rows.append(("lock/candidate_v2_1488/" + name, _pin(LOCK + "/candidate_v2_1488/" + name, CORR[key], name)))
    return rows


def route():
    """THE ONE import route (transcript line 79488): from harness_g1v3, the harness owners first."""
    os.chdir(H)
    sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/home/faisal/EventMarketDB")
    import build_kfields_key as K, a6_launch_freeze, a7_g1_build, build_kfields_key_targeted as T   # noqa: F401,E401
    return K, T


def loaded_modules():
    rows = []
    for name, mod in sorted(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and f.startswith(S):
            rows.append((name, f.replace(S + "/", ""), sha(read(f))))
    return rows


def baseline(K):
    """The A3 v2 baseline through the exact re-audit owner, in a clean interpreter, as the key owner runs it."""
    out = K.A3_BASELINE
    trace = OUTROOT + "/reaudit.strace"
    p = subprocess.run(["strace", "-f", "-e", "trace=openat", "-o", trace, PY, "-B", K.A3_REAUDIT, out], capture_output=True, text=True, cwd=K._REPO, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    for line in io.open(trace, encoding="utf-8", errors="replace"):
        m = __import__("re").search(r'openat\(.*?"([^"]+)".*O_RDONLY', line)
        if m and m.group(1).startswith(S) and os.path.isfile(m.group(1)):
            OPENED.add(m.group(1))
    doc = json.loads(p.stdout) if p.returncode == 0 else None
    return {"rc": p.returncode, "stderr": p.stderr.strip()[-300:], "digest": doc["digest"] if doc else None, "files": len(doc["files"]) if doc else None,
            "file_sha256": sha(read(out)) if os.path.exists(out) else None, "problems": doc["primary_problems"] if doc else None, "doc": doc}


def checks(K, T, doc, pkg_dir):
    man = json.loads(read(pkg_dir + "/phase1.manifest.json").decode("utf-8"))
    cr = json.loads(read(T.CORRECTION_RECEIPT).decode("utf-8"))
    rows = [("calls", man["calls"], 11), ("targets in order", [r["packet_id"] for r in man["items"]], PINS["targets"]),
            ("correction.targets", [t["packet_id"] for t in man["correction"]["targets"]], PINS["targets"]),
            ("correction.frozen_inventory_sha256", man["correction"]["frozen_inventory_sha256"], sha(read(K.INV.INV))),
            ("correction.correction_receipt_sha256", man["correction"]["correction_receipt_sha256"], CORR["correction_receipt"]),
            ("correction.source_receipt", man["correction"]["source_receipt"], cr["source_receipt"]),
            ("correction.corrected_inventory_sha256", man["correction"]["corrected_inventory_sha256"], CORR["final_inventory"]),
            ("inventory_sha256", man["inventory_sha256"], CORR["final_inventory"]),
            ("budget.budget_receipt_sha256", man["budget"]["budget_receipt_sha256"], PINS["budget_receipt_sha256"]),
            ("budget.before/after/ceiling", (man["budget"]["before"], man["budget"]["after"], man["budget"]["ceiling"]), (json.loads(read("/tmp/a7_budget_receipt_1488.json"))["completed_before"], json.loads(read("/tmp/a7_budget_receipt_1488.json"))["completed_before"] + 11, json.loads(read("/tmp/a7_budget_receipt_1488.json"))["ceiling"])),
            ("rules_sha256", man["rules_sha256"], sha(read(pkg_dir + "/rules.txt"))),
            ("transport block", man["transport"], json.loads(json.dumps(K._transport_block()))),
            ("a3_binding", man["a3_binding"], json.loads(json.dumps(K.a3_evidence()["binding"]))),
            ("package_problems", T.package_problems(pkg_dir), [])]
    items = {it["packet_id"]: it for it in T.targeted_items()}
    rows.append(("items prompt/script hashes recomputed", sum(1 for r in man["items"] if K._sha(K.phase1_prompt(items[r["packet_id"]])) == r["prompt_sha256"] and K._sha(K.render_launcher(items[r["packet_id"]])) == r["script_sha256"]), len(man["items"])))
    rows.append(("items drafts = a3 drafts", sum(1 for r in man["items"] if r["drafts"] == [{"lane_id": d["lane_id"], "sha256": d["sha256"]} for d in items[r["packet_id"]]["a3_drafts"]]), len(man["items"])))
    return [(k, g, w, "ok" if g == w else "DIFF") for k, g, w in rows]


def door(K, T, run_dir):
    r = T.prepare_run(run_dir)
    rp = run_dir + "/receipt.json"
    rec = json.loads(read(rp).decode("utf-8")) if os.path.exists(rp) else None
    valid = K._receipt_problems(run_dir, rec, T._ctx()) if rec else ["no receipt"]
    return {"ok": r["ok"], "problems": r["problems"], "invocations": [i["packet_id"] for i in r["invocations"]], "receipt": bool(rec), "receipt_problems": valid, "receipt_sha256": sha(read(rp)) if rec else None, "allowed": rec.get("allowed") if rec else None}


def door_proofs(K, T):
    """Green control, the moved-byte refusal through the real door, the green control again."""
    base_doc = json.loads(read(K.A3_BASELINE).decode("utf-8"))
    target = sorted(f for f in base_doc["files"] if f.startswith("harness_g1v3/") and f.endswith(".py"))[0]
    g1 = door(K, T, S + "/door_green_1")
    p = K._X + "/" + target; orig = read(p); io.open(p, "wb").write(orig + b"\n# moved\n")
    try:
        red = door(K, T, S + "/door_red")
    finally:
        io.open(p, "wb").write(orig)
    g2 = door(K, T, S + "/door_green_2")
    rows = [("green 1 ok/problems/invocations/receipt valid", (g1["ok"], g1["problems"], len(g1["invocations"]), g1["receipt"], g1["receipt_problems"]), (True, [], 11, True, [])),
            ("green 1 invocation order", g1["invocations"], PINS["targets"]),
            ("red (%s +1 byte) ok/reason/invocations/receipt" % target, (red["ok"], P99["refusal_reason"] in red["problems"], len(red["invocations"]), red["receipt"]), (False, True, 0, False)),
            ("red problems", red["problems"], [P99["refusal_reason"]]),
            ("green 2 ok/problems/invocations/receipt valid", (g2["ok"], g2["problems"], len(g2["invocations"]), g2["receipt"], g2["receipt_problems"]), (True, [], 11, True, [])),
            ("green 2 receipt allows the same keys as green 1", g2["allowed"] == g1["allowed"] and g1["allowed"] is not None, True)]
    return [(k, g, w, "ok" if g == w else "DIFF") for k, g, w in rows], {"green_1": g1, "red": red, "green_2": g2, "mutated_file": target}


def main(tag):
    out = OUTROOT + "/" + tag; os.makedirs(out, exist_ok=True)
    placed = place_world_without_correction()
    K, T = route()
    # RED: the exact build with the correction directory absent
    try:
        T.build_targeted(S + "/red_pkg"); red = "RED: the owner BUILT without the correction directory (unexpected)"
    except Exception as e:
        red = "RED: the owner REFUSED without the correction directory: %s: %s" % (type(e).__name__, str(e)[:160])
    io.open(out + "/red.txt", "w", encoding="utf-8").write(red + "\n"); print(red)
    placed += place_correction()
    bl = baseline(K)
    doc = T.build_targeted(T.PKG_DIR)
    mods = loaded_modules()
    got_m, got_r = sha(read(T.PKG_DIR + "/phase1.manifest.json")), sha(read(T.PKG_DIR + "/rules.txt"))
    ck = checks(K, T, doc, T.PKG_DIR)
    lines = ["manifest got %s want %s %s" % (got_m, PINS["manifest_sha256"], "MATCH" if got_m == PINS["manifest_sha256"] else "DIFF"),
             "rules got %s want %s %s" % (got_r, PINS["rules_sha256"], "MATCH" if got_r == PINS["rules_sha256"] else "DIFF"),
             "baseline rc=%s file %s want %s %s; digest %s want %s %s; files %s; problems %s" % (bl["rc"], bl["file_sha256"], PINS["baseline_sha256"], "MATCH" if bl["file_sha256"] == PINS["baseline_sha256"] else "DIFF", bl["digest"], PINS["baseline_digest"], "MATCH" if bl["digest"] == PINS["baseline_digest"] else "DIFF", bl["files"], bl["problems"])]
    lines += ["check %s: %s vs %s %s" % (c[0], str(c[1])[:200], str(c[2])[:200], c[3]) for c in ck]
    bl_ok = bl["file_sha256"] == PINS["baseline_sha256"] and bl["digest"] == PINS["baseline_digest"] and bl["files"] == 48 and bl["problems"] == []
    dk, dd = (door_proofs(K, T) if bl_ok else ([("door", "skipped: the baseline is not exact", "", "DIFF")], {}))
    lines += ["door %s: %s vs %s %s" % (c[0], str(c[1])[:200], str(c[2])[:200], c[3]) for c in dk]
    ok = got_m == PINS["manifest_sha256"] and got_r == PINS["rules_sha256"] and all(c[3] == "ok" for c in ck) and bl_ok and all(c[3] == "ok" for c in dk)
    lines.append("loaded modules %d" % len(mods)); lines.append("RESULT " + ("MATCH" if ok else "DIFF"))
    for n in ("phase1.manifest.json", "rules.txt"):
        _cp(T.PKG_DIR + "/" + n, out + "/phase1_targeted_1488/" + n)
    if bl["file_sha256"]:
        _cp(K.A3_BASELINE, out + "/a3_baseline.v2_1488.json")
    io.open(out + "/RESULT.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    _tsv(out + "/PLACED.tsv", [("path", "sha256")] + placed); _tsv(out + "/DEPENDENCIES.tsv", [("module", "path", "sha256")] + mods); _tsv(out + "/CHECKS.tsv", [("check", "got", "want", "status")] + [(c[0], json.dumps(c[1], default=str), json.dumps(c[2], default=str), c[3]) for c in ck])
    if bl["doc"]:
        io.open(out + "/a3_reaudit_measure.json", "w", encoding="utf-8").write(json.dumps(bl["doc"], indent=1))
    _tsv(out + "/DOOR.tsv", [("check", "got", "want", "status")] + [(c[0], json.dumps(c[1], default=str), json.dumps(c[2], default=str), c[3]) for c in dk])
    for g in ("green_1", "green_2"):
        if dd.get(g, {}).get("receipt"):
            _cp(S + "/door_" + g + "/receipt.json", out + "/door_" + g + ".receipt.json")
    io.open(out + "/DOOR.json", "w", encoding="utf-8").write(json.dumps(dd, indent=1, default=str))
    opened = sorted(p for p in OPENED if os.path.isfile(p))
    _tsv(out + "/OPENED.tsv", [("path", "sha256")] + [(p.replace(S + "/", ""), sha(read(p))) for p in opened])
    lines.append("opened files under the world %d" % len(opened))
    print("\n".join(lines))
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
