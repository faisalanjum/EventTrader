#!/usr/bin/env python3
"""The package-backed projection of the historical evidence tree (Codex SEQ 1561 item 1).

The accepted A3 audit binds the receipt to the run directory's ABSOLUTE historical path
and derives launcher paths from it, so the real finalization can only run where that
path exists. It is reproduced inside a private mount namespace whose /tmp is a tmpfs,
and this module says exactly what may appear there: every file under the package's
vendored experiments tree, at its historical path, and NOTHING else. The historical root
and the run directory's historical name are read from the accepted receipt itself.

`build`  writes evidence/PROJECTION.tsv: phase, historical path, package path, bytes,
         sha256, from the freeze's own walk (only manifested files are projected).
         Phase `input` rows are projected BEFORE the run; phase `identity` rows are the
         run directory's own files - what the run must GENERATE, byte for byte equal to
         the package copies (the receipts it republishes, the launchers it arms, the
         finalizations and answers it writes) - verified AFTER the run.
`verify` checks a projected view: every row present, a regular file (never a symlink),
         bytes and sha256 equal, and no extra regular file under the projected root.
`pointer` restores the run-directory pointer to history's own bytes - the historical
         absolute run path - so the same file is valid in the projection and, by
         design, refuses in the ordinary package-root run.
"""
import hashlib
import io
import json
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.join("bench", ".claude", "plans", "Drivers", "experiments")
PACKAGE_RUN = os.path.join(EXPERIMENTS, "runs", "a3_serial_run")
TSV = os.path.join(R, "evidence", "PROJECTION.tsv")
POINTER = os.path.join(R, EXPERIMENTS, "a3_serial_dir.txt")


