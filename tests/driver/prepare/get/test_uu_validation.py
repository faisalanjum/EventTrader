"""UU line validation: the full byte alphabet, legal lengths and native decoding."""
import binascii
import unittest

from driver.prepare.get.acquire import _decode, _uu_invalid, AcquisitionError


class UuValidation(unittest.TestCase):
    def test_all_prefixes_lengths_and_byte_positions(self):
        allowed = set(range(32, 97))
        for prefix in range(256):
            for length in range(1, 67):
                line = bytes([prefix]) + b' ' * (length - 1)
                count = (prefix - 32) % 64
                expected = (prefix not in allowed or count > 45
                            or length > 1 + 4 * ((count + 2) // 3))
                self.assertEqual(bool(_uu_invalid(line)), expected, (prefix, length))
        valid = b'M' + b' ' * 60  # the length prefix declares 45 zero bytes
        self.assertFalse(_uu_invalid(valid))
        for position in range(1, len(valid)):
            for value in range(256):
                line = valid[:position] + bytes([value]) + valid[position + 1:]
                self.assertEqual(bool(_uu_invalid(line)), value not in allowed, (position, value))

    def test_every_decoded_length_and_padding_uses_native_bytes(self):
        for count in range(46):
            raw = bytes((17 * k + count) % 256 for k in range(count))
            line = binascii.b2a_uu(raw).rstrip(b'\n')
            self.assertFalse(_uu_invalid(line))
            wrapped = b'begin 644 test.bin\n' + line + b'\n`\nend\n'
            self.assertEqual(_decode(wrapped, 'test.bin'), raw)
        for bad in (b'\x1f', b'\x61', b'\xff'):
            with self.assertRaises(AcquisitionError):
                _decode(b'begin 644 test.bin\nM' + bad * 60 + b'\n`\nend\n', 'test.bin')


if __name__ == '__main__':
    unittest.main()
