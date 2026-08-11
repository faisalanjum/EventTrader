"""#827 ROUND 3 — mutation proof for the PACKET EVIDENCE CENSUS.

The census is a script, not a pytest test, so `step4_mutations.py` (which runs
pytest detectors) cannot reach it. Every repaired check therefore needs its own
runnable proof here.

TWO KINDS OF CASE, and the second kind is the one that was missing:

  MUST-CATCH  a real corruption; the census must report a problem.
  MUST-ALLOW  something PRODUCTION legitimately emits; the census must stay
              silent. Two rules were wrong in this direction — a repeated quote
              (lawful: `verify_occurrence` disambiguates with an occurrence
              index) and two pieces sharing text at different spans (lawful:
              two header cells both reading "Total"). A checker is only correct
              if it is correct in BOTH directions, so both are pinned.

A CLEAN CONTROL runs first: the unmutated packets must report ZERO problems.

The live packets are NEVER touched — each case copies them to a temp directory,
mutates the copy, and throws it away. Read-only w.r.t. the repository; no graph,
no network, no AI.

Run:  venv/bin/python receipts_827/packet_census_mutations.py
Out:  receipts_827/12_packet_census_mutations.json
"""
import datetime
import glob as _glob
import hashlib
import json
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, _HERE)
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "driver", "relocation"))
OUT = os.path.join(_HERE, "12_packet_census_mutations.json")
CACHE = os.path.join(_REPO, "scripts", "driver_seed", "relocate_probe",
                     "inline_html_cache")


def copy_packets(tmp, drop_one=False):
    src = sorted(_glob.glob(os.path.join(
        _REPO, "data", "driver_catalog_seed", "*", "packets.jsonl")))
    if not src:
        raise RuntimeError("no packets.jsonl discovered — no premise")
    if drop_one:
        src = src[1:]
    out = []
    for i, p in enumerate(src):
        d = os.path.join(tmp, f"pk{i}")
        os.makedirs(d)
        dst = os.path.join(d, "packets.jsonl")
        shutil.copy2(p, dst)
        out.append(dst)
    return out


def run_census(packet_paths, tmp):
    import packet_evidence_census as C
    C.OUT = os.path.join(tmp, "out.json")
    C.MANIFEST = os.path.join(tmp, "m.txt")
    real = _glob.glob
    C.glob.glob = lambda pat: (sorted(packet_paths) if "packets.jsonl" in pat
                               else real(pat))
    try:
        rc = C.main()
    finally:
        C.glob.glob = real
    return rc, json.load(open(C.OUT)).get("problems", [])


def _prepared(source_id, _cache={}):
    """The filing's prepared text — needed to build a LAWFUL second span."""
    if source_id not in _cache:
        from driver.relocation.inline_html import prepare
        path = os.path.join(CACHE, f"{source_id}.htm")
        _cache[source_id] = prepare(
            open(path, encoding="utf-8", errors="replace").read())
    return _cache[source_id]


def mutate(paths, fn, require_change=True):
    n = 0
    for p in paths:
        lines = []
        for line in open(p, encoding="utf-8"):
            if not line.strip():
                continue
            packet = json.loads(line)
            for item in packet.get("items", []):
                ev = (item.get("xbrl") or {}).get("source_evidence")
                if ev and fn(packet, item, ev):
                    n += 1
            lines.append(json.dumps(packet))
        open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    if require_change and not n:
        raise RuntimeError("the mutation changed NOTHING — it proves nothing")
    return n


# ---- MUST-CATCH ----------------------------------------------------------

def dup_piece_same_span(_pkt, _item, ev, _d=[]):
    """The same address twice — no new evidence."""
    if _d or not ev.get("pieces"):
        return False
    ev["pieces"] = list(ev["pieces"]) + [dict(ev["pieces"][0])]
    _d.append(1)
    return True


def drop_label_span(_pkt, _item, ev):
    if ev.get("raw_label_span") is None:
        return False
    ev["raw_label_span"] = None
    return True


def shift_quote_span(_pkt, _item, ev, _d=[]):
    if _d:
        return False
    a, b = ev["quote_span"]
    ev["quote_span"] = [a + 1, b + 1]
    _d.append(1)
    return True


def swap_claimed_quote(_pkt, item, _ev, _d=[]):
    if _d:
        return False
    item["quote"] = (item.get("quote") or "") + " NOT THE ROW AT THIS SPAN"
    _d.append(1)
    return True


def corrupt_representation_sha(_pkt, _item, ev, _d=[]):
    if _d:
        return False
    ev["representation_sha256"] = "0" * 64
    _d.append(1)
    return True


# ---- MUST-ALLOW (production-consistent) ----------------------------------

def piece_repeated_text_new_span(pkt, _item, ev, _d=[]):
    """A SECOND piece with the same (kind, text) at a DIFFERENT LAWFUL span —
    exactly what `inline_html` emits when two header cells read alike."""
    if _d or not ev.get("pieces"):
        return False
    text = _prepared(pkt["source_id"])["text"]
    for piece in ev["pieces"]:
        second = text.find(piece["text"], piece["span"][1])
        if second != -1:
            ev["pieces"] = list(ev["pieces"]) + [
                {"kind": piece["kind"], "text": piece["text"],
                 "span": [second, second + len(piece["text"])]}]
            _d.append(1)
            return True
    return False


