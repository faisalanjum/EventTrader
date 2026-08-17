#!/usr/bin/env python3
"""Focused tests for the source-choice Qwen table screen."""

from __future__ import annotations

import hashlib
import json
import unittest

import choice_v2


HTML = b"""
<html><body><table>
  <tr><th></th><th>Three Months Ended</th><th>Three Months Ended</th></tr>
  <tr><th></th><th>2025</th><th>2024</th></tr>
  <tr><th colspan="3">Gas Sales</th></tr>
  <tr><td>Natural Gas</td><td>51</td><td>48</td></tr>
  <tr><th colspan="3">Gas Revenues</th></tr>
  <tr><td>Natural Gas</td><td>282</td><td>278</td></tr>
</table></body></html>
"""

TABLE_ID = "example.htm#t0"
TABLE_META = {
    "source_file": "example.htm",
    "source_sha256": hashlib.sha256(HTML).hexdigest(),
}


def request() -> dict:
    return {
        "request_id": "q1",
        "table": TABLE_ID,
        "ask": {
            "label_wording": "Natural Gas Revenue",
            "target": (
                "occurrence #2 of the 2 asked cells of that labeled row "
                "(ordinal screen simplification)"
            ),
        },
        "anchor_id": "anchor-1",
    }


class SourceMenuTests(unittest.TestCase):
    def test_real_source_geometry_builds_clean_complete_choices(self):
        choices = choice_v2.build_table_choices(
            TABLE_ID, TABLE_META, HTML)

        self.assertEqual(len(choices), 4)
        self.assertEqual(
            [item["value"] for item in choices], ["51", "48", "282", "278"])
        self.assertEqual(
            choices[2],
            {
                "choice": 3,
                "block_id": "example.htm#t0-r05",
                "occurrence_id": "example.htm#t0-r05-o1",
                "label": "Natural Gas",
                "section": "Gas Revenues",
                "caption": "",
                "value": "282",
                "period_headers": ["Three Months Ended", "2025"],
            },
        )

    def test_source_hash_mismatch_fails_before_building_choices(self):
        bad = dict(TABLE_META, source_sha256="0" * 64)

        with self.assertRaisesRegex(ValueError, "source hash"):
            choice_v2.build_table_choices(TABLE_ID, bad, HTML)


class BlindCaseTests(unittest.TestCase):
    def test_prompt_contains_clean_choices_but_no_source_ids_or_markers(self):
        choices = choice_v2.build_table_choices(
            TABLE_ID, TABLE_META, HTML)
        case = choice_v2.build_model_case(
            "case-1", request(), choices)

        self.assertIn("Natural Gas Revenue", case["prompt"])
        self.assertIn("Gas Revenues", case["prompt"])
        self.assertIn('headers=[\"Three Months Ended\", \"2024\"]',
                      case["prompt"])
        self.assertNotIn("example.htm", case["prompt"])
        self.assertNotIn("occurrence_id", case["prompt"])
        self.assertNotIn("expected_", case["prompt"])
        self.assertNotIn("\u27e8", case["prompt"])
        self.assertEqual(
            case["schema"]["properties"]["choice"]["enum"],
            [None, 1, 2, 3, 4],
        )
        self.assertEqual(
            set(case["schema"]["properties"]), {"choice"})

    def test_hidden_answers_are_not_an_input_to_case_builder(self):
        self.assertEqual(
            list(choice_v2.build_cases_from_calls.__code__.co_varnames[
                :choice_v2.build_cases_from_calls.__code__.co_argcount
            ]),
            ["calls", "source_loader"],
        )


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        choices = choice_v2.build_table_choices(
            TABLE_ID, TABLE_META, HTML)
        self.case = choice_v2.build_model_case(
            "case-1", request(), choices)

    def test_code_reconstructs_every_exact_evidence_field(self):
        answer = choice_v2.reconstruct_answer(self.case, 4)

        self.assertEqual(
            answer,
            {
                "request_id": "q1",
                "anchor_id": "anchor-1",
                "block_id": "example.htm#t0-r05",
                "occurrence_id": "example.htm#t0-r05-o2",
                "copied_label": "Natural Gas",
                "copied_period_evidence": ["Three Months Ended", "2024"],
                "abstain": False,
            },
        )

    def test_null_is_a_clean_abstention(self):
        answer = choice_v2.reconstruct_answer(self.case, None)

        self.assertEqual(
            answer,
            {
                "request_id": "q1",
                "anchor_id": "anchor-1",
                "block_id": None,
                "occurrence_id": None,
                "copied_label": None,
                "copied_period_evidence": None,
                "abstain": True,
            },
        )

    def test_unknown_choice_fails_instead_of_being_repaired(self):
        with self.assertRaisesRegex(ValueError, "unknown choice"):
            choice_v2.reconstruct_answer(self.case, 99)


