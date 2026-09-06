# -*- coding: utf-8 -*-
"""Propose a NEW owner-snapshot root; never edit the published one (SEQ 1781).

The root pins the audit owner, so the corrected owner needs its OWN root. This
freezes one at the SAME logical candidate/run identity but a NEW durable
output, then proves its ONLY difference from the published root is the audit
owner hash. It is a proposal; it authorizes no call.
"""
import hashlib, io, json, os, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
CAND = S + "/g1_precall_cand_1525"
#: the SAME logical run identity; only the durable backing differs
NEW_RUN = S + "/g1_precall_run_1525"
OLD_ROOT = ("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1778/"
            "out/g1_precall_run_1525/root.json")
OUT = "/tmp/a7_logs_1781"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
CANDIDATE = "2be60129ee18c99996b31079b155d3f4558bec4141e1d3574cdb8b3129c7746a"
PUBLISHED_ROOT = "9af8e5ca553e0a4cf0dff2107fef4b8e6ffe0f4e50c72b429554c5cbe72a1691"
import a7_g1_build as G                                          # noqa: E402


def diff(a, b, path=""):
    out = []
    # compare by STRUCTURE: the owner builds OrderedDicts, json.load builds
    # plain dicts, and that difference is not a difference in the root
    if isinstance(a, dict) != isinstance(b, dict) or isinstance(a, list) != isinstance(b, list):
        return [(path, a, b)]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k), b.get(k), path + "/" + str(k))
    elif isinstance(a, list):
        if len(a) != len(b):
            return [(path + "[len]", len(a), len(b))]
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, path + "[%d]" % i)
    elif a != b:
        out.append((path, a, b))
    return out


def main():
    old = json.load(io.open(OLD_ROOT, encoding="utf-8"))
    assert hashlib.sha256(io.open(OLD_ROOT, "rb").read()).hexdigest() == PUBLISHED_ROOT
    root, root_sha, problems = G.freeze_root(CAND, NEW_RUN, CANDIDATE)
    if problems:
        print("REFUSED:", problems[:3]); return 1
    d = diff(old, root)
    print("published root : %s" % PUBLISHED_ROOT)
    print("proposed root  : %s  (%d bytes)"
          % (root_sha, os.path.getsize(G.root_path(NEW_RUN))))
    print("differences    : %d" % len(d))
    for p, a, b in d:
        print("   %-34s %s -> %s" % (p, str(a)[:34], str(b)[:34]))
    only_owner = (len(d) == 1 and d[0][0].startswith("/owners/"))
    print("ONLY the audit owner differs:", only_owner)
    print("rows %d (was %d), candidate %s"
          % (len(root["rows"]), len(old["rows"]), root["candidate_sha256"][:16]))
    os.makedirs(OUT, exist_ok=True)
    io.open(OUT + "/ROOT_PROPOSAL.json", "w", encoding="utf-8").write(json.dumps(
        {"published_root": PUBLISHED_ROOT, "proposed_root": root_sha,
         "differences": [{"path": p, "published": a, "proposed": b} for p, a, b in d],
         "only_audit_owner_differs": only_owner,
         "rows": len(root["rows"]), "candidate_sha256": root["candidate_sha256"]},
        indent=1) + "\n")
    return 0 if only_owner else 1


if __name__ == "__main__":
    sys.exit(main())
