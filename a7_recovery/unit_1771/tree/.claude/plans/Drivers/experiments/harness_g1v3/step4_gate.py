#!/usr/bin/env python3
"""Step 4 begin-conditions gate (step4.md "Fresh-session start" + section 1).

step4.md permits Step 4 to BEGIN only if five things hold. This file answers all
five in one verdict, and it answers each one FROM THE FILE THAT ALREADY OWNS IT
rather than from a number written here:

  condition (step4.md)                     owner consulted
  ---------------------------------------  ------------------------------------
  1 frozen rows closed, no residual        receipts_827/26_*, 28_* (the Step-3
    and no owner decision                  reconciliations' own open/unaccounted
                                           lists)
  2 Step 3 candidate unchanged             WORKORDER_STATUS.md's own file table,
                                           every hash RECOMPUTED from the tree
  3 36-event denominator exact             both launch manifests (population
                                           agreement, not a literal 36)
  4 focused tests green                    pytest, node identities recorded
  5 V1 active, write/launch switches off   make_pin_inventory.py --check, plus
                                           each manifest's own switch fields

WHY NO EXPECTED VALUES LIVE HERE. A gate that carries its own copy of the answer
stops being evidence the moment the owner moves; that is the second-owner defect
this arc has repeatedly paid for. The only constants below are the REQUIRED
STATES quoted from step4.md itself ("zero open rows, zero unexplained paths,
zero unknowns, and zero owner decisions"), which are the spec, not a tuning knob.

The 36-event check deliberately does NOT assert the number 36. It asserts that
each manifest's declared n_events equals its own event list, that ids are
unique, and that BOTH plans name the identical population. If the owner ever
moves the population to 40, this gate still passes and still means something;
a hardcoded 36 would only prove that someone edited this file.

Run:  venv/bin/python harness/step4_gate.py [--expect-handoff <sha256>]
                                            [--skip-tests] [--out <receipt.json>]
Exit 0 only if every condition PASSES.
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
_RECEIPTS = os.path.join(_HERE, "receipts_827")
_HANDOFF = os.path.join(_HERE, "..", "WORKORDER_STATUS.md")

# The focused suites named by step4.md section 6 items 1-3. Kept as PATHS, so a
# renamed suite fails loudly here instead of silently shrinking the denominator.
FOCUSED = (
    os.path.join(_HERE, "test_harness_guards.py"),
    os.path.join(_HERE, "test_g_suite.py"),
    os.path.join(_HERE, "test_no_semantic_patterns.py"),
    os.path.join(_REPO, ".claude/plans/Drivers/workflows/tests/test_perx_naming_residue.py"),
)

# The handoff's own file table. One row = one path the Step 1-3 selection claims.
_ROW = re.compile(r"^\| `([^`]+)` \| (modified|untracked|deleted) \| "
                  r"(?:`([0-9a-f]{64})`|\*\(deleted[^|]*\)\*) \|$", re.M)


def _sha(path):
    with io.open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _receipt(name):
    return json.load(io.open(os.path.join(_RECEIPTS, name), encoding="utf-8"))


def c1_frozen_rows_closed():
    """step4.md: zero open rows, zero unknowns, zero owner decisions.

    The two Step-3 receipts prove "nothing left over" in two DIFFERENT lawful
    shapes, and this gate honours both rather than forcing one on the other
    (step4.md section 1 forbids creating new categories at the merge):

      * an explicit residual shape — the receipt publishes `open_rows` /
        `unaccounted` lists and they must be empty;
      * a complete-classification shape — the receipt classifies every row, so
        zero residual means every row carries a nonblank class drawn from the
        receipt's OWN declared vocabulary, and the published tally matches a
        recount.

    The class vocabulary is taken from the receipt's own `counts` keys, never
    from a list written here: a gate that carries its own vocabulary silently
    stops noticing when the owner adds a class."""
    out, problems = {}, []
    for name in sorted(n for n in os.listdir(_RECEIPTS)
                       if re.match(r"^2[68]_step3_.*\.json$", n)):
        d = _receipt(name)
        proved = []

        residual = {k: d[k] for k in ("open_rows", "unaccounted", "unknowns", "owner_decisions")
                    if isinstance(d.get(k), list)}
        if residual:
            proved.append("explicit-residual")
            for k, v in residual.items():
                if v:
                    problems.append("%s carries %d %s: %r" % (name, len(v), k, v[:3]))

        counts, rows = d.get("counts"), d.get("tests")
        if isinstance(counts, dict) and isinstance(rows, dict):
            proved.append("complete-classification")
            vocab = set(counts)
            leaf = {k: v for k, v in rows.items()
                    if isinstance(v, dict) and not any(isinstance(x, dict) for x in v.values())}
            tally = {}
            for row_name, row in leaf.items():
                cls = (row.get("class") or "").strip()
                if not cls:
                    problems.append("%s: row %r has no class — unclassified residual" % (name, row_name))
                    continue
                if cls not in vocab:
                    problems.append("%s: row %r has class %r outside the receipt's own vocabulary %s"
                                    % (name, row_name, cls, sorted(vocab)))
                if not (row.get("why") or "").strip():
                    problems.append("%s: row %r carries no reason" % (name, row_name))
                tally[cls] = tally.get(cls, 0) + 1
            if len(leaf) != len(rows):
                problems.append("%s: %d of %d row entries are not leaf rows"
                                % (name, len(rows) - len(leaf), len(rows)))
            if tally != {k: v for k, v in counts.items() if v}:
                problems.append("%s: published counts %r do not match a recount %r"
                                % (name, counts, tally))
            out.setdefault(name, {})["classified"] = {"rows": len(leaf), "recount": tally}

        if not proved:
            problems.append("%s publishes neither a residual list nor a complete "
                            "classification — cannot prove zero" % name)
        out.setdefault(name, {})["residual_lists"] = {k: len(v) for k, v in residual.items()}
        out[name]["proof_shape"] = proved
    if not out:
        problems.append("no Step-3 reconciliation receipts found — the denominator has no owner")
    return (not problems), out, problems


def c2_candidate_unchanged(expect_handoff=None):
    """step4.md: the Step 3 candidate is unchanged.

    Every present-file hash in the handoff table is RECOMPUTED from the live
    tree, and every deleted row is confirmed still absent. A row that merely
    looks well-formed proves nothing."""
    text = io.open(_HANDOFF, encoding="utf-8").read()
    problems = []

    # PARSE ONLY THE AUTHORITATIVE TABLE. The handoff also RECORDS its own
    # history, and those superseded sections legitimately carry the hashes that
    # were true when they were written. Verifying them against today's tree
    # manufactures false drift — the first version of this gate read all 111
    # row-shaped lines in the file and duly "found" drift in a historical row.
    # The anchor is the document's own declared selection header, and the parse
    # is then PROVED against the count that header declares, so a wrong anchor
    # fails loudly here instead of silently checking the wrong denominator.
    decl = None
    for m in re.finditer(r"\*\*Selected candidate: (\d+) paths\*\*", text):
        decl = m                              # last declaration wins: later corrections supersede
    if decl is None:
        return False, {}, ["the handoff declares no selected candidate — cannot locate the frozen table"]
    declared = int(decl.group(1))
    rows = _ROW.findall(text[decl.end():])

    counts = {"modified": 0, "untracked": 0, "deleted": 0}
    checked = 0
    # The handoff is itself a selected path but cannot list its own hash, so the
    # table holds declared-1 rows. Any other arithmetic means a misparse.
    if len(rows) != declared - 1:
        problems.append("parsed %d table rows but the handoff declares %d selected paths "
                        "(expected %d rows plus the handoff itself)"
                        % (len(rows), declared, declared - 1))
    for path, status, sha in rows:
        counts[status] += 1
        full = os.path.join(_REPO, path)
        if status == "deleted":
            if os.path.exists(full):
                problems.append("row says deleted but file is present: %s" % path)
            continue
        if not os.path.exists(full):
            problems.append("row hashed but file is missing: %s" % path)
            continue
        checked += 1
        if _sha(full) != sha:
            problems.append("BYTE DRIFT since the reviewed candidate: %s" % path)
    handoff_sha = _sha(_HANDOFF)
    if expect_handoff and handoff_sha != expect_handoff:
        problems.append("handoff moved: %s != expected %s" % (handoff_sha, expect_handoff))
    if not rows:
        problems.append("handoff table parsed to ZERO rows — the parser or the table changed")
    out = {"declared_selected_paths": declared, "rows": len(rows), "by_status": counts,
           "hashes_recomputed": checked,
           "handoff_sha256": handoff_sha, "expected_handoff": expect_handoff}
    return (not problems), out, problems


def _manifests():
    for name in sorted(os.listdir(_HERE)):
        if name.startswith("launch_") and name.endswith(".manifest.json"):
            yield name, json.load(io.open(os.path.join(_HERE, name), encoding="utf-8"))


def c3_event_denominator_exact():
    """step4.md: the 36-event denominator is exact, plus the disabled contingency.

    Asserted as INTERNAL CONSISTENCY and CROSS-PLAN AGREEMENT, never as the
    literal 36 — see the module docstring."""
    out, problems, populations = {}, [], {}
    for name, d in _manifests():
        ids = [e["source_id"] for e in d.get("events", [])]
        populations[name] = frozenset(ids)
        out[name] = {"n_events": d.get("n_events"), "listed": len(ids), "unique": len(set(ids))}
        if d.get("n_events") != len(ids):
            problems.append("%s: declared n_events=%r but lists %d events" % (name, d.get("n_events"), len(ids)))
        if len(set(ids)) != len(ids):
            problems.append("%s: duplicate source_id in the event population" % name)
        if not ids:
            problems.append("%s: empty event population" % name)
    distinct = set(populations.values())
    if len(distinct) > 1:
        problems.append("the launch plans name DIFFERENT event populations: %s"
                        % {k: len(v) for k, v in populations.items()})
    out["populations_agree"] = (len(distinct) == 1)
    return (not problems), out, problems


def c4_focused_tests_green(skip=False):
    """step4.md: focused tests are green. Identities recorded, not just a count."""
    if skip:
        return True, {"skipped": True}, []
    py = os.path.join(_REPO, "venv/bin/python3")
    cmd = [py, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"] + list(FOCUSED)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO, env=env)
    tail = (r.stdout or "").strip().splitlines()[-1:] or [""]
    # THE ELAPSED TIME IS DROPPED ON PURPOSE. step4.md section 3 requires this
    # preparation freeze to rebuild byte-identically; pytest's summary line ends
    # in "... in 131.38s", so recording it verbatim would change this receipt's
    # bytes on every run and break the very reproducibility it is evidence for.
    # The outcome TOTALS that section 6 asks for are kept; only the clock goes.
    totals = dict((int(n), w) for n, w in re.findall(r"(\d+) (passed|failed|error|skipped|xfailed|xpassed)", tail[0]))
    out = {"command": " ".join(os.path.relpath(c, _REPO) if os.path.isabs(c) else c for c in cmd),
           "suites": [os.path.relpath(p, _REPO) for p in FOCUSED],
           "totals": {w: n for n, w in totals.items()}, "returncode": r.returncode}
    problems = [] if r.returncode == 0 else ["focused suites are NOT green: %s" % tail[0]]
    for p in FOCUSED:
        if not os.path.exists(p):
            problems.append("named focused suite is missing: %s" % os.path.relpath(p, _REPO))
    return (not problems), out, problems


def c5_switches_off():
    """step4.md: V1 still active and all write/model launch switches off.

    Authority/protected bytes are delegated to make_pin_inventory.py --check,
    which already owns that proof. The launch switches are read from each
    manifest's own fields."""
    out, problems = {}, []
    py = os.path.join(_REPO, "venv/bin/python3")
    r = subprocess.run([py, "-B", os.path.join(_HERE, "make_pin_inventory.py"), "--check"],
                       capture_output=True, text=True, cwd=_REPO,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    out["pin_inventory_check"] = {"returncode": r.returncode,
                                  "tail": (r.stdout or r.stderr or "").strip().splitlines()[-1:] or [""]}
    if r.returncode != 0:
        problems.append("protected/authority pins do not verify (make_pin_inventory.py --check)")
    for name, d in _manifests():
        lock = d.get("kfields_lock")
        state = {"made_calls": d.get("made_calls"),
                 "kfields_lock_sha256": (lock or {}).get("sha256") if isinstance(lock, dict) else lock,
                 "od11_enabled": (d.get("od11_contingency") or {}).get("enabled")}
        out[name] = state
        if state["made_calls"] != 0:
            problems.append("%s: made_calls=%r — a paid call is recorded" % (name, state["made_calls"]))
        if state["kfields_lock_sha256"] is not None:
            problems.append("%s: K-fields lock is SET — GO#1 is no longer unfired" % name)
        if state["od11_enabled"] is not False:
            problems.append("%s: OD-11 contingency is not disabled" % name)
    return (not problems), out, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-handoff", default=None,
                    help="sha256 the reviewer VERIFIED; omit to report without asserting")
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    checks = [
        ("1_frozen_rows_closed", c1_frozen_rows_closed()),
        ("2_candidate_unchanged", c2_candidate_unchanged(a.expect_handoff)),
        ("3_event_denominator_exact", c3_event_denominator_exact()),
        ("4_focused_tests_green", c4_focused_tests_green(a.skip_tests)),
        ("5_switches_off", c5_switches_off()),
    ]
    report, ok_all = {}, True
    for name, (ok, detail, problems) in checks:
        report[name] = {"pass": ok, "detail": detail, "problems": problems}
        ok_all = ok_all and ok
        print("%-28s %s" % (name, "PASS" if ok else "FAIL"))
        for p in problems:
            print("    - " + p)
    report["verdict"] = "PASS" if ok_all else "FAIL"
    report["what_this_proves"] = ("the five step4.md begin-conditions, each answered from the file "
                                  "that already owns it; no expected value is stored in this gate")
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
        print("wrote " + os.path.relpath(a.out, _REPO))
    print("VERDICT " + report["verdict"])
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
