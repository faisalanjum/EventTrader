"""#827 round 9 — what the TWO-VIEW parser does to the whole frozen cache.

MANIFEST-BOUND, HARD-FAILING, READ-ONLY. Every input is named and hash-checked
against `01b_ix_input_manifest.txt` before it is read, and ANY missing file or
hash mismatch ABORTS the run — a census that quietly skips its own inputs is
not a census. Nothing is written outside this receipts directory.

THREE INDEPENDENT QUESTIONS, and each is answered by something other than the
code under test:

1. IS THE DOCUMENT READABLE?  Answered by lxml directly, with the same strict
   settings the parser uses but WITHOUT importing it. The production module
   never gets to certify its own readability verdict.

2. WHAT DOES A REFUSAL COST?  Counted namespace-aware, as `{ix}nonFraction`
   elements — never by searching for the string `ix:nonFraction`, which is the
   literal-prefix rule this whole round exists to remove. A document that is not
   well-formed CANNOT be counted this way, by definition, so for those the
   number is not guessed: the limit is named.

   SCOPED, ON PURPOSE, TO THE 2013 INLINE XBRL NAMESPACE. That is the one the
   parser consumes today. Whether the earlier official namespaces must also be
   recognised is a STANDARDS question — it has to be answered from the official
   specification list, never from whatever this corpus happens to contain — and
   it is a later stage. This count is therefore the 2013 population, said so
   here rather than presented as "all inline facts".

3. IS THE RENDERED REPRESENTATION UNCHANGED?  Compared against a REAL
   before-state: the renderer walk as it stands in the FROZEN STAGED TREE that
   round 7b certified, extracted from git and executed here. Not HEAD — HEAD's
   renderer is a different one, so a comparison against it would prove
   no-regression against a version this work never started from.
"""
import hashlib
import json
import os
import subprocess
import sys
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from lxml import etree

# The ONE expected warning, and only it: bs4 notices XML-looking input handed to
# its HTML parser, which is exactly what the renderer view does on purpose.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, _REPO)

ROOT = os.path.join(_REPO, "scripts", "driver_seed", "relocate_probe",
                    "inline_html_cache")
MANIFEST = os.path.join(_HERE, "01b_ix_input_manifest.txt")
OUT = os.path.join(_HERE, "16_two_view_census.json")

IX = "http://www.xbrl.org/2013/inlineXBRL"


class CensusAborted(Exception):
    """The population is not the one this census claims to cover."""


def manifest_rows():
    """The pinned population, or abort.

    THE MANIFEST IS CHECKED BEFORE IT IS TRUSTED. A duplicate row would count a
    filing twice, a malformed row would silently drop one, and an extra file in
    the cache that no row names would sit outside the scope every earlier round
    measured. None of that is visible in the output afterwards, so it is refused
    here rather than reported later.
    """
    lines = [ln for ln in open(MANIFEST, encoding="utf-8").read().split("\n")
             if ln.strip()]
    rows = [ln.split() for ln in lines]
    if any(len(r) != 2 for r in rows):
        raise CensusAborted("a manifest row is not exactly (name, sha256)")
    names = [r[0] for r in rows]
    if len(set(names)) != len(names):
        raise CensusAborted("the manifest names a file more than once")
    if any(len(r[1]) != 64 or r[1].strip("0123456789abcdef") for r in rows):
        raise CensusAborted("a manifest row does not carry a sha256")
    on_disk = {f for f in os.listdir(ROOT)
               if os.path.isfile(os.path.join(ROOT, f))}
    if set(names) != on_disk:
        raise CensusAborted(
            "the manifest is not the exact frozen scope: "
            f"{len(set(names) - on_disk)} named but absent, "
            f"{len(on_disk - set(names))} present but unnamed")
    return rows


#: THE BASELINE IS THE FROZEN STAGED TREE, not HEAD. They are not the same
#: renderer: `_visible_walk` and `_soup` both differ between them, so comparing
#: against HEAD would prove no-regression against a version this work never
#: started from. This is the exact tree the round-7b gate certified.
FROZEN_TREE = "28a42377e51b844961c268e5ad6c13b1c5c33f02"


