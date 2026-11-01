#!/usr/bin/env python3
"""
Deterministic tests for vault_search.py — run against the LIVE vault on disk.

These assert RELATIVE invariants (helper agrees with independent ripgrep ground truth) rather
than hard-coded counts, so they stay green as the vault grows. They depend ONLY on ripgrep +
the vault files (NOT on the flaky Obsidian app), so they are deterministic.

Run:  python3 scripts/obsidian/test_vault_search.py
Exit: 0 = all pass, 1 = a test failed.
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vault_search as vs  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "vault_search.py")
FLAGGER = os.path.join(HERE, "check_broken_search.sh")
VAULT = vs.DEFAULT_VAULT
RG = shutil.which("rg")

# A word known to be common in the vault, and one that should never exist.
COMMON = "guidance"
ABSENT = "zzqq_definitely_absent_token_4711"

_failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


def ground_truth_files(term):
    """Independent ground truth: files containing `term` (case-insensitive, literal)."""
    p = subprocess.run([RG, "-l", "-i", "-F", "-g", "*.md", "--", term, VAULT],
                       capture_output=True, text=True)
    return set(p.stdout.splitlines()) if p.returncode in (0, 1) else set()


def main():
    print(f"vault: {VAULT}")
    print(f"ripgrep: {RG}\n")
    check("ripgrep present", bool(RG))
    check("vault exists", os.path.isdir(VAULT))

    # 1) helper count == independent ripgrep ground truth (engine consistency)
    gt = ground_truth_files(COMMON)
    res = vs.search(COMMON)
    check("1 engine consistency: helper count == ground-truth file count",
          res["count"] == len(gt), f'{res["count"]} vs {len(gt)}')

    # 2) common word actually returns hits (proves we are NOT silently empty like obsidian search)
    check("2 common word returns hits", res["count"] > 0, f'count={res["count"]}')

    # 3) absent word -> ok, zero hits, empty list (clean no-result, not an error)
    z = vs.search(ABSENT)
    check("3 absent word -> ok & count 0 & no results",
          z["ok"] and z["count"] == 0 and z["results"] == [])

    # 4) results ranked by match count, descending
    counts = [r["matches"] for r in res["results"]]
    check("4 results ranked desc by match count", counts == sorted(counts, reverse=True))

    # 5) returned respects limit and never exceeds count
    lim = vs.search(COMMON, limit=5)
    check("5 limit honored", lim["returned"] <= 5 and lim["returned"] <= lim["count"])

    # 6) every returned note really contains the term, with a snippet
    bad = [r["path"] for r in res["results"][:5] if r["abs_path"] not in gt or not r["snippet"]]
    check("6 returned notes genuinely match & have a snippet", not bad, f"offenders={bad}")

    # 7) frontmatter scope <= full scope, is non-empty, and the hit truly has it in frontmatter
    full_type = vs.search("type")
    fm_type = vs.search("type", frontmatter=True)
    ok_fm = fm_type["count"] > 0 and fm_type["count"] <= full_type["count"]
    if fm_type["results"]:
        top = fm_type["results"][0]["abs_path"]
        fm_lines = [t for _, t in vs._frontmatter_lines(top)]
        ok_fm = ok_fm and any("type" in t.lower() for t in fm_lines)
    check("7 frontmatter scope is a non-empty subset & genuinely in frontmatter", ok_fm,
          f'fm={fm_type["count"]} full={full_type["count"]}')

    # 8) CLI --json emits valid JSON with the documented keys, exits 0
    proc = subprocess.run([sys.executable, SCRIPT, "--json", COMMON],
                          capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout)
        keys_ok = all(k in payload for k in ("ok", "engine", "query", "count", "returned", "results"))
    except Exception:
        payload, keys_ok = None, False
    check("8 CLI --json valid + documented keys + exit 0",
          keys_ok and proc.returncode == 0, f"rc={proc.returncode}")

    # 9) CLI exits 0 even on zero results (no false 'error' for a clean miss)
    miss = subprocess.run([sys.executable, SCRIPT, "--json", ABSENT],
                          capture_output=True, text=True)
    check("9 CLI exit 0 on zero results", miss.returncode == 0, f"rc={miss.returncode}")

    # 10) the tripwire runs and reports clean on the current repo
    flag = subprocess.run(["bash", FLAGGER], capture_output=True, text=True)
    check("10 broken-search tripwire passes (no offending callers)",
          flag.returncode == 0, flag.stdout.strip() + flag.stderr.strip())

    print()
    if _failures:
        print(f"RESULT: {len(_failures)} FAILED -> {_failures}")
        sys.exit(1)
    print("RESULT: ALL TESTS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
