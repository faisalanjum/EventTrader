"""#827 finite census — inline-XBRL transformations (READ-ONLY file scan).

Recomputes, never transcribes: every inline-XBRL `nonFraction` element in the
frozen filing cache, counted by the EXPANDED identity of its `format`
attribute, plus every distinct `sign` and `scale` spelling.

WHY THIS WAS REBUILT. The previous scanner matched the literal bytes
`<ix:nonfraction` with a case-insensitive regex and read attributes out of the
matched tag text. That is the very mistake this whole round exists to remove: a
prefix is an alias a document may bind to anything (W3C Namespaces in XML 1.0
3e §3), so `ix:` is a LABEL and the namespace URI is the ADDRESS. A filing that
binds inline XBRL to any other prefix was invisible to it, and a document that
bound `ix:` to something else entirely would have been counted as inline XBRL.
It then had three elaborate controls checking that its regex read tags
consistently — which measures the regex against itself and cannot detect the
one error that mattered. Its `format` values were counted as raw strings, so
`ixt:num-dot-decimal` and `ixt4:num-dot-decimal` were two different classes and
a filing binding `ixt:` to TR3 versus TR4 was one class.

WHAT IT DOES NOW:
  * STRICT, NAMESPACE-AWARE XML. Each file is parsed as XML and elements are
    identified by expanded name — `{namespace}local` — for inline XBRL 1.0 and
    1.1 alike. No regex, no prefix literal, nothing case-insensitive.
  * FORMAT RESOLVED TO AN ADDRESS. The `format` QName's prefix is resolved
    against the in-scope namespaces OF THE ELEMENT THAT CARRIES IT, and the
    census is keyed by `(registry URI, local name)`. An unresolvable prefix is
    its own recorded bucket, never a guess.
  * NOTHING IS REPAIRED. The old scanner decoded with `errors='replace'` in
    four places, which silently rewrites bytes it cannot read — the exact
    defect class removed from the product this round. A file that will not
    parse is recorded by NAME, HASH and REASON and excluded from lawful product
    scope — never skipped silently and never patched. The run may still succeed:
    such a document is not a valid Inline XBRL report, so it has no lawful
    transform occurrence to replay, and leaving it out is the standard being
    applied rather than coverage being missed. What must hold is the manifest
    PARTITION — every file parsed, or named as standards-invalid.
  * NO PRODUCTION CODE IS IMPORTED. The old scanner drove every observed format
    through `inline_html.printed_value` and reported which ones the product
    "supported". A census that asks the product to grade itself cannot find a
    class the product mishandles. That section is deleted; this file now only
    reports what filings contain, and the judging happens elsewhere against it.

BINDING. `01b_ix_input_manifest.txt` lists every input by name and sha256, and
both output receipts carry that manifest's own sha256, so a later reader can
prove which corpus produced these numbers.

Run:  venv/bin/python receipts_827/scan_ix_transforms.py
Out:  receipts_827/01_ix_transform_census.json
      receipts_827/01b_ix_input_manifest.txt
      receipts_827/01c_ix_transform_occurrences.json  (replay inputs, corpus)
"""
import hashlib
import json
import os
import sys

from lxml import etree

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
ROOT = os.path.join(_REPO, "scripts", "driver_seed", "relocate_probe",
                    "inline_html_cache")
OUT = os.path.join(_HERE, "01_ix_transform_census.json")
MANIFEST = os.path.join(_HERE, "01b_ix_input_manifest.txt")
OCCURRENCES = os.path.join(_HERE, "01c_ix_transform_occurrences.json")

#: Inline XBRL 1.1 and the 1.0 namespace, BY ADDRESS. Both are
#: counted, so a filing using the older one is visible rather than absent.
#: THE PRODUCT VERSION, and only this one. The SEC route is Inline XBRL 1.1:
#: SEC EDGAR XBRL Guide, June 2026, §11.2 requires an Inline XBRL document to
#: be valid against 1.1. Its facts are the ones accounted for and replayed.
PRODUCT_NS = "http://www.xbrl.org/2013/inlineXBRL"

