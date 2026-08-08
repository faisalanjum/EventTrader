"""#827 finding 2 — the filing DATE/dateTime/timezone inventory (READ-ONLY).

Required before the strict dateUnion parser is written: what lexical forms do
the real filings actually use? Scans every cached filing for the period
children of the XBRL INSTANCE NAMESPACE — startDate / endDate / instant,
resolved by (namespace URI, local name), never by a prefix — and classifies
each raw value:
date-only vs dateTime, timezone absent / Z / +hh:mm / -hh:mm, and any value
that is neither. Explicit raises; nothing is inferred or repaired.

Out: receipts_827/09_filing_date_inventory.json
"""
import collections, datetime, hashlib, json, os, re, sys

from lxml import etree

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
ROOT = os.path.join(_REPO, "scripts", "driver_seed", "relocate_probe",
                    "inline_html_cache")
OUT = os.path.join(_HERE, "09_filing_date_inventory.json")

#: XBRL 2.1 §4.7.2 — the period children this census inventories, named by the
#: instance NAMESPACE and local name. The URI is the fixed standard value
#: (XBRL 2.1 Recommendation 2003-12-31 + corrected errata 2013-02-20); the
#: prefix a filing chooses is an alias and carries no identity.
_INSTANCE_NS = "http://www.xbrl.org/2003/instance"
PERIOD_LOCALS = ("startDate", "endDate", "instant")

# THE OLD SCAN WAS THE DEFECT IT EXISTS TO MEASURE. It was a raw-bytes regex
# `<xbrli:(startDate|endDate|instant)>` with re.I — three separate errors in one
# line: it matched a PREFIX rather than a namespace, so a filing that lawfully
# binds the instance namespace to any other prefix contributed NOTHING to the
# inventory and one that bound `xbrli:` to a different namespace was counted as
# if it were XBRL; and `re.I` made the match case-insensitive, which XML names
# never are. A census that cannot see a lawful filing cannot bound the parser
# it exists to bound.
#
# It now resolves names the way XML defines them, through a namespace-aware
# parse — and deliberately through `lxml.etree` DIRECTLY, not through the
# production reader. The independence is the whole point of this file: a census
# that borrowed production's parser could only ever prove that parser agrees
# with itself. Entities and network are disabled; nothing is repaired.
def _period_values(blob):
    """Every (local name, raw text) period value, or a refusal reason.

    Returns (values, reason). `reason` is None when the document is readable.

    `recover=False` IS NOT BY ITSELF A PROOF OF ENCODING CONFORMANCE. XML 1.0
    5e section 4.3.3 makes it a FATAL error for an entity to contain bytes that
    are not legal in its declared encoding, and that is not the same question a
    well-formedness parse answers. So the declared encoding is enforced here
    separately, with Python's own standard codec in strict mode — a library
    decoder applied to the parser's own reported encoding, not a second
    handmade XML or namespace validator, and it adds no grammar of its own.

    IT IS A GENERAL GUARD, NOT A RESPONSE TO A KNOWN FAILURE, and the record is
    corrected here because an earlier round of this audit said otherwise. NO
    filing in this corpus violates its declared encoding: the check refuses
    zero of 1,769. In particular the 41 filings whose renderer text differs
    from their XML text do NOT belong to it — they are all-ASCII bytes carrying
    the ASCII character reference `&#153;`, which XML 1.0 5e sections 2.2 and
    4.1 make a lawful reference to U+0099, while the HTML Living Standard's
    numeric-character-reference replacement table maps decimal 153 to U+2122.
    Both parsers are correct; that is a standards-defined difference between a
    renderer view and a semantic view, not malformed input.
    """
    parser = etree.XMLParser(resolve_entities=False, no_network=True,
                             load_dtd=False, huge_tree=True, recover=False)
    try:
        tree = etree.fromstring(blob, parser).getroottree()
    except Exception as exc:                       # noqa: BLE001 - census
        return [], "not_wellformed_xml: " + str(exc)[:160]
    declared = tree.docinfo.encoding
    if declared:
        try:
            blob.decode(declared, errors="strict")
        except (UnicodeDecodeError, LookupError) as exc:
            return [], (f"bytes_illegal_in_declared_encoding {declared!r} "
                        f"(XML 1.0 5e 4.3.3): {exc}"[:200])
    root = tree.getroot()
    out = []
    for local in PERIOD_LOCALS:
        for el in root.iter("{%s}%s" % (_INSTANCE_NS, local)):
            out.append((local, el.text if el.text is not None else ""))
    return out, None


