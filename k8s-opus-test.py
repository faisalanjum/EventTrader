#!/usr/bin/env python3
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def run():
    print('Starting Opus K8s test...')
    try:
        async for msg in query(
            prompt='''Run /earnings-prediction for ticker ALKS, accession 0000950170-25-099382.

Write your complete prediction analysis to: earnings-analysis/Companies/ALKS/0000950170-25-099382.md

IMPORTANT: Add this header at the top of the file:
# K8S_OPUS_THINKING_TEST

Include all analysis sections as specified in the skill.''',
            options=ClaudeAgentOptions(
                model='claude-opus-4-5-20251101',
                setting_sources=['user', 'project'],
                max_turns=50,
                permission_mode='bypassPermissions',
            )
        ):
            print(f'Got: {type(msg).__name__}')
        print('Test complete!')
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(run())
