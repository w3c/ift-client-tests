import struct

from testCaseGeneratorLib.constants import (
    IFT_ENTRIES_OFFSET_END,
    IFT_ENTRIES_OFFSET_START,
    IFT_ENTRY_ID_STRING_OFFSET_END,
    IFT_ENTRY_ID_STRING_OFFSET_START,
    IFT_FORMAT_OFFSET,
    IFT_URL_TEMPLATE_LENGTH_OFFSET,
    IFT_URL_TEMPLATE_START,
)


def replace_format2_url_template(iftData, new_template):
    """Replace the Format 2 patch map URL template and fix patch-map-relative offsets.

    Layout (§5.3.2 Patch Map Table: Format 2, https://www.w3.org/TR/IFT/#patch-map-format-2):
    bytes 0–32: format … entryIdStringData; 33–34: urlTemplateLength; 35+: urlTemplate;
    then optional cffCharStringsOffset / cff2CharStringsOffset (flags), then remaining
    table bytes (e.g. mapping entries at ``entries``).

    Only ``entries`` and ``entryIdStringData`` in the header are adjusted when template
    length changes; they are Offset32 values from the start of this table. Optional
    CFF charstring offsets immediately after ``urlTemplate`` are copied unchanged —
    they are relative to the CFF/CFF2 table, not the patch map.

    Expand URL Template: https://www.w3.org/TR/IFT/#url-templates
    """
    iftData = bytearray(iftData)
    if iftData[IFT_FORMAT_OFFSET] != 2:
        raise ValueError("Expected IFT patch map format 2")
    old_len = int.from_bytes(
        iftData[IFT_URL_TEMPLATE_LENGTH_OFFSET : IFT_URL_TEMPLATE_LENGTH_OFFSET + 2], "big"
    )
    new_len = len(new_template)
    delta = new_len - old_len
    suffix_start = IFT_URL_TEMPLATE_START + old_len

    new_patch_map = bytearray()
    new_patch_map.extend(iftData[:IFT_URL_TEMPLATE_LENGTH_OFFSET])
    new_patch_map.extend(struct.pack(">H", new_len))
    new_patch_map.extend(new_template)
    new_patch_map.extend(iftData[suffix_start:])

    if delta != 0:
        def adjust_patch_map_offset(offset):
            if offset != 0 and offset >= suffix_start:
                return offset + delta
            return offset

        entries_offset = int.from_bytes(
            new_patch_map[IFT_ENTRIES_OFFSET_START:IFT_ENTRIES_OFFSET_END], "big"
        )

        # update the entries offset
        new_patch_map[IFT_ENTRIES_OFFSET_START:IFT_ENTRIES_OFFSET_END] = struct.pack(
            ">I", adjust_patch_map_offset(entries_offset)
        )
        entry_id_offset = int.from_bytes(
            new_patch_map[IFT_ENTRY_ID_STRING_OFFSET_START:IFT_ENTRY_ID_STRING_OFFSET_END],
            "big",
        )
        # update the entry id string offset
        new_patch_map[IFT_ENTRY_ID_STRING_OFFSET_START:IFT_ENTRY_ID_STRING_OFFSET_END] = (
            struct.pack(">I", adjust_patch_map_offset(entry_id_offset))
        )

    return new_patch_map

import base64


def decode_id32_to_int(id32_str):
    """
    Decode a base32hex string (no padding, per spec §5.3.3) to an integer.

    Base32hex uses alphabet 0-9, A-V (RFC 4648 §7).
    Examples: '04' -> 1,  '08' -> 2,  '0C' -> 3,  '0G' -> 4
    """
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUV'
    id32_str = id32_str.upper()
    n_chars = len(id32_str)
    value = 0
    for c in id32_str:
        value = value * 32 + alphabet.index(c)
    # Strip trailing padding bits that were added during encoding.
    # Encoding pads the last group to 5 bits; we strip those extra bits here.
    n_bits = 5 * n_chars
    padding_bits = n_bits % 8
    if padding_bits:
        value >>= padding_bits
    return value


