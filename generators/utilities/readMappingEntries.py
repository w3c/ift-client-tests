import sys
from pathlib import Path

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from testCaseGeneratorLib.iftFile import IFTFile

# -----------------------
# Open the font and get IFT table
# -----------------------

testName = "exampleTestFile"
fontFormat = "GLYF"
IFT_FONT_FILENAME = "myfont-mod.ift.woff2"
nft = IFTFile(testName,fontFormat, IFT_FONT_FILENAME)

iftData = nft.getIFTTableData()

entriesOffset = int.from_bytes(iftData[25:29], "big")
entriesData = iftData[entriesOffset:]

print("entriesData length:", len(entriesData))
print("entriesData (hex):")
print(entriesData.hex())
print("\nLooping through entries:")
print("-" * 50)

# Loop through each byte in entriesData
for i, byte in enumerate(entriesData):
    print(f"Entry {i}: 0x{byte:02x} ({byte})")
    
print("-" * 50)
print(f"Total entries: {len(entriesData)}")
