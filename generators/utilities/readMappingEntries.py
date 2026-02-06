import sys
import struct
import pprint
from pathlib import Path
from typing import List, Dict, Union

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
# Map entry index to encoder filename
# -----------------------
def encoder_filename(entry_index: int) -> str:
    """
    Return the actual encoder filename for the given entry index.
    Modify this mapping to match your encoder output:
    Examples:
      0  -> 04.ift_tk
      1  -> 08.ift_tk
      2  -> 0C.ift_tk
      3  -> 0G.ift_tk
      ...
      16 -> 1_00.ift_gk
    """
    encoder_mapping = [
        "04.ift_tk","08.ift_tk","0C.ift_tk","0G.ift_tk","0K.ift_tk","0O.ift_tk","0S.ift_tk",
        "1_00.ift_gk","10.ift_tk","14.ift_tk","18.ift_tk","1C.ift_tk","1G.ift_tk","2_00.ift_gk"
    ]
    if entry_index < len(encoder_mapping):
        return encoder_mapping[entry_index]
    # fallback: sequential hex if out of mapping
    return f"{entry_index:02X}.ift_tk"

def read_uint24(data, offset):
    return int.from_bytes(data[offset:offset+3], "big"), offset + 3

def parse_format2_table(data: bytes):
    offset = 0
    table_start = 0  # offsets are relative to start of this table

    # uint8 format
    format_ = data[offset]
    offset += 1

    # uint24 reserved
    reserved, offset = read_uint24(data, offset)

    # uint8 flags
    flags = data[offset]
    offset += 1

    has_cff = bool(flags & 0x01)
    has_cff2 = bool(flags & 0x02)

    # uint32[4] compatibilityId
    compatibility_ids = struct.unpack_from(">4I", data, offset)
    offset += 16

    # uint8 defaultPatchFormat
    default_patch_format = data[offset]
    offset += 1

    # uint24 entryCount
    entry_count, offset = read_uint24(data, offset)

    # Offset32 entries
    entries_offset = struct.unpack_from(">I", data, offset)[0]
    offset += 4

    # Offset32 entryIdStringData
    entry_id_string_data_offset = struct.unpack_from(">I", data, offset)[0]
    offset += 4

    # uint16 urlTemplateLength
    url_template_length = struct.unpack_from(">H", data, offset)[0]
    offset += 2

    # uint8[urlTemplateLength] urlTemplate
    url_template_bytes = data[offset:offset + url_template_length]
    offset += url_template_length

    # Optional uint32 cffCharStringsOffset
    cff_charstrings_offset = None
    if has_cff:
        cff_charstrings_offset = struct.unpack_from(">I", data, offset)[0]
        offset += 4

    # Optional uint32 cff2CharStringsOffset
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
        "nextOffset": offset,  # where Mapping Entries table begins if sequential
    }
# -----------------------
# Load IFT table
# -----------------------
iftFile = IFTFile("exampleTestFile", "GLYF", "myfont-mod.ift.woff2")
ift_data = iftFile.getIFTTableData()

pprint.pprint(parse_format2_table(ift_data))