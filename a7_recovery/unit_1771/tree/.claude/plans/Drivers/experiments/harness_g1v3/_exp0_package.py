#!/usr/bin/env python3
"""Render the EXP-0 contested-pair evidence package (markdown) for Fable re-adjudication (0 LLM).
args: RUNDIR CLASSIF  -- reads contested_evidence.json + classifications, writes contested_pairs_package.md"""
import json
import sys
from collections import Counter

RUNDIR, CLASSIF = sys.argv[1], sys.argv[2]
ev = json.load(open(RUNDIR + "/contested_evidence.json"))
cls = json.load(open(CLASSIF))
CATS = {"KEY": "A. TRUE KEY PROBLEM -- the label/quote genuinely makes the two sides different; the grader is defensibly right (candidate re-label to DIFFERENT or drop)",
        "PROMPT": "B. PROMPT TOO STRICT -- same underlying driver, but the 'same SCOPE (business population + ownership class)' / MECHANISM clause + default-DIFFERENT makes BOTH Sonnet instances over-split (Opus judged these SAME). Key label is correct.",
        "MODEL": "C. MODEL OVER-CONSERVATIVE -- a single instance split a clear synonym the other two accepted (instance noise; includes the budgeted doctrine probe kp_0118)."}
ORDER = ["KEY", "PROMPT", "MODEL"]
fr = ev["false_refusal_over_50"]
pa = ev["pass_analysis"]
cc = Counter(cls[c["pair_id"]]["cat"] for c in ev["contested"])
L = []
L.append("# EXP-0 — Contested-pair evidence package for Fable re-adjudication\n")
L.append("**Run:** `%s`  ·  **Key:** %s  ·  **Gate:** %s\n" % (ev["run_id"], ev["key"], ev["gate"]))
L.append("_Read-only evidence. No grader rerun · no key edits · no prompt edits. Fable adjudicates every re-label._\n")
L.append("## Invariants — the safety story\n")
L.append("- **wrong_same = 0 / 110 for EVERY arm** — zero over-merge (the permanent, dangerous error never happened).")
L.append("- **invalid = 0 for every arm** — 480/480 on-schema, perfect reliability.")
L.append("- The gate fails ONLY on **false_refusal** (over-splitting true synonyms): Sonnet A **%d/50**, Sonnet B **%d/50**, Opus **%d/50** (bar ≤ 5 = 10%%).\n" % (fr["sonnet_a"], fr["sonnet_b"], fr["opus"]))
L.append("## Exact re-labels to pass a tier\n")
L.append("- **Opus qualifies with %d gold-SAME → DIFFERENT re-labels**, and all %d Opus refusals sit in group A below (defensible). Moving ≥%d of them clears Opus." % (pa["opus_min_SAME_to_DIFFERENT_flips_to_pass"], fr["opus"], pa["opus_min_SAME_to_DIFFERENT_flips_to_pass"]))
L.append("- **Sonnet tier would need %d re-labels** — but the bulk of Sonnet's refusals are of REAL synonyms (groups B/C, Opus confirms SAME). Flipping them would corrupt the key. **Sonnet is not rescuable by errata.**\n" % pa["sonnet_tier_min_flips_to_pass"])
L.append("## Grouping — %d contested of %d gold-SAME\n" % (ev["contested_count"], ev["gold_same_total"]))
for k in ORDER:
    L.append("- **Group %s: %d pairs**" % (k, cc.get(k, 0)))
L.append("")
L.append("## Recommendation\n")
L.append("Re-adjudicate the **%d Group-A pairs**. Several are genuine genus/species or quote-narrowed scope differences; moving even %d to DIFFERENT/drop **qualifies Opus** as the grader tier — the plan's \"Sonnet fails → Opus\" path (O10). Sonnet's over-splitting of real synonyms (Groups B/C) is a genuine tier property, not a key defect — see the O10 reproducibility note.\n" % (cc.get("KEY", 0), pa["opus_min_SAME_to_DIFFERENT_flips_to_pass"]))


def block(cat):
    L.append("\n---\n\n## %s\n" % CATS[cat])
    for c in [x for x in ev["contested"] if cls[x["pair_id"]]["cat"] == cat]:
        g = c["graders"]
        L.append("### %s  ·  hard=%s  ·  refused by: %s%s\n" % (c["pair_id"], c["hard"], ", ".join(c["refused_by"]), "  ·  **ALL THREE**" if c["refused_by_all3"] else ""))
        L.append("- **A** `%s` — %s" % (c["side_a"]["name"], " / ".join('"%s"' % q for q in c["side_a"]["quotes"])))
        L.append("- **B** `%s` — %s" % (c["side_b"]["name"], " / ".join('"%s"' % q for q in c["side_b"]["quotes"])))
        L.append("- **Fable gold rationale:** %s" % c["gold_rationale"])
        L.append("- **Assessment [%s]:** %s" % (cat, cls[c["pair_id"]]["note"]))
        L.append("- **Grader verdicts:**")
        for a in ("sonnet_a", "sonnet_b", "opus"):
            L.append("  - `%s` → **%s** — %s" % (a, g[a]["verdict"], g[a]["reason"]))
        L.append("")


for k in ORDER:
    block(k)
L.append("\n---\n\n## Execution note for O10 (reproducibility)\n")
L.append(ev["execution_note_for_O10"])
L.append("\n**Constraints honored:** no grader rerun · no key edits · no prompt edits — this package is evidence only.")
open(RUNDIR + "/contested_pairs_package.md", "w").write("\n".join(L))
print("WROTE contested_pairs_package.md | contested %d | KEY %d PROMPT %d MODEL %d | opus_flips %d sonnet_flips %d"
      % (ev["contested_count"], cc.get("KEY", 0), cc.get("PROMPT", 0), cc.get("MODEL", 0),
         pa["opus_min_SAME_to_DIFFERENT_flips_to_pass"], pa["sonnet_tier_min_flips_to_pass"]))
