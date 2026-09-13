# -*- coding: utf-8 -*-
"""The owner-directed RESULT RECOVERY connection (Codex SEQ 2053 / 2054 / 2055).

One narrow versioned successor binding, in the shape `a4_source_correction`
(C2023) and `a4_source_decision` (D2041) already use. It recovers ONE already
saved result into the verified correction chain and does nothing else. Zero
model calls: this module never launches anything.

Codex SEQ 2054 named four executed failures in the first version of this file
(reviewed at b883b535..., kept byte-identical under `reviewed/`). All four came
from the same mistake: the connection was made at a HIGH-LEVEL merge of my own
that the real consumers do not read. The repair moves it down to the seams the
consumers actually use, and deletes the competing merge and the parallel count:

  * `accepted_shards` - the correction phase's own read. `F.prior_replies`,
    `F.corrected_shards`, the gate, the candidate and the grader all reach the
    key through it, so binding it once is the whole connection. The recovered
    reply now IS a correction-phase reply wherever one is read.
  * `_phase_owed` - the frozen run is no longer asked for the recovered labels,
    because the recovery run answers them. Its bytes on disk never change.
  * `_expected_for` - the recovery run's own receipt expectation is the labels
    it recovers.
  * `decision_ledger_before` - the real next phase's budget counts the extra
    call. There is no separate number left to disagree with.
  * `_prior_runs` - the next phase's freshness sees the recovery run, so a
    later call cannot reuse the recovered call's identities.
  * `history_evidence` / `history_unchanged` - the next receipt PINS the
    recovery run's own bytes and re-measures them, exactly as it pins v1/v2.

Honesty is carried in data, not in silence: the run holds a pinned record
naming its authority, its frozen parent's exact hashes, the labels it recovers,
the exact saved state / response / transcript identities it recovers them from,
and the real ordinal of the extra call. Every one of those is ENFORCED on every
read - a record missing or drifting from any of them refuses, and a different
later successful call cannot be substituted for the specifically saved result.
The failed attempt stays in the accounting; nothing is backdated and no native
attempt is relabelled.

The context is carried by a PERSISTED binding document, in the shape
`C2023.input_scope` already uses, so a cold caller reconstructs exactly this
context from one path instead of an unpinned argument.

Codex SEQ 2055 closed three more gaps, all about the record's own identity:
  * the binding PINS the record's hash, and that one pin replaces every
    per-field validator - any changed field changes the hash;
  * the pin is rechecked at the consumer read boundary on EVERY read, so a
    record that changes after a good read cannot keep its credit through the
    shard caches;
  * the next receipt's history pins the record too, and the CANDIDATE's own
    counter shares the one extra-attempt derivation with the next phase's, so
    the two can never disagree.
"""
import collections
import contextlib
import json
import os
import sys
from pathlib import Path

UNIT = Path(__file__).resolve().parent
A7 = UNIT.parent
sys.path.insert(0, str(A7 / "unit_2009/owner"))
sys.path.insert(0, str(A7 / "unit_2023_source_correction"))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402

F, K, SK, INV = R.F, R.K, R.SK, R.INV
SCHEMA = "a7-source-recovery/2054"
RECORD_NAME = "recovery.json"
PHASE = "corrections"
#: the tag this run is pinned under in the next phase's receipt. It is its own
#: tag, never `v2`: the frozen v2 receipt on disk recorded no recovery and must
#: keep re-deriving exactly as it was written.
HISTORY_TAG = "v2_recovery"
#: the frozen outcome a label must carry to be recoverable at all: a call that
#: was scheduled and returned no answer. A valid or invalid outcome is not
#: recoverable here, and neither is an event the phase never scheduled.
RECOVERABLE = ("transport_no_answer",)
#: the record's own shape. Enforced exactly - an extra or missing key refuses,
#: so a field cannot be quietly dropped and go on being cited.
RECORD_FIELDS = ("schema", "kind", "authority", "recovered_labels",
                 "frozen_parent", "result_evidence", "extra_call_ordinal",
                 "model_calls_by_this_module")
