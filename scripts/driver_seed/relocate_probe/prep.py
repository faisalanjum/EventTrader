#!/usr/bin/env python3
"""ISOLATED probe (v2 — richer, generalizable disclosure address).

Honest leave-one-out test that a stored disclosure ADDRESS lets us blind-refetch a TEXT-only
driver's value in a DIFFERENT period's filing at ~100% precision. The address is built by GENERAL
mechanical rules (nearest table caption, the other row-labels in the table, unit) — no per-company
or per-domain tuning — so it must work on unseen filings. We prove that with --set holdout: a fresh
slice of companies never inspected while designing the method.

    venv/bin/python scripts/driver_seed/relocate_probe/prep.py --set design  --n 20
    venv/bin/python scripts/driver_seed/relocate_probe/prep.py --set holdout --n 20   # unseen

Writes batches_<set>/batch_<i>.json (address + target candidates, NO target value) and truth_<set>.jsonl.
"""
import os, re, json, glob, gzip, argparse, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import link_lib as L
import run_code_tier as RC

RUN = 'data/fiscal_ai_segments/runs/2026-07-10/raw'
SEED = 'data/driver_catalog_seed/part1/seed_records.jsonl'
HERE = os.path.dirname(__file__)
GRAN = {'10-K': 'Annual', '10-Q': 'Quarterly'}
# generic structural / time words that are NOT identifying labels (domain-neutral)
STRUCT = {'table', 'start', 'end', 'total', 'net', 'sales', 'revenue', 'revenues', 'the', 'and',
          'for', 'year', 'years', 'ended', 'month', 'months', 'three', 'six', 'nine', 'twelve',
          'december', 'march', 'june', 'september', 'january', 'february', 'april', 'may', 'july',
          'august', 'october', 'november', 'fiscal', 'quarter', 'period', 'change', 'percent',
          'increase', 'decrease', 'million', 'millions', 'thousand', 'thousands', 'inc', 'corp'}
# BUG-A FIX: for relocation the metric KIND is the discriminator (profit vs sales vs margin), so the
# label must KEEP those words — unlike link_lib._toks, which strips them for the value-first pipeline.
KPI_STOP = {'the', 'and', 'of', 'by', 'for', 'from', 'inc', 'corp', 'company', 'to', 'a', 'an'}


def kpi_tokens(name):
    """KPI label tokens that KEEP metric-kind words (profit/revenue/income/margin/...). So
    'Operating Profit' and 'Net Sales' get DIFFERENT labels -> the locator ranks the right table and
    the reader can tell the metric KIND apart, not just the segment."""
    return [t for t in re.findall(r"[A-Za-z]{3,}", name) if t.lower() not in KPI_STOP]


def caption_of(pretext):
    """BUG-B FIX: the table's nearest heading, not a whole paragraph. Take only the trailing clause
    before the table (after the last sentence break), capped — 'Segment Operating Profit' not a
    200-char MD&A sentence."""
    p = L._tidy(pretext)
    frag = re.split(r'(?<=[.;:])\s+', p)[-1] if p else ''
    return frag[-160:]


def raw_path(ticker):
    hits = glob.glob(f'{RUN}/*-{ticker}_quarterly.json.gz')
    return hits[0] if hits else None


def free_periods(raw, category, metric_id, gran):
    try:
        cat = raw['pageProps']['segmentsData']['data'][gran][category]
    except KeyError:
        return {}
    free = {c['id'] for c in cat.get('columns', [])
            if isinstance(c, dict) and c.get('id', '').count('-') == 2
            and not c.get('paywalledTiers', {}).get('Free')}
    for row in cat.get('rows', []):
        m = row.get('metric')
        if isinstance(m, dict) and m.get('metricId') == metric_id:
            out = {}
            for d in free:
                cell = row.get(d)
                v = cell.get('value') if isinstance(cell, dict) else cell
                if v is not None and v != '':
                    out[d] = v
            return out
    return {}


def label_terms(s):
    return {w.lower() for w in re.findall(r"[A-Za-z]{3,}", s)} - STRUCT


def unit_of(fmt, text):
    if fmt == '%':
        return 'percent'
    low = text.lower()
    if 'thousand' in low:
        return '$ thousands' if '$' in text else 'thousands'
    if 'million' in low:
        return '$ millions' if '$' in text else 'millions'
    return '$' if '$' in text else 'count/number'


