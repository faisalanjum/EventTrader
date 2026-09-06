# -*- coding: utf-8 -*-
"""Freeze the complete A4 recovery for publication (Codex SEQ 1743).

Corrections over FREEZE_1742, all at the same owner:

  no circular checksum - the manifest lists neither itself nor the seal, it is written
  after every other named byte, the seal is written from the rows actually written, and
  the finished result is read back and rehashed before this claims success;

  real dependencies - the required set is derived independently of the proposed commit:
  the bind map, the two finite accepted manifests, and the IMPORT closure of the commands
  (a module imported from a directory the script puts on sys.path is a dependency, which
  is how budget_inputs_1720/owner_derive is covered);

  evidence bound to its actual operation - each executed row names its own log, and the
  marker AND the identities it must contain are checked inside that log; the reuse rows
  carry the exact transcript records, extracted and rehashed here;

  gates that check the stated condition - a nonzero return code, an absent required file,
  a marker that is not in the log, and a file too large for the remote all refuse.
"""
import ast
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
A = P + "/a4_owner_1726"
PRIOR = P + "/budget_inputs_1720"
OUT = UNIT + "/FREEZE_1743"
LOGS = UNIT + "/logs"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
TRANSCRIPT = R + "/a3_recovery/regen_1541/evidence/transcript/accepted_prefix.jsonl"
#: the transcript is far too large for the remote, so the package carries a LOSSLESS
#: compressed copy of it and proves the copy decompresses to the original's bytes
TRANSCRIPT_GZ = UNIT + "/evidence/transcript/accepted_prefix.jsonl.gz"
#: github.com refuses a push carrying a file above this size
REMOTE_FILE_LIMIT = 100 * 1024 * 1024
SKIP = (".git", "__pycache__")

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
rel = lambda p: os.path.relpath(p, R)


def walk(root):
    if os.path.isfile(root):
        return [root]
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP]
        out += [os.path.join(dp, f) for f in sorted(fn) if not f.endswith(".pyc")]
    return out


def git_tracked():
    out = subprocess.run(["git", "-C", R, "ls-files"], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL, timeout=900).stdout
    return set(out.splitlines())


def fold(node, env):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = fold(node.left, env), fold(node.right, env)
        return (a + b) if isinstance(a, str) and isinstance(b, str) else None
    return None


def deps_of(path):
    """(files this script names, directories it puts on the import path, modules it imports)."""
    if not path.endswith(".py"):
        return [], [], []          # only a python source has imports to follow
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except (OSError, SyntaxError, UnicodeDecodeError):
        return [], [], []
    env = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            v = fold(n.value, env)
            if isinstance(v, str):
                env[n.targets[0].id] = v
    files, dirs, mods = [], [], []
    for n in ast.walk(tree):
        v = fold(n, env)
        if isinstance(v, str) and v.startswith(R + "/"):
            if os.path.isfile(v):
                files.append(v)
            elif os.path.isdir(v):
                dirs.append(v)
        if isinstance(n, ast.Import):
            mods += [a.name.split(".")[0] for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            mods.append(n.module.split(".")[0])
    return files, dirs, mods


def import_closure(scripts):
    """Every recovery file the commands actually reach, by name or by import."""
    seen, queue, found = set(), list(scripts), []
    while queue:
        p = queue.pop()
        if p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        found.append(p)
        files, dirs, mods = deps_of(p)
        for f in files:
            queue.append(f)
        for d in dirs:
            for mname in mods:
                cand = os.path.join(d, mname + ".py")
                if os.path.isfile(cand):
                    queue.append(cand)
    return found


def manifest_files(manifest_path, base):
    """Every path a finite accepted manifest lists (existing or not - absence must refuse)."""
    rows = io.open(manifest_path, encoding="utf-8").read().splitlines()[1:]
    return [os.path.join(base, l.split("\t")[0]) for l in rows if l.strip()]


# ------------------------------------------------------------------ the gates --
def gate_tests(results):
    return ["required test failed: %s rc=%s" % (n, rc) for n, rc, _o in results if rc != 0]


def gate_unchanged(checks):
    """(name, expected, measured, returncode) - both the text and the code must hold."""
    bad = []
    for name, want, got, rc in checks:
        if rc != 0:
            bad.append("unchanged-input check %r returned %s" % (name, rc))
        if got != want:
            bad.append("unchanged-input check %r is %r, not %r" % (name, got, want))
    return bad


def gate_evidence(rows):
    """An executed row must name a real log whose bytes are the recorded ones and which
    actually carries its marker and every identity it claims."""
    bad = []
    for r in rows:
        if r.get("kind") != "executed":
            continue
        what, log = r.get("what"), r.get("log") or ""
        p = os.path.join(UNIT, log)
        if not log:
            bad.append("no log bound for %r" % what)
            continue
        if not os.path.isfile(p):
            bad.append("bound log missing for %r" % what)
            continue
        if r.get("log_sha256") != sha(p):
            bad.append("bound log hash wrong for %r" % what)
            continue
        text = io.open(p, encoding="utf-8", errors="replace").read()
        if r.get("marker") and r["marker"] not in text:
            bad.append("marker %r is not in the log bound to %r" % (r["marker"], what))
        for ident in (r.get("must_contain") or ([r["run"]] if r.get("run") else [])):
            if ident and ident not in text:
                bad.append("identity %r is not in the log bound to %r" % (ident, what))
        for art, want in (r.get("artifacts") or []):
            q = os.path.join(UNIT, art)
            if not os.path.isfile(q):
                bad.append("artifact of %r is absent: %s" % (what, art))
            elif sha(q) != want:
                bad.append("artifact of %r is not %s: %s" % (what, want[:16], art))
    return bad


def gate_coverage(required, roots, tracked, prereq):
    """Every required input must EXIST and be either in the proposed commit, already
    tracked, or preserved in it losslessly (prereq carries those, with their proof)."""
    bad = []
    for p in sorted(set(required)):
        if not os.path.isfile(p):
            bad.append("required input is absent: %s" % rel(p))
            continue
        r = rel(p)
        if r in prereq or r in tracked:
            continue
        if any(r == x or r.startswith(x + "/") for x in roots):
            continue
        bad.append("uncovered required input: %s" % r)
    return bad


def gate_preserved(preserved):
    """A file too large to publish raw is preserved only if its compressed copy really
    decompresses to the original's bytes."""
    bad = []
    for orig, d in preserved.items():
        gz = os.path.join(R, d["gz"])
        if not os.path.isfile(gz):
            bad.append("the preserved copy of %s is absent" % orig)
            continue
        h, n = hashlib.sha256(), 0
        with gzip.open(gz, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 22), b""):
                h.update(b)
                n += len(b)
        if h.hexdigest() != d["sha256"] or n != d["bytes"]:
            bad.append("the preserved copy of %s decompresses to %s (%d bytes)"
                       % (orig, h.hexdigest()[:16], n))
    return bad


