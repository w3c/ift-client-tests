"""
This script generates the IFT client test cases. It will create a directory
one level up from the directory containing this script called "IFTClient".
That directory will have the structure:

    /IFTClient
        /Tests
            /xhtml1
                testcaseindex.xht - index of all test cases
                /resources
                    fonts.css - css for font samples
                    ift.js - IFT assigner
                    index.css - page style sheet
                    /rust-client - RUST client
                    /cc-client - Brotli compression library
                    /fallback - fallback fonts

Within this script, each test case is generated with a call to the
writeTest function.
"""

import os
import glob
import shutil
import struct
import zipfile
from fontTools.ttLib import TTFont
from testCaseGeneratorLib.paths import (
    resourcesDirectory,
    clientDirectory,
    clientTestDirectory,
    clientTestResourcesDirectory,
    fallbackFontPath,
    buildDirectory
)
from testCaseGeneratorLib.html import generateClientIndexHTML, expandSpecLinks
from testCaseGeneratorLib.iftFile import IFTFile
from testCaseGeneratorLib.helpers import (
    decode_id32_to_int,
    id32_no_strip,
    replace_format2_url_template,
    compute_id64_file_name,
    compute_id64_no_strip,
)

# IFT Table Header Offsets
IFT_ENTRIES_OFFSET_START = 25
IFT_ENTRIES_OFFSET_END = 29
IFT_FORMAT_OFFSET = 0
# URL Template offsets (Format 2 fixed header layout):
# format(1) + reserved(3) + flags(1) + compatibilityId(16) +
# defaultPatchFormat(1) + entryCount(3) + entriesOffset(4) +
# entryIdStringDataOffset(4) + urlTemplateLength(2) + urlTemplate[...]
IFT_URL_TEMPLATE_OFFSET = 35
# Other constants
IFT_FONT_FILENAME = "myfont-mod.ift.woff2"

# ------------------
# Directory Creation
# (if needed)
# ------------------

if not os.path.exists(clientDirectory):
    os.makedirs(clientDirectory)
if not os.path.exists(clientTestDirectory):
    os.makedirs(clientTestDirectory)
if not os.path.exists(clientTestResourcesDirectory):
    os.makedirs(clientTestResourcesDirectory)

# -------------------
# Move HTML Resources
# -------------------

# index css
destPath = os.path.join(clientTestResourcesDirectory, "index.css")
if os.path.exists(destPath):
    os.remove(destPath)
shutil.copy(os.path.join(resourcesDirectory, "index.css"), destPath)

# fonts css
destPath = os.path.join(clientTestResourcesDirectory, "fonts.css")
if os.path.exists(destPath):
    os.remove(destPath)
shutil.copy(os.path.join(resourcesDirectory, "fonts.css"), destPath)

# ift js
destPath = os.path.join(clientTestResourcesDirectory, "ift.js")
if os.path.exists(destPath):
    os.remove(destPath)
shutil.copy(os.path.join(resourcesDirectory, "ift.js"), destPath)

# brotli JS
destPath = os.path.join(clientTestResourcesDirectory,"cc-client")
if os.path.exists(destPath):
    shutil.rmtree(destPath)
shutil.copytree(os.path.join(resourcesDirectory, "cc-client"), destPath)

# rust client
destPath = os.path.join(clientTestResourcesDirectory,"rust-client")
if os.path.exists(destPath):
    shutil.rmtree(destPath)
shutil.copytree(os.path.join(resourcesDirectory, "rust-client"), destPath)

# fallback font
destPath = os.path.join(clientTestResourcesDirectory,"fallback")
if os.path.exists(destPath):
    shutil.rmtree(destPath)
os.makedirs(destPath)
shutil.copy(fallbackFontPath, os.path.join(destPath, "Roboto.ttf"))

# ---------------
# Test Case Index
# ---------------

# As the tests are generated a log will be kept.
# This log will be translated into an index after
# all of the tests have been written.

indexNote = """
index note
""".strip()


clientNote = """
client note
""".strip()

groupDefinitions = [
    # identifier, title, spec section, category note
    ("client", "Client Conformance Tests", expandSpecLinks("#DataTables"), clientNote),
]

testRegistry = {}
for group in groupDefinitions:
    tag = group[0]
    testRegistry[tag] = []

# -----------------
# Test Case Writing
# -----------------

registeredIdentifiers = set()
registeredTitles = set()
registeredDescriptions = set()

def writeTest(identifier, title, description, fontFormats, func, funcArgs=None, specLink=None, credits=[], shouldShowIFT=False, extraHTML=None):
    """
    This function generates all of the files needed by a test case and
    registers the case with the suite. The arguments:

    identifier: The identifier for the test case. The identifier must be
    a - separated sequence of group name (from the groupDefinitions
    listed above), and test case description (arbitrary length).

    title: A thorough, but not too long, title for the test case.

    description: A detailed statement about what the test case is proving.

    func: The function that generates the IFT files specific for the test.

    specLink: The anchor in the WOFF spec that the test case is testing.

    credits: A list of dictionaries defining the credits for the test case. The
    dictionaries must have this form:

        title="Name of the autor or reviewer",
        role="author or reviewer",
        link="mailto:email or http://contactpage"

    shouldShowIFT: A boolean indicating if the SFNT is valid enough for
    conversion to WOFF.

    extraHTML: Optional raw HTML (and inline <script>/<iframe> markup) that is
    inserted verbatim into the test case's details block on the generated
    index page. Used for tests that need custom client-side script assertions
    beyond the standard "does the IFT font render" check (e.g. tests that
    require a second Document/iframe to verify cross-document behavior).

    """
    print("Compiling %s..." % identifier)
    for fontFormat in fontFormats:
        if funcArgs is not None:
            func(fontFormat, *funcArgs)
        else:
            func(fontFormat)
    assert identifier not in registeredIdentifiers, "Duplicate identifier! %s" % identifier
    assert title not in registeredTitles, "Duplicate title! %s" % title
    assert description not in registeredDescriptions, "Duplicate description! %s" % description
    registeredIdentifiers.add(identifier)
    registeredTitles.add(title)
    registeredDescriptions.add(description)

    specLink = expandSpecLinks(specLink)

    # register the test
    tag = identifier.split("-")[0]
    testRegistry[tag].append(
        dict(
            identifier=identifier,
            title=title,
            description=description,
            shouldShowIFT=shouldShowIFT,
            specLink=specLink,
            fontFormats=fontFormats,
            extraHTML=extraHTML,
        )
    )


# start of tests
def makeIFTWithFormatID(fontFormat, formatId, testName):
    nft = IFTFile(testName,fontFormat, IFT_FONT_FILENAME)
    raw = nft.getIFTTableData()
    raw[IFT_FORMAT_OFFSET] = formatId
    nft.setIFTTableData(bytes(raw))
    nft.writeTestIFTFile()

testType = "client"

testTag = "conform-format2-valid-format-number"
identifierString= "%s-%s" % (testType, testTag)
fontFormats = ["GLYF","CFF"]
writeTest(
    identifier=identifierString,
    title="Format 2 with invalid format number",
    description="The IFT table 'format' field for a format 2 is set to 3, which is an invalid format number.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink= "#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithFormatID,
    funcArgs=(3, identifierString)
)

def makeIFTWithInvalidDesignSpaceSegmentEndValue(fontFormat, testName):
    # This test is only for format 2. For reference: https://www.w3.org/TR/IFT/#patch-map-format-2
    nft = IFTFile(testName,fontFormat, IFT_FONT_FILENAME)
    iftData = nft.getIFTTableData()

    entriesOffset = int.from_bytes(iftData[IFT_ENTRIES_OFFSET_START:IFT_ENTRIES_OFFSET_END], "big")
    entriesData = iftData[entriesOffset:]
    offset = 0

    # First Mapping Entry
    formatFlags = entriesData[offset]
    offset += 1

    hasFeature = formatFlags & 0b00000001
    if hasFeature:
        # featureCount + featureTags
        featureCount = entriesData[offset]
        offset += 1
        offset += featureCount * 4  # skip featureTags

        # designSpaceCount
        designSpaceCount = int.from_bytes(entriesData[offset:offset+2], "big")
        offset += 2

        if designSpaceCount > 0:
            # first Design Space Segment
            segmentOffset = offset
            # skip tag (4) + start (4)
            endOffset = segmentOffset + 8

            # set end to invalid value
            invalidEndFixed = int(-1 * (1 << 16))  # negative 16.16 fixed
            entriesData[endOffset:endOffset+4] = struct.pack(">i", invalidEndFixed)
    iftData = bytearray(iftData[:entriesOffset]) + entriesData
    nft.setIFTTableData(bytes(iftData))
    # Write back
    nft.writeTestIFTFile()

testTag = "conform-design-space-segment-end-valid-value"
identifierString= "%s-%s" % (testType, testTag)
fontFormats = ["GLYF","CFF"]
writeTest(
    identifier=identifierString,
    title="Format 2 with invalid design space segment end value",
    description="The IFT table design space segment end value is set to an invalid negative number.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink= "#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithInvalidDesignSpaceSegmentEndValue,
    funcArgs=(identifierString,)
)

