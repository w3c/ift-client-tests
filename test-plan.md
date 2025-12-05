# High Level Plan

The IFT client tests in the repository will be designed to be executed by a browser which implements the IFT
specification. The tests will be provided as a series of HTML files, and collection of IFT fonts. When viewed by an IFT
capable browser the tests will exercise IFT functionality around the various client conformance statements and display a
visible PASS or FAIL if the browser correctly handles the test.

These tests will take the same appraoch as the [WOFF2 conformance tests](https://github.com/w3c/woff2-compiled-tests)
where specially crafted HTML and font combinations will be used to probe the user agent's IFT client side implementation.

For example, let's say we needed to check that the user agent correctly rejects a IFT font that contains invalid data.
The test file would have some text which is configured to first use an IFT font to render it, and then as a fallback a
non-incremental font. The IFT font is modified to be invalid. The non-incremental font is modified to display a "PASS"
glyph when rendering the sample text. If the user agent is implemented correctly it will fail to use the IFT font and
fallback to the non-incremental font.  As a result a PASS glyph will be displayed.

Since no browsers currently implement IFT, as a temporary work around a javascript polyfill built from the
[fontations IFT client](https://github.com/googlefonts/fontations/tree/main/incremental-font-transfer) will be utilized.
Once, browser support becomes available we can rework the framework to no longer rely on the polyfill.

The incremental font extension specification supports 4 main types of outline tables: glyf, gvar, CFF, and CFF2. Each
individual test should include 4 separate sub tests each using one of the outline formats (where the outline format is
relevant to the test). In the same vein we should ensure we have some test coverage for the various colour formats
(eg. COLRv0, COLRv1, sbix, SVG, and CBDT/CBLC). While these aren't treated specially by the spec they are of
special interest due to being alternate ways for encoding glyph outlines. Glyph keyed patches do not yet support
the extending the bitmap and SVG tables, but the spec may be expanded to add that.

# Test Case Plans

## Test ID: extend-font-subset

The incremental font extension algorithm is the heart of incremental font transfer. It will require a large collection
of tests to fully cover the various aspects and corner cases of it. Here is a non-exhaustive list of some areas of
concern:

* Error cases: throughout the algorithm there are various points where it can exit with an error. We should aim to have
  at least one test per error case. These tests will generally look pretty similar in that they'll attempt to load a font
  which will trigger the specific error with the expectation that the font fails to load.
  
* Incremental font extension can happen along three different aspects of content presence: unicode codepoints, variable
  design space, and, layout features. Testing of the extension algorithm should aim to cover all three of these.
  
* Step 7 and 8: the ordering of patch selection is a key feature of the extension algorithm. We'll want to ensure we
  have sufficient test coverage that probes the clients selection ordering. There are two main areas of importance:
  ordering of selection between multiple invalidation categories, and ordering of selection within invalidating patches
  which has a [separate selection criteria](https://w3c.github.io/IFT/Overview.html#invalidating-patch-selection). The
  latter has it's own conformance ID so test coverage there will be discussed in a later section.
  
  It should be possible to test ordering via the use of patches that overwrite each other (for example patches that
  completely replace the glyf/CFF table). This would give a way to tell which patch was applied last.
  
  Note: classification directly effects ordering decisions. So testing ordering can also be used to probe classification
  of patches by the client.
  
* Step 10: we'll want tests that check the client respects the various request limits introduced here.

* We'll want to be sure that the tests include cases which involve more than one iteration of the extension algorithm.
  For example to ensure that the client isn't just repeating the first iteration over and over.
  
* We'll want to ensure we have some tests covering the mixed glyph + table keyed + design space extension use case.
  including things such as having table keyed patches which overwrite the glyph keyed patch mapping. Potential client
  side issues could include things such as using a cached patch mapping and as a result not respecting the patch mapping
  changes introduced by the table keyed patch.
  
## Test ID: conform-stop-extend-after-errors

The approach to this test will be to introduce an error in an otherwise valid IFT font (where it would be technically
possible to continue extension). Test will ensure that no further patches get applied (if they are that would set the
“FAIL” glyph).

## Test ID: fully-expanding-a-font

This one will be interesting to test since it's typically not reachable via the standard IFT client use case. It will likely
need to be invoked via a save page for offline viewing flow in the browser. Once the that problem is solved, the test
itself will be straightforward. Javascript will modify the saved page upon viewing to attempt to access a codepoint that
isn't originally present. The test passes if correctly rendered.

## Test ID: Format 1 and 2 Validation

There are a collection of validation requirements for format 1 and 2. The tests for these should generally be straightforward.
A font that is crafted to fail each validation requirement will be tested for rejection.

TODO: this should be expanded into individual sections for each id.

## Test ID: Format 1 and 2 Interpretation

The results of patch map interpretation are primarily visible via the behaviour of the extension algorithm. So these
algorithms will primarily be covered by the suite of extension algorithm tests. We'll want to ensure that the extension
algorithm tests contain both format 1 and format 2 test cases.

There will be a some cases that are specific to each of the two formats. For format 1:

* Mappings with entry index = 0 should be ignored.

* Applied entries bitmap should be respected and the marked entries are ignored.

* Cases where multiple entries map to the same URL (due to a URL template which only partially utilizes the entry index).
  In the spec the URL is effectively a unique key for an entry. So if there are multiple entry ids that result in
  the same URL these get merged into a single entry prior to extension.

For format 2:

* Of particular note is the sparse bit set encoding, which will need to have test coverage. Some areas of interest:
  bias, 0 bytes to fill in ranges, handling of trailing data.

* Two different ways of specifying URLs (id string data or numeric indices), we will want coverage of both.

* Design space was not supported in format 1 but is in format 2, so tests will also need to cover design space cases.

* In format 2 entries can overlap, which should be covered in tests.

* Entry indices are based on previous entries, so tests should include cases with more than one entry to ensure this aspect is correctly
  handled.

* Copy indices mechanism will need coverage. Including nested conjunctive/disjunctive conditions.

* Test will be need for rejection of child indices that are too large.

TODO: this should be expanded into individual sections for each id.

## Test ID: Url Template Expansion

Test coverage is needed for the different op codes, and literal expansion variables. Patch loading is a direct result
of template expansion so it should be straightforward to check the results of expansion via which URLs get requested, where
the correct URL loads a patch that causes a pass.

## Test ID: Glyph and Table Keyed Patch Interpretation

These will also be covered implicitly inside of the extension algorithm tests, since the extension algorithm will apply
patches. However, there are some areas the may need separate tests:

* Validation requirements from the two formats.
* Glyph keyed patch application + CFF specific requirements.
* Handling of compatibility IDs, particularly rejection of mismatched ones.
* In glyph keyed, ignoring unsupported tables.
* Error handling.

TODO: this should be expanded into individual sections for each id.