def gate_size(files, limit=REMOTE_FILE_LIMIT):
    return ["too large to publish (%d bytes): %s" % (os.path.getsize(f), rel(f))
            for f in files if os.path.isfile(f) and os.path.getsize(f) > limit]


def gate_inventory(rows):
    bad = []
    for rel_path, _what, kind, ev in rows:
        if kind not in ("test", "execution"):
            bad.append("uncovered: %s" % rel_path)
        if not ev.strip():
            bad.append("no evidence named for %s" % rel_path)
    return bad


def refuse(problems, stage):
    if problems:
        for p in problems[:8]:
            print("   REFUSE %s" % p, flush=True)
        sys.exit("REFUSE: %s (%d problem(s))" % (stage, len(problems)))


# ------------------------------------------------------------- what was done --
#: the complete identity of what a stage wrote, proved against the artifact itself -
#: the log carries the short form, the file carries the whole one
ARTIFACTS = {
    "round 2 states recorded and finalized once": [
        ("runs_rw/a4_final_targeted_corr2_run_1506/receipt.json",
         "281811031aeb9a50346ccd13b9261979f68b882802d4754347f1e906d43d421c"),
        ("runs_rw/a4_final_targeted_corr2_run_1506/finalization.json",
         "ee6aaa97556b1aa5e5145c998b26f01e1045f3bd7ec792a748c6992f354c9303")],
    "round 3 states recorded and finalized once": [
        ("runs_rw/a4_final_targeted_corr3_run_1509/receipt.json",
         "268f55910d888ced32895f4ed3337146090dc66137f408f11d80e8b136cde1dd"),
        ("runs_rw/a4_final_targeted_corr3_run_1509/finalization.json",
         "603be212f3320a21c74ebedd44a16bb8495b8c2a2e17c128d3cb3c050ffa2fc9")],
    "lock and receipt written once": [
        ("lock/final_key_candidate_1511/a4_final_key_lock.json",
         "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0"),
        ("lock/final_key_candidate_1511/a4_final_key_lock_receipt.json",
         "7f1f7bef4d02b9c5501d9ec6d8d5b9eab5e8aab225092878b7280964bd5d44e3")],
}

