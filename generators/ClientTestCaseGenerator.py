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
shutil.copytree(os.path.join(resourcesDirectory, "fallback"), destPath)
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
    ("conform", "Client Conformance Tests", expandSpecLinks("#DataTables"), clientNote),
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

def writeTest(identifier, title, description, func, specLink=None, credits=[], shouldShowIFT=False, flavor="CFF"):
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

    func: The function that generates the IFT files specific for the test.

    specLink: The anchor in the WOFF spec that the test case is testing.

    credits: A list of dictionaries defining the credits for the test case. The
    dictionaries must have this form:

        title="Name of the autor or reviewer",
        role="author or reviewer",
        link="mailto:email or http://contactpage"

    shouldShowIFT: A boolean indicating if the SFNT is valid enough for
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
            shouldShowIFT=shouldShowIFT,
            specLink=specLink
        )
    )


def makeIFTWithFormatID(format_id, test_name):
    test_directory = os.path.join(clientTestDirectory, test_name)
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
    raw[0] = format_id

    # Put the bytes back and save
    tbl.data = bytes(raw)
    font.save(outPath)

writeTest(
    identifier="conform-format2-valid-format-number",
    title="Format 2 with valid format number",
    description="The IFT table 'format' field for a format 2 is set to 3, which is a invalid format number.",
    shouldShowIFT=False,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#conform-format1-valid-format-number",
    func=lambda: makeIFTWithFormatID(3,"conform-format2-valid-format-number")
)
writeTest(
    identifier="conform-format1-valid-format-number",
    title="Format 1 with valid format number",
    description="The IFT table 'format' field for a format 1 is set to 3, which is a invalid format number.",
    shouldShowIFT=True,
    credits=[dict(title="Scott Treude", role="author", link="http://treude.com")],
    specLink="#conform-format2-valid-format-number",
    func=lambda: makeIFTWithFormatID(2,"conform-format1-valid-format-number")
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
conform_pattern = os.path.join(clientTestDirectory, "conform-*")
for dir_path in glob.glob(conform_pattern):
    if os.path.isdir(dir_path):
        dir_name = os.path.basename(dir_path)
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                archive_path = os.path.join(dir_name, os.path.relpath(file_path, dir_path))
                allBinariesZip.write(file_path, archive_path)

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
