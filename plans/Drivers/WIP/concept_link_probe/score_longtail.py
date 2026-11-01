#!/usr/bin/env python3
"""Score long-tail self-labeled recall. Truth = each concept's own qname.
correct = pick==truth ; abstained = pick null ; wrong = picked a different concept."""
import json, pathlib, collections

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")

def main():
    correct = abstained = wrong = 0
    wrongs = []
    done = 0
    for f in sorted((CLP / "longtail").glob("*.json")):
        t = f.stem
        pf = CLP / "longtail_picks" / f"{t}.json"
        if not pf.exists():
            continue
        done += 1
        truth = {q["slug"]: q["truth_qname"] for q in json.loads(f.read_text())["queries"]}
        picks = {r["slug"]: r.get("qname") for r in json.loads(pf.read_text()) if r.get("slug")}
        for slug, tq in truth.items():
            p = picks.get(slug, None)
            if p == tq:
                correct += 1
            elif p is None:
                abstained += 1
            else:
                wrong += 1
                wrongs.append((t, slug, p, tq))
    n = correct + abstained + wrong
    print(f"=== long-tail self-labeled recall (companies scored: {done}/31) ===")
    print(f"  queries: {n}")
    print(f"  correct (pick==truth): {correct} = {correct/max(n,1):.1%}")
    print(f"  abstained (null):      {abstained} = {abstained/max(n,1):.1%}")
    print(f"  WRONG (diff concept):  {wrong} = {wrong/max(n,1):.1%}")
    print(f"  recall among non-abstained: {correct/max(correct+wrong,1):.1%}")
    print("--- sample WRONG (long-tail precision risks; many are near-duplicate concepts) ---")
    for t, s, p, tq in wrongs[:30]:
        print(f"  {t}|{s}: pick={p.split(':')[-1][:30]}  truth={tq.split(':')[-1][:30]}")
    (CLP / "longtail_score.json").write_text(json.dumps(
        {"correct": correct, "abstained": abstained, "wrong": wrong, "wrongs": wrongs}))

if __name__ == "__main__":
    main()
