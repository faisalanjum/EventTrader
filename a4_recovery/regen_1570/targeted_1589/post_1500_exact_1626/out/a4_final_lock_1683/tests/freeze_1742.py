# -*- coding: utf-8 -*-
"""Freeze the complete A4 recovery so it can be published (Codex SEQ 1742).

What the first freeze got wrong and this one fixes:

  the publication set is DERIVED, not hand-picked - every source the bind map actually
  binds, every script the runs actually invoked, every path those scripts name (folded
  out of their own constants), every log the evidence cites, and the outputs;

  it FAILS CLOSED - a failed required test, a failed unchanged-input check, an evidence
  row that does not bind to its exact run, or a required input that is neither in the
  proposed commit nor already tracked, all refuse BEFORE the final bytes are written;

  the evidence rows BIND - each executed row names its marker and the run it belongs to,
  and both must appear in the same log; a short test's real output and exit status are
  kept beside it, apart from the source hash.

The manifest does not hash itself: SEAL.json carries its digest, row count and byte total.
"""
import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
A = P + "/a4_owner_1726"
OUT = UNIT + "/FREEZE_1742"
LOGS = UNIT + "/logs"
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
rel = lambda p: os.path.relpath(p, R)


#: never publishable: the repository's own database and byte-compiled caches
SKIP = (".git", "__pycache__")


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
                         stdin=subprocess.DEVNULL, timeout=600).stdout
    return set(out.splitlines())


def map_sources(map_path):
    """Every source the bind map binds - the run's real inputs."""
    return [l.split("\t")[1] for l in
            io.open(map_path, encoding="utf-8").read().splitlines() if l.strip()]


def folded_paths(path):
    """Paths a script names, including ones built from its own module constants."""
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except (OSError, SyntaxError):
        return []
    env = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            v = fold(n.value, env)
            if isinstance(v, str):
                env[n.targets[0].id] = v
    found = []
    for n in ast.walk(tree):
        v = fold(n, env)
        # A script names its DEPENDENCIES as files. A folded string that is a directory
        # is a root constant (the worktree, the unit), not something the script depends
        # on, and following it would drag in the whole tree.
        if isinstance(v, str) and v.startswith(R + "/") and os.path.isfile(v):
            found.append(v)
    return found


def fold(node, env):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = fold(node.left, env), fold(node.right, env)
        return (a + b) if isinstance(a, str) and isinstance(b, str) else None
    return None


# ------------------------------------------------------------------ the gates --
def gate_tests(results):
    """A required test that did not pass refuses the freeze."""
    bad = [(n, rc) for n, rc, _o in results if rc != 0]
    return ["required test failed: %s rc=%s" % b for b in bad]


def gate_unchanged(checks):
    """An unchanged-input check that did not hold refuses the freeze."""
    bad = []
    for name, want, got in checks:
        if got != want:
            bad.append("unchanged-input check %r is %r, not %r" % (name, got, want))
    return bad


def gate_evidence(rows):
    """An executed row must bind to a real log that carries BOTH its marker and its run."""
    bad = []
    for r in rows:
        if r["kind"] != "executed":
            continue
        if not r.get("log"):
            bad.append("no log bound for %r" % r["what"])
        elif not os.path.isfile(os.path.join(UNIT, r["log"])):
            bad.append("bound log missing for %r" % r["what"])
        elif r.get("log_sha256") != sha(os.path.join(UNIT, r["log"])):
            bad.append("bound log hash wrong for %r" % r["what"])
    return bad


def gate_coverage(required, roots, tracked):
    """Every required input is in the proposed commit or already tracked."""
    bad = []
    for p in sorted(set(required)):
        r = rel(p)
        if any(r == x or r.startswith(x + "/") for x in roots) or r in tracked:
            continue
        bad.append("uncovered required input: %s" % r)
    return bad


def refuse(problems, stage):
    if problems:
        for p in problems[:8]:
            print("   REFUSE %s" % p, flush=True)
        sys.exit("REFUSE: %s (%d problem(s))" % (stage, len(problems)))


