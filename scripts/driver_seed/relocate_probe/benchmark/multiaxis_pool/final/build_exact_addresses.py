#!/usr/bin/env python3
"""Bind each old structured fact to its exact visible filing cell.

The old value is used only as a verification gate. Model-facing address files omit
the value, the old row of numbers, and physical cell coordinates.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from neo4j import GraphDatabase

REPO = Path("/home/faisal/EventMarketDB")
ROOT = Path("/tmp/relocate_multi_axis.mrogHs")
RUN = ROOT / "runs" / "clean_multi_axis"
POOL = RUN / "truth_pool.jsonl"
EXTRACTOR = Path("/tmp/cell_address_probe.WhbHsb/lock_row_extract.py")
CACHE = RUN / "inline_lock_html"
sys.path.insert(0, str(ROOT / "driver_seed"))
import link_lib as L

candidate_spec = importlib.util.spec_from_file_location(
    "candidate_builder", ROOT / "prototype/build_clean_candidates.py"
)
candidate_builder = importlib.util.module_from_spec(candidate_spec)
candidate_spec.loader.exec_module(candidate_builder)
extract_spec = importlib.util.spec_from_file_location("lock_extract", EXTRACTOR)
lock_extract = importlib.util.module_from_spec(extract_spec)
extract_spec.loader.exec_module(lock_extract)


def load_env():
    for line in (REPO / ".env").read_text().splitlines():
        match = re.match(r"\s*(NEO4J_[A-Z_]+)=(.*)", line)
        if match:
            os.environ[match.group(1)] = match.group(2).strip().strip('"').strip("'")


def fetch_urls(report_ids):
    load_env()
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    with driver.session() as session:
        rows = session.run(
            "MATCH (r:Report) WHERE r.id IN $ids "
            "RETURN r.id AS id, r.linkToFilingDetails AS inline_url, "
            "r.primaryDocumentUrl AS instance_url",
            ids=sorted(report_ids),
        )
        result = {row["id"]: (row["inline_url"] or row["instance_url"]) for row in rows}
    driver.close()
    return result


def download_one(report_id, url):
    path = CACHE / f"{report_id}.html"
    if path.exists() and path.stat().st_size > 1000:
        return report_id, path, None
    if not url:
        return report_id, None, "missing_inline_url"
    if url.endswith("_htm.xml"):
        url = url[: -len("_htm.xml")] + ".htm"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "EventMarketDB relocation research contact@example.com"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
        if len(body) < 1000:
            return report_id, None, "short_download"
        path.write_bytes(body)
        return report_id, path, None
    except Exception as exc:
        return report_id, None, f"download:{type(exc).__name__}"


def contains_old_value(text, old_value):
    return any(
        L.bounded_hit(str(text), form)
        for form in L.value_forms(float(old_value), "number")
        if len(form) >= 2
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("development", "holdout"), required=True)
    parser.add_argument("--limit", type=int, default=150)
    args = parser.parse_args()
    rows = [json.loads(line) for line in POOL.read_text().splitlines()]
    selected = candidate_builder.select(rows, args.split, args.limit * 2)
    CACHE.mkdir(parents=True, exist_ok=True)
    urls = fetch_urls({row["lock"]["report_id"] for row in selected})
    downloaded = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = {
            executor.submit(download_one, rid, urls.get(rid)): rid
            for rid in sorted({row["lock"]["report_id"] for row in selected})
        }
        for future in as_completed(jobs):
            report_id, path, error = future.result()
            downloaded[report_id] = (path, error)

    addresses = []
    audit = []
    for row in selected:
        if len(addresses) >= args.limit:
            break
        lock = row["lock"]
        html, download_error = downloaded.get(lock["report_id"], (None, "not_downloaded"))
        if download_error:
            audit.append({"pool_id": row["id"], "ticker": row["ticker"], "ok": False,
                          "reason": download_error})
            continue
        pairs = [(facet["axis_qname"], facet["member_qname"]) for facet in lock["facets"]]
        try:
            result = lock_extract.extract(
                html,
                lock["concept_qname"],
                lock["period_start"],
                lock["period_end"],
                pairs,
            )
        except (SystemExit, AttributeError, ValueError, TypeError) as exc:
            audit.append({"pool_id": row["id"], "ticker": row["ticker"], "ok": False,
                          "reason": str(exc)})
            continue
        displayed = result["evidence"]["displayed_value"]
        if not L.stated_match(displayed, float(lock["value_raw"])):
            audit.append({"pool_id": row["id"], "ticker": row["ticker"], "ok": False,
                          "reason": "displayed_value_does_not_match_structured_value",
                          "displayed": displayed})
            continue
        source_words = {
            key: value
            for key, value in result["source_words"].items()
            if value and not contains_old_value(value, float(lock["value_raw"]))
        }
        if not source_words.get("row"):
            audit.append({"pool_id": row["id"], "ticker": row["ticker"], "ok": False,
                          "reason": "no_visible_row_label", "source_words": source_words})
            continue
        address = candidate_builder.address_for(row)
        address["source_words"] = source_words
        if contains_old_value(json.dumps(address), float(lock["value_raw"])):
            audit.append({"pool_id": row["id"], "ticker": row["ticker"], "ok": False,
                          "reason": "old_value_form_in_model_address"})
            continue
        addresses.append({"pool_id": row["id"], "pair_key": row["pair_key"], "address": address})
        audit.append(
            {
                "pool_id": row["id"],
                "ticker": row["ticker"],
                "ok": True,
                "html_sha256": hashlib.sha256(Path(html).read_bytes()).hexdigest(),
                "fact_id": result["evidence"]["fact_id"],
                "context_id": result["evidence"]["context_id"],
                "displayed_value": displayed,
                "source_words": source_words,
                "row_cells": result["evidence"]["row_cells"],
            }
        )

    address_path = RUN / f"{args.split}_exact_addresses.jsonl"
    address_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in addresses))
    audit_path = RUN / f"{args.split}_exact_lock_audit.jsonl"
    audit_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in audit))
    report = {
        "split": args.split,
        "requested": args.limit,
        "addresses": len(addresses),
        "attempted": len(audit),
        "companies": len({row["ticker"] for row in audit if row["ok"]}),
        "failures": len([row for row in audit if not row["ok"]]),
        "failure_reasons": dict(
            __import__("collections").Counter(row["reason"] for row in audit if not row["ok"])
        ),
        "model_address_contains_old_value_or_old_numeric_row": False,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "extractor_sha256": hashlib.sha256(EXTRACTOR.read_bytes()).hexdigest(),
    }
    (RUN / f"{args.split}_exact_address_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
