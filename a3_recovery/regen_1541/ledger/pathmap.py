"""The explicit durable-path map (Codex SEQ 1539 item 4).

Recovered owners carry the historical logical paths - `/tmp/claude-1000/.../scratchpad/...`
- and those strings must stay exactly as they were, because serialized identities were
computed over them. This module leaves every string alone and redirects only the PHYSICAL
filesystem access, so nothing is read from or written to /tmp and no symlink is made.

A mapped read of a path that has no durable counterpart fails as a plain missing file, so a
gap is reported by the owner that needed it rather than hidden by the map.
"""
import builtins
import contextlib
import io
import os

#: logical prefix -> durable prefix, longest first at match time
_RULES = []


def rules():
    return list(_RULES)


def set_rules(pairs):
    global _RULES
    _RULES = sorted(((str(a).rstrip("/"), str(b).rstrip("/")) for a, b in pairs),
                    key=lambda r: -len(r[0]))
    return rules()


def translate(path):
    p = str(path)
    for logical, physical in _RULES:
        if p == logical or p.startswith(logical + "/"):
            return physical + p[len(logical):]
    return p


@contextlib.contextmanager
def mapped():
    """Redirect physical file access for the duration of a replay."""
    real = {"io_open": io.open, "open": builtins.open,
            "isfile": os.path.isfile, "isdir": os.path.isdir,
            "exists": os.path.exists, "listdir": os.listdir,
            "makedirs": os.makedirs, "stat": os.stat, "remove": os.remove}

    def io_open(path, *a, **kw):
        target = translate(path)
        if any(m in (a[0] if a else kw.get("mode", "r")) for m in ("w", "a", "x")):
            d = os.path.dirname(target)
            if d and not real["isdir"](d):
                real["makedirs"](d)
        return real["io_open"](target, *a, **kw)

    def _open(path, *a, **kw):
        return io_open(path, *a, **kw)

    io.open = io_open
    builtins.open = _open
    os.path.isfile = lambda p: real["isfile"](translate(p))
    os.path.isdir = lambda p: real["isdir"](translate(p))
    os.path.exists = lambda p: real["exists"](translate(p))
    os.listdir = lambda p=".": real["listdir"](translate(p))
    os.makedirs = lambda p, *a, **kw: real["makedirs"](translate(p), *a, **kw)
    os.stat = lambda p, *a, **kw: real["stat"](translate(p), *a, **kw)
    os.remove = lambda p: real["remove"](translate(p))
    try:
        yield translate
    finally:
        io.open = real["io_open"]
        builtins.open = real["open"]
        os.path.isfile = real["isfile"]
        os.path.isdir = real["isdir"]
        os.path.exists = real["exists"]
        os.listdir = real["listdir"]
        os.makedirs = real["makedirs"]
        os.stat = real["stat"]
        os.remove = real["remove"]
