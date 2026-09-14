"""THE one ACTIVE owner of the current K-fields key lifecycle (Codex SEQ 1359).

WHY THIS FILE EXISTS. The pre-A2 review package and its owner
`build_inventory_review.py` are FROZEN HISTORY: they shipped 168 mechanical
proposals, and the review they fed produced the signed 196-record inventory.
Those two counts are both true and must never be forced equal, so that owner is
never edited, rebuilt, repinned, and its live-coupled `--verify` is never used
as an active gate. This module is the single active owner beside it.

WHAT IT OWNS, and nothing else:
    lineage ......... read the frozen 168 package as immutable input history
    the seam ........ the accepted materializer: verdicts + the ONE reviewed
                      reconciliation -> the signed final inventory
    the lock ........ the accepted pre-A2 lock shape, re-derived not copied
    A4 phase 1 ...... one independent adjudication call per frozen item

WHAT IT BORROWS, never re-implements:
    raw JSON cleaner ......... raw_transport.parse_reply
    item schema + menu ....... a1_reader (defaults, required fields, menu)
    locator .................. kf_lint.part_lookup + verify_occurrence
    inventory contract ....... validate_benchmark_inventory (fields, check,
                               classes, floor, base commit)
    source set + transport ... build_launch_manifest and the frozen A3 plan

There is deliberately no proof framework, no provider, no runner and no
compatibility layer here. The A3 drafts this package ships are UNTRUSTED LEADS:
they are what two blind readers wrote, never what is true.
"""
import collections
import hashlib
import io
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_X = os.path.dirname(_HERE)
_REPO = os.path.abspath(os.path.join(_X, "..", "..", "..", ".."))
for _p in (_HERE, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import a1_reader                                                # noqa: E402
import audit_worker_access as AUD                               # noqa: E402
import build_exp5_contract as C                                 # noqa: E402
import kf_lint                                                  # noqa: E402
import build_launch_manifest as BLM                             # noqa: E402
import raw_transport as RT                                      # noqa: E402
import validate_benchmark_inventory as INV                      # noqa: E402
from driver.core.prepared_fact_v2 import verify_occurrence      # noqa: E402

#: The run evidence lives outside the repo, so it is named once and may be
#: pointed elsewhere; nothing else in this module knows a path.
EVIDENCE = os.environ.get(
    "KFIELDS_EVIDENCE",
    "/tmp/claude-1000/-home-faisal-EventMarketDB/"
    "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
HISTORY = os.path.join(_X, "inventory_review")
REVIEW_RUN = os.path.join(EVIDENCE, "invrev_run4")
LOCK_DIR = os.path.join(EVIDENCE, "lock", "candidate")
#: THE A3 DEPENDENCY BASELINE, versioned beside its history (Codex SEQ 1488
#: item 2). v1 was measured over the pre-v3 `harness/` tree that this module
#: no longer imports, so it could neither pass nor guard; v2 is measured in a
#: clean interpreter over the exact tree the lifecycle imports.
A3_BASELINE_V1 = os.path.join(EVIDENCE, "a4", "a3_baseline.json")
A3_BASELINE = os.path.join(EVIDENCE, "a4", "a3_baseline.v2_1488.json")

#: Codex's stated A3 ledger baseline (SEQ 1357); everything after it is
#: MEASURED from the A3 finalizations rather than typed.
LEDGER_A3_BASELINE = 3597

SOURCE_MARK = "[SOURCE]"
MENU_MARK = "[MENU]"
ITEM_MARK = "[ITEM]"
DRAFTS_MARK = "[A3 DRAFTS - UNTRUSTED LEADS]"
REPLY_KEYS = ("packet_id", "settled", "reconciliation", "ambiguities")
#: The settled shape is the one-item reader's OWN reply contract, taken
#: from it rather than retyped, so a schema change moves this by itself.
SETTLED_KEYS = tuple(a1_reader.REPLY_KEYS)
RECON_KEYS = ("lane_id", "exact_match", "why")
AMBIGUITY_KEYS = ("what", "why")

_PLAN = RT.a1_plan()
MODEL = _PLAN["transport"]["model"]
EFFORT = _PLAN["transport"]["effort"]
AGENT_TYPE = _PLAN["transport"]["agentType"]
DISALLOWED = tuple(_PLAN["transport"]["disallowedTools"])
MAX_OUTPUT = _PLAN["transport"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"]

#: The RUNTIME model id is pinned from the frozen runtime proof, not from
#: the launcher alias: `sonnet` is what we ask for, `claude-sonnet-5` is
#: what answered, and only the second one is evidence (Codex SEQ 1360 item 3).
RUNTIME_FREEZE = json.loads(io.open(
    os.path.join(_HERE, "a2_runtime_freeze.json"), encoding="utf-8").read())
RUNTIME_MODEL_ID = RUNTIME_FREEZE["runtime_model_id"]
PARENT_SESSION = RUNTIME_FREEZE["parent_session_id"]

#: The rendered-script size ceiling, borrowed from the owner that
#: already measured it rather than retyped here.
TRANSPORT_LIMIT = __import__("build_inventory_review").TRANSPORT_LIMIT

A4_DOOR = "a4_phase1_one_item_key"


def _transport_block():
    """What the launcher asks for AND what must answer. Both are evidence."""
    return collections.OrderedDict([
        ("model_alias", MODEL), ("runtime_model_id", RUNTIME_MODEL_ID),
        ("effort", EFFORT), ("agentType", AGENT_TYPE),
        ("disallowedTools", list(DISALLOWED)),
        ("CLAUDE_CODE_MAX_OUTPUT_TOKENS", MAX_OUTPUT),
        ("parent_session_id", PARENT_SESSION),
        ("transport", "Claude Code Workflow agent(), subscription"),
        ("runtime_freeze_sha256",
         INV.sha_file(os.path.join(_HERE, "a2_runtime_freeze.json")))])


def _budget_block(calls):
    """Primaries, then the worst lawful case: one retry for every item."""
    return collections.OrderedDict([
        ("before", LEDGER_BEFORE), ("after", LEDGER_BEFORE + calls),
        ("retry_cap", 1),
        ("retry_cap_meaning", "PER ITEM, never a run total"),
        ("max_attempts_per_item", MAX_ATTEMPTS),
        ("abort_ceiling", LEDGER_BEFORE + 2 * calls)])



def _sha(text):
    return hashlib.sha256(text.encode("utf-8") if isinstance(text, str)
                          else text).hexdigest()


def _read(path):
    return io.open(path, encoding="utf-8").read()


def _load(path):
    return json.loads(_read(path))


# --------------------------------------------------------------- lineage ---

def historical_paths():
    """Every frozen byte this module reads as history. It never writes one."""
    man = os.path.join(HISTORY, "package.manifest.json")
    paths = [man, os.path.join(_HERE, "build_inventory_review.py")]
    for e in _load(man)["events"]:
        paths.append(os.path.join(HISTORY, "inputs", e["source_id"] + ".json"))
    return sorted(paths)


def historical_package():
    """The frozen 168-proposal package, verified as history and read-only.

    This checks the package against ITS OWN manifest - never against the live
    inventory, which its own review lawfully advanced to 196 records.
    """
    man = _load(os.path.join(HISTORY, "package.manifest.json"))
    problems, inputs = [], collections.OrderedDict()
    order = [e["source_id"] for e in man["events"]]
    if len(set(order)) != len(order):
        problems.append("the frozen package lists an event twice")
    shipped = 0
    for e in man["events"]:
        path = os.path.join(HISTORY, "inputs", e["source_id"] + ".json")
        if not os.path.isfile(path):
            problems.append("%s: shipped input is missing" % e["source_id"])
            continue
        got = INV.sha_file(path)
        inputs[e["source_id"]] = got
        if got != e["input_sha256_shipped"]:
            problems.append("%s: shipped input bytes are not the manifest's"
                            % e["source_id"])
        body = _load(path)
        if len(body["proposals"]) != e["proposals"]:
            problems.append("%s: ships %d proposal rows, the manifest says %d"
                            % (e["source_id"], len(body["proposals"]),
                               e["proposals"]))
        shipped += len(body["proposals"])
    if shipped != man["inventory"]["proposals"]:
        problems.append("the package ships %d proposal rows, its manifest "
                        "records %d" % (shipped, man["inventory"]["proposals"]))
    if man["package_owner"]["sha256"] != INV.sha_file(
            os.path.join(_HERE, "build_inventory_review.py")):
        problems.append("the historical owner's bytes are not the pinned ones")
    return {"manifest": man, "order": order, "inputs": inputs,
            "proposals": shipped, "problems": problems}


def historical_source_gap():
    """The narrow, honest record of one overwritten historical blob.

    The frozen manifest names the candidate inventory it was built from. That
    file was later overwritten in place by the accepted final inventory, so the
    original bytes no longer exist anywhere reachable. We report that rather
    than synthesise bytes and call them original (Codex SEQ 1359 item 3).
    """
    named = historical_package()["manifest"]["inventory"]["sha256"]
    roots = [_X, EVIDENCE, os.path.expanduser("~/.core827-orchestrator")]
    searched, found = [], False
    for root in roots:
        if not os.path.isdir(root):
            continue
        searched.append(root)
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if not f.endswith(".json"):
                    continue
                p = os.path.join(dirpath, f)
                try:
                    if os.path.getsize(p) > 20 * 1024 * 1024:
                        continue
                    if INV.sha_file(p) == named:
                        found = True
                except OSError:
                    continue
    return {"named_sha256": named, "found": found, "searched": searched,
            "bound_instead": "frozen_package_inputs",
            "why": "the named candidate inventory was overwritten in place by "
                   "the accepted final inventory; the frozen package's own 36 "
                   "inputs and 168 shipped proposal rows are bound as lineage"}


# ----------------------------------------------------------- source access --

def source_parts(source_id):
    """The ONE locator owner's view of an event's parts."""
    return kf_lint.part_lookup(source_id, BLM.INPUTS)


def source_input(source_id):
    return _load(os.path.join(BLM.INPUTS, source_id + ".json"))


# ------------------------------------------------- the adopted seam (item 4)

def _best_attempts():
    """The last attempt per event, from the review run's own ledger."""
    best = {}
    for a in _load(os.path.join(REVIEW_RUN, "attempts.json")):
        cur = best.get(a["source_id"])
        if cur is None or a["attempt"] > cur["attempt"]:
            best[a["source_id"]] = a
    return best


def _derive(recon, best, order):
    """Accepted verdicts + the ONE reviewed reconciliation -> rows.

    Adopted unchanged in behaviour from the reviewed scratch seam. The rows are
    DERIVED, never copied from the artifact; the artifact's own proposed
    inventory must then equal the derivation exactly.
    """
    problems, rows, sidecar, raws = [], collections.OrderedDict(), [], {}
    for sid in order:
        a = best[sid]
        raw = _read(os.path.join(REVIEW_RUN, "replies", a["raw_name"]))
        raws[sid] = raw
        got = RT.parse_reply(raw)
        ev = []
        for v in got["verdicts"]:
            if v.get("row") is not None:
                ev.append(dict(v["row"]))
            sidecar.append(collections.OrderedDict([
                ("source_id", sid), ("origin", "proposal"),
                ("proposal_id", v["proposal_id"]), ("decision", v["decision"]),
                ("why", v["why"]), ("row", v.get("row"))]))
        for ad in got.get("additions") or []:
            ev.append(dict(ad["row"]))
            sidecar.append(collections.OrderedDict([
                ("source_id", sid), ("origin", "addition"),
                ("proposal_id", None), ("decision", "add"),
                ("why", ad["why"]), ("row", ad["row"])]))
        for x in got.get("exclusions_considered") or []:
            sidecar.append(collections.OrderedDict([
                ("source_id", sid), ("origin", "exclusion_considered"),
                ("proposal_id", None), ("decision", "exclude"),
                ("why", x["why"]),
                ("row", {"quote": x["quote"], "part_ref": x["part_ref"],
                         "occurrence_in_part": x["occurrence_in_part"]})]))
        rows[sid] = ev

    declared = {c["owner"] for c in recon["changes"]}
    known = ({a["id"] for a in recon["aggregate_changes"]}
             | {c["id"] for c in recon["coverage_selections"]}
             | {"ledger#%02d" % r["ordinal"] for r in recon["resolutions"]})
    for owner in sorted(declared - known):
        problems.append("reconciliation change has no declared owner: %s" % owner)
    for r in recon["resolutions"]:
        if r["status"] == "remains_genuinely_unsettled":
            problems.append("resolution %d is unresolved" % r["ordinal"])
    for c in recon["changes"]:
        sid = c["source_id"]
        if sid not in rows:
            problems.append("change names an event outside the accepted set: %s"
                            % sid)
            continue
        if c["op"] == "promote":
            rows[sid].append(collections.OrderedDict([
                ("source_id", sid), ("part_ref", None),
                ("occurrence_in_part", None), ("quote", c["quote"]),
                ("raw_label_or_claim", c["label"]),
                ("proposed_record_kind", c["kind"]),
                ("proposed_hard_classes", list(c["tags"]))]))
            sidecar.append(collections.OrderedDict([
                ("source_id", sid), ("origin", "reviewed_reconciliation"),
                ("proposal_id", None), ("decision", "promote"),
                ("why", c["owner"]), ("row", None)]))
            continue
        hit = [r for r in rows[sid] if r["quote"] == c["quote"]
               and r["raw_label_or_claim"] == c["label"]]
        if len(hit) != 1:
            problems.append("change targets %d rows in %s" % (len(hit), sid))
            continue
        r = hit[0]
        r["proposed_record_kind"] = c["after"]["kind"]
        r["proposed_hard_classes"] = list(c["after"]["tags"])
        sidecar.append(collections.OrderedDict([
            ("source_id", sid), ("origin", "reviewed_reconciliation"),
            ("proposal_id", None), ("decision", c["op"]),
            ("why", c["owner"]), ("row", None)]))

    for sid, rs in rows.items():
        parts = source_parts(sid)
        for r in rs:
            if r["part_ref"] is None:
                owners = [p for p, t in parts.items() if r["quote"] in t]
                if len(owners) != 1:
                    problems.append("%s: a promoted quote locates in %d parts"
                                    % (sid, len(owners)))
                    continue
                r["part_ref"] = owners[0]

    locator = []
    for sid, rs in rows.items():
        parts = source_parts(sid)
        for r in rs:
            txt = parts.get(r["part_ref"])
            if txt is None:
                problems.append("%s: part %r is not a part of the event"
                                % (sid, r["part_ref"]))
                continue
            n = txt.count(r["quote"])
            raw_ix = r["occurrence_in_part"]
            if n == 0:
                problems.append("%s: quote does not locate" % sid)
                continue
            if n == 1:
                if raw_ix is not None:
                    problems.append("%s: unique quote carries an index" % sid)
                final = None
            else:
                if type(raw_ix) is not int or not 0 <= raw_ix <= n - 1:
                    problems.append("%s: raw index %r outside 0..%d"
                                    % (sid, raw_ix, n - 1))
                    continue
                final = raw_ix + 1
                locator.append(collections.OrderedDict([
                    ("source_id", sid), ("part_ref", r["part_ref"]),
                    ("quote", r["quote"]), ("raw_0_based", raw_ix),
                    ("final_1_based", final), ("occurrences", n)]))
            why = verify_occurrence(txt, r["quote"], final)
            if why:
                problems.append("%s: %s" % (sid, why))
            r["occurrence_in_part"] = final
    return rows, sidecar, raws, locator, problems


def materialize():
    """Re-run the accepted materialization and return its exact bytes.

    Writes nothing. A caller compares `inventory_text` to the signed inventory;
    any drift is a refusal, never a repair.
    """
    recon = _load(os.path.join(REVIEW_RUN, "reconciliation_final.json"))
    best = _best_attempts()
    order = historical_package()["order"]
    rows, sidecar, raws, locator, problems = _derive(recon, best, order)

    for sid in order:
        want = recon["proposed_inventory"].get(sid, [])
        got = rows.get(sid, [])
        if len(want) != len(got):
            problems.append("%s: derived %d rows, the artifact claims %d"
                            % (sid, len(got), len(want)))
            continue
        for w, g in zip(want, got):
            for f in ("source_id", "quote", "raw_label_or_claim",
                      "proposed_record_kind"):
                if w[f] != g[f]:
                    problems.append("%s: %s differs from the artifact"
                                    % (sid, f))
            if list(w["proposed_hard_classes"]) != list(g["proposed_hard_classes"]):
                problems.append("%s: tags differ from the artifact" % sid)

    records = [collections.OrderedDict((f, r[f]) for f in INV.RECORD_FIELDS)
               for sid in order for r in rows[sid]]
    counted = collections.Counter(r["proposed_record_kind"] for r in records)
    frozen = _load(INV.INV)
    inventory = collections.OrderedDict([
        ("base_commit", INV.BASE_COMMIT),
        ("counts", collections.OrderedDict([
            ("events_covered", len({r["source_id"] for r in records})),
            ("proposed_lawful_abstention_controls",
             counted["lawful_abstention_control"]),
            ("proposed_negative_controls", counted["negative_control"]),
            ("proposed_real_items", counted["real_item"]),
            ("records", len(records)), ("source_events", len(order))])),
        ("note", frozen["note"]), ("records", records),
        ("schema", INV.SCHEMA), ("source_manifest", frozen["source_manifest"])])
    inv_text = json.dumps(inventory, indent=1, sort_keys=True)
    problems += INV.check(json.loads(inv_text))

    tags = collections.defaultdict(set)
    for r in records:
        for t in r["proposed_hard_classes"]:
            tags[t].add((r["source_id"], r["quote"], r["raw_label_or_claim"]))
    counts = collections.OrderedDict((t, len(tags[t])) for t in INV.HARD_CLASSES)
    for t, n in counts.items():
        if n < INV.TAG_FLOOR:
            problems.append("hard class %s has %d distinct rows, below the "
                            "floor %d" % (t, n, INV.TAG_FLOOR))

    side_text = json.dumps(collections.OrderedDict([
        ("schema", "pre-a2-inventory-adjudication-v1"),
        ("rows", sidecar),
        ("reviewed_reconciliation", collections.OrderedDict([
            ("path", os.path.relpath(
                os.path.join(REVIEW_RUN, "reconciliation_final.json"),
                EVIDENCE)),
            ("sha256", _sha(_read(os.path.join(
                REVIEW_RUN, "reconciliation_final.json")))),
            ("resolutions", len(recon["resolutions"])),
            ("changes", len(recon["changes"])),
            ("locator_translations", locator)])),
        ("raw_replies", collections.OrderedDict(
            (s, _sha(raws[s])) for s in order))]), indent=1)
    val_text = json.dumps(collections.OrderedDict([
        ("validator", os.path.relpath(INV.__file__, "/home/faisal/EventMarketDB")),
        ("problems", []), ("records_checked", len(records)),
        ("hard_class_counts", dict(counts)), ("tag_floor", INV.TAG_FLOOR)]),
        indent=1)
    return {"inventory_text": inv_text, "sidecar_text": side_text,
            "receipt_text": val_text, "records": records,
            "hard_class_counts": counts, "locator": locator,
            "raw_replies": raws, "problems": problems}


def final_boundary_problems(records):
    """Why this record list is not the accepted final inventory.

    Order, identity, locator, class and control are all compared against the
    signed bytes; a swap, omission, duplicate, mutation or borrowed evidence
    refuses here rather than downstream.
    """
    bad = []
    signed = _load(INV.INV)["records"]
    if len(records) != len(signed):
        bad.append("%d records, the signed inventory holds %d"
                   % (len(records), len(signed)))
    for i, (got, want) in enumerate(zip(records, signed)):
        for f in INV.RECORD_FIELDS:
            a, b = got.get(f), want.get(f)
            if isinstance(a, list) or isinstance(b, list):
                a, b = list(a or []), list(b or [])
            if a != b:
                bad.append("record %d: %s is not the signed value" % (i, f))
    keys = [(r.get("source_id"), r.get("quote"), r.get("raw_label_or_claim"))
            for r in records]
    if len(set(keys)) != len(keys):
        bad.append("a record appears twice")
    for r in records:
        parts = source_parts(r.get("source_id", ""))
        txt = parts.get(r.get("part_ref"))
        if txt is None:
            bad.append("%s: part %r is not a part of that event"
                       % (r.get("source_id"), r.get("part_ref")))
            continue
        why = verify_occurrence(txt, r.get("quote", ""),
                                r.get("occurrence_in_part"))
        if why:
            bad.append("%s: %s" % (r.get("source_id"), why))
    return bad


# ------------------------------------------------------- the adopted lock ---

_LOCK_BOUND = collections.OrderedDict([
    ("reviewed_reconciliation", (REVIEW_RUN, "reconciliation_final.json")),
    ("final_inventory", (LOCK_DIR, "final_inventory.json")),
    ("adjudication_sidecar", (LOCK_DIR, "adjudication_sidecar.json")),
    ("validator_receipt", (LOCK_DIR, "validator_receipt.json")),
    ("sign_input", (LOCK_DIR, "final_sign_input.json")),
    ("sign_prompt", (LOCK_DIR, "final_sign_prompt.txt")),
    ("sign_script", (LOCK_DIR, "final_sign.js")),
    ("signer_raw", (LOCK_DIR, "final_sign.attempt1.raw.json")),
])


def lock():
    """The accepted pre-A2 lock, re-derived from live bytes every time."""
    ev = _load(os.path.join(LOCK_DIR, "final_sign_evidence.json"))
    reply = _load(os.path.join(LOCK_DIR, "final_sign_reply.json"))
    out = materialize()
    atts = _load(os.path.join(REVIEW_RUN, "attempts.json"))
    reps = _load(os.path.join(REVIEW_RUN,
                              "transport_proof_replacements.json"))
    inv = json.loads(out["inventory_text"])
    return collections.OrderedDict([
        ("schema", "pre-a2-inventory-lock-v1"),
        ("state", "LOCKED"),
        ("base_commit", INV.BASE_COMMIT),
        ("artifacts", collections.OrderedDict(
            (k, INV.sha_file(os.path.join(*p))) for k, p in _LOCK_BOUND.items())),
        ("counts", inv["counts"]),
        ("hard_class_counts", collections.OrderedDict(out["hard_class_counts"])),
        ("tag_floor", INV.TAG_FLOOR),
        ("signer", collections.OrderedDict([
            ("signed", reply["signed"]), ("blocked", reply["blocked"]),
            ("run_id", ev["run_id"]), ("agent_id", ev["agent_id"]),
            ("attempt", ev["attempt"]),
            ("state_sha256", ev["state_sha256"]),
            ("transcript_sha256", ev["transcript_sha256"]),
            ("raw_sha256", ev["raw_sha256"]),
            ("parent_session_id", ev["parent_session_id"]),
            ("model", ev["model"]), ("effort", ev["effort"]),
            ("agent_type", ev["agent_type"]), ("transport", "subscription"),
            ("max_output_tokens", "128000"), ("tool_calls", ev["tool_calls"])])),
        ("call_accounting", collections.OrderedDict([
            ("event_attempts", len(atts)), ("quarantined_calls", len(reps)),
            ("sign_calls", 1),
            ("paid_calls", len(atts) + len(reps) + 1),
            ("abort_ceiling", 74)])),
    ])


def lock_problems(candidate):
    """Re-derive every bound value; mutating any one of them must refuse."""
    bad = []
    live = lock()
    for k, p in _LOCK_BOUND.items():
        path = os.path.join(*p)
        if not os.path.isfile(path):
            bad.append("bound artifact missing: %s" % k)
        elif candidate.get("artifacts", {}).get(k) != INV.sha_file(path):
            bad.append("bound artifact changed: %s" % k)
    for k in ("counts", "hard_class_counts", "call_accounting", "base_commit",
              "state", "tag_floor"):
        if candidate.get(k) != live[k]:
            bad.append("%s does not re-derive" % k)
    for k, v in live["signer"].items():
        if candidate.get("signer", {}).get(k) != v:
            bad.append("signer %s does not re-derive" % k)
    if candidate.get("signer", {}).get("signed") is not True or \
            candidate.get("signer", {}).get("blocked") is not None:
        bad.append("the lock does not carry a clean signature")
    return bad


# ---------------------------------------------------- A4 phase 1 (item 5) ---

def a3_run_dirs():
    run = _read(os.path.join(EVIDENCE, "a3_serial_dir.txt")).strip()
    return run, os.path.join(run, "retry")


#: NO AUDIT CACHE. Keying the auditor's answer on the receipt bytes was wrong:
#: the audit reads state files, transcripts, launchers, the plan, the manifest
#: and code, so a dependency can drift while the receipt stays byte-identical
#: and a cached "clean" would survive it (Codex SEQ 1364 item 4). The uncached
#: read costs about 0.6s, which is not worth a stale proof.


def a3_evidence():
    """The PROVED A3 answers, taken only from the existing A1 auditor.

    An earlier version paired sorted raw filenames to `receipt.allowed` by
    position. Position proves nothing: swap the bytes under a name and the
    pairing still lines up, so unverified post-A3 bytes could have become A4
    evidence. Codex proved exactly that by mutation (SEQ 1360 item 2).

    So this consumes `audit_worker_access.audit()`'s own `answers` handoff and
    nothing else, for the primary and for the one lawful child, and refuses
    unless the primary is clean, the canonical 392 keys are exactly present,
    the child is exactly the finalizer's invalid-only set, and the child
    supersedes. No second auditor is built here.
    """
    primary, retry = a3_run_dirs()
    plan = RT.a1_plan()
    problems, binding = [], collections.OrderedDict()

    pa = AUD.audit(os.path.join(primary, "receipt.json"))
    problems += ["primary audit: %s" % p for p in pa["problems"]]
    fin = _load(os.path.join(primary, "finalization.json"))
    problems += ["primary finalization: %s" % p
                 for p in RT.a1_primary_evidence_problems(fin, plan, primary)]
    canonical = {tuple(c) for c in RT.a1_canonical_calls(plan, 1)}
    if set(pa["answers"]) != canonical:
        problems.append("the primary proves %d of the canonical %d A3 answers"
                        % (len(set(pa["answers"]) & canonical), len(canonical)))

    want = {tuple(k) for k in RT.a1_primary_retry_keys(fin, plan)}
    answers = dict(pa["answers"])
    child = os.path.join(retry, "receipt.json")
    if want and not os.path.isfile(child):
        problems.append("the finalizer names %d retry keys and no child ran"
                        % len(want))
    elif os.path.isfile(child):
        ra = AUD.audit(child)
        problems += ["retry audit: %s" % p for p in ra["problems"]]
        if set(ra["answers"]) != want:
            problems.append("the child answers %s, the finalizer names %s"
                            % (sorted(ra["answers"]), sorted(want)))
        cfin = _load(os.path.join(retry, "finalization.json"))
        if cfin.get("retry"):
            problems.append("the child names a successor; there is no third "
                            "attempt")
        answers.update(ra["answers"])          # the child supersedes, by order
        for name, path in (("retry_receipt", child),
                           ("retry_finalization",
                            os.path.join(retry, "finalization.json"))):
            binding[name] = INV.sha_file(path)

    for name, path in (("primary_receipt",
                        os.path.join(primary, "receipt.json")),
                       ("primary_finalization",
                        os.path.join(primary, "finalization.json"))):
        binding[name] = INV.sha_file(path)
    return {"answers": answers, "problems": problems, "binding": binding}


def phase1_items():
    """The ordered denominator: one call per frozen item, in plan order.

    Refuses outright if the A3 evidence is not proved: a lead whose provenance
    is unproved is worse than no lead at all.
    """
    ev = a3_evidence()
    if ev["problems"]:
        raise RuntimeError("A3 evidence is not proved: %s" % ev["problems"][:3])
    answers = ev["answers"]
    items = []
    for packet in _PLAN["packets"]:
        drafts = []
        for lane in sorted(k[1] for k in answers if k[0] == packet["packet_id"]):
            drafts.append({"lane_id": lane,
                           "text": answers[(packet["packet_id"], lane)],
                           "sha256": _sha(answers[(packet["packet_id"], lane)])})
        row = collections.OrderedDict([
            ("packet_id", packet["packet_id"]),
            ("source_id", packet["source_id"]),
            ("part_ref", packet["item"]["part_ref"]),
            ("occurrence_in_part", packet["item"]["occurrence_in_part"]),
            ("quote", packet["item"]["quote"]),
            ("raw_label_or_claim", packet["item"]["raw_label_or_claim"]),
            ("a3_drafts", drafts)])
        items.append(row)
    return items


def locator_problems(item):
    """The one locator boundary, asked of its existing owner."""
    parts = source_parts(item["source_id"])
    txt = parts.get(item["part_ref"])
    if txt is None:
        return ["%s: part %r is not a part of that event"
                % (item["source_id"], item["part_ref"])]
    why = verify_occurrence(txt, item["quote"], item["occurrence_in_part"])
    return [why] if why else []


def _rules_block():
    """The fixed, byte-identical authority.

    The ACTIVE one-item meaning owner is served WHOLE, not summarised: this
    takes `build_exp5_contract.build_prompt("drafter")` - role, rules, the
    derived output card, the data boundary and the injection control - and
    keeps everything up to its [INPUT] marker. A thin hand-written summary was
    the defect Codex refused in SEQ 1360 item 1; borrowing the assembled owner
    means a future rule change moves this prompt by itself.

    Only the A4 additions are written here: the adjudication task, the
    untrusted-draft reconciliation and the ambiguity envelope.
    """
    base = C.build_prompt("drafter")
    head, sep, _tail = base.partition("[INPUT]")
    if not sep:
        raise SystemExit("the meaning owner no longer marks its [INPUT]")
    lanes = ", ".join("`%s`" % k for k in RECON_KEYS)
    return head.rstrip() + "\n\n" + "\n".join([
        "[A4 TASK]",
        "You are the independent K-fields KEY OWNER. Everything above defines",
        "what a lawful reply means; obey it exactly. Your job is to SETTLE the",
        "expected reply for the one located item, from the source alone.",
        "",
        "Two earlier drafts from blind readers are shown last, after the data.",
        "They are UNTRUSTED LEADS. They may both be wrong, and they may agree",
        "with each other and still both be wrong. Never treat either as truth,",
        "never borrow evidence from one, and never split a difference to agree",
        "with them. Settle the item first; only then compare.",
        "",
        "Genuine ambiguity is an ANSWER, not a failure. Record it rather than",
        "resolving it by guessing.",
        "",
        "[A4 OUTPUT]",
        "Reply with ONE JSON object and nothing else - no prose before or after",
        "it, no second object. Plain JSON, or exactly one fenced JSON block.",
        "Its keys are EXACTLY these four, with no others: %s."
        % ", ".join("`%s`" % k for k in REPLY_KEYS),
        "",
        "`packet_id`      the packet id shown in the item block, echoed exactly.",
        "`settled`        the reply the [OUTPUT] section above defines, in that",
        "                 exact sparse four-field shape: %s."
        % ", ".join("`%s`" % k for k in SETTLED_KEYS),
        "                 Its `source_id` is the event's, echoed exactly. When",
        "                 no lawful fact exists, `facts` is empty and the reason",
        "                 belongs in `abstentions` - that IS the no-fact reason,",
        "                 and `continuity_hints` is still stated, never dropped.",
        "`reconciliation` exactly one row per draft lane shown below, in the",
        "                 order shown, each an object with keys %s." % lanes,
        "                 `lane_id` echoes that lane exactly. `exact_match` is a",
        "                 real boolean: true only if that draft states the same",
        "                 settled reply you just wrote. `why` is a nonempty",
        "                 sentence saying what matches or differs.",
        "`ambiguities`    a list, possibly empty, of objects with keys %s,"
        % ", ".join("`%s`" % k for k in AMBIGUITY_KEYS),
        "                 both nonempty strings.",
        "",
        "Every field is required. Emit no key that is not named here.",
    ]) + "\n"


RULES_BLOCK = _rules_block()


def phase1_prompt(item):
    """Fixed rules first, byte-identical; the untrusted drafts strictly last."""
    src = source_input(item["source_id"])
    parts = ["%s\n\n%s %s\n" % (RULES_BLOCK, SOURCE_MARK, item["source_id"])]
    for part in src["text_parts"]:
        parts.append("--- %s ---\n%s\n" % (part["part"], part["content"]))
    # the owner returns (display, back); only the DISPLAY is shown, one token
    # per line, and `restore_menu_pick` turns any exact pick back again
    display, _back = a1_reader.readable_menu(src["menu_tokens"])
    parts.append("\n%s\n%s\n" % (MENU_MARK, "\n".join(display)))
    parts.append("\n%s\n%s\n" % (ITEM_MARK, json.dumps(
        collections.OrderedDict(
            (f, item[f]) for f in ("packet_id", "source_id", "part_ref",
                                   "occurrence_in_part", "quote",
                                   "raw_label_or_claim")), indent=1)))
    parts.append("\n%s\n" % DRAFTS_MARK)
    for d in item["a3_drafts"]:
        parts.append("--- %s ---\n%s\n" % (d["lane_id"], d["text"]))
    return "".join(parts)


# -------------------------------------------------- the frozen A4 package ---

def ledger_before():
    """MEASURED: Codex's A3 baseline plus what the A3 receipts actually spent."""
    run = _read(os.path.join(EVIDENCE, "a3_serial_dir.txt")).strip()
    spent = 0
    for base in (run, os.path.join(run, "retry")):
        fin = os.path.join(base, "finalization.json")
        if os.path.isfile(fin):
            spent += _load(fin)["ledger"]["scheduled"]
    return LEDGER_A3_BASELINE + spent


LEDGER_BEFORE = ledger_before()


def build_phase1(out_dir):
    """Write the frozen A4 phase-1 candidate. Launches nothing.

    The prompts are NOT shipped as 196 files: each one embeds its whole source,
    so shipping them would duplicate the frozen sources many times over for no
    proof. The manifest pins each prompt's hash and `package_problems` renders
    every prompt again from the same owners and compares, which is the stronger
    check and the smaller package.
    """
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    items = phase1_items()
    ev = a3_evidence()
    rows, sizes, scripts = [], [], []
    for item in items:
        text = phase1_prompt(item)
        script = render_launcher(item)
        sizes.append(len(text.encode("utf-8")))
        scripts.append(len(script.encode("utf-8")))
        rows.append(collections.OrderedDict([
            ("packet_id", item["packet_id"]),
            ("source_id", item["source_id"]),
            ("prompt_sha256", _sha(text)),
            ("prompt_bytes", sizes[-1]),
            ("script_sha256", _sha(script)),
            ("script_bytes", scripts[-1]),
            # every accepted A3 answer is bound BY HASH, so a swapped draft
            # cannot pass as evidence later
            ("drafts", [collections.OrderedDict([("lane_id", d["lane_id"]),
                                                 ("sha256", d["sha256"])])
                        for d in item["a3_drafts"]])]))
    doc = collections.OrderedDict([
        ("schema", "kfields-a4-phase1-v1"),
        ("base_commit", INV.BASE_COMMIT),
        ("door", "a4_phase1_one_item_key"),
        ("calls", len(rows)),
        ("inventory_sha256", INV.sha_file(INV.INV)),
        ("rules_sha256", _sha(RULES_BLOCK)),
        ("transport", _transport_block()),
        ("a3_binding", ev["binding"]),
        ("budget", _budget_block(len(rows))),
        ("capacity", collections.OrderedDict([
            ("unit", "UTF-8 bytes of the serialized launcher script the "
                     "runtime actually runs; never summed"),
            ("transport_limit_bytes", TRANSPORT_LIMIT),
            ("largest_script_bytes", max(scripts)),
            ("smallest_script_bytes", min(scripts)),
            ("largest_prompt_bytes", max(sizes)),
            ("at_or_over_transport_limit",
             sorted(r["packet_id"] for r, n in zip(rows, scripts)
                    if n >= TRANSPORT_LIMIT))])),
        ("history", collections.OrderedDict([
            ("frozen_package_proposals",
             historical_package()["manifest"]["inventory"]["proposals"]),
            ("final_inventory_records", len(_load(INV.INV)["records"])),
            ("source_gap", historical_source_gap())])),
        ("reply_keys", list(REPLY_KEYS)),
        ("launch", collections.OrderedDict([
            ("renderer", "build_kfields_key.render_launcher"),
            ("gate", "build_kfields_key.preflight must pass first"),
            ("prepare", "build_kfields_key.prepare_run"),
            ("finalize", "build_kfields_key.finalize"),
            ("order", "the items list below, once each, in this order"),
            ("one_agent_in_flight", True),
            ("retry", "at most one identical-prompt retry, transport/JSON/"
                      "schema only; never a semantic retry"),
            ("raw_first", "preserve every raw answer before any parse")])),
        ("items", rows)])
    text = json.dumps(doc, indent=1)
    io.open(os.path.join(out_dir, "phase1.manifest.json"), "w",
            encoding="utf-8").write(text)
    io.open(os.path.join(out_dir, "rules.txt"), "w",
            encoding="utf-8").write(RULES_BLOCK)
    doc["manifest_sha256"] = _sha(text)
    return doc


def package_problems(pkg_dir):
    """Why this built package is not the exact, ordered, unaltered candidate."""
    bad = []
    doc = _load(os.path.join(pkg_dir, "phase1.manifest.json"))
    items = phase1_items()
    if doc["calls"] != len(items) or len(doc["items"]) != len(items):
        bad.append("the package declares %d calls for %d frozen items"
                   % (doc["calls"], len(items)))
    if doc["rules_sha256"] != _sha(RULES_BLOCK):
        bad.append("the shipped rules block is not the live one")
    if doc["inventory_sha256"] != INV.sha_file(INV.INV):
        bad.append("the package is not bound to the signed inventory")
    over = doc["capacity"]["at_or_over_transport_limit"]
    if over:
        bad.append("%d prompts are at or over the transport limit" % len(over))
    if doc["capacity"]["transport_limit_bytes"] != TRANSPORT_LIMIT:
        bad.append("the package records a different transport limit")
    for got, item in zip(doc["items"], items):
        if got["packet_id"] != item["packet_id"]:
            bad.append("call order changed at %s" % got["packet_id"])
            continue
        if got["prompt_sha256"] != _sha(phase1_prompt(item)):
            bad.append("%s: the pinned prompt hash is not the live rendering"
                       % item["packet_id"])
        if got["script_sha256"] != _sha(render_launcher(item)):
            bad.append("%s: the pinned launcher script is not the live one"
                       % item["packet_id"])
        live = [collections.OrderedDict([("lane_id", d["lane_id"]),
                                         ("sha256", d["sha256"])])
                for d in item["a3_drafts"]]
        if [dict(d) for d in got["drafts"]] != [dict(d) for d in live]:
            bad.append("%s: the pinned A3 draft bytes are not the proved ones"
                       % item["packet_id"])
    if doc["transport"] != _transport_block():
        bad.append("the pinned transport is not the live frozen one")
    if doc["a3_binding"] != a3_evidence()["binding"]:
        bad.append("the pinned A3 receipts/finalizations are not the live ones")
    if doc["budget"] != _budget_block(len(items)):
        bad.append("the pinned budget is not the derived one")
    return bad


# ------------------------------------------------------ A3 stays untouched --

#: THE re-audit owner: the versioned successor of the SEQ 1358 a3_reaudit.py,
#: run in a CLEAN interpreter so this module's own imports can never change
#: what A3 is said to depend on. This module holds no copy of its derivation.
A3_REAUDIT = os.path.join(EVIDENCE, "a4", "a3_reaudit_v2.py")


def _a3_probe(out=None):
    cmd = [sys.executable, "-B", A3_REAUDIT] + ([out] if out else [])
    got = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO)
    if got.returncode != 0:
        raise RuntimeError(got.stderr.strip()[-400:])
    doc = json.loads(got.stdout)
    if os.path.realpath(doc["tree"]) != os.path.realpath(_HERE):
        raise RuntimeError("the re-audit owner measures %s; this lifecycle "
                           "imports %s" % (doc["tree"], _HERE))
    return doc


def a3_dependency_digest():
    return _a3_probe()["digest"]


def a3_problems():
    return _a3_probe()["primary_problems"]


def write_a3_baseline():
    """Publish THE versioned baseline once, through the re-audit owner and
    its write-once output. No caller chooses the path."""
    return _a3_probe(A3_BASELINE)


if __name__ == "__main__":
    hist = historical_package()
    print("history: %d shipped proposals, %d events, problems %s"
          % (hist["proposals"], len(hist["order"]), hist["problems"] or "none"))
    gap = historical_source_gap()
    print("history source gap: named %s found=%s bound=%s"
          % (gap["named_sha256"][:12], gap["found"], gap["bound_instead"]))
    out = materialize()
    print("materialized: %d records, problems %s"
          % (len(out["records"]), out["problems"][:2] or "none"))
    print("  reproduces the signed inventory: %s"
          % (_sha(out["inventory_text"]) == INV.sha_file(INV.INV)))
    print("lock: problems %s" % (lock_problems(lock())[:2] or "none"))
    items = phase1_items()
    print("A4 phase 1: %d calls, ledger %d -> %d"
          % (len(items), LEDGER_BEFORE, LEDGER_BEFORE + len(items)))
    print("A3: digest %s problems %s"
          % (a3_dependency_digest()[:12], a3_problems() or "none"))


# ------------------------------------------ the A4 phase-1 door (item 3) ---
#: One item may be attempted at most twice, and attempt 2 only after a SAVED
#: invalid attempt 1. `retry_cap = 1` below is PER ITEM, never a run total.
MAX_ATTEMPTS = 2


def _frozen_item(item):
    """The four located fields the reader is allowed to trust."""
    return {k: item[k] for k in ("part_ref", "occurrence_in_part", "quote",
                                 "raw_label_or_claim")}


def completed_draft(item, text):
    """One A3 draft, completed through the SAME reader as a settled reply.

    Returns None when the draft is not a lawful reply at all: an unreadable
    lead cannot equal anything, so `exact_match` for it is false.
    """
    try:
        obj = RT.parse_reply(text)
    except Exception:                                 # noqa: BLE001 - by design
        return None
    if not isinstance(obj, dict):
        return None
    _display, back = a1_reader.readable_menu(
        source_input(item["source_id"])["menu_tokens"])
    frozen, sid = _frozen_item(item), item["source_id"]
    completed, bad = a1_reader.normalize(obj, frozen, sid, back)
    if bad or completed is None:
        return None
    if a1_reader.validate(completed, frozen, source_parts(sid)):
        return None
    return completed


def _answer_identity(completed):
    """The completed reply projected onto what makes it THE SAME ANSWER.

    `abstentions[].reason` is required, nonblank and preserved evidence - the
    reader enforces that before anything reaches here - but it is not answer
    identity: two lawful readers may word one abstention differently and still
    have decided the same thing about the same span. Everything else stays:
    the fact-versus-abstain branch, the source binding, the exact locator
    (quote / part_ref / occurrence_in_part), every fact field and every
    continuity proposal (Codex SEQ 1370 ruling 1).
    """
    return dict(completed, abstentions=[
        {k: v for k, v in a.items() if k != "reason"}
        for a in completed["abstentions"]])


def _same_answer(a, b):
    """Do these two completed replies state the same answer? Structural only."""
    if a is None or b is None:
        return False
    return _answer_identity(a) == _answer_identity(b)


def read_reply(text, item):
    """Raw A4 answer -> the settled envelope, validated WHOLE. -> (obj, problems)

    A single problem accepts nothing: no sibling row, no half-reconciliation and
    no partial credit. The nested settled reply is normalized and validated by
    the existing one-item reader, so this owner adds no second fact schema.
    """
    if not isinstance(text, str):
        return None, ["no reply text: %s" % type(text).__name__]
    try:
        obj = RT.parse_reply(text)
    except Exception as exc:                          # noqa: BLE001 - by design
        return None, ["not one lawful JSON object: %s" % str(exc)[:120]]
    if not isinstance(obj, dict):
        return None, ["the reply is %s, not an object" % type(obj).__name__]
    if set(obj) != set(REPLY_KEYS):
        return None, ["keys are %s, not exactly %s"
                      % (sorted(obj), sorted(REPLY_KEYS))]

    problems = []
    if obj["packet_id"] != item["packet_id"]:
        problems.append("packet echo is %r, not %r"
                        % (obj["packet_id"], item["packet_id"]))

    settled = obj["settled"]
    completed = None
    if not isinstance(settled, dict):
        problems.append("settled is %s, not an object" % type(settled).__name__)
    elif set(settled) != set(SETTLED_KEYS):
        problems.append("settled keys are %s, not exactly %s"
                        % (sorted(settled), sorted(SETTLED_KEYS)))
    else:
        # NEVER re-serialise: `parse_reply` returns exact Decimals, and a
        # round trip through text would either crash or quietly change a
        # number's type. `normalize`/`validate` are the reader's own
        # object-level seams, which is what read_one calls after parsing.
        _display, back = a1_reader.readable_menu(
            source_input(item["source_id"])["menu_tokens"])
        frozen, sid = _frozen_item(item), item["source_id"]
        completed, sub = a1_reader.normalize(settled, frozen, sid, back)
        if not sub:
            sub = a1_reader.validate(completed, frozen,
                                     source_parts(sid)) or []
            if sub:
                completed = None
        problems += ["settled: %s" % s for s in sub]

    lanes = [d["lane_id"] for d in item["a3_drafts"]]
    rec = obj["reconciliation"]
    if not isinstance(rec, list) or len(rec) != len(lanes):
        problems.append("reconciliation must be %d rows, one per shown lane"
                        % len(lanes))
    else:
        for row, lane in zip(rec, lanes):
            if not isinstance(row, dict) or set(row) != set(RECON_KEYS):
                problems.append("a reconciliation row is not exactly %s"
                                % sorted(RECON_KEYS))
                continue
            if row["lane_id"] != lane:
                problems.append("reconciliation names %r, not %r"
                                % (row["lane_id"], lane))
            if type(row["exact_match"]) is not bool:
                problems.append("%s: exact_match is not a real boolean" % lane)
            elif completed is not None:
                # DERIVED, never trusted. The model may say anything; whether a
                # draft states the same settled reply is a fact this owner
                # computes, by completing that draft through the same reader
                # and comparing the completed objects exactly.
                drafted = completed_draft(
                    item, [d for d in item["a3_drafts"]
                           if d["lane_id"] == lane][0]["text"])
                truth = _same_answer(drafted, completed)
                if row["exact_match"] != truth:
                    problems.append("%s: exact_match says %r; this draft %s "
                                    "the settled reply"
                                    % (lane, row["exact_match"],
                                       "states" if truth else "does not state"))
            if not (isinstance(row["why"], str) and row["why"].strip()):
                problems.append("%s: why is not a nonempty string" % lane)

    amb = obj["ambiguities"]
    if not isinstance(amb, list):
        problems.append("ambiguities is not a list")
    else:
        for a in amb:
            if not isinstance(a, dict) or set(a) != set(AMBIGUITY_KEYS):
                problems.append("an ambiguity is not exactly %s"
                                % sorted(AMBIGUITY_KEYS))
                continue
            for k in AMBIGUITY_KEYS:
                if not (isinstance(a[k], str) and a[k].strip()):
                    problems.append("an ambiguity's %s is not a nonempty "
                                    "string" % k)
    if problems:
        return None, problems
    return {"packet_id": obj["packet_id"], "settled": completed,
            "reconciliation": rec, "ambiguities": amb}, []


def render_launcher(item, attempt=1):
    """The ONE supported serial route: a single agent() call, nothing else."""
    call = collections.OrderedDict([("packet_id", item["packet_id"]),
                                    ("source_id", item["source_id"]),
                                    ("attempt", attempt)])
    return "\n".join([
        "export const meta = {",
        "  name: 'kfields-a4-phase1',",
        "  description: 'K-fields A4 phase 1: one independent key call for one"
        " already-located item',",
        "  phases: [{ title: 'Adjudicate' }],",
        "}",
        "const CALL = " + json.dumps(call),
        "const PROMPT = " + json.dumps(phase1_prompt(item)),
        "let text = null",
        "try {",
        "  text = await agent(PROMPT, {",
        "    label: CALL.packet_id, phase: 'Adjudicate',",
        "    model: " + json.dumps(MODEL) + ", effort: " + json.dumps(EFFORT) + ",",
        "    agentType: " + json.dumps(AGENT_TYPE) + ",",
        "    disallowedTools: " + json.dumps(list(DISALLOWED)) + ",",
        "  })",
        "} catch (e) { text = null }",
        "return { packet_id: CALL.packet_id, source_id: CALL.source_id,",
        "         attempt: CALL.attempt, model: " + json.dumps(MODEL) + ",",
        "         effort: " + json.dumps(EFFORT) + ",",
        "         agentType: " + json.dumps(AGENT_TYPE) + ",",
        "         text: typeof text === 'string' ? text : null }",
        "",
    ])


def _recorded_zero(value):
    """A RECORDED JSON integer zero, and nothing that merely looks like one.

    `(x or 0) != 0` accepted absent, null, false, "", [], {} and 0.0 alike, so
    a state that never recorded the evidence proved zero tool use. Missing or
    wrongly typed evidence proves nothing (Codex SEQ 1367, 1368).
    """
    return type(value) is int and value == 0


def _official_proof(state_path, prompt):
    """Prove ONE official state's transcript. -> (final, complete, problems)

    `final` is what the runtime handed back and what the state's own returned
    object must equal byte-for-byte; `complete` is the whole answer across a
    lawful continuation and is the ONLY thing parsed. The chain owner keeps
    them distinct on purpose, and so does this (Codex SEQ 1364 item 3).
    """
    bad = []
    session_dir, session_id = AUD._official_location(state_path)
    if session_dir is None:
        return None, None, ["the state is not where the runtime puts an "
                            "official one"]
    if session_id != PARENT_SESSION:
        bad.append("parent session is %r, not the frozen one" % session_id)
    doc = _load(state_path)
    if doc.get("status") != "completed":
        bad.append("state status is %r" % doc.get("status"))
    rows = [r for r in (doc.get("workflowProgress") or [])
            if r.get("type") == "workflow_agent"]
    if len(rows) != 1:
        return None, None, bad + ["%d agent rows; phase 1 runs exactly one"
                                  % len(rows)]
    row = rows[0]
    if row.get("model") != RUNTIME_MODEL_ID:
        bad.append("the state row names model %r, not the frozen runtime id"
                   % row.get("model"))
    if row.get("agentType") != AGENT_TYPE:
        bad.append("agentType %r" % row.get("agentType"))
    if not _recorded_zero(row.get("toolCalls")):
        bad.append("row toolCalls is %r, not a recorded integer zero"
                   % (row.get("toolCalls"),))
    if not _recorded_zero(doc.get("totalToolCalls")):
        bad.append("run totalToolCalls is %r, not a recorded integer zero"
                   % (doc.get("totalToolCalls"),))
    if "lastToolName" in row:
        # the same rule the official-state audit already applies
        bad.append("the row records a last tool name")
    tp = os.path.join(session_dir, "subagents", "workflows",
                      os.path.splitext(os.path.basename(state_path))[0],
                      "agent-%s.jsonl" % row.get("agentId"))
    if not os.path.isfile(tp):
        return None, None, bad + ["the transcript is missing"]
    recs = AUD._jsonl(tp)
    if recs is None:
        return None, None, bad + ["the transcript cannot be read whole"]
    asst = [r for r in recs if r.get("type") == "assistant"]
    bad += AUD._input(recs, _sha(prompt))          # the owner pins a HASH
    models = {(r.get("message") or {}).get("model") for r in asst}
    if models - {RUNTIME_MODEL_ID}:
        bad.append("a response names model %s" % sorted(models, key=str))
    efforts = {r.get("effort") for r in asst}
    if efforts - {EFFORT}:
        bad.append("a response names effort %s" % sorted(efforts, key=str))
    tools = [b for r in asst for b in (r["message"].get("content") or [])
             if isinstance(b, dict) and b.get("type") in ("tool_use",
                                                          "tool_result")]
    if tools:
        bad.append("%d tool blocks in the transcript" % len(tools))
    if not asst:
        return None, None, bad + [NO_ANSWER]
    chain, final, complete = AUD._chain(recs, asst)
    bad += chain
    if complete is None:
        bad.append("no proved answer")
    return final, complete, bad


def official_answer(state_path, prompt):
    """The COMPLETE proved answer, for callers that only parse."""
    _final, complete, bad = _official_proof(state_path, prompt)
    return complete, bad


RECEIPT_NAME = "receipt.json"
FINALIZATION_NAME = "finalization.json"
PKG_DIR = os.path.join(_X, "kfields_key_a4", "phase1")

#: Every immutable receipt field. `states` is the ONLY appendable one, and the
#: same expectation writes a receipt and later checks it (Codex SEQ 1363 #2).
RECEIPT_IMMUTABLE = ("run_id", "door", "attempt", "allowed", "parent",
                     "transport", "rules_sha256", "manifest_sha256",
                     "a3_binding", "prompts")


def _pkg(pkg):
    """THE package context (Codex SEQ 1488 item 1): the frozen phase-one
    package by default, or the supplied {dir, items} of a targeted package.
    Every lifecycle owner below reads its items and manifest from here and
    nowhere else, so one lifecycle serves both.

    The caller still cannot choose a subset (the SEQ 1363 law): a supplied
    context is accepted only if its items are exactly the BUILT package's
    items in the named directory, by packet id, order and prompt hash. A
    narrowed, reordered or foreign item list refuses here, before any gate."""
    if pkg is None:
        return {"dir": PKG_DIR, "items": phase1_items()}
    items = list(pkg["items"])
    rows = _load(os.path.join(pkg["dir"], "phase1.manifest.json")).get("items") or []
    if [r.get("packet_id") for r in rows] != [i["packet_id"] for i in items] or \
            any(r.get("prompt_sha256") != _sha(phase1_prompt(i))
                for r, i in zip(rows, items)):
        raise ValueError("the package context is not the package built at %s; "
                         "the caller cannot choose the items" % pkg["dir"])
    return {"dir": pkg["dir"], "items": items}


def _canonical_keys(pkg):
    """THE denominator. One key per item of the package, in its order."""
    return [i["packet_id"] for i in _pkg(pkg)["items"]]


def canonical_keys():
    return _canonical_keys(None)


def _expected_receipt(run_dir, attempt, keys, parent, pkg):
    """THE typed expectation. Used to WRITE a receipt and to CHECK one."""
    ctx = _pkg(pkg)
    items = {i["packet_id"]: i for i in ctx["items"]}
    man = os.path.join(ctx["dir"], "phase1.manifest.json")
    return collections.OrderedDict([
        ("run_id", os.path.basename(os.path.abspath(run_dir))),
        ("door", A4_DOOR), ("attempt", attempt),
        ("allowed", list(keys)),
        ("parent", parent),
        ("transport", _transport_block()),
        ("rules_sha256", _sha(RULES_BLOCK)),
        ("manifest_sha256", INV.sha_file(man) if os.path.isfile(man) else None),
        ("a3_binding", a3_evidence()["binding"]),
        ("prompts", collections.OrderedDict(
            (k, _sha(phase1_prompt(items[k]))) for k in keys)),
        ("states", [])])


def expected_receipt(run_dir, attempt, keys, parent=None):
    return _expected_receipt(run_dir, attempt, keys, parent, None)


def _write_receipt(run_dir, attempt, keys, parent=None, pkg=None):
    receipt = _expected_receipt(run_dir, attempt, keys, parent, pkg)
    os.path.isdir(run_dir) or os.makedirs(run_dir)
    # WRITE-ONCE through the transport's own owner (Codex SEQ 1488 item 4)
    RT.write_new(os.path.join(run_dir, RECEIPT_NAME),
                 json.dumps(receipt, indent=1))
    return receipt


def _expected_for(run_dir, receipt, pkg=None):
    """What THIS run's receipt must be, derived from canon and the parent."""
    attempt = receipt.get("attempt")
    if attempt == 1:
        return _expected_receipt(run_dir, 1, _canonical_keys(pkg), None,
                                 pkg), []
    if attempt != MAX_ATTEMPTS:
        return None, ["attempt %r is outside 1..%d" % (attempt, MAX_ATTEMPTS)]
    pdir = os.path.dirname(os.path.abspath(run_dir))
    pfin = os.path.join(pdir, FINALIZATION_NAME)
    if not os.path.isfile(pfin):
        return None, ["a child with no finalized parent is an orphan"]
    doc = _load(pfin)
    parent = collections.OrderedDict([
        ("run_id", doc.get("run_id")),
        ("finalization_sha256", INV.sha_file(pfin))])
    return _expected_receipt(run_dir, MAX_ATTEMPTS,
                             list(doc.get("retry") or []), parent, pkg), []


def receipt_problems(run_dir, receipt):
    return _receipt_problems(run_dir, receipt, None)


def _receipt_problems(run_dir, receipt, pkg):
    """Why this receipt is not the one the owner would have written."""
    if not isinstance(receipt, dict):
        return ["the receipt is not an object"]
    want, bad = _expected_for(run_dir, receipt, pkg)
    if want is None:
        return bad
    for field in RECEIPT_IMMUTABLE:
        if receipt.get(field) != want[field]:
            bad.append("receipt.%s is not the expected value" % field)
    keys = list(receipt.get("allowed") or [])
    if len(set(keys)) != len(keys):
        bad.append("the receipt names a key twice")
    if not isinstance(receipt.get("states"), list):
        bad.append("receipt.states is not a list")
    if set(receipt) != set(RECEIPT_IMMUTABLE) | {"states"}:
        bad.append("the receipt carries unexpected fields")
    return bad


def prepare_run(run_dir):
    """THE public frozen door: the whole frozen package, nothing else. No
    public parameter can name a directory, items, attempt or subset (Codex
    SEQ 1363; restored at SEQ 1489 item C)."""
    return _prepare_run(run_dir, None)


def _prepare_run(run_dir, pkg):
    """Publish THE canonical primary of a package. It takes nothing but a
    fresh directory and, privately, the complete package context."""
    if os.path.isdir(run_dir) and os.listdir(run_dir):
        return {"ok": False, "problems": ["output directory is not fresh"],
                "invocations": []}
    try:
        _pkg(pkg)
    except ValueError as exc:
        return {"ok": False, "problems": [str(exc)], "invocations": []}
    bad = _preflight(pkg)["problems"]
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    keys = _canonical_keys(pkg)
    _write_receipt(run_dir, 1, keys, pkg=pkg)
    return {"ok": True, "problems": [],
            "invocations": _invocations(keys, 1, pkg)}


def _invocations(keys, attempt, pkg=None):
    """The exact runnable calls, from the one renderer. Never reconstructed."""
    items = {i["packet_id"]: i for i in _pkg(pkg)["items"]}
    return [collections.OrderedDict([
        ("packet_id", k), ("attempt", attempt),
        ("script", render_launcher(items[k], attempt))]) for k in keys]


def record_state(run_dir, state_path):
    """Append ONE unique official state to the receipt, atomically."""
    path = os.path.join(run_dir, RECEIPT_NAME)
    receipt = _load(path)
    real = os.path.abspath(state_path)
    if not os.path.isfile(real):
        return ["no such state: %s" % state_path]
    if real in receipt["states"]:
        return ["that state is already recorded"]
    receipt["states"] = list(receipt["states"]) + [real]
    tmp = path + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(json.dumps(receipt, indent=1))
    os.replace(tmp, path)
    return []


#: Outcomes. Only the two RETRYABLE ones may ever earn the single child.
#: The one proved-transport phrase, named once so the prover and the run
#: owner cannot drift apart.
NO_ANSWER = "the worker was launched and never answered"

RETRYABLE = ("invalid_response", "transport_no_answer")


#: THE A4 result object, exactly as the one-agent launcher returns it. A
#: one-agent Workflow puts the returned value directly on `.result` (precedent:
#: the inventory run wf_a96a6985-aa2, whose `.result` IS its returned string),
#: so there is no `results` list here and no adapter for one.
RESULT_FIELDS = ("packet_id", "source_id", "attempt", "model", "effort",
                 "agentType", "text")


def direct_result(doc):
    """The returned object, or None when the state carries no readable one."""
    r = doc.get("result") if isinstance(doc, dict) else None
    return r if isinstance(r, dict) else None


def _spawned_transcripts(session_dir, run_id):
    """Every agent transcript this Workflow run spawned, if any."""
    d = os.path.join(session_dir or "", "subagents", "workflows", run_id)
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.startswith("agent-") and f.endswith(".jsonl")]


def run_evidence(run_dir, receipt):
    return _run_evidence(run_dir, receipt, None)


def _state_label(doc):
    """The one scheduled label an official state names, or None."""
    rows = [r for r in ((doc if isinstance(doc, dict) else {})
                        .get("workflowProgress") or [])
            if isinstance(r, dict) and r.get("type") == "workflow_agent"]
    return rows[0].get("label") if len(rows) == 1 else None


def _stored_matches(path, text):
    """STORED ANSWER IDENTITY (Codex SEQ 1489 item A). -> None when nothing
    is stored, True when the stored bytes ARE the official text, False for
    different, unreadable or undecodable bytes. Nothing is ever written or
    replaced here; the caller writes only on None and credits only on True."""
    if not os.path.exists(path):
        return None
    try:
        with io.open(path, encoding="utf-8", newline="") as fh:
            return fh.read() == text
    except (OSError, ValueError):
        return False


def _run_evidence(run_dir, receipt, pkg):
    """THE run-level proof. -> {label: (outcome, why, text)}, problems

    ORDER IS THE LAW HERE. The COMMON checks - official location and bound
    parent session, filename/runId, completed status, one scheduled row, the
    reviewed launcher embedded and at its path, run uniqueness, and the exact
    A4 returned object identity - all run BEFORE anything branches on the row
    state. An earlier version branched on a structured error row first, so a
    hand-written file in /tmp could earn the one paid retry without ever being
    proved official (Codex SEQ 1365). Only after the common checks are clean
    may a row become a done answer or a genuine pre-agent rejection.
    """
    ctx = _pkg(pkg)
    items = {i["packet_id"]: i for i in ctx["items"]}
    pinned = {}
    man = os.path.join(ctx["dir"], "phase1.manifest.json")
    if os.path.isfile(man):
        pinned = {r["packet_id"]: r for r in _load(man)["items"]}
    attempt = receipt.get("attempt")
    out, problems = collections.OrderedDict(), []
    runs, agents, responses = set(), set(), set()

    def _refuse(label, why, bad):
        problems.extend("%s: %s" % (label, b) for b in bad or [why])
        out[label] = ("unproved", why, None)

    for state in receipt.get("states") or []:
        run_id = (os.path.splitext(os.path.basename(state))[0]
                  if isinstance(state, str) else "unreadable")
        bad = []
        try:
            doc = _load(state)
        except Exception as exc:                      # noqa: BLE001 - by design
            problems.append("%s: state is unreadable (%s)"
                            % (run_id, str(exc)[:80]))
            continue
        if not isinstance(doc, dict):
            problems.append("%s: state is not an object" % run_id)
            continue

        # ---- COMMON CHECK 1: it must be an official state of this session
        session_dir, session_id = AUD._official_location(state)
        if session_dir is None:
            bad.append("the state is not where the runtime puts an official one")
        elif session_id != PARENT_SESSION:
            bad.append("parent session %r is not the frozen one" % session_id)
        if doc.get("runId") != run_id:
            bad.append("state runId %r is not its own official name"
                       % doc.get("runId"))
        if doc.get("runId") in runs:
            bad.append("run id %r is reused" % doc.get("runId"))
        runs.add(doc.get("runId"))
        if doc.get("status") != "completed":
            bad.append("state status is %r" % doc.get("status"))

        rows = [r for r in (doc.get("workflowProgress") or [])
                if r.get("type") == "workflow_agent"]
        if len(rows) != 1:
            problems.append("%s: %d agent rows; phase 1 runs exactly one"
                            % (run_id, len(rows)))
            continue
        row = rows[0]
        label = row.get("label")
        item = items.get(label)
        if item is None:
            problems.append("%s: names %r, which is not a scheduled item"
                            % (run_id, label))
            continue
        if label in out:
            problems.append("%s: %s was already served" % (run_id, label))
            continue

        # ---- COMMON CHECK 2: the reviewed BASE launcher, then THIS attempt's
        # The frozen manifest pins the reviewed base (attempt-1) rendering and
        # never moves, so it is checked against that base. The official state
        # must separately carry the rendering for the attempt its own receipt
        # binds. A lawful attempt 2 therefore changes only the bound attempt
        # identity, and attempt 3 is still impossible at the receipt
        # (Codex SEQ 1370 ruling 2).
        base_script = render_launcher(item, 1)
        if pinned.get(label, {}).get("script_sha256") not in (None,
                                                              _sha(base_script)):
            bad.append("the manifest pins a different base launcher for this key")
        want_script = render_launcher(item, attempt)
        if doc.get("script") != want_script:
            bad.append("the state did not run the pinned launcher bytes")
        sp = doc.get("scriptPath")
        if sp is not None:
            if not (isinstance(sp, str) and os.path.isfile(sp)):
                bad.append("scriptPath %r is not a readable file" % sp)
            elif INV.sha_file(sp) != _sha(want_script):
                bad.append("the scriptPath bytes are not the pinned launcher")

        # ---- COMMON CHECK 3: the exact A4 returned object identity
        got = direct_result(doc)
        if got is None:
            bad.append("the state carries no returned result object")
        else:
            if set(got) != set(RESULT_FIELDS):
                bad.append("the returned object's keys are %s, not exactly %s"
                           % (sorted(got), sorted(RESULT_FIELDS)))
            for field, want in (("packet_id", label),
                                ("source_id", item["source_id"]),
                                ("attempt", attempt), ("model", MODEL),
                                ("effort", EFFORT),
                                ("agentType", AGENT_TYPE)):
                if got.get(field) != want:
                    bad.append("result %s is %r, not %r"
                               % (field, got.get(field), want))

        # ---- ONLY NOW may the row state decide anything
        if row.get("state") == "done":
            if row.get("agentId") in agents:
                bad.append("agent id %r is reused" % row.get("agentId"))
            agents.add(row.get("agentId"))
            final, complete, why = _official_proof(state, phase1_prompt(item))
            bad += why
            tp = os.path.join(session_dir or "", "subagents", "workflows",
                              run_id, "agent-%s.jsonl" % row.get("agentId"))
            recs = AUD._jsonl(tp) if os.path.isfile(tp) else None
            if recs is None:
                bad.append("the transcript cannot be read whole")
            else:
                if {r.get("agentId") for r in recs} != {row.get("agentId")}:
                    bad.append("a transcript record carries a foreign agentId")
                if {r.get("sessionId") for r in recs} != {PARENT_SESSION}:
                    bad.append("a transcript record carries a foreign sessionId")
                ids = {(r.get("message") or {}).get("id") for r in recs
                       if r.get("type") == "assistant"}
                if ids & responses:
                    bad.append("a response id is reused across the run")
                responses |= ids
            if got is not None and got.get("text") != final:
                bad.append("the returned text is not the proved final segment")
            if bad:
                _refuse(label, bad[0], bad)
                continue
            out[label] = ("proved", "", complete)     # only COMPLETE is parsed
            continue

        # ---- a GENUINE pre-agent rejection: the runtime's own structured
        # evidence, a null-text returned object, and NO worker at all
        if row.get("state") == "error":
            bad += AUD._rejection(row, AGENT_TYPE, EFFORT)
            if got is not None and got.get("text") is not None:
                bad.append("a lane rejected before any model response cannot "
                           "carry answer text")
            # PRE-AGENT MEANS NO WORKER AT ALL. Looking inside for an
            # assistant row was too weak: a transcript carrying only a user
            # record still proves a worker was spawned, which contradicts a
            # lane rejected before any model response. The artifact's mere
            # existence is the contradiction, so nothing here parses it
            # (Codex SEQ 1366).
            if _spawned_transcripts(session_dir, run_id):
                bad.append("a lane rejected before any model response cannot "
                           "have spawned a worker transcript")
            # EXACTLY JSON INTEGER ZERO. `(x or 0) != 0` accepted absent,
            # null, false, "", [], {} and 0.0 alike - missing or wrongly typed
            # evidence cannot prove zero tool use (Codex SEQ 1367).
            if not _recorded_zero(doc.get("totalToolCalls")):
                bad.append("totalToolCalls is %r, not a recorded integer zero, "
                           "so zero tool use is not proved"
                           % (doc.get("totalToolCalls"),))
            if bad:
                _refuse(label, bad[0], bad)
                continue
            out[label] = ("transport_no_answer", NO_ANSWER, None)
            continue

        why = "the agent row is %r, not 'done'" % row.get("state")
        _refuse(label, why, bad + [why])
    return out, problems


def finalize(run_dir):
    """THE public frozen closeout door; see prepare_run."""
    return _finalize(run_dir, None)


def _finalize(run_dir, pkg):
    """Raw first, then the run-level proof, then parse. One outcome per item.
    Raw bytes, proved answers and the finalization are written ONCE through
    the transport's own write-once owner (Codex SEQ 1488); an already stored
    answer counts only when its bytes equal the official text (SEQ 1489 A)."""
    receipt = _load(os.path.join(run_dir, RECEIPT_NAME))
    attempt = receipt.get("attempt")
    raw_dir = os.path.join(run_dir, "raw")
    os.path.isdir(raw_dir) or os.makedirs(raw_dir)

    # ---- PAID BYTES FIRST, before any receipt, identity or parse check.
    harvested, mismatch = [], collections.OrderedDict()
    for state in receipt.get("states") or []:
        run_id = (os.path.splitext(os.path.basename(state))[0]
                  if isinstance(state, str) else "unreadable")
        try:
            doc = json.loads(_read(state))
            got = direct_result(doc)
        except Exception:                             # noqa: BLE001 - by design
            doc, got = None, None
        label = _state_label(doc)
        for n, text in enumerate([got.get("text")] if got else []):
            if not isinstance(text, str):
                continue
            name = "%s.%03d" % (run_id, n)
            path = os.path.join(raw_dir, RT._raw_filename(name))
            same = _stored_matches(path, text)
            if same is None:
                RT.save_raw(text, raw_dir, name)
            elif same is False:
                mismatch[label or run_id] = ("the stored raw answer %s is not "
                                             "the official returned text"
                                             % os.path.basename(path))
            harvested.append(os.path.basename(path))

    receipt_bad = _receipt_problems(run_dir, receipt, pkg)
    allowed = list(receipt.get("allowed") or [])
    items = {i["packet_id"]: i for i in _pkg(pkg)["items"]}

    # A receipt fault preserves raw and stops everything else: no parse, no
    # credit, no child (Codex SEQ 1363 item 2).
    if receipt_bad:
        proved, problems, outcomes = {}, [], collections.OrderedDict(
            (k, ("unproved", "the receipt is not the owner's")) for k in allowed)
    else:
        proved, problems = _run_evidence(run_dir, receipt, pkg)
        outcomes = collections.OrderedDict()
        for label, (state, why, text) in proved.items():
            if state != "proved" or label in mismatch:
                outcomes[label] = (state, why) if state != "proved" \
                    else ("unproved", mismatch[label])
                continue
            path = os.path.join(raw_dir, "%s.attempt%s.proved.json"
                                % (label.replace("#", "_"), attempt))
            same = _stored_matches(path, text)
            if same is None:
                RT.write_new(path, text)
            elif same is False:
                mismatch[label] = ("the stored proved answer %s is not the "
                                   "official returned text"
                                   % os.path.basename(path))
                outcomes[label] = ("unproved", mismatch[label])
                continue
            _obj, bad = read_reply(text, items[label])
            outcomes[label] = ("valid", "") if not bad \
                else ("invalid_response", bad[0])
    # A STORED ANSWER THAT IS NOT THE OFFICIAL TEXT is a run-level fault: the
    # answer is unproved, the run incomplete, and no child may follow.
    for label, why in mismatch.items():
        if label in allowed:
            outcomes[label] = ("unproved", why)
        problems.append("%s: %s" % (label, why))
    for key in allowed:
        outcomes.setdefault(key, ("missing", "no official state"))

    counts = collections.Counter(o for o, _w in outcomes.values())
    ledger = collections.OrderedDict(
        [("scheduled", len(allowed))]
        + [(name, counts.get(name, 0)) for name in
           ("valid", "invalid_response", "transport_no_answer", "unproved",
            "missing")])

    # ---- THE CHILD GATE. A child may only follow a COMPLETE, clean primary:
    # every scheduled key terminal and proved, nothing missing, unproved or
    # problematic anywhere (Codex SEQ 1363 item 3).
    complete = (not receipt_bad and not problems
                and set(outcomes) == set(allowed)
                and counts.get("missing", 0) == 0
                and counts.get("unproved", 0) == 0)
    retry = [k for k in allowed
             if outcomes[k][0] in RETRYABLE] if complete else []
    if attempt != 1:
        retry = []

    doc = collections.OrderedDict([
        ("door", A4_DOOR), ("attempt", attempt),
        ("run_id", receipt.get("run_id")),
        ("receipt_sha256", INV.sha_file(os.path.join(run_dir, RECEIPT_NAME))),
        ("rules_sha256", receipt.get("rules_sha256")),
        ("a3_binding", receipt.get("a3_binding")),
        ("harvested_raw", harvested),
        ("primary_complete", complete),
        ("problems", receipt_bad + problems),
        ("outcomes", [[k, o, w] for k, (o, w) in outcomes.items()]),
        ("ledger", ledger),
        ("retry", retry)])
    # WRITE-ONCE: a second closeout of the same run is refused here, and the
    # first bytes stay (Codex SEQ 1488 item 1).
    RT.write_new(os.path.join(run_dir, FINALIZATION_NAME),
                 json.dumps(doc, indent=1))

    child = _publish_child(run_dir, doc, pkg)
    if child:
        doc["child"] = child
    return doc


def _publish_child(primary_dir, doc, pkg=None):
    """At most ONE parent-bound child, published here, and RUNNABLE.

    The operator never reconstructs a script or a key: the exact validated
    invocations come back from the same renderer and receipt owner.
    """
    keys = list(doc.get("retry") or [])
    if not keys or doc.get("attempt") != 1 or not doc.get("primary_complete"):
        return None
    child_dir = os.path.join(primary_dir, "retry")
    if os.path.isdir(child_dir) and os.listdir(child_dir):
        return None
    _write_receipt(child_dir, MAX_ATTEMPTS, keys,
                   parent=collections.OrderedDict([
                       ("run_id", doc["run_id"]),
                       ("finalization_sha256", INV.sha_file(
                           os.path.join(primary_dir, FINALIZATION_NAME)))]),
                   pkg=pkg)
    receipt = _load(os.path.join(child_dir, RECEIPT_NAME))
    bad = _receipt_problems(child_dir, receipt, pkg)
    if bad:                                   # never hand back an unlawful child
        return None
    return {"dir": child_dir, "problems": [],
            "invocations": _invocations(keys, MAX_ATTEMPTS, pkg)}


def preflight():
    return _preflight(None)


def _preflight(pkg):
    """The ONE gate that must pass before any phase-1 call is made; the
    package context only chooses WHICH items' locators and launchers it
    checks, never which proofs run."""
    problems = []
    ev = a3_evidence()
    problems += ev["problems"]
    hist = historical_package()
    problems += hist["problems"]
    mat = materialize()
    problems += mat["problems"]
    if _sha(mat["inventory_text"]) != INV.sha_file(INV.INV):
        problems.append("the materialization no longer reproduces the signed "
                        "inventory")
    problems += final_boundary_problems(mat["records"])
    problems += lock_problems(lock())
    if a3_dependency_digest() != _load(A3_BASELINE)["digest"]:
        problems.append("an A3 dependency byte moved")
    problems += ["A3 re-audit: %s" % p for p in a3_problems()]

    calls, over = 0, []
    if not problems:
        for item in _pkg(pkg)["items"]:
            calls += 1
            problems += locator_problems(item)
            if len(item["a3_drafts"]) != 2:
                problems.append("%s: %d drafts" % (item["packet_id"],
                                                   len(item["a3_drafts"])))
            n = len(render_launcher(item).encode("utf-8"))
            if n >= TRANSPORT_LIMIT:
                over.append(item["packet_id"])
        if pkg is None and calls != len(_load(INV.INV)["records"]):
            problems.append("the denominator is %d, not the signed record count"
                            % calls)
    if over:
        problems.append("%d launcher scripts are at or over the transport limit"
                        % len(over))
    return {"calls": calls, "problems": problems,
            "budget": _budget_block(calls)}
