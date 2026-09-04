"""THE one enumerated logical-source-to-local-file mapper (Codex SEQ 1570 item 1, SEQ 1572).

Every immutable input the candidate needs is named here once: its logical source (an official
record store path, a durable package file, a proven blob, or one transcript record), its role,
and its destination under this root. `copy` copies each into the candidate and writes
SOURCES.tsv (source, bytes, sha256, role, destination); `verify` re-hashes every destination
against that table. Nothing outside this table is read by the finished runtime; a source that
is missing, a destination whose bytes drift, or a destination outside the root refuses.

    sources.py copy      copy every enumerated input (existing identical files are left alone)
    sources.py verify    re-check every destination against SOURCES.tsv
"""
import hashlib
import io
import json
import os
import shutil
import sys

R = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(R, "inputs", "owner_recipes", "SOURCES.tsv")
BLOBS = "/home/faisal/.core827_backups/recovery_1531/regen_1537/probe/blobs"
STAGE1 = "/home/faisal/.core827_backups/recovery_1531/regen_1539/builds/stage1/tree/.claude/plans/Drivers/experiments/harness_g1v3"
TRANSCRIPT = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")

#: (logical source, role, destination relative to the root); a source of the form
#: transcript:<line> is that one record line of the bound session transcript
ENUMERATED = [
    (BLOBS + "/5ae25b1d9248ea60", "A6 owner recipe source A (proven blob)", "inputs/owner_recipes/blob_5ae25b1d9248ea60"),
    (BLOBS + "/2b8667dc9614c965", "A6 owner recipe source B (proven blob)", "inputs/owner_recipes/blob_2b8667dc9614c965"),
    (STAGE1 + "/raw_transport.py", "raw transport recipe base (stage-1 bytes)", "inputs/owner_recipes/stage1_raw_transport.py"),
    ("transcript:91763", "raw transport recipe: the record-91763 Edit (immutable record)", "inputs/owner_recipes/transcript_record_91763.json"),
]


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _source_bytes(src):
    if src.startswith("transcript:"):
        want = int(src.split(":", 1)[1])
        with io.open(TRANSCRIPT, "rb") as fh:
            for n, raw in enumerate(fh, 1):
                if n == want:
                    json.loads(raw)  # must be one intact record
                    return raw
        raise SystemExit("REFUSED: transcript record %d is absent" % want)
    if not os.path.isfile(src):
        raise SystemExit("REFUSED: source missing: %s" % src)
    return io.open(src, "rb").read()


def copy():
    rows = []
    for src, role, rel in ENUMERATED:
        dst = os.path.normpath(os.path.join(R, rel))
        if not dst.startswith(R + os.sep):
            raise SystemExit("REFUSED: destination outside the root: %s" % rel)
        b = _source_bytes(src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isfile(dst):
            if io.open(dst, "rb").read() != b:
                raise SystemExit("REFUSED: %s exists with different bytes" % rel)
        else:
            io.open(dst, "wb").write(b)
        rows.append((src, len(b), _sha(b), role, rel))
    os.makedirs(os.path.dirname(TABLE), exist_ok=True)
    with io.open(TABLE, "w", encoding="utf-8") as fh:
        fh.write("source\tbytes\tsha256\trole\tdestination\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    print("copied %d inputs; SOURCES.tsv written" % len(rows))
    return 0


def verify():
    bad = 0
    for l in io.open(TABLE, encoding="utf-8").read().split("\n")[1:]:
        if not l.strip():
            continue
        src, size, sha, role, rel = l.split("\t")
        p = os.path.join(R, rel)
        if not os.path.isfile(p) or os.path.getsize(p) != int(size) or _sha(io.open(p, "rb").read()) != sha:
            print("DRIFT %s" % rel); bad += 1
    print("sources: %s" % ("every destination holds" if not bad else "%d drifted" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(verify() if sys.argv[1:] == ["verify"] else copy())
