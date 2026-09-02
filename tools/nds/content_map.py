#!/usr/bin/env python3
"""Nintendo DS content-structure helpers for the Beyblade RE project.

The functions in this module operate on immutable byte strings. They parse
standard NARC containers, Nintendo LZ11 streams, and the ARM9 Bey resource
lookup structures used by the Metal Fusion / Metal Masters engine lineage.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"u32 offset out of range: 0x{offset:X}")
    return struct.unpack_from("<I", data, offset)[0]


def _cstring(data: bytes, offset: int, limit: int = 512) -> str | None:
    if offset < 0 or offset >= len(data):
        return None
    end = data.find(b"\0", offset, min(len(data), offset + limit))
    if end < 0:
        return None
    raw = data[offset:end]
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError:
        return None


def lz11_decompress(data: bytes, max_output: int = 64 * 1024 * 1024) -> bytes:
    """Decompress a Nintendo DS LZ11 stream."""
    if len(data) < 4 or data[0] != 0x11:
        raise ValueError("not an LZ11 stream")
    out_size = int.from_bytes(data[1:4], "little")
    pos = 4
    if out_size == 0:
        if len(data) < 8:
            raise ValueError("truncated extended LZ11 header")
        out_size = int.from_bytes(data[4:8], "little")
        pos = 8
    if out_size > max_output:
        raise ValueError(f"unreasonable LZ11 output size: {out_size}")

    out = bytearray()
    while len(out) < out_size:
        if pos >= len(data):
            raise ValueError("truncated LZ11 flags")
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= out_size:
                break
            if not (flags & (1 << bit)):
                if pos >= len(data):
                    raise ValueError("truncated LZ11 literal")
                out.append(data[pos])
                pos += 1
                continue

            if pos >= len(data):
                raise ValueError("truncated LZ11 back-reference")
            first = data[pos]
            hi = first >> 4
            if hi == 0:
                if pos + 3 > len(data):
                    raise ValueError("truncated LZ11 medium back-reference")
                second, third = data[pos + 1], data[pos + 2]
                length = (((first & 0x0F) << 4) | (second >> 4)) + 0x11
                displacement = (((second & 0x0F) << 8) | third) + 1
                pos += 3
            elif hi == 1:
                if pos + 4 > len(data):
                    raise ValueError("truncated LZ11 long back-reference")
                second, third, fourth = data[pos + 1], data[pos + 2], data[pos + 3]
                length = (
                    ((first & 0x0F) << 12) | (second << 4) | (third >> 4)
                ) + 0x111
                displacement = (((third & 0x0F) << 8) | fourth) + 1
                pos += 4
            else:
                if pos + 2 > len(data):
                    raise ValueError("truncated LZ11 short back-reference")
                second = data[pos + 1]
                length = hi + 1
                displacement = (((first & 0x0F) << 8) | second) + 1
                pos += 2

            if displacement <= 0 or displacement > len(out):
                raise ValueError(
                    f"invalid LZ11 displacement {displacement} at output {len(out)}"
                )
            for _ in range(length):
                if len(out) >= out_size:
                    break
                out.append(out[-displacement])

    return bytes(out)


def parse_narc(data: bytes) -> list[dict]:
    """Return member extents/data from a standard Nintendo NARC container."""
    if len(data) < 0x10 or data[:4] != b"NARC":
        raise ValueError("not a NARC container")
    total_size = _u32(data, 8)
    header_size = struct.unpack_from("<H", data, 0x0C)[0]
    section_count = struct.unpack_from("<H", data, 0x0E)[0]
    if header_size < 0x10 or header_size > len(data):
        raise ValueError("invalid NARC header size")
    if total_size > len(data) or total_size < header_size:
        raise ValueError("invalid NARC total size")

    sections: dict[bytes, tuple[int, int]] = {}
    pos = header_size
    for _ in range(section_count):
        if pos + 8 > total_size:
            raise ValueError("truncated NARC section header")
        magic = data[pos:pos + 4]
        size = _u32(data, pos + 4)
        if size < 8 or pos + size > total_size:
            raise ValueError("invalid NARC section size")
        sections[magic] = (pos, size)
        pos += size

    if b"BTAF" not in sections or b"GMIF" not in sections:
        raise ValueError("NARC missing BTAF or GMIF")
    fat_pos, fat_size = sections[b"BTAF"]
    gmif_pos, gmif_size = sections[b"GMIF"]
    if fat_size < 12:
        raise ValueError("truncated NARC BTAF")
    count = struct.unpack_from("<H", data, fat_pos + 8)[0]
    if 12 + count * 8 > fat_size:
        raise ValueError("NARC BTAF entry count exceeds section")
    payload_start = gmif_pos + 8
    payload_size = gmif_size - 8

    result = []
    for index in range(count):
        entry = fat_pos + 12 + index * 8
        start, end = struct.unpack_from("<II", data, entry)
        if start > end or end > payload_size:
            raise ValueError(f"NARC member {index} outside GMIF")
        result.append({
            "index": index,
            "start": start,
            "end": end,
            "size": end - start,
            "data": data[payload_start + start:payload_start + end],
        })
    return result


_BEY_PATH_RE = re.compile(rb"/bey/([0-9]{2})_([^\x00/]+)\.narc\x00")


def _collect_bey_paths(image: bytes, ram_base: int) -> dict[int, str]:
    paths: dict[int, str] = {}
    for match in _BEY_PATH_RE.finditer(image):
        paths[ram_base + match.start()] = match.group(0)[:-1].decode("ascii")
    return paths


def _path_group(path: str) -> int:
    match = re.match(r"^/bey/([0-9]{2})_", path)
    if not match:
        raise ValueError(f"not a grouped Bey path: {path}")
    return int(match.group(1))


def _is_texture_path(path: str) -> bool:
    return path[:-5].endswith("t")


def find_bey_resource_tables(
    arm9: bytes,
    *,
    ram_base: int = 0x02000000,
    min_model_entries: int = 32,
) -> dict:
    """Locate the inherited Bey model/texture/logical-usage lookup tables."""
    path_by_address = _collect_bey_paths(arm9, ram_base)
    model_addresses = {
        addr for addr, path in path_by_address.items() if not _is_texture_path(path)
    }
    texture_addresses = {
        addr for addr, path in path_by_address.items() if _is_texture_path(path)
    }
    if not model_addresses or not texture_addresses:
        raise ValueError("Bey model/texture path strings were not found")

    best_start = None
    best_count = 0
    off = 0
    while off + 4 <= len(arm9):
        if _u32(arm9, off) not in model_addresses:
            off += 4
            continue
        start = off
        count = 0
        while off + 4 <= len(arm9) and _u32(arm9, off) in model_addresses:
            count += 1
            off += 4
        if count > best_count:
            best_start, best_count = start, count
    if best_start is None or best_count < min_model_entries:
        raise ValueError(
            f"no Bey model pointer run with at least {min_model_entries} entries"
        )

    model_start = best_start
    model_end = model_start + best_count * 4
    model_paths = [
        path_by_address[_u32(arm9, model_start + i * 4)]
        for i in range(best_count)
    ]

    texture_start = model_end
    texture_records: list[dict] = []
    pos = texture_start
    while pos + 12 <= len(arm9):
        path_ptr, name_ptr, zero = struct.unpack_from("<III", arm9, pos)
        if path_ptr not in texture_addresses or zero != 0:
            break
        name = _cstring(arm9, name_ptr - ram_base)
        if name is None or not name.endswith(".bin"):
            break
        texture_records.append({
            "index": len(texture_records),
            "offset": pos,
            "path": path_by_address[path_ptr],
            "name": name,
        })
        pos += 12
    if len(texture_records) != best_count:
        raise ValueError(
            "model pointer count and adjacent texture descriptor count differ: "
            f"{best_count} vs {len(texture_records)}"
        )
    texture_end = pos

    model_table_runtime = ram_base + model_start
    texture_table_runtime = ram_base + texture_start
    usage_start = texture_end
    usage_records: list[dict] = []
    pos = usage_start
    while pos + 8 <= len(arm9):
        model_entry_ptr, texture_entry_ptr = struct.unpack_from("<II", arm9, pos)
        model_delta = model_entry_ptr - model_table_runtime
        texture_delta = texture_entry_ptr - texture_table_runtime
        if (
            model_delta < 0
            or model_delta >= best_count * 4
            or model_delta % 4
            or texture_delta < 0
            or texture_delta >= best_count * 12
            or texture_delta % 12
        ):
            break
        model_index = model_delta // 4
        texture_index = texture_delta // 12
        model_path = model_paths[model_index]
        texture_path = texture_records[texture_index]["path"]
        usage_records.append({
            "index": len(usage_records),
            "offset": pos,
            "model_index": model_index,
            "texture_index": texture_index,
            "model_path": model_path,
            "texture_path": texture_path,
            "group": _path_group(model_path),
        })
        pos += 8
    if not usage_records:
        raise ValueError("no logical Bey usage records followed the texture table")

    runs: list[dict] = []
    for record in usage_records:
        group = record["group"]
        if not runs or runs[-1]["group"] != group:
            runs.append({
                "group": group,
                "start_index": record["index"],
                "count": 1,
            })
        else:
            runs[-1]["count"] += 1
    for run in runs:
        start = run["start_index"]
        end = start + run["count"]
        subset = usage_records[start:end]
        run["unique_model_count"] = len({r["model_index"] for r in subset})
        run["runtime_address"] = ram_base + usage_start + start * 8

    return {
        "model_pointer_table": {
            "offset": model_start,
            "runtime_address": ram_base + model_start,
            "count": best_count,
            "end_offset": model_end,
        },
        "texture_descriptor_table": {
            "offset": texture_start,
            "runtime_address": ram_base + texture_start,
            "count": len(texture_records),
            "stride": 12,
            "end_offset": texture_end,
        },
        "usage_table": {
            "offset": usage_start,
            "runtime_address": ram_base + usage_start,
            "count": len(usage_records),
            "stride": 8,
            "end_offset": usage_start + len(usage_records) * 8,
        },
        "category_runs": runs,
        "model_paths": model_paths,
        "texture_records": texture_records,
        "usage_records": usage_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Map Bey model/texture lookup tables in a decompressed NDS ARM9 image."
    )
    parser.add_argument("arm9", type=Path, help="decompressed ARM9 binary")
    parser.add_argument("--ram-base", type=lambda s: int(s, 0), default=0x02000000)
    parser.add_argument("--min-model-entries", type=int, default=32)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="omit per-model, texture, and logical-usage records",
    )
    args = parser.parse_args()

    result = find_bey_resource_tables(
        args.arm9.read_bytes(),
        ram_base=args.ram_base,
        min_model_entries=args.min_model_entries,
    )
    if args.compact:
        result = {
            key: value
            for key, value in result.items()
            if key not in {"model_paths", "texture_records", "usage_records"}
        }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
