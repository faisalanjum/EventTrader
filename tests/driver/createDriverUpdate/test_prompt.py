import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from jinja2 import DictLoader, Environment
from neo4j.graph import Graph, Node

from driver.createDriverUpdate.asset import Asset, Unit
from driver.createDriverUpdate.prompt import render_find_facts


class FindFactsPromptTests(unittest.TestCase):
    def test_full_prompt_matches_review(self):
        folder = Path(__file__).resolve().parents[3] / "driver" / "Prompts"
        review = json.loads((folder / "find_facts_review.json").read_text(encoding="utf-8"))
        full = render_find_facts()
        self.assertEqual(hashlib.sha256(full.encode()).hexdigest(), review["prompt_sha256"])
        self.assertEqual(len(full.split()), review["prompt_words"])
        self.assertEqual(hashlib.sha256((folder / "find_facts.txt").read_bytes()).hexdigest(),
                         review["template_sha256"])

    def test_rules_by_source(self):
        for source, transcript, filing in (
            (None, True, True), ("", False, False), ("  ", False, False),
            ("transcript", True, False), ("news", False, False),
            ("8-K", False, True), ("10-Q", False, True), ("10-K", False, True),
            ("8k", False, True), ("10q", False, True), ("10k", False, True),
            ("425", False, False), ("10-K/A", False, False),
        ):
            with self.subTest(source=source):
                prompt = render_find_facts(source)
                self.assertEqual("In transcripts, questions/assumptions" in prompt, transcript)
                self.assertEqual("The filing’s own tags on that number" in prompt, filing)
                self.assertIn("Keep needed question-and-answer context", prompt)
                self.assertIn("Never infer units/scales", prompt)

    def test_uses_existing_source_metadata(self):
        for label, properties, expected in (
            ("Report", {"formType": "10-Q"}, "10-Q"),
            ("Report", {"formType": "8-K/A"}, "8-K/A"),
            ("Report", {}, ""),
            ("Transcript", {"formType": "TRANSCRIPT_Q1"}, "Transcript"),
            ("News", {}, "News"),
        ):
            with self.subTest(label=label, properties=properties):
                node = Node(Graph(), "1", 1, [label], properties)
                self.assertEqual(render_find_facts(node), render_find_facts(expected))

    def test_prepared_document_uses_its_source_type(self):
        asset = Asset("1", "10-Q", datetime(2026, 1, 1, tzinfo=timezone.utc),
                      (Unit("text", "report.htm", 0, 4),))
        self.assertEqual(render_find_facts(asset), render_find_facts("10-Q"))

    def test_adding_a_news_rule_only_changes_news(self):
        template = 'common{% if applies_to("news") %} + news{% endif %}'
        env = Environment(loader=DictLoader({"find_facts.txt": template}))
        with patch("driver.createDriverUpdate.prompt._PROMPTS", env):
            self.assertEqual(render_find_facts(Node(Graph(), "1", 1, ["News"])), "common + news")
            self.assertEqual(render_find_facts(""), "common")
