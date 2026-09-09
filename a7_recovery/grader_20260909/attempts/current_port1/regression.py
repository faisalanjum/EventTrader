# -*- coding: utf-8 -*-
"""ONE SIDE of the aligned affected regression (Codex SEQ 1955 item 3).

Run once per comparison side, against the SAME served fixture, with only the
changed owners differing. The saved 1925 baseline is a different fixture
(101 packets / 202 calls) and is NOT reused for id comparison; the matching
baseline is established here, once, by running this same payload against the
pre-change owner tree.

Two earlier defects are fixed here rather than repeated:
  * the module set is the DEDUPLICATED UNION and is run ONCE. The
    changed-owner set is contained in the raw_transport set, so running both
    lists ran the same tests twice.
  * the input record is compared SYMMETRICALLY. Adding descriptive plan
    counts to one snapshot and not the other made a file-stability check that
    could never pass.
"""
import ast, collections, hashlib, io, json, os, subprocess, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
VIEW = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
ATT = os.environ["A7_ATTEMPT_DIR"]; os.makedirs(ATT, exist_ok=True)
TAG = os.environ["A7_TAG"]
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery")
sys.path.insert(0, VIEW)
#: THE OWNERS THIS UNIT CHANGED. The two lock_owners files (signer_proof,
#: build_final_key_candidate) are loaded by path from outside this tree and no
#: test module here imports them, so they add nothing to this population; their
#: proof is the executed integration probe, not a collected test.
CHANGED = ("build_inventory_review", "build_kfields_key",
           "build_a5_exp5_kit", "audit_worker_access",
           "build_launch_manifest", "build_kfields_final",
           "build_kfields_hard_review", "g1_fake_state")
FIXTURES = ("test_a5_route_1406", "test_harness_guards")
EXCLUDED = ()


def sha(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def artifacts():
    """The SAME keys on both sides, always - no side-only extras."""
    import build_launch_manifest as BLM
    out = collections.OrderedDict()
    for name in ("launch_kfields_drafts.manifest.json",
                 "launch_kfields_a1.bundle.json", "raw_transport.py",
                 "a7_reference_inventory.py", "a7_g1_build.py",
                 "test_a5_route_1406.py", "test_harness_guards.py"):
        p = os.path.join(VIEW, name)
        out[name] = sha(p) if os.path.isfile(p) else None
    out["inventory"] = sha(BLM.INVENTORY)
    return out


import build_launch_manifest as BLM                              # noqa: E402
res = collections.OrderedDict(tag=TAG, kind="ALIGNED_SIDE")
res["environment"] = {k: os.environ.get(k) for k in (
    "A7_APPROVED_KEY_DIR", "A7_TRACE_FIXTURE", "A7_FIXTURE_PROJECTS",
    "A7_RUN_BINDING", "A7_LANE_INPUT_PROFILES", "A7_DRIVER_VALIDATORS_SHA",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS")}
res["artifacts_before"] = artifacts()
dest = BLM.build()
plan = json.load(io.open(dest, encoding="utf-8"))
res["artifacts_after_build"] = artifacts()
# descriptive, recorded APART from the compared snapshot
res["plan_counts"] = {"n_packets": plan.get("n_packets"),
                      "n_calls": plan.get("n_calls")}
res["inventory_sha256"] = res["artifacts_after_build"]["inventory"]

_mods = {n[:-3]: os.path.join(VIEW, n) for n in os.listdir(VIEW)
         if n.endswith(".py")}
_imports = {}
for _name, _path in _mods.items():
    _got = set()
    for _node in ast.walk(ast.parse(io.open(_path, encoding="utf-8").read(),
                                    _name)):
        if isinstance(_node, ast.Import):
            _got |= {a.name for a in _node.names if a.name in _mods}
        elif isinstance(_node, ast.ImportFrom) and _node.module in _mods:
            _got.add(_node.module)
    _imports[_name] = _got


def reaches(name, targets, seen=None):
    seen = seen or set()
    if name in seen:
        return False
    seen.add(name)
    if set(_imports.get(name, ())) & set(targets):
        return True
    return any(reaches(m, targets, seen) for m in _imports.get(name, ()))


def tests_reaching(targets):
    return set(n for n in _mods if n.startswith("test_")
               and (n in targets or reaches(n, targets)) and n not in EXCLUDED)


comparable = tests_reaching(("raw_transport",))
affected = tests_reaching(CHANGED)
fixture_side = tests_reaching(FIXTURES)
union = sorted(n + ".py" for n in (comparable | affected | fixture_side))
selected = os.environ.get("A7_TESTS")
if selected:
    union = json.loads(selected)
else:
    union = sorted(n + ".py" for n in _mods if n.startswith("test_"))
res["comparable"] = len(comparable)
res["changed_owner_affected"] = len(affected)
res["fixture_dependent"] = len(fixture_side)
res["affected_minus_comparable"] = sorted(affected - comparable)
res["fixture_minus_comparable"] = sorted(fixture_side - comparable)
res["union_modules"] = union
res["union_size"] = len(union)

command = [sys.executable, "-m", "pytest", "-q", "--no-header",
           "-rfE", "-p", "no:cacheprovider", "--basetemp", ATT + "/pytest"] + union
collected = subprocess.run(command + ["--collect-only"],
                           cwd=VIEW, capture_output=True, text=True)
with io.open(os.path.join(ATT, "COLLECTION.txt"), "x", encoding="utf-8") as fh:
    fh.write(collected.stdout + "\n--- stderr ---\n" + collected.stderr)
res["command"] = command
res["collection_exit"] = collected.returncode
out = subprocess.run(command,
                     cwd=VIEW, capture_output=True, text=True)
ids, errors = [], []
for line in (out.stdout or "").splitlines():
    for verb in ("FAILED ", "ERROR "):
        if line.startswith(verb):
            got = line[len(verb):].split(" - ", 1)[0].strip()
            ids.append(got)
            if verb == "ERROR ":
                errors.append(got)
            break
res["child_exit"] = out.returncode
res["failed_ids"] = sorted(set(ids))
res["failed_id_count"] = len(set(ids))
res["collection_errors"] = sorted(set(errors))
tail = [l for l in (out.stdout or "").strip().splitlines() if l][-1:]
res["summary"] = tail[0] if tail else ""
res["artifacts_after_run"] = artifacts()
res["artifacts_stable"] = (res["artifacts_after_run"]
                           == res["artifacts_after_build"])

io.open(os.path.join(ATT, "IDS_%s.txt" % TAG), "w", encoding="utf-8").write(
    "\n".join(sorted(set(ids))) + "\n")
io.open(os.path.join(ATT, "REGRESSION_%s.txt" % TAG), "w",
        encoding="utf-8").write((out.stdout or "") + "\n--- stderr ---\n"
                                + (out.stderr or ""))
io.open(os.path.join(ATT, "ALIGNED_%s.json" % TAG), "w",
        encoding="utf-8").write(json.dumps(res, indent=2, default=str) + "\n")
print("  union %d modules (comparable %d, changed-owner %d, fixture %d)"
      % (res["union_size"], res["comparable"], res["changed_owner_affected"],
         res["fixture_dependent"]))
print("  plan %s/%s  inventory %s"
      % (res["plan_counts"]["n_packets"], res["plan_counts"]["n_calls"],
         res["inventory_sha256"][:16]))
print("  child exit %d  unique ids %d  collection errors %d  stable %s"
      % (res["child_exit"], res["failed_id_count"],
         len(res["collection_errors"]), res["artifacts_stable"]))
print("  %s" % res["summary"])
sys.exit(out.returncode)
