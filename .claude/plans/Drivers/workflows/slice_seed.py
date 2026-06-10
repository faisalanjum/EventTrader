#!/usr/bin/env python3
"""
§11.11 deterministic seed slicer — the PROVEN reconcile.js review-batch slicing, extracted
VERBATIM from the reconcile.js Slice agent's python heredoc into a tested CLI (the bound
enforcement lives here, the proven slicer; fold_catalogs.py part-a is now a pure-python WARN).

slice_seed.py <run_dir>
    Reads <run_dir>/seed.json ({industry, catalog:[...], analysis}). Slices catalog[] into
    name-sorted CONTIGUOUS review batches under the §11.11 caps (<=400 records, <=300000 chars
    per batch — the seed's records are already sorted by driver_name, so contiguous slices stay
    name-sorted). Cross-batch SAME_AS misses = the ACCEPTED residual (under-merge, safe
    direction; late-duplicate repair is the catch-up). Writes seed_batch_001.json ... and prints
    a one-line JSON {"ok":true,"files":[...],"notes":"..."} the Slice agent relays VERBATIM.
    EDGE: a SINGLE record bigger than the char cap goes ALONE into its own batch (a record is
    never split); the notes record that.
"""
import json
import sys
from pathlib import Path

MAX_RECORDS = 400        # §11.11 [OWNER]
MAX_CHARS = 300_000      # §11.11 [OWNER] — full serialized records, not the AI view


def rec_chars(records):
    """Serialized char size of a record list, the §11.11 metric (compact, matches the guard)."""
    return sum(len(json.dumps(r, separators=(",", ":"), ensure_ascii=False)) for r in records)


def slice_records(recs, max_records=MAX_RECORDS, max_chars=MAX_CHARS):
    """Name-sorted contiguous batches under the caps (VERBATIM from the reconcile heredoc).
    A single record bigger than the char cap lands alone (the flush check fires on the NEXT
    record, so an oversize record is never split nor co-located)."""
    batches, cur, chars = [], [], 0
    for r in recs:
        s = len(json.dumps(r, separators=(",", ":"), ensure_ascii=False))
        if cur and (len(cur) >= max_records or chars + s > max_chars):
            batches.append(cur)
            cur, chars = [], 0
        cur.append(r)
        chars += s
    if cur:
        batches.append(cur)
    return batches


def slice_seed(run_dir, max_records=MAX_RECORDS, max_chars=MAX_CHARS):
    run = Path(run_dir)
    d = json.load(open(run / "seed.json"))
    recs = d.get("catalog") or []
    batches = slice_records(recs, max_records, max_chars)
    files = []
    for i, b in enumerate(batches, 1):
        p = run / ("seed_batch_%03d.json" % i)
        p.write_text(json.dumps({"industry": d.get("industry"), "catalog": b, "analysis": {}},
                                indent=1, ensure_ascii=False) + "\n")
        files.append(str(p))
    sizes = [len(b) for b in batches]
    fat = [b[0].get("driver_name") for b in batches
           if len(b) == 1 and rec_chars(b) > max_chars]
    notes = f"sizes={sizes}"
    if fat:
        notes += f"; oversize single record(s) isolated alone (never split): {fat}"
    return {"ok": True, "files": files, "notes": notes}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Usage: slice_seed.py <run_dir>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(slice_seed(argv[0])))


if __name__ == "__main__":
    main()
