"""value_ok must never bind a value to a quote whose OWN NOTATION contradicts its sign.

THE BLANKET RULE (mechanical, zero false parks):
  * The quote prints THIS number in accounting-negative notation — '(123)' or '-123' -> the quote ASSERTS
    negative. A value with the opposite sign is a real conflict -> reject.
  * The quote prints it plainly -> the quote asserts NOTHING about sign (the minus may live in a word like
    "loss" — a MEANING call the core owns per OD-12) -> NO verdict -> pass. Never park a good fact.
So it catches wrong signs without a keyword list and without discarding word-carried negatives.

    venv/bin/python -m pytest scripts/driver_seed/test_sign_gate.py -q
"""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import link_lib as L


# ---- the hole: a POSITIVE value matching a NEGATIVE print (46,806 '%' rows are exposed) ----
def test_positive_value_must_not_match_a_parenthesised_negative_print():
    assert L.value_ok(0.2, '%', 'operating margin fell (0.2)% year over year') is False


def test_positive_value_must_not_match_a_minus_signed_print():
    assert L.value_ok(380000000, 'number', 'segment result was -380,000,000 for the year') is False


# ---- consistent cases must still pass (no recall loss) ----
def test_negative_value_matches_a_parenthesised_negative_print():
    assert L.value_ok(-0.2, '%', 'operating margin fell (0.2)% year over year') is True


def test_negative_value_matches_the_real_wmg_row():
    # the real #6 quote: the printed segment row, cropped mid-number
    assert L.value_ok(-106000000, 'number',
                      'Corporate expenses and eliminations Revenue eliminations (2) (2) - - % Operating loss (106') is True


def test_positive_value_matches_a_plain_positive_print():
    assert L.value_ok(500000, 'number', 'Widget revenue 500,000 for the period') is True


# ---- the deliberate NON-verdict: sign carried by a WORD, not by notation ----
def test_negative_value_on_a_plain_print_still_passes_no_verdict():
    # real #3/#5: "Adjusted OIBDA loss ... to $180" — the word "loss" carries the minus, not the print.
    # Judging this needs MEANING (the core's job). A mechanical park here would discard a correct fact.
    assert L.value_ok(-180000000, 'number',
                      'Adjusted OIBDA loss from corporate expenses and eliminations increased by $25 million to $180') is True


# ---- #827 B1 packet 6 (SEQ 312): '$'/'$ ' between the sign mark and the digits ----
# The sign notation wraps the DECORATED print. The detector must see the sign around the
# exact generated form ('$5,365'), not only around the bare numeric core.
_B6_CURRENCY_NEGATIVE_PRINTS = [
    pytest.param('($5,365)', 5365, id='paren-dollar'),
    pytest.param('($ 5,365)', 5365, id='paren-dollar-space'),
    pytest.param('-$5,365', 5365, id='ascii-minus-dollar'),
    pytest.param('−$5,365', 5365, id='u2212-minus-dollar'),
    pytest.param('($1,234,567,890,123)', 1234567890123, id='paren-dollar-13-digits'),
]


@pytest.mark.parametrize('quote, value', _B6_CURRENCY_NEGATIVE_PRINTS)
def test_827B6_positive_value_must_not_match_currency_negative_notation(quote, value):
    # control FIRST: a numeric form of this value IS present at a boundary in the quote,
    # so a refusal below can only come from the sign rule — never from a missing form.
    assert any(L.bounded_hit(quote, f) for f in L.value_forms(value, 'number'))
    assert L.value_ok(value, 'number', quote) is False


@pytest.mark.parametrize('quote, value', _B6_CURRENCY_NEGATIVE_PRINTS)
def test_827B6_negative_value_still_matches_the_same_notation(quote, value):
    assert L.value_ok(-value, 'number', quote) is True


def test_827B6_plain_positive_currency_stays_allowed():
    assert L.value_ok(5365, 'number', 'segment revenue of $5,365 for the period') is True


def test_827B6_parenthetical_words_stay_a_non_verdict():
    # '(500 employees)' is a parenthetical, not accounting notation for 500.
    assert L.value_ok(500, 'number', 'headcount grew (500 employees) in the region') is True


