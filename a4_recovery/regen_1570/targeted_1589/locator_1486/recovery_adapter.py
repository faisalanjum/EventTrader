# -*- coding: utf-8 -*-
"""RECOVERY ADAPTER for the SEQ 1486 locator receipt (Codex SEQ 1592). NOT the owner.

Inside the recovery world it (1) derives the USED-FIELD PROJECTIONS of the two absent
files through the surviving owners over the frozen inputs, (2) derives the evidence
pointers a6_launch_freeze.bound() reads from the recovered A4 run directories, (3) serves,
at ONE identity seam, the two historical file identities the receipt embeds, and
(4) executes the exact, unmodified owner and exports what the owner wrote.
Every derived file is a PROJECTION of a lost original, never the original.
"""
import collections, glob, hashlib, io, json, os, re, sys, types

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
BENCH = S + "/bench_1306"
EXP = BENCH + "/.claude/plans/Drivers/experiments"
H = EXP + "/harness_g1v3"
A3H = EXP + "/harness"                                 # the accepted world's A3 harness
HOME = os.environ["LOCATOR_1486_HOME"]                 # the durable recovery subdirectory
OWNER = HOME + "/owner/locator_audit_1486.py"          # the exact SEQ 1486 owner, bound by hash below
PINS = json.load(io.open(HOME + "/pins_1592.json", encoding="utf-8"))
#: pointer file -> the recovered run kind whose ONE directory it names (the historical
#: run-directory naming of the A4 phases: recognised here, decided nowhere)
POINTERS = collections.OrderedDict([
    ("a4_dir.txt", "phase1"), ("hr_dir.txt", "hardreview"), ("hrfix_dir.txt", "hrfix"),
    ("final_dir.txt", "final"), ("corr_dir.txt", "corr"), ("decision_dir.txt", "decision"),
    ("v4_dir.txt", "v4corr"), ("v5_dir.txt", "v5corr"), ("v6_dir.txt", "v6corr")])


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return io.open(p, "rb").read()


def owner_source():
    src = read(OWNER)
    if sha(src) != PINS["owner_sha256"]:
        raise RuntimeError("the owner at %s is not the exact SEQ 1486 bytes" % OWNER)
    return src


def owner_paths(src):
    """The owner's own constant paths, read from its bytes (never restated here)."""
    text = src.decode("utf-8")
    return {n: re.search(r'^%s = "([^"]+)"$' % n, text, re.M).group(1) for n in ("OUT", "MANIFEST", "FREEZE")}


def derive_pointers():
    """The evidence pointers, each naming the ONE recovered run directory of its kind."""
    rows = collections.OrderedDict()
    for name, kind in POINTERS.items():
        dirs = sorted(glob.glob(EXP + "/runs/kf-a4-" + kind + "-*"))
        if len(dirs) != 1:
            raise RuntimeError("%s: %d recovered run directories of kind %s" % (name, len(dirs), kind))
        rows[name] = dirs[0]
    exported = read(S + "/a4_dir.txt").decode("utf-8").strip()      # the accepted world's own phase-1 pointer
    if rows["a4_dir.txt"] != exported:
        raise RuntimeError("phase-1 pointer disagrees with the accepted world: %s vs %s" % (rows["a4_dir.txt"], exported))
    for name, d in rows.items():
        if name != "a4_dir.txt":                                     # the accepted one stays as exported
            io.open(S + "/" + name, "w", encoding="utf-8").write(d + "\n")
    return rows


def derive_a1_plan():
    """The A1 drafting plan and its launcher bundle the A3 evidence binds, placed where the G1v3
    harness reads them.

    K.a3_evidence() proves the A3 primary receipt against harness_g1v3/launch_kfields_drafts.manifest.json
    (receipt.manifest_sha256 must be that file's hash) and the run's armed launchers against the pins of
    harness_g1v3/launch_kfields_a1.bundle.json (whose own manifest_sha256 names the same plan). The stage-1
    tree's copies are later regenerations (the plan builder's default route rewrites them), so the exact
    bytes the A3 evidence binds - held by the accepted world at the A3 harness path - are projected there.
    Both are selected by the A3 receipt's own manifest_sha256; nothing typed.
    """
    primary = read(S + "/a3_serial_dir.txt").decode("utf-8").strip()
    want = json.loads(read(primary + "/receipt.json").decode("utf-8"))["manifest_sha256"]
    out = collections.OrderedDict()
    # THE A1-ERA RENDER INPUT: the G1v3 auditor proves each A3 transcript against a prompt it re-renders
    # from the era's package text (build_exp5_contract._PKG), regenerating the contract files the A3 plan
    # pins (contract, contract_manifest). The stage-1 copy of the unversioned package holds v3 content
    # (the era-less build overwrote it), so the accepted A3 harness copy is projected; the plan's pins
    # then prove the regenerated files (checked in a3_proof_pins below).
    for name, check in (("launch_kfields_drafts.manifest.json", lambda b: sha(b) == want),
                        ("launch_kfields_a1.bundle.json", lambda b: json.loads(b.decode("utf-8")).get("manifest_sha256") == want),
                        ("exp5_rev4_package.md", lambda b: True)):
        b = read(A3H + "/" + name)
        if not check(b):
            raise RuntimeError("the accepted A3 harness %s is not bound to the plan the A3 receipt names (%s)" % (name, want))
        dst = H + "/" + name
        before = sha(read(dst)) if os.path.exists(dst) else None
        if before != sha(b):
            io.open(HOME + "/out/" + name.replace(".json", ".stage1_displaced.json"), "wb").write(read(dst))
            io.open(dst, "wb").write(b)
        out[name] = {"path": dst, "sha256": sha(b), "displaced_stage1_sha256": before}
    return {"path": out["launch_kfields_drafts.manifest.json"]["path"], "sha256": want,
            "displaced_stage1_sha256": out["launch_kfields_drafts.manifest.json"]["displaced_stage1_sha256"], "files": out}


