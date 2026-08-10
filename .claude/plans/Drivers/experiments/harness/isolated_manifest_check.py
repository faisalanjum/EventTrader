#!/usr/bin/env python3
"""Prove the COMMIT is self-sufficient: build the exact tree `git commit` would
write, run the clean lane inside it under a SANITIZED environment, and require
the pinned result.

WHY. Every green count was once measured in the WORKING TREE, which holds
hundreds of unrelated changes and machine-local data. That says nothing about
whether the committed set stands on its own: a test file left out is simply not
collected, so the run goes green while proving less.

TWO LEAKS HAVE BEEN CLOSED HERE, AND THE SECOND IS THE REASON FOR THIS VERSION.

  THE FILESYSTEM LEAK. An earlier version archived HEAD, copied in 50 untracked
  harness files and 39 untracked exam inputs as "external", then ran
  `git add -A`. Uncommitted files became "committed" inside the temporary
  repository, so the gate proved "committed == tested" about a tree that will
  never exist. The tree is now `git write-tree` — the exact tree object
  `git commit` records — and the temporary repository's own `write-tree` must
  EQUAL it, so a returning overlay breaks the identity instead of hiding in it.

  THE ENVIRONMENT LEAK. The fix above isolated the FILES and left the PROCESS
  privileged: the run inherited `**os.environ`, including this machine's
  `NEO4J_URI/USERNAME/PASSWORD` and `OPENAI_API_KEY`. Tests that reach the graph
  through `os.environ` therefore CONNECTED TO THE LIVE DATABASE inside a tree
  being called clean — 42 test nodes, of which only 7 were visible because those
  7 happened to read a `.env` FILE instead. "Every non-live test passed" was
  measured with the database reachable, which is not the claim. The environment
  is now built from an ALLOWLIST (below), so any credential is absent by
  default rather than by enumeration.

THE TWO LANES ARE NOW EXPLICIT, and this file owns only the first:

  CLEAN LANE (here)   no credentials, no `.env`, no user HOME. Runs
                      `-m "not live and not live_write"`. EVERY test must PASS:
                      no failures, no errors, no skips. The allow_skip /
                      allow_fail pin family is DELETED (2026-07-30): once the
                      write probe became marker-deselected, zero pins used it,
                      and machinery waiting for a use is a door waiting to be
                      opened.
  LIVE LANES (not here)  `-m live` is the READ-ONLY graph lane, run against a
                      real Neo4j in the working tree. `-m live_write` is the
                      owner-gated write/delete probe and is never run.

WHAT IT PROVES, each able to fail on its own:

  1. THE TREE IS THE COMMIT   temp `write-tree` == source `write-tree`.
  2. NOTHING FORBIDDEN        no secret, cache, or bytecode path is added.
  3. THE RUN REALLY RAN       pytest's exit code must mean "the suite executed".
  4. EXACT IDENTITIES         clean-lane identities + the pinned live inventory
                              == the pinned full set, so a test cannot vanish by
                              being dropped from the commit OR by being quietly
                              marked live.
  5. NO DUPLICATES ANYWHERE   duplicate pins, duplicate pinned identities and
                              duplicate JUnit identities are all rejected. Each
                              used to collapse silently into a dict or a set.
  6. EVERY TEST PASSES        zero failures, zero errors, zero skips — no
                              exception machinery exists to pin one.
  7. THE TESTS CHANGED NOTHING  after pytest, the temporary repository must
                              show no tracked modification and no new untracked
                              file. A test that rewrites or drops a file would
                              otherwise invalidate proof 1 after it had already
                              been checked.

Outcomes come from a JUnit report, not from parsing human-readable output.

Run:            venv/bin/python harness/isolated_manifest_check.py
Re-pin ids:     ... isolated_manifest_check.py --write-expected     (LIVE tree)
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))

EXPECTED = os.path.join(_HERE, "expected_test_nodes.txt")
PINS = os.path.join(_HERE, "gate_pins.jsonl")

TEST_ROOTS = ("driver/core", "driver/relocation",
              ".claude/plans/Drivers/experiments/harness")
CLEAN_LANE = "not live and not live_write"

# pytest's own exit codes. 0 = all passed, 1 = tests failed. Everything else
# means the suite did NOT execute as asked: 2 interrupted, 3 internal error,
# 4 usage error, 5 nothing collected. Those were previously accepted in silence.
PYTEST_RAN = (0, 1)

# THE ENVIRONMENT ALLOWLIST. An allowlist, not a blocklist of `NEO4J_*`: a
# blocklist leaks the next credential somebody adds, which is the same
# instance-versus-class mistake the `.env` path guard made. Nothing here can
# authenticate to anything.
SAFE_ENV = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TZ")

FORBIDDEN_PARTS = ("__pycache__", ".pytest_cache", ".credentials.json",
                   "anthropic_drivers_key", "writer.lock")
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".so", ".key", ".pem")
# SEGMENT PREFIXES. `.env` alone was an INSTANCE guard: it blocked `.env` and
# `config/.env` while `.env.local`, `.env.production` and `.env.bak` passed, and
# every one of those carries the same secrets.
FORBIDDEN_PREFIXES = (".env",)

# A CLOSED, ALL-LIVE vocabulary. allow_skip / allow_fail were DELETED
# 2026-07-30: zero pins used either once the write probe carried its marker,
# and the clean lane's law is 100% PASS — an exception kind with no lawful
# holder only waits to excuse the next regression.
PIN_KINDS = ("live_read", "live_write")


def forbidden(paths):
    bad = []
    for p in paths:
        segs = p.split("/")
        if any(part in segs for part in FORBIDDEN_PARTS) \
                or p.endswith(FORBIDDEN_SUFFIXES) \
                or any(s.startswith(FORBIDDEN_PREFIXES) for s in segs):
            bad.append(p)
    return bad


def sanitized_env(root, home):
    """A process environment built from nothing but the allowlist. Nothing here
    can authenticate to anything; the lanes that need credentials build their
    own environment and pass it in."""
    env = {k: os.environ[k] for k in SAFE_ENV if k in os.environ}
    env["HOME"] = home            # never the user's: no ~/.env, no key files
    env["PYTHONPATH"] = root
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # PC-2 (#827): the allowlist concept is right, the OMISSION was the defect.
    # In a read-only jail the child pytest died at capture init before it could
    # write a report — strace showed tempfile's whole fallback chain refused
    # (/tmp EROFS, /var/tmp EROFS, /usr/tmp ENOENT, cwd EROFS). TMPDIR is the
    # exact name the runtime consults FIRST (CPython
    # tempfile._candidate_tempdir_list), and `home` is the writable scratch this
    # function is already handed, so the child gets a place to write without any
    # new name entering the allowlist.
    env["TMPDIR"] = home
    return env


def git(args, cwd, stdin=None, check=True):
    """EVERY git call is checked. An earlier version ran init/add/commit in a
    loop and looked at none of their exit codes, so a repository that failed to
    initialise still produced a "proof"."""
    p = subprocess.run(["git", *args], cwd=cwd, input=stdin,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check:
        assert p.returncode == 0, (
            f"git {' '.join(args)} failed in {cwd} ({p.returncode}): "
            f"{p.stderr.decode('utf-8', 'replace')[:400]}")
    return p


def staged_paths():
    out = git(["diff", "--cached", "--name-only"], _REPO).stdout.decode().split()
    assert out, "the index is empty — there is no commit to check"
    return sorted(out)


def index_tree():
    """The exact tree object `git commit` would record from the current index."""
    return git(["write-tree"], _REPO).stdout.decode().strip()


# ---------------------------------------------------------------------------
# PINS — one delimiter-safe format for every kind of exception.
# ---------------------------------------------------------------------------

def load_pins(text):
    """JSON Lines -> {node: entry}. JSONL because a test id is not a safe string:
    the real suite contains ids holding `#` (`…[0001306830-24-000155#0]`) and `/`
    (`…[x/y]`). The previous format used ` # ` as its comment delimiter and
    `partition("#")` truncated exactly those ids, silently pinning the wrong
    node. There is no delimiter to escape here.

    Duplicates are REJECTED. Two lines naming one node used to overwrite each
    other in a dict, so a reviewed pin could be replaced by an unreviewed one
    with no diff-visible sign.
    """
    out = {}
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise AssertionError(f"gate_pins.jsonl:{n}: not valid JSON: {exc}")
        for field in ("node", "kind", "why"):
            assert row.get(field), f"gate_pins.jsonl:{n}: missing {field!r}"
        assert row["kind"] in PIN_KINDS, \
            f"gate_pins.jsonl:{n}: unknown kind {row['kind']!r}"
        assert row["node"] not in out, \
            f"gate_pins.jsonl:{n}: duplicate pin for {row['node']}"
        out[row["node"]] = row
    return out


def load_expected(text):
    """The pinned identity list. Duplicates REJECTED: this was read into a set,
    so a doubled line collapsed and the count silently disagreed with the file."""
    out, seen = [], set()
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        assert line not in seen, \
            f"expected_test_nodes.txt:{n}: duplicate identity {line}"
        seen.add(line)
        out.append(line)
    assert out, "the pinned identity file is empty"
    return set(out)


def parse_junit(xml_text):
    """{nodeid: (outcome, message)}. Duplicate identities REJECTED — a dict
    assignment used to keep only the last, hiding one of two colliding tests.

    `classname`, never `file`: pytest leaves `file` empty here, so identities
    came out as "None::test_x" — not durable, and two same-named tests in
    different modules collided.

    The MESSAGE is kept, not only the label. Recording "failed" alone made a
    missing database and a real production assertion indistinguishable, which is
    exactly how a regression hides inside an accepted exception.
    """
    out = {}
    for c in ET.fromstring(xml_text).iter("testcase"):
        node = f"{c.get('classname') or '?'}::{c.get('name')}"
        outcome, text = "passed", ""
        for kind, label in (("error", "error"), ("failure", "failed"),
                            ("skipped", "skipped")):
            el = c.find(kind)
            if el is not None:
                outcome = label
                text = f"{el.get('type') or ''} {el.get('message') or ''} " \
                       f"{el.text or ''}"
                break
        assert node not in out, f"duplicate JUnit identity: {node}"
        out[node] = (outcome, text)
    assert out, "zero test cases — an empty collection is never a clean result"
    return out


# ---------------------------------------------------------------------------

def build_isolated_tree(tree, base):
    """Extract `tree` into `base/tree` and make it a real repository whose own
    tree hash equals `tree`.

    A REAL REPOSITORY because several tests shell out to git (`apply --check`,
    `status --porcelain`); against a bare directory they fail for a reason that
    has nothing to do with the commit.

    NOT `git add -A`: the paths come from the tree listing itself, and `--force`
    is required because tracked-but-ignored files exist (cache filings are
    tracked despite the ignore rule). The hash equality below is what makes this
    airtight — it cannot pass if anything was added, dropped or altered.
    """
    tmp = os.path.join(base, "tree")
    os.makedirs(tmp)
    tar = git(["archive", tree], _REPO)
    assert subprocess.run(["tar", "-x", "-C", tmp],
                          input=tar.stdout).returncode == 0, "tar extract failed"
    names = git(["ls-tree", "-r", "--name-only", "-z", tree], _REPO).stdout
    git(["init", "-q"], tmp)
    git(["-c", "user.name=isolated", "-c", "user.email=i@x", "add", "--force",
         "--pathspec-from-file=-", "--pathspec-file-nul"], tmp, stdin=names)
    got = git(["write-tree"], tmp).stdout.decode().strip()
    assert got == tree, (
        f"the isolated tree is NOT the commit: {got} != {tree}. Something was "
        f"added, dropped or changed on the way in.")
    git(["-c", "user.name=isolated", "-c", "user.email=i@x", "commit", "-q",
         "-m", "the candidate commit"], tmp)
    return tmp


def run_lane(root, home, marker=None, env=None):
    """{nodeid: (outcome, message)} for one lane. `marker` None = no filtering.

    `no:cacheprovider` because pytest's cache is a WRITE into the tree being
    proven (.pytest_cache appeared on every run and `--untracked-files=no` hid
    it); bytecode is already off via PYTHONDONTWRITEBYTECODE in the sanitized
    environment. With both silenced, anything the post-run check finds is a
    test's own doing."""
    for rel in TEST_ROOTS:
        assert os.path.isdir(os.path.join(root, rel)), \
            f"{rel} is absent from the tree — the scan has no premise"
    with tempfile.TemporaryDirectory() as t:
        xml = os.path.join(t, "r.xml")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly",
             "-p", "no:cacheprovider",
             "--no-header", "--tb=line", *(("-m", marker) if marker else ()),
             f"--junit-xml={xml}", *TEST_ROOTS],
            cwd=root, capture_output=True, text=True,
            env=env if env is not None else sanitized_env(root, home))
        # PC-2 (#827): STDERR IS PART OF THE DIAGNOSIS. These two asserts used
        # to print stdout only, so a child that died before capture started —
        # exactly the read-only-TMPDIR crash above — reported an empty message
        # while its traceback sat unread on stderr.
        assert proc.returncode in PYTEST_RAN, (
            f"pytest exited {proc.returncode} — the suite did not run as asked "
            f"(0/1 mean it ran; 2-5 mean interrupted, internal error, usage "
            f"error or nothing collected):\n{proc.stdout[-3000:]}"
            f"\n--- stderr ---\n{proc.stderr[-3000:]}")
        assert os.path.exists(xml), (
            "pytest produced no report at all — the run did not even start:\n"
            + proc.stdout[-2000:]
            + f"\n--- stderr ---\n{proc.stderr[-2000:]}")
        return parse_junit(io.open(xml, encoding="utf-8").read())


