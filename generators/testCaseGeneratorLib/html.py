"""
Test case HTML generator.
"""

import os
import html

from testCaseGeneratorLib.paths import clientTestResourcesDirectory
from testCaseGeneratorLib.assertions import BUILTIN_ASSERTIONS

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


def _emit_assert_paragraph(html_string, test_id, font_format, assertion):
    type_id = assertion["assert"]
    spec = BUILTIN_ASSERTIONS[type_id]
    label = spec.label(assertion["value"], assertion.get("scope"))
    span = spec.emit_html(
        test_id,
        font_format,
        assertion["value"],
        assertion.get("scope"),
        assertion.get("config") or None,
    )
    html_string.append(
        "\t\t\t\t\t<p>%s: %s (%s)</p>"
        % (html.escape(label), span, font_format)
    )


def _emit_single_shot_test(html_string, test):
    identifier = test["identifier"]
    title = html.escape(test["title"])
    description = html.escape(test["description"])
    shouldShowIFT = test["shouldShowIFT"]
    fontFormats = test["fontFormats"]
    char = "P" if shouldShowIFT else "F"
    specLink = test["specLink"]
    assertions = test.get("assertions") or []

    html_string.append("\t\t<div class=\"testCase\" id=\"%s\">" % identifier)
    html_string.append("\t\t\t<div class=\"testCaseOverview\">")
    html_string.append(
        "\t\t\t\t<h3><a href=\"#%s\">%s</a>: %s</h3>" % (identifier, identifier, title)
    )
    html_string.append("\t\t\t\t<p>%s</p>" % description)
    html_string.append("\t\t\t</div>")
    html_string.append("\t\t\t<div class=\"testCaseDetails\">")

    render_text = "Should Render IFT" if shouldShowIFT else "Should Not Render IFT"
    for fontFormat in fontFormats:
        format_identifier = "%s-%s" % (fontFormat, identifier)
        string = (
            '%s: <span id="%s" data-format="%s" class="result">%s</span> (%s)'
            % (render_text, format_identifier, fontFormat, char, fontFormat)
        )
        html_string.append("\t\t\t\t\t<p>%s</p>" % string)
        for assertion in assertions:
            _emit_assert_paragraph(html_string, identifier, fontFormat, assertion)

    if specLink is not None:
        links = specLink.split(" ")
        html_string.append("\t\t\t\t\t<p>")
        for link in links:
            name = "Documentation"
            if "#" in link:
                name = link.split("#")[1]
            html_string.append("\t\t\t\t\t\t<a href=\"%s\">%s</a> " % (link, name))
        html_string.append("\t\t\t\t\t</p>")

    html_string.append("\t\t\t</div>")
    html_string.append("\t\t</div>")


def _emit_sequence_test(html_string, test):
    identifier = test["identifier"]
    title = html.escape(test["title"])
    description = html.escape(test["description"])
    shouldShowIFT = test["shouldShowIFT"]
    fontFormats = test["fontFormats"]
    char = "P" if shouldShowIFT else "F"
    specLink = test["specLink"]
    sequence = test.get("sequence") or []

    html_string.append(
        "\t\t<div class=\"testCase sequence\" id=\"%s\">" % identifier
    )
    html_string.append("\t\t\t<div class=\"testCaseOverview\">")
    html_string.append(
        "\t\t\t\t<h3><a href=\"#%s\">%s</a>: %s</h3>" % (identifier, identifier, title)
    )
    html_string.append("\t\t\t\t<p>%s</p>" % description)
    html_string.append("\t\t\t</div>")

    for fontFormat in fontFormats:
        html_string.append(
            "\t\t\t<div class=\"testCaseDetails\" data-format=\"%s\" data-test-id=\"%s\">"
            % (fontFormat, identifier)
        )

        if shouldShowIFT is not None:
            # Visual P/F inside sequence — legacy loader skips .testCase.sequence
            format_identifier = "%s-%s" % (fontFormat, identifier)
            render_text = (
                "Should Render IFT" if shouldShowIFT else "Should Not Render IFT"
            )
            string = (
                '%s: <span id="%s" data-format="%s" class="result">%s</span> (%s)'
                % (render_text, format_identifier, fontFormat, char, fontFormat)
            )
            html_string.append("\t\t\t\t\t<p>%s</p>" % string)

        last_render_index = None
        for seq_index, item in enumerate(sequence):
            if "action" in item:
                last_render_index = seq_index
                text = html.escape(item["text"])
                html_string.append(
                    "\t\t\t\t<div class=\"sequence-item sequence-render\" "
                    "data-seq-index=\"%d\" data-test-id=\"%s\" data-format=\"%s\">"
                    % (seq_index, identifier, fontFormat)
                )
                html_string.append(
                    "\t\t\t\t\t<p>Render: <span class=\"render-text\">%s</span></p>"
                    % text
                )
                html_string.append("\t\t\t\t</div>")
            else:
                after = (
                    ' data-after-render="%d"' % last_render_index
                    if last_render_index is not None
                    else ""
                )
                html_string.append(
                    "\t\t\t\t<div class=\"sequence-item sequence-assert\" "
                    "data-seq-index=\"%d\"%s>"
                    % (seq_index, after)
                )
                type_id = item["assert"]
                spec = BUILTIN_ASSERTIONS[type_id]
                label = html.escape(spec.label(item["value"], item.get("scope")))
                span = spec.emit_html(
                    identifier,
                    fontFormat,
                    item["value"],
                    item.get("scope"),
                    item.get("config") or None,
                )
                html_string.append(
                    "\t\t\t\t\t<p>%s: %s</p>" % (label, span)
                )
                html_string.append("\t\t\t\t</div>")

        if specLink is not None:
            links = specLink.split(" ")
            html_string.append("\t\t\t\t\t<p>")
            for link in links:
                name = "Documentation"
                if "#" in link:
                    name = link.split("#")[1]
                html_string.append(
                    "\t\t\t\t\t\t<a href=\"%s\">%s</a> " % (link, name)
                )
            html_string.append("\t\t\t\t\t</p>")

        html_string.append("\t\t\t</div>")

    html_string.append("\t\t</div>")


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
            if test.get("sequential"):
                _emit_sequence_test(html_string, test)
            else:
                _emit_single_shot_test(html_string, test)
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
