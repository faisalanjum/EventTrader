# -*- coding: utf-8 -*-
"""GIT-ONLY RESOLUTION, materialized (Codex SEQ 1944 item 2).

The previous check gated `builtins.open` and `io.open`, which importlib does
NOT go through: every "import ok" row was reading the populated working
directory, so it proved nothing about Git. This replaces that claim.

The proposed staged tree is exported with `git archive` into a fresh directory
and every entrypoint is imported and exercised THERE, with the working tree
off `sys.path` and bytecode writing disabled. Each loaded module's `__file__`
must sit inside the export, and its bytes must equal the STAGED BLOB - not
merely some file of the same name.

Sibling reads are exercised, not just imports: the owners hash files beside
themselves, which an import graph never names.

usage: gitonly_check_1944.py <export_dir> <label> [remove_rel ...]
`remove_rel` deletes a file from the export copy first - that is how the
missing-module, missing-sibling-asset and missing-signer negatives are made.
"""
import collections, hashlib, io, json, os, subprocess, sys

R = "/home/faisal/EventMarketDB-driver-recovery"
EXPORT = os.path.abspath(sys.argv[1])
LABEL = sys.argv[2]
REMOVE = list(sys.argv[3:])
V = os.path.join(EXPORT, "a7_recovery/unit_1939/view/tree/harness_g1v3")
LOCKS = os.path.join(EXPORT, "a7_recovery/unit_1939/out_a/lock_owners")
res = collections.OrderedDict(label=LABEL, export=EXPORT, removed=REMOVE)


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


staged = {}
for line in subprocess.run(["git", "-C", R, "ls-files", "-s"],
                           capture_output=True, text=True).stdout.splitlines():
    meta, path = line.split("\t", 1)
    staged[path] = meta.split()[1]
res["staged_entries"] = len(staged)

for rel in REMOVE:
    p = os.path.join(EXPORT, rel)
    if os.path.isfile(p):
        os.remove(p)
res["removed_present_before"] = [r for r in REMOVE]

# THE WORKING TREE IS NOT ON THE PATH. Only the export answers an import.
sys.path = [V, LOCKS, EXPORT] + [p for p in sys.path
                                 if not p.startswith(R) and p]
sys.dont_write_bytecode = True
steps = collections.OrderedDict()
loaded = {}


def step(name, fn):
    try:
        fn()
        steps[name] = "ok"
    except BaseException as exc:                      # noqa: BLE001 - by design
        steps[name] = "%s: %s" % (type(exc).__name__, str(exc)[:150])


def imp(name):
    def go():
        mod = __import__(name)
        loaded[name] = getattr(mod, "__file__", None)
    return go


ENTRIES = ("raw_transport", "a1_reader", "kf_lint", "audit_worker_access",
           "build_launch_manifest", "build_exp5_contract",
           "build_inventory_review", "build_kfields_key",
           "build_kfields_hard_review", "build_kfields_hr_correction",
           "build_kfields_final", "build_a5_exp5_kit", "a6_launch_freeze",
           "a7_prepared_run", "a7_g1_build", "a7_g23_build", "a7_g23_run",
           "a7_g1_complete_v2", "a7_reference_inventory", "a7_key_correction",
           "validate_benchmark_inventory")
for n in ENTRIES:
    step("import " + n, imp(n))

# ---- SIBLING READS, the part imports never cover ------------------------
step("a7_g1_build.owner_hashes (hashes sibling owners)",
     lambda: __import__("a7_g1_build").owner_hashes())
# EVERY SIBLING AN OWNER OPENS BESIDE ITSELF must be present in the export
# and byte-equal to its staged blob. `build_kfields_final.manifest` takes a
# bound argument, so its ten sibling reads are proved by presence and identity
# here rather than by inventing a caller for them; owner_hashes above is the
# live sibling-hashing call.
def _siblings_present():
    spec = json.load(io.open(os.path.join(
        R, "a7_recovery/unit_1943/ALLOWLIST_1944.json"), encoding="utf-8"))
    missing, differing = [], []
    for owner, rels in spec["sibling_reads"].items():
        for rel in rels:
            fp = os.path.join(V, rel)
            key = "a7_recovery/unit_1939/view/tree/harness_g1v3/" + rel
            if not os.path.isfile(fp):
                missing.append("%s -> %s" % (owner, rel))
                continue
            blob = staged.get(key)
            if blob is None:
                differing.append(rel + " (unstaged)")
                continue
            want = subprocess.run(["git", "-C", R, "cat-file", "blob", blob],
                                  capture_output=True).stdout
            if hashlib.sha256(want).hexdigest() != sha(fp):
                differing.append(rel)
    res["sibling_pairs_checked"] = sum(
        len(v) for v in spec["sibling_reads"].values())
    res["siblings_missing"] = missing
    res["siblings_differing"] = differing
    assert not missing and not differing, (missing[:3], differing[:3])


