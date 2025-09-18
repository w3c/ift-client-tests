import os
import glob
import shutil
from fontTools.ttLib import TTFont
from testCaseGeneratorLib.paths import IFTSourcePath, IFTTestDirectory, resourcesDirectory


if not os.path.exists(IFTTestDirectory):
    os.makedirs(IFTTestDirectory)

test_name = "conform-format1-valid-format-number"
test_directory = os.path.join(IFTTestDirectory, test_name)
if not os.path.exists(test_directory):
    os.makedirs(test_directory)

# Copy _gk and _tk files from resources/IFT/ to test_directory
source_dir = os.path.join(resourcesDirectory, "IFT")
for pattern in ("*_gk", "*_tk"):
    for file_path in glob.glob(os.path.join(source_dir, pattern)):
        shutil.copy(file_path, test_directory)
        print(f"Copied {file_path} to {test_directory}")

outPath = os.path.join(test_directory, "myfont-mod.ift.otf");
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
