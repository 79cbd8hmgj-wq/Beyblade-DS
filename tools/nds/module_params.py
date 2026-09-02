from __future__ import annotations

import struct

MAGIC_BE = 0xDEC00621
MAGIC_LE = 0x2106C0DE


def find_module_params(image: bytes, ram_base: int = 0x02000000) -> dict:
    marker = struct.pack('<II', MAGIC_BE, MAGIC_LE)
    pos = image.find(marker)
    if pos < 28:
        raise ValueError('Nitro module parameters not found')
    offset = pos - 28
    if offset + 36 > len(image):
        raise ValueError('truncated Nitro module parameters')
    (
        autoload_list,
        autoload_list_end,
        autoload_start,
        static_bss_start,
        static_bss_end,
        compressed_static_end,
        sdk_version,
        magic_be,
        magic_le,
    ) = struct.unpack_from('<9I', image, offset)
    if (magic_be, magic_le) != (MAGIC_BE, MAGIC_LE):
        raise ValueError('invalid Nitro module parameter magic')
    list_off = autoload_list - ram_base
    list_end_off = autoload_list_end - ram_base
    source_off = autoload_start - ram_base
    if not (0 <= list_off <= list_end_off <= len(image)):
        raise ValueError('autoload list lies outside ARM9 image')
    if (list_end_off - list_off) % 12:
        raise ValueError('autoload list length is not a multiple of 12')
    if not (0 <= source_off <= len(image)):
        raise ValueError('autoload source lies outside ARM9 image')
    autoloads = []
    current_source = source_off
    for index, entry_off in enumerate(range(list_off, list_end_off, 12)):
        destination, size, bss_size = struct.unpack_from('<III', image, entry_off)
        if current_source + size > len(image):
            raise ValueError('autoload source extent lies outside ARM9 image')
        autoloads.append({
            'index': index,
            'list_offset': entry_off,
            'destination': destination,
            'size': size,
            'bss_size': bss_size,
            'source_offset': current_source,
            'source_end_offset': current_source + size,
        })
        current_source += size
    return {
        'offset': offset,
        'runtime_address': ram_base + offset,
        'ram_base': ram_base,
        'autoload_list': autoload_list,
        'autoload_list_end': autoload_list_end,
        'autoload_start': autoload_start,
        'static_bss_start': static_bss_start,
        'static_bss_end': static_bss_end,
        'compressed_static_end': compressed_static_end,
        'sdk_version': sdk_version,
        'magic_be': magic_be,
        'magic_le': magic_le,
        'autoloads': autoloads,
        'autoload_source_end_offset': current_source,
    }


def map_arm9_runtime(report: dict, address: int) -> dict:
    base = report['ram_base']
    if base <= address < report['static_bss_start']:
        return {'kind': 'static', 'file_offset': address - base}
    if report['static_bss_start'] <= address < report['static_bss_end']:
        return {'kind': 'bss', 'file_offset': None}
    for entry in report['autoloads']:
        start = entry['destination']
        data_end = start + entry['size']
        bss_end = data_end + entry['bss_size']
        if start <= address < data_end:
            return {
                'kind': 'autoload',
                'file_offset': entry['source_offset'] + (address - start),
                'autoload_index': entry['index'],
            }
        if data_end <= address < bss_end:
            return {'kind': 'autoload_bss', 'file_offset': None, 'autoload_index': entry['index']}
    return {'kind': 'unmapped', 'file_offset': None}
