#!/usr/bin/env python3
"""Verify every FIXED decision input against its own authority (Codex SEQ 1559).

  evidence/transcript/ACCEPTED.tsv   the accepted transcript prefix: bytes, rows, sha
  evidence/git_bases/GIT_BASES.tsv   every committed object the routes resolve
  evidence/RESUME_INPUTS.tsv         every input materialised for the resume path

Each authority is read only; each named file must exist and hash to the recorded
identity. Nothing is searched, nothing is rebuilt, and a mismatch is an exit status.
"""
import hashlib
import io
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))


def _sha(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def failures(root=R):
    bad = []
    # 1. the transcript prefix
    ident = os.path.join(root, "evidence", "transcript", "ACCEPTED.tsv")
    try:
        name, nbytes, nrows, sha = io.open(ident, encoding="utf-8").read().split("\t")[:4]
        fp = os.path.join(root, "evidence", "transcript", name)
        raw_len = os.path.getsize(fp)
        rows = 0
        with io.open(fp, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                rows += chunk.count(b"\n")
        if raw_len != int(nbytes) or rows != int(nrows) or _sha(fp) != sha:
            bad.append("transcript prefix is not the accepted authority (%d bytes, %d rows)"
                       % (raw_len, rows))
    except (IOError, OSError, ValueError) as exc:
        bad.append("transcript authority unusable: %s" % exc)
    # 2. the git base store
    store = os.path.join(root, "evidence", "git_bases")
    try:
        lines = io.open(os.path.join(store, "GIT_BASES.tsv"), encoding="utf-8").read().split("\n")
        if lines[0] != "commit\trel\tbytes\tsha256":
            raise ValueError("bad header")
        n = 0
        for line in lines[1:]:
            if not line.strip():
                continue
            commit, rel, nbytes, sha = line.split("\t")
            fp = os.path.join(store, commit + ".tree") if rel == "<tree>" else os.path.join(store, commit, rel)
            if not os.path.isfile(fp):
                bad.append("git store lacks %s:%s" % (commit[:12], rel))
            elif os.path.getsize(fp) != int(nbytes) or _sha(fp) != sha:
                bad.append("git store object %s:%s does not hash to its identity" % (commit[:12], rel))
            n += 1
        if n == 0:
            bad.append("git store authority names no objects")
    except (IOError, OSError, ValueError) as exc:
        bad.append("git store authority unusable: %s" % exc)
    # 3b. the mounted copies a saved program or the resume path reads: workflow states
    #     (at least one is always needed) and subagent records (may lawfully be none)
    for sub, name, may_be_empty in (("workflow_states", "WORKFLOW_STATES.tsv", False),
                                    ("subagent_records", "SUBAGENT_RECORDS.tsv", True)):
        try:
            wdir = os.path.join(root, "evidence", sub)
            lines = io.open(os.path.join(wdir, name), encoding="utf-8").read().split("\n")
            if lines[0] != "file\tbytes\tsha256\thistorical_path":
                raise ValueError("bad header")
            n = 0
            for line in lines[1:]:
                if not line.strip():
                    continue
                fname, nbytes, sha, _hist = line.split("\t")
                fp = os.path.join(wdir, fname)
                if not os.path.isfile(fp):
                    bad.append("%s copy missing: %s" % (sub, fname))
                elif os.path.getsize(fp) != int(nbytes) or _sha(fp) != sha:
                    bad.append("%s copy does not hash to its identity: %s" % (sub, fname))
                n += 1
            if n == 0 and not may_be_empty:
                bad.append("%s authority names no files" % sub)
            # every file in the directory must be pinned: an unpinned copy is unmanifested evidence
            pinned = {l.split("\t")[0] for l in lines[1:] if l.strip()}
            for dirpath, _d, files in os.walk(wdir):
                for f in files:
                    rel = os.path.relpath(os.path.join(dirpath, f), wdir)
                    if rel != name and rel not in pinned:
                        bad.append("%s holds an unpinned file: %s" % (sub, rel))
        except (IOError, OSError, ValueError) as exc:
            bad.append("%s authority unusable: %s" % (sub, exc))
    # 3. the resume inputs
    try:
        lines = io.open(os.path.join(root, "evidence", "RESUME_INPUTS.tsv"), encoding="utf-8").read().split("\n")
        if lines[0] != "path\tbytes\tsha256\tsource":
            raise ValueError("bad header")
        n = 0
        for line in lines[1:]:
            if not line.strip():
                continue
            path, nbytes, sha, _source = line.split("\t")
            fp = os.path.join(root, path)
            if not os.path.isfile(fp):
                bad.append("resume input missing: %s" % path)
            elif os.path.getsize(fp) != int(nbytes) or _sha(fp) != sha:
                bad.append("resume input does not hash to its identity: %s" % path)
            n += 1
        if n == 0:
            bad.append("resume inputs authority names no files")
    except (IOError, OSError, ValueError) as exc:
        bad.append("resume inputs authority unusable: %s" % exc)
    return bad


def main():
    bad = failures()
    for b in bad:
        print("FAIL " + b)
    print("FIXED INPUTS %s" % ("OK: transcript prefix, git store, workflow-state copies and resume inputs all hash to their authorities" if not bad else "REJECTED (%d defects)" % len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
