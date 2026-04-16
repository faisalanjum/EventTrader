#!/usr/bin/env python3
"""Test: Can an SDK session with embedded prompt (not /skill-name) spawn Data SubAgents?

This tests the "embed" invocation pattern where learner SKILL.md content is
passed as raw prompt text, giving the session main-session tool access
(including Agent tool for Data SubAgent spawning).
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

async def main():
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError:
        print("ERROR: claude_agent_sdk not available")
        return

    prompt = """You are testing Data SubAgent access from an SDK session with embedded prompt.

IMPORTANT: Do NOT use /slash commands. Use the Agent tool directly to spawn sub-agents.

Do these steps IN ORDER and write results to earnings-analysis/test-outputs/test-sdk-embed-datasub.json:

STEP 1: Check your tool inventory. Do you have the "Agent" tool? Report YES or NO.
Also count your total built-in tools (exclude MCP).

STEP 2: If Agent tool available, spawn a neo4j-report sub-agent with prompt:
"Get one AAPL 8-K filing. Return only accession_number, ticker, form_type. Minimal response."
Record: success or failed, plus a 1-line evidence snippet.

STEP 3: If Agent tool available, spawn a neo4j-news sub-agent with prompt:
"Get one recent AAPL earnings headline. Return only title and date. Minimal response."
Record: success or failed.

STEP 4: If Agent tool available, spawn a perplexity-ask sub-agent with prompt:
"What was AAPL's Q1 FY2025 EPS? One sentence answer."
Record: success or failed.

STEP 5: Write the final JSON result file. Shape:
{
  "test": "sdk-embed-datasub",
  "invocation_mode": "embedded_prompt",
  "agent_tool_available": true/false,
  "builtin_tool_count": N,
  "results": [
    {"agent": "neo4j-report", "status": "success|failed", "evidence": "..."},
    {"agent": "neo4j-news", "status": "success|failed", "evidence": "..."},
    {"agent": "perplexity-ask", "status": "success|failed", "evidence": "..."}
  ]
}

After writing the file, stop immediately.
"""

    print("Starting SDK embed test...", flush=True)
    final = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=20,
        ),
    ):
        if hasattr(msg, "result"):
            final = str(msg.result)

    print(f"SDK embed test done. Result: {final}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
