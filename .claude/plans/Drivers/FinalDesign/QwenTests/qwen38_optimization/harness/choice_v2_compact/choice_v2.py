#!/usr/bin/env python3
"""QF-01 choice-v2: Qwen chooses a source cell; code copies the evidence.

This is a development test, not an unseen certification. The production-shaped
path is:

    real HTML -> source-only choices -> Qwen choice/null -> exact reconstruction

The hidden key is used only after source-only cases have been written: first to
prove that every expected cell exists exactly once, and later to score results.

Commands:
    python3 choice_v2.py prepare
    python3 choice_v2.py verify
    python3 choice_v2.py run       # requires separate owner GO
    python3 choice_v2.py score
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
WIP = ROOT / ".claude/plans/Drivers/WIP"
PHASE2 = ROOT / "scripts/driver_seed/relocate_probe/phase2"
SOURCE_CACHE = ROOT / "scripts/driver_seed/relocate_probe/exhibit_html_cache"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PHASE2))

from config import local_llm as L  # noqa: E402
from driver.relocation import inline_html as IH  # noqa: E402
import m1_structure_inventory as INV  # noqa: E402
from m2_native_table_shadow_r3 import (  # noqa: E402
    _context_track,
    _emit_family,
    _numeric_data_cols,
    _row_scope,
)

SOURCE_CALLS = [
    WIP / f"phase6_screen_call_{number}.json" for number in (1, 2, 3)
]
HIDDEN_KEY = WIP / "phase6_screen_answers_HIDDEN.json"
FISCAL_GRADER = WIP / "phase6_screen_grade.py"
FISCAL_VALIDATOR = WIP / "phase6_screen_validate.py"

CASES_PATH = HERE / "cases.jsonl"
MANIFEST_PATH = HERE / "manifest.json"
RESULTS_DIR = HERE / "results"
RAW_RESULTS_PATH = RESULTS_DIR / "raw_results.jsonl"
RUN_RECORD_PATH = RESULTS_DIR / "run_record.json"
SCORE_PATH = RESULTS_DIR / "score.json"

TEST_ID = "QF-01-CHOICE-V2-COMPACT-DEV"
MODEL_NAME = "qwen3.8:27b-mlx"
# num_ctx is configurable at PREPARE time (frozen into the manifest, verified at
# run time). Keep it fixed for a whole run: changing it reloads the model and
# drops the server prefix cache. 16384 comfortably holds the largest dense prompt
# (~6.3k tokens) plus output; larger values cost KV memory and prefill time.
NUM_CTX = int(os.environ.get("QWEN_NUM_CTX", "16384"))
MAX_TOKENS = 512
TIMEOUT_SECONDS = 1800
WORKERS = 1
# Prefix priming (QWEN_PRIME=0 disables): before the first call of each family,
# send the family's shared prompt prefix once (raw) so the server leaves a cache
# snapshot at the branch point. Prompt bytes per case are UNCHANGED; this only
# removes the second cold prefill per table. See config/local_llm.py: prime().
PRIME_PREFIX = os.environ.get("QWEN_PRIME", "1") != "0"

FORBIDDEN_PROMPT_TEXT = (
    "expected_",
    "occurrence_id",
    "block_id",
    "\u27e8",
    "\u27e9",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    return sha256_bytes(Path(path).read_bytes())


def sha256_json(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(raw)


def root_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def load_source_calls() -> list[dict]:
    calls = []
    for path in SOURCE_CALLS:
        call = load_json(path)
        call["_source_name"] = path.name
        calls.append(call)
    return calls


def load_source_bytes(table: dict) -> bytes:
    return (SOURCE_CACHE / table["source_file"]).read_bytes()


def _table_number(table_id: str) -> int:
    match = re.fullmatch(r".+#t(\d+)", table_id)
    if not match:
        raise ValueError(f"malformed table id: {table_id}")
    return int(match.group(1))


def build_table_choices(
    table_id: str,
    table: dict,
    html_bytes: bytes,
) -> list[dict]:
    """Build every numeric data-cell choice from the real table, without gold."""
    actual_sha = sha256_bytes(html_bytes)
    if actual_sha != table.get("source_sha256"):
        raise ValueError(
            f"source hash mismatch for {table.get('source_file')}: "
            f"expected {table.get('source_sha256')}, got {actual_sha}"
        )

    soup = IH._soup(html_bytes.decode("utf-8", "replace"))
    spans = {}
    IH._visible_walk(soup, spans)
    tables = [
        item for item in soup.find_all("table")
        if item.find_parent("table") is None
    ]
    table_number = _table_number(table_id)
    if table_number >= len(tables):
        raise ValueError(
            f"table {table_number} missing from {table.get('source_file')}")

    rows = INV._own_rows(tables[table_number])
    grid = IH._table_grid(rows)
    zone_end = next(
        (index for index, placed in enumerate(grid)
         if INV._data_like(placed)),
        0,
    )
    grid_width = max(
        (end for placed in grid for _cell, _start, end in placed),
        default=0,
    )
    numeric_columns = _numeric_data_cols(grid, zone_end)
    context = _context_track(grid, numeric_columns, grid_width)

    choices = []
    for row_index in range(zone_end, len(grid)):
        if not INV._data_like(grid[row_index]):
            continue
        scope = _row_scope(
            rows, grid, zone_end, grid_width, row_index,
            numeric_columns, context,
        )
        family = _emit_family(
            rows, grid, zone_end, grid_width, row_index,
            table["source_file"], table_number, spans, context,
        )
        block_id = f"{table_id}-r{row_index:02d}"
        caption = (
            "" if scope["caption"] == scope["section"]
            else scope["caption"]
        )
        for occurrence_number, cell in enumerate(family["cells"], 1):
            choices.append({
                "choice": len(choices) + 1,
                "block_id": block_id,
                "occurrence_id":
                    f"{block_id}-o{occurrence_number}",
                "label": scope["row_label"],
                "section": scope["section"],
                "caption": caption,
                "value": cell["cell_text"],
                "period_headers":
                    list(cell["aligned_headers_verbatim"]),
            })

    if not choices:
        raise ValueError(f"no source choices found for {table_id}")
    return choices


def response_schema(choices: list[dict]) -> dict:
    allowed = [None, *[item["choice"] for item in choices]]
    return {
        "type": "object",
        "properties": {
            "choice": {
                "type": ["integer", "null"],
                "enum": allowed,
            },
        },
        "required": ["choice"],
        "additionalProperties": False,
    }


SYSTEM_MESSAGE = (
    "You are a JSON API. You emit exactly one JSON object and nothing "
    "else. Never write analysis, reasoning, explanation, or markdown. "
    "Your entire response must parse as JSON."
)
# Required on the MLX engine: Ollama's MLX path ignores the `format`
# JSON-schema (no grammar enforcement), so without a hard role
# instruction the model emits chain-of-thought prose on ~30% of cases.
# Verified 2026-08-15: SCR-05-q1 / SCR-06-q2 prose -> valid JSON.

def _strip_fences(text: str) -> str:
    """MLX has no grammar enforcement and sometimes wraps JSON in a
    markdown fence. Mirrors config/local_llm.py _strip_fences: parsing
    only, the answer content is untouched."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split(chr(10), 1)[-1] if chr(10) in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _prompt(request: dict, choices: list[dict]) -> str:
    lines = [
        "Choose the exact source-table cell for this known Driver evidence.",
        "",
        "How to choose:",
        "- Find the row and section whose meaning matches the known Driver.",
        "- Within that row, occurrence numbers run left-to-right across the "
        "numeric choices.",
        "- Choose null if the requested cell is absent or cannot be proven.",
        "- Never calculate, guess, or explain.",
        "- Return JSON only, no prose and no code fence.",
        "",
        "Source-derived choices. Every choice line is "
        "choice|occurrence|value|headers:",
    ]

    prior_block = None
    row_number = 0
    occurrence_in_row = 0
    for item in choices:
        if item["block_id"] != prior_block:
            prior_block = item["block_id"]
            row_number += 1
            occurrence_in_row = 0
            # DENSE ENCODING (2026-08-16): the choice lines were 78% of the
            # whole prompt (16,745 of 21,472 chars on SCR-14-q1). Prefill is
            # LINEAR in tokens, so a pure re-encoding - no information
            # dropped - buys ~2.4x on every COLD call, including brand-new
            # documents that caching cannot help.
            header = f"ROW {row_number}"
            if item["caption"]:
                header += f" caption={json.dumps(item['caption'], ensure_ascii=False)}"
            header += (f" section={json.dumps(item['section'], ensure_ascii=False)}"
                       f" label={json.dumps(item['label'], ensure_ascii=False)}")
            # COMPACT ENCODING (2026-08-16): the per-row `cols:` legend cost
            # 12 tokens x 41 rows (7.6% of the prompt); it is stated once in
            # the instructions instead.
            lines.extend(["", header])
        # OCCURRENCE LABELLING (2026-08-16): the model was asked to COUNT the
        # left-to-right ordinal position within a row and got it wrong on 4/93
        # cases (all WRONG:occurrence). The count is fully deterministic, so
        # emit it instead of making the model do arithmetic. Same principle as
        # row_v3 ("code applies the occurrence; Qwen never retypes").
        occurrence_in_row += 1
        heads = ",".join(str(h) for h in item["period_headers"])
        # COMPACT ENCODING (2026-08-16): the two-space indent tokenised as
        # two separate tokens on every line (10% of the whole prompt).
        lines.append(
            f"{item['choice']}|{occurrence_in_row}|{item['value']}|{heads}"
        )
    # PREFIX-CACHE ORDERING (2026-08-16): the per-call target lines used to sit
    # at char ~144, ahead of the ~17k-char row block that every case in a
    # family shares. That made the shared prefix 0.8% and forced a full
    # re-prefill of the table on every call. Moving them to the END makes the
    # prefix 99.6% identical, so Ollama's KV cache is reused.
    # Measured on SCR-11: prefill 102.1s -> 1.1s / 0.6s on later calls.
    lines.extend([
        "",
        "TARGET FOR THIS CALL:",
        f"Known Driver evidence: {request['ask']['label_wording']}",
        f"Requested cell: {request['ask']['target']}",
        "",
        'Return only JSON in this form: {"choice": <number or null>}',
    ])
    return "\n".join(lines)


