# -*- coding: utf-8 -*-
"""Freeze unit_1881, and verify the sealed unit_1880 is preserved.

unit_1829's manifest listed a hash of ITSELF, which can never be right: the
file's content changes as it is written. This one excludes its own destination
and the temporary file it is written through, lists every other member, then
re-reads and verifies all of them. The manifest's own hash is reported
EXTERNALLY, by this script, not stored inside it.
"""
import hashlib, io, json, os, sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U = A + "/unit_1881"
DEST = U + "/MANIFEST.sha256"
TMP = DEST + ".tmp"


def sha(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


#: Non-regular entries carry no bytes to hash. pytest leaves a dangling
#: `<test name>current` symlink in every basetemp, so the walk sees names that
#: cannot be opened. They are SKIPPED and REPORTED by name, never silently
#: dropped - the same rule the boundary's own dir_manifest_sha applies.
#: A SET, not a list: `members()` is called twice (once to build the manifest,
#: once to prove nothing is unlisted), so a list double-counted every skipped
#: link and reported 202 where there are 101 (Codex SEQ 1879).
SKIPPED = set()


def members(root, excluded):
    got = []
    for base, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(base, f)
            if os.path.abspath(p) in excluded:
                continue
            if os.path.islink(p) or not os.path.isfile(p):
                SKIPPED.add(os.path.relpath(p, root))
                continue
            got.append(os.path.relpath(p, root))
    return sorted(got)


#: The freeze REPORT records the manifest's hash, so the manifest cannot also
#: record the report's - they would chase each other. Both are excluded by
#: NAME, and both hashes are reported externally below. Nothing else may be
#: missing: every other file in the unit must appear.
REPORT = U + "/logs/FREEZE_1881.json"
excluded = {os.path.abspath(x) for x in (DEST, TMP, REPORT)}
rows = [(sha(os.path.join(U, r)), r) for r in members(U, excluded)]
io.open(TMP, "w", encoding="utf-8").write(
    "".join("%s  %s\n" % (s, r) for s, r in rows))
os.replace(TMP, DEST)

# verify every listed member from the manifest as written
listed = [ln.split("  ", 1) for ln in
          io.open(DEST, encoding="utf-8").read().splitlines()]
bad = [r for s, r in listed if sha(os.path.join(U, r)) != s]
assert not bad, bad
assert not os.path.exists(TMP), "temporary destination survived"
assert all(r not in ("MANIFEST.sha256", "MANIFEST.sha256.tmp",
                     "logs/FREEZE_1881.json")
           for _s, r in listed), "the manifest lists an excluded destination"
# nothing may be silently unlisted
present = set(members(U, excluded)) - set(SKIPPED)
assert present == {r for _s, r in listed}, sorted(present ^ {r for _s, r in listed})

# unit_1829 stays preserved: every member it lists, except the self-hash it
# should never have carried, must still match.
p29 = A + "/unit_1880/MANIFEST.sha256"
l29 = [ln.split("  ", 1) for ln in
       io.open(p29, encoding="utf-8").read().splitlines()]
self_rows = [r for _s, r in l29 if r == "MANIFEST.sha256"]
assert not self_rows, "unit_1880 should carry no self row"
bad29 = [r for s, r in l29
         if r != "MANIFEST.sha256" and sha(os.path.join(A, "unit_1880", r)) != s]
out = {
    "unit_1881": {
        "members": len(listed),
        "manifest_external_sha256": sha(DEST),
        "excludes": ["MANIFEST.sha256", "MANIFEST.sha256.tmp",
                     "logs/FREEZE_1881.json"],
        "all_members_verified": not bad,
        "nothing_unlisted": True,
        "non_regular_skipped": len(SKIPPED),
        # DANGLING vs EXISTING aliases, counted apart: an alias that resolves
        # is a second name for a member already listed, not a missing artifact.
        "non_regular_dangling": sum(
            1 for r in SKIPPED if not os.path.exists(os.path.join(U, r))),
        "non_regular_existing_aliases": sum(
            1 for r in SKIPPED if os.path.exists(os.path.join(U, r))),
        "non_regular_names": sorted(SKIPPED)[:6],
    },
    "prior_unit_preserved": {
        "members_listed": len(l29),
        "self_rows_it_should_not_have": self_rows,
        "non_self_members_mismatched": bad29,
    },
}
io.open(U + "/logs/FREEZE_1881.json", "w", encoding="utf-8").write(
    json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
sys.exit(1 if bad or bad29 else 0)
