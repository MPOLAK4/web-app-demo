"""HTTP API additions for Round 3: picture files (R10) and data mode (R11)."""
import unittest

from wireframe import model
from test_server import ServerTestCase
from helpers import block, doc, state, transition


def sample():
    a = state("a", [block("b1", "button", 10, 20, 120, 40, label="Total {{t}}", event="go"),
                    block("hid", "text", label="HIDDEN {{t}}") | {"hidden": True}])
    b = state("b", [block("b2", "checkbox", label="Agree") | {"value": "true"}])
    d = doc([a, b], [transition("t1", "a", "b", "go")], name="My App")
    d["data"] = {"t": "$9"}
    return d


class RenderApiTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        model.save(sample(), self.path)

    def test_R10_render_returns_svg_for_the_initial_screen(self):
        """R10(h)."""
        status, headers, body = self.call("GET", "/api/render")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("image/svg+xml"))
        self.assertTrue(body.decode().startswith("<svg"))

    def test_R10_render_html_state_and_data_mode(self):
        """R10(h), R11(f)."""
        status, headers, body = self.call("GET", "/api/render?state=a&format=html&data=live")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/html"))
        self.assertIn("Total $9", body.decode())
        _, _, raw = self.call("GET", "/api/render?state=a&data=debug")
        self.assertIn("{{t}}", raw.decode())

    def test_R10_after_events_selects_the_screen_reached(self):
        """R10(h): repeated after= parameters, like walk."""
        _, _, body = self.call("GET", "/api/render?after=go")
        self.assertIn("[x] Agree", body.decode())

    def test_R10_render_sends_a_policy_that_forbids_scripts(self):
        """R10(h): even if a label held markup, the browser would not run it."""
        _, headers, _ = self.call("GET", "/api/render?format=html")
        policy = headers["Content-Security-Policy"]
        self.assertIn("default-src 'none'", policy)
        self.assertNotIn("script-src", policy.replace("default-src 'none'", ""))

    def test_R10_download_adds_an_attachment_filename(self):
        """R10(h)."""
        _, headers, _ = self.call("GET", "/api/render?state=b&format=html&download=1")
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="My-App-b.html"')
        _, headers, _ = self.call("GET", "/api/render")
        self.assertNotIn("Content-Disposition", headers)

    def test_R10_bad_input_is_400(self):
        """R10(h): unknown screen, format or mode; both selectors; stuck event."""
        for query in ("state=zzz", "format=png", "data=fancy", "state=a&after=go", "after=nope"):
            with self.subTest(query=query):
                status, body = self.jcall("GET", "/api/render?" + query)
                self.assertEqual(status, 400)
                self.assertTrue(body["errors"])

    def test_R10_render_never_changes_the_file(self):
        """R10(h): read-only."""
        before = self.stored()
        self.call("GET", "/api/render?data=live&format=html")
        self.assertEqual(self.stored(), before)

    def test_R10_render_rejects_other_methods(self):
        """R10(h)."""
        status, _ = self.jcall("POST", "/api/render", {})
        self.assertEqual(status, 405)


class DataModeApiTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        model.save(sample(), self.path)

    def test_R10_lines_gives_every_block_its_text_lines(self):
        """R10(d): the browser asks the server instead of working it out itself."""
        status, body = self.jcall("GET", "/api/lines?state=b")
        self.assertEqual((status, body), (200, {"b2": ["[x] Agree"]}))

    def test_R11_lines_follow_the_data_mode(self):
        """R11(f)."""
        _, debug = self.jcall("GET", "/api/lines?state=a")
        _, live = self.jcall("GET", "/api/lines?state=a&data=live")
        self.assertEqual(debug["b1"], ["Total {{t}}"])
        self.assertEqual(live["b1"], ["Total $9"])
        self.assertIn("hid", live)          # the editor still draws hidden blocks

    def test_R11_lines_default_to_the_initial_screen_and_reject_bad_input(self):
        """R11(f)."""
        _, body = self.jcall("GET", "/api/lines")
        self.assertIn("b1", body)
        for query in ("data=fancy", "state=zzz"):
            status, _ = self.jcall("GET", "/api/lines?" + query)
            self.assertEqual(status, 400)

    def test_R11_play_blocks_carry_lines_in_the_chosen_mode(self):
        """R11(f): Play draws `lines`; hidden blocks are absent."""
        _, live = self.jcall("GET", "/api/play?state=a&data=live")
        self.assertEqual([b["lines"] for b in live["blocks"]], [["Total $9"]])
        _, debug = self.jcall("GET", "/api/play?state=a")
        self.assertEqual(debug["blocks"][0]["lines"], ["Total {{t}}"])
        status, _ = self.jcall("GET", "/api/play?data=fancy")
        self.assertEqual(status, 400)

    def test_R11_play_still_shows_the_stored_text_unchanged(self):
        """R11(g): a standin is never written back."""
        before = self.stored()
        self.jcall("GET", "/api/play?state=a&data=live")
        self.assertEqual(self.stored(), before)

    def test_R11_spec_endpoint_takes_data(self):
        """R11(e)."""
        _, _, live = self.call("GET", "/api/spec?mode=image&data=live")
        self.assertIn("Total $9", live.decode())
        _, _, debug = self.call("GET", "/api/spec?mode=image")
        self.assertIn("{{t}}", debug.decode())
        status, _ = self.jcall("GET", "/api/spec?mode=image&data=fancy")
        self.assertEqual(status, 400)

    def test_R11_set_data_op_over_http(self):
        """R11(d): the browser edits data with the same ops."""
        status, body = self.jcall("POST", "/api/op", {"op": "set_data", "key": "x.y", "value": "Z"})
        self.assertEqual((status, body["data"]["x.y"]), (200, "Z"))
        status, _ = self.jcall("POST", "/api/op", {"op": "set_data", "key": "bad key", "value": "Z"})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