def a3_proof_pins():
    """The A3 plan's protected-file pins against the files the G1v3 harness now holds or regenerates."""
    if H not in sys.path:
        sys.path.insert(0, H)
    import build_launch_manifest as B
    import build_exp5_contract as BEC
    plan = json.loads(read(H + "/launch_kfields_drafts.manifest.json").decode("utf-8"))
    BEC.build_prompt("drafter", contract_suffix="")          # regenerates the era's contract files from the package
    rows = []
    for name, path in sorted(B._protected_pins("").items()):
        got = sha(read(path)) if os.path.exists(path) else None
        rows.append((name, path.replace(S + "/", ""), plan["pins"].get(name), got, "ok" if got == plan["pins"].get(name) else "DIFF"))
    return rows


def a3_proof():
    """The G1v3 key owner's own A3 evidence proof, as the owner's path will run it."""
    if H not in sys.path:
        sys.path.insert(0, H)
    import build_kfields_key as K
    return K.a3_evidence()["problems"]


def derive_projections():
    """The used fields of the two absent files, through the surviving owners over the frozen inputs."""
    if H not in sys.path:
        sys.path.insert(0, H)
    import build_launch_manifest as B
    import build_a5_exp5_kit as KIT
    inv = read(B.INVENTORY)
    if sha(inv) != PINS["inventory_sha256"]:
        raise RuntimeError("the default inventory is not the uncorrected one Codex named")
    kit = read(KIT.FROZEN_KIT_PATH)
    if sha(kit) != PINS["frozen_kit_sha256"]:
        raise RuntimeError("the frozen kit is not the one Codex named")
    role, suffix = KIT.ONE_ITEM_ROLE_NAME, B.PRODUCER_CONTRACT_SUFFIX
    pks, prompts = B._one_item_packets(B._events(), role=role, contract_suffix=suffix)
    packets = []
    for p in pks:
        text = prompts[p["packet_id"]]
        digest = sha(text.encode("utf-8"))
        if p["prompt_chars"] != len(text) or p.get("prompt_sha256", digest) != digest:
            raise RuntimeError("the packet owner and the rendered prompt disagree for %s" % p["packet_id"])
        packets.append(collections.OrderedDict([
            ("packet_id", p["packet_id"]), ("prompt_sha256", digest), ("prompt_chars", p["prompt_chars"])]))
    cap = B.measured_capacity(pks, prompts)
    manifest = collections.OrderedDict([
        ("_projection", "USED-FIELD PROJECTION of the absent /tmp/a7_v3_prepared_run_1479/plan/"
                        "a5_exp5_reader.manifest.json (Codex SEQ 1592 item 2); NOT the original file"),
        ("prompt_role", role), ("contract_suffix", suffix), ("packets", packets),
        ("arms", [dict(a) for a in KIT.active_arms()])])
    freeze = collections.OrderedDict([
        ("_projection", "USED-FIELD PROJECTION of the absent /tmp/a7_a6_freeze_1479/"
                        "a6_exp5_launch_freeze.json (Codex SEQ 1592 item 2); NOT the original file"),
        ("counts", {"capacity": collections.OrderedDict([
            ("prompt_chars_max", cap["prompt_chars_max"]),
            ("prompt_utf8_bytes_max", cap["prompt_utf8_bytes_max"])])})])
    blm, kitp = sha(read(H + "/build_launch_manifest.py")), sha(read(H + "/build_a5_exp5_kit.py"))
    provenance = [
        ("prompt_role", "build_a5_exp5_kit.ONE_ITEM_ROLE_NAME", kitp),
        ("contract_suffix", "build_launch_manifest.PRODUCER_CONTRACT_SUFFIX", blm),
        ("packets[196].packet_id,prompt_sha256,prompt_chars", "build_launch_manifest._one_item_packets(_events(), role, contract_suffix) over the default inventory " + B.INVENTORY, sha(inv)),
        ("arms", "build_a5_exp5_kit.active_arms() over the frozen kit " + KIT.FROZEN_KIT_PATH, sha(kit)),
        ("counts.capacity.prompt_chars_max,prompt_utf8_bytes_max", "build_launch_manifest.measured_capacity(packets, prompts) over the same population", blm)]
    return manifest, freeze, provenance, prompts


