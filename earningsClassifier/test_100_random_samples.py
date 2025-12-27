#!/usr/bin/env python3
"""
Test earnings classifiers on 100+ random samples from Neo4j
Provides more statistically significant results
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from py2neo import Graph
    HAS_PY2NEO = True
except ImportError:
    HAS_PY2NEO = False
from earnings_classifier_final import EarningsClassifier
from earnings_classifier_honest import HonestEarningsClassifier
import pandas as pd
from collections import defaultdict
import random
from datetime import datetime

def get_random_news_sample(graph, sample_size=100):
    """Get random sample of news from Neo4j"""
    
    # First, get total count
    count_query = """
    MATCH (n:News)
    WHERE n.title IS NOT NULL
    RETURN count(n) as total
    """
    
    total_count = graph.run(count_query).data()[0]['total']
    print(f"Total news items in database: {total_count:,}")
    
    # Get random sample
    query = """
    MATCH (n:News)
    WHERE n.title IS NOT NULL
    WITH n, rand() as r
    ORDER BY r
    LIMIT $limit
    RETURN n.id as id, 
           n.title as title, 
           n.body as body,
           n.teaser as teaser,
           n.publishedAt as published_at
    """
    
    results = graph.run(query, limit=sample_size).data()
    print(f"Retrieved {len(results)} random news items")
    
    return results


def manually_label_earnings(news_items, sample_size=20):
    """
    Manually label a subset to establish ground truth
    This simulates what would be a manual review process
    """
    
    # For demonstration, we'll use rules to simulate manual labeling
    # In reality, this would be human review
    
    labeled = []
    
    for item in news_items:
        title = item['title'].lower()
        body = (item.get('body') or item.get('teaser', ''))[:500].lower()
        full_text = f"{title} {body}"
        
        # Simulate manual labeling with comprehensive rules
        is_earnings = False
        confidence = "high"
        
        # Definitive earnings patterns
        if any(pattern in full_text for pattern in [
            'earnings report', 'earnings results', 'earnings call',
            'quarterly earnings', 'q1 earnings', 'q2 earnings', 'q3 earnings', 'q4 earnings',
            'eps beat', 'eps miss', 'earnings beat', 'earnings miss',
            'earnings per share of', 'adjusted earnings',
            'financial results for the quarter',
            'quarterly financial results'
        ]):
            is_earnings = True
            confidence = "high"
            
        # Revenue/sales with quarter
        elif any(q in full_text for q in ['q1', 'q2', 'q3', 'q4', 'quarter', 'quarterly']) and \
             any(f in full_text for f in ['revenue', 'sales', 'profit', 'income']):
            is_earnings = True
            confidence = "medium"
            
        # Guidance updates
        elif any(pattern in full_text for pattern in [
            'raises guidance', 'lowers guidance', 'updates guidance',
            'raises outlook', 'lowers outlook', 'maintains outlook',
            'fy guidance', 'full-year guidance', 'annual guidance'
        ]):
            is_earnings = True
            confidence = "medium"
            
        # Beat/miss language
        elif ('beat' in full_text or 'miss' in full_text or 'exceed' in full_text) and \
             any(term in full_text for term in ['estimate', 'consensus', 'expectation']):
            is_earnings = True
            confidence = "medium"
            
        # Definitive non-earnings
        elif any(pattern in full_text for pattern in [
            'fda approv', 'clinical trial', 'drug approv',
            'appoints ceo', 'appoints cfo', 'new ceo', 'new cfo',
            'retire', 'resign', 'step down',
            'acquisition', 'to acquire', 'merger', 'merge with',
            'partnership', 'collaboration', 'joint venture',
            'product launch', 'launches new', 'unveils',
            'recall', 'lawsuit', 'settlement'
        ]):
            is_earnings = False
            confidence = "high"
        
        # Stock movement alone is not earnings
        elif ('stock' in title or 'shares' in title) and \
             not any(e in full_text for e in ['earnings', 'revenue', 'profit', 'quarter']):
            is_earnings = False
            confidence = "medium"
        
        else:
            # Default to not earnings if unclear
            is_earnings = False
            confidence = "low"
        
        labeled.append({
            **item,
            'manual_label': is_earnings,
            'label_confidence': confidence
        })
    
    return labeled


def test_classifiers_on_sample(labeled_items):
    """Test both classifiers on labeled sample"""
    
    # Initialize classifiers
    final_classifier = EarningsClassifier()
    honest_classifier = HonestEarningsClassifier()
    
    results = {
        'final': [],
        'honest': []
    }
    
    for i, item in enumerate(labeled_items):
        # Test final classifier
        final_result = final_classifier.classify(item)
        results['final'].append({
            'id': item.get('id', f"test_{i}"),
            'title': item['title'][:100],
            'manual_label': item.get('manual_label', item.get('expected')),
            'predicted': final_result.is_earnings,
            'correct': final_result.is_earnings == item.get('manual_label', item.get('expected')),
            'confidence': final_result.confidence,
            'needs_llm': final_classifier.should_use_llm(final_result),
            'method': final_result.method,
            'label_confidence': item.get('label_confidence', 'high')
        })
        
        # Test honest classifier
        honest_result = honest_classifier.classify(item)
        results['honest'].append({
            'id': item.get('id', f"test_{i}"),
            'title': item['title'][:100],
            'manual_label': item.get('manual_label', item.get('expected')),
            'predicted': honest_result['is_earnings'],
            'correct': honest_result['is_earnings'] == item.get('manual_label', item.get('expected')),
            'confidence': honest_result['confidence'],
            'needs_llm': honest_result['needs_llm'],
            'method': honest_result.get('reason', ''),
            'label_confidence': item.get('label_confidence', 'high')
        })
    
    return results


def analyze_results(results, classifier_name):
    """Analyze results for a classifier"""
    
    df = pd.DataFrame(results)
    total = len(df)
    
    print(f"\n{classifier_name.upper()} CLASSIFIER RESULTS")
    print("="*80)
    
    # Overall accuracy
    correct = df['correct'].sum()
    accuracy = 100 * correct / total
    print(f"Overall Accuracy: {correct}/{total} ({accuracy:.1f}%)")
    
    # False negatives and positives
    actual_earnings = df[df['manual_label'] == True]
    actual_not_earnings = df[df['manual_label'] == False]
    
    false_negatives = actual_earnings[actual_earnings['predicted'] == False]
    false_positives = actual_not_earnings[actual_not_earnings['predicted'] == True]
    
    print(f"\nFalse Negatives: {len(false_negatives)}/{len(actual_earnings)} ({100*len(false_negatives)/len(actual_earnings):.1f}%)")
    print(f"False Positives: {len(false_positives)}/{len(actual_not_earnings)} ({100*len(false_positives)/len(actual_not_earnings):.1f}%)")
    
    # Accuracy by confidence level
    print("\nAccuracy by Confidence Level:")
    
    # Define confidence buckets
    high_conf = df[df['confidence'] >= 0.95]
    med_conf = df[(df['confidence'] >= 0.85) & (df['confidence'] < 0.95)]
    low_conf = df[df['confidence'] < 0.85]
    
    for conf_df, name in [(high_conf, "High (≥0.95)"), (med_conf, "Medium (0.85-0.95)"), (low_conf, "Low (<0.85)")]:
        if len(conf_df) > 0:
            conf_correct = conf_df['correct'].sum()
            conf_acc = 100 * conf_correct / len(conf_df)
            llm_needed = conf_df['needs_llm'].sum()
            print(f"  {name:20} {conf_correct:3}/{len(conf_df):3} ({conf_acc:5.1f}%) - LLM needed: {llm_needed:3} ({100*llm_needed/len(conf_df):5.1f}%)")
    
    # LLM usage
    total_llm = df['needs_llm'].sum()
    print(f"\nTotal Needing LLM: {total_llm}/{total} ({100*total_llm/total:.1f}%)")
    
    # Show some false negatives
    if len(false_negatives) > 0:
        print("\nExample False Negatives:")
        for idx, row in false_negatives.head(5).iterrows():
            print(f"  - {row['title'][:70]:70} (conf: {row['confidence']:.2f})")
            print(f"    Method: {row['method']}")
    
    # Show accuracy by label confidence
    print("\nAccuracy by Label Confidence:")
    for conf in ['high', 'medium', 'low']:
        conf_items = df[df['label_confidence'] == conf]
        if len(conf_items) > 0:
            conf_correct = conf_items['correct'].sum()
            conf_acc = 100 * conf_correct / len(conf_items)
            print(f"  {conf:10} {conf_correct:3}/{len(conf_items):3} ({conf_acc:5.1f}%)")
    
    return df


def main():
    """Run test on 100+ random samples"""
    
    print("TESTING EARNINGS CLASSIFIERS ON 100+ RANDOM SAMPLES")
    print("="*80)
    
    try:
        # Connect to Neo4j
        if not HAS_PY2NEO:
            raise ImportError("py2neo not available")
        
        print("Connecting to Neo4j...")
        graph = Graph("bolt://localhost:30687", auth=("neo4j", "Next2020#"))
        
        # Get random sample (we'll get 150 to ensure we have enough after filtering)
        news_items = get_random_news_sample(graph, sample_size=150)
        
        # Filter out items with very short titles or no body
        filtered_items = [
            item for item in news_items 
            if len(item['title']) > 20 and (item.get('body') or item.get('teaser'))
        ]
        
        # Take exactly 100 items
        test_items = filtered_items[:100]
        print(f"\nUsing {len(test_items)} items for testing")
        
        # "Manually" label them (simulated)
        print("\nLabeling items (simulated manual review)...")
        labeled_items = manually_label_earnings(test_items)
        
        # Count labels
        earnings_count = sum(1 for item in labeled_items if item['manual_label'])
        print(f"Labeled as earnings: {earnings_count}")
        print(f"Labeled as non-earnings: {len(labeled_items) - earnings_count}")
        
        # Test classifiers
        print("\nTesting classifiers...")
        results = test_classifiers_on_sample(labeled_items)
        
        # Analyze results
        final_df = analyze_results(results['final'], 'final')
        honest_df = analyze_results(results['honest'], 'honest')
        
        # Save detailed results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        final_df.to_csv(f'random_test_final_{timestamp}.csv', index=False)
        honest_df.to_csv(f'random_test_honest_{timestamp}.csv', index=False)
        
        print(f"\nDetailed results saved to:")
        print(f"  - random_test_final_{timestamp}.csv")
        print(f"  - random_test_honest_{timestamp}.csv")
        
        # Summary comparison
        print("\n" + "="*80)
        print("SUMMARY COMPARISON")
        print("="*80)
        
        final_acc = 100 * final_df['correct'].sum() / len(final_df)
        honest_acc = 100 * honest_df['correct'].sum() / len(honest_df)
        
        final_fn = len(final_df[(final_df['manual_label'] == True) & (final_df['predicted'] == False)])
        honest_fn = len(honest_df[(honest_df['manual_label'] == True) & (honest_df['predicted'] == False)])
        
        final_llm = final_df['needs_llm'].sum()
        honest_llm = honest_df['needs_llm'].sum()
        
        print(f"{'':20} {'Final':>15} {'Honest':>15}")
        print(f"{'Overall Accuracy':20} {final_acc:14.1f}% {honest_acc:14.1f}%")
        print(f"{'False Negatives':20} {final_fn:15} {honest_fn:15}")
        print(f"{'Needs LLM':20} {final_llm:15} {honest_llm:15}")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nFalling back to synthetic test data...")
        
        # Create synthetic test data if Neo4j not available
        from test_false_negatives_and_accuracy import create_comprehensive_test_set
        
        # Get our curated test set
        test_cases = create_comprehensive_test_set()
        
        # Add more synthetic cases to reach 100
        additional_cases = []
        
        # Generate variations
        templates = [
            ("Company Reports Q{q} {year} Revenue of ${amount}B", True),
            ("Company Sees {metric} Growth of {pct}% in Latest Quarter", True),
            ("Company {action} Full-Year {metric} Guidance", True),
            ("Company Stock {movement} After {event}", False),
            ("Company Announces New {product} Launch", False),
            ("Company CEO {action} After {years} Years", False),
            ("FDA Approves Company's {drug} for {condition}", False),
            ("Company Completes ${amount}B Acquisition of {target}", False)
        ]
        
        companies = ["Apple", "Microsoft", "Google", "Amazon", "Meta", "Tesla", "Nvidia", "Intel"]
        quarters = ["1", "2", "3", "4"]
        years = ["2023", "2024"]
        metrics = ["Revenue", "Sales", "Profit", "EPS"]
        actions = ["Raises", "Lowers", "Maintains", "Updates"]
        movements = ["Jumps", "Falls", "Surges", "Drops"]
        
        # Generate cases
        for i in range(100 - len(test_cases)):
            template, is_earnings = random.choice(templates)
            
            title = template.format(
                q=random.choice(quarters),
                year=random.choice(years),
                amount=random.randint(1, 100),
                metric=random.choice(metrics),
                pct=random.randint(1, 50),
                action=random.choice(actions),
                movement=random.choice(movements),
                event=random.choice(["Earnings Beat", "Strong Results", "Q3 Report"]),
                product=random.choice(["iPhone", "Surface", "Pixel", "Echo"]),
                years=random.randint(5, 30),
                drug=random.choice(["Treatment", "Vaccine", "Therapy"]),
                condition=random.choice(["Cancer", "Diabetes", "COVID"]),
                target=random.choice(["StartupCo", "TechCorp", "DataInc"])
            )
            
            title = title.replace("Company", random.choice(companies))
            
            additional_cases.append({
                "title": title,
                "expected": is_earnings,
                "category": "synthetic",
                "manual_label": is_earnings,
                "label_confidence": "high"
            })
        
        # Combine all cases
        all_test_items = test_cases + additional_cases
        
        print(f"\nUsing {len(all_test_items)} synthetic test items")
        print(f"Earnings: {sum(1 for item in all_test_items if item.get('expected', item.get('manual_label')))}")
        print(f"Non-earnings: {sum(1 for item in all_test_items if not item.get('expected', item.get('manual_label')))}")
        
        # Test on synthetic data
        results = test_classifiers_on_sample(all_test_items)
        
        # Analyze
        final_df = analyze_results(results['final'], 'final (synthetic data)')
        honest_df = analyze_results(results['honest'], 'honest (synthetic data)')


if __name__ == "__main__":
    main()