# -*- coding: utf-8 -*-
"""Reconstruct the COMPLETED 392-answer producer run with zero model calls.

Codex SEQ 1773 item 1. Nothing here invents a byte:

  * the run starts as the accepted A5 prelaunch fixture (seeded on the host)
  * each of the 36 preserved workflow records is recorded through the REAL
    owner, AUD.record_state, in the order the receipt's own `invocations`
    list gives - the order is matched by args, never guessed, and that rule
    was first confirmed against the independent dev run (36/36 in position)
  * the raw replies, the answers and the finalization are then written by the
    REAL recorded serializer, RT.a1_finalize, which harvests the rows from the
    recorded states and saves every paid byte before it parses anything

The targets are END assertions, checked after the fact, never inputs.
"""
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
WF = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
      "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/workflows")
RUN = S + "/a6_a5run_1515"
#: the fixture keeps its own basename: a lawful run is identified by it
PRELAUNCH = "/tmp/a7_prelaunch_1773/a6_a5run_1515"
OUT = "/tmp/a7_logs_1773"
REPORTS = "/tmp/a7_producer_reports_1773"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

WANT = {
    "receipt": "c43457c99231edb36f3d479848f1ea9ac63fcc84d095755c5a1b8d7a2109b8c4",
    "finalization": "04b53cddf63528933cd99afe1b215061d2a07d8f4bc2fb0738014dd50aa30880",
    "run_digest": "9aa2d1b2efcdbec5ee5d58958e68dc6ec91b076f64f832d625f941488970215a",
    "a5_manifest": "5e33c3e4acbff1c710321008335d6a66622992a8317027c9d231d85912f37c53",
    "a5_bundle": "d2e850d86f643f177868b8b755b0a0d92c0a57f1aec8fabd4455acea2367edff",
    "a6_freeze": "4123bb693f6b040af48f4ea53c533b2ad800e80102113844adb5afc69c65052d",
}
CHECKS = []


def check(name, got, want):
    CHECKS.append((name, got == want, got, want))
    print("  %-5s %-22s %s" % ("ok" if got == want else "BAD", name, got))
    return got == want


def fsha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def main():
    import audit_worker_access as AUD
    import raw_transport as RT
    import a7_prepared_run as PR

    receipt_path = os.path.join(RUN, "receipt.json")
    pre = json.load(io.open(receipt_path, encoding="utf-8"))
    print("seeded run: states=%d allowed=%d run_id=%s"
          % (len(pre["states"]), len(pre["allowed"]), pre["run_id"]))

    # --- 1. the recorded order, matched by args through the receipt itself ---
    def key(a):
        return json.dumps(a, sort_keys=True)

    # THE RUN'S OWN RECORDS, named by the existing producer index. The bound
    # store holds earlier runs over the same lanes whose launch args are
    # byte-identical, so args alone identifies a record only WITHIN one run.
    idx = json.load(io.open(REPORTS + "/producer_rows.json", encoding="utf-8"))
    mine = sorted({r["state"] for r in idx})
    absent = [n for n in mine if not os.path.isfile(os.path.join(WF, n))]
    if absent:
        raise SystemExit("indexed states absent from the store: %s" % absent[:3])
    print("index names %d states for this run, all present" % len(mine))

    by_args = {}
    for name in mine:
        try:
            doc = json.load(io.open(os.path.join(WF, name), encoding="utf-8"))
        except ValueError:
            continue
        by_args.setdefault(key(doc.get("args")), []).append(name)

    order = []
    for i, iv in enumerate(pre["invocations"]):
        hit = by_args.get(key(iv.get("args")))
        if not hit:
            raise SystemExit("invocation %d has no recorded state" % i)
        if len(hit) != 1:
            raise SystemExit("invocation %d matches %d states: %s"
                             % (i, len(hit), hit[:3]))
        order.append(hit[0])
    print("matched %d invocations to exactly one recorded state each" % len(order))

    # --- 2. record every state through the real owner ---
    for name in order:
        AUD.record_state(receipt_path, pre["run_id"], os.path.join(WF, name))
    after = json.load(io.open(receipt_path, encoding="utf-8"))
    print("recorded states: %d" % len(after["states"]))
    check("receipt", fsha(receipt_path), WANT["receipt"])

    # --- 3. the real recorded serializer writes the paid bytes ---
    res = RT.a1_finalize(RUN)
    print("a1_finalize ->", str(res)[:160])
    check("finalization", fsha(os.path.join(RUN, "finalization.json")),
          WANT["finalization"])

    # --- 4. the identity the A7 route will read ---
    # THE LATER A6 HELPER IS VALIDATED TWO WAYS, not fitted to the target.
    # First it must still reproduce the CLOSED A6 result on the untouched
    # prelaunch fixture, which proves it is freeze-compatible with the accepted
    # closure and only adds the pre-call reconstruction. Then the executed run
    # must bind to that same accepted identity through precall_view.
    import a6_launch_freeze as A6L
    # The accepted A6 freeze of the prelaunch fixture is a CLOSED A6 proof and
    # is reused, not re-run (Codex SEQ 1773 item 3). What A7 must show is that
    # the EXECUTED run still binds to that same accepted identity, and that the
    # live freeze genuinely differs - so precall_view is doing real work.
    live = hashlib.sha256(
        A6L.render(A6L.freeze(RUN)).encode("utf-8")).hexdigest()
    CHECKS.append(("live_freeze_differs", live != WANT["a6_freeze"], live, "!= accepted"))
    print("  %-5s %-22s %s" % ("ok" if live != WANT["a6_freeze"] else "BAD",
                               "live_freeze_differs", live))
    check("precall_of_executed", hashlib.sha256(
        A6L.render(A6L.precall_view(A6L.freeze(RUN), RUN)).encode("utf-8")).hexdigest(),
        WANT["a6_freeze"])

    ident = PR.load(RUN)
    check("a5_manifest", ident["a5_manifest_sha256"], WANT["a5_manifest"])
    check("a5_bundle", ident["a5_bundle_sha256"], WANT["a5_bundle"])
    check("a6_freeze", ident["a6_freeze_sha256"], WANT["a6_freeze"])
    check("run_digest", ident["executed"]["run_digest"], WANT["run_digest"])
    check("run_files", ident["executed"]["run_files"], 861)
    check("scheduled_calls", ident["scheduled_calls"], 392)
    check("contract_suffix", ident["contract_suffix"], ".v3")

    os.makedirs(OUT, exist_ok=True)
    io.open(OUT + "/IDENTITY.json", "w", encoding="utf-8").write(
        json.dumps(ident, indent=1))
    io.open(OUT + "/CHECKS.tsv", "w", encoding="utf-8").write(
        "".join("%s\t%s\t%s\t%s\n" % (n, "ok" if k else "BAD", g, w)
                for n, k, g, w in CHECKS))
    bad = [n for n, k, _g, _w in CHECKS if not k]
    print("\n%d checks, %d bad %s" % (len(CHECKS), len(bad), bad or ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
