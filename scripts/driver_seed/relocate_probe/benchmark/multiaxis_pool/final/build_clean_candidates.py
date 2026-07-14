#!/usr/bin/env python3
"""Build blind reader batches from the exact two-slice pool.

The locator receives only old-source identity labels and target source text. Hidden
target values are consulted only after every candidate file has been written.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import re
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from neo4j import GraphDatabase

REPO = Path("/home/faisal/EventMarketDB")
ROOT = Path("/tmp/relocate_multi_axis.mrogHs")
POOL = ROOT / "runs" / "clean_multi_axis" / "truth_pool.jsonl"
OUT = ROOT / "runs" / "clean_multi_axis"
sys.path.insert(0, str(ROOT / "driver_seed"))
import link_lib as L

STOP = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "is", "of", "on",
    "or", "the", "to", "with", "axis", "member", "members", "table", "page", "note", "notes",
    "ended", "ending", "month", "months", "quarter", "quarterly", "year", "years", "fiscal",
    "three", "six", "nine", "twelve", "million", "millions", "thousand", "thousands",
}


def load_env():
    for line in (REPO / ".env").read_text().splitlines():
        match = re.match(r"\s*(NEO4J_[A-Z_]+)=(.*)", line)
        if match:
            os.environ[match.group(1)] = match.group(2).strip().strip('"').strip("'")


def words(text):
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(text or ""))
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    return [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9&'-]*", text)
        if len(word) >= 2 and word.lower() not in STOP
    ]


def human(text):
    return " ".join(words(text))


def exact_phrase(text):
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(text or ""))
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    return " ".join(text.lower().split())


def phrases(text, max_n=4):
    tokens = words(text)
    return {
        " ".join(tokens[start : start + size])
        for size in range(2, max_n + 1)
        for start in range(len(tokens) - size + 1)
    }


def tidy(text):
    return " ".join(str(text or "").replace("\u200b", "").split())


def address_for(row):
    lock = row["lock"]
    return {
        "metric": {
            "qname": lock["concept_qname"],
            "label": human(lock["concept_label"] or lock["concept_qname"]),
        },
        "facets": [
            {
                "kind": facet["kind"],
                "axis_qname": facet["axis_qname"],
                "member_qname": facet["member_qname"],
                "member_label": human(facet["member_label"] or facet["member_qname"]),
            }
            for facet in lock["facets"]
        ],
        "unit": {"name": lock["unit_name"], "is_divide": lock["unit_is_divide"]},
    }


def query(address):
    facet_groups = []
    facet_phrases = []
    for facet in address["facets"]:
        group = set(words(facet["member_label"] or facet["member_qname"]))
        if group:
            facet_groups.append(group)
            facet_phrases.append(" ".join(words(facet["member_label"])))
    metric = set(words(address["metric"]["label"] or address["metric"]["qname"]))
    all_words = set(metric)
    for group in facet_groups:
        all_words |= group
    source_groups = []
    source_phrases = []
    for key, value in (address.get("source_words") or {}).items():
        group = set(words(value))
        # A physical column can be a period or unit heading. Keep it in the
        # reader's address, but use it for retrieval only when it names a facet.
        if key == "column" and not any(group & facet for facet in facet_groups):
            continue
        if group:
            source_groups.append(group)
            source_phrases.append(exact_phrase(value))
            all_words |= group
    return {
        "facet_groups": facet_groups,
        "facet_phrases": facet_phrases,
        "metric_words": metric,
        "source_groups": source_groups,
        "source_phrases": source_phrases,
        "all_words": all_words,
        "all_phrases": phrases(" ".join(sorted(all_words))),
    }


def chunks(text, span=3600, stride=2200):
    text = str(text or "")
    units = []
    for match in re.finditer(r"##TABLE_START", text):
        end = text.find("##TABLE_END", match.end())
        if end < 0:
            continue
        end += len("##TABLE_END")
        table = text[match.start() : end]
        if len(table) <= 6000:
            units.append(("table", tidy(table)))
        else:
            header = tidy(table[:700])
            for start in range(0, len(table), stride):
                local = tidy(table[start : start + span])
                if local:
                    units.append(("table_chunk", tidy(header + " " + local)))
                if start + span >= len(table):
                    break
    for start in range(0, len(text), stride):
        local = tidy(text[start : start + span])
        if local and re.search(r"\d", local):
            units.append(("source_chunk", local))
        if start + span >= len(text):
            break
    return units


def locate(sources, address, keep):
    q = query(address)
    raw = []
    for source in sources:
        low_source = source["text"].lower()
        for phrase in q["source_phrases"]:
            if not phrase:
                continue
            start = 0
            while True:
                hit = low_source.find(phrase, start)
                if hit < 0:
                    break
                left = max(0, hit - 1800)
                block = tidy(source["text"][left : hit + len(phrase) + 1800])
                if block and re.search(r"\d", block):
                    raw.append({"source_kind": source["kind"], "source_id": source["id"],
                                "chunk_kind": "address_window", "text": block})
                start = hit + len(phrase)
        for chunk_kind, text in chunks(source["text"]):
            raw.append(
                {
                    "source_kind": source["kind"],
                    "source_id": source["id"],
                    "chunk_kind": chunk_kind,
                    "text": text,
                }
            )
    unique = []
    seen = set()
    for unit in raw:
        key = hashlib.sha256(unit["text"].encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        unit["words"] = set(words(unit["text"]))
        unit["low"] = unit["text"].lower()
        unique.append(unit)

    frequency = collections.Counter()
    for unit in unique:
        frequency.update(unit["words"] & q["all_words"])
    total = max(len(unique), 1)
    scored = []
    for unit in unique:
        token_set = unit["words"]
        facet_scores = [len(group & token_set) / len(group) for group in q["facet_groups"]]
        facet_complete = sum(score == 1 for score in facet_scores)
        facet_partial = sum(facet_scores)
        exact_facets = sum(phrase and phrase in unit["low"] for phrase in q["facet_phrases"])
        source_scores = [len(group & token_set) / len(group) for group in q["source_groups"]]
        source_complete = sum(score == 1 for score in source_scores)
        source_partial = sum(source_scores)
        exact_source = sum(phrase and phrase in unit["low"] for phrase in q["source_phrases"])
        metric = len(q["metric_words"] & token_set) / max(len(q["metric_words"]), 1)
        rarity = sum(
            math.log((total + 1) / (frequency[token] + 1)) + 1
            for token in q["all_words"] & token_set
        ) / math.sqrt(max(len(token_set), 1))
        score = (12 * facet_complete + 5 * facet_partial + 7 * exact_facets +
                 10 * source_complete + 4 * source_partial + 7 * exact_source +
                 4 * metric + rarity)
        if score > 0:
            scored.append((score, facet_complete, exact_facets, metric, -len(unit["text"]), unit))
    scored.sort(key=lambda item: item[:5], reverse=True)
    chosen = []
    address_windows = 0
    for item in scored:
        is_address_window = item[5]["chunk_kind"] == "address_window"
        if is_address_window and address_windows >= min(6, keep):
            continue
        chosen.append(item)
        address_windows += int(is_address_window)
        if len(chosen) == keep:
            break
    section = tidy((address.get("source_words") or {}).get("section"))
    return [
        {
            "source_kind": item[5]["source_kind"],
            "source_id": item[5]["source_id"],
            "text": item[5]["text"],
            "retrieval_score": round(item[0], 4),
            # This is a tie-break signal, not a filter: exact old section labels
            # outrank longer labels that merely contain the same words.
            "exact_section": bool(section and section in item[5]["text"]),
        }
        for item in chosen
    ]


def select(rows, split, limit):
    eligible = [
        row
        for row in rows
        if row["split"] == split
        and row["confirmed_facet_count"] == row["facet_count"]
        and row["lock"]["unit_name"] == "iso4217:USD"
        and row["lock"]["unit_is_divide"] != "1"
    ]
    eligible.sort(key=lambda row: row["pair_key"])
    # Diversity first: first identity per company, then second, etc.
    selected = []
    for ordinal in range(5):
        by_company = collections.defaultdict(list)
        for row in eligible:
            by_company[row["ticker"]].append(row)
        for ticker in sorted(by_company, key=lambda value: hashlib.sha256(value.encode()).hexdigest()):
            if ordinal < len(by_company[ticker]):
                selected.append(by_company[ticker][ordinal])
                if len(selected) == limit:
                    return selected
    return selected


def fetch_primary_sources(session, report_ids):
    out = collections.defaultdict(list)
    queries = [
        (
            "filing_section",
            "MATCH (r:Report)-[:HAS_SECTION]->(x:ExtractedSectionContent) "
            "WHERE r.id IN $ids RETURN r.id AS rid, x.id AS id, x.content AS text",
        ),
        (
            "filing_text",
            "MATCH (r:Report)-[:HAS_FILING_TEXT]->(x:FilingTextContent) "
            "WHERE r.id IN $ids RETURN r.id AS rid, x.id AS id, x.content AS text",
        ),
        (
            "filing_exhibit",
            "MATCH (r:Report)-[:HAS_EXHIBIT]->(x:ExhibitContent) "
            "WHERE r.id IN $ids RETURN r.id AS rid, x.id AS id, x.content AS text",
        ),
    ]
    for kind, cypher in queries:
        for row in session.run(cypher, ids=sorted(report_ids)):
            if row["text"]:
                out[row["rid"]].append({"kind": kind, "id": row["id"], "text": row["text"]})
    return out


def leaks(value, payload):
    text = json.dumps(payload, sort_keys=True)
    forms = [form for form in L.value_forms(float(Decimal(value)), "number") if len(form) >= 2]
    return sorted(form for form in forms if L.bounded_hit(text, form))


def value_present(value, text):
    return L.value_ok(value, "number", text) or L.value_present_rounded(value, "number", text)


def nested_keys(value):
    if isinstance(value, dict):
        return set(value) | set().union(*(nested_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(nested_keys(item) for item in value), set())
    return set()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("development", "holdout"), required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--keep", type=int, default=24)
    args = parser.parse_args()
    rows = [json.loads(line) for line in POOL.read_text().splitlines()]
    selected = select(rows, args.split, args.limit * 2)
    exact_path = OUT / f"{args.split}_exact_addresses.jsonl"
    exact_addresses = {
        row["pair_key"]: row["address"]
        for row in (json.loads(line) for line in exact_path.read_text().splitlines())
    }

    load_env()
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    with driver.session() as session:
        source_map = fetch_primary_sources(session, {row["target"]["report_id"] for row in selected})
    driver.close()

    batch_dir = OUT / f"{args.split}_blind_batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    for old in batch_dir.glob("batch_*.json"):
        old.unlink()
    truth_out = []
    retrieval_audit = []
    skipped = collections.Counter()
    for row in selected:
        if len(truth_out) >= args.limit:
            break
        address = exact_addresses.get(row["pair_key"])
        if not address:
            skipped["no_exact_visible_lock_address"] += 1
            continue
        batch_shell = {
            "ticker": row["ticker"],
            "period_type": "quarterly",
            "period_target": row["target"]["period_end"],
            "address": address,
        }
        target_leaks = leaks(row["target"]["value_raw"], batch_shell)
        old_leaks = leaks(row["lock"]["value_raw"], batch_shell)
        if target_leaks:
            skipped["target_number_form_in_non_candidate_input"] += 1
            continue
        if old_leaks:
            skipped["old_number_form_in_non_candidate_input"] += 1
            continue
        sources = source_map.get(row["target"]["report_id"], [])
        candidates = locate(sources, address, args.keep)
        case_id = len(truth_out)
        batch = {"id": case_id, **batch_shell, "candidates": candidates}
        forbidden = {"value_raw", "target", "lock", "truth", "fact_id", "target_value_raw"}
        assert not (nested_keys(batch_shell) & forbidden)
        (batch_dir / f"batch_{case_id}.json").write_text(json.dumps(batch, indent=2))
        target = float(Decimal(row["target"]["value_raw"]))
        source_present = any(value_present(target, source["text"]) for source in sources)
        candidate_present = any(
            value_present(target, candidate["text"]) for candidate in candidates
        )
        truth_out.append(
            {
                "id": case_id,
                "pool_id": row["id"],
                "pair_key": row["pair_key"],
                "ticker": row["ticker"],
                "facet_count": row["facet_count"],
                "target_value_raw": row["target"]["value_raw"],
                "target_decimals": row["target"]["decimals"],
                "target_report_id": row["target"]["report_id"],
                "source_present": source_present,
                "candidate_present": candidate_present,
            }
        )
        retrieval_audit.append(
            {
                "id": case_id,
                "sources": len(sources),
                "candidates": len(candidates),
                "source_present": source_present,
                "candidate_present": candidate_present,
            }
        )

    truth_path = OUT / f"{args.split}_blind_truth.jsonl"
    truth_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in truth_out))
    report = {
        "split": args.split,
        "requested": args.limit,
        "built": len(truth_out),
        "companies": len({row["ticker"] for row in truth_out}),
        "keep": args.keep,
        "source_present": sum(row["source_present"] for row in truth_out),
        "candidate_present": sum(row["candidate_present"] for row in truth_out),
        "skipped": dict(skipped),
        "reader_input_contains_old_or_target_value": False,
        "records": retrieval_audit,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "link_lib_sha256": hashlib.sha256((ROOT / "driver_seed/link_lib.py").read_bytes()).hexdigest(),
    }
    (OUT / f"{args.split}_retrieval_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
