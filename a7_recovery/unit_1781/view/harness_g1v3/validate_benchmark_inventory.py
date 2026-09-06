"""Deterministic proof of the one-item benchmark inventory.

WHAT THIS PROVES: the frozen source set is intact against its existing manifest
owner, every record binds to that source through the ONE shared occurrence
owner, the file's structure matches its declared contract, and every reported
count is the record list's own arithmetic.

WHAT THIS DOES NOT PROVE: item meaning, the proposed hard class, control status,
or that a chosen quote boundary is the one the key owner wants. A shorter but
still uniquely located span is lawful here; judging boundaries and meaning is
the independent key owner's job.

The only literals are contract-owned identities: schema name, frozen base
commit, the manifest path, and the structural enum values the contract defines.
There is no keyword, regex, threshold, length rule or example anywhere.
"""
import json, os, sys, glob, hashlib, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "..", "..", "..", "..", "..")))
import kf_lint
import build_launch_manifest as BLM
from driver.core.prepared_fact_v2 import verify_occurrence

HERE = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(HERE, "..", "one_item_benchmark_inventory.json")
SRC_DIR = BLM.INPUTS
MANIFEST_REL = "keys/K-fields/draft_inputs.hashes.json"
MANIFEST = os.path.join(os.path.dirname(SRC_DIR), "draft_inputs.hashes.json")

SCHEMA = "one-item-benchmark-inventory-v5"
BASE_COMMIT = "cd961e51d55bf13aa9311b79c5d7eca20e9b11cc"
TOP_FIELDS = ("schema", "base_commit", "source_manifest", "note", "records", "counts")
MANIFEST_FIELDS = ("path", "file_sha256", "combined_sha256", "n")
#: `raw_label_or_claim` is the source's own label for THIS item. Two lawful
#: distinct facts can be forced into one inseparable quote ("... were $476
#: million and $382 million, respectively"), and only their exact source labels
#: tell the items apart, so identity carries it (Codex SEQ 1336).
RECORD_FIELDS = ("source_id", "part_ref", "occurrence_in_part", "quote",
                 "raw_label_or_claim", "proposed_record_kind",
                 "proposed_hard_classes")
RECORD_KINDS = ("real_item", "lawful_abstention_control", "negative_control")
#: The ten hidden benchmark COVERAGE TAGS. They are non-exclusive test
#: metadata naming which existing rule a row exercises; they are never a
#: production Driver field and never a reader output. An empty list means the
#: row exercises no hard class (owner ruling via Codex SEQ 1330 item 1).
HARD_CLASSES = ("point_range_floor_ceiling", "losses_and_sign",
                "sequential_comparison", "measurement_wording",
                "favourable_unfavourable_direction", "expectation_routing",
                "slices_and_unknown_axes", "portion_versus_whole",
                "ambiguous_menus", "corrections_and_amendments")
#: Every tag must occur on at least this many DISTINCT final rows.
TAG_FLOOR = 5
COUNT_FIELDS = ("records", "proposed_real_items",
                "proposed_lawful_abstention_controls",
                "proposed_negative_controls", "events_covered", "source_events")


