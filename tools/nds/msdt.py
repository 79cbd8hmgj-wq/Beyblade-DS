#!/usr/bin/env python3
"""Read-only parser for the Beyblade DS MSDT message container."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


def parse_msdt(data: bytes) -> dict:
    if len(data) < 4:
        raise ValueError("MSDT file too short")
    marker = struct.unpack_from("<I", data, 0)[0]
    if marker == 0:
        raise ValueError("invalid MSDT marker")
    count = marker - 1
    table_size = 4 + count * 4
    if table_size > len(data):
        raise ValueError("truncated MSDT message table")
    payload = data[table_size:]
    if len(payload) & 1:
        raise ValueError("MSDT payload has odd byte length")
    units = struct.unpack(f"<{len(payload)//2}H", payload) if payload else ()
    messages = []
    previous_end = -1
    for index in range(count):
        bank, end_unit = struct.unpack_from("<HH", data, 4 + index * 4)
        if end_unit < previous_end:
            raise ValueError("MSDT end offsets are not monotonic")
        if end_unit >= len(units):
            raise ValueError("MSDT end offset lies outside payload")
        start_unit = previous_end + 1
        messages.append({
            "index": index,
            "bank": bank,
            "start_unit": start_unit,
            "end_unit_inclusive": end_unit,
            "units": list(units[start_unit:end_unit + 1]),
        })
        previous_end = end_unit
    if messages and previous_end != len(units) - 1:
        raise ValueError("MSDT message table does not consume the payload")
    if not messages and units:
        raise ValueError("MSDT has payload but no messages")
    return {
        "marker": marker,
        "message_count": count,
        "table_size": table_size,
        "payload_units": len(units),
        "messages": messages,
    }


def decode_asciiish(units: list[int]) -> str:
    """Best-effort display decoder for the Latin message subset.

    The game uses 16-bit glyph/control codes, not plain UTF-16. Unknown/control
    units are omitted rather than assigned unsupported semantics.
    """
    out: list[str] = []
    for unit in units:
        if unit in (0x8001, 0x8002, 0x8003, 0x8004, 0x8005):
            continue
        if unit == 0:
            out.append(" ")
        elif unit in (0x0C, 0x0E):
            out.append("\n")
        elif 33 <= unit <= 58:
            out.append(chr(unit + 32))
        elif 32 <= unit < 127:
            out.append(chr(unit))
    return "".join(out).strip()


def summarize(data: bytes) -> dict:
    parsed = parse_msdt(data)
    return {
        "marker": parsed["marker"],
        "message_count": parsed["message_count"],
        "table_size": parsed["table_size"],
        "payload_units": parsed["payload_units"],
        "banks": sorted({message["bank"] for message in parsed["messages"]}),
        "messages": [
            {
                "index": message["index"],
                "bank": message["bank"],
                "start_unit": message["start_unit"],
                "end_unit_inclusive": message["end_unit_inclusive"],
                "text_asciiish": decode_asciiish(message["units"]),
            }
            for message in parsed["messages"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("msdt", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = summarize(args.msdt.read_bytes())
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
