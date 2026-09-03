"""Cutoff-aware chronological replay from a COMMITTED base (Codex SEQ 1541).

My SEQ 1539 mistake was to search for an owner's FINAL hash, find nothing, and conclude no
base survived. The base is the committed file at the clean worktree commit; every later
change is a saved tool input in the transcript. This module replays those changes onto that
base up to a cutoff, and reports the digest after each step so historical measurements can
be asserted as CHECKPOINTS - outputs, never inputs.

Nothing here consults a target hash to decide what to do: the record sequence is discovered
from the transcript, applied in transcript order, and whatever it produces is what is
reported. A caller may assert the result afterwards.
"""
import collections
import hashlib
import contextlib
import io
import json
import os
import traceback
import re
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
import replay_transcript as RT

#: THE WRITE MUST TARGET THIS FILE. A bare `.write(` matched any write the
#: command happened to make - a draft, a claims file - which pulled in records
#: that only READ this owner. The write is recognised only when its destination
#: resolves to this file: a literal path, a variable assigned that path, or a
#: shell redirect onto it.
_ASSIGN = r"""^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(?\s*["'](.*?)["']\s*\)?\s*$"""

#: ONE definition of shell-variable expansion, shared with the replayer, which needs
#: the same substitution the shell performed on a double-quoted `-c` program.
_shell_vars = RT.shell_vars
_expand = RT.expand


def _cd_relative(command, start=None):
    """-> resolved paths for `cd DIR` followed by a RELATIVE path in the program.

    A command routinely cd-ed into a PARENT directory and then opened the file by a
    multi-segment relative name (`cd .../experiments` then `harness/<name>`). Matching
    only a cd into the file's own directory missed those records entirely.
    """
    env = _shell_vars(command)
    cmd = _expand(command, env)
    # ORDER MATTERS. One command often cd-ed into more than one tree, and a relative
    # name belongs to the cd that PRECEDES it, not to all of them. Pairing every cd
    # with every relative name resolved a path into a tree it was never written in -
    # the same copy-confusion that once applied another tree's edit to this owner.
    cds = ([(-1, start)] if start and os.path.isabs(str(start)) else []) + \
        [(m.start(), m.group(1).strip("\"'"))
         for m in re.finditer(r"""cd\s+("[^"]+"|'[^']+'|\S+)""", cmd)]

    def _cwd_at(pos):
        prior = [d for p, d in cds if p < pos and d.startswith("/")]
        return prior[-1] if prior else None

    # ONLY a relative path the command actually WRITES. Pairing every `cd` with every
    # quoted literal pulled in records that merely MENTION another file - it added an
    # unrelated record to an owner's route, which refused harmlessly but was wrong.
    rels = []
    for m in re.finditer(r"""(?:io\.)?open\(\s*["']([\w][\w./-]*\.(?:py|js|mjs|json))["']""", cmd):
        rels.append((m.start(), m.group(1)))
    for m in re.finditer(r"""^\s*([A-Za-z_]\w*)\s*=\s*["']([\w][\w./-]*\.(?:py|js|mjs|json))["']""",
                         cmd, re.M):
        if re.search(r"""(?:io\.)?open\(\s*%s\b""" % re.escape(m.group(1)), cmd):
            rels.append((m.start(), m.group(2)))
    # A SHELL REDIRECT IS A WRITE TOO. `cd <parent>` then `cat >> harness/<name>`
    # appends exactly as a python program would, and modelling only python opens
    # left every such record invisible to the file it actually appended to.
    for m in re.finditer(r""">>?\s*["']?([\w][\w./-]*/[\w./-]*\.(?:py|js|mjs|json))["']?""", cmd):
        rels.append((m.start(), m.group(1)))
    hits = set()
    for pos, r in rels:
        d = _cwd_at(pos)
        if d:
            hits.add(d.rstrip("/") + "/" + r)
    return hits


def targets(command, target_path):
    """True when this saved command writes THIS copy of the file.

    Several copies of each owner lived side by side (harness, harness_g1v2,
    harness_g1v3, iso trees), so the decision is made on the RESOLVED path, not on
    the bare name: the command's own shell variables are expanded first, and a
    program that cd-ed into this file's directory and used the relative name counts.
    """
    env = _shell_vars(command)
    expanded = _expand(command, env)
    name = os.path.basename(target_path)
    # A SHELL PATH IS USUALLY BARE. Matching only quoted literals missed `cp $A
    # $H/<name>`, the very record that swapped this file for a version built in
    # another tree. The owner path is tree-qualified, so naming it is unambiguous.
    if target_path in expanded:
        return True
    for m in re.finditer(r"[\"']([^\"'\n]*%s)[\"']" % re.escape(name), expanded):
        if m.group(1).endswith(target_path):
            return True
    # BOTH the expanded and the RAW command are consulted. Shell-variable expansion is
    # needed when a path is built from `$H`, but it can also mangle a python assignment
    # that spans adjacent string literals - and that is exactly how a record addressed
    # this owner while never writing its path contiguously anywhere.
    for text in (expanded, command):
        if any(v.endswith(target_path)
               for vs in _py_path_multi(text).values() for v in vs):
            return True
    if any(p.endswith(target_path) for p in _cd_relative(command)):
        return True
    d = os.path.dirname(target_path)
    if d and re.search(r"cd\s+\"?[^\"\s]*%s\"?" % re.escape(d), expanded):
        return True
    # a command that EXECUTES a saved script targets whatever that script targets
    for text in _executed_script_texts(expanded):
        if text and targets(text, target_path):
            return True
    return False


def _py_path_multi(cmd):
    """-> {variable: [every path it is assigned]}.

    ONE VARIABLE, SEVERAL FILES. A single saved command commonly walked a list of
    owners, rebinding the same `p` to each in turn. Keeping only the last binding
    hid every earlier file - including this one - so the record looked unrelated.
    """
    env, multi = _py_paths(cmd), {}
    # EVERY assignment, not just the last one the scan happened to keep. A multi-file
    # record rebinds the same `p` to each file in turn, and keeping only the final
    # binding hid every earlier one - including this owner.
    for m in re.finditer(r"""^[ \t]*([A-Za-z_]\w*)[ \t]*=[ \t]*\(((?:\s*["'][^"'\n]*["'])+)\s*\)""",
                         cmd, re.M):
        multi.setdefault(m.group(1), []).append(
            "".join(re.findall(r"""["']([^"'\n]*)["']""", m.group(2))))
    for m in re.finditer(r"""^\s*([A-Za-z_]\w*)\s*=\s*((?:["'][^"'\n]*["']\s*)+)$""", cmd, re.M):
        multi.setdefault(m.group(1), []).append(
            "".join(re.findall(r"""["']([^"'\n]*)["']""", m.group(2))))
    for m in re.finditer(r"""^\s*([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\+\s*["']([^"'\n]*)["']""",
                         cmd, re.M):
        if m.group(2) in env:
            multi.setdefault(m.group(1), []).append(env[m.group(2)] + m.group(3))
    # A LOOP OVER FILENAMES BINDS ONE VARIABLE TO MANY PATHS. A record that renames a
    # symbol across several files walks a tuple of names and joins each onto a base
    # directory (`for f in (...): p = H + f`). Matching only single assignments hid
    # EVERY file such a record touched - including a rename this owner needed, whose
    # absence left an anchor unmatched hundreds of records later.
    for m in re.finditer(r"""for\s+([A-Za-z_]\w*)\s+in\s*[\(\[]((?:\s*["'][^"'\n]*["']\s*,?)+)[\)\]]\s*:""",
                         cmd):
        var, names = m.group(1), re.findall(r"""["']([^"'\n]*)["']""", m.group(2))
        for am in re.finditer(
                r"""^\s*([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\+\s*%s\b""" % re.escape(var),
                cmd, re.M):
            base = env.get(am.group(2))
            if base:
                for nm in names:
                    multi.setdefault(am.group(1), []).append(base + nm)
        for am in re.finditer(
                r"""^\s*([A-Za-z_]\w*)\s*=\s*os\.path\.join\(\s*([A-Za-z_]\w*)\s*,\s*%s\s*\)"""
                % re.escape(var), cmd, re.M):
            base = env.get(am.group(2))
            if base:
                for nm in names:
                    multi.setdefault(am.group(1), []).append(
                        base.rstrip("/") + "/" + nm)
    for k, v in env.items():
        multi.setdefault(k, []).append(v)
    return multi


