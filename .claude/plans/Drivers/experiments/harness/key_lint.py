#!/usr/bin/env python3
"""EXP-0 / WP-KEYS linter + blind projector for K-pairs (READ-ONLY, 0 LLM, no network, no Neo4j).

Subcommands:
  lint  --key <K-pairs.vN.jsonl>   validate kp_ schema + strata quotas + ANTI-TELL (no surface-stat leaks).
                                   Exit 0 iff clean. sha_lock.py refuses to lock a key that does not lint clean.
  blind --key <...> --arm <arm>    emit the grader-VISIBLE projection: raw sides only
                                   (name, quotes, slice_tokens, per_x, industry) with gold / gold_rationale /
                                   family / provenance / rival STRIPPED, deterministically shuffled by
                                   h32(arm+pair_id). This projector is the single choke point that enforces
                                   grader blindness (kernel section 9 smoke-alarm). Never spends an LLM call.

Anti-tell (protocol section 7): no single surface feature of the VISIBLE fields may separate SAME from
DIFFERENT beyond tolerance. Separation = 2*|AUC-0.5| for numeric features, class-rate deviation for
categorical. Also enforces the hard-SAME floor. Locked keys are immutable (WorkOrder section 1.4)."""
import argparse
import hashlib
import json
import re
import sys

DIFFERENT_FAMILIES = [
    "bookings_billings", "adjusted_vs_gaap", "gross_net", "segment_consolidated",
    "deferred_recognized", "genus_species", "benchmark_siblings", "cause_consequence",
    "channel_homonym", "ownership_axis", "per_x", "cross_flavor",
]
SAME_FAMILY = "synonym"
MINED_FAMILY = "mined"
FAMILIES = DIFFERENT_FAMILIES + [SAME_FAMILY, MINED_FAMILY]
PROVENANCE = ("planted", "mined")
GOLD = ("SAME", "DIFFERENT")
BLIND_SIDE_FIELDS = ["name", "quotes", "slice_tokens", "per_x", "industry"]

_TOK = re.compile(r"[a-z0-9]+")


