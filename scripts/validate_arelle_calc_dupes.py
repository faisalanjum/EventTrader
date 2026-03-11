#!/usr/bin/env python3
"""
Arelle Items 4+5 Validation:
  Item 4: Spec-compliant calculation validation (inferredDecimals) vs current 0.1% tolerance
  Item 5: DuplicateFactSet deduplication vs current tie-break logic

READ-ONLY: Does NOT write to Neo4j or modify any pipeline files.
Loads filings from SEC EDGAR, runs both old and new approaches, compares results.

Usage: source venv/bin/activate && python scripts/validate_arelle_calc_dupes.py
"""
import sys, os, time, json, logging
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
from math import isinf, isnan
from dotenv import load_dotenv

# Setup
load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)
logging.basicConfig(level=logging.WARNING, format='%(message)s')

from arelle import Cntlr, FileSource, XbrlConst
from arelle.ModelFormulaObject import FormulaOptions
from arelle.ValidateXbrlCalcs import inferredDecimals, rangeValue
from arelle.ValidateDuplicateFacts import DuplicateFactSet

# Same 50 filings used in Items 1+2 validation
SAMPLE_URLS = [
    "https://www.sec.gov/Archives/edgar/data/109177/000119312523016335/d428749d10ka_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1584509/000158450923000237/cik0-20230929_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/34903/000003490323000064/frt-20230930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1687229/000168722923000081/invh-20230930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1086222/000108622223000187/akam-20230331_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1786352/000178635223000009/bill-20221231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1821806/000095017023018002/lesl-20230401_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1274494/000127449424000038/fslr-20240930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/872589/000180422023000016/regn-20230331_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1699838/000169983825000006/cflt-20250630_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1704711/000170471124000157/fnko-20240930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1520262/000095017023055178/alks-20230930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1447669/000144766924000034/twlo-20231231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/103379/000010337925000036/vfc-20250628_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1177609/000117760923000022/five-20230729_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1099800/000109980023000005/ew-20221231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/78003/000007800323000024/pfe-20221231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1532961/000162828023016102/nvee-20230401_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230701_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1177394/000117739424000075/snx-20240831_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1065837/000095017024120080/skx-20240930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/16058/000162828025038739/caci-20250630_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1506307/000150630723000023/kmi-20221231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1575515/000095017024018768/sfm-20231231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1600620/000160062024000041/auph-20231231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1090012/000095017023002852/dvn-20221231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1428336/000142833625000022/hqy-20250430_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/49826/000004982625000014/itw-20250331_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/711404/000071140423000045/coo-20230731_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1510295/000151029523000012/mpc-20221231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/87347/000095017025007638/slb-20241231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/107687/000010768723000028/wgo-20230826_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/868857/000110465923057746/acm-20230331x10q_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/97210/000095017025062503/ter-20250330_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/319201/000031920123000020/klac-20230331_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1410384/000141038424000197/qtwo-20240930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/901491/000162828023015436/pzza-20230326_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/61986/000095017023058333/mtw-20230930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1166691/000116669125000011/cmcsa-20241231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/71691/000007169123000034/nyt-20230930_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1447669/000144766923000171/twlo-20230630_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1506307/000150630723000036/kmi-20230331_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1802665/000155837025001441/hrmy-20241231x10k_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1802156/000095017025039541/xpof-20241231_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/883241/000088324123000019/snps-20231031_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1937653/000193765324000028/zyme-20240331_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1037868/000103786824000030/ame-20240331_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/1581068/000158106825000030/brx-20250630_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/899923/000089992323000058/mygn-20230630_htm.xml",
    "https://www.sec.gov/Archives/edgar/data/879101/000143774924005407/kim20231231_10k_htm.xml",
]


