#!/usr/bin/env python3
"""Regenerate rev4_pin_inventory.md FROM the files themselves.

WHY IT IS GENERATED. v3 carried 74 rows pinning the inventory to ITSELF. v4
dropped those but still addressed every pin by `file:LINE`, and a line number is
not a durable anchor: adding one sentence anywhere above a pin silently
invalidates 73 of the 76 rows while every hash stays correct. The inventory then
says "re-stamp line 810" about a line that has moved, which is worse than saying
nothing.

WHAT THE ANCHOR IS NOW. Each row is keyed by (file, nearest enclosing Markdown
heading, pinned sha). A heading survives reflowing, insertion and deletion of
surrounding prose; it changes only when the section it names is genuinely
renamed, which is exactly when a pin SHOULD be revisited. Occurrences that share
one (file, heading, sha) collapse into one row with a count, so repeated stamps
in a long history section stop producing dozens of near-identical lines.

This is deliberately the same shape as `make_g_ledger.py`: one file, one
purpose, no framework, no template engine, no config.

Run: venv/bin/python harness/make_pin_inventory.py [--check]
"""
import ast
import hashlib
import io
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
INVENTORY = os.path.join(_HERE, "rev4_pin_inventory.md")

# EACH PIN NAMES A REAL ARTIFACT, so the hash is RECOMPUTED from that file
# rather than merely located as text. The first version only grepped for the
# hex string, which confirms a pin is PRESENT and says nothing about whether it
# is still TRUE — and one of the three had already gone stale.
PINS = {
    "aa7239ed": ("packet v1.0",
                 ".claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md"),
    "86b2fc17": ("packet pre-amendment",
                 ".claude/plans/Drivers/FinalDesign/archive/"
                 "2026-07-15_pre-consolidation/15_CandidateFactPacket.pre-amendment.md"),
    "d91443f8": ("WorkOrder v2.0",
                 ".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md"),
}


# THE HASH METHOD, stated: sha256 of the file's exact bytes, first 8 hex
# characters. An unlabelled digest is a pin nobody else can reproduce.
HASH_METHOD = "sha256(file bytes), first 8 hex"


def committed_bytes(rel):
    """The file's bytes AS THE COMMIT WOULD HAVE THEM, or None if absent.

    THE INDEX IS THE COMMIT. `git show :path` reads the staged content, which is
    exactly what `git commit` will record — for every path in the index, whether
    this work changed it or not.

    THE RULE THIS REPLACES kept a side list of untracked files "declared" for the
    commit and read those from DISK instead. Two registers described one commit,
    and a file could be declared without ever being staged — which is precisely
    how this artifact came to describe a tree that would never exist. A file that
    belongs in the commit is a file in the index; there is no second register.
    """
    got = subprocess.run(["git", "show", f":{rel}"], cwd=_REPO,
                         capture_output=True)
    return got.stdout if got.returncode == 0 else None


def verify_pins():
    """pin -> (label, artifact, recomputed, agreement). AGREES / DIFFERS / ABSENT.

    DELIBERATELY NOT "stale". Whether a difference is a DEFECT depends on what
    the occurrence CLAIMS, and that is decided per occurrence below — a dated
    record row stating what was true when written is not wrong merely because the
    file moved on afterwards.
    """
    out = {}
    for pin, (label, rel) in PINS.items():
        raw = committed_bytes(rel)
        if raw is None:
            out[pin] = (label, rel, "", "ABSENT")
            continue
        got = hashlib.sha256(raw).hexdigest()
        out[pin] = (label, rel, got[:8],
                    "AGREES" if got.startswith(pin) else "DIFFERS")
    return out


# WHAT AN OCCURRENCE CLAIMS — from the document's STRUCTURAL MARKER, never a
# substring search.
#
# WHY THIS WAS WRONG BEFORE. `"CURRENT" in line` classified by the word appearing
# ANYWHERE, so a dated round record that merely MENTIONS "a CURRENT pin line
# added", and a table row in this programme's own audit ledger reading "CURRENT
# claims whose pin...", were both read as live pins. That is the exact
# history-damage risk this split exists to prevent: mark a dated record "wrong"
# and the repair is to edit history.
#
# THE MARKER is the live-pin form these records actually use: the line OPENS with
# a bold CURRENT token, optionally inside a blockquote —
#     > **CURRENT (2026-07-25):** WorkOrder v2.0 (sha `d91443f8...`)
# A dated round row opens with its date; a Markdown table cell opens with `|`;
# and anything inside a fenced code block is QUOTED text, not a claim this
# document is making.
_CURRENT_MARKER = re.compile(r"\s*>?\s*\*\*CURRENT\b")


def _roles_for(lines):
    """Role per line index, fence-aware. Quoted text never claims anything."""
    roles, fenced = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            fenced = not fenced
            roles.append("dated record")
            continue
        roles.append("current claim"
                     if not fenced and _CURRENT_MARKER.match(line)
                     else "dated record")
    return roles