def removeTable(fontFormat, testName, tableTag):
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.getIFTTableData()
    nft.removeTable(tableTag)
    nft.writeTestIFTFile()

testTag = "extend-font-subset_require-ift-table"
identifierString= "%s-%s" % (testType, testTag)
fontFormats = ["GLYF","CFF"]
writeTest(
    identifier=identifierString,
    title="IFT table missing",
    description="All incremental fonts must contain the 'IFT ' table.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink= "#%s" % identifierString,
    fontFormats=fontFormats,
    func=removeTable,
    funcArgs=(identifierString,"IFT ",)
)

def makeIFTWithInvalidTableKeyedPatchFormat(fontFormat, testName):
    """Modify all table keyed patch files to have an invalid format tag.

    Per the spec (§6.2 Table Keyed), the format field of a table keyed patch
    must be set to 'iftk'. This test sets it to 'XXXX' so the client should
    reject the patch during step 2 of Apply table keyed patch.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.getIFTTableData()

    # Modify all _tk patch files in the test directory to have an invalid format tag
    destDir = os.path.join(nft.testDirectory, fontFormat)
    for tkFile in glob.glob(os.path.join(destDir, "*_tk")):
        with open(tkFile, "rb") as f:
            data = bytearray(f.read())
        # The first 4 bytes are the format Tag, which must be 'iftk'.
        # Replace with an invalid value.
        data[0:4] = b'XXXX'
        with open(tkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()

testTag = "conform-table-keyed-format-equals-iftk"
identifierString= "%s-%s" % (testType, testTag)
fontFormats = ["GLYF","CFF"]
writeTest(
    identifier=identifierString,
    title="Table keyed patch with invalid format tag",
    description="The table keyed patch format field is set to an invalid value (not 'iftk'). The client must reject the patch.",
    shouldShowIFT=False,
    credits=[dict(title="Dileep Maurya", role="author", link="https://github.com/dmaurya-edge")],
    specLink= "#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithInvalidTableKeyedPatchFormat,
    funcArgs=(identifierString,)
)

def makeIFTWithInvalidGlyphKeyedPatchFormat(fontFormat, testName):
    """Modify all glyph keyed patch files to have an invalid format tag.

    Per the spec (§6.3 Glyph Keyed), the format field of a glyph keyed patch
    must be set to 'ifgk'. This test sets it to 'XXXX' so the client should
    reject the patch.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.getIFTTableData()

    # Modify all _gk patch files in the test directory to have an invalid format tag
    destDir = os.path.join(nft.testDirectory, fontFormat)
    for gkFile in glob.glob(os.path.join(destDir, "*_gk")):
        with open(gkFile, "rb") as f:
            data = bytearray(f.read())
        # The first 4 bytes are the format Tag, which must be 'ifgk'.
        # Replace with an invalid value.
        data[0:4] = b'XXXX'
        with open(gkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()

testTag = "conform-glyph-keyed-format-equals-ifgk"
identifierString= "%s-%s" % (testType, testTag)
fontFormats = ["GLYF","CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch with invalid format tag",
    description="The glyph keyed patch format field is set to an invalid value (not 'ifgk'). The client must reject the patch.",
    shouldShowIFT=False,
    credits=[dict(title="Takeru Suzuki", role="author", link="https://github.com/terkel")],
    specLink= "#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithInvalidGlyphKeyedPatchFormat,
    funcArgs=(identifierString,)
)

def makeIFTWithUnsortedTableKeyedPatchOffsets(fontFormat, testName):
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.getIFTTableData()
    nft.writeTestIFTFile()

    # Modify the _tk patch files in the test directory to have unsorted offsets
    tkDir = os.path.join(nft.testDirectory, fontFormat)
    for tkPath in glob.glob(os.path.join(tkDir, "*_tk")):
        with open(tkPath, "rb") as f:
            data = bytearray(f.read())

        # Table keyed patch layout:
        #   0: format (Tag, 4 bytes)
        #   4: reserved (uint32, 4 bytes)
        #   8: compatibilityId (uint32[4], 16 bytes)
        #  24: patchesCount (uint16, 2 bytes)
        #  26: patches (Offset32[patchesCount+1], 4 bytes each)
        patchesCount = struct.unpack(">H", data[24:26])[0]
        numOffsets = patchesCount + 1
        if numOffsets < 2:
            continue

        offsetsStart = 26
        offsets = []
        for i in range(numOffsets):
            pos = offsetsStart + i * 4
            offsets.append(struct.unpack(">I", data[pos:pos+4])[0])

        # Reverse the offsets so they are no longer in ascending order
        offsets.reverse()

        for i in range(numOffsets):
            pos = offsetsStart + i * 4
            data[pos:pos+4] = struct.pack(">I", offsets[i])

        with open(tkPath, "wb") as f:
            f.write(data)

testTag = "conform-table-keyed-patches-sort-ascending"
identifierString= "%s-%s" % (testType, testTag)
fontFormats = ["GLYF","CFF"]
writeTest(
    identifier=identifierString,
    title="Table keyed patch with unsorted offsets",
    description="The patches offsets array in the table keyed patch is not sorted in ascending order.",
    shouldShowIFT=False,
    credits=[dict(title="Takeru Suzuki", role="author", link="https://github.com/terkel")],
    specLink= "#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithUnsortedTableKeyedPatchOffsets,
    funcArgs=(identifierString,)
)

def makeIFTWithDuplicateGlyphKeyedTables(fontFormat, testName):
    import brotli
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.getIFTTableData()

    # Modify all _gk patch files in the test directory
    destDir = os.path.join(nft.testDirectory, fontFormat)
    for gkFile in glob.glob(os.path.join(destDir, "*_gk")):
        with open(gkFile, "rb") as f:
            data = bytearray(f.read())

        # Glyph keyed patch header layout:
        #   0-3:   format (Tag, 4 bytes) = 'ifgk'
        #   4-7:   reserved (uint32, 4 bytes)
        #   8:     flags (uint8, 1 byte)
        #   9-24:  compatibilityId (uint32[4], 16 bytes)
        #   25-28: maxUncompressedLength (uint32, 4 bytes)
        #   29+:   brotliStream (variable)
        flags = data[8]
        brotli_data = bytes(data[29:])
        decompressed = bytearray(brotli.decompress(brotli_data))

        # GlyphPatches layout:
        #   0-3:  glyphCount (uint32)
        #   4:    tableCount (uint8)
        #   5+:   glyphIds[glyphCount] (uint16 or uint24 each)
        #   then: tables[tableCount] (Tag, 4 bytes each)
        glyph_count = struct.unpack(">I", decompressed[0:4])[0]
        table_count = decompressed[4]
        use_uint24 = flags & 1
        gid_size = 3 if use_uint24 else 2

        # Calculate offset to tables array
        tables_offset = 5 + glyph_count * gid_size
        first_tag = decompressed[tables_offset:tables_offset + 4]

        # Set tableCount to 2 and insert a duplicate of the first tag
        decompressed[4] = 2
        decompressed[tables_offset + 4:tables_offset + 4] = first_tag

        # Re-compress and write back
        recompressed = brotli.compress(bytes(decompressed))
        struct.pack_into(">I", data, 25, len(decompressed))
        data[29:] = recompressed

        with open(gkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()

testTag = "conform-glyph-keyed-tables-sort-ascending-unique"
identifierString= "%s-%s" % (testType, testTag)
fontFormats = ["GLYF","CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch with duplicate table tags",
    description="The glyph keyed patch tables array contains duplicate values. The client must reject the patch.",
    shouldShowIFT=False,
    credits=[dict(title="Dileep Maurya", role="author", link="https://github.com/dmaurya-edge")],
    specLink= "#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithDuplicateGlyphKeyedTables,
    funcArgs=(identifierString,)
)


def makeIFTWithUnstrippedId32PatchNames(fontFormat, testName):
    """
    Rename patch files to use the un-stripped (wrong) id32 encoding, then verify
    that a correct client (which DOES strip leading zeros) cannot find them.

    Tests conform-entry-id-must-be-converted: 'When entry ID is an unsigned integer
    it must first be converted to a big endian 32 bit unsigned integer, but then all
    leading bytes that are equal to 0 are removed before encoding.'

    Patches are renamed from the correctly-stripped id32 names (e.g. '04.ift_tk'
    for entry 1) to the incorrectly un-stripped 4-byte id32 names (e.g.
    '0000008.ift_tk' for entry 1). A conforming client computes '04.ift_tk' for
    entry 1, which no longer exists, so it cannot load the font.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)

    dest_dir = os.path.join(nft.testDirectory, fontFormat)
    # Rename each *.ift_tk from its correct id32 name to the un-stripped variant
    for old_path in glob.glob(os.path.join(dest_dir, "*_tk")):
        old_basename = os.path.basename(old_path)
        id32_part = old_basename.replace(".ift_tk", "")
        # Only rename files whose names are valid base32hex (id32-encoded)
        if not all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUV" for c in id32_part.upper()):
            continue
        entry_id = decode_id32_to_int(id32_part)
        wrong_name = id32_no_strip(entry_id) + ".ift_tk"
        shutil.move(old_path, os.path.join(dest_dir, wrong_name))

    nft.writeTestIFTFile()

testTag = "conform-entry-id-must-be-converted"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="URL template id32 must strip leading zero bytes from integer entry IDs",
    description="Patch files are stored at the un-stripped base32hex names "
                "(e.g. '0000008.ift_tk' for entry 1). A conforming client strips "
                "leading zero bytes and looks for '04.ift_tk', which does not exist, "
                "so the IFT font cannot be loaded.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithUnstrippedId32PatchNames,
    funcArgs=(identifierString,)
)

def madeIFTwithInvalidOpCodeInURLTemplate(fontFormat, testName, url_template_bytes):
    """Embed invalid URL template bytes per negative examples in §5.3.3 URL Templates."""
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    iftData = nft.getIFTTableData()
    iftData = replace_format2_url_template(iftData, bytes(url_template_bytes))
    nft.setIFTTableData(bytes(iftData))
    nft.writeTestIFTFile()

# https://www.w3.org/TR/IFT/#example-305f10ca example of negative tests
_url_template_negative_tests = [
    (
        "invalid-opcode-150",
        "URL template with invalid op code 150",
        "Expand URL Template must return an error when the template contains op code 150 (not in the op code table).",
        [4, *map(ord, "foo/"), 150],
    ),
    (
        "opcode-zero",
        "URL template with invalid literal op code 0",
        "Expand URL Template must return an error when a literal op code requests 0 bytes (op code 0 is invalid).",
        [4, *map(ord, "foo/"), 0, 128],
    ),
    (
        "literal-insufficient-bytes",
        "URL template with literal op code requesting too few bytes",
        "Expand URL Template must return an error when a literal op code requests 10 bytes but fewer remain in the template.",
        [10, *map(ord, "foo/"), 128],
    ),
    (
        "literal-invalid-utf8",
        "URL template with invalid UTF-8 literal",
        "Expand URL Template must return an error when literal bytes are not valid UTF-8.",
        [4, *map(ord, "foo/"), 0x85, 128],
    ),
]

for suffix, title, description, template_bytes in _url_template_negative_tests:
    identifier_string = "%s-url-templates_%s" % (testType, suffix)
    writeTest(
        identifier=identifier_string,
        title=title,
        description=description,
        shouldShowIFT=False,
        credits=[dict(title="Yongji Chen", role="author", link="https://github.com/yChenMonotype")],
        specLink="#url-templates",
        fontFormats=["GLYF", "CFF"],
        func=madeIFTwithInvalidOpCodeInURLTemplate,
        funcArgs=(identifier_string, bytes(template_bytes)),
    )


def madeIFTWithCustomURLTemplate(fontFormat, testName):
    # copy build/URL_TEMPLATE/IFT/{fontFormat} to test directory if not exists
    if not os.path.exists(os.path.join(clientTestDirectory, testName, fontFormat)):
        shutil.copytree(os.path.join(buildDirectory, "URL_TEMPLATE", "IFT", fontFormat), os.path.join(clientTestDirectory, testName, fontFormat))
    # rename the font.ift.woff2 file to myfont-mod.ift.woff2 if exists
    if os.path.exists(os.path.join(clientTestDirectory, testName, fontFormat, "font.ift.woff2")):
        os.rename(os.path.join(clientTestDirectory, testName, fontFormat, "font.ift.woff2"), os.path.join(clientTestDirectory, testName, fontFormat, "myfont-mod.ift.woff2"))

testTag = "url-template-prefix"
identifierString= "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Override URL template prefix",
    description=f"The URL template prefix is overridden to a custom value. For example, setting the url template prefix to '\\x08patches/\\x80'will cause the client to look for patches(.ift_tk and .ift_gk) in the 'patches' directory in relative to the font.ift.woff2 file.",
    shouldShowIFT=True,
    credits=[dict(title="Yongji Chen", role="author", link="https://github.com/yChenMonotype")],
    specLink="#url-templates",
    fontFormats=fontFormats,
    func=madeIFTWithCustomURLTemplate,
    funcArgs=(identifierString,)
)

def makeIFTWithId64OpcodeRenamedPatches(fontFormat, testName):
    """
    Switch the URL template opcode to id64 (0x85) and rename patch files to
    use base64url names with '=' padding (e.g. 'AQ==.ift_tk' for entry 1).

    Tests conform-equal-sign-encoded: 'Because the padding character is =,
    it must be URL-encoded as %3D.'

    A conforming client:
      1. Computes the id64 name for entry 1: [0x01] -> base64url -> 'AQ=='
      2. URL-encodes '=' as '%3D' -> requests 'AQ%3D%3D.ift_tk'
      3. The static server decodes '%3D' -> '=' and serves 'AQ==.ift_tk'
      4. The IFT font loads successfully.

    This is a positive test (shouldShowIFT=True): a conforming client can load
    the font, so 'P' renders as PASS via the IFT font. A non-conforming client
    that requests 'AQ==.ift_tk' directly also resolves to the same file on a
    standard server, so this test primarily validates the id64 opcode path
    end-to-end.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    raw = nft.getIFTTableData()
    # Change opcode from 0x80 (Insert id32) to 0x85 (Insert id64)
    raw[IFT_URL_TEMPLATE_OFFSET] = 0x85
    nft.setIFTTableData(bytes(raw))

    # Rename *.ift_tk files from id32 names to id64 names (with '=' padding)
    dest_dir = os.path.join(nft.testDirectory, fontFormat)
    for old_path in glob.glob(os.path.join(dest_dir, "*_tk")):
        old_basename = os.path.basename(old_path)
        id32_part = old_basename.replace(".ift_tk", "")
        if not all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUV" for c in id32_part.upper()):
            continue
        entry_id = decode_id32_to_int(id32_part)
        id64_name = compute_id64_file_name(entry_id) + ".ift_tk"
        shutil.move(old_path, os.path.join(dest_dir, id64_name))

    nft.writeTestIFTFile()

testTag = "conform-equal-sign-encoded"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="URL template id64 base64url '=' padding must be URL-encoded as %3D",
    description="The URL template uses the id64 opcode (0x85). Patch files are "
                "named with base64url '=' padding (e.g. 'AQ==.ift_tk' for entry 1). "
                "A conforming client URL-encodes '=' as '%3D' and requests "
                "'AQ%3D%3D.ift_tk'. The server decodes '%3D' to '=' and serves "
                "'AQ==.ift_tk', allowing the IFT font to load successfully.",
    shouldShowIFT=True,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithId64OpcodeRenamedPatches,
    funcArgs=(identifierString,)
)


def makeIFTWithUnsortedGlyphDataOffsets(fontFormat, testName):
    """
    Reverse the glyphDataOffsets array inside each glyph-keyed patch file so
    that the offsets are no longer in ascending order.

    Tests conform-glyph-keyed-glyph-data-offsets-sort-ascending:
    'Offsets must be sorted in ascending order.'

    GlyphPatches layout (after brotli decompression):
      0-3:   glyphCount (uint32)
      4:     tableCount (uint8)
      5+:    glyphIds[glyphCount]  (uint16 or uint24, per flags bit 0)
      then:  tables[tableCount]    (Tag, 4 bytes each)
      then:  glyphDataOffsets[glyphCount * tableCount + 1] (Offset32 each)
      then:  glyphData[variable]
    """
    import brotli

    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)

    destDir = os.path.join(nft.testDirectory, fontFormat)
    for gkFile in glob.glob(os.path.join(destDir, "*_gk")):
        with open(gkFile, "rb") as f:
            data = bytearray(f.read())

        # Outer header: format(4) reserved(4) flags(1) compatibilityId(16)
        #               maxUncompressedLength(4) brotliStream(...)
        flags = data[8]
        brotli_data = bytes(data[29:])
        decompressed = bytearray(brotli.decompress(brotli_data))

        glyph_count = struct.unpack(">I", decompressed[0:4])[0]
        table_count = decompressed[4]
        gid_size = 3 if (flags & 1) else 2

        # Navigate to glyphDataOffsets
        tables_offset = 5 + glyph_count * gid_size
        glyph_data_offsets_offset = tables_offset + table_count * 4
        num_offsets = glyph_count * table_count + 1

        if num_offsets >= 2:
            # Read all offsets
            offsets = [
                struct.unpack(">I", decompressed[glyph_data_offsets_offset + i * 4:
                                                 glyph_data_offsets_offset + i * 4 + 4])[0]
                for i in range(num_offsets)
            ]
            # Reverse so they are no longer ascending
            offsets.reverse()
            for i, off in enumerate(offsets):
                struct.pack_into(">I", decompressed,
                                 glyph_data_offsets_offset + i * 4, off)

        recompressed = brotli.compress(bytes(decompressed))
        struct.pack_into(">I", data, 25, len(decompressed))
        data[29:] = recompressed

        with open(gkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()

testTag = "conform-glyph-keyed-glyph-data-offsets-sort-ascending"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch with unsorted glyphDataOffsets",
    description="The glyphDataOffsets array in the glyph keyed patch is reversed so the "
                "offsets are no longer in ascending order. The client must reject the patch.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithUnsortedGlyphDataOffsets,
    funcArgs=(identifierString,)
)

