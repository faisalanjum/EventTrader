# -*- coding: utf-8 -*-
"""The source-only correction connection (Codex SEQ 2023).

One narrow versioned successor binding, nothing else. Every rule, prompt,
launcher, receipt, finalization, shard, gate and ledger owner stays exactly
where it is: this module only BINDS the existing correction lifecycle to the
CURRENT source-only key and refuses when that binding would be silent.

What it fixes, and nothing more:
  * the correction base is the prefix THIS package served, proved against the
    package manifest's own pin - never the historical A4 prefix, and never an
    answer-informed owner-rulings file;
  * the data-boundary key declaration names the keys the task ACTUALLY sends,
    derived from the body itself rather than typed;
  * source-review findings ride AFTER the evidence boundary, bound to the
    exact event and the exact original raw reply.

It calls no model, publishes nothing, signs nothing and approves no
population or ceiling.
"""
import collections
import collections.abc
import contextlib
import json
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / "unit_2009/owner"))
import a4_review_composite as R                                    # noqa: E402

F, K, SK, CL, INV = R.F, R.K, R.SK, R.CL, R.INV
SCHEMA = "a7-source-correction/2023"
#: A findings document is NEVER read by default: the withdrawn 2022 proposals
#: alone are not the current finding set, so a caller must name the document it
#: means. A named document that is missing REFUSES rather than silently
#: yielding no findings (Codex SEQ 2025 item 3).
ERRATA_2022 = str(A7 / "unit_2022_source_errata" / "SOURCE_ERRATA_2022.json")
FINDINGS_KEY = "source_review_findings"
LAUNCHER_NAME = "a7-source-only-correction"
DESCRIPTION = ("A7 source-only correction: one independent key owner settles "
               "every frozen target of one event again, from its source")
#: The served prefix's own declaration sentence. The span between these two
#: literals is the key list; both must appear exactly once or the base refuses.
_LEAD = "Everything below is ONE JSON object with the keys "
_TRAIL = ", in that order."
_BOUNDARY = "[BOUNDARY]\n"


def _task_section():
    """The new instruction. No rulings, no examples, no desired answers."""
    return "\n".join([
        "This event was already settled once. That earlier reply, its open",
        "issues, and any review findings shown with it are UNTRUSTED LEADS:",
        "read them, agree or disagree, and never borrow their evidence,",
        "their names or their conclusions.",
        "",
        "Settle EVERY located row of this event again, each on its own",
        "source evidence and on the rules above, exactly as the first",
        "settlement was asked to. Reply in the SAME schema, with the same",
        "required keys and the same row order.",
    ])
    # NOTHING IS SAID HERE ABOUT AMBIGUITY. The served [A4 FINAL TASK] already
    # owns it: genuine ambiguity is an ANSWER, and only what BLOCKS a safe
    # final answer goes in the open-issue branch. A second, broader sentence
    # here would turn permitted uncertainty into mandatory failure, so this
    # section has exactly one owner and it is not this file (Codex SEQ 2026
    # finding 1).


def _served_prefix(bound):
    """The prefix this package actually served, proved against its own pin."""
    text = SK.prompt_prefix()
    manifest = K._load(os.path.join(bound.package, SK.MANIFEST_NAME))
    want = manifest["prefix_sha256"]
    got = K._sha(text)
    if got != want:
        raise ValueError(
            "the correction base is not the prefix this package served: "
            "%s is not the manifest's %s" % (got, want))
    return text


def _declaration_span(text):
    if text.count(_LEAD) != 1:
        raise ValueError("the base carries %d data-boundary key declarations, "
                         "not one" % text.count(_LEAD))
    start = text.index(_LEAD) + len(_LEAD)
    return start, text.index(_TRAIL, start)


def declared_keys(text):
    """The keys the prompt's own data boundary declares, in order."""
    start, end = _declaration_span(text)
    return [p.strip(" `") for p in text[start:end].replace(" and", ",").split(",")
            if p.strip(" `\n")]


def correction_prefix(bound, keys):
    """The served source-only prefix, transformed: the new task above the
    boundary, and the declaration below it naming exactly `keys`."""
    base = _served_prefix(bound)
    if base.count(_BOUNDARY) != 1:
        raise ValueError("the served prefix no longer carries one boundary")
    head, tail = base.split(_BOUNDARY, 1)
    start, end = _declaration_span(tail)
    declared = ", ".join("`%s`" % k for k in keys)
    return (head
            + "[A7 SOURCE CORRECTION TASK]\n%s\n\n" % _task_section()
            + _BOUNDARY + tail[:start] + declared + tail[end:])


def correction_labels(bound):
    """The affected events, DERIVED by the existing owner. Not a population
    approval and not a caller-supplied subset."""
    return F.correction_labels(bound)


