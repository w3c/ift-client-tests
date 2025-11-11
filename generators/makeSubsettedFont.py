
"""
Subsetting Font Generator for IFT Client Tests

This script creates subset test fonts from a source font file for use in 
Incremental Font Transfer (IFT) client testing. It generates fonts with 
specific glyph substitution rules to test client behavior.

The script:
1. Subsets the input font to keep only required glyphs (A, F, I, L, P, S)
2. Adds OpenType GSUB ligature features based on the specified mode
3. Renames the font family to reflect its purpose
4. Saves the processed font to the output directory

Usage:
    python makeSubsettedFont.py <input_font> <mode>

Arguments:
    input_font - Path to the source font file (TTF, OTF, WOFF, WOFF2, etc.)
    mode       - Either 'ift' or 'fallback'
                 ift:      Creates a font where P→PASS and F→FAIL (for IFT success tests)
                 fallback: Creates a font where P→FAIL and F→PASS (for fallback tests)

Output:
    The output font will be saved in the subsettedFonts directory,
    with the mode appended to the base filename (preserving the original extension).

Examples:
    python makeSubsettedFont.py ../fonts/Roboto-Regular.ttf ift
    python makeSubsettedFont.py ../fonts/MyFont.otf fallback

The generated fonts use OpenType ligature substitutions to display
test results visually in IFT client tests.
"""

import os
import sys
from testCaseGeneratorLib.paths import subsetFontPath
from fontTools.ttLib import TTFont, newTable
from fontTools.subset import Subsetter, Options
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

# Ensure output directory exists
if not os.path.exists(subsetFontPath):
    os.makedirs(subsetFontPath)

# Parse and validate command line arguments
if len(sys.argv) < 3 or sys.argv[2] not in ("ift", "fallback"):
    print("Usage: python makeSubsettedFont.py <input_font> <mode>")
    print("  input_font: Path to the source font file")
    print("  mode: 'ift' or 'fallback'")
    sys.exit(1)

input_font_path = sys.argv[1]
mode = sys.argv[2]

# Validate input file exists
if not os.path.exists(input_font_path):
    print(f"Error: Input font file not found: {input_font_path}")
    sys.exit(1)

# Extract base filename and extension
base_name = os.path.splitext(os.path.basename(input_font_path))[0]
extension = os.path.splitext(input_font_path)[1]

# Configure output file paths
subset_font_path = os.path.join(subsetFontPath, f"{base_name}-subset{extension}")
final_font_path = os.path.join(subsetFontPath, f"{base_name}{mode.capitalize()}{extension}")

# Step 1: Create subset font containing only required glyphs
# Only keep glyphs needed for test words "PASS" and "FAIL"
glyphs_to_keep = ["A", "F", "I", "L", "P", "S"]

font = TTFont(input_font_path)

# Configure subsetting options to preserve necessary font features
options = Options()
options.glyph_names = True      # Keep glyph names for debugging
options.notdef_glyph = True     # Keep .notdef glyph for missing characters
options.recalc_bounds = True    # Recalculate glyph bounds after subsetting
options.recalc_timestamp = True # Update font timestamp
options.layout_features = ["*"] # Keep all OpenType layout features

# Perform the subsetting operation
subsetter = Subsetter(options=options)
subsetter.populate(glyphs=glyphs_to_keep + [".notdef", "space"])
subsetter.subset(font)
font.save(subset_font_path)

# Step 2: Add ligature substitution rules to the subset font
# Reload the font to work with the subset version
font = TTFont(subset_font_path)

# Update font family name to reflect its test purpose
new_name = f"RobotoFallback{mode.capitalize()}"

# Update font naming table entries
# Name ID 1: Font Family name (e.g., "Arial")
# Name ID 2: Font Subfamily (e.g., "Regular", "Bold")  
# Name ID 4: Full font name (e.g., "Arial Regular")
# Name ID 6: PostScript name (e.g., "Arial-Regular")
name_table = font['name']

for record in name_table.names:
    if record.nameID in [1, 4, 6]:
        # Update family and full names to reflect test font purpose
        record.string = new_name.encode(record.getEncoding())
    elif record.nameID == 2:
        # Keep subfamily as "Regular"
        record.string = b"Regular"

# Ensure GSUB (Glyph Substitution) table exists for ligature rules
if "GSUB" not in font:
    font["GSUB"] = newTable("GSUB")

# Create ligature substitution rules based on test mode
# These rules determine what text appears when P or F is typed
if mode == "ift":
    # IFT success case: P shows "PASS", F shows "FAIL"
    fea_code = """
feature liga {
    sub P by P A S S;
    sub F by F A I L;
} liga;
"""
else:
    # Fallback case: P shows "FAIL", F shows "PASS" (inverted for testing)
    fea_code = """
feature liga {
    sub P by F A I L;
    sub F by P A S S;
} liga;
"""

# Apply the ligature rules to the font using FontTools feature library
addOpenTypeFeaturesFromString(font, fea_code)

# Step 3: Save the final processed font
font.save(final_font_path)
print(f"Font saved to {final_font_path}")

# Clean up: Remove the temporary subset font file
try:
    os.remove(subset_font_path)
    print(f"Removed intermediate file: {subset_font_path}")
except Exception as e:
    print(f"Warning: Could not remove {subset_font_path}: {e}")
