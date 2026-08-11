"""#827: a vendor column key becomes a STORED PERIOD, so deciding whether a key
is a date needs one truthful owner rather than a shape guess.

The old gate was `re.compile(r'^\\d{4}-\\d{2}-\\d{2}$').match(key)`, which
admitted three independent classes of wrong key. Each is pinned ALONE below,
beside a lawful control, so no later mutation can let one check hide another:

  * `\\d` matches every Unicode decimal digit, so full-width and Arabic-Indic
    keys passed a grammar whose contract is ASCII;
  * `.match` with `$` accepts a trailing newline, so `'2025-07-01\\n'` passed;
  * shape says nothing about the calendar, so `2025-02-30` passed.

`2025-2-03` was already refused by the shape and is kept as a control that the
fix did not widen anything.
"""
import gzip
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_worklist as BW                                         # noqa: E402
from build_worklist import _is_period_key                           # noqa: E402

LAWFUL = "2025-07-01"
LEAP = "2024-02-29"
BAD_KEYS = ["２０２５-０７-０１", "٢٠٢٥-٠٧-٠١", LAWFUL + "\n",
            "2025-02-30", "2025-2-03"]


def test_the_REAL_extraction_path_keeps_only_lawful_keys(tmp_path, monkeypatch):
    """THE PUBLIC PATH, not just the predicate. One vendor row carrying both
    lawful keys and every bad class; `extract_instances` must yield exactly the
    lawful ones, with their raw spelling preserved byte-for-byte."""
    raw = tmp_path / "raw"
    raw.mkdir()
    row = {"metric": {"metricName": "Revenue"}}
    for k in [LAWFUL, LEAP] + BAD_KEYS:
        row[k] = {"value": 1}
    doc = {"pageProps": {"segmentsData": {"data": {
        "Quarterly": {"catA": {"rows": [row]}}}}}}
    with gzip.open(raw / "NasdaqGS-AAPL_quarterly.json.gz", "wt",
                   encoding="utf-8") as fh:
        json.dump(doc, fh)
    monkeypatch.setattr(BW, "RUN", str(tmp_path))

    periods = [i["period"] for i in BW.extract_instances()]
    assert sorted(periods) == sorted([LAWFUL, LEAP]), periods
    for bad in BAD_KEYS:
        assert bad not in periods, bad
    # raw spelling preserved exactly — no repair, no normalisation
    assert LAWFUL in periods and LEAP in periods


def test_the_lawful_ascii_key_is_accepted():
    assert _is_period_key(LAWFUL)


def test_a_lawful_leap_day_is_accepted():
    """The calendar check must use the real calendar, not month-length guesses."""
    assert _is_period_key(LEAP)


@pytest.mark.parametrize("key,why", [
    ("２０２５-０７-０１", "full-width digits"),
    ("٢٠٢٥-٠٧-٠١", "Arabic-Indic digits"),
])
def test_UNICODE_GRAMMAR_alone_refuses(key, why):
    """Isolating case 1: correct shape, correct calendar, wrong script."""
    assert not _is_period_key(key), why


def test_TRAILING_RESIDUE_alone_refuses():
    """Isolating case 2: the digits and the calendar are both lawful; only the
    trailing newline is wrong. `$` matches before a final newline, so only a
    whole-value match refuses this."""
    assert _is_period_key(LAWFUL)
    assert not _is_period_key(LAWFUL + "\n")


def test_IMPOSSIBLE_CALENDAR_alone_refuses():
    """Isolating case 3: ASCII, canonical shape, no residue — February 30th
    simply does not exist. Shape alone cannot see this."""
    assert not _is_period_key("2025-02-30")
    assert _is_period_key("2025-02-28")


def test_non_canonical_padding_still_refuses():
    """Control: already refused before the fix, and must stay refused — the
    change narrows the gate and widens nothing."""
    assert not _is_period_key("2025-2-03")


@pytest.mark.parametrize("key", [None, 20250701, b"2025-07-01", ["2025-07-01"]])
def test_a_non_string_key_refuses_without_raising(key):
    """A bad row must be dropped, never crash the harvest loop."""
    assert not _is_period_key(key)
