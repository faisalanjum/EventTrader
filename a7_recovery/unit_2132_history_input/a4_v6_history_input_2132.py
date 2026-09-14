# -*- coding: utf-8 -*-
"""Each completed round's OWN served input, preserved when it becomes history.

Codex SEQ 2132. THE DEFECT, measured first as `core_repro2132_a`: the real
current `B.scope` renders the live round under the clarified wording, but that
wording lives only in the OUTER scope. When the same completed round is handed
to the existing cold reader as a PREDECESSOR, `first_round_scope` restores F's
originals and re-derives it under the HISTORICAL unclarified wording, so its
published receipt refuses its own prompts:

    the current merged key does not read cleanly: receipt.prompts is not the
    expected value; 7 events have no accepted shard

WHAT THIS ADDS, and nothing more: a round may declare the wording it was
ACTUALLY served under, pinned by that renderer's bytes, and the cold
reconstruction installs THAT wording for THAT round only. A round which
declares nothing keeps the historical original, so every earlier round is
byte-unchanged and no old call is relabelled.

WHAT IT REFUSES TO DO: it never infers a version from a model answer, never
accepts a receipt whose prompts it cannot re-derive, and adds no lifecycle,
cache or registry. The accepted owner, renderer and round binding are imported
and used unchanged; this module owns only the per-round input.
"""
import collections
import contextlib
import importlib.util
import os
import sys
from importlib.machinery import SourceFileLoader

sys.dont_write_bytecode = True

#: The wording a completed round was served under: WHICH renderer, pinned by
#: its bytes, and which attribute on it carries the prefix. Byte-bound, and
#: carrying no company, event or round name.
RoundInput = collections.namedtuple("RoundInput",
                                    "renderer_path renderer_sha256 attr")


def round_input(sha_file, renderer_path, renderer_sha256,
                attr="served_prefix"):
    """Declare one round's served wording, refusing a pin that does not match.

    The hash is checked HERE, at declaration, so a wrong or moved renderer is
    named before any reconstruction starts rather than surfacing later as an
    unexplained prompt mismatch.
    """
    path = os.path.abspath(renderer_path)
    if not os.path.isfile(path):
        raise ValueError("the declared renderer does not exist: %s" % path)
    got = sha_file(path)
    if got != renderer_sha256:
        raise ValueError("the declared renderer is %s, not the pinned %s: %s"
                         % (got, renderer_sha256, path))
    return RoundInput(renderer_path=path, renderer_sha256=renderer_sha256,
                      attr=attr)


