"""The two A4-boundary owners the stores do not hold, rebuilt from exact byte recipes
(Codex SEQ 1572, replacing the rejected chronology replay).

A6/accounting owner: source-A lines 1..620 then source-B lines 192..255, newlines preserved,
nothing added or removed -> 33,302 bytes, sha256 f0d7b828...
Raw transport: the stage-1 bytes, the record-91763 Edit reversed once (new -> old), then three
literal block reversals, each matching exactly once -> 86,695 bytes, 1,824 newlines, ending in
a newline, sha256 05b02f5b...

Every input is a copied immutable file under inputs/ (its source, size and hash recorded in
SOURCES.tsv); every pin is checked before and after; any mismatch refuses and writes nothing.
The runtime reads only this candidate.

    owners_recipe.py            build both owners under experiments/harness_g1v3/ (fail closed)
    owners_recipe.py --verify   re-derive both from inputs/ and compare with the files on disk
"""
import hashlib
import io
import json
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
IN = os.path.join(R, "inputs", "owner_recipes")
OUT = os.path.join(R, "experiments", "harness_g1v3")

A6 = {
    "source_a": ("blob_5ae25b1d9248ea60", "5ae25b1d9248ea607414f28775c50a404a3b61f41e1ac1757c9f18dbda1b156c", 1, 620),
    "source_b": ("blob_2b8667dc9614c965", "2b8667dc9614c9655d653969a0f8069cec34a7c6e2f11b244ed925ea94b3b4fd", 192, 255),
    "bytes": 33302,
    "sha256": "f0d7b8281ae13bc8184be34253bf0236132c1900f60db574d005ae018880d4de",
}
RAW = {
    "base": ("stage1_raw_transport.py", "cf22ccd6e045ff1187d996c27d3caf770c1c6bf2dd23a768b5494c5ccde00a72"),
    "edit_record": "transcript_record_91763.json",
    "after_edit": (86750, "02f51e5a8a8bd87d3a97eb44aeae57ba127492a9bebdb8df3f1471d8859fae4b"),
    "blocks": [
        ('''    derived = blm.derive_expected(
        plan.get("runtime_model_id"),
        contract_suffix=plan.get("contract_suffix"),
        inventory=blm.plan_inventory(plan))
''', '''    derived = blm.derive_expected(
        plan.get("runtime_model_id", inventory=blm.plan_inventory(plan)),
        contract_suffix=plan.get("contract_suffix"))
'''),
        ('''    derived = blm.derive_expected(
        plan.get("runtime_model_id", inventory=blm.plan_inventory(plan)),
        contract_suffix=plan.get("contract_suffix"))
''', '''    derived = blm.derive_expected(
        plan.get("runtime_model_id"),
        contract_suffix=plan.get("contract_suffix"))
'''),
        ('with io.open(blm.plan_inventory(plan), encoding="utf-8") as fh:',
         'with io.open(blm.INVENTORY, encoding="utf-8") as fh:'),
    ],
    "bytes": 86695,
    "newlines": 1824,
    "sha256": "05b02f5bb67944d39fcf726da043f768d5d640bddbe18754ce3c3ef6c4bc10de",
}


class Refused(SystemExit):
    pass


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _read(name, sha):
    p = os.path.join(IN, name)
    if not os.path.isfile(p):
        raise Refused("REFUSED: recipe input missing: inputs/owner_recipes/%s" % name)
    b = io.open(p, "rb").read()
    if _sha(b) != sha:
        raise Refused("REFUSED: recipe input %s is %s, not %s" % (name, _sha(b)[:16], sha[:16]))
    return b


def _lines(b, lo, hi):
    """Bytes of lines lo..hi inclusive (1-based), each with its newline, as they stand."""
    parts = b.split(b"\n")
    if len(parts) - 1 < hi:
        raise Refused("REFUSED: source has only %d lines, %d requested" % (len(parts) - 1, hi))
    return b"".join(x + b"\n" for x in parts[lo - 1:hi])


def a6_bytes():
    a_name, a_sha, a_lo, a_hi = A6["source_a"]
    b_name, b_sha, b_lo, b_hi = A6["source_b"]
    out = _lines(_read(a_name, a_sha), a_lo, a_hi) + _lines(_read(b_name, b_sha), b_lo, b_hi)
    if len(out) != A6["bytes"] or _sha(out) != A6["sha256"]:
        raise Refused("REFUSED: A6 recipe gives %d bytes %s, not %d bytes %s" % (len(out), _sha(out)[:16], A6["bytes"], A6["sha256"][:16]))
    return out


def raw_bytes():
    name, sha = RAW["base"]
    s = _read(name, sha).decode("utf-8")
    rec = json.loads(_read(RAW["edit_record"], _edit_record_sha()).decode("utf-8"))
    use = [c for c in rec["message"]["content"] if isinstance(c, dict) and c.get("type") == "tool_use"]
    if len(use) != 1 or use[0]["name"] != "Edit" or not use[0]["input"]["file_path"].endswith("/raw_transport.py"):
        raise Refused("REFUSED: record 91763 is not the single Edit of raw_transport.py")
    old, new = use[0]["input"]["old_string"], use[0]["input"]["new_string"]
    if s.count(new) != 1:
        raise Refused("REFUSED: the record-91763 text occurs %d times in the stage-1 bytes" % s.count(new))
    s = s.replace(new, old, 1)
    b = s.encode("utf-8")
    if (len(b), _sha(b)) != RAW["after_edit"]:
        raise Refused("REFUSED: after the 91763 reversal: %d bytes %s" % (len(b), _sha(b)[:16]))
    for i, (old_, new_) in enumerate(RAW["blocks"], 1):
        if s.count(old_) != 1:
            raise Refused("REFUSED: block reversal %d matches %d times" % (i, s.count(old_)))
        s = s.replace(old_, new_, 1)
    b = s.encode("utf-8")
    if len(b) != RAW["bytes"] or b.count(b"\n") != RAW["newlines"] or not b.endswith(b"\n") or _sha(b) != RAW["sha256"]:
        raise Refused("REFUSED: raw recipe gives %d bytes, %d newlines, %s" % (len(b), b.count(b"\n"), _sha(b)[:16]))
    return b


def _edit_record_sha():
    p = os.path.join(IN, "SOURCES.tsv")
    if not os.path.isfile(p):
        raise Refused("REFUSED: inputs/owner_recipes/SOURCES.tsv missing")
    for l in io.open(p, encoding="utf-8").read().split("\n")[1:]:
        if l.strip() and os.path.basename(l.split("\t")[4]) == RAW["edit_record"]:
            return l.split("\t")[2]
    raise Refused("REFUSED: the record-91763 input is not in SOURCES.tsv")


def build():
    outs = {"a6_launch_freeze.py": a6_bytes(), "raw_transport.py": raw_bytes()}
    os.makedirs(OUT, exist_ok=True)
    for name, b in outs.items():
        io.open(os.path.join(OUT, name), "wb").write(b)
        print("OWNER %s %d bytes sha256 %s" % (name, len(b), _sha(b)))
    return 0


def verify():
    bad = []
    for name, b in (("a6_launch_freeze.py", a6_bytes()), ("raw_transport.py", raw_bytes())):
        p = os.path.join(OUT, name)
        if not os.path.isfile(p):
            bad.append("%s absent" % name)
        elif io.open(p, "rb").read() != b:
            bad.append("%s differs from its recipe" % name)
    print("owner recipes: %s" % ("both hold" if not bad else "; ".join(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(verify() if "--verify" in sys.argv[1:] else build())
