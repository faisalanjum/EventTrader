"""
Earnings Classifier Verification Framework
Find false negatives and verify classification accuracy
"""

import random
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import json
from datetime import datetime
from py2neo import Graph
import pandas as pd
from earnings_classifier_final import EarningsClassifier

class ClassifierVerificationFramework:
    """
    Framework for finding false negatives and verifying classifier accuracy
    """
    
    def __init__(self, neo4j_driver: Graph):
        self.neo4j = neo4j_driver
        self.classifier = EarningsClassifier()
        self.verification_results = defaultdict(list)
        
    def get_random_sample(self, sample_percent: float = 0.1) -> List[Dict]:
        """Get random sample of news from Neo4j"""
        query = """
        MATCH (n:News)
        WHERE n.title IS NOT NULL
        WITH n, rand() as r
        ORDER BY r
        LIMIT toInteger(COUNT(n) * $percent)
        RETURN n.id as id, 
               n.title as title, 
               n.body as body,
               n.teaser as teaser,
               n.publishedAt as published_at
        """
        
        result = self.neo4j.run(query, percent=sample_percent).data()
        print(f"Retrieved {len(result)} news items ({sample_percent*100}% sample)")
        return result
    
    def find_potential_false_negatives(self, news_items: List[Dict]) -> List[Dict]:
        """
        Find news that might be earnings but classified as not
        Uses broader search to catch potential misses
        """
        false_negative_patterns = [
            # Financial performance indicators that might be missed
            ('revenue', r'\$\d+\.?\d*[BMK]?'),  # Revenue with dollar amount
            ('sales', r'(up|down|grew|fell)\s+\d+%'),  # Sales growth
            ('profit', r'(record|strong|weak)'),  # Profit descriptors
            ('margin', r'(expand|contract|improve)'),  # Margin changes
            
            # Quarter/period mentions that might be missed
            ('quarter', r'(latest|recent|current)'),  # Temporal without specific Q
            ('period', r'(reporting|fiscal)'),  # Period references
            ('year', r'(full.?year|annual)'),  # Annual references
            
            # Guidance/outlook that might be missed
            ('outlook', r'(raise|lower|maintain)'),  # Outlook changes
            ('guidance', r'(update|revise|affirm)'),  # Guidance updates
            ('forecast', r'(revenue|earnings|sales)'),  # Forecast mentions
            
            # Stock reactions that suggest earnings
            ('stock', r'(jump|surge|fall|drop).*(after|following)'),  # Post-event moves
            ('shares', r'(trade|react).*(report|announce)'),  # Market reaction
            
            # Comparative language
            ('beat', ''),  # Any mention of beat
            ('miss', ''),  # Any mention of miss
            ('exceed', ''),  # Exceeding something
            ('estimate', ''),  # Estimates mentioned
            ('consensus', ''),  # Consensus mentioned
        ]
        
        potential_false_negatives = []
        
        for item in news_items:
            result = self.classifier.classify(item)
            
            # If classified as NOT earnings, check for potential miss
            if not result.is_earnings:
                text = f"{item['title']} {item.get('body', item.get('teaser', ''))[:500]}".lower()
                
                matches = []
                for keyword, pattern in false_negative_patterns:
                    if keyword in text:
                        if not pattern or __import__('re').search(pattern, text, __import__('re').I):
                            matches.append(keyword)
                
                # If multiple indicators present, might be false negative
                if len(matches) >= 2:
                    potential_false_negatives.append({
                        **item,
                        'classification': result,
                        'suspicious_patterns': matches,
                        'confidence': result.confidence
                    })
        
        return potential_false_negatives
    
    def analyze_confidence_distribution(self, news_items: List[Dict]) -> Dict:
        """Analyze confidence distribution and LLM needs"""
        confidence_buckets = {
            'very_high': [],  # >= 0.95
            'high': [],       # 0.90-0.95  
            'medium': [],     # 0.85-0.90
            'low': []         # < 0.85
        }
        
        llm_needed = []
        
        for item in news_items:
            result = self.classifier.classify(item)
            
            record = {
                'id': item['id'],
                'title': item['title'][:100],
                'is_earnings': result.is_earnings,
                'confidence': result.confidence,
                'method': result.method,
                'reason': result.reason
            }
            
            if result.confidence >= 0.95:
                confidence_buckets['very_high'].append(record)
            elif result.confidence >= 0.90:
                confidence_buckets['high'].append(record)
            elif result.confidence >= 0.85:
                confidence_buckets['medium'].append(record)
            else:
                confidence_buckets['low'].append(record)
            
            if self.classifier.should_use_llm(result):
                llm_needed.append(record)
        
        return {
            'distribution': {k: len(v) for k, v in confidence_buckets.items()},
            'buckets': confidence_buckets,
            'llm_needed': llm_needed,
            'llm_percent': 100 * len(llm_needed) / len(news_items) if news_items else 0
        }
    
    def generate_verification_sample(self, news_items: List[Dict], sample_size: int = 100) -> pd.DataFrame:
        """
        Generate a stratified sample for manual verification
        Includes high-confidence cases to verify they're actually accurate
        """
        classifications = []
        
        for item in news_items:
            result = self.classifier.classify(item)
            classifications.append({
                'id': item['id'],
                'title': item['title'],
                'preview': (item.get('body') or item.get('teaser', ''))[:200],
                'is_earnings': result.is_earnings,
                'confidence': result.confidence,
                'method': result.method,
                'reason': result.reason,
                'needs_llm': self.classifier.should_use_llm(result)
            })
        
        df = pd.DataFrame(classifications)
        
        # Stratified sampling
        samples = []
        
        # Get samples from each confidence/classification group
        groups = [
            ('high_conf_earnings', df[(df['is_earnings'] == True) & (df['confidence'] >= 0.95)]),
            ('high_conf_not_earnings', df[(df['is_earnings'] == False) & (df['confidence'] >= 0.95)]),
            ('medium_conf_earnings', df[(df['is_earnings'] == True) & (df['confidence'] < 0.95) & (df['confidence'] >= 0.90)]),
            ('medium_conf_not_earnings', df[(df['is_earnings'] == False) & (df['confidence'] < 0.95) & (df['confidence'] >= 0.90)]),
            ('low_conf_all', df[df['confidence'] < 0.90])
        ]
        
        for group_name, group_df in groups:
            if len(group_df) > 0:
                n_samples = min(sample_size // 5, len(group_df))
                samples.append(group_df.sample(n=n_samples))
        
        verification_df = pd.concat(samples, ignore_index=True)
        
        # Add verification columns
        verification_df['human_is_earnings'] = None
        verification_df['human_confidence'] = None
        verification_df['notes'] = ''
        
        return verification_df
    
    def check_high_confidence_accuracy(self, news_items: List[Dict], check_size: int = 50) -> Dict:
        """
        Specifically check high-confidence classifications for accuracy
        These should be ~100% accurate if we trust them without LLM
        """
        high_conf_items = []
        
        for item in news_items:
            result = self.classifier.classify(item)
            if result.confidence >= 0.95:
                high_conf_items.append({
                    'item': item,
                    'result': result
                })
        
        # Random sample of high confidence items
        sample = random.sample(high_conf_items, min(check_size, len(high_conf_items)))
        
        # Look for potential errors in high confidence
        potential_errors = []
        
        for entry in sample:
            item = entry['item']
            result = entry['result']
            text = f"{item['title']} {item.get('body', '')[:300]}".lower()
            
            # Check for contradictions
            if result.is_earnings:
                # Check if it might NOT be earnings despite high confidence
                if any(phrase in text for phrase in [
                    'not related to earnings',
                    'unrelated to financial',
                    'outside of earnings',
                    'separate from earnings'
                ]):
                    potential_errors.append({
                        'item': item,
                        'result': result,
                        'issue': 'Explicit non-earnings language'
                    })
            else:
                # Check if it might BE earnings despite high confidence not
                earnings_phrases = [
                    'quarterly results', 'earnings report', 'financial results',
                    'eps of', 'earnings per share', 'revenue of $'
                ]
                if sum(1 for phrase in earnings_phrases if phrase in text) >= 2:
                    potential_errors.append({
                        'item': item,
                        'result': result,
                        'issue': 'Multiple earnings indicators present'
                    })
        
        return {
            'total_high_confidence': len(high_conf_items),
            'checked': len(sample),
            'potential_errors': potential_errors,
            'error_rate': len(potential_errors) / len(sample) if sample else 0
        }
    
    def run_comprehensive_verification(self, sample_percent: float = 0.1) -> Dict:
        """Run comprehensive verification and analysis"""
        print("Starting comprehensive verification...")
        
        # Get random sample
        news_items = self.get_random_sample(sample_percent)
        
        # Find potential false negatives
        print("\nSearching for potential false negatives...")
        false_negatives = self.find_potential_false_negatives(news_items)
        
        # Analyze confidence distribution
        print("\nAnalyzing confidence distribution...")
        confidence_analysis = self.analyze_confidence_distribution(news_items)
        
        # Check high confidence accuracy
        print("\nChecking high confidence accuracy...")
        high_conf_check = self.check_high_confidence_accuracy(news_items)
        
        # Generate verification sample
        print("\nGenerating manual verification sample...")
        verification_df = self.generate_verification_sample(news_items)
        
        # Save verification sample
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        verification_file = f"earnings_verification_sample_{timestamp}.csv"
        verification_df.to_csv(verification_file, index=False)
        
        results = {
            'sample_size': len(news_items),
            'potential_false_negatives': len(false_negatives),
            'false_negative_examples': false_negatives[:10],  # First 10
            'confidence_distribution': confidence_analysis['distribution'],
            'llm_needed_percent': confidence_analysis['llm_percent'],
            'high_confidence_check': high_conf_check,
            'verification_file': verification_file
        }
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict):
        """Print verification summary"""
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)
        
        print(f"\nSample Size: {results['sample_size']} news items")
        
        print(f"\nPotential False Negatives: {results['potential_false_negatives']}")
        if results['false_negative_examples']:
            print("Examples:")
            for i, item in enumerate(results['false_negative_examples'][:3]):
                print(f"\n{i+1}. {item['title']}")
                print(f"   Patterns: {', '.join(item['suspicious_patterns'])}")
                print(f"   Confidence: {item['confidence']:.2f}")
        
        print("\nConfidence Distribution:")
        for bucket, count in results['confidence_distribution'].items():
            print(f"  {bucket}: {count}")
        
        print(f"\nLLM Needed: {results['llm_needed_percent']:.1f}%")
        
        hc = results['high_confidence_check']
        print(f"\nHigh Confidence Accuracy Check:")
        print(f"  Checked: {hc['checked']} items")
        print(f"  Potential errors: {len(hc['potential_errors'])}")
        print(f"  Error rate: {hc['error_rate']*100:.1f}%")
        
        print(f"\nVerification file saved: {results['verification_file']}")


