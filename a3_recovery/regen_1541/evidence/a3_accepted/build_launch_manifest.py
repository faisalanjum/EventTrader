"""Generate the K-fields drafting LAUNCH MANIFEST (machine-checkable plan).

The plan: 36 events x EXACTLY {one sonnet + one opus} lane each — 72 workers —
every lane effort=high on agentType=lean-probe (Read-only: structural
blindness), byte-identical prompts except the model slot, raw-text replies,
pinned to the LIVE contract/wrapper/protocol hashes at generation time.
Deterministic: same frozen inputs + same pinned files -> same manifest bytes.
Run from experiments/:  venv/bin/python harness/build_launch_manifest.py
"""
import io
import hashlib
import json
import collections
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
# IMPORT FROM THE TREE THIS FILE BELONGS TO. A reproducible build runs a COPY of
# this generator; without this the copy imported `driver.core` from whatever
# tree happened to be on the path and silently built against different code.
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def _assert_own_tree():
    """Refuse to build against a tree that lacks what A1 needs.

    A1's reader is EXPERIMENT-owned (Codex SEQ 1313): production carries none of
    it until Step 3 moves it, so the surface to check is `a1_reader`, not
    `driver.core.slice_menu`. Core is still checked for what A1 genuinely reuses.
    """
    import a1_reader
    from driver.core import prepared_fact_v2 as _pf2
    if not hasattr(a1_reader, "readable_menu"):
        raise SystemExit("refusing to build: a1_reader has no readable_menu")
    if not hasattr(_pf2, "verify_occurrence"):
        raise SystemExit("refusing to build: driver.core.prepared_fact_v2 at %s "
                         "has no verify_occurrence — a stale tree is on the path"
                         % getattr(_pf2, "__file__", "?"))
    from driver.core import slice_menu
    # A reproducible-build COPY legitimately shares the worktree's `driver`
    # package (it imports top-level siblings and cannot be copied whole), so the
    # check is on the SURFACE this generator needs, not on a path. Without it a
    # stale `driver` on the path built silently against different code.
    if not hasattr(slice_menu, "classify_axis"):
        raise SystemExit("refusing to build: driver.core.slice_menu at %s has "
                         "no classify_axis — a stale tree is on the path"
                         % getattr(slice_menu, "__file__", "?"))
KF = os.path.join(_HERE, "..", "keys", "K-fields")
INPUTS = os.path.join(KF, "draft_inputs")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


#: STEP3 §3 — the OD-11 replacement stays DISABLED and is recorded as such, so
#: "all 36 events AND the disabled contingency are accounted for" is a fact in
#: the artifact rather than an absence nobody can check. It may be PROPOSED only
#: after later drafting finds fewer than the official number of sequential-basis
#: facts, and then needs a new versioned record and review. No general
#: substitution engine exists or is implied.
OD11_CONTINGENCY = {
    "id": "OD-11 ULTA -> LUV replacement",
    "enabled": False,
    "may_be_proposed_only_if": "later drafting finds FEWER than the official "
                               "number of sequential-basis facts",
    "then_requires": "a new versioned record and review",
    "substitution_engine": None,
}


def _assemble(events, instruction_name):
    """The COMPLETE preassembled prompt per event — ONE owner, both plans.

    STEP 3 §2: the trusted launcher assembles it here and embeds it, so a worker
    receives that string and nothing else — no repository path, no file to read.
    The body is a Step-2 builder output; only the event view is substituted, at
    the builder's own placeholder. Parameterised by INSTRUCTION rather than
    copied, because the reader plan needs the producer instruction while the
    K-fields plan needs the drafter one (Codex SEQ 1145.2).
    """
    import build_exp5_contract as _bec
    body = open(os.path.join(_HERE, instruction_name), encoding="utf-8").read()
    assert _bec.EVENT_PLACEHOLDER in body, (
        f"{instruction_name} has no event placeholder")
    out = {}
    for e in events:
        raw = json.load(open(os.path.join(_REPO, e["input_path"]),
                             encoding="utf-8"))
        # ONLY the WorkOrder-authorized view. Absent by construction: gold,
        # current-filing XBRL, realized returns, future evidence, secrets, paths.
        view = {k: raw[k] for k in ("source_id", "ticker", "event_date",
                                    "fye_month", "menu_tokens", "text_parts")}
        out[e["source_id"]] = body.replace(
            _bec.EVENT_PLACEHOLDER, json.dumps(view, sort_keys=True, indent=1))
    return out


