# IFT Client Tests
This is the repository for a **test suite for clients** which claim to conform to
the W3C [Incremental Font Transfer specification](https://w3c.github.io/IFT/Overview.html), 
developed by the [W3C Web Fonts working group](https://www.w3.org/Fonts/WG/).

## Setup

This repository pulls in a copy of the specification to check test coverage via git submodules,
so you will need to run:

```
git submodule init
git submodule update
```

To initialize the repository.

## Test Coverage Reports

Run 

```
make all
```

To generate test and test plan coverage reports (test-coverage-report.txt and
test-plan-coverage-report.txt) that specify which specification client
conformance statements are not covered.
