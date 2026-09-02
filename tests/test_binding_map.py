import struct
import unittest

from tools.nds.binding_map import find_binding_runs, find_debug_enum_runs


class BindingMapTests(unittest.TestCase):
    def test_finds_pair_run_targeting_model_entries_and_texture_records(self):
        base = 0x02000000
        blob = bytearray(0x500)
        model_base = base + 0x100
        texture_base = base + 0x200
        pairs = [
            (model_base + 8, texture_base + 24),
            (model_base + 0, texture_base + 0),
            (model_base + 4, texture_base + 12),
        ]
        for index, pair in enumerate(pairs):
            struct.pack_into('<II', blob, 0x300 + index * 8, *pair)

        runs = find_binding_runs(bytes(blob), base, model_base, 3, texture_base, 3, min_records=3)

        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['runtime_start'], base + 0x300)
        self.assertEqual(runs[0]['count'], 3)
        self.assertEqual([r['model_index'] for r in runs[0]['records']], [2, 0, 1])
        self.assertEqual([r['texture_index'] for r in runs[0]['records']], [2, 0, 1])

    def test_finds_debug_pointer_id_enum_run(self):
        base = 0x02100000
        blob = bytearray(0x200)
        strings = [(0x100, b'ALPHA_A\0'), (0x110, b'ALPHA_B\0'), (0x120, b'BETA_A\0')]
        for off, text in strings:
            blob[off:off + len(text)] = text
        for i, (off, _) in enumerate(strings):
            struct.pack_into('<II', blob, 0x40 + i * 8, base + off, 10 + i)

        runs = find_debug_enum_runs(bytes(blob), base, max_value=0x100, min_records=3)

        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['runtime_start'], base + 0x40)
        self.assertEqual([x['text'] for x in runs[0]['records']], ['ALPHA_A', 'ALPHA_B', 'BETA_A'])
        self.assertEqual([x['value'] for x in runs[0]['records']], [10, 11, 12])


if __name__ == '__main__':
    unittest.main()
