"""The SUCCESSOR round's six bindings, on the real owners and the real runs.

Zero calls, zero native writes, no mock of any owner under test. Each test
drives the live connection over the COMPLETED first v6 round on disk and
asserts the one property the next stage depends on, then breaks it.

Run before `a4_v6_successor` to reproduce the boundary, after it to see it
closed. `test_next_boundary_2072` states WHY a second round is needed at all.
"""
import collections
import contextlib
import copy
import json
from pathlib import Path
import sys
import unittest

A7 = Path(__file__).resolve().parents[1]
UNIT = Path(__file__).resolve().parent
for _rel in ("unit_2009/owner", "unit_2023_source_correction",
             "unit_2041_decision_connection", "unit_2053_owner_retry",
             "unit_2061_settlement_connection", "unit_2065_closeout_connection",
             "unit_2068_input_recovery", "unit_2069_targeted_source",
             "unit_2005/owner"):
    sys.path.insert(0, str(A7 / _rel))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
import a4_source_decision as D2041                                 # noqa: E402
import a4_source_recovery as RECOV                                 # noqa: E402
import a4_source_settlement as S2061                               # noqa: E402
import a4_source_closeout as C2065                                 # noqa: E402
import a4_phase_input as N                                         # noqa: E402
import a4_targeted_source as T2069                                 # noqa: E402
import build_final_key_candidate as CAND                           # noqa: E402
sys.path.insert(0, str(UNIT))
import a4_v6_successor as X                                        # noqa: E402

F, K, SK = R.F, R.K, R.SK
PREV_PACKET = A7 / "unit_2069_targeted_source/packet_codex_tarpkt2069_b"
SAVED = K._load(str(PREV_PACKET / "FINDINGS_BY_EVENT.json"))
PREVIOUS = [SAVED[k] for k in ("by_event", "decision_by_event",
                               "settlement_by_event", "closeout_by_event")]
FIRST_RUN = SAVED["targeted"]
FIRST_FINDINGS = SAVED["targeted_by_event"]
PHASE_PATH = SAVED["phase_input_binding"]
PHASE = K._load(PHASE_PATH)
CARRIER = K._load(PHASE["input_binding"])
FINDINGS = K._load(str(A7 / "unit_2020_codex_check/SOURCE_FINDINGS_2072.json")
                   )["findings"]


@contextlib.contextmanager
def lane():
    """The real closed lane, exactly as the first v6 round was prepared."""
    with R.final_scope(SAVED["review_run"], SAVED["review_package"],
                       bind_role=True), N.input_scope(PHASE_PATH):
        corrected = C2023.bind(SK.bound(SAVED["run"], CARRIER["package"]),
                               SAVED["corrections"])
        closed = C2065.bind(S2061.bind(D2041.bind(corrected, SAVED["decision"]),
                                       SAVED["settlement"]), PHASE["run"])
        with RECOV.recovery_scope(SAVED["recovery"], corrected, PREVIOUS[0]):
            yield closed


def successor(bound, findings=None):
    return X.successor_scope(bound, FINDINGS if findings is None else findings,
                             FIRST_RUN, FIRST_FINDINGS, PREVIOUS)


def body_of(prompt):
    return json.loads(prompt.split("[INPUT]\n", 1)[1])


def refuses(fn):
    try:
        fn()
    except (ValueError, KeyError, OSError) as exc:
        return "%s: %s" % (type(exc).__name__, exc)
    return None


class ThePopulationIsTheTwoReviewedEvents(unittest.TestCase):

    def test_the_existing_owner_selects_exactly_the_reviewed_sources(self):
        with lane() as bound, successor(bound):
            self.assertEqual(F.v6_labels(bound), list(FINDINGS))

    def test_the_ceiling_is_the_two_affected_events_and_nothing_wider(self):
        with lane() as bound, successor(bound):
            self.assertEqual(len(F.v6_labels(bound)), len(FINDINGS))
            self.assertEqual(len(F.v6_scripts(bound)), len(FINDINGS))

    def test_an_event_the_first_round_never_accepted_refuses(self):
        extra = dict(FINDINGS)
        outsider = next(s for s in FIRST_FINDINGS if s not in FINDINGS)
        row = copy.deepcopy(FINDINGS[next(iter(FINDINGS))][0])
        row["source_id"] = "no-such-source"
        extra["no-such-source"] = [row]
        with lane() as bound, successor(bound, extra):
            self.assertIsNotNone(refuses(lambda: F.v6_labels(bound)))
        self.assertIn(outsider, FIRST_FINDINGS)

    def test_no_findings_at_all_refuses_rather_than_defaulting(self):
        with lane() as bound, successor(bound, {}):
            self.assertIsNotNone(refuses(lambda: F.v6_labels(bound)))

    def test_a_changed_population_order_refuses(self):
        with lane() as bound, successor(
                bound, dict(reversed(list(FINDINGS.items())))):
            self.assertIsNotNone(refuses(lambda: F.v6_labels(bound)))


