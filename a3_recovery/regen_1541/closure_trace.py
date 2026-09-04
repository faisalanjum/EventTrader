#!/usr/bin/env python3
"""The durable closure of the real resume/finalization path, MEASURED (Codex SEQ 1563 item 2).

`build_a3_finalization.sh prove` - the real a1_finalize, the pinned boundary and the real
build_kfields_key.py::__main__ inside the projection - is run once more under strace, and
every regular file it (or any child, inside the mount namespace or not) opened for reading
or executed under the package root is recorded. The resume's own audit sees one process;
this sees them all, the shell and both interpreters. The closure is the union of those
package-relative paths with every row of evidence/PROJECTION.tsv (what the path reads at a
historical path), each bound by bytes and sha256, in evidence/CLOSURE.tsv. Reads outside
the package root are listed by their root so a resolution into the live checkout or the
real /tmp cannot hide.
"""
import hashlib
import io
import os
import re
import subprocess
import sys

R = os.path.dirname(os.path.abspath(__file__))
TSV = os.path.join(R, "evidence", "CLOSURE.tsv")
TRACE = os.path.join(R, "logs", "closure.strace")
OPEN = re.compile(r'^\d+\s+openat\((?:AT_FDCWD|\d+)(?:<[^>]*>)?, "([^"]+)", ([A-Z_|]+)(?:, \d+)?\) = (-?\d+)')
EXEC = re.compile(r'^\d+\s+execve\("([^"]+)", .* = (-?\d+)')
IGNORED_ROOTS = (sys.prefix, sys.base_prefix, "/usr", "/lib", "/etc", "/proc", "/dev", "/sys")


def _sha(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def trace(root=R):
    os.makedirs(os.path.join(root, "logs"), exist_ok=True)
    r = subprocess.run(["strace", "-f", "-e", "trace=openat,execve", "-o", TRACE, "./build_a3_finalization.sh", "prove"],
                       cwd=root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


def opened(root=R):
    """-> (package-relative reads and executions, {outside root: count}) from the trace. A
    read of a projected historical path is a read of the projection row's package file."""
    root = os.path.realpath(root)
    hist = {}
    for ln in io.open(os.path.join(root, "evidence", "PROJECTION.tsv"), encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            _ph, h, rel, _b, _s = ln.split("\t")
            hist[h] = rel
    inside, outside = {}, {}
    for ln in io.open(TRACE, encoding="utf-8", errors="replace"):
        m = OPEN.match(ln)
        kind = "read"
        if m:
            path, flags, rc = m.group(1), m.group(2), int(m.group(3))
            if rc < 0 or "O_WRONLY" in flags or "O_RDWR" in flags or "O_DIRECTORY" in flags:
                continue
        else:
            m = EXEC.match(ln)
            if not m or int(m.group(2)) < 0:
                continue
            path, kind = m.group(1), "exec"
        if path in hist:
            inside.setdefault(hist[path], "projected-" + kind)
            continue
        real = os.path.realpath(path) if os.path.exists(path) else path
        if real.startswith(root + os.sep) and os.path.isfile(real):
            inside.setdefault(os.path.relpath(real, root), kind)
        elif not real.startswith(IGNORED_ROOTS):
            top = "/".join(real.split("/")[:4])
            outside[top] = outside.get(top, 0) + 1
    return inside, outside


def closure_rows(root=R):
    """-> {package relpath: (bytes, sha256, source)} from the trace and the projection."""
    inside, outside = opened(root)
    rows = {}
    for ln in io.open(os.path.join(root, "evidence", "PROJECTION.tsv"), encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            _ph, _h, rel, b, s = ln.split("\t")
            rows[rel] = (int(b), s, "projection")
    for rel, kind in inside.items():
        if rel.startswith("logs/") or rel.startswith("reports/") or rel.startswith("sibling_cache/") or rel.startswith("home/"):
            continue                         # the run's own outputs and caches are not its inputs
        fp = os.path.join(root, rel)
        rows[rel] = (os.path.getsize(fp), _sha(fp), "traced-" + kind) if rel not in rows else (rows[rel][0], rows[rel][1], "projection+" + kind)
    return rows, inside, outside


def build(root=R):
    rc = trace(root)
    if rc != 0:
        print("CLOSURE REFUSED: the real path failed under trace, rc=%d" % rc)
        return rc
    rows, inside, outside = closure_rows(root)
    io.open(TSV, "w", encoding="utf-8").write("path\tbytes\tsha256\tsource\n" +
                                              "".join("%s\t%d\t%s\t%s\n" % (rel, b, s, src) for rel, (b, s, src) in sorted(rows.items())))
    by = {}
    for _rel, (_b, _s, src) in rows.items():
        by[src] = by.get(src, 0) + 1
    print("closure: %d files, %d bytes (%s); traced opens under the package %d; outside the package and the interpreter: %s"
          % (len(rows), sum(b for b, _s, _src in rows.values()), ", ".join("%s %d" % kv for kv in sorted(by.items())),
             len(inside), dict(sorted(outside.items())) or "none"))
    return 0


def load(root=R):
    out = {}
    for ln in io.open(os.path.join(root, "evidence", "CLOSURE.tsv"), encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            rel, b, s, src = ln.split("\t")
            out[rel] = (int(b), s, src)
    return out


if __name__ == "__main__":
    sys.exit(build())
