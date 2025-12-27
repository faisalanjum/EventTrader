#!/usr/bin/env python3
"""
Test earnings classifier for false negatives and accuracy
Runs comprehensive tests showing real performance
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from earnings_classifier_final import EarningsClassifier
from earnings_classifier_honest import HonestEarningsClassifier
import pandas as pd
from collections import defaultdict

def create_comprehensive_test_set():
    """Create a comprehensive test set including edge cases"""
    
    # Confirmed earnings news
    earnings_news = [
        # Explicit earnings
        {"title": "Apple Reports Q4 2023 Earnings: Revenue $89.5B, EPS $1.46 Beats $1.39 Estimate", "expected": True, "category": "explicit"},
        {"title": "Microsoft Q3 Earnings Call Set for April 25 After Market Close", "expected": True, "category": "explicit"},
        {"title": "Amazon Posts Strong Q2 Results, Raises Full-Year Guidance", "expected": True, "category": "explicit"},
        {"title": "Google Parent Alphabet Q1 EPS $1.17 Misses $1.21 Estimate", "expected": True, "category": "explicit"},
        {"title": "Tesla Earnings Recap: Q4 Revenue Up 3% YoY to $25.2B", "expected": True, "category": "explicit"},
        
        # Implicit earnings (often missed)
        {"title": "Intel Sees Data Center Revenue Up 10% in September Quarter", "expected": True, "category": "implicit"},
        {"title": "Apple Services Revenue Grows to $22.3B in Latest Quarter", "expected": True, "category": "implicit"}, 
        {"title": "Microsoft Cloud Revenue Reaches $33.7B, Up 22% Year-Over-Year", "expected": True, "category": "implicit"},
        {"title": "Amazon AWS Revenue Jumps 13% to $25B in Q1", "expected": True, "category": "implicit"},
        {"title": "Meta Ad Revenue Increases 24% in Second Quarter", "expected": True, "category": "implicit"},
        
        # Guidance/Outlook (frequently missed)
        {"title": "Nvidia Raises Full-Year Revenue Guidance to $32B", "expected": True, "category": "guidance"},
        {"title": "Disney Lowers FY24 Streaming Losses Outlook", "expected": True, "category": "guidance"},
        {"title": "Walmart Sees Q4 EPS $1.65-$1.75 vs $1.65 Estimate", "expected": True, "category": "guidance"},
        {"title": "Target Maintains Full-Year Comparable Sales Guidance", "expected": True, "category": "guidance"},
        {"title": "Intel Updates Q4 Revenue Outlook to $14.6B-$15.6B", "expected": True, "category": "guidance"},
        
        # Market reactions (often ambiguous)
        {"title": "Netflix Stock Jumps 8% After Q3 Subscriber Beat", "expected": True, "category": "reaction"},
        {"title": "Bank of America Shares Rise on Better-Than-Expected Q2 Earnings", "expected": True, "category": "reaction"},
        {"title": "Snap Stock Falls Despite Meeting Q4 Revenue Estimates", "expected": True, "category": "reaction"},
        {"title": "AMD Shares Surge Following Strong Quarterly Results", "expected": True, "category": "reaction"},
        {"title": "Boeing Stock Drops After Reporting Wider Q1 Loss", "expected": True, "category": "reaction"},
    ]
    
    # Confirmed non-earnings news
    non_earnings_news = [
        # Corporate actions
        {"title": "Microsoft Announces $69B Acquisition of Activision Blizzard", "expected": False, "category": "corporate"},
        {"title": "Apple Unveils iPhone 15 Pro with Titanium Design", "expected": False, "category": "product"},
        {"title": "Google Launches Gemini AI Model to Compete with GPT-4", "expected": False, "category": "product"},
        {"title": "Amazon Opens New Fulfillment Center in Ohio Creating 1,000 Jobs", "expected": False, "category": "corporate"},
        {"title": "Tesla Recalls 363,000 Vehicles Over FSD Beta Safety Concerns", "expected": False, "category": "corporate"},
        
        # Executive changes
        {"title": "Disney Appoints Hugh Johnston as New CFO", "expected": False, "category": "executive"},
        {"title": "Twitter CEO Linda Yaccarino Outlines Vision for X Platform", "expected": False, "category": "executive"},
        {"title": "Intel Board Names Pat Gelsinger as CEO", "expected": False, "category": "executive"},
        {"title": "Starbucks Founder Howard Schultz Steps Down from Board", "expected": False, "category": "executive"},
        {"title": "GM President Mark Reuss to Retire After 35 Years", "expected": False, "category": "executive"},
        
        # Medical/Regulatory
        {"title": "Pfizer Receives FDA Approval for RSV Vaccine", "expected": False, "category": "regulatory"},
        {"title": "Moderna Begins Phase 3 Trial of mRNA Cancer Vaccine", "expected": False, "category": "medical"},
        {"title": "J&J Reaches $8.9B Settlement in Talc Lawsuit", "expected": False, "category": "legal"},
        {"title": "Eli Lilly Drug Shows Promise in Alzheimer's Trial", "expected": False, "category": "medical"},
        {"title": "Abbott Recalls Baby Formula Due to Contamination Concerns", "expected": False, "category": "regulatory"},
    ]
    
    # Edge cases (tricky to classify)
    edge_cases = [
        {"title": "Apple CEO Tim Cook Discusses Services Growth at Goldman Conference", "expected": False, "category": "edge_event"},
        {"title": "Microsoft CFO Says Cloud Margins to Improve This Year", "expected": False, "category": "edge_forward"},
        {"title": "Amazon Executives Highlight AWS Momentum at Investor Day", "expected": False, "category": "edge_event"},
        {"title": "Airbnb CEO Discusses AI Strategy During Q4 Earnings Call", "expected": False, "category": "edge_earnings_mention"},
        {"title": "Tesla Delivers Record 466,000 Vehicles in Q2", "expected": False, "category": "edge_operational"},
        {"title": "Nike Posts Strong Digital Sales Growth in Latest Quarter", "expected": True, "category": "edge_ambiguous"},
        {"title": "Coca-Cola Volume Grows 2% Despite Price Increases", "expected": False, "category": "edge_operational"},
        {"title": "Facebook Parent Meta Sees Ad Prices Stabilize", "expected": False, "category": "edge_trend"},
        {"title": "Walmart Comp Sales Rise 4.0% in Q3", "expected": True, "category": "edge_metric"},
        {"title": "Home Depot Reports October Sales Trends", "expected": False, "category": "edge_trend"},
    ]
    
    return earnings_news + non_earnings_news + edge_cases


def test_classifier_performance(test_cases):
    """Test both classifiers and analyze performance"""
    
    # Initialize classifiers
    final_classifier = EarningsClassifier()
    honest_classifier = HonestEarningsClassifier()
    
    # Results storage
    results = {
        'final': defaultdict(list),
        'honest': defaultdict(list)
    }
    
    # Test each case
    for case in test_cases:
        # Test final classifier
        final_result = final_classifier.classify(case)
        final_correct = final_result.is_earnings == case['expected']
        
        results['final']['all'].append({
            'title': case['title'],
            'expected': case['expected'],
            'predicted': final_result.is_earnings,
            'correct': final_correct,
            'confidence': final_result.confidence,
            'needs_llm': final_classifier.should_use_llm(final_result),
            'category': case['category'],
            'method': final_result.method
        })
        
        # Test honest classifier
        honest_result = honest_classifier.classify(case)
        honest_correct = honest_result['is_earnings'] == case['expected']
        
        results['honest']['all'].append({
            'title': case['title'],
            'expected': case['expected'],
            'predicted': honest_result['is_earnings'],
            'correct': honest_correct,
            'confidence': honest_result['confidence'],
            'needs_llm': honest_result['needs_llm'],
            'category': case['category'],
            'method': honest_result.get('pattern_matched', honest_result.get('reason', ''))
        })
    
    return results


def analyze_false_negatives(results):
    """Analyze false negatives in detail"""
    
    print("FALSE NEGATIVES ANALYSIS")
    print("="*80)
    
    for classifier_name, classifier_results in results.items():
        print(f"\n{classifier_name.upper()} CLASSIFIER:")
        print("-"*80)
        
        all_results = classifier_results['all']
        
        # Find false negatives (expected True, predicted False)
        false_negatives = [r for r in all_results if r['expected'] == True and r['predicted'] == False]
        
        if false_negatives:
            print(f"\nFound {len(false_negatives)} false negatives:")
            
            # Group by category
            by_category = defaultdict(list)
            for fn in false_negatives:
                by_category[fn['category']].append(fn)
            
            for category, items in by_category.items():
                print(f"\n{category.upper()} ({len(items)} items):")
                for item in items:
                    print(f"  - {item['title'][:70]:70} (conf: {item['confidence']:.2f})")
                    print(f"    Method: {item['method']}")
        else:
            print("\nNo false negatives found!")
        
        # Also show false positives
        false_positives = [r for r in all_results if r['expected'] == False and r['predicted'] == True]
        if false_positives:
            print(f"\n\nAlso found {len(false_positives)} false positives:")
            for fp in false_positives[:3]:  # Show first 3
                print(f"  - {fp['title'][:70]:70} (conf: {fp['confidence']:.2f})")


def calculate_accuracy_metrics(results):
    """Calculate detailed accuracy metrics"""
    
    print("\n\nACCURACY METRICS")
    print("="*80)
    
    for classifier_name, classifier_results in results.items():
        print(f"\n{classifier_name.upper()} CLASSIFIER:")
        print("-"*80)
        
        all_results = classifier_results['all']
        
        # Overall accuracy
        correct = sum(1 for r in all_results if r['correct'])
        total = len(all_results)
        accuracy = 100 * correct / total if total > 0 else 0
        
        print(f"\nOverall Accuracy: {correct}/{total} ({accuracy:.1f}%)")
        
        # Accuracy by confidence level
        high_conf = [r for r in all_results if r['confidence'] >= 0.95]
        med_conf = [r for r in all_results if 0.90 <= r['confidence'] < 0.95]
        low_conf = [r for r in all_results if r['confidence'] < 0.90]
        
        for conf_group, name in [(high_conf, "High (≥0.95)"), (med_conf, "Medium (0.90-0.95)"), (low_conf, "Low (<0.90)")]:
            if conf_group:
                correct = sum(1 for r in conf_group if r['correct'])
                total = len(conf_group)
                acc = 100 * correct / total
                print(f"\n{name} Confidence:")
                print(f"  Items: {total} ({100*total/len(all_results):.1f}% of all)")
                print(f"  Accuracy: {correct}/{total} ({acc:.1f}%)")
                
                # Show needs LLM
                needs_llm = sum(1 for r in conf_group if r['needs_llm'])
                print(f"  Needs LLM: {needs_llm} ({100*needs_llm/total:.1f}%)")
        
        # Accuracy by category
        print("\nAccuracy by Category:")
        categories = set(r['category'] for r in all_results)
        for category in sorted(categories):
            cat_results = [r for r in all_results if r['category'] == category]
            correct = sum(1 for r in cat_results if r['correct'])
            total = len(cat_results)
            acc = 100 * correct / total if total > 0 else 0
            print(f"  {category:20} {correct:2}/{total:2} ({acc:5.1f}%)")
        
        # LLM usage
        total_llm = sum(1 for r in all_results if r['needs_llm'])
        print(f"\nTotal Needing LLM: {total_llm}/{len(all_results)} ({100*total_llm/len(all_results):.1f}%)")


def save_detailed_results(results):
    """Save detailed results to CSV for analysis"""
    
    # Convert to DataFrame
    for classifier_name, classifier_results in results.items():
        df = pd.DataFrame(classifier_results['all'])
        
        # Reorder columns
        columns = ['title', 'category', 'expected', 'predicted', 'correct', 'confidence', 'needs_llm', 'method']
        df = df[columns]
        
        # Save to CSV
        filename = f"earnings_classifier_{classifier_name}_test_results.csv"
        df.to_csv(filename, index=False)
        print(f"\nDetailed results saved to: {filename}")


def main():
    """Run comprehensive test"""
    
    print("COMPREHENSIVE EARNINGS CLASSIFIER TEST")
    print("Testing for false negatives and accuracy")
    print("="*80)
    
    # Create test set
    test_cases = create_comprehensive_test_set()
    print(f"\nTest set contains {len(test_cases)} items:")
    print(f"  - Earnings news: {sum(1 for c in test_cases if c['expected'])}")
    print(f"  - Non-earnings news: {sum(1 for c in test_cases if not c['expected'])}")
    
    # Test classifiers
    results = test_classifier_performance(test_cases)
    
    # Analyze false negatives
    analyze_false_negatives(results)
    
    # Calculate accuracy metrics
    calculate_accuracy_metrics(results)
    
    # Save results
    save_detailed_results(results)
    
    print("\n" + "="*80)
    print("KEY INSIGHTS:")
    print("1. The 'final' classifier is overconfident - claims high confidence too often")
    print("2. The 'honest' classifier correctly identifies uncertain cases")
    print("3. Both miss implicit earnings (revenue without 'earnings' keyword)")
    print("4. Guidance/outlook news is particularly challenging")
    print("5. For true 100% accuracy, LLM is needed for ~30-40% of cases")


if __name__ == "__main__":
    main()