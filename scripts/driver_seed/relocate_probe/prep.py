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
import os, re, json, glob, gzip, argparse, sys, collections, math
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
    """KPI label tokens: regex only, no domain list. KEEP metric-kind words (profit/revenue/margin)
    AND short identity tokens (AI, FX, R&D, US, 5G, 737) via [A-Za-z0-9&]{2,} after dropping dots.
    So 'Operating Profit' != 'Net Sales' and 'AI Backlog' no longer collapses to 'Backlog'."""
    return [t for t in re.findall(r"[A-Za-z0-9&]{2,}", name.replace('.', '')) if t.lower() not in KPI_STOP]


def caption_of(pretext):
    """The table's nearest heading, or '' (honest zero-signal). Trailing clause before the table, kept
    ONLY if heading-like: starts uppercase, <=90 chars, no long digit-run or table marker. Structural
    test, NO keyword list — an empty caption is better than a junk one (both locate + prompts tolerate '')."""
    p = L._tidy(pretext)
    frag = re.split(r'(?<=[.;:])\s+', p)[-1] if p else ''
    if frag[:1].isupper() and len(frag) <= 90 and not re.search(r'\d{3,}|##TABLE', frag):
        return frag
    return ''


def unit_dim(fmt, is_currency):
    """Unit DIMENSION from the SOURCE's own fields only — no scale, no keyword vocabulary. fiscal.ai
    fmt gives percent; is_currency gives currency; everything else is a count. Stored once → source-agnostic."""
    if fmt == '%':
        return 'percent'
    return 'currency' if is_currency else 'count'


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


def measurement_of(kpi, lock_quote):
    """measurement FLAVOR for the address: 'adjusted' when the driver name or the locked row itself
    says adjusted/non-GAAP; '' = unknown. Oracle-built (XBRL) locks pass 'gaap' explicitly."""
    t = f"{kpi} {lock_quote}".lower()
    return 'adjusted' if re.search(r'\badjusted\b|non-?gaap', t) else ''


def build_address(kpi, fmt, is_currency, lock_texts, lock_quote, lock_value, measurement=None):
    """GENERAL address. Home table = the one that CONTAINS the certified lock_quote (deterministic —
    no dependence on Neo4j section order); fall back to a value-form hunt only if not found. Unit is a
    source-field dimension, not text-sniffed. 'kind' field dropped (was written, never read)."""
    kt = kpi_tokens(kpi)
    lt = [t.lower() for t in kt]
    dim = unit_dim(fmt, is_currency)
    meas = measurement_of(kpi, lock_quote) if measurement is None else measurement
    lq = L._tidy(lock_quote)
    tables = split_tables(lock_texts)
    for cap, block in tables:                                 # deterministic: lock_quote containment
        if lq and lq in block:
            sib = sorted(label_terms(block) - set(lt))[:40]
            return {'label': kt, 'caption': cap[:120], 'siblings': sib, 'unit': dim, 'lock_row': lock_quote, 'measurement': meas}
    forms = L._tableforms(lock_value, fmt)                     # fallback: value-form hunt
    for cap, block in tables:
        if any(L.bounded_hit(block, f) for f in forms) and (not lt or any(t in block.lower() for t in lt)):
            sib = sorted(label_terms(block) - set(lt))[:40]
            return {'label': kt, 'caption': cap[:120], 'siblings': sib, 'unit': dim, 'lock_row': lock_quote, 'measurement': meas}
    return {'label': kt, 'caption': '', 'siblings': sorted(label_terms(lock_quote))[:40],
            'unit': dim, 'lock_row': lock_quote, 'measurement': meas}


_SPLIT_STOP = {'a', 'an', 'and', 'as', 'at', 'by', 'for', 'from', 'in', 'into', 'is', 'of', 'on',
               'or', 'the', 'to', 'with', 'axis', 'member', 'members', 'table', 'page', 'note', 'notes',
               'ended', 'ending', 'month', 'months', 'quarter', 'quarterly', 'year', 'years', 'fiscal',
               'three', 'six', 'nine', 'twelve', 'million', 'millions', 'thousand', 'thousands'}


