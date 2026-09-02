#!/usr/bin/env python3
"""Parse Metal Masters character/loadout records from a decompressed ARM9 image.

The tool is read-only. It operates on a caller-supplied decompressed ARM9 file
and emits derived metadata; it never writes to a ROM image.
"""
from __future__ import annotations

import argparse
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path

ARM9_RAM_BASE = 0x02000000
LOADOUT_TABLE = 0x0205D834
LOADOUT_GROUPS = 40
LOADOUT_VARIANTS = 10
LOADOUT_STRIDE = 0x0C
LOADOUT_GROUP_STRIDE = LOADOUT_VARIANTS * LOADOUT_STRIDE
FACE_RING_MAP = 0x02059890
FACE_RING_COUNT = 127

CHARACTER_DEBUG_NAMES = (
    "GINGA", "TSUBASA", "MASAMUNE", "RYUGA", "KENTA", "KYOYA", "BENKEI",
    "HYOMA", "YUU", "SORA", "HIKARU", "RYUSEI", "DAIDOUJI", "MIZUTI",
    "WATARIGANI", "TOBIO", "RYUTAROU", "SAOTOME", "BUSUJIMA", "KUMASUKE",
    "MADOKA", "TAKERU", "REIKI", "HERIOS", "DJ", "ZAKO_A", "FURYO_A",
    "AGITO_BEF", "TI-YUN", "WAN", "NAIRU", "SI-ZA-", "WERUZ", "SOFY",
    "GEO", "GASURU", "AREKUSEI", "CHAU", "MEIMEI", "AGITO_AFT",
)


@dataclass(frozen=True)
class LoadoutRecord:
    group_index: int
    character_debug_name: str
    variant_index: int
    runtime_address: str
    energy_ring_id: int
    fusion_wheel_global_id: int
    fusion_wheel_local_id: int
    spin_track_global_id: int
    spin_track_local_id: int
    performance_tip_global_id: int
    performance_tip_local_id: int
    special_move_id_1based: int
    special_move_debug_index: int | None
    field_0a_u16: int
    face_resource_id: int
    energy_ring_resource_id: int


def _offset(runtime_address: int, size: int, image_size: int) -> int:
    off = runtime_address - ARM9_RAM_BASE
    if off < 0 or off + size > image_size:
        raise ValueError(
            f"runtime range 0x{runtime_address:08X}+0x{size:X} is outside ARM9 image"
        )
    return off


def parse_face_ring_map(image: bytes) -> list[tuple[int, int]]:
    off = _offset(FACE_RING_MAP, FACE_RING_COUNT * 8, len(image))
    return [
        struct.unpack_from("<II", image, off + index * 8)
        for index in range(FACE_RING_COUNT)
    ]


def parse_loadouts(
    image: bytes, *, require_identical_variants: bool = False
) -> list[LoadoutRecord]:
    table_size = LOADOUT_GROUPS * LOADOUT_GROUP_STRIDE
    off = _offset(LOADOUT_TABLE, table_size, len(image))
    face_ring = parse_face_ring_map(image)
    result: list[LoadoutRecord] = []

    for group in range(LOADOUT_GROUPS):
        group_off = off + group * LOADOUT_GROUP_STRIDE
        first = image[group_off : group_off + LOADOUT_STRIDE]
        for variant in range(LOADOUT_VARIANTS):
            rec_off = group_off + variant * LOADOUT_STRIDE
            raw = image[rec_off : rec_off + LOADOUT_STRIDE]
            if require_identical_variants and raw != first:
                raise ValueError(
                    f"group {group} variant {variant} differs from variant 0"
                )
            ring, wheel, track, tip, move, field_0a = struct.unpack_from(
                "<6H", raw
            )
            if not 0 <= ring < 127:
                raise ValueError(
                    f"group {group} variant {variant}: Energy Ring ID {ring} out of range"
                )
            if not 400 <= wheel < 501:
                raise ValueError(
                    f"group {group} variant {variant}: Fusion Wheel ID {wheel} out of range"
                )
            if not 600 <= track < 707:
                raise ValueError(
                    f"group {group} variant {variant}: Track ID {track} out of range"
                )
            if not 800 <= tip < 907:
                raise ValueError(
                    f"group {group} variant {variant}: Tip ID {tip} out of range"
                )
            face_resource, ring_resource = face_ring[ring]
            result.append(
                LoadoutRecord(
                    group_index=group,
                    character_debug_name=CHARACTER_DEBUG_NAMES[group],
                    variant_index=variant,
                    runtime_address=(
                        f"0x{LOADOUT_TABLE + group * LOADOUT_GROUP_STRIDE + variant * LOADOUT_STRIDE:08X}"
                    ),
                    energy_ring_id=ring,
                    fusion_wheel_global_id=wheel,
                    fusion_wheel_local_id=wheel - 400,
                    spin_track_global_id=track,
                    spin_track_local_id=track - 600,
                    performance_tip_global_id=tip,
                    performance_tip_local_id=tip - 800,
                    special_move_id_1based=move,
                    special_move_debug_index=(move - 1 if move else None),
                    field_0a_u16=field_0a,
                    face_resource_id=face_resource,
                    energy_ring_resource_id=ring_resource,
                )
            )
    return result


def build_report(image: bytes) -> dict:
    records = parse_loadouts(image, require_identical_variants=True)
    canonical = [record for record in records if record.variant_index == 0]
    field_0a_counts: dict[str, int] = {}
    for record in canonical:
        key = str(record.field_0a_u16)
        field_0a_counts[key] = field_0a_counts.get(key, 0) + 1
    return {
        "schema_version": 1,
        "table": {
            "runtime_start": f"0x{LOADOUT_TABLE:08X}",
            "end_exclusive": (
                f"0x{LOADOUT_TABLE + LOADOUT_GROUPS * LOADOUT_GROUP_STRIDE:08X}"
            ),
            "character_groups": LOADOUT_GROUPS,
            "variants_per_group": LOADOUT_VARIANTS,
            "record_stride": LOADOUT_STRIDE,
            "group_stride": LOADOUT_GROUP_STRIDE,
            "all_variants_identical_within_group": True,
        },
        "face_energy_ring_map": {
            "runtime_start": f"0x{FACE_RING_MAP:08X}",
            "count": FACE_RING_COUNT,
            "stride": 8,
            "record": ["face_resource_id", "energy_ring_resource_id"],
        },
        "field_statistics": {
            "special_move_id_1based": {
                "minimum": min(r.special_move_id_1based for r in canonical),
                "maximum": max(r.special_move_id_1based for r in canonical),
                "unique_count": len({r.special_move_id_1based for r in canonical}),
            },
            "field_0a_u16_counts": field_0a_counts,
        },
        "canonical_variant_zero": [asdict(record) for record in canonical],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "arm9", type=Path, help="decompressed Metal Masters ARM9 image"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.arm9.read_bytes())
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
