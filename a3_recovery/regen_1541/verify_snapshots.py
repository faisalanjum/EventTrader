#!/usr/bin/env python3
"""Verify the replay against SURVIVING ERA BYTES, aligned by EVENT, not by clock.

Codex SEQ 1542: the evidence boundary is JSONL event order and event type, never file
mtime. The transcript carries the file-history events themselves:

  * `file-history-delta`  names a backup taken BEFORE the edit its message performed,
    so its bytes are the PRE-trigger state - the file as it stood entering that event.
  * `file-history-snapshot` records the tracked backups AFTER the message, so its bytes
    are the POST-trigger state.

Each stored blob is therefore pinned to a transcript LINE, and the cutoff follows from
its kind: a delta is compared against the replay BEFORE that line, a snapshot against
the replay through it. An mtime is a save time and can fall anywhere; it was never the
boundary. Every digest here is an OUTPUT assertion, read after the replay runs.
"""
import collections
import hashlib
import io
import json
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(R, "ledger"))
import chrono_replay as CR
import replay_transcript as RT

STORE = "/home/faisal/.claude/file-history"


def history_events():
    """-> {backupFileName: (line, kind, trackingPath)} from the transcript itself.

    A DELTA IS PINNED TO THE MESSAGE THAT TRIGGERED IT, not to where the delta record
    happens to sit. The backup is taken BEFORE that message edits the file, and the
    delta record is written just after it; aligning on the delta's own line therefore
    includes the very edit the backup precedes.
    """
    out, at = {}, {}
    with io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            try:
                d = json.loads(line, strict=False)
            except ValueError:
                continue
            if d.get("uuid"):
                at.setdefault(d["uuid"], n)
            mid = (d.get("message") or {}).get("id")
            if mid:
                at.setdefault(mid, n)
            t = d.get("type")
            if t == "file-history-delta":
                b = d.get("backup") or {}
                if b.get("backupFileName"):
                    out[b["backupFileName"]] = (n, "delta", d.get("trackingPath"),
                                                d.get("messageId"))
            elif t == "file-history-snapshot":
                for path, b in ((d.get("snapshot") or {})
                                .get("trackedFileBackups") or {}).items():
                    if isinstance(b, dict) and b.get("backupFileName"):
                        out.setdefault(b["backupFileName"],
                                       (n, "snapshot", path, d.get("messageId")))
    return dict((k, (at.get(v[3], v[0]) if v[1] == "delta" else v[0], v[1], v[2]))
                for k, v in out.items())


def blobs(abspath):
    """-> [(backupFileName, bytes, sha256)] for one absolute path, oldest version first.

    The store keys a file by the digest of its absolute path, so the path is proved by
    the key rather than assumed: a wrong path simply finds nothing.
    """
    key = hashlib.sha256(abspath.encode()).hexdigest()[:16]
    out = []
    for d in sorted(os.listdir(STORE)):
        p = os.path.join(STORE, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            if not f.startswith(key + "@v"):
                continue
            b = io.open(os.path.join(p, f), "rb").read()
            out.append((f, int(f.rsplit("@v", 1)[1]), len(b),
                        hashlib.sha256(b).hexdigest()))
    return sorted(out, key=lambda r: r[1])


def check(abspath, owner):
    """-> one row per surviving blob, aligned by its own event and kind."""
    events = history_events()
    rows = []
    for name, ver, size, sha in blobs(abspath):
        ev = events.get(name)
        if ev is None:
            rows.append(collections.OrderedDict([
                ("version", ver), ("backup", name), ("kind", "UNPINNED"),
                ("event_line", None), ("era_bytes", size), ("replay_bytes", None),
                ("era_sha256", sha), ("replay_sha256", None), ("exact", False)]))
            continue
        line, kind, _path = ev
        # a delta holds the PRE-trigger bytes, so the replay must stop BEFORE that
        # event; a snapshot holds the POST-trigger bytes, so it runs THROUGH it
        upto = line if kind == "delta" else line + 1
        mine = CR.sibling_text(abspath, upto) or ""
        got = hashlib.sha256(mine.encode()).hexdigest()
        rows.append(collections.OrderedDict([
            ("version", ver), ("backup", name), ("kind", kind),
            ("event_line", line), ("era_bytes", size),
            ("replay_bytes", len(mine.encode())), ("era_sha256", sha),
            ("replay_sha256", got), ("exact", got == sha)]))
    return rows


def main():
    # THE SCRATCH ROOT IS SESSION-SCOPED. Its directory is named for the project and
    # the session, both of which the transcript's own path already carries, so the
    # absolute path is derived rather than typed - and the store key then proves it.
    ses, proj = os.path.basename(RT.TRANSCRIPT)[:-6], os.path.basename(
        os.path.dirname(RT.TRANSCRIPT))
    abspath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        RT.SCRATCH_ROOT, proj, ses, "scratchpad", "step1_iso",
        ".claude/plans/Drivers/experiments/harness/test_harness_guards.py")
    owner = abspath.split("scratchpad/", 1)[1]
    rows = check(abspath, owner)
    for r in rows:
        print("v%-2d %-9s line %-7s era %7d %s | mine %7s %s | %s" % (
            r["version"], r["kind"], r["event_line"], r["era_bytes"],
            r["era_sha256"][:8],
            "-" if r["replay_bytes"] is None else r["replay_bytes"],
            (r["replay_sha256"] or "-")[:8],
            "EXACT" if r["exact"] else
            ("no event" if r["replay_bytes"] is None else
             "diff %+d" % (r["replay_bytes"] - r["era_bytes"]))))
    print("%d of %d era blobs reproduced byte-exactly" % (
        sum(1 for r in rows if r["exact"]), len(rows)))
    out = os.path.join(R, "reports", "era_snapshots_%s.json" % (
        owner.split("/")[0] + "_" + os.path.splitext(os.path.basename(abspath))[0]))
    io.open(out, "w", encoding="utf-8").write(json.dumps(
        collections.OrderedDict([("path", abspath), ("owner", owner),
                                 ("aligned_by", "transcript event order and type"),
                                 ("snapshots", rows)]), indent=2) + "\n")


if __name__ == "__main__":
    main()