def makeIFTWithUnsortedGlyphIds(fontFormat, testName):
    """
    Reverse the glyphIds array inside each glyph-keyed patch file so that
    the glyph IDs are no longer in ascending sorted order.

    Tests conform-glyph-keyed-glyph-ids-sort-ascending-unique:
    'Must be in ascending sorted order and must not contain any duplicate values.'

    GlyphPatches layout (after brotli decompression):
      0-3:   glyphCount (uint32)
      4:     tableCount (uint8)
      5+:    glyphIds[glyphCount]  (uint16 or uint24, per flags bit 0)
      then:  tables[tableCount]    (Tag, 4 bytes each)
      then:  glyphDataOffsets[...]
      then:  glyphData[...]
    """
    import brotli

    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)

    destDir = os.path.join(nft.testDirectory, fontFormat)
    for gkFile in glob.glob(os.path.join(destDir, "*_gk")):
        with open(gkFile, "rb") as f:
            data = bytearray(f.read())

        # Outer header: format(4) reserved(4) flags(1) compatibilityId(16)
        #               maxUncompressedLength(4) brotliStream(...)
        flags = data[8]
        brotli_data = bytes(data[29:])
        decompressed = bytearray(brotli.decompress(brotli_data))

        glyph_count = struct.unpack(">I", decompressed[0:4])[0]
        gid_size = 3 if (flags & 1) else 2

        assert glyph_count >= 2, (
            f"{gkFile}: glyph_count={glyph_count}, need at least 2 to reverse glyphIds. "
            "The source glyph-keyed patch must contain multiple glyphs for this test."
        )

        # Read all glyph IDs
        gids = [
            int.from_bytes(decompressed[5 + i * gid_size:5 + i * gid_size + gid_size], 'big')
            for i in range(glyph_count)
        ]
        # Reverse so they are no longer in ascending order
        gids.reverse()
        for i, gid in enumerate(gids):
            decompressed[5 + i * gid_size:5 + i * gid_size + gid_size] = gid.to_bytes(gid_size, 'big')

        recompressed = brotli.compress(bytes(decompressed))
        struct.pack_into(">I", data, 25, len(decompressed))
        data[29:] = recompressed

        with open(gkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()

testTag = "conform-glyph-keyed-glyph-ids-sort-ascending-unique"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch with unsorted glyph IDs",
    description="The glyphIds array in the glyph keyed patch is reversed so the "
                "glyph IDs are no longer in ascending sorted order. The client must "
                "reject the patch.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithUnsortedGlyphIds,
    funcArgs=(identifierString,)
)


