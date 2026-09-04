"""The replay world's edges (Codex SEQ 1559 item 1): nothing outside the package is read
for real - not by open, not by import - and what durable sources provide is served."""
import os
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "ledger"))
import replay_transcript as RT                                 # noqa: E402


def test_outside_means_not_inside_the_package_and_not_tooling():
    assert RT._outside("/tmp/claude-1000/x") is True
    assert RT._outside("/home/faisal/EventMarketDB/driver/core/x.py") is True
    assert RT._outside(os.path.join(RT.PACKAGE, "evidence", "x")) is False
    assert RT._outside(os.path.join(sys.prefix, "lib", "x.py")) is False
    # a relative name with no known working directory belonged to a vanished tree
    assert RT._outside("relative/name") is True


def test_an_import_only_the_live_filesystem_provides_is_refused(tmp_path):
    """A module under an OUTSIDE root that exists on disk but that no durable source
    serves must raise, never be read from the box."""
    root = tmp_path / "live_only"; root.mkdir()
    (root / "liveonly_mod.py").write_text("X = 1\n")
    finder = RT._SiblingFinder([str(root)], {}, 1)
    import pytest
    with pytest.raises(ModuleNotFoundError):
        finder.find_spec("liveonly_mod")


def test_an_import_the_side_table_provides_is_served(tmp_path):
    root = str(tmp_path / "scratch")
    side = {os.path.join(root, "served_mod.py"): "VALUE = 42\n"}
    finder = RT._SiblingFinder([root], side, 1)
    spec = finder.find_spec("served_mod")
    assert spec is not None
    import importlib.util
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.VALUE == 42


def test_a_package_import_the_mount_provides_is_served(tmp_path):
    """A mounted tree serves `pkg/__init__.py` as a package with a search path."""
    hist = "/tmp/claude-1000/x-historical-tree"
    dest = tmp_path / "mounted"; (dest / "mpkg").mkdir(parents=True)
    (dest / "mpkg" / "__init__.py").write_text("NAME = 'mounted'\n")
    saved = dict(RT.MOUNTS)
    RT.MOUNTS[hist] = str(dest)
    try:
        finder = RT._SiblingFinder([hist], {}, 1)
        spec = finder.find_spec("mpkg")
        assert spec is not None and spec.submodule_search_locations
    finally:
        RT.MOUNTS.clear(); RT.MOUNTS.update(saved)


def test_executed_scripts_receive_their_own_arguments():
    cmd = ('S=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad\n'
           'PYTHONDONTWRITEBYTECODE=1 /home/faisal/EventMarketDB/venv/bin/python -B "$S/harvest.py" '
           '11 0000940944-26-000005 wf_76911211-8a4 1 2>&1 | tail -8')
    argv = RT._executed_script_argv(cmd)
    assert argv and argv[0][1:] == ["11", "0000940944-26-000005", "wf_76911211-8a4", "1"]
    assert argv[0][0].endswith("/scratchpad/harvest.py")


def test_a_mount_serves_its_copy_and_records_what_it_lacks(tmp_path):
    """A mounted historical root serves the package copy; a path it lacks is None AND
    recorded, so the recovery tool copies exactly what a run asked for."""
    hist = "/tmp/claude-1000/x-mount-root"
    dest = tmp_path / "copy"; dest.mkdir()
    (dest / "present.json").write_text('{"ok": true}')
    saved = dict(RT.MOUNTS); before = len(RT.MOUNT_MISSES)
    RT.MOUNTS[hist] = str(dest)
    try:
        assert RT._mounted(hist + "/present.json") == '{"ok": true}'
        assert RT._mounted(hist + "/absent.json") is None
        assert RT.MOUNT_MISSES[before:] == [hist + "/absent.json"]
    finally:
        RT.MOUNTS.clear(); RT.MOUNTS.update(saved)
        del RT.MOUNT_MISSES[before:]


def test_a_repo_package_import_is_served_from_the_git_store_not_the_checkout():
    """`driver` and `driver.core` resolve through the store at the worktree commit when
    the program's sys.path names the live checkout - the checkout itself is never read."""
    import importlib.util
    finder = RT._SiblingFinder(["/home/faisal/EventMarketDB"], {}, 1)
    spec = finder.find_spec("driver")
    assert spec is not None and spec.submodule_search_locations
    assert spec.loader is not None                  # an "absent" empty __init__ leaves a namespace package
    assert spec.loader.path.startswith("/home/faisal/EventMarketDB/driver/")
    sub = finder.find_spec("driver.core", path=spec.submodule_search_locations)
    assert sub is not None and sub.submodule_search_locations
    leaf = finder.find_spec("driver.core.prepared_fact_v2", path=sub.submodule_search_locations)
    assert leaf is not None and leaf.loader.source.startswith(("#", '"""', "import", "from"))


