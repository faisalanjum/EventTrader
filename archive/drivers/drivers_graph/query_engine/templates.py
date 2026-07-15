"""
Template Library for Neo4j Query System V5
Converts natural language queries to parameterized Cypher templates
"""

import re
from typing import Callable, Dict, Any, List, Optional
from datetime import datetime, timedelta


class Template:
    """A parameterized Cypher template with validation"""
    
    def __init__(self, 
                 keywords: List[str],
                 cypher: str,
                 extractors: Dict[str, Callable],
                 validator: Optional[Callable[[dict], bool]] = None,
                 description: str = ""):
        self.keywords = keywords
        self.cypher = cypher
        self.extractors = extractors
        self.validator = validator or (lambda p: True)
        self.description = description


# Helper extractors
def extract_ticker(query: str) -> str:
    """Extract stock ticker from query - now with company name aliases"""
    # First check for company names before looking for tickers
    # This prevents matching '10-K' as ticker 'K'
    query_lower = query.lower()
    
    # Common company name aliases
    ALIASES = {
        "microsoft": "MSFT",
        "apple": "AAPL",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "amazon": "AMZN",
        "meta": "META",
        "facebook": "META",
        "netflix": "NFLX",
        "tesla": "TSLA",
        "nvidia": "NVDA",
        "berkshire": "BRK.B",
        "jp morgan": "JPM",
        "jpmorgan": "JPM",
        "johnson": "JNJ",  # Johnson & Johnson
        "walmart": "WMT",
        "visa": "V",
        "mastercard": "MA",
        "disney": "DIS",
        "intel": "INTC",
        "amd": "AMD",
    }
    
    # Check company names first
    for company, ticker in ALIASES.items():
        if company in query_lower:
            return ticker
    
    # Then try to find explicit tickers (uppercase) but exclude form types
    tickers = re.findall(r'\b[A-Z]{1,5}\b', query)
    for ticker in tickers:
        # Get position of ticker in original query to check context
        ticker_pos = query.find(ticker)
        if ticker_pos > 0 and query[ticker_pos-1] in '-0123456789':
            # This is part of a form type like 10-K or 8-K
            continue
        # Skip single letters and common English words that aren't tickers
        # Note: These are NOT "SQL keywords" - we use Neo4j/Cypher, not SQL
        # These are just common English words that might appear in uppercase
        if len(ticker) == 1 or ticker in ['AND', 'OR', 'NOT', 'THE', 'FOR', 'WITH', 'FROM', 'US', 'UK', 'EU', 'IN', 'AS', 'BY', 'TO', 'OF']:
            continue
        return ticker
    
    return "AAPL"  # Safe default

def extract_ticker_or_name(query: str) -> str:
    """Extract ticker or company name - same as extract_ticker but named clearly"""
    return extract_ticker(query)

def extract_limit(query: str) -> int:
    """Extract limit from query, avoiding years and other numbers"""
    query_lower = query.lower()
    
    # Look for explicit limit keywords
    limit_patterns = [
        r'(?:limit|top|first|last)\s+(\d+)',
        r'(\d+)\s+(?:results?|rows?|records?|entries)',
    ]
    
    for pattern in limit_patterns:
        match = re.search(pattern, query_lower)
        if match:
            n = int(match.group(1))
            if 1 <= n <= 100:
                return n
    
    # Fallback: look for small numbers not likely to be years
    numbers = re.findall(r'\b(\d+)\b', query)
    for num in numbers:
        n = int(num)
        # Exclude likely years (1900-2099) and large numbers
        if 1 <= n <= 100:
            return n
    
    return 20

def extract_days(query: str) -> int:
    """Extract time period in days as integer"""
    if "year" in query.lower():
        return 365
    elif "month" in query.lower():
        return 30
    elif "week" in query.lower():
        return 7
    else:
        numbers = re.findall(r'\b(\d+)\b', query)
        return int(numbers[0]) if numbers else 30

def extract_form_types(query: str) -> List[str]:
    """Extract report form types"""
    query_lower = query.lower()
    if "10-k" in query_lower or "annual" in query_lower:
        return ["10-K"]
    elif "10-q" in query_lower or "quarterly" in query_lower:
        return ["10-Q"]
    elif "8-k" in query_lower:
        return ["8-K"]
    else:
        return ["10-K", "10-Q"]

