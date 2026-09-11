# -*- coding: utf-8 -*-
"""Codex SEQ 2013: derive the smallest complete publication inventory.

NOTHING IS STAGED, COMMITTED OR COPIED. This reads live code, the active
boundary maps and the frozen review manifests and writes ONE list: path, byte
hash, size, tracked state and why it is there. Every population is DERIVED -
the executable closure from the modules that actually load, the data closure
from the maps that actually served the verified runs, and the reviewed file
population of a large unit from that unit's own frozen manifest, which is what
keeps a 41 GB scratch tree out of the proposal.
"""
import collections, hashlib, io, json, os, subprocess, sys

ROOT = "/home/faisal/EventMarketDB-driver-recovery"
A = ROOT + "/a7_recovery"
OUT = A + "/unit_2013_publication_inventory"

#: units whose reviewed population is defined by their OWN frozen manifest
SNAPSHOT_UNITS = ("unit_2002", "unit_2005", "unit_2006")
#: the boundary maps that actually served verified work, newest binding last
ACTIVE_MAPS = (
    ("unit_2006/map_review_retry_live_2006.tsv", "served the approved child review collection"),
    ("unit_2008/map_review_2008.tsv", "served the clarified-wrapper preparation"),
    ("unit_2009/map_integration_a.tsv", "served the final-key join positive"),
    ("unit_2010_native_fixture/map_native_2010.tsv", "served the private native fixture proof"),
    ("unit_2011_retention_review/map_retention_2011.tsv", "served the retention review"),
    ("unit_2012_final_join_review/map_join_2012.tsv", "served the final-join review"),
)
#: raw proof to publish with the code it proves
PROOF_ATTEMPTS = (
    ("codex_join2009_a", "the final-key join positive"),
    ("core_oldproof2008_a", "the old run proved under its own binding"),
    ("core_prep2008_d", "the clarified four-seat preparation"),
    ("core_bat2008_final", "the clarified-wrapper battery"),
    ("core_probe2010_b", "the private native fixture proof"),
    ("core_retention2011_d", "the retention review"),
    ("core_gate2011_a", "the closeout-gate isolation"),
    ("core_join2012_c", "the final-join review"),
)
#: named exclusions, each with the reason it is not published
EXCLUDE_MARKERS = (
    ("__pycache__", "build artefact"),
    (".pytest_cache", "test scratch"),
    ("/integration_", "private fixture clone"),
    ("/TEST_projects/", "private native fixture clone"),
    ("/TEST_join_clone/", "private fixture clone"),
    ("/lifecycle_projects", "private fixture clone"),
    ("/regression_", "duplicate regression scratch"),
    ("/bat2008_", "battery scratch run"),
    ("/native/", "private native copy, named separately"),
)
#: my own independent-review units. Their local trees are CLONES of evidence
#: that is already included from the unit that owns it, so only their own
#: top-level scripts, maps and reports are published.
REVIEW_UNITS = ("unit_2010_native_fixture", "unit_2011_retention_review",
                "unit_2012_final_join_review")
NAMED_EXCLUSIONS = (
    ("a7_recovery/unit_2008/owner/a4_review_composite.py",
     "the REJECTED record-based composite; superseded by the unit_2009 adapter"),
    ("a7_recovery/unit_2006/harness_g1v3/a7_prepared_run.py",
     "unserved cold variant; not pinned by its unit's own manifest"),
    ("a7_recovery/grader_20260909/harness_g1v3/build_inventory_review.py",
     "pre-existing dirty tracked file; not part of this scope"),
)


def rel(p):
    return os.path.relpath(os.path.abspath(p), ROOT)


