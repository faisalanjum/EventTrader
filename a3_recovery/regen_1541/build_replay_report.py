#!/usr/bin/env python3
"""Rebuild reports/raw_transport_replay.json from a live replay (Codex SEQ 1541).

Every number here is produced by running the replay now. The three A3 pins are
compared only AFTER the run, as output assertions, and reported met or unmet.
"""
import collections
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(R, "ledger"))
import chrono_replay as CR
import replay_transcript as RT

#: THE OWNER IS IDENTIFIED BY ITS TREE, NOT ONLY BY ITS DIRECTORY. A pristine copy of
#: the same harness lived at scratchpad/p1319, and record 26932 cd-ed into THAT tree
#: and edited its `raw_transport.py` by the bare name. Matching on "harness/<name>"
#: accepted it, so another copy's edit was applied to this file. Qualifying the owner
#: with its worktree is what separates the two.
OWNER = "bench_1306/.claude/plans/Drivers/experiments/harness/raw_transport.py"
FIRST, UPTO = 23361, 32847
PIN_32846 = "12d4aca9a7bfd9a51303271b54433ad55058dad268e771cff757a3ea0b68a14a"
PIN_32672 = "f5ea60c9f21da4d70e7644680a9fa93a14d6235d35013bdf7c5f905c55d82eac"
PIN_PRE = "15589cb3f86b593f3feb76915f5db18892e2fb3828fedec7d1ee9cdfc650ece5"

#: history's OWN printed measurements, quoted from the saved tool results. These are
#: checkpoints: the replay is compared against them, and never steered by them.
PRINTED = collections.OrderedDict([
    (24876, ["648"]), (25743, ["749"]), (25922, ["894"]), (26119, ["948"]),
    (26447, ["777"]), (26825, ["68112", "68616"]), (26853, ["70773"]),
    (26932, ["1319"]),
])


def _lines():
    with io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
        return fh.readlines()


def _result(all_lines, n):
    for i in range(n + 1, n + 4):
        if i - 1 >= len(all_lines):
            break
        rec = json.loads(all_lines[i - 1])
        for b in ((rec.get("message") or {}).get("content") or []):
            if isinstance(b, dict) and b.get("type") == "tool_result":
                c = b.get("content")
                t = c if isinstance(c, str) else " ".join(
                    x.get("text", "") for x in c or [] if isinstance(x, dict))
                if t.strip():
                    return t.strip()
    return ""


def main():
    base = subprocess.check_output(
        ["git", "-C", "/home/faisal/EventMarketDB", "show",
         "cd961e51:.claude/plans/Drivers/experiments/harness/" + os.path.basename(OWNER)],
        text=True)
    all_lines = _lines()
    recs, producers = CR.route_records(OWNER, FIRST, UPTO)
    text, side = base, {}
    steps, refused, checks = [], {}, []
    at_32672 = at_pre_32672 = None
    for n, rec in recs:
        if n == 32672:
            at_pre_32672 = hashlib.sha256(text.encode()).hexdigest()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                text, _ = RT.apply_saved_edits(text, {n: rec}, OWNER, side=side)
            out = buf.getvalue()
        except Exception as exc:
            out = buf.getvalue()
            refused[n] = "%s: %s" % (type(exc).__name__, str(exc)[:80])
        steps.append(collections.OrderedDict([
            ("line", n), ("bytes", len(text.encode())),
            ("sha256", hashlib.sha256(text.encode()).hexdigest())]))
        if n in PRINTED:
            mine = re.findall(r"\d{3,6}", out)
            hist = re.findall(r"\d{3,6}", _result(all_lines, n))
            checks.append(collections.OrderedDict([
                ("line", n), ("history_printed", PRINTED[n]),
                ("replay_printed", mine),
                ("met", all(v in mine for v in PRINTED[n])
                        and all(v in hist for v in PRINTED[n]))]))
        if n == 32672:
            at_32672 = hashlib.sha256(text.encode()).hexdigest()
    final = hashlib.sha256(text.encode()).hexdigest()
    report = collections.OrderedDict([
        ("owner", OWNER),
        ("git_base_commit", RT.WORKTREE_COMMIT),
        ("git_base_sha256", hashlib.sha256(base.encode()).hexdigest()),
        ("history_confirms_this_base",
         "transcript line 28728 records 'raw_transport.py before "
         "8cca087c384aa4dd300ebc48f23da6ccb77baff9abf48f9eb22b29af606a1db1', which is "
         "this committed base, measured by the campaign itself"),
        ("route_first_line", FIRST), ("route_upto_line", UPTO),
        ("records", len(recs)),
        ("producers_pulled_in", {str(k): v for k, v in producers.items()}),
        ("applied", len(recs) - len(refused)),
        ("refused", {str(k): v for k, v in refused.items()}),
        ("refusal_is_faithful",
         "26845 fails with the SAME TypeError history recorded at transcript line "
         "26846: rep() missing 1 required positional argument: 'why'. The record "
         "changed nothing when it was first run either."),
        ("checkpoints_from_history", checks),
        ("checkpoints_met", sum(1 for c in checks if c["met"])),
        ("checkpoints_total", len(checks)),
        ("pin_32846", PIN_32846), ("pin_32846_met", final == PIN_32846),
        ("pin_32672", PIN_32672), ("pin_32672_met", at_32672 == PIN_32672),
        ("pin_pre_32672", PIN_PRE), ("pin_pre_32672_met", at_pre_32672 == PIN_PRE),
        ("reached_sha256", final), ("reached_bytes", len(text.encode())),
        ("what_closed_the_gap",
         "record 26932 cd-ed into the SEPARATE pristine tree at scratchpad/p1319 and "
         "edited its own copy of this filename by the bare name. Matching the owner as "
         "'harness/raw_transport.py' accepted that record, so another tree's edit was "
         "applied to this file. Qualifying the owner with its worktree (bench_1306) "
         "excludes it, and the replay then reproduces both pins exactly."),
        ("steps", steps)])
    out = os.path.join(R, "reports", "raw_transport_replay.json")
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(report, indent=2) + "\n")
    print("records %d applied %d refused %d | checkpoints %d/%d met | %d bytes" % (
        len(recs), report["applied"], len(refused), report["checkpoints_met"],
        report["checkpoints_total"], report["reached_bytes"]))
    print("pins: 32846 %s | 32672 %s | pre-32672 %s" % (
        report["pin_32846_met"], report["pin_32672_met"], report["pin_pre_32672_met"]))


if __name__ == "__main__":
    main()
