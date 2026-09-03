#!/usr/bin/env python3
"""Verify the already-paid signer handoff STRUCTURALLY (Codex SEQ 1558 item 4).

The previous version only asked whether three local digests appeared SOMEWHERE inside
`archive_CORE_1161.md`, and reported an empty transcript list. Occurring in a file is
not a binding: it says nothing about which workflow produced the bytes, whether that
workflow completed, whether the agent called any tool, or whether the terminal message
is the answer that was kept.

This proves the relationships, each one-to-one, from `products/SIGNER_HANDOFF.tsv`:

  * every pinned artefact still hashes to its pinned digest and byte count
  * the workflow state reports status `completed` and its own run id
  * the agent transcript is EXACTLY three rows: one user, two assistant
  * the transcript contains ZERO tool_use blocks - the answer was not tool-assisted
  * exactly one terminal assistant row, and it ended by `end_turn`
  * the terminal message's text equals `raw.bin` BYTE FOR BYTE
  * the transcript's parent session is this session
  * the accepting archive still hashes to its pin and carries the evidence digest

No signer retry is lawful; nothing here calls a model.
"""
import hashlib
import io
import json
import os
import re

R = os.path.dirname(os.path.abspath(__file__))
TSV = os.path.join(R, "products", "SIGNER_HANDOFF.tsv")
SESSION = "5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
COLUMNS = ["role", "path", "bytes", "sha256"]


def pinned(path=TSV):
    lines = [l.rstrip("\n") for l in io.open(path, encoding="utf-8") if l.strip()]
    if not lines or lines[0].split("\t") != COLUMNS:
        raise ValueError("handoff header is not %s" % COLUMNS)
    out = {}
    for line in lines[1:]:
        f = line.split("\t")
        if len(f) != len(COLUMNS):
            raise ValueError("malformed handoff row: %r" % line)
        out[f[0]] = {"path": f[1], "bytes": int(f[2]), "sha256": f[3]}
    return out


def _read(root, entry):
    p = entry["path"] if os.path.isabs(entry["path"]) else os.path.join(root, entry["path"])
    return io.open(p, "rb").read()


ROLES = ("workflow_state", "agent_transcript", "agent_meta", "signer_evidence",
         "signer_raw", "signer_reply", "producer_report", "acceptance")

#: The producer report (Core 1161) states the run as ONE sentence and each artefact's
#: digest beside its own name. These patterns RECOGNISE those sentences; every
#: decision below is an equality against the pinned bytes.
_RUN = re.compile(r"run (wf_[0-9a-f-]+), child agent ([0-9a-f]+), model ([\w.-]+), "
                  r"effort ([\w-]+), agent type ([\w-]+)")
_RAW = re.compile(r"final_sign\.attempt1\.raw\.json, (\d+) characters, sha256 ([0-9a-f]{64})")
_STATE = re.compile(r"Official state sha256 ([0-9a-f]{64}); transcript sha256 ([0-9a-f]{64})")
_EVID = re.compile(r"final_sign_evidence\.json sha256 ([0-9a-f]{64})")
_REPLY = re.compile(r"final_sign_reply\.json sha256 ([0-9a-f]{64})")
_PROMPT = re.compile(r'const PROMPT = "((?:[^"\\]|\\.)*)"')
_CONFIG = re.compile(r"agent\(PROMPT,\s*\{(.*?)\}\)", re.S)
_FIELD = re.compile(r'(\w+):\s*"([^"]*)"')


def _js_string(literal):
    """Decode a JS double-quoted string literal. The escapes a generated script
    uses are JSON's, so JSON's decoder is exact for them; anything else refuses."""
    return json.loads('"' + literal + '"')


def _header(text, key):
    m = re.search(r"^%s:\s*(.+?)\s*$" % re.escape(key), text, re.M)
    return m.group(1) if m else None


