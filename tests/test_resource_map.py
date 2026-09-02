import struct
import unittest

from tools.nds.resource_map import analyze_bey_lookup


class BeyResourceMapTests(unittest.TestCase):
    def test_finds_model_pointer_and_texture_descriptor_tables(self):
        base = 0x02000000
        data = bytearray(0x400)

        strings = {
            0x200: b"/bey/00_01.narc\0",
            0x220: b"/bey/01_02.narc\0",
            0x240: b"/bey/04_03.narc\0",
            0x280: b"/bey/00_01t.narc\0",
            0x2A0: b"00_01t.bin\0",
            0x2C0: b"/bey/01_02t.narc\0",
            0x2E0: b"01_02t.bin\0",
        }
        for off, value in strings.items():
            data[off : off + len(value)] = value

        struct.pack_into("<III", data, 0x40, base + 0x200, base + 0x220, base + 0x240)
        struct.pack_into("<III", data, 0x80, base + 0x280, base + 0x2A0, 0)
        struct.pack_into("<III", data, 0x8C, base + 0x2C0, base + 0x2E0, 0)

        report = analyze_bey_lookup(bytes(data), ram_base=base)

        self.assertEqual(report["model_table"]["offset"], 0x40)
        self.assertEqual(report["model_table"]["count"], 3)
        self.assertEqual(report["model_table"]["prefix_counts"], {"00": 1, "01": 1, "04": 1})
        self.assertEqual(report["texture_table"]["offset"], 0x80)
        self.assertEqual(report["texture_table"]["count"], 2)
        self.assertEqual(report["texture_table"]["entries"][0]["member"], "00_01t.bin")


if __name__ == "__main__":
    unittest.main()