# ---- #827 B6 (SEQ 319): sign belongs to the OCCURRENCE, not the whole quote ----
# A financial comparison lawfully prints the same number twice with different signs
# ("20, compared with (20) prior year"). A positive value binds when at least one
# qualifying occurrence is NOT negatively printed; an all-negative quote still refuses.
def test_827B6_positive_occurrence_survives_a_negative_neighbor_after():
    assert L.value_ok(20, 'number', 'Revenue was 20, compared with (20) prior year.') is True


def test_827B6_positive_occurrence_survives_a_negative_neighbor_before():
    assert L.value_ok(20, 'number', 'Prior year was (20); revenue is now 20.') is True


def test_827B6_single_positive_print_still_binds():
    assert L.value_ok(20, 'number', 'Revenue was 20.') is True


def test_827B6_single_negative_print_still_refuses_positive():
    assert L.value_ok(20, 'number', 'Revenue was (20).') is False


def test_827B6_all_negative_occurrences_still_refuse_positive_both_orders():
    assert L.value_ok(20, 'number', 'Loss was (20), compared with (20) prior year.') is False
    assert L.value_ok(20, 'number', 'Prior year was (20); loss is now (20).') is False


def test_827B6_negative_value_unaffected_by_mixed_prints():
    assert L.value_ok(-20, 'number', 'Revenue was 20, compared with (20) prior year.') is True


# ---- #827 B6 (SEQ 321): no cross-occurrence laundering — the positive evidence must
# itself be a FULLY qualifying print of THIS fact. A percent-marked '20%' or a
# scale-conflicting '20 million' is not this plain-number fact's print; it counts
# neither way, so the negative '(20)' still refuses.
@pytest.mark.parametrize('quote', [
    pytest.param('Loss was (20), while margin was 20%.', id='pct-after'),
    pytest.param('Margin was 20%, while loss was (20).', id='pct-before'),
], )
def test_827B6_percent_marked_occurrence_cannot_launder_the_sign(quote):
    assert L.value_ok(20, 'number', quote) is False


@pytest.mark.parametrize('quote', [
    pytest.param('Loss was (20), while revenue was 20 million.', id='scale-after'),
    pytest.param('Revenue was 20 million, while loss was (20).', id='scale-before'),
], )
def test_827B6_scale_conflicting_occurrence_cannot_launder_the_sign(quote):
    assert L.value_ok(20, 'number', quote) is False


@pytest.mark.parametrize('quote', [
    pytest.param('Loss was (20), while revenue was 20.', id='plain-after'),
    pytest.param('Revenue was 20, while loss was (20).', id='plain-before'),
], )
def test_827B6_truly_plain_occurrence_still_rescues_the_positive(quote):
    assert L.value_ok(20, 'number', quote) is True


# ---- #827 B6 (SEQ 322): occurrences are of the EXACT FORM, in every format ----
# A plain '20' is not a percent form; it can neither satisfy nor launder a %-fact.
@pytest.mark.parametrize('quote', [
    pytest.param('Margin was (20)%, while revenue was 20.', id='plain-neighbor-after'),
    pytest.param('Revenue was 20, while margin was (20)%.', id='plain-neighbor-before'),
], )
def test_827B6_plain_number_cannot_launder_a_percent_fact(quote):
    assert L.value_ok(20, '%', quote) is False


# ---- #827 B6 (SEQ 325): raw evidence keeps its scale word — trillion included ----
@pytest.mark.parametrize('word, value', [
    pytest.param('million', 1_200_000, id='million-evidence-kept'),
    pytest.param('billion', 1_200_000_000, id='billion-evidence-kept'),
    pytest.param('trillion', 1_200_000_000_000, id='trillion-evidence-kept'),
], )
def test_827B6_row_quote_keeps_the_scale_word_evidence(word, value):
    q = L.row_quote([f'Widget revenues 1.2 {word} for the period'],
                    ['Widget', 'revenues'], value, 'number', scale_gate=True)
    assert q is not None and word in q


