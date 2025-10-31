"""
Test case HTML generator.
"""

import os
import html

from testCaseGeneratorLib.paths import clientTestResourcesDirectory

# ------------------------
# Specification URLs
# This is used frequently.
# ------------------------

specificationURL = "https://www.w3.org/TR/IFT/";

# -------------------
# Do not edit warning
# -------------------

doNotEditWarning = "<!-- THIS FILE WAS AUTOMATICALLY GENERATED, DO NOT EDIT. -->"

# ------------------
# SFNT Display Tests
# ------------------

testPassCharacter = "P"
testFailCharacter = "F"
refPassCharacter = testPassCharacter

testCSS = """
@import url("support/test-fonts.css");
@font-face {
	font-family: "IFT Test";
	src: url("%s/%s.woff2") format("woff2");
}
body {
	font-size: 20px;
}
pre {
	font-size: 12px;
}
.test {
	font-family: "IFT Test", "IFT Test %s Fallback";
	font-size: 200px;
	margin-top: 50px;
}
""".strip()

refCSS = """
@import url("support/test-fonts.css");
body {
	font-size: 20px;
}
pre {
	font-size: 12px;
}
.test {
	font-family: "IFT Test %s Reference";
	font-size: 200px;
	margin-top: 50px;
}
""".strip()

def escapeAttributeText(text):
    text = html.escape(text)
    replacements = {
        "\"" : "&quot;",
    }
    for before, after in replacements.items():
        text = text.replace(before, after)
    return text

def poorManMath(text):
    import re
    return re.sub(r"\^\{(.*.)\}", r"<sup>\1</sup>", text)

def generateClientIndexHTML(directory=None, testCases=[], note=None):
    testCount = sum([len(group["testCases"]) for group in testCases])
    html_string = [
        "<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.1//EN\" \"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd\">",
        doNotEditWarning,
        "<html xmlns=\"http://www.w3.org/1999/xhtml\">",
        "\t<head>",
        "\t\t<title>Incremenetal Font Transfer: Client Test Suite</title>",
        "\t\t<style type=\"text/css\">",
        "\t\t\t@import \"resources/index.css\";",
        "\t\t</style>",
        "\t\t<style type=\"text/css\">",
        "\t\t\t@import \"resources/fonts.css\";",
        "\t\t</style>",
        "\t\t<script type=\"text/javascript\" src=\"resources/cc-client/brotli.js\"></script>",
        "\t\t<script type=\"module\" src=\"resources/ift.js\"></script>",
        "\t\t<script>",
        "    createModule().then(function (Module) {",
        "      window.Woff2Decoder = Module.Woff2Decoder;",
        "    });",
        "  </script>",
        "\t</head>",
        "\t<body>",
        "\t\t<h1>Incremental Font Transfer: Client Test Suite (%d tests)</h1>" % testCount,
    ]
    # add a download note
    html_string.append("\t\t<div class=\"mainNote\">")
    html_string.append("\t\t\tThe files used in these test can be obtained individually <a href=\"../xhtml1\">here</a> or as a single zip file <a href=\"ClientTestFonts.zip\">here</a>.")
    html_string.append("\t\t</div>")
    # add the note
    if note:
        html_string.append("\t\t<div class=\"mainNote\">")
        for line in note.splitlines():
            html_string.append("\t\t\t" + line)
        html_string.append("\t\t</div>")
    # add the test groups
    for group in testCases:
        title = group["title"]
        title = html.escape(title)
        # write the group header
        html_string.append("")
        html_string.append("\t\t<h2 class=\"testCategory\">%s</h2>" % title)
        # write the group note
        note = group["note"]
        if note:
            html_string.append("\t\t<div class=\"testCategoryNote\">")
            for line in note.splitlines():
                html_string.append("\t\t\t" + line)
            html_string.append("\t\t</div>")
        # write the individual test cases
        for test in group["testCases"]:
            identifier = test["identifier"]
            title = test["title"]
            title = html.escape(title)
            description = test["description"]
            description = html.escape(description)
            shouldShowIFT = test["shouldShowIFT"]
            if shouldShowIFT:
                shouldShowIFT = "P"
            else:
                shouldShowIFT = "F"
            specLink = test["specLink"]
            # start the test case div
            html_string.append("\t\t<div class=\"testCase\" id=\"%s\">" % identifier)
            # start the overview div
            html_string.append("\t\t\t<div class=\"testCaseOverview\">")
            # title
            html_string.append("\t\t\t\t<h3><a href=\"#%s\">%s</a>: %s</h3>" % (identifier, identifier, title))
            # assertion
            html_string.append("\t\t\t\t<p>%s</p>" % description)
            # close the overview div
            html_string.append("\t\t\t</div>")
            # start the details div
            html_string.append("\t\t\t<div class=\"testCaseDetails\">")
            # validity
            
            render_text = "Should Render IFT" if shouldShowIFT != "F" else "Should Not Render IFT"
            string = "%s: <span id=\"%s\" class=\"result\">%s</span>" % (render_text, identifier, shouldShowIFT)
            html_string.append("\t\t\t\t\t<p>%s</p>" % string)
            # documentation
            if specLink is not None:
                links = specLink.split(' ')

                html_string.append("\t\t\t\t\t<p>")
                for link in links:
                    name = 'Documentation'
                    if '#' in link:
                        name = link.split('#')[1]
                    string = "\t\t\t\t\t\t<a href=\"%s\">%s</a> " % (link, name)
                    html_string.append(string)
                html_string.append("\t\t\t\t\t</p>")

            # close the details div
            html_string.append("\t\t\t</div>")
            # close the test case div
            html_string.append("\t\t</div>")
    # close body
    html_string.append("\t</body>")
    # close html
    html_string.append("</html>")
    # finalize
    html_string = "\n".join(html_string)
    # write
    path = os.path.join(directory, "testcaseindex.xht")
    f = open(path, "w")
    f.write(html_string)
    f.close()

def expandSpecLinks(links):
    """
    This function expands anchor-only references to fully qualified spec links.
    #name expands to <iftspecurl>#name. 

    links: 0..N space-separated #anchor references
    """
    if links is None or len(links) == 0:
        links = ""

    specLinks = []
    for link in links.split(" "):
        link = specificationURL + link

        specLinks.append(link)

    return " ".join(specLinks)
