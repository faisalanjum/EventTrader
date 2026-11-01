#!/usr/bin/env python3
"""Build a KPI-name catalog from Fiscal.ai raw snapshots (offline, no network).

Reads the gzipped payloads a scrape run already wrote (raw/*.json.gz) and emits
the authoritative per-company KPI catalog from `segmentsData.metrics` — names
plus the metadata the flattening step throws away (tag, category, segment
grouping, currency flag, discontinued-by-period, which period types carry data).

    python3 scripts/fiscal_ai_kpi_catalog.py RAW_DIR --out OUT_DIR
    python3 scripts/fiscal_ai_kpi_catalog.py --self-check

Diff two runs' catalogs to find KPI names added/removed:
    python3 scripts/fiscal_ai_kpi_catalog.py --diff OLD/kpi_catalog.sqlite NEW/kpi_catalog.sqlite
"""

from __future__ import annotations

import argparse
import csv
import glob
import gzip
import json
import os
import sqlite3
import sys
from pathlib import Path

PERIODS = ("Annual", "Quarterly", "Semi-Annual", "LTM")

COLUMNS = [
    "symbol", "company_slug", "company_name", "cik",
    "metric_id", "metric_name", "metric_tag", "category", "format",
    "is_kpi", "is_currency", "seg_type", "overlap", "grouping_metric",
    "discontinued_periods",   # comma-list of period types flagged discontinued
    "periods_with_data",      # comma-list of period types that have >=1 non-null cell
    "n_periods_with_data",
    "source_files",           # annual / quarterly / both
]


def periods_with_values(sd: dict, metric_id: str) -> set[str]:
    """Which period types actually carry a non-null cell for this metric."""
    hits = set()
    for pk in PERIODS:
        dates = [d.get("date") for d in sd.get("dates", {}).get(pk, [])]
        for section in sd.get("data", {}).get(pk, {}).values():
            for row in section.get("rows", []):
                m = row.get("metric") or {}
                if (m.get("metricId") or m.get("id")) != metric_id:
                    continue
                if any(row.get(d, {}).get("value") is not None for d in dates if d):
                    hits.add(pk)
    return hits


def parse_file(path: str) -> list[dict]:
    pp = json.load(gzip.open(path, "rt", encoding="utf-8")).get("pageProps") or {}
    comp = pp.get("company") or {}
    sd = pp.get("segmentsData") or {}
    slug = os.path.basename(path).rsplit("_", 1)[0]
    which = "annual" if path.endswith("_annual.json.gz") else "quarterly"
    out = []
    for m in sd.get("metrics", []):
        mid = m.get("metricId") or m.get("id")
        if not mid:
            continue
        g = m.get("grouping") or {}
        disc = [p for p, v in (m.get("discontinued") or {}).items() if v]
        pw = periods_with_values(sd, mid)
        out.append({
            "symbol": comp.get("ticker") or "",
            "company_slug": slug,
            "company_name": comp.get("name") or "",
            "cik": comp.get("cik") or "",
            "metric_id": mid,
            "metric_name": m.get("metricName") or mid,
            "metric_tag": m.get("metricTag") or "",
            "category": m.get("category") or "",
            "format": m.get("format") or "",
            "is_kpi": int(bool(m.get("isKPIs"))),
            "is_currency": int(bool(m.get("isCurrency"))),
            "seg_type": g.get("segType") or "",
            "overlap": g.get("overlap") or "",
            "grouping_metric": g.get("metric") or "",
            "discontinued_periods": ",".join(sorted(disc)),
            "periods_with_data": ",".join(p for p in PERIODS if p in pw),
            "n_periods_with_data": len(pw),
            "_source": which,
        })
    return out


def build(raw_dir: Path) -> list[dict]:
    """One row per (slug, metric_id), merged across a company's annual+quarterly files."""
    merged: dict[tuple[str, str], dict] = {}
    files = sorted(glob.glob(str(raw_dir / "*.json.gz")))
    if not files:
        raise SystemExit(f"no *.json.gz under {raw_dir}")
    for f in files:
        for rec in parse_file(f):
            key = (rec["company_slug"], rec["metric_id"])
            src = rec.pop("_source")
            if key not in merged:
                rec["source_files"] = src
                merged[key] = rec
            else:
                prev = merged[key]
                # union the period-coverage across both files; keep richer metadata
                pw = set(filter(None, prev["periods_with_data"].split(","))) | \
                     set(filter(None, rec["periods_with_data"].split(",")))
                prev["periods_with_data"] = ",".join(p for p in PERIODS if p in pw)
                prev["n_periods_with_data"] = len(pw)
                if src not in prev["source_files"]:
                    prev["source_files"] = "both"
    return list(merged.values())


