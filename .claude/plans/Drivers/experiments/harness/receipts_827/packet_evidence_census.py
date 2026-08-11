"""#827 STEP 1 — packet source-evidence census (READ-ONLY files, no graph).

Every saved Route-A packet item carrying `xbrl.source_evidence` is proven
against the FILING ITSELF, not against a restatement of it:

  * the required filing exists in the cache;
  * the prepared-text SHA-256 equals the evidence's representation_sha256;
  * every half-open character span reproduces its own text exactly;
  * the raw label lies INSIDE the quote whenever a label span is present;
  * piece keys, kinds, order, text and spans are exact (order is CARRIED by
    the producer — aligned headers near->far, then the section — and is
    compared as a sequence, never sorted);
  * quote occurrence counts and duplicate-piece counts are recorded;
  * items sharing one quote+label row are grouped, their multiplicities
    reported, and their ORDERED header pieces must be pairwise DISTINCT —
    that is what tells sibling columns apart;
  * every packet and filing path is listed in a sorted manifest with its
    SHA-256.

Inputs are DISCOVERED (glob over data/driver_catalog_seed/*/packets.jsonl),
never hand-listed. Explicit raises, never `assert`: python -O strips asserts.

The synthetic event text used elsewhere is NOT touched here and nothing in
this receipt claims to be the historical model view — that view was never
archived.

Run:  venv/bin/python receipts_827/packet_evidence_census.py
Out:  receipts_827/06_packet_evidence_census.json
      receipts_827/06b_packet_input_manifest.txt
"""
import datetime
import glob
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "driver", "relocation"))

CACHE = os.path.join(_REPO, "scripts", "driver_seed", "relocate_probe",
                     "inline_html_cache")
OUT = os.path.join(_HERE, "06_packet_evidence_census.json")

#: The dated checkpoint, ASSERTED: CE 4, then ACI 3/2/2.
EXPECTED_GROUP_MULTIPLICITIES = [4, 3, 2, 2]

#: THE INPUT ITSELF, PINNED. These were computed, printed and recorded — and
#: never compared — so DELETING A WHOLE PACKET FILE passed with zero problems:
#: 7/136/743 became 6/99/560 and the census still exited 0, because the only
#: pinned shape (the group multiplicities) happened to survive. A census whose
#: premise can silently shrink measures nothing; the size of what was examined
#: is part of the claim.
EXPECTED_COUNTS = {"packet_files": 7, "events": 136, "items": 743,
                   "items_with_source_evidence": 11, "filings_required": 4}
MANIFEST = os.path.join(_HERE, "06b_packet_input_manifest.txt")


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _bounded(start, end, length):
    """A span is lawful only if it is a REAL half-open range inside the text.

    Python slicing accepts negative indices and out-of-range ends silently, so
    an unbounded span could still reproduce 'its own' text and pass every
    downstream check. Both offsets must be plain ints — a bool is an int
    subclass and is not an offset.
    """
    return (type(start) is int and type(end) is int
            and 0 <= start < end <= length)


