# -*- coding: utf-8 -*-
"""Pre-call record for the segment-8 native batch (Codex SEQ 1812).

Checks only the live conditions this call depends on and freezes the exact
native envelope from the published preparation. The args array is read from the
committed invocation and hashed three ways against the reviewer's pins; nothing
is retyped.
"""
import collections, hashlib, io, json, os, subprocess, sys
R = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
P = R + "/unit_1808/out/run_1808"
U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SID = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
DECL = R + "/unit_1792/evidence/declared_input_attachments.json"
PIN = {
    "script_sha256": "0fa03ab1a35e3f4cfbc933dd4319bb88f54aaa8a7d1a482beb519e1b7b879b1f",
    "script_bytes": 23594,
    "args_compact_sha256": "5a397266d4c37e461bcdb512af6ac5b267ad9b4dc2c929632ae82a714ddc224c",
    "args_compact_bytes": 1174,
    "args_sorted_default_sha256":
        "923f2abf36e3d62fcf0846e6e9b0e39cc61d935117924c08be2e5083dfc6894b",
    "typed_input_sha256": "55b56959bbc260c9720d9a4137d609fc4a32b51e3e69bd33962363663c364ea8",
    "typed_input_bytes": 1297,
    "root": "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0",
    "receipt": "40e95878c57b92db27e45dff372716eeea159721d3277287a100b64e597cf62b",
    "reservation": "1d62a5cd7b21b6127bada23f19552ef8c448fb695e174c0b2aa10700859e3b7a",
    "invocation": "aadc00529ae4b971383d617e2d8d53ff7d8e4e60d9cd3bdc4b3d173f0b032ea8",
    "runtime_sha256": "4ae40dd1784e85753e742e09f267d29ecbb82890361ad3817d27560866d364a6",
    "runtime_bytes": 215641584,
    "child_payload": "25394a531146690a27fd4db50c37758af8ac9e4f71e307e143fab2fe7bc3abc1",
    "preflight": "d5b64d838213c605a01f439d4ed69f882d6e06ce191555816fb13388e0f492c9",   # the two proofs Codex told us to REUSE, not repeat
    "read_record": "c7a6023d33c8e7bd99105f6ab7b2f65e0023e7b7efcb9250e2e35b483f9b9cfa",
}
WANTED = ("CLAUDE_CODE_MAX_OUTPUT_TOKENS", "CLAUDE_CODE_SUBAGENT_MODEL",
          "CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "ANTHROPIC_API_KEY")
sha = lambda b: hashlib.sha256(b).hexdigest()
fsha = lambda p: sha(io.open(p, "rb").read())
WFDIR = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/"
                           "%s/subagents/workflows" % SID)
PREFLIGHT = R + "/unit_1810/logs/PREFLIGHT_1810.json"
READREC = R + "/unit_1811/evidence/native_records_1811/read_result.jsonl"


