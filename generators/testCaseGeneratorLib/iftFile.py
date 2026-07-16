import os
import shutil
from fontTools.ttLib import TTFont
from testCaseGeneratorLib.paths import clientTestDirectory, buildDirectory

class IFTFile:
    def __init__(
        self,
        testName,
        format,
        fontFileName,
        sourceRelativeDir="IFT",
        destSubdir=None,
    ):
        self.testName = testName
        self.format = format
        self.fontFileName = fontFileName
        self.sourceRelativeDir = sourceRelativeDir
        self.destSubdir = destSubdir
        self.testDirectory = os.path.join(clientTestDirectory, testName)
        self.sourceDir = os.path.join(buildDirectory, sourceRelativeDir, format)
        self.sourceFontPath = os.path.join(self.sourceDir, "font.ift.woff2")
        if destSubdir:
            self.destDir = os.path.join(self.testDirectory, format, destSubdir)
        else:
            self.destDir = os.path.join(self.testDirectory, format)
        self.font = TTFont(self.sourceFontPath)
        self.tbl = None
        self.raw = None
        self.createTestDirectory()
        self.copyIFTSourceFiles()

    def createTestDirectory(self):
        if not os.path.exists(self.destDir):
            os.makedirs(self.destDir)

    def copyIFTSourceFiles(self):
        # Copy _gk and _tk files from the configured build IFT tree to destDir
        if not os.path.exists(self.destDir):
            os.makedirs(self.destDir)
        for name in os.listdir(self.sourceDir):
            if name == "font.ift.woff2":
                continue
            src = os.path.join(self.sourceDir, name)
            dst = os.path.join(self.destDir, name)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            print(f"Copied {src} to {dst}")

    def getIFTTableData(self):
        if "IFT " not in self.font:
            raise ValueError("IFT table not found in font.")
        # Unknown/custom tables are stored as raw bytes on .data
        self.tbl = self.font["IFT "]
        self.raw = bytearray(self.tbl.data)
        return self.raw

    def setIFTTableData(self, data):
        self.raw = bytearray(data)
        if self.tbl is not None:
            self.tbl.data = bytes(self.raw)

    def removeTable(self, tableTag):
        del self.font[tableTag]

    def writeTestIFTFile(self):
        outPath = os.path.join(self.destDir, self.fontFileName)
        self.font.save(outPath)