def _wording(sha_file, ri):
    """The declared renderer's prefix function, re-checked at use."""
    got = sha_file(ri.renderer_path)
    if got != ri.renderer_sha256:
        raise ValueError("the declared renderer moved: %s is %s, not %s"
                         % (ri.renderer_path, got, ri.renderer_sha256))
    name = "round_input_%s" % ri.renderer_sha256[:12]
    spec = importlib.util.spec_from_file_location(
        name, ri.renderer_path,
        loader=SourceFileLoader(name, ri.renderer_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, ri.attr, None)
    if not callable(fn):
        raise ValueError("the declared renderer has no callable %r: %s"
                         % (ri.attr, ri.renderer_path))
    return fn


def _aware(E, carrier, inputs, base):
    """`base` plus each round's own declared wording, chosen by the bound run.

    `v6_prompt` is the one owner handed the bound round, so the run in the v6
    slot names which round is being derived and an installed wording can never
    leak into another round.

    Each renderer is resolved ONCE, here, while the carrier still holds its
    ORIGINAL prefix. MEASURED (core_hist2132_b): the merge derives a prompt
    inside another prompt derivation, so resolving per call re-imported the
    renderer while the carrier was already swapped, and the fresh copy took
    the SWAPPED prefix as its base - applying the clarification twice and
    breaking the very receipt this repair exists to re-derive.
    """
    R = E.R
    declared = collections.OrderedDict(
        (run, _wording(E.G._sha_file, ri)) for run, ri in inputs.items())

    def prompt(bound, label):
        fn = declared.get(bound.decision_correction_v6)
        if fn is None:
            return base(bound, label)
        with R._using(carrier, served_prefix=fn):
            return base(bound, label)

    return prompt


@contextlib.contextmanager
def restored_wording(E, X, carrier, inputs):
    """Make the owner's OWN restore hand back a wording-aware prompt.

    THE REASON THIS IS NOT A PLAIN SWAP: the accepted owner restores F's
    captured originals every time it reconstructs a historical round, so a
    wording installed around it is wiped by that restore (measured, the
    `ledger` case). The declared wording therefore has to travel INSIDE the
    thing being restored. Nothing is edited: the owner's captured map is
    replaced for the length of this scope through the same `_using` helper the
    owner itself uses, and the true original is what the replacement delegates
    to.
    """
    if not inputs:
        yield
        return
    original = X._ORIGINAL
    aware = collections.OrderedDict(original)
    aware["v6_prompt"] = _aware(E, carrier, inputs, original["v6_prompt"])
    with E.R._using(X, _ORIGINAL=aware):
        with E.R._using(E.F, v6_prompt=aware["v6_prompt"]):
            yield


@contextlib.contextmanager
def served_inputs(E, carrier, inputs):
    """The declared wording over whatever owner is installed RIGHT HERE.

    BOTH layers are needed and neither replaces the other (measured, the
    `prompts` case). `restored_wording` reaches the owner's own restore, which
    is what its internal cold reads see. But when the predecessor is ITSELF a
    successor, the owner enters that round's successor scope AFTER the
    restore, and that scope installs its own prompt - so the outermost
    derivation would lose the wording again. This wraps whatever is installed
    at that innermost point, so the round is rendered under its own wording on
    every path into it.
    """
    if not inputs:
        yield
        return
    with E.R._using(E.F, v6_prompt=_aware(E, carrier, inputs, E.F.v6_prompt)):
        yield


#: A REPORTED LIMITATION, measured (core_hist2132_e/f), not repaired here.
#: `accepted_shards` caches on (run, bound, phase, receipt_sha, labels). None
#: of those change when the SERVED WORDING changes, so one round's shards
#: derived under one wording are handed back under another. The owner's own
#: note warns about this class - "a cache keyed only on files would keep
#: answering after the derivation itself changed" - and the wording is now one
#: more input its key does not carry. Clearing it from here was tried and
#: REJECTED: it also drops entries whose own scope has since closed, and the
#: signature owner's closeout then cannot re-derive at all. Widening the
#: owner's key is the real repair and it is the owner's to make. Until then a
#: process must not read one round under two wordings.
CACHE_KEY_OMITS_THE_SERVED_WORDING = True


@contextlib.contextmanager
def first_round_scope(E, X, bound, first_run, first_findings, previous,
                      prior=(), signatures=None, carrier=None, inputs=None):
    """The accepted cold scope, with each round's own served input restored."""
    with restored_wording(E, X, carrier, inputs):
        with X.first_round_scope(bound, first_run, first_findings, previous,
                                 prior, signatures=signatures):
            with served_inputs(E, carrier, inputs):
                yield


@contextlib.contextmanager
def successor_scope(E, X, bound, findings, first_run, first_findings, previous,
                    prior=(), signatures=None, carrier=None, inputs=None):
    """The NEXT round's scope, over a predecessor that has its own wording.

    The same repair, at the seam the next round will actually use: the owner
    reads its predecessor cold while entering this scope, so without the
    restored wording the next round cannot be bound at all.
    """
    with restored_wording(E, X, carrier, inputs):
        with X.successor_scope(bound, findings, first_run, first_findings,
                               previous, prior, signatures=signatures):
            with served_inputs(E, carrier, inputs):
                yield


def first_round_key(E, X, bound, first_run, first_findings, previous,
                    prior=(), signatures=None, carrier=None, inputs=None):
    """The predecessor round's complete merged key, read under its own input.

    Identity stays where it already lives. A missing, misplaced or drifted
    declaration makes the re-derived prompts differ from the published
    receipt, and the EXISTING owner refuses that - the same refusal this
    repair was measured against. Nothing here re-checks what it already
    checks; the one check this module adds is the renderer byte pin, because
    an unpinned declaration is the only way a wrong wording could load without
    the owner ever seeing a mismatch it could name.
    """
    fb = X.first_bound(bound, first_run)
    with first_round_scope(E, X, bound, first_run, first_findings, previous,
                           prior, signatures=signatures, carrier=carrier,
                           inputs=inputs):
        key = E.F.v6_shards(fb)
    if key[3]:
        raise ValueError("the current merged key does not read cleanly: %s"
                         % key[3][:2])
    return key
