"""The five package source texts that build_kfields_final reads beside itself (Codex SEQ 1575
item 4), each a deterministic byte recipe over one copied immutable input under
inputs/package_texts/ (source, size and hash recorded in inputs/owner_recipes/SOURCES.tsv):

  owner_rulings_1383.txt   archive 1383: from the first OWNER RULINGS marker up to (excluding)
                           the KNOWN CLASS-WIDE ACCEPTANCE CONSEQUENCES marker, rstrip, one newline
  decision_rules_1387.txt  archive 1387: section "## A." before "## B.", only lines ^[0-9]+\.
  v4_findings_1390.txt     archive 1390: the same section-A numbered-line recipe
  v5_findings_1394.txt     the stage-1 bytes, bound as they stand
  v6_findings_1396.txt     archive 1396: the numbered findings, whose ids must be exactly the ids of
                           its frozen denominator (the two-space-indented id lines), each once;
                           whitespace collapsed, emitted as "N. <id> — <body>" in denominator order

A source whose hash differs, a marker that is absent, a finding whose id the denominator does not
name, a missing or repeated finding or denominator id, or an output whose byte count, newline
count or hash differs from its pin, refuses before anything is written. The runtime reads only this candidate.

    package_texts_recipe.py            build the five under experiments/harness_g1v3/ (fail closed)
    package_texts_recipe.py --verify   re-derive the five from inputs/ and compare with disk
"""
import io
import os
import re
import sys

from owners_recipe import OUT, Refused, _sha

R = os.path.dirname(os.path.abspath(__file__))
IN = os.path.join(R, "inputs", "package_texts")

#: output name -> (input file, input sha256, required bytes, required newlines, required sha256)
PINS = {
    "owner_rulings_1383.txt": ("archive_CODEX_1383.md", "5b84d789938b1dd3a43ebbfc95b95dda40882b96c6ddcb42dd3abacfe677e379", 3369, 14, "a925ba6ffce6ae14a47c942f5c660c626d13c1060910c2e79055680c7632dbca"),
    "decision_rules_1387.txt": ("archive_CODEX_1387.md", "a7ca92f36366393322a545aa9782bfcf7375240feb997b2f98e9dda71deac5ad", 3029, 10, "d5830182899461c7a34f3eed3f3cc374a40412618f9c80e2047f029c6a933fb2"),
    "v4_findings_1390.txt": ("archive_CODEX_1390.md", "3ee629ef65fa5a7573cb3a68f536e2e8694226550952fadf1c2a8838d79e0f28", 3279, 21, "0b669decd55e430fb86271378db177a0b1c2525eaa6ec6455dfbb22d7fdce6e0"),
    "v5_findings_1394.txt": ("stage1_v5_findings_1394.txt", "11a086123f4081be6561839527625ed42773faa800226520f6b7e01d6d98a1d1", 808, 4, "11a086123f4081be6561839527625ed42773faa800226520f6b7e01d6d98a1d1"),
    "v6_findings_1396.txt": ("archive_CODEX_1396.md", "db5859954b707a3b2ca6d3d57fd5db92091f64bc76f8a7625783d76164988685", 1557, 3, "b9842d7db6d3454587fc6bda25ec9bec41c3183832010b2a3f6d5189dda43ef3"),
}


def _between(t, start, end):
    lo = t.find(start)
    hi = t.find(end, lo + len(start)) if lo >= 0 else -1
    if lo < 0 or hi < 0:
        raise Refused("REFUSED: marker %r then %r not found in that order" % (start, end))
    return t[lo:hi]


def owner_rulings(b):
    t = b.decode("utf-8")
    return (_between(t, "OWNER RULINGS", "KNOWN CLASS-WIDE ACCEPTANCE CONSEQUENCES").rstrip() + "\n").encode("utf-8")


def numbered_section_a(b):
    keep = [l for l in _between(b.decode("utf-8"), "## A.", "## B.").split("\n") if re.match(r"^[0-9]+\. ", l)]
    return ("\n".join(keep) + "\n").encode("utf-8")


def v6_findings(b):
    t = b.decode("utf-8")
    order = re.findall(r"^  (\S+)$", t, re.M)
    found = {}
    for sid, body in re.findall(r"^[0-9]+\. (\S+) (.+?)(?=\n\n)", t, re.S | re.M):
        found.setdefault(sid, []).append(" ".join(body.split()))
    if not order or len(set(order)) != len(order) or set(found) != set(order) or any(len(v) != 1 for v in found.values()):
        raise Refused("REFUSED: the numbered findings %s and the denominator %s must be the same ids, each exactly once" % (sorted(found), order))
    return "".join("%d. %s — %s\n" % (i, sid, found[sid][0]) for i, sid in enumerate(order, 1)).encode("utf-8")


RECIPES = {
    "owner_rulings_1383.txt": owner_rulings,
    "decision_rules_1387.txt": numbered_section_a,
    "v4_findings_1390.txt": numbered_section_a,
    "v5_findings_1394.txt": lambda b: b,
    "v6_findings_1396.txt": v6_findings,
}


def derive(name):
    src, src_sha, size, newlines, out_sha = PINS[name]
    p = os.path.join(IN, src)
    if not os.path.isfile(p):
        raise Refused("REFUSED: recipe input missing: inputs/package_texts/%s" % src)
    b = io.open(p, "rb").read()
    if _sha(b) != src_sha:
        raise Refused("REFUSED: recipe input %s is %s, not %s" % (src, _sha(b)[:16], src_sha[:16]))
    out = RECIPES[name](b)
    if len(out) != size or out.count(b"\n") != newlines or _sha(out) != out_sha:
        raise Refused("REFUSED: %s recipe gives %d bytes, %d newlines, %s; pinned %d, %d, %s" % (name, len(out), out.count(b"\n"), _sha(out)[:16], size, newlines, out_sha[:16]))
    return out


def build():
    outs = {name: derive(name) for name in PINS}
    os.makedirs(OUT, exist_ok=True)
    for name, b in outs.items():
        io.open(os.path.join(OUT, name), "wb").write(b)
        print("TEXT %s %d bytes sha256 %s" % (name, len(b), _sha(b)))
    return 0


def verify():
    bad = []
    for name in PINS:
        p = os.path.join(OUT, name)
        if not os.path.isfile(p):
            bad.append("%s absent" % name)
        elif io.open(p, "rb").read() != derive(name):
            bad.append("%s differs from its recipe" % name)
    print("package text recipes: %s" % ("all five hold" if not bad else "; ".join(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(verify() if "--verify" in sys.argv[1:] else build())