def build_model_case(
    case_id: str,
    request: dict,
    choices: list[dict],
) -> dict:
    if not request.get("request_id") or not request.get("anchor_id"):
        raise ValueError("request or anchor id is missing")
    if not isinstance(request.get("ask"), dict):
        raise ValueError("request ask is missing")
    prompt = _prompt(request, choices)
    if any(text in prompt for text in FORBIDDEN_PROMPT_TEXT):
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
        "choices": choices,
        "prompt": prompt,
        "schema": response_schema(choices),
    }


def build_cases_from_calls(calls, source_loader) -> list[dict]:
    """Build blind model cases. This API deliberately cannot receive gold."""
    table_choices = {}
    cases = []
    seen_request_ids = set()

    for call in calls:
        for source_case in call.get("cases", []):
            table_id = source_case.get("table")
            table = call.get("tables", {}).get(table_id)
            if table is None:
                raise ValueError(f"missing table {table_id}")
            if table_id not in table_choices:
                choices = build_table_choices(
                    table_id, table, source_loader(table))
                marked_ids = {
                    occurrence_id
                    for block in table.get("blocks", [])
                    for occurrence_id in re.findall(
                        r"\u27e8([^\u27e9]+)\u27e9", block.get("text", ""))
                }
                untraced = sorted(
                    item["occurrence_id"] for item in choices
                    if item["occurrence_id"] not in marked_ids
                )
                if untraced:
                    raise ValueError(
                        f"{len(untraced)} choices lack source markers in "
                        f"{table_id}")
                table_choices[table_id] = choices

            for request in source_case.get("requests", []):
                request_id = request.get("request_id")
                if not request_id or request_id in seen_request_ids:
                    raise ValueError(
                        f"missing or duplicate request id: {request_id}")
                if request.get("table") != table_id:
                    raise ValueError(
                        f"request {request_id} names a different table")
                seen_request_ids.add(request_id)
                case = build_model_case(
                    source_case["case_id"],
                    request,
                    table_choices[table_id],
                )
                case["source_call"] = call.get("_source_name")
                case["source_sha256"] = table["source_sha256"]
                cases.append(case)
    return cases


