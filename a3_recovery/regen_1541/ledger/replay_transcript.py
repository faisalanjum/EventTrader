"""Replay exact saved work out of the Core transcript (Codex SEQ 1539 items 3-4).

The transcript preserves, verbatim, the Write inputs that created a file and the Bash
programs that later edited it. This module reads those records and replays them in memory:
a saved edit script that reads and rewrites a file on disk is executed against an in-memory
copy, so nothing outside the recovery directory is read or written. Every step reports the
digest of the content it produced; a step whose anchor does not match refuses.
"""
import builtins
import collections
import hashlib
import errno
import io
import json
import os
import re
import subprocess
import sys

#: the whole wiped scratch root: derived intermediates were written here too
SCRATCH_ROOT = "/tmp/claude-1000"

#: THE SCRATCH WORKTREE WAS A COMMIT. Core transcript line 22311 records the bench
#: worktree being created from this commit, so every file in it that no record has
#: yet rewritten still holds its committed bytes. A saved program that edits this
#: owner often edits a SIBLING first; without that sibling the program raised before
#: it ever reached the owner, and the owner's change was silently lost. Seeding
#: siblings from the commit is not an extra input - it is the state history ran on.
#: THE REPLAY'S OWN READS ARE NOT THE PROGRAM'S. Sibling resolution, source resolution,
#: script rebuilding and tree-origin lookup read the transcript, the recovered inventory
#: and the cache; entered from inside a replayed program's open, those reads came back
#: through the shim and were counted as the PROGRAM's pass-throughs - 21 "transcript
#: reads" at one record, five cache reads (Codex SEQ 1559 item 2). While any machinery
#: entry point is active the shim hands every open to the real opener and audits
#: nothing, whatever the call path.
_MACHINERY = [0]


def machinery(fn):
    """Mark a replay-machinery entry point: opens made while it runs bypass the shim."""
    def wrapped(*a, **k):
        _MACHINERY[0] += 1
        try:
            return fn(*a, **k)
        finally:
            _MACHINERY[0] -= 1
    wrapped.__name__ = getattr(fn, "__name__", "machinery")
    wrapped.__wrapped__ = fn
    return wrapped


WORKTREE_COMMIT = "cd961e51d55bf13aa9311b79c5d7eca20e9b11cc"
#: THE PACKAGE IS THE ONLY ROOT. No checkout is consulted: the committed objects the
#: routes resolve were recovered ONCE (recover_git_bases.py) into evidence/git_bases/,
#: and the accepted transcript prefix lives in evidence/transcript/. A proof that
#: shelled out to `git` against the dirty main tree depended on bytes no manifest
#: protected (Codex SEQ 1559 item 1).
PACKAGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_BASES = os.path.join(PACKAGE, "evidence", "git_bases")
#: interpreter and system paths are tooling a program may open; everything else that is
#: not inside the package is outside the replay world
TOOLING = (sys.prefix, sys.base_prefix, "/usr/lib", "/usr/local/lib", "/proc", "/dev",
           "/sys", "/etc")


def _outside(sp):
    """Outside the package: every absolute path that is neither inside it nor tooling,
    and every RELATIVE path whose working directory the replay could not establish -
    such a name belonged to a scratch tree, and resolving it against this process's
    own directory would read the package by accident."""
    if not os.path.isabs(sp):
        return True
    return not sp.startswith(PACKAGE + "/") and not sp.startswith(TOOLING)
_TREE = {}

#: Set by the route builder to `f(path, before_line) -> text or None`. A sibling file
#: is NOT frozen at the commit: by the time this owner's record reads it, its own
#: records have already rewritten it. The resolver replays the sibling's own route up
#: to this point, so the owner sees the sibling as history did. Falls back to the
#: committed bytes when the sibling has no records yet.
SIBLING_RESOLVER = None

#: Set by the route builder to `f(tree) -> commit`. `git show HEAD:<rel>` inside a
#: scratch worktree yields that TREE's COMMITTED bytes, which are not the bytes the
#: replay has built so far - and that difference is the whole point of a command that
#: restores a region deleted since the checkout.
TREE_COMMIT = None

_GIT_SHOW_REDIRECT = re.compile(
    r"git\s+show\s+([A-Za-z0-9_./^~-]+):([^\s>|]+)\s*>(?!>)\s*\"?([^\"\s]+)")


@machinery
def seed_git_show(cmd, side):
    """Put each `git show <rev>:<rel> > DST` in the command into the scratch files.

    A redirect like this PRODUCES a file that a later step of the same command (or a
    later record) reads. Without it the read finds nothing and the whole command
    refuses, losing every edit it went on to make.
    """
    env = shell_vars(cmd)
    tree = cmd.split("scratchpad/", 1)[1].split("/")[0] if "scratchpad/" in cmd else ""
    for m in _GIT_SHOW_REDIRECT.finditer(cmd):
        rev, rel, dst = m.group(1), expand(m.group(2), env), expand(m.group(3), env)
        # a named revision (HEAD, a branch) means "this tree's base"; an explicit
        # object id is already the answer and is used as written
        commit = rev if re.fullmatch(r"[0-9a-f]{7,40}", rev) else None
        if commit is None and TREE_COMMIT is not None and tree:
            commit = TREE_COMMIT(tree)
        body = _committed(rel, commit=commit or WORKTREE_COMMIT)
        if body is not None:
            side[dst] = body


@machinery
def _committed(path, commit=WORKTREE_COMMIT):
    """-> committed text for a scratch path, by the LONGEST SUFFIX the commit holds.

    The worktree's own root directory name is never assumed: the path is matched
    against the commit's file list from the right, so any checkout location works.
    """
    commit = _full_commit(commit)
    if commit not in _TREE:
        tree = os.path.join(GIT_BASES, commit + ".tree")
        if not os.path.isfile(tree):
            raise RuntimeError("git base store has no tree for commit %s; the proof "
                               "does not consult a checkout (recover_git_bases.py)"
                               % commit)
        _TREE[commit] = set(n for n in
                            io.open(tree, encoding="utf-8").read().split("\n") if n)
    parts = str(path).strip("/").split("/")
    for i in range(len(parts)):
        rel = "/".join(parts[i:])
        # PATH-AWARE, NOT NAME-AWARE: a one-segment suffix of a longer path is a bare
        # filename, and a bare `__init__.py` or `setup.py` matches the repository's
        # root copy of any such name - the wrong file, served silently. A suffix must
        # carry at least its directory unless the path itself is a bare name.
        if len(parts) > 1 and i == len(parts) - 1:
            break
        if rel in _TREE[commit]:
            obj = os.path.join(GIT_BASES, commit, rel)
            if not os.path.isfile(obj):
                STORE_MISSES.append("%s:%s" % (commit, rel))
                raise RuntimeError("git base store lacks %s:%s although the commit "
                                   "carries it; the proof does not consult a checkout"
                                   % (commit, rel))
            return io.open(obj, "rb").read().decode("utf-8")
    return None


#: THE RUN TREES THE TRANSCRIPT REFERS TO, SERVED FROM THE PACKAGE. A saved program
#: reads files under its scratch run tree that no transcript record wrote - workflow
#: states copied into quarantine, receipts, journals. Those bytes were recovered once
#: into the vendored experiments tree, and a read of the historical scratch path is
#: served from there, as the LAST resort after the side table, the sibling resolver
#: and the committed store. The keys name the SUBJECT (the trees history used); the
#: values are inside the package, so a mounted read is never a read outside it.
_SCRATCH = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
            "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
MOUNTS = {
    _SCRATCH + "/invrev_run4": os.path.join(PACKAGE, "bench", ".claude", "plans",
                                            "Drivers", "experiments", "invrev_run4"),
    # the official workflow states a saved program reads: durable, copied and pinned
    # in evidence/workflow_states/WORKFLOW_STATES.tsv
    os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/"
                       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/workflows"):
        os.path.join(PACKAGE, "evidence", "workflow_states"),
    # the agent transcripts and journals of those runs, copied and pinned the same way
    os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/"
                       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/subagents/workflows"):
        os.path.join(PACKAGE, "evidence", "subagent_records"),
}
#: every historical path a mount was asked for and could not serve - for the recovery
#: tools, which copy exactly those durable files into the package
MOUNT_MISSES = []
#: (commit:rel) pairs a route asked the git store for and the store did not hold,
#: although the commit's tree carries them. A recovery run dumps these so the store
#: can be EXTENDED from a measured list - never from a hand-typed object name.
STORE_MISSES = []
#: module names the sibling loader served, evicted after each program (see _replay)
SERVED_MODULES = []
#: the package's vendored evidence tree: modules loaded from it belong to no replayed program
BENCH_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bench")
#: records the harness refused to run (their saved result is a `<tool_use_error>`);
#: they are stepped over, never replayed
REJECTED_CALLS = []
#: every (module, outside root) the import finder refused because only the live
#: filesystem could provide it
IMPORT_MISSES = []


@machinery
def _mounted(sp):
    """-> the durable bytes for a historical scratch path, or None."""
    for root, dest in MOUNTS.items():
        if sp == root or sp.startswith(root + "/"):
            fp = os.path.join(dest, os.path.relpath(sp, root)) if sp != root else dest
            if os.path.isfile(fp):
                return _REAL_IO_OPEN(fp, "rb").read().decode("utf-8")
            MOUNT_MISSES.append(sp)
    return None


def _full_commit(commit):
    """The store is keyed by FULL ids; a saved command may name a short one."""
    commit = str(commit)
    if len(commit) == 40:
        return commit
    hits = [n[:-5] for n in os.listdir(GIT_BASES)
            if n.endswith(".tree") and n.startswith(commit)]
    if len(hits) != 1:
        raise RuntimeError("git base store resolves %r to %d commits" % (commit, len(hits)))
    return hits[0]
#: THE ACCEPTED TRANSCRIPT AUTHORITY: exactly the first 210560179 bytes of the Core
#: transcript, 111621 rows, materialised once and manifested. Never the live file,
#: which grows under any proof that reads it.
TRANSCRIPT = os.path.join(PACKAGE, "evidence", "transcript", "accepted_prefix.jsonl")


#: THE TRUE FILE OPENERS, captured ONCE at import and never reassigned.
#: `apply_saved_edits` patches `io.open` and `builtins.open` while a saved program runs.
#: A NESTED replay - resolving a sibling while an outer program is mid-open - used to
#: capture the OUTER shim as its "real" opener, so a fall-through went shim to shim
#: without end. Falling back to these makes that impossible however deeply replays nest.
_REAL_IO_OPEN = io.open
_REAL_BUILTIN_OPEN = builtins.open

class TranscriptError(ValueError):
    pass


class ReplayEnvironmentError(TranscriptError):
    """Raised when a saved program asks for something this replay cannot supply.

    A program that shells out was OBSERVING a live tree - running its tests, reading
    its git state. That tree is gone, so running the command now answers from the
    wrong world, and the answer decides what the program does next. Refusing is the
    only honest reply, and it is distinguishable from a failure history itself had.
    """


class _NoSubprocess(object):
    """Stands in for `subprocess` inside a replayed program, and only there.

    The replay's own machinery keeps the real module through its existing import, so
    reading a committed base still works while the program's calls are refused.
    """

    def __getattr__(self, name):
        def _refuse(*_a, **_k):
            raise ReplayEnvironmentError(
                "a saved program called subprocess.%s; the tree it observed no longer "
                "exists, so the replay cannot answer for it" % name)
        return _refuse


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@machinery
def lines(numbers, path=TRANSCRIPT):
    """-> {line number: parsed record} for the requested 1-based line numbers."""
    want = set(numbers)
    out = {}
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            if n in want:
                out[n] = json.loads(line)
                if len(out) == len(want):
                    break
    missing = want - set(out)
    if missing:
        raise TranscriptError("transcript lines %s are absent" % sorted(missing))
    return out


