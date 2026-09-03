"""THE CENSUS RULES, one importable owner (Codex SEQ 1559 item 5).

The census module replays everything at import, so its rules could only be reached by
compiling slices of its source - and a slice cannot be mutated by the harness. These
functions are the same ones the census calls; the controls import this module, and the
mutation harness declares faults against it.
"""
import hashlib
import io
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
import replay_transcript as RT                                 # noqa: E402

#: every open the boundary served, appended by the audit functions below
opens = []


def _raw(path):
    """-> (bytes, sha256) read as RAW BYTES. No decode, so no `errors='replace'` can
    quietly lose data and still produce a digest.

    Read through `RT._REAL_IO_OPEN` - the unpatched primitive the replay ITSELF serves
    pass-throughs with - never `io.open`. While a saved program runs the replay swaps
    `io.open` for its shim, so measuring through `io.open` re-entered the shim, which
    called this measurement again: RecursionError on every pass-through, which the
    census then refused as unexplained. One primitive for "the real open", owned by the
    replay, shared by its census."""
    try:
        raw = RT._REAL_IO_OPEN(path, "rb").read()
    except (IOError, OSError):
        return None, None
    return len(raw), hashlib.sha256(raw).hexdigest()


def _AUDIT_PRE(sp, mode, line):
    """Measure a pass-through target BEFORE the open, as raw bytes."""
    n_bytes, sha = _raw(sp)
    row = {"resolved_target": sp, "served_path": sp, "effective_mode": mode,
           "kind": "passthrough", "transcript_line": line,
           "inside_package": os.path.realpath(sp).startswith(os.path.realpath(R)),
           "before_bytes": n_bytes, "before_sha256": sha}
    if n_bytes is None:
        row["before_bytes"], row["before_sha256"] = 0, None
        row["unreadable_before"] = True
    opens.append(row)
    return row


def _AUDIT_POST(row):
    """Measure the same target after the consumer is DONE with it - on close, or at
    the record's end. A read-only open must leave the bytes identical; anything else
    is drift and is refused."""
    if row.get("after_measured"):
        return
    row["after_measured"] = True
    n_bytes, sha = _raw(row["served_path"])
    row["after_bytes"] = 0 if n_bytes is None else n_bytes
    row["after_sha256"] = sha
    if n_bytes is None:
        row["unreadable_after"] = True
    read_only = not any(m in row["effective_mode"] for m in ("w", "a", "x", "+"))
    row["read_only"] = read_only
    row["pre_post_identical"] = (row["before_sha256"] == sha)
    if read_only and not row["pre_post_identical"]:
        row["drift_under_read_only_open"] = True


def _AUDIT_FAILED(row, exc):
    """The open itself raised: the program received that exception, and nothing was
    read or written. The row is completed rather than left half-measured."""
    row["open_failed"] = type(exc).__name__
    row["after_measured"] = True
    row["after_bytes"], row["after_sha256"] = row["before_bytes"], row["before_sha256"]
    row["read_only"] = not any(m in row["effective_mode"] for m in ("w", "a", "x", "+"))
    row["pre_post_identical"] = True


_OWNED = []


class _Owned(object):
    """The returned reader, owned by the census: every attribute is the real handle's,
    and closing it - or the record ending - measures the after-state."""
    def __init__(self, fh, row):
        object.__setattr__(self, "_fh", fh)
        object.__setattr__(self, "_row", row)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_fh"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_fh"), name, value)

    def __iter__(self):
        return iter(object.__getattribute__(self, "_fh"))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False

    def close(self):
        fh, row = object.__getattribute__(self, "_fh"), object.__getattribute__(self, "_row")
        try:
            fh.close()
        finally:
            _AUDIT_POST(row)


def _AUDIT_OWN(row, fh):
    owned = _Owned(fh, row)
    _OWNED.append(owned)
    return owned


def _close_owned_handles():
    """At the record's end, measure every handle the program never closed."""
    while _OWNED:
        h = _OWNED.pop()
        row = object.__getattribute__(h, "_row")
        if not row.get("after_measured"):
            row["closed_by_census"] = True
            h.close()



def route_failures(owner, cutoff, want_sha, want_bytes, clean_sha, clean_bytes, opens):
    """-> the defects in ONE route's clean replay. Pure, so a control can exercise it."""
    bad = []
    if clean_sha != want_sha:
        bad.append("checkpoint mismatch %s@%d: replayed %s, accepted %s"
                   % (owner, cutoff, clean_sha, want_sha))
    if clean_bytes != want_bytes:
        bad.append("byte-count mismatch %s@%d: replayed %d, accepted %d"
                   % (owner, cutoff, clean_bytes, want_bytes))
    if not opens:
        bad.append("no opens recorded for %s@%d" % (owner, cutoff))
    return bad


def row_failures(rows, package_root, required):
    """-> the defects in the collected open rows. Pure, for the same reason.

    EVERY required field must be present AND non-null - one owner, the `required`
    list, never a second hand-list of "the null-sensitive ones". Malformed rows are
    refused, never indexed: a missing `kind` used to raise KeyError here instead of
    returning a refusal (Codex SEQ 1559 item 2)."""
    bad = []
    incomplete = [r for r in rows if any(k not in r or r.get(k) is None for k in required)]
    if incomplete:
        bad.append("%d open rows are missing or null in a required field" % len(incomplete))
    odd = [r for r in rows if r.get("kind") not in ("owner", "sibling", "passthrough")]
    if odd:
        bad.append("%d opens have an unexplained kind" % len(odd))
    drifted = [r for r in rows if r.get("drift_under_read_only_open")]
    if drifted:
        bad.append("%d read-only opens saw the target change under them" % len(drifted))
    # a target that could not be read is faithful ONLY when the open itself failed,
    # because then the program received that failure too; an open that succeeded
    # over bytes the census could not read is a measurement gap
    unread = [r for r in rows if (r.get("unreadable_before") or r.get("unreadable_after"))
              and not r.get("open_failed")]
    if unread:
        bad.append("%d opens succeeded over bytes the census could not read" % len(unread))
    root = os.path.realpath(package_root) if package_root else None
    outside = [r for r in rows if r.get("kind") == "passthrough" and not r.get("open_failed")
               and root is not None
               and not os.path.realpath(str(r.get("resolved_target"))).startswith(root)]
    if outside:
        bad.append("%d pass-throughs read outside the package" % len(outside))
    return bad



REQUIRED = ["owner", "cutoff", "record_line", "tool_use_id", "record_outcome",
            "resolved_target", "effective_mode", "kind",
            "before_bytes", "before_sha256", "after_bytes", "after_sha256"]


#: The replay's OWN typed inability. `ReplayEnvironmentError` is raised by the stand-in
#: the replay installs for what it cannot provide (a subprocess against a vanished tree).
#: Such a refusal is explained by the replay's declared limitation - by its own class
#: name, never by a keyword - so it is reported in its own column: never faithful, never
#: unexplained, and never silent.
ENVIRONMENT_ERRORS = ("ReplayEnvironmentError",)


def refusal_class(error_name):
    """-> "environment" for the replay's own typed inability, else "program"."""
    return "environment" if error_name in ENVIRONMENT_ERRORS else "program"