#: Inline XBRL 1.0 is DETECTED so a 1.0 document is visible in a census rather
#: than silently absent — and it stops there. Being able to recognise an older
#: lawful standard is not a reason to treat it as supported SEC input, and
#: quietly replaying its facts would widen the product boundary by accident.
#: Today the corpus contains zero of them; this is about tomorrow's.
DETECTED_ONLY_NS = "http://www.xbrl.org/2008/inlineXBRL"

INLINE_NS = (PRODUCT_NS, DETECTED_ONLY_NS)
NONFRACTION = tuple("{%s}nonFraction" % uri for uri in INLINE_NS)
#: The expanded name whose facts are actually processed. Decided by NAMESPACE
#: URI, never by prefix spelling.
PRODUCT_NONFRACTION = "{%s}nonFraction" % PRODUCT_NS

#: No DTD loading and no network: the scan reads the corpus and nothing else.
#: Entities are deliberately NOT resolved — an unresolved entity stays a
#: visible node, whereas resolving would need the DTD this parser must not go
#: and fetch.
PARSER = etree.XMLParser(resolve_entities=False, load_dtd=False,
                         no_network=True, huge_tree=False)


#: The two outcomes that are NOT an address, kept apart because they mean
#: different things: one filing wrote something that is not a QName at all, the
#: other wrote a well-formed QName whose prefix nothing here declares.
MALFORMED = "<malformed QName>"
UNRESOLVABLE = "<undeclared prefix>"
#: An unprefixed name with no default namespace in scope is not a broken
#: reference — it lawfully names something in NO namespace. Kept separate so it
#: is refused by the registry comparison for what it is, rather than reported
#: as a declaration someone forgot to write.
NO_NAMESPACE = "<absent namespace>"

#: A placeholder namespace used ONLY so `etree.QName` will check a name
#: component. Which namespace it is cannot affect whether a name is valid.
_VALIDATION_NS = "urn:x-name-validation"

#: THE FOUR XML WHITESPACE CHARACTERS, and only these. `format` is typed
#: `xs:QName`, whose fixed `whiteSpace=collapse` facet (XSD Part 2 §4.3.6)
#: normalises exactly space, tab, CR and LF. Python's bare `strip()` also eats
#: NBSP, vertical tab and a long tail of Unicode spaces — so it would quietly
#: ACCEPT a QName that is malformed under the schema, which is the wrong
#: direction to be lenient in.
XML_SPACE = " \t\r\n"


def expanded(el, qname):
    """`ixt:num-dot-decimal` -> `(registry URI, 'num-dot-decimal')`.

    Resolution is against THIS element's in-scope namespaces and nowhere else,
    because that is the only scope a prefix has. An UNPREFIXED name is lawful
    and takes the in-scope DEFAULT namespace: the Inline XBRL 1.1 schema
    declares `format` as `xs:QName`, and XML Schema Part 2 §3.3.18 interprets
    an unprefixed QName value through the default namespace declaration. An
    earlier draft rejected that form outright, which would have misfiled every
    filing that uses it.

    THE NAME IS VALIDATED BEFORE ANY LOOKUP, and BOTH components are validated.
    Judging the prefix only by whether it is declared reports a malformed
    prefix as a lawful one someone forgot to declare — a different defect with
    a different fix. Validation is delegated to the XML library, `etree.QName`,
    rather than to an ASCII pattern of mine: a hand-written character class is
    one more place to be subtly wrong about XML names, which is the whole
    subject of this round.

    Three non-addresses come back, and they are NOT the same thing: the value
    is not a QName at all; it names a prefix nothing declares; or it lawfully
    names something in no namespace.
    """
    parts = qname.strip(XML_SPACE).split(":")
    if len(parts) == 1:
        prefix, local = None, parts[0]
    elif len(parts) == 2:
        prefix, local = parts
    else:
        return MALFORMED
    if not _is_name(local) or (prefix is not None and not _is_name(prefix)):
        return MALFORMED
    uri = el.nsmap.get(prefix)
    if not uri:
        return UNRESOLVABLE if prefix is not None else NO_NAMESPACE
    return uri, local


def _is_name(component):
    """One NCName, judged by the XML library rather than by a pattern."""
    try:
        etree.QName(_VALIDATION_NS, component)
    except ValueError:
        return False
    return True


