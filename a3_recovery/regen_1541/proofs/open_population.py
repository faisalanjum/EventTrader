"""Every effective file open in the recovered routes, measured AT THE BOUNDARY.

Codex SEQ 1556 item 2. The previous census read the saved program TEXT with a regex and
hand-listed three owners, so a mode held in a variable, passed by keyword, reached
through an import, or written by an executed script could not be seen at all - and the
route set was three typed rows rather than the chain's live identities.

This measures instead. The routes are DERIVED from the package's own accepted
checkpoint log (owner + cutoff), and an audit-only copy of `_replay` records what the
mode-owning boundary actually decided for every open it served: the resolved target,
the effective mode, owner-or-sibling, and whether the record executed or was refused.
Production is untouched - the instrumented copy exists only inside this process.
"""
import ast
import contextlib
import io
import json
import os
import hashlib
import re
import sys
import types

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
sys.path.insert(0, R)
import chrono_replay as CR                                     # noqa: E402
import replay_transcript as RT                                 # noqa: E402

SRC = os.path.join(R, "ledger", "replay_transcript.py")
#: the two returns the mode-owning boundary can take, and what each one means
BOUNDARY = [
    ('                    keep = side.get(sp, "") if "a" in _extra or "a" in mode else ""\n'
     '                    return _Sink(lambda v, k=sp: side.__setitem__(k, v), keep)',
     '                    keep = side.get(sp, "") if "a" in _extra or "a" in mode else ""\n'
     '                    _AUDIT(sp, _extra if any(m in _extra for m in ("w", "a", "x"))\n'
     '                           else mode, "sibling", n, keep)\n'
     '                    return _Sink(lambda v, k=sp: side.__setitem__(k, v), keep)'),
    ('                _m = _mode_of(mode, args, kwargs)\n'
     '                if "w" in _m:',
     '                _m = _mode_of(mode, args, kwargs)\n'
     '                _AUDIT(sp, _m, "owner", n, state["text"])\n'
     '                if "w" in _m:'),
    # THE THIRD ARM. An open the shim does not serve falls through to the real
    # filesystem; the previous census called two such opens "sibling" by matching
    # their basename, which is a guess about a path the replay never resolved.
    # THE THIRD ARM, MEASURED RATHER THAN ASSUMED. It used to pass a literal "" as the
    # before-state, so all 58 pass-through rows reported zero bytes and one identical
    # digest - a constant dressed as evidence. Now the raw bytes are read at the
    # boundary before the open and again after it returns, and a read-only open must
    # leave them identical.
    # THE READER IS OWNED. Measuring after `open()` returned but before the consumer
    # read could not see a change during the actual read (Codex SEQ 1559 item 2); the
    # returned handle is wrapped and the after-state is measured when it is CLOSED,
    # or at the record's end if the program never closed it. An open that raises
    # still yields a complete row, marked `open_failed`, because the program received
    # that exception in history too.
    # anchored on the owner arm's last line too: the bare return is also the text of
    # the machinery guard at the top of the shim, and an anchor must name ONE place
    ('                raise FileNotFoundError(errno.ENOENT, "not part of the replay world", path)\n'
     '            return _REAL_IO_OPEN(path, mode, *args, **kwargs)',
     '                raise FileNotFoundError(errno.ENOENT, "not part of the replay world", path)\n'
     '            _pt = _AUDIT_PRE(sp, _mode_of(mode, args, kwargs), n)\n'
     '            try:\n'
     '                _fh = _REAL_IO_OPEN(_pt["served_path"], mode, *args, **kwargs)\n'
     '            except BaseException as _e:\n'
     '                _AUDIT_FAILED(_pt, _e)\n'
     '                raise\n'
     '            return _AUDIT_OWN(_pt, _fh)'),
]