def _blocks(rec, kind):
    for b in ((rec.get("message") or {}).get("content") or []):
        if isinstance(b, dict) and b.get("type") == kind:
            yield b


def write_input(rec):
    """-> (file_path, content) of the Write tool call saved on this line."""
    for b in _blocks(rec, "tool_use"):
        if b.get("name") == "Write":
            inp = b.get("input") or {}
            return inp.get("file_path"), inp.get("content")
    raise TranscriptError("this record carries no Write input")


def bash_command(rec):
    for b in _blocks(rec, "tool_use"):
        if b.get("name") == "Bash":
            return (b.get("input") or {}).get("command", "")
    raise TranscriptError("this record carries no Bash command")


def tool_result_text(rec):
    for b in _blocks(rec, "tool_result"):
        c = b.get("content")
        if isinstance(c, str):
            return c
        return "".join(x.get("text", "") for x in c if isinstance(x, dict))
    raise TranscriptError("this record carries no tool result")


def shell_vars(command):
    """-> {name: value} for the simple VAR=... assignments a saved command opens with,
    with earlier variables expanded into later ones. Nothing is executed."""
    env = {}
    # `SP=...; NEW=$SP/step1_128k; OLD=$SP/step1_envelope` is three assignments on one
    # line: record 13148 created a worktree that way, and a line-only parser left
    # `$NEW` unexpanded so the tree read as originless
    for m in re.finditer(r"(?:^|;|&&)\s*([A-Za-z_][A-Za-z0-9_]*)=(\"[^\"]*\"|'[^']*'|[^\s;&]+)\s*(?=;|&&|$)",
                         command, re.M):
        val = m.group(2).strip("\"'")
        for k, v in env.items():
            val = val.replace("${%s}" % k, v).replace("$" + k, v)
        env[m.group(1)] = val
    return env


def expand(text, env):
    for k, v in sorted(env.items(), key=lambda kv: -len(kv[0])):
        text = text.replace("${%s}" % k, v).replace("$" + k, v)
    return text


def grep_vars(command, text, basename):
    """-> {name: line number} for `VAR=$(grep -n "MARK" <this file> | cut -d: -f1)`.

    The shell computed this from the file's own bytes before the program ran, so the
    value is a product of the replay, not an outside input. The marker must select
    exactly one line; anything else refuses rather than picking one.
    """
    env = {}
    for m in re.finditer(
            r"""^\s*([A-Za-z_]\w*)=\$\(\s*grep\s+-n\s+["'](.+?)["']\s+(\S+)\s*\|"""
            r"""\s*cut\s+-d:\s+-f1\s*\)\s*$""", command, re.M):
        name, pat, path = m.group(1), m.group(2), m.group(3)
        if not expand(path, shell_vars(command)).endswith(basename):
            continue
        pat = pat[1:] if pat.startswith("^") else pat
        hits = [i for i, line in enumerate(text.split("\n"), 1) if line.startswith(pat)]
        if len(hits) != 1:
            raise TranscriptError(
                "the saved substitution for %s matches %d lines" % (name, len(hits)))
        env[name] = str(hits[0])
    return env


def heredocs(command, env=None):
    """-> every program in a saved command, in order.

    ONE COMMAND WAS OFTEN SEVERAL PROCESSES. A saved command frequently ran one
    program against a sibling file and a SECOND against this owner. Each is its own
    interpreter, so a failure in one did not stop the next; returning only the first
    made the owner's own change invisible whenever a sibling program preceded it.
    """
    return [p for _, _, p in program_spans(command, env)]


def program_spans(command, env=None):
    """-> sorted [(start, end, source)] for every program the command runs.

    The POSITIONS matter as much as the sources: a command routinely ran a program
    and then went on to append to the same file with the shell, so the composer has
    to know where the program sat in order to apply what came after it.
    """
    spans = []
    # THE OPENING LINE MAY CONTINUE PAST THE TAG. `python3 - <<'PY' 2>&1 | tail -22`
    # runs a program exactly as `<<'PY'` does; requiring the tag to end the line made
    # every such record invisible, so its program never replayed and the files it
    # produced were never built.
    for m in re.finditer(r"<<'?([A-Za-z0-9_]+)'?[^\n]*\n(.*?)\n\1\s*$",
                         command, re.S | re.M):
        # A HEREDOC IS ONLY A PROGRAM WHEN AN INTERPRETER IS READING IT. The same
        # syntax delivered file CONTENT (`cat > x <<'PY'`), which the shell-composition
        # path already applies; executing those bodies too would apply them twice.
        head = command[:m.start()].split("\n")[-1]
        if "python" in head:
            spans.append((m.start(), m.end(), m.group(2)))
    bodies = [(m.start(), m.end()) for m in re.finditer(
        r"<<'?([A-Za-z0-9_]+)'?[^\n]*\n(.*?)\n\1\s*$", command, re.S | re.M)]
    for start, end, src in _dash_c_programs(command):
        # A `-c` LINE INSIDE A HEREDOC BODY IS FILE CONTENT, NOT A PROCESS. Record 7097
        # wrote mkclaims.py with `cat > ... <<'CEOF'`, and that file carried a
        # `python3 -c "..."` line of its own; the shell never ran it here, but the
        # replay did - in this record's directory - and imported the wrong tree.
        if any(a <= start < b for a, b in bodies):
            continue
        # A `-c` PROGRAM IS DOUBLE-QUOTED, so the shell substituted the command's own
        # variables before Python ever saw it. Replaying it with `$H` still literal
        # made it open a path that resolves nowhere. Heredoc bodies quoted `<<'PY'`
        # are NOT expanded by the shell, and are correspondingly left alone.
        vars_ = dict(shell_vars(command))
        vars_.update(env or {})
        spans.append((start, end, expand(src, vars_)))
    return sorted(spans)


def _dash_c_programs(command):
    """-> [(start, end, source)] for every `python -c "..."` / `python -c '...'` in a
    command, the string read the way the shell read it: to the MATCHING quote, honouring
    backslash escapes inside double quotes - not to the last quote on the line. Records
    14092, 14415, 14653 and 15295 ran `python3 -c "..." ; echo "... $(run)"; cp ...` on
    one line, and a regex that ended at the line's last quote glued the shell that
    followed onto the program, which then failed to compile where history had run it."""
    out = []
    for m in re.finditer(r"""python3?\s+-c\s+(["'])""", command):
        q = m.group(1)
        i = m.end()
        buf = []
        while i < len(command):
            ch = command[i]
            if q == '"' and ch == "\\" and i + 1 < len(command) and command[i + 1] in '"\\$`':
                buf.append(command[i + 1]); i += 2; continue
            if ch == q:
                break
            buf.append(ch); i += 1
        else:
            continue
        out.append((m.start(), i + 1, "".join(buf)))
    return out


def cwd_at(command, pos, start=None):
    """-> the directory the shell stood in when it reached `pos`, or None.

    ONE `cd` PER PROCESS, IN ORDER. A command routinely enters one tree, edits a file
    by a relative name, then enters another; taking any `cd` in the command made a
    relative name resolve into a tree the process was never in.
    `start` is where the shell stood before its first `cd` - the record's own `cwd`.
    """
    cwd = start if start and os.path.isabs(str(start)) else None
    env = shell_vars(command)
    for m in re.finditer(r"(?m)(?:^|&&|;|\|\|)\s*cd\s+\"?([^\"\s&;|]+)\"?", command[:pos]):
        got = expand(m.group(1), env)
        cwd = got if os.path.isabs(got) else (
            os.path.normpath(os.path.join(cwd, got)) if cwd else got)
    return cwd


def process_units(command, start_dir=None):
    """-> [(start, end, cwd, kind, text)] - one unit per PROCESS the command runs.

    A Bash tool call is not one actor. It is a sequence of processes, each with its own
    working directory: `cd $A && python3 - <<PY ... PY` followed by `cd $B && python3 -
    <<PY ... PY` is two processes in two trees. Classifying the call as a whole let a
    `cd` into a sibling tree be ignored and let a filename that appears only as TEXT
    inside one process's program classify the whole call.

    Program units carry an interpreter's source; shell units carry the plain shell text
    between them. The split is by POSITION, so nothing is counted twice.
    """
    spans = program_spans(command)
    units, pos = [], 0
    for start, end, src in spans:
        if start > pos:
            units.append((pos, start, cwd_at(command, pos, start_dir), "shell",
                          command[pos:start]))
        units.append((start, end, cwd_at(command, start, start_dir), "program", src))
        pos = end
    if pos < len(command):
        units.append((pos, len(command), cwd_at(command, pos, start_dir), "shell",
                      command[pos:]))
    return units


#: Set by the route builder to `f(command, basename, line) -> [program indices]`. Only
#: the processes that write this owner (and their producers) are executed; a sibling
#: process that merely shares the Bash call is not this owner's business.
SELECT_UNITS = None


def heredoc(command, tag=None):
    """The FIRST program inside a saved command, verbatim."""
    m = re.search(r"<<'?([A-Za-z0-9_]+)'?\n(.*?)\n\1\s*$", command, re.S | re.M)
    if tag and m and m.group(1) != tag:
        raise TranscriptError("heredoc tag %r is not %r" % (m.group(1), tag))
    progs = heredocs(command)
    if not progs:
        raise TranscriptError("the saved command carries no heredoc program")
    return progs[0]


def _edit_input(rec, basename):
    """-> (old, new, replace_all) if this record is an Edit of `basename`."""
    for b in _blocks(rec, "tool_use"):
        if b.get("name") != "Edit":
            continue
        inp = b.get("input") or {}
        if not str(inp.get("file_path", "")).endswith(basename.lstrip("/")):
            continue
        return (inp.get("old_string", ""), inp.get("new_string", ""),
                bool(inp.get("replace_all")))
    return None



@machinery
def _resolve_source(src, side, line, bodies=None):
    """-> the bytes of a file a shell operation reads, or None.

    A SOURCE MAY LIVE IN ANOTHER TREE. The campaign rebuilt a file by copying a version
    it had built elsewhere; that source is a deterministic product of its own records,
    so when it is not already in memory the resolver replays its route rather than
    giving up and leaving the operation unapplied.
    """
    # MEASURED: skipping a stale-marked copy here was tried and REVERTED - it gained
    # the auditor nothing and cost the guard seven extra refusals, because a copy held
    # from an earlier record is still the best evidence when nothing can rebuild it.
    if bodies and src in bodies:
        return bodies[src]
    if src in side:
        return side[src]
    # the fallback match is path-aware: with a directory in the request the last TWO
    # segments must match, so `pathlib/__init__.py` is never satisfied by whichever
    # `__init__.py` the side table happens to hold
    # EXACT PATH OR NOTHING. A lookup used to be answered by any held file whose last
    # two components agreed with it, so a path history never had (record 22655's
    # `driver/core/.claude/skills/.../fiscal_math.py`) was served the real module under
    # the wrong name, and the module's own identity guard refused where history's
    # interpreter had skipped the missing directory and found the next root.
    if SIBLING_RESOLVER is not None and line is not None:
        got = SIBLING_RESOLVER(src, line)
        if got is not None:
            side[src] = got
            return got
    return _committed(src)


def _bre_to_py(pattern):
    """-> a Python regex for a POSIX basic regular expression, as `sed` reads it.

    In a BRE the escaping is inverted from Python's: `\\(` groups while `(` is a
    literal, and `+` and `?` are ordinary characters. Translating rather than passing
    the pattern through is what keeps a literal `(` from silently becoming a group.
    """
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            nxt = pattern[i + 1]
            out.append(nxt if nxt in "(){}" else "\\" + nxt)
            i += 2
            continue
        out.append("\\" + c if c in "(){}+?" else c)
        i += 1
    return "".join(out)


#: (script path, cutoff) -> its reconstructed text
_EXECUTED_CACHE = {}


