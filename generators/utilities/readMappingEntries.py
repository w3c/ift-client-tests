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
def parse_first_mapping_entry(entryData: bytes, entries_offset: int, entryIdStringDataOffset: int,tableData: bytes,):
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
        entry["featureCount"] = featureCount
        offset += 1
        tags = []
        for _ in range(featureCount):
            tags.append(entryData[offset:offset+4])
            offset += 4
        entry["featureTags"] = tags
        designSpaceCount = struct.unpack_from(">H", entryData, offset)[0]  # '>H' = big-endian uint16
        offset += 2  # move past the 2 bytes
        entry["designSpaceCount"] = designSpaceCount
        # assume offset is at the start of the list
        entry["designSpace"] = []

        for i in range(designSpaceCount):
            # read the 4-byte tag
            tag_bytes = entryData[offset:offset+4]
            tag = tag_bytes.decode("ascii")  # convert to string
            offset += 4

            # read 4-byte start (Fixed 16.16)
            start_raw = struct.unpack_from(">i", entryData, offset)[0]  # big-endian signed int
            start = start_raw / 65536.0  # convert 16.16 fixed-point to float
            offset += 4

            # read 4-byte end (Fixed 16.16)
            end_raw = struct.unpack_from(">i", entryData, offset)[0]
            end = end_raw / 65536.0
            offset += 4

            entry["designSpace"].append({
                "tag": tag,
                "start": start,
                "end": end
            })

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

    entryIdStringLengths = []

    # Only present if bit 2 set AND entryIdStringDataOffset != 0
    if (formatFlags & 0x04) and entryIdStringDataOffset != 0:

        string_offset = entryIdStringDataOffset

        while True:
            raw_len, string_offset = read_uint24(tableData, string_offset)

            # MSB (bit 23) indicates continuation
            has_more = raw_len & 0x800000

            # Actual length = lower 23 bits
            length = raw_len & 0x7FFFFF

            entryIdStringLengths.append(length)

            # stop when MSB cleared
            if not has_more:
                break

    else:
        print("Why are we here? bit 2 is not set or entryIdStringDataOffset is 0", entryIdStringDataOffset )
        # Default case: one string inherited / empty
        entryIdStringLengths = []

    entry["entryIdStringLengths"] = entryIdStringLengths

    patchFormat = None  # default if not present

    # Check if bit 3 (0x08) of formatFlags is set
    if formatFlags & 0x08:
        patchFormat = entryData[offset]  # uint8
        offset += 1  # advance offset

    entry["patchFormat"] = patchFormat


    bias = None  # default if not present

    # Check if bit 5 is set (0x20)
    if formatFlags & 0x20:
        if formatFlags & 0x10:
            # Bit 4 is 1 → bias is uint24
            bias, offset = read_uint24(entryData, offset)
        else:
            # Bit 4 is 0 → bias is uint16
            bias = int.from_bytes(entryData[offset:offset+2], "big")
            offset += 2

    entry["bias"] = bias


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
    first_entry = parse_first_mapping_entry(ift_data, header["entriesOffset"],header["entryIdStringDataOffset"],ift_data)
    pprint.pprint(first_entry)