def post_run_changes(tree):
    """Everything the test run left behind in `tree` — tracked modifications,
    untracked files, AND ignored files. `--untracked-files=no` was an
    undisclosed narrowing: a test that DROPS a brand-new file into the tree
    corrupts the proof exactly as much as one that rewrites a tracked file, and
    it was invisible. `--ignored` closes the last blind spot: the tree carries
    tracked .gitignore files, so without it a dropping that happens to match an
    ignore rule vanished too. The isolated tree starts pristine and cache/
    bytecode writes are disabled, so anything reported here is a test's own."""
    out = git(["status", "--porcelain", "--untracked-files=all", "--ignored"],
              tree)
    return [ln for ln in out.stdout.decode().splitlines() if ln.strip()]


# The write probe's opt-in variable. Stripped from every child environment this
# file builds: the marker filter below is the CLASS guard (a deselected test
# never executes, whatever the environment holds); removing the variable is the
# second, independent barrier the incident of 2026-07-30 demanded.
WRITE_OPT_IN = "RUN_NEO4J_ROUNDTRIP_PROBE"


def write_expected():
    """Pin the identity list FROM THE LIVE TREE, never from the isolated one.

    THE CIRCULARITY THIS AVOIDS: the isolated tree is the thing under test. Pin
    from it and an omitted test file is written into the expectation as normal,
    so the one defect this file exists to catch becomes invisible. The live tree
    holds the complete suite, which is what the commit is supposed to carry —
    and it is pinned across BOTH lanes, so a test cannot escape the pin by
    carrying a marker.

    LIVE_WRITE IS NEVER RUNNABLE FROM HERE. The first version ran with the full
    environment and NO marker filter, so this bookkeeping command was one
    environment variable away from writing to the live graph. Now `-m "not
    live_write"` excludes the probe STRUCTURALLY, the opt-in variable is
    stripped as an independent second barrier, and the probe's identity enters
    the pin from gate_pins.jsonl — the reviewed pin, never an execution.
    Everything else keeps the full environment: this call's job is COMPLETENESS
    (a missing credential could turn a live test into a collection error whose
    identity is never emitted), and sanitizing is the clean lane's job.
    """
    home = tempfile.mkdtemp(prefix="gate_home_")
    try:
        env = {k: v for k, v in os.environ.items() if k != WRITE_OPT_IN}
        env["PYTHONPATH"] = _REPO
        env["PYTHONDONTWRITEBYTECODE"] = "1"    # this run is in the LIVE tree
        every = run_lane(_REPO, home, "not live_write", env)
    finally:
        shutil.rmtree(home, ignore_errors=True)
    pins = load_pins(io.open(PINS, encoding="utf-8").read())
    write_nodes = {n for n, r in pins.items() if r["kind"] == "live_write"}
    overlap = write_nodes & set(every)
    assert not overlap, (
        f"node(s) pinned live_write appeared in a 'not live_write' run — the "
        f"marker moved: {sorted(overlap)}")
    io.open(EXPECTED, "w", encoding="utf-8").write(
        "\n".join(sorted(set(every) | write_nodes)) + "\n")
    print(f"pinned {len(every)} identities from the LIVE tree + "
          f"{len(write_nodes)} live_write pin(s) -> {os.path.basename(EXPECTED)}")
    return 0


