"""
Decoy-glyph Font Generator for the conform-stop-extend-after-errors test (issue #22).

The standard "-ift" subsetted fonts (see makeSubsettedFont.py) only contain the
glyphs needed to spell "PASS"/"FAIL" (A, F, I, L, P, S) plus space. Every
existing test's target text (title + description + result label) only ever
requires those glyphs, and per Scott's network-tab observation, they all
resolve in a single glyph-keyed patch -- there's never a second, independent
patch in the chain.

conform-stop-extend-after-errors ("In the case of all other errors the client
must not attempt to further extend the font subset.") can only be tested if
extending the font requires more than one patch: one patch must fail with a
non-load error while a second, otherwise-valid patch is still pending/
reachable. A conforming client must never apply that second patch once the
first has failed with such an error.

This script builds a *separate* variant of the -ift subsetted fonts with one
extra glyph added, copied from the original source font (glyph "B", chosen
arbitrarily -- its shape is irrelevant since it's never shown on screen) and
mapped to U+E000 (start of the Private Use Area, unused anywhere else in this
suite). That gives the segmentation/encoding pipeline a second, independent
codepoint with no Latin-script frequency data of its own, so the auto
segmenter has no basis to merge it into the same patch as the PASS/FAIL
letters -- it should end up forming its own separate glyph-keyed patch.

This is intentionally a standalone script (rather than a modification of
makeSubsettedFont.py) so the shared "-ift"/"-fallback" fonts used by every
other test are completely untouched. Output:
    build/subsettedFonts/glyf-ift-stopextend.ttf
    build/subsettedFonts/cff-ift-stopextend.otf

The decoy codepoint (U+E000) is placed off-screen in the test's HTML (see
the extraHTML for conform-stop-extend-after-errors in
ClientTestCaseGenerator.py) using absolute positioning rather than
display:none/visibility:hidden, because element.innerText -- which is what
determines the codepoints requested for extension (see resources/ift.js) --
omits text from elements that are not rendered at all.
"""

import os
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from testCaseGeneratorLib.paths import subsetFontPath, TTFSourcePath, CFFSourcePath

# Same glyph set as makeSubsettedFont.py's "ift" mode, plus one extra decoy
# glyph ("B", chosen arbitrarily) that is not part of the PASS/FAIL spelling.
DECOY_GLYPH_NAME = "B"
DECOY_CODEPOINT = 0xE000  # Private Use Area, unused elsewhere in this suite.
GLYPHS_TO_KEEP = ["A", "F", "I", "L", "P", "S", DECOY_GLYPH_NAME]


def makeStopExtendFont(sourceFontPath):
    fileName = os.path.basename(sourceFontPath)
    fileNameWithoutExt, ext = os.path.splitext(fileName)
    subsetFont = os.path.join(subsetFontPath, f"{fileNameWithoutExt}-stopextend-subset{ext}")
    finalFontPath = os.path.join(subsetFontPath, f"{fileNameWithoutExt}-ift-stopextend{ext}")

    font = TTFont(sourceFontPath)

    options = Options()
    options.glyph_names = True
    options.notdef_glyph = True
    options.recalc_bounds = True
    options.recalc_timestamp = True
    options.layout_features = ["*"]

    subsetter = Subsetter(options=options)
    subsetter.populate(glyphs=GLYPHS_TO_KEEP + [".notdef", "space"])
    subsetter.subset(font)
    font.save(subsetFont)

    font = TTFont(subsetFont)

    # Add the decoy codepoint -> decoy glyph mapping. The source font already
    # maps DECOY_GLYPH_NAME from its normal codepoint (e.g. 0x42 for "B");
    # that mapping is left in place (harmless, never typed in test HTML) and
    # U+E000 is added alongside it in every cmap subtable.
    cmapTable = font["cmap"]
    for subtable in cmapTable.tables:
        subtable.cmap[DECOY_CODEPOINT] = DECOY_GLYPH_NAME

    new_name = "RobotoFallbackIftStopextend"
    name_table = font["name"]
    for record in name_table.names:
        if record.nameID in (1, 4, 6):
            record.string = new_name.encode(record.getEncoding())
        elif record.nameID == 2:
            record.string = b"Regular"

    # Re-apply the same liga rules as the standard "ift" mode font so the
    # existing PASS/FAIL indicator behaves identically; the decoy glyph is
    # untouched by these substitution rules.
    if "GSUB" not in font:
        from fontTools.ttLib import newTable
        font["GSUB"] = newTable("GSUB")
    fea_code = """
    feature liga {
        sub P by P A S S;
        sub F by F A I L;
    } liga;
    """
    addOpenTypeFeaturesFromString(font, fea_code)

    font.save(finalFontPath)
    print(f"Font saved to {finalFontPath}")

    os.remove(subsetFont)


if __name__ == "__main__":
    makeStopExtendFont(TTFSourcePath)
    makeStopExtendFont(CFFSourcePath)
