#!/usr/bin/env python3
"""QF-01 row-only development harness.

Real HTML is parsed by the existing deterministic source parser. Qwen chooses
one source row or abstains. Code then applies the request's explicit
left-to-right occurrence number and copies the exact source evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
V2_DIR = HERE.parent / "choice_v2"
sys.path.insert(0, str(V2_DIR))

import choice_v2 as V2  # noqa: E402


ROOT = V2.ROOT
TEST_ID = "QF-01-ROW-V3-DEV"
CASES_PATH = HERE / "cases.jsonl"
MANIFEST_PATH = HERE / "manifest.json"
RESULTS_DIR = HERE / "results"
RAW_RESULTS_PATH = RESULTS_DIR / "raw_results.jsonl"
RUN_RECORD_PATH = RESULTS_DIR / "run_record.json"
SCORE_PATH = RESULTS_DIR / "score.json"

OCCURRENCE_TARGET = re.compile(
    r"^occurrence #([1-9][0-9]*) of the ([1-9][0-9]*) asked cells "
    r"of that labeled row \(ordinal screen simplification\)$"
)


def parse_occurrence_target(target: str) -> tuple[int, int]:
    match = OCCURRENCE_TARGET.fullmatch(target or "")
    if not match:
        raise ValueError(f"invalid occurrence target: {target!r}")
    number, total = (int(value) for value in match.groups())
    if number > total:
        raise ValueError(
            f"occurrence target {number} exceeds declared row width {total}")
    return number, total


def _order_is_proven(row: dict) -> bool:
    cells = row.get("cells")
    if not isinstance(cells, list) or not cells:
        return False
    return all(
        cell.get("block_id") == row.get("block_id")
        and cell.get("occurrence_id")
        == f"{row['block_id']}-o{number}"
        for number, cell in enumerate(cells, 1)
    )


def build_row_choices(cell_choices: list[dict]) -> list[dict]:
    """Collapse source cells into one choice per source row."""
    rows = []
    by_block = {}
    closed_blocks = set()
    prior_block = None

    for cell in cell_choices:
        block_id = cell.get("block_id")
        if not block_id:
            raise ValueError("source cell has no block id")
        if block_id != prior_block:
            if block_id in closed_blocks:
                raise ValueError(f"source row is not contiguous: {block_id}")
            if prior_block is not None:
                closed_blocks.add(prior_block)
            prior_block = block_id

        row = by_block.get(block_id)
        if row is None:
            row = {
                "choice": len(rows) + 1,
                "block_id": block_id,
                "label": cell["label"],
                "section": cell["section"],
                "caption": cell["caption"],
                "cells": [],
            }
            by_block[block_id] = row
            rows.append(row)
        elif any(
            row[field] != cell[field]
            for field in ("label", "section", "caption")
        ):
            raise ValueError(f"row meaning changed within {block_id}")
        row["cells"].append(dict(cell))

    if not rows:
        raise ValueError("no source rows found")
    for row in rows:
        if not _order_is_proven(row):
            raise ValueError(
                f"source occurrence order is not proven for "
                f"{row['block_id']}")
    return rows


def response_schema(rows: list[dict]) -> dict:
    return {
        "type": "object",
        "properties": {
            "choice": {
                "type": ["integer", "null"],
                "enum": [None, *[row["choice"] for row in rows]],
            },
        },
        "required": ["choice"],
        "additionalProperties": False,
    }


def _prompt(request: dict, rows: list[dict]) -> str:
    lines = [
        "Choose the one source-table row whose complete meaning matches "
        "this known Driver.",
        "",
        f"Known Driver: {request['ask']['label_wording']}",
        "",
        "How to choose:",
        "- Treat caption, section, and row label together as the row's "
        "complete meaning.",
        "- Do not accept a partial meaning that conflicts with any "
        "distinguishing word in the known Driver.",
        "- Choose null unless exactly one row can be proven.",
        "- Never calculate, guess, or explain.",
        "",
        "Source-derived row choices:",
    ]
    for row in rows:
        lines.extend([
            "",
            f"choice {row['choice']}:",
            f"  caption={json.dumps(row['caption'], ensure_ascii=False)}",
            f"  section={json.dumps(row['section'], ensure_ascii=False)}",
            f"  label={json.dumps(row['label'], ensure_ascii=False)}",
        ])
    lines.extend([
        "",
        'Return only JSON in this form: {"choice": <number or null>}',
    ])
    return "\n".join(lines)


def build_model_case(
    case_id: str,
    request: dict,
    rows: list[dict],
) -> dict:
    if not request.get("request_id") or not request.get("anchor_id"):
        raise ValueError("request or anchor id is missing")
    if not isinstance(request.get("ask"), dict):
        raise ValueError("request ask is missing")
    parse_occurrence_target(request["ask"].get("target", ""))
    prompt = _prompt(request, rows)
    if any(text in prompt for text in V2.FORBIDDEN_PROMPT_TEXT):
        raise ValueError("source ID or hidden-answer marker leaked into prompt")
    return {
        "id": request["request_id"],
        "case_id": case_id,
        "request": {
            "request_id": request["request_id"],
            "anchor_id": request["anchor_id"],
            "table": request["table"],
            "ask": request["ask"],
        },
        "choices": rows,
        "prompt": prompt,
        "schema": response_schema(rows),
    }


def build_cases_from_calls(calls, source_loader) -> list[dict]:
    """Build blind row cases. This API deliberately cannot receive gold."""
    cell_cases = V2.build_cases_from_calls(calls, source_loader)
    cases = []
    for cell_case in cell_cases:
        case = build_model_case(
            cell_case["case_id"],
            cell_case["request"],
            build_row_choices(cell_case["choices"]),
        )
        case["source_call"] = cell_case.get("source_call")
        case["source_sha256"] = cell_case.get("source_sha256")
        cases.append(case)
    return cases


def _abstention(request: dict) -> dict:
    return {
        "request_id": request["request_id"],
        "anchor_id": request["anchor_id"],
        "block_id": None,
        "occurrence_id": None,
        "copied_label": None,
        "copied_period_evidence": None,
        "abstain": True,
    }


def reconstruct_answer(case: dict, choice: int | None) -> dict:
    """Apply the explicit occurrence only after Qwen selects a source row."""
    request = case["request"]
    if choice is None:
        return _abstention(request)

    matches = [
        row for row in case["choices"] if row["choice"] == choice
    ]
    if len(matches) != 1:
        raise ValueError(f"unknown choice: {choice}")
    row = matches[0]
    number, declared_total = parse_occurrence_target(
        request["ask"]["target"])
    if (
        not _order_is_proven(row)
        or len(row["cells"]) != declared_total
        or number > len(row["cells"])
    ):
        return _abstention(request)

    selected = row["cells"][number - 1]
    return {
        "request_id": request["request_id"],
        "anchor_id": request["anchor_id"],
        "block_id": selected["block_id"],
        "occurrence_id": selected["occurrence_id"],
        "copied_label": selected["label"],
        "copied_period_evidence": list(selected["period_headers"]),
        "abstain": False,
    }


def _answer_fields_match(reconstructed: dict, answer: dict) -> bool:
    return (
        reconstructed["request_id"] == answer["expected_request_id"]
        and reconstructed["anchor_id"] == answer["expected_anchor_id"]
        and reconstructed["block_id"] == answer["expected_block_id"]
        and reconstructed["occurrence_id"] == answer["expected_occurrence"]
        and reconstructed["copied_label"]
        == answer["expected_copied_label"]
        and reconstructed["copied_period_evidence"]
        == answer["expected_period_evidence_array"]
        and reconstructed["abstain"] is False
    )


def validate_gold_coverage(cases: list[dict], answers: dict) -> dict:
    """Prove each gold cell is the declared occurrence of one source row."""
    case_ids = {case["id"] for case in cases}
    if case_ids != set(answers) or len(case_ids) != len(cases):
        raise ValueError("case IDs and hidden-answer IDs differ")

    gold_rows = 0
    reconstructed = 0
    for case in cases:
        answer = answers[case["id"]]
        matches = [
            row
            for row in case["choices"]
            if any(
                V2._choice_matches_gold(case, cell, answer)
                for cell in row["cells"]
            )
        ]
        if len(matches) != 1:
            raise ValueError(
                f"gold row for {case['id']} appears {len(matches)} times")
        gold_rows += 1
        result = reconstruct_answer(case, matches[0]["choice"])
        if not _answer_fields_match(result, answer):
            raise ValueError(
                f"declared occurrence does not reconstruct gold for "
                f"{case['id']}")
        reconstructed += 1
    return {
        "cases": len(cases),
        "gold_rows_found_exactly_once": gold_rows,
        "occurrences_reconstructed_exactly": reconstructed,
    }


def model_fingerprint() -> dict:
    """Use stable identity fields; model residency is only live status."""
    fingerprint = dict(V2.model_fingerprint())
    fingerprint.pop("resident", None)
    return fingerprint


def _source_html_paths(calls: list[dict]) -> list[Path]:
    return V2._source_html_paths(calls)


def frozen_files(calls: list[dict]) -> dict[str, str]:
    paths = [
        *V2.SOURCE_CALLS,
        V2.HIDDEN_KEY,
        V2.FISCAL_GRADER,
        ROOT / "config/local_llm.py",
        ROOT / "driver/relocation/inline_html.py",
        V2.PHASE2 / "m1_structure_inventory.py",
        V2.PHASE2 / "m1_transcript_census.py",
        V2.PHASE2 / "m2_native_table_shadow_r3.py",
        V2_DIR / "choice_v2.py",
        Path(__file__).resolve(),
        HERE / "test_row_v3.py",
        CASES_PATH,
        *_source_html_paths(calls),
    ]
    return {
        V2.root_relative(path): V2.sha256_file(path)
        for path in paths
    }


def prepare() -> dict:
    if CASES_PATH.exists() or MANIFEST_PATH.exists():
        raise RuntimeError("prepared files already exist; refusing to replace")
    if RAW_RESULTS_PATH.exists() or SCORE_PATH.exists():
        raise RuntimeError("used results already exist; refusing to prepare")

    calls = V2.load_source_calls()
    cases = build_cases_from_calls(calls, V2.load_source_bytes)
    if len(cases) != 93 or len({case["id"] for case in cases}) != 93:
        raise ValueError("expected 93 unique source-only cases")

    table_ids = {
        source_case["table"]
        for call in calls for source_case in call["cases"]
    }
    source_files = {
        table["source_file"]
        for call in calls for table in call["tables"].values()
    }
    if len(table_ids) != 8 or len(source_files) != 7:
        raise ValueError("expected 8 tables from 7 filings")

    budget = V2.ensure_prompt_budget(cases, num_ctx=V2.NUM_CTX)
    V2.write_jsonl_atomic(CASES_PATH, cases)
    cases_sha_before_key = V2.sha256_file(CASES_PATH)

    answers = V2.load_json(V2.HIDDEN_KEY)["answers"]
    gold_preflight = validate_gold_coverage(cases, answers)
    if V2.sha256_file(CASES_PATH) != cases_sha_before_key:
        raise RuntimeError("case bytes changed during hidden-key preflight")

    manifest = {
        "test_id": TEST_ID,
        "purpose": (
            "Development test: Qwen chooses one source-derived row or "
            "abstains; code applies the explicit occurrence and copies "
            "exact evidence"
        ),
        "prepared_at_utc": V2.utc_now(),
        "scope": {
            "development_cases": len(cases),
            "independent_tables": len(table_ids),
            "filings": len(source_files),
            "model_calls": len(cases),
            "requests_per_call": 1,
            "unseen_certification": False,
        },
        "model": model_fingerprint(),
        "settings": {
            "reasoning": False,
            "temperature": 0.0,
            "num_ctx": V2.NUM_CTX,
            "max_tokens": V2.MAX_TOKENS,
            "timeout_seconds": V2.TIMEOUT_SECONDS,
            "workers": V2.WORKERS,
            "completed_answer_retries": 0,
            "system_message": None,
        },
        "interface": {
            "model_output": '{"choice": row_number_or_null}',
            "qwen_selects_occurrence": False,
            "qwen_copies_ids_labels_headers_or_values": False,
            "row_choices_built_from": "real source HTML only",
            "occurrence_source": "explicit request contract",
            "occurrence_applied_by": "deterministic code after row choice",
            "unproven_or_missing_occurrence": "abstain",
            "hidden_key_used_to_build_choices": False,
            "semantic_repair_after_row_choice": False,
            "production_replicable": True,
        },
        "prompt_budget": budget,
        "cases_sha256_before_hidden_key_opened": cases_sha_before_key,
        "gold_preflight": gold_preflight,
        "frozen_files": frozen_files(calls),
        "pass_gate": {
            "correct": 93,
            "wrong": 0,
            "abstained": 0,
            "invalid": 0,
        },
        "interpretation": (
            "This opened set can compare development interfaces only; fresh "
            "unseen cases remain required for certification"
        ),
    }
    V2.write_json_atomic(MANIFEST_PATH, manifest)
    return manifest


def verify_manifest(*, check_model: bool = True) -> dict:
    manifest = V2.load_json(MANIFEST_PATH)
    if manifest.get("test_id") != TEST_ID:
        raise ValueError("wrong test manifest")
    V2.verify_frozen_hashes(manifest["frozen_files"])
    cases = V2.load_jsonl(CASES_PATH)
    if len(cases) != 93 or len({case["id"] for case in cases}) != 93:
        raise ValueError("frozen case count or IDs changed")
    if V2.sha256_file(CASES_PATH) != (
        manifest["cases_sha256_before_hidden_key_opened"]
    ):
        raise ValueError("case bytes differ from the pre-key freeze")
    V2.ensure_prompt_budget(cases, num_ctx=V2.NUM_CTX)
    if V2.L.MODEL != V2.MODEL_NAME:
        raise ValueError(
            f"model changed from {V2.MODEL_NAME} to {V2.L.MODEL}")
    if check_model and model_fingerprint() != manifest["model"]:
        raise ValueError("live model fingerprint changed")
    return manifest


def run() -> dict:
    manifest = verify_manifest(check_model=True)
    if RUN_RECORD_PATH.exists():
        raise RuntimeError("completed run record exists; refusing to answer twice")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = V2.load_jsonl(CASES_PATH)
    prior_results = (
        V2.load_jsonl(RAW_RESULTS_PATH)
        if RAW_RESULTS_PATH.exists() else []
    )
    pending = V2.pending_cases(cases, prior_results)
    started_utc = V2.utc_now()
    started = time.monotonic()
    new_results = []

    mode = "a" if RAW_RESULTS_PATH.exists() else "x"
    with RAW_RESULTS_PATH.open(mode, encoding="utf-8") as handle:
        for number, case in enumerate(pending, 1):
            result = V2.run_one(case)
            new_results.append(result)
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            handle.flush()
            print(
                f"[{number}/{len(pending)}] {case['id']} "
                f"answer={result['completed_response']} "
                f"ok={result['ok']} "
                f"{result['stats'].get('wall_s', '?')}s",
                flush=True,
            )
            if not result["completed_response"]:
                raise RuntimeError(
                    "transport failed before an answer; rerun the same command "
                    "to resume. Completed answers will not be called again.")

    results = [*prior_results, *new_results]
    if V2.pending_cases(cases, results):
        raise RuntimeError("run ended with unanswered cases")
    record = {
        "test_id": TEST_ID,
        "started_at_utc": started_utc,
        "finished_at_utc": V2.utc_now(),
        "wall_seconds": round(time.monotonic() - started, 3),
        "manifest_sha256": V2.sha256_file(MANIFEST_PATH),
        "raw_results_sha256": V2.sha256_file(RAW_RESULTS_PATH),
        "case_count": len(cases),
        "completed_responses": sum(
            bool(item["completed_response"]) for item in results),
        "transport_failures": sum(
            not bool(item["completed_response"]) for item in results),
        "model_before": manifest["model"],
        "model_after": model_fingerprint(),
        "scored": False,
    }
    if record["model_after"] != record["model_before"]:
        raise RuntimeError("model changed during run")
    V2.write_json_atomic(RUN_RECORD_PATH, record)
    return record


def score_records(
    results: list[dict],
    cases: list[dict],
    answers: dict,
) -> dict:
    by_case = {case["id"]: case for case in cases}
    by_result = {}
    for result in results:
        result_id = result.get("id")
        if result_id in by_result:
            raise ValueError(f"duplicate result: {result_id}")
        by_result[result_id] = result
    if set(by_case) != set(answers) or set(by_case) != set(by_result):
        raise ValueError("case, result, and answer IDs differ")

    grade_one = V2.load_fiscal_grade_one()
    counts = {
        "correct": 0,
        "wrong": 0,
        "abstained": 0,
        "invalid": 0,
        "total": len(cases),
    }
    per_request = {}
    for request_id in sorted(by_case):
        result = by_result[request_id]
        if not result.get("completed_response") or not result.get("ok"):
            category = "invalid"
            detail = result.get("error") or "INVALID_RESULT"
        else:
            try:
                reconstructed = reconstruct_answer(
                    by_case[request_id], result.get("choice"))
            except ValueError as error:
                category = "invalid"
                detail = str(error)
            else:
                detail = grade_one(
                    request_id, reconstructed, answers)
                if detail == "CORRECT":
                    category = "correct"
                elif detail == "abstain":
                    category = "abstained"
                else:
                    category = "wrong"
        counts[category] += 1
        per_request[request_id] = {
            "category": category,
            "detail": detail,
        }

    accepts = counts["correct"] + counts["wrong"]
    precision = counts["correct"] / accepts if accepts else None
    recall = counts["correct"] / counts["total"] if counts["total"] else None
    perfect = counts == {
        "correct": len(cases),
        "wrong": 0,
        "abstained": 0,
        "invalid": 0,
        "total": len(cases),
    }
    return {
        "test_id": TEST_ID,
        "counts": counts,
        "precision": precision,
        "recall": recall,
        "development_gate": (
            "PERFECT_93_OF_93" if perfect else "NOT_PERFECT"
        ),
        "production_authorized": False,
        "unseen_certification_required": True,
        "per_request": per_request,
    }


def score() -> dict:
    verify_manifest(check_model=False)
    if SCORE_PATH.exists():
        raise RuntimeError("score exists; refusing to replace")
    cases = V2.load_jsonl(CASES_PATH)
    results = V2.load_jsonl(RAW_RESULTS_PATH)
    answers = V2.load_json(V2.HIDDEN_KEY)["answers"]
    validate_gold_coverage(cases, answers)
    scored = score_records(results, cases, answers)
    scored["raw_results_sha256"] = V2.sha256_file(RAW_RESULTS_PATH)
    scored["manifest_sha256"] = V2.sha256_file(MANIFEST_PATH)
    V2.write_json_atomic(SCORE_PATH, scored)
    return scored


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("prepare", "verify", "run", "score"))
    args = parser.parse_args()
    if args.command == "prepare":
        output = prepare()
    elif args.command == "verify":
        output = verify_manifest(check_model=True)
    elif args.command == "run":
        output = run()
    else:
        output = score()
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
