#!/usr/bin/env python3
"""Focused tests for the row-only Qwen table screen."""

from __future__ import annotations

import hashlib
import unittest

import row_v3


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


def source_rows() -> list[dict]:
    cells = row_v3.V2.build_table_choices(
        TABLE_ID, TABLE_META, HTML)
    return row_v3.build_row_choices(cells)


class RowMenuTests(unittest.TestCase):
    def test_each_source_row_becomes_exactly_one_model_choice(self):
        rows = source_rows()

        self.assertEqual(len(rows), 2)
        self.assertEqual(
            [(row["choice"], row["section"], row["label"])
             for row in rows],
            [
                (1, "Gas Sales", "Natural Gas"),
                (2, "Gas Revenues", "Natural Gas"),
            ],
        )
        self.assertEqual(
            [cell["value"] for cell in rows[1]["cells"]],
            ["282", "278"],
        )

    def test_non_contiguous_source_occurrences_fail_closed(self):
        cells = row_v3.V2.build_table_choices(
            TABLE_ID, TABLE_META, HTML)
        cells[1] = dict(
            cells[1],
            occurrence_id="example.htm#t0-r03-o3",
        )

        with self.assertRaisesRegex(ValueError, "occurrence order"):
            row_v3.build_row_choices(cells)


class BlindPromptTests(unittest.TestCase):
    def test_prompt_shows_each_row_once_and_no_cell_level_distractions(self):
        case = row_v3.build_model_case(
            "case-1", request(), source_rows())

        self.assertEqual(case["prompt"].count("Natural Gas"), 3)
        self.assertEqual(case["prompt"].count("Gas Sales"), 1)
        self.assertEqual(case["prompt"].count("Gas Revenues"), 1)
        self.assertNotIn("Requested cell", case["prompt"])
        self.assertNotIn("value=", case["prompt"])
        self.assertNotIn("headers=", case["prompt"])
        self.assertNotIn("example.htm", case["prompt"])
        self.assertNotIn("occurrence_id", case["prompt"])
        self.assertEqual(
            case["schema"]["properties"]["choice"]["enum"],
            [None, 1, 2],
        )

    def test_hidden_answers_are_not_an_input_to_case_builder(self):
        self.assertEqual(
            list(row_v3.build_cases_from_calls.__code__.co_varnames[
                :row_v3.build_cases_from_calls.__code__.co_argcount
            ]),
            ["calls", "source_loader"],
        )


class DeterministicOccurrenceTests(unittest.TestCase):
    def setUp(self):
        self.case = row_v3.build_model_case(
            "case-1", request(), source_rows())

    def test_code_applies_requested_occurrence_after_row_selection(self):
        answer = row_v3.reconstruct_answer(self.case, 2)

        self.assertEqual(
            answer,
            {
                "request_id": "q1",
                "anchor_id": "anchor-1",
                "block_id": "example.htm#t0-r05",
                "occurrence_id": "example.htm#t0-r05-o2",
                "copied_label": "Natural Gas",
                "copied_period_evidence":
                    ["Three Months Ended", "2024"],
                "abstain": False,
            },
        )

    def test_mismatched_row_width_abstains_instead_of_guessing(self):
        self.case["choices"][1]["cells"] = (
            self.case["choices"][1]["cells"][:1]
        )

        answer = row_v3.reconstruct_answer(self.case, 2)

        self.assertTrue(answer["abstain"])
        self.assertIsNone(answer["occurrence_id"])

    def test_malformed_occurrence_contract_fails_before_model_use(self):
        bad = request()
        bad["ask"] = dict(
            bad["ask"],
            target="please choose the second value",
        )

        with self.assertRaisesRegex(ValueError, "occurrence target"):
            row_v3.build_model_case("case-1", bad, source_rows())

    def test_null_is_a_clean_abstention(self):
        answer = row_v3.reconstruct_answer(self.case, None)

        self.assertTrue(answer["abstain"])
        self.assertIsNone(answer["block_id"])


class HiddenKeyPreflightTests(unittest.TestCase):
    def test_gold_cell_must_equal_the_code_selected_cell(self):
        case = row_v3.build_model_case(
            "case-1", request(), source_rows())
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

        summary = row_v3.validate_gold_coverage([case], answers)

        self.assertEqual(summary, {
            "cases": 1,
            "gold_rows_found_exactly_once": 1,
            "occurrences_reconstructed_exactly": 1,
        })


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.case = row_v3.build_model_case(
            "case-1", request(), source_rows())
        self.answer = {
            "expected_request_id": "q1",
            "expected_anchor_id": "anchor-1",
            "expected_block_id": "example.htm#t0-r05",
            "expected_occurrence": "example.htm#t0-r05-o2",
            "expected_copied_label": "Natural Gas",
            "expected_period_evidence_array":
                ["Three Months Ended", "2024"],
            "cell_text": "278",
        }

    @staticmethod
    def result(choice: int) -> dict:
        return {
            "id": "q1",
            "ok": True,
            "completed_response": True,
            "choice": choice,
            "error": None,
        }

    def test_score_uses_row_then_deterministic_occurrence(self):
        scored = row_v3.score_records(
            [self.result(2)],
            [self.case],
            {"q1": self.answer},
        )

        self.assertEqual(
            scored["counts"],
            {
                "correct": 1,
                "wrong": 0,
                "abstained": 0,
                "invalid": 0,
                "total": 1,
            },
        )

    def test_duplicate_completed_answers_fail_loud(self):
        with self.assertRaisesRegex(ValueError, "duplicate result"):
            row_v3.score_records(
                [self.result(2), self.result(1)],
                [self.case],
                {"q1": self.answer},
            )


if __name__ == "__main__":
    unittest.main()
