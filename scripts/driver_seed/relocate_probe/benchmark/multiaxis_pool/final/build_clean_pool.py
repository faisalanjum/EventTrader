#!/usr/bin/env python3
"""Build a real, exact-identity pool for two-or-more-slice quarterly facts.

Read-only Neo4j input. All artifacts are written below /tmp. The pool is truth;
no reader input is produced here.
"""
from __future__ import annotations

import ast
import collections
import hashlib
import json
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from neo4j import GraphDatabase

REPO = Path("/home/faisal/EventMarketDB")
ROOT = Path("/tmp/relocate_multi_axis.mrogHs")
OUT = ROOT / "runs" / "clean_multi_axis"
HARNESS = REPO / ".claude/plans/Drivers/experiments/harness/xbrl_dryrun_materializer.py"
METRIC = re.compile(
    r"revenue|sales|income|profit|cost|expense|asset|premium|earningspershare",
    re.I,
)


def load_env() -> None:
    for line in (REPO / ".env").read_text().splitlines():
        match = re.match(r"\s*(NEO4J_[A-Z_]+)=(.*)", line)
        if match:
            os.environ[match.group(1)] = match.group(2).strip().strip('"').strip("'")


def literal_assignment(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def frozen_axis_rules():
    source = HARNESS.read_bytes()
    tree = ast.parse(source)
    return {
        "source": str(HARNESS),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "confirmed_axes": literal_assignment(tree, "CONFIRMED_AXES"),
        "standard_namespaces": sorted(literal_assignment(tree, "STD_NS")),
        "elimination_locals": sorted(literal_assignment(tree, "ELIMINATION_LOCALS")),
    }


def norm_uid(value: str | None) -> str:
    value = str(value or "")
    first, sep, rest = value.partition(":")
    if sep and first.isdigit():
        return str(int(first)) + sep + rest
    return value


def local(qname: str) -> str:
    return str(qname or "").split(":")[-1]


def plain(qname: str, suffix: str = "") -> str:
    name = local(qname)
    if suffix and name.endswith(suffix):
        name = name[: -len(suffix)]
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    return " ".join(re.findall(r"[A-Za-z0-9]+", name)).strip()


def clean_label(label: str | None, qname: str, suffix: str = "") -> str:
    value = " ".join(str(label or "").split()).strip()
    return value or plain(qname, suffix)


def parse_value(raw) -> Decimal | None:
    try:
        return Decimal(str(raw).replace(",", "").strip())
    except InvalidOperation:
        return None


def iso(value) -> str:
    return str(value or "")[:10]


def classify_pairs(dims, mems, dim_map, mem_map, rules):
    resolved_dims = []
    for uid in dims or []:
        row = dim_map.get(norm_uid(uid))
        if row is None:
            return None, "unresolved_dimension"
        if str(row[1]).strip().lower() in {"true", "1", "t", "yes"}:
            resolved_dims.append(row)
    resolved_mems = []
    for uid in mems or []:
        row = mem_map.get(norm_uid(uid))
        if row is None:
            return None, "unresolved_member"
        resolved_mems.append(row)
    if len(resolved_dims) != len(resolved_mems):
        return None, "pairing_mismatch"

    confirmed = rules["confirmed_axes"]
    standard = set(rules["standard_namespaces"])
    eliminations = set(rules["elimination_locals"])
    facets = []
    for (axis, _), (member, member_label) in zip(resolved_dims, resolved_mems):
        if axis in confirmed:
            kind = confirmed[axis]
            if kind == "segment" and local(member) in eliminations:
                return None, "elimination"
            status = "confirmed"
        elif axis.split(":")[0] in standard:
            return None, "known_non_slice_axis"
        else:
            kind = "unknown"
            status = "provisional"
        facets.append(
            {
                "axis_qname": axis,
                "axis_label": plain(axis, "Axis"),
                "member_qname": member,
                "member_label": clean_label(member_label, member, "Member"),
                "kind": kind,
                "status": status,
            }
        )
    if len(facets) < 2:
        return None, "fewer_than_two_slices"
    return facets, None


def query_maps(session):
    dim_map = {}
    for row in session.run(
        "MATCH (d:Dimension) RETURN d.u_id AS uid, d.qname AS qname, d.is_explicit AS explicit"
    ):
        dim_map[norm_uid(row["uid"])] = (str(row["qname"] or ""), row["explicit"])
    mem_map = {}
    for row in session.run(
        "MATCH (m:Member) RETURN m.u_id AS uid, m.qname AS qname, m.label AS label"
    ):
        mem_map[norm_uid(row["uid"])] = (str(row["qname"] or ""), str(row["label"] or ""))
    return dim_map, mem_map


FACT_QUERY = """
MATCH (r:Report {formType:'10-Q'})-[:PRIMARY_FILER]->(c:Company),
      (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept),
      (f)-[:IN_CONTEXT]->(ctx:Context),
      (f)-[:HAS_PERIOD]->(p:Period)
OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit)
WHERE r.periodOfReport >= $since
  AND coalesce(r.isAmendment,false) = false
  AND f.is_numeric='1' AND f.is_nil='0'
  AND size(coalesce(ctx.dimension_u_ids,[])) >= 2
  AND p.period_type='duration'
  AND toString(p.end_date) = toString(date(r.periodOfReport)+duration('P1D'))
  AND duration.inDays(date(p.start_date),date(p.end_date)).days >= 80
  AND duration.inDays(date(p.start_date),date(p.end_date)).days <= 105
  AND con.qname =~ '(?i).*(Revenue|Sales|Income|Profit|Cost|Expense|Asset|Premium|EarningsPerShare).*'
RETURN c.ticker AS ticker, r.id AS report_id, r.accessionNo AS accession,
       r.periodOfReport AS report_period, r.created AS created,
       r.primaryDocumentUrl AS primary_document_url,
       f.id AS fact_id, con.qname AS concept_qname, con.label AS concept_label,
       f.value AS value_raw, f.decimals AS decimals,
       u.name AS unit_name, u.is_divide AS unit_is_divide,
       p.start_date AS period_start, p.end_date AS period_end_exclusive,
       ctx.dimension_u_ids AS dimension_u_ids, ctx.member_u_ids AS member_u_ids
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rules = frozen_axis_rules()
    (OUT / "axis_rules.json").write_text(json.dumps(rules, indent=2, sort_keys=True))
    load_env()
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    counters = collections.Counter()
    observations = []
    with driver.session() as session:
        dim_map, mem_map = query_maps(session)
        for index, row in enumerate(session.run(FACT_QUERY, since="2022-01-01"), 1):
            counters["raw_fact_rows"] += 1
            concept = str(row["concept_qname"] or "")
            if not METRIC.search(concept):
                counters["non_metric"] += 1
                continue
            value = parse_value(row["value_raw"])
            if value is None or value == 0:
                counters["bad_or_zero_value"] += 1
                continue
            facets, reason = classify_pairs(
                row["dimension_u_ids"], row["member_u_ids"], dim_map, mem_map, rules
            )
            if reason:
                counters[reason] += 1
                continue
            report_period = iso(row["report_period"])
            start = iso(row["period_start"])
            end_exclusive = iso(row["period_end_exclusive"])
            observations.append(
                {
                    "ticker": row["ticker"],
                    "report_id": row["report_id"],
                    "accession": row["accession"],
                    "report_period": report_period,
                    "created": str(row["created"] or ""),
                    "primary_document_url": row["primary_document_url"],
                    "fact_id": row["fact_id"],
                    "concept_qname": concept,
                    "concept_label": clean_label(row["concept_label"], concept),
                    "value_raw": str(value),
                    "decimals": str(row["decimals"] or ""),
                    "unit_name": str(row["unit_name"] or ""),
                    "unit_is_divide": str(row["unit_is_divide"] or ""),
                    "period_start": start,
                    "period_end": report_period,
                    "period_end_exclusive": end_exclusive,
                    "facets": facets,
                }
            )
            counters["eligible_fact_rows"] += 1
            if index % 25000 == 0:
                print(f"streamed {index:,}; eligible {len(observations):,}", flush=True)
    driver.close()

    # Pick one deterministic original filing per company/report period.
    chosen_report = {}
    for row in observations:
        key = (row["ticker"], row["report_period"])
        rank = (row["created"], row["report_id"])
        chosen_report[key] = max(chosen_report.get(key, rank), rank)
    observations = [
        row
        for row in observations
        if (row["created"], row["report_id"])
        == chosen_report[(row["ticker"], row["report_period"])]
    ]

    def identity(row):
        return (
            row["ticker"],
            row["concept_qname"],
            row["unit_name"],
            row["unit_is_divide"],
            tuple((f["axis_qname"], f["member_qname"]) for f in row["facets"]),
        )

    grouped = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in observations:
        grouped[identity(row)][row["report_period"]].append(row)

    clean_series = {}
    for key, by_period in grouped.items():
        clean = {}
        for period, rows in by_period.items():
            values = {row["value_raw"] for row in rows}
            if len(values) == 1:
                clean[period] = sorted(rows, key=lambda row: str(row["fact_id"]))[0]
            else:
                counters["identity_value_collision"] += 1
        if len(clean) >= 2:
            clean_series[key] = clean

    pairs = []
    for key, by_period in clean_series.items():
        ordered = sorted(by_period)
        for lock_period, target_period in zip(ordered, ordered[1:]):
            gap = (date.fromisoformat(target_period) - date.fromisoformat(lock_period)).days
            if not 75 <= gap <= 120:
                continue
            lock = by_period[lock_period]
            target = by_period[target_period]
            if lock["value_raw"] == target["value_raw"]:
                counters["equal_lock_target"] += 1
                continue
            payload = json.dumps(
                [lock["ticker"], lock["concept_qname"], lock["facets"], target_period],
                sort_keys=True,
            )
            pairs.append(
                {
                    "pair_key": hashlib.sha256(payload.encode()).hexdigest(),
                    "ticker": lock["ticker"],
                    "lock": lock,
                    "target": target,
                    "facet_count": len(lock["facets"]),
                    "confirmed_facet_count": sum(f["status"] == "confirmed" for f in lock["facets"]),
                }
            )

    pairs.sort(key=lambda row: row["pair_key"])
    # Bound correlated evidence: at most five identities per company.
    per_company = collections.Counter()
    balanced = []
    for pair in pairs:
        if per_company[pair["ticker"]] >= 5:
            continue
        per_company[pair["ticker"]] += 1
        company_bucket = int(hashlib.sha256(pair["ticker"].encode()).hexdigest()[:8], 16) % 5
        pair["split"] = "holdout" if company_bucket == 0 else "development"
        pair["id"] = len(balanced)
        balanced.append(pair)

    pool = OUT / "truth_pool.jsonl"
    pool.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in balanced))
    summary = {
        "scope": {"since": "2022-01-01", "all_database_companies": True, "max_per_company": 5},
        "rules_sha256": rules["source_sha256"],
        "counts": dict(counters),
        "maps": {"dimensions": len(dim_map), "members": len(mem_map)},
        "eligible_observations_after_report_dedup": len(observations),
        "eligible_series": len(clean_series),
        "adjacent_nontrivial_pairs_unbalanced": len(pairs),
        "balanced_pairs": len(balanced),
        "companies": len({row["ticker"] for row in balanced}),
        "splits": dict(collections.Counter(row["split"] for row in balanced)),
        "facet_counts": dict(collections.Counter(str(row["facet_count"]) for row in balanced)),
        "confirmed_facet_counts": dict(
            collections.Counter(str(row["confirmed_facet_count"]) for row in balanced)
        ),
    }
    (OUT / "pool_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
