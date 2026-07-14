#!/usr/bin/env python3
"""Code tier (0 LLM tokens): resolve KPI->verbatim quote deterministically from Neo4j XBRL + sections.

FETCH stage of the fiscal.ai metric channel (S2 packet spec, Part D). Per company-period it fetches
each SOURCE EVENT separately -- the 10-Q/10-K filing (XBRL + text sections) AND the earnings 8-K
EX-99.1 press release -- and resolves the KPI's value against EACH source on its own. A quote is
stamped with the accession of the doc that ACTUALLY contains it (provenance is never merged): a value
found only in the press release becomes an 8-K-sourced record, never a mis-stamped 10-Q record. A value
present in both filing and PR = two records on two events (read-time collapse merges them later).

Gate-clean hits -> code_resolved.jsonl (rich FETCH record). value_ok gate-fails / label-only hits ->
residual.jsonl (candidates tagged with their source, handed to the LLM locator). Derived rows / plugs ->
abstain.jsonl. Records carry raw signals ONLY (cadence, period_end, xbrl context); NO decomposition
(name/slice/measurement/unit/fiscal-quarter are shared-core, added downstream by the adapter+decomposer).

    venv/bin/python scripts/driver_seed/run_code_tier.py --part 1 --nparts 4
    venv/bin/python scripts/driver_seed/run_code_tier.py --tickers AAP,AGL --tag smoke   # small free run

Reads data/driver_catalog_seed/worklist.jsonl; writes data/driver_catalog_seed/<tag>/.
"""
import os, re, json, argparse, collections, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(__file__))
import link_lib as L

OUT = 'data/driver_catalog_seed'
FORMMAP = {'10-K': '10k', '10-Q': '10q', '8-K': '8k'}


def load_env_neo4j():
    for line in open('.env'):
        m = re.match(r'\s*(NEO4J_[A-Z_]+)=(.*)', line)
        if m:
            os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


# --- legacy fetchers (relocate_probe pipeline: prep/grade/oracle/exam depend on these exact signatures) ---
def fetch_press_release(session, tk, period):
    """earnings 8-K EX-99.1 filed ~5-75 days AFTER the fiscal period end (announce-date offset)."""
    try:
        d0 = date.fromisoformat(period[:10])
    except ValueError:
        return []
    lo = (d0 + timedelta(days=5)).isoformat(); hi = (d0 + timedelta(days=75)).isoformat()
    rows = list(session.run(
        """MATCH (r:Report {formType:'8-K'})-[:PRIMARY_FILER]->(c:Company {ticker:$tk})
           WHERE r.periodOfReport >= $lo AND r.periodOfReport <= $hi
           MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
           WHERE e.exhibit_number IN ['EX-99.1','EX-99','99.1']
           RETURN e.content AS content ORDER BY r.periodOfReport LIMIT 3""",
        tk=tk, lo=lo, hi=hi))
    return [x['content'] for x in rows if x['content']]


def fetch_corpus(session, tk, form, period):
    """xbrls (list of JSON strings), texts (list of section strings), filing_ids."""
    rows = list(session.run(
        """MATCH (r:Report {formType:$form})-[:PRIMARY_FILER]->(c:Company {ticker:$tk})
           WHERE r.periodOfReport STARTS WITH $period
           OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
           OPTIONAL MATCH (r)-[:HAS_SECTION]->(x:ExtractedSectionContent)
           RETURN elementId(r) AS report_eid,
                  collect(DISTINCT f.value)      AS xbrls,
                  collect(DISTINCT x.content)    AS texts,
                  collect(DISTINCT f.filing_id)  AS ffids,
                  collect(DISTINCT x.filing_id)  AS xfids""",
        form=form, tk=tk, period=period))
    xbrls, texts, fids = [], [], []
    for r in rows:
        xbrls += [v for v in r['xbrls'] if v]
        texts += [v for v in r['texts'] if v]
        fids += [v for v in (r['ffids'] + r['xfids']) if v]
        if r['report_eid']:
            fids.append(r['report_eid'])
    seen = []
    for f in fids:
        if f not in seen:
            seen.append(f)
    return xbrls, texts, seen