def load_filing(url):
    """Load a single XBRL filing via Arelle controller."""
    cntlr = Cntlr.Cntlr(logFileName="logToPrint")
    cntlr.startLogging(logFileName="logToPrint", logFileMode="w")

    model_xbrl = cntlr.modelManager.load(
        FileSource.openFileSource(url, cntlr),
        f"Loading {url}",
        formulaOptions=FormulaOptions()
    )

    if model_xbrl is None or not hasattr(model_xbrl, 'facts'):
        cntlr.close()
        return None, None

    return model_xbrl, cntlr


def clean_number(value):
    """Same as XBRL/utils.py:clean_number"""
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace(',', ''))


# ─── ITEM 4: Calculation validation ────────────────────────────────────

def validate_calc_old_way(parent_value, child_weighted_values):
    """
    Current codebase: 0.1% percentage tolerance.
    Returns (is_match, percent_diff)
    """
    total_sum = sum(child_weighted_values)
    if parent_value == 0:
        percent_diff = abs(parent_value - total_sum)
    else:
        percent_diff = abs(parent_value - total_sum) / abs(parent_value)
    return percent_diff < 0.001, percent_diff


def validate_calc_spec_way(parent_fact, child_facts_weights):
    """
    XBRL spec approach: uses inferredDecimals to compute valid range.
    A summation is valid if the difference (parent - sum_children) is within
    the rounding range implied by the LEAST precise participant.

    Returns (is_match, details_dict)
    """
    # Get parent's inferred decimals
    try:
        parent_dec = inferredDecimals(parent_fact)
    except:
        return None, {"reason": "cannot_infer_parent_decimals"}

    # Compute sum of weighted children
    total_sum = Decimal(0)
    min_decimals = parent_dec  # track least precise

    for child_fact, weight in child_facts_weights:
        try:
            child_dec = inferredDecimals(child_fact)
        except:
            return None, {"reason": "cannot_infer_child_decimals"}

        try:
            child_val = Decimal(str(child_fact.xValue)) * Decimal(str(weight))
            total_sum += child_val
        except:
            return None, {"reason": "cannot_compute_child_value"}

        # Track least precise decimals (smallest number = least precise)
        if not (isinf(child_dec) or isnan(child_dec)):
            if isinf(min_decimals) or isnan(min_decimals):
                min_decimals = child_dec
            else:
                min_decimals = min(min_decimals, child_dec)

    # Also consider parent precision
    if not (isinf(parent_dec) or isnan(parent_dec)):
        if isinf(min_decimals) or isnan(min_decimals):
            min_decimals = parent_dec
        else:
            min_decimals = min(min_decimals, parent_dec)

    try:
        parent_val = Decimal(str(parent_fact.xValue))
    except:
        return None, {"reason": "cannot_get_parent_xValue"}

    diff = abs(parent_val - total_sum)

    # If all participants are INF precision, must match exactly
    if isinf(min_decimals):
        is_match = diff == 0
        return is_match, {
            "parent_decimals": "INF",
            "min_decimals": "INF",
            "tolerance": "0 (exact)",
            "diff": str(diff)
        }

    # If any decimals are NaN, can't determine
    if isnan(min_decimals):
        return None, {"reason": "nan_decimals"}

    # Tolerance = 10^(-min_decimals) / 2 (round-to-nearest per Calc 1.1)
    tolerance = Decimal(10) ** Decimal(-int(min_decimals)) / Decimal(2)
    is_match = diff <= tolerance

    return is_match, {
        "parent_decimals": str(parent_dec),
        "min_decimals": str(min_decimals),
        "tolerance": str(tolerance),
        "diff": str(diff)
    }


