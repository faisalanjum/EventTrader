"""
Financial Data Extraction using LangExtract
============================================

Usage in notebook:
    from extract_financials import extract, display_results

    result = extract("Your financial text here...")
    display_results(result)

Or all-in-one:
    from extract_financials import run
    run("Your financial text here...")

From a file:
    from extract_financials import run_file
    run_file("/path/to/document.txt")
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION - Edit these settings as needed
# =============================================================================

# Model Selection (see available models below)
MODEL_NAME = "gemini-2.5-flash"

# Available models:
# - "gemini-2.5-flash"       (Recommended - best price/performance)
# - "gemini-2.5-flash-lite"  (Cheaper/faster)
# - "gemini-2.5-pro"         (Most capable)
# - "gemini-3-flash-preview" (Bleeding edge)
# - "gemini-3-pro-preview"   (Latest, most capable)

# Extraction Prompt - Describes what to extract
PROMPT = """\
Extract financial entities, metrics, and relationships from text.
Focus on:
- XBRL concepts: company names, tickers, financial items
- Facts: numerical values, dates, percentages
- Descriptions: analyst ratings, business segments, financial conditions

Use exact text for extractions. Preserve numerical precision.
Provide meaningful attributes like units, periods, and context."""

# Schema Examples - Guide the model on extraction format
# Each example shows input text and expected extractions
EXAMPLES_CONFIG = [
    {
        "text": "Apple Inc. (NASDAQ: AAPL) reported revenue of $89.5 billion for Q4 2023, representing a 2% year-over-year decline.",
        "extractions": [
            {"class": "company", "text": "Apple Inc.", "attrs": {"ticker": "AAPL", "exchange": "NASDAQ"}},
            {"class": "xbrl_concept", "text": "revenue", "attrs": {"concept": "Revenue", "gaap_item": "us-gaap:Revenues"}},
            {"class": "fact", "text": "$89.5 billion", "attrs": {"value": 89500000000, "unit": "USD", "decimals": 9}},
            {"class": "period", "text": "Q4 2023", "attrs": {"fiscal_period": "Q4", "fiscal_year": 2023}},
            {"class": "fact", "text": "2% year-over-year decline", "attrs": {"value": -0.02, "unit": "percent", "comparison": "YoY"}},
        ]
    },
    {
        "text": "The company's gross margin improved to 45.2% from 43.1% in the prior quarter, driven by product mix optimization.",
        "extractions": [
            {"class": "xbrl_concept", "text": "gross margin", "attrs": {"concept": "GrossMargin", "gaap_item": "us-gaap:GrossProfitMargin"}},
            {"class": "fact", "text": "45.2%", "attrs": {"value": 0.452, "unit": "percent", "period": "current_quarter"}},
            {"class": "fact", "text": "43.1%", "attrs": {"value": 0.431, "unit": "percent", "period": "prior_quarter"}},
            {"class": "description", "text": "driven by product mix optimization", "attrs": {"type": "reason", "impact": "positive"}},
        ]
    }
]

# Display Settings
CARD_VIEW_MAX_HEIGHT = 600  # pixels
CARD_COLORS = {
    'company': '#4CAF50',       # Green
    'fact': '#2196F3',          # Blue
    'xbrl_concept': '#9C27B0',  # Purple
    'period': '#FF9800',        # Orange
    'description': '#607D8B',   # Gray
}

# =============================================================================
# INTERNAL - No need to edit below unless customizing behavior
# =============================================================================

import langextract as lx
import textwrap
import pandas as pd
from IPython.display import display, HTML


def _build_examples():
    """Convert config examples to LangExtract format."""
    examples = []
    for ex in EXAMPLES_CONFIG:
        extractions = [
            lx.data.Extraction(
                extraction_class=e["class"],
                extraction_text=e["text"],
                attributes=e["attrs"]
            )
            for e in ex["extractions"]
        ]
        examples.append(lx.data.ExampleData(text=ex["text"], extractions=extractions))
    return examples


def extract(text: str, model: str = None) -> "lx.AnnotatedDocument":
    """
    Extract financial entities from text.

    Args:
        text: The input text to extract from
        model: Optional model override (uses MODEL_NAME if not specified)

    Returns:
        AnnotatedDocument with extractions
    """
    # Ensure API key is set
    if not os.getenv('LANGEXTRACT_API_KEY'):
        os.environ['LANGEXTRACT_API_KEY'] = os.getenv('GEMINI_API_KEY', '')

    if not os.getenv('LANGEXTRACT_API_KEY'):
        raise ValueError("No API key found. Set GEMINI_API_KEY or LANGEXTRACT_API_KEY in .env")

    result = lx.extract(
        text_or_documents=text,
        prompt_description=textwrap.dedent(PROMPT),
        examples=_build_examples(),
        model_id=model or MODEL_NAME,
    )
    return result


def to_dataframe(result: "lx.AnnotatedDocument") -> pd.DataFrame:
    """
    Convert extraction result to a pandas DataFrame.

    Args:
        result: The AnnotatedDocument from extract()

    Returns:
        DataFrame with all extractions and attributes
    """
    rows = []
    for ext in result.extractions:
        row = {
            'class': ext.extraction_class,
            'text': ext.extraction_text,
            'span_start': ext.char_interval.start_pos if ext.char_interval else None,
            'span_end': ext.char_interval.end_pos if ext.char_interval else None,
            'alignment': ext.alignment_status.value if ext.alignment_status else None,
        }
        if ext.attributes:
            row.update(ext.attributes)
        rows.append(row)

    return pd.DataFrame(rows)


def display_cards(result: "lx.AnnotatedDocument"):
    """Display extractions as color-coded scrollable cards."""
    html_parts = [f'<div style="max-height:{CARD_VIEW_MAX_HEIGHT}px; overflow-y:auto;">']

    for i, ext in enumerate(result.extractions, 1):
        # Handle None attributes
        attrs = ""
        if ext.attributes:
            attrs = " | ".join(f"<b>{k}</b>: {v}" for k, v in ext.attributes.items() if v)

        span = f"{ext.char_interval.start_pos}-{ext.char_interval.end_pos}" if ext.char_interval else "N/A"
        bg_color = CARD_COLORS.get(ext.extraction_class, '#757575')

        html_parts.append(f"""
        <div style="border:1px solid #ddd; border-radius:8px; padding:10px; margin:8px 0; background:#fafafa;">
            <span style="background:{bg_color}; color:white; padding:2px 8px; border-radius:4px; font-size:11px;">
                {ext.extraction_class.upper()}
            </span>
            <b style="font-size:14px; margin-left:10px;">"{ext.extraction_text}"</b>
            <span style="color:#888; font-size:11px; margin-left:10px;">[char {span}]</span>
            <div style="margin-top:6px; font-size:12px; color:#555;">{attrs if attrs else '<i>No attributes</i>'}</div>
        </div>
        """)

    html_parts.append('</div>')
    display(HTML(''.join(html_parts)))


def display_table(result: "lx.AnnotatedDocument"):
    """Display extractions as a styled DataFrame table."""
    rows = []
    for i, ext in enumerate(result.extractions, 1):
        row = {
            '#': i,
            'Class': ext.extraction_class,
            'Text': ext.extraction_text,
            'Span': f"{ext.char_interval.start_pos}:{ext.char_interval.end_pos}" if ext.char_interval else None,
            'Alignment': ext.alignment_status.value.replace('match_', '') if ext.alignment_status else None,
        }
        if ext.attributes:
            for k, v in ext.attributes.items():
                if v not in [None, '', []]:
                    row[k.title()] = v
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.dropna(axis=1, how='all')

    styled = df.style.set_properties(**{
        'text-align': 'left',
        'font-size': '11px',
    }).set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#4a4a4a'), ('color', 'white'), ('font-size', '11px')]},
        {'selector': 'td', 'props': [('max-width', '200px'), ('overflow', 'hidden'), ('text-overflow', 'ellipsis')]},
    ]).hide(axis='index')

    display(styled)


def display_results(result: "lx.AnnotatedDocument", show_table: bool = True):
    """
    Display extraction results with card view and optional table.

    Args:
        result: The AnnotatedDocument from extract()
        show_table: Whether to also show the DataFrame table (default: True)
    """
    print(f"Extracted {len(result.extractions)} entities\n")
    display_cards(result)
    if show_table:
        print("\n")
        display_table(result)


def run(text: str, model: str = None, show_table: bool = True):
    """
    All-in-one: Extract and display results.

    Args:
        text: The input text to extract from
        model: Optional model override
        show_table: Whether to show DataFrame table (default: True)

    Returns:
        The extraction result (AnnotatedDocument)
    """
    result = extract(text, model=model)
    display_results(result, show_table=show_table)
    return result


def extract_file(filepath: str, model: str = None) -> "lx.AnnotatedDocument":
    """
    Extract financial entities from a text file.

    Args:
        filepath: Path to the text file
        model: Optional model override (uses MODEL_NAME if not specified)

    Returns:
        AnnotatedDocument with extractions
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"Loaded {len(text):,} characters from: {os.path.basename(filepath)}")
    return extract(text, model=model)


def run_file(filepath: str, model: str = None, show_table: bool = True):
    """
    All-in-one: Extract from file and display results.

    Args:
        filepath: Path to the text file
        model: Optional model override
        show_table: Whether to show DataFrame table (default: True)

    Returns:
        The extraction result (AnnotatedDocument)
    """
    result = extract_file(filepath, model=model)
    display_results(result, show_table=show_table)
    return result
