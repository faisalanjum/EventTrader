# -*- coding: utf-8 -*-
"""RECOVERY ADAPTER for /tmp/a4_targeted_run_1491 (Codex SEQ 1601, 1603, 1605). NOT an owner. Zero model calls.

In a fresh private world: (1) the accepted phase-1 world and canonical package through the committed phase-1
adapter, with the EXACT later targeted owner (derived once from the recorded replacement chain, pinned) placed
over the committed phase-1 copy before the historical import route runs, and the verified A3 v2 baseline
copied (never re-measured) to where the door's preflight reads it; (2) the twelve official states, copied and
pinned, projected to their exact historical paths inside the masked private session store (the one relocation
seam); (3) each state's armed launcher restored at its exact historical scriptPath under the private launch
directory, only when it is unique, names the expected attempt, equals K.render_launcher(item, attempt) and
hashes equal on disk; (4) the exact historical lifecycle prepare_run -> record_state x11 -> finalize ->
record_state x1 (child) -> finalize; (5) the binding and the spend through the exact owner; (6) every identity
checked against the pins and exported. This adapter writes nothing outside its own out/ and the private world."""
import collections, hashlib, io, json, os, shutil, sys

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
HOME = os.environ["RUN_1491_HOME"]
P1 = os.path.dirname(HOME) + "/phase1_targeted_1488"
os.environ.setdefault("PHASE1_1488_HOME", P1)
OUTROOT = HOME + "/out/attempt6"
PINS = json.load(io.open(HOME + "/pins_1601.json", encoding="utf-8"))
SRC_ROOT = HOME + "/inputs/session_store/projects"
SESS = "/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"   # the historical official store path (masked tmpfs in the world)
RUN = PINS["run_dir"]
LAUNCH = RUN + "_launch"                                                  # the historical private launch directory
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HOME))))   # the tree that holds a4_recovery/; tables name paths relative to it
OPENED = set()
QUIET = ("/home/faisal/EventMarketDB/venv", "/usr", "/lib", "/etc", "/proc", "/dev", "/sys")


def _audit(event, args):
    if event == "open" and isinstance(args[0], str) and (args[1] is None or "r" in str(args[1])) and not args[0].startswith(QUIET):
        OPENED.add(args[0])


sys.addaudithook(_audit)
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: io.open(p, "rb").read()
treesha = lambda d: sha(("".join(sha(read(d + "/" + f)) + "  " + f + "\n" for f in sorted(os.listdir(d)))).encode())


def _tsv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write("".join("\t".join(str(c) for c in r) + "\n" for r in rows))


def workflows():
    rows = [l.split("\t") for l in io.open(HOME + "/inputs/WORKFLOWS.tsv", encoding="utf-8").read().splitlines()[1:]]
    return [dict(zip(("order", "attempt", "packet_id", "wf", "state", "journal", "tree"), r)) for r in rows]


def place_owner(A):
    """The EXACT later targeted owner (derive_owner_1491.py, pinned) over the committed phase-1 copy, before import."""
    b = read(HOME + "/build_kfields_key_targeted.py")
    if sha(b) != PINS["later_owner"]:
        raise RuntimeError("the derived targeted owner is not the pinned later owner")
    dst = A.H + "/build_kfields_key_targeted.py"; before = sha(read(dst))
    io.open(dst, "wb").write(b)
    return [("harness_g1v3/build_kfields_key_targeted.py (exact later owner, displaced " + before + ")", sha(read(dst)))]


def place_baseline(K, A):
    """The verified A3 v2 baseline, copied from the accepted phase-1 output after its pin; never re-measured here."""
    b = read(P1 + "/out/attempt5/A/a3_baseline.v2_1488.json")
    if sha(b) != A.P99["baseline_sha256"] or json.loads(b.decode("utf-8"))["digest"] != A.P99["baseline_digest"]:
        raise RuntimeError("the verified A3 baseline is not the pinned bytes")
    if os.path.exists(K.A3_BASELINE):
        raise RuntimeError("a baseline is already present in the world")
    os.makedirs(os.path.dirname(K.A3_BASELINE), exist_ok=True); io.open(K.A3_BASELINE, "wb").write(b)
    return [("a4/a3_baseline.v2_1488.json (verified phase-1 copy)", sha(read(K.A3_BASELINE)))]