def main():
    from driver.relocation.inline_html import (PIECE_KEYS, PIECE_KINDS,
                                               SOURCE_EVIDENCE_KEYS, prepare)

    packets = sorted(glob.glob(os.path.join(
        _REPO, "data", "driver_catalog_seed", "*", "packets.jsonl")))
    if not packets:
        raise RuntimeError("no packets.jsonl discovered — census has no premise")

    manifest, problems, rows = [], [], []
    n_events = n_items = 0
    for path in packets:
        manifest.append(f"{os.path.relpath(path, _REPO)} {_sha(path)}")
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            packet = json.loads(line)
            n_events += 1
            for index, item in enumerate(packet.get("items", [])):
                n_items += 1
                ev = (item.get("xbrl") or {}).get("source_evidence")
                if ev:
                    rows.append({"packet": os.path.relpath(path, _REPO),
                                 "source_id": packet["source_id"],
                                 "item_index": index, "evidence": ev,
                                 "concept": item["xbrl"].get("concept"),
                                 # THE PACKET'S OWN CLAIM — the thing the
                                 # evidence must describe. Without these the
                                 # census only proved the spans were valid
                                 # SOMEWHERE in the filing, so swapping an item
                                 # to a different real row passed silently.
                                 "claimed_quote": item.get("quote"),
                                 # THE REAL KEY IS `raw_label_or_claim` — the
                                 # ChannelContract's public name. I read
                                 # `raw_label`, which is absent, so `.get`
                                 # returned None and my label check NEVER RAN:
                                 # a dead comparison reading as a proof.
                                 "claimed_label":
                                     item.get("raw_label_or_claim")})

    prepared_by_filing, filings = {}, []
    for r in rows:
        sid = r["source_id"]
        if sid in prepared_by_filing:
            continue
        fpath = os.path.join(CACHE, f"{sid}.htm")
        if not os.path.exists(fpath):
            problems.append(f"{sid}: required filing is ABSENT from the cache")
            continue
        filings.append(fpath)
        prepared_by_filing[sid] = prepare(
            open(fpath, encoding="utf-8", errors="replace").read())
    for fpath in sorted(set(filings)):
        manifest.append(f"{os.path.relpath(fpath, _REPO)} {_sha(fpath)}")

    for r in rows:
        ev, sid, tag = r["evidence"], r["source_id"], \
            f"{r['source_id']}#{r['item_index']}"
        prepared = prepared_by_filing.get(sid)
        if prepared is None:
            continue
        text = prepared["text"]

        if sorted(ev) != sorted(SOURCE_EVIDENCE_KEYS):
            problems.append(f"{tag}: evidence keys {sorted(ev)} != the four "
                            f"approved {sorted(SOURCE_EVIDENCE_KEYS)}")
        if ev["representation_sha256"] != prepared["text_sha"]:
            problems.append(f"{tag}: representation_sha256 does not match the "
                            f"prepared text of its own filing")

        q0, q1 = ev["quote_span"]
        # BOUNDS BEFORE USE. A negative offset is a lawful Python slice and an
        # unlawful span: `text[-5:-2]` returns characters happily, so an
        # unbounded span could reproduce "its" text and pass.
        if not _bounded(q0, q1, len(text)):
            problems.append(f"{tag}: quote_span {ev['quote_span']} is not a "
                            f"half-open range inside the text")
            continue
        quote = text[q0:q1]
        r["quote"] = quote
        r["quote_occurrences"] = text.count(quote)
        # THE EVIDENCE MUST DESCRIBE *THIS* ITEM (blocker 5). A span that is
        # valid in the filing but belongs to another row is exactly the attack
        # the reviewer ran: group multiplicities moved 4/3/2/2 -> 3/3/2/2/1 and
        # the census still said zero problems.
        # EXACT EQUALITY, not containment: a containment test passes whenever
        # the claim happens to appear anywhere inside the span, so a wider or
        # neighbouring row satisfied it. Verified against the live packets —
        # all 11 items are exactly equal, so the strict rule costs nothing.
        claimed = r.get("claimed_quote")
        if claimed is None:
            problems.append(f"{tag}: the item states no quote of its own, so "
                            f"nothing ties this evidence to it")
        elif claimed != quote:
            problems.append(f"{tag}: the quote_span text does NOT EQUAL the "
                            f"item's own quote — the evidence describes a "
                            f"different row")
        # A REPEATED QUOTE IS LAWFUL, and demanding uniqueness here CONTRADICTED
        # PRODUCTION. `prepared_fact_v2.verify_occurrence` explicitly allows a
        # quote to occur n>1 times and disambiguates with `occurrence_in_part`
        # (1 <= k <= count); the previous rule rejected exactly what production
        # accepts. The ADDRESS is the span, and the span is already checked to
        # reproduce the item's own quote EXACTLY — repetition elsewhere in the
        # filing cannot make that span point somewhere else. Recorded, not
        # judged. (My own over-reach: it passed on 11 samples and was wrong
        # about the universe.)

        label_span = ev["raw_label_span"]
        # A CLAIMED LABEL MUST BE BACKED BY A SPAN. The check below ran only
        # when a span was PRESENT, so deleting the span deleted the check with
        # it: the reviewer removed all 11 label spans and the census still
        # reported zero problems. Absence of evidence was reading as absence of
        # a claim. The item's own claim decides whether a span is required.
        if label_span is None and r.get("claimed_label") is not None:
            problems.append(f"{tag}: the item claims a raw_label_or_claim but "
                            f"the evidence carries NO raw_label_span, so the "
                            f"label is unbacked")
        if label_span is not None:
            l0, l1 = label_span
            if not (q0 <= l0 < l1 <= q1):
                problems.append(f"{tag}: the raw label span is NOT inside the "
                                f"quote span")
            r["raw_label"] = text[l0:l1]
            claimed_label = r.get("claimed_label")
            if claimed_label is None:
                problems.append(f"{tag}: a raw_label_span is present but the "
                                f"item states no raw_label_or_claim")
            elif claimed_label != r["raw_label"]:
                problems.append(f"{tag}: the raw_label_span text does NOT "
                                f"EQUAL the item's own raw_label_or_claim")

        kinds, texts, spans = [], [], []
        for i, piece in enumerate(ev["pieces"]):
            if sorted(piece) != sorted(PIECE_KEYS):
                problems.append(f"{tag}: piece {i} keys {sorted(piece)} != "
                                f"{sorted(PIECE_KEYS)}")
                continue
            if piece["kind"] not in PIECE_KINDS:
                problems.append(f"{tag}: piece {i} kind {piece['kind']!r} is "
                                f"outside {PIECE_KINDS}")
            s0, s1 = piece["span"]
            if not _bounded(s0, s1, len(text)):
                problems.append(f"{tag}: piece {i} span {piece['span']} is not "
                                f"a half-open range inside the text")
                continue
            if text[s0:s1] != piece["text"]:
                problems.append(f"{tag}: piece {i} span does not reproduce its "
                                f"own text")
            kinds.append(piece["kind"])
            texts.append(piece["text"])
            spans.append((s0, s1))
        # ORDER IS CARRIED: every header precedes the single optional section.
        if "section" in kinds and kinds != ["header"] * kinds.index("section") \
                + ["section"]:
            problems.append(f"{tag}: piece order is not headers-then-section: "
                            f"{kinds}")
        r["piece_kinds"] = kinds
        r["piece_count"] = len(ev["pieces"])
        # A DUPLICATE IS THE SAME ADDRESS TWICE — same kind AND same span.
        # Keying on (kind, TEXT) was wrong in BOTH directions: it never fired
        # (computed, reported, never judged, so a duplicated piece passed), and
        # once it did fire it rejected what production legitimately builds —
        # two different header cells reading "Total" are two distinct pieces at
        # two distinct spans, and `inline_html` emits them without dedupe.
        # The span is the identity, so the span is what must not repeat.
        addresses = [(k, tuple(sp)) for k, sp in zip(kinds, spans)]
        r["duplicate_pieces"] = len(addresses) - len(set(addresses))
        if r["duplicate_pieces"]:
            problems.append(f"{tag}: {r['duplicate_pieces']} evidence piece(s) "
                            f"repeat an earlier (kind, span) — the same address "
                            f"twice is not additional evidence")
        r["header_sequence"] = [t for k, t in zip(kinds, texts)
                                if k == "header"]

    groups = {}
    for r in rows:
        if "quote" not in r:
            continue
        key = (r["source_id"], tuple(r["evidence"]["quote_span"]),
               tuple(r["evidence"]["raw_label_span"] or ()))
        groups.setdefault(key, []).append(r)
    group_report = []
    for key, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        seqs = [tuple(m["header_sequence"]) for m in members]
        distinct = len(set(seqs)) == len(seqs)
        if len(members) > 1 and not distinct:
            problems.append(
                f"{key[0]} rows sharing one quote+label do NOT have distinct "
                f"ordered header pieces — sibling columns are indistinguishable")
        group_report.append({
            "source_id": key[0], "quote_span": list(key[1]),
            "raw_label_span": list(key[2]) or None,
            "multiplicity": len(members),
            "ordered_header_sequences_distinct": distinct,
            "item_indexes": sorted(m["item_index"] for m in members),
            "piece_counts": [m["piece_count"] for m in members]})

    # THE PINNED SHAPE, ASSERTED — not merely reported. The checkpoint is
    # 4/3/2/2 (CE's four shared-row facts, then ACI's 3/2/2). Any regrouping
    # is drift and must fail loudly.
    seen_mult = sorted((len(m) for m in groups.values()), reverse=True)
    if seen_mult != EXPECTED_GROUP_MULTIPLICITIES:
        problems.append(
            f"shared-row group multiplicities are {seen_mult}, not the pinned "
            f"{EXPECTED_GROUP_MULTIPLICITIES} — the evidence regrouped")

    counts = {"packet_files": len(packets), "events": n_events,
              "items": n_items, "items_with_source_evidence": len(rows),
              "filings_required": len(prepared_by_filing)}
    if counts != EXPECTED_COUNTS:
        problems.append(
            f"the examined input is not the pinned one: {counts} != "
            f"{EXPECTED_COUNTS} — a census over a different corpus proves "
            f"nothing about this one")

    manifest_body = "\n".join(sorted(manifest)) + "\n"
    open(MANIFEST, "w").write(manifest_body)
    doc = {
        "receipt": "#827 packet source-evidence census",
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "inputs_discovered_by": "glob data/driver_catalog_seed/*/packets.jsonl",
        "input_manifest_file": os.path.basename(MANIFEST),
        "input_manifest_sha256": hashlib.sha256(
            manifest_body.encode()).hexdigest(),
        "script_sha256": _sha(os.path.abspath(__file__)),
        "counts": counts,
        "counts_pinned": EXPECTED_COUNTS,
        "evidence_keys_seen": sorted({k for r in rows for k in r["evidence"]}),
        "per_item": [{"source_id": r["source_id"],
                      "item_index": r["item_index"],
                      "packet": r["packet"], "concept": r["concept"],
                      "quote_occurrences": r.get("quote_occurrences"),
                      "piece_count": r.get("piece_count"),
                      "piece_kinds": r.get("piece_kinds"),
                      "duplicate_pieces": r.get("duplicate_pieces"),
                      "raw_label": r.get("raw_label")} for r in rows],
        "shared_row_groups": group_report,
        "group_multiplicities": sorted(
            (g["multiplicity"] for g in group_report), reverse=True),
        "problems": problems,
        "note": "the synthetic event text used by the door tests is NOT "
                "evidence and is not examined here; the historical model view "
                "was never archived and nothing in this receipt claims to be "
                "it",
    }
    body = json.dumps(doc, indent=1, sort_keys=True)
    open(OUT, "w").write(body + "\n")
    print(f"packets={len(packets)} events={n_events} items={n_items} "
          f"evidence_items={len(rows)} filings={len(prepared_by_filing)}")
    print(f"group multiplicities: {doc['group_multiplicities']}")
    print(f"piece counts: {[r.get('piece_count') for r in rows]}")
    print(f"problems: {len(problems)}")
    for p in problems[:10]:
        print("   ", p)
    print(f"wrote {os.path.relpath(OUT, _REPO)} "
          f"(sha256 {hashlib.sha256(body.encode()).hexdigest()[:16]})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