def reconstruct_answer(case: dict, choice: int | None) -> dict:
    request = case["request"]
    if choice is None:
        return {
            "request_id": request["request_id"],
            "anchor_id": request["anchor_id"],
            "block_id": None,
            "occurrence_id": None,
            "copied_label": None,
            "copied_period_evidence": None,
            "abstain": True,
        }

    matches = [
        item for item in case["choices"] if item["choice"] == choice
    ]
    if len(matches) != 1:
        raise ValueError(f"unknown choice: {choice}")
    selected = matches[0]
    return {
        "request_id": request["request_id"],
        "anchor_id": request["anchor_id"],
        "block_id": selected["block_id"],
        "occurrence_id": selected["occurrence_id"],
        "copied_label": selected["label"],
        "copied_period_evidence": list(selected["period_headers"]),
        "abstain": False,
    }


def _choice_matches_gold(case: dict, choice: dict, answer: dict) -> bool:
    return (
        case["request"]["request_id"] == answer["expected_request_id"]
        and case["request"]["anchor_id"] == answer["expected_anchor_id"]
        and choice["block_id"] == answer["expected_block_id"]
        and choice["occurrence_id"] == answer["expected_occurrence"]
        and choice["label"] == answer["expected_copied_label"]
        and choice["period_headers"]
        == answer["expected_period_evidence_array"]
        and choice["value"] == answer["cell_text"]
    )


