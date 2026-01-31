#!/usr/bin/env python3
"""Get presentations for a ticker in date range (exclusive). Placeholder - not yet implemented."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, error, ok
load_env()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_presentations_range.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]
    print(ok("NO_PRESENTATIONS", f"No presentations found for {ticker} {start}->{end}"))
