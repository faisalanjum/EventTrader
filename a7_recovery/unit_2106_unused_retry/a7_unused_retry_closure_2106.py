"""Close a published retry that was NEVER launched and is no longer needed.

WHY NOT close_prelaunch_refusal. That owner closes a segment the transport
REFUSED: its inspector requires exactly one Workflow use naming the script and
one linked result flagged is_error. A never-launched segment has zero of each,
so satisfying it would mean fabricating a tool use and an error. This is a
separate closure with the opposite parent-record requirement, and it borrows
every check it can: W._no_output, W._states_naming, W._parent_records,
W._zero_capture_accounting, W._stable, G.preflight, G.account_segment,
G.load_root, G.latest_retry, G.whole_answers and F.read/F.scope all keep their
authority here.

WHY THERE IS NO RECOVERY REPORT PARAMETER. An earlier version took the caller's
recovery report and checked only that it named the right code and carried a
non-empty answer dict. Codex disproved that by handing it a fabricated report -
segment 999, a junk answer, recovered false - which it accepted. A report is a
claim; it can say anything. So nothing is taken on report now: the prior
segment is derived from the ORIGINAL eligible-retry owner, its own saved whole
reply is re-verified, and the approved F.read is called over those exact bytes
under F.scope, which verifies the live format code and rule against the
caller's external expectations before anything is read.

WHAT IT WRITES. One finalization, crediting zero calls and marking every
reserved lane uncalled - the single artifact that clears "one publication at a
time". It deletes and hides nothing: reservation, receipt, invocation and
script all stay, so the lane remains claimed and can never be re-reserved.

IT RESUMES. Interrupted artifacts are re-derived and required to match, never
overwritten, and the whole inspection is repeated immediately before writing.
"""
import collections
import io
import json
import os
import sys

CLOSURE_KIND = "unused_recovered_retry"
SCHEMA = "a7_unused_retry_closure/1"


def _load_owners(harness, format_dir):
    # the format owner imports a4_review_composite, which lives beside the
    # other a7 units rather than in the harness - the same path the approved
    # freeze payload adds.
    composite = os.path.join(os.path.dirname(format_dir), 'unit_2009/owner')
    for path in (harness, format_dir, composite):
        if path not in sys.path:
            sys.path.insert(0, path)
    import a7_g1_build as G
    import a7_g1_workflow_gate as W
    import a7_meaning_format_2105 as F
    return G, W, F


def evidence_path(G, run_dir, n):
    return os.path.join(run_dir, "unused_retry.%s.json" % G._seg(n))


def _prior_reading(G, F, out_dir, run_dir, root, root_sha, lane, attempt):
    """Is this lane's PRIOR reading complete and usable? -> (record, problems).

    Derived, never supplied: the prior segment comes from the original
    eligible-retry owner, and the answer comes from F.read over that segment's
    own re-verified whole reply and the frozen batch binding.
    """
    problems = []
    eligible = G.latest_retry(run_dir)
    prior = eligible.get(lane)
    if prior is None:
        return None, ["%s was not named a retry by the latest finalized "
                      "attempt-%d segment" % (lane, attempt - 1)]
    if G.segment_state(run_dir, prior) != "finalized":
        return None, ["the prior segment %d for %s is not finalized"
                      % (prior, lane)]

    final = G._read(G.finalization_path(run_dir, prior))
    validity = dict(final.get("validity") or [])
    if lane not in validity:
        return None, ["the prior segment %d records no verdict for %s"
                      % (prior, lane)]
    # ORIGINAL HISTORY IS PRESERVED, not rewritten: the prior reading must
    # still stand as invalid. A prior that was VALID needs no recovery and no
    # retry, and is not this case.
    if validity[lane] is not False:
        problems.append("the prior segment %d records %s as valid; this "
                        "closure is only for a recovered invalid reading"
                        % (prior, lane))
    if lane in (final.get("uncalled") or []):
        problems.append("the prior segment %d records %s as uncalled, so "
                        "there is no reading to recover" % (prior, lane))

    # the prior publication must still verify on its own terms
    _packet, prior_problems = G.preflight(out_dir, run_dir, prior, root_sha,
                                          final["receipt_sha256"])
    problems += ["prior segment %d: %s" % (prior, p) for p in prior_problems]

    whole, whole_problems = G.whole_answers(run_dir, prior)
    problems += ["prior segment %d: %s" % (prior, p) for p in whole_problems]
    if whole is None or lane not in (whole or {}):
        problems.append("the prior segment %d records no whole reply for %s"
                        % (prior, lane))

    # THE NATIVE CHECK. whole_answers verifies a record against its OWN
    # recorded hash, which a copied-and-rehashed record satisfies happily -
    # self-consistency is not native identity. The one audit owner re-derives
    # what actually ran from the approved root and receipt and the separately
    # captured rows, and the bound whole mapping must equal it exactly.
    audit_problems, native_whole = G.audit_official_state(
        run_dir, prior, root_sha, final["receipt_sha256"])
    problems += ["prior segment %d native audit: %s" % (prior, p)
                 for p in audit_problems]
    if not audit_problems and G._plain(whole or {}) != G._plain(native_whole):
        problems.append("the prior segment %d bound whole answers are not the "
                        "native audited ones" % prior)
    if problems:
        return None, problems

    rows = {row["lane_id"]: row for row in root["rows"]}
    doc, _digest = G.load_frozen(root["candidate_dir"],
                                 root["candidate_sha256"])
    binding, _parser = G.binding_and_parser(G.task_kind(doc))
    answer, remaining, audit = F.read(whole[lane],
                                      binding(doc, rows[lane]["batch_id"]))
    if remaining or answer is None:
        problems.append("%s is still unusable after the approved recovery: %s"
                        % (lane, list(remaining)[:2]))
    if not audit.get("recovered"):
        problems.append("the approved recovery did not recover %s" % lane)
    if audit.get("original_valid") is not False:
        problems.append("the recovery audit does not record %s as originally "
                        "invalid" % lane)
    if problems:
        return None, problems
    return collections.OrderedDict([
        ("prior_segment", prior),
        ("prior_attempt", final["attempt"]),
        ("prior_raw_sha256", audit.get("raw_sha256")),
        ("original_valid", audit.get("original_valid")),
        ("original_problems", list(audit.get("original_problems") or [])),
        ("recovered", True),
        ("conversions", len(audit.get("conversions") or [])),
    ]), []


