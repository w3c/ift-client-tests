# High Level Plan

The IFT client tests in the repository will be designed to be executed by a browser which implements the IFT
specification. The tests will be provided as a series of HTML files, and collection of IFT fonts. When viewed by an IFT
capable browser the tests will exercise IFT functionality around the various client conformance statements and display a
visible PASS or FAIL if the browser correctly handles the test.

These tests will take the same appraoch as the [WOFF2 conformance tests](https://github.com/w3c/woff2-compiled-tests)
where specially crafted HTML and font combinations will be used to probe the user agent's IFT client side implementation.

For example, let's say we needed to check that the user agent correctly rejects a IFT font that contains invalid data.
The test file would have some text which is configured to irst use an IFT font to render it, and then as a fallback a
non-incremental font. The IFT font is modified to be invalid. The non-incremental font is modified to display a "PASS"
glyph when rendering the sample text. If the user agent is implemented correctly it will fail to use the IFT font and
fallback to the non-incremental font.  As a result a PASS glyph will be displayed.

# Test Case Plans

## Test ID: conform-stop-extend-after-errors

TODO describe how this test will be set up.

TODO add additional sections for each of the client conformance statements.

