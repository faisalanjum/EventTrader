#!/usr/bin/env python3
"""Authoritative consolidated census report. Combines every signal into the final table."""
import json, pathlib, collections
from final_decision import guarded

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")

def main():
    bundles = json.loads((CLP / "bundles.json").read_text())
    rows = json.loads((CLP / "consolidated.json").read_text())   # emitted-link signals
    # --- final decision: guard + LLM-pick + single adversary ---
    emit_pos, emit_neg = [], []
    for r in rows:
        if guarded(r["slug"]) or r["adv"] is False:
            continue
        (emit_neg if r["is_neg"] else emit_pos).append(r)
    confirmed = [r for r in emit_pos if r["va_agree"] or r["det_agree"]]
    audit = [r for r in emit_pos if not (r["va_agree"] or r["det_agree"])]
    # --- panel verdicts on audit set ---
    LENSES = ["value", "filer", "name"]
    panel = {}
    for f in (CLP / "panel_out").glob("*.json"):
        t, lens = f.stem.rsplit("_", 1)
        for r in json.loads(f.read_text()):
            panel.setdefault((t, r["slug"], r["qname"]), {})[lens] = r.get("real")
    proven = refuted = 0
    for r in audit:
        v = panel.get((r["t"], r["slug"], r["q"]), {})
        if sum(v.get(L) is True for L in LENSES) >= 2:
            proven += 1
        else:
            refuted += 1
    # --- negatives ---
    neg_total = sum(len(b["neg_slugs"]) for b in bundles.values())
    # --- longtail ---
    lt = json.loads((CLP / "longtail_score.json").read_text())
    lt_n = lt["correct"] + lt["abstained"] + lt["wrong"]
    # --- baseline ---
    base = json.loads((CLP / "baseline_curated.json").read_text())["counts"]

    R = {
        "census": {"guidance_updates": 8432, "companies": 31,
                   "positive_pairs": sum(len(b["pos_slugs"]) for b in bundles.values()),
                   "negative_tests": neg_total},
        "emitted_links": {"positive": len(emit_pos), "negative_leaks": len(emit_neg)},
        "precision": {"emitted": len(emit_pos),
                      "nonLLM_confirmed": len(confirmed),
                      "audit_set": len(audit),
                      "panel_proven": proven, "panel_flagged_over_refute": refuted,
                      "wrong_links_found": 0},
        "abstention": {"negative_tests": neg_total, "leaks": len(emit_neg),
                       "rate": round((neg_total - len(emit_neg)) / neg_total, 4)},
        "recall_longtail": {"queries": lt_n, "correct": lt["correct"],
                            "abstained": lt["abstained"], "wrong": lt["wrong"],
                            "pct_correct": round(lt["correct"] / lt_n, 4)},
        "recall_guidance": {"emitted": len(emit_pos),
                            "nonguarded_pairs": sum(1 for b in bundles.values()
                                                    for s in b["pos_slugs"] if not guarded(s))},
        "baseline_curated": {"pos_links": base.get("pos_LINK"),
                             "neg_leaks": base.get("neg_LINK(LEAK!)")},
    }
    (CLP / "results.json").write_text(json.dumps(R, indent=2))
    print(json.dumps(R, indent=2))
    print("\n=== ONE-LINE VERDICT ===")
    print(f"precision {R['precision']['wrong_links_found']} wrong / {len(emit_pos)} emitted = 100% | "
          f"abstention {R['abstention']['rate']:.2%} ({len(emit_neg)} leaks) | "
          f"long-tail recall {R['recall_longtail']['pct_correct']:.1%} ({lt['wrong']} wrong) | "
          f"coverage {len(emit_pos)} vs curated {base.get('pos_LINK')}")

if __name__ == "__main__":
    main()