def inspect(harness, format_dir, out_dir, run_dir, n, expect_root_sha,
            expect_receipt_sha, expect_gate_sha, expect_code_sha,
            expect_rule_sha, session_jsonl, allow=()):
    """READ-ONLY. Every condition that must hold. -> (evidence, problems)."""
    G, W, F = _load_owners(harness, format_dir)
    if W.owner_sha256() != expect_gate_sha:
        return None, ["the workflow gate is %s, not the reviewed %s"
                      % (W.owner_sha256(), expect_gate_sha)]

    _packet, problems = G.preflight(out_dir, run_dir, n, expect_root_sha,
                                    expect_receipt_sha)
    if problems:
        return None, problems
    receipt = G.load_receipt(run_dir, n)
    script_path = receipt["script_path"]

    # 1. NOTHING WAS LAUNCHED. Passing the script path for BOTH arguments keeps
    # the gate's prefilter as exactly "mentions this script"; an empty tool id
    # would be a substring of every line and disable it.
    uses, _results, problems = W._parent_records(session_jsonl, script_path,
                                                 script_path)
    if problems:
        return None, problems
    if uses:
        return None, ["the session records %d Workflow uses naming %s; a "
                      "never-launched segment has none"
                      % (len(uses), script_path)]
    matches, scanned, scan_problems = W._states_naming(script_path)
    if scan_problems:
        return None, scan_problems
    if matches:
        return None, ["%d official workflow states name %s"
                      % (len(matches), script_path)]

    # 2. NOTHING WAS PRODUCED.
    problems = list(W._no_output(run_dir, n, receipt, allow=allow))

    # 3. THE RESERVATION IS THE RECEIPT'S, and the sidecar is EXACTLY the
    # owner's empty shape. A missing, null, false or foreign-run sidecar is not
    # proof of no activity.
    reservation = G._read(G.reservation_path(run_dir, n))
    lanes = [r["lane_id"] for r in receipt["rows"]]
    if list(reservation.get("lanes") or []) != lanes:
        problems.append("the reservation lanes are not the receipt's rows")
    if reservation.get("attempt") != receipt["attempt"]:
        problems.append("the reservation attempt is not the receipt's")
    if not os.path.isfile(receipt["state_path"]):
        problems.append("the state sidecar does not exist")
    else:
        state = G._read(receipt["state_path"])
        want = collections.OrderedDict([("run_id", receipt["run_id"]),
                                        ("states", [])])
        if G._plain(state) != G._plain(want):
            problems.append("the state sidecar is not this receipt's empty "
                            "{run_id, states: []}")

    # 4. AND EVERY RESERVED LANE'S PRIOR READING IS COMPLETELY RECOVERED,
    # derived from the saved evidence under the pinned approved recovery.
    root = G.load_root(run_dir, expect_root_sha)
    priors = collections.OrderedDict()
    try:
        with F.scope(expect_code_sha, expect_rule_sha):
            for lane in lanes:
                record, lane_problems = _prior_reading(
                    G, F, out_dir, run_dir, root, expect_root_sha, lane,
                    receipt["attempt"])
                problems += lane_problems
                if record is not None:
                    priors[lane] = record
    except Exception as exc:                       # an unapproved pin refuses
        problems.append("the approved recovery scope refused: %s" % exc)

    if problems:
        return None, problems

    return collections.OrderedDict([
        ("schema", SCHEMA), ("closure", CLOSURE_KIND), ("segment", n),
        ("attempt", receipt["attempt"]), ("lanes", lanes),
        ("script_path", script_path),
        ("root_sha256", expect_root_sha),
        ("receipt_sha256", expect_receipt_sha),
        ("workflow_gate_sha256", expect_gate_sha),
        ("format_code_sha256", expect_code_sha),
        ("format_rule_sha256", expect_rule_sha),
        ("workflow_uses_naming_this_script", 0),
        ("official_states_naming_this_script", 0),
        ("state_sidecar_entries", 0),
        ("prior_reading", priors),
        ("model_calls", 0),
        ("reason", "the published retry was never launched and the prior "
                   "reading it existed to replace is completely recovered "
                   "under the approved format rule"),
        # NOT PART OF THIS CLOSURE'S IDENTITY. How many unrelated workflow
        # states exist in the session changes whenever anything else runs; a
        # staged closure must survive that. W._stable drops this key, while a
        # state naming THIS script still refuses above.
        ("transient", collections.OrderedDict([
            ("official_states_scanned", scanned)])),
    ]), []