class TheBodyCarriesTheFirstRoundsReply(unittest.TestCase):

    def test_the_prior_reply_is_the_first_v6_answer_named_for_its_round(self):
        with lane() as bound:
            _s, raws = X.first_round_accepted(bound, FIRST_RUN,
                                              FIRST_FINDINGS, PREVIOUS)
            with successor(bound):
                for sid in F.v6_labels(bound):
                    body = body_of(F.v6_prompt(bound, sid))
                    self.assertIn(X.PRIOR_KEY, body)
                    self.assertNotIn("v5_shard", body)
                    self.assertEqual(body[X.PRIOR_KEY]["origin"],
                                     X.PRIOR_ORIGIN)
                    self.assertEqual(body[X.PRIOR_KEY]["raw"], raws[sid])
                    self.assertEqual(body[X.PRIOR_KEY]["sha256"],
                                     K._sha(raws[sid]))

    def test_the_reviewed_finding_binds_to_the_raw_the_body_shows(self):
        with lane() as bound, successor(bound):
            for sid in F.v6_labels(bound):
                body = body_of(F.v6_prompt(bound, sid))
                self.assertEqual(body["reviewer_finding"]["finding"],
                                 FINDINGS[sid])
                self.assertEqual(FINDINGS[sid][0]["raw_sha256"],
                                 body[X.PRIOR_KEY]["sha256"])

    def test_the_declaration_names_exactly_the_keys_the_body_sends(self):
        with lane() as bound, successor(bound):
            for sid in F.v6_labels(bound):
                prompt = F.v6_prompt(bound, sid)
                self.assertEqual(C2023.declared_keys(prompt),
                                 list(body_of(prompt)))
                self.assertEqual(prompt.count("v5_shard"), 0)

    def test_the_served_base_is_the_source_only_repaired_prefix(self):
        with lane() as bound, successor(bound):
            prompt = F.v6_prompt(bound, F.v6_labels(bound)[0])
        self.assertIn("[A7 SOURCE CORRECTION TASK]", prompt)
        self.assertNotIn("[A4 FINAL DECISION TASK]", prompt)

    def test_the_script_the_receipt_would_pin_carries_that_same_body(self):
        with lane() as bound, successor(bound):
            sid = F.v6_labels(bound)[0]
            script = F.render_v6_launcher(bound, sid, 1)
            self.assertIn(json.dumps(F.v6_prompt(bound, sid)), script)
            self.assertLess(len(script.encode("utf-8")), K.TRANSPORT_LIMIT)

    def test_a_finding_bound_to_any_other_identity_refuses(self):
        for field, value in (("raw_sha256", "0" * 64),
                             ("source_id", "not-this-source"),
                             ("row", "not-this-row")):
            changed = copy.deepcopy(FINDINGS)
            changed[next(iter(changed))][0][field] = value
            with lane() as bound, successor(bound, changed):
                self.assertIsNotNone(refuses(lambda: F.v6_scripts(bound)),
                                     field)

    def test_a_finding_bound_to_the_closeout_reply_refuses(self):
        """The superseded raw is the exact mistake this round must not make."""
        with lane() as bound:
            with C2065._render_scope(*PREVIOUS):
                _s, closeout_raws, bad = F.accepted_shards(
                    bound.decision_correction_v5, bound, C2065.PHASE)
            self.assertFalse(bad)
            stale = copy.deepcopy(FINDINGS)
            sid = next(iter(stale))
            stale[sid][0]["raw_sha256"] = K._sha(closeout_raws[sid])
            with successor(bound, stale):
                self.assertIsNotNone(refuses(lambda: F.v6_scripts(bound)))


