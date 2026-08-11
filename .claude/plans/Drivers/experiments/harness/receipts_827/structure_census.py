"""#827 round 5 — the FULL structure census, as a runnable receipt.

The round-4 census existed only as prose in the ledger: a number nobody could
reproduce is not evidence, and the reviewer was right to refuse it. This script
IS the evidence, and it answers exactly one question:

    Does the XBRL 2.1 §4.7/§4.8 structure rule refuse any REAL context or unit?

A guard may only ship if refusing costs ZERO lawful evidence. Over-catching is
as wrong as under-catching — a rule that rejected real filings would silently
delete facts the graph depends on.

BOTH DIRECTIONS, IN THIS ORDER. A census that reports zero because its detector
is broken is worthless, so synthetic malformed documents are driven through the
REAL `prepare()` first and must every one be refused. Only then is the corpus
scanned, and only then does a zero mean anything.

Read-only: local files, no graph, no network, no AI.

Run:  venv/bin/python receipts_827/structure_census.py
Out:  receipts_827/14_structure_census.json
"""
import datetime
import hashlib
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, _REPO)
from driver.relocation.inline_html import prepare      # noqa: E402

CACHE = os.path.join(_REPO, "scripts", "driver_seed", "relocate_probe",
                     "inline_html_cache")
OUT = os.path.join(_HERE, "14_structure_census.json")
MANIFEST = os.path.join(_HERE, "01b_ix_input_manifest.txt")
#: the example list is a SAMPLE, never the count. Both the cap and
#: what it dropped are reported, so the sample can never be read as
#: the whole population.
EXAMPLES_LIMIT = 50

_ENT = ('<xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>'
        '</xbrli:entity>')
_PER = ('<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>'
        '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>')
_DATES = ('<xbrli:startDate>2026-01-01</xbrli:startDate>'
          '<xbrli:endDate>2026-03-31</xbrli:endDate>')
_IDENT = '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>'
_DIV = ('<xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:USD'
        '</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator>'
        '<xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator>'
        '</xbrli:divide>')