# WHAT KIND OF FILE HOLDS THE PIN, derived from the path. This replaces a
# hand-written status+action table that was a SECOND authority of its own and got
# it wrong: a blanket `.py` rule labelled two build scripts and a test file
# "CURRENT binding · moves in the atomic migration commit", which is a claim
# about production wiring that none of them make. No editorial action column is
# emitted at all — the disposition lives in the package, in one place.
def _kind(rel):
    base = os.path.basename(rel)
    if "/archive/" in rel:
        return "archived history"
    if base.startswith("test_"):
        return "test"
    if base.startswith(("build_", "make_", "rev3_", "rev4_")):
        return "build script"
    if rel.startswith("driver/"):
        return "production"
    if base == "exp5_rev4_package.md":
        return "package"
    return "record"

# NEVER pin the inventory to itself, and never pin the generator either.
_SELF = {"rev4_pin_inventory.md", "make_pin_inventory.py"}

# PART F OWNS THE ACTIONS. This inventory says what each pin IS and where it is
# written; what should be DONE about one is Part F's, and only Part F's. The
# heading is named here so the link is checkable rather than a polite mention —
# rename the section and the check fails.
ACTION_OWNER = ("exp5_rev4_package.md",
                "PART F — GOVERNING-DOCUMENT CHANGES")


def _heading_for(lines, i):
    """The nearest enclosing Markdown heading above line `i`, or the file itself."""
    for j in range(i, -1, -1):
        m = re.match(r"\s{0,3}(#{1,6})\s+(.*\S)", lines[j])
        if m:
            return re.sub(r"\s+", " ", m.group(2))
    return "(file preamble)"


