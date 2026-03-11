#!/usr/bin/env python3
"""
Arelle Items 1+2 Validation: rootConcepts + fromModelObject vs manual tree building.

READ-ONLY: Does NOT write to Neo4j or modify any files.
Loads filings from SEC EDGAR, builds trees both ways, compares node-for-node.

Usage: source venv/bin/activate && python scripts/validate_arelle_tree_apis.py
"""
import sys, os, time, json, random, logging
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

# Setup
load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)
logging.basicConfig(level=logging.WARNING, format='%(message)s')

from arelle import Cntlr, FileSource, XbrlConst
from arelle.ModelFormulaObject import FormulaOptions

# 50 random filings from Neo4j (pre-selected, diverse: 10-K, 10-Q, 10-K/A)
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


def make_concept_id(model_obj):
    """Same ID format as your codebase: namespace:qname"""
    return f"{model_obj.qname.namespaceURI}:{model_obj.qname}"


def build_tree_old_way(rel_set):
    """
    Current codebase approach: flat iterate modelRelationships,
    build parent_child_map, compute roots via set subtraction.
    Returns (roots_set, nodes_dict) where nodes_dict maps concept_id -> sorted children list.
    """
    if not rel_set:
        return set(), {}

    parent_child_map = defaultdict(list)
    for rel in rel_set.modelRelationships:
        if rel.fromModelObject is None or rel.toModelObject is None:
            continue
        parent_id = make_concept_id(rel.fromModelObject)
        child_id = make_concept_id(rel.toModelObject)
        parent_child_map[parent_id].append((child_id, rel.order or 0))

    # Roots: parents that are never children (current codebase logic)
    all_children = {child for children in parent_child_map.values() for child, _ in children}
    roots = set(parent_child_map.keys()) - all_children

    # Build sorted children for each node
    nodes = {}
    for parent_id, children in parent_child_map.items():
        nodes[parent_id] = sorted(children, key=lambda x: x[1])
    return roots, nodes


def build_tree_new_way(rel_set):
    """
    New API approach: use rootConcepts + fromModelObject() recursive walk.
    Returns (roots_set, nodes_dict) in same format for comparison.
    """
    if not rel_set:
        return set(), {}

    root_concepts = rel_set.rootConcepts
    roots = set()
    nodes = defaultdict(list)

    def walk(concept):
        concept_id = make_concept_id(concept)
        if concept_id in nodes:
            return  # Already visited (cycle protection)
        nodes[concept_id] = []  # Mark as visited
        child_rels = rel_set.fromModelObject(concept)
        children = []
        for child_rel in child_rels:
            if child_rel.toModelObject is None:
                continue
            child_id = make_concept_id(child_rel.toModelObject)
            children.append((child_id, child_rel.order or 0))
            walk(child_rel.toModelObject)
        nodes[concept_id] = sorted(children, key=lambda x: x[1])

    for root in root_concepts:
        root_id = make_concept_id(root)
        roots.add(root_id)
        walk(root)

    return roots, dict(nodes)


def compare_trees(old_roots, old_nodes, new_roots, new_nodes, network_uri, arcrole_label):
    """Compare two tree representations. Returns list of differences."""
    diffs = []

    # Compare roots
    if old_roots != new_roots:
        only_old = old_roots - new_roots
        only_new = new_roots - old_roots
        diffs.append(f"  ROOT MISMATCH [{arcrole_label}] {network_uri}: "
                     f"old_only={len(only_old)} new_only={len(only_new)}")
        for r in list(only_old)[:3]:
            diffs.append(f"    old_only: {r}")
        for r in list(only_new)[:3]:
            diffs.append(f"    new_only: {r}")

    # Compare node children
    all_concept_ids = set(old_nodes.keys()) | set(new_nodes.keys())
    for cid in all_concept_ids:
        old_children = old_nodes.get(cid, [])
        new_children = new_nodes.get(cid, [])
        if old_children != new_children:
            diffs.append(f"  CHILDREN MISMATCH [{arcrole_label}] {cid}: "
                         f"old={len(old_children)} new={len(new_children)}")

    return diffs