def place_states(src_root=SRC_ROOT, dest=SESS):
    """THE ONE RELOCATION SEAM: the twelve copied official states and their transcript directories are
    projected to their exact historical paths inside the masked private session store (beside the
    foundation-projected A3 states), so the shared audit resolves them exactly as the runtime laid them
    out and the receipt records the same absolute state paths history recorded. Each is pinned first."""
    src = None
    for proj in os.listdir(src_root):
        for sid in os.listdir(src_root + "/" + proj):
            src = src_root + "/" + proj + "/" + sid
    os.makedirs(dest + "/workflows", exist_ok=True); os.makedirs(dest + "/subagents/workflows", exist_ok=True)
    rows = []
    for w in workflows():
        st_src = src + "/workflows/" + w["wf"] + ".json"; tr_src = src + "/subagents/workflows/" + w["wf"]
        if sha(read(st_src)) != w["state"] or sha(read(tr_src + "/journal.jsonl")) != w["journal"] or treesha(tr_src) != w["tree"]:
            raise RuntimeError("copied evidence for %s is not the pinned bytes" % w["wf"])
        st = dest + "/workflows/" + w["wf"] + ".json"; tr = dest + "/subagents/workflows/" + w["wf"]
        if os.path.exists(st) or os.path.isdir(tr):
            raise RuntimeError("%s already present in the world store" % w["wf"])
        shutil.copyfile(st_src, st); shutil.copytree(tr_src, tr)
        rows.append((w["order"], w["attempt"], w["packet_id"], w["wf"], st, "pinned+projected"))
    return dest, rows


def state_docs(sess):
    """(order, attempt, packet_id, wf, state document) for the twelve projected states, in Core 1310 order."""
    return [(w["order"], int(w["attempt"]), w["packet_id"], w["wf"], json.loads(read(sess + "/workflows/" + w["wf"] + ".json").decode("utf-8"))) for w in workflows()]


def place_launchers(K, items, docs, launch_dir):
    """Restore each state's armed launcher at its exact historical scriptPath, fail-closed: the path must lie in
    the private launch directory, be unique, name the expected attempt; the state's embedded script must equal
    K.render_launcher(item, attempt) for the state's own label; the bytes written must hash equal to both."""
    if os.path.exists(launch_dir):
        raise RuntimeError("the launch directory is already present")
    os.makedirs(launch_dir)
    seen, rows = set(), []
    for order, attempt, pid, wf, doc in docs:
        sp, script = doc.get("scriptPath"), doc.get("script")
        if not isinstance(sp, str) or os.path.dirname(sp) != launch_dir:
            raise RuntimeError("%s: scriptPath %r is not in the private launch directory" % (wf, sp))
        if sp in seen:
            raise RuntimeError("%s: scriptPath %r is not unique" % (wf, sp))
        seen.add(sp)
        if not sp.endswith(".attempt%d.js" % attempt):
            raise RuntimeError("%s: scriptPath %r does not name attempt %d" % (wf, sp, attempt))
        if K._state_label(doc) != pid or pid not in items:
            raise RuntimeError("%s: the state's label is not the scheduled item %s" % (wf, pid))
        want = K.render_launcher(items[pid], attempt)
        if script != want:
            raise RuntimeError("%s: the state's script is not the renderer's attempt-%d launcher" % (wf, attempt))
        io.open(sp, "wb").write(script.encode("utf-8"))
        got = sha(read(sp))
        if got != sha(script.encode("utf-8")) or got != sha(want.encode("utf-8")):
            raise RuntimeError("%s: the restored launcher does not hash equal" % wf)
        rows.append((order, attempt, pid, wf, sp, got, len(script.encode("utf-8"))))
    return rows


def world():
    import recover_phase1_1488 as A
    placed = A.place_world_without_correction() + A.place_correction() + place_owner(A)
    K, T = A.route()
    placed += place_baseline(K, A)
    T.build_targeted(T.PKG_DIR)                                          # the canonical package the door serves
    if T.package_problems(T.PKG_DIR):
        raise RuntimeError("the canonical package does not rebuild")
    import audit_worker_access as AUD
    return A, K, T, AUD, placed