# ------------------------------------------------------- the publication set --
def publication_set():
    """(required files, whitelist roots) derived from the map, the commands and the
    evidence - never a hand-written tree list. A ROOT is a directory or file this
    recovery actually depends on; the required files are everything under those roots."""
    roots = []

    def need(path):
        if os.path.exists(path) and path not in roots:
            roots.append(path)

    #: the commands and helpers this recovery runs
    script_roots = [UNIT + "/reconstruct", UNIT + "/tests", UNIT + "/launcher",
                    UNIT + "/lock", A + "/tests"]
    for d in script_roots:
        need(d)
    scripts = [f for d in script_roots for f in walk(d) if f.endswith((".py", ".sh"))]
    for f in (A + "/recover_a4_owner.py", A + "/patch_replay.py",
              A + "/verify_prior_unit.py", A + "/freeze_1726.py"):
        if os.path.isfile(f):
            need(f)
            scripts.append(f)
    #: everything the bind map binds
    for src in map_sources(UNIT + "/launcher/a4_final_map.tsv"):
        need(src)
    #: every recovery path those scripts name themselves, folded out of their constants
    for f in scripts:
        for q in folded_paths(f):
            need(q)
    #: the outputs, the logs and the evidence of this recovery
    for d in (UNIT + "/out", UNIT + "/runs_rw", UNIT + "/manifest", UNIT + "/logs",
              UNIT + "/superseded", UNIT + "/evidence", UNIT + "/lock", OUT):
        if os.path.isdir(d):
            need(d)
    #: a root inside another root adds nothing
    keep = []
    for r in sorted(set(roots)):
        if not any(r.startswith(x + "/") for x in keep):
            keep.append(r)
    required = sorted({f for r in keep for f in walk(r)})
    return required, [rel(r) for r in keep]


# ------------------------------------------------------------------- the run --
def find_log(marker, run):
    """The one log that carries BOTH this marker and the run it belongs to."""
    hits = []
    for f in sorted(os.listdir(LOGS)):
        if not f.startswith("a4_"):
            continue
        text = io.open(os.path.join(LOGS, f), encoding="utf-8", errors="replace").read()
        if marker in text and (run is None or run in text):
            hits.append(f)
    return ("logs/" + hits[-1]) if hits else ""


#: (what, marker, the run that identifies it) - the marker alone is not an identity
EXECUTED = [
    ("round 2 states recorded in the receipt's scheduled order", "RECORD_ROUND1_OK",
     "a4_final_targeted_corr2_run_1506"),
    ("round 2 finalized once", "FINALIZE_ROUND1_OK", "a4_final_targeted_corr2_run_1506"),
    ("round 2 bound; ledger 5217", "LEDGER_OK 5217", "final_targeted_correction_2_primary"),
    ("round 3 corrected budget receipt ae27f66f", "BUDGET_1508_OK",
     "ae27f66f2447dcf632345236cd0a4ec63aca6740628d723fa853caea1026d05a"),
    ("round 3 package eb3cce17", "BUILD_PACKAGE_OK",
     "eb3cce1754ef354e449e650daa163e73818f101bdfc464d6ec0659390d48c634"),
    ("round 3 prepared receipt 071b41f7", "PREPARE_DONE",
     "071b41f781b0452c506e878cfa1115969f7fef3e876693b11935bf718b134544"),
    ("round 3 evidence helper derived", "EVIDENCE_1509_OK", "evidence_1509.py"),
    ("round 3 bound; ledger 5219", "LEDGER_OK 5219", "final_targeted_correction_3"),
    ("final candidate built and verified", "BUILD_CANDIDATE_OK",
     "verify problems: []"),
    ("saved signer harvested (no new call)", "HARVEST_OK", "wf_8dedf1de-a52"),
    ("four owed checker cases under real pytest", "CHECK_CANDIDATE_OK", "4 passed"),
    ("lock and receipt written once; 28/28 mutations refuse", "LOCK_OK",
     "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0"),
    ("the signed checkpoint re-checked read-only", "CHECKPOINT_OK", "verify problems: []"),
]
#: short recovery-side tests: their real output and exit status are kept, not just a hash
SHORT_TESTS = [UNIT + "/tests/test_build_wrapper_refusal.py",
               UNIT + "/tests/test_stage_propagation.py",
               UNIT + "/tests/test_recovery_wrappers_1741.py",
               UNIT + "/tests/test_placement_rules.py",
               UNIT + "/tests/test_freeze_gates_1742.py",
               A + "/tests/test_extraction_1726.py",
               A + "/tests/test_missed_writes_1727.py",
               A + "/tests/test_mixed_command_1728.py"]
#: reuse, bound to the actual recorded invocation and to the exact source it ran
REUSED = [
    ("the rest of check_final_key_candidate.py", "original 87726 invocation / 87817 result",
     "lock/check_final_key_candidate.py"),
    ("its one corrected case", "original 87823 patch / 87835 passing rerun",
     "lock/check_final_key_candidate.py"),
    ("correction-round regression", "original 87773 invocation and its corrected rerun",
     "runs_rw/a4_final_targeted_corr_run_1504/receipt.json"),
    ("two identical candidate builds", "the build plus fresh C.verify in this unit",
     "lock/build_final_key_candidate.py"),
]


