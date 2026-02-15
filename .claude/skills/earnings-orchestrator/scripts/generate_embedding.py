#!/usr/bin/env python3
"""
Generate a 3072-dim embedding using OpenAI text-embedding-3-large.

Usage:
    python3 .claude/skills/earnings-orchestrator/scripts/generate_embedding.py "your search query text"

Output:
    JSON array of 3072 floats on stdout.
    On error: ERROR|CODE|message
"""
# /// script
# dependencies = ["openai", "python-dotenv"]
# ///
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=True)


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("ERROR|USAGE|generate_embedding.py 'query text'")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR|CONFIG|OPENAI_API_KEY not set in .env")
        sys.exit(1)

    from openai import OpenAI

    try:
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=sys.argv[1],
            dimensions=3072,
        )
        print(json.dumps(response.data[0].embedding))
    except Exception as e:
        print(f"ERROR|OPENAI|{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
