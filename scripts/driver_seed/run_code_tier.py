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
import os, re, json, argparse, collections, sys, hashlib, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'earnings'))
import quarter_identity as QI          # LIVE lane + trust gate (AUTO_OK); labels NOT used here (round-15)
from get_quarterly_filings import match_8k_to_periodic   # HISTORICAL lane: THE shared structured
                                                          # matcher (owner rule: historical pairing =
                                                          # get_quarterly_filings; live = quarter_identity)
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'driver', 'relocation'))
import exact_numbers as XN            # Decimal-exact number law (round-13: malformed values PARK)
import fiscal_ai_rules as FA          # fiscal.ai channel-specific rules (is_derived / plug) — not shared core
import locate                          # the shared, channel-neutral two-mode locator (value-known lane here)

OUT = 'data/driver_catalog_seed'
FORMMAP = {'10-K': '10k', '10-Q': '10q', '8-K': '8k'}


def load_env_neo4j():
    for line in open('.env'):
        m = re.match(r'\s*(NEO4J_[A-Z_]+)=(.*)', line)
        if m:
            os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


# --- legacy fetchers (relocate_probe pipeline: prep/grade/oracle/exam depend on these exact signatures) ---
def fetch_press_release(session, tk, period):
    """LEGACY BENCHMARK-CORPUS FETCHER — frozen semantics (5-75-day window, EX-99 exhibits).
    Consumed ONLY by the certified relocation/grading pipelines (grade.py, prep*.py,
    recall_report.py) whose FROZEN benchmark sets were built with exactly this corpus recipe —
    changing it would silently re-define the certified floors. The fiscal.ai HARVEST path never
    uses this: it uses fetch_earnings_8ks (the safe, quarter-identity-gated selector) below.
    (WP1 lesson: this function was deleted with 10 live consumers — restored verbatim.)"""
    from datetime import date, timedelta
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


def _8k_gate(info, match_acc, lag_valid, target_acc):
    """PURE round-15 gate (Option D): accept iff the resolver TRUSTS the 8-K (AUTO_OK — the only
    thing quarter_identity contributes here; labels and calculated dates are IGNORED, year-name
    conventions poisoned every identity-based join) AND the existing matcher's returned periodic
    accession EXACTLY equals the target AND the filing lag was valid.
    Matched HERE but lag-invalid (late supplements, PHR class) or unmatchable -> 'uncertain'
    (park, counted — never silently complete). Matched elsewhere -> 'other_period'."""
    if (info or {}).get('safety_action') != 'AUTO_OK':
        return 'uncertain'
    if match_acc is None:
        return 'uncertain'
    if match_acc != target_acc:
        return 'other_period'
    return 'accept' if lag_valid else 'uncertain'


def dedupe_rows(rows):
    """Collapse byte-identical raw rows (fiscal.ai repeats e.g. BX 'Total Distributable Earnings'
    under two segment groupings — 18 groups / 31 extra occurrences in the full sheet). Identical
    rows are ONE fact; _iid hashes the whole row, so duplicates share one id by construction.
    Returns (unique_rows_in_order, dropped_count)."""
    seen, out, dropped = set(), [], 0
    for r in rows:
        k = json.dumps(r, sort_keys=True, default=str)
        if k in seen:
            dropped += 1
            continue
        seen.add(k)
        out.append(r)
    return out, dropped


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
    """The named filing as ONE source event: {source_id, source_type, event_time, doc_url, xbrls, texts}.
    doc_url = the inline-XBRL document, so the locator's exact-cell rung can quote the PRINTED row."""
    rows = list(session.run(
        """MATCH (r:Report {formType:$form})-[:PRIMARY_FILER]->(c:Company {ticker:$tk})
           WHERE r.periodOfReport STARTS WITH $period
           OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent)
           OPTIONAL MATCH (r)-[:HAS_SECTION]->(x:ExtractedSectionContent)
           RETURN r.accessionNo AS acc, r.created AS created, r.primaryDocumentUrl AS doc_url,
                  collect(DISTINCT f.value)   AS xbrls,
                  collect(DISTINCT x.content) AS texts""",
        form=form, tk=tk, period=period))
    if not rows or not rows[0]['acc']:
        return None
    r = rows[0]
    return {'source_id': r['acc'], 'source_type': FORMMAP.get(form, form), 'event_time': r['created'],
            'doc_url': r['doc_url'],
            'xbrls': [x for x in r['xbrls'] if x], 'texts': [x for x in r['texts'] if x]}


