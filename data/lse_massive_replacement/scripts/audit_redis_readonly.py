#!/usr/bin/env python3
"""Read-only inventory of return data currently present in Redis.

Only non-mutating Redis commands are used: PING, SCAN, TYPE, GET, ZCARD,
ZRANGE, TTL, and DBSIZE. No project Redis wrapper is imported because its
constructor performs initialization writes.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import redis


SOURCES = ("news", "reports", "transcripts")


def namespace(key: str) -> str:
    parts = key.split(":")
    if key.startswith("tracking:meta:") and len(parts) >= 4:
        return ":".join(parts[:3]) + ":*"
    if len(parts) >= 3 and parts[1] in ("withreturns", "withoutreturns"):
        return ":".join(parts[:2]) + ":*"
    if len(parts) >= 4 and parts[2] in ("withreturns", "withoutreturns"):
        return ":".join(parts[:3]) + ":*"
    if key.endswith("pending_returns"):
        return key
    return ":".join(parts[: min(4, len(parts))]) + (":*" if len(parts) > 4 else "")


def shape_of_json(raw: str) -> dict[str, Any]:
    try:
        item = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"valid_json": False}
    if not isinstance(item, dict):
        return {"valid_json": True, "json_type": type(item).__name__}

    metadata = item.get("metadata")
    returns = item.get("returns")
    result: dict[str, Any] = {
        "valid_json": True,
        "top_level_fields": sorted(item),
        "has_metadata": isinstance(metadata, dict),
        "has_returns": isinstance(returns, dict),
    }
    if isinstance(metadata, dict):
        result["metadata_fields"] = sorted(metadata)
        instruments = metadata.get("instruments")
        result["instrument_count"] = len(instruments) if isinstance(instruments, list) else None
        schedule = metadata.get("returns_schedule")
        result["returns_schedule_fields"] = (
            sorted(schedule) if isinstance(schedule, dict) else None
        )
    if isinstance(returns, dict):
        symbols = returns.get("symbols", returns)
        if isinstance(symbols, dict):
            result["return_symbol_count"] = len(symbols)
            return_shapes: Counter[tuple[str, ...]] = Counter()
            leaf_fields: Counter[tuple[str, ...]] = Counter()
            null_leaves = 0
            populated_leaves = 0
            for symbol_data in symbols.values():
                if not isinstance(symbol_data, dict):
                    continue
                return_shapes[tuple(sorted(symbol_data))] += 1
                for period_data in symbol_data.values():
                    if isinstance(period_data, dict):
                        leaf_fields[tuple(sorted(period_data))] += 1
                        for value in period_data.values():
                            if value is None:
                                null_leaves += 1
                            else:
                                populated_leaves += 1
                    elif period_data is None:
                        null_leaves += 1
            result["return_period_field_shapes"] = [
                {"fields": list(fields), "symbols": count}
                for fields, count in return_shapes.items()
            ]
            result["return_leaf_field_shapes"] = [
                {"fields": list(fields), "periods": count}
                for fields, count in leaf_fields.items()
            ]
            result["null_return_leaves"] = null_leaves
            result["populated_return_leaves"] = populated_leaves
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    host = os.environ.get("REDIS_HOST", "localhost")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    client = redis.Redis(
        host=host,
        port=port,
        db=int(os.environ.get("REDIS_DB", "0")),
        password=os.environ.get("REDIS_PASSWORD") or None,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=30,
    )
    client.ping()

    counts: Counter[str] = Counter()
    samples: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[str] = set()

    for pattern in ("*returns*", "tracking:meta:*"):
        for key in client.scan_iter(match=pattern, count=2000):
            if key in seen:
                continue
            seen.add(key)
            group = namespace(key)
            counts[group] += 1
            if len(samples[group]) >= 3:
                continue
            key_type = client.type(key)
            sample: dict[str, Any] = {
                "key": key,
                "type": key_type,
                "ttl_seconds": client.ttl(key),
            }
            if key_type == "string":
                raw = client.get(key)
                if raw is not None:
                    sample["bytes"] = len(raw.encode("utf-8"))
                    sample["json_shape"] = shape_of_json(raw)
            elif key_type == "zset":
                sample["members"] = client.zcard(key)
                sample["first_with_score"] = client.zrange(key, 0, 0, withscores=True)
                sample["last_with_score"] = client.zrange(key, -1, -1, withscores=True)
            elif key_type == "hash":
                sample["fields"] = sorted(client.hkeys(key))
            samples[group].append(sample)

    pending: dict[str, Any] = {}
    for source in SOURCES:
        key = f"{source}:pending_returns"
        key_type = client.type(key)
        pending[key] = {"type": key_type}
        if key_type == "zset":
            pending[key].update(
                {
                    "members": client.zcard(key),
                    "first_with_score": client.zrange(key, 0, 0, withscores=True),
                    "last_with_score": client.zrange(key, -1, -1, withscores=True),
                }
            )

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "safety": (
            "Only PING, SCAN, TYPE, GET, ZCARD, ZRANGE, TTL, HKEYS, and DBSIZE "
            "were used."
        ),
        "database_size_keys": client.dbsize(),
        "matched_unique_keys": len(seen),
        "counts_by_namespace": dict(sorted(counts.items())),
        "samples_by_namespace": dict(sorted(samples.items())),
        "pending_sets": pending,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"matched {len(seen)} keys across {len(counts)} namespaces")
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