def test_827B6_row_quote_wrong_scale_still_refuses():
    assert L.row_quote(['Widget revenues 1.2 million for the period'],
                       ['Widget', 'revenues'], 1_200_000_000_000, 'number',
                       scale_gate=True) is None


# ---- #827 B6 (SEQ 326): scale companions belong to the plain-number lane ONLY ----
def test_827B6_scaled_companion_must_not_launder_percent_evidence():
    assert L.value_ok(1_200_000, '%', 'margin was 1.2') is False


def test_827B6_genuine_percent_print_still_binds():
    assert L.value_ok(1.2, '%', 'margin was 1.2%') is True


# ---- #827 B6 (SEQ 327): the companion ladder is the FULL frozen scale family ----
# UniversalLocator_ReviewRecord_2026-07-18.md, Round 16 (ChatGPT, 2026-07-19) item 4:
# thousand + trillion exact forms belong to the same marker-gated scale law as
# million/billion (Rounds 13 item 3(c) / 14 item 2 own the required-multiplier rule).
@pytest.mark.parametrize('value, word', [
    pytest.param(2_020_200, 'thousand', id='thousand-grouped-decimal-companion'),
    pytest.param(2_020_200_000, 'million', id='million-grouped-decimal-companion'),
    pytest.param(2_020_200_000_000, 'billion', id='billion-grouped-decimal-companion'),
    pytest.param(2_020_200_000_000_000, 'trillion', id='trillion-grouped-decimal-companion'),
], )
def test_827B6_grouped_decimal_companion_binds_with_its_scale_evidence(value, word):
    assert L.value_ok(value, 'number', f'total revenue of 2,020.2 {word} for the year') is True


@pytest.mark.parametrize('value, word', [
    pytest.param(2_020_200_000_000, 'million', id='million-tag-for-a-trillion-value-refused'),
    pytest.param(2_020_200, 'trillion', id='trillion-tag-for-a-thousand-value-refused'),
], )
def test_827B6_grouped_decimal_companion_wrong_scale_refuses(value, word):
    assert L.value_ok(value, 'number', f'total revenue of 2,020.2 {word} for the year') is False


@pytest.mark.parametrize('value, word, tag', [
    pytest.param(1_200, 'thousand', 'K', id='thousand-row'),
    pytest.param(1_200_000, 'million', 'M', id='million-row'),
    pytest.param(1_200_000_000, 'billion', 'B', id='billion-row'),
    pytest.param(1_200_000_000_000, 'trillion', 'T', id='trillion-row'),
], )
def test_827B6_every_scale_table_row_produces_its_worded_and_tagged_forms(value, word, tag):
    # direct owner pins for all four (value, word, tag) contract rows — word drift,
    # divisor drift and tag drift each have a detector here
    forms = L.value_forms(value, 'number')
    assert f'1.2{tag}' in forms
    assert f'1.2 {word}' in forms


# ---- #827 B6 (SEQ 323): ONE numeric-boundary law for every form, dot-leading included ----
@pytest.mark.parametrize('quote, want', [
    pytest.param('margin was .3%', True, id='omitted-zero-print-lawful'),
    pytest.param('margin was 0.3%', True, id='full-print-lawful'),
    pytest.param('margin was 1.3%', False, id='inside-larger-decimal-refused'),
    pytest.param('margin was 11.3%', False, id='inside-larger-two-digit-refused'),
], )
def test_827B6_dot_leading_form_obeys_the_numeric_boundary(quote, want):
    assert L.value_ok(0.3, '%', quote) is want


def test_827B6_percent_negative_only_still_refuses_positive():
    assert L.value_ok(20, '%', 'Margin was (20)% only.') is False


def test_827B6_genuine_plain_percent_still_rescues():
    assert L.value_ok(20, '%', 'Margin was (20)%, compared with 20%.') is True


def test_827B6_printed_negative_owner_is_occurrence_uniform():
    # Direct owner pins (consumer: locate.py's sign hint): a mixed print is NOT
    # "printed negative"; only a uniformly negative print is.
    assert L.printed_negative('20 vs (20)', '20') is False
    assert L.printed_negative('(20) vs (20)', '20') is True


