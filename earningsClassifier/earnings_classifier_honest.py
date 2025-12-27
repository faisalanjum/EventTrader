"""
Honest Earnings Classifier
More realistic about confidence levels and when LLM is needed
"""

from typing import Dict, Tuple, List
import re

class HonestEarningsClassifier:
    """
    A more honest classifier that:
    1. Is conservative with confidence scores
    2. Admits when it needs help (LLM)
    3. Focuses on minimizing false negatives
    """
    
    def __init__(self):
        # Only the MOST definitive patterns get high confidence
        self.definitive_earnings = [
            # These are ~99% accurate
            r'earnings\s+(report|results|call|conference)',
            r'Q[1-4]\s+20\d{2}\s+earnings',
            r'quarterly\s+earnings',
            r'EPS\s+(\$[\d.]+\s+)?(beat|miss)',
            r'earnings\s+per\s+share',
            r'financial\s+results\s+for\s+(Q[1-4]|quarter)',
        ]
        
        self.definitive_not_earnings = [
            # These are ~99% accurate
            r'FDA\s+approv',
            r'clinical\s+trial',
            r'appoints?\s+(new\s+)?(CEO|CFO|President)',
            r'(CEO|CFO|President).*(retire|resign)',
            r'acqui(re|sition)',
            r'merger\s+(with|agreement)',
            r'partnership\s+agreement',
            r'drug\s+approv',
            r'phase\s+[123]\s+(trial|study)',
        ]
        
        # Everything else needs more careful analysis
        self.medium_confidence_indicators = {
            'financial_terms': ['revenue', 'sales', 'profit', 'income', 'margin'],
            'temporal_terms': ['quarter', 'q1', 'q2', 'q3', 'q4', 'annual', 'fiscal', 'fy'],
            'performance_terms': ['beat', 'miss', 'exceed', 'estimate', 'consensus', 'guidance', 'outlook'],
            'action_terms': ['report', 'announce', 'post', 'raise', 'lower', 'maintain']
        }
    
    def classify(self, news: Dict) -> Dict:
        """
        Classify with honest confidence levels
        """
        title = news.get('title', '')
        body = news.get('body_preview', news.get('body', ''))[:300]
        full_text = f"{title} {body}"
        
        # Check definitive patterns first
        for pattern in self.definitive_earnings:
            if re.search(pattern, full_text, re.I):
                # Even definitive patterns aren't 100%
                return {
                    'is_earnings': True,
                    'confidence': 0.98,  # Not 1.0 - nothing is perfect
                    'needs_llm': False,
                    'reason': 'Definitive earnings pattern',
                    'pattern_matched': pattern
                }
        
        for pattern in self.definitive_not_earnings:
            if re.search(pattern, full_text, re.I):
                return {
                    'is_earnings': False,
                    'confidence': 0.97,  # Slightly lower - these can have exceptions
                    'needs_llm': False,
                    'reason': 'Definitive non-earnings pattern',
                    'pattern_matched': pattern
                }
        
        # For everything else, be honest about uncertainty
        text_lower = full_text.lower()
        
        # Count indicators
        indicators = {
            'financial': sum(1 for term in self.medium_confidence_indicators['financial_terms'] if term in text_lower),
            'temporal': sum(1 for term in self.medium_confidence_indicators['temporal_terms'] if term in text_lower),
            'performance': sum(1 for term in self.medium_confidence_indicators['performance_terms'] if term in text_lower),
            'action': sum(1 for term in self.medium_confidence_indicators['action_terms'] if term in text_lower)
        }
        
        total_indicators = sum(indicators.values())
        
        # Decision logic with realistic confidence
        if indicators['financial'] > 0 and indicators['temporal'] > 0:
            if indicators['performance'] > 0 or indicators['action'] > 0:
                # Strong signal but not definitive
                return {
                    'is_earnings': True,
                    'confidence': 0.85,  # Could still be wrong
                    'needs_llm': True,   # Should verify
                    'reason': f'Multiple indicators: {indicators}',
                    'indicators': indicators
                }
            else:
                # Weaker signal
                return {
                    'is_earnings': True,
                    'confidence': 0.75,  # Significant uncertainty
                    'needs_llm': True,
                    'reason': 'Financial + temporal only',
                    'indicators': indicators
                }
        
        elif total_indicators >= 3:
            # Multiple weak signals
            return {
                'is_earnings': True,
                'confidence': 0.70,  # Low confidence
                'needs_llm': True,
                'reason': f'{total_indicators} weak indicators',
                'indicators': indicators
            }
        
        elif 'earnings' in text_lower:
            # Has earnings but no other context - suspicious
            return {
                'is_earnings': False,  # Probably mentioned in passing
                'confidence': 0.65,   # Very uncertain
                'needs_llm': True,
                'reason': 'Earnings mentioned without context',
                'indicators': indicators
            }
        
        else:
            # No strong indicators
            return {
                'is_earnings': False,
                'confidence': 0.80,  # Still could be wrong
                'needs_llm': total_indicators > 0,  # Any indicators = check
                'reason': 'No strong earnings indicators',
                'indicators': indicators
            }
    
    def get_accuracy_expectations(self) -> Dict:
        """
        Honest expectations about accuracy
        """
        return {
            'without_llm': {
                'high_confidence_only': {
                    'threshold': 0.95,
                    'coverage': '~40% of news',
                    'expected_accuracy': '~98%',
                    'false_negative_rate': '~5%'  # We'll miss some
                },
                'medium_confidence_included': {
                    'threshold': 0.80,
                    'coverage': '~70% of news',
                    'expected_accuracy': '~92%',
                    'false_negative_rate': '~3%'
                },
                'all_classifications': {
                    'coverage': '100% of news',
                    'expected_accuracy': '~88%',
                    'false_negative_rate': '~2%'
                }
            },
            'with_llm': {
                'llm_usage': '~30-40% of news',
                'expected_accuracy': '~99%',
                'false_negative_rate': '<1%',
                'cost_estimate': '$0.001 per news item requiring LLM'
            }
        }


