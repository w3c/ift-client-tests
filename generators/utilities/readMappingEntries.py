import sys
import struct
import pprint
from pathlib import Path
from typing import List
import collections
from fontTools.ttLib import TTFont

sys.path.append(str(Path(__file__).resolve().parent.parent))
from testCaseGeneratorLib.iftFile import IFTFile

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def read_uint24(data, offset):
    return int.from_bytes(data[offset:offset+3], "big"), offset + 3

# --------------------------------------------------
# Sparse bitset decoder (spec §5.3.2.3)
# --------------------------------------------------
def read_sparse_bit_set(tableData: bytes, offset: int, bias: int):
    header = tableData[offset]
    offset += 1

    bf_bits = header & 0x03
    height = (header >> 2) & 0x1F

    if bf_bits == 0:
        B = 2
    elif bf_bits == 1:
        B = 4
    elif bf_bits == 2:
        B = 8
    else:
        B = 32

    S = []

    if height == 0:
        return S, offset

    bit_stream = []
    byte_index = offset
    while byte_index < len(tableData):
        b = tableData[byte_index]
        for bit in range(8):
            bit_stream.append((b >> bit) & 1)
        byte_index += 1

    offset = byte_index

    Q = collections.deque()
    Q.append((0, 1))

    idx = 0
    max_cp = 0x10FFFF

    while Q and idx < len(bit_stream):
        start, depth = Q.popleft()

        bits = bit_stream[idx:idx+B]
        idx += B

        if all(v == 0 for v in bits):
            length = B ** (height - depth + 1)
            for x in range(start, start+length):
                cp = x + bias
                if cp <= max_cp:
                    S.append(cp)
        else:
            for i,v in enumerate(bits):
                if v == 1:
                    if depth == height:
                        cp = start+i+bias
                        if cp <= max_cp:
                            S.append(cp)
                    else:
                        next_start = start + (i * (B ** (height-depth)))
                        Q.append((next_start, depth+1))

    return sorted(set(S)), offset

# --------------------------------------------------
# Format 2 Header
# --------------------------------------------------
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

    url_template = data[offset:offset+url_template_length]
    offset += url_template_length

    cff = None
    if has_cff:
        cff = struct.unpack_from(">I", data, offset)[0]
        offset += 4

    cff2 = None
    if has_cff2:
        cff2 = struct.unpack_from(">I", data, offset)[0]
        offset += 4

    return {
        "format": format_,
        "entryCount": entry_count,
        "entriesOffset": entries_offset,
        "entryIdStringDataOffset": entry_id_string_data_offset,
        "urlTemplate": url_template,
    }

# --------------------------------------------------
# Parse ONE mapping entry
# --------------------------------------------------
def parse_mapping_entry(data, offset, entryIdStringDataOffset):

    start = offset
    entry = {}

    formatFlags = data[offset]
    offset += 1
    entry["formatFlags"] = f"{formatFlags:08b}"

    # ---- bit 0 : features + design space
    if formatFlags & 0x01:
        featureCount = data[offset]
        offset += 1

        tags = []
        for _ in range(featureCount):
            tags.append(data[offset:offset+4].decode("ascii", errors="replace"))
            offset += 4
        entry["featureTags"] = tags

        designSpaceCount = struct.unpack_from(">H", data, offset)[0]
        offset += 2

        ds = []
        for _ in range(designSpaceCount):
            tag = data[offset:offset+4].decode("ascii", errors="replace")
            offset += 4
            start_raw = struct.unpack_from(">i", data, offset)[0]
            offset += 4
            end_raw = struct.unpack_from(">i", data, offset)[0]
            offset += 4
            ds.append({"tag":tag,"start":start_raw/65536,"end":end_raw/65536})
        entry["designSpace"] = ds
    else:
        entry["featureTags"] = []
        entry["designSpace"] = []

    # ---- bit 1 : child entries
    if formatFlags & 0x02:
        b = data[offset]
        offset += 1
        entry["childMatchMode"] = (b>>7)&1
        count = b & 0x7F

        indices = []
        for _ in range(count):
            v, offset = read_uint24(data, offset)
            indices.append(v)
        entry["childEntryIndices"] = indices
    else:
        entry["childEntryIndices"] = []

    # ---- bit 2 : entryIdStringLengths
    lengths = []
    if (formatFlags & 0x04) and entryIdStringDataOffset != 0:
        ptr = entryIdStringDataOffset
        while True:
            raw, ptr = read_uint24(data, ptr)
            lengths.append(raw & 0x7FFFFF)
            if not (raw & 0x800000):
                break
    entry["entryIdStringLengths"] = lengths

    # ---- bit 3 : patchFormat
    if formatFlags & 0x08:
        entry["patchFormat"] = data[offset]
        offset += 1
    else:
        entry["patchFormat"] = None

    # ---- bits 4/5 : bias + sparse set
    bias = 0
    if formatFlags & 0x20:
        if formatFlags & 0x10:
            bias, offset = read_uint24(data, offset)
        else:
            bias = struct.unpack_from(">H", data, offset)[0]
            offset += 2
    entry["bias"] = bias

    if formatFlags & 0x30:
        cps, offset = read_sparse_bit_set(data, offset, bias)
        entry["codePoints"] = cps
    else:
        entry["codePoints"] = []

    # ---- Determine table-keyed vs glyph-keyed
    entry["tableKeyed"] = False
    if entry["patchFormat"] is not None and not entry["codePoints"]:
        entry["tableKeyed"] = True

    entry["size"] = offset-start
    return entry, offset

# --------------------------------------------------
# Parse ALL mapping entries
# --------------------------------------------------
def parse_mapping_entries(data, header):
    entries = []
    offset = header["entriesOffset"]

    for i in range(header["entryCount"]):
        if offset >= len(data):
            break
        entry, offset = parse_mapping_entry(
            data,
            offset,
            header["entryIdStringDataOffset"]
        )
        entry["index"] = i
        entries.append(entry)

    return entries

# --------------------------------------------------
# Main
# --------------------------------------------------
if __name__ == "__main__":
    fontFile = "../resources/IFT/GLYF/font.ift.woff2"
    # fontFile = "./resources/Roboto-IFT.woff2"
    font = TTFont(fontFile)
    tbl = font["IFT "] 
    data = bytearray(tbl.data)
    header = parse_format2_table(data)
    pprint.pprint(header)

    print("\nMapping Entries:\n")
    entries = parse_mapping_entries(data, header)
    for e in entries:
        pprint.pprint(e)
        print("--------------")