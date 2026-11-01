#!/usr/bin/env python3
"""Diff two Fiscal.ai scrape runs: added / removed / restated KPI rows.

Usage:
    python3 scripts/fiscal_ai_diff_runs.py PREV.sqlite CURR.sqlite --out-dir DIR
    python3 scripts/fiscal_ai_diff_runs.py --self-check

Row identity is the fiscal_segments primary key:
    (company_slug, period_type, metric_key, period_end_date)

Both databases are opened read-only.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

# ponytail: run_id / scraped_at / source_url (embeds the Next.js build id) and
# exchange_rate -> value_usd / value_millions_usd change on EVERY run regardless
# of whether the data moved. Equality is value_native + currency_native only.
JOIN_ON = " AND ".join(
    f"p.{c} = c.{c}"
    for c in ("company_slug", "period_type", "metric_key", "period_end_date")
)
NOT_EXISTS = """
    SELECT 1 FROM {other}.fiscal_segments x
    WHERE x.company_slug = t.company_slug AND x.period_type = t.period_type
      AND x.metric_key = t.metric_key AND x.period_end_date = t.period_end_date
"""
ONLY_IN = """
    SELECT t.symbol, t.company_slug, t.period_type, t.section, t.metric_name,
           t.metric_key, t.period_end_date, t.currency_native, t.value_native
    FROM {side}.fiscal_segments t
    WHERE NOT EXISTS (%s)
""" % NOT_EXISTS

OVERLAP = f"""
    SELECT p.symbol, p.company_slug, p.period_type, p.section, p.metric_name,
           p.metric_key, p.period_end_date,
           p.currency_native, c.currency_native,
           p.value_native, c.value_native
    FROM prev.fiscal_segments p
    JOIN curr.fiscal_segments c ON {JOIN_ON}
    WHERE p.value_native IS NOT c.value_native
       OR p.currency_native IS NOT c.currency_native
"""

CSV_HEADER = [
    "symbol", "company_slug", "period_type", "section", "metric_name",
    "metric_key", "period_end_date", "currency_prev", "currency_curr",
    "value_prev", "value_curr", "pct_change", "kind",
]


def changed(old, new, tol: float) -> bool:
    """True if the two values differ beyond a relative tolerance."""
    if old is None or new is None:
        return old is not new
    if tol <= 0:
        return old != new
    scale = max(abs(old), abs(new))
    return abs(new - old) > tol * scale if scale else False


def pct(old, new):
    if old in (None, 0) or new is None:
        return ""
    return round((new - old) / abs(old) * 100, 4)


def attach(prev: Path, curr: Path) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:", uri=True)
    for alias, path in (("prev", prev), ("curr", curr)):
        con.execute("ATTACH DATABASE ? AS " + alias, (f"file:{path}?mode=ro",))
    return con


def diff(con: sqlite3.Connection, tol: float):
    rows: list[list] = []

    for kind, side, other in (("removed", "prev", "curr"), ("added", "curr", "prev")):
        for r in con.execute(ONLY_IN.format(side=side, other=other)):
            sym, slug, per, sec, name, key, end, cur, val = r
            prev_v, curr_v = (val, None) if kind == "removed" else (None, val)
            rows.append([sym, slug, per, sec, name, key, end, cur, cur,
                         prev_v, curr_v, "", kind])

    for r in con.execute(OVERLAP):
        sym, slug, per, sec, name, key, end, cur_p, cur_c, val_p, val_c = r
        if cur_p != cur_c:
            kind = "currency_changed"
        elif changed(val_p, val_c, tol):
            kind = "restated"
        else:
            continue  # within tolerance
        rows.append([sym, slug, per, sec, name, key, end, cur_p, cur_c,
                     val_p, val_c, pct(val_p, val_c), kind])

    return rows


def symbols(con: sqlite3.Connection, alias: str) -> set[str]:
    return {s for (s,) in con.execute(f"SELECT DISTINCT symbol FROM {alias}.fiscal_segments")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prev", nargs="?", type=Path, help="baseline fiscal_segments.sqlite")
    ap.add_argument("curr", nargs="?", type=Path, help="new run fiscal_segments.sqlite")
    ap.add_argument("--out-dir", type=Path, help="write <kind>.csv here")
    ap.add_argument("--tol", type=float, default=0.0,
                    help="relative tolerance; 0 = exact (default)")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return self_check()
    if not args.prev or not args.curr:
        ap.error("prev and curr are required")

    con = attach(args.prev, args.curr)
    rows = diff(con, args.tol)

    counts: dict[str, int] = {}
    for r in rows:
        counts[r[-1]] = counts.get(r[-1], 0) + 1

    only_prev = symbols(con, "prev") - symbols(con, "curr")
    only_curr = symbols(con, "curr") - symbols(con, "prev")

    print(f"prev: {args.prev}\ncurr: {args.curr}\ntol:  {args.tol}\n")
    for kind in ("restated", "currency_changed", "added", "removed"):
        print(f"  {kind:18} {counts.get(kind, 0):>9,}")
    print(f"\n  symbols lost       {len(only_prev):>9,}  {sorted(only_prev)[:10]}")
    print(f"  symbols gained     {len(only_curr):>9,}  {sorted(only_curr)[:10]}")

    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for kind in counts:
            path = args.out_dir / f"{kind}.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(CSV_HEADER)
                w.writerows(r for r in rows if r[-1] == kind)
            print(f"\nwrote {path} ({counts[kind]:,} rows)")
    return 0


def self_check() -> int:
    con = sqlite3.connect(":memory:")
    for alias in ("prev", "curr"):
        con.execute(f"ATTACH ':memory:' AS {alias}")
        con.execute(f"""CREATE TABLE {alias}.fiscal_segments (
            symbol TEXT, company_slug TEXT, period_type TEXT, section TEXT,
            metric_name TEXT, metric_key TEXT, period_end_date TEXT,
            currency_native TEXT, value_native REAL)""")

    def ins(alias, key, val, cur="USD"):
        con.execute(f"INSERT INTO {alias}.fiscal_segments VALUES ('S','NYSE-S','annual','Seg','M',?,'2024-12-31',?,?)",
                    (key, cur, val))

    ins("prev", "same", 100.0);            ins("curr", "same", 100.0)
    ins("prev", "restated", 100.0);        ins("curr", "restated", 110.0)
    ins("prev", "gone", 1.0)
    ins("curr", "fresh", 2.0)
    ins("prev", "fx", 5.0, "CAD");         ins("curr", "fx", 5.0, "USD")
    ins("prev", "wasnull", None);          ins("curr", "wasnull", 7.0)
    ins("prev", "rounded", 100.0);         ins("curr", "rounded", 100.001)

    kinds = lambda tol: sorted((r[5], r[-1]) for r in diff(con, tol))
    assert kinds(0.0) == [
        ("fresh", "added"), ("fx", "currency_changed"), ("gone", "removed"),
        ("restated", "restated"), ("rounded", "restated"), ("wasnull", "restated"),
    ], kinds(0.0)

    # a 1e-5 relative wobble is absorbed by tol=1e-4, a 10% restatement is not
    assert ("rounded", "restated") not in kinds(1e-4)
    assert ("restated", "restated") in kinds(1e-4)
    # NULL -> value is always a change, tolerance cannot hide it
    assert ("wasnull", "restated") in kinds(1e-4)

    print("self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
