"""The raw route prefilter must see a script run inside a JSON-escaped line.

Records are scanned raw, before JSON decoding, and a script invocation with a quoted
path is stored as `python -B \\"$S/harvest.py\\"`: the backslash before the quote defeated
the script-runner pattern, so the thirty-five harvest calls never reached the
path-aware check and the accumulator they rewrite had three records instead of
thirty-eight.
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "ledger")]
import chrono_replay as CR  # noqa: E402


def test_the_script_runner_pattern_matches_a_json_escaped_quoted_path():
    raw = '{"command":"S=/tmp/x\\nPYTHONDONTWRITEBYTECODE=1 /v/bin/python -B \\"$S/harvest.py\\" 11 sid wf_1 1"}'
    assert CR._RUNS_SCRIPT.search(raw)


def test_the_pattern_still_matches_the_plain_forms():
    assert CR._RUNS_SCRIPT.search('python3 "/tmp/x/harvest.py" 1')
    assert CR._RUNS_SCRIPT.search("python3 -B /tmp/x/harvest.py")
    assert not CR._RUNS_SCRIPT.search("python3 - <<'PY'")