def _py_paths(cmd):
    """-> {variable: resolved path} for python string variables in a saved program.

    Covers the two forms the campaign used: a variable assigned adjacent string
    literals, and a variable assigned another such variable plus a literal suffix
    (`H = ("..." "...")` then `p = H + "/name.py"`). Nothing is executed.
    """
    env = {}
    # a parenthesised assignment may span lines, which per-line anchoring missed
    for m in re.finditer(r"""^[ \t]*([A-Za-z_]\w*)[ \t]*=[ \t]*\(((?:\s*["'][^"'\n]*["'])+)\s*\)""",
                         cmd, re.M):
        env[m.group(1)] = "".join(re.findall(r"""["']([^"'\n]*)["']""", m.group(2)))
    for m in re.finditer(r"""^\s*([A-Za-z_]\w*)\s*=\s*((?:\s*["'][^"'\n]*["'])+)\s*$""",
                         cmd, re.M):
        env[m.group(1)] = "".join(re.findall(r"""["']([^"'\n]*)["']""", m.group(2)))
    for _ in range(3):
        for m in re.finditer(r"""^\s*([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\+\s*["']([^"'\n]*)["']""",
                             cmd, re.M):
            if m.group(2) in env:
                env[m.group(1)] = env[m.group(2)] + m.group(3)
        # A PATH DERIVED FROM ANOTHER PATH: `t = p.replace("a.py", "b.py")`. The
        # campaign addressed a sibling by editing one path string into another, so a
        # record could rewrite this file without ever naming it.
        for m in re.finditer(
                r"""^\s*([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\.replace\(\s*["']([^"'\n]*)["']\s*,"""
                r"""\s*["']([^"'\n]*)["']\s*\)""", cmd, re.M):
            if m.group(2) in env:
                env[m.group(1)] = env[m.group(2)].replace(m.group(3), m.group(4))
    return env


def _resolve(cwd, path):
    """-> `path` as the process saw it: relative names belong to that process's cwd."""
    if os.path.isabs(path) or not cwd:
        return path
    return os.path.normpath(os.path.join(cwd, path))


def _names_owner(path, target_path, name, cwd):
    """True when a write destination is THIS owner, as the writing process saw it."""
    p = _resolve(cwd, path)
    # SEGMENT-ALIGNED, NOT CHARACTER-ALIGNED: `agent.py` is not `nt.py`, and
    # `experiment.py` is not `nt.py` either. A suffix matches only at a path boundary;
    # a character-suffix match built a route for the stdlib name `nt` out of every
    # write whose filename merely ended in those letters (Codex SEQ 1559).
    if os.path.isabs(p):
        # an absolute path carries its tree and must match in full
        return p == target_path or p.endswith("/" + target_path)
    # PATH-AWARE, NOT NAME-AWARE: a bare relative name equals the owner only when the
    # owner itself is bare. A relative write of `__init__.py` in some package directory
    # is not a write of `pathlib/__init__.py` - that match built a bogus route for a
    # stdlib package and served it in place of the real one.
    return (p == target_path or p.endswith("/" + target_path)
            or (p == name and "/" not in target_path))


def _python_writes(text, cwd, target_path, env, name, argv=None):
    """True when a PYTHON process writes this owner.

    Only python write forms are read here. A shell redirect or a bare filename that
    appears inside this program is TEXT the program prints, not a write - reading the
    whole Bash call at once is what made a printed `-> test_harness_guards.py` look
    like an edit of it.
    """
    holders = set()
    for k, vs in _py_path_multi(text).items():
        if any(_names_owner(v, target_path, name, cwd) for v in vs):
            holders.add(k)
    for m in re.finditer(
            r"""([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(?\s*((?:["'][^"'\n]*["']\s*)+)\)?""",
            text):
        val = "".join(re.findall(r"""["']([^"'\n]*)["']""", m.group(2)))
        if _names_owner(val, target_path, name, cwd):
            holders.add(m.group(1))
    for h in holders:
        if re.search(r"""(io\.)?open\(\s*%s\s*,\s*["'][wax]""" % re.escape(h), text):
            return True
        if re.search(r"""%s\.write_text\(|%s\)\.write\(""" % (re.escape(h),
                                                                re.escape(h)), text):
            return True
    # A PATH BUILT INSIDE THE CALL. `open(H + "name.py", "w")` names this owner just as
    # plainly as a variable holding the whole path, and recognising only the assignment
    # form lost the record that spliced a deleted region back into this file.
    for m in re.finditer(
            r"""(?:io\.)?open\(\s*([A-Za-z_]\w*)\s*\+\s*["']([^"'\n]+)["']\s*,\s*["'][wax]""",
            text):
        base = env.get(m.group(1)) or _py_paths(text).get(m.group(1))
        if base and _names_owner(base.rstrip("/") + "/" + m.group(2).lstrip("/"),
                                 target_path, name, cwd):
            return True
    # a literal path opened for writing - or APPENDING: a process that appends to
    # this owner writes it as surely as one that truncates it - resolved through THIS
    # process's cwd
    for m in re.finditer(r"""(?:io\.)?open\(\s*["']([^"'\n]+)["']\s*,\s*["'][wax]""",
                         text):
        if _names_owner(m.group(1), target_path, name, cwd):
            return True
    # A JOIN NAMES ITS FILE. `open(os.path.join(NAME, "file"), "w")` with NAME a literal
    # assignment, a derivation, or `sys.argv[k]` - the run directory the shell passed
    # on the program's own line. Every run directory of the campaign was written so.
    bound = dict(_py_paths(text))
    for m in re.finditer(r"""([A-Za-z_]\w*)\s*=\s*sys\.argv\[(\d+)\]""", text):
        k = int(m.group(2))
        if argv and 0 < k <= len(argv):
            bound[m.group(1)] = argv[k - 1]
    for m in re.finditer(
            r"""(?:io\.)?open\(\s*os\.path\.join\(\s*([A-Za-z_]\w*)\s*,\s*((?:["'][^"'\n]+["']\s*,?\s*)+)\)\s*,\s*["'][wax]""",
            text):
        base = bound.get(m.group(1)) or env.get(m.group(1))
        if base:
            parts = re.findall(r"""["']([^"'\n]+)["']""", m.group(2))
            if _names_owner(os.path.join(base, *parts), target_path, name, cwd):
                return True
    return False


