from __future__ import annotations


def blz_decompress(data: bytes) -> bytes:
    """Decompress Nintendo backwards-LZ used by DS ARM9/overlay binaries.

    The 24-bit compressed-length footer field includes the BLZ header itself.
    Bytes before that compressed region are an uncompressed prefix and must be
    copied verbatim.
    """
    if len(data) < 4:
        raise ValueError("BLZ input too short")
    extra_size = int.from_bytes(data[-4:], "little")
    if extra_size == 0:
        return data[:-4]
    if len(data) < 8:
        raise ValueError("BLZ header too short")

    header_size = data[-5]
    compressed_total = int.from_bytes(data[-8:-5], "little")
    if header_size < 8 or header_size > len(data):
        raise ValueError("invalid BLZ header size")
    if compressed_total < header_size or compressed_total > len(data):
        raise ValueError("invalid BLZ compressed size")
    if any(byte != 0xFF for byte in data[-header_size:-8]):
        raise ValueError("invalid BLZ header padding")

    prefix_size = len(data) - compressed_total
    compressed_size = compressed_total - header_size
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
            byte1 = source[-1 - read]
            read += 1
            byte2 = source[-1 - read]
            read += 1
            length = (byte1 >> 4) + 3
            displacement = (((byte1 & 0x0F) << 8) | byte2) + 3
            if displacement > written:
                raise ValueError("invalid BLZ displacement")
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