def load_findings(path, label, bound):
    """One NAMED findings document, filtered to this event and hash-bound.

    A missing named document refuses: losing required findings silently is the
    failure this exists to prevent. A finding whose recorded raw identity is
    not this event's live raw reply refuses for the same reason.
    """
    if not os.path.isfile(path):
        raise ValueError("the named findings document is missing: %s" % path)
    _shards, raws, bad = F.accepted_shards(bound.events, bound)
    if bad:
        raise ValueError("the accepted event phase is not clean: %s" % bad[:2])
    live = K._sha(raws[label])
    out = []
    for d in K._load(path)["decisions"]:
        if d["source_id"] != label:
            continue
        if d["raw_sha256"] != live:
            raise ValueError("finding %s is bound to raw %s, not this event's "
                             "%s" % (d["row"], d["raw_sha256"], live))
        out.append(collections.OrderedDict(
            [("source_id", d["source_id"]), ("raw_sha256", d["raw_sha256"])]
            + [(k, d[k]) for k in ("row", "fact_index", "field", "decision",
                                   "source_evidence", "owning_clause")]))
    return out


def correction_body(bound, label, findings=None):
    """The existing payload composition, plus the original reply and the
    findings - all of it DATA, all of it below the boundary."""
    task = F._task_by_label(bound.evidence, label)
    shards, raws, bad = F.accepted_shards(bound.events, bound)
    if bad:
        raise ValueError("the accepted event phase is not clean: %s" % bad[:2])
    live = K._sha(raws[label])
    entries = [] if findings is None else list(findings)
    for e in entries:
        if e.get("source_id") != label or e.get("raw_sha256") != live:
            raise ValueError("a finding does not bind to this event's exact "
                             "raw reply: %s" % e.get("row"))
    body = collections.OrderedDict(F.payload(bound, task))
    body["original_final_shard"] = collections.OrderedDict([
        ("origin", "a7_source_only_key_v1"), ("sha256", live),
        ("raw", raws[label])])
    body["original_open_issues"] = shards[label]["open_issues"]
    body[FINDINGS_KEY] = entries
    return body


def correction_prompt(bound, label, findings=None):
    body = correction_body(bound, label, findings)
    return correction_prefix(bound, list(body)) + json.dumps(body, indent=1)


def render_correction_launcher(bound, label, attempt=1, findings=None):
    """The released launcher again, transformed. Transport bytes untouched."""
    task = F._task_by_label(bound.evidence, label)
    lines = F.render_launcher(task, bound, attempt).split("\n")
    F._swap(lines, "  name:", "  name: '%s'," % LAUNCHER_NAME, "meta name")
    F._swap(lines, "  description:", "  description: '%s'," % DESCRIPTION,
            "description")
    F._swap(lines, "const PROMPT = ",
            "const PROMPT = " + json.dumps(
                correction_prompt(bound, label, findings)), "PROMPT")
    return "\n".join(lines)


def entries_for(findings_by_event, label):
    """This event's findings out of a per-event mapping, or None.

    A multi-event phase renders one script per event, so ONE flat list cannot
    serve it: every event after the first would carry another event's entries,
    which correction_body then refuses. The binding is therefore explicit and
    keyed by event id (Codex SEQ 2026 finding 2).
    """
    if findings_by_event is None:
        return None
    if not isinstance(findings_by_event, collections.abc.Mapping):
        raise ValueError(
            "findings must be a mapping of event id -> that event's findings; "
            "one flat list cannot serve a multi-event correction phase")
    return findings_by_event.get(label)


@contextlib.contextmanager
def correction_scope(findings=None):
    """Bind THIS source-only renderer at F's own preparation seams.

    F keeps every responsibility - correction_scripts, the receipt, the
    invocations, run_evidence, finalize, the retry law and the ledger. Only the
    two rendering functions those seams call are this phase's. The binding is
    SCOPED on purpose: requirement 1 asks that the ORIGINAL prompt owners still
    reconstruct cold once it exits, which a permanent replacement would break.
    """
    def prompt(bound, label):
        return correction_prompt(bound, label, entries_for(findings, label))

    def launcher(bound, label, attempt=1):
        return render_correction_launcher(bound, label, attempt,
                                          entries_for(findings, label))

    with R._using(F, correction_prompt=prompt,
                  render_correction_launcher=launcher):
        yield


def prepare(out_dir, bound, findings=None):
    """F's own preparer, with this phase's renderer installed at its seam."""
    with correction_scope(findings):
        return F.prepare_corrections(out_dir, bound)


def finalize(out_dir, bound, findings=None):
    """F's own finalizer. The seam matters here too: run_evidence re-derives
    the prompt to prove the native state, so without the binding it would
    rebuild the HISTORICAL one and look for an answer-informed rulings file
    that this source-only phase does not have."""
    with correction_scope(findings):
        return F.finalize(out_dir, bound)


def corrected_shards(bound, findings=None):
    """F's own merge, read through the same installed renderer."""
    with correction_scope(findings):
        return F.corrected_shards(bound)


def bind(bound, corrections_run):
    """Carry the correction run explicitly. There is no fallback."""
    if not corrections_run:
        raise ValueError("a corrected binding needs its correction run; "
                         "falling back to the uncorrected key is refused")
    return bound._replace(corrections=corrections_run)