def h32(s):
    """32-bit rolling hash, byte-identical to the ab_ kit's JS h32 (ASCII/BMP)."""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def canon(v):
    """Canonical serializer byte-identical to the ab_pair_judge.js JS canon (sorted keys, compact),
    so a workflow's h32(canon(pairs)) matches this module's page_h32 across the JS/python boundary."""
    if isinstance(v, list):
        return "[" + ",".join(canon(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canon(v[k]) for k in sorted(v)) + "}"
    return json.dumps(v, ensure_ascii=False)


def load_records(path):
    recs = []
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append((ln, json.loads(line)))
            except Exception as e:
                raise SystemExit("ABORT: %s:%d not valid JSON: %s" % (path, ln, e))
    return recs


# ---------------------------------------------------------------- surface features (VISIBLE fields only)
def _side_text(side):
    return (side.get("name", "") or "") + " " + " ".join(side.get("quotes", []) or [])


def _tokens(side):
    return set(_TOK.findall(_side_text(side).lower()))


def surface_features(rec):
    a, b = rec.get("side_a", {}), rec.get("side_b", {})
    ta, tb = _tokens(a), _tokens(b)
    uni = ta | tb
    na, nb = set(_TOK.findall((a.get("name", "") or "").lower())), set(_TOK.findall((b.get("name", "") or "").lower()))
    nuni = na | nb
    txt = _side_text(a) + _side_text(b)
    qa, qb = " ".join(a.get("quotes", []) or []), " ".join(b.get("quotes", []) or [])
    return {
        "lexical_overlap": (len(ta & tb) / len(uni)) if uni else 0.0,
        "name_overlap": (len(na & nb) / len(nuni)) if nuni else 0.0,
        "quote_char_total": float(len(qa) + len(qb)),
        "quote_char_absdiff": float(abs(len(qa) - len(qb))),
        "digit_frac": (sum(c.isdigit() for c in txt) / len(txt)) if txt else 0.0,
        # categorical
        "industry": rec.get("side_a", {}).get("industry"),
        "per_x_present": bool(a.get("per_x") or b.get("per_x")),
        "slice_present": bool(a.get("slice_tokens") or b.get("slice_tokens")),
        "name_exact_equal": (a.get("name", "") or "").strip().lower() == (b.get("name", "") or "").strip().lower(),
        "pct_present": ("%" in txt) or ("percent" in txt.lower()),
    }


def _auc(pos, neg):
    """AUC of a numeric feature separating pos (label=1) from neg (label=0). Ties=0.5."""
    if not pos or not neg:
        return 0.5
    wins = 0.0
    for x in pos:
        for y in neg:
            wins += 1.0 if x > y else (0.5 if x == y else 0.0)
    return wins / (len(pos) * len(neg))


NUMERIC = ["lexical_overlap", "name_overlap", "quote_char_total", "quote_char_absdiff", "digit_frac"]
CATEGORICAL = ["industry", "per_x_present", "slice_present", "name_exact_equal", "pct_present"]


def anti_tell(recs, sep_max=0.40, cat_dev_max=0.30, cat_support=10, hard_same_min=12, hard_overlap_max=0.34):
    """Returns (ok, findings, report). A finding = a surface feature that separates the classes too well."""
    feats = []
    for _ln, r in recs:
        f = surface_features(r)
        f["_gold"] = r.get("gold")
        feats.append(f)
    same = [f for f in feats if f["_gold"] == "SAME"]
    diff = [f for f in feats if f["_gold"] == "DIFFERENT"]
    n = len(feats)
    base_same = (len(same) / n) if n else 0.0
    findings = []
    report = {"base_same_rate": round(base_same, 4), "numeric": {}, "categorical": {}}

    for key in NUMERIC:
        ps = [f[key] for f in same]
        ng = [f[key] for f in diff]
        auc = _auc(ps, ng)
        sep = 2 * abs(auc - 0.5)
        report["numeric"][key] = {"auc": round(auc, 4), "separation": round(sep, 4),
                                  "mean_same": round(sum(ps) / len(ps), 4) if ps else None,
                                  "mean_diff": round(sum(ng) / len(ng), 4) if ng else None}
        if sep > sep_max:
            findings.append("TELL[numeric] '%s' separates classes: separation=%.3f > %.2f (auc=%.3f)"
                            % (key, sep, sep_max, auc))

    for key in CATEGORICAL:
        vals = {}
        for f in feats:
            v = f[key]
            d = vals.setdefault(v, {"n": 0, "same": 0})
            d["n"] += 1
            d["same"] += 1 if f["_gold"] == "SAME" else 0
        report["categorical"][key] = {}
        for v, d in vals.items():
            rate = d["same"] / d["n"] if d["n"] else 0.0
            report["categorical"][key][str(v)] = {"n": d["n"], "same_rate": round(rate, 4)}
            if d["n"] >= cat_support and abs(rate - base_same) > cat_dev_max:
                findings.append("TELL[categorical] '%s'=%s is class-skewed: same_rate=%.3f vs base %.3f (n=%d)"
                                % (key, v, rate, base_same, d["n"]))

    # hard-SAME floor: enough SAME with LOW lexical overlap (different vocabulary, not easy synonyms)
    hard_same = sum(1 for f in same if f["lexical_overlap"] <= hard_overlap_max)
    report["hard_same_count"] = hard_same
    report["hard_same_required"] = hard_same_min
    if hard_same < hard_same_min:
        findings.append("HARD-SAME shortfall: only %d SAME with overlap<=%.2f, need >=%d"
                        % (hard_same, hard_overlap_max, hard_same_min))

    return (len(findings) == 0, findings, report)


def _check_side(side, where, errs):
    if not isinstance(side, dict):
        errs.append("%s: not an object" % where); return
    if not (isinstance(side.get("name"), str) and side.get("name").strip()):
        errs.append("%s.name missing/empty" % where)
    q = side.get("quotes")
    if not (isinstance(q, list) and len(q) >= 1 and all(isinstance(x, str) and x.strip() for x in q)):
        errs.append("%s.quotes must be a list of >=1 non-empty strings" % where)
    if not isinstance(side.get("slice_tokens", []), list):
        errs.append("%s.slice_tokens must be a list" % where)
    if not (side.get("per_x") is None or isinstance(side.get("per_x"), str)):
        errs.append("%s.per_x must be null or string" % where)
    if not (isinstance(side.get("industry"), str) and side.get("industry").strip()):
        errs.append("%s.industry missing/empty" % where)
    if not (side.get("fact_type") is None or isinstance(side.get("fact_type"), str)):
        errs.append("%s.fact_type must be null or string" % where)


def lint_key(path, expect_total=160, expect_diff=110, expect_same=50,
             per_family_min=8, families_min=12, allow_mined=False, run_anti_tell=True):
    """Returns (ok, errors, stats). families_min = number of DIFFERENT families that must be used (>=8 each)."""
    recs = load_records(path)
    errs = []
    seen = set()
    n_diff = n_same = n_planted = n_mined = 0
    fam_diff = {}
    for ln, r in recs:
        tag = "line %d" % ln
        pid = r.get("pair_id")
        if not (isinstance(pid, str) and re.match(r"^kp_\d+$", pid)):
            errs.append("%s: pair_id must match ^kp_\\d+$" % tag)
        elif pid in seen:
            errs.append("%s: duplicate pair_id %s" % (tag, pid))
        else:
            seen.add(pid)
        prov = r.get("provenance")
        if prov not in PROVENANCE:
            errs.append("%s: provenance must be one of %s" % (tag, PROVENANCE))
        fam = r.get("family")
        if fam not in FAMILIES:
            errs.append("%s: family '%s' not allowed" % (tag, fam))
        if fam == MINED_FAMILY and not allow_mined:
            errs.append("%s: family 'mined' forbidden in v1" % tag)
        gold = r.get("gold")
        if gold not in GOLD:
            errs.append("%s: gold must be SAME|DIFFERENT" % tag)
        if not (isinstance(r.get("gold_rationale"), str) and r.get("gold_rationale").strip()):
            errs.append("%s: gold_rationale missing/empty" % tag)
        if not isinstance(r.get("hard"), bool):
            errs.append("%s: hard must be boolean" % tag)
        if not (r.get("rival") is None or isinstance(r.get("rival"), dict)):
            errs.append("%s: rival must be null or object" % tag)
        # NO source refs allowed in the grader-visible key (protocol section 2/3)
        for banned in ("source_ref", "source", "source_id", "grounding", "sidecar"):
            if banned in r:
                errs.append("%s: banned field '%s' in grader-visible key (belongs in sidecar)" % (tag, banned))
        _check_side(r.get("side_a"), "%s side_a" % tag, errs)
        _check_side(r.get("side_b"), "%s side_b" % tag, errs)
        if prov == "planted" and gold in GOLD:
            if gold == "SAME" and fam != SAME_FAMILY:
                errs.append("%s: planted-SAME must be family '%s' (got %s)" % (tag, SAME_FAMILY, fam))
            if gold == "DIFFERENT" and fam not in DIFFERENT_FAMILIES:
                errs.append("%s: planted-DIFFERENT must be a trap family (got %s)" % (tag, fam))
        n_mined += 1 if prov == "mined" else 0
        n_planted += 1 if prov == "planted" else 0
        if gold == "DIFFERENT":
            n_diff += 1
            if fam in DIFFERENT_FAMILIES:
                fam_diff[fam] = fam_diff.get(fam, 0) + 1
        elif gold == "SAME":
            n_same += 1
    # strata
    if expect_total is not None and len(recs) != expect_total:
        errs.append("STRATA: expected %d records, found %d" % (expect_total, len(recs)))
    if expect_diff is not None and n_diff != expect_diff:
        errs.append("STRATA: expected %d gold=DIFFERENT, found %d" % (expect_diff, n_diff))
    if expect_same is not None and n_same != expect_same:
        errs.append("STRATA: expected %d gold=SAME, found %d" % (expect_same, n_same))
    if not allow_mined and n_mined:
        errs.append("STRATA: %d mined rows in a v1 (planted-only) key" % n_mined)
    used = sorted(f for f, c in fam_diff.items() if c > 0)
    if families_min is not None and len(used) < families_min:
        errs.append("STRATA: %d DIFFERENT families used, need >=%d" % (len(used), families_min))
    if per_family_min is not None:
        for f in DIFFERENT_FAMILIES:
            c = fam_diff.get(f, 0)
            if c < per_family_min:
                errs.append("STRATA: family '%s' has %d < %d planted-DIFFERENT" % (f, c, per_family_min))
    stats = {"n_records": len(recs), "gold_DIFFERENT": n_diff, "gold_SAME": n_same,
             "planted": n_planted, "mined": n_mined, "families_used": used, "by_family_DIFFERENT": fam_diff}
    # anti-tell
    at_report = None
    if run_anti_tell and not any(e.startswith("STRATA") or e.startswith("ABORT") for e in errs):
        ok_at, at_findings, at_report = anti_tell(recs)
        errs.extend(at_findings)
    stats["anti_tell"] = at_report
    return (len(errs) == 0, errs, stats)


def project_blind(path, arm):
    recs = load_records(path)
    pairs = []
    for _ln, r in recs:
        pairs.append({
            "pair_id": r.get("pair_id"),
            "side_a": {k: r.get("side_a", {}).get(k) for k in BLIND_SIDE_FIELDS},
            "side_b": {k: r.get("side_b", {}).get(k) for k in BLIND_SIDE_FIELDS},
        })
    # per-arm shuffle: md5 avalanche so arms differing by one char get fully distinct orders (parallel
    # judging makes order immaterial to the gate, but the work order asks for a per-arm shuffle).
    pairs.sort(key=lambda p: hashlib.md5((arm + ":" + str(p["pair_id"])).encode()).hexdigest())
    return pairs, h32(canon(pairs))


def main(argv=None):
    ap = argparse.ArgumentParser(description="K-pairs linter + blind projector (0 LLM)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("lint")
    pl.add_argument("--key", required=True)
    pl.add_argument("--expect-total", type=int, default=160)
    pl.add_argument("--expect-diff", type=int, default=110)
    pl.add_argument("--expect-same", type=int, default=50)
    pl.add_argument("--per-family-min", type=int, default=8)
    pl.add_argument("--families-min", type=int, default=12)
    pl.add_argument("--allow-mined", action="store_true")
    pl.add_argument("--no-anti-tell", action="store_true")
    pb = sub.add_parser("blind")
    pb.add_argument("--key", required=True)
    pb.add_argument("--arm", required=True)
    pb.add_argument("--page-h32-only", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "lint":
        ok, errs, stats = lint_key(a.key, a.expect_total, a.expect_diff, a.expect_same,
                                   a.per_family_min, a.families_min, a.allow_mined, not a.no_anti_tell)
        print(json.dumps({"ok": ok, "errors": errs, "stats": stats}, indent=2, sort_keys=True))
        sys.exit(0 if ok else 1)
    elif a.cmd == "blind":
        pairs, page = project_blind(a.key, a.arm)
        if a.page_h32_only:
            print(page)
        else:
            print(json.dumps({"arm": a.arm, "n": len(pairs), "page_h32": page, "pairs": pairs},
                             sort_keys=True, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main()
