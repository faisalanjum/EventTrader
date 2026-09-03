#!/usr/bin/env python3
"""Mutation campaign over the replay's own decision branches (Codex SEQ 1542).

A test that passes proves nothing on its own: it must also FAIL when the rule it
guards is broken. Each case below breaks exactly one branch of the implementation and
asserts the check catches it, and each carries an independent POSITIVE CONTROL - the
same check on the unmutated rule, which must pass. A mutation that goes unnoticed is
reported as SURVIVED, which is a hole in the evidence, not a pass.

Nothing here writes outside this directory and nothing runs a model or a subprocess of
the era. The replay modules are imported once and mutated in memory.
"""
import collections
import types
import hashlib
import contextlib
import io
import re
import json
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(R, "ledger"))
import chrono_replay as CR
import replay_caches
import replay_transcript as RT

BENCH = "bench_1306/.claude/plans/Drivers/experiments/harness"
ISO = "step1_iso/.claude/plans/Drivers/experiments/harness"
#: Codex's frozen append-only prefix, verified byte-exact this round
FROZEN = 210560179


def _rec(cmd):
    return {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                     "input": {"command": cmd}}]}}


# ---------------------------------------------------------------- the cases ---
def case_wrong_tree(mutate):
    """A record that edits ANOTHER tree's copy must not touch this owner.

    The command NAMES this owner's tree (it echoes the path it is comparing against),
    so the cheap prefilter passes and the decision falls to the rule that resolves a
    write destination - which is where the tree must be honoured.
    """
    P = "/tmp/claude-1000/x/scratchpad/p1319/.claude/plans/Drivers/experiments/harness"
    cmd = ('echo "comparing against %s/raw_transport.py"\n'
           'cd "%s" && python3 - <<\'PY\'\n'
           'import io\n'
           'io.open("raw_transport.py","w",encoding="utf-8").write("other tree")\n'
           'PY\n' % (BENCH, P))
    owner = BENCH + "/raw_transport.py"
    saved = CR._names_owner
    if mutate:
        FAULTS['wrong tree'].install()
    try:
        return CR.writes_this(cmd, owner) is False
    finally:
        CR._names_owner = saved


def case_wrong_cwd(mutate):
    """A relative name belongs to the `cd` that PRECEDES it, not to any other."""
    cmd = ("cd /tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments\n"
           "cat >> harness/raw_transport.py <<'PY'\nx = 1\nPY\n"
           "cd /tmp/claude-1000/x/scratchpad/step1_iso/.claude/plans/Drivers/experiments\n"
           "cat >> harness/audit_worker_access.py <<'PY'\ny = 2\nPY\n")
    saved = RT.cwd_at
    if mutate:
        FAULTS['wrong cwd for a relative name'].install()
    try:
        return (CR.writes_this(cmd, BENCH + "/raw_transport.py") is True
                and CR.writes_this(cmd, ISO + "/raw_transport.py") is False)
    finally:
        RT.cwd_at = saved


def case_sed_insert(mutate):
    """`sed -i.bak '2i TEXT'` inserts BEFORE line 2."""
    cmd = "sed -i.bak '2i import io' /x/harness/raw_transport.py\n"
    saved = RT.apply_sed
    if mutate:
        FAULTS['sed line insertion'].install()
    try:
        out, _ = RT.apply_saved_edits("A\nB\n", {1: _rec(cmd)},
                                      "harness/raw_transport.py")
    finally:
        RT.apply_sed = saved
    return out == "A\nimport io\nB\n"


def case_grep_guarded_sed(mutate):
    """`grep P F || sed -i ...` must NOT insert when the grep already finds it."""
    cmd = ("grep -n \"^import io\" /x/harness/raw_transport.py || "
           "sed -i '1i import io' /x/harness/raw_transport.py\n")
    saved = RT.sed_operations
    if mutate:
        FAULTS['grep-guarded sed is idempotent'].install()
    try:
        out, _ = RT.apply_saved_edits("import io\nB\n", {1: _rec(cmd)},
                                      "harness/raw_transport.py")
    finally:
        RT.sed_operations = saved
    return out == "import io\nB\n"


def case_no_final_newline(mutate):
    """A file with no trailing newline must not silently gain a spurious one."""
    cmd = "sed -i '1a X' /x/harness/raw_transport.py\n"
    saved = RT.apply_sed
    if mutate:
        FAULTS['no final newline'].install()
    try:
        out, _ = RT.apply_saved_edits("A", {1: _rec(cmd)}, "harness/raw_transport.py")
    finally:
        RT.apply_sed = saved
    return out == "A\nX\n"


def case_backup_restore(mutate):
    """`cp owner scratch` … edit … `cp scratch owner` is a NET ZERO record."""
    saved = RT._shell_compose
    if mutate:
        FAULTS['backup and restore is net zero'].install()
    cmd = ("cd /x/harness_dir\n"
           "A=audit_worker_access.py\n"
           "cp $A /tmp/claude-1000/aud_backup.py\n"
           "python3 - <<'PY'\n"
           "import io\n"
           "s = io.open('audit_worker_access.py').read()\n"
           "io.open('audit_worker_access.py','w').write(s.replace('KEEP','GONE'))\n"
           "PY\n"
           "cp /tmp/claude-1000/aud_backup.py $A\n")
    out, _ = RT.apply_saved_edits("KEEP\n", {1: _rec(cmd)},
                                  "harness_dir/audit_worker_access.py")
    try:
        return out == "KEEP\n"
    finally:
        RT._shell_compose = saved


def case_multi_file_program(mutate):
    """One program editing SEVERAL files must be seen by every file it touches."""
    cmd = ('python3 - <<\'PY\'\n'
           'import io\n'
           'H="/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/'
           'experiments/harness/"\n'
           'for f in ("raw_transport.py", "audit_worker_access.py"):\n'
           '    p = H + f\n'
           '    s = io.open(p).read()\n'
           '    io.open(p, "w").write(s.replace("OLD", "NEW"))\n'
           'PY\n')
    saved_multi = CR._py_path_multi
    if mutate:
        FAULTS['multi-file saved program'].install()
    try:
        got = [CR.writes_this(cmd, BENCH + "/" + n)
               for n in ("raw_transport.py", "audit_worker_access.py")]
    finally:
        CR._py_path_multi = saved_multi
    return got == [True, True]


def case_alias_cycle(mutate):
    """A cycle is caught on the CANONICAL path, so a second spelling cannot slip in."""
    saved = CR.canonical_path
    if mutate:
        FAULTS['canonical-path alias cycle'].install()
    try:
        a = CR.canonical_path("./a/../harness/x.py")
        b = CR.canonical_path("harness/x.py")
    finally:
        CR.canonical_path = saved
    return a == b


def case_not_a_path(mutate):
    """A file's TEXT handed to open() is not a path and must never build a route."""
    blob = "not a path\nit is a whole file's text\n" * 40
    saved = CR.looks_like_path
    if mutate:
        FAULTS["a file's text is not a path"].install()
    try:
        return CR.looks_like_path(blob) is False
    finally:
        CR.looks_like_path = saved


def _broken_apply_sed(text, kind, payload):
    """The pre-fix behaviour: whole-file substitution and a clamped line address."""
    import re as _re
    if kind == "subst":
        pat, rep, glob = payload
        return _re.sub(pat, rep, text, count=0 if glob else 1, flags=_re.M)
    lineno, where, ins = payload
    lines = text.splitlines(True)
    at = max(0, min(lineno - 1 if where == "i" else lineno, len(lines)))
    return "".join(lines[:at]) + ins + "\n" + "".join(lines[at:])


def _with_broken_sed(mutate, fn, name):
    saved = RT.apply_sed
    if mutate:
        FAULTS[name].install()
    try:
        return fn()
    finally:
        RT.apply_sed = saved


def case_out_of_range_insert(mutate):
    """A line address past the end runs no cycle, so it inserts NOTHING."""
    cmd = "sed -i '9i X' /x/harness/raw_transport.py\n"
    return _with_broken_sed(mutate, lambda: RT.apply_saved_edits(
        "A\nB\nC\n", {1: _rec(cmd)}, "harness/raw_transport.py")[0] == "A\nB\nC\n", 'out-of-range line insert')


def case_empty_file_insert(mutate):
    """With no input lines sed executes no cycle at all."""
    cmd = "sed -i '1i X' /x/harness/raw_transport.py\n"
    return _with_broken_sed(mutate, lambda: RT.apply_saved_edits(
        "", {1: _rec(cmd)}, "harness/raw_transport.py")[0] == "", 'empty-file line insert')


def case_per_line_substitution(mutate):
    """`s/a/b/` replaces the first match ON EVERY LINE, not once in the file."""
    cmd = "sed -i 's/a/b/' /x/harness/raw_transport.py\n"
    return _with_broken_sed(mutate, lambda: RT.apply_saved_edits(
        "a a\na a\n", {1: _rec(cmd)}, "harness/raw_transport.py")[0] == "b a\nb a\n", 'per-line substitution')


def case_guard_reads_the_named_file(mutate):
    """`grep P OTHER || sed ... THIS` guards on OTHER's content, not THIS file's."""
    cmd = ("grep -n \"^marker\" /tmp/claude-1000/other.py || "
           "sed -i '1i X' /x/harness/raw_transport.py\n")
    saved = RT.sed_operations
    if mutate:
        FAULTS['guard reads the named file'].install()
    try:
        side = {"/tmp/claude-1000/other.py": "marker\n"}
        out, _ = RT.apply_saved_edits("A\n", {1: _rec(cmd)},
                                      "harness/raw_transport.py", side=side)
        return out == "A\n"
    finally:
        RT.sed_operations = saved


def case_sed_command_order(mutate):
    """Operations run in the order written; regrouping them by kind changes the file."""
    cmd = ("sed -i '1i first' /x/harness/raw_transport.py\n"
           "sed -i 's/^first$/second/' /x/harness/raw_transport.py\n")
    saved = RT.sed_operations
    if mutate:
        FAULTS['sed command order'].install()
    try:
        out, _ = RT.apply_saved_edits("A\n", {1: _rec(cmd)},
                                      "harness/raw_transport.py")
        return out == "second\nA\n"
    finally:
        RT.sed_operations = saved


def case_bak_preserved(mutate):
    """`sed -i.bak` leaves the PRE-EDIT bytes beside the file for a later restore."""
    cmd = "sed -i.bak '1i X' /tmp/claude-1000/x.py\n"
    saved = RT.sed_operations
    if mutate:
        FAULTS['.bak preserved for restore'].install()
    try:
        side = {"/tmp/claude-1000/x.py": "A\n"}
        RT.apply_saved_edits("owner\n", {1: _rec(cmd)}, "harness/raw_transport.py",
                             side=side)
        return side.get("/tmp/claude-1000/x.py.bak") == "A\n"
    finally:
        RT.sed_operations = saved


def case_shell_termination(mutate):
    """A command whose whole saved result is a termination status made no edit."""
    cmd = ("pkill -f 'x'; sleep 1\n"
           "python3 - <<'PY'\n"
           "import io\n"
           "p='/x/harness/raw_transport.py'\n"
           "io.open(p,'w').write(io.open(p).read() + 'INVENTED\\n')\n"
           "PY\n")
    saved = RT.shell_terminated
    if mutate:
        FAULTS['shell termination'].install()
    try:
        out, _ = RT.apply_saved_edits("A\n", {1: _rec(cmd)},
                                      "harness/raw_transport.py",
                                      result="Exit code 144")
        return out == "A\n"
    finally:
        RT.shell_terminated = saved


def case_script_closure(mutate):
    """A command that EXECUTES a saved script owns that script's writes."""
    script = ("import io\n"
              "p = '/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/"
              "experiments/harness/raw_transport.py'\n"
              "io.open(p, 'w').write(io.open(p).read() + 'FROM SCRIPT\\n')\n")
    cmd = "python3 /tmp/claude-1000/apply_preflight_cli.py\n"
    owner = BENCH + "/raw_transport.py"
    saved_res, saved_cache = RT.SIBLING_RESOLVER, dict(CR._SCRIPT_CACHE)
    saved_texts = CR._executed_script_texts
    CR._SCRIPT_CACHE.clear()
    RT.SIBLING_RESOLVER = lambda p_, n: (
        script if p_.endswith("apply_preflight_cli.py") else None)
    if mutate:
        FAULTS['executed-script closure'].install()
    try:
        return CR.writes_this(cmd, owner) is True
    finally:
        RT.SIBLING_RESOLVER = saved_res
        CR._executed_script_texts = saved_texts
        CR._SCRIPT_CACHE.clear()
        CR._SCRIPT_CACHE.update(saved_cache)


def case_inline_concat_write(mutate):
    """`open(H + "name.py", "w")` names this owner. Recognising only a variable that
    holds the WHOLE path drops the record that restored a deleted region, so the file
    comes back ~92 KB short."""
    H = ("/tmp/claude-1000/x/scratchpad/" + BENCH + "/")
    cmd = ("cp %sraw_transport.py /tmp/claude-1000/rt.bak\n"
           "python3 - <<'PY'\n"
           "import io\n"
           'H = "%s"\n'
           'io.open(H + "raw_transport.py", "w", encoding="utf-8").write("X\\n")\n'
           "PY\n") % (H, H)
    owner = BENCH + "/raw_transport.py"
    saved = CR._py_paths
    if mutate:
        FAULTS['path built inside the open call'].install()
    try:
        return CR.writes_this(cmd, owner) is True
    finally:
        CR._py_paths = saved


def case_git_show_producer(mutate):
    """`git show <rev>:<rel> > DST` PRODUCES DST. Drop the producer and the step that
    reads DST finds nothing, so the whole command refuses and every edit it went on to
    make is lost."""
    cmd = ("cd /tmp/claude-1000/x/scratchpad/bench_1306 && git show "
           "HEAD:.claude/plans/Drivers/experiments/harness/raw_transport.py "
           "> /tmp/claude-1000/head_rt.py\n")
    side = {}
    saved = RT._GIT_SHOW_REDIRECT
    if mutate:
        FAULTS['git show produces its redirect target'].install()
    try:
        RT.seed_git_show(cmd, side)
        want = RT._committed("/x/" + BENCH + "/raw_transport.py",
                             commit=CR.tree_origin("bench_1306")[1])
        return side.get("/tmp/claude-1000/head_rt.py") == want
    finally:
        RT._GIT_SHOW_REDIRECT = saved


def case_cross_tree_destination(mutate):
    """An ABSOLUTE destination names its own tree: `cp $H/<n> $P/<n>` copies this owner
    INTO another tree and is not a write of it."""
    H = "/tmp/claude-1000/x/scratchpad/" + BENCH
    P = "/tmp/claude-1000/x/scratchpad/" + BENCH.replace("bench_1306", "p1319")
    owner = BENCH + "/raw_transport.py"
    cmd = 'H=%s\nP=%s\ncp "$H/raw_transport.py" "$P/raw_transport.py"\n' % (H, P)
    saved = CR._names_owner
    if mutate:
        FAULTS['absolute destination names its tree'].install()
    try:
        return CR.writes_this(cmd, owner) is False
    finally:
        CR._names_owner = saved


def case_binary_read(mutate):
    """A BINARY read must give BYTES. Serving text whatever the mode killed every
    saved program that hashed a file - a failure of the replay, not of history."""
    import hashlib
    owner = BENCH + "/thing.py"
    prog = ("import hashlib, io\n"
            "d = hashlib.sha256(io.open('thing.py', 'rb').read()).hexdigest()\n"
            "io.open('thing.py', 'w').write('DIGEST ' + d[:8] + '\\n')\n")
    cmd = ("cd /tmp/claude-1000/x/scratchpad/" + BENCH +
           "\npython3 - <<'PY'\n%s\nPY\n" % prog)
    saved = RT._reader
    if mutate:
        FAULTS['binary read yields bytes'].install()
    try:
        got = _outcome(
            lambda: RT.apply_saved_edits("hello\n", {1: _rec(cmd)}, owner, side={})[0],
            TypeError)
        return got == "DIGEST %s\n" % hashlib.sha256(b"hello\n").hexdigest()[:8]
    finally:
        RT._reader = saved


def case_result_by_id(mutate):
    """A command's saved result is found by its tool_use_id. Record 23746's result sits
    six lines below it, so a fixed look-ahead read it as ABSENT - turning a failure
    history ALSO had into an unexplained refusal."""
    saved = RT.result_ledger
    if mutate:
        FAULTS['result found by its tool_use_id'].install()
    try:
        got = RT.saved_result(23746)
        return got is not None and "AssertionError" in got
    finally:
        RT.result_ledger = saved


def _cmd_at(line):
    rec = RT.lines([line])[line]
    for b in ((rec.get("message") or {}).get("content") or []):
        if isinstance(b, dict) and b.get("type") == "tool_use":
            return (b.get("input") or {}).get("command") or ""
    raise AssertionError(line)


G1V3 = BENCH.replace("harness", "harness_g1v3")


def case_cwd_names_the_tree(mutate):
    """A `cd` into a sibling tree decides which copy a RELATIVE name means."""
    saved = RT.cwd_at
    if mutate:
        FAULTS['a cd names the tree'].install()
    try:
        cmd = _cmd_at(72328)
        return (CR.writes_this(cmd, BENCH + "/test_harness_guards.py") is False
                and CR.writes_this(cmd, G1V3 + "/test_harness_guards.py") is True)
    finally:
        RT.cwd_at = saved


def case_text_inside_a_program(mutate):
    """A filename PRINTED by a program is not a write by the shell around it."""
    saved = RT.process_units
    if mutate:
        FAULTS['text inside a program is not a write'].install()
    try:
        return CR.writes_this(_cmd_at(28721), BENCH + "/test_harness_guards.py") is False
    finally:
        RT.process_units = saved