#: (what, log, marker, identities that must appear in THAT log, note)
EXECUTED = [
    ("round 2 states recorded and finalized once",
     "logs/a4_20260905T230912.log", "FINALIZE_ROUND1_OK",
     ["281811031aeb9a50", "ee6aaa97556b1aa5", "a4_final_targeted_corr2_run_1506"],
     "the FIRST stage pair of this log; the same log then repeats the two local stages and"
     " the second finalization REFUSES, because a finalized run is never finalized twice"),
    ("round 2 bound; ledger 5217", "logs/a4_20260905T232316.log", "LEDGER_OK 5217",
     ["final_targeted_correction_2_primary 2", "fe3e6e03f9444aa2"], ""),
    ("round 3 corrected budget receipt", "logs/a4_20260905T235533.log", "BUDGET_1508_OK",
     ["ae27f66f2447dcf632345236cd0a4ec63aca6740628d723fa853caea1026d05a",
      "43cb623295a4a2dc328ab61980bf4e5357a86fba5aec0a6ca02821593c0f3d9c"], ""),
    ("round 3 package", "logs/a4_20260905T235925.log", "BUILD_PACKAGE_OK",
     ["eb3cce1754ef354e449e650daa163e73818f101bdfc464d6ec0659390d48c634",
      "29672e0d91e3d68606fc9dbb53b19f1b2da2f841b8377b475bd6eca2bf780b90"], ""),
    ("round 3 prepared", "logs/a4_20260906T000056.log", "PREPARE_DONE",
     ["071b41f781b0452c506e878cfa1115969f7fef3e876693b11935bf718b134544",
      "ledger 5217"], ""),
    ("round 3 states recorded and finalized once", "logs/a4_20260906T000549.log",
     "FINALIZE_ROUND1_OK",
     ["268f55910d888ced", "603be212f3320a21", "a4_final_targeted_corr3_run_1509"], ""),
    ("round 3 evidence helper derived", "logs/a4_20260906T001302.log", "EVIDENCE_1509_OK",
     ["52b4210a96210283", "agents    rc=0 2"], ""),
    ("round 3 bound; ledger 5219", "logs/a4_20260906T001648.log", "LEDGER_OK 5219",
     ["final_targeted_correction_3_primary 2",
      "6438b015564c8f504511e0619caebb8a1d8f85a7e12dd8b0c8ee22d04b442ef1"], ""),
    ("final candidate built and verified", "logs/a4_20260906T003331.log",
     "BUILD_CANDIDATE_OK",
     ["verify problems: []", "\"rows\": 196", "open_issues 0 tags_below_floor []"],
     "this one build plus its fresh C.verify is the two-identical-builds proof"),
    ("saved signer harvested, no new call", "logs/a4_20260906T005300.log", "HARVEST_OK",
     ["wf_8dedf1de-a52", "signed=True blocked=[]",
      "fd57049fdc9df15247094ec869feba546c2410bd1eea57a7a740543738c86aeb"], ""),
    ("the four owed checker cases under real pytest", "logs/a4_20260906T010803.log",
     "CHECK_CANDIDATE_OK",
     ["4 passed", "dd4e321d7009887da0813fda85badbfe78083f86c887c3283cd277126c48151d"], ""),
    ("lock and receipt written once", "logs/a4_20260906T011110.log", "LOCK_OK",
     ["63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0",
      "7f1f7bef4d02b9c5501d9ec6d8d5b9eab5e8aab225092878b7280964bd5d44e3",
      "mutations 28/28 refused"], ""),
    ("the signed checkpoint re-checked read-only", "logs/a4_20260906T013007.log",
     "CHECKPOINT_OK", ["verify problems: []", "5219", "5220"], ""),
]
#: the reuse, as the exact transcript records - extracted and rehashed here
#: the recovered sources the reused suites actually ran, before and after their patch
SUITES = {
    "checker": {
        "before": "28646d249e08726e497fd32c2e0d43cdaaf5c96b9e157e0e7c3613d29db4c0b5",
        "after": "dd4e321d7009887da0813fda85badbfe78083f86c887c3283cd277126c48151d",
        "source": UNIT + "/lock/check_final_key_candidate.py",
        "cases": 13, "executed_today": 4, "reused": 9,
        "changed": "test_the_composed_row_maps_are_exported_by_the_composition_owner"
                   "_and_verified_independently"},
    "correction suite": {
        "before": "bb50489c2bcb62bd32ed18f143c6d0110277f45418c66b9c91a1c6bbc1616538",
        "after": "a3fb098e3a144ba03536d94e2959b3ed64d8b04c85f829b479a20c576fad727c",
        "source": os.path.dirname(P) + "/post_1500_closure_1624/replay/scratch"
                                       "/test_a4_third_correction_1508.py",
        "cases": 17, "executed_today": 0, "reused": 17,
        "changed": "test_run_1506_is_bound_once_and_counted_by_its_own_owner"},
}
REUSED_RECORDS = [
    (87726, "8fa768550041c3ed5ccc54a2a3c48f9da4b67b043c0eb689306bc983b18123a3",
     "invocation that starts BOTH suites"),
    (87817, "1bac8fdcd604ffa4f23241bcc43bc1a8f40809df15358a38410179ae58350684",
     "checker result: 1 failed, 12 passed"),
    (87823, "77976df8c5172c6514160d7e8379e809b4a965197156b5eb41db6b2dc5966d5f",
     "checker patch and rerun"),
    (87835, "0a6e1240911c3afc2de4ab322954860b07d442889cf3ebfbb7dcb3a646f8a14f",
     "checker corrected result: 1 passed, 12 deselected"),
    (87773, "a04cfc10415756061b7c1500c170cc73a4fae3e55377b193e41eebbfd427099f",
     "correction-suite result: 1 failed, 16 passed"),
    (87779, "be23d1d46ad02d414ac52514d855c3d1392534adfb2f5c889095069e3b308571",
     "correction-suite patch and rerun"),
    (87788, "19a318df1e65e808d4754ad511a4c011c88e108270b798ec6d725bc1231e8d99",
     "correction-suite corrected result: 1 passed, 16 deselected, rc0, 218.44s"),
    (87703, "559a85417d6fea15db3b64d351af9b6e5ea35e7475f8135b93bec06257857e8a",
     "the command that adapted the correction suite to the already-closed round"),
    (87711, "a1e39b23f07be04dafdd5174c35e74bb984cc94b1d24c7ea87b53e9fb334b835",
     "its result, printing the pre-run source bb50489c2bcb62bd before invocation 87726"),
]
REUSED = [
    ("checker: 9 of its 13 cases", "records 87726 (invocation), 87817, 87823, 87835",
     "checker"),
    ("correction suite: all 17 cases",
     "records 87703, 87711, 87726 (invocation), 87773, 87779, 87788", "correction suite"),
    ("two identical candidate builds", "logs/a4_20260906T003331.log", None),
]
SHORT_TESTS = [UNIT + "/tests/test_build_wrapper_refusal.py",
               UNIT + "/tests/test_stage_propagation.py",
               UNIT + "/tests/test_recovery_wrappers_1741.py",
               UNIT + "/tests/test_placement_rules.py",
               UNIT + "/tests/test_freeze_gates_1742.py",
               UNIT + "/tests/test_boundary_checks_1743.py",
               UNIT + "/tests/test_handoff_command_1744.py",
               A + "/tests/test_extraction_1726.py",
               A + "/tests/test_missed_writes_1727.py",
               A + "/tests/test_mixed_command_1728.py"]