def escape_string(value: str) -> str:
    """Escape single quotes for safe string insertion"""
    return value.replace("'", "\\'")

def extract_search_term(query: str) -> str:
    """Extract search terms for fulltext search"""
    # Remove common instruction words
    stopwords = ["find", "show", "get", "list", "display", "search", "query", "return", "fetch"]
    words = query.lower().split()
    terms = [w for w in words if w not in stopwords and len(w) > 3]
    result = ' '.join(terms) if terms else "financial"
    return escape_string(result)

def extract_sector(query: str) -> str:
    """Extract sector name from query"""
    sectors = ["technology", "healthcare", "financials", "energy", "industrials",
               "consumer", "utilities", "materials", "real", "communication", "staples"]
    for word in query.lower().split():
        if word in sectors:
            return word
    return "technology"



# Template Library
TEMPLATES = {
    
    # ========== XBRL Templates (10-K/10-Q ONLY) ==========
    
    "xbrl_revenue": Template(
        keywords=["revenue", "sales", "income from contracts", "10-k", "10-q", "annual", "quarterly"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
        WHERE r.formType IN $forms 
          AND con.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
          AND f.is_numeric = '1'
        RETURN c.ticker, f.value as revenue, r.formType, r.created, r.periodOfReport
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "forms": extract_form_types,
            "limit": extract_limit
        },
        validator=lambda p: p["ticker"].isupper() and len(p["ticker"]) <= 5,
        description="Get revenue from 10-K/10-Q XBRL data"
    ),
    
    "xbrl_net_income": Template(
        keywords=["profit", "earnings", "net income", "income", "bottom line", "10-k", "10-q", "quarterly"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
        WHERE r.formType IN $forms 
          AND con.qname = 'us-gaap:NetIncomeLoss'
          AND f.is_numeric = '1'
        RETURN c.ticker, f.value as net_income, r.formType, r.created, r.periodOfReport
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "forms": extract_form_types,
            "limit": extract_limit
        },
        description="Get net income/loss from XBRL data"
    ),
    
    "xbrl_eps": Template(
        keywords=["earnings per share", "eps", "per share", "10-k", "10-q"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
        WHERE r.formType IN $forms 
          AND con.qname IN ['us-gaap:EarningsPerShareBasic', 'us-gaap:EarningsPerShareDiluted']
          AND f.is_numeric = '1'
        RETURN c.ticker, con.qname as eps_type, f.value as eps, r.formType, r.created
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "forms": extract_form_types,
            "limit": extract_limit
        },
        description="Get earnings per share from XBRL"
    ),
    
    "xbrl_assets": Template(
        keywords=["assets", "total assets", "balance sheet", "10-k", "10-q"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
        WHERE r.formType IN $forms 
          AND con.qname = 'us-gaap:Assets'
          AND f.is_numeric = '1'
        RETURN c.ticker, f.value as total_assets, r.formType, r.created, r.periodOfReport
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "forms": extract_form_types,
            "limit": extract_limit
        },
        description="Get total assets from balance sheet"
    ),
    
    # ========== Fulltext Search Templates ==========
    
    "text_risk_factors": Template(
        keywords=["risk", "factors", "risks", "discuss", "describe", "explain"],
        cypher="""
        CALL db.index.fulltext.queryNodes('extracted_section_content_ft', $search_term) 
        YIELD node, score
        WHERE node.section_name = 'RiskFactors' AND score > 0.5
        RETURN node.filing_id, node.form_type, substring(node.content, 0, 500) as excerpt, score
        ORDER BY score DESC
        LIMIT $limit
        """,
        extractors={
            "search_term": extract_search_term,
            "limit": extract_limit
        },
        description="Search risk factors discussions"
    ),
    
    "text_management_discussion": Template(
        keywords=["management", "discussion", "analysis", "mda", "explain", "describe"],
        cypher="""
        CALL db.index.fulltext.queryNodes('extracted_section_content_ft', $search_term) 
        YIELD node, score
        WHERE node.section_name CONTAINS 'ManagementDiscussion' AND score > 0.5
        RETURN node.filing_id, node.form_type, substring(node.content, 0, 500) as excerpt, score
        ORDER BY score DESC
        LIMIT $limit
        """,
        extractors={
            "search_term": extract_search_term,
            "limit": extract_limit
        },
        description="Search management discussion and analysis"
    ),
    
    "text_cybersecurity": Template(
        keywords=["cyber", "security", "breach", "hack", "data protection"],
        cypher="""
        CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'cybersecurity OR "cyber security" OR breach OR hack') 
        YIELD node, score
        WHERE score > 0.5
        RETURN node.filing_id, node.section_name, substring(node.content, 0, 500) as excerpt, score
        ORDER BY score DESC
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Search for cybersecurity discussions"
    ),
    
    # ========== 8-K Event Templates (NEVER have XBRL) ==========
    
    "8k_departures": Template(
        keywords=["8-k", "departure", "resignation", "executive", "officer", "director"],
        cypher="""
        MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(s:ExtractedSectionContent)
        WHERE s.section_name = 'DepartureofDirectorsorCertainOfficers'
          AND datetime(r.created) > datetime() - duration({days: $days})
        RETURN c.ticker, r.created, r.accessionNo, substring(s.content, 0, 500) as excerpt
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "days": extract_days,
            "limit": extract_limit
        },
        validator=lambda p: p["days"] <= 365,
        description="Find executive departures from 8-K filings"
    ),
    
    "8k_acquisitions": Template(
        keywords=["8-k", "acquisition", "merger", "purchase", "material agreement"],
        cypher="""
        MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(s:ExtractedSectionContent)
        WHERE s.section_name IN ['EntryintoaMaterialDefinitiveAgreement', 'CompletionofAcquisitionorDispositionofAssets']
          AND datetime(r.created) > datetime() - duration({days: $days})
        RETURN c.ticker, r.created, s.section_name, substring(s.content, 0, 500) as excerpt
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "days": extract_days,
            "limit": extract_limit
        },
        description="Find acquisitions and material agreements"
    ),
    
    "8k_results": Template(
        keywords=["8-k", "results", "operations", "financial condition", "earnings"],
        cypher="""
        MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(s:ExtractedSectionContent)
        WHERE s.section_name = 'ResultsofOperationsandFinancialCondition'
          AND datetime(r.created) > datetime() - duration({days: $days})
        RETURN c.ticker, r.created, substring(s.content, 0, 500) as excerpt
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "days": extract_days,
            "limit": extract_limit
        },
        description="Find 8-K results announcements"
    ),
    
    # ========== Influence Relationships ==========
    
    "influences_news_max": Template(
        keywords=["news", "influence", "impact", "maximum", "highest", "significant", "stock", "return", "movements"],
        cypher="""
        MATCH (n:News)-[r:INFLUENCES]->(c:Company)
        WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN'
        WITH n, c, toFloat(r.daily_stock) as daily_return
        WHERE NOT isNaN(daily_return)
        RETURN c.ticker, n.title, daily_return, n.created
        ORDER BY daily_return DESC
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find news with maximum positive stock impact"
    ),
    
    "influences_news_negative": Template(
        keywords=["news", "negative", "decline", "drop", "worst", "stock"],
        cypher="""
        MATCH (n:News)-[r:INFLUENCES]->(c:Company)
        WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN'
        WITH n, c, toFloat(r.daily_stock) as daily_return
        WHERE NOT isNaN(daily_return) AND daily_return < 0
        RETURN c.ticker, n.title, daily_return, n.created
        ORDER BY daily_return
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find news with negative stock impact"
    ),
    
    "influences_underperform_market": Template(
        keywords=["underperform", "underperforming", "underperforming market", "below market", "worse than spy", "lagging"],
        cypher="""
        MATCH (n:News)-[rel:INFLUENCES]->(c:Company)
        WHERE rel.daily_stock < rel.daily_macro - 2.0
        RETURN n.title, c.ticker, rel.daily_stock, rel.daily_macro, 
               rel.daily_stock - rel.daily_macro as underperformance
        ORDER BY underperformance
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find stocks underperforming the market"
    ),
    
    "influences_outperform_market": Template(
        keywords=["outperform", "outperforming", "outperforming spy", "beat market", "better than spy", "exceed"],
        cypher="""
        MATCH (n:News)-[rel:INFLUENCES]->(c:Company)
        WHERE rel.daily_stock > rel.daily_macro + 3.0
        RETURN n.title, c.ticker, rel.daily_stock, rel.daily_macro,
               rel.daily_stock - rel.daily_macro as outperformance
        ORDER BY outperformance DESC
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find stocks outperforming the market"
    ),
    
    "influences_transcript": Template(
        keywords=["transcript", "earnings call", "conference", "influence", "impact"],
        cypher="""
        MATCH (t:Transcript)-[rel:INFLUENCES]->(c:Company)
        WHERE rel.daily_stock IS NOT NULL AND rel.daily_stock <> 'NaN'
        WITH t, c, toFloat(rel.daily_stock) as daily_return
        WHERE NOT isNaN(daily_return)
        RETURN c.ticker, t.conference_datetime, daily_return, t.fiscal_quarter, t.fiscal_year
        ORDER BY abs(daily_return) DESC
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find earnings call impacts on stock"
    ),
    
    "influences_industry": Template(
        keywords=["industry", "industries", "sector", "influence", "impact", "affect", "affecting"],
        cypher="""
        MATCH (n:News)-[r:INFLUENCES]->(i:Industry)
        WHERE r.daily_industry IS NOT NULL AND r.daily_industry <> 'NaN'
        WITH n, i, toFloat(r.daily_industry) as industry_return
        WHERE NOT isNaN(industry_return)
        RETURN i.name, n.title, industry_return, n.created
        ORDER BY abs(industry_return) DESC
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find news affecting entire industries"
    ),
    
    # ========== Complex Queries with Joins ==========
    
    "same_day_news_report": Template(
        keywords=["same day", "report", "news", "filing", "coincide"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report)
        WITH c, r, date(datetime(r.created)) as report_date
        MATCH (n:News)-[rel:INFLUENCES]->(c)
        WHERE date(datetime(n.created)) = report_date
        RETURN c.ticker, n.title, r.formType, report_date, rel.daily_stock
        ORDER BY report_date DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "limit": extract_limit
        },
        description="Find news on same day as report filing"
    ),
    
    "10q_with_news_underperformance": Template(
        keywords=["10-q", "quarterly", "news", "underperform", "negative"],
        cypher="""
        MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)
        WHERE r.formType = '10-Q' 
          AND datetime(r.created) > datetime() - duration('P60D')
        WITH c, r, date(datetime(r.created)) as report_date
        MATCH (n:News)-[rel:INFLUENCES]->(c)
        WHERE date(datetime(n.created)) = report_date 
          AND rel.daily_stock < rel.daily_macro - 4.0
        RETURN c.ticker, n.title, rel.daily_stock, rel.daily_macro, r.formType, report_date
        ORDER BY rel.daily_stock
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find 10-Q filings with same-day negative news"
    ),
    
    # ========== Transcript Queries ==========
    
    "transcript_qa": Template(
        keywords=["transcript", "question", "answer", "qa", "analyst"],
        cypher="""
        MATCH (t:Transcript {symbol: $ticker})-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
        WHERE qa.questioner CONTAINS 'analyst'
        RETURN qa.questioner, qa.questioner_title, substring(qa.exchanges, 0, 500) as excerpt
        ORDER BY qa.sequence
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "limit": extract_limit
        },
        description="Get Q&A exchanges from earnings calls"
    ),
    
    # ========== Price/Time Series ==========
    
    "price_history": Template(
        keywords=["price", "history", "stock price", "trading", "ohlc"],
        cypher="""
        MATCH (d:Date)-[p:HAS_PRICE]->(c:Company {ticker: $ticker})
        WHERE date(d.date) >= date(datetime() - duration({days: $days}))
        RETURN d.date, p.open, p.high, p.low, p.close, p.volume
        ORDER BY d.date DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "days": extract_days,
            "limit": extract_limit
        },
        description="Get stock price history"
    ),
    
    # ========== Company Information ==========
    
    "company_info": Template(
        keywords=["company", "information", "details", "market cap", "employees"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})
        OPTIONAL MATCH (c)-[:BELONGS_TO]->(i:Industry)-[:BELONGS_TO]->(s:Sector)
        RETURN c.ticker, c.name, c.mkt_cap, c.employees, c.exchange, 
               i.name as industry, s.name as sector
        """,
        extractors={
            "ticker": extract_ticker
        },
        description="Get company information and hierarchy"
    ),
    
    "companies_by_industry": Template(
        keywords=["companies", "industry", "sector", "list"],
        cypher="""
        MATCH (c:Company)-[:BELONGS_TO]->(i:Industry)
        WHERE toLower(i.name) CONTAINS toLower($industry)
        RETURN c.ticker, c.name, c.mkt_cap, i.name as industry
        ORDER BY c.mkt_cap DESC
        LIMIT $limit
        """,
        extractors={
            "industry": lambda q: extract_search_term(q) or "technology",
            "limit": extract_limit
        },
        validator=lambda p: (
            p.get("industry") and 
            isinstance(p["industry"], str) and
            len(p["industry"]) > 2 and
            p["industry"].lower() not in ["number", "companies", "database", "list", "all", "total", "count", "how many"]
        ),
        description="List companies in a specific industry"
    ),
    
    # ========== Recent Activity ==========
    
    "recent_reports": Template(
        keywords=["recent", "latest", "new", "reports", "filings"],
        cypher="""
        MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)
        WHERE datetime(r.created) > datetime() - duration({days: $days})
        RETURN c.ticker, r.formType, r.created, r.periodOfReport
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "days": extract_days,
            "limit": extract_limit
        },
        description="Find recent report filings"
    ),
    
    "recent_news": Template(
        keywords=["recent", "latest", "news", "articles", "stories"],
        cypher="""
        MATCH (n:News)-[:INFLUENCES]->(c:Company)
        WHERE datetime(n.created) > datetime() - duration({days: $days})
        RETURN c.ticker, n.title, n.created, n.url
        ORDER BY n.created DESC
        LIMIT $limit
        """,
        extractors={
            "days": extract_days,
            "limit": extract_limit
        },
        description="Find recent news articles"
    ),
    
    # ========== Dividend & Corporate Actions ==========
    
    "dividends": Template(
        keywords=["dividend", "dividends", "dividend history", "dividends history", "distribution", "payout"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})-[:DECLARED_DIVIDEND]->(d:Dividend)
        RETURN d.ex_dividend_date, d.pay_date, d.cash_amount, d.dividend_type
        ORDER BY d.ex_dividend_date DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "limit": extract_limit
        },
        description="Get dividend history"
    ),
    
    "stock_splits": Template(
        keywords=["split", "stock split", "shares"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})-[:DECLARED_SPLIT]->(s:Split)
        RETURN s.execution_date, s.split_from, s.split_to
        ORDER BY s.execution_date DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "limit": extract_limit
        },
        description="Get stock split history"
    ),
    
    # ========== Aggregation Queries ==========
    
    "count_reports": Template(
        keywords=["count", "how many", "number of", "reports", "filings"],
        cypher="""
        MATCH (r:Report)
        WHERE r.formType IN $forms
        RETURN r.formType, count(r) as count
        ORDER BY count DESC
        """,
        extractors={
            "forms": lambda q: extract_form_types(q) or ["10-K", "10-Q", "8-K"]
        },
        validator=lambda p: p.get("forms") and len(p["forms"]) > 0,
        description="Count reports by form type"
    ),
    
    "average_returns": Template(
        keywords=["average", "mean", "typical", "returns", "performance"],
        cypher="""
        MATCH ()-[r:INFLUENCES]->()
        WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN'
        WITH toFloat(r.daily_stock) as value
        WHERE NOT isNaN(value)
        RETURN AVG(value) as avg_return, MIN(value) as min_return, MAX(value) as max_return
        """,
        extractors={},
        description="Calculate average returns"
    ),
    
    # ========== Special Pattern Queries ==========
    
    "hourly_impact": Template(
        keywords=["hourly", "hourly stock movements", "intraday", "short term", "immediate"],
        cypher="""
        MATCH (n:News)-[r:INFLUENCES]->(c:Company)
        WHERE r.hourly_stock IS NOT NULL
        WITH n, c, toFloat(r.hourly_stock) as hourly_return
        WHERE abs(hourly_return) > 2.0
        RETURN c.ticker, n.title, hourly_return, n.created
        ORDER BY abs(hourly_return) DESC
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find significant hourly stock movements"
    ),
    
    "premarket_impact": Template(
        keywords=["premarket", "pre-market", "before open", "pre market"],
        cypher="""
        MATCH (n:News)-[r:INFLUENCES]->(c:Company)
        WHERE n.market_session = 'pre_market' 
          AND r.session_stock IS NOT NULL
        RETURN c.ticker, n.title, r.session_stock, n.created
        ORDER BY abs(r.session_stock) DESC
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find pre-market news impacts"
    ),
    
    "postmarket_impact": Template(
        keywords=["afterhours", "after hours", "after hours trading", "post market", "after close"],
        cypher="""
        MATCH (n:News)-[r:INFLUENCES]->(c:Company)
        WHERE n.market_session = 'post_market' 
          AND r.session_stock IS NOT NULL
        RETURN c.ticker, n.title, r.session_stock, n.created
        ORDER BY abs(r.session_stock) DESC
        LIMIT $limit
        """,
        extractors={
            "limit": extract_limit
        },
        description="Find after-hours news impacts"
    ),
    
    # ========== NEW TEMPLATES ADDED ==========
    
    "sector_price_history": Template(
        keywords=["sector", "etf", "sector price", "sector index", "sector ohlc"],
        cypher="""
        MATCH (d:Date)-[p:HAS_PRICE]->(s:Sector)
        WHERE toLower(s.name) CONTAINS toLower($sector)
          AND date(d.date) >= date(datetime() - duration({days: $days}))
        RETURN d.date, s.name, p.open, p.high, p.low, p.close, p.volume
        ORDER BY d.date DESC
        LIMIT $limit
        """,
        extractors={
            "sector": extract_sector,
            "days": extract_days,
            "limit": extract_limit
        },
        description="OHLC time-series for any GICS sector"
    ),
    
    "market_index_price_history": Template(
        keywords=["index", "market index", "spy", "sp500", "s&p", "benchmark"],
        cypher="""
        MATCH (d:Date)-[p:HAS_PRICE]->(m:MarketIndex)
        WHERE (m.ticker = $ticker OR toLower(m.name) CONTAINS toLower($ticker))
          AND date(d.date) >= date(datetime() - duration({days: $days}))
        RETURN d.date, m.ticker, p.open, p.high, p.low, p.close, p.volume
        ORDER BY d.date DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": lambda q: "SPY" if "sp" in q.lower() else "SPY",
            "days": extract_days,
            "limit": extract_limit
        },
        description="Benchmark (SPY or other) OHLC series"
    ),
    
    "financial_statement_json": Template(
        keywords=["json", "financial statement", "balance sheet", "income statement",
                  "cash flow", "shareholders equity"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-
              (r:Report)-[:HAS_FINANCIAL_STATEMENT]->
              (fsc:FinancialStatementContent {statement_type: $statement})
        RETURN c.ticker, r.formType, r.created,
               substring(fsc.value, 0, 1000) AS statement_snippet,
               size(fsc.value) AS json_size
        ORDER BY r.created DESC
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "statement": lambda q: (
                "BalanceSheets"       if "balance"   in q.lower() else
                "StatementsOfIncome"  if "income"    in q.lower() else
                "StatementsOfCashFlows" if "cash"     in q.lower() else
                "StatementsOfShareholdersEquity"
            ),
            "limit": extract_limit
        },
        description="Grab raw JSON statements when XBRL is absent"
    ),
    
    "exhibit_press_release": Template(
        keywords=["exhibit", "99.1", "press release", "earnings release",
                  "ex-99.1", "announcement"],
        cypher="""
        CALL db.index.fulltext.queryNodes('exhibit_content_ft', $search_term)
        YIELD node, score
        WHERE node.exhibit_number = 'EX-99.1' AND score > 0.5
        MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {id: node.filing_id})
        RETURN c.ticker, r.formType, r.created,
               substring(node.content, 0, 1500) AS excerpt, score
        ORDER BY score DESC
        LIMIT $limit
        """,
        extractors={
            "search_term": extract_search_term,
            "limit": extract_limit
        },
        description="Search earnings-press-release exhibits"
    ),
    
    "related_companies": Template(
        keywords=["peers", "competitors", "related companies", "similar companies",
                  "partner", "supplier", "customer"],
        cypher="""
        MATCH (c:Company {ticker: $ticker})-
              [rel:RELATED_TO]->(peer:Company)
        RETURN c.ticker AS source, peer.ticker AS peer,
               rel.relationship_type, rel.bidirectional
        ORDER BY peer.ticker
        LIMIT $limit
        """,
        extractors={
            "ticker": extract_ticker,
            "limit": extract_limit
        },
        description="Retrieve peer / competitor graph via RELATED_TO"
    ),
    
    "report_influence_sector": Template(
        keywords=["report", "filing", "influence", "sector return",
                  "market move", "industry impact"],
        cypher="""
        MATCH (r:Report)-[rel:INFLUENCES]->(s)
        WHERE (s:Sector OR s:MarketIndex)
          AND rel.daily_sector IS NOT NULL
          AND toFloat(rel.daily_sector) <> 'NaN'
        WITH r, s, toFloat(rel.daily_sector) AS sector_ret
        WHERE NOT isNaN(sector_ret)
        RETURN r.formType, s.name AS sector, sector_ret,
               r.created, r.accessionNo
        ORDER BY ABS(sector_ret) DESC
        LIMIT $limit
        """,
        extractors={"limit": extract_limit},
        description="Find filings that moved an entire sector / index"
    ),
    
    # ========== New Essential Templates for 100% Accuracy ==========
    
    "count_companies": Template(
        keywords=["count", "number", "companies", "total", "how many", "firms"],
        cypher="MATCH (c:Company) RETURN count(c) as company_count",
        extractors={},
        validator=lambda p: True,
        description="Count all companies in the database"
    ),
    
    "list_all_companies": Template(
        keywords=["list", "all", "companies", "show", "firms"],
        cypher="MATCH (c:Company) RETURN c.ticker, c.name ORDER BY c.ticker LIMIT 100",
        extractors={},
        validator=lambda p: True,
        description="List all companies with tickers and names"
    ),
    
    "company_guidance": Template(
        keywords=["guidance", "outlook", "forecast", "expect", "forward-looking", "expectations"],
        cypher="""MATCH (c:Company {ticker: $ticker})
        OPTIONAL MATCH (c)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_SECTION]->(s:ExtractedSectionContent)
        WHERE r.formType IN ['8-K', '10-K', '10-Q'] 
        OPTIONAL MATCH (c)-[:HAS_TRANSCRIPT]->(t:Transcript)
        OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
        OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
        OPTIONAL MATCH (t)-[:HAS_FULL_TEXT]->(ft:FullTranscriptText)
        WITH c, r, t, COLLECT(s) + COLLECT(qa) + COLLECT(pr) + COLLECT(ft) as contents
        UNWIND contents AS content
        WITH c, r, t, content,
             toLower(
               CASE
                 WHEN content:ExtractedSectionContent THEN content.content
                 WHEN content:QAExchange THEN content.exchanges
                 WHEN content:PreparedRemark THEN coalesce(content.content, '')
                 WHEN content:FullTranscriptText THEN content.content
                 ELSE ''
               END
             ) AS body
        WHERE body CONTAINS 'guidance'
           OR body CONTAINS 'outlook'
           OR body CONTAINS 'forecast'
           OR body CONTAINS 'expect'
        RETURN c.ticker, content AS node, 1.0 AS score
        ORDER BY coalesce(content.created, t.conference_datetime, r.created) DESC
        LIMIT 20""",
        extractors={"ticker": extract_ticker_or_name},
        validator=lambda p: bool(p.get("ticker")),
        description="Find financial guidance for a company"
    ),
}


def get_template(template_id: str) -> Optional[Template]:
    """Get a template by ID"""
    return TEMPLATES.get(template_id)


def list_template_ids() -> List[str]:
    """List all available template IDs"""
    return list(TEMPLATES.keys())


def find_matching_templates(query: str, min_keyword_matches: int = 1) -> List[tuple[str, int]]:
    """Find templates matching a query based on keyword overlap - now more flexible"""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    matches = []
    
    for template_id, template in TEMPLATES.items():
        score = 0
        for keyword in template.keywords:
            # Check exact phrase match
            if keyword in query_lower:
                score += 2  # Exact phrase gets higher score
            # Check if any word from the keyword phrase appears
            elif any(word in query_words for word in keyword.split()):
                score += 1  # Partial match
        
        if score >= min_keyword_matches:
            matches.append((template_id, score))
    
    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches