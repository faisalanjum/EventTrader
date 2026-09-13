# -*- coding: utf-8 -*-
"""The source-only FINAL SETTLEMENT connection (Codex SEQ 2060).

The narrow versioned successor to `a4_source_decision` (D2041), exactly as
D2041 is to `a4_source_correction` (C2023). It binds the EXISTING v4
`decision_correction` lifecycle to the CURRENT source-only key and adds no
lifecycle of its own: F keeps the receipt, native proof, record, resume,
finalization, retry law, materializer, gate, counts, signer and lock.

What it binds, and nothing more:

  * the prefix is the one THIS package served, proved against the package
    manifest's own pin - never F's historical answer-informed base. The task
    text is `C2023._task_section()` REUSED VERBATIM: that already-reviewed
    section says an event settled once is being settled again, that the
    earlier reply, its open issues and any review findings shown with it are
    untrusted leads, and that the reply keeps the same schema and row order.
    That is precisely this phase, so no new task text is written here, the
    old `_v4_clarification` is not carried (its narrower tag restatement is
    already owned by the served TAG RULES), and nothing is said about
    ambiguity - so a guessed empty `open_issues` is never required;
  * the body is F's OWN `v4_prompt` body. F already carries the accepted
    decision into `v3_shard`, so no second prior-reply reader is added here;
  * the population is DERIVED from this phase's own reviewed findings, in
    frozen order, and must be a subset of the events the decision run really
    accepted - so an undecided event, and therefore either carried news
    result, can never enter it;
  * the three phases' review inputs stay SEPARATE and immutable: correction
    findings reconstruct the frozen v2 phase, decision findings the frozen v3
    phase, and this phase's own findings reach only this body;
  * the merge carries settlements over the DECIDED merge with its TRUE
    origins. F's own `v4_shards` re-stamps every carried event
    `a4_final_v3_decision`, which would relabel the two carried news results
    and any carried correction; this owner keeps what D2041 derived and
    stamps only the events it actually replaced.

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
sys.path.insert(0, str(A7 / "unit_2009/owner"))
sys.path.insert(0, str(A7 / "unit_2023_source_correction"))
sys.path.insert(0, str(A7 / "unit_2041_decision_connection"))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
import a4_source_decision as D2041                                 # noqa: E402

F, K, SK, INV = R.F, R.K, R.SK, R.INV
SCHEMA = "a7-source-settlement/2061"
LAUNCHER_NAME = "a7-source-only-final-settlement"
DESCRIPTION = ("A7 source-only final settlement: one independent key owner "
               "re-audits one whole decided event and returns a complete "
               "replacement")
FINDINGS_KEY = C2023.FINDINGS_KEY
#: The phase name the EXISTING lifecycle already uses for this stage.
PHASE = "decision_correction"
#: F's own origin for this stage. Reused, never coined here.
ORIGIN = "a4_final_v4_correction"
#: F's OWN v4 body builder, captured before this module ever swaps that
#: name at F. Calling `F.v4_prompt` from inside the scope that replaces
#: it would call this module's own renderer and recurse forever.
_F_V4_PROMPT = F.v4_prompt


def settlement_prefix(bound, keys):
    """The served source-only prefix with the correction task and `keys`.

    `C2023.correction_prefix` is REUSED WHOLE rather than re-composed: it
    already proves the base against this package's own `prefix_sha256`,
    already carries the settle-this-event-again task, and already declares
    exactly the keys the body sends. A second prefix builder here would be a
    second owner for one behaviour.
    """
    return C2023.correction_prefix(bound, keys)


def _decision_raw(bound, label, correction_findings=None,
                  decision_findings=None):
    """The accepted decision reply this settlement is allowed to correct."""
    with D2041._render_scope(correction_findings, decision_findings):
        _shards, raws, bad = F.accepted_shards(bound.decision, bound,
                                               "decision")
    if bad:
        raise ValueError("the decision run does not read cleanly: %s" % bad[:2])
    if label not in raws:
        raise ValueError("%s has no accepted decision to correct" % label)
    return raws[label]


def settlement_finding_for(bound, label, settlement_findings,
                           correction_findings=None, decision_findings=None):
    """This event's own reviewed findings, from DATA - never a package ledger.

    A finding must bind to the evidence this body actually shows, and the v4
    body shows exactly one prior reply: this event's accepted decision. A
    finding recorded against any other raw refuses rather than reaching the
    prompt as if it described what the model can see.
    """
    entries = C2023.entries_for(settlement_findings, label)
    if not entries:
        raise ValueError("no settlement finding is bound for %s" % label)
    shown = K._sha(_decision_raw(bound, label, correction_findings,
                                 decision_findings))
    for e in entries:
        if e.get("source_id") != label or e.get("raw_sha256") != shown:
            raise ValueError("a settlement finding does not bind to this "
                             "event's accepted decision: %s" % e.get("row"))
    return collections.OrderedDict([("source_id", label),
                                    ("finding", list(entries))])


def settlement_labels(bound, correction_findings=None, decision_findings=None,
                      settlement_findings=None):
    """The denominator, DERIVED: the events this phase's own findings name.

    Frozen order, no repeats, and every named event must be one the decision
    run REALLY accepted - a settlement corrects a decision, never an event
    nobody decided. There is deliberately no caller subset and no typed count.
    """
    if settlement_findings is None:
        raise ValueError("this phase needs its own reviewed findings; it has "
                         "no default population")
    ids = [s for s in settlement_findings
           if C2023.entries_for(settlement_findings, s)]
    order = [t["source_id"] for t in F.event_tasks(bound.evidence)]
    unknown = [s for s in ids if s not in order]
    if unknown:
        raise ValueError("the settlement findings name %d entries that are "
                         "not frozen events: %s" % (len(unknown), unknown))
    with D2041._render_scope(correction_findings, decision_findings):
        decided, _raws, bad = F.accepted_shards(bound.decision, bound,
                                                "decision")
    if bad:
        raise ValueError("the decision run does not read cleanly: %s" % bad[:2])
    outside = [s for s in ids if s not in decided]
    if outside:
        raise ValueError("the settlement findings name %d events the decision "
                         "phase never accepted: %s" % (len(outside), outside))
    return [s for s in order if s in set(ids)]


def settlement_prompt(bound, label, correction_findings=None,
                      decision_findings=None, settlement_findings=None):
    """F's OWN v4 body, with this phase's prefix and findings at F's seams."""
    def prefix(package_dir, keys):
        if os.path.abspath(package_dir) != os.path.abspath(bound.package):
            raise ValueError("the settlement prefix was asked for a different "
                             "package: %s" % package_dir)
        return settlement_prefix(bound, keys)

    def finding_for(b, sid):
        return settlement_finding_for(b, sid, settlement_findings,
                                      correction_findings, decision_findings)

    with D2041._render_scope(correction_findings, decision_findings), \
            R._using(F, v4_prefix=prefix, v4_finding_for=finding_for):
        return _F_V4_PROMPT(bound, label)


