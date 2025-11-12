"""
Paths to important directories and files.
"""

import os

def dirname(path, depth=1):
    """
    >>> path = "/5/4/3/2/1"
    >>> dirname(path)
    '/5/4/3/2'
    >>> dirname(path, 2)
    '/5/4/3'
    >>> dirname(path, 3)
    '/5/4'
    >>> dirname(path, 4)
    '/5'
    """
    for i in range(depth):
        path = os.path.dirname(path)
    return path

mainDirectory = dirname(__file__)
mainDirectory = dirname(mainDirectory, 2)

# directory for test case resources,
resourcesDirectory = os.path.join(mainDirectory, "generators", "resources")
# paths to specific resources
IFTSourcePath = os.path.join(resourcesDirectory, "IFT", "GLYF", "font.ift.woff2")
# directory for source font file
TTFSourcePath = os.path.join(mainDirectory,"generators","sourceFonts","glyf.ttf") 
CFFSourcePath = os.path.join(mainDirectory,"generators","sourceFonts","cff.otf") 
# directory for subsetted font files
subsetFontPath = os.path.join(mainDirectory,"generators","subsettedFonts") 
# fallback font path
fallbackFontPath = os.path.join(subsetFontPath, "glyf-fallback.ttf")
# directories for test output
fontsDirectory = os.path.join(mainDirectory, "client","fonts")
# directory for subset fonts
subsetDirectory = os.path.join(mainDirectory,"generators", "subsettedFonts")
fallbackDirectory = os.path.join(fontsDirectory, "fallback")

clientDirectory = os.path.join(mainDirectory, "IFTClient")
clientTestDirectory = os.path.join(clientDirectory, "Tests", "xhtml1")
clientTestResourcesDirectory = os.path.join(clientTestDirectory, "resources")

if __name__ == "__main__":
    import doctest
    doctest.testmod()