def _shell_writes(text, cwd, target_path, env, name, line):
    """True when a SHELL process writes this owner: a redirect, a copy, or a script."""
    # A SHELL PROCESS MAY `cd` INSIDE ITSELF. The directory in force at the redirect
    # is the one that names its tree, so it is read at the match's own position and
    # falls back to what the process inherited.
    for m in re.finditer(RT._COPY_RE,
                         text, re.M):
        if _names_owner(m.group(2), target_path, name,
                        RT.cwd_at(text, m.start()) or cwd):
            return True
    # a tree seeded from another tree's modified files writes each of them
    for _src, dst in RT.seed_copies(text, line, cwd):
        if _names_owner(dst, target_path, name, cwd):
            return True
    for m in re.finditer(r""">>?\s*"?([^"\s|;&]+)""", text):
        if _names_owner(m.group(1), target_path, name,
                        RT.cwd_at(text, m.start()) or cwd):
            return True
    # A COMMAND THAT EXECUTES A SAVED SCRIPT WRITES WHATEVER THAT SCRIPT WRITES.
    # One record produces a helper and a later one runs it; the consumer never names
    # this owner, so a route built on names alone loses every edit the script makes.
    # AN IN-PLACE sed IS A WRITE OF THE FILE IT NAMES. Record 29188 moved the harvest
    # program's run directory with `sed -i 's#run3#run4#' "$S/harvest.py"`; the route
    # knew redirects, copies and scripts, never sed, and the program stayed on run 2.
    for _pos, path, _suffix, _kind, _payload, _guard in RT.sed_operations(text):
        # the file is named from where the shell stood at the sed, after any `cd`
        # earlier on the line (`cd $TREE/... && sed -i '...' harness/x.py`)
        if _names_owner(_expand(path, env), target_path, name,
                        RT.cwd_at(text, _pos, cwd) or cwd):
            return True
    for src in _executed_script_texts(text, line):
        if src and _python_writes(src, cwd, target_path, env, name):
            return True
    return False


def unit_writes(unit, target_path, line=None):
    """True when ONE process of a command writes this owner."""
    _start, _end, cwd, kind, text = unit[:5]
    env = _shell_vars(text)
    body = _expand(text, env) if kind == "shell" else text
    if kind == "program":
        return _python_writes(body, cwd, target_path, env,
                              os.path.basename(target_path), argv=unit[5] if len(unit) > 5 else None)
    return _shell_writes(body, cwd, target_path, env,
                         os.path.basename(target_path), line)


def selected_units(command, target_path, line=None, start=None):
    """-> [(index among this command's PROGRAMS, unit)] for the processes to execute.

    Only the processes that write this owner are its business. Running the unrelated
    sibling programs of the same Bash call replayed edits to other files, and let one
    unrelated program's failure erase a selected process's write.
    """
    env = _shell_vars(command)
    out, i = [], 0
    for unit in RT.process_units(command, start):
        if unit[3] != "program":
            continue
        u = (unit[0], unit[1], unit[2] or RT.cwd_at(command, unit[0], start), "program",
             unit[4], RT.stdin_program_argv(command, unit[0]))
        if unit_writes(u, target_path, line):
            out.append((i, unit))
        i += 1
    return out


def writes_this(command, target_path, line=None, start=None):
    """True when SOME PROCESS of this command writes this exact copy.

    Not "the command mentions the file": a Bash call runs several processes, each in
    its own directory, and only the one that actually writes this tree-qualified copy
    makes the record this owner's.
    """
    # a command that seeds one tree from another, or copies a directory whole, names
    # the files it moves only through a loop or a directory: the expanded copies decide
    if not targets(command, target_path):
        name = os.path.basename(target_path)
        # CHEAP FIRST: a copy loop or a directory copy can only write this owner if
        # some copy DESTINATION in the command names the owner's tree or directory;
        # expanding the loops (which rebuilds the source tree's files) is done only then
        # A WRITE MAY NAME ITS FILE ONLY BY ITS BARE NAME - `os.path.join(run,
        # "attempts.json")`, or `sed -i '...' harness/x.py` after a `cd` - so a command
        # whose text carries the owner's bare name as a whole segment goes on to the
        # per-process check, which is path-aware; the copy expansion below is for
        # commands that never spell the name at all.
        # A SCRIPT THE COMMAND RUNS NAMES THE FILE IN ITS OWN TEXT: `python
        # "$S/harvest.py" ...` never spells `attempts.json`; the harvest program does.
        # The script is read at its LATEST text here - one resolution per script
        # path, cached - because this is a pre-filter over thousands of script-running
        # records; the per-process check below reads it at the record's own cutoff.
        _spelled = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(name))
        if not _spelled.search(command) and not any(
                t and _spelled.search(t) for t in _executed_script_texts(command, None)):
            if not RT.copy_destinations_may_name(command, target_path, start):
                return False
            cwd0 = RT.cwd_at(command, len(command), start)
            if not any(_names_owner(d, target_path, name, cwd0)
                       for _s, d in RT.seed_copies(command, line, start)):
                return False
    env = _shell_vars(command)
    for unit in RT.process_units(command, start):
        cwd = unit[2]
        u = (unit[0], unit[1], cwd, unit[3],
             unit[4] if unit[3] == "program" else _expand(unit[4], env),
             RT.stdin_program_argv(command, unit[0]) if unit[3] == "program" else None)
        if unit_writes(u, target_path, line):
            return True
    return False


#: a script's reconstruction, kept per path for ROUTE membership. Deciding whether a
#: command could write an owner asks what the script does, and rebuilding that script
#: once per candidate record replayed its whole history thousands of times over. The
#: REPLAY still resolves the script at its own consuming line; only this membership
#: question reuses the answer.
_SCRIPT_CACHE = {}


#: True while a script's own text is being reconstructed. Deciding whether a command
#: writes an owner needs the script it runs, but reconstructing THAT script must not
#: itself go looking for further scripts: route building then re-enters route building,
#: and a single record can spend minutes rebuilding the same handful of files. One
#: level is what the rule needs; deeper is repetition, not evidence.
_IN_SCRIPT = [False]