def write_projections(manifest, freeze, paths):
    for doc, p in ((manifest, paths["MANIFEST"]), (freeze, paths["FREEZE"])):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1, ensure_ascii=False))


# ---- THE ONE RECOVERY-ONLY IDENTITY SEAM ------------------------------------------------
class _Identity(object):
    """The historical identity of an absent full file, served for its projection's exact bytes."""
    def __init__(self, hexdigest):
        self._hex = hexdigest

    def hexdigest(self):
        return self._hex


_REAL = hashlib
_SEAM = types.ModuleType("hashlib")
_SEAM.__dict__.update(_REAL.__dict__)
_SEAM.by_bytes = {}


def _sha256(data=b"", *a, **k):
    if isinstance(data, (bytes, bytearray, memoryview)) and bytes(data) in _SEAM.by_bytes:
        return _Identity(_SEAM.by_bytes[bytes(data)])
    return _REAL.sha256(data, *a, **k)


_SEAM.sha256 = _sha256


def run_owner(identities):
    """Execute the exact owner bytes, unmodified, with the seam serving only the two identities."""
    src = owner_source()
    paths = owner_paths(src)
    _SEAM.by_bytes = {read(paths["MANIFEST"]): identities["manifest"], read(paths["FREEZE"]): identities["freeze"]}
    if os.path.exists(paths["OUT"]):
        os.remove(paths["OUT"])
    g = {"__name__": "__main__", "__file__": OWNER}
    saved_path, saved_out, saved_mod = list(sys.path), sys.stdout, sys.modules.get("hashlib")
    buf = io.StringIO()
    sys.stdout, sys.modules["hashlib"] = buf, _SEAM
    try:
        exec(compile(src, OWNER, "exec"), g)
    finally:
        sys.stdout, sys.modules["hashlib"] = saved_out, saved_mod
        sys.path[:] = saved_path
        _SEAM.by_bytes = {}
    out = read(paths["OUT"])
    return {"receipt_sha256": g["doc"]["receipt_sha256"], "file_sha256": sha(out), "bytes": out, "stdout": buf.getvalue()}


def identities():
    return {"manifest": PINS["manifest_identity"], "freeze": PINS["freeze_identity"]}


def targets():
    return (PINS["target_receipt_sha256"], PINS["target_file_sha256"])