def _events():
    """The locked event rows — ONE owner, shared by both plans."""
    events = []
    for fn in sorted(os.listdir(INPUTS)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(INPUTS, fn)
        d = json.load(open(p))
        events.append({
            "source_id": d["source_id"], "ticker": d["ticker"],
            # REPO-RELATIVE, resolved by the caller from the repository root.
            # `os.path.abspath` wrote 36 copies of one machine's home directory
            # into a committed artifact, so the manifest was wrong in every other
            # checkout — and regenerating it rewrote all 36 lines, which is how a
            # test came to modify tracked files without anyone noticing. The test
            # compared two builds to EACH OTHER and never to the commit.
            "input_path": os.path.relpath(p, _REPO), "input_sha256": _sha(p),
            })
    return events


def slice_template():
    with io.open(os.path.join(_HERE, "launch_kfields_a1_slice.template.js"),
                 encoding="utf-8") as fh:
        tmpl = fh.read()
    if "__SLICE__" not in tmpl:
        raise SystemExit("slice template placeholder missing")
    return tmpl


def render_launcher(sid, pks, ev, heads, slices, runtime_model_id, tmpl=None):
    """THE launcher renderer, pure. Build writes what this returns; preflight
    re-renders and compares bytes, which is how a wrong frozen launcher
    substituted for a source is caught (Codex SEQ 1313 item 5)."""
    import raw_transport as _rt
    tmpl = slice_template() if tmpl is None else tmpl
    block = ("const MAX_OUTPUT_TOKENS_SETTING = "
             + json.dumps(MAX_OUTPUT_TOKENS_SETTING) + "\n"
             "const ALLOWED_ATTEMPTS = "
             + json.dumps(list(range(1, _rt.A1_MAX_ATTEMPTS + 1))) + "\n"
             "const INPUT_SHA = " + json.dumps(ev["input_sha256"]) + "\n"
             "const RUNTIME_MODEL_ID = " + json.dumps(runtime_model_id) + "\n"
             # the committed launcher can never call: only the run coordinator
             # substitutes a receipt, and only after a passing preflight
             "const RECEIPT = null\n"
             "const PROMPT_SHA = "
             + json.dumps({p["packet_id"]: p["prompt_sha256"]
                           for p in pks}) + "\n"
             "const PINNED_MODEL = " + json.dumps(PINNED_MODEL) + "\n"
             "const PINNED_EFFORT = " + json.dumps(PINNED_EFFORT) + "\n"
             "const PINNED_AGENT_TYPE = "
             + json.dumps(PINNED_AGENT_TYPE) + "\n"
             "const EXPECTED_LANES_PER_PACKET = "
             + json.dumps(LANES_PER_PACKET) + "\n"
             "const SOURCE_ID = " + json.dumps(sid) + "\n"
             "const INPUT_PATH = " + json.dumps(ev["input_path"]) + "\n"
             "const HEAD = " + json.dumps(heads[sid]) + "\n"
             "const ITEMS = " + json.dumps(
                 {q["packet_id"]: slices[q["packet_id"]] for q in pks},
                 sort_keys=True) + "\n"
             "const LANES = " + json.dumps(
                 {q["packet_id"]: q["lanes"] for q in pks}, sort_keys=True))
    return tmpl.replace("__SLICE__", block)


def derive_expected(runtime_model_id=None):
    """THE pure ordered derivation, from the FROZEN INVENTORY outward:

        inventory records -> packets -> ordered (packet, lane) calls ->
        per-source launcher bytes -> exact prompt bytes.

    Build and preflight both call this. Nothing here reads the plan's own
    totals, which is exactly how a coherent 168-to-167 truncation with matching
    budgets passed before (Codex SEQ 1313 item 5).
    """
    events = _events()
    packets, prompts = _one_item_packets(events)
    heads, slices = slice_prompts(packets, prompts)
    by_event = collections.OrderedDict()
    for pk in packets:
        by_event.setdefault(pk["source_id"], []).append(pk)
    tmpl = slice_template()
    launchers = {}
    for sid, pks in by_event.items():
        ev = [e for e in events if e["source_id"] == sid][0]
        launchers[sid] = render_launcher(sid, pks, ev, heads, slices,
                                         runtime_model_id, tmpl)
    # the COMPLETE expected bundle rows, built exactly as `build` builds them,
    # so preflight compares the whole thing instead of selected projections
    bundle_slices = []
    for sid, pks in by_event.items():
        ev = [e for e in events if e["source_id"] == sid][0]
        text = launchers[sid]
        raw = text.encode("utf-8")
        bundle_slices.append({
            "source_id": sid,
            "launcher": os.path.relpath(os.path.join(
                _HERE, "launchers_a1", "kfields_a1_%s.workflow.js" % sid), _REPO),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "input_path": ev["input_path"], "input_sha256": ev["input_sha256"],
            "packets": [{"packet_id": q["packet_id"],
                         "prompt_sha256": q["prompt_sha256"],
                         "lanes": [l["lane_id"] for l in q["lanes"]]}
                        for q in pks]})
    return {"events": events, "packets": packets, "prompts": prompts,
            "bundle_slices": bundle_slices,
            # the PLAN's order: inventory record order
            "calls": [(pk["packet_id"], l["lane_id"])
                      for pk in packets for l in pk["lanes"]],
            # the BUNDLE's order: grouped by source event, which is how the
            # launcher set is written. Derived here so the gate compares the
            # bundle to its own lawful ordering rather than to a different one.
            "bundle_calls": [(pk["packet_id"], l["lane_id"])
                             for pks in by_event.values() for pk in pks
                             for l in pk["lanes"]],
            "order": [sid for sid in by_event],
            "launchers": launchers}


#: A2 freezes the exact runtime identity INDEPENDENTLY. Until that artifact
#: exists, every runtime is NO-GO: a non-null value in the plan is the plan
#: asserting its own approval, which is not approval (Codex SEQ 1313 item D).
A2_RUNTIME_FREEZE = os.path.join(_HERE, "a2_runtime_freeze.json")


def a2_runtime():
    """A2's INDEPENDENTLY frozen runtime identity, or None while it is absent."""
    if not os.path.exists(A2_RUNTIME_FREEZE):
        return None
    with io.open(A2_RUNTIME_FREEZE, encoding="utf-8") as fh:
        return json.load(fh).get("runtime_model_id")


def protected_pin_problems(plan):
    """THE one protected-owner comparison, shared by the pre-call gate and the
    finalizer. Preflight proves the pins BEFORE the calls; the finalizer proves
    them again AFTER them, because the live reader bytes are what decide
    validity and retry once the calls are spent (Codex SEQ 1316 item 8)."""
    bad = []
    live_pins = _protected_pins()
    claimed = (plan.get("pins") or {}) if isinstance(plan, dict) else {}
    for name in sorted(set(live_pins) | set(claimed)):
        if name not in claimed:
            bad.append("pin %s is protected but the plan does not carry it" % name)
        elif name not in live_pins:
            bad.append("pin %s is claimed but is not a protected file" % name)
        elif not os.path.exists(live_pins[name]):
            bad.append("pin %s: the protected file is missing" % name)
        elif claimed[name] != _sha(live_pins[name]):
            bad.append("pin %s: the protected file's bytes changed" % name)
    return bad


def _protected_pins():
    """THE protected contract/source files, by name -> path. ONE owner, so the
    plan and the pre-call gate can never protect different sets."""
    return {
        # THE READER OWNER IS PROTECTED. Replacing its validator with accept-all
        # changed no gate result because nothing pinned it (Codex SEQ 1314 #8).
        "a1_reader": os.path.join(_HERE, "a1_reader.py"),
        "contract": os.path.join(_HERE, "exp5_prompt_drafter.md"),
        "contract_manifest": os.path.join(
            _HERE, "exp5_prompt_contract.manifest.json"),
        "wrapper": os.path.join(KF, "drafting_wrapper.md"),
        "protocol": os.path.join(KF, "protocol.md"),
        "inputs_manifest": os.path.join(KF, "draft_inputs.hashes.json"),
    }


def build():
    events = _events()
    doc = {
        # A NEW, STILL-UNRUN CANDIDATE. The GO #1 whole-event plan and its date
        # remain history at the parent commit; this is not that plan.
        "plan": "K-fields A1 one-item blind drafts",
        "plan_version": "a1-one-item-v1",
        "amendment": "2026-08-18 one-item / four-field owner amendment",
        "events": events,
        "n_events": len(events),
        "pins": {k: _sha(v) for k, v in _protected_pins().items()},
        # SCHEMA BLOCK DELETED (Codex SEQ 1093). It published a COPIED
        # `model_owned_fields` count — a second owner of the item shape. Swapping
        # 37 for another hand-written number would keep the defect and only change
        # its value. The Step-2 builder and its manifest own the shape; what this
        # plan needs is a pin on the exact prompt each worker receives, bound per
        # event below.
        "od11_contingency": OD11_CONTINGENCY,
        "enforced_by": "kf_lint (after raw_transport exact parse)",
        "made_calls": 0,          # DISABLED plan: preparing it makes no call
        # THE DOOR THIS PLAN EXECUTES (B-13). Written here so the approved plan
        # — not caller memory — decides which contract its replies are checked
        # against, and so the plan can hash the behaviour it will run.
        # THE DOOR NAMES THE PATH THAT ACTUALLY RUNS. `gold` pointed at the old
        # dense gold linter while the prompt requires the sparse four-field
        # reply, so the plan promised a validator that could not accept its own
        # replies (Codex SEQ 1312 item 6).
        "door": "one_item_sparse",
        # DERIVED from the frozen inventory rows. The retired 19/9/72/100
        # accounting belonged to the whole-event plan and is not restated here.
        # THREE SEPARATELY DERIVED NUMBERS. 336 is the PRIMARY count, not the
        # total: the one-invalid-retry rule allows one retry per primary pair.
        "budget": {"primary_calls": None, "retry_cap": None, "all_in_max": None},
        "rules": ["byte-identical prompts across the two blind lanes",
                  "agentType lean-probe = Read-only (Bash/Glob/Grep impossible)",
                  "no Qwen, no Opus, no EXP-5 under A1"],
        # THE SUPPORTED PROCEDURE, naming the commands that actually exist and
        # the interpreter that actually has their dependencies. A launch with a
        # skipped preflight is not supported: the gate exits nonzero and prints
        # every reason, and it is NO-GO until A2 freezes the runtime.
        "procedure": {
            "interpreter": "venv/bin/python3 (the repo environment)",
            "0_note": "the committed launchers under launchers_a1/ carry "
                      "RECEIPT=null and CANNOT call. launch_kfields_drafts."
                      "workflow.template.js is RETIRED and non-runnable. "
                      "`--preflight` is DIAGNOSTIC ONLY: it arms nothing, and "
                      "only a1_prepare_run makes a run callable.",
            "1_prepare": "inv = raw_transport.a1_prepare_run(<fresh_run_dir>)"
                         "['invocations']   # ordered; ok=False writes nothing",
            "2_launch": "for row in inv (IN ORDER): Workflow(scriptPath="
                        "row['scriptPath'], args=row['args'])   # pass those "
                        "bytes UNCHANGED - do not rebuild, reorder or regroup "
                        "them",
            "3_record": "audit_worker_access.record_state(<run_dir>/receipt.json"
                        ", run_id, <official state path>)   # immediately after "
                        "each single invocation, before the next",
            "4_finalize": "raw_transport.a1_finalize(<run_dir>)   # invokes the "
                          "audit itself, saves every raw row before any parse, "
                          "rechecks the protected owners, and writes "
                          "finalization.json",
            "5_retry_prepare": "raw_transport.a1_prepare_retry(<primary_run_dir>)"
                               "   # only if finalization.retry is non-empty; "
                               "keys, attempt and the fixed <primary>/retry "
                               "destination all come from the primary's bytes",
            "6_retry_launch": "repeat steps 2 and 3 for the retry's OWN returned "
                              "invocations",
            "7_retry_finalize": "raw_transport.a1_finalize(<primary_run_dir>/"
                                "retry)   # writes its own finalization with "
                                "retry=[]; there is no third attempt",
            "replay_boundary": "Workflow 2.1.236 exposes no filesystem, import "
                               "or process primitive, so a launcher cannot "
                               "enforce single use by itself. The lawful "
                               "minimum is trusted one-shot orchestration: "
                               "Codex authorises one exact invocation at a "
                               "time; Core invokes each returned invocation "
                               "ONCE, immediately records that one official "
                               "run/state, and waits. A duplicate invocation, "
                               "state or call is fully counted and FAILS the "
                               "package - never credited and never retried. "
                               "This is not a cryptographic single-use claim.",
        },
    }
    # STEP 3 §2 (Codex SEQ 1089): the TRUSTED launcher assembles the COMPLETE
    # prompt here and embeds it. A worker receives that string and nothing else —
    # no repository path, no file to read. The prompt body comes from the ONE
    # Step-2 builder's output; only the event view is appended, LAST, in place of
    # its placeholder. No schema is copied and no second prompt owner is created.
    packets, prompts = _one_item_packets(events)
    doc["packets"] = packets
    doc["n_packets"] = len(packets)
    import raw_transport                       # the ONE retry-limit owner
    doc["n_calls"] = sum(len(p["lanes"]) for p in packets)
    doc["call_ceiling"] = doc["n_calls"]        # the PRIMARY ceiling
    retries = raw_transport.A1_MAX_ATTEMPTS - 1
    doc["budget"]["primary_calls"] = doc["n_calls"]
    doc["budget"]["retry_cap"] = doc["n_calls"] * retries
    doc["budget"]["all_in_max"] = doc["n_calls"] * (1 + retries)
    # THE RUNTIME COMES FROM A2's OWN FROZEN ARTIFACT, never from this builder.
    # While that artifact is absent the plan carries null and the gate is NO-GO;
    # when A2 lands, dropping the file in and rebuilding is the whole change.
    doc["runtime_model_id"] = a2_runtime()
    doc["inventory_sha256"] = _sha(INVENTORY)
    doc["source_manifest_sha256"] = _sha(os.path.join(
        KF, "draft_inputs.hashes.json"))
    doc["measured_capacity"] = measured_capacity(packets, prompts)
    doc["transport"] = {"runtime": "claude-code", "model": "sonnet",
                        "effort": "high", "agentType": "lean-probe",
                        OUTPUT_TOKENS_VAR: MAX_OUTPUT_TOKENS_SETTING}

    dest = os.path.join(_HERE, "launch_kfields_drafts.manifest.json")
    with open(dest, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    # regenerate the WORKFLOW from the pristine TEMPLATE (idempotent by
    # construction — never patches its own prior output): the locked
    # (source_id -> input_path) table is EMBEDDED; args deviating from the
    # locked plan throw (duplicates, unknown events, swapped inputs).
    # ---- ONE LAUNCHER PER FROZEN SOURCE EVENT, each under the transport limit
    heads, slices = slice_prompts(packets, prompts)
    lane_dir = os.path.join(_HERE, "launchers_a1")
    if os.path.isdir(lane_dir):
        for old in sorted(os.listdir(lane_dir)):
            os.remove(os.path.join(lane_dir, old))
    else:
        os.makedirs(lane_dir)
    tmpl = open(os.path.join(_HERE, "launch_kfields_a1_slice.template.js"),
                encoding="utf-8").read()
    assert "__SLICE__" in tmpl, "slice template placeholder missing"
    by_event = collections.OrderedDict()
    for pk in packets:
        by_event.setdefault(pk["source_id"], []).append(pk)
    slice_rows = []
    for sid, pks in by_event.items():
        ev = [e for e in events if e["source_id"] == sid][0]
        text = render_launcher(sid, pks, ev, heads, slices,
                               doc.get("runtime_model_id"), tmpl)
        name = "kfields_a1_%s.workflow.js" % sid
        path = os.path.join(lane_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        size = os.path.getsize(path)
        if size >= WORKFLOW_MAX_BYTES:
            raise SystemExit("%s: launcher is %d bytes, at or over the %d "
                             "transport limit" % (name, size, WORKFLOW_MAX_BYTES))
        slice_rows.append({
            "source_id": sid,
            "launcher": os.path.relpath(path, _REPO),
            "bytes": size, "sha256": _sha(path),
            "input_path": ev["input_path"], "input_sha256": ev["input_sha256"],
            "packets": [{"packet_id": q["packet_id"],
                         "prompt_sha256": q["prompt_sha256"],
                         "lanes": [l["lane_id"] for l in q["lanes"]]}
                        for q in pks]})
    bundle = {
        "bundle": "K-fields A1 one-item launcher set",
        "manifest_sha256": None,          # filled after the manifest is written
        "workflow_max_bytes": WORKFLOW_MAX_BYTES,
        "slices": slice_rows,
        "n_slices": len(slice_rows),
        "n_packets": sum(len(r["packets"]) for r in slice_rows),
        "n_calls": sum(len(q["lanes"]) for r in slice_rows for q in r["packets"]),
        "largest_launcher_bytes": max(r["bytes"] for r in slice_rows)}
    doc["bundle"] = {"path": os.path.relpath(
        os.path.join(_HERE, "launch_kfields_a1.bundle.json"), _REPO)}

    bundle["manifest_sha256"] = _sha(dest)
    bpath = os.path.join(_HERE, "launch_kfields_a1.bundle.json")
    with open(bpath, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=1, sort_keys=True)
    print("manifest:", _sha(dest))
    print("bundle:", _sha(bpath), "slices", bundle["n_slices"],
          "largest", bundle["largest_launcher_bytes"])
    print(f"events={doc['n_events']} packets={doc['n_packets']} "
          f"calls={doc['n_calls']}")
    return dest


def build_reader_plan(events=None):
    """THE SECOND, SEPARATE, DISABLED PLAN — step3 §4 "EXP-5 reader plan".

    Same machinery, its OWN manifest: §4 says these are separate approvals and
    separate manifests and that neither may launch the other, so this shares the
    event/pin builders above and writes a different file. It does NOT extend the
    K-fields manifest, which would let one approval carry both.

    156 producer calls exactly: P1..P4 over all 36 events (144) plus P5
    `opus_ref` over the 12-event h32 subsample (12).

    THE SUBSAMPLE IS LAW, NOT A CHOICE. WorkOrder:172 — "All sampling =
    h32-seeded deterministic shuffle ... seed string recorded in the manifest".
    `key_lint.h32` is the existing owner and is imported, never re-implemented;
    the seed string is written into the manifest so the selection is
    reproducible by anyone without this code.

    MODEL ROLES ARE PINNED, RUNTIME IDS ARE NOT (§4): freezing an alias as
    though it were the final ID is exactly what the WorkOrder forbids.
    """
    import sys
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from key_lint import h32

    if events is None:
        events = _events()
    seed = "exp5_opus_ref_subsample_v1"
    # deterministic h32-seeded shuffle over the source ids, then the first 12
    ordered = sorted(events, key=lambda e: (h32(seed + e["source_id"]),
                                            e["source_id"]))
    subsample = sorted(e["source_id"] for e in ordered[:12])

    arms = [{"arm": "P1", "role": "sonnet_run1", "tier": "sonnet",
             "effort": "high", "active": True, "scope": "all_36"},
            {"arm": "P2", "role": "sonnet_run2", "tier": "sonnet",
             "effort": "high", "active": True, "scope": "all_36"},
            {"arm": "P3", "role": "haiku_run1", "tier": "haiku",
             "effort": "high", "active": True, "scope": "all_36"},
            {"arm": "P4", "role": "haiku_run2", "tier": "haiku",
             "effort": "high", "active": True, "scope": "all_36"},
            {"arm": "P5", "role": "opus_ref", "tier": "opus",
             "effort": "high", "active": True, "scope": "h32_subsample_12"}]
    planned = sum(len(events) if a["scope"] == "all_36" else len(subsample)
                  for a in arms)


    # GENERATED FIRST: `identities` below hashes this launcher, so it must
    # exist before the manifest is assembled.
    # §5: the EXACT assembled prompt for every event — the PRODUCER instruction,
    # not the drafter's (Codex SEQ 1145.2).
    reader_prompts = _assemble(events, "exp5_prompt_producer.md")
    for e in events:
        e["prompt_sha256"] = hashlib.sha256(
            reader_prompts[e["source_id"]].encode("utf-8")).hexdigest()

    # THE GENERATED READER LAUNCHER, from its own pristine template. Same
    # convention as the K-fields launcher: the locked table is EMBEDDED, so args
    # deviating from the approved plan throw rather than silently running.
    expected = {e["source_id"]: e["input_path"] for e in events}
    guard = ("const EXPECTED = " + json.dumps(expected, sort_keys=True) + "\n"
             "if (!Array.isArray(EVENTS)) throw new Error('args must be an array')\n"
             "const ids = EVENTS.map(e => e.source_id)\n"
             "if (new Set(ids).size !== Object.keys(EXPECTED).length ||\n"
             "    ids.length !== Object.keys(EXPECTED).length)\n"
             "  throw new Error(`args must carry EXACTLY the ${Object.keys(EXPECTED).length} locked events, no duplicates`)\n"
             "for (const e of EVENTS) {\n"
             "  const want = EXPECTED[e.source_id]\n"
             "  if (!want) throw new Error(`unknown event ${e.source_id} — not in the locked manifest`)\n"
             "  const got = e.input_path || e.path\n"
             "  if (got !== want) throw new Error(`swapped/wrong input for ${e.source_id}: ${got}`)\n"
             "}")
    guard += "\nconst PROMPTS = " + json.dumps(reader_prompts, sort_keys=True)
    guard += "\nconst ARMS = " + json.dumps(arms, sort_keys=True)
    guard += "\nconst SUBSAMPLE = " + json.dumps(subsample, sort_keys=True)
    guard += "\nconst PLANNED_CALLS = " + str(planned)
    # the launcher emits the hash of the exact prompt each call used, from the
    # SAME table it prompts from — so the evidence cannot disagree with the send
    guard += "\nconst PROMPT_SHA = " + json.dumps(
        {e["source_id"]: e["prompt_sha256"] for e in events}, sort_keys=True)
    # The EXPECTED lock travels with the launcher so the start gate compares the
    # supplied lock against the APPROVED plan, not against a caller's claim.
    guard += "\nconst KFIELDS_LOCK_SHA256 = " + json.dumps(
        doc_kfields_lock := None)
    tmpl = open(os.path.join(_HERE,
                             "launch_exp5_readers.workflow.template.js")).read()
    assert "__GUARD__" in tmpl, "reader template placeholder missing"
    with open(os.path.join(_HERE,
                           "launch_exp5_readers.workflow.js"), "w") as f:
        f.write(tmpl.replace("__GUARD__", guard))

    # STEP3 §5 IDENTITY BINDING. Repo-relative paths, raw file bytes, sorted
    # deterministically, through the SAME `_sha` the K-fields plan uses — not a
    # second fingerprint system. NO credential, machine path, volatile value, or
    # self-referential hash: the manifest never hashes itself.
    def _id(*parts):
        """{path, sha256} — a bare hash cannot be mechanically re-checked
        against the file it names (Codex SEQ 1145.3)."""
        abs_p = os.path.join(_REPO, *parts)
        return {"path": os.path.relpath(abs_p, _REPO), "sha256": _sha(abs_p)}

    def _hid(name):
        return _id(os.path.relpath(os.path.join(_HERE, name), _REPO))
    identities = {
        # authority
        "workorder": _id(".claude/plans/Drivers/FinalDesign/"
                         "FableExperimentWorkOrder.md"),
        "core_foundation": _id(".claude/plans/Drivers/FinalDesign/"
                               "FINAL_DESIGN.md"),
        "staged_v2_contract": _id(".claude/plans/Drivers/FinalDesign/"
                                  "ChannelContractV2.md"),
        # Step 2 owners
        "step2_builder": _hid("build_exp5_contract.py"),
        "step2_instruction_producer": _hid("exp5_prompt_producer.md"),
        "step2_contract_manifest": _hid("exp5_prompt_contract.manifest.json"),
        "step2_checker": _hid("kf_lint.py"),
        # the execution owners this plan will drive
        "reply_transport": _hid("raw_transport.py"),
        "matcher": _id("driver/core/fact_match.py"),
        "scorer": _hid(os.path.join("scorers", "score_exp5.py")),
        "core_route": _id("driver/core/driver_write_cli.py"),
        # THE READER'S OWN launcher, template AND generated. The K-fields
        # template hardcodes 36 x (sonnet+opus) = 72 gold drafts and cannot
        # express P1-P5, so pinning it was pinning the wrong launcher entirely
        # (Codex SEQ 1145.1).
        "launcher_template": _hid("launch_exp5_readers.workflow.template.js"),
        "launcher_generated": _hid("launch_exp5_readers.workflow.js"),
        "tests": _hid("test_harness_guards.py"),
    }
    doc = {
        "identities": {k: identities[k] for k in sorted(identities)},
        "output": {
            "dir": os.path.relpath(os.path.join(_HERE, "runs"), _REPO),
            "no_overwrite": "an existing run directory is NEVER overwritten; a "
                            "second run writes a NEW directory or refuses",
        },
        # THE FUTURE K-FIELDS LOCK DOES NOT EXIST YET (§5). It is NULL, not a
        # final-looking placeholder: a plausible-looking hash here is exactly
        # how an unreviewed lock gets accepted as reviewed.
        "kfields_lock": {
            "sha256": None,
            "runner_rule": "the EXP-5 runner REFUSES TO START until the real "
                           "reviewed K-fields lock hash is supplied here",
        },
        "od11_contingency": OD11_CONTINGENCY,
        "plan": "EXP-5 reader arms (separate approval; NOT GO #1)",
        "events": [{k: e[k] for k in ("source_id", "ticker", "input_path",
                                      "input_sha256", "prompt_sha256")}
                   for e in events],
        "n_events": len(events),
        "arms": arms,
        "opus_ref_subsample": {"seed": seed, "n": len(subsample),
                               "source_ids": subsample,
                               "rule": "h32-seeded deterministic shuffle "
                                       "(WorkOrder:172); key_lint.h32 is the "
                                       "owner and is imported, not restated"},
        "planned_producer_calls": planned,
        "made_calls": 0,               # DISABLED: preparing it makes no call
        "door": "reader",              # producers answer with the plain V2 envelope
        "unions": "same-tier only",
        "withdrawn": ["P6 local-Qwen"],
        "conditional_cheap_fallback": {
            "enabled": False,
            "why": "disabled unless its official trigger fires AND Fable/owner "
                   "separately approve — never enabled by preparing this plan"},
        "model_resolution": {
            "pinned": "ROLES ONLY",
            "rule": "exact runtime model IDs are resolved and written "
                    "immediately before a future approved run (WorkOrder); "
                    "an alias is NEVER frozen as the final ID"},
        "grading": {
            "exact_count": None,
            "why": "grading volume depends on the unmatched facts actually "
                   "produced, so an exact number here would be invented",
            "formula_owner": "WorkOrder EXP-5 grading formula",
            "hard_cap_owner": "WorkOrder EXP-5 grading cap"},
        "separation": "separate approval and separate manifest from "
                      "launch_kfields_drafts.manifest.json; neither plan may "
                      "launch the other",
    }

    dest = os.path.join(_HERE, "launch_exp5_readers.manifest.json")
    with open(dest, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    print("reader manifest:", _sha(dest))
    print(f"arms={len(arms)} planned_producer_calls={planned} made_calls=0")
    return dest



# ---------------------------------------------------------------- A1 ------
# ONE PACKET PER FROZEN INVENTORY RECORD. The old plan sent a whole event to a
# Sonnet lane and an Opus lane. A1 sends the complete ordered event plus exactly
# ONE already-located item, and reads it twice with blind Sonnet lanes. Every
# count is derived from the frozen inventory; no ceiling constant survives.

INVENTORY = os.path.join(_HERE, "..", "one_item_benchmark_inventory.json")


def _packet_item(rec, parts):
    """The one trusted item: EXACTLY the four source-owned fields.

    `source_id` is packet/event identity and is deliberately NOT duplicated
    inside the item. Code binds all four; the model never copies or chooses
    them. Fails closed.
    """
    from driver.core.prepared_fact_v2 import verify_occurrence
    text = parts[rec["part_ref"]]
    why = verify_occurrence(text, rec["quote"], rec["occurrence_in_part"])
    if why:
        raise SystemExit("%s: %s" % (rec["source_id"], why))
    # THE REVIEWED FIELD PASSES THROUGH BYTE FOR BYTE. Deriving it from the
    # quote invented a source fact and made two lawfully distinct items
    # indistinguishable (Codex SEQ 1336).
    label = rec["raw_label_or_claim"]
    if not isinstance(label, str) or not label.strip() or label not in text:
        raise SystemExit("%s: raw_label_or_claim is not exact source text"
                         % rec["source_id"])
    return {"part_ref": rec["part_ref"],
            "occurrence_in_part": rec["occurrence_in_part"],
            "quote": rec["quote"], "raw_label_or_claim": label}


def _one_item_packets(events, role="drafter"):
    """THE packet owner. One packet per frozen inventory record: the byte-
    identical stable rules, the readable menu, the complete ordered event, and
    exactly ONE already-located item last. Returns (packets, prompts)."""
    _assert_own_tree()
    import build_exp5_contract as _bec
    import kf_lint
    import a1_reader
    inv = json.load(open(INVENTORY, encoding="utf-8"))
    fixed = _bec.build_prompt(role)
    # The prefix is everything up to the placeholder; slicing by the placeholder
    # position is exact and does not search data for a marker.
    stable = fixed[:fixed.index(_bec.EVENT_PLACEHOLDER)]
    raws = {}
    for e in events:
        raws[e["source_id"]] = json.load(
            open(os.path.join(_REPO, e["input_path"]), encoding="utf-8"))
        e["menu_tokens_retained"] = list(raws[e["source_id"]]["menu_tokens"])
    by_sid = {e["source_id"]: e for e in events}

    packets, prompts, menu_maps = [], {}, {}
    for n, rec in enumerate(inv["records"]):
        raw = raws[rec["source_id"]]
        parts = kf_lint.part_lookup(rec["source_id"], INPUTS)
        item = _packet_item(rec, parts)
        view = {k: raw[k] for k in ("source_id", "ticker", "event_date",
                                    "fye_month", "text_parts")}
        # ONE deterministic JSON object, ordered menu -> event -> item. No
        # marker text has to be searched for in data that may contain it.
        shown, back = a1_reader.readable_menu(raw["menu_tokens"])
        menu_maps[rec["source_id"]] = back
        payload = {"menu": shown, "event": view, "item": item}
        prompt = stable + json.dumps(payload, indent=1)
        pid = "%s#%03d" % (rec["source_id"], n)
        prompts[pid] = prompt
        packets.append({
            "packet_id": pid,
            "source_id": rec["source_id"],
            "input_path": by_sid[rec["source_id"]]["input_path"],
            "item": item,
            "stable_prefix_chars": len(stable),
            "prompt_chars": len(prompt),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "lanes": [{"lane_id": "%s/L%d" % (pid, i + 1),
                        "model": PINNED_MODEL, "effort": PINNED_EFFORT,
                        "agentType": PINNED_AGENT_TYPE}
                       for i in range(LANES_PER_PACKET)]})
    for e in events:
        e["menu_display_to_original"] = menu_maps.get(e["source_id"], {})
    return packets, prompts


# The transport setting the pinned Claude Code runtime actually reads. It is a
# CONTRACT-OWNED identity, not a tuned threshold: the runtime refuses to emit
# more than this many output tokens, so a plan that runs without it can be
# silently truncated mid-reply and score a lie.
OUTPUT_TOKENS_VAR = "CLAUDE_CODE_MAX_OUTPUT_TOKENS"
MAX_OUTPUT_TOKENS_SETTING = "128000"
#: The pinned runtime identity every lane must carry. `sonnet` is an ALIAS; A2
#: freezes the exact runtime and capacity, and this is not that proof.
PINNED_MODEL = "sonnet"
PINNED_EFFORT = "high"
PINNED_AGENT_TYPE = "lean-probe"
LANES_PER_PACKET = 2


def measured_capacity(packets, prompts):
    """THREE DIFFERENT QUANTITIES, never conflated (Codex SEQ 1311 \u00a75):

    * prompt CHARACTERS and prompt UTF-8 BYTES — measured from the real bytes;
    * runtime INPUT TOKENS — a runtime measurement this plan cannot take before
      the run, so it is null here and A2 freezes it;
    * the maximum-OUTPUT SETTING — a configuration value, not a measurement.
    """
    chars = sorted(p["prompt_chars"] for p in packets)
    byts = sorted(len(prompts[p["packet_id"]].encode("utf-8")) for p in packets)
    out = {"packets": len(chars), "prompt_chars_min": chars[0],
           "prompt_chars_median": chars[len(chars) // 2],
           "prompt_chars_max": chars[-1],
           "prompt_utf8_bytes_min": byts[0],
           "prompt_utf8_bytes_median": byts[len(byts) // 2],
           "prompt_utf8_bytes_max": byts[-1],
           "runtime_input_tokens": None,
           "max_output_tokens_setting": int(MAX_OUTPUT_TOKENS_SETTING)}
    return out


#: The Workflow transport rejects any script at or over this size before args
#: or calls (proved by Core 1019). It is a transport limit, not a tuned number.
WORKFLOW_MAX_BYTES = 524288
ITEM_SLOT = "\n \"item\": "


def slice_prompts(packets, prompts):
    """Split every packet prompt into (shared head, exact item text).

    The head carries the stable instructions, the menu and the event; it is
    IDENTICAL for every packet of the same source event, so a per-event launcher
    stores it once. Byte-exactness is guaranteed because the pieces are cut from
    the real rendered prompt and proved to rejoin.
    """
    heads, slices = {}, {}
    for pk in packets:
        full = prompts[pk["packet_id"]]
        cut = full.rindex(ITEM_SLOT) + len(ITEM_SLOT)
        head, body = full[:cut], full[cut:]
        prior = heads.setdefault(pk["source_id"], head)
        if prior != head:
            raise SystemExit("%s: packets of one event disagree on the shared "
                             "head" % pk["source_id"])
        slices[pk["packet_id"]] = body
        if head + body != full:
            raise SystemExit("%s: slice does not rejoin" % pk["packet_id"])
    return heads, slices


def preflight(env=None, run_dir=None):
    """THE PRE-CALL GATE. Returns every reason this launch must NOT run.

    Everything is RE-DERIVED from the frozen inventory outward by
    `derive_expected()`; the plan's own totals are never trusted, which is what
    let a coherent 168-to-167 truncation with matching budgets pass before. Top
    level shapes are checked BEFORE any `.get`, ordered lists are compared with
    multiplicity before any set, and a malformed structure yields a reason
    instead of a traceback.
    """
    import raw_transport
    env = os.environ if env is None else env
    bad = []

    def _guard(label, fn):
        try:
            fn()
        except Exception as exc:                      # noqa: BLE001 - by design
            bad.append("%s: malformed input (%s: %s)"
                       % (label, type(exc).__name__, exc))

    if run_dir is None:
        bad.append("no run directory given - a fresh output directory is "
                   "required, and a run that skips it cannot be audited")
    elif os.path.exists(run_dir) and os.listdir(run_dir):
        bad.append("output directory is not fresh: %s" % run_dir)

    got = env.get(OUTPUT_TOKENS_VAR)
    if got != MAX_OUTPUT_TOKENS_SETTING:
        bad.append("%s is %r, not the pinned %r; replies could be silently "
                   "truncated" % (OUTPUT_TOKENS_VAR, got,
                                  MAX_OUTPUT_TOKENS_SETTING))

    mpath = os.path.join(_HERE, "launch_kfields_drafts.manifest.json")
    bpath = os.path.join(_HERE, "launch_kfields_a1.bundle.json")
    for label, path in (("manifest", mpath), ("bundle", bpath),
                        ("inventory", INVENTORY)):
        if not os.path.exists(path):
            bad.append("%s is missing: %s" % (label, path))
    if any("is missing" in b for b in bad):
        return bad
    try:
        plan = json.load(open(mpath, encoding="utf-8"))
        bundle = json.load(open(bpath, encoding="utf-8"))
    except Exception as exc:                          # noqa: BLE001 - by design
        return bad + ["manifest/bundle is not readable JSON: %s" % exc]

    # SHAPES BEFORE ANY `.get`: a top-level list would raise AttributeError and
    # take the whole gate down instead of refusing.
    for label, obj in (("manifest", plan), ("bundle", bundle)):
        if not isinstance(obj, dict):
            bad.append("%s top level is %s, not an object"
                       % (label, type(obj).__name__))
    if bad and any("top level is" in b for b in bad):
        return bad
    for label, obj, key, kind in (("manifest", plan, "packets", list),
                                  ("manifest", plan, "events", list),
                                  ("manifest", plan, "budget", dict),
                                  ("manifest", plan, "pins", dict),
                                  ("bundle", bundle, "slices", list)):
        if not isinstance(obj.get(key), kind):
            bad.append("%s.%s is %s, not %s"
                       % (label, key, type(obj.get(key)).__name__,
                          kind.__name__))
    if any(" is " in b and ", not " in b for b in bad):
        return bad

    # --- THE RUNTIME IS NOT FROZEN, AND A PLAN CANNOT FREEZE ITSELF ---------
    if not os.path.exists(A2_RUNTIME_FREEZE):
        bad.append("the exact runtime is unresolved: A2 has frozen no runtime "
                   "identity (%s is absent), so %r remains an alias and every "
                   "runtime is NO-GO - a non-null value in the plan is not "
                   "approval" % (os.path.basename(A2_RUNTIME_FREEZE),
                                 PINNED_MODEL))
    else:
        frozen = json.load(open(A2_RUNTIME_FREEZE, encoding="utf-8"))
        if plan.get("runtime_model_id") != frozen.get("runtime_model_id"):
            bad.append("the plan's runtime %r is not A2's frozen runtime %r"
                       % (plan.get("runtime_model_id"),
                          frozen.get("runtime_model_id")))

    if plan.get("made_calls") != 0:
        bad.append("the plan records prior calls: made_calls=%r"
                   % plan.get("made_calls"))
    if plan.get("door") != raw_transport.A1_DOOR:
        bad.append("the plan names door %r, but A1 replies are validated by the"
                   " sparse one-item path" % plan.get("door"))

    bad.extend(protected_pin_problems(plan))
    if plan.get("inventory_sha256") != _sha(INVENTORY):
        bad.append("the frozen inventory bytes changed since the plan was built")
    if plan.get("source_manifest_sha256") != _sha(
            os.path.join(KF, "draft_inputs.hashes.json")):
        bad.append("the frozen source manifest's bytes changed")
    if bundle.get("manifest_sha256") != _sha(mpath):
        bad.append("the bundle does not bind THIS manifest's bytes")

    def _inventory():
        import validate_benchmark_inventory as vbi
        for why in vbi.check(json.load(open(INVENTORY, encoding="utf-8"))):
            bad.append("inventory: %s" % why)
    _guard("inventory validator", _inventory)

    # --- THE ORDERED DERIVATION, from the frozen inventory outward ----------
    derived = {}
    _guard("derivation", lambda: derived.update(
        derive_expected(plan.get("runtime_model_id"))))
    if not derived:
        return bad

    def _first_diff(got, want, label):
        """Report the FIRST index where two ordered lists differ, and how."""
        if got == want:
            return
        n = min(len(got), len(want))
        at = next((i for i in range(n) if got[i] != want[i]), n)
        bad.append("%s is not the derivation: %d rows vs %d derived, first "
                   "difference at index %d" % (label, len(got), len(want), at))

    def _chain():
        # COMPLETE ordered rows, not projections: the event rows carry their
        # input identity AND the reversible menu map, and the packet rows carry
        # their item and lanes. Comparing selected fields let a deleted event, a
        # changed packet source and a corrupted menu back-map all pass with the
        # bundle hash refreshed (Codex SEQ 1314 item 7).
        _first_diff(plan.get("events"), derived["events"], "the plan's events")
        _first_diff(plan.get("packets"), derived["packets"], "the plan's packets")
        want_calls = list(derived["calls"])
        got_calls = [(r["packet_id"], r["lane_id"])
                     for r in raw_transport.a1_schedule(plan)]
        _first_diff(got_calls, want_calls, "the plan's ordered calls")
        limits = raw_transport.a1_limits(plan)
        for field, want in limits.items():
            if (plan.get("budget") or {}).get(field) != want:
                bad.append("budget.%s is %r, derived %d"
                           % (field, (plan.get("budget") or {}).get(field), want))
        if plan.get("n_calls") != limits["primary_calls"] or \
                plan.get("call_ceiling") != limits["primary_calls"]:
            bad.append("n_calls / call_ceiling disagree with the derived "
                       "primary count %d" % limits["primary_calls"])
        if plan.get("n_packets") != len(derived["packets"]):
            bad.append("n_packets disagrees with the derived packet count")
        if plan.get("n_events") != len(derived["events"]):
            bad.append("n_events disagrees with the derived event count")
        want_prompts = derived["prompts"]
        for pk in derived["packets"]:
            body = want_prompts[pk["packet_id"]]
            if hashlib.sha256(body.encode("utf-8")).hexdigest() != \
                    pk["prompt_sha256"]:
                bad.append("%s: the derived prompt does not match its own pin"
                           % pk["packet_id"])
    _guard("ordered chain", _chain)

    # --- the source events, re-hashed from disk ------------------------------
    def _sources():
        want = {e["source_id"]: e for e in derived["events"]}
        for e in plan.get("events", []):
            live = os.path.join(_REPO, e["input_path"])
            if not os.path.exists(live):
                bad.append("%s: input is missing" % e["source_id"]); continue
            if _sha(live) != e["input_sha256"]:
                bad.append("%s: source input bytes drifted" % e["source_id"])
            if e["source_id"] in want and \
                    want[e["source_id"]]["input_sha256"] != e["input_sha256"]:
                bad.append("%s: the plan's input hash is not the derived one"
                           % e["source_id"])
    _guard("source inputs", _sources)

    # --- the bundle, ordered, and every launcher's BYTES re-rendered --------
    def _bundle():
        # the WHOLE bundle, row for row, plus its own totals
        _first_diff(bundle.get("slices"), derived["bundle_slices"],
                    "the bundle's slices")
        if bundle.get("workflow_max_bytes") != WORKFLOW_MAX_BYTES:
            bad.append("the bundle names a different transport limit")
        n_calls = len(derived["calls"])
        for field, want in (("n_slices", len(derived["bundle_slices"])),
                            ("n_packets", len(derived["packets"])),
                            ("n_calls", n_calls),
                            ("largest_launcher_bytes",
                             max(r["bytes"] for r in derived["bundle_slices"]))):
            if bundle.get(field) != want:
                bad.append("bundle.%s is %r, derived %r"
                           % (field, bundle.get(field), want))
        # and the launcher BYTES on disk are the derived bytes
        for row in derived["bundle_slices"]:
            live = os.path.join(_REPO, row["launcher"])
            if not os.path.isfile(live):
                bad.append("%s: launcher missing" % row["source_id"]); continue
            with io.open(live, encoding="utf-8") as fh:
                text = fh.read()
            if text != derived["launchers"][row["source_id"]]:
                bad.append("%s: the launcher on disk is not the launcher this "
                           "source derives - wrong or drifted bytes"
                           % row["source_id"])
            if os.path.getsize(live) >= WORKFLOW_MAX_BYTES:
                bad.append("%s: launcher is at or over the %d transport limit"
                           % (row["source_id"], WORKFLOW_MAX_BYTES))
    _guard("bundle", _bundle)

    # --- every lane carries the pinned runtime identity ----------------------
    def _lanes():
        for pk in plan["packets"]:
            if len(pk["lanes"]) != LANES_PER_PACKET:
                bad.append("%s: %d lanes, expected %d"
                           % (pk["packet_id"], len(pk["lanes"]),
                              LANES_PER_PACKET))
            for lane in pk["lanes"]:
                if (lane["model"] != PINNED_MODEL
                        or lane["effort"] != PINNED_EFFORT
                        or lane["agentType"] != PINNED_AGENT_TYPE):
                    bad.append("%s: lane %s is not the pinned runtime identity"
                               % (pk["packet_id"], lane["lane_id"]))
    _guard("lanes", _lanes)
    return bad


def one_item_prompts(role="drafter"):
    """The exact prompt bytes each packet's workers receive, from the ONE owner."""
    return _one_item_packets(_events(), role)[1]
if __name__ == "__main__":
    # DIAGNOSTIC ONLY. `--preflight [run_dir]` ARMS NOTHING: it reports whether
    # a launch WOULD be refused, and prints every reason. The SUPPORTED ROUTE is
    # `raw_transport.a1_prepare_run(<fresh_run_dir>)`, which runs this same gate
    # and then publishes the armed launchers and the invocations to replay.
    if len(sys.argv) > 1 and sys.argv[1] == "--preflight":
        problems = preflight(run_dir=sys.argv[2] if len(sys.argv) > 2 else None)
        for why in problems:
            print("REFUSED: %s" % why)
        print("preflight: %s" % ("GO" if not problems
                                 else "NO-GO (%d)" % len(problems)))
        raise SystemExit(1 if problems else 0)
    build()
    build_reader_plan()