def case_only_owning_processes_run(mutate):
    """A sibling process that edits another file is not this owner's business."""
    saved = RT.SELECT_UNITS
    if mutate:
        FAULTS['only owning processes run'].install()
    try:
        H = "/tmp/claude-1000/x/scratchpad/" + BENCH
        # the unrelated program writes ANOTHER file: if it ran, that write shows in
        # the side table; a cut-short restore (rule 26) cannot hide that
        cmd = ("python3 - <<'PY'\nimport io\n"
               "io.open('%s/other.py','w').write('X\\n')\nPY\n"
               "python3 - <<'PY'\nimport io\n"
               "io.open('%s/thing.py','w').write('OWNER\\n')\nPY\n" % (H, H))
        side = {}
        got = _outcome(
            lambda: RT.apply_saved_edits("BASE\n", {1: _rec(cmd)},
                                         BENCH + "/thing.py", side=side)[0],
            RT.ReplayEnvironmentError)
        return got == "OWNER\n" and not any(k.endswith("/other.py") for k in side)
    finally:
        RT.SELECT_UNITS = saved


def case_termination_decided_first(mutate):
    """A killed command reached NO step - not the shell composer either."""
    saved = RT.shell_terminated
    if mutate:
        FAULTS['termination decided first'].install()
    try:
        H = "/tmp/claude-1000/x/scratchpad/" + BENCH
        cmd = "cat >> %s/thing.py <<'PY'\nINVENTED\nPY\n" % H
        out, _ = RT.apply_saved_edits("BASE\n", {1: _rec(cmd)}, BENCH + "/thing.py",
                                      side={}, result="Exit code 144")
        return out == "BASE\n"
    finally:
        RT.shell_terminated = saved


def case_script_cache_per_cutoff(mutate):
    """A script's text at one cutoff is not its text at another."""
    CR._SCRIPT_CACHE.clear()
    saved_res, saved_cache = RT.SIBLING_RESOLVER, dict(CR._SCRIPT_CACHE)
    RT.SIBLING_RESOLVER = lambda p, before: "AT_%d\n" % before
    path = "/tmp/claude-1000/s/tool.py"
    cmd = "python3 %s\n" % path
    try:
        a = CR._executed_script_texts(cmd, 10)
        if mutate:
            # the ACTUAL broken rule: keyed by path, so the first answer is reused
            FAULTS['script cached per cutoff'].install()
        b = CR._executed_script_texts(cmd, 30)
        # the poisoned entry lies AHEAD of the cutoff that wrote it: a later consumer at
        # the poisoned cutoff must still be answered for its own line
        c = CR._executed_script_texts(cmd, 50)
        return a == ["AT_10\n"] and b == ["AT_30\n"] and c == ["AT_50\n"]
    finally:
        RT.SIBLING_RESOLVER = saved_res
        CR._SCRIPT_CACHE.clear()
        CR._SCRIPT_CACHE.update(saved_cache)


def case_empty_result_is_present(mutate):
    """A command that completed with no output has an EMPTY result, not none."""
    L = RT.result_ledger()
    saved = RT.result_ledger
    if mutate:
        FAULTS['an empty result is present'].install()
    try:
        return RT.result_present(24632) is True
    finally:
        RT.result_ledger = saved


class _AlwaysAgrees(set):
    """A stored applied-set that claims to match whatever it is compared with."""

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __hash__(self):
        return 0


class _Agreeable(dict):
    """The resume point, with its record of WHICH records produced it made useless."""

    def __setitem__(self, key, value):
        if isinstance(value, tuple) and len(value) == 4:
            value = (value[0], value[1], value[2], _AlwaysAgrees())
        dict.__setitem__(self, key, value)


def case_ledger_accounts_for_every_row(mutate):
    """The counts must add up to the FILE. A corrupt row carries no keywords, so a
    keyword prefilter excused it from the accounting entirely."""
    saved = RT._LEDGERS
    RT._LEDGERS = {}
    src = io.open(os.path.join(R, "ledger", "replay_transcript.py"),
                  encoding="utf-8").read()
    try:
        if mutate:
            # the ACTUAL broken rule: only rows that mention a tool block are parsed,
            # so a truncated row is never seen and never counted
            ns = {"__name__": "mutant_replay_transcript",
                  "__file__": os.path.join(R, "ledger", "replay_transcript.py")}
            exec(compile(src.replace(
                "        try:\n            rec = json.loads(row, strict=False)\n"
                "        except ValueError:\n            L.corrupt.append(i)\n"
                "            continue\n"
                "        if '\"tool_use\"' not in row and '\"tool_result\"' not in row:\n"
                "            continue",
                "        if '\"tool_use\"' not in row and '\"tool_result\"' not in row:\n"
                "            continue\n"
                "        try:\n            rec = json.loads(row, strict=False)\n"
                "        except ValueError:\n            L.corrupt.append(i)\n"
                "            continue"),
                "<mutant>", "exec"), ns)
            L = ns["result_ledger"](RT.TRANSCRIPT, limit_bytes=FROZEN)
        else:
            L = RT.result_ledger(RT.TRANSCRIPT, limit_bytes=FROZEN)
        return L.corrupt == [93274] and L.rows == 111621
    finally:
        RT._LEDGERS = saved


def case_child_audit_crosses_the_boundary(mutate):
    """A child interpreter's reads must be audited too: a run that looks clean only
    because its child was invisible proves nothing about the package."""
    import subprocess
    import tempfile
    sys.path.insert(0, R)
    import run_resume_path as RRP
    d = tempfile.mkdtemp(prefix="childmut_", dir=os.path.join(R, "logs"))
    dep = os.path.join(d, "dep.json")
    io.open(dep, "w", encoding="utf-8").write("{}\n")
    audit = os.path.join(d, "audit.txt")
    prog = "import io\nio.open(%r, encoding='utf-8').read()\n" % dep
    RRP.child_opened.clear()
    saved = RRP._CHILD_AUDIT
    if mutate:
        FAULTS['child audit crosses the boundary'].install()
    try:
        unpatch = RRP.instrument_children(audit)
        try:
            subprocess.run([sys.executable, "-B", "-c", prog, "x"],
                           capture_output=True)
        finally:
            unpatch()
        return dep in RRP.child_opened
    finally:
        RRP._CHILD_AUDIT = saved
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def case_package_manifest_compares_content(mutate):
    """`--verify` must re-measure BYTES, not just the file list. Comparing names only
    lets an edited file pass as the package it was frozen from.

    Built on its own throwaway tree so it never depends on the live manifest being
    current - a control that only passes in the right order is not a control.
    """
    import shutil
    import tempfile
    sys.path.insert(0, R)
    import freeze_package as FP
    stage = tempfile.mkdtemp(prefix="pkgmut_", dir=os.path.join(R, "logs"))
    saved_R, saved_entries = FP.R, FP.entries
    try:
        io.open(os.path.join(stage, "a.py"), "w", encoding="utf-8").write("frozen\n")
        FP.R = stage
        if mutate:
            # the ACTUAL broken rule: the manifest records only the path, on BOTH
            # sides, so a file whose bytes changed still "verifies"
            FAULTS['package manifest compares content'].install()
        FP.write()                                   # freeze the throwaway package
        io.open(os.path.join(stage, "a.py"), "w", encoding="utf-8").write("CHANGED\n")
        return FP.verify() != 0                      # a changed file MUST be caught
    finally:
        FP.entries = saved_entries
        FP.R = saved_R
        shutil.rmtree(stage, ignore_errors=True)


def case_heredoc_opening_line_continues(mutate):
    """`python3 - <<'PY' 2>&1 | tail -22` runs a program exactly as `<<'PY'` does."""
    cmd = ("cd /tmp/x && /usr/bin/python3 -B - <<'PY' 2>&1 | tail -22\n"
           "import io\n"
           "io.open('out.json','w').write('[]')\n"
           "PY\n")
    saved = RT.program_spans
    if mutate:
        FAULTS['heredoc opening line continues'].install()
    try:
        return len(RT.program_spans(cmd)) == 1
    finally:
        RT.program_spans = saved


def case_module_import_is_served(mutate):
    """A replayed program may IMPORT a sibling, not only open it."""
    saved = RT._SiblingFinder
    H = "/tmp/claude-1000/x/scratchpad/" + BENCH
    side = {H + "/helper_mod.py": "VALUE = 7\n"}
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\nimport helper_mod\n"
           "io.open('thing.py','w').write('V%%d\\n' %% helper_mod.VALUE)\nPY\n" % H)
    if mutate:
        FAULTS['a module import is served'].install()
    try:
        got = _outcome(
            lambda: RT.apply_saved_edits("BASE\n", {1: _rec(cmd)},
                                         BENCH + "/thing.py", side=side)[0],
            ModuleNotFoundError)
        return got == "V7\n"
    finally:
        RT._SiblingFinder = saved


def case_recovered_artefact_era(mutate):
    """A recovered artefact belongs to an ERA. One path holds six bodies across this
    campaign; serving a single one for every cutoff hands a record bytes it never saw."""
    import hashlib
    INV = ".claude/plans/Drivers/experiments/one_item_benchmark_inventory.json"
    saved = CR._recovered
    if mutate:
        FAULTS['a recovered artefact has an era'].install()
    try:
        pre = CR._recovered("/x/" + INV, 22000)
        early = CR._recovered("/x/" + INV, 22600)
        late = CR._recovered("/x/" + INV, 29200)
        return (pre is None and early is not None and late is not None
                and hashlib.sha256(early.encode()).hexdigest().startswith("165be143")
                and hashlib.sha256(late.encode()).hexdigest().startswith("b137e87e"))
    finally:
        CR._recovered = saved


def case_tree_sibling_is_not_a_producer(mutate):
    """A source with its own TREE is resolved as a sibling, never executed as an
    ephemeral producer against the consuming owner."""
    tree_sibling = ("/tmp/claude-1000/-home/s/scratchpad/bench_1306/.claude/plans/"
                    "Drivers/experiments/one_item_benchmark_inventory.json")
    side_file = "/tmp/claude-1000/rt_keep.py"
    saved = CR.is_side_file
    if mutate:
        FAULTS['a tree sibling is not a producer'].install()
    try:
        return (CR.is_side_file(tree_sibling) is False
                and CR.is_side_file(side_file) is True)
    finally:
        CR.is_side_file = saved


def case_era_less_fallback_may_not_fill_a_pre_series_window(mutate):
    """The exact defect Codex found: an era-less body registered beside a timed series
    filled the window BEFORE the first timed body, so a record was handed bytes from an
    era that had not happened yet. Built on its own index so the package's real one is
    untouched."""
    import hashlib
    import shutil
    import tempfile
    stage = tempfile.mkdtemp(prefix="eramut_", dir=os.path.join(R, "logs"))
    saved_dir = CR._RECOVERED_DIR
    try:
        early = "EARLY" + chr(10)
        stale = "STALE" + chr(10)
        io.open(os.path.join(stage, "early.json"), "w", encoding="utf-8").write(early)
        io.open(os.path.join(stage, "stale.json"), "w", encoding="utf-8").write(stale)
        sha = lambda t: hashlib.sha256(t.encode()).hexdigest()
        io.open(os.path.join(stage, "RECOVERED.tsv"), "w", encoding="utf-8").write(
            "%s\t.claude/x/thing.json%s" % (sha(stale), chr(10)) +
            "%s\t.claude/x/thing.json\t500\tearly.json%s" % (sha(early), chr(10)))
        CR._RECOVERED_DIR = stage
        if mutate:
            globals()["_ERA_LESS_STALE"] = stale
            FAULTS["an era-less fallback may not fill a pre-series window"].install()
        before = CR._recovered("/x/.claude/x/thing.json", 100)
        after = CR._recovered("/x/.claude/x/thing.json", 600)
        return before is None and after == early
    finally:
        CR._RECOVERED_DIR = saved_dir
        shutil.rmtree(stage, ignore_errors=True)


def case_the_product_check_is_real(mutate):
    """The report must INSPECT the producer's product, not the owner's text.

    This runs the real `classify()` on the live audit route, so it proves the inspection
    happened - calling the pure outcome helper proves only that the helper is correct.
    The mutant neuters the product lookup exactly as the original defect did: the
    producer's side file is never consulted, so a real product reads as no change.
    """
    import contextlib
    sys.path.insert(0, R)
    src = io.open(os.path.join(R, "branch_inventory.py"), encoding="utf-8").read()
    if mutate:
        src = FAULTS['the product check is real'].patched_source(src)
    ns = {"__name__": "branch_inventory_mutant",
          "__file__": os.path.join(R, "branch_inventory.py")}
    exec(compile(src, "<mutant:branch_inventory>", "exec"), ns)
    owner = BENCH + "/audit_worker_access.py"
    with contextlib.redirect_stdout(io.StringIO()):
        _rows, _detail, _text, products = ns["classify"](owner, 33828)
    return bool(products) and all(
        r["present"] and r["bytes"] and r["sha256"]
        and r["product_status"] == "correct" and r["call_outcome"] == "completed"
        for r in products.values())


def case_a_wrong_product_is_rejected(mutate):
    """PRESENCE IS NOT CORRECTNESS. A producer that writes the right path, present and
    nonempty, but the WRONG bytes, must fail closed - it read `applied` before.

    Run through the real `classify()` so the identity comparison is proved to happen,
    not merely to exist.
    """
    import contextlib
    sys.path.insert(0, R)
    src = io.open(os.path.join(R, "branch_inventory.py"), encoding="utf-8").read()
    if mutate:
        src = FAULTS['a wrong product is rejected'].patched_source(src)
    ns = {"__name__": "branch_inventory_mutant",
          "__file__": os.path.join(R, "branch_inventory.py")}
    exec(compile(src, "<mutant:branch_inventory>", "exec"), ns)
    owner = BENCH + "/audit_worker_access.py"
    with contextlib.redirect_stdout(io.StringIO()):
        _recs, producers = CR.route_records(owner, CR.tree_origin("bench_1306")[0],
                                            33828)
    real = RT.apply_saved_edits

    def corrupt(text, records, basename, prepare=None, side=None, result=None):
        line = list(records)[0]
        if line in producers:
            side[producers[line]] = "BROKEN" + chr(10)
            return text, {}
        return real(text, records, basename, prepare, side, result)
    RT.apply_saved_edits = corrupt
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            _rows, _detail, _text, products = ns["classify"](owner, 33828)
    finally:
        RT.apply_saved_edits = real
    return bool(products) and all(
        r["product_status"] == "wrong" for r in products.values())


def _classify_audit(src_edit=None):
    """Run the REAL report on the live audit route, optionally with one edited rule."""
    import contextlib
    sys.path.insert(0, R)
    src = io.open(os.path.join(R, "branch_inventory.py"), encoding="utf-8").read()
    if src_edit is not None:
        old, new_ = src_edit
        assert src.count(old) == 1, "mutation anchor"
        src = src.replace(old, new_, 1)
    ns = {"__name__": "branch_inventory_mutant",
          "__file__": os.path.join(R, "branch_inventory.py")}
    exec(compile(src, "<mutant:branch_inventory>", "exec"), ns)
    with contextlib.redirect_stdout(io.StringIO()):
        return ns, ns["classify"](BENCH + "/audit_worker_access.py", 33828)


def case_termination_precedes_execution(mutate):
    """A terminated producer must not execute. Proved by watching whether it ran."""
    edit = None
    if mutate:
        edit = FAULTS['termination precedes execution'].source_edit()
    saved_term, saved_apply = RT.shell_terminated, RT.apply_saved_edits
    ran = []

    def watch(text, records, basename, prepare=None, side=None, result=None):
        ran.append(list(records)[0])
        return saved_apply(text, records, basename, prepare, side, result)
    RT.shell_terminated = lambda r: True
    RT.apply_saved_edits = watch
    try:
        _ns, (_rows, _detail, _text, products) = _classify_audit(edit)
        return (bool(products)
                and all(r["call_outcome"] == "terminated" for r in products.values())
                and not [n for n in ran if n in products])
    finally:
        RT.shell_terminated, RT.apply_saved_edits = saved_term, saved_apply


def case_absent_result_is_not_completed(mutate):
    """Local replay producing bytes may not credit a call history never answered."""
    sys.path.insert(0, R)
    import branch_inventory as BI
    saved = BI.call_outcome
    if mutate:
        FAULTS['an absent result is not completed'].install()
    try:
        return (BI.call_outcome(False, None, False, False) == "missing-result"
                and BI.call_outcome(False, None, False, True) == "waiting"
                and BI.call_outcome(False, "ok", True, False) == "completed")
    finally:
        BI.call_outcome = saved


def case_bench_module_hidden(mutate):
    """A replayed import is served from its world even when the process pre-loaded the bench owner."""
    import contextlib, io as _io, sys as _sys
    if mutate:
        FAULTS['a pre-loaded bench module answers a replayed import'].install()
    bench_h = os.path.join(R, "bench", ".claude", "plans", "Drivers", "experiments", "harness")
    _sys.path.insert(0, bench_h)
    os.environ.setdefault("GUIDANCE_SCRIPTS_DIR", os.path.join(R, "bench", ".claude", "skills", "earnings-orchestrator", "scripts"))
    import kf_lint                                             # noqa: F401 - pre-loaded on purpose
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    side = {H + "/kf_lint.py": "def part_lookup(source_id, inputs_dir):\n    return {'ok': source_id}\n"}
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\nimport kf_lint\n"
           "io.open('thing.py','w').write(kf_lint.part_lookup('SID','d')['ok'] + '\\n')\nPY\n" % H)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
    try:
        with contextlib.redirect_stdout(_io.StringIO()):
            out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", side=side)
    except Exception:
        return False
    return out == "SID\n"


