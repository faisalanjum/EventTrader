"""THE Fiscal public-contract boundary adapter (production, tiny by order).

Maps internal packet items to the PUBLIC ChannelContract v1.0 field names:
`raw_label` -> `raw_label_or_claim`; `xbrl.axis_members` -> `xbrl.dimensions`
as {axis, member} dicts (verified-empty [] preserved explicitly). Forbidden
fields FAIL CLOSED; every other field is preserved exactly. Pure (never mutates
its input) and safely repeatable; non-XBRL prose items map cleanly.
"""
import copy

_ALLOWED = frozenset((                     # the CURRENT Fiscal packet shape —
    'raw_label', 'raw_label_or_claim',      # anything else fails closed (strict
    'value', 'fmt', 'is_currency',          # allowlist, not a blacklist)
    'period_end', 'cadence', 'quote', 'period_evidence',
    'tier', 'quote_source', 'xbrl',
    'level_unit_raw', 'level_unit_kind_hint',
    'level_money_mode_hint', 'level_shape_hint'))


def _pair_ok(a, m):
    return (isinstance(a, str) and a.strip()
            and isinstance(m, str) and m.strip())


def to_public(packets):
    out = copy.deepcopy(packets)
    for p in out:
        for i in p.get('items', []):
            unknown = set(i) - _ALLOWED
            if unknown:
                raise ValueError(f'unknown item fields {sorted(unknown)} — fail closed')
            if ('raw_label' in i) == ('raw_label_or_claim' in i):
                raise ValueError('exactly ONE label representation required')
            if 'raw_label' in i:
                i['raw_label_or_claim'] = i.pop('raw_label')
            lab = i['raw_label_or_claim']
            if not isinstance(lab, str) or not lab.strip():
                raise ValueError('label must be a nonblank string — fail closed')
            x = i.get('xbrl')
            if x is not None:
                if ('axis_members' in x) == ('dimensions' in x):
                    raise ValueError('exactly ONE dimension representation required')
                if 'axis_members' in x:
                    pairs = x.pop('axis_members')
                    if not all(isinstance(p_, (list, tuple)) and len(p_) == 2
                               and _pair_ok(*p_) for p_ in pairs):
                        raise ValueError('malformed dimension pair — fail closed')
                    x['dimensions'] = [{'axis': a, 'member': m} for a, m in pairs]
                if not isinstance(x['dimensions'], list) or not all(
                        isinstance(d, dict) and set(d) == {'axis', 'member'}
                        and _pair_ok(d['axis'], d['member'])
                        for d in x['dimensions']):
                    raise ValueError('malformed dimension — fail closed')
    return out