def split_tables(texts):
    """(caption, block) for every ##TABLE_START..##TABLE_END in the corpus. Caption = nearest
    heading text before the table (general — the disclosure's own title)."""
    out = []
    for t in texts:
        for m in re.finditer('##TABLE_START', t):
            s = m.start(); e = t.find('##TABLE_END', s)
            if e < 0:
                continue
            out.append((caption_of(t[max(0, s-300):s]), L._tidy(t[s:e + len('##TABLE_END')])))
    return out


def prose_windows(texts, kpi, keep):
    """label-anchored prose windows (fallback for metrics stated in sentences, not tables)."""
    toks = [t.lower() for t in L._toks(kpi)]
    if not toks:
        return []
    anchor = max(toks, key=len)
    out = []
    for t in texts:
        low = t.lower()
        for m in re.finditer(re.escape(anchor), low):
            s = m.start()
            if '##TABLE_START' in t[max(0, s-400):s+400]:
                continue                                    # already covered by table split
            out.append({'caption': '', 'text': L._tidy(t[max(0, s-400):s+500])})
            if len(out) >= keep:
                return out
    return out


def build_address(kpi, fmt, lock_texts, lock_quote, lock_value):
    """GENERAL address of where/how this driver was disclosed in the lock period."""
    kt = kpi_tokens(kpi)                                     # keeps metric-kind words (BUG-A fix)
    lt = [t.lower() for t in kt]
    forms = L._tableforms(lock_value, fmt)
    for cap, block in split_tables(lock_texts):
        if any(L.bounded_hit(block, f) for f in forms) and (not lt or any(t in block.lower() for t in lt)):
            sib = sorted(label_terms(block) - set(lt))[:40]
            return {'kind': 'table', 'label': kt, 'caption': cap[:240],
                    'siblings': sib, 'unit': unit_of(fmt, cap + ' ' + block), 'lock_row': lock_quote}
    return {'kind': 'prose', 'label': kt, 'caption': '',
            'siblings': sorted(label_terms(lock_quote))[:40], 'unit': unit_of(fmt, lock_quote),
            'lock_row': lock_quote}


def locate(target_texts, addr, kpi, keep=6):
    """Find candidate disclosures in the TARGET filing by GENERAL structural match: overlap of the
    address's sibling row-labels + caption terms + the KPI's own label. Value is NOT used (unknown).

    FIX 1 (widen the net, UNIFORMLY for every metric — no per-company logic): hand the reader more
    snippets (keep=6), ALWAYS also include any table that literally contains the metric's WHOLE label
    (the strongest 'the metric is here' signal, even if its siblings drifted), plus prose windows.
    More snippets can't create a wrong answer — verify + the column gate still decide — so this only
    moves recall, never precision."""
    lt = [t.lower() for t in addr['label']]
    sib = set(addr['siblings']); capt = label_terms(addr['caption'])
    tables = split_tables(target_texts)
    scored = []
    for cap, block in tables:
        bt = label_terms(block)
        score = 2 * len(sib & bt) + 2 * len(capt & label_terms(cap)) + sum(1 for t in lt if t in block.lower())
        if score > 0:
            scored.append((score, len(block), cap[:240], block))
    scored.sort(key=lambda c: (-c[0], c[1]))                # label presence already lifts the score
    picked, seen = [], set()

    def add(cap, block):
        k = block[:80]
        if k not in seen:
            seen.add(k); picked.append({'caption': cap, 'text': block})

    for _, _, cap, block in scored[:keep]:                  # top-keep ranked tables (bounded)
        add(cap, block)
    for w in prose_windows(target_texts, kpi, 2):           # + sentences (prose-stated metrics)
        add(w['caption'], w['text'])
    return picked


def metric_type(sd):
    """Domain-neutral bucket from fiscal.ai's own category (for stratified coverage, not tuning)."""
    cat = sd.get('category', '') or ''
    if sd.get('fmt') == '%':
        return 'percent'
    if cat.endswith('geo'):
        return 'geography'
    if any(w in cat for w in ('EBITDA', 'Adjusted', 'Profit', 'Income', 'Margin')):
        return 'nongaap'
    if cat.endswith('non'):
        return 'operational'
    if cat.endswith('seg1') or 'Revenue' in cat:
        return 'segment'
    return 'other'