def instrumented():
    """-> an audit-only `_replay` that reports every open the boundary served."""
    src = io.open(SRC, encoding="utf-8").read()
    for anchor, replacement in BOUNDARY:
        assert src.count(anchor) == 1, "stale boundary anchor:\n%s" % anchor[:80]
        src = src.replace(anchor, replacement, 1)
    ns = {"__name__": "audit_replay", "__file__": SRC}
    exec(compile(src, "<audit:_replay>", "exec"), ns)
    fn = ns["_replay"]
    return types.FunctionType(fn.__code__, RT.__dict__, fn.__name__,
                              fn.__defaults__, fn.__closure__)


def routes():
    """-> [(owner, cutoff, sha256, bytes, evidence_path)] from THE accepted inventory.

    THE INVENTORY FORMAT HAS ONE OWNER. This used to parse the TSV itself, and when the
    verifier gained a pinned acceptance-archive column the census still expected the old
    field count and refused the file as malformed - two readers of one format, which is
    the same defect class as a control that invents the schema its rule reads. It now
    asks `verify_accepted_checkpoints` for the rows, so the format cannot drift between
    them.
    """
    sys.path.insert(0, R)
    import verify_accepted_checkpoints as VAC
    # the census names the FILE; the verifier owns the FORMAT. A control that
    # redirects the census's root must still reach the parser it actually uses.
    try:
        data = VAC.rows(os.path.join(R, "products", "ACCEPTED_CHECKPOINTS.tsv"))
    except (IOError, OSError, ValueError) as exc:
        raise SystemExit("FAIL: accepted-checkpoint inventory unusable: %s" % exc)
    if not data:
        raise SystemExit("FAIL: accepted-checkpoint inventory is empty")
    return [(r["owner"], int(r["cutoff"]), r["sha256"], int(r["bytes"]),
             r["evidence_path"]) for r in data]


HARNESS = "bench_1306/.claude/plans/Drivers/experiments/harness/"
import census_rules as CRU                                      # noqa: E402
from census_rules import (_raw, _AUDIT_PRE, _AUDIT_POST, _AUDIT_FAILED,   # noqa: E402,F401
                          _AUDIT_OWN, _close_owned_handles, route_failures,
                          row_failures)
opens = CRU.opens


def _digest(text):
    """-> (utf8_byte_count, full sha256). Not len(text), which counts CHARACTERS, and
    not a 16-hex prefix: both were wrong in the previous census."""
    raw = (text or "").encode("utf-8")
    return len(raw), hashlib.sha256(raw).hexdigest()


