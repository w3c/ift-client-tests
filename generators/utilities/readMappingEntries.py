import sys
from pathlib import Path
import struct
from typing import List, Dict, Union

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from testCaseGeneratorLib.iftFile import IFTFile

# -----------------------
# Parser for IFT tables
# -----------------------
def parseIftTable(iftData: bytes) -> List[Dict[str, Union[int, bytes, List[int]]]]:
    """
    Parse an IFT table (Incremental Font Transfer Patch Map) from raw bytes
    and extract patch entries.
    """
    entries = []
    offset = 0
    dataLen = len(iftData)

    if dataLen < 4:
        raise ValueError("IFT table too short")

    # --- Read table format ---
    formatByte = iftData[offset]
    offset += 1
    if formatByte not in (1, 2):
        raise ValueError(f"Unsupported IFT table format: {formatByte}")

    # Skip reserved 3 bytes
    offset += 3

    # Flags (1 byte)
    flags = iftData[offset]
    offset += 1

    # 4 x uint32 compatibility ID
    if offset + 16 > dataLen:
        raise ValueError("IFT table truncated before compatibilityId")
    compatibilityId = struct.unpack(">4I", iftData[offset:offset+16])
    offset += 16

    if formatByte == 1:
        # --- Format 1 ---
        if offset + 4 > dataLen:
            raise ValueError("IFT table truncated before maxEntryIndex")
        maxEntryIndex, maxGlyphMapIndex = struct.unpack(">HH", iftData[offset:offset+4])
        offset += 4

        # glyph count (uint24)
        if offset + 3 > dataLen:
            raise ValueError("IFT table truncated before glyphCount")
        glyphCount = int.from_bytes(iftData[offset:offset+3], "big")
        offset += 3

        # Glyph map offset (uint32) and feature map offset (uint32)
        if offset + 8 > dataLen:
            raise ValueError("IFT table truncated before glyphMapOffset/featureMapOffset")
        glyphMapOffset, featureMapOffset = struct.unpack(">II", iftData[offset:offset+8])
        offset += 8

        # Applied entries bitmap
        bitmapSize = (maxEntryIndex + 7) // 8
        if offset + bitmapSize > dataLen:
            raise ValueError("IFT table truncated before applied entries bitmap")
        appliedBitmap = iftData[offset:offset+bitmapSize]
        offset += bitmapSize

        # URL template length (uint8) and URL template bytes
        if offset + 1 > dataLen:
            raise ValueError("IFT table truncated before URL template length")
        urlTemplateLength = iftData[offset]
        offset += 1
        if offset + urlTemplateLength > dataLen:
            raise ValueError("IFT table truncated before URL template bytes")
        urlTemplateBytes = iftData[offset:offset+urlTemplateLength]
        offset += urlTemplateLength

        entries.append({
            "format": 1,
            "compatibilityId": compatibilityId,
            "maxEntryIndex": maxEntryIndex,
            "glyphCount": glyphCount,
            "urlTemplateBytes": urlTemplateBytes,
            "appliedBitmap": appliedBitmap
        })

    elif formatByte == 2:
        # --- Format 2 ---
        if offset + 1 > dataLen:
            raise ValueError("IFT table truncated before defaultPatchFormat")
        defaultPatchFormat = iftData[offset]
        offset += 1

        # The remaining bytes are a sequence of patch entries
        while offset < dataLen:
            if offset + 1 > dataLen:
                break
            entryFormat = iftData[offset]
            offset += 1

            # Length-prefixed URL template
            if offset + 1 > dataLen:
                break
            urlLen = iftData[offset]
            offset += 1
            if offset + urlLen > dataLen:
                break
            urlTemplateBytes = iftData[offset:offset+urlLen]
            offset += urlLen

            # Glyph subset count (1 byte) and glyph indices
            if offset + 1 > dataLen:
                break
            glyphCount = iftData[offset]
            offset += 1
            if offset + glyphCount > dataLen:
                break
            glyphs = list(iftData[offset:offset+glyphCount])
            offset += glyphCount

            entries.append({
                "format": 2,
                "entryFormat": entryFormat,
                "defaultPatchFormat": defaultPatchFormat,
                "urlTemplateBytes": urlTemplateBytes,
                "glyphs": glyphs
            })

    return entries

# -----------------------
# Load IFT table using IFTFile class
# -----------------------
testName = "exampleTestFile"
fontFormat = "GLYF"
iftFontFilename = "myfont-mod.ift.woff2"

nft = IFTFile(testName, fontFormat, iftFontFilename)
iftData = nft.getIFTTableData()  # raw IFT table bytes

# -----------------------
# Parse patch entries
# -----------------------
patchEntries = parseIftTable(iftData)

# -----------------------
# Print results
# -----------------------
for idx, entry in enumerate(patchEntries):
    print(f"Entry {idx}:")
    print("  format:", entry.get("format"))
    print("  url template bytes:", entry.get("urlTemplateBytes"))
    if "glyphs" in entry:
        print("  glyphs:", entry["glyphs"])
    if "appliedBitmap" in entry:
        print("  applied bitmap:", entry["appliedBitmap"].hex())
    print()