def test_the_store_serves_an_empty_committed_file_as_present():
    """A zero-byte package marker is a file: "" from the store, never None."""
    full = "cd961e51d55bf13aa9311b79c5d7eca20e9b11cc"
    assert RT._committed("/home/faisal/EventMarketDB/driver/__init__.py", commit=full) == ""
    assert RT._committed("/home/faisal/EventMarketDB/driver/no_such_module_xyz.py", commit=full) is None
    # a bare generic name over a LONG path must never match the repository root's copy:
    # the suffix must carry its directory (the mutation that drops this rule is named
    # `a bare filename matches the repository root copy`)
    assert RT._committed("/tmp/x/y/__init__.py", commit=full) is None


def test_a_bare_relative_name_never_matches_a_package_marker_of_another_package():
    """`__init__.py` written in some directory is not `pathlib/__init__.py`."""
    import chrono_replay as CR
    assert CR._names_owner("__init__.py", "pathlib/__init__.py", "__init__.py", None) is False
    assert CR._names_owner("harness/x.py", "x.py", "x.py", None) is True
    assert CR._names_owner("pathlib/__init__.py", "pathlib/__init__.py", "__init__.py", None) is True


def test_stdlib_names_are_not_served_from_the_synthetic_replay_root():
    finder = RT._SiblingFinder([None, "/replay"], {}, 22345)
    for name in ("pathlib", "datetime", "json"):
        assert finder.find_spec(name) is None, name


def test_the_owner_match_is_segment_aligned_not_character_aligned():
    """`agent.py` is not `nt.py`; a suffix matches only at a path boundary."""
    import chrono_replay as CR
    assert CR._names_owner("agent.py", "nt.py", "nt.py", None) is False
    assert CR._names_owner("/tmp/x/experiment.py", "nt.py", "nt.py", None) is False
    assert CR._names_owner("/tmp/x/nt.py", "nt.py", "nt.py", None) is True
    assert CR._names_owner("/tmp/x/harness/raw_transport.py", "harness/raw_transport.py",
                           "raw_transport.py", None) is True


def test_filesystem_questions_are_answered_by_the_world_for_outside_paths(tmp_path):
    """isfile/isdir/listdir over the side table, a mount and the committed store."""
    side = {"/tmp/claude-1000/x/scratch/a.txt": "A\n", "/tmp/claude-1000/x/scratch/sub/b.txt": "B\n"}
    assert RT._world_isfile("/tmp/claude-1000/x/scratch/a.txt", side) is True
    assert RT._world_isfile("/tmp/claude-1000/x/scratch/nope.txt", side) is False
    assert RT._world_isdir("/tmp/claude-1000/x/scratch", side) is True
    assert RT._world_isdir("/tmp/claude-1000/x/scratch/sub", side) is True
    assert RT._world_listdir("/tmp/claude-1000/x/scratch", side) == ["a.txt", "sub"]
    # the committed store answers for the repository's own tree
    assert RT._world_isfile("/tmp/claude-1000/t/driver/core/unit_resolver.py", {}) is True
    assert RT._world_isdir("/tmp/claude-1000/t/driver/core", {}) is True
    assert "unit_resolver.py" in RT._world_listdir("/tmp/claude-1000/t/driver/core", {})
    assert RT._world_isfile("/tmp/claude-1000/t/.claude/skills/earnings-orchestrator/scripts/guidance_ids.py", {}) is True
    # a mount answers for the copied durable files
    dest = tmp_path / "m"; dest.mkdir(); (dest / "wf.json").write_text("{}")
    saved = dict(RT.MOUNTS); RT.MOUNTS["/tmp/claude-1000/hist-root"] = str(dest)
    try:
        assert RT._world_isfile("/tmp/claude-1000/hist-root/wf.json", {}) is True
        assert RT._world_listdir("/tmp/claude-1000/hist-root", {}) == ["wf.json"]
    finally:
        RT.MOUNTS.clear(); RT.MOUNTS.update(saved)
    import pytest
    with pytest.raises(FileNotFoundError):
        RT._world_listdir("/tmp/claude-1000/nowhere/at/all", {})