step("every sibling file resolves and matches its blob", _siblings_present)
step("raw_transport.a1_plan_path", lambda: __import__("raw_transport").a1_plan_path())

# ---- THE SIGNER / LOCK OWNERS ------------------------------------------
step("import signer_proof", imp("signer_proof"))
step("import build_final_key_candidate", imp("build_final_key_candidate"))

# ---- THE DYNAMIC SCORER LOAD, through the owner that actually does it ----
# s2_g23_native_1942.py selects scorers/score_exp5_current.py under VIEW and
# hands it to B.bind_grading_scorer with its hash. That is a caller-selected,
# dynamically loaded file: no import statement names it, so the import closure
# never saw it and the earlier 26 checks never exercised this boundary.
SCORER_REL = "scorers/score_exp5_current.py"
SCORER = os.path.join(V, SCORER_REL)
ACCEPTED = "0f769167dcac0bb634e57e6d30a030f569264f8be1c14cd6f83cab0385268e52"


def _bind_the_current_scorer():
    B = __import__("a7_g23_build")
    B.bind_grading_scorer(SCORER, sha(SCORER))
    fields = B.meaning_fields()
    assert fields, "the bound scorer exposes no meaning fields"
    res["scorer_meaning_fields"] = len(fields)


def _scorer_is_the_accepted_bytes():
    got = sha(SCORER)
    res["scorer_sha256"] = got
    assert got == ACCEPTED, (got, ACCEPTED)


step("bind_grading_scorer on the current scorer", _bind_the_current_scorer)
step("the loaded scorer is the accepted bytes", _scorer_is_the_accepted_bytes)

# ---- EVERY project module actually loaded, not just the named list -------
# An owner can insert its own path, so the initial sys.path assignment is not
# the proof. This walks sys.modules AFTER the boundaries have run.
for _n, _m in list(sys.modules.items()):
    if _n == "__main__":
        continue          # this probe itself, which necessarily runs outside
    _f = getattr(_m, "__file__", None)
    if not _f:
        continue
    _fp = os.path.abspath(_f)
    if _fp.startswith(EXPORT + os.sep) or _fp.startswith(R + os.sep):
        loaded.setdefault(_n, _fp)

# ---- every loaded file must be IN the export and equal its staged blob --
outside, mismatched, unstaged = [], [], []
for name, f in sorted(loaded.items()):
    if not f:
        continue
    fp = os.path.abspath(f)
    if not fp.startswith(EXPORT + os.sep):
        outside.append([name, fp])
        continue
    rel = os.path.relpath(fp, EXPORT)
    blob = staged.get(rel)
    if blob is None:
        unstaged.append(rel)
        continue
    want = subprocess.run(["git", "-C", R, "cat-file", "blob", blob],
                          capture_output=True).stdout
    if hashlib.sha256(want).hexdigest() != sha(fp):
        mismatched.append(rel)
res["modules_loaded"] = len(loaded)
res["loaded_outside_the_export"] = outside
res["loaded_but_unstaged"] = unstaged
res["bytes_differ_from_staged_blob"] = mismatched
res["steps"] = steps
res["ok_steps"] = sum(1 for v in steps.values() if v == "ok")
res["total_steps"] = len(steps)
res["all_ok"] = (res["ok_steps"] == res["total_steps"] and not outside
                 and not unstaged and not mismatched)
out = os.path.join(R, "a7_recovery/unit_1943", "GITONLY_%s.json" % LABEL)
io.open(out, "w", encoding="utf-8").write(
    json.dumps(res, indent=2, default=str) + "\n")
print("  %-22s %d/%d ok  loaded %d  outside %d  unstaged %d  mismatch %d"
      % (LABEL, res["ok_steps"], res["total_steps"], res["modules_loaded"],
         len(outside), len(unstaged), len(mismatched)))
for k, v in steps.items():
    if v != "ok":
        print("      FAIL %-46s %s" % (k, v[:90]))
sys.exit(0 if res["all_ok"] else 1)
