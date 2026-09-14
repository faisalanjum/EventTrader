#!/usr/bin/env python3
"""Rev-4 coverage gate — MACHINE-RUN, replaces the Part-J checklist sentence
that revision 3 claimed but never executed (the review's finding).

Two proofs, both mechanical:
  A. PATCH COVERAGE — apply the patch to temp copies; every governing doc then
     contains ZERO active old-rule residue markers. History is exempted ONLY
     inside explicitly marked superseded/history blocks.
  B. Every marker below names its doc and its meaning — a human meaning-review
     stays separate and is NOT claimed by this script.

Run: venv/bin/python harness/rev4_coverage_check.py <patch-file>
Exit 0 = clean; nonzero = residue listed. RED against the rev-3 patch by
design — its failures ARE the rev-4 work list.
"""
import subprocess, sys, tempfile, shutil, os, io

# IMPORT MUST DO NOTHING: this resolved the repo root with a subprocess at module
# level, and the file ENDED with a bare `main(sys.argv[1])` — so importing it ran
# the whole gate and crashed with IndexError when there was no argv[1].
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = None


def repo():
    global _REPO
    if _REPO is None:
        _REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True,
                               cwd=_HERE).stdout.strip() or _HERE
    return _REPO
# Residue markers: text that may not remain ACTIVE after the patch.
RESIDUE = {
 ".claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md":
    ["level_unit_kind_hint", "level_money_mode_hint", "FROZEN v1.0", "code does format, measurement token normalization (OD-9), units,",
     "It hands the shared core ONE object"],
 ".claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md":
    ["29+7 green", "per-slot hints", "missing hint", "CLI order:** hints", "derive the missing hints"],
 ".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md":
    ["37 model-owned", "GLOBAL 1-based", "never reset per part", "level_unit_kind_hint", "sequential_evidence \u00b7", "gold_item", "OPEN OWNER DECISION", "else exact\nquote equality", "1:1 fixpoint"],
 ".claude/plans/Drivers/experiments/keys/K-fields/protocol.md":
    ["GLOBAL 1-based count", "gold_item", "the 37", "producer-only (never in the gold key)"],
 ".claude/plans/Drivers/experiments/harness/exp5_scoring_spec_v3.md":
    ["TO BE PROVEN", "20-char overlap", "PreparedFactV1", "GLOBAL 1-based", "NOT proven today"],
 ".claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md":
    ["unit-kind hint", "per-X lint (money level"],
}
SUPERSEDED_MARKS = ("history above unedited",)   # narrowed: no broad word-contains exemption
import re
HISTORY_LINE = re.compile(r"^> \*\*v\d")   # blockquoted status-history entries: exempt, never edited