def validate_gold_coverage(cases: list[dict], answers: dict) -> dict:
    """Prove gold is present once; return no gold choice IDs."""
    case_ids = {case["id"] for case in cases}
    if case_ids != set(answers) or len(case_ids) != len(cases):
        raise ValueError("case IDs and hidden-answer IDs differ")
    found = 0
    for case in cases:
        matches = [
            item for item in case["choices"]
            if _choice_matches_gold(case, item, answers[case["id"]])
        ]
        if len(matches) != 1:
            raise ValueError(
                f"gold choice for {case['id']} appears {len(matches)} times")
        found += 1
    return {
        "cases": len(cases),
        "gold_choices_found_exactly_once": found,
    }


def ensure_prompt_budget(cases: list[dict], *, num_ctx: int) -> dict:
    if not cases:
        raise ValueError("no cases")
    budget = num_ctx // 2
    byte_counts = [
        len(case["prompt"].encode("utf-8")) for case in cases
    ]
    maximum = max(byte_counts)
    # The original compared raw UTF-8 BYTES against a TOKEN budget, which is
    # ~4x too strict (1 token is roughly 4 bytes of English). That unit error
    # forced num_ctx=65536; with OLLAMA_NUM_PARALLEL=4 that allocates KV for
    # 4 x 65536 tokens and drove resident memory to 35 GB of a 37.4 GiB
    # budget, causing thrashing and 5-minute calls. Convert conservatively
    # at 3 bytes/token instead. Changed 2026-08-15 for model experimentation.
    max_tokens_estimate = (maximum + 2) // 3
    if max_tokens_estimate >= budget:
        raise ValueError(
            f"input budget unsafe: largest prompt is {maximum} UTF-8 bytes "
            f"(~{max_tokens_estimate} tokens) against budget {budget}")
    return {
        "largest_prompt_utf8_bytes": maximum,
        "largest_prompt_token_estimate": max_tokens_estimate,
        "conservative_input_token_budget": budget,
    }


def model_fingerprint() -> dict:
    health = L.health()
    if health.get("error"):
        raise RuntimeError(f"Qwen health failed: {health['error']}")
    host = health["host"]
    with urllib.request.urlopen(f"{host}/api/tags", timeout=10) as response:
        tags = json.loads(response.read().decode("utf-8"))
    matches = [
        model for model in tags.get("models", [])
        if model.get("name") == L.MODEL
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one model named {L.MODEL}, found {len(matches)}")
    model = matches[0]
    details = model.get("details", {})
    return {
        "name": model.get("name"),
        "digest": model.get("digest"),
        "size_bytes": model.get("size"),
        "format": details.get("format"),
        "family": details.get("family"),
        "parameter_size": details.get("parameter_size"),
        "quantization_level": details.get("quantization_level"),
        "runtime_version": health.get("version"),
        "resident": L.MODEL in (health.get("loaded") or []),
    }


def _source_html_paths(calls: list[dict]) -> list[Path]:
    names = {
        table["source_file"]
        for call in calls for table in call.get("tables", {}).values()
    }
    return [SOURCE_CACHE / name for name in sorted(names)]


def frozen_files(calls: list[dict]) -> dict[str, str]:
    paths = [
        *SOURCE_CALLS,
        HIDDEN_KEY,
        FISCAL_GRADER,
        FISCAL_VALIDATOR,
        ROOT / "config/local_llm.py",
        ROOT / "driver/relocation/inline_html.py",
        PHASE2 / "m1_structure_inventory.py",
        PHASE2 / "m1_transcript_census.py",
        PHASE2 / "m2_native_table_shadow_r3.py",
        Path(__file__).resolve(),
        HERE / "test_choice_v2.py",
        CASES_PATH,
        *_source_html_paths(calls),
    ]
    return {root_relative(path): sha256_file(path) for path in paths}


def verify_frozen_hashes(hashes: dict[str, str]) -> None:
    for name, expected in hashes.items():
        path = ROOT / name
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"hash mismatch for {name}: expected {expected}, got {actual}")


