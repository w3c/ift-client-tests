import sys
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
# Parse Format 2 IFT table
# -----------------------
def parse_format2_ift_table(iftData: bytes):
    offset = 0
    iftFormat = iftData[offset] if len(iftData) > 0 else 0
    offset += 1
    reserved = int.from_bytes(iftData[offset:offset+3], byteorder='big') if len(iftData) >= offset+3 else 0
    offset += 3
    flags = iftData[offset] if len(iftData) > offset else 0
    offset += 1

    compatibilityIds = []
    for _ in range(4):
        if len(iftData) >= offset + 4:
            compatibilityIds.append(int.from_bytes(iftData[offset:offset+4], byteorder='big'))
            offset += 4
        else:
            compatibilityIds.append(0)
    print("what is up?",iftFormat,reserved,flags)

# -----------------------
# Load IFT table
# -----------------------
iftFile = IFTFile("exampleTestFile", "GLYF", "myfont-mod.ift.woff2")
iftData = iftFile.getIFTTableData()

patch_entries = parse_format2_ift_table(iftData)

# -----------------------
# Print entries
# -----------------------
# for idx, e in enumerate(patch_entries):
#     print(f"Entry {idx}:")
#     print("  url:", e["url"])
#     print("  patchFormat:", e["patchFormat"])
#     print("  glyphs:", e["glyphs"])
#     print()