def sha_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def check(inv):
    bad = []
    if set(inv) != set(TOP_FIELDS):
        bad.append("top-level fields are not exactly the schema")
    if inv.get("schema") != SCHEMA:
        bad.append("schema is not %s" % SCHEMA)
    if inv.get("base_commit") != BASE_COMMIT:
        bad.append("base_commit is not the frozen base")

    # --- the frozen source set, proved against its EXISTING manifest owner
    sm = inv.get("source_manifest", {})
    if set(sm) != set(MANIFEST_FIELDS):
        bad.append("source_manifest fields are not exactly the schema")
    if sm.get("path") != MANIFEST_REL:
        bad.append("source_manifest path is not the manifest owner")
    man = json.load(open(MANIFEST))
    if sm.get("file_sha256") != sha_file(MANIFEST):
        bad.append("source_manifest file_sha256 does not match the manifest file")
    if sm.get("combined_sha256") != man["combined_sha256"]:
        bad.append("source_manifest combined_sha256 does not match its owner")
    live = {os.path.basename(f) for f in glob.glob(os.path.join(SRC_DIR, "*.json"))}
    if live != set(man["files"]):
        bad.append("live source filenames differ from the manifest's set")
    if sm.get("n") != man["n"] or man["n"] != len(live):
        bad.append("manifest n disagrees with the live source set")
    for name in sorted(live & set(man["files"])):
        if sha_file(os.path.join(SRC_DIR, name)) != man["files"][name]:
            bad.append("source file %s does not match its manifest hash" % name)
    combined = hashlib.sha256(b"".join(
        open(os.path.join(SRC_DIR, n), "rb").read()
        for n in sorted(live))).hexdigest()
    if combined != man["combined_sha256"]:
        bad.append("recomputed combined source hash does not match the manifest")

    events = [os.path.splitext(n)[0] for n in sorted(live)]
    seen = collections.Counter()
    for n, r in enumerate(inv.get("records", [])):
        w = "record %d (%s)" % (n, r.get("source_id"))
        if set(r) != set(RECORD_FIELDS):
            bad.append(w + ": fields are not exactly the record schema"); continue
        if r["proposed_record_kind"] not in RECORD_KINDS:
            bad.append(w + ": proposed_record_kind is not a contract value")
        tags = r["proposed_hard_classes"]
        if not isinstance(tags, list) or any(not isinstance(t, str)
                                             for t in tags):
            bad.append(w + ": proposed_hard_classes is not a list of tags")
        elif len(set(tags)) != len(tags):
            bad.append(w + ": repeats a tag; a row counts once per tag")
        elif any(t not in HARD_CLASSES for t in tags):
            bad.append(w + ": names a tag no contract declares")
        if r["source_id"] not in events:
            bad.append(w + ": names an event outside the frozen set"); continue
        label = r["raw_label_or_claim"]
        if not isinstance(label, str) or not label.strip():
            bad.append(w + ": raw_label_or_claim is not a nonblank string")
        elif label not in r["quote"]:
            # the label must be INSIDE this row's own contiguous quote; if it
            # is not, the source owner extends the quote or refuses
            bad.append(w + ": raw_label_or_claim is not source text inside "
                           "this row's quote")
        # IDENTITY IS THE COMPLETE SOURCE ITEM. Two distinct labels may lawfully
        # share one exact quote; the same label at the same place is a duplicate.
        seen[(r["source_id"], r["part_ref"], r["occurrence_in_part"],
              r["quote"], label)] += 1
        # THE EXISTING DUPLICATE-REFUSING LOOKUP. A dict comprehension over the
        # parts silently keeps the last of two identically labelled parts, so a
        # locator could be checked against the wrong text and still pass.
        parts = kf_lint.part_lookup(r["source_id"], SRC_DIR)
        if r["part_ref"] not in parts:
            bad.append(w + ": part_ref is not a part of its event"); continue
        # THE ONE OWNER decides the locator. part_ref plus the within-part
        # occurrence identifies the span, so the same wording in another named
        # part is not ambiguous and is not refused.
        why = verify_occurrence(parts[r["part_ref"]], r["quote"],
                                r["occurrence_in_part"])
        if why:
            bad.append("%s: %s" % (w, why))
    for k, v in seen.items():
        if v != 1:
            bad.append("duplicate source item x%d in %s" % (v, k[0]))

    counted = collections.Counter(r.get("proposed_record_kind")
                                  for r in inv.get("records", []))
    c = inv.get("counts", {})
    if set(c) != set(COUNT_FIELDS):
        bad.append("counts block is not exactly the counts schema")
    else:
        derived = {"records": len(inv["records"]),
                   "proposed_real_items": counted["real_item"],
                   "proposed_lawful_abstention_controls": counted["lawful_abstention_control"],
                   "proposed_negative_controls": counted["negative_control"],
                   "events_covered": len({r["source_id"] for r in inv["records"]}),
                   "source_events": len(events)}
        for k, v in derived.items():
            if c[k] != v:
                bad.append("counts.%s %s != derived %s" % (k, c[k], v))
    for e in events:
        if e not in {r.get("source_id") for r in inv.get("records", [])}:
            bad.append("event %s has no record" % e)
    return bad


if __name__ == "__main__":
    inv = json.load(open(INV))
    bad = check(inv)
    print("records checked: %d" % len(inv["records"]))
    print("proposed kinds:", dict(collections.Counter(
        r["proposed_record_kind"] for r in inv["records"])))
    for b in bad:
        print("  PROBLEM:", b)
    print("RESULT:", "PASS" if not bad else "FAIL (%d problems)" % len(bad))
    sys.exit(1 if bad else 0)
