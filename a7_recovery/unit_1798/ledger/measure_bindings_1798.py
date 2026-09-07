# -*- coding: utf-8 -*-
"""Measure the ACTUAL native bindings before declaring any pending lane's input.

Codex SEQ 1798 item 2. Nothing here is assumed and nothing is taken from a
Python environment assignment: the executable is resolved and hashed, the bound
session is read from the runtime's own transcript, and the administrative
payload is measured from records the runtime actually wrote - the parent's own,
and the ones it projected into the served subagents of the published batch.
The two published binaries are compared at the projection site itself.
"""
import collections
import hashlib
import io
import json
import os
import re
import subprocess
import sys

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
DECL = R + "/unit_1792/evidence/declared_input_attachments.json"
CAP = R + "/unit_1786/capture/after/wf_41b934cf-f76"
SID = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
PROJ = "/home/faisal/.claude/projects/-home-faisal-EventMarketDB"
VERS = os.path.expanduser("~/.local/share/claude/versions")
LINK = os.path.expanduser("~/.local/bin/claude")
NEEDLE = b"sendUserFileHint"


def sha(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def canon(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def sites(path, needle):
    """Every offset of `needle`, with the surrounding readable context."""
    data = io.open(path, "rb").read()
    out = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        ctx = data[max(0, i - 160):i + 160]
        out.append((i, re.sub(rb"[^\x20-\x7e]", b".", ctx).decode("ascii")))
        start = i + 1
    return out, len(data)


def main():
    decl = json.load(io.open(DECL, encoding="utf-8"))
    declared = decl["attachments"][0]
    origin = decl["origin"]

    live = os.path.realpath(LINK)
    old = os.path.join(VERS, origin["runtime"])
    doc = collections.OrderedDict()
    doc["executable"] = collections.OrderedDict([
        ("link", LINK), ("resolves_to", live),
        ("version_reported", subprocess.run(["claude", "--version"], capture_output=True,
                                            text=True).stdout.strip()),
        ("sha256", sha(live)),
        ("declared_runtime", origin["runtime"]),
        ("declared_runtime_sha256", origin["runtime_sha256"]),
        ("declared_binary_still_present", os.path.isfile(old)),
        ("declared_binary_sha256", sha(old) if os.path.isfile(old) else None),
        ("running_the_declared_binary", os.path.realpath(live) == os.path.realpath(old))])
    doc["executable"]["declared_binary_hash_holds"] = (
        doc["executable"]["declared_binary_sha256"] == origin["runtime_sha256"])

    doc["session"] = collections.OrderedDict([
        ("bound_sid", SID),
        ("transcript", os.path.join(PROJ, SID + ".jsonl")),
        ("transcript_present", os.path.isfile(os.path.join(PROJ, SID + ".jsonl"))),
        ("declared_parent_bridge_session_id", origin["parent_bridge_session_id"])])

    # ---- what the runtime writes for ITSELF, now ---------------------------
    parent, kinds = collections.Counter(), collections.Counter()
    newest = None
    for n, line in enumerate(io.open(doc["session"]["transcript"], encoding="utf-8"), 1):
        if '"attachment"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") != "attachment":
            continue
        obj = rec.get("attachment")
        if not isinstance(obj, dict):
            continue
        kinds[obj.get("type")] += 1
        if obj.get("type") == declared["object"]["type"]:
            parent[canon(obj)] += 1
            newest = (n, obj)
    doc["parent_records"] = collections.OrderedDict([
        ("of_the_declared_type", sum(parent.values())),
        ("distinct_payloads", len(parent)),
        ("payload_hashes", dict(parent)),
        ("newest_line", newest[0] if newest else None),
        ("newest_payload", newest[1] if newest else None)])

    # ---- what the runtime PROJECTED into the served subagents --------------
    served = collections.Counter()
    for name in sorted(os.listdir(CAP)):
        if not (name.startswith("agent-") and name.endswith(".jsonl")):
            continue
        try:
            recs = [json.loads(l) for l in io.open(os.path.join(CAP, name),
                                                   encoding="utf-8") if l.strip()]
        except ValueError:
            continue
        for rec in recs:
            obj = rec.get("attachment")
            if isinstance(obj, dict) and obj.get("type") == declared["object"]["type"]:
                served[canon(obj)] += 1
    doc["subagent_projection_in_the_published_batch"] = collections.OrderedDict([
        ("records", sum(served.values())), ("distinct_payloads", len(served)),
        ("payload_hashes", dict(served)),
        ("declared_sha256", declared["canonical_sha256"]),
        ("matches_the_declaration",
         list(served) == [declared["canonical_sha256"]])])

    # ---- the difference, field by field ------------------------------------
    diff = []
    if newest:
        for key in sorted(set(newest[1]) | set(declared["object"])):
            a, b = declared["object"].get(key), newest[1].get(key)
            if a != b:
                diff.append({"field": key, "declared": a, "parent_now": b})
    doc["field_difference_parent_now_vs_declared"] = diff

    # ---- the projection site in both binaries ------------------------------
    binaries = collections.OrderedDict()
    for label, path in (("declared_%s" % origin["runtime"], old), ("live", live)):
        if not os.path.isfile(path):
            binaries[label] = {"present": False}
            continue
        found, size = sites(path, NEEDLE)
        binaries[label] = collections.OrderedDict([
            ("present", True), ("bytes", size), ("occurrences", len(found)),
            ("offsets", [o for o, _c in found]),
            ("context", [c for _o, c in found][:2])])
    doc["projection_site"] = binaries
    ctxs = {l: b.get("context") for l, b in binaries.items() if b.get("present")}
    doc["projection_context_identical_across_binaries"] = (
        len(ctxs) == 2 and len(set(map(str, ctxs.values()))) == 1)

    io.open(U + "/evidence/NATIVE_BINDINGS_1798.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")

    e = doc["executable"]
    print("  live executable   : %s  (%s)" % (e["version_reported"], e["sha256"][:16]))
    print("  declared runtime  : %s  (%s)  still present %s, hash holds %s"
          % (e["declared_runtime"], e["declared_runtime_sha256"][:16],
             e["declared_binary_still_present"], e["declared_binary_hash_holds"]))
    print("  RUNNING THE DECLARED BINARY: %s" % e["running_the_declared_binary"])
    print("  bound sid         : %s" % doc["session"]["bound_sid"])
    print("  parent records    : %d, %d distinct %s"
          % (doc["parent_records"]["of_the_declared_type"],
             doc["parent_records"]["distinct_payloads"],
             list(doc["parent_records"]["payload_hashes"])))
    p = doc["subagent_projection_in_the_published_batch"]
    print("  batch projection  : %d records, %d distinct, matches declaration %s"
          % (p["records"], p["distinct_payloads"], p["matches_the_declaration"]))
    print("  field differences : %s" % (diff or "none"))
    for label, b in binaries.items():
        print("  %-18s: %s occurrences of the field name, %s bytes"
              % (label, b.get("occurrences"), b.get("bytes")))
    print("  projection context identical across binaries: %s"
          % doc["projection_context_identical_across_binaries"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