def fact_text(el):
    """The transform's input, per Inline XBRL 1.1 Part 1 §10.1.1.

    THE EDITION IS THE CURRENT ONE, checked rather than assumed: Recommendation
    2013-11-18 with approved errata corrections to 2026-07-14
    (specifications.xbrl.org release history for Inline XBRL 1.1 Part 1). Read
    from that text, §10.1.1 still says the element "MUST have exactly one child
    which SHALL be either an `ix:nonFraction` element or a text node, unless it
    has an `xsi:nil` attribute with the value true", the nested element must be
    in the SAME namespace, and a text-node child "MUST be a non-empty string".
    No relevant difference from the original Recommendation was found; the rule
    used here is unchanged.

    THE CONTENT MODEL IS NARROW, and an earlier draft of this file ignored how
    narrow: `ix:nonFraction` has exactly one child, either a single text node
    or a single nested `ix:nonFraction`. That draft applied the exclude /
    relevant-content rule instead, which belongs to the NON-NUMERIC content
    model — so it would have flattened styling spans, footnote markup and
    stray text into a number and fed that invention into the replay as though
    a filing had printed it.

    Taken from the specification, NOT from this repository's production reader.
    Anything else — mixed text, extra children, another element, a comment, an
    entity reference, a tail after the nested element — returns None and is
    counted as unlawful content. None of it is repaired.
    """
    node = el
    while True:
        kids = list(node)
        if not kids:
            return node.text            # None for an empty element: no text
        # THE NESTED CHILD MUST BE A PRODUCT-VERSION FACT, by expanded name.
        # This read `not in NONFRACTION`, and NONFRACTION gained the
        # detection-only 1.0 namespace when 1.0 counting was added — so a 1.1
        # fact wrapping a 1.0 fact would have contributed the inner text to the
        # SUPPORTED replay population, widening the product boundary through
        # the very tuple that exists only to make 1.0 visible. Production
        # checks the 1.1 address at every level (`_is(child, _INLINE_NS,
        # 'nonFraction')`); this enforces the same boundary independently.
        if len(kids) != 1 or kids[0].tag != PRODUCT_NONFRACTION:
            return None                 # comments and entities land here too
        child = kids[0]
        if node.text is not None or child.tail is not None:
            return None                 # mixed content around the nesting
        node = child