def run_item4_for_filing(model_xbrl):
    """
    Compare old (0.1% tolerance) vs new (spec-compliant decimals-based) calc validation.
    Builds calc relationships from scratch (same as xbrl_processor._build_networks + check_calculation_steps).
    """
    results = {
        "both_match": 0,          # old=match, new=match
        "both_nonmatch": 0,       # old=nonmatch, new=nonmatch
        "old_match_new_nonmatch": 0,   # FALSE POSITIVE in old code
        "old_nonmatch_new_match": 0,   # FALSE NEGATIVE in old code
        "new_undetermined": 0,    # spec can't determine (NaN decimals etc)
        "total_summations": 0,
        "false_positive_examples": [],
        "false_negative_examples": [],
    }

    # Get all calculation networks
    calc_arcrole = XbrlConst.summationItem
    link_roles = model_xbrl.relationshipSet(calc_arcrole).linkRoleUris

    for network_uri in link_roles:
        rel_set = model_xbrl.relationshipSet(calc_arcrole, network_uri)
        if not rel_set:
            continue

        # Build parent->[(child_fact, weight)] groups per context
        # We need actual facts, not just concepts
        roots = rel_set.rootConcepts

        # Walk calc tree to get parent-child-weight relationships at concept level
        concept_children = defaultdict(list)  # parent_concept -> [(child_concept, weight)]

        def walk_calc(concept):
            concept_key = str(concept.qname)
            for child_rel in rel_set.fromModelObject(concept):
                if child_rel.toModelObject is None:
                    continue
                child = child_rel.toModelObject
                concept_children[concept_key].append((child, child_rel.weight))
                walk_calc(child)

        for root in roots:
            walk_calc(root)

        if not concept_children:
            continue

        # Group facts by (concept_qname, context_id, unit_id) for lookup
        fact_index = defaultdict(list)
        for fact in model_xbrl.factsInInstance:
            if fact.isNumeric and fact.context is not None and not fact.isNil:
                key = (str(fact.concept.qname), fact.contextID, fact.unitID)
                fact_index[key].append(fact)

        # For each parent concept with calc children, find matching facts
        for parent_qname, children_and_weights in concept_children.items():
            # Find all fact instances for this parent concept
            parent_facts_by_ctx = defaultdict(list)
            for key, facts in fact_index.items():
                if key[0] == parent_qname:
                    for f in facts:
                        parent_facts_by_ctx[(f.contextID, f.unitID)].append(f)

            for (ctx_id, unit_id), parent_facts in parent_facts_by_ctx.items():
                parent_fact = parent_facts[0]  # take first (same as codebase simplification)

                # Find matching child facts in same context+unit
                child_facts_weights = []
                all_children_found = True
                for child_concept, weight in children_and_weights:
                    child_key = (str(child_concept.qname), ctx_id, unit_id)
                    child_facts = fact_index.get(child_key, [])
                    if not child_facts:
                        all_children_found = False
                        break
                    child_facts_weights.append((child_facts[0], weight))

                if not all_children_found or not child_facts_weights:
                    continue

                results["total_summations"] += 1

                # OLD WAY: 0.1% tolerance
                try:
                    parent_value = clean_number(parent_fact.sValue if hasattr(parent_fact, 'sValue') else parent_fact.value)
                    child_weighted = [float(cf.sValue if hasattr(cf, 'sValue') else cf.value) * w
                                     for cf, w in child_facts_weights]
                    old_match, old_pct = validate_calc_old_way(parent_value, child_weighted)
                except (ValueError, TypeError):
                    continue

                # NEW WAY: spec-compliant decimals
                new_match, new_details = validate_calc_spec_way(parent_fact, child_facts_weights)

                if new_match is None:
                    results["new_undetermined"] += 1
                    continue

                if old_match and new_match:
                    results["both_match"] += 1
                elif not old_match and not new_match:
                    results["both_nonmatch"] += 1
                elif old_match and not new_match:
                    # Old says match, spec says no → FALSE POSITIVE in old code
                    results["old_match_new_nonmatch"] += 1
                    if len(results["false_positive_examples"]) < 5:
                        results["false_positive_examples"].append({
                            "parent": parent_qname,
                            "context": ctx_id,
                            "parent_value": str(parent_fact.xValue),
                            "parent_decimals": parent_fact.decimals,
                            "sum": str(sum(Decimal(str(cf.xValue)) * Decimal(str(w)) for cf, w in child_facts_weights)),
                            "old_pct_diff": f"{old_pct:.6f}",
                            "spec_details": new_details,
                        })
                else:
                    # Old says no match, spec says match → FALSE NEGATIVE in old code
                    results["old_nonmatch_new_match"] += 1
                    if len(results["false_negative_examples"]) < 5:
                        results["false_negative_examples"].append({
                            "parent": parent_qname,
                            "context": ctx_id,
                            "parent_value": str(parent_fact.xValue),
                            "parent_decimals": parent_fact.decimals,
                            "sum": str(sum(Decimal(str(cf.xValue)) * Decimal(str(w)) for cf, w in child_facts_weights)),
                            "old_pct_diff": f"{old_pct:.6f}",
                            "spec_details": new_details,
                        })

    return results


