#!/usr/bin/env python3
"""
Test earnings classifiers on 200 comprehensive samples
Provides statistically significant results with diverse test cases
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from earnings_classifier_final import EarningsClassifier
from earnings_classifier_honest import HonestEarningsClassifier
import pandas as pd
import random
from collections import defaultdict

def create_large_test_set():
    """Create 200 diverse test cases"""
    
    # Company names for variety
    companies = [
        "Apple", "Microsoft", "Google", "Amazon", "Meta", "Tesla", "Nvidia", "Intel",
        "IBM", "Oracle", "Salesforce", "Adobe", "Netflix", "Disney", "Walmart", 
        "Target", "Home Depot", "Nike", "Starbucks", "McDonald's", "Coca-Cola",
        "PepsiCo", "Johnson & Johnson", "Pfizer", "Moderna", "Bank of America",
        "JPMorgan", "Goldman Sachs", "Morgan Stanley", "Visa", "Mastercard"
    ]
    
    test_cases = []
    
    # 1. Clear earnings news (50 cases)
    earnings_templates = [
        "{company} Reports Q{q} {year} Earnings: Revenue ${rev}B, EPS ${eps} Beats ${est} Estimate",
        "{company} Q{q} Earnings Call Scheduled for {date} After Market Close",
        "{company} Posts {adj} Q{q} EPS of ${eps}, Sales ${rev}B Beat Estimates",
        "{company} {year} Q{q} Results: Adj. EPS ${eps} vs ${est} Est., Revenue ${rev}B vs ${rev2}B Est.",
        "{company} Announces Q{q} Earnings Beat: EPS ${eps} vs ${est} Expected",
        "{company} Q{q} Financial Results: Revenue Up {pct}% YoY to ${rev}B",
        "{company} Delivers Strong Q{q} Earnings, Raises Full-Year Guidance",
        "{company} Reports Mixed Q{q} Results: Revenue Beat, EPS Miss",
        "Earnings Preview: {company} Expected to Report ${eps} EPS for Q{q}",
        "{company} Quarterly Earnings Exceed Analyst Expectations"
    ]
    
    for i in range(50):
        template = random.choice(earnings_templates)
        company = random.choice(companies)
        q = random.choice(["1", "2", "3", "4"])
        year = random.choice(["2023", "2024"])
        rev = round(random.uniform(10, 200), 1)
        rev2 = round(rev * random.uniform(0.95, 1.05), 1)
        eps = round(random.uniform(0.5, 5.0), 2)
        est = round(eps * random.uniform(0.9, 1.1), 2)
        pct = random.randint(5, 30)
        adj = random.choice(["Strong", "Solid", "Mixed", "Weak"])
        date = random.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        
        title = template.format(
            company=company, q=q, year=year, rev=rev, rev2=rev2,
            eps=eps, est=est, pct=pct, adj=adj, date=date
        )
        
        test_cases.append({
            "title": title,
            "expected": True,
            "category": "explicit_earnings"
        })
    
    # 2. Implicit earnings (30 cases) - often missed
    implicit_templates = [
        "{company} Revenue Grows {pct}% to ${rev}B in {period} Quarter",
        "{company} {period} Quarter Sales Reach ${rev}B, Up {pct}% Year-Over-Year",
        "{company} Posts {period} Quarter Operating Income of ${rev}M",
        "{company} {segment} Revenue Jumps {pct}% in Q{q}",
        "{company} Sees Profit Margin Expand to {pct}% in Latest Quarter",
        "{company} {period} Quarter: Cloud Revenue ${rev}B, Up {pct}%",
        "{company} Reports Record {period} Quarter Revenue of ${rev}B",
        "{company} Net Income Rises {pct}% to ${rev}M in Q{q}"
    ]
    
    for i in range(30):
        template = random.choice(implicit_templates)
        company = random.choice(companies)
        period = random.choice(["First", "Second", "Third", "Fourth", "Latest"])
        segment = random.choice(["Cloud", "Services", "Software", "Hardware", "Retail"])
        q = random.choice(["1", "2", "3", "4"])
        rev = round(random.uniform(1, 50), 1)
        pct = random.randint(5, 40)
        
        title = template.format(
            company=company, period=period, segment=segment,
            q=q, rev=rev, pct=pct
        )
        
        test_cases.append({
            "title": title,
            "expected": True,
            "category": "implicit_earnings"
        })
    
    # 3. Guidance/Outlook (20 cases)
    guidance_templates = [
        "{company} Raises FY{year} Revenue Guidance to ${rev}B-${rev2}B",
        "{company} Lowers Q{q} EPS Outlook to ${eps}-${eps2}",
        "{company} Maintains {year} Sales Guidance Despite {challenge}",
        "{company} Updates FY{year} Outlook: Sees EPS ${eps}-${eps2}",
        "{company} Boosts Full-Year Profit Forecast Amid Strong Demand",
        "{company} Cuts Revenue Guidance Citing {reason}",
        "{company} Reaffirms {year} Financial Targets",
        "{company} Sees Q{q} Revenue ${rev}B-${rev2}B vs ${est}B Consensus"
    ]
    
    for i in range(20):
        template = random.choice(guidance_templates)
        company = random.choice(companies)
        year = random.choice(["23", "24", "2024"])
        q = random.choice(["1", "2", "3", "4"])
        rev = round(random.uniform(10, 100), 1)
        rev2 = round(rev * 1.1, 1)
        eps = round(random.uniform(1, 10), 2)
        eps2 = round(eps * 1.1, 2)
        est = round(rev * 1.05, 1)
        challenge = random.choice(["Headwinds", "Supply Chain Issues", "Macro Uncertainty"])
        reason = random.choice(["Weak Demand", "Currency Headwinds", "Market Conditions"])
        
        title = template.format(
            company=company, year=year, q=q, rev=rev, rev2=rev2,
            eps=eps, eps2=eps2, est=est, challenge=challenge, reason=reason
        )
        
        test_cases.append({
            "title": title,
            "expected": True,
            "category": "guidance"
        })
    
    # 4. Non-earnings corporate news (40 cases)
    corporate_templates = [
        "{company} Announces ${amount}B Acquisition of {target}",
        "{company} Appoints {name} as New {position}",
        "{company} Launches {product} to Compete with {competitor}",
        "{company} Opens New {facility} in {location}",
        "{company} Announces {number} Job Cuts Amid Restructuring",
        "{company} Partners with {partner} on {initiative}",
        "{company} Unveils New {product} at {event}",
        "{company} {exec} to Retire After {years} Years",
        "{company} Faces {amount}M Fine for {violation}",
        "{company} Expands into {market} Market with New {product}"
    ]
    
    for i in range(40):
        template = random.choice(corporate_templates)
        company = random.choice(companies)
        amount = random.randint(1, 50)
        target = random.choice(["TechStartup", "DataCorp", "CloudCo", "AILabs"])
        name = random.choice(["John Smith", "Jane Doe", "Mike Johnson", "Sarah Williams"])
        position = random.choice(["CEO", "CFO", "CTO", "President"])
        product = random.choice(["AI Assistant", "Cloud Platform", "Mobile App", "Chip"])
        competitor = random.choice(["Rival Product", "Market Leader", "Incumbent"])
        facility = random.choice(["Factory", "Data Center", "R&D Lab", "Office"])
        location = random.choice(["Texas", "California", "New York", "Europe"])
        number = random.choice(["1,000", "5,000", "10,000"])
        partner = random.choice(["Tech Giant", "Startup", "University", "Government"])
        initiative = random.choice(["AI Research", "5G Network", "Cloud Services"])
        event = random.choice(["CES", "Tech Conference", "Developer Event"])
        exec = random.choice(["CEO", "Founder", "President"])
        years = random.randint(10, 30)
        violation = random.choice(["Privacy Breach", "Antitrust", "Securities"])
        market = random.choice(["Asian", "European", "Latin American"])
        
        title = template.format(
            company=company, amount=amount, target=target, name=name,
            position=position, product=product, competitor=competitor,
            facility=facility, location=location, number=number,
            partner=partner, initiative=initiative, event=event,
            exec=exec, years=years, violation=violation, market=market
        )
        
        test_cases.append({
            "title": title,
            "expected": False,
            "category": "corporate"
        })
    
    # 5. Medical/Regulatory (20 cases)
    medical_templates = [
        "{company} Receives FDA Approval for {drug} to Treat {condition}",
        "{company} {drug} Shows {result} in Phase {phase} {condition} Trial",
        "{company} Halts {drug} Trial Due to {reason}",
        "FDA Grants {designation} to {company}'s {drug}",
        "{company} Submits {application} for {drug} Approval",
        "{company} Recalls {product} Due to {issue}",
        "{company} Drug Fails to Meet Primary Endpoint in {condition} Study",
        "{company} Begins Phase {phase} Trial of {drug} for {condition}"
    ]
    
    for i in range(20):
        template = random.choice(medical_templates)
        company = random.choice(["Pfizer", "Moderna", "J&J", "Merck", "AbbVie", "Gilead"])
        drug = random.choice(["Drug-X", "Treatment-Y", "Vaccine-Z", "Therapy-A"])
        condition = random.choice(["Cancer", "Diabetes", "COVID-19", "Alzheimer's"])
        result = random.choice(["Positive Results", "Efficacy", "Safety Profile"])
        phase = random.choice(["1", "2", "3"])
        reason = random.choice(["Safety Concerns", "Lack of Efficacy", "Side Effects"])
        designation = random.choice(["Breakthrough Therapy", "Fast Track", "Priority Review"])
        application = random.choice(["NDA", "BLA", "sNDA"])
        product = random.choice(["Medicine", "Device", "Vaccine"])
        issue = random.choice(["Contamination", "Labeling Error", "Quality Issues"])
        
        title = template.format(
            company=company, drug=drug, condition=condition, result=result,
            phase=phase, reason=reason, designation=designation,
            application=application, product=product, issue=issue
        )
        
        test_cases.append({
            "title": title,
            "expected": False,
            "category": "medical"
        })
    
    # 6. Market reaction/Stock movement (20 cases)
    market_templates = [
        "{company} Stock {movement} {pct}% After {event}",
        "{company} Shares {movement} on {news}",
        "{company} Stock {movement} Despite {event}",
        "Why {company} Stock Is {movement} Today",
        "{company} Leads {index} {movement} with {pct}% Gain"
    ]
    
    movements = ["Jumps", "Surges", "Falls", "Drops", "Rallies", "Plunges"]
    events_earnings = ["Q3 Earnings Beat", "Strong Results", "Revenue Beat", "EPS Beat"]
    events_other = ["Product Launch", "FDA Approval", "Partnership News", "Analyst Upgrade"]
    news_items = ["Heavy Volume", "Analyst Upgrade", "Market Rally", "Sector Rotation"]
    indices = ["S&P 500", "Nasdaq", "Dow"]
    
    # Half should be earnings-related
    for i in range(10):
        template = random.choice(market_templates)
        company = random.choice(companies)
        movement = random.choice(movements)
        pct = random.randint(2, 15)
        event = random.choice(events_earnings)
        news = random.choice(news_items)
        index = random.choice(indices)
        
        title = template.format(
            company=company, movement=movement, pct=pct,
            event=event, news=news, index=index
        )
        
        test_cases.append({
            "title": title,
            "expected": True,  # Earnings-related
            "category": "market_reaction_earnings"
        })
    
    # Half should be non-earnings
    for i in range(10):
        template = random.choice(market_templates)
        company = random.choice(companies)
        movement = random.choice(movements)
        pct = random.randint(2, 15)
        event = random.choice(events_other)
        news = random.choice(news_items)
        index = random.choice(indices)
        
        title = template.format(
            company=company, movement=movement, pct=pct,
            event=event, news=news, index=index
        )
        
        test_cases.append({
            "title": title,
            "expected": False,  # Not earnings-related
            "category": "market_reaction_other"
        })
    
    # 7. Edge cases (20 cases)
    edge_cases = [
        # Earnings-related edge cases
        {"title": "Apple CEO Tim Cook Discusses Services Growth at Goldman Sachs Conference", "expected": False, "category": "edge_conference"},
        {"title": "Microsoft CFO Amy Hood to Present at Morgan Stanley Conference", "expected": False, "category": "edge_conference"},
        {"title": "Tesla Delivers Record 466,140 Vehicles in Q2 2023", "expected": False, "category": "edge_operational"},
        {"title": "Amazon Prime Day Sales Hit New Record", "expected": False, "category": "edge_operational"},
        {"title": "Netflix Adds 5.9 Million Subscribers in Q2", "expected": True, "category": "edge_metric"},  # This is earnings
        {"title": "Disney+ Reaches 150 Million Subscribers", "expected": False, "category": "edge_operational"},
        {"title": "Walmart Comp Sales Rise 4.0% in Q3", "expected": True, "category": "edge_metric"},  # This is earnings
        {"title": "Target Same-Store Sales Decline 5.4%", "expected": True, "category": "edge_metric"},  # This is earnings
        {"title": "Starbucks Opens 500th Store in China", "expected": False, "category": "edge_expansion"},
        {"title": "McDonald's Tests New AI Drive-Thru Technology", "expected": False, "category": "edge_technology"},
        
        # Ambiguous cases
        {"title": "Intel CEO Discusses Chip Strategy During Q4 Earnings Call", "expected": False, "category": "edge_earnings_mention"},
        {"title": "AMD CEO Lisa Su on Competition at Earnings Conference", "expected": False, "category": "edge_earnings_mention"},
        {"title": "Nike Digital Sales Growth Accelerates", "expected": False, "category": "edge_trend"},
        {"title": "Apple Services Revenue Reaches All-Time High", "expected": False, "category": "edge_trend"},
        {"title": "Google Cloud Nears Profitability Milestone", "expected": False, "category": "edge_trend"},
        {"title": "Meta Reality Labs Losses Widen to $3.7B", "expected": False, "category": "edge_segment"},
        {"title": "Amazon AWS Growth Slows to 12%", "expected": False, "category": "edge_trend"},
        {"title": "Microsoft Sees Continued Cloud Strength", "expected": False, "category": "edge_outlook"},
        {"title": "Tesla Gross Margins Under Pressure", "expected": False, "category": "edge_trend"},
        {"title": "Netflix Plans Ad-Tier Expansion", "expected": False, "category": "edge_strategy"}
    ]
    
    test_cases.extend(edge_cases)
    
    # Shuffle to mix categories
    random.shuffle(test_cases)
    
    return test_cases[:200]  # Return exactly 200


def test_classifiers(test_cases):
    """Test both classifiers on the dataset"""
    
    final_classifier = EarningsClassifier()
    honest_classifier = HonestEarningsClassifier()
    
    results = {
        'final': [],
        'honest': []
    }
    
    print("Testing classifiers on 200 samples...")
    
    for i, case in enumerate(test_cases):
        # Test final classifier
        final_result = final_classifier.classify(case)
        results['final'].append({
            'id': f"test_{i}",
            'title': case['title'][:100],
            'category': case['category'],
            'expected': case['expected'],
            'predicted': final_result.is_earnings,
            'correct': final_result.is_earnings == case['expected'],
            'confidence': final_result.confidence,
            'needs_llm': final_classifier.should_use_llm(final_result),
            'method': final_result.method
        })
        
        # Test honest classifier
        honest_result = honest_classifier.classify(case)
        results['honest'].append({
            'id': f"test_{i}",
            'title': case['title'][:100],
            'category': case['category'],
            'expected': case['expected'],
            'predicted': honest_result['is_earnings'],
            'correct': honest_result['is_earnings'] == case['expected'],
            'confidence': honest_result['confidence'],
            'needs_llm': honest_result['needs_llm'],
            'method': honest_result.get('reason', '')
        })
        
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/200 samples...")
    
    return results


def analyze_results(results, classifier_name):
    """Comprehensive analysis of results"""
    
    df = pd.DataFrame(results)
    total = len(df)
    
    print(f"\n{'='*80}")
    print(f"{classifier_name.upper()} CLASSIFIER - ANALYSIS OF 200 SAMPLES")
    print("="*80)
    
    # Overall metrics
    correct = df['correct'].sum()
    accuracy = 100 * correct / total
    
    print(f"\nOVERALL PERFORMANCE:")
    print(f"  Total Samples: {total}")
    print(f"  Correct: {correct}")
    print(f"  Accuracy: {accuracy:.1f}%")
    
    # Split by actual label
    actual_earnings = df[df['expected'] == True]
    actual_not_earnings = df[df['expected'] == False]
    
    print(f"\n  Actual Distribution:")
    print(f"    Earnings: {len(actual_earnings)} ({100*len(actual_earnings)/total:.1f}%)")
    print(f"    Non-earnings: {len(actual_not_earnings)} ({100*len(actual_not_earnings)/total:.1f}%)")
    
    # False negatives and positives
    false_negatives = actual_earnings[actual_earnings['predicted'] == False]
    false_positives = actual_not_earnings[actual_not_earnings['predicted'] == True]
    
    fn_rate = 100 * len(false_negatives) / len(actual_earnings) if len(actual_earnings) > 0 else 0
    fp_rate = 100 * len(false_positives) / len(actual_not_earnings) if len(actual_not_earnings) > 0 else 0
    
    print(f"\nERROR ANALYSIS:")
    print(f"  False Negatives: {len(false_negatives)}/{len(actual_earnings)} ({fn_rate:.1f}%)")
    print(f"  False Positives: {len(false_positives)}/{len(actual_not_earnings)} ({fp_rate:.1f}%)")
    
    # Accuracy by confidence
    print(f"\nACCURACY BY CONFIDENCE LEVEL:")
    
    conf_ranges = [
        (0.95, 1.0, "Very High (≥0.95)"),
        (0.90, 0.95, "High (0.90-0.95)"),
        (0.85, 0.90, "Medium (0.85-0.90)"),
        (0.0, 0.85, "Low (<0.85)")
    ]
    
    for min_conf, max_conf, label in conf_ranges:
        mask = (df['confidence'] >= min_conf) & (df['confidence'] < max_conf)
        subset = df[mask]
        if len(subset) > 0:
            subset_correct = subset['correct'].sum()
            subset_acc = 100 * subset_correct / len(subset)
            subset_llm = subset['needs_llm'].sum()
            subset_llm_pct = 100 * subset_llm / len(subset)
            print(f"  {label:20} {subset_correct:3}/{len(subset):3} ({subset_acc:5.1f}%) - LLM: {subset_llm:3} ({subset_llm_pct:5.1f}%)")
    
    # Accuracy by category
    print(f"\nACCURACY BY CATEGORY:")
    categories = df['category'].unique()
    
    cat_results = []
    for cat in sorted(categories):
        cat_df = df[df['category'] == cat]
        if len(cat_df) > 0:
            cat_correct = cat_df['correct'].sum()
            cat_acc = 100 * cat_correct / len(cat_df)
            cat_results.append((cat, len(cat_df), cat_correct, cat_acc))
    
    # Sort by accuracy (worst first)
    cat_results.sort(key=lambda x: x[3])
    
    for cat, total, correct, acc in cat_results:
        print(f"  {cat:25} {correct:2}/{total:2} ({acc:5.1f}%)")
    
    # LLM usage
    total_llm = df['needs_llm'].sum()
    llm_pct = 100 * total_llm / total
    
    print(f"\nLLM USAGE:")
    print(f"  Total needing LLM: {total_llm}/{total} ({llm_pct:.1f}%)")
    
    # Confidence when wrong
    wrong = df[df['correct'] == False]
    if len(wrong) > 0:
        avg_conf_wrong = wrong['confidence'].mean()
        print(f"  Average confidence when wrong: {avg_conf_wrong:.2f}")
    
    # Show some false negatives
    if len(false_negatives) > 0:
        print(f"\nSAMPLE FALSE NEGATIVES (missed earnings):")
        for _, row in false_negatives.head(5).iterrows():
            print(f"  [{row['category']}] {row['title'][:60]:60} (conf: {row['confidence']:.2f})")
    
    return df


def main():
    """Run comprehensive 200-sample test"""
    
    print("COMPREHENSIVE TEST: 200 SAMPLES")
    print("="*80)
    
    # Create test set
    print("Creating diverse test set of 200 samples...")
    test_cases = create_large_test_set()
    
    # Count distribution
    earnings_count = sum(1 for case in test_cases if case['expected'])
    print(f"\nTest Set Composition:")
    print(f"  Total: 200 samples")
    print(f"  Earnings: {earnings_count} ({100*earnings_count/200:.1f}%)")
    print(f"  Non-earnings: {200-earnings_count} ({100*(200-earnings_count)/200:.1f}%)")
    
    # Test classifiers
    print("\nRunning tests...")
    results = test_classifiers(test_cases)
    
    # Analyze results
    final_df = analyze_results(results['final'], 'final')
    honest_df = analyze_results(results['honest'], 'honest')
    
    # Summary comparison
    print("\n" + "="*80)
    print("SUMMARY COMPARISON")
    print("="*80)
    
    final_acc = 100 * final_df['correct'].sum() / len(final_df)
    honest_acc = 100 * honest_df['correct'].sum() / len(honest_df)
    
    final_fn = len(final_df[(final_df['expected'] == True) & (final_df['predicted'] == False)])
    honest_fn = len(honest_df[(honest_df['expected'] == True) & (honest_df['predicted'] == False)])
    
    final_fp = len(final_df[(final_df['expected'] == False) & (final_df['predicted'] == True)])
    honest_fp = len(honest_df[(honest_df['expected'] == False) & (honest_df['predicted'] == True)])
    
    final_llm = final_df['needs_llm'].sum()
    honest_llm = honest_df['needs_llm'].sum()
    
    print(f"\n{'Metric':25} {'Final':>15} {'Honest':>15}")
    print("-"*55)
    print(f"{'Overall Accuracy':25} {final_acc:14.1f}% {honest_acc:14.1f}%")
    print(f"{'False Negatives':25} {final_fn:15} {honest_fn:15}")
    print(f"{'False Positives':25} {final_fp:15} {honest_fp:15}")
    print(f"{'Needs LLM':25} {final_llm:15} {honest_llm:15}")
    print(f"{'LLM Usage %':25} {100*final_llm/200:14.1f}% {100*honest_llm/200:14.1f}%")
    
    # Save results
    final_df.to_csv('final_classifier_200_results.csv', index=False)
    honest_df.to_csv('honest_classifier_200_results.csv', index=False)
    
    print("\nResults saved to CSV files for detailed analysis.")


if __name__ == "__main__":
    main()