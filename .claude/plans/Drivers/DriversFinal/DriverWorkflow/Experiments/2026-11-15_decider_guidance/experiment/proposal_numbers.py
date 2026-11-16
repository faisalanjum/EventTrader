"""Diagnostic adapter for the trial's existing unit choices and source tokens.

Babel 2.17 supplies strict en_US decimal/group parsing; the existing shared
exact_numbers helper supplies exact scaling. Neither accepts a currency sign,
percent sign or sentence punctuation, so the small wrapper below accepts one
complete literal and passes its number to Babel. It never hunts for a number
inside arbitrary text. Unsupported spellings/choices are explicit failures.
This is not a new production financial parser or a claimed all-locale reader.
"""
import re
import sys

from babel.numbers import parse_decimal

sys.path.insert(0, '/home/faisal/EventMarketDB')
from driver_reference.core.driver_ids import dec_canon
from driver_reference.relocation.exact_numbers import exact_scaleb

SCALING = {
    'usd': ('usd', 0), 'usd_cents': ('usd', -2),
    'm_usd_from_dollars': ('m_usd', -6), 'm_usd_from_thousands': ('m_usd', -3),
    'm_usd_from_millions': ('m_usd', 0), 'm_usd_from_billions': ('m_usd', 3),
    'count': ('count', 0), 'count_thousand': ('count', 3),
    'count_million': ('count', 6), 'count_billion': ('count', 9),
    **{u: (u, 0) for u in ['percent', 'percent_yoy', 'percent_sequential',
                           'percent_points', 'basis_points', 'x', 'unknown']}}


def printed_decimal(token):
    match = re.fullmatch(r'\$?([+-]?(?:[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?|\.[0-9]+))%?[,.;:!?]?', token)
    if not match:
        raise ValueError('unsupported complete numeric spelling: ' + repr(token))
    return parse_decimal(match[1], locale='en_US', strict=True)


def normalize(token, unit_choice, sign):
    value = printed_decimal(token)
    if unit_choice not in SCALING or sign not in ['positive', 'negative', 'zero']:
        raise ValueError('unresolved unit/scale or sign')
    if (value < 0 and sign != 'negative') or ((value == 0) != (sign == 'zero')):
        raise ValueError('source number and selected sign conflict')
    value = value.copy_abs().copy_negate() if sign == 'negative' else value
    unit, exponent = SCALING[unit_choice]
    return dec_canon(exact_scaleb(value, exponent)), unit