def case_unmapped_tmp_refuses(mutate):
    """An unmapped /tmp read is a temporary read, never covered."""
    sys.path.insert(0, R)
    import run_resume_path as RRP
    if mutate:
        FAULTS['an unmapped /tmp read is covered'].install()
    return (RRP.classify_read("/tmp/claude-1000/x/unmapped.json", set(), None) == "temporary"
            and RRP.classify_read("/tmp/claude-1000/x/unmapped.json", set(), {"/tmp/claude-1000/x/other": ("b", "0" * 64)}) == "temporary")


def case_invalid_attempt_not_valid(mutate):
    """The owner's shape refusal keeps the two invalid attempt-1 replies invalid."""
    import contextlib, io as _io
    sys.path.insert(0, os.path.join(R, "proofs"))
    import accepted_evidence_census as AEC
    if mutate:
        FAULTS['a schema-invalid attempt is counted as valid'].install()
    with contextlib.redirect_stdout(_io.StringIO()):
        rep = AEC.census(R)
    a = rep["accounting"]
    return a["schema_invalid_attempts"] == 2 and a["schema_valid_attempts"] == 36 and len(rep["lawful_attempt2_replacements"]) == 2


def case_raw_prefilter_escaped_script(mutate):
    """The raw prefilter sees a script run whose quoted path carries the JSON escape."""
    sys.path.insert(0, os.path.join(R, "ledger"))
    import chrono_replay as CR
    if mutate:
        FAULTS['the raw prefilter misses a JSON-escaped script path'].install()
    return bool(CR._RUNS_SCRIPT.search('{"command":"S=/tmp/x\\nPYTHONDONTWRITEBYTECODE=1 /v/bin/python -B \\"$S/harvest.py\\" 11 sid wf_1 1"}')) and not CR._RUNS_SCRIPT.search("python3 - <<'PY'")


def _rec_of(cmd):
    return {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                     "input": {"command": cmd}}]}, "cwd": "/home/x"}


def case_cut_short_keeps_write(mutate):
    """A write survives a later environment failure when the rest never names the file."""
    import contextlib, io as _io
    if mutate:
        FAULTS['a cut-short program always loses its write'].install()
    try:
        with contextlib.redirect_stdout(_io.StringIO()):
            out, _ = RT.apply_saved_edits("", {1: _rec_of("python3 - <<'PY'\nimport io, subprocess\nio.open('/tmp/claude-1000/x/scratchpad/run4/attempts.json', 'w').write('[]')\nsubprocess.run(['claude', 'auth', 'status'])\nprint('done')\nPY\n")}, "run4/attempts.json", side={})
    except Exception:
        return False
    return out == "[]"


def case_stdin_argv(mutate):
    """A stdin program with arguments gets them."""
    import contextlib, io as _io
    if mutate:
        FAULTS['a stdin program keeps the synthetic argv'].install()
    try:
        with contextlib.redirect_stdout(_io.StringIO()):
            out, _ = RT.apply_saved_edits("", {1: _rec_of('S=/tmp/claude-1000/x/scratchpad\nRUN="$S/run4"\npython3 - "$RUN" <<\'PY\'\nimport io, os, sys\nio.open(os.path.join(sys.argv[1], \'other.json\'), \'w\').write(\'SIB\')\nio.open(\'/tmp/claude-1000/x/scratchpad/run4/attempts.json\', \'w\').write(io.open(\'/tmp/claude-1000/x/scratchpad/run4/other.json\').read())\nPY\n')}, "run4/attempts.json", side={})
    except Exception:
        return False
    return out == "SIB"


def case_prefilter_reads_scripts(mutate):
    """The pre-filter admits a command whose executed script names the file."""
    sys.path.insert(0, os.path.join(R, "ledger"))
    import chrono_replay as CR
    if mutate:
        FAULTS['the pre-filter never reads an executed script'].install()
    saved = CR._executed_script_texts
    CR._executed_script_texts = lambda cmd, before_line=None: ["import io, os\nRUN = ('/tmp/claude-1000/x/scratchpad' '/run4')\nio.open(os.path.join(RUN, 'attempts.json'), 'w').write('[]')\n"] if "harvest.py" in cmd else []
    try:
        return (CR.writes_this('S=/tmp/claude-1000/x/scratchpad\npython -B "$S/harvest.py" 11 sid wf_1 1 | tail -8\n', '/tmp/claude-1000/x/scratchpad/run4/attempts.json', line=5, start="/home/x")
                and not CR.writes_this('S=/tmp/claude-1000/x/scratchpad\npython -B "$S/harvest.py" 11 sid wf_1 1 | tail -8\n', '/tmp/claude-1000/x/scratchpad/run3/attempts.json', line=5, start="/home/x"))
    finally:
        CR._executed_script_texts = saved


def case_sed_after_cd(mutate):
    """A sed after a same-line cd names its file from where the shell stood."""
    sys.path.insert(0, os.path.join(R, "ledger"))
    import chrono_replay as CR
    if mutate:
        FAULTS['a sed after a cd names its file from the record start'].install()
    cmd = "cd /tmp/claude-1000/x/scratchpad/step1_envelope/.claude/plans/Drivers/experiments && sed -i 's|old_guard|new_guard|' harness/test_harness_guards.py\n"
    return (CR.writes_this(cmd, '/tmp/claude-1000/x/scratchpad/step1_envelope/.claude/plans/Drivers/experiments/harness/test_harness_guards.py', line=1, start="/home/x")
            and not CR.writes_this(cmd, '/tmp/claude-1000/x/scratchpad/step1_ctl/.claude/plans/Drivers/experiments/harness/test_harness_guards.py', line=1, start="/home/x"))


def case_sed_in_place_route(mutate):
    """sed -i on a quoted file is a route of that file."""
    sys.path.insert(0, os.path.join(R, "ledger"))
    import chrono_replay as CR
    if mutate:
        FAULTS['an in-place sed is not a route'].install()
    cmd = 'S=/tmp/claude-1000/x/scratchpad\nsed -i \'s#/scratchpad/invrev_run3#/scratchpad/invrev_run4#\' "$S/harvest.py"\n'
    return (CR.writes_this(cmd, '/tmp/claude-1000/x/scratchpad/harvest.py', line=1, start="/home/x")
            and not CR.writes_this(cmd, '/tmp/claude-1000/x/scratchpad/other.py', line=1, start="/home/x"))


def case_sed_file_token_unquoted(mutate):
    """A routed sed -i on a quoted file is applied at replay."""
    import contextlib, io as _io
    if mutate:
        FAULTS["the sed file token keeps its quotes"].install()
    cmd = 'S=/tmp/claude-1000/x/scratchpad\nsed -i \'s#/scratchpad/invrev_run3#/scratchpad/invrev_run4#\' "$S/harvest.py"\n'
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits('RUN = "/tmp/claude-1000/x/scratchpad/invrev_run3"\n', {1: rec}, "harvest.py", side={})
    return out == 'RUN = "/tmp/claude-1000/x/scratchpad/invrev_run4"\n'


def case_join_write(mutate):
    """A write through os.path.join(literal directory, name) names that file."""
    sys.path.insert(0, os.path.join(R, "ledger"))
    import chrono_replay as CR
    if mutate:
        FAULTS['a join-form write is not a write'].install()
    S = "/tmp/claude-1000/x/scratchpad"
    cmd = ('python3 - <<\'PY\'\nimport io, os\nRUN = ("%s"\n       "/invrev_run2")\n'
           'io.open(os.path.join(RUN, "attempts.json"), "w", encoding="utf-8").write("[]")\nPY\n' % S)
    return (CR.writes_this(cmd, S + "/invrev_run2/attempts.json", line=1, start="/home/x")
            and not CR.writes_this(cmd, S + "/invrev_run3/attempts.json", line=1, start="/home/x"))


def case_argv_bound(mutate):
    """A write through os.path.join(sys.argv[1], name) names the file under the passed directory."""
    sys.path.insert(0, os.path.join(R, "ledger"))
    import chrono_replay as CR
    if mutate:
        FAULTS["a program's argument is not bound"].install()
    S = "/tmp/claude-1000/x/scratchpad"
    cmd = ('S=%s\nRUN="$S/invrev_run2"\npython3 - "$RUN" <<\'PY\'\nimport io, os, sys\nrun = sys.argv[1]\n'
           'io.open(os.path.join(run, "attempts.json"), "w", encoding="utf-8").write("[]")\nPY\n' % S)
    return (CR.writes_this(cmd, S + "/invrev_run2/attempts.json", line=1, start="/home/x")
            and not CR.writes_this(cmd, S + "/invrev_run3/attempts.json", line=1, start="/home/x"))


def case_no_real_sleep(mutate):
    """A replayed program's sleep decides nothing and takes no time."""
    import contextlib, io as _io, time as _t
    if mutate:
        FAULTS['a replayed program sleeps real time'].install()
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    cmd = ("cd %s\npython3 - <<'PY'\nimport io, time\nt = time.time(); time.sleep(1.5)\n"
           "io.open('thing.py','w').write(str(time.time() - t < 1) + '\\n')\nPY\n" % H)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: rec},
                                      "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", side={})
    return out == "True\n"


def case_stat_miss_recorded(mutate):
    """An absent mounted file asked through isfile is a recorded miss."""
    import tempfile
    if mutate:
        FAULTS['a stat miss on a mount is not recorded'].install()
    d = tempfile.mkdtemp(); root = "/hist/session/workflows"
    saved = dict(RT.MOUNTS); RT.MOUNTS[root] = d
    try:
        del RT.MOUNT_MISSES[:]
        return (RT._world_isfile(root + "/gone.json", {}) is False
                and root + "/gone.json" in RT.MOUNT_MISSES)
    finally:
        RT.MOUNTS.clear(); RT.MOUNTS.update(saved)


def case_seed_tree_climb_stops(mutate):
    """A copy source outside every seeded tree has no seed tree, promptly."""
    import signal
    if mutate:
        FAULTS['the seed-tree climb never stops at the root'].install()
    def _alarm(_sig, _frm):
        raise TimeoutError("the climb did not end")
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(5)
    try:
        return (RT._seed_tree("/home/faisal/EventMarketDB/driver/core") is None
                and RT._seed_tree("/x/step1_iso/a/b") == "/x/step1_iso")
    except TimeoutError:
        return False
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def case_exact_path_lookup(mutate):
    """A path the world does not hold is absent, not a suffix-matching neighbour."""
    if mutate:
        FAULTS['a lookup is answered by a suffix match'].install()
    side = {"/w/a/scripts/f.py": "A\n"}
    return (RT._resolve_source("/w/a/scripts/f.py", side, None) == "A\n"
            and RT._resolve_source("/w/b/scripts/f.py", side, None) is None)


def case_bare_exception_class(mutate):
    """A saved traceback ending in a bare exception class is the same failure."""
    sys.path.insert(0, R)
    import branch_inventory as BI
    saved = BI.call_outcome
    if mutate:
        FAULTS['a bare exception class never matches'].install()
    saved_result = ("Traceback (most recent call last):\n  File \"<stdin>\", line 6, in <module>\n"
                    "AssertionError\nShell cwd was reset to /home/faisal/EventMarketDB")
    try:
        return (BI.call_outcome(True, saved_result, True, False,
                                replay_error=("AssertionError", "")) == "faithfully-failed"
                and BI.call_outcome(True, saved_result, True, False,
                                    replay_error=("AssertionError", "x")) == "refused")
    finally:
        BI.call_outcome = saved


def case_the_two_facts_do_not_collapse(mutate):
    """A wrong product may not erase what the call did, nor the reverse."""
    edit = None
    if mutate:
        edit = FAULTS['the two facts do not collapse'].source_edit()
    saved_apply = RT.apply_saved_edits
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        _recs, producers = CR.route_records(BENCH + "/audit_worker_access.py",
                                            CR.tree_origin("bench_1306")[0], 33828)

    def wrong_then_fail(text, records, basename, prepare=None, side=None, result=None):
        line = list(records)[0]
        if line in producers:
            side[producers[line]] = "BROKEN" + chr(10)
            raise RuntimeError("after the product")
        return saved_apply(text, records, basename, prepare, side, result)
    saved_res = RT.saved_result
    RT.apply_saved_edits = wrong_then_fail
    RT.saved_result = lambda line, path=None: "Traceback (most recent call last)"
    try:
        _ns, (_rows, _detail, _text, products) = _classify_audit(edit)
        return bool(products) and all(
            r["product_status"] == "wrong" and r["call_outcome"] == "faithfully-failed"
            for r in products.values())
    finally:
        RT.apply_saved_edits, RT.saved_result = saved_apply, saved_res


def case_the_report_lists_every_call_state(mutate):
    """Every state must appear even when empty: a live zero only means something if the
    bucket exists at all."""
    sys.path.insert(0, R)
    import branch_inventory as BI
    saved = BI.producer_report
    if mutate:
        FAULTS['the report lists every call state'].install()
    try:
        # THE ORACLE IS LITERAL. Comparing the report's keys to the production
        # constants makes expected and actual drop a state together, which is no check
        # at all.
        want_call = ["completed", "faithfully-failed", "historically-failed",
                     "missing-result", "refused", "terminated", "waiting"]
        want_product = ["correct", "missing", "not-attempted", "unpinned", "wrong"]
        one = {1: {"product_status": "correct", "call_outcome": "completed",
                   "finalizable": True}}
        rep = BI.producer_report(one)
        return (sorted(rep["call_states"]) == want_call
                and sorted(rep["product_states"]) == want_product
                and rep["call_states"]["refused"] == [])
    finally:
        BI.producer_report = saved


def case_history_failure_is_not_completed(mutate):
    """A saved historical failure may not be credited as a completed call, however
    cleanly the local replay went through."""
    sys.path.insert(0, R)
    import branch_inventory as BI
    saved = BI.call_outcome
    if mutate:
        FAULTS['a history failure is not completed'].install()
    try:
        fail = "Traceback (most recent call last)"
        return (BI.call_outcome(False, fail, True, False) == "historically-failed"
                and BI.call_outcome(False, "fine", True, False) == "completed"
                and BI.call_outcome(True, fail, True, False) == "faithfully-failed")
    finally:
        BI.call_outcome = saved


def case_finalization_requires_a_completed_call(mutate):
    """A correct product may not finalize while the call state is not completed."""
    edit = None
    if mutate:
        edit = FAULTS['finalization requires a completed call'].source_edit()
    saved_res = RT.saved_result
    RT.saved_result = lambda line, path=None: "Traceback (most recent call last)"
    try:
        _ns, (_rows, _detail, _text, products) = _classify_audit(edit)
        return bool(products) and all(
            r["product_status"] == "correct" and r["call_outcome"] == "historically-failed"
            and r["finalizable"] is False for r in products.values())
    finally:
        RT.saved_result = saved_res


def case_a_populated_call_state_line_is_not_omitted(mutate):
    """Removing a POPULATED producer line must be caught - the empty-key check alone
    cannot reveal the omission class."""
    sys.path.insert(0, R)
    import branch_inventory as BI
    saved = BI.producer_report
    if mutate:
        FAULTS['a populated call-state line is not omitted'].install()
    try:
        rows = {1: {"product_status": "correct",
                    "call_outcome": "historically-failed", "finalizable": False}}
        rep = BI.producer_report(rows)
        return rep["call_states"]["historically-failed"] == [1]
    finally:
        BI.producer_report = saved


def case_a_missing_pin_is_not_treated_as_correct(mutate):
    """A present product with no pinned identity is `unpinned`, never `correct`."""
    sys.path.insert(0, R)
    import branch_inventory as BI
    saved = BI.product_status
    if mutate:
        FAULTS['a missing pin is not correct'].install()
    try:
        return (BI.product_status(("p", 1, "aa"), None) == "unpinned"
                and BI.product_status(("p", 1, "aa"), ("p", 1, "aa")) == "correct"
                and BI.product_status(None, None) == "missing")
    finally:
        BI.product_status = saved


def case_owner_lists_exclude_producer_rows(mutate):
    """The TOP-LEVEL owner lists must hold only owner rows.

    Driven through the real `main()` into a throwaway root, so the selector itself is
    executed rather than restated: a regression from exact equality to `endswith` shows
    up in the emitted report or nowhere.
    """
    import json as _json
    import shutil
    import tempfile
    src = io.open(os.path.join(R, "branch_inventory.py"), encoding="utf-8").read()
    if mutate:
        src = FAULTS['owner lists exclude producer rows'].patched_source(src)
    ns = {"__name__": "branch_inventory_mutant",
          "__file__": os.path.join(R, "branch_inventory.py")}
    exec(compile(src, "<mutant:branch_inventory>", "exec"), ns)
    stage = tempfile.mkdtemp(prefix="ownerlist_", dir=os.path.join(R, "logs"))
    try:
        os.makedirs(os.path.join(stage, "reports"))
        detail = [(10, "waiting"), (11, "producer-correct/waiting")]
        products = {11: {"product_status": "correct", "call_outcome": "waiting",
                         "finalizable": False}}
        ns["R"] = stage
        ns["OWNERS"] = {"only": ("some/owner.py", 1)}
        ns["branches"] = lambda: []
        ns["classify"] = lambda owner, upto: ({}, detail, "", products)
        with contextlib.redirect_stdout(io.StringIO()):
            ns["main"]()
        got = _json.loads(io.open(os.path.join(stage, "reports",
                                               "branch_inventory.json"),
                                  encoding="utf-8").read())["only"]
        return got["waiting_lines"] == [10] and got["producer_lines"] == [11]
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def case_an_unknown_module_is_not_invented(mutate):
    """The finder serves a sibling that EXISTS; a name nothing provides still raises.

    Without this, a replayed program could quietly run against a module the era never
    had - the opposite failure from not serving imports at all.
    """
    import contextlib
    H = "/tmp/claude-1000/x/scratchpad/" + BENCH
    cmd = ("cd %s" + chr(10) + "python3 - <<'PY'" + chr(10) + "import io" + chr(10) +
           "import a_module_that_never_existed" + chr(10) +
           "io.open('thing.py','w').write('X" + chr(92) + "n')" + chr(10) +
           "PY" + chr(10)) % H
    owner = BENCH + "/thing.py"
    saved = RT._SiblingFinder
    if mutate:
        FAULTS['an unknown module is not invented'].install()
    try:
        raised = None
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                RT.apply_saved_edits("BASE" + chr(10), {1: _rec(cmd)}, owner, side={})
            except Exception as exc:                          # noqa: BLE001
                raised = exc
        return isinstance(raised, ModuleNotFoundError)
    finally:
        RT._SiblingFinder = saved


