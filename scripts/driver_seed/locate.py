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


def locate_by_value(req):
    """value-known: the certified link_lib ladder (XBRL tier1 -> strict text label) + the value_ok gate.
    req: {xbrls, texts, name, value, fmt, period, allow_xbrl?}. Returns {'hit': hit|None, 'snips': [...]}."""
    xbrls = req.get('xbrls') or []
    texts = req.get('texts') or []
    name, val, fmt, per = req['name'], req['value'], req.get('fmt'), req.get('period')
    allow_t1 = req.get('allow_xbrl', True)
    t1 = L.tier1(xbrls, name, val, per) if (allow_t1 and xbrls and fmt != '%') else None
    strict, snips = L.scan_text(texts, name, val, fmt)
    if t1 and not strict:                    # XBRL matched but KPI wording absent by the value;
        strict = L.row_quote(texts, L.member_tokens([t1['member']]), val, fmt)   # try the filer's member wording
    xbrl = None
    if t1:
        xbrl = {'concept': t1['concept'], 'axis_members': t1['axis_members'],
                'period_start': t1['period_start'], 'period_end': t1['period_end'], 'ptype': t1['ptype']}
    if t1 and strict:
        hit = {'tier': 'T1-xbrl', 'member': t1['member'].split(':')[-1], 'concept': t1['concept'],
               'quote': strict, 'quote_source': 'section', 'period_evidence': (snips[0] if snips else strict),
               'xbrl': xbrl, 'xbrl_fact': t1['quote']}
    elif t1:
        hit = {'tier': 'T1-xbrl', 'member': t1['member'].split(':')[-1], 'concept': t1['concept'],
               'quote': t1['quote'], 'quote_source': 'xbrl_fact', 'period_evidence': '',
               'xbrl': xbrl, 'xbrl_fact': t1['quote']}
    elif strict:
        hit = {'tier': 'T2-label', 'quote': strict, 'quote_source': 'section',
               'period_evidence': (snips[0] if snips else strict)}
    else:
        return {'hit': None, 'snips': snips}
    if L.value_ok(val, fmt, hit['quote']):   # deterministic belt+braces: the number really is in the quote
        return {'hit': hit, 'snips': snips}
    return {'hit': None, 'snips': snips}      # gate-fail -> no hit; snips still hand off to the LLM tier


def locate_by_fingerprint(req):
    """value-unknown: the certified xbrl_lane. req: {xbrls, concept, members, period_start, period_end}."""
    # ponytail: import xbrl_lane lazily — it pulls oracle -> run_code_tier, and run_code_tier imports THIS
    # module; a top-level import would cycle. By call time every module is loaded, so this is safe.
    sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
    import xbrl_lane
    return {'value': xbrl_lane.resolve(req.get('xbrls') or [], req['concept'], req['members'],
                                       req['period_start'], req['period_end'])}


if __name__ == '__main__':
    import subprocess
    subprocess.run([sys.executable, '-m', 'pytest', os.path.join(HERE, 'test_locate.py'), '-q'])
