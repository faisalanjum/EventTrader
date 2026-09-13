# -*- coding: utf-8 -*-
"""The source-only CLOSEOUT connection (Codex SEQ 2063 item 4 / 2064 item 4).

The narrow versioned successor to `a4_source_settlement` (S2061), exactly as
S2061 is to `a4_source_decision` (D2041). It binds the EXISTING v5
`decision_correction_v5` lifecycle to the CURRENT source-only key and adds no
lifecycle of its own: F keeps the receipt, native proof, record, resume,
finalization, retry law, materializer, gate, counts, signer and lock.

Why this phase exists: the 31 settled events came back with 108 raw open
issues, and Codex SEQ 2064 traced them to two instruction defects rather than
to the source. `a4_source_taskv2` (V2) repairs those two spans. This connection
serves that repaired prefix for one more whole-event re-audit per affected
event, so the open issues are answered under the clarified instruction instead
of being cleared by hand.

What it binds, and nothing more:

  * the prefix is `C2023.correction_prefix` REUSED WHOLE with V2's repaired
    base swapped in for the duration of that one call. The swap is deliberately
    NOT held across the phase: `F.v5_prompt` re-derives the SETTLEMENT prompts
    to prove its own `v4_shard`, and a held swap would move those 31 frozen
    prompts and break the run that produced them;
  * the body is F's OWN `v5_prompt`. F already reads the accepted settlement
    into `v4_shard`, so no second prior-reply reader is added here;
  * the population is DERIVED from this phase's own reviewed findings, in
    frozen order, and must be a subset of the events the settlement run really
    accepted - so an unsettled event, and therefore either carried news
    result, can never enter it;
  * the four phases' review inputs stay SEPARATE and immutable: correction
    findings reconstruct the frozen v2 phase, decision findings the frozen v3
    phase, settlement findings the frozen v4 phase, and this phase's own
    findings reach only this body;
  * the merge is F's OWN `v5_shards`, entered UNDER S2061's settlement scope.
    F's v5 merge already carries its base forward untouched and stamps only
    the events it actually replaced; under S's scope that base is the settled
    merge with its TRUE mixed origins, so both original news results keep
    theirs. There is deliberately no merge, origin map or count owner here.

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
             "unit_2041_decision_connection", "unit_2061_settlement_connection",
             "unit_2063_source_closeout"):
    sys.path.insert(0, str(A7 / _rel))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
import a4_source_decision as D2041                                 # noqa: E402
import a4_source_settlement as S2061                               # noqa: E402
import a4_source_taskv2 as V2                                      # noqa: E402

F, K, SK, INV = R.F, R.K, R.SK, R.INV
SCHEMA = "a7-source-closeout/2065"
LAUNCHER_NAME = "a7-source-only-closeout"
DESCRIPTION = ("A7 source-only closeout: one independent key owner re-audits "
               "one whole settled event under the clarified task and returns "
               "a complete replacement")
FINDINGS_KEY = C2023.FINDINGS_KEY
#: The phase name the EXISTING lifecycle already uses for this stage.
PHASE = "decision_correction_v5"
#: F's own origin for this stage. Reused, never coined here.
ORIGIN = "a4_final_v5_correction"
#: The version of the served task text this phase exists to serve.
TASK_VERSION = V2.VERSION
#: F's OWN v5 body builder, captured before this module ever swaps that name
#: at F. Calling `F.v5_prompt` from inside the scope that replaces it would
#: call this module's own renderer and recurse forever.
_F_V5_PROMPT = F.v5_prompt


def closeout_prefix(bound, keys):
    """The REPAIRED source-only prefix with the correction task and `keys`.

    `C2023.correction_prefix` is reused whole - it already proves the base
    against this package's own `prefix_sha256`, already carries the
    settle-this-event-again task, and already declares exactly the keys the
    body sends. Only its BASE is swapped, for the duration of this one call,
    to V2's repaired prefix. Holding that swap wider would move the 31 frozen
    settlement prompts this phase's own body re-derives.
    """
    with R._using(C2023, _served_prefix=V2.served_prefix):
        return C2023.correction_prefix(bound, keys)


def _settlement_raw(bound, label, correction_findings=None,
                    decision_findings=None, settlement_findings=None):
    """The accepted settlement reply this closeout is allowed to correct."""
    with S2061._render_scope(correction_findings, decision_findings,
                             settlement_findings):
        _shards, raws, bad = F.accepted_shards(bound.decision_correction,
                                               bound, S2061.PHASE)
    if bad:
        raise ValueError("the settlement run does not read cleanly: %s"
                         % bad[:2])
    if label not in raws:
        raise ValueError("%s has no accepted settlement to correct" % label)
    return raws[label]


def closeout_finding_for(bound, label, closeout_findings,
                         correction_findings=None, decision_findings=None,
                         settlement_findings=None):
    """This event's own reviewed findings, from DATA - never a package ledger.

    A finding must bind to the evidence this body actually shows, and the v5
    body shows exactly one prior reply: this event's accepted settlement. A
    finding recorded against any other raw refuses rather than reaching the
    prompt as if it described what the model can see.
    """
    entries = C2023.entries_for(closeout_findings, label)
    if not entries:
        raise ValueError("no closeout finding is bound for %s" % label)
    shown = K._sha(_settlement_raw(bound, label, correction_findings,
                                   decision_findings, settlement_findings))
    for e in entries:
        if e.get("source_id") != label or e.get("raw_sha256") != shown:
            raise ValueError("a closeout finding does not bind to this "
                             "event's accepted settlement: %s" % e.get("row"))
    return collections.OrderedDict([("source_id", label),
                                    ("finding", list(entries))])


def closeout_labels(bound, correction_findings=None, decision_findings=None,
                    settlement_findings=None, closeout_findings=None):
    """The denominator, DERIVED: the events this phase's own findings name.

    Frozen order, no repeats, and every named event must be one the settlement
    run REALLY accepted - a closeout corrects a settlement, never an event
    nobody settled. There is deliberately no caller subset and no typed count.
    """
    if closeout_findings is None:
        raise ValueError("this phase needs its own reviewed findings; it has "
                         "no default population")
    ids = [s for s in closeout_findings
           if C2023.entries_for(closeout_findings, s)]
    order = [t["source_id"] for t in F.event_tasks(bound.evidence)]
    unknown = [s for s in ids if s not in order]
    if unknown:
        raise ValueError("the closeout findings name %d entries that are not "
                         "frozen events: %s" % (len(unknown), unknown))
    with S2061._render_scope(correction_findings, decision_findings,
                             settlement_findings):
        settled, _raws, bad = F.accepted_shards(bound.decision_correction,
                                                bound, S2061.PHASE)
    if bad:
        raise ValueError("the settlement run does not read cleanly: %s"
                         % bad[:2])
    outside = [s for s in ids if s not in settled]
    if outside:
        raise ValueError("the closeout findings name %d events the settlement "
                         "phase never accepted: %s" % (len(outside), outside))
    return [s for s in order if s in set(ids)]


def closeout_prompt(bound, label, correction_findings=None,
                    decision_findings=None, settlement_findings=None,
                    closeout_findings=None):
    """F's OWN v5 body, with this phase's prefix and findings at F's seams."""
    def prefix(package_dir, keys):
        if os.path.abspath(package_dir) != os.path.abspath(bound.package):
            raise ValueError("the closeout prefix was asked for a different "
                             "package: %s" % package_dir)
        return closeout_prefix(bound, keys)

    def finding_for(b, sid):
        return closeout_finding_for(b, sid, closeout_findings,
                                    correction_findings, decision_findings,
                                    settlement_findings)

    with S2061._render_scope(correction_findings, decision_findings,
                             settlement_findings), \
            R._using(F, v5_prefix=prefix, v5_finding_for=finding_for):
        return _F_V5_PROMPT(bound, label)


