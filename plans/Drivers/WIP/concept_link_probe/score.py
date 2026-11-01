#!/usr/bin/env python3
"""Score LLM-pick matcher vs the value-anchor oracle + curated baseline.

Buckets (positive set):
  CONFIRMED   LLM linked, VA(strong) agrees                 → high-confidence correct
  CONFLICT    LLM linked, VA(strong) disagrees              → audit (VA may be coincidence)
  LLM_ONLY    LLM linked, VA absent/weak                    → adversarial verify
  RECALL_MISS LLM abstained, VA(strong) found a concept     → missed recall
  BOTH_SILENT LLM abstained, VA absent                      → fine
Negative set: any LLM link = LEAK (precision failure). Target 0.

Reads picks/{ticker}.json = [{slug,qname,confidence,reason}].
"""
import json, pathlib, collections

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")
PICKS = CLP / "picks"

def va_oracle():
    pi = json.loads((CLP / "per_instance.json").read_text())
    by = collections.defaultdict(list)
    for r in pi:
        by[(r["ticker"], r["slug"])].append(r["qname"])
    out = {}
    for k, qs in by.items():
        c = collections.Counter(qs)
        q, n = c.most_common(1)[0]
        share = n / len(qs)
        tier = "strong" if (len(qs) >= 2 and share >= 0.8) else "weak"
        out[k] = {"qname": q, "n": len(qs), "share": round(share, 2), "tier": tier}
    return out

def load_picks():
    picks = {}
    for f in sorted(PICKS.glob("*.json")):
        try:
            arr = json.loads(f.read_text())
        except Exception:
            continue
        d = {}
        for r in arr:
            if isinstance(r, dict) and r.get("slug"):
                d[r["slug"]] = r
        picks[f.stem] = d
    return picks

def main():
    bundles = json.loads((CLP / "bundles.json").read_text())
    va = va_oracle()
    picks = load_picks()
    pos_b = collections.Counter()
    conflicts, llm_only, recall_miss = [], [], []
    neg_leaks = []
    pos_links = neg_links = 0
    pos_total = neg_total = 0
    for t, b in bundles.items():
        p = picks.get(t, {})
        for slug in b["pos_slugs"]:
            pos_total += 1
            rec = p.get(slug) or {}
            q = rec.get("qname")
            o = va.get((t, slug))
            if q: pos_links += 1
            if q and o and o["tier"] == "strong":
                if q == o["qname"]:
                    pos_b["CONFIRMED"] += 1
                else:
                    pos_b["CONFLICT"] += 1
                    conflicts.append((t, slug, q, o["qname"], rec.get("confidence")))
            elif q:
                pos_b["LLM_ONLY"] += 1
                llm_only.append((t, slug, q, rec.get("confidence")))
            elif o and o["tier"] == "strong":
                pos_b["RECALL_MISS"] += 1
                recall_miss.append((t, slug, o["qname"], o["n"]))
            else:
                pos_b["BOTH_SILENT"] += 1
        for slug in b["neg_slugs"]:
            neg_total += 1
            q = (p.get(slug) or {}).get("qname")
            if q:
                neg_links += 1
                neg_leaks.append((t, slug, q, (p.get(slug) or {}).get("confidence")))
    print(f"=== POSITIVE set ({pos_total} pairs) ===")
    print(f"  LLM linked: {pos_links} ({pos_links/pos_total:.1%})  vs curated baseline 195 (24.1%)")
    for k in ["CONFIRMED", "CONFLICT", "LLM_ONLY", "RECALL_MISS", "BOTH_SILENT"]:
        print(f"  {k}: {pos_b[k]}")
    denom = pos_b["CONFIRMED"] + pos_b["CONFLICT"]
    if denom:
        print(f"  precision proxy (CONFIRMED / VA-strong-overlap) = {pos_b['CONFIRMED']/denom:.1%}")
    print(f"=== NEGATIVE set ({neg_total} abstention tests) ===")
    print(f"  LEAKS (LLM linked a conceptless driver): {neg_links}  vs curated baseline 21")
    print(f"  abstention rate: {(neg_total-neg_links)/neg_total:.2%}")
    out = {"pos_buckets": dict(pos_b), "conflicts": conflicts, "llm_only": llm_only,
           "recall_miss": recall_miss, "neg_leaks": neg_leaks}
    (CLP / "score.json").write_text(json.dumps(out, indent=0))
    print(f"\nconflicts: {len(conflicts)}  llm_only: {len(llm_only)}  recall_miss: {len(recall_miss)}  neg_leaks: {len(neg_leaks)}")
    print("--- sample CONFLICTs (LLM vs VA-strong) ---")
    for t, s, q, oq, c in conflicts[:15]:
        print(f"  {t}|{s}: LLM={q.split(':')[-1][:30]} ({c})  VA={oq.split(':')[-1][:30]}")
    print("--- sample NEG LEAKS ---")
    for t, s, q, c in neg_leaks[:15]:
        print(f"  {t}|{s} -> {q.split(':')[-1]} ({c})")

if __name__ == "__main__":
    main()
