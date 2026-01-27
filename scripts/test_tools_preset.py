#!/usr/bin/env python3
"""
Test: Does tools preset 'claude_code' include TaskCreate/List/Get/Update?

This tests whether using:
    tools={"type": "preset", "preset": "claude_code"}

Gives SDK sessions access to the full Claude Code tool set including
TaskCreate, TaskList, TaskGet, TaskUpdate.
"""
import asyncio
import os
from datetime import datetime

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_FILE = "earnings-analysis/test-outputs/tools-preset-test.txt"

async def run_test():
    print("=" * 70)
    print("TEST: Does 'claude_code' tools preset include Task management tools?")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Output file: {OUTPUT_FILE}")
    print("-" * 70)

    # Clean previous output
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    full_output = []

    prompt = """You are testing tool availability. Do these steps IN ORDER:

1. First, write to file 'earnings-analysis/test-outputs/tools-preset-test.txt' with header:
   ```
   TEST: tools preset claude_code
   TIMESTAMP: {current ISO timestamp}
   ```

2. Check if TaskList tool is available by trying to call it.
   - If it works, append to the file: "TASKLIST_AVAILABLE: YES" and include the output
   - If it fails or doesn't exist, append: "TASKLIST_AVAILABLE: NO" and the error

3. Check if TaskCreate tool is available by trying to create a task with subject "PRESET-TEST-TASK".
   - If it works, append: "TASKCREATE_AVAILABLE: YES" and the task ID
   - If it fails, append: "TASKCREATE_AVAILABLE: NO" and the error

4. List ALL tools you have access to and append them to the file under "AVAILABLE_TOOLS:"

5. Return a summary of findings."""

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                tools={"type": "preset", "preset": "claude_code"},  # KEY TEST
                setting_sources=["project"],
                max_turns=15,
                permission_mode="bypassPermissions",
            )
        ):
            if hasattr(message, 'result'):
                full_output.append(str(message.result))
                print(f"\nSDK Result: {message.result}")
            elif hasattr(message, 'content'):
                # Print tool usage for visibility
                for block in message.content:
                    if hasattr(block, 'name'):
                        print(f"  Tool used: {block.name}")

    except Exception as e:
        print(f"ERROR during query: {e}")
        import traceback
        traceback.print_exc()
        return None

    print("-" * 70)

    # Check results
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            content = f.read()
        print("\n" + "=" * 70)
        print("OUTPUT FILE CONTENT:")
        print("=" * 70)
        print(content)
        print("=" * 70)

        if "TASKLIST_AVAILABLE: YES" in content:
            print("\n✅ RESULT: TaskList IS available with claude_code preset!")
            return True
        elif "TASKLIST_AVAILABLE: NO" in content:
            print("\n❌ RESULT: TaskList is NOT available even with claude_code preset")
            return False
        else:
            print("\n⚠️  RESULT: Inconclusive - check output")
            return None
    else:
        print(f"\nERROR: Output file {OUTPUT_FILE} was not created")
        print("Full SDK output:")
        for o in full_output:
            print(o)
        return None


if __name__ == "__main__":
    result = asyncio.run(run_test())
    print("\n" + "=" * 70)
    if result is True:
        print("CONCLUSION: 'claude_code' tools preset DOES include Task tools!")
        print("Update Infrastructure.md - SDK CAN have task tools with preset")
    elif result is False:
        print("CONCLUSION: 'claude_code' tools preset does NOT include Task tools")
        print("Original finding confirmed - task tools are CLI-only")
    else:
        print("CONCLUSION: Test inconclusive - manual review needed")
    print("=" * 70)
