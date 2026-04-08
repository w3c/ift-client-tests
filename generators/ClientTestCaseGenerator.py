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
import base64
import shutil
import struct
import zipfile
from fontTools.ttLib import TTFont
from testCaseGeneratorLib.paths import resourcesDirectory, clientDirectory, clientTestDirectory,\
                          clientTestResourcesDirectory, fallbackFontPath
from testCaseGeneratorLib.html import generateClientIndexHTML, expandSpecLinks
from testCaseGeneratorLib.iftFile import IFTFile
from testCaseGeneratorLib.helpers import decode_id32_to_int, id32_no_strip


# IFT Table Header Offsets
IFT_ENTRIES_OFFSET_START = 25
IFT_ENTRIES_OFFSET_END = 29
IFT_FORMAT_OFFSET = 0
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

def writeTest(identifier, title, description, fontFormats, func, funcArgs=None, specLink=None, credits=[], shouldShowIFT=False):
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
    nft.getIFTTableData()  # load but do not modify the IFT table

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