def close(harness, format_dir, out_dir, run_dir, n, expect_root_sha,
          expect_receipt_sha, expect_gate_sha, expect_code_sha,
          expect_rule_sha, session_jsonl):
    """Durably close it. -> (final, problems). Resumable; never overwrites."""
    G, W, F = _load_owners(harness, format_dir)
    if os.path.isfile(G.finalization_path(run_dir, n)):
        return None, ["segment %d is already closed" % n]

    staged = []
    if os.path.isfile(evidence_path(G, run_dir, n)):
        staged.append("closure evidence")
    if os.path.isfile(G.accounting_path(run_dir, n)):
        if "closure evidence" not in staged:
            return None, ["segment %d has accounting but no closure evidence"
                          % n]
        staged.append("accounting")
    # Only accounting is a _no_output allowance. A REFUSAL evidence file must
    # never be allowed: a segment carrying one was closed as a transport
    # refusal, which this is not.
    allow = tuple(s for s in staged if s == "accounting")

    args = (harness, format_dir, out_dir, run_dir, n, expect_root_sha,
            expect_receipt_sha, expect_gate_sha, expect_code_sha,
            expect_rule_sha, session_jsonl)
    evidence, problems = inspect(*args, allow=allow)
    if problems:
        return None, problems

    if "closure evidence" in staged:
        if W._stable(G._read(evidence_path(G, run_dir, n))) != W._stable(evidence):
            return None, ["the staged closure evidence for segment %d is not "
                          "the evidence this run derives" % n]
    else:
        G._write_new(evidence_path(G, run_dir, n), G._pretty(evidence) + "\n")

    receipt = G.load_receipt(run_dir, n)
    if "accounting" in staged:
        staged_acc = G._read(G.accounting_path(run_dir, n))
        want = W._zero_capture_accounting(run_dir, n, receipt)
        if G._plain(staged_acc) != G._plain(want):
            return None, ["the staged accounting for segment %d is not the "
                          "canonical zero-capture accounting of it" % n]
        accounting = staged_acc
    else:
        accounting = G.account_segment(
            run_dir, n, G.load_root(run_dir, expect_root_sha))

    # THE LAST LOOK IS THE WHOLE INSPECTION, repeated: a use, a state, a
    # capture or a sidecar entry appearing after staging must still refuse.
    again, problems = inspect(*args, allow=("accounting",))
    if problems:
        return None, problems
    if W._stable(again) != W._stable(evidence):
        return None, ["the evidence for segment %d changed between staging and "
                      "finalization" % n]

    lanes = [r["lane_id"] for r in receipt["rows"]]
    final = collections.OrderedDict([
        ("schema", G.SCHEMA), ("segment", n), ("attempt", receipt["attempt"]),
        ("root_sha256", expect_root_sha),
        ("candidate_sha256", receipt["candidate_sha256"]),
        ("receipt_sha256", accounting["receipt_sha256"]),
        ("accounting_sha256", G._sha_file(G.accounting_path(run_dir, n))),
        # NOT A JUDGMENT. These lanes were never read at this attempt, so they
        # are neither valid nor invalid here; the prior attempt's own recorded
        # invalidity stands untouched in its own finalization.
        ("validity", []),
        ("problems", collections.OrderedDict()),
        ("retry", []), ("uncalled", list(lanes)),
        ("ledger", collections.OrderedDict([
            ("scheduled", 0), ("valid", 0), ("invalid", 0), ("retry", 0),
            ("uncalled", len(lanes))])),
        ("closure", CLOSURE_KIND),
        ("state_audited", False),
        ("credited", 0),
        ("closure_evidence_sha256", G._sha_file(evidence_path(G, run_dir, n))),
        ("workflow_gate_sha256", expect_gate_sha)])
    G._write_new(G.finalization_path(run_dir, n), G._pretty(final) + "\n")
    return final, []
