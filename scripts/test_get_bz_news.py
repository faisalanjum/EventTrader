#!/usr/bin/env python3
"""Test get-bz-news skill via Claude SDK."""

import subprocess
import sys
import time

def run_skill(ticker: str, start: str, end: str, threshold: str = "1.5s"):
    """Run get-bz-news skill and measure time."""
    args = f"{ticker} {start} {end} {threshold}"
    cmd = ["claude", "-p", f"/get-bz-news {args}", "--output-format", "text"]

    print(f"\n{'='*60}")
    print(f"Running: /get-bz-news {args}")
    print(f"{'='*60}")

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/faisal/EventMarketDB")
    elapsed = time.time() - start_time

    print(f"\nCompleted in {elapsed:.2f}s")
    print(f"\nOutput:\n{result.stdout[:2000]}...")  # Truncate for readability

    if result.returncode != 0:
        print(f"\nError: {result.stderr}")

    return elapsed, result.stdout

def main():
    # Test cases with different date ranges (different volatility windows)
    test_cases = [
        ("NVDA", "2024-01-01T00:00:00", "2024-03-01T00:00:00", "1.5s"),
        ("NVDA", "2024-04-01T00:00:00", "2024-06-01T00:00:00", "1.5s"),  # Different vol window
        ("AAPL", "2024-01-01T00:00:00", "2024-06-01T00:00:00", "2s"),    # Higher threshold
    ]

    if len(sys.argv) > 1:
        # Custom args: python test_get_bz_news.py TICKER START END [THRESHOLD]
        ticker = sys.argv[1]
        start = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01T00:00:00"
        end = sys.argv[3] if len(sys.argv) > 3 else "2024-06-01T00:00:00"
        threshold = sys.argv[4] if len(sys.argv) > 4 else "1.5s"
        test_cases = [(ticker, start, end, threshold)]

    results = []
    for ticker, start, end, threshold in test_cases:
        elapsed, output = run_skill(ticker, start, end, threshold)
        results.append((ticker, start, threshold, elapsed))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for ticker, start, threshold, elapsed in results:
        print(f"{ticker} ({start[:10]}, {threshold}): {elapsed:.2f}s")

if __name__ == "__main__":
    main()