def before_state():
    """The frozen tree's renderer walk, loaded from git — the certified BEFORE.

    Loaded as SOURCE TEXT out of the tree object, not imported from the working
    tree, so it cannot pick up any of this round's edits. Only the three
    definitions the representation depends on are taken; nothing else in that
    file would run, because its own imports no longer exist.
    """
    src = subprocess.run(["git", "-C", _REPO, "show",
                          f"{FROZEN_TREE}:driver/relocation/inline_html.py"],
                         capture_output=True, text=True, check=True).stdout
    wanted, out, keep = ("def _hidden_cell(", "def _visible_walk("), [], False
    for block in src.split("\n\n\n"):
        if block.lstrip().startswith(wanted):
            keep = True
        if keep and (block.lstrip().startswith(wanted)
                     or block.lstrip().startswith("_SPAN_TAGS")):
            out.append(block)
    ns = {"re": __import__("re")}
    exec("\n\n\n".join(out), ns)                     # noqa: S102 - pinned source
    return ns["_visible_walk"], hashlib.sha256(
        "\n\n\n".join(out).encode()).hexdigest()


def main():
    baseline_walk, baseline_sha = before_state()
    from driver.relocation import inline_html as IH   # the AFTER, under test

    rows = manifest_rows()
    readable = refused = 0
    reasons, refused_files, unchanged, changed = {}, [], 0, []
    facts_readable = 0

    strict = etree.XMLParser(recover=False, resolve_entities=False,
                             load_dtd=False, no_network=True)
    for name, want_sha in rows:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            raise CensusAborted(f"manifest names a file that is not there: {name}")
        raw = open(path, "rb").read()
        got = hashlib.sha256(raw).hexdigest()
        if got != want_sha:
            raise CensusAborted(
                f"{name}: frozen cache drifted — pinned {want_sha}, found {got}")
        text = raw.decode("utf-8", "surrogateescape")

        # (1) READABILITY, decided independently of the module under test.
        try:
            root = etree.fromstring(text.encode("utf-8", "surrogatepass"), strict)
        except etree.XMLSyntaxError as exc:
            refused += 1
            kind = str(exc).split(",")[0]
            reasons[kind] = reasons.get(kind, 0) + 1
            refused_files.append({
                "file": name, "lxml_diagnosis": kind,
                "facts_lost": "NOT DERIVABLE — a document that is not "
                              "well-formed cannot be counted namespace-aware, "
                              "and a text search for a prefix is the very rule "
                              "this round removes"})
            continue
        readable += 1
        # (2) THE COST, namespace-aware.
        facts_readable += sum(1 for _ in root.iter("{%s}nonFraction" % IX))

        # (3) THE REPRESENTATION, against the real before-state.
        before = baseline_walk(BeautifulSoup(text, "lxml"))
        after = IH.prepare(text)["text"]
        if before == after:
            unchanged += 1
        else:
            changed.append({"file": name,
                            "before_len": len(before), "after_len": len(after)})

    out = {
        "population": {
            "manifest": os.path.relpath(MANIFEST, _REPO),
            "manifest_sha256": hashlib.sha256(
                open(MANIFEST, "rb").read()).hexdigest(),
            "cache_root": os.path.relpath(ROOT, _REPO),
            "documents": len(rows),
            "every_input_hash_verified": True},
        "readability_decided_by": "lxml directly (recover=False), NOT the "
                                  "module under test",
        "fact_counting_scope": "the 2013 Inline XBRL namespace only "
                               f"({IX}); earlier official namespaces are a "
                               "later standards-derived stage",
        "readable": readable,
        "refused": refused,
        "refusal_reasons": reasons,
        "refused_files": refused_files,
        "ix_nonFraction_elements_in_readable_documents": facts_readable,
        "representation": {
            "before_state": f"{FROZEN_TREE}:driver/relocation/inline_html.py"
                            " _visible_walk + _hidden_cell + _SPAN_TAGS",
            "before_state_source_sha256": baseline_sha,
            "identical": unchanged,
            "differs": len(changed),
            "differing_files": changed},
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