def _find_and_corrupt_sparse_bit_set(iftData):
    """
    Navigate Format 2 IFT table entries to find the first codePoints sparse bit set,
    then corrupt its header byte so that H exceeds the maximum height for the
    given branch factor.

    Per §sparse-bit-set-decoding step 2: 'If H is greater than the Maximum Height
    in the Branch Factor Encoding table in the row for B then the encoding is invalid,
    return an error.'

    Branch Factor Encoding (spec §sparse-bit-set-decoding):
      bits 0-1 = 0b00 → B=2,  maxH=31
      bits 0-1 = 0b01 → B=4,  maxH=16
      bits 0-1 = 0b10 → B=8,  maxH=11
      bits 0-1 = 0b11 → B=32, maxH=7
    """
    iftData = bytearray(iftData)
    entry_id_string_data_offset = int.from_bytes(iftData[29:33], 'big')
    entries_offset = int.from_bytes(iftData[25:29], 'big')
    entry_count = int.from_bytes(iftData[22:25], 'big')

    offset = entries_offset
    for _ in range(entry_count):
        format_flags = iftData[offset]
        offset += 1

        # bit 0: featureCount + featureTags + designSpaceCount + designSpaceSegments
        if format_flags & 0x01:
            feature_count = iftData[offset]
            offset += 1 + feature_count * 4  # featureCount byte + featureTags (4 bytes each)
            design_space_count = int.from_bytes(iftData[offset:offset + 2], 'big')
            offset += 2 + design_space_count * 12  # designSpaceCount uint16 + segments (12 bytes each)

        # bit 1: childEntryMatchModeAndCount + childEntryIndices
        if format_flags & 0x02:
            child_entry_match_mode_and_count = iftData[offset]
            offset += 1
            child_entry_count = child_entry_match_mode_and_count & 0x7F
            offset += child_entry_count * 3  # uint24 each

        # bit 2: entryIdDelta (variable int24, LSB continuation) or entryIdStringLength
        if format_flags & 0x04:
            if entry_id_string_data_offset == 0:
                # entryIdDelta: LSB set means another delta follows
                while True:
                    delta = int.from_bytes(iftData[offset:offset + 3], 'big')
                    offset += 3
                    if not (delta & 0x01):
                        break
            else:
                # entryIdStringLength: MSB set means another length follows
                while True:
                    length_val = int.from_bytes(iftData[offset:offset + 3], 'big')
                    offset += 3
                    if not (length_val & 0x800000):
                        break

        # bit 3: patchFormat (1 byte)
        if format_flags & 0x08:
            offset += 1

        # bits 4 and/or 5: bias (if bit 5 set) then codePoints sparse bit set
        if format_flags & 0x30:
            if format_flags & 0x20:  # bit 5: bias present
                if format_flags & 0x10:  # bits 4+5: uint24 bias
                    offset += 3
                else:                    # bit 5 only: uint16 bias
                    offset += 2

            # Corrupt the sparse bit set header byte
            header_byte = iftData[offset]
            branch_factor_bits = header_byte & 0x03
            max_heights = {0: 31, 1: 16, 2: 11, 3: 7}
            max_h = max_heights[branch_factor_bits]
            # Set H = max_h + 1 (invalid). H occupies bits 2-6 (5 bits).
            invalid_h = (max_h + 1) & 0x1F
            iftData[offset] = (header_byte & 0x03) | (invalid_h << 2)
            return bytes(iftData)

    raise ValueError("No codePoints (sparse bit set) field found in any mapping entry")