def id32_no_strip(entry_id_int):
    """
    Encode an integer as base32hex WITHOUT stripping leading zero bytes.

    The spec (conform-entry-id-must-be-converted) requires leading zeros to be
    stripped. This helper deliberately omits that step, producing the 'wrong'
    encoding used in negative tests that verify clients strip leading zeros.
    Example: integer 1 -> big-endian [0x00, 0x00, 0x00, 0x01] -> '0000008'
             (correct encoding strips to [0x01] -> '04')
    """
    # Always use 4 bytes (big-endian 32-bit), no stripping
    b = entry_id_int.to_bytes(4, 'big')
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUV'
    result = ''
    bits = 0
    num_bits = 0
    for byte in b:
        bits = (bits << 8) | byte
        num_bits += 8
        while num_bits >= 5:
            num_bits -= 5
            result += alphabet[(bits >> num_bits) & 0x1F]
    if num_bits > 0:
        result += alphabet[(bits << (5 - num_bits)) & 0x1F]
    return result


def compute_id64_file_name(entry_id_int):
    """
    Compute the base64url patch file name for an integer entry ID (id64 opcode).

    Per the spec (conform-entry-id-converted): integer -> big-endian 32-bit ->
    strip leading zero bytes -> base64url encode. Returns the raw base64url
    string with actual '=' padding chars (not '%3D'), suitable for use as a
    file name on disk. The HTTP server decodes a client's '%3D'-encoded request
    back to '=' before looking up the file.
    """
    if entry_id_int == 0:
        b = bytes([0])
    else:
        raw = entry_id_int.to_bytes(4, 'big').lstrip(b'\x00')
        b = raw if raw else bytes([0])
    return base64.urlsafe_b64encode(b).decode('ascii')


def compute_id64_no_strip(entry_id_int):
    """
    Encode an integer as base64url WITHOUT stripping leading zero bytes.

    The spec (conform-entry-id-converted) requires leading zeros to be stripped
    before base64url encoding. This helper deliberately omits that step, producing
    the 'wrong' encoding used in negative tests that verify clients strip leading
    zeros.
    Example: integer 1 -> big-endian [0x00, 0x00, 0x00, 0x01] -> 'AAAAAQ=='
             (correct encoding strips to [0x01] -> 'AQ==')
    """
    b = entry_id_int.to_bytes(4, 'big')  # always 4 bytes, no stripping
    return base64.urlsafe_b64encode(b).decode('ascii')

def encode_id32(entry_id_int):
    """
    Encode an integer entry ID as base32hex (no padding) the way the id32 URL
    template op code does (spec §5.3.3): big endian 32-bit, strip leading zero
    bytes, then base32hex. The inverse of decode_id32_to_int.
    Examples: 1 -> '04', 2 -> '08', 3 -> '0C', 13 -> '1K'
    """
    raw = entry_id_int.to_bytes(4, 'big').lstrip(b'\x00') or b'\x00'
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUV'
    result = ''
    bits = 0
    num_bits = 0
    for byte in raw:
        bits = (bits << 8) | byte
        num_bits += 8
        while num_bits >= 5:
            num_bits -= 5
            result += alphabet[(bits >> num_bits) & 0x1F]
    if num_bits > 0:
        result += alphabet[(bits << (5 - num_bits)) & 0x1F]
    return result


