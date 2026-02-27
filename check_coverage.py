"""
Usage
python3 check_coverage.py <path to spec html> <tested ids file>
"""

import sys

from html.parser import HTMLParser


def print_usage():
  print("python3 check_coverage.py <path to spec html> <path to test html>")

class ImplementedTestFinder(HTMLParser):
  """Finds all implemented tests in the client test HTML."""

  def __init__(self):
    super().__init__()
    self.conformance_ids = set()

  def handle_starttag(self, tag, attrs):
    if tag != "div":
      return

    attr_map = {a[0]: a[1] for a in attrs}
    if "id" not in attr_map or "class" not in attr_map:
      return

    if "testCase" not in attr_map["class"]:
      return

    # In the test HTML all tests are prefixed with "client-" remove it
    test_id = attr_map["id"].removeprefix("client-")
    self.conformance_ids.add(test_id)

  def handle_endtag(self, tag):
    pass

  def handle_data(self, data):
    pass

  def error(self, message):
    pass

class ConformanceStatementFinder(HTMLParser):
  """Finds all conformance statements tagged in the spec."""

  def __init__(self):
    super().__init__()
    self.algorithm_conformance_ids = set()
    self.conformance_ids = set()

  def handle_starttag(self, tag, attrs):
    if tag != "span" and tag != "h3" and tag != "h4" and tag != "h5":
      return

    attr_map = {a[0]: a[1] for a in attrs}

    if "id" not in attr_map or "class" not in attr_map:
      return

    if "conform" not in attr_map["class"]:
      return

    if "client" not in attr_map["class"]:
      return

    if"data-algorithm" in attr_map:
      self.algorithm_conformance_ids.add(attr_map["id"])
    else:
      self.conformance_ids.add(attr_map["id"])

  def handle_endtag(self, tag):
    pass

  def handle_data(self, data):
    pass

  def error(self, message):
    pass


def run(spec_html_path, test_html_path):
  """Report which conformance statements are not being tested."""
  with open(spec_html_path, "r", encoding='utf-8') as html_file:
    spec_html_text = html_file.read()

  with open(test_html_path, "r", encoding='utf-8') as html_file:
    test_html_text = html_file.read()

  finder = ConformanceStatementFinder()
  finder.feed(spec_html_text)
  spec_ids = finder.conformance_ids
  spec_algorithm_ids = finder.algorithm_conformance_ids

  finder = ImplementedTestFinder()
  finder.feed(test_html_text)
  tested_ids = finder.conformance_ids

  algorithm_coverage = {id: 0 for id in spec_algorithm_ids}
  normalized_tested_ids = set()
  for id in tested_ids:
    prefix = id.split('_')[0]
    normalized_tested_ids.add(prefix)
    if prefix not in spec_algorithm_ids:
      continue
    algorithm_coverage[prefix] += 1
  tested_ids = normalized_tested_ids

  # Section 1 tests that are missing coverage
  untested_ids = (spec_ids | spec_algorithm_ids) - tested_ids
  if len(untested_ids) > 0:
    print("# Conformance statements in Spec that are not tested:")
    for i in untested_ids:
      print(f"UNTESTED {i}")


  print("# Algorithm test coverage:")
  for id, count in algorithm_coverage.items():
    if count > 0:
      print(f"TEST_COUNT {id} {count}")

  missing_from_spec = tested_ids - spec_ids - spec_algorithm_ids

  if len(missing_from_spec) > 0:
    print("# Tested IDs that are not in the spec:")
    for i in missing_from_spec:
      print(f"NOT_IN_SPEC {i}")


if __name__ == '__main__':
  if len(sys.argv) != 3:
    print_usage()
    sys.exit()

  run(sys.argv[1], sys.argv[2])
