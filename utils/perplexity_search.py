"""
Perplexity Search Utilities
===========================

Provides two search modes for financial research and attribution analysis:
1. perplexity_search - General web search
2. perplexity_sec_search - SEC filings specific search (10-K, 10-Q, 8-K, S-1, S-4, 20-F)

API Documentation Sources:
--------------------------
- Models: https://docs.perplexity.ai/getting-started/models/models/sonar-pro
- SEC Guide: https://docs.perplexity.ai/guides/sec-guide
- MCP Server: https://docs.perplexity.ai/guides/mcp-server
- Changelog: https://docs.perplexity.ai/changelog/changelog

Available Models (as of Jan 2025):
----------------------------------
| Model ID              | Category  | Context | Best For                              |
|-----------------------|-----------|---------|---------------------------------------|
| sonar                 | Search    | 127K    | Lightweight, fast search              |
| sonar-pro             | Search    | 200K    | Deep retrieval, BEST FACTUALITY       |
| sonar-reasoning       | Reasoning | 127K    | Real-time reasoning + search          |
| sonar-reasoning-pro   | Reasoning | 127K    | DeepSeek-R1 powered reasoning         |
| sonar-deep-research   | Research  | -       | Long-form reports (async)             |

Recommendation: Use 'sonar-pro' (default) for SEC/financial searches - highest factuality (F-score 0.858)

API Parameters:
---------------
- search_mode: 'sec' for SEC filings, None for general web
- search_context_size: 'small', 'medium' (default), 'large' - controls search depth
- search_after_date_filter: MM/DD/YYYY format - only search after this date
- search_before_date_filter: MM/DD/YYYY format - only search before this date

SEC Search (search_mode='sec'):
-------------------------------
- Limits results to SEC's EDGAR database and regulatory filings
- Supported filings: 10-K, 10-Q, 8-K, S-1, S-4, 20-F
- Best for: Risk factors, MD&A, financials, compliance queries
- Note: 8-K Item 2.02 earnings often reference press releases (may not have inline numbers)

Usage Examples:
---------------
    from utils.perplexity_search import perplexity_search, perplexity_sec_search

    # General web search
    result = perplexity_search("What caused NVDA stock to drop today?")

    # SEC filings search with date filter
    result = perplexity_sec_search(
        "What are Apple's key risk factors in their latest 10-K?",
        search_after_date="01/01/2024"
    )

    # Use specific model
    result = perplexity_search("market analysis", model="sonar-reasoning-pro")

For LangChain/LangGraph agents:
    from utils.perplexity_search import get_perplexity_tools
    tools = get_perplexity_tools()  # Returns [perplexity_search_tool, perplexity_sec_search_tool]

Notes:
------
- MCP Server does NOT expose search_mode='sec' - use this utility for SEC searches
- API key auto-loaded from: PERPLEXITY_API_KEY env var > .env file > eventtrader.keys
- Rate limits apply - see Perplexity pricing docs

Last updated: 2026-01-13
"""

import os
import requests
from typing import Optional
from functools import lru_cache
from pathlib import Path

# Try to import LangChain tool decorator, but don't fail if not available
try:
    from langchain.tools import tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Dummy decorator if langchain not available
    def tool(func):
        return func

# Auto-load .env file once on module import
_ENV_FILE = Path(__file__).parent.parent / ".env"
if _ENV_FILE.exists() and not os.getenv("PERPLEXITY_API_KEY"):
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE)
    except ImportError:
        # Fallback: parse .env manually
        with open(_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key == "PERPLEXITY_API_KEY" and not os.getenv(key):
                        os.environ[key] = value.strip('"').strip("'")


def _get_api_key() -> str:
    """Get Perplexity API key from environment, .env, or eventtrader.keys"""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        try:
            from eventtrader.keys import PERPLEXITY_API_KEY
            api_key = PERPLEXITY_API_KEY
        except ImportError:
            pass
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not found in environment, .env, or eventtrader.keys")
    return api_key


# =============================================================================
# API Reference: https://api.perplexity.ai/chat/completions
#
# Example payload for SEC search:
# {
#     "model": "sonar-pro",
#     "messages": [{"role": "user", "content": "..."}],
#     "search_mode": "sec",
#     "web_search_options": {"search_context_size": "medium"},
#     "search_after_date_filter": "01/01/2024",
#     "search_before_date_filter": "12/31/2024"
# }
# =============================================================================

def _perplexity_request(
    query: str,
    search_mode: Optional[str] = None,
    model: str = "sonar-pro",
    search_context_size: str = "medium",
    search_after_date: Optional[str] = None,
    search_before_date: Optional[str] = None,
) -> dict:
    """
    Make a request to Perplexity API.

    Args:
        query: The search query
        search_mode: Optional search mode ('sec' for SEC filings, None for general web)
        model: Model to use (sonar-pro, sonar, sonar-reasoning, sonar-reasoning-pro, sonar-deep-research)
        search_context_size: Size of search context (small, medium, large)
        search_after_date: Only search after this date (format: MM/DD/YYYY)
        search_before_date: Only search before this date (format: MM/DD/YYYY)

    Returns:
        dict with 'content' (response text) and 'citations' (list of URLs)
    """
    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": query}],
        "web_search_options": {"search_context_size": search_context_size},
    }

    # Add search mode if specified
    if search_mode:
        payload["search_mode"] = search_mode

    # Add date filters if specified
    if search_after_date:
        payload["search_after_date_filter"] = search_after_date
    if search_before_date:
        payload["search_before_date_filter"] = search_before_date

    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    resp.raise_for_status()

    result = resp.json()
    message = result["choices"][0]["message"]

    return {
        "content": message.get("content", ""),
        "citations": message.get("citations", []),
        "model": result.get("model", model),
    }


