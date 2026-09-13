# -*- coding: utf-8 -*-
"""The source-only FINAL DECISION connection (Codex SEQ 2039 / 2041).

One narrow versioned successor binding, exactly as `a4_source_correction`
(C2023) is for the correction phase. Every rule, task text, reply schema,
launcher, receipt, native proof, finalization, retry law, materializer, gate,
candidate, signer, lock and consumer stays where it is: this module only BINDS
the existing final-decision lifecycle to the CURRENT source-only key.

What it fixes, and nothing more:
  * the decision base is the prefix THIS package served, proved against the
    package manifest's own pin - never the historical A4 prefix and never the
    answer-informed SEQ 1383/1387 artifacts, which this package does not ship;
  * the data-boundary declaration names the keys the body ACTUALLY sends;
  * the population is DERIVED from the events whose current merged shard still
    carries an open issue, in frozen order - never typed, never a caller subset;
  * the two phases' review inputs stay SEPARATE: the immutable correction
    findings reconstruct the frozen correction phase and nothing else, and the
    new final-decision leads reach the decision body and nothing else. Neither
    is ever inferred from the other (Codex SEQ 2042/2043);
  * the merge carries decisions over the corrected/original shards with their
    TRUE origins, so a carried original is never labelled a decision.

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
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402

F, K, SK, INV = R.F, R.K, R.SK, R.INV
SCHEMA = "a7-source-decision/2041"
LAUNCHER_NAME = "a7-source-only-final-decision"
DESCRIPTION = ("A7 source-only final decision: one independent key owner "
               "settles every located row of one event once, from its source")
FINDINGS_KEY = C2023.FINDINGS_KEY
#: The origin this phase stamps. The carried origins are the correction
#: owner's own; only a genuinely decided event gets this one.
ORIGIN = "a4_final_v3_decision"


def decision_prefix(bound, keys):
    """The served source-only prefix, transformed: the EXISTING final-decision
    task above the boundary, and the declaration below it naming `keys`.

    `C2023._served_prefix` proves the base against the package manifest's own
    `prefix_sha256`, so a historical prefix cannot be substituted here.
    """
    base = C2023._served_prefix(bound)
    if base.count(C2023._BOUNDARY) != 1:
        raise ValueError("the served prefix no longer carries one boundary")
    head, tail = base.split(C2023._BOUNDARY, 1)
    start, end = C2023._declaration_span(tail)
    declared = ", ".join("`%s`" % k for k in keys)
    return (head
            + "[A4 FINAL DECISION TASK]\n%s\n\n" % F._decision_task_section()
            + C2023._BOUNDARY + tail[:start] + declared + tail[end:])


def decision_labels(bound, correction_findings=None):
    """The denominator, DERIVED: every merged event whose current shard still
    carries an open issue, in frozen order.

    The final decision permits no open issue (`F.open_issue_text`), so the
    events that still carry one are exactly the final answers still missing.
    A terminal refusal keeps its own open issues and therefore stays IN this
    population; it is held by the phase's own preparation and by the gate,
    never dropped here (Codex SEQ 2041). There is deliberately no caller subset.

    This owner reports the inventory; it does not judge readiness. The merge's
    own problems ride on with `decided_shards` to the gate, and
    `F.prepare_decision` refuses on them, so an unready key still cannot
    schedule anything - while its real population stays reportable rather than
    raising (Codex SEQ 2043).
    """
    shards, _raws, _origins, _bad = C2023.corrected_shards(
        bound, correction_findings)
    left, _stops = F.open_issue_text(shards)
    return [s for s in shards if s in left]


def decision_body(bound, label, correction_findings=None,
                  decision_findings=None):
    """The existing payload, the event's own prior replies, and its own
    hash-bound source-review leads - all DATA, all below the boundary.

    TWO DISTINCT INPUTS. `correction_findings` are the immutable ones the
    correction phase was rendered with: they are used ONLY to reconstruct that
    frozen phase while its prior reply is read. `decision_findings` are the
    new final-decision leads and are the ONLY thing that reaches this body.
    Neither is defaulted from the other: a caller that supplies no decision
    leads sends none, and never the correction phase's (Codex SEQ 2042).
    """
    task = F._task_by_label(bound.evidence, label)
    # THE PRIOR REPLIES ARE READ THROUGH THE OWNERS THAT RENDERED THEM: the
    # correction run re-derives its own prompts to prove its states, so the
    # correction renderer must be installed - with ITS OWN findings - for that
    # read wherever this body is built from.
    with C2023.correction_scope(correction_findings):
        prior = F.prior_replies(bound, label)
    if not prior:
        raise ValueError("%s has no prior source-key reply to carry" % label)
    # A LEAD MUST BIND TO EVIDENCE THIS BODY ACTUALLY SHOWS. A new review lead
    # may name either prior reply of this event - the original or its accepted
    # correction - and anything else refuses.
    shown = {p["sha256"] for p in prior}
    entries = C2023.entries_for(decision_findings, label) or []
    for e in entries:
        if e.get("source_id") != label or e.get("raw_sha256") not in shown:
            raise ValueError("a finding does not bind to a prior reply of this "
                             "event: %s" % e.get("row"))
    body = collections.OrderedDict(F.payload(bound, task))
    body["prior_replies"] = prior
    body[FINDINGS_KEY] = list(entries)
    return body


def decision_prompt(bound, label, correction_findings=None,
                    decision_findings=None):
    body = decision_body(bound, label, correction_findings, decision_findings)
    return decision_prefix(bound, list(body)) + json.dumps(body, indent=1)


def render_decision_launcher(bound, label, attempt=1, correction_findings=None,
                             decision_findings=None):
    """The released launcher again, transformed. Transport bytes untouched."""
    task = F._task_by_label(bound.evidence, label)
    lines = F.render_launcher(task, bound, attempt).split("\n")
    F._swap(lines, "  name:", "  name: '%s'," % LAUNCHER_NAME, "meta name")
    F._swap(lines, "  description:", "  description: '%s'," % DESCRIPTION,
            "description")
    F._swap(lines, "const PROMPT = ",
            "const PROMPT = " + json.dumps(decision_prompt(
                bound, label, correction_findings, decision_findings)), "PROMPT")
    return "\n".join(lines)


def decided_shards(bound, correction_findings=None, decision_findings=None):
    """THE ONE merge/origin owner for the decided key.

    -> (shards, raws, origins, problems). The corrected/original merge is the
    base and keeps ITS origins; an accepted decision replaces its event whole
    and is the only thing stamped `a4_final_v3_decision`. Frozen order.
    Missing decisions are the existing reader's own refusal, not a rule here.
    """
    shards, raws, origins, bad = C2023.corrected_shards(
        bound, correction_findings)
    if bound.decision is None:
        return shards, raws, origins, bad
    # SAME REASON, one phase later: reading the decision run re-derives this
    # phase's own prompts, so its renderer - with ITS OWN leads - is installed
    # for that read.
    with _render_scope(correction_findings, decision_findings):
        repl, rraws, rbad = F.accepted_shards(bound.decision, bound, "decision")
    bad += rbad
    for label, shard in repl.items():
        shards[label], raws[label] = shard, rraws[label]
        origins[label] = ORIGIN
    order = [t["source_id"] for t in F.event_tasks(bound.evidence)]
    return (collections.OrderedDict((s, shards[s]) for s in order),
            collections.OrderedDict((s, raws[s]) for s in order),
            collections.OrderedDict((s, origins[s]) for s in order), bad)


@contextlib.contextmanager
def _render_scope(correction_findings=None, decision_findings=None):
    """THIS phase's rendering and population, at F's own three seams.

    Everything that READS a decision run needs these, because the existing
    per-call proof and receipt validation re-derive the prompt and the
    population they are checking. The correction scope is entered first,
    with ITS OWN immutable findings, because the same reads reach back into
    the v2 run; the new decision leads never reach that renderer.
    """
    def prompt(bound, label):
        return decision_prompt(bound, label, correction_findings,
                               decision_findings)

    def launcher(bound, label, attempt=1):
        return render_decision_launcher(bound, label, attempt,
                                        correction_findings, decision_findings)

    def labels(bound):
        return decision_labels(bound, correction_findings)

    with C2023.correction_scope(correction_findings), \
            R._using(F, decision_prompt=prompt,
                     render_decision_launcher=launcher,
                     decision_labels=labels):
        yield


@contextlib.contextmanager
def decision_scope(correction_findings=None, decision_findings=None):
    """The rendering scope, plus the merge and its origins at F's own seams.

    F keeps every responsibility - the receipt, the invocations, run_evidence,
    finalize, the retry law, materialize, the gate's stops and counts, the
    signer and the lock. The gate wrapper replaces exactly one value: the
    origin map, which the decision branch would otherwise stamp onto carried
    originals, and it takes that map from the SAME merge owner above rather
    than deciding anything itself (Codex SEQ 2039 item 4a).
    """
    real_gate = F.signing_gate

    def decided(bound):
        shards, raws, _origins, bad = decided_shards(
            bound, correction_findings, decision_findings)
        return shards, raws, bad

    def gate(event_dir, bound):
        result = real_gate(event_dir, bound)
        if bound.decision is None or not result.get("origins"):
            return result
        origins = decided_shards(bound, correction_findings,
                                 decision_findings)[2]
        if set(origins) != set(result["origins"]):
            raise ValueError("the merge and the gate disagree about which "
                             "events the key holds")
        result["origins"] = collections.OrderedDict(
            (s, origins[s]) for s in result["origins"])
        return result

    with _render_scope(correction_findings, decision_findings), \
            R._using(F, decided_shards=decided, signing_gate=gate):
        yield


def bind(bound, decision_run):
    """Carry the decision run explicitly. There is no fallback."""
    if not decision_run:
        raise ValueError("a decided binding needs its decision run; falling "
                         "back to the corrected key is refused")
    return bound._replace(decision=decision_run)


def prepare(out_dir, bound, correction_findings=None,
                       decision_findings=None):
    """F's own preparer, with this phase's renderer installed at its seam."""
    with decision_scope(correction_findings, decision_findings):
        return F.prepare_decision(out_dir, bound)


def finalize(out_dir, bound, correction_findings=None,
                        decision_findings=None):
    """F's own finalizer. The seam matters here too: run_evidence re-derives
    the prompt to prove the native state."""
    with decision_scope(correction_findings, decision_findings):
        return F.finalize(out_dir, bound)


def gate_problems(bound, correction_findings=None, decision_findings=None):
    """The existing signing gate, through the decided binding only."""
    if bound.decision is None:
        raise ValueError("this binding carries no decision run: refusing "
                         "rather than signing the undecided key")
    with decision_scope(correction_findings, decision_findings):
        return list(F.signing_gate(bound.events, bound).get("stops") or [])


def provenance(bound, label, correction_findings=None,
               decision_findings=None):
    """The identities this decision is bound to. Nothing is approved here."""
    with decision_scope(correction_findings, decision_findings):
        body = decision_body(bound, label, correction_findings,
                             decision_findings)
        prefix = decision_prefix(bound, list(body))
        return collections.OrderedDict([
            ("schema", SCHEMA), ("source_id", label),
            ("served_source_only_prefix_sha256",
             K._sha(C2023._served_prefix(bound))),
            ("decision_prefix_sha256", K._sha(prefix)),
            ("decision_prompt_sha256",
             K._sha(prefix + json.dumps(body, indent=1))),
            ("declared_keys", C2023.declared_keys(prefix)),
            ("prior_replies", [collections.OrderedDict(
                [("origin", p["origin"]), ("sha256", p["sha256"])])
                for p in body["prior_replies"]]),
            ("findings", len(body[FINDINGS_KEY])),
            ("owner_sha256", INV.sha_file(os.path.abspath(__file__))),
            ("package_manifest_sha256",
             INV.sha_file(os.path.join(bound.package, SK.MANIFEST_NAME))),
            ("population_approved", False), ("ceiling_approved", False),
            ("model_calls", 0)])