# ─── ITEM 5: Duplicate fact detection ──────────────────────────────────

def run_item5_for_filing(model_xbrl):
    """
    Compare old (custom tie-break) vs new (DuplicateFactSet) duplicate detection.

    Old approach: group by (qname, context_id, unit_id), pick fact with higher decimals
                  or more significant digits. Non-deterministic due to set iteration.

    New approach: DuplicateFactSet.deduplicateConsistentSet() — spec-compliant,
                  picks highest-precision fact deterministically.
    """
    results = {
        "total_facts": 0,
        "facts_with_duplicates": 0,
        "duplicate_groups": 0,
        "same_primary_selected": 0,     # old and new pick same fact
        "different_primary_selected": 0, # old and new pick different fact
        "old_nondeterministic_groups": 0, # groups where old approach is order-dependent
        "new_inconsistent_groups": 0,     # groups with inconsistent duplicates (spec)
        "examples_different": [],
        "nondeterminism_examples": [],
    }

    # Filter valid facts (same as _build_facts)
    valid_facts = [fact for fact in model_xbrl.factsInInstance
                   if not (fact.id and fact.id.startswith('hidden-fact'))
                   and fact.context is not None
                   and hasattr(fact, 'contextID') and fact.contextID]

    results["total_facts"] = len(valid_facts)

    # Group by canonical key (same as codebase)
    groups = defaultdict(list)
    for fact in valid_facts:
        canonical_key = f"{fact.concept.qname}:{fact.contextID}:{fact.unitID}"
        groups[canonical_key].append(fact)

    # Only look at groups with duplicates
    for canonical_key, facts in groups.items():
        if len(facts) < 2:
            continue

        results["duplicate_groups"] += 1
        results["facts_with_duplicates"] += len(facts)

        # ─── OLD WAY: custom tie-break (simulates _build_facts logic) ───
        # Note: factsInInstance is a set, so iteration order is non-deterministic.
        # We simulate this by trying both orderings for 2-fact groups.

        def old_pick_primary(fact_list):
            """Simulate current tie-break. Returns primary fact."""
            primary = fact_list[0]
            for fact in fact_list[1:]:
                fact_decimals = fact.decimals if fact.decimals is not None else float('-inf')
                primary_decimals = primary.decimals if primary.decimals is not None else float('-inf')

                # Convert string decimals to comparable values
                try:
                    if isinstance(fact_decimals, str):
                        fact_decimals = float('inf') if fact_decimals == 'INF' else int(fact_decimals)
                    if isinstance(primary_decimals, str):
                        primary_decimals = float('inf') if primary_decimals == 'INF' else int(primary_decimals)
                except (ValueError, TypeError):
                    pass

                if fact_decimals > primary_decimals or (
                    fact_decimals == primary_decimals and
                    len(str(fact.sValue).lstrip('0').replace('.', '').replace('-', '')) >
                    len(str(primary.sValue).lstrip('0').replace('.', '').replace('-', ''))
                ):
                    primary = fact
            return primary

        # Check if old approach is order-dependent (non-deterministic)
        old_primary_forward = old_pick_primary(facts)
        old_primary_reverse = old_pick_primary(list(reversed(facts)))

        is_nondeterministic = (old_primary_forward is not old_primary_reverse)
        if is_nondeterministic:
            results["old_nondeterministic_groups"] += 1
            if len(results["nondeterminism_examples"]) < 5:
                results["nondeterminism_examples"].append({
                    "canonical_key": canonical_key,
                    "num_duplicates": len(facts),
                    "forward_pick_id": old_primary_forward.id,
                    "forward_pick_decimals": old_primary_forward.decimals,
                    "forward_pick_value": str(old_primary_forward.sValue)[:50],
                    "reverse_pick_id": old_primary_reverse.id,
                    "reverse_pick_decimals": old_primary_reverse.decimals,
                    "reverse_pick_value": str(old_primary_reverse.sValue)[:50],
                })

        # ─── NEW WAY: DuplicateFactSet ───
        # Only process numeric facts through DuplicateFactSet (non-numeric use exact match)
        if facts[0].isNumeric:
            try:
                dup_set = DuplicateFactSet(facts=facts)
                new_primary_list, reason = dup_set.deduplicateConsistentSet()

                if reason:
                    results["new_inconsistent_groups"] += 1

                if len(new_primary_list) == 1:
                    new_primary = new_primary_list[0]
                else:
                    # Multiple results means inconsistent — take highest decimals as fallback
                    new_primary = new_primary_list[0]

                # Compare selections
                if old_primary_forward is new_primary:
                    results["same_primary_selected"] += 1
                else:
                    results["different_primary_selected"] += 1
                    if len(results["examples_different"]) < 10:
                        results["examples_different"].append({
                            "canonical_key": canonical_key,
                            "num_duplicates": len(facts),
                            "old_pick_id": old_primary_forward.id,
                            "old_pick_decimals": old_primary_forward.decimals,
                            "old_pick_value": str(old_primary_forward.sValue)[:50],
                            "new_pick_id": new_primary.id,
                            "new_pick_decimals": new_primary.decimals,
                            "new_pick_value": str(new_primary.sValue)[:50],
                            "is_old_nondeterministic": is_nondeterministic,
                            "arelle_consistent": dup_set.areAllConsistent,
                            "arelle_complete": dup_set.areAllComplete,
                            "reason": reason,
                        })
            except Exception as e:
                # DuplicateFactSet might fail on edge cases
                pass
        else:
            # Non-numeric: DuplicateFactSet uses exact value match
            try:
                dup_set = DuplicateFactSet(facts=facts)
                complete_deduped = dup_set.deduplicateCompleteSubsets()
                if len(complete_deduped) == 1:
                    new_primary = complete_deduped[0]
                    if old_primary_forward is new_primary:
                        results["same_primary_selected"] += 1
                    else:
                        results["different_primary_selected"] += 1
                else:
                    # Non-numeric with different values — not really duplicates
                    results["same_primary_selected"] += 1  # both would keep all
            except:
                pass

    return results