@RT.machinery
def _executed_script_texts(cmd, before_line=None):
    """-> the reconstructed text of each saved script this command executes."""
    out = []
    # KEYED BY (path, cutoff). A script is itself rebuilt from its own history, so its
    # text at cutoff 30 is not its text at cutoff 10; caching by path alone served the
    # earliest reconstruction to every later consumer.
    upto = before_line or 10 ** 9
    if _IN_SCRIPT[0]:
        # already reconstructing a script: answer only from what is known
        for m in re.finditer(r"""python3?\s+(?:-B\s+)?["']?(%s[^\s"']*\.py)["']?"""
                             % re.escape(RT.SCRATCH_ROOT), cmd):
            if (m.group(1), upto) in _SCRIPT_CACHE:
                out.append(_SCRIPT_CACHE[(m.group(1), upto)])
        return out
    for m in re.finditer(r"""python3?\s+(?:-B\s+)?["']?(%s[^\s"']*\.py)["']?"""
                         % re.escape(RT.SCRATCH_ROOT), cmd):
        path = m.group(1)
        if path in _RESOLVING:
            continue
        if (path, upto) in _SCRIPT_CACHE:
            out.append(_SCRIPT_CACHE[(path, upto)])
            continue
        _IN_SCRIPT[0] = True
        try:
            text = (sibling_text(path, upto)
                    if RT.SIBLING_RESOLVER is None
                    else RT.SIBLING_RESOLVER(path, upto))
        except Exception:
            text = None
        finally:
            _IN_SCRIPT[0] = False
        _SCRIPT_CACHE[(path, upto)] = text
        out.append(text)
    return out


#: a command that executes a saved scratch script - the consumer half of a
#: producer-to-consumer pair, which names no owner of its own
#: A COMMAND NAMES ITS SCRIPT THROUGH A VARIABLE. Requiring the literal scratch
#: root here dropped the consumer half of a producer/consumer pair before any
#: check ran, because the raw line carries `$S/...`. The prefilter therefore
#: admits any python invocation of a `.py` file; `writes_this` still decides on
#: the RESOLVED script.
# THE RAW LINE IS JSON: a quoted script path is stored as `\"$S/harvest.py\"`, so the
# quote may carry a backslash. Without it the harvest calls never reached the check.
_RUNS_SCRIPT = re.compile(r"""python3?\\?\s+(?:-B\\?\s+)?(?:\\?[\"'])?[\w$/.\-]+\.py""")


#: (basename, first, upto) -> the decided records, so an identical query is answered
#: without re-reading the transcript. Only the scan is remembered; the decision that
#: produced it is unchanged.
_RECORD_INDEX = {}
#: the package's sibling cache directory: routes are cached beside the texts
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sibling_cache")


def route_cache_path(basename, first, upto):
    """The on-disk route entry for one query, bound to the code and input digest."""
    key = hashlib.sha256(("%s\n%s\n%s\n%s" % (_code_digest(), basename, first, upto)).encode("utf-8")).hexdigest()[:24]
    return os.path.join(_CACHE_DIR, "route_%s_%s.json" % (_code_digest(), key))


def _route_cache_read(basename, first, upto):
    fp = route_cache_path(basename, first, upto)
    if not os.path.isfile(fp):
        return None
    try:
        lines = json.load(io.open(fp, encoding="utf-8"))["records"]
    except (ValueError, KeyError, OSError):
        return None
    recs = RT.lines(set(lines))
    if any(n not in recs for n in lines):
        return None
    return [(n, recs[n]) for n in lines]


def _route_cache_write(basename, first, upto, out):
    if not DISK_CACHE_WRITES:
        return
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        tmp = route_cache_path(basename, first, upto) + ".tmp"
        io.open(tmp, "w", encoding="utf-8").write(json.dumps({"basename": basename, "first": first, "upto": upto,
                                                             "records": [n for n, _r in out]}))
        os.replace(tmp, route_cache_path(basename, first, upto))
    except OSError:
        pass


@RT.machinery
def modifying_records(basename, first=1, upto=None):
    """-> ordered transcript lines that write `basename`, within [first, upto)."""
    name = os.path.basename(basename)
    stem = name.split(".")[0]
    # THE WINDOW IS PART OF THE QUERY. Scanning past `upto` decided thousands of
    # records nobody asked about, each able to resolve a script and replay its route -
    # route building went from instant to not finishing. The cache therefore keys on
    # the window, so an exact repeat is free and a different window is honest work.
    ckey = (basename, first, upto)
    if ckey in _RECORD_INDEX:
        return _RECORD_INDEX[ckey]
    # THE ROUTE CACHE: the same key discipline as the sibling cache. A route decided
    # once for this code, this transcript and this store is served from disk to every
    # later namespace; each mutation and audited row used to rescan the transcript.
    cached = _route_cache_read(basename, first, upto)
    if cached is not None:
        _RECORD_INDEX[ckey] = cached
        return cached
    out = []
    with io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            if upto is not None and n >= upto:
                break
            if n < first:
                continue
            # A RECORD NEED NOT NAME THIS FILE TO WRITE IT. One that EXECUTES a saved
            # script writes whatever the script writes, and the consumer never mentions
            # the owner - so a name-only prefilter drops it before any check runs. Such
            # records are admitted as candidates and then decided on the RESOLVED script.
            # A script-runner is only a candidate if the record is a Bash tool call;
            # testing that on the raw line first avoids parsing large assistant
            # messages that merely quote such a command. Semantics are unchanged - the
            # decision is still made on the resolved script below.
            if stem not in line and "status --porcelain" not in line and "cp -r" not in line and not (
                    '"name":"Bash"' in line.replace(" ", "")
                    and _RUNS_SCRIPT.search(line)):
                continue
            rec = json.loads(line)
            for b in ((rec.get("message") or {}).get("content") or []):
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                nm = b.get("name")
                inp = b.get("input") or {}
                fp = str(inp.get("file_path") or "")
                p = inp.get("command") or inp.get("content") or ""
                if nm in ("Write", "Edit") and fp.endswith(basename):
                    out.append((n, rec))
                elif nm == "Bash" and (name in p or _RUNS_SCRIPT.search(p)
                                       or "status --porcelain" in p) \
                        and writes_this(p, basename, line=n, start=rec.get("cwd")):
                    out.append((n, rec))
                break
    _RECORD_INDEX[ckey] = out
    _route_cache_write(basename, first, upto, out)
    return out


#: guards against a sibling whose own route reads back the file that asked for it
_RESOLVING = set()
#: canonical path -> the text of a file whose rebuild is currently in flight,
#: so a re-entrant read is answered with what the file holds at that moment
_INPROGRESS = {}
_SIBLING_CACHE = {}
#: path -> (cutoff, text, scratch) of the most recent resolution, so a later
#: cutoff resumes from it instead of replaying the file's whole history
_LAST_RESOLVED = {}
_ORIGINS = {}


