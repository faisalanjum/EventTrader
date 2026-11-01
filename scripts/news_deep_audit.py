#!/usr/bin/env python3
"""Read-only, repeatable audit of every News node in Neo4j.

The script does not produce a final article taxonomy. It measures raw signals,
tests explicit working hypotheses, and writes a compact JSON profile that a
later deterministic classifier can use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable
from urllib.parse import urlparse

from dotenv import load_dotenv
from neo4j import GraphDatabase, READ_ACCESS


SAMPLE_SIZE = 8
TOP_N = 30
NUMBER_RE = re.compile(
    r"(?<![a-z])(?:[$€£¥])?[-+]?\d[\d,]*(?:\.\d+)?(?:%|x|m|b|k|mm|bn)?",
    re.IGNORECASE,
)
SPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[a-z][a-z0-9&'-]{1,}")
PUNCT_RE = re.compile(r"[^a-z0-9<>%$&+'-]+")

STOPWORDS = {
    "about", "after", "again", "against", "ahead", "along", "also", "amid",
    "among", "around", "because", "before", "being", "below", "between", "both",
    "could", "despite", "during", "each", "from", "have", "having", "into", "just",
    "more", "most", "other", "over", "says", "shares", "should", "some", "stock",
    "stocks", "than", "that", "their", "there", "these", "they", "this", "through",
    "under", "very", "what", "when", "where", "which", "while", "with", "would",
    "your", "benzinga", "company", "companies", "today", "week", "year",
}

# Broad headline probes. These measure metadata coverage; they are deliberately
# not presented as a finished classifier or as ground truth.
TITLE_SIGNAL_SPECS = {
    "earnings_result": {
        "pattern": r"\b(?:eps|earnings|revenue|sales)\b.{0,80}\b(?:beat|miss|estimate|reported|reports|rose|fell)\b|\b(?:beat|miss)(?:es)?\b.{0,80}\b(?:eps|earnings|revenue|sales|estimate)\b",
        "expected_channels": ["Earnings"],
    },
    "guidance_or_outlook": {
        "pattern": r"\b(?:guidance|outlook|forecast|reaffirm(?:s|ed)?|guides|sees\s+(?:q[1-4]|fy|20\d\d)|expects\s+(?:q[1-4]|fy|20\d\d))\b",
        "expected_channels": ["Guidance"],
    },
    "dividend_action": {
        "pattern": r"\b(?:declare|declares|declared|raise|raises|raised|increase|increases|increased|cut|cuts|reduce|reduces|suspend|suspends|maintain|maintains|approve|approves|announces?)\b.{0,60}\bdividend\b|\bdividend\b.{0,60}\b(?:declared|raised|increased|cut|reduced|suspended|maintained|approved)\b",
        "expected_channels": ["Dividends"],
    },
    "merger_or_acquisition": {
        "pattern": r"\b(?:acquire|acquires|acquired|acquisition|merger|merge|merges|buyout|takeover|to buy|agrees to buy|strategic alternatives)\b",
        "expected_channels": ["M&A"],
    },
    "contract_or_order": {
        "pattern": r"\b(?:award|awards|awarded|win|wins|won|secure|secures|secured|receive|receives|received)\b.{0,70}\b(?:contract|order)\b|\bcontract\b.{0,60}\b(?:award|worth|valued|from|ceiling)\b",
        "expected_channels": ["Contracts"],
    },
    "fda_action": {
        "pattern": r"\bfda\b",
        "expected_channels": ["FDA"],
    },
    "management_change": {
        "pattern": r"\b(?:appoints?|appointed|names?|named|hires?|hired)\b.{0,80}\b(?:ceo|cfo|chief|president|director|board|chair)|\b(?:ceo|cfo|chief|president|director|chair)\b.{0,60}\b(?:resigns?|retires?|steps down|departs?|departure)\b",
        "expected_channels": ["Management"],
    },
    "legal_or_enforcement": {
        "pattern": r"\b(?:lawsuit|sues|sued|suing|settlement|settles|settled|court|jury|subpoena|antitrust|doj|ftc|sec charges|investigation|probe)\b",
        "expected_channels": ["Legal"],
    },
    "buyback_or_repurchase": {
        "pattern": r"\b(?:buyback|share repurchase|repurchases? (?:its )?(?:shares|stock)|repurchase authorization)\b",
        "expected_channels": ["Buybacks"],
    },
    "equity_offering": {
        "pattern": r"\b(?:public offering|stock offering|share offering|registered direct|private placement|at-the-market offering|atm offering)\b",
        "expected_channels": ["Offerings"],
    },
    "debt_financing": {
        "pattern": r"\b(?:senior notes|convertible notes|credit facility|debt financing|term loan|revolving credit|bond offering)\b",
        "expected_channels": ["Financing"],
    },
    "stock_split": {
        "pattern": r"\b(?:stock split|share split|reverse split|split-adjusted)\b",
        "expected_channels": ["Stock Split"],
    },
    "product_launch": {
        "pattern": r"\b(?:launches|launched|launching|unveils|unveiled|introduces|introduced|debuts|debuted)\b",
        "expected_channels": [],
    },
    "partnership_or_collaboration": {
        "pattern": r"\b(?:partners with|partnership|collaboration|collaborates with|strategic alliance)\b",
        "expected_channels": [],
    },
    "clinical_trial_or_data": {
        "pattern": r"\b(?:phase (?:1|2|3|i|ii|iii)|clinical trial|clinical data|topline (?:data|results)|primary endpoint)\b",
        "expected_channels": [],
    },
    "layoff_or_workforce_cut": {
        "pattern": r"\b(?:layoffs?|lays off|laid off|job cuts?|cuts? jobs|workforce reduction|reduce(?:s|d)? (?:its )?workforce)\b",
        "expected_channels": [],
    },
    "bankruptcy": {
        "pattern": r"\b(?:bankruptcy|chapter 11|chapter 7)\b",
        "expected_channels": [],
    },
    "restructuring": {
        "pattern": r"\b(?:restructuring|restructure|restructures|restructuring plan)\b",
        "expected_channels": [],
    },
    "analyst_action": {
        "pattern": r"\b(?:upgrades?|downgrades?|initiates? coverage|maintains? (?:buy|sell|hold|neutral|overweight|underweight|outperform|underperform)|price target)\b",
        "expected_channels": ["Analyst Ratings"],
    },
    "stock_move": {
        "pattern": r"\b(?:shares|stock) (?:are |is )?(?:trading |moving )?(?:higher|lower|up|down|rising|falling|surging|sliding|soaring|tumbling|plunging|jumping|rallying)\b|\bwhy (?:is |are )?.{0,60}\b(?:stock|shares)\b",
        "expected_channels": ["Movers", "Trading Ideas"],
    },
    "macro_or_policy": {
        "pattern": r"\b(?:federal reserve|fed rate|interest rates?|inflation|tariffs?|gdp|jobs report|unemployment|white house|president trump|president biden)\b",
        "expected_channels": ["Macro Economic Events", "Federal Reserve", "Economics", "Politics", "Government"],
    },
}
TITLE_SIGNALS = {
    name: {**spec, "regex": re.compile(spec["pattern"], re.IGNORECASE)}
    for name, spec in TITLE_SIGNAL_SPECS.items()
}

# The five groups proposed in the working hypothesis. A channel may appear in
# more than one conceptual axis in reality; these sets only test whether the
# raw channel field can anchor the proposed A-E model.
PROPOSED_CHANNEL_BUCKETS = {
    "A_company_action": {
        "Dividends", "Management", "M&A", "Contracts", "FDA", "Legal",
        "Buybacks", "Offerings", "Asset Sales", "IPOs", "Financing",
        "Stock Split",
    },
    "B_company_numbers": {
        "Earnings", "Guidance", "Earnings Beats", "Earnings Misses",
    },
    "C_outside_voice": {
        "Analyst Ratings", "Price Target", "Reiteration", "Initiation",
        "Downgrades", "Upgrades", "Analyst Color", "Short Sellers", "Rumors",
        "Hedge Funds", "Insider Trades", "Opinion", "Interview", "Termination",
    },
    "D_world_or_policy": {
        "Politics", "Government", "Regulations", "Economics", "Global", "Asia",
        "Eurozone", "Macro Economic Events", "Federal Reserve", "Econ #s",
        "Treasuries", "Latin America", "Emerging Markets", "SEC",
    },
    "E_stock_behavior": {
        "Trading Ideas", "Options", "Movers", "Short Ideas", "Long Ideas",
        "Technicals", "Intraday Update", "After-Hours Center",
        "Pre-Market Outlook", "Signals", "Movers & Shakers", "Market Summary",
    },
}

SOURCE_MARKERS = {
    "Reuters": re.compile(r"^\s*-?\s*reuters\b", re.IGNORECASE),
    "Bloomberg": re.compile(r"^\s*-?\s*bloomberg\b", re.IGNORECASE),
    "SEC filing": re.compile(r"^\s*-?\s*sec filing\b", re.IGNORECASE),
    "conference call": re.compile(r"^\s*-?\s*(?:conf(?:erence)? call)\b", re.IGNORECASE),
    "CNBC": re.compile(r"^\s*-?\s*cnbc\b", re.IGNORECASE),
    "Dow Jones": re.compile(r"^\s*-?\s*dow jones\b", re.IGNORECASE),
}

BEAT_TERM_RE = re.compile(r"\b(?:beat|beats|beating)\b", re.IGNORECASE)
MISS_TERM_RE = re.compile(r"\b(?:miss|misses|missing)\b", re.IGNORECASE)


def length_bucket(value: int) -> str:
    if value == 0:
        return "0"
    if value <= 20:
        return "1-20"
    if value <= 100:
        return "21-100"
    if value <= 200:
        return "101-200"
    if value <= 500:
        return "201-500"
    if value <= 1000:
        return "501-1000"
    if value <= 2500:
        return "1001-2500"
    if value <= 5000:
        return "2501-5000"
    return "5001+"


def url_section(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if not parts:
        return "<root>"
    root = parts[0]
    hierarchical_roots = {
        "news", "insights", "analyst-ratings", "markets", "trading-ideas",
        "general", "government", "tech", "media",
    }
    if root in hierarchical_roots and len(parts) > 1 and not parts[1].isdigit():
        return f"{root}/{parts[1]}"
    return root


def parse_json(value: Any, expected: type, errors: Counter) -> Any:
    if value is None or value == "":
        return expected()
    if isinstance(value, expected):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        errors[f"invalid_{expected.__name__}"] += 1
        return expected()
    if not isinstance(parsed, expected):
        errors[f"wrong_type_{expected.__name__}"] += 1
        return expected()
    return parsed


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "p25": None, "median": None,
                "p75": None, "p90": None, "p99": None, "max": None, "mean": None}
    return {
        "count": len(values),
        "min": min(values),
        "p25": round(percentile(values, 0.25), 2),
        "median": round(percentile(values, 0.50), 2),
        "p75": round(percentile(values, 0.75), 2),
        "p90": round(percentile(values, 0.90), 2),
        "p99": round(percentile(values, 0.99), 2),
        "max": max(values),
        "mean": round(mean(values), 2),
    }


def top(counter: Counter, n: int = TOP_N) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(n)]


def top_map(counter: Counter, n: int = TOP_N) -> dict[str, int]:
    return dict(counter.most_common(n))


def normalize_tag(tag: str) -> str:
    return SPACE_RE.sub(" ", re.sub(r"[^a-z0-9]+", " ", tag.casefold())).strip()


def normalize_title(title: str, company_names: Iterable[str], tickers: Iterable[str]) -> str:
    value = title.casefold()
    for company_name in sorted((x for x in company_names if x), key=len, reverse=True):
        if len(company_name) >= 3:
            value = re.sub(rf"\b{re.escape(company_name.casefold())}\b", " <company> ", value)
    for ticker in tickers:
        if ticker and len(ticker) >= 1:
            value = re.sub(rf"(?<![a-z0-9]){re.escape(ticker.casefold())}(?![a-z0-9])", " <ticker> ", value)
    value = NUMBER_RE.sub(" <num> ", value)
    value = re.sub(r"\b(?:q[1-4]|fy)\s*<num>\b", " <period> ", value)
    value = PUNCT_RE.sub(" ", value)
    return SPACE_RE.sub(" ", value).strip()


def title_terms(title: str, company_names: Iterable[str], tickers: Iterable[str]) -> list[str]:
    value = title.casefold()
    for item in list(company_names) + list(tickers):
        if item and len(item) >= 2:
            value = value.replace(item.casefold(), " ")
    return [token for token in TOKEN_RE.findall(value) if token not in STOPWORDS and not token.isdigit()]


def stable_sample_add(samples: list[tuple[int, dict[str, Any]]], record: dict[str, Any]) -> None:
    digest = hashlib.blake2b(record["id"].encode("utf-8"), digest_size=8).digest()
    score = int.from_bytes(digest, "big")
    samples.append((score, record))
    samples.sort(key=lambda item: item[0])
    if len(samples) > SAMPLE_SIZE:
        samples.pop()


def serialize_samples(samples: list[tuple[int, dict[str, Any]]]) -> list[dict[str, Any]]:
    return [record for _, record in samples]


def article_stream(session):
    query = """
    MATCH (n:News)
    RETURN n.id AS id,
           n.title AS title,
           n.teaser AS teaser,
           substring(coalesce(n.body, ''), 0, 700) AS body_prefix,
           size(coalesce(n.body, '')) AS body_length,
           size(coalesce(n.teaser, '')) AS teaser_length,
           n.created AS created,
           n.updated AS updated,
           n.url AS url,
           n.channels AS channels,
           n.tags AS tags,
           n.authors AS authors,
           n.market_session AS market_session,
           n.returns_schedule AS returns_schedule,
           [(n)-[:INFLUENCES]->(c:Company) | c.ticker] AS tickers,
           [(n)-[:INFLUENCES]->(c:Company) | c.name] AS company_names
    """
    return session.run(query)


def run_audit(session) -> dict[str, Any]:
    parse_errors: Counter = Counter()
    coverage: Counter = Counter()
    channel_counts: Counter = Counter()
    channel_positions: dict[str, Counter] = defaultdict(Counter)
    channel_years: dict[str, Counter] = defaultdict(Counter)
    channel_authors: dict[str, Counter] = defaultdict(Counter)
    channel_tags: dict[str, Counter] = defaultdict(Counter)
    channel_sessions: dict[str, Counter] = defaultdict(Counter)
    channel_terms: dict[str, Counter] = defaultdict(Counter)
    channel_templates: dict[str, Counter] = defaultdict(Counter)
    channel_body: dict[str, Counter] = defaultdict(Counter)
    channel_body_lengths: dict[str, list[int]] = defaultdict(list)
    channel_url_sections: dict[str, Counter] = defaultdict(Counter)
    channel_tagged: Counter = Counter()
    channel_samples: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    channel_first_seen: dict[str, str] = {}
    channel_last_seen: dict[str, str] = {}
    channel_pairs: Counter = Counter()
    channel_cardinality: Counter = Counter()
    channel_combos: Counter = Counter()
    channel_sequences: Counter = Counter()

    tag_counts: Counter = Counter()
    tag_years: dict[str, Counter] = defaultdict(Counter)
    tag_channels: dict[str, Counter] = defaultdict(Counter)
    tag_authors: dict[str, Counter] = defaultdict(Counter)
    tag_variants: dict[str, Counter] = defaultdict(Counter)
    tag_pairs: Counter = Counter()
    tag_cardinality: Counter = Counter()
    tag_presence_years: dict[str, Counter] = defaultdict(Counter)
    bzi_tag_counts: Counter = Counter()
    bzi_tag_channel_combos: dict[str, Counter] = defaultdict(Counter)
    articles_with_bzi_tag = 0

    author_counts: Counter = Counter()
    author_years: dict[str, Counter] = defaultdict(Counter)
    author_channels: dict[str, Counter] = defaultdict(Counter)
    author_tags: dict[str, Counter] = defaultdict(Counter)
    author_sessions: dict[str, Counter] = defaultdict(Counter)
    author_templates: dict[str, Counter] = defaultdict(Counter)
    author_body: dict[str, Counter] = defaultdict(Counter)
    author_body_lengths: dict[str, list[int]] = defaultdict(list)
    author_url_sections: dict[str, Counter] = defaultdict(Counter)
    author_tagged: Counter = Counter()
    author_first_seen: dict[str, str] = {}
    author_last_seen: dict[str, str] = {}
    author_cardinality: Counter = Counter()

    year_counts: Counter = Counter()
    month_counts: Counter = Counter()
    weekday_counts: Counter = Counter()
    hour_counts: Counter = Counter()
    session_counts: Counter = Counter()
    session_years: dict[str, Counter] = defaultdict(Counter)
    company_cardinality: Counter = Counter()
    company_counts: Counter = Counter()
    returns_shapes: Counter = Counter()
    returns_value_types: dict[str, Counter] = defaultdict(Counter)
    host_counts: Counter = Counter()
    url_path_roots: Counter = Counter()
    url_section_counts: Counter = Counter()
    url_section_years: dict[str, Counter] = defaultdict(Counter)
    url_section_authors: dict[str, Counter] = defaultdict(Counter)
    url_section_channels: dict[str, Counter] = defaultdict(Counter)
    url_section_tags: dict[str, Counter] = defaultdict(Counter)
    url_section_body_lengths: dict[str, list[int]] = defaultdict(list)
    url_section_tagged: Counter = Counter()
    url_section_samples: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    exact_titles: Counter = Counter()
    exact_title_ids: dict[str, list[str]] = defaultdict(list)
    templates: Counter = Counter()
    template_examples: dict[str, list[str]] = defaultdict(list)
    opening_phrases: Counter = Counter()
    overall_terms: Counter = Counter()
    body_prefixes: Counter = Counter()
    title_lengths: list[float] = []
    body_lengths: list[float] = []
    teaser_lengths: list[float] = []
    body_length_buckets: Counter = Counter()
    text_field_shapes: Counter = Counter()
    update_delays: list[float] = []
    update_delay_buckets: Counter = Counter()
    created_offsets: Counter = Counter()
    first_created: str | None = None
    last_created: str | None = None
    id_shapes: Counter = Counter()
    id_counts: Counter = Counter()
    title_signal_counts: Counter = Counter()
    title_signal_channel_hits: Counter = Counter()
    title_signal_years: dict[str, Counter] = defaultdict(Counter)
    title_signal_authors: dict[str, Counter] = defaultdict(Counter)
    title_signal_channels: dict[str, Counter] = defaultdict(Counter)
    title_signal_missed_samples: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    title_signal_pairs: Counter = Counter()
    title_signal_cardinality: Counter = Counter()
    title_signal_union = 0
    source_style_counts: Counter = Counter()
    source_style_years: dict[str, Counter] = defaultdict(Counter)
    source_style_channels: dict[str, Counter] = defaultdict(Counter)
    source_style_tags: dict[str, Counter] = defaultdict(Counter)
    source_style_url_sections: dict[str, Counter] = defaultdict(Counter)
    source_style_body_lengths: dict[str, list[int]] = defaultdict(list)
    source_style_tagged: Counter = Counter()
    source_style_teaser: dict[str, Counter] = defaultdict(Counter)
    source_style_templates: dict[str, Counter] = defaultdict(Counter)
    source_markers: Counter = Counter()
    source_marker_authors: dict[str, Counter] = defaultdict(Counter)
    proposed_bucket_counts: Counter = Counter()
    proposed_bucket_combinations: Counter = Counter()
    proposed_bucket_cardinality: Counter = Counter()
    proposed_no_anchor_samples: list[tuple[int, dict[str, Any]]] = []
    earnings_label_rollout: dict[str, Counter] = defaultdict(Counter)
    earnings_child_summary: Counter = Counter()
    earnings_child_without_parent_samples: list[tuple[int, dict[str, Any]]] = []
    earnings_text_without_child_samples: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    company_day_counts: Counter = Counter()
    company_day_titles: dict[str, list[str]] = defaultdict(list)
    special_samples: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    total = 0

    for raw in article_stream(session):
        total += 1
        article_id = raw["id"] or ""
        title = raw["title"] or ""
        teaser = raw["teaser"] or ""
        body_prefix = raw["body_prefix"] or ""
        body_length = int(raw["body_length"] or 0)
        teaser_length = int(raw["teaser_length"] or 0)
        created = raw["created"] or ""
        updated = raw["updated"] or ""
        channels = [str(x).strip() for x in parse_json(raw["channels"], list, parse_errors) if str(x).strip()]
        tags = [str(x).strip() for x in parse_json(raw["tags"], list, parse_errors) if str(x).strip()]
        authors = [str(x).strip() for x in parse_json(raw["authors"], list, parse_errors) if str(x).strip()]
        returns_schedule = parse_json(raw["returns_schedule"], dict, parse_errors)
        tickers = [x for x in (raw["tickers"] or []) if x]
        company_names = [x for x in (raw["company_names"] or []) if x]
        market_session = raw["market_session"] or "<missing>"
        year = created[:4] if len(created) >= 4 else "<invalid>"
        month = created[:7] if len(created) >= 7 else "<invalid>"
        article_date = created[:10] if len(created) >= 10 else "<invalid>"
        first_created = min(first_created, created) if first_created else created
        last_created = max(last_created, created) if last_created else created
        id_counts[article_id] += 1
        id_shapes["bzNews_numeric" if re.fullmatch(r"bzNews_\d+", article_id) else "other"] += 1
        if len(created) >= 6 and re.search(r"[+-]\d\d:\d\d$", created):
            created_offsets[created[-6:]] += 1
        else:
            created_offsets["<missing_or_invalid>"] += 1

        coverage["title"] += bool(title)
        coverage["teaser"] += bool(teaser)
        coverage["body"] += body_length > 0
        coverage["created"] += bool(created)
        coverage["updated"] += bool(updated)
        coverage["url"] += bool(raw["url"])
        coverage["channels"] += bool(channels)
        coverage["tags"] += bool(tags)
        coverage["authors"] += bool(authors)
        coverage["market_session"] += market_session != "<missing>"
        coverage["returns_schedule"] += bool(returns_schedule)
        coverage["company"] += bool(tickers)
        title_lengths.append(len(title))
        body_lengths.append(body_length)
        teaser_lengths.append(teaser_length)
        body_length_buckets[length_bucket(body_length)] += 1
        if body_length and teaser:
            text_field_shapes["body_and_teaser"] += 1
        elif body_length:
            text_field_shapes["body_only"] += 1
        elif teaser:
            text_field_shapes["teaser_only"] += 1
        else:
            text_field_shapes["neither_body_nor_teaser"] += 1

        year_counts[year] += 1
        month_counts[month] += 1
        session_counts[market_session] += 1
        session_years[market_session][year] += 1
        company_cardinality[len(tickers)] += 1
        for ticker in set(tickers):
            company_counts[ticker] += 1
            company_day_key = f"{ticker} | {article_date}"
            company_day_counts[company_day_key] += 1
            if len(company_day_titles[company_day_key]) < 8:
                company_day_titles[company_day_key].append(title)
        returns_shapes[tuple(sorted(returns_schedule.keys()))] += 1
        for key in ("hourly", "session", "daily"):
            value = returns_schedule.get(key)
            returns_value_types[key][type(value).__name__ if value is not None else "missing"] += 1
        tag_presence_years[year]["tagged" if tags else "untagged"] += 1

        try:
            created_dt = datetime.fromisoformat(created)
            weekday_counts[created_dt.strftime("%A")] += 1
            hour_counts[f"{created_dt.hour:02d}"] += 1
            if updated:
                delay = (datetime.fromisoformat(updated) - created_dt).total_seconds()
                update_delays.append(delay)
                if delay == 0:
                    update_delay_buckets["0 seconds"] += 1
                elif delay <= 1:
                    update_delay_buckets["1 second"] += 1
                elif delay <= 60:
                    update_delay_buckets["2-60 seconds"] += 1
                elif delay <= 3600:
                    update_delay_buckets["1 minute-1 hour"] += 1
                elif delay <= 86400:
                    update_delay_buckets["1 hour-1 day"] += 1
                elif delay <= 604800:
                    update_delay_buckets["1-7 days"] += 1
                elif delay <= 2592000:
                    update_delay_buckets["7-30 days"] += 1
                else:
                    update_delay_buckets[">30 days"] += 1
        except (TypeError, ValueError):
            parse_errors["invalid_datetime"] += 1

        section = "<missing>"
        if raw["url"]:
            parsed_url = urlparse(raw["url"])
            host_counts[parsed_url.netloc.casefold()] += 1
            root = next((part for part in parsed_url.path.split("/") if part), "<root>")
            url_path_roots[root] += 1
            section = url_section(raw["url"])
            url_section_counts[section] += 1
            url_section_years[section][year] += 1
            url_section_body_lengths[section].append(body_length)
            if tags:
                url_section_tagged[section] += 1

        channel_cardinality[len(channels)] += 1
        author_cardinality[len(authors)] += 1
        tag_cardinality[len(tags)] += 1
        channel_sequences[" | ".join(channels)] += 1
        channel_combos[" | ".join(sorted(set(channels)))] += 1
        exact_titles[title] += 1
        if len(exact_title_ids[title]) < 5:
            exact_title_ids[title].append(article_id)

        template = normalize_title(title, company_names, tickers)
        templates[template] += 1
        if len(template_examples[template]) < 3 and title not in template_examples[template]:
            template_examples[template].append(title)
        terms = title_terms(title, company_names, tickers)
        overall_terms.update(set(terms))
        opening_phrases[" ".join(template.split()[:6])] += 1
        normalized_prefix = normalize_title(body_prefix[:250], company_names, tickers)
        if normalized_prefix:
            body_prefixes[" ".join(normalized_prefix.split()[:14])] += 1

        sample_record = {
            "id": article_id,
            "created": created,
            "title": title,
            "authors": authors,
            "channels": channels,
            "tags": tags[:10],
            "body_length": body_length,
            "body_prefix": SPACE_RE.sub(" ", body_prefix).strip()[:500],
            "tickers": tickers,
            "url_section": section,
        }

        has_earnings = "Earnings" in channels
        has_beat_label = "Earnings Beats" in channels
        has_miss_label = "Earnings Misses" in channels
        has_beat_text = bool(BEAT_TERM_RE.search(title))
        has_miss_text = bool(MISS_TERM_RE.search(title))
        if has_earnings:
            rollout = earnings_label_rollout[year]
            rollout["earnings_articles"] += 1
            rollout["beat_label"] += has_beat_label
            rollout["miss_label"] += has_miss_label
            rollout["beat_text"] += has_beat_text
            rollout["miss_text"] += has_miss_text
            rollout["beat_text_without_label"] += has_beat_text and not has_beat_label
            rollout["miss_text_without_label"] += has_miss_text and not has_miss_label
            rollout["both_child_labels"] += has_beat_label and has_miss_label
            if has_beat_text and not has_beat_label:
                stable_sample_add(earnings_text_without_child_samples["beat"], sample_record)
            if has_miss_text and not has_miss_label:
                stable_sample_add(earnings_text_without_child_samples["miss"], sample_record)
        if has_beat_label or has_miss_label:
            earnings_child_summary["articles_with_any_child_label"] += 1
            earnings_child_summary["beat_label_articles"] += has_beat_label
            earnings_child_summary["miss_label_articles"] += has_miss_label
            earnings_child_summary["both_child_labels"] += has_beat_label and has_miss_label
            earnings_child_summary["child_without_parent"] += not has_earnings
            earnings_child_summary["beat_label_without_beat_text"] += has_beat_label and not has_beat_text
            earnings_child_summary["miss_label_without_miss_text"] += has_miss_label and not has_miss_text
            if not has_earnings:
                stable_sample_add(earnings_child_without_parent_samples, sample_record)

        if unique_authors := list(dict.fromkeys(authors)):
            primary_author = unique_authors[0]
        else:
            primary_author = "<missing>"
        if primary_author == "Benzinga Insights":
            source_style = "benzinga_insights_template_product"
        elif primary_author == "Benzinga Newsdesk" and body_length <= 200:
            source_style = "newsdesk_wire_short"
        elif primary_author == "Benzinga Newsdesk":
            source_style = "newsdesk_wire_long"
        elif body_length <= 200:
            source_style = "named_byline_short"
        else:
            source_style = "named_byline_long"
        source_style_counts[source_style] += 1
        source_style_years[source_style][year] += 1
        source_style_body_lengths[source_style].append(body_length)
        source_style_url_sections[source_style][section] += 1
        source_style_teaser[source_style]["with_teaser" if teaser else "without_teaser"] += 1
        source_style_templates[source_style][template] += 1
        if tags:
            source_style_tagged[source_style] += 1
        for channel in set(channels):
            source_style_channels[source_style][channel] += 1
        for tag in set(tags):
            source_style_tags[source_style][tag] += 1

        for marker_name, marker_re in SOURCE_MARKERS.items():
            if marker_re.search(body_prefix):
                source_markers[marker_name] += 1
                source_marker_authors[marker_name][primary_author] += 1

        if section != "<missing>":
            for author in set(authors):
                url_section_authors[section][author] += 1
            for channel in set(channels):
                url_section_channels[section][channel] += 1
            for tag in set(tags):
                url_section_tags[section][tag] += 1
            stable_sample_add(url_section_samples[section], sample_record)

        proposed_hits = sorted(
            name for name, members in PROPOSED_CHANNEL_BUCKETS.items()
            if members.intersection(channels)
        )
        proposed_bucket_cardinality[len(proposed_hits)] += 1
        proposed_bucket_combinations[" | ".join(proposed_hits)] += 1
        for name in proposed_hits:
            proposed_bucket_counts[name] += 1
        if not proposed_hits:
            stable_sample_add(proposed_no_anchor_samples, sample_record)

        if not channels:
            stable_sample_add(special_samples["no_channels"], sample_record)
        if not tags:
            stable_sample_add(special_samples["no_tags"], sample_record)
        if not body_length:
            stable_sample_add(special_samples["no_body"], sample_record)
        if not tickers:
            stable_sample_add(special_samples["no_company"], sample_record)

        article_bzi_tags = [tag for tag in set(tags) if tag.upper().startswith("BZI-")]
        if article_bzi_tags:
            articles_with_bzi_tag += 1
        channel_combo = " | ".join(sorted(set(channels)))
        for tag in article_bzi_tags:
            bzi_tag_counts[tag] += 1
            bzi_tag_channel_combos[tag][channel_combo] += 1

        matched_signals = []
        for signal_name, signal_spec in TITLE_SIGNALS.items():
            if not signal_spec["regex"].search(title):
                continue
            matched_signals.append(signal_name)
            title_signal_counts[signal_name] += 1
            title_signal_years[signal_name][year] += 1
            title_signal_authors[signal_name][primary_author] += 1
            for channel in set(channels):
                title_signal_channels[signal_name][channel] += 1
            expected = signal_spec["expected_channels"]
            hit = not expected or any(channel in channels for channel in expected)
            if hit:
                title_signal_channel_hits[signal_name] += 1
            else:
                stable_sample_add(title_signal_missed_samples[signal_name], sample_record)
        for i, left in enumerate(sorted(matched_signals)):
            for right in sorted(matched_signals)[i + 1:]:
                title_signal_pairs[f"{left} | {right}"] += 1
        title_signal_cardinality[len(matched_signals)] += 1
        title_signal_union += bool(matched_signals)

        unique_channels = list(dict.fromkeys(channels))
        unique_tags = list(dict.fromkeys(tags))
        unique_authors = list(dict.fromkeys(authors))
        for index, channel in enumerate(channels):
            channel_positions[channel][str(index + 1)] += 1
        for channel in unique_channels:
            channel_counts[channel] += 1
            channel_years[channel][year] += 1
            channel_sessions[channel][market_session] += 1
            channel_body[channel]["with_body" if body_length else "without_body"] += 1
            channel_body[channel]["with_teaser" if teaser else "without_teaser"] += 1
            channel_body_lengths[channel].append(body_length)
            channel_url_sections[channel][section] += 1
            if tags:
                channel_tagged[channel] += 1
            channel_templates[channel][template] += 1
            channel_terms[channel].update(set(terms))
            for author in unique_authors:
                channel_authors[channel][author] += 1
            for tag in unique_tags:
                channel_tags[channel][tag] += 1
            stable_sample_add(channel_samples[channel], sample_record)
            channel_first_seen[channel] = min(channel_first_seen.get(channel, created), created)
            channel_last_seen[channel] = max(channel_last_seen.get(channel, created), created)
        for i, left in enumerate(sorted(set(unique_channels))):
            for right in sorted(set(unique_channels))[i + 1:]:
                channel_pairs[f"{left} | {right}"] += 1

        for tag in unique_tags:
            tag_counts[tag] += 1
            tag_years[tag][year] += 1
            tag_variants[normalize_tag(tag)][tag] += 1
            for channel in unique_channels:
                tag_channels[tag][channel] += 1
            for author in unique_authors:
                tag_authors[tag][author] += 1
        for i, left in enumerate(sorted(set(unique_tags))):
            for right in sorted(set(unique_tags))[i + 1:]:
                tag_pairs[f"{left} | {right}"] += 1

        for author in unique_authors:
            author_counts[author] += 1
            author_years[author][year] += 1
            author_sessions[author][market_session] += 1
            author_templates[author][template] += 1
            author_body[author]["with_body" if body_length else "without_body"] += 1
            author_body[author]["with_teaser" if teaser else "without_teaser"] += 1
            author_body_lengths[author].append(body_length)
            author_url_sections[author][section] += 1
            if tags:
                author_tagged[author] += 1
            for channel in unique_channels:
                author_channels[author][channel] += 1
            for tag in unique_tags:
                author_tags[author][tag] += 1
            author_first_seen[author] = min(author_first_seen.get(author, created), created)
            author_last_seen[author] = max(author_last_seen.get(author, created), created)

    duplicate_title_groups = Counter({k: v for k, v in exact_titles.items() if k and v > 1})
    repeated_templates = Counter({k: v for k, v in templates.items() if k and v > 1})

    channels_out = {}
    for channel, count in channel_counts.most_common():
        cochannels = Counter()
        for pair, pair_count in channel_pairs.items():
            left, right = pair.split(" | ", 1)
            if left == channel:
                cochannels[right] = pair_count
            elif right == channel:
                cochannels[left] = pair_count
        term_scores = []
        for term, term_count in channel_terms[channel].items():
            if term_count < 3:
                continue
            background = overall_terms[term]
            score = (term_count / count) / max(background / total, 1 / total)
            term_scores.append((round(score, 3), term_count, term))
        term_scores.sort(reverse=True)
        channels_out[channel] = {
            "count": count,
            "share": round(count / total, 6),
            "first_seen": channel_first_seen[channel],
            "last_seen": channel_last_seen[channel],
            "positions": top_map(channel_positions[channel], 20),
            "years": dict(sorted(channel_years[channel].items())),
            "sessions": top_map(channel_sessions[channel], 10),
            "body": dict(channel_body[channel]),
            "body_length": distribution(channel_body_lengths[channel]),
            "tagged_articles": channel_tagged[channel],
            "tag_coverage": round(channel_tagged[channel] / count, 6),
            "top_url_sections": top(channel_url_sections[channel], 12),
            "top_authors": top(channel_authors[channel], 12),
            "top_cochannels": top(cochannels, 15),
            "top_tags": top(channel_tags[channel], 12),
            "top_templates": top(channel_templates[channel], 10),
            "distinctive_terms": [
                {"term": term, "articles": term_count, "lift": score}
                for score, term_count, term in term_scores[:15]
            ],
            "samples": serialize_samples(channel_samples[channel]),
        }

    authors_out = {}
    for author, count in author_counts.most_common():
        authors_out[author] = {
            "count": count,
            "share": round(count / total, 6),
            "first_seen": author_first_seen[author],
            "last_seen": author_last_seen[author],
            "years": dict(sorted(author_years[author].items())),
            "sessions": top_map(author_sessions[author], 10),
            "body": dict(author_body[author]),
            "body_length": distribution(author_body_lengths[author]),
            "tagged_articles": author_tagged[author],
            "tag_coverage": round(author_tagged[author] / count, 6),
            "top_url_sections": top(author_url_sections[author], 12),
            "top_channels": top(author_channels[author], 15),
            "top_tags": top(author_tags[author], 15),
            "top_templates": top(author_templates[author], 12),
        }

    tags_out = {}
    for tag, count in tag_counts.most_common():
        tags_out[tag] = {
            "count": count,
            "share": round(count / total, 6),
            "years": dict(sorted(tag_years[tag].items())),
            "top_channels": top(tag_channels[tag], 10),
            "top_authors": top(tag_authors[tag], 8),
        }

    variant_groups = []
    for normalized, variants in tag_variants.items():
        if len(variants) > 1:
            variant_groups.append({
                "normalized": normalized,
                "total": sum(variants.values()),
                "variants": top(variants, 20),
            })
    variant_groups.sort(key=lambda row: row["total"], reverse=True)

    relationship_cardinality = session.run("""
        MATCH (n:News)
        WITH size([(n)-[:INFLUENCES]->(c:Company) | c]) AS companies,
             size([(n)-[:INFLUENCES]->(s:Sector) | s]) AS sectors,
             size([(n)-[:INFLUENCES]->(i:Industry) | i]) AS industries,
             size([(n)-[:INFLUENCES]->(m:MarketIndex) | m]) AS indexes
        RETURN companies, sectors, industries, indexes, count(*) AS articles
        ORDER BY articles DESC
    """).data()

    property_coverage = session.run("""
        MATCH (n:News)
        UNWIND keys(n) AS property
        RETURN property, count(*) AS articles
        ORDER BY articles DESC, property
    """).data()

    relationship_properties = session.run("""
        MATCH (:News)-[r:INFLUENCES]->()
        RETURN labels(endNode(r)) AS target_labels,
               keys(r) AS property_keys,
               count(*) AS relationships
        ORDER BY relationships DESC
    """).data()

    duplicate_urls = session.run("""
        MATCH (n:News)
        WITH n.url AS url, count(*) AS copies
        WHERE url IS NOT NULL AND url <> '' AND copies > 1
        RETURN count(*) AS groups, sum(copies) AS articles, max(copies) AS largest_group
    """).single().data()

    text_relationships = session.run("""
        MATCH (n:News)
        RETURN sum(CASE WHEN size(coalesce(n.body, '')) > 0
                             AND size(coalesce(n.teaser, '')) > 0 THEN 1 ELSE 0 END)
                   AS body_and_teaser,
               sum(CASE WHEN size(coalesce(n.body, '')) > 0
                             AND size(coalesce(n.teaser, '')) > 0
                             AND n.body STARTS WITH n.teaser THEN 1 ELSE 0 END)
                   AS body_starts_with_full_teaser,
               sum(CASE WHEN size(coalesce(n.body, '')) > 0
                             AND size(coalesce(n.teaser, '')) > 0
                             AND n.body CONTAINS n.teaser THEN 1 ELSE 0 END)
                   AS body_contains_full_teaser,
               sum(CASE WHEN size(coalesce(n.title, '')) > 0
                             AND size(coalesce(n.teaser, '')) > 0
                             AND n.teaser CONTAINS n.title THEN 1 ELSE 0 END)
                   AS teaser_contains_title
    """).single().data()

    embedding_dimensions = session.run("""
        MATCH (n:News)
        WHERE n.embedding IS NOT NULL
        RETURN size(n.embedding) AS dimensions, count(*) AS articles
        ORDER BY articles DESC
    """).data()

    missing_embedding = session.run("""
        MATCH (n:News)
        WHERE n.embedding IS NULL
        RETURN substring(n.created, 0, 10) AS date, n.authors AS authors, count(*) AS articles
        ORDER BY date DESC, articles DESC
    """).data()

    missing_index_samples = session.run("""
        MATCH (n:News)
        WHERE NOT (n)-[:INFLUENCES]->(:MarketIndex)
        RETURN n.id AS id, n.created AS created, n.title AS title, n.authors AS authors,
               size([(n)-[:INFLUENCES]->(:Company) | 1]) AS companies
        ORDER BY n.created DESC
        LIMIT 50
    """).data()

    exact_duplicate_examples = []
    for title, count in duplicate_title_groups.most_common(30):
        exact_duplicate_examples.append({"title": title, "count": count, "ids": exact_title_ids[title]})
    template_examples_out = []
    for template, count in repeated_templates.most_common(50):
        template_examples_out.append({
            "template": template,
            "count": count,
            "examples": template_examples[template],
        })

    tag_frequency_buckets = Counter()
    for count in tag_counts.values():
        if count == 1:
            tag_frequency_buckets["1"] += 1
        elif count <= 4:
            tag_frequency_buckets["2-4"] += 1
        elif count <= 9:
            tag_frequency_buckets["5-9"] += 1
        elif count <= 99:
            tag_frequency_buckets["10-99"] += 1
        elif count <= 999:
            tag_frequency_buckets["100-999"] += 1
        else:
            tag_frequency_buckets["1000+"] += 1

    url_sections_out = {}
    for section, count in url_section_counts.most_common():
        url_sections_out[section] = {
            "count": count,
            "share": round(count / total, 6),
            "years": dict(sorted(url_section_years[section].items())),
            "body_length": distribution(url_section_body_lengths[section]),
            "tagged_articles": url_section_tagged[section],
            "tag_coverage": round(url_section_tagged[section] / count, 6),
            "top_authors": top(url_section_authors[section], 10),
            "top_channels": top(url_section_channels[section], 12),
            "top_tags": top(url_section_tags[section], 10),
            "samples": serialize_samples(url_section_samples[section]),
        }

    source_styles_out = {}
    for style, count in source_style_counts.most_common():
        style_templates = source_style_templates[style]
        repeated_articles = sum(value for value in style_templates.values() if value > 1)
        source_styles_out[style] = {
            "count": count,
            "share": round(count / total, 6),
            "years": dict(sorted(source_style_years[style].items())),
            "body_length": distribution(source_style_body_lengths[style]),
            "teaser": dict(source_style_teaser[style]),
            "tagged_articles": source_style_tagged[style],
            "tag_coverage": round(source_style_tagged[style] / count, 6),
            "unique_title_templates": len(style_templates),
            "articles_in_repeated_templates": repeated_articles,
            "repeated_template_share": round(repeated_articles / count, 6),
            "top_channels": top(source_style_channels[style], 15),
            "top_tags": top(source_style_tags[style], 15),
            "top_url_sections": top(source_style_url_sections[style], 15),
        }

    bzi_tags_out = {}
    for tag, count in bzi_tag_counts.most_common():
        bzi_tags_out[tag] = {
            "count": count,
            "top_channel_combinations": top(bzi_tag_channel_combos[tag], 12),
        }

    company_day_buckets: Counter = Counter()
    for count in company_day_counts.values():
        if count == 1:
            company_day_buckets["1"] += 1
        elif count == 2:
            company_day_buckets["2"] += 1
        elif count <= 5:
            company_day_buckets["3-5"] += 1
        elif count <= 10:
            company_day_buckets["6-10"] += 1
        elif count <= 20:
            company_day_buckets["11-20"] += 1
        elif count <= 50:
            company_day_buckets["21-50"] += 1
        else:
            company_day_buckets["51+"] += 1
    top_company_days = [
        {"company_day": key, "articles": count, "sample_titles": company_day_titles[key]}
        for key, count in company_day_counts.most_common(50)
    ]

    title_signals_out = {}
    for signal_name, signal_spec in TITLE_SIGNALS.items():
        count = title_signal_counts[signal_name]
        expected = signal_spec["expected_channels"]
        hits = title_signal_channel_hits[signal_name]
        title_signals_out[signal_name] = {
            "pattern": signal_spec["pattern"],
            "expected_channels": expected,
            "headline_matches": count,
            "expected_channel_hits": hits if expected else None,
            "expected_channel_coverage": round(hits / count, 6) if expected and count else None,
            "years": dict(sorted(title_signal_years[signal_name].items())),
            "top_authors": top(title_signal_authors[signal_name], 12),
            "top_channels": top(title_signal_channels[signal_name], 15),
            "samples_without_expected_channel": serialize_samples(
                title_signal_missed_samples[signal_name]
            ),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_articles": total,
        "coverage": dict(coverage),
        "parse_errors": dict(parse_errors),
        "date_range": {
            "first_month": min(month_counts) if month_counts else None,
            "last_month": max(month_counts) if month_counts else None,
            "first_created": first_created,
            "last_created": last_created,
        },
        "property_coverage": property_coverage,
        "relationship_cardinality": relationship_cardinality,
        "relationship_properties": relationship_properties,
        "duplicate_urls": duplicate_urls,
        "field_distributions": {
            "title_length": distribution(title_lengths),
            "body_length": distribution(body_lengths),
            "body_length_buckets": dict(body_length_buckets),
            "teaser_length": distribution(teaser_lengths),
            "text_field_shapes": dict(text_field_shapes),
            "text_field_relationships": text_relationships,
            "update_delay_seconds": distribution(update_delays),
            "update_delay_buckets": dict(update_delay_buckets),
            "channel_cardinality": dict(sorted(channel_cardinality.items())),
            "author_cardinality": dict(sorted(author_cardinality.items())),
            "tag_cardinality": dict(sorted(tag_cardinality.items())),
            "company_cardinality": dict(sorted(company_cardinality.items())),
        },
        "timeline": {
            "years": dict(sorted(year_counts.items())),
            "months": dict(sorted(month_counts.items())),
            "weekdays": dict(weekday_counts),
            "hours": dict(sorted(hour_counts.items())),
            "sessions": dict(session_counts),
            "session_years": {k: dict(sorted(v.items())) for k, v in session_years.items()},
            "created_utc_offsets": dict(created_offsets),
            "tag_presence_years": {
                year: dict(values) for year, values in sorted(tag_presence_years.items())
            },
        },
        "storage": {
            "returns_schedule_key_shapes": {" | ".join(k): v for k, v in returns_shapes.items()},
            "returns_schedule_value_types": {
                key: dict(values) for key, values in returns_value_types.items()
            },
            "url_hosts": top(host_counts, 20),
            "url_path_roots": top(url_path_roots, 20),
            "url_sections": url_sections_out,
            "id_shapes": dict(id_shapes),
            "duplicate_ids": {
                "groups": sum(1 for count in id_counts.values() if count > 1),
                "articles": sum(count for count in id_counts.values() if count > 1),
            },
            "embedding_dimensions": embedding_dimensions,
        },
        "channels": channels_out,
        "channel_pairs": top(channel_pairs, 300),
        "channel_combinations": top(channel_combos, 200),
        "channel_sequences": top(channel_sequences, 200),
        "authors": authors_out,
        "tags": tags_out,
        "tag_summary": {
            "unique": len(tag_counts),
            "frequency_buckets": dict(tag_frequency_buckets),
            "articles_with_bzi_tag": articles_with_bzi_tag,
            "unique_bzi_tags": len(bzi_tag_counts),
            "bzi_tags": bzi_tags_out,
            "normalized_variant_groups": variant_groups[:200],
            "top_pairs": top(tag_pairs, 200),
        },
        "companies": {"unique": len(company_counts), "top": top(company_counts, 50)},
        "company_day_clusters": {
            "unique_company_days": len(company_day_counts),
            "cluster_size_buckets": dict(company_day_buckets),
            "articles_in_multi_article_days": sum(
                count for count in company_day_counts.values() if count > 1
            ),
            "top": top_company_days,
        },
        "text_repetition": {
            "unique_exact_titles": len(exact_titles),
            "exact_duplicate_groups": len(duplicate_title_groups),
            "articles_in_exact_duplicate_groups": sum(duplicate_title_groups.values()),
            "top_exact_duplicates": exact_duplicate_examples,
            "unique_normalized_templates": len(templates),
            "repeated_template_groups": len(repeated_templates),
            "articles_in_repeated_templates": sum(repeated_templates.values()),
            "top_templates": template_examples_out,
            "top_opening_phrases": top(opening_phrases, 100),
            "top_body_prefixes": top(body_prefixes, 100),
        },
        "source_styles": source_styles_out,
        "source_markers": {
            marker: {
                "count": count,
                "top_authors": top(source_marker_authors[marker], 15),
            }
            for marker, count in source_markers.most_common()
        },
        "earnings_label_rollout": {
            "by_year": {
                year: dict(values) for year, values in sorted(earnings_label_rollout.items())
            },
            "child_summary": dict(earnings_child_summary),
            "child_without_parent_samples": serialize_samples(
                earnings_child_without_parent_samples
            ),
            "text_without_child_samples": {
                name: serialize_samples(samples)
                for name, samples in earnings_text_without_child_samples.items()
            },
        },
        "proposed_bucket_stress_test": {
            "definitions": {
                name: sorted(values) for name, values in PROPOSED_CHANNEL_BUCKETS.items()
            },
            "anchor_counts": dict(proposed_bucket_counts),
            "anchor_cardinality": dict(sorted(proposed_bucket_cardinality.items())),
            "anchor_combinations": top(proposed_bucket_combinations, 50),
            "no_anchor_samples": serialize_samples(proposed_no_anchor_samples),
        },
        "title_signal_probes": title_signals_out,
        "title_signal_summary": {
            "articles_matching_any_probe": title_signal_union,
            "articles_matching_no_probe": total - title_signal_union,
            "probe_cardinality": dict(sorted(title_signal_cardinality.items())),
        },
        "title_signal_pairs": top(title_signal_pairs, 200),
        "special_samples": {
            name: serialize_samples(samples) for name, samples in special_samples.items()
        },
        "latest_ingestion_state": {
            "missing_embedding": missing_embedding,
            "missing_market_index_samples": missing_index_samples,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/news_deep_audit.json"))
    args = parser.parse_args()

    load_dotenv()
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    if not all((uri, username, password)):
        raise SystemExit("NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are required")

    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        with driver.session(default_access_mode=READ_ACCESS, fetch_size=1000) as session:
            result = run_audit(session)
    finally:
        driver.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({result['total_articles']:,} articles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