@machinery
def _executed_scripts(command, line):
    """-> the TEXT of every saved script this command executes.

    `python3 <path>.py` runs a file the replay can rebuild. Only scratch paths qualify:
    they are deterministic products of the replay, never outside inputs.
    """
    out = []
    for m in re.finditer(r"""python3?\s+(?:-B\s+)?["']?(%s[^\s"']*\.py)["']?"""
                         % re.escape(SCRATCH_ROOT), expand(command, shell_vars(command))):
        if SIBLING_RESOLVER is None:
            continue
        key = (m.group(1), line)
        # the same command is replayed more than once across a route and its siblings;
        # rebuilding the script it runs each time repeats an entire replay for no new
        # information, since the answer depends only on the script and the cutoff
        if key not in _EXECUTED_CACHE:
            _EXECUTED_CACHE[key] = SIBLING_RESOLVER(key[0], line)
        out.append(_EXECUTED_CACHE[key])
    return out


def stdin_program_argv(command, program_start):
    """-> the arguments the shell passed to the stdin program whose heredoc body starts
    at `program_start`: the tokens after the `-` on its `python ... - ARGS <<TAG` line,
    shell variables expanded. A program that reads `sys.argv[k]` read exactly these."""
    import shlex
    head = command[:program_start]                 # ends at the heredoc operator
    line = head.rstrip("\n").rsplit("\n", 1)[-1]
    m = re.search(r"(?:^|[\s;&|(])(?:\S*python[0-9.]*)(?:\s+-[A-Za-z]+)*\s+-\s+(.*?)\s*(?:<<.*)?$", line)
    if not m:
        return []
    env = shell_vars(command)
    try:
        return [expand(t, env) for t in shlex.split(m.group(1))]
    except ValueError:
        return []


def _executed_script_argv(command):
    """-> [argv, ...] for every saved script `_executed_scripts` returns, in order:
    the script's path followed by the arguments the command line gave it, expanded.
    A run such as `python -B "$S/harvest.py" 11 <sid> <run> 1` is meaningless without
    them - the replay used to hand every program the owner's synthetic argv."""
    import shlex
    out = []
    text = expand(command, shell_vars(command))
    for m in re.finditer(r"""python3?\s+(?:-B\s+)?["']?(%s[^\s"']*\.py)["']?([^\n|;&]*)"""
                         % re.escape(SCRATCH_ROOT), text):
        # the arguments end where a redirection begins: `2>&1`, `> out`, `< in`
        tail = re.split(r"\s+\d*[<>]", m.group(2))[0]
        try:
            args = shlex.split(tail)
        except ValueError:
            args = tail.split()
        out.append([m.group(1)] + args)
    return out


#: the transcript, read ONCE. `saved_result` is consulted for every replayed record,
#: including every record of every sibling replay, and re-reading a hundred thousand
#: lines each time cost a quarter of a second per record - which is where a long
#: owner's replay actually went.
_LINES = {}


@machinery
def transcript_lines(path=TRANSCRIPT):
    if path not in _LINES:
        try:
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                _LINES[path] = fh.readlines()
        except Exception:
            _LINES[path] = []
    return _LINES[path]


class ResultLedger(object):
    """Every tool use and every tool result of a transcript, keyed by exact id.

    PRESENCE AND TEXT ARE DIFFERENT FACTS. A command that completed with no output has
    an EMPTY result; a call whose result never arrived has NO result. Collapsing the
    two - which a `.strip()` filter does - reads eight real completions as silence and
    would let a genuinely outstanding call look like a success.

    Nothing here guesses by position: a result belongs to the use whose id it names.
    Corrupt, duplicate, unmatched and outstanding rows are counted rather than dropped,
    so the accounting adds up to the file.
    """

    def __init__(self):
        self.uses = {}                #: id -> line of the tool_use
        self.results = {}             #: id -> line of the tool_result
        self.text = {}                #: id -> result text (may be "")
        self.corrupt = []             #: rows that do not parse
        self.duplicate_uses = []
        self.duplicate_results = []
        self.rows = 0

    @property
    def matched(self):
        return len(set(self.uses) & set(self.results))

    @property
    def unmatched(self):
        """Results naming a use this file does not contain."""
        return sorted(set(self.results) - set(self.uses))

    @property
    def outstanding(self):
        """Uses whose result never arrived - a call still live at the boundary."""
        return sorted(set(self.uses) - set(self.results))

    @property
    def empty_results(self):
        return sum(1 for t in self.text.values() if t == "")

    def present(self, tool_use_id):
        return tool_use_id in self.results

    def _id_at(self, line):
        for tid, ln in self.uses.items():
            if ln == line:
                return tid
        return None

    def present_at(self, line):
        tid = self._id_at(line)
        return tid is not None and self.present(tid)

    def text_at(self, line):
        tid = self._id_at(line)
        return None if tid is None else self.text.get(tid)


#: parsed ledgers, keyed by (path, limit) - one parse per transcript view
_LEDGERS = {}


@machinery
def result_ledger(path=TRANSCRIPT, limit_bytes=None):
    """-> the ONE parsed ledger for this transcript (or a frozen prefix of it)."""
    key = (path, limit_bytes)
    if key in _LEDGERS:
        return _LEDGERS[key]
    L = ResultLedger()
    with io.open(path, "rb") as fh:
        raw = fh.read() if limit_bytes is None else fh.read(limit_bytes)
    rows = raw.decode("utf-8", "replace").split("\n")
    if rows and rows[-1] == "":
        rows.pop()
    L.rows = len(rows)
    for i, row in enumerate(rows, 1):
        # EVERY ROW IS PARSED. A corrupt row carries no keywords to filter on, so a
        # keyword prefilter silently excused it from the accounting - and the whole
        # point of this ledger is that the counts add up to the file. Parsing all
        # 111,621 rows costs well under a second.
        try:
            rec = json.loads(row, strict=False)
        except ValueError:
            L.corrupt.append(i)
            continue
        if '"tool_use"' not in row and '"tool_result"' not in row:
            continue
        for b in ((rec.get("message") or {}).get("content") or []):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("id"):
                if b["id"] in L.uses:
                    L.duplicate_uses.append(b["id"])
                else:
                    L.uses[b["id"]] = i
            elif b.get("type") == "tool_result" and b.get("tool_use_id"):
                tid = b["tool_use_id"]
                if tid in L.results:
                    L.duplicate_results.append(tid)
                    continue
                c = b.get("content")
                L.results[tid] = i
                L.text[tid] = c if isinstance(c, str) else "".join(
                    x.get("text", "") for x in c or [] if isinstance(x, dict))
    _LEDGERS[key] = L
    return L


@machinery
def saved_result(line, path=TRANSCRIPT):
    """-> the result text saved for the command on `line`, or None if there is none.

    BY ITS ID, AND EMPTY IS NOT ABSENT. The transcript interleaves assistant text
    between a command and its result, so a fixed look-ahead missed results that sit
    further down; and a completed command that printed nothing has an EMPTY result,
    which is a fact about history, not a gap in it.
    """
    L = result_ledger(path)
    rows = transcript_lines(path)
    if not rows or line >= len(rows):
        return None
    try:
        rec = json.loads(rows[line - 1], strict=False)
    except ValueError:
        return None
    for b in ((rec.get("message") or {}).get("content") or []):
        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id"):
            if b["id"] in L.text:
                return L.text[b["id"]]
    return None


_LAUNCH = re.compile(r"Command running in background with ID: ([A-Za-z0-9_-]+)")


def background_task_id(result):
    """-> the task id when a saved result is only the launch notice of a background
    command, else None. Such a record proves the LAUNCH, never the outcome."""
    m = _LAUNCH.match((result or "").lstrip())
    return m.group(1) if m else None


def background_outcome(line, path=TRANSCRIPT):
    """-> (task id, the text history later OBSERVED for that task) for a record whose
    saved result is a background launch notice, or (task id, None) when nothing in the
    transcript ever read that task's output, or (None, None) for a foreground record.

    A BACKGROUND RECORD'S RESULT IS NOT ITS OUTCOME. `python3 mkclaims.py` launched at
    record 7097 answered "Command running in background with ID: b1bxwdxrx"; the run's
    real result reached history through the later waiter that `cat` the task's output
    file, and through the task notification. Judging the replay of such a program
    against the launch notice calls every background failure unexplained and every
    background success invisible; judging it against what history observed is the
    same exact-exception rule the foreground records already answer to."""
    tid = background_task_id(saved_result(line, path))
    if not tid:
        return None, None
    seen = []
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for n, raw in enumerate(fh, 1):
            if n <= line or tid not in raw:
                continue
            try:
                rec = json.loads(raw)
            except ValueError:
                continue
            for b in ((rec.get("message") or {}).get("content") or []):
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                if "tasks/%s.output" % tid in (inp.get("command") or "") + (inp.get("file_path") or ""):
                    got = saved_result(n, path)
                    if got:
                        seen.append(got)
            if rec.get("type") in ("attachment", "queue-operation"):
                s = json.dumps(rec)
                if "<task-id>%s</task-id>" % tid in s:
                    seen.append(s)
    return tid, ("\n".join(seen) if seen else None)


@machinery
def result_present(line, path=TRANSCRIPT):
    """True when history recorded an outcome for this command, empty or not."""
    return result_ledger(path).present_at(line)


def shell_terminated(result):
    """True when a command's WHOLE result is a termination notice.

    A command that kills its own shell - `pkill` matching the shell, a signal, a hard
    timeout - never reaches its later steps, and the transcript records nothing but the
    exit status. Replaying the embedded program then invents content the era never had.
    The judgement is made on the saved result, not on the text of the command, so it
    needs no knowledge of which commands are dangerous.
    """
    if result is None:
        return False
    body = result.strip()
    return bool(body) and bool(re.fullmatch(r"Exit code \d+", body))


def _remainder_names_owner(failure, progs, name):
    """True when the part of the failed program that never ran names the owner.

    THE RESTORE IS DECIDED BY HISTORY'S OWN TEXT. A program the environment cut short
    (its `subprocess` call) may have edited the owner and then, in the part that did not
    run, written the original back - that is what the restore is for. When the rest of
    the program never names the file, history kept the write: record 29188 created
    `attempts.json`, then asked `claude auth status`, and the restore emptied the file
    the harvest era read from that day on."""
    tb = getattr(failure, "__traceback__", None)
    frames = []
    while tb is not None:
        frames.append((tb.tb_frame.f_code.co_filename, tb.tb_lineno))
        tb = tb.tb_next
    hit = [(f, ln) for f, ln in frames if f.startswith("<transcript:")]
    if not hit:
        return True                                  # no program frame: keep the old rule
    fname, lineno = hit[-1]
    try:
        idx = int(fname.strip("<>").split(":")[2])
    except (IndexError, ValueError):
        return True
    if idx >= len(progs):
        return True
    prog = progs[idx]
    rest = "\n".join(prog.split("\n")[lineno:])
    if name in rest:
        return True
    # a variable bound to a literal path that names the owner (`p = '.../x.json'`)
    # names the owner wherever the remainder uses it
    for m in re.finditer(r"""([A-Za-z_]\w*)\s*=\s*\(?\s*((?:["'][^"'\n]*["']\s*)+)\)?""", prog):
        lit = "".join(re.findall(r"""["']([^"'\n]*)["']""", m.group(2)))
        if lit.endswith(name) and re.search(r"\b%s\b" % re.escape(m.group(1)), rest):
            return True
    return False