@RT.machinery
def tree_origin(tree):
    """-> (creation line, commit) for a scratch worktree, or None.

    EVERY TREE HAS ITS OWN ORIGIN. `bench_1306` was checked out from one commit and
    `step1_iso` from another, each at its own moment. Treating them all as the same
    base at the same start line replays another era's records onto the wrong bytes,
    which is exactly how a reconstruction ended up twice its true length.
    """
    if tree in _ORIGINS:
        return _ORIGINS[tree]
    found = None
    # THE SAVED COMMAND NAMES THE TREE THROUGH A VARIABLE (`B=$S/bench_1306`), so the
    # full path never appears in the line; pre-filter on the tree's own name and let
    # the expanded destination decide
    key = os.path.basename(tree.rstrip("/"))
    with io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            if key not in line or "worktree add" not in line:
                continue
            rec = json.loads(line)
            for b in ((rec.get("message") or {}).get("content") or []):
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                cmd = (b.get("input") or {}).get("command") or ""
                env = _shell_vars(cmd)
                for m in re.finditer(
                        r"git\s+(?:-C\s+\S+\s+)?worktree\s+add\s+((?:-{1,2}\w+\s+)*)"
                        r"\"?([^\"\s]+)\"?\s+([0-9a-f]{7,40})", cmd):
                    dest = _expand(m.group(2), env)
                    if dest.rstrip("/").endswith(tree):
                        found = (n, m.group(3))
                break
            if found:
                break
    _ORIGINS[tree] = found
    return found


#: artifacts the replay CANNOT rebuild, because the era GENERATED them and no record
#: ever writes their bytes. Each is listed with the digest it must have, and every one
#: of those digests is a value history itself recorded - the signed inventory, for
#: instance, is the `inventory_sha256` the accepted plan binds. A file whose bytes do
#: not match its listed digest is refused rather than served, so this can supply
#: recovered evidence but never invent any.
_RECOVERED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "recovered")


#: the longest path this filesystem can hold; anything longer is not a path
_PATH_MAX = 4096


def looks_like_path(value):
    """True when `value` can be a filename at all.

    A saved program can hand `open()` something that is not a path - a whole file's
    text, a multi-line blob. Treating that as a sibling built a route from it and then
    compiled it into a regular expression, which exhausted the interpreter's stack in
    the regex parser rather than failing as the bad input it is.
    """
    s = str(value)
    return bool(s) and len(s) <= _PATH_MAX and "\n" not in s and "\x00" not in s


def canonical_path(path):
    """-> ONE spelling for a file, so identity never depends on how it was written.

    `harness/x.py`, `./harness/x.py`, `a/../harness/x.py` and the absolute form all name
    the same file. Cycle detection and caching key on this; without it the same file
    enters resolution twice under two names and the loop is invisible.
    """
    p = os.path.normpath(str(path))
    return p[2:] if p.startswith("./") else p


@RT.machinery
def _recovered(path, line=None):
    """-> bytes of a recovered artefact for this path AT THIS CUTOFF, or None.

    A RECOVERED ARTEFACT BELONGS TO AN ERA. One path can hold several bodies across the
    campaign - the one-item inventory has six - so an entry may name the record that
    PRODUCED it. The body served is the latest such entry produced BEFORE this cutoff;
    an entry with no producer line is the era-less fallback it always was. Every entry
    is still digest-gated: a body that does not hash to its own line is refused.
    """
    index = os.path.join(_RECOVERED_DIR, "RECOVERED.tsv")
    if not os.path.isfile(index):
        return None
    best = None
    # A PATH WITH A TIMED SERIES HAS NO ERA-LESS ANSWER. An entry with no producing
    # record is a fallback for a path whose history this recovery never timed; letting
    # it fill the window BEFORE the first timed body hands a record bytes from an era
    # that had not happened yet, which is worse than serving nothing.
    timed = False
    for entry in io.open(index, encoding="utf-8"):
        parts = entry.rstrip("\n").split("\t")
        if len(parts) > 2 and parts[2].isdigit() and path.endswith(parts[1]):
            timed = True
            break
    for entry in io.open(index, encoding="utf-8"):
        if not entry.strip():
            continue
        parts = entry.rstrip("\n").split("\t")
        want, rel = parts[0], parts[1]
        if not path.endswith(rel):
            continue
        produced = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
        fname = parts[3] if len(parts) > 3 else os.path.basename(rel)
        if produced is not None:
            if line is None or produced >= line:
                continue
            if best is not None and best[0] is not None and produced <= best[0]:
                continue
        elif timed or best is not None:
            continue
        best = (produced, want, fname)
    if best is None:
        return None
    fp = os.path.join(_RECOVERED_DIR, best[2])
    if not os.path.isfile(fp):
        return None
    text = io.open(fp, encoding="utf-8").read()
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != best[1]:
        return None
    return text


#: Resolved siblings are deterministic: the same transcript, the same commit and the
#: same replay code always produce the same bytes. The FIRST resolution of a sibling is
#: also the single most expensive step in a long owner's replay, so it is written to a
#: cache beside the package and reused by later runs. The key includes a digest of the
#: replay modules themselves, so ANY change to the rules invalidates every entry rather
#: than silently serving bytes the current code would not produce.
#: every refusal swallowed while rebuilding a sibling, for the census to adjudicate
SIBLING_REFUSALS = []

_DISK_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sibling_cache")


def _code_digest():
    """The cache key binds EVERY input a sibling's bytes depend on: the replay code,
    the accepted transcript identity and the git base store identity. The previous key
    bound only the code, so a cache built against different transcript bytes would
    have been served as if it were this proof's (Codex SEQ 1559 item 2)."""
    if not hasattr(_code_digest, "value"):
        h = hashlib.sha256()
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("chrono_replay.py", "replay_transcript.py"):
            h.update(io.open(os.path.join(here, name), "rb").read())
        for ident in (os.path.join(RT.PACKAGE, "evidence", "transcript", "ACCEPTED.tsv"),
                      os.path.join(RT.GIT_BASES, "GIT_BASES.tsv")):
            h.update(io.open(ident, "rb").read())
        _code_digest.value = h.hexdigest()[:16]
    return _code_digest.value


def _disk_key(path, before_line):
    return hashlib.sha256(
        ("%s|%s|%s" % (_code_digest(), path, before_line)).encode()).hexdigest()[:32]


@RT.machinery
def _disk_get(path, before_line):
    fp = os.path.join(_DISK_CACHE, _disk_key(path, before_line))
    try:
        return RT._REAL_IO_OPEN(fp, encoding="utf-8").read()
    except Exception:
        return None


#: THE DISK CACHES ARE READ-ONLY WHILE ANY FAULT IS INSTALLED. A mutant namespace
#: computes texts and routes with a broken rule; written under the honest key they
#: would be served to every later honest computation. The harness clears this flag
#: when it installs a fault and restores it afterwards.
DISK_CACHE_WRITES = True


@RT.machinery
def _disk_put(path, before_line, text):
    if not DISK_CACHE_WRITES:
        return
    try:
        os.makedirs(_DISK_CACHE, exist_ok=True)
        fp = os.path.join(_DISK_CACHE, _disk_key(path, before_line))
        tmp = fp + ".tmp"
        RT._REAL_IO_OPEN(tmp, "w", encoding="utf-8").write(text)
        os.replace(tmp, fp)
    except Exception:
        pass


