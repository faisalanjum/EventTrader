# -*- coding: utf-8 -*-
"""Recreate the ORIGINAL G1 root through the existing owner (SEQ 1778 item 1).

G.freeze_root writes the root itself, with its own serializer. Nothing here
composes or edits a root: the saved 35877-byte identity is an END assertion
checked after the owner has written it.
"""
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
CAND = S + "/g1_precall_cand_1525"
RUN = S + "/g1_precall_run_1525"
OUT = "/tmp/a7_logs_1778"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

CANDIDATE = "2be60129ee18c99996b31079b155d3f4558bec4141e1d3574cdb8b3129c7746a"
WANT_ROOT = "9af8e5ca553e0a4cf0dff2107fef4b8e6ffe0f4e50c72b429554c5cbe72a1691"
WANT_BYTES = 35877

import a7_g1_build as G                                          # noqa: E402


def main():
    root, root_sha, problems = G.freeze_root(CAND, RUN, CANDIDATE)
    if problems:
        print("REFUSED:", problems[:3])
        return 1
    p = G.root_path(RUN)
    size = os.path.getsize(p)
    body = io.open(p, "rb").read()
    print("root written : %s" % p)
    print("  sha256     : %s" % root_sha)
    print("  required   : %s" % WANT_ROOT)
    print("  bytes      : %d (required %d)" % (size, WANT_BYTES))
    # the original serializer, re-derived independently of the owner's write
    again = json.dumps(root, indent=1, sort_keys=True) + "\n"
    print("  serializer reproduces the bytes: %s"
          % (hashlib.sha256(again.encode("utf-8")).hexdigest()
             == hashlib.sha256(body).hexdigest()))
    print("  rows       : %d" % len(root.get("rows", [])))
    ok = (root_sha == WANT_ROOT and size == WANT_BYTES)
    print("MATCH:", ok)
    os.makedirs(OUT, exist_ok=True)
    io.open(OUT + "/ROOT_CHECK.json", "w", encoding="utf-8").write(json.dumps(
        {"root_sha256": root_sha, "required": WANT_ROOT, "bytes": size,
         "required_bytes": WANT_BYTES, "rows": len(root.get("rows", [])),
         "match": ok}, indent=1) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