def decode_sparse_bit_set(data, offset, bias=0):
    """
    Decode a sparse bit set (spec §5.3.4) starting at data[offset].

    Returns (set_of_ints, offset_after_the_set).
    """
    header = data[offset]
    offset += 1
    branch_factor = {0: 2, 1: 4, 2: 8, 3: 32}[header & 0b11]
    height = (header >> 2) & 0b11111
    if height == 0:
        return set(), offset

    result = set()
    queue = [(0, 1)]
    bit_pos = 0

    def take_bits(count):
        nonlocal bit_pos
        bits = []
        for _ in range(count):
            byte = data[offset + bit_pos // 8]
            bits.append((byte >> (bit_pos % 8)) & 1)
            bit_pos += 1
        return bits

    while queue:
        start, depth = queue.pop(0)
        bits = take_bits(branch_factor)
        if not any(bits):
            size = branch_factor ** (height - depth + 1)
            result.update(range(start + bias, start + bias + size))
            continue
        for i, bit in enumerate(bits):
            if not bit:
                continue
            if depth == height:
                result.add(start + bias + i)
            else:
                queue.append((start + i * branch_factor ** (height - depth), depth + 1))

    return result, offset + (bit_pos + 7) // 8


def parse_format2_entries(iftData):
    """
    Interpret the mapping entries of a Format 2 patch map table (spec §5.3.2,
    Interpret Patch Map Entry) and return them as a list of dicts, in entry
    order, with keys:

        offset, length  - byte range of the entry within the table
        flags           - the formatFlags byte
        ids             - list of numeric entry ids (first id = the patch the
                          entry activates, remaining ids = prefetch list)
        patchFormat     - resolved patch format number
        codepoints      - set of code points
        features        - list of feature tags
        designSpace     - list of (tag, start, end)
        children        - list of child entry indices
        conjunctive     - child match mode (True = conjunctive)
        ignored         - bit 6 of formatFlags

    Only numeric entry ids (no entryIdStringData) are supported, which is what
    the encoder produces for this suite.
    """
    iftData = bytes(iftData)
    if iftData[IFT_FORMAT_OFFSET] != 2:
        raise ValueError("Expected IFT patch map format 2")
    default_patch_format = iftData[21]
    entry_count = int.from_bytes(iftData[22:25], 'big')
    entries_offset = int.from_bytes(iftData[IFT_ENTRIES_OFFSET_START:IFT_ENTRIES_OFFSET_END], 'big')
    id_string_offset = int.from_bytes(
        iftData[IFT_ENTRY_ID_STRING_OFFSET_START:IFT_ENTRY_ID_STRING_OFFSET_END], 'big'
    )
    if id_string_offset != 0:
        raise ValueError("String entry ids are not supported")

    entries = []
    offset = entries_offset
    last_id = 0
    for _ in range(entry_count):
        start = offset
        flags = iftData[offset]
        offset += 1

        features = []
        design_space = []
        if flags & 0x01:
            feature_count = iftData[offset]
            offset += 1
            for _ in range(feature_count):
                features.append(iftData[offset:offset + 4].decode('latin-1'))
                offset += 4
            design_space_count = int.from_bytes(iftData[offset:offset + 2], 'big')
            offset += 2
            for _ in range(design_space_count):
                tag = iftData[offset:offset + 4].decode('latin-1')
                seg_start = int.from_bytes(iftData[offset + 4:offset + 8], 'big', signed=True) / 65536
                seg_end = int.from_bytes(iftData[offset + 8:offset + 12], 'big', signed=True) / 65536
                design_space.append((tag, seg_start, seg_end))
                offset += 12

        children = []
        conjunctive = False
        if flags & 0x02:
            mode_and_count = iftData[offset]
            offset += 1
            conjunctive = bool(mode_and_count & 0x80)
            for _ in range(mode_and_count & 0x7F):
                children.append(int.from_bytes(iftData[offset:offset + 3], 'big'))
                offset += 3

        ids = []
        if flags & 0x04:
            while True:
                delta = int.from_bytes(iftData[offset:offset + 3], 'big', signed=True)
                offset += 3
                # The low bit is the continuation flag. The encoder and the
                # reference client both divide the signed value by 2 rounding
                # toward zero (the spec text says floor, which differs for
                # negative odd values), so follow the implementations here.
                last_id = last_id + 1 + int(delta / 2)
                ids.append(last_id)
                if not (delta & 0x01):
                    break
        else:
            last_id += 1
            ids.append(last_id)

        patch_format = default_patch_format
        if flags & 0x08:
            patch_format = iftData[offset]
            offset += 1

        codepoints = set()
        if flags & 0x30:
            bias = 0
            if (flags & 0x30) == 0x20:
                bias = int.from_bytes(iftData[offset:offset + 2], 'big')
                offset += 2
            elif (flags & 0x30) == 0x30:
                bias = int.from_bytes(iftData[offset:offset + 3], 'big')
                offset += 3
            codepoints, offset = decode_sparse_bit_set(iftData, offset, bias)

        entries.append(dict(
            offset=start,
            length=offset - start,
            flags=flags,
            ids=ids,
            patchFormat=patch_format,
            codepoints=codepoints,
            features=features,
            designSpace=design_space,
            children=children,
            conjunctive=conjunctive,
            ignored=bool(flags & 0x40),
        ))

    return entries