# ---- #827 B6 (SEQ 313): stated_match sign law — ONE notation owner, no anywhere-parens ----
_B6_STATED_SIGN_ROWS = [
    pytest.param('24.6 (unaudited)', 24.6, True, id='trailing-parenthetical-allows-positive'),
    pytest.param('(24.6)', -24.6, True, id='wrapped-negative-truth-allows'),
    pytest.param('-24.6', -24.6, True, id='ascii-minus-negative-truth-allows'),
    pytest.param('-24.6', 24.6, False, id='ascii-minus-positive-truth-refuses'),
    pytest.param('−24.6', -24.6, True, id='u2212-negative-truth-allows'),
    pytest.param('−24.6', 24.6, False, id='u2212-positive-truth-refuses'),
    pytest.param('($5,365)', -5365, True, id='paren-dollar-negative-truth-allows'),
    pytest.param('($5,365)', 5365, False, id='paren-dollar-positive-truth-refuses'),
    pytest.param('-$5,365', -5365, True, id='minus-dollar-negative-truth-allows'),
    pytest.param('-$5,365', 5365, False, id='minus-dollar-positive-truth-refuses'),
    pytest.param('$(5,365)', -5365, True, id='dollar-paren-negative-truth-allows'),
    pytest.param('$(5,365)', 5365, False, id='dollar-paren-positive-truth-refuses'),
    pytest.param('$ ( 0.20 )', -0.2, True, id='spaced-paren-padded-negative-allows'),
    pytest.param('$ ( 0.20 )', 0.2, False, id='spaced-paren-padded-positive-refuses'),
    pytest.param('24.6', 24643957000, True, id='pin-rounded-consistent'),
    pytest.param('1,017.0', 989400000, False, id='pin-genuinely-different'),
    pytest.param('6,115', 6115000000, True, id='pin-grouped-scale-ladder'),
    pytest.param('$ 6,115', 6115000000, True, id='pin-currency-spaced'),
    # SEQ 315/316: lawful features COMBINED stay lawful — decoration between the sign
    # mark and the digits ('($0.20)': parens + currency + padded coefficient together)
    pytest.param('($0.20)', -0.2, True, id='paren-dollar-padded-negative-allows'),
    pytest.param('($0.20)', 0.2, False, id='paren-dollar-padded-positive-refuses'),
    pytest.param('($ 0.20)', -0.2, True, id='paren-dollar-space-padded-negative-allows'),
    pytest.param('($ 0.20)', 0.2, False, id='paren-dollar-space-padded-positive-refuses'),
    pytest.param('-$0.20', -0.2, True, id='minus-dollar-padded-negative-allows'),
    pytest.param('-$0.20', 0.2, False, id='minus-dollar-padded-positive-refuses'),
    pytest.param('−$0.20', -0.2, True, id='u2212-dollar-padded-negative-allows'),
    pytest.param('−$0.20', 0.2, False, id='u2212-dollar-padded-positive-refuses'),
    # SEQ 316: the code must not know '$' — any non-word decoration obeys the same law
    pytest.param('(€0.20)', -0.2, True, id='euro-paren-padded-negative-allows'),
    pytest.param('(€0.20)', 0.2, False, id='euro-paren-padded-positive-refuses'),
    # SEQ 316: a sign inside a CLOSED delimiter never donates across the closer
    pytest.param('(-) $24.6', 24.6, True, id='closed-minus-paren-does-not-donate-positive-allows'),
    pytest.param('(-) $24.6', -24.6, False, id='closed-minus-paren-does-not-donate-negative-refuses'),
    pytest.param('[−] $24.6', 24.6, True, id='closed-minus-bracket-does-not-donate-positive-allows'),
    pytest.param('[−] $24.6', -24.6, False, id='closed-minus-bracket-does-not-donate-negative-refuses'),
    pytest.param('{−} $24.6', 24.6, True, id='closed-minus-brace-does-not-donate-positive-allows'),
    pytest.param('{−} $24.6', -24.6, False, id='closed-minus-brace-does-not-donate-negative-refuses'),
    # ordinary parenthetical controls (both directions of neighborhood)
    pytest.param('(audited) 24.6', 24.6, True, id='closed-parenthetical-before-number-allows'),
]