def validate_filing(url, controller):
    """Load one filing, compare old vs new tree building for all networks."""
    ticker = url.split('/')[-1].split('-')[0].split('_')[0]
    result = {
        'url': url, 'ticker': ticker, 'status': 'OK',
        'pres_networks': 0, 'calc_networks': 0,
        'pres_nodes_total': 0, 'calc_nodes_total': 0,
        'diffs': []
    }

    try:
        model = controller.modelManager.load(
            filesource=FileSource.FileSource(url), discover=True
        )
    except Exception as e:
        result['status'] = f'LOAD_ERROR: {str(e)[:80]}'
        return result

    try:
        # Get all linkroles that have presentation or calculation relationships
        for arcrole, label in [
            (XbrlConst.parentChild, 'PRES'),
            (XbrlConst.summationItem, 'CALC')
        ]:
            # Get all linkroles for this arcrole
            full_rel_set = model.relationshipSet(arcrole)
            if not full_rel_set:
                continue

            linkroles = set()
            for rel in full_rel_set.modelRelationships:
                linkroles.add(rel.linkrole)

            for linkrole in linkroles:
                rel_set = model.relationshipSet(arcrole, linkrole)
                if not rel_set or not rel_set.modelRelationships:
                    continue

                if label == 'PRES':
                    result['pres_networks'] += 1
                else:
                    result['calc_networks'] += 1

                # Build trees both ways
                old_roots, old_nodes = build_tree_old_way(rel_set)
                new_roots, new_nodes = build_tree_new_way(rel_set)

                node_count = max(len(old_nodes), len(new_nodes))
                if label == 'PRES':
                    result['pres_nodes_total'] += node_count
                else:
                    result['calc_nodes_total'] += node_count

                # Compare
                diffs = compare_trees(old_roots, old_nodes, new_roots, new_nodes,
                                      linkrole, label)
                result['diffs'].extend(diffs)

    except Exception as e:
        result['status'] = f'PROCESS_ERROR: {str(e)[:80]}'
    finally:
        try:
            model.close()
        except:
            pass

    if result['diffs']:
        result['status'] = f'DIFFS_FOUND ({len(result["diffs"])})'

    return result


def main():
    print("=" * 80)
    print("ARELLE ITEMS 1+2 VALIDATION: rootConcepts + fromModelObject vs manual")
    print("READ-ONLY — no database writes, no code changes")
    print("=" * 80)

    controller = Cntlr.Cntlr(logFileName='NUL' if os.name == 'nt' else '/dev/null')
    controller.modelManager.formulaOptions = FormulaOptions()

    # SEC compliance
    if hasattr(controller, 'webCache'):
        controller.webCache.userAgent = "EventTrader faianjum@gmail.com"
        controller.webCache.delay = 0.25 + random.uniform(0, 0.1)
        controller.webCache.timeout = 120
        controller.webCache.noCertificateCheck = True
        controller.webCache.recheck = float('inf')

    results = []
    total = len(SAMPLE_URLS)
    start_time = time.time()

    for i, url in enumerate(SAMPLE_URLS, 1):
        ticker = url.split('/')[-1].split('-')[0].split('_')[0]
        elapsed = time.time() - start_time
        print(f"\n[{i}/{total}] {ticker} ({elapsed:.0f}s elapsed)")

        filing_start = time.time()
        result = validate_filing(url, controller)
        filing_time = time.time() - filing_start

        result['time_seconds'] = round(filing_time, 1)
        results.append(result)

        # Print inline result
        status_icon = "PASS" if result['status'] == 'OK' else "FAIL"
        print(f"  {status_icon} | pres_networks={result['pres_networks']} "
              f"calc_networks={result['calc_networks']} "
              f"pres_nodes={result['pres_nodes_total']} "
              f"calc_nodes={result['calc_nodes_total']} "
              f"| {filing_time:.1f}s")

        if result['diffs']:
            for d in result['diffs'][:5]:
                print(f"  {d}")
            if len(result['diffs']) > 5:
                print(f"  ... and {len(result['diffs']) - 5} more diffs")

    # Summary
    total_time = time.time() - start_time
    passed = sum(1 for r in results if r['status'] == 'OK')
    failed = sum(1 for r in results if 'DIFFS_FOUND' in r['status'])
    errors = sum(1 for r in results if 'ERROR' in r['status'])

    print("\n" + "=" * 80)
    print(f"FINAL SUMMARY ({total_time:.0f}s total)")
    print(f"  Filings tested: {total}")
    print(f"  PASS (trees match):  {passed}")
    print(f"  FAIL (diffs found):  {failed}")
    print(f"  ERROR (load failed): {errors}")
    print(f"  Total pres networks: {sum(r['pres_networks'] for r in results)}")
    print(f"  Total calc networks: {sum(r['calc_networks'] for r in results)}")
    print(f"  Total pres nodes:    {sum(r['pres_nodes_total'] for r in results)}")
    print(f"  Total calc nodes:    {sum(r['calc_nodes_total'] for r in results)}")

    if failed == 0 and errors == 0:
        print("\n  VERDICT: rootConcepts + fromModelObject() produces IDENTICAL trees")
        print("           to manual set-subtraction + flat iteration for all 50 filings.")
    elif failed > 0:
        print(f"\n  VERDICT: {failed} filings had differences — investigate before migrating.")

    # Save detailed results
    out_path = Path(__file__).parent / 'validate_arelle_tree_results.json'
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Detailed results saved to: {out_path}")

    controller.close()


if __name__ == '__main__':
    main()
