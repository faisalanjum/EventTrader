import sys
import unittest

sys.path.insert(0, '/tmp/decider_claude_review_20261115')
from metadata_candidates import body_start, digit_tokens


class MetadataCandidateChecks(unittest.TestCase):
    def test_metadata_excluded_content_and_context_preserved(self):
        text = 'Executive 2 [78]: Guidance is $5 million and 20%; note [7].'
        start, reason = body_start(text, {'Executive 2': 'CFO'}, 'Executive 2')
        self.assertEqual(reason, 'verified_header')
        self.assertEqual(text[start:], 'Guidance is $5 million and 20%; note [7].')
        tokens = digit_tokens(text, {'Executive 2': 'CFO'}, 'Executive 2')
        self.assertEqual([t['text'] for t in tokens], ['$5', '20%;', '[7].'])
        for token in tokens:
            self.assertEqual(text[token['start']:token['end']], token['text'])

    def test_uncertain_metadata_keeps_every_number(self):
        text = 'Executive [78]: Guidance is $5 million.'
        for speakers, speaker in [({}, None), ({'Someone else': 'CFO'}, None),
                                  ({'Executive': 'CFO'}, 'Different speaker')]:
            with self.subTest(speakers=speakers, speaker=speaker):
                start, _ = body_start(text, speakers, speaker)
                self.assertEqual(start, 0)
                self.assertEqual([t['text'] for t in digit_tokens(text, speakers, speaker)], ['[78]:', '$5'])

    def test_header_like_text_inside_speech_is_never_removed(self):
        text = 'Executive [0]: The label Revenue [12]: means $12 million.\nExecutive [20]: is an example.'
        tokens = digit_tokens(text, {'Executive': 'CFO'}, 'Executive')
        self.assertEqual([t['text'] for t in tokens], ['[12]:', '$12', '[20]:'])

    def test_plain_and_negative_timestamp_forms_are_retained(self):
        for text in ['Revenue forecast 20%.', 'Executive [-1]: Revenue 20%.',
                     'Statement\nExecutive [1]: Revenue 20%.']:
            with self.subTest(text=text):
                self.assertEqual(body_start(text, {'Executive': 'CFO'})[0], 0)

    def test_speech_touching_header_boundary_is_preserved(self):
        text = 'Executive [0]:20% growth.'
        tokens = digit_tokens(text, {'Executive': 'CFO'}, 'Executive')
        self.assertEqual([t['text'] for t in tokens], ['20%'])
        self.assertEqual(text[tokens[0]['start']:tokens[0]['end']], '20%')


if __name__ == '__main__':
    unittest.main()
