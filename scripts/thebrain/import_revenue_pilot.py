#!/usr/bin/env python3
"""Create a repeatable, conservative revenue pilot in TheBrain.

The pilot intentionally uses only seed rows whose raw KPI name is exactly
"Total Revenue". It does not guess how segment, product, or geography labels
should map into the canonical Driver model.

TheBrain API key is read from THEBRAIN_API_KEY and is never written to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SEED = Path("data/driver_catalog_seed/part1/seed_records.jsonl")
DEFAULT_API_BASE = "http://127.0.0.1:18001/api"
DEFAULT_BRAIN_NAME = "Driver Catalog"
PILOT_KPI = "Total Revenue"

MANAGED_START = "<!-- EMDB-REVENUE-PILOT-START -->"
MANAGED_END = "<!-- EMDB-REVENUE-PILOT-END -->"
LEGACY_START_MARKERS = (
    "<!-- EVENTMARKETDB:REVENUE_PILOT:START -->",
    "<!-- EVENTMARKETDB:REVENUE\\_PILOT:START -->",
)
LEGACY_END_MARKERS = (
    "<!-- EVENTMARKETDB:REVENUE_PILOT:END -->",
    "<!-- EVENTMARKETDB:REVENUE\\_PILOT:END -->",
)
MAX_NOTE_CHARS = 250_000


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
        payload: dict[str, Any] | None = None,
        allowed: tuple[int, ...] = (200,),
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
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.status
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
        except urllib.error.URLError as exc:
            raise ApiError(f"TheBrain API connection failed: {exc.reason}") from exc

        text = raw.decode("utf-8", errors="replace") if raw else ""
        if status not in allowed:
            brief = text[:500].replace("\n", " ")
            raise ApiError(f"{method} {path} returned HTTP {status}: {brief}")
        if not text:
            return status, None
        try:
            return status, json.loads(text)
        except json.JSONDecodeError:
            return status, text


class PilotImporter:
    def __init__(self, api: TheBrainApi, brain_id: str, home_id: str) -> None:
        self.api = api
        self.brain_id = brain_id
        self.home_id = home_id
        self.cache: dict[str, dict[str, Any]] = {}
        self.created_thoughts = 0
        self.reused_thoughts = 0
        self.created_links = 0

    def find_exact(self, name: str) -> dict[str, Any] | None:
        if name in self.cache:
            return self.cache[name]
        query = urllib.parse.urlencode({"nameExact": name})
        status, body = self.api.request(
            "GET",
            f"thoughts/{self.brain_id}?{query}",
            allowed=(200, 204, 404),
        )
        if status != 200 or not isinstance(body, dict) or not body.get("id"):
            return None
        self.cache[name] = body
        return body

    def create_thought(
        self,
        name: str,
        *,
        parent_id: str | None = None,
        kind: int = 1,
        type_id: str | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "kind": kind, "acType": 1}
        if parent_id:
            payload.update({"sourceThoughtId": parent_id, "relation": 1})
        if type_id:
            payload["typeId"] = type_id
        if label:
            payload["label"] = label
        _, body = self.api.request("POST", f"thoughts/{self.brain_id}", payload)
        thought_id = body.get("id") if isinstance(body, dict) else None
        if not thought_id:
            raise ApiError(f"TheBrain did not return an ID for new thought {name!r}")
        thought = {
            "id": thought_id,
            "name": name,
            "kind": kind,
            "typeId": type_id,
        }
        self.cache[name] = thought
        self.created_thoughts += 1
        if parent_id:
            self.ensure_link(parent_id, thought_id, relation=1)
        return thought

    def get_or_create(
        self,
        name: str,
        *,
        parent_id: str | None = None,
        kind: int = 1,
        type_id: str | None = None,
        label: str | None = None,
        require_managed_marker: bool = False,
    ) -> dict[str, Any]:
        thought = self.find_exact(name)
        if thought is None:
            thought = self.create_thought(
                name,
                parent_id=parent_id,
                kind=kind,
                type_id=type_id,
                label=label,
            )
            if require_managed_marker:
                self.update_managed_note(
                    thought["id"], f"# {name}\n\nPilot import in progress."
                )
            return thought
        if kind == 2 and thought.get("kind") != 2:
            raise ApiError(
                f"Existing thought {name!r} is not a Thought Type; refusing to reuse it"
            )
        if type_id and thought.get("typeId") != type_id:
            raise ApiError(
                f"Existing thought {name!r} does not have the expected managed type; "
                "refusing to reuse it"
            )
        if require_managed_marker:
            existing_note = self.read_note(thought["id"])
            if not has_managed_markers(existing_note):
                raise ApiError(
                    f"Existing thought {name!r} is not marked as managed by this pilot; "
                    "refusing to change it"
                )
        self.reused_thoughts += 1
        if parent_id:
            self.ensure_link(parent_id, thought["id"], relation=1)
        return thought

    def ensure_link(
        self,
        thought_a: str,
        thought_b: str,
        *,
        relation: int,
        name: str | None = None,
    ) -> None:
        status, existing = self.api.request(
            "GET",
            f"links/{self.brain_id}/{thought_a}/{thought_b}",
            allowed=(200, 204, 404),
        )
        if status == 200:
            if (
                isinstance(existing, dict)
                and existing.get("thoughtIdA") == thought_a
                and existing.get("thoughtIdB") == thought_b
                and existing.get("relation") == relation
            ):
                return
            raise ApiError(
                "A different or reversed link already exists between managed thoughts; "
                "refusing to treat it as the requested parent-child link"
            )
        payload: dict[str, Any] = {
            "thoughtIdA": thought_a,
            "thoughtIdB": thought_b,
            "relation": relation,
        }
        if name:
            payload["name"] = name
        self.api.request("POST", f"links/{self.brain_id}", payload)
        self.created_links += 1

    def read_note(self, thought_id: str) -> str:
        status, body = self.api.request(
            "GET",
            f"notes/{self.brain_id}/{thought_id}",
            allowed=(200, 204, 404),
        )
        if status != 200:
            return ""
        if isinstance(body, dict):
            return body.get("markdown") or ""
        return body if isinstance(body, str) else ""

    def update_managed_note(self, thought_id: str, managed_markdown: str) -> None:
        old = self.read_note(thought_id)
        merged = merge_managed_note(old, managed_markdown)
        if len(merged) > MAX_NOTE_CHARS:
            raise ApiError(
                f"Managed note is {len(merged):,} characters; limit is "
                f"{MAX_NOTE_CHARS:,}. Split it before importing."
            )
        self.api.request(
            "POST",
            f"notes/{self.brain_id}/{thought_id}/update",
            {"markdown": merged},
        )
        written = self.read_note(thought_id)
        if MANAGED_START not in written or MANAGED_END not in written:
            raise ApiError(
                f"TheBrain note read-back is missing its boundary marker for thought "
                f"{thought_id}; the write may have been truncated"
            )
        if len(written) < int(len(merged) * 0.80):
            raise ApiError(
                f"TheBrain note read-back is unexpectedly short for thought {thought_id}: "
                f"wrote {len(merged):,}, read {len(written):,} characters"
            )

    def pin(self, thought_id: str) -> None:
        self.api.request(
            "POST",
            f"thoughts/{self.brain_id}/{thought_id}/pin",
            allowed=(200, 400),
        )

    def activate(self, thought_id: str) -> None:
        self.api.request(
            "POST",
            f"app/brain/{self.brain_id}/thought/{thought_id}/activate",
        )


def marker_bounds(existing: str) -> tuple[int, int] | None:
    starts = (MANAGED_START, *LEGACY_START_MARKERS)
    ends = (MANAGED_END, *LEGACY_END_MARKERS)
    found_starts = [(existing.find(marker), marker) for marker in starts]
    found_starts = [(position, marker) for position, marker in found_starts if position >= 0]
    if not found_starts:
        return None
    start, _ = min(found_starts, key=lambda item: item[0])
    found_ends = []
    for marker in ends:
        position = existing.find(marker, start)
        if position >= 0:
            found_ends.append((position + len(marker), marker))
    if not found_ends:
        return None
    end, _ = min(found_ends, key=lambda item: item[0])
    return start, end


def has_managed_markers(existing: str) -> bool:
    return marker_bounds(existing) is not None


def merge_managed_note(existing: str, managed_markdown: str) -> str:
    block = f"{MANAGED_START}\n{managed_markdown.strip()}\n{MANAGED_END}"
    bounds = marker_bounds(existing)
    if bounds:
        start, end = bounds
        return f"{existing[:start]}{block}{existing[end:]}".strip() + "\n"
    if existing.strip():
        return f"{block}\n\n{existing.strip()}\n"
    return f"{block}\n\n## Personal notes\n\n"


def load_pilot_records(seed_path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = seed_path.read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    records = []
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON at {seed_path}:{line_number}: {exc}") from exc
        if record.get("kpi") == PILOT_KPI:
            record["_seed_line"] = line_number
            records.append(record)
    if not records:
        raise RuntimeError(f"No exact {PILOT_KPI!r} records found in {seed_path}")
    keys = [(r.get("ticker"), r.get("kpi"), r.get("period")) for r in records]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Pilot records contain duplicate ticker + KPI + period keys")
    records.sort(key=lambda r: (r.get("ticker", ""), r.get("period", ""), r.get("form", "")))
    return records, source_sha


def record_hash(record: dict[str, Any]) -> str:
    clean = {k: v for k, v in record.items() if not k.startswith("_")}
    raw = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def quote_block(quote: Any) -> str:
    text = str(quote or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(f"> {line}" if line else ">" for line in text.split("\n"))


def display_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def compact_value(record: dict[str, Any] | None) -> str:
    """Human-friendly quick view; the exact normalized value remains in evidence."""
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


def latest_record(records: list[dict[str, Any]], form: str) -> dict[str, Any] | None:
    matches = [record for record in records if record.get("form") == form]
    return max(matches, key=lambda record: record.get("period", "")) if matches else None


def build_driver_note(
    records: list[dict[str, Any]], source_sha: str, seed_path: Path
) -> str:
    tickers = sorted({r["ticker"] for r in records})
    periods = sorted({r["period"] for r in records})
    tiers = Counter(r.get("tier") or "unknown" for r in records)
    examples: list[dict[str, Any]] = []
    for tier in ("T1-xbrl", "T2-label", "T3-llm"):
        match = next((r for r in records if r.get("tier") == tier), None)
        if match:
            examples.append(match)

    lines = [
        "# revenue",
        "",
        "**Status:** Provisional visual pilot — not the finalized production catalog.",
        "",
        "**Meaning:** The reusable consolidated revenue metric. Company, period, value, and proof remain evidence details; they are not part of this Driver's identity.",
        "",
        "## Pilot boundary",
        "",
        f"This first pilot uses only seed rows whose raw KPI name is exactly `{PILOT_KPI}`. Segment, product, geography, adjusted, and other revenue labels are deliberately excluded until the formal Driver-and-slice mapping step.",
        "",
        "## Coverage",
        "",
        f"- Evidence records: **{len(records):,}**",
        f"- Companies: **{len(tickers):,}**",
        f"- Period range: **{periods[0]} to {periods[-1]}**",
        f"- Match methods: **{', '.join(f'{k}: {v}' for k, v in sorted(tiers.items()))}**",
        f"- Seed source: `{seed_path}`",
        f"- Seed SHA-256: `{source_sha}`",
        "",
        "## Proof examples",
        "",
    ]
    for r in examples:
        lines.extend(
            [
                f"### {r['ticker']} · {r['period']} · {r.get('tier', 'unknown')}",
                "",
                quote_block(r.get("quote")),
                "",
                f"Filing: `{r.get('filing_id')}` · `{r.get('form')}` · evidence row `{record_hash(r)}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Full evidence",
            "",
            "Open the child thought **Evidence · revenue** for every company, period, value, filing, match method, and exact quote.",
        ]
    )
    return "\n".join(lines)


def build_evidence_note(
    records: list[dict[str, Any]], source_sha: str, seed_path: Path
) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["ticker"]].append(record)

    lines = [
        "# Evidence · revenue",
        "",
        "Every entry below is proof for the shared `revenue` Driver. Values and periods describe individual company occurrences, not the Driver identity.",
        "",
        f"Source: `{seed_path}`  ",
        f"SHA-256: `{source_sha}`  ",
        f"Rows: **{len(records):,}** · Companies: **{len(grouped):,}**",
        "",
        "## Company comparison",
        "",
        "This quick view borrows the useful company-versus-KPI comparison from `kpi_explorer.html`. Compact values are for scanning only; the exact normalized value and verbatim quote remain below.",
        "",
        "| Company | Latest quarter | Latest annual | Evidence rows |",
        "|---|---:|---:|---:|",
    ]
    for ticker in sorted(grouped):
        company_records = grouped[ticker]
        lines.append(
            f"| {ticker} | {compact_value(latest_record(company_records, '10-Q'))} | "
            f"{compact_value(latest_record(company_records, '10-K'))} | {len(company_records)} |"
        )
    lines.extend(["", "## Full evidence by company", ""])
    for ticker in sorted(grouped):
        lines.extend([f"## {ticker}", ""])
        for r in grouped[ticker]:
            lines.extend(
                [
                    f"### {r['period']} · {r.get('form')} · {r.get('tier', 'unknown')}",
                    "",
                    f"- Normalized value: `{display_value(r.get('value'))}`",
                    f"- Format: `{r.get('fmt')}` · currency flag: `{r.get('is_currency')}`",
                    f"- Filing: `{r.get('filing_id')}`",
                    f"- Source: `{r.get('source')}`",
                    f"- Original KPI: `{r.get('kpi')}`",
                    f"- Seed line: `{r.get('_seed_line')}` · evidence row: `{record_hash(r)}`",
                ]
            )
            if r.get("concept"):
                lines.append(f"- Filing concept: `{r['concept']}`")
            if r.get("member"):
                lines.append(f"- Filing member: `{r['member']}`")
            if r.get("source_element_id"):
                lines.append(f"- Source node: `{r['source_element_id']}`")
            if r.get("value_as_written"):
                lines.append(f"- Value as written: `{r['value_as_written']}`")
            lines.extend(["", "**Exact quote**", "", quote_block(r.get("quote")), ""])
            if r.get("xbrl_fact"):
                lines.extend(["**Structured filing fact**", "", quote_block(r["xbrl_fact"]), ""])
    return "\n".join(lines)


def build_company_note(ticker: str, records: list[dict[str, Any]]) -> str:
    quarterly = latest_record(records, "10-Q")
    annual = latest_record(records, "10-K")
    return "\n".join(
        [
            f"# {ticker}",
            "",
            "## Driver overview",
            "",
            "| Driver | Latest quarter | Latest annual | Evidence rows |",
            "|---|---:|---:|---:|",
            f"| `revenue` | {compact_value(quarterly)} | {compact_value(annual)} | {len(records)} |",
            "",
            "**Pilot boundary:** this currently covers only seed records whose original KPI is exactly `Total Revenue`.",
            "",
            "Navigate through this Company's `revenue evidence` parent to reach the shared `revenue` Driver and its full proof.",
        ]
    )


def build_most_common_note(records: list[dict[str, Any]]) -> str:
    companies = len({record["ticker"] for record in records})
    return "\n".join(
        [
            "# Most Common Drivers",
            "",
            "Drivers ranked by how many companies have accepted evidence. This view borrows the useful breadth ranking from `kpi_explorer.html`, while keeping one shared Driver identity across companies.",
            "",
            "| Rank | Driver | Companies | Evidence rows |",
            "|---:|---|---:|---:|",
            f"| 1 | `revenue` | {companies} | {len(records)} |",
            "",
            "This is a one-Driver pilot. The table will become meaningful after more approved Drivers are imported.",
        ]
    )


def build_status_note(
    records: list[dict[str, Any]],
    source_sha: str,
    seed_path: Path,
    revenue_id: str,
    evidence_id: str,
) -> str:
    return "\n".join(
        [
            "# Revenue pilot status",
            "",
            "**State:** Imported and managed by EventMarketDB.",
            "",
            f"- Imported at: `{datetime.now(timezone.utc).isoformat()}`",
            f"- Exact raw KPI filter: `{PILOT_KPI}`",
            f"- Evidence records: **{len(records):,}**",
            f"- Companies: **{len({r['ticker'] for r in records}):,}**",
            f"- Seed: `{seed_path}`",
            f"- Seed SHA-256: `{source_sha}`",
            f"- Revenue thought ID: `{revenue_id}`",
            f"- Evidence thought ID: `{evidence_id}`",
            "",
            "Rerunning the importer updates these managed notes and reuses existing thoughts and links. It never deletes thoughts.",
        ]
    )


def letter_bucket(ticker: str) -> str:
    first = (ticker[:1] or "#").upper()
    return first if "A" <= first <= "Z" else "#"


def select_brain(api: TheBrainApi, brain_name: str) -> tuple[str, str]:
    _, brains = api.request("GET", "brains")
    matches = [b for b in brains if b.get("name") == brain_name]
    if len(matches) != 1:
        raise ApiError(
            f"Expected one brain named {brain_name!r}, found {len(matches)}"
        )
    brain = matches[0]
    return brain["id"], brain["homeThoughtId"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--brain-name", default=DEFAULT_BRAIN_NAME)
    parser.add_argument(
        "--expected-sha256",
        help="Required for a live import; prevents importing a changing seed file",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records, source_sha = load_pilot_records(args.seed)
    tickers = sorted({r["ticker"] for r in records})
    driver_note = build_driver_note(records, source_sha, args.seed)
    evidence_note = build_evidence_note(records, source_sha, args.seed)

    print(
        json.dumps(
            {
                "pilot_kpi": PILOT_KPI,
                "records": len(records),
                "companies": len(tickers),
                "seed_sha256": source_sha,
                "driver_note_chars": len(driver_note),
                "evidence_note_chars": len(evidence_note),
                "dry_run": args.dry_run,
            },
            indent=2,
        )
    )
    if args.dry_run:
        return 0

    if not args.expected_sha256:
        raise RuntimeError("--expected-sha256 is required for a live import")
    if args.expected_sha256 != source_sha:
        raise RuntimeError(
            "Seed file changed: expected SHA-256 "
            f"{args.expected_sha256}, found {source_sha}. Run --dry-run and review again."
        )

    api_key = os.environ.get("THEBRAIN_API_KEY")
    if not api_key:
        raise RuntimeError("THEBRAIN_API_KEY is required for a live import")
    api = TheBrainApi(args.api_base, api_key)
    brain_id, home_id = select_brain(api, args.brain_name)
    importer = PilotImporter(api, brain_id, home_id)

    index_type = importer.get_or_create("Catalog Index", kind=2)
    metric_type = importer.get_or_create("Metric Driver", kind=2)
    company_type = importer.get_or_create("Company", kind=2)

    drivers = importer.get_or_create(
        "Drivers", parent_id=home_id, type_id=index_type["id"]
    )
    companies = importer.get_or_create(
        "Companies", parent_id=home_id, type_id=index_type["id"]
    )
    coverage = importer.get_or_create(
        "Coverage & Import", parent_id=home_id, type_id=index_type["id"]
    )
    most_common = importer.get_or_create(
        "Most Common Drivers",
        parent_id=home_id,
        type_id=index_type["id"],
        require_managed_marker=True,
    )
    revenue = importer.get_or_create(
        "revenue",
        parent_id=drivers["id"],
        type_id=metric_type["id"],
        label=f"Metric · {len(records)} evidence · {len(tickers)} companies",
        require_managed_marker=True,
    )
    evidence = importer.get_or_create(
        "Evidence · revenue",
        parent_id=revenue["id"],
        type_id=index_type["id"],
        label=f"{len(records)} records · {len(tickers)} companies",
        require_managed_marker=True,
    )
    status = importer.get_or_create(
        "Revenue Pilot Status",
        parent_id=coverage["id"],
        type_id=index_type["id"],
        require_managed_marker=True,
    )

    company_buckets: dict[str, str] = {}
    evidence_buckets: dict[str, str] = {}
    by_ticker = Counter(r["ticker"] for r in records)
    records_by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_ticker[record["ticker"]].append(record)
    for ticker in tickers:
        letter = letter_bucket(ticker)
        if letter not in company_buckets:
            bucket = importer.get_or_create(
                f"Companies · {letter}",
                parent_id=companies["id"],
                type_id=index_type["id"],
            )
            company_buckets[letter] = bucket["id"]
        if letter not in evidence_buckets:
            bucket = importer.get_or_create(
                f"revenue evidence · {letter}",
                parent_id=evidence["id"],
                type_id=index_type["id"],
            )
            evidence_buckets[letter] = bucket["id"]
        company = importer.get_or_create(
            ticker,
            parent_id=company_buckets[letter],
            type_id=company_type["id"],
            label=f"{by_ticker[ticker]} revenue observation{'s' if by_ticker[ticker] != 1 else ''}",
            require_managed_marker=True,
        )
        importer.ensure_link(
            evidence_buckets[letter], company["id"], relation=1
        )
        importer.update_managed_note(
            company["id"], build_company_note(ticker, records_by_ticker[ticker])
        )

    importer.ensure_link(most_common["id"], revenue["id"], relation=1)
    importer.update_managed_note(revenue["id"], driver_note)
    importer.update_managed_note(evidence["id"], evidence_note)
    importer.update_managed_note(most_common["id"], build_most_common_note(records))
    importer.update_managed_note(
        status["id"],
        build_status_note(
            records,
            source_sha,
            args.seed,
            revenue["id"],
            evidence["id"],
        ),
    )

    for thought in (drivers, companies, most_common, coverage, revenue):
        importer.pin(thought["id"])
    importer.activate(revenue["id"])

    print(
        json.dumps(
            {
                "brain_id": brain_id,
                "revenue_thought_id": revenue["id"],
                "evidence_thought_id": evidence["id"],
                "created_thoughts": importer.created_thoughts,
                "reused_thoughts": importer.reused_thoughts,
                "created_links": importer.created_links,
                "companies_linked": len(tickers),
                "status": "complete",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ApiError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
