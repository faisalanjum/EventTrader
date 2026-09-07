# -*- coding: utf-8 -*-
"""Corrected 206-row disposition with exact old/new card bytes, plus the one
affected existing test. Serialization is the harness's OWN canonical pair
(G._pretty / G._sha); this file introduces no serializer of its own.
"""
import collections, io, json, os, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U = A + "/unit_1820"
CAND, RUN, OUT = (S + "/g1_precall_cand_1525", S + "/g1_precall_run_1525",
                  "/tmp/a7_logs_1781")
FROZEN = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/"
          "targeted_1589/post_1500_exact_1626/budget_inputs_1720/out_g23/"
          "tmp__a7_reference_inventory.json")
PIN = {"root": "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0",
       "run_digest": "ec50dc6e9af2e6efc5dd5e4114c0d6dc0f09b77070a9760aece3839f3bffab71",
       "run_files": 471}
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
sys.path.insert(0, U + "/candidate")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_reference_inventory as REF                             # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_g1_complete_v2 as C                                    # noqa: E402


def main():
    exp = json.load(io.open(U + "/candidate/EXPECTED_CARDS_14.json",
                            encoding="utf-8"))
    judged = {(r["source_id"], r["gold_idx"]): r for r in exp["rows"]}
    _root, doc, _l, _p = C.evidence(CAND, RUN, PIN["root"], PIN["run_digest"],
                                    PIN["run_files"])
    run, (key, _i) = doc["producer_identity"], G.live_key()
    rows, problems = REF.build(key, run)
    new = {(r["source_id"], r["gold_idx"]): r for r in rows}
    old = {(r["source_id"], r["gold_idx"]): r
           for r in json.load(io.open(FROZEN, encoding="utf-8"))["rows"]}

    changed, unchanged_exact = [], 0
    for k in sorted(old):
        ob, nb = G._pretty(old[k]), G._pretty(new[k])
        if k in judged:
            changed.append(collections.OrderedDict([
                ("source_id", k[0]), ("gold_idx", k[1]),
                ("packet_id", new[k]["packet_id"]),
                ("fact_index", new[k]["fact_index"]),
                ("fact_sha256", new[k]["fact_sha256"]),
                ("quote_sha256", new[k]["quote_sha256"]),
                ("old_reference_name", old[k]["reference_name"]),
                ("new_reference_name", new[k]["reference_name"]),
                ("old_card_bytes", len(ob.encode("utf-8"))),
                ("new_card_bytes", len(nb.encode("utf-8"))),
                ("old_card_sha256", G._sha(ob)), ("new_card_sha256", G._sha(nb)),
                ("reason", judged[k]["reason"])]))
        elif ob == nb:
            unchanged_exact += 1

    disp = [collections.OrderedDict([
        ("source_id", k[0]), ("gold_idx", k[1]),
        ("fact_sha256", new[k]["fact_sha256"]),
        ("quote_sha256", new[k]["quote_sha256"]),
        ("reference_name", new[k]["reference_name"]),
        ("disposition", "CHANGE" if k in judged else "KEEP")])
        for k in sorted(new)]
    counts = collections.Counter(r["disposition"] for r in disp)

    # the one existing test that consumes this owner
    t = "test_a7_runstates_1470.py"
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", H + "/" + t],
                       capture_output=True, text=True, cwd=H,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                                PYTHONPATH=U + "/candidate:" + H))
    tail = (r.stdout or "")[-400:] + (r.stderr or "")[-200:]

    doc_out = collections.OrderedDict([
        ("rows_total", len(disp)), ("counts", dict(counts)),
        ("build_problems", problems),
        ("untouched_rows_byte_exact", unchanged_exact),
        ("changed_rows", changed),
        ("affected_existing_test", collections.OrderedDict([
            ("test", t), ("exit", r.returncode), ("tail", tail.strip()[-380:])])),
        ("disposition", disp)])
    io.open(OUT + "/DISPOSITION_1820.json", "w", encoding="utf-8").write(
        json.dumps(doc_out, indent=1) + "\n")
    print("  disposition: %s total %d" % (dict(counts), len(disp)))
    print("  build problems: %s" % (problems or "none"))
    print("  untouched rows byte-exact: %d of 192" % unchanged_exact)
    print("  changed rows recorded with old/new card bytes: %d" % len(changed))
    print("  %s -> exit %d" % (t, r.returncode))
    print("     %s" % tail.strip().splitlines()[-1] if tail.strip() else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
