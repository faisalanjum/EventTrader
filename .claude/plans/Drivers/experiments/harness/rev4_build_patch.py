#!/usr/bin/env python3
"""Replay the historical rev-4 edit tables, not the current Step 6 migration.

The source documents have since been consolidated. Historical paths resolve
only against DOC_BASE; never apply this patch to the combined live contract.
Step 6 instead derives its internal V2 contract from the proved Step 5 code.

Pipeline (the documented regeneration recipe, now a saved script):
  1. load R + APPEND from rev3_build.py (source truncated before its build tail)
  2. load EXTRA from rev4_extra.py (includes the rev-4f corrective entries)
  3. per file: apply R edits then EXTRA edits SEQUENTIALLY, each asserted to
     match EXACTLY ONCE (a silent no-op is impossible by construction)
  4. difflib unified diff with a/ b/ prefixes; ADDED lines rstripped
  5. STRICT `git apply --check --whitespace=error` on the result

Run: venv/bin/python .claude/plans/Drivers/experiments/harness/rev4_build_patch.py
"""
import difflib, io, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "exp5_rev4_docs.patch")
DOC_BASE = "18f38be90bae6926b69b44fd1ce3a8d6c858d26c"  # last pre-consolidation main

# IMPORT MUST DO NOTHING. This ran `git rev-parse` and then `os.chdir` at module
# level, so merely importing this builder spawned a subprocess and MOVED THE
# CALLER'S WORKING DIRECTORY — the same class as the bare `main()` call fixed in
# `make_g_ledger`, still live in a sibling. Both are now lazy.
_REPO = None


def repo():
    """The repository root, resolved ONCE, on first use — never at import."""
    global _REPO
    if _REPO is None:
        _REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True,
                               cwd=HERE).stdout.strip()
    return _REPO


def load_tables():
    src = io.open(os.path.join(HERE, "rev3_build.py"), encoding="utf-8").read()
    ns = {}
    exec(compile(src[: src.index("\nproblems = []")], "rev3_build.py", "exec"), ns)
    ns2 = {}
    exec(compile(io.open(os.path.join(HERE, "rev4_extra.py"), encoding="utf-8").read(),
                 "rev4_extra.py", "exec"), ns2)
    return ns["R"], ns["APPEND"], ns2["EXTRA"]


# TARGETS WHOSE COMMITTED TEXT CANNOT CARRY THESE EDITS. Declared, never
# silently skipped — and the declaration is FALSIFIABLE: a blocked file that
# would build cleanly fails the build, so this cannot become a place to hide an
# edit that simply stopped matching.
# EMPTIED at SEQ 904, exactly as the removed entry's own instruction said: the
# WorkOrder is committed (DOC-EXP5, 214bc760) and all 17 of its edits are applied,
# so nothing is blocked and its residue + name-level schema checks now RUN instead
# of printing NOT SCANNED. The falsifiable-declaration machinery is unchanged: a
# blocked file that would build cleanly still fails the build.
BLOCKED = {}


def normalize_blank_context(patch):
    """A context line for a BLANK source line is written as a bare newline, not
    as a single space.

    WHY IT MATTERS AND WHY IT IS SAFE. `git diff --cached --check` flags every
    one-space line as trailing whitespace, so committing a diff artifact made the
    check exit non-zero — 51 warnings across the two patches. I claimed stripping
    them would corrupt the patch; that was wrong, and the reviewer was right.
    `git apply` accepts an empty line as context for an empty line (a long-
    standing accommodation for mailers that strip trailing blanks), and it is
    checked both ways: strict `git apply --check --whitespace=error` still passes
    and the APPLIED OUTPUT is byte-identical. Verified, not assumed.
    """
    return "\n".join("" if ln == " " else ln for ln in patch.split("\n"))


def source_text(rel):
    """Historical source bytes, independent of today's paths or dirty index."""
    got = subprocess.run(["git", "show", f"{DOC_BASE}:{rel}"], cwd=repo(),
                         capture_output=True)
    assert got.returncode == 0, f"{rel} is absent at historical base {DOC_BASE}"
    return got.stdout.decode("utf-8")


def spent_edit(old, new, mod):
    """An edit whose replacement ALREADY LANDED, and whose `old` is a substring of
    that replacement — so the builder matches the finished sentence and applies it
    a SECOND time, silently duplicating the amendment. `git apply --check` cannot
    see it: the result is well-formed, just wrong. It happened twice (the WorkOrder
    table, then F14), which is why this is a guard and not a one-off fix.

    Safe by construction: with exactly one `old` match, and `old` inside a `new`
    that is present, that sole match IS the one inside the landed text — an
    independent pending occurrence would make the count 2 and take the existing
    `n != 1` path instead.
    """
    return old in new and new in mod


def build_patch_text():
    """Build the patch and RETURN it. Separated from writing so determinism can
    be proven (build twice, compare) without touching the artifact on disk."""
    R, APPEND, EXTRA = load_tables()
    files = list(dict.fromkeys(list(R) + list(EXTRA)))
    problems, hunks, stale_blocks = [], [], []
    for rel in files:
        src = source_text(rel)
        mod = src
        misses = 0
        for old, new in R.get(rel, []) + EXTRA.get(rel, []):
            n = mod.count(old)
            if n == 1 and spent_edit(old, new, mod):
                misses += 1
                if rel not in BLOCKED:
                    problems.append(f"{rel}: SPENT EDIT (already landed; `old` is "
                                    f"inside its own `new`): {old[:80]!r}")
                continue
            if n != 1:
                misses += 1
                if rel not in BLOCKED:
                    problems.append(f"{rel}: count={n}: {old[:80]!r}")
                continue
            mod = mod.replace(old, new, 1)
        if rel in BLOCKED:
            if not misses:
                stale_blocks.append(rel)      # it builds now — stop excluding it
            continue                          # no hunk: the patch omits it
        if rel in APPEND:
            mod += APPEND[rel]
        hunks.append((rel, src, mod))
    if stale_blocks:
        raise SystemExit(
            "BLOCKED entr(ies) now build cleanly from the index and must be "
            "removed from BLOCKED:\n  " + "\n  ".join(stale_blocks))
    for rel, extra in APPEND.items():
        if rel not in files and rel not in BLOCKED:   # a block covers BOTH paths
            src = source_text(rel)
            hunks.append((rel, src, src + extra))
    if problems:
        raise SystemExit("MISMATCHES (nothing written):\n  " + "\n  ".join(problems))
    out = []
    for rel, src, mod in hunks:
        mod = "\n".join(ln.rstrip() for ln in mod.split("\n"))
        out.append("".join(difflib.unified_diff(
            src.splitlines(keepends=True), mod.splitlines(keepends=True),
            fromfile="a/" + rel, tofile="b/" + rel)))
    return normalize_blank_context("".join(out)), len(hunks)


def main():
    patch, n_files = build_patch_text()
    with io.open(OUT, encoding="utf-8") as fh:
        saved = fh.read()
    if patch != saved:
        raise SystemExit("Historical rebuild differs from the saved patch; nothing overwritten. "
                         "Use its original code/source snapshot to investigate.")
    from rev4_coverage_check import main as check_historical_patch
    check_historical_patch(OUT)


if __name__ == "__main__":
    main()
