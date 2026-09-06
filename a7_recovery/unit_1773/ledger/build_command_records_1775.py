# -*- coding: utf-8 -*-
"""Bind every preserved log to the launch that actually produced it.

Codex SEQ 1775 item 3. The earlier record matched the latest transcript mention
of a payload name, which for the test suites was a script-definition line rather
than the launch of the log that now stands. Every binding here is an explicit
(log, transcript line, tool_use id) pointer, and each one is VERIFIED against
the transcript before it is written: the line must parse, carry that tool_use
id, and its command must name the log it claims to have produced.

  * both generations of a re-run log are kept; history is not overwritten
  * the FULL linked tool_result is retained, never a truncated head
  * a background launch does not record the payload's numeric exit merely
    because the launching shell returned, so an unrecorded payload exit is
    written as "not captured" - never invented as 0. Where the payload wrote
    its own exit into its records, that recorded exit is cited instead.
"""
import hashlib
import io
import json
import os

T = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = UNIT + "/evidence/COMMAND_RECORDS_1775.json"

#: (log, line, tool_use id, generation, what) - the pointers Codex supplied,
#: plus the two already-correct ones and the two foreground records.
BIND = [
    ("logs/reconstruct_1773.log", 174972, "toolu_01QjWZiqfDkWYzrWUv8h3Gop",
     "attempt 1 launch", "first reconstruction attempt"),
    ("logs/reconstruct_1773.log", 174994, "toolu_01UjE1J7vxfsWavRAMTw3W5U",
     "attempt 1 relaunch", "same log, second launch after the state index was added"),
    ("logs/reconstruct_1773b.log", 175064, "toolu_01CMkzJ88qa1ED8NWo5i6diz",
     "single", "child transcripts bound"),
    ("logs/reconstruct_1773c.log", 175096, "toolu_012ksjZn7iQeCAuycxYWZKhk",
     "single", "A7-era owners placed"),
    ("logs/reconstruct_1773d.log", 175101, "toolu_01SnVnvGbRzH2ua1PaFRpyY4",
     "single", "fixture bind path corrected"),
    ("logs/reconstruct_1773e.log", 175106, "toolu_01RNsohAoczoUdtxCQgcP2vW",
     "single", "closed A6 proof no longer re-run"),
    ("logs/reconstruct_1773f.log", 175154, None,
     "single", "THE ACCEPTED producer reconstruction"),
    ("logs/candidate_1773.log", 175179, "toolu_0115vE7Fny1z2dLwJJnBMw6F",
     "generation 1", "first candidate proof; probe read a root key from the candidate"),
    ("logs/candidate_1773b.log", 175211, None,
     "single", "THE ACCEPTED two-build candidate proof"),
    ("logs/tests_1774.log", 175411, "toolu_018SbhuPF4irH59r2R2Z1pfL",
     "generation 1 (superseded)", "three-suite list naming a module later replaced"),
    ("logs/tests_1774.log", 175554, "toolu_01Lesfcop2ZA8TiRG7Vo3a74",
     "generation 2 (the live log)", "the corrected two-suite run"),
    ("logs/mutations_1774.log", 175447, "toolu_01VRj6h3qhGHc528kAQ4w8WZ",
     "generation 1 (superseded)", "first mutation run; the boundary refused on a stale view pin"),
    ("logs/mutations_1774.log", 175466, "toolu_01WFedpWFKGoYsj5hV2XenF7",
     "generation 2 (the live log)", "THE ACCEPTED mutation cases, after the map was re-pinned"),
    ("logs/compose_views_1773.log", 175320, "toolu_01UQyc61Wt6DhPsgQQ9CqrKg",
     "single", "the view compose command, foreground, with its own recorded exit"),
]


def blocks(rec):
    c = ((rec.get("message") or {}).get("content"))
    return c if isinstance(c, list) else []


def main():
    lines = io.open(T, encoding="utf-8").read().splitlines(True)

    def parse(n):
        try:
            return json.loads(lines[n - 1])
        except (IndexError, ValueError):
            return None

    def line_sha(n):
        return hashlib.sha256(lines[n - 1].encode("utf-8")).hexdigest()

    # every tool_result in the transcript, by the id it answers
    results = {}
    for i, raw in enumerate(lines, 1):
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        for b in blocks(rec):
            if isinstance(b, dict) and b.get("type") == "tool_result":
                out = b.get("content")
                if isinstance(out, list):
                    out = "".join(x.get("text", "") for x in out
                                  if isinstance(x, dict))
                results[b.get("tool_use_id")] = (i, out if isinstance(out, str) else "")

    out, problems = [], []
    for log, line, tid, gen, what in BIND:
        rec = parse(line)
        cmd = found_id = None
        if rec:
            for b in blocks(rec):
                if (isinstance(b, dict) and b.get("type") == "tool_use"
                        and isinstance(b.get("input"), dict)):
                    if tid is None or b.get("id") == tid:
                        cmd = b["input"].get("command")
                        found_id = b.get("id")
                        break
        entry = {"log": log, "generation": gen, "what": what,
                 "transcript": T, "invocation_line": line,
                 "invocation_line_sha256": line_sha(line),
                 "tool_use_id": found_id, "command": cmd}
        if cmd is None:
            problems.append("%s: line %d carries no tool_use %s" % (log, line, tid))
            entry["verified"] = False
            out.append(entry)
            continue
        # the binding must be to the launch of THIS log, not a mention of it
        entry["names_this_log"] = os.path.basename(log) in cmd
        if not entry["names_this_log"]:
            problems.append("%s: line %d does not name this log" % (log, line))
        rln, rtext = results.get(found_id, (None, ""))
        entry["result_line"] = rln
        entry["result_line_sha256"] = line_sha(rln) if rln else None
        entry["result_full"] = rtext                      # FULL, never truncated
        # a background launch returns before the payload does
        bg = "setsid" in cmd or "nohup" in cmd
        entry["launch_kind"] = "background" if bg else "foreground"
        entry["payload_exit"] = (
            "not captured (background launch: the shell returned before the "
            "payload exited; no numeric payload exit was recorded)" if bg
            else "not captured (the shell recorded no separate payload exit)")
        entry["verified"] = bool(entry["names_this_log"])
        p = os.path.join(UNIT, log)
        if os.path.isfile(p):
            entry["log_sha256"] = hashlib.sha256(io.open(p, "rb").read()).hexdigest()
            entry["log_bytes"] = os.path.getsize(p)
        out.append(entry)

    doc = {"note": ("Every binding is an explicit pointer, verified against the "
                    "transcript. Payload exits that were never recorded are named "
                    "as such and never invented; the runs whose payloads DID record "
                    "their own numeric exits are the suite and per-case records."),
           "recorded_exits_elsewhere": {
               "logs/TEST_RECORDS.json": "each suite's real numeric exit, written at execution",
               "logs/MUTATION_RECORDS.json": "each case's real numeric exit, written at execution",
               "out/mutations/*/case.log": "per-case argv, stdout, stderr and exit",
               "logs/compose_views_1773.log": "foreground compose with its recorded [rc=0]",
               "logs/manifest_red_1775.log": "the retained red manifest check with its rc"},
           "bindings": out, "problems": problems}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, indent=1) + "\n")
    for e in out:
        print("  %-28s line %-7s %-26s %s" % (e["log"], e["invocation_line"],
                                              (e["tool_use_id"] or "-")[:26],
                                              "ok" if e["verified"] else "UNVERIFIED"))
    print("problems: %d" % len(problems))
    for p in problems:
        print("   ", p)
    return len(problems)


if __name__ == "__main__":
    raise SystemExit(main())