INVENTORY = [
    ("tests/a4_pipeline.py", "stage filter and preservation", "test",
     "test_recovery_wrappers_1741 (4 filter cases); test_stage_propagation (53)"),
    ("tests/build_1501_map.py", "bind map: era owner by hash, lock superset, runs_rw",
     "execution", "every boundary run in logs/"),
    ("tests/seed_runs_rw.py", "materialise a round's writable run directory", "test",
     "test_recovery_wrappers_1741 (differing byte refused, identical accepted)"),
    ("tests/place_era_owner.py", "put one era owner in the bench, by hash", "test",
     "test_recovery_wrappers_1741 (unknown hash, unknown name)"),
    ("tests/extract_budget_chain.py", "take a recorded program out of its own record",
     "execution", "reconstruct/budget_chain and reconstruct/evidence_chain"),
    ("tests/run_a4.sh", "one boundary run with its inputs", "execution", "every run in logs/"),
    ("tests/freeze_1743.py", "this freeze and its gates", "test",
     "test_boundary_checks_1743 (evidence, unchanged, coverage, prior-unit, harvest)"),
    ("reconstruct/budget_receipt_1508.py", "run the corrected generator, gate ae27f66f",
     "test", "test_recovery_wrappers_1741 (wrong generator); executed BUDGET_1508_OK"),
    ("reconstruct/evidence_1509.py", "derive the round-3 evidence helper", "execution",
     "executed EVIDENCE_1509_OK after a refused incomplete helper"),
    ("reconstruct/build_final_candidate.py", "run the builder, gate the verifier", "test",
     "test_build_wrapper_refusal (6 cases, red then green)"),
    ("reconstruct/harvest_final_sign_run.py", "harvest the saved signer state", "test",
     "test_boundary_checks_1743 exercises THIS wrapper's own nonzero-child seam;"
     " executed HARVEST_OK"),
    ("reconstruct/check_final_key_candidate.py", "real pytest over the frozen selection",
     "test", "test_recovery_wrappers_1741 (5 skip/short/failure cases)"),
    ("reconstruct/build_final_key_lock_run.py", "run the saved lock builder once",
     "execution", "executed LOCK_OK"),
    ("reconstruct/ledger_check.py", "fresh-process ledger gate", "test",
     "test_recovery_wrappers_1741 (missing expected total)"),
    ("reconstruct/verify_checkpoint.py", "read-only checkpoint check", "execution",
     "executed CHECKPOINT_OK"),
    ("a4_owner_1726/patch_replay.py", "replay one saved patch on proved preimages",
     "execution", "produced 960ebdeb, cdd008c1 and f323b7bc"),
    ("a4_owner_1726/verify_prior_unit.py", "the accepted unit is exactly its manifest",
     "test", "test_boundary_checks_1743 (a deleted listed file now refuses)"),
]


def bound_identity(test):
    """The identity of a test AND of the files it names, so a cached result is reused only
    while the code it actually tested is unchanged."""
    h = hashlib.sha256(sha(test).encode())
    for f in sorted(set(deps_of(test)[0])):
        h.update(("%s:%s" % (rel(f), sha(f))).encode())
    return h.hexdigest()