def test_glob_walks_directories_through_the_world():
    """`glob` iterates a directory with `os.scandir`; the world answers it for the side
    table and the committed tree, and `is_dir` distinguishes the two kinds of entry."""
    side = {"/tmp/claude-1000/x/runs/r1/a.raw.json": "{}", "/tmp/claude-1000/x/runs/r1/sub/b.txt": "B\n"}
    with RT._world_scandir("/tmp/claude-1000/x/runs/r1", side) as it:
        got = {(e.name, e.is_dir(), e.is_file()) for e in it}
    assert got == {("a.raw.json", False, True), ("sub", True, False)}
    names = {e.name for e in RT._world_scandir("/tmp/claude-1000/t/driver/core", {})}
    assert "unit_resolver.py" in names
    import pytest
    with pytest.raises(FileNotFoundError):
        RT._world_scandir("/tmp/claude-1000/nowhere/at/all", {})


def test_a_namespace_package_is_served_from_the_committed_tree():
    """`driver.relocation` has no __init__.py; the finder serves it as a namespace
    package whose search path is the world's directory, never the live one - with a
    loader that records it as served, so it never lingers in sys.modules."""
    finder = RT._SiblingFinder(["/tmp/claude-1000/t"], {}, 1)
    spec = finder.find_spec("driver")
    assert spec is not None
    sub = finder.find_spec("driver.relocation", path=spec.submodule_search_locations)
    assert sub is not None and isinstance(sub.loader, RT._SiblingNamespace)
    assert sub.submodule_search_locations == ["/tmp/claude-1000/t/driver/relocation"]
    leaf = finder.find_spec("driver.relocation.exact_numbers", path=sub.submodule_search_locations)
    assert leaf is not None and leaf.loader is not None

def test_relative_import_roots_are_absolute_in_the_world():
    """`sys.path.insert(0, '.')` names the program's own directory; a served module's
    `__file__` comes from that root, so it is absolutised against the record's cwd."""
    finder = RT._SiblingFinder(["../core"], {}, 1, cwd="/tmp/claude-1000/t/driver/relocation")
    spec = finder.find_spec("unit_resolver")
    assert spec is not None
    assert spec.loader.path == "/tmp/claude-1000/t/driver/core/unit_resolver.py"
    assert RT._root_dir("../x", "/tmp/claude-1000/t/driver") == "/tmp/claude-1000/t/x"
    assert RT._root_dir("/abs/x", "/tmp/claude-1000/t") == "/abs/x"


def test_a_program_stands_where_its_command_cd_ed():
    """`os.getcwd()` inside a replayed program is the record's own directory, so
    `os.path.abspath` of a relative name resolves into the world, not the census."""
    import contextlib
    import io as _io
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    cmd = ("cd %s\npython3 - <<'PY'\nimport io, os\n"
           "io.open('thing.py','w').write(os.getcwd() + '|' + os.path.abspath('k') + '\\n')\nPY\n" % H)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, owner, side={})
    assert out == H + "|" + H + "/k\n", out

def test_an_import_is_served_from_where_the_program_stood_not_where_the_command_ended():
    """A command cd-s into A, runs a program that imports a sibling, then cd-s into B,
    where the owner lives: the sibling is A's, never B's (the owner's directory) and
    never the directory the command ended in."""
    import contextlib
    import io as _io
    A = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    B = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/other"
    side = {A + "/who.py": "WHERE = 'A'\n", B + "/who.py": "WHERE = 'B'\n"}
    cmd = ("cd %s\npython3 - <<'PY'\nimport io, who\n"
           "io.open('%s/thing.py','w').write(who.WHERE + '\\n')\nPY\ncd %s\n" % (A, B, B))
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/other/thing.py"
    try:
        with contextlib.redirect_stdout(_io.StringIO()):
            out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, owner, side=side)
    except Exception as exc:                          # noqa: BLE001 - a wrong root finds no module
        out = "%s: %s" % (type(exc).__name__, exc)
    assert out == "A\n", out

def test_a_dot_dot_path_is_the_same_directory_to_the_world():
    """`harness/../keys` is `keys`: filesystem questions and opens through the world
    resolve `..` before the suffix match, as the live filesystem would."""
    import contextlib
    import io as _io
    X = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments"
    side = {X + "/keys/a.txt": "K\n"}
    cmd = ("cd %s/harness\npython3 - <<'PY'\nimport io, os\n"
           "a = os.path.isdir('%s/harness/../keys'); b = os.path.isdir('../keys')\n"
           "c = os.path.isfile('%s/harness/../keys/a.txt')\n"
           "d = io.open('%s/harness/../keys/a.txt').read().strip()\n"
           "io.open('thing.py','w').write('%%s %%s %%s %%s\\n' %% (a, b, c, d))\nPY\n" % (X, X, X, X))
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, owner, side=side)
    assert out == "True True True K\n", out