def _corpus_missing_row(it):
    """A raw row whose named filing is absent from the graph — PARKED with its item_id (round-12:
    EVERY raw row yields an id-carrying outcome; corpus_missing was the one un-id'd path)."""
    return {**it, 'item_id': _iid(it), 'status': 'park', 'reason': 'corpus_missing',
            'sources_searched': []}


def fetch_earnings_8ks(session, tk, target_acc):
    """Safe 8-K selection (WP1 Step 3 — replaces the 5-75-day window guess and the EX-99-only
    filter). Round-15, OWNER RULE: historical 8-K pairing = get_quarterly_filings (THE shared
    structured matcher — real period dates + filing-time checks, imported never copied); live
    prediction = quarter_identity, which here contributes ONLY its AUTO_OK trust verdict (labels
    and calculated dates ignored — year-name conventions poisoned every identity join). Accept an
    8-K iff its matched periodic accession EXACTLY equals the target. For every ACCEPTED accession
    fetch + DEDUPLICATE all stored text (sections + exhibits + filing text).
    require_daily_stock=False (documented deviation from the presentation tool): pairing is
    independent of returns availability; the harvest must see EVERY 2.02 8-K.
    Returns (events, uncertain_count, audit): uncertain_count > 0 means the target's expected
    source set is INCOMPLETE (abstains stay parked, never SKIP) — an unprovable 8-K counts ONLY
    when the matcher places it AT THIS TARGET (relevant=True: unlabelable true announcers and
    lag-invalid late supplements park HERE; other cycles' mysteries never leak in). audit = one
    {'acc','created','verdict','label','match','lag_valid','relevant'} row per enumerated 8-K,
    written to the run's sources_ledger (label informational only)."""
    events, audit, uncertain = [], [], 0
    for m in match_8k_to_periodic(session, tk, require_daily_stock=False):
        acc8 = m['accession_8k']
        if not acc8:
            continue
        cand, lag_ok = m['accession_10q'], m['lag_valid']
        try:
            info = QI.resolve_quarter_info(tk, acc8, session=session)
        except ValueError:                 # a 2.02 8-K the resolver still can't place -> fail closed
            relevant = cand == target_acc
            audit.append({'acc': acc8, 'created': str(m['filed_8k']), 'verdict': 'resolver_error',
                          'label': None, 'match': cand, 'lag_valid': lag_ok, 'relevant': relevant})
            uncertain += 1 if relevant else 0
            continue
        verdict = _8k_gate(info, cand, lag_ok, target_acc)
        relevant = verdict == 'uncertain' and cand == target_acc
        audit.append({'acc': acc8, 'created': str(m['filed_8k']), 'verdict': verdict,
                      'label': (info or {}).get('quarter_label'), 'match': cand,
                      'lag_valid': lag_ok, 'relevant': relevant})
        if verdict == 'uncertain':
            uncertain += 1 if relevant else 0
            continue
        if verdict != 'accept':
            continue
        txt = list(session.run(
            """MATCH (r:Report {accessionNo:$a})
               OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
               OPTIONAL MATCH (r)-[:HAS_SECTION]->(sx:ExtractedSectionContent)
               OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(f:FilingTextContent)
               RETURN collect(DISTINCT e.content) + collect(DISTINCT sx.content)
                      + collect(DISTINCT f.content) AS cs""", a=acc8))
        seen, contents = set(), []
        for c in (txt[0]['cs'] if txt else []):
            if c and c not in seen:
                seen.add(c); contents.append(c)
        if contents:
            events.append({'source_id': acc8, 'source_type': '8k',
                           'event_time': str(m['filed_8k']), 'xbrls': [], 'texts': contents})
    return events, uncertain, audit


