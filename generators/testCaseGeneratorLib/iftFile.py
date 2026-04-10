import os
import glob
import shutil
from fontTools.ttLib import TTFont
from testCaseGeneratorLib.paths import clientTestDirectory, buildDirectory

class IFTFile:
    def __init__(self, testName,format,fontFileName):
        self.testName = testName
        self.format = format
        self.fontFileName = fontFileName
        self.testDirectory = os.path.join(clientTestDirectory, testName)
        self.sourceFontPath = os.path.join(buildDirectory, "IFT", format, "font.ift.woff2")
        self.font = TTFont(self.sourceFontPath)
        self.tbl = None
        self.raw = None
        self.createTestDirectory()
        self.copyIFTSourceFiles()
    def createTestDirectory(self):
        if not os.path.exists(self.testDirectory):
            os.makedirs(self.testDirectory)
    def copyIFTSourceFiles(self):
        # Copy _gk and _tk files from resources/IFT/ to testDirectory
        sourceDir = os.path.join(buildDirectory, "IFT",self.format)
        destDir = os.path.join(self.testDirectory,self.format)
        if not os.path.exists(destDir):
            os.makedirs(destDir)
        for pattern in ("*_gk", "*_tk"):
            for filePath in glob.glob(os.path.join(sourceDir, pattern)):
                shutil.copy(filePath, destDir)
                print(f"Copied {filePath} to {destDir}")
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
    def removeTable(self,tableTag):
        del self.font[tableTag]
    def writeTestIFTFile(self):
        outPath = os.path.join(self.testDirectory, self.format, self.fontFileName)
        self.font.save(outPath)