def case_owner_append_keeps_text(mutate):
    """An owner opened for append must keep what is already there."""
    H = "/tmp/claude-1000/x/scratchpad/" + BENCH
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\n"
           "io.open('thing.py','a').write('TAIL\\n')\nPY\n" % H)
    if mutate:
        FAULTS["owner append keeps its text"].install()
    out, _ = RT.apply_saved_edits("HEAD\n", {1: _rec(cmd)},
                                  BENCH + "/thing.py", side={})
    return out == "HEAD\nTAIL\n"


def case_sibling_append_keeps_text(mutate):
    """A scratch sibling opened for append must keep what is already there."""
    H = "/tmp/claude-1000/x/scratchpad/" + BENCH
    side = {H + "/note.txt": "HEAD\n"}
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\n"
           "io.open('note.txt','a').write('TAIL\\n')\n"
           "io.open('thing.py','w').write(io.open('note.txt').read())\nPY\n" % H)
    if mutate:
        FAULTS["sibling append keeps its text"].install()
    out, _ = RT.apply_saved_edits("BASE\n", {1: _rec(cmd)},
                                  BENCH + "/thing.py", side=side)
    return out == "HEAD\nTAIL\n"


def case_shim_steps_aside(mutate):
    """The shim must be OFF while the replay's own machinery reads.

    The resolver reads a scratch-root path for itself - the same shape `_committed`
    uses. Stepped aside, that read reaches the real filesystem and finds nothing.
    Left installed, the shim answers the replay's own read with its in-memory copy,
    so the replay resolves from itself instead of from history.
    """
    H = "/tmp/claude-1000/x/scratchpad/" + BENCH
    probe = H + "/probe_not_on_disk.txt"
    side = {probe: "SHIM ANSWER\n"}
    seen = {}

    def resolver(path, line):
        if seen.get("busy"):                  # the shim called us from inside our read
            seen["got"] = "SHIM ANSWERED THE REPLAY'S OWN READ"
            return "RE-ENTERED\n"
        seen["busy"] = True
        try:
            seen["got"] = io.open(probe, encoding="utf-8").read()
        except (IOError, OSError):
            seen["got"] = "REAL FILESYSTEM SAYS NO"
        finally:
            seen["busy"] = False
        return "RESOLVED\n"

    cmd = ("cd %s\npython3 - <<'PY'\nimport io\n"
           "t = io.open('%s/sibling.py').read()\n"
           "io.open('%s/thing.py','w').write(t)\nPY\n" % (H, H, H))
    saved = RT.SIBLING_RESOLVER
    RT.SIBLING_RESOLVER = resolver
    if mutate:
        FAULTS["the shim steps aside for its own reads"].install()
    try:
        RT.apply_saved_edits("BASE\n", {1: _rec(cmd)}, BENCH + "/thing.py", side=side)
    except RecursionError:
        seen["got"] = "SHIM FED ITSELF WITHOUT END"
    finally:
        RT.SIBLING_RESOLVER = saved
    return seen.get("got") == "REAL FILESYSTEM SAYS NO"


def case_recovered_digest_refusal(mutate):
    """A recovered body whose bytes do not match its recorded digest is refused."""
    import shutil
    import tempfile
    stage = tempfile.mkdtemp(prefix="digmut_", dir=os.path.join(R, "logs"))
    good = "REAL BODY\n"
    saved_dir = CR._RECOVERED_DIR
    try:
        io.open(os.path.join(stage, "thing.json"), "w",
                encoding="utf-8").write("TAMPERED\n")
        io.open(os.path.join(stage, "RECOVERED.tsv"), "w", encoding="utf-8").write(
            "%s\t.claude/x/thing.json\n"
            % hashlib.sha256(good.encode("utf-8")).hexdigest())
        CR._RECOVERED_DIR = stage
        if mutate:
            FAULTS["a recovered body must match its digest"].install()
        return CR._recovered("/x/.claude/x/thing.json", 10) is None
    finally:
        CR._RECOVERED_DIR = saved_dir
        shutil.rmtree(stage, ignore_errors=True)


def case_resume_agrees_with_past_route(mutate):
    """A resume point is reused only while the wider route still agrees about the past.

    The route below reveals the producer at 8 only once the consumer at 18 is in view,
    so the narrow resume state describes a past the wide route no longer has. The rule
    must therefore DISCARD it and rebuild; the mutant reuses it and loses the 'P'.
    """
    import uuid
    path = "/tmp/claude-1000/s/built_%s.py" % uuid.uuid4().hex[:12]
    wide = {5: "A", 8: "P", 18: "M"}
    expected = "".join(v for _n, v in sorted(wide.items()))

    def route(first, upto):
        steps = {5: "A", 18: "M"} if upto < 15 else wide
        return [(n, _rec("python3 - <<'PY'\nimport io\n"
                         "t = io.open(%r).read()\n"
                         "io.open(%r,'w').write(t + %r)\nPY\n" % (path, path, v)))
                for n, v in sorted(steps.items()) if first <= n <= upto]

    saved = dict((k, getattr(CR, k)) for k in
                 ("route_records", "_disk_get", "_disk_put"))
    # the caches are FENCED, not cleared: emptying them at the end would destroy
    # entries this case never owned (Codex SEQ 1556 item 1)
    with replay_caches.preserved(CR, RT):
        CR.route_records = lambda owner, first, upto: (route(first, upto), None)
        CR._disk_get = lambda p_, n: None
        CR._disk_put = lambda p_, n, text: None
        if mutate:
            FAULTS["resume agrees with the past route"].install()
        try:
            CR._SIBLING_CACHE.clear()
            CR._LAST_RESOLVED.clear()
            CR.sibling_text(path, 10, first=1)        # warm the narrow resume point
            CR._SIBLING_CACHE.clear()                 # it may not answer for the wide
            return CR.sibling_text(path, 20, first=1) == expected
        finally:
            for k, v in saved.items():
                setattr(CR, k, v)

def case_a_missing_product_still_fails_closed(mutate):
    """A producer that returned NO product may never read as correct.

    The neutered product LOOKUP (`the product check is real`) cannot show this: with
    the lookup gone every product is missing, which is what this rule already expects.
    Only the missing branch itself discriminates it.
    """
    if mutate:
        FAULTS["a missing product still fails closed"].install()
    import branch_inventory as _BI
    return (_BI.product_status(None, "pinned") == "missing"
            and _BI.product_status("body", "pinned") == "wrong"
            and _BI.product_status("body", "body") == "correct")



def case_write_mode_still_truncates(mutate):
    """Only append changed: `w` must still replace the owner's text."""
    H = "/tmp/claude-1000/x/scratchpad/" + BENCH
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\n"
           "io.open('thing.py','w').write('REPLACED\\n')\nPY\n" % H)
    if mutate:
        FAULTS["write mode still truncates"].install()
    out, _ = RT.apply_saved_edits("HEAD\n", {1: _rec(cmd)},
                                  BENCH + "/thing.py", side={})
    return out == "REPLACED\n"


def case_sibling_write_mode_still_truncates(mutate):
    """`w` on a scratch sibling must replace, not append."""
    H = "/tmp/claude-1000/x/scratchpad/" + BENCH
    side = {H + "/note.txt": "FIRST\n"}
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\n"
           "io.open('note.txt','w').write('ONLY\\n')\nPY\n" % H)
    if mutate:
        FAULTS["sibling write mode still truncates"].install()
    RT.apply_saved_edits("BASE\n", {1: _rec(cmd)}, BENCH + "/thing.py", side=side)
    return side[H + "/note.txt"] == "ONLY\n"


def case_the_cache_guard_clears_before_refilling(mutate):
    """The fence must CLEAR then refill: refilling alone keeps the run's own additions."""
    import replay_caches as RC
    if mutate:
        FAULTS["the cache guard clears before refilling"].install()
    probe = CR._SIBLING_CACHE
    probe[("keep", 0)] = "ORIGINAL"
    try:
        with RC.preserved(CR, RT):
            probe[("added", 0)] = "SHOULD NOT SURVIVE"
        return probe.get(("keep", 0)) == "ORIGINAL" and ("added", 0) not in probe
    finally:
        probe.pop(("keep", 0), None)
        probe.pop(("added", 0), None)


# ------------------------------------------------ Codex SEQ 1559 cases ---
def _tmp_tsv(lines, name="x.tsv"):
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, name)
    io.open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return p, d


def _aliases():
    """The fault-target modules, populated on first use: a case must not depend on an
    earlier case having installed a fault to fill the table."""
    if not Fault.ALIASES:
        Fault("RT.WORKTREE_COMMIT", lambda saved: saved)._owner()
    return Fault.ALIASES



def case_checkpoint_tuple_binds_cutoff(mutate):
    """Swap two rows' cutoffs, keep the archive: only a bound tuple refuses."""
    import verify_accepted_checkpoints as V
    lines = [l.rstrip("\n") for l in io.open(V.TSV, encoding="utf-8") if l.strip()]
    a = [i for i, l in enumerate(lines) if l.startswith("audit_worker_access.py\t")][0]
    b = [i for i, l in enumerate(lines) if l.startswith("test_harness_guards.py\t23131\t")][0]
    fa, fb = lines[a].split("\t"), lines[b].split("\t")
    fa[1], fb[1] = fb[1], fa[1]
    lines[a], lines[b] = "\t".join(fa), "\t".join(fb)
    p, _ = _tmp_tsv(lines)
    if mutate:
        FAULTS['checkpoint tuple binds cutoff'].install()
    return bool(_aliases()["VAC"].failures(p))


def _signer_copy(mutate_role, fn):
    import hashlib, tempfile, json
    import verify_signer_handoff as V
    pins = V.pinned(); d = tempfile.mkdtemp(); out = []
    for role, e in pins.items():
        src = e["path"] if os.path.isabs(e["path"]) else os.path.join(R, e["path"])
        raw = io.open(src, "rb").read()
        if role == mutate_role:
            raw = fn(raw)
        dst = os.path.join(d, os.path.basename(e["path"]))
        io.open(dst, "wb").write(raw)
        out.append("%s\t%s\t%d\t%s" % (role, dst, len(raw), hashlib.sha256(raw).hexdigest()))
    tsv = os.path.join(d, "SIGNER_HANDOFF.tsv")
    io.open(tsv, "w", encoding="utf-8").write("\t".join(V.COLUMNS) + "\n" + "\n".join(out) + "\n")
    return tsv


def case_signer_prompt_bound_in_full(mutate):
    import json
    def last_byte(raw):
        rows = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
        c = rows[0]["message"]["content"]
        rows[0]["message"]["content"] = c[:-1] + ("X" if c[-1] != "X" else "Y")
        return ("\n".join(json.dumps(r) for r in rows) + "\n").encode()
    tsv = _signer_copy("agent_transcript", last_byte)
    if mutate:
        FAULTS['signer prompt bound in full'].install()
    return any("full PROMPT" in x for x in _aliases()["VSH"].failures(tsv, R))


def case_signer_chain_bound(mutate):
    import json
    def break_chain(raw):
        rows = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
        rows[2]["parentUuid"] = rows[0]["uuid"]
        return ("\n".join(json.dumps(r) for r in rows) + "\n").encode()
    tsv = _signer_copy("agent_transcript", break_chain)
    if mutate:
        FAULTS['signer chain bound'].install()
    return any("parentUuid" in x for x in _aliases()["VSH"].failures(tsv, R))


def case_after_state_after_read(mutate):
    import tempfile
    C = _aliases()["CRU"]
    d = tempfile.mkdtemp(); f = os.path.join(d, "t.bin")
    io.open(f, "wb").write(b"before")
    if mutate:
        FAULTS['after-state measured after open, not after read'].install()
    row = C._AUDIT_PRE(f, "r", 1)
    fh = C._AUDIT_OWN(row, io.open(f, "rb"))
    io.open(f, "wb").write(b"CHANGED")
    fh.read(); fh.close()
    C._close_owned_handles()
    return bool(row.get("drift_under_read_only_open"))


def case_required_null_refused(mutate):
    C = _aliases()["CRU"]
    row = dict((k, "x") for k in C.REQUIRED)
    row.update({"kind": "owner", "before_bytes": 1, "after_bytes": 1,
                "resolved_target": "/n/x", "effective_mode": "r", "owner": None})
    if mutate:
        FAULTS['a null in a required field is accepted'].install()
    return bool(C.row_failures([row], R, C.REQUIRED))


def case_exact_historical_exception(mutate):
    BI = _aliases()["BI"]
    saved = ("Traceback (most recent call last):\n  File \"x\", line 1, in <module>\n"
             "TypeError: the real message")
    if mutate:
        FAULTS['a generic failure keyword stands in for the exact exception'].install()
    return BI.call_outcome(True, saved, True, False,
                           replay_error=("ValueError", "unrelated")) == "refused"


def case_prefix_digest_compared(mutate):
    import hashlib, tempfile
    V = _aliases()["VFI"]
    root = tempfile.mkdtemp()
    t = os.path.join(root, "evidence", "transcript"); os.makedirs(t)
    good = b'{"a":1}\n{"b":2}\n'
    io.open(os.path.join(t, "ACCEPTED.tsv"), "w").write("p.jsonl\t%d\t2\t%s\tnote\n" % (len(good), hashlib.sha256(good).hexdigest()))
    io.open(os.path.join(t, "p.jsonl"), "wb").write(b'{"a":1}\n{"b":3}\n')   # same size, same rows
    g = os.path.join(root, "evidence", "git_bases"); os.makedirs(os.path.join(g, "c"))
    obj = b"x\n"; tree = b"x.py\n"
    io.open(os.path.join(g, "c", "x.py"), "wb").write(obj); io.open(os.path.join(g, "c.tree"), "wb").write(tree)
    io.open(os.path.join(g, "GIT_BASES.tsv"), "w").write("commit\trel\tbytes\tsha256\nc\t<tree>\t%d\t%s\nc\tx.py\t%d\t%s\n" % (len(tree), hashlib.sha256(tree).hexdigest(), len(obj), hashlib.sha256(obj).hexdigest()))
    io.open(os.path.join(root, "in.json"), "wb").write(b"{}")
    io.open(os.path.join(root, "evidence", "RESUME_INPUTS.tsv"), "w").write("path\tbytes\tsha256\tsource\nin.json\t2\t%s\tnote\n" % hashlib.sha256(b"{}").hexdigest())
    if mutate:
        FAULTS['the prefix digest is not compared'].install()
    return any("transcript prefix" in x for x in V.failures(root))


def case_cache_key_binds_inputs(mutate):
    import shutil, tempfile
    d = tempfile.mkdtemp()
    for rel in ("evidence/transcript/ACCEPTED.tsv", "evidence/git_bases/GIT_BASES.tsv"):
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        shutil.copy(os.path.join(R, rel), os.path.join(d, rel))
    saved = (RT.PACKAGE, RT.GIT_BASES)
    if mutate:
        FAULTS['the cache key ignores the input identity'].install()
    try:
        RT.PACKAGE, RT.GIT_BASES = d, os.path.join(d, "evidence", "git_bases")
        if hasattr(CR._code_digest, "value"):
            del CR._code_digest.value
        k1 = CR._code_digest()
        io.open(os.path.join(d, "evidence", "transcript", "ACCEPTED.tsv"), "a").write("changed\n")
        del CR._code_digest.value
        k2 = CR._code_digest()
    finally:
        RT.PACKAGE, RT.GIT_BASES = saved
        if hasattr(CR._code_digest, "value"):
            del CR._code_digest.value
    return k1 != k2


def case_failed_resume_not_clean(mutate):
    RRP = _aliases()["RRP"]
    if mutate:
        FAULTS['a failed resume is clean'].install()
    return RRP.verdict("FileNotFoundError: x", [], [], [], []) is False


# ------------------------------------------ the replay world's edges: cases ---
def _finder_class():
    return RT._SiblingFinder


def case_live_only_import_refused(mutate):
    import tempfile
    root = tempfile.mkdtemp(); io.open(os.path.join(root, "liveonly_m.py"), "w").write("X = 1\n")
    if mutate:
        FAULTS['an import only the live filesystem provides is served'].install()
    f = _finder_class()([root], {}, 1)
    try:
        f.find_spec("liveonly_m")
    except ModuleNotFoundError:
        return True
    return False


def case_outside_is_outside(mutate):
    if mutate:
        FAULTS['a path outside the package counts as inside'].install()
    o = _aliases()["RT"]._outside
    return o("/tmp/claude-1000/x") is True and o(os.path.join(R, "x")) is False


def case_executed_script_argv(mutate):
    if mutate:
        FAULTS['an executed script gets no arguments'].install()
    cmd = ('S=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad\n'
           '/home/faisal/EventMarketDB/venv/bin/python -B "$S/harvest.py" 11 sid wf_x 1 2>&1 | tail -8')
    a = _aliases()["RT"]._executed_script_argv(cmd)
    return bool(a) and a[0][1:] == ["11", "sid", "wf_x", "1"]


def case_bare_name_needs_a_directory(mutate):
    if mutate:
        FAULTS['a bare filename matches the repository root copy'].install()
    c = _aliases()["RT"]._committed("/tmp/x/y/__init__.py", commit="cd961e51d55bf13aa9311b79c5d7eca20e9b11cc")
    return c is None