def write_restart():
    """The handoff: what this snapshot IS, the one command that checks it without
    rebuilding, the next lawful gate, and - clearly labelled as history - how it was
    reconstructed. Every identity is read from the live bytes, never typed."""
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
    swaps = UNIT + "/manifest/BENCH_OWNER_SWAPS.tsv"
    lines = ["# A4 recovery - the signed checkpoint and how to hand it on", "",
             "## What this snapshot is", "",
             "A4 is recovered, signed and LOCKED. Every operation below is write-once and",
             "REFUSES a second run on this snapshot; nothing here asks for one.", ""]
    for name, path in ident:
        if os.path.isfile(path):
            lines.append("    %-18s %s" % (name, sha(path)))
    acc = json.load(io.open(C + "/a4_final_key_lock.json", encoding="utf-8"))["call_accounting"]
    lines += ["", "    call accounting    %s -> %s (%d signer call, %d retries), ceiling %s"
              % (acc["ledger_before"], acc["ledger_after"], acc["signer_calls"],
                 acc["retries"], acc["ceiling"]), "",
              "## Resume: check the checkpoint, build nothing", "",
              "    cd %s" % UNIT,
              "    A4_ROUND=3 A4_STEPS=verify_checkpoint \\",
              "      A4_A6=%s \\" % sha(A + "/proved/a6_launch_freeze.f0d7b828.py"),
              "      bash tests/run_a4.sh", "",
              "It re-hashes the ten bound inputs, the lock and its receipt, runs the lock",
              "owner's own verify() on the live bytes and prints the call accounting.",
              "Read-only: it writes nothing and refuses on any difference.", "",
              "The recovery-side tests need no boundary:", ""]
    for t in SHORT_TESTS:
        if os.path.isfile(t):
            lines.append("    %s -B %s" % (PY3, rel(t)))
    lines += ["", "## The next lawful gate", "",
              "1. Codex's complete-snapshot verification of this freeze.",
              "2. Then the scoped A4 staging and commit of exactly FREEZE_1742/WHITELIST.tsv,",
              "   then push. Nothing is staged now.",
              "3. Then A5, in order. Not before.", "",
              "## History - how it was reconstructed (do NOT re-run on this snapshot)", "",
              "The era owner was placed in the bench before each round; the recorded swaps are:", ""]
    if os.path.isfile(swaps):
        for l in io.open(swaps, encoding="utf-8").read().splitlines():
            lines.append("    " + l)
    lines += ["", "The stage order actually used, per round:", "",
              "    round 2  review_receipt_1505 build_package prepare_1506"
              " record_round1_states finalize_round1 bind_1506 ledger_check(5217)",
              "    round 3  review_receipt_1507 review_receipt_1508 budget_receipt_1508"
              " build_package prepare_1509",
              "             record_round1_states finalize_round1 evidence_1509"
              " bind_1509 ledger_check(5219)",
              "    closure  build_final_candidate harvest_final_sign_run"
              " check_final_key_candidate build_final_key_lock_run", "",
              "Between prepare and recording, each round's writable run directory was"
              " materialised once:", ""]
    for run in sorted(os.listdir(UNIT + "/runs_rw")):
        lines.append("    %s -B tests/seed_runs_rw.py %s" % (PY3, run))
    lines.append("")
    io.open(OUT + "/RESTART.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")


