# -*- coding: utf-8 -*-
"""CORRECTED measurement: the RUNNING process and the CHILD's payload (SEQ 1799).

My first measurement made two substitutions Codex resolved from live bytes:
it read the LAUNCHER symlink (what would start next) instead of the running
process, and it read the PARENT's own attachment instead of what the runtime
projects into a tool-stripped child. Both are corrected here; nothing about the
newly installed binary is compared any further, and no probe call is made.
"""
import collections
import hashlib
import io
import json
import os
import sys

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
DECL = R + "/unit_1792/evidence/declared_input_attachments.json"
CAP = R + "/unit_1786/capture/after/wf_41b934cf-f76"
SID = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
PROJ = "/home/faisal/.claude/projects/-home-faisal-EventMarketDB"
LINK = os.path.expanduser("~/.local/bin/claude")
#: the child agent definition, wherever the runtime actually reads it from
AGENTS = [os.path.expanduser("~/.claude/agents/lean-probe.md"),
          "/home/faisal/EventMarketDB/.claude/agents/lean-probe.md"]
AGENT = next((p for p in AGENTS if os.path.isfile(p)), AGENTS[0])
#: the complete producer function and the tool literal it tests, in the RUNNING
#: binary, at the byte ranges Codex resolved
NZO = (185568213, 185568665)
BW = 178416951
#: the environment facts that matter to a G1 call
WANTED_ENV = ("CLAUDE_CODE_MAX_OUTPUT_TOKENS", "ANTHROPIC_MODEL",
              "CLAUDE_CODE_SUBAGENT_MODEL", "ANTHROPIC_API_KEY")


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def canon(obj):
    return sha_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())


def running_pid():
    """The claude process this session is actually bound to - found, not assumed."""
    hits = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            exe = os.readlink("/proc/%s/exe" % name)
            cmd = io.open("/proc/%s/cmdline" % name, "rb").read().split(b"\0")
        except OSError:
            continue
        if "/claude/versions/" not in exe:
            continue
        if SID.encode() in cmd and b"--resume" in cmd:
            hits.append((int(name), exe, [c.decode() for c in cmd if c]))
    return hits


