#!/usr/bin/env python3
"""Verify the accepted-checkpoint inventory. It does not BUILD it (Codex SEQ 1558 #3).

The previous builder held a second hand-written list of the eight states and searched
every Codex archive for `digest[:8]`, so its output could change as the mailbox grew and
an 8-hex prefix stood in for a 64-hex identity. Two owners of the same truth, and one of
them mutable.

`products/ACCEPTED_CHECKPOINTS.tsv` is the sole authority now. This reads it and proves,
for every row:

  * the evidence file exists, is valid UTF-8, and its bytes hash to the recorded digest
  * the recorded byte count is the UTF-8 BYTE length and the char count is len(text)
  * the acceptance archive named by the row still hashes to the digest the row pins
  * that archive carries the row's FULL 64-hex digest, its cutoff and its owner - the
    whole tuple, not a prefix
  * the eight rows are distinct in (owner, cutoff) and there are exactly eight

Nothing is searched, nothing is discovered. A row is checked against what it names.
"""
import hashlib
import io
import os
import re
import sys

R = os.path.dirname(os.path.abspath(__file__))
TSV = os.path.join(R, "products", "ACCEPTED_CHECKPOINTS.tsv")
MAIL = "/home/faisal/.core827-orchestrator"
COLUMNS = ["owner", "cutoff", "sha256", "bytes", "chars", "evidence_path",
           "evidence_sha256", "accepted_in", "accepted_in_sha256"]
EXPECTED_ROWS = 8


def rows(path=TSV):
    lines = [l.rstrip("\n") for l in io.open(path, encoding="utf-8") if l.strip()]
    if not lines:
        raise ValueError("inventory is empty")
    if lines[0].split("\t") != COLUMNS:
        raise ValueError("inventory header is not %s" % COLUMNS)
    out = []
    for n, line in enumerate(lines[1:], 2):
        f = line.split("\t")
        if len(f) != len(COLUMNS):
            raise ValueError("row %d has %d fields, expected %d"
                             % (n, len(f), len(COLUMNS)))
        out.append(dict(zip(COLUMNS, f)))
    return out


def failures(path=TSV, mail=MAIL, root=R):
    """-> [] when the inventory is exactly right, else one string per defect."""
    bad = []
    try:
        data = rows(path)
    except (IOError, OSError, ValueError) as exc:
        return ["inventory unreadable or malformed: %s" % exc]
    if len(data) != EXPECTED_ROWS:
        bad.append("expected %d rows, found %d" % (EXPECTED_ROWS, len(data)))
    seen = set()
    for r in data:
        key = (r["owner"], r["cutoff"])
        if key in seen:
            bad.append("duplicate row for %s@%s" % key)
        seen.add(key)
        if len(r["sha256"]) != 64 or not all(c in "0123456789abcdef" for c in r["sha256"]):
            bad.append("%s@%s: digest is not a full 64-hex identity" % key)
            continue
        ev = os.path.join(root, r["evidence_path"])
        if not os.path.isfile(ev):
            bad.append("%s@%s: evidence missing: %s" % (key + (r["evidence_path"],)))
            continue
        raw = io.open(ev, "rb").read()
        if hashlib.sha256(raw).hexdigest() != r["sha256"]:
            bad.append("%s@%s: evidence bytes do not hash to the recorded digest" % key)
        if r["evidence_sha256"] != r["sha256"]:
            bad.append("%s@%s: evidence_sha256 disagrees with sha256" % key)
        if len(raw) != int(r["bytes"]):
            bad.append("%s@%s: byte count %s is not the UTF-8 length %d"
                       % (key + (r["bytes"], len(raw))))
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            bad.append("%s@%s: evidence is not valid UTF-8" % key)
            continue
        if len(text) != int(r["chars"]):
            bad.append("%s@%s: char count %s is not len(text) %d"
                       % (key + (r["chars"], len(text))))
        arch = os.path.join(mail, r["accepted_in"])
        if not os.path.isfile(arch):
            bad.append("%s@%s: acceptance archive missing: %s"
                       % (key + (r["accepted_in"],)))
            continue
        ab = io.open(arch, "rb").read()
        if hashlib.sha256(ab).hexdigest() != r["accepted_in_sha256"]:
            bad.append("%s@%s: acceptance archive bytes changed since it was pinned"
                       % key)
        # THE TUPLE, NOT THREE SUBSTRINGS. Searching owner, cutoff and digest as
        # independent tokens anywhere in the archive proved nothing about their
        # relationship: Codex swapped two rows' cutoffs and the old check passed
        # (SEQ 1559 item 3). The archive states each accepted checkpoint as ONE
        # structured line; that line is parsed and bound field by field.
        try:
            tuples = accepted_tuples(ab.decode("utf-8"))
        except UnicodeDecodeError:
            bad.append("%s@%s: acceptance archive is not valid UTF-8" % key)
            continue
        hits = [t for t in tuples if t["sha256"] == r["sha256"]]
        if len(hits) != 1:
            bad.append("%s@%s: acceptance archive states %d tuples with this digest, "
                       "expected exactly one" % (key + (len(hits),)))
            continue
        t = hits[0]
        for field in ("owner", "cutoff", "bytes"):
            if str(t[field]) != str(r[field]):
                bad.append("%s@%s: the archive binds this digest to %s %r, the row "
                           "says %r" % (key + (field, t[field], r[field])))
        if t["evidence_path"] and t["evidence_path"] != r["evidence_path"]:
            bad.append("%s@%s: the archive binds this digest to evidence %r, the row "
                       "says %r" % (key + (t["evidence_path"], r["evidence_path"])))
    return bad


#: One accepted checkpoint as the archive states it, on one line:
#:   * <owner> @ <cutoff> — <64-hex> — <bytes> bytes [— `<evidence path>`]
#: The pattern RECOGNISES the archive's own line shape; every decision is a field
#: comparison against the inventory row.
_TUPLE = re.compile(r"^\* (?P<owner>\S+) @ (?P<cutoff>\d+) — (?P<sha256>[0-9a-f]{64})"
                    r" — (?P<bytes>\d+) bytes(?: — `(?P<evidence_path>[^`]+)`)?\s*$")


def accepted_tuples(text):
    """-> every structured checkpoint tuple the archive states, in order."""
    out = []
    for line in text.split("\n"):
        m = _TUPLE.match(line)
        if m:
            d = m.groupdict()
            d["evidence_path"] = d.get("evidence_path") or ""
            out.append(d)
    return out


def main():
    bad = failures()
    for b in bad:
        print("FAIL %s" % b)
    if bad:
        print("ACCEPTED-CHECKPOINT INVENTORY REJECTED (%d defects)" % len(bad))
        return 1
    for r in rows():
        print("  %-24s @%-6s %s %9s bytes  %s"
              % (r["owner"], r["cutoff"], r["sha256"][:16], r["bytes"],
                 r["accepted_in"]))
    print("INVENTORY OK: %d accepted checkpoints, each verified against its evidence "
          "and its pinned acceptance archive" % EXPECTED_ROWS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
