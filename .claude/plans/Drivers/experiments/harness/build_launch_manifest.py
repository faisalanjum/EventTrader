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


def build():
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
    doc = {
        "plan": "K-fields dual blind drafts (GO #1)",
        "date": "2026-07-24",
        "events": events,
        "n_events": len(events),
        "n_workers": sum(len(e["lanes"]) for e in events),
        "pins": {
            "contract": _sha(os.path.join(_HERE, "exp5_item_contract.md")),
            "contract_manifest": _sha(os.path.join(
                _HERE, "exp5_item_contract.manifest.json")),
            "wrapper": _sha(os.path.join(KF, "drafting_wrapper.md")),
            "protocol": _sha(os.path.join(KF, "protocol.md")),
            "inputs_manifest": _sha(os.path.join(
                KF, "draft_inputs.hashes.json")),
        },
        # v2.1 contract: 37 model-owned fields (derived from PreparedFactV1) and
        # a verbatim, non-blank quote — the 60-200 band was never WorkOrder law.
        "schema": {"model_owned_fields": 37,
                   "quote": "verbatim non-blank substring; no length limit",
                   "enforced_by": "kf_lint (after raw_transport exact parse)"},
        "budget": {"quarantined": 19, "fresh_drafts": 72,
                   "briefs_max": 9, "total_cap": 100},
        "rules": ["byte-identical prompts across lanes except the model slot",
                  "agentType lean-probe = Read-only (Bash/Glob/Grep impossible)",
                  "post-run: audit_worker_access.py --expect 72 + per-event-"
                  "per-lane coverage", "no Qwen, no EXP-5 under GO #1"],
    }
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


if __name__ == "__main__":
    build()