def test_a_sibling_written_by_this_record_is_read_back_as_written_even_if_marked_stale():
    """Record 24277 renamed a token in build_launch_manifest.py (a sibling), then
    re-read it to edit further. A copy of that sibling from an earlier record is marked
    stale when the record begins, so the re-read went back to the resolver and got the
    pre-write bytes; the program's own write must win for the rest of the record."""
    import contextlib
    import io as _io
    H = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    BLM = H + "/build_launch_manifest.py"
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\n"
           "io.open('%s','w').write('MINE\\n'); s = io.open('%s').read()\n"
           "io.open('thing.py','w').write(s)\nPY\n" % (H, BLM, BLM))
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    side = {BLM: "an earlier record's copy\n"}      # marked stale when the record begins
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {24000: rec}, owner, side=side)
    assert out == "MINE\n", out[:80]

def test_assignments_separated_by_semicolons_are_shell_variables():
    """Record 13148 wrote `SP=...; NEW=$SP/step1_128k; OLD=$SP/step1_envelope` on one
    line and created a worktree at "$NEW": the tree's origin depends on reading it."""
    env = RT.shell_vars("SP=/tmp/claude-1000/s; NEW=$SP/step1_128k; OLD=$SP/step1_envelope\ngit worktree add --detach \"$NEW\" abc1234\n")
    assert env.get("NEW") == "/tmp/claude-1000/s/step1_128k" and env.get("OLD") == "/tmp/claude-1000/s/step1_envelope"
    # `cd X && H=.claude/x && for f in ...` chains an assignment with `&&` (records 7192, 8291)
    assert RT.shell_vars("cd /tmp/s && H=.claude/x && for f in a b; do cp i/$H/$f o/$H/$f; done").get("H") == ".claude/x"
    import re
    import chrono_replay as CR
    tree = RT._SCRATCH + "/step1_128k"
    CR._ORIGINS.pop(tree, None)
    cmd = RT.bash_command(RT.lines({13148})[13148])
    want = re.search(r"worktree add --detach \"\$NEW\" ([0-9a-f]{40})", cmd).group(1)
    assert CR.tree_origin(tree) == (13148, want)


def test_a_nested_program_does_not_evict_an_outer_import_still_loading():
    """While an outer program's `import X` is still loading (a half-built X sits in
    sys.modules and in SERVED_MODULES), a nested replay - the resolver's, run under the
    machinery guard - imports a module named X too. It must get ITS OWN X, and when it
    ends the outer, half-built X must be back in sys.modules: popping it killed the
    outer import with KeyError (record 7097's shape)."""
    import contextlib
    import io as _io
    import sys as _sys
    import types
    inner = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command":
        "cd /tmp/claude-1000/t2\npython3 - <<'PY'\nimport X, io\nio.open('inner.txt','w').write(str(X.V))\nPY\n"}}]}}
    outer = types.ModuleType("X")
    outer.half_built = True
    _sys.modules["X"] = outer
    RT.SERVED_MODULES.append("X")
    try:
        run = RT.machinery(lambda: RT.apply_saved_edits("", {2: inner}, "t2/inner.txt",
                                                        side={"/tmp/claude-1000/t2/X.py": "V = 2\n"}))
        try:
            with contextlib.redirect_stdout(_io.StringIO()):
                out, _ = run()
        except Exception as exc:                      # noqa: BLE001 - the evicted outer X breaks the inner import
            out = "%s: %s" % (type(exc).__name__, exc)
        assert out == "2", out[:80]                       # the inner program's own X
        assert _sys.modules.get("X") is outer             # the outer, half-built X is back
    finally:
        _sys.modules.pop("X", None)
        if RT.SERVED_MODULES and RT.SERVED_MODULES[-1] == "X":
            RT.SERVED_MODULES.pop()



