#!/usr/bin/env python3
"""Execute the REAL no-model resume path with every open and import pinned (SEQ 1543).

The callable inventory is derived from the entry point, not hand-listed: this runs
`build_kfields_key.py`'s own `__main__` body - the historical package, the source gap,
materialisation, the lock, the A4 phase-1 door and the A3 probe - and an audit hook
records every file the run actually touches.

The gate is not "did it finish" but "did it stay inside the package": any read that
resolves into the dirty main checkout, or into a file this package does not manifest,
is a FAILURE even when the run succeeds. That is what proves the package is executable
on its own rather than borrowing from a working tree that keeps changing.

No model or grader call is made; nothing outside this directory is written.
"""
import hashlib
import io
import json
import os
import runpy
import sys

sys.dont_write_bytecode = True

R = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(R, "bench", ".claude", "plans", "Drivers", "experiments",
                       "harness")
REPO = "/home/faisal/EventMarketDB"
EVIDENCE_ROOT = os.path.join(R, "bench", ".claude", "plans", "Drivers", "experiments")
#: the interpreter's own files are tooling, not evidence
TOOLING = (sys.prefix, sys.base_prefix, "/usr/lib", "/usr/local/lib", "/proc",
           "/dev", "/sys", "/etc")

opened = set()
#: every path the CHILD interpreters opened, merged into the parent's audit
child_opened = set()

#: THE AUDIT HOOK DOES NOT CROSS A SUBPROCESS. `_a3_probe` measures A3 in a clean
#: interpreter on purpose, so the parent's `sys.addaudithook` sees nothing it reads.
#: The child is given the same hook by prepending it to the `-c` source; the source
#: itself is unchanged otherwise, so what the child computes is what it always
#: computed.
_CHILD_AUDIT = """import sys as _s, os as _o, atexit as _a
_out = %r
_seen = set()
def _hook(event, args):
    # the audit's OWN output file is noise this instrument creates, not a read the
    # child would ever have made
    if event == "open" and args and isinstance(args[0], str):
        p = _o.path.abspath(args[0])
        if p != _out:
            _seen.add(p)
_s.addaudithook(_hook)
_a.register(lambda: open(_out, "w").write("\\n".join(sorted(_seen))))
"""


def instrument_children(audit_path):
    """Give every `-c` child the parent's audit hook; return the unpatch callable."""
    import subprocess
    real = subprocess.run

    def run(cmd, *a, **kw):
        subprocess_calls.append([str(x)[:80] for x in cmd] if isinstance(cmd, (list, tuple))
                                else str(cmd)[:200])
        if (isinstance(cmd, (list, tuple)) and len(cmd) > 3 and "-c" in cmd):
            cmd = list(cmd)
            i = cmd.index("-c")
            cmd[i + 1] = (_CHILD_AUDIT % os.path.abspath(audit_path)) + cmd[i + 1]
        else:
            unaudited_children.append(subprocess_calls[-1])
        out = real(cmd, *a, **kw)
        if os.path.exists(audit_path):
            for line in io.open(audit_path, encoding="utf-8").read().split("\n"):
                if line.strip():
                    child_opened.add(line.strip())
            os.remove(audit_path)
        return out

    subprocess.run = run
    return lambda: setattr(subprocess, "run", real)


#: abspath -> the stack that opened it, for reads outside the package. Naming a read
#: is not the same as explaining it, and an unexplained read is what a leak looks like.
why = {}
#: every subprocess the run spawned, and those whose reads the audit cannot see
subprocess_calls, unaudited_children = [], []


def _hook(event, args):
    if event == "open" and args and isinstance(args[0], str):
        ap = os.path.abspath(args[0])
        opened.add(ap)
        if not ap.startswith(R) and not ap.startswith(tuple(TOOLING)) and ap not in why:
            import traceback
            why[ap] = "".join(traceback.format_stack()[-4:-1])[-600:]


def verdict(result, outside, unmanifested, temporary, unaudited):
    """CLEAN MEANS COMPLETED AND INSIDE THE PACKAGE. The one owner of the resume
    verdict: a run that raised is never clean whatever it read; a read into the dirty
    checkout, an unmanifested file, a temporary tree, or through a child the audit
    could not see is never clean whatever the run returned (Codex SEQ 1559 item 1)."""
    return bool(result == "completed" and not outside and not unmanifested
                and not temporary and not unaudited)


def manifested():
    """The files the package manifests, from the freeze's OWN walk - never from a
    previous run's TSV. The resume step runs before the freeze in the ordered chain,
    so the manifest on disk is the last chain's, and every input added since would
    have read as unmanifested and halted the chain on a stale list."""
    sys.path.insert(0, R)
    import freeze_package as FP
    return {os.path.join(R, rel) for _kind, rel, _v in FP.entries()}