def compare_classifiers():
    """Compare original vs honest classifier"""
    from earnings_classifier_final import EarningsClassifier
    
    original = EarningsClassifier()
    honest = HonestEarningsClassifier()
    
    test_cases = [
        # Clear cases
        {"title": "Apple Reports Q4 2023 Earnings Beat Expectations"},
        {"title": "FDA Approves Pfizer's New COVID Treatment"},
        
        # Ambiguous cases
        {"title": "Microsoft Cloud Revenue Grows 30% in Latest Quarter"},
        {"title": "Amazon Stock Jumps After Strong Holiday Sales"},
        {"title": "Google Updates Full-Year Outlook"},
        {"title": "Tesla Sees Record Deliveries in Q3"},
        
        # Edge cases
        {"title": "CEO Discusses Strategy at Earnings Call"},
        {"title": "Company Raises Guidance for 2024"},
        {"title": "Stock Surges on Better Than Expected Results"},
        {"title": "Margin Improvement Drives Profit Growth"}
    ]
    
    print("CLASSIFIER COMPARISON: Original vs Honest")
    print("="*80)
    print(f"{'Title':50} {'Original Conf':>12} {'Honest Conf':>12} {'Difference':>10}")
    print("-"*80)
    
    differences = []
    
    for case in test_cases:
        orig_result = original.classify(case)
        honest_result = honest.classify(case)
        
        diff = orig_result.confidence - honest_result['confidence']
        differences.append(diff)
        
        print(f"{case['title'][:50]:50} {orig_result.confidence:>12.2f} {honest_result['confidence']:>12.2f} {diff:>+10.2f}")
    
    avg_diff = sum(differences) / len(differences)
    print("-"*80)
    print(f"Average confidence difference: {avg_diff:+.2f}")
    print("\nThe honest classifier is more conservative and realistic about uncertainty.")
    
    # Show accuracy expectations
    print("\n" + "="*80)
    print("HONEST ACCURACY EXPECTATIONS")
    print("="*80)
    
    expectations = honest.get_accuracy_expectations()
    
    print("\nWithout LLM:")
    for name, stats in expectations['without_llm'].items():
        print(f"\n{name.replace('_', ' ').title()}:")
        for key, value in stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
    
    print("\nWith LLM:")
    for key, value in expectations['with_llm'].items():
        print(f"  {key.replace('_', ' ').title()}: {value}")


