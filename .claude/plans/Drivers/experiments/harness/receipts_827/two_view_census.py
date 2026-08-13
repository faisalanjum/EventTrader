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
import re
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


#: EU-094 is measured through the REAL section-selection decision, never through
#: a proxy. Counting "word-bearing cells" would answer a question the production
#: code does not ask: the real decision at inline_html.py:3098-3135 also depends
#: on prior rows carrying a real fact, direct cells, visible slices,
#: `_has_number_fact`, first-cell text, the EXACTLY-ONE-eligible-cell rule,
#: parentheses, and reverse scan/break order.
#:
#: AND THE FILTER IS NOT MONOTONE, so a one-sided count would be wrong in
#: principle. The frozen test test_row_label_span.py:134-142 shows the digit
#: filter CAUSING an acceptance: in "Q1 2023 | Segment detail" it removes the
#: digit cell, leaving EXACTLY ONE eligible cell, and the section is accepted —
#: without the filter there are two candidates and no section at all. So the
#: counterfactual is run in full and every outcome class is reported separately.
_CF_ANCHOR = "if _words(t) and not re.search(r'\\d', t)]"
_CF_REPLACE = "if _words(t)]"


def _section_evidence(ev):
    """The EXACT section evidence pair: (text, normalized span).

    The production decision at inline_html.py:3135 is the PAIR, not the words.
    If the same words appear in two cells and the digit rule changes WHICH cell
    is selected, comparing text alone would call that UNCHANGED while the source
    attribution actually moved — the exact failure class this area already hit
    (test_row_label_span.py::test_section_TEXT_and_SPAN_come_from_the_SAME_cell).
    Absent evidence is the exact empty pair, never a bare falsy value.
    """
    ev = ev or {}
    span = ev.get("section_span")
    return (ev.get("section") or "",
            tuple(span) if isinstance(span, (list, tuple)) else ())


