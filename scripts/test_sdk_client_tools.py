#!/usr/bin/env python3
"""
Test: Does ClaudeSDKClient (streaming mode, no --print) have TaskCreate/TaskList?
"""
import asyncio
import os
os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

OUTPUT_FILE = "earnings-analysis/test-outputs/sdk-client-tools.txt"

async def run_test():
    print("Testing ClaudeSDKClient (streaming mode, no --print flag)")
    print("-" * 60)

    options = ClaudeAgentOptions(
        tools={"type": "preset", "preset": "claude_code"},
        permission_mode="bypassPermissions",
        max_turns=5,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(f"""Write to file '{OUTPUT_FILE}' with:
1. HEADER: "SDK_CLIENT_TEST (streaming mode)"
2. Try to call TaskList - report if it works or not
3. Try to call TaskCreate with subject "CLIENT-TEST" - report if it works or not
4. List ALL available tools you have
Be concise. Just facts.""")

        async for message in client.receive_response():
            if hasattr(message, 'result'):
                print(f"Result: {message.result}")
            elif hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'name'):
                        print(f"  Tool: {block.name}")

    # Check output
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            print("\n" + "=" * 60)
            print("OUTPUT FILE:")
            print("=" * 60)
            print(f.read())

asyncio.run(run_test())
