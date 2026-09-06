# -*- coding: utf-8 -*-
"""The A4 pipeline's bind map with the three recovered budget inputs (Codex SEQ 1725).

The accepted map is taken as it stands; the event-run row is repointed at the composed
view and the two candidate directories are added, all read-only. Nothing else changes,
so the pipeline sees exactly the inputs it was blocked on and no more.
"""
import io, os, sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
V = UNIT + "/views"
sys.path.insert(0, UNIT + "/launcher")
import boundary                                              # noqa: E402

#: the later rounds' own budget receipts, preserved as inputs of this unit and bound
#: read-only at the paths their owners read
#: the CORRECTED third-round budget generator: the pre-1509 one and everything built on
#: it are kept under superseded/ and are bound nowhere, so the active path can neither
#: reuse them nor write over them (Codex SEQ 1739)
ADD = {"/tmp/claude-1000/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/budget_receipt_1508.py":
           P + "/a4_owner_1726/proved/budget_receipt_1508.43cb6232.py",
       "/tmp/a7_budget_receipt_1505.json":
           P + "/inputs/receipts/a7_budget_receipt_1505.json",
       "/tmp/a7_g1_event_run4": V + "/a7_g1_event_run4",
       "/tmp/a7_g2_candidate": V + "/a7_g2_candidate",
       "/tmp/a7_g3_candidate": V + "/a7_g3_candidate"}

rows, seen = [], set()
for ln in io.open(UNIT + "/launcher/era_1501_map.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg in ADD:
        src, mode = ADD[lg], "ro"
        sha = boundary.source_sha(src)
    elif os.path.isdir(src) and src.endswith("/bench/bench_1306"):
        # the authorized era-owner replacement changes the bench's own manifest, so the
        # row is re-measured rather than left claiming the byte it no longer holds
        sha = boundary.source_sha(src)
    seen.add(lg)
    rows.append("\t".join([lg, src, sha, mode]))
for lg, src in sorted(ADD.items()):
    if lg not in seen:
        rows.append("\t".join([lg, src, boundary.source_sha(src), "ro"]))

# the run views this map repoints are directories; naming them before the loop keeps
# a preserved file from being bound a second time inside one of them
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
# THE CORRECTION PACKAGE IS AN OUTPUT, NOT EVIDENCE. The owner writes each round's
# package under the key directory, so that one directory is bound WRITABLE from a
# durable copy while the bench itself stays read-only.
PKG = S + "/bench_1306/.claude/plans/Drivers/experiments/kfields_key_a4"
rows.append("\t".join([PKG, UNIT + "/pkg/kfields_key_a4",
                       boundary.source_sha(UNIT + "/pkg/kfields_key_a4"), "rw"]))
seen.add(PKG)
print("   RW  %-46s <- pkg/kfields_key_a4" % PKG.replace(S, "S"))

# THE CORRECTION RUN IS AN OUTPUT TOO. Its receipt is rewritten as each saved state is
# recorded, so the run is bound as ONE writable directory rather than a set of read-only
# files; the durable copy under runs_rw carries whatever earlier stages produced.
# THE LOCK WORKSPACE. The final candidate, its signer packet and the lock are written
# under $S/lock by their own owners, so that one directory is bound WRITABLE from the
# durable copy that carries the four closure scripts.
LOCK = S + "/lock"
hit = [k for k, r in enumerate(rows) if r.split("\t")[0] == LOCK]
if len(hit) != 1:
    raise SystemExit("REFUSE: %d lock rows in the map" % len(hit))
rows[hit[0]] = "\t".join([LOCK, UNIT + "/lock",
                          boundary.source_sha(UNIT + "/lock"), "rw"])
seen.add(LOCK)
print("   RW  %-46s <- lock (the evidence copy plus the closure scripts)"
      % LOCK.replace(S, "S"))

RW_RUNS = UNIT + "/runs_rw"
for name in sorted(os.listdir(RW_RUNS)) if os.path.isdir(RW_RUNS) else []:
    lg = "/tmp/" + name
    rows.append("\t".join([lg, os.path.join(RW_RUNS, name),
                           boundary.source_sha(os.path.join(RW_RUNS, name)), "rw"]))
    seen.add(lg)
    print("   RW  %-46s <- runs_rw/%s" % (lg, name))

seen |= set(ADD)
# A STAGE'S OWN OUTPUT IS THE NEXT STAGE'S INPUT, and the namespace keeps nothing:
# every artifact a completed stage preserved is bound back read-only at the historical
# path it was written to, so the sequence continues where it left off instead of
# recomputing a prerequisite that already succeeded.
OUT = UNIT + "/out"
for name in sorted(os.listdir(OUT)) if os.path.isdir(OUT) else []:
    src = os.path.join(OUT, name)
    if not os.path.isfile(src) or name == "ARTIFACTS.tsv":
        continue
    lg = (S + "/" + name[len("scratch__"):]) if name.startswith("scratch__") \
        else "/tmp/" + name.replace("__", "/")
    # a run this map already binds as a whole directory supplies its own files; adding
    # them again would stack a second mount inside a mount for no added guarantee
    if lg in seen or any(lg.startswith(d + "/") for d in seen):
        continue
    seen.add(lg)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "ro"]))
    print("   RO  %-46s <- out/%s" % (lg.replace(S, "S"), name))

# THE LEDGER OWNER OF THE CORRECTION ROUNDS. The accepted map pins the base whose ledger
# has no correction stage at all, so the row is repointed at that base plus the two
# literal substitutions its own saved patch makes.
A6_LOGICAL = (S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
                  "/a6_launch_freeze.py")
# Each correction round is counted by the ledger owner of ITS OWN era, so the wanted
# owner is named as a complete hash (A4_A6, default the round-1 one) and located BY
# HASH among the proved owners - never by a file name that could drift off its bytes.
A6_SHA = os.environ.get("A4_A6") or (
    "7081e9a51a94ca43ea8fee281711337fd8674fe19e1501bd2fca7246a5bddd74")
PROVED = P + "/a4_owner_1726/proved"
A6_SRC = next((os.path.join(PROVED, f) for f in sorted(os.listdir(PROVED))
               if os.path.isfile(os.path.join(PROVED, f))
               and boundary.source_sha(os.path.join(PROVED, f)) == A6_SHA), None)
if A6_SRC is None:
    raise SystemExit("REFUSE: no proved ledger owner at %s" % A6_SHA[:16])
got = boundary.source_sha(A6_SRC)
hit = [k for k, r in enumerate(rows) if r.split("\t")[0] == A6_LOGICAL]
if len(hit) != 1:
    raise SystemExit("REFUSE: %d ledger-owner rows in the map" % len(hit))
rows[hit[0]] = "\t".join([A6_LOGICAL, A6_SRC, got, "ro"])
print("   RO  harness_g1v3/a6_launch_freeze.py <- %s" % got[:16])

io.open(UNIT + "/launcher/a4_final_map.tsv", "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("a4_final_map.tsv: %d rows" % len(rows))
for l in rows:
    c = l.split("\t")
    if c[0] in ADD:
        print("   RO  %-26s <- %s" % (c[0], c[1].replace(UNIT + "/", "")))