def resolve_one(it, src, allow_t1):
    """Resolve this KPI's value inside ONE source. Returns (record|None, candidate_snippet_strings).
    record present => gate-clean verbatim quote in THIS source. None + snippets => hand to LLM tier."""
    name, val, fmt = it['kpi'], it['value'], it['fmt']
    per = it['period']
    base = {'item_id': _iid(it), 'source_id': src['source_id'], 'source_type': src['source_type'],
            'event_time': src.get('event_time'), 'ticker': it['ticker'],
            'raw_label': name, 'value': val, 'fmt': fmt, 'is_currency': it['is_currency'],
            'period_end': per, 'form': it['form'], 'cadence': it.get('section'),
            'category': it.get('category', '')}
    # value-known locate + the value_ok gate = the SHARED, channel-neutral core (locate.locate_by_value).
    r = locate.locate_by_value({'xbrls': src['xbrls'], 'texts': src['texts'], 'name': name,
                                'value': val, 'fmt': fmt, 'period': per, 'allow_xbrl': allow_t1,
                                'is_currency': it.get('is_currency'),
                                'doc_url': src.get('doc_url'), 'source_id': src['source_id']})
    hit, snips = r['hit'], r['snips']
    if hit is None:
        return None, snips                        # gate-fail or no locate -> residual candidates for the LLM tier
    return {**base, **hit}, snips                 # fiscal.ai record fields + the shared locator hit


def _iid(it):
    """ONE deterministic item id per DISTINCT RAW ROW, carried through resolved/residual/abstain.
    Hashes the WHOLE row: a 4-field key conflated 26 groups in the wp1 cohort (fiscal.ai repeats a
    KPI label across category variants with different values — reviewer catch, confirmed)."""
    return hashlib.sha1(json.dumps(it, sort_keys=True, default=str).encode()).hexdigest()[:12]