# ASCII ONLY, and XML whitespace ONLY. The first version used `\d` (which
# matches every Unicode decimal digit) and `str.strip()` (which strips NBSP and
# the whole Unicode space family) — so full-width `２０２３-０６-３０` and
# NBSP-padded values were counted as LAWFUL date-only. That is the very defect
# this census exists to measure, committed by the census itself.
# THE COMPLETE XSD GRAMMAR, written INDEPENDENTLY of the production parser.
# The independence is the point: this census exists to BOUND that parser, so
# importing it would only prove the parser agrees with itself. A cross-check
# test asserts the two implementations agree on legality — that is what keeps
# two deliberate copies honest.
#
# Four defects the first version had, all reproduced by the reviewer:
#   * `[0-9]{4,}` accepted `02023` — a >4-digit year may NOT have a leading
#     zero (XML Schema 1.0 §3.2.7, "no leading zeros" beyond the four-digit
#     minimum).
#   * `[+-][0-9]{2}:[0-9]{2}` accepted `+15:00`, `+14:01` and `+05:60` — the
#     lawful range is exactly -14:00..+14:00 with minutes 00-59.
#   * an `xs:date` MAY carry a timezone; requiring `T` to have one classified
#     lawful `2023-06-30Z` as non-conforming.
_YEAR = r"-?(?:[1-9][0-9]{3,}|0[0-9]{3})"
_TZ = r"(?:Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))"
DATE_ONLY = re.compile(rf"{_YEAR}-[0-9]{{2}}-[0-9]{{2}}({_TZ})?")
DATETIME = re.compile(rf"{_YEAR}-[0-9]{{2}}-[0-9]{{2}}"
                      rf"T[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}(\.[0-9]+)?"
                      rf"({_TZ})?")
TZ = re.compile(rf"({_TZ})$")
XML_WS = " \t\r\n"


def _days_in_month(year_mod_400, month):
    """Proleptic Gregorian month length — pure arithmetic, so the check does not
    depend on what `datetime` happens to represent.

    Takes the year MODULO 400, which is all leap-ness needs, so a year of any
    magnitude can be answered without ever holding it as an integer.
    """
    if month == 2:
        leap = (year_mod_400 % 4 == 0
                and (year_mod_400 % 100 != 0 or year_mod_400 % 400 == 0))
        return 29 if leap else 28
    return 30 if month in (4, 6, 9, 11) else 31


def _real_calendar_and_clock(s):
    """SHAPE IS NOT VALIDITY. The first version matched a regex and stopped, so
    `2023-02-30`, `2023-13-01`, `2023-06-30T25:00:00` and `9999-99-99` were all
    counted as lawful. A census that miscounts what is lawful cannot bound the
    parser that reads it."""
    body = TZ.sub("", s)
    d_part, _, t_part = body.partition("T")
    year_s, month_s, day_s = d_part.lstrip("-").split("-")
    # XML Schema bounds NEITHER the year's value nor its digit count, and Python
    # refuses to convert a digit string past its 4300-digit limit — the very
    # wall `xml_int` already guards in production. `int(year_s)` therefore
    # CRASHED this census on a lawful 5,000-digit year: the tool was less robust
    # than the code it audits, which is how a census stops describing reality.
    #
    # Leap-ness needs the year only MODULO 400, and 400 divides 10**4, so the
    # last four digits give that EXACTLY for a year of any length. The sign does
    # not matter either: -n is divisible by 4, 100 or 400 exactly when n is.
    # Year zero is "every digit is a zero", which needs no conversion at all.
    if not year_s.strip("0"):
        return False                      # XSD 1.0 has no year 0
    year_mod_400 = int(year_s[-4:]) % 400
    month, day = int(month_s), int(day_s)
    if not 1 <= month <= 12 or not 1 <= day <= _days_in_month(year_mod_400, month):
        return False
    if t_part:
        hh, mm, ss = t_part.split(":")
        # XBRL 2.1 §4.7.2 forbids the `24:00:00` end-of-day spelling that XML
        # Schema allows, so the census counts it as non-conforming too.
        if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59
                and 0 <= int(ss.partition(".")[0]) <= 60):
            return False
    return True


def classify(raw):
    """(kind, timezone) for one raw period value.

    `fullmatch`, never `match`: the anchors moved out of the patterns when the
    year and timezone grammars were written as shared fragments, and a bare
    `match` would accept any lawful PREFIX — `2023-06-30xyz` would classify as
    a lawful date.
    """
    s = raw.strip(XML_WS)   # XML whitespace only — NBSP is a character
    is_dt = DATETIME.fullmatch(s) is not None
    is_date = (not is_dt) and DATE_ONLY.fullmatch(s) is not None
    if not (is_dt or is_date) or not _real_calendar_and_clock(s):
        return "OTHER (neither xs:date nor xs:dateTime)", "n/a"
    kind = "dateTime" if is_dt else "date-only"
    # A DATE MAY CARRY A TIMEZONE, so it gets the same reporting as a dateTime
    # rather than a hardcoded "n/a" that hid the distinction.
    tz = TZ.search(s)
    if tz is None:
        return kind, "absent"
    return kind, ("Z" if tz.group(1) == "Z" else tz.group(1))


