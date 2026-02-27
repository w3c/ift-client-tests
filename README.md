# IFT Client Tests
This is the repository for a **test suite for clients** which claim to conform to
the W3C [Incremental Font Transfer specification](https://w3c.github.io/IFT/Overview.html),
developed by the [W3C Web Fonts working group](https://www.w3.org/Fonts/WG/).

## Testing Plan

[Testing Plan](test-plan.md): A document describing the planned approach to the IFT client tests.

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

```bash
# From the repository root
make test-coverage-report.txt
```

To generate test coverage reports (test-coverage-report.txt) that specify which specification client
conformance statements are covered and not covered.

## Generate Client Tests

Client tests have the following dependencies:

* FontTools https://github.com/behdad/fonttools
* Bazel https://bazel.build/install
* C++ compiler (gcc/clang)

The test cases are generated as follows:

```bash
# From the repository root
make IFTClient/Tests/xhtml1/index.html
```

This will create the html client test suite, which will be found under IFTClient/