def prepare() -> dict:
    if CASES_PATH.exists() or MANIFEST_PATH.exists():
        raise RuntimeError("prepared files already exist; refusing to replace")
    if RAW_RESULTS_PATH.exists() or SCORE_PATH.exists():
        raise RuntimeError("used results already exist; refusing to prepare")

    calls = load_source_calls()
    cases = build_cases_from_calls(calls, load_source_bytes)
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

    budget = ensure_prompt_budget(cases, num_ctx=NUM_CTX)
    write_jsonl_atomic(CASES_PATH, cases)
    cases_sha_before_key = sha256_file(CASES_PATH)

    # The key is opened only after the source-only case bytes are fixed.
    answers = load_json(HIDDEN_KEY)["answers"]
    gold_preflight = validate_gold_coverage(cases, answers)
    if sha256_file(CASES_PATH) != cases_sha_before_key:
        raise RuntimeError("case bytes changed during hidden-key preflight")

    manifest = {
        "test_id": TEST_ID,
        "purpose": (
            "Development test: Qwen chooses one clean source-derived cell "
            "or abstains; code reconstructs exact evidence"
        ),
        "prepared_at_utc": utc_now(),
        "authorization": (
            "Owner authorized TDD preparation, but not model calls, "
            "on 2026-07-24"
        ),
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
            "num_ctx": NUM_CTX,
            "max_tokens": MAX_TOKENS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "workers": WORKERS,
            "completed_answer_retries": 0,
            "system_message": SYSTEM_MESSAGE,
        },
        "interface": {
            "model_output": '{"choice": integer_or_null}',
            "qwen_copies_ids_labels_headers_or_values": False,
            "choices_built_from": "real source HTML only",
            "hidden_key_used_to_build_choices": False,
            "semantic_repair_after_choice": False,
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
            "93/93 would prove this production-replicable interface on these "
            "93 development cases only; fresh unseen cases remain required"
        ),
    }
    write_json_atomic(MANIFEST_PATH, manifest)
    return manifest


def verify_manifest(*, check_model: bool = True) -> dict:
    manifest = load_json(MANIFEST_PATH)
    if manifest.get("test_id") != TEST_ID:
        raise ValueError("wrong test manifest")
    verify_frozen_hashes(manifest["frozen_files"])
    cases = load_jsonl(CASES_PATH)
    if len(cases) != 93 or len({case["id"] for case in cases}) != 93:
        raise ValueError("frozen case count or IDs changed")
    if sha256_file(CASES_PATH) != (
        manifest["cases_sha256_before_hidden_key_opened"]
    ):
        raise ValueError("case bytes differ from the pre-key freeze")
    ensure_prompt_budget(cases, num_ctx=NUM_CTX)
    expected_settings = {
        "reasoning": False,
        "temperature": 0.0,
        "num_ctx": NUM_CTX,
        "max_tokens": MAX_TOKENS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "workers": WORKERS,
        "completed_answer_retries": 0,
        "system_message": SYSTEM_MESSAGE,
    }
    if manifest["settings"] != expected_settings:
        raise ValueError("runner settings changed")
    if L.MODEL != MODEL_NAME:
        raise ValueError(f"model changed from {MODEL_NAME} to {L.MODEL}")
    if check_model and model_fingerprint() != manifest["model"]:
        raise ValueError("live model fingerprint changed")
    return manifest


def _valid_choice_output(output, case: dict) -> bool:
    if not isinstance(output, dict) or set(output) != {"choice"}:
        return False
    choice = output["choice"]
    if choice is None:
        return True
    if isinstance(choice, bool) or not isinstance(choice, int):
        return False
    return any(item["choice"] == choice for item in case["choices"])


