# -*- coding: utf-8 -*-
"""Gap 2: the ACTUAL model-facing cards, old and new, via the existing owners.

The card is a7_g23_build.reference_card output - quote, reference_name, values -
serialized by G._pretty. The old cards are served from the FROZEN inventory; the
new ones from a candidate inventory derived in this unit's own output space
through the existing validation owner. The frozen document is never overwritten.
"""
import collections, hashlib, io, json, os, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U = A + "/unit_1821"
CAND, RUN, OUT = (S + "/g1_precall_cand_1525", S + "/g1_precall_run_1525",
                  "/tmp/a7_logs_1781")
FROZEN = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/"
          "targeted_1589/post_1500_exact_1626/budget_inputs_1720/out_g23/"
          "tmp__a7_reference_inventory.json")
PIN = {"root": "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0",
       "run_digest": "ec50dc6e9af2e6efc5dd5e4114c0d6dc0f09b77070a9760aece3839f3bffab71",
       "run_files": 471}
#: the reviewer's independently executed values for one row
CODEX = {"old_sha": "a3afa11c35e1022dff6ea3ff70de2d4397266c4fbe75fda9623560cac2e00572",
         "new_sha": "611690a4b5bf1dc28018f44aed901ce9c11e7d1e3193a670e1fad9aab68d66c3",
         "old_bytes": 216, "new_bytes": 213,
         "row": ("0000027904-26-000022", 2)}
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
sys.path.insert(0, A + "/unit_1820/candidate")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_reference_inventory as REF                             # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_g1_complete_v2 as C                                    # noqa: E402
import a7_g23_build as B                                         # noqa: E402
usha = lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()


def cards_from(path, run, key, wanted):
    """The real model cards, served from ONE inventory document."""
    REF.INVENTORY_PATH = path
    B._INVENTORY.clear()
    out = {}
    for sid, gi in wanted:
        card = B.reference_card(key[sid][gi], sid, gi, run)
        text = G._pretty(card)
        out[(sid, gi)] = (card, text)
    return out


def main():
    exp = json.load(io.open(A + "/unit_1820/candidate/EXPECTED_CARDS_14.json",
                            encoding="utf-8"))
    wanted = [(r["source_id"], r["gold_idx"]) for r in exp["rows"]]
    _r, doc, _l, _p = C.evidence(CAND, RUN, PIN["root"], PIN["run_digest"],
                                 PIN["run_files"])
    run, (key, _i) = doc["producer_identity"], G.live_key()

    # the candidate inventory, in THIS unit's output space, proved by the owner
    cand_path = OUT + "/candidate_reference_inventory.json"
    if os.path.exists(cand_path):
        os.remove(cand_path)
    REF.write(REF.expected_document(run), cand_path)
    served = REF.validate(cand_path, run)          # refuses unless exact
    print("  candidate inventory written and VALIDATED by the owner: %d rows"
          % len(served))
    print("  frozen document untouched: %s"
          % (hashlib.sha256(io.open(FROZEN, "rb").read()).hexdigest()
             == "ae81caf4936c43432fe27d5ac686dfa090539c615620ce029eaeb00b2f900106"))

    old = cards_from(FROZEN, run, key, wanted)
    new = cards_from(cand_path, run, key, wanted)
    rows = []
    for k in wanted:
        oc, ot = old[k]
        nc, nt = new[k]
        rows.append(collections.OrderedDict([
            ("source_id", k[0]), ("gold_idx", k[1]),
            ("old_card_text", ot), ("new_card_text", nt),
            ("old_card_bytes", len(ot.encode("utf-8"))),
            ("new_card_bytes", len(nt.encode("utf-8"))),
            ("old_card_sha256", usha(ot)), ("new_card_sha256", usha(nt)),
            ("old_reference_name", oc["reference_name"]),
            ("new_reference_name", nc["reference_name"]),
            ("quote_unchanged", oc["quote"] == nc["quote"]),
            ("values_unchanged", oc["values"] == nc["values"])]))
    hit = next(r for r in rows if (r["source_id"], r["gold_idx"]) == CODEX["row"])
    checks = collections.OrderedDict([
        ("codex_old_sha256", hit["old_card_sha256"] == CODEX["old_sha"]),
        ("codex_new_sha256", hit["new_card_sha256"] == CODEX["new_sha"]),
        ("codex_old_bytes", hit["old_card_bytes"] == CODEX["old_bytes"]),
        ("codex_new_bytes", hit["new_card_bytes"] == CODEX["new_bytes"]),
        ("only_the_name_moved",
         all(r["quote_unchanged"] and r["values_unchanged"] for r in rows))])
    io.open(OUT + "/MODEL_CARDS_1821.json", "w", encoding="utf-8").write(
        json.dumps(collections.OrderedDict([
            ("serializer", "a7_g23_build.reference_card then a7_g1_build._pretty"),
            ("candidate_inventory", cand_path),
            ("candidate_inventory_sha256",
             hashlib.sha256(io.open(cand_path, "rb").read()).hexdigest()),
            ("rows", rows), ("reviewer_cross_check", checks)]), indent=1) + "\n")
    for k, v in checks.items():
        print("  %-24s %s" % (k, v))
    print("  one row, verbatim: %s g%s" % CODEX["row"])
    print("    old (%d B, %s): %s" % (hit["old_card_bytes"],
                                      hit["old_card_sha256"][:16],
                                      hit["old_reference_name"]))
    print("    new (%d B, %s): %s" % (hit["new_card_bytes"],
                                      hit["new_card_sha256"][:16],
                                      hit["new_reference_name"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