def test_a_dash_c_line_inside_a_heredoc_body_is_content_not_a_program():
    """`cat > mkclaims.py <<'CEOF'` carried a `python3 -c "..."` line: file content the
    shell never ran here. Only a `-c` outside every heredoc body is a process."""
    cmd = ("cd /tmp/claude-1000/x\ncat > tool.py <<'CEOF'\nimport subprocess\n"
           "subprocess.run(['python3', '-c', 'print(1)'])\n"
           "python3 -c \"print('inside')\"\nCEOF\n"
           "python3 -c \"print('outside')\"\n")
    spans = RT.program_spans(cmd)
    assert [s[2] for s in spans] == ["print('outside')"], spans

def test_a_rejected_tool_call_did_nothing():
    """A Bash call the harness refused (input validation, a blocking hook) or an Edit it
    refused (anchor not found, file moved) answered `<tool_use_error>` and never ran:
    record 25329 was such a Bash call, and replaying it injected a token the real file
    never had. Both kinds are stepped over."""
    import contextlib
    import io as _io
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    bash = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command":
        "cd %s\npython3 - <<'PY'\nimport io\nio.open('thing.py','w').write('INJECTED\\n')\nPY\n" % H}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: bash}, owner, side={},
                                      result="<tool_use_error>InputValidationError: [\n  {\"code\": \"custom\"}]")
    assert out == "BASE\n", out
    edit = {"message": {"content": [{"type": "tool_use", "name": "Edit", "input": {
        "file_path": H + "/thing.py", "old_string": "NOT THERE", "new_string": "X"}}]}}
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: edit}, owner, side={},
                                      result="<tool_use_error>String to replace not found in file.")
    assert out == "BASE\n", out
    assert 1 in RT.REJECTED_CALLS