def classify(results, pins, expected):
    """The whole verdict, as a list of problems. Pure, so the regression matrix
    can drive it with synthetic input instead of a two-minute suite run."""
    problems = []
    live = set(pins)        # PIN_KINDS admits only live kinds — see its comment

    # 4. nothing may vanish — from the commit, or into a marker.
    covered = set(results) | live
    missing, extra = sorted(expected - covered), sorted(covered - expected)
    if missing:
        problems.append(f"{len(missing)} pinned test(s) neither ran in the clean "
                        f"lane nor are pinned as live — an omitted test file "
                        f"shrinks the suite instead of failing it: {missing[:5]}")
    if extra:
        problems.append(f"{len(extra)} identit(ies) are not in the pin: {extra[:5]}")
    ran_live = sorted(live & set(results))
    if ran_live:
        problems.append(f"{len(ran_live)} test(s) pinned as live RAN in the clean "
                        f"lane — the marker and the pin disagree: {ran_live[:5]}")

    # 6. every test PASSES. No exception kind exists to pin a skip or a
    # failure, so any non-pass is a problem, with its message kept — a missing
    # database and a real assertion must stay distinguishable to the reader.
    for node, (outcome, text) in sorted(results.items()):
        if outcome != "passed":
            problems.append(f"{node} {outcome} in the clean lane — every "
                            f"clean-lane test must PASS: {text.strip()[:160]}")
    return problems


