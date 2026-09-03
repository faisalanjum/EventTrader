"""HISTORY'S OWN PRINTS AS WITNESSES OF THE REBUILT TEXT.

A saved command such as `sed -n '60,110p' test_harness_guards.py` carries, in its saved
result, the bytes the live file had at that moment. Comparing that print with the same
slice of the REBUILT text at the same record is a byte-level check of the replay that
needs no interpretation: where the two agree the reconstruction is right up to there;
the first record where they disagree brackets the divergence between the last agreeing
witness and itself. Diagnostic and evidence at once: nothing here is asserted, every
row is measured.
"""
import contextlib
import io
import os
import re
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [R, os.path.join(R, "ledger")]
import replay_transcript as RT  # noqa: E402
import chrono_replay as CR  # noqa: E402

FOOTERS = ("Shell cwd was reset to", "Session cwd remains")
_SED = re.compile(r"^sed\s+-n\s+'(\d+)(?:,(\d+))?p'\s+\"?([^\"\s|;&]+)\"?\s*$")
_CAT = re.compile(r"^cat\s+\"?([^\"\s|;&]+)\"?\s*$")
_HEAD = re.compile(r"^(head|tail)\s+(?:-n\s*|-)(\d+)\s+\"?([^\"\s|;&]+)\"?\s*$")


def _observed(n):
    lines = (RT.saved_result(n) or "").split("\n")
    while lines and (not lines[-1].strip() or lines[-1].startswith(FOOTERS)):
        lines.pop()
    return lines


def _ops(cmd):
    """-> [(kind, a, b, path)] for the print operations a saved command consists of,
    or [] when the command does anything else (pipes, several prints, edits)."""
    env = RT.shell_vars(cmd)
    ops = []
    for raw in cmd.split("\n"):
        line = RT.expand(raw.strip(), env)
        if not line or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", line) or line.startswith("cd "):
            continue
        if line.startswith("echo "):
            return []
        m = _SED.match(line)
        if m:
            ops.append(("sed", int(m.group(1)), int(m.group(2) or m.group(1)), m.group(3)))
            continue
        m = _CAT.match(line)
        if m:
            ops.append(("cat", None, None, m.group(1)))
            continue
        m = _HEAD.match(line)
        if m:
            ops.append((m.group(1), int(m.group(2)), None, m.group(3)))
            continue
        return []
    return ops if len(ops) == 1 else []


def _names(path, cmd, target):
    if not os.path.isabs(path):
        d = RT.cwd_at(cmd, len(cmd))
        path = os.path.normpath(os.path.join(d, path)) if d else path
    return os.path.normpath(path) == target


def witnesses(target, first, upto):
    """-> rows for every clean print of `target` between `first` and `upto`."""
    rows = []
    base = os.path.basename(target)
    with io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
        for n, raw in enumerate(fh, 1):
            if n < first or n > upto or base not in raw or '"Bash"' not in raw:
                continue
            try:
                rec = RT.lines({n})[n]
                cmd = RT.bash_command(rec)
            except Exception:
                continue
            ops = _ops(cmd)
            if not ops or not _names(ops[0][3], cmd, target):
                continue
            kind, a, b, _ = ops[0]
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    text = CR.sibling_text(target, n) or ""
                except Exception as exc:
                    rows.append({"record": n, "op": kind, "refused": "%s: %s" % (type(exc).__name__, str(exc)[:80])})
                    continue
            lines = text.split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            if kind == "sed":
                expect = lines[a - 1:b]
            elif kind == "cat":
                expect = lines
            elif kind == "head":
                expect = lines[:a]
            else:
                expect = lines[-a:] if a else []
            got = _observed(n)
            # A SAVED RESULT THAT IS A TRACEBACK IS NOT A PRINT: the command died before
            # or instead of printing (record 23340's `sed` never ran), so there is no
            # witness here - neither agreement nor disagreement
            if got and (got[0].startswith("Traceback (most recent call last)") or got[0].startswith('  File "')):
                rows.append({"record": n, "op": kind, "not_a_print": "the saved result is a traceback"})
                continue
            # THE RECORDER TRIMMED THE PRINT. A saved tool result carries neither the
            # leading nor the trailing blank lines the command printed (record 3402's
            # `sed -n '54,180p'` began with an empty line 54 that the result lacks), so
            # the rebuilt slice is trimmed the same way before the bytes are compared.
            while expect and expect[-1] == "":
                expect = expect[:-1]
            while expect and expect[0] == "":
                expect = expect[1:]
            while got and got[0] == "":
                got = got[1:]
            same = expect == got
            first_bad = next((i for i, (x, y) in enumerate(zip(expect, got)) if x != y),
                             None if same else min(len(expect), len(got)))
            rows.append({"record": n, "op": "%s %s%s" % (kind, a or "", ("," + str(b)) if kind == "sed" and b != a else ""),
                         "match": same, "expected_lines": len(expect), "observed_lines": len(got),
                         "first_differing_line": None if same else (a or 1) + (first_bad or 0),
                         "expected": None if same else (expect[first_bad] if first_bad is not None and first_bad < len(expect) else ""),
                         "observed": None if same else (got[first_bad] if first_bad is not None and first_bad < len(got) else "")})
    return rows


def main(target, first, upto):
    rows = witnesses(target, int(first), int(upto))
    ok = [r for r in rows if r.get("match")]
    bad = [r for r in rows if r.get("match") is False]
    print("WITNESSES %s: %d prints, %d agree, %d disagree, %d refused, %d not prints" % (
        os.path.basename(target), len(rows), len(ok), len(bad), sum(1 for r in rows if "refused" in r),
        sum(1 for r in rows if "not_a_print" in r)))
    for r in rows:
        if "not_a_print" in r:
            print("  %6d %-10s NOT A PRINT: %s" % (r["record"], r["op"], r["not_a_print"]))
        elif "refused" in r:
            print("  %6d %-10s REFUSED %s" % (r["record"], r["op"], r["refused"]))
        elif r["match"]:
            print("  %6d %-10s agree (%d lines)" % (r["record"], r["op"], r["expected_lines"]))
        else:
            print("  %6d %-10s DIFFER at line %s: expected %r observed %r" % (
                r["record"], r["op"], r["first_differing_line"], (r["expected"] or "")[:70], (r["observed"] or "")[:70]))
    if bad:
        last_ok = max([r["record"] for r in ok if r["record"] < bad[0]["record"]] or [int(first)])
        print("DIVERGENCE WINDOW: after record %d, at or before record %d" % (last_ok, bad[0]["record"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
