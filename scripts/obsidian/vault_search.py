#!/usr/bin/env python3
"""
vault_search.py — the ONE reliable full-content search over the Obsidian vault.

WHY THIS EXISTS
  Obsidian's built-in search is BROKEN on this host (v1.12.4, headless). Verified 2026-06-17:
  the word "guidance" exists in 2,931 vault notes, yet every built-in path returned NOTHING:
    - `obsidian search query=...`   -> empty
    - `obsidian search:context`     -> empty
    - `obsidian search total`       -> empty
    - `obsidian eval` + cachedRead  -> empty   (the old "known-good" workaround no longer works)
  An agent that trusts any of those silently concludes "the info isn't there" — a silent,
  exit-code-0 failure. This helper avoids the whole flaky stack.

WHAT THIS DOES
  Searches the actual .md files on disk with ripgrep (ground truth). No Obsidian index,
  no running Obsidian app required, instant (~15 ms for the full vault). Every agent that
  needs to FIND notes should call this instead of any `obsidian search`.

USAGE
  python3 scripts/obsidian/vault_search.py [options] QUERY
    --vault PATH       vault root (default: $OBSIDIAN_VAULT or the earnings-analysis vault)
    --regex            treat QUERY as a regex (default: fixed/literal string)
    --case-sensitive   case-sensitive match (default: insensitive)
    --frontmatter      only match inside each note's YAML frontmatter (--- ... ---)
    --content          also print the matching lines (default: path + count + 1 snippet)
    --limit N          max notes in the result list (default 20); `count` is the TRUE total
    --json             machine-readable JSON (agents: parse this; trust `count`, not exit code)

EXIT CODES
  0  ran OK (with OR without hits)      2  error (ripgrep missing / vault missing / bad usage)
  Note: a clean "0 results" also exits 0 — distinguish hits via the printed `count`/JSON `count`,
  never via the exit code (this host's tooling returns 0 even on failure).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

DEFAULT_VAULT = os.environ.get(
    "OBSIDIAN_VAULT",
    "/home/faisal/Obsidian/EventTrader/Earnings/earnings-analysis",
)
SNIPPET_MAX = 200


def _die(msg: str) -> "None":
    print(f"vault_search: error: {msg}", file=sys.stderr)
    sys.exit(2)


def _rg() -> str:
    rg = shutil.which("rg")
    if not rg:
        _die("ripgrep (rg) not found on PATH — install ripgrep (apt install ripgrep).")
    return rg


def _snippet(text: str) -> str:
    s = " ".join(text.split())
    return s[:SNIPPET_MAX] + ("…" if len(s) > SNIPPET_MAX else "")


def _base_flags(case_sensitive: bool, regex: bool) -> "list":
    flags = ["--color=never", "-g", "*.md"]
    if not case_sensitive:
        flags.append("-i")
    if not regex:
        flags.append("-F")
    return flags


def _frontmatter_lines(path: str) -> "list":
    """Inner YAML frontmatter lines as (1-based line_no, text); [] if the note has none."""
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            if f.readline().strip() != "---":
                return []
            line_no = 1
            for line in f:
                line_no += 1
                if line.strip() == "---":
                    return out
                out.append((line_no, line.rstrip("\n")))
    except OSError:
        return []
    return []  # no closing delimiter -> treat as no frontmatter


def _line_matches(text: str, query: str, regex: bool, case_sensitive: bool) -> bool:
    if regex:
        return re.search(query, text, 0 if case_sensitive else re.IGNORECASE) is not None
    if case_sensitive:
        return query in text
    return query.lower() in text.lower()


def search(query, vault=DEFAULT_VAULT, regex=False, case_sensitive=False,
           frontmatter=False, limit=20, want_content=False):
    """Return {ok, engine, query, vault, frontmatter, count, returned, results[]}."""
    rg = _rg()
    if not os.path.isdir(vault):
        _die(f"vault not found: {vault}")
    flags = _base_flags(case_sensitive, regex)

    # 1) total occurrences per file (single fast call = ground truth on disk)
    cm = subprocess.run([rg, "--count-matches", *flags, "--", query, vault],
                        capture_output=True, text=True)
    if cm.returncode not in (0, 1):  # 0=hits, 1=no hits, 2=error
        _die(f"ripgrep failed: {cm.stderr.strip() or cm.returncode}")
    file_counts = {}
    for line in cm.stdout.splitlines():
        path, sep, count = line.rpartition(":")
        if sep and path:
            try:
                file_counts[path] = int(count)
            except ValueError:
                pass

    # 2) optional frontmatter scope (filter to matches inside the YAML block)
    fm_hits = {}
    if frontmatter:
        kept = {}
        for path in file_counts:
            hits = [(ln, t) for ln, t in _frontmatter_lines(path)
                    if _line_matches(t, query, regex, case_sensitive)]
            if hits:
                kept[path] = len(hits)
                fm_hits[path] = hits
        file_counts = kept

    count = len(file_counts)
    ranked = sorted(file_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:max(0, limit)]
    results = [{"path": os.path.relpath(p, vault), "abs_path": p,
                "matches": m, "snippet": "", "lines": []} for p, m in ranked]

    # 3) snippets / content for the ranked files only (bounded)
    k = 10 if want_content else 1
    by_path = {r["abs_path"]: r for r in results}
    if results and frontmatter:
        for path, r in by_path.items():
            hits = fm_hits.get(path, [])[:k]
            if hits:
                r["snippet"] = _snippet(hits[0][1])
                if want_content:
                    r["lines"] = [{"line": ln, "text": _snippet(t)} for ln, t in hits]
    elif results:
        proc = subprocess.run([rg, "-n", "--no-heading", "-m", str(k), *flags, "--",
                               query, *by_path.keys()], capture_output=True, text=True)
        for line in proc.stdout.splitlines():
            path, sep, rest = line.partition(":")
            lineno, sep2, text = rest.partition(":")
            r = by_path.get(path)
            if not r or not sep2:
                continue
            try:
                ln = int(lineno)
            except ValueError:
                continue
            snip = _snippet(text)
            if not r["snippet"]:
                r["snippet"] = snip
            if want_content and len(r["lines"]) < k:
                r["lines"].append({"line": ln, "text": snip})

    return {"ok": True, "engine": "ripgrep", "query": query, "vault": vault,
            "frontmatter": frontmatter, "count": count, "returned": len(results),
            "results": results}


def _print_human(res, want_content):
    scope = " (frontmatter only)" if res["frontmatter"] else ""
    print(f'{res["count"]} note(s) match "{res["query"]}"{scope}   [engine: ripgrep]')
    if res["count"] > res["returned"]:
        print(f"showing top {res['returned']} by match count:")
    for e in res["results"]:
        print(f'  {e["matches"]:>5}x  {e["path"]}')
        if e["snippet"]:
            print(f'         {e["snippet"]}')
        if want_content:
            for L in e["lines"]:
                print(f'         L{L["line"]}: {L["text"]}')


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="vault_search.py",
        description="Reliable Obsidian-vault search (ripgrep) — replaces the broken `obsidian search`.")
    ap.add_argument("query", nargs="+", help="search text (joined with spaces)")
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--regex", action="store_true")
    ap.add_argument("--case-sensitive", action="store_true")
    ap.add_argument("--frontmatter", action="store_true")
    ap.add_argument("--content", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    res = search(" ".join(args.query), vault=args.vault, regex=args.regex,
                 case_sensitive=args.case_sensitive, frontmatter=args.frontmatter,
                 limit=args.limit, want_content=args.content)
    if args.json:
        print(json.dumps(res))
    else:
        _print_human(res, args.content)
    sys.exit(0)


if __name__ == "__main__":
    main()