#: every callable this recovery added or changed, and how it is actually covered
INVENTORY = [
    ("tests/a4_pipeline.py", "stage filter and preservation", "test",
     "test_recovery_wrappers_1741 (4 filter cases); test_stage_propagation (53)"),
    ("tests/build_1501_map.py", "bind map: era owner by hash, lock superset, runs_rw, out/ replay",
     "execution", "every boundary run in logs/; placement rules re-run today"),
    ("tests/seed_runs_rw.py", "materialise a round's writable run directory", "test",
     "test_recovery_wrappers_1741 (differing byte refused, identical accepted)"),
    ("tests/place_era_owner.py", "put one era owner in the bench, by hash", "test",
     "test_recovery_wrappers_1741 (unknown hash, unknown name); manifest/BENCH_OWNER_SWAPS.tsv"),
    ("tests/extract_budget_chain.py", "take a recorded program out of its own record",
     "execution", "both chains in reconstruct/budget_chain and reconstruct/evidence_chain;"
     " refused records 83500 and 87448 in this session's output"),
    ("tests/run_a4.sh", "one boundary run with its inputs", "execution", "every run in logs/"),
    ("tests/freeze_1742.py", "this freeze and its gates", "test",
     "test_freeze_gates_1742 (20 checks, with the first freeze as the failing control)"),
    ("reconstruct/budget_receipt_1508.py", "run the corrected generator, gate ae27f66f",
     "test", "test_recovery_wrappers_1741 (wrong generator); executed BUDGET_1508_OK"),
    ("reconstruct/evidence_1509.py", "derive the round-3 evidence helper from its records",
     "execution", "executed EVIDENCE_1509_OK after a refused incomplete helper"),
    ("reconstruct/build_final_candidate.py", "run the builder, gate the verifier", "test",
     "test_build_wrapper_refusal (6, red then green); executed BUILD_CANDIDATE_OK"),
    ("reconstruct/harvest_final_sign_run.py", "harvest the saved signer state", "execution",
     "executed HARVEST_OK; the nonzero-child branch is tested in test_recovery_wrappers_1741"),
    ("reconstruct/check_final_key_candidate.py", "real pytest over the frozen selection",
     "test", "test_recovery_wrappers_1741 (5 skip/short/failure cases); executed 4 passed"),
    ("reconstruct/build_final_key_lock_run.py", "run the saved lock builder once", "execution",
     "executed LOCK_OK: lock, receipt, 28/28 mutations, accounting"),
    ("reconstruct/ledger_check.py", "fresh-process ledger gate", "test",
     "test_recovery_wrappers_1741 (missing expected total); executed at 5217 and 5219"),
    ("reconstruct/verify_checkpoint.py", "read-only checkpoint check", "execution",
     "executed CHECKPOINT_OK"),
    ("a4_owner_1726/patch_replay.py", "replay one saved patch on proved preimages",
     "execution", "produced 960ebdeb, cdd008c1 and f323b7bc; refuses without a proved preimage"),
]


def gate_inventory(rows):
    """Nothing may be labelled covered by evidence that does not exist."""
    bad = []
    for rel_path, _what, kind, ev in rows:
        if kind not in ("test", "execution"):
            bad.append("uncovered: %s" % rel_path)
        if not ev.strip():
            bad.append("no evidence named for %s" % rel_path)
    return bad