def _verify_frozen_inputs():
    """PROVE the input set instead of trusting the folder (#827 round 6).

    This census read "whatever .htm is in the directory". The pinned manifest
    of 1,769 name+sha256 pairs already existed and was never opened, so a file
    edited, added or removed underneath it would have changed every number in
    the receipt in silence. Every name and every hash is checked — a partial
    check on a frozen-input claim is the claim restated, not evidence for it.
    """
    manifest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "01b_ix_input_manifest.txt")
    with open(manifest) as fh:
        pinned = dict(line.split() for line in fh if line.strip())
    on_disk = {f for f in os.listdir(ROOT) if f.endswith(".htm")}
    if on_disk != set(pinned):
        raise SystemExit(
            f"the input set is not the pinned one: "
            f"{len(on_disk - set(pinned))} unpinned, "
            f"{len(set(pinned) - on_disk)} missing")
    import hashlib as _h
    for name in sorted(pinned):
        with open(os.path.join(ROOT, name), "rb") as fh:
            if _h.sha256(fh.read()).hexdigest() != pinned[name]:
                raise SystemExit(f"{name} does not match its pinned sha256")
    return sorted(pinned), _h.sha256(
        open(manifest, "rb").read()).hexdigest()


def main():
    # THE SCAN IS THE MANIFEST. Verifying the manifest and then listing the
    # directory means the census reads whatever is there, which is the claim it
    # was supposed to prove rather than assume.
    pinned_names, manifest_sha = _verify_frozen_inputs()
    print(f"frozen inputs PROVEN: {len(pinned_names):,} filings, every name and "
          f"sha256; manifest sha256 {manifest_sha[:16]}", flush=True)
    files = list(pinned_names)
    if not files:
        raise RuntimeError("no filings — the inventory has no premise")
    kinds, tzs, elems, others, whitespace = (collections.Counter() for _ in range(5))
    unparsed = {}
    total = 0
    for i, fn in enumerate(files, 1):
        data = open(os.path.join(ROOT, fn), "rb").read()
        values, error = _period_values(data)
        if error is not None:
            # NOT a silent zero. A document that is not well-formed XML is not
            # an Inline XBRL report, and the inventory says so by name.
            unparsed[fn] = error
            continue
        for elem, raw in values:
            total += 1
            if raw != raw.strip():
                whitespace[repr(raw[:2] + "…" + raw[-2:])] += 1
            kind, tz = classify(raw)
            elems[elem] += 1
            kinds[kind] += 1
            tzs[f"{kind} | tz={tz}"] += 1
            if kind.startswith("OTHER"):
                others[raw.strip()[:40]] += 1
        if i % 400 == 0:
            print(f"{i}/{len(files)} files, {total} period values", flush=True)
    doc = {"receipt": "#827 filing date/dateTime/timezone inventory",
           # the census scans EXACTLY these names, and records the
           # manifest it took them from — verifying a manifest and then
           # listing the directory proves nothing about what was read.
           "input_manifest_sha256": manifest_sha,
           "inputs_are_exactly_the_manifest": True,
           "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
           "cache_root": os.path.relpath(ROOT, _REPO), "n_files": len(files),
           "script_sha256": hashlib.sha256(
               open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "total_period_values": total,
           # WHAT THE CENSUS COULD NOT READ, named. The scan resolves period
           # children by (namespace URI, local name) through a namespace-aware
           # parse, so a filing binding the instance namespace to any prefix is
           # counted; a filing that is not well-formed XML is reported here
           # instead of contributing an invisible zero.
           # NAMED, NOT COUNTED AS A CLAIM ABOUT ALL MALFORMED XML. Two
           # distinct refusals can appear here and each row says which it is:
           # a document lxml itself rejects, and a document whose bytes are
           # illegal in its own declared encoding (XML 1.0 5e 4.3.3), which a
           # well-formedness parse does not answer. The field is therefore not
           # called "all non-well-formed". The 41 filings whose renderer and
           # XML text differ are NOT here and are not malformed: they carry the
           # lawful ASCII reference `&#153;`, which XML resolves to U+0099 and
           # the HTML replacement table maps to U+2122.
           "files_refused_unreadable": len(unparsed),
           "refused_unreadable": dict(sorted(unparsed.items())),
           "period_children_resolved_by": {
               "namespace": _INSTANCE_NS, "local_names": list(PERIOD_LOCALS),
               "standard": "XBRL 2.1 REC-2003-12-31 + corrected errata "
                           "2013-02-20, section 4.7.2",
               "parser": "lxml.etree, resolve_entities=False, no_network=True, "
                         "recover=False — deliberately NOT the production "
                         "reader, so this census cannot prove that reader "
                         "agrees with itself"},
           "by_element": dict(elems), "by_kind": dict(kinds),
           "by_kind_and_timezone": dict(tzs),
           "values_with_surrounding_whitespace": dict(whitespace),
           "non_conforming_values": dict(others.most_common(20))}
    body = json.dumps(doc, indent=1, sort_keys=True)
    open(OUT, "w").write(body + "\n")
    print("kinds:", dict(kinds))
    print("tz:", dict(tzs))
    print("non-conforming:", dict(others.most_common(5)))
    print(f"wrote {os.path.basename(OUT)} total={total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
