#!/usr/bin/env python3
"""QF-01: one-request-at-a-time local-Qwen 8-K table evidence screen.

This file owns only the Qwen-specific evaluation wrapper. It reuses the Fiscal
source tables, hidden answers, and mechanical grader without copying or
changing them.

Commands:
    python3 qf01.py prepare   # build blind cases and freeze all hashes/settings
    python3 qf01.py verify    # prove the frozen inputs and live model still match
    python3 qf01.py run       # one completed Qwen answer per request, no retries
    python3 qf01.py score     # open the hidden key only after inference is over

The run command deliberately does not use local_llm.structured(): that helper
may retry a malformed completed answer. This test must count the first completed
answer exactly as produced.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
WIP = ROOT / ".claude/plans/Drivers/WIP"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(WIP))
from config import local_llm as L  # noqa: E402

# ---- R28 ALIGNMENT (owner ruling, Phase6 plan §6) --------------------------
# QF-01 now IS the 5x50 table task: one value-blind anchor + ONE rendered table
# -> {request_id, evidence_ids} or [] to abstain; CODE alone copies + verifies.
# The old per-cell contract (copied_label + period-header arrays, ordinal
# targets) scored 0/93 and is REFUSED. Every command below FIRST passes the
# preflight gate; old results stay untouched in results/ as history.
from truth5x50_schema import TABLE_SOLVE, table_solve_prompt  # noqa: E402
from truth5x50_build import table_fixture  # noqa: E402
from truth5x50_grade import score_table_batch  # noqa: E402
from truth5x50_qf01_preflight import (  # noqa: E402
    MISALIGNED_FIELDS, preflight_gate)

ALIGNED_SPEC = {
    "prompt": table_solve_prompt(),
    "response_contract_keys": list(TABLE_SOLVE),
    "per_case_inputs": ["anchor", "rendered_table"],
}

# R30 AUDITED FIXTURE UNITS — one EXPLICIT entry per anchor family, justified by
# the VISIBLE label text alone (never the hidden key). A blanket 'usd' was
# WRONG: 'Load Factor (Percent)' is not money. Law applied: money -> 'usd'
# (cents included — money base); percent labels -> 'percent'; PHYSICAL
# parentheticals (kmt, mdmt) stay in the NAME per the per-X law and the
# series_unit carries the lawful base 'count'. A family missing here FAILS
# CLOSED — no keyword classifier decides units.
AUDITED_FIXTURE_UNITS = {
    "SCR-01-anchor": "usd",      # Cargo Revenue — money
    "SCR-02-anchor": "usd",      # Passenger Revenue — money
    "SCR-03-anchor": "percent",  # Passenger Load Factor (Percent)
    "SCR-04-anchor": "usd",      # Yield (Cents) — cents = money base
    "SCR-05-anchor": "usd",      # Ag Services & Oilseeds Revenue — money
    "SCR-06-anchor": "usd",      # Carbohydrate Solutions Revenue — money
    "SCR-07-anchor": "usd",      # Nutrition Revenue — money
    "SCR-08-anchor": "usd",      # Ag Services & Oilseeds Revenue — money
    "SCR-09-anchor": "usd",      # Carbohydrate Solutions Revenue — money
    "SCR-10-anchor": "usd",      # Nutrition Revenue — money
    "SCR-11-anchor": "count",    # Alumina Production (kmt) — physical
    "SCR-12-anchor": "count",    # Bauxite Production (mdmt) — physical
    "SCR-13-anchor": "count",    # Alumina Third-Party Shipments (kmt)
    "SCR-14-anchor": "count",    # Bauxite Third-Party Shipments (mdmt)
    "SCR-15-anchor": "usd",      # Ameren Illinois Natural Gas Revenue — money
    "SCR-16-anchor": "usd",      # Ameren Illinois Natural Gas Revenue — money
    "SCR-17-anchor": "count",    # Alumina Production (kmt) — physical
    "SCR-18-anchor": "count",    # Bauxite Production (mdmt) — physical
    "SCR-19-anchor": "count",    # Alumina Third-Party Shipments (kmt)
}


def require_alignment() -> None:
    """THE gate: every QF-01 command refuses to proceed unless this exact
    harness spec passes the preflight (owner ruling: a preflight test must
    refuse QF-01 until the alignment passes)."""
    why = preflight_gate(ALIGNED_SPEC)
    if why:
        raise SystemExit(f"QF-01 PREFLIGHT REFUSED: {why}")

SOURCE_CALLS = [
    WIP / f"phase6_screen_call_{number}.json" for number in (1, 2, 3)
]
HIDDEN_KEY = WIP / "phase6_screen_answers_HIDDEN.json"
FISCAL_GRADER = WIP / "phase6_screen_grade.py"
FISCAL_VALIDATOR = WIP / "phase6_screen_validate.py"
FISCAL_MANIFEST = WIP / "phase6_screen_manifest_v2.json"

CASES_PATH = HERE / "cases.jsonl"
MANIFEST_PATH = HERE / "manifest.json"
RESULTS_DIR = HERE / "results_aligned"   # R28: results/ = the OLD 0/93 run,
# preserved untouched as history; the aligned harness writes here instead.
RAW_RESULTS_PATH = RESULTS_DIR / "raw_results.jsonl"
RUN_RECORD_PATH = RESULTS_DIR / "run_record.json"
SCORE_PATH = RESULTS_DIR / "score.json"

INPUT_MARKER = "\n\nINPUT (exactly one request and its complete table):\n"
FORBIDDEN_MODEL_TEXT = (
    "expected", "truth_", "HIDDEN", "cell_text", "grading_law",
)

NUM_CTX = int(os.environ.get("QWEN_NUM_CTX", "16384"))  # frozen at prepare
MAX_TOKENS = 512
TIMEOUT_SECONDS = 1800   # cold prefill of a 12k-char table can exceed 300 s
WORKERS = 1              # sequential, grouped by table: prefix cache + priming
MODEL_NAME = "qwen3.8:27b-mlx"
# Prefix priming per table (QWEN_PRIME=0 disables) - see config/local_llm.py prime()
PRIME_PREFIX = os.environ.get("QWEN_PRIME", "1") != "0"

# R28: THE aligned contract — the 5x50 table response, nothing else. The old
# per-cell shape (block/occurrence/copied_label/period arrays) is the 0/93
# failure mode and is refused at every layer.
REQUIRED_RESPONSE_KEYS = set(TABLE_SOLVE)          # {request_id, evidence_ids}
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "request_id": {"type": "string"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": sorted(REQUIRED_RESPONSE_KEYS),
    "additionalProperties": False,
}


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
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(temp, path)


def load_source_calls() -> list[dict]:
    calls = []
    for path in SOURCE_CALLS:
        call = load_json(path)
        call["_source_name"] = path.name
        calls.append(call)
    return calls


def build_cases_from_calls(calls: list[dict]) -> list[dict]:
    """R28 ALIGNED builder: the old per-cell ordinal requests are GROUPED into
    per-anchor families (SCR-01-q1..q3 sharing one anchor become ONE aligned
    request), and each aligned case is exactly the 5x50 task — one value-blind
    anchor + ONE rendered [En] table. The instruction is THE 5x50
    table_solve_prompt, never the old screen prompt."""
    if not calls:
        raise ValueError("no source calls")
    instruction = table_solve_prompt()
    fixtures: dict[str, tuple] = {}
    cases, seen = [], set()
    for call in calls:
        for source_case in call.get("cases", []):
            table_id = source_case.get("table")
            table = call.get("tables", {}).get(table_id)
            if table is None:
                raise ValueError(f"missing complete table {table_id}")
            if table_id not in fixtures:
                fname, ti = table_id.rsplit("#t", 1)
                fixtures[table_id] = table_fixture(
                    fname, table["source_sha256"], int(ti))
            _cells, rendered, id_map, _units = fixtures[table_id]
            families: dict[str, dict] = {}
            for request in source_case.get("requests", []):
                if request.get("table") != table_id:
                    raise ValueError(
                        f"request {request['request_id']} names another table")
                fam = families.setdefault(request["anchor_id"], {
                    "labels": set(), "members": []})
                fam["labels"].add(request["ask"]["label_wording"])
                fam["members"].append(request["request_id"])
            for anchor_id, fam in sorted(families.items()):
                if len(fam["labels"]) != 1:
                    raise ValueError(
                        f"{anchor_id}: one family must share ONE label")
                if anchor_id in seen:
                    raise ValueError(f"duplicate aligned request {anchor_id}")
                seen.add(anchor_id)
                label = next(iter(fam["labels"]))
                if anchor_id not in AUDITED_FIXTURE_UNITS:
                    raise ValueError(
                        f"{anchor_id}: no AUDITED fixture unit — refusing to "
                        "guess (add an audited entry, never a classifier)")
                anchor = {"driver": label, "slice": "", "measurement": "",
                          "series_unit": AUDITED_FIXTURE_UNITS[anchor_id],
                          "time_type": "duration",
                          "wording": [label]}   # FIXTURE anchor — value-blind;
                # a diagnostic stand-in, never Core output.
                # PREFIX-CACHE ORDERING (2026-08-16): the table (shared by every
                # anchor on it) goes FIRST and the per-call anchor LAST, so the
                # server KV prefix is reused across the table's calls. Same JSON
                # content, same keys; only the key order changes.
                model_input = {"rendered_table": rendered, "anchor": anchor}
                prompt = (instruction + INPUT_MARKER
                          + json.dumps(model_input, ensure_ascii=False,
                                       indent=2))
                if any(m in prompt for m in FORBIDDEN_MODEL_TEXT):
                    raise ValueError(
                        f"hidden-answer marker leaked into {anchor_id}")
                cases.append({
                    "id": anchor_id,
                    "prompt": prompt,
                    "schema": RESPONSE_SCHEMA,
                    "source_call": call.get("_source_name"),
                    "case_id": source_case["case_id"],
                    "table_id": table_id,
                    "source_sha256": table["source_sha256"],
                    "anchor": anchor,
                    "member_requests": sorted(fam["members"]),
                    "id_map": id_map,
                    "rendered_sha256": sha256_bytes(rendered.encode()),
                })
    return cases


def ensure_prompt_budget(cases: list[dict], *, num_ctx: int) -> dict:
    """Use UTF-8 bytes as a conservative upper bound on tokenizer tokens."""
    if not cases:
        raise ValueError("no cases to check against the input budget")
    budget = num_ctx // 2
    byte_counts = [
        len(case["prompt"].encode("utf-8")) for case in cases
    ]
    maximum = max(byte_counts)
    # The original compared raw UTF-8 BYTES against a TOKEN budget (~3-4x too
    # strict; measured 2026-08-16 with the Qwen tokenizer: the largest aligned
    # prompt is 12,276 bytes = 3,920 tokens). Convert at 3 bytes/token, which is
    # still conservative for these rendered tables (3.13 chars/token measured).
    max_tokens_estimate = (maximum + 2) // 3
    if max_tokens_estimate >= budget:
        raise ValueError(
            f"input budget unsafe: largest prompt is {maximum} UTF-8 bytes "
            f"(~{max_tokens_estimate} tokens) against a {budget}-token budget")
    return {
        "largest_case_utf8_bytes": maximum,
        "largest_case_token_estimate": max_tokens_estimate,
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


def frozen_files(cases_path: Path = CASES_PATH) -> dict[str, str]:
    paths = [
        *SOURCE_CALLS,
        HIDDEN_KEY,
        FISCAL_GRADER,
        FISCAL_VALIDATOR,
        FISCAL_MANIFEST,
        ROOT / "config/local_llm.py",
        Path(__file__).resolve(),
        cases_path,
    ]
    return {root_relative(path): sha256_file(path) for path in paths}


def verify_frozen_hashes(hashes: dict[str, str]) -> None:
    for name, expected in hashes.items():
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / path
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"hash mismatch for {name}: expected {expected}, got {actual}")


def prepare() -> dict:
    if RAW_RESULTS_PATH.exists() or SCORE_PATH.exists():
        raise RuntimeError("results already exist; refusing to replace a used test")
    calls = load_source_calls()
    cases = build_cases_from_calls(calls)
    members = [m for case in cases for m in case["member_requests"]]
    if len(members) != 93 or len(set(members)) != 93:
        raise ValueError(
            f"the aligned families must cover EXACTLY the 93 screen requests "
            f"once each; covered {len(set(members))}")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("aligned request IDs are not unique")

    max_chars = max(len(case["prompt"]) for case in cases)
    budget_check = ensure_prompt_budget(cases, num_ctx=NUM_CTX)
    max_bytes = budget_check["largest_case_utf8_bytes"]

    write_jsonl_atomic(CASES_PATH, cases)
    source_files = {
        table["source_file"]
        for call in calls
        for table in call["tables"].values()
    }
    table_ids = {
        table_id
        for call in calls
        for table_id in call["tables"]
    }
    if len(table_ids) != 8 or len(source_files) != 7:
        raise ValueError(
            "expected 8 independent tables from 7 filings, found "
            f"{len(table_ids)} tables from {len(source_files)} filings")
    manifest = {
        "test_id": "QF-01",
        "purpose": (
            "Diagnostic only: exact 8-K table evidence for a known anchor"
        ),
        "prepared_at_utc": utc_now(),
        "authorization": ("ALIGNED per the owner ruling 2026-07-25 (Phase6 plan S6). The 2026-07-24 run authorization was CONSUMED by the failed old-format run (0/93, history in results/); a NEW model run requires its OWN owner GO."),
        "scope": {
            "answerable_requests": len(cases),
            "independent_tables": len(table_ids),
            "filings": len(source_files),
            "model_calls": len(cases),
            "requests_per_call": 1,
        },
        "model": model_fingerprint(),
        "settings": {
            "reasoning": False,
            "temperature": 0.0,
            "num_ctx": NUM_CTX,
            "conservative_input_token_budget": NUM_CTX // 2,
            "max_tokens": MAX_TOKENS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "workers": WORKERS,
            "completed_answer_retries": 0,
            "system_message": None,
        },
        "prompt": {
            "aligned_instruction_sha256": sha256_bytes(
                table_solve_prompt().encode("utf-8")),   # THE 5x50 prompt —
            # never the old screen prompt (a stale pin his audit would catch)
            "input_marker": INPUT_MARKER,
            "response_schema_sha256": sha256_json(RESPONSE_SCHEMA),
            "largest_case_characters": max_chars,
            "largest_case_utf8_bytes": max_bytes,
            "conservative_input_token_budget":
                budget_check["conservative_input_token_budget"],
        },
        "frozen_files": frozen_files(),
        "blindness": {
            "hidden_key_sent_to_model": False,
            "gold_fields_present_in_cases": False,
            "scoring_starts_only_after_run": True,
        },
        "pass_gate": {
            "correct": len(cases),        # a PERFECT run = every SET call
            "wrong": 0,
            "abstained": 0,
            "invalid": 0,
            "note": ("statistics are SET-CALL based (19); 93 is retained ONLY "
                     "as hidden-cell coverage and 8 as independent tables"),
        },
        "cell_coverage": {"hidden_cells": 93, "independent_tables": 8},
    }
    write_json_atomic(MANIFEST_PATH, manifest)
    return manifest


def verify_manifest() -> dict:
    manifest = load_json(MANIFEST_PATH)
    if manifest.get("test_id") != "QF-01":
        raise ValueError("wrong test manifest")
    verify_frozen_hashes(manifest["frozen_files"])
    settings = manifest["settings"]
    current_settings = {
        "reasoning": False,
        "temperature": 0.0,
        "num_ctx": NUM_CTX,
        "conservative_input_token_budget": NUM_CTX // 2,
        "max_tokens": MAX_TOKENS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "workers": WORKERS,
        "completed_answer_retries": 0,
        "system_message": None,
    }
    if settings != current_settings:
        raise ValueError("frozen settings no longer match the runner")
    if L.MODEL != MODEL_NAME:
        raise ValueError(f"model changed from {MODEL_NAME} to {L.MODEL}")
    current_model = model_fingerprint()
    if current_model != manifest["model"]:
        raise ValueError(
            "live model fingerprint differs from the frozen manifest")
    cases = load_jsonl(CASES_PATH)
    members = [m for case in cases for m in case.get("member_requests", [])]
    if (len({case["id"] for case in cases}) != len(cases)
            or len(members) != 93 or len(set(members)) != 93):
        raise ValueError(
            "frozen case count or IDs changed (aligned law: unique set-request "
            "families covering EXACTLY the 93 screen cells once each)")
    if len(cases) != manifest["scope"]["answerable_requests"]:
        raise ValueError("case count differs from the frozen manifest scope")
    return manifest


def run_one(case: dict, *, client=L) -> dict:
    """Send exactly one inference request and parse exactly one response."""
    started = time.monotonic()
    try:
        raw, stats = client.generate(
            case["prompt"],
            system=None,
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
    except Exception as error:  # no completed answer is available to score
        return {
            "id": case["id"],
            "ok": False,
            "completed_response": False,
            "raw_output": None,
            "output": None,
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
            "output": None,
            "error": "TruncatedResponse: model input or output was cut",
            "stats": stats,
        }
    try:
        output = json.loads(raw)
    except Exception as error:
        return {
            "id": case["id"],
            "ok": False,
            "completed_response": True,
            "raw_output": raw,
            "output": None,
            "error": f"{type(error).__name__}: {error}",
            "stats": stats,
        }
    return {
        "id": case["id"],
        "ok": True,
        "completed_response": True,
        "raw_output": raw,
        "output": output,
        "error": None,
        "stats": stats,
    }


def run() -> dict:
    manifest = verify_manifest()
    if RAW_RESULTS_PATH.exists() or RUN_RECORD_PATH.exists():
        raise RuntimeError(
            "run output already exists; refusing to answer any case twice")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_jsonl(CASES_PATH)
    started = utc_now()
    started_wall = time.monotonic()
    counts = {"completed": 0, "no_response": 0}

    # Sequential, grouped by table, one prime per table (see PRIME_PREFIX).
    ordered = sorted(cases, key=lambda c: (c.get("table_id") or "", c["id"]))
    prime_log = []
    last_table = None

    def _results():
        nonlocal last_table
        for case in ordered:
            table = case.get("table_id")
            if PRIME_PREFIX and table != last_table:
                prompts = [c["prompt"] for c in ordered if c.get("table_id") == table]
                t0 = time.monotonic()
                entry = {"table": table, "cases": len(prompts)}
                try:
                    entry["stats"] = L.prime_for(prompts, None, num_ctx=NUM_CTX,
                                                 timeout=TIMEOUT_SECONDS)
                except Exception as error:  # noqa: BLE001
                    entry["error"] = f"{type(error).__name__}: {error}"
                entry["wall_s"] = round(time.monotonic() - t0, 3)
                print(f"[prime] {table} {entry.get('stats') or entry.get('error')} "
                      f"{entry['wall_s']}s", flush=True)
                prime_log.append(entry)
            last_table = table
            yield run_one(case)

    with RAW_RESULTS_PATH.open("x", encoding="utf-8") as output_file:
        if True:
            for number, result in enumerate(_results(), 1):
                output_file.write(
                    json.dumps(result, ensure_ascii=False) + "\n")
                output_file.flush()
                if result["completed_response"]:
                    counts["completed"] += 1
                else:
                    counts["no_response"] += 1
                stats = result.get("stats", {})
                print(
                    f"[{number}/{len(cases)}] {result['id']} "
                    f"answer={result['completed_response']} ok={result['ok']} "
                    f"{stats.get('wall_s', '?')}s",
                    flush=True,
                )

    record = {
        "test_id": "QF-01",
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "wall_seconds": round(time.monotonic() - started_wall, 3),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "raw_results_sha256": sha256_file(RAW_RESULTS_PATH),
        "case_count": len(cases),
        "counts": counts,
        "model_before": manifest["model"],
        "model_after": model_fingerprint(),
        "prefix_priming": PRIME_PREFIX,
        "prime_calls": prime_log,
        "scored": False,
    }
    if record["model_after"] != record["model_before"]:
        raise RuntimeError("model changed during the run")
    write_json_atomic(RUN_RECORD_PATH, record)
    return record


def load_fiscal_grade_one():
    spec = importlib.util.spec_from_file_location(
        "qf01_fiscal_grader", FISCAL_GRADER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Fiscal grader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grade_one


def valid_response_shape(output) -> bool:
    """R28 ALIGNED shape: ONE object {request_id, evidence_ids}; [] = abstain.
    The old 93-cell per-cell format — or ANY response smuggling a
    model-re-typed evidence field — is refused outright."""
    response = output[0] if (isinstance(output, list)
                             and len(output) == 1) else output
    if not isinstance(response, dict):
        return False
    if any(f in response for f in MISALIGNED_FIELDS):
        return False                           # the 0/93 failure mode
    if set(response) != REQUIRED_RESPONSE_KEYS:
        return False
    if not isinstance(response["request_id"], str):
        return False
    ids = response["evidence_ids"]
    return (isinstance(ids, list)
            and all(isinstance(x, str) for x in ids)
            and len(ids) == len(set(ids)))


def build_aligned_answers(answers: dict, cases: list[dict]) -> dict:
    """R28: the hidden SET-BASED answers. Each of the 93 per-cell hidden
    answers is located in the NEW fixture MECHANICALLY — row index from its old
    block id + EXACT cell text + the period-header array — and grouped into its
    family's evidence-ID set. Exactly ONE match per cell or this FAILS CLOSED;
    nothing is guessed and no judgment is applied."""
    from truth5x50_build import table_parse
    fam_of, by_case = {}, {}
    for case in cases:
        by_case[case["id"]] = case
        for member in case["member_requests"]:
            fam_of[member] = case["id"]
    aligned: dict[str, set] = {}
    for rid, ans in answers.items():
        fam = fam_of.get(rid)
        if fam is None:
            raise ValueError(f"hidden answer {rid} has no aligned family")
        case = by_case[fam]
        fname, ti = case["table_id"].rsplit("#t", 1)
        row = int(ans["expected_block_id"].rsplit("-r", 1)[1].split("-")[0])
        cells, _rows, _units = table_parse(
            fname, case["source_sha256"], int(ti))
        hits = [c for c in cells
                if c["row_index"] == row and c["is_data"]
                and str(c["value_text"]).strip() == str(ans["cell_text"]).strip()
                and all(h in c["aligned_headers"]
                        for h in ans["expected_period_evidence_array"])]
        if len(hits) != 1:
            raise ValueError(
                f"ALIGNMENT FAILURE for {rid}: {len(hits)} cells match the "
                "hidden identity — refusing to guess")
        rev = {addr: en for en, addr in case["id_map"].items()}
        addr = hits[0]["addr"]
        if addr not in rev:
            raise ValueError(f"{rid}: matched cell {addr} carries no [En] id")
        aligned.setdefault(fam, set()).add(rev[addr])
    return {fam: sorted(ids) for fam, ids in aligned.items()}


def score_records(results: list[dict], answers: dict,
                  cases: list[dict]) -> dict:
    """Strictly score every ALIGNED request once against its hidden evidence-ID
    SET (exact set equality via the 5x50 mechanical grader — verify_set re-pulls
    the pinned source and copies the evidence; never repairs model output)."""
    aligned = build_aligned_answers(answers, cases)
    by_case = {case["id"]: case for case in cases}
    by_id: dict[str, list[dict]] = {}
    for result in results:
        by_id.setdefault(result.get("id"), []).append(result)
    expected_ids = set(aligned)
    extra_ids = sorted(rid for rid in by_id if rid not in expected_ids)
    per_request = {}
    counts = {"correct": 0, "wrong": 0, "abstained": 0, "invalid": 0,
              "total": len(expected_ids)}
    for request_id in sorted(expected_ids):
        matches = by_id.get(request_id, [])
        if len(matches) != 1:
            category = "invalid"
            detail = "MISSING_RESULT" if not matches else "DUPLICATE_RESULT"
        else:
            result = matches[0]
            if (not result.get("completed_response") or not result.get("ok")
                    or not valid_response_shape(result.get("output"))):
                category = "invalid"
                detail = result.get("error") or "MALFORMED_OUTPUT"
            else:
                out = result["output"]
                response = out[0] if isinstance(out, list) else out
                case = by_case[request_id]
                fname, ti = case["table_id"].rsplit("#t", 1)
                gcase = {"case_id": request_id, "request_id": request_id,
                         "category": "8k_tables", "file": fname,
                         "file_sha": case["source_sha256"],
                         "table_index": int(ti), "id_map": case["id_map"]}
                from truth5x50_build import table_fixture
                gcase["rendered"] = table_fixture(
                    fname, case["source_sha256"], int(ti))[1]
                expected_addrs = {request_id: sorted(
                    case["id_map"][en] for en in aligned[request_id])}
                verdicts = score_table_batch(
                    [gcase], [dict(response, request_id=request_id)],
                    expected_addrs)
                v = verdicts["per_request"][request_id]["verdict"]
                detail = v
                if v == "correct":
                    category = "correct"
                elif v.startswith("abstain"):
                    category = "abstained"
                elif v.startswith("invalid"):
                    category = "invalid"
                else:
                    category = "wrong"     # WRONG-ACCEPT, recall-miss, safe-reject
        counts[category] += 1
        per_request[request_id] = {"category": category, "detail": detail}
    precision_denominator = counts["correct"] + counts["wrong"]
    precision = (counts["correct"] / precision_denominator
                 if precision_denominator else None)
    recall = counts["correct"] / counts["total"] if counts["total"] else None
    if (not extra_ids and counts["correct"] == counts["total"]
            and not counts["wrong"] and not counts["abstained"]
            and not counts["invalid"]):
        qualification = "QWEN_ONLY_QUALIFIED"
    elif not counts["wrong"] and not extra_ids:
        qualification = "SAFE_FIRST_PASS_ONLY"
    else:
        qualification = "NOT_SAFE_FOR_TASK"
    return {"counts": counts, "evidence_precision": precision,
            "evidence_recall": recall, "qualification": qualification,
            "extra_result_ids": extra_ids, "per_request": per_request}


def score() -> dict:
    manifest = verify_manifest()
    if not RAW_RESULTS_PATH.exists() or not RUN_RECORD_PATH.exists():
        raise RuntimeError("the blind run is not complete")
    if SCORE_PATH.exists():
        raise RuntimeError("score already exists; refusing to score twice")
    run_record = load_json(RUN_RECORD_PATH)
    if sha256_file(RAW_RESULTS_PATH) != run_record["raw_results_sha256"]:
        raise ValueError("raw results changed after the run")
    hidden = load_json(HIDDEN_KEY)
    answers = hidden["answers"]
    results = load_jsonl(RAW_RESULTS_PATH)
    cases = load_jsonl(CASES_PATH)
    summary = score_records(results, answers, cases)
    summary.update({
        "test_id": "QF-01",
        "scored_at_utc": utc_now(),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "raw_results_sha256": sha256_file(RAW_RESULTS_PATH),
        "hidden_key_sha256": sha256_file(HIDDEN_KEY),
        "fiscal_grader_sha256": sha256_file(FISCAL_GRADER),
        "independence": {
            "aligned_set_requests": "one per anchor family",
            "hidden_cells_covered": 93,
            "independent_tables": 8,
            "filings": 7,
        },
        "zero_error_rule_of_three_upper_bound": (
            {
                "set_call_level": 3 / 19,       # THE unit of this test
                # NO 3/93 bound: the 93 cells are COVERAGE, not 93 independent
                # trials (they cluster inside 19 calls / 8 tables), so a
                # rule-of-three at cell level would claim statistical support
                # the data cannot give.
                "independent_table_level": 3 / 8,
            }
            if summary["counts"]["correct"] == summary["counts"]["total"]
            else None
        ),
        "scope_limit": (
            "Screen only: exact table evidence for known anchors; no "
            "production certification or general reader claim"
        ),
        "model": manifest["model"],
    })
    write_json_atomic(SCORE_PATH, summary)
    run_record["scored"] = True
    run_record["score_sha256"] = sha256_file(SCORE_PATH)
    write_json_atomic(RUN_RECORD_PATH, run_record)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("prepare", "verify", "run", "score"))
    args = parser.parse_args()
    require_alignment()      # R28: NO QF-01 command runs unless the preflight
    #                          accepts this harness's exact aligned spec
    if args.command == "prepare":
        value = prepare()
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.command == "verify":
        value = verify_manifest()
        print(
            f"QF-01 frozen inputs and model verified: "
            f"{value['scope']['answerable_requests']} cases")
    elif args.command == "run":
        value = run()
        print(json.dumps(value, ensure_ascii=False, indent=2))
    else:
        value = score()
        print(json.dumps(
            {key: value[key] for key in (
                "counts", "evidence_precision", "evidence_recall",
                "qualification",
            )},
            ensure_ascii=False,
            indent=2,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