class HiddenKeyPreflightTests(unittest.TestCase):
    def test_gold_must_match_exactly_one_source_choice(self):
        choices = choice_v2.build_table_choices(
            TABLE_ID, TABLE_META, HTML)
        case = choice_v2.build_model_case(
            "case-1", request(), choices)
        answers = {
            "q1": {
                "expected_request_id": "q1",
                "expected_anchor_id": "anchor-1",
                "expected_block_id": "example.htm#t0-r05",
                "expected_occurrence": "example.htm#t0-r05-o2",
                "expected_copied_label": "Natural Gas",
                "expected_period_evidence_array":
                    ["Three Months Ended", "2024"],
                "cell_text": "278",
            },
        }

        summary = choice_v2.validate_gold_coverage([case], answers)

        self.assertEqual(summary, {
            "cases": 1,
            "gold_choices_found_exactly_once": 1,
        })


class OneCallTests(unittest.TestCase):
    class FakeClient:
        MODEL = "fake-model"

        def __init__(self, raw):
            self.raw = raw
            self.calls = []

        def generate(self, prompt, system=None, **kwargs):
            self.calls.append((prompt, system, kwargs))
            return self.raw, {
                "done_reason": "stop",
                "truncated_input": False,
                "truncated_output": False,
            }

    def test_completed_answer_is_used_once_without_retry_or_repair(self):
        choices = choice_v2.build_table_choices(
            TABLE_ID, TABLE_META, HTML)
        case = choice_v2.build_model_case(
            "case-1", request(), choices)
        client = self.FakeClient(json.dumps({"choice": 4}))

        result = choice_v2.run_one(case, client=client)

        self.assertEqual(len(client.calls), 1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["choice"], 4)
        kwargs = client.calls[0][2]
        self.assertEqual(kwargs["retries"], 0)
        self.assertFalse(kwargs["think"])
        self.assertEqual(kwargs["temperature"], 0.0)
        self.assertEqual(kwargs["format"], case["schema"])

    def test_extra_output_field_is_invalid_not_repaired(self):
        choices = choice_v2.build_table_choices(
            TABLE_ID, TABLE_META, HTML)
        case = choice_v2.build_model_case(
            "case-1", request(), choices)
        client = self.FakeClient(
            json.dumps({"choice": 4, "explanation": "because"}))

        result = choice_v2.run_one(case, client=client)

        self.assertEqual(len(client.calls), 1)
        self.assertFalse(result["ok"])
        self.assertIn("response shape", result["error"])


class ResumeBoundaryTests(unittest.TestCase):
    def test_only_transport_failures_are_pending_again(self):
        cases = [{"id": "q1"}, {"id": "q2"}]
        results = [
            {
                "id": "q1",
                "completed_response": False,
                "ok": False,
            },
            {
                "id": "q2",
                "completed_response": True,
                "ok": False,
            },
        ]

        pending = choice_v2.pending_cases(cases, results)

        self.assertEqual(pending, [{"id": "q1"}])

    def test_duplicate_completed_answers_fail_loud(self):
        cases = [{"id": "q1"}]
        results = [
            {"id": "q1", "completed_response": True},
            {"id": "q1", "completed_response": True},
        ]

        with self.assertRaisesRegex(ValueError, "duplicate completed"):
            choice_v2.pending_cases(cases, results)


if __name__ == "__main__":
    unittest.main()