def sed_operations(command):
    """-> every `sed -i` operation this command performs, IN COMMAND ORDER.

    ONE parser and one order. Substitutions and line-addressed inserts were previously
    collected by two scans and applied one kind after the other, which is not what the
    shell did: a command that inserts a line and then rewrites it produces a different
    file if the rewrite runs first.

    Each op is (pos, path, backup_suffix, kind, payload, guard), where `guard` is the
    `grep PATTERN FILE ||` that made the edit idempotent - and it carries the file the
    grep NAMES, because that is the file whose content decides.
    """
    ops = []
    guard_re = (r"""(?:grep(?:\s+-[a-zA-Z]+)*\s+(['"])(.*?)\1\s+(\S+)\s*\|\|\s*)?"""
                r"""sed\s+-i(\.\S+)?(?:\s+-[a-zA-Z]+)*\s+""")
    for m in re.finditer(
            guard_re + r"""(['"])s(.)(.*?)(?<!\\)\6(.*?)(?<!\\)\6([gi]*)\5\s+(\S+)""",
            command, re.S):
        delim, pat, rep, flags = m.group(6), m.group(7), m.group(8), m.group(9)
        rep = rep.replace("\\" + delim, delim)
        rep = re.sub(r"(?<!\\)&", r"\\g<0>", rep)
        guard = (_bre_to_py(m.group(2)), m.group(3)) if m.group(1) else None
        # THE FILE TOKEN IS UNQUOTED. `sed -i '...' "$S/harvest.py"` names the file in
        # quotes; kept, the quote made the expanded path end in `"` and match nothing.
        ops.append((m.start(), m.group(10).strip("'\""), m.group(4), "subst",
                    (_bre_to_py(pat.replace("\\" + delim, delim)), rep, "g" in flags),
                    guard))
    for m in re.finditer(
            guard_re + r"""(['"])\s*(\d+)\s*([ia])\s?(.*?)\5\s+(\S+)""",
            command, re.S):
        guard = (_bre_to_py(m.group(2)), m.group(3)) if m.group(1) else None
        ops.append((m.start(), m.group(9).strip("'\""), m.group(4), "line",
                    (int(m.group(6)), m.group(7), m.group(8)), guard))
    return sorted(ops)


def apply_sed(text, kind, payload):
    """-> `text` after ONE sed operation, with sed's own semantics.

    A substitution without `g` replaces the first match ON EVERY LINE, not the first
    match in the file; treating the file as one string silently drops every later line's
    edit. A line address that does not exist runs no cycle at all, so an out-of-range
    or empty-file `i`/`a` inserts NOTHING rather than clamping to an end that invents a
    line the era never had.
    """
    if kind == "subst":
        pat, rep, glob = payload
        return "".join(re.sub(pat, rep, ln, count=0 if glob else 1)
                       for ln in text.splitlines(True))
    lineno, where, ins = payload
    lines = text.splitlines(True)
    if not lines or lineno < 1 or lineno > len(lines):
        return text
    at = lineno - 1 if where == "i" else lineno
    if at == len(lines) and lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return "".join(lines[:at]) + ins + "\n" + "".join(lines[at:])


#: `cp SRC DST`, `mv SRC DST`, `cp -f SRC DST`, `install -D -m 644 SRC DST`: one copy
#: each. Flags were invisible before, so a flagged copy replaced nothing.
_COPY_RE = r"^\s*(?:cp|mv|install)(?:\s+-[A-Za-z]+(?:\s+[0-7]{3,4})?)*\s+\"?([^\"\s]+)\"?\s+\"?([^\"\s]+)\"?\s*$"

#: -> the files under a scratch tree that differ from their committed base before a
#: record: installed by chrono_replay, measured from the transcript, never listed by hand
TREE_MODIFIED = None

_SEED_LOOP = re.compile(
    r"git\s+(?:-C\s+\"?([^\"\s|]+)\"?\s+)?status\s+--porcelain\s*"
    r"((?:\|(?!\s*(?:awk|sed)\b)[^|\n]*\s*\\?\s*)*)\|\s*"
    r"(?:awk\s+'\$1==\"M\"\{print \$2\}'|sed\s+'s/\^\.\.\.//')\s*\|\s*"
    r"while\s+read\s+(?:-r\s+)?(\w+)\s*;\s*do\s+(.*?)\s*;?\s*done", re.S)

_FOR_LOOP = re.compile(r"for\s+(\w+)\s+in\s+((?:[^\s;]+\s+)*[^\s;]+)\s*;\s*do\s+(.*?)\s*;?\s*done", re.S)

_COPY_IN_BODY = re.compile(r"(?:cp|install)(?:\s+-[A-Za-z]+(?:\s+[0-7]{3,4})?)*\s+\"?([^\"\s;]+)\"?\s+\"?([^\"\s;]+)\"?")

#: `cp -r SRC DST` / `cp -a SRC DST`, anywhere in a line (the campaign joined its steps
#: with `&&`), a directory copied whole
_DIR_COPY = re.compile(r"(?:^|[;&|]\s*)cp\s+-[a-zA-Z]*[ra][a-zA-Z]*\s+\"?([^\"\s;&|]+)\"?\s+\"?([^\"\s;&|]+)\"?(?=\s*(?:$|[;&|]))", re.M)


def _abs(path, cwd):
    return path if os.path.isabs(path) or not cwd else os.path.normpath(os.path.join(cwd, path))


def seed_copies(command, line, start=None):
    """-> [(src, dst)] for every file a shell LOOP or DIRECTORY COPY moved.

    The campaign built each new scratch tree from its predecessor's working state:
    `for f in a.py b.py ...; do cp OLD/$H/$f NEW/$H/$f; done` (records 7192, 8291),
    `git status --porcelain | ... | sed 's/^...//' | while read -r f; do cp -a
    "$SRC/$f" "$DST/$f"; done` (10162), `git -C $OLD status --porcelain | awk
    '$1=="M"{print $2}' | while read p; do install -D -m 644 "$OLD/$p" "$NEW/$p"; done`
    (13156), and `cp -r OLD/.../launchers NEW/.../launchers`. Each is one copy per
    file; which files a status loop moved is what `git status` printed - the source
    tree's files that differed from their commit, which the world answers from the
    transcript alone - and which files a directory copy moved is what the world holds
    under that directory. Nothing is listed by hand.
    """
    env = shell_vars(command)
    out = []
    for m in _FOR_LOOP.finditer(command):
        var, words, body = m.group(1), m.group(2).split(), m.group(3)
        cwd = cwd_at(command, m.start(), start)
        for c in _COPY_IN_BODY.finditer(body):
            if ("$" + var) not in c.group(1) or ("$" + var) not in c.group(2):
                continue
            for w in words:
                w = expand(w, env)
                src = expand(c.group(1).replace("${%s}" % var, w).replace("$" + var, w), env)
                dst = expand(c.group(2).replace("${%s}" % var, w).replace("$" + var, w), env)
                out.append((_abs(src, cwd), _abs(dst, cwd)))
    if TREE_MODIFIED is not None:
        for m in _SEED_LOOP.finditer(command):
            cwd = cwd_at(command, m.start(), start)
            src_tree = expand(m.group(1), env) if m.group(1) else cwd
            if not src_tree:
                continue
            src_tree = src_tree.rstrip("/")
            tracked_only = "awk" in m.group(0)
            excluded = [expand(x, env) for x in re.findall(r"grep\s+-v\s+\"\^\?\? ([^\"]+)\"", m.group(2) or "")]
            var, body = m.group(3), m.group(4)
            for c in _COPY_IN_BODY.finditer(body):
                src_t, dst_t = expand(c.group(1), env), expand(c.group(2), env)
                tail = "$" + var
                if tail not in src_t or tail not in dst_t:
                    continue
                src_root = _abs(src_t.split(tail)[0].rstrip("/"), cwd)
                dst_root = _abs(dst_t.split(tail)[0].rstrip("/"), cwd)
                if src_root != src_tree:
                    continue
                for rel, tracked in sorted(TREE_MODIFIED(src_tree, line, True)):
                    if tracked_only and not tracked:
                        continue
                    if not tracked and any(rel.startswith(x) for x in excluded):
                        continue
                    out.append((src_root + "/" + rel, dst_root + "/" + rel))
                break
    for m in _DIR_COPY.finditer(command):
        cwd = cwd_at(command, m.start(), start)
        src_dir, dst_dir = _abs(expand(m.group(1), env), cwd), _abs(expand(m.group(2), env), cwd)
        if src_dir.endswith("."):
            src_dir = src_dir[:-1].rstrip("/")
        for rel in _dir_files(src_dir, line):
            out.append((src_dir + "/" + rel, dst_dir + "/" + rel))
    return out


def copy_destinations_may_name(command, target_path, start=None):
    """True when some copy destination in the command's loops or directory copies could
    be this owner: its directory (with the loop variable stripped) is a prefix of the
    owner's tree-qualified path. A cheap gate before the loops are expanded."""
    env = shell_vars(command)
    tree_dir = os.path.dirname(target_path)
    dsts = []
    for m in _FOR_LOOP.finditer(command):
        for c in _COPY_IN_BODY.finditer(m.group(3)):
            dsts.append((c.group(2), m.start(), "$" + m.group(1)))
    for m in _SEED_LOOP.finditer(command):
        for c in _COPY_IN_BODY.finditer(m.group(4)):
            dsts.append((c.group(2), m.start(), "$" + m.group(3)))
    for m in _DIR_COPY.finditer(command):
        dsts.append((m.group(2), m.start(), None))
    for dst, pos, var in dsts:
        d = expand(dst, env)
        if var:
            d = d.split(var)[0]
        d = _abs(d.rstrip("/"), cwd_at(command, pos, start)).rstrip("/")
        if not d:
            continue
        if d.endswith("/" + tree_dir) or ("/" + tree_dir + "/") in (d + "/") or tree_dir.startswith(d.lstrip("/")):
            return True
        # the owner's tree root may be deeper than the copy's root (a directory copy
        # of a parent), or the copy's root deeper than the owner's tree (a subdirectory)
        parts = target_path.split("/")
        if any(d.endswith("/" + "/".join(parts[:k])) for k in range(1, len(parts))):
            return True
    return False


def _seed_tree(path):
    """-> the seeded scratch tree `path` lies under, or None.

    THE CLIMB STOPS AT THE ROOT. `dirname("/")` is "/" again, so a source outside
    every seeded tree - the harvest era copied launch files from the repository
    checkout - climbed for ever: ledger recoveries 11 and 14 spent hours there."""
    tree = path
    while tree and tree != "/" and not (os.path.basename(tree).startswith("step1_")
                                        or os.path.basename(tree).startswith("bench_")):
        tree = os.path.dirname(tree)
    return tree if tree and tree != "/" else None


def _dir_files(src_dir, line):
    """-> relative names of every file the world holds under `src_dir` at `line`:
    the committed listing of that directory plus the files the transcript wrote there."""
    names = set()
    kids = _committed_children(src_dir)
    for nm in kids or []:
        sub = _committed_children(src_dir + "/" + nm)
        if sub:
            for nm2 in sub:
                names.add(nm + "/" + nm2)
        else:
            names.add(nm)
    if TREE_MODIFIED is not None:
        tree = _seed_tree(src_dir)
        if tree:
            prefix = os.path.relpath(src_dir, tree) + "/"
            for rel, _tracked in TREE_MODIFIED(tree, line, True, prefix):
                if rel.startswith(prefix):
                    names.add(rel[len(prefix):])
    return sorted(names)