def fetch_filing(session, tk, form, period):
    """The named filing as ONE source event: {source_id, source_type, event_time, xbrls, texts}."""
    rows = list(session.run(
        """MATCH (r:Report {formType:$form})-[:PRIMARY_FILER]->(c:Company {ticker:$tk})
           WHERE r.periodOfReport STARTS WITH $period
           OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
           OPTIONAL MATCH (r)-[:HAS_SECTION]->(x:ExtractedSectionContent)
           RETURN r.accessionNo AS acc, r.created AS created,
                  collect(DISTINCT f.value)   AS xbrls,
                  collect(DISTINCT x.content) AS texts""",
        form=form, tk=tk, period=period))
    if not rows or not rows[0]['acc']:
        return None
    r = rows[0]
    return {'source_id': r['acc'], 'source_type': FORMMAP.get(form, form), 'event_time': r['created'],
            'xbrls': [x for x in r['xbrls'] if x], 'texts': [x for x in r['texts'] if x]}


def fetch_press_releases(session, tk, period):
    """Earnings 8-K EX-99.1 filed ~5-75d AFTER period end -> a list of separate 8-K source events."""
    try:
        d0 = date.fromisoformat(period[:10])
    except ValueError:
        return []
    lo = (d0 + timedelta(days=5)).isoformat(); hi = (d0 + timedelta(days=75)).isoformat()
    rows = list(session.run(
        """MATCH (r:Report {formType:'8-K'})-[:PRIMARY_FILER]->(c:Company {ticker:$tk})
           WHERE r.periodOfReport >= $lo AND r.periodOfReport <= $hi
           MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
           WHERE e.exhibit_number IN ['EX-99.1','EX-99','99.1']
           RETURN r.accessionNo AS acc, r.created AS created, r.periodOfReport AS por,
                  collect(e.content) AS texts
           ORDER BY por LIMIT 3""",
        tk=tk, lo=lo, hi=hi))
    return [{'source_id': x['acc'], 'source_type': '8k', 'event_time': x['created'], 'xbrls': [],
             'texts': [c for c in x['texts'] if c]} for x in rows if x['acc']]


def resolve_one(it, src, allow_t1):
    """Resolve this KPI's value inside ONE source. Returns (record|None, candidate_snippet_strings).
    record present => gate-clean verbatim quote in THIS source. None + snippets => hand to LLM tier."""
    name, val, fmt = it['kpi'], it['value'], it['fmt']
    per = it['period']
    base = {'source_id': src['source_id'], 'source_type': src['source_type'],
            'event_time': src.get('event_time'), 'ticker': it['ticker'],
            'raw_label': name, 'value': val, 'fmt': fmt, 'is_currency': it['is_currency'],
            'period_end': per, 'form': it['form'], 'cadence': it.get('section'),
            'category': it.get('category', '')}
    t1 = L.tier1(src['xbrls'], name, val, per) if (allow_t1 and src['xbrls'] and fmt != '%') else None
    strict, snips = L.scan_text(src['texts'], name, val, fmt)
    if t1 and not strict:                        # XBRL matched but KPI wording absent by the value;
        strict = L.row_quote(src['texts'], L.member_tokens([t1['member']]), val, fmt)   # try filer's member wording
    xbrl = None
    if t1:
        xbrl = {'concept': t1['concept'], 'axis_members': t1['axis_members'],
                'period_start': t1['period_start'], 'period_end': t1['period_end'], 'ptype': t1['ptype']}
    if t1 and strict:
        rec = {**base, 'tier': 'T1-xbrl', 'member': t1['member'].split(':')[-1], 'concept': t1['concept'],
               'quote': strict, 'quote_source': 'section', 'period_evidence': (snips[0] if snips else strict),
               'xbrl': xbrl, 'xbrl_fact': t1['quote']}
    elif t1:
        rec = {**base, 'tier': 'T1-xbrl', 'member': t1['member'].split(':')[-1], 'concept': t1['concept'],
               'quote': t1['quote'], 'quote_source': 'xbrl_fact', 'period_evidence': '',
               'xbrl': xbrl, 'xbrl_fact': t1['quote']}
    elif strict:
        rec = {**base, 'tier': 'T2-label', 'quote': strict, 'quote_source': 'section',
               'period_evidence': (snips[0] if snips else strict)}
    else:
        return None, snips
    if L.value_ok(val, fmt, rec['quote']):       # deterministic belt+braces: number really in the quote
        return rec, snips
    return None, snips                            # gate-fail -> residual candidates


