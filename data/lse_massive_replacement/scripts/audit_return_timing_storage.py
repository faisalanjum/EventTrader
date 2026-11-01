#!/usr/bin/env python3
"""Check saved return times in Redis and Neo4j without changing either store.

The production data model saves the event time and each return's end time.
It does not save separate start-time fields. This audit imports the production
market-session helper read-only, reconstructs each start and end, and compares
the reconstructed end with the saved schedule.

Redis access is limited to PING, SCAN, TYPE, GET, ZCARD, and ZRANGE. Every
Neo4j query uses a READ_ACCESS session and execute_read.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import redis
from neo4j import GraphDatabase, READ_ACCESS


REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY))

from utils.market_session import MarketSessionClassifier  # noqa: E402


PERIODS = ("hourly", "session", "daily")
SOURCES = ("news", "reports", "transcripts")
PRODUCTION_DELAY_SECONDS = 17 * 60


NEO4J_PATTERNS = {
    "News": (
        "MATCH (n:News)-[r:INFLUENCES]->(c:Company) "
        "WHERE r.hourly_stock IS NOT NULL"
    ),
    "Report": (
        "MATCH (n:Report)-[r:PRIMARY_FILER|REFERENCED_IN]->(c:Company) "
        "WHERE r.hourly_stock IS NOT NULL"
    ),
    "Transcript": (
        "MATCH (n:Transcript)-[r:INFLUENCES]->(c:Company) "
        "WHERE r.hourly_stock IS NOT NULL"
    ),
}


def parse_schedule(raw_schedule: Any) -> tuple[dict[str, Any], str | None]:
    """Return a schedule dictionary and a plain parse-error label."""

    if isinstance(raw_schedule, Mapping):
        return dict(raw_schedule), None
    if isinstance(raw_schedule, str):
        try:
            parsed = json.loads(raw_schedule)
        except json.JSONDecodeError:
            return {}, "invalid_json"
        if isinstance(parsed, dict):
            return parsed, None
        return {}, f"json_{type(parsed).__name__}"
    if raw_schedule is None:
        return {}, "missing"
    return {}, type(raw_schedule).__name__


def eastern_timestamp(value: Any) -> pd.Timestamp:
    """Parse a saved timestamp using the same naive-time assumption as production."""

    parsed = pd.Timestamp(value)
    if parsed.tzinfo is None:
        parsed = parsed.tz_localize(
            "America/New_York",
            ambiguous="raise",
            nonexistent="raise",
        )
    else:
        parsed = parsed.tz_convert("America/New_York")
    return parsed


def same_instant(left: Any, right: Any) -> bool:
    return eastern_timestamp(left).tz_convert("UTC") == eastern_timestamp(
        right
    ).tz_convert("UTC")


def iso_timestamp(value: Any) -> str:
    return eastern_timestamp(value).isoformat()


def cached_classifier() -> MarketSessionClassifier:
    """Use production methods unchanged while avoiding repeated same-input work."""

    classifier = MarketSessionClassifier()
    classifier.get_market_session = lru_cache(maxsize=8192)(  # type: ignore[method-assign]
        classifier.get_market_session
    )
    classifier.get_trading_hours = lru_cache(maxsize=4096)(  # type: ignore[method-assign]
        classifier.get_trading_hours
    )
    return classifier


def production_windows(
    classifier: MarketSessionClassifier,
    created: Any,
    periods: Sequence[str] = PERIODS,
) -> dict[str, dict[str, str]]:
    """Call the live production helper for the requested return windows."""

    windows: dict[str, dict[str, str]] = {}
    if "hourly" in periods:
        start = classifier.get_interval_start_time(created)
        end = classifier.get_interval_end_time(
            created,
            60,
            respect_session_boundary=False,
        )
        windows["hourly"] = {
            "start": iso_timestamp(start),
            "end": iso_timestamp(end),
        }
    if "session" in periods:
        start = classifier.get_start_time(created)
        end = classifier.get_end_time(created)
        windows["session"] = {
            "start": iso_timestamp(start),
            "end": iso_timestamp(end),
        }
    if "daily" in periods:
        start, end = classifier.get_1d_impact_times(created)
        windows["daily"] = {
            "start": iso_timestamp(start),
            "end": iso_timestamp(end),
        }
    return windows


def audit_timing_values(
    *,
    identifier: str,
    created: Any,
    stored_market_session: Any,
    raw_schedule: Any,
    periods: Sequence[str] = PERIODS,
    classifier: MarketSessionClassifier | None = None,
) -> dict[str, Any]:
    """Compare one stored event with the current production time calculation."""

    classifier = classifier or cached_classifier()
    schedule, schedule_error = parse_schedule(raw_schedule)
    created_eastern = iso_timestamp(created)
    computed_market_session = classifier.get_market_session(created)
    windows = production_windows(classifier, created, periods)

    checks: dict[str, Any] = {
        "schedule_parse_error": schedule_error,
        "stored_market_session_matches": (
            stored_market_session == computed_market_session
            if stored_market_session is not None
            else None
        ),
    }
    for period, window in windows.items():
        saved_end = schedule.get(period)
        checks[f"stored_{period}_end_present"] = saved_end is not None
        checks[f"stored_{period}_end_matches"] = (
            same_instant(saved_end, window["end"])
            if saved_end is not None
            else None
        )

    hourly_transition = None
    if "hourly" in windows:
        created_utc = eastern_timestamp(created).tz_convert("UTC")
        start_utc = eastern_timestamp(windows["hourly"]["start"]).tz_convert(
            "UTC"
        )
        end_utc = eastern_timestamp(windows["hourly"]["end"]).tz_convert("UTC")
        checks.update(
            {
                "hourly_start_equals_event": start_utc == created_utc,
                "hourly_start_after_event": start_utc > created_utc,
                "hourly_end_before_event": end_utc < created_utc,
                "hourly_duration_seconds": (
                    end_utc - start_utc
                ).total_seconds(),
            }
        )
        start_session = classifier.get_market_session(
            windows["hourly"]["start"]
        )
        end_session = classifier.get_market_session(windows["hourly"]["end"])
        hourly_transition = f"{start_session}->{end_session}"

    return {
        "identifier": str(identifier),
        "created": created_eastern,
        "stored_market_session": stored_market_session,
        "computed_market_session": computed_market_session,
        "stored_schedule": {
            period: schedule.get(period) for period in PERIODS
        },
        "computed_windows": windows,
        "hourly_transition": hourly_transition,
        "checks": checks,
    }


def compare_pending_score(
    *,
    stored_end: Any,
    redis_score: float,
    delay_seconds: int,
) -> dict[str, Any]:
    """Compare a Redis sorted-set score with saved end + configured delay."""

    end = eastern_timestamp(stored_end)
    expected_score = end.timestamp() + delay_seconds
    actual = pd.Timestamp(
        datetime.fromtimestamp(float(redis_score), tz=timezone.utc)
    ).tz_convert("America/New_York")
    expected = pd.Timestamp(
        datetime.fromtimestamp(expected_score, tz=timezone.utc)
    ).tz_convert("America/New_York")
    difference = float(redis_score) - expected_score
    return {
        "stored_end": end.isoformat(),
        "expected_run_time": expected.isoformat(),
        "redis_run_time": actual.isoformat(),
        "difference_seconds": difference,
        "score_matches": abs(difference) < 0.001,
    }


def redis_payload_timing(
    *,
    key: str,
    raw_payload: str,
    classifier: MarketSessionClassifier,
) -> dict[str, Any]:
    """Extract timing fields only, never event text, from one Redis value."""

    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        raise ValueError("payload_not_object")
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("metadata_missing")
    event = metadata.get("event")
    if not isinstance(event, dict):
        raise ValueError("metadata_event_missing")

    top_level_created = payload.get("created")
    metadata_created = event.get("created")
    created = metadata_created or top_level_created
    if created is None:
        raise ValueError("created_missing")

    identifier = key.split(":", 2)[-1]
    result = audit_timing_values(
        identifier=identifier,
        created=created,
        stored_market_session=event.get("market_session"),
        raw_schedule=metadata.get("returns_schedule"),
        classifier=classifier,
    )
    result["storage_key"] = key
    result["saved_created_fields"] = {
        "top_level": top_level_created,
        "metadata_event": metadata_created,
    }
    result["checks"]["saved_created_fields_match"] = (
        same_instant(top_level_created, metadata_created)
        if top_level_created is not None and metadata_created is not None
        else None
    )
    return result


def increment_timing_counts(counts: Counter[str], record: dict[str, Any]) -> None:
    counts["timing_records"] += 1
    checks = record["checks"]
    if checks.get("schedule_parse_error") == "missing":
        counts["schedule_missing"] += 1
    elif checks.get("schedule_parse_error") is not None:
        counts["schedule_parse_errors"] += 1
    if checks.get("stored_market_session_matches") is True:
        counts["market_session_matches"] += 1
    elif checks.get("stored_market_session_matches") is False:
        counts["market_session_mismatches"] += 1
    for period in PERIODS:
        match = checks.get(f"stored_{period}_end_matches")
        if match is True:
            counts[f"{period}_end_matches"] += 1
        elif match is False:
            counts[f"{period}_end_mismatches"] += 1
        elif checks.get(f"stored_{period}_end_present") is False:
            counts[f"{period}_end_missing"] += 1
    if checks.get("hourly_start_equals_event"):
        counts["hourly_start_equals_event"] += 1
    if checks.get("hourly_start_after_event"):
        counts["hourly_start_after_event"] += 1
    if checks.get("hourly_end_before_event"):
        counts["hourly_end_before_event"] += 1
    if checks.get("hourly_duration_seconds") != 3600:
        counts["hourly_duration_not_3600_seconds"] += 1


def audit_redis(
    *,
    host: str,
    port: int,
    database: int,
    password: str | None,
    delay_seconds: int,
    sample_per_group: int,
) -> dict[str, Any]:
    client = redis.Redis(
        host=host,
        port=port,
        db=database,
        password=password,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=30,
    )
    client.ping()
    classifier = cached_classifier()
    counts: Counter[str] = Counter()
    namespace_counts: Counter[str] = Counter()
    transition_counts: Counter[str] = Counter()
    samples: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    records_by_source_identifier: dict[
        tuple[str, str], dict[str, Any]
    ] = {}
    seen: set[str] = set()
    errors: list[dict[str, str]] = []

    try:
        for source in SOURCES:
            for namespace in ("withreturns", "withoutreturns"):
                pattern = f"{source}:{namespace}:*"
                for key in client.scan_iter(match=pattern, count=2000):
                    if key in seen:
                        continue
                    seen.add(key)
                    counts["keys_scanned"] += 1
                    namespace_key = f"{source}:{namespace}"
                    namespace_counts[namespace_key] += 1
                    key_type = client.type(key)
                    if key_type != "string":
                        counts["non_string_keys"] += 1
                        if len(errors) < 20:
                            errors.append(
                                {
                                    "storage_key": key,
                                    "error": f"unexpected_type:{key_type}",
                                }
                            )
                        continue
                    raw = client.get(key)
                    if raw is None:
                        counts["vanished_during_scan"] += 1
                        continue
                    try:
                        record = redis_payload_timing(
                            key=key,
                            raw_payload=raw,
                            classifier=classifier,
                        )
                    except (ValueError, TypeError, json.JSONDecodeError) as exc:
                        counts["payload_errors"] += 1
                        if len(errors) < 20:
                            errors.append(
                                {
                                    "storage_key": key,
                                    "error": str(exc),
                                }
                            )
                        continue

                    increment_timing_counts(counts, record)
                    transition_counts[record["hourly_transition"]] += 1
                    group = (
                        f"{namespace_key}:"
                        f"{record['computed_market_session']}"
                    )
                    if len(samples[group]) < sample_per_group:
                        samples[group].append(record)
                    identifier = key.split(":", 2)[-1]
                    records_by_source_identifier[(source, identifier)] = record

        pending_counts: Counter[str] = Counter()
        pending_samples: list[dict[str, Any]] = []
        for source in SOURCES:
            pending_key = f"{source}:pending_returns"
            key_type = client.type(pending_key)
            pending_counts[f"{source}_key_exists"] = int(key_type == "zset")
            if key_type != "zset":
                continue
            pending_counts[f"{source}_members"] = client.zcard(pending_key)
            members = client.zrange(pending_key, 0, -1, withscores=True)
            for member, score in members:
                pending_counts["members_checked"] += 1
                identifier, separator, period = member.rpartition(":")
                if not separator or period not in PERIODS:
                    pending_counts["invalid_member_names"] += 1
                    continue
                pending_counts[f"{period}_members_checked"] += 1
                record = records_by_source_identifier.get((source, identifier))
                if record is None:
                    pending_counts["payload_not_found"] += 1
                    pending_counts[f"{period}_payload_not_found"] += 1
                    continue
                stored_end = record["stored_schedule"].get(period)
                if stored_end is None:
                    pending_counts["stored_end_missing"] += 1
                    pending_counts[f"{period}_stored_end_missing"] += 1
                    continue
                comparison = compare_pending_score(
                    stored_end=stored_end,
                    redis_score=score,
                    delay_seconds=delay_seconds,
                )
                comparison.update(
                    {
                        "source": source,
                        "member": member,
                        "period": period,
                    }
                )
                if comparison["score_matches"]:
                    pending_counts["scores_matching_end_plus_delay"] += 1
                    pending_counts[f"{period}_scores_matching"] += 1
                else:
                    pending_counts["scores_not_matching_end_plus_delay"] += 1
                    pending_counts[f"{period}_scores_not_matching"] += 1
                if (
                    len(pending_samples) < 18
                    and (
                        period == "hourly"
                        or not comparison["score_matches"]
                    )
                ):
                    pending_samples.append(comparison)
    finally:
        client.close()

    return {
        "commands_used": [
            "PING",
            "SCAN",
            "TYPE",
            "GET",
            "ZCARD",
            "ZRANGE",
        ],
        "production_delay_seconds_checked": delay_seconds,
        "counts": dict(sorted(counts.items())),
        "keys_by_namespace": dict(sorted(namespace_counts.items())),
        "hourly_transition_counts": dict(sorted(transition_counts.items())),
        "samples_by_namespace_and_session": dict(sorted(samples.items())),
        "pending_schedule": {
            "counts": dict(sorted(pending_counts.items())),
            "samples": pending_samples,
        },
        "errors": errors,
    }


def neo4j_rows(tx, query: str) -> list[dict[str, Any]]:
    return [record.data() for record in tx.run(query)]


def neo4j_single(tx, query: str) -> dict[str, Any]:
    record = tx.run(query).single(strict=True)
    return record.data()


def audit_neo4j_source(
    tx,
    *,
    query: str,
    source: str,
    sample_per_session: int,
) -> dict[str, Any]:
    classifier = cached_classifier()
    counts: Counter[str] = Counter()
    stored_sessions: Counter[str] = Counter()
    computed_sessions: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    samples: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    mismatch_samples: list[dict[str, Any]] = []
    end_before_event_samples: list[dict[str, Any]] = []
    error_samples: list[dict[str, Any]] = []

    result = tx.run(query)
    for row in result:
        counts["events_checked"] += 1
        identifier = str(row["identifier"])
        created = row["created"]
        if created is None:
            counts["created_missing"] += 1
            continue
        try:
            record = audit_timing_values(
                identifier=identifier,
                created=created,
                stored_market_session=row["market_session"],
                raw_schedule=row["returns_schedule"],
                periods=("hourly",),
                classifier=classifier,
            )
        except Exception as exc:
            counts["calculation_errors"] += 1
            if len(error_samples) < 20:
                error_samples.append(
                    {
                        "identifier": identifier,
                        "created": str(created),
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )
            continue

        record["relationship"] = {
            "type": row["relationship_type"],
            "symbol": row["symbol"],
            "created_at": row["relationship_created_at"],
        }
        record["event_node_times"] = {
            "created": row["node_created"],
            "updated": row["node_updated"],
        }
        node_created = row["node_created"]
        relationship_created = row["relationship_created_at"]
        node_matches_relationship = (
            same_instant(node_created, relationship_created)
            if node_created is not None and relationship_created is not None
            else None
        )
        record["checks"][
            "event_node_created_matches_relationship_created_at"
        ] = node_matches_relationship
        if node_matches_relationship is True:
            counts["node_created_matches_relationship_created_at"] += 1
        elif node_matches_relationship is False:
            counts["node_created_mismatches_relationship_created_at"] += 1
        else:
            counts["node_or_relationship_created_missing"] += 1

        increment_timing_counts(counts, record)
        stored_sessions[str(record["stored_market_session"])] += 1
        computed_sessions[record["computed_market_session"]] += 1
        transitions[record["hourly_transition"]] += 1
        session = record["computed_market_session"]
        if len(samples[session]) < sample_per_session:
            samples[session].append(
                audit_timing_values(
                    identifier=identifier,
                    created=created,
                    stored_market_session=row["market_session"],
                    raw_schedule=row["returns_schedule"],
                    classifier=classifier,
                )
            )
        if (
            record["checks"].get("stored_hourly_end_matches") is False
            and len(mismatch_samples) < 100
        ):
            mismatch_samples.append(record)
        if (
            record["checks"].get("hourly_end_before_event")
            and len(end_before_event_samples) < 100
        ):
            end_before_event_samples.append(record)

    return {
        "source": source,
        "counts": dict(sorted(counts.items())),
        "stored_market_sessions": dict(sorted(stored_sessions.items())),
        "computed_market_sessions": dict(sorted(computed_sessions.items())),
        "hourly_transition_counts": dict(sorted(transitions.items())),
        "samples_by_computed_session": dict(sorted(samples.items())),
        "hourly_schedule_mismatch_samples": mismatch_samples,
        "hourly_end_before_event_samples": end_before_event_samples,
        "calculation_error_samples": error_samples,
    }


def audit_neo4j(
    *,
    uri: str,
    username: str,
    password: str,
    sample_per_session: int,
) -> dict[str, Any]:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    source_results: dict[str, Any] = {}
    inventories: dict[str, Any] = {}
    try:
        driver.verify_connectivity()
        with driver.session(default_access_mode=READ_ACCESS) as session:
            for source, match_clause in NEO4J_PATTERNS.items():
                event_query = f"""
                {match_clause}
                RETURN coalesce(
                           toString(n.id),
                           toString(n.accessionNo),
                           elementId(n)
                       ) AS identifier,
                       toString(coalesce(r.created_at, n.created)) AS created,
                       toString(n.created) AS node_created,
                       toString(n.updated) AS node_updated,
                       toString(r.created_at) AS relationship_created_at,
                       type(r) AS relationship_type,
                       coalesce(r.symbol, c.ticker) AS symbol,
                       n.market_session AS market_session,
                       n.returns_schedule AS returns_schedule
                """
                source_results[source] = session.execute_read(
                    audit_neo4j_source,
                    query=event_query,
                    source=source,
                    sample_per_session=sample_per_session,
                )

                count_query = f"""
                {match_clause}
                RETURN count(r) AS relationships,
                       count(DISTINCT n) AS distinct_events
                """
                node_properties_query = f"""
                {match_clause}
                WITH DISTINCT n
                UNWIND keys(n) AS property
                RETURN property, count(*) AS nodes
                ORDER BY property
                """
                relationship_properties_query = f"""
                {match_clause}
                UNWIND keys(r) AS property
                RETURN property, count(*) AS relationships
                ORDER BY property
                """
                inventories[source] = {
                    "coverage": session.execute_read(
                        neo4j_single,
                        count_query,
                    ),
                    "event_node_properties": session.execute_read(
                        neo4j_rows,
                        node_properties_query,
                    ),
                    "return_relationship_properties": session.execute_read(
                        neo4j_rows,
                        relationship_properties_query,
                    ),
                }
    finally:
        driver.close()

    aggregate: Counter[str] = Counter()
    for source_result in source_results.values():
        for key, value in source_result["counts"].items():
            if isinstance(value, int):
                aggregate[key] += value

    return {
        "access_rule": (
            "Every query used a READ_ACCESS session and execute_read."
        ),
        "aggregate_counts": dict(sorted(aggregate.items())),
        "sources": source_results,
        "storage_inventory": inventories,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-redis", action="store_true")
    parser.add_argument("--skip-neo4j", action="store_true")
    parser.add_argument(
        "--delay-seconds",
        type=int,
        default=PRODUCTION_DELAY_SECONDS,
    )
    parser.add_argument("--sample-per-group", type=int, default=2)
    args = parser.parse_args()
    if args.skip_redis and args.skip_neo4j:
        raise SystemExit("At least one store must be checked")

    output: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "production_code_imported_read_only": (
            "utils.market_session.MarketSessionClassifier"
        ),
        "storage_model": {
            "saved": (
                "Each return relationship saves created_at, the exact event "
                "time attached to its return values. News and Report nodes "
                "also save market-session and hourly/session/daily end times."
            ),
            "not_saved": (
                "Separate start-price timestamps or the actual Massive bar "
                "timestamps selected after backward fallback."
            ),
            "reconstruction": (
                "This audit calls the current production market-session helper "
                "to rebuild each start and end from relationship.created_at. "
                "It separately checks the event node's created field because "
                "News updates can leave that node field stale."
            ),
        },
        "safety": (
            "No Redis or Neo4j write command was used. Connection credentials "
            "are read from environment variables and omitted from this file."
        ),
    }

    if not args.skip_redis:
        output["redis"] = audit_redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            database=int(os.environ.get("REDIS_DB", "0")),
            password=os.environ.get("REDIS_PASSWORD") or None,
            delay_seconds=args.delay_seconds,
            sample_per_group=args.sample_per_group,
        )

    if not args.skip_neo4j:
        uri = os.environ.get("NEO4J_URI")
        username = os.environ.get("NEO4J_USERNAME")
        password = os.environ.get("NEO4J_PASSWORD")
        if not all((uri, username, password)):
            raise SystemExit("Neo4j environment variables are required")
        output["neo4j"] = audit_neo4j(
            uri=uri,
            username=username,
            password=password,
            sample_per_session=args.sample_per_group,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
