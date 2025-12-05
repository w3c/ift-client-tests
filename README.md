# IFT Client Tests
This is the repository for a **test suite for clients** which claim to conform to
the W3C [Incremental Font Transfer specification](https://w3c.github.io/IFT/Overview.html), 
developed by the [W3C Web Fonts working group](https://www.w3.org/Fonts/WG/).

## Setup

This repository pulls in a copy of the specification to check test coverage via git submodules,
so you will need to run:

```bash
# From the repository root
git submodule init
git submodule update
```

To initialize the repository.

## Test Coverage Reports

Run 

```bash
# From the repository root
make all
```

To generate test and test plan coverage reports (test-coverage-report.txt and
test-plan-coverage-report.txt) that specify which specification client
conformance statements are not covered.

## Generate Client Tests

Client tests have the following dependencies:

* FontTools https://github.com/behdad/fonttools
* Bazel https://bazel.build/install
* C++ compiler (gcc/clang)

The test cases are generated as follows:

Create the fallback font:

```bash
# From the repository root
ift-client-tests$ cd generators
ift-client-tests/generators$ python makeSubsettedFont.py fallback
```

(this will generate font files that substitute the letter `P` with the glyph sequence `FAIL` and the letter `F` with the glyph sequence `PASS`)

Create the source font for the IFT:

```bash
# From the repository root
ift-client-tests$ cd generators
ift-client-tests/generators$ python makeSubsettedFont.py ift
```

(this will generate font files that substitute the letter `P` with the glyph sequence `PASS` and the letter `F` with the glyph sequence `FAIL`)

To encode the subsetted IFT from the IFT source font:

```bash
# From the repository root
ift-client-tests$ cd encoder
ift-client-tests/encoder$ make
```

Compile the client test suite:

```bash
# From the repository root
ift-client-tests$ cd generators
ift-client-tests/generators$ python ClientTestCaseGenerator.py
```