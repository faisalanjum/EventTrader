# -*- coding: utf-8 -*-
"""Restore each exact launcher from its named official state (Codex SEQ 1696 item 1).

Supersedes the earlier render attempt: under Codex's epoch rule an earlier bound
run's launcher is NEVER re-rendered with the final owners. The bytes are already
durable inside the receipt-named official state's `script` field, so they are
restored, not produced.

Every file passes the four-way join before it is written:
  1. the manifest row's `wf` names an official state present in the unit;
  2. that state's `runId` equals the same `wf`;
  3. that state's `scriptPath` equals the manifest path exactly;
  4. SHA-256 of the state `script` UTF-8 bytes equals the manifest pin AND its
     byte length equals the manifest length.
A duplicate destination, a missing state, or any mismatch REFUSES that row and
the run; nothing partial is accepted. No model is called and nothing is rendered.
"""
import hashlib
import io
import json
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
T = R + "/a4_recovery/regen_1570/targeted_1589"
UNIT = T + "/post_1500_exact_1626/out/a4_final_lock_1683"
SESS = (UNIT + "/session_store/projects/-home-faisal-EventMarketDB"
               "/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/workflows")
RUNS = UNIT + "/runs"
LAUNCH = UNIT + "/launch"

SPECS = [("a4_targeted_run_1491", T + "/targeted_run_1491/out/attempt6/A/LAUNCHERS.tsv"),
         ("a4_hard_review_run_1495", T + "/hard_review_1495/out/attempt10/A/LAUNCHERS.tsv"),
         ("a4_final_targeted_run_1500", T + "/final_adjudication_1500/out/attempt5/A/LAUNCHERS.tsv")]

problems, written, verified = [], [], 0
seen_dst = {}


def sha(b):
    return hashlib.sha256(b).hexdigest()


for run, tsv in SPECS:
    rows = [l for l in io.open(tsv, encoding="utf-8").read().splitlines() if l.strip()]
    hdr = rows[0].split("\t")
    i_wf, i_sp, i_sha, i_by = (hdr.index("wf"), hdr.index("scriptPath"),
                               hdr.index("sha256"), hdr.index("bytes"))
    for r in rows[1:]:
        c = r.split("\t")
        wf, spath, pin, nbytes = c[i_wf], c[i_sp], c[i_sha], int(c[i_by])

        # (1) the named official state must be present in the unit
        state_path = os.path.join(SESS, wf + ".json")
        if not os.path.isfile(state_path):
            problems.append("%s %s: no official state in the unit" % (run, wf))
            continue
        try:
            st = json.load(io.open(state_path, encoding="utf-8"))
        except Exception as exc:                                 # noqa: BLE001
            problems.append("%s %s: state unreadable (%s)" % (run, wf, exc))
            continue

        # (2) the state must name itself
        if st.get("runId") != wf:
            problems.append("%s %s: state runId is %r" % (run, wf, st.get("runId")))
            continue
        # (3) the state must name the same script path
        if st.get("scriptPath") != spath:
            problems.append("%s %s: state scriptPath %r != manifest %r"
                            % (run, wf, st.get("scriptPath"), spath))
            continue
        # (4) the bytes must be the pinned bytes, at the pinned length
        script = st.get("script")
        if not isinstance(script, str):
            problems.append("%s %s: state carries no script text" % (run, wf))
            continue
        b = script.encode("utf-8")
        if sha(b) != pin or len(b) != nbytes:
            problems.append("%s %s: script sha/len %s/%d != pinned %s/%d"
                            % (run, wf, sha(b)[:16], len(b), pin[:16], nbytes))
            continue

        rel = spath[len("/tmp/"):] if spath.startswith("/tmp/") else os.path.basename(spath)
        top = rel.split("/")[0]
        dst = os.path.join(RUNS if os.path.isdir(os.path.join(RUNS, top)) else LAUNCH, rel)
        if dst in seen_dst and seen_dst[dst] != pin:
            problems.append("duplicate destination %s from %s and %s"
                            % (dst, seen_dst[dst][:16], pin[:16]))
            continue
        seen_dst[dst] = pin

        if os.path.isfile(dst):
            if sha(io.open(dst, "rb").read()) == pin:
                verified += 1
                continue
            problems.append("REFUSE differing byte already at %s" % dst)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with io.open(dst, "w", encoding="utf-8", newline="") as fh:
            fh.write(script)
        if sha(io.open(dst, "rb").read()) != pin:
            problems.append("REFUSE write mismatch at %s" % dst)
            continue
        written.append((os.path.relpath(dst, UNIT), pin))
        verified += 1

man = UNIT + "/manifest/LAUNCHERS_RESTORED.tsv"
with io.open(man, "w", encoding="utf-8") as fh:
    fh.write("dest_rel\tsha256\tsource\n")
    for rel, h in sorted(written):
        fh.write("%s\t%s\t%s\n" % (rel, h, "official state script (four-way join)"))

print("launchers verified against their pins : %d" % verified)
print("newly restored from official states   : %d" % len(written))
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems[:15]:
        print("   " + p)
    sys.exit(1)
print("LAUNCHERS RESTORED OK")