PARENT_FIELDS = ("run_dir", "receipt_sha256", "finalization_sha256", "ledger",
                 "recovered_from_outcome")
#: the three saved identities every recovered label is bound to.
EVIDENCE_PARTS = ("state", "response", "transcript")
EVIDENCE_FIELDS = ("native_path", "preserved_path", "sha256", "bytes")
BINDING_FIELDS = ("recovery_run", "corrections_run", "record_sha256")


def _hex64(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _frozen(bound):
    """The frozen parent's own receipt and finalization. -> (paths, doc)"""
    receipt = os.path.join(bound.corrections, K.RECEIPT_NAME)
    final = os.path.join(bound.corrections, K.FINALIZATION_NAME)
    if not (os.path.isfile(receipt) and os.path.isfile(final)):
        raise ValueError("the frozen correction parent is not published")
    return (receipt, final), K._load(final)


def write_record(run_dir, bound, result_evidence, authority):
    """The honest successor record. Written BEFORE the receipt, once.

    It says what this run is: recovery AFTER the call, of results that already
    exist, bound to the frozen parent it follows and to the EXACT saved
    evidence it recovers. The population is the evidence's own keys - a label
    with no pinned saved result cannot be recovered, so the two cannot drift.
    """
    (receipt, final), doc = _frozen(bound)
    labels = list(result_evidence)
    outcome = {row[0]: row[1] for row in doc["outcomes"]}
    for label in labels:
        if outcome.get(label) not in RECOVERABLE:
            raise ValueError("%s is not a recoverable frozen outcome: %r"
                             % (label, outcome.get(label)))
    os.path.isdir(run_dir) or os.makedirs(run_dir)
    record_doc = collections.OrderedDict([
        ("schema", SCHEMA),
        ("kind", "recovery of an already saved result, after the call; not a "
                 "scheduled phase, not a retry allowance, not an approval"),
        ("authority", authority),
        ("recovered_labels", labels),
        ("frozen_parent", collections.OrderedDict([
            ("run_dir", bound.corrections),
            ("receipt_sha256", INV.sha_file(receipt)),
            ("finalization_sha256", INV.sha_file(final)),
            ("ledger", doc["ledger"]),
            ("recovered_from_outcome",
             collections.OrderedDict((l, outcome[l]) for l in labels))])),
        ("result_evidence", result_evidence),
        # the real ordinal of the extra call inside the correction line: the
        # frozen schedule plus this recovery's own calls. It is recorded here
        # instead of being hidden inside the parent's own count.
        ("extra_call_ordinal", doc["ledger"]["scheduled"] + len(labels)),
        ("model_calls_by_this_module", 0)])
    K.RT.write_new(os.path.join(run_dir, RECORD_NAME),
                   json.dumps(record_doc, indent=1))
    return record_doc


def record(run_dir, expected=None):
    """The run's record, checked against the hash its binding PINS.

    Codex SEQ 2055: one frozen expected hash, not eight competing validators.
    Any change to any field changes the hash, so the pin covers every
    changed-field case - cold and after a good read. The shape check names
    only the fields this owner reads, so a truncated record refuses with a
    reason instead of a KeyError. The hash is measured BEFORE the load, so a
    substituted document cannot answer for its own identity.
    """
    path = os.path.join(run_dir, RECORD_NAME)
    if expected is not None and INV.sha_file(path) != expected:
        raise ValueError("the recovery record is not the pinned one")
    doc = K._load(path)
    if not isinstance(doc, dict) or tuple(doc) != RECORD_FIELDS:
        raise ValueError("the recovery record must carry exactly %s"
                         % (list(RECORD_FIELDS),))
    return doc


def _extra_calls(run_dir):
    """THE ONE extra-attempt derivation. Every counter that must see the
    recovery call reads it from here, so two counters cannot disagree."""
    total = 0
    for base in (run_dir, os.path.join(run_dir, "retry")):
        fin = os.path.join(base, K.FINALIZATION_NAME)
        if os.path.isfile(fin):
            total += K._load(fin)["ledger"]["scheduled"]
    return total


def _saved_pin(doc, label, part):
    return doc["result_evidence"][label][part]


def recovery_labels(run_dir, bound, expected=None):
    """The labels this recovery run answers, DERIVED and re-proved every read.

    Nothing here is taken on trust: the record's shape, its frozen parent's
    live hashes, each label's frozen outcome, each label still being an owed
    correction, the extra ordinal, the saved evidence still measuring exactly
    what was pinned, and - once the run has recorded anything - the recorded
    state being one of the pinned saved states. A later successful call is a
    different state and a different response, so it cannot be substituted for
    the specifically saved result under a generic authority string.
    """
    doc = record(run_dir, expected)
    (receipt, final), frozen = _frozen(bound)
    if doc["frozen_parent"]["receipt_sha256"] != INV.sha_file(receipt) \
            or doc["frozen_parent"]["finalization_sha256"] != INV.sha_file(final):
        raise ValueError("the recovery record does not bind this frozen parent")
    outcome = {row[0]: row[1] for row in frozen["outcomes"]}
    owed = set(C2023.correction_labels(bound))
    for label in doc["recovered_labels"]:
        if outcome.get(label) not in RECOVERABLE or label not in owed:
            raise ValueError("%s is not a recoverable owed correction" % label)
    if doc["extra_call_ordinal"] != (frozen["ledger"]["scheduled"]
                                     + len(doc["recovered_labels"])):
        raise ValueError("the extra call ordinal is not this run's real place "
                         "after the frozen schedule")
    states = set()
    for label in doc["recovered_labels"]:
        for part in EVIDENCE_PARTS:
            pin = _saved_pin(doc, label, part)
            path = pin["preserved_path"]
            if not os.path.isfile(path) or INV.sha_file(path) != pin["sha256"] \
                    or os.path.getsize(path) != pin["bytes"]:
                raise ValueError("the saved %s of %s is missing or changed"
                                 % (part, label))
        states.add(_saved_pin(doc, label, "state")["native_path"])
    live = os.path.join(run_dir, K.RECEIPT_NAME)
    if os.path.isfile(live):
        for state in K._load(live).get("states") or []:
            if state not in states:
                raise ValueError("this run recorded a state that is not the "
                                 "saved result it is authorized to recover")
    order = [t["source_id"] for t in F.event_tasks(bound.evidence)]
    return [s for s in order if s in set(doc["recovered_labels"])]


def binding(path):
    """The PERSISTED recovery context: two absolute paths, and its own pins.

    Same shape as the served correction input binding (`C2023._input_binding`)
    so a cold caller reconstructs this exact context from one path. The pins
    are returned for the caller to report; the enforcing is the record's.
    """
    doc = K._load(path)
    if not isinstance(doc, dict) or tuple(doc) != BINDING_FIELDS or any(
            not isinstance(doc[k], str) or not os.path.isabs(doc[k])
            for k in ("recovery_run", "corrections_run")):
        raise ValueError("a recovery binding needs exactly %s - two absolute "
                         "paths and the record's own hash"
                         % (list(BINDING_FIELDS),))
    if not _hex64(doc["record_sha256"]):
        raise ValueError("the recovery binding pins no measured record hash")
    for key in ("recovery_run", "corrections_run"):
        if not os.path.isdir(doc[key]):
            raise ValueError("the declared %s does not exist" % key)
    held = record(doc["recovery_run"], doc["record_sha256"])
    if os.path.realpath(held["frozen_parent"]["run_dir"]) \
            != os.path.realpath(doc["corrections_run"]):
        raise ValueError("the recovery run does not follow the declared "
                         "correction run")
    pins = collections.OrderedDict(
        (name, {"path": p, "sha256": INV.sha_file(p)})
        for name, p in (("binding", path),
                        (RECORD_NAME, os.path.join(doc["recovery_run"],
                                                   RECORD_NAME))))
    pins["owner_sha256"] = INV.sha_file(os.path.abspath(__file__))
    return doc, pins


@contextlib.contextmanager
def recovery_scope(path, bound, correction_findings=None):
    """The recovery, connected at the seams the real consumers read.

    `path` is the persisted binding document. Everything else stays the
    existing owner's: the prompt, the native proof, the parser, the finalizer,
    the retry law, the merge's own rules, the gate, the signer and the lock.
    `F.RETRYABLE` is untouched.
    """
    doc, _pins = binding(path)
    run_dir, pinned = doc["recovery_run"], doc["record_sha256"]
    if bound.corrections is None or os.path.realpath(bound.corrections) \
            != os.path.realpath(doc["corrections_run"]):
        raise ValueError("this binding is not the correction run the recovery "
                         "context declares")
    labels = recovery_labels(run_dir, bound, pinned)
    recovered = set(labels)
    frozen_dir = os.path.abspath(bound.corrections)
    recovery_dir = os.path.abspath(run_dir)
    real_expected, real_owed = F._expected_for, F._phase_owed
    real_accepted, real_before = F.accepted_shards, F.decision_ledger_before
    real_prior, real_hist = F._prior_runs, F.history_evidence
    real_unchanged, real_v4 = F.history_unchanged, F.v4_ledger_before

    def expected_for(out_dir, b, receipt):
        if os.path.abspath(out_dir) != recovery_dir:
            return real_expected(out_dir, b, receipt)
        if receipt.get("phase") != PHASE or receipt.get("attempt") != 1:
            return None, ["a recovery run is this phase's own attempt 1 for the "
                          "labels it recovers"]
        return F.expected_receipt(out_dir, b, PHASE, 1, labels, None), []

    def phase_owed(event_dir, default):
        owed = real_owed(event_dir, default)
        if os.path.abspath(event_dir) == frozen_dir:
            # the recovery run answers these, so the frozen run is no longer
            # asked for them. Its bytes on disk are untouched.
            return owed - recovered
        return owed

    def accepted_shards(event_dir, b, phase="events"):
        """THE correction-phase read, recovery included. One merge, one place.

        Everything downstream - the next prompt's prior replies, the corrected
        key, the gate, the candidate, the grader - reads the phase through
        here, so there is no second merged view for a caller to disagree with.
        """
        shards, raws, bad = real_accepted(event_dir, b, phase)
        if phase != PHASE or os.path.abspath(event_dir) != frozen_dir:
            return shards, raws, bad
        # RECHECKED HERE, on every read, before any credit: the shard reads
        # below are cached on their own receipts, so a record that changed
        # after the scope opened would otherwise keep being believed
        # (Codex SEQ 2055). The pinned hash is the whole check.
        held = record(run_dir, pinned)
        rec, recraws, recbad = real_accepted(run_dir, b, PHASE)
        bad = list(bad) + list(recbad)
        for label, shard in rec.items():
            want = _saved_pin(held, label, "response")["sha256"]
            if K._sha(recraws[label]) != want:
                raise ValueError("%s recovered a reply that is not the saved "
                                 "result this run is bound to" % label)
            shards[label], raws[label] = shard, recraws[label]
        order = [t["source_id"] for t in F.event_tasks(b.evidence)]
        return (collections.OrderedDict((s, shards[s]) for s in order
                                        if s in shards),
                collections.OrderedDict((s, raws[s]) for s in order
                                        if s in raws), bad)

    def decision_ledger_before(b):
        """The real next phase's counter, with the extra call in it."""
        return real_before(b) + _extra_calls(run_dir)

    def v4_ledger_before(b):
        """The CANDIDATE's own counter, from the SAME derivation. It walks the
        old phases independently, so it needs the extra call independently -
        and it must never disagree with the one above (Codex SEQ 2055)."""
        return real_v4(b) + _extra_calls(run_dir)

    def prior_runs(out_dir, b, receipt):
        """Freshness: a later phase may not reuse the recovered identities."""
        dirs = real_prior(out_dir, b, receipt)
        if frozen_dir in [os.path.abspath(d) for d in dirs]:
            dirs = list(dirs) + [d for d in (run_dir,
                                             os.path.join(run_dir, "retry"))
                                 if os.path.isdir(d)]
        return dirs

    def history_evidence(b, tags=("v1", "v2")):
        """The next receipt pins the recovery run's own bytes too."""
        out = real_hist(b, tags)
        if "v2" in tags:
            pins = F._run_evidence_pins(run_dir)
            # the run's receipt/finalization/raw tree do NOT cover the record,
            # so the next receipt would pin everything about this run except
            # the document that authorizes it (Codex SEQ 2055).
            pins[RECORD_NAME] = INV.sha_file(os.path.join(run_dir, RECORD_NAME))
            out[HISTORY_TAG] = pins
        return out

    def history_unchanged(b, pinned):
        """...and re-measures them, so a later edit to it refuses."""
        rest = collections.OrderedDict(
            (k, v) for k, v in pinned.items() if k != HISTORY_TAG)
        bad = list(real_unchanged(b, rest))
        if HISTORY_TAG in pinned:
            bad += F._pins_unchanged(run_dir, pinned[HISTORY_TAG], HISTORY_TAG)
        return bad

    with C2023.correction_scope(correction_findings), \
            R._using(F, _expected_for=expected_for, _phase_owed=phase_owed,
                     accepted_shards=accepted_shards,
                     decision_ledger_before=decision_ledger_before,
                     _prior_runs=prior_runs, history_evidence=history_evidence,
                     history_unchanged=history_unchanged,
                     v4_ledger_before=v4_ledger_before):
        yield labels


def prepare(path, bound, correction_findings=None):
    """Write the receipt through F's own writer. Launches nothing: the result
    being recovered already exists."""
    run_dir = binding(path)[0]["recovery_run"]
    with recovery_scope(path, bound, correction_findings) as derived:
        F._write_receipt(run_dir, bound, PHASE, 1, derived)
        receipt = K._load(os.path.join(run_dir, K.RECEIPT_NAME))
        bad = F.receipt_problems(run_dir, bound, receipt)
    return {"ok": not bad, "problems": bad, "labels": derived}


def record_state(path, bound, state_path, correction_findings=None):
    """The existing recorder, inside this run's own expectation."""
    run_dir = binding(path)[0]["recovery_run"]
    with recovery_scope(path, bound, correction_findings):
        return F.record_state(run_dir, state_path)


def finalize(path, bound, correction_findings=None):
    """F's own finalizer, over this run's own population."""
    run_dir = binding(path)[0]["recovery_run"]
    with recovery_scope(path, bound, correction_findings):
        return F.finalize(run_dir, bound)


def gate_problems(path, bound, correction_findings=None):
    """The existing signing gate, over the recovered key."""
    with recovery_scope(path, bound, correction_findings):
        return list(F.signing_gate(bound.events, bound).get("stops") or [])


def attempts(path, bound):
    """The whole accounting, with the failed attempt kept. -> ordered counts.

    A REPORT derived from the two finalizations and the record, not a second
    counter: the budget the next phase actually spends is F's own, bound above.
    """
    run_dir = binding(path)[0]["recovery_run"]
    (_paths, frozen) = _frozen(bound)
    ledger = dict(frozen["ledger"])
    fin = os.path.join(run_dir, K.FINALIZATION_NAME)
    extra = K._load(fin)["ledger"] if os.path.isfile(fin) else {}
    made = _extra_calls(run_dir)
    return collections.OrderedDict([
        ("frozen_scheduled", ledger["scheduled"]),
        ("frozen_valid", ledger["valid"]),
        ("frozen_transport_no_answer", ledger["transport_no_answer"]),
        ("recovery_scheduled", extra.get("scheduled", 0)),
        ("recovery_valid", extra.get("valid", 0)),
        ("calls_made_in_the_correction_line", ledger["scheduled"] + made),
        ("accepted_corrections", ledger["valid"] + extra.get("valid", 0)),
        ("the_refusal_is_still_counted_once",
         ledger["transport_no_answer"] == 1),
        ("extra_call_ordinal", record(run_dir)["extra_call_ordinal"])])