def case_empty_module_is_present(mutate):
    if mutate:
        FAULTS['an empty module source is absence'].install()
    f = _finder_class()(["/home/faisal/EventMarketDB"], {}, 1)
    try:
        spec = f.find_spec("driver")
    except ModuleNotFoundError:
        return False
    # a REGULAR package: its empty __init__.py is served, so the spec carries a loader;
    # an "absent" __init__ falls to the namespace-package branch, whose loader is None
    return spec is not None and bool(spec.submodule_search_locations) and spec.loader is not None


def case_bare_name_needs_a_bare_owner(mutate):
    if mutate:
        FAULTS['a bare relative name matches any owner of that basename'].install()
    return (CR._names_owner("__init__.py", "pathlib/__init__.py", "__init__.py", None) is False
            and CR._names_owner("harness/x.py", "x.py", "x.py", None) is True)


def case_world_isfile_sees_the_side_table(mutate):
    if mutate:
        FAULTS['a filesystem question about the side table answers from the live box'].install()
    side = {"/tmp/claude-1000/x/scratch/a.txt": "A\n"}
    return RT._world_isfile("/tmp/claude-1000/x/scratch/a.txt", side) is True


def case_semicolon_assignments(mutate):
    if mutate:
        FAULTS['assignments on one line are not shell variables'].install()
    env = RT.shell_vars("SP=/tmp/claude-1000/s; NEW=$SP/step1_128k; OLD=$SP/step1_envelope\n")
    return env.get("NEW") == "/tmp/claude-1000/s/step1_128k"


def case_nested_import_restore(mutate):
    if mutate:
        FAULTS['a nested program evicts an outer import'].install()
    import contextlib, io as _io, sys as _sys, types
    inner = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command":
        "cd /tmp/claude-1000/t2\npython3 - <<'PY'\nimport X, io\nio.open('inner.txt','w').write(str(X.V))\nPY\n"}}]}}
    outer = types.ModuleType("X"); _sys.modules["X"] = outer; RT.SERVED_MODULES.append("X")
    try:
        try:
            with contextlib.redirect_stdout(_io.StringIO()):
                out, _ = RT.machinery(lambda: RT.apply_saved_edits("", {2: inner}, "t2/inner.txt", side={"/tmp/claude-1000/t2/X.py": "V = 2\n"}))()
        except Exception:
            return False
        return out == "2" and _sys.modules.get("X") is outer
    finally:
        _sys.modules.pop("X", None)
        if RT.SERVED_MODULES and RT.SERVED_MODULES[-1] == "X":
            RT.SERVED_MODULES.pop()


def case_dash_c_matching_quote(mutate):
    if mutate:
        FAULTS["a -c program runs to the line's last quote"].install()
    cmd = 'python3 -c "print(1)"; echo "gate: $(run)"; cp /tmp/a /tmp/b\n'
    return [s[2] for s in RT.program_spans(cmd)] == ["print(1)"]


def case_active_owner_cutoff(mutate):
    if mutate:
        FAULTS['the active owner text ignores the cutoff'].install()
    basename = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    path = "/tmp/claude-1000/x/scratchpad/" + basename
    RT.ACTIVE_OWNERS.append((basename, {"text": "LIVE\n", "line": 24277}))
    try:
        return RT.active_owner_text(path, 24278) == "LIVE\n" and RT.active_owner_text(path, 24246) is None
    finally:
        RT.ACTIVE_OWNERS.pop()


def case_seeded_tree(mutate):
    if mutate:
        FAULTS['a seeded tree starts from the bare commit'].install()
    cmd = ("SP=/tmp/claude-1000/s; OLD=$SP/step1_envelope; NEW=$SP/step1_128k\n"
           "git -C $OLD status --porcelain | awk '$1==\"M\"{print $2}' | while read p; do install -D -m 644 \"$OLD/$p\" \"$NEW/$p\"; done\n")
    saved = RT.TREE_MODIFIED
    RT.TREE_MODIFIED = lambda tree, line, with_tracked=False: ({("h/b.py", True)} if with_tracked else {"h/b.py"}) if tree == "/tmp/claude-1000/s/step1_envelope" else set()
    try:
        return RT.seed_copies(cmd, 5) == [("/tmp/claude-1000/s/step1_envelope/h/b.py", "/tmp/claude-1000/s/step1_128k/h/b.py")]
    finally:
        RT.TREE_MODIFIED = saved


def case_append_is_a_write(mutate):
    if mutate:
        FAULTS['an append is not a write'].install()
    R_ = "/tmp/claude-1000/x/scratchpad/bench_1306"
    cmd = "cd %s/.claude/plans\npython3 - <<'PY'\nimport io\nio.open('Drivers/experiments/harness/thing.py','a').write('MORE\\n')\nPY\n" % R_
    return CR._python_writes(RT.program_spans(cmd)[0][2], R_ + "/.claude/plans", "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", {}, "thing.py") is True


def case_record_cwd(mutate):
    if mutate:
        FAULTS['a command without cd stood nowhere'].install()
    import contextlib, io as _io
    R = "/tmp/claude-1000/x/scratchpad/bench_1306"
    cmd = "python3 - <<'PY'\nimport io, os\nio.open('%s/.claude/plans/Drivers/experiments/harness/thing.py','w').write(os.getcwd() + '\\n')\nPY\n" % R
    rec = {"cwd": R, "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("", {1: rec}, "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", side={})
    return out == R + "\n"


def case_reentrant_cutoff(mutate):
    if mutate:
        FAULTS['a re-entrant read ignores its cutoff'].install()
    p = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    saved = CR._INPROGRESS.get(p); CR._INPROGRESS[p] = (24276, "SO FAR\n")
    try:
        return CR._reentrant_text(p, 24278) == "SO FAR\n" and CR._reentrant_text(p, 24246) is None
    finally:
        if saved is None: CR._INPROGRESS.pop(p, None)
        else: CR._INPROGRESS[p] = saved


def case_rejected_call(mutate):
    if mutate:
        FAULTS['a rejected tool call is replayed'].install()
    import contextlib, io as _io
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    bash = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command":
        "cd %s\npython3 - <<'PY'\nimport io\nio.open('thing.py','w').write('INJECTED\\n')\nPY\n" % H}}]}}
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: bash}, "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", side={},
                                      result="<tool_use_error>InputValidationError: []")
    return out == "BASE\n"


def case_dash_c_inside_heredoc(mutate):
    if mutate:
        FAULTS['a -c line inside a heredoc body is a program'].install()
    cmd = "cd /tmp/claude-1000/x\ncat > tool.py <<'CEOF'\npython3 -c \"print('inside')\"\nCEOF\npython3 -c \"print('outside')\"\n"
    return [s[2] for s in RT.program_spans(cmd)] == ["print('outside')"]


def case_own_write_read_back(mutate):
    if mutate:
        FAULTS["a record's own sibling write stays stale"].install()
    import contextlib, io as _io
    H = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    BLM = H + "/build_launch_manifest.py"
    cmd = "cd %s\npython3 - <<'PY'\nimport io\nio.open('%s','w').write('MINE\\n'); s = io.open('%s').read()\nio.open('thing.py','w').write(s)\nPY\n" % (H, BLM, BLM)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {24000: rec}, "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", side={BLM: "an earlier record's copy\n"})
    return out == "MINE\n"


def case_background_outcome(mutate):
    if mutate:
        FAULTS['a background record is judged by its launch notice'].install()
    tid, observed = RT.background_outcome(7097)
    return tid == "b1bxwdxrx" and bool(observed) and "ok  tguards" in observed


def case_dot_dot_path(mutate):
    if mutate:
        FAULTS['a dot-dot path is a different directory'].install()
    import contextlib, io as _io
    X = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments"
    cmd = "cd %s/harness\npython3 - <<'PY'\nimport io, os\nio.open('thing.py','w').write(str(os.path.isdir('%s/harness/../keys')) + '\\n')\nPY\n" % (X, X)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", side={X + "/keys/a.txt": "K\n"})
    return out == "True\n"


def case_import_root_where_program_stood(mutate):
    if mutate:
        FAULTS['an import root is where the command ended'].install()
    import contextlib, io as _io
    A = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    B = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/other"
    side = {A + "/who.py": "WHERE = 'A'\n", B + "/who.py": "WHERE = 'B'\n"}
    cmd = "cd %s\npython3 - <<'PY'\nimport io, who\nio.open('%s/thing.py','w').write(who.WHERE + '\\n')\nPY\ncd %s\n" % (A, B, B)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
    try:
        with contextlib.redirect_stdout(_io.StringIO()):
            out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, "bench_1306/.claude/plans/Drivers/experiments/other/thing.py", side=side)
    except Exception:
        return False                    # a root where the command ended finds no module at all
    return out == "A\n"


def case_import_roots_absolute(mutate):
    if mutate:
        FAULTS['import roots stay relative'].install()
    f = RT._SiblingFinder(["../core"], {}, 1, cwd="/tmp/claude-1000/t/driver/relocation")
    spec = f.find_spec("unit_resolver")
    return spec is not None and spec.loader.path == "/tmp/claude-1000/t/driver/core/unit_resolver.py"


def case_program_cwd(mutate):
    if mutate:
        FAULTS['a program stands in the census directory'].install()
    import contextlib, io as _io
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    cmd = "cd %s\npython3 - <<'PY'\nimport io, os\nio.open('thing.py','w').write(os.getcwd() + '\\n')\nPY\n" % H
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", side={})
    return out == H + "\n"


def case_tree_origin_through_variable(mutate):
    if mutate:
        FAULTS['a tree named through a variable has no origin'].install()
    tree = RT._SCRATCH + "/bench_1306"
    CR._ORIGINS.pop(tree, None)
    got = CR.tree_origin(tree)
    CR._ORIGINS.pop(tree, None)
    return got is not None and got[0] == 22310


def case_glob_through_the_world(mutate):
    if mutate:
        FAULTS['glob walks the live box'].install()
    names = {e.name for e in RT._world_scandir("/tmp/claude-1000/t/driver/core", {})}
    return "unit_resolver.py" in names


def case_namespace_package_served(mutate):
    if mutate:
        FAULTS['a namespace package is not served'].install()
    f = RT._SiblingFinder(["/tmp/claude-1000/t"], {}, 1)
    spec = f.find_spec("driver")
    if spec is None:
        return False
    sub = f.find_spec("driver.relocation", path=spec.submodule_search_locations)
    return sub is not None and sub.loader is None


CASES = [
    ("a pre-loaded bench module answers a replayed import", case_bench_module_hidden),
    ("an unmapped /tmp read is covered", case_unmapped_tmp_refuses),
    ("a schema-invalid attempt is counted as valid", case_invalid_attempt_not_valid),
    ("the raw prefilter misses a JSON-escaped script path", case_raw_prefilter_escaped_script),
    ("a cut-short program always loses its write", case_cut_short_keeps_write),
    ("a stdin program keeps the synthetic argv", case_stdin_argv),
    ("the pre-filter never reads an executed script", case_prefilter_reads_scripts),
    ("a sed after a cd names its file from the record start", case_sed_after_cd),
    ("an in-place sed is not a route", case_sed_in_place_route),
    ("the sed file token keeps its quotes", case_sed_file_token_unquoted),
    ("a join-form write is not a write", case_join_write),
    ("a program's argument is not bound", case_argv_bound),
    ("a replayed program sleeps real time", case_no_real_sleep),
    ("a stat miss on a mount is not recorded", case_stat_miss_recorded),
    ("the seed-tree climb never stops at the root", case_seed_tree_climb_stops),
    ("a lookup is answered by a suffix match", case_exact_path_lookup),
    ("a bare exception class never matches", case_bare_exception_class),
    ("a -c program runs to the line's last quote", case_dash_c_matching_quote),
    ("the active owner text ignores the cutoff", case_active_owner_cutoff),
    ("a seeded tree starts from the bare commit", case_seeded_tree),
    ("an append is not a write", case_append_is_a_write),
    ("a command without cd stood nowhere", case_record_cwd),
    ("a re-entrant read ignores its cutoff", case_reentrant_cutoff),
    ("a rejected tool call is replayed", case_rejected_call),
    ("a -c line inside a heredoc body is a program", case_dash_c_inside_heredoc),
    ("assignments on one line are not shell variables", case_semicolon_assignments),
    ("a nested program evicts an outer import", case_nested_import_restore),
    ("a record's own sibling write stays stale", case_own_write_read_back),
    ("a background record is judged by its launch notice", case_background_outcome),
    ("a dot-dot path is a different directory", case_dot_dot_path),
    ("an import root is where the command ended", case_import_root_where_program_stood),
    ("import roots stay relative", case_import_roots_absolute),
    ("a program stands in the census directory", case_program_cwd),
    ("a tree named through a variable has no origin", case_tree_origin_through_variable),
    ("glob walks the live box", case_glob_through_the_world),
    ("a namespace package is not served", case_namespace_package_served),
    ("a filesystem question about the side table answers from the live box", case_world_isfile_sees_the_side_table),
    ("a bare relative name matches any owner of that basename", case_bare_name_needs_a_bare_owner),
    ("an import only the live filesystem provides is served", case_live_only_import_refused),
    ("a path outside the package counts as inside", case_outside_is_outside),
    ("an executed script gets no arguments", case_executed_script_argv),
    ("a bare filename matches the repository root copy", case_bare_name_needs_a_directory),
    ("an empty module source is absence", case_empty_module_is_present),
    ("checkpoint tuple binds cutoff", case_checkpoint_tuple_binds_cutoff),
    ("signer prompt bound in full", case_signer_prompt_bound_in_full),
    ("signer chain bound", case_signer_chain_bound),
    ("after-state measured after open, not after read", case_after_state_after_read),
    ("a null in a required field is accepted", case_required_null_refused),
    ("a generic failure keyword stands in for the exact exception", case_exact_historical_exception),
    ("the prefix digest is not compared", case_prefix_digest_compared),
    ("the cache key ignores the input identity", case_cache_key_binds_inputs),
    ("a failed resume is clean", case_failed_resume_not_clean),
    ("the cache guard clears before refilling",
     case_the_cache_guard_clears_before_refilling),
    ("sibling write mode still truncates",
     case_sibling_write_mode_still_truncates),
    ("write mode still truncates", case_write_mode_still_truncates),
    ("a missing product still fails closed",
     case_a_missing_product_still_fails_closed),
    ("owner append keeps its text", case_owner_append_keeps_text),
    ("sibling append keeps its text", case_sibling_append_keeps_text),
    ("the shim steps aside for its own reads", case_shim_steps_aside),
    ("a recovered body must match its digest", case_recovered_digest_refusal),
    ("resume agrees with the past route", case_resume_agrees_with_past_route),
    ("wrong tree", case_wrong_tree),
    ("wrong cwd for a relative name", case_wrong_cwd),
    ("sed line insertion", case_sed_insert),
    ("grep-guarded sed is idempotent", case_grep_guarded_sed),
    ("no final newline", case_no_final_newline),
    ("backup and restore is net zero", case_backup_restore),
    ("multi-file saved program", case_multi_file_program),
    ("canonical-path alias cycle", case_alias_cycle),
    ("a file's text is not a path", case_not_a_path),
    ("out-of-range line insert", case_out_of_range_insert),
    ("empty-file line insert", case_empty_file_insert),
    ("per-line substitution", case_per_line_substitution),
    ("guard reads the named file", case_guard_reads_the_named_file),
    ("sed command order", case_sed_command_order),
    (".bak preserved for restore", case_bak_preserved),
    ("shell termination", case_shell_termination),
    ("executed-script closure", case_script_closure),
    ("path built inside the open call", case_inline_concat_write),
    ("git show produces its redirect target", case_git_show_producer),
    ("absolute destination names its tree", case_cross_tree_destination),
    ("binary read yields bytes", case_binary_read),
    ("result found by its tool_use_id", case_result_by_id),
    ("a cd names the tree", case_cwd_names_the_tree),
    ("text inside a program is not a write", case_text_inside_a_program),
    ("only owning processes run", case_only_owning_processes_run),
    ("termination decided first", case_termination_decided_first),
    ("script cached per cutoff", case_script_cache_per_cutoff),
    ("an empty result is present", case_empty_result_is_present),
    ("ledger accounts for every row", case_ledger_accounts_for_every_row),
    ("child audit crosses the boundary", case_child_audit_crosses_the_boundary),
    ("package manifest compares content", case_package_manifest_compares_content),
    ("heredoc opening line continues", case_heredoc_opening_line_continues),
    ("a module import is served", case_module_import_is_served),
    ("an unknown module is not invented", case_an_unknown_module_is_not_invented),
    ("a recovered artefact has an era", case_recovered_artefact_era),
    ("an era-less fallback may not fill a pre-series window",
     case_era_less_fallback_may_not_fill_a_pre_series_window),
    ("a tree sibling is not a producer", case_tree_sibling_is_not_a_producer),
    ("the product check is real", case_the_product_check_is_real),
    ("a wrong product is rejected", case_a_wrong_product_is_rejected),
    ("termination precedes execution", case_termination_precedes_execution),
    ("an absent result is not completed", case_absent_result_is_not_completed),
    ("the two facts do not collapse", case_the_two_facts_do_not_collapse),
    ("the report lists every call state", case_the_report_lists_every_call_state),
    ("a history failure is not completed", case_history_failure_is_not_completed),
    ("finalization requires a completed call",
     case_finalization_requires_a_completed_call),
    ("a populated call-state line is not omitted",
     case_a_populated_call_state_line_is_not_omitted),
    ("owner lists exclude producer rows", case_owner_lists_exclude_producer_rows),
    ("a missing pin is not correct", case_a_missing_pin_is_not_treated_as_correct),
]


def _source_files():
    """Every source file a case could conceivably touch, with its bytes."""
    keep = {}
    for d in (R, os.path.join(R, "ledger")):
        for f in sorted(os.listdir(d)):
            fp = os.path.join(d, f)
            if f.endswith(".py") and os.path.isfile(fp):
                keep[fp] = io.open(fp, "rb").read()
    return keep


