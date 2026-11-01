#!/usr/bin/env python3
"""Independent matchers over a company's concept MENU. Each maps a metric name
(slug) -> a menu qname or ⊘ (abstain). Kept independent so AGREEMENT = truth.

Method here: M_label — deterministic normalized token crosswalk (STRING signal,
orthogonal to the numeric value-anchor). High precision, low recall by design:
fires only when the slug's tokens are literally present in a single menu concept's
label/local-name. NOT a curated per-metric dict — one general normalizer.

Inference is VALUE-WITHHELD: matchers see only (slug, menu), never the number.
"""
import json, re, pathlib, collections

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")

STOP = {"of", "and", "the", "to", "in", "for", "by", "a", "an", "at", "on", "with",
        "including", "excluding", "assessed", "continuing", "operations", "before"}

def _camel_tokens(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s or "")     # camelCase split
    s = re.sub(r"[^A-Za-z0-9]+", " ", s).lower()
    return [w for w in s.split() if w]

def _stem(w):
    for suf in ("ies", "es", "s"):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[:-len(suf)] + ("y" if suf == "ies" else "")
    return w

def tokset(s):
    return frozenset(_stem(w) for w in _camel_tokens(s) if w not in STOP)

def local_name(qname):
    return qname.split(":", 1)[1] if ":" in qname else qname

def build_menus():
    """menu[ticker] = [{qname,label,usage}] from the facts cache (distinct concepts)."""
    facts = json.loads((CLP / "facts.json").read_text())
    menus = {}
    for t, rows in facts.items():
        agg = collections.defaultdict(lambda: {"usage": 0, "label": None})
        for f in rows:
            q = f["qname"]
            agg[q]["usage"] += 1
            agg[q]["label"] = f.get("label")
        menus[t] = [{"qname": q, "label": v["label"], "usage": v["usage"]} for q, v in agg.items()]
    return menus

def det_label_match(slug, menu):
    """Return (qname, reason) — qname if exactly one menu concept cleanly contains the
    slug's tokens (set-equality preferred, then minimal-extra), else (None, reason)."""
    st = tokset(slug)
    if not st:
        return None, "empty_slug"
    scored = []
    for c in menu:
        ct = tokset(c["label"]) | tokset(local_name(c["qname"]))
        if st <= ct:                                   # full coverage of slug tokens
            extra = len(ct - st)
            exact = (ct == st)
            scored.append((0 if exact else 1, extra, -c["usage"], c["qname"]))
    if not scored:
        return None, "no_token_cover"
    scored.sort()
    best = scored[0]
    # ambiguous if a second candidate ties on (exact, extra) rank
    ties = [s for s in scored if s[0] == best[0] and s[1] == best[1]]
    if len(ties) > 1:
        # tie-break only if one usage clearly dominates; else abstain (precision-protective)
        ties.sort(key=lambda s: s[2])
        if ties[0][2] == ties[1][2]:
            return None, f"ambiguous_{len(ties)}"
    return best[3], "ok"

# ── quick eval: M_label vs value-anchor, and their agreement (the oracle seed) ──
if __name__ == "__main__":
    menus = build_menus()
    guidance = json.loads((CLP / "guidance.json").read_text())
    per_instance = json.loads((CLP / "per_instance.json").read_text())
    # value-anchor aggregated oracle (ticker|slug -> mode qname)
    va = collections.defaultdict(list)
    for r in per_instance:
        va[(r["ticker"], r["slug"])].append(r["qname"])
    va_mode = {k: collections.Counter(v).most_common(1)[0][0] for k, v in va.items()}

    # M_label over every (ticker, slug) that appears in guidance
    keys = sorted({(g["ticker"], g["slug"]) for g in guidance if g.get("ticker") in menus
                   and (g.get("segment") or "Total") == "Total"})
    det = {}
    det_reason = collections.Counter()
    for t, slug in keys:
        q, why = det_label_match(slug, menus[t])
        det[(t, slug)] = q
        det_reason["hit" if q else why] += 1
    print(f"=== M_label over {len(keys)} (ticker,slug) pairs ===")
    for k, n in det_reason.most_common():
        print(f"  {k}: {n}")
    n_hit = det_reason["hit"]
    print(f"  -> det hit {n_hit}/{len(keys)} = {n_hit/len(keys):.1%}")

    # agreement: where BOTH value-anchor and det fire, do they agree?
    both = [(t, s) for (t, s) in keys if (t, s) in va_mode and det.get((t, s))]
    agree = [(t, s) for (t, s) in both if va_mode[(t, s)] == det[(t, s)]]
    print(f"=== agreement (oracle seed) ===")
    print(f"  both value-anchor & det fired: {len(both)}")
    print(f"  agree: {len(agree)} = {len(agree)/max(len(both),1):.1%}")
    # the agreed set IS the high-precision answer key
    oracle = {f"{t}|{s}": va_mode[(t, s)] for (t, s) in agree}
    (CLP / "oracle_agree.json").write_text(json.dumps(oracle, indent=0))
    print(f"  -> oracle_agree.json: {len(oracle)} confirmed (ticker,slug,qname)")
    print("=== sample agreed truths ===")
    for k in list(oracle)[:20]:
        print(f"  {k} -> {oracle[k].split(':')[-1]}")
    print("=== disagreements (value-anchor vs det) — audit these ===")
    shown = 0
    for (t, s) in both:
        if va_mode[(t, s)] != det[(t, s)]:
            print(f"  {t}|{s}: VA={va_mode[(t,s)].split(':')[-1][:34]}  DET={det[(t,s)].split(':')[-1][:34]}")
            shown += 1
            if shown >= 20: break
