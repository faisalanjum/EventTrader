# -*- coding: utf-8 -*-
"""Ordinary exclusive creation for a run's durable targets (Codex SEQ 1876).

A previous attempt's output is EVIDENCE. So this never clears, never
overwrites and never invents a unique name behind the caller's back: the
caller names the target and this either creates it or refuses it.

`os.makedirs` and `os.open(O_CREAT|O_EXCL)` already do the whole job; the only
thing added is one named exception so a refusal reads as a refusal instead of
an errno. The control payload and the native run import THESE functions, so
the refusal that is tested is the one that runs.
"""
import errno, io, os


class TargetExists(Exception):
    """The named target is already there and a previous attempt owns it."""


def new_dir(path):
    """Create `path`. Refuse if anything is already there."""
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise TargetExists("refusing an existing target: %s" % path)
        raise
    return path


def new_file(path, text):
    """Write `text` to a NEW `path`. Refuse if anything is already there."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise TargetExists("refusing an existing target: %s" % path)
        raise
    with io.open(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path
