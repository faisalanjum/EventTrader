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
