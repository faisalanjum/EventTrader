"""
grade.py — deterministic grader for the Step 4 naming proof.

Two modes:
  python3 grade.py --blind            -> writes blind_quotes.json (id, source_type, quote) for the readers
  python3 grade.py r1.json r2.json .. -> grades each reader file, aggregates (ANY flicker = fail), prints GO/NO-GO

A reader file is a JSON list of {"id": "...", "driver_name": "..."} (a dict {id:name} also works).

Checks per case (name N; tokens = slug(N).split('_')):
  C1 per-X presence  : per_share kind -> name carries eps/dps/per_share/per_unit;
                       per-X kinds carry the basis via must_contain_tokens (incl. 'per').
  C2 no-invent       : if no_invent, 'per' must NOT be a token (no hallucinated basis).
  C3 must_contain    : all required tokens present.
  C4 must_not_contain: no forbidden token present (token-level; 'per' substring in 'operating' is NOT a hit).
  C5 resolver/lint   : resolve_unit(N, unit_raw, hints).canonical_unit == expected_unit;
                       and for a USD per-X, lint_per_x_naming(N, unit_raw) is None (name carries the basis).
  C6 distinctness    : within a distinct_group, the produced names must all differ (Rule 3 / no wrong SAME_AS).

Gate: golden 100% AND real_perx 100% AND real_negative 0 invented — across EVERY reader run.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "unit_probe"))
from unit_resolver import resolve_unit, lint_per_x_naming, _gid  # noqa: E402

CORPUS = json.load(open(os.path.join(HERE, "corpus.json")))["cases"]


def toks(name):
    return set(_gid.slug(name or "").split("_")) - {""}


def per_share_ok(t):
    return bool(t & {"eps", "dps"}) or {"per", "share"} <= t or {"per", "unit"} <= t


def grade_case(c, name):
    """Return (ok, [failed_check_strings])."""
    L = c["label"]
    t = toks(name)
    fails = []
    if L.get("per_share") and not per_share_ok(t):
        fails.append("C1 per-share: name lacks eps/dps/per_share/per_unit")
    if L.get("no_invent") and "per" in t:
        fails.append("C2 no-invent: hallucinated a 'per' basis")
    for mc in L.get("must_contain_tokens", []):
        if mc not in t:
            fails.append(f"C3 must_contain: missing '{mc}'")
    for mn in L.get("must_not_contain_tokens", []):
        if mn in t:
            fails.append(f"C4 forbidden token present: '{mn}'")
    r = resolve_unit(name, L["unit_raw"], None,
                     unit_kind_hint=L.get("unit_kind_hint"),
                     money_mode_hint=L.get("money_mode_hint"))
    if r.canonical_unit != L["expected_unit"]:
        fails.append(f"C5 unit: got {r.canonical_unit} want {L['expected_unit']}")
    if L.get("usd_per_x"):
        lint = lint_per_x_naming(name, L["unit_raw"])
        if lint is not None:
            fails.append("C5 lint: name fails per-X lint (basis not in name)")
    return (not fails), fails


def load_reader(path):
    data = json.load(open(path))
    if isinstance(data, dict):
        return data
    return {d["id"]: d.get("driver_name", "") for d in data}


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--blind":
        blind = [{"id": c["id"], "source_type": c["source_type"], "quote": c["quote"]} for c in CORPUS]
        out = os.path.join(HERE, "blind_quotes.json")
        json.dump(blind, open(out, "w"), indent=1)
        print(f"wrote {out} ({len(blind)} quotes, NO labels)")
        return

    reader_files = sys.argv[1:]
    if not reader_files:
        print("usage: grade.py --blind | grade.py r1.json [r2.json ...]")
        sys.exit(2)

    readers = {os.path.basename(p): load_reader(p) for p in reader_files}
    ids = [c["id"] for c in CORPUS]
    by_id = {c["id"]: c for c in CORPUS}

    # per-(reader,case) result
    res = {}  # (rname, id) -> (ok, fails, name)
    for rname, rmap in readers.items():
        for cid in ids:
            name = rmap.get(cid, "")
            if not name:
                res[(rname, cid)] = (False, ["MISSING reader output"], "")
                continue
            ok, fails = grade_case(by_id[cid], name)
            res[(rname, cid)] = (ok, fails, name)

    # C6 distinctness per reader per group
    for rname, rmap in readers.items():
        groups = {}
        for c in CORPUS:
            g = c["label"].get("distinct_group")
            if g:
                groups.setdefault(g, []).append(c["id"])
        for g, cids in groups.items():
            names = [_gid.slug(rmap.get(cid, "")) for cid in cids]
            if len(set(names)) != len(names):
                for cid in cids:
                    ok, fails, nm = res[(rname, cid)]
                    fails = list(fails) + [f"C6 distinctness: group '{g}' names collided ({names})"]
                    res[(rname, cid)] = (False, fails, nm)

    # matrix + failures
    print(f"=== readers: {list(readers)} ===\n")
    hdr = f"{'id':<5} {'layer':<14} " + " ".join(f"{r[:10]:<11}" for r in readers) + "  names"
    print(hdr); print("-" * len(hdr))
    layer_stats = {}
    flicker_fail_ids = []
    for cid in ids:
        c = by_id[cid]
        layer = c["layer"]
        cells, names, all_ok = [], [], True
        for rname in readers:
            ok, fails, nm = res[(rname, cid)]
            cells.append("OK " if ok else "XX ")
            names.append(nm)
            all_ok = all_ok and ok
        layer_stats.setdefault(layer, [0, 0])
        layer_stats[layer][1] += 1
        layer_stats[layer][0] += all_ok
        if not all_ok:
            flicker_fail_ids.append(cid)
        nameshow = names[0] if len(set(names)) == 1 else " | ".join(names)
        print(f"{cid:<5} {layer:<14} " + " ".join(f"{x:<11}" for x in cells) + f"  {nameshow}")

    print("\n=== FAILURES (any reader) ===")
    if not flicker_fail_ids:
        print("  none")
    for cid in flicker_fail_ids:
        for rname in readers:
            ok, fails, nm = res[(rname, cid)]
            if not ok:
                print(f"  [{cid}] {rname}: name={nm!r} -> {'; '.join(fails)}")

    print("\n=== PER-LAYER (passes = ALL readers correct; any flicker = fail) ===")
    for layer, (p, tot) in sorted(layer_stats.items()):
        print(f"  {layer:<14} {p}/{tot} = {p/tot*100:.0f}%")

    golden = layer_stats.get("golden", [0, 0])
    perx = layer_stats.get("real_perx", [0, 0])
    neg = layer_stats.get("real_negative", [0, 0])
    gate = (golden[0] == golden[1]) and (perx[0] == perx[1]) and (neg[0] == neg[1])
    print("\n=== GATE ===")
    print(f"  golden 100%:        {'PASS' if golden[0]==golden[1] else 'FAIL'} ({golden[0]}/{golden[1]})")
    print(f"  real per-X 100%:    {'PASS' if perx[0]==perx[1] else 'FAIL'} ({perx[0]}/{perx[1]})")
    print(f"  negatives 0-invent: {'PASS' if neg[0]==neg[1] else 'FAIL'} ({neg[0]}/{neg[1]})")
    print(f"\n  >>> {'GO — prompt is locked' if gate else 'NO-GO — prompt NOT locked'} <<<")
    sys.exit(0 if gate else 1)


if __name__ == "__main__":
    main()