def _reentrant_text(path, before_line):
    """-> the in-flight text of `path` when the cutoff asked for lies beyond the record
    last applied to it (the bytes so far ARE its state before that cutoff), else None:
    an earlier cutoff must be rebuilt on its own, never served the newer bytes."""
    got = _INPROGRESS.get(path)
    if got is None:
        return None
    pos, text = got
    if before_line is None or before_line > pos:
        return text
    return None


@RT.machinery
def sibling_text(path, before_line, first=1):
    """-> a sibling scratch file as it stood just before `before_line`, or None.

    THE SIBLING IS NOT FROZEN AT THE COMMIT. By the time this owner's record reads
    `test_harness_guards.py`, that file has been rewritten many times by its own
    records. Replaying the sibling's own route up to this point is what history
    actually presented to the program. The sibling's route is DERIVED exactly as the
    owner's is, and never consults any target digest.
    """
    key = (path, before_line)
    if key in _SIBLING_CACHE:
        return _SIBLING_CACHE[key]
    name = os.path.basename(path)
    # A CYCLE IS DETECTED ON THE CANONICAL PATH, not on the spelling. The same file can
    # be asked for as `harness/x.py`, `./harness/x.py` or by its absolute path, and a
    # guard keyed on the raw string lets a cycle through under a second spelling. There
    # is no depth limit: a real chain of siblings may be long, and cutting it by depth
    # would silently truncate lawful resolution instead of catching the actual loop.
    if not looks_like_path(path):
        return None
    path = canonical_path(path)
    if path in _RESOLVING:
        # A RE-ENTRY IS NOT A DEAD END. On disk there was one file: a program that read
        # it while its own rebuild was in flight saw the bytes it had SO FAR, not
        # nothing. Returning None here handed such a record a stale committed copy, and
        # its anchor assertions then failed - the same record applied perfectly at top
        # level, where the file was simply served from the state being built.
        # BUT ONLY FOR A CUTOFF BEYOND THE REBUILT POSITION. A nested route may ask for
        # an EARLIER state of the file in flight (build_launch_manifest.py's record
        # 24246 reads test_harness_guards.py as of 24246 while test_harness_guards.py
        # is being rebuilt past 24276); the bytes so far are too new for it, and
        # serving them anyway is how record 24277 refused only inside the census.
        # An earlier cutoff is replayed on its own, which terminates: it is strictly
        # earlier than the rebuild in flight.
        got = _reentrant_text(path, before_line)
        if got is not None:
            return got
        saved_prog = _INPROGRESS.pop(path, None)
        _RESOLVING.discard(path)
        try:
            return sibling_text(path, before_line, first)
        finally:
            _RESOLVING.add(path)
            if saved_prog is not None:
                _INPROGRESS[path] = saved_prog
    # A SIBLING NEED NOT BE PYTHON, AND NEED NOT PREDATE THE ERA. Files created during
    # the run (a .js template, a generated fixture) have no committed base; they start
    # empty and are built entirely by their own records. Refusing them left the record
    # that read them raising before it reached its owner.
    # THIS TREE'S OWN BASE AND START LINE, not the caller's. A tree checked out from a
    # DIFFERENT commit at a DIFFERENT moment must be replayed from ITS origin; treating
    # every tree as the same base at line 1 replays another era's records onto the
    # wrong bytes, which is how one reconstruction ended up twice its true length.
    tree = path.split("scratchpad/", 1)[1].split("/")[0] if "scratchpad/" in path else ""
    origin = tree_origin(tree) if tree else None
    if origin:
        first = max(first, origin[0])
        base = RT._committed(path, commit=origin[1])
    else:
        base = RT._committed(path)
    # EACH TREE HAS ITS OWN ERA, so a sibling must be identified by its TREE, exactly
    # as the owner is. Qualified this way its route can start at the beginning of the
    # transcript without mixing in another tree's copy of the same filename - which is
    # what a folder-name-only match did, inflating one file to 321 KB.
    if "scratchpad/" in path:
        owner = path.split("scratchpad/", 1)[1]
    else:
        parent = os.path.basename(os.path.dirname(path))
        owner = os.path.join(parent, name) if parent else name
    # A SIBLING DESERVES THE SAME ROUTE THE OWNER GETS. Using the bare record list left
    # siblings rebuilt from a weaker history than the owner - without the producers of
    # the intermediates they are themselves assembled from.
    try:
        recs = route_records(owner, first, before_line)[0]
    except Exception:
        recs = modifying_records(owner, first, before_line)
    if base is None and not recs:
        return _recovered(path, before_line)
    # A SIBLING THAT NOTHING WROTE IN BETWEEN IS THE SAME FILE. Nested resolution asks
    # for the same sibling at many cutoffs, and replaying its whole history again for
    # each one arrives at identical bytes. Reuse is allowed ONLY when this sibling has
    # no record of its own between the two cutoffs - the condition under which the
    # answer cannot have changed.
    # A FILE ALREADY BEING REPLAYED IS SERVED ITS IN-FLIGHT BYTES. That is what the
    # program actually read from the disk at that moment, and rebuilding it from its
    # tree origin instead was both slower and a different answer.
    live = RT.active_owner_text(path, before_line)
    if live is not None:
        return live
    disk = _disk_get(path, before_line)
    if disk is not None:
        _SIBLING_CACHE[key] = disk
        return disk
    # THE INVARIANT THAT MAKES RESUMING SOUND: a file's start line is its TREE's origin,
    # never the caller's, so every request for the same path shares one window start.
    # Were that not so, a later request beginning EARLIER than a stored state would
    # resume from bytes that had skipped the earlier records, and the reuse would be
    # silently wrong rather than merely stale.
    # RESOLUTION IS INCREMENTAL. The same sibling is asked for at rising cutoffs, and
    # replaying its whole history from the tree origin each time is quadratic in the
    # number of asks - which is what made one record take longer than every other
    # record combined. The state after a record sequence is a pure function of that
    # sequence, so a later cutoff resumes from the earlier one and applies only the
    # records in between. The scratch filesystem is carried with it, because a record
    # may read an intermediate an earlier record of the same sibling wrote.
    last = _LAST_RESOLVED.get(path)
    start_text, start_side, done_upto = base or "", {}, 0
    # A RESUME IS ONLY SOUND WHEN THE WIDER ROUTE AGREES ABOUT THE PAST. A later
    # consumer can reveal a producer that sits BEFORE the resume point; applying only
    # the records after it would silently drop that producer, so the resumed answer
    # would differ from a fresh rebuild. When the past disagrees, rebuild.
    if (last is not None and last[0] <= (before_line or 0)
            and {n for n, _r in recs if n < last[0]} == last[3]):
        pending = [n for n, _r in recs if last[0] <= n < (before_line or 0)]
        if not pending:
            _SIBLING_CACHE[key] = last[1]
            return last[1]
        start_text, start_side, done_upto = last[1], dict(last[2]), last[0]
    # the set that describes what `text` will contain is the WHOLE route, not the tail
    # this call happens to apply; a later resume compares against it
    applied = {n for n, _r in recs}
    recs = [(n, r) for n, r in recs if n >= done_upto]
    _RESOLVING.add(path)
    try:
        text, side = start_text, start_side
        _INPROGRESS[path] = (done_upto - 1 if done_upto else 0, text)
        refused_here = False
        for n, rec in recs:
            try:
                text, _ = RT.apply_saved_edits(text, {n: rec}, owner, side=side)
            except Exception as exc:                            # noqa: BLE001
                # a sibling record that refuses leaves the sibling as it was, exactly
                # as the failed command did; it must not abort the owner's replay.
                # IT IS NEVER SILENT: the refusal is recorded with its exact class
                # and message so the census can adjudicate it against history's own
                # result, and a sibling built over a refusal is never cached - a
                # later run must rebuild it rather than be served the short bytes.
                refused_here = True
                SIBLING_REFUSALS.append({"path": path, "record_line": n,
                                         "error": type(exc).__name__,
                                         "error_message": str(exc),
                                         "traceback": traceback.format_exc()})
            # publish after every record, WITH ITS POSITION, so a re-entrant read sees
            # this file exactly as far as it has been rebuilt - or knows it must not
            _INPROGRESS[path] = (n, text)
        _LAST_RESOLVED[path] = (before_line or 0, text, dict(side), applied)
        if not refused_here:
            _disk_put(path, before_line, text)
    finally:
        _RESOLVING.discard(path)
        _INPROGRESS.pop(path, None)
    # A GENERATED ARTEFACT HAS RECORDS THAT MENTION IT AND NONE THAT WRITE ITS BYTES,
    # so the replay legitimately produces nothing. Serving a recovered copy - only ever
    # one whose digest history itself recorded - is what lets the record that READS it
    # run at all; an empty read killed the whole program and every later edit with it.
    if not text:
        text = _recovered(path, before_line) or text
    _SIBLING_CACHE[key] = text
    return text