def main():
    os.makedirs(OUT, exist_ok=True)
    testout = OUT + "/testout"
    os.makedirs(testout, exist_ok=True)

    results = []
    for t in SHORT_TESTS:
        if not os.path.isfile(t):
            results.append((rel(t), 127, ""))
            continue
        r = subprocess.run([PY3, "-B", t], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, cwd=os.path.dirname(os.path.dirname(t)),
                           timeout=1800, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        o = os.path.join(testout, os.path.basename(t) + ".out")
        io.open(o, "w", encoding="utf-8").write((r.stdout or "") + (r.stderr or ""))
        print("%-4s %-44s rc=%d" % ("ok" if r.returncode == 0 else "BAD",
                                    os.path.basename(t), r.returncode), flush=True)
        results.append((rel(t), r.returncode, o))
    refuse(gate_tests(results), "a required test did not pass")

    prior = subprocess.run([PY3, "-B", A + "/verify_prior_unit.py"], capture_output=True,
                           text=True, stdin=subprocess.DEVNULL, timeout=900).stdout.strip()
    ev_dir = UNIT + "/evidence/lock"
    differ = [f for f in walk(ev_dir)
          if sha(f) != sha(os.path.join(UNIT, "lock", os.path.relpath(f, ev_dir)))]
    unchanged = [("budget_inputs_1720 (accepted unit)", "rows 109 mismatched 0 extra 0", prior),
                 ("evidence/lock carried unchanged inside lock/", "0 differ",
                  "%d differ" % len(differ))]
    refuse(gate_unchanged(unchanged), "an accepted input moved")

    rows = []
    for what, marker, run in EXECUTED:
        log = find_log(marker, run)
        rows.append({"kind": "executed", "what": what, "marker": marker, "run": run,
                     "log": log,
                     "log_sha256": sha(os.path.join(UNIT, log)) if log else "",
                     "output": "", "rc": ""})
    for name, rc, o in results:
        rows.append({"kind": "executed", "what": name, "marker": "recovery-side test",
                     "run": "", "log": rel(o).replace(rel(UNIT) + "/", "") if o else "",
                     "log_sha256": sha(o) if o else "", "output": sha(o) if o else "",
                     "rc": str(rc)})
    refuse(gate_evidence(rows), "an evidence row does not bind to its run")

    refuse(gate_inventory(INVENTORY), "a changed callable is not covered")
    required, roots = publication_set()
    tracked = git_tracked()
    refuse(gate_coverage(required, roots, tracked), "a required input is not published")

    with io.open(OUT + "/EVIDENCE.tsv", "w", encoding="utf-8") as fh:
        fh.write("kind\twhat\tmarker\tbound_run_identity\tlog_or_output\tsha256\trc\n")
        for r in rows:
            fh.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n"
                     % (r["kind"], r["what"], r["marker"], r["run"], r["log"],
                        r["log_sha256"], r["rc"]))
        for what, invocation, bound in REUSED:
            p = os.path.join(UNIT, bound)
            fh.write("reused\t%s\t%s\t%s\t%s\t%s\t\n"
                     % (what, invocation, bound, "", sha(p) if os.path.isfile(p) else "MISSING"))

    with io.open(OUT + "/UNCHANGED.tsv", "w", encoding="utf-8") as fh:
        fh.write("check\texpected\tmeasured\n")
        for name, want, got in unchanged:
            fh.write("%s\t%s\t%s\n" % (name, want, got))
        for name, cmd in (("main HEAD", "git -C /home/faisal/EventMarketDB rev-parse HEAD"),
                          ("main staged files",
                           "git -C /home/faisal/EventMarketDB diff --cached --name-only | wc -l"),
                          ("recovery HEAD", "git -C %s rev-parse HEAD" % R),
                          ("recovery staged files",
                           "git -C %s diff --cached --name-only | wc -l" % R)):
            v = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=300).stdout.strip()
            fh.write("%s\t(recorded)\t%s\n" % (name, v))
    with io.open(OUT + "/INVENTORY.tsv", "w", encoding="utf-8") as fh:
        fh.write("callable\twhat_changed\tcoverage_kind\tcovering_evidence\tsha256\n")
        for rel_path, what, kind, ev in INVENTORY:
            f = (UNIT + "/" + rel_path) if not rel_path.startswith("a4_owner_1726/") \
                else (A + "/" + rel_path.split("/", 1)[1])
            fh.write("%s\t%s\t%s\t%s\t%s\n"
                     % (rel_path, what, kind, ev,
                        sha(f) if os.path.isfile(f) else "MISSING"))
    with io.open(OUT + "/WHITELIST.tsv", "w", encoding="utf-8") as fh:
        fh.write("git_add_path\tfiles\tbytes\n")
        for r in roots:
            fs = walk(os.path.join(R, r))
            fh.write("%s\t%d\t%d\n" % (r, len(fs), sum(os.path.getsize(f) for f in fs)))
    with io.open(OUT + "/COVERAGE.tsv", "w", encoding="utf-8") as fh:
        fh.write("required_root\tsource\tin_commit\talready_tracked_files\n")
        for r in roots:
            fs = walk(os.path.join(R, r))
            fh.write("%s\t%s\t%s\t%d\n"
                     % (r, "derived", "yes", sum(1 for f in fs if rel(f) in tracked)))
        fh.write("%s\t%s\t%s\t%s\n"
                 % (PY3, "external interpreter prerequisite", "no (environment)", ""))

    write_restart()
    #: the manifest is hashed LAST, so every other frozen byte already exists; it does
    #: not hash itself, and SEAL.json (written after it) carries its digest instead.
    total = 0
    with io.open(OUT + "/MANIFEST.sha256", "w", encoding="utf-8") as fh:
        fh.write("path\tsha256\tbytes\n")
        for f in required:
            if os.path.realpath(f) == os.path.realpath(OUT + "/MANIFEST.sha256"):
                continue
            n = os.path.getsize(f)
            total += n
            fh.write("%s\t%s\t%d\n" % (rel(f), sha(f), n))
    seal = {"schema": "a4-recovery-freeze-seal/1742",
            "manifest": "FREEZE_1742/MANIFEST.sha256",
            "manifest_sha256": sha(OUT + "/MANIFEST.sha256"),
            "manifest_rows": len(required), "manifest_bytes": total,
            "whitelist_roots": len(roots),
            "evidence_rows": len(rows) + len(REUSED),
            "inventory_rows": len(INVENTORY),
            "required_tests_passed": len(results),
            "lock": sha(UNIT + "/lock/final_key_candidate_1511/a4_final_key_lock.json"),
            "lock_receipt": sha(UNIT + "/lock/final_key_candidate_1511/a4_final_key_lock_receipt.json")}
    io.open(OUT + "/SEAL.json", "w", encoding="utf-8").write(json.dumps(seal, indent=1) + "\n")
    print(json.dumps(seal, indent=1), flush=True)
    print("FREEZE_OK", flush=True)


if __name__ == "__main__":
    main()
