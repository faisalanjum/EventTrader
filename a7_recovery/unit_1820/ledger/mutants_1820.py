# -*- coding: utf-8 -*-
"""Meaningful mutations over the approved DATA and its real consumer.

Each mutant restores one old wrong label, or swaps in a sibling's span that is
STILL a verbatim substring of the same quote. Both must fail the independently
judged expectation - the second shows that being a real source substring is not
enough to be the right one. The overrides are mutated in memory only; the
candidate file is never written.
"""
import collections, copy, io, json, os, sys
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
sys.path.insert(0, U + "/candidate")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_reference_inventory as REF                             # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_g1_complete_v2 as C                                    # noqa: E402

#: a sibling's own span, verbatim in the SAME quote, for the swap mutant
SIBLING_SWAP = (("0001104659-26-027061", 1), "1.6% increase in transactions")


def main():
    exp = json.load(io.open(U + "/candidate/EXPECTED_CARDS_14.json",
                            encoding="utf-8"))
    judged = {(r["source_id"], r["gold_idx"]): r for r in exp["rows"]}
    _root, doc, _l, _p = C.evidence(CAND, RUN, PIN["root"], PIN["run_digest"],
                                    PIN["run_files"])
    run, (key, _i) = doc["producer_identity"], G.live_key()
    base = copy.deepcopy(REF.SPAN_OVERRIDES)

    def names():
        rows, problems = REF.build(key, run)
        return ({(r["source_id"], r["gold_idx"]): r["reference_name"]
                 for r in rows}, problems)

    def holds():
        got, problems = names()
        return all(got.get(k) == v["expected_reference_name"]
                   for k, v in judged.items()), problems

    out = []
    ok, problems = holds()
    out.append(collections.OrderedDict([
        ("mutant", "none (ordinary positive run)"), ("expectation_holds", ok),
        ("build_problems", problems), ("verdict", "GREEN" if ok else "RED")]))

    for k, v in sorted(judged.items()):
        REF.SPAN_OVERRIDES = copy.deepcopy(base)
        REF.SPAN_OVERRIDES[k] = v["current_reference_name"]   # the OLD wrong label
        ok, problems = holds()
        out.append(collections.OrderedDict([
            ("mutant", "restore old label at %s g%s" % k),
            ("label", v["current_reference_name"]),
            ("expectation_holds", ok), ("build_problems", problems),
            ("verdict", "CAUGHT" if not ok else "ESCAPED")]))

    k, span = SIBLING_SWAP
    REF.SPAN_OVERRIDES = copy.deepcopy(base)
    REF.SPAN_OVERRIDES[k] = span
    ok, problems = holds()
    got, _pr = names()
    out.append(collections.OrderedDict([
        ("mutant", "sibling span swap at %s g%s" % k), ("label", span),
        ("is_verbatim_substring_of_the_same_quote", True),
        ("owner_accepted_it_as_a_span", not problems),
        ("expectation_holds", ok),
        ("verdict", "CAUGHT" if not ok else "ESCAPED")]))
    REF.SPAN_OVERRIDES = base

    caught = sum(1 for r in out if r["verdict"] == "CAUGHT")
    escaped = [r for r in out if r["verdict"] == "ESCAPED"]
    io.open(OUT + "/MUTANTS_1820.json", "w", encoding="utf-8").write(
        json.dumps(collections.OrderedDict([
            ("mutants", out), ("caught", caught), ("escaped", len(escaped)),
            ("positive_run", out[0]["verdict"])]), indent=1) + "\n")
    print("  ordinary positive run : %s" % out[0]["verdict"])
    print("  mutants caught        : %d of %d" % (caught, len(out) - 1))
    print("  escaped               : %d" % len(escaped))
    sw = out[-1]
    print("  sibling-span swap     : %s (the owner ACCEPTED it as a valid span: %s)"
          % (sw["verdict"], sw["owner_accepted_it_as_a_span"]))
    for r in escaped:
        print("    ESCAPED: %s" % r["mutant"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