#: THE SIBLING'S ROUTE STARTS WHERE THIS ERA DOES. Replaying it from transcript line 1
#: replays other eras' copies of the same filename onto this era's base - which is how
#: a sibling ballooned to 321 KB. The route builder sets this to its own start line.
#: A TREE-QUALIFIED sibling may safely replay from the start of the transcript: its
#: route can only match records naming ITS tree, so an older tree that predates this
#: era still gets the records that actually built it.
SIBLING_FIRST = [1]
RT.SIBLING_RESOLVER = RT.machinery(lambda p, n: sibling_text(p, n, first=1))
RT.TREE_COMMIT = lambda t: (tree_origin(t) or (None, None))[1]


def _select_units(command, basename, line, start=None):
    """-> the program indices this owner owns, plus the producers they read."""
    chosen = {i for i, _u in selected_units(command, basename, line, start)}
    if not chosen:
        return chosen
    # A PRODUCER IS PART OF THE SELECTION. A selected process routinely reads a
    # file an EARLIER process of the same command wrote; dropping that producer
    # leaves the consumer reading nothing.
    progs = [u for u in RT.process_units(command, start) if u[3] == "program"]
    reads = set()
    for i in sorted(chosen):
        reads |= _opened_paths(progs[i][4], progs[i][2])
    for i, u in enumerate(progs):
        if i in chosen or i > max(chosen):
            continue
        if _written_paths(u[4], u[2]) & reads:
            chosen.add(i)
    return chosen


def _opened_paths(text, cwd):
    """-> every path a python process READS, as that process saw it."""
    out = set()
    for m in re.finditer(r"""(?:io\.)?open\(\s*["\']([^"\'\n]+)["\']""", text):
        out.add(_resolve(cwd, m.group(1)))
    for v in _py_paths(text).values():
        out.add(_resolve(cwd, v))
    return out


def _written_paths(text, cwd):
    """-> every path a python process WRITES, as that process saw it."""
    out = set()
    for m in re.finditer(
            r"""(?:io\.)?open\(\s*["\']([^"\'\n]+)["\']\s*,\s*["\']w""", text):
        out.add(_resolve(cwd, m.group(1)))
    for k, v in _py_paths(text).items():
        if re.search(r"""(io\.)?open\(\s*%s\s*,\s*["\']w""" % re.escape(k), text):
            out.add(_resolve(cwd, v))
    return out



_MODIFIED_CACHE = {}


def _tree_mentions(tree):
    """-> [(line, rel)] for every file any record names under `tree`, scanned ONCE per
    tree; a question about an earlier line filters this list in memory. Scanning the
    transcript afresh for every (tree, line) asked about cost a full pass per record."""
    if tree in _MENTIONS_CACHE:
        return _MENTIONS_CACHE[tree]
    base_name = os.path.basename(tree.rstrip("/"))
    pat = re.compile(re.escape(tree.rstrip("/")) + r"/((?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]+)")
    out = []
    with io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
        for n, raw in enumerate(fh, 1):
            if base_name not in raw:
                continue
            try:
                rec = json.loads(raw)
            except ValueError:
                continue
            for b in ((rec.get("message") or {}).get("content") or []):
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                fp = str(inp.get("file_path") or "")
                if b.get("name") in ("Write", "Edit") and fp.startswith(tree.rstrip("/") + "/"):
                    out.append((n, fp[len(tree.rstrip("/")) + 1:]))
                cmd = inp.get("command") or ""
                if b.get("name") == "Bash" and cmd:
                    expanded = _expand(cmd, _shell_vars(cmd))
                    for m in pat.finditer(expanded):
                        out.append((n, m.group(1)))
                    # A FILE NAMED RELATIVELY AFTER A `cd` INTO THE TREE. The era's
                    # programs did `cd "$ISO/.../harness"` then `p='x.py'`; the tree
                    # prefix never precedes the name, so the cd's own directory does.
                    for resolved in _cd_relative(cmd, rec.get("cwd")):
                        if resolved.startswith(tree.rstrip("/") + "/"):
                            out.append((n, resolved[len(tree.rstrip("/")) + 1:]))
    _MENTIONS_CACHE[tree] = out
    return out


_MENTIONS_CACHE = {}