def run_short_tests():
    """Run a short test only when its source changed since the captured result."""
    testout = OUT + "/testout"
    os.makedirs(testout, exist_ok=True)
    prev = {}
    rp = testout + "/RESULTS.tsv"
    if os.path.isfile(rp):
        for l in io.open(rp, encoding="utf-8").read().splitlines()[1:]:
            c = l.split("\t")
            if len(c) >= 5:
                prev[c[0]] = (c[1], int(c[2]), c[3], c[4])
    results, rows = [], []
    for t in SHORT_TESTS:
        r_t, src = rel(t), bound_identity(t) if os.path.isfile(t) else ""
        o = os.path.join(testout, os.path.basename(t) + ".out")
        old = prev.get(r_t)
        if old and old[0] == src and os.path.isfile(o) and sha(o) == old[3]:
            print("%-4s %-44s rc=%d (reused, source unchanged)"
                  % ("ok" if old[1] == 0 else "BAD", os.path.basename(t), old[1]), flush=True)
            results.append((r_t, old[1], o))
            rows.append((r_t, src, old[1], os.path.basename(o), old[3]))
            continue
        r = subprocess.run([PY3, "-B", t], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL,
                           cwd=os.path.dirname(os.path.dirname(t)), timeout=1800,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        io.open(o, "w", encoding="utf-8").write((r.stdout or "") + (r.stderr or ""))
        print("%-4s %-44s rc=%d (ran)" % ("ok" if r.returncode == 0 else "BAD",
                                          os.path.basename(t), r.returncode), flush=True)
        results.append((r_t, r.returncode, o))
        rows.append((r_t, src, r.returncode, os.path.basename(o), sha(o)))
    with io.open(rp, "w", encoding="utf-8") as fh:
        fh.write("test\ttest_and_tested_sha256\trc\toutput_file\toutput_sha256\n")
        for x in rows:
            fh.write("%s\t%s\t%d\t%s\t%s\n" % x)
    return results


def required_inputs():
    """Derived independently of the proposed commit."""
    req = []
    scripts = [f for d in (UNIT + "/reconstruct", UNIT + "/tests", UNIT + "/launcher",
                           UNIT + "/lock", A + "/tests")
               for f in walk(d) if f.endswith((".py", ".sh"))]
    scripts += [A + "/recover_a4_owner.py", A + "/patch_replay.py",
                A + "/verify_prior_unit.py"]
    req += import_closure([f for f in scripts if os.path.isfile(f)])
    for l in io.open(UNIT + "/launcher/a4_final_map.tsv", encoding="utf-8").read().splitlines():
        if l.strip():
            req += walk(l.split("\t")[1])
    req += manifest_files(PRIOR + "/MANIFEST_g23.sha256", PRIOR)
    req += [PRIOR + "/MANIFEST_g23.sha256"]
    if os.path.isfile(A + "/MANIFEST_1726.sha256"):
        req += manifest_files(A + "/MANIFEST_1726.sha256", A) + [A + "/MANIFEST_1726.sha256"]
    for what, log, _m, _ids, _n in EXECUTED:
        req.append(os.path.join(UNIT, log))
    #: the recovered sources the reused suites ran
    for d in SUITES.values():
        if os.path.isfile(d["source"]):
            req.append(d["source"])
    #: the derivation evidence of the owners this recovery reproduced
    for d in (UNIT + "/out", UNIT + "/runs_rw", UNIT + "/manifest", UNIT + "/logs",
              UNIT + "/superseded", UNIT + "/evidence", UNIT + "/lock", OUT,
              A + "/patches", A + "/proved"):
        if os.path.isdir(d):
            req += walk(d)
    return sorted({f for f in req})


def commit_roots(required, prereq):
    """The smallest cover of the REQUIRED files: a directory becomes a root only when
    every file under it is required, otherwise its required files are named one by one.
    Nothing is included because it happens to sit next to something required."""
    req = {rel(f) for f in required} - set(prereq)
    tops, roots = set(), []
    for r in req:
        parts = r.split("/")
        tops.add("/".join(parts[:6]) if len(parts) > 6 else r)

    def visit(d):
        files = walk(os.path.join(R, d))
        if not files:
            return
        rels = [rel(f) for f in files]
        if all(x in req for x in rels):
            roots.append(d)
            return
        if not any(x in req for x in rels):
            return
        full = os.path.join(R, d)
        for entry in sorted(os.listdir(full)):
            if entry in SKIP:
                continue
            q = os.path.join(full, entry)
            if os.path.isdir(q):
                visit(rel(q))
            elif rel(q) in req:
                roots.append(rel(q))

    for t in sorted(tops):
        if os.path.isdir(os.path.join(R, t)):
            visit(t)
        elif t in req:
            roots.append(t)
    keep = []
    for r in sorted(set(roots)):
        if not any(r.startswith(x + "/") for x in keep):
            keep.append(r)
    return keep


def write_restart(seal_note):
    C = UNIT + "/lock/final_key_candidate_1511"
    ident = [("lock", C + "/a4_final_key_lock.json"),
             ("lock receipt", C + "/a4_final_key_lock_receipt.json"),
             ("key identity", C + "/key_identity.json"),
             ("sidecar", C + "/sidecar.json"),
             ("provenance", C + "/provenance.json"),
             ("validator receipt", C + "/validator_receipt.json"),
             ("signer prompt", C + "/signer/signer_prompt.txt"),
             ("signer launcher", C + "/signer/final_sign.attempt1.js"),
             ("signer manifest", C + "/signer/signer.manifest.json"),
             ("signer raw", C + "/signer/final_sign.attempt1.raw.json"),
             ("signer evidence", C + "/signer/final_sign.attempt1.evidence.json"),
             ("signer reply", C + "/signer/final_sign.attempt1.reply.json"),
             ("round 1 binding", UNIT + "/out/scratch__final_targeted_corr_binding.json"),
             ("round 2 binding", UNIT + "/out/scratch__final_targeted_corr2_binding.json"),
             ("round 3 binding", UNIT + "/out/scratch__final_targeted_corr3_binding.json")]
    acc = json.load(io.open(C + "/a4_final_key_lock.json", encoding="utf-8"))["call_accounting"]
    L = ["# A4 recovery - the signed checkpoint and how to hand it on", "",
         "## What this snapshot is", "",
         "A4 is recovered, signed and LOCKED. Every build, harvest and lock operation is",
         "write-once and REFUSES a second run on this snapshot.", ""]
    for name, path in ident:
        if os.path.isfile(path):
            L.append("    %-18s %s" % (name, sha(path)))
    L += ["", "    call accounting    %s -> %s (%d signer call, %d retries), ceiling %s"
          % (acc["ledger_before"], acc["ledger_after"], acc["signer_calls"],
             acc["retries"], acc["ceiling"]),
          "    %s" % seal_note, "",
          "## Check the checkpoint (builds nothing, changes no frozen byte)", "",
          "    cd %s" % UNIT,
          "    A4_ROUND=3 A4_STEPS=verify_checkpoint \\",
          "      A4_A6=%s \\" % sha(A + "/proved/a6_launch_freeze.f0d7b828.py"),
          "      bash tests/run_a4.sh", "",
          "It re-hashes the ten bound inputs, the lock and its receipt, runs the lock",
          "owner's own verify() on the live bytes and prints the call accounting.",
          "",
          "WHAT THAT COMMAND WRITES, exactly - it is read-only about the ANSWER, not about",
          "the run's own bookkeeping:",
          "",
          "    logs/a4_<timestamp>.log        a NEW file each time",
          "    launcher/a4_final_map.tsv      rebuilt from the same sources (re-measured)",
          "    out/ARTIFACTS.tsv              rewritten by the preservation step",
          "",
          "Nothing else changes: the candidate, the signer packet, the lock, the receipt,",
          "the bindings, the run directories and every earlier log stay byte-identical, so",
          "the manifest rows for those three bookkeeping files are the only ones expected",
          "to move. To check without writing anything at all, verify the manifest instead:",
          "",
          "    %s -B - <<'EOF'" % PY3,
          "    import hashlib, io",
          "    R = '%s'" % R,
          "    man = '%s/MANIFEST.sha256'" % rel(OUT),
          "    bad = 0",
          "    for line in io.open(R + '/' + man, encoding='utf-8').read().splitlines()[1:]:",
          "        path, want, _n = line.split('\\t')",
          "        got = hashlib.sha256(io.open(R + '/' + path, 'rb').read()).hexdigest()",
          "        bad += (got != want)",
          "    print('manifest rows checked, mismatched', bad)",
          "    raise SystemExit(1 if bad else 0)",
          "    EOF", "",
          "## If the original transcript is ever missing", "",
          "The package carries a lossless gzip of it; the original is left untouched. This",
          "restores it only when it is absent, and never over anything:", "",
          "    T=%s" % TRANSCRIPT,
          "    GZ=%s" % TRANSCRIPT_GZ,
          "    if [ -e \"$T\" ]; then echo \"present - leaving it alone\"; else \\",
          "      gunzip -c \"$GZ\" > \"$T.restored\" && \\",
          "      sha256sum \"$T.restored\" && \\",
          "      echo \"expect %s\" && \\" % sha(TRANSCRIPT),
          "      mv -n \"$T.restored\" \"$T\"; fi", "",
          "## The recovery-side tests (absolute paths; no boundary needed)", ""]
    for t in SHORT_TESTS:
        if os.path.isfile(t):
            L.append("    %s -B %s" % (PY3, t))
    L += ["", "## The next lawful gate", "",
          "1. Codex verifies this complete snapshot.",
          "2. Then staging only, of exactly the roots in FREEZE_1743/WHITELIST.tsv, for his",
          "   staged-identity review; then the scoped commit and the normal push.",
          "3. Then A5, in order. Nothing is staged now.", "",
          "## History - how it was reconstructed. DO NOT RE-RUN on this snapshot.", "",
          "The completed operations refuse a second run; these lines record what happened.", ""]
    swaps = UNIT + "/manifest/BENCH_OWNER_SWAPS.tsv"
    if os.path.isfile(swaps):
        for l in io.open(swaps, encoding="utf-8").read().splitlines():
            L.append("    " + l)
    L += ["",
          "    round 2  review_receipt_1505 build_package prepare_1506"
          " record_round1_states finalize_round1 bind_1506 ledger_check(5217)",
          "    round 3  review_receipt_1507 review_receipt_1508 budget_receipt_1508"
          " build_package prepare_1509",
          "             record_round1_states finalize_round1 evidence_1509"
          " bind_1509 ledger_check(5219)",
          "    closure  build_final_candidate harvest_final_sign_run"
          " check_final_key_candidate build_final_key_lock_run", ""]
    for run in sorted(os.listdir(UNIT + "/runs_rw")):
        L.append("    %s -B %s/tests/seed_runs_rw.py %s" % (PY3, UNIT, run))
    L.append("")
    io.open(OUT + "/RESTART.md", "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    #: the handoff is one of the things under test, so it is written before the tests run;
    #: the manifest still comes last, after every other named byte has settled
    write_restart("manifest and seal: see FREEZE_1743/SEAL.json")
    results = run_short_tests()
    refuse(gate_tests(results), "a required test did not pass")

    pr = subprocess.run([PY3, "-B", A + "/verify_prior_unit.py"], capture_output=True,
                        text=True, stdin=subprocess.DEVNULL, timeout=900)
    ev_dir = UNIT + "/evidence/lock"
    differ = [f for f in walk(ev_dir)
              if sha(f) != sha(os.path.join(UNIT, "lock", os.path.relpath(f, ev_dir)))]
    unchanged = [("budget_inputs_1720 (accepted unit)",
                  "rows 109 mismatched 0 extra 0 missing 0", pr.stdout.strip().splitlines()[0]
                  if pr.stdout.strip() else "", pr.returncode),
                 ("evidence/lock carried unchanged inside lock/", "0 differ",
                  "%d differ" % len(differ), 0)]
    refuse(gate_unchanged(unchanged), "an accepted input moved")

    # the reuse records, extracted from the accepted prefix and rehashed here
    recdir = OUT + "/reused_records"
    os.makedirs(recdir, exist_ok=True)
    lines = io.open(TRANSCRIPT, encoding="utf-8", errors="replace").readlines()
    recs, bad = [], []
    for n, want, what in REUSED_RECORDS:
        b = lines[n - 1].encode("utf-8", "replace")
        got = hashlib.sha256(b).hexdigest()
        p = os.path.join(recdir, "record_%d.jsonl" % n)
        io.open(p, "wb").write(b)
        if got != want or sha(p) != want:
            bad.append("record %d is %s, not %s" % (n, got, want))
        recs.append((n, want, what, rel(p), len(b)))
    refuse(bad, "a reuse record is not the recorded byte")

    rows = []
    for what, log, marker, ids, note in EXECUTED:
        p = os.path.join(UNIT, log)
        rows.append({"kind": "executed", "what": what, "log": log, "marker": marker,
                     "must_contain": ids, "note": note,
                     "artifacts": ARTIFACTS.get(what, []),
                     "log_sha256": sha(p) if os.path.isfile(p) else "", "rc": ""})
    for name, rc, o in results:
        rows.append({"kind": "executed", "what": name, "log": rel(o).replace(rel(UNIT) + "/", ""),
                     "marker": "", "must_contain": [], "note": "recovery-side test output",
                     "log_sha256": sha(o) if os.path.isfile(o) else "", "rc": str(rc)})
    refuse(gate_evidence(rows), "an evidence row does not bind to its operation")
    refuse(gate_inventory(INVENTORY), "a changed callable is not covered")

    required = required_inputs()
    preserved = {rel(TRANSCRIPT): {"sha256": sha(TRANSCRIPT),
                                   "bytes": os.path.getsize(TRANSCRIPT),
                                   "gz": rel(TRANSCRIPT_GZ),
                                   "gz_sha256": sha(TRANSCRIPT_GZ),
                                   "gz_bytes": os.path.getsize(TRANSCRIPT_GZ)}}
    refuse(gate_preserved(preserved), "a preserved copy is not lossless")
    prereq = set(preserved)
    tracked = git_tracked()
    roots = commit_roots(required, prereq)
    refuse(gate_coverage(required, roots, tracked, prereq), "a required input is not published")
    committed = sorted({f for r in roots for f in walk(os.path.join(R, r))})
    refuse(gate_size(committed), "a proposed file is too large for the remote")
    #: the commands' own import closure must resolve inside what is published
    reach = import_closure([t for t in SHORT_TESTS if os.path.isfile(t)]
                           + [UNIT + "/reconstruct/verify_checkpoint.py"])
    inset = {rel(f) for f in committed} | tracked | set(prereq)
    refuse([("a required import does not resolve from the publication set: %s" % rel(f))
            for f in reach if rel(f) not in inset],
           "an import of a required command is outside the publication set")

    with io.open(OUT + "/EVIDENCE.tsv", "w", encoding="utf-8") as fh:
        fh.write("kind\twhat\tlog_or_output\tsha256\tmarker\tbound_identities\trc\tnote\n")
        for r in rows:
            fh.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n"
                     % (r["kind"], r["what"], r["log"], r["log_sha256"], r["marker"],
                        " | ".join(r["must_contain"]
                                   + ["%s=%s" % (a, h) for a, h in (r.get("artifacts") or [])]),
                        r["rc"], r["note"]))
        for what, invocation, suite in REUSED:
            if suite is None:
                b = UNIT + "/lock/build_final_key_candidate.py"
                fh.write("reused\t%s\t%s\t%s\t\t\t\t%s\n"
                         % (what, invocation, sha(b), "the builder this reuse binds"))
                continue
            d = SUITES[suite]
            fh.write("reused\t%s\t%s\t%s\t%s\t%s\t\t%s\n"
                     % (what, invocation, sha(d["source"]), "source before " + d["before"],
                        "source after " + d["after"],
                        "%d cases: %d executed today, %d reused; the patch changed only %s"
                        % (d["cases"], d["executed_today"], d["reused"], d["changed"])))
    with io.open(OUT + "/REUSED_RECORDS.tsv", "w", encoding="utf-8") as fh:
        fh.write("record\tsha256\twhat\tpublished_as\tbytes\n")
        for x in recs:
            fh.write("%d\t%s\t%s\t%s\t%d\n" % x)
    with io.open(OUT + "/PRESERVED.tsv", "w", encoding="utf-8") as fh:
        fh.write("original\tsha256\tbytes\tpreserved_as\tgz_sha256\tgz_bytes"
                 "\tdecompresses_to_the_original\twhy\n")
        for r, d in sorted(preserved.items()):
            fh.write("%s\t%s\t%d\t%s\t%s\t%d\tyes (proved by streaming decompression"
                     " in this freeze)\t%s\n"
                     % (r, d["sha256"], d["bytes"], d["gz"], d["gz_sha256"], d["gz_bytes"],
                        "the raw file exceeds the remote's %d-byte per-file limit; the"
                        " lossless copy is published in its place and the original is left"
                        " untouched" % REMOTE_FILE_LIMIT))
        fh.write("%s\t\t\t%s\t\t\t\t%s\n"
                 % (PY3, "(not published)", "environment prerequisite: the interpreter"))
    with io.open(OUT + "/UNCHANGED.tsv", "w", encoding="utf-8") as fh:
        fh.write("check\texpected\tmeasured\treturncode\n")
        for name, want, got, rc in unchanged:
            fh.write("%s\t%s\t%s\t%d\n" % (name, want, got, rc))
        for name, cmd in (("main HEAD", "git -C /home/faisal/EventMarketDB rev-parse HEAD"),
                          ("main staged files",
                           "git -C /home/faisal/EventMarketDB diff --cached --name-only | wc -l"),
                          ("recovery HEAD", "git -C %s rev-parse HEAD" % R),
                          ("recovery staged files",
                           "git -C %s diff --cached --name-only | wc -l" % R)):
            v = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=300).stdout.strip()
            fh.write("%s\t(recorded)\t%s\t0\n" % (name, v))
    with io.open(OUT + "/INVENTORY.tsv", "w", encoding="utf-8") as fh:
        fh.write("callable\twhat_changed\tcoverage_kind\tcovering_evidence\tsha256\n")
        for rel_path, what, kind, ev in INVENTORY:
            f = (UNIT + "/" + rel_path) if not rel_path.startswith("a4_owner_1726/") \
                else (A + "/" + rel_path.split("/", 1)[1])
            fh.write("%s\t%s\t%s\t%s\t%s\n"
                     % (rel_path, what, kind, ev, sha(f) if os.path.isfile(f) else "MISSING"))
    with io.open(OUT + "/WHITELIST.tsv", "w", encoding="utf-8") as fh:
        fh.write("git_add_path\tfiles\tbytes\n")
        for r in roots:
            fs = walk(os.path.join(R, r))
            fh.write("%s\t%d\t%d\n" % (r, len(fs), sum(os.path.getsize(f) for f in fs)))
    with io.open(OUT + "/COVERAGE.tsv", "w", encoding="utf-8") as fh:
        fh.write("required_input\tstate\tdetail\n")
        for f in required:
            r = rel(f)
            if r in prereq:
                state, detail = "preserved", "lossless copy published; see PRESERVED.tsv"
            elif any(r == x or r.startswith(x + "/") for x in roots):
                state, detail = "in_commit", "under a whitelist root"
            else:
                state, detail = "tracked", "already committed"
            fh.write("%s\t%s\t%s\n" % (r, state, detail))
        fh.write("%s\t%s\t%s\n" % (PY3, "environment", "interpreter prerequisite"))
        for r, d in sorted(preserved.items()):
            fh.write("%s\t%s\t%s\n" % (d["gz"], "in_commit",
                                        "the lossless copy of " + r))

    #: the manifest is written after every other named byte and lists neither itself
    #: nor the seal, so nothing in it can change after it is hashed
    man_path, seal_path = OUT + "/MANIFEST.sha256", OUT + "/SEAL.json"
    listed, total = [], 0
    for f in committed:
        if os.path.realpath(f) in (os.path.realpath(man_path), os.path.realpath(seal_path)):
            continue
        n = os.path.getsize(f)
        total += n
        listed.append((rel(f), sha(f), n))
    with io.open(man_path, "w", encoding="utf-8") as fh:
        fh.write("path\tsha256\tbytes\n")
        for x in listed:
            fh.write("%s\t%s\t%d\n" % x)
    seal = {"schema": "a4-recovery-freeze-seal/1743",
            "manifest": rel(man_path), "manifest_sha256": sha(man_path),
            "manifest_rows": len(listed), "manifest_bytes": total,
            "excluded_from_manifest": [rel(man_path), rel(seal_path)],
            "whitelist_roots": len(roots), "required_inputs": len(required),
            "preserved_losslessly": len(preserved), "reused_records": len(recs),
            "evidence_rows": len(rows) + len(REUSED), "inventory_rows": len(INVENTORY),
            "required_tests_passed": len(results),
            "lock": sha(UNIT + "/lock/final_key_candidate_1511/a4_final_key_lock.json"),
            "lock_receipt": sha(UNIT + "/lock/final_key_candidate_1511/a4_final_key_lock_receipt.json")}
    io.open(seal_path, "w", encoding="utf-8").write(json.dumps(seal, indent=1) + "\n")

    # read the finished result back and rehash it before claiming anything
    back = io.open(man_path, encoding="utf-8").read().splitlines()[1:]
    mism = [l.split("\t")[0] for l in back
            if sha(os.path.join(R, l.split("\t")[0])) != l.split("\t")[1]]
    refuse(mism, "the finished manifest does not rehash")
    if len(back) != seal["manifest_rows"] or sha(man_path) != seal["manifest_sha256"]:
        refuse(["the seal does not describe the manifest it sealed"], "the seal is wrong")
    print(json.dumps(seal, indent=1), flush=True)
    print("rehashed %d rows, mismatched 0" % len(back), flush=True)
    print("FREEZE_OK", flush=True)


if __name__ == "__main__":
    main()
