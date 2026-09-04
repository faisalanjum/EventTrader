# -*- coding: utf-8 -*-
"""RECOVERY ADAPTER for the candidate_v2_1488 correction unit (Codex SEQ 1594, 1597). NOT an owner.

Inside a fresh private projected world it (1) places the exact 1487 owner and the exact v1 seam at
their historical scratch paths, the committed locator receipt at the owner's constant path and the
verified reviewed reconciliation at the seam's constant path (the projected f104 copy set aside,
unaltered), (2) runs the exact 1487 owner as history ran it (the red/control), (3) replays the two
recorded transcript patches verbatim to derive the 1488 owner and requires its historical hash,
(4) imports the 1488 owner through the exact historical route recorded at transcript line 79488
and calls its build (the green), freezing every module actually loaded, (5) derives the binding
checks from the output bytes and exports everything. Nothing is hand-built.
"""
import collections, hashlib, io, json, os, shutil, subprocess, sys

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
LOCK = S + "/lock"
RUN = S + "/invrev_run4"
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
H = X + "/harness_g1v3"
HOME = os.environ["CORR_1488_HOME"]
OUTROOT = HOME + "/out/attempt3_exact_recon"
R = os.path.abspath(HOME + "/../..")                                 # regen_1570
PINS = json.load(io.open(HOME + "/pins_1594.json", encoding="utf-8"))
LOC = json.load(io.open(os.path.dirname(HOME) + "/locator_1486/pins_1592.json", encoding="utf-8"))
RECON = json.load(io.open(HOME + "/reconciliation_1342/pins_1596.json", encoding="utf-8"))
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
OWNER = LOCK + "/build_final_lock_v2.py"
OUTPUTS = ("final_inventory.json", "adjudication_sidecar.json", "validator_receipt.json", "correction_receipt.json")


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


def place_world():
    """The historical scratch state the owners read, from committed, verified or recorded bytes only."""
    rows = []
    for name in ("build_final_lock.py", "build_final_lock_v2.py"):
        _cp(HOME + "/owner_1487/" + name, LOCK + "/" + name); rows.append(("lock/" + name, sha(read(LOCK + "/" + name))))
    if sha(read(OWNER)) != PINS["owner_1487_sha256"]:
        raise RuntimeError("the 1487 owner is not the exact bytes Codex named")
    rp = [l for l in io.open(OWNER, encoding="utf-8") if l.startswith("RECEIPT_PATH = ")][0].split('"')[1]
    src = os.path.dirname(HOME) + "/locator_1486/out/a7_source_locator_audit_1486.recovered.json"
    if sha(read(src)) != LOC["target_file_sha256"]:
        raise RuntimeError("the committed locator receipt is not the verified bytes")
    _cp(src, rp); rows.append((rp, sha(read(rp))))
    # THE VERIFIED REVIEWED RECONCILIATION at the seam's constant path; the projected f104 copy set aside, unaltered
    rc = HOME + "/reconciliation_1342/out/A/reconciliation_final.replayed.json"
    if sha(read(rc)) != RECON["target_json_sha256"]:
        raise RuntimeError("the recovered reconciliation is not the verified bytes")
    dst = RUN + "/reconciliation_final.json"; aside = RUN + "/projected_f104"; os.makedirs(aside, exist_ok=True)
    rows.append(("invrev_run4/reconciliation_final.json (projected, set aside)", sha(read(dst)))); shutil.move(dst, aside + "/reconciliation_final.json")
    _cp(rc, dst); rows.append(("invrev_run4/reconciliation_final.json (verified 1342 replay)", sha(read(dst))))
    for name in ("harness/raw_transport.py", "harness_g1v3/raw_transport.py", "harness_g1v3/validate_benchmark_inventory.py", "harness_g1v3/build_kfields_key.py", "one_item_benchmark_inventory.json"):
        rows.append((name, sha(read(X + "/" + name))))
    return rows


