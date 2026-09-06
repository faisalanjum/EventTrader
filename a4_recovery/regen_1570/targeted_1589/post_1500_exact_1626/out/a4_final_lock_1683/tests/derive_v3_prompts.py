# -*- coding: utf-8 -*-
"""Recover the exact v3 prompt pair from the recorded v1 -> v2 -> v3 commands
(Codex SEQ 1700/1702).

No copy of the v2 or v3 bytes survives anywhere, so they are DERIVED, and the
derivation is only trusted because every stage is gated on its recorded hash and
size. The two edit operations are not retyped: the recorded Bash commands are
read out of the accepted transcript by their tool-use UUID, their embedded
Python is parsed, and the OLD/NEW and R5A/R6 literals are taken from that source
of truth. The insertion positions are the recorded ones; if any of it were off
by a byte the stage hashes would not match and nothing is written.

Provenance goes into the one existing projection owner, PROJECTION_PLACED.tsv.
"""
import ast
import hashlib
import io
import json
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
HV = UNIT + "/bench/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
MAN = UNIT + "/manifest/PROJECTION_PLACED.tsv"
BENCH_REL = ".claude/plans/Drivers/experiments/harness_g1v3/"
TRANSCRIPT = R + "/a3_recovery/regen_1541/evidence/transcript/accepted_prefix.jsonl"

RULE7_UUID = "b0e5b649-53bd-46cd-96be-7c62c0ae42e3"
R5A_R6_UUID = "4ba50a26-2b95-4c8d-a8b3-eb1a47de2ebc"

# v1 -> v2 -> v3, each stage pinned by Codex SEQ 1700
V1 = {"drafter": ("a13289a8a135fe7f26beaeef1168a219496f197345063c963e677fa7fa452fef", 23953),
      "producer": ("8d3d7231ab3cc4c702eecfebec99221300e8fb2f122776fd23ce7cbb380000a9", 25844)}
V2 = {"drafter": ("ee507e67b93eceb190c9aa0bdd040562ae73a4a8f15bc53308b84072b506b3f0", 24141),
      "producer": ("ad30204054d4edd86e12746aea661601420ed1cd995bf06486636d096934b1b0", 26032)}
V3 = {"drafter": ("421613e2998cb29b4482507b2713bbf225dcd71bdbf61f7cf613871a4e25030c", 24630),
      "producer": ("b8bcbf0f4712218db1578cefbc3508e762b0db938c9fbf44996a98bc6e5f3f57", 26521)}

# durable v1 carriers, accepted only at their pinned bytes
V1_SRC = {"drafter": HV + "/exp5_prompt_drafter.md",
          "producer": (R + "/a3_recovery/regen_1541/bench/.claude/plans/Drivers"
                           "/experiments/harness/exp5_prompt_producer.md")}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def gate(stage, role, text, pins):
    b = text.encode("utf-8")
    want_sha, want_len = pins[role]
    ok = sha(b) == want_sha and len(b) == want_len
    print("%s %-8s %-8s %6d bytes (want %6d)  %s"
          % ("ok  " if ok else "BAD ", stage, role, len(b), want_len, sha(b)[:16]))
    if not ok:
        sys.exit("REFUSED at %s/%s: %s != %s" % (stage, role, sha(b)[:16], want_sha[:16]))
    return b


def recorded_command(uuid):
    """The Bash command of the recorded tool_use with this UUID."""
    for ln in io.open(TRANSCRIPT, encoding="utf-8"):
        if uuid not in ln:
            continue
        d = json.loads(ln)
        if d.get("uuid") != uuid or d.get("type") != "assistant":
            continue
        for b in d["message"]["content"]:
            if b.get("type") == "tool_use":
                return b["input"]["command"]
    sys.exit("REFUSED: no recorded tool_use %s" % uuid)


def literals(command, names):
    """Module-level string literals of the Python heredoc inside a recorded command."""
    body = command.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    tree = ast.parse(body)
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id in names:
            out[n.targets[0].id] = ast.literal_eval(n.value)
    missing = set(names) - set(out)
    if missing:
        sys.exit("REFUSED: recorded command has no %s" % sorted(missing))
    return out


rule7 = literals(recorded_command(RULE7_UUID), ("OLD", "NEW"))
ins = literals(recorded_command(R5A_R6_UUID), ("R5A", "R6"))
print("rule 7 substitution  : %d -> %d bytes   (uuid %s)"
      % (len(rule7["OLD"].encode()), len(rule7["NEW"].encode()), RULE7_UUID))
print("R5A + R6 insertions  : %d + %d bytes    (uuid %s)"
      % (len(ins["R5A"].encode()), len(ins["R6"].encode()), R5A_R6_UUID))

placed = []
for role in sorted(V1):
    src = V1_SRC[role]
    v1 = io.open(src, encoding="utf-8").read()
    gate("v1", role, v1, V1)

    # the recorded Rule 7 edit: exactly one occurrence, replaced in place
    if v1.count(rule7["OLD"]) != 1:
        sys.exit("REFUSED: %s carries the Rule 7 block %d times" % (role, v1.count(rule7["OLD"])))
    v2 = v1.replace(rule7["OLD"], rule7["NEW"])
    gate("v2", role, v2, V2)

    # the recorded R5A/R6 insertions, at the recorded anchors
    lines = v2.splitlines(True)
    head = next(i for i, l in enumerate(lines) if l.startswith("**Rule 5a"))
    out = lines[:head + 1] + [ins["R5A"]] + lines[head + 1:]
    wire = next(i for i, l in enumerate(out) if l.startswith("The wire:"))
    out = out[:wire] + [ins["R6"]] + out[wire:]
    v3 = "".join(out)
    b3 = gate("v3", role, v3, V3)

    dst = HV + "/exp5_prompt_%s.v3.md" % role
    if os.path.isfile(dst):
        if open(dst, "rb").read() == b3:
            print("     already present at the derived byte: %s" % os.path.basename(dst))
            continue
        sys.exit("REFUSED: %s exists with different bytes" % dst)
    with open(dst, "wb") as fh:
        fh.write(b3)
    if open(dst, "rb").read() != b3:
        sys.exit("REFUSED: written copy differs")
    placed.append((BENCH_REL + os.path.basename(dst), V3[role][0],
                   "derived: %s (%s, %d) -> rule7@%s -> v2 %s (%d) -> R5A+R6@%s -> v3 (%d)"
                   % (src.replace(R + "/", ""), V1[role][0][:16], V1[role][1], RULE7_UUID,
                      V2[role][0][:16], V2[role][1], R5A_R6_UUID, V3[role][1])))

if placed:
    with io.open(MAN, "a", encoding="utf-8") as fh:
        for rel, h, prov in placed:
            fh.write("%s\t%s\t%s\n" % (rel, h, prov))
print("\nplaced %d file(s); manifest %s" % (len(placed), sha(open(MAN, "rb").read())[:16]))
