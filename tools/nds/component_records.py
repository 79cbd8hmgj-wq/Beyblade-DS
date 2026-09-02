from __future__ import annotations

import struct

RECORD_SIZE = 20


def _runtime_to_offset(address: int, ram_base: int, image_len: int) -> int:
    offset = address - ram_base
    if not 0 <= offset < image_len:
        raise ValueError(f'runtime pointer 0x{address:08X} lies outside ARM9 image')
    return offset


def parse_effect_script(image: bytes, pointer: int, ram_base: int = 0x02000000) -> list[dict]:
    if pointer == 0:
        return []
    offset = _runtime_to_offset(pointer, ram_base, len(image))
    effects = []
    while True:
        if offset + 4 > len(image):
            raise ValueError('truncated component effect script')
        opcode, value = struct.unpack_from('<Hh', image, offset)
        if opcode == 0:
            return effects
        if not 1 <= opcode <= 10:
            raise ValueError(f'invalid component effect opcode {opcode}')
        effects.append({'opcode': opcode, 'stat_offset': (opcode - 1) * 2, 'value': value})
        offset += 4


def parse_component_table(
    image: bytes,
    table_address: int,
    count: int,
    selection_base: int,
    ram_base: int = 0x02000000,
) -> list[dict]:
    table_offset = _runtime_to_offset(table_address, ram_base, len(image))
    end = table_offset + count * RECORD_SIZE
    if count < 0 or end > len(image):
        raise ValueError('component table lies outside ARM9 image')
    records = []
    for index in range(count):
        offset = table_offset + index * RECORD_SIZE
        field_00, field_04, primary_ptr, secondary_ptr, field_10 = struct.unpack_from('<5I', image, offset)
        records.append({
            'index': index,
            'selection_id': selection_base + index,
            'runtime_address': table_address + index * RECORD_SIZE,
            'field_00_u32': field_00,
            'field_04_bytes': list(field_04.to_bytes(4, 'little')),
            'primary_effect_ptr': primary_ptr,
            'secondary_effect_ptr': secondary_ptr,
            'field_10_bytes': list(field_10.to_bytes(4, 'little')),
            'primary_effects': parse_effect_script(image, primary_ptr, ram_base),
            'secondary_effects': parse_effect_script(image, secondary_ptr, ram_base),
        })
    return records
