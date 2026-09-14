# -*- coding: utf-8 -*-
"""The SUCCESSOR ROUND of the existing `decision_correction_v6` phase.

Revision 2134: per-round prefix inputs travel through the existing recursion;
scoped input identity participates in the existing evidence cache. Original
2126 and all recorded prompts/results stay immutable. No new lifecycle.

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
    which must bind to the FIRST ROUND's accepted raw - never the closeout's;
  * once a SIGNATURE has already been made, that completed call belongs to all
    three of the ACCUMULATING seams too. It is not another round: its
    directory carries no receipt, no finalization and no raw tree, so every
    per-run reader F has returns nothing for it. Its own published lock owner
    already holds the count, the byte identities and the native identities, so
    `signature_accounting` reads them from there and the seams use them. See
    that function for the measurement and for why no second reader is added.

Everything the first round is read for is read under `first_round_scope`,
which puts every seam this module swaps back before entering the first
round's own real inputs. That is what keeps the first round's frozen prompts,
receipt and finalized bytes reconstructing exactly as they were recorded.

It calls no model, publishes nothing, signs nothing, approves no population,
ceiling or source truth, and clears no open issue by itself.
"""
import collections
import contextlib
import importlib.util
import json
import os
import sys
from importlib.machinery import SourceFileLoader
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
    ("_phase_history", F._phase_history),
    ("_accepted_shards_cached", F._accepted_shards_cached)])
_F_V6_SHARDS = F.v6_shards

#: The signature's OWN owners, where the tree already keeps them. The
#: candidate directory is this module's argument; only the owner is fixed.
_LOCK_OWNERS = A7 / "unit_1955/lock_owners"

#: What the three ACCUMULATING seams need about a call that already happened
#: OUTSIDE a run directory: where it lives, the published lock its own owner
#: has just re-derived from the live bytes, and the identities it spent. The
#: count and the byte pins are read out of that same lock, so there is one
#: place they can come from and it is not this module.
Signature = collections.namedtuple("Signature",
                                   "directory lock_path lock identities")

def _lock_owner(candidate_dir):
    """The published-lock owner, bound to THIS candidate.

    It resolves its candidate, signer directory, lawful attempt range and
    bound-artifact list AT IMPORT from its own documented knob, so a second
    candidate needs a second module object rather than a re-import that would
    quietly answer with the first candidate's paths.
    """
    os.environ["A7_CANDIDATE_DIR"] = candidate_dir
    path = str(_LOCK_OWNERS / "build_final_key_lock.py")
    name = "a4_signature_lock_owner_%s" % K._sha(candidate_dir)[:12]
    spec = importlib.util.spec_from_file_location(
        name, path, loader=SourceFileLoader(name, path))
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    if os.path.abspath(owner.OUT) != candidate_dir:
        raise ValueError("the lock owner bound %s, not %s"
                         % (owner.OUT, candidate_dir))
    return owner