# ─── MAIN ──────────────────────────────────────────────────────────────

def main():
    total_start = time.time()
    all_results = []

    # Totals for Item 4
    total_item4 = {
        "both_match": 0, "both_nonmatch": 0,
        "old_match_new_nonmatch": 0, "old_nonmatch_new_match": 0,
        "new_undetermined": 0, "total_summations": 0,
        "all_false_positives": [], "all_false_negatives": [],
    }

    # Totals for Item 5
    total_item5 = {
        "total_facts": 0, "duplicate_groups": 0,
        "same_primary_selected": 0, "different_primary_selected": 0,
        "old_nondeterministic_groups": 0, "new_inconsistent_groups": 0,
        "all_nondeterminism_examples": [], "all_different_examples": [],
    }

    errors = 0

    for i, url in enumerate(SAMPLE_URLS):
        ticker = url.split('/')[-1].split('-')[0].split('_')[0]
        t0 = time.time()
        print(f"[{i+1:2d}/50] {ticker}...", end=" ", flush=True)

        try:
            model_xbrl, cntlr = load_filing(url)
            if model_xbrl is None:
                print("LOAD_ERROR")
                errors += 1
                continue

            # Run Item 4
            r4 = run_item4_for_filing(model_xbrl)

            # Run Item 5
            r5 = run_item5_for_filing(model_xbrl)

            elapsed = time.time() - t0

            # Accumulate Item 4
            total_item4["both_match"] += r4["both_match"]
            total_item4["both_nonmatch"] += r4["both_nonmatch"]
            total_item4["old_match_new_nonmatch"] += r4["old_match_new_nonmatch"]
            total_item4["old_nonmatch_new_match"] += r4["old_nonmatch_new_match"]
            total_item4["new_undetermined"] += r4["new_undetermined"]
            total_item4["total_summations"] += r4["total_summations"]
            for ex in r4["false_positive_examples"]:
                ex["ticker"] = ticker
                total_item4["all_false_positives"].append(ex)
            for ex in r4["false_negative_examples"]:
                ex["ticker"] = ticker
                total_item4["all_false_negatives"].append(ex)

            # Accumulate Item 5
            total_item5["total_facts"] += r5["total_facts"]
            total_item5["duplicate_groups"] += r5["duplicate_groups"]
            total_item5["same_primary_selected"] += r5["same_primary_selected"]
            total_item5["different_primary_selected"] += r5["different_primary_selected"]
            total_item5["old_nondeterministic_groups"] += r5["old_nondeterministic_groups"]
            total_item5["new_inconsistent_groups"] += r5["new_inconsistent_groups"]
            for ex in r5["nondeterminism_examples"]:
                ex["ticker"] = ticker
                total_item5["all_nondeterminism_examples"].append(ex)
            for ex in r5["examples_different"]:
                ex["ticker"] = ticker
                total_item5["all_different_examples"].append(ex)

            fp = r4["old_match_new_nonmatch"]
            fn = r4["old_nonmatch_new_match"]
            nd = r5["old_nondeterministic_groups"]
            dd = r5["different_primary_selected"]

            status_parts = []
            if fp: status_parts.append(f"calc_FP={fp}")
            if fn: status_parts.append(f"calc_FN={fn}")
            if nd: status_parts.append(f"dup_nondet={nd}")
            if dd: status_parts.append(f"dup_diff={dd}")
            status = ", ".join(status_parts) if status_parts else "clean"

            print(f"{status} ({elapsed:.1f}s)")

            all_results.append({
                "url": url,
                "ticker": ticker,
                "time_seconds": round(elapsed, 1),
                "item4": {k: v for k, v in r4.items() if not k.endswith("_examples")},
                "item5": {k: v for k, v in r5.items() if not k.endswith("_examples") and k != "examples_different"},
            })

            # Cleanup
            cntlr.modelManager.close()
            cntlr.close()

        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1
            continue

    total_elapsed = time.time() - total_start

    # ─── Print summary ───
    print("\n" + "=" * 72)
    print(f"ITEM 4: CALCULATION VALIDATION ({total_elapsed:.0f}s total)")
    print("=" * 72)
    print(f"  Total summation checks:     {total_item4['total_summations']}")
    print(f"  Both agree MATCH:           {total_item4['both_match']}")
    print(f"  Both agree NON-MATCH:       {total_item4['both_nonmatch']}")
    print(f"  FALSE POSITIVES (old=Y new=N): {total_item4['old_match_new_nonmatch']}")
    print(f"  FALSE NEGATIVES (old=N new=Y): {total_item4['old_nonmatch_new_match']}")
    print(f"  Undetermined (NaN decimals):   {total_item4['new_undetermined']}")

    if total_item4['total_summations'] > 0:
        agree = total_item4['both_match'] + total_item4['both_nonmatch']
        determined = total_item4['total_summations'] - total_item4['new_undetermined']
        if determined > 0:
            print(f"  Agreement rate:             {agree/determined*100:.1f}% ({agree}/{determined})")

    if total_item4['all_false_positives']:
        print(f"\n  First {min(5, len(total_item4['all_false_positives']))} FALSE POSITIVE examples (old code says match, spec says no):")
        for ex in total_item4['all_false_positives'][:5]:
            print(f"    [{ex['ticker']}] {ex['parent']} ctx={ex['context'][:30]}")
            print(f"      parent={ex['parent_value']}, decimals={ex['parent_decimals']}")
            print(f"      sum={ex['sum']}, old_pct_diff={ex['old_pct_diff']}")
            print(f"      spec: tolerance={ex['spec_details'].get('tolerance')}, diff={ex['spec_details'].get('diff')}")

    if total_item4['all_false_negatives']:
        print(f"\n  First {min(5, len(total_item4['all_false_negatives']))} FALSE NEGATIVE examples (old code says no match, spec says yes):")
        for ex in total_item4['all_false_negatives'][:5]:
            print(f"    [{ex['ticker']}] {ex['parent']} ctx={ex['context'][:30]}")
            print(f"      parent={ex['parent_value']}, decimals={ex['parent_decimals']}")
            print(f"      sum={ex['sum']}, old_pct_diff={ex['old_pct_diff']}")
            print(f"      spec: tolerance={ex['spec_details'].get('tolerance')}, diff={ex['spec_details'].get('diff')}")

    print("\n" + "=" * 72)
    print(f"ITEM 5: DUPLICATE FACT DETECTION")
    print("=" * 72)
    print(f"  Total facts processed:      {total_item5['total_facts']}")
    print(f"  Duplicate groups found:     {total_item5['duplicate_groups']}")
    print(f"  Same primary selected:      {total_item5['same_primary_selected']}")
    print(f"  Different primary selected: {total_item5['different_primary_selected']}")
    print(f"  Old nondeterministic groups: {total_item5['old_nondeterministic_groups']}")
    print(f"  New inconsistent groups:    {total_item5['new_inconsistent_groups']}")

    if total_item5['all_nondeterminism_examples']:
        print(f"\n  First {min(5, len(total_item5['all_nondeterminism_examples']))} NONDETERMINISM examples (old code gives different result based on iteration order):")
        for ex in total_item5['all_nondeterminism_examples'][:5]:
            print(f"    [{ex['ticker']}] {ex['canonical_key'][:60]}")
            print(f"      forward: id={ex['forward_pick_id']}, dec={ex['forward_pick_decimals']}, val={ex['forward_pick_value']}")
            print(f"      reverse: id={ex['reverse_pick_id']}, dec={ex['reverse_pick_decimals']}, val={ex['reverse_pick_value']}")

    if total_item5['all_different_examples']:
        print(f"\n  First {min(10, len(total_item5['all_different_examples']))} DIFFERENT SELECTION examples (old vs DuplicateFactSet):")
        for ex in total_item5['all_different_examples'][:10]:
            print(f"    [{ex['ticker']}] {ex['canonical_key'][:60]}")
            print(f"      old:  id={ex['old_pick_id']}, dec={ex['old_pick_decimals']}, val={ex['old_pick_value']}")
            print(f"      new:  id={ex['new_pick_id']}, dec={ex['new_pick_decimals']}, val={ex['new_pick_value']}")
            print(f"      nondeterministic={ex['is_old_nondeterministic']}, consistent={ex['arelle_consistent']}, complete={ex['arelle_complete']}")

    print(f"\n  Load errors: {errors}")
    print("=" * 72)

    # Save results
    output_path = Path(__file__).parent / "validate_arelle_calc_dupes_results.json"
    output = {
        "item4_summary": {k: v for k, v in total_item4.items()},
        "item5_summary": {k: v for k, v in total_item5.items()},
        "per_filing": all_results,
        "total_seconds": round(total_elapsed, 1),
        "errors": errors,
    }
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nDetailed results saved to {output_path}")


if __name__ == "__main__":
    main()