def projection_inputs(argv):
    """-> (evidence root, {historical path: (package relpath, sha256)}) or (None, None).

    ONE EXPLICIT, VERIFIED INPUT (Codex SEQ 1561 item 1). The recovery wrapper names the
    projected evidence root and the projection table together; an ambient environment
    value never wins. Without them the ordinary package root is the only default and
    every /tmp read refuses. With them the projected view is verified BEFORE the run:
    every row present, a regular file, bytes equal to the manifested package file, and
    no extra file in the projected tree."""
    if "--evidence-root" not in argv and "--projection" not in argv:
        return None, None
    if not ("--evidence-root" in argv and "--projection" in argv):
        raise SystemExit("REFUSED: --evidence-root and --projection must be given together")
    root = argv[argv.index("--evidence-root") + 1]
    tsv = argv[argv.index("--projection") + 1]
    sys.path.insert(0, R)
    import project_historical_tree as PHT
    if os.path.abspath(tsv) != os.path.abspath(PHT.TSV):
        raise SystemExit("REFUSED: the projection table must be the package's own %s" % PHT.TSV)
    ev, _run = PHT.historical_roots()
    if os.path.abspath(root) != ev:
        raise SystemExit("REFUSED: --evidence-root %s is not the receipt's historical root %s" % (root, ev))
    bad = PHT.verify()
    if bad:
        for b in bad[:10]:
            print("  PROJECTION DEFECT", b)
        raise SystemExit("REFUSED: the projected view is not exactly the manifested package (%d defects)" % len(bad))
    return ev, {h: (rel, digest) for _ph, h, rel, _b, digest in PHT.load()}