def render_settlement_launcher(bound, label, attempt=1,
                               correction_findings=None,
                               decision_findings=None,
                               settlement_findings=None):
    """The released launcher again, transformed. Transport bytes untouched."""
    task = F._task_by_label(bound.evidence, label)
    lines = F.render_launcher(task, bound, attempt).split("\n")
    F._swap(lines, "  name:", "  name: '%s'," % LAUNCHER_NAME, "meta name")
    F._swap(lines, "  description:", "  description: '%s'," % DESCRIPTION,
            "description")
    F._swap(lines, "const PROMPT = ",
            "const PROMPT = " + json.dumps(settlement_prompt(
                bound, label, correction_findings, decision_findings,
                settlement_findings)), "PROMPT")
    return "\n".join(lines)


def settled_shards(bound, correction_findings=None, decision_findings=None,
                   settlement_findings=None):
    """THE ONE merge/origin owner for the settled key.

    -> (shards, raws, origins, problems). The DECIDED merge is the base and
    keeps ITS origins, so a carried news result stays what it is; an accepted
    settlement replaces its event whole and is the only thing stamped ORIGIN.
    Frozen order. Missing settlements are the existing reader's own refusal.
    """
    shards, raws, origins, bad = D2041.decided_shards(
        bound, correction_findings, decision_findings)
    if bound.decision_correction is None:
        return shards, raws, origins, bad
    shards = collections.OrderedDict(shards)
    raws = collections.OrderedDict(raws)
    origins = collections.OrderedDict(origins)
    with _render_scope(correction_findings, decision_findings,
                       settlement_findings):
        repl, rraws, rbad = F.accepted_shards(bound.decision_correction,
                                              bound, PHASE)
    bad += rbad
    for label, shard in repl.items():
        shards[label], raws[label] = shard, rraws[label]
        origins[label] = ORIGIN
    missing = sorted(set(settlement_labels(bound, correction_findings,
                                           decision_findings,
                                           settlement_findings)) - set(repl))
    if missing:
        bad.append("%d named events have no accepted settlement: %s"
                   % (len(missing), missing[:3]))
    order = [t["source_id"] for t in F.event_tasks(bound.evidence)]
    return (collections.OrderedDict((s, shards[s]) for s in order),
            collections.OrderedDict((s, raws[s]) for s in order),
            collections.OrderedDict((s, origins[s]) for s in order), bad)


