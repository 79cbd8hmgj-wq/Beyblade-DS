import struct
import unittest

from tools.nds.module_params import find_module_params, map_arm9_runtime


class ModuleParamsTests(unittest.TestCase):
    def test_maps_static_bss_and_autoload_sources(self):
        base = 0x02000000
        image = bytearray(0x400)
        params_off = 0x40
        words = [
            base + 0x3E8,  # autoload list
            base + 0x400,  # autoload list end
            base + 0x300,  # autoload source start
            base + 0x300,  # static BSS start
            0x02100000,    # static BSS end
            base + 0x280,  # compressed static end
            0x04027539,
            0xDEC00621,
            0x2106C0DE,
        ]
        struct.pack_into('<9I', image, params_off, *words)
        struct.pack_into('<III', image, 0x3E8, 0x01FF8000, 0x80, 0)
        struct.pack_into('<III', image, 0x3F4, 0x027E0000, 0x68, 0x100)

        report = find_module_params(bytes(image), base)

        self.assertEqual(report['offset'], params_off)
        self.assertEqual(report['static_bss_start'], base + 0x300)
        self.assertEqual(report['autoloads'][0]['source_offset'], 0x300)
        self.assertEqual(report['autoloads'][1]['source_offset'], 0x380)
        self.assertEqual(report['autoloads'][1]['destination'], 0x027E0000)
        self.assertEqual(map_arm9_runtime(report, base + 0x250), {'kind': 'static', 'file_offset': 0x250})
        self.assertEqual(map_arm9_runtime(report, base + 0x350), {'kind': 'bss', 'file_offset': None})
        self.assertEqual(map_arm9_runtime(report, 0x01FF8010), {'kind': 'autoload', 'file_offset': 0x310, 'autoload_index': 0})
        self.assertEqual(map_arm9_runtime(report, 0x027E0070), {'kind': 'autoload_bss', 'file_offset': None, 'autoload_index': 1})


if __name__ == '__main__':
    unittest.main()
