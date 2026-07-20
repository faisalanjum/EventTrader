#!/usr/bin/env python3
"""locate() — the ONE reusable, channel-neutral locator entry. Two modes, dispatched by input:

  value KNOWN   (req has 'value')  -> find WHERE that number is written  -> {'hit': {...}|None, 'snips': [...]}
  value UNKNOWN (no 'value')       -> find the value from a fingerprint  -> {'value': int|None}

Both reuse the CERTIFIED engines unchanged (link_lib.tier1 ladder + xbrl_lane.resolve); this module only
routes and shapes. Channel-neutral: it takes raw source material (xbrls/texts) + a plain request dict, never
a fiscal.ai record shape. FETCH-only — it returns the quote + RAW xbrl (axis+member) pairs and NEVER names a
driver, classifies a slice kind, or stamps fact_type (that is the shared core's job).

    venv/bin/python -m pytest scripts/driver_seed/test_locate.py -q
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import link_lib as L


def locate(req):
    """Dispatch by presence of a stated value. See module docstring for the two return shapes."""
    if req.get('value') is not None:
        return locate_by_value(req)
    return locate_by_fingerprint(req)


def _exact_cell(req, t1):
    """TOP rung for an XBRL-matched item: anchor the known fact to its PRINTED CELL and quote the filer's
    own row verbatim. Returns (row_quote, column_header) or None (abstain -> next rung).
    Needs the filing's inline HTML (10-K/10-Q carry ix: tags); the caller supplies the doc url."""
    url, acc = req.get('doc_url'), req.get('source_id')
    if not (url and acc):
        return None
    sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
    import lock_cell
    path = lock_cell.fetch_inline_html(url, acc)
    if not path:
        return None
    sw = lock_cell.exact_cell(path, t1['concept'], t1['period_start'], t1['period_end'],
                              [tuple(p) for p in (t1.get('axis_members') or [])])
    if not sw or not sw.get('row'):
        return None
    cells = [str(c).strip() for c in (sw.get('row_cells') or []) if str(c).strip()]
    quote = ' '.join(cells)
    # the printed row can carry SEVERAL years; the column header says which one is ours (ChannelContract
    # §3 "adjacent period wording (column header ...)"). The XBRL context pins the period authoritatively.
    return (quote, sw.get('column') or '') if quote else None


def _sign_visible(val, fmt, quote):
    """does the quote PRINT this value's negative sign — '(123)' or '-123'? notation only, never words."""
    forms = {f for f in L.value_forms(val, fmt or 'number') if len(f) >= 2}
    return any(L.printed_negative(quote, f) for f in forms if L.bounded_hit(quote, f))


