import unittest

from tools.nds.scan_rom import blz_decompress


class BlzTests(unittest.TestCase):
    def test_compressed_length_includes_header_and_preserves_prefix(self):
        # Decodes to b"XY" + b"ABC" * 6. The 0x18 flags deliberately leave
        # another back-reference bit set after the intended output is complete;
        # a decoder that incorrectly treats the uncompressed prefix as part of
        # the compressed body will overwrite XY with AB.
        body = bytes([0x00, 0xC0, ord("A"), ord("B"), ord("C"), 0x18])
        footer = bytes([0x10, 0x00, 0x00, 0x0A, 0x02, 0x00, 0x00, 0x00])
        fixture = b"XY" + body + b"\xFF\xFF" + footer
        self.assertEqual(blz_decompress(fixture), b"XY" + b"ABC" * 6)


if __name__ == "__main__":
    unittest.main()