def signature_accounting(candidate_dir):
    """A COMPLETED SIGNATURE, through its own published-lock owner.

    A signature is not another round of a phase. Its directory holds a
    manifest, a launcher, a raw, an evidence record and a reply - no receipt,
    no finalization, no raw tree - so every per-run reader F has answers
    nothing for it. MEASURED, `codex_keyboundary2121_c/POST_SIGNATURE_
    ACCOUNTING_PROBE.json`: with the signature already made, the source-key
    ledger still gives the pre-signature count, no history tag appears for it,
    and the legacy identity reader returns (0, 0, 0, 0) at that directory.

    Teaching F a second directory format would be a second signer validator.
    It is not needed: the signature's own owner already holds all three facts.

      * `build_final_key_lock.verify` re-derives every bound value from the
        LIVE bytes and proves every attempt with `signer_proof.prove`, so a
        missing, moved or tampered signature refuses HERE instead of being
        counted. That refusal is the whole admission rule;
      * its `call_accounting` is the count and `artifacts` the byte pins - the
        values the published lock recorded BEFORE anything could move, which
        is exactly why comparing them to the live bytes catches drift;
      * `signer_proof.prove` is asked once more for the identities the
        verification does not hand back. Same owner, same bytes, same shared
        response-identity dictionary - a second READING, never a second rule.

    NOT CACHED, deliberately. Caching this on the directory would answer a
    LATER caller from an EARLIER verification, so bytes edited at that same
    path after one clean read would keep being counted as verified - the one
    thing this function exists to refuse. Each caller re-reads the live bytes.
    The seams therefore read it ONCE, when their scope is entered.

    -> Signature
    """
    owner = _lock_owner(candidate_dir)
    if not os.path.isfile(owner.LOCK):
        raise ValueError("there is no published signature lock at %s"
                         % owner.LOCK)
    lock = K._load(owner.LOCK)
    # The lock NAMES its own authority; the owner then re-hashes that file and
    # refuses if the bytes moved. Reading the name from the lock is what keeps
    # this module free of a second, competing authority constant.
    owner.AUTHORITY = os.path.join(owner.MAILBOX,
                                   lock["authority"]["instruction"])
    str(_LOCK_OWNERS) in sys.path or sys.path.insert(0, str(_LOCK_OWNERS))
    import signer_proof as SP                                   # noqa: E402
    # Re-derive source-key inputs in their ordinary role before the native
    # signer proof changes K's model seat. This fresh owner's existing memo
    # is then reused by verify(); no proof or decision is substituted.
    owner._candidate_problems()
    # The signer's own seat: `signer_proof` compares the returned model,
    # effort and agent type against K's constants, which are the source-key
    # role's for the duration of one serial scope.
    with R.SK._key_role_binding():
        bad = owner.verify(lock)
        if bad:
            raise ValueError("the completed signature does not verify: %s"
                             % bad[:2])
        manifest = K._load(owner.BOUND["signer_manifest"])
        seen, runs, agents = {}, set(), set()
        for n in owner._chain():
            kind, record_path = owner._slot(n)
            if kind != "evidence":
                # A refused invocation earned no call and spent no identity;
                # the owner's own verification already says so.
                continue
            record = K._load(record_path)
            proof, why = SP.prove(owner.SIG, manifest, n, record.get("run_id"),
                                  owner.SESS, seen)
            if why:
                raise ValueError("the completed signature does not prove: %s"
                                 % why[:2])
            runs.add(proof["run_id"])
            agents.add(proof["agent_id"])
    return Signature(
        directory=os.path.abspath(owner.SIG), lock_path=owner.LOCK, lock=lock,
        identities=(runs, agents, {m for m, _q in seen},
                    {q for _m, q in seen}))


def first_bound(bound, first_run):
    """The same binding as the FIRST round had: its run in the v6 slot."""
    return bound._replace(decision_correction_v6=first_run)


def _checked_prefixes(prefixes, runs):
    """Explicit per-round renderers; no version guessing or fallback."""
    result = dict(prefixes or {})
    if set(result) - set(runs):
        raise ValueError("a prefix names a round outside this history")
    if any(not callable(fn) for fn in result.values()):
        raise ValueError("each round prefix must be callable")
    return result


@contextlib.contextmanager
def _round_input_scope(bound, findings, previous, rounds, signatures, prefixes):
    """Restore one round's input at the existing prefix and evidence-cache seams.

    Renderers accept bound and return the source-only task text. They are
    supplied by the byte-pinned caller, not inferred from any model reply.
    Only the prefix call changes; earlier prompt bodies keep their own scopes.

    The existing operation cache omits these scoped inputs. The actual
    core_warm_missing test accepted seven replies after their required wording
    was removed. Add the input identity to that cache's existing expectation
    key; do not clear it, create another cache or weaken receipt verification.
    """
    run = bound.decision_correction_v6
    renderer = (prefixes or {}).get(run)
    installed = F.v6_prefix
    original_cache = _ORIGINAL["_accepted_shards_cached"]
    context = K._sha(json.dumps([findings, previous, rounds, signatures]))

    def prefix(package, keys):
        if renderer is None:
            return installed(package, keys)
        with R._using(C2065.V2, served_prefix=renderer):
            return installed(package, keys)

    def cached(event_dir, b, phase, receipt_sha, expected):
        if phase == PHASE and event_dir == run:
            # Derive the prefix under the LIVE scope, including a caller's
            # current-round install. The receipt owner still compares every
            # complete prompt, including its actual body-key declaration.
            expected = (expected, context,
                        K._sha(F.v6_prefix(b.package, ())))
        return original_cache(event_dir, b, phase, receipt_sha, expected)

    cached.cache_clear = original_cache.cache_clear
    with R._using(F, v6_prefix=prefix, _accepted_shards_cached=cached):
        yield


