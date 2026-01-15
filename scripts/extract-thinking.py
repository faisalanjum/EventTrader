#!/usr/bin/env python3
"""
Extract thinking blocks from Claude Code transcript files.

Usage:
    python3 extract-thinking.py <transcript.jsonl>
    python3 extract-thinking.py ~/.claude/projects/*/session-id.jsonl
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def extract_thinking(filepath: str, max_chars: int = 5000):
    """Extract all thinking blocks from a transcript file."""

    filepath = Path(filepath).expanduser()
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return

    print(f"\n{'='*60}")
    print(f"Transcript: {filepath.name}")
    print(f"{'='*60}\n")

    thinking_count = 0

    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())

                # Check if this is an assistant message with content
                if data.get('type') != 'assistant':
                    continue

                message = data.get('message', {})
                content = message.get('content', [])

                if not isinstance(content, list):
                    continue

                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'thinking':
                        thinking_count += 1
                        thinking_text = block.get('thinking', '')
                        timestamp = data.get('timestamp', 'unknown')

                        print(f"--- Thinking Block #{thinking_count} ---")
                        print(f"Timestamp: {timestamp}")
                        print(f"Length: {len(thinking_text)} chars")
                        print()

                        # Print thinking (truncated if too long)
                        if len(thinking_text) > max_chars:
                            print(thinking_text[:max_chars])
                            print(f"\n... [truncated, {len(thinking_text) - max_chars} more chars]")
                        else:
                            print(thinking_text)

                        print(f"\n{'─'*40}\n")

            except json.JSONDecodeError:
                continue

    if thinking_count == 0:
        print("No thinking blocks found in this transcript.")
    else:
        print(f"\nTotal thinking blocks found: {thinking_count}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample:")
        print("  python3 extract-thinking.py ~/.claude/projects/-home-faisal-EventMarketDB/*.jsonl")
        sys.exit(1)

    for filepath in sys.argv[1:]:
        extract_thinking(filepath)


if __name__ == "__main__":
    main()