#: (label, context body, MUST it be refused). The controls are the point: a
#: rule is only correct if it is correct in BOTH directions.
CONTEXT_PROBES = [
    ("lawful duration", _ENT + _PER, False),
    ("lawful instant",
     _ENT + '<xbrli:period><xbrli:instant>2026-03-31</xbrli:instant>'
     '</xbrli:period>', False),
    ("lawful forever", _ENT + '<xbrli:period><xbrli:forever/></xbrli:period>',
     False),
    ("lawful segment member",
     '<xbrli:entity>' + _IDENT + '<xbrli:segment><xbrldi:explicitMember '
     'dimension="a:Ax">a:M</xbrldi:explicitMember></xbrli:segment>'
     '</xbrli:entity>' + _PER, False),
    ("lawful scenario member",
     _ENT + _PER + '<xbrli:scenario><xbrldi:explicitMember dimension="a:Ax">'
     'a:M</xbrldi:explicitMember></xbrli:scenario>', False),
    ("identifier outside entity", '<xbrli:entity></xbrli:entity>' + _IDENT
     + _PER, True),
    ("bare identifier, no entity", _IDENT + _PER, True),
    ("identifier inside period",
     '<xbrli:entity></xbrli:entity><xbrli:period>' + _IDENT + _DATES
     + '</xbrli:period>', True),
    ("dates outside period", _ENT + _DATES, True),
    ("dates under a wrapper", _ENT + '<xbrli:period><div>' + _DATES
     + '</div></xbrli:period>', True),
    ("two periods", _ENT + _PER + _PER, True),
    ("two entities", _ENT + _ENT + _PER, True),
    ("duplicate forever",
     _ENT + '<xbrli:period><xbrli:forever/><xbrli:forever/></xbrli:period>',
     True),
    ("start with no end",
     _ENT + '<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>'
     '</xbrli:period>', True),
    ("two segments",
     '<xbrli:entity>' + _IDENT + '<xbrli:segment/><xbrli:segment/>'
     '</xbrli:entity>' + _PER, True),
    ("orphan explicitMember",
     '<xbrli:entity>' + _IDENT + '<xbrldi:explicitMember dimension="a:Ax">a:M'
     '</xbrldi:explicitMember></xbrli:entity>' + _PER, True),
    # ---- the round-5b crash: validate before sorting ----------------------
    ("member with NO dimension=",
     '<xbrli:entity>' + _IDENT + '<xbrli:segment><xbrldi:explicitMember>a:M'
     '</xbrldi:explicitMember></xbrli:segment></xbrli:entity>' + _PER, True),
    ("member with a BLANK dimension=",
     '<xbrli:entity>' + _IDENT + '<xbrli:segment><xbrldi:explicitMember '
     'dimension="">a:M</xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
     + _PER, True),
    ("member with no VALUE",
     '<xbrli:entity>' + _IDENT + '<xbrli:segment><xbrldi:explicitMember '
     'dimension="a:Ax"></xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
     + _PER, True),
    ("ONE VALID PLUS ONE NAMELESS — the reported TypeError",
     '<xbrli:entity>' + _IDENT + '<xbrli:segment><xbrldi:explicitMember '
     'dimension="a:Ax">a:M</xbrldi:explicitMember><xbrldi:explicitMember>a:M2'
     '</xbrldi:explicitMember></xbrli:segment></xbrli:entity>' + _PER, True),
    # ---- XBRL 2.1 xs:sequence ---------------------------------------------
    ("period BEFORE entity", _PER + _ENT, True),
    ("scenario BEFORE period",
     _ENT + '<xbrli:scenario><xbrldi:explicitMember dimension="a:Ax">a:M'
     '</xbrldi:explicitMember></xbrli:scenario>' + _PER, True),
    ("segment BEFORE identifier",
     '<xbrli:entity><xbrli:segment><xbrldi:explicitMember dimension="a:Ax">a:M'
     '</xbrldi:explicitMember></xbrli:segment>' + _IDENT + '</xbrli:entity>'
     + _PER, True),
    ("endDate BEFORE startDate",
     _ENT + '<xbrli:period><xbrli:endDate>2026-03-31</xbrli:endDate>'
     '<xbrli:startDate>2026-01-01</xbrli:startDate></xbrli:period>', True),
]
UNIT_PROBES = [
    ("lawful plain", '<xbrli:measure>iso4217:USD</xbrli:measure>', False),
    ("lawful divide", _DIV, False),
    ("divide REVERSED — denominator before numerator",
     '<xbrli:divide><xbrli:unitDenominator><xbrli:measure>xbrli:shares'
     '</xbrli:measure></xbrli:unitDenominator><xbrli:unitNumerator>'
     '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
     '</xbrli:divide>', True),
    ("lawful COMPOUND numerator",
     '<xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:USD'
     '</xbrli:measure><xbrli:measure>xbrli:shares</xbrli:measure>'
     '</xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>utr:MWh'
     '</xbrli:measure></xbrli:unitDenominator></xbrli:divide>', False),
    ("orphan numerator, no divide",
     '<xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure>'
     '</xbrli:unitNumerator>', True),
    ("orphan denominator, no divide",
     '<xbrli:unitDenominator><xbrli:measure>iso4217:USD</xbrli:measure>'
     '</xbrli:unitDenominator>', True),
    ("measure beside a divide",
     '<xbrli:measure>iso4217:USD</xbrli:measure>' + _DIV, True),
    ("two divides", _DIV + _DIV, True),
    ("divide under a wrapper", '<div>' + _DIV + '</div>', True),
    ("empty numerator",
     '<xbrli:divide><xbrli:unitNumerator></xbrli:unitNumerator>'
     '<xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
     '</xbrli:unitDenominator></xbrli:divide>', True),
    ("nothing at all", '', True),
]


def _probe_doc(ctx_body="", unit_body=""):
    return ('<html xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:iso4217="http://example.org/iso4217" xmlns:utr="http://example.org/utr" xmlns:us-gaap="http://example.org/us-gaap" xmlns:dei="http://example.org/dei" xmlns:srt="http://example.org/srt" xmlns:a="http://example.org/a" xmlns:x="http://example.org/x" xmlns:aapl="http://example.org/aapl" xmlns:slg="http://example.org/slg" xmlns:accd="http://example.org/accd" xmlns:ed="http://example.org/ed" xmlns:dvn="http://example.org/dvn" xmlns:fcx="http://example.org/fcx" xmlns:nog="http://example.org/nog" xmlns:inst="http://example.org/inst" xmlns:dimns="http://example.org/dimns" xmlns:nope="http://example.org/nope" xmlns:geo="http://example.org/geo" xmlns:eqt="http://example.org/eqt" xmlns:geography="http://example.org/geography" xmlns:seg="http://example.org/seg" xmlns:country="http://example.org/country"><body><div style="display:none"><ix:header><ix:resources>'
            f'<xbrli:context id="p">{ctx_body}</xbrli:context>'
            f'<xbrli:unit id="p">{unit_body}</xbrli:unit>'
            '</ix:resources></ix:header></div></body></html>')


