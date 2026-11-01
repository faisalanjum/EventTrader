#!/usr/bin/env python3
"""Long-tail self-labeled breadth test.

The guidance positive set covers ~30 common metrics. To prove the matcher generalizes
to the LONG TAIL of metrics a DriverUpdate could name, we self-label from the XBRL Facts:
each reported Concept IS its own answer. We query the matcher with a humanized SHORT form
of the concept's standard label and check it recovers that exact qname (or abstains when the
short form is genuinely ambiguous among near-duplicate concepts).

Stress comes from near-duplicates in the SAME menu (InterestExpense vs InterestExpenseNonoperating
vs InterestIncomeExpenseNet; the dozens of ShareBasedCompensation* variants).

Picks the most driver-relevant concepts: us-gaap, monetary/per-share/shares/pure, by usage.
"""
import json, re, pathlib, collections

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")
SAMPLE_PER_CO = 45

DROP_TAIL = re.compile(r",?\s*(net|total|continuing operations|excluding assessed tax|"
                       r"including assessed tax|before income taxes.*|at carrying value|"
                       r"period increase decrease.*)\s*$", re.I)

def humanize(label):
    s = label or ""
    prev = None
    while prev != s:
        prev = s
        s = DROP_TAIL.sub("", s).strip().strip(",")
    return s or label

def main():
    facts = json.loads((CLP / "facts.json").read_text())
    bundles_per = CLP / "longtail"
    bundles_per.mkdir(exist_ok=True)
    n_q = 0
    for t, rows in facts.items():
        agg = collections.defaultdict(lambda: {"usage": 0, "label": None})
        for f in rows:
            q = f["qname"]
            agg[q]["usage"] += 1
            agg[q]["label"] = f.get("label")
        menu = [{"qname": q, "label": v["label"], "usage": v["usage"]} for q, v in agg.items()]
        # candidate concepts to query: us-gaap, with a usable label, sorted by usage
        cand = [c for c in menu if c["qname"].startswith("us-gaap:") and c["label"]]
        cand.sort(key=lambda c: -c["usage"])
        queries = []
        seen = set()
        for c in cand[:SAMPLE_PER_CO * 2]:
            h = humanize(c["label"])
            sl = re.sub(r"[^a-z0-9]+", "_", h.lower()).strip("_")
            if not sl or sl in seen:
                continue
            seen.add(sl)
            queries.append({"slug": sl, "truth_qname": c["qname"], "label": c["label"]})
            if len(queries) >= SAMPLE_PER_CO:
                break
        n_q += len(queries)
        (bundles_per / f"{t}.json").write_text(json.dumps(
            {"ticker": t, "menu": sorted(menu, key=lambda c: -c["usage"]), "queries": queries}))
    print(f"longtail: {n_q} self-labeled breadth queries across {len(facts)} companies "
          f"→ {bundles_per} (avg {n_q/len(facts):.0f}/co)")

if __name__ == "__main__":
    main()