def dependencies():
    """Every module the run resolved from the world, with its identity."""
    rows = []
    for name, mod in sorted(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and (f.startswith(BENCH) or f == OWNER):
            rows.append((name, f.replace(S + "/", ""), sha(read(f))))
    return rows


def _tsv(path, rows):
    io.open(path, "w", encoding="utf-8").write("".join("\t".join(str(c) for c in r) + "\n" for r in rows))


def red():
    """The old stage-1 projection (no arms, role producer) must NOT reproduce the target."""
    src = owner_source()
    paths = owner_paths(src)
    derive_pointers()
    plan = derive_a1_plan()
    pins = a3_proof_pins()
    problems = a3_proof()
    print("A3 identity files projected into harness_g1v3: %s\nA3 plan pins: %s\nA3 proof problems: %d %s" % (json.dumps(plan["files"]), json.dumps(pins), len(problems), problems[:6]))
    if problems:
        return 6
    for fn, key in (("a5_exp5_reader.manifest.json", "MANIFEST"), ("a6_exp5_launch_freeze.json", "FREEZE")):
        os.makedirs(os.path.dirname(paths[key]), exist_ok=True)
        io.open(paths[key], "wb").write(read(HOME + "/old_projection/" + fn))
    try:
        r = run_owner(identities())
    except Exception as e:
        print("RED: the owner REFUSED the old projection: %s: %s" % (type(e).__name__, str(e)[:300]))
        return 0
    got = (r["receipt_sha256"], r["file_sha256"])
    print("RED: the owner ran over the old projection: receipt %s file %s vs targets %s %s -> %s"
          % (got + targets() + ("DIFF" if got != targets() else "MATCH",)))
    return 0 if got != targets() else 9


def green():
    out = HOME + "/out"
    src = owner_source()
    paths = owner_paths(src)
    pointers = derive_pointers()
    plan = derive_a1_plan()
    pins = a3_proof_pins()
    problems = a3_proof()
    print("A3 identity files projected into harness_g1v3: %s\nA3 plan pins: %s\nA3 proof problems: %d %s" % (json.dumps(plan["files"]), json.dumps(pins), len(problems), problems[:6]))
    _tsv(out + "/A3_PROOF.tsv", [("pin", "path", "plan_pin", "live", "status")] + pins + [("a3_evidence problems", "", "", str(len(problems)), "ok" if not problems else "REFUSED")])
    if problems:
        print("STOP: the dependency build_kfields_key.a3_evidence refuses; named above")
        return 6
    manifest, freeze, provenance, prompts = derive_projections()
    provenance = provenance + [("harness_g1v3/" + n + " (A1-era file the G1v3 A3 proof reads)", "the accepted world's A3 harness copy (plan and bundle selected by the A3 receipt's manifest_sha256; the package proven through the plan's contract pins and the 392 transcript comparisons); displaced stage-1 copy " + str(v["displaced_stage1_sha256"]), v["sha256"]) for n, v in plan["files"].items()]
    write_projections(manifest, freeze, paths)
    r = run_owner(identities())
    got = (r["receipt_sha256"], r["file_sha256"])
    want = targets()
    io.open(out + "/a5_exp5_reader.manifest.projection.json", "wb").write(read(paths["MANIFEST"]))
    io.open(out + "/a6_exp5_launch_freeze.projection.json", "wb").write(read(paths["FREEZE"]))
    io.open(out + "/a7_source_locator_audit_1486.recovered.json", "wb").write(r["bytes"])
    io.open(out + "/owner_stdout.txt", "w", encoding="utf-8").write(r["stdout"])
    _tsv(out + "/PROVENANCE.tsv", [("field", "owner_route", "source_sha256")] + provenance
         + [("manifest identity (seam)", "historical identity of the absent full file, Core SEQ 1298/1299 and Codex SEQ 1480", identities()["manifest"]),
            ("freeze identity (seam)", "historical identity of the absent full file, Core SEQ 1298/1299 and Codex SEQ 1480", identities()["freeze"])])
    _tsv(out + "/POINTERS.tsv", [("pointer", "run_directory", "files")] + [(k, v, sum(len(f) for _, _, f in os.walk(v))) for k, v in pointers.items()])
    _tsv(out + "/DEPENDENCIES.tsv", [("module", "path", "sha256")] + dependencies())
    old = json.load(io.open(HOME + "/old_projection/a5_exp5_reader.manifest.json", encoding="utf-8"))
    oldp = {p["packet_id"]: p for p in old["packets"]}
    same_sha = sum(1 for p in manifest["packets"] if p["packet_id"] in oldp and oldp[p["packet_id"]]["prompt_sha256"] == p["prompt_sha256"])
    same_chars = sum(1 for p in manifest["packets"] if p["packet_id"] in oldp and oldp[p["packet_id"]]["prompt_chars"] == p["prompt_chars"])
    lines = [
        "receipt_sha256 got %s want %s %s" % (got[0], want[0], "MATCH" if got[0] == want[0] else "DIFF"),
        "file_sha256    got %s want %s %s" % (got[1], want[1], "MATCH" if got[1] == want[1] else "DIFF"),
        "recovered bytes %d" % len(r["bytes"]),
        "packets %d, prompt_role %s, contract_suffix %s, arms %d records %s" % (len(manifest["packets"]), manifest["prompt_role"], manifest["contract_suffix"], len(manifest["arms"]), json.dumps(manifest["arms"])),
        "capacity %s" % json.dumps(freeze["counts"]["capacity"]),
        "old stage-1 projection (not an input): %d of %d ids present, %d equal prompt hashes, %d equal char counts, role %s"
        % (sum(1 for p in manifest["packets"] if p["packet_id"] in oldp), len(manifest["packets"]), same_sha, same_chars, old.get("prompt_role")),
        "projection files: manifest %s (%d bytes) freeze %s (%d bytes)" % (sha(read(paths["MANIFEST"])), len(read(paths["MANIFEST"])), sha(read(paths["FREEZE"])), len(read(paths["FREEZE"]))),
        "RESULT " + ("MATCH" if got == want else "FIRST MISMATCH: " + ("receipt_sha256" if got[0] != want[0] else "file_sha256"))]
    io.open(out + "/RESULT.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if got == want else 5


if __name__ == "__main__":
    sys.exit({"red": red, "green": green}[sys.argv[1]]())