def install_seam(AUD, sess):
    """Prove the seam: the shared audit resolves a projected state to the frozen parent session."""
    session_dir, session_id = AUD._official_location(sess + "/workflows/" + workflows()[0]["wf"] + ".json")
    if os.path.realpath(session_dir) != os.path.realpath(sess):
        raise RuntimeError("the seam does not resolve the projected session")
    return session_id


def lifecycle(K, T, sess):
    log = []
    r = T.prepare_run(RUN); log.append(("prepare_run", r["ok"], len(r["invocations"]), r["problems"]))
    if not r["ok"]:
        raise RuntimeError("prepare_run refused: %s" % r["problems"][:2])
    for w in workflows():
        if w["attempt"] != "1":
            continue
        bad = K.record_state(RUN, sess + "/workflows/" + w["wf"] + ".json"); log.append(("record_state", w["wf"], bad))
        if bad:
            raise RuntimeError("record_state refused %s: %s" % (w["wf"], bad))
    fin = T.finalize(RUN); log.append(("finalize primary", fin["ledger"], fin.get("retry")))
    retry = RUN + "/retry"
    child = [w for w in workflows() if w["attempt"] == "2"]
    if fin.get("retry"):
        for w in child:
            bad = K.record_state(retry, sess + "/workflows/" + w["wf"] + ".json"); log.append(("record_state child", w["wf"], bad))
            if bad:
                raise RuntimeError("child record_state refused: %s" % bad)
        cfin = T.finalize(retry); log.append(("finalize child", cfin["ledger"], cfin.get("retry")))
    else:
        cfin = None
    return fin, cfin, log


def checks(K, T, fin, cfin):
    rows = []
    rows.append(("primary receipt", sha(read(RUN + "/receipt.json")), PINS["primary_receipt"]))
    rows.append(("primary finalization", sha(read(RUN + "/finalization.json")), PINS["primary_finalization"]))
    rows.append(("primary raw tree (22)", treesha(RUN + "/raw"), PINS["primary_rawtree"])); rows.append(("primary raw files", len(os.listdir(RUN + "/raw")), 22))
    rows.append(("child receipt", sha(read(RUN + "/retry/receipt.json")), PINS["child_receipt"]))
    rows.append(("child finalization", sha(read(RUN + "/retry/finalization.json")), PINS["child_finalization"]))
    rows.append(("child raw tree (2)", treesha(RUN + "/retry/raw"), PINS["child_rawtree"])); rows.append(("child raw files", len(os.listdir(RUN + "/retry/raw")), 2))
    L = fin["ledger"]; rows.append(("primary ledger scheduled/valid/invalid/missing/unproved", (L["scheduled"], L["valid"], L["invalid_response"], L["missing"], L["unproved"]), (11, 10, 1, 0, 0)))
    rows.append(("primary retry keys", list(fin.get("retry") or []), [w["packet_id"] for w in workflows() if w["attempt"] == "2"]))
    C = cfin["ledger"]; rows.append(("child ledger scheduled/valid/invalid", (C["scheduled"], C["valid"], C["invalid_response"]), (1, 0, 1))); rows.append(("child retry (no third attempt)", list(cfin.get("retry") or []), []))
    rows.append(("binding", sha(read(T.BINDING)), PINS["binding"])); bd = json.loads(read(T.BINDING).decode("utf-8")); rows.append(("binding schema", bd["schema"], PINS["binding_schema"])); rows.append(("binding run_dir", bd["run_dir"], RUN))
    spend = T.proved_spend(RUN); rows.append(("proved_spend attempts/calls", [(r["attempt"], r["calls"]) for r in spend], [(1, 11), (2, 1)])); rows.append(("completed calls", sum(r["calls"] for r in spend), 12))
    rows.append(("targeted owner imported", sha(read(T.__file__)), PINS["later_owner"]))
    return [(k, g, w, "ok" if g == w else "DIFF") for k, g, w in rows]


def _rel(p):
    return p[len(ROOT) + 1:] if p.startswith(ROOT + "/") else p.replace(S + "/", "")


def loaded_modules():
    return [(n, _rel(m.__file__), sha(read(m.__file__))) for n, m in sorted(sys.modules.items()) if getattr(m, "__file__", None) and (m.__file__.startswith(S) or m.__file__.startswith(HOME) or m.__file__.startswith(P1))]


