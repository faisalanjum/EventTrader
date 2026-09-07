# -*- coding: utf-8 -*-
"""ONE exact expected input per lane, derived once (Codex SEQ 1794 item 2).

WHAT THIS PRODUCES
    evidence/lane_input_profiles.json - for EVERY row of the approved seg-4
    receipt, either `null` (this lane may carry no added input at all) or the
    ONE input it must carry, as structured data: record index, outer record
    type, the field the payload sits in, and the payload's canonical sha256.

HOW A LANE IS CLASSIFIED - no cutoff, no lane name, no cached flag
    A row is PRECALL-CACHED when the run already held a completed answer for
    it before the call. The precall journal names the completed agents; the
    approved receipt pins each row's prompt. Joining them:

        a receipt row is precall-cached  <=>  the number of precall-COMPLETED
        agents whose own prompt hashes to that row's APPROVED pin equals the
        number of receipt rows carrying that pin.

    Two rows share one prompt (the two graders of a batch), so the count is
    what makes the join exact. A PARTIAL match cannot say which of the sharing
    rows was cached, so it REFUSES rather than guess. Nothing here reads the
    state's `cached` flag, and no ordinal is compared against a number.

WHERE THE EXPECTED SHAPE COMES FROM
    The reviewed declaration in evidence/declared_input_attachments.json plus
    the position/type/field block below, which was MEASURED ONCE over the whole
    served population and is declared here as data. The audit never re-derives
    any of it from the transcript it is judging; it reads only what the root
    froze. This file records the measurement so the declaration is reviewable.
"""
import collections
import hashlib
import io
import json
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = R + "/unit_1792"
RECEIPT = UNIT + "/out/proposed_run/receipt.seg04.json"
PRECALL_JOURNAL = R + "/unit_1786/capture/journal.before.jsonl"
PRECALL_IDS = R + "/unit_1786/logs/PRECALL_IDENTITIES.json"
SERVED_DIR = R + "/unit_1786/capture/after/wf_41b934cf-f76"
DECLARED = UNIT + "/evidence/declared_input_attachments.json"
OUT = UNIT + "/evidence/lane_input_profiles.json"


