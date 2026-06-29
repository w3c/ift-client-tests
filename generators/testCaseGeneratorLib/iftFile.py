import os
import glob
import shutil
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.DefaultTable import DefaultTable
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
        self.tbl = self.font["IFT "]
        # fontTools (>= 4.63) decodes "IFT " into a structured table_I_F_T_,
        # so compile it back to the on-disk bytes for byte-level callers.
        self.raw = bytearray(self.tbl.compile(self.font))
        return self.raw
    def setIFTTableData(self, data):
        self.raw = bytearray(data)
        # Swap in a raw DefaultTable to bypass fontTools table validation
        # so that intentionally malformed bytes can be written verbatim.
        rawTable = DefaultTable("IFT ")
        rawTable.data = bytes(self.raw)
        self.font["IFT "] = rawTable
        self.tbl = rawTable
    def removeTable(self,tableTag):
        del self.font[tableTag]
    def writeTestIFTFile(self):
        outPath = os.path.join(self.testDirectory, self.format, self.fontFileName)
        self.font.save(outPath)