@contextlib.contextmanager
def first_round_scope(bound, first_run, first_findings, previous, prior=(),
                      signatures=None, prefixes=None):
    """The PREDECESSOR round, read under its OWN inputs.

    Every seam this module swaps is put BACK first, so anything reached from
    here - the frozen prompts, the published receipt, the finalized bytes -
    re-derives exactly as it was recorded. Without the restore, F's `v6_shards`
    would reach this module's `v5_shards` binding and recurse forever.

    `prior` is the SAVED CHAIN of the rounds before the predecessor, oldest
    first, each `(run, findings)`. Empty means the predecessor is the FIRST
    v6 round, whose inputs are T2069's - byte-identical to this function
    before the chain existed. Non-empty means the predecessor is itself a
    successor, so it is read under THIS module's scope over its own
    predecessor. MEASURED (test_resume_boundary_2076): asking T2069's reader
    for a later round refuses, because it validates that round's findings
    against the CLOSEOUT raws while they are bound to the round before it.
    The chain is data from the packet record, not a second Bound field.
    """
    fb = first_bound(bound, first_run)
    prefixes = _checked_prefixes(prefixes,
                                tuple(r for r, _f in prior) + (first_run,))
    if prior:
        inner = successor_scope(fb, first_findings, prior[-1][0], prior[-1][1],
                                previous, tuple(prior[:-1]),
                                signatures=signatures, prefixes=prefixes)
    else:
        if signatures:
            raise ValueError("a signature cannot be attached before this first v6 round")
        inner = T2069.correction_scope(fb, first_findings, previous)
    with R._using(F, **_ORIGINAL), inner:
        if prior:
            yield                 # successor_scope owns this round's inputs
        else:
            with _round_input_scope(fb, first_findings, previous, (),
                                    signatures, prefixes):
                yield


def first_round_accepted(bound, first_run, first_findings, previous, prior=(),
                         signatures=None, prefixes=None):
    """The first round's accepted shards and their exact raw texts."""
    fb = first_bound(bound, first_run)
    with first_round_scope(bound, first_run, first_findings, previous,
                           prior, signatures=signatures, prefixes=prefixes):
        shards, raws, bad = F.accepted_shards(first_run, fb, PHASE)
    if bad:
        raise ValueError("the first v6 round does not read cleanly: %s"
                         % bad[:2])
    return shards, raws


def first_round_key(bound, first_run, first_findings, previous, prior=(),
                    signatures=None, prefixes=None):
    """The first round's COMPLETE merged key: this successor's base.

    F's own v6 merge, over the first round's own binding and inputs. Not a
    second merge - the value F's `v5_shards` seam is bound to.
    """
    fb = first_bound(bound, first_run)
    with first_round_scope(bound, first_run, first_findings, previous,
                           prior, signatures=signatures, prefixes=prefixes):
        key = _F_V6_SHARDS(fb)
    if key[3]:
        raise ValueError("the current merged key does not read cleanly: %s"
                         % key[3][:2])
    return key