def test_a_command_without_cd_stood_in_the_records_working_directory():
    """The transcript records each call's `cwd`; a command with no `cd` ran there, so
    `os.getcwd()` and a relative import root resolve under it, and a relative `cd`
    chains from it."""
    import contextlib
    import io as _io
    R = "/tmp/claude-1000/x/scratchpad/bench_1306"
    cmd = ("python3 - <<'PY'\nimport io, os\n"
           "io.open('%s/.claude/plans/Drivers/experiments/harness/thing.py','w').write(os.getcwd() + '\\n')\nPY\n"
           "cd .claude/plans\npython3 - <<'PY'\nimport io, os\n"
           "io.open('Drivers/experiments/harness/thing.py','a').write(os.getcwd() + '\\n')\nPY\n" % R)
    rec = {"cwd": R, "message": {"content": [{"type": "tool_use", "name": "Bash",
                                              "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    with contextlib.redirect_stdout(_io.StringIO()):
        out, _ = RT.apply_saved_edits("", {1: rec}, owner, side={})
    assert out == R + "\n" + R + "/.claude/plans\n", out[:120]

def test_an_append_to_the_owner_selects_the_process():
    """A process that only appends to this owner writes it; the selection used to look
    for `open(..., "w")` alone and dropped the appending process, losing its bytes."""
    import chrono_replay as CR
    R_ = "/tmp/claude-1000/x/scratchpad/bench_1306"
    cmd = "cd %s/.claude/plans\npython3 - <<'PY'\nimport io\nio.open('Drivers/experiments/harness/thing.py','a').write('MORE\\n')\nPY\n" % R_
    body = RT.program_spans(cmd)[0][2]
    assert CR._python_writes(body, R_ + "/.claude/plans", "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py", {}, "thing.py") is True

def test_a_tree_seeded_from_another_trees_modified_files_copies_each_of_them():
    """The campaign built each scratch tree from its predecessor: a `for f in ...; do
    cp OLD/$H/$f NEW/$H/$f; done` loop (7192, 8291), a `git status --porcelain | ... |
    while read f; do install/cp ...; done` loop (10162, 13156) and `cp -r OLD/dir
    NEW/dir`. Each is one copy per file; a status loop copies what the source tree had
    modified (tracked only for the awk-M form), which the world answers itself."""
    import chrono_replay as CR          # importing it INSTALLS the real hook: import first, stub after
    cmd = ("SP=/tmp/claude-1000/s; OLD=$SP/step1_envelope; NEW=$SP/step1_128k\n"
           "git -C $OLD status --porcelain | awk '$1==\"M\"{print $2}' | while read p; do install -D -m 644 \"$OLD/$p\" \"$NEW/$p\"; done\n"
           "cp -f \"$OLD/x/a.py\" \"$NEW/x/a.py\"\n")
    saved = RT.TREE_MODIFIED
    RT.TREE_MODIFIED = lambda tree, line, with_tracked=False: (
        {("h/b.py", True), ("h/c.py", True), ("h/u.py", False)} if with_tracked else {"h/b.py", "h/c.py", "h/u.py"}
    ) if tree == "/tmp/claude-1000/s/step1_envelope" else set()
    try:
        # the awk-M form copies TRACKED modified files only
        assert RT.seed_copies(cmd, 5) == [("/tmp/claude-1000/s/step1_envelope/h/b.py", "/tmp/claude-1000/s/step1_128k/h/b.py"),
                                         ("/tmp/claude-1000/s/step1_envelope/h/c.py", "/tmp/claude-1000/s/step1_128k/h/c.py")]
        assert CR.writes_this(cmd, "step1_128k/h/b.py", line=5) is True
        assert CR.writes_this(cmd, "step1_128k/h/zzz.py", line=5) is False
        # the sed form, after `cd $SRC`, copies every status entry (untracked too), minus a grep exclusion
        cmd2 = ("SP=/tmp/claude-1000/s; SRC=$SP/step1_envelope; DST=$SP/step1_128k\ncd $SRC\n"
                "git status --porcelain | grep -v \"^?? h/u\" | sed 's/^...//' | while read -r f; do "
                "if [ -d \"$SRC/$f\" ]; then cp -a \"$SRC/$f.\" \"$DST/$f\"; else cp -a \"$SRC/$f\" \"$DST/$f\"; fi; done\n")
        got = RT.seed_copies(cmd2, 5, "/tmp/claude-1000/s")
        assert ("/tmp/claude-1000/s/step1_envelope/h/b.py", "/tmp/claude-1000/s/step1_128k/h/b.py") in got
        assert not any(d.endswith("/h/u.py") for _s, d in got), got
        # a for-list loop copies each listed file, relative to the record's directory
        cmd3 = "H=.claude/x\nfor f in a.py b.py; do cp step1_iso/$H/$f step1_fmt/$H/$f; done\n"
        assert RT.seed_copies(cmd3, 5, "/tmp/claude-1000/s") == [
            ("/tmp/claude-1000/s/step1_iso/.claude/x/a.py", "/tmp/claude-1000/s/step1_fmt/.claude/x/a.py"),
            ("/tmp/claude-1000/s/step1_iso/.claude/x/b.py", "/tmp/claude-1000/s/step1_fmt/.claude/x/b.py")]
    finally:
        RT.TREE_MODIFIED = saved
    import re as _re
    assert _re.match(RT._COPY_RE, 'cp -f "$OLD/x/a.py" "$NEW/x/a.py"')
    assert _re.match(RT._COPY_RE, 'install -D -m 644 "$OLD/$p" "$NEW/$p"')
    assert RT._DIR_COPY.search("cp -r step1_iso/h/launchers step1_fmt/h/launchers\n")

def test_the_active_owners_text_is_served_only_at_or_beyond_the_record_being_applied():
    """While a replay of X is applying record N, a nested read of X for a cutoff at or
    beyond N gets the in-flight text; one for an EARLIER cutoff gets nothing here and
    is rebuilt on its own. Handing the in-flight bytes over regardless of the cutoff
    was the second door record 24277's context came through."""
    basename = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    path = "/tmp/claude-1000/x/scratchpad/" + basename
    RT.ACTIVE_OWNERS.append((basename, {"text": "LIVE\n", "line": 24277}))
    try:
        assert RT.active_owner_text(path) == "LIVE\n"
        assert RT.active_owner_text(path, 24278) == "LIVE\n"
        assert RT.active_owner_text(path, 24277) == "LIVE\n"
        assert RT.active_owner_text(path, 24246) is None
    finally:
        RT.ACTIVE_OWNERS.pop()

def test_a_dash_c_program_ends_at_its_matching_quote_not_the_lines_last_quote():
    """`python3 -c "..." ; echo "... $(run)"; cp a b` on one line: the program is the
    double-quoted string as the shell read it (escapes honoured), never the shell that
    follows it on the line."""
    cmd = 'python3 -c "import io; io.open(\'x\',\'w\').write(\\"a\\")"; echo "gate: $(run)"; cp /tmp/a /tmp/b\n'
    spans = RT.program_spans(cmd)
    assert [s[2] for s in spans] == ['import io; io.open(\'x\',\'w\').write("a")'], spans
    cmd2 = "python3 -c 'print(1)'; python3 -c \"print(2)\"\n"
    assert [s[2] for s in RT.program_spans(cmd2)] == ["print(1)", "print(2)"]
