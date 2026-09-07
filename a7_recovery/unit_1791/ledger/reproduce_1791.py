# -*- coding: utf-8 -*-
"""Reproduce the input-shape refusal over the COMPLETE population, read-only.

Codex SEQ 1791 item 2. Runs the PUBLISHED _g1_shape_problems - no copy, no
second rule engine - over all 34 served transcripts of the resumed run: the 30
newly started ones and the 4 cached controls. Nothing is written, changed or
called.
"""
import hashlib, io, json, os, sys, collections
R = "/home/faisal/EventMarketDB-driver-recovery"
V = R + "/a7_recovery/unit_1781/view/harness_g1v3"
D = (R + "/a7_recovery/unit_1786/capture/after/wf_41b934cf-f76")
BEFORE = R + "/a7_recovery/unit_1786/capture/journal.before.jsonl"
sys.path.insert(0, V)
import audit_worker_access as AUD                                # noqa: E402


def jsonl(p):
    out = []
    for l in io.open(p, encoding="utf-8"):
        l = l.strip()
        if l:
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
    return out


cached = {r.get("agentId") for r in jsonl(BEFORE) if r.get("type") == "result"}
rows, payloads = [], collections.Counter()
for name in sorted(os.listdir(D)):
    if not name.startswith("agent-") or not name.endswith(".jsonl"):
        continue
    aid = name[len("agent-"):-len(".jsonl")]
    recs = jsonl(os.path.join(D, name))
    bad = AUD._g1_shape_problems(recs, aid)
    kinds = [r.get("type") for r in recs]
    att = [r for r in recs if not isinstance(r.get("message"), dict)]
    for a in att:
        payloads[hashlib.sha256(
            json.dumps(a, sort_keys=True, separators=(",", ":")).encode()).hexdigest()] += 1
    rows.append({"agent": aid, "cached": aid in cached, "records": len(recs),
                 "problems": len(bad), "first": (bad[0] if bad else None),
                 "types": kinds[:3], "no_message_records": len(att)})

new = [r for r in rows if not r["cached"]]
old = [r for r in rows if r["cached"]]
print("  transcripts examined      : %d  (new %d, cached controls %d)"
      % (len(rows), len(new), len(old)))
print("  NEW refused by the owner  : %d" % sum(1 for r in new if r["problems"]))
print("  cached controls refused   : %d" % sum(1 for r in old if r["problems"]))
print("  new with a no-message rec : %d" % sum(1 for r in new if r["no_message_records"]))
print("  cached with a no-message  : %d" % sum(1 for r in old if r["no_message_records"]))
print("  distinct attachment payloads: %d" % len(payloads))
for h, n in payloads.most_common():
    print("     %s  x%d" % (h, n))
ex = next((r for r in new if r["problems"]), None)
if ex:
    print("  example refusal: %s" % ex["first"])
    print("  its record types: %s" % ex["types"])
io.open("%s/a7_recovery/unit_1791/evidence/REPRODUCTION.json" % R, "w").write(
    json.dumps({"rows": rows,
                "new_refused": sum(1 for r in new if r["problems"]),
                "cached_refused": sum(1 for r in old if r["problems"]),
                "attachment_payloads": dict(payloads)}, indent=1) + "\n")
