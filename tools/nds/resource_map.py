from __future__ import annotations

import argparse
import json
import re
import struct
from collections import Counter
from pathlib import Path

MODEL_RE = re.compile(rb"/bey/([0-9]{2})_([0-9]{2,3})\.narc\x00")
TEXTURE_RE = re.compile(rb"/bey/([0-9]{2})_([0-9]{2,3})t\.narc\x00")
MEMBER_RE = re.compile(rb"([0-9]{2})_([0-9]{2,3})t\.bin\x00")


def _strings(data: bytes, pattern: re.Pattern[bytes], ram_base: int) -> dict[int, str]:
    return {
        ram_base + match.start(): match.group()[:-1].decode("ascii")
        for match in pattern.finditer(data)
    }


def _longest_pointer_run(data: bytes, targets: dict[int, str]) -> tuple[int, list[str]]:
    best_offset = -1
    best: list[str] = []
    current_offset = -1
    current: list[str] = []
    for off in range(0, len(data) - 3, 4):
        value = struct.unpack_from("<I", data, off)[0]
        text = targets.get(value)
        if text is not None:
            if not current:
                current_offset = off
            current.append(text)
        else:
            if len(current) > len(best):
                best_offset, best = current_offset, current
            current_offset, current = -1, []
    if len(current) > len(best):
        best_offset, best = current_offset, current
    return best_offset, best


def _texture_runs(data: bytes, texture_paths: dict[int, str], member_names: dict[int, str]) -> tuple[int, list[dict]]:
    best_offset = -1
    best: list[dict] = []
    for start in range(0, len(data) - 11, 4):
        entries: list[dict] = []
        off = start
        while off + 12 <= len(data):
            path_ptr, member_ptr, reserved = struct.unpack_from("<III", data, off)
            path = texture_paths.get(path_ptr)
            member = member_names.get(member_ptr)
            if path is None or member is None or reserved != 0:
                break
            if path.rsplit("/", 1)[-1][:-5] != member[:-4]:
                break
            entries.append({"path": path, "member": member})
            off += 12
        if len(entries) > len(best):
            best_offset, best = start, entries
    return best_offset, best


def _prefix_counts(paths: list[str]) -> dict[str, int]:
    counts = Counter(path.split("/bey/", 1)[1].split("_", 1)[0] for path in paths)
    return dict(sorted(counts.items()))


def analyze_bey_lookup(arm9: bytes, ram_base: int = 0x02000000) -> dict:
    model_strings = _strings(arm9, MODEL_RE, ram_base)
    texture_strings = _strings(arm9, TEXTURE_RE, ram_base)
    member_strings = _strings(arm9, MEMBER_RE, ram_base)
    model_offset, model_entries = _longest_pointer_run(arm9, model_strings)
    texture_offset, texture_entries = _texture_runs(arm9, texture_strings, member_strings)
    return {
        "ram_base": ram_base,
        "model_string_count": len(model_strings),
        "texture_string_count": len(texture_strings),
        "texture_member_string_count": len(member_strings),
        "model_table": {
            "offset": model_offset,
            "runtime_address": ram_base + model_offset if model_offset >= 0 else None,
            "count": len(model_entries),
            "end_offset": model_offset + 4 * len(model_entries) if model_offset >= 0 else None,
            "prefix_counts": _prefix_counts(model_entries),
            "entries": model_entries,
        },
        "texture_table": {
            "offset": texture_offset,
            "runtime_address": ram_base + texture_offset if texture_offset >= 0 else None,
            "count": len(texture_entries),
            "end_offset": texture_offset + 12 * len(texture_entries) if texture_offset >= 0 else None,
            "prefix_counts": _prefix_counts([entry["path"] for entry in texture_entries]),
            "entries": texture_entries,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Map Beyblade ARM9 model and texture resource lookup tables")
    parser.add_argument("arm9", type=Path, help="decompressed ARM9 binary")
    parser.add_argument("--ram-base", type=lambda value: int(value, 0), default=0x02000000)
    parser.add_argument("--compact", action="store_true", help="omit full table entries")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze_bey_lookup(args.arm9.read_bytes(), args.ram_base)
    if args.compact:
        report["model_table"].pop("entries", None)
        report["texture_table"].pop("entries", None)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
