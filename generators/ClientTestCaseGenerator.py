"""
This script generates the authoring tool test cases. It will create a directory
one level up from the directory containing this script called "AuthoringTool".
That directory will have the structure:

    /Format
        README.txt - information about how the tests were generated and how they should be modified
        /Tests
            testcaseindex.xht - index of all test cases
            test-case-name-number.otf/ttf - individual SFNT test case
            /resources
                index.css - index CSS file

Within this script, each test case is generated with a call to the
writeTest function. In this, SFNT data must be passed along with
details about the data. This function will generate the SFNT
and register the case in the suite index.
"""

import os
import shutil
import glob
import zipfile
from fontTools.ttLib import TTFont
from testCaseGeneratorLib.paths import resourcesDirectory, clientDirectory, clientTestDirectory,\
                          clientTestResourcesDirectory, IFTTestDirectory, IFTSourcePath
from testCaseGeneratorLib.html import generateClientIndexHTML, expandSpecLinks

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

# brotli JS
destPath = os.path.join(clientTestResourcesDirectory, "brotli.js")
if os.path.exists(destPath):
    os.remove(destPath)
shutil.copy(os.path.join(resourcesDirectory, "cc-client","brotli.js"), destPath)

# ---------------
# Test Case Index
# ---------------

# As the tests are generated a log will be kept.
# This log will be translated into an index after
# all of the tests have been written.

indexNote = """
The tests in this suite represent SFNT data to be used for WOFF
conversion without any alteration or correction. An authoring tool
may allow the explicit or silent modification and/or correction of
SFNT data. In such a case, the tests in this suite that are labeled
as "should not convert" may be converted, so long as the problems
in the files have been corrected. In that case, there is no longer
any access to the "input font" as defined in the WOFF specification,
so the bitwise identical tests should be skipped.
""".strip()

tableDataNote = """
These files are valid SFNTs that excercise conversion of the table data.
""".strip()

tableDirectoryNote = """
These files are valid SFNTs that excercise conversion of the table directory.
""".strip()

collectionNote = """
These files are valid SFNTs that excercise conversion of font collections.
""".strip()

groupDefinitions = [
    # identifier, title, spec section, category note
    ("tabledirectory", "SFNT Table Directory Tests", expandSpecLinks("#DataTables"), tableDirectoryNote),
    ("tabledata", "SFNT Table Data Tests", expandSpecLinks("#DataTables"), tableDataNote),
    ("collection", "SFNT Collection Tests", expandSpecLinks("#DataTables"), collectionNote),
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

def writeTest(identifier, title, description, func, specLink=None, credits=[], shouldConvert=False, flavor="CFF"):
    """
    This function generates all of the files needed by a test case and
    registers the case with the suite. The arguments:

    identifier: The identifier for the test case. The identifier must be
    a - separated sequence of group name (from the groupDefinitions
    listed above), test case description (arbitrary length) and a number
    to make the name unique. The number should be zero padded to a length
    of three characters (ie "001" instead of "1").

    title: A thorough, but not too long, title for the test case.

    description: A detailed statement about what the test case is proving.

    data: The complete binary data for the SFNT.

    specLink: The anchor in the WOFF spec that the test case is testing.

    credits: A list of dictionaries defining the credits for the test case. The
    dictionaries must have this form:

        title="Name of the autor or reviewer",
        role="author or reviewer",
        link="mailto:email or http://contactpage"

    shouldConvert: A boolean indicating if the SFNT is valid enough for
    conversion to WOFF.

    flavor: The flavor of the WOFF data. The options are CFF or TTF.
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
            shouldConvert=shouldConvert,
            specLink=specLink
        )
    )


def makeFormat3IFT():
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
    # return b'\x00\x01\x00\x00\x00\x0c\x44\x53\x49\x47\x00\x00\x00\x08'
    return tbl.data

writeTest(
    identifier="tabledata-dsig-001",
    title="Format 1 with valid format number",
    description="The IFT table 'format' field is set to 3, which is a invalid format number.",
    shouldConvert=True,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#conform-format1-valid-format-number",
    func=makeFormat3IFT
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

# ----------------
# Generate the zip
# ----------------

print("Compiling zip file...")

zipPath = os.path.join(clientTestDirectory, "ClientTestFonts.zip")
if os.path.exists(zipPath):
    os.remove(zipPath)

allBinariesZip = zipfile.ZipFile(zipPath, "w")

pattern = os.path.join(clientTestDirectory, "*.?t?")
for path in glob.glob(pattern):
    ext = os.path.splitext(path)[1]
    assert ext in (".otf", ".ttf", ".otc", ".ttc")
    allBinariesZip.write(path, os.path.basename(path))

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

# -----------------------
# Check for Unknown Files
# -----------------------

otfPattern = os.path.join(clientTestDirectory, "*.otf")
ttfPattern = os.path.join(clientTestDirectory, "*.ttf")
otcPattern = os.path.join(clientTestDirectory, "*.otc")
ttcPattern = os.path.join(clientTestDirectory, "*.ttc")
filesOnDisk = glob.glob(otfPattern) + glob.glob(ttfPattern) + glob.glob(otcPattern) + glob.glob(ttcPattern)

for path in filesOnDisk:
    identifier = os.path.basename(path)
    identifier = identifier.split(".")[0]
    if identifier not in registeredIdentifiers:
        print("Unknown file:", path)