def write_outputs(rows: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "kpi_catalog.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    db_path = out_dir / "kpi_catalog.sqlite"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    cols = ", ".join(f'"{c}" TEXT' for c in COLUMNS)
    con.execute(f"CREATE TABLE kpi_catalog ({cols}, PRIMARY KEY(company_slug, metric_id))")
    con.executemany(
        f"INSERT OR REPLACE INTO kpi_catalog VALUES ({','.join('?' for _ in COLUMNS)})",
        [[r[c] for c in COLUMNS] for r in rows],
    )
    con.execute("CREATE INDEX idx_name ON kpi_catalog(metric_name)")
    con.commit()
    con.close()
    print(f"wrote {csv_path}")
    print(f"wrote {db_path}")


def diff(old: Path, new: Path) -> int:
    con = sqlite3.connect(":memory:")
    con.execute("ATTACH ? AS o", (f"file:{old}?mode=ro",))
    con.execute("ATTACH ? AS n", (f"file:{new}?mode=ro",))
    key = "company_slug || '||' || metric_name"
    added = con.execute(
        f"SELECT company_slug, metric_name FROM n.kpi_catalog "
        f"WHERE {key} NOT IN (SELECT {key} FROM o.kpi_catalog) ORDER BY 1,2").fetchall()
    removed = con.execute(
        f"SELECT company_slug, metric_name FROM o.kpi_catalog "
        f"WHERE {key} NOT IN (SELECT {key} FROM n.kpi_catalog) ORDER BY 1,2").fetchall()
    print(f"KPI names ADDED   (in new, not old): {len(added):,}")
    for s, m in added[:25]:
        print(f"  + {s:22} {m}")
    print(f"\nKPI names REMOVED (in old, not new): {len(removed):,}")
    for s, m in removed[:25]:
        print(f"  - {s:22} {m}")
    return 0


def self_check() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        raw = d / "raw"
        raw.mkdir()
        payload = {"pageProps": {
            "company": {"ticker": "ZZ", "name": "Zeta", "cik": "1"},
            "segmentsData": {
                "metrics": [
                    {"metricId": "Widget Rev", "metricName": "Widget Rev", "metricTag": "Revenue",
                     "category": "Revenue seg1", "format": "number", "isCurrency": True, "isKPIs": True,
                     "grouping": {"segType": "seg1", "overlap": "y1a", "metric": "rev"},
                     "discontinued": {"Annual": False, "LTM": True}},
                    {"metricId": "Empty KPI", "metricName": "Empty KPI", "isKPIs": True},
                ],
                "dates": {"Annual": [{"date": "2024-12-31"}], "LTM": [{"date": "2024-09-30"}]},
                "data": {"Annual": {"S": {"rows": [
                    {"metric": {"metricId": "Widget Rev"}, "2024-12-31": {"value": 5.0}},
                    {"metric": {"metricId": "Empty KPI"}, "2024-12-31": {"value": None}},
                ]}}},
            }}}
        for per in ("annual", "quarterly"):
            with gzip.open(raw / f"NYSE-ZZ_{per}.json.gz", "wt") as f:
                json.dump(payload, f)

        rows = {r["metric_id"]: r for r in build(raw)}
        assert set(rows) == {"Widget Rev", "Empty KPI"}, rows.keys()
        w = rows["Widget Rev"]
        assert w["symbol"] == "ZZ" and w["metric_tag"] == "Revenue" and w["seg_type"] == "seg1"
        assert w["discontinued_periods"] == "LTM"
        assert w["periods_with_data"] == "Annual"          # only Annual has a non-null cell
        assert w["source_files"] == "both"                  # merged annual+quarterly
        assert rows["Empty KPI"]["periods_with_data"] == "" # null cell -> no coverage
        write_outputs(list(rows.values()), d / "out")

        # diff: drop one, add one, rebuild -> catalog b
        payload["pageProps"]["segmentsData"]["metrics"] = [
            payload["pageProps"]["segmentsData"]["metrics"][0],
            {"metricId": "New KPI", "metricName": "New KPI", "isKPIs": True},
        ]
        raw2 = d / "raw2"; raw2.mkdir()
        for per in ("annual", "quarterly"):
            with gzip.open(raw2 / f"NYSE-ZZ_{per}.json.gz", "wt") as f:
                json.dump(payload, f)
        write_outputs(build(raw2), d / "out2")
        print("--- diff self-check ---")
        diff(d / "out" / "kpi_catalog.sqlite", d / "out2" / "kpi_catalog.sqlite")
    print("self-check OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir", nargs="?", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--diff", nargs=2, type=Path, metavar=("OLD", "NEW"))
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()

    if a.self_check:
        return self_check()
    if a.diff:
        return diff(*a.diff)
    if not a.raw_dir or not a.out:
        ap.error("need RAW_DIR and --out (or --diff / --self-check)")

    rows = build(a.raw_dir)
    write_outputs(rows, a.out)
    slugs = {r["company_slug"] for r in rows}
    names = {r["metric_name"] for r in rows}
    print(f"\ncompanies: {len(slugs):,}   catalog rows: {len(rows):,}   distinct KPI names: {len(names):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
