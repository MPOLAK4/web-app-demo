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


class Round3EditorTests(unittest.TestCase):
    """R10(i), R11(g): picture-file links, data mode, data panel. Try them by hand too."""

    def test_R11_editor_gets_block_text_from_the_server_not_its_own_rules(self):
        """R10(d): the per-type text rules live only in render.content_lines."""
        js = read("app.js")
        self.assertNotIn("function contentLines", js)
        self.assertIn("/api/lines", js)

    def test_R10_page_has_save_html_and_svg_links_that_ask_the_server(self):
        """R10(i)."""
        html, js = read("index.html"), read("app.js")
        self.assertIn('id="save-html"', html)
        self.assertIn('id="save-svg"', html)
        self.assertIn("/api/render?state=", js)
        self.assertIn("download=1", js)

    def test_R11_page_has_a_debug_live_choice_and_a_data_panel(self):
        """R11(g)."""
        html = read("index.html")
        self.assertRegex(html, r'id="data-mode"[^>]*>\s*<option value="debug">debug</option><option value="live">live</option>')
        for ident in ("data-list", "add-data-form", "new-data-key", "new-data-value"):
            self.assertIn(f'id="{ident}"', html)

    def test_R11_editor_edits_data_only_through_ops(self):
        """R11(g): CLAUDE.md, editing rules live in ops."""
        sent = set(re.findall(r'op: "([a-z_]+)"', read("app.js")))
        self.assertTrue({"set_data", "delete_data"} <= sent)

    def test_R11_play_asks_for_the_chosen_mode_and_draws_server_lines(self):
        """R11(g): Play shows the mode too, and still never sends an edit."""
        js = read("app.js")
        self.assertIn("/api/play?state=${encodeURIComponent(stateId)}&data=${dataMode}", js)
        self.assertIn("b.lines", js)

    def test_R11_inspector_edits_raw_text(self):
        """R11(g): the inspector must not be fed standins, or saving would write them back."""
        js = read("app.js")
        start = js.index("function renderInspector")
        end = js.index("\nfunction ", start + 10)
        self.assertNotIn("linesOf", js[start:end])
        self.assertNotIn("lines[", js[start:end])


if __name__ == "__main__":
    unittest.main()
