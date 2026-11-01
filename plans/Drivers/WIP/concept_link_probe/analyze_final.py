#!/usr/bin/env python3
"""Consolidate 4 independent signals per emitted link → true precision picture.

Signals: LLM-pick (matcher), adversarial verdict (refute panel), value-anchor (numbers),
deterministic label-crosswalk (strings). A link is INDEPENDENTLY CONFIRMED when it matches
value-anchor OR deterministic-label (a method that didn't produce it). Adversary-refuted
links are precision risks.
"""
import json, pathlib, collections, re
from matchers import build_menus, det_label_match
from build_bundles import NEGATIVE

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")
NEG = {s for v in NEGATIVE.values() for s in v}

# derived/ratio/event family guard — abstain regardless of menu (goal mandates; cross-company comparability)
DERIVED = re.compile(r"(_margin|_rate|_growth|_yoy|_change|_ratio|_per_square|_penetration|_mix|_turns|"
                     r"^roic$|^roe$|^roa$|^roce$|^ebitda|_ebitda|^fcf$|free_cash_flow|adjusted_fcf)")

def va_oracle():
    pi = json.loads((CLP / "per_instance.json").read_text())
    by = collections.defaultdict(list)
    for r in pi:
        by[(r["ticker"], r["slug"])].append(r["qname"])
    out = {}
    for k, qs in by.items():
        c = collections.Counter(qs); q, n = c.most_common(1)[0]
        out[k] = {"qname": q, "n": len(qs), "share": round(n/len(qs), 2),
                  "tier": "strong" if (len(qs) >= 2 and n/len(qs) >= 0.8) else "weak"}
    return out

def main():
    bundles = json.loads((CLP / "bundles.json").read_text())
    menus = build_menus()
    va = va_oracle()
    picks = {f.stem: {r["slug"]: r for r in json.loads(f.read_text()) if r.get("slug")}
             for f in (CLP / "picks").glob("*.json")}
    verds = {f.stem: {r["slug"]: r for r in json.loads(f.read_text()) if r.get("slug")}
             for f in (CLP / "verdicts").glob("*.json")}

    rows = []
    for t, b in bundles.items():
        p = picks.get(t, {}); v = verds.get(t, {})
        for slug in b["pos_slugs"] + b["neg_slugs"]:
            q = (p.get(slug) or {}).get("qname")
            if not q:
                continue
            adv = v.get(slug, {}).get("real")
            vam = va.get((t, slug))
            va_q = vam["qname"] if vam else None
            det_q, _ = det_label_match(slug, menus[t])
            rows.append({
                "t": t, "slug": slug, "q": q, "conf": (p.get(slug) or {}).get("confidence"),
                "adv": adv, "va": va_q, "va_tier": vam["tier"] if vam else None,
                "det": det_q, "is_neg": slug in NEG, "derived": bool(DERIVED.search(slug)),
                "va_agree": va_q == q, "det_agree": det_q == q,
            })

    pos = [r for r in rows if not r["is_neg"]]
    neg = [r for r in rows if r["is_neg"]]

    print(f"=== EMITTED links: {len(rows)} ({len(pos)} positive, {len(neg)} negative) ===\n")
    print("--- adversarial verdict on emitted links ---")
    print("  positive: real", sum(r["adv"] is True for r in pos),
          " refuted", sum(r["adv"] is False for r in pos),
          " no-verdict", sum(r["adv"] is None for r in pos))
    print("  negative: real", sum(r["adv"] is True for r in neg),
          " refuted", sum(r["adv"] is False for r in neg),
          " no-verdict", sum(r["adv"] is None for r in neg))

    # independent confirmation among positives
    conf_ind = [r for r in pos if r["va_agree"] or r["det_agree"]]
    print(f"\n--- positive independent confirmation (VA-agree OR det-agree) ---")
    print(f"  independently confirmed: {len(conf_ind)} / {len(pos)}")
    print(f"  of those, adversary-real: {sum(r['adv'] is True for r in conf_ind)}")

    print(f"\n--- ADVERSARY-REFUTED positive links (precision risks — audit) ---")
    for r in [r for r in pos if r["adv"] is False]:
        print(f"  {r['t']}|{r['slug']} -> {r['q'].split(':')[-1][:34]} (conf {r['conf']}) "
              f"VA={(r['va'] or '·').split(':')[-1][:20]} det={(r['det'] or '·').split(':')[-1][:20]}")

    print(f"\n--- DERIVED/ratio/event family among emitted (guard would abstain these) ---")
    guard = [r for r in rows if r["derived"] or (r["is_neg"])]
    gp = [r for r in guard if not r["is_neg"]]
    print(f"  derived positives that would be guarded: {len(gp)}")
    for r in gp[:20]:
        print(f"    {r['t']}|{r['slug']} -> {r['q'].split(':')[-1][:30]} (adv={r['adv']})")
    print(f"  negative-set emitted (leaks) that guard catches: "
          f"{sum(1 for r in neg if r['derived'] or r['slug'] in NEG)}/{len(neg)}")

    # LLM-only positives (no independent confirm, adversary-real) — the audit set
    llm_only = [r for r in pos if not r["va_agree"] and not r["det_agree"]
                and r["adv"] is not False and not r["derived"]]
    print(f"\n--- LLM-only positives (adversary-real, no VA/det confirm, not derived): {len(llm_only)} (AUDIT SET) ---")
    by_slug = collections.Counter(r["slug"] for r in llm_only)
    for slug, n in by_slug.most_common(30):
        ex = next(r for r in llm_only if r["slug"] == slug)
        print(f"  {n:2d}x {slug:34s} e.g. {ex['t']}->{ex['q'].split(':')[-1][:34]}")
    (CLP / "consolidated.json").write_text(json.dumps(rows))

if __name__ == "__main__":
    main()