def successor_entries(bound, findings, first_run, first_findings, previous,
                      prior=(), signatures=None, prefixes=None):
    """This round's findings at F's ledger seam, bound to the FIRST ROUND.

    The same shape T2069 uses one round earlier, with one difference that is
    the whole point: a finding must bind to the raw this body actually shows,
    and this body shows the first v6 round's accepted reply.
    """
    if not findings:
        raise ValueError("the v6 successor round needs explicit findings")
    _shards, raws, _origins, _bad = first_round_key(
        bound, first_run, first_findings, previous, prior,
        signatures=signatures, prefixes=prefixes)
    result = []
    for sid in findings:
        rows = C2023.entries_for(findings, sid)
        if sid not in raws or not rows:
            raise ValueError("a finding has no accepted current-key "
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


def successor_prompt(bound, label, first_run, first_findings, previous,
                     prior=(), signatures=None, prefixes=None):
    """F's OWN v6 body, with the LATEST v6 reply named for what it is.

    Same payload owner, same prefix seam, same finding seam and same key order
    as `F.v6_prompt`. The two differences are the two this round exists for:
    the prior reply comes from the first v6 round rather than the closeout,
    and it is named for the round that produced it.
    """
    _shards, raws, origins, _bad = first_round_key(
        bound, first_run, first_findings, previous, prior,
        signatures=signatures, prefixes=prefixes)
    if label not in raws:
        raise ValueError("the current key has no accepted shard for %s"
                         % label)
    task = F._task_by_label(bound.evidence, label)
    body = collections.OrderedDict(F.payload(bound, task))
    # Preserve completed v6 prompts byte-for-byte. Inherited replies retain
    # their actual origin instead of being mislabeled as this round's output.
    prior_key = PRIOR_KEY if origins[label] == ORIGIN else "prior_key_shard"
    body[prior_key] = collections.OrderedDict([
        ("origin", origins[label] + "_reply"), ("sha256", K._sha(raws[label])),
        ("raw", raws[label])])
    body["reviewer_finding"] = F.v6_finding_for(bound, label)
    return F.v6_prefix(bound.package, tuple(body)) + json.dumps(body, indent=1)


@contextlib.contextmanager
def successor_scope(bound, findings, first_run, first_findings, previous,
                    prior=(), signature=None, signatures=None, prefixes=None):
    """This round's inputs, base, count and history at F's OWN v6 seams.

    T2069's connection is entered first and kept: the population, the finding
    lookup and the repaired source-only prefix are ITS owners, reading this
    round's findings through the ledger seam. What is added on top is only
    what a SECOND round of one phase needs.

    `signatures` maps each round preceded by a completed signature to its
    candidate directory. The existing `signature` argument is the shorthand
    for a signature immediately before this round. Each is read once, HERE: the reading enters the
    signer's own role binding, which swaps K's transport constants for the
    length of one serial scope, and a seam that entered it half way through a
    preparation would do that under a receipt already being written.
    """
    # Preserve an outer recovery scope's prior-identity reader. A round's own
    # proof still excludes itself; its retry sees its parent through the
    # existing owner, not through an added self-reference.
    real_prior = F._prior_runs
    real_spent = F._spent_identities
    #: EVERY completed round this one follows, oldest first. The three seams
    #: that ACCUMULATE - identities, calls and history - must each walk the
    #: whole chain, not just the immediate predecessor: with only the
    #: predecessor, a third round protected 1 of 2 earlier rounds' identities
    #: and counted 659 instead of 665 (measured, attempt core_chain2076_a).
    chain_runs = tuple(r for r, _f in prior) + (first_run,)
    # A signature belongs BEFORE an exact round, not permanently after the
    # last predecessor. Keep that boundary when a completed round is cold-read.
    # The old argument is the byte-compatible shorthand for this round.
    current_run = bound.decision_correction_v6
    prefixes = _checked_prefixes(prefixes, chain_runs + (current_run,))
    signatures = dict(signatures or {})
    if signature:
        if current_run in signatures and signatures[current_run] != signature:
            raise ValueError("two signatures name the same round boundary")
        signatures[current_run] = signature
    if set(signatures) - set(chain_runs + (current_run,)):
        raise ValueError("a signature names a round outside this history")
    if len({os.path.abspath(p) for p in signatures.values()}) != len(signatures):
        raise ValueError("a completed signature cannot be counted twice")
    completed = collections.OrderedDict()
    rounds = tuple(prior) + ((first_run, first_findings),)
    for n, (run, _findings) in enumerate(rounds + ((current_run, findings),)):
        if run not in signatures:
            continue
        if n == 0:
            raise ValueError("a signature cannot precede the first v6 round")
        before_run, before_findings = rounds[n - 1]
        earlier = {r: p for r, p in signatures.items()
                   if r in chain_runs[:n]}
        # Its candidate must re-derive in the history that was signed, not
        # under the later correction's temporarily installed field readers.
        with first_round_scope(bound, before_run, before_findings, previous,
                               rounds[:n - 1], signatures=earlier,
                               prefixes={r: p for r, p in prefixes.items()
                                         if r in chain_runs[:n]}):
            completed[run] = signature_accounting(signatures[run])
    predecessor_signatures = {r: p for r, p in signatures.items()
                              if r in chain_runs}
    predecessor_prefixes = {r: p for r, p in prefixes.items()
                            if r in chain_runs}
    first_dirs = tuple(d for run in chain_runs
                       for d in (run, os.path.join(run, "retry")))

    def entries(package, name):
        if name != F.V6_FINDINGS_NAME:
            # F's OWN reader, captured at import: reading the live attribute
            # here would call this function again and recurse forever.
            return _ORIGINAL["findings_entries"](package, name)
        if os.path.abspath(package) != os.path.abspath(bound.package):
            raise ValueError("the successor findings name a different carrier")
        return successor_entries(bound, findings, first_run, first_findings,
                                 previous, prior,
                                 signatures=predecessor_signatures,
                                prefixes=predecessor_prefixes)

    def prefix(package, keys):
        if os.path.abspath(package) != os.path.abspath(bound.package):
            raise ValueError("the successor prefix names a different carrier")
        return C2065.closeout_prefix(bound, keys)

    def prompt(b, label):
        return successor_prompt(b, label, first_run, first_findings,
                                previous, prior,
                                signatures=predecessor_signatures,
                               prefixes=predecessor_prefixes)

    def base_shards(b):
        return first_round_key(b, first_run, first_findings, previous, prior,
                               signatures=predecessor_signatures,
                                 prefixes=predecessor_prefixes)

    def ledger_before(b):
        total = _ORIGINAL["v6_ledger_before"](b)
        for run in chain_runs + (current_run,):
            if run in completed:
                account = completed[run].lock["call_accounting"]
                if account["ledger_before"] != total:
                    raise ValueError("the completed signature was budgeted after %d "
                                     "calls but this phase counts %d"
                                     % (account["ledger_before"], total))
                total = account["ledger_after"]
            if run != current_run:
                total += _finalized_scheduled(run)
        return total

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
        # each earlier round of this same phase is pinned under its own tag,
        # so an edit to ANY of them diverges. With an empty chain this loop
        # adds nothing and the receipt is byte-identical to a first successor.
        for n, (run, _f) in enumerate(prior):
            out["v6_round%d" % (n + 1)] = F._run_evidence_pins(run)
        for n, sig in enumerate(completed.values()):
            # Preserve the first signature's recorded tag byte-for-byte.
            tag = "signature" if n == 0 else "signature_%d" % (n + 1)
            out[tag] = collections.OrderedDict(sig.lock["artifacts"])
        return out

    #: Every directory whose identities a NEW call of this phase must not
    #: reuse: the earlier rounds, and the signature if one has been made.
    spent_signatures = {sig.directory: sig.identities
                        for sig in completed.values()}
    spent_dirs = first_dirs + tuple(spent_signatures)

    def prior_runs(out_dir, b, receipt):
        runs = real_prior(out_dir, b, receipt)
        if (receipt.get("phase") in (PHASE, "signer")
                and os.path.abspath(out_dir) not in
                {os.path.abspath(p) for p in spent_dirs}):
            for run in spent_dirs:
                if os.path.isdir(run) and run not in runs:
                    runs.append(run)
        return runs

    def spent(run_dir):
        # ONLY the signature's own directory is answered from its own proof;
        # every ordinary run keeps F's receipt reader exactly as it is.
        if os.path.abspath(run_dir) in spent_signatures:
            return spent_signatures[os.path.abspath(run_dir)]
        return real_spent(run_dir)

    swaps = dict(findings_entries=entries, v6_prefix=prefix, v6_prompt=prompt,
                 v5_shards=base_shards, v6_ledger_before=ledger_before,
                 _phase_history=history, _prior_runs=prior_runs)
    if completed:
        swaps["_spent_identities"] = spent
    with C2065.closeout_scope(*previous), R._using(F, **swaps):
        with _round_input_scope(bound, findings, previous, rounds,
                                signatures, prefixes):
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