def process_cp(items, filing, prs, sources_incomplete=False):
    """Route each KPI of one company-period through every source event. Returns (resolved, residual, abstain).
    resolved may hold TWO records for one KPI (filing + PR) -- separate source events, by design.
    sources_incomplete: an expected 8-K could not be safely labeled (fail-closed drop) -> value-absent
    rows stay PARKED/retryable; a terminal SKIP is only legal against a clean, complete source set."""
    resolved, residual, abstain = [], [], []
    searched = [filing['source_type']] + [p['source_type'] for p in prs]
    for it in items:
        name, val, fmt = it['kpi'], it['value'], it['fmt']
        base = {'item_id': _iid(it), 'ticker': it['ticker'], 'raw_label': name, 'value': val,
                'fmt': fmt, 'period_end': it['period'],
                'form': it['form'], 'cadence': it.get('section'), 'sources_searched': searched}
        if val is None:
            continue
        if FA.is_derived(name):                  # fiscal.ai-computed (% Chg / Common Size) -> terminal SKIP
            abstain.append({**base, 'status': 'skip', 'reason': 'derived_metric'}); continue
        try:                                     # round-13/14: a malformed vendor number is a CHANNEL
            if not math.isfinite(float(XN.dec(str(val)))):   # DATA defect -> visible PARK, never a
                raise XN.ExactError('non-finite')            # crash and never a value_absent/terminal-
        except (XN.ExactError, OverflowError, ValueError):   # skip masquerade. float() catches the
            abstain.append({**base, 'status': 'park', 'reason': 'invalid_value'})   # 1e309 class:
            continue                             # Decimal-finite but float-infinite -> OverflowError
        # NO magnitude 'plug' skip: it dropped legit small facts (78 'Total X = 0' rows, stores=86, ACPU=670).
        # No value is pre-skipped by size; the locator decides, and no located proof -> value_absent (below).
        emitted = False; cands = []
        for src, allow_t1 in [(filing, True)] + [(p, False) for p in prs]:
            rec, snips = resolve_one(it, src, allow_t1)
            if rec:
                resolved.append(rec); emitted = True          # this source -> its own record
            elif snips:                                        # an UNRESOLVED source's evidence for the LLM tier
                cands += [{'text': s, 'src': src['source_id'], 'src_type': src['source_type']} for s in snips]
        if cands:
            # #2: keep a source's LLM candidates EVEN IF another source already resolved deterministically —
            # same value on two sources = two records (15 D.2), and the 8-K/PR carries earlier availability.
            # Fields match the LLM batcher's contract (prep_llm_batches: kpi/period/is_currency/filing_id) so
            # the residual -> LLM path is schema-compatible.
            residual.append({'item_id': _iid(it), 'ticker': it['ticker'], 'kpi': name, 'value': val,
                             'fmt': fmt, 'is_currency': it['is_currency'], 'period': it['period'],
                             'form': it['form'], 'filing_id': filing['source_id'],
                             'sources_searched': searched, 'candidates': cands})
        elif not emitted:
            abstain.append({**base, 'status': 'value_absent', 'reason': 'value_absent',
                            'sources_incomplete': bool(sources_incomplete)})
    return resolved, residual, abstain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', type=int)
    ap.add_argument('--nparts', type=int, default=4)
    ap.add_argument('--tickers', help='comma list; overrides --part (small free run)')
    ap.add_argument('--tag', help='output subdir name (default part<N>)')
    ap.add_argument('--worklist', default=f'{OUT}/worklist.jsonl',
                    help='input rows file (pass the COMMITTED slice for reproducible runs — '
                         'round-19: a clean checkout must not depend on the ignored full sheet)')
    a = ap.parse_args()

    work = [json.loads(l) for l in open(a.worklist)]
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
    work, dup_collapsed = dedupe_rows(work)      # round-13: identical rows are ONE fact, ONE id
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
    AB = open(f'{pdir}/abstain.jsonl', 'w'); SL = open(f'{pdir}/sources_ledger.jsonl', 'w')
    nR = nRes = nAb = 0
    stats = collections.Counter()
    with drv.session() as s:
        for i, ((tk, form, period), items) in enumerate(sorted(cps.items())):
            filing = fetch_filing(s, tk, form, period)
            if filing is None:                   # named filing not in Neo4j yet -> whole cp PARKs downstream
                for it in items:
                    AB.write(json.dumps(_corpus_missing_row(it)) + '\n'); nAb += 1
                stats['cp_no_filing'] += 1
                continue
            prs, uncertain_8ks, audit = fetch_earnings_8ks(s, tk, filing['source_id'])
            SL.write(json.dumps({'ticker': tk, 'form': form, 'period': period,
                                 'filing_acc': filing['source_id'],
                                 'eightk': audit}) + '\n')
            resolved, residual, abstain = process_cp(items, filing, prs,
                                                     sources_incomplete=uncertain_8ks > 0)
            for r in resolved: R.write(json.dumps(r) + '\n'); nR += 1
            for r in residual: RES.write(json.dumps(r) + '\n'); nRes += 1
            for r in abstain: AB.write(json.dumps(r) + '\n'); nAb += 1
            stats[('tier', 'T1')] += sum(1 for r in resolved if r['tier'] == 'T1-xbrl')
            stats[('tier', 'T2')] += sum(1 for r in resolved if r['tier'] == 'T2-label')
            stats['pr_records'] += sum(1 for r in resolved if r['source_type'] == '8k')
            if (i+1) % 100 == 0:
                print(f"  {i+1}/{len(cps)} cps  resolved={nR} residual={nRes} abstain={nAb}")
    drv.close(); R.close(); RES.close(); AB.close(); SL.close()
    tot = nR + nRes + nAb
    summary = {'tag': tag, 'records_resolved': nR, 'residual': nRes, 'abstain': nAb,
               'company_periods': len(cps), 'T1_xbrl': stats[('tier', 'T1')], 'T2_label': stats[('tier', 'T2')],
               'pr_records': stats['pr_records'], 'cp_no_filing': stats['cp_no_filing'],
               'duplicate_rows_collapsed': dup_collapsed}
    json.dump(summary, open(f'{pdir}/code_summary.json', 'w'), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