def _mentions(needle):
    """True if ANY existing run directory names this exact string."""
    return subprocess.call(["grep", "-rqlF", "--", needle, WFDIR],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0


def main():
    args = json.load(io.open(P + "/invocation.seg08.json", encoding="utf-8"))["args"]
    script = P + "/grade_batch.seg08.js"
    compact = json.dumps(args, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sorted_default = json.dumps(args, sort_keys=True).encode("utf-8")
    typed = json.dumps({"args": args, "scriptPath": script},
                       sort_keys=True, separators=(",", ":")).encode("utf-8")
    env = collections.OrderedDict([
        ("scriptPath", script), ("script_bytes", os.path.getsize(script)),
        ("script_sha256", fsha(script)), ("args_rows", len(args)),
        ("first_lane", args[0]["lane_id"]), ("last_lane", args[-1]["lane_id"]),
        ("attempts", sorted({a.get("attempt") for a in args})),
        ("args_compact_bytes", len(compact)), ("args_compact_sha256", sha(compact)),
        ("args_sorted_default_sha256", sha(sorted_default)),
        ("typed_input_bytes", len(typed)), ("typed_input_sha256", sha(typed)),
        ("typed_input_keys", ["args", "scriptPath"])])
    checks = collections.OrderedDict([
        ("script_sha256", env["script_sha256"] == PIN["script_sha256"]),
        ("script_bytes", env["script_bytes"] == PIN["script_bytes"]),
        ("args_compact_sha256", env["args_compact_sha256"] == PIN["args_compact_sha256"]),
        ("args_compact_bytes", env["args_compact_bytes"] == PIN["args_compact_bytes"]),
        ("args_sorted_default_sha256",
         env["args_sorted_default_sha256"] == PIN["args_sorted_default_sha256"]),
        ("typed_input_sha256", env["typed_input_sha256"] == PIN["typed_input_sha256"]),
        ("typed_input_bytes", env["typed_input_bytes"] == PIN["typed_input_bytes"]),
        ("args_rows_3", len(args) == 3), ("attempt_1_only", env["attempts"] == [1]),
        ("root", fsha(P + "/root.json") == PIN["root"]),
        ("receipt", fsha(P + "/receipt.seg08.json") == PIN["receipt"]),
        ("reservation", fsha(P + "/reservation.seg08.json") == PIN["reservation"]),
        ("invocation", fsha(P + "/invocation.seg08.json") == PIN["invocation"])])
    hits = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            exe = os.readlink("/proc/%s/exe" % name)
            cmd = io.open("/proc/%s/cmdline" % name, "rb").read().split(b"\0")
        except OSError:
            continue
        if "/claude/versions/" in exe and SID.encode() in cmd and b"--resume" in cmd:
            hits.append((int(name), exe, [c.decode() for c in cmd if c]))
    if len(hits) != 1:
        print("REFUSED: %d bound processes" % len(hits)); return 1
    pid, exe, cmd = hits[0]
    envv = {}
    for e in io.open("/proc/%d/environ" % pid, "rb").read().split(b"\0"):
        if b"=" in e:
            k, v = e.decode("utf-8", "replace").split("=", 1)
            if k in WANTED:
                envv[k] = v
    desc = "/home/faisal/.claude/sessions/%d.json" % pid
    bridge = json.load(io.open(desc, encoding="utf-8")).get("bridgeSessionId") \
        if os.path.isfile(desc) else None
    live = collections.OrderedDict([
        ("pid", pid), ("exe", exe), ("exe_bytes", os.path.getsize("/proc/%d/exe" % pid)),
        ("exe_sha256", fsha("/proc/%d/exe" % pid)),
        ("permission_mode", cmd[cmd.index("--permission-mode") + 1]
         if "--permission-mode" in cmd else None),
        ("output_cap", envv.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")),
        ("model_force_present", [k for k in WANTED[1:3] if k in envv]),
        ("api_key_in_environment", "ANTHROPIC_API_KEY" in envv),
        ("bridge_session_id", bridge)])
    checks["runtime_is_the_declared_one"] = live["exe_sha256"] == PIN["runtime_sha256"]
    checks["runtime_bytes"] = live["exe_bytes"] == PIN["runtime_bytes"]
    checks["output_cap_128000"] = live["output_cap"] == "128000"
    checks["no_model_forcing"] = live["model_force_present"] == []
    checks["bridge_unchanged"] = bridge == json.load(
        io.open(DECL, encoding="utf-8"))["origin"]["parent_bridge_session_id"]
    checks["no_previous_start_of_this_exact_script"] = not _mentions(script)
    checks["no_previous_start_of_these_lanes"] = not any(
        _mentions(a["lane_id"]) for a in args)
    checks["reused_preflight_unchanged"] = fsha(PREFLIGHT) == PIN["preflight"]
    checks["reused_read_record_unchanged"] = fsha(READREC) == PIN["read_record"]
    wf = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/%s/"
                            "subagents/workflows" % SID)
    existing = sorted(os.listdir(wf)) if os.path.isdir(wf) else []
    doc = collections.OrderedDict([
        ("envelope", env), ("live", live), ("checks", checks),
        ("all_checks_pass", all(checks.values())),
        ("existing_run_directories_before_the_call", len(existing)),
        ("lane_ids", [a["lane_id"] for a in args]),
        ("call_settings", collections.OrderedDict(
            (k, args[0].get(k)) for k in ("model", "runtime_model_id", "effort", "agentType",
                                          "disallowedTools", "max_output_tokens"))),
        ("child_input_payload", PIN["child_payload"]),
        ("no_run_id_supplied", True), ("no_resume_from_run_id", True)])
    io.open(U + "/evidence/PRECALL_1812.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    io.open(U + "/evidence/native_envelope_1812.json", "w", encoding="utf-8").write(
        json.dumps({"args": args, "scriptPath": script},
                   sort_keys=True, separators=(",", ":")))
    for k, v in checks.items():
        if not v:
            print("  FAIL %s" % k)
    print("  envelope: %d rows %s..%s attempt %s" % (len(args), env["first_lane"],
                                                     env["last_lane"], env["attempts"]))
    print("  script  : %s (%d bytes)" % (env["script_sha256"][:16], env["script_bytes"]))
    print("  args    : compact %s (%d B) | sorted-default %s | typed %s (%d B)"
          % (env["args_compact_sha256"][:16], env["args_compact_bytes"],
             env["args_sorted_default_sha256"][:16], env["typed_input_sha256"][:16],
             env["typed_input_bytes"]))
    print("  live    : pid %d %s %d B cap %s force %s bridge %s"
          % (pid, exe.rsplit("/", 1)[-1], live["exe_bytes"], live["output_cap"],
             live["model_force_present"] or "none", bridge))
    print("  settings: %s" % json.dumps(doc["call_settings"], sort_keys=True))
    print("  existing run dirs: %d   ALL CHECKS PASS: %s"
          % (len(existing), doc["all_checks_pass"]))
    return 0 if doc["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