class TheMergeBaseIsTheFirstRoundsKey(unittest.TestCase):

    def test_the_base_is_the_completed_first_round_not_the_closeout(self):
        with lane() as bound:
            with C2065.closeout_scope(*PREVIOUS):
                closeout_origins = F.v5_shards(bound)[2]
            with successor(bound):
                shards, _raws, origins, bad = F.v5_shards(bound)
        self.assertEqual(bad, [])
        self.assertEqual(len(shards), len(closeout_origins))
        first = collections.Counter(origins.values())[X.ORIGIN]
        self.assertEqual(first, len(FIRST_FINDINGS))
        self.assertEqual(collections.Counter(closeout_origins.values())[X.ORIGIN],
                         0)

    def test_the_four_carried_corrections_keep_the_first_rounds_content(self):
        carried = [s for s in FIRST_FINDINGS if s not in FINDINGS]
        with lane() as bound:
            _s, first_raws = X.first_round_accepted(bound, FIRST_RUN,
                                                    FIRST_FINDINGS, PREVIOUS)
            with successor(bound):
                _sh, raws, origins, _bad = F.v5_shards(bound)
        self.assertEqual(len(carried), 4)
        for sid in carried:
            self.assertEqual(raws[sid], first_raws[sid])
            self.assertEqual(origins[sid], X.ORIGIN)


class TheCountIsEveryPreviousCallOnce(unittest.TestCase):

    def test_the_ledger_before_adds_the_first_round_exactly_once(self):
        with lane() as bound:
            short = F.v6_ledger_before(bound)
            authoritative = CAND.signer_ledger_before(
                X.first_bound(bound, FIRST_RUN))
            with successor(bound):
                served = F.v6_ledger_before(bound)
        made = X._finalized_scheduled(FIRST_RUN)
        self.assertEqual(served - short, made)
        self.assertEqual(served, authoritative)
        self.assertEqual(made, len(FIRST_FINDINGS))

    def test_the_signer_owner_adds_this_round_on_top_without_double_count(self):
        with lane() as bound:
            with successor(bound):
                served = F.v6_ledger_before(bound)
                # no successor run is finalized yet, so the authoritative
                # count before the signer is still the count before this round
                self.assertEqual(CAND.signer_ledger_before(bound), served)


class TheHistoryPinsTheFirstRound(unittest.TestCase):

    def test_this_phase_pins_the_first_round_and_earlier_phases_do_not(self):
        with lane() as bound, successor(bound):
            mine = F._phase_history(bound, X.PHASE)
            earlier = F._phase_history(bound, "decision_correction_v5")
        self.assertIn("v6", mine)
        self.assertEqual(mine["v6"], F._run_evidence_pins(FIRST_RUN))
        self.assertNotIn("v6", earlier)

    def test_the_earlier_receipts_on_disk_still_re_derive_unchanged(self):
        with lane() as bound, successor(bound):
            for run in (bound.events, bound.corrections, bound.decision,
                        bound.decision_correction, bound.decision_correction_v5):
                self.assertEqual(F._receipt_still_the_proved_one(run, bound),
                                 [], run)


class TheFirstRoundIsReadUnderItsOwnInputs(unittest.TestCase):

    def test_the_first_rounds_frozen_prompts_still_re_derive_byte_identically(self):
        with lane() as bound:
            fb = X.first_bound(bound, FIRST_RUN)
            with X.first_round_scope(bound, FIRST_RUN, FIRST_FINDINGS,
                                     PREVIOUS):
                stale = F._receipt_still_the_proved_one(FIRST_RUN, fb)
                redone = {s: K._sha(F.v6_prompt(fb, s))
                          for s in F.v6_labels(fb)}
        receipt = K._load(str(Path(FIRST_RUN) / K.RECEIPT_NAME))
        self.assertEqual(stale, [])
        self.assertEqual(len(redone), len(FIRST_FINDINGS))
        self.assertEqual({s: receipt["prompts"][s] for s in redone}, redone)

    def test_the_first_round_still_reports_one_finalized_call_per_event(self):
        fin = K._load(str(Path(FIRST_RUN) / K.FINALIZATION_NAME))
        self.assertEqual(fin["phase"], X.PHASE)
        self.assertEqual(fin["ledger"]["scheduled"], len(FIRST_FINDINGS))


class TheScopeLeavesNoOwnerSwapped(unittest.TestCase):

    def test_every_swapped_owner_is_restored_when_the_scope_exits(self):
        with lane() as bound:
            before = {n: getattr(F, n) for n in X._ORIGINAL}
            with successor(bound):
                inside = {n: getattr(F, n) for n in X._ORIGINAL}
            after = {n: getattr(F, n) for n in X._ORIGINAL}
        self.assertEqual(after, before)
        self.assertEqual(before, dict(X._ORIGINAL))
        self.assertTrue(all(inside[n] is not before[n] for n in X._ORIGINAL))

    def test_a_prompt_asked_for_a_different_carrier_refuses(self):
        with lane() as bound, successor(bound):
            other = bound._replace(package="/TEST_ONLY/not-this-package")
            self.assertIsNotNone(
                refuses(lambda: F.v6_prefix(other.package, ("menu",))))


if __name__ == "__main__":
    unittest.main(verbosity=2)
