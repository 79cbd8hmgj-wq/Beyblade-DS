import struct
import unittest

from tools.nds.msdt import decode_asciiish, parse_msdt


class MsdtTests(unittest.TestCase):
    def test_parses_inclusive_end_offsets(self):
        units = [33, 34, 0x0E, 35]
        data = struct.pack("<IHHHH4H", 3, 0, 1, 0, 3, *units)
        parsed = parse_msdt(data)
        self.assertEqual(parsed["message_count"], 2)
        self.assertEqual(parsed["messages"][0]["units"], [33, 34])
        self.assertEqual(parsed["messages"][1]["units"], [0x0E, 35])

    def test_rejects_nonmonotonic_offsets(self):
        data = struct.pack("<IHHHH3H", 3, 0, 2, 0, 1, 33, 34, 35)
        with self.assertRaisesRegex(ValueError, "not monotonic"):
            parse_msdt(data)

    def test_asciiish_decoder(self):
        self.assertEqual(decode_asciiish([33, 34, 0x0E, 35]), "AB\nC")


if __name__ == "__main__":
    unittest.main()
