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
from testCaseGeneratorLib.paths import resourcesDirectory, clientDirectory, clientTestDirectory,\
                          clientTestResourcesDirectory, IFTSourcePath, fallbackFontPath
from testCaseGeneratorLib.html import generateClientIndexHTML, expandSpecLinks

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

def writeTest(identifier, title, description, func, specLink=None, credits=[], shouldShowIFT=False):
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
    func()
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
            specLink=specLink
        )
    )

class NFTFile:
    def __init__(self, testName,sourceFontPath):
        self.testName = testName 
        self.testDirectory = os.path.join(clientTestDirectory, testName)
        self.sourceFontPath = sourceFontPath
        self.createTestDirectory()
        self.copyIFTSourceFiles()
    def createTestDirectory(self):
        if not os.path.exists(self.testDirectory):
            os.makedirs(self.testDirectory)
    def copyIFTSourceFiles(self):
        # Copy _gk and _tk files from resources/IFT/ to testDirectory
        sourceDir = os.path.join(resourcesDirectory, "IFT")
        for pattern in ("*_gk", "*_tk"):
            for filePath in glob.glob(os.path.join(sourceDir, pattern)):
                shutil.copy(filePath, self.testDirectory)
                print(f"Copied {filePath} to {self.testDirectory}")
    def getIFTTableData(self):
        self.font = TTFont(self.sourceFontPath)
        if "IFT " not in self.font:
            raise ValueError("IFT table not found in font.")
        # Unknown/custom tables are stored as raw bytes on .data
        self.tbl = self.font["IFT "]
        self.raw = bytearray(self.tbl.data)
        return self.raw
    def setIFTTableData(self, data):
        self.raw = bytearray(data)
    def removeIFTTable(self):
        del self.font["IFT "]
    def writeTestIFTFile(self):
        if self.tbl and self.raw:
            self.tbl.data = bytes(self.raw)
        outPath = os.path.join(self.testDirectory, IFT_FONT_FILENAME)
        self.font.save(outPath)
    

# start of tests
def makeIFTWithFormatID(formatId, testName):
    nft = NFTFile(testName,IFTSourcePath)
    raw = nft.getIFTTableData()
    raw[IFT_FORMAT_OFFSET] = formatId
    nft.setIFTTableData(bytes(raw))
    nft.writeTestIFTFile()

testType = "client"

testTag = "conform-format2-valid-format-number"
identifierString= "%s-%s" % (testType, testTag)
writeTest(
    identifier=identifierString,
    title="Format 2 with invalid format number",
    description="The IFT table 'format' field for a format 2 is set to 3, which is an invalid format number.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink= "#%s" % identifierString,
    func=lambda: makeIFTWithFormatID(3, identifierString) 
)

def makeIFTWithInvalidDesignSpaceSegmentEndValue(testName): 
    # This test is only for format 2. For reference: https://www.w3.org/TR/IFT/#patch-map-format-2
    nft = NFTFile(testName,IFTSourcePath)
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

testTag = "conform-design-space-segment-end-invalid-value"
identifierString= "%s-%s" % (testType, testTag)
writeTest(
    identifier=identifierString,
    title="Format 2 with invalid design space segment end value",
    description="The IFT table design space segment end value is set to an invalid negative number.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink= "#%s" % identifierString,
    func=lambda: makeIFTWithInvalidDesignSpaceSegmentEndValue(identifierString) 
)

def removeIFTTable(testName):
    nft = NFTFile(testName,IFTSourcePath)
    raw = nft.getIFTTableData()
    nft.removeIFTTable()
    nft.writeTestIFTFile()

testTag = "conform-require-ift-table"
identifierString= "%s-%s" % (testType, testTag)
writeTest(
    identifier=identifierString,
    title="IFT table missing",
    description="All incremental fonts must contain the 'IFT ' table.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink= "#%s" % identifierString,
    func=lambda: removeIFTTable(identifierString) 
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
