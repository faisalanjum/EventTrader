import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import poll_feed


class PollFeedTests(unittest.TestCase):
    def test_runtime_files_stay_beside_the_script(self):
        folder = Path(poll_feed.__file__).resolve().parent
        self.assertEqual(poll_feed.STATE, folder / ".trackers_state.json")
        self.assertEqual(poll_feed.OUT, folder / "trackers_events.jsonl")

    def test_tickers_are_unique_and_sorted(self):
        event = {"payload": "$TSLA moved after $AAPL; $TSLA again"}
        self.assertEqual(poll_feed.tickers(event), ["AAPL", "TSLA"])

    def test_velocity_counts_distinct_accounts(self):
        events = [
            {"payload": "$TSLA", "subject": "account_a"},
            {"payload": "$TSLA", "subject": "account_a"},
            {"payload": "$TSLA", "subject": "account_b"},
        ]
        self.assertEqual(poll_feed.velocity(events), {"TSLA": {"account_a", "account_b"}})

    def test_pull_once_deduplicates_and_saves_state(self):
        events = [
            {"seq": 10, "payload": "$OLD", "subject": "old"},
            {"seq": 11, "payload": "$AAPL", "subject": "new"},
            {"seq": "bad", "payload": "$BAD", "subject": "bad"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / ".trackers_state.json"
            output = Path(tmp) / "trackers_events.jsonl"
            state.write_text('{"last_seq": 10}')

            with (
                patch.object(poll_feed, "STATE", state),
                patch.object(poll_feed, "OUT", output),
                patch.object(poll_feed, "_get", return_value={"events": events}),
            ):
                new = poll_feed.pull_once(verbose=False)

            self.assertEqual([event["seq"] for event in new], [11])
            self.assertEqual(json.loads(state.read_text()), {"last_seq": 11})
            saved = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["tickers_naive"], ["AAPL"])


if __name__ == "__main__":
    unittest.main()