def failures(path=TSV, root=R):
    bad = []
    try:
        pins = pinned(path)
    except (IOError, OSError, ValueError) as exc:
        return ["handoff inventory unreadable or malformed: %s" % exc]
    for role in ROLES:
        if role not in pins:
            bad.append("handoff does not pin %s" % role)
    if bad:
        return bad
    blobs = {}
    for role, entry in pins.items():
        try:
            raw = _read(root, entry)
        except (IOError, OSError):
            bad.append("%s: pinned artefact missing at %s" % (role, entry["path"]))
            continue
        blobs[role] = raw
        if len(raw) != entry["bytes"]:
            bad.append("%s: %d bytes on disk, %d pinned" % (role, len(raw), entry["bytes"]))
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            bad.append("%s: bytes do not hash to the pinned digest" % role)
    if bad:
        return bad

    # ---- the producer report's own statements, the authority every pin binds to
    report = blobs["producer_report"].decode("utf-8", "strict")
    run = _RUN.search(report)
    if not run:
        return ["producer report does not state the run sentence (run id, agent, model, "
                "effort, agent type)"]
    run_id, agent_id, model, effort, agent_type = run.groups()
    stated = {}
    for name, pat, roles in (("raw", _RAW, ("signer_raw",)),
                             ("state", _STATE, ("workflow_state", "agent_transcript")),
                             ("evidence", _EVID, ("signer_evidence",)),
                             ("reply", _REPLY, ("signer_reply",))):
        m = pat.search(report)
        if not m:
            bad.append("producer report does not state the %s digest" % name)
            continue
        shas = m.groups()[-len(roles):]
        for role, sha in zip(roles, shas):
            if sha != pins[role]["sha256"]:
                bad.append("producer report binds %s to %s..., the pinned artefact is "
                           "%s..." % (role, sha[:12], pins[role]["sha256"][:12]))
        if name == "raw" and int(m.group(1)) != len(blobs["signer_raw"].decode("utf-8")):
            bad.append("producer report states %s raw characters, raw.bin has %d"
                       % (m.group(1), len(blobs["signer_raw"].decode("utf-8"))))

    # ---- the acceptance: Codex's reply to THAT report, pinning its exact bytes
    acc = blobs["acceptance"].decode("utf-8", "strict")
    seq = _header(report, "SEQ")
    if _header(acc, "IN_REPLY_TO") != seq:
        bad.append("acceptance replies to SEQ %r, the producer report is SEQ %r"
                   % (_header(acc, "IN_REPLY_TO"), seq))
    ident = _header(acc, "IDENTITY") or ""
    want = "Core SEQ %s sha256 %s" % (seq, pins["producer_report"]["sha256"])
    if want not in ident:
        bad.append("acceptance IDENTITY does not pin the producer report's exact bytes")
    if not re.search(r"^VERIFIED:", acc, re.M):
        bad.append("acceptance carries no VERIFIED line")
    if _header(report, "FROM") != "Core" or _header(acc, "FROM") != "Codex":
        bad.append("the chain is not Core report -> Codex acceptance")

    # ---- the workflow state: run, config, full prompt, result
    wf = json.loads(blobs["workflow_state"].decode("utf-8"))
    if wf.get("status") != "completed":
        bad.append("workflow status is %r, not completed" % wf.get("status"))
    if wf.get("runId") != run_id:
        bad.append("workflow run id %r is not the reported %r" % (wf.get("runId"), run_id))
    agents = [e for e in wf.get("workflowProgress", [])
              if isinstance(e, dict) and e.get("agentId")]
    if len(agents) != 1:
        bad.append("workflow state carries %d agent records, expected exactly one"
                   % len(agents))
        return bad
    agent = agents[0]
    if agent.get("agentId") != agent_id:
        bad.append("workflow agent id %r is not the reported %r"
                   % (agent.get("agentId"), agent_id))
    script = wf.get("script") or ""
    pm = _PROMPT.search(script)
    cm = _CONFIG.search(script)
    if not pm or not cm:
        bad.append("workflow script does not carry a PROMPT literal and an agent() config")
        return bad
    try:
        prompt = _js_string(pm.group(1))
    except ValueError:
        bad.append("workflow script's PROMPT literal is not decodable")
        prompt = None
    config = dict(_FIELD.findall(cm.group(1)))
    for key, want_v in (("model", model), ("effort", effort), ("agentType", agent_type)):
        if config.get(key) != want_v:
            bad.append("workflow script config %s=%r, the report states %r"
                       % (key, config.get(key), want_v))
    if agent.get("model") != model:
        bad.append("workflow agent record model %r is not %r" % (agent.get("model"), model))
    meta = json.loads(blobs["agent_meta"].decode("utf-8"))
    if meta.get("model") != model or meta.get("agentType") != agent_type:
        bad.append("agent meta (%r, %r) disagrees with (%r, %r)"
                   % (meta.get("model"), meta.get("agentType"), model, agent_type))
    result = wf.get("result")
    if not isinstance(result, str) or result.encode("utf-8") != blobs["signer_raw"]:
        bad.append("workflow result is not byte-identical to raw.bin")

    # ---- the transcript: exact rows, ids, chain, model/effort, zero tools, terminal
    rows = [json.loads(l) for l in
            blobs["agent_transcript"].decode("utf-8").splitlines() if l.strip()]
    kinds = [r.get("type") for r in rows]
    if kinds != ["user", "assistant", "assistant"]:
        bad.append("transcript row types are %s, expected exactly user, assistant, "
                   "assistant" % kinds)
        return bad
    if agent_id not in os.path.basename(pins["agent_transcript"]["path"]):
        bad.append("agent id %r does not name the pinned transcript" % agent_id)
    tool_uses = 0
    for i, r in enumerate(rows):
        if r.get("agentId") != agent_id:
            bad.append("row %d agentId %r is not %r" % (i, r.get("agentId"), agent_id))
        if r.get("sessionId") != SESSION:
            bad.append("row %d sessionId %r is not the parent session" % (i, r.get("sessionId")))
        if not r.get("uuid"):
            bad.append("row %d has no uuid" % i)
        want_parent = rows[i - 1].get("uuid") if i else None
        if r.get("parentUuid") != want_parent:
            bad.append("row %d parentUuid %r does not continue the chain from %r"
                       % (i, r.get("parentUuid"), want_parent))
        m = r.get("message", {})
        content = m.get("content", [])
        if isinstance(content, list):
            tool_uses += sum(1 for x in content
                             if isinstance(x, dict) and x.get("type") == "tool_use")
        if r.get("type") == "assistant":
            if m.get("model") != model:
                bad.append("row %d model %r is not %r" % (i, m.get("model"), model))
            if r.get("effort") != effort:
                bad.append("row %d effort %r is not %r" % (i, r.get("effort"), effort))
    if len({r.get("uuid") for r in rows}) != len(rows):
        bad.append("transcript uuids are not distinct")
    if tool_uses:
        bad.append("the signer agent made %d tool call(s)" % tool_uses)
    if wf.get("totalToolCalls") != tool_uses or agent.get("toolCalls") not in (0, None, tool_uses):
        bad.append("workflow state reports %r tool calls, the transcript contains %d"
                   % (wf.get("totalToolCalls"), tool_uses))
    c0 = rows[0].get("message", {}).get("content", "")
    user = c0 if isinstance(c0, str) else "".join(
        x.get("text", "") for x in c0 if isinstance(x, dict))
    if prompt is not None and user != prompt:
        bad.append("the agent's user message is not byte-identical to the script's "
                   "full PROMPT (%d vs %d chars)" % (len(user), len(prompt)))
    last = rows[-1]
    if last.get("message", {}).get("stop_reason") != "end_turn":
        bad.append("terminal row did not end by end_turn")
    lc = last.get("message", {}).get("content", [])
    text = "".join(x.get("text", "") for x in lc
                   if isinstance(x, dict)) if isinstance(lc, list) else ""
    if text.encode("utf-8") != blobs["signer_raw"]:
        bad.append("terminal message text is not byte-identical to raw.bin")

    # ---- the lock evidence file states the same facts a second time, in its own
    # fields; every one must agree with the report and the pinned bytes
    ev = json.loads(blobs["signer_evidence"].decode("utf-8"))
    for key, want_v in (("run_id", run_id), ("agent_id", agent_id), ("model", model),
                        ("effort", effort), ("agent_type", agent_type),
                        ("state_sha256", pins["workflow_state"]["sha256"]),
                        ("transcript_sha256", pins["agent_transcript"]["sha256"]),
                        ("raw_sha256", pins["signer_raw"]["sha256"]),
                        ("parent_session_id", SESSION), ("tool_calls", tool_uses),
                        ("raw_chars", len(blobs["signer_raw"].decode("utf-8")))):
        if ev.get(key) != want_v:
            bad.append("lock evidence %s=%r disagrees with %r" % (key, ev.get(key), want_v))
    if prompt is not None and ev.get("prompt_sha256") != hashlib.sha256(
            prompt.encode("utf-8")).hexdigest():
        bad.append("lock evidence prompt_sha256 is not the digest of the full prompt")

    # ---- the answer: strict JSON with exactly the three keys and their meaning
    for role in ("signer_raw", "signer_reply"):
        try:
            ans = json.loads(blobs[role].decode("utf-8"))
        except ValueError:
            bad.append("%s is not strict JSON" % role)
            continue
        if not isinstance(ans, dict) or set(ans) != {"signed", "blocked", "why"}:
            bad.append("%s keys are %s, expected exactly signed, blocked, why"
                       % (role, sorted(ans) if isinstance(ans, dict) else type(ans).__name__))
            continue
        if ans["signed"] is not True or ans["blocked"] is not None \
                or not isinstance(ans["why"], str) or not ans["why"].strip():
            bad.append("%s does not state signed=true, blocked=null, why=nonempty" % role)
    try:
        if json.loads(blobs["signer_raw"].decode()) != json.loads(blobs["signer_reply"].decode()):
            bad.append("reply.bin is not the parsed copy of raw.bin")
    except ValueError:
        pass
    return bad


def main():
    bad = failures()
    for b in bad:
        print("FAIL %s" % b)
    if bad:
        print("SIGNER HANDOFF REJECTED (%d defects)" % len(bad))
        return 1
    pins = pinned()
    for role in sorted(pins):
        print("  %-18s %8d bytes  %s" % (role, pins[role]["bytes"],
                                         pins[role]["sha256"][:16]))
    print("SIGNER HANDOFF OK: completed workflow, three-row transcript, zero tool "
          "calls, terminal text == raw.bin. No retry is lawful.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