@pytest.mark.parametrize('vstr, truth, want', _B6_STATED_SIGN_ROWS)
def test_827B6_stated_match_sign_law(vstr, truth, want):
    assert L.stated_match(vstr, truth) is want


# ---- #827 B6 (SEQ 313): _parse_stated token/scale contract — park, never guess ----
# Frozen-corpus measurement (seq313_measurements.txt): 653 gate-passing picks — 0 leading-dot
# forms, 0 malformed single tokens, 0 substring-only scale words, 4 multi-token prints (all
# grade False today). The strict contract below therefore flips no frozen verdict.
_B6_PARK_ROWS = [
    pytest.param('(1) 24.6', id='earlier-token-must-not-donate-sign'),
    pytest.param('1,,234', id='double-comma-not-1234'),
    pytest.param('12,34', id='misplaced-group-not-1234'),
    pytest.param('24.6 (2025)', id='second-token-not-glued-into-value'),
    pytest.param('5 million billion', id='two-scale-words-park'),
    pytest.param('9' * 400, id='non-finite-parks'),
    pytest.param('$107,741 thousand (~$107.7 million)', id='frozen-dual-representation-parks'),
    # SEQ 314: the lexical rule is ASCII [0-9] — Unicode digits park, they never convert
    pytest.param('٤٢', id='arabic-digits-park'),
    pytest.param('２４.６', id='fullwidth-digits-park'),
    # SEQ 314: punctuation is never silently repaired — the value must not change
    pytest.param('.20', id='leading-dot-must-not-become-20'),
    pytest.param(',123', id='leading-comma-must-not-become-123'),
    pytest.param('1.', id='trailing-dot-without-fraction-parks'),
    pytest.param('FY86', id='alphanumeric-glued-token-parks'),
    # SEQ 314: exact word OCCURRENCES, not distinct multipliers — repeats park too
    pytest.param('5 million million', id='repeated-scale-word-parks'),
    pytest.param('5 million millions', id='repeated-scale-family-parks'),
]


@pytest.mark.parametrize('vstr', _B6_PARK_ROWS)
def test_827B6_parse_stated_parks_malformed_and_ambiguous(vstr):
    assert L._parse_stated(vstr) is None


def test_827B6_parse_stated_scale_needs_a_word_boundary():
    # 'millionaire' contains 'million' but states no scale — substring matching is banned.
    assert L._parse_stated('24.6 millionaire') == (False, 24.6, 1, None)


_B6_LAWFUL_PARSE_ROWS = [
    pytest.param('24.6', (False, 24.6, 1, None), id='plain'),
    pytest.param('(24.6)', (True, 24.6, 1, None), id='wrapped'),
    pytest.param('$ 6,115', (False, 6115.0, 0, None), id='currency-grouped'),
    pytest.param('1,017.0', (False, 1017.0, 1, None), id='grouped-decimal'),
    pytest.param('6,115 million', (False, 6115.0, 0, 1e6), id='one-scale-word'),
    pytest.param('$ ( 0.20 )', (True, 0.2, 2, None), id='spaced-paren-padded-print'),
    # SEQ 314 lawful twins beside the new parks
    pytest.param('0.20', (False, 0.2, 2, None), id='zero-led-decimal'),
    pytest.param('123', (False, 123.0, 0, None), id='bare-int'),
    pytest.param('1,234.56', (False, 1234.56, 2, None), id='grouped-two-decimals'),
    pytest.param('5 million', (False, 5.0, 0, 1e6), id='single-scale-word'),
    # SEQ 319: scale words derive from locator._WORD2DIV (the one owner) under the
    # existing s?-plural convention — the plural spelling stays lawful
    pytest.param('5 millions', (False, 5.0, 0, 1e6), id='single-scale-word-plural'),
]


@pytest.mark.parametrize('vstr, expected', _B6_LAWFUL_PARSE_ROWS)
def test_827B6_parse_stated_keeps_lawful_prints(vstr, expected):
    assert L._parse_stated(vstr) == expected