def fsha(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


GIT = ["git", "--git-dir=%s/.git" % ROOT, "--work-tree=%s" % ROOT]


def git(*args):
    env = dict(os.environ)
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return subprocess.check_output(GIT + list(args), env=env).decode("utf-8")


tracked = set(git("ls-files").splitlines())

entries, excluded = collections.OrderedDict(), []


def excluded_reason(path):
    r = rel(path)
    for marker, why in EXCLUDE_MARKERS:
        if marker in "/" + r:
            return why
    for named, why in NAMED_EXCLUSIONS:
        if r == named:
            return why
    return None


def add(path, reason, kind):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return
    r = rel(path)
    if r.startswith(".."):
        return                                   # outside the repository
    why = excluded_reason(path)
    if why:
        excluded.append((r, why))
        return
    if r in entries:
        return
    entries[r] = collections.OrderedDict(
        [("path", r), ("kind", kind), ("reason", reason),
         ("bytes", os.path.getsize(path)),
         ("tracked", r in tracked), ("sha256", fsha(path))])


def add_tree(root, reason, kind):
    for d, _s, fs in os.walk(root):
        for n in sorted(fs):
            add(os.path.join(d, n), reason, kind)


# ---- 1. the EXECUTABLE closure: what actually loads -------------------
sys.path.insert(0, A + "/unit_2009/owner")
import a4_review_composite as RC                                  # noqa: E402
sys.path.insert(0, A + "/unit_2005/owner")
import a4_source_candidate as SC                                  # noqa: E402
loaded = []
for name, mod in sorted(sys.modules.items()):
    f = getattr(mod, "__file__", None)
    if f and os.path.abspath(f).startswith(ROOT):
        loaded.append((name, os.path.abspath(f).rstrip("c")))
for name, f in loaded:
    add(f, "callable dependency actually imported by the reviewed owners",
        "executable")
add(RC.OLD_OWNER_PATH, "the historical review owner the adapter loads by path",
    "executable")

# ---- 2. the DATA closure: what the active maps really serve ----------
map_sources = []
for m, why in ACTIVE_MAPS:
    p = os.path.join(A, m)
    if not os.path.isfile(p):
        continue
    add(p, "active boundary map: " + why, "data")
    for line in io.open(p, encoding="utf-8"):
        if not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        map_sources.append((parts[1], m))

# ---- 3. the REVIEWED population of a large unit is its OWN manifest ---
snapshot_counts = collections.OrderedDict()
for unit in SNAPSHOT_UNITS:
    snap = os.path.join(A, unit, "REVIEW_SNAPSHOT.json")
    if not os.path.isfile(snap):
        continue
    add(snap, "the frozen review manifest that defines this unit's reviewed "
              "population", "data")
    doc = json.loads(io.open(snap, encoding="utf-8").read())
    n = 0
    for e in doc.get("entries") or []:
        p = os.path.join(ROOT, e["path"])
        if e.get("kind") == "file":
            add(p, "pinned by %s's frozen review manifest" % unit, "data")
            n += 1
        else:
            add_tree(p, "pinned directory in %s's frozen review manifest"
                     % unit, "data")
            n += 1
    for f in doc.get("files") or []:
        p = os.path.join(ROOT, f["path"] if isinstance(f, dict) else f)
        add(p, "pinned by %s's frozen review manifest" % unit, "data")
        n += 1
    snapshot_counts[unit] = n

# ---- 4. the data every map row names, when it is inside the repo ------
#    A map's binding to a tree inside one of MY review units is a private
#    clone of evidence already included from its owning unit; only cross-unit
#    bindings are real dependencies.
clone_bindings = []
for src, m in map_sources:
    owner_unit = m.split("/")[0]
    if owner_unit in REVIEW_UNITS and os.path.abspath(src).startswith(
            os.path.join(A, owner_unit) + os.sep):
        clone_bindings.append(rel(src))
        continue
    if os.path.isfile(src):
        add(src, "bound by %s" % m, "data")
    elif os.path.isdir(src):
        add_tree(src, "bound by %s" % m, "data")

# ---- 5. raw proof, published with the code it proves ------------------
for tag, why in PROOF_ATTEMPTS:
    d = os.path.join(A, "unit_1947", "logs", "attempt_" + tag)
    for n in ("stdout.txt", "stderr.txt", "exit", "owner.tsv"):
        add(os.path.join(d, n), "raw proof of " + why, "proof")

# ---- 6. the review reports and their own checkers ---------------------
for unit, why in (("unit_2010_native_fixture", "the private native fixture"),
                  ("unit_2011_retention_review", "the retention review"),
                  ("unit_2012_final_join_review", "the final-join review")):
    for n in sorted(os.listdir(os.path.join(A, unit))):
        p = os.path.join(A, unit, n)
        if os.path.isfile(p):
            add(p, "independent review evidence for " + why, "proof")

# ---- the report -------------------------------------------------------
by_kind = collections.Counter(e["kind"] for e in entries.values())
untracked = [e for e in entries.values() if not e["tracked"]]
big = [e for e in entries.values() if e["bytes"] > 100 * 1024 * 1024]
total = sum(e["bytes"] for e in entries.values())
doc = collections.OrderedDict([
    ("kind", "publication INVENTORY PROPOSAL; nothing staged, committed or copied"),
    ("branch", git("rev-parse", "--abbrev-ref", "HEAD").strip()),
    ("head", git("rev-parse", "HEAD").strip()),
    ("files", len(entries)), ("bytes", total),
    ("mib", round(total / 1048576.0, 1)),
    ("by_kind", dict(by_kind)),
    ("already_tracked", len(entries) - len(untracked)),
    ("to_add", len(untracked)),
    ("over_100_mib", [e["path"] for e in big]),
    ("modules_loaded_from_the_repo", len(loaded)),
    ("snapshot_defined_entries", snapshot_counts),
    ("to_add_by_unit", collections.OrderedDict(sorted(collections.Counter(
        e["path"].split("/")[1] if e["path"].startswith("a7_recovery/")
        else e["path"].split("/")[0]
        for e in untracked).items(), key=lambda kv: -kv[1]))),
    ("to_add_bytes_by_unit", collections.OrderedDict(sorted(
        [(u, sum(e["bytes"] for e in untracked
                 if (e["path"].split("/")[1]
                     if e["path"].startswith("a7_recovery/")
                     else e["path"].split("/")[0]) == u))
         for u in {(e["path"].split("/")[1]
                    if e["path"].startswith("a7_recovery/")
                    else e["path"].split("/")[0]) for e in untracked}],
        key=lambda kv: -kv[1]))),
    ("private_clone_bindings_skipped", sorted(set(clone_bindings))),
    ("external_native_evidence", collections.OrderedDict([
        ("what", "the 113 native states and 113 child transcripts the reviewed "
                 "owners re-prove, which live outside this repository in the "
                 "runtime's own store"),
        ("durable_private_copy", rel(A + "/unit_2010_native_fixture/native")),
        ("files", sum(len(f) for _d, _s, f in os.walk(
            A + "/unit_2010_native_fixture/native"))),
        ("bytes", sum(os.path.getsize(os.path.join(d, n))
                      for d, _s, fs in os.walk(
                          A + "/unit_2010_native_fixture/native")
                      for n in fs)),
        ("manifest", rel(A + "/unit_2010_native_fixture/"
                         "NATIVE_FIXTURE_MANIFEST.json")),
        ("decision", "NOT included by this proposal: naming it is required, "
                     "publishing it is Codex's call")])),
    ("excluded_examples", excluded[:6]),
    ("excluded_total", len(excluded)),
    ("entries", list(entries.values()))])
io.open(OUT + "/PUBLICATION_INVENTORY.json", "w", encoding="utf-8").write(
    json.dumps(doc, indent=1))
io.open(OUT + "/PUBLICATION_INVENTORY.txt", "w", encoding="utf-8").write(
    "".join("%-10s %-9s %12d  %s  %s\n"
            % (e["kind"], "tracked" if e["tracked"] else "TO ADD",
               e["bytes"], e["sha256"][:16], e["path"])
            for e in entries.values()))
summary = {k: v for k, v in doc.items() if k != "entries"}
print(json.dumps(summary, indent=1, default=str))