@contextlib.contextmanager
def _render_scope(correction_findings=None, decision_findings=None,
                  settlement_findings=None):
    """THIS phase's rendering and population, at F's own v4 seams.

    Everything that READS a settlement run needs these, because the existing
    per-call proof and receipt validation re-derive the prompt and the
    population they are checking. D2041's render scope is entered first, with
    the two earlier phases' OWN immutable findings, because the same reads
    reach back into the decision and correction runs; this phase's findings
    never reach either of those renderers.

    D2041's *decision* scope is deliberately NOT entered: its gate wrapper
    replaces the origin map with the decided one, which would relabel every
    event this phase settled.
    """
    def prompt(bound, label):
        return settlement_prompt(bound, label, correction_findings,
                                 decision_findings, settlement_findings)

    def launcher(bound, label, attempt=1):
        return render_settlement_launcher(bound, label, attempt,
                                          correction_findings,
                                          decision_findings,
                                          settlement_findings)

    def labels(bound):
        return settlement_labels(bound, correction_findings,
                                 decision_findings, settlement_findings)

    with D2041._render_scope(correction_findings, decision_findings), \
            R._using(F, v4_prompt=prompt, render_v4_launcher=launcher,
                     v4_labels=labels):
        yield


@contextlib.contextmanager
def settlement_scope(correction_findings=None, decision_findings=None,
                     settlement_findings=None):
    """The rendering scope, plus the merge and its origins at F's own seam.

    F's gate already dispatches to `v4_shards` whenever a decision_correction
    is bound, so replacing that ONE owner is the whole connection: no gate
    wrapper, no second count, merge or approval engine, and no edit to F.
    """
    def shards(bound):
        return settled_shards(bound, correction_findings, decision_findings,
                              settlement_findings)

    with _render_scope(correction_findings, decision_findings,
                       settlement_findings), \
            R._using(F, v4_shards=shards):
        yield


def bind(bound, settlement_run):
    """Carry the settlement run explicitly. There is no fallback."""
    if not settlement_run:
        raise ValueError("a settled binding needs its settlement run; falling "
                         "back to the decided key is refused")
    if bound.decision is None:
        raise ValueError("a settlement corrects a decision; this binding "
                         "carries no decision run")
    return bound._replace(decision_correction=settlement_run)


def prepare(out_dir, bound, correction_findings=None, decision_findings=None,
            settlement_findings=None):
    """F's own preparer, with this phase's renderer installed at its seam."""
    with settlement_scope(correction_findings, decision_findings,
                          settlement_findings):
        return F.prepare_v4(out_dir, bound)


def finalize(out_dir, bound, correction_findings=None, decision_findings=None,
             settlement_findings=None):
    """F's own finalizer. The seam matters here too: run_evidence re-derives
    the prompt to prove the native state."""
    with settlement_scope(correction_findings, decision_findings,
                          settlement_findings):
        return F.finalize(out_dir, bound)


def gate_problems(bound, correction_findings=None, decision_findings=None,
                  settlement_findings=None):
    """The existing signing gate, through the settled binding only."""
    if bound.decision_correction is None:
        raise ValueError("this binding carries no settlement run: refusing "
                         "rather than signing the unsettled key")
    with settlement_scope(correction_findings, decision_findings,
                          settlement_findings):
        return list(F.signing_gate(bound.events, bound).get("stops") or [])


def provenance(bound, label, correction_findings=None, decision_findings=None,
               settlement_findings=None):
    """The identities this settlement is bound to. Nothing is approved here."""
    with settlement_scope(correction_findings, decision_findings,
                          settlement_findings):
        prompt = settlement_prompt(bound, label, correction_findings,
                                   decision_findings, settlement_findings)
        finding = settlement_finding_for(bound, label, settlement_findings,
                                         correction_findings,
                                         decision_findings)
        return collections.OrderedDict([
            ("schema", SCHEMA), ("source_id", label), ("phase", PHASE),
            ("served_source_only_prefix_sha256",
             K._sha(C2023._served_prefix(bound))),
            ("settlement_prompt_sha256", K._sha(prompt)),
            ("decision_raw_sha256",
             K._sha(_decision_raw(bound, label, correction_findings,
                                  decision_findings))),
            ("findings", len(finding["finding"])),
            ("owner_sha256", INV.sha_file(os.path.abspath(__file__))),
            ("package_manifest_sha256",
             INV.sha_file(os.path.join(bound.package, SK.MANIFEST_NAME))),
            ("population_approved", False), ("ceiling_approved", False),
            ("model_calls", 0)])
