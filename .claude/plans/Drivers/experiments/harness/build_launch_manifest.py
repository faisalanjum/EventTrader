"""Generate the K-fields drafting LAUNCH MANIFEST (machine-checkable plan).

The plan: 36 events x EXACTLY {one sonnet + one opus} lane each — 72 workers —
every lane effort=high on agentType=lean-probe (Read-only: structural
blindness), byte-identical prompts except the model slot, raw-text replies,
pinned to the LIVE contract/wrapper/protocol hashes at generation time.
Deterministic: same frozen inputs + same pinned files -> same manifest bytes.
Run from experiments/:  venv/bin/python harness/build_launch_manifest.py
"""
import hashlib
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
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
            "lanes": [
                {"model": "sonnet", "effort": "high",
                 "agentType": "lean-probe"},
                {"model": "opus", "effort": "high",
                 "agentType": "lean-probe"},
            ]})
    return events


def build():
    events = _events()
    doc = {
        "plan": "K-fields dual blind drafts (GO #1)",
        "date": "2026-07-24",
        "events": events,
        "n_events": len(events),
        "n_workers": sum(len(e["lanes"]) for e in events),
        "pins": {
            "contract": _sha(os.path.join(_HERE, "exp5_prompt_drafter.md")),
            "contract_manifest": _sha(os.path.join(
                _HERE, "exp5_prompt_contract.manifest.json")),
            "wrapper": _sha(os.path.join(KF, "drafting_wrapper.md")),
            "protocol": _sha(os.path.join(KF, "protocol.md")),
            "inputs_manifest": _sha(os.path.join(
                KF, "draft_inputs.hashes.json")),
        },
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
        "door": "gold",           # K-fields drafters answer with the gold fields
        "budget": {"quarantined": 19, "fresh_drafts": 72,
                   "briefs_max": 9, "total_cap": 100},
        "rules": ["byte-identical prompts across lanes except the model slot",
                  "agentType lean-probe = Read-only (Bash/Glob/Grep impossible)",
                  "post-run: audit_worker_access.py --expect 72 + per-event-"
                  "per-lane coverage", "no Qwen, no EXP-5 under GO #1"],
    }
    # STEP 3 §2 (Codex SEQ 1089): the TRUSTED launcher assembles the COMPLETE
    # prompt here and embeds it. A worker receives that string and nothing else —
    # no repository path, no file to read. The prompt body comes from the ONE
    # Step-2 builder's output; only the event view is appended, LAST, in place of
    # its placeholder. No schema is copied and no second prompt owner is created.
    prompts = _assemble(events, "exp5_prompt_drafter.md")
    # Every event row carries the sha256 of the EXACT prompt bytes its workers
    # will receive, so an edited or regenerated prompt cannot pass the pinned
    # plan unnoticed.
    for e in events:
        e["prompt_sha256"] = hashlib.sha256(
            prompts[e["source_id"]].encode("utf-8")).hexdigest()

    dest = os.path.join(_HERE, "launch_kfields_drafts.manifest.json")
    with open(dest, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    # regenerate the WORKFLOW from the pristine TEMPLATE (idempotent by
    # construction — never patches its own prior output): the locked
    # (source_id -> input_path) table is EMBEDDED; args deviating from the
    # locked plan throw (duplicates, unknown events, swapped inputs).
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
    guard += "\nconst PROMPTS = " + json.dumps(prompts, sort_keys=True)

    tmpl = open(os.path.join(_HERE,
                             "launch_kfields_drafts.workflow.template.js")).read()
    assert "__GUARD__" in tmpl, "template placeholder missing"
    with open(os.path.join(_HERE,
                           "launch_kfields_drafts.workflow.js"), "w") as f:
        f.write(tmpl.replace("__GUARD__", guard))
    print("manifest:", _sha(dest))
    print("workflow: EXPECTED table embedded,", len(expected), "events bound")
    print(f"events={doc['n_events']} workers={doc['n_workers']}")
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


if __name__ == "__main__":
    build()
    build_reader_plan()
