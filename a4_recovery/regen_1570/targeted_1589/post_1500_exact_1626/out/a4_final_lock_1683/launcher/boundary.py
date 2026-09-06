# -*- coding: utf-8 -*-
"""Minimal recovery boundary (Codex SEQ 1683 step 1 / 1687).

Presents historical absolute logical paths (identity-bearing /tmp names in the
frozen bindings) to UNCHANGED owners via a private user+mount namespace, while
every real byte stays durable under the recovery worktree. Host /tmp is never
touched: the tmpfs + binds live only inside the namespace.

Contract (two phases, one file):
  host phase  -- validate the bind map on the host, REFUSE before any namespace
                 if a source is missing / a bound byte changed / a logical path
                 escapes the /tmp map; else re-exec self under unshare.
  ns phase    -- (uid 0 in the private ns) tmpfs at /tmp, bind each source onto
                 its logical path (ro inputs, rw outputs), exec the payload with
                 python -B and PYTHONDONTWRITEBYTECODE=1.

Bind map TSV rows: logical<TAB>source<TAB>expected_sha256<TAB>mode(ro|rw)
  expected_sha256 for a file = sha256(bytes); for a dir = manifest sha (see
  dir_manifest_sha); mode rw skips the integrity check (output target).
"""
import hashlib, io, os, subprocess, sys

UNSHARE = ["unshare", "--user", "--map-root-user", "--mount", "--propagation", "private"]
ALLOW_ROOT = "/tmp/"   # every logical mountpoint must stay under here
# Codex SEQ 1692: additionally allow EXACTLY the historical session-store projects
# root (and its children), never its parent, a look-alike prefix, or other /home.
PROJECTS_MOUNT = "/home/faisal/.claude/projects"


def _under_allowed(norm):
    return (norm + "/").startswith(ALLOW_ROOT) or norm == PROJECTS_MOUNT or (norm + "/").startswith(PROJECTS_MOUNT + "/")


def file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dir_manifest_sha(root):
    """Deterministic sha over (relpath, filesha) for every regular file, sorted."""
    rows = []
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            ap = os.path.join(dp, f)
            if os.path.islink(ap) or not os.path.isfile(ap):
                continue
            rows.append(os.path.relpath(ap, root) + "\0" + file_sha(ap))
    h = hashlib.sha256()
    for r in sorted(rows):
        h.update(r.encode() + b"\n")
    return h.hexdigest()


def source_sha(p):
    return dir_manifest_sha(p) if os.path.isdir(p) else file_sha(p)


def read_map(path):
    rows = []
    with io.open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            if not ln or ln.startswith("#"):
                continue
            c = ln.split("\t")
            assert len(c) == 4, "bad bind row: %r" % (ln,)
            rows.append({"logical": c[0], "source": c[1], "sha": c[2], "mode": c[3]})
    return rows


def validate(rows):
    """Return list of refusals; empty == ok. Runs on the host, before any mount."""
    bad = []
    for r in rows:
        lg, src, want, mode = r["logical"], r["source"], r["sha"], r["mode"]
        # escape check: absolute, normalized, strictly under ALLOW_ROOT, no ..
        norm = os.path.normpath(lg)
        if not (os.path.isabs(lg) and _under_allowed(norm) and ".." not in lg.split("/")):
            bad.append("REFUSE escape: logical %r not under %s or %s" % (lg, ALLOW_ROOT, PROJECTS_MOUNT)); continue
        if not os.path.exists(src):
            bad.append("REFUSE missing bind target: %s" % src); continue
        if mode not in ("ro", "rw"):
            bad.append("REFUSE bad mode: %r" % mode); continue
        if mode == "ro":
            got = source_sha(src)
            if got != want:
                bad.append("REFUSE sha mismatch: %s want %s got %s" % (src, want[:16], got[:16]))
    return bad


def host_phase(mapfile, payload, argv_rest):
    rows = read_map(mapfile)
    bad = validate(rows)
    if bad:
        for b in bad:
            sys.stderr.write(b + "\n")
        return 3  # refusal, before any namespace or mount
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = UNSHARE + [sys.executable, "-B", os.path.abspath(__file__),
                     "--ns", mapfile, payload] + argv_rest
    return subprocess.call(cmd, env=env)


def ns_phase(mapfile, payload, argv_rest):
    # uid 0 inside the private ns; mounts here never reach the host.
    rows = read_map(mapfile)
    subprocess.check_call(["mount", "-t", "tmpfs", "none", "/tmp"])
    for r in rows:
        lg, src, mode = r["logical"], r["source"], r["mode"]
        # Create the mountpoint ONLY when it is absent. A scoped override binds
        # onto a path that already exists inside an earlier read-only bind, and
        # creating it there would fail on the read-only filesystem.
        if os.path.isdir(src):
            if not os.path.isdir(lg):
                os.makedirs(lg, exist_ok=True)
        elif not os.path.exists(lg):
            os.makedirs(os.path.dirname(lg), exist_ok=True)
            open(lg, "a").close()
        subprocess.check_call(["mount", "--bind", src, lg])
        if mode == "ro":
            subprocess.check_call(["mount", "-o", "remount,ro,bind", lg])
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
    os.execve(sys.executable, [sys.executable, "-B", payload] + argv_rest, env)


def main():
    a = sys.argv[1:]
    if a and a[0] == "--ns":
        return ns_phase(a[1], a[2], a[3:])
    assert a and a[0] == "--host", "usage: boundary.py --host <map.tsv> <payload.py> [args...]"
    return host_phase(a[1], a[2], a[3:])


if __name__ == "__main__":
    sys.exit(main())
