# -*- coding: utf-8 -*-
"""Codex SEQ 2010 step 1: the minimal PRIVATE native fixture.

It derives the required native states from the two receipts that already own
them, asks the existing transcript owner which child evidence each run really
spawned, and copies those bytes - unchanged, unparsed, unrelabelled - into a
private tree that mirrors the official store's own layout.

NO MODEL IS CALLED. Nothing outside this unit is written. The originals are
only read: their bytes and their exact nanosecond mtimes are recorded as
strings, before and after, so any touch would show.
"""
import collections
import hashlib
import io
import json
import os
import shutil
import sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A + "/unit_2002/owner")
import a4_source_closure as CL                                    # noqa: E402

K = CL.K
BASE = os.path.dirname(CL.PKG_DIR)
RUN = os.path.join(BASE, "review_2004")
PROJECTS = "/home/faisal/.claude/projects"
UNIT = A + "/unit_2010_native_fixture"
PRIV = UNIT + "/native"
MANIFEST = UNIT + "/NATIVE_FIXTURE_MANIFEST.json"


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def mtime(path):
    # STRING-VALUED on purpose: a nanosecond mtime does not survive a JSON
    # number intact, and a silently rounded timestamp proves nothing.
    return str(os.stat(path).st_mtime_ns)


def record(path):
    return collections.OrderedDict([("sha256", fsha(path)),
                                    ("mtime_ns", mtime(path)),
                                    ("bytes", os.path.getsize(path))])


# ---- the required states, from the receipts that own them ---------------
# STEP 1 names the two review receipts. The owner's own context ALSO reads the
# initial source-only collection through SK.accepted_shards, so its receipt is
# derived here from the owner's own INITIAL_RUN rather than assumed: without
# it the historical proof cannot run at all. Each scope is reported separately.
SCOPES = (("primary", RUN, "step1"),
          ("child", os.path.join(RUN, "retry"), "step1"),
          ("initial_collection", CL.INITIAL_RUN, "owner_context"))
states, per_receipt = [], collections.OrderedDict()
by_scope = collections.Counter()
for name, base, scope in SCOPES:
    receipt = K._load(os.path.join(base, K.RECEIPT_NAME))
    owned = list(receipt.get("states") or [])
    per_receipt[name] = collections.OrderedDict(
        [("required_by", scope), ("run_dir", base),
         ("receipt_sha256", K._sha(K._read(os.path.join(base,
                                                        K.RECEIPT_NAME)))),
         ("allowed", len(receipt["allowed"])), ("states", len(owned))])
    by_scope[scope] += len(owned)
    states.extend(owned)
if len(states) != len(set(states)):
    raise ValueError("the two receipts name the same native state twice")

# ---- copy each state and its REAL child evidence ------------------------
before, copied, kinds = collections.OrderedDict(), [], collections.Counter()
for state in states:
    session_dir = os.path.dirname(os.path.dirname(state))
    run_id = os.path.splitext(os.path.basename(state))[0]
    # THE EXISTING OWNER decides what a run spawned; this fixture does not
    # reconstruct a transcript path from a convention of its own.
    wanted = [state] + list(K._spawned_transcripts(session_dir, run_id))
    for src in wanted:
        if not os.path.isfile(src):
            raise ValueError("required native evidence is missing: %s" % src)
        rel = os.path.relpath(src, PROJECTS)
        dst = os.path.join(PRIV, rel)
        before[src] = record(src)
        os.path.isdir(os.path.dirname(dst)) or os.makedirs(
            os.path.dirname(dst))
        if os.path.isfile(dst):
            if fsha(dst) != before[src]["sha256"]:
                raise ValueError("a different private copy already exists: %s"
                                 % dst)
        else:
            shutil.copyfile(src, dst)          # BYTES ONLY; never re-serialised
        if fsha(dst) != before[src]["sha256"]:
            raise ValueError("the private copy is not the original: %s" % dst)
        kinds["state" if src == state else "transcript"] += 1
        copied.append(collections.OrderedDict(
            [("source", src), ("private", dst),
             ("kind", "state" if src == state else "transcript"),
             ("sha256", before[src]["sha256"]),
             ("source_mtime_ns", before[src]["mtime_ns"]),
             ("bytes", before[src]["bytes"])]))

# ---- the originals are untouched ---------------------------------------
after = collections.OrderedDict((p, record(p)) for p in before)
unchanged = [p for p in before if after[p] == before[p]]
moved = [p for p in before if after[p] != before[p]]

doc = collections.OrderedDict([
    ("kind", "private native fixture for the preserved review states; no call"),
    ("closure_owner_sha256", fsha(CL.__file__.rstrip("c"))),
    ("key_owner_sha256", fsha(K.__file__.rstrip("c"))),
    ("projects_root", PROJECTS), ("private_root", PRIV),
    ("receipts", per_receipt),
    ("states_by_scope", dict(by_scope)),
    ("required_states", len(states)),
    ("copied_files", len(copied)),
    ("copied_by_kind", dict(kinds)),
    ("originals_unchanged", len(unchanged)),
    ("originals_moved", moved),
    ("files", copied)])

res = collections.OrderedDict()
if os.path.isfile(MANIFEST):
    old = json.loads(io.open(MANIFEST, encoding="utf-8").read())
    res["manifest"] = "already frozen; not rewritten"
    res["identical"] = old == doc
else:
    K.RT.write_new(MANIFEST, json.dumps(doc, indent=1))
    res["manifest"] = "frozen"
    res["identical"] = True
res["manifest_sha256"] = fsha(MANIFEST)
for key in ("receipts", "required_states", "copied_files", "copied_by_kind",
            "originals_unchanged", "originals_moved"):
    res[key] = doc[key]
res["states_by_scope"] = doc["states_by_scope"]
res["ok"] = (doc["states_by_scope"].get("step1") == 80
             and not doc["originals_moved"]
             and res["identical"]
             and doc["originals_unchanged"] == len(before))
print(json.dumps(res, indent=1, default=str))
raise SystemExit(0 if res["ok"] else 3)
