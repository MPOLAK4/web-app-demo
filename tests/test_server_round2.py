"""HTTP API additions for Round 2: play (R9) and resolved styles (R6, R8)."""
import unittest

from wireframe import model, styles
from test_play import flow
from test_server import ServerTestCase
from helpers import block, doc, state


class PlayApiTests(ServerTestCase):
    def setUp(self):
        super().setUp()
        model.save(flow(), self.path)

    def test_R9_get_play_describes_a_screen(self):
        """R9(a): GET /api/play?state=ID."""
        status, body = self.jcall("GET", "/api/play?state=home")
        self.assertEqual(status, 200)
        self.assertEqual(body["state"], "home")
        self.assertEqual(body["events"], ["go", "pick"])

    def test_R9_get_play_without_state_starts_at_the_initial_screen(self):
        """R9(a)."""
        status, body = self.jcall("GET", "/api/play")
        self.assertEqual((status, body["state"]), (200, "home"))

    def test_R9_get_play_unknown_state_is_400(self):
        """R9(a)."""
        status, body = self.jcall("GET", "/api/play?state=zzz")
        self.assertEqual(status, 400)
        self.assertIn("zzz", body["errors"][0])

    def test_R9_post_play_takes_a_step(self):
        """R9(b)."""
        status, body = self.jcall("POST", "/api/play", {"state": "home", "event": "go"})
        self.assertEqual((status, body["status"], body["state"]), (200, "moved", "next"))

    def test_R9_post_play_can_ask_for_a_choice_and_take_it(self):
        """R9(c)."""
        _, body = self.jcall("POST", "/api/play", {"state": "home", "event": "pick"})
        self.assertEqual(body["status"], "choose")
        _, body = self.jcall("POST", "/api/play", {"state": "home", "event": "pick", "choice": "t3"})
        self.assertEqual((body["status"], body["state"]), ("moved", "a"))

    def test_R9_post_play_rejects_a_malformed_request(self):
        """R9(b): state and event must be strings."""
        for bad in ({}, {"state": "home"}, {"state": 1, "event": "go"}, {"state": "home", "event": 3},
                    {"state": "home", "event": "go", "choice": 5}, [1]):
            with self.subTest(bad=bad):
                status, _ = self.jcall("POST", "/api/play", bad)
                self.assertEqual(status, 400)

    def test_R9_playing_never_changes_the_file(self):
        """R9(d)."""
        before = self.stored()
        self.jcall("POST", "/api/play", {"state": "home", "event": "go"})
        self.jcall("GET", "/api/play?state=next")
        self.assertEqual(self.stored(), before)

    def test_R9_play_endpoint_rejects_other_methods(self):
        """R9: known path, wrong method is 405 like the other endpoints."""
        status, _ = self.jcall("DELETE", "/api/play")
        self.assertEqual(status, 405)

    def test_R9_post_play_must_be_json(self):
        """R1(f) still applies: a form post from another web page is refused."""
        status, _, _ = self.call("POST", "/api/play", raw=b"state=home&event=go",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(status, 415)


class ResolvedApiTests(ServerTestCase):
    def test_R6_resolved_maps_every_block_to_its_full_style(self):
        """R6(b): the editor draws with these, so it never has to copy the default table."""
        d = doc([state("s", [block("a", "button"), block("b", "text")])])
        d["styles"] = {"p": {"fill": "#123456"}}
        d["states"][0]["blocks"][0]["style"] = "p"
        model.save(d, self.path)
        status, body = self.jcall("GET", "/api/resolved")
        self.assertEqual(status, 200)
        self.assertEqual(set(body), {"s/a", "s/b"})
        self.assertEqual(body["s/a"]["fill"], "#123456")
        self.assertEqual(set(body["s/b"]), set(styles.STYLE_FIELDS))

    def test_R6_resolved_is_read_only(self):
        """R6(b)."""
        status, _ = self.jcall("POST", "/api/resolved", {})
        self.assertEqual(status, 405)


if __name__ == "__main__":
    unittest.main()
