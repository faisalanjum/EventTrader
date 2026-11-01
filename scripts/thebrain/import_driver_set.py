#!/usr/bin/env python3
"""Import the accepted seed as Driver-only TheBrain thoughts.

Phase 1 deliberately creates no company, sector, evidence, index, type, or tag
thoughts. Each distinct raw KPI name becomes one Driver thought linked directly
to the Driver Catalog home thought. All accepted evidence is stored in its note.

TheBrain API key is read from THEBRAIN_API_KEY and is never written to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DEFAULT_SEED = Path("data/driver_catalog_seed/part1/seed_records.jsonl")
DEFAULT_API_BASE = "http://127.0.0.1:18001/api"
DEFAULT_BRAIN_NAME = "Driver Catalog"
DEFAULT_MANIFEST = Path("data/driver_catalog_seed/thebrain_driver_manifest.json")
DEFAULT_CLEANUP_BACKUP = Path(
    "data/driver_catalog_seed/thebrain_pilot_cleanup_backup.json"
)
IMPORT_VERSION = "driver-only-v1"
MAX_NOTE_CHARS = 250_000
DEFAULT_WORKERS = 1

MANAGED_START = "<!-- EMDB-DRIVER-SET-START -->"
MANAGED_END = "<!-- EMDB-DRIVER-SET-END -->"

PILOT_MARKERS = (
    "<!-- EMDB-REVENUE-PILOT-START -->",
    "<!-- EVENTMARKETDB:REVENUE_PILOT:START -->",
    "<!-- EVENTMARKETDB:REVENUE\\_PILOT:START -->",
)
PILOT_TYPE_NAMES = ("Catalog Index", "Metric Driver", "Company")
PILOT_FIXED_NAMES = (
    "Drivers",
    "Companies",
    "Coverage & Import",
    "Most Common Drivers",
    "revenue",
    "Evidence · revenue",
    "Revenue Pilot Status",
)
LIVE_TEST_NAME = "Live API Test"
LIVE_TEST_ID = "7c3898ba-85aa-475b-9d9f-abcecf1af1fa"
PILOT_REVENUE_ID = "3a87b0ab-f6df-45a3-affc-dd20ad8033e7"
PILOT_EVIDENCE_ID = "75bed6f9-2824-4feb-b622-1e22beb8f12a"
PILOT_LINK_COUNT = 258
PILOT_NOTE_COUNT = 125


class ApiError(RuntimeError):
    pass


class TheBrainApi:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def request(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        allowed: tuple[int, ...] = (200,),
        timeout: int = 30,
    ) -> tuple[int, Any]:
        data = None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"{self.base_url}/{path.lstrip('/')}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
        except urllib.error.URLError as exc:
            raise ApiError(f"TheBrain API connection failed: {exc.reason}") from exc
        text = raw.decode("utf-8", errors="replace") if raw else ""
        if status not in allowed:
            raise ApiError(
                f"{method} {path} returned HTTP {status}: "
                f"{text[:500].replace(chr(10), ' ')}"
            )
        if not text:
            return status, None
        try:
            return status, json.loads(text)
        except json.JSONDecodeError:
            return status, text

    def find_exact(self, brain_id: str, name: str) -> dict[str, Any] | None:
        query = urllib.parse.urlencode({"nameExact": name})
        status, body = self.request(
            "GET", f"thoughts/{brain_id}?{query}", allowed=(200, 204, 404)
        )
        if status in (204, 404):
            return None
        if not isinstance(body, dict) or not body.get("id"):
            raise ApiError(
                f"Exact-name lookup for {name!r} returned malformed HTTP 200 data"
            )
        return body

    def read_note(self, brain_id: str, thought_id: str) -> str:
        status, body = self.request(
            "GET", f"notes/{brain_id}/{thought_id}", allowed=(200, 204, 404)
        )
        if status in (204, 404):
            return ""
        if not isinstance(body, dict):
            raise ApiError(f"Note lookup for thought {thought_id} returned malformed data")
        markdown = body.get("markdown")
        if markdown is None:
            return ""
        if not isinstance(markdown, str):
            raise ApiError(f"Note markdown for thought {thought_id} is not text")
        return markdown

    def get_thought(self, brain_id: str, thought_id: str) -> dict[str, Any] | None:
        status, body = self.request(
            "GET",
            f"thoughts/{brain_id}/{thought_id}",
            # TheBrain Desktop 1.0.5 returns 403 for a deleted thought ID.
            # Authentication is checked separately by the brain lookup first.
            allowed=(200, 204, 403, 404),
        )
        if status in (204, 403, 404):
            return None
        if not isinstance(body, dict) or body.get("id") != thought_id:
            raise ApiError(f"Thought lookup for {thought_id} returned malformed data")
        return body

    def read_graph(self, brain_id: str, thought_id: str) -> dict[str, Any]:
        _, body = self.request("GET", f"thoughts/{brain_id}/{thought_id}/graph")
        if not isinstance(body, dict):
            raise ApiError(f"Graph lookup for thought {thought_id} returned malformed data")
        return body

    def update_label(self, brain_id: str, thought_id: str, label: str) -> None:
        self.request(
            "PATCH",
            f"thoughts/{brain_id}/{thought_id}",
            [
                {
                    "value": label,
                    "operationType": 2,
                    "path": "/label",
                    "op": "replace",
                }
            ],
        )

    def has_parent_link(
        self, brain_id: str, parent_id: str, child_id: str
    ) -> bool:
        status, body = self.request(
            "GET",
            f"links/{brain_id}/{parent_id}/{child_id}",
            allowed=(200, 204, 404),
        )
        if status in (204, 404):
            return False
        if not isinstance(body, dict):
            raise ApiError("TheBrain returned malformed link data")
        if (
            body.get("thoughtIdA") != parent_id
            or body.get("thoughtIdB") != child_id
            or body.get("relation") != 1
        ):
            raise ApiError("An existing Driver link has the wrong direction or relation")
        return True

    def ensure_parent_link(
        self, brain_id: str, parent_id: str, child_id: str
    ) -> None:
        if self.has_parent_link(brain_id, parent_id, child_id):
            return
        self.request(
            "POST",
            f"links/{brain_id}",
            {"thoughtIdA": parent_id, "thoughtIdB": child_id, "relation": 1},
        )
        for _ in range(20):
            if self.has_parent_link(brain_id, parent_id, child_id):
                return
            time.sleep(0.25)
        raise ApiError(f"TheBrain did not confirm the link for Driver {child_id}")


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_groups(path: Path) -> tuple[dict[str, list[dict[str, Any]]], str]:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_fact_keys: set[tuple[Any, ...]] = set()
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
        name = str(record.get("kpi") or "").strip()
        if not name:
            raise RuntimeError(f"Missing KPI name at {path}:{line_number}")
        fact_key = (record.get("ticker"), name, record.get("period"))
        if fact_key in seen_fact_keys:
            raise RuntimeError(f"Duplicate ticker + KPI + period at {path}:{line_number}")
        seen_fact_keys.add(fact_key)
        record["_seed_line"] = line_number
        groups[name].append(record)
    if not groups:
        raise RuntimeError(f"No Driver records found in {path}")
    for records in groups.values():
        records.sort(
            key=lambda record: (
                record.get("ticker", ""),
                record.get("period", ""),
                record.get("form", ""),
            )
        )
    return dict(sorted(groups.items())), sha


def record_hash(record: dict[str, Any]) -> str:
    clean = {key: value for key, value in record.items() if not key.startswith("_")}
    blob = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def driver_key(name: str) -> str:
    return hashlib.sha256(f"raw-kpi:{name}".encode("utf-8")).hexdigest()[:20]


def driver_label(name: str, records: list[dict[str, Any]]) -> str:
    companies = len({record["ticker"] for record in records})
    return (
        f"{len(records)} evidence · {companies} companies · "
        f"emdb:{driver_key(name)}"
    )


def evidence_start_marker(record: dict[str, Any]) -> str:
    return f"<!-- EMDB-EVIDENCE-{record_hash(record)}-START -->"


def evidence_end_marker(record: dict[str, Any]) -> str:
    return f"<!-- EMDB-EVIDENCE-{record_hash(record)}-END -->"


def company_marker(ticker: str, boundary: str) -> str:
    key = hashlib.sha256(ticker.encode("utf-8")).hexdigest()[:16]
    return f"<!-- EMDB-COMPANY-{key}-{boundary} -->"


def content_signature(
    name: str, records: list[dict[str, Any]], sha: str
) -> str:
    payload = {
        "version": IMPORT_VERSION,
        "driver_key": driver_key(name),
        "seed_sha256": sha,
        "evidence": [record_hash(record) for record in records],
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def quote_block(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(f"> {line}" if line else ">" for line in text.split("\n"))


def exact_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def compact_value(record: dict[str, Any] | None) -> str:
    if not record or record.get("value") is None:
        return "—"
    value = float(record["value"])
    if record.get("fmt") == "%":
        return f"{value:,.2f}".rstrip("0").rstrip(".") + "%"
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if absolute >= divisor:
            scaled = absolute / divisor
            digits = 2 if scaled < 10 else 1 if scaled < 100 else 0
            number = f"{scaled:,.{digits}f}"
            if digits:
                number = number.rstrip("0").rstrip(".")
            currency = "$" if record.get("is_currency") else ""
            return f"{sign}{currency}{number}{suffix}"
    currency = "$" if record.get("is_currency") else ""
    number = f"{absolute:,.2f}".rstrip("0").rstrip(".")
    return f"{sign}{currency}{number}"


def latest(records: list[dict[str, Any]], form: str) -> dict[str, Any] | None:
    matches = [record for record in records if record.get("form") == form]
    return max(matches, key=lambda record: record.get("period", "")) if matches else None


def managed_block(name: str, records: list[dict[str, Any]], sha: str, seed: Path) -> str:
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_ticker[record["ticker"]].append(record)
    tickers = sorted(by_ticker)
    periods = sorted({record["period"] for record in records})
    tiers = Counter(record.get("tier") or "unknown" for record in records)
    forms = Counter(record.get("form") or "unknown" for record in records)
    categories = sorted(
        {str(record.get("category")) for record in records if record.get("category")}
    )
    key = driver_key(name)
    lines = [
        MANAGED_START,
        f"<!-- EMDB-IMPORT-VERSION-{IMPORT_VERSION} -->",
        f"<!-- EMDB-SOURCE-SHA256-{sha} -->",
        f"<!-- EMDB-DRIVER-KEY-{key} -->",
        f"<!-- EMDB-EVIDENCE-COUNT-{len(records)} -->",
        f"<!-- EMDB-CONTENT-SHA256-{content_signature(name, records, sha)} -->",
        f"# {name}",
        "",
        "## Driver summary",
        "",
        f"- Evidence records: **{len(records):,}**",
        f"- Companies: **{len(tickers):,}**",
        f"- Period range: **{periods[0]} to {periods[-1]}**",
        f"- Filing forms: **{', '.join(f'{item}: {count}' for item, count in sorted(forms.items()))}**",
        f"- Proof methods: **{', '.join(f'{item}: {count}' for item, count in sorted(tiers.items()))}**",
        f"- Driver key: `{key}`",
        f"- Seed: `{seed}`",
        f"- Seed SHA-256: `{sha}`",
    ]
    if categories:
        lines.append(f"- Source categories: {', '.join(f'`{item}`' for item in categories)}")
    lines.extend(
        [
            "",
            "## Company comparison",
            "",
            "Compact values are for quick scanning. Exact normalized values and verbatim quotes appear in the full evidence below.",
            "",
            "| Company | Latest quarter | Latest annual | Evidence rows |",
            "|---|---:|---:|---:|",
        ]
    )
    for ticker in tickers:
        company_records = by_ticker[ticker]
        lines.append(
            f"| {ticker} | {compact_value(latest(company_records, '10-Q'))} | "
            f"{compact_value(latest(company_records, '10-K'))} | {len(company_records)} |"
        )
    lines.extend(["", "## Full accepted evidence", ""])
    for ticker in tickers:
        lines.extend([company_marker(ticker, "START"), f"### {ticker}", ""])
        for record in by_ticker[ticker]:
            lines.extend(
                [
                    evidence_start_marker(record),
                    f"#### {record['period']} · {record.get('form')} · {record.get('tier', 'unknown')}",
                    "",
                    f"- Exact normalized value: `{exact_value(record.get('value'))}`",
                    f"- Format: `{record.get('fmt')}` · currency flag: `{record.get('is_currency')}`",
                    f"- Filing: `{record.get('filing_id')}`",
                    f"- Source: `{record.get('source')}`",
                    f"- Seed line: `{record.get('_seed_line')}` · evidence row: `{record_hash(record)}`",
                ]
            )
            if record.get("category"):
                lines.append(f"- Source category: `{record['category']}`")
            if record.get("concept"):
                lines.append(f"- Filing concept: `{record['concept']}`")
            if record.get("member"):
                lines.append(f"- Filing member: `{record['member']}`")
            if record.get("source_element_id"):
                lines.append(f"- Source node: `{record['source_element_id']}`")
            if record.get("value_as_written"):
                lines.append(f"- Value as written: `{record['value_as_written']}`")
            lines.extend(
                ["", "**Exact quote**", "", quote_block(record.get("quote")), ""]
            )
            if record.get("xbrl_fact"):
                lines.extend(
                    [
                        "**Structured filing fact**",
                        "",
                        quote_block(record["xbrl_fact"]),
                        "",
                    ]
                )
            lines.extend([evidence_end_marker(record), ""])
        lines.extend([company_marker(ticker, "END"), ""])
    lines.append(MANAGED_END)
    return "\n".join(lines)


def managed_bounds(note: str) -> tuple[int, int] | None:
    starts = note.count(MANAGED_START)
    ends = note.count(MANAGED_END)
    if starts == 0 and ends == 0:
        return None
    if starts != 1 or ends != 1:
        raise ApiError(
            f"Managed note has {starts} start markers and {ends} end markers"
        )
    start = note.index(MANAGED_START)
    try:
        end = note.index(MANAGED_END, start) + len(MANAGED_END)
    except ValueError as exc:
        raise ApiError("Managed note end marker appears before its start marker") from exc
    return start, end


def merge_note(existing: str, block: str) -> str:
    bounds = managed_bounds(existing)
    if bounds:
        start, end = bounds
        return f"{existing[:start]}{block}{existing[end:]}".strip() + "\n"
    if existing.strip():
        return f"{block}\n\n{existing.strip()}\n"
    return f"{block}\n\n## Personal notes\n\n"


def select_brain(api: TheBrainApi, name: str) -> tuple[str, str]:
    _, brains = api.request("GET", "brains")
    if not isinstance(brains, list):
        raise ApiError("TheBrain returned a malformed brain list")
    matches = [brain for brain in brains if brain.get("name") == name]
    if len(matches) != 1:
        raise ApiError(f"Expected one brain named {name!r}, found {len(matches)}")
    return matches[0]["id"], matches[0]["homeThoughtId"]


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def load_manifest(
    path: Path,
    brain_id: str,
    sha: str,
    groups: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    if path.exists():
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot read Driver manifest {path}: {exc}") from exc
        if not isinstance(manifest, dict):
            raise RuntimeError(f"Driver manifest {path} is not a JSON object")
        expected = {
            "version": IMPORT_VERSION,
            "brain_id": brain_id,
            "seed_sha256": sha,
        }
        for field, value in expected.items():
            if manifest.get(field) != value:
                raise RuntimeError(
                    f"Driver manifest {path} has a different {field}; review it first"
                )
    else:
        manifest = {
            "version": IMPORT_VERSION,
            "brain_id": brain_id,
            "seed_sha256": sha,
            "driver_count": len(groups),
            "drivers": {},
        }
    drivers = manifest.get("drivers")
    if not isinstance(drivers, dict):
        raise RuntimeError(f"Driver manifest {path} has no valid drivers map")
    if manifest.get("driver_count") != len(groups):
        raise RuntimeError(f"Driver manifest {path} has the wrong driver_count")
    expected_names = set(groups)
    recorded_names: set[str] = set()
    recorded_ids: set[str] = set()
    for key, entry in drivers.items():
        if not isinstance(entry, dict):
            raise RuntimeError(f"Driver manifest entry {key!r} is invalid")
        name = entry.get("name")
        thought_id = entry.get("thought_id")
        if name not in expected_names or key != driver_key(name):
            raise RuntimeError(f"Driver manifest entry {key!r} does not match this seed")
        if name in recorded_names or (thought_id and thought_id in recorded_ids):
            raise RuntimeError("Driver manifest contains a duplicate name or thought ID")
        recorded_names.add(name)
        if thought_id:
            recorded_ids.add(thought_id)
        state = entry.get("state")
        if state not in ("created", "verified"):
            raise RuntimeError(f"Driver manifest entry {key!r} has an invalid state")
        if state == "verified":
            records = groups[name]
            expected_fields = {
                "evidence_count": len(records),
                "company_count": len({record["ticker"] for record in records}),
                "content_sha256": content_signature(name, records, sha),
            }
            for field, expected_value in expected_fields.items():
                if entry.get(field) != expected_value:
                    raise RuntimeError(
                        f"Driver manifest entry {key!r} has the wrong {field}"
                    )
    return manifest


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json_atomic(path, manifest)


def normalize_visible_text(value: Any) -> str:
    text = html.unescape(str(value or "")).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\\([\\`*_{}\[\]()#+.!|>\-])", r"\1", text)
    cleaned_lines = []
    for line in text.split("\n"):
        line = re.sub(r"^\s{0,3}>\s?", "", line)
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        line = re.sub(r"^\s*[-*]\s+", "", line)
        cleaned_lines.append(line.replace("`", "").replace("**", ""))
    return re.sub(r"\s+", " ", " ".join(cleaned_lines)).strip()


def record_visible_fragments(record: dict[str, Any]) -> list[str]:
    fragments = [
        f"{record.get('period')} · {record.get('form')} · {record.get('tier', 'unknown')}",
        f"Exact normalized value: {exact_value(record.get('value'))}",
        f"Format: {record.get('fmt')} · currency flag: {record.get('is_currency')}",
        f"Filing: {record.get('filing_id')}",
        f"Source: {record.get('source')}",
        f"Seed line: {record.get('_seed_line')} · evidence row: {record_hash(record)}",
        str(record.get("quote") or ""),
    ]
    optional_fields = (
        ("Source category", "category"),
        ("Filing concept", "concept"),
        ("Filing member", "member"),
        ("Source node", "source_element_id"),
        ("Value as written", "value_as_written"),
    )
    for label, field in optional_fields:
        if record.get(field):
            fragments.append(f"{label}: {record[field]}")
    if record.get("xbrl_fact"):
        fragments.append(record["xbrl_fact"])
    return [normalize_visible_text(fragment) for fragment in fragments]


def note_is_current(note: str, name: str, records: list[dict[str, Any]], sha: str) -> bool:
    bounds = managed_bounds(note)
    if not bounds:
        return False
    start, end = bounds
    managed = note[start:end]
    required = (
        f"<!-- EMDB-IMPORT-VERSION-{IMPORT_VERSION} -->",
        f"<!-- EMDB-SOURCE-SHA256-{sha} -->",
        f"<!-- EMDB-DRIVER-KEY-{driver_key(name)} -->",
        f"<!-- EMDB-EVIDENCE-COUNT-{len(records)} -->",
        f"<!-- EMDB-CONTENT-SHA256-{content_signature(name, records, sha)} -->",
    )
    if any(managed.count(marker) != 1 for marker in required):
        return False
    tickers = sorted({record["ticker"] for record in records})
    periods = sorted({record["period"] for record in records})
    tiers = Counter(record.get("tier") or "unknown" for record in records)
    forms = Counter(record.get("form") or "unknown" for record in records)
    summary_fragments = (
        name,
        f"Evidence records: {len(records):,}",
        f"Companies: {len(tickers):,}",
        f"Period range: {periods[0]} to {periods[-1]}",
        f"Filing forms: {', '.join(f'{item}: {count}' for item, count in sorted(forms.items()))}",
        f"Proof methods: {', '.join(f'{item}: {count}' for item, count in sorted(tiers.items()))}",
        "Company comparison",
        "Full accepted evidence",
    )
    normalized_managed = normalize_visible_text(managed)
    if any(
        normalize_visible_text(fragment) not in normalized_managed
        for fragment in summary_fragments
    ):
        return False

    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_ticker[record["ticker"]].append(record)
    for ticker, company_records in by_ticker.items():
        company_start = company_marker(ticker, "START")
        company_end = company_marker(ticker, "END")
        if managed.count(company_start) != 1 or managed.count(company_end) != 1:
            return False
        group_start = managed.index(company_start) + len(company_start)
        try:
            group_end = managed.index(company_end, group_start)
        except ValueError:
            return False
        company_block = managed[group_start:group_end]
        if not normalize_visible_text(company_block).startswith(
            normalize_visible_text(ticker) + " "
        ):
            return False
        for record in company_records:
            if (
                evidence_start_marker(record) not in company_block
                or evidence_end_marker(record) not in company_block
            ):
                return False
    for record in records:
        start_marker = evidence_start_marker(record)
        end_marker = evidence_end_marker(record)
        if managed.count(start_marker) != 1 or managed.count(end_marker) != 1:
            return False
        record_start = managed.index(start_marker) + len(start_marker)
        try:
            record_end = managed.index(end_marker, record_start)
        except ValueError:
            return False
        visible = normalize_visible_text(managed[record_start:record_end])
        if any(fragment not in visible for fragment in record_visible_fragments(record)):
            return False
    expected = managed_block(name, records, sha, DEFAULT_SEED)
    return len(managed) >= int(len(expected) * 0.75)


def note_has_owner(note: str, name: str) -> bool:
    bounds = managed_bounds(note)
    if not bounds:
        return False
    start, end = bounds
    return note[start:end].count(
        f"<!-- EMDB-DRIVER-KEY-{driver_key(name)} -->"
    ) == 1


def import_one(
    api: TheBrainApi,
    brain_id: str,
    home_id: str,
    name: str,
    records: list[dict[str, Any]],
    sha: str,
    seed: Path,
    thought: dict[str, Any] | None,
    on_created: Callable[[str], None],
) -> tuple[str, str]:
    created = False
    if thought:
        note = api.read_note(brain_id, thought["id"])
        if not note_has_owner(note, name) and thought.get("label") != driver_label(
            name, records
        ):
            raise ApiError(
                f"Name collision: existing thought {name!r} is not managed by this import"
            )
        if note_is_current(note, name, records, sha):
            if thought.get("label") != driver_label(name, records):
                api.update_label(
                    brain_id, thought["id"], driver_label(name, records)
                )
                api.ensure_parent_link(brain_id, home_id, thought["id"])
                return "updated", thought["id"]
            api.ensure_parent_link(brain_id, home_id, thought["id"])
            return "unchanged", thought["id"]
    else:
        _, body = api.request(
            "POST",
            f"thoughts/{brain_id}",
            {
                "name": name,
                "kind": 1,
                "acType": 1,
                "label": driver_label(name, records),
            },
        )
        thought_id = body.get("id") if isinstance(body, dict) else None
        if not thought_id:
            raise ApiError(f"TheBrain returned no ID for new Driver {name!r}")
        thought = {
            "id": thought_id,
            "name": name,
            "kind": 1,
            "label": driver_label(name, records),
        }
        created = True
        on_created(thought_id)

    existing = api.read_note(brain_id, thought["id"])
    block = managed_block(name, records, sha, seed)
    merged = merge_note(existing, block)
    if len(merged) > MAX_NOTE_CHARS:
        raise ApiError(
            f"Driver {name!r} note is {len(merged):,} characters; "
            f"limit is {MAX_NOTE_CHARS:,}"
        )
    api.request(
        "POST",
        f"notes/{brain_id}/{thought['id']}/update",
        {"markdown": merged},
        timeout=60,
    )
    written = ""
    for _ in range(20):
        written = api.read_note(brain_id, thought["id"])
        if note_is_current(written, name, records, sha) and len(written) >= int(
            len(merged) * 0.85
        ):
            break
        time.sleep(0.25)
    else:
        raise ApiError(
            f"Driver {name!r} note failed read-back verification: "
            f"wrote {len(merged):,}, read {len(written):,} characters"
        )
    if thought.get("label") != driver_label(name, records):
        api.update_label(brain_id, thought["id"], driver_label(name, records))
    api.ensure_parent_link(brain_id, home_id, thought["id"])
    return ("created" if created else "updated"), thought["id"]


def pilot_expected_names(groups: dict[str, list[dict[str, Any]]]) -> tuple[list[str], list[str]]:
    total_revenue = groups.get("Total Revenue") or []
    tickers = sorted({record["ticker"] for record in total_revenue})
    letters = sorted({(ticker[:1] or "#").upper() for ticker in tickers})
    bucket_names = [f"Companies · {letter}" for letter in letters]
    bucket_names += [f"revenue evidence · {letter}" for letter in letters]
    normal_names = [*PILOT_FIXED_NAMES, *bucket_names, *tickers, LIVE_TEST_NAME]
    return normal_names, list(PILOT_TYPE_NAMES)


def has_pilot_marker(note: str) -> bool:
    return any(marker in note for marker in PILOT_MARKERS)


def resume_cleanup_plan(
    api: TheBrainApi,
    brain_id: str,
    home_id: str,
    backup_path: Path,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    if (
        snapshot.get("version") != "revenue-pilot-cleanup-v1"
        or snapshot.get("brain_id") != brain_id
        or snapshot.get("home_thought_id") != home_id
    ):
        raise ApiError(f"Cleanup backup {backup_path} does not match this brain")
    plan = snapshot.get("delete_order")
    deleted_ids = snapshot.get("deleted_ids")
    if not isinstance(plan, list) or not isinstance(deleted_ids, list):
        raise ApiError(f"Cleanup backup {backup_path} has no valid deletion plan")
    plan_ids: set[str] = set()
    for item in plan:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("name"), str)
            or item.get("kind") not in (1, 2)
            or item["id"] in plan_ids
        ):
            raise ApiError(f"Cleanup backup {backup_path} has an invalid target")
        plan_ids.add(item["id"])
    if (
        any(not isinstance(thought_id, str) for thought_id in deleted_ids)
        or len(set(deleted_ids)) != len(deleted_ids)
        or not set(deleted_ids).issubset(plan_ids)
    ):
        raise ApiError(f"Cleanup backup {backup_path} has invalid deleted IDs")

    present: dict[str, dict[str, Any]] = {}
    for item in plan:
        thought = api.get_thought(brain_id, item["id"])
        if thought:
            if thought.get("name") != item["name"] or thought.get("kind") != item["kind"]:
                raise ApiError(
                    f"Cleanup target {item['id']} no longer matches {item['name']!r}"
                )
            present[item["id"]] = thought

    _, current_stats = api.request("GET", f"brains/{brain_id}/statistics")
    if not isinstance(current_stats, dict):
        raise ApiError("Cleanup resume returned malformed brain statistics")
    present_normal = sum(item["kind"] == 1 and item["id"] in present for item in plan)
    present_types = sum(item["kind"] == 2 and item["id"] in present for item in plan)
    for field, expected in {
        "thoughts": present_normal + 1,
        "thoughtTypes": present_types,
        "tags": 0,
    }.items():
        actual = integer_stat(current_stats, field)
        if actual != expected:
            raise ApiError(
                f"Cleanup resume expected {field}={expected}, found {actual}; "
                "unplanned thoughts may exist"
            )
    if integer_stat(current_stats, "links") > PILOT_LINK_COUNT:
        raise ApiError("Cleanup resume found links outside the frozen pilot plan")

    deleted = set(deleted_ids)
    snapshot["state"] = "deleting"
    write_json_atomic(backup_path, snapshot)
    for item in plan:
        thought_id = item["id"]
        if thought_id not in present:
            deleted.add(thought_id)
        else:
            api.request(
                "DELETE",
                f"thoughts/{brain_id}/{thought_id}",
                allowed=(200, 204),
            )
            for _ in range(12):
                if not api.get_thought(brain_id, thought_id):
                    break
                time.sleep(0.25)
            else:
                raise ApiError(f"Cleanup verification failed for {item['name']!r}")
            deleted.add(thought_id)
        snapshot["deleted_ids"] = sorted(deleted)
        write_json_atomic(backup_path, snapshot)

    _, after_stats = api.request("GET", f"brains/{brain_id}/statistics")
    if not isinstance(after_stats, dict):
        raise ApiError("Cleanup verification returned malformed brain statistics")
    for field, expected in {
        "thoughts": 1,
        "thoughtTypes": 0,
        "links": 0,
        "tags": 0,
    }.items():
        actual = integer_stat(after_stats, field)
        if actual != expected:
            raise ApiError(
                f"Cleanup verification expected {field}={expected}, found {actual}"
            )
    snapshot["state"] = "complete"
    snapshot["statistics_after"] = after_stats
    write_json_atomic(backup_path, snapshot)
    return {
        "deleted": len(plan),
        "backup": str(backup_path),
        "brain_statistics_after": after_stats,
        "resumable": True,
    }


def cleanup_pilot(
    api: TheBrainApi,
    brain_id: str,
    home_id: str,
    groups: dict[str, list[dict[str, Any]]],
    dry_run: bool,
    backup_path: Path,
    sha: str,
) -> dict[str, Any]:
    if not dry_run and backup_path.exists():
        try:
            existing_snapshot = json.loads(backup_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ApiError(f"Cannot read cleanup backup {backup_path}: {exc}") from exc
        if not isinstance(existing_snapshot, dict):
            raise ApiError(f"Cleanup backup {backup_path} is not a JSON object")
        if existing_snapshot.get("seed_sha256") != sha:
            raise ApiError(f"Cleanup backup {backup_path} has a different source hash")
        return resume_cleanup_plan(
            api, brain_id, home_id, backup_path, existing_snapshot
        )

    normal_names, type_names = pilot_expected_names(groups)
    found: dict[str, dict[str, Any]] = {}
    for name in [*normal_names, *type_names]:
        thought = api.find_exact(brain_id, name)
        if thought:
            found[name] = thought

    if LIVE_TEST_NAME in found and found[LIVE_TEST_NAME]["id"] != LIVE_TEST_ID:
        raise ApiError("Live API Test ID does not match the test thought created in this session")
    for name, expected_id in {
        "revenue": PILOT_REVENUE_ID,
        "Evidence · revenue": PILOT_EVIDENCE_ID,
    }.items():
        thought = found.get(name)
        if not thought or thought["id"] != expected_id:
            raise ApiError(f"Cleanup refused: {name!r} does not match the known pilot ID")

    type_ids = {name: found[name]["id"] for name in type_names if name in found}
    for name in type_names:
        thought = found.get(name)
        if thought and thought.get("kind") != 2:
            raise ApiError(f"Cleanup refused: {name!r} is not the expected Thought Type")

    marker_names = {
        "Most Common Drivers",
        "revenue",
        "Evidence · revenue",
        "Revenue Pilot Status",
        *{record["ticker"] for record in groups.get("Total Revenue", [])},
    }
    for name in marker_names:
        thought = found.get(name)
        if thought and not has_pilot_marker(api.read_note(brain_id, thought["id"])):
            raise ApiError(f"Cleanup refused: {name!r} lacks the pilot marker")

    index_id = type_ids.get("Catalog Index")
    metric_id = type_ids.get("Metric Driver")
    company_id = type_ids.get("Company")
    index_names = {
        "Drivers",
        "Companies",
        "Coverage & Import",
        "Most Common Drivers",
        "Evidence · revenue",
        "Revenue Pilot Status",
        *{name for name in normal_names if name.startswith("Companies · ")},
        *{name for name in normal_names if name.startswith("revenue evidence · ")},
    }
    company_names = {record["ticker"] for record in groups.get("Total Revenue", [])}
    for name, expected_type in [
        *((name, index_id) for name in index_names),
        *((name, company_id) for name in company_names),
        ("revenue", metric_id),
    ]:
        thought = found.get(name)
        if thought and expected_type and thought.get("typeId") != expected_type:
            raise ApiError(f"Cleanup refused: {name!r} has an unexpected Thought Type")

    planned = [name for name in normal_names if name in found]
    planned_types = [name for name in type_names if name in found]
    missing = sorted(set(normal_names + type_names) - set(found))
    if missing not in ([], [LIVE_TEST_NAME]):
        raise ApiError(f"Cleanup refused because pilot thoughts are missing: {missing}")
    target_ids = [found[name]["id"] for name in planned + planned_types]
    if home_id in target_ids or len(set(target_ids)) != len(target_ids):
        raise ApiError("Cleanup refused: target IDs include the home thought or a duplicate")

    _, before_stats = api.request("GET", f"brains/{brain_id}/statistics")
    if not isinstance(before_stats, dict):
        raise ApiError("Cleanup refused: malformed brain statistics")
    before_checks = {
        "thoughts": len(planned) + 1,
        "thoughtTypes": len(planned_types),
        "links": PILOT_LINK_COUNT,
        "notes": PILOT_NOTE_COUNT,
        "forgottenThoughts": 0,
        "linkTypes": 0,
        "tags": 0,
        "internalFiles": 0,
        "externalFiles": 0,
        "webLinks": 0,
    }
    for field, expected in before_checks.items():
        actual = integer_stat(before_stats, field)
        if actual != expected:
            raise ApiError(
                f"Cleanup refused: expected {field}={expected}, found {actual}"
            )
    result = {
        "expected_cleanup_thoughts": len(normal_names) + len(type_names),
        "found_cleanup_thoughts": len(planned) + len(planned_types),
        "missing": missing,
        "dry_run": dry_run,
        "brain_statistics_before": before_stats,
    }
    if dry_run:
        return result

    company_names = sorted(
        {record["ticker"] for record in groups.get("Total Revenue", [])}
    )
    bucket_names = sorted(
        name
        for name in planned
        if name.startswith("Companies · ") or name.startswith("revenue evidence · ")
    )
    roots_last = [
        "Revenue Pilot Status",
        "Most Common Drivers",
        "Evidence · revenue",
        "revenue",
        "Drivers",
        "Companies",
        "Coverage & Import",
        LIVE_TEST_NAME,
    ]
    delete_names = []
    for name in [*company_names, *bucket_names, *roots_last, *planned]:
        if name in planned and name not in delete_names:
            delete_names.append(name)
    delete_names.extend(planned_types)

    snapshot = {
        "version": "revenue-pilot-cleanup-v1",
        "state": "planned",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "brain_id": brain_id,
        "home_thought_id": home_id,
        "seed_sha256": sha,
        "statistics": before_stats,
        "deleted_ids": [],
        "delete_order": [
            {
                "name": name,
                "id": found[name]["id"],
                "kind": found[name]["kind"],
            }
            for name in delete_names
        ],
        "thoughts": [
            {
                "name": name,
                "thought": found[name],
                "note_markdown": api.read_note(brain_id, found[name]["id"]),
            }
            for name in planned + planned_types
        ],
        "graphs": {
            found[name]["id"]: api.read_graph(brain_id, found[name]["id"])
            for name in planned
        },
    }
    write_json_atomic(backup_path, snapshot)
    result.update(
        resume_cleanup_plan(api, brain_id, home_id, backup_path, snapshot)
    )
    return result


def dry_run_report(
    groups: dict[str, list[dict[str, Any]]], sha: str, seed: Path
) -> dict[str, Any]:
    sizes = []
    for name, records in groups.items():
        size = len(managed_block(name, records, sha, seed))
        sizes.append((size, name, len(records), len({record["ticker"] for record in records})))
    sizes.sort(reverse=True)
    too_large = [item for item in sizes if item[0] > MAX_NOTE_CHARS]
    return {
        "seed_sha256": sha,
        "evidence_rows": sum(len(records) for records in groups.values()),
        "driver_thoughts": len(groups),
        "max_name_chars": max(len(name) for name in groups),
        "largest_notes": [
            {
                "driver": name,
                "note_chars": size,
                "evidence": evidence,
                "companies": companies,
            }
            for size, name, evidence, companies in sizes[:10]
        ],
        "notes_over_limit": len(too_large),
    }


def integer_stat(stats: dict[str, Any], field: str) -> int:
    value = stats.get(field)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or int(value) != value
    ):
        raise ApiError(f"Brain statistic {field!r} is not a whole number")
    return int(value)


def preflight_import(
    api: TheBrainApi,
    brain_id: str,
    home_id: str,
    groups: dict[str, list[dict[str, Any]]],
    manifest: dict[str, Any],
    workers: int,
) -> dict[str, dict[str, Any]]:
    existing: dict[str, dict[str, Any]] = {}
    recorded = manifest["drivers"]
    items = list(groups.items())

    def inspect(
        item: tuple[str, list[dict[str, Any]]]
    ) -> tuple[str, dict[str, Any] | None, bool]:
        name, records = item
        thought = api.find_exact(brain_id, name)
        linked = False
        if thought:
            if thought.get("name") != name or thought.get("kind") != 1:
                raise ApiError(f"Existing exact match for {name!r} is not a normal Driver")
            note = api.read_note(brain_id, thought["id"])
            entry = recorded.get(driver_key(name))
            known_id = entry.get("thought_id") if entry else None
            owned = note_has_owner(note, name) or thought.get("label") == driver_label(
                name, records
            )
            if not owned:
                raise ApiError(
                    f"Name collision: existing thought {name!r} is not owned by this import"
                )
            if known_id and known_id != thought["id"]:
                raise ApiError(f"Driver manifest ID mismatch for {name!r}")
            linked = api.has_parent_link(brain_id, home_id, thought["id"])
        return name, thought, linked

    linked_count = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(inspect, item) for item in items]
        for index, future in enumerate(as_completed(futures), start=1):
            name, thought, linked = future.result()
            if thought:
                existing[name] = thought
            if linked:
                linked_count += 1
            if index % 100 == 0 or index == len(items):
                print(
                    f"preflight {index}/{len(items)} existing={len(existing)}",
                    flush=True,
                )

    for entry in recorded.values():
        if entry.get("thought_id") and entry["name"] not in existing:
            raise ApiError(
                f"Manifest Driver {entry['name']!r} is missing or was renamed in TheBrain"
            )

    _, stats = api.request("GET", f"brains/{brain_id}/statistics")
    if not isinstance(stats, dict):
        raise ApiError("TheBrain returned malformed brain statistics")
    expected_thoughts = len(existing) + 1  # the one home thought
    checks = {
        "thoughts": expected_thoughts,
        "thoughtTypes": 0,
        "links": linked_count,
        "tags": 0,
    }
    for field, expected in checks.items():
        actual = integer_stat(stats, field)
        if actual != expected:
            raise ApiError(
                f"Import preflight expected {field}={expected}, found {actual}; "
                "the brain contains something beyond the expected Driver-to-Catalog links"
            )
    return existing


def import_all(
    api: TheBrainApi,
    brain_id: str,
    home_id: str,
    groups: dict[str, list[dict[str, Any]]],
    sha: str,
    seed: Path,
    manifest_path: Path,
    workers: int,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, brain_id, sha, groups)
    existing = preflight_import(
        api, brain_id, home_id, groups, manifest, workers
    )
    save_manifest(manifest_path, manifest)
    counts: Counter[str] = Counter()
    items = list(groups.items())
    for index, (name, records) in enumerate(items, start=1):
        key = driver_key(name)

        def remember_created(thought_id: str) -> None:
            manifest["drivers"][key] = {
                "name": name,
                "thought_id": thought_id,
                "state": "created",
            }
            save_manifest(manifest_path, manifest)

        outcome, thought_id = import_one(
            api,
            brain_id,
            home_id,
            name,
            records,
            sha,
            seed,
            existing.get(name),
            remember_created,
        )
        counts[outcome] += 1
        manifest["drivers"][key] = {
            "name": name,
            "thought_id": thought_id,
            "state": "verified",
            "evidence_count": len(records),
            "company_count": len({record["ticker"] for record in records}),
            "content_sha256": content_signature(name, records, sha),
        }
        save_manifest(manifest_path, manifest)
        if index % 25 == 0 or index == len(items):
            print(
                f"progress {index}/{len(items)} created={counts['created']} "
                f"updated={counts['updated']} unchanged={counts['unchanged']}",
                flush=True,
            )
    _, stats = api.request("GET", f"brains/{brain_id}/statistics")
    if not isinstance(stats, dict):
        raise ApiError("Final import statistics are malformed")
    for field, expected in {
        "thoughts": len(groups) + 1,
        "thoughtTypes": 0,
        "links": len(groups),
        "tags": 0,
    }.items():
        actual = integer_stat(stats, field)
        if actual != expected:
            raise ApiError(
                f"Final import expected {field}={expected}, found {actual}"
            )
    return {
        "drivers": len(items),
        **dict(counts),
        "manifest": str(manifest_path),
        "brain_statistics": stats,
    }


def verify_all(
    api: TheBrainApi,
    brain_id: str,
    home_id: str,
    groups: dict[str, list[dict[str, Any]]],
    sha: str,
    workers: int,
    manifest_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    manifest = load_manifest(manifest_path, brain_id, sha, groups)

    def verify_one(item: tuple[str, list[dict[str, Any]]]) -> None:
        name, records = item
        thought = api.find_exact(brain_id, name)
        if not thought:
            raise ApiError("missing thought")
        entry = manifest["drivers"].get(driver_key(name))
        if not entry or entry.get("thought_id") != thought["id"]:
            raise ApiError("thought ID does not match the local Driver manifest")
        if thought.get("label") != driver_label(name, records):
            raise ApiError("visible Driver label does not match the frozen source")
        if not api.has_parent_link(brain_id, home_id, thought["id"]):
            raise ApiError("Driver is not linked directly to Driver Catalog")
        note = api.read_note(brain_id, thought["id"])
        if not note_is_current(note, name, records, sha):
            raise ApiError("managed evidence does not match the frozen source")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(verify_one, item): item[0] for item in groups.items()}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                errors.append(f"{futures[future]}: {exc}")
    driver_error_count = len(errors)
    _, stats = api.request("GET", f"brains/{brain_id}/statistics")
    if not isinstance(stats, dict):
        errors.append("brain statistics: malformed response")
    else:
        for field, expected in {
            "thoughts": len(groups) + 1,
            "thoughtTypes": 0,
            "links": len(groups),
            "tags": 0,
        }.items():
            try:
                actual = integer_stat(stats, field)
                if actual != expected:
                    errors.append(
                        f"brain statistics: expected {field}={expected}, found {actual}"
                    )
            except ApiError as exc:
                errors.append(f"brain statistics: {exc}")
    return {
        "expected_drivers": len(groups),
        "verified_drivers": len(groups) - driver_error_count,
        "errors": errors[:20],
        "brain_statistics": stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--cleanup-pilot", action="store_true")
    action.add_argument("--import-drivers", action="store_true")
    action.add_argument("--verify", action="store_true")
    action.add_argument("--cleanup-dry-run", action="store_true")
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--brain-name", default=DEFAULT_BRAIN_NAME)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cleanup-backup", type=Path, default=DEFAULT_CLEANUP_BACKUP)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise RuntimeError("--workers must be at least 1")
    groups, sha = load_groups(args.seed)
    report = dry_run_report(groups, sha, args.seed)
    print(json.dumps(report, indent=2), flush=True)
    live_action = args.cleanup_pilot or args.cleanup_dry_run or args.import_drivers or args.verify
    if not live_action:
        return 0
    if not args.expected_sha256:
        raise RuntimeError("--expected-sha256 is required for cleanup/import/verify")
    if args.expected_sha256 != sha:
        raise RuntimeError(
            f"Seed changed: expected {args.expected_sha256}, found {sha}. Review again."
        )
    if report["notes_over_limit"]:
        raise RuntimeError("One or more Driver notes exceed the safe size limit")
    api_key = os.environ.get("THEBRAIN_API_KEY")
    if not api_key:
        raise RuntimeError("THEBRAIN_API_KEY is required")
    api = TheBrainApi(args.api_base, api_key)
    brain_id, home_id = select_brain(api, args.brain_name)

    if args.cleanup_pilot or args.cleanup_dry_run:
        result = cleanup_pilot(
            api,
            brain_id,
            home_id,
            groups,
            dry_run=args.cleanup_dry_run,
            backup_path=args.cleanup_backup,
            sha=sha,
        )
    elif args.import_drivers:
        result = import_all(
            api,
            brain_id,
            home_id,
            groups,
            sha,
            args.seed,
            args.manifest,
            args.workers,
        )
    elif args.verify:
        result = verify_all(
            api,
            brain_id,
            home_id,
            groups,
            sha,
            args.workers,
            args.manifest,
        )
    else:
        result = {"dry_run": True}
    print(json.dumps(result, indent=2), flush=True)
    if args.verify and result.get("errors"):
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ApiError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