def quote_that_lawfully_REPEATS(pkt, item, ev, _d=[]):
    """Repoint a WHOLE shared-row group at a window that occurs TWICE.

    THE CONTROL THAT WAS PROMISED AND MISSING. The docstring claimed two lawful
    controls and the table held one, so reintroducing the old
    "a quote must occur exactly once" rule would still have passed — the rule
    that CONTRADICTED production (`verify_occurrence` admits n>1 and
    disambiguates with an occurrence index).

    The whole GROUP moves together, and the label claim is dropped on both
    members, so the group key stays shared: multiplicities remain [4,3,2,2] and
    header-sequence distinctness is untouched. Mutating one member alone would
    split the group and trip the pinned multiplicities — failing for a reason
    that has nothing to do with repetition.
    """
    if pkt["source_id"] != "0001646972-23-000056" or len(_d) >= 2:
        return False
    text = _prepared(pkt["source_id"])["text"]
    window = None
    for n in (60, 50, 40, 30):
        for i in range(0, len(text) - n, 7):
            w = text[i:i + n]
            if w.strip() == w and len(w) == n and text.count(w) >= 2:
                window = (w, i, i + n)
                break
        if window:
            break
    if window is None:
        raise RuntimeError("no repeated window in the filing — control has no premise")
    w, a, b = window
    ev["quote_span"] = [a, b]
    ev["raw_label_span"] = None          # no label claimed -> no label required
    item["quote"] = w
    item["raw_label_or_claim"] = None
    _d.append(1)
    return True


CASES = [
    ("MUST-ALLOW  a quote that lawfully occurs TWICE in the filing",
     quote_that_lawfully_REPEATS, False),
    ("MUST-CATCH  a duplicated evidence piece (same span)", dup_piece_same_span, True),
    ("MUST-CATCH  every raw_label_span removed", drop_label_span, True),
    ("MUST-CATCH  a quote span shifted by one", shift_quote_span, True),
    ("MUST-CATCH  the item's own quote swapped for another row's",
     swap_claimed_quote, True),
    ("MUST-CATCH  a corrupted representation_sha256",
     corrupt_representation_sha, True),
    ("MUST-ALLOW  the same (kind,text) piece at a DIFFERENT lawful span",
     piece_repeated_text_new_span, False),
]


def main():
    results, problems = [], []

    tmp = tempfile.mkdtemp(prefix="pcm_control_")
    try:
        rc, found = run_census(copy_packets(tmp), tmp)
        results.append({"phase": "clean control", "rc": rc, "problems": found})
        if rc != 0 or found:
            problems.append(f"the CLEAN control reported {len(found)} "
                            f"problem(s) — every case below is meaningless")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # THE WHOLE-FILE CASE is separate: it mutates the INPUT SET, not an item.
    tmp = tempfile.mkdtemp(prefix="pcm_drop_")
    try:
        rc, found = run_census(copy_packets(tmp, drop_one=True), tmp)
        caught = bool(found)
        results.append({"phase": "case", "name": "MUST-CATCH  a whole packet "
                        "file deleted from the input set", "rc": rc,
                        "caught": caught, "problem_count": len(found),
                        "problems": found[:2]})
        print(f"[{'CAUGHT ' if caught else 'ESCAPED'}] MUST-CATCH  a whole "
              f"packet file deleted ({len(found)} problem(s))", flush=True)
        if not caught:
            problems.append("deleting a whole packet file did not fail the "
                            "census — its premise can silently shrink")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    for name, fn, must_catch in CASES:
        tmp = tempfile.mkdtemp(prefix="pcm_")
        try:
            paths = copy_packets(tmp)
            n = mutate(paths, fn)
            rc, found = run_census(paths, tmp)
            ok = bool(found) if must_catch else not found
            results.append({"phase": "case", "name": name, "items_mutated": n,
                            "rc": rc, "must_catch": must_catch, "ok": ok,
                            "problem_count": len(found),
                            "problems": found[:2]})
            print(f"[{'OK     ' if ok else 'FAILED '}] {name} "
                  f"({n} mutated, {len(found)} problem(s))", flush=True)
            if not ok:
                problems.append(
                    f"{name}: expected the census to "
                    f"{'REPORT' if must_catch else 'ALLOW'} this, it did not")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    doc = {"receipt": "#827 round 3 — packet-census mutation proof",
           "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
           "method": "the REAL census over COPIES of the real packets; the "
                     "live packets are never edited; a clean control must "
                     "report zero problems first; MUST-ALLOW cases prove the "
                     "census does not over-reject what production emits",
           "script_sha256": hashlib.sha256(
               open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "results": results, "problems": problems}
    open(OUT, "w").write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"\nproblems: {len(problems)}")
    for p in problems:
        print("   ", p)
    print(f"wrote {os.path.basename(OUT)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
