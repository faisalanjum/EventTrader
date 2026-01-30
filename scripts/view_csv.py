#!/usr/bin/env python3
"""View pipe-delimited CSV with aligned columns. Usage: python scripts/view_csv.py <file.csv>"""
import sys

def view(path, delim="|", max_w=35):
    rows = [l.strip().split(delim) for l in open(path) if l.strip()]
    widths = [min(max(len(r[i]) if i < len(r) else 0 for r in rows), max_w) for i in range(len(rows[0]))]

    for i, row in enumerate(rows):
        print("| " + " | ".join((c[:max_w-2]+".." if len(c)>max_w else c).ljust(w) for c, w in zip(row, widths)) + " |")
        if i == 0:
            print("+" + "+".join("-"*(w+2) for w in widths) + "+")

if __name__ == "__main__":
    view(sys.argv[1]) if len(sys.argv) > 1 else print("Usage: python view_csv.py <file.csv>")
