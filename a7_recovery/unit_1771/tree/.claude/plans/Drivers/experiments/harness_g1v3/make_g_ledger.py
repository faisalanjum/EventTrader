#!/usr/bin/env python3
"""Regenerate g_status_ledger.md FROM the registry — the counts are never typed.

Two hand-copied mixes had already gone stale against `G_COVERAGE`, which is how
a status claim rots into a false one. This makes the ledger a build product:
`test_the_g_ledger_is_regenerated_not_transcribed` fails if the file on disk
differs from what this script produces.

Run: venv/bin/python harness/make_g_ledger.py [--check]
"""
import io, os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
LEDGER = os.path.join(_HERE, "g_status_ledger.md")

MEANING = {
    "code": "a runnable test proves it today",
    "grading": "only hidden grading can catch it (a MEANING error) — never counted as a code proof",
    "partial": "one leg proven, one leg unbuilt or switch-dependent",
    "gated-switch": "NOT provable until the owner-approved atomic switch",
}


def render():
    from test_g_suite import G_COVERAGE
    order = sorted(G_COVERAGE, key=lambda g: int(g[1:]))
    counts = {}
    for status, _selector, _reason in G_COVERAGE.values():
        counts[status] = counts.get(status, 0) + 1
    out = ["# G1-G35 status ledger — DERIVED from `test_g_suite.py::G_COVERAGE`",
           "",
           "Do not edit by hand: run `make_g_ledger.py` and commit the result.",
           "", "| status | count | meaning |", "|---|---|---|"]
    for status in ("code", "partial", "grading", "gated-switch"):
        out.append(f"| {status} | {counts.get(status, 0)} | {MEANING[status]} |")
    out += [f"| **total** | **{sum(counts.values())}** | |", "",
            "| G | status | proving pytest node id | remaining leg |",
            "|---|---|---|---|"]
    for g in order:
        status, selector, reason = G_COVERAGE[g]
        out.append(f"| {g} | {status} | `{selector}` | {reason or '—'} |")
    return "\n".join(out) + "\n"


def main():
    text = render()
    if "--check" in sys.argv:
        on_disk = io.open(LEDGER, encoding="utf-8").read() if os.path.exists(LEDGER) else ""
        if on_disk != text:
            print("STALE: g_status_ledger.md differs from the registry")
            sys.exit(1)
        print("ledger matches the registry")
        return
    io.open(LEDGER, "w", encoding="utf-8").write(text)
    print(f"wrote {LEDGER}")


if __name__ == "__main__":          # IMPORTING must not write, print, exit or
    main()                          # spawn anything — it ran `main()` at import
