import struct
import unittest

from tools.nds.content_map import (
    find_bey_resource_tables,
    lz11_decompress,
    parse_narc,
)


def make_literal_lz11(payload: bytes) -> bytes:
    out = bytearray([0x11])
    out += len(payload).to_bytes(3, "little")
    for pos in range(0, len(payload), 8):
        out.append(0)
        out += payload[pos:pos + 8]
    return bytes(out)


def make_one_file_narc(payload: bytes) -> bytes:
    # Standard NARC with one FAT entry and an empty filename table.
    btaf = b"BTAF" + struct.pack("<IHHII", 0x14, 1, 0, 0, len(payload))
    btnf_payload = struct.pack("<IHH", 8, 0, 1) + b"\0\0\0\0"
    btnf = b"BTNF" + struct.pack("<I", 8 + len(btnf_payload)) + btnf_payload
    gmif = b"GMIF" + struct.pack("<I", 8 + len(payload)) + payload
    total = 0x10 + len(btaf) + len(btnf) + len(gmif)
    header = b"NARC" + b"\xff\xfe" + struct.pack("<H", 0x0100)
    header += struct.pack("<IHH", total, 0x10, 3)
    return header + btaf + btnf + gmif


class ContentMapTests(unittest.TestCase):
    def test_lz11_literal_stream_round_trips(self):
        payload = b"BMD0DATA"
        self.assertEqual(lz11_decompress(make_literal_lz11(payload)), payload)

    def test_parse_narc_extracts_single_file(self):
        payload = make_literal_lz11(b"BMD0TEST")
        files = parse_narc(make_one_file_narc(payload))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["data"], payload)
        self.assertEqual(files[0]["start"], 0)
        self.assertEqual(files[0]["end"], len(payload))

    def test_find_bey_resource_tables_recovers_model_texture_and_usage(self):
        image = bytearray(0x600)
        ram = 0x02000000

        strings = {
            0x100: b"/bey/00_00.narc\0",
            0x120: b"/bey/01_00.narc\0",
            0x160: b"/bey/00_00t.narc\0",
            0x180: b"/bey/01_00t.narc\0",
            0x1c0: b"00_00t.bin\0",
            0x1e0: b"01_00t.bin\0",
        }
        for off, value in strings.items():
            image[off:off + len(value)] = value

        model_table = 0x300
        struct.pack_into("<II", image, model_table, ram + 0x100, ram + 0x120)

        texture_table = model_table + 8
        struct.pack_into("<III", image, texture_table, ram + 0x160, ram + 0x1c0, 0)
        struct.pack_into("<III", image, texture_table + 12, ram + 0x180, ram + 0x1e0, 0)

        usage_table = texture_table + 24
        # Two direct mappings plus one logical alias of group 0.
        struct.pack_into("<II", image, usage_table, ram + model_table, ram + texture_table)
        struct.pack_into("<II", image, usage_table + 8, ram + model_table + 4, ram + texture_table + 12)
        struct.pack_into("<II", image, usage_table + 16, ram + model_table, ram + texture_table)

        result = find_bey_resource_tables(bytes(image), ram_base=ram, min_model_entries=2)
        self.assertEqual(result["model_pointer_table"]["offset"], model_table)
        self.assertEqual(result["model_pointer_table"]["count"], 2)
        self.assertEqual(result["texture_descriptor_table"]["offset"], texture_table)
        self.assertEqual(result["texture_descriptor_table"]["count"], 2)
        self.assertEqual(result["usage_table"]["offset"], usage_table)
        self.assertEqual(result["usage_table"]["count"], 3)
        self.assertEqual(
            [(r["group"], r["start_index"], r["count"]) for r in result["category_runs"]],
            [(0, 0, 1), (1, 1, 1), (0, 2, 1)],
        )


if __name__ == "__main__":
    unittest.main()
