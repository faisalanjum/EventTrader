"""The read closure of one foundation build, MEASURED with the A3 tracer's own rules (Codex SEQ 1579
item 3): every regular file the build (all processes) opened for reading or executed, classified (after path normalisation)
as a projected historical path (a read of manifested candidate bytes), a candidate file under
regen_1570, a file the build itself wrote inside the private tree, a successful read beneath the read-only Git
object store bound at the bench (the owner's base-tree identity, reported separately; any other .git or relative
read is OUTSIDE), an interpreter/venv/system file (reported separately), or an outside read - which
refuses. Same openat/execve grammar as the accepted A3 closure_trace.py; no second path law.

    foundation_closure.py <strace file> <projection table> <out CLOSURE.tsv>
"""
import io
import os
import re
import sys

R = os.path.dirname(os.path.abspath(__file__))
OPEN = re.compile(r'^\d+\s+openat\((?:AT_FDCWD|\d+)(?:<[^>]*>)?, "([^"]+)", ([A-Z_|]+)(?:, \d+)?\) = (-?\d+)')
EXEC = re.compile(r'^\d+\s+execve\("([^"]+)", .* = (-?\d+)')
SYSTEM_ROOTS = (sys.prefix, sys.base_prefix, "/usr", "/lib", "/etc", "/proc", "/dev", "/sys", "/bin", "/sbin")
VENV = "/home/faisal/EventMarketDB/venv"
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
SESS = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
GIT = S + "/bench_1306/.git"
GIT_OBJECTS = GIT + "/objects"
GIT_CONTROL = GIT + "/HEAD"                          # the deterministic control file the wrapper writes in the namespace


def classify(trace_text, table_text, root=R):
    hist = {}
    for ln in table_text.split("\n")[1:]:
        if ln.strip():
            ph, h, rel, _b, _s = ln.split("\t")
            hist[h] = (ph, rel)
    projected, candidate, generated, git, system, outside = {}, {}, {}, {}, {}, {}
    for ln in trace_text.split("\n"):
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
        path = os.path.normpath(path)
        if path in hist:
            projected.setdefault(path, (hist[path][0], hist[path][1], kind))
        elif path.startswith(GIT_OBJECTS + os.sep) or path.startswith(".git/objects/"):
            git.setdefault(path, kind)              # the narrow read-only Git identity input: the object store only
        elif path == GIT_CONTROL:
            generated.setdefault(path, kind)        # the control file the wrapper wrote inside the private namespace
        elif path.startswith(GIT + os.sep) or not path.startswith("/"):
            outside[path] = kind                    # any other .git path or relative read is not a permitted input
        elif path.startswith((S + os.sep, SESS + os.sep)):
            generated.setdefault(path, kind)        # written by the build itself inside the private tree
        elif path.startswith(root + os.sep):
            candidate.setdefault(os.path.relpath(path, root), kind)
        elif path.startswith(VENV + os.sep) or path.startswith(SYSTEM_ROOTS):
            top = "/".join(path.split("/")[:4])
            system[top] = system.get(top, 0) + 1
        else:
            outside[path] = kind
    return projected, candidate, generated, git, system, outside


def main(trace, table, out):
    projected, candidate, generated, git, system, outside = classify(io.open(trace, encoding="utf-8", errors="replace").read(),
                                                     io.open(table, encoding="utf-8").read())
    with io.open(out, "w", encoding="utf-8") as fh:
        fh.write("class\tpath\tphase\tcandidate_path\tkind\n")
        for p, (ph, rel, kind) in sorted(projected.items()):
            fh.write("projected\t%s\t%s\t%s\t%s\n" % (p, ph, rel, kind))
        for rel, kind in sorted(candidate.items()):
            fh.write("candidate\t%s\t\t%s\t%s\n" % (os.path.join(R, rel), rel, kind))
        for p, kind in sorted(generated.items()):
            fh.write("generated\t%s\t\t\t%s\n" % (p, kind))
        for p, kind in sorted(git.items()):
            fh.write("git-identity\t%s\t\t\t%s\n" % (p, kind))
        for p, kind in sorted(outside.items()):
            fh.write("OUTSIDE\t%s\t\t\t%s\n" % (p, kind))
    by_phase = {}
    for ph, _rel, _k in projected.values():
        by_phase[ph] = by_phase.get(ph, 0) + 1
    print("closure: projected reads %d (%s); candidate reads %d; reads of the build's own outputs %d; Git identity reads %d; interpreter/venv/system roots %s; OUTSIDE reads %d"
          % (len(projected), ", ".join("%s %d" % kv for kv in sorted(by_phase.items())), len(candidate), len(generated), len(git),
             dict(sorted(system.items())), len(outside)))
    for p in sorted(outside)[:20]:
        print("  OUTSIDE " + p)
    return 1 if outside else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
