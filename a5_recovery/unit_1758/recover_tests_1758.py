# -*- coding: utf-8 -*-
"""Core SEQ 1757 / Codex SEQ 1758 step 2 - recover the two changed A5-era tests.

Their edits are recorded literally inside the reversal program the original run
executed (transcript record 88543). That program applies the pairs BACKWARD; the
A5-era bytes are the same pairs applied FORWARD to each recorded base. The pairs
are parsed out of the recorded command, never retyped.
"""
import ast
import hashlib
import io
import json
import os
import subprocess
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
T = R + "/a3_recovery/regen_1541/evidence/transcript/accepted_prefix.jsonl"
RECORD = 88543
UNIT = os.path.dirname(os.path.abspath(__file__))
OWNERS = UNIT + "/owners"
EV = UNIT + "/evidence"

# base -> A5-era result, exactly as Core SEQ 1514 reported them at record 88564
WANT = {
    "test_a5_contract_1401.py": (
        "23deb88ab4def94cfa183b181d926d2cddbf8d029ea65b604fef7328156d64cf",
        "523ede2853e8ac4b3ffe857e5b7fbc6775200f70ab4af8a173a31a92e78f9e67"),
    "test_harness_guards.py": (
        "4b8bb7acd585ad4dbfd9be64892236c2f33441aa92f1a21042cfdba1a1fe9237",
        "24e4f441603fce225f4a09aae50f2b5817efd5a50bc8db41c3a9d0ddcfaaa37f"),
}
CHECKS = []


def sha(b):
    return hashlib.sha256(b).hexdigest()


def check(name, got, want):
    ok = got == want
    CHECKS.append((name, ok))
    print("%s %-56s %s%s" % ("ok  " if ok else "BAD ", name, str(got)[:66],
                             "" if ok else "  != %s" % str(want)[:66]), flush=True)
    return ok


def recorded_command(path, line_no):
    line = subprocess.run(["sed", "-n", "%dp" % line_no, path],
                          capture_output=True, text=True).stdout
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "tool_use" and o.get("name") == "Bash":
                found.append(o["input"]["command"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(json.loads(line))
    if len(found) != 1:
        raise SystemExit("REFUSED: record %d holds %d shell commands" % (line_no, len(found)))
    return found[0]


def heredoc_body(cmd):
    """The python program the recorded command fed on stdin."""
    lines = cmd.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip().endswith("<<'PYEOF'"))
    end = next(i for i, l in enumerate(lines) if i > start and l.strip() == "PYEOF")
    return "\n".join(lines[start + 1:end])


def pairs_for(src, basename):
    """Every (old, new) literal the recorded program lists for one owner."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or getattr(node.func, "id", None) != "reverse":
            continue
        target = ast.get_source_segment(src, node.args[0]) or ""
        if basename not in target:
            continue
        return [(ast.literal_eval(e.elts[0]), ast.literal_eval(e.elts[1]))
                for e in node.args[1].elts]
    raise SystemExit("REFUSED: record %d lists no edits for %s" % (RECORD, basename))


def find_by_hash(basename, want_sha):
    """A durable copy whose bytes are exactly the recorded base."""
    out = subprocess.run(
        ["find", R, "/home/faisal/.core827_backups", "-name", basename], capture_output=True, text=True)
    for p in out.stdout.split():
        try:
            b = io.open(p, "rb").read()
        except OSError:
            continue
        if sha(b) == want_sha:
            return p, b
    return None, None


os.makedirs(OWNERS, exist_ok=True)
os.makedirs(EV, exist_ok=True)
prog = heredoc_body(recorded_command(T, RECORD))
io.open(EV + "/record_%d_program.py" % RECORD, "w", encoding="utf-8").write(prog)
check("the recorded program parses", bool(ast.parse(prog)), True)

report = []
for basename, (base_sha, want_sha) in WANT.items():
    print("\n== %s ==" % basename)
    pairs = pairs_for(prog, basename)
    check("%s: edits recorded" % basename, len(pairs) > 0, True)
    path, data = find_by_hash(basename, base_sha)
    if data is None:
        check("%s: its recorded base is on disk" % basename, False, True)
        report.append((basename, "BASE MISSING %s" % base_sha[:16], None))
        continue
    print("  base found at %s" % path.replace(R + "/", "").replace("/home/faisal/", "~/"))
    text = data.decode("utf-8")
    ok = True
    for i, (old, new) in enumerate(pairs, 1):
        if not check("%s: edit %d applies exactly once" % (basename, i), text.count(old), 1):
            ok = False
            break
        text = text.replace(old, new)
    if not ok:
        report.append((basename, "EDIT DID NOT APPLY", None))
        continue
    got = sha(text.encode("utf-8"))
    if check("%s: recovered sha256" % basename, got, want_sha):
        io.open(OWNERS + "/" + basename, "w", encoding="utf-8").write(text)
        report.append((basename, "recovered", got))
    else:
        report.append((basename, "MISMATCH %s" % got[:16], got))

io.open(EV + "/tests_recovery.txt", "w", encoding="utf-8").write(
    "\n".join("%s\t%s\t%s" % r for r in report) + "\n")
bad = [n for n, ok in CHECKS if not ok]
print("\nchecks %d  failed %d  %s" % (len(CHECKS), len(bad), bad))
for r in report:
    print("  %-30s %s" % (r[0], r[1]))
sys.exit(1 if bad else 0)