def changed_sources(before):
    """-> package sources whose bytes differ from `before`, as relative paths.

    Separated so a control can prove the harness REPORTS a change rather than
    reverting it; the reverting version silently erased a real edit.
    """
    return sorted(os.path.relpath(fp, R) for fp, data in before.items()
                  if not os.path.exists(fp) or io.open(fp, "rb").read() != data)


def main():
    """THE HARNESS NEVER REWRITES PACKAGE SOURCES. It only refuses if they changed.

    The old rule restored the bytes it had captured at start, which silently erased a
    REAL edit made while a run was in flight: a guard added and tested mid-run was
    reverted at exit, and I then reported it as present. Restoring is indistinguishable
    from clobbering, because the harness cannot know whether a difference came from a
    case or from an author. So it reports the difference and fails, and a case that
    needs to mutate a file works on a copy under `logs/` instead.
    """
    before = _source_files()
    status = _run()
    changed = changed_sources(before)
    if changed:
        for rel in changed:
            print("SOURCE CHANGED DURING THE RUN: %s" % rel)
        print("the harness does not rewrite sources; this run's evidence is void")
        return 1
    return status


#: ONE fault-injection owner. A mutation is declared once, as the replacement for a
#: named attribute, and the SAME declaration is applied by this harness and by the
#: exhaustive credit audit. A second patch table is how the audit came to measure a
#: different thing from the harness.
FAULTS = {}
import time as _time_mod
_real_time_sleep = _time_mod.sleep
#: the stale era-less body the fallback fault serves; set by its control
_ERA_LESS_STALE = "STALE\n"


class Fault(object):
    """One declared fault: `module.attribute` replaced by `make(original)`."""

    def __init__(self, target, make, note=""):
        self.module, self.attr = target.split(".", 1)
        self.make = make
        self.note = note

    #: prefix -> module for every mutable owner. This is the ONE place a fault's
    #: target is resolved, and `_snapshot()` derives what to restore from the targets
    #: actually declared in FAULTS, so a new owner cannot be mutated without also
    #: being restored. A test may register an owner here to prove that.
    ALIASES = {}

    def _owner(self):
        if not Fault.ALIASES:
            import branch_inventory
            import freeze_package
            import replay_caches
            import run_resume_path
            import verify_accepted_checkpoints
            import verify_signer_handoff
            import verify_fixed_inputs
            sys.path.insert(0, os.path.join(R, "proofs"))
            import census_rules
            import accepted_evidence_census
            Fault.ALIASES.update({"CR": CR, "RT": RT, "BI": branch_inventory,
                                  "FP": freeze_package, "RRP": run_resume_path,
                                  "RC": replay_caches, "VAC": verify_accepted_checkpoints,
                                  "VSH": verify_signer_handoff, "VFI": verify_fixed_inputs,
                                  "CRU": census_rules, "AEC": accepted_evidence_census})
        if self.module not in Fault.ALIASES:
            raise KeyError("no module registered for fault target prefix %r"
                           % self.module)
        return _aliases()[self.module]

    @contextlib.contextmanager
    def applied(self, active=True):
        CR.DISK_CACHE_WRITES = False        # no disk-cache write under any applied fault
        owner = self._owner()
        saved = getattr(owner, self.attr)
        if active:
            setattr(owner, self.attr, self.make(saved))
        try:
            yield saved
        finally:
            setattr(owner, self.attr, saved)
            CR.DISK_CACHE_WRITES = True          # writes resume once no fault is applied


    def install(self):
        """Apply the fault to the live module and -> the original, for callers that
        already own a save/restore (every case control does)."""
        # no disk-cache write may come from a mutant namespace (chrono_replay.DISK_CACHE_WRITES)
        CR.DISK_CACHE_WRITES = False
        owner = self._owner()
        saved = getattr(owner, self.attr)
        setattr(owner, self.attr, self.make(saved))
        return saved

    def source_edit(self):
        """-> this fault's (anchor, replacement) pair, for a case that hands the edit
        to a helper rather than patching a string itself."""
        return (self.make.anchor, self.make.replacement)

    def patched_source(self, src):
        """-> `src` with this fault's one anchor replaced, for a case that recompiles a
        private copy. The anchor and replacement are the SAME ones the audit applies,
        so the case and the audit can never drift apart."""
        anchor, repl = self.make.anchor, self.make.replacement
        assert src.count(anchor) == 1, "stale mutation anchor: %s" % self.attr
        return src.replace(anchor, repl, 1)


def fault(name, target=None, make=None, note=""):
    """Declare a fault, fetch one already declared, or decorate a `make` function."""
    if target is not None and make is None:
        def deco(fn):
            FAULTS[name] = Fault(target, fn, note)
            return FAULTS[name]
        return deco
    if target is not None:
        FAULTS[name] = Fault(target, make, note)
    return FAULTS[name]


def recompiled(module_path, anchor, replacement, symbol):
    """-> a factory rebuilding ONE symbol from source with exactly one anchor changed.

    A source-level fault is still a declared attribute replacement, so the audit can
    apply it the same way as any other; the anchor is asserted before use.
    """
    def make(_saved):
        src = io.open(module_path, encoding="utf-8").read()
        assert src.count(anchor) == 1, "stale mutation anchor in %s" % module_path
        live = sys.modules[os.path.basename(module_path)[:-3]]
        ns = {"__name__": "mutant_%s" % os.path.basename(module_path)[:-3],
              "__file__": module_path}
        # THE MODULE BODY INSTALLS HOOKS ELSEWHERE AS A SIDE EFFECT (chrono_replay sets
        # RT.SIBLING_RESOLVER, TREE_COMMIT, TREE_MODIFIED, SELECT_UNITS at import), so
        # executing it again pointed those hooks at the mutant namespace and the
        # revert of the ONE targeted attribute left them there. Every attribute of the
        # live modules is put back exactly as it was before the exec.
        lives = {m: dict(vars(m)) for m in (RT, live) if m is not None}
        exec(compile(src.replace(anchor, replacement, 1), "<mutant>", "exec"), ns)
        for m, was in lives.items():
            for k, v in was.items():
                if vars(m).get(k, was) is not v:
                    setattr(m, k, v)
            for k in list(vars(m)):
                if k not in was:
                    delattr(m, k)
        fn = ns[symbol]
        # A GUARDED ENTRY POINT STAYS GUARDED WHEN MUTATED. The replay marks its
        # machinery entry points with `RT.machinery`, whose wrapper reads the guard
        # counter from replay_transcript's globals; rebinding the WRAPPER's code to
        # another module's globals raised NameError inside the mutant. The inner
        # function is what the fault rebuilds; the guard is put back around it.
        guarded = hasattr(fn, "__wrapped__")
        fn = getattr(fn, "__wrapped__", fn)
        # Bind the ONE patched function back to the LIVE module's globals. Executed
        # into its own namespace it also re-created every module-level value, so a
        # control that later set `CR._RECOVERED_DIR` or `RT.SIBLING_RESOLVER` was
        # invisible to it and the mutant quietly ran against the real world.
        rebuilt = types.FunctionType(fn.__code__, live.__dict__, fn.__name__,
                                     fn.__defaults__, fn.__closure__)
        return RT.machinery(rebuilt) if guarded else rebuilt
    make.anchor, make.replacement = anchor, replacement
    return make



# ---------------------------------------------------------------------------
# The declared faults. ONE owner: each case control applies the entry below
# and the exhaustive branch-to-test audit applies the SAME entry, so a case
# and its audit row can never drift apart. Lifted from the case bodies that
# used to own them - not retyped.
# ---------------------------------------------------------------------------

@fault('wrong tree', 'CR._names_owner',
       note="a write destination is judged by its bare filename, so another tree's copy of the same name counts as this owner")
def _m_wrong_tree(saved):
    # the ACTUAL broken rule: a write destination is judged by its bare filename,
    # so another tree's copy of the same name counts as this owner
    return (lambda path, target, name, cwd: path.endswith(name))


@fault('wrong cwd for a relative name', 'RT.cwd_at',
       note='the LAST `cd` of the command wins wherever the write sits, so a relative name resolves into a tree the write never happened in')
def _m_wrong_cwd_for_a_relative_name(saved):
    # the ACTUAL broken rule: the LAST `cd` of the command wins wherever the write
    # sits, so a relative name resolves into a tree the write never happened in
    return (lambda command, pos, start=None: saved(command, len(command), start))


@fault('sed line insertion', 'RT.apply_sed',
       note='a line-addressed insert lands at the end instead of at its own line')
def _m_sed_line_insertion(saved):
    # the ACTUAL broken rule: a line-addressed insert lands at the end instead of
    # at its own line
    return (lambda text, kind, payload: (
        saved(text, kind, payload) if kind == "subst"
        else text + payload[2] + chr(10)))


@fault('grep-guarded sed is idempotent', 'RT.sed_operations',
       note='the guard is dropped, so the insert runs even though the line is already there')
def _m_grep_guarded_sed_is_idempotent(saved):
    # the ACTUAL broken rule: the guard is dropped, so the insert runs even though
    # the line is already there
    return (lambda c: [(o[0], o[1], o[2], o[3], o[4], None)
                                   for o in saved(c)])


@fault('no final newline', 'RT.apply_sed',
       note='an appended line keeps no trailing newline, so the file silently loses its final one')
def _m_no_final_newline(saved):
    # the ACTUAL broken rule: an appended line keeps no trailing newline, so the
    # file silently loses its final one
    return (lambda text, kind, payload: (
        saved(text, kind, payload) if kind == "subst"
        else saved(text, kind, payload).rstrip(chr(10))))


@fault('backup and restore is net zero', 'RT._shell_compose',
       note="the composer ignores the restoring copy, so the experiment's edit is left in place where history put the file back")
def _m_backup_and_restore_is_net_zero(saved):
    # the ACTUAL broken rule: the composer ignores the restoring copy, so the
    # experiment's edit is left in place where history put the file back
    return (lambda rec, basename, side, window=None, line=None: None)


@fault('multi-file saved program', 'CR._py_path_multi',
       note="a loop variable binds to only ONE file, so the program's second target is never recognised as written")
def _m_multi_file_saved_program(saved):
    # the ACTUAL broken rule: a loop variable binds to only ONE file, so the
    # program's second target is never recognised as written
    return (lambda cmd: dict(
        (k, vs[:1]) for k, vs in saved(cmd).items()))


@fault('canonical-path alias cycle', 'CR.canonical_path',
       note='the path is not canonicalised, so two names for one file look like two files')
def _m_canonical_path_alias_cycle(saved):
    # the ACTUAL broken rule: the path is not canonicalised, so two names for one
    # file look like two files
    return (lambda p: p)


@fault("a file's text is not a path", 'CR.looks_like_path',
       note="anything non-empty looks like a path, so a file's whole text is treated as one")
def _m_a_file_s_text_is_not_a_path(saved):
    # the ACTUAL broken rule: anything non-empty looks like a path, so a file's
    # whole text is treated as one
    return (lambda t: bool(t))


@fault('guard reads the named file', 'RT.sed_operations',
       note='the pre-fix behaviour: keep the pattern, forget which file it names')
def _m_guard_reads_the_named_file(saved):
    # the pre-fix behaviour: keep the pattern, forget which file it names
    return (lambda c: [
        (o[0], o[1], o[2], o[3], o[4],
         (o[5][0], "/x/harness/raw_transport.py") if o[5] else None)
        for o in saved(c)])


@fault('sed command order', 'RT.sed_operations',
       note='regroup: substitutions first')
def _m_sed_command_order(saved):
    return (lambda c: sorted(       # regroup: substitutions first
        saved(c), key=lambda o: (o[3] != "subst", o[0])))


@fault('shell termination', 'RT.shell_terminated',
       note='never notice a killed shell')
def _m_shell_termination(saved):
    return (lambda r: False)


@fault('path built inside the open call', 'CR._py_paths',
       note='the base variable is not resolved, so a path built inside the call is invisible while every other form sees the same command')
def _m_path_built_inside_the_open_call(saved):
    # the ACTUAL broken rule: the base variable is not resolved, so a path built
    # inside the call is invisible while every other form sees the same command
    return (lambda c: {})


@fault('git show produces its redirect target', 'RT._GIT_SHOW_REDIRECT',
       note='only an APPEND redirect is treated as a producer, so the plain `>` that created the file is not seen at all')
def _m_git_show_produces_its_redirect_target(saved):
    # the ACTUAL broken rule: only an APPEND redirect is treated as a producer,
    # so the plain `>` that created the file is not seen at all
    return (re.compile(
        r"git\s+show\s+([A-Za-z0-9_./^~-]+):([^\s>|]+)\s*>>\s*\"?([^\"\s]+)"))


@fault('absolute destination names its tree', 'CR._names_owner',
       note='an absolute destination is accepted on its bare filename, so this owner copied INTO another tree counts as a write of it')
def _m_absolute_destination_names_its_tree(saved):
    # the ACTUAL broken rule: an absolute destination is accepted on its bare
    # filename, so this owner copied INTO another tree counts as a write of it
    return (lambda path, target, name, cwd: (
        path.endswith(target) or path.endswith("/" + name)))


@fault('binary read yields bytes', 'RT._reader',
       note='one text reader for every mode')
def _m_binary_read_yields_bytes(saved):
    # the ACTUAL broken rule: one text reader for every mode
    return (lambda text, mode: io.StringIO(text))


@fault('result found by its tool_use_id', 'RT.result_ledger',
       note='the ledger does not reach this record, so the lookup comes back empty exactly as the old proximity window did')
def _m_result_found_by_its_tool_use_id(saved):
    # the ACTUAL broken rule: the ledger does not reach this record, so the lookup
    # comes back empty exactly as the old proximity window did
    return (lambda *a, **k: RT.ResultLedger())


@fault('a cd names the tree', 'RT.cwd_at',
       note='no process knows its directory, so a relative name matches by bare filename in whatever tree is being asked about')
def _m_a_cd_names_the_tree(saved):
    # the ACTUAL broken rule: no process knows its directory, so a relative name
    # matches by bare filename in whatever tree is being asked about
    return (lambda command, pos, start=None: None)


@fault('text inside a program is not a write', 'RT.process_units',
       note='one unit for the whole call, so a name that appears only inside a Python string classifies the surrounding shell')
def _m_text_inside_a_program_is_not_a_write(saved):
    # the ACTUAL broken rule: one unit for the whole call, so a name that appears
    # only inside a Python string classifies the surrounding shell
    return (lambda command, start_dir=None: [(0, len(command), None, "shell", command)])


@fault('only owning processes run', 'RT.SELECT_UNITS',
       note='run every program')
def _m_only_owning_processes_run(saved):
    return (None)


@fault('termination decided first', 'RT.shell_terminated',
       note='the check happens too late to stop the composer')
def _m_termination_decided_first(saved):
    # the ACTUAL broken rule: the check happens too late to stop the composer
    return (lambda result: False)


@fault('an empty result is present', 'RT.result_ledger',
       note='empty text is filtered out, so the completion disappears and the call looks like it never returned')
def _m_an_empty_result_is_present(saved):
    # the ACTUAL broken rule: empty text is filtered out, so the completion
    # disappears and the call looks like it never returned
    L = saved()          # the real ledger, read through the symbol being replaced

    class Blind(object):
        uses, results, corrupt = L.uses, L.results, L.corrupt
        text = {k: v for k, v in L.text.items() if v.strip()}

        def present(self, tid):
            return tid in self.text

        def present_at(self, line):
            for tid, ln in self.uses.items():
                if ln == line:
                    return self.present(tid)
            return False
    return (lambda *a, **k: Blind())


@fault('child audit crosses the boundary', 'RRP._CHILD_AUDIT',
       note="the child is left uninstrumented, so the parent's audit reports nothing at all for it")
def _m_child_audit_crosses_the_boundary(saved):
    # the ACTUAL broken rule: the child is left uninstrumented, so the parent's
    # audit reports nothing at all for it
    return ("pass\n" + "#%s\n")


@fault('heredoc opening line continues', 'RT.program_spans',
       note='the tag must END the opening line, so a heredoc piped or redirected on that line is not seen as a program at all')
def _m_heredoc_opening_line_continues(saved):
    # the ACTUAL broken rule: the tag must END the opening line, so a heredoc
    # piped or redirected on that line is not seen as a program at all
    def narrow(command, env=None):
        out = []
        for m in re.finditer(r"<<'?([A-Za-z0-9_]+)'?\n(.*?)\n\1\s*$",
                             command, re.S | re.M):
            head = command[:m.start()].split("\n")[-1]
            if "python" in head:
                out.append((m.start(), m.end(), m.group(2)))
        return sorted(out)
    return (narrow)


@fault('a module import is served', 'RT._SiblingFinder',
       note='imports are not served, so a program that imports a sibling it could OPEN dies with ModuleNotFoundError')
def _m_a_module_import_is_served(saved):
    # the ACTUAL broken rule: imports are not served, so a program that imports a
    # sibling it could OPEN dies with ModuleNotFoundError
    class Blind(object):
        def __init__(self, *a, **kw):
            pass

        def find_spec(self, name, path=None, target=None):
            return None
    return (Blind)


@fault('an unknown module is not invented', 'RT._SiblingFinder',
       note='any name is served, so the program runs against a module that never existed')
def _m_an_unknown_module_is_not_invented(saved):
    # the ACTUAL broken rule: any name is served, so the program runs against a
    # module that never existed
    import importlib.util

    class Inventing(object):
        def __init__(self, roots, side, line):
            pass

        def find_spec(self, name, path=None, target=None):
            if path is not None or "." in name:
                return None
            return importlib.util.spec_from_loader(
                name, RT._SiblingLoader(name, "", "<invented>"))
    return (Inventing)


@fault('a recovered artefact has an era', 'CR._recovered',
       note='the cutoff is ignored, so the LAST registered body is served at every era')
