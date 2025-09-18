
import os
import sys
from testCaseGeneratorLib.paths import TTFSourcePath, fallbackDirectory
from fontTools.ttLib import TTFont, newTable
from fontTools.subset import Subsetter, Options
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString


if not os.path.exists(fallbackDirectory):
    os.makedirs(fallbackDirectory)





# Check command line argument for ift/fail
if len(sys.argv) < 2 or sys.argv[1] not in ("ift", "fallback"):
    print("Usage: python makeFallbackFont.py [ift|fallback]")
    sys.exit(1)

mode = sys.argv[1]

if (mode == "ift"):
    file_descriptor = "fallback";
elif (mode == "fallback"):
    file_descriptor = "";
# Input and output files
input_font_path = TTFSourcePath
subset_font_path = os.path.join(fallbackDirectory, "Roboto-subset.ttf")
final_font_path = os.path.join(fallbackDirectory, f"Roboto{file_descriptor}.ttf")

# Step 1: Subset the font to keep only required glyphs
glyphs_to_keep = ["A", "F", "I", "L", "P", "S"]

font = TTFont(input_font_path)

options = Options()
options.glyph_names = True
options.notdef_glyph = True
options.recalc_bounds = True
options.recalc_timestamp = True
options.layout_features = ["*"]

subsetter = Subsetter(options=options)
subsetter.populate(glyphs=glyphs_to_keep + [".notdef", "space"])
subsetter.subset(font)
font.save(subset_font_path)


# Step 2: Reload the subset font and add GSUB feature for a → p a s s
font = TTFont(subset_font_path)

new_name = f"RobotoFallback{mode.capitalize()}"

# Name IDs you typically want to change:
# 1: Font Family name
# 2: Font Subfamily (Regular, Bold, etc.)
# 4: Full font name
# 6: PostScript name
name_table = font['name']

for record in name_table.names:
    if record.nameID in [1, 4, 6]:
        record.string = new_name.encode(record.getEncoding())
    elif record.nameID == 2:
        # Optional: keep style information
        record.string = b"Regular"

# Ensure GSUB table exists
if "GSUB" not in font:
    font["GSUB"] = newTable("GSUB")


# Determine mapping based on command line argument
if mode == "ift":
    fea_code = """
feature liga {
    sub P by P A S S;
    sub F by F A I L;
} liga;
"""
else:
    fea_code = """
feature liga {
    sub P by F A I L;
    sub F by P A S S;
} liga;
"""

# Add the feature to the font
addOpenTypeFeaturesFromString(font, fea_code)


# Save the final font
font.save(final_font_path)
print(f"Font saved to {final_font_path}")

# Remove the intermediate subset font file
import os
try:
    os.remove(subset_font_path)
    print(f"Removed intermediate file: {subset_font_path}")
except Exception as e:
    print(f"Warning: Could not remove {subset_font_path}: {e}")
