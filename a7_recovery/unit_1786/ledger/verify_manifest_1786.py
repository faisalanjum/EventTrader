# -*- coding: utf-8 -*-
"""Check EVERY manifest row against the bytes on disk (Codex SEQ 1775 item 1).

A manifest that hashes a file and then replaces it records a hash of bytes that
no longer exist. This is the check that catches it: it re-measures every
ordinary row, and reports the composed-view digest rows separately because they
pin a directory rather than a file.

An explicitly identified self-reference exclusion is not a failure - it is the
one row a manifest cannot contain - so it is reported as EXCLUDED, and anything
else that mismatches is a real failure.
"""
import hashlib, io, os, sys

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = U + "/MANIFEST.sha256"
SELF_NAME = "MANIFEST.sha256"


def fsha(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ok = bad = views = 0
    fails, notes = [], []
    for ln in io.open(MAN, encoding="utf-8").read().splitlines():
        if not ln.strip():
            continue
        if ln.startswith("#"):
            notes.append(ln)
            continue
        want, rest = ln.split("  ", 1)
        rel = rest.split("  (")[0].strip()
        if rel.endswith("/"):
            views += 1
            continue
        p = os.path.join(U, rel)
        if not os.path.isfile(p):
            bad += 1
            fails.append((rel, want, "ABSENT"))
            continue
        got = fsha(p)
        if got == want:
            ok += 1
        else:
            bad += 1
            fails.append((rel, want, got))
    listed = {ln.split("  ", 1)[1].split("  (")[0].strip()
              for ln in io.open(MAN, encoding="utf-8").read().splitlines()
              if ln.strip() and not ln.startswith("#")}
    missing_from_manifest = sorted(
        rel for rel in _every_file() if rel not in listed)
    print("rows ok        : %d" % ok)
    print("view digests   : %d" % views)
    print("MISMATCHED     : %d" % bad)
    for rel, want, got in fails:
        print("   %-24s want %s got %s" % (rel, want[:16], got[:16]))
    print("not in manifest: %d %s" % (len(missing_from_manifest),
                                      missing_from_manifest))
    print("declared exclusion:")
    for n in notes:
        print("   ", n)
    named = any(SELF_NAME in n for n in notes)
    unexplained = [m for m in missing_from_manifest if m != SELF_NAME]
    if not named:
        print("   NONE DECLARED")
    return 1 if (bad or unexplained or not named) else 0


def _every_file():
    for base, dirs, files in os.walk(U):
        rel = os.path.relpath(base, U)
        if any(rel == v or rel.startswith(v + os.sep)
               for v in ()):
            dirs[:] = []
            continue
        for n in files:
            yield os.path.relpath(os.path.join(base, n), U)


if __name__ == "__main__":
    sys.exit(main())
