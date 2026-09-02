from __future__ import annotations

import struct


def find_binding_runs(
    blob: bytes,
    image_base: int,
    model_table_base: int,
    model_count: int,
    texture_table_base: int,
    texture_count: int,
    *,
    min_records: int = 2,
) -> list[dict]:
    model_end = model_table_base + model_count * 4
    texture_end = texture_table_base + texture_count * 12

    def decode_record(offset: int):
        if offset + 8 > len(blob):
            return None
        model_ptr, texture_ptr = struct.unpack_from('<II', blob, offset)
        if not (model_table_base <= model_ptr < model_end):
            return None
        if (model_ptr - model_table_base) % 4:
            return None
        if not (texture_table_base <= texture_ptr < texture_end):
            return None
        if (texture_ptr - texture_table_base) % 12:
            return None
        return {
            'offset': offset,
            'runtime_address': image_base + offset,
            'model_entry_pointer': model_ptr,
            'texture_descriptor_pointer': texture_ptr,
            'model_index': (model_ptr - model_table_base) // 4,
            'texture_index': (texture_ptr - texture_table_base) // 12,
        }

    runs: list[dict] = []
    offset = 0
    while offset + 8 <= len(blob):
        first = decode_record(offset)
        if first is None:
            offset += 4
            continue
        records = []
        start = offset
        while offset + 8 <= len(blob):
            record = decode_record(offset)
            if record is None:
                break
            records.append(record)
            offset += 8
        if len(records) >= min_records:
            runs.append({
                'offset': start,
                'runtime_start': image_base + start,
                'count': len(records),
                'stride': 8,
                'records': records,
            })
        if offset == start:
            offset += 4
    return runs


def _read_ascii_string(blob: bytes, image_base: int, pointer: int, max_length: int = 128) -> str | None:
    offset = pointer - image_base
    if offset < 0 or offset >= len(blob):
        return None
    end = blob.find(b'\0', offset, min(len(blob), offset + max_length))
    if end < 0 or end == offset:
        return None
    raw = blob[offset:end]
    if any(byte < 0x20 or byte > 0x7E for byte in raw):
        return None
    try:
        return raw.decode('ascii').rstrip()
    except UnicodeDecodeError:
        return None


def find_debug_enum_runs(
    blob: bytes,
    image_base: int,
    *,
    max_value: int = 0x1FF,
    min_records: int = 3,
) -> list[dict]:
    runs: list[dict] = []
    for phase in (0, 4):
        offset = phase
        while offset + 8 <= len(blob):
            pointer, value = struct.unpack_from('<II', blob, offset)
            text = _read_ascii_string(blob, image_base, pointer)
            if text is None or value > max_value:
                offset += 8
                continue
            start = offset
            records = []
            while offset + 8 <= len(blob):
                pointer, value = struct.unpack_from('<II', blob, offset)
                text = _read_ascii_string(blob, image_base, pointer)
                if text is None or value > max_value:
                    break
                records.append({
                    'offset': offset,
                    'runtime_address': image_base + offset,
                    'string_pointer': pointer,
                    'text': text,
                    'value': value,
                })
                offset += 8
            if len(records) >= min_records:
                runs.append({
                    'offset': start,
                    'runtime_start': image_base + start,
                    'count': len(records),
                    'stride': 8,
                    'records': records,
                })
            if offset == start:
                offset += 8
    dedup = {}
    for run in runs:
        current = dedup.get(run['offset'])
        if current is None or run['count'] > current['count']:
            dedup[run['offset']] = run
    return [dedup[key] for key in sorted(dedup)]
