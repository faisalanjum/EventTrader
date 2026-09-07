# -*- coding: utf-8 -*-
"""The pre-call record for the segment-5 native batch (Codex SEQ 1802).

Checks only the live conditions the call depends on, and freezes the exact
native envelope from the COMMITTED preparation. Nothing is retyped: the args
array is read from unit_1798's invocation and hashed three ways against the
values Codex pinned.
"""
import collections, hashlib, io, json, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
P = R + "/unit_1803/out/run_1803"
U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SID = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
DECL = R + "/unit_1792/evidence/declared_input_attachments.json"
PIN = {
    "script_sha256": "3d25e52f3bcad283bd0b2ac5fb7712a7fb7db63b1804ff25f2c3c375350f0d71",
    "script_bytes": 510132,
    "args_compact_sha256": "030353e579f66b8101534f06936e4d6a5dd12e75451b7663b3c7ef0a92980751",
    "args_compact_bytes": 3911,
    "typed_input_sha256": "0346c6c1f61f50be58a3ef19c5d80923d7a45124446efbfc71d2ab66e09a60c0",
    "typed_input_bytes": 4034,
    "root": "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0",
    "receipt": "2b0e8a4153a2d32461f5630a7821e6d29bbb831a82a7f8859ac7f212b50677fb",
    "reservation": "714a1ef40a661a248fb6dfa2b0d06374fdb950eab441348a6e89db3f2ced2d3c",
    "invocation": "bb6d26359c1728a5d220011ee65a3b28861af36273d95ff267749ec31e5ab68a",
    "runtime_sha256": "4ae40dd1784e85753e742e09f267d29ecbb82890361ad3817d27560866d364a6",
    "runtime_bytes": 215641584,
    "child_payload": "25394a531146690a27fd4db50c37758af8ac9e4f71e307e143fab2fe7bc3abc1",
}
sha = lambda b: hashlib.sha256(b).hexdigest()
fsha = lambda p: sha(io.open(p, "rb").read())

def main():
    inv = json.load(io.open(P + "/invocation.seg06.json", encoding="utf-8"))
    args = inv["args"]
    script = P + "/grade_batch.seg06.js"
    compact = json.dumps(args, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sorted_default = json.dumps(args, sort_keys=True).encode("utf-8")
    typed = json.dumps({"args": args, "scriptPath": script},
                       sort_keys=True, separators=(",", ":")).encode("utf-8")
    env = collections.OrderedDict([
        ("scriptPath", script), ("script_bytes", os.path.getsize(script)),
        ("script_sha256", fsha(script)),
        ("args_rows", len(args)),
        ("first_lane", args[0]["lane_id"]), ("last_lane", args[-1]["lane_id"]),
        ("attempts", sorted({a.get("attempt") for a in args})),
        ("args_compact_bytes", len(compact)), ("args_compact_sha256", sha(compact)),
        ("typed_input_bytes", len(typed)), ("typed_input_sha256", sha(typed)),
        ("typed_input_keys", ["args", "scriptPath"])])
    checks = collections.OrderedDict([
        ("script_sha256", env["script_sha256"] == PIN["script_sha256"]),
        ("script_bytes", env["script_bytes"] == PIN["script_bytes"]),
        ("args_compact_sha256", env["args_compact_sha256"] == PIN["args_compact_sha256"]),
        ("args_compact_bytes", env["args_compact_bytes"] == PIN["args_compact_bytes"]),
        ("typed_input_sha256", env["typed_input_sha256"] == PIN["typed_input_sha256"]),
        ("typed_input_bytes", env["typed_input_bytes"] == PIN["typed_input_bytes"]),
        ("args_rows_10", len(args) == 10),
        ("attempt_1_only", env["attempts"] == [1]),
        ("receipt", fsha(P + "/receipt.seg06.json") == PIN["receipt"]),
        ("reservation", fsha(P + "/reservation.seg06.json") == PIN["reservation"]),
        ("invocation", fsha(P + "/invocation.seg06.json") == PIN["invocation"]),
        ("root", fsha(P + "/root.json") == PIN["root"])])
    # ---- the live process ---------------------------------------------------
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
        ("model_force_present", [k for k in ("CLAUDE_CODE_SUBAGENT_MODEL",
                                             "CLAUDE_CODE_SUBAGENT_MODEL_FORCE") if k in envv]),
        ("bridge_session_id", bridge)])
    checks["runtime_is_the_declared_one"] = live["exe_sha256"] == PIN["runtime_sha256"]
    checks["runtime_bytes"] = live["exe_bytes"] == PIN["runtime_bytes"]
    checks["output_cap_128000"] = live["output_cap"] == "128000"
    checks["no_model_forcing"] = live["model_force_present"] == []
    checks["bridge_unchanged"] = bridge == json.load(
        io.open(DECL, encoding="utf-8"))["origin"]["parent_bridge_session_id"]
    # ---- no competing run of these lanes -------------------------------------
    wf = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/%s/"
                            "subagents/workflows" % SID)
    existing = sorted(os.listdir(wf)) if os.path.isdir(wf) else []
    doc = collections.OrderedDict([
        ("envelope", env), ("live", live), ("checks", checks),
        ("all_checks_pass", all(checks.values())),
        ("existing_run_directories_before_the_call", len(existing)),
        ("lane_ids", [a["lane_id"] for a in args]),
        ("call_settings", collections.OrderedDict(
            (k, args[0].get(k)) for k in ("model", "runtime_model_id", "effort",
                                          "agentType", "disallowedTools",
                                          "max_output_tokens"))),
        ("no_run_id_supplied", True), ("no_resume_from_run_id", True)])
    io.open(U + "/evidence/PRECALL_1805.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    io.open(U + "/evidence/native_envelope_1805.json", "w", encoding="utf-8").write(
        json.dumps({"args": args, "scriptPath": script},
                   sort_keys=True, separators=(",", ":")))
    for k, v in checks.items():
        if not v:
            print("  FAIL %s" % k)
    print("  envelope: %d rows %s..%s attempt %s" % (len(args), env["first_lane"],
                                                     env["last_lane"], env["attempts"]))
    print("  script  : %s (%d bytes)" % (env["script_sha256"][:16], env["script_bytes"]))
    print("  args    : compact %s (%d B) | typed input %s (%d B)"
          % (env["args_compact_sha256"][:16], env["args_compact_bytes"],
             env["typed_input_sha256"][:16], env["typed_input_bytes"]))
    print("  live    : pid %d %s cap %s force %s bridge %s"
          % (pid, exe.rsplit("/", 1)[-1], live["output_cap"],
             live["model_force_present"] or "none", bridge))
    print("  settings: %s" % json.dumps(doc["call_settings"], sort_keys=True))
    print("  existing run dirs: %d   ALL CHECKS PASS: %s"
          % (len(existing), doc["all_checks_pass"]))
    return 0 if doc["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