def locate_by_value(req):
    """value-known. LADDER (each rung falls to the next; nothing is invented):
        1. exact-cell  — the filer's own printed row, for an XBRL-matched item (needs doc_url)
        2. text-strict — the strict same-row label match
        3. no hit      — hand the snippets to the LLM tier. There is NO fabricated-quote rung.
    req: {xbrls, texts, name, value, fmt, period, allow_xbrl?, doc_url?, source_id?}."""
    xbrls = req.get('xbrls') or []
    texts = req.get('texts') or []
    name, val, fmt, per = req['name'], req['value'], req.get('fmt'), req.get('period')
    try:                                     # round-13/14 (both live-reproduced): 'N/A'/'-331x'
        if not L._finite(L.XN.dec(str(val))):    # crashed with ValueError; '1e309' is Decimal-
            raise L.XN.ExactError('non-finite')  # finite but float-INFINITE. ONE shared finite
    except (L.XN.ExactError, OverflowError, ValueError):     # predicate (corrective 3); the
                                                             # caller's abstain path unchanged.
        return {'hit': None, 'snips': []}
    allow_t1 = req.get('allow_xbrl', True)
    t1 = (L.tier1(xbrls, name, val, per, is_currency=req.get('is_currency'))
          if (allow_t1 and xbrls and fmt != '%') else None)
    # scale_gate (round-13): a bare SCALED print ('1,200' for 1.2B) binds only with scale evidence
    # (section marker / immediate tail / full-magnitude print). Opt-in here — certified benchmark
    # preps keep byte-identical legacy behavior.
    strict, snips, strict_ctx = L.scan_text(texts, name, val, fmt, scale_gate=True,
                                            with_context=True)   # Rule 2: ONE call, same occurrence
    if t1 and not strict:                    # XBRL matched but KPI wording absent by the value;
        strict, strict_ctx = L.row_quote(texts, L.member_tokens([t1['member']]), val, fmt,
                                         scale_gate=True, with_context=True)
    xbrl = None
    if t1:
        xbrl = {'concept': t1['concept'], 'axis_members': t1['axis_members'],
                'period_start': t1['period_start'], 'period_end': t1['period_end'], 'ptype': t1['ptype']}
    base_t1 = {'tier': 'T1-xbrl', 'member': (t1['member'].split(':')[-1] if t1 else None),
               'concept': (t1['concept'] if t1 else None), 'xbrl': xbrl,
               'xbrl_fact': (t1['quote'] if t1 else None)}
    hit = None
    if t1:                                                    # rung 1 — the printed cell ANCHORS;
        cell = _exact_cell(req, t1)                           # the emitted quote must be a CORPUS
        if cell:                                              # slice (v5.5 §3); cells = audit data
            cq = strict or L.row_quote(texts, L.member_tokens([t1['member']]), val, fmt,
                                       scale_gate=True)
            if cq and L.value_ok(val, fmt, cq):
                hit = {**base_t1, 'quote': cq, 'quote_source': 'exact_cell',
                       'period_evidence': cell[1], 'cell_evidence': cell[0]}
    if hit is None and strict:                                # rung 2 — strict text label
        if t1:
            hit = {**base_t1, 'quote': strict, 'quote_source': 'section',
                   'period_evidence': (strict_ctx or strict)}
        else:
            hit = {'tier': 'T2-label', 'quote': strict, 'quote_source': 'section',
                   'period_evidence': (strict_ctx or strict)}
    if hit is None:
        return {'hit': None, 'snips': snips}                  # rung 3 — the LLM tier
    if not L.value_ok(val, fmt, hit['quote']):   # deterministic belt+braces: the number really is in the quote
        return {'hit': None, 'snips': snips}
    # TEXT-ONLY sign routing: with no XBRL the sign is unproven, and if the print does not SHOW it the minus
    # lives in a word ("operating loss of 331") — a MEANING call. Never guess it here; hand it to the tier
    # that reads meaning. (T1 needs no check: tier1 matched the SIGNED value, link_lib.py:318.)
    if t1 is None and float(val) < 0 and not _sign_visible(val, fmt, hit['quote']):
        return {'hit': None, 'snips': snips}
    return {'hit': hit, 'snips': snips}


def locate_by_fingerprint(req):
    """value-unknown via the thin adapter over the neutral matcher. req: {xbrls, concept,
    pairs?, members?, period_start, period_end, unit_ref?, expected_unit?}. `pairs` (the FULL
    (axis,member) address) is THE identity and is FORWARDED when present; a dimensioned
    members-only req abstains downstream (an axis is never inferred)."""
    # Lazy import kept for import-order simplicity until R3; the old cycle
    # (locate -> xbrl_lane -> oracle -> run_code_tier -> locate) DIED in WP2 when xbrl_lane
    # dropped its oracle import and became a thin adapter over the neutral locator.
    sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
    import xbrl_lane
    # round-13: unit identity FORWARDED (it was dropped — a shares fact could satisfy a money request)
    pairs = req.get('pairs')
    return {'value': xbrl_lane.resolve(req.get('xbrls') or [], req['concept'],
                                       None if pairs is not None else req.get('members'),
                                       req['period_start'], req['period_end'],
                                       unit_ref=req.get('unit_ref'),
                                       expected_unit=req.get('expected_unit'),
                                       pairs=pairs)}


if __name__ == '__main__':
    import subprocess
    subprocess.run([sys.executable, '-m', 'pytest', os.path.join(HERE, 'test_locate.py'), '-q'])