def _opened_rows():
    R = os.path.dirname(os.path.dirname(os.path.dirname(HOME)))
    classes = (("unit", HOME), ("phase1", P1), ("regen_1570", R), ("bench", S), ("tmp", "/tmp/"), ("store", SESS))
    rows = []
    for p in sorted({os.path.normpath(p) for p in OPENED if os.path.isfile(p)}):
        cls = next((c for c, pre in classes if p.startswith(pre)), "OUTSIDE")
        rows.append((cls, _rel(p), sha(read(p))))
    return rows


def main(tag):
    out = OUTROOT + "/" + tag; os.makedirs(out, exist_ok=True)
    sys.path.insert(0, P1); sys.path.insert(0, HOME)
    A, K, T, AUD, placed = world()
    # RED: the lifecycle without the twelve copied states cannot finalize a complete run
    r0 = T.prepare_run(S + "/red_run")
    fin0 = T.finalize(S + "/red_run"); red = "RED: finalize with no recorded state -> ledger %s, complete=%s (prepare ok=%s)" % (json.dumps(fin0["ledger"]), fin0.get("primary_complete"), r0["ok"])
    io.open(out + "/red.txt", "w", encoding="utf-8").write(red + "\n"); print(red)
    sess, rows = place_states(); sid = install_seam(AUD, sess)
    items = {i["packet_id"]: i for i in T.targeted_items()}
    launchers = place_launchers(K, items, state_docs(sess), LAUNCH)
    fin, cfin, log = lifecycle(K, T, sess)
    io.open(out + "/LIFECYCLE.txt", "w", encoding="utf-8").write("\n".join(json.dumps(l, default=str) for l in log) + "\n")
    if cfin is None:
        io.open(out + "/RESULT.txt", "w", encoding="utf-8").write("RESULT DIFF: the primary finalization named no child (retry=%s); ledger %s\n" % (fin.get("retry"), json.dumps(fin["ledger"])))
        print("RESULT DIFF: no child; primary ledger", json.dumps(fin["ledger"]), "outcomes", json.dumps(fin.get("outcomes"), default=str)[:600]); return 5
    T.write_binding(RUN)
    ck = checks(K, T, fin, cfin)
    ok = all(c[3] == "ok" for c in ck)
    lines = ["seam: twelve states projected into the masked store at %s; audit session %s == PARENT_SESSION %s" % (SESS, sid, sid == K.PARENT_SESSION),
             "launchers: %d restored under %s" % (len(launchers), LAUNCH)] + ["lifecycle %s" % (json.dumps(l, default=str)[:200]) for l in log]
    lines += ["check %s: %s vs %s %s" % (c[0], str(c[1])[:160], str(c[2])[:160], c[3]) for c in ck] + ["RESULT " + ("MATCH" if ok and sid == K.PARENT_SESSION else "DIFF")]
    io.open(out + "/RESULT.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n"); print("\n".join(lines))
    for base, label in ((RUN, "primary"), (RUN + "/retry", "child")):
        for n in ("receipt.json", "finalization.json"):
            shutil.copyfile(base + "/" + n, out + "/" + label + "." + n)
        os.makedirs(out + "/" + label + "_raw", exist_ok=True)
        for f in os.listdir(base + "/raw"):
            shutil.copyfile(base + "/raw/" + f, out + "/" + label + "_raw/" + f)
    shutil.copyfile(T.BINDING, out + "/targeted_binding.json")
    _tsv(out + "/STATES.tsv", [("order", "attempt", "packet_id", "wf", "world_state_path", "status")] + rows)
    _tsv(out + "/LAUNCHERS.tsv", [("order", "attempt", "packet_id", "wf", "scriptPath", "sha256", "bytes")] + launchers)
    _tsv(out + "/PLACED.tsv", [("path", "sha256")] + placed); _tsv(out + "/CHECKS.tsv", [("check", "got", "want", "status")] + [(c[0], json.dumps(c[1], default=str), json.dumps(c[2], default=str), c[3]) for c in ck])
    _tsv(out + "/DEPENDENCIES.tsv", [("module", "path", "sha256")] + loaded_modules())
    _tsv(out + "/OPENED.tsv", [("class", "path", "sha256")] + _opened_rows())
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