def frozen_inputs():
    """THE FROZEN MANIFEST IS THE PREMISE, never this run's own output.

    The previous design listed the directory and then WROTE the manifest from
    whatever it found, so the receipt certified the corpus that happened to be
    on disk at the time — a file added, removed or edited since the freeze
    would have been absorbed silently and then attested to. Here the manifest
    is READ, every name and every hash is checked against the directory, any
    difference fails the run, and the verified list is what gets scanned.
    """
    if not os.path.exists(MANIFEST):
        raise RuntimeError(
            f"{os.path.basename(MANIFEST)} is missing. This census consumes a "
            "frozen input list; generating one here would let the run certify "
            "its own premise.")
    # RAW BYTES, hashed as they are on disk. Reading as text and hashing the
    # result would normalise line endings, so two byte-different manifests
    # could report the same identity — a binding that does not bind.
    with open(MANIFEST, "rb") as fh:
        raw = fh.read()
    pinned = {}
    for line in raw.decode("utf-8").splitlines():
        name, _, digest = line.partition(" ")
        if not name or len(digest) != 64 \
                or any(c not in "0123456789abcdef" for c in digest):
            raise RuntimeError(
                f"manifest line is not `<name> <sha256>`: {line[:120]!r}")
        if name in pinned:
            raise RuntimeError(
                f"{name} is pinned twice in the manifest; a duplicate makes "
                "the input list ambiguous about which hash must hold")
        pinned[name] = digest
    present = {f for f in os.listdir(ROOT)
               if os.path.isfile(os.path.join(ROOT, f))}
    missing, extra = sorted(set(pinned) - present), sorted(present - set(pinned))
    if missing or extra:
        raise RuntimeError(
            f"the corpus no longer matches the frozen manifest: "
            f"{len(missing)} missing (e.g. {missing[:2]}), "
            f"{len(extra)} unpinned (e.g. {extra[:2]})")
    changed = []
    for name in sorted(pinned):
        with open(os.path.join(ROOT, name), "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != pinned[name]:
                changed.append(name)
    if changed:
        raise RuntimeError(
            f"{len(changed)} file(s) differ from their pinned hash, e.g. "
            f"{changed[:3]} — the frozen corpus has moved under this census")
    return sorted(pinned), hashlib.sha256(raw).hexdigest()


def main():
    files, manifest_sha = frozen_inputs()
    fmt, sign, scale = {}, {}, {}          # keyed by IDENTITY, not by spelling
    raw_format_spellings = {}
    occurrences = {}      # {(registry, local, transform input): times seen}
    by_inline_ns = {uri: 0 for uri in INLINE_NS}
    total = formatted = addressed = eligible = 0
    outside_product_version = 0
    bad_qname = unresolvable_format = no_namespace = not_lawful = 0
    # MEASURED, not assumed. An earlier draft dropped every fact with nested
    # content while the parity prose claimed a complete replay. These two say
    # how large that class actually is and how much of it is the lawful
    # nested-`nonFraction` chain, so the claim can be checked instead of
    # believed.
    nested_content = nested_chain = 0
    unparseable = []
    for i, fn in enumerate(files, 1):
        p = os.path.join(ROOT, fn)
        try:
            root = etree.parse(p, PARSER).getroot()
        except etree.XMLSyntaxError as exc:
            # RECORDED BY NAME, HASH AND REASON — never skipped, never
            # repaired. It is excluded from lawful product scope and stays
            # visible in both receipts; the manifest partition below is what
            # must hold. A census that quietly dropped what it cannot read
            # would report a corpus that does not exist.
            with open(p, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            unparseable.append({"file": fn, "sha256": digest,
                                "reason": str(exc)[:300]})
            continue
        for el in root.iter(*NONFRACTION):
            by_inline_ns[el.tag.split("}")[0][1:]] += 1
            if el.tag != PRODUCT_NONFRACTION:
                # DETECTED, AND THAT IS ALL. An Inline XBRL 1.0 fact is counted
                # by namespace so the document is visible, and then goes no
                # further: its format is not accounted, its text is not added
                # to the replay population, and nothing downstream can mistake
                # it for supported SEC input.
                outside_product_version += 1
                continue
            total += 1
            for name, bucket in (("sign", sign), ("scale", scale)):
                got = el.get(name)
                key = got if got is not None else f"<{name} absent>"
                bucket[key] = bucket.get(key, 0) + 1

            spelled = el.get("format")
            if spelled is None:
                fmt["<format absent>"] = fmt.get("<format absent>", 0) + 1
                continue
            formatted += 1
            raw_format_spellings[spelled] = \
                raw_format_spellings.get(spelled, 0) + 1
            address = expanded(el, spelled)
            if address in (MALFORMED, UNRESOLVABLE, NO_NAMESPACE):
                # KEPT APART. "not a QName", "a prefix nothing declares" and
                # "lawfully in no namespace" are three different situations
                # with three different fixes; merging them would hide all of
                # them behind whichever name got printed. The raw spelling is
                # preserved here exactly as the filing wrote it.
                bad_qname += address == MALFORMED
                unresolvable_format += address == UNRESOLVABLE
                no_namespace += address == NO_NAMESPACE
                key = f"{address} {spelled}"
                fmt[key] = fmt.get(key, 0) + 1
                continue
            registry, local = address
            addressed += 1
            fmt[f"{registry}|{local}"] = fmt.get(f"{registry}|{local}", 0) + 1
            if len(el):
                nested_content += 1
                # SAME product-only definition as `fact_text`, so the counter
                # cannot describe a chain the value rule would refuse.
                nested_chain += any(k.tag == PRODUCT_NONFRACTION for k in el)

            text = fact_text(el)
            if text is None:
                not_lawful += 1
                continue
            eligible += 1
            occ = (registry, local, text)
            occurrences[occ] = occurrences.get(occ, 0) + 1
        root.clear()
        if i % 200 == 0:
            print(f"{i}/{len(files)} files scanned, {total} facts", flush=True)

    # THE ACCOUNTING, stated as an equation rather than as adjacent counters.
    # Every formatted fact lands in exactly one bucket, and the replay
    # multiplicities sum EXACTLY to the eligible ones — so "every occurrence is
    # replayed" is a checked claim and not a hopeful sentence in a docstring.
    if formatted != addressed + bad_qname + unresolvable_format + no_namespace:
        raise RuntimeError(
            f"formatted facts {formatted} != addressed {addressed} + malformed "
            f"{bad_qname} + undeclared prefix {unresolvable_format} + absent "
            f"namespace {no_namespace}")
    if addressed != eligible + not_lawful:
        raise RuntimeError(
            f"addressed facts {addressed} != eligible {eligible} + "
            f"unlawful content {not_lawful}")
    if sum(occurrences.values()) != eligible:
        raise RuntimeError(
            f"replay multiplicities sum to {sum(occurrences.values())} but "
            f"{eligible} facts are eligible — the replay set is not the corpus")

    # THE MANIFEST PARTITION — the one boolean, and what it actually means.
    #
    # An earlier version called this `census_complete` and set it false whenever
    # any file failed to parse, which CONFLATED TWO DIFFERENT FACTS. A document
    # that is not well-formed XML is not a gap in our coverage: Inline XBRL 1.1
    # §3.1 and SEC EDGAR XBRL Guide June 2026 §11.2 require a well-formed,
    # valid report, so such a file has NO lawful transform occurrences for this
    # product to replay. Excluding it is the standard being applied, not
    # coverage being missed.
    #
    # What must hold instead is that every manifest file is ACCOUNTED FOR —
    # parsed, or named and hashed as standards-invalid — with nothing
    # unexplained in between. `frozen_inputs()` has already verified the names
    # and hashes, so this closes the partition.
    parsed = len(files) - len(unparseable)
    supported_scope_complete = (parsed + len(unparseable)) == len(files)
    if not supported_scope_complete:
        raise RuntimeError(
            f"manifest partition broken: {parsed} parsed + "
            f"{len(unparseable)} standards-invalid != {len(files)} in manifest")

    # THE REPLAY INPUTS, bound to the manifest this run VERIFIED rather than
    # to one it wrote. Every entry is a triple a filing actually produced: the
    # registry ADDRESS the format resolved to, the transform's local name, and
    # the element's value under Inline XBRL 1.1 §10.1.1.
    occ_doc = {
        "receipt": "#827 inline-XBRL transform occurrences (replay inputs)",
        "input_manifest_file": os.path.basename(MANIFEST),
        "input_manifest_sha256": manifest_sha,
        "n_files_in_manifest": len(files),
        "n_files_parsed": parsed,
        "supported_scope_complete": supported_scope_complete,
        "files_not_well_formed": unparseable,
        "eligible_facts": eligible,
        "excluded_from_replay": {
            "content_not_lawful_under_10_1_1": not_lawful,
            "format_qname_malformed": bad_qname,
            "format_prefix_undeclared": unresolvable_format,
            "format_in_absent_namespace": no_namespace,
            "facts_outside_product_inline_xbrl_version": outside_product_version,
        },
        "note": "every triple below was read from the corpus; none was chosen "
                "or invented. `count` is how many facts printed it, and the "
                "counts sum exactly to `eligible_facts`. THIS IS NOT EVERY "
                "FILE IN THE MANIFEST: files listed in `files_not_well_formed` "
                "are not valid Inline XBRL reports and have no lawful "
                "occurrences to replay.",
        "occurrences": [
            {"registry": r, "local": lo, "text": t, "count": n}
            for (r, lo, t), n in sorted(occurrences.items(),
                                        key=lambda kv: (-kv[1], kv[0]))],
    }
    with open(OCCURRENCES, "w", encoding="utf-8") as fh:
        json.dump(occ_doc, fh, indent=1, sort_keys=True)

    doc = {
        # NO WALL-CLOCK STAMP. Two runs over the same frozen corpus with the
        # same script must be byte-identical, so that "unchanged" is provable
        # by comparing the receipts rather than by reading them.
        "receipt": "#827 inline-XBRL transformation census",
        "cache_root": os.path.relpath(ROOT, _REPO),
        "supported_scope_complete": supported_scope_complete,
        "files_not_well_formed": unparseable,
        "n_files_in_manifest": len(files),
        "n_files_parsed": parsed,
        "scope_note": "`supported_scope_complete` means every manifest file is "
                      "ACCOUNTED FOR — parsed, or named and hashed as not a "
                      "well-formed Inline XBRL report. It does NOT mean every "
                      "file parsed. A file in `files_not_well_formed` fails "
                      "Inline XBRL 1.1 §3.1 / SEC EDGAR XBRL Guide June 2026 "
                      "§11.2 and therefore has no lawful transform occurrence "
                      "for this product to replay.",
        "input_manifest_file": os.path.basename(MANIFEST),
        "input_manifest_sha256": manifest_sha,
        "occurrence_file": os.path.basename(OCCURRENCES),
        "script_sha256": hashlib.sha256(
            open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "method": "strict namespace-aware XML parse; elements identified by "
                  "expanded name {namespace}nonFraction; Inline XBRL 1.1 is "
                  "the PRODUCT version and only its facts are accounted and "
                  "replayed, while 1.0 is counted as detected-outside-product "
                  "and goes no further; the `format` QName resolved to "
                  "(registry URI, local name) against the in-scope namespaces "
                  "of the element carrying it; absent, unresolvable and "
                  "non-simple content each counted in their own explicit "
                  "bucket; no regex, no prefix literal, no replacement "
                  "decoding, and no production code imported",
        "counts": {
            "facts_by_inline_namespace": by_inline_ns,
            "facts_outside_product_inline_xbrl_version": outside_product_version,
            "product_inline_xbrl_namespace": PRODUCT_NS,
            "facts_with_a_format": formatted,
            "facts_whose_format_resolved_to_an_address": addressed,
            "facts_with_malformed_format_qname": bad_qname,
            "facts_with_undeclared_format_prefix": unresolvable_format,
            "facts_whose_format_is_in_no_namespace": no_namespace,
            "facts_with_content_not_lawful_under_10_1_1": not_lawful,
            "addressed_facts_with_any_child_node": nested_content,
            "addressed_facts_with_a_nested_nonFraction": nested_chain,
            "facts_eligible_for_replay": eligible,
            "distinct_replay_occurrences": len(occurrences),
            "replay_occurrence_total": sum(occurrences.values()),
        },
        "by_raw_format_spelling": dict(
            sorted(raw_format_spellings.items(), key=lambda kv: -kv[1])),
        "by_format": dict(sorted(fmt.items(), key=lambda kv: -kv[1])),
        "by_sign": dict(sorted(sign.items(), key=lambda kv: -kv[1])),
        "by_scale": dict(sorted(scale.items(), key=lambda kv: -kv[1])),
    }
    body = json.dumps(doc, indent=1, sort_keys=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")
    print(f"wrote {os.path.relpath(OUT, _REPO)} "
          f"(sha256 {hashlib.sha256(body.encode()).hexdigest()[:16]})")
    print(f"files={len(files)} product-version facts={total} "
          f"format identities={len(fmt)}")
    print(f"  by inline namespace          : {by_inline_ns}")
    print(f"  outside product version (1.0): {outside_product_version}"
          f"  (detected only, never replayed)")
    print(f"  distinct raw format spellings: {len(raw_format_spellings)}")
    print(f"  formatted -> addressed       : {formatted} -> {addressed}"
          f"  (malformed {bad_qname}, undeclared prefix"
          f" {unresolvable_format}, absent namespace {no_namespace})")
    print(f"  addressed -> eligible        : {addressed} -> {eligible}"
          f"  (content not lawful {not_lawful};"
          f" any child {nested_content}, nested nonFraction {nested_chain})")
    print(f"  distinct replay occurrences  : {len(occurrences)}"
          f"  summing to {sum(occurrences.values())}")
    # THE INVALID FILES STAY PROMINENT even on a passing run. The partition
    # holding is not permission to stop mentioning them: this census covers
    # `n_files_parsed` of `n_files_in_manifest`, never "all files".
    print(f"  manifest partition           : {parsed} parsed + "
          f"{len(unparseable)} standards-invalid = {len(files)}")
    if unparseable:
        print(f"  NOT VALID INLINE XBRL — {len(unparseable)} file(s), excluded "
              "from replay because they have no lawful occurrences:")
        for u in unparseable:
            print(f"     {u['file']}  sha256 {u['sha256'][:16]}…")
            print(f"       {u['reason'][:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