#: THE TRANSCRIPT AUTHORITY IS THE MANIFESTED PREFIX, never a snapshot of a moving
#: file: `RT.TRANSCRIPT` is evidence/transcript/accepted_prefix.jsonl, and the census
#: refuses to start unless those bytes hash to the accepted identity recorded beside it.
def transcript_authority():
    ident = os.path.join(R, "evidence", "transcript", "ACCEPTED.tsv")
    name, nbytes, nrows, sha = io.open(ident, encoding="utf-8").read().split("\t")[:4]
    raw = RT._REAL_IO_OPEN(RT.TRANSCRIPT, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if os.path.basename(RT.TRANSCRIPT) != name or len(raw) != int(nbytes) \
            or raw.count(b"\n") != int(nrows) or got != sha:
        raise SystemExit("FAIL: the transcript the replay reads is not the accepted "
                         "authority (%s, %d bytes, %d rows) - got %d bytes %s"
                         % (name, int(nbytes), int(nrows), len(raw), got[:16]))
    return {"path": os.path.relpath(RT.TRANSCRIPT, R), "bytes": len(raw),
            "rows": raw.count(b"\n"), "sha256": got}


def _audit(sp, mode, kind, line, before):
    n_bytes, sha = _digest(before)
    opens.append({"resolved_target": sp, "effective_mode": mode, "kind": kind,
                  "transcript_line": line,
                  "before_bytes": n_bytes, "before_sha256": sha})


RT._AUDIT = _audit
RT._AUDIT_PRE = _AUDIT_PRE
RT._AUDIT_POST = _AUDIT_POST
RT._AUDIT_FAILED = _AUDIT_FAILED
RT._AUDIT_OWN = _AUDIT_OWN
AUTHORITY = transcript_authority()

# NOTHING OUTSIDE THE PACKAGE IS OPENED DURING THE CENSUS, BY ANYONE. The shim sees the
# program's opens; this sees every open the process makes - the replay's own machinery
# included - so a live transcript, a checkout or a temporary tree read from anywhere is
# a refusal, not a footnote. Interpreter and system paths are tooling, not evidence.
import collections as _collections
import run_resume_path as _RRP
OUTSIDE = _collections.Counter()


def _os_hook(event, args):
    if event == "open" and args and isinstance(args[0], str):
        ap = os.path.abspath(args[0])
        if not ap.startswith(R) and not ap.startswith(tuple(_RRP.TOOLING)):
            OUTSIDE[ap] += 1


sys.addaudithook(_os_hook)
_UNFAULTED_REPLAY = RT._replay          # identity to compare a fault against
saved_replay = RT._replay
RT._replay = instrumented()
rows = []
by_record = {}
route_lines = set()
try:
    for owner, cutoff, want, want_bytes, ev in routes():
        origin = CR.tree_origin("bench_1306")
        full = HARNESS + owner
        # THE SAME LOOP THE REPORT USES: a committed base, then one record at a time
        # carrying `text` and `side` forward. Replaying the whole route in a single
        # call from an empty base reached almost none of the real opens.
        base = RT._committed("/x/" + full, commit=origin[1]) or ""
        with contextlib.redirect_stdout(io.StringIO()):
            recs, _producers = CR.route_records(full, origin[0], cutoff)
        route_lines.update((owner, cutoff, n) for n, _r in recs)
        text, side = base, {}
        for n, rec in recs:
            start = len(opens)
            outcome, err = "executed", None
            with contextlib.redirect_stdout(io.StringIO()):
                err_msg = None
                try:
                    text, _ = RT.apply_saved_edits(text, {n: rec}, full, side=side)
                except Exception as exc:                       # noqa: BLE001
                    outcome, err, err_msg = "refused", type(exc).__name__, str(exc)
                finally:
                    _close_owned_handles()
            content = rec.get("message", {}).get("content", [{}])[0]
            by_record[(owner, cutoff, n)] = {
                "outcome": outcome, "error": err, "error_message": err_msg,
                "tool_use_id": content.get("id")}
            for row in opens[start:]:
                # THE AFTER STATE, measured once the record completed. Every row had
                # `after_bytes: null` before, so the report could not show what any
                # open did. Owner opens read the owner's text, in-memory siblings read
                # the scratch filesystem, and a pass-through is read from the real file
                # it actually reached - a kind that cannot be read is a refusal.
                sp = row["resolved_target"]
                if row["kind"] == "owner":
                    row["after_bytes"], row["after_sha256"] = _digest(text)
                elif row["kind"] == "sibling":
                    row["after_bytes"], row["after_sha256"] = _digest(side.get(sp, ""))
                # A pass-through's after-state is NOT re-measured here. `_AUDIT_POST`
                # already measured it per OPEN, as raw bytes, from the served (frozen)
                # path. This loop used to decode the LIVE file with errors="replace"
                # and overwrite that - the decode loss Codex named, and a second owner
                # for one measurement. A pass-through row that somehow lacks the
                # per-open after-state fails the REQUIRED-field check below.
                row.update({"owner": owner, "cutoff": cutoff, "want": want,
                            "record_line": n, "record_outcome": outcome,
                            "record_error": err, "record_error_message": err_msg,
                            "tool_use_id": content.get("id")})
                rows.append(row)
finally:
    RT._replay = saved_replay

appends = [r for r in rows if "a" in r["effective_mode"]]


def final_text(owner, cutoff, fault=None):
    """-> (sha256, utf8_bytes) for a whole route, optionally under ONE declared fault.

    ONE fault, never a stack. Both append faults replace `RT._replay`, so entering them
    together made the second capture the FIRST'S MUTANT as the value to restore and
    install its own over it: the first was masked, and the "0 affected" I reported was
    measured with a single fault active. Faults that share a target must be run in
    separate passes, or composed into one owner - never nested.

    Bytes are UTF-8 bytes. The previous version returned `len(text)`, which is
    CHARACTERS, and labelled it bytes; its sizes were smaller than the accepted counts
    for exactly that reason.
    """
    import contextlib as _c
    import hashlib
    full = HARNESS + owner
    origin = CR.tree_origin("bench_1306")
    base = RT._committed("/x/" + full, commit=origin[1]) or ""
    with _c.redirect_stdout(io.StringIO()):
        recs, _p = CR.route_records(full, origin[0], cutoff)
    # A FAULT THAT SILENTLY FAILS TO INSTALL PRODUCES THE SAME DIGEST AS NO FAULT.
    # "0 routes affected" would then be indistinguishable from "the faults never ran",
    # so each pass proves the replacement actually happened before trusting its result.
    ctx = fault.applied(True) if fault is not None else _c.nullcontext()
    with ctx:
        if fault is not None and RT._replay is _UNFAULTED_REPLAY:
            raise SystemExit("FAIL: fault %r did not replace RT._replay; a null result "
                             "from this pass would be meaningless" % fault.note[:40])
        text, side = base, {}
        for n, rec in recs:
            with _c.redirect_stdout(io.StringIO()):
                try:
                    text, _ = RT.apply_saved_edits(text, {n: rec}, full, side=side)
                except Exception:                              # noqa: BLE001
                    pass
                finally:
                    # owned readers opened in a clean or faulted pass are closed at
                    # the record's end here too; their rows are not the census's
                    # rows, but an unclosed handle is a leak, not a measurement
                    _close_owned_handles()
    raw = text.encode("utf-8")
    return (hashlib.sha256(raw).hexdigest(), len(raw))


# AFFECTED OR NOT, measured rather than argued, and measured ONE FAULT AT A TIME.
sys.path.insert(0, R)
import mutations as MU                                         # noqa: E402
APPEND_FAULTS = [("owner append keeps its text",
                  MU.FAULTS["owner append keeps its text"]),
                 ("sibling append keeps its text",
                  MU.FAULTS["sibling append keeps its text"])]
FAILURES = []          # this script REFUSES; it does not report and exit zero


import branch_inventory as BI_for_siblings                       # noqa: E402


def adjudicate_refusals(rows_by_record):
    """Bind every refused record to DURABLE evidence, through the existing ledger.

    Counting refusals is not adjudicating them: the previous census listed 15 refused
    occurrences at five record lines and still reported an empty `failures`, because
    `final_text()` swallowed every exception and moved on.

    The rule is not reinvented here. `branch_inventory.call_outcome` already owns it:
    a replay failure where HISTORY also failed is `faithfully-failed` and expected; a
    replay failure where history SUCCEEDED is `refused` - my defect. The saved result
    comes from the exact result ledger, keyed by the record's own tool_use id, so no
    hand list of "known" refusals is involved.
    """
    import branch_inventory as BI
    L = RT.result_ledger()
    waiting = {L.uses[t] for t in L.outstanding if t in L.uses}
    out = []
    for (owner, cutoff, line), info in sorted(rows_by_record.items()):
        if info["outcome"] != "refused":
            continue
        tid = info.get("tool_use_id")
        present = bool(tid) and L.present(tid)
        result = L.text.get(tid) if tid else None
        verdict = BI.call_outcome(True, result, present, line in waiting,
                                  replay_error=(info.get("error"),
                                                info.get("error_message")))
        row = {"owner": owner, "cutoff": cutoff, "record_line": line,
               "tool_use_id": tid, "replay_error": info.get("error"),
               "replay_error_message": info.get("error_message"),
               "refusal_class": CRU.refusal_class(info.get("error")),
               "result_present": present,
               "historical_verdict": verdict,
               "expected": verdict == "faithfully-failed"}
        out.append(row)
        if not row["expected"] and row["refusal_class"] != "environment":
            FAILURES.append(
                "unexplained refusal at %s@%d line %d: replay raised %s but history's "
                "own result adjudicates it %r, not faithfully-failed"
                % (owner, cutoff, line, "%s: %s" % (info.get("error"),
                                                     info.get("error_message")), verdict))
    return out
per_route = []
for owner, cutoff, want, want_bytes, ev in routes():
    mine = [r for r in rows if r["owner"] == owner and r["cutoff"] == cutoff]
    clean_sha, clean_bytes = final_text(owner, cutoff)
    # THE CLEAN REPLAY IS CHECKED AGAINST THE ACCEPTED INVENTORY, not merely recorded.
    # A census that replays something other than the accepted state proves nothing
    # about the accepted population.
    FAILURES.extend(route_failures(owner, cutoff, want, want_bytes,
                                   clean_sha, clean_bytes, mine))
    under = {}
    for fname, fobj in APPEND_FAULTS:               # ONE AT A TIME, never nested
        f_sha, f_bytes = final_text(owner, cutoff, fobj)
        under[fname] = {"sha256": f_sha, "bytes": f_bytes,
                        "differs_from_clean": f_sha != clean_sha}
    per_route.append({
        "owner": owner, "cutoff": cutoff,
        "accepted_sha256": want, "accepted_bytes": want_bytes, "evidence": ev,
        "clean_sha256": clean_sha, "clean_bytes": clean_bytes,
        "clean_matches_accepted": clean_sha == want and clean_bytes == want_bytes,
        "opens_served": len(mine),
        "by_kind": {k: sum(1 for r in mine if r["kind"] == k)
                    for k in ("owner", "sibling", "passthrough")},
        "appends": sum(1 for r in mine if "a" in r["effective_mode"]),
        "records_refused": sorted({r["record_line"] for r in mine
                                   if r["record_outcome"] == "refused"}),
        "under_each_append_fault": under,
        "affected_by_any_append_fault": any(v["differs_from_clean"]
                                            for v in under.values()),
    })

def _spans_at(line):
    """-> how many saved programs the replay would execute for this record."""
    for owner, cutoff, _w, _b, _e in routes():
        origin = CR.tree_origin("bench_1306")
        with contextlib.redirect_stdout(io.StringIO()):
            recs, _p = CR.route_records(HARNESS + owner, origin[0], cutoff)
        for n, rec in recs:
            if n != line:
                continue
            content = rec.get("message", {}).get("content", [{}])[0]
            cmd = content.get("input", {}).get("command", "")
            return len(RT.program_spans(cmd)) if cmd else 0
    return None


# The two opens the previous census reported, reconciled against what the boundary saw.
# The two record lines my SEQ 1553 census reported as live appends. These are named
# deliberately: this block exists to reconcile MY OWN previous claim, so the claim's
# subject is the input, not a rule inferred from it. Nothing else in this file is
# hand-listed.
CLAIMED = [25826, 26357]
reconciliation = [{
    "record_line": n,
    # MEMBERSHIP, not "did it open anything": the first version of this field asked
    # whether the record appeared in the opens table, which is a different question
    # and would have reported a record that IS in the route as absent from it.
    "in_a_route": any(l == n for _o, _c, l in route_lines),
    "routes_containing_it": sorted({"%s@%d" % (o, c) for o, c, l in route_lines
                                    if l == n}),
    "served_no_open_at_the_boundary":
        not any(r["record_line"] == n for r in rows),
    # WHY it served none: the replay executes SAVED PROGRAMS, and this record has
    # none. The previous census matched `open(..., "a")` in the command TEXT, which
    # the replay never runs, and reported it as a live append.
    "saved_program_spans": _spans_at(n),
    "opens_the_boundary_served_for_this_record":
        [{"kind": r["kind"], "mode": r["effective_mode"],
          "target": r["resolved_target"]}
         for r in rows if r["record_line"] == n],
} for n in CLAIMED]

REQUIRED = CRU.REQUIRED

# EVERY row is written, not just the append subset. The previous report announced
# `opens_total=1453` and then saved only the empty append list, so the number zero was
# concluded from data the report did not contain. A row missing any required field is
# a refusal, not a footnote.
# ONE OWNER for these checks: the module and the controls call the same functions,
# so a control cannot pass against a rule the census does not actually apply.
FAILURES.extend(row_failures(rows, R, REQUIRED))
if OUTSIDE:
    FAILURES.append("%d opens outside the package during the census: %s"
                    % (sum(OUTSIDE.values()), sorted(OUTSIDE)[:5]))
refusals = adjudicate_refusals(by_record)
# REFUSALS INSIDE THE RESOLVER ARE ADJUDICATED TOO. A sibling record that refused is
# faithful only when history's own result carries the same exception; a refusal
# history did not have is a replay defect, however deep in the resolution it sat.
sibling_refusals = []
_L = RT.result_ledger()
_waiting = {_L.uses[t] for t in _L.outstanding if t in _L.uses}
for _r in CR.SIBLING_REFUSALS:
    # history's result for that RECORD LINE, through the replay's own owners of it
    _n = _r["record_line"]
    _hist = RT.saved_result(_n)
    _tid, _observed = RT.background_outcome(_n)
    if _tid and _observed is None:
        # launched in the background and never read back: history holds no outcome
        # for this program at all, so the replay's failure is neither explained nor
        # unexplained - it is reported apart, never folded into either count
        _v = "background-unobserved"
    else:
        _v = BI_for_siblings.call_outcome(True, _observed if _tid else _hist,
                                          RT.result_present(_n), _n in _waiting,
                                          replay_error=(_r["error"], _r["error_message"]))
    row = dict(_r, historical_verdict=_v, expected=(_v == "faithfully-failed"),
               background_task=_tid, refusal_class=CRU.refusal_class(_r["error"]))
    sibling_refusals.append(row)
    if not row["expected"] and row["refusal_class"] != "environment" \
            and _v != "background-unobserved":
        # the innermost frame of the refusal, so the reader sees WHERE, not only what
        _frames = [l.strip() for l in (_r.get("traceback") or "").splitlines() if l.strip().startswith("File ")]
        _hist = (RT.saved_result(_n) or "").strip().splitlines()
        FAILURES.append("unexplained refusal inside the resolver: %s at record %d raised "
                        "%s: %s; adjudicated %r - history's own result at that record ends %r; at %s"
                        % (os.path.basename(_r["path"]), _r["record_line"], _r["error"],
                           _r["error_message"][:120], _v, (_hist[-1] if _hist else "")[:80],
                           _frames[-1][:120] if _frames else "(no traceback)"))
out = {
    "routes_derived_from": "products/ACCEPTED_CHECKPOINTS.tsv",
    "routes": per_route,
    "opens_total": len(rows),
    # records the harness refused to run (`<tool_use_error>` results) that the routes
    # stepped over instead of replaying: measured, never assumed absent
    "rejected_calls_stepped_over": sorted(set(RT.REJECTED_CALLS)),
    "opens": rows,                      # ALL of them, in full
    "open_row_schema": REQUIRED,
    "appends_total": len(appends),
    "appends": appends,
    "by_kind_total": {k: sum(1 for r in rows if r["kind"] == k)
                      for k in ("owner", "sibling", "passthrough")},
    # EVERY PASS-THROUGH ACCOUNTED FOR. These reach the real filesystem rather than the
    # replay's memory, so their after-state is whatever the real file held. One that
    # does not exist is reported as unreadable rather than silently recorded as empty.
    "passthrough_accounting": {
        "total": sum(1 for r in rows if r["kind"] == "passthrough"),
        "after_state_read": sum(1 for r in rows if r["kind"] == "passthrough"
                                and not r.get("unreadable_after")),
        "after_state_unreadable": sum(1 for r in rows if r["kind"] == "passthrough"
                                      and r.get("unreadable_after")),
        "open_failed": sum(1 for r in rows if r.get("open_failed")),
        "closed_by_census": sum(1 for r in rows if r.get("closed_by_census")),
        "outside_package": sum(1 for r in rows if r["kind"] == "passthrough"
                               and not r.get("inside_package") and not r.get("open_failed")),
        "distinct_targets": len({r["resolved_target"] for r in rows
                                 if r["kind"] == "passthrough"}),
    },
    "previous_census_reconciliation": reconciliation,
    "transcript_authority": AUTHORITY,
    "outside_package_os_opens": dict(OUTSIDE),
    "sibling_cache_entries": len(os.listdir(CR._DISK_CACHE)) if os.path.isdir(CR._DISK_CACHE) else 0,
    "refusal_adjudication": refusals,
    "sibling_refusal_adjudication": sibling_refusals,
    "sibling_refusals_unexplained": sum(1 for r in sibling_refusals
                                        if not r["expected"] and r["refusal_class"] != "environment"
                                        and r["historical_verdict"] != "background-unobserved"),
    "sibling_refusals_background_unobserved": sum(1 for r in sibling_refusals
                                                  if r["historical_verdict"] == "background-unobserved"),
    "sibling_refusals_background_adjudicated": sum(1 for r in sibling_refusals
                                                   if r.get("background_task") and r["historical_verdict"] != "background-unobserved"),
    "sibling_refusals_environment": sum(1 for r in sibling_refusals
                                        if r["refusal_class"] == "environment"),
    # the same sibling record is replayed once per route that needs it, so one
    # divergence is recorded several times; the DISTINCT (sibling, record) pairs are
    # the fair count, listed by owner and exception class
    "sibling_refusals_distinct": sorted({(os.path.basename(r["path"]), r["record_line"],
                                          r["error"], r["refusal_class"])
                                         for r in sibling_refusals}),
    "sibling_refusals_distinct_unexplained": len({(r["path"], r["record_line"]) for r in sibling_refusals
                                                  if not r["expected"] and r["refusal_class"] != "environment"}),
    "refusals_expected": sum(1 for r in refusals if r["expected"]),
    "refusals_unexplained": sum(1 for r in refusals
                                if not r["expected"] and r["refusal_class"] != "environment"),
    "refusals_environment": sum(1 for r in refusals if r["refusal_class"] == "environment"),
    "affected_routes": [r["owner"] for r in per_route
                        if r["affected_by_any_append_fault"]],
    "failures": FAILURES,
}
assert sum(out["by_kind_total"].values()) == len(rows), "kind totals do not reconcile"
dest = os.path.join(R, "reports", "open_population.json")
io.open(dest, "w", encoding="utf-8").write(json.dumps(out, indent=2, sort_keys=True) + "\n")
print("routes %d | opens served %d (owner %d, sibling %d, passthrough %d) | appends %d"
      % (len(per_route), len(rows), out["by_kind_total"]["owner"],
         out["by_kind_total"]["sibling"], out["by_kind_total"]["passthrough"],
         len(appends)))
pt = out["passthrough_accounting"]
print("pass-throughs %d: after-state read %d, unreadable %d, distinct targets %d"
      % (pt["total"], pt["after_state_read"], pt["after_state_unreadable"],
         pt["distinct_targets"]))
print("routes whose clean replay matches the accepted inventory: %d of %d"
      % (sum(1 for r in per_route if r["clean_matches_accepted"]), len(per_route)))
print("routes affected by an append fault: %d" % len(out["affected_routes"]))
for r in reconciliation:
    print("  record %d in a route: %s | saved program spans: %s | opens served: %d"
          % (r["record_line"], r["in_a_route"], r["saved_program_spans"],
             len(r["opens_the_boundary_served_for_this_record"])))
if FAILURES:
    print()
    for f in FAILURES:
        print("FAIL %s" % f)
    raise SystemExit(1)          # FAIL CLOSED: a census that found a defect must refuse
print("CENSUS OK")