def _m_a_recovered_artefact_has_an_era(saved):
    # the ACTUAL broken rule: the cutoff is ignored, so the LAST registered body is
    # served at every era
    return (lambda path, line=None: saved(path, 10 ** 9))


@fault('a tree sibling is not a producer', 'CR.is_side_file',
       note="anything under the scratch root counts as a temporary file, so another tree's copy is injected as a producer")
def _m_a_tree_sibling_is_not_a_producer(saved):
    # the ACTUAL broken rule: anything under the scratch root counts as a
    # temporary file, so another tree's copy is injected as a producer
    return (lambda path: True)


# ------------------------------------------------ Codex SEQ 1559 boundaries ---
fault('checkpoint tuple binds cutoff', "VAC.failures",
      recompiled(os.path.join(R, 'verify_accepted_checkpoints.py'),
                 '        for field in ("owner", "cutoff", "bytes"):\n',
                 '        for field in ("owner", "bytes"):\n', 'failures'),
      note='the archive tuple is bound on owner and bytes only, so two rows may swap cutoffs unnoticed')

fault('signer prompt bound in full', "VSH.failures",
      recompiled(os.path.join(R, 'verify_signer_handoff.py'),
                 '    if prompt is not None and user != prompt:\n',
                 '    if prompt is not None and not user.startswith(prompt[:400]):\n', 'failures'),
      note='the prompt is bound by a 400-character prefix, the old preview rule, so a later byte may change')

fault('signer chain bound', "VSH.failures",
      recompiled(os.path.join(R, 'verify_signer_handoff.py'),
                 '        if r.get("parentUuid") != want_parent:\n',
                 '        if False:\n', 'failures'),
      note='the uuid parent chain is never checked, so rows from different conversations pass')

fault('after-state measured after open, not after read', "CRU._AUDIT_OWN",
      recompiled(os.path.join(R, 'proofs', 'census_rules.py'),
                 '    owned = _Owned(fh, row)\n    _OWNED.append(owned)\n    return owned\n',
                 '    _AUDIT_POST(row)\n    return fh\n', '_AUDIT_OWN'),
      note='the after-state is measured as soon as open() returns, so a change during the read is invisible')

fault('a null in a required field is accepted', "CRU.row_failures",
      recompiled(os.path.join(R, 'proofs', 'census_rules.py'),
                 '    incomplete = [r for r in rows if any(k not in r or r.get(k) is None for k in required)]\n',
                 '    incomplete = [r for r in rows if any(k not in r for k in required)]\n', 'row_failures'),
      note='presence is checked but not nullness, so a null owner or digest passes')

fault('a generic failure keyword stands in for the exact exception', "BI.call_outcome",
      recompiled(os.path.join(R, 'branch_inventory.py'),
                 '            exact = any(b == want or b.startswith(want + "\\n") for b in blocks)\n',
                 '            exact = bool(historical_failure)\n', 'call_outcome'),
      note='any saved traceback makes any replay failure faithful, class and message unread')

fault('the prefix digest is not compared', "VFI.failures",
      recompiled(os.path.join(R, 'verify_fixed_inputs.py'),
                 '        if raw_len != int(nbytes) or rows != int(nrows) or _sha(fp) != sha:\n',
                 '        if raw_len != int(nbytes) or rows != int(nrows):\n', 'failures'),
      note='the transcript prefix is verified by size and row count only, never by digest')

fault('the cache key ignores the input identity', "CR._code_digest",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '        for ident in (os.path.join(RT.PACKAGE, "evidence", "transcript", "ACCEPTED.tsv"),\n'
                 '                      os.path.join(RT.GIT_BASES, "GIT_BASES.tsv")):\n'
                 '            h.update(io.open(ident, "rb").read())\n',
                 '        pass\n', '_code_digest'),
      note='the cache key binds the code only, so entries built against other inputs are served')

fault('a failed resume is clean', "RRP.verdict",
      recompiled(os.path.join(R, 'run_resume_path.py'),
                 '    return bool(result == "completed" and not outside and not unmanifested\n',
                 '    return bool(not outside and not unmanifested\n', 'verdict'),
      note='the verdict ignores whether the run completed, so an exception with no bad reads is clean')


# ------------------------------------------ the replay world's edges (SEQ 1559) ---
fault('an import only the live filesystem provides is served', "RT._refuse_live_only",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    IMPORT_MISSES.append((name, root))\n'
                 '    raise ModuleNotFoundError("%s is outside the replay world (%s)" % (name, root))\n',
                 '    IMPORT_MISSES.append((name, root))\n'
                 '    return None\n', '_refuse_live_only'),
      note="a module no durable source provides falls through to Python's finder, which reads the live checkout")

fault('a path outside the package counts as inside', "RT._outside",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    return not sp.startswith(PACKAGE + "/") and not sp.startswith(TOOLING)\n',
                 '    return False\n', '_outside'),
      note='no path is outside the replay world, so the shim serves reads and writes from this box')

fault('an executed script gets no arguments', "RT._executed_script_argv",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '        out.append([m.group(1)] + args)\n',
                 '        out.append([m.group(1)])\n', '_executed_script_argv'),
      note='a saved script runs without the arguments its command gave it')

fault('a bare filename matches the repository root copy', "RT._committed",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '        # carry at least its directory unless the path itself is a bare name.\n        if len(parts) > 1 and i == len(parts) - 1:\n            break\n',
                 '        # carry at least its directory unless the path itself is a bare name.\n        pass\n', '_committed'),
      note='a one-segment suffix of a long path is served from the commit, so a bare __init__.py is the root copy')

fault('an empty module source is absence', "RT._present",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    return text is not None\n',
                 '    return bool(text)\n', '_present'),
      note='a zero-byte package marker reads as a missing module and the whole package is refused')


fault('a bare relative name matches any owner of that basename', "CR._names_owner",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '    return (p == target_path or p.endswith("/" + target_path)\n'
                 '            or (p == name and "/" not in target_path))\n',
                 '    return (p == target_path or p.endswith("/" + target_path) or p == name)\n',
                 '_names_owner'),
      note='a relative write of __init__.py counts as a write of any package marker, so a bogus route is built for a stdlib package')


fault('a filesystem question about the side table answers from the live box', "RT._world_isfile",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    if isinstance(side.get(sp), str):\n        return True\n    mt = _mount_target(sp)\n    if mt is not None:\n        if os.path.isfile(mt):\n            return True\n        # A STAT MISS IS A MISS. The harvest program asked `isfile` before opening,\n        # so an absent state file never reached `_mounted` and was never recorded;\n        # the recovery tool that copies missing mount files had nothing to copy.\n        MOUNT_MISSES.append(sp)\n',
                 '    if os.path.isfile(sp):\n        return True\n    mt = _mount_target(sp)\n    if mt is not None:\n        if os.path.isfile(mt):\n            return True\n        # A STAT MISS IS A MISS. The harvest program asked `isfile` before opening,\n        # so an absent state file never reached `_mounted` and was never recorded;\n        # the recovery tool that copies missing mount files had nothing to copy.\n        MOUNT_MISSES.append(sp)\n', '_world_isfile'),
      note='a file the replay itself wrote is reported absent, so a program that checks before reading refuses')


fault('assignments on one line are not shell variables', "RT.shell_vars",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    for m in re.finditer(r"(?:^|;|&&)\\s*([A-Za-z_][A-Za-z0-9_]*)=(\\"[^\\"]*\\"|\'[^\']*\'|[^\\s;&]+)\\s*(?=;|&&|$)",\n',
                 '    for m in re.finditer(r"^\\s*([A-Za-z_][A-Za-z0-9_]*)=(\\"[^\\"]*\\"|\'[^\']*\'|\\S+)\\s*$",\n', 'shell_vars'),
      note='a `;`-separated assignment is invisible, so a worktree created at "$NEW" has no origin')

fault('a -c program runs to the line\'s last quote', "RT._dash_c_programs",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '            if ch == q:\n                break\n',
                 '            if ch == q and command.find(q, i + 1) < 0:\n                break\n', '_dash_c_programs'),
      note='the program text swallows the shell that follows it on the line and fails to compile')


fault('the active owner text ignores the cutoff', "RT.active_owner_text",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '            if before_line is not None and before_line < state.get("line", 0):\n                return None\n',
                 '            pass\n', 'active_owner_text'),
      note='a nested route asking for an earlier state of the file being replayed is handed its in-flight bytes')


fault('a seeded tree starts from the bare commit', "RT.seed_copies",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    env = shell_vars(command)\n    out = []\n    for m in _FOR_LOOP.finditer(command):\n',
                 '    env = shell_vars(command)\n    out = []\n    return out\n    for m in _FOR_LOOP.finditer(command):\n', 'seed_copies'),
      note='the copy loop that filled a new worktree from another tree is invisible, so the new tree starts from its bare commit')


fault('an append is not a write', "CR._python_writes",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '    for m in re.finditer(r"""(?:io\\.)?open\\(\\s*["\']([^"\'\\n]+)["\']\\s*,\\s*["\'][wax]""",\n',
                 '    for m in re.finditer(r"""(?:io\\.)?open\\(\\s*["\']([^"\'\\n]+)["\']\\s*,\\s*["\']w""",\n', '_python_writes'),
      note='a process that only APPENDS to this owner is not selected, and its append is lost')


fault('a command without cd stood nowhere', "RT._replay",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '        _cds = [(-1, _start)] if _start and os.path.isabs(str(_start)) else []\n',
                 '        _cds = []\n', '_replay'),
      note="the record's working directory is ignored, so a program with no cd has no directory and its relative roots stay relative")


fault('a re-entrant read ignores its cutoff', "CR._reentrant_text",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '    if before_line is None or before_line > pos:\n        return text\n    return None\n',
                 '    return text\n', '_reentrant_text'),
      note='a nested route asking for an earlier state of a file in flight is served the newer bytes so far')


fault('a rejected tool call is replayed', "RT._replay",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '        if isinstance(_res, str) and _res.lstrip().startswith("<tool_use_error>"):\n',
                 '        if False:\n', '_replay'),
      note='a call the harness refused is replayed as if it had run, injecting an edit the real file never received')


fault('a -c line inside a heredoc body is a program', "RT.program_spans",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '        if any(a <= start < b for a, b in bodies):\n            continue\n',
                 '        pass\n', 'program_spans'),
      note='file content written by a heredoc is executed as if the shell had run it, in this record\'s directory')


fault('a nested program evicts an outer import', "RT._replay",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '                    _hidden = dict((_m, sys.modules.pop(_m)) for _m in SERVED_MODULES[:_served_before]\n                                   if _m in sys.modules)\n',
                 '                    _hidden = {}\n', '_replay'),
      note='the inner program pops a name the outer import is still loading, and the outer import dies with KeyError')


fault('a record\'s own sibling write stays stale', "RT._replay",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '                    side.setdefault("__stale__", set()).discard(sp)\n',
                 '                    pass\n', '_replay'),
      note='the stale mark survives the program\'s own write, so its read-back is served by the resolver with the pre-write bytes')


fault('a background record is judged by its launch notice', "RT.background_outcome",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    return tid, ("\\n".join(seen) if seen else None)\n',
                 '    return tid, None\n', 'background_outcome'),
      note='what history observed through the waiter is dropped, so every background program reads as unobserved and its real success or failure never enters the adjudication')


fault('a dot-dot path is a different directory', "RT._replay",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '            return os.path.normpath(sp) if os.path.isabs(sp) else sp\n',
                 '            return sp\n', '_replay'),
      note='the world is asked about `harness/../keys` verbatim; the suffix match never sees a `..`, so the directory reads as absent')


fault('an import root is where the command ended', "RT._own_roots",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    return [here] if here else []\n',
                 '    return []\n', '_own_roots'),
      note="the program's own directory is dropped from the import roots, so a sibling resolves from the owner's directory or a later cd, never from where the program stood")


fault('import roots stay relative', "RT._root_dir",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    return os.path.normpath(os.path.join(cwd, root))\n',
                 '    return root\n', '_root_dir'),
      note="a served module's __file__ is built from '.', and every path derived from it is absolutised against the census's directory")

fault('a program stands in the census directory', "RT._replay",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '            return d if d and not _MACHINERY[0] else _real_getcwd()\n',
                 '            return _real_getcwd()\n', '_replay'),
      note='os.getcwd() inside a replayed program answers with the live process directory, not where the record cd-ed')


fault('a tree named through a variable has no origin', "CR.tree_origin",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '            if key not in line or "worktree add" not in line:\n',
                 '            if tree not in line or "worktree add" not in line:\n', 'tree_origin'),
      note='the pre-filter wants the full path in the saved line, which a `B=$S/bench_1306` command never carries, so the origin reads as unknown')


fault('glob walks the live box', "RT._world_entries",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    return [_WorldEntry(parent, nm, side) for nm in _world_listdir(parent, side)]\n',
                 '    return []\n', '_world_entries'),
      note='a directory iterated through os.scandir reads as empty, so every glob inside a program matches nothing')


fault('a namespace package is not served', "RT._world_isdir",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    return _committed_children(sp) is not None\n',
                 '    return False\n', '_world_isdir'),
      note='a directory the commit carries without a marker reads as absent, so driver.relocation is refused')


fault('the product check is real', "BI.classify",
      recompiled(os.path.join(R, 'branch_inventory.py'),
                 '            now = side.get(product)\n',
                 '            now = None\n', 'classify'),
      note='the product is never looked at, so its presence, bytes and digest are invisible and every producer reads unchanged')


fault('a wrong product is rejected', "BI.product_status",
      recompiled(os.path.join(R, 'branch_inventory.py'),
                 '    return "correct" if now == want else "wrong"',
                 '    return "correct"', 'product_status'),
      note='the pinned identity is never compared, so any present, changed body counts as the required product')


fault('termination precedes execution', "BI.classify",
      recompiled(os.path.join(R, 'branch_inventory.py'),
                 '        if n in producers and RT.shell_terminated(result):',
                 '        if n in producers and False:', 'classify'),
      note='the termination gate is gone, so the producer runs')


@fault('an absent result is not completed', 'BI.call_outcome',
       note='a call that did not raise is completed, whatever history recorded')
def _m_an_absent_result_is_not_completed(saved):
    # the ACTUAL broken rule: a call that did not raise is completed, whatever
    # history recorded
    return (lambda failed, result, present, waiting: (
        "completed" if not failed else saved(failed, result, present, waiting)))


fault('a pre-loaded bench module answers a replayed import', 'RT._replay',
      recompiled(os.path.join(R, 'ledger/replay_transcript.py'),
                 '                    for _m, _mod in list(sys.modules.items()):\n                        _f = getattr(_mod, "__file__", None)\n                        if _f and str(_f).startswith(BENCH_ROOT + os.sep) and _m not in _hidden:\n                            _hidden[_m] = sys.modules.pop(_m)',
                 '                    pass', '_replay'),
      note="the census imports the bench harness owners; a program's `import kf_lint` then finds the real module in sys.modules and its own sibling is never served")


fault('an unmapped /tmp read is covered', 'RRP.classify_read',
      recompiled(os.path.join(R, 'run_resume_path.py'),
                 '    if p.startswith("/tmp"):\n        return "temporary"',
                 '    if p.startswith("/tmp"):\n        return "covered"', 'classify_read'),
      note='a /tmp read outside the projection is called covered, so a real or unmapped temporary tree passes as package-backed')


fault('a schema-invalid attempt is counted as valid', 'AEC.census',
      recompiled(os.path.join(R, 'proofs/accepted_evidence_census.py'),
                 '        if shape:\n            verdict["problems"] = [str(s)[:160] for s in shape[:3]]\n            invalid.append(verdict)\n        else:\n            valid.append(verdict)',
                 '        if shape:\n            verdict["problems"] = [str(s)[:160] for s in shape[:3]]\n            valid.append(verdict)\n        else:\n            valid.append(verdict)', 'census'),
      note="the owner's shape refusal is ignored and the two invalid attempt-1 replies are accepted")


fault('the raw prefilter misses a JSON-escaped script path', 'CR._RUNS_SCRIPT',
      make=lambda saved: re.compile('python3?\\\\?\\s+(?:-B\\\\?\\s+)?[\\"\']?[\\w$/.\\-]+\\.py'),
      note='the raw line stores the quoted script path with a JSON escape before the quote; without it the harvest calls never reached the check')


fault('a cut-short program always loses its write', 'RT._replay',
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '            if env_limited and state["text"] != before and _remainder_names_owner(\n                    failure, progs, os.path.basename(basename)):\n                state["text"] = before',
                 '            if env_limited and state["text"] != before:\n                state["text"] = before', '_replay'),
      note='the restore emptied attempts.json although the unexecuted rest of record 29188 never names it')


fault('a stdin program keeps the synthetic argv', 'RT._replay',
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '                        _real_args = stdin_program_argv(cmd_text, spans[i][0])\n                        if _real_args:\n                            sys.argv = ["-"] + _real_args',
                 '                        pass', '_replay'),
      note="run = sys.argv[1] read the owner's synthetic path; the siblings written under it were lost")


fault('the pre-filter never reads an executed script', 'CR.writes_this',
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '        if not _spelled.search(command) and not any(\n                t and _spelled.search(t) for t in _executed_script_texts(command, None)):',
                 '        if not _spelled.search(command):', 'writes_this'),
      note='python "$S/harvest.py" never spells attempts.json; the 35 harvest rewrites were not the accumulator\'s records')


fault('a sed after a cd names its file from the record start', "CR._shell_writes",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '        if _names_owner(_expand(path, env), target_path, name,\n                        RT.cwd_at(text, _pos, cwd) or cwd):\n            return True',
                 '        if _names_owner(_expand(path, env), target_path, name, cwd):\n            return True', '_shell_writes'),
      note="`cd $TREE/... && sed -i '...' harness/x.py` resolved harness/x.py against the record's start directory, never the tree the shell stood in")


