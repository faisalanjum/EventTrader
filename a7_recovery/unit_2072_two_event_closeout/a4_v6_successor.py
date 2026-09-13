# -*- coding: utf-8 -*-
"""The SUCCESSOR ROUND of the existing `decision_correction_v6` phase.

Codex SEQ 2072: two whole-event decisions from the completed v6 round are
still unsettled, and the lane has no seventh door. `test_next_boundary_2072`
measures why: `F.PHASES` ends at v6, `F.Bound` has no seventh run field,
`F._HISTORY_OF` has no seventh key, and the frozen owner names no v7 at all.
So this round is the SAME phase, entered a second time - and everything a
second round of one phase needs that F does not yet have is what this module
adds, and nothing else.

F still owns the receipt, native proof, record, resume, finalization, retry
law, materializer, gate, counts, signer and lock. C2065 owns the repaired
source-only prefix; T2069 owns the current-findings connection at the v6
seams. This module owns only the SUCCESSION.

What a second round of one phase needs, measured, and where it is bound:

  * its PRIOR REPLY is the first round's accepted v6 answer, not the v5
    closeout `F.v6_prompt` reads. F's own body is otherwise reproduced
    exactly - same payload owner, same prefix seam, same finding seam, same
    key order - and the prior reply is named `v6_shard` with F's own v6
    origin, because serving a v6 answer under the key `v5_shard` would tell
    the reader the round it is correcting is one round older than it is.
    MEASURED: the served source-only prefix names `v5_shard` exactly once and
    that one mention is the generated key declaration, so the rename carries
    through with no second sentence to keep in step;
  * its MERGE BASE is the first round's completed key. F's `v6_shards`
    replaces whole events on top of `v5_shards`, so `v5_shards` is bound to
    the first round's own merge and F's existing carry-forward does the rest.
    There is no second merge, origin map or gate here;
  * its LEDGER BEFORE is every call already made, the first round's included.
    F's chain stops one round short by construction;
  * its HISTORY is the first round, which F cannot pin because a phase never
    pins itself - true for one round, wrong for the second. Pinned for THIS
    phase only, so the earlier phases' receipts still re-derive untouched;
  * its PRIOR IDENTITIES include that first round for both this round and
    the signer. Pinning old bytes does not seed the native proof's separate
    duplicate-identity check;
  * its POPULATION and FINDINGS come from this round's own reviewed findings,
    which must bind to the FIRST ROUND's accepted raw - never the closeout's.

Everything the first round is read for is read under `first_round_scope`,
which puts every seam this module swaps back before entering the first
round's own real inputs. That is what keeps the first round's frozen prompts,
receipt and finalized bytes reconstructing exactly as they were recorded.

It calls no model, publishes nothing, signs nothing, approves no population,
ceiling or source truth, and clears no open issue by itself.
"""
import collections
import contextlib
import json
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
for _rel in ("unit_2009/owner", "unit_2023_source_correction",
             "unit_2065_closeout_connection", "unit_2069_targeted_source",
             "unit_2005/owner"):
    sys.path.insert(0, str(A7 / _rel))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
import a4_source_closeout as C2065                                 # noqa: E402
import a4_targeted_source as T2069                                 # noqa: E402
from a4_call_accounting import finalized_scheduled as _finalized_scheduled

F, K = R.F, R.K
#: F's OWN phase, entered a second time. No name is coined here.
PHASE = "decision_correction_v6"
#: F's OWN origin for this stage; the merge stamp is unchanged.
ORIGIN = "a4_final_v6_correction"
#: The body key and origin for the reply this round corrects. The round is
#: named for what really produced it.
PRIOR_KEY = "v6_shard"
PRIOR_ORIGIN = ORIGIN + "_reply"

#: Every owner this module swaps at F, captured BEFORE the first swap. Reading
#: the live attribute inside a scope that replaced it would call this module's
#: own function again and recurse forever (the discipline C2065 records for
#: `_F_V5_PROMPT` and V2 for `_C2023_SERVED_PREFIX`).
_ORIGINAL = collections.OrderedDict([
    ("findings_entries", F.findings_entries), ("v5_shards", F.v5_shards),
    ("v6_prompt", F.v6_prompt), ("v6_prefix", F.v6_prefix),
    ("v6_ledger_before", F.v6_ledger_before),
    ("_phase_history", F._phase_history)])
_F_V6_SHARDS = F.v6_shards


def first_bound(bound, first_run):
    """The same binding as the FIRST round had: its run in the v6 slot."""
    return bound._replace(decision_correction_v6=first_run)


@contextlib.contextmanager
def first_round_scope(bound, first_run, first_findings, previous):
    """The first round, read under its OWN inputs.

    Every seam this module swaps is put BACK first, so anything reached from
    here - the frozen prompts, the published receipt, the finalized bytes -
    re-derives exactly as it was recorded. Without the restore, F's `v6_shards`
    would reach this module's `v5_shards` binding and recurse forever.
    """
    with R._using(F, **_ORIGINAL), \
            T2069.correction_scope(first_bound(bound, first_run),
                                   first_findings, previous):
        yield


def first_round_accepted(bound, first_run, first_findings, previous):
    """The first round's accepted shards and their exact raw texts."""
    fb = first_bound(bound, first_run)
    with first_round_scope(bound, first_run, first_findings, previous):
        shards, raws, bad = F.accepted_shards(first_run, fb, PHASE)
    if bad:
        raise ValueError("the first v6 round does not read cleanly: %s"
                         % bad[:2])
    return shards, raws