def run_owner_script(log_name):
    """The exact 1487 route: cd lock && python3 -B build_final_lock_v2.py (transcript line 79030)."""
    p = subprocess.run([PY, "-B", "build_final_lock_v2.py"], cwd=LOCK, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    os.makedirs(OUTROOT, exist_ok=True)
    io.open(OUTROOT + "/" + log_name, "w", encoding="utf-8").write("rc=%d\n--- stdout\n%s\n--- stderr\n%s" % (p.returncode, p.stdout, p.stderr))
    return p.returncode


def replay_patches():
    """The two recorded transcript patches, executed verbatim; each rewrites the owner first and then
    reaches files outside this unit (absent here), exactly as the recorded commands did."""
    rows = []
    for name, want_line in (("patch_79355_pin_and_bind.py", "build_final_lock_v2.py patched; pin "), ("patch_79488_default_out.py", "L2 DEFAULT_OUT -> candidate_v2_1488")):
        body = read(HOME + "/patches/" + name)
        p = subprocess.run([PY, "-"], input=body, capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        out, err = p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
        first = out.splitlines()[0] if out.strip() else ""
        rows.append((name, sha(body), p.returncode, first, err.strip().splitlines()[-1][:160] if err.strip() else "", sha(read(OWNER))))
        if not first.startswith(want_line):
            raise RuntimeError("%s did not rewrite the owner as recorded: %r" % (name, first))
    got = sha(read(OWNER))
    if got != PINS["owner_1488_sha256"]:
        raise RuntimeError("the replayed owner hashes %s, not the historical %s" % (got, PINS["owner_1488_sha256"]))
    return rows


def historical_import_route():
    """THE ONE import route of the historical 1488 build (transcript line 79488): from harness_g1v3, the
    harness owners first, then the correction owner from the lock. Shared by the green run and the tests."""
    os.chdir(H)
    sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/home/faisal/EventMarketDB")
    import build_kfields_key as K, a6_launch_freeze, a7_g1_build, build_kfields_key_targeted as T   # noqa: F401,E401
    sys.path.insert(0, S + "/lock")
    import build_final_lock_v2 as L2
    if sha(read(L2.__file__)) != PINS["owner_1488_sha256"]:
        raise RuntimeError("the imported correction owner is not the 1488 bytes")
    return L2


def loaded_modules():
    rows = []
    for name, mod in sorted(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and f.startswith(S):
            rows.append((name, f.replace(S + "/", ""), sha(read(f))))
    return rows


def checks(L2, out_dir):
    """The bindings, derived from the output bytes alone."""
    j = lambda n: json.loads(read(out_dir + "/" + n).decode("utf-8"))
    sc, vr, cr = j("adjudication_sidecar.json"), j("validator_receipt.json"), j("correction_receipt.json")
    h = {n: sha(read(out_dir + "/" + n)) for n in OUTPUTS}
    rows = [("sidecar reviewed_reconciliation.sha256", sc["reviewed_reconciliation"]["sha256"], RECON["target_json_sha256"]),
            ("sidecar reviewed_reconciliation.sha256 = placed file", sc["reviewed_reconciliation"]["sha256"], sha(read(L2.L.RECON))),
            ("sidecar source_correction.receipt_file_sha256", sc["source_correction"]["receipt_file_sha256"], LOC["target_file_sha256"]),
            ("sidecar source_correction.receipt_sha256", sc["source_correction"]["receipt_sha256"], LOC["target_receipt_sha256"]),
            ("sidecar source_correction.changes", len(sc["source_correction"]["changes"]), 11),
            ("sidecar rows decision=rebind", sum(1 for r in sc["rows"] if r.get("decision") == "rebind"), 11),
            ("validator problems", vr["problems"], []),
            ("validator module path from harness_g1v3", "harness_g1v3/validate_benchmark_inventory.py" in vr["validator"], True),
            ("correction outputs.final_inventory.json", cr["outputs"]["final_inventory.json"], h["final_inventory.json"]),
            ("correction outputs.adjudication_sidecar.json", cr["outputs"]["adjudication_sidecar.json"], h["adjudication_sidecar.json"]),
            ("correction outputs.validator_receipt.json", cr["outputs"]["validator_receipt.json"], h["validator_receipt.json"]),
            ("correction versioned_inventory_path", cr["versioned_inventory_path"], L2.VERSIONED_INVENTORY),
            ("correction versioned inventory bytes = final_inventory", sha(read(cr["versioned_inventory_path"])), h["final_inventory.json"]),
            ("correction source_receipt.file_sha256", cr["source_receipt"]["file_sha256"], LOC["target_file_sha256"]),
            ("correction source_receipt.receipt_sha256", cr["source_receipt"]["receipt_sha256"], LOC["target_receipt_sha256"]),
            ("correction census", json.dumps(cr["census"], sort_keys=True), json.dumps({"records": 196, "changed_records": 11, "quote": 11, "raw_label_or_claim": 1, "other_fields": 0}, sort_keys=True))]
    return [(k, g, w, "ok" if g == w else "DIFF") for k, g, w in rows]


def main(tag):
    out = OUTROOT + "/" + tag; os.makedirs(out, exist_ok=True)
    placed = place_world()
    rc_red = run_owner_script(tag + "_red_1487.txt")                 # the exact 1487 owner, as history ran it
    patches = replay_patches()
    L2 = historical_import_route()                                    # the exact 1488 owner, through the historical route
    got = L2.build(L2.DEFAULT_OUT, L2.RECEIPT_PATH)                   # the historical call
    io.open(OUTROOT + "/" + tag + "_green_1488.txt", "w", encoding="utf-8").write(json.dumps(got, indent=1))
    mods = loaded_modules()
    want = {"final_inventory.json": PINS["final_inventory"], "adjudication_sidecar.json": PINS["adjudication_sidecar"], "validator_receipt.json": PINS["validator_receipt"], "correction_receipt.json": PINS["correction_receipt"]}
    rec = {l.split("\t")[1].split()[1]: l.split("\t")[1].split()[2] for l in io.open(HOME + "/patches/RECORDED_RESULTS.tsv", encoding="utf-8") if "\t1487 " in l}
    lines, ok = [], rc_red == 0
    for n in OUTPUTS:
        g = sha(read(L2.DEFAULT_OUT + "/" + n)); lines.append("1488 %s got %s want %s %s" % (n, g, want[n], "MATCH" if g == want[n] else "DIFF")); ok = ok and g == want[n]
        r = sha(read(LOCK + "/candidate_v2_1487/" + n)); lines.append("1487 %s got %s recorded %s %s" % (n, r, rec.get(n), "MATCH" if r == rec.get(n) else "DIFF"))
    ck = checks(L2, L2.DEFAULT_OUT); lines += ["check %s: %s vs %s %s" % c for c in ck]; ok = ok and all(c[3] == "ok" for c in ck)
    lines.append("owner 1488 %s want %s %s" % (sha(read(OWNER)), PINS["owner_1488_sha256"], "MATCH" if sha(read(OWNER)) == PINS["owner_1488_sha256"] else "DIFF"))
    lines.append("red rc=%d; loaded modules %d" % (rc_red, len(mods)))
    lines.append("RESULT " + ("MATCH" if ok else "DIFF"))
    for label, d in (("1487", LOCK + "/candidate_v2_1487"), ("1488", L2.DEFAULT_OUT)):
        for n in sorted(os.listdir(d)):
            _cp(d + "/" + n, out + "/candidate_v2_" + label + "/" + n)
    _cp(L2.VERSIONED_INVENTORY, out + "/one_item_benchmark_inventory.v2_1487.json"); _cp(OWNER, out + "/build_final_lock_v2.1488.py"); _cp(L2.L.RECON, out + "/reconciliation_final.placed.json")
    io.open(out + "/RESULT.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    _tsv(out + "/PLACED.tsv", [("path", "sha256")] + placed); _tsv(out + "/PATCHES.tsv", [("patch", "patch_sha256", "rc", "first_stdout_line", "last_stderr_line", "owner_sha256_after")] + patches)
    _tsv(out + "/DEPENDENCIES.tsv", [("module", "path", "sha256")] + mods); _tsv(out + "/CHECKS.tsv", [("check", "got", "want", "status")] + ck)
    print("\n".join(lines))
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