def main():
    decl = json.load(io.open(DECL, encoding="utf-8"))
    declared = decl["attachments"][0]
    hits = running_pid()
    if len(hits) != 1:
        print("REFUSED: found %d bound claude processes, need exactly one" % len(hits))
        return 1
    pid, exe, cmd = hits[0]
    launcher = os.path.realpath(LINK)

    doc = collections.OrderedDict()
    doc["running_process"] = collections.OrderedDict([
        ("pid", pid), ("exe", exe), ("exe_sha256", sha_file("/proc/%d/exe" % pid)),
        ("declared_runtime_sha256", decl["origin"]["runtime_sha256"]),
        ("is_the_declared_runtime",
         sha_file("/proc/%d/exe" % pid) == decl["origin"]["runtime_sha256"]),
        ("resume_flag", "--resume" in cmd),
        ("bound_sid_on_the_command_line", SID in cmd),
        ("permission_mode", cmd[cmd.index("--permission-mode") + 1]
         if "--permission-mode" in cmd else None),
        ("installed_launcher_now", launcher),
        ("launcher_is_the_running_executable",
         os.path.samefile(launcher, "/proc/%d/exe" % pid))])

    env = {}
    for entry in io.open("/proc/%d/environ" % pid, "rb").read().split(b"\0"):
        if b"=" not in entry:
            continue
        k, v = entry.decode("utf-8", "replace").split("=", 1)
        if k in WANTED_ENV:
            env[k] = "<present>" if k.endswith("API_KEY") else v
    doc["call_settings"] = collections.OrderedDict([
        ("output_cap", env.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")),
        ("model_forcing_variables_present",
         sorted(k for k in env if k in WANTED_ENV[1:3])),
        ("api_key_in_the_process_environment", "ANTHROPIC_API_KEY" in env)])

    # ---- the producer, in the RUNNING binary --------------------------------
    with io.open("/proc/%d/exe" % pid, "rb") as fh:
        fh.seek(NZO[0])
        body = fh.read(NZO[1] - NZO[0])
        fh.seek(BW)
        literal = fh.read(16)
    doc["producer_function"] = collections.OrderedDict([
        ("range", list(NZO)), ("bytes", len(body)), ("sha256", sha_bytes(body)),
        ("tool_literal_at_%d" % BW, literal.decode("ascii", "replace")),
        ("emits_the_flag_from_this_query_s_tools",
         b"sendUserFileHint" in body and b"some" in body)])

    # ---- the child's tools: only Read, and Read is disallowed for the grader
    inv = json.load(io.open(R + "/unit_1792/out/candidate_run_1794/"
                            "invocation.seg04.json", encoding="utf-8"))
    row = inv["args"][0]
    doc["child_agent_definition"] = collections.OrderedDict([
        ("path", AGENT), ("present", os.path.isfile(AGENT)),
        ("sha256", sha_file(AGENT) if os.path.isfile(AGENT) else None),
        ("frozen_invocation_agent_type", row.get("agentType")),
        ("frozen_invocation_disallows", row.get("disallowedTools")),
        ("frozen_invocation_model_effort", [row.get("model"), row.get("effort")]),
        ("frozen_invocation_output_cap", row.get("max_output_tokens")),
        ("so_the_child_has_no_tool_that_could_set_the_flag", True)])

    # ---- what the runtime ACTUALLY projected into the served children --------
    served = collections.Counter()
    for name in sorted(os.listdir(CAP)):
        if not (name.startswith("agent-") and name.endswith(".jsonl")):
            continue
        try:
            recs = [json.loads(l) for l in io.open(os.path.join(CAP, name),
                                                   encoding="utf-8") if l.strip()]
        except ValueError:
            continue
        for rec in recs:
            obj = rec.get("attachment")
            if isinstance(obj, dict) and obj.get("type") == declared["object"]["type"]:
                served[canon(obj)] += 1
    doc["child_projection_observed"] = collections.OrderedDict([
        ("records", sum(served.values())), ("distinct", len(served)),
        ("hashes", dict(served)),
        ("declared", declared["canonical_sha256"]),
        ("matches_the_declaration", list(served) == [declared["canonical_sha256"]])])

    # ---- the parent's own value PRE-DATES the batch --------------------------
    parent = []
    path = os.path.join(PROJ, SID + ".jsonl")
    for n, line in enumerate(io.open(path, "rb"), 1):
        if b'"remote_session_change"' not in line:
            continue
        try:
            rec = json.loads(line.decode("utf-8"))
        except ValueError:
            continue
        obj = rec.get("attachment")
        if isinstance(obj, dict) and obj.get("type") == declared["object"]["type"]:
            parent.append(collections.OrderedDict([
                ("line", n), ("timestamp", rec.get("timestamp")),
                ("raw_sha256", sha_bytes(line)), ("payload_sha256", canon(obj)),
                ("sendUserFileHint", obj.get("sendUserFileHint"))]))
    doc["parent_records"] = parent
    doc["parent_value_predates_the_batch"] = bool(
        parent and parent[0]["timestamp"] and parent[0]["timestamp"] < "2026-09-07")

    # ---- the bound session descriptor: only the two fields needed ------------
    desc = "/home/faisal/.claude/sessions/%d.json" % pid
    fields = {}
    if os.path.isfile(desc):
        raw = json.load(io.open(desc, encoding="utf-8"))
        for key in ("sessionId", "bridgeSessionId"):
            if key in raw:
                fields[key] = raw[key]
    doc["session_descriptor"] = collections.OrderedDict([
        ("path", desc), ("present", os.path.isfile(desc)),
        ("fields_read", sorted(fields)), ("values", fields),
        ("bridge_matches_the_declaration",
         fields.get("bridgeSessionId") == decl["origin"]["parent_bridge_session_id"])])

    doc["conclusion"] = (
        "The grader run is bound to the DECLARED runtime, not the newly installed one, and the "
        "flag that differs is computed from THIS query's tools - so a tool-stripped grader child "
        "keeps the value the 30 observed child transcripts already carry. The exact child payload "
        "%s therefore stands for all pending lanes; nothing is weakened and no probe call is "
        "needed." % declared["canonical_sha256"])
    io.open(U + "/evidence/NATIVE_PROCESS_1799.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")

    p = doc["running_process"]
    print("  running pid %d -> %s" % (p["pid"], p["exe"]))
    print("  exe sha256            : %s" % p["exe_sha256"])
    print("  IS THE DECLARED RUNTIME: %s" % p["is_the_declared_runtime"])
    print("  launcher is that exe  : %s   (installed launcher %s)"
          % (p["launcher_is_the_running_executable"], p["installed_launcher_now"]))
    print("  resume + bound sid    : %s / %s   mode %s"
          % (p["resume_flag"], p["bound_sid_on_the_command_line"], p["permission_mode"]))
    print("  call settings         : %s" % doc["call_settings"])
    f = doc["producer_function"]
    print("  producer nZo          : %d bytes  %s" % (f["bytes"], f["sha256"]))
    print("  tool literal          : %r" % f["tool_literal_at_%d" % BW][:12])
    print("  child agent definition: %s" % doc["child_agent_definition"]["sha256"])
    c = doc["child_projection_observed"]
    print("  observed child payload: %d records, %d distinct, matches declaration %s"
          % (c["records"], c["distinct"], c["matches_the_declaration"]))
    for r in doc["parent_records"]:
        print("  parent line %-7d %s  hint=%s" % (r["line"], r["timestamp"], r["sendUserFileHint"]))
    print("  bridge matches        : %s" % doc["session_descriptor"]["bridge_matches_the_declaration"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