def modified_in_tree(tree, line, with_tracked=False, under=None):
    """-> the relative paths under `tree` whose rebuilt text before `line` differs from
    their committed base: what `git status --porcelain` listed as M at that moment.

    The candidates are the files any record before `line` named under the tree; each
    is rebuilt to that line and compared with the tree's own commit. Nothing is listed
    by hand, and a file the transcript never touched cannot appear modified."""
    key = (tree, line, under)
    if key in _MODIFIED_CACHE:
        got = _MODIFIED_CACHE[key]
        return got if with_tracked else {r for r, _t in got}
    o = tree_origin(tree)
    rels = {rel for n, rel in _tree_mentions(tree) if n < line}
    out = set()
    # a name resolved through `..` is normalised; one that escapes the tree is not its
    rels = {os.path.normpath(r) for r in rels}
    rels = {r for r in rels if not r.startswith("../") and r != ".."}
    # ONLY THE NAMES ASKED ABOUT ARE REBUILT. Listing what a directory copy moved
    # needs the files under THAT directory; rebuilding every file of the tree to
    # answer it replayed whole eras for a directory of launch scripts.
    if under:
        rels = {r for r in rels if r.startswith(under)}
    for rel in sorted(rels):
        path = tree.rstrip("/") + "/" + rel
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                text = sibling_text(path, line)
        except Exception:                                      # noqa: BLE001
            text = None
        try:
            base = RT._committed(path, commit=o[1]) if o else RT._committed(path)
        except RuntimeError:
            base = None
        if text is not None and text != (base if base is not None else ""):
            out.add((rel, base is not None))          # tracked when the commit holds it
    _MODIFIED_CACHE[key] = out
    return out if with_tracked else {r for r, _t in out}


RT.TREE_MODIFIED = modified_in_tree

RT.SELECT_UNITS = _select_units


def _sources(command, target_path):
    """-> scratch paths this command copies or appends INTO the target file."""
    cmd = _expand(command, _shell_vars(command))
    out = []
    for m in re.finditer(RT._COPY_RE,
                         cmd, re.M):
        if m.group(2).endswith(target_path):
            out.append(m.group(1))
    for m in re.finditer(r"cat\s+\"?([^\"\s]+)\"?\s*>>\s*\"?([^\"\s]+)\"?", cmd):
        if m.group(2).endswith(target_path):
            out.append(m.group(1))
    # `cat A B > DST` names SEVERAL sources; taking only the first lost the body half
    # of a file rebuilt from a sliced head plus a separately written body.
    for m in re.finditer(r"cat\s+((?:[^\s>|]+[ \t]+)*[^\s>|]+)[ \t]*>(?!>)[ \t]*\"?([^\"\s]+)\"?",
                         cmd):
        if m.group(2).endswith(target_path):
            out.extend(m.group(1).split())
    # A PROGRAM READS INTERMEDIATES TOO. A record that splices a prepared block into
    # this file opens that block by path; without its producer the block is missing and
    # the splice silently degrades into a duplicate. Only scratch paths qualify - they
    # are deterministic products of the replay, never outside inputs.
    for m in re.finditer(r"""(?:io\.)?open\(\s*["'](%s[^"'\n]*)["']"""
                         % re.escape(RT.SCRATCH_ROOT), cmd):
        if not m.group(1).endswith(target_path):
            out.append(m.group(1))
    return [s for s in out if s.startswith(RT.SCRATCH_ROOT)]


def is_side_file(path):
    """True when a source is a genuine TEMPORARY file rather than a tree sibling.

    A source under `scratchpad/<tree>/...` has its own committed or recovered history
    and is already owned by the sibling resolver: it must be RESOLVED at the consuming
    cutoff, not executed as an ephemeral producer against the consuming owner. Doing the
    latter pulled another tree's records into this owner's route - and, worse, ran them.
    A temporary file has no tree, so nothing else can rebuild it and its producer really
    does belong to whoever consumes it.
    """
    return "scratchpad/" not in str(path)


@RT.machinery
def route_records(basename, first=1, upto=None):
    """-> the owner's records PLUS the records that produced the files they consume.

    A record that rebuilds this file from an intermediate (`cp rt_keep.py <owner>`)
    depends on the earlier record that SLICED that intermediate out of this same
    file. The intermediate is a deterministic product of the replay, not an outside
    input, so its producer belongs in the route. Producers are found by asking which
    earlier record wrote that path - never by naming a file.
    """
    if not _RESOLVING:
        # only the top-level route resets the cache; a nested sibling route must not
        # discard the work the outer replay is in the middle of using
        SIBLING_FIRST[0] = first
        _SIBLING_CACHE.clear()
    own = modifying_records(basename, first, upto)
    wanted = {}
    for n, rec in own:
        for b in ((rec.get("message") or {}).get("content") or []):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                cmd = (b.get("input") or {}).get("command") or ""
                for src in _sources(cmd, basename):
                    if not is_side_file(src):
                        continue        # a tree sibling is resolved, never executed
                    wanted.setdefault(src, n)
            break
    extra = {}
    if wanted:
        with io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if n < first or (upto is not None and n >= upto):
                    continue
                for src, need in wanted.items():
                    if n >= need or os.path.basename(src) not in line:
                        continue
                    rec = json.loads(line)
                    for b in ((rec.get("message") or {}).get("content") or []):
                        if not isinstance(b, dict) or b.get("type") != "tool_use":
                            continue
                        inp = b.get("input") or {}
                        cmd = inp.get("command") or ""
                        # AN INTERMEDIATE COULD BE CREATED BY THE WRITE TOOL, not only
                        # by a shell command: the auditor's 17,089-byte body is a saved
                        # Write, and a Bash-only producer scan never found it.
                        if b.get("name") == "Write" and str(inp.get("file_path")) == src:
                            extra[n] = (rec, src)
                        elif cmd and writes_this(cmd, os.path.basename(src)):
                            extra[n] = (rec, src)
                        break
    merged = dict((n, rec) for n, rec in own)
    for n, (rec, _src) in extra.items():
        merged.setdefault(n, rec)
    return [(n, merged[n]) for n in sorted(merged)], {
        n: src for n, (_r, src) in extra.items()}


def replay(base_text, basename, first=1, upto=None, checkpoints=None):
    """-> (text, steps). `checkpoints` maps a transcript line -> expected digest AFTER
    that line; each is verified when reached and reported, never used to choose."""
    checkpoints = checkpoints or {}
    text, steps, met = base_text, [], collections.OrderedDict()
    for n, rec in modifying_records(basename, first, upto):
        row = collections.OrderedDict([("line", n)])
        try:
            new, _s = RT.apply_saved_edits(text, {n: rec}, basename)
            row["result"] = "applied" if new != text else "no-change"
            text = new
        except Exception as exc:
            row["result"] = "REFUSED"
            row["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:90])
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        row["sha256"] = digest
        row["bytes"] = len(text.encode("utf-8"))
        if n in checkpoints:
            row["checkpoint"] = checkpoints[n]
            row["checkpoint_met"] = digest == checkpoints[n]
            met[n] = row["checkpoint_met"]
        steps.append(row)
    return text, collections.OrderedDict([
        ("basename", basename), ("first", first), ("upto", upto),
        ("base_sha256", hashlib.sha256(base_text.encode("utf-8")).hexdigest()),
        ("records", len(steps)),
        ("applied", sum(1 for s in steps if s["result"] == "applied")),
        ("refused", sum(1 for s in steps if s["result"] == "REFUSED")),
        ("final_sha256", hashlib.sha256(text.encode("utf-8")).hexdigest()),
        ("final_bytes", len(text.encode("utf-8"))),
        ("checkpoints_met", met), ("steps", steps)])