def _shell_compose(rec, basename, side, window=None, line=None):
    """-> the file's new text when a saved command builds it with shell operations.

    The campaign composed files with ordinary shell steps, in order:
      * `cp SRC DST` / `mv SRC DST` REPLACES the file (this is how it was truncated
        to a slice that an earlier record had written out);
      * `cat >> DST <<'TAG' ... TAG` appends the heredoc's exact bytes;
      * `cat SECTION >> DST` appends a section file written earlier in the command.
    Only operations whose destination resolves to this file are applied, and the
    sources come from the in-memory scratch filesystem, never from disk. A command
    with none of these shapes returns None rather than being guessed at.
    """
    try:
        cmd = bash_command(rec)
    except TranscriptError:
        return None
    # PRECEDENCE. A command may both run a python program that rewrites this file
    # and use shell composition on it. The program is the richer description and
    # historically ran in the same command, so when both are present the composer
    # defers and the program is replayed instead of appending on top of it.
    # THE POSITION COMES FROM THE MATCH, NOT FROM SEARCHING FOR THE SOURCE. A `-c`
    # program is shell-expanded before it is replayed, so looking the source text up
    # in the command failed and the whole command looked program-free - which applied
    # a post-program append a second time, ahead of the program that was to cut it.
    spans = program_spans(cmd)
    prog_pos = spans[0][0] if spans else -1
    text, touched = None, False
    bodies = {}
    for m in re.finditer(r"cat\s+>\s*\"?([^\"\s]+)\"?\s*<<'([A-Za-z0-9_]+)'\n(.*?)\n\2\n",
                         cmd, re.S):
        bodies[m.group(1)] = m.group(3)
    ops = []
    for m in re.finditer(_COPY_RE,
                         cmd, re.M):
        ops.append((m.start(), "replace", m.group(1), m.group(2)))
    # A TREE SEEDED FROM ANOTHER TREE, A LOOP OF COPIES, A DIRECTORY COPY: one copy
    # per file, in command order
    for src, dst in seed_copies(cmd, line, rec.get("cwd") if isinstance(rec, dict) else None):
        ops.append((0, "replace", src, dst))
    # `cat > DST <<'TAG'` CREATES DST from the heredoc's exact bytes. This is how files
    # that have no committed base were written during the era; without it such a file
    # could never be served to the record that later reads it.
    for m in re.finditer(r"cat\s+>\s*\"?([^\"\s]+)\"?\s*<<'([A-Za-z0-9_]+)'\n(.*?)\n\2\n",
                         cmd, re.S):
        ops.append((m.start(), "replace_literal", m.group(3), m.group(1)))
    for m in re.finditer(r"cat\s+>>\s*\"?([^\"\s]+)\"?\s*<<'([A-Za-z0-9_]+)'\n(.*?)\n\2\n",
                         cmd, re.S):
        ops.append((m.start(), "append_literal", m.group(3), m.group(1)))
    for m in re.finditer(r"cat\s+\"?([^\"\s]+)\"?\s*>>\s*\"?([^\"\s]+)\"?", cmd):
        ops.append((m.start(), "append_file", m.group(1), m.group(2)))
    # `cat SRC > DST` REPLACES DST. This is how the campaign truncated the owner back
    # to a slice it had just written out. Modelling only `cp` missed it, so the
    # truncation never happened and every later block piled on top of a stale copy -
    # which is exactly what duplicated whole sections of this file.
    for m in re.finditer(r"cat\s+((?:[^\s>|]+[ \t]+)*[^\s>|]+)[ \t]*>(?!>)[ \t]*\"?([^\"\s]+)\"?",
                         cmd):
        # `cat A B > DST` CONCATENATES, in order: the first source replaces the file and
        # each further source is appended. This is how a file was rebuilt from a sliced
        # head plus a body written separately.
        srcs = m.group(1).split()
        ops.append((m.start(), "replace", srcs[0], m.group(2)))
        for i, extra in enumerate(srcs[1:], 1):
            ops.append((m.start() + i, "append_file", extra, m.group(2)))
    if window is not None:
        # THE PROGRAM IS NOT THE END OF THE COMMAND. A command commonly cut the file
        # with a program and then appended the replacement block with the shell; only
        # applying what PRECEDED the program silently dropped that block. The caller
        # replays the two sides around the program, in command order.
        ops = [o for o in ops if window[0] <= o[0] < window[1]]
    elif prog_pos >= 0:
        ops = [o for o in ops if o[0] < prog_pos]
    # PATHS ARE EXPANDED, THE BODIES ARE NOT. A single-quoted heredoc was NOT expanded
    # by the shell, so expanding the whole command would corrupt content that contains
    # a `$`. Only the operation's own paths are resolved.
    env = shell_vars(cmd)
    for _pos, kind, src, dst in sorted(ops):
        dst = expand(dst, env)
        if kind != "append_literal" and kind != "replace_literal":
            src = expand(src, env)
        # AN ABSOLUTE DESTINATION NAMES ITS OWN TREE (see chrono_replay._dst_is_owner):
        # matching it on the bare filename let a copy INTO ANOTHER TREE overwrite this
        # owner with a sibling tree's bytes.
        if dst.startswith("/"):
            if not dst.endswith(basename):
                continue
        elif not (dst.endswith(basename) or dst.endswith(os.path.basename(basename))):
            continue
        if text is None:
            text = side.get("__owner__", "")
        if kind == "replace":
            body = _resolve_source(src, side, line)
            if body is None:
                return None
            text, touched = body, True
        elif kind == "append_literal":
            text, touched = text + src + "\n", True
        elif kind == "replace_literal":
            text, touched = src + "\n", True
        else:
            body = bodies.get(src)
            if body is None:
                body = _resolve_source(src, side, line, bodies)
            if body is None:
                return None
            # `cat A B` JOINS RAW BYTES. A body that came from a FILE already carries
            # its own trailing newline, and adding another left the result one byte
            # long - byte-identical content that still missed its digest. A heredoc
            # body, whose terminator the pattern consumed, does need one.
            text = text + body if body.endswith("\n") else text + body + "\n"
            touched = True
    return text if touched else None


def _shell_append(rec, basename):
    """-> text a saved command appends to `basename` by shell composition.

    The campaign added whole sections with `cat > SECTION <<'TAG' ... TAG` followed by
    `cat SECTION >> .../<basename>`. That is an append of the heredoc's exact bytes, and
    it is replayed as one. Anything else about the command is ignored, and a command that
    does not have this exact shape returns None rather than being guessed at.
    """
    try:
        cmd = bash_command(rec)
    except TranscriptError:
        return None
    # the one-step form: `cat >> <target> <<'TAG' ... TAG` appends the heredoc itself
    for m in re.finditer(
            r"cat\s+>>\s*\"?([^\"\s]+)\"?\s*<<'([A-Za-z0-9_]+)'\n(.*?)\n\2\n",
            cmd, re.S):
        if m.group(1).endswith(basename):
            return m.group(3) + "\n"
    # the two-step form: write a section file, then append that file
    bodies = {}
    for m in re.finditer(r"cat\s+>\s*\"?([^\"\s]+)\"?\s*<<'([A-Za-z0-9_]+)'\n(.*?)\n\2\n",
                         cmd, re.S):
        bodies[m.group(1)] = m.group(3)
    for m in re.finditer(r"cat\s+\"?([^\"\s]+)\"?\s*>>\s*\"?([^\"\s]+)\"?", cmd):
        src, dst = m.group(1), m.group(2)
        if not dst.endswith(basename):
            continue
        for name, body in bodies.items():
            if name.split("/")[-1] == src.split("/")[-1]:
                return body + "\n"
    return None


def _reader(text, mode):
    """-> a file object over `text` in the mode the program asked for.

    A BINARY read must give BYTES. Serving text whatever the mode was asked for made
    any program that hashed a file die on the first read - a failure of the replay,
    not of history.
    """
    return io.BytesIO(text.encode("utf-8")) if "b" in mode else io.StringIO(text)


class _Sink(io.StringIO):
    """A writable handle over replayed text.

    APPEND KEEPS WHAT IS THERE. `w` truncates and `a` does not, and the replay served
    the same empty sink for both - so an append to a scratch sibling overwrote it, and
    an append to the OWNER was served a reader and thrown away entirely. Seeding the
    buffer with the existing text and leaving the cursor at its end is the whole of the
    difference; write/truncate behaviour is untouched.
    """

    def __init__(self, setter, existing=""):
        super().__init__(existing or "")
        if existing:
            self.seek(0, os.SEEK_END)
        self._set = setter

    def write(self, s):
        # a binary write arrives as bytes; the scratch filesystem holds text
        n = super().write(s.decode("utf-8") if isinstance(s, bytes) else s)
        self._set(self.getvalue())
        return n

    def close(self):
        if not self.closed:
            self._set(self.getvalue())
        super().close()


#: (basename, state) for each replay currently in progress, outermost first, so a
#: nested read of a file already being replayed is served its in-flight bytes
ACTIVE_OWNERS = []


def active_owner_text(path, before_line=None):
    """-> the in-flight text of a replay whose owner this path names, or None.

    ONLY FOR A CUTOFF AT OR BEYOND THE RECORD BEING APPLIED. The in-flight text is the
    owner's state before the record now running (plus what that record has written so
    far); a nested route asking for an EARLIER state of the same file must not be
    served it. This is the second door the in-flight bytes came through: the
    re-entrant guard refused them, the rebuild it ordered came here, and here they
    were handed over regardless of the cutoff - which is how record 24277 kept
    failing only inside the census while every reproduction outside it passed."""
    for basename, state in reversed(ACTIVE_OWNERS):
        if str(path).endswith(basename) or str(path) == os.path.basename(basename):
            if before_line is not None and before_line < state.get("line", 0):
                return None
            return state["text"]
    return None


def apply_saved_edits(text, records, basename, prepare=None, side=None,
                      result=None):
    """Replay saved edit programs against `text` held in memory.

    `records` is an ordered mapping of transcript line -> record. Every read or write of a
    path ending in `basename` is served from memory; everything else falls through to the
    real filesystem, so the programs still see their genuine inputs. `prepare(line, src)`
    may trim a saved program to the part that owns this file, exactly as the durable
    recipes do.
    """
    state = {"text": text}
    # THE FILE BEING REPLAYED IS ON THE DISK THE PROGRAMS SEE. A record of some OTHER
    # file may read this one, and until now that read triggered a fresh replay of this
    # file from its tree origin - slower, and wrong: what history's program actually
    # read was this file as it stood at that moment, which is exactly `state`. Publish
    # it so a nested read is answered with the bytes in flight.
    ACTIVE_OWNERS.append((basename, state))
    try:
        return _replay(state, records, basename, prepare, side, result)
    finally:
        ACTIVE_OWNERS.pop()


import contextlib as _contextlib


@_contextlib.contextmanager
def _shim_off():
    """Run replay machinery from inside a program: the guard makes every open real."""
    _MACHINERY[0] += 1
    try:
        yield
    finally:
        _MACHINERY[0] -= 1


def _present(text):
    """A module source is present when it is not None: "" is an empty module, as
    package markers usually are; None is absence."""
    return text is not None


def _refuse_live_only(name, root):
    """A module only the live filesystem provides is refused, and the ask recorded."""
    IMPORT_MISSES.append((name, root))
    raise ModuleNotFoundError("%s is outside the replay world (%s)" % (name, root))


#: THE FILESYSTEM QUESTIONS A PROGRAM ASKS ARE ANSWERED BY THE REPLAY WORLD TOO.
#: Served modules do not only open files: they ask whether a path exists, list a
#: directory, walk a tree. `unit_resolver` walks upward from its own file looking for a
#: scripts directory; under the vanished scratch tree every candidate is absent on this
#: box while history had it. For an OUTSIDE path these questions are answered from the
#: side table, the mounts and the committed store - never from the live filesystem -
#: exactly as opens are (Codex SEQ 1559 item 1).
def _committed_children(path):
    """-> the names directly under `path` in the worktree commit, by the same
    directory-qualified suffix rule `_committed` uses, or None when the commit has no
    such directory."""
    try:
        commit = _full_commit(WORKTREE_COMMIT)
    except RuntimeError:
        return None
    if commit not in _TREE:
        tree = os.path.join(GIT_BASES, commit + ".tree")
        if not os.path.isfile(tree):
            return None
        _TREE[commit] = set(n for n in _REAL_IO_OPEN(tree, encoding="utf-8").read().split("\n") if n)
    parts = str(path).strip("/").split("/")
    names = _TREE[commit]
    for i in range(len(parts)):
        if len(parts) > 1 and i == len(parts) - 1:
            break
        rel = "/".join(parts[i:]) + "/"
        kids = {n[len(rel):].split("/", 1)[0] for n in names if n.startswith(rel)}
        if kids:
            return sorted(kids)
    return None


