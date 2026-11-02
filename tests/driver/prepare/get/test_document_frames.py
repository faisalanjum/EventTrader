"""Exact SEC framing controls; expectations come from independently assembled bytes."""
import hashlib
import itertools
import unittest

from driver.prepare.get.acquire import AcquisitionError, document_parts, parse_package


ACC = '0001004434-23-000015'
CIK = '0001004434'
FORM = '8-K'
LF, CRLF = b'\n', b'\r\n'
FIELDS = (b'<TYPE>8-K', b'<SEQUENCE>1', b'<FILENAME>one.txt', b'<DESCRIPTION>printed label')


def frame(body, endings=None, fields=FIELDS):
    endings = endings or (LF,) * (len(fields) + 4)
    before = b'<DOCUMENT>' + endings[0]
    before += b''.join(value + nl for value, nl in zip(fields, endings[1:]))
    before += b'<TEXT>' + endings[len(fields) + 1]
    after = b'</TEXT>' + endings[len(fields) + 2] + b'</DOCUMENT>' + endings[len(fields) + 3]
    return before + body + after, before, after


def packet(frames, gap=b'', final=LF):
    header = (b'<SEC-DOCUMENT>' + ACC.encode() + b'.txt : 20230501\n'
              b'<SEC-HEADER>independent header\n'
              b'<ACCEPTANCE-DATETIME>20230501071224\n'
              b'ACCESSION NUMBER: ' + ACC.encode() + b'\n'
              b'CONFORMED SUBMISSION TYPE: 8-K\n'
              b'PUBLIC DOCUMENT COUNT: ' + str(len(frames)).encode() + b'\n'
              b'FILER:\n\tCENTRAL INDEX KEY: 0001004434\n</SEC-HEADER>\n')
    data = header + gap
    bounds = []
    for block in frames:
        start = len(data)
        data += block
        bounds.append([start, len(data)])
        data += gap
    return data + b'</SEC-DOCUMENT>' + final, bounds


