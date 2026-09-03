#!/usr/bin/env python3
"""ONE-TIME RECOVERY TOOL, not a proof step: copy into the package every durable file a
mount was asked for and could not serve, and pin each in its mount's authority.

The list comes from a run that RECORDED the misses (replay_transcript.MOUNT_MISSES),
never from a hand list. Only files that exist at their historical path are copied; a
path that is gone is reported and stays absent, exactly as the replay treats it.
"""
import hashlib
import io
import json
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(R, "ledger"))
import replay_transcript as RT                                   # noqa: E402

AUTHORITY = {os.path.join(R, "evidence", "workflow_states"): "WORKFLOW_STATES.tsv",
             os.path.join(R, "evidence", "subagent_records"): "SUBAGENT_RECORDS.tsv"}


def _rows(dest):
    out = []
    for dirpath, _dirs, files in os.walk(dest):
        for f in sorted(files):
            if f.endswith(".tsv") and dirpath == dest:
                continue
            fp = os.path.join(dirpath, f)
            raw = io.open(fp, "rb").read()
            out.append((os.path.relpath(fp, dest), len(raw), hashlib.sha256(raw).hexdigest()))
    return sorted(out)


def main(misses_json):
    miss = json.load(io.open(misses_json, encoding="utf-8"))["missing"]
    copied, gone = [], []
    for sp in sorted(set(miss)):
        for root, dest in RT.MOUNTS.items():
            if sp == root or sp.startswith(root + "/"):
                rel = os.path.relpath(sp, root)
                if os.path.isfile(sp):
                    fp = os.path.join(dest, rel)
                    os.makedirs(os.path.dirname(fp), exist_ok=True)
                    io.open(fp, "wb").write(io.open(sp, "rb").read())
                    copied.append((dest, rel))
                else:
                    gone.append(sp)
    for dest, name in AUTHORITY.items():
        os.makedirs(dest, exist_ok=True)
        root = [r for r, d in RT.MOUNTS.items() if d == dest][0]
        rows = _rows(dest)
        io.open(os.path.join(dest, name), "w", encoding="utf-8").write(
            "file\tbytes\tsha256\thistorical_path\n"
            + "".join("%s\t%d\t%s\t%s\n" % (f, b, s, os.path.join(root, f).replace(
                os.path.expanduser("~"), "~")) for f, b, s in rows))
        print("%s: %d files pinned" % (name, len(rows)))
    print("copied %d, gone %d" % (len(copied), len(gone)))
    for sp in gone[:10]:
        print("  GONE", sp)


if __name__ == "__main__":
    main(sys.argv[1])
