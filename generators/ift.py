import os
from fontTools.ttLib import TTFont
from testCaseGeneratorLib.paths import IFTSourcePath, IFTTestDirectory


# TODO:  Need to create sub-directory for each IFT because they are multiple files
if not os.path.exists(IFTTestDirectory):
    os.makedirs(IFTTestDirectory)

testDirectory = os.path.join(IFTTestDirectory, "test_name_goes_here");
if not os.path.exists(testDirectory):
    os.makedirs(testDirectory)
outPath = os.path.join(testDirectory, "myfont-mod.ift.otf");
font = TTFont(IFTSourcePath)

if "IFT " not in font:
    raise ValueError("IFT table not found in font.")

# Unknown/custom tables are stored as raw bytes on .data
tbl = font["IFT "]
raw = bytearray(tbl.data)

# The first byte is the 'format' (uint8). Set it to 3.
raw[0] = 3

# Put the bytes back and save
tbl.data = bytes(raw)
font.save(outPath)

print("Wrote", outPath)

# --- Inspect the saved font ---
font2 = TTFont(outPath)
ift_tbl = font2["IFT "]
format_value = ift_tbl.data[0]  # first byte is 'format'
print("IFT table format field is now:", format_value)