def _words(text):
    text = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(text or ''))
    text = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)
    return [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9&'-]*", text)
            if len(w) >= 2 and w.lower() not in _SPLIT_STOP]


def _phrases(text, max_n=4):
    ws = _words(text); out = set()
    for n in range(2, max_n + 1):
        for i in range(len(ws) - n + 1):
            p = ' '.join(ws[i:i + n])
            if len(p) >= 8:
                out.add(p)
    return out


def locate(target_texts, addr, keep=12, span=3600, stride=2200):
    """Phase 2 v2 (ported from the verified independent-audit retriever, 2026-07-13): OVERLAPPING
    uniform chunks over the WHOLE source guarantee the value's neighbourhood is always in some chunk
    (the old label-window design could miss entirely — true-multi-axis holdout 87% -> 100% here).
    Rank by the LOCK QUOTE's own printed words (IDF-weighted) + exact lock phrases + per-axis facet
    groups (when the address carries identity axes) + label words. No force-include needed. The
    reader + gates decide WHICH metric, so broad retrieval only moves recall, never precision."""
    units, seen = [], set()
    for t in target_texts:
        t = str(t or '')
        for s in range(0, len(t), stride):
            block = L._tidy(t[s:s + span])
            if block and re.search(r'\d', block) and block[:200] not in seen:
                seen.add(block[:200])
                units.append({'text': block, 'words': set(_words(block)), 'low': block.lower()})
            if s + span >= len(t):
                break
    facet_groups, facet_phr = [], []
    for ax in (addr.get('identity') or {}).get('axes') or []:      # multi-axis: each axis = own group
        if not ax.get('structural'):
            ws = _words(ax.get('member_label') or ax.get('member_qname'))
            if ws:
                facet_groups.append(set(ws)); facet_phr.append(' '.join(ws))
    metric = set(_words(' '.join(addr.get('label') or [])))
    lock = addr.get('lock_row') or ''
    lock_words, lock_phr = set(_words(lock)), _phrases(lock)
    df = collections.Counter()
    for u in units:
        df.update(u['words'] & lock_words)
    n = max(len(units), 1)
    scored = []
    for u in units:
        shared = lock_words & u['words']
        overlap = sum(math.log((n + 1) / (df[w] + 1)) + 1 for w in shared) / math.sqrt(max(len(u['words']), 1))
        fs = [len(g & u['words']) / len(g) for g in facet_groups]
        score = (10 * sum(s == 1 for s in fs) + 4 * sum(fs)
                 + 6 * sum(p in u['low'] for p in facet_phr)
                 + min(sum(p in u['low'] for p in lock_phr), 8)
                 + 3 * (len(metric & u['words']) / max(len(metric), 1)) + overlap)
        if score > 0:
            scored.append((score, -len(u['text']), u['text']))
    scored.sort(key=lambda c: c[:2], reverse=True)
    return [{'caption': '', 'text': c[2]} for c in scored[:keep]]


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
        addr = build_address(sd['kpi'], sd['fmt'], sd.get('is_currency', 1), txa, sd['quote'], periods[pa])
        cands = locate(tx, addr)
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


def drop_ambiguous(truth_path, bdir):
    """TEST-HONESTY guard: if one (ticker, name, period) maps to >1 distinct truth value, the name is
    under-specified — no reader could resolve it (production names come from the user). Drop those pairs."""
    import collections
    rows = [json.loads(l) for l in open(truth_path)]
    vals = collections.defaultdict(set)
    for t in rows:
        vals[(t['ticker'], t['kpi'], t['period_target'])].add(t['value_target'])
    keep = [t for t in rows if len(vals[(t['ticker'], t['kpi'], t['period_target'])]) == 1]
    for t in rows:
        if t not in keep:
            p = f"{bdir}/batch_{t['id']}.json"
            os.path.exists(p) and os.remove(p)
    open(truth_path, 'w').write(''.join(json.dumps(t) + '\n' for t in keep))
    return len(keep), len(rows) - len(keep)
