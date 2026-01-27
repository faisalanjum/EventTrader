#!/usr/bin/env python3
"""
Test: Do forked skills called from SDK have TaskCreate/List/Get/Update tools?

This is an empirical test to settle the question definitively.

IMPORTANT: This test uses a SEPARATE output file (FROM-SDK.txt) to avoid
confusion with CLI tests (which use FROM-CLI.txt).
"""
import asyncio
import os
import sys
from datetime import datetime

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

# SEPARATE output file for SDK tests
OUTPUT_FILE = "earnings-analysis/test-outputs/task-tools-FROM-SDK.txt"

async def run_test():
    print("=" * 70)
    print("EMPIRICAL TEST: Task Tools in SDK-Called Forked Skills")
    print("=" * 70)

    # Clean previous output
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
        print(f"Deleted previous: {OUTPUT_FILE}")

    timestamp = datetime.now().isoformat()

    print(f"\nTimestamp: {timestamp}")
    print(f"Output file: {OUTPUT_FILE}")
    print("Calling /test-sdk-task-tools FROM-SDK.txt via SDK...")
    print("-" * 70)

    full_output = []

    async for message in query(
        prompt="Run /test-sdk-task-tools FROM-SDK.txt - this passes 'FROM-SDK.txt' as the output filename argument.",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=10,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(message, 'result'):
            full_output.append(str(message.result))
            print(f"SDK Output: {message.result[:200]}..." if len(str(message.result)) > 200 else f"SDK Output: {message.result}")

    print("-" * 70)

    # Check results
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            content = f.read()
        print("\n=== OUTPUT FILE CONTENT ===")
        print(content)
        print("=== END OUTPUT FILE ===\n")

        if "TASKLIST_AVAILABLE: YES" in content:
            print("RESULT: TaskList IS available in SDK-called forked skills")
            return True
        elif "TASKLIST_AVAILABLE: NO" in content:
            print("RESULT: TaskList is NOT available in SDK-called forked skills")
            return False
        else:
            print("RESULT: Inconclusive - check output file")
            return None
    else:
        print(f"ERROR: Output file {OUTPUT_FILE} was not created")
        print("Full SDK output:")
        for o in full_output:
            print(o)
        return None

if __name__ == "__main__":
    try:
        result = asyncio.run(run_test())
        print("\n" + "=" * 70)
        if result is True:
            print("CONCLUSION: Forked skills from SDK DO have Task tools")
        elif result is False:
            print("CONCLUSION: Forked skills from SDK do NOT have Task tools")
        else:
            print("CONCLUSION: Test inconclusive - manual review needed")
        print("=" * 70)
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