def counterfactual_module():
    """The live module with ONLY the digit filter removed, imported under its
    own name. Production is never written; the source is copied and mutated in a
    temp directory. A missing or ambiguous anchor ABORTS — a counterfactual that
    silently failed to remove the rule would report a false 'no difference'."""
    import importlib.util
    import tempfile
    src_path = os.path.join(_REPO, "driver", "relocation", "inline_html.py")
    src = open(src_path, encoding="utf-8").read()
    if src.count(_CF_ANCHOR) != 1:
        raise CensusAborted(
            f"the digit-filter anchor appears {src.count(_CF_ANCHOR)}x in "
            "inline_html.py — the counterfactual cannot be built unambiguously")
    tmp = tempfile.mkdtemp(prefix="eu094_cf_")
    path = os.path.join(tmp, "inline_html_no_digit_filter.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(_CF_ANCHOR, _CF_REPLACE, 1))
    spec = importlib.util.spec_from_file_location("inline_html_cf", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, hashlib.sha256(src.encode()).hexdigest()


def eu094_counterfactual(name, text, IH, CF, tally):
    """Compare the REAL section outcome per fact, live vs no-digit-filter.

    BOTH FACT POPULATIONS ARE THE DENOMINATOR. `prepare()` splits facts into
    `elements` (ID-bearing, keyed by the collapsed xs:NCName) and
    `noid_elements` (null-graph-id facts, a list), and BOTH reach
    `_evidence_from` — the ID-less ones through the fallback/identity path. A
    census over `elements` alone would report a denominator that is not the real
    decision's.

    ID-bearing facts are aligned by EXACT KEY and ID-less facts by their stable
    bridge/source order, with the keys and counts asserted equal BEFORE any
    comparison. The mutation removes one filter inside section selection and
    cannot change which facts exist, so a population that does not line up means
    the counterfactual is not the same document: that ABORTS the census rather
    than being quietly counted and excluded.
    """
    live, cf = IH.prepare(text), CF.prepare(text)
    live_ref, cf_ref = IH.refused(live), CF.refused(cf)
    if live_ref or cf_ref:
        if bool(live_ref) != bool(cf_ref):
            raise CensusAborted(
                f"{name}: the digit-filter mutation changed DOCUMENT refusal "
                f"(live={live_ref!r}, counterfactual={cf_ref!r}) — impossible "
                "for this mutation, so the census is not comparing one document")
        tally["documents_refused"] += 1
        tally["refusal_reasons"][str(live_ref)] = \
            tally["refusal_reasons"].get(str(live_ref), 0) + 1
        return

    live_el, cf_el = live.get("elements", {}), cf.get("elements", {})
    if set(live_el) != set(cf_el):
        raise CensusAborted(
            f"{name}: ID-bearing fact keys differ under a one-line mutation — "
            f"{len(set(live_el) - set(cf_el))} only-live, "
            f"{len(set(cf_el) - set(live_el))} only-counterfactual")
    live_noid, cf_noid = live.get("noid_elements", []), cf.get("noid_elements", [])
    if len(live_noid) != len(cf_noid):
        raise CensusAborted(
            f"{name}: ID-less fact COUNT differs under a one-line mutation — "
            f"live {len(live_noid)} vs counterfactual {len(cf_noid)}")

    pairs = [(k, live_el[k], cf_el[k], "id") for k in sorted(live_el)]
    pairs += [(f"noid#{i}", a, b, "noid")
              for i, (a, b) in enumerate(zip(live_noid, cf_noid))]
    tally["id_bearing_facts"] += len(live_el)
    tally["idless_facts"] += len(live_noid)
    for key, a_el, b_el, kind in pairs:
        tally["facts_compared"] += 1
        a_txt, a_span = _section_evidence(IH._evidence_from(a_el, live)[0])
        b_txt, b_span = _section_evidence(CF._evidence_from(b_el, cf)[0])
        if (a_txt, a_span) == (b_txt, b_span):
            tally["unchanged"] += 1
        elif a_txt and not b_txt:
            tally["current_only_accepted"] += 1     # the FILTER caused acceptance
            if len(tally["current_only_examples"]) < 20:
                tally["current_only_examples"].append(
                    {"document": name, "fact": key, "kind": kind,
                     "section": a_txt, "span": a_span})
        elif b_txt and not a_txt:
            tally["counterfactual_only_accepted_withheld"] += 1
            if len(tally["withheld_examples"]) < 20:
                tally["withheld_examples"].append(
                    {"document": name, "fact": key, "kind": kind,
                     "section": b_txt, "span": b_span})
        else:
            # SAME WORDS, DIFFERENT CELL counts here too: the pair differs even
            # when the text matches, which is the source-attribution change a
            # text-only comparison would have reported as UNCHANGED.
            tally["changed_section"] += 1
            if len(tally["changed_examples"]) < 20:
                tally["changed_examples"].append(
                    {"document": name, "fact": key, "kind": kind,
                     "current": a_txt, "current_span": a_span,
                     "counterfactual": b_txt, "counterfactual_span": b_span,
                     "same_text_different_cell": a_txt == b_txt})


def recall_populations(soup, IH):
    """B-18 — the TWO recall costs behind the two separately-dispositioned
    regex sites, measured over the same manifest-bound corpus.

    They are counted SEPARATELY and never merged: they are different questions
    over different populations, and one of them was previously recorded as
    UNKNOWN. Nothing here is copied from the source comments — those name the
    numbers as leads; these are the measurement.

    EU-150 (`_words`, the ASCII label-word rule): over text-bearing td/th cells,
      how many carry letters the rule cannot see AT ALL (withheld), versus
      letters it sees (accepted), versus mixed cells that survive through their
      ASCII words.
    EU-094 is NOT measured here: a cell-level proxy is not the production
    population. It is measured through the real section decision by
    eu094_counterfactual().
    """
    eu150 = {"text_bearing_cells": 0, "accepted_rule_sees_words": 0,
             "withheld_letters_rule_cannot_see": 0,
             "accepted_mixed_survives_via_ascii": 0}
    for cell in soup.find_all(["td", "th"]):
        text = cell.get_text()
        if not text.strip():
            continue
        eu150["text_bearing_cells"] += 1
        words = IH._words(text)
        if words:
            eu150["accepted_rule_sees_words"] += 1
            if any(c.isalpha() and not c.isascii() for c in text):
                eu150["accepted_mixed_survives_via_ascii"] += 1
        elif any(c.isalpha() for c in text):
            eu150["withheld_letters_rule_cannot_see"] += 1
    return eu150


def main():
    baseline_walk, baseline_sha = before_state()
    from driver.relocation import inline_html as IH   # the AFTER, under test

    rows = manifest_rows()
    readable = refused = 0
    eu150_tot = {"text_bearing_cells": 0, "accepted_rule_sees_words": 0,
                 "withheld_letters_rule_cannot_see": 0,
                 "accepted_mixed_survives_via_ascii": 0}
    CF, live_src_sha = counterfactual_module()
    eu094 = {"id_bearing_facts": 0, "idless_facts": 0, "facts_compared": 0,
             "unchanged": 0, "current_only_accepted": 0,
             "counterfactual_only_accepted_withheld": 0, "changed_section": 0,
             "documents_refused": 0, "refusal_reasons": {},
             "current_only_examples": [], "withheld_examples": [],
             "changed_examples": []}
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
        soup = BeautifulSoup(text, "lxml")     # ONE parse, reused by both
        for k, v in recall_populations(soup, IH).items():
            eu150_tot[k] += v
        eu094_counterfactual(name, text, IH, CF, eu094)
        before = baseline_walk(soup)
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
        "recall_cost_two_separate_populations": {
            "measured_over": "the readable documents of the same manifest-bound "
                             "corpus; the source-comment numbers are LEADS, "
                             "never evidence — these are the measurement",
            "EU-150_ascii_label_word_rule": dict(
                eu150_tot,
                withheld_share_of_text_bearing_cells=(
                    eu150_tot["withheld_letters_rule_cannot_see"]
                    / eu150_tot["text_bearing_cells"]
                    if eu150_tot["text_bearing_cells"] else None),
                direction="SELECTION-SIDE: the rule decides eligibility, never "
                          "stored text, so its worst error WITHHOLDS"),
            "EU-094_digit_heading_probe": dict(
                eu094,
                denominator_check={
                    "id_bearing_plus_idless": (eu094["id_bearing_facts"]
                                               + eu094["idless_facts"]),
                    "facts_compared": eu094["facts_compared"],
                    "outcomes_sum": (eu094["unchanged"]
                                     + eu094["current_only_accepted"]
                                     + eu094["counterfactual_only_accepted_withheld"]
                                     + eu094["changed_section"]),
                    "both_populations_covered": "elements + noid_elements"},
                measured_through="the REAL section-selection decision, live vs "
                                 "the same module with ONLY the digit filter "
                                 "removed — not a cell-level proxy",
                live_source_sha256=live_src_sha,
                denominator="facts_compared",
                fail_closed_premise=(
                    "DISPROVED" if (eu094["current_only_accepted"]
                                    or eu094["changed_section"])
                    else "not contradicted by this corpus"),
                note="the source comment claims withhold-only; the frozen test "
                     "test_row_label_span.py:134-142 shows the filter CAUSING "
                     "an acceptance, so the direction is measured, not asserted"),
        },
        "representation": {
            "before_state": f"{FROZEN_TREE}:driver/relocation/inline_html.py"
                            " _visible_walk + _hidden_cell + _SPAN_TAGS",
            "before_state_source_sha256": baseline_sha,
            "identical": unchanged,
            "differs": len(changed),
            "differing_files": changed},
    }
    _sub = eu094["id_bearing_facts"] + eu094["idless_facts"]
    _out = (eu094["unchanged"] + eu094["current_only_accepted"]
            + eu094["counterfactual_only_accepted_withheld"]
            + eu094["changed_section"])
    if not (_sub == eu094["facts_compared"] == _out):
        raise CensusAborted(
            "EU-094 denominator does not close: id+noid=%d, compared=%d, "
            "outcomes=%d" % (_sub, eu094["facts_compared"], _out))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