def sha_file(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def records(path):
    """Whole-file read: None if ANY line is malformed. Nothing is skipped."""
    out = []
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            return None
    return out or None


def prompt_pin(recs):
    """The pin of the prompt this worker was actually given, or None."""
    content = ((recs[0].get("message") or {}) if recs else {}).get("content")
    if not isinstance(content, str):
        return None
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def main():
    receipt = json.load(io.open(RECEIPT, encoding="utf-8"))
    rows = receipt["rows"]
    rows_per_pin = collections.Counter(r["prompt_sha256"] for r in rows)

    journal = records(PRECALL_JOURNAL)
    if journal is None:
        print("REFUSED: the precall journal does not read whole")
        return 1
    completed = [r for r in journal if r.get("type") == "result" and r.get("agentId")]

    cached_agents, cached_per_pin = [], collections.Counter()
    for rec in sorted(completed, key=lambda r: r["agentId"]):
        aid = rec["agentId"]
        recs = records(os.path.join(SERVED_DIR, "agent-%s.jsonl" % aid))
        pin = prompt_pin(recs) if recs else None
        if pin is None:
            print("REFUSED: precall agent %s has no readable single-string prompt" % aid)
            return 1
        if pin not in rows_per_pin:
            print("REFUSED: precall agent %s carries a prompt no approved row pins" % aid)
            return 1
        cached_per_pin[pin] += 1
        cached_agents.append(collections.OrderedDict([
            ("agent_id", aid), ("cache_key", rec.get("key")), ("prompt_sha256", pin)]))

    ambiguous = sorted(p for p, n in cached_per_pin.items() if n != rows_per_pin[p])
    if ambiguous:
        print("REFUSED: %d prompt(s) are matched by only some of their rows; the "
              "cached row cannot be identified: %s" % (len(ambiguous), ambiguous))
        return 1

    # ---- the reviewed expected shape ---------------------------------------
    declared = json.load(io.open(DECLARED, encoding="utf-8"))
    if len(declared["attachments"]) != 1:
        print("REFUSED: the declaration names %d attachments; this run declares one"
              % len(declared["attachments"]))
        return 1
    payload = declared["attachments"][0]
    if canon_sha(payload["object"]) != payload["canonical_sha256"]:
        print("REFUSED: the declared payload does not hash to its declared sha256")
        return 1
    spec = collections.OrderedDict([
        ("record_index", 1),
        ("record_type", "attachment"),
        ("payload_field", "attachment"),
        ("payload_sha256", payload["canonical_sha256"])])

    profiles = collections.OrderedDict(
        (r["lane_id"], None if cached_per_pin.get(r["prompt_sha256"]) else
         collections.OrderedDict(spec)) for r in rows)
    n_cached = sum(1 for v in profiles.values() if v is None)

    # ---- the measurement that justifies the declared shape ------------------
    agree, disagree, unreadable = 0, [], []
    served = [f[len("agent-"):-len(".jsonl")] for f in sorted(os.listdir(SERVED_DIR))
              if f.startswith("agent-") and f.endswith(".jsonl")]
    cached_ids = {x["agent_id"] for x in cached_agents}
    for aid in served:
        recs = records(os.path.join(SERVED_DIR, "agent-%s.jsonl" % aid))
        if recs is None:
            # preserved, and never a served answer: a transcript that does not
            # read whole cannot be one, and the owners refuse it on sight
            unreadable.append(aid)
            continue
        extra = [i for i, rec in enumerate(recs) if not isinstance(rec.get("message"), dict)]
        if aid in cached_ids:
            if extra:
                disagree.append((aid, "a precall-cached worker carries %s" % extra))
            continue
        if extra != [spec["record_index"]]:
            disagree.append((aid, "added input at %s, declared %d"
                             % (extra, spec["record_index"])))
            continue
        rec = recs[spec["record_index"]]
        if rec.get("type") != spec["record_type"]:
            disagree.append((aid, "outer type %r" % rec.get("type")))
        elif canon_sha(rec.get(spec["payload_field"])) != spec["payload_sha256"]:
            disagree.append((aid, "a different payload"))
        else:
            agree += 1

    doc = collections.OrderedDict([
        ("purpose", "ONE exact expected input per lane, frozen into the run root and "
                    "read by the audit from there. Never inferred from the state or "
                    "transcript being judged (Codex SEQ 1794 item 2)."),
        ("classification_rule",
         "A receipt row is precall-cached iff the number of precall-COMPLETED agents "
         "whose own prompt hashes to that row's approved pin equals the number of "
         "receipt rows carrying that pin. A partial match refuses. No cached flag, "
         "no lane name and no ordinal cutoff is used."),
        ("sources", collections.OrderedDict([
            ("approved_receipt", collections.OrderedDict([
                ("path", RECEIPT), ("sha256", sha_file(RECEIPT)),
                ("rows", len(rows)), ("distinct_prompt_pins", len(rows_per_pin))])),
            ("precall_journal", collections.OrderedDict([
                ("path", PRECALL_JOURNAL), ("sha256", sha_file(PRECALL_JOURNAL)),
                ("completed_agents", len(completed)),
                ("started_without_result",
                 len([r for r in journal if r.get("type") == "started"]) - len(completed))])),
            ("precall_identities", collections.OrderedDict([
                ("path", PRECALL_IDS), ("sha256", sha_file(PRECALL_IDS))])),
            ("declared_payload", collections.OrderedDict([
                ("path", DECLARED), ("sha256", sha_file(DECLARED))]))])),
        ("precall_completed_agents", cached_agents),
        ("expected_input_for_served_lanes", spec),
        ("declared_shape_basis",
         "record_index, record_type and payload_field were measured ONCE over the "
         "whole served population and are declared here as data; the payload sha256 "
         "is the one reviewed under SEQ 1792. The audit consumes only this "
         "declaration. The payload bytes themselves stay in "
         "declared_input_attachments.json and appear in no code."),
        ("measurement", collections.OrderedDict([
            ("transcripts_present", len(served)),
            ("agree_with_the_declared_shape", agree),
            ("precall_cached_carrying_no_added_input", len(cached_ids)),
            ("preserved_but_unreadable_so_never_an_answer", unreadable),
            ("disagree", [{"agent_id": a, "why": w} for a, w in disagree])])),
        ("counts", collections.OrderedDict([
            ("lanes", len(profiles)), ("no_added_input", n_cached),
            ("expect_the_declared_input", len(profiles) - n_cached)])),
        ("profiles", profiles)])
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, indent=1) + "\n")

    print("  approved receipt rows        : %d (%d distinct prompt pins)"
          % (len(rows), len(rows_per_pin)))
    print("  precall completed agents     : %d" % len(completed))
    print("  lanes expecting NO added input: %d" % n_cached)
    print("  lanes expecting the declared  : %d" % (len(profiles) - n_cached))
    print("  cached lanes                 : %s"
          % [k for k, v in profiles.items() if v is None])
    print("  transcripts present          : %d = %d agreeing + %d cached with none "
          "+ %d unreadable + %d disagreeing"
          % (len(served), agree, len(cached_ids), len(unreadable), len(disagree)))
    for a, w in disagree[:5]:
        print("     %s  %s" % (a, w))
    print("  -> %s  %s" % (OUT, sha_file(OUT)[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
