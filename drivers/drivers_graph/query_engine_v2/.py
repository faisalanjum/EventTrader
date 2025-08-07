#!/usr/bin/env python3
"""Generate router prompt automatically from template_library.json"""

import json
from pathlib import Path

def generate_router_prompt():
    """Generate the complete router prompt from template library."""
    
    # Load templates
    template_path = Path("templates/template_library.json")
    templates = json.loads(template_path.read_text())
    
    # Start building the prompt
    prompt = """You are a Neo4j query router. Your ONLY job is to analyze user questions and output JSON with the template name and parameters.

AVAILABLE TEMPLATES:
"""
    
    # Add each template with examples
    template_examples = {
        "compare_two_entities_metric": "Compare Apple and Microsoft revenue",
        "distinct_companies_with_fact": "Which companies reported revenue between 2023-01-01 and 2023-12-31",
        "entity_list": "Show me 5 companies",
        "latest_report_for_company": "Latest 10-K for Apple",
        "industry_members": "Show software companies", 
        "news_recent_by_company": "News for AAPL in the last 30 days",
        "price_history_date_range": "Apple stock prices from 2024-01-01 to 2024-01-31",
        "transcripts_for_company": "Show Apple earnings calls",
        "xbrl_process_status": "Show XBRL status",
        "fact_lookup": "Apple's revenue from latest 10-K",
        "entity_search_text": "Find companies with 'Apple' in the name",
        "news_between_dates": "Apple news between 2024-01-01 and 2024-02-01",
        "fact_by_dimension": "Show revenue by product segment",
        "fulltext_section_search": "Search for 'climate change' in filings",
        "8k_section_specific": "Recent 8-K acquisition events",
        "company_report_content_summary": "Summary of Apple's recent filings"
    }
    
    # Generate template documentation
    for i, (name, template) in enumerate(templates.items(), 1):
        prompt += f"\n{i}. {name} - {template['comment']}\n"
        prompt += f"   Params: {', '.join(template['params']) if template['params'] else '(none)'}\n"
        
        # Add example if available
        if name in template_examples:
            prompt += f"   Example: \"{template_examples[name]}\"\n"
    
    # Add the rest of the prompt
    prompt += """
OUTPUT FORMAT:
You MUST respond with ONLY valid JSON in this format:
{
  "intent": "template_name_here",
  "params": {
    "param1": "value1", 
    "param2": "value2"
  },
  "plan": ""  // or "EXPLAIN" or "PROFILE" if user asks for it
}

If no template matches, output:
{
  "intent": "unknown",
  "params": {},
  "reason": "Brief explanation why no template matches"
}

PARAMETER EXTRACTION RULES:
1. Company tickers: Extract standard tickers (AAPL for Apple, MSFT for Microsoft, GOOGL for Google, etc.)
2. Dates: Convert to YYYY-MM-DD format
3. Financial concepts (qname): Use GAAP qualified names:
   - Revenue: "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
   - Net Income: "us-gaap:NetIncomeLoss" 
   - Assets: "us-gaap:Assets"
   - Cash: "us-gaap:CashAndCashEquivalentsAtCarryingValue"
4. Form types: 10-K, 10-Q, 8-K, etc.
5. Limits: Default to 10 if not specified
6. Industries: Use exact names like "SoftwareInfrastructure", "Semiconductors", "Biotechnology"
7. Labels: Company, Report, News, Transcript, etc.
8. For "plan": Set to "EXPLAIN" or "PROFILE" ONLY if user explicitly uses those words

CRITICAL: Output ONLY the JSON object. No explanations, no markdown, no extra text.

EXAMPLES:
User: "Compare Apple and Microsoft revenue"
{"intent": "compare_two_entities_metric", "params": {"ticker1": "AAPL", "ticker2": "MSFT", "qname": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"}, "plan": ""}

User: "explain how Apple's latest 10-K looks"  
{"intent": "latest_report_for_company", "params": {"ticker": "AAPL", "form": "10-K"}, "plan": "EXPLAIN"}

User: "Show me biotech companies"
{"intent": "industry_members", "params": {"industry": "Biotechnology", "limit": 10}, "plan": ""}

User: "Who owns unicorns?"
{"intent": "unknown", "params": {}, "reason": "No template for ownership or unicorn-related queries"}"""
    
    return prompt

def update_router_prompt():
    """Update the router prompt file."""
    prompt = generate_router_prompt()
    
    # Save to file
    prompt_path = Path("router_prompt.txt")
    prompt_path.write_text(prompt)
    
    print(f"✅ Generated router prompt with {len(json.loads(Path('templates/template_library.json').read_text()))} templates")
    print(f"✅ Saved to {prompt_path}")
    
    # Also create a Python version for easy import
    py_path = Path("router_prompt.py")
    py_content = f'"""Auto-generated router prompt from templates."""\n\nROUTER_PROMPT = """{prompt}"""'
    py_path.write_text(py_content)
    print(f"✅ Also saved Python version to {py_path}")

if __name__ == "__main__":
    update_router_prompt()