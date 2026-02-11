import sys
import struct
import pprint
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).resolve().parent.parent))
from testCaseGeneratorLib.iftFile import IFTFile

# -----------------------
# Decode sparse bitset to glyph indices
# -----------------------
def decode_sparse_bitset(data: bytes, base: int = 0) -> List[int]:
    glyphs = []
    for byte_index, byte_val in enumerate(data):
        for bit_index in range(8):
            if byte_val & (1 << (7 - bit_index)):
                glyphs.append(base + byte_index * 8 + bit_index)
    return glyphs

# -----------------------
# Helpers
# -----------------------
def read_uint24(data, offset):
    return int.from_bytes(data[offset:offset+3], "big"), offset + 3

# -----------------------
# Parse Format-2 table header
# -----------------------
def parse_format2_table(data: bytes):
    offset = 0

    format_ = data[offset]
    offset += 1

    reserved, offset = read_uint24(data, offset)

    flags = data[offset]
    offset += 1
    has_cff = bool(flags & 0x01)
    has_cff2 = bool(flags & 0x02)

    compatibility_ids = struct.unpack_from(">4I", data, offset)
    offset += 16

    default_patch_format = data[offset]
    offset += 1

    entry_count, offset = read_uint24(data, offset)

    entries_offset = struct.unpack_from(">I", data, offset)[0]
    offset += 4

    entry_id_string_data_offset = struct.unpack_from(">I", data, offset)[0]
    offset += 4

    url_template_length = struct.unpack_from(">H", data, offset)[0]
    offset += 2

    url_template_bytes = data[offset:offset + url_template_length]
    offset += url_template_length

    cff_charstrings_offset = None
    if has_cff:
        cff_charstrings_offset = struct.unpack_from(">I", data, offset)[0]
        offset += 4

    cff2_charstrings_offset = None
    if has_cff2:
        cff2_charstrings_offset = struct.unpack_from(">I", data, offset)[0]
        offset += 4

    return {
        "format": format_,
        "reserved": reserved,
        "flags": flags,
        "hasCFF": has_cff,
        "hasCFF2": has_cff2,
        "compatibilityId": compatibility_ids,
        "defaultPatchFormat": default_patch_format,
        "entryCount": entry_count,
        "entriesOffset": entries_offset,
        "entryIdStringDataOffset": entry_id_string_data_offset,
        "urlTemplateLength": url_template_length,
        "urlTemplate": url_template_bytes,
        "cffCharStringsOffset": cff_charstrings_offset,
        "cff2CharStringsOffset": cff2_charstrings_offset,
        "nextOffset": offset,
    }

# -----------------------
# Parse the first Mapping Entry only
# -----------------------
def parse_first_mapping_entry(entryData: bytes, entries_offset: int):
    if entries_offset >= len(entryData):
        return {}

    offset = entries_offset
    entry = {}

    # formatFlags (uint8)

    formatFlags = entryData[offset]
    entry["formatFlags"] = f"{formatFlags:08b}"
    offset += 1

    # -----------------------
    # Bit 0 → featureCount + featureTags + designSpaceCount
    # -----------------------
    if formatFlags & 0x01:
        # bit 0 is set → optional fields present
        featureCount = entryData[offset]
        offset += 1
        tags = []
        for _ in range(featureCount):
            tags.append(entryData[offset:offset+4])
            offset += 4
        entry["featureTags"] = tags

        # designSpaceCount (uint16)
        if offset + 2 <= len(entryData):
            entry["designSpaceCount"] = int.from_bytes(entryData[offset:offset+2], "big")
            offset += 2
        else:
            entry["designSpaceCount"] = 0
    else:
        # bit 0 clear → no optional fields
        entry["featureTags"] = []
        entry["designSpaceCount"] = 0

    # -----------------------
    # Bit 1 → childEntryMatchModeAndCount
    # -----------------------
    if formatFlags & 0x02:
        if offset < len(entryData):
            childEntryMatchModeAndCount = entryData[offset]
            offset += 1
            mode = (childEntryMatchModeAndCount & 0x80) >> 7
            count = childEntryMatchModeAndCount & 0x7F
            entry["childMatchMode"] = mode
            entry["childEntryCount"] = count
        else:
            entry["childMatchMode"] = None
            entry["childEntryCount"] = 0
    else:
        entry["childMatchMode"] = None
        entry["childEntryCount"] = 0

    # total size read for this entry
    entry["size"] = offset - entries_offset
    return entry


# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    iftFile = IFTFile("exampleTestFile", "GLYF", "myfont-mod.ift.woff2")
    ift_data = iftFile.getIFTTableData()

    header = parse_format2_table(ift_data)
    pprint.pprint(header)

    print("\nFirst Mapping Entry:")
    first_entry = parse_first_mapping_entry(ift_data, header["entriesOffset"])
    pprint.pprint(first_entry)