def _mount_target(sp):
    for root, dest in MOUNTS.items():
        if sp == root or sp.startswith(root + "/"):
            return os.path.join(dest, os.path.relpath(sp, root)) if sp != root else dest
    return None


def w_sleep(seconds):
    """A replayed program's sleep: nothing in the world changes while it waits."""
    return None


def _world_isfile(sp, side):
    if isinstance(side.get(sp), str):
        return True
    mt = _mount_target(sp)
    if mt is not None:
        if os.path.isfile(mt):
            return True
        # A STAT MISS IS A MISS. The harvest program asked `isfile` before opening,
        # so an absent state file never reached `_mounted` and was never recorded;
        # the recovery tool that copies missing mount files had nothing to copy.
        MOUNT_MISSES.append(sp)
    try:
        return _committed(sp) is not None
    except RuntimeError:
        return False


def _world_isdir(sp, side):
    prefix = sp.rstrip("/") + "/"
    if any(isinstance(k, str) and k.startswith(prefix) for k in side):
        return True
    mt = _mount_target(sp)
    if mt is not None and os.path.isdir(mt):
        return True
    return _committed_children(sp) is not None


def _world_listdir(sp, side):
    prefix = sp.rstrip("/") + "/"
    names = {k[len(prefix):].split("/", 1)[0] for k in side
             if isinstance(k, str) and k.startswith(prefix)}
    mt = _mount_target(sp)
    if mt is not None and os.path.isdir(mt):
        names |= set(os.listdir(mt))
    kids = _committed_children(sp)
    if kids:
        names |= set(kids)
    if not names and not _world_isdir(sp, side):
        raise FileNotFoundError(errno.ENOENT, "not part of the replay world", sp)
    return sorted(n for n in names if n and not n.startswith("__"))


def _root_dir(root, cwd):
    """A relative import root (`sys.path.insert(0, '.')`, `'../../..'`) is the program's
    own directory relative to where its command stood; served modules take their
    `__file__` from it, so it must be absolute in the world, never left relative."""
    root = str(root)
    if os.path.isabs(root) or not cwd:
        return root
    return os.path.normpath(os.path.join(cwd, root))


def _own_roots(here):
    """The program's own directory - where its command stood when it ran - is the
    first import root; a later `cd` in the same command is not where it stood."""
    return [here] if here else []


class _SiblingFinder(object):
    """Serve `import X` from the sibling `X.py` the executing tree actually had.

    THE SAME RULE THE READ SHIM ALREADY APPLIES. Python's import machinery never calls
    the `open` the shim replaces, so a program that imported a sibling died with
    ModuleNotFoundError even though the replay could serve that exact file - the last
    refusal where history had succeeded. Nothing is invented: a module is served only
    when a sibling of that name resolves in one of THIS program's own directories, and
    a name nothing provides still raises.
    """

    def __init__(self, roots, side, line, cwd=None):
        self.roots, self.side, self.line, self.cwd = roots, side, line, cwd

    def find_spec(self, name, path=None, target=None):
        """A module is served from the replay world or it is absent. IMPORTS FROM THE
        DIRTY CHECKOUT were the last read outside the package: a program that did
        `sys.path.insert(0, "/home/faisal/EventMarketDB")` and imported `driver.core`
        had Python's own finder read the live tree - 875 opens the OS-level audit
        counted (Codex SEQ 1559 item 1). Every candidate location outside the package
        - this program's own roots, the parent package's path, any outside sys.path
        entry - is resolved through the side table, the resolver, the git store and
        the mounts; a module that only the live filesystem could provide is refused."""
        import importlib.util
        import importlib.machinery
        last = name.rsplit(".", 1)[-1]
        here = self.cwd() if callable(self.cwd) else self.cwd
        own = _own_roots(here)
        roots = list(path) if path is not None else \
            [r for r in (_root_dir(x, here) for x in own + list(self.roots) + list(sys.path) if x)
             if _outside(r)]
        for root in roots:
            root = str(root)
            if not _outside(root):
                continue
            for rel, is_pkg in ((last + ".py", False),
                                (os.path.join(last, "__init__.py"), True)):
                path_ = os.path.join(root, rel)
                # AN EMPTY FILE IS A PRESENT FILE. `driver/__init__.py` is zero bytes in
                # the commit, as package markers usually are; "" is a module, None is
                # absence, and treating them alike refused the whole package.
                with _shim_off():
                    try:
                        text = _resolve_source(path_, self.side, self.line)
                    except RuntimeError:
                        text = None
                    if text is None:
                        text = _mounted(path_)
                if _present(text):
                    spec = importlib.util.spec_from_loader(
                        name, _SiblingLoader(name, text, path_), is_package=is_pkg)
                    if is_pkg:
                        spec.submodule_search_locations = [os.path.dirname(path_)]
                    return spec
        # A NAMESPACE PACKAGE IS A DIRECTORY WITH NO MARKER. `driver/relocation` has
        # twenty-five modules and no __init__.py; Python's own finder serves it from
        # the filesystem, so the replay serves it from the world's view of that
        # directory - side table, mount or committed tree - with no loader.
        for root in roots:
            root = str(root)
            if _outside(root):
                with _shim_off():
                    is_dir = _world_isdir(os.path.join(root, last), self.side)
                if is_dir:
                    spec = importlib.machinery.ModuleSpec(name, None, is_package=True)
                    spec.submodule_search_locations = [os.path.join(root, last)]
                    return spec
        # nothing durable provides it; if the live filesystem would, refuse rather
        # than let Python's finder read outside the package - and RECORD what was
        # asked for, so the store can be extended from a measurement, never a list
        for root in roots:
            root = str(root)
            if _outside(root) and (os.path.isfile(os.path.join(root, last + ".py"))
                                   or os.path.isfile(os.path.join(root, last, "__init__.py"))):
                _refuse_live_only(name, root)
        return None


class _SiblingLoader(object):
    def __init__(self, name, source, path):
        self.name, self.source, self.path = name, source, path

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        # a real loader gives the module its own `__file__`; era modules compute
        # paths from it, and without it they raise NameError instead of running
        module.__file__ = self.path
        SERVED_MODULES.append(self.name)
        exec(compile(self.source, "<sibling:%s>" % self.name, "exec"),
             module.__dict__)


class _WorldEntry(object):
    """What `os.scandir` yields, answered by the world: `glob` walks directories through
    `os.scandir`, so without this a pattern like `runs/x/*.json` silently matched the
    live box - empty once /tmp was gone - while `os.listdir` of the same directory
    answered from the world."""

    def __init__(self, parent, name, side):
        self.name = name
        self.path = os.path.join(parent, name)
        self._side = side

    def is_dir(self, follow_symlinks=True):
        return _world_isdir(self.path, self._side)

    def is_file(self, follow_symlinks=True):
        return not self.is_dir()

    def is_symlink(self):
        return False

    def __fspath__(self):
        return self.path


def _world_entries(parent, side):
    return [_WorldEntry(parent, nm, side) for nm in _world_listdir(parent, side)]


class _WorldScandir(object):
    def __init__(self, parent, side):
        self._it = iter(_world_entries(parent, side))

    def __iter__(self):
        return self._it

    def __next__(self):
        return next(self._it)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass


def _world_scandir(sp, side):
    return _WorldScandir(sp, side)