def _sha(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _receipts():
    out = []
    for rel in ("receipt.json", os.path.join("retry", "receipt.json")):
        fp = os.path.join(R, PACKAGE_RUN, rel)
        if os.path.isfile(fp):
            out.append(json.load(io.open(fp, encoding="utf-8")))
    return out


def historical_roots():
    """-> (historical experiments root, historical run dir), from the receipt."""
    receipt = _receipts()[0]
    run_id = receipt["run_id"]
    launcher = list(receipt["receipts"].values())[0]["launcher_path"]
    marker = "/runs/" + run_id + "/"
    assert marker in launcher, "the receipt's launcher path does not carry its run id"
    ev = launcher[:launcher.index(marker)]
    return ev, ev + "/runs/" + run_id


ATTEMPTS = os.path.join(EXPERIMENTS, "invrev_run4", "attempts.json")


def state_paths():
    """-> the official workflow-state paths the receipts record, plus the 38 saved
    attempts' states the strict identity proof reads - historical and absolute."""
    out = []
    for r in _receipts():
        out.extend(r.get("states") or [])
    fp = os.path.join(R, ATTEMPTS)
    if os.path.isfile(fp):
        out.extend(a["state_path"] for a in json.load(io.open(fp, encoding="utf-8")))
    return sorted(set(out))


def states_root():
    """The one directory the receipts' states live in - the live session records dir,
    which the namespace masks and the projection fills from the package copies."""
    dirs = {os.path.dirname(p) for p in state_paths()}
    assert len(dirs) == 1, "the receipts' states are not in one directory: %s" % sorted(dirs)
    return dirs.pop()


def records_root():
    """The live subagent-records directory of the same session, masked likewise."""
    return os.path.join(os.path.dirname(states_root()), "subagents", "workflows")


def record_paths():
    """-> the agent transcripts every workflow_agent row of the official states names,
    historical and absolute: the A3 probe reads exactly these."""
    out = []
    for st_path in state_paths():
        st = json.load(io.open(os.path.join(R, "evidence", "workflow_states", os.path.basename(st_path)), encoding="utf-8"))
        for row in st.get("workflowProgress") or []:
            if row.get("type") == "workflow_agent":
                out.append(os.path.join(records_root(), st["runId"], "agent-%s.jsonl" % row["agentId"]))
    return sorted(set(out))


def _authority_paths(rel_tsv):
    """{package relpath: historical path} from a mount authority's own column."""
    out = {}
    base = os.path.dirname(rel_tsv)
    for ln in io.open(os.path.join(R, rel_tsv), encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            f, _b, _s, hist = ln.split("\t")[:4]
            out[os.path.join(base, f)] = os.path.expanduser(hist)
    return out


def rows():
    """-> [(historical path, package relpath, bytes, sha256)] for the projection."""
    sys.path.insert(0, R)
    import freeze_package as FP
    ev, run = historical_roots()
    out = []
    for kind, rel, _v in FP.entries():
        if kind != "file" or not rel.startswith(EXPERIMENTS + "/") or rel.startswith(EXPERIMENTS + "/harness/"):
            continue
        if rel.startswith(PACKAGE_RUN + "/"):
            phase, hist = "identity", run + "/" + os.path.relpath(rel, PACKAGE_RUN)
        else:
            phase, hist = "input", ev + "/" + os.path.relpath(rel, EXPERIMENTS)
        fp = os.path.join(R, rel)
        out.append((phase, hist, rel, os.path.getsize(fp), _sha(fp)))
    # THE OFFICIAL STATES the receipts name, from their manifested copies: a read of the
    # historical path inside the namespace is a read of package bytes, never of the live
    # session records
    manifested = {rel for kind, rel, _v in FP.entries() if kind == "file"}
    for hist in state_paths():
        rel = os.path.join("evidence", "workflow_states", os.path.basename(hist))
        assert rel in manifested, "a state the receipt names is not manifested: %s" % rel
        fp = os.path.join(R, rel)
        out.append(("state", hist, rel, os.path.getsize(fp), _sha(fp)))
    # THE AGENT TRANSCRIPTS those states name, from their manifested copies likewise
    for hist in record_paths():
        rel = os.path.join("evidence", "subagent_records", os.path.relpath(hist, records_root()))
        assert rel in manifested, "a record the states name is not manifested: %s" % rel
        fp = os.path.join(R, rel)
        out.append(("record", hist, rel, os.path.getsize(fp), _sha(fp)))
    # ONE AUTHORITY FOR WHERE A STATE OR RECORD STOOD: the mount authority that pinned it
    # at recovery must name the very path the receipts and the saved rows name
    auth = _authority_paths(os.path.join("evidence", "workflow_states", "WORKFLOW_STATES.tsv"))
    auth.update(_authority_paths(os.path.join("evidence", "subagent_records", "SUBAGENT_RECORDS.tsv")))
    for ph, hist, rel, _b, _s in out:
        if ph in ("state", "record"):
            assert auth.get(rel) == hist, "%s is pinned at %s by its mount authority, not at %s" % (rel, auth.get(rel), hist)
    return sorted(out, key=lambda r: r[1])


def build():
    rs = rows()
    io.open(TSV, "w", encoding="utf-8").write("phase\thistorical_path\tpackage_path\tbytes\tsha256\n" +
                                              "".join("%s\t%s\t%s\t%d\t%s\n" % r for r in rs))
    print("projection: %d input + %d identity + %d state + %d record files, historical root %s, states root %s, records root %s"
          % (sum(1 for r in rs if r[0] == "input"), sum(1 for r in rs if r[0] == "identity"),
             sum(1 for r in rs if r[0] == "state"), sum(1 for r in rs if r[0] == "record"),
             historical_roots()[0], states_root(), records_root()))
    return 0


def load():
    out = []
    for ln in io.open(TSV, encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            ph, h, p, b, s = ln.split("\t")
            out.append((ph, h, p, int(b), s))
    return out


def view_path(view_root, hist):
    """THE ONE MAPPING of a historical path into a test view. A historical path is
    either under the experiments root or under the states root; anything else, and any
    mapping that would leave the view, is refused - a control once joined a path outside
    the experiments root onto its view and reached a LIVE record through `..`."""
    if view_root is None:
        return hist
    ev, _run = historical_roots()
    sroot, rroot = states_root(), records_root()
    if hist.startswith(sroot + "/"):
        out = os.path.join(view_root, "states", os.path.relpath(hist, sroot))
    elif hist.startswith(rroot + "/"):
        out = os.path.join(view_root, "records", os.path.relpath(hist, rroot))
    elif hist.startswith(ev + "/"):
        out = os.path.join(view_root, os.path.relpath(hist, ev))
    else:
        raise ValueError("historical path outside both projected roots: %s" % hist)
    if not os.path.abspath(out).startswith(os.path.abspath(view_root) + os.sep):
        raise ValueError("view path escapes the view root: %s" % out)
    return out


def verify(view_root=None, phase=None):
    """-> list of defects of the projected view (empty when exact). `view_root` maps the
    historical root elsewhere for tests; inside the namespace it is the real root.
    `phase="input"` checks the inputs alone, before the run, and requires the run
    directory to be absent; `None` checks every row after the run."""
    ev, run = historical_roots()
    sroot = states_root()
    where = lambda hist: view_path(view_root, hist)
    defects, projected = [], set()
    if phase == "input" and os.path.exists(where(run)):
        defects.append("the run directory exists before the run: %s" % where(run))
    for ph, hist, rel, size, digest in load():
        if phase == "input" and ph == "identity":
            continue                      # identity rows are generated by the run
        if phase is not None and phase != "input" and ph != phase:
            continue
        v = where(hist)
        projected.add(os.path.realpath(v) if not os.path.islink(v) else v)
        if os.path.islink(v):
            defects.append("symlink where a projected file must be: %s" % v)
        elif not os.path.isfile(v):
            defects.append("missing projected file: %s" % v)
        elif os.path.getsize(v) != size or _sha(v) != digest:
            defects.append("projected bytes differ from the manifested %s: %s" % (rel, v))
        pf = os.path.join(R, rel)
        if not os.path.isfile(pf) or _sha(pf) != digest:
            defects.append("package file no longer matches the projection: %s" % rel)
    root = ev if view_root is None else view_root
    for base in ([root, sroot, records_root()] if view_root is None else [root]):
      for dp, dirs, files in os.walk(base):
        for f in files:
            fp = os.path.join(dp, f)
            key = os.path.realpath(fp) if not os.path.islink(fp) else fp
            if key not in projected:
                defects.append("extra file in the projected tree, not package-backed: %s" % fp)
    return defects


def pointer():
    """History's own pointer bytes: the absolute historical run directory, one line."""
    _ev, run = historical_roots()
    data = (run + "\n").encode("utf-8")
    io.open(POINTER, "wb").write(data)
    tsv = os.path.join(R, "evidence", "RESUME_INPUTS.tsv")
    rel = os.path.relpath(POINTER, R)
    lines = [l for l in io.open(tsv, encoding="utf-8").read().split("\n") if l.strip()]
    lines = [l for l in lines if not l.startswith(rel + "\t")]
    lines.append("%s\t%d\t%s\tpointer to the run directory as history wrote it (record 34232): the "
                 "historical absolute path, valid only inside the package-backed projection"
                 % (rel, len(data), hashlib.sha256(data).hexdigest()))
    io.open(tsv, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("pointer restored to history's bytes (%d bytes) and re-pinned in RESUME_INPUTS.tsv" % len(data))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        sys.exit(build())
    if cmd == "pointer":
        sys.exit(pointer())
    if cmd == "verify":
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        bad = verify(args[0] if args else None, "input" if "--inputs" in sys.argv else None)
        for b in bad[:20]:
            print("  DEFECT", b)
        print("projection verify: %d defects" % len(bad))
        sys.exit(1 if bad else 0)
    sys.exit("usage: project_historical_tree.py build|pointer|verify [view_root]")