def build_pair(s, sd, raw_cache):
    """Turn one seed into a leave-one-out pair: address from the lock filing + candidates from a
    target period that has a REAL 10-K/10-Q (kills fiscal.ai LTM/MRQ stub columns). None if unusable."""
    tk = sd['ticker']; gran = GRAN.get(sd['form'])
    if not gran:
        return None
    if tk not in raw_cache:
        p = raw_path(tk)
        raw_cache[tk] = json.load(gzip.open(p)) if p else None
    raw = raw_cache[tk]
    if not raw:
        return None
    periods = free_periods(raw, sd.get('category', ''), sd['kpi'], gran)
    pa = sd['period']
    if pa not in periods:
        return None
    for pb in sorted([d for d in periods if d != pa], reverse=True):
        xb, txf, _ = RC.fetch_corpus(s, tk, sd['form'], pb)
        if not txf and not xb:
            continue                                     # no real filing for this period -> stub
        tx = txf + RC.fetch_press_release(s, tk, pb)
        _, txa, _ = RC.fetch_corpus(s, tk, sd['form'], pa)
        txa = txa + RC.fetch_press_release(s, tk, pa)
        addr = build_address(sd['kpi'], sd['fmt'], txa, sd['quote'], periods[pa])
        cands = locate(tx, addr, sd['kpi'])
        if not cands:
            continue
        return {'addr': addr, 'pb': pb, 'cands': cands, 'v_lock': periods[pa], 'v_target': periods[pb]}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--set', choices=['design', 'holdout', 'validation'], default='design')
    ap.add_argument('--n', type=int, default=20)
    ap.add_argument('--per-ticker', type=int, default=3)     # validation: allow a few metrics/company
    a = ap.parse_args()

    seeds = [json.loads(l) for l in open(SEED)]
    text_only = [s for s in seeds if s.get('tier') in ('T2-label', 'T3-llm') and s.get('quote')]
    seen_k, uniq = set(), []                                 # dedup (ticker, kpi)
    for sd in text_only:
        k = (sd['ticker'], sd['kpi'])
        if k not in seen_k:
            seen_k.add(k); uniq.append(sd)
    text_only = uniq

    if a.set == 'validation':                               # round-robin across (form, metric type)
        buckets = collections.defaultdict(list)
        for sd in text_only:
            buckets[(sd['form'], metric_type(sd))].append(sd)
        order, pools, idx = [], [buckets[k] for k in sorted(buckets)], None
        idx = [0] * len(pools)
        while len(order) < len(text_only):
            moved = False
            for j, pool in enumerate(pools):
                if idx[j] < len(pool):
                    order.append(pool[idx[j]]); idx[j] += 1; moved = True
            if not moved:
                break
        offset, cap = 0, a.per_ticker
    else:
        order, offset, cap = text_only, (0 if a.set == 'design' else a.n), 1

    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))

    bdir = f'{HERE}/batches_{a.set}'
    os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    truth = open(f'{HERE}/truth_{a.set}.jsonl', 'w')

    raw_cache = {}; per_tk = collections.Counter(); made = rank = 0
    rank = -1; tally = collections.Counter()
    with drv.session() as s:
        for sd in order:
            if made >= a.n:
                break
            tk = sd['ticker']
            if per_tk[tk] >= cap:
                continue
            res = build_pair(s, sd, raw_cache)
            if not res:
                continue
            if a.set != 'validation':                       # design/holdout: slice viable tickers
                rank += 1; per_tk[tk] += 1
                if rank < offset or rank >= offset + a.n:
                    continue
            typ = metric_type(sd)
            bid = made
            batch = {'id': bid, 'ticker': tk, 'kpi': sd['kpi'], 'fmt': sd['fmt'],
                     'category': sd.get('category', ''), 'form': sd['form'], 'type': typ,
                     'period_type': 'annual' if sd['form'] == '10-K' else 'quarterly',
                     'period_lock': sd['period'], 'period_target': res['pb'],
                     'address': res['addr'], 'candidates': res['cands']}
            json.dump(batch, open(f'{bdir}/batch_{bid}.json', 'w'))
            truth.write(json.dumps({'id': bid, 'ticker': tk, 'kpi': sd['kpi'], 'fmt': sd['fmt'],
                                    'type': typ, 'period_target': res['pb'],
                                    'value_target': res['v_target'], 'value_lock': res['v_lock']}) + '\n')
            if a.set == 'validation':
                per_tk[tk] += 1
            made += 1; tally[typ] += 1
            if made % 20 == 0:
                print(f"  built {made}/{a.n}…  {dict(tally)}", flush=True)
    drv.close(); truth.close()
    print(f"\n[{a.set}] prepared {made} pairs;  by type: {dict(tally)}")


if __name__ == '__main__':
    main()