def main():
    if "--write-expected" in sys.argv:
        return write_expected()

    problems = []
    staged = staged_paths()
    tree = index_tree()
    print(f"the candidate commit: tree {tree}, {len(staged)} paths changed "
          f"against HEAD")

    # P-O6 (#827) TREE-ID HANDOFF. The mutation battery captures ONE tree id and
    # certifies against it; this gate computes its own. Two independent reads of
    # a mutable index can silently disagree, and then each artifact is honest
    # about a DIFFERENT tree. A caller that knows which tree it is certifying
    # says so with --expect-tree, and a mismatch is a hard problem here rather
    # than a discrepancy nobody compares. Absent the flag, nothing changes.
    if "--expect-tree" in sys.argv:
        want = sys.argv[sys.argv.index("--expect-tree") + 1]
        if want != tree:
            problems.append(
                f"TREE-ID MISMATCH: the caller is certifying {want}, this index "
                f"yields {tree} — the two artifacts describe different trees")
        else:
            print(f"tree-id handoff: caller's {want} == this index (ok)")

    bad = forbidden(staged)
    print(f"forbidden paths among them: {len(bad)}"
          + (f" -> {bad}" if bad else " (none)"))
    if bad:
        problems.append(f"FORBIDDEN in the commit: {bad}")

    # A file edited but not re-staged would be tested in its OLD form. Not a
    # property of the commit — a property of my workflow — so it is reported,
    # and only about paths this work touches.
    dirty = [p for p in git(["diff", "--name-only"], _REPO).stdout.decode().split()
             if p in set(staged)]
    if dirty:
        print(f"edited since staging ({len(dirty)}): {dirty}")
        problems.append(f"{len(dirty)} staged file(s) have later unstaged edits — "
                        f"the tree below is not what is on disk")

    pins = load_pins(io.open(PINS, encoding="utf-8").read())
    expected = load_expected(io.open(EXPECTED, encoding="utf-8").read())
    n_read = sum(1 for r in pins.values() if r["kind"] == "live_read")
    print(f"pins: {len(pins)} live-lane node(s) ({n_read} read-only, "
          f"{len(pins) - n_read} owner-gated write probe, never run); "
          f"identities pinned: {len(expected)}")

    base = tempfile.mkdtemp(prefix="isolated_commit_")
    home = os.path.join(base, "home")
    os.makedirs(home)
    try:
        tmp = build_isolated_tree(tree, base)
        print(f"isolated tree verified: its own write-tree == {tree}")
        print(f"clean lane: -m {CLEAN_LANE!r}, environment built from "
              f"{len(SAFE_ENV)} allowlisted names, HOME redirected, no "
              f"credentials of any kind")
        results = run_lane(tmp, home, CLEAN_LANE)
        by = {}
        for outcome, _t in results.values():
            by[outcome] = by.get(outcome, 0) + 1
        print(f"clean-lane run: {by}")

        # 7. THE TESTS CHANGED NOTHING — tracked OR untracked. Proof 1 was
        # taken BEFORE pytest; a test that rewrites a tracked file would
        # invalidate it afterwards, unseen — and a test that DROPS a new file
        # into the tree corrupts it exactly as much. With the cache provider
        # and bytecode writes disabled, anything found here is a test's own.
        changed = post_run_changes(tmp)
        if changed:
            for ln in changed[:5]:
                print(f"   TEST-TIME CHANGE  {ln}")
            problems.append(f"the tests created or modified {len(changed)} "
                            f"file(s) in the isolated tree, so the tree that "
                            f"passed is not the tree that was verified")

        problems += classify(results, pins, expected)
        print(f"   live lanes: {len(pins)} node(s) pinned and run separately "
              f"(-m live read-only; -m live_write owner-gated, never run)")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print()
    if problems:
        print("THE COMMIT IS NOT PROVEN:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"THE COMMIT IS PROVEN: the isolated tree IS the commit (tree {tree}); "
          f"nothing forbidden; no duplicate pin, identity or JUnit id; the clean "
          f"lane ran with NO credentials and every one of its tests PASSED "
          f"(zero skips — no exception kind exists to pin one); every pinned "
          f"identity is accounted for in a lane; the tests left no tracked "
          f"modification and no untracked file behind.")
    return 0


if __name__ == "__main__":          # IMPORTING must not build a tree or run pytest
    raise SystemExit(main())
