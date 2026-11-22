"""The browser editor's files (R1(e)).

Python's unittest cannot click buttons, so these tests check what it can: the
files exist, the page points at files that exist, the JavaScript parses, and
the editor only sends ops that the server really knows. Dragging and resizing
must still be tried by hand in a browser (see README).
"""
import os
import re
import shutil
import subprocess
import unittest

from wireframe import ops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")


def read(name):
    with open(os.path.join(STATIC, name), encoding="utf-8") as f:
        return f.read()


class EditorFilesTests(unittest.TestCase):
    def test_R1_editor_files_exist(self):
        """R1(e)."""
        for name in ("index.html", "style.css", "app.js"):
            self.assertTrue(os.path.isfile(os.path.join(STATIC, name)), name)

    def test_R1_page_links_only_to_files_that_exist(self):
        """A typo in a <script src> or <link href> would give a blank, silent page."""
        html = read("index.html")
        links = re.findall(r'(?:src|href)="(/static/[^"]+)"', html)
        self.assertTrue(links)
        for link in links:
            self.assertTrue(os.path.isfile(os.path.join(STATIC, link[len("/static/"):])), link)

    def test_R1_every_element_id_the_script_uses_exists_in_the_page(self):
        """app.js looks elements up by id; a missing one stops the whole script."""
        html_ids = set(re.findall(r'id="([^"]+)"', read("index.html")))
        used = set(re.findall(r'\$\("([^"]+)"\)', read("app.js")))
        self.assertEqual(used - html_ids, set())

    def test_R1_the_editor_never_writes_html_from_data(self):
        """R1(f)/safety: labels are user text; innerHTML would let a label run as code."""
        # Look at code only: comments are allowed to mention the banned words.
        js = "\n".join(line.split("//")[0] for line in read("app.js").splitlines())
        for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            self.assertNotIn(banned, js)

    def test_R1_every_op_the_editor_sends_exists_on_the_server(self):
        """The browser and the headless interface share one list of ops."""
        sent = set(re.findall(r'op: "([a-z_]+)"', read("app.js")))
        self.assertTrue(sent)
        self.assertEqual(sent - set(ops.OPS), set())

    def test_R1_block_types_offered_match_the_model(self):
        from wireframe import model
        listed = re.search(r"BLOCK_TYPES = \[(.*?)\];", read("app.js"), re.S).group(1)
        self.assertEqual(set(re.findall(r'"(\w+)"', listed)), set(model.BLOCK_TYPES))

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_R1_javascript_has_no_syntax_errors(self):
        result = subprocess.run(["node", "--check", os.path.join(STATIC, "app.js")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
