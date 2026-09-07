# -*- coding: utf-8 -*-
"""The PROPOSED combined publication path set (Codex SEQ 1795).

This checkpoint must carry three units together: unit_1786's immutable capture,
unit_1791's diagnosis, and unit_1792. It proposes paths only - nothing is
staged, committed or edited, and no published unit is touched.

unit_1791's own whitelist has nine rows and omits its WHITELIST.tsv and
MANIFEST.sha256; both are added HERE, in the proposed set, rather than by
editing that preserved unit. Every unit is cross-checked against what is
actually on disk so an omission is named rather than inherited.
"""
import collections
import io
import json
import os
import subprocess
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
A = R + "/a7_recovery"
UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = ["unit_1786", "unit_1791", "unit_1792"]
#: this unit's workflow-state view is rebuilt by its recipe, never republished
NOT_REPUBLISHED = {"unit_1792": "view/workflows"}


def on_disk(unit):
    root = os.path.join(A, unit)
    skip = NOT_REPUBLISHED.get(unit)
    out = set()
    for base, dirs, files in os.walk(root):
        rel = os.path.relpath(base, root)
        if skip and (rel == skip or rel.startswith(skip + os.sep)):
            dirs[:] = []
            continue
        for name in files:
            out.add(os.path.relpath(os.path.join(base, name), root))
    return out


def whitelisted(unit):
    path = os.path.join(A, unit, "WHITELIST.tsv")
    if not os.path.isfile(path):
        return None
    return {l for l in io.open(path, encoding="utf-8").read().splitlines() if l.strip()}


def main():
    tracked = {t for t in subprocess.run(["git", "-C", R, "ls-files"],
                                         capture_output=True, text=True).stdout.split("\n") if t}
    rows, report = [], []
    for unit in UNITS:
        disk, wl = on_disk(unit), whitelisted(unit)
        added = sorted(disk - wl) if wl is not None else sorted(disk)
        for rel in sorted(disk):
            rows.append("a7_recovery/%s/%s" % (unit, rel))
        report.append(collections.OrderedDict([
            ("unit", unit),
            ("manifest_sha256", None if not os.path.isfile(os.path.join(A, unit, "MANIFEST.sha256"))
             else __import__("hashlib").sha256(
                 io.open(os.path.join(A, unit, "MANIFEST.sha256"), "rb").read()).hexdigest()),
            ("files_on_disk", len(disk)),
            ("its_own_whitelist_rows", None if wl is None else len(wl)),
            ("omitted_by_its_whitelist_and_added_here", added),
            ("not_republished", NOT_REPUBLISHED.get(unit))]))
    already = sorted(p for p in rows if p in tracked)
    doc = collections.OrderedDict([
        ("what", "the exact repo-relative paths this checkpoint proposes to publish, "
                 "across the three units that must land together"),
        ("staged", False), ("committed", False),
        ("units", report),
        ("total_paths", len(rows)),
        ("already_git_tracked", already),
        ("view_supplied_by_recipe", "a7_recovery/unit_1792/compose_views_1792.sh rebuilds "
                                    "unit_1792/view/workflows from unit_1781's published view "
                                    "plus unit_1786's captured state, which this same "
                                    "checkpoint publishes")])
    out = UNIT + "/evidence/PROPOSED_PUBLICATION_1795"
    io.open(out + ".tsv", "w", encoding="utf-8").write("".join(p + "\n" for p in rows))
    io.open(out + ".json", "w", encoding="utf-8").write(json.dumps(doc, indent=1) + "\n")
    for r in report:
        print("  %-10s on disk %5d   its whitelist %s   added here %s"
              % (r["unit"], r["files_on_disk"], r["its_own_whitelist_rows"],
                 r["omitted_by_its_whitelist_and_added_here"] or "none"))
    print("  proposed paths : %d   already git-tracked: %d" % (len(rows), len(already)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