def gate_problems(bound, findings=None):
    """The existing signing gate, through the corrected binding only."""
    if bound.corrections is None:
        raise ValueError("this binding carries no correction run: refusing "
                         "rather than signing the uncorrected key")
    with correction_scope(findings):
        gate = F.signing_gate(bound.events, bound)
    return list(gate.get("stops") or [])


def ledger_before(bound):
    """The existing owner that counts completed correction attempts."""
    return F.decision_ledger_before(bound)


def _input_binding(path):
    """Read an explicitly served phase binding, never infer it from replies.

    The runner must pin this document and its profile read-only. A null
    profile declaration means NO additional input, not an optional attachment.
    Missing files or a missing declaration key cannot select that meaning.
    """
    doc = K._load(path)
    fields = {'source_run', 'source_package', 'package', 'profile'}
    if not isinstance(doc, dict) or set(doc) != fields or any(
            not isinstance(doc[k], str) or not os.path.isabs(doc[k])
            for k in fields):
        raise ValueError('correction input binding needs exactly four absolute paths')
    if os.path.realpath(doc['package']) == os.path.realpath(doc['source_package']):
        raise ValueError('the correction carrier must not replace the source carrier')
    profile = K._load(doc['profile'])
    if not isinstance(profile, dict) or R.RT.DECLARED_INPUT_KEY not in profile:
        raise ValueError('the served correction profile must explicitly declare its input')
    source = os.path.join(doc['source_package'], SK.MANIFEST_NAME)
    pins = collections.OrderedDict(
        (name, {'path': p, 'sha256': INV.sha_file(p)})
        for name, p in (('binding', path), ('source_manifest', source),
                        ('profile', doc['profile'])))
    pins['owner_sha256'] = INV.sha_file(__file__)
    return doc, pins


@contextlib.contextmanager
def _input_package_scope(path):
    doc, pins = _input_binding(path)
    original = SK.manifest

    def manifest():
        result = original()
        result['source_correction_inputs'] = pins
        return result

    with R._using(R.RT, LANE_INPUT_PROFILES=doc['profile']), \
            R._using(SK, manifest=manifest):
        yield doc


def build_input_package(path):
    """Existing builder, new immutable carrier; enter the source build scope first."""
    with _input_package_scope(path) as doc:
        os.makedirs(doc['package'])  # Claim a NEW destination; never overwrite a carrier.
        return SK.build(doc['package'])


@contextlib.contextmanager
def input_scope(path=None):
    """Select each phase's carrier at the existing owner boundaries.

    Enter inside R.final_scope or R.candidate_scope. Keep this scope around
    preparation, native proof, finalization and candidate/consumer reads.
    The new manifest pins this binding, the original manifest, the explicit
    profile and this owner; existing candidate/signature checks pin it in turn.
    Original source reads retain their exact original package and declaration.
    No parser, native proof rule, outcome or retry decision is replaced.
    """
    if path is None:
        yield
        return
    doc, pins = _input_binding(path)
    manifest = K._load(os.path.join(doc['package'], SK.MANIFEST_NAME))
    if manifest.get('source_correction_inputs') != pins:
        raise ValueError('the correction input binding differs from its frozen carrier')
    package_check, accepted = SK.package_problems, F.accepted_shards

    def check(package):
        if package == doc['package']:
            with _input_package_scope(path):
                return package_check(package)
        return package_check(package)

    def source_bound(run, bound, phase='events'):
        if (phase == 'events' and run == doc['source_run']
                and bound.package == doc['package']):
            return bound._replace(package=doc['source_package'])
        return bound

    def source_read(run, bound, phase='events'):
        return accepted(run, source_bound(run, bound, phase), phase)

    with R._using(SK, package_problems=check), \
            R._using(F, accepted_shards=source_read):
        yield


def provenance(bound, label, findings=None):
    """The identities this correction is bound to. Nothing is approved here."""
    body = correction_body(bound, label, findings)
    prefix = correction_prefix(bound, list(body))
    return collections.OrderedDict([
        ("schema", SCHEMA), ("source_id", label),
        ("served_source_only_prefix_sha256", K._sha(_served_prefix(bound))),
        ("correction_prefix_sha256", K._sha(prefix)),
        ("correction_prompt_sha256",
         K._sha(prefix + json.dumps(body, indent=1))),
        ("declared_keys", declared_keys(prefix)),
        ("original_raw_sha256", body["original_final_shard"]["sha256"]),
        ("original_open_issues", len(body["original_open_issues"])),
        ("findings", len(body[FINDINGS_KEY])),
        ("findings_sha256", K._sha(json.dumps(body[FINDINGS_KEY], indent=1))),
        ("owner_sha256", INV.sha_file(os.path.abspath(__file__))),
        ("package_manifest_sha256",
         INV.sha_file(os.path.join(bound.package, SK.MANIFEST_NAME))),
        ("event_finalization_sha256",
         INV.sha_file(os.path.join(bound.events, K.FINALIZATION_NAME))),
        ("ledger_before", ledger_before(bound)),
        ("population_approved", False), ("ceiling_approved", False),
        ("model_calls", 0)])
