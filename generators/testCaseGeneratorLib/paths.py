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

# directory for SFNT data, test case templates,
resourcesDirectory = os.path.join(mainDirectory, "generators", "resources")
# paths to specific resources
TTFSourcePath = os.path.join(resourcesDirectory, "Roboto-Regular.ttf")
IFTSourcePath = os.path.join(resourcesDirectory, "myfont.ift.ttf")

# directories for test output
IFTTestDirectory = os.path.join(mainDirectory, "IFT")

if __name__ == "__main__":
    import doctest
    doctest.testmod()
