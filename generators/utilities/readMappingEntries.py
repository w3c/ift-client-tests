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

# -----------------------
# Parse Format 2 IFT table
# -----------------------
def parse_format2_ift_table(ift_data: bytes) -> List[Dict[str, Union[str,int,List[int]]]]:
    offset = 0
    data_len = len(ift_data)
    entries: List[Dict[str, Union[str,int,List[int]]]] = []

    # --- Header ---
    format_byte = ift_data[offset]
    offset += 1
    if format_byte != 2:
        raise ValueError("Only Format 2 supported")
    offset += 3  # reserved
    flags = ift_data[offset]
    offset += 1

    offset += 16  # skip compatibility ID
    default_patch_format = ift_data[offset]
    offset += 1
    entry_count_bytes = ift_data[offset:offset+3]
    entryCount = int.from_bytes(entry_count_bytes, byteorder='big')
    offset += 3

    # --- Parse entries ---
    for entry_index in range(entryCount):   
        print(entry_index);
#         entry_format = ift_data[offset]
#         offset += 1
# 
#         url_len = ift_data[offset]
#         offset += 1
#         offset += url_len  # skip per-entry URL bytes
# 
#         # patch data: until next 0x00 or 0x01 byte (simple heuristic)
#         next_entry_offset = offset
#         while next_entry_offset < data_len and ift_data[next_entry_offset] not in (0x00,0x01):
#             next_entry_offset += 1
#         patch_data = ift_data[offset:next_entry_offset]
#         offset = next_entry_offset

        # decode glyphs
#         glyphs = decode_sparse_bitset(patch_data) if entry_format == 1 else list(range(len(patch_data)))

#         url = encoder_filename(entry_index)

#         entries.append({
#             "entryFormat": entry_format,
#             "url": url,
#             "patchFormat": default_patch_format,
#             "glyphs": glyphs,
#             "patchBytes": patch_data.hex()
#         })


#    return entries

# -----------------------
# Load IFT table
# -----------------------
iftFile = IFTFile("exampleTestFile", "GLYF", "myfont-mod.ift.woff2")
ift_data = iftFile.getIFTTableData()

patch_entries = parse_format2_ift_table(ift_data)

# -----------------------
# Print entries
# -----------------------
for idx, e in enumerate(patch_entries):
    print(f"Entry {idx}:")
    print("  url:", e["url"])
    print("  patchFormat:", e["patchFormat"])
    print("  glyphs:", e["glyphs"])
    print()