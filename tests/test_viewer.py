"""R13: the clickable viewer file, and R12(i)/(j) bits that live in the editor and the guide.

Nothing here can open a browser. What can be checked: the file is self-contained,
its data is exactly what the Python rules answer, wireframe text cannot become
markup, and the page's script is valid JavaScript. Opening `viewer.html` by
double-click and clicking around must still be tried by hand.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from wireframe import cli, model, play, render, spec, viewer
from wireframe.example import example_wireframe
from helpers import block, doc, state, transition
from test_server import ServerTestCase
from test_static import read

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sample():
    a = state("a", [block("b1", "button", 10, 20, 120, 40, label="Total {{t}}", event="go"),
                    block("b2", "button", 10, 80, 120, 40, label="Off", event="never") | {"disabled": True},
                    block("hid", "text", label="HIDDEN") | {"hidden": True, "event": "ghost"},
                    block("two", "link", 200, 20, 80, 20, label="Pick", event="pick")])
    b = state("b", [block("b3", "text", label="Done")], final=True)
    c = state("c", [])
    d = doc([a, b, c], [transition("t1", "a", "b", "go"),
                        transition("t2", "a", "b", "pick", guard="x is true"),
                        transition("t3", "a", "c", "pick", guard="x is false"),
                        transition("t4", "a", "c", "sys:timeout")], name="My App")
    d["data"] = {"t": "$9"}
    return d


def extract_data(html):
    """The JSON block the page reads its data from."""
    match = re.search(r'<script type="application/json" id="wireframe-data">(.*?)</script>', html, re.S)
    assert match, "no data block"
    return json.loads(match.group(1))


class ViewerContentTests(unittest.TestCase):
    def setUp(self):
        self.doc = sample()
        self.html = viewer.build_viewer(self.doc)
        self.data = extract_data(self.html)

    def test_R13_file_is_self_contained(self):
        """R13(a): nothing is loaded from anywhere, and the page makes no network request."""
        self.assertTrue(self.html.lstrip().startswith("<!DOCTYPE html>"))
        self.assertNotRegex(self.html, r"https?://(?!www\.w3\.org/2000/svg)")
        self.assertNotRegex(self.html, r'\b(src|href)="(?!#|data:)')
        for word in ("fetch(", "XMLHttpRequest", "WebSocket", "import(", "importScripts"):
            self.assertNotIn(word, self.html, word)

    def test_R13_every_screen_carries_its_pictures_in_both_data_modes(self):
        """R13(b): the SVG is exactly what render_screen makes."""
        self.assertEqual(set(self.data["states"]), {"a", "b", "c"})
        for sid, info in self.data["states"].items():
            for mode in ("debug", "live"):
                self.assertEqual(info["svg"][mode], render.render_screen(self.doc, sid, "svg", mode))
        self.assertIn("Total $9", self.data["states"]["a"]["svg"]["live"])
        self.assertIn("{{t}}", self.data["states"]["a"]["svg"]["debug"])

    def test_R13_screen_facts_match_play(self):
        """R13(b): title, final flag, first screen and events come from play.screen."""
        self.assertEqual(self.data["initial"], "a")
        self.assertEqual(self.data["name"], "My App")
        self.assertEqual(self.data["canvas"], {"width": 800, "height": 600})
        for sid, info in self.data["states"].items():
            scr = play.screen(self.doc, sid)
            self.assertEqual(info["title"], scr["title"])
            self.assertEqual(info["final"], scr["final"])
            self.assertEqual(info["events"], scr["events"] + scr["system_events"])

    def test_R13_click_areas_are_visible_enabled_blocks_that_raise_events(self):
        """R13(b): a disabled or hidden block gets no hotspot; its box is the block's box."""
        spots = self.data["states"]["a"]["hotspots"]
        self.assertEqual(spots, [{"x": 10, "y": 20, "w": 120, "h": 40, "event": "go"},
                                 {"x": 200, "y": 20, "w": 80, "h": 20, "event": "pick"}])
        self.assertEqual(self.data["states"]["b"]["hotspots"], [])

    def test_R13_every_event_has_the_answer_play_step_gives(self):
        """R13(b): moved / choose / stuck are looked up, never decided by the page."""
        steps = self.data["states"]["a"]["steps"]
        for event in ("go", "pick", "sys:timeout"):
            self.assertEqual(steps[event], play.step(self.doc, "a", event), event)
        self.assertEqual(steps["go"]["status"], "moved")
        self.assertEqual(steps["pick"]["status"], "choose")
        self.assertEqual(len(steps["pick"]["options"]), 2)
        self.assertNotIn("never", steps)        # disabled blocks offer no event
        self.assertNotIn("ghost", steps)        # hidden blocks neither

    def test_R13_an_event_nothing_handles_is_recorded_as_stuck(self):
        """R13(b)."""
        d = doc([state("a", [block("b1", "button", event="lost")])])
        data = extract_data(viewer.build_viewer(d))
        self.assertEqual(data["states"]["a"]["steps"]["lost"]["status"], "stuck")

    def test_R13_choose_answer_can_be_resolved_to_a_screen(self):
        """R13(b): each option of a choose names a transition and a target that exist."""
        for o in self.data["states"]["a"]["steps"]["pick"]["options"]:
            self.assertEqual(play.step(self.doc, "a", "pick", o["transition"])["state"], o["target"])
            self.assertIn(o["target"], self.data["states"])

    def test_R13_output_is_deterministic_and_building_does_not_change_the_document(self):
        """R13(e)."""
        before = json.dumps(self.doc, sort_keys=True)
        self.assertEqual(viewer.build_viewer(self.doc), viewer.build_viewer(self.doc))
        self.assertEqual(json.dumps(self.doc, sort_keys=True), before)

    def test_R13_wireframe_text_cannot_break_out_of_the_page(self):
        """R13(c): a label or name holding </script> or markup stays text."""
        evil = "</script><script>alert(1)</script><img src=x onerror=alert(2)>"
        d = doc([state("a", [block("b1", "text", label=evil)], title=evil)], name=evil)
        html = viewer.build_viewer(d)
        self.assertEqual(html.count("<script"), 2)            # the data block and the page's own script
        self.assertEqual(html.count("</script>"), 2)
        self.assertNotIn("<img src=x", html)
        data = extract_data(html)                              # still valid JSON, text intact
        self.assertEqual(data["name"], evil)
        self.assertEqual(data["states"]["a"]["title"], evil)

    def test_R13_page_carries_a_content_security_policy(self):
        """R13(c): no network, images only from data:."""
        match = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', self.html)
        self.assertTrue(match)
        policy = match.group(1)
        self.assertIn("default-src 'none'", policy)
        self.assertIn("img-src data:", policy)
        self.assertNotIn("connect-src", policy)

    def test_R13_page_has_the_controls_the_spec_lists(self):
        """R13(d): screen list, debug/live, Back, Restart, Save SVG, a place for options."""
        for ident in ("screen-list", "data-mode", "btn-back", "btn-restart", "save-svg",
                      "picture", "event-list", "choice-box", "message"):
            self.assertIn(f'id="{ident}"', self.html, ident)

    def test_R13_the_page_shows_pictures_with_img_not_innerhtml_of_wireframe_text(self):
        """R13(c): an <img> cannot run script; innerHTML would let a label become markup."""
        self.assertIn("data:image/svg+xml", self.html)
        self.assertNotIn("innerHTML", self.html)
        self.assertNotIn("eval(", self.html)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_R13_page_script_is_valid_javascript(self):
        """R13(d): a syntax slip would leave a blank page; node --check catches it."""
        script = re.findall(r"<script>(.*?)</script>", self.html, re.S)[-1]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "page.js")
            with open(path, "w", encoding="utf-8") as f:
                f.write(script)
            result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_R13_works_for_an_old_style_document_and_the_example(self):
        """R13: no new fields are needed; a minimal file and the example both build."""
        extract_data(viewer.build_viewer(doc([state("only", [])])))
        data = extract_data(viewer.build_viewer(example_wireframe()))
        self.assertEqual(data["initial"], example_wireframe()["initial"])


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class ViewerCommandTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "w.json")
        model.save(sample(), self.path)

    def test_R13_viewer_command_writes_the_file(self):
        """R13(f)."""
        out_path = os.path.join(self.dir.name, "v.html")
        code, out, err = run("viewer", self.path, "--out", out_path)
        self.assertEqual(code, 0, err)
        with open(out_path, encoding="utf-8") as f:
            self.assertEqual(f.read(), viewer.build_viewer(sample()))

    def test_R13_viewer_command_replaces_an_existing_file(self):
        """R13(f)."""
        out_path = os.path.join(self.dir.name, "v.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("old")
        run("viewer", self.path, "--out", out_path)
        with open(out_path, encoding="utf-8") as f:
            self.assertNotEqual(f.read(), "old")

    def test_R13_viewer_command_prints_without_out(self):
        """R13(f)."""
        code, out, _ = run("viewer", self.path)
        self.assertEqual(code, 0)
        self.assertEqual(out, viewer.build_viewer(sample()))
        self.assertIn("wireframe-data", out)

    def test_R13_viewer_command_fails_cleanly_on_a_bad_file_and_writes_nothing(self):
        """R13(f)."""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{nope")
        out_path = os.path.join(self.dir.name, "v.html")
        code, _, err = run("viewer", self.path, "--out", out_path)
        self.assertEqual(code, 1)
        self.assertTrue(err)
        self.assertFalse(os.path.exists(out_path))


class ViewerApiTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        model.save(sample(), self.path)

    def test_R13_api_viewer_returns_the_page(self):
        """R13(g)."""
        status, headers, body = self.call("GET", "/api/viewer")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/html"))
        self.assertEqual(body.decode(), viewer.build_viewer(sample()))
        self.assertNotIn("Content-Disposition", headers)

    def test_R13_api_viewer_download_adds_a_filename(self):
        """R13(g)."""
        _, headers, _ = self.call("GET", "/api/viewer?download=1")
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="My-App-viewer.html"')

    def test_R13_api_viewer_is_get_only(self):
        """R13(g)."""
        status, _, _ = self.call("POST", "/api/viewer", {})
        self.assertEqual(status, 405)


class RepositoryViewerTests(unittest.TestCase):
    def test_R13_viewer_html_in_the_repository_is_up_to_date(self):
        """R13(h): the committed file is the example, built by the current code."""
        with open(os.path.join(ROOT, "viewer.html"), encoding="utf-8", newline="") as f:
            committed = f.read().replace("\r\n", "\n")
        self.assertEqual(committed, viewer.build_viewer(example_wireframe()))


class EditorAndGuideTests(unittest.TestCase):
    def test_R12_editor_pings_every_minute(self):
        """R12(i): the heartbeat targets /api/ping at a 60 second interval."""
        js = read("app.js")
        self.assertRegex(js, r"setInterval\([^;]*?60[_ ]?000\)|setInterval\([^;]*?60 \* 1000\)")
        self.assertIn("/api/ping", js)

    def test_R13_editor_offers_save_viewer(self):
        """R13(g)."""
        self.assertRegex(read("index.html"), r'id="save-viewer"[^>]*href="/api/viewer\?download=1"|href="/api/viewer\?download=1"[^>]*id="save-viewer"')

    def test_R12_guide_prefers_the_command_line_and_says_to_stop_servers(self):
        """R12(j)."""
        guide = spec.authoring_guide()
        for phrase in ("python -m wireframe stop", "python -m wireframe start", "no server"):
            self.assertIn(phrase, guide, phrase)


if __name__ == "__main__":
    unittest.main()