def _replay(state, records, basename, prepare, side, result):
    side = {} if side is None else side
    steps = collections.OrderedDict()
    # the shim always restores what it found, but it FALLS BACK to the true
    # openers, so a nested replay can never chain one shim into another
    real_open = io.open
    real_builtin = builtins.open
    for n, rec in records.items():
        state["line"] = n          # the record now being applied, for active_owner_text
        # AN EDIT RECORD IS A SAVED EDIT TOO. The transcript records a file change
        # either as an Edit (old_string -> new_string) or as a program that rewrites
        # the file; both are replayed, and an Edit whose anchor is not present
        # exactly once refuses rather than guessing.
        # A SIBLING IN A TREE IS RE-RESOLVED FOR EVERY RECORD. Its own history keeps
        # moving between this owner's records, so a copy kept from an earlier record is
        # stale by the time a later one reads it. Intermediates the replay itself
        # produced (a slice under the scratch root, with no tree and no route of their
        # own) are NOT dropped: nothing could rebuild them.
        # Marked, not discarded: a re-resolution is preferred, but if the sibling has
        # no route of its own the copy already in hand is still the best evidence.
        side["__stale__"] = set(k for k in side
                                if isinstance(k, str) and "scratchpad/" in k)
        # THE SHELL MAY NOT HAVE SURVIVED THIS COMMAND, AND THAT IS DECIDED FIRST.
        # When the saved result is nothing but a termination status, NO step of the
        # command ran - not the shell composition either. Checking it after the
        # composer let a killed command still append, inventing a line history never
        # had.
        try:
            _killed = shell_terminated(result if result is not None
                                       else saved_result(n))
        except TranscriptError:
            _killed = False
        if _killed:
            steps[n] = _sha(state["text"])
            continue
        # A REJECTED TOOL CALL DID NOTHING. The harness answers a call it refused -
        # a Bash command that failed input validation, an Edit whose anchor was not
        # found or whose file had moved, a command a hook blocked - with a
        # `<tool_use_error>` and never runs it. Record 25329 was such a Bash call, and
        # replaying its program injected a token the real file never received, which
        # is why the next edit's assertion held in history and failed here.
        _res = result if result is not None else saved_result(n)
        if isinstance(_res, str) and _res.lstrip().startswith("<tool_use_error>"):
            REJECTED_CALLS.append(n)
            steps[n] = _sha(state["text"])
            continue
        side["__owner__"] = state["text"]
        composed = _shell_compose(rec, basename, side, line=n)
        if composed is not None:
            state["text"] = composed
            steps[n] = _sha(state["text"])
            try:
                has_prog = bool(heredoc(bash_command(rec)))
            except TranscriptError:
                has_prog = False
            if not has_prog:
                continue
        # A WRITE OF A SIDE FILE IS A PRODUCER. The intermediate a later record
        # concatenates was often created by the Write tool; it belongs in the in-memory
        # filesystem, not on disk, and it is not an edit of this owner.
        wrote_side = False
        for b in _blocks(rec, "tool_use"):
            if b.get("name") == "Write":
                inp = b.get("input") or {}
                path = str(inp.get("file_path") or "")
                if not path:
                    continue
                if path.endswith(basename):
                    # A WRITE OF THIS FILE IS THE WHOLE FILE. The route selects Write
                    # records, but only Edit and Bash were ever applied, so a file
                    # CREATED by the Write tool never moved off its committed base.
                    state["text"] = inp.get("content") or ""
                else:
                    side[path] = inp.get("content") or ""
                wrote_side = True
        if wrote_side:
            steps[n] = _sha(state["text"])
            continue
        edit = _edit_input(rec, basename)
        if edit is not None:
            old, new, replace_all = edit
            hits = state["text"].count(old)
            if hits == 0 or (hits > 1 and not replace_all):
                raise TranscriptError(
                    "the saved edit at line %d matches its anchor %d times" % (n, hits))
            state["text"] = state["text"].replace(old, new,
                                                  -1 if replace_all else 1)
            steps[n] = _sha(state["text"])
            continue
        cmd_text = bash_command(rec)
        # where the shell stood before its first `cd`: the record's own `cwd`
        _start = rec.get("cwd") if isinstance(rec, dict) else None
        seed_git_show(cmd_text, side)
        spans = program_spans(cmd_text,
                             env=grep_vars(cmd_text, state["text"], basename))
        # ONLY THIS OWNER'S PROCESSES RUN. A Bash call runs several processes, and a
        # sibling process that edits another file is not this owner's business:
        # executing it replayed edits into other trees, and let ITS failure - an
        # unavailable subprocess, a missing module - erase a write a selected process
        # had already made. Producers this owner's processes read are kept.
        if SELECT_UNITS is not None and len(spans) > 1:
            keep = SELECT_UNITS(cmd_text, basename, n, _start)
            if keep:
                spans = [sp for i, sp in enumerate(spans) if i in keep]
        progs = [s[2] for s in spans]
        # A COMMAND THAT RUNS A SAVED SCRIPT OWNS THAT SCRIPT'S WRITES. One record
        # writes a helper and a later one executes it; the consumer never names this
        # owner, so without resolving the script every edit it makes is lost.
        script_texts = _executed_scripts(cmd_text, n)
        script_argv = [a for a, tx in zip(_executed_script_argv(cmd_text), script_texts) if tx]
        progs += [tx for tx in script_texts if tx]
        if prepare is not None:
            progs = [prepare(n, s) for s in progs]

        # THE PROGRAM MAY OPEN THIS OWNER BY A RELATIVE NAME after the command
        # cd-ed into a parent directory. Resolving that here is what lets such a
        # record be replayed at all: the shim serves by suffix, and a bare
        # `harness/<name>` matches no tree-qualified owner without this.
        # POSITIONS ARE READ FROM THE RAW COMMAND, values expanded individually, so
        # these offsets share one coordinate system with the program spans below.
        # Expanding the whole command first shifts every offset by the length of the
        # substitutions and silently mis-orders the two against each other.
        _env_x = shell_vars(cmd_text)
        # THE SHELL STARTED SOMEWHERE, AND THE RECORD SAYS WHERE. Every saved call
        # carries the session's working directory (`cwd`); a command with no `cd` of
        # its own ran there - record 22655 imported `driver.core` through a bare
        # `sys.path.insert(0, '.')` from /home/faisal/EventMarketDB. With no start the
        # program's directory was unknown, its relative roots stayed relative, and two
        # modules of one package were served under two spellings of the same path.
        _cds = [(-1, _start)] if _start and os.path.isabs(str(_start)) else []
        for m in re.finditer(r'''cd\s+("[^"]+"|'[^']+'|\S+)''', cmd_text):
            _d = expand(m.group(1).strip("\"'"), _env_x)
            if not os.path.isabs(_d):
                _prev = [d for _p, d in _cds if d.startswith("/")]
                _d = os.path.normpath(os.path.join(_prev[-1], _d)) if _prev else _d
            _cds.append((m.start(), _d))
        #: where the program now running sat in the command, so a relative open is
        #: resolved through the `cd` that PRECEDED it rather than through any `cd`
        #: anywhere in the command
        _at = [len(cmd_text)]

        def _cwd_now():
            prior = [d for p, d in _cds if p < _at[0] and d.startswith("/")]
            return prior[-1] if prior else None

        def _is_owner(sp):
            if sp == os.path.basename(basename) or sp.endswith(basename):
                return True
            # A RELATIVE OPEN IS RESOLVED THROUGH THE COMMAND'S OWN `cd`. The shim
            # serves files by path suffix, so a bare `harness/<name>` matched no
            # tree-qualified owner and the record raised instead of being replayed.
            # ORDER IS PART OF THE RESOLUTION: one command cd-ed into several trees,
            # and taking ANY of them resolved a relative name into a tree the program
            # was not standing in - which silently rewrote a different copy.
            if not os.path.isabs(sp):
                d = _cwd_now()
                return bool(d) and os.path.join(d, sp).endswith(basename)
            return False

        def _mode_of(mode, args, kwargs):
            extra = args[0] if args and isinstance(args[0], str) else \
                kwargs.get("mode", "")
            return (mode if isinstance(mode, str) else "") + extra

        def fake_open(path, mode="r", *args, **kwargs):

            if _MACHINERY[0]:

                return _REAL_IO_OPEN(path, mode, *args, **kwargs)
            # A MEMORY FILESYSTEM FOR THE WIPED SCRATCH ROOT. Some saved programs
            # derive an intermediate file from the owner (slice it out, write it,
            # read it back). Those files are deterministic products of the replay,
            # not external inputs, so they live in memory beside the owner and are
            # never written to disk.
            sp = str(path)
            # A RELATIVE OPEN IS RESOLVED FOR SIBLINGS TOO, but ONLY INTO THIS OWNER'S
            # OWN TREE. A record that cd-ed into the experiments directory and edited
            # several files by a relative name reaches the real filesystem for every
            # file that is not this owner, and that filesystem is gone, so the program
            # dies on the FIRST sibling and never makes its later edits (record 29136
            # is the worked example). Resolving through ANY `cd` is what went wrong the
            # first time: it pulled files into trees they were never written in and
            # took the step1_iso guard from five of seven era snapshots down to two.
            # The owner is already tree-qualified, so its tree is the only lawful
            # destination, and a join that lands anywhere else is left alone.
            # A RELATIVE OPEN IS RESOLVED FOR SIBLINGS TOO, through the `cd` in force
            # at that point in the command. A record that cd-ed into a directory and
            # read several files by relative name reaches the real filesystem for every
            # file that is not this owner, and that filesystem is gone, so the program
            # dies on the FIRST sibling and never makes its later edits.
            if not os.path.isabs(sp):
                _d = _cwd_now()
                if _d:
                    sp = os.path.normpath(os.path.join(_d, sp))
            if os.path.isabs(sp):
                sp = os.path.normpath(sp)      # `harness/../keys/x` is `keys/x`
            if not _is_owner(sp) and _outside(sp):
                # THE SECOND POSITIONAL ARGUMENT IS NOT ALWAYS A MODE. `open(p, "w", 1)`
                # passes buffering there, and testing `"w" in 1` raises TypeError -
                # which surfaced as a saved program mysteriously failing rather than as
                # a bug here. Only a string can carry a mode.
                _extra = args[0] if args and isinstance(args[0], str) else \
                    kwargs.get("mode", "r")
                if any(m in _extra for m in ("w", "a", "x")) \
                        or "w" in mode or "a" in mode:
                    # what the replay writes is authoritative: drop any seeded mark so
                    # a later read never discards it for a re-resolved copy
                    side.setdefault("__seeded__", {}).pop(sp, None)
                    # A WRITE THIS RECORD MAKES IS AUTHORITATIVE FOR THE REST OF THE
                    # RECORD. Every scratch-path copy is marked stale when a record
                    # begins, so that a later record re-resolves it; but a program
                    # that writes a sibling and reads it back in the same breath
                    # (record 24277 renamed a token in build_launch_manifest.py, then
                    # re-read it to edit further) must see ITS OWN bytes, not the
                    # resolver's pre-write text - which is what the stale mark sent it
                    # back to, and why its anchor was "missing" only when the sibling
                    # had been touched earlier in this owner's route.
                    side.setdefault("__stale__", set()).discard(sp)
                    keep = side.get(sp, "") if "a" in _extra or "a" in mode else ""
                    return _Sink(lambda v, k=sp: side.__setitem__(k, v), keep)
                # A SEEDED SIBLING GOES STALE. It was resolved as of an EARLIER
                # record; a later record needs that file as it stood later. Caching by
                # path alone froze it, so a record read an older sibling and its
                # anchors no longer matched. A file this replay WROTE is authoritative
                # and is never refreshed - only a seeded one is.
                seeded_at = side.setdefault("__seeded__", {})
                stale = side.setdefault("__stale__", set())
                if sp in side and sp not in ("__seeded__", "__stale__"):
                    if sp not in stale and seeded_at.get(sp, n) >= n:
                        return _reader(side[sp], _mode_of(mode, args, kwargs))
                # THE SHIM MUST BE OFF WHILE THE REPLAY'S OWN MACHINERY RUNS.
                # Resolving a sibling reads the commit through `git show`, and
                # subprocess opens files of its own - which came straight back into
                # this shim, which resolved again, without end. The saved program is
                # what the shim exists to serve; the replay's own reads are not.
                seeded = None
                io.open, builtins.open = _REAL_IO_OPEN, _REAL_BUILTIN_OPEN
                try:
                    if SIBLING_RESOLVER is not None:
                        seeded = SIBLING_RESOLVER(sp, n)
                    if seeded is None:
                        seeded = _committed(sp)
                    if seeded is None:
                        seeded = _mounted(sp)
                finally:
                    io.open, builtins.open = fake_open, fake_open
                if seeded is not None:
                    side[sp] = seeded
                    seeded_at[sp] = n
                    stale.discard(sp)
                    return _reader(seeded, _mode_of(mode, args, kwargs))
                if sp in side and sp not in ("__seeded__", "__stale__"):
                    return _reader(side[sp], _mode_of(mode, args, kwargs))   # nothing better
            # PATH-AWARE, not name-aware. Several copies of the same file existed
            # side by side (harness, harness_g1v2, harness_g1v3, iso trees); a
            # record editing another copy must not touch this one. `basename` may
            # carry leading directories to discriminate, and a bare name still
            # matches the relative use a program makes after cd-ing into its dir.
            if _is_owner(sp):
                _m = _mode_of(mode, args, kwargs)
                if "w" in _m:
                    return _Sink(lambda v: state.__setitem__("text", v))
                if "a" in _m:
                    return _Sink(lambda v: state.__setitem__("text", v), state["text"])
                return _reader(state["text"], _m)
            if _outside(sp):
                # THE REPLAY READS AND WRITES NOTHING OUTSIDE THE PACKAGE. A path no
                # owner served is absent for the program - exactly what the vanished
                # tree gives it - and a write to it lands in the side table, never on
                # this box: three two-byte files under /tmp were this replay's own side
                # effects before this rule (Codex SEQ 1559 item 1).
                _m = _mode_of(mode, args, kwargs)
                if any(ch in _m for ch in ("w", "a", "x")):
                    return _Sink(lambda v, k=sp: side.__setitem__(k, v),
                                 side.get(sp, "") if "a" in _m else "")
                raise FileNotFoundError(errno.ENOENT, "not part of the replay world", path)
            return _REAL_IO_OPEN(path, mode, *args, **kwargs)

        # A saved program may take its target from argv (`python3 - "$S/x.py"`).
        # The shim serves the file by basename, so a synthetic path carrying that
        # basename is exactly what the program needs and reaches nothing real.
        # BOTH open functions are served. Saved programs use `io.open` and the
        # builtin `open` interchangeably; patching only one let a record read the
        # real filesystem, which no longer holds this file.
        # A COMMAND OFTEN BACKS THIS FILE UP BEFORE EXPERIMENTING ON IT and copies the
        # backup back when it is done: `cp <owner> <scratch>` ... edit ... `cp <scratch>
        # <owner>`. The composer only ever tracked copies INTO the owner, so the backup
        # was never taken and the restore had nothing to restore from - leaving the
        # experiment's edit in place when history ended with the file untouched.
        for _m in re.finditer(_COPY_RE,
                              cmd_text, re.M):
            _src = expand(_m.group(1), _env_x)
            _dst = expand(_m.group(2), _env_x)
            _at[0] = _m.start()
            if _dst.startswith(SCRATCH_ROOT) and _is_owner(_src):
                side[_dst] = state["text"]
        _at[0] = len(cmd_text)

        io.open = fake_open
        builtins.open = fake_open
        # the filesystem questions, answered by the same world as the opens
        _real_isfile, _real_exists, _real_isdir = os.path.isfile, os.path.exists, os.path.isdir
        _real_listdir, _real_walk = os.listdir, os.walk

        def _w(path):
            sp = str(path)
            if not os.path.isabs(sp):
                _d = _cwd_now()
                if _d:
                    sp = os.path.join(_d, sp)
            # `harness/../keys/K-fields` names the same directory as `keys/K-fields`,
            # but a suffix match against the commit's file list never sees a `..`:
            # the harvest program's INPUTS was answered "absent" for exactly this
            return os.path.normpath(sp) if os.path.isabs(sp) else sp

        def w_isfile(path):
            sp = _w(path)
            if _MACHINERY[0] or not _outside(sp):
                return _real_isfile(path)
            return _is_owner(sp) or _world_isfile(sp, side)

        def w_isdir(path):
            sp = _w(path)
            if _MACHINERY[0] or not _outside(sp):
                return _real_isdir(path)
            return _world_isdir(sp, side)

        def w_exists(path):
            return w_isfile(path) or w_isdir(path)

        def w_listdir(path="."):
            sp = _w(path)
            if _MACHINERY[0] or not _outside(sp):
                return _real_listdir(path)
            return _world_listdir(sp, side)

        def w_walk(top, topdown=True, onerror=None, followlinks=False):
            sp = _w(top)
            if _MACHINERY[0] or not _outside(sp):
                return _real_walk(top, topdown, onerror, followlinks)

            def _gen(d):
                try:
                    names = _world_listdir(d, side)
                except OSError as exc:
                    if onerror is not None:
                        onerror(exc)
                    return
                dirs = [nm for nm in names if _world_isdir(os.path.join(d, nm), side)]
                files = [nm for nm in names if nm not in dirs]
                if topdown:
                    yield d, dirs, files
                for nm in dirs:
                    for item in _gen(os.path.join(d, nm)):
                        yield item
                if not topdown:
                    yield d, dirs, files
            return _gen(sp)

        _real_scandir, _real_lexists = os.scandir, os.path.lexists

        def w_scandir(path="."):
            sp = _w(path)
            if _MACHINERY[0] or not _outside(sp):
                return _real_scandir(path)
            return _world_scandir(sp, side)

        def w_lexists(path):
            sp = _w(path)
            if _MACHINERY[0] or not _outside(sp):
                return _real_lexists(path)
            return w_exists(path)

        os.path.isfile, os.path.exists, os.path.isdir = w_isfile, w_exists, w_isdir
        os.listdir, os.walk = w_listdir, w_walk
        os.scandir, os.path.lexists = w_scandir, w_lexists
        _real_getcwd = os.getcwd

        def w_getcwd():
            # THE PROGRAM STANDS WHERE ITS COMMAND cd-ED, not where the census runs.
            # `os.path.abspath` and `Path.cwd()` ask this; a served module's `__file__`
            # built from a relative sys.path root was absolutised against the census's
            # own directory, and every path derived from it then pointed nowhere.
            d = _cwd_now()
            return d if d and not _MACHINERY[0] else _real_getcwd()
        os.getcwd = w_getcwd
        # THE WORLD IS FIXED, SO A WAIT DECIDES NOTHING. The harvest program polled a
        # workflow state 360 times with `time.sleep(10)` between tries; what it found
        # is the same on the first try as on the last, and a replay that slept the
        # hour on an absent file was not computing anything.
        import time as _time
        _real_sleep = _time.sleep
        _time.sleep = w_sleep
        saved_argv = sys.argv
        sys.argv = ["-", os.path.join("/replay", basename.lstrip("/"))]
        before = state["text"]
        failure = None
        env_limited = False
        saved_sub = sys.modules.get("subprocess")
        sys.modules["subprocess"] = _NoSubprocess()
        # A PROGRAM MAY IMPORT A SIBLING, NOT ONLY OPEN IT. The roots are this
        # program's own: the directory it cd-ed into and the owner's own
        # directory, which is where a sibling of the era lived.
        # ONE cd PER PROCESS, IN ORDER: the program's own directory is where the
        # command stood when THIS program ran (the finder asks `_cwd_now` per import),
        # never where the command ended up after a later cd
        _roots = [os.path.dirname("/replay/" + basename.lstrip("/"))]
        _finder = _SiblingFinder(_roots, side, n, cwd=_cwd_now)
        sys.meta_path.insert(0, _finder)
        try:
            for i, src in enumerate(progs):
                # EACH PROGRAM IS ITS OWN PROCESS. One that raises does not prevent the
                # next from running, exactly as the shell ran them.
                try:
                    _at[0] = spans[i][0] if i < len(spans) else len(cmd_text)
                    # A PROGRAM RUN BY THE MACHINERY IS STILL A PROGRAM. The resolver is a machinery
                    # entry point, so while it replayed a sibling's own records the guard was on and
                    # the shim handed the program's opens to the real filesystem - the sibling's
                    # edits refused on a vanished /tmp path and were swallowed. The guard covers the
                    # machinery's own reads only; a saved program executes with the shim in force.
                    _guard_depth = _MACHINERY[0]
                    _MACHINERY[0] = 0
                    # AN EXECUTED SCRIPT GETS THE ARGUMENTS ITS COMMAND GAVE IT; a
                    # stdin program keeps the owner's synthetic argv.
                    _argv_before = sys.argv
                    if i >= len(spans) and (i - len(spans)) < len(script_argv):
                        sys.argv = list(script_argv[i - len(spans)])
                    elif i < len(spans):
                        # THE ARGUMENTS THE SHELL PASSED. `python - "$RUN" <<'PY'` with
                        # `run = sys.argv[1]` read the synthetic owner path instead, so
                        # every sibling it wrote under that directory landed where no
                        # later record could read it (invrev_run4/plan.json, ...).
                        _real_args = stdin_program_argv(cmd_text, spans[i][0])
                        if _real_args:
                            sys.argv = ["-"] + _real_args
                    # EACH PROGRAM IS ITS OWN PROCESS, for imports too. A program's
                    # sys.path insertions and the sibling modules it loaded used to
                    # persist into the next program of the same replay, where history
                    # gave that program a fresh interpreter: a later program then
                    # imported an earlier program's sibling instead of its own.
                    _path_before = list(sys.path)
                    _served_before = len(SERVED_MODULES)
                    # A PROGRAM'S IMPORTS ARE ITS OWN. History gave every program a
                    # fresh interpreter; a nested replay (a sibling resolved while an
                    # outer program's `import X` is still loading X) must neither see
                    # the outer, half-built X nor take it away: what an outer program
                    # served is hidden while this one runs and put back afterwards,
                    # and what this one served is dropped at its end.
                    _hidden = dict((_m, sys.modules.pop(_m)) for _m in SERVED_MODULES[:_served_before]
                                   if _m in sys.modules)
                    # A MODULE THE PROCESS LOADED FROM THE VENDORED EVIDENCE TREE IS NOT
                    # THIS PROGRAM'S. The census imports the bench harness owners; a
                    # program that then `import kf_lint`s found that real module in
                    # sys.modules and the finder never ran, so the sibling its own world
                    # held was never served. Such modules are hidden for the program's
                    # duration and put back afterwards.
                    for _m, _mod in list(sys.modules.items()):
                        _f = getattr(_mod, "__file__", None)
                        if _f and str(_f).startswith(BENCH_ROOT + os.sep) and _m not in _hidden:
                            _hidden[_m] = sys.modules.pop(_m)
                    try:
                        exec(compile(src, "<transcript:%d:%d>" % (n, i), "exec"),
                             {"__name__": "__replay__"})
                    finally:
                        _MACHINERY[0] = _guard_depth
                        sys.argv = _argv_before
                        sys.path[:] = _path_before
                        for _m in SERVED_MODULES[_served_before:]:
                            sys.modules.pop(_m, None)
                        del SERVED_MODULES[_served_before:]
                        sys.modules.update(_hidden)
                except (Exception, SystemExit) as exc:
                    # SystemExit ends ONE process, not the command: a saved program
                    # that exited did not stop the program that followed it.
                    failure = failure or exc
                    env_limited = env_limited or isinstance(exc, ReplayEnvironmentError)
            # A PROGRAM THIS REPLAY CUT SHORT LEAVES NO HALF-EDIT. These programs
            # commonly keep the original text, edit the file, observe the result and
            # then write the original back; stopping at the observation keeps an edit
            # history undid moments later. The rest of that program is unreachable, so
            # the file is left exactly as the record found it and the record is
            # reported as environment-limited rather than silently half-applied. An
            # ordinary failure still keeps its write - that one history had too.
            if env_limited and state["text"] != before and _remainder_names_owner(
                    failure, progs, os.path.basename(basename)):
                state["text"] = before
            # A saved program often edits this file AND another one. The write to this
            # file already happened and is what the file became; a failure on a
            # DIFFERENT file cannot undo it. If nothing was written here at all, the
            # failure is this file's own and the record refuses.
            # WHAT THE SHELL DID AFTER THE PROGRAM. Applied here so it lands on the
            # text the program produced, exactly as the command ran it.
            if spans:
                side["__owner__"] = state["text"]
                tail = _shell_compose(rec, basename, side, line=n,
                                      window=(spans[-1][1], len(cmd_text)))
                if tail is not None:
                    state["text"] = tail
            # A saved program often edits this file AND another one. The write to this
            # file already happened and is what the file became; a failure on a
            # DIFFERENT file cannot undo it. If nothing was written here at all, the
            # failure is this file's own and the record refuses.
            # `sed -i` edits land after the programs that produced the file, in the
            # order the command ran them, and apply to the owner or to an in-memory
            # intermediate alike.
            # EVERY sed operation, in the order the command wrote them, against
            # the owner or an in-memory intermediate alike.
            for _pos, path, suffix, kind, payload, guard in sed_operations(cmd_text):
                target = expand(path, shell_vars(cmd_text))
                # A RELATIVE FILE IS NAMED FROM WHERE THE SHELL STOOD at the sed - after
                # a `cd` earlier on the line - so `harness/x.py` in the envelope tree is
                # the envelope copy, not any file that merely ends in those segments.
                if not os.path.isabs(target):
                    _here = cwd_at(cmd_text, _pos, rec.get("cwd"))
                    if _here:
                        target = os.path.normpath(os.path.join(_here, target))
                own = target.endswith(basename) or target == os.path.basename(basename)
                cur = state["text"] if own else side.get(target)
                if cur is None:
                    continue
                if guard is not None:
                    gpat, gpath = guard
                    gtarget = expand(gpath, shell_vars(cmd_text))
                    gown = (gtarget.endswith(basename)
                            or gtarget == os.path.basename(basename))
                    gtext = state["text"] if gown else side.get(gtarget)
                    # the grep decides on the file IT names; an unreadable file makes
                    # grep fail, which is exactly when the campaign ran the sed
                    if gtext is not None and re.search(gpat, gtext, re.M):
                        continue
                if suffix:
                    # `-i.bak` leaves the PRE-EDIT bytes beside the file; the campaign
                    # restored from them, and without this the restore finds nothing
                    side[target + suffix] = cur
                new_text = apply_sed(cur, kind, payload)
                if own:
                    state["text"] = new_text
                else:
                    side[target] = new_text
            if failure is not None and state["text"] == before:
                if isinstance(failure, Exception):
                    raise failure
                raise TranscriptError("the saved program at line %d exited: %s"
                                      % (n, failure))
        finally:
            io.open = real_open
            builtins.open = real_builtin
            os.path.isfile, os.path.exists, os.path.isdir = _real_isfile, _real_exists, _real_isdir
            os.listdir, os.walk = _real_listdir, _real_walk
            os.scandir, os.path.lexists = _real_scandir, _real_lexists
            os.getcwd = _real_getcwd
            _time.sleep = _real_sleep
            sys.argv = saved_argv
            if _finder in sys.meta_path:
                sys.meta_path.remove(_finder)
            # a sibling served to ONE record must not linger for the next: its own
            # history keeps moving, and a cached module would freeze it
            for _m in [k for k, v in sys.modules.items()
                       if getattr(getattr(v, "__spec__", None), "loader", None)
                       .__class__ is _SiblingLoader]:
                sys.modules.pop(_m, None)
            if saved_sub is not None:
                sys.modules["subprocess"] = saved_sub
            else:
                sys.modules.pop("subprocess", None)
        steps[n] = _sha(state["text"])
    return state["text"], steps