def classify_read(p, known, projection):
    """-> 'covered' | 'unmanifested' | 'temporary' | 'outside' | 'tooling' | 'package'.

    THE ONE OWNER of what a read outside the package may be. A read outside the package
    is covered only when the path is a projected row AND its bytes still equal the
    manifested package file - the historical experiments tree under /tmp, the official
    states and the agent records under the session directory alike. Every other /tmp
    path or byte is a temporary read; every other path is unmanifested; a name-only
    match never covers anything (Codex SEQ 1561 item 1)."""
    if not p.startswith(R):
        row = (projection or {}).get(p)
        if row and os.path.isfile(p) and not os.path.islink(p) \
                and hashlib.sha256(io.open(p, "rb").read()).hexdigest() == row[1]:
            return "covered"
    if p.startswith(R):
        if p not in known and "__pycache__" not in p and p != os.path.join(R, "logs", "child_audit.txt"):
            return "unmanifested"
        return "package"
    if p.startswith(tuple(TOOLING)):
        return "tooling"
    if p.startswith("/tmp"):
        return "temporary"
    if p.startswith(REPO):
        return "outside"
    return "unmanifested"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    evidence_root, projection = projection_inputs(argv)
    known = manifested()
    sys.path.insert(0, HARNESS)
    os.environ["GUIDANCE_SCRIPTS_DIR"] = os.path.join(
        R, "bench", ".claude", "skills", "earnings-orchestrator", "scripts")
    # the A3 probe reads the run directory pointer; inside the namespace that
    # already points at the reconstructed run, so an existing value wins
    # THE EVIDENCE ROOT IS OVERRIDDEN, NEVER INHERITED. `setdefault` let a stale value
    # from the environment win, which is how a run that read a vanished /tmp tree was
    # reported as clean (Codex SEQ 1559 item 1). The root is the package's own
    # vendored experiments tree, into which every recovered input is materialised.
    os.environ["KFIELDS_EVIDENCE"] = evidence_root or EVIDENCE_ROOT
    # THE HOME DIRECTORY IS OVERRIDDEN TOO. The builder's source-gap search declares
    # `~/.core827-orchestrator` as a root and hashed the live mailbox looking for a
    # named inventory - a read outside the package that found nothing and was excused
    # as "declared search". With HOME set to the package's own empty home, `~` resolves
    # inside the package and the search reads nothing outside it; nothing is excused.
    if projection is None:
        os.makedirs(os.path.join(R, "home"), exist_ok=True)
        os.environ["HOME"] = os.path.join(R, "home")
    # with the explicit projection pair, HOME stays real: the official-state check needs
    # the receipts' historical paths under it, and the namespace masks the live session
    # records and the mailbox directory so every read there is a projected package byte
    sys.addaudithook(_hook)
    unpatch = instrument_children(os.path.join(R, "logs", "child_audit.txt"))
    cwd = os.getcwd()
    os.chdir(HARNESS)
    result, err = None, None
    try:
        runpy.run_path(os.path.join(HARNESS, "build_kfields_key.py"),
                       run_name="__main__")
        result = "completed"
    except SystemExit as exc:
        result = "SystemExit %s" % exc.code
    except Exception as exc:                          # noqa: BLE001 - reported
        # NEVER TRUNCATE THE EVIDENCE. Cutting the message at 200 characters hid
        # the very filename the run was missing, which is the whole content of
        # the finding.
        result = "%s: %s" % (type(exc).__name__, exc)
        err = result
    finally:
        os.chdir(cwd)
        unpatch()
        opened.update(child_opened)

    # THE PROGRAM DECLARES ITS OWN SEARCH ROOTS. `historical_source_gap` walks a set
    # of candidate directories hashing every .json to look for the named inventory;
    # those reads are a SEARCH, not a dependency, and the roots come from the run's own
    # declaration rather than from a list written here.
    search_roots = []
    try:
        import build_kfields_key as _K
        search_roots = [r for r in _K.historical_source_gap().get("searched", [])
                        if r and not r.startswith(R)]
    except Exception:
        pass

    outside, unmanifested, run_artifacts, searched_reads, covered = [], [], [], [], []
    # THE BYTES ARE IN THE PACKAGE EVEN WHEN THE PATH IS NOT: the receipts pin the
    # official states and their agent records by historical absolute paths, and the
    # projection table maps each such path to its manifested copy; a read of the
    # historical path is lawful exactly when the projection covers it, byte for byte.
    for p in sorted(opened):
        label = classify_read(p, known, projection)
        if label == "covered":
            covered.append(p)
        elif label == "unmanifested":
            unmanifested.append(p)
        elif label == "temporary":
            # A TEMPORARY TREE IS NEVER LAWFUL RUN INPUT unless it is the package-backed
            # projection, byte for byte; anything else under /tmp refuses.
            run_artifacts.append(p)
        elif label == "outside":
            outside.append(p)
    rep = {
        "entry_point": "build_kfields_key.py::__main__",
        "result": result,
        "files_opened": len(opened),
        "child_files_opened": len(child_opened),
        "resolved_into_dirty_main": outside[:20],
        "unmanifested_reads": unmanifested[:20],
        "why_outside": {k: why[k] for k in list(why)[:5]},
        "run_artifacts_read": len(run_artifacts),
        "declared_search_reads": len(searched_reads),      # always 0 now: no read is excused as a search
        "home_override": os.environ.get("HOME"),
        "evidence_root": evidence_root or EVIDENCE_ROOT,
        "projection_rows": len(projection) if projection else 0,
        "search_roots": search_roots,
        "temporary_reads": run_artifacts[:20],
        "outside_reads_covered_by_manifested_copies": len(covered),
        "entry_sha256": hashlib.sha256(io.open(os.path.join(
            HARNESS, "build_kfields_key.py"), "rb").read()).hexdigest(),
        "subprocess_calls": subprocess_calls,
        "unaudited_children": unaudited_children,
        "clean": verdict(result, outside, unmanifested, run_artifacts, unaudited_children),
    }
    io.open(os.path.join(R, "reports", "resume_path.json"), "w",
            encoding="utf-8").write(json.dumps(rep, indent=2) + "\n")
    # NEVER TRUNCATE THE EVIDENCE: the report keeps twenty of each for reading, the log
    # keeps every read by class, which is what a recovery is derived from
    io.open(os.path.join(R, "logs", "resume_reads.json"), "w", encoding="utf-8").write(json.dumps({
        "resolved_into_dirty_main": outside, "unmanifested_reads": unmanifested,
        "temporary_reads": run_artifacts, "covered": covered}, indent=1) + "\n")
    print("entry point : %s" % rep["entry_point"])
    print("result      : %s" % result)
    print("files opened: %d (child %d)" % (len(opened), len(child_opened)))
    print("into dirty main : %d %s" % (len(outside), outside[:3]))
    print("unmanifested    : %d %s" % (len(unmanifested), unmanifested[:3]))
    print("run artifacts   : %d (the run under audit)" % len(run_artifacts))
    print("declared search : %d in %s" % (len(searched_reads), search_roots))
    print("temporary reads: %d %s" % (len(run_artifacts), run_artifacts[:2]))
    print("subprocesses    : %d audited, %d unaudited" % (len(subprocess_calls),
                                                       len(unaudited_children)))
    print("CLEAN" if rep["clean"] else "NOT CLEAN")
    return 0 if rep["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