def makeIFTWithInvalidSparseBitSet(fontFormat, testName):
    """
    Corrupt the first codePoints sparse bit set in the IFT table so that its
    height H exceeds the maximum allowed for the encoded branch factor.

    Tests conform-sparse-bit-set-decoding: if the decoding algorithm returns
    an error the client must treat the patch map as invalid and not apply any
    patches, causing the IFT font to fail to render.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    raw = nft.getIFTTableData()
    corrupted = _find_and_corrupt_sparse_bit_set(bytes(raw))
    nft.setIFTTableData(corrupted)
    nft.writeTestIFTFile()


testTag = "conform-sparse-bit-set-decoding"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Sparse bit set with height exceeding maximum for branch factor",
    description="The codePoints sparse bit set in a mapping entry has a height H that "
                "exceeds the maximum allowed for its branch factor. The client must treat "
                "the patch map as invalid and not render using the IFT font.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithInvalidSparseBitSet,
    funcArgs=(identifierString,)
)


def makeIFTWithUnsupportedTableInGlyphPatch(fontFormat, testName):
    """
    Add an unsupported table entry ('hmtx') with zero-length glyph data alongside
    the existing supported table entry in each glyph-keyed patch file.

    Tests conform-table-entries-ignore-others:
    'Entries for tables of any other types must be ignored.'

    A conforming client ignores the 'hmtx' entry and still applies the supported
    table (glyf or CFF), allowing the IFT font to load and render correctly.
    shouldShowIFT=True: the font renders correctly when the client correctly
    ignores the unsupported table entry.

    GlyphPatches layout (decompressed):
      0-3:   glyphCount (uint32)
      4:     tableCount (uint8)
      5+:    glyphIds[glyphCount]  (uint16 or uint24 per flags bit 0)
      then:  tables[tableCount]    (Tag, 4 bytes each)
      then:  glyphDataOffsets[glyphCount * tableCount + 1] (Offset32 each)
      then:  glyphData[variable]

    We append 'hmtx' as an additional table tag and add glyphCount new offsets
    (all equal to the sentinel value) so the new table has zero-length glyph data
    for every glyph.
    """
    import brotli

    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)

    destDir = os.path.join(nft.testDirectory, fontFormat)
    for gkFile in glob.glob(os.path.join(destDir, "*_gk")):
        with open(gkFile, "rb") as f:
            data = bytearray(f.read())

        flags = data[8]
        gid_size = 3 if (flags & 1) else 2
        decompressed = bytearray(brotli.decompress(bytes(data[29:])))

        glyph_count = struct.unpack(">I", decompressed[0:4])[0]
        table_count = decompressed[4]

        tables_offset = 5 + glyph_count * gid_size
        glyph_data_offsets_offset = tables_offset + table_count * 4
        num_offsets = glyph_count * table_count + 1
        glyph_data_start = glyph_data_offsets_offset + num_offsets * 4

        # Offsets are absolute from the start of the decompressed buffer.
        # Adding 1 table tag (4 bytes) and glyph_count new offset entries
        # (glyph_count * 4 bytes) shifts glyphData forward by this delta.
        # All existing offsets must be adjusted accordingly.
        offset_delta = 4 + glyph_count * 4

        # Read and adjust all existing offsets (including the sentinel)
        existing_offsets = [
            struct.unpack(">I", decompressed[
                glyph_data_offsets_offset + i * 4:
                glyph_data_offsets_offset + i * 4 + 4
            ])[0] + offset_delta
            for i in range(num_offsets)
        ]
        new_sentinel = existing_offsets[-1]

        new_decompressed = bytearray()
        # glyphCount (unchanged)
        new_decompressed.extend(struct.pack(">I", glyph_count))
        # tableCount + 1
        new_decompressed.append(table_count + 1)
        # glyphIds (unchanged)
        new_decompressed.extend(decompressed[5:tables_offset])
        # existing table tags (unchanged)
        new_decompressed.extend(decompressed[tables_offset:glyph_data_offsets_offset])
        # new unsupported table tag
        new_decompressed.extend(b'hmtx')
        # adjusted existing offsets minus the sentinel
        for off in existing_offsets[:-1]:
            new_decompressed.extend(struct.pack(">I", off))
        # glyph_count new offsets for 'hmtx', all equal to new_sentinel (zero-length data)
        for _ in range(glyph_count):
            new_decompressed.extend(struct.pack(">I", new_sentinel))
        # new sentinel
        new_decompressed.extend(struct.pack(">I", new_sentinel))
        # glyph data (unchanged)
        new_decompressed.extend(decompressed[glyph_data_start:])

        recompressed = brotli.compress(bytes(new_decompressed))
        struct.pack_into(">I", data, 25, len(new_decompressed))
        data[29:] = recompressed

        with open(gkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()


testTag = "conform-table-entries-ignore-others"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch with unsupported table entry must be ignored",
    description="Each glyph-keyed patch contains an entry for the unsupported table 'hmtx' "
                "alongside the supported table entry. A conforming client ignores the 'hmtx' "
                "entry and still applies the supported table, allowing the IFT font to render "
                "correctly.",
    shouldShowIFT=True,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithUnsupportedTableInGlyphPatch,
    funcArgs=(identifierString,)
)


def makeIFTWithUnstrippedId64PatchNames(fontFormat, testName):
    """
    Switch the URL template opcode to id64 (0x85) and rename patch files to
    use the un-stripped 4-byte base64url encoding.

    Tests conform-entry-id-converted (id64 variant):
    'When entry ID is an unsigned integer it must first be converted to a big
    endian 32 bit unsigned integer, but then all leading bytes that are equal
    to 0 are removed before encoding.'

    Patches are renamed from the correctly-stripped id64 names (e.g. 'AQ==.ift_tk'
    for entry 1) to the incorrectly un-stripped 4-byte base64url names (e.g.
    'AAAAAQ==.ift_tk' for entry 1). A conforming client strips leading zero bytes
    and looks for 'AQ==.ift_tk' (URL-encoded as 'AQ%3D%3D.ift_tk'), which does
    not exist, so the IFT font cannot be loaded.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    raw = nft.getIFTTableData()
    raw[IFT_URL_TEMPLATE_OFFSET] = 0x85  # id64 opcode
    nft.setIFTTableData(bytes(raw))

    dest_dir = os.path.join(nft.testDirectory, fontFormat)
    for old_path in glob.glob(os.path.join(dest_dir, "*_tk")):
        old_basename = os.path.basename(old_path)
        id32_part = old_basename.replace(".ift_tk", "")
        if not all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUV" for c in id32_part.upper()):
            continue
        entry_id = decode_id32_to_int(id32_part)
        wrong_name = compute_id64_no_strip(entry_id) + ".ift_tk"
        shutil.move(old_path, os.path.join(dest_dir, wrong_name))

    nft.writeTestIFTFile()


testTag = "conform-entry-id-converted"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="URL template id64 must strip leading zero bytes from integer entry IDs",
    description="The URL template uses the id64 opcode (0x85). Patch files are stored "
                "at the un-stripped 4-byte base64url names (e.g. 'AAAAAQ==.ift_tk' for "
                "entry 1). A conforming client strips leading zero bytes and looks for "
                "'AQ==.ift_tk' (URL-encoded as 'AQ%3D%3D.ift_tk'), which does not exist, "
                "so the IFT font cannot be loaded.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithUnstrippedId64PatchNames,
    funcArgs=(identifierString,)
)


def makeIFTWithFormat1MismatchedGlyphCount(fontFormat, testName):
    """
    Replace the Format 2 IFT table with a hand-built Format 1 patch map whose
    glyphCount field does not match the number of glyphs in the font (maxp.numGlyphs).

    Tests conform-format1-glyph-count-matches: 'Number of glyphs that mappings are
    provided for. Must match the number of glyphs in the the font file.'

    The constructed Format 1 table is otherwise well-formed: maxEntryIndex and
    maxGlyphMapEntryIndex are both 0, the Glyph Map has firstMappedGlyph equal to
    glyphCount so the entryIndex array is empty (all font glyphs are implicitly
    mapped to entry 0), and a valid URL template and patchFormat are provided.
    The only defect is the glyphCount value, so a conforming client must detect
    the mismatch in step 1 of Interpret Format 1 Patch Map and reject the font.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    raw = nft.getIFTTableData()

    # Preserve the original compatibilityId so the only defect is glyphCount.
    # Format 2 layout: compatibilityId is bytes 5..21.
    compatibility_id = bytes(raw[5:21])

    num_glyphs = nft.font["maxp"].numGlyphs
    bad_glyph_count = num_glyphs + 90  # any value != num_glyphs

    # Format 1 Patch Map fixed header (see spec §patch-map-format-1)
    header = bytearray()
    header.append(1)                                  # format = 1
    header.extend(b"\x00\x00\x00")                    # reserved (uint24)
    header.append(0)                                  # flags
    header.extend(compatibility_id)                   # compatibilityId[16]
    header.extend(struct.pack(">H", 0))               # maxEntryIndex
    header.extend(struct.pack(">H", 0))               # maxGlyphMapEntryIndex
    header.extend(bad_glyph_count.to_bytes(3, "big")) # glyphCount (uint24) — INVALID

    # Offsets are placeholders; filled in after the variable-length fields are sized.
    glyph_map_offset_pos = len(header)
    header.extend(struct.pack(">I", 0))               # glyphMapOffset (uint32)
    header.extend(struct.pack(">I", 0))               # featureMapOffset = 0 (null)

    # appliedEntriesBitMap[(maxEntryIndex + 8) / 8] = appliedEntriesBitMap[1]
    header.append(0)

    # URL template: id32 insertion opcode (0x80), then literal ".ift_tk" (length 7).
    # Matches the patch file naming used elsewhere in this test suite (e.g. "04.ift_tk").
    url_template = bytes([0x80, 7]) + b".ift_tk"
    header.extend(struct.pack(">H", len(url_template)))  # urlTemplateLength
    header.extend(url_template)                          # urlTemplate

    header.append(1)                                  # patchFormat = 1 (table keyed, full invalidation)

    # Glyph Map sub-table. firstMappedGlyph = bad_glyph_count makes
    # entryIndex[glyphCount - firstMappedGlyph] zero-length.
    glyph_map = struct.pack(">H", bad_glyph_count)

    # Fill in glyphMapOffset
    struct.pack_into(">I", header, glyph_map_offset_pos, len(header))

    new_ift = bytes(header) + glyph_map
    nft.setIFTTableData(new_ift)
    nft.writeTestIFTFile()


testTag = "conform-format1-glyph-count-matches"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Format 1 patch map with glyphCount that does not match the font",
    description="The IFT table uses Format 1 with a glyphCount field set to a value "
                "that does not match the number of glyphs in the font (maxp.numGlyphs). "
                "A conforming client must detect the mismatch during Interpret Format 1 "
                "Patch Map and reject the font.",
    shouldShowIFT=False,
    credits=[dict(title="Takeru Suzuki", role="author", link="https://github.com/terkel")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithFormat1MismatchedGlyphCount,
    funcArgs=(identifierString,)
)


def makeIFTWithFormat1InvalidPatchFormat(fontFormat, testName):
    """
    Replace the Format 2 IFT table with a hand-built Format 1 patch map whose
    patchFormat field is set to 0, which is not one of the values from §6.1
    Formats Summary (valid values are 1, 2, 3).

    Tests conform-format1-valid-format-number: 'Must be set to one of the format
    numbers from the §6.1 Formats Summary table.'

    The constructed Format 1 table is otherwise well-formed (correct glyphCount,
    null featureMap, empty entryIndex array since all font glyphs map to entry 0
    implicitly); the only defect is the invalid patchFormat value, so a conforming
    client must reject the font.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    raw = nft.getIFTTableData()

    compatibility_id = bytes(raw[5:21])

    num_glyphs = nft.font["maxp"].numGlyphs

    header = bytearray()
    header.append(1)                                  # format = 1
    header.extend(b"\x00\x00\x00")                    # reserved (uint24)
    header.append(0)                                  # flags
    header.extend(compatibility_id)                   # compatibilityId[16]
    header.extend(struct.pack(">H", 0))               # maxEntryIndex
    header.extend(struct.pack(">H", 0))               # maxGlyphMapEntryIndex
    header.extend(num_glyphs.to_bytes(3, "big"))      # glyphCount (uint24)

    glyph_map_offset_pos = len(header)
    header.extend(struct.pack(">I", 0))               # glyphMapOffset (uint32)
    header.extend(struct.pack(">I", 0))               # featureMapOffset = 0 (null)

    header.append(0)                                  # appliedEntriesBitMap[1]

    url_template = bytes([0x80, 7]) + b".ift_tk"
    header.extend(struct.pack(">H", len(url_template)))
    header.extend(url_template)

    header.append(0)                                  # patchFormat = 0 — INVALID

    # firstMappedGlyph = glyphCount makes entryIndex[] zero-length, so every
    # glyph is implicitly mapped to entry 0.
    glyph_map = struct.pack(">H", num_glyphs)

    struct.pack_into(">I", header, glyph_map_offset_pos, len(header))

    new_ift = bytes(header) + glyph_map
    nft.setIFTTableData(new_ift)
    nft.writeTestIFTFile()