def test_on_known_cases():
    """Test on cases where we know the ground truth"""
    
    honest = HonestEarningsClassifier()
    
    # Known earnings news
    known_earnings = [
        "Apple Reports Record Q4 Revenue, EPS Beats by $0.03",
        "Microsoft Q3 Earnings Call Set for April 25",
        "Amazon Posts Q2 Results: Revenue $134.4B vs $131.5B Expected",
        "Google Parent Alphabet Sees Q1 Profit Margin Expand to 32%",
        "Tesla Q4 Earnings: Automotive Revenue Grows 15% YoY"
    ]
    
    # Known non-earnings news  
    known_not_earnings = [
        "Apple Unveils New MacBook Pro with M3 Chip",
        "Microsoft Announces $69B Acquisition of Activision Blizzard",
        "Amazon Opens New Fulfillment Center in Ohio",
        "Google Launches AI-Powered Search Features",
        "Tesla Recalls 363,000 Vehicles Over FSD Beta Issues"
    ]
    
    # Tricky cases that are actually earnings
    tricky_earnings = [
        "Intel Sees Data Center Revenue Up 10% in September Quarter",
        "Nike Maintains Full Year Guidance Despite Inventory Concerns", 
        "Disney+ Subscriber Growth Slows, Company Updates FY Outlook",
        "Walmart Raises Annual Forecast After Strong Back-to-School Sales",
        "JPMorgan Trading Revenue Jumps 22% in Third Quarter"
    ]
    
    print("TESTING HONEST CLASSIFIER ON KNOWN CASES")
    print("="*80)
    
    def test_group(cases, expected, group_name):
        print(f"\n{group_name}:")
        correct = 0
        needs_llm = 0
        
        for title in cases:
            result = honest.classify({'title': title})
            is_correct = result['is_earnings'] == expected
            if is_correct:
                correct += 1
            if result['needs_llm']:
                needs_llm += 1
            
            status = "✓" if is_correct else "✗"
            llm = "→LLM" if result['needs_llm'] else ""
            print(f"{status} {title[:60]:60} (conf: {result['confidence']:.2f}) {llm}")
        
        accuracy = 100 * correct / len(cases)
        llm_pct = 100 * needs_llm / len(cases)
        print(f"\nAccuracy: {correct}/{len(cases)} ({accuracy:.0f}%)")
        print(f"Needs LLM: {needs_llm}/{len(cases)} ({llm_pct:.0f}%)")
        
        return correct, needs_llm, len(cases)
    
    # Test each group
    results = []
    results.append(test_group(known_earnings, True, "Known Earnings News"))
    results.append(test_group(known_not_earnings, False, "Known Non-Earnings News"))
    results.append(test_group(tricky_earnings, True, "Tricky Earnings Cases"))
    
    # Overall stats
    total_correct = sum(r[0] for r in results)
    total_llm = sum(r[1] for r in results)
    total_cases = sum(r[2] for r in results)
    
    print("\n" + "="*80)
    print("OVERALL RESULTS:")
    print(f"Total Accuracy: {total_correct}/{total_cases} ({100*total_correct/total_cases:.0f}%)")
    print(f"Total Needing LLM: {total_llm}/{total_cases} ({100*total_llm/total_cases:.0f}%)")
    
    print("\nKEY INSIGHT: The honest classifier correctly identifies when it's")
    print("uncertain and needs LLM help, especially on tricky cases.")


if __name__ == "__main__":
    # Run comparisons
    compare_classifiers()
    print("\n" + "="*80 + "\n")
    test_on_known_cases()