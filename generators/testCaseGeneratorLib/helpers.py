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