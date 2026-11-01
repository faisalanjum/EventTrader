#!/usr/bin/env python3
"""Read-only audit of News as evidence for the Driver system.

This script does not assign final article or Driver labels. It measures
deterministic signals on every News node and compares publication time with
nearby filings and earnings calls for the linked company. The result is a
reproducible evidence file for designing a fact-level news channel.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase, READ_ACCESS


SAMPLE_SIZE = 10
PRIMARY_FORMS = {"8-K": "8k", "10-Q": "10q", "10-K": "10k"}
DAY = timedelta(days=1)
WEEK = timedelta(days=7)


def rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)


# These are broad title probes, not truth labels. Their purpose is to expose
# overlap, source proximity, and missing metadata across the whole corpus.
EVENT_PROBES: dict[str, re.Pattern[str]] = {
    "reported_results": rx(
        r"(?<!to )\b(?:reports?|reported|posts?|posted)\b.{0,90}"
        r"\b(?:eps|earnings|revenue|sales|income|loss)\b|"
        r"\b(?:eps|earnings|revenue|sales)\b.{0,90}"
        r"\b(?:beat|miss|estimate|reported|rose|fell)\b"
    ),
    "company_guidance": rx(
        r"\b(?:guidance|outlook|forecast|reaffirms?|withdraws?|"
        r"sees\s+(?:q[1-4]|fy|20\d\d)|expects\s+(?:q[1-4]|fy|20\d\d))\b"
    ),
    "dividend_action": rx(
        r"\b(?:declares?|raises?|cuts?|suspends?|maintains?|approves?)\b"
        r".{0,70}\bdividend\b|\bdividend\b.{0,70}"
        r"\b(?:declared|raised|cut|suspended|maintained|approved)\b"
    ),
    "buyback": rx(r"\b(?:buyback|share repurchase|repurchase authorization)\b"),
    "financing_or_security_action": rx(
        r"\b(?:public offering|stock offering|registered direct|private placement|"
        r"at-the-market offering|senior notes|convertible notes|credit facility|"
        r"term loan|bond offering|stock split|reverse split)\b"
    ),
    "m_and_a_or_asset_transaction": rx(
        r"\b(?:acquires?|acquired|acquisition|merger|merges?|buyout|takeover|"
        r"(?:agrees?|plans?|offers?|set) to buy|asset sale|divest(?:s|iture)?|spin[- ]?off|"
        r"strategic alternatives)\b"
    ),
    "contract_or_order": rx(
        r"\b(?:award(?:s|ed)?|win(?:s|ning)?|won|secure(?:s|d)?|receive(?:s|d)?)\b"
        r".{0,80}\b(?:contract|order)\b|\bcontract\b.{0,70}"
        r"\b(?:award|worth|valued|from|ceiling)\b"
    ),
    "partnership_or_customer_action": rx(
        r"\b(?:partners? with|partnership|collaboration|collaborates? with|"
        r"strategic alliance|selected by|customer win|supplier agreement)\b"
    ),
    "product_or_strategy_action": rx(
        r"\b(?:launches|launched|unveils|unveiled|introduces|introduced|debuts|"
        r"opens? (?:a |new )?(?:store|location|facility)|closes? (?:a |its )?"
        r"(?:store|location|facility)|price increase|raises? prices?(?!\s+target))\b"
    ),
    "management_change": rx(
        r"\b(?:appoints?|appointed|names?|named|hires?|hired)\b.{0,90}"
        r"\b(?:ceo|cfo|chief|president|director|board|chair)\b|"
        r"\b(?:ceo|cfo|chief|president|director|chair)\b.{0,70}"
        r"\b(?:resigns?|retires?|steps down|departs?|departure)\b"
    ),
    "workforce_or_restructuring": rx(
        r"\b(?:layoffs?|lays off|laid off|job cuts?|cuts? jobs|workforce reduction|"
        r"reduce(?:s|d)? (?:its )?workforce|restructuring|bankruptcy|chapter 11|"
        r"chapter 7)\b"
    ),
    "regulatory_or_clinical": rx(
        r"\b(?:fda|clinical trial|phase (?:1|2|3|i|ii|iii)|topline data|"
        r"primary endpoint|regulatory approval|regulatory clearance|"
        r"complete response letter|pdufa)\b"
    ),
    "legal_or_enforcement": rx(
        r"\b(?:lawsuit|sues|sued|settlement|settles|court|judge|jury|subpoena|"
        r"antitrust|doj|ftc|sec charges|investigation|probe|fine|penalty)\b"
    ),
    "operating_incident": rx(
        r"\b(?:outage|shutdown|disruption|fire|explosion|accident|crash|walkout|"
        r"shortage|contamination|injur(?:y|ies)|fatalit(?:y|ies)|"
        r"hurricane|storm damage|flood|earthquake)\b"
        r"|\b(?:labor|worker|workers|union|employee|employees)\b.{0,50}\bstrike\b"
        r"|\bstrike\b.{0,50}\b(?:labor|worker|workers|union|employee|employees)\b"
    ),
    "cyber_or_data_incident": rx(
        r"\b(?:cyberattack|cyber attack|ransomware|data breach|security breach|"
        r"unauthorized access|systems? breach)\b"
    ),
    "recall_or_safety_action": rx(
        r"\b(?:recalls?|recalled|product recall|safety recall|nhtsa investigation|"
        r"safety probe)\b"
    ),
    "macro_policy_or_geopolitics": rx(
        r"\b(?:federal reserve|fed rate|interest rates?|inflation|tariffs?|gdp|"
        r"jobs report|unemployment|treasury yields?|sanctions?|oil prices?|"
        r"natural gas prices?|government shutdown|white house|war|ceasefire)\b"
    ),
    "analyst_or_investor_action": rx(
        r"\b(?:upgrades?|downgrades?|initiates? coverage|price target|"
        r"maintains? (?:buy|sell|hold|neutral|overweight|underweight|"
        r"outperform|underperform)|short seller|activist investor)\b"
    ),
    "ownership_or_insider_action": rx(
        r"\b(?:insider (?:buy|sale|sell|purchase|trade)|buys? stake|sells? stake|"
        r"takes? a stake|beneficial ownership|13d|13g)\b"
    ),
    "rumor_or_unconfirmed_plan": rx(
        r"\b(?:rumou?r|reportedly|hearing|unconfirmed|people familiar with the matter|"
        r"sources? (?:say|said)|exploring (?:a |the )?(?:sale|deal|options)|"
        r"considering (?:a |the )?(?:sale|deal|offer))\b"
    ),
    "stock_reaction": rx(
        r"\b(?:shares|stock)\b.{0,35}\b(?:higher|lower|up|down|rising|falling|"
        r"surging|sliding|soaring|tumbling|plunging|jumping|rallying|gains?|drops?)\b|"
        r"\bwhy (?:is |are )?.{0,70}\b(?:stock|shares)\b"
    ),
    "trading_mechanics": rx(
        r"\b(?:option alert|options activity|call sweep|put sweep|short interest|"
        r"trading halt|halted|resumption|technical signal|moving average)\b"
    ),
}


AUTHORITY_ACTION_RE = rx(
    r"(?:\b(?:fda|ftc|doj|sec|nhtsa|faa|fcc|epa|cms|cfius|court|judge|jury|"
    r"regulator|government|white house|department of [a-z ]+|european commission)\b"
    r".{0,120}\b(?:approv|clear|authoriz|deny|reject|block|sue|charg|fine|order|"
    r"rul|investigat|probe|recall|grant|revoke|ban|settle))|"
    r"(?:\b(?:approv|clear|authoriz|deny|reject|block|sue|charg|fine|order|rul|"
    r"investigat|probe|recall|grant|revoke|ban|settle)\w*\b.{0,120}"
    r"\b(?:fda|ftc|doj|sec|nhtsa|faa|fcc|epa|cms|cfius|court|judge|jury|"
    r"regulator|government|european commission)\b)"
)

COUNTERPARTY_ACTION_RE = rx(
    r"\b(?:customer|client|supplier|vendor|partner|distributor|union|landlord|"
    r"lender|creditor|competitor|bidder)\b.{0,120}"
    r"\b(?:award|select|order|sign|partner|cancel|terminate|renew|strike|reject|"
    r"accept|acquire|buy|sell|supply|distribute|default)\w*\b"
)

INDEPENDENT_DATA_RE = rx(
    r"\b(?:sensor tower|nielsen|circana|similarweb|appfigures|s3 partners|ortex|"
    r"placer\.ai|counterpoint research|idc|gartner|canalys|kantar|"
    r"cox automotive|mastercard spendingpulse|adobe analytics)\b"
)

COMPANY_ATTRIBUTION_RE = rx(
    r"\b(?:the company|company|management|chief executive|ceo|cfo)\b.{0,80}"
    r"\b(?:said|says|announced|reported|expects|forecasts?|guides?|confirmed|"
    r"disclosed|filed|reaffirmed|withdrew)\b"
)

PRIMARY_RELAY_RE = rx(
    r"^\s*-?\s*(?:sec filing|conference call|conf(?:erence)? call)\b|"
    r"\baccording to (?:an? )?(?:sec )?filing\b|\bin (?:an? )?8-k filing\b|"
    r"\bon (?:the |its )?(?:earnings|conference) call\b"
)

WIRE_MARKERS = {
    "reuters": rx(r"^\s*-?\s*reuters\b"),
    "bloomberg": rx(r"^\s*-?\s*bloomberg\b"),
    "cnbc": rx(r"^\s*-?\s*cnbc\b"),
    "dow_jones": rx(r"^\s*-?\s*dow jones\b"),
}

ANALYST_CHANNELS = {
    "Analyst Ratings", "Price Target", "Reiteration", "Initiation",
    "Downgrades", "Upgrades", "Analyst Color", "Short Sellers",
    "Short Ideas", "Long Ideas", "Opinion",
}
MARKET_CHANNELS = {
    "Trading Ideas", "Options", "Movers", "Technicals", "Intraday Update",
    "After-Hours Center", "Pre-Market Outlook", "Signals",
    "Movers & Shakers", "Market Summary",
}
RUMOR_CHANNELS = {"Rumors"}

# Products that are normally packaging, screening, historical comparison, or
# market commentary rather than a newly sourced operating fact.
EDITORIAL_PRODUCT_CODES = {
    "BZI-AAR", "BZI-AAR-UPDATE", "BZI-UOA", "BZI-POD", "BZI-SHORTHIST",
    "BZI-EP", "BZI-Recaps", "BZI-ROCE", "BZI-PE", "BZI-IA", "BZI-ExDiv",
    "BZI-Debt", "BZI-CROSS", "BZI-CONF", "BZI-WIIM", "BZI-TFM",
    "BZI-CC", "BZI-SHORT", "BZI-52Weeks",
}

INCIDENT_RE = rx(
    r"\b(?:outage|shutdown|disruption|fire|explosion|accident|walkout|"
    r"cyberattack|cyber attack|ransomware|data breach|recall|contamination|"
    r"hurricane|storm damage|flood|earthquake)\b"
    r"|\b(?:labor|worker|workers|union|employee|employees)\b.{0,50}\bstrike\b"
    r"|\bstrike\b.{0,50}\b(?:labor|worker|workers|union|employee|employees)\b"
)
MACRO_RE = EVENT_PROBES["macro_policy_or_geopolitics"]
RUMOR_RE = EVENT_PROBES["rumor_or_unconfirmed_plan"]
MARKET_RE = rx(
    EVENT_PROBES["stock_reaction"].pattern + "|" +
    EVENT_PROBES["trading_mechanics"].pattern
)
ANALYST_RE = EVENT_PROBES["analyst_or_investor_action"]


def parse_json_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def stable_sample_add(
    samples: list[tuple[int, dict[str, Any]]], record: dict[str, Any]
) -> None:
    score = int.from_bytes(
        hashlib.blake2b(record["id"].encode("utf-8"), digest_size=8).digest(),
        "big",
    )
    samples.append((score, record))
    samples.sort(key=lambda item: item[0])
    if len(samples) > SAMPLE_SIZE:
        samples.pop()


def load_primary_timelines(session) -> dict[str, list[tuple[datetime, str, str]]]:
    timelines: dict[str, list[tuple[datetime, str, str]]] = defaultdict(list)

    reports = session.run(
        """
        MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
        WHERE r.formType IN ['8-K', '10-Q', '10-K']
        RETURN c.ticker AS ticker, r.id AS id, r.formType AS form, r.created AS at
        """
    )
    for row in reports:
        at = parse_time(row["at"])
        ticker = row["ticker"]
        if at is not None and ticker:
            timelines[ticker].append((at, PRIMARY_FORMS[row["form"]], row["id"]))

    transcripts = session.run(
        """
        MATCH (t:Transcript)
        RETURN t.symbol AS ticker, t.id AS id, t.conference_datetime AS at
        """
    )
    for row in transcripts:
        at = parse_time(row["at"])
        ticker = row["ticker"]
        if at is not None and ticker:
            timelines[ticker].append((at, "transcript", row["id"]))

    for events in timelines.values():
        events.sort(key=lambda item: item[0])
    return timelines


def primary_proximity(
    events: list[tuple[datetime, str, str]], at: datetime
) -> dict[str, Any]:
    if not events:
        return {
            "relation": "no_company_primary_timeline",
            "same_day_types": [],
            "nearest_type": None,
            "nearest_seconds": None,
        }

    times = [item[0] for item in events]
    idx = bisect.bisect_left(times, at)
    candidates = []
    if idx:
        candidates.append(events[idx - 1])
    if idx < len(events):
        candidates.append(events[idx])
    nearest = min(candidates, key=lambda item: abs((item[0] - at).total_seconds()))
    nearest_seconds = int((nearest[0] - at).total_seconds())

    left = bisect.bisect_left(times, at - WEEK)
    right = bisect.bisect_right(times, at + WEEK)
    nearby = events[left:right]
    same_day_types = sorted({
        kind for source_at, kind, _ in nearby
        if source_at.date() == at.date()
    })
    prior_day = [item for item in nearby if at - DAY <= item[0] <= at]
    later_day = [item for item in nearby if at < item[0] <= at + DAY]
    prior_week = [item for item in nearby if item[0] <= at]
    later_week = [item for item in nearby if item[0] > at]

    if prior_day:
        relation = "primary_available_within_prior_24h"
    elif later_day:
        relation = "primary_arrives_within_next_24h"
    elif prior_week:
        relation = "primary_available_1_to_7d_before"
    elif later_week:
        relation = "primary_arrives_1_to_7d_after"
    else:
        relation = "no_primary_within_7d"

    return {
        "relation": relation,
        "same_day_types": same_day_types,
        "nearest_type": nearest[1],
        "nearest_seconds": nearest_seconds,
    }


def article_stream(session):
    return session.run(
        """
        MATCH (n:News)
        RETURN n.id AS id, n.created AS created, n.title AS title,
               n.teaser AS teaser, n.body AS body, n.url AS url,
               n.channels AS channels, n.tags AS tags, n.authors AS authors,
               [(n)-[:INFLUENCES]->(c:Company) | c.ticker] AS tickers
        """
    )


def source_role_signals(
    title: str,
    body: str,
    teaser: str,
    channels: set[str],
    tags: set[str],
    author: str,
) -> set[str]:
    text = "\n".join((title, teaser, body))
    signals: set[str] = set()

    if PRIMARY_RELAY_RE.search(text):
        signals.add("explicit_filing_or_call_relay")
    if COMPANY_ATTRIBUTION_RE.search(text):
        signals.add("company_or_management_statement")
    if AUTHORITY_ACTION_RE.search(text):
        signals.add("external_authority_action")
    if COUNTERPARTY_ACTION_RE.search(text):
        signals.add("counterparty_action")
    if INDEPENDENT_DATA_RE.search(text):
        signals.add("independent_measurement")
    if INCIDENT_RE.search(text):
        signals.add("observed_operating_incident")
    if MACRO_RE.search(title):
        signals.add("macro_or_world_condition")
    if channels & ANALYST_CHANNELS or ANALYST_RE.search(title):
        signals.add("analyst_or_investor_view")
    if channels & RUMOR_CHANNELS or RUMOR_RE.search(title):
        signals.add("rumor_or_unverified_claim")
    if channels & MARKET_CHANNELS or MARKET_RE.search(title):
        signals.add("market_reaction_or_mechanics")

    product_codes = {tag for tag in tags if tag.startswith("BZI-")}
    if product_codes & EDITORIAL_PRODUCT_CODES or author == "Benzinga Insights":
        signals.add("editorial_or_template_product")
    if any(pattern.search(body) for pattern in WIRE_MARKERS.values()):
        signals.add("external_wire_relay")
    return signals


def sample_record(
    row: Any,
    channels: list[str],
    tags: list[str],
    author: str,
    relation: dict[str, Any],
    event_hits: list[str],
    role_hits: list[str],
) -> dict[str, Any]:
    return {
        "id": row["id"],
        "created": row["created"],
        "ticker": (row["tickers"] or [None])[0],
        "title": row["title"],
        "author": author,
        "channels": channels,
        "tags": tags[:12],
        "body_prefix": (row["body"] or "")[:500],
        "primary_relation": relation["relation"],
        "same_day_primary_types": relation["same_day_types"],
        "event_signals": event_hits,
        "source_role_signals": role_hits,
    }


def add_relation_counts(counter: Counter, relation: dict[str, Any]) -> None:
    counter["articles"] += 1
    counter[f"relation:{relation['relation']}"] += 1
    for source_type in relation["same_day_types"]:
        counter[f"same_day:{source_type}"] += 1


def run_audit(session) -> dict[str, Any]:
    timelines = load_primary_timelines(session)
    timeline_summary = {
        "companies": len(timelines),
        "events": sum(len(events) for events in timelines.values()),
        "source_types": dict(Counter(
            source_type
            for events in timelines.values()
            for _, source_type, _ in events
        )),
    }

    overall: Counter = Counter()
    event_stats: dict[str, Counter] = defaultdict(Counter)
    role_stats: dict[str, Counter] = defaultdict(Counter)
    workflow_stats: dict[str, Counter] = defaultdict(Counter)
    channel_stats: dict[str, Counter] = defaultdict(Counter)
    source_marker_stats: dict[str, Counter] = defaultdict(Counter)
    event_hit_cardinality: Counter = Counter()
    role_hit_cardinality: Counter = Counter()
    event_combinations: Counter = Counter()
    role_combinations: Counter = Counter()
    samples: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)

    for row in article_stream(session):
        title = row["title"] or ""
        teaser = row["teaser"] or ""
        body = row["body"] or ""
        channels_list = [str(value) for value in parse_json_list(row["channels"])]
        tags_list = [str(value) for value in parse_json_list(row["tags"])]
        authors = parse_json_list(row["authors"])
        author = str(authors[0]) if authors else "<missing>"
        channels = set(channels_list)
        tags = set(tags_list)
        tickers = row["tickers"] or []
        ticker = tickers[0] if tickers else None
        at = parse_time(row["created"])

        if at is None:
            overall["invalid_created"] += 1
            continue
        relation = primary_proximity(timelines.get(ticker, []), at)
        add_relation_counts(overall, relation)

        if author == "Benzinga Insights":
            workflow = "insights_product"
        elif author == "Benzinga Newsdesk" and len(body) <= 200:
            workflow = "newsdesk_short_wire"
        elif author == "Benzinga Newsdesk":
            workflow = "newsdesk_long_wire"
        elif len(body) <= 200:
            workflow = "named_byline_short"
        else:
            workflow = "named_byline_long"
        add_relation_counts(workflow_stats[workflow], relation)

        event_hits = sorted(
            name for name, pattern in EVENT_PROBES.items() if pattern.search(title)
        )
        role_hits = sorted(source_role_signals(
            title, body, teaser, channels, tags, author
        ))
        event_hit_cardinality[str(len(event_hits))] += 1
        role_hit_cardinality[str(len(role_hits))] += 1
        if event_hits:
            event_combinations[" | ".join(event_hits)] += 1
        if role_hits:
            role_combinations[" | ".join(role_hits)] += 1

        record = sample_record(
            row, channels_list, tags_list, author, relation, event_hits, role_hits
        )
        for name in event_hits:
            add_relation_counts(event_stats[name], relation)
            stable_sample_add(samples[f"event:{name}"], record)
            if relation["relation"] == "no_primary_within_7d":
                stable_sample_add(samples[f"event:{name}:no_primary_7d"], record)
        for name in role_hits:
            add_relation_counts(role_stats[name], relation)
            stable_sample_add(samples[f"role:{name}"], record)
            if relation["relation"] == "no_primary_within_7d":
                stable_sample_add(samples[f"role:{name}:no_primary_7d"], record)
        for channel in channels:
            add_relation_counts(channel_stats[channel], relation)

        for marker, pattern in WIRE_MARKERS.items():
            if pattern.search(body):
                add_relation_counts(source_marker_stats[marker], relation)
                stable_sample_add(samples[f"source_marker:{marker}"], record)

    def serialize_stats(stats: dict[str, Counter]) -> dict[str, dict[str, int]]:
        return {
            key: dict(value)
            for key, value in sorted(
                stats.items(), key=lambda item: (-item[1]["articles"], item[0])
            )
        }

    def top_combinations(counter: Counter, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {"signals": key.split(" | "), "articles": count}
            for key, count in counter.most_common(limit)
        ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warning": (
            "All labels in this file are broad deterministic signals. A nearby "
            "filing or call is not proof of duplicate content, and no nearby "
            "primary source is not proof that a news fact is unique."
        ),
        "primary_timeline": timeline_summary,
        "overall": dict(overall),
        "workflow_source_proximity": serialize_stats(workflow_stats),
        "event_signal_source_proximity": serialize_stats(event_stats),
        "source_role_signal_proximity": serialize_stats(role_stats),
        "channel_source_proximity": serialize_stats(channel_stats),
        "explicit_wire_markers": serialize_stats(source_marker_stats),
        "event_signal_count_per_article": dict(sorted(event_hit_cardinality.items())),
        "source_role_signal_count_per_article": dict(sorted(role_hit_cardinality.items())),
        "top_event_signal_combinations": top_combinations(event_combinations),
        "top_source_role_signal_combinations": top_combinations(role_combinations),
        "samples": {
            key: [record for _, record in value]
            for key, value in sorted(samples.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/news_driver_source_audit.json"),
    )
    args = parser.parse_args()

    load_dotenv()
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    if not all((uri, username, password)):
        raise SystemExit("NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are required")

    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        with driver.session(default_access_mode=READ_ACCESS, fetch_size=500) as session:
            result = run_audit(session)
    finally:
        driver.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n")
    print(f"Wrote {args.output}")
    print(json.dumps(result["overall"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