def first_round_key(bound, first_run, first_findings, previous):
    """The first round's COMPLETE merged key: this successor's base.

    F's own v6 merge, over the first round's own binding and inputs. Not a
    second merge - the value F's `v5_shards` seam is bound to.
    """
    fb = first_bound(bound, first_run)
    with first_round_scope(bound, first_run, first_findings, previous):
        return _F_V6_SHARDS(fb)


def successor_entries(bound, findings, first_run, first_findings, previous):
    """This round's findings at F's ledger seam, bound to the FIRST ROUND.

    The same shape T2069 uses one round earlier, with one difference that is
    the whole point: a finding must bind to the raw this body actually shows,
    and this body shows the first v6 round's accepted reply.
    """
    if not findings:
        raise ValueError("the v6 successor round needs explicit findings")
    _shards, raws = first_round_accepted(bound, first_run, first_findings,
                                         previous)
    result = []
    for sid in findings:
        rows = C2023.entries_for(findings, sid)
        if sid not in raws or not rows:
            raise ValueError("a finding has no accepted first-round v6 "
                             "source: %s" % sid)
        allowed = F._task_by_label(bound.evidence, sid)["rows"]
        for row in rows:
            if (row.get("source_id") != sid
                    or row.get("raw_sha256") != K._sha(raws[sid])
                    or row.get("row") not in allowed):
                raise ValueError("a finding does not bind the exact "
                                 "source/raw/row: %s" % sid)
        result.append((sid, rows))
    return result


def successor_prompt(bound, label, first_run, first_findings, previous):
    """F's OWN v6 body, with the LATEST v6 reply named for what it is.

    Same payload owner, same prefix seam, same finding seam and same key order
    as `F.v6_prompt`. The two differences are the two this round exists for:
    the prior reply comes from the first v6 round rather than the closeout,
    and it is named for the round that produced it.
    """
    _shards, raws = first_round_accepted(bound, first_run, first_findings,
                                         previous)
    if label not in raws:
        raise ValueError("the first v6 round has no accepted shard for %s"
                         % label)
    task = F._task_by_label(bound.evidence, label)
    body = collections.OrderedDict(F.payload(bound, task))
    body[PRIOR_KEY] = collections.OrderedDict([
        ("origin", PRIOR_ORIGIN), ("sha256", K._sha(raws[label])),
        ("raw", raws[label])])
    body["reviewer_finding"] = F.v6_finding_for(bound, label)
    return F.v6_prefix(bound.package, tuple(body)) + json.dumps(body, indent=1)


@contextlib.contextmanager
def successor_scope(bound, findings, first_run, first_findings, previous):
    """This round's inputs, base, count and history at F's OWN v6 seams.

    T2069's connection is entered first and kept: the population, the finding
    lookup and the repaired source-only prefix are ITS owners, reading this
    round's findings through the ledger seam. What is added on top is only
    what a SECOND round of one phase needs.
    """
    # Preserve an outer recovery scope's prior-identity reader. The first
    # round's own proof still excludes itself; its retry sees its parent
    # through the existing owner, not through an added self-reference.
    real_prior = F._prior_runs
    first_dirs = (first_run, os.path.join(first_run, "retry"))

    def entries(package, name):
        if name != F.V6_FINDINGS_NAME:
            # F's OWN reader, captured at import: reading the live attribute
            # here would call this function again and recurse forever.
            return _ORIGINAL["findings_entries"](package, name)
        if os.path.abspath(package) != os.path.abspath(bound.package):
            raise ValueError("the successor findings name a different carrier")
        return successor_entries(bound, findings, first_run, first_findings,
                                 previous)

    def prefix(package, keys):
        if os.path.abspath(package) != os.path.abspath(bound.package):
            raise ValueError("the successor prefix names a different carrier")
        return C2065.closeout_prefix(bound, keys)

    def prompt(b, label):
        return successor_prompt(b, label, first_run, first_findings, previous)

    def base_shards(b):
        return first_round_key(b, first_run, first_findings, previous)

    def ledger_before(b):
        return (_ORIGINAL["v6_ledger_before"](b)
                + _finalized_scheduled(first_run))

    def history(b, phase):
        hist = _ORIGINAL["_phase_history"](b, phase)
        if phase != PHASE:
            # a v5 or earlier receipt pins v1..v4 and nothing else; adding the
            # first v6 round to it would invalidate a finalized run that never
            # changed - exactly the defect F's "a phase NEVER pins itself"
            # comment records one round earlier.
            return hist
        out = collections.OrderedDict(hist)
        out["v6"] = F._run_evidence_pins(first_run)
        return out

    def prior_runs(out_dir, b, receipt):
        runs = real_prior(out_dir, b, receipt)
        if (receipt.get("phase") in (PHASE, "signer")
                and os.path.abspath(out_dir) not in
                {os.path.abspath(p) for p in first_dirs}):
            for run in first_dirs:
                if os.path.isdir(run) and run not in runs:
                    runs.append(run)
        return runs

    with C2065.closeout_scope(*previous), \
            R._using(F, findings_entries=entries, v6_prefix=prefix,
                     v6_prompt=prompt, v5_shards=base_shards,
                     v6_ledger_before=ledger_before, _phase_history=history,
                     _prior_runs=prior_runs):
        yield


def bind(bound, successor_run):
    """Carry the successor round explicitly. There is no fallback."""
    if not successor_run:
        raise ValueError("a successor binding needs its own run; falling back "
                         "to the first v6 round is refused")
    if bound.decision_correction_v5 is None:
        raise ValueError("a v6 round corrects a closeout; this binding "
                         "carries no closeout run")
    return bound._replace(decision_correction_v6=successor_run)