testTag = "conform-format1-valid-format-number"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Format 1 patch map with invalid patchFormat value",
    description="The IFT table uses Format 1 with a patchFormat field set to 0, "
                "which is not one of the format numbers listed in the §6.1 Formats "
                "Summary table (valid values are 1, 2, and 3). A conforming client "
                "must reject the font.",
    shouldShowIFT=False,
    credits=[dict(title="Takeru Suzuki", role="author", link="https://github.com/terkel")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithFormat1InvalidPatchFormat,
    funcArgs=(identifierString,)
)

def makeIFTForDocumentIsolationTest(fontFormat, testName):
    """
    Build a test from a valid, unmodified glyph-keyed patch -- identical to
    makeIFTWithValidGlyphKeyedPatch's positive control -- so the standard
    per-format harness (resources/ift.js) reconstructs a genuine IFT font
    from real patches in *this* (parent) document, exactly like every other
    test in the suite. This is the "specific IFT loaded in the parent
    window" that conform-web-font-not-accessible-from-different-document
    then checks does not leak into a sibling iframe.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.writeTestIFTFile()


def _makeDifferentDocumentIframe(identifierString, fontFormat):
    """
    Builds the extra markup for conform-web-font-not-accessible-from-different-document.

    Per https://www.w3.org/TR/IFT/#per-origin (quoting CSS Fonts 4):
    "A Web Font must not be accessible in any other Document from the one
    which either is associated with the @font-face rule or owns the
    FontFaceSet."

    Unlike the first version of this test (see PR review on #27), nothing
    custom is fetched/loaded here. `func` above builds an ordinary, valid,
    unmodified patch, so the *standard* per-format harness in
    resources/ift.js reconstructs a real IFT font from real patches and adds
    it to this (parent) document's FontFaceSet, under the same name it
    always uses: "<fontFormat>-<identifier>-IFT-Font". That row's own
    "Should Render IFT: P (<fontFormat>)" indicator is left in place as a
    sanity check that the setup genuinely works in the parent.

    This markup adds a sibling iframe (a distinct Document). The iframe
    never loads resources/ift.js and never receives this FontFace itself,
    so its own indicator span, styled with that *exact same* family name
    plus the suite's usual "RobotoFallback" fallback, should only ever be
    able to render via the fallback if isolation is correctly enforced.

    The critical fix from the first version: the reconstructed IFT font
    uses the "ift" mode ligature (F -> FAIL), while the site-wide
    RobotoFallback fallback uses the inverted "fallback" mode ligature
    (F -> PASS) -- see makeSubsettedFont.py. Those are deliberately
    different fonts, so the two outcomes are visually distinguishable:
      - Isolated (conforming): the family name resolves to nothing in the
        iframe's own (empty) FontFaceSet -> falls back to RobotoFallback ->
        renders PASS.
      - Leaked (non-conforming): the family name resolves to the parent's
        reconstructed font inside the iframe too -> renders FAIL.
    The first version of this test used the *same* fallback file as both
    the "loaded" font and the iframe's own fallback, so isolated and leaked
    were visually identical (both PASS) and the test could never actually
    fail regardless of browser behavior.

    The iframe's font-family is baked directly into its `srcdoc` HTML
    (rather than being set later via script once the iframe "loads") so
    there's no dependency on iframe load timing: `frame.contentDocument`
    initially points at a blank placeholder document before the srcdoc
    navigation completes, and checking its readyState can spuriously read as
    "complete" for that placeholder (which has no #result element at all),
    while the real "load" event for the actual content may already have
    fired before a listener gets attached -- either way, the intended style
    never reaches the real element. Setting it inline from the start avoids
    that race entirely.
    """
    family = "%s-%s-IFT-Font" % (fontFormat, identifierString)
    frameId = "diffdoc-frame-%s" % identifierString
    frameSrcdoc = (
        "&lt;!DOCTYPE html&gt;&lt;html&gt;&lt;head&gt;&lt;style&gt;"
        "@font-face{font-family:'RobotoFallback';src:url(resources/fallback/Roboto.ttf) format('truetype');}"
        "html,body{height:100%%;margin:0;}"
        "body{display:flex;align-items:center;justify-content:center;}"
        "&lt;/style&gt;&lt;/head&gt;"
        "&lt;body&gt;"
        "&lt;span id=&quot;result&quot; class=&quot;result&quot; "
        "style=&quot;font-family:%s, RobotoFallback; font-size:15px&quot;&gt;F&lt;/span&gt;"
        "&lt;/body&gt;&lt;/html&gt;"
    ) % family
    return """
					<p>Should Not Render IFT in the iframe (the font above is only added to the parent document's FontFaceSet):
					<iframe id="%(frameId)s" style="width:40px;height:44px;border:0;vertical-align:middle;"
							srcdoc="%(frameSrcdoc)s"></iframe></p>
""".strip("\n") % dict(
        frameId=frameId,
        frameSrcdoc=frameSrcdoc,
    )


testTag = "conform-web-font-not-accessible-from-different-document"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF"]
writeTest(
    identifier=identifierString,
    title="Web font must not be accessible from a different Document",
    description="Per CSS Fonts 4, a Web Font (including one loaded incrementally via "
                "the FontFace API and added to document.fonts, as an IFT client does "
                "when it reconstructs a font from patches) must not be accessible in "
                "any Document other than the one whose FontFaceSet it was added to. "
                "This test extends a genuine IFT font from real patches in the "
                "top-level document -- the same mechanism every other test in this "
                "suite uses, and the same 'Should Render IFT: P' row confirms it -- "
                "then checks a second 'Should Render IFT' indicator inside a sibling "
                "iframe (a distinct Document) that never receives the font, so it "
                "must read 'F' (falling back, rather than resolving the family name "
                "to the parent's font).",
    shouldShowIFT=True,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTForDocumentIsolationTest,
    funcArgs=(identifierString,),
    extraHTML=_makeDifferentDocumentIframe(identifierString, fontFormats[0]),
)



# --------------------------------------------------------------------------
# apply-glyph-keyed algorithm tests (spec §6.3.1 Applying Glyph Keyed Patches)
#
# These four sub-tests cover the important pieces of the Apply glyph keyed
# patch algorithm (see issue #8):
#   - Step 2: reject a patch whose compatibilityId does not match.
#   - Step 3: reject a patch whose decoded size exceeds maxUncompressedLength.
#   - Step 4: reject a patch that references a base table that is missing.
#   - Step 4: correctly insert glyf/loca or CFF glyph data (positive control).
#
# All four share the "apply-glyph-keyed" algorithm conformance id (the id is an
# algorithm statement in the spec), differentiated by an "_<name>" suffix so
# check_coverage.py counts them as separate tests of the same algorithm.
#
# Glyph keyed patch header layout (used by the modifying tests):
#   0-3:   format (Tag) = 'ifgk'
#   4-7:   reserved (uint32)
#   8:     flags (uint8)          -- bit 0: glyphIds use uint24 (else uint16)
#   9-24:  compatibilityId (uint32[4], 16 bytes)
#   25-28: maxUncompressedLength (uint32)
#   29+:   brotliStream (compressed GlyphPatches table)
# --------------------------------------------------------------------------

def makeIFTWithMismatchedGlyphKeyedCompatId(fontFormat, testName):
    """
    Corrupt the compatibilityId field in each glyph-keyed patch so it no longer
    matches the compatibility id from the base font's 'IFT '/'IFTX' table.

    Tests apply-glyph-keyed step 2: 'Check that the compatibilityId field in
    patch is equal to compatibility id. If there is no match ... patch
    application has failed, return an error.'

    A conforming client detects the mismatch and rejects the patch, so the IFT
    font fails to render and the fallback font shows PASS.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.getIFTTableData()

    destDir = os.path.join(nft.testDirectory, fontFormat)
    for gkFile in glob.glob(os.path.join(destDir, "*_gk")):
        with open(gkFile, "rb") as f:
            data = bytearray(f.read())
        # Flip the first byte of the 16-byte compatibilityId (bytes 9-24) so it
        # is guaranteed to differ from the compatibility id declared in the base
        # font's IFT table. This is the only defect introduced.
        data[9] ^= 0xFF
        with open(gkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()


testTag = "apply-glyph-keyed_reject-mismatched-compatibility-id"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch with mismatched compatibility id",
    description="The compatibilityId field of each glyph-keyed patch is altered so "
                "it no longer matches the compatibility id in the base font's IFT "
                "table. A conforming client must reject the patch (Apply glyph keyed "
                "patch, step 2), so the IFT font fails to render.",
    shouldShowIFT=False,
    credits=[dict(title="Takeru Suzuki", role="author", link="https://github.com/terkel")],
    specLink="#apply-glyph-keyed",
    fontFormats=fontFormats,
    func=makeIFTWithMismatchedGlyphKeyedCompatId,
    funcArgs=(identifierString,)
)


def makeIFTWithGlyphKeyedDecodedSizeExceedingMax(fontFormat, testName):
    """
    Set maxUncompressedLength in each glyph-keyed patch to one less than the
    actual decoded size of its brotli stream.

    Tests apply-glyph-keyed step 3: 'Decode the brotli encoded data in
    brotliStream ... If the decoded data is larger than maxUncompressedLength
    return an error.'

    Only the maxUncompressedLength header field is changed; the brotliStream is
    left untouched, so the decoded GlyphPatches table is exactly one byte larger
    than the declared maximum. A conforming client detects this and rejects the
    patch, so the IFT font fails to render and the fallback font shows PASS.
    """
    import brotli
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.getIFTTableData()

    destDir = os.path.join(nft.testDirectory, fontFormat)
    for gkFile in glob.glob(os.path.join(destDir, "*_gk")):
        with open(gkFile, "rb") as f:
            data = bytearray(f.read())
        decoded_length = len(brotli.decompress(bytes(data[29:])))
        # Declare a maximum uncompressed length smaller than the true decoded
        # size so decoding must exceed it. maxUncompressedLength is bytes 25-28.
        struct.pack_into(">I", data, 25, decoded_length - 1)
        with open(gkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()


testTag = "apply-glyph-keyed_reject-decoded-size-exceeds-max"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch decoded size exceeds maxUncompressedLength",
    description="The maxUncompressedLength field of each glyph-keyed patch is set to "
                "one less than the actual decoded size of its brotli stream. A "
                "conforming client must reject the patch when the decoded data is "
                "larger than maxUncompressedLength (Apply glyph keyed patch, step 3), "
                "so the IFT font fails to render.",
    shouldShowIFT=False,
    credits=[dict(title="Takeru Suzuki", role="author", link="https://github.com/terkel")],
    specLink="#apply-glyph-keyed",
    fontFormats=fontFormats,
    func=makeIFTWithGlyphKeyedDecodedSizeExceedingMax,
    funcArgs=(identifierString,)
)


def makeIFTWithMissingTableInGlyphPatch(fontFormat, testName):
    """
    Add a supported-type table entry ('gvar') that is absent from the base font
    to each glyph-keyed patch, with zero-length glyph data for every glyph.

    Tests apply-glyph-keyed step 4: 'If base font subset does not have a matching
    table, return an error.' Unlike unsupported table types (which must be
    ignored, see conform-table-entries-ignore-others), 'gvar' is one of the
    supported table types (glyf, gvar, CFF, CFF2), so a conforming client must
    process the entry, find that the base font has no 'gvar' table, and reject
    the patch. The IFT font then fails to render and the fallback font shows PASS.

    'gvar' sorts after both 'glyf' and 'CFF ', so appending it keeps the tables
    array in ascending order (conform-glyph-keyed-tables-sort-ascending-unique),
    making the missing base table the only defect.

    GlyphPatches layout (decompressed):
      0-3:   glyphCount (uint32)
      4:     tableCount (uint8)
      5+:    glyphIds[glyphCount]  (uint16 or uint24 per flags bit 0)
      then:  tables[tableCount]    (Tag, 4 bytes each)
      then:  glyphDataOffsets[glyphCount * tableCount + 1] (Offset32 each)
      then:  glyphData[variable]
    """
    import brotli
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.getIFTTableData()

    destDir = os.path.join(nft.testDirectory, fontFormat)
    for gkFile in glob.glob(os.path.join(destDir, "*_gk")):
        with open(gkFile, "rb") as f:
            data = bytearray(f.read())

        flags = data[8]
        gid_size = 3 if (flags & 1) else 2
        decompressed = bytearray(brotli.decompress(bytes(data[29:])))

        glyph_count = struct.unpack(">I", decompressed[0:4])[0]
        table_count = decompressed[4]

        tables_offset = 5 + glyph_count * gid_size
        glyph_data_offsets_offset = tables_offset + table_count * 4
        num_offsets = glyph_count * table_count + 1
        glyph_data_start = glyph_data_offsets_offset + num_offsets * 4

        # Appending 1 table tag (4 bytes) and glyph_count new offset entries
        # (glyph_count * 4 bytes) shifts glyphData forward; every existing
        # (absolute) offset must be adjusted by this delta.
        offset_delta = 4 + glyph_count * 4
        existing_offsets = [
            struct.unpack(">I", decompressed[
                glyph_data_offsets_offset + i * 4:
                glyph_data_offsets_offset + i * 4 + 4
            ])[0] + offset_delta
            for i in range(num_offsets)
        ]
        new_sentinel = existing_offsets[-1]

        new_decompressed = bytearray()
        # glyphCount (unchanged)
        new_decompressed.extend(struct.pack(">I", glyph_count))
        # tableCount + 1
        new_decompressed.append(table_count + 1)
        # glyphIds (unchanged)
        new_decompressed.extend(decompressed[5:tables_offset])
        # existing table tags (unchanged)
        new_decompressed.extend(decompressed[tables_offset:glyph_data_offsets_offset])
        # new supported-but-missing table tag, appended in ascending order
        new_decompressed.extend(b'gvar')
        # adjusted existing offsets minus the sentinel
        for off in existing_offsets[:-1]:
            new_decompressed.extend(struct.pack(">I", off))
        # glyph_count new offsets for 'gvar', all equal to new_sentinel (zero-length data)
        for _ in range(glyph_count):
            new_decompressed.extend(struct.pack(">I", new_sentinel))
        # new sentinel
        new_decompressed.extend(struct.pack(">I", new_sentinel))
        # glyph data (unchanged)
        new_decompressed.extend(decompressed[glyph_data_start:])

        recompressed = brotli.compress(bytes(new_decompressed))
        struct.pack_into(">I", data, 25, len(new_decompressed))
        data[29:] = recompressed

        with open(gkFile, "wb") as f:
            f.write(data)

    nft.writeTestIFTFile()


testTag = "apply-glyph-keyed_reject-missing-table"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch references a table missing from the base font",
    description="Each glyph-keyed patch is given an additional entry for the supported "
                "table 'gvar', which is not present in the base font. A conforming client "
                "must reject the patch because the base font has no matching table (Apply "
                "glyph keyed patch, step 4), so the IFT font fails to render.",
    shouldShowIFT=False,
    credits=[dict(title="Takeru Suzuki", role="author", link="https://github.com/terkel")],
    specLink="#apply-glyph-keyed",
    fontFormats=fontFormats,
    func=makeIFTWithMissingTableInGlyphPatch,
    funcArgs=(identifierString,)
)


def makeIFTWithValidGlyphKeyedPatch(fontFormat, testName):
    """
    Build a test from a valid, unmodified glyph-keyed patch as a positive control
    for the apply-glyph-keyed algorithm.

    Tests apply-glyph-keyed step 4 (glyph data insertion): a conforming client
    must apply the valid glyph-keyed patch, synthesizing the glyf/loca (GLYF) or
    CFF (CFF) table with the patched per-glyph data inserted. The base subset has
    empty outlines for the patched glyphs, so the ligatures that render 'PASS'
    only appear when the client correctly inserts the glyph data from the patch.

    shouldShowIFT=True: correct insertion renders 'PASS' via the IFT font; a
    client that fails to apply the glyph-keyed patch leaves the glyphs empty and
    shows FAIL.
    """
    nft = IFTFile(testName, fontFormat, IFT_FONT_FILENAME)
    nft.writeTestIFTFile()


testTag = "apply-glyph-keyed_insert-glyph-data"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Glyph keyed patch glyph data is inserted correctly",
    description="A valid, unmodified glyph-keyed patch is applied. The base subset has "
                "empty outlines for the patched glyphs, so the IFT font renders 'PASS' "
                "only if the client correctly inserts the glyf/loca (GLYF) or CFF (CFF) "
                "glyph data from the patch (Apply glyph keyed patch, step 4).",
    shouldShowIFT=True,
    credits=[dict(title="Takeru Suzuki", role="author", link="https://github.com/terkel")],
    specLink="#apply-glyph-keyed",
    fontFormats=fontFormats,
    func=makeIFTWithValidGlyphKeyedPatch,
    funcArgs=(identifierString,)
)


# --------------------------------------------------------------------------
# conform-stop-extend-after-errors (issue #22)
#
# "In the case of all other errors the client must not attempt to further
# extend the font subset."
#
# Every other test in this suite only ever needs a single glyph-keyed patch
# to satisfy its target text (the base -ift subset already contains
# everything except the PASS/FAIL letters, all of which live in one patch),
# so there's never a second patch left over to *not* apply. This test uses
# a separate font build (build/STOP_EXTEND, see
# generators/makeStopExtendDecoyFont.py and the Makefile) that adds one
# extra, independent glyph/codepoint (U+E000) with its own dedicated
# glyph-keyed patch alongside the usual PASS/FAIL patch.
#
# The decoy codepoint is placed off-screen in the test's HTML (absolute
# positioning, not display:none/visibility:hidden -- innerText omits text
# from elements that aren't rendered at all) so it's picked up by
# resources/ift.js's codepoint computation and requested for extension
# along with the visible PASS/FAIL text, without ever being seen.
#
# Only the decoy's patch file is corrupted (bad format tag -> a non-load
# error, same defect as conform-glyph-keyed-format-equals-ifgk). The
# PASS/FAIL patch is left completely valid. A conforming client must not
# apply that valid patch once the decoy patch has failed with this error,
# so the IFT font never renders and the fallback (FAIL) shows. A client
# that incorrectly keeps extending after the error would still apply the
# valid patch and incorrectly show PASS.
# --------------------------------------------------------------------------

DECOY_CODEPOINT = 0xE000


def makeIFTWithDecoyPatchNonLoadError(fontFormat, testName):
    """
    Use the STOP_EXTEND build (base PASS/FAIL font plus one extra,
    independent glyph-keyed patch for the decoy codepoint) and corrupt every
    decoy patch file, identified by having the fewest glyphs of any _gk
    patch in this build (it should contain exactly the one decoy glyph,
    versus several for the PASS/FAIL group).

    Each patch "slot" in the segmentation plan is compiled into more than
    one physical _gk file (e.g. "04.1"/"04.2") -- alternate versions of the
    same patch for different possible client states (jump_ahead/prefetch).
    Corrupting only one of them left a valid fallback copy in place, so the
    client could satisfy the decoy requirement from the untouched copy and
    the test never actually exercised the error path. All physical files
    for the decoy slot must be corrupted, while every PASS/FAIL file is left
    completely valid.
    """
    import brotli

    destDir = os.path.join(clientTestDirectory, testName, fontFormat)
    if not os.path.exists(destDir):
        shutil.copytree(
            os.path.join(buildDirectory, "STOP_EXTEND", "IFT", fontFormat),
            destDir,
        )

    builtFontPath = os.path.join(destDir, "font.ift.woff2")
    if os.path.exists(builtFontPath):
        os.rename(builtFontPath, os.path.join(destDir, IFT_FONT_FILENAME))

    gkFiles = glob.glob(os.path.join(destDir, "*_gk"))
    counts = {}
    for gkFile in gkFiles:
        with open(gkFile, "rb") as f:
            data = f.read()
        decompressed = brotli.decompress(bytes(data[29:]))
        glyphCount = struct.unpack(">I", decompressed[0:4])[0]
        counts[gkFile] = glyphCount

    if not counts:
        raise ValueError(
            "No _gk patch files found in %s -- has the STOP_EXTEND build "
            "been generated (see Makefile)?" % destDir
        )

    # Every physical file for the decoy slot has the fewest glyphs (1); the
    # PASS/FAIL slot's files group several letters together. Corrupt all of
    # the former, none of the latter.
    minCount = min(counts.values())
    assert minCount == 1, (
        "Expected the decoy patch to contain exactly 1 glyph, but the "
        "smallest _gk patch in %s has %d. If a future encoder/segmentation "
        "change merged the decoy glyph into the PASS/FAIL patch (or grouped "
        "it some other way), this test would silently become a no-op -- fix "
        "the font/plan generation (see makeStopExtendDecoyFont.py) rather "
        "than loosening this assertion." % (destDir, minCount)
    )
    decoyFiles = [gkFile for gkFile, count in counts.items() if count == minCount]

    for decoyFile in decoyFiles:
        with open(decoyFile, "rb") as f:
            data = bytearray(f.read())
        data[0:4] = b"XXXX"
        with open(decoyFile, "wb") as f:
            f.write(data)

    # At least one _gk patch (the PASS/FAIL group) must remain valid and
    # untouched. Without this, there's nothing left to distinguish "the
    # client stopped extending after an error" from "nothing was ever going
    # to render regardless" -- the test would still show FAIL, but for the
    # wrong reason.
    validFiles = [gkFile for gkFile in gkFiles if gkFile not in decoyFiles]
    assert validFiles, (
        "No valid (uncorrupted) _gk patch file remains in %s after "
        "corrupting the decoy patch(es) -- this test needs a still-valid "
        "PASS/FAIL patch to prove the client refuses to apply it." % destDir
    )
    for validFile in validFiles:
        with open(validFile, "rb") as f:
            tag = f.read(4)
        assert tag == b"ifgk", (
            "%s was expected to remain a valid, untouched glyph-keyed patch "
            "(tag 'ifgk') but has tag %r." % (validFile, tag)
        )


def _makeDecoyCodepointSpan():
    """
    An off-screen (not display:none/visibility:hidden, since those are
    excluded from element.innerText) span containing the decoy codepoint, so
    it's requested for extension alongside the visible PASS/FAIL text but
    never actually seen.
    """
    return (
        "\t\t\t\t\t<p style=\"position:absolute;left:-9999px;\" aria-hidden=\"true\">"
        "&#x%X;</p>"
    ) % DECOY_CODEPOINT


testTag = "conform-stop-extend-after-errors"
identifierString = "%s-%s" % (testType, testTag)
fontFormats = ["GLYF", "CFF"]
writeTest(
    identifier=identifierString,
    title="Client must not continue extending after a non-load error",
    description="The font requires two independent glyph-keyed patches to satisfy the "
                "requested text: one for the visible PASS/FAIL letters, and one for an "
                "off-screen decoy codepoint. Only the decoy's patch is corrupted (invalid "
                "format tag), while the PASS/FAIL patch is left completely valid. A "
                "conforming client must not attempt to further extend the font subset once "
                "the decoy patch fails with this error, so the IFT font must not render "
                "even though the PASS/FAIL patch itself was valid.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#%s" % identifierString,
    fontFormats=fontFormats,
    func=makeIFTWithDecoyPatchNonLoadError,
    funcArgs=(identifierString,),
    extraHTML=_makeDecoyCodepointSpan(),
)


# ------------------
# Generate the Index
# ------------------

print("Compiling index...")

testGroups = []

for tag, title, url, note in groupDefinitions:
    group = dict(title=title, url=url, testCases=testRegistry[tag], note=note)
    testGroups.append(group)

generateClientIndexHTML(directory=clientTestDirectory, testCases=testGroups, note=indexNote)

destPath = os.path.join(clientTestDirectory, "index.html")
if os.path.exists(destPath):
    os.remove(destPath)
shutil.copy(os.path.join(clientTestDirectory, "testcaseindex.xht"), destPath)

# ----------------
# Generate the zip
# ----------------

print("Compiling zip file...")

zipPath = os.path.join(clientTestDirectory, "ClientTestFonts.zip")
if os.path.exists(zipPath):
    os.remove(zipPath)

allBinariesZip = zipfile.ZipFile(zipPath, "w")

# Add directories that start with 'conform-'
conformPattern = os.path.join(clientTestDirectory, "conform-*")
for dirPath in glob.glob(conformPattern):
    if os.path.isdir(dirPath):
        dirName = os.path.basename(dirPath)
        for root, dirs, files in os.walk(dirPath):
            for file in files:
                filePath = os.path.join(root, file)
                archive_path = os.path.join(dirName, os.path.relpath(filePath, dirPath))
                allBinariesZip.write(filePath, archive_path)

allBinariesZip.close()

# ---------------------
# Generate the Manifest
# ---------------------

print("Compiling manifest...")

manifest = []

for tag, title, url, note in groupDefinitions:
    for testCase in testRegistry[tag]:
        identifier = testCase["identifier"]
        title = testCase["title"]
        assertion = testCase["description"]
        links = "#" + testCase["specLink"].split("#")[-1]
        # XXX force the chapter onto the links
        links = "#TableDirectory," + links
        flags = ""
        credits = ""
        # format the line
        line = "%s\t%s\t%s\t%s\t%s\t%s" % (
            identifier,             # id
            "",                     # reference
            title,                  # title
            flags,                  # flags
            links,                  # links
            assertion               # assertion
        )
        # store
        manifest.append(line)

path = os.path.join(clientDirectory, "manifest.txt")
if os.path.exists(path):
    os.remove(path)
f = open(path, "w")
f.write("\n".join(manifest))
f.close()
