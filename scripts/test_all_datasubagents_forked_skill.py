#!/usr/bin/env python3
"""
Validate whether a forked skill can invoke the full data-subagent surface.

Flow:
SDK/main -> /test-all-datasubagents-fork -> per-subagent slash command calls
"""
import asyncio
import json
import os
from pathlib import Path

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import ClaudeAgentOptions, query

OUTPUT_JSON = Path("earnings-analysis/test-outputs/test-all-datasubagents-fork.json")
OUTPUT_TXT = Path("earnings-analysis/test-outputs/test-all-datasubagents-fork.txt")


async def run_test():
    print("=" * 72)
    print("TEST: Forked Skill -> Full Data-SubAgent Surface")
    print("=" * 72)
    print("Invoking /test-all-datasubagents-fork ...")

    if OUTPUT_JSON.exists():
        OUTPUT_JSON.unlink()
    if OUTPUT_TXT.exists():
        OUTPUT_TXT.unlink()

    tool_names = []
    final_text = []

    async for message in query(
        prompt="/test-all-datasubagents-fork",
        options=ClaudeAgentOptions(
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=120,
        ),
    ):
        if hasattr(message, "data"):
            data = message.data
            if data.get("type") == "tool_use":
                name = data.get("name", "")
                if name:
                    tool_names.append(name)
                    print(f"[TOOL] {name}")

        if hasattr(message, "result"):
            chunk = str(message.result)
            final_text.append(chunk)
            if chunk:
                print(f"[OUTPUT] {chunk[:240]}...")

    print("\n" + "-" * 72)
    print(f"Tool uses observed: {tool_names}")

    if not OUTPUT_JSON.exists():
        print(f"❌ Expected report not found: {OUTPUT_JSON}")
        return False

    try:
        payload = json.loads(OUTPUT_JSON.read_text())
    except Exception as exc:
        print(f"❌ Could not parse JSON report: {exc}")
        return False

    results = payload.get("results") or []
    summary = payload.get("summary") or {}
    ok = summary.get("invoke_ok_count")
    failed = summary.get("invoke_failed_count")

    print(f"Report file: {OUTPUT_JSON}")
    print(f"Summary: invoke_ok={ok}, invoke_failed={failed}, total={summary.get('total')}")

    print("\nPer-agent results:")
    for item in results:
        name = item.get("name", "?")
        status = item.get("invocation_status", "?")
        outcome = item.get("outcome_type", "?")
        evidence = (item.get("evidence", "") or "").replace("\n", " ")
        print(f"- {name}: {status} | {outcome} | {evidence[:140]}")

    expected = {
        "neo4j-report",
        "neo4j-transcript",
        "neo4j-xbrl",
        "neo4j-entity",
        "neo4j-news",
        "neo4j-vector-search",
        "alphavantage-earnings",
        "yahoo-earnings",
        "bz-news-api",
        "perplexity-search",
        "perplexity-ask",
        "perplexity-reason",
        "perplexity-research",
        "perplexity-sec",
    }
    seen = {item.get("name") for item in results}
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)

    checks = {
        "JSON report exists": True,
        "All 14 agents represented": not missing and not extra,
        "Summary total is 14": summary.get("total") == 14,
        "No invocation failures": summary.get("invoke_failed_count") == 0,
    }

    print("\nChecks:")
    all_pass = True
    for label, passed in checks.items():
        print(f"{'✅' if passed else '❌'} {label}")
        if not passed:
            all_pass = False

    if missing:
        print(f"Missing entries: {missing}")
    if extra:
        print(f"Unexpected entries: {extra}")

    print("-" * 72)
    print("✅ PASS" if all_pass else "⚠️ PARTIAL / FAIL")
    return all_pass


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(run_test()) else 1)
