import struct
import unittest

from tools.nds.loadout_map import (
    ARM9_RAM_BASE,
    FACE_RING_COUNT,
    FACE_RING_MAP,
    LOADOUT_GROUPS,
    LOADOUT_GROUP_STRIDE,
    LOADOUT_STRIDE,
    LOADOUT_TABLE,
    LOADOUT_VARIANTS,
    build_report,
    parse_loadouts,
)


def synthetic_image() -> bytearray:
    end = max(
        FACE_RING_MAP + FACE_RING_COUNT * 8,
        LOADOUT_TABLE + LOADOUT_GROUPS * LOADOUT_GROUP_STRIDE,
    )
    image = bytearray(end - ARM9_RAM_BASE)
    face_off = FACE_RING_MAP - ARM9_RAM_BASE
    for index in range(FACE_RING_COUNT):
        struct.pack_into(
            "<II", image, face_off + index * 8, index + 10, index + 100
        )
    loadout_off = LOADOUT_TABLE - ARM9_RAM_BASE
    for group in range(LOADOUT_GROUPS):
        raw = struct.pack(
            "<6H",
            group % 127,
            400 + group % 101,
            600 + group % 107,
            800 + group % 107,
            1 + group % 37,
            11 if group in (24, 25) else 0,
        )
        for variant in range(LOADOUT_VARIANTS):
            start = (
                loadout_off
                + group * LOADOUT_GROUP_STRIDE
                + variant * LOADOUT_STRIDE
            )
            image[start : start + LOADOUT_STRIDE] = raw
    return image


class LoadoutMapTests(unittest.TestCase):
    def test_parses_all_records_and_derives_local_ids(self):
        records = parse_loadouts(
            bytes(synthetic_image()), require_identical_variants=True
        )
        self.assertEqual(len(records), 400)
        record = records[25 * 10]
        self.assertEqual(record.group_index, 25)
        self.assertEqual(record.character_debug_name, "ZAKO_A")
        self.assertEqual(record.fusion_wheel_local_id, 25)
        self.assertEqual(record.spin_track_local_id, 25)
        self.assertEqual(record.performance_tip_local_id, 25)
        self.assertEqual(record.special_move_debug_index, 25)
        self.assertEqual(record.field_0a_u16, 11)
        self.assertEqual(record.face_resource_id, 35)
        self.assertEqual(record.energy_ring_resource_id, 125)

    def test_rejects_variant_mismatch_when_requested(self):
        image = synthetic_image()
        off = LOADOUT_TABLE - ARM9_RAM_BASE + LOADOUT_STRIDE
        struct.pack_into("<H", image, off, 3)
        with self.assertRaisesRegex(ValueError, "variant 1 differs"):
            parse_loadouts(bytes(image), require_identical_variants=True)

    def test_report_has_canonical_40_rows(self):
        report = build_report(bytes(synthetic_image()))
        self.assertEqual(len(report["canonical_variant_zero"]), 40)
        self.assertTrue(report["table"]["all_variants_identical_within_group"])
        self.assertEqual(
            report["field_statistics"]["field_0a_u16_counts"],
            {"0": 38, "11": 2},
        )


if __name__ == "__main__":
    unittest.main()