def perplexity_search(
    query: str,
    model: str = "sonar-pro",
    search_context_size: str = "medium",
    search_after_date: Optional[str] = None,
    search_before_date: Optional[str] = None,
) -> str:
    """
    General web search using Perplexity API.

    Args:
        query: The search query
        model: Model to use - sonar-pro (default, best factuality), sonar, sonar-reasoning, sonar-reasoning-pro
        search_context_size: Size of search context (small, medium, large)
        search_after_date: Only search after this date (format: MM/DD/YYYY)
        search_before_date: Only search before this date (format: MM/DD/YYYY)

    Returns:
        Search result as string with citations

    Example:
        result = perplexity_search("Why did ROK stock drop on November 2, 2023?")
    """
    result = _perplexity_request(
        query=query,
        search_mode=None,
        model=model,
        search_context_size=search_context_size,
        search_after_date=search_after_date,
        search_before_date=search_before_date,
    )

    # Format response with citations
    content = result["content"]
    if result["citations"]:
        content += "\n\nSources:\n"
        for i, citation in enumerate(result["citations"], 1):
            content += f"[{i}] {citation}\n"

    return content


def perplexity_sec_search(
    query: str,
    model: str = "sonar-pro",
    search_context_size: str = "medium",
    search_after_date: Optional[str] = None,
    search_before_date: Optional[str] = None,
) -> str:
    """
    SEC filings search using Perplexity API.

    Searches 10-K, 10-Q, 8-K, S-1, S-4, 20-F filings directly via search_mode='sec'.

    Args:
        query: The search query about SEC filings
        model: Model to use - sonar-pro (default, best factuality), sonar, sonar-reasoning, sonar-reasoning-pro
        search_context_size: Size of search context (small, medium, large)
        search_after_date: Only search after this date (format: MM/DD/YYYY)
        search_before_date: Only search before this date (format: MM/DD/YYYY)

    Returns:
        Search result as string with citations

    Example:
        result = perplexity_sec_search(
            "What did Rockwell Automation report in their Q4 2023 8-K filing?",
            search_after_date="10/1/2023"
        )
    """
    result = _perplexity_request(
        query=query,
        search_mode="sec",
        model=model,
        search_context_size=search_context_size,
        search_after_date=search_after_date,
        search_before_date=search_before_date,
    )

    # Format response with citations
    content = result["content"]
    if result["citations"]:
        content += "\n\nSEC Filing Sources:\n"
        for i, citation in enumerate(result["citations"], 1):
            content += f"[{i}] {citation}\n"

    return content


# LangChain Tool versions for use with agents
@tool
def perplexity_search_tool(query: str) -> str:
    """
    Search the web using Perplexity AI for real-time information.
    Use this for general questions about stocks, market news, company events, etc.

    Args:
        query: The search query

    Returns:
        Search results with sources
    """
    return perplexity_search(query)


@tool
def perplexity_sec_search_tool(query: str) -> str:
    """
    Search SEC filings (10-K, 10-Q, 8-K, S-1, etc.) using Perplexity AI.
    Use this for questions about company financials, earnings reports,
    management discussion, risk factors, and other SEC filing content.

    Args:
        query: The search query about SEC filings

    Returns:
        Search results from SEC filings with sources
    """
    return perplexity_sec_search(query)


# Convenience function to get both tools for agent use
def get_perplexity_tools():
    """
    Returns both Perplexity search tools for use with LangChain/LangGraph agents.

    Example:
        from utils.perplexity_search import get_perplexity_tools
        tools = get_perplexity_tools()
        # tools = [perplexity_search_tool, perplexity_sec_search_tool]
    """
    return [perplexity_search_tool, perplexity_sec_search_tool]


if __name__ == "__main__":
    # Test the functions
    print("Testing Perplexity Search...")

    # Test regular search
    print("\n=== Regular Search ===")
    result = perplexity_search("What is Rockwell Automation's stock ticker?")
    print(result[:500] + "..." if len(result) > 500 else result)

    # Test SEC search
    print("\n=== SEC Search ===")
    result = perplexity_sec_search(
        "What did Rockwell Automation report in their November 2023 8-K?",
        search_after_date="10/1/2023",
        search_before_date="12/1/2023"
    )
    print(result[:500] + "..." if len(result) > 500 else result)