def render_closeout_launcher(bound, label, attempt=1, correction_findings=None,
                             decision_findings=None, settlement_findings=None,
                             closeout_findings=None):
    """The released launcher again, transformed. Transport bytes untouched."""
    task = F._task_by_label(bound.evidence, label)
    lines = F.render_launcher(task, bound, attempt).split("\n")
    F._swap(lines, "  name:", "  name: '%s'," % LAUNCHER_NAME, "meta name")
    F._swap(lines, "  description:", "  description: '%s'," % DESCRIPTION,
            "description")
    F._swap(lines, "const PROMPT = ",
            "const PROMPT = " + json.dumps(closeout_prompt(
                bound, label, correction_findings, decision_findings,
                settlement_findings, closeout_findings)), "PROMPT")
    return "\n".join(lines)


@contextlib.contextmanager
def _render_scope(correction_findings=None, decision_findings=None,
                  settlement_findings=None, closeout_findings=None):
    """THIS phase's rendering and population, at F's own v5 seams.

    Everything that READS a closeout run needs these, because the existing
    per-call proof and receipt validation re-derive the prompt and the
    population they are checking. S2061's render scope is entered first, with
    the three earlier phases' OWN immutable findings, because the same reads
    reach back into the settlement, decision and correction runs; this phase's
    findings never reach any of those renderers.
    """
    def prompt(bound, label):
        return closeout_prompt(bound, label, correction_findings,
                               decision_findings, settlement_findings,
                               closeout_findings)

    def launcher(bound, label, attempt=1):
        return render_closeout_launcher(bound, label, attempt,
                                        correction_findings,
                                        decision_findings,
                                        settlement_findings,
                                        closeout_findings)

    def labels(bound):
        return closeout_labels(bound, correction_findings, decision_findings,
                               settlement_findings, closeout_findings)

    with S2061._render_scope(correction_findings, decision_findings,
                             settlement_findings), \
            R._using(F, v5_prompt=prompt, render_v5_launcher=launcher,
                     v5_labels=labels):
        yield


@contextlib.contextmanager
def closeout_scope(correction_findings=None, decision_findings=None,
                   settlement_findings=None, closeout_findings=None):
    """The rendering scope, over S2061's settled merge.

    There is NO merge owner here on purpose. F's gate already dispatches to
    `v5_shards` whenever a decision_correction_v5 is bound, and F's own v5
    merge carries its base forward untouched and stamps only what it replaced.
    Entering S2061's settlement scope makes that base the settled merge with
    its TRUE mixed origins, so the carry-preserving behaviour this phase needs
    is the EXISTING one - no gate wrapper, no second count, merge or approval
    engine, and no edit to F.
    """
    with S2061.settlement_scope(correction_findings, decision_findings,
                                settlement_findings), \
            _render_scope(correction_findings, decision_findings,
                          settlement_findings, closeout_findings):
        yield


def closed_shards(bound, correction_findings=None, decision_findings=None,
                  settlement_findings=None, closeout_findings=None):
    """F's OWN v5 merge, read under this phase's scope. Not a second merge."""
    with closeout_scope(correction_findings, decision_findings,
                        settlement_findings, closeout_findings):
        return F.v5_shards(bound)


def bind(bound, closeout_run):
    """Carry the closeout run explicitly. There is no fallback."""
    if not closeout_run:
        raise ValueError("a closed binding needs its closeout run; falling "
                         "back to the settled key is refused")
    if bound.decision_correction is None:
        raise ValueError("a closeout corrects a settlement; this binding "
                         "carries no settlement run")
    return bound._replace(decision_correction_v5=closeout_run)


def prepare(out_dir, bound, correction_findings=None, decision_findings=None,
            settlement_findings=None, closeout_findings=None):
    """F's own preparer, with this phase's renderer installed at its seam."""
    with closeout_scope(correction_findings, decision_findings,
                        settlement_findings, closeout_findings):
        return F.prepare_v5(out_dir, bound)


def finalize(out_dir, bound, correction_findings=None, decision_findings=None,
             settlement_findings=None, closeout_findings=None):
    """F's own finalizer. The seam matters here too: run_evidence re-derives
    the prompt to prove the native state."""
    with closeout_scope(correction_findings, decision_findings,
                        settlement_findings, closeout_findings):
        return F.finalize(out_dir, bound)


def gate_problems(bound, correction_findings=None, decision_findings=None,
                  settlement_findings=None, closeout_findings=None):
    """The existing signing gate, through the closed binding only."""
    if bound.decision_correction_v5 is None:
        raise ValueError("this binding carries no closeout run: refusing "
                         "rather than signing the settled key")
    with closeout_scope(correction_findings, decision_findings,
                        settlement_findings, closeout_findings):
        return list(F.signing_gate(bound.events, bound).get("stops") or [])


def provenance(bound, label, correction_findings=None, decision_findings=None,
               settlement_findings=None, closeout_findings=None):
    """The identities this closeout is bound to. Nothing is approved here."""
    with closeout_scope(correction_findings, decision_findings,
                        settlement_findings, closeout_findings):
        prompt = closeout_prompt(bound, label, correction_findings,
                                 decision_findings, settlement_findings,
                                 closeout_findings)
        finding = closeout_finding_for(bound, label, closeout_findings,
                                       correction_findings, decision_findings,
                                       settlement_findings)
        return collections.OrderedDict([
            ("schema", SCHEMA), ("source_id", label), ("phase", PHASE),
            ("task_version", TASK_VERSION),
            ("served_source_only_prefix_sha256",
             K._sha(C2023._served_prefix(bound))),
            ("repaired_prefix_sha256", K._sha(V2.served_prefix(bound))),
            ("closeout_prompt_sha256", K._sha(prompt)),
            ("settlement_raw_sha256",
             K._sha(_settlement_raw(bound, label, correction_findings,
                                    decision_findings, settlement_findings))),
            ("findings", len(finding["finding"])),
            ("owner_sha256", INV.sha_file(os.path.abspath(__file__))),
            ("task_owner_sha256", INV.sha_file(os.path.abspath(V2.__file__))),
            ("package_manifest_sha256",
             INV.sha_file(os.path.join(bound.package, SK.MANIFEST_NAME))),
            ("population_approved", False), ("ceiling_approved", False),
            ("model_calls", 0)])