def main(patch):
    tmp = tempfile.mkdtemp()
    fails = []
    # stage EVERY file the patch touches (derived from the patch, never hand-listed)
    targets = set()
    for ln in io.open(patch, encoding="utf-8"):
        if ln.startswith("--- a/"):
            targets.add(ln[6:].strip())
    for rel in targets | set(RESIDUE):
        dst = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(os.path.join(repo(), rel)):
            continue                  # blocked/absent target: nothing to scan
        shutil.copy(os.path.join(repo(), rel), dst)
    r = subprocess.run(["git", "apply", "--unsafe-paths", "--directory", tmp, patch],
                       capture_output=True, text=True, cwd=repo())
    if r.returncode != 0:
        print("PATCH DID NOT APPLY to temp copies:", r.stderr[:300]); sys.exit(2)
    # A BLOCKED TARGET HAS NO HUNKS, so its residue is exactly what the missing
    # hunks would have removed — reporting it as a failure would say "the rev-4
    # work is incomplete" when the truth is "another track's document is not
    # committed yet". The block list has ONE owner (the patch builder), and that
    # builder already fails if a blocked file would build cleanly, so this cannot
    # become a way to hide live residue.
    sys.path.insert(0, _HERE)
    from rev4_build_patch import BLOCKED
    for rel in sorted(set(RESIDUE) & set(BLOCKED)):
        print(f"RESIDUE NOT SCANNED (blocked target, no hunks): {rel}\n"
              f"    {BLOCKED[rel]}")
    for rel, markers in RESIDUE.items():
        if rel in BLOCKED:
            continue
        text = io.open(os.path.join(tmp, rel), encoding="utf-8").read()
        # strip lines inside/announcing superseded blocks from the scan
        active = "\n".join(ln for ln in text.splitlines()
                           if not any(m in ln for m in SUPERSEDED_MARKS)
                           and not HISTORY_LINE.match(ln))
        for m in markers:
            n = active.count(m)
            if n:
                fails.append(f"{rel}: ACTIVE residue {m!r} x{n}")
    # SCHEMA EQUALITY: the WorkOrder field list == the package A3 item keys,
    # derived both sides.
    import re as _re
    _WO = ".claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md"
    pkg = io.open(os.path.join(
        repo(),
        ".claude/plans/Drivers/experiments/harness/exp5_rev4_package.md"),
        encoding="utf-8").read()
    pm = _re.search(r'"item": \{\n(.*?)\n    \}\}', pkg, _re.S)
    pkg_fields = set(_re.findall(r'"([a-z_]+)":', pm.group(1))) if pm else set()
    if len(pkg_fields) != 32:
        fails.append(f"package A3 item block has {len(pkg_fields)} keys, not 32")
    if _WO in BLOCKED:
        # THE HALF THAT CANNOT RUN, SAID OUT LOUD. The only document that
        # ENUMERATES the 32 names is the WorkOrder, and that enumeration is
        # itself created by the blocked hunks \u2014 no committed file lists them
        # (`protocol.md` refers to "the 32 fields" in a comment; the plan states
        # only the count). So name-level equality is unavailable here, while the
        # package-side count is still proven above. Removing the block restores
        # the full check with no further edit.
        print("SCHEMA EQUALITY, NAME LEVEL: NOT CHECKED \u2014 the field list it "
              "compares against is created by the blocked WorkOrder hunks. "
              "Package-side count (32) IS checked.")
    else:
        wo = io.open(os.path.join(tmp, _WO), encoding="utf-8").read()
        m = _re.search(r"the 32 model-owned fields:\n(.*?)\n\(each of the five",
                       wo, _re.S)
        if not m:
            fails.append("WorkOrder: 32-field list block not found in the expected shape")
        else:
            wo_fields = {t.strip().rstrip("[]") for t in
                         m.group(1).replace("\n", " ").split("\u00b7") if t.strip()}
            if wo_fields != pkg_fields:
                fails.append(f"SCHEMA MISMATCH: WorkOrder-only={sorted(wo_fields - pkg_fields)} package-only={sorted(pkg_fields - wo_fields)}")
    if fails:
        print("RESIDUE FOUND (the rev-4 work list):")
        for f in fails: print("  ", f)
        sys.exit(1)
    # STATE EXACTLY WHAT RAN. The old line claimed "schema list equality holds"
    # unconditionally, which would have been an overclaim the moment any part of
    # it was skipped — the same defect class this round is repairing elsewhere.
    _blocked = sorted(set(RESIDUE) & set(BLOCKED))
    print("COVERAGE CLEAN: zero active old-rule residue after patch in "
          f"{len(RESIDUE) - len(_blocked)} of {len(RESIDUE)} scanned documents; "
          "the package's 32-key item block is verified"
          + (f". NOT CHECKED: {len(_blocked)} blocked target(s) "
             f"({', '.join(b.rsplit('/', 1)[-1] for b in _blocked)}) and the "
             f"name-level schema equality that depends on them."
             if _blocked else "; name-level schema equality holds."))
if __name__ == "__main__":
    main(sys.argv[1])
