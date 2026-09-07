# -*- coding: utf-8 -*-
"""Drive the REAL a7_reference_inventory.build() against judged expectations.

The candidate copy of the owner is put FIRST on the path, so this executes the
owner itself - its name selection, card construction and validation - not a
re-implementation. The expectations are independently judged DATA; this file
decides no meaning.
"""
import collections, io, json, os, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U = A + "/unit_1820"
CAND, RUN, OUT = (S + "/g1_precall_cand_1525", S + "/g1_precall_run_1525",
                  "/tmp/a7_logs_1781")
PIN = {"root": "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0",
       "run_digest": "ec50dc6e9af2e6efc5dd5e4114c0d6dc0f09b77070a9760aece3839f3bffab71",
       "run_files": 471}
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
sys.path.insert(0, U + "/candidate")          # the CANDIDATE owner wins
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
# the candidate owner FIRST: a7_g1_build imports this module, so importing it
# afterwards would leave the harness copy cached in sys.modules and the test
# would silently exercise the wrong file.
import a7_reference_inventory as REF                             # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_g1_complete_v2 as C                                    # noqa: E402
assert os.path.dirname(os.path.abspath(REF.__file__)) == U + "/candidate", REF.__file__


def main():
    exp = json.load(io.open(U + "/candidate/EXPECTED_CARDS_14.json",
                            encoding="utf-8"))
    judged = {(r["source_id"], r["gold_idx"]): r for r in exp["rows"]}
    ctrl = exp["positive_control"]
    _root, doc, _lanes, _p = C.evidence(CAND, RUN, PIN["root"],
                                        PIN["run_digest"], PIN["run_files"])
    run = doc["producer_identity"]
    key, _ident = G.live_key()                 # the executable loader, not the display
    rows, problems = REF.build(key, run)
    got = {(r["source_id"], r["gold_idx"]): r["reference_name"] for r in rows}
    print("  owner: %s" % REF.__file__)
    print("  overrides in this candidate: %d" % len(REF.SPAN_OVERRIDES))
    print("  build() rows %d, problems %s" % (len(rows), problems or "none"))

    results = []
    for k in sorted(judged):
        want = judged[k]["expected_reference_name"]
        results.append(collections.OrderedDict([
            ("check", "%s g%s" % k), ("expected", want), ("observed", got.get(k)),
            ("status", "GREEN" if got.get(k) == want else "RED")]))
    ck = (ctrl["source_id"], ctrl["gold_idx"])
    results.append(collections.OrderedDict([
        ("check", "POSITIVE CONTROL %s g%s" % ck),
        ("expected", ctrl["expected_reference_name"]), ("observed", got.get(ck)),
        ("status", "GREEN" if got.get(ck) == ctrl["expected_reference_name"] else "RED")]))
    # every row this correction does NOT touch must stay byte-exact
    frozen = json.load(io.open(
        "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/"
        "targeted_1589/post_1500_exact_1626/budget_inputs_1720/out_g23/"
        "tmp__a7_reference_inventory.json", encoding="utf-8"))
    base = {(r["source_id"], r["gold_idx"]): r["reference_name"]
            for r in frozen["rows"]}
    drifted = sorted(k for k in base
                     if k not in judged and base[k] != got.get(k))
    results.append(collections.OrderedDict([
        ("check", "the %d untouched rows stay byte-exact" % (len(base) - len(judged))),
        ("expected", 0), ("observed", len(drifted)),
        ("status", "GREEN" if not drifted else "RED")]))
    red = [r for r in results if r["status"] == "RED"]
    for r in results:
        if r["status"] == "RED":
            print("    RED   %-34s expected %r, observed %r"
                  % (r["check"], r["expected"], r["observed"]))
    print("    GREEN %d, RED %d" % (len(results) - len(red), len(red)))
    if drifted:
        print("    drifted rows: %s" % drifted[:5])
    io.open(OUT + "/CARDS_TEST_%s.json" % os.environ.get("PHASE", "x"), "w",
            encoding="utf-8").write(json.dumps(collections.OrderedDict([
                ("owner", REF.__file__), ("overrides", len(REF.SPAN_OVERRIDES)),
                ("build_problems", problems), ("rows_built", len(rows)),
                ("checks", results), ("red", len(red)),
                ("green", len(results) - len(red)),
                ("untouched_drift", drifted)]), indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
