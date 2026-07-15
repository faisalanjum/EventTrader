#!/usr/bin/env python3
"""LLM-based router for Neo4j query templates."""

import json
import os
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

# Import template executor
from run_template import execute, driver
from templates import TEMPLATES

# Check for available LLM libraries
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    USE_LANGCHAIN = True
except ImportError:
    USE_LANGCHAIN = False
    
try:
    import openai
    USE_OPENAI = True
except ImportError:
    USE_OPENAI = False

# Load router prompt
try:
    from router_prompt import ROUTER_PROMPT
except ImportError:
    # Fallback: load from text file
    prompt_path = Path("router_prompt.txt")
    if prompt_path.exists():
        ROUTER_PROMPT = prompt_path.read_text()
    else:
        raise ImportError("Router prompt not found. Run generate_router_prompt.py first.")

class LLMRouter:
    """Routes natural language queries to Neo4j templates."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """Initialize the router with LLM configuration."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
        
        # Initialize LLM
        if USE_LANGCHAIN:
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                model=model,
                temperature=0,  # Deterministic for routing
                response_format={"type": "json_object"}
            )
        elif USE_OPENAI:
            openai.api_key = self.api_key
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            raise ImportError("Install langchain-openai or openai: pip install langchain-openai")
    
    def get_llm_response(self, question: str) -> Dict[str, Any]:
        """Get structured JSON response from LLM."""
        if USE_LANGCHAIN:
            messages = [
                SystemMessage(content=ROUTER_PROMPT),
                HumanMessage(content=question)
            ]
            response = self.llm.invoke(messages)
            return json.loads(response.content)
        
        elif USE_OPENAI:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ROUTER_PROMPT},
                    {"role": "user", "content": question}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
    
    def route(self, question: str) -> Dict[str, Any]:
        """Route a natural language question to appropriate template."""
        # Get LLM classification
        llm_json = self.get_llm_response(question)
        
        # Handle unknown intent
        if llm_json.get("intent") == "unknown":
            # Log unknown query for later analysis
            log_path = Path("unknown_queries.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} | {question} | {llm_json.get('reason', 'No reason provided')}\n")
            
            return {
                "status": "unknown",
                "reason": llm_json.get("reason", "No matching template found"),
                "suggestion": "This query type needs a new template to be added.",
                "logged": True
            }
        
        # Get template
        intent = llm_json["intent"]
        if intent not in TEMPLATES:
            return {
                "status": "error",
                "error": f"Template '{intent}' not found in library"
            }
        
        # Extract plan (EXPLAIN/PROFILE)
        plan = llm_json.get("plan", "").upper()
        if plan and plan not in ["EXPLAIN", "PROFILE"]:
            plan = ""
        
        # Execute query
        try:
            params = llm_json.get("params", {})
            
            # If plan specified, we need to modify execution
            if plan:
                # Get the cypher query without executing
                tpl = TEMPLATES[intent]
                cypher = tpl["cypher"]
                
                # Apply parameter substitution (same as in execute())
                for param, value in params.items():
                    if param in ["Label", "L1", "L2", "L3", "Rel", "Rel1", "Rel2", "RelType", 
                                 "RelMetric", "Event", "Target", "Metric1", "Metric2", 
                                 "CompanyLabel", "SrcLabel", "TgtLabel", "SubRel", "SubLabel",
                                 "EventA", "EventB", "RelA", "RelB", "prop", "srcProp", 
                                 "dateProp", "groupProp", "aggProp", "metric", "index", 
                                 "dir", "cmp", "order", "agg", "aggFunc"]:
                        cypher = cypher.replace(f"${param}", str(value))
                
                # Add plan prefix
                cypher = f"{plan} {cypher}"
                
                # Execute with remaining params
                clean_params = {k: v for k, v in params.items() if f"${k}" in tpl["cypher"]}
                
                with driver.session() as sess:
                    result = sess.run(cypher, clean_params)
                    
                    if plan == "EXPLAIN":
                        # Return the plan
                        plan_data = result.consume().plan
                        return {
                            "status": "success",
                            "intent": intent,
                            "plan_type": "EXPLAIN",
                            "plan": str(plan_data) if plan_data else "No plan available"
                        }
                    else:  # PROFILE
                        # Must consume results first
                        data = result.data()
                        profile = result.consume().profile
                        return {
                            "status": "success", 
                            "intent": intent,
                            "plan_type": "PROFILE",
                            "data": data,
                            "profile": str(profile) if profile else "No profile available"
                        }
            else:
                # Normal execution
                data = execute(intent, **params)
                return {
                    "status": "success",
                    "intent": intent,
                    "data": data,
                    "count": len(data)
                }
                
        except Exception as e:
            return {
                "status": "error",
                "intent": intent,
                "error": str(e),
                "params": params
            }

def main():
    """Example usage and testing."""
    router = LLMRouter()
    
    test_queries = [
        "Show me 5 companies",
        "Compare Apple and Microsoft revenue", 
        "explain how to get latest 10-K for Apple",
        "profile Apple stock prices from 2024-01-01 to 2024-01-05",
        "Who owns unicorns?",
        "Show XBRL processing status"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print("-" * 60)
        
        result = router.route(query)
        
        if result["status"] == "success":
            print(f"✅ Intent: {result['intent']}")
            if "plan_type" in result:
                print(f"📊 Plan Type: {result['plan_type']}")
                print(f"Plan/Profile: {result.get('plan') or result.get('profile')[:200] + '...'}")
            else:
                print(f"📊 Results: {result['count']} rows")
                if result['data'] and result['count'] > 0:
                    print(f"Sample: {list(result['data'][0].keys())}")
        
        elif result["status"] == "unknown":
            print(f"❓ Unknown query: {result['reason']}")
            print(f"💡 {result['suggestion']}")
        
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()