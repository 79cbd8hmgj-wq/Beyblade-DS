import struct
import unittest

from tools.nds.component_records import parse_component_table


class ComponentRecordTests(unittest.TestCase):
    def test_parses_record_and_effect_scripts(self):
        base = 0x02000000
        image = bytearray(0x200)
        table = base + 0x40
        primary = base + 0x100
        secondary = base + 0x120
        struct.pack_into('<IIIII', image, 0x40,
                         7, 0x01020304, primary, secondary, 0x05060708)
        struct.pack_into('<HhHhHH', image, 0x100,
                         1, 4, 10, -2, 0, 0)
        struct.pack_into('<HhHH', image, 0x120,
                         3, 9, 0, 0)

        records = parse_component_table(bytes(image), table, 1, 0x190, base)
        record = records[0]

        self.assertEqual(record['selection_id'], 0x190)
        self.assertEqual(record['field_00_u32'], 7)
        self.assertEqual(record['field_04_bytes'], [4, 3, 2, 1])
        self.assertEqual(record['field_10_bytes'], [8, 7, 6, 5])
        self.assertEqual(record['primary_effects'], [
            {'opcode': 1, 'stat_offset': 0, 'value': 4},
            {'opcode': 10, 'stat_offset': 18, 'value': -2},
        ])
        self.assertEqual(record['secondary_effects'], [
            {'opcode': 3, 'stat_offset': 4, 'value': 9},
        ])

    def test_rejects_invalid_effect_opcode(self):
        base = 0x02000000
        image = bytearray(0x100)
        struct.pack_into('<IIIII', image, 0x20, 1, 0, base + 0x80, 0, 0)
        struct.pack_into('<HhHH', image, 0x80, 11, 1, 0, 0)
        with self.assertRaises(ValueError):
            parse_component_table(bytes(image), base + 0x20, 1, 0, base)


if __name__ == '__main__':
    unittest.main()