fault('an in-place sed is not a route', "CR._shell_writes",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '        if _names_owner(_expand(path, env), target_path, name,\n                        RT.cwd_at(text, _pos, cwd) or cwd):\n            return True\n    for src in _executed_script_texts(text, line):',
                 '        pass\n    for src in _executed_script_texts(text, line):', '_shell_writes'),
      note="sed -i on the owner is not the owner's record: the harvest program stayed on run directory 2")


fault("the sed file token keeps its quotes", "RT.sed_operations",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '        ops.append((m.start(), m.group(10).strip("\'\\""), m.group(4), "subst",',
                 '        ops.append((m.start(), m.group(10), m.group(4), "subst",', 'sed_operations'),
      note='a quoted file token expands to a path ending in a quote and matches no owner, so the routed edit is skipped')


fault('a join-form write is not a write', "CR._python_writes",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '            if _names_owner(os.path.join(base, *parts), target_path, name, cwd):\n                return True',
                 '            pass', '_python_writes'),
      note="open(os.path.join(NAME, 'file'), 'w') is invisible: every run directory's attempts.json had no route")


fault("a program's argument is not bound", "CR._python_writes",
      recompiled(os.path.join(R, 'ledger', 'chrono_replay.py'),
                 '        if argv and 0 < k <= len(argv):\n            bound[m.group(1)] = argv[k - 1]',
                 '        pass', '_python_writes'),
      note="run = sys.argv[1] binds nothing, so the run directory the shell passed never names the file")


fault('a replayed program sleeps real time', "RT.w_sleep",
      make=lambda saved: (lambda seconds: _real_time_sleep(seconds)),
      note="the harvest program's 360 x time.sleep(10) poll of an absent state file cost an hour per record")


fault('a stat miss on a mount is not recorded', "RT._world_isfile",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '        MOUNT_MISSES.append(sp)\n    try:\n        return _committed(sp) is not None',
                 '        pass\n    try:\n        return _committed(sp) is not None', '_world_isfile'),
      note="an absent mounted file asked through isfile never reaches _mounted, so the recovery tool sees no miss")


fault('the seed-tree climb never stops at the root', "RT._seed_tree",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    while tree and tree != "/" and not (os.path.basename(tree).startswith("step1_")',
                 '    while tree and not (os.path.basename(tree).startswith("step1_")', '_seed_tree'),
      note="dirname('/') is '/' again: a copy source outside every seeded tree climbs for ever (ledger recoveries 11 and 14)")


fault('a lookup is answered by a suffix match', "RT._resolve_source",
      recompiled(os.path.join(R, 'ledger', 'replay_transcript.py'),
                 '    # interpreter had skipped the missing directory and found the next root.\n',
                 '    # interpreter had skipped the missing directory and found the next root.\n'
                 '    parts = str(src).strip("/").split("/")\n'
                 '    tail = "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]\n'
                 '    for store in ([bodies] if bodies else []) + [side]:\n'
                 '        for k, v in store.items():\n'
                 '            if isinstance(k, str) and k.endswith("/" + tail) and isinstance(v, str):\n'
                 '                return v\n', '_resolve_source'),
      note="a path the world does not hold is answered by any held file sharing its last two components; record 22655's module was served under the wrong name")


fault('a bare exception class never matches', "BI.call_outcome",
      recompiled(os.path.join(R, 'branch_inventory.py'),
                 '            want = "%s: %s" % (cls, msg) if msg else cls',
                 '            want = "%s: %s" % (cls, msg)', 'call_outcome'),
      note="a saved traceback ending in a bare `AssertionError` is asked for `AssertionError: ` and the identical failure is ruled refused")


fault('the two facts do not collapse', "BI.classify",
      recompiled(os.path.join(R, 'branch_inventory.py'),
                 '            kind = "producer-%s/%s" % (pstatus, outcome)',
                 '            outcome = pstatus if pstatus != "correct" else outcome\n            kind = "producer-%s/%s" % (pstatus, outcome)', 'classify'),
      note="the product status overwrites the call outcome, which is exactly how `producer-wrong-product-partial` lost the call's real state")


@fault('the report lists every call state', 'BI.producer_report',
       note='only the states that happen to occur are listed, so a refused, waiting or terminated producer would simply be absent')
def _m_the_report_lists_every_call_state(saved):
    # the ACTUAL broken rule: only the states that happen to occur are listed, so a
    # refused, waiting or terminated producer would simply be absent
    def thin(products):
        out = {"product_states": {}, "call_states": {}, "finalizable": []}
        for line in sorted(products):
            row = products[line]
            out["product_states"].setdefault(row["product_status"], []).append(line)
            out["call_states"].setdefault(row["call_outcome"], []).append(line)
        return out
    return (thin)


@fault('a history failure is not completed', 'BI.call_outcome',
       note='a replay that did not raise is completed, and the saved result is never consulted')
def _m_a_history_failure_is_not_completed(saved):
    # the ACTUAL broken rule: a replay that did not raise is completed, and the
    # saved result is never consulted
    return (lambda failed, result, present, waiting: (
        "completed" if (present and not failed)
        else saved(failed, result, present, waiting)))


fault('finalization requires a completed call', "BI.classify",
      recompiled(os.path.join(R, 'branch_inventory.py'),
                 '                ("finalizable", pstatus == "correct" and outcome == "completed")])',
                 '                ("finalizable", pstatus == "correct")])', 'classify'),
      note='finalization looks only at the product')


@fault('a populated call-state line is not omitted', 'BI.producer_report',
       note='a populated state is dropped from the listing')
def _m_a_populated_call_state_line_is_not_omitted(saved):
    # the ACTUAL broken rule: a populated state is dropped from the listing
    def drop(products):
        rep = saved(products)
        rep["call_states"]["historically-failed"] = []
        return rep
    return (drop)


fault('owner lists exclude producer rows', "BI.main",
      recompiled(os.path.join(R, 'branch_inventory.py'),
                 '("waiting_lines", [n for n, k in detail if k == "waiting"]),',
                 '("waiting_lines", [n for n, k in detail if k.endswith("waiting")]),', 'main'),
      note='suffix matching, which pulls `producer-.../waiting` into the owner list')


@fault('a missing pin is not correct', 'BI.product_status',
       note='no pin means nothing to fail, so it passes')
def _m_a_missing_pin_is_not_correct(saved):
    # the ACTUAL broken rule: no pin means nothing to fail, so it passes
    return (lambda now, want: (
        "missing" if now is None else "correct"))

# --- the remaining nine, declared here for the same two consumers -------------
# Five sed rules share ONE fault: the pre-fix `apply_sed`, which substituted over the
# whole file and clamped a line address instead of running no cycle at all.
for _n in ("out-of-range line insert", "empty-file line insert",
           "per-line substitution"):
    fault(_n, "RT.apply_sed", lambda saved: _broken_apply_sed,
          note="whole-file substitution and a clamped line address")



@fault(".bak preserved for restore", "RT.sed_operations",
       note="the backup suffix is forgotten, so the pre-edit bytes are never kept")
def _m_bak_preserved_for_restore(saved):
    return lambda c: [(o[0], o[1], None, o[3], o[4], o[5]) for o in saved(c)]


@fault("executed-script closure", "CR._executed_script_texts",
       note="the replay stops looking through executed scripts, so a write made by a "
            "script the command RUNS is credited to nobody")
def _m_executed_script_closure(saved):
    return lambda c, before_line=None: []


@fault("package manifest compares content", "FP.entries",
       note="the manifest records only the path, on BOTH sides, so a file whose "
            "bytes changed still verifies")
def _m_package_manifest_compares_content(saved):
    return lambda: [(k, p_, "") for k, p_, _v in saved()]


def _ledger_fault(saved):
    """The ledger MEMOISES. Installed after any clean read, the mutant would never
    parse a row and the control would pass against a cached answer."""
    RT._LEDGERS.clear()
    return _ledger_recompiled(saved)


_ledger_recompiled = recompiled(
    os.path.join(R, "ledger", "replay_transcript.py"),
                 "        try:\n            rec = json.loads(row, strict=False)\n"
                 "        except ValueError:\n            L.corrupt.append(i)\n"
                 "            continue\n"
                 "        if '\"tool_use\"' not in row and '\"tool_result\"' not in row:\n"
                 "            continue",
                 "        if '\"tool_use\"' not in row and '\"tool_result\"' not in row:\n"
                 "            continue\n"
                 "        try:\n            rec = json.loads(row, strict=False)\n"
                 "        except ValueError:\n            L.corrupt.append(i)\n"
                 "            continue",
                 "result_ledger")

fault("ledger accounts for every row", "RT.result_ledger", _ledger_fault,
      note="only rows mentioning a tool block are parsed, so a truncated row is "
           "never seen and never counted")

fault("script cached per cutoff", "CR._executed_script_texts",
      recompiled(os.path.join(R, "ledger", "chrono_replay.py"),
                 "        _SCRIPT_CACHE[(path, upto)] = text",
                 "        _SCRIPT_CACHE[(path, upto)] = text\n"
                 "        _SCRIPT_CACHE[(path, upto + 20)] = text",
                 "_executed_script_texts"),
      note="a script's text is reused across cutoffs, so the answer at one line is "
           "served at another")


# --- the five rules this round added or restored ------------------------------
fault("owner append keeps its text", "RT._replay",
      recompiled(os.path.join(R, "ledger", "replay_transcript.py"),
                 '                if "a" in _m:\n'
                 '                    return _Sink(lambda v: state.__setitem__("text", v), state["text"])',
                 '                if "a" in _m:\n'
                 '                    return _reader(state["text"], _m)',
                 "_replay"),
      note="THE ORIGINAL DEFECT: an owner opened for append is handed a READER, so "
           "everything it appends is discarded")

fault("sibling append keeps its text", "RT._replay",
      recompiled(os.path.join(R, "ledger", "replay_transcript.py"),
                 '                    keep = side.get(sp, "") if "a" in _extra or "a" in mode else ""',
                 '                    keep = ""',
                 "_replay"),
      note="THE ORIGINAL DEFECT: a scratch sibling opened for append starts from "
           "empty, so it overwrites what was already there")

fault("the shim steps aside for its own reads", "RT._replay",
      recompiled(os.path.join(R, "ledger", "replay_transcript.py"),
                 "                io.open, builtins.open = _REAL_IO_OPEN, _REAL_BUILTIN_OPEN",
                 "                pass",
                 "_replay"),
      note="the shim is left installed while the replay reads for itself, so its own "
           "reads come straight back into the shim")

fault("a recovered body must match its digest", "CR._recovered",
      recompiled(os.path.join(R, "ledger", "chrono_replay.py"),
                 '    if hashlib.sha256(text.encode("utf-8")).hexdigest() != best[1]:',
                 "    if False:",
                 "_recovered"),
      note="the recorded digest is never compared, so a recovered body that does not "
           "match it is served anyway")

fault("resume agrees with the past route", "CR.sibling_text",
      recompiled(os.path.join(R, "ledger", "chrono_replay.py"),
                 "            and {n for n, _r in recs if n < last[0]} == last[3]):",
                 "            and True):",
                 "sibling_text"),
      note="the resume point is reused whatever the wider route says about the past, "
           "so a changed history is silently ignored")


@fault("an era-less fallback may not fill a pre-series window", "CR._recovered",
       note="an era-less body is allowed to answer for a path that HAS a timed "
            "series, so it fills the window before the first era")
def _m_era_less_fallback(saved):
    stale = _ERA_LESS_STALE

    def loose(path, line=None):
        return saved(path, line) if line is None or line > 500 else stale
    return loose


fault("a missing product still fails closed", "BI.product_status",
      recompiled(os.path.join(R, "branch_inventory.py"),
                 '    if now is None:\n        return "missing"',
                 '    if now is None:\n        return "correct"',
                 "product_status"),
      note="a producer that returned NO product is read as if it had produced the "
           "right one, so a call with nothing behind it becomes finalizable")


fault("write mode still truncates", "RT._replay",
      recompiled(os.path.join(R, "ledger", "replay_transcript.py"),
                 '                if "w" in _m:\n'
                 '                    return _Sink(lambda v: state.__setitem__("text", v))',
                 '                if "w" in _m:\n'
                 '                    return _Sink(lambda v: state.__setitem__("text", v),\n'
                 '                                 state["text"])',
                 "_replay"),
      note="correcting append also seeded the WRITE sink, so `w` would append instead "
           "of replacing - the regression the append fix could have caused")


fault("sibling write mode still truncates", "RT._replay",
      recompiled(os.path.join(R, "ledger", "replay_transcript.py"),
                 '                    keep = side.get(sp, "") if "a" in _extra or "a" in mode else ""',
                 '                    keep = side.get(sp, "")',
                 "_replay"),
      note="the side-file half of the same boundary: `w` on a scratch sibling would "
           "append instead of replacing")



@fault("the cache guard clears before refilling", "RC.preserved",
       note="restoring by refilling WITHOUT clearing leaves everything the fenced run "
            "added, so the next run inherits state the fence was built to contain")
def _m_cache_guard_clears(saved):
    """`preserved` is a @contextmanager, so its module globals may NOT be rebound the
    way a plain function's are: the decorated object is contextlib's own wrapper and
    rebinding its code breaks contextlib itself. The mutant keeps its own namespace."""
    path = os.path.join(R, "replay_caches.py")
    src = io.open(path, encoding="utf-8").read()
    anchor = "            obj.clear()\n"
    assert src.count(anchor) == 1, "stale mutation anchor in %s" % path
    ns = {"__name__": "mutant_replay_caches", "__file__": path}
    exec(compile(src.replace(anchor, "", 1), "<mutant:replay_caches>", "exec"), ns)
    return ns["preserved"]


def _outcome(run, catching):
    """-> what `run()` produced, or a marker naming the exact exception it raised.

    A mutant whose intended effect is a failure must still be judged by the SAME
    predicate and the same literal expected answer as its control. Letting the
    exception escape made the harness call it a kill without ever comparing anything,
    and an unrelated crash got the same credit. Only the named exception is turned into
    an outcome; anything else escapes and is reported as a harness error.
    """
    try:
        return run()
    except catching as exc:                                    # noqa: BLE001
        return ("RAISED", type(exc).__name__)


def _snapshot():
    """Every module attribute a case could swap, so nothing leaks into the next case.

    Restoring only the source files and one name was not enough: a case that replaced
    `CR._recovered` and restored only `_RECOVERED_DIR` left the mutated callable in
    place for every case after it.
    """
    sys.path.insert(0, R)
    # DERIVED FROM THE REGISTRY, not listed. A module that can be MUTATED must be a
    # module that gets RESTORED, so the set to restore is exactly the set of owners
    # the declared faults name. A hand list is how `replay_caches` came to be mutable
    # but unrestored: its mutant stayed installed for every later case and the
    # replay's list registers grew until the runner died.
    mods = []
    for f in FAULTS.values():
        owner = f._owner()
        if owner not in mods:
            mods.append(owner)
    return [(m, dict(vars(m))) for m in mods]


def _restore(shot):
    for module, before in shot:
        now = vars(module)
        for key, value in before.items():
            if now.get(key, _MISSING) is not value:
                setattr(module, key, value)
        for key in [k for k in list(now) if k not in before]:
            delattr(module, key)
    CR.DISK_CACHE_WRITES = True



_MISSING = object()


def _call(fn, mutate):
    """-> (value, error). An uncaught exception is a HARNESS ERROR, never a kill.

    Catching everything and calling it `mutant = False` credited a NameError, a stale
    anchor and any unrelated crash as a killed behavioural mutation.
    """
    try:
        # EVERY run is fenced. A shallow module snapshot cannot undo a cleared cache,
        # so without this a case that empties `_SIBLING_CACHE` or `_LEDGERS` leaves the
        # next case measuring against state it destroyed.
        with replay_caches.preserved(CR, RT):
            return fn(mutate), None
    except Exception as exc:                                   # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, str(exc)[:160])


def _run():
    # WARM THE LEDGER BEFORE THE FIRST FENCE. The fence restores each cache to what it
    # held before a case ran, so an empty `_LEDGERS` means every case that needs the
    # ledger re-parses the frozen prefix - a 1.3 GB peak each time, which exhausted
    # memory and killed the runner outright. Parsed once here, it is part of every
    # fence's "before" snapshot, so it survives each restore while a MUTANT ledger
    # built inside a fence is still discarded. Isolation is unchanged; the cost is not.
    RT.result_ledger()
    rows, survived, errors = [], 0, 0
    for name, fn in CASES:
        shot = _snapshot()
        control, control_err = _call(fn, False)
        _restore(shot)
        shot = _snapshot()
        mutant, mutant_err = _call(fn, True)
        _restore(shot)
        error = control_err or mutant_err
        killed = bool(control) and mutant is False and error is None
        if error is not None:
            errors += 1
            survived += 1
        elif not killed:
            survived += 1
        rows.append(collections.OrderedDict([
            ("case", name), ("positive_control", bool(control)),
            ("mutant_detected", mutant is False), ("killed", killed),
            ("error", error)]))
        print("%-44s control=%-5s mutant_caught=%-5s %s" % (
            name, control, mutant is False,
            "ERROR %s" % error if error else ("KILLED" if killed else "SURVIVED")))
    print("%d harness errors" % errors)
    print("%d of %d mutations killed; %d survived" % (
        len(rows) - survived, len(rows), survived))
    errors = [r["case"] for r in rows if r["error"]]
    if errors:
        print("HARNESS ERRORS: %s" % errors)
    io.open(os.path.join(R, "reports", "mutations.json"), "w",
            encoding="utf-8").write(json.dumps(collections.OrderedDict([
                ("total", len(rows)), ("killed", len(rows) - survived),
                ("survived", survived), ("cases", rows)]), indent=2) + "\n")
    return 1 if survived else 0


if __name__ == "__main__":
    raise SystemExit(main())
