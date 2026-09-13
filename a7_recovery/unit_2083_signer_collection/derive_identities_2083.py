# -*- coding: utf-8 -*-
"""Codex SEQ 2083: derive the per-event identities from the PRESERVED bytes.

Read-only. Every value comes from this unit's own preserved official state and
transcript, never from the request that asked for them. It also checks the one
property the SEQ 2073 identity seam exists to protect: none of this round's
run/agent/response/request identities may collide with the completed first
round's. Judges no answer and writes no run artifact.
"""
import collections, glob, hashlib, io, json, os, sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A + "/unit_2008/harness_g1v3")
import raw_transport as RT                                         # noqa: E402

HERE = A + "/unit_2083_signer_collection/evidence/signer"
PRIOR = (A + "/unit_2070_targeted_collection/evidence/v6",
         A + "/unit_2080_source_collection/evidence/v6r3",
         A + "/unit_2074_successor_collection/evidence/v6r2")
sha = lambda b: hashlib.sha256(b).hexdigest()


def identities(evdir):
    """(run, agent, response, request) ids per event, from preserved bytes."""
    out = collections.OrderedDict()
    for sp in sorted(glob.glob(os.path.join(evdir, "*.state.json"))):
        doc = json.loads(io.open(sp, encoding="utf-8").read())
        rows = [r for r in (doc.get("workflowProgress") or [])
                if r.get("type") == "workflow_agent"]
        if len(rows) != 1:
            raise ValueError("not one agent row: %s" % sp)
        run_id = doc["runId"]
        tp = os.path.join(evdir, run_id + ".transcript.jsonl")
        recs = [json.loads(l) for l in io.open(tp, encoding="utf-8") if l.strip()]
        asst = [r for r in recs if r.get("type") == "assistant"]
        got = doc.get("result") or {}
        out[rows[0].get("label")] = collections.OrderedDict([
            ("runId", run_id), ("agentId", rows[0].get("agentId")),
            ("response_ids", sorted({(r.get("message") or {}).get("id")
                                     for r in asst}, key=str)),
            ("request_ids", sorted({r.get("requestId") for r in asst}, key=str)),
            ("timestamps", sorted({r.get("timestamp") for r in recs
                                   if r.get("timestamp")}, key=str)[:1]
             + sorted({r.get("timestamp") for r in recs
                       if r.get("timestamp")}, key=str)[-1:]),
            ("cli_versions", sorted({r.get("version") for r in recs
                                     if r.get("version")}, key=str)),
            ("usage", collections.OrderedDict([
                ("totalTokens", doc.get("totalTokens")),
                ("durationMs", doc.get("durationMs")),
                ("totalToolCalls", doc.get("totalToolCalls")),
                ("agentCount", doc.get("agentCount"))])),
            ("observed", collections.OrderedDict([
                ("workflow_row_model", rows[0].get("model")),
                ("workflow_row_effort", rows[0].get("effort")),
                ("agentType", rows[0].get("agentType")),
                ("toolCalls", rows[0].get("toolCalls")),
                ("agent_state", rows[0].get("state")),
                ("status", doc.get("status")),
                ("transcript_models", sorted({(r.get("message") or {}).get("model")
                                              for r in asst}, key=str)),
                ("transcript_efforts", sorted({r.get("effort") for r in asst},
                                              key=str)),
                ("record_shape", [r.get("type") for r in recs])])),
            ("returned", collections.OrderedDict([
                ("declared_model", got.get("model")),
                ("declared_effort", got.get("effort")),
                ("declared_agentType", got.get("agentType")),
                ("attempt", got.get("attempt")),
                ("text_sha256", sha((got.get("text") or "").encode("utf-8"))),
                ("text_bytes", len((got.get("text") or "").encode("utf-8"))),
                ("is_error", got.get("is_error")),
                ("refusal_or_wait", None)])),
            ("preserved", collections.OrderedDict([
                ("state_path", sp), ("state_sha256", sha(io.open(sp, "rb").read())),
                ("transcript_path", tp),
                ("transcript_sha256", sha(io.open(tp, "rb").read())),
                ("returned_path", os.path.join(evdir, run_id + ".returned.txt")),
                ("returned_sha256", sha(io.open(
                    os.path.join(evdir, run_id + ".returned.txt"), "rb").read()))]))])
    return out


now = identities(HERE)
#: EVERY completed round, not just the first: this is the third
#: round, so a reused identity from EITHER earlier round matters.
before = collections.OrderedDict()
for _d in PRIOR:
    before.update(identities(_d))


def flat(idmap, field):
    return {v for row in idmap.values() for v in
            (row[field] if isinstance(row[field], list) else [row[field]])}


collisions = collections.OrderedDict(
    (f, sorted(flat(now, f) & flat(before, f)))
    for f in ("runId", "agentId", "response_ids", "request_ids"))
internal = collections.OrderedDict()
for f in ("runId", "agentId", "response_ids", "request_ids"):
    vals = [v for row in now.values() for v in
            (row[f] if isinstance(row[f], list) else [row[f]])]
    internal[f] = sorted(v for v in set(vals) if vals.count(v) > 1)

doc = collections.OrderedDict([
    ("authority", "Codex SEQ 2083"), ("events", now),
    ("collides_with_earlier_rounds", collisions),
    ("repeats_within_this_round", internal),
    ("any_collision", any(collisions.values()) or any(internal.values()))])
RT._atomic_json(HERE + "/identities_2083.json", doc)
print(json.dumps(collections.OrderedDict([
    ("events", list(now)),
    ("collides_with_earlier_rounds", collisions),
    ("repeats_within_this_round", internal),
    ("any_collision", doc["any_collision"])]), indent=1, default=str))