def _py_anchor(text, i):
    """The enclosing top-level def/class of line `i` — a DURABLE anchor for code.

    Markdown headings do not exist in a `.py` or `.json` file, so every such row
    used to anchor on the literal string "(file preamble)", which is not a
    semantic anchor at all: two pins in different parts of one script were
    indistinguishable, and neither moved when the code did.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "(unparsable module)"
    best = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and node.lineno - 1 <= i <= (node.end_lineno or node.lineno) - 1:
            best = f"{type(node).__name__.replace('Def', '').lower()} {node.name}"
    return best or "(module level)"


def _json_anchor(lines, i):
    """The nearest object key at or above line `i` — the durable anchor for JSON."""
    for j in range(i, -1, -1):
        m = re.search(r'"([^"]+)"\s*:', lines[j])
        if m:
            return f'key "{m.group(1)}"'
    return "(document root)"


def _anchor_for(rel, text, lines, i):
    if rel.endswith(".md"):
        return _heading_for(lines, i)
    if rel.endswith(".py"):
        return _py_anchor(text, i)
    return _json_anchor(lines, i)


def _targets():
    """THE REPRODUCIBLE SET, as (relative path, exact committed text) pairs.

    The previous version walked the WORKING TREE, so the generated inventory
    depended on files outside the commit — four of them dirty at the time — and a
    fresh clone regenerating it got a different answer, which makes the committed
    artifact unverifiable. The universe is now the INDEX and nothing else, so the
    inventory reproduces from the commit alone.
    """
    universe = sorted(subprocess.run(["git", "ls-files"], capture_output=True,
                                     text=True, cwd=_REPO).stdout.split())
    assert universe, "git named no files — the scan has no premise"
    seen = 0
    for rel in universe:
        if not rel.startswith((".claude/plans/Drivers/", "driver/")):
            continue
        if os.path.basename(rel) in _SELF or not rel.endswith((".md", ".py", ".json")):
            continue
        # CONTENT COMES FROM THE COMMIT, not the working tree. Restricting which
        # PATHS are scanned was not enough: a tracked file with uncommitted edits
        # still contributed its DIRTY text, so the artifact still could not be
        # reproduced from the commit. A manifest file is read from disk (that IS
        # what will be committed); every other tracked file is read at HEAD.
        #
        # THE TRADE, stated: pin references added by another track's uncommitted
        # edits are not listed until they are committed. That is correct for a
        # COMMITTED artifact — it must describe the committed tree — and the
        # generator can always be run against a working tree separately.
        raw = committed_bytes(rel)          # THE one content rule
        if raw is None:
            continue
        text = raw.decode("utf-8", errors="replace")
        seen += 1
        yield rel, text
    assert seen, "no scannable file under the pinned roots — the scan is broken"


def collect():
    """(file, heading, sha, role) -> occurrence count, for every pinned sha."""
    found = {}
    for rel, text in _targets():
        if not any(sha in text for sha in PINS):
            continue
        lines = text.splitlines()
        roles = _roles_for(lines)        # fence-aware, computed ONCE per file
        for i, line in enumerate(lines):
            for sha in PINS:
                if sha in line:
                    key = (rel, _anchor_for(rel, text, lines, i), sha, roles[i])
                    found[key] = found.get(key, 0) + 1
    return found


def render():
    found = collect()
    verified = verify_pins()
    out = ["# Rev-4 pin inventory v9 — DERIVED from the INDEX (the commit "
           "itself); each pin RECOMPUTED; each occurrence classified by a "
           "STRUCTURAL marker; actions owned by Part F",
           "",
           "Do not edit by hand: run `make_pin_inventory.py` and commit the result.",
           "",
           f"Hash method: **{HASH_METHOD}**. An unlabelled digest is a pin nobody "
           "else can reproduce, so the method is stated rather than implied.",
           "",
           "v4 addressed pins by `file:LINE`. A line number is not durable — one "
           "inserted sentence invalidated 73 of 76 rows while every hash stayed "
           "correct. Rows are keyed by the nearest enclosing heading, which moves "
           "only when the section is genuinely renamed. The inventory never lists "
           "itself or its generator.",
           "",
           "v5 only LOCATED the hash text, which proves a pin is present and says "
           "nothing about whether it still describes its artifact. v6 recomputed, "
           "but called every difference STALE — which mislabels a dated record as "
           "a defect. **v7 separates the two:** a pin is recomputed ONCE, and each "
           "PLACE it is written is classified from its own line as a **current "
           "claim** or a **dated record**. Only a current claim can be WRONG. A "
           "record row states what was true on its date and is never corrected; "
           "a correction is APPENDED beside it.",
           "",
           f"**This inventory takes no action and owns none.** What should be "
           f"DONE about a pin lives in `{ACTION_OWNER[0]}` -> "
           f"**{ACTION_OWNER[1]}**, which is its sole owner. v8 dropped that "
           f"relationship silently, and an inventory that hints at actions "
           f"beside an owner that decides them is two authorities on one "
           f"question. Rows below say what each pin IS and where it is written; "
           f"read Part F for what happens next.",
           "",
           f"## Each pin, recomputed ({HASH_METHOD})",
           "",
           "| pin | names | artifact | recomputed | agreement |",
           "|---|---|---|---|---|"]
    for pin, (label, rel, got, agree) in sorted(verified.items()):
        out.append(f"| `{pin}` | {label} | `{rel}` | `{got or '—'}` | "
                   f"**{agree}** |")
    out += ["",
            "## Where each pin is written, and what that place CLAIMS",
            "",
            "| file | kind | semantic anchor (nearest heading) | pin | claims | n |",
            "|---|---|---|---|---|---|"]
    for key in sorted(found):
        rel, heading, sha, role = key
        out.append(f"| `{rel}` | {_kind(rel)} | {heading} | "
                   f"{sha} ({PINS[sha][0]}) | {role} | {found[key]} |")
    # THE ONLY DEFECT CLASS: a place that claims to be CURRENT while its pin no
    # longer describes the artifact. Everything else is history and stands.
    # KEYED BY THE ANCHOR TOO. Deduping on (file, pin) collapsed several distinct
    # misclassified occurrences in ONE file into a single reported row, so the
    # summary read "1" while three separate places were wrong — the count hid the
    # very defect it was meant to expose.
    wrong = sorted({(key[0], key[1], key[2]) for key in found
                    if key[3] == "current claim"
                    and verified[key[2]][3] != "AGREES"})
    out += ["",
            "| | |",
            "|---|---|",
            f"| **CURRENT claims whose pin no longer describes its artifact** | "
            f"**{len(wrong)}**"
            + ("".join(f"<br>`{f}` — {h} -> `{pin}`" for f, h, pin in wrong)
               if wrong else "")
            + " |",
            f"| dated record occurrences (stand as written, never corrected) | "
            f"{sum(n for k, n in found.items() if k[3] == 'dated record')} |",
            f"| rows | {len(found)} |",
            f"| distinct files | {len({k[0] for k in found})} |",
            f"| total occurrences | {sum(found.values())} |"]
    return "\n".join(out) + "\n"


def main():
    text = render()
    if "--check" in sys.argv:
        on_disk = (io.open(INVENTORY, encoding="utf-8").read()
                   if os.path.exists(INVENTORY) else "")
        if on_disk != text:
            print("STALE: rev4_pin_inventory.md differs from the files")
            sys.exit(1)
        print("pin inventory matches the files")
        return
    io.open(INVENTORY, "w", encoding="utf-8").write(text)
    print(f"wrote {INVENTORY} "
          f"(sha256 {hashlib.sha256(text.encode()).hexdigest()[:12]})")


if __name__ == "__main__":          # IMPORTING must not write, print, exit or
    main()                          # spawn anything — the ledger's own lesson