def self_test():
    """Drive every probe through the REAL parser. Returns the failures."""
    bad = []
    for label, body, must_refuse in CONTEXT_PROBES:
        got = prepare(_probe_doc(ctx_body=body))["contexts"]["p"]
        if isinstance(got, str) != must_refuse:
            bad.append({"kind": "context", "label": label,
                        "expected": "refused" if must_refuse else "allowed",
                        "got": got if isinstance(got, str) else "allowed"})
    for label, body, must_refuse in UNIT_PROBES:
        got = prepare(_probe_doc(ctx_body=_ENT + _PER,
                                 unit_body=body))["units"]["p"]
        if isinstance(got, str) != must_refuse:
            bad.append({"kind": "unit", "label": label,
                        "expected": "refused" if must_refuse else "allowed",
                        "got": got if isinstance(got, str) else "allowed"})
    return bad


def main():
    failures = self_test()
    print(f"detector self-test: {len(CONTEXT_PROBES) + len(UNIT_PROBES)} probes,"
          f" {len(failures)} wrong")
    if failures:
        for f in failures:
            print(f"   WRONG {f['kind']} {f['label']}: expected {f['expected']},"
                  f" got {f['got']}")
        raise SystemExit("the detector cannot see its own probes — a corpus "
                         "zero would prove nothing. REFUSING to census.")

    # THE INPUTS ARE THE PINNED ONES, PROVEN — not "whatever is in the folder".
    # A census over an unknown input set measures an unknown thing, and the
    # manifest of 1,769 filings already exists; it was simply never checked.
    with open(MANIFEST) as fh:
        pinned = dict(line.split() for line in fh if line.strip())
    files = sorted(f for f in os.listdir(CACHE) if f.endswith(".htm"))
    if set(files) != set(pinned):
        raise SystemExit(
            f"input set does not match the manifest: "
            f"{len(set(files) - set(pinned))} unpinned on disk, "
            f"{len(set(pinned) - set(files))} pinned but missing")

    contexts = units = examples_omitted = 0
    refused = {}
    examples = []
    for i, name in enumerate(files, 1):
        with open(os.path.join(CACHE, name), "rb") as fh:
            raw = fh.read()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != pinned[name]:
            raise SystemExit(f"{name} does not match its pinned sha256 — the "
                             f"census input changed under the receipt")
        doc = prepare(raw.decode("utf-8", errors="replace"))
        for kind in ("contexts", "units"):
            for ident, value in sorted(doc[kind].items()):
                if kind == "contexts":
                    contexts += 1
                else:
                    units += 1
                if isinstance(value, str):
                    refused[value] = refused.get(value, 0) + 1
                    # THE LIST IS BOUNDED, AND SAYS SO. It used to stop at 50
                    # in silence, so a receipt showing 50 examples could be
                    # hiding thousands. The totals were always complete; only
                    # the sample was cut, and an uncounted cut reads as "that
                    # was all of them".
                    if len(examples) < EXAMPLES_LIMIT:
                        examples.append({"filing": name, "kind": kind,
                                         "id": ident, "reason": value})
                    else:
                        examples_omitted += 1
        if i % 200 == 0:
            print(f"   {i}/{len(files)}  contexts={contexts:,} units={units:,}"
                  f"  refused={sum(refused.values()):,}", flush=True)

    doc = {
        "receipt": "#827 round 5 — full structure census (XBRL 2.1 §4.7/§4.8)",
        "question": "does the structure rule refuse any REAL context or unit?",
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "script_sha256": hashlib.sha256(
            open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "detector_self_test": {
            "probes": len(CONTEXT_PROBES) + len(UNIT_PROBES),
            "must_refuse": sum(1 for p in CONTEXT_PROBES + UNIT_PROBES if p[2]),
            "must_allow": sum(1 for p in CONTEXT_PROBES + UNIT_PROBES
                              if not p[2]),
            "wrong": len(failures),
            "note": "run BEFORE the corpus; a zero from a blind detector is "
                    "not evidence",
        },
        "inputs": {"manifest": os.path.basename(MANIFEST),
                   "filings_pinned": len(pinned),
                   "every_sha256_verified": True,
                   "note": "the census refuses to run unless the input set and "
                           "every file hash match the pinned manifest"},
        "filings_scanned": len(files),
        "contexts_scanned": contexts,
        "units_scanned": units,
        "refused_total": sum(refused.values()),
        "refused_by_reason": dict(sorted(refused.items())),
        "refused_examples": examples,
        "examples_limit": EXAMPLES_LIMIT,
        "examples_omitted": examples_omitted,
    }
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"\nfilings {len(files)}  contexts {contexts:,}  units {units:,}")
    print(f"REFUSED: {sum(refused.values()):,}")
    for reason, n in sorted(refused.items()):
        print(f"   {n:>9,}  {reason}")
    print(f"wrote {os.path.basename(OUT)}")
    # A refusal is not automatically a defect — but it IS a claim that must be
    # read by a human before the rule ships, so it is surfaced, never buried.
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
