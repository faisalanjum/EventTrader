"""#827 F6 (a): the attach ENVELOPE census — measured reality per field from
the accepted packet corpus, beside the frozen contract intent. Durable and
repo-relative (the SEQ 802 builder law): inputs discovered by glob, every
input hashed, re-runs byte-identical but for the timestamp.

No rule is authored here. The receipt records WHAT IS; the F6 dossier adopts
per field the STRICTER of measured reality vs contract intent (owner ruling
sheet #7 + the SEQ 778 rider: census evidence may narrow, never create
acceptance; widening = census evidence + authority)."""
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
OUT = os.path.join(HERE, "13_f6_envelope_census.json")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


def span_shape(v):
    if type(v) is not list or len(v) != 2:
        return f"NOT-2-LIST:{type(v).__name__}"
    a, b = v
    if type(a) is not int or type(b) is not int:
        return "NON-INT-ENDPOINTS"
    if not 0 <= a < b:
        return "UNORDERED"
    return "OK"


def main():
    files = sorted(glob.glob(os.path.join(
        REPO, "data/driver_catalog_seed/*/packets.jsonl")))
    c = {"packet_files": len(files), "events": 0, "items": 0,
         "items_with_xbrl": 0, "xbrl_with_source_evidence": 0}
    seen = {"event_key_sets": set(), "item_key_sets": set(),
            "xbrl_key_sets": set(), "evidence_key_sets": set(),
            "piece_key_sets": set(), "piece_kinds": set(),
            "dimension_key_sets": set()}
    m = {"sha_grammar_violations": 0, "quote_span_shapes": set(),
         "label_span_shapes": set(), "label_absent": 0,
         "label_outside_quote": 0, "piece_span_shapes": set(),
         "blank_piece_text": 0, "duplicate_piece_records": 0,
         "pieces_container_types": set(), "piece_counts": set(),
         "member_refs_container_types": set(), "text_parts_in_corpus": 0}
    inputs = []
    for f in files:
        inputs.append({"file": os.path.relpath(f, REPO), "sha256":
                       hashlib.sha256(open(f, "rb").read()).hexdigest()})
        for line in open(f, encoding="utf-8"):
            ev = json.loads(line)
            c["events"] += 1
            seen["event_key_sets"].add(tuple(sorted(ev)))
            if "text_parts" in ev:
                m["text_parts_in_corpus"] += 1
            for it in ev.get("items", []):
                c["items"] += 1
                seen["item_key_sets"].add(tuple(sorted(it)))
                x = it.get("xbrl")
                if x is None:
                    continue
                c["items_with_xbrl"] += 1
                seen["xbrl_key_sets"].add(tuple(sorted(x)))
                for dk in ("dimensions", "axis_members"):
                    if isinstance(x.get(dk), list):
                        for dd in x[dk]:
                            if isinstance(dd, dict):
                                seen["dimension_key_sets"].add(
                                    tuple(sorted(dd)))
                se = x.get("source_evidence")
                if se is None:
                    continue
                c["xbrl_with_source_evidence"] += 1
                seen["evidence_key_sets"].add(tuple(sorted(se)))
                sha = se.get("representation_sha256")
                if not (isinstance(sha, str) and SHA64.fullmatch(sha)):
                    m["sha_grammar_violations"] += 1
                m["quote_span_shapes"].add(span_shape(se.get("quote_span")))
                lab = se.get("raw_label_span")
                if lab is None:
                    m["label_absent"] += 1
                else:
                    m["label_span_shapes"].add(span_shape(lab))
                    q = se.get("quote_span")
                    if (span_shape(lab) == "OK" and span_shape(q) == "OK"
                            and not (q[0] <= lab[0] and lab[1] <= q[1])):
                        m["label_outside_quote"] += 1
                ps = se.get("pieces")
                m["pieces_container_types"].add(type(ps).__name__)
                if isinstance(ps, list):
                    m["piece_counts"].add(len(ps))
                    records = []
                    for p in ps:
                        if not isinstance(p, dict):
                            continue
                        seen["piece_key_sets"].add(tuple(sorted(p)))
                        seen["piece_kinds"].add(p.get("kind"))
                        t = p.get("text")
                        if not (isinstance(t, str) and t.strip()):
                            m["blank_piece_text"] += 1
                        m["piece_span_shapes"].add(span_shape(p.get("span")))
                        r = (p.get("kind"), t, tuple(p.get("span") or ()))
                        if r in records:
                            m["duplicate_piece_records"] += 1
                        records.append(r)
    doc = {"receipt": "#827 F6 envelope census (measured reality only)",
           "inputs": inputs,
           "counts": c,
           "seen": {k: sorted(map(list, v)) if k.endswith("_sets")
                    else sorted(v, key=str) for k, v in seen.items()},
           "measured": {k: (sorted(v, key=str) if isinstance(v, set) else v)
                        for k, v in m.items()},
           "script_sha256": hashlib.sha256(
               open(os.path.abspath(__file__), "rb").read()).hexdigest()}
    json.dump(doc, open(OUT, "w"), indent=1, sort_keys=True)
    open(OUT, "a").write("\n")
    print(json.dumps({"counts": c}, indent=1))
    print("kinds:", sorted(seen["piece_kinds"], key=str))
    print("evidence key sets:", sorted(map(list, seen["evidence_key_sets"])))
    print("piece key sets:", sorted(map(list, seen["piece_key_sets"])))
    print("measured:", {k: (sorted(v, key=str) if isinstance(v, set) else v)
                        for k, v in m.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