class DocumentFrames(unittest.TestCase):
    def check(self, body, endings=None, fields=FIELDS, gap=b'', final=LF):
        block, before, after = frame(body, endings, fields)
        data, bounds = packet([block], gap, final)
        manifest, files = parse_package(data, ACC, CIK, FORM)
        self.assertEqual(files, {'one.txt': body})
        member, = manifest['members']
        self.assertEqual(member['package_range'], bounds[0])
        self.assertEqual(member['bytes'], len(body))
        self.assertEqual(member['sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(data[bounds[0][0]:bounds[0][1]], before + body + after)
        self.assertEqual(document_parts(data, bounds[0][0]), (before, after))
        return data, bounds

    def test_all_256_lf_crlf_vectors_at_the_eight_document_line_slots(self):
        body = b' first\r\n\nlast \x00\xff'
        for endings in itertools.product((LF, CRLF), repeat=8):
            with self.subTest(endings=endings):
                self.check(body, endings)

    def test_each_metadata_order_and_optional_description_preserves_bounds(self):
        for fields in (FIELDS[:3], FIELDS):
            for order in itertools.permutations(fields):
                with self.subTest(fields=order):
                    self.check(b'content with no trailing newline', fields=order)

    def test_adjacent_members_do_not_merge_and_mixed_empty_gaps_stay_outside(self):
        first, before1, after1 = frame(b'one\r\n\n', (LF, CRLF) * 4)
        fields2 = (b'<TYPE>EX-99.1', b'<SEQUENCE>2', b'<FILENAME>two.txt')
        second, before2, after2 = frame(b'two\x00\xff', (CRLF, LF, LF, CRLF, LF, CRLF, LF), fields2)
        for gap in (b'', LF, CRLF, LF + CRLF + LF):
            for final in (b'', LF, CRLF):
                data, bounds = packet([first, second], gap, final)
                with self.subTest(gap=gap, final=final):
                    manifest, files = parse_package(data, ACC, CIK, FORM)
                    self.assertEqual(files, {'one.txt': b'one\r\n\n', 'two.txt': b'two\x00\xff'})
                    self.assertEqual([m['package_range'] for m in manifest['members']], bounds)
                    self.assertEqual(document_parts(data, bounds[0][0]), (before1, after1))
                    self.assertEqual(document_parts(data, bounds[1][0]), (before2, after2))

    def test_empty_binary_and_near_delimiters_are_exact_payload_not_framing(self):
        bodies = (b'', b'no newline', bytes(range(256)),
                  b'quoted <TEXT> is prose\nquoted </TEXT> is prose\n',
                  b'quoted </TEXT>\nnot-document\n',
                  b'quoted </TEXT>\r\n</DOCUMENT> trailing word\r\n',
                  b'quoted </TEXT>\n </DOCUMENT>\n',
                  b'quoted </TEXT>\r</DOCUMENT>\r',
                  b'x</text>\n</document>\n',
                  b'x</TEXT>\n</DOCUMENT >\n')
        for body in bodies:
            with self.subTest(body=body[:60]):
                self.check(body)
        self.check(b'x' * (1024 * 1024) + b' quoted </TEXT>\nnot-document\n')

    def test_standalone_reserved_tags_or_embedded_complete_frame_are_rejected(self):
        self.check(b'valid positive\n')
        for tag in (b'<DOCUMENT>', b'</DOCUMENT>', b'<TEXT>', b'</TEXT>'):
            for nl in (LF, CRLF):
                body = b'before' + nl + tag + nl + b'after\n'
                data, _ = packet([frame(body)[0]])
                with self.subTest(tag=tag, nl=nl), self.assertRaises(AcquisitionError):
                    parse_package(data, ACC, CIK, FORM)
        inner, _, _ = frame(b'inner')
        for body in (b'prefix\n' + inner + b'suffix',
                     b'inline </TEXT>\n</DOCUMENT>\nleftover',
                     b'quoted </TEXT>\n</DOCUMENT>'):  # an exact reserved tag at TEXT end is still a whole line
            data, _ = packet([frame(body)[0]])
            with self.subTest(body=body[:70]), self.assertRaises(AcquisitionError):
                parse_package(data, ACC, CIK, FORM)

    def test_missing_first_member_delimiters_cannot_swallow_the_next_member(self):
        endings = (LF, CRLF) * 4
        first, _, _ = frame(b'first payload\n', endings)
        second = frame(b'second payload\n', (CRLF,) * 7,
                       fields=(b'<TYPE>EX-99.1', b'<SEQUENCE>2', b'<FILENAME>two.txt'))[0]
        positive, _ = packet([first, second])
        self.assertEqual(parse_package(positive, ACC, CIK, FORM)[1],
                         {'one.txt': b'first payload\n', 'two.txt': b'second payload\n'})
        for marker in (b'<DOCUMENT>' + endings[0], b'<TEXT>' + endings[5],
                       b'</TEXT>' + endings[6], b'</DOCUMENT>' + endings[7],
                       b'</TEXT>' + endings[6] + b'</DOCUMENT>' + endings[7]):
            bad, _ = packet([first.replace(marker, b'', 1), second])
            with self.subTest(marker=marker), self.assertRaises(AcquisitionError):
                parse_package(bad, ACC, CIK, FORM)

    def test_malformed_newlines_closing_pairs_and_headers_are_not_relaxed(self):
        self.check(b'positive')
        good = frame(b'payload')[0]
        bad_blocks = [good.replace(token, replacement, 1) for token, replacement in (
            (b'<DOCUMENT>\n', b'<DOCUMENT>\r'), (b'<TEXT>\n', b'<TEXT> \n'),
            (b'</TEXT>\n', b'</TEXT>\r'), (b'</DOCUMENT>\n', b'</DOCUMENT>\r'),
            (b'</TEXT>\n</DOCUMENT>', b'</TEXT>\n\n</DOCUMENT>'),
            (b'</TEXT>', b'</text>'), (b'</DOCUMENT>', b'</DOCUMENT >'),
            (b'<TYPE>8-K\n', b'<TYPE>8-K\n<TYPE>EX-1\n'),
            (b'<DESCRIPTION>printed label\n', b'<DESCRIPTION>literal <TEXT>\n'))]
        for block in bad_blocks:
            data, _ = packet([block])
            with self.subTest(block=block[-80:]), self.assertRaises(AcquisitionError):
                parse_package(data, ACC, CIK, FORM)

    def test_document_parts_matches_only_at_the_given_byte_start(self):
        block, before, after = frame(b'exact body\x00\xff')
        data = b'prefix </TEXT>\n</DOCUMENT>\n' + block + b'untouched tail'
        start = len(b'prefix </TEXT>\n</DOCUMENT>\n')
        self.assertEqual(document_parts(data, start), (before, after))
        for bad_start in (0, start - 1, start + 1, len(data), len(data) + 1):
            with self.subTest(start=bad_start), self.assertRaises(AcquisitionError):
                document_parts(data, bad_start)
        for bad in (block.replace(b'<TEXT>\n', b'', 1), block.replace(b'</TEXT>', b'', 1), block[:-1]):
            with self.subTest(body=bad[-40:]), self.assertRaises(AcquisitionError):
                document_parts(bad, 0)


if __name__ == '__main__':
    unittest.main()