def process_cp(items, filing, prs):
    """Route each KPI of one company-period through every source event. Returns (resolved, residual, abstain).
    resolved may hold TWO records for one KPI (filing + PR) -- separate source events, by design."""
    resolved, residual, abstain = [], [], []
    searched = [filing['source_type']] + [p['source_type'] for p in prs]
    for it in items:
        name, val, fmt = it['kpi'], it['value'], it['fmt']
        base = {'ticker': it['ticker'], 'raw_label': name, 'value': val, 'fmt': fmt, 'period_end': it['period'],
                'form': it['form'], 'cadence': it.get('section'), 'sources_searched': searched}
        if val is None:
            continue
        if L.is_derived(name):                   # fiscal.ai-computed (% Chg / Common Size) -> terminal SKIP
            abstain.append({**base, 'status': 'skip', 'reason': 'derived_metric'}); continue
        if fmt in (None, 'number') and abs(float(val)) <= 1000:
            abstain.append({**base, 'status': 'skip', 'reason': 'plug'}); continue
        emitted = False; cands = []
        for src, allow_t1 in [(filing, True)] + [(p, False) for p in prs]:
            rec, snips = resolve_one(it, src, allow_t1)
            if rec:
                resolved.append(rec); emitted = True
            cands += [{'text': s, 'src': src['source_id'], 'src_type': src['source_type']} for s in snips]
        if emitted:
            continue
        if cands:
            residual.append({**base, 'candidates': cands}); continue
        abstain.append({**base, 'status': 'value_absent', 'reason': 'value_absent'})
    return resolved, residual, abstain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', type=int)
    ap.add_argument('--nparts', type=int, default=4)
    ap.add_argument('--tickers', help='comma list; overrides --part (small free run)')
    ap.add_argument('--tag', help='output subdir name (default part<N>)')
    a = ap.parse_args()

    work = [json.loads(l) for l in open(f'{OUT}/worklist.jsonl')]
    if a.tickers:
        keep = set(a.tickers.split(',')); work = [w for w in work if w['ticker'] in keep]
        tag = a.tag or 'smoke'
    else:
        assert a.part, 'need --part or --tickers'
        tickers = sorted({w['ticker'] for w in work})
        chunk = (len(tickers) + a.nparts - 1) // a.nparts
        part_tickers = set(tickers[(a.part-1)*chunk: a.part*chunk])
        work = [w for w in work if w['ticker'] in part_tickers]
        tag = a.tag or f'part{a.part}'
    cps = collections.defaultdict(list)
    for w in work:
        cps[(w['ticker'], w['form'], w['period'])].append(w)
    print(f"[{tag}] {len(work)} instances, {len(cps)} company-periods")

    load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    pdir = f'{OUT}/{tag}'; os.makedirs(pdir, exist_ok=True)
    R = open(f'{pdir}/code_resolved.jsonl', 'w'); RES = open(f'{pdir}/residual.jsonl', 'w')
    AB = open(f'{pdir}/abstain.jsonl', 'w')
    nR = nRes = nAb = 0
    stats = collections.Counter()
    with drv.session() as s:
        for i, ((tk, form, period), items) in enumerate(sorted(cps.items())):
            filing = fetch_filing(s, tk, form, period)
            if filing is None:                   # named filing not in Neo4j yet -> whole cp PARKs downstream
                for it in items:
                    AB.write(json.dumps({**it, 'status': 'park', 'reason': 'corpus_missing',
                                         'sources_searched': []}) + '\n'); nAb += 1
                stats['cp_no_filing'] += 1
                continue
            prs = fetch_press_releases(s, tk, period)
            resolved, residual, abstain = process_cp(items, filing, prs)
            for r in resolved: R.write(json.dumps(r) + '\n'); nR += 1
            for r in residual: RES.write(json.dumps(r) + '\n'); nRes += 1
            for r in abstain: AB.write(json.dumps(r) + '\n'); nAb += 1
            stats[('tier', 'T1')] += sum(1 for r in resolved if r['tier'] == 'T1-xbrl')
            stats[('tier', 'T2')] += sum(1 for r in resolved if r['tier'] == 'T2-label')
            stats['pr_records'] += sum(1 for r in resolved if r['source_type'] == '8k')
            if (i+1) % 100 == 0:
                print(f"  {i+1}/{len(cps)} cps  resolved={nR} residual={nRes} abstain={nAb}")
    drv.close(); R.close(); RES.close(); AB.close()
    tot = nR + nRes + nAb
    summary = {'tag': tag, 'records_resolved': nR, 'residual': nRes, 'abstain': nAb,
               'company_periods': len(cps), 'T1_xbrl': stats[('tier', 'T1')], 'T2_label': stats[('tier', 'T2')],
               'pr_records': stats['pr_records'], 'cp_no_filing': stats['cp_no_filing']}
    json.dump(summary, open(f'{pdir}/code_summary.json', 'w'), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