def run_one(case: dict, *, client=L) -> dict:
    """Make one stateless call; never retry or repair a completed answer."""
    started = time.monotonic()
    try:
        raw, stats = client.generate(
            case["prompt"],
            system=SYSTEM_MESSAGE,
            format=case["schema"],
            think=False,
            temperature=0.0,
            num_ctx=NUM_CTX,
            max_tokens=MAX_TOKENS,
            timeout=TIMEOUT_SECONDS,
            retries=0,
            allow_truncation=False,
            with_stats=True,
        )
    except Exception as error:
        return {
            "id": case["id"],
            "ok": False,
            "completed_response": False,
            "raw_output": None,
            "choice": None,
            "error": f"{type(error).__name__}: {error}",
            "stats": {"wall_s": round(time.monotonic() - started, 3)},
        }

    stats = dict(stats)
    stats["wall_s"] = round(time.monotonic() - started, 3)
    stats["model"] = getattr(client, "MODEL", MODEL_NAME)
    if stats.get("truncated_input") or stats.get("truncated_output"):
        return {
            "id": case["id"],
            "ok": False,
            "completed_response": True,
            "raw_output": raw,
            "choice": None,
            "error": "TruncatedResponse: input or output was cut",
            "stats": stats,
        }
    try:
        output = json.loads(_strip_fences(raw))
    except Exception as error:
        return {
            "id": case["id"],
            "ok": False,
            "completed_response": True,
            "raw_output": raw,
            "choice": None,
            "error": f"{type(error).__name__}: {error}",
            "stats": stats,
        }
    if not _valid_choice_output(output, case):
        return {
            "id": case["id"],
            "ok": False,
            "completed_response": True,
            "raw_output": raw,
            "choice": None,
            "error": "InvalidResponse: response shape or choice is invalid",
            "stats": stats,
        }
    return {
        "id": case["id"],
        "ok": True,
        "completed_response": True,
        "raw_output": raw,
        "choice": output["choice"],
        "error": None,
        "stats": stats,
    }


def pending_cases(cases: list[dict], results: list[dict]) -> list[dict]:
    """Resume transport failures only; any completed answer is permanently final."""
    known_ids = {case["id"] for case in cases}
    extra_ids = {
        result.get("id") for result in results
        if result.get("id") not in known_ids
    }
    if extra_ids:
        raise ValueError(f"unknown result ids: {sorted(extra_ids)}")
    completed_counts = {}
    for result in results:
        if result.get("completed_response"):
            result_id = result.get("id")
            completed_counts[result_id] = (
                completed_counts.get(result_id, 0) + 1
            )
    duplicates = sorted(
        result_id for result_id, count in completed_counts.items()
        if count > 1
    )
    if duplicates:
        raise ValueError(
            f"duplicate completed answers: {duplicates}")
    return [
        case for case in cases if case["id"] not in completed_counts
    ]


def _family_of(case: dict) -> str:
    """SCR-11-q3 -> SCR-11: all cases of a family share one source table."""
    return case["id"].rsplit("-", 1)[0]


def _prime_family(family: str, prompts: list[str]) -> dict:
    """Prime the server prefix cache with the family's shared prompt prefix.
    Never fails the run: priming is a pure cache warm-up (its output is
    discarded and no case prompt changes)."""
    started = time.monotonic()
    entry = {"family": family, "cases": len(prompts)}
    try:
        stats = L.prime_for(prompts, SYSTEM_MESSAGE, num_ctx=NUM_CTX,
                            timeout=TIMEOUT_SECONDS)
        entry["stats"] = stats
    except Exception as error:  # noqa: BLE001
        entry["error"] = f"{type(error).__name__}: {error}"
    entry["wall_s"] = round(time.monotonic() - started, 3)
    print(f"[prime] {family} {entry.get('stats') or entry.get('error')} "
          f"{entry['wall_s']}s", flush=True)
    return entry


