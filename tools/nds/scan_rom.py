#!/usr/bin/env python3
"""Compact Nintendo DS ROM scanner used by the Beyblade RE project.

It never modifies the source ROM. It reports header/CPU/FNT/FAT/overlay metadata,
NitroFS file hashes, and can BLZ-decompress ARM9 for executable comparisons.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_fnt(data: bytes, fnt_off: int, fnt_size: int) -> list[tuple[int, str]]:
    fnt = data[fnt_off : fnt_off + fnt_size]
    if len(fnt) < 8:
        return []
    _, _, dir_count = struct.unpack_from("<IHH", fnt, 0)
    dirs = []
    for index in range(dir_count):
        off = index * 8
        if off + 8 > len(fnt):
            break
        dirs.append(struct.unpack_from("<IHH", fnt, off))

    files: list[tuple[int, str]] = []

    def walk(dir_index: int, prefix: str) -> None:
        if not 0 <= dir_index < len(dirs):
            return
        subtable_off, first_file_id, _ = dirs[dir_index]
        pos = subtable_off
        file_id = first_file_id
        while pos < len(fnt):
            control = fnt[pos]
            pos += 1
            if control == 0:
                break
            is_dir = bool(control & 0x80)
            name_len = control & 0x7F
            name = fnt[pos : pos + name_len].decode("ascii", "replace")
            pos += name_len
            if is_dir:
                if pos + 2 > len(fnt):
                    break
                child = struct.unpack_from("<H", fnt, pos)[0]
                pos += 2
                walk(child - 0xF000, prefix + name + "/")
            else:
                files.append((file_id, prefix + name))
                file_id += 1

    walk(0, "")
    return files


def blz_decompress(data: bytes) -> bytes:
    """Decompress Nintendo backwards-LZ (BLZ/LZ-Overlay) data."""
    if len(data) < 4:
        raise ValueError("BLZ input too short")
    extra_size = int.from_bytes(data[-4:], "little")
    if extra_size == 0:
        return data[:-4]
    if len(data) < 8:
        raise ValueError("BLZ header too short")

    header_size = data[-5]
    compressed_size = int.from_bytes(data[-8:-5], "little")
    if header_size < 8 or header_size > len(data):
        raise ValueError("invalid BLZ header size")
    if any(byte != 0xFF for byte in data[-header_size:-8]):
        raise ValueError("invalid BLZ header padding")
    if compressed_size + header_size >= len(data):
        compressed_size = len(data) - header_size

    prefix_size = len(data) - header_size - compressed_size
    prefix = data[:prefix_size]
    source = data[prefix_size : prefix_size + compressed_size]
    output = bytearray(compressed_size + header_size + extra_size)

    written = 0
    read = 0
    flags = 0
    mask = 1
    while written < len(output):
        if mask == 1:
            if read >= compressed_size:
                raise ValueError("BLZ stream ended before flags")
            flags = source[-1 - read]
            read += 1
            mask = 0x80
        else:
            mask >>= 1

        if flags & mask:
            if read + 1 >= compressed_size:
                raise ValueError("BLZ stream ended inside back-reference")
            byte1 = source[compressed_size - 1 - read]
            read += 1
            byte2 = source[compressed_size - 1 - read]
            read += 1
            length = (byte1 >> 4) + 3
            displacement = (((byte1 & 0x0F) << 8) | byte2) + 3
            if displacement > written:
                if written < 2:
                    raise ValueError("invalid BLZ displacement")
                displacement = 2
            source_index = written - displacement
            for _ in range(length):
                if written >= len(output):
                    break
                output[-1 - written] = output[-1 - source_index]
                source_index += 1
                written += 1
        else:
            if read >= compressed_size:
                raise ValueError("BLZ stream ended inside literal")
            output[-1 - written] = source[-1 - read]
            read += 1
            written += 1

    return prefix + bytes(output)


def scan_rom(path: Path, include_files: bool = True) -> dict:
    data = path.read_bytes()
    if len(data) < 0x200:
        raise ValueError(f"{path}: file is too small to be an NDS ROM")
    header = data[:0x200]

    arm9_off, arm9_entry, arm9_ram, arm9_size = (u32(header, x) for x in (0x20, 0x24, 0x28, 0x2C))
    arm7_off, arm7_entry, arm7_ram, arm7_size = (u32(header, x) for x in (0x30, 0x34, 0x38, 0x3C))
    fnt_off, fnt_size = u32(header, 0x40), u32(header, 0x44)
    fat_off, fat_size = u32(header, 0x48), u32(header, 0x4C)
    ov9_off, ov9_size = u32(header, 0x50), u32(header, 0x54)
    ov7_off, ov7_size = u32(header, 0x58), u32(header, 0x5C)

    fat: list[tuple[int, int]] = []
    for off in range(fat_off, fat_off + fat_size, 8):
        if off + 8 > len(data):
            break
        fat.append(struct.unpack_from("<II", data, off))

    files = {}
    for file_id, name in parse_fnt(data, fnt_off, fnt_size):
        if file_id >= len(fat):
            continue
        start, end = fat[file_id]
        blob = data[start:end]
        files[name] = {
            "id": file_id,
            "start": start,
            "end": end,
            "size": end - start,
            "sha256": sha256(blob),
        }

    def overlay_table(off: int, size: int) -> list[dict]:
        result = []
        for pos in range(off, off + size, 32):
            if pos + 32 > len(data):
                break
            overlay_id, ram, ram_size, bss, init_start, init_end, file_id, reserved = struct.unpack_from("<8I", data, pos)
            record = {
                "id": overlay_id,
                "ram_address": ram,
                "ram_size": ram_size,
                "bss_size": bss,
                "static_init_start": init_start,
                "static_init_end": init_end,
                "file_id": file_id,
                "reserved": reserved,
            }
            if file_id < len(fat):
                start, end = fat[file_id]
                record.update({"rom_start": start, "rom_end": end, "file_size": end - start, "sha256": sha256(data[start:end])})
            result.append(record)
        return result

    arm9 = data[arm9_off : arm9_off + arm9_size]
    arm7 = data[arm7_off : arm7_off + arm7_size]
    arm9_decompressed_size = None
    try:
        arm9_decompressed_size = len(blz_decompress(arm9))
    except ValueError:
        pass

    result = {
        "file": path.name,
        "size": len(data),
        "sha256": sha256(data),
        "title": header[0:12].rstrip(b"\0").decode("ascii", "replace"),
        "game_code": header[0x0C:0x10].decode("ascii", "replace"),
        "maker_code": header[0x10:0x12].decode("ascii", "replace"),
        "unit_code": header[0x12],
        "rom_version": header[0x1E],
        "arm9": {"rom_offset": arm9_off, "entry": arm9_entry, "ram_address": arm9_ram, "size": arm9_size, "sha256": sha256(arm9), "blz_decompressed_size": arm9_decompressed_size},
        "arm7": {"rom_offset": arm7_off, "entry": arm7_entry, "ram_address": arm7_ram, "size": arm7_size, "sha256": sha256(arm7)},
        "fnt": {"offset": fnt_off, "size": fnt_size},
        "fat": {"offset": fat_off, "size": fat_size},
        "arm9_overlays": overlay_table(ov9_off, ov9_size),
        "arm7_overlays": overlay_table(ov7_off, ov7_size),
        "nitrofs_file_count": len(files),
        "used_rom_size": u32(header, 0x80),
    }
    if include_files:
        result["files"] = files
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", nargs="+", type=Path)
    parser.add_argument("--compact", action="store_true", help="omit per-file NitroFS hashes")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = [scan_rom(path, include_files=not args.compact) for path in args.rom]
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
