#!/usr/bin/env python3
"""
Run comprehensive earnings classifier verification on Neo4j data
Focus on finding false negatives and verifying high-confidence accuracy
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from py2neo import Graph
from earnings_classifier_verification import ClassifierVerificationFramework
from earnings_classifier_final import EarningsClassifier
import json
from datetime import datetime
import pandas as pd

def analyze_false_negatives():
    """Deep dive into potential false negatives"""
    
    # Connect to Neo4j
    graph = Graph("bolt://localhost:30687", auth=("neo4j", "Next2020#"))
    
    # Query for news that might be earnings but could be missed
    # These queries look for specific patterns that suggest earnings
    
    queries = [
        # Query 1: Revenue/Sales with dollar amounts
        """
        MATCH (n:News)
        WHERE n.title =~ '.*[Rr]evenue.*\\$[0-9]+.*' 
           OR n.title =~ '.*[Ss]ales.*\\$[0-9]+.*'
        RETURN n.id as id, n.title as title, n.body as body, n.teaser as teaser
        LIMIT 100
        """,
        
        # Query 2: Percentage changes with financial terms
        """
        MATCH (n:News)
        WHERE n.title =~ '.*([Rr]evenue|[Ss]ales|[Pp]rofit|[Mm]argin).*(up|down|grew|fell|rise|drop).*[0-9]+%.*'
        RETURN n.id as id, n.title as title, n.body as body, n.teaser as teaser
        LIMIT 100
        """,
        
        # Query 3: Guidance/Outlook mentions
        """
        MATCH (n:News)
        WHERE n.title =~ '.*(raises|lowers|cuts|maintains|updates).*([Gg]uidance|[Oo]utlook|[Ff]orecast).*'
           OR n.title =~ '.*([Gg]uidance|[Oo]utlook).*(raise|lower|cut|maintain|update).*'
        RETURN n.id as id, n.title as title, n.body as body, n.teaser as teaser
        LIMIT 100
        """,
        
        # Query 4: Stock reactions suggesting earnings
        """
        MATCH (n:News)
        WHERE n.title =~ '.*(stock|shares).*(jump|surge|fall|drop|slide).*(after|following).*'
           OR n.title =~ '.*(beat|miss|exceed).*estimate.*'
        RETURN n.id as id, n.title as title, n.body as body, n.teaser as teaser
        LIMIT 100
        """,
        
        # Query 5: Quarter/Period with financial metrics
        """
        MATCH (n:News)
        WHERE (n.title =~ '.*[Qq]uarter.*' OR n.title =~ '.*Q[1-4].*' OR n.title =~ '.*FY.*')
          AND (n.title =~ '.*(revenue|sales|profit|earnings|income).*')
        RETURN n.id as id, n.title as title, n.body as body, n.teaser as teaser
        LIMIT 100
        """
    ]
    
    classifier = EarningsClassifier()
    all_potential_misses = []
    
    print("Searching for potential false negatives...")
    print("="*80)
    
    for i, query in enumerate(queries):
        print(f"\nRunning query {i+1}...")
        try:
            results = graph.run(query).data()
            print(f"Found {len(results)} items")
            
            # Check each for potential false negative
            for item in results:
                result = classifier.classify(item)
                
                # If classified as NOT earnings, it might be a false negative
                if not result.is_earnings:
                    all_potential_misses.append({
                        'query_num': i+1,
                        'id': item['id'],
                        'title': item['title'],
                        'preview': (item.get('body') or item.get('teaser', ''))[:200],
                        'confidence': result.confidence,
                        'method': result.method,
                        'reason': result.reason
                    })
                    
        except Exception as e:
            print(f"Query {i+1} failed: {e}")
    
    # Deduplicate by ID
    seen_ids = set()
    unique_misses = []
    for item in all_potential_misses:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_misses.append(item)
    
    print(f"\n{'='*80}")
    print(f"POTENTIAL FALSE NEGATIVES: {len(unique_misses)} unique items")
    print("="*80)
    
    # Show examples
    if unique_misses:
        print("\nExamples of potential false negatives:")
        for i, item in enumerate(unique_misses[:10]):
            print(f"\n{i+1}. {item['title']}")
            print(f"   Confidence: {item['confidence']:.2f}")
            print(f"   Reason: {item['reason']}")
            print(f"   Preview: {item['preview'][:100]}...")
    
    # Save full results
    if unique_misses:
        df = pd.DataFrame(unique_misses)
        filename = f"potential_false_negatives_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        print(f"\nFull results saved to: {filename}")
    
    return unique_misses


def verify_high_confidence_accuracy():
    """Check if high-confidence classifications are truly accurate"""
    
    graph = Graph("bolt://localhost:30687", auth=("neo4j", "Next2020#"))
    classifier = EarningsClassifier()
    
    # Get a sample of news items
    query = """
    MATCH (n:News)
    WHERE n.title IS NOT NULL
    WITH n, rand() as r
    ORDER BY r
    LIMIT 1000
    RETURN n.id as id, n.title as title, n.body as body, n.teaser as teaser
    """
    
    news_items = graph.run(query).data()
    print(f"Analyzing {len(news_items)} news items...")
    
    # Classify and group by confidence
    high_conf_earnings = []
    high_conf_not_earnings = []
    medium_conf = []
    low_conf = []
    
    for item in news_items:
        result = classifier.classify(item)
        
        record = {
            'id': item['id'],
            'title': item['title'],
            'preview': (item.get('body') or item.get('teaser', ''))[:200],
            'is_earnings': result.is_earnings,
            'confidence': result.confidence,
            'method': result.method,
            'reason': result.reason,
            'needs_llm': classifier.should_use_llm(result)
        }
        
        if result.confidence >= 0.95:
            if result.is_earnings:
                high_conf_earnings.append(record)
            else:
                high_conf_not_earnings.append(record)
        elif result.confidence >= 0.90:
            medium_conf.append(record)
        else:
            low_conf.append(record)
    
    # Analyze distribution
    print(f"\nConfidence Distribution:")
    print(f"  High confidence earnings: {len(high_conf_earnings)}")
    print(f"  High confidence not earnings: {len(high_conf_not_earnings)}")
    print(f"  Medium confidence (0.90-0.95): {len(medium_conf)}")
    print(f"  Low confidence (<0.90): {len(low_conf)}")
    
    total_high_conf = len(high_conf_earnings) + len(high_conf_not_earnings)
    print(f"\nHigh confidence total: {total_high_conf} ({100*total_high_conf/len(news_items):.1f}%)")
    print(f"Needs LLM: {len(low_conf)} ({100*len(low_conf)/len(news_items):.1f}%)")
    
    # Look for suspicious high-confidence classifications
    print("\nChecking for suspicious high-confidence classifications...")
    
    suspicious = []
    
    # Check high confidence earnings
    for item in high_conf_earnings[:50]:  # Check first 50
        text = f"{item['title']} {item['preview']}".lower()
        
        # Look for contradictions
        if any(phrase in text for phrase in [
            'not earnings', 'unrelated to earnings', 'outside earnings',
            'appoint', 'retire', 'fda', 'clinical', 'merger', 'acquisition'
        ]):
            suspicious.append({**item, 'issue': 'Contains non-earnings keywords'})
    
    # Check high confidence not earnings  
    for item in high_conf_not_earnings[:50]:  # Check first 50
        text = f"{item['title']} {item['preview']}".lower()
        
        # Count earnings indicators
        indicators = sum(1 for phrase in [
            'earnings', 'revenue', 'profit', 'quarter', 'beat', 'miss',
            'guidance', 'outlook', 'eps', 'sales growth'
        ] if phrase in text)
        
        if indicators >= 3:
            suspicious.append({**item, 'issue': f'{indicators} earnings indicators found'})
    
    if suspicious:
        print(f"\nFound {len(suspicious)} suspicious high-confidence classifications:")
        for i, item in enumerate(suspicious[:5]):
            print(f"\n{i+1}. {item['title']}")
            print(f"   Classified as: {'EARNINGS' if item['is_earnings'] else 'NOT EARNINGS'}")
            print(f"   Issue: {item['issue']}")
    
    # Create verification sample
    verification_items = []
    
    # Sample from each group
    for group, name in [
        (high_conf_earnings[:20], 'high_conf_earnings'),
        (high_conf_not_earnings[:20], 'high_conf_not_earnings'),
        (medium_conf[:20], 'medium_conf'),
        (low_conf[:20], 'low_conf'),
        (suspicious, 'suspicious')
    ]:
        for item in group:
            verification_items.append({**item, 'group': name})
    
    # Save verification sample
    df = pd.DataFrame(verification_items)
    filename = f"earnings_verification_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    print(f"\nVerification sample saved to: {filename}")
    print("Please manually review this file to verify accuracy")
    
    return {
        'total': len(news_items),
        'high_conf_earnings': len(high_conf_earnings),
        'high_conf_not_earnings': len(high_conf_not_earnings),
        'medium_conf': len(medium_conf),
        'low_conf': len(low_conf),
        'suspicious': len(suspicious)
    }


def calculate_actual_accuracy():
    """
    Calculate what our ACTUAL accuracy is based on different confidence thresholds
    """
    graph = Graph("bolt://localhost:30687", auth=("neo4j", "Next2020#"))
    
    # Get 10% random sample
    print("Getting 10% random sample from Neo4j...")
    query = """
    MATCH (n:News)
    WHERE n.title IS NOT NULL
    RETURN count(n) as total
    """
    total_count = graph.run(query).data()[0]['total']
    sample_size = int(total_count * 0.1)
    
    print(f"Total news items: {total_count}")
    print(f"Sample size (10%): {sample_size}")
    
    query = """
    MATCH (n:News)
    WHERE n.title IS NOT NULL
    WITH n, rand() as r
    ORDER BY r
    LIMIT $limit
    RETURN n.id as id, n.title as title, n.body as body, n.teaser as teaser
    """
    
    news_items = graph.run(query, limit=sample_size).data()
    
    # Run verification framework
    framework = ClassifierVerificationFramework(graph)
    results = framework.run_comprehensive_verification(sample_percent=0.1)
    
    return results


def main():
    """Run all verification analyses"""
    print("EARNINGS CLASSIFIER VERIFICATION")
    print("="*80)
    
    try:
        # 1. Find false negatives
        print("\n1. SEARCHING FOR FALSE NEGATIVES")
        print("-"*80)
        false_negatives = analyze_false_negatives()
        
        # 2. Verify high confidence accuracy
        print("\n2. VERIFYING HIGH CONFIDENCE ACCURACY")
        print("-"*80)
        accuracy_results = verify_high_confidence_accuracy()
        
        # 3. Run comprehensive verification
        print("\n3. RUNNING COMPREHENSIVE VERIFICATION")
        print("-"*80)
        verification_results = calculate_actual_accuracy()
        
        # Summary
        print("\n" + "="*80)
        print("VERIFICATION COMPLETE")
        print("="*80)
        print("\nKey Findings:")
        print(f"1. Potential false negatives found: {len(false_negatives)}")
        print(f"2. High confidence items: {accuracy_results['high_conf_earnings'] + accuracy_results['high_conf_not_earnings']}")
        print(f"3. Suspicious high-conf items: {accuracy_results['suspicious']}")
        print(f"4. Items needing LLM: {verification_results['llm_needed_percent']:.1f}%")
        
        print("\nACTION ITEMS:")
        print("1. Review the false negatives CSV to identify patterns we're missing")
        print("2. Manually verify the verification sample CSV")
        print("3. Check the suspicious high-confidence items")
        print("\nThe verification CSVs have been created for manual review.")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure Neo4j is accessible at bolt://localhost:30687")


if __name__ == "__main__":
    main()