def run() -> dict:
    manifest = verify_manifest(check_model=True)
    if RUN_RECORD_PATH.exists():
        raise RuntimeError("completed run record exists; refusing to answer twice")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_jsonl(CASES_PATH)
    prior_results = (
        load_jsonl(RAW_RESULTS_PATH) if RAW_RESULTS_PATH.exists() else []
    )
    pending = pending_cases(cases, prior_results)
    started_utc = utc_now()
    started = time.monotonic()
    new_results = []

    families = {}
    for case in cases:
        families.setdefault(_family_of(case), []).append(case["prompt"])
    prime_log = []
    last_family = None

    mode = "a" if RAW_RESULTS_PATH.exists() else "x"
    with RAW_RESULTS_PATH.open(mode, encoding="utf-8") as handle:
        for number, case in enumerate(pending, 1):
            family = _family_of(case)
            if PRIME_PREFIX and family != last_family:
                prime_log.append(_prime_family(family, families[family]))
            last_family = family
            result = run_one(case)
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
    if pending_cases(cases, results):
        raise RuntimeError("run ended with unanswered cases")

    record = {
        "test_id": TEST_ID,
        "started_at_utc": started_utc,
        "finished_at_utc": utc_now(),
        "wall_seconds": round(time.monotonic() - started, 3),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "raw_results_sha256": sha256_file(RAW_RESULTS_PATH),
        "case_count": len(cases),
        "completed_responses": sum(
            bool(item["completed_response"]) for item in results),
        "transport_failures": sum(
            not bool(item["completed_response"]) for item in results),
        "model_before": manifest["model"],
        "model_after": model_fingerprint(),
        "prefix_priming": PRIME_PREFIX,
        "prime_calls": prime_log,
        "scored": False,
    }
    if record["model_after"] != record["model_before"]:
        raise RuntimeError("model changed during run")
    write_json_atomic(RUN_RECORD_PATH, record)
    return record


def load_fiscal_grade_one():
    spec = importlib.util.spec_from_file_location(
        "choice_v2_fiscal_grader", FISCAL_GRADER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Fiscal grader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grade_one


def score_records(
    results: list[dict],
    cases: list[dict],
    answers: dict,
) -> dict:
    by_case = {case["id"]: case for case in cases}
    by_result: dict[str, list[dict]] = {}
    for result in results:
        by_result.setdefault(result.get("id"), []).append(result)
    if set(by_case) != set(answers):
        raise ValueError("case and answer IDs differ")
    extra_result_ids = sorted(set(by_result) - set(by_case))
    if extra_result_ids:
        raise ValueError(f"unknown result IDs: {extra_result_ids}")

    grade_one = load_fiscal_grade_one()
    counts = {
        "correct": 0,
        "wrong": 0,
        "abstained": 0,
        "invalid": 0,
        "total": len(cases),
    }
    per_request = {}
    transport_failures = sum(
        not bool(result.get("completed_response")) for result in results
    )
    for request_id in sorted(by_case):
        attempts = by_result.get(request_id, [])
        matches = [
            result for result in attempts
            if result.get("completed_response")
        ]
        if len(matches) != 1:
            category = "invalid"
            detail = "MISSING_RESULT" if not matches else "DUPLICATE_RESULT"
        else:
            result = matches[0]
            if not result.get("ok"):
                category = "invalid"
                detail = result.get("error") or "INVALID_RESULT"
            else:
                choice = result.get("choice")
                try:
                    reconstructed = reconstruct_answer(
                        by_case[request_id], choice)
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

    precision_denominator = counts["correct"] + counts["wrong"]
    precision = (
        counts["correct"] / precision_denominator
        if precision_denominator else None
    )
    recall = counts["correct"] / counts["total"] if counts["total"] else None
    perfect = (
        counts["correct"] == counts["total"]
        and counts["wrong"] == 0
        and counts["abstained"] == 0
        and counts["invalid"] == 0
    )
    return {
        "test_id": TEST_ID,
        "counts": counts,
        "precision": precision,
        "recall": recall,
        "development_gate": (
            "PERFECT_93_OF_93" if perfect else "NOT_PERFECT"
        ),
        "transport_failures_before_completed_answers": transport_failures,
        "production_authorized": False,
        "unseen_certification_required": True,
        "per_request": per_request,
    }


def score() -> dict:
    verify_manifest(check_model=False)
    if SCORE_PATH.exists():
        raise RuntimeError("score exists; refusing to replace")
    cases = load_jsonl(CASES_PATH)
    results = load_jsonl(RAW_RESULTS_PATH)
    answers = load_json(HIDDEN_KEY)["answers"]
    validate_gold_coverage(cases, answers)
    scored = score_records(results, cases, answers)
    scored["raw_results_sha256"] = sha256_file(RAW_RESULTS_PATH)
    scored["manifest_sha256"] = sha256_file(MANIFEST_PATH)
    write_json_atomic(SCORE_PATH, scored)
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
