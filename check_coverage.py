"""
Usage
python3 check_coverage.py <path to spec html> <tested ids file>
"""

import sys

from html.parser import HTMLParser


def print_usage():
  print("python3 check_coverage.py <path to spec html> <path to tested ids>")


class ConformanceStatementFinder(HTMLParser):
  """Finds all conformance statements tagged in the spec."""

  def __init__(self):
    super().__init__()
    self.in_span = False
    self.conformance_ids = set()

  def handle_starttag(self, tag, attrs):
    if tag != "span":
      return

    attr_map = {a[0]: a[1] for a in attrs}
    if "id" not in attr_map or "class" not in attr_map:
      return

    if "conform" not in attr_map["class"]:
      return
    if "server" not in attr_map["class"]:
      return

    self.conformance_ids.add(attr_map["id"])

  def handle_endtag(self, tag):
    pass

  def handle_data(self, data):
    pass

  def error(self, message):
    pass


def run(html_path, tested_ids_path):
  """Report which conformance statements are not being tested."""
  with open(html_path, "r", encoding='utf-8') as html_file:
    html_text = html_file.read()

  finder = ConformanceStatementFinder()
  finder.feed(html_text)
  spec_ids = finder.conformance_ids
  tested_ids = tested_conformance_ids(tested_ids_path)

  untested_ids = spec_ids - tested_ids
  if len(untested_ids) > 0:
    print("Conformance statements in Spec that are not tested:")
    for i in untested_ids:
      print(i)
  print("")

  missing_from_spec = tested_ids - spec_ids
  if len(missing_from_spec) > 0:
    print("Tested IDs that are not in the spec:")
    for i in missing_from_spec:
      print(i)


def tested_conformance_ids(tested_ids_path):
  """Loads the test of ids which have been tested."""
  with open(tested_ids_path, "r", encoding='utf-8') as tested_ids_file:
    tested_ids_text = tested_ids_file.readlines()

  ids = set()
  line_start = "tested conformance id: "
  for line in tested_ids_text:
    if line.startswith(line_start):
      ids.add(line[len(line_start):-1])

  return ids


if __name__ == '__main__':
  if len(sys.argv) != 3:
    print_usage()
    sys.exit()

  run(sys.argv[1], sys.argv[2])