def manual_verification_tool():
    """Interactive tool for manual verification"""
    
    def verify_batch(csv_file: str):
        """Interactive verification of a CSV batch"""
        df = pd.read_csv(csv_file)
        
        print(f"\nLoaded {len(df)} items for verification")
        print("For each item, enter: y (yes earnings), n (no earnings), s (skip), q (quit)")
        
        for idx, row in df.iterrows():
            print(f"\n{'='*80}")
            print(f"Item {idx+1}/{len(df)}")
            print(f"Title: {row['title']}")
            print(f"Preview: {row['preview']}")
            print(f"\nClassifier: {'EARNINGS' if row['is_earnings'] else 'NOT EARNINGS'} (conf: {row['confidence']:.2f})")
            print(f"Reason: {row['reason']}")
            
            while True:
                response = input("\nIs this earnings-related? (y/n/s/q): ").lower()
                if response in ['y', 'n', 's', 'q']:
                    break
            
            if response == 'q':
                break
            elif response == 's':
                continue
            else:
                df.at[idx, 'human_is_earnings'] = (response == 'y')
                df.at[idx, 'human_confidence'] = input("Your confidence (0-1): ")
                df.at[idx, 'notes'] = input("Notes (optional): ")
        
        # Save results
        output_file = csv_file.replace('.csv', '_verified.csv')
        df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")
        
        # Calculate accuracy
        verified = df[df['human_is_earnings'].notna()]
        if len(verified) > 0:
            matches = verified['is_earnings'] == verified['human_is_earnings']
            accuracy = matches.sum() / len(matches)
            print(f"\nAccuracy on verified items: {accuracy*100:.1f}%")
            
            # Check high confidence accuracy
            high_conf = verified[verified['confidence'] >= 0.95]
            if len(high_conf) > 0:
                hc_matches = high_conf['is_earnings'] == high_conf['human_is_earnings']
                hc_accuracy = hc_matches.sum() / len(hc_matches)
                print(f"High confidence (>=0.95) accuracy: {hc_accuracy*100:.1f}%")
    
    return verify_batch


if __name__ == "__main__":
    # Example usage
    print("Earnings Classifier Verification Framework")
    print("This will help find false negatives and verify accuracy")
    
    # Mock example without Neo4j connection
    test_items = [
        {"id": "1", "title": "Apple Revenue Grows 5% to $90B in Latest Quarter", "body": ""},
        {"id": "2", "title": "Microsoft Stock Jumps After Cloud Revenue Beat", "body": ""},
        {"id": "3", "title": "Google Raises Full-Year Outlook Amid Strong Ad Sales", "body": ""},
        {"id": "4", "title": "Tesla Shares Fall Despite Record Vehicle Deliveries", "body": ""},
        {"id": "5", "title": "Amazon CEO Discusses AI Strategy at Tech Conference", "body": ""}
    ]
    
    classifier = EarningsClassifier()
    
    print("\nTest Classifications:")
    for item in test_items:
        result = classifier.classify(item)
        status = "EARNINGS" if result.is_earnings else "NOT EARNINGS"
        llm = "→ LLM" if classifier.should_use_llm(result) else ""
        print(f"{item['title'][:50]:50} | {status:12} ({result.confidence:.2f}) {llm}")